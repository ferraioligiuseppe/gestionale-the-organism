# -*- coding: utf-8 -*-
"""
modules/pecs/ui_pecs.py
-----------------------
Interfaccia Streamlit del modulo PECS.

Innesto nel gestionale:

    from modules.pecs import ui_pecs
    ui_pecs.render()                       # con selettore paziente interno
    ui_pecs.render(paziente_id=123)        # paziente gia' scelto dalla shell

studio_id e operatore vengono letti da st.session_state se non passati.

Studio The Organism - Dott. Giuseppe Ferraioli
"""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

import streamlit as st

from . import db_pecs as db
from . import pecs_contenuti as pc
from . import pdf_pecs

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None

VERDE = "#1D6B44"


# ---------------------------------------------------------------------------
# Contesto (studio_id / operatore)
# ---------------------------------------------------------------------------

def _studio_id(esplicito: Optional[int] = None) -> Optional[int]:
    if esplicito is not None:
        return int(esplicito)
    for chiave in ("studio_id", "id_studio", "current_studio_id"):
        v = st.session_state.get(chiave)
        if v:
            return int(v)
    return None


def _operatore(esplicito: Optional[str] = None) -> str:
    if esplicito:
        return esplicito
    for chiave in ("operatore", "utente", "username", "user_email"):
        v = st.session_state.get(chiave)
        if v:
            return str(v)
    return ""


def _chiave_prove(protocollo_id: int) -> str:
    return "pecs_prove_%s" % protocollo_id


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def render_pecs(conn, paziente_id):
    """Wrapper compatibile col router: prende (conn, paz_id) come gli altri moduli."""
    import streamlit as st
    from . import db_pecs
    db_pecs.configura(get_connection=lambda: conn, chiudi_connessione=False)
    try:
        conn.rollback()
    except Exception:
        pass
    try:
        db_pecs.inizializza_schema()
    except Exception as e:
        st.error(f"Errore inizializzazione schema PECS: {e}")
        try:
            conn.rollback()
        except Exception:
            pass
        return
    studio_id = None
    try:
        cur = conn.cursor()
        cur.execute("SELECT current_setting('app.current_studio', true)::bigint")
        row = cur.fetchone()
        studio_id = row[0] if row else None
    except Exception:
        try: conn.rollback()
        except Exception: pass
    st.session_state["studio_id"] = studio_id
    render(studio_id=studio_id, paziente_id=paziente_id)


def render(studio_id: Optional[int] = None, paziente_id: Optional[int] = None,
           operatore: Optional[str] = None) -> None:
    sid = _studio_id(studio_id)
    op = _operatore(operatore)

    st.markdown(
        "## <span style='color:%s'>PECS</span> &middot; "
        "<span style='font-size:0.6em;color:#6b6b6b'>Picture Exchange "
        "Communication System</span>" % VERDE, unsafe_allow_html=True)

    if sid is None:
        st.error("Studio non identificato: studio_id assente in sessione.")
        return

    # --- selezione paziente ---
    if paziente_id is None:
        try:
            pazienti = db.lista_pazienti(sid)
        except Exception as e:
            st.error("Impossibile leggere l'anagrafica pazienti: %s" % e)
            return
        if not pazienti:
            st.info("Nessun paziente in anagrafica.")
            return
        etichette = {p["id"]: "%s %s" % (p.get("cognome") or "",
                                         p.get("nome") or "") for p in pazienti}
        paziente_id = st.selectbox("Paziente", list(etichette.keys()),
                                   format_func=lambda i: etichette[i],
                                   key="pecs_sel_paziente")

    paziente = db.get_paziente(sid, paziente_id)
    protocollo = db.get_protocollo_attivo(sid, paziente_id)

    if protocollo is None:
        _avvio_protocollo(sid, paziente_id, op)
        return

    fase_corrente = protocollo["fase_corrente"]
    st.caption("Protocollo avviato il %s &middot; fase attuale: **%s**"
               % (protocollo["data_inizio"].strftime("%d/%m/%Y"),
                  pc.etichetta_fase(fase_corrente)))

    tabs = st.tabs(["Sessione", "Andamento e criterio", "Rinforzatori",
                    "Scheda della fase", "Vocabolario", "Report", "Protocollo"])

    with tabs[0]:
        _tab_sessione(sid, protocollo, op)
    with tabs[1]:
        _tab_andamento(sid, protocollo, op)
    with tabs[2]:
        _tab_rinforzatori(sid, protocollo)
    with tabs[3]:
        _tab_scheda(fase_corrente)
    with tabs[4]:
        _tab_vocabolario(sid, protocollo)
    with tabs[5]:
        _tab_report(sid, protocollo, paziente, op)
    with tabs[6]:
        _tab_protocollo(sid, protocollo)


