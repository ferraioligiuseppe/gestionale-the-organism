# -*- coding: utf-8 -*-
"""
modules/ui_professionisti.py — Pannello admin per gestire i professionisti abilitati.

Visibile solo agli utenti con ruolo admin. Raggiungibile da:
    Area Studio → 🩺 Professionisti abilitati

Funzionalità:
  - Lista professionisti con badge default/attivo
  - Form di creazione e modifica
  - Caricamento firma scansionata (PNG/JPG, ridimensionata automaticamente)
  - Imposta come default / Disattiva / Riattiva / Cancella
  - Anteprima della firma caricata
"""

from __future__ import annotations

import io
from datetime import datetime
from typing import Optional

import streamlit as st

from vision_manager import professionisti_db as P


# Limiti per l'upload firma
MAX_FIRMA_BYTES = 500 * 1024            # 500 KB
MAX_FIRMA_LATO = 600                    # px (lato lungo)


# =============================================================================
#  ENTRY POINT
# =============================================================================

def render_professionisti(conn, is_admin: bool = True, current_user_id: Optional[int] = None):
    """Punto di ingresso del pannello.

    Args:
        conn: connessione psycopg2 al DB
        is_admin: True per consentire la gestione (Vision Manager non ha auth oggi).
                  Lascia il parametro per futura integrazione con l'autenticazione.
        current_user_id: id dell'utente loggato (per audit). Lasciare None se non c'è auth.
    """
    st.markdown("# 🩺 Professionisti abilitati")
    st.caption("Anagrafica dei professionisti abilitati a firmare prescrizioni occhiali.")

    if not is_admin:
        st.error("⛔ Accesso negato. Solo gli admin possono gestire i professionisti.")
        return

    # Tabs: lista vs nuovo
    tab_lista, tab_nuovo = st.tabs(["📋 Elenco professionisti", "➕ Nuovo professionista"])

    with tab_lista:
        _render_lista(conn, current_user_id)

    with tab_nuovo:
        _render_form_nuovo(conn, current_user_id)


# =============================================================================
#  LISTA
# =============================================================================

def _render_lista(conn, current_user_id: Optional[int]):
    """Mostra la lista dei professionisti, con possibilità di modifica/azione."""

    # Toggle: mostra anche i disattivati?
    mostra_disattivati = st.checkbox("Mostra anche disattivati", value=False, key="presc_show_inactive")
    elenco = P.list_professionisti(conn, solo_attivi=not mostra_disattivati)

    if not elenco:
        st.info("Nessun professionista configurato. Vai sul tab **➕ Nuovo professionista** per crearne uno.")
        return

    st.markdown(f"**{len(elenco)}** professionisti"
                + (" (inclusi disattivati)" if mostra_disattivati else " attivi"))
    st.divider()

    # Riga per riga, con expander per ognuno
    for idx, p in enumerate(elenco):
        badge_default = " ⭐ **default**" if p["is_default"] else ""
        badge_attivo = "" if p["attivo"] else " 🚫 *disattivato*"
        badge_firma = " ✍️" if p["ha_firma"] else ""
        titolo = (
            f"#{p['id']} — {p['nome_completo']}"
            f"{badge_default}{badge_attivo}{badge_firma}"
        )

        with st.expander(titolo, expanded=False):
            _render_riga_professionista(conn, p, current_user_id)


