# -*- coding: utf-8 -*-
"""
modules/consensi_costellazioni/ui/pannello_paziente.py

Pannello consensi costellazioni nella scheda paziente.
Visualizza lo stato dei 4 consensi del paziente con badge di stato e
bottoni di azione (firma, rinnova, revoca, scarica PDF).

API pubblica:
    render_pannello_consensi(paziente_id: int, paziente_nome: str)

Da chiamare nella scheda paziente del gestionale, ad esempio in un
st.tabs(["Anagrafica", "Anamnesi", ..., "Consensi"]) accanto alle altre tab.
"""

from __future__ import annotations

import logging
from typing import Optional

import streamlit as st

from .. import services
from ..pdf_generator import genera_pdf_consenso, genera_pdf_revoca

logger = logging.getLogger(__name__)


# I 4 codici nei nostri template, in ordine di visualizzazione
ORDINE_CODICI = [
    "costellazioni_individuali",
    "costellazioni_gruppo",
    "costellazioni_rappresentante",
    "costellazioni_registrazione",
]

LABEL_CODICI = {
    "costellazioni_individuali":   "Costellazioni 1:1 (individuali)",
    "costellazioni_gruppo":        "Costellazioni di gruppo",
    "costellazioni_rappresentante": "Ruolo di rappresentante",
    "costellazioni_registrazione": "Registrazione audio/video/foto",
}


# =============================================================================
# UTILS
# =============================================================================

def _get_conn():
    """Recupera la connessione DB tramite il pattern del gestionale."""
    from modules.app_core import get_connection
    return get_connection()


def _operatore_corrente() -> tuple[Optional[str], Optional[int]]:
    """
    Recupera username e id dell'operatore loggato dalla session_state.
    Pattern del gestionale: st.session_state["user"] = {"id", "username", ...}.
    """
    user = st.session_state.get("user") or {}
    return user.get("username"), user.get("id")


def _badge_stato(consenso: Optional[dict]) -> str:
    """Emoji + testo per la riga di stato di un consenso."""
    if not consenso:
        return "⚪ Mancante"
    stato = consenso["stato"]
    if stato == "attivo" and consenso.get("da_rinnovare"):
        return f"🟡 Da rinnovare (firmato v{consenso['template_versione']} → attivo v{consenso['versione_attiva']})"
    if stato == "attivo":
        return f"✅ Attivo (v{consenso['template_versione']})"
    if stato == "revocato":
        return f"🔴 Revocato"
    if stato == "superseduto":
        return f"⏭️ Sostituito da nuova versione"
    return f"⚠️ {stato}"


def _trova_attivo_per_codice(consensi: list[dict], codice: str) -> Optional[dict]:
    """Trova nella lista il consenso attivo per un certo codice (None se assente)."""
    for c in consensi:
        if c["template_codice"] == codice and c["stato"] == "attivo":
            return c
    return None


# =============================================================================
# RENDER PRINCIPALE
# =============================================================================

def render_pannello_consensi(paziente_id: int, paziente_nome: str = ""):
    """
    Renderizza il pannello consensi nella scheda paziente.

    Args:
        paziente_id: id del paziente (intero)
        paziente_nome: "Cognome Nome" per i PDF e le UI
    """
    conn = _get_conn()

    st.markdown("### 🤝 Consensi costellazioni familiari")
    st.caption(
        "Gestione dei consensi specifici per le costellazioni. "
        "Per i consensi privacy generali, vedi la sezione Privacy classica."
    )

    # Recupero stato dei 4 consensi
    consensi = services.consensi_attivi_paziente(
        conn, paziente_id, include_storico=False
    )

    # Tabella di stato
    cols = st.columns([3, 3, 2, 2])
    cols[0].markdown("**Tipologia**")
    cols[1].markdown("**Stato**")
    cols[2].markdown("**Modalità**")
    cols[3].markdown("**Azioni**")
    st.divider()

    for codice in ORDINE_CODICI:
        c = _trova_attivo_per_codice(consensi, codice)
        cols = st.columns([3, 3, 2, 2])

        cols[0].write(LABEL_CODICI[codice])
        cols[1].write(_badge_stato(c))
        cols[2].write(c["modalita_firma"] if c else "—")

        with cols[3]:
            if c:
                # Consenso attivo: pulsante per dettagli/azioni
                if st.button(
                    "Dettagli", key=f"det_{codice}_{paziente_id}",
                    use_container_width=True
                ):
                    st.session_state[f"_show_det_{codice}_{paziente_id}"] = True
            else:
                # Consenso mancante: pulsante per firmare
                if st.button(
                    "Firma", key=f"firm_{codice}_{paziente_id}",
                    type="primary", use_container_width=True
                ):
                    st.session_state[f"_show_firm_{codice}_{paziente_id}"] = True

    st.divider()

    # === SEZIONI ESPANDIBILI: dettagli e firma ===
    for codice in ORDINE_CODICI:
        # Dettagli consenso attivo
        if st.session_state.get(f"_show_det_{codice}_{paziente_id}"):
            _render_dettagli_consenso(conn, paziente_id, paziente_nome, codice)

        # Form di firma
        if st.session_state.get(f"_show_firm_{codice}_{paziente_id}"):
            _render_firma_consenso(conn, paziente_id, paziente_nome, codice)

    # === Storico consensi (revocati / superseduti) ===
    with st.expander("📜 Storico completo (incluso revocati/sostituiti)"):
        storico = services.consensi_attivi_paziente(
            conn, paziente_id, include_storico=True
        )
        if not storico:
            st.info("Nessun consenso registrato.")
        else:
            for c in storico:
                st.markdown(
                    f"- **{LABEL_CODICI.get(c['template_codice'], c['template_codice'])}** "
                    f"v{c['template_versione']} — "
                    f"firmato il {c['data_accettazione']} via *{c['modalita_firma']}* "
                    f"— stato: {_badge_stato(c)}"
                )


