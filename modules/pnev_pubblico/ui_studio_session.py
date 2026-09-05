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
    # Il vero lettore audio (MAPS-CLEAR-v2) vive su pnev.it, non nel gestionale:
    # qui generavamo solo il link alla dashboard dei progressi, che è vuota
    # finché non si fa almeno una sessione — per questo "non partiva" nulla.
    base_player = st.secrets.get("MAPS_CLEAR_PLAYER_URL",
                                  "https://www.pnev.it/wp-content/uploads/balbuzie/MAPS-CLEAR-v2.html").rstrip("/")
    base_dash = st.secrets.get("APP_URL_PUBBLICO", APP_URL_PUBBLICO_DEFAULT).rstrip("/")
    url_player = f"{base_player}?t={token}"
    url_dash = f"{base_dash}/?t={token}"

    st.link_button("🎧 Avvia la sessione audio (nuova scheda)", url_player, type="primary")
    st.caption("Apre il vero percorso guidato con l'audio — quello che il paziente sente anche da casa su pnev.it.")
    st.link_button("📊 Vedi la dashboard progressi", url_dash)

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

    st.divider()
    st.markdown("**✍️ Registra una sessione fatta in studio**")
    st.caption("Per sedute svolte in autonomia con lo strumento Potential/Focus/Precision, "
               "senza passare dal sito — resta comunque tracciata qui e su MAPS-CLEAR pubblico.")
    giorni_fatti = {s[1] for s in sessioni}
    giorno_default = min((g for g in range(1, 8) if g not in giorni_fatti), default=1)
    with st.form("form_sessione_studio"):
        c1, c2, c3 = st.columns(3)
        giorno = c1.number_input("Giorno del percorso", min_value=1, max_value=7, value=giorno_default)
        modalita = c2.selectbox("Modalità", ["potential", "focus", "motor", "ricarica", "growth", "libero"])
        orecchio = c3.selectbox("Orecchio dominante usato", ["R", "L", "—"], index=2)
        c4, c5 = st.columns(2)
        fluency_pre = c4.slider("Fluenza prima (1-10)", 1, 10, 5)
        fluency_post = c5.slider("Fluenza dopo (1-10)", 1, 10, 5)
        c6, c7 = st.columns(2)
        comfort = c6.slider("Comfort (1-10)", 1, 10, 7)
        beneficio = c7.slider("Beneficio percepito (1-10)", 1, 10, 6)
        note = st.text_area("Note della seduta", placeholder="Es: seduta in studio con Potential, buona tenuta")
        if st.form_submit_button("💾 Salva sessione in studio", type="primary"):
            db.salva_sessione(
                conn, utente_id, giorno=int(giorno), modalita=modalita,
                delay_ms=None, orecchio=None if orecchio == "—" else orecchio,
                fluency_pre=int(fluency_pre), fluency_post=int(fluency_post),
                comfort=int(comfort), beneficio=int(beneficio),
                note=(note or "") + " [seduta in studio]",
            )
            st.success(f"Sessione del giorno {giorno} salvata ✅ — visibile anche su MAPS-CLEAR pubblico.")
            st.rerun()
