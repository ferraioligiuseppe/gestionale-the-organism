# -*- coding: utf-8 -*-
"""Stimolazione visiva PNEV a casa.

Si scelgono gli esercizi dell'app di pnev.it (V1–V10), il livello e le
opzioni (filtro colorato per Irlen, colore di quiete, metronomo); il
gestionale crea il link per la famiglia. Il link non contiene dati del
paziente: solo codici, minuti e impostazioni.

Libreria: static/visione/esercizi.json. Tabella: vis_programmi.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import urllib.parse

import streamlit as st

PAGINA = "https://www.pnev.it/wp-content/uploads/visione/esercizi.html"
TEORIA = "https://www.pnev.it/wp-content/uploads/visione/stimolazione-visiva.html"
LIVELLI = {1: "1 · base (bambini piccoli, inizio)", 2: "2 · intermedio", 3: "3 · avanzato / adulti / sport"}
FILTRI = ["", "giallo", "rosa", "azzurro", "verde", "arancio", "lilla", "grigio"]
COLORI = ["verde", "blu", "giallo", "rosso", "viola", "arancio"]


def _cfg(k, d):
    try:
        return (st.secrets.get("visione", {}) or {}).get(k) or d
    except Exception:
        return d


@st.cache_data(show_spinner=False)
def libreria():
    for base in ("static", os.path.join(os.path.dirname(__file__), "..", "static")):
        try:
            with open(os.path.join(base, "visione", "esercizi.json"), encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            continue
    return {"esercizi": []}


def _q(conn, sql, par=()):
    try:
        cur = conn.cursor()
        cur.execute(sql, par)
        r = cur.fetchall() or []
        if r and not isinstance(r[0], dict):
            n = [c[0] for c in cur.description]
            r = [dict(zip(n, x)) for x in r]
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


def _tabella(conn):
    if st.session_state.get("_vis_ok"):
        return
    if not _esegui(conn,
        "CREATE TABLE IF NOT EXISTS vis_programmi ("
        " id SERIAL PRIMARY KEY, paziente_id INTEGER NOT NULL, data_inizio DATE,"
        " esercizi TEXT, impostazioni TEXT, nota_famiglia TEXT, note_cliniche TEXT, link TEXT,"
        " attivo BOOLEAN DEFAULT TRUE, creato_il TIMESTAMP DEFAULT NOW(), creato_da TEXT)"):
        st.session_state["_vis_ok"] = True


def crea_link(esercizi, imp, nota=""):
    q = {"e": ",".join(f"{x['codice']}.{int(x['minuti'])}" for x in esercizi),
         "l": imp["livello"], "v": imp["volte"], "g": imp["giorni"], "s": imp["settimane"]}
    if imp.get("filtro"):
        q["f"] = imp["filtro"]
    if any(x["codice"] == "V9" for x in esercizi):
        q["c"] = imp.get("colore") or "verde"
    if any(x["codice"] == "V10" for x in esercizi):
        q["b"] = imp.get("bpm") or 60
    if imp.get("numeri"):
        q["t"] = "n"
    if nota.strip():
        q["n"] = nota.strip()[:300]
    return _cfg("PAGINA", PAGINA) + "?" + urllib.parse.urlencode(q, quote_via=urllib.parse.quote, safe=",.")


def programma_attivo(conn, paz_id):
    r = _q(conn, "SELECT * FROM vis_programmi WHERE paziente_id=%s AND attivo ORDER BY id DESC LIMIT 1", (int(paz_id),))
    if not r:
        return None
    p = r[0]
    for k in ("esercizi", "impostazioni"):
        try:
            p[k] = json.loads(p.get(k) or ("[]" if k == "esercizi" else "{}"))
        except Exception:
            p[k] = [] if k == "esercizi" else {}
    return p


def render_visione_casa(conn, paz_id):
    st.subheader("👁️ Stimolazione visiva a casa")
    st.caption("Esercizi dell'app PNEV su pnev.it. Scegli quali, per quanti minuti e con quali impostazioni: "
               "la famiglia riceve un link con solo quelli. "
               f"[Che cos'è, per genitori e colleghi]({_cfg('TEORIA', TEORIA)})")
    lib = libreria()
    if not lib.get("esercizi"):
        st.error("Libreria non trovata: caricare static/visione/esercizi.json")
        return
    if conn is None or not paz_id:
        st.info("Seleziona un paziente.")
        return
    _tabella(conn)
    prog = programma_attivo(conn, paz_id)
    imp0 = (prog or {}).get("impostazioni") or {}
    scelti = {x["codice"]: x for x in (prog or {}).get("esercizi", [])}
    t1, t2, t3 = st.tabs(["🧒 Programma per casa", "📈 Storico", "📚 Libreria"])

    with t1:
        if prog:
            st.info(f"Programma in corso dal {prog['data_inizio']:%d/%m/%Y} · {len(prog['esercizi'])} esercizi · "
                    f"livello {imp0.get('livello', 1)}")
        k = f"vis_{paz_id}"
        nuovi = []
        for e in lib["esercizi"]:
            c = e["codice"]
            a, b = st.columns([5, 1.3])
            on = a.checkbox(f"**{c}** · {e['nome']} — {e['area']}", value=c in scelti, key=f"{k}_on_{c}",
                            help=e.get("clinica"))
            m = b.number_input("min", 1, 15, int((scelti.get(c) or {}).get("minuti") or e["minuti_default"]),
                               key=f"{k}_m_{c}", label_visibility="collapsed", disabled=not on)
            if on:
                nuovi.append({"codice": c, "minuti": int(m)})
        st.markdown("**Impostazioni**")
        c1, c2, c3 = st.columns(3)
        liv = c1.selectbox("Livello", list(LIVELLI), format_func=LIVELLI.get,
                           index=list(LIVELLI).index(int(imp0.get("livello") or 1)), key=f"{k}_liv")
        filt = c2.selectbox("Filtro colorato (Irlen) su V2, V3, V5", FILTRI,
                            index=FILTRI.index(imp0.get("filtro") or ""), key=f"{k}_f",
                            format_func=lambda x: x or "nessuno",
                            help="Solo se in studio un colore ha migliorato la lettura in modo chiaro e ripetibile.")
        num = c3.checkbox("Tabella V3 con numeri invece di lettere", value=bool(imp0.get("numeri")), key=f"{k}_num")
        c4, c5 = st.columns(2)
        col = c4.selectbox("Colore di quiete (V9)", COLORI, index=COLORI.index(imp0.get("colore") or "verde"),
                           key=f"{k}_col", disabled="V9" not in [x["codice"] for x in nuovi])
        bpm = c5.number_input("Metronomo V10 (battiti/min)", 30, 120, int(imp0.get("bpm") or 60), step=5,
                              key=f"{k}_bpm", disabled="V10" not in [x["codice"] for x in nuovi])
        d1, d2, d3 = st.columns(3)
        volte = d1.number_input("Volte al giorno", 1, 3, int(imp0.get("volte") or 1), key=f"{k}_v")
        giorni = d2.number_input("Giorni a settimana", 1, 7, int(imp0.get("giorni") or 5), key=f"{k}_g")
        sett = d3.number_input("Settimane", 1, 26, int(imp0.get("settimane") or 4), key=f"{k}_s")
        nota = st.text_area("Nota per la famiglia (facoltativa)", (prog or {}).get("nota_famiglia") or "",
                            key=f"{k}_nota", height=70)
        ncl = st.text_area("Note cliniche (non vanno alla famiglia)", (prog or {}).get("note_cliniche") or "",
                           key=f"{k}_ncl", height=70)
        if "V4" in [x["codice"] for x in nuovi]:
            st.caption("V4 richiede la cordicella di Brock: consegnala in studio.")
        if "V5" in [x["codice"] for x in nuovi]:
            st.caption("V5 richiede la tabella di lettura stampata, da appendere a 3 metri.")
        if st.button("💾 Salva il programma e crea il link", type="primary", key=f"{k}_salva", disabled=not nuovi):
            imp = {"livello": int(liv), "filtro": filt, "numeri": bool(num), "colore": col, "bpm": int(bpm),
                   "volte": int(volte), "giorni": int(giorni), "settimane": int(sett)}
            link = crea_link(nuovi, imp, nota)
            _esegui(conn, "UPDATE vis_programmi SET attivo=FALSE WHERE paziente_id=%s AND attivo", (int(paz_id),))
            err = _esegui(conn,
                "INSERT INTO vis_programmi (paziente_id, data_inizio, esercizi, impostazioni, nota_famiglia, "
                "note_cliniche, link, attivo, creato_da) VALUES (%s,%s,%s,%s,%s,%s,%s,TRUE,%s)",
                (int(paz_id), dt.date.today(), json.dumps(nuovi), json.dumps(imp), nota.strip(), ncl.strip(), link,
                 str(st.session_state.get("username") or "")))
            if err:
                st.error(f"Non salvato: {err}")
            else:
                st.success("Programma salvato.")
                st.rerun()
        if prog and prog.get("link"):
            st.markdown("---")
            st.markdown("**🔗 Link per la famiglia**")
            st.code(prog["link"], language=None)
            a, b, c = st.columns(3)
            a.link_button("Apri / prova", prog["link"], use_container_width=True)
            msg = urllib.parse.quote("Ecco gli esercizi per gli occhi da fare a casa: " + prog["link"])
            b.link_button("WhatsApp", f"https://wa.me/?text={msg}", use_container_width=True)
            mail = c.text_input("Email", key=f"{k}_mail", label_visibility="collapsed", placeholder="email")
            if c.button("📧 Invia", key=f"{k}_inv", use_container_width=True):
                try:
                    from modules.email_otp import invia_email
                    ok, mot = invia_email(mail.strip(), "Esercizi visivi a casa — Studio The Organism",
                                          "Gentile famiglia,\n\nqui trovate gli esercizi visivi da fare a casa:\n\n"
                                          + prog["link"] + "\n\nStudio The Organism · www.pnev.it", dettaglio=True)
                    (st.success if ok else st.error)(mot)
                except Exception as e:
                    st.error(f"Email non disponibile: {e}")
            st.caption("I risultati restano sul dispositivo della famiglia: dalla pagina possono copiarli e "
                       "mandarveli con «Copia i risultati per il terapista».")

    with t2:
        righe = _q(conn, "SELECT * FROM vis_programmi WHERE paziente_id=%s ORDER BY id DESC", (int(paz_id),))
        if not righe:
            st.info("Nessun programma per questo paziente.")
        for p in righe:
            try:
                es = json.loads(p.get("esercizi") or "[]")
                im = json.loads(p.get("impostazioni") or "{}")
            except Exception:
                es, im = [], {}
            st.markdown(f"- {'🟢' if p.get('attivo') else '⚪'} dal {p['data_inizio']:%d/%m/%Y} · livello {im.get('livello', 1)}"
                        + (f" · filtro {im['filtro']}" if im.get("filtro") else "") + " · "
                        + ", ".join(f"{x['codice']} {x['minuti']}′" for x in es))

    with t3:
        for e in lib["esercizi"]:
            with st.expander(f"{e['codice']} · {e['nome']} — {e['area']}"):
                st.markdown(f"**Esecuzione:** {e.get('clinica')}")
                st.markdown(f"**Cosa osservare:** {e.get('osservare')}")


def sintesi_visione(conn, paz_id) -> list[str]:
    p = programma_attivo(conn, paz_id) if conn and paz_id else None
    if not p:
        return []
    return ["Stimolazione visiva a casa dal " + p["data_inizio"].strftime("%d/%m/%Y") + ": "
            + ", ".join(f"{x['codice']} {x['minuti']}′" for x in p["esercizi"])]
