import streamlit as st
import qrcode
import io

# IMPORT MOBILE
from modules.photoref_ai.ui_photoref_mobile import ui_photoref_mobile


def ui_photoref(conn=None):
    # =========================
    # 🚀 REDIRECT MOBILE
    # =========================
    photoref_token = st.query_params.get("photoref_token", "")
    if isinstance(photoref_token, list):
        photoref_token = photoref_token[0] if photoref_token else ""

    if photoref_token:
        return ui_photoref_mobile(conn=conn)

    # =========================
    # 🖥️ VERSIONE DESKTOP
    # =========================
    st.title("📸 Photoref AI")

    # --- GENERAZIONE TOKEN (DEMO)
    # qui puoi collegare il tuo sistema reale
    import secrets
    token = secrets.token_urlsafe(16)

    link = f"https://testgestionale.streamlit.app/?photoref_token={token}"

    st.markdown("### 📱 Accesso da smartphone")

    # QR CODE
    qr = qrcode.make(link)
    buf = io.BytesIO()
    qr.save(buf, format="PNG")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.image(buf.getvalue(), width=250)

    with col2:
        st.write("Scansiona oppure apri:")
        st.code(link)
        st.link_button("Apri su smartphone", link)

    st.divider()

    # =========================
    # 👇 IL TUO CODICE ESISTENTE
    # =========================
    st.markdown("### Area operatore")

    # NON toccare il resto del tuo codice
    # puoi rimettere qui tabs, sessioni ecc.

    st.info("Qui resta tutto il tuo sistema attuale")
