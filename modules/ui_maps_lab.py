# -*- coding: utf-8 -*-
"""MAPS-CLEAR Lab nel gestionale, e percorsi fissi su pnev.it.

Lab (solo qui, per i collaboratori): la voce torna in cuffia sempre in ritardo,
e il programma confronta quale ritardo, su quale orecchio e con quale filtro
funziona meglio per il paziente selezionato. Il file sta nel repository
(static/maps_lab/) e non e' pubblicato sul sito.

Percorsi fissi (pnev.it/…/giochi/touch/pnev-ascolto.html): «Impara una lingua
ascoltando la tua voce» e «Leggi meglio ascoltando la tua voce». La pagina non
ha regolazioni: la configurazione la decide il terapista qui e viaggia nel link.
Le sessioni salvate (dal lab o da casa) compaiono in «Giochiamo imparando».
"""
import base64
import json
import os

import streamlit as st
import streamlit.components.v1 as components

from .grafomotricita import db_grafomotricita as db

URL_ASCOLTO = db.BASE_URL + "pnev-ascolto.html"
FILTRI = {"nessuno": "Senza filtro (come MAPS-CLEAR)", "alto": "Passa alto 2000 Hz", "basso": "Passa basso 1000 Hz",
          "banda": "Passa banda 1000–4000 Hz", "lingua": "Banda della lingua (Tomatis)"}
ORECCHIO = {"dominante": "Orecchio dominante", "altro": "L'altro orecchio", "entrambi": "Entrambe"}
LINGUE = {"en": "Inglese", "fr": "Francese", "es": "Spagnolo", "de": "Tedesco"}


def _html_lab():
    for base in ("static", os.path.join(os.path.dirname(__file__), "..", "static")):
        p = os.path.join(base, "maps_lab", "pnev-maps-lab.html")
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                return f.read()
    return ""


def _utente():
    return str(st.session_state.get("utente") or st.session_state.get("username") or "")


def render_maps_lab(conn, paz_id):
    st.subheader("🎧 MAPS-CLEAR Lab")
    st.caption("La voce del paziente torna in cuffia sempre in ritardo. Il Lab confronta quale ritardo, "
               "su quale orecchio e con quale filtro funziona meglio; il percorso a casa usa poi la "
               "configurazione che scegli tu.")
    if conn is None or not paz_id:
        st.info("Seleziona un paziente.")
        return
    try:
        db.init_db(conn)
    except Exception:
        pass
    t1, t2 = st.tabs(["🔬 Lab in studio", "🏠 Percorso a casa (pnev.it)"])

    with t1:
        html = _html_lab()
        if not html:
            st.error("File del Lab non trovato: verifica che static/maps_lab/pnev-maps-lab.html sia su GitHub.")
        else:
            k = "maps_lab_tok_%s" % paz_id
            if k not in st.session_state:
                st.session_state[k] = db.crea_token(conn, paz_id, 2, ["maps_lab"], _utente())
            inj = "<script>window.PNEV_TOKEN=%s;window.PNEV_CTX='studio';</script>" % json.dumps(st.session_state[k])
            components.html(html.replace("<head>", "<head>" + inj, 1), height=1700, scrolling=True)
            st.caption("Cuffie con il filo. Il browser chiede il permesso per il microfono: va concesso. "
                       "«Invia allo studio» apre una scheda che salva la sessione: la trovi in "
                       "«✍️ Giochiamo imparando», insieme al confronto delle condizioni.")

    with t2:
        st.markdown("Il paziente apre una pagina **senza regolazioni**: legge e ascolta con la configurazione "
                    "decisa qui. Il link contiene il codice personale, quindi i risultati arrivano nel fascicolo.")
        c1, c2 = st.columns(2)
        perc = c1.radio("Percorso", ["lettura", "lingua"], key="ml_p_%s" % paz_id,
                        format_func={"lettura": "📖 Leggi meglio ascoltando la tua voce",
                                     "lingua": "🌍 Impara una lingua ascoltando la tua voce"}.get)
        if perc == "lingua":
            lingua = c2.selectbox("Lingua", list(LINGUE), format_func=LINGUE.get, key="ml_lg_%s" % paz_id)
            livello = None
        else:
            lingua = "it"
            livello = c2.selectbox("Testi", ["b", "a"], key="ml_lv_%s" % paz_id,
                                   format_func={"b": "Bambini", "a": "Ragazzi e adulti"}.get)
        c3, c4, c5 = st.columns(3)
        rit = c3.selectbox("Ritardo (ms)", [40, 60, 90, 120], index=1, key="ml_r_%s" % paz_id)
        ore = c4.selectbox("Ritardo su", list(ORECCHIO), format_func=ORECCHIO.get, key="ml_o_%s" % paz_id)
        dirt = c5.selectbox("Altro orecchio", [0, 1], format_func={0: "Silenzio", 1: "Voce senza ritardo"}.get,
                            key="ml_d_%s" % paz_id, disabled=ore == "entrambi")
        c6, c7, c8 = st.columns(3)
        filt = c6.selectbox("Filtro", list(FILTRI), index=4 if perc == "lingua" else 0, format_func=FILTRI.get,
                            key="ml_f_%s_%s" % (paz_id, perc))
        dom = c7.selectbox("Orecchio dominante", ["chiedi", "dx", "sx"], key="ml_dom_%s" % paz_id,
                           format_func={"chiedi": "Lo chiede la pagina", "dx": "Destro", "sx": "Sinistro"}.get)
        minuti = c8.selectbox("Minuti al giorno", [5, 10, 15], index=1, key="ml_m_%s" % paz_id)
        giorni = st.number_input("Link valido per (giorni)", 1, 120, 30, key="ml_g_%s" % paz_id)
        st.caption("Suggerimento: usa la configurazione risultata migliore nel Lab (la trovi nelle sedute di "
                   "«Giochiamo imparando»).")
        if st.button("Genera link per il paziente", type="primary", key="ml_gen_%s" % paz_id):
            cfg = {"percorso": perc, "lingua": lingua, "ritardo": rit, "orecchio": ore,
                   "diretto": 0 if ore == "entrambi" else dirt, "filtro": filt, "minuti": minuti}
            if livello:
                cfg["livello"] = livello
            if dom != "chiedi":
                cfg["dom"] = dom
            p = base64.urlsafe_b64encode(json.dumps(cfg).encode()).decode().rstrip("=")
            tok = db.crea_token(conn, paz_id, int(giorni), ["maps_lab"], _utente())
            st.session_state["ml_link_%s" % paz_id] = "%s?t=%s&p=%s" % (URL_ASCOLTO, tok, p)
        url = st.session_state.get("ml_link_%s" % paz_id)
        if url:
            st.success("Link pronto: mandalo alla famiglia.")
            st.code(url, language=None)
        st.caption("Senza link la pagina funziona lo stesso con le impostazioni standard (ritardo 60 ms "
                   "sull'orecchio dominante), ma i risultati non arrivano allo studio.")
