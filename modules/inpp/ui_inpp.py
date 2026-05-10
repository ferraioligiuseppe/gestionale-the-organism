# -*- coding: utf-8 -*-
"""
UI Streamlit del modulo INPP.

Architettura:
- Schermata "lista valutazioni" del paziente attivo
- Bottone "Nuova valutazione" → apre l'editor
- Editor → tabs per le 10 sezioni del protocollo, calcoli automatici, salvataggio
- Possibilità di rieditare valutazioni esistenti

Il modulo è data-driven: la struttura delle sezioni e delle prove è in protocollo.py,
quindi questo file resta agnostico rispetto al contenuto clinico.
"""

from datetime import date
import streamlit as st

from . import db_inpp
from .protocollo import (
    PROTOCOLLO_INPP,
    SCORING_LABELS,
    riepilogo_punteggi,
    calcola_punteggio_sezione,
)

try:
    # PDF è opzionale: se manca reportlab non rompiamo il modulo
    from . import pdf_inpp
    _PDF_DISPONIBILE = True
except Exception:
    _PDF_DISPONIBILE = False


# =============================================================================
# ENTRY POINT
# =============================================================================

def render_inpp(conn, paziente_id: int, paziente_nome: str) -> None:
    """
    Entry point del modulo INPP. Da chiamare dal router dopo l'header
    paziente_attivo.
    """
    db_inpp.ensure_schema(conn)

    st.markdown(
        "## 🧬 INPP — Valutazione Diagnostica dello Sviluppo Neurologico"
    )
    st.caption(
        "Formulario INPP rev. 01/22 — 10 sezioni, ~150 prove. "
        "I totali per sezione vengono calcolati automaticamente solo sulle prove con scoring 0–4."
    )

    # Stato: stiamo editando una valutazione? (None = lista)
    edit_key = f"_inpp_edit_{paziente_id}"
    if edit_key not in st.session_state:
        st.session_state[edit_key] = None  # None = vista lista; "new" = nuova; <int> = id da editare

    modalita = st.session_state[edit_key]

    if modalita is None:
        _render_lista(conn, paziente_id, paziente_nome, edit_key)
    elif modalita == "new":
        _render_editor(conn, paziente_id, paziente_nome, edit_key, val_id=None)
    else:
        _render_editor(conn, paziente_id, paziente_nome, edit_key, val_id=int(modalita))


# =============================================================================
# VISTA LISTA
# =============================================================================

def _render_lista(conn, paziente_id: int, paziente_nome: str, edit_key: str):
    """Mostra le valutazioni esistenti + bottone nuova."""
    st.divider()

    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"### Valutazioni di **{paziente_nome}**")
    with col2:
        if st.button("➕ Nuova valutazione", type="primary", use_container_width=True):
            st.session_state[edit_key] = "new"
            st.rerun()

    valutazioni = db_inpp.lista_valutazioni(conn, paziente_id)

    if not valutazioni:
        st.info("Nessuna valutazione INPP registrata per questo paziente.")
        return

    st.markdown(f"**{len(valutazioni)}** valutazione/i registrata/e.")
    st.caption("")

    for v in valutazioni:
        with st.container(border=True):
            c1, c2, c3, c4 = st.columns([2, 2, 3, 2])
            with c1:
                st.markdown(f"**{v['data_valutazione'].strftime('%d/%m/%Y')}**")
                if v.get("terapista"):
                    st.caption(f"Terapista: {v['terapista']}")
            with c2:
                # Riepilogo dei punteggi: un mini riassunto
                ri = v.get("riepilogo") or {}
                if ri:
                    primi_due = list(ri.values())[:2]
                    for r in primi_due:
                        st.caption(f"{r.get('label', '')}: {r.get('ottenuto', 0)}/{r.get('massimo', 0)}")
                else:
                    st.caption("— senza punteggi —")
            with c3:
                if v.get("motivo"):
                    motivo = v["motivo"]
                    if len(motivo) > 120:
                        motivo = motivo[:117] + "..."
                    st.caption(motivo)
            with c4:
                if st.button("✏️ Apri", key=f"open_{v['id']}", use_container_width=True):
                    st.session_state[edit_key] = v["id"]
                    st.rerun()
                if st.button("🗑 Elimina", key=f"del_{v['id']}", use_container_width=True):
                    st.session_state[f"_confirm_del_inpp_{v['id']}"] = True
                    st.rerun()

            if st.session_state.get(f"_confirm_del_inpp_{v['id']}"):
                st.warning(f"Confermare eliminazione della valutazione del {v['data_valutazione'].strftime('%d/%m/%Y')}?")
                cdel1, cdel2, _ = st.columns([1, 1, 4])
                with cdel1:
                    if st.button("Sì, elimina", key=f"yes_{v['id']}", type="primary"):
                        db_inpp.elimina_valutazione(conn, v["id"])
                        st.session_state.pop(f"_confirm_del_inpp_{v['id']}", None)
                        st.success("Eliminata.")
                        st.rerun()
                with cdel2:
                    if st.button("Annulla", key=f"no_{v['id']}"):
                        st.session_state.pop(f"_confirm_del_inpp_{v['id']}", None)
                        st.rerun()


