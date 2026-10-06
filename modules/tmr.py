# -*- coding: utf-8 -*-
"""TMR — Training dei Movimenti Ritmici (H. Blomberg), rielaborazione Studio The Organism.

Quattro schede sul paziente:
  · 🧒 Programma per casa — si spuntano gli esercizi ATTIVI, con cicli e frequenza;
    nasce il link per la famiglia (pnev.it), che mostra solo quelli scelti.
  · 🏥 Seduta in studio — esercizi PASSIVI e attivi, con esito e reazioni.
  · 📈 Storico — programmi e sedute del paziente.
  · 📚 Libreria — le schede cliniche di tutti gli esercizi, con il video.

La libreria sta in static/tmr/tmr_esercizi.json: per correggere un testo o
aggiungere un esercizio si modifica quel file, non questo.

Il link per la famiglia NON contiene dati del paziente: solo codici degli
esercizi, cicli e frequenza. Si puo' mandare su WhatsApp senza problemi di privacy.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import urllib.parse

import streamlit as st

PAGINA_FAMIGLIA = "https://www.pnev.it/wp-content/uploads/tmr/tmr-genitori.html"
CARTELLA_VIDEO = "https://www.pnev.it/wp-content/uploads/tmr/"
PAGINA_TEORIA = "https://www.pnev.it/wp-content/uploads/tmr/tmr-teoria.html"

ESITI = ["", "fluido e ritmico", "con aiuto", "ritmo irregolare", "non eseguito"]
REAZIONI = ["tremore", "sbadigli", "respiro trattenuto", "irrequietezza", "pianto / rifiuto",
            "rilassamento", "sonnolenza", "rossore / calore"]


def _cfg(k, default):
    try:
        return (st.secrets.get("tmr", {}) or {}).get(k) or default
    except Exception:
        return default


# ── libreria ──────────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def libreria() -> dict:
    for base in ("static", os.path.join(os.path.dirname(__file__), "..", "static")):
        p = os.path.join(base, "tmr", "tmr_esercizi.json")
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            continue
    return {"esercizi": [], "note": "libreria non trovata: caricare static/tmr/tmr_esercizi.json"}


def _secondi(t):
    try:
        mm, ss = str(t).split(":")
        return int(mm) * 60 + int(ss)
    except Exception:
        return None


def url_video(e) -> str:
    f = e.get("video_file")
    if not f:
        return ""
    u = _cfg("VIDEO_BASE_URL", CARTELLA_VIDEO).rstrip("/") + "/" + urllib.parse.quote(f)
    a, b = _secondi(e.get("video_inizio")), _secondi(e.get("video_fine"))
    if a is not None:
        u += f"#t={a}" + (f",{b}" if b is not None else "")
    return u


# ── database ──────────────────────────────────────────────────────────

def _tabelle(conn):
    if st.session_state.get("_tmr_ok"):
        return
    try:
        cur = conn.cursor()
        cur.execute(
            "CREATE TABLE IF NOT EXISTS tmr_programmi ("
            " id SERIAL PRIMARY KEY, paziente_id INTEGER NOT NULL,"
            " data_inizio DATE, esercizi TEXT, volte_giorno INTEGER, giorni_settimana INTEGER,"
            " settimane INTEGER, nota_famiglia TEXT, note_cliniche TEXT, link TEXT,"
            " attivo BOOLEAN DEFAULT TRUE, creato_il TIMESTAMP DEFAULT NOW(), creato_da TEXT)")
        cur.execute(
            "CREATE TABLE IF NOT EXISTS tmr_sedute ("
            " id SERIAL PRIMARY KEY, paziente_id INTEGER NOT NULL, data DATE,"
            " esercizi TEXT, reazioni TEXT, osservazioni TEXT,"
            " creato_il TIMESTAMP DEFAULT NOW(), creato_da TEXT)")
        cur.execute("CREATE INDEX IF NOT EXISTS tmr_prog_paz ON tmr_programmi (paziente_id, attivo)")
        cur.execute("CREATE INDEX IF NOT EXISTS tmr_sed_paz ON tmr_sedute (paziente_id, data)")
        conn.commit()
        st.session_state["_tmr_ok"] = True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass


def _q(conn, sql, par=()):
    try:
        cur = conn.cursor()
        cur.execute(sql, par)
        r = cur.fetchall() or []
        if r and not isinstance(r[0], dict):
            nomi = [c[0] for c in cur.description]
            r = [dict(zip(nomi, x)) for x in r]
        return r
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return []


def _esegui(conn, sql, par=()):
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


def programma_attivo(conn, paz_id):
    r = _q(conn, "SELECT * FROM tmr_programmi WHERE paziente_id=%s AND attivo ORDER BY id DESC LIMIT 1",
           (int(paz_id),))
    if not r:
        return None
    p = r[0]
    try:
        p["esercizi"] = json.loads(p.get("esercizi") or "[]")
    except Exception:
        p["esercizi"] = []
    return p


# ── link per la famiglia ──────────────────────────────────────────────

def crea_link(esercizi, volte, giorni, settimane, nota="") -> str:
    """?e=A1.20,A2b.20&v=2&g=5&s=4 — nessun dato del paziente."""
    parti = [f"{x['codice']}{x.get('variante') or ''}.{int(x.get('cicli') or 20)}" for x in esercizi]
    q = {"e": ",".join(parti), "v": volte, "g": giorni, "s": settimane}
    if nota.strip():
        q["n"] = nota.strip()[:300]
    base = _cfg("PAGINA_FAMIGLIA", PAGINA_FAMIGLIA)
    return base + "?" + urllib.parse.urlencode(q, quote_via=urllib.parse.quote, safe=",.")


# ── schede ────────────────────────────────────────────────────────────

def _scheda_clinica(e):
    st.markdown(f"**Posizione:** {e.get('posizione') or '—'}  \n"
                f"**Punto di spinta:** {e.get('punto_spinta') or '—'} · **Direzione:** {e.get('direzione') or '—'}")
    st.markdown(f"**Esecuzione:** {e.get('esecuzione_clinica') or '—'}")
    if e.get("errori_tipici"):
        st.markdown(f"**Errori tipici:** {e['errori_tipici']}")
    if e.get("aiuti_operatore"):
        st.markdown(f"**Aiuti dell'operatore:** {e['aiuti_operatore']}")
    if e.get("riflesso"):
        st.markdown(f"**Riflesso:** {e['riflesso']}")
    if e.get("animazione"):
        st.markdown(f"[🎬 Animazione e approfondimento del riflesso]"
                    f"(https://www.pnev.it/wp-content/uploads/riflessi/{e['animazione']})")
    if e.get("tenuta_secondi") or e.get("ripetizioni"):
        st.markdown(f"**Dose:** pressione {e.get('tenuta_secondi') or '—'} s"
                    + (f" al {e['forza']} della forza" if e.get("forza") else "")
                    + f", {e.get('ripetizioni') or '—'} ripetizioni"
                    + (f" · {e['frequenza']}" if e.get("frequenza") else ""))
    if e.get("testo_famiglia"):
        st.caption(f"Testo per la famiglia: «{e['testo_famiglia']}»")
    if e.get("da_validare"):
        st.warning("Scheda da validare: testo ricostruito dal video, da verificare in studio.")
    v = url_video(e)
    if v:
        st.markdown(f"[▶ Video dell'esercizio]({v})")


def _tab_programma(conn, paz_id, lib):
    attivi = [e for e in lib["esercizi"] if e.get("assegnabile_casa")]
    prog = programma_attivo(conn, paz_id)
    scelti = {x["codice"]: x for x in (prog or {}).get("esercizi", [])}
    if prog:
        st.info(f"Programma in corso dal {prog['data_inizio']:%d/%m/%Y} · "
                f"{len(prog['esercizi'])} esercizi · {prog.get('volte_giorno') or 1} volta/e al giorno, "
                f"{prog.get('giorni_settimana') or 5} giorni a settimana")
    st.caption("Spunta solo gli esercizi da fare a casa. Le famiglie vedranno questi, nell'ordine "
               "dell'elenco, con i cicli che indichi. I passivi si fanno solo in studio.")
    k = f"tmr_{paz_id}"
    nuovi = []
    for e in attivi:
        c = e["codice"]
        prima = scelti.get(c)
        cols = st.columns([4, 1.2, 1.4])
        on = cols[0].checkbox(f"**{c}** · {e['nome']}", value=bool(prima), key=f"{k}_on_{c}",
                              help=e.get("testo_famiglia") or "")
        cicli = cols[1].number_input("Cicli", 5, 200, int((prima or {}).get("cicli") or e.get("cicli_default") or 20),
                                     step=5, key=f"{k}_ci_{c}", label_visibility="collapsed",
                                     disabled=not on)
        var = ""
        if c == "A2":
            opz = {"a": "a · con le mani", "b": "b · punte dei piedi, gambe tese", "c": "c · braccia lungo i fianchi"}
            var = cols[2].selectbox("Variante", list(opz), format_func=opz.get,
                                    index=list(opz).index((prima or {}).get("variante") or "a"),
                                    key=f"{k}_var_{c}", label_visibility="collapsed", disabled=not on)
        else:
            cols[2].caption("cicli")
        if on:
            nuovi.append({"codice": c, "cicli": int(cicli), "variante": var})
    a, b, c3 = st.columns(3)
    volte = a.number_input("Volte al giorno", 1, 3, int((prog or {}).get("volte_giorno") or 1), key=f"{k}_v")
    giorni = b.number_input("Giorni a settimana", 1, 7, int((prog or {}).get("giorni_settimana") or 5), key=f"{k}_g")
    sett = c3.number_input("Per quante settimane", 1, 26, int((prog or {}).get("settimane") or 4), key=f"{k}_s")
    nota = st.text_area("Nota per la famiglia (facoltativa, compare in cima alla pagina)",
                        value=(prog or {}).get("nota_famiglia") or "", key=f"{k}_nota", height=70,
                        placeholder="es. Fatelo dopo il bagno, prima della storia della sera.")
    note_cl = st.text_area("Note cliniche (non vanno alla famiglia)",
                           value=(prog or {}).get("note_cliniche") or "", key=f"{k}_ncl", height=70)

    if st.button("💾 Salva il programma e crea il link", type="primary", key=f"{k}_salva",
                 disabled=not nuovi):
        link = crea_link(nuovi, volte, giorni, sett, nota)
        _esegui(conn, "UPDATE tmr_programmi SET attivo=FALSE WHERE paziente_id=%s AND attivo", (int(paz_id),))
        err = _esegui(conn,
            "INSERT INTO tmr_programmi (paziente_id, data_inizio, esercizi, volte_giorno, giorni_settimana, "
            "settimane, nota_famiglia, note_cliniche, link, attivo, creato_da) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,TRUE,%s)",
            (int(paz_id), dt.date.today(), json.dumps(nuovi), int(volte), int(giorni), int(sett),
             nota.strip(), note_cl.strip(), link, _utente()))
        if err:
            st.error(f"Non salvato: {err}")
        else:
            st.success("Programma salvato.")
            st.rerun()
    if not nuovi:
        st.caption("Spunta almeno un esercizio.")

    if prog and prog.get("link"):
        st.markdown("---")
        st.markdown("**🔗 Pagina per la famiglia**")
        st.code(prog["link"], language=None)
        c1, c2, c3 = st.columns(3)
        c1.link_button("Apri / stampa", prog["link"], use_container_width=True)
        msg = urllib.parse.quote("Ecco gli esercizi di movimento ritmico da fare a casa: " + prog["link"])
        c2.link_button("WhatsApp", f"https://wa.me/?text={msg}", use_container_width=True)
        mail = c3.text_input("Email", key=f"{k}_mail", label_visibility="collapsed", placeholder="email genitore")
        if c3.button("📧 Invia", key=f"{k}_invia", use_container_width=True):
            try:
                from modules.email_otp import invia_email
                ok, mot = invia_email(mail.strip(), "Movimenti ritmici a casa — Studio The Organism",
                                      "Gentile famiglia,\n\nqui trovate gli esercizi di movimento ritmico da fare a casa, "
                                      "con i video e le indicazioni:\n\n" + prog["link"] +
                                      "\n\nDalla stessa pagina potete stamparli.\n\nStudio The Organism · www.pnev.it",
                                      dettaglio=True)
                (st.success if ok else st.error)(mot)
            except Exception as e:
                st.error(f"Email non disponibile: {e}")


def _tab_seduta(conn, paz_id, lib):
    k = f"tmrs_{paz_id}"
    data = st.date_input("Data della seduta", dt.date.today(), key=f"{k}_d", format="DD/MM/YYYY")
    righe = []
    for gruppo, filtro in (("Passivi · solo in studio", "passivo"), ("Isometrici · in studio", "isometrico"),
                           ("Attivi", "attivo")):
        gruppo_es = [x for x in lib["esercizi"] if x.get("modalita") == filtro]
        if not gruppo_es:
            continue
        st.markdown(f"**{gruppo}**")
        for e in gruppo_es:
            c = e["codice"]
            cols = st.columns([3.4, 1.1, 2])
            on = cols[0].checkbox(f"{c} · {e['nome']}" + (" ⚠️" if e.get("da_validare") else ""),
                                  key=f"{k}_on_{c}")
            if not on:
                continue
            ci = cols[1].number_input("Cicli", 1, 200, int(e.get("cicli_default") or 20), key=f"{k}_ci_{c}",
                                      label_visibility="collapsed")
            es = cols[2].selectbox("Esito", ESITI, key=f"{k}_es_{c}", label_visibility="collapsed",
                                   format_func=lambda x: x or "esito…")
            with st.expander(f"Scheda {c}", expanded=False):
                _scheda_clinica(e)
            oss = st.text_input(f"Osservazioni {c}", key=f"{k}_os_{c}", label_visibility="collapsed",
                                placeholder=f"Osservazioni su {c} (es. {e.get('errori_tipici') or ''})")
            righe.append({"codice": c, "cicli": int(ci), "esito": es, "osservazioni": oss.strip()})
    reaz = st.multiselect("Reazioni osservate durante o dopo", REAZIONI, key=f"{k}_rz",
                          placeholder="Scegli una o più voci")
    oss_g = st.text_area("Osservazioni generali", key=f"{k}_og", height=80)
    if st.button("💾 Salva la seduta", type="primary", key=f"{k}_salva", disabled=not righe):
        err = _esegui(conn,
            "INSERT INTO tmr_sedute (paziente_id, data, esercizi, reazioni, osservazioni, creato_da) "
            "VALUES (%s,%s,%s,%s,%s,%s)",
            (int(paz_id), data, json.dumps(righe), json.dumps(reaz), oss_g.strip(), _utente()))
        if err:
            st.error(f"Non salvata: {err}")
        else:
            for x in list(st.session_state):
                if x.startswith(k + "_"):
                    st.session_state.pop(x, None)
            st.success("Seduta salvata.")
            st.rerun()


def _tab_storico(conn, paz_id, lib):
    nomi = {e["codice"]: e["nome"] for e in lib["esercizi"]}
    sed = _q(conn, "SELECT * FROM tmr_sedute WHERE paziente_id=%s ORDER BY data DESC, id DESC", (int(paz_id),))
    prog = _q(conn, "SELECT * FROM tmr_programmi WHERE paziente_id=%s ORDER BY id DESC", (int(paz_id),))
    c1, c2 = st.columns(2)
    c1.metric("Sedute in studio", len(sed))
    c2.metric("Programmi per casa", len(prog))
    if sed:
        st.markdown("**Sedute**")
        for s in sed:
            try:
                es = json.loads(s.get("esercizi") or "[]")
                rz = json.loads(s.get("reazioni") or "[]")
            except Exception:
                es, rz = [], []
            with st.expander(f"{s['data']:%d/%m/%Y} · {len(es)} esercizi" + (f" · {', '.join(rz)}" if rz else "")):
                for x in es:
                    st.markdown(f"- **{x['codice']}** {nomi.get(x['codice'], '')} · {x.get('cicli')} cicli"
                                + (f" · {x['esito']}" if x.get("esito") else "")
                                + (f"  \n  {x['osservazioni']}" if x.get("osservazioni") else ""))
                if s.get("osservazioni"):
                    st.caption(s["osservazioni"])
    if prog:
        st.markdown("**Programmi per casa**")
        for p in prog:
            try:
                es = json.loads(p.get("esercizi") or "[]")
            except Exception:
                es = []
            st.markdown(f"- {'🟢' if p.get('attivo') else '⚪'} dal {p['data_inizio']:%d/%m/%Y} · "
                        + ", ".join(f"{x['codice']}{x.get('variante') or ''} ×{x['cicli']}" for x in es)
                        + f" · {p.get('giorni_settimana')} gg/sett per {p.get('settimane')} sett.")
    if not sed and not prog:
        st.info("Ancora niente per questo paziente.")


def _tab_libreria(lib):
    st.caption(f"{lib.get('libreria', '')} · fonte: {lib.get('fonte', '')} · versione {lib.get('versione', '')}")
    if lib.get("note"):
        st.info(lib["note"])
    st.markdown(f"📖 [Le basi teoriche del TMR, per genitori e professionisti]({_cfg('PAGINA_TEORIA', PAGINA_TEORIA)})")
    for gruppo, filtro in (("Passivi · eseguiti dall'operatore", "passivo"),
                           ("Isometrici · pressioni nella posizione del riflesso", "isometrico"),
                           ("Attivi · assegnabili a casa", "attivo")):
        gruppo_es = [x for x in lib["esercizi"] if x.get("modalita") == filtro]
        if not gruppo_es:
            continue
        st.markdown(f"#### {gruppo}")
        for e in gruppo_es:
            with st.expander(f"{e['codice']} · {e['nome']}" + (" ⚠️ da validare" if e.get("da_validare") else "")):
                _scheda_clinica(e)


def render_tmr(conn, paz_id):
    st.subheader("🎵 TMR — Movimenti ritmici")
    lib = libreria()
    if not lib.get("esercizi"):
        st.error(lib.get("note") or "Libreria TMR vuota.")
        return
    if conn is None or not paz_id:
        _tab_libreria(lib)
        return
    _tabelle(conn)
    t1, t2, t3, t4 = st.tabs(["🧒 Programma per casa", "🏥 Seduta in studio", "📈 Storico", "📚 Libreria"])
    with t1:
        _tab_programma(conn, paz_id, lib)
    with t2:
        _tab_seduta(conn, paz_id, lib)
    with t3:
        _tab_storico(conn, paz_id, lib)
    with t4:
        _tab_libreria(lib)


def sintesi_tmr(conn, paz_id) -> list[str]:
    """Per relazione e diagnosi assistita."""
    if conn is None or not paz_id:
        return []
    out = []
    p = programma_attivo(conn, paz_id)
    if p:
        out.append("TMR — programma per casa in corso dal " + p["data_inizio"].strftime("%d/%m/%Y") + ": "
                   + ", ".join(f"{x['codice']}{x.get('variante') or ''} ×{x['cicli']}" for x in p["esercizi"]))
    n = _q(conn, "SELECT COUNT(*) AS n FROM tmr_sedute WHERE paziente_id=%s", (int(paz_id),))
    if n and n[0].get("n"):
        out.append(f"TMR — sedute in studio registrate: {n[0]['n']}")
    return out
