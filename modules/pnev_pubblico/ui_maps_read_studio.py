# -*- coding: utf-8 -*-
"""
modules/pnev_pubblico/ui_maps_read_studio.py

MAPS-Read — Fase 2: stesso motore/stesso salvataggio del percorso
pubblico MAPS-CLEAR (stesso utente_id, stesso paziente) — così le
condizioni visive si confrontano con i dati uditivi nello stesso
screening. Sessioni ripetute nel tempo (training), sia in studio
sia da casa tramite link con token.
"""
import base64
import os
from datetime import datetime

import streamlit as st
import streamlit.components.v1 as components

from modules.pnev_pubblico import db_pnev_pubblico as db

# Lettore MAPS-Read dentro il gestionale (stesso programma di pnev.it, versione senza blocco di dominio):
# a fine seduta manda i dati qui e la seduta si salva da sola.
_LETTORE = components.declare_component(
    "maps_read_lettore", path=os.path.join(os.path.dirname(os.path.abspath(__file__)), "maps_read_component"))

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

    tab_qui, tab_link = st.tabs(["🖥️ Usa qui nel gestionale", "🔗 Link per casa o scheda nuova"])
    with tab_qui:
        st.caption("Il lettore si apre qui sotto. Per CLEAR servono le cuffie e il permesso del microfono. "
                   "A fine seduta (💾 Salva e vedi il riepilogo) la seduta si registra da sola in questo paziente, con l'audio.")
        valore = _LETTORE(key=f"maps_read_{paz_id}", default=None)
        if isinstance(valore, dict) and valore.get("id") and valore.get("id") != st.session_state.get("maps_read_ultimo"):
            st.session_state["maps_read_ultimo"] = valore["id"]
            _salva_da_lettore(conn, utente_id, valore)
    with tab_link:
        token = db.crea_magic_link(conn, utente_id)
        url_player = f"{MAPS_READ_URL_DEFAULT}?t={token}"
        st.link_button("🔤 Apri MAPS-Read (nuova scheda)", url_player, type="primary", use_container_width=True)
        st.caption("Usalo in una scheda a parte, oppure manda il link al genitore per farlo riprovare a casa.")
        st.code(url_player, language=None)

    st.divider()
    st.markdown("**📋 Sessioni già registrate per questo paziente**")
    sessioni = db.get_sessioni_read(conn, utente_id)
    if not sessioni:
        st.info("Nessuna sessione ancora salvata (da casa o in studio).")
    else:
        for s in sessioni:
            _, g, data_s, contenuto, condizione, testo_usato, cpre, fpre, cpost, fpost, facilita, note, audio_url = s
            riga = (f"Giorno {g} — {data_s:%d/%m/%Y %H:%M} — **{condizione}** "
                    f"— comfort {cpre or '—'}→{cpost or '—'} · fatica {fpre or '—'}→{fpost or '—'} · {facilita or '—'}")
            if audio_url:
                cA, cB = st.columns([5, 1])
                cA.write(riga)
                cB.markdown(f"[🔊 Ascolta]({audio_url})")
            else:
                st.write(riga)

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
        audio_file = st.audio_input("🎙️ Registra la lettura (facoltativo, va sul gestionale)")
        if st.form_submit_button("💾 Salva sessione", type="primary"):
            if not condizione.strip():
                st.error("Indica quale condizione visiva è stata provata.")
            else:
                audio_url = None
                if audio_file is not None:
                    from modules.dropbox_upload import upload_audio_bytes
                    path = f"/maps-read/{utente_id}/giorno{int(giorno)}_{condizione.strip()[:20]}.wav"
                    audio_url = upload_audio_bytes(audio_file.getvalue(), path)
                db.salva_sessione_read(
                    conn, utente_id, giorno=int(giorno), contenuto=contenuto,
                    condizione=condizione.strip(), testo_usato=(testo_usato or "").strip(),
                    comfort_pre=int(comfort_pre), fatica_pre=int(fatica_pre),
                    comfort_post=int(comfort_post), fatica_post=int(fatica_post),
                    facilita=facilita, note=(note or "").strip(), audio_url=audio_url,
                )
                st.success(f"Sessione del giorno {giorno} salvata ✅" + (" (audio caricato)" if audio_url else ""))
                st.rerun()


def _giorno_corrente(conn, utente_id) -> int:
    """Stesso giorno se oggi c'è già una seduta, altrimenti il giorno successivo all'ultimo."""
    sessioni = db.get_sessioni_read(conn, utente_id) or []
    if not sessioni:
        return 1
    oggi = datetime.now().date()
    for s in sessioni:
        try:
            if s[2].date() == oggi:
                return int(s[1])
        except Exception:
            pass
    return max(int(s[1]) for s in sessioni) + 1


def _num(x):
    """Risposta 1-5; None se la domanda è stata saltata."""
    try:
        return int(x) if x not in (None, "", "—") else None
    except (TypeError, ValueError):
        return None


def _salva_da_lettore(conn, utente_id, v: dict) -> None:
    """Salva la seduta arrivata dal lettore incorporato (stessa tabella delle sedute da casa)."""
    giorno = _giorno_corrente(conn, utente_id)
    condizione = (v.get("condizione") or "Nessun supporto").strip()
    note = []
    a = v.get("analisi") or {}
    if a.get("disponibile"):
        note.append(f"Lettura: {a.get('secondi')} s · {a.get('wpm')} parole/min · corrette {a.get('corrette')}/{a.get('totali')}")
    c = v.get("clear") or {}
    if c:
        agg = len(c.get("aggiustamenti") or [])
        note.append(f"CLEAR: orecchio {c.get('orecchio')}, ritardo {c.get('ritardo_iniziale')}→{c.get('ritardo_finale')} ms"
                    + (f", adattivo ({agg} aggiustamenti)" if c.get("adattivo") else ""))
    audio_url = None
    if v.get("audio_b64"):
        try:
            from modules.dropbox_upload import upload_audio_bytes
            est = "webm" if "webm" in (v.get("audio_tipo") or "webm") else "ogg"
            nome = "".join(ch for ch in condizione[:24] if ch.isalnum() or ch in " -_").strip().replace(" ", "_") or "lettura"
            audio_url = upload_audio_bytes(base64.b64decode(v["audio_b64"]),
                                           f"/maps-read/{utente_id}/giorno{giorno}_{nome}_{v.get('id', '')[-6:]}.{est}")
        except Exception as e:
            st.warning(f"Audio non caricato su Dropbox ({e}): la seduta viene salvata senza audio.")
    try:
        db.salva_sessione_read(
            conn, utente_id, giorno=giorno, contenuto=v.get("contenuto") or "Brano narrativo",
            condizione=condizione, testo_usato=(v.get("testo") or "").strip(),
            comfort_pre=_num(v.get("comfort_pre")), fatica_pre=_num(v.get("fatica_pre")),
            comfort_post=_num(v.get("comfort_post")), fatica_post=_num(v.get("fatica_post")),
            facilita=None if v.get("facilita") in (None, "", "—") else v.get("facilita"),
            note=" · ".join(note), audio_url=audio_url)
        st.success(f"✓ Seduta del giorno {giorno} salvata: {condizione}" + (" (con audio)" if audio_url else ""))
    except Exception as e:
        st.error(f"Seduta non salvata: {e}")
