# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════╗
║  APP MENU — Struttura razionalizzata PNEV (v8, Valutazione/Terapia   ║
║  separate) ║
║                                                                      ║
║  PULIZIA v9 — tre principi:                                          ║
║                                                                      ║
║  1. Ogni voce vive in UN posto solo. "Percorsi terapeutici" era      ║
║     ripetuto 6 volte (uno per disciplina) e apriva sempre la stessa  ║
║     schermata: la disciplina si sceglie DENTRO il modulo, non dal    ║
║     menu. Stesso criterio per Programma PNEV, Animazioni riflessi,   ║
║     Apprendimento PNEV, Lettura avanzata.                            ║
║                                                                      ║
║  2. Niente voci vuote. I "🚧 …(in arrivo)" non compaiono più nel      ║
║     menu: una voce che non fa nulla insegna a diffidare del menu.    ║
║     PLACEHOLDER_VOCI resta solo come rete di sicurezza del router,   ║
║     per vecchi link salvati.                                         ║
║                                                                      ║
║  3. Nessuna colonna oltre ~10 voci. Pazienti (21 voci) è ora         ║
║     raggruppata in 5 rami per momento di lavoro.                     ║
║                                                                      ║
║  Per riattivare un'area sospesa (Ortottica, Fisioterapia): rimetti   ║
║  la sua costante in AREE_ORDINE e le voci in SOTTOSEZIONI.           ║
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
AREA_PNEV          = "🧠 Valutazione PNEV"
AREA_TERAPIA_PNEV  = "🧘 Terapia"
AREA_OCULISTICA    = "👁️ Oculistica · LAC"
AREA_ORTOTTICA     = "🩺 Ortottica"
AREA_TNPEE         = "🗣️ Logopedia / TNPEE"
AREA_PECS          = "🖼️ PECS — CAA"
AREA_OSTEOPATIA    = "🦴 Osteopatia"
AREA_MATERIALI     = "📚 Materiali"
AREA_ACADEMY       = "🎓 PNEV Academy"
AREA_FISIOTERAPIA  = "🏃 Fisioterapia"
AREA_TEST_LIVE     = "🖥️ Test live"
AREA_SCREENING     = "🩺 Screening"
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
AREA_NPS_PSI            = AREA_PNEV  # alias legacy: la sezione NPS/Psicologia confluisce in Valutazione PNEV

AREE_ORDINE = [
    AREA_AGENDA,
    AREA_PAZIENTI,
    AREA_INVII,
    AREA_PNEV,
    AREA_TERAPIA_PNEV,
    AREA_OCULISTICA,
    AREA_TNPEE,
    AREA_PECS,
    AREA_OSTEOPATIA,
    AREA_SCREENING,
    AREA_TEST_LIVE,
    AREA_MATERIALI,
    AREA_TERAPIA,
    AREA_ACADEMY,
    AREA_STUDIO,
]

# ── Rami dell'area Valutazione PNEV (solo assessment — le procedure di
#    trattamento vivono nell'area Terapia qui sotto) ──────────────────
PNEV_RAMI = {
    "🧬 Riflessi primitivi": [
        "📋 Anamnesi PNEV",
        "🧬 INPP — Valutazione diagnostica",
    ],
    "👁️ Visiva": [
        "👁️ Anamnesi visiva",
        "👁️ Valutazione visuo-percettiva",
        "🔢 DEM interattivo",
        "👁️ Getman (manipolazione visiva)",
        "👁️ Groffman (visual tracing)",
        "👁️ Eye tracking",
    ],
    "🧠 Neurologica e posturale": [
        "🩶 Postura (Wii Balance Board)",
        "⚡ Protocollo Epilessia",
    ],
    "🎧 Uditiva": [
        "🔉 Diagnostica uditiva completa",
        "📊 Audiometria funzionale",
        "🎧 Bilancio uditivo",
        "🎧 Audiometria tonale calibrata",
        # NON è la calibrazione dello studio (quella sta in Diagnostica
        # uditiva completa → Calibrazione, ed è l'unica che il test tonale
        # legge). Questa è la raccolta di curve inviate dallo strumento
        # pubblico su pnev.it, utile come riferimento per modello.
        "🌐 Curve cuffie condivise (pnev.it)",
    ],
    "📚 Apprendimenti": [
        "📚 Strumenti open",
        "📚 DSA — Apprendimento",
        "📖 Lettura avanzata",
    ],
    "🔬 Test psicologici": [
        "🧠 NPS — Neuropsicologica",
        "🌐 WHODAS 2.0",
    ],
}

