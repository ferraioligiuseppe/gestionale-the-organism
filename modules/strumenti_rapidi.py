# -*- coding: utf-8 -*-
"""Strumenti rapidi — la cintura degli attrezzi, sempre in fondo al menu.

Il metronomo e il cronometro non sono destinazioni: sono strumenti che
servono MENTRE fai altro — mentre somministri un test a tempo, mentre
conduci un esercizio ritmico. Metterli come voce di menu significa dover
lasciare la schermata su cui stai lavorando.

Qui si aprono in una FINESTRA SEPARATA, e la ragione è tecnica prima che
di comodità: Streamlit ricarica la pagina a ogni interazione, e un
metronomo dentro la pagina si fermerebbe a ogni clic. Una finestra a
parte continua a funzionare per conto suo — la sposti su un angolo dello
schermo o sul secondo monitor e resta lì, mentre nel gestionale compili.
"""
from __future__ import annotations

import base64

import streamlit as st
import streamlit.components.v1 as components

import os

# Il metronomo vive nel repo: la copia su pnev.it non è pubblicata (404),
# quindi si legge il file locale e lo si scrive dentro la finestra.
_METRONOMO_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "static", "pnev_metronomo", "index.html")


def _html_metronomo() -> str:
    try:
        with open(_METRONOMO_FILE, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""


def _apri_finestra(nome_finestra: str, html: str = "", url: str = "",
                   larghezza: int = 460, altezza: int = 680) -> None:
    """Apre (o riporta in primo piano) una finestra separata.

    L'HTML viene passato come data-URL in base64 invece che con
    document.write: il metronomo contiene JavaScript con template
    literal, e qualunque `${...}` dentro una stringa JS verrebbe
    interpretato e romperebbe la pagina. Il base64 non ha questo problema.
    """
    if url:
        sorgente = f"w = window.open({url!r}, {nome_finestra!r}, opts);"
    else:
        b64 = base64.b64encode(html.encode("utf-8")).decode()
        sorgente = (f"w = window.open('data:text/html;base64,{b64}', "
                    f"{nome_finestra!r}, opts);")
    components.html(f"""<script>
      var opts = 'width={larghezza},height={altezza},menubar=no,toolbar=no,location=no';
      var w;
      {sorgente}
      if (w) {{ w.focus(); }}
      else {{ alert('Il browser ha bloccato la finestra: consenti i popup per questo sito.'); }}
    </script>""", height=0)


_CRONOMETRO = """<!DOCTYPE html><html lang="it"><head><meta charset="utf-8">
<title>Cronometro · The Organism</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{background:#0f1512;color:#fff;font-family:system-ui,sans-serif;
       display:flex;flex-direction:column;align-items:center;justify-content:center;
       min-height:100vh;gap:18px;padding:20px}
  #t{font-size:19vw;font-weight:600;font-variant-numeric:tabular-nums;letter-spacing:-2px;
     line-height:1}
  .riga{display:flex;gap:10px;flex-wrap:wrap;justify-content:center}
  button{background:#1D6B44;color:#fff;border:0;border-radius:999px;padding:13px 26px;
         font-size:16px;font-weight:600;cursor:pointer;font-family:inherit}
  button.sec{background:#2a3a33}
  #giri{width:100%;max-width:380px;max-height:34vh;overflow:auto;font-size:14px;
        font-variant-numeric:tabular-nums}
  #giri div{display:flex;justify-content:space-between;padding:5px 10px;
            border-bottom:1px solid #22302b;color:#cfe8da}
  .nota{font-size:12px;color:#7f938a;text-align:center;max-width:380px}
</style></head><body>
  <div id="t">0.0</div>
  <div class="riga">
    <button id="vai">Avvia</button>
    <button id="giro" class="sec">Giro</button>
    <button id="zero" class="sec">Azzera</button>
  </div>
  <div id="giri"></div>
  <p class="nota">Barra spaziatrice: avvia e ferma · G: giro · Questa finestra resta
     aperta mentre lavori nel gestionale.</p>
<script>
  var t0=0, acc=0, run=false, tick=null, n=0;
  var el=document.getElementById('t'), giri=document.getElementById('giri');
  function fmt(ms){
    var s=ms/1000;
    if(s<60) return s.toFixed(1);
    var m=Math.floor(s/60); var r=s-m*60;
    return m+':'+(r<10?'0':'')+r.toFixed(1);
  }
  function mostra(){ el.textContent=fmt(acc+(run?Date.now()-t0:0)); }
  function avvia(){
    if(run){ acc+=Date.now()-t0; run=false; clearInterval(tick);
             document.getElementById('vai').textContent='Riprendi'; }
    else { t0=Date.now(); run=true; tick=setInterval(mostra,50);
           document.getElementById('vai').textContent='Ferma'; }
    mostra();
  }
  function segnaGiro(){
    if(!run && acc===0) return;
    n++;
    var d=document.createElement('div');
    d.innerHTML='<span>'+n+'</span><span>'+fmt(acc+(run?Date.now()-t0:0))+'</span>';
    giri.insertBefore(d, giri.firstChild);
  }
  function azzera(){
    run=false; clearInterval(tick); acc=0; n=0; giri.innerHTML='';
    document.getElementById('vai').textContent='Avvia'; mostra();
  }
  document.getElementById('vai').onclick=avvia;
  document.getElementById('giro').onclick=segnaGiro;
  document.getElementById('zero').onclick=azzera;
  document.addEventListener('keydown',function(e){
    if(e.code==='Space'){ e.preventDefault(); avvia(); }
    if(e.key==='g'||e.key==='G'){ segnaGiro(); }
  });
  mostra();
</script></body></html>"""


def cintura_strumenti() -> None:
    """Riga di strumenti in fondo al menu, disponibile in ogni schermata."""
    with st.sidebar:
        st.markdown("---")
        aperta = st.session_state.get("_cintura_aperta", False)
        if st.button("🧰 Strumenti rapidi", key="cintura_toggle",
                     use_container_width=True):
            st.session_state["_cintura_aperta"] = not aperta
            st.rerun()
        if not st.session_state.get("_cintura_aperta"):
            return

        st.caption("Si aprono in una finestra a parte: restano attivi mentre "
                   "lavori qui dentro.")

        if st.button("🥁 Metronomo", key="cintura_metro", use_container_width=True):
            _h = _html_metronomo()
            if _h:
                _apri_finestra("pnev_metronomo", html=_h, larghezza=520, altezza=780)
            else:
                st.error("Metronomo non trovato: serve "
                         "static/pnev_metronomo/index.html nel repo.")

        if st.button("⏱️ Cronometro", key="cintura_crono", use_container_width=True):
            _apri_finestra("pnev_cronometro", html=_CRONOMETRO,
                           larghezza=420, altezza=560)

        if st.button("🖥️ Schermo paziente", key="cintura_monitor",
                     use_container_width=True):
            st.session_state["_cintura_monitor"] = True

        if st.session_state.get("_cintura_monitor"):
            testo = st.text_area(
                "Cosa mostrare", key="cintura_testo", height=80,
                placeholder="Scrivi qui e invialo al secondo schermo: una parola, "
                            "una consegna, un numero…")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Invia", key="cintura_invia", use_container_width=True,
                             type="primary"):
                    if testo.strip():
                        safe = testo.replace("<", "&lt;").replace(">", "&gt;")
                        # Stessa finestra degli altri test: una sola, si sposta
                        # una volta sul secondo monitor e resta lì.
                        _apri_finestra(
                            "finestra_screening_bambino",
                            html="<!DOCTYPE html><html><head><meta charset='utf-8'>"
                                 "<title>The Organism</title><style>"
                                 "body{margin:0;background:#0f1512;color:#fff;display:flex;"
                                 "align-items:center;justify-content:center;min-height:100vh;"
                                 "font-family:system-ui,sans-serif}"
                                 ".c{font-size:5vw;text-align:center;padding:40px;"
                                 "line-height:1.4;font-weight:600}</style></head><body>"
                                 f"<div class='c'>{safe}</div></body></html>",
                            larghezza=900, altezza=650)
            with c2:
                if st.button("Chiudi", key="cintura_chiudi_mon",
                             use_container_width=True):
                    st.session_state["_cintura_monitor"] = False
                    st.rerun()
