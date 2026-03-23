# -*- coding: utf-8 -*-
"""
Modulo: Bilancio Uditivo — Metodo Tomatis/Hiperion
Gestionale The Organism – PNEV

Test implementati:
  1. Lateralita uditiva di ricezione (WebAudio browser, 16 frequenze)
  2. Elasticita del timpano (noise generator + registrazione tolleranza)
  3. Test dicotico di Johansen (20 coppie sillabe, punteggio OD/OS)
  4. Sintesi + storico nel tempo con grafici

Salvataggio DB: tabella bilanci_uditivi
"""

import io
import wave
import math
import json
import streamlit as st
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import streamlit.components.v1 as components
import pandas as pd
from datetime import date, datetime

JOHANSEN_COPPIE = [
    {"od":"DAT","os":"SOT"},{"od":"MYL","os":"GIF"},{"od":"NIK","os":"VEF"},
    {"od":"GIF","os":"KIT"},{"od":"FAK","os":"BAT"},{"od":"NUR","os":"NIK"},
    {"od":"SOT","os":"VYF"},{"od":"GEP","os":"RIS"},{"od":"VYF","os":"MYL"},
    {"od":"POS","os":"LIR"},{"od":"BOT","os":"TIK"},{"od":"VEF","os":"FAK"},
    {"od":"KIR","os":"DAT"},{"od":"KIT","os":"NUR"},{"od":"TIK","os":"BOT"},
    {"od":"LYM","os":"LYM"},{"od":"TOS","os":"HUT"},{"od":"BAT","os":"GEP"},
    {"od":"RIS","os":"POS"},{"od":"HUT","os":"TOS"},
]

FREQS_16 = [125,250,500,750,1000,1500,2000,3000,4000,6000,8000,10500,12000,14000,16000,18000]