# =============================================================================
# SEZIONE: DETTAGLI CONSENSO
# =============================================================================

def _render_dettagli_consenso(conn, paziente_id: int, paziente_nome: str, codice: str):
    """Sezione dettagli + azioni (rinnova/revoca/scarica) per un consenso attivo."""
    consenso = services.firma_attiva_per_codice(conn, paziente_id, codice)
    if not consenso:
        st.warning(f"Consenso {codice} non più attivo.")
        st.session_state[f"_show_det_{codice}_{paziente_id}"] = False
        return

    with st.container(border=True):
        st.markdown(f"#### Dettagli: {LABEL_CODICI[codice]}")

        col1, col2 = st.columns(2)
        col1.markdown(f"**Versione firmata:** {consenso['template_versione']}")
        col1.markdown(f"**Modalità:** {consenso['modalita_firma']}")
        col2.markdown(f"**Firmato il:** {consenso['data_accettazione']}")
        col2.markdown(f"**ID firma:** {consenso['id']}")

        # Voci spuntate SÌ
        cur = conn.cursor()
        try:
            ph = "%s" if services._is_postgres(conn) else "?"
            cur.execute(
                f"SELECT codice_voce, valore FROM cf_voci WHERE firma_id = {ph} ORDER BY codice_voce",
                (consenso["id"],)
            )
            voci_rows = cur.fetchall()
        finally:
            try: cur.close()
            except: pass

        if voci_rows:
            st.markdown("**Voci accettate:**")
            for codice_voce, valore in voci_rows:
                icon = "✔" if (valore in (True, 1)) else "✗"
                st.markdown(f"- {icon} {codice_voce}")

        st.divider()

        # Azioni
        col_a, col_b, col_c, col_d = st.columns(4)

        # Scarica PDF
        with col_a:
            if st.button("📄 Scarica PDF", key=f"dl_{codice}_{paziente_id}",
                         use_container_width=True):
                _scarica_pdf_firma(conn, consenso["id"], codice, paziente_nome)

        # Rinnova
        with col_b:
            tpl_attivo = services.template_attivo_per_codice(conn, codice)
            puo_rinnovare = (
                tpl_attivo and tpl_attivo["versione"] != consenso["template_versione"]
            )
            if st.button("🔄 Rinnova", key=f"renew_{codice}_{paziente_id}",
                        disabled=not puo_rinnovare,
                        use_container_width=True,
                        help="Disponibile se esiste una versione più recente del template"):
                st.session_state[f"_show_firm_{codice}_{paziente_id}"] = True
                st.session_state[f"_renewing_{codice}_{paziente_id}"] = True
                st.rerun()

        # Revoca
        with col_c:
            if st.button("⛔ Revoca", key=f"rev_{codice}_{paziente_id}",
                         use_container_width=True):
                st.session_state[f"_show_rev_{codice}_{paziente_id}"] = True
                st.rerun()

        # Chiudi
        with col_d:
            if st.button("Chiudi", key=f"close_{codice}_{paziente_id}",
                         use_container_width=True):
                st.session_state[f"_show_det_{codice}_{paziente_id}"] = False
                st.rerun()

        # Form di revoca (in-place)
        if st.session_state.get(f"_show_rev_{codice}_{paziente_id}"):
            _render_form_revoca(conn, consenso, paziente_nome, codice)


