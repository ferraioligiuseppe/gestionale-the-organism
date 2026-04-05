# modules/pnev/ui_pnev.py
import streamlit as st
import json
from datetime import datetime
from modules.pnev.domande import QUESTIONARIO_BAMBINI, QUESTIONARIO_ADULTI
from modules.pnev.db_pnev import (
    init_pnev_tables, genera_token, get_token_paziente,
    get_risposte_paziente, get_ultima_risposta,
)

_CSS = """
<style>
* { -webkit-text-fill-color: #1e293b !important; }
.pnev-token-box {
    background: #f0fdf4;
    border: 2px solid #1D6B44;
    border-radius: 12px;
    padding: 1.2rem 1.5rem;
    margin: 1rem 0;
    text-align: center;
}
.pnev-token-code {
    font-size: 2.2rem;
    font-weight: 800;
    letter-spacing: 6px;
    color: #1D6B44 !important;
    -webkit-text-fill-color: #1D6B44 !important;
    font-family: monospace;
}
.pnev-link {
    font-size: 0.85rem;
    color: #475569 !important;
    -webkit-text-fill-color: #475569 !important;
    word-break: break-all;
    margin-top: 0.5rem;
}
.risposta-si {
    color: #dc2626 !important;
    -webkit-text-fill-color: #dc2626 !important;
    font-weight: 600;
}
.risposta-no {
    color: #16a34a !important;
    -webkit-text-fill-color: #16a34a !important;
}
.sezione-header-small {
    background: #e2e8f0;
    border-radius: 6px;
    padding: 6px 12px;
    font-weight: 600;
    font-size: 0.9rem;
    margin: 1rem 0 0.5rem 0;
}
</style>
"""

# URL dell'app pubblica (da configurare in produzione)
PNEV_PUBLIC_URL = "http://localhost:8502"  # modificare con URL Streamlit Cloud


def _conta_si(dati: dict) -> int:
    return sum(1 for v in dati.values() if isinstance(v, dict) and v.get("risp") == "Sì")


def _conta_domande(versione: str) -> int:
    q = QUESTIONARIO_BAMBINI if versione == "bambini" else QUESTIONARIO_ADULTI
    return sum(len(s["domande"]) for s in q["sezioni"])