_HTML_TEMPLATE = '<!DOCTYPE html><html><head><meta charset="utf-8">\n<style>\n*{box-sizing:border-box;margin:0;padding:0;font-family:system-ui,sans-serif}\nbody{padding:10px;background:#f8f7f4;color:#1a1a1a}\n.tabs{display:flex;border-bottom:2px solid #d4cec5;margin-bottom:12px;flex-wrap:wrap;gap:2px}\n.tab{padding:6px 12px;font-size:12px;cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-2px;color:#8a8a8a}\n.tab.active{color:#2d7d6f;font-weight:600;border-bottom-color:#2d7d6f}\n.section{display:none}.section.active{display:block}\n.card{background:#fff;border:1px solid #d4cec5;border-radius:10px;padding:12px 14px;margin-bottom:10px}\nh3{font-size:13px;font-weight:500;margin-bottom:3px}\n.cap{font-size:11px;color:#8a8a8a;margin-bottom:8px;line-height:1.4}\nbutton{font-family:inherit;font-size:12px;padding:5px 10px;border-radius:7px;border:1.5px solid #d4cec5;background:#fff;color:#4a4a4a;cursor:pointer;transition:all .15s}\nbutton:hover{background:#e8f3f1;border-color:#2d7d6f;color:#1a5248}\nbutton.primary{background:#2d7d6f;border-color:#2d7d6f;color:#fff}\nbutton:disabled{opacity:.4;cursor:not-allowed}\n.row{display:flex;align-items:center;gap:8px;margin:5px 0;font-size:12px;color:#4a4a4a}\n.row label{min-width:130px;font-size:11px}\n.row input[type=range]{flex:1;accent-color:#2d7d6f}\n.row span{min-width:44px;font-size:12px;font-weight:500}\n.grid2{display:grid;grid-template-columns:1fr 1fr;gap:10px}\n.ear{background:#f8f7f4;border-radius:8px;padding:10px;text-align:center}\n.ear-l{font-size:10px;font-weight:600;letter-spacing:.05em;text-transform:uppercase;margin-bottom:6px}\n.ear.od .ear-l{color:#c0392b}.ear.os .ear-l{color:#2980b9}\n.big{font-size:24px;font-weight:500}.unit{font-size:10px;color:#8a8a8a;margin-top:2px}\n.btn-row{display:flex;gap:5px;margin:8px 0;flex-wrap:wrap}\n.freq-grid{display:grid;grid-template-columns:repeat(8,1fr);gap:3px;margin:6px 0}\n.fq{font-size:10px;padding:4px 2px;border-radius:4px;text-align:center;border:1px solid #d4cec5;cursor:pointer;background:#f8f7f4;color:#8a8a8a}\n.fq.active{background:#e8f3f1;border-color:#2d7d6f;color:#1a5248;font-weight:600}\n.fq.done{background:#eaf5f0;border-color:#2d7d6f;color:#2d7d6f}\n.status{font-size:12px;padding:6px 10px;border-radius:6px;margin:6px 0}\n.ok{background:#e8f3f1;color:#1a5248}.warn{background:#fef7ec;color:#7a4f0a}.info{background:#ebf5fb;color:#154360}\n.meter{display:flex;gap:3px;align-items:flex-end;height:28px;margin:6px 0}\n.mb{width:8px;border-radius:2px 2px 0 0;transition:height .1s;min-height:2px}\n.jrow{display:grid;grid-template-columns:24px 70px 70px 1fr 1fr 1fr;gap:3px;padding:4px 6px;font-size:12px;align-items:center}\n.jrow:nth-child(even){background:#f8f7f4}\n.jhead{font-size:10px;font-weight:600;color:#8a8a8a;text-transform:uppercase;letter-spacing:.04em}\n.resp{font-size:11px;padding:3px 6px;min-width:36px;margin:1px}\n.resp.ok{background:#e8f3f1;border-color:#2d7d6f;color:#1a5248}\n.lat-bar{height:16px;border-radius:8px;background:#ede9e3;margin:6px 0;overflow:hidden}\n.lat-fill{height:100%;border-radius:8px;transition:width .4s;background:#2d7d6f}\n.sbox{background:#f8f7f4;border-radius:8px;padding:8px 12px;margin:5px 0}\n.sbox .sv{font-size:18px;font-weight:500}\n.ma{padding:3px 8px;border-radius:5px;border:1px solid #d4cec5;background:#f8f7f4;color:#8a8a8a;cursor:pointer;font-size:11px}\n.ma.active{background:#2d7d6f;border-color:#2d7d6f;color:#fff}\n</style></head><body>\n<div class="tabs">\n  <div class="tab active" onclick="sw(\'audio\')">&#127927; Audiogramma</div>\n  <div class="tab" onclick="sw(\'lat\')">&#127908; Lateralita</div>\n  <div class="tab" onclick="sw(\'timp\')">Timpano</div>\n  <div class="tab" onclick="sw(\'joh\')">Johansen</div>\n  <div class="tab" onclick="sw(\'ris\')">Risultati</div>\n</div>\n\n<!-- AUDIOGRAMMA TAB -->\n<div class="section active" id="tab-audio">\n<div class="card">\n  <h3>Test tonale liminare</h3>\n  <p class="cap">Start 30 dB. Risponde a 30dB -> scende a -20dB -> risale di 5dB. Ordine Hiperion: acuti a gravi.</p>\n  <div style="display:flex;gap:5px;flex-wrap:wrap;margin-bottom:8px">\n    <button style="border-color:#c0392b;background:#c0392b;color:#fff" id="bEOD" onclick="setAE(\'OD\')">OD</button>\n    <button style="border-color:#2980b9;color:#2980b9" id="bEOS" onclick="setAE(\'OS\')">OS</button>\n    <span style="font-size:11px;color:#8a8a8a;margin:0 4px;padding-top:4px">Modalita:</span>\n    <button class="ma active" id="maMan" onclick="setMA(\'man\')">Manuale</button>\n    <button class="ma" id="maSem" onclick="setMA(\'sem\')">Semi-auto</button>\n    <button class="ma" id="maAut" onclick="setMA(\'aut\')">Automatico</button>\n    <button onclick="resetA()" style="margin-left:auto;border-color:#e24b4a;color:#e24b4a;font-size:10px">Reset</button>\n  </div>\n  <div style="font-size:11px;color:#8a8a8a;margin-bottom:4px">Frequenza (ordine Hiperion: acuti -> gravi):</div>\n  <div id="aChips" style="display:flex;flex-wrap:wrap;gap:3px;margin:6px 0"></div>\n  <div style="display:flex;align-items:center;gap:14px;margin:8px 0">\n    <div style="text-align:center">\n      <div style="font-size:36px;font-weight:600;color:#2d7d6f" id="aDb">30</div>\n      <div style="font-size:12px;color:#8a8a8a">dB HL</div>\n      <div style="height:8px;background:#ede9e3;border-radius:4px;width:90px;margin:4px auto;overflow:hidden">\n        <div id="aDbBar" style="height:100%;border-radius:4px;background:#2d7d6f;width:45%;transition:width .2s"></div>\n      </div>\n    </div>\n    <div>\n      <div style="font-size:20px;font-weight:500" id="aFDisp">10.5k Hz</div>\n      <div style="font-size:11px;color:#8a8a8a" id="aEDisp">OD — Destro</div>\n    </div>\n  </div>\n  <div style="display:flex;gap:4px;flex-wrap:wrap;margin:6px 0">\n    <button onclick="adjA(-10)">-10</button>\n    <button onclick="adjA(-5)">-5</button>\n    <button onclick="adjA(-1)">-1</button>\n    <button class="primary" onclick="sendA()">&#9654; Invia tono</button>\n    <button onclick="adjA(1)">+1</button>\n    <button onclick="adjA(5)">+5</button>\n    <button onclick="adjA(10)">+10</button>\n  </div>\n  <div style="display:flex;gap:5px;margin:6px 0;flex-wrap:wrap">\n    <button onclick="aResp(true)" style="flex:1;padding:7px;border-color:#1d9e75;color:#1d9e75">&#10003; Risponde</button>\n    <button onclick="aResp(false)" style="flex:1;padding:7px;border-color:#e24b4a;color:#e24b4a">&#10007; Non risponde</button>\n    <button onclick="valA()" id="bValA" style="flex:1;padding:7px;border-color:#2d7d6f;color:#2d7d6f" disabled>&#10003; Valida soglia</button>\n    <button onclick="nextA()">&#8594; Succ.</button>\n  </div>\n  <div id="aSt" class="status info">Seleziona orecchio e frequenza, poi invia il tono.</div>\n</div>\n<div class="card">\n  <div class="grid2">\n    <div>\n      <div style="font-size:10px;color:#c0392b;font-weight:600;margin-bottom:4px">OD — Orecchio destro</div>\n      <div id="aSogOD" style="display:flex;flex-wrap:wrap;gap:3px"></div>\n    </div>\n    <div>\n      <div style="font-size:10px;color:#2980b9;font-weight:600;margin-bottom:4px">OS — Orecchio sinistro</div>\n      <div id="aSogOS" style="display:flex;flex-wrap:wrap;gap:3px"></div>\n    </div>\n  </div>\n</div>\n<div class="card">\n  <h3>Audiogramma + curva Tomatis</h3>\n  <canvas id="cvA" height="200"></canvas>\n  <div style="display:flex;gap:10px;font-size:10px;color:#8a8a8a;margin-top:4px">\n    <span style="color:#c0392b">&#9675; O = OD</span>\n    <span style="color:#2980b9">&#9747; X = OS</span>\n    <span style="color:#2d7d6f">-- Tomatis (target)</span>\n  </div>\n</div>\n<div class="card">\n  <h3>Delta EQ terapeutico</h3>\n  <p class="cap">Tomatis - soglia paziente. + = rinforzo (ipouduzione). - = attenuazione (iperudizione).</p>\n  <div id="aEQ" style="display:flex;gap:4px;justify-content:center;flex-wrap:wrap"></div>\n</div>\n</div>\n\n<!-- LATERALITA TAB -->\n<div class="section" id="tab-lat">\n<div class="card">\n  <h3>Lateralita uditiva di ricezione</h3>\n  <p class="cap">Il paziente centra il suono. Invia il tono e valida il balance.</p>\n  <div style="font-size:11px;color:#8a8a8a;margin-bottom:4px">Seleziona frequenza:</div>\n  <div class="freq-grid" id="freqGrid"></div>\n  <div class="row"><label>Volume (dB sopra soglia)</label><input type="range" id="vLat" min="10" max="50" value="30" oninput="vLatV.textContent=this.value+\'dB\'"><span id="vLatV">30dB</span></div>\n  <div class="row"><label>Balance</label><input type="range" id="bal" min="-100" max="100" value="0" oninput="updBal(this.value)"><span id="balV">Centro</span></div>\n</div>\n<div class="grid2">\n  <div class="ear od"><div class="ear-l">OD Destro</div><div class="big" id="latOD">-</div><div class="unit">errore medio</div></div>\n  <div class="ear os"><div class="ear-l">OS Sinistro</div><div class="big" id="latOS">-</div><div class="unit">errore medio</div></div>\n</div>\n<div class="btn-row">\n  <button class="primary" onclick="playLat()">Invia tono</button>\n  <button onclick="shiftB(-5)">SX</button>\n  <button onclick="shiftB(5)">DX</button>\n  <button onclick="valLat()" style="border-color:#2d7d6f;color:#2d7d6f">Valida</button>\n  <button onclick="nextFreq()">Freq. succ.</button>\n</div>\n<div id="latSt" class="status info">Seleziona frequenza e invia il tono.</div>\n</div>\n\n<!-- TIMPANO TAB -->\n<div class="section" id="tab-timp">\n<div class="card">\n  <h3>Elasticita del timpano</h3>\n  <p class="cap">Rumore da volume basso ad alto. Registra la tolleranza del paziente.</p>\n  <div class="row"><label>Volume (dB)</label><input type="range" id="vTimp" min="-40" max="0" value="-40" oninput="vTimpV.textContent=this.value+\'dB\'"><span id="vTimpV">-40dB</span></div>\n  <div class="row"><label>Tipo rumore</label>\n    <select id="noiseT" style="flex:1;font-size:12px;padding:4px 8px;border-radius:6px;border:1px solid #d4cec5">\n      <option value="white">Bianco</option><option value="pink" selected>Rosa</option><option value="brown">Marrone</option>\n    </select>\n  </div>\n  <div class="meter" id="meter"></div>\n</div>\n<div class="btn-row">\n  <button class="primary" id="btnT" onclick="togTimp()">Start</button>\n  <button onclick="adjV(-3)">-3dB</button><button onclick="adjV(3)">+3dB</button>\n</div>\n<div class="card">\n  <h3>Registra tolleranza</h3>\n  <div class="row"><label>Volume tollerato</label><input type="range" id="tolV" min="-40" max="0" value="-10" oninput="tolVV.textContent=this.value+\'dB\'"><span id="tolVV">-10dB</span></div>\n  <div class="row"><label>Durata (sec)</label><input type="range" id="durV" min="1" max="30" step="1" value="5" oninput="durVV.textContent=this.value+\'s\'"><span id="durVV">5s</span></div>\n  <div class="row"><label>Note</label><input id="timpNote" type="text" placeholder="note cliniche..." style="flex:1;padding:5px 8px;border-radius:6px;border:1px solid #d4cec5;font-size:12px"></div>\n  <div class="btn-row"><button onclick="saveTimp()">Salva timpano</button></div>\n  <div id="tSaved" class="status ok" style="display:none">Salvato</div>\n</div>\n</div>\n\n<!-- JOHANSEN TAB -->\n<div class="section" id="tab-joh">\n<div class="card">\n  <h3>Test dicotico di Johansen</h3>\n  <p class="cap">20 coppie OD/OS simultanee. Registra le risposte del paziente per ogni compito.</p>\n  <div class="btn-row">\n    <button class="primary" onclick="startJoh()">Avvia</button>\n    <button onclick="resetJoh()">Reset</button>\n  </div>\n  <div id="johSt" class="status info">Premi Avvia per iniziare.</div>\n</div>\n<div style="font-size:11px">\n  <div class="jrow jhead">\n    <div>#</div><div style="color:#c0392b">OD</div><div style="color:#2980b9">OS</div>\n    <div>Comp.3 DX</div><div>Comp.4 SX</div><div>Comp.5 Both</div>\n  </div>\n  <div id="johRows"></div>\n</div>\n<div class="grid2" style="margin-top:8px">\n  <div class="sbox"><div style="font-size:10px;color:#8a8a8a;text-transform:uppercase">Punteggio OD</div><div class="sv" id="jOD" style="color:#c0392b">0</div></div>\n  <div class="sbox"><div style="font-size:10px;color:#8a8a8a;text-transform:uppercase">Punteggio OS</div><div class="sv" id="jOS" style="color:#2980b9">0</div></div>\n</div>\n<div class="sbox">\n  <div style="font-size:10px;color:#8a8a8a">Indice (DX-SX)/(DX+SX)x100</div>\n  <div class="sv" id="jIdx">-</div>\n  <div class="lat-bar"><div class="lat-fill" id="jBar" style="width:50%"></div></div>\n  <div style="display:flex;justify-content:space-between;font-size:10px;color:#8a8a8a"><span>SX</span><span>Centro</span><span>DX</span></div>\n</div>\n</div>\n\n<!-- RISULTATI TAB -->\n<div class="section" id="tab-ris">\n<div class="card">\n  <h3>Sintesi bilancio uditivo</h3>\n  <div id="sumContent" style="font-size:13px;color:#4a4a4a">Esegui i test per vedere la sintesi.</div>\n</div>\n<div class="card">\n  <h3>Note cliniche</h3>\n  <textarea id="noteClin" rows="3" style="width:100%;font-size:12px;padding:6px 8px;border-radius:6px;border:1px solid #d4cec5;resize:vertical"></textarea>\n</div>\n<div class="btn-row"><button class="primary" onclick="saveAll()">Salva bilancio completo</button></div>\n<div id="allSaved" class="status ok" style="display:none">Bilancio salvato!</div>\n</div>\n\n<script>\nconst FREQS=__FREQS__;\nconst JOHANSEN=__JOHANSEN__;\nconst PAZ_ID=__PAZ_ID__;\nlet actx=null;\nfunction getCtx(){if(!actx)actx=new(window.AudioContext||window.webkitAudioContext)();if(actx.state===\'suspended\')actx.resume();return actx;}\n\n// ── AUDIOGRAMMA ──────────────────────────────────────────────────────────\nconst AFR=[125,250,500,750,1000,1500,2000,3000,4000,6000,8000,10500];\nconst AFL=[\'125\',\'250\',\'500\',\'750\',\'1k\',\'1.5k\',\'2k\',\'3k\',\'4k\',\'6k\',\'8k\',\'10.5k\'];\nconst AORD=[10500,8000,6000,4000,3000,2000,1500,1000,750,500,250,125];\nconst ATOM=[-5,-8,-10,-12,-14,-15,-14,-15,-12,-8,-5];\nlet aEr=\'OD\',aFI=11,aDv=30,aMd=\'man\',aLR=null;\nlet aOD=new Array(12).fill(null),aOS=new Array(12).fill(null);\n\nfunction bAC(){\n  const c=document.getElementById(\'aChips\');if(!c)return;c.innerHTML=\'\';\n  AFR.forEach((f,i)=>{\n    const d=document.createElement(\'div\');\n    const od=aOD[i]!==null,os=aOS[i]!==null;\n    let bg=\'#f8f7f4\',bc=\'#d4cec5\',cl=\'#4a4a4a\';\n    if(i===aFI){bg=\'#2d7d6f\';bc=\'#2d7d6f\';cl=\'#fff\';}\n    else if(od&&os){bg=\'#e8f3f1\';bc=\'#2d7d6f\';cl=\'#1a5248\';}\n    else if(od){bg=\'#fdecea\';bc=\'#c0392b\';cl=\'#c0392b\';}\n    else if(os){bg=\'#eaf4fb\';bc=\'#2980b9\';cl=\'#2980b9\';}\n    d.style.cssText=\'padding:3px 8px;border-radius:10px;font-size:11px;border:1px solid \'+bc+\';background:\'+bg+\';color:\'+cl+\';cursor:pointer;margin:1px\';\n    d.textContent=AFL[i]+(od||os?\' v\':\'\');\n    d.onclick=()=>{aFI=i;aDv=30;aLR=null;const bv=document.getElementById(\'bValA\');if(bv)bv.disabled=true;updA();bAC();};\n    c.appendChild(d);\n  });\n}\n\nfunction updA(){\n  const el=document.getElementById(\'aDb\');\n  if(el){el.textContent=aDv;const col=aDv<20?\'#2d7d6f\':aDv<40?\'#ba7517\':\'#e24b4a\';el.style.color=col;const bar=document.getElementById(\'aDbBar\');if(bar){bar.style.width=Math.max(0,Math.min(100,(aDv+20)/110*100))+\'%\';bar.style.background=col;}}\n  const f=AFR[aFI];\n  const fd=document.getElementById(\'aFDisp\');if(fd)fd.textContent=(f>=1000?f/1000+\'k\':f)+\' Hz\';\n  const ed=document.getElementById(\'aEDisp\');if(ed)ed.textContent=aEr===\'OD\'?\'OD — Destro\':\'OS — Sinistro\';\n}\n\nfunction setAE(e){\n  aEr=e;aDv=30;aLR=null;\n  const od=document.getElementById(\'bEOD\'),os=document.getElementById(\'bEOS\');\n  if(od){od.style.background=e===\'OD\'?\'#c0392b\':\'#fff\';od.style.color=e===\'OD\'?\'#fff\':\'#c0392b\';}\n  if(os){os.style.background=e===\'OS\'?\'#2980b9\':\'#fff\';os.style.color=e===\'OS\'?\'#fff\':\'#2980b9\';}\n  const bv=document.getElementById(\'bValA\');if(bv)bv.disabled=true;\n  updA();bAC();\n}\n\nfunction setMA(m){\n  aMd=m;\n  [\'Man\',\'Sem\',\'Aut\'].forEach(x=>{const el=document.getElementById(\'ma\'+x);if(el)el.classList.toggle(\'active\',x.toLowerCase().startsWith(m));});\n}\n\nfunction adjA(d){aDv=Math.max(-20,Math.min(90,aDv+d));updA();if(aMd!==\'man\')sendA();}\n\nfunction sendA(){\n  const ctx=getCtx();const f=AFR[aFI];\n  const amp=Math.pow(10,(aDv-90)/20)*0.85;\n  const osc=ctx.createOscillator(),g=ctx.createGain(),pan=ctx.createStereoPanner();\n  pan.pan.value=aEr===\'OD\'?0.85:-0.85;\n  osc.frequency.value=f;osc.type=\'sine\';\n  const dur=2.5;\n  g.gain.setValueAtTime(0,ctx.currentTime);\n  g.gain.linearRampToValueAtTime(amp,ctx.currentTime+0.05);\n  g.gain.setValueAtTime(amp,ctx.currentTime+dur-0.1);\n  g.gain.linearRampToValueAtTime(0,ctx.currentTime+dur);\n  osc.connect(g);g.connect(pan);pan.connect(ctx.destination);\n  osc.start();osc.stop(ctx.currentTime+dur);\n  const st=document.getElementById(\'aSt\');\n  if(st){st.textContent=\'Tono \'+f+\' Hz a \'+aDv+\' dB HL (\'+aEr+\')\';st.className=\'status ok\';}\n}\n\nfunction aResp(r){\n  if(r){\n    aLR=aDv;const bv=document.getElementById(\'bValA\');if(bv)bv.disabled=false;\n    if(aDv===30){aDv=-20;}else{aDv=Math.max(-20,aDv-5);}\n    updA();const st=document.getElementById(\'aSt\');\n    if(st){st.textContent=\'Risponde a \'+aLR+\' dB -> scendo a \'+aDv+\' dB\';st.className=\'status ok\';}\n  } else {\n    aDv=Math.min(90,aDv+5);updA();\n    const st=document.getElementById(\'aSt\');\n    if(st){st.textContent=\'Non risponde -> salgo a \'+aDv+\' dB\';st.className=\'status warn\';}\n  }\n  if(aMd===\'sem\'||aMd===\'aut\')setTimeout(sendA,500);\n}\n\nfunction valA(){\n  const db=aLR!==null?aLR:aDv;\n  if(aEr===\'OD\')aOD[aFI]=db;else aOS[aFI]=db;\n  aLR=null;aDv=30;\n  const bv=document.getElementById(\'bValA\');if(bv)bv.disabled=true;\n  const st=document.getElementById(\'aSt\');\n  if(st){st.textContent=\'Soglia \'+AFR[aFI]+\' Hz = \'+db+\' dB HL\';st.className=\'status ok\';}\n  bAC();bASog();drwA();calcA();\n  const ci=AORD.indexOf(AFR[aFI]);\n  if(ci>=0&&ci<AORD.length-1){\n    const ni=AFR.indexOf(AORD[ci+1]);\n    if(ni>=0){aFI=ni;aDv=30;updA();bAC();}\n    if(aMd===\'aut\')setTimeout(sendA,800);\n  }\n}\n\nfunction nextA(){\n  const ci=AORD.indexOf(AFR[aFI]);\n  if(ci>=0&&ci<AORD.length-1){\n    const ni=AFR.indexOf(AORD[ci+1]);\n    if(ni>=0){aFI=ni;aDv=30;aLR=null;updA();bAC();const bv=document.getElementById(\'bValA\');if(bv)bv.disabled=true;}\n  }\n}\n\nfunction resetA(){aOD=new Array(12).fill(null);aOS=new Array(12).fill(null);aDv=30;aLR=null;bAC();bASog();drwA();calcA();}\n\nfunction bASog(){\n  [\'OD\',\'OS\'].forEach(e=>{\n    const arr=e===\'OD\'?aOD:aOS;const el=document.getElementById(\'aSog\'+e);if(!el)return;el.innerHTML=\'\';\n    arr.forEach((v,i)=>{if(v===null)return;const s=document.createElement(\'span\');\n      s.style.cssText=\'padding:2px 7px;border-radius:9px;font-size:11px;background:\'+(e===\'OD\'?\'#fdecea\':\'#eaf4fb\')+\';border:1px solid \'+(e===\'OD\'?\'#c0392b\':\'#2980b9\')+\';color:\'+(e===\'OD\'?\'#c0392b\':\'#2980b9\')+\';margin:1px\';\n      s.textContent=AFL[i]+\':\'+v+\'dB\';el.appendChild(s);});\n  });\n}\n\nfunction drwA(){\n  const cv=document.getElementById(\'cvA\');if(!cv)return;\n  cv.width=cv.parentElement.clientWidth-28;\n  const c=cv.getContext(\'2d\'),W=cv.width,H=cv.height;\n  const pL=36,pR=8,pT=14,pB=20,cw=W-pL-pR,ch=H-pT-pB;\n  c.clearRect(0,0,W,H);c.fillStyle=\'#fff\';c.fillRect(0,0,W,H);\n  const mn=-20,mx=90,N=11;\n  const tx=i=>pL+i*(cw/(N-1));const ty=d=>pT+(d-mn)/(mx-mn)*ch;\n  c.strokeStyle=\'rgba(128,128,128,0.1)\';c.lineWidth=0.5;\n  for(let d=mn;d<=mx;d+=10){c.beginPath();c.moveTo(pL,ty(d));c.lineTo(W-pR,ty(d));c.stroke();}\n  for(let i=0;i<N;i++){c.beginPath();c.moveTo(tx(i),pT);c.lineTo(tx(i),pT+ch);c.stroke();}\n  c.strokeStyle=\'rgba(128,128,128,0.4)\';c.lineWidth=1;c.beginPath();c.moveTo(pL,ty(0));c.lineTo(W-pR,ty(0));c.stroke();\n  c.fillStyle=\'#aaa\';c.font=\'8px sans-serif\';c.textAlign=\'right\';\n  for(let d=mn;d<=mx;d+=10)c.fillText(d,pL-3,ty(d)+3);\n  c.textAlign=\'center\';for(let i=0;i<N;i++)c.fillText(AFL[i],tx(i),pT+ch+12);\n  c.strokeStyle=\'#2d7d6f\';c.lineWidth=2;c.setLineDash([5,4]);\n  c.beginPath();ATOM.forEach((v,i)=>i===0?c.moveTo(tx(i),ty(v)):c.lineTo(tx(i),ty(v)));c.stroke();c.setLineDash([]);\n  function dc(arr,col,sym){\n    const pts=arr.slice(0,N).map((v,i)=>v!==null?[tx(i),ty(v)]:null).filter(Boolean);\n    if(!pts.length)return;\n    c.strokeStyle=col;c.lineWidth=1.8;c.beginPath();pts.forEach(([x,y],i)=>i===0?c.moveTo(x,y):c.lineTo(x,y));c.stroke();\n    c.fillStyle=col;c.font=\'bold 11px sans-serif\';c.textAlign=\'center\';pts.forEach(([x,y])=>c.fillText(sym,x,y+4));\n  }\n  dc(aOD,\'#c0392b\',\'O\');dc(aOS,\'#2980b9\',\'X\');\n}\n\nfunction calcA(){\n  const g=document.getElementById(\'aEQ\');if(!g)return;g.innerHTML=\'\';\n  for(let i=0;i<11;i++){\n    const v=aOD[i]!==null?Math.round(ATOM[i]-aOD[i]):aOS[i]!==null?Math.round(ATOM[i]-aOS[i]):null;\n    if(v===null)continue;\n    const col=v>3?\'#1d9e75\':v<-3?\'#e24b4a\':\'#ba7517\';\n    const h=Math.min(26,Math.abs(v)*2);\n    const pos=v>=0?\'bottom:50%;height:\'+h+\'px\':\'top:50%;height:\'+h+\'px\';\n    const d=document.createElement(\'div\');\n    d.style.cssText=\'display:flex;flex-direction:column;align-items:center;gap:2px\';\n    d.innerHTML=\'<div style="width:14px;height:54px;background:#ede9e3;border-radius:3px;position:relative;overflow:hidden"><div style="position:absolute;width:100%;border-radius:2px;background:\'+col+\';\'+pos+\'"></div></div><div style="font-size:10px;font-weight:500;color:\'+col+\'">\'+(v>0?\'+\':\'\')+v+\'</div><div style="font-size:9px;color:#8a8a8a">\'+AFL[i]+\'</div>\';\n    g.appendChild(d);\n  }\n}\n\n// ── LATERALITA ──────────────────────────────────────────────────────────\nlet latData={},curF=FREQS[0],curBal=0;\nconst fg=document.getElementById(\'freqGrid\');\nFREQS.forEach(f=>{const d=document.createElement(\'div\');d.className=\'fq\'+(f===curF?\' active\':\'\');d.textContent=f>=1000?(f/1000)+\'k\':f;d.onclick=()=>{curF=f;rfg();};fg.appendChild(d);});\nfunction rfg(){Array.from(fg.children).forEach((d,i)=>{const f=FREQS[i];d.className=\'fq\';if(f===curF)d.classList.add(\'active\');else if(latData[f]!==undefined)d.classList.add(\'done\');});}\nfunction updBal(v){curBal=parseInt(v);balV.textContent=v==0?\'Centro\':(v<0?Math.abs(v)+\'% SX\':v+\'% DX\');}\nfunction shiftB(delta){const s=document.getElementById(\'bal\');s.value=Math.max(-100,Math.min(100,parseInt(s.value)+delta));updBal(s.value);}\nfunction playLat(){const ctx=getCtx();const osc=ctx.createOscillator(),g=ctx.createGain(),pan=ctx.createStereoPanner();osc.frequency.value=curF;osc.type=\'sine\';g.gain.value=0.25;pan.pan.value=curBal/100;osc.connect(g);g.connect(pan);pan.connect(ctx.destination);osc.start();osc.stop(ctx.currentTime+2);latSt.textContent=\'Tono \'+curF+\' Hz - Balance: \'+balV.textContent;latSt.className=\'status ok\';}\nfunction valLat(){latData[curF]=curBal;latSt.textContent=\'Validato \'+curF+\' Hz (balance \'+curBal+\')\';rfg();const vals=Object.values(latData);if(vals.length>0){const avg=Math.round(vals.reduce((a,b)=>a+b,0)/vals.length);latOD.textContent=avg>0?\'+\'+avg:\'-\';latOS.textContent=avg<0?Math.abs(avg):\'-\';}results.lat=latData;updSum();}\nfunction nextFreq(){const i=FREQS.indexOf(curF);if(i<FREQS.length-1){curF=FREQS[i+1];document.getElementById(\'bal\').value=0;updBal(0);rfg();}}\n\n// ── TIMPANO ──────────────────────────────────────────────────────────────\nlet tNode=null,tPlaying=false,mInt=null;\nfunction genNoise(ctx,type){const buf=ctx.createBuffer(1,ctx.sampleRate*3,ctx.sampleRate);const d=buf.getChannelData(0);if(type===\'white\'){for(let i=0;i<d.length;i++)d[i]=Math.random()*2-1;}else if(type===\'pink\'){let b0=0,b1=0,b2=0,b3=0,b4=0,b5=0,b6=0;for(let i=0;i<d.length;i++){const w=Math.random()*2-1;b0=.99886*b0+w*.0555179;b1=.99332*b1+w*.0750759;b2=.969*b2+w*.153852;b3=.8665*b3+w*.3104856;b4=.55*b4+w*.5329522;b5=-.7616*b5-w*.016898;d[i]=(b0+b1+b2+b3+b4+b5+b6+w*.5362)*.11;b6=w*.115926;}}else{let last=0;for(let i=0;i<d.length;i++){const w=Math.random()*2-1;last=(last+.02*w)/1.02;d[i]=last*3.5;}}return buf;}\nfunction togTimp(){const ctx=getCtx();if(tPlaying&&tNode){tNode.stop();tPlaying=false;btnT.textContent=\'Start\';clearInterval(mInt);meter.innerHTML=\'\';return;}const v=parseFloat(vTimp.value),nt=document.getElementById(\'noiseT\').value;const buf=genNoise(ctx,nt);const src=ctx.createBufferSource();const g=ctx.createGain();src.buffer=buf;src.loop=true;g.gain.value=Math.pow(10,v/20);src.connect(g);g.connect(ctx.destination);src.start();tNode=src;tPlaying=true;btnT.textContent=\'Stop\';mInt=setInterval(animM,100);}\nfunction animM(){if(!tPlaying)return;const v=(parseFloat(vTimp.value)+40)/40;meter.innerHTML=\'\';for(let i=0;i<14;i++){const b=document.createElement(\'div\');b.className=\'mb\';const h=Math.random()*18*v+3;b.style.height=h+\'px\';b.style.background=v>.8?\'#e74c3c\':v>.5?\'#f39c12\':\'#2d7d6f\';meter.appendChild(b);}}\nfunction updVT(v){vTimpV.textContent=v+\'dB\';}\nfunction adjV(delta){const s=document.getElementById(\'vTimp\');s.value=Math.max(-40,Math.min(0,parseInt(s.value)+delta));updVT(s.value);}\nfunction saveTimp(){results.timp={vol:tolV.value,dur:durV.value,note:document.getElementById(\'timpNote\').value};tSaved.style.display=\'block\';setTimeout(()=>tSaved.style.display=\'none\',2000);updSum();}\n\n// ── JOHANSEN ──────────────────────────────────────────────────────────────\nlet johAns={};\nlet results={};\nfunction buildJoh(){johRows.innerHTML=\'\';JOHANSEN.forEach((r,i)=>{const d=document.createElement(\'div\');d.className=\'jrow\';d.id=\'jr\'+i;d.innerHTML=\'<span style="color:#8a8a8a;font-size:10px">\'+(i+1)+\'</span><span style="color:#c0392b;font-weight:600">\'+r.od+\'</span><span style="color:#2980b9;font-weight:600">\'+r.os+\'</span><div><button class="resp" id="c3od\'+i+\'" onclick="mk(\'+i+\',\\\'c3\\\',\\\'od\\\')">OD</button><button class="resp" id="c3os\'+i+\'" onclick="mk(\'+i+\',\\\'c3\\\',\\\'os\\\')">OS</button></div><div><button class="resp" id="c4od\'+i+\'" onclick="mk(\'+i+\',\\\'c4\\\',\\\'od\\\')">OD</button><button class="resp" id="c4os\'+i+\'" onclick="mk(\'+i+\',\\\'c4\\\',\\\'os\\\')">OS</button></div><div><button class="resp" id="c5od\'+i+\'" onclick="mk(\'+i+\',\\\'c5\\\',\\\'od\\\')">OD</button><button class="resp" id="c5os\'+i+\'" onclick="mk(\'+i+\',\\\'c5\\\',\\\'os\\\')">OS</button><button class="resp" id="c5b\'+i+\'" onclick="mk(\'+i+\',\\\'c5\\\',\\\'b\\\')">Ent</button></div>\';johRows.appendChild(d);});}\nfunction startJoh(){buildJoh();johSt.textContent=\'Leggi le coppie e registra le risposte.\';johSt.className=\'status ok\';}\nfunction resetJoh(){johAns={};jOD.textContent=\'0\';jOS.textContent=\'0\';jIdx.textContent=\'-\';jBar.style.width=\'50%\';buildJoh();johSt.textContent=\'Premi Avvia.\';johSt.className=\'status info\';}\nfunction mk(i,comp,side){if(!johAns[i])johAns[i]={};johAns[i][comp]=side;[\'od\',\'os\',\'b\'].forEach(s=>{const el=document.getElementById(comp+s+i);if(el)el.classList.remove(\'ok\');});const el=document.getElementById(comp+side+i);if(el)el.classList.add(\'ok\');calcJoh();}\nfunction calcJoh(){let od=0,os=0;JOHANSEN.forEach((r,i)=>{const a=johAns[i]||{};if(a.c3===\'od\')od++;if(a.c4===\'os\')os++;if(a.c5===\'od\'||a.c5===\'b\')od++;if(a.c5===\'os\'||a.c5===\'b\')os++;});jOD.textContent=od;jOS.textContent=os;const tot=od+os;if(tot>0){const idx=Math.round((od-os)*100/tot);jIdx.textContent=(idx>0?\'+\':\'\')+idx+\' (\'+(idx>10?\'Dom DX\':idx<-10?\'Dom SX\':\'Bilanciato\')+\')\';jBar.style.width=((od/tot)*100)+\'%\';jBar.style.background=idx>10?\'#c0392b\':idx<-10?\'#2980b9\':\'#2d7d6f\';}results.joh={od:od,os:os,tot:tot,ans:johAns};updSum();}\n\nfunction updSum(){let h=\'\';if(results.lat){const vals=Object.values(results.lat),n=vals.length;if(n>0){const avg=Math.round(vals.reduce((a,b)=>a+b,0)/n);h+=\'<p><b>Lateralita:</b> \'+n+\' freq - balance medio \'+(avg>0?\'+\'+avg:avg)+\' (\'+(avg>5?\'Dom DX\':avg<-5?\'Dom SX\':\'Bilanciato\')+\')</p>\';}}if(results.timp)h+=\'<p><b>Timpano:</b> vol tollerato \'+results.timp.vol+\'dB per \'+results.timp.dur+\'s</p>\';if(results.joh&&results.joh.tot>0){const idx=Math.round((results.joh.od-results.joh.os)*100/results.joh.tot);h+=\'<p><b>Johansen:</b> OD=\'+results.joh.od+\' OS=\'+results.joh.os+\' Indice=\'+(idx>0?\'+\':\'\')+idx+\'</p>\';}if(aOD.some(v=>v!==null)||aOS.some(v=>v!==null)){h+=\'<p><b>Audiogramma:</b> soglie registrate - vedi tab Audiogramma per EQ</p>\';}sumContent.innerHTML=h||\'Esegui i test per vedere la sintesi.\';}\n\nfunction saveAll(){\n  const eqOD=Array.from({length:11},(_,i)=>aOD[i]!==null?Math.round(ATOM[i]-aOD[i]):0);\n  const eqOS=Array.from({length:11},(_,i)=>aOS[i]!==null?Math.round(ATOM[i]-aOS[i]):0);\n  const data={paz_id:PAZ_ID,lat:results.lat||{},timp:results.timp||{},joh:results.joh||{},od:aOD.slice(0,11),os:aOS.slice(0,11),eqOD:eqOD,eqOS:eqOS,note:document.getElementById(\'noteClin\').value};\n  window.parent.postMessage({type:\'streamlit:setComponentValue\',value:JSON.stringify(data)},\'*\');\n  allSaved.style.display=\'block\';setTimeout(()=>allSaved.style.display=\'none\',3000);\n}\n\nfunction sw(name){\n  const tabs=[\'audio\',\'lat\',\'timp\',\'joh\',\'ris\'];\n  document.querySelectorAll(\'.tab\').forEach((t,i)=>t.classList.toggle(\'active\',tabs[i]===name));\n  document.querySelectorAll(\'.section\').forEach(s=>s.classList.remove(\'active\'));\n  document.getElementById(\'tab-\'+name).classList.add(\'active\');\n  if(name===\'audio\'){setTimeout(()=>{drwA();calcA();},50);}\n}\n\n// Init\nbuildJoh();rfg();bAC();updA();\nwindow.addEventListener(\'resize\',()=>{drwA();});\nsetTimeout(()=>drwA(),150);\n</script></body></html>'


