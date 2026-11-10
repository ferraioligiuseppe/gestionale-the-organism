# -*- coding: utf-8 -*-
"""
ui_foglio.py — Vista «📋 Foglio» del brogliaccio: la giornata come un foglio Excel.

Una riga = un fatto. Si scrive direttamente nelle celle (menu a tendina nelle colonne a scelta),
si aggiungono righe in fondo, si cancellano selezionandole. Un solo «💾 Salva il foglio» salva
nuove righe, modifiche e cancellazioni. Stessa tabella del resto del brogliaccio.
"""
from __future__ import annotations

import datetime as dt
import math

import pandas as pd
import streamlit as st

from . import db_brogliaccio as db

COLONNE = ["id", "Ora", "Paziente", "Nome (se non in anagrafica)", "Telefono", "Cosa è successo", "Sede", "Chi",
           "Descrizione", "Prestazione", "Importo €", "Pagamento", "Fattura", "Prossimo passo", "A chi", "Entro"]


def _vuoto(v) -> bool:
    return v is None or (isinstance(v, float) and math.isnan(v)) or (isinstance(v, str) and not v.strip()) or v is pd.NaT


def _val(v):
    return None if _vuoto(v) else v


def vista_foglio(conn, operatori, io, pazienti, etichetta_paz, utente):
    c1, c2 = st.columns([2, 5])
    giorno = c1.date_input("Giorno", value=dt.datetime.now(db.TZ).date(), format="DD/MM/YYYY", key="foglio_giorno")
    c2.caption("Scrivi direttamente nelle celle, come in Excel. **Riga nuova**: clic sull'ultima riga vuota. "
               "**Cancellare**: seleziona la riga a sinistra e premi Canc. Alla fine **💾 Salva il foglio**.")

    # Etichette uniche dei pazienti (se due hanno lo stesso nome e data, aggiungo il numero)
    etichette, viste = {}, {}
    for p in pazienti:
        e = etichetta_paz(p)
        viste[e] = viste.get(e, 0) + 1
    for p in pazienti:
        e = etichetta_paz(p)
        etichette[int(p["id"])] = e if viste[e] == 1 else f"{e} · n.{p['id']}"
    per_etichetta = {v: k for k, v in etichette.items()}

    righe = db.del_giorno(conn, giorno)
    originali = {}
    dati = []
    for r in righe:
        quando = r["quando"].astimezone(db.TZ) if hasattr(r["quando"], "astimezone") else r["quando"]
        riga = {"id": int(r["id"]), "Ora": quando.time().replace(second=0, microsecond=0),
                "Paziente": etichette.get(int(r["paziente_id"])) if r.get("paziente_id") else None,
                "Nome (se non in anagrafica)": r.get("nominativo"), "Telefono": r.get("telefono"),
                "Cosa è successo": r.get("tipo"), "Sede": r.get("sede"), "Chi": r.get("operatore"),
                "Descrizione": r.get("descrizione"), "Prestazione": r.get("prestazione"),
                "Importo €": float(r["importo"]) if r.get("importo") is not None else None,
                "Pagamento": r.get("pagamento"), "Fattura": r.get("fattura"),
                "Prossimo passo": r.get("prossimo_passo"), "A chi": r.get("assegnato_a"), "Entro": r.get("scadenza")}
        originali[riga["id"]] = riga
        dati.append(riga)
    df = pd.DataFrame(dati, columns=COLONNE)
    df["id"] = df["id"].astype("Int64")

    gen = st.session_state.get("foglio_gen", 0)
    chi_opz = list(dict.fromkeys(operatori + [x for x in df["Chi"].dropna().tolist() + df["A chi"].dropna().tolist()]))
    modificato = st.data_editor(
        df, key=f"foglio_{giorno.isoformat()}_{gen}", num_rows="dynamic", hide_index=True, use_container_width=True,
        column_config={
            "id": None,
            "Ora": st.column_config.TimeColumn("Ora", format="HH:mm", step=300),
            "Paziente": st.column_config.SelectboxColumn("Paziente", options=list(etichette.values()), width="medium"),
            "Nome (se non in anagrafica)": st.column_config.TextColumn("Nome (se nuovo)"),
            "Cosa è successo": st.column_config.SelectboxColumn("Cosa è successo", options=db.TIPI, width="medium"),
            "Sede": st.column_config.SelectboxColumn("Sede", options=db.SEDI),
            "Chi": st.column_config.SelectboxColumn("Chi", options=chi_opz),
            "Descrizione": st.column_config.TextColumn("Descrizione", width="large"),
            "Prestazione": st.column_config.SelectboxColumn("Prestazione", options=db.PRESTAZIONI),
            "Importo €": st.column_config.NumberColumn("Importo €", min_value=0.0, step=5.0, format="%.2f €"),
            "Pagamento": st.column_config.SelectboxColumn("Pagamento", options=db.METODI),
            "Fattura": st.column_config.SelectboxColumn("Fattura", options=db.FATTURA),
            "Prossimo passo": st.column_config.TextColumn("Prossimo passo"),
            "A chi": st.column_config.SelectboxColumn("A chi", options=chi_opz),
            "Entro": st.column_config.DateColumn("Entro", format="DD/MM/YYYY"),
        })

    # Totale della giornata, calcolato da quello che c'è nel foglio adesso
    tot = db.riepilogo_importi([{"importo": _val(r["Importo €"]), "pagamento": _val(r["Pagamento"]),
                                 "fattura": _val(r["Fattura"])} for _, r in modificato.iterrows()])
    if tot["n"] or tot["fatture_da_fare"]:
        st.caption(f"💶 Incassato **{db.euro(tot['incassato'])}** (POS {db.euro(tot['per_metodo']['POS'])} · contanti "
                   f"{db.euro(tot['per_metodo']['Contanti'])} · bonifico {db.euro(tot['per_metodo']['Bonifico'])}) · "
                   f"da pagare **{db.euro(tot['da_pagare'])}** · fatture da fare **{tot['fatture_da_fare']}**")

    s1, s2 = st.columns(2)
    try:
        from .stampa_foglio import pdf_foglio
        s1.download_button("🖨️ Stampa il foglio del giorno (PDF)", data=pdf_foglio(giorno, righe),
                           file_name=f"oggi_in_studio_{giorno.isoformat()}.pdf", mime="application/pdf",
                           use_container_width=True, key="foglio_pdf",
                           help="Le righe già salvate, più alcune righe vuote e i totali. Salva prima le modifiche.")
        s2.download_button("📄 Foglio vuoto da compilare a mano (PDF)", data=pdf_foglio(None, None),
                           file_name="oggi_in_studio_foglio_vuoto.pdf", mime="application/pdf",
                           use_container_width=True, key="foglio_pdf_vuoto")
    except Exception as e:
        s1.caption(f"Stampa non disponibile: {e}")

    if st.button("💾 Salva il foglio", type="primary", use_container_width=True, key="foglio_salva"):
        esito = salva(conn, giorno, originali, modificato, per_etichetta, io, utente)
        st.session_state["foglio_gen"] = gen + 1
        st.session_state["foglio_esito"] = esito
        st.rerun()
    esito = st.session_state.pop("foglio_esito", None)
    if esito:
        nuove, cambiate, tolte, saltate = esito
        st.success(f"Salvato ✔ · {nuove} nuove · {cambiate} modificate · {tolte} cancellate")
        for s in saltate:
            st.warning(s)


