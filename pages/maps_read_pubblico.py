# -*- coding: utf-8 -*-
# pages/maps_read_pubblico.py
#
# Pagina pubblica per registrare una sessione MAPS-Read fatta a casa.
# URL: https://<app>.streamlit.app/maps_read_pubblico?t=<token>&giorno=..&contenuto=..
#      &condizione=..&testo=..&comfort_pre=..&fatica_pre=..&comfort_post=..&fatica_post=..&facilita=..
# Nessun login richiesto — il token collega automaticamente al paziente giusto.

import streamlit as st
import sys, os

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from modules.app_core import get_connection
from modules.pnev_pubblico import db_pnev_pubblico as db

st.set_page_config(
    page_title="The Organism — MAPS-Read",
    page_icon="🔤",
    layout="centered",
    initial_sidebar_state="collapsed",
)
st.markdown("""
<style>
[data-testid="stSidebar"], [data-testid="collapsedControl"] { display:none !important; }
#MainMenu, footer, header { visibility:hidden; }
.block-container { max-width:560px !important; padding:1.2rem 1rem 3rem 1rem !important; }
</style>
""", unsafe_allow_html=True)

conn = get_connection()
db.init_pnev_pubblico_db(conn)
db.init_maps_read_db(conn)

qp = st.query_params
token = (qp.get("t", "") or "").strip()

st.markdown("### 🔤 MAPS-Read — Registra la sessione")

if not token:
    st.warning("Link non valido: manca il codice di collegamento al paziente.")
    st.caption("📞 0815152334 · dr.ferraioligiuseppe@gmail.com")
    st.stop()

utente_id = db.valida_magic_link(conn, token)
if not utente_id:
    st.error("⛔ Link scaduto o non valido. Chiedi allo studio un nuovo link.")
    st.caption("📞 0815152334 · dr.ferraioligiuseppe@gmail.com")
    st.stop()

if "mr_inviato" not in st.session_state:
    st.session_state.mr_inviato = False

if st.session_state.mr_inviato:
    st.success("✅ Sessione registrata! Grazie — i dati sono arrivati allo studio.")
    st.caption("Puoi chiudere questa pagina.")
    st.stop()

def _q(name, default=""):
    return (qp.get(name, default) or default)

st.caption("Compila con i valori mostrati da MAPS-Read alla fine della sessione, poi invia.")

with st.form("form_maps_read_pubblico"):
    giorno = st.number_input("Giorno del percorso", min_value=1, max_value=30,
                              value=int(_q("giorno", "1") or 1))
    contenuto = st.selectbox("Tipo di testo", ["Brano narrativo", "Testo graduato", "Sillabe/non-parole"],
                              index=["Brano narrativo", "Testo graduato", "Sillabe/non-parole"].index(_q("contenuto", "Brano narrativo")) if _q("contenuto") in ["Brano narrativo", "Testo graduato", "Sillabe/non-parole"] else 0)
    condizione = st.text_input("Condizione visiva provata", value=_q("condizione", ""))
    testo_usato = st.text_input("Testo/brano usato", value=_q("testo", ""))
    c1, c2 = st.columns(2)
    comfort_pre = c1.slider("Comfort PRIMA (1-5)", 1, 5, int(_q("comfort_pre", "3") or 3))
    fatica_pre = c2.slider("Fatica PRIMA (1-5)", 1, 5, int(_q("fatica_pre", "3") or 3))
    c3, c4 = st.columns(2)
    comfort_post = c3.slider("Comfort DOPO (1-5)", 1, 5, int(_q("comfort_post", "3") or 3))
    fatica_post = c4.slider("Fatica DOPO (1-5)", 1, 5, int(_q("fatica_post", "3") or 3))
    opz_facilita = ["Molto più difficile", "Un po' più difficile", "Uguale", "Un po' più facile", "Molto più facile"]
    _def_fac = _q("facilita", "Uguale")
    facilita = st.selectbox("Facilità percepita rispetto a prima", opz_facilita,
                             index=opz_facilita.index(_def_fac) if _def_fac in opz_facilita else 2)
    note = st.text_area("Note (facoltativo)", value=_q("note", ""))
    audio_file = st.audio_input("🎙️ Se hai registrato la lettura, caricala qui (facoltativo)")
    submitted = st.form_submit_button("📤 INVIA AL GESTIONALE", type="primary", use_container_width=True)

if submitted:
    if not condizione.strip():
        st.error("Indica quale condizione visiva è stata provata.")
    else:
        try:
            audio_url = None
            if audio_file is not None:
                from modules.dropbox_upload import upload_audio_bytes
                path = f"/maps-read/{utente_id}/giorno{int(giorno)}_{condizione.strip()[:20]}.wav"
                audio_url = upload_audio_bytes(audio_file.getvalue(), path)
            db.salva_sessione_read(
                conn, utente_id, giorno=int(giorno), contenuto=contenuto,
                condizione=condizione.strip(), testo_usato=testo_usato.strip(),
                comfort_pre=int(comfort_pre), fatica_pre=int(fatica_pre),
                comfort_post=int(comfort_post), fatica_post=int(fatica_post),
                facilita=facilita, note=note.strip(), audio_url=audio_url,
            )
            st.session_state.mr_inviato = True
            st.rerun()
        except Exception as e:
            st.error(f"Errore salvataggio: {e}\n\nRiprova o contatta lo studio: 📞 0815152334")
