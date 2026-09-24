# -*- coding: utf-8 -*-
"""Rilievi PNEV: l'unita' comune del modello.

Ogni cosa che si sa di una persona si registra come RILIEVO: un'osservazione
fatta in un momento preciso, a uno dei sette livelli del modello, con una
fonte dichiarata (anamnesi, documento esterno, colloquio, test, seduta).

Fase 1 del modello (vedi «Modello PNEV», documento di lavoro):
  · la tabella dei rilievi e i sette livelli
  · i documenti pregressi: si caricano, l'AI li legge e PROPONE i rilievi,
    il clinico conferma, corregge o scarta. Niente entra nel fascicolo
    senza conferma.
"""
from __future__ import annotations

import datetime
import json
import re

import streamlit as st

LIVELLI = {
    7: ("Partecipazione e relazione", "vita sociale, famiglia, ruolo"),
    6: ("Prestazione", "apprendimenti, lavoro, autonomie"),
    5: ("Funzioni percettive e cognitive", "visuo-percezione, ascolto, linguaggio, attenzione, memoria"),
    4: ("Integrazione sensomotoria", "postura, movimenti oculari, coordinazione, lateralità"),
    3: ("Canali sensoriali", "vestibolare, propriocettivo, tattile, uditivo, visivo"),
    2: ("Riflessi e tono", "riflessi primitivi e posturali, tono muscolare"),
    1: ("Regolazione", "sonno, alimentazione, allerta, emozioni"),
}
FONTI = ["documento esterno", "anamnesi", "colloquio", "test", "osservazione in seduta"]
GIUDIZI = ["", "adeguato", "ai limiti", "fragile", "da approfondire"]
_ETICH_LIV = {n: f"{n} · {v[0]}" for n, v in LIVELLI.items()}


# ── Database ──────────────────────────────────────────────────────────

def _assicura_tabella(conn) -> None:
    if st.session_state.get("_rilievi_schema_ok"):
        return
    try:
        cur = conn.cursor()
        cur.execute(
            "CREATE TABLE IF NOT EXISTS rilievi_pnev ("
            " id SERIAL PRIMARY KEY,"
            " paziente_id INTEGER NOT NULL,"
            " data_rilievo DATE,"
            " livello INTEGER,"
            " area TEXT,"
            " fonte TEXT,"
            " fonte_id INTEGER,"
            " testo TEXT,"
            " valore TEXT,"
            " giudizio TEXT,"
            " autore TEXT,"
            " stato TEXT DEFAULT 'proposto',"
            " creato_il TIMESTAMP DEFAULT CURRENT_TIMESTAMP,"
            " creato_da TEXT)")
        cur.execute("CREATE INDEX IF NOT EXISTS rilievi_pnev_paz ON rilievi_pnev (paziente_id, stato)")
        conn.commit()
        st.session_state["_rilievi_schema_ok"] = True
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


def _esegui(conn, sql, par=()) -> str:
    try:
        cur = conn.cursor()
        cur.execute(sql, par)
        conn.commit()
        return ""
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        return str(e)


def _utente():
    return str(st.session_state.get("username") or st.session_state.get("user") or "")


def rilievi(conn, paz_id, stato=None):
    _assicura_tabella(conn)
    if stato:
        return _q(conn, "SELECT * FROM rilievi_pnev WHERE paziente_id=%s AND stato=%s "
                        "ORDER BY livello DESC, data_rilievo DESC NULLS LAST, id",
                  (int(paz_id), stato))
    return _q(conn, "SELECT * FROM rilievi_pnev WHERE paziente_id=%s AND stato<>'scartato' "
                    "ORDER BY livello DESC, data_rilievo DESC NULLS LAST, id", (int(paz_id),))


def aggiungi_rilievo(conn, paz_id, livello, testo, fonte, area="", valore="", giudizio="",
                     data=None, autore="", fonte_id=None, stato="confermato") -> str:
    _assicura_tabella(conn)
    return _esegui(conn,
        "INSERT INTO rilievi_pnev (paziente_id, data_rilievo, livello, area, fonte, fonte_id, "
        "testo, valore, giudizio, autore, stato, creato_da) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (int(paz_id), data, int(livello) if livello else None, area, fonte, fonte_id,
         testo, valore, giudizio, autore, stato, _utente()))


# ── Documenti pregressi ───────────────────────────────────────────────

def _documenti(conn, paz_id):
    # Mai SELECT *: la colonna `dati` contiene il file intero.
    return _q(conn, "SELECT id, tipo, nome_file, note, estratto, data "
                    "FROM documenti_clinici WHERE paziente_id=%s ORDER BY data DESC", (int(paz_id),))