# =============================================================================
# EDITOR (form completo)
# =============================================================================

def _render_editor(conn, paziente_id: int, paziente_nome: str,
                   edit_key: str, val_id: int | None):
    """
    Editor di una valutazione INPP. val_id=None → nuova; altrimenti → modifica.
    """
    # Caricamento dati esistenti
    val_caricata: dict = {}
    if val_id is not None:
        val_caricata = db_inpp.carica_valutazione(conn, val_id) or {}
        if not val_caricata:
            st.error(f"Valutazione id={val_id} non trovata.")
            if st.button("← Torna alla lista"):
                st.session_state[edit_key] = None
                st.rerun()
            return

    # Header con bottone indietro
    col_h1, col_h2 = st.columns([4, 1])
    with col_h1:
        titolo = "Nuova valutazione" if val_id is None else f"Valutazione del {val_caricata['data_valutazione'].strftime('%d/%m/%Y')}"
        st.markdown(f"### {titolo} — {paziente_nome}")
    with col_h2:
        if st.button("← Lista", use_container_width=True):
            st.session_state[edit_key] = None
            st.rerun()

    st.divider()

    # ----- Dati di intestazione -----
    st.markdown("#### Dati della valutazione")
    c1, c2 = st.columns(2)
    with c1:
        data_val = st.date_input(
            "Data valutazione",
            value=val_caricata.get("data_valutazione") or date.today(),
            key=f"inpp_data_{val_id}",
            format="DD/MM/YYYY",
        )
    with c2:
        terapista = st.text_input(
            "Terapista",
            value=val_caricata.get("terapista") or "",
            key=f"inpp_terapista_{val_id}",
        )
    motivo = st.text_area(
        "Motivo della valutazione",
        value=val_caricata.get("motivo") or "",
        height=80,
        key=f"inpp_motivo_{val_id}",
    )

    st.divider()

    # ----- Sezioni del protocollo -----
    st.markdown("#### Compilazione")

    # Stato dei valori in session_state per non perderli al rerun
    valori_key = f"_inpp_valori_{val_id}"
    if valori_key not in st.session_state:
        st.session_state[valori_key] = dict(val_caricata.get("risultati") or {})
    valori: dict = st.session_state[valori_key]

    # Tabs delle 10 sezioni
    tab_labels = [f"{s.get('icon', '•')} {_short_label(s['label'])}" for s in PROTOCOLLO_INPP]
    tabs = st.tabs(tab_labels)

    for tab, sezione in zip(tabs, PROTOCOLLO_INPP):
        with tab:
            _render_sezione(sezione, valori)

    st.divider()

    # ----- Note finali -----
    note_finali = st.text_area(
        "Note finali / interpretazione",
        value=val_caricata.get("note_finali") or "",
        height=120,
        key=f"inpp_note_{val_id}",
    )

    st.divider()

    # ----- Riepilogo punteggi -----
    st.markdown("#### Riepilogo punteggi")
    riepilogo = riepilogo_punteggi(valori)
    if riepilogo:
        cols = st.columns(min(len(riepilogo), 4))
        for i, (sez_id, info) in enumerate(riepilogo.items()):
            with cols[i % len(cols)]:
                st.metric(
                    label=_short_label(info["label"]),
                    value=f"{info['ottenuto']}/{info['massimo']}",
                    delta=f"{info['perc']}%",
                    delta_color="off",
                )
    else:
        st.caption("I punteggi appaiono qui man mano che compili le sezioni.")

    st.divider()

    # ----- Salvataggio -----
    csave1, csave2, _ = st.columns([1, 2, 3])
    with csave1:
        if st.button("💾 Salva", type="primary", use_container_width=True, key=f"save_{val_id}"):
            try:
                new_id = db_inpp.salva_valutazione(
                    conn,
                    paziente_id=paziente_id,
                    data_valutazione=data_val,
                    terapista=terapista.strip() or None,
                    motivo=motivo.strip() or None,
                    risultati=valori,
                    riepilogo=riepilogo,
                    note_finali=note_finali.strip() or None,
                    val_id=val_id,
                )
                st.success(f"Valutazione salvata (id={new_id}).")
                # se era nuova, passiamo all'edit dell'esistente
                if val_id is None:
                    st.session_state[edit_key] = new_id
                    # ribattezzo i valori sotto la nuova chiave
                    st.session_state[f"_inpp_valori_{new_id}"] = valori
                    st.session_state.pop(f"_inpp_valori_None", None)
                    st.rerun()
            except Exception as e:
                st.error(f"Errore nel salvataggio: {e}")

    with csave2:
        if _PDF_DISPONIBILE and val_id is not None:
            if st.button("📄 Scarica PDF referto", use_container_width=True, key=f"pdf_{val_id}"):
                try:
                    pdf_bytes = pdf_inpp.genera_pdf_referto(
                        paziente_nome=paziente_nome,
                        data_valutazione=data_val,
                        terapista=terapista,
                        motivo=motivo,
                        valori=valori,
                        riepilogo=riepilogo,
                        note_finali=note_finali,
                    )
                    st.download_button(
                        label="Scarica PDF",
                        data=pdf_bytes,
                        file_name=f"INPP_{paziente_nome.replace(' ', '_')}_{data_val.strftime('%Y%m%d')}.pdf",
                        mime="application/pdf",
                        key=f"dl_{val_id}",
                    )
                except Exception as e:
                    st.error(f"Errore generazione PDF: {e}")
        elif not _PDF_DISPONIBILE:
            st.caption("PDF disponibile dopo aver caricato `pdf_inpp.py`.")
        else:
            st.caption("Salva prima per generare il PDF.")


