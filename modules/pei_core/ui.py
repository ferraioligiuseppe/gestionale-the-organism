"""
pei_core.ui — interfaccia Streamlit comune.

Uso nelle app:
    from pei_core.ui import pagina_pei
    pagina_pei(conn, rif_tipo="corsista", rif_id=user_id, utente="gferraioli",
               anonimo_obbligatorio=True)                      # TFA Manager
    pagina_pei(conn, rif_tipo="paziente", rif_id=paz_id, utente=op,
               tenant_id=studio_id, intestazione=carta_intestata)  # gestionale
"""
from __future__ import annotations

from datetime import date

import streamlit as st

from . import db
from .model import Documento, controlla_anonimato, controlla_percorso, precompila_sezione2
from .pdf_io import genera_pdf, unisci_pdf
from .schema import TIPI_DOCUMENTO, schema_per


_ST_VER = tuple(int(x) for x in st.__version__.split(".")[:2])


def _widget(campo, valore, chiave):
    t, lab = campo["tipo"], campo["label"]
    if t == "text":
        return st.text_input(lab, value=valore or "", key=chiave)
    if t == "textarea":
        return st.text_area(lab, value=valore or "", key=chiave, height=110)
    if t == "number":
        return st.number_input(lab, min_value=0.0, max_value=60.0, step=0.5,
                               value=float(valore or 0), key=chiave)
    if t == "tabella":
        import pandas as pd
        cols = campo["opzioni"]
        df = pd.DataFrame(valore or [], columns=[c["key"] for c in cols])
        conf = {c["key"]: (st.column_config.SelectboxColumn(c["label"], options=c["opzioni"])
                           if c["tipo"] == "select" else st.column_config.TextColumn(c["label"]))
                for c in cols}
        st.markdown(f"**{lab}**")
        larghezza = ({"width": "stretch"} if _ST_VER >= (1, 46)
                     else {"use_container_width": True})          # gestionale: Streamlit < 1.46
        out = st.data_editor(df, column_config=conf, num_rows="dynamic", hide_index=True,
                             key=chiave, **larghezza)
        return [{k: ("" if pd.isna(v) else v) for k, v in r.items()}
                for r in out.to_dict("records") if any(str(v).strip() for v in r.values() if not pd.isna(v))]
    if t == "checkbox":
        return st.checkbox(lab, value=bool(valore), key=chiave)
    if t == "select":
        opz = [""] + campo["opzioni"]
        return st.selectbox(lab, opz, index=opz.index(valore) if valore in opz else 0, key=chiave)
    if t == "multiselect":
        return st.multiselect(lab, campo["opzioni"],
                              default=[v for v in (valore or []) if v in campo["opzioni"]], key=chiave)
    if t == "date":
        v = date.fromisoformat(valore) if valore else None
        d = st.date_input(lab, value=v, key=chiave, format="DD/MM/YYYY")
        return d.isoformat() if d else ""
    return st.text_input(lab, value=str(valore or ""), key=chiave)


def azzera_widget(prefisso: str):
    """Dopo una modifica esterna del contenuto, i campi devono rileggere dal database."""
    for k in list(st.session_state):
        if k.startswith(prefisso + "_"):
            del st.session_state[k]


def form_documento(doc: Documento, prefisso: str) -> dict:
    """Disegna il modulo a sezioni e restituisce il nuovo contenuto.
    La visibilità (PEI provvisorio) segue il valore appena scelto nell'intestazione."""
    nuovo = dict(doc.contenuto)
    for sez in schema_per(doc.tipo):
        anteprima = Documento(tipo=doc.tipo, contenuto=nuovo)
        if sez["id"] not in {x["id"] for x in anteprima.sezioni()}:
            continue
        with st.expander(sez["titolo"], expanded=sez["id"] in ("frontespizio", "intestazione")):
            for campo in sez["campi"]:
                nuovo[campo["key"]] = _widget(campo, doc.contenuto.get(campo["key"]),
                                              f"{prefisso}_{campo['key']}")
    return nuovo