def _html_bilancioio(paz_id: int) -> str:
    return (_HTML_TEMPLATE
            .replace("__FREQS__", json.dumps(FREQS_16))
            .replace("__JOHANSEN__", json.dumps(JOHANSEN_COPPIE))
            .replace("__PAZ_ID__", str(paz_id)))


def _is_postgres(conn) -> bool:
    t = type(conn).__name__
    if "Pg" in t or "pg" in t: return True
    try:
        import sys, os
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if root not in sys.path: sys.path.insert(0, root)
        from app_patched import _DB_BACKEND
        return _DB_BACKEND == "postgres"
    except Exception: pass
    return False

def _ph(n, conn):
    return ", ".join(["%s" if _is_postgres(conn) else "?"] * n)

def _get_conn():
    try:
        from modules.app_core import get_connection; return get_connection()
    except Exception: pass
    try:
        import sys, os
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if root not in sys.path: sys.path.insert(0, root)
        from app_patched import get_connection; return get_connection()
    except Exception: pass
    import sqlite3
    conn = sqlite3.connect("organism.db"); conn.row_factory = sqlite3.Row; return conn

def _row_get(row, key, default=None):
    try: v = row[key]; return v if v is not None else default
    except Exception:
        try: return row.get(key, default)
        except: return default

def _init_db(conn):
    raw = getattr(conn, "_conn", conn)
    try: cur = raw.cursor()
    except: cur = conn.cursor()
    pg = _is_postgres(conn)
    if pg:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS bilanci_uditivi (
            id BIGSERIAL PRIMARY KEY,
            paziente_id BIGINT NOT NULL,
            data_bilancio TEXT, operatore TEXT,
            lat_balance_json TEXT, lat_balance_medio DOUBLE PRECISION, lat_dominanza TEXT,
            timp_vol_tollerato DOUBLE PRECISION, timp_durata_sec DOUBLE PRECISION, timp_note TEXT,
            joh_od INTEGER, joh_os INTEGER,
            joh_indice DOUBLE PRECISION, joh_dominanza TEXT, joh_risposte_json TEXT,
            note_cliniche TEXT, created_at TEXT
        )""")
    else:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS bilanci_uditivi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paziente_id INTEGER NOT NULL,
            data_bilancio TEXT, operatore TEXT,
            lat_balance_json TEXT, lat_balance_medio REAL, lat_dominanza TEXT,
            timp_vol_tollerato REAL, timp_durata_sec REAL, timp_note TEXT,
            joh_od INTEGER, joh_os INTEGER,
            joh_indice REAL, joh_dominanza TEXT, joh_risposte_json TEXT,
            note_cliniche TEXT, created_at TEXT
        )""")
    try: raw.commit()
    except: conn.commit()

