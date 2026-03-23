# -*- coding: utf-8 -*-
"""
Modulo: Audiometria Funzionale + Test Dicotico Johansen
Gestionale The Organism — PNEV

Funzionalita:
  - Audiogramma funzionale con inserimento soglie dB HL (11 frequenze OD/OS)
  - Grafico audiogramma + curva Tomatis sovrapposta
  - Calcolo automatico delta dB → parametri EQ terapeutici
  - Tabella selettivita (LE BC, LE AC, RE BC, RE AC)
  - Lateralita uditiva binaurale (BPTA 20dB + a soglia)
  - Test dicotico Johansen con riproduzione tracce MP3 stereo (6 tracce)
  - Salvataggio DB: tabella audiometrie_funzionali

Curva Tomatis standard (dB HL target per frequenza):
  125: -5  250: -8  500: -10  750: -12  1k: -14
  1.5k: -15  2k: -14  3k: -15  4k: -12  6k: -8  8k: -5
  (picco a 3kHz, attenuazione progressiva verso gravi e acuti)
"""

import json
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from datetime import date, datetime

FREQS = [125, 250, 500, 750, 1000, 1500, 2000, 3000, 4000, 6000, 8000]
TOMATIS_STD = [-5, -8, -10, -12, -14, -15, -14, -15, -12, -8, -5]

JOHANSEN_COPPIE = [
    {"od":"DAT","os":"SOT"},{"od":"MYL","os":"GIF"},{"od":"NIK","os":"VEF"},
    {"od":"GIF","os":"KIT"},{"od":"FAK","os":"BAT"},{"od":"NUR","os":"NIK"},
    {"od":"SOT","os":"VYF"},{"od":"GEP","os":"RIS"},{"od":"VYF","os":"MYL"},
    {"od":"POS","os":"LIR"},{"od":"BOT","os":"TIK"},{"od":"VEF","os":"FAK"},
    {"od":"KIR","os":"DAT"},{"od":"KIT","os":"NUR"},{"od":"TIK","os":"BOT"},
    {"od":"LYM","os":"LYM"},{"od":"TOS","os":"HUT"},{"od":"BAT","os":"GEP"},
    {"od":"RIS","os":"POS"},{"od":"HUT","os":"TOS"},
]

JOHANSEN_INFO = [
    {"traccia": 1, "desc": "Istruzioni", "durata": "10s"},
    {"traccia": 2, "desc": "Compito 1 — OD (risposta a destra)", "durata": "69s"},
    {"traccia": 3, "desc": "Compito 2 — OS (risposta a sinistra)", "durata": "73s"},
    {"traccia": 4, "desc": "Compito 3 — Risposte a DX", "durata": "75s"},
    {"traccia": 5, "desc": "Compito 4 — Risposte a SX", "durata": "73s"},
    {"traccia": 6, "desc": "Compito 5 — Risposte su entrambi", "durata": "100s"},
]