_PROMPT = """Sei un assistente clinico dello Studio The Organism (modello PNEV).
Dal referto qui sotto estrai i RILIEVI clinici, uno per dato. Non interpretare
oltre quanto scritto: riporta cosa dice il documento.

Classifica ogni rilievo in uno dei sette livelli:
7 Partecipazione e relazione · 6 Prestazione (apprendimenti, lavoro, autonomie)
5 Funzioni percettive e cognitive · 4 Integrazione sensomotoria (postura,
movimenti oculari, coordinazione) · 3 Canali sensoriali (vista, udito, tatto,
vestibolare) · 2 Riflessi e tono · 1 Regolazione (sonno, alimentazione, emozioni)

Rispondi SOLO con un array JSON, senza testo prima o dopo:
[{"livello": 3, "area": "visivo", "testo": "...", "valore": "...",
  "giudizio": "adeguato|ai limiti|fragile|da approfondire|", "data": "AAAA-MM-GG o vuoto",
  "autore": "chi ha firmato il referto, se indicato"}]

Diagnosi formulate da altri (es. codici ICD o DSM) vanno riportate con
area "diagnosi di riferimento", al livello più pertinente.

REFERTO ({nome}, caricato il {data}):
{testo}
"""


def _json_lista(t: str):
    t = (t or "").strip()
    t = re.sub(r"^```(?:json)?|```$", "", t, flags=re.M).strip()
    i, j = t.find("["), t.rfind("]")
    if i < 0 or j < i:
        return None
    try:
        x = json.loads(t[i:j + 1])
        return x if isinstance(x, list) else None
    except Exception:
        return None


def _data_valida(s):
    try:
        return datetime.date.fromisoformat(str(s)[:10])
    except Exception:
        return None


def proponi_da_documento(conn, paz_id, doc) -> tuple[int, str]:
    """Legge il documento con l'AI e inserisce i rilievi come «proposti»."""
    from .ai_estrazione import ai_disponibile, estrai_da_documento, genera_testo
    if not ai_disponibile():
        return 0, "AI non configurata nei Secrets."
    estratto = (doc.get("estratto") or "").strip()
    if not estratto:
        r = _q(conn, "SELECT dati, mime, nome_file FROM documenti_clinici WHERE id=%s", (doc["id"],))
        if not r:
            return 0, "documento non trovato"
        estratto = estrai_da_documento(bytes(r[0]["dati"]), r[0].get("mime") or "", r[0].get("nome_file") or "")
        if estratto.startswith("⚠️"):
            return 0, estratto
        _esegui(conn, "UPDATE documenti_clinici SET estratto=%s WHERE id=%s", (estratto, doc["id"]))
    # replace e non .format: il prompt contiene un esempio JSON con le graffe
    prompt = (_PROMPT.replace("{nome}", str(doc.get("nome_file") or doc.get("tipo") or "documento"))
                     .replace("{data}", str(doc.get("data") or "")[:10])
                     .replace("{testo}", estratto[:12000]))
    risposta = genera_testo(prompt)
    if risposta.startswith("⚠️"):
        return 0, risposta
    lista = _json_lista(risposta)
    if lista is None:
        return 0, "l'AI non ha restituito un elenco leggibile: riprova"
    _esegui(conn, "DELETE FROM rilievi_pnev WHERE fonte_id=%s AND fonte='documento esterno' AND stato='proposto'",
            (doc["id"],))
    n = 0
    for x in lista:
        if not isinstance(x, dict) or not str(x.get("testo") or "").strip():
            continue
        try:
            liv = int(x.get("livello") or 0)
        except Exception:
            liv = 0
        err = aggiungi_rilievo(conn, paz_id, liv if liv in LIVELLI else None, str(x.get("testo")).strip(),
                               "documento esterno", area=str(x.get("area") or ""),
                               valore=str(x.get("valore") or ""),
                               giudizio=x.get("giudizio") if x.get("giudizio") in GIUDIZI else "",
                               data=_data_valida(x.get("data")) or _data_valida(doc.get("data")),
                               autore=str(x.get("autore") or ""), fonte_id=doc["id"], stato="proposto")
        if not err:
            n += 1
    return n, ""


def _carica_documento(conn, paz_id, f, tipo) -> str:
    return _esegui(conn,
        "INSERT INTO documenti_clinici (paziente_id, tipo, nome_file, mime, dati, data) "
        "VALUES (%s,%s,%s,%s,%s,%s)",
        (int(paz_id), tipo, f.name, f.type or "", f.getvalue(), datetime.date.today()))


