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
        st.error("Sessione non trovata")
        st.stop()

    st.success("Sessione attiva")

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
        return

    image_bytes = uploaded.getvalue()
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    st.image(image, caption="Anteprima foto", use_container_width=True)

    if st.button("Analizza e salva", type="primary"):
        with st.spinner("Analisi in corso..."):
            try:
                update_photoref_session_status(conn, photoref_token, "captured")

                result = run_photoref_analysis(conn, image, image_bytes, session_data)

                save_photoref_capture(
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
            except Exception as e:
                update_photoref_session_status(conn, photoref_token, "error")
                st.error(f"Errore durante il salvataggio: {e}")
