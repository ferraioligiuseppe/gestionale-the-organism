"""Laboratorio PNEV — interfaccia Streamlit.

Uso nel gestionale:

    from modules.laboratorio.ui_laboratorio import cattura_codice_da_url, render_laboratorio

    # 1) all'inizio dell'app, PRIMA del login, così il codice non si perde:
    cattura_codice_da_url()

    # 2) nella pagina/scheda del paziente:
    render_laboratorio(conn, paziente_id=paziente_corrente_id, studio_id=studio_id)
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from modules.laboratorio import db_laboratorio as db

# ADATTA: indirizzo della pagina HTML del Laboratorio (su pnev.it o come artifact)
LAB_URL = "https://www.pnev.it/laboratorio/"

CHIAVE_STATO = "lab_codice_in_arrivo"


def _tabella(df: pd.DataFrame) -> None:
    """Tabella a tutta larghezza, compatibile con versioni di Streamlit vecchie e nuove."""
    try:
        _tabella(df, hide_index=True, width="stretch")
    except TypeError:
        st.dataframe(df)


def cattura_codice_da_url() -> None:
    """Prende ?lab=... dall'indirizzo e lo conserva fino al salvataggio."""
    codice = st.query_params.get("lab")
    if codice:
        st.session_state[CHIAVE_STATO] = codice
        try:
            del st.query_params["lab"]
        except KeyError:
            pass


def _mostra_anteprima(dati: dict) -> None:
    quando = db.data_esecuzione(dati)
    c1, c2, c3 = st.columns(3)
    c1.metric("Modulo", db.MODULI.get(dati["modulo"], dati["modulo"]))
    c2.metric("Eseguito il", quando.strftime("%d/%m/%Y %H:%M") if quando else "—")
    c3.metric("Codice paziente", str(dati.get("paziente") or "—"))
    st.write(f"**Risultato:** {dati.get('risultato', '')}")
    st.caption(f"Parametri: {dati.get('parametri', '')} · Seduta: {dati.get('seduta') or '—'} · Operatore: {dati.get('operatore') or '—'}")
    metriche = dati.get("metriche") or {}
    if metriche:
        _tabella(pd.DataFrame([{"Misura": k.replace("_", " "), "Valore": "—" if v is None else str(v)} for k, v in metriche.items()]))
    prove = dati.get("prove") or []
    if prove:
        with st.expander(f"Dettaglio delle prove ({len(prove)})"):
            _tabella(pd.DataFrame(prove))


def _riquadro_salvataggio(conn, codice: str, paziente_id: int | None, studio_id: int | None, chiave: str) -> None:
    try:
        dati = db.decodifica_codice(codice)
    except db.CodiceNonValido as exc:
        st.error(str(exc))
        if st.button("Scarta il codice", key=f"{chiave}_scarta_err"):
            st.session_state.pop(CHIAVE_STATO, None)
            st.rerun()
        return

    _mostra_anteprima(dati)

    dal_codice = db.paziente_dal_codice(dati)
    proposto = paziente_id or dal_codice
    if paziente_id and dal_codice and paziente_id != dal_codice:
        st.warning(f"Il codice indica il paziente {dal_codice}, ma è aperta la scheda del paziente {paziente_id}. Controlla prima di salvare.")
    pid = st.number_input("Salva nella scheda del paziente (ID)", min_value=1, step=1,
                          value=int(proposto) if proposto else 1, key=f"{chiave}_pid")

    c1, c2 = st.columns(2)
    if c1.button("Salva nella scheda", type="primary", key=f"{chiave}_salva"):
        nuovo = db.salva_risultato(conn, int(pid), dati, codice, studio_id=studio_id)
        st.session_state.pop(CHIAVE_STATO, None)
        if nuovo:
            st.success(f"Risultato salvato nella scheda del paziente {int(pid)}.")
        else:
            st.info("Questo risultato era già stato salvato: nessun doppione creato.")
    if c2.button("Scarta", key=f"{chiave}_scarta"):
        st.session_state.pop(CHIAVE_STATO, None)
        st.rerun()


