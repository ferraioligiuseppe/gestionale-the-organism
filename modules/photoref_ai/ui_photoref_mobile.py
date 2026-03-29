from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import streamlit as st
from PIL import Image
import numpy as np
from .photoref_tokens import is_token_expired
from .photoref_storage import save_uploaded_capture
from .photoref_db import get_session_by_token, update_session_status, save_capture_record, save_analysis_record
from .photoref_analysis import analyze_image, traffic_light

BASE_DIR = str(Path(__file__).resolve().parent)

def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _show_checklist():
    st.subheader("✅ Checklist guidata")
    items = [
        st.checkbox("Ambiente semi-buio", value=True),
        st.checkbox("Luce non frontale diretta", value=True),
        st.checkbox("Distanza circa 50–100 cm", value=True),
        st.checkbox("Sguardo diritto verso la camera", value=True),
        st.checkbox("Blink prima dello scatto", value=True),
        st.checkbox("Paziente fermo", value=True),
    ]
    score_perc = int(sum(items) / 6 * 100)
    icon, label = traffic_light(score_perc)
    st.progress(score_perc)
    st.write(f"Checklist: **{icon} {label} ({score_perc}/100)**")
    return score_perc

def _render_analysis(analysis):
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Guida", f"{analysis['guidance']['quality_icon']} {analysis['guidance']['quality_label']}")
    c2.metric("Score guida", f"{analysis['guidance']['total_score']}/100")
    c3.metric("Luminanza", f"{analysis['guidance']['brightness']}")
    c4.metric("Nitidezza", analysis['guidance']['sharpness_label'])
    st.image(analysis["overlay_img"], caption="Maschera guida", use_container_width=True)
    col1, col2 = st.columns(2)
    for title, a, col in [("Occhio sinistro", analysis["left"], col1), ("Occhio destro", analysis["right"], col2)]:
        with col:
            st.markdown(f"### {title}")
            if a["eye_rgb"] is not None: st.image(a["eye_rgb"], use_container_width=True)
            if a["overlay"] is not None: st.image(a["overlay"], caption="Pupilla + bright spot", use_container_width=True)
            st.write(f"**Etichetta:** {a['message']}")
            st.write(f"**Ipotesi preliminare:** {a['refractive_hypothesis']}")
    st.subheader("Confronto OD/OS")
    comp = analysis["comparison"]
    st.write(f"**Simmetria:** {comp['symmetry']}")
    if comp["delta_h"] is not None:
        x1, x2, x3 = st.columns(3)
        x1.metric("Δ gradiente H", f"{comp['delta_h']:.2f}")
        x2.metric("Δ gradiente V", f"{comp['delta_v']:.2f}")
        x3.metric("Δ reflection score", f"{comp['delta_ref']:.2f}")

def ui_photoref_mobile():
    st.title("📱 Photoref Mobile")
    st.caption("Upload automatico + checklist guidata + analisi avanzata")
    token = st.query_params.get("photoref_token", "") or st.text_input("Token sessione")
    if not token:
        st.info("Apri questa pagina da un link con token oppure inserisci il token manualmente.")
        return
    session = get_session_by_token(BASE_DIR, token)
    if not session:
        st.error("Sessione non trovata."); return
    if is_token_expired(session.get("expires_at", "")):
        st.error("Sessione scaduta."); update_session_status(BASE_DIR, token, status="expired"); return
    update_session_status(BASE_DIR, token, status="opened", opened_at=_utc_now())
    st.success("Sessione valida")
    st.write(f"Paziente: **{session.get('patient_id','')}**")
    st.write(f"Visita: **{session.get('visit_id','')}**")
    st.write(f"Lato: **{session.get('eye_side','')}**")
    checklist_score = _show_checklist()
    auto_send = st.toggle("Invio automatico dopo selezione immagine", value=True)
    mode = st.radio("Modalità", ["Scatta foto", "Carica 1 immagine", "Carica 3 immagini e scegli la migliore"], horizontal=True)
    selected = None
    if mode == "Scatta foto":
        selected = st.camera_input("Scatta una foto")
    elif mode == "Carica 1 immagine":
        selected = st.file_uploader("Carica immagine", type=["jpg", "jpeg", "png"], key="mobile_single")
    else:
        uploads = st.file_uploader("Carica fino a 3 immagini", type=["jpg", "jpeg", "png"], accept_multiple_files=True, key="mobile_multi")
        if uploads:
            labels = [getattr(u, "name", f"frame_{i+1}.jpg") for i, u in enumerate(uploads[:3])]
            choice = st.radio("Seleziona il frame migliore", labels)
            selected = uploads[labels.index(choice)]
    if selected is None:
        st.info("Seleziona un'immagine per continuare."); return
    img = Image.open(selected).convert("RGB"); img_rgb = np.array(img)
    st.image(img, caption="Anteprima", use_container_width=True)
    analysis = analyze_image(img_rgb)
    _render_analysis(analysis)
    if auto_send or st.button("Invia al gestionale", type="primary"):
        saved = save_uploaded_capture(selected, patient_id=str(session.get("patient_id","")), visit_id=str(session.get("visit_id","")), eye_side=str(session.get("eye_side","BINOCULAR")), base_dir=BASE_DIR)
        capture_record = {"session_token": token, "patient_id": session.get("patient_id",""), "visit_id": session.get("visit_id",""), "eye_side": session.get("eye_side",""), "capture_type": session.get("capture_type",""), "uploaded_at": _utc_now(), "original_filename": getattr(selected,"name","capture.jpg"), "storage_path": saved["storage_path"], "file_size": saved["file_size"], "image_width": img.size[0], "image_height": img.size[1], "source_device": "smartphone_browser", "checklist_score": checklist_score, "guidance_score": analysis["guidance"]["total_score"]}
        save_capture_record(BASE_DIR, capture_record)
        ana_record = {"session_token": token, "patient_id": session.get("patient_id",""), "visit_id": session.get("visit_id",""), "eye_side": session.get("eye_side",""), "analyzed_at": _utc_now(), "guidance": analysis["guidance"], "left": {"message": analysis["left"]["message"], "refractive_hypothesis": analysis["left"]["refractive_hypothesis"], "reflection_score": analysis["left"]["bright_spot"]["reflection_score"] if analysis["left"]["bright_spot"] else None}, "right": {"message": analysis["right"]["message"], "refractive_hypothesis": analysis["right"]["refractive_hypothesis"], "reflection_score": analysis["right"]["bright_spot"]["reflection_score"] if analysis["right"]["bright_spot"] else None}, "comparison": analysis["comparison"]}
        save_analysis_record(BASE_DIR, ana_record)
        update_session_status(BASE_DIR, token, status="uploaded_analyzed", uploaded_at=_utc_now(), analyzed_at=_utc_now(), last_storage_path=saved["storage_path"])
        st.success("Foto inviata e analizzata automaticamente.")