def _salva_bilancio(conn, paz_id: int, data: dict, operatore: str = ""):
    cur = conn.cursor()
    lat = data.get("lat", {})
    lat_vals = [v for v in lat.values() if v is not None] if lat else []
    lat_medio = round(sum(lat_vals) / len(lat_vals), 2) if lat_vals else None
    lat_dom = (None if lat_medio is None else
               "DX" if lat_medio > 5 else "SX" if lat_medio < -5 else "Bilanciato")
    timp = data.get("timp", {})
    joh = data.get("joh", {})
    jod = int(joh.get("od", 0))
    jos = int(joh.get("os", 0))
    jtot = int(joh.get("tot", 0))
    jidx = round((jod - jos) * 100 / jtot, 1) if jtot > 0 else None
    jdom = (None if jidx is None else
            "DX" if jidx > 10 else "SX" if jidx < -10 else "Bilanciato")
    ph = _ph(17, conn)
    params = (
        paz_id, date.today().isoformat(), operatore,
        json.dumps(lat), lat_medio, lat_dom,
        float(timp.get("vol", 0)) if timp.get("vol") else None,
        float(timp.get("dur", 0)) if timp.get("dur") else None,
        timp.get("note", ""),
        jod, jos, jidx, jdom,
        json.dumps(joh.get("ans", {})),
        data.get("note", ""),
        datetime.now().isoformat(timespec="seconds"),
    )
    sql = (
        "INSERT INTO bilanci_uditivi (paziente_id, data_bilancio, operatore, "
        "lat_balance_json, lat_balance_medio, lat_dominanza, "
        "timp_vol_tollerato, timp_durata_sec, timp_note, "
        "joh_od, joh_os, joh_indice, joh_dominanza, joh_risposte_json, "
        f"note_cliniche, created_at) VALUES ({ph})"
    )
    try:
        cur.execute(sql, params)
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Errore salvataggio: {e}")
        return False


