from collections import Counter


def build_slap_tap_report(scoring: dict, bpm: int, mode: str, notes: str | None = None) -> str:
    rows = scoring.get("rows", [])
    total = scoring.get("total", 0)
    symbol_accuracy = scoring.get("symbol_accuracy", 0)
    timing_accuracy = scoring.get("timing_accuracy", 0)

    error_counter = Counter()
    timing_counter = Counter()

    for r in rows:
        if not r.get("correct") and r.get("error_type"):
            error_counter[r["error_type"]] += 1
        if r.get("timing_label"):
            timing_counter[r["timing_label"]] += 1

    interpretazione = []

    if symbol_accuracy >= 85:
        interpretazione.append(
            "Buona discriminazione simbolica e buona tenuta dell’associazione corpo-lettera."
        )
    elif symbol_accuracy >= 60:
        interpretazione.append(
            "Prestazione discreta, con presenza di errori non costanti nella conversione simbolo-risposta."
        )
    else:
        interpretazione.append(
            "Difficoltà significativa nell’associazione simbolo-risposta, da approfondire sul piano visuo-motorio e della lateralità."
        )

    if error_counter.get("errore_lateralita", 0) > 0:
        interpretazione.append(
            "Si osservano errori di lateralità, compatibili con instabilità dx/sx o con debolezza nella codifica spaziale."
        )

    if error_counter.get("errore_segmento", 0) > 0:
        interpretazione.append(
            "Sono presenti errori di segmento corporeo, suggestivi di difficoltà nell’associazione tra grafema e schema corporeo."
        )

    if timing_accuracy < 60:
        interpretazione.append(
            "La tenuta temporale sul metronomo appare fragile, con anticipi/ritardi che indicano difficoltà di sincronizzazione ritmica."
        )
    elif timing_accuracy < 85:
        interpretazione.append(
            "La sincronizzazione ritmica è discreta ma ancora instabile in alcuni passaggi."
        )
    else:
        interpretazione.append(
            "Buona sincronizzazione ritmica rispetto al metronomo."
        )

    text = f"""
SLAP TAP – Report sintetico

Parametri sessione
- BPM: {bpm}
- Modalità: {mode}
- Numero item: {total}

Prestazione
- Accuratezza simbolica: {symbol_accuracy}%
- Accuratezza temporale: {timing_accuracy}%

Distribuzione errori simbolici
- Errori di lateralità: {error_counter.get('errore_lateralita', 0)}
- Errori di segmento corporeo: {error_counter.get('errore_segmento', 0)}
- Omissioni: {error_counter.get('omissione', 0)}
- Errori generici: {error_counter.get('errore_generico', 0)}

Distribuzione timing
- In tempo: {timing_counter.get('in_tempo', 0)}
- Anticipi: {timing_counter.get('anticipo', 0)}
- Ritardi: {timing_counter.get('ritardo', 0)}
- Mancate risposte: {timing_counter.get('mancata_risposta', 0)}

Interpretazione clinica
- {' '.join(interpretazione)}
""".strip()

    if notes:
        text += f"\n\nNote operatore\n- {notes}"

    return text
