# -*- coding: utf-8 -*-
"""Colloqui clinici: la registrazione dell'incontro, per ogni professionista.

Fase 2 del modello PNEV. Ogni incontro (primo colloquio, colloquio con i
genitori, seduta, restituzione, incontro con la scuola) si registra qui, da
qualunque professionista dello studio: optometrista, psicologa, logopedista,
neuropsicomotricista, fisioterapista.

Tre modi di inserire il contenuto:
  · registrare o dettare dal microfono del computer o del telefono
  · caricare un file audio registrato altrove (es. col telefono)
  · scrivere a mano
L'audio viene trascritto e poi SCARTATO: nel database resta solo il testo.
La registrazione richiede il consenso, da spuntare prima di ogni colloquio.

Dal testo l'AI propone una sintesi e i rilievi PNEV (fonte «colloquio»):
entrano nel profilo solo dopo la conferma del clinico, come per i documenti.
Tutto resta modificabile.
"""
from __future__ import annotations

import datetime
import hashlib
import io
import json

import streamlit as st

RUOLI = ["Optometrista comportamentale", "Psicologo/a", "Logopedista",
         "Neuropsicomotricista (TNPEE)", "Fisioterapista", "Osteopata",
         "Educatore / pedagogista", "Medico", "Altro"]
TIPI = ["Primo colloquio (anamnestico)", "Colloquio con i genitori", "Colloquio con il paziente",
        "Seduta", "Restituzione", "Rivalutazione",
        "Incontro con scuola / altri professionisti", "Telefonata", "Altro"]

# Cosa guarda ciascuna figura: orienta la sintesi dell'AI, non la limita.
GUIDA = {
    "Optometrista comportamentale": "sintomi visivi riferiti, uso degli occhi da vicino, lettura, postura, affaticamento, cefalea",
    "Psicologo/a": "motivo della richiesta, vissuti, clima e relazioni familiari, regolazione emotiva, comportamento osservato, risorse",
    "Logopedista": "linguaggio espressivo e ricettivo, articolazione, fluenza, deglutizione e funzioni orali, lettura e scrittura",
    "Neuropsicomotricista (TNPEE)": "motricità globale e fine, tono, schema corporeo, gioco, regolazione sensoriale, relazione",
    "Fisioterapista": "postura, equilibrio, dolore, mobilità, schemi motori",
    "Osteopata": "postura, tensioni, respirazione, storia di traumi e interventi",
    "Educatore / pedagogista": "autonomie, comportamento in classe, apprendimenti, relazioni con i compagni",
    "Medico": "anamnesi medica, patologie, farmaci, esami, indicazioni",
}
_MAX_AUDIO = 25 * 1024 * 1024   # limite del servizio di trascrizione


# ── Database ──────────────────────────────────────────────────────────

