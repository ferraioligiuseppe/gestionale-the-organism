import streamlit as st
from PIL import Image
import numpy as np
from pathlib import Path
from .ui_photoref_session import ui_photoref_session
from .ui_photoref_mobile import ui_photoref_mobile
from .photoref_analysis import analyze_image
from .photoref_db import list_recent_captures, list_recent_analyses

BASE_DIR = str(Path(__file__).resolve().parent)

def _render_analysis(analysis):
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Guida", f"{analysis['guidance']['quality_icon']} {analysis['guidance']['quality_label']}")
    c2.metric("Score guida", f"{analysis['guidance']['total_score']}/100")
    c3.metric("Luminanza", f"{analysis['guidance']['brightness']}")
    c4.metric("Nitidezza", analysis['guidance']['sharpness_label'])
    st.image(analysis["overlay_img"], caption="Sovraimpressione guida", use_container_width=True)
    for m in analysis["guidance"]["messages"]:
        st.info(m)
    col1, col2 = st.columns(2)
    for title, a, col in [("Occhio sinistro", analysis["left"], col1), ("Occhio destro", analysis["right"], col2)]:
        with col:
            st.markdown(f"### {title}")
            if a["eye_rgb"] is not None: st.image(a["eye_rgb"], use_container_width=True)
            if a["overlay"] is not None: st.image(a["overlay"], caption="Pupilla + spot luminoso", use_container_width=True)
            st.write(f"**Etichetta riflesso:** {a['message']}")
            st.write(f"**Ipotesi preliminare:** {a['refractive_hypothesis']}")
    comp = analysis["comparison"]
    st.subheader("Confronto OD/OS")
    st.write(f"**Simmetria:** {comp['symmetry']}")
    if comp["delta_h"] is not None:
        x1, x2, x3 = st.columns(3)
        x1.metric("Δ gradiente H", f"{comp['delta_h']:.2f}")
        x2.metric("Δ gradiente V", f"{comp['delta_v']:.2f}")
        x3.metric("Δ reflection score", f"{comp['delta_ref']:.2f}")

def _ui_analysis():
    uploaded = st.file_uploader("Carica immagine", type=["jpg", "jpeg", "png"], key="photoref_guided_analysis_upload")
    if uploaded is None:
        st.info("Carica una foto per iniziare."); return
    img_pil = Image.open(uploaded).convert("RGB")
    analysis = analyze_image(np.array(img_pil))
    st.image(img_pil, caption="Anteprima", use_container_width=True)
    _render_analysis(analysis)

def _ui_recent():
    caps = list_recent_captures(BASE_DIR, limit=10)
    ans = list_recent_analyses(BASE_DIR, limit=10)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Catture")
        if not caps: st.info("Nessuna cattura.")
        for r in caps:
            st.write(f"**{r.get('patient_id','')}** | {r.get('eye_side','')} | checklist {r.get('checklist_score','-')} | guida {r.get('guidance_score','-')}")
    with c2:
        st.markdown("#### Analisi")
        if not ans: st.info("Nessuna analisi.")
        for r in ans:
            st.write(f"**{r.get('patient_id','')}** | {r.get('eye_side','')} | simmetria: {r.get('comparison',{}).get('symmetry','')}")

def ui_photoref():
    if st.query_params.get("photoref_token", ""):
        ui_photoref_mobile()
        return
    st.title("📸 Photoref AI")
    t1, t2, t3 = st.tabs(["Analisi riflesso", "Sessioni smartphone", "Storico rapido"])
    with t1: _ui_analysis()
    with t2: ui_photoref_session()
    with t3: _ui_recent()