def _render_riga_professionista(conn, p: dict, current_user_id: Optional[int]):
    """Render del singolo professionista dentro l'expander: form modifica + azioni."""

    pid = p["id"]

    # ── Form di modifica ──
    with st.form(key=f"form_edit_{pid}", clear_on_submit=False):
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome completo *", value=p["nome_completo"], key=f"nome_{pid}")
        ord_v = c2.number_input("Ordine in lista", min_value=0, value=p["ordine_visualizzazione"] or 0,
                                step=1, key=f"ord_{pid}")

        c1, c2 = st.columns(2)
        q1 = c1.text_input("Qualifica (riga 1)", value=p["qualifica_riga_1"] or "", key=f"q1_{pid}")
        q2 = c2.text_input("Qualifica (riga 2)", value=p["qualifica_riga_2"] or "", key=f"q2_{pid}")

        c1, c2 = st.columns(2)
        ord_albo = c1.text_input("Ordine / Albo", value=p["ordine_albo"] or "",
                                 placeholder="es. Ordine dei Medici di Salerno",
                                 key=f"ord_albo_{pid}")
        num_albo = c2.text_input("Numero albo", value=p["numero_albo"] or "",
                                 placeholder="es. n. 12345",
                                 key=f"num_albo_{pid}")

        c1, c2 = st.columns(2)
        email_p = c1.text_input("Email professionale", value=p["email_professionale"] or "",
                                key=f"email_{pid}")
        tel = c2.text_input("Telefono", value=p["telefono"] or "", key=f"tel_{pid}")

        salva = st.form_submit_button("💾 Salva modifiche", type="primary")

        if salva:
            try:
                P.aggiorna_professionista(
                    conn, pid,
                    nome_completo=nome,
                    qualifica_riga_1=q1,
                    qualifica_riga_2=q2,
                    ordine_albo=ord_albo,
                    numero_albo=num_albo,
                    email_professionale=email_p,
                    telefono=tel,
                    ordine_visualizzazione=ord_v,
                    updated_by=current_user_id,
                )
                st.success("✅ Modifiche salvate.")
                st.rerun()
            except Exception as e:
                st.error(f"Errore salvataggio: {e}")

    # ── Sezione FIRMA ──
    st.markdown("##### Firma scansionata")

    col_preview, col_upload = st.columns([1, 2])

    with col_preview:
        if p["ha_firma"]:
            firma_bytes = P.get_firma(conn, pid)
            if firma_bytes:
                st.image(firma_bytes, caption=p["firma_filename"] or "firma", width=200)
        else:
            st.caption("Nessuna firma caricata.")

    with col_upload:
        upload = st.file_uploader(
            "Carica nuova firma (PNG o JPG, max 500 KB)",
            type=["png", "jpg", "jpeg"],
            key=f"firma_upload_{pid}",
        )
        if upload is not None:
            firma_processed, errore = _processa_firma(upload)
            if errore:
                st.error(errore)
            else:
                st.image(firma_processed, caption="Anteprima processata", width=200)
                if st.button("💾 Salva questa firma", key=f"save_firma_{pid}"):
                    try:
                        P.carica_firma(conn, pid, firma_processed, upload.name, updated_by=current_user_id)
                        st.success("✅ Firma salvata.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Errore: {e}")

        if p["ha_firma"]:
            if st.button("🗑️ Rimuovi firma esistente", key=f"del_firma_{pid}"):
                P.cancella_firma(conn, pid, updated_by=current_user_id)
                st.success("Firma rimossa.")
                st.rerun()

    # ── Azioni rapide ──
    st.markdown("##### Azioni")
    c1, c2, c3 = st.columns(3)

    if not p["is_default"] and p["attivo"]:
        if c1.button("⭐ Rendi default", key=f"def_{pid}"):
            P.imposta_default(conn, pid, updated_by=current_user_id)
            st.success(f"{p['nome_completo']} è ora il professionista di default.")
            st.rerun()

    if p["attivo"]:
        if c2.button("🚫 Disattiva", key=f"deact_{pid}"):
            P.disattiva_professionista(conn, pid, updated_by=current_user_id)
            st.success("Disattivato.")
            st.rerun()
    else:
        if c2.button("✅ Riattiva", key=f"react_{pid}"):
            P.riattiva_professionista(conn, pid, updated_by=current_user_id)
            st.success("Riattivato.")
            st.rerun()

    # Cancellazione: rischiosa, doppio click di conferma
    conferma_key = f"confirm_del_{pid}"
    if c3.button("🗑️ Elimina definitivamente", key=f"del_btn_{pid}"):
        st.session_state[conferma_key] = True

    if st.session_state.get(conferma_key, False):
        st.warning("⚠️ Sei sicuro? Questa azione è irreversibile.")
        cc1, cc2 = st.columns(2)
        if cc1.button("Sì, elimina", key=f"del_yes_{pid}", type="primary"):
            ok, msg = P.cancella_professionista(conn, pid)
            if ok:
                st.success("Eliminato.")
                st.session_state[conferma_key] = False
                st.rerun()
            else:
                st.error(msg)
                st.session_state[conferma_key] = False
        if cc2.button("Annulla", key=f"del_no_{pid}"):
            st.session_state[conferma_key] = False
            st.rerun()

    # Info di audit, in piccolo
    st.caption(
        f"Creato il {p['created_at'].strftime('%d/%m/%Y %H:%M') if p['created_at'] else '—'}, "
        f"ultimo aggiornamento {p['updated_at'].strftime('%d/%m/%Y %H:%M') if p['updated_at'] else '—'}."
    )