def render_documenti_pregressi(conn, paz_id, px="doc") -> None:
    """Il blocco da mettere nell'anamnesi: carica, leggi, conferma.
    Niente expander qui dentro: puo' essere disegnato dentro un altro."""
    if conn is None or not paz_id:
        return
    _assicura_tabella(conn)
    px = f"{px}_{paz_id}"
    st.markdown("**📎 Documenti pregressi**")
    st.caption("Referti, certificazioni, relazioni di altri professionisti. L'AI li legge e "
               "propone i rilievi: entrano nel fascicolo solo dopo la tua conferma.")

    with st.container(border=True):
        c1, c2 = st.columns([3, 2])
        f = c1.file_uploader("Carica un documento", type=["pdf", "png", "jpg", "jpeg"],
                             key=f"{px}_up", label_visibility="collapsed")
        tipo = c2.selectbox("Tipo", ["Referto specialistico", "Certificazione", "Relazione",
                                     "Esame strumentale", "Altro"], key=f"{px}_tipo")
        if f is not None and st.button("Salva nel fascicolo", key=f"{px}_salva_doc"):
            err = _carica_documento(conn, paz_id, f, tipo)
            st.error(f"Non salvato: {err}") if err else st.success(f"«{f.name}» salvato.")

    docs = _documenti(conn, paz_id)
    if not docs:
        st.caption("Nessun documento in archivio per questo paziente.")
        return
    proposti = rilievi(conn, paz_id, "proposto")
    per_doc = {}
    for r in _q(conn, "SELECT fonte_id, stato, COUNT(*) AS n FROM rilievi_pnev WHERE paziente_id=%s "
                      "AND fonte='documento esterno' GROUP BY fonte_id, stato", (int(paz_id),)):
        per_doc.setdefault(r["fonte_id"], {})[r["stato"]] = r["n"]

    for d in docs:
        stato = per_doc.get(d["id"], {})
        conf, prop = stato.get("confermato", 0), stato.get("proposto", 0)
        etich = ("✅ " + str(conf) + " rilievi confermati" if conf else
                 "🟡 " + str(prop) + " da confermare" if prop else "⚪ non ancora letto")
        c1, c2 = st.columns([4, 2])
        c1.markdown(f"{d.get('tipo') or 'Documento'} — {d.get('nome_file') or 's.n.'} "
                    f"· {str(d.get('data') or '')[:10]}  \n{etich}")
        if c2.button("🤖 Proponi rilievi" if not (conf or prop) else "🤖 Rileggi",
                     key=f"{px}_leggi_{d['id']}"):
            with st.spinner("Lettura del documento…"):
                n, err = proponi_da_documento(conn, paz_id, d)
            st.error(err) if err else st.success(f"{n} rilievi proposti.")
            st.rerun()

    if proposti:
        st.markdown(f"**Da confermare · {len(proposti)}**")
        _revisione(conn, proposti, px)


def _revisione(conn, righe, px):
    liv_opts = [None] + sorted(LIVELLI, reverse=True)
    if st.button("✅ Conferma tutti", key=f"{px}_tutti"):
        for r in righe:
            _esegui(conn, "UPDATE rilievi_pnev SET stato='confermato' WHERE id=%s AND livello IS NOT NULL", (r["id"],))
        st.rerun()
    for r in righe:
        with st.container(border=True):
            c1, c2, c3 = st.columns([2, 5, 2])
            liv = c1.selectbox("Livello", liv_opts, key=f"{px}_l_{r['id']}",
                               index=liv_opts.index(r.get("livello")) if r.get("livello") in liv_opts else 0,
                               format_func=lambda n: "—" if n is None else _ETICH_LIV[n])
            testo = c2.text_input("Rilievo", r.get("testo") or "", key=f"{px}_t_{r['id']}")
            giud = c3.selectbox("Giudizio", GIUDIZI, key=f"{px}_g_{r['id']}",
                                index=GIUDIZI.index(r.get("giudizio")) if r.get("giudizio") in GIUDIZI else 0)
            info = " · ".join(x for x in (r.get("area") or "", r.get("valore") or "",
                                          str(r.get("data_rilievo") or "")[:10], r.get("autore") or "") if x)
            if info:
                st.caption(info)
            b1, b2, _ = st.columns([1, 1, 4])
            if b1.button("Conferma", key=f"{px}_ok_{r['id']}", disabled=liv is None):
                _esegui(conn, "UPDATE rilievi_pnev SET livello=%s, testo=%s, giudizio=%s, stato='confermato' "
                              "WHERE id=%s", (liv, testo, giud, r["id"]))
                st.rerun()
            if b2.button("Scarta", key=f"{px}_no_{r['id']}"):
                _esegui(conn, "UPDATE rilievi_pnev SET stato='scartato' WHERE id=%s", (r["id"],))
                st.rerun()


