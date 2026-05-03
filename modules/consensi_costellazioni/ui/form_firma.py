# -*- coding: utf-8 -*-
"""
modules/consensi_costellazioni/ui/form_firma.py

Form di firma "click in studio" — il paziente legge sul tablet/monitor
e l'operatore (o il paziente stesso) spunta le voci.

API pubblica:
    render_form_firma_click_studio(conn, paziente_id, paziente_nome, codice, is_renewing=False)
"""

from __future__ import annotations

import logging

import streamlit as st

from .. import services
from ..pdf_generator import genera_pdf_consenso

logger = logging.getLogger(__name__)


def _operatore_corrente() -> tuple:
    user = st.session_state.get("user") or {}
    return user.get("username"), user.get("id")


def _client_ip_user_agent() -> tuple[str, str]:
    """
    Tenta di recuperare IP e User-Agent del client.
    Streamlit non li espone direttamente; usiamo placeholder coerenti.
    """
    # In Streamlit Cloud il client IP è in headers ma non sempre accessibile.
    # Per il setting "click in studio" è il dispositivo dello studio,
    # quindi possiamo loggare un identificativo generico.
    ip = st.session_state.get("_client_ip", "studio_local")
    ua = st.session_state.get("_client_ua", "Streamlit-Studio")
    return ip, ua


def render_form_firma_click_studio(
    conn,
    paziente_id: int,
    paziente_nome: str,
    codice: str,
    is_renewing: bool = False,
):
    """
    Render del form di firma click_studio.

    Mostra: testo del template (espandibile), checkbox per ogni voce,
    pulsante di conferma firma. Al submit: valida, salva firma + voci,
    genera PDF con timbro digitale, salva PDF nel record.
    """
    tpl = services.template_attivo_per_codice(conn, codice)
    if not tpl:
        st.error(f"Template '{codice}' non trovato.")
        return

    voci_def = tpl.get("voci") or []

    # === TESTO INFORMATIVA (espandibile per non saturare la UI) ===
    with st.expander("📜 Leggi il testo completo dell'informativa", expanded=False):
        st.markdown(tpl.get("testo_md", ""))

    st.divider()

    # === CHECKBOX VOCI ===
    st.markdown("**Spunta le voci che il paziente accetta:**")
    st.caption(
        "Le voci marcate come *(obbligatoria)* devono essere accettate "
        "perché la firma sia valida."
    )

    # Form per evitare rerun a ogni checkbox
    with st.form(key=f"form_firma_click_{codice}_{paziente_id}"):
        voci_paziente = {}
        for v in sorted(voci_def, key=lambda x: x.get("ordine", 0)):
            cv = v["codice"]
            label_obb = " *(obbligatoria)*" if v.get("obbligatorio") else ""
            label = f"**{cv}** — {v['testo']}{label_obb}"
            # default: True se obbligatoria (l'operatore deve esplicitamente togliere)
            default_val = bool(v.get("obbligatorio"))
            voci_paziente[cv] = st.checkbox(
                label,
                value=default_val,
                key=f"voce_{codice}_{paziente_id}_{cv}",
            )

        st.markdown("---")
        st.markdown("**Dichiarazione di consenso**")
        st.caption(
            "Confermando, attesti che il paziente ha letto e compreso "
            "l'informativa e ha espresso le scelte sopra indicate."
        )

        note = st.text_area(
            "Note (opzionali)",
            max_chars=500,
            key=f"note_{codice}_{paziente_id}",
            help="Annotazioni libere, eventuali precisazioni del paziente"
        )

        col1, col2 = st.columns(2)
        confirm = col1.form_submit_button(
            "✔ Conferma firma digitale",
            type="primary",
            use_container_width=True,
        )
        # Form_submit_button con un solo "annulla" gestito dal pannello superiore

    if confirm:
        _esegui_firma(
            conn=conn,
            paziente_id=paziente_id,
            paziente_nome=paziente_nome,
            codice=codice,
            voci_paziente=voci_paziente,
            note=note,
            is_renewing=is_renewing,
            tpl=tpl,
        )


