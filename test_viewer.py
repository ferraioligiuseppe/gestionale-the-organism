# -*- coding: utf-8 -*-
"""
Visualizzatore tavole per i test visivi (riutilizzabile).

`mostra_tavola(img_bytes, titolo)` mostra un'immagine SEMPRE adattata allo
schermo (object-fit: contain) con un pulsante ⛶ per lo schermo intero, così
la tavola entra sempre — anche su 13" o sul monitor del paziente.
"""

import base64 as _b64
import streamlit.components.v1 as components


def mostra_tavola(img_bytes, titolo: str = "", altezza: int = 540):
    if not img_bytes:
        return
    uri = "data:image/png;base64," + _b64.b64encode(img_bytes).decode()
    html = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
  html,body{margin:0;height:100%;background:#fff;font-family:-apple-system,Segoe UI,Roboto,sans-serif}
  .bar{display:flex;align-items:center;gap:12px;padding:6px 10px;background:#f4f6f8}
  .bar b{font-size:14px}
  button{padding:7px 14px;border:none;border-radius:7px;cursor:pointer;font-size:14px;font-weight:bold;color:#fff;background:#1f8a5b}
  #box{display:flex;align-items:center;justify-content:center;background:#fff;height:CALCpx;padding:8px}
  #box img{max-width:100%;max-height:100%;object-fit:contain}
  #box:fullscreen{background:#fff;height:100vh;width:100vw}
  #box:fullscreen img{max-width:100vw;max-height:100vh}
</style></head><body>
<div class="bar"><button onclick="fs()">⛶ Schermo intero</button><b>TITOLO</b></div>
<div id="box"><img src="URI"></div>
<script>
function fs(){const e=document.getElementById('box');
 const r=e.requestFullscreen||e.webkitRequestFullscreen||e.mozRequestFullScreen;
 if(r) r.call(e);}
</script></body></html>"""
    html = html.replace("CALC", str(max(260, altezza - 60)))
    html = html.replace("TITOLO", titolo or "").replace("URI", uri)
    components.html(html, height=altezza, scrolling=False)
