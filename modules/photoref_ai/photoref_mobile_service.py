import json


def get_photoref_session_by_token(conn, token):
    if not token:
        return None

    # TEST SAFE MODE: non usa il DB per recuperare la sessione.
    # Così il flusso mobile parte anche se le tabelle non esistono ancora.
    return {
        "id": None,
        "token": token,
        "patient_id": None,
        "visit_id": None,
        "mode": "BINOCULAR",
        "status": "created",
    }


def update_photoref_session_status(conn, token, status):
    # TEST SAFE MODE: logga soltanto senza usare il DB.
    print("STATUS MOCK:", token, status)


def run_photoref_analysis(conn, image, image_bytes, session):
    width, height = image.size
    ratio = round(min(width, height) / max(width, height), 3) if max(width, height) else 0
    return {
        "ok": True,
        "quality_score": ratio,
        "eye_detected": True,
        "reflex_detected": True,
        "anisometropia_suspect": False,
        "notes": "demo",
        "annotated_image_bytes": None,
    }


def save_photoref_capture(conn, session, image_bytes, annotated, result, source):
    # TEST SAFE MODE: nessun salvataggio su DB per ora.
    print("SAVE MOCK:", {
        "token": session.get("token"),
        "source": source,
        "result": result,
    })
