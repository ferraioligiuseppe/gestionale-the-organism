"""
Modulo Grafomotricità e prove touch — interfaccia
Studio The Organism · www.pnev.it

render_grafomotricita(conn, paziente_id, paziente_nome)  → scheda nel gestionale (paziente attivo)
azione_touch(conn)                                       → pagina pubblica di salvataggio
                                                           (?azione=touch&t=TOKEN&d=DATI), da chiamare
                                                           dal router di apps/pnev_pubblico.py
"""
import json

import pandas as pd
import streamlit as st

from modules.grafomotricita import db_grafomotricita as db

VERDE = "#1D6B44"
NOTA_CLINICA = ("Misure grezze del comportamento grafomotorio e cognitivo. Non sono una diagnosi: "
                "vanno lette insieme alla valutazione clinica e ai test standardizzati. "
                "Il confronto con i coetanei sarà disponibile quando ci saranno norme per età.")


def _fmt_data(d):
    return d.strftime("%d/%m/%Y %H:%M") if d else "—"


def _riga_sintesi(s):
    sint = s.get("sintesi") or {}
    corte = []
    for k, v in sint.items():
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            corte.append("%s %s" % (k.replace("_", " "), v))
    return ", ".join(corte[:4])


def render_grafomotricita(conn, paziente_id, paziente_nome=""):
    if not paziente_id:
        st.info("Seleziona un paziente.")
        return
    db.init_db(conn)
    st.subheader("Grafomotricità e prove touch")
    if paziente_nome:
        st.caption(paziente_nome)
    t_assegna, t_sedute, t_andamento, t_importa = st.tabs(["Assegna", "Sedute", "Andamento", "Importa file"])

    # ── Assegna ──────────────────────────────────────────────────────────────
    with t_assegna:
        st.markdown("Scegli le prove e genera il link personale. Il bambino le svolge a casa o in studio; "
                    "ogni sessione arriva qui con il token.")
        scelte = st.multiselect(
            "Prove", options=[k for k in db.CATALOGO if k != "maps_lab"],
            default=[k for k in db.CATALOGO if not k.startswith(("lettura_", "maps_"))],
            format_func=lambda k: "%s (%s)" % (db.CATALOGO[k]["nome"], db.CATALOGO[k]["area"]))
        giorni = st.select_slider("Validità del link", options=[7, 14, 30, 60, 90], value=30,
                                  format_func=lambda g: "%d giorni" % g)
        if st.button("Genera link", type="primary", disabled=not scelte):
            tok = db.crea_token(conn, paziente_id, giorni, scelte, st.session_state.get("utente", ""))
            st.session_state["grafo_ultimo_token"] = (tok, scelte)
        ult = st.session_state.get("grafo_ultimo_token")
        if ult:
            tok, sc = ult
            st.success("Codice: %s" % tok)
            for k in sc:
                st.markdown("**%s**, a casa" % db.CATALOGO[k]["nome"])
                _l = db.link_prova(k, tok, "casa")
                st.code(_l, language=None)
                st.caption("In studio: " + db.link_prova(k, tok, "studio"))
        toks = db.token_paziente(conn, paziente_id)
        if toks:
            with st.expander("Link già generati"):
                for t in toks:
                    c1, c2 = st.columns([4, 1])
                    stato = "attivo" if t["attivo"] else "disattivato"
                    c1.write("%s, prove: %s, scade il %s (%s)" % (t["token"], t["compiti"] or "tutte",
                                                                 _fmt_data(t["scadenza"]), stato))
                    if t["attivo"] and c2.button("Disattiva", key="dis_%d" % t["id"]):
                        db.disattiva_token(conn, t["id"])
                        st.rerun()

    sessioni = db.sessioni_paziente(conn, paziente_id)

    # ── Sedute ───────────────────────────────────────────────────────────────
    with t_sedute:
        if not sessioni:
            st.info("Nessuna sessione registrata. Genera un link nella scheda Assegna oppure importa un file.")
        else:
            tab = pd.DataFrame([{
                "Data": _fmt_data(s["avvio"]), "Prova": db.CATALOGO.get(s["task"], {}).get("nome", s["task"]),
                "Contesto": s["contesto"] or "", "Input": s["input_tipo"] or "",
                "Calibrato": "sì" if s["calibrato"] else "no", "Sintesi": _riga_sintesi(s), "id": s["id"],
            } for s in sessioni])
            st.dataframe(tab.drop(columns=["id"]), hide_index=True, width="stretch")
            idx = st.selectbox("Dettaglio", options=range(len(sessioni)),
                               format_func=lambda i: "%s, %s" % (tab.iloc[i]["Data"], tab.iloc[i]["Prova"]))
            s = sessioni[idx]
            st.markdown("**Sintesi**")
            _sz = s["sintesi"] or {}
            if _sz.get("condizioni"):
                st.markdown("**MAPS-CLEAR Lab — confronto delle condizioni**")
                _m = _sz.get("migliore") or {}
                _ch = {"chiara": "differenza chiara", "piccola": "differenza piccola: ripetere un altro giorno",
                       "nessuna": "nessuna configurazione è risultata migliore della lettura senza voce in cuffia"}.get(_sz.get("chiarezza"), "")
                st.markdown("Proposta: **%s** · %s" % (_m.get("nome", "—"), _ch))
                st.dataframe([{"Condizione": c.get("nome"), "Sillabe/s": c.get("sill_s"), "Errori/100": c.get("err100"),
                               "Pause %": c.get("pause_pct"), "Reazione ms": c.get("rt_ms"), "Mancati": c.get("mancati"),
                               "Comprensione %": c.get("comprensione_pct"), "Comfort": c.get("comfort"), "Punti": c.get("punteggio")}
                              for c in sorted(_sz["condizioni"], key=lambda c: c.get("punteggio") or 0)],
                             use_container_width=True, hide_index=True)
                if _sz.get("latenza_ms") and _sz["latenza_ms"] > 40:
                    st.warning("Latenza audio %s ms: probabilmente cuffie Bluetooth, misure poco affidabili." % _sz["latenza_ms"])
            _voce = _sz.get("voce") or {}
            if _voce.get("parole_maps_clear") or _voce.get("coppie_suoni"):
                st.markdown("**Per MAPS**")
                if _voce.get("parole_maps_clear"):
                    st.markdown("Parole da allenare in MAPS CLEAR: " + ", ".join(_voce["parole_maps_clear"]))
                    st.code("\n".join(_voce["parole_maps_clear"]), language=None)
                if _voce.get("coppie_suoni"):
                    st.markdown("Suoni scambiati: " + ", ".join("%s (%s)" % (k, v) for k, v in _voce["coppie_suoni"].items()))
                for x in _voce.get("suggerimento_maps") or []:
                    st.markdown("- Da considerare per la stimolazione uditiva: " + x)
                if _voce.get("accordo_voce_adulto_pct") is not None:
                    st.caption("Accordo tra riconoscimento vocale e adulto: %s%%" % _voce["accordo_voce_adulto_pct"])
                st.caption("Indicazioni da confermare in seduta, non una diagnosi.")
            st.json(s["sintesi"] or {}, expanded=False)
            prove = s["prove"] or []
            if prove:
                st.markdown("**Prove**")
                st.dataframe(pd.DataFrame([{k: v for k, v in p.items() if not isinstance(v, (dict, list))} for p in prove]),
                             hide_index=True, width="stretch")
                kin = [dict(prova=p.get("n"), **p["cinematica"]) for p in prove if p.get("cinematica")]
                if kin:
                    st.markdown("**Profilo cinematico**")
                    st.dataframe(pd.DataFrame(kin), hide_index=True, width="stretch")
            disp = s["dispositivo"] or {}
            st.caption("Dispositivo: input %s, schermo %s, calibrazione %s. %s" % (
                disp.get("input", "n.d."), disp.get("schermo"), "sì" if disp.get("calibrato") else "no (mm stimati)",
                "Confronta le sedute fatte con lo stesso tipo di input." if not disp.get("calibrato") else ""))
            c1, c2 = st.columns(2)
            c1.download_button("Scarica JSON", data=json.dumps(s, default=str, ensure_ascii=False),
                               file_name="grafo_%d.json" % s["id"], mime="application/json")
            if c2.button("Elimina questa sessione", key="del_%d" % s["id"]):
                st.session_state["grafo_conferma_del"] = s["id"]
            if st.session_state.get("grafo_conferma_del") == s["id"]:
                st.warning("Confermi l'eliminazione definitiva?")
                if st.button("Sì, elimina", key="delok_%d" % s["id"]):
                    db.elimina_sessione(conn, s["id"], paziente_id)
                    st.session_state.pop("grafo_conferma_del", None)
                    st.rerun()
        st.caption(NOTA_CLINICA)

    # ── Andamento ────────────────────────────────────────────────────────────
    with t_andamento:
        tasks = sorted({s["task"] for s in sessioni if s["task"] in db.CATALOGO})
        if not tasks:
            st.info("L'andamento compare dopo le prime sessioni.")
        else:
            task = st.selectbox("Prova", tasks, format_func=lambda k: db.CATALOGO[k]["nome"])
            metr = db.CATALOGO[task]["metriche"]
            m = st.selectbox("Misura", range(len(metr)), format_func=lambda i: metr[i][1])
            perc, etich, meglio = metr[m]
            solo_input = st.checkbox("Solo sedute con lo stesso tipo di input dell'ultima", value=True)
            ss = [s for s in sessioni if s["task"] == task]
            if solo_input and ss:
                ss = [s for s in ss if s["input_tipo"] == ss[0]["input_tipo"]]
            punti = [(s["avvio"], db.valore_metrica(s, perc)) for s in reversed(ss)]
            punti = [(d, v) for d, v in punti if d and v is not None]
            if len(punti) < 2:
                st.info("Servono almeno due sedute con questa misura.")
            else:
                df = pd.DataFrame(punti, columns=["Data", etich]).set_index("Data")
                st.line_chart(df, color=VERDE)
                if meglio:
                    st.caption("Per questa misura il miglioramento è verso valori più %s." % ("alti" if meglio == "su" else "bassi"))

    # ── Importa ──────────────────────────────────────────────────────────────
    with t_importa:
        st.markdown("Per le prove fatte in studio senza link: sul dispositivo usa «Salva file sessione» e carica qui il file.")
        files = st.file_uploader("File sessione (.json)", type=["json"], accept_multiple_files=True)
        if files and st.button("Importa", type="primary"):
            for f in files:
                try:
                    sid, nuovo = db.salva_sessione(conn, paziente_id, json.loads(f.getvalue().decode("utf-8")), contesto="studio")
                    st.success("%s: %s" % (f.name, "importato" if nuovo else "già presente"))
                except (ValueError, json.JSONDecodeError) as e:
                    st.error("%s: %s" % (f.name, e))


def azione_touch(conn):
    """Pagina pubblica: riceve ?azione=touch&t=TOKEN&d=DATI, salva e conferma."""
    qp = st.query_params
    st.markdown("<h3 style='color:%s'>Studio The Organism</h3>" % VERDE, unsafe_allow_html=True)
    rec = db.verifica_token(conn, qp.get("t", ""))
    if not rec:
        st.error("Link non valido o scaduto. Chiedi allo studio un nuovo link.")
        st.stop()
    try:
        payload = db.decodifica_payload(qp.get("d", ""))
    except (ValueError, json.JSONDecodeError) as e:
        st.error("Non sono riuscito a leggere i dati della prova (%s). Riprova dal pulsante «Invia allo studio»." % e)
        st.stop()
    _, nuovo = db.salva_sessione(conn, rec["paziente_id"], payload, token_id=rec["id"])
    nome = db.CATALOGO[payload["task"]]["nome"]
    st.success(("Sessione «%s» salvata. Grazie!" if nuovo else "Sessione «%s» già salvata in precedenza.") % nome)
    st.caption("Puoi chiudere questa pagina e tornare alla prova.")
    st.stop()
