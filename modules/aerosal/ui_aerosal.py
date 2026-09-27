"""
modules/aerosal/ui_aerosal.py
Interfaccia Streamlit del modulo Aerosal.

Uso da app_core.py:
    from modules.aerosal import render_aerosal
    render_aerosal(conn, studio_id, pazienti=lista_pazienti, operatore=utente)

`pazienti` è una lista di tuple (id, "Cognome Nome") fornita dall'anagrafica
già esistente: il modulo non legge direttamente la tabella pazienti.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

import pandas as pd
import streamlit as st

from . import db_aerosal as db

SOGLIA_PM10 = "Erogazione nei primi minuti · max ~40 µg/m³ PM10 (soglia 50 µg/m³)"


def _euro(v) -> str:
    if v is None:
        return "—"
    return f"{Decimal(v):,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


def _scegli_paziente(pazienti, key: str, paziente_id=None):
    if paziente_id:
        return paziente_id
    if pazienti:
        opzioni = {lab: pid for pid, lab in pazienti}
        lab = st.selectbox("Paziente", list(opzioni), key=key)
        return opzioni[lab]
    return st.number_input("ID paziente", min_value=1, step=1, key=key)


# ------------------------------------------------------------------ Listino
def _tab_listino(conn, studio_id):
    mostra_tutto = st.toggle("Mostra anche le promo scadute", value=False)
    righe = db.listino(conn, studio_id, solo_attivi=not mostra_tutto)
    if not righe:
        st.info("Listino vuoto: esegui `02_aerosal_seed.sql` oppure aggiungi una voce qui sotto.")
    else:
        df = pd.DataFrame(righe)
        df["€/seduta"] = df.apply(
            lambda r: _euro(Decimal(r["prezzo"]) / r["n_sedute"]) if r["prezzo"] else "—", axis=1)
        df["prezzo"] = df["prezzo"].map(_euro)
        df["prezzo_pieno_rif"] = df["prezzo_pieno_rif"].map(lambda v: _euro(v) if v else "")
        st.dataframe(
            df[["codice", "descrizione", "tipo", "n_sedute", "prezzo", "€/seduta",
                "prezzo_pieno_rif", "promo_nome", "valido_dal", "valido_al", "attivo"]],
            hide_index=True, use_container_width=True)

    with st.expander("Aggiungi o aggiorna una voce"):
        c1, c2, c3 = st.columns(3)
        codice = c1.text_input("Codice", placeholder="PKG20")
        descr = c2.text_input("Descrizione")
        tipo = c3.selectbox("Tipo", ["base", "promo"])
        c4, c5, c6 = st.columns(3)
        n = c4.number_input("Sedute", min_value=1, value=20, step=1)
        prezzo = c5.number_input("Prezzo €", min_value=0.0, value=0.0, step=1.0, format="%.2f")
        pieno = c6.number_input("Prezzo pieno di riferimento €", min_value=0.0, value=0.0,
                                step=1.0, format="%.2f")
        c7, c8, c9 = st.columns(3)
        promo = c7.text_input("Nome promo")
        dal = c8.date_input("Valida dal", value=None)
        al = c9.date_input("Valida al", value=None)
        limite = st.number_input("Limite pacchetti per centro (0 = nessuno)", min_value=0, value=0)
        attivo = st.checkbox("Attiva", value=True)
        if st.button("Salva voce di listino", type="primary"):
            if not codice or not descr:
                st.error("Codice e descrizione sono obbligatori.")
            else:
                db.salva_voce_listino(conn, studio_id, {
                    "codice": codice.strip().upper(), "descrizione": descr, "tipo": tipo,
                    "n_sedute": int(n), "prezzo": Decimal(str(prezzo)),
                    "prezzo_pieno_rif": Decimal(str(pieno)) if pieno else None,
                    "promo_nome": promo or None, "valido_dal": dal, "valido_al": al,
                    "limite_pacchetti": int(limite) or None, "attivo": attivo})
                st.success(f"Voce {codice.upper()} salvata.")
                st.rerun()


# ------------------------------------------------------------- Prime prove
def _tab_prove(conn, studio_id, pazienti):
    cat = db.categorie_prova(conn)
    mappa = {c["descrizione"]: c["codice"] for c in cat}

    st.caption("Stesse 4 voci della campagna «Prima Seduta Prova» di Carta Respiro.")
    c1, c2 = st.columns(2)
    nominativo = c1.text_input("Nominativo")
    telefono = c2.text_input("Telefono")
    c3, c4, c5 = st.columns(3)
    categoria = c3.selectbox("Categoria", list(mappa))
    origine = c4.selectbox("Origine", ["open_day", "prima_seduta"],
                           format_func=lambda x: "Open day" if x == "open_day" else "Prima seduta")
    data_p = c5.date_input("Data", value=date.today())
    in_cr = st.checkbox("Già registrata su Carta Respiro")
    note = st.text_input("Note", key="prova_note")
    if st.button("Registra prova", type="primary"):
        if not nominativo:
            st.error("Inserisci il nominativo.")
        else:
            db.registra_prova(conn, studio_id, {
                "nominativo": nominativo, "telefono": telefono or None,
                "categoria": mappa[categoria], "origine": origine, "data_prova": data_p,
                "registrata_carta_respiro": in_cr, "note": note or None})
            st.success("Prova registrata.")
            st.rerun()

    st.divider()
    c6, c7 = st.columns(2)
    dal = c6.date_input("Dal", value=date.today() - timedelta(days=30), key="prove_dal")
    al = c7.date_input("Al", value=date.today(), key="prove_al")
    k = db.tasso_conversione(conn, studio_id, dal, al)
    m1, m2, m3 = st.columns(3)
    m1.metric("Prove", k["prove"])
    m2.metric("Convertite in pacchetto", k["convertite"])
    m3.metric("Conversione", f"{k['tasso']} %")

    righe = db.prove(conn, studio_id, dal, al)
    if righe:
        st.dataframe(pd.DataFrame(righe).drop(columns=["pacchetto_id"]),
                     hide_index=True, use_container_width=True)
        da_reg = [r for r in righe if not r["registrata_carta_respiro"]]
        if da_reg:
            st.warning(f"{len(da_reg)} prove non ancora caricate su Carta Respiro.")
            scelta = st.selectbox(
                "Segna come caricata",
                [f"{r['id']} · {r['nominativo']} · {r['data_prova']}" for r in da_reg])
            if st.button("Segna caricata su Carta Respiro"):
                db.segna_carta_respiro(conn, studio_id, int(scelta.split(" · ")[0]), True)
                st.rerun()
    else:
        st.info("Nessuna prova nel periodo scelto.")


# ----------------------------------------------------------------- Vendita
def _tab_vendita(conn, studio_id, pazienti, paziente_id):
    voci = db.listino(conn, studio_id, solo_attivi=True)
    voci = [v for v in voci if v["prezzo"] and v["prezzo"] > 0]
    if not voci:
        st.info("Nessuna voce attiva con prezzo: completa prima il listino.")
        return

    pid = _scegli_paziente(pazienti, "vend_paz", paziente_id)
    etichette = {f"{v['descrizione']} — {_euro(v['prezzo'])}": v for v in voci}
    voce = etichette[st.selectbox("Pacchetto", list(etichette))]

    if voce["limite_pacchetti"]:
        vendute = db.promo_vendute(conn, studio_id, voce["id"])
        residue = voce["limite_pacchetti"] - vendute
        (st.error if residue <= 0 else st.info)(
            f"Promo a disponibilità limitata: {vendute}/{voce['limite_pacchetti']} già venduti.")

    prezzo = st.number_input("Prezzo applicato €", min_value=0.0,
                             value=float(voce["prezzo"]), step=1.0, format="%.2f")
    data_acq = st.date_input("Data acquisto", value=date.today(), key="vend_data")
    modalita = st.radio("Pagamento", ["unica", "rateale"], horizontal=True,
                        format_func=lambda x: "Unica soluzione" if x == "unica" else "Rateale")

    provider = n_rate = metodo = None
    pagato_subito = False
    if modalita == "rateale":
        provider = st.selectbox("Rateizzazione", db.PROVIDER_RATE,
                                help="Klarna/PayPal/HeyLight: il centro incassa subito l'intero importo. "
                                     "Interno: genera il piano rate mensile.")
        if provider == "Interno":
            n_rate = st.number_input("Numero rate", min_value=2, max_value=24, value=3)
            anteprima = db.piano_rate(Decimal(str(prezzo)), int(n_rate), data_acq)
            st.dataframe(pd.DataFrame([{"scadenza": r["scadenza"], "importo": _euro(r["importo"])}
                                       for r in anteprima]), hide_index=True)
        else:
            metodo, pagato_subito = provider, True
    else:
        metodo = st.selectbox("Metodo", db.METODI_PAGAMENTO)
        pagato_subito = st.checkbox("Incassato oggi", value=True)

    detraibile = st.checkbox("Detraibile (dispositivo medico)", value=True)
    note = st.text_input("Note", key="vend_note")

    if st.button("Registra vendita", type="primary"):
        nuovo = db.vendi_pacchetto(conn, studio_id, {
            "paziente_id": int(pid), "listino_id": voce["id"], "descrizione": voce["descrizione"],
            "n_sedute": voce["n_sedute"], "prezzo_totale": Decimal(str(prezzo)),
            "data_acquisto": data_acq, "modalita": modalita, "provider_rate": provider,
            "n_rate": int(n_rate) if n_rate else None, "metodo": metodo,
            "pagato_subito": pagato_subito, "detraibile": detraibile, "note": note or None})
        st.success(f"Pacchetto n. {nuovo} registrato.")


# ------------------------------------------------------------------ Sedute
def _tab_sedute(conn, studio_id, pazienti, paziente_id, operatore):
    pid = _scegli_paziente(pazienti, "sed_paz", paziente_id)
    pacchetti = db.pacchetti_paziente(conn, studio_id, int(pid))
    attivi = [p for p in pacchetti if p["stato"] == "attivo"]

    if pacchetti:
        df = pd.DataFrame(pacchetti)[["pacchetto_id", "descrizione", "sedute_fatte",
                                      "sedute_residue", "prezzo_totale", "incassato", "stato"]]
        df["prezzo_totale"] = df["prezzo_totale"].map(_euro)
        df["incassato"] = df["incassato"].map(_euro)
        st.dataframe(df, hide_index=True, use_container_width=True)
    if not attivi:
        st.info("Nessun pacchetto attivo per questo paziente.")
        return

    scelte = {f"n. {p['pacchetto_id']} · {p['descrizione']} · residue {p['sedute_residue']}": p
              for p in attivi}
    pac = scelte[st.selectbox("Pacchetto", list(scelte))]
    st.progress(pac["sedute_fatte"] / pac["n_sedute"],
                text=f"{pac['sedute_fatte']} di {pac['n_sedute']} sedute")

    c1, c2, c3 = st.columns(3)
    giorno = c1.date_input("Data", value=date.today(), key="sed_data")
    ora = c2.time_input("Ora", value=datetime.now(db.TZ).time().replace(second=0, microsecond=0))
    durata = c3.number_input("Durata (min)", min_value=5, max_value=90, value=30, step=5)
    tollerata = st.checkbox("Seduta ben tollerata", value=True)
    sintomi = interrotta = None
    if not tollerata:
        sintomi = st.text_input("Sintomi osservati (tosse, dispnea, altro)")
        interrotta = st.checkbox("Seduta interrotta")
        st.warning("In presenza di tosse importante o difficoltà respiratoria: "
                   "interrompere e indirizzare al pediatra o al medico curante.")
    note = st.text_input("Note", key="sed_note")
    st.caption(SOGLIA_PM10)

    if st.button("Registra seduta", type="primary"):
        try:
            db.registra_seduta(conn, studio_id, {
                "pacchetto_id": pac["pacchetto_id"], "paziente_id": int(pid),
                "data_ora": datetime.combine(giorno, ora, tzinfo=db.TZ), "durata_min": int(durata),
                "operatore": operatore, "tollerata": tollerata, "sintomi": sintomi or None,
                "interrotta": bool(interrotta), "note": note or None})
            st.success("Seduta registrata.")
            st.rerun()
        except ValueError as e:
            st.error(str(e))

    with st.expander("Storico sedute del pacchetto"):
        storico = db.sedute_pacchetto(conn, studio_id, pac["pacchetto_id"])
        if storico:
            st.dataframe(pd.DataFrame(storico), hide_index=True, use_container_width=True)
        else:
            st.write("Nessuna seduta registrata.")


# -------------------------------------------------------------------- Rate
def _tab_rate(conn, studio_id):
    entro = st.date_input("Scadenze fino al", value=date.today() + timedelta(days=15))
    rate = db.rate_in_scadenza(conn, studio_id, entro)
    if not rate:
        st.success("Nessun pagamento in sospeso fino alla data scelta.")
        return
    df = pd.DataFrame(rate)
    df["scaduta"] = df["scadenza"] < date.today()
    df["importo"] = df["importo"].map(_euro)
    st.dataframe(df, hide_index=True, use_container_width=True)

    scelte = {f"{r['id']} · paz. {r['paziente_id']} · {r['scadenza']} · {_euro(r['importo'])}": r["id"]
              for r in rate}
    sel = st.selectbox("Incassa", list(scelte))
    c1, c2, c3 = st.columns(3)
    metodo = c1.selectbox("Metodo", db.METODI_PAGAMENTO, key="rate_metodo")
    data_pag = c2.date_input("Data incasso", value=date.today(), key="rate_data")
    rif = c3.text_input("Riferimento (n. ricevuta/CRO)")
    if st.button("Segna come incassata", type="primary"):
        db.segna_pagato(conn, studio_id, scelte[sel], metodo, data_pag, rif or None)
        st.rerun()


# -------------------------------------------------------------------- Sale
def _tab_sale(conn, studio_id):
    date_rit = db.date_ritiro_future(conn)
    if date_rit:
        prossima = date_rit[0]
        giorni = (prossima - date.today()).days
        msg = f"Prossimo ritiro: {prossima:%d/%m/%Y} (tra {giorni} giorni) · 9-12 o 14-16"
        (st.warning if giorni <= 3 else st.info)(msg)
    st.caption(f"Appuntamento obbligatorio: email a {db.EMAIL_ORDINI} con copia del pagamento.")

    with st.expander("Nuovo ordine sale", expanded=not db.ordini_sale(conn, studio_id)):
        c1, c2, c3 = st.columns(3)
        data_o = c1.date_input("Data ordine", value=date.today(), key="sale_data")
        qta = c2.text_input("Quantità")
        imp = c3.number_input("Importo €", min_value=0.0, value=0.0, step=1.0, format="%.2f")
        c4, c5, c6 = st.columns(3)
        data_pag = c4.date_input("Pagato il", value=None, key="sale_pag")
        rit = c5.selectbox("Data ritiro", [None] + date_rit,
                           format_func=lambda d: "Da definire" if d is None else f"{d:%d/%m/%Y}")
        fascia = c6.selectbox("Fascia", [None, *db.FASCE_RITIRO],
                              format_func=lambda f: "—" if f is None else f)
        mail = st.checkbox(f"Email inviata a {db.EMAIL_ORDINI}")
        if st.button("Salva ordine", type="primary"):
            stato = "appuntamento" if (mail and rit) else ("pagato" if data_pag else "da_pagare")
            db.salva_ordine_sale(conn, studio_id, {
                "data_ordine": data_o, "quantita": qta or None,
                "importo": Decimal(str(imp)) if imp else None, "data_pagamento": data_pag,
                "email_inviata": mail, "data_ritiro": rit, "fascia": fascia, "stato": stato})
            st.rerun()

    ordini = db.ordini_sale(conn, studio_id)
    if ordini:
        st.dataframe(pd.DataFrame(ordini), hide_index=True, use_container_width=True)
        aperti = [o for o in ordini if o["stato"] != "ritirato"]
        if aperti:
            c1, c2 = st.columns(2)
            scelte = {f"{o['id']} · {o['data_ordine']} · {o['stato']}": o["id"] for o in aperti}
            sel = c1.selectbox("Ordine", list(scelte))
            nuovo = c2.selectbox("Nuovo stato", ["pagato", "appuntamento", "ritirato"])
            if st.button("Aggiorna stato ordine"):
                db.aggiorna_stato_ordine(conn, studio_id, scelte[sel], nuovo)
                st.rerun()

    with st.expander("Aggiungi data di ritiro comunicata da Aerosal"):
        nd = st.date_input("Data", value=None, key="nuova_data_rit")
        if st.button("Aggiungi data") and nd:
            db.aggiungi_data_ritiro(conn, nd)
            st.rerun()


# ------------------------------------------------------------------- Entry
def render_aerosal(conn, studio_id: str, pazienti=None, paziente_id=None, operatore=None):
    st.header("Aerosal · Haloterapia")
    chiave = f"_aerosal_schema_ok_{studio_id}"
    if not st.session_state.get(chiave):
        err = db.assicura_schema(conn, studio_id)
        if err:
            st.error(f"Tabelle Aerosal non create: {err}")
            return
        st.session_state[chiave] = True
    tabs = st.tabs(["Listino", "Prime prove", "Vendita pacchetto", "Sedute", "Rate", "Sale"])
    with tabs[0]:
        _tab_listino(conn, studio_id)
    with tabs[1]:
        _tab_prove(conn, studio_id, pazienti)
    with tabs[2]:
        _tab_vendita(conn, studio_id, pazienti, paziente_id)
    with tabs[3]:
        _tab_sedute(conn, studio_id, pazienti, paziente_id, operatore)
    with tabs[4]:
        _tab_rate(conn, studio_id)
    with tabs[5]:
        _tab_sale(conn, studio_id)
