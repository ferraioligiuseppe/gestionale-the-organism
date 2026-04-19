# -*- coding: utf-8 -*-
"""Routing principale delle sezioni non uditive."""

from typing import Callable, Any
import streamlit as st

from .app_sections import (
    SECTION_PAZIENTI, SECTION_PNEV, SECTION_VISION, SECTION_SEDUTE,
    SECTION_OSTEOPATIA, SECTION_COUPON, SECTION_DASHBOARD,
    SECTION_RELAZIONI, SECTION_EVOLUTIVA, SECTION_PRIVACY,
    SECTION_DEBUG, SECTION_IMPORT, SECTION_GAZE, SECTION_READING_DOM,
    SECTION_UTENTI, SECTION_TERAPIA,
    SECTION_NPS_OLD, SECTION_PIANO_VT, SECTION_REPORT_PDF,
    SECTION_DEM, SECTION_KD, SECTION_EXPORT, SECTION_SEED_DEMO,
    SECTION_NPS, SECTION_DSA, SECTION_TEST_PSY, SECTION_FE,
    SECTION_SAAS_ADMIN,
    SECTION_SOMMINISTRAZIONE,
    SECTION_QUESTIONARI, SECTION_MIO_STUDIO,
)
from .pazienti import render_pazienti_section
from .anamnesi import render_anamnesi_section
from .privacy.ui_privacy_section import render_privacy_section
from .pnev.ui_pnev import render_pnev_section
from .sections.ui_cliniche import (
    render_vision_section, render_sedute_section, render_osteopatia_section,
    render_coupon_section, render_dashboard_section, render_relazioni_section,
    render_evolutiva_section, render_debug_section, render_import_section,
    render_gaze_section, render_utenti_section,
)
from .ui_lenti_contatto import ui_lenti_contatto
from .terapia_section import render_terapia_section

SECTION_LENTI_CONTATTO = "👁️ Lenti a contatto"
SECTION_PHOTOREF = "📸 Photoref AI"


def _get_paz_id() -> int | None:
    return st.session_state.get("paziente_id")


def _seleziona_paziente(conn, key_suffix: str = "") -> int | None:
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, Cognome, Nome, Data_Nascita FROM Pazienti "
            "WHERE COALESCE(Stato_Paziente,'ATTIVO') = 'ATTIVO' "
            "ORDER BY Cognome, Nome"
        )
        rows = cur.fetchall()
    except Exception as e:
        st.error(f"Errore caricamento pazienti: {e}")
        return None

    if not rows:
        st.info("Nessun paziente registrato.")
        return None

    def _label(r):
        if isinstance(r, dict):
            return f"{r.get('id')} - {r.get('Cognome','')} {r.get('Nome','')} · {r.get('Data_Nascita','')}"
        return f"{r[0]} - {r[1]} {r[2]}" + (f" · {r[3]}" if len(r) > 3 and r[3] else "")

    sel = st.selectbox("Seleziona paziente", options=rows,
                       format_func=_label, key=f"paz_sel_{key_suffix}")
    return int(sel[0] if not isinstance(sel, dict) else sel.get("id"))