def _render_form_revoca(conn, consenso, paziente_nome, codice):
    """Form per revoca del consenso."""
    paziente_id = consenso["paziente_id"]
    st.warning("⚠️ Revoca consenso (operazione tracciabile, non distruttiva)")

    with st.form(key=f"form_rev_{codice}_{paziente_id}"):
        modalita = st.selectbox(
            "Modalità di revoca",
            ["scritta", "verbale", "online", "altro"],
            help="Come è stata espressa la revoca dal paziente"
        )
        motivazione = st.text_area("Motivazione", max_chars=1000)

        col1, col2 = st.columns(2)
        confirm = col1.form_submit_button("✔ Conferma revoca", type="primary")
        cancel = col2.form_submit_button("Annulla")

    if cancel:
        st.session_state[f"_show_rev_{codice}_{paziente_id}"] = False
        st.rerun()

    if confirm:
        if not motivazione.strip():
            st.error("Inserisci una motivazione")
            return

        op_username, op_user_id = _operatore_corrente()
        try:
            services.revoca_consenso(
                conn=conn,
                firma_id=consenso["id"],
                motivazione=motivazione.strip(),
                modalita_revoca=modalita,
                operatore_username=op_username,
                operatore_user_id=op_user_id,
            )
            st.success("✅ Consenso revocato.")
            st.session_state[f"_show_rev_{codice}_{paziente_id}"] = False
            st.session_state[f"_show_det_{codice}_{paziente_id}"] = False
            st.rerun()
        except Exception as e:
            st.error(f"Errore: {e}")


# =============================================================================
# SEZIONE: FIRMA CONSENSO
# =============================================================================

def _render_firma_consenso(conn, paziente_id: int, paziente_nome: str, codice: str):
    """Form di firma di un nuovo consenso. Importa F5 (form_firma)."""
    from .form_firma import render_form_firma_click_studio
    from .form_cartaceo import render_form_firma_cartaceo

    is_renewing = st.session_state.get(f"_renewing_{codice}_{paziente_id}", False)

    with st.container(border=True):
        if is_renewing:
            st.markdown(f"#### 🔄 Rinnovo: {LABEL_CODICI[codice]}")
        else:
            st.markdown(f"#### ✍️ Firma: {LABEL_CODICI[codice]}")

        # Verifica prerequisiti
        tpl = services.template_attivo_per_codice(conn, codice)
        if not tpl:
            st.error(
                f"Template '{codice}' non trovato. "
                "Eseguire il seeding (sezione admin)."
            )
            if st.button("Chiudi", key=f"close_firm_{codice}_{paziente_id}"):
                st.session_state[f"_show_firm_{codice}_{paziente_id}"] = False
                st.session_state[f"_renewing_{codice}_{paziente_id}"] = False
                st.rerun()
            return

        # Check prerequisiti (es. costellazioni_gruppo richiede individuali)
        prereq = (tpl.get("requisiti") or {}).get("prerequisiti_codici", [])
        prereq_mancanti = []
        for p_codice in prereq:
            firma_p = services.firma_attiva_per_codice(conn, paziente_id, p_codice)
            if not firma_p:
                prereq_mancanti.append(p_codice)

        if prereq_mancanti:
            labels_mancanti = [LABEL_CODICI.get(c, c) for c in prereq_mancanti]
            st.error(
                f"⚠️ Per firmare questo consenso, il paziente deve prima firmare: "
                f"**{', '.join(labels_mancanti)}**"
            )
            if st.button("Chiudi", key=f"close_firm_{codice}_{paziente_id}"):
                st.session_state[f"_show_firm_{codice}_{paziente_id}"] = False
                st.session_state[f"_renewing_{codice}_{paziente_id}"] = False
                st.rerun()
            return

        # Selezione modalità
        st.markdown("**Modalità di firma**")
        modalita = st.radio(
            "modalita",
            options=["click_studio", "cartaceo", "link_paziente"],
            format_func=lambda m: {
                "click_studio": "📱 Click in studio (paziente firma sul tablet/PC)",
                "cartaceo": "📄 Cartaceo (stampa, firma a penna, ricarica)",
                "link_paziente": "🔗 Link al paziente (firma a distanza via email/sms)",
            }[m],
            key=f"mod_{codice}_{paziente_id}",
            label_visibility="collapsed",
        )

        st.divider()

        if modalita == "click_studio":
            render_form_firma_click_studio(
                conn, paziente_id, paziente_nome, codice, is_renewing=is_renewing
            )
        elif modalita == "cartaceo":
            render_form_firma_cartaceo(
                conn, paziente_id, paziente_nome, codice, is_renewing=is_renewing
            )
        else:
            _render_genera_link_paziente(conn, paziente_id, paziente_nome, codice)

        if st.button("✖ Chiudi senza firmare", key=f"close_firm_x_{codice}_{paziente_id}"):
            st.session_state[f"_show_firm_{codice}_{paziente_id}"] = False
            st.session_state[f"_renewing_{codice}_{paziente_id}"] = False
            st.rerun()


