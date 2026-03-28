import streamlit as st
from PIL import Image


def ui_photoref():
    st.title("📸 Photoref AI")
    st.success("Modulo Photoref AI attivo.")

    st.markdown(
        """
        Versione stabile di transizione.

        Funzioni attuali:
        - apertura modulo dal menu
        - upload immagine
        - visualizzazione immagine
        - lettura informazioni base
        """
    )

    uploaded = st.file_uploader(
        "Carica un'immagine",
        type=["jpg", "jpeg", "png"],
        key="photoref_upload_image",
    )

    if uploaded is None:
        st.info("Carica una foto frontale del volto o degli occhi.")
        return

    img = Image.open(uploaded).convert("RGB")
    width, height = img.size

    st.subheader("Anteprima")
    st.image(img, caption="Immagine caricata", use_container_width=True)

    st.subheader("Informazioni immagine")
    c1, c2, c3 = st.columns(3)
    c1.metric("Larghezza", f"{width}px")
    c2.metric("Altezza", f"{height}px")
    c3.metric("Formato", img.format if img.format else "N/D")

    st.subheader("Stato modulo")
    st.success("Upload eseguito correttamente.")
    st.info("Il modulo è pronto per il prossimo step di analisi.")
