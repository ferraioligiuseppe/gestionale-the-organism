# -*- coding: utf-8 -*-
"""
modules/pnev_pubblico/ui_studio_session.py

Esegue una sessione MAPS-CLEAR IN STUDIO per il paziente attivo del
gestionale — stesso motore/stesso salvataggio del percorso pubblico
(pnev_pubblico_*), così resta un'unica fonte di verità e una unica
traccia a database, sia che il paziente ascolti da casa sia in studio.

Uso: from modules.pnev_pubblico.ui_studio_session import render_maps_clear_studio
     render_maps_clear_studio(conn, paz_id, paziente_record)
"""
import streamlit as st
import streamlit.components.v1 as components

from modules.pnev_pubblico import db_pnev_pubblico as db

APP_URL_PUBBLICO_DEFAULT = "https://gestionale-the-organism-n77ucp3n4us2hmqke9ck7n.streamlit.app"


def render_maps_clear_studio(conn, paz_id, paziente):
    st.title("🎧 MAPS-CLEAR — Sessione in studio")
    st.caption("Stesso percorso di pnev.it, eseguito qui in studio col paziente. "
               "La sessione viene salvata nello stesso posto delle sessioni fatte da casa.")

    db.init_pnev_pubblico_db(conn)

    email = (paziente.get("Email") or paziente.get("email") or "").strip()
    cognome = paziente.get("Cognome") or paziente.get("cognome") or ""
    nome = paziente.get("Nome") or paziente.get("nome") or ""

    if not email:
        st.warning("Il paziente non ha un'email in anagrafica: serve per collegare "
                   "il percorso MAPS-CLEAR (anche fittizia se il percorso resta solo in studio).")
        email = st.text_input("Email da usare per questo paziente", key="maps_studio_email_fallback")
        if not email or "@" not in email:
            st.stop()

    utente = db.get_utente_by_email(conn, email)
    if not utente:
        utente_id = db.crea_utente(conn, nome=f"{cognome} {nome}".strip(), email=email, gdpr=True)
    else:
        utente_id = utente[0]

    token = db.crea_magic_link(conn, utente_id)
    base = st.secrets.get("APP_URL_PUBBLICO", APP_URL_PUBBLICO_DEFAULT).rstrip("/")
    url = f"{base}/?t={token}"

    st.link_button("🔗 Apri la sessione a schermo intero (nuova scheda)", url, type="primary")
    st.caption("Consigliato per lo studio: apri a schermo intero, così i controlli audio sono grandi.")

    with st.expander("Anteprima qui sotto (più piccola)", expanded=False):
        components.iframe(url, height=850, scrolling=True)

    st.divider()
    st.markdown("**📋 Sessioni già registrate per questo paziente**")
    sessioni = db.get_sessioni(conn, utente_id)
    if not sessioni:
        st.info("Nessuna sessione ancora salvata (da casa o in studio).")
    else:
        for s in sessioni:
            _, g, data_s, modalita, delay, orec, fpre, fpost, comfort, beneficio, note, _ = s
            st.write(f"Giorno {g} — {data_s:%d/%m/%Y %H:%M} — {modalita or '—'} "
                     f"— fluenza {fpre}→{fpost}")
