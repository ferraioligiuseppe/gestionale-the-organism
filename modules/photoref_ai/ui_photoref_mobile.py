import io
import streamlit as st
from PIL import Image

from modules.photoref_ai.photoref_mobile_service import (
    get_photoref_session_by_token,
    update_photoref_session_status,
    run_photoref_analysis,
    save_photoref_capture,
)


def ui_photoref_mobile(conn=None):
    st.title("📸 Photoref Mobile")

    photoref_token = st.query_params.get("photoref_token", "")
    if isinstance(photoref_token, list):
        photoref_token = photoref_token[0] if photoref_token else ""

    if not photoref_token:
        st.error("Token non valido")
        st.stop()

    session_data = get_photoref_session_by_token(conn, photoref_token)
    if not session_data:
        st.error("Sessione non trovata. Rigenera il link dal desktop.")
        st.stop()

    st.success("Sessione attiva")
    st.caption(f"Session ID: {session_data.get('id')} | Token: {session_data.get('token')}")

    photo = st.camera_input("Scatta foto")

    uploaded = None
    source = None

    if photo is not None:
        uploaded = photo
        source = "camera"
    else:
        file = st.file_uploader("Oppure carica", type=["jpg", "jpeg", "png"])
        if file is not None:
            uploaded = file
            source = "upload"

    if uploaded is None:
        st.info("Scatta o carica una foto per continuare.")
        return

    image_bytes = uploaded.getvalue()
    image_len = len(image_bytes) if image_bytes else 0

    try:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception as e:
        st.error(f"Errore apertura immagine: {e}")
        st.stop()

    st.image(image, caption="Anteprima foto", use_container_width=True)

    with st.expander("Debug acquisizione", expanded=True):
        st.write("session_id:", session_data.get("id"))
        st.write("source:", source)
        st.write("image_bytes_len:", image_len)

    if st.button("Analizza e salva", type="primary"):
        with st.spinner("Analisi in corso..."):
            try:
                session_id = session_data.get("id")
                if not session_id:
                    raise ValueError("Sessione senza id: impossibile salvare.")

                if not image_bytes:
                    raise ValueError("Immagine vuota: nessun byte acquisito.")

                update_photoref_session_status(conn, photoref_token, "captured")

                result = run_photoref_analysis(conn, image, image_bytes, session_data)

                st.write("DEBUG result:", {
                    "ok": result.get("ok"),
                    "quality_score": result.get("quality_score"),
                    "has_annotated": bool(result.get("annotated_image_bytes")),
                })

                save_info = save_photoref_capture(
                    conn=conn,
                    session=session_data,
                    image_bytes=image_bytes,
                    annotated=result.get("annotated_image_bytes"),
                    result=result,
                    source=source,
                )

                update_photoref_session_status(
                    conn,
                    photoref_token,
                    "completed" if result.get("ok") else "error"
                )

                st.success("Foto e analisi salvate correttamente")
                st.write(result)

                if save_info:
                    st.success(f"Capture salvata con id: {save_info.get('capture_id')}")
                    st.caption(f"Bytes immagine salvati: {save_info.get('image_bytes_len')}")

            except Exception as e:
                update_photoref_session_status(conn, photoref_token, "error")
                st.error(f"Errore durante il salvataggio: {e}")