def dispatch_main_section(*, sezione: str, get_connection: Callable[..., Any]) -> bool:
    photoref_token = st.query_params.get("photoref_token", "")
    if isinstance(photoref_token, list):
        photoref_token = photoref_token[0] if photoref_token else ""

    if photoref_token:
        try:
            from .photoref_ai.ui_photoref_mobile import ui_photoref_mobile
            ui_photoref_mobile(conn=get_connection())
        except Exception as e:
            st.error("Modulo Photoref Mobile non disponibile.")
            st.exception(e)
        return True

    # ── Sezioni core ────────────────────────────────────────────────
    if sezione == SECTION_PAZIENTI:
        render_pazienti_section(); return True
    if sezione == SECTION_PNEV:
        render_pnev_section(); return True
    if sezione == SECTION_VISION:
        render_vision_section(); return True
    if sezione == SECTION_LENTI_CONTATTO:
        ui_lenti_contatto(); return True
    if sezione == SECTION_PHOTOREF:
        try:
            from .photoref_ai.ui_photoref import ui_photoref
            ui_photoref()
        except Exception as e:
            st.error("Modulo Photoref AI non disponibile.")
            st.exception(e)
        return True
    if sezione == SECTION_TERAPIA:
        render_terapia_section(conn=get_connection()); return True
    if sezione == SECTION_SEDUTE:
        render_sedute_section(); return True
    if sezione == SECTION_OSTEOPATIA:
        render_osteopatia_section(); return True
    if sezione == SECTION_COUPON:
        render_coupon_section(); return True
    if sezione == SECTION_DASHBOARD:
        render_dashboard_section(); return True
    if sezione == SECTION_RELAZIONI:
        render_relazioni_section(); return True
    if sezione == SECTION_EVOLUTIVA:
        render_evolutiva_section(); return True
    if sezione == SECTION_PRIVACY:
        render_privacy_section(); return True
    if sezione == SECTION_DEBUG:
        render_debug_section(); return True
    if sezione == SECTION_IMPORT:
        render_import_section(); return True
    if sezione == SECTION_GAZE:
        render_gaze_section(); return True
    if sezione == SECTION_READING_DOM:
        try:
            from .reading.ui_reading_dom import ui_reading_dom
        except Exception as e:
            st.error("Modulo Lettura Avanzata DOM non disponibile.")
            st.exception(e)
            return True
        ui_reading_dom(); return True
    if sezione == SECTION_UTENTI:
        render_utenti_section(get_connection); return True

    # ── NPS / DSA / PSY / FE ────────────────────────────────────────
    if sezione == SECTION_NPS:
        try:
            from .ui_nps_completo import render_nps_completo
        except ImportError as e:
            st.error(f"Modulo NPS non disponibile: {e}"); return True
        paz_id = _seleziona_paziente(get_connection(), "nps")
        if paz_id:
            render_nps_completo(get_connection(), paz_id)
        return True

    if sezione == SECTION_DSA:
        try:
            from .ui_dsa import render_dsa
        except ImportError as e:
            st.error(f"Modulo DSA non disponibile: {e}"); return True
        paz_id = _seleziona_paziente(get_connection(), "dsa")
        if paz_id:
            render_dsa(get_connection(), paz_id)
        return True

    if sezione == SECTION_TEST_PSY:
        try:
            from .ui_nps_completo import render_test_psy
        except ImportError as e:
            st.error(f"Modulo PSY non disponibile: {e}"); return True
        paz_id = _seleziona_paziente(get_connection(), "psy")
        if paz_id:
            render_test_psy(get_connection(), paz_id)
        return True

    if sezione == SECTION_FE:
        try:
            from .ui_nps_completo import render_funzioni_esecutive
        except ImportError as e:
            st.error(f"Modulo FE non disponibile: {e}"); return True
        paz_id = _seleziona_paziente(get_connection(), "fe")
        if paz_id:
            render_funzioni_esecutive(get_connection(), paz_id)
        return True

    # ── Vecchi moduli gestionale_new_modules ────────────────────────
    if sezione in (SECTION_NPS_OLD, SECTION_PIANO_VT, SECTION_REPORT_PDF,
                   SECTION_DEM, SECTION_KD, SECTION_EXPORT, SECTION_SEED_DEMO):
        try:
            from .gestionale_new_modules import render_nuovi_moduli
        except ImportError as e:
            st.error(f"Modulo non disponibile: {e}"); return True
        mappa = {
            SECTION_NPS_OLD:    "NPS",
            SECTION_PIANO_VT:   "PianoVT",
            SECTION_REPORT_PDF: "ReportPDF",
            SECTION_DEM:        "DEM",
            SECTION_KD:         "KD",
            SECTION_EXPORT:     "ExportStatistici",
            SECTION_SEED_DEMO:  "SeedDemo",
        }
        paz_id = _seleziona_paziente(get_connection(), sezione) \
                 if sezione not in (SECTION_DEM, SECTION_KD,
                                    SECTION_EXPORT, SECTION_SEED_DEMO) else None
        render_nuovi_moduli(conn=get_connection(),
                            sezione=mappa[sezione],
                            paziente_id=paz_id)
        return True

    if sezione == SECTION_QUESTIONARI:
        try:
            from .ui_questionari import render_questionari_section
        except ImportError as e:
            st.error(f"Modulo questionari non disponibile: {e}"); return True
        paz_id = _seleziona_paziente(get_connection(), "qsec")
        if paz_id:
            render_questionari_section(get_connection(), paz_id)
        return True

    if sezione == SECTION_SOMMINISTRAZIONE:
        try:
            from .ui_test_somministrazione import render_somministrazione
        except ImportError as e:
            st.error(f"Modulo Somministrazione non disponibile: {e}"); return True
        paz_id = _seleziona_paziente(get_connection(), "som")
        if paz_id:
            render_somministrazione(get_connection(), paz_id)
        return True

    # ── SaaS Admin ──────────────────────────────────────────────────
    if sezione == SECTION_SAAS_ADMIN:
        try:
            from .saas_tenant import render_admin_saas
            render_admin_saas(get_connection())
        except ImportError as e:
            st.error(f"Modulo SaaS Admin non disponibile: {e}")
        return True

    if sezione == SECTION_MIO_STUDIO:
        try:
            from .saas_tenant import render_gestione_studio
            studio_id = st.session_state.get("studio_id", 1)
            piano     = st.session_state.get("piano", "professional")
            render_gestione_studio(get_connection(), studio_id, piano)
        except ImportError as e:
            st.error(f"Modulo Studio non disponibile: {e}")
        return True

    return False
