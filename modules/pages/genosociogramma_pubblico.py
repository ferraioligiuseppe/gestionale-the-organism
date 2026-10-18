# -*- coding: utf-8 -*-
# pages/genosociogramma_pubblico.py
#
# Pagina pubblica: il paziente costruisce il suo genosociogramma da casa.
# URL: https://<app>.streamlit.app/genosociogramma_pubblico?t=<token>
# Nessun login. Il link è creato dalla scheda «A casa» del modulo Genosociogramma;
# in DB c'è solo l'hash del token. Dopo l'invio la pagina non è più modificabile.

import os
import sys

import streamlit as st

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

st.set_page_config(page_title="Il tuo albero di famiglia — The Organism", page_icon="🌳",
                   layout="centered", initial_sidebar_state="collapsed")

st.markdown("""
<style>
[data-testid="stSidebar"], [data-testid="collapsedControl"] { display:none !important; }
#MainMenu, footer, header { visibility:hidden; }
.block-container { max-width:760px !important; padding:0.8rem 1rem 4rem 1rem !important; }
input, textarea { font-size:16px !important; }
.geno-titolo { text-align:center; font-size:1.4rem; font-weight:800; color:#1D6B44; margin-bottom:0.2rem; }
.geno-sub { text-align:center; font-size:0.92rem; color:#64748b; margin-bottom:1.2rem; }
</style>
""", unsafe_allow_html=True)

CONTATTI = "📞 WhatsApp 391 3598767 · apstheorganism@gmail.com"

from modules.app_core import get_connection  # noqa: E402
from modules.genosociogramma import db_genosociogramma as db  # noqa: E402
from modules.genosociogramma.ui_genosociogramma import (editor_legami, editor_persone, editor_unioni,  # noqa: E402
                                                        mostra_mappa, token_secret)

st.session_state["_geno_pubblico"] = True
st.markdown('<div class="geno-titolo">🌳 Il tuo albero di famiglia</div>', unsafe_allow_html=True)
st.markdown('<div class="geno-sub">Studio The Organism</div>', unsafe_allow_html=True)

token = st.query_params.get("t", "")
if isinstance(token, list):
    token = token[0] if token else ""
token = (token or "").strip()
if not token:
    st.error("Link non valido: manca il codice di accesso.")
    st.caption(CONTATTI)
    st.stop()

try:
    link = db.link_da_token(get_connection(), token, token_secret())
except Exception:
    link = None
if not link or link["stato"] == "revocato":
    st.error("Link non valido. Chiedi allo studio un nuovo link.")
    st.caption(CONTATTI)
    st.stop()
if link["stato"] == "inviato":
    st.success("Hai già inviato il tuo albero allo studio. Grazie: lo guarderemo insieme al prossimo incontro.")
    st.stop()
if link["scaduto"]:
    st.error("Il link è scaduto. Chiedi allo studio un nuovo link.")
    st.caption(CONTATTI)
    st.stop()

# Connessione dello studio del paziente: get_connection() usa lo studio in sessione.
st.session_state["studio_id"] = int(link["studio_id"])
conn = get_connection()
studio_id, gid = int(link["studio_id"]), int(link["genogramma_id"])

# ---------------------------------------------------------------- consenso
if not link["consenso_il"]:
    st.markdown(
        "Ti chiediamo di ricostruire la storia della tua famiglia su tre o quattro generazioni: "
        "nonni, genitori e zii, tu con fratelli e sorelle, eventuali figli. "
        "Lo guarderemo insieme in seduta.\n\n"
        "**Come procedere.** Inserisci prima le persone che ricordi, senza chiedere a nessuno: anche quello che "
        "non sai è utile. Nei giorni seguenti puoi tornare su questo link, verificare date e fatti con i "
        "familiari e completare. Quando hai finito premi «Invia allo studio»."
    )
    with st.form("geno_consenso"):
        nome = st.text_input("Il tuo nome e cognome")
        ok = st.checkbox(
            "Ho capito che inserirò anche dati sulla salute e sulla vita dei miei familiari (malattie, cause di "
            "morte, eventi). Acconsento a che lo Studio The Organism li conservi e li usi solo per il mio "
            "percorso clinico, nel rispetto del segreto professionale."
        )
        if st.form_submit_button("Inizia", type="primary"):
            if not nome.strip() or not ok:
                st.error("Scrivi il tuo nome e spunta il consenso per continuare.")
            else:
                db.registra_consenso(conn, link["id"], nome)
                st.rerun()
    st.caption(CONTATTI)
    st.stop()

# ---------------------------------------------------------------- compilazione
g = db.carica_genogramma(conn, gid)
if g is None:
    st.error("Questo albero non è più disponibile. Contatta lo studio.")
    st.caption(CONTATTI)
    st.stop()

st.caption(f"Puoi tornare su questo link fino al {link['scade_il']:%d/%m/%Y}: quello che inserisci viene salvato "
           "subito. Comincia da te («Sono io»), poi genitori, nonni, fratelli e zii.")
t_albero, t_pers, t_coppie, t_rapporti, t_invia = st.tabs(
    ["Il tuo albero", "Persone", "Coppie", "Rapporti", "Invia"])
with t_albero:
    mostra_mappa(g, vuoto="Il disegno comparirà qui quando avrai aggiunto le persone nella scheda «Persone».")
with t_pers:
    editor_persone(conn, studio_id, gid, g, pubblico=True)
with t_coppie:
    editor_unioni(conn, studio_id, gid, g, pubblico=True)
with t_rapporti:
    editor_legami(conn, studio_id, gid, g, pubblico=True)
with t_invia:
    n = len(g["persone"])
    st.markdown(f"Hai inserito **{n} persone**, **{len(g['unioni'])} coppie** e **{len(g['legami'])} rapporti**.")
    st.write("Dopo l’invio non potrai più modificare l’albero da questo link: eventuali correzioni le faremo "
             "insieme in seduta.")
    finito = st.checkbox("Ho finito e voglio inviarlo allo studio")
    if st.button("Invia allo studio", type="primary", disabled=not finito or n == 0):
        db.segna_inviato(conn, link["id"])
        try:
            from modules.email_otp import invia_email
            for dest in ("apstheorganism@gmail.com", "dr.ferraioligiuseppe@gmail.com"):
                invia_email(dest, "[Genosociogramma] Albero inviato dal paziente",
                            f"Un paziente ha inviato il genosociogramma compilato a casa ({n} persone).\n"
                            f"Lo trovi nel gestionale: Pazienti → Scheda clinica → Genosociogramma "
                            f"(paziente id {link['paziente_id']}).")
        except Exception:
            pass
        st.rerun()
st.caption(CONTATTI)
