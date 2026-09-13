# -*- coding: utf-8 -*-
"""Protocollo di valutazione — versione app HTML (import dal file preparato
con un altro assistente). Impaginazione A4 fedele al PDF, calcolatori con
indici automatici (PCC, %SS, ecc.), export/import JSON, stampa diretta.

Limiti da sapere:
- Il salvataggio "Salva"/"Riapri" della app usa il localStorage del BROWSER,
  non il database dei pazienti: è legato al dispositivo/browser usato in
  quel momento, non al paziente nel gestionale. Per conservarlo nel
  fascicolo del paziente, usa "Esporta" (scarica un file .json) e poi carica
  quel file in un secondo momento con "Importa" — anche da un altro
  dispositivo.
- Il bottone "Bozza di sintesi assistita" chiama l'API Anthropic
  DIRETTAMENTE dal browser con una chiave API incollata dall'utente: la
  chiave resta solo nella sessione del browser (si cancella chiudendo la
  scheda) e non passa dal gestionale. Se preferite non inserire chiavi API
  personali qui, usate invece "Genera relazione" nel modulo Screening o nel
  Protocollo di valutazione (tabelle), che usa l'AI già configurata nel
  gestionale.
"""
from __future__ import annotations
import os
import streamlit as st
import streamlit.components.v1 as components

_HTML_PATH = os.path.join(os.path.dirname(__file__), "..", "static_protocollo",
                          "PNEV_protocollo_app_MASTER.html")


def render_protocollo_pdf_app(conn=None, paz_id=None, paziente=None) -> None:
    st.header("📋 Protocollo di valutazione — app stampabile")
    st.caption("Versione a impaginazione A4 fedele al documento, con calcolatori automatici "
               "(PCC, %SS, indici) e stampa diretta.")
    st.warning("⚠️ Salvataggio: usa **Esporta** per scaricare i dati come file, e **Importa** per "
               "riaprirli — così restano legati al paziente indipendentemente dal browser usato. "
               "\"Salva\"/\"Riapri\" nella barra della app usano solo la memoria di questo browser.")

    _pdf_path = os.path.join(os.path.dirname(__file__), "..", "static_protocollo",
                              "Protocollo_valutazione_TheOrganism.pdf")
    try:
        with open(_pdf_path, "rb") as f:
            st.download_button("📄 Scarica il protocollo in PDF (bianco, da compilare a mano)",
                                data=f.read(), file_name="Protocollo_valutazione_TheOrganism.pdf",
                                mime="application/pdf")
    except Exception:
        pass

    try:
        with open(_HTML_PATH, "r", encoding="utf-8") as f:
            html = f.read()
    except Exception as e:
        st.error(f"File del protocollo non trovato: {e}")
        return

    _second_monitor_js = """
<style>
#pnev_sm_btn{position:fixed;bottom:16px;right:16px;z-index:9999;background:#1D6B44;color:#fff;
border:0;border-radius:999px;padding:10px 16px;font-size:13px;font-family:sans-serif;cursor:pointer;
box-shadow:0 2px 10px rgba(0,0,0,.25)}
#pnev_sm_hint{position:fixed;bottom:60px;right:16px;z-index:9999;background:#123a6b;color:#fff;
font-size:11px;font-family:sans-serif;padding:6px 10px;border-radius:6px;max-width:220px;display:none}
.pnev_sm_ico{cursor:pointer;margin-left:5px;font-size:.85em;opacity:.7;text-decoration:none;user-select:none}
.pnev_sm_ico:hover{opacity:1}
</style>
<button id="pnev_sm_btn" class="noprint" type="button">🖥️ Seleziona testo → secondo monitor</button>
<div id="pnev_sm_hint" class="noprint">Seleziona un testo/stimolo nella pagina, poi clicca di nuovo questo bottone.</div>
<script>
(function(){
  function openMonitor(text){
    var safe = (text||'').replace(/`/g,"'").replace(/<\\//g,'<\\\\/');
    var w = window.open('', 'finestra_screening_bambino');
    if (w){
      w.document.open();
      w.document.write('<!DOCTYPE html><html><head><meta charset="utf-8">' +
        '<title>The Organism · Schermo paziente</title><style>' +
        'body{margin:0;background:#0f1512;color:#fff;display:flex;align-items:center;' +
        'justify-content:center;min-height:100vh;font-family:sans-serif;}' +
        '.c{font-size:4vw;text-align:center;padding:40px;letter-spacing:.08em;line-height:1.5;font-weight:600;}' +
        '</style></head><body><div class="c">' + safe + '</div></body></html>');
      w.document.close();
      w.focus();
    } else {
      alert('Il browser ha bloccato la finestra popup: consenti i popup per questo sito.');
    }
  }

  // Bottone flottante generico: invia il testo selezionato con il mouse
  var btn = document.getElementById('pnev_sm_btn');
  var hint = document.getElementById('pnev_sm_hint');
  btn.addEventListener('click', function(){
    var sel = window.getSelection ? window.getSelection().toString().trim() : '';
    if (!sel){ hint.style.display='block'; setTimeout(function(){hint.style.display='none';}, 3500); return; }
    openMonitor(sel);
  });

  // Icona dedicata su ogni stimolo (.stim): un clic, senza dover selezionare nulla —
  // usata per liste di parole/non parole, bilancio fonetico, frasi, ecc.
  document.querySelectorAll('.stim').forEach(function(el){
    var ico = document.createElement('span');
    ico.className = 'pnev_sm_ico noprint';
    ico.title = 'Mostra questo stimolo sul secondo monitor';
    ico.textContent = '🖥️';
    ico.addEventListener('click', function(ev){
      ev.stopPropagation();
      openMonitor(el.textContent.trim());
    });
    el.appendChild(ico);
  });
})();
</script>
</body>
"""
    if "</body>" in html:
        html = html.replace("</body>", _second_monitor_js, 1)
    else:
        html += _second_monitor_js

    components.html(html, height=1400, scrolling=True)
