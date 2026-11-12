# -*- coding: utf-8 -*-
"""PNEV Metronomo — esercizi ritmici, integrazione bilaterale, timing.
Stesso file usato sul gestionale e su pnev.it (un solo strumento, due canali)."""
import os
import streamlit as st
import streamlit.components.v1 as components

_CANDIDATI = [
    os.path.join("static", "pnev_metronomo", "index.html"),
    os.path.join(os.path.dirname(__file__), "..", "static", "pnev_metronomo", "index.html"),
]
# Copia pubblica su pnev.it (per pazienti e lavoro a casa)
# La cartella su pnev.it usa il trattino BASSO (pnev_metronomo): con il
# trattino normale il link dava 404.
URL_PUBBLICO = "https://www.pnev.it/wp-content/uploads/pnev_metronomo/index.html"


def _carica_html() -> str:
    for p in _CANDIDATI:
        try:
            with open(p, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            continue
    return ""


def _bottone_finestra_separata(html: str) -> None:
    """Apre il metronomo in una scheda del browser tutta sua.

    Dentro la pagina del gestionale il metronomo si ferma appena si cambia
    voce di menu. Nella scheda separata continua a suonare mentre si lavora
    sulla scheda del paziente. Non dipende da pnev.it: usa lo stesso file."""
    import json
    carico = json.dumps(html).replace("</", "<\\/")
    components.html(
        """
<button id="apri" style="width:100%;padding:12px 16px;border-radius:8px;border:0;cursor:pointer;
  background:#1D6B44;color:#fff;font-weight:bold;font-size:15px;font-family:sans-serif">
  🪟 Apri il metronomo in una scheda separata (resta acceso mentre cambi pagina)</button>
<div id="msg" style="font:13px sans-serif;color:#b00020;margin-top:6px"></div>
<script>
const PAGINA = """ + carico + """;
document.getElementById('apri').addEventListener('click', function () {
  try {
    const url = URL.createObjectURL(new Blob([PAGINA], {type: 'text/html'}));
    const w = window.open(url, '_blank');
    if (!w) { document.getElementById('msg').textContent =
      'Il browser ha bloccato la nuova scheda: consenti i popup per questo sito e riprova.'; }
  } catch (e) { document.getElementById('msg').textContent = 'Non riesco ad aprire la scheda: ' + e; }
});
</script>
""", height=78)


def render_pnev_metronomo() -> None:
    st.subheader("🥁 PNEV Metronomo")
    st.caption("Esercizi ritmici, integrazione bilaterale e timing. Alternanza destra/sinistra "
              "in cuffia, suddivisioni, tap tempo, timer di seduta e flash visivo.")

    st.markdown(
        f'<a href="{URL_PUBBLICO}" target="_blank" rel="noopener" '
        'style="display:inline-block;margin-bottom:12px;padding:10px 16px;border-radius:8px;'
        'background:#1D6B44;color:#fff;font-weight:bold;text-decoration:none;font-size:14px">'
        '🔗 Versione per il paziente (pnev.it) — da inviare per il lavoro a casa</a>',
        unsafe_allow_html=True)

    html = _carica_html()
    if html:
        _bottone_finestra_separata(html)
        components.html(html, height=820, scrolling=True)
    else:
        st.error("File metronomo non trovato: verifica che static/pnev_metronomo/index.html "
                "sia stato caricato su GitHub.")