# ── Pagina: profilo per livelli ───────────────────────────────────────

def render_rilievi(conn, paz_id) -> None:
    st.subheader("🧩 Rilievi PNEV")
    st.caption("Tutto ciò che si sa della persona, ordinato sui sette livelli del modello.")
    if conn is None or not paz_id:
        st.info("Seleziona un paziente.")
        return
    _assicura_tabella(conn)
    conf = rilievi(conn, paz_id, "confermato")

    with st.expander("➕ Aggiungi un rilievo", expanded=not conf):
        c1, c2, c3 = st.columns([2, 2, 1])
        liv = c1.selectbox("Livello", sorted(LIVELLI, reverse=True), format_func=lambda n: _ETICH_LIV[n], key="ril_n_liv")
        fonte = c2.selectbox("Fonte", FONTI[1:] + FONTI[:1], key="ril_n_fonte")
        data = c3.date_input("Data", datetime.date.today(), key="ril_n_data")
        testo = st.text_input("Rilievo", key="ril_n_testo", placeholder="es. Moro attivo")
        c4, c5, c6 = st.columns(3)
        area = c4.text_input("Area", key="ril_n_area", placeholder="es. riflessi primitivi")
        valore = c5.text_input("Valore", key="ril_n_val")
        giud = c6.selectbox("Giudizio", GIUDIZI, key="ril_n_giud")
        if st.button("Salva rilievo", key="ril_n_salva", disabled=not testo.strip()):
            err = aggiungi_rilievo(conn, paz_id, liv, testo.strip(), fonte, area, valore, giud, data, _utente())
            st.error(err) if err else st.rerun()

    render_documenti_pregressi(conn, paz_id, "ril")
    st.markdown("---")

    if not conf:
        st.info("Nessun rilievo confermato per ora.")
        return
    for n in sorted(LIVELLI, reverse=True):
        del_liv = [r for r in conf if r.get("livello") == n]
        fragili = sum(1 for r in del_liv if r.get("giudizio") in ("fragile", "ai limiti"))
        segno = "⚪" if not del_liv else ("🟠" if fragili else "🟢")
        st.markdown(f"{segno} **{_ETICH_LIV[n]}** · {len(del_liv)} rilievi"
                    + (f" · {fragili} fragili o ai limiti" if fragili else ""))
        for r in del_liv:
            dett = " · ".join(x for x in (r.get("giudizio") or "", r.get("valore") or "", r.get("fonte") or "",
                                          str(r.get("data_rilievo") or "")[:10]) if x)
            c1, c2 = st.columns([8, 1])
            c1.markdown(f"&nbsp;&nbsp;&nbsp;– {r.get('testo')}" + (f"  \n&nbsp;&nbsp;&nbsp;&nbsp;<small>{dett}</small>" if dett else ""),
                        unsafe_allow_html=True)
            if c2.button("✕", key=f"ril_del_{r['id']}", help="Scarta questo rilievo"):
                _esegui(conn, "UPDATE rilievi_pnev SET stato='scartato' WHERE id=%s", (r["id"],))
                st.rerun()


# ── Per relazione e diagnosi ──────────────────────────────────────────

def sintesi_rilievi(conn, paz_id) -> list[str]:
    if conn is None or not paz_id:
        return []
    out = []
    conf = rilievi(conn, paz_id, "confermato")
    for n in sorted(LIVELLI, reverse=True):
        righe = [r for r in conf if r.get("livello") == n]
        if not righe:
            continue
        out.append(f"LIVELLO {_ETICH_LIV[n].upper()}")
        for r in righe:
            extra = ", ".join(x for x in (r.get("giudizio") or "", r.get("valore") or "",
                                          f"fonte: {r.get('fonte')}" if r.get("fonte") else "",
                                          str(r.get("data_rilievo") or "")[:10]) if x)
            out.append(f"- {r.get('testo')}" + (f" ({extra})" if extra else ""))
    return out


def documentazione_specialistica(conn, paz_id) -> str:
    """Il testo per la sezione «Documentazione specialistica» della relazione."""
    conf = [r for r in rilievi(conn, paz_id, "confermato") if r.get("fonte") == "documento esterno"]
    if not conf:
        return ""
    return "\n".join(f"- {r.get('testo')}" + (f" ({r.get('autore')}, {str(r.get('data_rilievo') or '')[:10]})"
                                              if r.get("autore") else "") for r in conf)
