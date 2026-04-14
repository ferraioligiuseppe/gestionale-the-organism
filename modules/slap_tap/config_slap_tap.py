LETTER_MAPPING = {
    "p": {
        "label": "Braccio DX Alto",
        "side": "dx",
        "segment": "braccio",
        "level": "alto",
    },
    "q": {
        "label": "Braccio SX Alto",
        "side": "sx",
        "segment": "braccio",
        "level": "alto",
    },
    "b": {
        "label": "Gamba DX Alto",
        "side": "dx",
        "segment": "gamba",
        "level": "alto",
    },
    "d": {
        "label": "Gamba SX Alto",
        "side": "sx",
        "segment": "gamba",
        "level": "alto",
    },
}

VALID_LETTERS = ["b", "d", "p", "q"]

ERROR_LABELS = {
    "omissione": "Omissione",
    "errore_lateralita": "Errore di lateralità",
    "errore_segmento": "Errore di segmento corporeo",
    "errore_generico": "Errore generico",
}
