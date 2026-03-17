"""
PNEV AI STUB (TEST ONLY)
Non usa IA vera, solo regole semplici.
Serve per non bloccare l'app e per futura integrazione.
"""

def generate_hypothesis(visita_snapshot, pnev_json):
    """Restituisce una bozza di ipotesi PNEV."""
    
    ipotesi = {
        "pattern": "Disregolazione sensoriale con impatto visuo-funzionale",
        "meccanismi": "Possibile sovraccarico sensoriale e instabilità dell’arousal",
        "mantenenti": "Affaticamento, richieste scolastiche elevate, stress ambientale",
        "ponte_visivo": "I dati visivi suggeriscono possibile interferenza funzionale con la regolazione"
    }

    return ipotesi


def generate_plan(visita_snapshot, pnev_json):
    """Restituisce una bozza di piano intervento."""
    
    piano = {
        "obiettivi_breve": [
            "Migliorare autoregolazione",
            "Ridurre affaticamento visivo"
        ],
        "obiettivi_medio": [
            "Stabilizzare integrazione sensoriale",
            "Migliorare partecipazione scolastica"
        ],
        "interventi": "Training multisensoriale, supporto visivo funzionale",
        "scuola": "Ridurre carico visivo e pause frequenti",
        "followup": "Rivalutazione tra 8 settimane"
    }

    return piano


def apply_to_session(prefix, suggestions):
    """
    Scrive i suggerimenti nei campi Streamlit.
    Non salva nel DB automaticamente.
    """
    import streamlit as st

    for key, value in suggestions.items():
        st.session_state[f"{prefix}_{key}"] = value