FREQS_AF    = [125, 250, 500, 750, 1000, 1500, 2000, 3000, 4000, 6000, 8000, 10500]
FLABELS_AF  = ['125','250','500','750','1k','1.5k','2k','3k','4k','6k','8k','10.5k']
FREQS_11    = FREQS_AF[:11]
FREQ_ORDER  = [10500,8000,6000,4000,3000,2000,1500,1000,750,500,250,125]
TOMATIS_STD = [-5,-8,-10,-12,-14,-15,-14,-15,-12,-8,-5]
JOHANSEN_TRACCE = [
    {"n":1,"desc":"Istruzioni","dur":"10s"},
    {"n":2,"desc":"Compito 1 — OD","dur":"69s"},
    {"n":3,"desc":"Compito 2 — OS","dur":"73s"},
    {"n":4,"desc":"Compito 3 — Risposte DX","dur":"75s"},
    {"n":5,"desc":"Compito 4 — Risposte SX","dur":"73s"},
    {"n":6,"desc":"Compito 5 — Entrambi","dur":"100s"},
]

def _tone_wav(freq_hz: int, db_hl: float, seconds: float = 2.5,
              sr: int = 44100) -> bytes:
    """
    Genera tono sinusoidale WAV mono 16-bit.
    db_hl: livello in dB HL (0 = soglia normale, 30 = 30 dB sopra soglia).
    Conversione dB HL → dBFS approssimata: dBFS = db_hl - 90
    """
    dbfs = db_hl - 90.0
    amp  = 10 ** (dbfs / 20.0)
    amp  = max(0.001, min(0.95, amp))

    t   = np.linspace(0, seconds, int(sr * seconds), endpoint=False)
    sig = amp * np.sin(2 * math.pi * freq_hz * t)

    # Fade in/out 20ms per evitare click
    fade = int(sr * 0.02)
    if len(sig) > 2 * fade:
        sig[:fade]  *= np.linspace(0, 1, fade)
        sig[-fade:] *= np.linspace(1, 0, fade)

    # Modulazione vibrato leggera (test modulato come Hiperion)
    vib = 1 + 0.03 * np.sin(2 * math.pi * 4 * t)
    sig *= vib

    pcm = np.int16(np.clip(sig, -1, 1) * 32767)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())
    return buf.getvalue()