# ---------------------------------------------------------------------------
# Avvio protocollo
# ---------------------------------------------------------------------------

def _avvio_protocollo(sid: int, paziente_id: int, op: str) -> None:
    st.info("Nessun protocollo PECS attivo per questo paziente.")
    with st.form("pecs_nuovo_protocollo"):
        data_inizio = st.date_input("Data di inizio", value=date.today())
        obiettivo = st.text_area(
            "Obiettivo comunicativo",
            placeholder="Es. richiesta funzionale di item preferiti in autonomia "
                        "nei contesti di casa e studio")
        note = st.text_area("Note iniziali", placeholder="Valutazione dei rinforzatori, "
                                                         "contesti, figure coinvolte")
        if st.form_submit_button("Avvia protocollo dalla Fase I", type="primary"):
            try:
                db.crea_protocollo(sid, paziente_id, operatore=op,
                                   data_inizio=data_inizio,
                                   obiettivo=obiettivo, note=note)
                st.success("Protocollo avviato.")
                st.rerun()
            except Exception as e:
                st.error("Errore nella creazione del protocollo: %s" % e)


# ---------------------------------------------------------------------------
# Tab: sessione
# ---------------------------------------------------------------------------

def _tab_sessione(sid: int, protocollo: Dict[str, Any], op: str) -> None:
    pid = protocollo["id"]
    fase_default = protocollo["fase_corrente"]

    c1, c2, c3 = st.columns(3)
    with c1:
        fase = st.selectbox("Fase lavorata", pc.ORDINE_FASI,
                            index=pc.ORDINE_FASI.index(fase_default),
                            format_func=pc.etichetta_fase, key="pecs_fase_sess")
        data_sess = st.date_input("Data", value=date.today(), key="pecs_data_sess")
    with c2:
        partner = st.text_input("Partner comunicativo", key="pecs_partner")
        prompter = st.text_input("Prompter fisico", key="pecs_prompter")
    with c3:
        contesto = st.text_input("Contesto", placeholder="studio / casa / mensa",
                                 key="pecs_contesto")
        operatore = st.text_input("Operatore", value=op, key="pecs_operatore")

    rinforzatori = db.lista_rinforzatori(sid, pid, solo_attivi=True)
    item_usati = st.multiselect("Item utilizzati",
                                [r["item"] for r in rinforzatori],
                                key="pecs_item_usati")
    if not rinforzatori:
        st.caption("Nessun rinforzatore attivo: inseriscili nella scheda "
                   "«Rinforzatori».")

    st.divider()

    # --- contatore prove ---
    st.markdown("**Registrazione delle prove**")
    chiave = _chiave_prove(pid)
    st.session_state.setdefault(chiave, [])
    prove: List[Dict[str, Any]] = st.session_state[chiave]

    b1, b2, b3, b4, b5 = st.columns([1, 1, 1, 0.7, 0.7])
    item_corrente = item_usati[0] if len(item_usati) == 1 else None
    if b1.button("Autonoma", use_container_width=True, key="pecs_b_auto"):
        prove.append({"esito": "autonoma", "item": item_corrente})
    if b2.button("Con prompt", use_container_width=True, key="pecs_b_prompt"):
        prove.append({"esito": "prompt", "item": item_corrente})
    if b3.button("Errore", use_container_width=True, key="pecs_b_err"):
        prove.append({"esito": "errore", "item": item_corrente})
    if b4.button("Annulla", use_container_width=True, key="pecs_b_undo") and prove:
        prove.pop()
    if b5.button("Azzera", use_container_width=True, key="pecs_b_reset"):
        st.session_state[chiave] = []
        prove = st.session_state[chiave]

    n_tot = len(prove)
    n_auto = sum(1 for p in prove if p["esito"] == "autonoma")
    m1, m2, m3 = st.columns(3)
    m1.metric("Opportunita'", n_tot)
    m2.metric("Autonome", n_auto)
    m3.metric("Autonomia", "%.0f%%" % (100.0 * n_auto / n_tot) if n_tot else "-")
    if prove:
        st.caption(" ".join(
            {"autonoma": "A", "prompt": "P", "errore": "x"}[p["esito"]]
            for p in prove))

    manuale = st.checkbox("Inserimento manuale dei conteggi "
                          "(prove gia' raccolte su carta)", key="pecs_manuale")
    if manuale:
        q1, q2, q3 = st.columns(3)
        n_tot = q1.number_input("Opportunita'", min_value=0, value=n_tot or 0,
                                step=1, key="pecs_m_tot")
        n_auto = q2.number_input("Autonome", min_value=0, value=n_auto or 0,
                                 step=1, key="pecs_m_auto")
        n_prompt = q3.number_input("Con prompt", min_value=0, value=0, step=1,
                                   key="pecs_m_prompt")
    else:
        n_prompt = sum(1 for p in prove if p["esito"] == "prompt")

    st.divider()

    # --- parametri specifici di fase ---
    fase_obj = pc.get_fase(fase)
    st.markdown("**Parametri della %s**" % pc.etichetta_fase(fase))
    parametri: Dict[str, Any] = {}
    colonne = st.columns(2)
    for i, campo in enumerate(fase_obj.campi):
        col = colonne[i % 2]
        k = "pecs_par_%s_%s" % (fase, campo.chiave)
        with col:
            if campo.tipo == "bool":
                parametri[campo.chiave] = st.checkbox(
                    campo.etichetta, value=bool(campo.default), help=campo.aiuto, key=k)
            elif campo.tipo == "int":
                parametri[campo.chiave] = st.number_input(
                    campo.etichetta, min_value=0, value=int(campo.default or 0),
                    step=1, help=campo.aiuto, key=k)
            elif campo.tipo == "float":
                parametri[campo.chiave] = st.number_input(
                    campo.etichetta, min_value=0.0, value=float(campo.default or 0.0),
                    step=0.5, help=campo.aiuto, key=k)
            elif campo.tipo == "scelta":
                parametri[campo.chiave] = st.selectbox(
                    campo.etichetta, campo.opzioni or [],
                    index=(campo.opzioni or []).index(campo.default)
                    if campo.default in (campo.opzioni or []) else 0,
                    help=campo.aiuto, key=k)
            else:
                parametri[campo.chiave] = st.text_input(
                    campo.etichetta, value=str(campo.default or ""),
                    help=campo.aiuto, key=k)

    # --- checklist di fedelta' ---
    with st.expander("Checklist di fedelta' procedurale", expanded=False):
        fedelta: Dict[str, bool] = {}
        voci = pc.FEDELTA_COMUNE + fase_obj.fedelta
        for i, voce in enumerate(voci):
            fedelta[voce] = st.checkbox(voce, key="pecs_fed_%s_%d" % (fase, i))
        rispettate = sum(1 for v in fedelta.values() if v)
        st.caption("Fedelta': %d/%d voci" % (rispettate, len(voci)))

    note = st.text_area("Note sulla sessione", key="pecs_note_sess")

    if st.button("Salva sessione", type="primary", key="pecs_salva_sess"):
        if n_tot == 0:
            st.warning("Nessuna prova registrata: la sessione non e' stata salvata.")
            return
        if n_auto > n_tot:
            st.error("Le risposte autonome non possono superare le opportunita'.")
            return
        try:
            db.salva_sessione(
                sid, pid, fase,
                data_sessione=data_sess, operatore=operatore, partner=partner,
                prompter=prompter, contesto=contesto, item_usati=item_usati,
                prove=None if manuale else prove,
                n_opportunita=n_tot, n_autonome=n_auto, n_prompt=n_prompt,
                n_errori=max(0, n_tot - n_auto - n_prompt),
                parametri=parametri, fedelta=fedelta, note=note,
            )
            st.session_state[chiave] = []
            st.success("Sessione salvata.")
            st.rerun()
        except Exception as e:
            st.error("Errore nel salvataggio: %s" % e)