# =============================================================================
#  CREAZIONE NUOVO
# =============================================================================

def _render_form_nuovo(conn, current_user_id: Optional[int]):
    """Form per creare un nuovo professionista."""

    st.markdown("Compila i campi qui sotto. La firma scansionata potrà essere "
                "caricata dopo la creazione, dall'elenco.")

    with st.form(key="form_nuovo_presc", clear_on_submit=True):
        c1, c2 = st.columns(2)
        nome = c1.text_input("Nome completo *",
                             placeholder="es. Dott. Salvatore Adriano Cirillo")
        ord_v = c2.number_input("Ordine in lista", min_value=0, value=10, step=1,
                                help="Valori più bassi appaiono prima nella tendina di selezione.")

        c1, c2 = st.columns(2)
        q1 = c1.text_input("Qualifica (riga 1)", placeholder="es. Medico Chirurgo")
        q2 = c2.text_input("Qualifica (riga 2)", placeholder="es. Oculista")

        c1, c2 = st.columns(2)
        ord_albo = c1.text_input("Ordine / Albo (opzionale)",
                                 placeholder="es. Ordine dei Medici di Salerno")
        num_albo = c2.text_input("Numero albo (opzionale)",
                                 placeholder="es. n. 12345")

        c1, c2 = st.columns(2)
        email_p = c1.text_input("Email professionale (opzionale)")
        tel = c2.text_input("Telefono (opzionale)")

        is_default = st.checkbox("Imposta come professionista di default", value=False,
                                 help="Sarà il selezionato automaticamente quando si genera una nuova prescrizione.")

        crea = st.form_submit_button("➕ Crea professionista", type="primary")

        if crea:
            if not nome.strip():
                st.error("Il nome completo è obbligatorio.")
            else:
                try:
                    new_id = P.crea_professionista(
                        conn,
                        nome_completo=nome,
                        qualifica_riga_1=q1,
                        qualifica_riga_2=q2,
                        ordine_albo=ord_albo,
                        numero_albo=num_albo,
                        email_professionale=email_p,
                        telefono=tel,
                        is_default=is_default,
                        ordine_visualizzazione=ord_v,
                        created_by=current_user_id,
                    )
                    st.success(f"✅ Professionista creato (id={new_id}). "
                               f"Vai sul tab **📋 Elenco** per caricare la firma.")
                except Exception as e:
                    st.error(f"Errore: {e}")


# =============================================================================
#  HELPER: processo firma (resize + conversione in PNG)
# =============================================================================

def _processa_firma(upload) -> tuple[Optional[bytes], Optional[str]]:
    """Processa l'immagine firma: ridimensiona e converte in PNG.

    Returns:
        (png_bytes, errore_string). Se errore_string è None, png_bytes è valido.
    """
    try:
        # Verifico dimensione
        upload.seek(0, 2)  # vai a fine file per misurare
        size = upload.tell()
        upload.seek(0)

        if size > MAX_FIRMA_BYTES:
            return None, f"Il file è troppo grande ({size // 1024} KB). Massimo {MAX_FIRMA_BYTES // 1024} KB."

        # Apro con PIL
        from PIL import Image
        img = Image.open(upload)

        # Converto in RGB (per JPG con alpha o PNG indicizzati)
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGB")

        # Resize se troppo grande
        w, h = img.size
        max_lato = max(w, h)
        if max_lato > MAX_FIRMA_LATO:
            ratio = MAX_FIRMA_LATO / max_lato
            new_size = (int(w * ratio), int(h * ratio))
            img = img.resize(new_size, Image.LANCZOS)

        # Salvo come PNG
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        return buf.getvalue(), None

    except Exception as e:
        return None, f"Errore nel processare l'immagine: {e}"
