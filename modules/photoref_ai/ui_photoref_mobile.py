from __future__ import annotations

import io
from typing import Any

import streamlit as st
from PIL import Image

from .photoref_mobile_service import (
    extract_token,
    get_photoref_session_by_token,
    parse_uploaded_image,
    run_photoref_analysis,
    save_photoref_capture,
    update_photoref_session_status,
)


CHECKLIST_KEY = "photoref_mobile_checklist"
DONE_KEY = "photoref_mobile_done"
RESULT_KEY = "photoref_mobile_result"
SOURCE_KEY = "photoref_mobile_source"


def _session_info_card(session_data: dict[str, Any]) -> None:
    with st.expander("Dettagli sessione", expanded=False):
        st.write(
            {
                "patient_id": session_data.get("patient_id"),
                "visit_id": session_data.get("visit_id"),
                "mode": session_data.get("mode"),
                "status": session_data.get("status"),
                "operator": session_data.get("operator"),
            }
        )


def _render_checklist() -> bool:
    st.markdown("### Checklist rapida")
    c1 = st.checkbox("Buona illuminazione", value=True, key=f"{CHECKLIST_KEY}_light")
    c2 = st.checkbox("Volto ben centrato", value=True, key=f"{CHECKLIST_KEY}_center")
    c3 = st.checkbox("Occhi ben visibili", value=True, key=f"{CHECKLIST_KEY}_eyes")
    c4 = st.checkbox("Niente mosso", value=True, key=f"{CHECKLIST_KEY}_motion")

    checklist_ok = all([c1, c2, c3, c4])
    if not checklist_ok:
        st.warning("Controlla la checklist prima di acquisire la foto.")
    return checklist_ok


def _acquire_image() -> tuple[bytes | None, str | None, Image.Image | None]:
    st.markdown("### Acquisizione immagine")
    st.caption("Prima prova con la fotocamera. Se non compare, usa il caricamento manuale come fallback.")

    photo = st.camera_input("Scatta foto del riflesso")

    uploaded = None
    source = None

    if photo is not None:
        uploaded = photo
        source = "camera"
    else:
        upload = st.file_uploader("Oppure carica una foto", type=["jpg", "jpeg", "png"])
        if upload is not None:
            uploaded = upload
            source = "upload"

    if uploaded is None:
        return None, None, None

    image_bytes, pil_image = parse_uploaded_image(uploaded)
    return image_bytes, source, pil_image


def _render_result(result: dict[str, Any]) -> None:
    st.markdown("### Esito analisi")

    if result.get("ok"):
        st.success("Analisi completata e salvata correttamente.")
    else:
        st.warning("Analisi completata con esito parziale o anomalie.")

    c1, c2 = st.columns(2)
    with c1:
        st.metric("Quality score", result.get("quality_score", "-"))
        st.write("Occhi rilevati:", result.get("eyes_detected", False))
        st.write("Riflessi rilevati:", result.get("reflex_detected", False))

    with c2:
        st.write("Sospetta anisometropia:", result.get("anisometropia_suspect", False))
        st.write("Simmetria pupillare:", result.get("pupillary_symmetry", "-"))
        st.write("Note:", result.get("notes", ""))

    ann_bytes = result.get("annotated_image_bytes")
    if ann_bytes:
        st.image(ann_bytes, caption="Immagine annotata", use_container_width=True)

    st.info("Operazione conclusa. Puoi chiudere questa schermata.")


def ui_photoref_mobile(conn=None) -> None:
    """
    UI mobile Photoref.

    - Non tocca router/menu/sidebar.
    - Va chiamata solo quando il flusso è già entrato nel modulo Photoref.
    - `conn` è opzionale: se passato, viene usato per DB query/update.
    """
    st.title("📸 Photoref Mobile")

    token = extract_token(st.query_params)
    if not token:
        st.error("Token mancante o non valido.")
        st.stop()

    session_data = get_photoref_session_by_token(token=token, conn=conn)
    if not session_data:
        st.error("Sessione Photoref non trovata o scaduta.")
        st.stop()

    st.success("Sessione riconosciuta correttamente.")
    _session_info_card(session_data)

    checklist_ok = _render_checklist()
    image_bytes, source, pil_image = _acquire_image()

    if image_bytes is None or pil_image is None:
        st.info("Scatta una foto oppure carica un'immagine per continuare.")
        st.stop()

    st.image(pil_image, caption="Immagine acquisita", use_container_width=True)

    if DONE_KEY not in st.session_state:
        st.session_state[DONE_KEY] = False
    if SOURCE_KEY not in st.session_state:
        st.session_state[SOURCE_KEY] = None

    analyze_now = st.button("Avvia analisi automatica", type="primary", disabled=not checklist_ok)

    if analyze_now and not st.session_state[DONE_KEY]:
        with st.spinner("Analisi in corso..."):
            try:
                update_photoref_session_status(token=token, status="captured", conn=conn)

                result = run_photoref_analysis(
                    pil_image=pil_image,
                    image_bytes=image_bytes,
                    session_data=session_data,
                )

                save_info = save_photoref_capture(
                    token=token,
                    session_data=session_data,
                    image_bytes=image_bytes,
                    annotated_image_bytes=result.get("annotated_image_bytes"),
                    analysis_result=result,
                    source=source or "unknown",
                    conn=conn,
                )

                result["save_info"] = save_info

                final_status = "completed" if result.get("ok") else "error"
                update_photoref_session_status(token=token, status=final_status, conn=conn)

                st.session_state[RESULT_KEY] = result
                st.session_state[DONE_KEY] = True
                st.session_state[SOURCE_KEY] = source
            except Exception as exc:
                update_photoref_session_status(token=token, status="error", conn=conn)
                st.error(f"Errore durante analisi/salvataggio: {exc}")
                st.stop()

    result = st.session_state.get(RESULT_KEY)
    if result:
        _render_result(result)