# ---------------------------------------------------------------------------
# Tab: andamento e criterio
# ---------------------------------------------------------------------------

def _tab_andamento(sid: int, protocollo: Dict[str, Any], op: str) -> None:
    pid = protocollo["id"]
    fase = protocollo["fase_corrente"]

    sessioni_fase = db.lista_sessioni(sid, pid, fase=fase)
    esito = pc.valuta_criterio(fase, sessioni_fase)

    st.markdown("**Criterio di passaggio &mdash; %s**" % pc.etichetta_fase(fase))
    st.caption(pc.get_fase(fase).criterio_testo)

    for r in esito.requisiti:
        icona = ":green[OK]" if r.soddisfatto else ":red[da raggiungere]"
        st.write("- %s &mdash; %s  \n  <span style='color:#6b6b6b;font-size:0.85em'>%s</span>"
                 % (r.etichetta, icona, r.valore or ""), unsafe_allow_html=True)

    prossima = pc.fase_successiva(fase)
    st.divider()

    if esito.soddisfatto and prossima:
        st.success("Criterio soddisfatto: e' possibile passare alla %s."
                   % pc.etichetta_fase(prossima))
        if st.button("Registra il passaggio alla %s" % pc.etichetta_fase(prossima),
                     type="primary", key="pecs_passa"):
            _registra_passaggio(sid, pid, fase, prossima, True, False, "", esito, op)
    elif esito.soddisfatto and not prossima:
        st.success("Fase VI completata: protocollo PECS concluso.")
        if st.button("Segna il protocollo come concluso", key="pecs_concludi"):
            db.aggiorna_protocollo(sid, pid, stato="concluso")
            st.rerun()
    elif prossima:
        with st.expander("Forzare comunque il passaggio alla %s"
                         % pc.etichetta_fase(prossima)):
            st.warning("Il criterio non e' soddisfatto. Il passaggio forzato "
                       "resta tracciato nello storico con la motivazione.")
            motivo = st.text_area("Motivazione clinica", key="pecs_motivo_forz")
            if st.button("Forza il passaggio", key="pecs_forza"):
                if not motivo.strip():
                    st.error("La motivazione e' obbligatoria per un passaggio forzato.")
                else:
                    _registra_passaggio(sid, pid, fase, prossima, False, True,
                                        motivo, esito, op)

    # --- grafico ---
    st.divider()
    dati = db.andamento(sid, pid)
    if dati and pd is not None:
        df = pd.DataFrame(dati)
        df["data"] = pd.to_datetime(df["data"])
        st.markdown("**Percentuale di risposte autonome**")
        st.line_chart(df.set_index("data")["percentuale"])
    elif dati:
        st.table(dati)

    # --- storico sessioni ---
    tutte = db.lista_sessioni(sid, pid)
    if tutte:
        st.markdown("**Sessioni registrate**")
        righe = [{
            "Data": s["data"],
            "Fase": s["fase"],
            "Partner": s.get("partner") or "",
            "Contesto": s.get("contesto") or "",
            "Prove": s.get("n_opportunita") or 0,
            "Autonome": s.get("n_autonome") or 0,
            "%": round(100.0 * (s.get("n_autonome") or 0) / (s["n_opportunita"] or 1), 0)
            if s.get("n_opportunita") else 0,
        } for s in tutte]
        st.dataframe(pd.DataFrame(righe) if pd is not None else righe,
                     use_container_width=True, hide_index=True)

    trans = db.lista_transizioni(sid, pid)
    if trans:
        with st.expander("Storico dei passaggi di fase"):
            for t in trans:
                nota = t.get("motivazione") or ""
                st.write("- **%s** &nbsp; %s &rarr; %s %s %s" % (
                    t["data"].strftime("%d/%m/%Y"), t.get("da_fase") or "avvio",
                    t["a_fase"], "(forzato)" if t.get("forzata") else "",
                    "- %s" % nota if nota else ""))