def _campi(r, per_etichetta) -> dict:
    paz = _val(r["Paziente"])
    entro = _val(r["Entro"])
    if isinstance(entro, (pd.Timestamp, dt.datetime)):
        entro = entro.date()
    imp = _val(r["Importo €"])
    return {"paziente_id": per_etichetta.get(paz) if paz else None,
            "nominativo": _val(r["Nome (se non in anagrafica)"]), "telefono": _val(r["Telefono"]),
            "tipo": _val(r["Cosa è successo"]), "sede": _val(r["Sede"]), "operatore": _val(r["Chi"]),
            "descrizione": _val(r["Descrizione"]), "prestazione": _val(r["Prestazione"]),
            "importo": round(float(imp), 2) if imp is not None else None, "pagamento": _val(r["Pagamento"]),
            "fattura": _val(r["Fattura"]), "prossimo_passo": _val(r["Prossimo passo"]),
            "assegnato_a": _val(r["A chi"]), "scadenza": entro}


def salva(conn, giorno, originali, modificato, per_etichetta, io, utente):
    """Ritorna (nuove, modificate, cancellate, avvisi)."""
    nuove = cambiate = tolte = 0
    avvisi = []
    ids_rimasti = set()
    for n, (_, r) in enumerate(modificato.iterrows(), start=1):
        rid = r["id"]
        c = _campi(r, per_etichetta)
        if c["fattura"] == "Da fare" and not c["prossimo_passo"]:
            c["prossimo_passo"] = "Fare la fattura"
        if c["prossimo_passo"] and not c["assegnato_a"]:
            c["assegnato_a"] = c["operatore"] or io
        if c["prossimo_passo"] and not c["scadenza"]:
            c["scadenza"] = giorno + dt.timedelta(days=2)
        ora = _val(r["Ora"])
        if isinstance(ora, str):
            try:
                ora = dt.time.fromisoformat(ora)
            except ValueError:
                ora = None
        if not _vuoto(rid):
            ids_rimasti.add(int(rid))
            prima = _campi(originali[int(rid)], per_etichetta) if int(rid) in originali else {}
            diversi = {k: v for k, v in c.items() if prima.get(k) != v}
            if ora and ora != originali.get(int(rid), {}).get("Ora"):
                diversi["quando"] = dt.datetime.combine(giorno, ora, tzinfo=db.TZ)
            if diversi:
                db.aggiorna(conn, int(rid), diversi)
                cambiate += 1
            continue
        # riga nuova
        if not (c["paziente_id"] or c["nominativo"] or c["descrizione"] or c["importo"] is not None):
            continue   # riga lasciata vuota
        if not c["tipo"]:
            c["tipo"] = db.T_SEDUTA if c["importo"] is not None else db.T_NOTA
        quando = dt.datetime.combine(giorno, ora or dt.datetime.now(db.TZ).time().replace(second=0, microsecond=0), tzinfo=db.TZ)
        rid_n = db.aggiungi(conn, tipo=c["tipo"], operatore=c["operatore"] or io, utente=utente, paziente_id=c["paziente_id"],
                            nominativo=c["nominativo"] or "", telefono=c["telefono"] or "", sede=c["sede"] or "",
                            descrizione=c["descrizione"] or "", prossimo_passo=c["prossimo_passo"] or "",
                            assegnato_a=c["assegnato_a"] or "", scadenza=c["scadenza"], quando=quando, rif_data=giorno,
                            importo=c["importo"], pagamento=c["pagamento"], fattura=c["fattura"], prestazione=c["prestazione"])
        if rid_n:
            nuove += 1
        else:
            avvisi.append(f"Riga {n}: non salvata, riprova.")
    for rid in originali:
        if rid not in ids_rimasti:
            db.elimina(conn, rid)
            tolte += 1
    return nuove, cambiate, tolte, avvisi
