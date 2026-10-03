"""
modules/crediti/ui_crediti.py
Cassa crediti/buoni e convenzioni, usabile da Aerosal, Ottica, Telefonia e Studio.

Uso da app_core.py:
    from modules.crediti import render_crediti
    render_crediti(conn, studio_id, settore_corrente="ottica", operatore=utente)
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pandas as pd
import streamlit as st

from . import db_crediti as dbc


def _euro(v) -> str:
    return f"{Decimal(v):,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


def _tab_cassa(conn, studio_id, settore, operatore):
    oggi = date.today()
    settore = settore or st.selectbox("Settore in cui stai incassando", dbc.SETTORI,
                                      format_func=dbc.ETICHETTE_SETTORE.get)
    cerca = st.text_input("Cerca cliente (nome o telefono)")
    crediti = dbc.crediti_disponibili(conn, studio_id, oggi, settore=settore, cerca=cerca or None)
    if not crediti:
        st.info(f"Nessun credito o buono spendibile in {dbc.ETICHETTE_SETTORE[settore]}.")
        return
    opz = {f"{c['nominativo']} · {c['tipo']} · residuo {_euro(c['residuo'])} · "
           f"scade {c['scade_il']:%d/%m/%Y}": c for c in crediti}
    c = opz[st.selectbox("Credito", list(opz))]
    importo = st.number_input("Importo da scalare €", min_value=0.01,
                              max_value=float(c["residuo"]), value=float(c["residuo"]), step=1.0)
    rif = st.text_input("Riferimento (scontrino, ordine, n. pacchetto)")
    if st.button("Scala credito", type="primary"):
        try:
            usato = dbc.usa_credito(conn, studio_id, c["id"], settore, Decimal(str(importo)),
                                    oggi, rif or None, operatore)
            st.success(f"Scalati {_euro(usato)} dal credito di {c['nominativo']}.")
        except ValueError as e:
            st.error(str(e))


def _tab_elenco(conn, studio_id):
    oggi = date.today()
    imp = st.session_state.get("_crediti_imp", {})
    c1, c2 = st.columns([3, 1])
    stati = c1.multiselect("Stato", ["attivo", "usato", "scaduto", "convertito", "annullato"],
                           default=["attivo"])
    if c2.button("Chiudi scadenze di oggi"):
        esito = dbc.gestisci_scadenze(conn, studio_id, oggi,
                                      converti=imp.get("converti_in_buono", True),
                                      giorni_buono=imp.get("giorni_validita_buono", 60))
        st.success(f"{esito['convertiti']} convertiti in buono · {esito['scaduti']} scaduti.")

    in_scad = dbc.in_scadenza(conn, studio_id, oggi, 7)
    if in_scad:
        st.warning(f"{len(in_scad)} crediti scadono nei prossimi 7 giorni: "
                   "contatta chi ha dato il consenso.")
        st.dataframe(pd.DataFrame(in_scad), hide_index=True, use_container_width=True)

    righe = dbc.elenco_crediti(conn, studio_id, tuple(stati) or ("attivo",))
    if righe:
        df = pd.DataFrame(righe)
        df["settori"] = df["settori"].map(lambda s: ", ".join(dbc.ETICHETTE_SETTORE[x] for x in s))
        st.dataframe(df, hide_index=True, use_container_width=True)
    else:
        st.info("Nessun credito con questi stati.")

    with st.expander("Movimenti per settore"):
        c3, c4 = st.columns(2)
        dal = c3.date_input("Dal", value=oggi - timedelta(days=30), key="cm_dal")
        al = c4.date_input("Al", value=oggi, key="cm_al")
        mov = dbc.movimenti(conn, studio_id, dal, al)
        if mov:
            df = pd.DataFrame(mov)
            st.dataframe(df, hide_index=True, use_container_width=True)
            st.bar_chart(df.groupby("settore")["importo"].sum().astype(float))
        else:
            st.write("Nessun movimento nel periodo.")


def _tab_nuovo(conn, studio_id):
    c1, c2 = st.columns(2)
    nom = c1.text_input("Nominativo", key="cn_nom")
    tel = c2.text_input("Telefono", key="cn_tel")
    c3, c4, c5 = st.columns(3)
    tipo = c3.selectbox("Tipo", ["buono", "credito"])
    importo = c4.number_input("Importo €", min_value=1.0, value=15.0, step=1.0)
    giorni = c5.number_input("Validità (giorni)", min_value=1, max_value=365, value=60)
    settori = st.multiselect("Spendibile in", dbc.SETTORI, default=["ottica", "telefonia"],
                             format_func=dbc.ETICHETTE_SETTORE.get)
    consenso = st.checkbox("Consenso marketing raccolto")
    note = st.text_input("Motivo / note", key="cn_note")
    if st.button("Emetti", type="primary"):
        if not nom or not settori:
            st.error("Nominativo e almeno un settore sono obbligatori.")
        else:
            dbc.crea_credito(conn, studio_id, {
                "nominativo": nom, "telefono": tel or None, "tipo": tipo, "origine": "manuale",
                "importo": Decimal(str(importo)), "settori": settori, "emesso_il": date.today(),
                "scade_il": date.today() + timedelta(days=int(giorni)),
                "consenso_marketing": consenso, "note": note or None})
            st.success("Emesso.")


def _tab_convenzioni(conn, studio_id):
    st.caption("Le convenzioni partono in bozza: attivale dopo aver concordato valori e condizioni "
               "con ottica e telefonia. Nessun vantaggio economico sulle prestazioni sanitarie.")
    conv = dbc.convenzioni(conn, studio_id)
    if not conv:
        st.info("Nessuna convenzione: esegui lo script 03.")
        return
    for c in conv:
        with st.container(border=True):
            st.markdown(f"**{c['nome']}**  \n{dbc.ETICHETTE_SETTORE[c['settore_origine']]} → "
                        f"{dbc.ETICHETTE_SETTORE[c['settore_vantaggio']]} · {c['condizione'] or ''}")
            k1, k2, k3 = st.columns([2, 1, 1])
            valore = k1.number_input(
                {"sconto_pct": "Sconto %", "buono_euro": "Buono €", "prezzo_speciale": "Prezzo €",
                 "omaggio": "Valore €"}[c["tipo_vantaggio"]],
                min_value=0.0, value=float(c["valore"] or 0), step=1.0, key=f"cv_{c['id']}")
            attiva = k2.toggle("Attiva", value=c["attiva"], key=f"ca_{c['id']}")
            if k3.button("Salva", key=f"cs_{c['id']}"):
                dbc.imposta_convenzione(conn, studio_id, c["id"], attiva, Decimal(str(valore)))
                st.rerun()
            if c["note"]:
                st.caption(c["note"])


def render_crediti(conn, studio_id: str, settore_corrente: str | None = None,
                   operatore: str | None = None, impostazioni: dict | None = None):
    """`impostazioni`: passare db_aerosal.impostazioni(conn, studio_id) per
    usare le regole di conversione credito → buono."""
    st.header("Crediti, buoni e convenzioni")
    st.session_state["_crediti_imp"] = impostazioni or {}
    tabs = st.tabs(["Cassa", "Elenco e scadenze", "Emetti buono", "Convenzioni"])
    with tabs[0]:
        _tab_cassa(conn, studio_id, settore_corrente, operatore)
    with tabs[1]:
        _tab_elenco(conn, studio_id)
    with tabs[2]:
        _tab_nuovo(conn, studio_id)
    with tabs[3]:
        _tab_convenzioni(conn, studio_id)