def _registra_passaggio(sid, pid, da_fase, a_fase, soddisfatto, forzata,
                        motivo, esito, op) -> None:
    evidenza = {"requisiti": [{"etichetta": r.etichetta,
                               "soddisfatto": r.soddisfatto,
                               "valore": str(r.valore)} for r in esito.requisiti],
                "sessioni_valutate": esito.sessioni_valutate}
    try:
        db.registra_transizione(sid, pid, da_fase, a_fase, soddisfatto,
                                forzata=forzata, motivazione=motivo,
                                evidenza=evidenza, operatore=op)
        st.success("Passaggio registrato: ora sei in %s." % pc.etichetta_fase(a_fase))
        st.rerun()
    except Exception as e:
        st.error("Errore nella registrazione del passaggio: %s" % e)


# ---------------------------------------------------------------------------
# Tab: rinforzatori
# ---------------------------------------------------------------------------

def _tab_rinforzatori(sid: int, protocollo: Dict[str, Any]) -> None:
    pid = protocollo["id"]

    scaduti = db.rinforzatori_da_riverificare(sid, pid, giorni=7)
    if scaduti:
        st.warning("Da riverificare (ultima verifica oltre 7 giorni fa): %s"
                   % ", ".join(r["item"] for r in scaduti))

    with st.form("pecs_nuovo_rinf", clear_on_submit=True):
        c1, c2, c3 = st.columns([2, 1.4, 1])
        item = c1.text_input("Item")
        categoria = c2.text_input("Categoria", placeholder="cibo / gioco / attivita'")
        gerarchia = c3.number_input("Gerarchia", min_value=1, max_value=20, value=1,
                                    step=1, help="1 = piu' preferito")
        note = st.text_input("Note", placeholder="modalita' di verifica, durata accesso")
        if st.form_submit_button("Aggiungi rinforzatore"):
            if item.strip():
                db.aggiungi_rinforzatore(sid, pid, item, categoria, int(gerarchia),
                                         note=note)
                st.rerun()
            else:
                st.error("Indica l'item.")

    elenco = db.lista_rinforzatori(sid, pid)
    if not elenco:
        st.info("Nessun rinforzatore registrato. La valutazione delle preferenze "
                "e' il prerequisito della Fase I.")
        return

    for r in elenco:
        c1, c2, c3, c4 = st.columns([3, 1.4, 1.4, 1])
        c1.write("**%s**%s" % (r["item"],
                               " &middot; %s" % r["categoria"] if r.get("categoria") else ""))
        c2.caption("gerarchia %s" % r["gerarchia"])
        c3.caption("verificato %s" % r["data_verifica"].strftime("%d/%m/%Y"))
        if c4.button("Riverifica", key="pecs_riv_%s" % r["id"]):
            db.aggiorna_rinforzatore(sid, r["id"], data_verifica=date.today())
            st.rerun()
        cA, cB = st.columns([1, 6])
        if cA.button("Disattiva" if r["attivo"] else "Riattiva",
                     key="pecs_att_%s" % r["id"]):
            db.aggiorna_rinforzatore(sid, r["id"], attivo=not r["attivo"])
            st.rerun()
        st.divider()