# ── Area Terapia — elenco piatto ──────────────────────────────────────
# Prima era divisa in 6 rami per disciplina, ma "🧘 Percorsi terapeutici"
# compariva in tutti e sei aprendo sempre lo stesso identico modulo: la
# disciplina non è una sezione del menu, è un filtro DENTRO il modulo
# (il selettore "Percorso terapeutico" in cima a Percorsi terapeutici).
# Sei etichette per una schermata sola facevano solo rumore.
TERAPIA_RAMI = {}

# ── Rami dell'area Pazienti ───────────────────────────────────────────
# Erano 21 voci in un'unica colonna: troppe per sceglierne una a colpo
# d'occhio. Raggruppate per momento di lavoro, non per funzione.
PAZIENTI_RAMI = {
    "🏠 Panoramica": [
        "🏠 Dashboard",
        "👤 Anagrafica pazienti",
        "🧩 Quadro storico",
        # Statistiche sull'efficacia dei trattamenti dello studio: stava
        # sotto "Apprendimenti", dove "apprendimento" indica quello del
        # bambino — due significati opposti sotto la stessa parola.
        "🧭 Bussola degli esiti",
    ],
    "📁 Scheda clinica": [
        "📎 Documenti clinici",
        "🗓️ Diario clinico",
        "📝 Diagnosi assistita",
        "📅 Sedute / Terapie",
        "📈 Esiti / Follow-up",
        "🔒 Privacy & Consensi",
    ],
    "💡 Strumenti": [
        "💡 Assistente PNEV",
        "📄 Modulistica / Schede da stampare",
        "🎟️ Coupon OF / SDS",
    ],
    "🌐 Dal sito pnev.it": [
        "📨 Contatti dal sito",
        "📋 Questionari dal sito",
        "🎧 Aderenza ascolti MAPS",
        "📝 Consensi ascolti MAPS",
        "🔗 Sincronizza pnev.it",
        "🚀 Trasferisci a pnev.it",
    ],
    "📥 Dati": [
        "📥 Import pazienti",
    ],
}

# Aree ramificate (menu a 2 livelli: ramo poi voce). Il router usa questo
# dizionario invece di agganciarsi a una sola area — così si possono avere
# più aree con rami senza toccare app_main_router.py.
RAMI_PER_AREA = {
    AREA_PAZIENTI: PAZIENTI_RAMI,
    AREA_PNEV: PNEV_RAMI,
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
    AREA_TERAPIA_PNEV: [
        # Il piano sta in cima perche' e' il punto da cui si guarda il
        # paziente: obiettivi, settimana corrente e aderenza di TUTTI i
        # percorsi insieme. Le voci sotto restano quelle di prima.
        "🎯 Piano di trattamento",
        "🧘 Percorsi terapeutici",
        "🧩 Programma PNEV",
        "🎯 Piano Vision Therapy",
        "🎧 MAPS",
        "🗂 Programmi MAPS",
        "🧭 Percorsi MAPS",
        "🎧 MAPS-CLEAR in studio",
        "🎧 MAPS-CLEAR pubblico",
        "🔤 MAPS-Read",
    ],
    AREA_INVII: [
        "📋 Questionari remoti",
        "🎧 Screening uditivo",
        "📋 Consenso screening scolastico",
    ],
    AREA_OCULISTICA: [
        # Non e' solo un nome: la scheda contiene sia la parte oculistica
        # (tono, CCT, fondo, OCT, esame obiettivo) sia quella optometrica
        # (accomodazione, vergenze, AC/A, dominanza). Il tipo di visita si
        # sceglie in cima alla schermata, non qui.
        "👁️ Visita oculistica / optometrica",
        "👁️ Contattologia",
    ],
    AREA_OSTEOPATIA: [
        "🦴 Osteopatia",
    ],
    AREA_SCREENING: [
        "🩺 Screening rapido",
        "🩺 Screening breve (15 min)",
        "🧸 Screening 0-4 anni",
        "🩺 Screening completo",
    ],
    AREA_TNPEE: [
        "🗣️ Logopedia / SMOF",
        "🤸 Psicomotricità funzionale",
    ],
    AREA_PECS: [
        "🖼️ PECS — CAA",
    ],
    AREA_MATERIALI: [
        "📐 PNEV-Chart (schede stampabili)",
        "🥁 PNEV Metronomo",
        "🎬 Animazioni dei riflessi",
        "🕹️ PNEV Game Center",
        "🎮 Esercizi Wordwall",
        "🏃 PNEV Sport Vision",
    ],
    AREA_ACADEMY: [
        "📅 Eventi e iscrizioni",
    ],
    AREA_TEST_LIVE: [
        "🖥️ Somministrazione test",
        "📸 Photoref AI",
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
        "🩺 Diagnostica moduli",
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