def render_pnev(paziente_id, nome_paziente):
    st.markdown(_CSS, unsafe_allow_html=True)
    init_pnev_tables()

    st.markdown(f"### 📋 Questionario PNEV — {nome_paziente}")

    tab_genera, tab_risposte = st.tabs(["🔑 Genera Link", "📊 Risposte"])

    # ── TAB GENERA LINK ───────────────────────────────────────────────────────
    with tab_genera:
        st.markdown("**Invia il questionario al paziente/genitore**")
        st.markdown(
            "Genera un codice OTP monouso. Il paziente lo inserisce sull'app pubblica "
            "e compila il questionario dal proprio smartphone."
        )

        col1, col2 = st.columns(2)
        with col1:
            versione = st.selectbox(
                "Versione questionario",
                options=["bambini", "adulti"],
                format_func=lambda x: "👶 Bambini (compila il genitore)" if x == "bambini" else "🧑 Adulti (autocompilato)",
                key="pnev_versione",
            )
        with col2:
            ore = st.selectbox(
                "Validità codice",
                options=[24, 48, 72, 168],
                format_func=lambda x: f"{x} ore ({x//24} giorni)" if x >= 24 else f"{x} ore",
                index=2,
                key="pnev_ore",
            )

        # Token attivo esistente
        token_attivo = get_token_paziente(paziente_id, versione)
        if token_attivo:
            scadenza = token_attivo.get("scadenza", "")
            st.info(
                f"⚠️ Esiste già un token attivo per questa versione "
                f"(scade il {scadenza}). Generandone uno nuovo, quello vecchio verrà invalidato."
            )

        if st.button("🔑 Genera nuovo codice OTP", type="primary", key="pnev_genera"):
            token = genera_token(paziente_id, nome_paziente, versione, ore)
            link = f"{PNEV_PUBLIC_URL}?token={token}"
            st.markdown(
                f'<div class="pnev-token-box">'
                f'<div style="font-size:0.85rem;margin-bottom:0.5rem;">Codice OTP per <strong>{nome_paziente}</strong></div>'
                f'<div class="pnev-token-code">{token}</div>'
                f'<div class="pnev-link">Link diretto: {link}</div>'
                f'</div>',
                unsafe_allow_html=True
            )
            st.success(
                f"✅ Codice generato! Valido per {ore} ore. "
                f"Invia il codice **{token}** al paziente via WhatsApp, SMS o email."
            )

            # Testo pronto per WhatsApp
            q = QUESTIONARIO_BAMBINI if versione == "bambini" else QUESTIONARIO_ADULTI
            n_sezioni = len(q["sezioni"])
            st.markdown("**Messaggio pronto da inviare:**")
            msg = (
                f"Gentile {nome_paziente},\n\n"
                f"La invitiamo a compilare il questionario di screening dello Studio The Organism.\n\n"
                f"🔗 Collegati a: {PNEV_PUBLIC_URL}\n"
                f"🔑 Codice di accesso: **{token}**\n\n"
                f"Il questionario ({n_sezioni} sezioni, circa 10-15 min) è valido per {ore} ore.\n\n"
                f"Cordiali saluti,\nStudio The Organism\nDott. Giuseppe Ferraioli"
            )
            st.code(msg, language=None)

        st.divider()
        st.markdown("**Come funziona:**")
        st.markdown(
            "1. Clicca *Genera nuovo codice OTP* → ottieni codice 8 caratteri + link\n"
            "2. Invia il codice al paziente via WhatsApp/SMS/email\n"
            "3. Il paziente va su **" + PNEV_PUBLIC_URL + "** e inserisce il codice\n"
            "4. Compila il questionario dal proprio smartphone\n"
            "5. Le risposte appaiono automaticamente nella scheda **Risposte**"
        )

    # ── TAB RISPOSTE ──────────────────────────────────────────────────────────
    with tab_risposte:
        risposte_list = get_risposte_paziente(paziente_id)

        if not risposte_list:
            st.info("Nessun questionario compilato ancora. Genera un link dalla scheda 'Genera Link'.")
            return

        # Seleziona quale risposta visualizzare
        opzioni = []
        for r in risposte_list:
            stato = "✅ Completato" if r["completato"] else "⏳ In corso"
            label = f"{r['created_at'][:10]} — {r['versione'].capitalize()} — {stato}"
            opzioni.append((label, r))

        label_sel, risposta_sel = st.selectbox(
            "Seleziona questionario",
            options=opzioni,
            format_func=lambda x: x[0],
            key="pnev_sel_risposta",
        )

        r = risposta_sel
        dati = json.loads(r.get("dati_json", "{}"))
        versione = r["versione"]
        q = QUESTIONARIO_BAMBINI if versione == "bambini" else QUESTIONARIO_ADULTI
        n_tot = _conta_domande(versione)
        n_si = _conta_si(dati)

        # Riepilogo
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Compilatore", r.get("nome_compilatore", "—"))
        col2.metric("Relazione", r.get("relazione", "—"))
        col3.metric("Sì totali", f"{n_si}/{n_tot}")
        col4.metric("Stato", "✅ Completo" if r["completato"] else "⏳ Parziale")

        if r.get("note_finali"):
            st.info(f"📝 Note compilatore: {r['note_finali']}")

        st.divider()

        # Visualizzazione risposte per sezione
        st.markdown("**Dettaglio risposte:**")

        for sezione in q["sezioni"]:
            sid = sezione["id"]
            # Conta i Sì in questa sezione
            n_si_sez = sum(
                1 for dom in sezione["domande"]
                if dati.get(dom["id"], {}).get("risp") == "Sì"
            )
            n_tot_sez = len(sezione["domande"])

            with st.expander(
                f"{sezione['titolo']} — {n_si_sez}/{n_tot_sez} positivi",
                expanded=(n_si_sez > 0)
            ):
                for dom in sezione["domande"]:
                    did = dom["id"]
                    risp_dom = dati.get(did, {})
                    risp = risp_dom.get("risp", "—")
                    dettaglio = risp_dom.get("dettaglio", "")

                    if risp == "Sì":
                        badge = "🔴 **Sì**"
                    elif risp == "No":
                        badge = "🟢 No"
                    else:
                        badge = f"⚪ {risp}"

                    st.markdown(f"{badge} — {dom['testo']}")
                    if dettaglio:
                        st.caption(f"   ↳ {dettaglio}")

        # Sintesi flag principali
        st.divider()
        st.markdown("**🚩 Flag positivi (da approfondire):**")
        flag = []
        for sezione in q["sezioni"]:
            for dom in sezione["domande"]:
                did = dom["id"]
                if dati.get(did, {}).get("risp") == "Sì":
                    flag.append(f"• [{sezione['titolo']}] {dom['testo']}")

        if flag:
            for f_item in flag:
                st.markdown(f_item)
        else:
            st.success("Nessuna risposta positiva registrata.")
