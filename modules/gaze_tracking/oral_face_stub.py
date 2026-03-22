from __future__ import annotations


def get_oral_face_stub_info() -> dict:
    return {
        "enabled": False,
        "module_name": "oral_face_stub",
        "status": "placeholder",
        "future_targets": [
            "bocca",
            "orbicolare",
            "mentoniero",
            "mandibola",
            "lingua",
            "postura_testa",
            "sincronizzazione_occhio_bocca",
            "indici_multimodali_pnev",
        ],
    }