def _esegui_firma(
    *, conn, paziente_id, paziente_nome, codice, voci_paziente, note, is_renewing, tpl
):
    """Salva firma, genera PDF, aggiorna record con PDF blob + hash."""
    op_username, op_user_id = _operatore_corrente()
    ip, ua = _client_ip_user_agent()

    try:
        # 1. Salva firma + voci atomiche (senza PDF blob: lo aggiungiamo dopo)
        if is_renewing:
            ris = services.rinnova_consenso(
                conn=conn,
                paziente_id=paziente_id,
                codice_template=codice,
                voci=voci_paziente,
                modalita_firma="click_studio",
                operatore_username=op_username,
                operatore_user_id=op_user_id,
                ip_address=ip,
                user_agent=ua,
                note=(note or None),
            )
        else:
            ris = services.firma_consenso(
                conn=conn,
                paziente_id=paziente_id,
                codice_template=codice,
                voci=voci_paziente,
                modalita_firma="click_studio",
                operatore_username=op_username,
                operatore_user_id=op_user_id,
                ip_address=ip,
                user_agent=ua,
                note=(note or None),
            )
    except services.VoceValidationError as e:
        st.error(f"⚠️ Voci obbligatorie non accettate: {e}")
        return
    except Exception as e:
        logger.exception("Firma fallita")
        st.error(f"Errore durante la firma: {e}")
        return

    # 2. Genera PDF firmato (con timbro che include hash placeholder, poi rigenera con hash reale)
    try:
        # Prima generazione: senza hash, calcola hash, rigenera con hash
        pdf_temp = genera_pdf_consenso(
            template=tpl,
            modalita_firma="click_studio",
            paziente_nome=paziente_nome,
            paziente_id=paziente_id,
            voci_paziente=ris["voci_normalizzate"],
            operatore=op_username,
            data_accettazione=ris["data_accettazione"],
            pdf_hash=None,
            ip_address=ip,
            user_agent=ua,
        )

        import hashlib
        pdf_hash = hashlib.sha256(pdf_temp).hexdigest()

        pdf_final = genera_pdf_consenso(
            template=tpl,
            modalita_firma="click_studio",
            paziente_nome=paziente_nome,
            paziente_id=paziente_id,
            voci_paziente=ris["voci_normalizzate"],
            operatore=op_username,
            data_accettazione=ris["data_accettazione"],
            pdf_hash=pdf_hash,
            ip_address=ip,
            user_agent=ua,
        )

        # 3. Salva PDF blob nel record
        ph = "%s" if services._is_postgres(conn) else "?"
        cur = conn.cursor()
        try:
            cur.execute(
                f"""
                UPDATE cf_firme SET
                    pdf_blob = {ph}, pdf_filename = {ph}, pdf_hash = {ph}
                WHERE id = {ph}
                """,
                (
                    pdf_final,
                    f"consenso_{codice}_{paziente_id}_{ris['firma_id']}.pdf",
                    pdf_hash,
                    ris["firma_id"]
                )
            )
            conn.commit()
        finally:
            try: cur.close()
            except: pass

    except Exception as e:
        logger.exception("Generazione PDF fallita (firma è comunque salvata)")
        st.warning(
            f"Firma salvata, ma generazione PDF fallita: {e}. "
            "Il PDF potrà essere rigenerato in seguito."
        )
        pdf_final = None

    # 4. Conferma e download
    st.success(f"✅ Consenso firmato (id firma: {ris['firma_id']})")

    if pdf_final:
        st.download_button(
            "📥 Scarica PDF firmato",
            data=pdf_final,
            file_name=f"consenso_{codice}_{paziente_id}.pdf",
            mime="application/pdf",
            key=f"dl_just_signed_{ris['firma_id']}",
        )

    # Cleanup state per refresh corretto del pannello
    st.session_state[f"_show_firm_{codice}_{paziente_id}"] = False
    st.session_state[f"_renewing_{codice}_{paziente_id}"] = False

    # Bottone per chiudere e refreshare
    if st.button("Torna al pannello", key=f"back_panel_{ris['firma_id']}"):
        st.rerun()
