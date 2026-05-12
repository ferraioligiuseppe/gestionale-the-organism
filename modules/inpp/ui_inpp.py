# -*- coding: utf-8 -*-
"""
UI Streamlit del modulo INPP.

Architettura:
- Schermata "lista valutazioni" del paziente attivo
- Bottone "Nuova valutazione" → apre l'editor
- Editor → tabs per le 10 sezioni del protocollo, calcoli automatici, salvataggio
- Possibilità di rieditare valutazioni esistenti
- Possibilità di agganciare un URL YouTube della seduta al record
- Tracking automatico in background (created_by/updated_by + snapshot storico):
  gestito interamente da db_inpp.salva_valutazione; qui ci limitiamo a
  passargli lo username dell'utente loggato.
- UI Storico modifiche:
    * Visualizza una versione (sola lettura)
    * Ripristina soft: ricarica i valori nell'editor, non salva finché l'utente
      non clicca 💾 Salva (la "salvata di ripristino" crea a sua volta una
      nuova riga storico — niente perdita)
    * Diff: tabella delle prove con valori diversi rispetto allo stato corrente in DB

Il modulo è data-driven: la struttura delle sezioni e delle prove è in protocollo.py,
quindi questo file resta agnostico rispetto al contenuto clinico.
"""

import functools
from datetime import date
from typing import Optional

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
# HELPERS
# =============================================================================

def _get_username() -> Optional[str]:
    """
    Estrae lo username dell'utente loggato.
    Restituisce None se non c'è autenticazione attiva (es. sviluppo locale).
    """
    u = st.session_state.get("user")
    if isinstance(u, dict):
        v = u.get("username")
        return str(v).strip() if v else None
    return None


@functools.lru_cache(maxsize=1)
def _label_index() -> dict[str, dict]:
    """
    Indice id_prova → {label, scoring, sezione, gruppo}.
    Cache-ato: il protocollo è statico in memoria.
    """
    idx = {}
    for sezione in PROTOCOLLO_INPP:
        for gruppo in sezione["gruppi"]:
            for prova in gruppo["prove"]:
                idx[prova["id"]] = {
                    "label": prova.get("label", prova["id"]),
                    "scoring": prova.get("scoring", "0-4"),
                    "sezione": sezione.get("label", ""),
                    "gruppo": gruppo.get("label", ""),
                }
    return idx


