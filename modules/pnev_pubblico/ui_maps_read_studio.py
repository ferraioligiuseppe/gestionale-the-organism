# -*- coding: utf-8 -*-
"""
modules/pnev_pubblico/ui_maps_read_studio.py

MAPS-Read — Fase 1: apre lo strumento di lettura con overlay colorati,
anaglifico e guida sillabica, sia per l'uso in studio sia per darlo al
paziente da usare a casa (stesso file, nessun login richiesto).
I dati di comfort pre/post restano per ora sul dispositivo del paziente
(localStorage) — non c'è ancora un salvataggio centralizzato nel gestionale.
"""
import streamlit as st

MAPS_READ_URL_DEFAULT = "https://www.pnev.it/wp-content/uploads/maps-read/MAPS-Read-v1.html"


def render_maps_read_studio(conn=None, paz_id=None, paziente=None):
    st.title("🔤 MAPS-Read — Comfort visivo nella lettura")
    st.caption("Overlay colorati (stile Irlen), sfondo pagina, anaglifico rosso/ciano e guida "
               "di lettura parola per parola — con auto-valutazione di comfort e fatica visiva "
               "prima e dopo, per capire cosa aiuta davvero questo paziente.")

    url = st.secrets.get("MAPS_READ_PLAYER_URL", MAPS_READ_URL_DEFAULT).rstrip("/")

    st.link_button("🔤 Apri MAPS-Read (nuova scheda)", url, type="primary", use_container_width=True)
    st.caption("Usalo qui in studio con il paziente davanti a te, con l'operatore che sceglie le condizioni da provare.")

    st.divider()
    st.markdown("**📋 Per l'uso a casa**")
    st.write(
        "È lo stesso identico strumento pubblicato su pnev.it: nessun account, nessun accesso richiesto. "
        "Puoi mandare questo link al genitore per farlo riprovare a casa con più calma:"
    )
    st.code(url, language=None)

    st.divider()
    st.info(
        "**Nota — Fase 1**: i risultati di ogni sessione (comfort/fatica prima e dopo) restano "
        "salvati solo sul dispositivo usato, per ora. Se serve vederli centralizzati nel diario "
        "del paziente, si può aggiungere in un secondo passaggio un salvataggio nel gestionale."
    )
