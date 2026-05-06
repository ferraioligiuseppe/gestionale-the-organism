# -*- coding: utf-8 -*-
"""
Entry point modulare canonico per la sezione Privacy.

Aggiornato: ora con 2 tab — Consensi GDPR (esistente) + Costellazioni (nuovo).
"""

import streamlit as st


def render_privacy_section(*args, **kwargs):
    """Sezione Privacy & Consensi: 2 tab con Consensi GDPR e Costellazioni."""
    tab_gdpr, tab_costellazioni = st.tabs([
        "📄 Consensi GDPR",
        "🤝 Costellazioni Familiari",
    ])

    with tab_gdpr:
        # Consensi GDPR esistenti (Adulto/Minore con PDF firmati a penna)
        from modules.app_core import ui_privacy_pdf
        ui_privacy_pdf(*args, **kwargs)

    with tab_costellazioni:
        # Nuovo modulo Consensi Costellazioni Familiari
        try:
            _render_costellazioni_tab()
        except Exception as e:
            st.error(f"Errore caricamento modulo costellazioni: {e}")
            import traceback
            with st.expander("Dettagli errore"):
                st.code(traceback.format_exc())


def _render_costellazioni_tab():
    """Renderizza il pannello costellazioni per il paziente attivo."""
    from modules.app_core import get_connection
    from modules.paziente_attivo import get_paziente_attivo
    from modules.consensi_costellazioni.ui import render_pannello_consensi

    conn = get_connection()
    pid = get_paziente_attivo(conn)
    if not pid:
        st.info("⚠️ Seleziona prima un paziente.")
        return

    # Recupero anagrafica per nome paziente
    paziente_nome = _get_nome_paziente(conn, pid)

    # Renderizza il pannello
    render_pannello_consensi(
        paziente_id=int(pid),
        paziente_nome=paziente_nome,
    )


def _get_nome_paziente(conn, paziente_id: int) -> str:
    """Recupera 'Cognome Nome' del paziente. Best effort."""
    try:
        from modules.app_core import _detect_patient_table_and_cols
        tab, cols = _detect_patient_table_and_cols(conn)
        if tab and cols:
            cur = conn.cursor()
            try:
                cur.execute(
                    f'SELECT "{cols["cognome"]}", "{cols["nome"]}" '
                    f'FROM {tab} WHERE "{cols["id"]}" = %s',
                    (paziente_id,)
                )
                row = cur.fetchone()
                if row:
                    return f"{row[0]} {row[1]}".strip()
            finally:
                try:
                    cur.close()
                except Exception:
                    pass
    except Exception:
        pass

    return f"Paziente {paziente_id}"