# ─────────────────────────────────────────────────────────────────────────────
# DB helpers
# ─────────────────────────────────────────────────────────────────────────────

def _disegna_audiogramma(od, os, tom):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(9, 4), facecolor='white')
    ax.set_facecolor('white')

    # Griglia
    ax.set_xlim(-0.5, len(FREQS_11)-0.5)
    ax.set_ylim(90, -20)
    ax.set_xticks(range(len(FREQS_11)))
    ax.set_xticklabels([str(f) if f < 1000 else f"{f//1000}k" for f in FREQS_11],
                       fontsize=8)
    ax.set_yticks(range(-20, 91, 10))
    ax.set_ylabel("dB HL", fontsize=9)
    ax.set_xlabel("Frequenza (Hz)", fontsize=9)
    ax.axhline(0, color='gray', linewidth=0.8, linestyle='--', alpha=0.5)
    ax.grid(True, alpha=0.15, linewidth=0.5)
    ax.fill_between(range(len(FREQS_11)), -20, 0,
                    alpha=0.04, color='#2d7d6f', label='_')
    ax.text(0.01, 0.02, 'Iperudizione', transform=ax.transAxes,
            fontsize=7, color='#2d7d6f', alpha=0.7)

    # Curva Tomatis
    x_tom = list(range(len(tom)))
    ax.plot(x_tom, tom, color='#2d7d6f', linewidth=2,
            linestyle='--', label='Curva Tomatis', zorder=3)

    # OD
    od_pts = [(i, v) for i, v in enumerate(od[:11]) if v is not None]
    if od_pts:
        xi, yi = zip(*od_pts)
        ax.plot(xi, yi, color='#c0392b', linewidth=1.8,
                marker='o', markersize=7, label='OD', zorder=4)
        for x, y in od_pts:
            ax.text(x, y-4, 'O', ha='center', fontsize=9,
                    color='#c0392b', fontweight='bold')

    # OS
    os_pts = [(i, v) for i, v in enumerate(os[:11]) if v is not None]
    if os_pts:
        xi, yi = zip(*os_pts)
        ax.plot(xi, yi, color='#2980b9', linewidth=1.8,
                marker='x', markersize=7, label='OS', zorder=4)
        for x, y in os_pts:
            ax.text(x, y+5, 'X', ha='center', fontsize=9,
                    color='#2980b9', fontweight='bold')

    ax.legend(fontsize=8, loc='lower right')
    fig.tight_layout(pad=0.5)

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=110, bbox_inches='tight',
                facecolor='white')
    plt.close(fig)
    buf.seek(0)
    return buf

# ─────────────────────────────────────────────────────────────────────────────
# UI principale
# ─────────────────────────────────────────────────────────────────────────────

