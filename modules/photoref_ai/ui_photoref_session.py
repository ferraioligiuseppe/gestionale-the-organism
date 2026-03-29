from __future__ import annotations
from pathlib import Path
import streamlit as st
from .photoref_tokens import create_capture_token
from .photoref_db import create_capture_session, list_recent_sessions

BASE_DIR = str(Path(__file__).resolve().parent)

def _base_url_guess() -> str:
    return st.query_params.get("base_url", "") or ""

def _make_mobile_link(token: str) -> str:
    base_url = _base_url_guess()
    if base_url:
        sep = "&" if "?" in base_url else "?"
        return f"{base_url}{sep}photoref_token={token}"
    return f"?photoref_token={token}"

def ui_photoref_session(patient_id: str = "", visit_id: str = "", operator_user: str = ""):
    st.subheader("📱 Sessioni smartphone")
    with st.form("photoref_session_form"):
        c1, c2 = st.columns(2)
        patient_id = c1.text_input("Patient ID", value=patient_id)
        visit_id = c2.text_input("Visit ID", value=visit_id)
        c3, c4 = st.columns(2)
        eye_side = c3.selectbox("Lato", ["OD", "OS", "BINOCULAR"], index=2)
        capture_type = c4.selectbox("Tipo acquisizione", ["photoref", "standard_photo", "followup"], index=0)
        notes = st.text_area("Note sessione", value="")
        operator_user = st.text_input("Operatore", value=operator_user)
        submitted = st.form_submit_button("Genera sessione")
    if submitted:
        tok = create_capture_token(expire_minutes=30)
        link = _make_mobile_link(tok["token"])
        record = {"token": tok["token"], "created_at": tok["created_at"], "expires_at": tok["expires_at"], "status": "created", "patient_id": patient_id, "visit_id": visit_id, "eye_side": eye_side, "capture_type": capture_type, "operator_user": operator_user, "notes": notes, "mobile_link": link}
        create_capture_session(BASE_DIR, record)
        st.success("Sessione creata"); st.code(link, language="text")
        st.session_state["last_photoref_link"] = link
    if st.session_state.get("last_photoref_link"):
        st.markdown("**Ultimo link generato**"); st.code(st.session_state["last_photoref_link"], language="text")
    rows = list_recent_sessions(BASE_DIR, limit=20)
    if rows:
        st.markdown("**Storico sessioni recenti**")
        for row in rows:
            st.markdown(f"**{row.get('patient_id','')}** | visita **{row.get('visit_id','')}** | {row.get('eye_side','')} | stato **{row.get('status','')}**")
            if row.get("mobile_link"): st.code(row["mobile_link"], language="text")
            st.divider()