def _render_genera_link_paziente(conn, paziente_id: int, paziente_nome: str, codice: str):
    """Genera token per firma a distanza."""
    st.info(
        "Verrà generato un link monouso (scadenza 72 ore) che puoi inviare "
        "al paziente via email o SMS. Il paziente firmerà sul proprio dispositivo."
    )

    with st.form(key=f"form_link_{codice}_{paziente_id}"):
        durata_ore = st.slider(
            "Durata validità link (ore)",
            min_value=24, max_value=168, value=72, step=24
        )
        submit = st.form_submit_button("🔗 Genera link", type="primary")

    if submit:
        op_username, _ = _operatore_corrente()
        try:
            ris = services.crea_token_firma(
                conn=conn,
                paziente_id=paziente_id,
                codice_template=codice,
                durata_ore=durata_ore,
                operatore_username=op_username,
            )
            st.success("✅ Link generato:")
            base_url = st.session_state.get("_app_base_url", "https://testgestionale.streamlit.app")
            full_url = f"{base_url}{ris['url_path']}"
            st.code(full_url, language=None)
            st.caption(f"Scade il: {ris['scadenza']}")

            # Bottone copia (best effort, dipende da componente)
            st.text_input(
                "URL da copiare:",
                value=full_url,
                key=f"url_copy_{ris['token_id']}",
            )
        except Exception as e:
            st.error(f"Errore: {e}")


# =============================================================================
# UTILS: SCARICA PDF
# =============================================================================

def _scarica_pdf_firma(conn, firma_id: int, codice: str, paziente_nome: str):
    """Recupera PDF salvato (se presente) o lo rigenera al volo."""
    ph = "%s" if services._is_postgres(conn) else "?"
    cur = conn.cursor()
    try:
        cur.execute(
            f"""
            SELECT pdf_blob, pdf_filename, modalita_firma,
                   data_accettazione, firmato_da, ip_address, user_agent,
                   pdf_hash, paziente_id
            FROM cf_firme WHERE id = {ph}
            """,
            (firma_id,)
        )
        row = cur.fetchone()
        if not row:
            st.error("Firma non trovata")
            return

        pdf_blob = row[0]
        pdf_filename = row[1] or f"consenso_{codice}_{firma_id}.pdf"

        if pdf_blob:
            # PDF già salvato → download diretto
            st.download_button(
                "📥 Scarica PDF",
                data=bytes(pdf_blob),
                file_name=pdf_filename,
                mime="application/pdf",
                key=f"dl_btn_{firma_id}",
            )
        else:
            # PDF non salvato → rigenera
            tpl = services.template_attivo_per_codice(conn, codice)
            # Recupero voci
            cur2 = conn.cursor()
            try:
                cur2.execute(
                    f"SELECT codice_voce, valore FROM cf_voci WHERE firma_id = {ph}",
                    (firma_id,)
                )
                voci = {r[0]: bool(r[1]) for r in cur2.fetchall()}
            finally:
                try: cur2.close()
                except: pass

            pdf_bytes = genera_pdf_consenso(
                template=tpl,
                modalita_firma=row[2],
                paziente_nome=paziente_nome,
                paziente_id=row[8],
                voci_paziente=voci,
                operatore=row[4],
                data_accettazione=row[3],
                pdf_hash=row[7],
                ip_address=row[5],
                user_agent=row[6],
            )
            st.download_button(
                "📥 Scarica PDF",
                data=pdf_bytes,
                file_name=pdf_filename,
                mime="application/pdf",
                key=f"dl_btn_{firma_id}",
            )
    finally:
        try: cur.close()
        except: pass