# ---------------------------------------------------------------------------
# Tab: scheda clinica della fase
# ---------------------------------------------------------------------------

def _tab_vocabolario(sid, protocollo) -> None:
    st.caption(
        "Pittogrammi ARASAAC (gratuiti per uso clinico) come punto di partenza. "
        "Puoi sostituire ciascuna card con una foto reale dell'item o del paziente "
        "— resta personale per questo paziente."
    )
    paziente_id = protocollo["paziente_id"]
    categorie = ["Tutte"] + pc.categorie_vocabolario()
    cat_scelta = st.selectbox("Categoria", categorie, key="pecs_voc_cat")
    items = [it for it in pc.VOCABOLARIO_INIZIALE
             if cat_scelta == "Tutte" or it.categoria == cat_scelta]

    cols = st.columns(4)
    for i, item in enumerate(items):
        with cols[i % 4]:
            foto = db.get_foto_item(sid, paziente_id, item.nome)
            if foto:
                st.image(foto, use_container_width=True)
            else:
                st.image(pc.url_arasaac(item.arasaac_id), use_container_width=True)
            st.caption(f"**{item.nome}**")
            up = st.file_uploader("Sostituisci con una foto", type=["png", "jpg", "jpeg"],
                                  key=f"pecs_upl_{item.nome}", label_visibility="collapsed")
            if up is not None:
                db.salva_foto_item(sid, paziente_id, item.nome, up.getvalue())
                st.rerun()
            if foto and st.button("Ripristina pittogramma", key=f"pecs_reset_{item.nome}"):
                db.elimina_foto_item(sid, paziente_id, item.nome)
                st.rerun()


