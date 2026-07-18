# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════╗
║  APP MENU — Struttura razionalizzata PNEV (v7, con rami annidati)    ║
║                                                                      ║
║  AREE (in ordine):                                                   ║
║  1. 📅 Agenda                                                        ║
║  2. 👥 Pazienti                                                      ║
║  3. 📋 Questionari                                                   ║
║  4. 🎮 PNEV Games                                                    ║
║  5. 🧠 Valutazione e Trattamento PNEV                                ║
║       ↳ 4 rami annidati (si sceglie il ramo, poi la voce):           ║
║         👶 PNEV Child · 👁️ PNEV Visiva ·                             ║
║         🧬 Integrazione sensoriale · 🎧 Uditiva                       ║
║  6. 👁️ Oculistica · LAC                                              ║
║  7. 🩺 Ortottica                                                     ║
║  8. 🗣️ Logopedia / TNPEE                                            ║
║  9. 🎓 PNEV Academy  (Osteopatia + Eventi/iscrizioni)                 ║
║  10. 🏃 Fisioterapia                                                 ║
║  11. 🧠 NPS / Psicologia                                             ║
║  12. 🖥️ Test live (generico)                                        ║
║  13. 📄 Relazioni & studio clinico                                   ║
║  14. ⚙️ Studio                                                       ║
║                                                                      ║
║  Le voci "🚧 …(in arrivo)" sono placeholder: compaiono nel menu ma    ║
║  mostrano solo un avviso "in costruzione" — non esiste ancora un     ║
║  modulo dietro (vedi PLACEHOLDER_VOCI, gestito in                    ║
║  app_main_router._dispatch_sotto).                                   ║
║                                                                      ║
║  NOTA: il routing (app_main_router._dispatch_sotto) aggancia ogni    ║
║  voce SOLO al suo nome, non all'area/ramo. Quindi qui si possono     ║
║  riorganizzare aree e rami liberamente senza toccare il router,      ║
║  purché le etichette restino identiche a quelle del router.          ║
╚══════════════════════════════════════════════════════════════════════╝
"""

# ── Costanti aree ──────────────────────────────────────────────────────
AREA_AGENDA        = "📅 Agenda"
AREA_PAZIENTI      = "👥 Pazienti"
AREA_INVII         = "📋 Questionari"
AREA_GAMES         = "🎮 PNEV Games"
AREA_PNEV          = "🧠 Valutazione e Trattamento PNEV"
AREA_OCULISTICA    = "👁️ Oculistica · LAC"
AREA_ORTOTTICA     = "🩺 Ortottica"
AREA_TNPEE         = "🗣️ Logopedia / TNPEE"
AREA_OSTEOPATIA    = "🦴 Osteopatia"
AREA_ACADEMY       = "🎓 PNEV Academy"
AREA_FISIOTERAPIA  = "🏃 Fisioterapia"
AREA_NPS_PSI       = "🧠 NPS / Psicologia"
AREA_TEST_LIVE     = "🖥️ Test live"
AREA_TERAPIA       = "📄 Relazioni & studio clinico"
AREA_STUDIO        = "⚙️ Studio"

# ── Alias legacy (mantengono validi gli import esistenti in
#    app_main_router.py e app_main.py) — puntano all'area più coerente
#    nella nuova struttura, il nome del modulo non cambia. ─────────────
AREA_VALUTAZIONE        = AREA_PNEV
AREA_VALUTAZIONE_VISIVA = AREA_PNEV
AREA_TEST_NEUROEVOL     = AREA_PNEV
AREA_QUESTIONARI        = AREA_INVII
AREA_REPORT_AI          = AREA_TERAPIA
AREA_AUDIOLOGIA         = AREA_PNEV
AREA_MARKETING          = AREA_ACADEMY
AREA_FORMAZIONE         = AREA_ACADEMY
AREA_EVENTI             = AREA_ACADEMY

AREE_ORDINE = [
    AREA_AGENDA,
    AREA_PAZIENTI,
    AREA_INVII,
    AREA_GAMES,
    AREA_PNEV,
    AREA_OCULISTICA,
    AREA_ORTOTTICA,
    AREA_TNPEE,
    AREA_OSTEOPATIA,
    AREA_FISIOTERAPIA,
    AREA_NPS_PSI,
    AREA_TEST_LIVE,
    AREA_TERAPIA,
    AREA_ACADEMY,
    AREA_STUDIO,
]

# ── Rami dell'area PNEV (annidati: si sceglie prima il ramo, poi la voce) ──
PNEV_RAMI = {
    "👶 PNEV Child": [
        "📋 Anamnesi PNEV",
        "🧘 Percorsi terapeutici",
        "🧩 Programma PNEV",
        "🚧 Castagnini (in arrivo)",
        "🚧 Vojta (in arrivo)",
    ],
    "👁️ PNEV Visiva": [
        "👁️ Anamnesi visiva",
        "👁️ Valutazione visuo-percettiva",
        "🔢 DEM interattivo",
        "👁️ Getman (manipolazione visiva)",
        "👁️ Groffman (visual tracing)",
        "👁️ Eye tracking",
        "🎯 Piano Vision Therapy",
        "🧘 Percorsi terapeutici",
        "🧩 Programma PNEV",
    ],
    "🧬 Integrazione sensoriale": [
        "🧬 INPP — Valutazione diagnostica",
        "🚧 Masgutova / MNRI (in arrivo)",
        "🚧 TMR — Movimenti ritmici (in arrivo)",
        "🚧 Melillo / NCHW (in arrivo)",
        "🧘 Percorsi terapeutici",
        "🧩 Programma PNEV",
    ],
    "🎧 Uditiva": [
        "🎧 Stimolazione uditiva",
        "📊 Audiometria funzionale",
        "🎧 Bilancio uditivo",
        "🎧 MAPS",
        "🗂 Programmi MAPS",
        "🧭 Percorsi MAPS",
        "🎧 MAPS-CLEAR pubblico",
        "🧘 Percorsi terapeutici",
        "🧩 Programma PNEV",
    ],
}

# Etichette delle voci "in arrivo" — vedi PLACEHOLDER_VOCI in
# app_main_router.py per il messaggio mostrato al click.
PLACEHOLDER_VOCI = [
    "🚧 Castagnini (in arrivo)",
    "🚧 Vojta (in arrivo)",
    "🚧 Masgutova / MNRI (in arrivo)",
    "🚧 TMR — Movimenti ritmici (in arrivo)",
    "🚧 Melillo / NCHW (in arrivo)",
    "🚧 Oculistica (da importare dal gestionale esistente)",
    "🚧 Ortottica (in arrivo)",
    "🚧 Fisioterapia (in arrivo)",
    "🚧 Psicologia (in arrivo)",
    "🚧 Contenuti formativi PNEV Academy (in arrivo)",
]

# ── Sottosezioni per area (tutte tranne AREA_PNEV, che usa PNEV_RAMI) ──
SOTTOSEZIONI = {
    AREA_AGENDA: [
        "📅 Agenda appuntamenti",
    ],
    AREA_PAZIENTI: [
        "🏠 Dashboard",
        "👤 Anagrafica pazienti",
        "📎 Documenti clinici",
        "🧩 Quadro storico",
        "💡 Assistente PNEV",
        "📈 Esiti / Follow-up",
        "🧪 Apprendimento PNEV",
        "📝 Diagnosi assistita",
        "📄 Modulistica / Schede da stampare",
        "🎟️ Coupon OF / SDS",
        "📅 Sedute / Terapie",
        "🔒 Privacy & Consensi",
        "📥 Import pazienti",
        "🔗 Sincronizza pnev.it",
        "🚀 Trasferisci a pnev.it",
    ],
    AREA_INVII: [
        "📋 Questionari remoti",
        "🎧 Screening uditivo",
    ],
    AREA_GAMES: [
        "🎮 Esercizi Wordwall",
    ],
    AREA_OCULISTICA: [
        "👁️ Oculistica",
        "👁️ Lenti a contatto",
    ],
    AREA_ORTOTTICA: [
        "🚧 Ortottica (in arrivo)",
    ],
    AREA_TNPEE: [
        "🗣️ Logopedia / SMOF",
    ],
    AREA_OSTEOPATIA: [
        "🦴 Osteopatia",
    ],
    AREA_ACADEMY: [
        "📅 Eventi e iscrizioni",
        "🚧 Contenuti formativi PNEV Academy (in arrivo)",
    ],
    AREA_FISIOTERAPIA: [
        "🚧 Fisioterapia (in arrivo)",
    ],
    AREA_NPS_PSI: [
        "🧠 NPS — Neuropsicologica",
        "📚 DSA — Apprendimento",
        "🚧 Psicologia (in arrivo)",
    ],
    AREA_TEST_LIVE: [
        "🖥️ Somministrazione test",
        "📸 Photoref AI",
        "📖 Lettura avanzata",
    ],
    AREA_TERAPIA: [
        "📝 Relazione clinica",
        "📄 Report PDF con grafici",
        "📊 Export statistici",
        "🧪 Caso demo",
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
