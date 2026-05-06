# -*- coding: utf-8 -*-
"""
modules/consensi_costellazioni/ui/form_cartaceo.py

Form di firma cartaceo: l'operatore (1) scarica il PDF da stampare,
(2) il paziente firma a penna, (3) l'operatore scansiona e ricarica.

Il sistema riconcilia automaticamente le voci spuntate dichiarate manualmente
con quelle del PDF firmato, calcola hash SHA-256, salva tutto.

API pubblica:
    render_form_firma_cartaceo(conn, paziente_id, paziente_nome, codice, is_renewing=False)
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st

from .. import services
from ..pdf_generator import genera_pdf_consenso

logger = logging.getLogger(__name__)
ROME_TZ = ZoneInfo("Europe/Rome")


def _operatore_corrente():
    user = st.session_state.get("user") or {}
    return user.get("username"), user.get("id")


def render_form_firma_cartaceo(
    conn,
    paziente_id: int,
    paziente_nome: str,
    codice: str,
    is_renewing: bool = False,
):
    """
    Render del workflow cartaceo a 3 step.
    """
    tpl = services.template_attivo_per_codice(conn, codice)
    if not tpl:
        st.error(f"Template '{codice}' non trovato.")
        return

    voci_def = tpl.get("voci") or []

    # === STEP 1: Scarica PDF stampabile ===
    st.markdown("**Passo 1 — Scarica e stampa il modulo**")

    if st.button(
        "📄 Genera PDF da stampare",
        key=f"gen_pdf_{codice}_{paziente_id}",
        type="primary",
    ):
        pdf_bytes = genera_pdf_consenso(
            template=tpl,
            modalita_firma="cartaceo",
            paziente_nome=paziente_nome,
            paziente_id=paziente_id,
        )
        st.session_state[f"_pdf_cartaceo_{codice}_{paziente_id}"] = pdf_bytes

    if st.session_state.get(f"_pdf_cartaceo_{codice}_{paziente_id}"):
        st.download_button(
            "📥 Scarica PDF (stampabile, vuoto)",
            data=st.session_state[f"_pdf_cartaceo_{codice}_{paziente_id}"],
            file_name=f"consenso_{codice}_{paziente_id}_DA_FIRMARE.pdf",
            mime="application/pdf",
            key=f"dl_cart_{codice}_{paziente_id}",
        )

    st.divider()

    # === STEP 2: Operatore registra le voci spuntate dal paziente ===
    st.markdown("**Passo 2 — Riporta nel sistema le voci che il paziente ha spuntato**")
    st.caption(
        "Dopo che il paziente ha letto, spuntato le voci e firmato il modulo cartaceo, "
        "ricopia qui sotto le scelte del paziente per registrarle nel sistema."
    )

    with st.form(key=f"form_firma_cart_{codice}_{paziente_id}"):
        voci_paziente = {}
        for v in sorted(voci_def, key=lambda x: x.get("ordine", 0)):
            cv = v["codice"]
            label_obb = " *(obbligatoria)*" if v.get("obbligatorio") else ""
            label = f"**{cv}** — {v['testo']}{label_obb}"
            default_val = bool(v.get("obbligatorio"))
            voci_paziente[cv] = st.checkbox(
                label,
                value=default_val,
                key=f"voce_cart_{codice}_{paziente_id}_{cv}",
            )

        st.divider()
        st.markdown("**Passo 3 — Carica la scansione del modulo firmato**")
        uploaded_file = st.file_uploader(
            "PDF firmato (scansione)",
            type=["pdf"],
            key=f"upload_cart_{codice}_{paziente_id}",
            help="Carica la scansione del modulo firmato dal paziente",
        )

        data_firma = st.date_input(
            "Data della firma cartacea",
            value=datetime.now(ROME_TZ).date(),
            key=f"data_firma_cart_{codice}_{paziente_id}",
        )

        note = st.text_area(
            "Note (opzionali)",
            max_chars=500,
            key=f"note_cart_{codice}_{paziente_id}",
        )

        confirm = st.form_submit_button(
            "✔ Registra firma cartacea",
            type="primary",
            use_container_width=True,
        )

    if confirm:
        if not uploaded_file:
            st.error("⚠️ Carica la scansione del PDF firmato prima di confermare.")
            return

        _esegui_firma_cartacea(
            conn=conn,
            paziente_id=paziente_id,
            paziente_nome=paziente_nome,
            codice=codice,
            voci_paziente=voci_paziente,
            pdf_uploaded=uploaded_file,
            data_firma=data_firma,
            note=note,
            is_renewing=is_renewing,
            tpl=tpl,
        )


def _esegui_firma_cartacea(
    *, conn, paziente_id, paziente_nome, codice, voci_paziente,
    pdf_uploaded, data_firma, note, is_renewing, tpl,
):
    """Registra firma cartacea con PDF allegato."""
    op_username, op_user_id = _operatore_corrente()
    pdf_bytes = pdf_uploaded.read()
    pdf_hash = hashlib.sha256(pdf_bytes).hexdigest()
    pdf_filename = pdf_uploaded.name

    try:
        if is_renewing:
            ris = services.rinnova_consenso(
                conn=conn,
                paziente_id=paziente_id,
                codice_template=codice,
                voci=voci_paziente,
                modalita_firma="cartaceo",
                operatore_username=op_username,
                operatore_user_id=op_user_id,
                pdf_blob=pdf_bytes,
                pdf_filename=pdf_filename,
                note=(note or None),
            )
        else:
            ris = services.firma_consenso(
                conn=conn,
                paziente_id=paziente_id,
                codice_template=codice,
                voci=voci_paziente,
                modalita_firma="cartaceo",
                operatore_username=op_username,
                operatore_user_id=op_user_id,
                pdf_blob=pdf_bytes,
                pdf_filename=pdf_filename,
                note=(note or None),
            )
    except services.VoceValidationError as e:
        st.error(f"⚠️ Voci obbligatorie non accettate: {e}")
        return
    except Exception as e:
        logger.exception("Firma cartacea fallita")
        st.error(f"Errore: {e}")
        return

    st.success(
        f"✅ Firma cartacea registrata (id firma: {ris['firma_id']}). "
        f"Hash SHA-256 del PDF: `{pdf_hash[:24]}...`"
    )

    # Cleanup state
    st.session_state[f"_show_firm_{codice}_{paziente_id}"] = False
    st.session_state[f"_renewing_{codice}_{paziente_id}"] = False
    st.session_state.pop(f"_pdf_cartaceo_{codice}_{paziente_id}", None)

    if st.button("Torna al pannello", key=f"back_cart_{ris['firma_id']}"):
        st.rerun()