# =============================================================================
# RENDER DI UNA SEZIONE
# =============================================================================

def _render_sezione(sezione: dict, valori: dict):
    """Renderizza una sezione del protocollo dentro un tab."""
    st.markdown(f"##### {sezione['label']}")

    if not sezione.get("no_total"):
        ott, mx = calcola_punteggio_sezione(sezione["id"], valori)
        if mx > 0:
            st.caption(f"Punteggio sezione: **{ott} / {mx}** ({round(100.0 * ott / mx, 1)}%)")

    for gruppo in sezione["gruppi"]:
        with st.container(border=True):
            st.markdown(f"**{gruppo['label']}**")
            for prova in gruppo["prove"]:
                _render_prova(prova, valori)


def _render_prova(prova: dict, valori: dict):
    """Renderizza una singola prova in base al tipo di scoring."""
    pid = prova["id"]
    scoring = prova.get("scoring", "0-4")
    label = prova["label"]
    current = valori.get(pid)

    if scoring == "0-4":
        # radio orizzontale 0-4
        opt_labels = [str(i) for i in range(5)]
        try:
            idx = int(current) if current is not None else 0
            if idx < 0 or idx > 4:
                idx = 0
        except (TypeError, ValueError):
            idx = 0
        nuovo = st.radio(
            label,
            options=range(5),
            index=idx,
            format_func=lambda i: f"{i} — {SCORING_LABELS[i].split('/')[0].strip()}" if i in SCORING_LABELS else str(i),
            horizontal=True,
            key=f"prova_{pid}",
        )
        valori[pid] = int(nuovo)

    elif scoring == "si_no":
        opzioni = ["—", "Sì", "No"]
        idx = 0
        if current == "Sì":
            idx = 1
        elif current == "No":
            idx = 2
        nuovo = st.radio(
            label, options=opzioni, index=idx, horizontal=True, key=f"prova_{pid}",
        )
        valori[pid] = nuovo if nuovo != "—" else None

    elif scoring == "lateralita":
        opzioni = ["—", "Sx", "Dx"]
        idx = 0
        if current == "Sx":
            idx = 1
        elif current == "Dx":
            idx = 2
        nuovo = st.radio(
            label, options=opzioni, index=idx, horizontal=True, key=f"prova_{pid}",
        )
        valori[pid] = nuovo if nuovo != "—" else None

    elif scoring == "scelta":
        opzioni = ["—"] + list(prova.get("opzioni", []))
        idx = 0
        if current in opzioni:
            idx = opzioni.index(current)
        nuovo = st.radio(
            label, options=opzioni, index=idx, horizontal=True, key=f"prova_{pid}",
        )
        valori[pid] = nuovo if nuovo != "—" else None

    elif scoring == "numerico":
        try:
            val = float(current) if current is not None else 0.0
        except (TypeError, ValueError):
            val = 0.0
        nuovo = st.number_input(
            label,
            value=val,
            step=1.0,
            format="%.1f",
            key=f"prova_{pid}",
        )
        valori[pid] = nuovo

    elif scoring == "testo":
        nuovo = st.text_input(
            label,
            value=current or "",
            key=f"prova_{pid}",
        )
        valori[pid] = nuovo or None

    else:
        st.caption(f"⚠️ tipo di scoring sconosciuto: {scoring}")


# =============================================================================
# UTILITY
# =============================================================================

def _short_label(label: str) -> str:
    """Accorcia label lunghe per le etichette dei tab."""
    cuts = {
        "Coordinazione grosso-motoria ed equilibrio": "Coordinazione",
        "Schemi di sviluppo motorio": "Sviluppo motorio",
        "Funzionalità cerebellare": "Cerebellare",
        "Disdiadococinesia": "Disdiadococin.",
        "Orientamento spaziale e propriocezione": "Orient./Propriocez.",
        "Riflessi dello sviluppo": "Riflessi",
        "Lateralità": "Lateralità",
        "Test oculo-motori": "Oculo-motori",
        "Test visuo-percettivi": "Visuo-percettivi",
        "Test di Goodenough (Indice di Aston)": "Goodenough",
    }
    return cuts.get(label, label)
