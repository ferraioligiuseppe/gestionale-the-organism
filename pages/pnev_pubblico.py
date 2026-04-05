# -*- coding: utf-8 -*-
# pages/pnev_pubblico.py
#
# Pagina pubblica Questionario Psico-Neuro-EVolutivo (PNEV)
# URL: https://<tuaapp>.streamlit.app/pnev_pubblico
# Nessun login richiesto — accessibile con codice OTP ricevuto dallo studio
#
# Struttura repo:
#   modules/domande.py   ← domande questionario (già presente)
#   modules/db_pnev.py   ← OTP + salvataggio risposte (già presente)

import streamlit as st
import json
import sys
import os

# Assicura che la root del progetto sia nel path
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# Import dai moduli esistenti nel repo
# (domande.py e db_pnev.py stanno in modules/ — NON in modules/pnev/)
from modules.domande import QUESTIONARIO_BAMBINI, QUESTIONARIO_ADULTI
from modules.db_pnev import init_pnev_tables, verifica_token, salva_risposte

# ── CONFIG PAGINA ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="The Organism — Questionario PNEV",
    page_icon="🌿",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── CSS MOBILE-FIRST ──────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Nasconde sidebar e nav Streamlit */
[data-testid="stSidebar"]       { display: none !important; }
[data-testid="collapsedControl"]{ display: none !important; }
#MainMenu { visibility: hidden; }
footer    { visibility: hidden; }
header    { visibility: hidden; }

