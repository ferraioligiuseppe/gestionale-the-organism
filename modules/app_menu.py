# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════╗
║  APP MENU — Struttura a 7 aree                                      ║
║                                                                     ║
║  AREE:                                                              ║
║  1. 👥 Pazienti        — anagrafica, sedute, privacy, import        ║
║  2. 🔬 Valutazione     — PNEV, VVF, NPS, DSA, PSY, FE              ║
║  3. 🖥️ Test live        — DEM, K-D, somministrazione                ║
║  4. 📋 Questionari     — link remoti, risposte, lenti, osteopatia   ║
║  5. 🤖 Report & AI     — relazioni, piano VT, PDF, export           ║
║  6. 🔉 Audiologia      — diagnostica, stimolazione, bilancio        ║
║  7. ⚙️ Studio          — incassi, utenti, admin SaaS                ║
╚══════════════════════════════════════════════════════════════════════╝
"""

# ── Costanti aree ─────────────────────────────────────────────────────
AREA_PAZIENTI    = "👥 Pazienti"
AREA_VALUTAZIONE = "🔬 Valutazione"
AREA_TEST_LIVE   = "🖥️ Test live"
AREA_QUESTIONARI = "📋 Questionari"
AREA_REPORT_AI   = "🤖 Report & AI"
AREA_AUDIOLOGIA  = "🔉 Audiologia"
AREA_STUDIO      = "⚙️ Studio"

AREE_ORDINE = [
    AREA_PAZIENTI,
    AREA_VALUTAZIONE,
    AREA_TEST_LIVE,
    AREA_QUESTIONARI,
    AREA_REPORT_AI,
    AREA_AUDIOLOGIA,
    AREA_STUDIO,
]

# ── Sottosezioni per area ─────────────────────────────────────────────
SOTTOSEZIONI = {
    AREA_PAZIENTI: [
        "🏠 Dashboard",
        "👤 Anagrafica pazienti",
        "📅 Sedute / Terapie",
        "🔒 Privacy & Consensi",
        "📥 Import pazienti",
    ],
    AREA_VALUTAZIONE: [
        "🔬 PNEV",
        "📋 Anamnesi The Organism",
        "👁️ Valutazione visiva (VVF)",
        "🧠 NPS — Neuropsicologica",
        "📚 DSA — Apprendimento",
        "🔬 Test psicologici",
        "⚡ Funzioni esecutive",
        "👓 Optometria comportamentale",
    ],
    AREA_TEST_LIVE: [
        "🔢 DEM interattivo",
        "👁️ K-D interattivo",
        "🖥️ Somministrazione test",
        "👁️ Eye tracking",
    ],
    AREA_QUESTIONARI: [
        "📋 Questionari remoti",
        "👁️ Lenti a contatto",
        "🦴 Osteopatia",
        "📸 Photoref AI",
    ],
    AREA_REPORT_AI: [
        "🤖 Relazioni cliniche (AI)",
        "🎯 Piano Vision Therapy",
        "📄 Report PDF con grafici",
        "📊 Export statistici",
        "🧪 Caso demo",
    ],
    AREA_AUDIOLOGIA: [
        "🔉 Diagnostica uditiva",
        "🎵 Stimolazione passiva",
        "🎧 Bilancio uditivo",
        "📊 Audiometria funzionale",
        "📖 Lettura avanzata",
    ],
    AREA_STUDIO: [
        "📊 Dashboard incassi",
        "🏥 Il mio studio",
        "👥 Utenti / Ruoli",
        "⚙️ Platform Admin",
        "🐛 Debug DB",
    ],
}

# ── Costanti legacy (compatibilità con app_core.py) ───────────────────
# Mantenute per non rompere i riferimenti esistenti in app_core.py
SECTION_PAZIENTI     = "Pazienti"
SECTION_PNEV         = "Valutazione PNEV"
SECTION_VISION       = "Valutazioni visive / oculistiche"
SECTION_SEDUTE       = "Sedute / Terapie"
SECTION_OSTEOPATIA   = "Osteopatia"
SECTION_COUPON       = "Coupon OF / SDS"
SECTION_DASHBOARD    = "Dashboard incassi"
SECTION_RELAZIONI    = "️ Relazioni cliniche"
SECTION_EVOLUTIVA    = " Dashboard evolutiva"
SECTION_PRIVACY      = " Privacy & Consensi (PDF)"
SECTION_DEBUG        = "️ Debug DB"
SECTION_IMPORT       = " Import Pazienti"
SECTION_UTENTI       = " Utenti / Ruoli"
SECTION_GAZE         = " Eye Tracking"
SECTION_READING_DOM  = " Lettura Avanzata DOM"
SECTION_TERAPIA      = "🧠 Terapia"
SECTION_NPS_OLD      = "🧠 NPS Neuropsicologico"
SECTION_PIANO_VT     = "🎯 Piano Vision Therapy"
SECTION_REPORT_PDF   = "📄 Report PDF Clinico"
SECTION_DEM          = "🔢 DEM Interattivo"
SECTION_KD           = "👁️ K-D Interattivo"
SECTION_EXPORT       = "📊 Export Statistici"
SECTION_SEED_DEMO    = "🧪 Caso Demo"
SECTION_NPS          = "🧠 NPS — Valutazione Neuropsicologica"
SECTION_DSA          = "📚 DSA — Apprendimento"
SECTION_TEST_PSY     = "🔬 Test Psicologici"
SECTION_FE           = "⚡ Funzioni Esecutive"
SECTION_SAAS_ADMIN   = "⚙️ Platform Admin"
SECTION_MIO_STUDIO   = "🏥 Il mio studio"
SECTION_SOMMINISTRAZIONE = "🖥️ Somministrazione Test"
SECTION_QUESTIONARI  = "📋 Questionari Remoti"

SECTION_DIAGNOSTICA_UDITIVA = "🔉 Diagnostica Uditiva"
SECTION_STIMOLAZIONE_PASSIVA = "🎵 Stimolazione Passiva"


def build_sections(is_admin: bool, app_mode: str) -> list[str]:
    """Compatibilità legacy — ritorna la lista piatta originale."""
    sections = [
        SECTION_DASHBOARD, SECTION_PAZIENTI, SECTION_PNEV,
        SECTION_VISION, SECTION_SEDUTE, SECTION_OSTEOPATIA,
        SECTION_RELAZIONI, SECTION_EVOLUTIVA, SECTION_PRIVACY,
        SECTION_DEBUG, SECTION_IMPORT, SECTION_GAZE,
        SECTION_READING_DOM, SECTION_TERAPIA,
        SECTION_NPS, SECTION_DSA, SECTION_FE, SECTION_TEST_PSY,
        SECTION_QUESTIONARI, SECTION_SOMMINISTRAZIONE,
        SECTION_DEM, SECTION_KD, SECTION_PIANO_VT,
        SECTION_REPORT_PDF, SECTION_EXPORT,
        SECTION_MIO_STUDIO,
        SECTION_DIAGNOSTICA_UDITIVA, SECTION_STIMOLAZIONE_PASSIVA,
    ]
    if is_admin:
        sections += [SECTION_UTENTI, SECTION_SEED_DEMO, SECTION_SAAS_ADMIN]
    return sections
