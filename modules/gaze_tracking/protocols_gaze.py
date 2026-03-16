from __future__ import annotations


def get_gaze_protocols() -> list[dict]:
    return [
        {
            "code": "READING_STANDARD",
            "label": "Lettura standard",
            "description": "Analisi lettura clinica base con metriche di regressione, fissazione e saccadi.",
        },
        {
            "code": "VISUAL_ATTENTION",
            "label": "Attenzione visiva",
            "description": "Task di attenzione visiva e tenuta del target.",
        },
        {
            "code": "OCULOMOTOR_SCREENING",
            "label": "Screening oculomotorio",
            "description": "Screening generale di inseguimenti, saccadi e stabilità.",
        },
        {
            "code": "BINOCULARITY_BASIC",
            "label": "Binocularità base",
            "description": "Analisi di base se disponibili dati OD/OS.",
        },
    ]


def get_protocol_labels() -> list[str]:
    return [p["label"] for p in get_gaze_protocols()]


def protocol_label_to_code(label: str) -> str:
    for p in get_gaze_protocols():
        if p["label"] == label:
            return p["code"]
    return "READING_STANDARD"