def _format_valore(pid: str, valore) -> str:
    """Rappresentazione human-readable di un valore di prova per il diff."""
    if valore is None or valore == "" or valore == "—":
        return "—"
    info = _label_index().get(pid, {})
    scoring = info.get("scoring", "0-4")
    if scoring == "0-4":
        try:
            v = int(valore)
            etichetta = SCORING_LABELS.get(v, "")
            etichetta = etichetta.split("/")[0].strip() if etichetta else ""
            return f"{v}" + (f" — {etichetta}" if etichetta else "")
        except (TypeError, ValueError):
            return str(valore)
    return str(valore)


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
                # Icona 🎥 se è presente un video della seduta
                video_badge = " 🎥" if v.get("video_seduta_url") else ""
                st.markdown(f"**{v['data_valutazione'].strftime('%d/%m/%Y')}**{video_badge}")
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

    # ── SALT per consentire restore di una versione storica ──────────
    # Quando si ripristina una versione, incrementiamo salt: tutte le key
    # widget cambiano e i nuovi widget partono da `value=` (cioè dai valori
    # ripristinati) invece che dalla session_state stale.
    salt_key = f"_inpp_salt_{val_id}"
    if salt_key not in st.session_state:
        st.session_state[salt_key] = 0

    # ── Gestione restore pendente ─────────────────────────────────────
    restore_pending_key = f"_inpp_restore_pending_{val_id}"
    restored_versione = None
    if restore_pending_key in st.session_state:
        versione = st.session_state.pop(restore_pending_key)
        if versione:
            # Sovrascrivo val_caricata con i campi della versione storica
            val_caricata = {
                **val_caricata,
                "data_valutazione": versione.get("data_valutazione") or val_caricata.get("data_valutazione"),
                "terapista": versione.get("terapista"),
                "motivo": versione.get("motivo"),
                "risultati": versione.get("risultati") or {},
                "note_finali": versione.get("note_finali"),
                "video_seduta_url": versione.get("video_seduta_url"),
            }
            # Resetto la session_state dei valori delle prove
            st.session_state[f"_inpp_valori_{val_id}"] = dict(val_caricata["risultati"])
            # Incremento salt per buttare via le vecchie key widget
            st.session_state[salt_key] += 1
            restored_versione = versione.get("versione")

    salt = st.session_state[salt_key]

    # Header con bottone indietro
    col_h1, col_h2 = st.columns([4, 1])
    with col_h1:
        titolo = "Nuova valutazione" if val_id is None else f"Valutazione del {val_caricata['data_valutazione'].strftime('%d/%m/%Y')}"
        st.markdown(f"### {titolo} — {paziente_nome}")
    with col_h2:
        if st.button("← Lista", use_container_width=True):
            st.session_state[edit_key] = None
            st.rerun()

    # Banner di restore in corso
    if restored_versione is not None:
        st.warning(
            f"↩️ **Versione {restored_versione} caricata nell'editor.** "
            f"Modifica se necessario e clicca **💾 Salva** per confermare. "
            f"Lo stato attuale in DB verrà archiviato come nuova versione."
        )

    st.divider()

    # ----- Dati di intestazione -----
    st.markdown("#### Dati della valutazione")
    c1, c2 = st.columns(2)
    with c1:
        data_val = st.date_input(
            "Data valutazione",
            value=val_caricata.get("data_valutazione") or date.today(),
            key=f"inpp_data_{val_id}_{salt}",
            format="DD/MM/YYYY",
        )
    with c2:
        terapista = st.text_input(
            "Terapista",
            value=val_caricata.get("terapista") or "",
            key=f"inpp_terapista_{val_id}_{salt}",
        )
    motivo = st.text_area(
        "Motivo della valutazione",
        value=val_caricata.get("motivo") or "",
        height=80,
        key=f"inpp_motivo_{val_id}_{salt}",
    )

    # ----- Video della seduta (URL YouTube) -----
    video_seduta_url = st.text_input(
        "🎥 Video della seduta (URL YouTube)",
        value=val_caricata.get("video_seduta_url") or "",
        placeholder="https://youtu.be/abc123xyz  oppure  https://www.youtube.com/watch?v=...",
        help=(
            "Incolla qui l'URL YouTube del video della seduta. "
            "Suggerimento: caricare il video come 'Non in elenco' per mantenerlo "
            "riservato ma riproducibile dal gestionale."
        ),
        key=f"inpp_video_seduta_{val_id}_{salt}",
    )
    if video_seduta_url and video_seduta_url.strip().lower().startswith(("http://", "https://")):
        with st.expander("▶️ Anteprima video", expanded=False):
            try:
                st.video(video_seduta_url.strip())
            except Exception as e:
                st.caption(f"⚠️ video non riproducibile: {e}")
                st.caption(f"Link: {video_seduta_url.strip()}")

    st.divider()

    # ----- Sezioni del protocollo -----
    st.markdown("#### Compilazione")

    valori_key = f"_inpp_valori_{val_id}"
    if valori_key not in st.session_state:
        st.session_state[valori_key] = dict(val_caricata.get("risultati") or {})
    valori: dict = st.session_state[valori_key]

    tab_labels = [f"{s.get('icon', '•')} {_short_label(s['label'])}" for s in PROTOCOLLO_INPP]
    tabs = st.tabs(tab_labels)

    for tab, sezione in zip(tabs, PROTOCOLLO_INPP):
        with tab:
            _render_sezione(sezione, valori, salt)

    st.divider()

    # ----- Note finali -----
    note_finali = st.text_area(
        "Note finali / interpretazione",
        value=val_caricata.get("note_finali") or "",
        height=120,
        key=f"inpp_note_{val_id}_{salt}",
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
                    video_seduta_url=video_seduta_url,
                    username=_get_username(),
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

    # ----- Storico modifiche (solo se la valutazione esiste già) -----
    if val_id is not None:
        st.divider()
        _render_storico(conn, val_id, val_caricata)


# =============================================================================
# STORICO MODIFICHE
# =============================================================================

def _render_storico(conn, val_id: int, val_caricata: dict):
    """
    Sezione 'Storico modifiche': lista versioni precedenti con azioni
    visualizza / ripristina / diff.
    """
    versioni = db_inpp.lista_versioni_storico(conn, val_id)

    if not versioni:
        with st.expander("🕓 Storico modifiche (0)", expanded=False):
            st.caption(
                "Nessuna modifica registrata. Lo storico viene popolato "
                "automaticamente dal secondo salvataggio in poi."
            )
        return

    with st.expander(f"🕓 Storico modifiche ({len(versioni)})", expanded=False):
        st.caption(
            f"Lo stato corrente in DB è stato modificato l'ultima volta il "
            f"**{val_caricata.get('updated_at').strftime('%d/%m/%Y %H:%M') if val_caricata.get('updated_at') else '—'}**"
            f" da **{val_caricata.get('updated_by') or '—'}**."
        )
        st.markdown("")

        # ── View / Diff / Restore pendenti ──────────────────────────
        view_key = f"_inpp_view_storico_{val_id}"
        diff_key = f"_inpp_diff_storico_{val_id}"
        confirm_restore_key = f"_inpp_confirm_restore_{val_id}"

        # Mostra anteprima versione (sola lettura)
        if view_key in st.session_state:
            _render_view_versione(conn, val_id, st.session_state[view_key])

        # Mostra diff
        if diff_key in st.session_state:
            _render_diff_versione(conn, val_id, st.session_state[diff_key], val_caricata)

        # ── Lista versioni ──────────────────────────────────────────
        for ver in versioni:
            with st.container(border=True):
                cv1, cv2, cv3 = st.columns([3, 4, 4])
                with cv1:
                    archived_at = ver.get("archived_at")
                    archived_at_str = archived_at.strftime("%d/%m/%Y %H:%M") if archived_at else "—"
                    st.markdown(f"**Versione {ver['versione']}**")
                    st.caption(f"📅 {archived_at_str}")
                with cv2:
                    archived_by = ver.get("archived_by") or "—"
                    st.caption(f"👤 Modificata da: **{archived_by}**")
                    data_val = ver.get("data_valutazione")
                    if data_val:
                        st.caption(f"Data valutazione (in versione): {data_val.strftime('%d/%m/%Y')}")
                with cv3:
                    bb1, bb2, bb3 = st.columns(3)
                    with bb1:
                        if st.button("👁", key=f"view_st_{ver['id']}",
                                     help="Visualizza in sola lettura",
                                     use_container_width=True):
                            st.session_state[view_key] = ver["id"]
                            st.session_state.pop(diff_key, None)
                            st.rerun()
                    with bb2:
                        if st.button("📋", key=f"diff_st_{ver['id']}",
                                     help="Diff vs stato attuale",
                                     use_container_width=True):
                            st.session_state[diff_key] = ver["id"]
                            st.session_state.pop(view_key, None)
                            st.rerun()
                    with bb3:
                        if st.button("↩️", key=f"rest_st_{ver['id']}",
                                     help="Ripristina questa versione (richiede Salva)",
                                     use_container_width=True):
                            st.session_state[confirm_restore_key] = ver["id"]
                            st.rerun()

                # Conferma restore
                if st.session_state.get(confirm_restore_key) == ver["id"]:
                    st.warning(
                        f"Ripristinare la **versione {ver['versione']}**? "
                        f"I valori verranno caricati nell'editor sopra ma NON salvati "
                        f"finché non clicchi 💾 Salva."
                    )
                    cc1, cc2, _ = st.columns([1, 1, 4])
                    with cc1:
                        if st.button("Sì, ripristina", key=f"yes_rest_{ver['id']}", type="primary"):
                            versione_completa = db_inpp.carica_versione_storico(conn, ver["id"])
                            if versione_completa:
                                # Programmiamo il restore: verrà processato dall'editor al prossimo rerun
                                st.session_state[f"_inpp_restore_pending_{val_id}"] = versione_completa
                            st.session_state.pop(confirm_restore_key, None)
                            st.session_state.pop(view_key, None)
                            st.session_state.pop(diff_key, None)
                            st.rerun()
                    with cc2:
                        if st.button("Annulla", key=f"no_rest_{ver['id']}"):
                            st.session_state.pop(confirm_restore_key, None)
                            st.rerun()


def _render_view_versione(conn, val_id: int, storico_id: int):
    """Mostra una versione storica in sola lettura, dentro un container."""
    ver = db_inpp.carica_versione_storico(conn, storico_id)
    if not ver:
        st.caption("Versione non trovata.")
        return

    with st.container(border=True):
        ch1, ch2 = st.columns([5, 1])
        with ch1:
            archived_at = ver.get("archived_at")
            archived_at_str = archived_at.strftime("%d/%m/%Y %H:%M") if archived_at else "—"
            st.markdown(f"#### 👁 Anteprima versione {ver['versione']} — sola lettura")
            st.caption(f"Archiviata il {archived_at_str} da {ver.get('archived_by') or '—'}")
        with ch2:
            if st.button("✖ Chiudi", key=f"close_view_{val_id}", use_container_width=True):
                st.session_state.pop(f"_inpp_view_storico_{val_id}", None)
                st.rerun()

        # Metadati
        cm1, cm2 = st.columns(2)
        with cm1:
            data_v = ver.get("data_valutazione")
            st.markdown(
                f"**Data valutazione:** {data_v.strftime('%d/%m/%Y') if data_v else '—'}"
            )
        with cm2:
            st.markdown(f"**Terapista:** {ver.get('terapista') or '—'}")

        if ver.get("motivo"):
            st.markdown(f"**Motivo:** {ver['motivo']}")
        if ver.get("video_seduta_url"):
            st.markdown(f"**Video seduta:** {ver['video_seduta_url']}")
        if ver.get("note_finali"):
            st.markdown("**Note finali:**")
            st.write(ver["note_finali"])

        # Riepilogo
        ri = ver.get("riepilogo") or {}
        if ri:
            st.markdown("**Riepilogo punteggi:**")
            cols = st.columns(min(len(ri), 4))
            for i, (_sez_id, info) in enumerate(ri.items()):
                with cols[i % len(cols)]:
                    st.metric(
                        label=_short_label(info.get("label", "")),
                        value=f"{info.get('ottenuto', 0)}/{info.get('massimo', 0)}",
                        delta=f"{info.get('perc', 0)}%",
                        delta_color="off",
                    )

        # Valori compilati (raggruppati per sezione, solo prove valorizzate)
        risultati = ver.get("risultati") or {}
        valorizzati = {pid: v for pid, v in risultati.items()
                       if v is not None and v != "" and v != "—"}
        if valorizzati:
            st.markdown(f"**Prove compilate: {len(valorizzati)}**")
            with st.expander(f"Dettaglio prove ({len(valorizzati)})", expanded=False):
                idx = _label_index()
                # Raggruppa per sezione
                per_sez: dict[str, list[tuple]] = {}
                for pid, val in valorizzati.items():
                    info = idx.get(pid, {})
                    sez = info.get("sezione", "—")
                    per_sez.setdefault(sez, []).append((pid, info.get("label", pid), val))
                for sez_label, righe in per_sez.items():
                    st.markdown(f"*{sez_label}*")
                    for pid, label, val in righe:
                        st.caption(f"• {label}: **{_format_valore(pid, val)}**")


def _render_diff_versione(conn, val_id: int, storico_id: int, val_caricata: dict):
    """Confronta versione storica vs stato corrente in DB."""
    ver = db_inpp.carica_versione_storico(conn, storico_id)
    if not ver:
        st.caption("Versione non trovata.")
        return

    with st.container(border=True):
        ch1, ch2 = st.columns([5, 1])
        with ch1:
            st.markdown(f"#### 📋 Diff: versione {ver['versione']} → stato attuale in DB")
            st.caption(
                "Confronto rispetto allo stato salvato in DB. "
                "Modifiche non salvate nell'editor non vengono considerate."
            )
        with ch2:
            if st.button("✖ Chiudi", key=f"close_diff_{val_id}", use_container_width=True):
                st.session_state.pop(f"_inpp_diff_storico_{val_id}", None)
                st.rerun()

        # Diff metadati
        meta_diffs = []
        for campo, label_campo in [
            ("data_valutazione", "Data valutazione"),
            ("terapista", "Terapista"),
            ("motivo", "Motivo"),
            ("note_finali", "Note finali"),
            ("video_seduta_url", "Video seduta"),
        ]:
            v_stor = ver.get(campo)
            v_corr = val_caricata.get(campo)
            # normalizza per il confronto
            ns = v_stor if v_stor not in (None, "") else None
            nc = v_corr if v_corr not in (None, "") else None
            if ns != nc:
                # formatto le date
                if campo == "data_valutazione":
                    ns_str = ns.strftime('%d/%m/%Y') if ns else "—"
                    nc_str = nc.strftime('%d/%m/%Y') if nc else "—"
                else:
                    ns_str = str(ns) if ns else "—"
                    nc_str = str(nc) if nc else "—"
                meta_diffs.append((label_campo, ns_str, nc_str))

        if meta_diffs:
            st.markdown("**Metadati cambiati:**")
            for label_campo, ns, nc in meta_diffs:
                st.markdown(f"- **{label_campo}**: ~~{ns}~~ → **{nc}**")

        # Diff valori prove
        valori_storici = ver.get("risultati") or {}
        valori_correnti = val_caricata.get("risultati") or {}
        all_pids = set(valori_storici.keys()) | set(valori_correnti.keys())

        diffs = []
        idx = _label_index()
        for pid in all_pids:
            v_stor = valori_storici.get(pid)
            v_corr = valori_correnti.get(pid)
            # normalizza vuoti
            ns = v_stor if v_stor not in (None, "", "—") else None
            nc = v_corr if v_corr not in (None, "", "—") else None
            if ns != nc:
                info = idx.get(pid, {})
                diffs.append({
                    "sezione": info.get("sezione", "—"),
                    "label": info.get("label", pid),
                    "storica": _format_valore(pid, v_stor),
                    "corrente": _format_valore(pid, v_corr),
                })

        if not meta_diffs and not diffs:
            st.success("✓ Nessuna differenza tra questa versione storica e lo stato attuale.")
            return

        if diffs:
            st.markdown(f"**Prove con valore diverso: {len(diffs)}**")
            # Raggruppa per sezione per leggibilità
            per_sez: dict[str, list] = {}
            for d in diffs:
                per_sez.setdefault(d["sezione"], []).append(d)
            for sez_label, righe in per_sez.items():
                st.markdown(f"*{sez_label}*")
                for d in righe:
                    st.markdown(
                        f"- **{d['label']}**: ~~{d['storica']}~~ → **{d['corrente']}**"
                    )


# =============================================================================
# RENDER DI UNA SEZIONE
# =============================================================================

def _render_sezione(sezione: dict, valori: dict, salt: int):
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
                _render_prova(prova, valori, salt)


def _render_prova(prova: dict, valori: dict, salt: int):
    """Renderizza una singola prova in base al tipo di scoring."""
    pid = prova["id"]
    scoring = prova.get("scoring", "0-4")
    label = prova["label"]
    current = valori.get(pid)
    widget_key = f"prova_{pid}_{salt}"

    # ── Pannello guida clinica (istruzioni / osservazioni / video) ────
    has_istruzioni = bool(prova.get("istruzioni"))
    has_osservazioni = bool(prova.get("osservazioni"))
    has_scoring_spec = bool(prova.get("scoring_specifico"))
    has_video = bool(prova.get("video_url"))

    if has_istruzioni or has_osservazioni or has_video or has_scoring_spec:
        with st.expander(f"📖 Guida — {label}", expanded=False):
            if has_istruzioni:
                st.markdown("**Istruzioni al paziente**")
                st.write(prova["istruzioni"])
            if has_osservazioni:
                st.markdown("**Osservazioni cliniche**")
                st.write(prova["osservazioni"])
            if has_scoring_spec:
                st.markdown("**Scoring specifico per questo test**")
                for k in sorted(prova["scoring_specifico"].keys()):
                    st.markdown(f"- **{k}** — {prova['scoring_specifico'][k]}")
            if has_video:
                st.markdown("**Video esplicativo**")
                try:
                    st.video(prova["video_url"])
                except Exception as e:
                    st.caption(f"⚠️ video non riproducibile: {e}")
                    st.caption(f"Link: {prova['video_url']}")
            if prova.get("posturale"):
                st.info(
                    "ℹ️ Riflesso **posturale**: clinicamente lo scoring si interpreta "
                    "al contrario (0 = riflesso assente, 4 = riflesso completo)."
                )

    # ── Widget di input vero e proprio ────────────────────────────────
    if scoring == "0-4":
        spec = prova.get("scoring_specifico") or {}
        try:
            idx = int(current) if current is not None else 0
            if idx < 0 or idx > 4:
                idx = 0
        except (TypeError, ValueError):
            idx = 0

        def _fmt(i):
            if i in spec:
                desc = spec[i]
                if len(desc) > 50:
                    desc = desc[:47] + "..."
                return f"{i} — {desc}"
            if i in SCORING_LABELS:
                return f"{i} — {SCORING_LABELS[i].split('/')[0].strip()}"
            return str(i)

        nuovo = st.radio(
            label,
            options=range(5),
            index=idx,
            format_func=_fmt,
            horizontal=False if spec else True,
            key=widget_key,
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
            label, options=opzioni, index=idx, horizontal=True, key=widget_key,
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
            label, options=opzioni, index=idx, horizontal=True, key=widget_key,
        )
        valori[pid] = nuovo if nuovo != "—" else None

    elif scoring == "scelta":
        opzioni = ["—"] + list(prova.get("opzioni", []))
        idx = 0
        if current in opzioni:
            idx = opzioni.index(current)
        nuovo = st.radio(
            label, options=opzioni, index=idx, horizontal=True, key=widget_key,
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
            key=widget_key,
        )
        valori[pid] = nuovo

    elif scoring == "testo":
        nuovo = st.text_input(
            label,
            value=current or "",
            key=widget_key,
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