_HTML_AUDIOGRAMMA = r"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
*{box-sizing:border-box;margin:0;padding:0;font-family:system-ui,sans-serif}
body{padding:10px;background:#f8f7f4;color:#1a1a1a}
.tabs{display:flex;border-bottom:2px solid #d4cec5;margin-bottom:12px}
.tab{padding:7px 13px;font-size:12px;cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-2px;color:#8a8a8a}
.tab.active{color:#2d7d6f;font-weight:600;border-bottom-color:#2d7d6f}
.section{display:none}.section.active{display:block}
.card{background:#fff;border:1px solid #d4cec5;border-radius:10px;padding:12px 16px;margin-bottom:10px}
h3{font-size:13px;font-weight:500;margin-bottom:3px}
.cap{font-size:11px;color:#8a8a8a;margin-bottom:8px;line-height:1.4}
button{font-family:inherit;font-size:12px;padding:6px 12px;border-radius:7px;border:1.5px solid #d4cec5;background:#fff;color:#4a4a4a;cursor:pointer;margin:2px;transition:all .15s}
button:hover{background:#e8f3f1;border-color:#2d7d6f;color:#1a5248}
button.primary{background:#2d7d6f;border-color:#2d7d6f;color:#fff}
button.primary:hover{background:#1a5248}
button.danger{border-color:#e24b4a;color:#e24b4a}
button.danger:hover{background:#fdecea}
button.od-btn{border-color:#c0392b;color:#c0392b}
button.od-btn.active{background:#c0392b;color:#fff}
button.os-btn{border-color:#2980b9;color:#2980b9}
button.os-btn.active{background:#2980b9;color:#fff}
button:disabled{opacity:.35;cursor:not-allowed}
canvas{display:block;width:100%;border-radius:6px}
.legend{display:flex;gap:14px;flex-wrap:wrap;margin:6px 0;font-size:10px;color:#8a8a8a}
.leg{display:flex;align-items:center;gap:4px}
.ll{width:20px;height:2px;border-radius:1px}
.fchips{display:flex;flex-wrap:wrap;gap:4px;margin:8px 0}
.fchip{padding:4px 10px;border-radius:12px;font-size:11px;border:1px solid #d4cec5;cursor:pointer;background:#f8f7f4;color:#4a4a4a;transition:all .15s}
.fchip.active{background:#2d7d6f;border-color:#2d7d6f;color:#fff;font-weight:600}
.fchip.done-od{background:#fdecea;border-color:#c0392b;color:#c0392b}
.fchip.done-os{background:#eaf4fb;border-color:#2980b9;color:#2980b9}
.fchip.done-both{background:#e8f3f1;border-color:#2d7d6f;color:#1a5248}
.db-display{font-size:36px;font-weight:500;color:#1a1a1a;text-align:center;padding:10px 0;letter-spacing:-1px}
.db-display span{font-size:16px;color:#8a8a8a;margin-left:4px}
.db-bar{height:10px;background:#ede9e3;border-radius:5px;margin:6px 0;overflow:hidden}
.db-fill{height:100%;border-radius:5px;transition:width .2s,background .2s}
.resp-area{display:flex;gap:6px;align-items:center;justify-content:center;margin:10px 0;flex-wrap:wrap}
.status{font-size:12px;padding:6px 10px;border-radius:6px;margin:6px 0}
.ok{background:#e8f3f1;color:#1a5248}
.warn{background:#fef7ec;color:#7a4f0a}
.info{background:#ebf5fb;color:#154360}
.err{background:#fdecea;color:#7a1a1a}
.tvis{display:flex;align-items:flex-end;gap:2px;height:24px;margin:0 6px}
.tb{width:4px;border-radius:2px 2px 0 0;background:#2d7d6f;animation:wv .5s ease-in-out infinite}
.tb:nth-child(2){animation-delay:.1s}.tb:nth-child(3){animation-delay:.2s}.tb:nth-child(4){animation-delay:.3s}
@keyframes wv{0%,100%{height:4px}50%{height:20px}}
.mode-btn{padding:5px 10px;border-radius:6px;border:1px solid #d4cec5;background:#f8f7f4;color:#8a8a8a;cursor:pointer;font-size:11px;transition:all .15s}
.mode-btn.active{background:#2d7d6f;border-color:#2d7d6f;color:#fff}
.prog{height:4px;background:#ede9e3;border-radius:2px;margin:6px 0}
.prog-fill{height:100%;border-radius:2px;background:#2d7d6f;transition:width .3s}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.metric{background:#f8f7f4;border-radius:6px;padding:7px 10px}
.metric .v{font-size:16px;font-weight:500}.metric .l{font-size:10px;color:#8a8a8a;margin-top:1px}
.eq-grid{display:flex;gap:5px;justify-content:center;flex-wrap:wrap;margin:6px 0}
.eq-bar{display:flex;flex-direction:column;align-items:center;gap:2px}
.eq-track{width:16px;height:60px;background:#ede9e3;border-radius:3px;position:relative;overflow:hidden}
.eq-fill{position:absolute;width:100%;border-radius:2px}
.eq-val{font-size:10px;font-weight:500}.eq-lbl{font-size:9px;color:#8a8a8a}
.sel-table{width:100%;border-collapse:collapse;font-size:11px}
.sel-table th{background:#f0ede8;padding:4px 5px;text-align:center;font-weight:500;font-size:10px}
.sel-table td{padding:2px 3px;text-align:center;border:0.5px solid #d4cec5}
.sel-table td:first-child{text-align:left;font-weight:500;background:#f8f7f4;padding:4px 8px;white-space:nowrap}
select.sel{font-size:11px;padding:1px 2px;border-radius:3px;border:1px solid #d4cec5;background:#fff;color:#1a1a1a;width:40px}
.tom-grid{display:grid;grid-template-columns:repeat(11,1fr);gap:3px;margin:5px 0}
.tg{display:flex;flex-direction:column;align-items:center;gap:2px}
.tg label{font-size:9px;color:#8a8a8a}
.tg input{width:100%;padding:2px;border-radius:3px;border:1px solid #2d7d6f;font-size:11px;text-align:center;color:#2d7d6f;background:#fff}
</style></head><body>

<div class="tabs">
  <div class="tab active" onclick="sw(0)">Test tonale</div>
  <div class="tab" onclick="sw(1)">Grafico + EQ</div>
  <div class="tab" onclick="sw(2)">Selettivita</div>
  <div class="tab" onclick="sw(3)">Lateralita</div>
</div>

<!-- TAB 0: TEST TONALE CON GENERAZIONE SUONI -->
<div class="section active" id="t0">

<div class="card">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
    <div>
      <h3>Test tonale liminare</h3>
      <p class="cap">Determina il suono piu debole udito per ogni frequenza. Start 30 dB → discesa a -20 dB → risalita per soglia.</p>
    </div>
    <div style="display:flex;gap:4px;align-items:center">
      <button class="od-btn active" id="bOD" onclick="setEar('OD')">OD</button>
      <button class="os-btn" id="bOS" onclick="setEar('OS')">OS</button>
    </div>
  </div>

  <!-- Modalita -->
  <div style="display:flex;gap:4px;margin-bottom:8px;flex-wrap:wrap">
    <span style="font-size:11px;color:#8a8a8a;padding-top:4px">Modalita:</span>
    <button class="mode-btn active" id="mMan" onclick="setMode('manual')">Manuale</button>
    <button class="mode-btn" id="mSemi" onclick="setMode('semi')">Semi-auto</button>
    <button class="mode-btn" id="mAuto" onclick="setMode('auto')">Automatico</button>
  </div>

  <!-- Frequenze -->
  <div style="font-size:11px;color:#8a8a8a;margin-bottom:4px">Frequenze (click per selezionare):</div>
  <div class="fchips" id="fchips"></div>

  <!-- Display dB corrente -->
  <div style="display:flex;align-items:center;justify-content:space-between;margin:8px 0">
    <div style="flex:1">
      <div style="font-size:11px;color:#8a8a8a;margin-bottom:2px">Livello corrente</div>
      <div class="db-display" id="dbDisp">30<span>dB HL</span></div>
      <div class="db-bar">
        <div class="db-fill" id="dbFill" style="width:45%;background:#2d7d6f"></div>
      </div>
    </div>
    <div style="width:120px;text-align:center">
      <div style="font-size:11px;color:#8a8a8a;margin-bottom:4px">Frequenza</div>
      <div style="font-size:22px;font-weight:500;color:#2d7d6f" id="freqDisp">10.5k</div>
      <div style="font-size:10px;color:#8a8a8a">Hz</div>
      <div class="tvis" id="tVis" style="display:none;justify-content:center">
        <div class="tb"></div><div class="tb"></div><div class="tb"></div><div class="tb"></div>
      </div>
    </div>
  </div>

  <!-- Controlli manuale / semi -->
  <div id="ctrlManual">
    <div class="resp-area">
      <button onclick="adjDb(-5)" id="bM5">−5 dB</button>
      <button onclick="adjDb(-1)" id="bM1">−1 dB</button>
      <button class="primary" onclick="sendTone()" id="bSend">▶ Invia tono</button>
      <button onclick="adjDb(1)" id="bP1">+1 dB</button>
      <button onclick="adjDb(5)" id="bP5">+5 dB</button>
    </div>
    <div class="resp-area">
      <button onclick="markResp(true)" style="border-color:#1d9e75;color:#1d9e75;font-size:13px;padding:8px 20px" id="bResp">✓ Paziente risponde</button>
      <button onclick="markResp(false)" style="border-color:#e24b4a;color:#e24b4a;font-size:13px;padding:8px 20px" id="bNoResp">✗ No risposta</button>
      <button onclick="validateSoglia()" class="primary" id="bVal" style="font-size:13px;padding:8px 20px" disabled>Valida soglia</button>
    </div>
  </div>

  <!-- Controlli automatico -->
  <div id="ctrlAuto" style="display:none">
    <div class="resp-area">
      <button class="primary" onclick="startAuto()" id="bAutoStart">▶ Avvia automatico</button>
      <button onclick="stopAuto()" id="bAutoStop" disabled>■ Stop</button>
      <div class="tvis" id="tVisAuto" style="display:none;justify-content:center">
        <div class="tb"></div><div class="tb"></div><div class="tb"></div><div class="tb"></div>
      </div>
    </div>
    <div id="autoInfo" class="status info">Premi Avvia per la sequenza automatica (da acuti a gravi).</div>
    <div class="prog"><div class="prog-fill" id="progFill" style="width:0%"></div></div>
  </div>

  <div id="testStatus" class="status info">Seleziona orecchio e frequenza, poi invia il tono.</div>
</div>

<!-- Soglie registrate -->
<div class="card">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
    <h3>Soglie registrate</h3>
    <button class="danger" onclick="resetSoglie()" style="font-size:10px">Reset</button>
  </div>
  <div class="grid2">
    <div>
      <div style="font-size:10px;color:#c0392b;font-weight:600;margin-bottom:4px">OD — Orecchio destro</div>
      <div id="sogOD" style="display:flex;flex-wrap:wrap;gap:4px"></div>
    </div>
    <div>
      <div style="font-size:10px;color:#2980b9;font-weight:600;margin-bottom:4px">OS — Orecchio sinistro</div>
      <div id="sogOS" style="display:flex;flex-wrap:wrap;gap:4px"></div>
    </div>
  </div>
</div>

</div>

<!-- TAB 1: GRAFICO + EQ -->
<div class="section" id="t1">
<div class="card">
  <h3>Audiogramma + curva Tomatis</h3>
  <p class="cap">O = OD (rosso) &nbsp; X = OS (blu) &nbsp; Verde tratteggiato = target Tomatis</p>
  <canvas id="cvA" height="280"></canvas>
  <div class="legend">
    <div class="leg"><div class="ll" style="background:#c0392b"></div>OD</div>
    <div class="leg"><div class="ll" style="background:#2980b9"></div>OS</div>
    <div class="leg"><div class="ll" style="background:#2d7d6f;border-top:2px dashed #2d7d6f;height:0"></div>Curva Tomatis</div>
  </div>
</div>
<div class="card">
  <h3>Curva Tomatis (modificabile per paziente)</h3>
  <p class="cap">Default: curva standard. Modifica per personalizzare il target terapeutico.</p>
  <div class="tom-grid" id="tomGrid"></div>
  <button onclick="resetTom()" style="margin-top:5px;font-size:10px">Ripristina standard</button>
</div>
<div class="card">
  <h3>Delta EQ — parametri terapeutici generati</h3>
  <p class="cap">Curva Tomatis − soglia paziente. Positivo = rinforzo (ipouduzione). Negativo = attenuazione (iperudizione).</p>
  <div class="eq-grid" id="eqGrid"></div>
  <div class="grid2" style="margin-top:8px">
    <div class="metric"><div class="v" id="eqNote">-</div><div class="l">Indicazione</div></div>
    <div class="metric"><div class="v" id="eqDom">-</div><div class="l">Frequenza critica</div></div>
  </div>
</div>
</div>

<!-- TAB 2: SELETTIVITA -->
<div class="section" id="t2">
<div class="card">
  <h3>Selettivita uditiva</h3>
  <p class="cap">BC = via ossea &nbsp; AC = via aerea &nbsp; O = ODX &nbsp; X = OSN &nbsp; OX = Entrambi</p>
  <table class="sel-table">
    <thead><tr><th></th><th>125</th><th>250</th><th>500</th><th>750</th><th>1k</th><th>1.5k</th><th>2k</th><th>3k</th><th>4k</th><th>6k</th><th>8k</th></tr></thead>
    <tbody id="selBody"></tbody>
  </table>
</div>
</div>

<!-- TAB 3: LATERALITA -->
<div class="section" id="t3">
<div class="card">
  <h3>Lateralita uditiva binaurale</h3>
  <p class="cap">BPTA a 20 dB e a soglia &nbsp; O = ODX &nbsp; X = OSN &nbsp; OX = Entrambi</p>
  <table class="sel-table">
    <thead><tr><th></th><th>125</th><th>250</th><th>500</th><th>750</th><th>1k</th><th>1.5k</th><th>2k</th><th>3k</th><th>4k</th><th>6k</th><th>8k</th></tr></thead>
    <tbody id="latBody"></tbody>
  </table>
</div>
<div class="card" style="margin-top:8px">
  <div class="grid2">
    <div class="metric"><div class="v" id="latDom">-</div><div class="l">Orecchio dominante</div></div>
    <div class="metric"><div class="v" id="latIdx">-</div><div class="l">Indice lateralita</div></div>
  </div>
</div>
<div style="margin-top:10px">
  <button class="primary" onclick="saveAll()" style="width:100%;padding:10px;font-size:13px">Salva audiometria completa</button>
  <div id="saved" class="status ok" style="display:none;margin-top:6px">Audiometria salvata.</div>
</div>
</div>

<script>
const FR=[125,250,500,750,1000,1500,2000,3000,4000,6000,8000];
const FL=['125','250','500','750','1k','1.5k','2k','3k','4k','6k','8k'];
const TOM_STD=[-5,-8,-10,-12,-14,-15,-14,-15,-12,-8,-5];
// Ordine test Hiperion: da acuti a gravi
const FR_ORDER=[10500,8000,6000,4000,3000,2000,1500,1000,750,500,250,125];
const FR_ALL=[125,250,500,750,1000,1500,2000,3000,4000,6000,8000,10500];
const FL_ALL=['125','250','500','750','1k','1.5k','2k','3k','4k','6k','8k','10.5k'];

let tom=[...TOM_STD];
let od=new Array(12).fill(null); // 12 frequenze inclusa 10.5k
let os=new Array(12).fill(null);
let ear='OD';
let curFIdx=11; // parte da 10.5k (indice 11)
let curDb=30;
let mode='manual';
let toneActive=false;
let autoRunning=false;
let autoTimer=null;
let autoPhase='send'; // send|wait|validate
let autoRespPending=false;
let lastRespDb=null;
let confirmed={}; // {ear_fidx: db}
let respHistory=[]; // per il metodo soglia

let actx=null;
let toneNodes=[];

function getCtx(){
  if(!actx)actx=new(window.AudioContext||window.webkitAudioContext)();
  if(actx.state==='suspended')actx.resume();
  return actx;
}

function freqAtIdx(i){ return FR_ALL[i]; }
function idxOfFreq(f){ return FR_ALL.indexOf(f); }

// ── Chips frequenze ──────────────────────────────────────────────────────
function buildChips(){
  const c=document.getElementById('fchips'); c.innerHTML='';
  FR_ALL.forEach((f,i)=>{
    const d=document.createElement('div');
    d.className='fchip'+(i===curFIdx?' active':'');
    const odDone=od[i]!==null, osDone=os[i]!==null;
    if(odDone&&osDone) d.classList.add('done-both');
    else if(odDone) d.classList.add('done-od');
    else if(osDone) d.classList.add('done-os');
    d.textContent=FL_ALL[i]+(odDone||osDone?' ✓':'');
    d.onclick=()=>{ curFIdx=i; curDb=30; buildChips(); updDbDisp(); stopTones();
      document.getElementById('freqDisp').textContent=FL_ALL[i];
      document.getElementById('bVal').disabled=true; respHistory=[];
      document.getElementById('testStatus').textContent='Frequenza '+FL_ALL[i]+' Hz selezionata. Invia tono a 30 dB.';
      document.getElementById('testStatus').className='status info';
    };
    c.appendChild(d);
  });
  document.getElementById('freqDisp').textContent=FL_ALL[curFIdx];
}

// ── Display dB ───────────────────────────────────────────────────────────
function updDbDisp(){
  document.getElementById('dbDisp').innerHTML=curDb+'<span> dB HL</span>';
  const pct=Math.max(0,Math.min(100,(curDb+20)/110*100));
  const fill=document.getElementById('dbFill');
  fill.style.width=pct+'%';
  fill.style.background=curDb<0?'#2980b9':curDb<20?'#1d9e75':curDb<40?'#ba7517':'#e24b4a';
}

function adjDb(d){
  curDb=Math.max(-20,Math.min(90,curDb+d));
  updDbDisp();
  if(mode==='manual') sendTone();
}

// ── Generazione tono ─────────────────────────────────────────────────────
function stopTones(){
  toneNodes.forEach(n=>{try{n.stop();}catch(e){}});
  toneNodes=[];
  toneActive=false;
  document.getElementById('tVis').style.display='none';
}

function sendTone(dur=2.5){
  stopTones();
  const ctx=getCtx();
  const f=FR_ALL[curFIdx];
  const osc=ctx.createOscillator();
  const gain=ctx.createGain();
  const amp=Math.pow(10,(curDb-90)/20)*0.8;
  osc.frequency.value=f; osc.type='sine';

  // Fade in/out per evitare click
  gain.gain.setValueAtTime(0,ctx.currentTime);
  gain.gain.linearRampToValueAtTime(amp,ctx.currentTime+0.05);
  gain.gain.setValueAtTime(amp,ctx.currentTime+dur-0.1);
  gain.gain.linearRampToValueAtTime(0,ctx.currentTime+dur);

  osc.connect(gain); gain.connect(ctx.destination);
  osc.start(); osc.stop(ctx.currentTime+dur);
  toneNodes=[osc];
  toneActive=true;

  document.getElementById('tVis').style.display='flex';
  document.getElementById('testStatus').textContent='Tono '+f+' Hz a '+curDb+' dB HL ('+dur.toFixed(1)+'s)';
  document.getElementById('testStatus').className='status ok';

  setTimeout(()=>{
    document.getElementById('tVis').style.display='none';
    toneActive=false;
    if(mode==='semi'){
      document.getElementById('testStatus').textContent='Il paziente ha risposto? Premi il tasto corretto.';
      document.getElementById('testStatus').className='status warn';
    }
  }, dur*1000);
}

// ── Risposta paziente ────────────────────────────────────────────────────
function markResp(resp){
  stopTones();
  respHistory.push({db:curDb, resp:resp});

  if(resp){
    lastRespDb=curDb;
    // Ha risposto: scende ancora per cercare la soglia minima
    if(curDb>-20){
      // Prima risposta: vai a -20 dB
      if(respHistory.filter(h=>h.resp).length===1 && curDb===30){
        curDb=-20; updDbDisp();
        document.getElementById('bVal').disabled=false;
        document.getElementById('testStatus').textContent='Risponde a 30 dB → scendo a -20 dB. Invia tono.';
        document.getElementById('testStatus').className='status ok';
      } else {
        adjDb(-5);
        document.getElementById('testStatus').textContent='Risponde — scendo di 5 dB. Invia tono.';
        document.getElementById('testStatus').className='status ok';
      }
    } else {
      document.getElementById('bVal').disabled=false;
      document.getElementById('testStatus').textContent='Risponde a '+curDb+' dB. Premi Valida soglia.';
      document.getElementById('testStatus').className='status ok';
    }
  } else {
    // Non risponde: sali di 5 dB
    if(curDb<90){
      adjDb(5);
      document.getElementById('testStatus').textContent='No risposta — salgo di 5 dB. Invia tono.';
      document.getElementById('testStatus').className='status warn';
    }
    if(curDb>=50){
      document.getElementById('testStatus').textContent='No risposta a 50+ dB. Frequenza non validata (grigio).';
      document.getElementById('testStatus').className='status err';
    }
  }
  if(mode==='semi') setTimeout(()=>sendTone(), 600);
}

function validateSoglia(){
  const i=curFIdx;
  const db=lastRespDb!==null?lastRespDb:curDb;
  if(ear==='OD') od[i]=db; else os[i]=db;
  confirmed[ear+'_'+i]=db;
  document.getElementById('bVal').disabled=true;
  lastRespDb=null; respHistory=[];
  document.getElementById('testStatus').textContent='Soglia validata: '+FR_ALL[i]+' Hz = '+db+' dB HL';
  document.getElementById('testStatus').className='status ok';
  buildChips();
  buildSoglie();
  // Avanza alla frequenza successiva nell'ordine Hiperion
  autoAdvance();
}

function autoAdvance(){
  const order=FR_ORDER;
  const curF=FR_ALL[curFIdx];
  const idx=order.indexOf(curF);
  if(idx<order.length-1){
    const nextF=order[idx+1];
    const nextIdx=FR_ALL.indexOf(nextF);
    if(nextIdx>=0){
      setTimeout(()=>{
        curFIdx=nextIdx; curDb=30; buildChips(); updDbDisp();
        document.getElementById('freqDisp').textContent=FL_ALL[nextIdx];
        if(mode==='auto'||mode==='semi') sendTone();
      }, mode==='auto'?800:0);
    }
  }
}

// ── Modo automatico ──────────────────────────────────────────────────────
function setMode(m){
  mode=m;
  ['manual','semi','auto'].forEach(x=>{
    document.getElementById('m'+x.charAt(0).toUpperCase()+x.slice(1)).classList.toggle('active',x===m);
  });
  document.getElementById('ctrlManual').style.display=(m==='auto')?'none':'block';
  document.getElementById('ctrlAuto').style.display=(m==='auto')?'block':'none';
}

let autoFOrder=[]; let autoFIdx=0; let autoNResp=0;

function startAuto(){
  autoFOrder=[...FR_ORDER].filter(f=>FR_ALL.includes(f));
  autoFIdx=0; autoNResp=0;
  document.getElementById('bAutoStart').disabled=true;
  document.getElementById('bAutoStop').disabled=false;
  autoRunning=true;
  autoNext();
}

function stopAuto(){
  autoRunning=false;
  if(autoTimer)clearTimeout(autoTimer);
  document.getElementById('bAutoStart').disabled=false;
  document.getElementById('bAutoStop').disabled=true;
  document.getElementById('tVisAuto').style.display='none';
  document.getElementById('autoInfo').textContent='Test automatico interrotto.';
  document.getElementById('autoInfo').className='status warn';
}

function autoNext(){
  if(!autoRunning||autoFIdx>=autoFOrder.length){
    document.getElementById('autoInfo').textContent='Test automatico completato.';
    document.getElementById('autoInfo').className='status ok';
    document.getElementById('bAutoStart').disabled=false;
    document.getElementById('bAutoStop').disabled=true;
    buildChips();
    return;
  }
  const f=autoFOrder[autoFIdx];
  const fi=FR_ALL.indexOf(f);
  curFIdx=fi; curDb=30; respHistory=[];
  buildChips(); updDbDisp();
  document.getElementById('freqDisp').textContent=FL_ALL[fi];
  const pct=Math.round(autoFIdx/autoFOrder.length*100);
  document.getElementById('progFill').style.width=pct+'%';
  document.getElementById('autoInfo').textContent='Frequenza '+f+' Hz — invio tono a '+curDb+' dB...';
  document.getElementById('autoInfo').className='status info';
  document.getElementById('tVisAuto').style.display='flex';
  autoSendAndWait();
}

function autoSendAndWait(){
  if(!autoRunning) return;
  const ctx=getCtx();
  const f=FR_ALL[curFIdx];
  const osc=ctx.createOscillator();
  const gain=ctx.createGain();
  const amp=Math.pow(10,(curDb-90)/20)*0.8;
  osc.frequency.value=f; osc.type='sine';
  gain.gain.setValueAtTime(0,ctx.currentTime);
  gain.gain.linearRampToValueAtTime(amp,ctx.currentTime+0.05);
  gain.gain.setValueAtTime(amp,ctx.currentTime+2.5);
  gain.gain.linearRampToValueAtTime(0,ctx.currentTime+2.6);
  osc.connect(gain); gain.connect(ctx.destination);
  osc.start(); osc.stop(ctx.currentTime+2.6);
  document.getElementById('autoInfo').textContent=f+' Hz @ '+curDb+' dB — il paziente risponde?';
  document.getElementById('autoInfo').className='status warn';
  // Aspetta risposta dal terapeuta via pulsanti
  autoRespPending=true;
}

function autoResp(resp){
  if(!autoRespPending||!autoRunning) return;
  autoRespPending=false;
  if(resp){
    lastRespDb=curDb;
    if(respHistory.filter(h=>h.resp).length===0 && curDb===30){
      curDb=-20; updDbDisp(); respHistory.push({db:30,resp:true});
      autoTimer=setTimeout(autoSendAndWait,600);
    } else if(curDb<=-20){
      // Valida
      const fi=curFIdx;
      if(ear==='OD') od[fi]=curDb; else os[fi]=curDb;
      buildChips(); buildSoglie();
      autoFIdx++; autoTimer=setTimeout(autoNext,800);
    } else {
      respHistory.push({db:curDb,resp:true});
      curDb=Math.max(-20,curDb-5); updDbDisp();
      autoTimer=setTimeout(autoSendAndWait,600);
    }
  } else {
    respHistory.push({db:curDb,resp:false});
    if(curDb>=50){
      // Non valida
      autoFIdx++; autoTimer=setTimeout(autoNext,800);
    } else {
      curDb=Math.min(90,curDb+5); updDbDisp();
      autoTimer=setTimeout(autoSendAndWait,600);
    }
  }
}

// Pulsanti risposta visibili in auto
document.getElementById('bResp').addEventListener('click',()=>{if(mode==='auto')autoResp(true);else markResp(true);});
document.getElementById('bNoResp').addEventListener('click',()=>{if(mode==='auto')autoResp(false);else markResp(false);});

// ── Ear ─────────────────────────────────────────────────────────────────
function setEar(e){
  ear=e;
  document.getElementById('bOD').classList.toggle('active',e==='OD');
  document.getElementById('bOS').classList.toggle('active',e==='OS');
  curDb=30; buildChips(); updDbDisp(); respHistory=[]; lastRespDb=null;
  document.getElementById('bVal').disabled=true;
  document.getElementById('testStatus').textContent='Orecchio '+e+'. Seleziona frequenza e invia tono.';
  document.getElementById('testStatus').className='status info';
}

// ── Soglie display ───────────────────────────────────────────────────────
function buildSoglie(){
  ['OD','OS'].forEach(e=>{
    const arr=e==='OD'?od:os;
    const el=document.getElementById('sog'+e);
    el.innerHTML='';
    FR_ALL.forEach((f,i)=>{
      if(arr[i]===null) return;
      const chip=document.createElement('div');
      chip.style.cssText=`display:inline-flex;align-items:center;gap:4px;padding:3px 8px;border-radius:10px;font-size:11px;background:${e==='OD'?'#fdecea':'#eaf4fb'};border:1px solid ${e==='OD'?'#c0392b':'#2980b9'};color:${e==='OD'?'#c0392b':'#2980b9'}`;
      chip.textContent=FL_ALL[i]+': '+arr[i]+'dB';
      el.appendChild(chip);
    });
    if(!FR_ALL.some((_,i)=>arr[i]!==null)){
      el.innerHTML='<span style="font-size:11px;color:#8a8a8a">Nessuna soglia registrata</span>';
    }
  });
  drawAudio(); calcEQ();
}

function resetSoglie(){od=new Array(12).fill(null);os=new Array(12).fill(null);buildChips();buildSoglie();}

// ── Grafico ──────────────────────────────────────────────────────────────
function drawAudio(){
  const cv=document.getElementById('cvA');
  if(!cv) return;
  cv.width=cv.parentElement.clientWidth-32;
  const ctx2=cv.getContext('2d');
  const W=cv.width,H=cv.height;
  const pL=44,pR=12,pT=18,pB=24;
  const cw=W-pL-pR,ch=H-pT-pB;
  ctx2.clearRect(0,0,W,H);
  ctx2.fillStyle='#fff';ctx2.fillRect(0,0,W,H);
  const mn=-20,mx=90;
  const tx=i=>pL+i*(cw/(FR.length-1));
  const ty=d=>pT+(d-mn)/(mx-mn)*ch;
  ctx2.strokeStyle='rgba(128,128,128,0.12)';ctx2.lineWidth=0.5;
  for(let d=mn;d<=mx;d+=10){ctx2.beginPath();ctx2.moveTo(pL,ty(d));ctx2.lineTo(W-pR,ty(d));ctx2.stroke();}
  FR.forEach((_,i)=>{ctx2.beginPath();ctx2.moveTo(tx(i),pT);ctx2.lineTo(tx(i),pT+ch);ctx2.stroke();});
  ctx2.strokeStyle='rgba(128,128,128,0.45)';ctx2.lineWidth=1;
  ctx2.beginPath();ctx2.moveTo(pL,ty(0));ctx2.lineTo(W-pR,ty(0));ctx2.stroke();
  ctx2.fillStyle='#aaa';ctx2.font='9px sans-serif';ctx2.textAlign='right';
  for(let d=mn;d<=mx;d+=10)ctx2.fillText(d,pL-3,ty(d)+3);
  ctx2.textAlign='center';FR.forEach((_,i)=>ctx2.fillText(FL[i],tx(i),pT+ch+13));
  // Zona iperudizione
  ctx2.fillStyle='rgba(45,125,111,0.05)';ctx2.fillRect(pL,pT,cw,ty(0)-pT);
  // Tomatis
  ctx2.strokeStyle='#2d7d6f';ctx2.lineWidth=2;ctx2.setLineDash([5,4]);
  ctx2.beginPath();
  tom.forEach((v,i)=>{const x=tx(i),y=ty(v);i===0?ctx2.moveTo(x,y):ctx2.lineTo(x,y);});
  ctx2.stroke();ctx2.setLineDash([]);
  // OD (usa solo le 11 frequenze base, non 10.5k per il grafico)
  function dc(vals,col,sym){
    const pts=vals.slice(0,11).map((v,i)=>v!==null?[tx(i),ty(v)]:null).filter(Boolean);
    if(!pts.length)return;
    ctx2.strokeStyle=col;ctx2.lineWidth=2;
    ctx2.beginPath();pts.forEach(([x,y],i)=>i===0?ctx2.moveTo(x,y):ctx2.lineTo(x,y));ctx2.stroke();
    ctx2.fillStyle=col;ctx2.font='bold 13px sans-serif';ctx2.textAlign='center';
    pts.forEach(([x,y])=>ctx2.fillText(sym,x,y+4));
  }
  dc(od,'#c0392b','O');dc(os,'#2980b9','X');
}

// ── Tomatis grid ─────────────────────────────────────────────────────────
function buildTomGrid(){
  const g=document.getElementById('tomGrid');g.innerHTML='';
  FR.forEach((_,i)=>{
    const d=document.createElement('div');d.className='tg';
    d.innerHTML=`<label>${FL[i]}</label><input type="number" id="tom_${i}" value="${tom[i]}" min="-30" max="10" step="1" oninput="setTom(${i},this.value)">`;
    g.appendChild(d);
  });
}
function setTom(i,v){tom[i]=parseFloat(v)||0;drawAudio();calcEQ();}
function resetTom(){tom=[...TOM_STD];FR.forEach((_,i)=>{const e=document.getElementById('tom_'+i);if(e)e.value=tom[i];});drawAudio();calcEQ();}

// ── EQ ───────────────────────────────────────────────────────────────────
function calcEQ(){
  const eqOD=FR.map((_,i)=>od[i]!==null?Math.round(tom[i]-od[i]):null);
  const eqOS=FR.map((_,i)=>os[i]!==null?Math.round(tom[i]-os[i]):null);
  const g=document.getElementById('eqGrid');g.innerHTML='';
  FR.forEach((_,i)=>{
    const v=eqOD[i]!==null?eqOD[i]:eqOS[i];
    if(v===null) return;
    const col=v>3?'#1d9e75':v<-3?'#e24b4a':'#ba7517';
    const h=Math.min(28,Math.abs(v)*2);
    const pos=v>=0?`bottom:50%;height:${h}px`:`top:50%;height:${h}px`;
    const d=document.createElement('div');d.className='eq-bar';
    d.innerHTML=`<div class="eq-track"><div class="eq-fill" style="${pos};background:${col}"></div></div><div class="eq-val" style="color:${col}">${v>0?'+'+v:v}</div><div class="eq-lbl">${FL[i]}</div>`;
    g.appendChild(d);
  });
  const vals=eqOD.filter(v=>v!==null);
  if(vals.length>0){
    const avg=vals.reduce((a,b)=>a+b,0)/vals.length;
    document.getElementById('eqNote').textContent=avg>5?'Ipouduzione — rinforzo':avg<-5?'Iperudizione — attenuazione':'Soglie vicine al target';
    const maxIdx=vals.indexOf(Math.max(...vals.map(Math.abs)));
    document.getElementById('eqDom').textContent=FR[maxIdx]+'Hz ('+( eqOD[maxIdx]>0?'+':'')+eqOD[maxIdx]+' dB)';
  }
}

// ── Selettivita / Lateralita ─────────────────────────────────────────────
const SEL_ROWS=['LE BC','LE AC','RE BC','RE AC'];
const LAT_ROWS=['BPTA 20dB','A soglia'];
const OPTS=['','O','X','OX'];

function buildSel(){
  const b=document.getElementById('selBody');b.innerHTML='';
  SEL_ROWS.forEach(r=>{const tr=document.createElement('tr');
    tr.innerHTML=`<td>${r}</td>`+FR.map((_,i)=>`<td><select class="sel" id="sl_${r.replace(/\s/g,'_')}_${i}">${OPTS.map(o=>`<option>${o}</option>`).join('')}</select></td>`).join('');
    b.appendChild(tr);});
}
function buildLat(){
  const b=document.getElementById('latBody');b.innerHTML='';
  LAT_ROWS.forEach(r=>{const tr=document.createElement('tr');
    tr.innerHTML=`<td>${r}</td>`+FR.map((_,i)=>`<td><select class="sel" id="lt_${r.replace(/\s/g,'_')}_${i}" onchange="calcLat()">${OPTS.map(o=>`<option>${o}</option>`).join('')}</select></td>`).join('');
    b.appendChild(tr);});
}
function calcLat(){
  let odC=0,osC=0;
  FR.forEach((_,i)=>{LAT_ROWS.forEach(r=>{const v=document.getElementById(`lt_${r.replace(/\s/g,'_')}_${i}`)?.value||'';
    if(v==='O')odC++;else if(v==='X')osC++;else if(v==='OX'){odC++;osC++;}});});
  const tot=odC+osC;
  document.getElementById('latDom').textContent=odC>osC?'OD dominante':osC>odC?'OS dominante':'Bilanciato';
  document.getElementById('latIdx').textContent=tot?Math.round((odC-osC)*100/tot)+'/100':'-';
}

// ── Tab switch ───────────────────────────────────────────────────────────
function sw(n){
  document.querySelectorAll('.section').forEach((s,i)=>s.classList.toggle('active',i===n));
  document.querySelectorAll('.tab').forEach((t,i)=>t.classList.toggle('active',i===n));
  if(n===1){setTimeout(()=>{drawAudio();calcEQ();buildTomGrid();},50);}
}

// ── Save ─────────────────────────────────────────────────────────────────
function saveAll(){
  const eqOD=FR.map((_,i)=>od[i]!==null?Math.round(tom[i]-od[i]):0);
  const eqOS=FR.map((_,i)=>os[i]!==null?Math.round(tom[i]-os[i]):0);
  const selData={};
  SEL_ROWS.forEach(r=>FR.forEach((_,i)=>{const v=document.getElementById(`sl_${r.replace(/\s/g,'_')}_${i}`)?.value;if(v)selData[r+'_'+i]=v;}));
  const latData={};
  LAT_ROWS.forEach(r=>FR.forEach((_,i)=>{const v=document.getElementById(`lt_${r.replace(/\s/g,'_')}_${i}`)?.value;if(v)latData[r+'_'+i]=v;}));
  const data={od:od.slice(0,11),os:os.slice(0,11),tom:tom,eqOD:eqOD,eqOS:eqOS,sel:selData,lat:latData};
  window.parent.postMessage({type:'streamlit:setComponentValue',value:JSON.stringify(data)},'*');
  document.getElementById('saved').style.display='block';
  setTimeout(()=>document.getElementById('saved').style.display='none',3000);
}

// ── Init ─────────────────────────────────────────────────────────────────
buildChips(); updDbDisp(); buildSel(); buildLat();
buildSoglie();
window.addEventListener('resize',()=>{drawAudio();});
setTimeout(()=>{drawAudio();},120);
</script></body></html>"""


def _is_postgres(conn):
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

def _row_get(row, key, default=None):
    try: v = row[key]; return v if v is not None else default
    except Exception:
        try: return row.get(key, default)
        except: return default

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

def _init_db(conn):
    raw = getattr(conn, "_conn", conn)
    try: cur = raw.cursor()
    except: cur = conn.cursor()
    pg = _is_postgres(conn)
    if pg:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS audiometrie_funzionali (
            id BIGSERIAL PRIMARY KEY,
            paziente_id BIGINT NOT NULL,
            data_esame TEXT, operatore TEXT,
            od_json TEXT, os_json TEXT,
            tomatis_json TEXT,
            eq_od_json TEXT, eq_os_json TEXT,
            sel_json TEXT, lat_json TEXT,
            joh_od INTEGER, joh_os INTEGER,
            joh_indice DOUBLE PRECISION, joh_dominanza TEXT,
            note TEXT, created_at TEXT
        )""")
    else:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS audiometrie_funzionali (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paziente_id INTEGER NOT NULL,
            data_esame TEXT, operatore TEXT,
            od_json TEXT, os_json TEXT,
            tomatis_json TEXT,
            eq_od_json TEXT, eq_os_json TEXT,
            sel_json TEXT, lat_json TEXT,
            joh_od INTEGER, joh_os INTEGER,
            joh_indice REAL, joh_dominanza TEXT,
            note TEXT, created_at TEXT
        )""")
    try: raw.commit()
    except: conn.commit()

def _salva_audiometria(conn, paz_id, data, operatore=""):
    cur = conn.cursor()
    joh = data.get("joh", {})
    jod = int(joh.get("od", 0))
    jos = int(joh.get("os", 0))
    jtot = jod + jos
    jidx = round((jod - jos) * 100 / jtot, 1) if jtot > 0 else None
    jdom = (None if jidx is None else
            "OD" if jidx > 10 else "OS" if jidx < -10 else "Bilanciato")
    ph = _ph(16, conn)
    params = (
        paz_id, date.today().isoformat(), operatore,
        json.dumps(data.get("od", [])),
        json.dumps(data.get("os", [])),
        json.dumps(data.get("tom", TOMATIS_STD)),
        json.dumps(data.get("eqOD", [])),
        json.dumps(data.get("eqOS", [])),
        json.dumps(data.get("sel", {})),
        json.dumps(data.get("lat", {})),
        jod, jos, jidx, jdom,
        data.get("note", ""),
        datetime.now().isoformat(timespec="seconds"),
    )
    sql = (
        "INSERT INTO audiometrie_funzionali "
        "(paziente_id, data_esame, operatore, od_json, os_json, tomatis_json, "
        "eq_od_json, eq_os_json, sel_json, lat_json, joh_od, joh_os, "
        f"joh_indice, joh_dominanza, note, created_at) VALUES ({ph})"
    )
    try:
        cur.execute(sql, params)
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Errore salvataggio: {e}")
        return False


def ui_audiometria_funzionale():
    st.header("Audiometria Funzionale")
    st.caption(
        "Audiogramma + curva Tomatis · Delta EQ terapeutico · "
        "Selettivita · Lateralita · Test dicotico Johansen"
    )

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
    c1, c2 = st.columns([3, 1])
    with c1: sel = st.selectbox("Paziente", opts, key="af_paz")
    with c2: op = st.text_input("Operatore", "", key="af_op")
    paz_id = int(sel.split(" - ", 1)[0])

    st.divider()

    tab_audio, tab_joh, tab_storico = st.tabs([
        "Audiogramma + EQ", "Test dicotico Johansen", "Storico"
    ])

    with tab_audio:
        result = components.html(_HTML_AUDIOGRAMMA, height=900, scrolling=True)
        if result:
            try:
                data = json.loads(result) if isinstance(result, str) else result
                if data and (data.get("od") or data.get("os")):
                    if _salva_audiometria(conn, paz_id, data, op):
                        st.success("Audiometria salvata.")
                        _mostra_eq_summary(data)
                        st.rerun()
            except Exception:
                pass

    with tab_joh:
        _ui_test_dicotico(conn, cur, paz_id)

    with tab_storico:
        _ui_storico_audiometria(conn, cur, paz_id)


def _mostra_eq_summary(data):
    eq_od = data.get("eqOD", [])
    if not any(eq_od):
        return
    st.markdown("**EQ generato (OD):**")
    freq_labels = ["125","250","500","750","1k","1.5k","2k","3k","4k","6k","8k"]
    cols = st.columns(11)
    for i, (c, v) in enumerate(zip(cols, eq_od)):
        color = "green" if v > 3 else "red" if v < -3 else "orange"
        c.markdown(f"<div style='text-align:center;font-size:11px'><b style='color:{color}'>{v:+d}</b><br><span style='font-size:9px;color:#888'>{freq_labels[i]}</span></div>", unsafe_allow_html=True)


def _ui_test_dicotico(conn, cur, paz_id):
    st.subheader("Test dicotico di Johansen")
    st.caption(
        "Carica le 6 tracce MP3 stereo (una per compito). "
        "Le tracce presentano sillabe diverse OD/OS simultaneamente. "
        "Registra le risposte del paziente per ogni coppia."
    )

    st.info(
        "Carica le tracce MP3 del test Johansen (le 6 tracce stereo della sequenza). "
        "Ogni traccia corrisponde a un compito specifico."
    )

    # Upload tracce
    with st.expander("Carica tracce MP3", expanded=True):
        uploaded = {}
        for info in JOHANSEN_INFO:
            n = info["traccia"]
            f = st.file_uploader(
                f"Traccia {n} — {info['desc']} ({info['durata']})",
                type=["mp3","wav"], key=f"joh_track_{n}"
            )
            if f: uploaded[n] = f

    if uploaded:
        st.markdown("**Riproduci le tracce in ordine:**")
        for n, f in sorted(uploaded.items()):
            info = JOHANSEN_INFO[n-1]
            st.markdown(f"**Traccia {n} — {info['desc']}**")
            st.audio(f.getvalue(), format="audio/mp3")

    # Tabella risposte
    st.markdown("---")
    st.markdown("**Registra le risposte del paziente:**")
    st.caption("Per ogni coppia segna cosa ha risposto il paziente. Comp.3 = risposta DX, Comp.4 = SX, Comp.5 = entrambi")

    if "joh_risposte" not in st.session_state:
        st.session_state.joh_risposte = {}

    opts_resp = ["", "OD", "OS", "Entrambi"]
    for i, coppia in enumerate(JOHANSEN_COPPIE):
        c0, c1, c2, c3, c4, c5 = st.columns([0.5, 1, 1, 1.5, 1.5, 1.5])
        c0.markdown(f"<div style='font-size:11px;color:#888;padding-top:8px'>{i+1}</div>", unsafe_allow_html=True)
        c1.markdown(f"<div style='color:#c0392b;font-weight:600;font-size:13px;padding-top:6px'>{coppia['od']}</div>", unsafe_allow_html=True)
        c2.markdown(f"<div style='color:#2980b9;font-weight:600;font-size:13px;padding-top:6px'>{coppia['os']}</div>", unsafe_allow_html=True)
        r = st.session_state.joh_risposte.get(i, {})
        with c3:
            v = st.selectbox("Comp.3", opts_resp, key=f"jc3_{i}", index=opts_resp.index(r.get("c3","")) if r.get("c3","") in opts_resp else 0, label_visibility="collapsed")
            if v: st.session_state.joh_risposte.setdefault(i, {})["c3"] = v
        with c4:
            v = st.selectbox("Comp.4", opts_resp, key=f"jc4_{i}", index=opts_resp.index(r.get("c4","")) if r.get("c4","") in opts_resp else 0, label_visibility="collapsed")
            if v: st.session_state.joh_risposte.setdefault(i, {})["c4"] = v
        with c5:
            v = st.selectbox("Comp.5", opts_resp, key=f"jc5_{i}", index=opts_resp.index(r.get("c5","")) if r.get("c5","") in opts_resp else 0, label_visibility="collapsed")
            if v: st.session_state.joh_risposte.setdefault(i, {})["c5"] = v

    # Calcolo punteggi
    jod, jos = 0, 0
    for i, r in st.session_state.joh_risposte.items():
        if r.get("c3") == "OD": jod += 1
        if r.get("c4") == "OS": jos += 1
        if r.get("c5") in ["OD", "Entrambi"]: jod += 1
        if r.get("c5") in ["OS", "Entrambi"]: jos += 1

    tot = jod + jos
    idx = round((jod - jos) * 100 / tot, 1) if tot > 0 else 0
    dom = "OD dominante" if idx > 10 else "OS dominante" if idx < -10 else "Bilanciato"

    m1, m2, m3 = st.columns(3)
    m1.metric("Punteggio OD", jod)
    m2.metric("Punteggio OS", jos)
    m3.metric("Indice lateralita", f"{idx:+.1f}" if tot > 0 else "—")
    if tot > 0:
        st.info(f"**{dom}** (indice {idx:+.1f}/100)")

    if st.button("Salva test Johansen", type="primary", key="save_joh"):
        data = {"joh": {"od": jod, "os": jos, "ans": dict(st.session_state.joh_risposte)}}
        if _salva_audiometria(conn, paz_id, data, ""):
            st.success(f"Test Johansen salvato: OD={jod} OS={jos} Indice={idx:+.1f}")


def _ui_storico_audiometria(conn, cur, paz_id):
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

    # Grafici trend EQ nel tempo
    eq_trend = []
    for r in rows:
        d = _row_get(r, "data_esame", "")
        eq_raw = _row_get(r, "eq_od_json", "[]")
        try:
            eq = json.loads(eq_raw) if eq_raw else []
            if eq and any(eq):
                avg = round(sum(eq) / len(eq), 1)
                eq_trend.append({"Data": d, "Delta EQ medio OD": avg})
        except Exception:
            pass

    if eq_trend:
        st.markdown("**Andamento delta EQ nel tempo (OD)**")
        st.line_chart(pd.DataFrame(eq_trend).sort_values("Data").set_index("Data"))

    for r in rows:
        eid = _row_get(r, "id")
        data_e = _row_get(r, "data_esame", "")
        jdom = _row_get(r, "joh_dominanza", "—")
        jidx = _row_get(r, "joh_indice")

        with st.expander(f"#{eid} | {data_e} | Johansen: {jdom}"):
            try:
                od = json.loads(_row_get(r, "od_json", "[]") or "[]")
                os_ = json.loads(_row_get(r, "os_json", "[]") or "[]")
                eq = json.loads(_row_get(r, "eq_od_json", "[]") or "[]")
                tom = json.loads(_row_get(r, "tomatis_json", "[]") or "[]")
            except Exception:
                od, os_, eq, tom = [], [], [], []

            freq_labels = ["125","250","500","750","1k","1.5k","2k","3k","4k","6k","8k"]
            if od and any(v is not None for v in od):
                st.markdown("**Soglie OD (dB HL):**")
                cols = st.columns(11)
                for i, (c, v) in enumerate(zip(cols, od)):
                    if v is not None:
                        c.markdown(f"<div style='text-align:center;font-size:11px'><b>{v}</b><br><span style='font-size:9px;color:#888'>{freq_labels[i]}</span></div>", unsafe_allow_html=True)

            if eq and any(eq):
                st.markdown("**EQ terapeutico OD:**")
                cols = st.columns(11)
                for i, (c, v) in enumerate(zip(cols, eq)):
                    color = "green" if v > 3 else "red" if v < -3 else "orange"
                    c.markdown(f"<div style='text-align:center;font-size:11px'><b style='color:{color}'>{v:+d}</b><br><span style='font-size:9px;color:#888'>{freq_labels[i]}</span></div>", unsafe_allow_html=True)

            jod = _row_get(r, "joh_od")
            jos = _row_get(r, "joh_os")
            if jod is not None:
                m1, m2, m3 = st.columns(3)
                m1.metric("Johansen OD", jod)
                m2.metric("Johansen OS", jos)
                m3.metric("Indice", f"{jidx:+.1f}" if jidx else "—")
