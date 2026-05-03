# -*- coding: utf-8 -*-
# pages/firma_consenso_pubblico.py
#
# Pagina pubblica per firma di consenso costellazioni a distanza.
# URL: https://<app>.streamlit.app/firma_consenso_pubblico?t=<token>
# Nessun login richiesto. Token monouso con scadenza.

import streamlit as st
import sys, os
import hashlib
from datetime import datetime
from zoneinfo import ZoneInfo

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from modules.app_core import get_connection
from modules.consensi_costellazioni import services
from modules.consensi_costellazioni.pdf_generator import genera_pdf_consenso

ROME_TZ = ZoneInfo("Europe/Rome")


# =============================================================================
# CONFIG STREAMLIT
# =============================================================================

st.set_page_config(
    page_title="The Organism — Firma consenso",
    page_icon="🌿",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# CSS coerente con pages/pnev_pubblico.py
st.markdown("""
<style>
[data-testid="stSidebar"], [data-testid="collapsedControl"] { display:none !important; }
#MainMenu, footer, header { visibility:hidden; }
* { -webkit-text-fill-color: #1e293b !important; }
.block-container { max-width:680px !important; padding:0.8rem 1rem 4rem 1rem !important; }
.cf-titolo {
    text-align:center; font-size:1.4rem; font-weight:800;
    color:#1D6B44 !important; -webkit-text-fill-color:#1D6B44 !important;
    margin-bottom:0.2rem;
}
.cf-sub {
    text-align:center; font-size:0.9rem;
    color:#64748b !important; -webkit-text-fill-color:#64748b !important;
    margin-bottom:1.2rem;
}
.cf-versione {
    text-align:center; font-size:0.8rem;
    color:#94a3b8 !important; -webkit-text-fill-color:#94a3b8 !important;
    font-style:italic; margin-bottom:1.5rem;
}
.cf-info-box {
    background:#f0fdf4; border-left:4px solid #1D6B44;
    border-radius:8px; padding:1rem 1.2rem; margin:1rem 0;
    font-size:0.9rem;
}
.cf-success-box {
    background:#f0fdf4; border:2px solid #1D6B44;
    border-radius:12px; padding:2rem; text-align:center; margin-top:1.5rem;
}
.cf-error-box {
    background:#fef2f2; border:2px solid #dc2626;
    border-radius:12px; padding:1.5rem; text-align:center;
}
.cf-paziente {
    text-align:center; font-size:1rem; font-weight:600;
    color:#1f2937 !important; -webkit-text-fill-color:#1f2937 !important;
    margin-bottom:1rem;
}
</style>
""", unsafe_allow_html=True)


# =============================================================================
# RECUPERO TOKEN
# =============================================================================

# Streamlit query params
qparams = st.query_params
token = qparams.get("t", "")
if isinstance(token, list):
    token = token[0] if token else ""
token = (token or "").strip()


# =============================================================================
# RENDER ERROR
# =============================================================================

def render_error(titolo: str, messaggio: str):
    st.markdown('<div class="cf-titolo">The Organism</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="cf-error-box">'
        f'<h3 style="color:#dc2626; margin-top:0;">⚠️ {titolo}</h3>'
        f'<p>{messaggio}</p>'
        f'</div>',
        unsafe_allow_html=True
    )
    st.stop()


if not token:
    render_error(
        "Link non valido",
        "Il link non contiene un token. Contatta lo studio per ricevere un nuovo link."
    )


# =============================================================================
# VALIDAZIONE TOKEN
# =============================================================================

try:
    conn = get_connection()
except Exception as e:
    render_error("Servizio non disponibile", f"Impossibile connettersi al sistema: {e}")

token_data = services.valida_token_firma(conn, token)
if not token_data:
    render_error(
        "Link scaduto o non valido",
        "Questo link è già stato utilizzato, è scaduto, o non esiste. "
        "Se hai bisogno di un nuovo link, contatta lo studio."
    )


# Recupero anagrafica paziente per personalizzare la UI
def _recupera_paziente(conn, paziente_id: int) -> dict:
    """Best-effort: usa _detect_patient_table_and_cols se disponibile."""
    try:
        from modules.app_core import _detect_patient_table_and_cols
        tab, cols = _detect_patient_table_and_cols(conn)
        if tab and cols:
            ph = "%s" if services._is_postgres(conn) else "?"
            cur = conn.cursor()
            try:
                cur.execute(
                    f'SELECT "{cols["nome"]}", "{cols["cognome"]}" '
                    f'FROM {tab} WHERE "{cols["id"]}" = {ph}',
                    (paziente_id,)
                )
                row = cur.fetchone()
                if row:
                    return {"nome": row[0], "cognome": row[1]}
            finally:
                try: cur.close()
                except: pass
    except Exception:
        pass

    # Fallback: query semplice su Pazienti
    try:
        ph = "%s" if services._is_postgres(conn) else "?"
        cur = conn.cursor()
        try:
            cur.execute(
                f"SELECT nome, cognome FROM Pazienti WHERE id = {ph}",
                (paziente_id,)
            )
            row = cur.fetchone()
            if row:
                return {"nome": row[0], "cognome": row[1]}
        finally:
            try: cur.close()
            except: pass
    except Exception:
        pass

    return {"nome": "", "cognome": ""}


paziente_info = _recupera_paziente(conn, token_data["paziente_id"])
paziente_nome = f"{paziente_info.get('nome', '')} {paziente_info.get('cognome', '')}".strip() or "(paziente)"


# =============================================================================
# HEADER
# =============================================================================

st.markdown('<div class="cf-titolo">The Organism</div>', unsafe_allow_html=True)
st.markdown(
    f'<div class="cf-sub">{token_data["nome"]}</div>',
    unsafe_allow_html=True
)
st.markdown(
    f'<div class="cf-versione">Codice: {token_data["codice"]} — Versione: {token_data["versione"]}</div>',
    unsafe_allow_html=True
)
st.markdown(
    f'<div class="cf-paziente">📋 Paziente: <b>{paziente_nome}</b></div>',
    unsafe_allow_html=True
)


# =============================================================================
# CHECK SE GIÀ FIRMATO IN QUESTA SESSIONE
# =============================================================================

session_key = f"_firmato_{token}"
if st.session_state.get(session_key):
    st.markdown(
        '<div class="cf-success-box">'
        '<h2 style="color:#1D6B44; margin-top:0;">✅ Consenso firmato</h2>'
        '<p>Il consenso è stato registrato con successo.</p>'
        '<p>Puoi chiudere questa pagina.</p>'
        '</div>',
        unsafe_allow_html=True
    )
    if st.session_state.get(f"_pdf_{token}"):
        st.download_button(
            "📥 Scarica copia del consenso firmato (PDF)",
            data=st.session_state[f"_pdf_{token}"],
            file_name=f"consenso_firmato_{token_data['codice']}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    st.stop()


# =============================================================================
# RECUPERO TEMPLATE COMPLETO + RENDER FORM
# =============================================================================

template_completo = services.template_per_id(conn, token_data["template_id"])
if not template_completo:
    render_error(
        "Errore di sistema",
        "Il modello di consenso non è più disponibile. Contatta lo studio."
    )


st.markdown(
    '<div class="cf-info-box">'
    '<b>📜 Cosa stai per firmare?</b><br/>'
    'Leggi attentamente il testo dell\'informativa, poi spunta le voci che '
    'vuoi accettare e clicca "Conferma firma" in fondo alla pagina.'
    '</div>',
    unsafe_allow_html=True
)


# === Testo informativa (espandibile) ===
with st.expander("📖 Leggi l'informativa completa", expanded=False):
    st.markdown(template_completo.get("testo_md", ""))


st.divider()


# === Form di firma ===
voci_def = template_completo.get("voci") or []

st.markdown("**Le tue scelte:**")
st.caption(
    "Le voci con etichetta *(obbligatoria)* devono essere accettate "
    "perché la firma sia valida."
)

with st.form(key=f"form_firma_pubblica_{token}"):
    voci_paziente = {}
    for v in sorted(voci_def, key=lambda x: x.get("ordine", 0)):
        cv = v["codice"]
        label_obb = " *(obbligatoria)*" if v.get("obbligatorio") else ""
        label = f"**{cv}** — {v['testo']}{label_obb}"
        default_val = bool(v.get("obbligatorio"))
        voci_paziente[cv] = st.checkbox(
            label,
            value=default_val,
            key=f"voce_pub_{token}_{cv}",
        )

    st.markdown("---")
    st.markdown(
        "**Dichiarazione**\n\n"
        "Confermando, attesti di aver letto l'informativa e di aver espresso "
        "le tue scelte sopra indicate. La firma è elettronica e tracciata "
        "(timestamp, IP). Riceverai una copia PDF del consenso firmato."
    )

    accetto = st.checkbox(
        "✔ Confermo le mie scelte e desidero firmare elettronicamente",
        key=f"accetto_{token}",
    )

    submit = st.form_submit_button(
        "🖋️ Conferma firma",
        type="primary",
        use_container_width=True,
        disabled=False,
    )


if submit:
    if not accetto:
        st.error("⚠️ Devi confermare la dichiarazione prima di firmare.")
        st.stop()

    # Tracciamento minimo (non possiamo recuperare IP reale facilmente da Streamlit)
    ip_addr = "remoto"
    user_agent = "browser_mobile"

    try:
        ris = services.firma_consenso(
            conn=conn,
            paziente_id=token_data["paziente_id"],
            codice_template=token_data["codice"],
            voci=voci_paziente,
            modalita_firma="link_paziente",
            ip_address=ip_addr,
            user_agent=user_agent,
            token_id=token_data["id"],
        )
    except services.VoceValidationError as e:
        st.error(f"⚠️ Voci obbligatorie non accettate: {e}")
        st.stop()
    except Exception as e:
        st.error(f"Errore durante la firma: {e}")
        st.stop()

    # Genera PDF
    try:
        pdf_temp = genera_pdf_consenso(
            template=template_completo,
            modalita_firma="link_paziente",
            paziente_nome=paziente_nome,
            paziente_id=token_data["paziente_id"],
            voci_paziente=ris["voci_normalizzate"],
            data_accettazione=ris["data_accettazione"],
            pdf_hash=None,
            ip_address=ip_addr,
            user_agent=user_agent,
        )
        pdf_hash = hashlib.sha256(pdf_temp).hexdigest()
        pdf_final = genera_pdf_consenso(
            template=template_completo,
            modalita_firma="link_paziente",
            paziente_nome=paziente_nome,
            paziente_id=token_data["paziente_id"],
            voci_paziente=ris["voci_normalizzate"],
            data_accettazione=ris["data_accettazione"],
            pdf_hash=pdf_hash,
            ip_address=ip_addr,
            user_agent=user_agent,
        )

        # Salva PDF nel record
        ph = "%s" if services._is_postgres(conn) else "?"
        cur = conn.cursor()
        try:
            cur.execute(
                f"""
                UPDATE cf_firme SET
                    pdf_blob = {ph}, pdf_filename = {ph}, pdf_hash = {ph}
                WHERE id = {ph}
                """,
                (
                    pdf_final,
                    f"consenso_{token_data['codice']}_{ris['firma_id']}.pdf",
                    pdf_hash,
                    ris["firma_id"]
                )
            )
            conn.commit()
        finally:
            try: cur.close()
            except: pass

        st.session_state[f"_pdf_{token}"] = pdf_final
    except Exception as e:
        # Firma comunque salvata; il PDF è secondario
        st.warning(f"PDF non generato (firma comunque salvata): {e}")

    st.session_state[session_key] = True
    st.rerun()
