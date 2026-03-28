import streamlit as st
from PIL import Image


def ui_photoref():
    st.title("📸 Photoref AI")
    st.success("Modulo Photoref AI caricato correttamente.")

    st.markdown(
        """
        Versione compatibile senza OpenCV.

        Serve per:
        - verificare il menu
        - caricare immagini
        - mantenere il modulo attivo senza errori di dipendenze
        """
    )

    uploaded = st.file_uploader(
        "Carica un'immagine di prova",
        type=["jpg", "jpeg", "png"],
        key="photoref_test_upload",
    )

    if uploaded is not None:
        img = Image.open(uploaded).convert("RGB")
        st.image(img, caption="Immagine caricata", use_container_width=True)

        st.info("Upload eseguito correttamente.")
        st.write("Analisi disponibile in versione base compatibile.")
    else:
        st.warning("Nessuna immagine caricata.")