def pagina_pei(conn, rif_tipo: str, rif_id: int, utente: str = "",
               tenant_id: int | None = None, intestazione=None,
               anonimo_obbligatorio: bool = False, salva_esportato=None,
               etichetta_salva: str = "Salva una copia nei documenti",
               margini=None, valori_iniziali: dict | None = None,
               mostra_esempio: bool = False, prima_del_modulo=None):
    """salva_esportato: callback opzionale (nome_file, bytes_pdf, doc) -> bool,
    per archiviare il PDF esportato nell'area documenti dell'app ospite.
    mostra_esempio: offre il caso didattico (TFA Manager).
    prima_del_modulo: callback (doc, prefisso_chiavi) disegnato sopra i campi."""
    st.subheader("PEI · PDF · documenti per l'inclusione")

    # ---- scelta documento --------------------------------------------------
    docs = db.elenco_documenti(conn, rif_tipo, rif_id)
    etichette = {"__nuovo__": "➕ Nuovo documento"}
    for d in docs:
        etichette[d["id"]] = (f"{d['tipo']} · {d['soggetto'] or '—'} · {d['anno_scolastico'] or ''}"
                              f" · {d['stato']}")
    chiave_sel = f"pei_sel_{rif_tipo}_{rif_id}"
    if chiave_sel + "_pend" in st.session_state:          # selezione impostata dal giro precedente
        st.session_state[chiave_sel] = st.session_state.pop(chiave_sel + "_pend")
    if st.session_state.get(chiave_sel) not in etichette:
        st.session_state[chiave_sel] = docs[0]["id"] if docs else "__nuovo__"
    scelta = st.selectbox("Documento", list(etichette), format_func=etichette.get, key=chiave_sel)

    if scelta == "__nuovo__":
        c1, c2 = st.columns(2)
        tipo = c1.selectbox("Tipo", list(TIPI_DOCUMENTO),
                            format_func=lambda k: f"{k} — {TIPI_DOCUMENTO[k]}")
        anno = c2.text_input("Anno scolastico", value="2026/2027")
        if st.button("Crea"):
            nuovo = Documento(tipo=tipo, anno_scolastico=anno, anonimo=anonimo_obbligatorio)
            nuovo.contenuto.update(valori_iniziali or {})
            nuovo.contenuto["anno_scolastico"] = anno
            st.session_state[chiave_sel + "_pend"] = db.salva_documento(conn, nuovo, rif_tipo, rif_id,
                                                                        utente, tenant_id)
            st.rerun()
        if mostra_esempio:
            from .esempi import AVVERTENZA, crea_esempio
            st.divider()
            st.markdown("**Caso d'esempio** — PDF e PEI completi e collegati, per esercitarsi")
            st.caption(AVVERTENZA)
            if st.button("📘 Crea il caso d'esempio", key=f"pei_es_{rif_tipo}_{rif_id}"):
                _, id_pei = crea_esempio(conn, rif_tipo, rif_id, utente, tenant_id)
                st.session_state[chiave_sel + "_pend"] = id_pei
                st.rerun()
        return

    doc = db.carica_documento(conn, scelta, rif_tipo, rif_id)
    if doc is None:
        st.error("Documento non trovato.")
        return
    pref = f"pei{doc.id}"
    st.progress(doc.completamento() / 100, text=f"Compilato al {doc.completamento()}%")

    # ---- precompilazione sezione 2 (solo PEI) ------------------------------
    if doc.tipo == "PEI":
        sorgenti = [d for d in docs if d["tipo"] in ("PF", "PDF", "DF")]
        if sorgenti:
            with st.popover("Precompila sezione 2 da PF / PDF / DF"):
                s_id = st.selectbox("Documento sorgente", [d["id"] for d in sorgenti],
                                    format_func=lambda i: etichette[i], key=f"{pref}_src")
                if st.button("Precompila", key=f"{pref}_go"):
                    src = db.carica_documento(conn, s_id, rif_tipo, rif_id)
                    precompila_sezione2(doc, src)
                    db.salva_documento(conn, doc, rif_tipo, rif_id, utente, tenant_id, sorgente_id=s_id)
                    azzera_widget(pref)
                    st.rerun()

    # ---- aggancio dell'app ospite (es. dati clinici del gestionale) --------
    if prima_del_modulo:
        prima_del_modulo(doc, pref)

    # ---- modulo ------------------------------------------------------------
    doc.contenuto = form_documento(doc, pref)
    if not anonimo_obbligatorio:
        doc.anonimo = st.toggle("Documento anonimizzato", value=doc.anonimo, key=f"{pref}_anon")
    else:
        doc.anonimo = True

    avvisi = controlla_anonimato(doc) if doc.anonimo else []
    for a in avvisi:
        st.warning(a)
    for a in controlla_percorso(doc):
        st.info(a)
    if doc.provvisorio:
        st.caption("PEI provvisorio: sono mostrate solo le sezioni prescritte dall'art. 16 c.3 "
                   "(intestazione e GLO, 1, 2, 4, 6, 12).")

    c1, c2, c3 = st.columns(3)
    if c1.button("💾 Salva bozza", key=f"{pref}_save"):
        doc.stato = "bozza"
        db.salva_documento(conn, doc, rif_tipo, rif_id, utente, tenant_id)
        st.success("Salvato.")
    if c2.button("✅ Segna definitivo", key=f"{pref}_def",
                 disabled=bool(avvisi and anonimo_obbligatorio)):
        doc.stato = "definitivo"
        db.salva_documento(conn, doc, rif_tipo, rif_id, utente, tenant_id)
        st.success("Segnato come definitivo.")
    if c3.button("🗑️ Elimina", key=f"{pref}_del"):
        st.session_state[f"{pref}_conferma"] = True
    if st.session_state.get(f"{pref}_conferma"):
        st.error("Eliminare il documento e i suoi allegati?")
        if st.button("Sì, elimina", key=f"{pref}_del_ok"):
            db.elimina_documento(conn, doc.id, rif_tipo, rif_id)
            st.session_state.pop(f"{pref}_conferma")
            st.session_state[chiave_sel + "_pend"] = "__nuovo__"
            st.rerun()

    # ---- allegati PDF ------------------------------------------------------
    st.markdown("#### Allegati PDF")
    if anonimo_obbligatorio:
        st.caption("Nel TFA carica solo file già anonimizzati.")
    up = st.file_uploader("Carica PDF (DF, PDF della scuola, PEI firmato…)", type=["pdf"],
                          key=f"{pref}_up")
    if up is not None and st.button("Aggiungi allegato", key=f"{pref}_upok"):
        try:
            info = db.aggiungi_allegato(conn, doc.id, up.getvalue(), up.name, utente)
            if info["duplicato"]:
                st.info("Questo file è già allegato.")
            else:
                msg = f"Allegato: {info['pagine']} pagine."
                if info["scansione"]:
                    msg += " Sembra una scansione: il testo non è ricercabile."
                st.success(msg)
        except ValueError as e:
            st.error(str(e))

    allegati = db.elenco_allegati(conn, doc.id)
    for a in allegati:
        a1, a2, a3 = st.columns([6, 2, 1])
        a1.write(f"📄 {a['nome_file']} · {a['pagine']} pag · {a['dimensione'] // 1024} KB")
        nome, dati = db.leggi_allegato_db(conn, a["id"], rif_tipo, rif_id)
        a2.download_button("Scarica", dati, file_name=nome, mime="application/pdf",
                           key=f"{pref}_dl{a['id']}")
        if a3.button("✖", key=f"{pref}_rm{a['id']}"):
            db.elimina_allegato(conn, a["id"], rif_tipo, rif_id)
            st.rerun()

    # ---- export ------------------------------------------------------------
    st.markdown("#### Esporta")
    vuoti = st.checkbox("Includi i campi non compilati", key=f"{pref}_vuoti")
    con_all = st.checkbox("Accoda gli allegati PDF", key=f"{pref}_conall",
                          disabled=not allegati)
    pdf = genera_pdf(doc, intestazione=intestazione, includi_vuoti=vuoti, margini=margini)
    if con_all and allegati:
        pdf = unisci_pdf(pdf, [db.leggi_allegato_db(conn, a["id"], rif_tipo, rif_id)[1]
                               for a in allegati])
    nome_out = f"{doc.tipo}_{(doc.contenuto.get('soggetto') or 'documento').replace(' ', '_')}.pdf"
    e1, e2 = st.columns(2)
    e1.download_button("⬇️ Scarica PDF", pdf, file_name=nome_out, mime="application/pdf",
                       key=f"{pref}_exp", type="primary")
    if salva_esportato and e2.button(etichetta_salva, key=f"{pref}_arch"):
        if salva_esportato(nome_out, pdf, doc):
            st.success("Copia salvata.")
