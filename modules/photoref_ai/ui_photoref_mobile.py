from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import streamlit as st
from PIL import Image
from .photoref_tokens import is_token_expired
from .photoref_storage import save_uploaded_capture
from .photoref_db import get_session_by_token, update_session_status, save_capture_record

BASE_DIR = str(Path(__file__).resolve().parent)

def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def ui_photoref_mobile():
    st.title("📱 Photoref Mobile Upload")
    st.caption("Pagina mobile per acquisizione immagine collegata al gestionale")

    token = st.query_params.get("photoref_token", "")
    if not token:
        token = st.text_input("Token sessione")

    if not token:
        st.info("Apri questa pagina da un link con token oppure inserisci il token manualmente.")
        return

    session = get_session_by_token(BASE_DIR, token)
    if not session:
        st.error("Sessione non trovata.")
        return

    if is_token_expired(session.get("expires_at", "")):
        st.error("Sessione scaduta.")
        update_session_status(BASE_DIR, token, status="expired")
        return

    update_session_status(BASE_DIR, token, status="opened", opened_at=_utc_now())

    st.success("Sessione valida")
    st.write(f"Paziente: **{session.get('patient_id','')}**")
    st.write(f"Visita: **{session.get('visit_id','')}**")
    st.write(f"Lato: **{session.get('eye_side','')}**")
    st.write(f"Tipo: **{session.get('capture_type','')}**")

    st.markdown(
        '''
### Istruzioni rapide
- distanza: **50–100 cm**
- ambiente: **semi-buio**
- sguardo: **diritto**
- evita luce frontale forte
- prova luce leggermente laterale
'''
    )

    photo = st.camera_input("Scatta una foto")
    upload = st.file_uploader("Oppure carica immagine", type=["jpg", "jpeg", "png"])
    selected = photo if photo is not None else upload

    if selected is None:
        st.info("Scatta o carica una foto per continuare.")
        return

    img = Image.open(selected).convert("RGB")
    st.image(img, caption="Anteprima", use_container_width=True)

    if st.button("Invia al gestionale"):
        saved = save_uploaded_capture(
            selected,
            patient_id=str(session.get("patient_id", "")),
            visit_id=str(session.get("visit_id", "")),
            eye_side=str(session.get("eye_side", "BINOCULAR")),
            base_dir=BASE_DIR,
        )

        capture_record = {
            "session_token": token,
            "patient_id": session.get("patient_id", ""),
            "visit_id": session.get("visit_id", ""),
            "eye_side": session.get("eye_side", ""),
            "capture_type": session.get("capture_type", ""),
            "uploaded_at": _utc_now(),
            "original_filename": getattr(selected, "name", "capture.jpg"),
            "storage_path": saved["storage_path"],
            "file_size": saved["file_size"],
            "image_width": img.size[0],
            "image_height": img.size[1],
            "source_device": "smartphone_browser",
            "quality_score": None,
            "quality_label": None,
            "reflection_label": None,
            "reflection_score": None,
            "offset_x": None,
            "offset_y": None,
            "offset_norm": None,
            "horizontal_gradient": None,
            "vertical_gradient": None,
            "analysis_json": None,
        }
        save_capture_record(BASE_DIR, capture_record)
        update_session_status(
            BASE_DIR,
            token,
            status="uploaded",
            uploaded_at=_utc_now(),
            last_storage_path=saved["storage_path"],
        )

        st.success("Foto inviata al gestionale.")
        st.caption("Nel prossimo step il desktop potrà leggere e analizzare automaticamente questa immagine.")