/* Layout mobile */
* { -webkit-text-fill-color: #1e293b !important; }
.block-container {
    max-width: 620px !important;
    padding: 0.8rem 1rem 4rem 1rem !important;
}

/* Header studio */
.pnev-logo       { text-align:center; padding:1.2rem 0 0.2rem 0; }
.pnev-titolo     {
    text-align:center; font-size:1.35rem; font-weight:800;
    color:#1D6B44 !important; -webkit-text-fill-color:#1D6B44 !important;
    margin-bottom:0.15rem;
}
.pnev-sottotitolo{
    text-align:center; font-size:0.85rem;
    color:#64748b !important; -webkit-text-fill-color:#64748b !important;
    margin-bottom:1.2rem;
}

/* Sezioni questionario */
.sezione-header {
    background:#1D6B44; color:white !important;
    -webkit-text-fill-color:white !important;
    border-radius:8px; padding:10px 16px;
    font-size:1rem; font-weight:700; margin:1.4rem 0 0.7rem 0;
}
.sezione-desc {
    color:#475569 !important; -webkit-text-fill-color:#475569 !important;
    font-size:0.84rem; margin-bottom:0.9rem; font-style:italic;
}
.progress-label {
    font-size:0.78rem; color:#64748b !important;
    -webkit-text-fill-color:#64748b !important;
    text-align:right; margin-bottom:0.2rem;
}

/* Box token e completato */
.token-box {
    background:#f8fafc; border:1px solid #e2e8f0;
    border-radius:10px; padding:1.1rem 1.4rem; margin:0.8rem 0;
}
.completato-box {
    background:#f0fdf4; border:2px solid #1D6B44;
    border-radius:12px; padding:2rem; text-align:center; margin-top:1.5rem;
}
</style>
""", unsafe_allow_html=True)

# ── INIT DB ───────────────────────────────────────────────────────────────────
try:
    init_pnev_tables()
except Exception as e:
    st.error(f"Errore inizializzazione DB: {e}")
    st.stop()

# ── HEADER STUDIO ─────────────────────────────────────────────────────────────
st.markdown("""
<div class="pnev-logo"><span style="font-size:2.6rem;">🌿</span></div>
<div class="pnev-titolo">Studio The Organism</div>
<div class="pnev-sottotitolo">
    Dott. Giuseppe Ferraioli · Psicologo Optometrista Comportamentale<br>
    <strong>Questionario Psico-Neuro-EVolutivo (PNEV)</strong>
</div>
""", unsafe_allow_html=True)

# ── SESSION STATE ─────────────────────────────────────────────────────────────
_DEFAULTS = {
    "pnev_fase": "login",          # login | info | compila | completato
    "pnev_token_rec": None,
    "pnev_questionario": None,
    "pnev_sezione_idx": 0,
    "pnev_risposte": {},
    "pnev_nome_compilatore": "",
    "pnev_relazione": "",
    "pnev_note_extra": "",
}
for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ── FASE: LOGIN ───────────────────────────────────────────────────────────────
if st.session_state.pnev_fase == "login":

    st.markdown("### Inserisci il codice ricevuto dallo studio")
    st.markdown(
        "Hai ricevuto un **codice di 8 caratteri** (es. `ABC12345`). "
        "Inseriscilo qui sotto per accedere al questionario."
    )

    # Supporto link diretto con ?token=XXXXXXXX
    token_da_url = st.query_params.get("token", "").upper().strip()

    with st.form("login_form"):
        token_input = st.text_input(
            "Codice di accesso",
            value=token_da_url,
            max_chars=8,
            placeholder="Es. ABC12345",
        ).upper().strip()
        accedi = st.form_submit_button(
            "Accedi →", type="primary", use_container_width=True
        )

    if accedi:
        if not token_input:
            st.error("Inserisci il codice di accesso.")
        else:
            try:
                rec = verifica_token(token_input)
            except Exception as e:
                st.error(f"Errore verifica codice: {e}")
                rec = None

            if rec is None:
                st.error(
                    "⛔ Codice non valido, già utilizzato o scaduto.\n\n"
                    "Contatta lo studio per ricevere un nuovo codice:\n"
                    "📞 0815152334  |  ✉️ dr.ferraioligiuseppe@gmail.com"
                )
            else:
                versione = rec.get("versione", "bambini")
                st.session_state.pnev_token_rec = rec
                st.session_state.pnev_questionario = (
                    QUESTIONARIO_BAMBINI if versione == "bambini"
                    else QUESTIONARIO_ADULTI
                )
                st.session_state.pnev_fase = "info"
                st.rerun()

    st.divider()
    st.caption(
        "📞 Studio The Organism · Via De Rosa, 46 – Pagani (SA) · "
        "Tel. 0815152334 · dr.ferraioligiuseppe@gmail.com"
    )

# ── FASE: INFO COMPILATORE ────────────────────────────────────────────────────
elif st.session_state.pnev_fase == "info":
    rec = st.session_state.pnev_token_rec
    q   = st.session_state.pnev_questionario
    nome_paz = rec.get("nome_paziente", "")
    versione = rec.get("versione", "bambini")

    st.markdown("### Benvenuto/a!")
    n_sez = len(q["sezioni"])
    n_dom = sum(len(s["domande"]) for s in q["sezioni"])

    st.markdown(
        f'<div class="token-box">'
        f'<strong>Questionario per:</strong> {nome_paz}<br>'
        f'<strong>Tipo:</strong> {q["titolo"]}<br>'
        f'<strong>{n_sez} sezioni</strong> · circa {n_dom} domande · ~10–15 minuti'
        f'</div>',
        unsafe_allow_html=True,
    )

    with st.form("info_form"):
        nome_comp = st.text_input(
            "Il tuo nome e cognome *",
            placeholder="Chi sta compilando questo questionario?",
        )
        if versione == "bambini":
            relazione = st.selectbox(
                "Relazione con il bambino *",
                ["Madre", "Padre", "Entrambi i genitori", "Nonno/a", "Tutore legale", "Altro"],
            )
        else:
            relazione = "Autocompilato"
            st.info("Il questionario viene compilato direttamente dall'adulto interessato.")

        inizia = st.form_submit_button(
            "Inizia il questionario →", type="primary", use_container_width=True
        )

    if inizia:
        if not nome_comp.strip():
            st.error("Inserisci il tuo nome per continuare.")
        else:
            st.session_state.pnev_nome_compilatore = nome_comp.strip()
            st.session_state.pnev_relazione = relazione
            st.session_state.pnev_sezione_idx = 0
            st.session_state.pnev_fase = "compila"
            st.rerun()

# ── FASE: COMPILAZIONE ────────────────────────────────────────────────────────
elif st.session_state.pnev_fase == "compila":
    q        = st.session_state.pnev_questionario
    sezioni  = q["sezioni"]
    n_sezioni = len(sezioni)
    idx      = st.session_state.pnev_sezione_idx
    rec      = st.session_state.pnev_token_rec
    sezione  = sezioni[idx]
    e_ultima = (idx == n_sezioni - 1)

    # Barra progresso
    st.markdown(
        f'<div class="progress-label">'
        f'Sezione {idx+1} di {n_sezioni} — {sezione["titolo"]}'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.progress((idx + 1) / n_sezioni)

    st.markdown(
        f'<div class="sezione-header">{sezione["titolo"]}</div>',
        unsafe_allow_html=True,
    )
    if sezione.get("descrizione"):
        st.markdown(
            f'<div class="sezione-desc">{sezione["descrizione"]}</div>',
            unsafe_allow_html=True,
        )

    risposte_sezione = {}

    with st.form(f"sezione_{idx}"):
        for dom in sezione["domande"]:
            did   = dom["id"]
            testo = dom["testo"]
            tipo  = dom.get("tipo", "si_no")
            prev  = st.session_state.pnev_risposte.get(did, {})

            st.markdown(f"**{testo}**")

            if tipo == "si_no":
                risp = st.radio(
                    did, ["No", "Sì"],
                    index=1 if prev.get("risp") == "Sì" else 0,
                    horizontal=True, label_visibility="collapsed",
                    key=f"r_{did}_{idx}",
                )
                risposte_sezione[did] = {"risp": risp}

            elif tipo == "si_no_testo":
                risp = st.radio(
                    did, ["No", "Sì"],
                    index=1 if prev.get("risp") == "Sì" else 0,
                    horizontal=True, label_visibility="collapsed",
                    key=f"r_{did}_{idx}",
                )
                det = ""
                if risp == "Sì":
                    det = st.text_area(
                        "Specificare (opzionale):",
                        value=prev.get("dettaglio", ""),
                        height=65, key=f"d_{did}_{idx}",
                        placeholder=dom.get("placeholder", ""),
                    )
                risposte_sezione[did] = {"risp": risp, "dettaglio": det}

            elif tipo == "frequenza":
                opzioni  = dom.get("opzioni", ["Mai", "Talvolta", "Spesso"])
                prev_val = prev.get("risp", opzioni[0])
                idx_prev = opzioni.index(prev_val) if prev_val in opzioni else 0
                risp = st.radio(
                    did, opzioni, index=idx_prev,
                    horizontal=True, label_visibility="collapsed",
                    key=f"r_{did}_{idx}",
                )
                risposte_sezione[did] = {"risp": risp}

            st.markdown("---")

        # Note finali solo sull'ultima sezione
        note_extra = ""
        if e_ultima and q.get("note_finali"):
            note_extra = st.text_area(
                "📝 Vuoi aggiungere qualcosa? "
                "(informazioni aggiuntive, terapie precedenti, lingua madre...)",
                height=100, key="note_extra_field",
            )

        col1, col2 = st.columns(2)
        with col1:
            back  = st.form_submit_button(
                "← Indietro", use_container_width=True, disabled=(idx == 0)
            )
        with col2:
            avanti = st.form_submit_button(
                "✅ Invia" if e_ultima else "Avanti →",
                type="primary", use_container_width=True,
            )

    # ── Navigazione ───────────────────────────────────────────────────────────
    if back and idx > 0:
        st.session_state.pnev_risposte.update(risposte_sezione)
        st.session_state.pnev_sezione_idx -= 1
        st.rerun()

    if avanti:
        st.session_state.pnev_risposte.update(risposte_sezione)

        # Salvataggio (intermedio o finale)
        try:
            ok = salva_risposte(
                token=rec["token"],
                dati_json=st.session_state.pnev_risposte,
                nome_compilatore=st.session_state.pnev_nome_compilatore,
                relazione=st.session_state.pnev_relazione,
                note_finali=note_extra if e_ultima else "",
                completato=e_ultima,
            )
        except Exception as e:
            st.error(f"Errore salvataggio: {e}")
            ok = False

        if not ok:
            st.error(
                "Errore nel salvataggio. Riprova oppure contatta lo studio:\n"
                "📞 0815152334"
            )
        elif e_ultima:
            st.session_state.pnev_fase = "completato"
            st.rerun()
        else:
            st.session_state.pnev_sezione_idx += 1
            st.rerun()

# ── FASE: COMPLETATO ──────────────────────────────────────────────────────────
elif st.session_state.pnev_fase == "completato":
    st.markdown("""
    <div class="completato-box">
        <div style="font-size:3.5rem; margin-bottom:0.5rem;">✅</div>
        <h2 style="color:#1D6B44 !important; -webkit-text-fill-color:#1D6B44 !important;">
            Questionario inviato!
        </h2>
        <p style="font-size:1rem;">
            Grazie per aver compilato il questionario PNEV.<br>
            Le risposte sono state ricevute dallo studio.
        </p>
        <p style="font-size:0.95rem; font-weight:600; margin-top:0.8rem;">
            Lo studio la contatterà a breve per fissare o confermare l'appuntamento.
        </p>
        <hr style="margin:1.4rem 0; border-color:#bbf7d0;">
        <p style="font-size:0.8rem; color:#64748b;">
            Studio The Organism · Via De Rosa, 46 – Pagani (SA)<br>
            📞 0815152334 &nbsp;|&nbsp; ✉️ dr.ferraioligiuseppe@gmail.com<br>
            🌐 www.theorganism.it
        </p>
    </div>
    """, unsafe_allow_html=True)
