# -*- coding: utf-8 -*-
# pages/pnev_pubblico.py
#
# Pagina pubblica questionari PNEV — The Organism
# URL: https://<app>.streamlit.app/pnev_pubblico?q=INPPS&t=<token>
# Nessun login richiesto.

import streamlit as st
import sys, os

# Root nel path
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from modules.public_questionnaires import (
    init_public_tokens_table,
    validate_public_token,
    mark_token_used,
    save_inpps_response,
    REGISTRY,
)

st.set_page_config(
    page_title="The Organism — Questionario PNEV",
    page_icon="🌿",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
[data-testid="stSidebar"], [data-testid="collapsedControl"] { display:none !important; }
#MainMenu, footer, header { visibility:hidden; }
* { -webkit-text-fill-color: #1e293b !important; }
.block-container { max-width:620px !important; padding:0.8rem 1rem 4rem 1rem !important; }
.pnev-titolo {
    text-align:center; font-size:1.35rem; font-weight:800;
    color:#1D6B44 !important; -webkit-text-fill-color:#1D6B44 !important;
    margin-bottom:0.15rem;
}
.pnev-sub {
    text-align:center; font-size:0.85rem;
    color:#64748b !important; -webkit-text-fill-color:#64748b !important;
    margin-bottom:1.2rem;
}
.completato-box {
    background:#f0fdf4; border:2px solid #1D6B44;
    border-radius:12px; padding:2rem; text-align:center; margin-top:1.5rem;
}
</style>
""", unsafe_allow_html=True)

try:
    init_public_tokens_table()
except Exception as e:
    st.error(f"Errore DB: {e}")
    st.stop()

st.markdown("""
<div style="text-align:center;padding:1rem 0 0.3rem">
    <span style="font-size:2.6rem">🌿</span>
</div>
<div class="pnev-titolo">Studio The Organism</div>
<div class="pnev-sub">
    Dott. Giuseppe Ferraioli · Psicologo Optometrista Comportamentale<br>
    <strong>Questionario Psico-Neuro-Evolutivo (PNEV)</strong>
</div>
""", unsafe_allow_html=True)

qp     = st.query_params
q_type = (qp.get("q", "") or "").upper().strip()
token  = (qp.get("t", "") or "").strip()

if not q_type or not token:
    st.warning(
        "Pagina riservata ai pazienti dello Studio The Organism.\n\n"
        "Se hai ricevuto un link dallo studio, assicurati di aprirlo per intero."
    )
    st.caption("📞 0815152334 · dr.ferraioligiuseppe@gmail.com · www.theorganism.it")
    st.stop()

if q_type not in REGISTRY:
    st.error(f"Tipo questionario '{q_type}' non riconosciuto.")
    st.stop()

rec = validate_public_token(token, q_type)
if rec is None:
    st.error(
        "⛔ Link non valido, già utilizzato o scaduto.\n\n"
        "Contatta lo studio per ricevere un nuovo link:\n"
        "📞 0815152334 · dr.ferraioligiuseppe@gmail.com"
    )
    st.stop()

paziente_id   = int(rec["paziente_id"])
nome_paziente = rec.get("nome_paziente", "")
token_id      = int(rec["id"])

if "pq_completato" not in st.session_state:
    st.session_state.pq_completato = False

if st.session_state.pq_completato:
    st.markdown("""
    <div class="completato-box">
        <div style="font-size:3rem;margin-bottom:0.5rem">✅</div>
        <h2 style="color:#1D6B44 !important;-webkit-text-fill-color:#1D6B44 !important">
            Questionario inviato!
        </h2>
        <p>Le risposte sono state ricevute dallo studio.<br>
        La contatteremo a breve per confermare l'appuntamento.</p>
        <hr style="margin:1.2rem 0;border-color:#bbf7d0">
        <p style="font-size:0.8rem;color:#64748b">
            Studio The Organism · Via De Rosa, 46 – Pagani (SA)<br>
            📞 0815152334 · dr.ferraioligiuseppe@gmail.com · www.theorganism.it
        </p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

reg_info = REGISTRY[q_type]
st.markdown(f"### {reg_info['label']}")
if nome_paziente:
    st.caption(f"Paziente: **{nome_paziente}**")
st.caption("Compila e premi **INVIA**. Le risposte verranno registrate nel gestionale.")

if q_type in ("INPPS", "INPPS_ADULTI"):
    try:
        from app_core import inpps_collect_ui
    except ImportError:
        try:
            from modules.app_core import inpps_collect_ui
        except ImportError:
            st.error("Impossibile caricare il questionario. Contattare lo studio: 📞 0815152334")
            st.stop()

    with st.form("public_form"):
        inpps_data, inpps_summary = inpps_collect_ui(
            prefix=f"pub_{q_type.lower()}",
            existing=None,
        )
        submitted = st.form_submit_button(
            "✅ INVIA QUESTIONARIO",
            type="primary",
            use_container_width=True,
        )

    if submitted:
        try:
            save_inpps_response(paziente_id, inpps_data, inpps_summary)
            mark_token_used(token_id)
            st.session_state.pq_completato = True
            st.rerun()
        except Exception as e:
            st.error(f"Errore salvataggio: {e}\n\nRiprova o contatta lo studio: 📞 0815152334")
else:
    st.info(f"Il questionario **{reg_info['label']}** è in fase di attivazione.")