def _assicura_tabella(conn) -> None:
    if st.session_state.get("_colloqui_schema_ok"):
        return
    try:
        cur = conn.cursor()
        cur.execute(
            "CREATE TABLE IF NOT EXISTS colloqui_clinici ("
            " id SERIAL PRIMARY KEY,"
            " paziente_id INTEGER NOT NULL,"
            " data DATE,"
            " ruolo TEXT, tipo TEXT, presenti TEXT, professionista TEXT,"
            " consenso_audio BOOLEAN DEFAULT FALSE,"
            " trascrizione TEXT, sintesi TEXT,"
            " creato_il TIMESTAMP DEFAULT CURRENT_TIMESTAMP,"
            " aggiornato_il TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        cur.execute("CREATE INDEX IF NOT EXISTS colloqui_clinici_paz ON colloqui_clinici (paziente_id, data)")
        conn.commit()
        st.session_state["_colloqui_schema_ok"] = True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass


def _q(conn, sql, par=()):
    try:
        cur = conn.cursor()
        cur.execute(sql, par)
        righe = cur.fetchall() or []
        if righe and not isinstance(righe[0], dict):
            nomi = [c[0] for c in cur.description]
            righe = [dict(zip(nomi, r)) for r in righe]
        return righe
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return []


def _esegui(conn, sql, par=(), ritorna_id=False):
    try:
        cur = conn.cursor()
        cur.execute(sql + (" RETURNING id" if ritorna_id else ""), par)
        nuovo = None
        if ritorna_id:
            r = cur.fetchone()
            nuovo = r.get("id") if isinstance(r, dict) else r[0]
        conn.commit()
        return nuovo, ""
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        return None, str(e)


def _utente():
    return str(st.session_state.get("username") or st.session_state.get("user") or "")


def colloqui(conn, paz_id):
    _assicura_tabella(conn)
    return _q(conn, "SELECT * FROM colloqui_clinici WHERE paziente_id=%s "
                    "ORDER BY data DESC NULLS LAST, id DESC", (int(paz_id),))


# ── Trascrizione ──────────────────────────────────────────────────────

def trascrivi(dati: bytes, nome: str = "audio.wav") -> tuple[str, str]:
    """(testo, errore). Usa il servizio di trascrizione di OpenAI."""
    if len(dati) > _MAX_AUDIO:
        return "", (f"File troppo grande ({len(dati) // (1024 * 1024)} MB, massimo 25). "
                    "Dividilo in parti o registralo a qualità più bassa.")
    try:
        a = st.secrets.get("ai", {})
    except Exception:
        a = {}
    chiave = a.get("OPENAI_API_KEY")
    if not chiave:
        return "", ("La trascrizione richiede OPENAI_API_KEY nei Secrets, sezione [ai]. "
                    "Nel frattempo puoi scrivere il testo a mano.")
    try:
        from openai import OpenAI
        f = io.BytesIO(dati)
        f.name = nome
        r = OpenAI(api_key=chiave).audio.transcriptions.create(
            model=str(a.get("OPENAI_TRANSCRIBE_MODEL", "whisper-1")), file=f, language="it")
        return (getattr(r, "text", "") or "").strip(), ""
    except Exception as e:
        return "", f"Trascrizione non riuscita: {e}"


def _acquisisci(audio, key_testo, key_hash, nome):
    """Trascrive un audio nuovo e lo accoda al testo. Va chiamata PRIMA di
    disegnare il riquadro del testo, altrimenti Streamlit non lo aggiorna."""
    if audio is None:
        return
    dati = audio.getvalue()
    firma = hashlib.md5(dati).hexdigest()
    if st.session_state.get(key_hash) == firma:
        return
    st.session_state[key_hash] = firma
    with st.spinner("Trascrizione in corso…"):
        testo, err = trascrivi(dati, getattr(audio, "name", None) or nome)
    if err:
        st.error(err)
        return
    prima = (st.session_state.get(key_testo) or "").rstrip()
    st.session_state[key_testo] = (prima + "\n\n" + testo).strip() if prima else testo
    st.success("Trascritto e aggiunto al testo. Rileggilo e correggilo prima di salvare.")


# ── Sintesi e rilievi con l'AI ────────────────────────────────────────

_PROMPT = """Sei l'assistente clinico dello Studio The Organism (modello PNEV).
Qui sotto c'è la trascrizione di un incontro. Professionista: {ruolo}.
Tipo di incontro: {tipo}. Presenti: {presenti}.
Per questa figura contano soprattutto: {guida}.

1. Scrivi una SINTESI clinica in italiano, 8-15 righe, in terza persona, solo
   con ciò che è stato detto o osservato. Distingui ciò che è RIFERITO (dalla
   famiglia, dal paziente) da ciò che è OSSERVATO dal professionista.
   Nessuna diagnosi che non sia stata detta esplicitamente.
2. Estrai i RILIEVI, uno per dato, classificati in uno dei sette livelli:
   7 Partecipazione e relazione · 6 Prestazione · 5 Funzioni percettive e
   cognitive · 4 Integrazione sensomotoria · 3 Canali sensoriali ·
   2 Riflessi e tono · 1 Regolazione (sonno, alimentazione, emozioni).

Rispondi SOLO con un oggetto JSON, senza testo prima o dopo:
{"sintesi": "...", "rilievi": [{"livello": 1, "area": "sonno", "testo": "...",
 "valore": "", "giudizio": "adeguato|ai limiti|fragile|da approfondire|",
 "riferito": true}]}

TRASCRIZIONE:
{testo}
"""


def _json_oggetto(t: str):
    t = (t or "").strip()
    i, j = t.find("{"), t.rfind("}")
    if i < 0 or j < i:
        return None
    try:
        x = json.loads(t[i:j + 1])
        return x if isinstance(x, dict) else None
    except Exception:
        return None


def elabora_con_ai(conn, paz_id, col) -> tuple[int, str]:
    from .ai_estrazione import ai_disponibile, genera_testo
    from .rilievi_pnev import LIVELLI, GIUDIZI, aggiungi_rilievo
    if not ai_disponibile():
        return 0, "AI non configurata nei Secrets."
    testo = (col.get("trascrizione") or "").strip()
    if len(testo) < 40:
        return 0, "Il testo del colloquio è troppo breve per una sintesi."
    prompt = (_PROMPT.replace("{ruolo}", col.get("ruolo") or "")
                     .replace("{tipo}", col.get("tipo") or "")
                     .replace("{presenti}", col.get("presenti") or "non indicati")
                     .replace("{guida}", GUIDA.get(col.get("ruolo"), "quadro generale"))
                     .replace("{testo}", testo[:14000]))
    risposta = genera_testo(prompt)
    if risposta.startswith("⚠️"):
        return 0, risposta
    x = _json_oggetto(risposta)
    if x is None:
        return 0, "L'AI non ha restituito una risposta leggibile: riprova."
    _esegui(conn, "UPDATE colloqui_clinici SET sintesi=%s, aggiornato_il=CURRENT_TIMESTAMP WHERE id=%s",
            (str(x.get("sintesi") or "").strip(), col["id"]))
    _esegui(conn, "DELETE FROM rilievi_pnev WHERE fonte='colloquio' AND fonte_id=%s AND stato='proposto'",
            (col["id"],))
    n = 0
    for r in x.get("rilievi") or []:
        if not isinstance(r, dict) or not str(r.get("testo") or "").strip():
            continue
        try:
            liv = int(r.get("livello") or 0)
        except Exception:
            liv = 0
        area = str(r.get("area") or "")
        if r.get("riferito"):
            area = (area + " · riferito").strip(" ·")
        err = aggiungi_rilievo(conn, paz_id, liv if liv in LIVELLI else None, str(r["testo"]).strip(),
                               "colloquio", area=area, valore=str(r.get("valore") or ""),
                               giudizio=r.get("giudizio") if r.get("giudizio") in GIUDIZI else "",
                               data=col.get("data"), autore=col.get("professionista") or "",
                               fonte_id=col["id"], stato="proposto")
        if not err:
            n += 1
    st.session_state[f"_coll_sint_{col['id']}"] = str(x.get("sintesi") or "").strip()
    return n, ""


# ── Disegno ───────────────────────────────────────────────────────────

def _nuovo(conn, paz_id, px, tipo_default):
    k = lambda s: f"{px}_n_{s}"
    with st.container(border=True):
        st.markdown("**➕ Nuovo colloquio**")
        c1, c2, c3 = st.columns([3, 3, 2])
        ruolo_def = st.session_state.get("_coll_ultimo_ruolo", RUOLI[0])
        ruolo = c1.selectbox("Professionista", RUOLI, key=k("ruolo"),
                             index=RUOLI.index(ruolo_def) if ruolo_def in RUOLI else 0)
        tipo = c2.selectbox("Tipo di incontro", TIPI, key=k("tipo"),
                            index=TIPI.index(tipo_default) if tipo_default in TIPI else 0)
        data = c3.date_input("Data", datetime.date.today(), key=k("data"), format="DD/MM/YYYY")
        presenti = st.text_input("Presenti", key=k("presenti"), placeholder="es. madre e bambino")

        modo = st.radio("Come inserisci il contenuto", ["🎙️ Registra o detta", "📁 Carica un file audio",
                                                        "⌨️ Scrivi"], horizontal=True, key=k("modo"))
        consenso = False
        if modo != "⌨️ Scrivi":
            consenso = st.checkbox("Il paziente, o chi ne ha la responsabilità, acconsente alla "
                                   "registrazione audio. L'audio viene trascritto e poi eliminato: "
                                   "si conserva solo il testo.", key=k("consenso"))
            if not consenso:
                st.caption("Spunta il consenso per attivare la registrazione. Per una dettatura "
                           "tua, senza il paziente, spuntalo comunque.")
            elif modo == "🎙️ Registra o detta":
                if hasattr(st, "audio_input"):
                    _acquisisci(st.audio_input("Premi il microfono per iniziare e di nuovo per fermare",
                                               key=k("mic")), k("testo"), k("h_mic"), "registrazione.wav")
                else:
                    st.caption("Questa versione di Streamlit non registra dal browser: carica un file audio.")
            else:
                _acquisisci(st.file_uploader("File audio (fino a 25 MB)", key=k("file"),
                                             type=["mp3", "m4a", "wav", "webm", "ogg", "mp4", "mpeg", "mpga"]),
                            k("testo"), k("h_file"), "audio.m4a")

        testo = st.text_area("Testo del colloquio", key=k("testo"), height=220,
                             placeholder="La trascrizione compare qui. Puoi correggerla o scrivere a mano.")
        if st.button("💾 Salva colloquio", key=k("salva"), type="primary", disabled=not testo.strip()):
            nuovo, err = _esegui(conn,
                "INSERT INTO colloqui_clinici (paziente_id, data, ruolo, tipo, presenti, professionista, "
                "consenso_audio, trascrizione) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                (int(paz_id), data, ruolo, tipo, presenti.strip(), _utente(), bool(consenso), testo.strip()),
                ritorna_id=True)
            if err:
                st.error(f"Non salvato: {err}")
            else:
                st.session_state["_coll_ultimo_ruolo"] = ruolo
                st.session_state[f"{px}_aperto"] = nuovo
                for s in ("testo", "presenti", "consenso", "h_mic", "h_file", "mic", "file"):
                    st.session_state.pop(k(s), None)
                st.rerun()


def _dettaglio(conn, paz_id, col, px):
    from .rilievi_pnev import rilievi, _revisione
    cid = col["id"]
    k = lambda s: f"{px}_c{cid}_{s}"
    with st.container(border=True):
        st.caption(" · ".join(x for x in (
            col.get("professionista") or "", col.get("presenti") or "",
            "audio con consenso" if col.get("consenso_audio") else "") if x))
        if k("testo") not in st.session_state:
            st.session_state[k("testo")] = col.get("trascrizione") or ""
        sint_nuova = st.session_state.pop(f"_coll_sint_{cid}", None)
        if sint_nuova is not None or k("sintesi") not in st.session_state:
            st.session_state[k("sintesi")] = sint_nuova if sint_nuova is not None else (col.get("sintesi") or "")
        testo = st.text_area("Testo del colloquio", key=k("testo"), height=200)
        sintesi = st.text_area("Sintesi clinica", key=k("sintesi"), height=140,
                               placeholder="Premi «Sintesi e rilievi» per farla proporre dall'AI, o scrivila tu.")
        b1, b2, b3 = st.columns([2, 3, 2])
        if b1.button("💾 Salva modifiche", key=k("salva")):
            _, err = _esegui(conn, "UPDATE colloqui_clinici SET trascrizione=%s, sintesi=%s, "
                                   "aggiornato_il=CURRENT_TIMESTAMP WHERE id=%s", (testo, sintesi, cid))
            st.error(err) if err else st.success("Salvato.")
        if b2.button("🤖 Sintesi e rilievi con AI", key=k("ai")):
            _esegui(conn, "UPDATE colloqui_clinici SET trascrizione=%s WHERE id=%s", (testo, cid))
            with st.spinner("Lettura del colloquio…"):
                n, err = elabora_con_ai(conn, paz_id, {**col, "trascrizione": testo})
            if err:
                st.error(err)
            else:
                st.rerun()
        if b3.button("🗑️ Elimina", key=k("del")):
            st.session_state[k("conferma_del")] = True
        if st.session_state.get(k("conferma_del")):
            st.warning("Eliminare questo colloquio? I rilievi già confermati restano nel profilo.")
            d1, d2, _ = st.columns([1, 1, 4])
            if d1.button("Sì, elimina", key=k("del_ok")):
                _esegui(conn, "DELETE FROM rilievi_pnev WHERE fonte='colloquio' AND fonte_id=%s "
                              "AND stato='proposto'", (cid,))
                _esegui(conn, "DELETE FROM colloqui_clinici WHERE id=%s", (cid,))
                st.session_state.pop(f"{px}_aperto", None)
                st.rerun()
            if d2.button("Annulla", key=k("del_no")):
                st.session_state.pop(k("conferma_del"), None)
                st.rerun()

        proposti = [r for r in rilievi(conn, paz_id, "proposto")
                    if r.get("fonte") == "colloquio" and r.get("fonte_id") == cid]
        if proposti:
            st.markdown(f"**Rilievi da confermare · {len(proposti)}**")
            _revisione(conn, proposti, k("ril"))


def _etichetta(c):
    d = c.get("data")
    d = d.strftime("%d/%m/%Y") if hasattr(d, "strftime") else str(d or "")
    return f"{d} · {c.get('ruolo') or ''} · {c.get('tipo') or ''}"


def render_colloqui(conn, paz_id, px: str = "coll", tipo_default: str | None = None) -> None:
    """Il blocco completo. Senza expander, cosi' si puo' mettere anche
    dentro altre pagine (anamnesi, protocollo)."""
    if conn is None or not paz_id:
        st.info("Seleziona un paziente.")
        return
    _assicura_tabella(conn)
    px = f"{px}_{paz_id}"
    st.markdown("**🎙️ Colloqui clinici**")
    st.caption("Ogni incontro, di ogni professionista dello studio. Registri, detti o scrivi; "
               "l'AI propone sintesi e rilievi, tu confermi. Sempre modificabile.")

    elenco = colloqui(conn, paz_id)
    if st.toggle("➕ Nuovo colloquio", key=f"{px}_mostra_nuovo", value=not elenco):
        _nuovo(conn, paz_id, px, tipo_default)
    if not elenco:
        return
    ids = [c["id"] for c in elenco]
    aperto = st.session_state.get(f"{px}_aperto")
    scelta = st.selectbox(f"Colloqui registrati · {len(elenco)}", [None] + ids, key=f"{px}_scelta",
                          index=(ids.index(aperto) + 1) if aperto in ids else 0,
                          format_func=lambda i: "— scegli un colloquio da aprire —" if i is None
                          else _etichetta(next(c for c in elenco if c["id"] == i)))
    if scelta:
        st.session_state[f"{px}_aperto"] = scelta
        _dettaglio(conn, paz_id, next(c for c in elenco if c["id"] == scelta), px)


def render_pagina_colloqui(conn, paz_id) -> None:
    st.subheader("🎙️ Colloqui clinici")
    render_colloqui(conn, paz_id, "pag")


# ── Per diagnosi e relazione ──────────────────────────────────────────

def sintesi_colloqui(conn, paz_id) -> list[str]:
    if conn is None or not paz_id:
        return []
    out = []
    for c in colloqui(conn, paz_id):
        corpo = (c.get("sintesi") or "").strip() or " ".join((c.get("trascrizione") or "").split())[:600]
        if corpo:
            out.append(f"- {_etichetta(c)}" + (f" (presenti: {c['presenti']})" if c.get("presenti") else "")
                       + f": {' '.join(corpo.split())}")
    return out
