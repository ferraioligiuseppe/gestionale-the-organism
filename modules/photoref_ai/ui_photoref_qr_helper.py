import io
import streamlit as st
import qrcode


def render_photoref_qr_block(token: str, base_url: str = "https://testgestionale.streamlit.app") -> str:
    """
    Renderizza un blocco QR per il link mobile Photoref.
    Restituisce il link completo generato.
    """
    if not token:
        st.warning("Token Photoref mancante.")
        return ""

    link = f"{base_url.rstrip('/')}/?photoref_token={token}"

    st.markdown("### 📱 Accesso da smartphone")
    st.success("Scansiona il QR con il telefono oppure apri il link")

    qr = qrcode.make(link)
    buf = io.BytesIO()
    qr.save(buf, format="PNG")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.image(buf.getvalue(), width=260, caption="QR Photoref")

    with col2:
        st.write("Link diretto:")
        st.code(link)
        st.link_button("Apri link", link)

    return link
