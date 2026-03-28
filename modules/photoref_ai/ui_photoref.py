import streamlit as st


def ui_photoref():
    st.title("📸 Photoref AI")
    st.success("Modulo Photoref AI caricato correttamente.")

    st.markdown(
        """
        Questa è una versione minimale di test.

        Serve solo a verificare che:
        - il menu funzioni
        - il router richiami correttamente il modulo
        - il gestionale non vada in errore
        """
    )

    uploaded = st.file_uploader(
        "Carica un'immagine di prova",
        type=["jpg", "jpeg", "png"],
        key="photoref_test_upload",
    )

    if uploaded is not None:
        st.image(uploaded, caption="Immagine caricata", use_container_width=True)
        st.info("Upload eseguito correttamente. Il modulo è attivo.")
    else:
        st.warning("Nessuna immagine caricata.")
