# -*- coding: utf-8 -*-
"""Menu principale del gestionale.

Primo step di modularizzazione: qui vive solo la definizione delle voci sidebar.
Questo riduce il rischio di rompere app.py quando si aggiungono/rimuovono sezioni.
"""

BASE_SECTIONS = [
    "Pazienti",
    "Valutazione PNEV",
    "Valutazioni visive / oculistiche",
    "Sedute / Terapie",
    "Osteopatia",
    "Coupon OF / SDS",
    "Dashboard incassi",
    "🗂️ Relazioni cliniche",
    "📊 Dashboard evolutiva",
    "📄 Privacy & Consensi (PDF)",
    "🛠️ Debug DB",
    "📥 Import Pazienti",
]

ADMIN_SECTIONS = [
    "👥 Utenti / Ruoli",
]

UDITO_PROD_SECTIONS = [
    "🎧 ORL + EQ (MODULO)",
    "🎧 Genera stimolazione (JOB)",
    "🎧 Stimolazione uditiva (TEST)",
]

UDITO_TEST_ONLY_SECTIONS = [
    "🎧 Audiogramma funzionale (TEST)",
    "🩺 Esami ORL – soglie tonali (TEST)",
    "🎚️ EQ stimolazione uditiva (TEST)",
    "🔧 Calibrazione cuffie (TEST)",
    "🧹 Pulizia DB (TEST)",
]

def build_sections(is_admin: bool, app_mode: str) -> list[str]:
    sections = list(BASE_SECTIONS)
    if is_admin:
        sections.extend(ADMIN_SECTIONS)
    sections.extend(UDITO_PROD_SECTIONS)
    if str(app_mode).lower().strip() == "test":
        sections.extend(UDITO_TEST_ONLY_SECTIONS)
    return sections
