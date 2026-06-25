# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════╗
║  ASSISTENTE PNEV — co-pilota clinico trasversale (Mattone A)         ║
║                                                                      ║
║  Legge TUTTO lo storico del paziente (ogni specialità: oculistica,   ║
║  optometria, logopedia, osteopatia, neuropsicologia…) e, su          ║
║  richiesta, propone:                                                 ║
║    • 🔑 una CHIAVE DI LETTURA del quadro                             ║
║    • 🎯 una PROPOSTA TERAPEUTICA in ottica PNEV                       ║
║    • 🔁 un eventuale INVIO ad altro specialista                      ║
║                                                                      ║
║  Tiene conto anche degli ESITI già registrati (cosa ha funzionato o  ║
║  no): è il primo passo dell'"imparare dagli errori".                 ║
║                                                                      ║
║  Riutilizzabile: from .assistente_pnev import render_assistente      ║
║                  render_assistente(conn, paz_id, paziente, contesto) ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import streamlit as st

try:
    from .diagnosi_assistita import _riassunto_storico, _identificativi
except Exception:
    def _riassunto_storico(conn, paz_id):
        return ""
    def _identificativi(p):
        return ""

_SISTEMA = (
    "Sei il co-pilota clinico dello Studio The Organism e ragioni secondo il "
    "Metodo PNEV (Psico-Neuro-Evolutivo Integrato) del Dott. Giuseppe Ferraioli. "
    "Leggi il quadro del paziente in modo TRASVERSALE e integrato fra tutte le "
    "specialità (oculistica, optometria comportamentale, logopedia, terapia "
    "miofunzionale, osteopatia, psicomotricità, neuropsicologia, posturologia). "
    "Scrivi in italiano, registro clinico, conciso e operativo. NON inventare "
    "dati: usa SOLO ciò che è nello storico. Dove manca un elemento, dillo e "
    "indica cosa servirebbe per chiarirlo. Tieni conto degli ESITI già "
    "registrati: se un intervento non ha migliorato, proponi un'alternativa e "
    "spiega perché. Ricorda sempre che la decisione finale è del clinico."
)

_RICHIESTA = (
    "Analizza il quadro del paziente e rispondi ESATTAMENTE in tre sezioni:\n\n"
    "🔑 CHIAVE DI LETTURA\n"
    "(interpretazione integrata e trasversale del quadro: cosa lega i dati delle "
    "diverse aree; ipotesi funzionale PNEV)\n\n"
    "🎯 PROPOSTA TERAPEUTICA PNEV\n"
    "(indicazioni operative concrete; se esistono esiti precedenti, parti da "
    "quelli e correggi il tiro)\n\n"
    "🔁 INVIO / CONFRONTO SPECIALISTICO\n"
    "(se utile, a quale figura inviare e con quale quesito; altrimenti scrivi "
    "«non necessario al momento»)\n\n"
)


def render_assistente(conn=None, paz_id=None, paziente=None, contesto: str = "",
                      titolo: str = "💡 Assistente PNEV", compatto: bool = False):
    """Riquadro del co-pilota. `contesto` = testo della cosa appena inserita
    (es. esito di un test), che viene messo in cima all'analisi."""
    if not compatto:
        st.subheader(titolo)
        st.caption("Lettura trasversale di tutto lo storico del paziente, con "
                   "proposta terapeutica e di invio. L'AI propone, tu decidi.")

    if conn is None or not paz_id:
        st.info("Seleziona prima un paziente.")
        return

    try:
        from .ai_estrazione import genera_testo, ai_disponibile
    except Exception:
        st.warning("Motore AI non disponibile.")
        return

    if not ai_disponibile():
        st.caption("AI non configurata: aggiungi la chiave nei Secrets per usare "
                   "l'assistente.")
        return

    storico = _riassunto_storico(conn, paz_id)
    if not storico and not contesto:
        st.info("Nessuno storico ancora presente per questo paziente.")
        return

    key_out = f"assist_out_{paz_id}"
    etichetta = "💡 Chiedi all'assistente" if not contesto else "💡 Leggi questo dato"
    if st.button(etichetta, type="primary", key=f"assist_btn_{paz_id}"):
        ident = _identificativi(paziente)
        blocco = ""
        if contesto:
            blocco += "=== DATO APPENA INSERITO (da considerare per primo) ===\n" \
                      + contesto.strip() + "\n\n"
        blocco += "=== DATI IDENTIFICATIVI ===\n" + ident + "\n\n"
        blocco += "=== STORICO COMPLETO DEL PAZIENTE ===\n" + (storico or "non disponibile")
        with st.spinner("L'assistente sta leggendo il quadro…"):
            st.session_state[key_out] = genera_testo(_RICHIESTA + blocco,
                                                     sistema=_SISTEMA)

    out = st.session_state.get(key_out)
    if out:
        st.markdown(out)
        st.download_button("⬇️ Scarica analisi (.txt)", data=out,
                           file_name="assistente_pnev.txt", mime="text/plain",
                           key=f"assist_dl_{paz_id}")
        st.caption("⚠️ Proposta generata dall'AI: va sempre validata dal clinico.")
