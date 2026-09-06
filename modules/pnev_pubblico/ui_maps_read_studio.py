# -*- coding: utf-8 -*-
"""
modules/pnev_pubblico/ui_maps_read_studio.py

MAPS-Read — Fase 2: stesso motore/stesso salvataggio del percorso
pubblico MAPS-CLEAR (stesso utente_id, stesso paziente) — così le
condizioni visive si confrontano con i dati uditivi nello stesso
screening. Sessioni ripetute nel tempo (training), sia in studio
sia da casa tramite link con token.
"""
import streamlit as st

from modules.pnev_pubblico import db_pnev_pubblico as db

MAPS_READ_URL_DEFAULT = "https://www.pnev.it/wp-content/uploads/maps-read/MAPS-Read-v1.html"


def render_maps_read_studio(conn, paz_id, paziente):
    st.title("🔤 MAPS-Read — Comfort visivo nella lettura")
    st.caption("Overlay colorati, sfondo pagina, anaglifico rosso/ciano e guida di lettura "
               "parola per parola. Sedute ripetute nel tempo (training), collegate allo stesso "
               "paziente di MAPS-CLEAR per confrontare i dati visivi e uditivi.")

    db.init_pnev_pubblico_db(conn)
    db.init_maps_read_db(conn)

    paziente = paziente or {}
    email = (paziente.get("Email") or paziente.get("email") or "").strip()
    cognome = paziente.get("Cognome") or paziente.get("cognome") or ""
    nome = paziente.get("Nome") or paziente.get("nome") or ""

    if not email:
        st.warning("Il paziente non ha un'email in anagrafica: serve per collegare "
                   "il percorso MAPS-Read (anche fittizia se resta solo in studio).")
        email = st.text_input("Email da usare per questo paziente", key="maps_read_email_fallback")
        if not email or "@" not in email:
            st.stop()

    utente = db.get_utente_by_email(conn, email)
    if not utente:
        utente_id = db.crea_utente(conn, nome=f"{cognome} {nome}".strip(), email=email, gdpr=True)
    else:
        utente_id = utente[0]

    token = db.crea_magic_link(conn, utente_id)
    url_player = f"{MAPS_READ_URL_DEFAULT}?t={token}"

    st.link_button("🔤 Apri MAPS-Read (nuova scheda)", url_player, type="primary", use_container_width=True)
    st.caption("Usalo in studio con il paziente davanti a te, oppure manda il link al genitore per farlo riprovare a casa.")
    st.code(url_player, language=None)

    st.divider()
    st.markdown("**📋 Sessioni già registrate per questo paziente**")
    sessioni = db.get_sessioni_read(conn, utente_id)
    if not sessioni:
        st.info("Nessuna sessione ancora salvata (da casa o in studio).")
    else:
        for s in sessioni:
            _, g, data_s, contenuto, condizione, testo_usato, cpre, fpre, cpost, fpost, facilita, note = s
            st.write(f"Giorno {g} — {data_s:%d/%m/%Y %H:%M} — **{condizione}** "
                     f"— comfort {cpre}→{cpost} · fatica {fpre}→{fpost} · {facilita or '—'}")

    st.divider()
    st.markdown("**✍️ Registra una sessione fatta in studio (o riportata dal genitore)**")
    giorni_fatti = {s[1] for s in sessioni}
    giorno_default = min((g for g in range(1, 15) if g not in giorni_fatti), default=1)
    with st.form("form_sessione_read"):
        c1, c2 = st.columns(2)
        giorno = c1.number_input("Giorno del percorso", min_value=1, max_value=30, value=giorno_default)
        contenuto = c2.selectbox("Tipo di testo", ["Brano narrativo", "Testo graduato", "Sillabe/non-parole"])
        condizione = st.text_input("Condizione visiva provata", placeholder="Es: Overlay giallo, Anaglifico, Nessun supporto")
        testo_usato = st.text_input("Testo/brano usato (facoltativo)", placeholder="Es: Fascia 2 — Brano 1")
        c3, c4 = st.columns(2)
        comfort_pre = c3.slider("Comfort PRIMA (1-5)", 1, 5, 3)
        fatica_pre = c4.slider("Fatica PRIMA (1-5)", 1, 5, 3)
        c5, c6 = st.columns(2)
        comfort_post = c5.slider("Comfort DOPO (1-5)", 1, 5, 3)
        fatica_post = c6.slider("Fatica DOPO (1-5)", 1, 5, 3)
        facilita = st.selectbox("Facilità percepita rispetto a prima", 
                                 ["Molto più difficile", "Un po' più difficile", "Uguale", "Un po' più facile", "Molto più facile"], index=2)
        note = st.text_area("Note della seduta")
        if st.form_submit_button("💾 Salva sessione", type="primary"):
            if not condizione.strip():
                st.error("Indica quale condizione visiva è stata provata.")
            else:
                db.salva_sessione_read(
                    conn, utente_id, giorno=int(giorno), contenuto=contenuto,
                    condizione=condizione.strip(), testo_usato=(testo_usato or "").strip(),
                    comfort_pre=int(comfort_pre), fatica_pre=int(fatica_pre),
                    comfort_post=int(comfort_post), fatica_post=int(fatica_post),
                    facilita=facilita, note=(note or "").strip(),
                )
                st.success(f"Sessione del giorno {giorno} salvata ✅")
                st.rerun()
