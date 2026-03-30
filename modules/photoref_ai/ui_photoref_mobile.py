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

    st.markdown("### Checklist rapida")
    ok_light = st.checkbox("Buona illuminazione", value=True)
    ok_distance = st.checkbox("Distanza corretta", value=True)
    ok_eyes = st.checkbox("Occhi ben visibili", value=True)

    if not (ok_light and ok_distance and ok_eyes):
        st.warning("Controlla la checklist prima di acquisire la foto.")

    st.markdown("### Acquisizione immagine")
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

    image_bytes = uploaded.read()
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    st.image(image, use_container_width=True)

    if "photoref_mobile_done" not in st.session_state:
        st.session_state["photoref_mobile_done"] = False
    if "photoref_mobile_result" not in st.session_state:
        st.session_state["photoref_mobile_result"] = None

    if st.button("Analizza", type="primary") and not st.session_state["photoref_mobile_done"]:
        with st.spinner("Analisi..."):
            try:
                update_photoref_session_status(conn, photoref_token, "captured")

                result = run_photoref_analysis(
                    conn=conn,
                    image=image,
                    image_bytes=image_bytes,
                    session=session_data,
                )

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

                st.session_state["photoref_mobile_result"] = result
                st.session_state["photoref_mobile_done"] = True
                st.success("Salvato!")
            except Exception as e:
                update_photoref_session_status(conn, photoref_token, "error")
                st.error(f"Errore durante analisi/salvataggio: {e}")
                st.stop()

    result = st.session_state.get("photoref_mobile_result")
    if result:
        st.markdown("### Esito")
        st.write(result)
