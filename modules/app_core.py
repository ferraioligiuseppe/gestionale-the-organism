# PATCHED app_core.py (safe import + ready for Lenti a contatto)

import streamlit as st

# SAFE IMPORT UDITO
try:
    from modules.ui_bilancio_uditivo import ui_bilancio_uditivo
except Exception:
    ui_bilancio_uditivo = None

try:
    from modules.ui_audiometria_funzionale import ui_audiometria_funzionale
except Exception:
    ui_audiometria_funzionale = None

# LENTI A CONTATTO
from modules.ui_lenti_contatto import ui_lenti_contatto

SECTION_LENTI_CONTATTO = "👁️ Lenti a contatto"

def main():
    st.sidebar.title("Menu")

    sezione = st.sidebar.selectbox(
        "Seleziona sezione",
        [
            "Dashboard",
            "Pazienti",
            "Valutazione PNEV",
            "Valutazioni visive / oculistiche",
            SECTION_LENTI_CONTATTO,
        ],
    )

    if sezione == SECTION_LENTI_CONTATTO:
        ui_lenti_contatto()
        return

    st.write(f"Sezione: {sezione}")