def _andamento(righe: list[dict]) -> None:
    for modulo, misure in db.METRICHE_ANDAMENTO.items():
        del_modulo = [r for r in righe if r["modulo"] == modulo]
        punti = []
        for r in del_modulo:
            quando = r["eseguito_il"] or r["salvato_il"]
            riga = {"Data": pd.to_datetime(quando)}
            for chiave, etichetta in misure:
                valore = (r["metriche"] or {}).get(chiave)
                if isinstance(valore, (int, float)):
                    riga[etichetta] = valore
            if len(riga) > 1:
                punti.append(riga)
        if len(punti) >= 2:
            st.markdown(f"**{db.MODULI[modulo]}**")
            df = pd.DataFrame(punti).sort_values("Data").set_index("Data")
            st.line_chart(df)


def render_laboratorio(conn, paziente_id: int | None = None, studio_id: int | None = None) -> None:
    st.subheader("Laboratorio PNEV · sezione sperimentale")
    st.caption("Visore binoculare, suono e sonno, memoria iconica, ritmo theta. Le prove si svolgono nella pagina del Laboratorio; qui si salvano e si seguono nel tempo.")
    st.link_button("Apri il Laboratorio PNEV", LAB_URL)

    db.crea_tabella(conn)

    # 1) risultato arrivato dal link «Invia al gestionale»
    in_arrivo = st.session_state.get(CHIAVE_STATO)
    if in_arrivo:
        with st.container(border=True):
            st.markdown("#### Risultato ricevuto dal Laboratorio")
            _riquadro_salvataggio(conn, in_arrivo, paziente_id, studio_id, chiave="arrivo")

    # 2) codice incollato a mano
    with st.expander("Incolla un codice dal Registro del Laboratorio"):
        incollato = st.text_area("Codice (inizia con z1. o j1.)", key="lab_incolla", height=90)
        if incollato.strip():
            _riquadro_salvataggio(conn, incollato.strip(), paziente_id, studio_id, chiave="incolla")

    # 3) storico del paziente
    if not paziente_id:
        st.info("Apri la scheda di un paziente per vedere i suoi risultati del Laboratorio.")
        return
    righe = db.elenco_risultati(conn, paziente_id)
    if not righe:
        st.info("Nessun risultato del Laboratorio salvato per questo paziente.")
        return

    st.markdown("#### Andamento nel tempo")
    _andamento(righe)

    st.markdown("#### Tutti i risultati")
    tabella = pd.DataFrame([
        {
            "Data": (r["eseguito_il"] or r["salvato_il"]).astimezone(db.TZ).strftime("%d/%m/%Y %H:%M"),
            "Modulo": db.MODULI.get(r["modulo"], r["modulo"]),
            "Seduta": r["seduta"] or "",
            "Risultato": r["risultato"] or "",
            "Operatore": r["operatore"] or "",
            "ID": r["id"],
        }
        for r in righe
    ])
    _tabella(tabella)

    with st.expander("Dettaglio o eliminazione di un risultato"):
        scelta = st.selectbox("Risultato", options=[r["id"] for r in righe],
                              format_func=lambda i: next(f"{t['Data']} · {t['Modulo']}" for t in tabella.to_dict("records") if t["ID"] == i))
        r = next(x for x in righe if x["id"] == scelta)
        st.json(r["metriche"] or {})
        if r["prove"]:
            _tabella(pd.DataFrame(r["prove"]))
        conferma = st.checkbox("Confermo di voler eliminare questo risultato", key=f"lab_conf_{scelta}")
        if st.button("Elimina risultato", disabled=not conferma, key=f"lab_del_{scelta}"):
            db.elimina_risultato(conn, scelta)
            st.success("Risultato eliminato.")
            st.rerun()