def _ui_test_tonale(conn, paz_id, operatore):
    # Session state
    ss = st.session_state
    if "af_od"   not in ss: ss.af_od   = [None] * 12
    if "af_os"   not in ss: ss.af_os   = [None] * 12
    if "af_tom"  not in ss: ss.af_tom  = list(TOMATIS_STD)
    if "af_ear"  not in ss: ss.af_ear  = "OD"
    if "af_fidx" not in ss: ss.af_fidx = 0   # parte da 10.5k (indice 11 in FREQ_ORDER)
    if "af_db"   not in ss: ss.af_db   = 30
    if "af_mode" not in ss: ss.af_mode = "Manuale"
    if "af_last_resp_db" not in ss: ss.af_last_resp_db = None
    if "af_sel"  not in ss: ss.af_sel  = {}
    if "af_lat"  not in ss: ss.af_lat  = {}

    # Frequenza corrente
    cur_f  = FREQS_AF[ss.af_fidx]
    cur_db = ss.af_db

    # ── Controlli in alto ────────────────────────────────────────────────
    col_ear, col_mode, col_reset = st.columns([2, 3, 1])

    with col_ear:
        st.markdown("**Orecchio**")
        ec1, ec2 = st.columns(2)
        if ec1.button("OD", type="primary" if ss.af_ear=="OD" else "secondary",
                      key="af_btn_od", use_container_width=True):
            ss.af_ear = "OD"; ss.af_db = 30; ss.af_last_resp_db = None
        if ec2.button("OS", type="primary" if ss.af_ear=="OS" else "secondary",
                      key="af_btn_os", use_container_width=True):
            ss.af_ear = "OS"; ss.af_db = 30; ss.af_last_resp_db = None

    with col_mode:
        st.markdown("**Modalità**")
        ss.af_mode = st.radio("", ["Manuale","Semi-auto","Automatico"],
                              horizontal=True, label_visibility="collapsed",
                              key="af_mode_radio")

    with col_reset:
        st.markdown("**Reset**")
        if st.button("🗑️", key="af_reset", help="Azzera tutte le soglie"):
            ss.af_od  = [None] * 12
            ss.af_os  = [None] * 12
            ss.af_db  = 30
            ss.af_last_resp_db = None
            st.rerun()

    st.divider()

    # ── Selezione frequenza ───────────────────────────────────────────────
    st.markdown("**Frequenza** (click per selezionare — ordine Hipérion: acuti → gravi)")
    freq_cols = st.columns(12)
    for i, (f, lbl) in enumerate(zip(FREQS, FLABELS)):
        od_done = ss.af_od[i] is not None
        os_done = ss.af_os[i] is not None
        tag = ""
        if od_done and os_done: tag = " ✓✓"
        elif od_done: tag = " O"
        elif os_done: tag = " X"
        is_cur = (i == ss.af_fidx)
        btn_lbl = f"**{lbl}{tag}**" if is_cur else f"{lbl}{tag}"
        if freq_cols[i].button(lbl + tag, key=f"af_fsel_{i}",
                               type="primary" if is_cur else "secondary",
                               use_container_width=True):
            ss.af_fidx = i
            ss.af_db   = 30
            ss.af_last_resp_db = None
            st.rerun()

    cur_f  = FREQS_AF[ss.af_fidx]
    cur_db = ss.af_db

    # ── Display livello corrente ──────────────────────────────────────────
    st.divider()
    mc1, mc2, mc3 = st.columns([2, 1, 2])

    with mc1:
        st.metric("Frequenza", f"{cur_f} Hz" if cur_f < 1000 else
                  f"{cur_f/1000:.1f} kHz")
        st.metric("Orecchio", ss.af_ear,
                  delta="Destro" if ss.af_ear=="OD" else "Sinistro")

    with mc2:
        # Barra dB
        pct = max(0, min(100, (cur_db + 20) / 110 * 100))
        color = "#2d7d6f" if cur_db < 20 else "#ba7517" if cur_db < 40 else "#e24b4a"
        st.markdown(f"""
        <div style="text-align:center;margin-top:8px">
          <div style="font-size:42px;font-weight:600;color:{color};line-height:1">
            {cur_db}
          </div>
          <div style="font-size:13px;color:#8a8a8a">dB HL</div>
          <div style="height:8px;background:#ede9e3;border-radius:4px;margin:6px 0;overflow:hidden">
            <div style="width:{pct}%;height:100%;background:{color};border-radius:4px"></div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    with mc3:
        last = ss.af_last_resp_db
        if last is not None:
            st.metric("Ultima risposta", f"{last} dB HL")
        cur_soglia = (ss.af_od[ss.af_fidx] if ss.af_ear=="OD"
                      else ss.af_os[ss.af_fidx])
        if cur_soglia is not None:
            st.metric("Soglia validata", f"{cur_soglia} dB HL",
                      delta="registrata ✓")

    # ── TONO ─────────────────────────────────────────────────────────────
    st.markdown("**Genera tono**")
    tc1, tc2, tc3 = st.columns([1, 2, 1])

    with tc1:
        dur = st.select_slider("Durata", options=[0.5, 1.0, 1.5, 2.0, 2.5, 3.0],
                               value=2.0, key="af_dur",
                               format_func=lambda x: f"{x}s")

    with tc2:
        if st.button("▶ Invia tono", type="primary", key="af_play",
                     use_container_width=True):
            wav = _tone_wav(cur_f, float(cur_db), float(dur))
            st.audio(wav, format="audio/wav", autoplay=True)
            if ss.af_mode == "Semi-auto":
                st.info(f"Tono {cur_f} Hz a {cur_db} dB HL — Il paziente risponde?")

    with tc3:
        st.caption(f"{'Vibrato ON' if True else ''}")

    # ── Regolazione dB ───────────────────────────────────────────────────
    st.markdown("**Regola livello dB HL**")
    db_cols = st.columns(6)
    for delta, lbl, col in zip([-10,-5,-1,1,5,10],
                               ["−10","−5","−1","+1","+5","+10"],
                               db_cols):
        if col.button(lbl, key=f"af_adj_{delta}", use_container_width=True):
            ss.af_db = max(-20, min(90, ss.af_db + delta))
            if ss.af_mode in ("Semi-auto","Automatico"):
                wav = _tone_wav(FREQS_AF[ss.af_fidx], float(ss.af_db), float(
                    st.session_state.get("af_dur", 2.0)))
                st.audio(wav, format="audio/wav", autoplay=True)
            st.rerun()

    # Slider dB
    new_db = st.slider("dB HL", -20, 90, cur_db, 5, key="af_db_slider",
                       label_visibility="collapsed")
    if new_db != cur_db:
        ss.af_db = new_db
        st.rerun()

    # ── Risposta paziente ─────────────────────────────────────────────────
    st.divider()
    st.markdown("**Risposta paziente**")
    rc1, rc2, rc3, rc4 = st.columns(4)

    with rc1:
        if st.button("✓ Risponde", key="af_resp_yes",
                     use_container_width=True):
            ss.af_last_resp_db = ss.af_db
            # Metodo Hipérion: se risponde a 30dB → vai a -20dB
            if ss.af_db == 30:
                ss.af_db = -20
            else:
                ss.af_db = max(-20, ss.af_db - 5)
            if ss.af_mode == "Automatico":
                wav = _tone_wav(FREQS_AF[ss.af_fidx], float(ss.af_db), 2.0)
                st.audio(wav, format="audio/wav", autoplay=True)
            st.rerun()

    with rc2:
        if st.button("✗ Non risponde", key="af_resp_no",
                     use_container_width=True):
            ss.af_db = min(90, ss.af_db + 5)
            if ss.af_db >= 50:
                st.warning("Perdita > 50 dB — frequenza non validata")
            if ss.af_mode == "Automatico":
                wav = _tone_wav(FREQS_AF[ss.af_fidx], float(ss.af_db), 2.0)
                st.audio(wav, format="audio/wav", autoplay=True)
            st.rerun()

    with rc3:
        val_disabled = ss.af_last_resp_db is None
        if st.button("✅ Valida soglia", key="af_val",
                     disabled=val_disabled, use_container_width=True,
                     type="primary"):
            db_val = ss.af_last_resp_db
            if ss.af_ear == "OD":
                ss.af_od[ss.af_fidx] = db_val
            else:
                ss.af_os[ss.af_fidx] = db_val
            ss.af_last_resp_db = None
            ss.af_db = 30
            # Avanza automaticamente alla frequenza successiva
            cur_f_now = FREQS_AF[ss.af_fidx]
            order_idx = FREQ_ORDER.index(cur_f_now) if cur_f_now in FREQ_ORDER else -1
            if order_idx >= 0 and order_idx < len(FREQ_ORDER) - 1:
                next_f = FREQ_ORDER[order_idx + 1]
                if next_f in FREQS:
                    ss.af_fidx = FREQS_AF.index(next_f)
            st.success(f"Soglia {cur_f_now} Hz = {db_val} dB HL registrata")
            st.rerun()

    with rc4:
        if st.button("→ Freq. successiva", key="af_next",
                     use_container_width=True):
            cur_f_now = FREQS_AF[ss.af_fidx]
            order_idx = FREQ_ORDER.index(cur_f_now) if cur_f_now in FREQ_ORDER else -1
            if order_idx >= 0 and order_idx < len(FREQ_ORDER) - 1:
                next_f = FREQ_ORDER[order_idx + 1]
                if next_f in FREQS:
                    ss.af_fidx = FREQS_AF.index(next_f)
                    ss.af_db = 30
                    ss.af_last_resp_db = None
            st.rerun()

    # Istruzioni modalità
    if ss.af_mode == "Manuale":
        st.caption("Manuale: invia il tono → il paziente risponde → aggiusta dB → valida soglia")
    elif ss.af_mode == "Semi-auto":
        st.caption("Semi-auto: premi Risponde/Non risponde → il tono riparte automaticamente al nuovo livello")
    else:
        st.caption("Automatico: premi Risponde/Non risponde → il livello si aggiusta e il tono riparte da solo")

    # ── Soglie registrate ─────────────────────────────────────────────────
    st.divider()
    st.markdown("**Soglie registrate**")
    sc1, sc2 = st.columns(2)
    with sc1:
        st.markdown("🔴 **OD — Orecchio destro**")
        for i, v in enumerate(ss.af_od):
            if v is not None:
                st.markdown(
                    f"<span style='background:#fdecea;border:1px solid #c0392b;"
                    f"border-radius:10px;padding:2px 8px;font-size:12px;"
                    f"color:#c0392b;margin:2px;display:inline-block'>"
                    f"{FLABELS_AF[i]}: {v} dB</span>",
                    unsafe_allow_html=True)
    with sc2:
        st.markdown("🔵 **OS — Orecchio sinistro**")
        for i, v in enumerate(ss.af_os):
            if v is not None:
                st.markdown(
                    f"<span style='background:#eaf4fb;border:1px solid #2980b9;"
                    f"border-radius:10px;padding:2px 8px;font-size:12px;"
                    f"color:#2980b9;margin:2px;display:inline-block'>"
                    f"{FLABELS_AF[i]}: {v} dB</span>",
                    unsafe_allow_html=True)

    # ── Grafico + EQ ──────────────────────────────────────────────────────
    if any(v is not None for v in ss.af_od + ss.af_os):
        st.divider()
        st.markdown("**Audiogramma + curva Tomatis**")

        with st.expander("Modifica curva Tomatis", expanded=False):
            tom_cols = st.columns(11)
            for i, (f, lbl) in enumerate(zip(FREQS_11, FLABELS_AF[:11])):
                new_v = tom_cols[i].number_input(
                    lbl, -30, 10, ss.af_tom[i], 1,
                    key=f"af_tom_{i}", label_visibility="visible")
                ss.af_tom[i] = new_v
            if st.button("Ripristina standard", key="af_tom_reset"):
                ss.af_tom = list(TOMATIS_STD)
                st.rerun()

        buf = _disegna_audiogramma(ss.af_od, ss.af_os, ss.af_tom)
        st.image(buf, use_container_width=True)

        # EQ
        st.markdown("**Delta EQ terapeutico** (Tomatis − soglia paziente)")
        eq_od = [round(ss.af_tom[i] - ss.af_od[i], 1)
                 if i < len(ss.af_od) and ss.af_od[i] is not None else None
                 for i in range(11)]
        eq_os = [round(ss.af_tom[i] - ss.af_os[i], 1)
                 if i < len(ss.af_os) and ss.af_os[i] is not None else None
                 for i in range(11)]

        eq_cols = st.columns(11)
        for i, (lbl, vod, vos) in enumerate(zip(FLABELS_AF[:11], eq_od, eq_os)):
            v = vod if vod is not None else vos
            if v is not None:
                color = "green" if v > 3 else "red" if v < -3 else "orange"
                eq_cols[i].markdown(
                    f"<div style='text-align:center'>"
                    f"<b style='color:{color};font-size:14px'>{v:+.0f}</b>"
                    f"<br><span style='font-size:9px;color:#888'>{lbl}</span></div>",
                    unsafe_allow_html=True)

        # Selettività
        st.divider()
        st.markdown("**Selettività uditiva**")
        sel_rows = ["LE BC", "LE AC", "RE BC", "RE AC"]
        opts_sel = ["", "O", "X", "OX"]
        for row in sel_rows:
            cols = st.columns([2] + [1]*11)
            cols[0].markdown(f"**{row}**")
            for i, lbl in enumerate(FLABELS_AF[:11]):
                key = f"af_sel_{row}_{i}"
                cur_v = ss.af_sel.get(f"{row}_{i}", "")
                idx = opts_sel.index(cur_v) if cur_v in opts_sel else 0
                v = cols[i+1].selectbox("", opts_sel, index=idx,
                                        key=key, label_visibility="collapsed")
                ss.af_sel[f"{row}_{i}"] = v

        # Lateralità
        st.divider()
        st.markdown("**Lateralità uditiva binaurale**")
        lat_rows = ["BPTA 20dB", "A soglia"]
        for row in lat_rows:
            cols = st.columns([2] + [1]*11)
            cols[0].markdown(f"**{row}**")
            for i, lbl in enumerate(FLABELS_AF[:11]):
                key = f"af_lat_{row}_{i}"
                cur_v = ss.af_lat.get(f"{row}_{i}", "")
                idx = opts_sel.index(cur_v) if cur_v in opts_sel else 0
                v = cols[i+1].selectbox("", opts_sel, index=idx,
                                        key=key, label_visibility="collapsed")
                ss.af_lat[f"{row}_{i}"] = v

        # Salvataggio
        st.divider()
        note = st.text_area("Note cliniche", key="af_note", height=80)
        if st.button("💾 Salva audiometria completa", type="primary",
                     key="af_save"):
            data = {
                "od":    ss.af_od[:11],
                "os":    ss.af_os[:11],
                "tom":   ss.af_tom,
                "eqOD":  [v if v is not None else 0 for v in eq_od],
                "eqOS":  [v if v is not None else 0 for v in eq_os],
                "sel":   dict(ss.af_sel),
                "lat":   dict(ss.af_lat),
                "note":  note,
            }
            conn = _get_conn()
            if _salva(conn, paz_id, data, operatore):
                st.success("✅ Audiometria salvata correttamente.")


# ─────────────────────────────────────────────────────────────────────────────
# Test dicotico Johansen
# ─────────────────────────────────────────────────────────────────────────────

def _ui_johansen_af(conn, cur, paz_id):
    st.subheader("Test dicotico di Johansen")
    st.caption(
        "Carica le 6 tracce MP3 stereo. "
        "Ogni traccia presenta sillabe diverse OD/OS simultaneamente."
    )

    if "joh_risposte" not in st.session_state:
        st.session_state.joh_risposte = {}

    with st.expander("▶ Carica e riproduci tracce", expanded=True):
        for info in JOHANSEN_TRACCE:
            n = info["n"]
            c1, c2 = st.columns([3, 1])
            with c1:
                f = st.file_uploader(
                    f"Traccia {n} — {info['desc']} ({info['dur']})",
                    type=["mp3","wav"], key=f"joh_t{n}")
            with c2:
                if f:
                    st.audio(f.getvalue(), format="audio/mp3")

    st.divider()
    st.markdown("**Registra le risposte del paziente** (Comp.3 = DX · Comp.4 = SX · Comp.5 = entrambi)")

    opts = ["", "OD", "OS", "Entrambi"]
    h = st.columns([0.4, 0.8, 0.8, 1.2, 1.2, 1.2])
    for lbl, col in zip(["#", "OD", "OS", "Comp.3 DX", "Comp.4 SX", "Comp.5 Both"], h):
        col.markdown(f"<div style='font-size:11px;font-weight:600;color:#8a8a8a'>{lbl}</div>",
                     unsafe_allow_html=True)

    for i, coppia in enumerate(JOHANSEN_COPPIE):
        c0,c1,c2,c3,c4,c5 = st.columns([0.4, 0.8, 0.8, 1.2, 1.2, 1.2])
        c0.markdown(f"<div style='font-size:11px;color:#8a8a8a;padding-top:8px'>{i+1}</div>",
                    unsafe_allow_html=True)
        c1.markdown(f"<div style='color:#c0392b;font-weight:600;font-size:13px;padding-top:6px'>{coppia['od']}</div>",
                    unsafe_allow_html=True)
        c2.markdown(f"<div style='color:#2980b9;font-weight:600;font-size:13px;padding-top:6px'>{coppia['os']}</div>",
                    unsafe_allow_html=True)
        r = st.session_state.joh_risposte.get(i, {})
        for comp, col in [("c3",c3),("c4",c4),("c5",c5)]:
            cur_v = r.get(comp, "")
            idx = opts.index(cur_v) if cur_v in opts else 0
            v = col.selectbox("", opts, index=idx,
                              key=f"jc_{comp}_{i}",
                              label_visibility="collapsed")
            if v:
                st.session_state.joh_risposte.setdefault(i, {})[comp] = v

    # Punteggi
    jod, jos = 0, 0
    for i, r in st.session_state.joh_risposte.items():
        if r.get("c3") == "OD": jod += 1
        if r.get("c4") == "OS": jos += 1
        if r.get("c5") in ["OD","Entrambi"]: jod += 1
        if r.get("c5") in ["OS","Entrambi"]: jos += 1

    tot = jod + jos
    idx = round((jod-jos)*100/tot, 1) if tot > 0 else 0
    dom = "OD dominante" if idx > 10 else "OS dominante" if idx < -10 else "Bilanciato"

    st.divider()
    m1,m2,m3 = st.columns(3)
    m1.metric("Punteggio OD", jod)
    m2.metric("Punteggio OS", jos)
    m3.metric("Indice lateralità", f"{idx:+.1f}" if tot > 0 else "—")
    if tot > 0:
        color = "#c0392b" if idx > 10 else "#2980b9" if idx < -10 else "#2d7d6f"
        st.markdown(
            f"<div style='padding:8px 12px;background:#f8f7f4;border-radius:8px;"
            f"border-left:4px solid {color};font-size:13px'>"
            f"<b style='color:{color}'>{dom}</b> (indice {idx:+.1f}/100)</div>",
            unsafe_allow_html=True)

    if st.button("💾 Salva test Johansen", type="primary", key="joh_save"):
        data = {"joh": {"od": jod, "os": jos,
                        "ans": {str(k): v for k, v in
                                st.session_state.joh_risposte.items()}}}
        if _salva(conn, paz_id, data, ""):
            st.success(f"Test Johansen salvato: OD={jod} OS={jos} Indice={idx:+.1f}")


# ─────────────────────────────────────────────────────────────────────────────
# Storico
# ─────────────────────────────────────────────────────────────────────────────

def _ui_storico_audio(conn, cur, paz_id):
    ph1 = _ph(1, conn)
    try:
        cur.execute(
            "SELECT * FROM audiometrie_funzionali WHERE paziente_id = " + ph1 +
            " ORDER BY data_esame DESC, id DESC LIMIT 20", (paz_id,))
        rows = cur.fetchall()
    except Exception as e:
        st.error(f"Errore storico: {e}"); return

    if not rows:
        st.info("Nessuna audiometria registrata per questo paziente."); return

    # Trend EQ
    eq_trend = []
    for r in rows:
        d = _rg(r, "data_esame", "")
        try:
            eq = json.loads(_rg(r, "eq_od_json", "[]") or "[]")
            if eq and any(eq):
                eq_trend.append({"Data": d, "Delta EQ medio OD":
                                 round(sum(eq)/len(eq), 1)})
        except Exception: pass

    if eq_trend:
        st.markdown("**Andamento delta EQ nel tempo (OD)**")
        st.line_chart(pd.DataFrame(eq_trend).sort_values("Data").set_index("Data"))

    for r in rows:
        eid    = _rg(r, "id")
        data_e = _rg(r, "data_esame", "")
        jdom   = _rg(r, "joh_dominanza", "—")
        jidx   = _rg(r, "joh_indice")

        with st.expander(f"#{eid} | {data_e} | Johansen: {jdom}"):
            try:
                od  = json.loads(_rg(r, "od_json",     "[]") or "[]")
                os_ = json.loads(_rg(r, "os_json",     "[]") or "[]")
                eq  = json.loads(_rg(r, "eq_od_json",  "[]") or "[]")
                tom = json.loads(_rg(r, "tomatis_json","[]") or "[]")
            except Exception:
                od, os_, eq, tom = [], [], [], []

            if od and any(v is not None for v in od):
                buf = _disegna_audiogramma(od, os_, tom or TOMATIS_STD)
                st.image(buf, use_container_width=True)

            if eq and any(eq):
                st.markdown("**EQ terapeutico OD:**")
                ecols = st.columns(11)
                for i, (c, v) in enumerate(zip(ecols, eq)):
                    if v:
                        col = "green" if v > 3 else "red" if v < -3 else "orange"
                        c.markdown(
                            f"<div style='text-align:center'>"
                            f"<b style='color:{col};font-size:13px'>{v:+.0f}</b>"
                            f"<br><span style='font-size:9px;color:#888'>{FLABELS[i]}</span></div>",
                            unsafe_allow_html=True)

            jod = _rg(r, "joh_od")
            jos = _rg(r, "joh_os")
            if jod is not None:
                m1,m2,m3 = st.columns(3)
                m1.metric("Johansen OD", jod)
                m2.metric("Johansen OS", jos)
                m3.metric("Indice", f"{jidx:+.1f}" if jidx else "—")

def ui_bilancio_uditivo():
    try:
        from modules.ui_calibrazione_cuffie import ui_calibrazione_cuffie, ui_fonometro_wizard
        _has_calib = True
    except Exception:
        _has_calib = False

    st.header("Bilancio Uditivo")
    st.caption("Lateralita uditiva · Elasticita timpano · Test dicotico Johansen — Metodo Tomatis/Hiperion")

    conn = _get_conn()
    _init_db(conn)
    cur = conn.cursor()

    try:
        cur.execute('SELECT id, "Cognome", "Nome" FROM "Pazienti" ORDER BY "Cognome", "Nome"')
        pazienti = cur.fetchall()
    except Exception:
        try:
            cur.execute("SELECT id, Cognome, Nome FROM Pazienti ORDER BY Cognome, Nome")
            pazienti = cur.fetchall()
        except Exception as e:
            st.error(f"Errore pazienti: {e}"); return

    if not pazienti:
        st.info("Nessun paziente registrato."); return

    opts = [f"{_row_get(p,'id')} - {_row_get(p,'Cognome','')} {_row_get(p,'Nome','')}".strip()
            for p in pazienti]
    sel = st.selectbox("Paziente", opts, key="bu_paz")
    paz_id = int(sel.split(" - ", 1)[0])
    op = st.text_input("Operatore", "", key="bu_op")
    st.divider()

    result = components.html(_html_bilancio(paz_id), height=720, scrolling=True)

    if result:
        try:
            data = json.loads(result) if isinstance(result, str) else result
            if data and data.get("paz_id"):
                if _salva_bilancio(conn, paz_id, data, op):
                    st.success("Bilancio uditivo salvato correttamente.")
                    st.rerun()
        except Exception:
            pass

    st.divider()
    with st.expander("Storico bilanci uditivi", expanded=False):
        _ui_storico_audio(conn, cur, paz_id)

    st.divider()

    with st.expander("🔧 Calibrazione cuffie con fonometro", expanded=False):
        if _has_calib:
            tab_fon, tab_classic = st.tabs(["Fonometro wizard", "Wizard classico + profili"])
            with tab_fon:
                ui_fonometro_wizard()
            with tab_classic:
                ui_calibrazione_cuffie(conn)
        else:
            st.info("Modulo calibrazione non disponibile.")

    st.divider()
    st.markdown("### Test Tonale + Johansen")
    tab_tonal, tab_joh_new, tab_storico = st.tabs([
        "🎵 Test Tonale + EQ", "📋 Test Johansen", "📈 Storico"
    ])
    with tab_tonal:
        _ui_test_tonale(conn, paz_id, op)
    with tab_joh_new:
        _ui_johansen_af(conn, conn.cursor(), paz_id)
    with tab_storico:
        _ui_storico_audio(conn, conn.cursor(), paz_id)