def _tab_scheda(fase_corrente: str) -> None:
    fase = st.selectbox("Fase", pc.ORDINE_FASI,
                        index=pc.ORDINE_FASI.index(fase_corrente),
                        format_func=pc.etichetta_fase, key="pecs_scheda_fase")
    f = pc.get_fase(fase)

    st.markdown("#### %s" % pc.etichetta_fase(fase))
    st.info(f.obiettivo)

    st.markdown("**Operatori**")
    st.write(f.operatori)

    st.markdown("**Materiali**")
    for m in f.materiali:
        st.write("- %s" % m)

    st.markdown("**Procedura**")
    for p in f.procedura:
        st.write("- %s" % p)

    st.markdown("**Gestione del prompt**")
    for p in f.prompt:
        st.write("- %s" % p)

    st.markdown("**Errori da evitare**")
    for e in f.errori:
        st.write("- %s" % e)

    st.success("**Criterio di passaggio** &mdash; %s" % f.criterio_testo)


# ---------------------------------------------------------------------------
# Tab: report PDF
# ---------------------------------------------------------------------------

def _tab_report(sid: int, protocollo: Dict[str, Any],
                paziente: Optional[Dict[str, Any]], op: str) -> None:
    pid = protocollo["id"]
    fase = protocollo["fase_corrente"]

    sessioni = db.lista_sessioni(sid, pid)
    trans = db.lista_transizioni(sid, pid)
    esito = pc.valuta_criterio(fase, [s for s in sessioni if s["fase"] == fase])

    carta = st.session_state.get("carta_intestata")  # caricata al login
    if st.button("Genera report PDF", type="primary", key="pecs_gen_pdf"):
        try:
            dati = pdf_pecs.genera_report(protocollo, paziente, sessioni, trans,
                                          esito, operatore=op, carta_intestata=carta)
            nome = "PECS_%s_%s.pdf" % (
                (paziente or {}).get("cognome", "paziente"),
                protocollo["data_inizio"].strftime("%Y%m%d"))
            st.download_button("Scarica il report", data=dati, file_name=nome,
                               mime="application/pdf", key="pecs_dl_pdf")
        except Exception as e:
            st.error("Errore nella generazione del PDF: %s" % e)


# ---------------------------------------------------------------------------
# Tab: gestione protocollo
# ---------------------------------------------------------------------------

def _tab_protocollo(sid: int, protocollo: Dict[str, Any]) -> None:
    pid = protocollo["id"]
    with st.form("pecs_form_protocollo"):
        obiettivo = st.text_area("Obiettivo comunicativo",
                                 value=protocollo.get("obiettivo") or "")
        note = st.text_area("Note", value=protocollo.get("note") or "")
        stato = st.selectbox("Stato", ["attivo", "sospeso", "concluso"],
                             index=["attivo", "sospeso", "concluso"].index(
                                 protocollo.get("stato", "attivo")))
        if st.form_submit_button("Aggiorna"):
            db.aggiorna_protocollo(sid, pid, obiettivo=obiettivo, note=note,
                                   stato=stato)
            st.success("Protocollo aggiornato.")
            st.rerun()

    with st.expander("Correzione manuale della fase"):
        st.caption("Da usare solo per correggere un errore di inserimento: "
                   "non registra una transizione nello storico.")
        nuova = st.selectbox("Fase corrente", pc.ORDINE_FASI,
                             index=pc.ORDINE_FASI.index(protocollo["fase_corrente"]),
                             format_func=pc.etichetta_fase, key="pecs_corr_fase")
        if st.button("Correggi", key="pecs_corr_btn"):
            db.aggiorna_protocollo(sid, pid, fase_corrente=nuova)
            st.rerun()
