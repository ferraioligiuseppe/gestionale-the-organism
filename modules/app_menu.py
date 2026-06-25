# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════╗
║  APP MENU — Struttura a 7 aree (v4, in ordine di visita)             ║
║                                                                     ║
║  AREE:                                                              ║
║  1. 👥 Pazienti                                                     ║
║  2. 📨 Invii al paziente                                            ║
║  3. 🔍 Valutazione funzionale  (occhi + orecchie + riflessi insieme)║
║  4. 🖥️ Test live                                                    ║
║  5. 🎧 Terapia & relazione                                          ║
║  6. 🎓 Formazione & professionisti                                  ║
║  7. ⚙️ Studio                                                       ║
║                                                                     ║
║  NOTA: il routing (app_main_router._dispatch_sotto) aggancia ogni   ║
║  voce SOLO al suo nome, non all'area. Quindi qui si possono         ║
║  riorganizzare le aree liberamente senza toccare il router, purché  ║
║  le etichette delle voci restino identiche a quelle del router.     ║
╚══════════════════════════════════════════════════════════════════════╝
"""

# ── Costanti aree (7 attive) ──────────────────────────────────────────
AREA_PAZIENTI    = "👥 Pazienti"
AREA_AGENDA      = "📅 Agenda"
AREA_INVII       = "📨 Invii al paziente"
AREA_VALUTAZIONE = "🔍 Valutazione funzionale"
AREA_TEST_LIVE   = "🖥️ Test live"
AREA_TERAPIA     = "🎧 Terapia & relazione"
AREA_OSTEOPATIA  = "🦴 Osteopatia"
AREA_EVENTI      = "📅 Eventi"
AREA_STUDIO      = "⚙️ Studio"

# Vecchia area unica (Osteopatia+Eventi), ora separata. Mantenuta come
# alias per non rompere gli import legacy nel router.
AREA_FORMAZIONE  = AREA_OSTEOPATIA

# ── Alias legacy (mantengono validi gli import esistenti in
#    app_main_router.py e app_main.py) ──────────────────────────────────
AREA_VALUTAZIONE_VISIVA = AREA_VALUTAZIONE
AREA_TEST_NEUROEVOL     = AREA_VALUTAZIONE
AREA_QUESTIONARI        = AREA_INVII
AREA_REPORT_AI          = AREA_TERAPIA
AREA_AUDIOLOGIA         = AREA_TERAPIA
AREA_MARKETING          = AREA_EVENTI

AREE_ORDINE = [
    AREA_PAZIENTI,
    AREA_AGENDA,
    AREA_INVII,
    AREA_VALUTAZIONE,
    AREA_TEST_LIVE,
    AREA_TERAPIA,
    AREA_OSTEOPATIA,
    AREA_EVENTI,
    AREA_STUDIO,
]

# ── Sottosezioni per area ─────────────────────────────────────────────
SOTTOSEZIONI = {
    AREA_PAZIENTI: [
        "🏠 Dashboard",
        "👤 Anagrafica pazienti",
        "📎 Documenti clinici",
        "🎟️ Coupon OF / SDS",
        "📅 Sedute / Terapie",
        "🔒 Privacy & Consensi",
        "📥 Import pazienti",
        "🔗 Sincronizza pnev.it",
        "🚀 Trasferisci a pnev.it",
    ],
    AREA_AGENDA: [
        "📅 Agenda appuntamenti",
    ],
    AREA_INVII: [
        "📋 Questionari remoti",
        "🎧 Screening uditivo",
        "🎮 Esercizi Wordwall",
    ],
    AREA_VALUTAZIONE: [
        "📋 Anamnesi The Organism",
        "👁️ Anamnesi visiva",
        "👁️ Valutazione visuo-percettiva",
        "🔉 Diagnostica uditiva",
        "📊 Audiometria funzionale",
        "🎧 Bilancio uditivo",
        "🧬 INPP — Valutazione diagnostica",
        "🧠 NPS — Neuropsicologica",
        "📚 DSA — Apprendimento",
    ],
    AREA_TEST_LIVE: [
        "🔢 DEM interattivo",
        "👁️ Getman (manipolazione visiva)",
        "👁️ Groffman (visual tracing)",
        "👁️ Eye tracking",
        "🖥️ Somministrazione test",
        "📸 Photoref AI",
        "📖 Lettura avanzata",
    ],
    AREA_TERAPIA: [
        "🎧 MAPS",
        "🗂 Programmi MAPS",
        "🧭 Percorsi MAPS",
        "🎯 Piano Vision Therapy",
        "👁️ Lenti a contatto",
        "📝 Relazione clinica",
        "📄 Report PDF con grafici",
        "📊 Export statistici",
        "🧪 Caso demo",
    ],
    AREA_OSTEOPATIA: [
        "🦴 Osteopatia",
    ],
    AREA_EVENTI: [
        "📅 Eventi e iscrizioni",
    ],
    AREA_STUDIO: [
        "📊 Dashboard incassi",
        "🏥 Il mio studio",
        "👤 Il mio profilo",
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
