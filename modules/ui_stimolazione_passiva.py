# -*- coding: utf-8 -*-
"""
Modulo: Stimolazione Uditiva Passiva — Metodo Hipérion
Gestionale The Organism

Motore WebAudio completo:
  - EQ paziente (delta Tomatis, 11 bande per canale)
  - Gate Ampiezza (Bascula Ampiezza Hipérion)
  - Gate Frequenze (Bascula Frequenze tornante)
  - Gate G/D (alternanza OD/OS)
  - Lissage (smoothing transizioni)
  - Delay via aerea vs ossea
  - Binaurale beats (Delta/Theta/Alfa/Beta/Gamma)
  - VU meter real-time
  - Timer seduta
"""

import json
import streamlit as st
from datetime import datetime

# ─────────────────────────────────────────────────────────────────────────────
# Costanti
# ─────────────────────────────────────────────────────────────────────────────

FREQS_EQ = [125, 250, 500, 750, 1000, 1500, 2000, 3000, 4000, 6000, 8000]
FLABELS  = ['125','250','500','750','1k','1.5k','2k','3k','4k','6k','8k']

BINAURAL_PRESETS = {
    "Delta (1.5-3 Hz) — Sonno profondo / autoguarigione": {"beat": 2.0,  "carrier": 100},
    "Theta (4-7 Hz) — Meditazione / creativita":          {"beat": 5.0,  "carrier": 200},
    "Alfa (8-12 Hz) — Rilassamento / creativita":         {"beat": 10.0, "carrier": 200},
    "Beta basso (13-20 Hz) — Focus / concentrazione":     {"beat": 15.0, "carrier": 300},
    "Beta alto (20-39 Hz) — Veglia / attivita fisica":    {"beat": 25.0, "carrier": 300},
    "Gamma (40+ Hz) — Alta cognizione":                   {"beat": 40.0, "carrier": 400},
    "Personalizzato":                                      {"beat": 10.0, "carrier": 200},
}

STIM_HTML = r"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
*{box-sizing:border-box;margin:0;padding:0;font-family:system-ui,sans-serif}
body{padding:10px;background:#f8f7f4;color:#1a1a1a;font-size:13px}
.card{background:#fff;border:1px solid #d4cec5;border-radius:10px;padding:12px 14px;margin-bottom:8px}
h3{font-size:13px;font-weight:500;margin-bottom:6px}
.cap{font-size:11px;color:#8a8a8a;margin-bottom:8px}
.row{display:flex;align-items:center;gap:8px;margin:4px 0}
.row label{font-size:11px;color:#4a4a4a;min-width:120px}
.row span.val{font-size:12px;font-weight:500;min-width:48px;text-align:right}
input[type=range]{flex:1;accent-color:#1d9e75;cursor:pointer}
select,input[type=number],input[type=text]{padding:4px 8px;border-radius:6px;border:1px solid #d4cec5;font-size:12px;background:#fff;color:#1a1a1a;font-family:inherit}
input[type=text]{flex:1}
button{font-family:inherit;font-size:12px;padding:6px 12px;border-radius:7px;border:1.5px solid #d4cec5;background:#fff;color:#4a4a4a;cursor:pointer;transition:all .15s}
button:hover{background:#e1f5ee;border-color:#1d9e75;color:#0f6e56}
button.primary{background:#1d9e75;border-color:#1d9e75;color:#fff}
button.primary:hover{background:#0f6e56}
button.danger{background:#e24b4a;border-color:#e24b4a;color:#fff}
button.danger:hover{background:#a32d2d}
button.sm{padding:3px 8px;font-size:11px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.grid3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px}
.status{font-size:11px;padding:5px 9px;border-radius:6px;margin:5px 0}
.ok{background:#e1f5ee;color:#0f6e56}
.warn{background:#fef7ec;color:#7a4f0a}
.info{background:#ebf5fb;color:#154360}
.err{background:#fcebeb;color:#a32d2d}
.toggle-row{display:flex;align-items:center;gap:8px}
.toggle{width:38px;height:22px;border-radius:11px;position:relative;cursor:pointer;border:none;padding:0;transition:background .2s;flex-shrink:0}
.toggle.on{background:#1d9e75}.toggle.off{background:#b4b2a9}
.toggle::after{content:'';position:absolute;width:16px;height:16px;border-radius:50%;background:#fff;top:3px;transition:left .2s}
.toggle.on::after{left:19px}.toggle.off::after{left:3px}
.eq-wrap{display:flex;gap:3px;margin:6px 0}
.eq-col{flex:1;display:flex;flex-direction:column;align-items:center;gap:2px}
.eq-col input[type=range]{writing-mode:vertical-lr;direction:rtl;width:24px;height:70px;accent-color:#1d9e75}
.eq-col .lbl{font-size:9px;color:#8a8a8a;text-align:center}
.eq-col .val{font-size:9px;font-weight:500;text-align:center;min-width:26px}
.vu-wrap{margin:6px 0}
.vu-label{font-size:10px;color:#8a8a8a;margin-bottom:2px}
.vu{height:12px;background:#ede9e3;border-radius:6px;overflow:hidden;position:relative}
.vu-fill{height:100%;border-radius:6px;transition:width .04s;will-change:width}
.vu-od{background:linear-gradient(90deg,#1d9e75,#ba7517,#e24b4a)}
.vu-os{background:linear-gradient(90deg,#1d9e75,#2980b9,#8e44ad)}
.timer-big{font-size:40px;font-weight:500;text-align:center;letter-spacing:3px;font-variant-numeric:tabular-nums;padding:6px 0}
.timer-sub{font-size:11px;color:#8a8a8a;text-align:center;margin-bottom:6px}
.btn-row{display:flex;gap:8px;justify-content:center;margin-top:6px}
.freq-band{display:flex;gap:2px;flex-wrap:wrap;margin:6px 0}
.freq-chip{padding:3px 7px;border-radius:8px;font-size:10px;cursor:pointer;border:1px solid #d4cec5;background:#f8f7f4;color:#8a8a8a;transition:all .1s}
.freq-chip.active{background:#1d9e75;border-color:#1d9e75;color:#fff}
.binaural-wave{height:40px;width:100%;margin:6px 0}
.section-sep{height:1px;background:#ede9e3;margin:8px 0}
</style></head><body>

<!-- SORGENTE AUDIO -->
<div class="card">
  <h3>Sorgente audio</h3>
  <div class="row">
    <label>URL file</label>
    <input type="text" id="audioUrl" placeholder="https://... (WAV, FLAC, MP3, OGG)">
    <button onclick="loadAudio()" class="primary">Carica</button>
  </div>
  <div id="audioSt" class="status info">Inserisci URL del file audio.</div>
  <div class="row" style="margin-top:6px">
    <label>Volume master</label>
    <input type="range" id="masterVol" min="0" max="100" value="80" step="1" oninput="setMasterVol(this.value)">
    <span class="val" id="masterVolV">80%</span>
  </div>
</div>

<!-- EQ PAZIENTE -->
<div class="card">
  <h3>Profilo EQ paziente (delta Tomatis — 11 bande)</h3>
  <p class="cap">Positivo = rinforzo, negativo = attenuazione. Carica dal profilo audiometrico o imposta manualmente.</p>
  <div style="display:flex;gap:6px;margin-bottom:6px">
    <button onclick="loadEQFromProfile()" class="sm">Carica da audiogramma</button>
    <button onclick="resetEQ()" class="sm">Reset flat</button>
    <span id="eqSt" style="font-size:11px;color:#8a8a8a;margin-left:4px"></span>
  </div>
  <div style="font-size:11px;font-weight:500;color:#c0392b;margin-bottom:2px">OD — canale destro</div>
  <div class="eq-wrap" id="eqOD_sliders"></div>
  <div style="font-size:11px;font-weight:500;color:#2980b9;margin-top:6px;margin-bottom:2px">OS — canale sinistro</div>
  <div class="eq-wrap" id="eqOS_sliders"></div>
</div>

<!-- GATING HIPERION -->
<div class="card">
  <h3>Gating Hipérion</h3>
  <div class="grid2">
    <div>
      <div style="font-size:12px;font-weight:500;margin-bottom:6px;color:#1d9e75">Bascula Ampiezza</div>
      <div class="row"><label>Durata ciclo</label>
        <select id="gDur"><option value="300">-5 min</option><option value="600">5 min</option><option value="900" selected>-5 min (default)</option><option value="1200">10 min</option><option value="1500">15 min</option><option value="1800">20 min</option></select>
      </div>
      <div class="row"><label>Attenuazione (dB)</label>
        <select id="gAtten" onchange="applyGating()">
          <option value="0">0 dB</option><option value="3">-3 dB</option>
          <option value="6">-6 dB</option><option value="9" selected>-9 dB</option>
          <option value="12">-12 dB</option><option value="15">-15 dB</option>
        </select>
      </div>
      <div class="row"><label>Tempo min (s)</label>
        <select id="gMin" onchange="applyGating()">
          <option value="0.2">0.2 s</option><option value="0.5">0.5 s</option>
          <option value="1" selected>1 s</option><option value="1.5">1.5 s</option>
          <option value="2">2 s</option><option value="3">3 s</option><option value="5">5 s</option>
        </select>
      </div>
      <div class="row"><label>Tempo max (s)</label>
        <select id="gMax" onchange="applyGating()">
          <option value="0.5" selected>0.5 s</option><option value="1">1 s</option>
          <option value="1.5">1.5 s</option><option value="2">2 s</option>
          <option value="3">3 s</option><option value="5">5 s</option>
        </select>
      </div>
      <div class="row"><label>Lissage</label>
        <input type="range" id="lissage" min="0" max="200" value="30" step="1" oninput="updLissage(this.value)">
        <span class="val" id="lissageV">30ms</span>
      </div>
    </div>
    <div>
      <div style="font-size:12px;font-weight:500;margin-bottom:6px;color:#1d9e75">Bascula Frequenze</div>
      <div class="row"><label>Freq. tornante</label>
        <select id="fTornante" onchange="applyGating()">
          <option value="750">750 Hz</option><option value="1000">1000 Hz</option>
          <option value="1500" selected>1500 Hz</option><option value="2000">2000 Hz</option>
          <option value="2500">2500 Hz</option><option value="3000">3000 Hz</option>
          <option value="3500">3500 Hz</option><option value="4000">4000 Hz</option>
        </select>
      </div>
      <div class="row"><label>Attenuazione</label>
        <select id="fAtten" onchange="applyGating()">
          <option value="0,9">0-9 dB</option><option value="3,13">-3-13 dB</option>
          <option value="6,16">-6-16 dB</option><option value="9,20">-9-20 dB</option>
          <option value="12,25">-12-25 dB</option><option value="15,30">-15-30 dB</option>
          <option value="25,35">-25-35 dB</option>
        </select>
      </div>
      <div class="row"><label>Tempo min</label>
        <select id="fMin" onchange="applyGating()">
          <option value="100" selected>100 ms</option><option value="150">150 ms</option>
          <option value="200">200 ms</option><option value="300">300 ms</option>
          <option value="500">500 ms</option><option value="1000">1000 ms</option>
        </select>
      </div>
      <div class="row"><label>Tempo max</label>
        <select id="fMax" onchange="applyGating()">
          <option value="500">500 ms</option><option value="1000">1000 ms</option>
          <option value="1500" selected>1500 ms</option><option value="2000">2000 ms</option>
          <option value="3000">3000 ms</option>
        </select>
      </div>
      <div class="section-sep"></div>
      <div class="toggle-row" style="margin:4px 0">
        <button class="toggle on" id="togGD" onclick="toggleBtn('togGD','togGDlbl',toggleGD)"></button>
        <span id="togGDlbl" style="font-size:11px">Gate G/D attivo</span>
      </div>
      <div class="toggle-row" style="margin:4px 0">
        <button class="toggle on" id="togAlea" onclick="toggleBtn('togAlea','togAlealbl',toggleAlea)"></button>
        <span id="togAlealbl" style="font-size:11px">Alea (timing random)</span>
      </div>
    </div>
  </div>
</div>

<!-- DELAY -->
<div class="card">
  <h3>Delay via aerea / ossea</h3>
  <div class="grid3">
    <div><div style="font-size:11px;color:#8a8a8a;margin-bottom:3px">Latenza Air (ms)</div>
      <input type="number" id="delayAir" min="0" max="500" value="0" style="width:80px" oninput="applyDelay()">
    </div>
    <div><div style="font-size:11px;color:#8a8a8a;margin-bottom:3px">Latenza Bone (ms)</div>
      <input type="number" id="delayBone" min="0" max="500" value="100" style="width:80px" oninput="applyDelay()">
    </div>
    <div><div style="font-size:11px;color:#8a8a8a;margin-bottom:3px">Modalita</div>
      <select id="modality" onchange="applyDelay()">
        <option selected>Solo Air</option><option>Solo Bone</option><option>Air + Bone</option>
      </select>
    </div>
  </div>
</div>

<!-- BINAURALE -->
<div class="card">
  <h3>Effetto binaurale (Brainwave Entrainment)</h3>
  <p class="cap">Tono carrier OD + (carrier + beat) OS. Il cervello percepisce la differenza = frequenza di sincronizzazione.</p>
  <div class="toggle-row" style="margin-bottom:8px">
    <button class="toggle on" id="togBin" onclick="toggleBtn('togBin','togBinlbl',toggleBinaural)"></button>
    <span id="togBinlbl" style="font-size:11px">Binaurale attivo</span>
  </div>
  <div class="row"><label>Preset onda</label>
    <select id="binPreset" onchange="loadPreset()" style="flex:1">
      <option>Delta (1.5-3 Hz) — Sonno profondo / autoguarigione</option>
      <option>Theta (4-7 Hz) — Meditazione / creativita</option>
      <option selected>Alfa (8-12 Hz) — Rilassamento / creativita</option>
      <option>Beta basso (13-20 Hz) — Focus / concentrazione</option>
      <option>Beta alto (20-39 Hz) — Veglia / attivita fisica</option>
      <option>Gamma (40+ Hz) — Alta cognizione</option>
      <option>Personalizzato</option>
    </select>
  </div>
  <div class="row"><label>Frequenza carrier (Hz)</label>
    <input type="range" id="binCarrier" min="50" max="500" value="200" step="1" oninput="updBinaural()">
    <span class="val" id="binCarrierV">200 Hz</span>
  </div>
  <div class="row"><label>Beat frequency (Hz)</label>
    <input type="range" id="binBeat" min="0.5" max="50" value="10" step="0.5" oninput="updBinaural()">
    <span class="val" id="binBeatV">10.0 Hz</span>
  </div>
  <div class="row"><label>Volume binaurale</label>
    <input type="range" id="binVol" min="0" max="100" value="15" step="1" oninput="updBinaural()">
    <span class="val" id="binVolV">15%</span>
  </div>
  <canvas class="binaural-wave" id="binCanvas"></canvas>
  <div id="binInfo" class="status info">Alfa 10 Hz — Carrier OD: 200 Hz — OS: 210 Hz</div>
</div>

<!-- TRATTAMENTO -->
<div class="card">
  <h3>Trattamento</h3>
  <div class="grid2">
    <div>
      <div class="row"><label>Durata seduta</label>
        <select id="sessDur">
          <option value="900">15 min</option><option value="1800">30 min</option>
          <option value="3600" selected>60 min</option>
          <option value="5400">90 min</option><option value="7200">120 min</option>
        </select>
      </div>
      <div class="row"><label>Paziente</label>
        <input type="text" id="pazNome" placeholder="Nome paziente (opzionale)" style="flex:1">
      </div>
    </div>
    <div>
      <div class="timer-big" id="timerDisp">00:00:00</div>
      <div class="timer-sub" id="sessStatus">In attesa</div>
      <div class="btn-row">
        <button class="primary" id="btnStart" onclick="startSess()">Avvia</button>
        <button id="btnPause" onclick="pauseSess()">Pausa</button>
        <button class="danger" onclick="stopSess()">Stop</button>
      </div>
    </div>
  </div>
  <div class="vu-wrap" style="margin-top:8px">
    <div class="vu-label">VU OD (destro)</div>
    <div class="vu"><div class="vu-fill vu-od" id="vuOD" style="width:0%"></div></div>
    <div class="vu-label" style="margin-top:4px">VU OS (sinistro)</div>
    <div class="vu"><div class="vu-fill vu-os" id="vuOS" style="width:0%"></div></div>
  </div>
</div>

<!-- LOG SEDUTA -->
<div class="card">
  <h3>Log seduta</h3>
  <div id="sessLog" style="font-size:11px;color:#4a4a4a;font-family:monospace;max-height:120px;overflow-y:auto;background:#f8f7f4;border-radius:6px;padding:6px"></div>
</div>

<script>
/* ───────────────────────────────────────────────────────────
   STATO GLOBALE
   ─────────────────────────────────────────────────────────── */
const FREQS = [125,250,500,750,1000,1500,2000,3000,4000,6000,8000];
const FL    = ['125','250','500','750','1k','1.5k','2k','3k','4k','6k','8k'];

let eqOD = new Array(11).fill(0);
let eqOS = new Array(11).fill(0);
let gGD=true, gAlea=true, gBinaural=true;
let sessRunning=false, sessPaused=false;
let sessStart=0, sessPauseAt=0, sessTimer=null;
let gateTimer=null, vuTimer=null, binWaveTimer=null;

/* WebAudio nodes */
let actx=null, srcNode=null, audioBuffer=null;
let masterGain=null, splitter=null, merger=null;
let gainOD=null, gainOS=null;           // master per canale
let eqFiltersOD=[], eqFiltersOS=[];     // 11 BiquadFilter per canale
let gateGainOD=null, gateGainOS=null;  // gate ampiezza per canale
let freqFilterOD=null, freqFilterOS=null; // gate frequenze
let delayNodeAir=null, delayNodeBone=null;
let binOscOD=null, binOscOS=null, binGain=null;
let analyserOD=null, analyserOS=null;

/* ───────────────────────────────────────────────────────────
   EQ SLIDERS
   ─────────────────────────────────────────────────────────── */
function buildEQSliders(){
  ['eqOD_sliders','eqOS_sliders'].forEach((id,ci)=>{
    const c=document.getElementById(id);c.innerHTML='';
    const data=ci===0?eqOD:eqOS;
    const col=ci===0?'#c0392b':'#2980b9';
    FL.forEach((lbl,i)=>{
      const d=document.createElement('div');d.className='eq-col';
      const v=data[i];
      d.innerHTML=`<div class="val" id="${id}_v${i}" style="color:${Math.abs(v)>3?(v>0?'#1d9e75':'#e24b4a'):'#4a4a4a'}">${v>0?'+':''}${v}</div>
        <input type="range" min="-30" max="30" value="${v}" step="1"
          oninput="setEQ(${ci},${i},this.value)"
          style="accent-color:${col}">
        <div class="lbl">${lbl}</div>`;
      c.appendChild(d);
    });
  });
}

function setEQ(ch,i,v){
  v=parseInt(v);
  if(ch===0){eqOD[i]=v;}else{eqOS[i]=v;}
  const id=(ch===0?'eqOD_sliders':'eqOS_sliders')+'_v'+i;
  const el=document.getElementById(id);
  if(el){el.textContent=(v>0?'+':'')+v;el.style.color=Math.abs(v)>3?(v>0?'#1d9e75':'#e24b4a'):'#4a4a4a';}
  if(actx) applyEQtoNodes();
}

function loadEQFromProfile(){
  /* Carica EQ da variabile globale iniettata da Python */
  if(window._eqOD && window._eqOS){
    eqOD=[...window._eqOD];
    eqOS=[...window._eqOS];
    buildEQSliders();
    document.getElementById('eqSt').textContent='EQ caricato da profilo paziente.';
    if(actx) applyEQtoNodes();
  } else {
    document.getElementById('eqSt').textContent='Nessun profilo EQ disponibile. Esegui prima il test tonale.';
  }
}

function resetEQ(){
  eqOD=new Array(11).fill(0);
  eqOS=new Array(11).fill(0);
  buildEQSliders();
  document.getElementById('eqSt').textContent='EQ reset — flat.';
  if(actx) applyEQtoNodes();
}

/* ───────────────────────────────────────────────────────────
   WEBAUDIO: INIZIALIZZAZIONE
   ─────────────────────────────────────────────────────────── */
function initAudioGraph(){
  if(actx) actx.close();
  actx = new(window.AudioContext||window.webkitAudioContext)();

  masterGain  = actx.createGain();
  masterGain.gain.value = parseFloat(document.getElementById('masterVol').value)/100;

  splitter    = actx.createChannelSplitter(2);
  merger      = actx.createChannelMerger(2);

  gainOD      = actx.createGain();
  gainOS      = actx.createGain();
  gateGainOD  = actx.createGain();
  gateGainOS  = actx.createGain();
  freqFilterOD= actx.createBiquadFilter();
  freqFilterOS= actx.createBiquadFilter();
  freqFilterOD.type = freqFilterOS.type = 'peaking';

  delayNodeAir  = actx.createDelay(1.0);
  delayNodeBone = actx.createDelay(1.0);
  analyserOD    = actx.createAnalyser();
  analyserOS    = actx.createAnalyser();
  analyserOD.fftSize = analyserOS.fftSize = 256;

  /* EQ filters */
  eqFiltersOD = FREQS.map(f=>{
    const n=actx.createBiquadFilter();n.type='peaking';n.frequency.value=f;n.Q.value=1.4;return n;
  });
  eqFiltersOS = FREQS.map(f=>{
    const n=actx.createBiquadFilter();n.type='peaking';n.frequency.value=f;n.Q.value=1.4;return n;
  });

  /* Binaurale */
  binGain = actx.createGain();
  binGain.gain.value = parseFloat(document.getElementById('binVol').value)/100;

  applyEQtoNodes();
  applyGating();
  applyDelay();
}

function connectGraph(){
  if(!srcNode || !actx) return;

  srcNode.disconnect();
  srcNode.connect(splitter);

  /* OD chain */
  let nodeOD = splitter;
  // EQ OD
  let prev = {connect:(n)=>splitter.connect(n,0)};
  eqFiltersOD.forEach((f,i)=>{
    if(i===0) splitter.connect(f,0);
    else eqFiltersOD[i-1].connect(f);
  });
  const lastEQOD = eqFiltersOD[eqFiltersOD.length-1];
  lastEQOD.connect(gateGainOD);
  gateGainOD.connect(freqFilterOD);
  freqFilterOD.connect(gainOD);
  gainOD.connect(delayNodeAir);
  delayNodeAir.connect(analyserOD);
  analyserOD.connect(merger,0,0);

  /* OS chain */
  eqFiltersOS.forEach((f,i)=>{
    if(i===0) splitter.connect(f,1);
    else eqFiltersOS[i-1].connect(f);
  });
  const lastEQOS = eqFiltersOS[eqFiltersOS.length-1];
  lastEQOS.connect(gateGainOS);
  gateGainOS.connect(freqFilterOS);
  freqFilterOS.connect(gainOS);
  gainOS.connect(delayNodeBone);
  delayNodeBone.connect(analyserOS);
  analyserOS.connect(merger,0,1);

  merger.connect(masterGain);
  masterGain.connect(actx.destination);

  /* Binaurale layer */
  if(gBinaural) connectBinaural();
}

/* ───────────────────────────────────────────────────────────
   EQ APPLY
   ─────────────────────────────────────────────────────────── */
function applyEQtoNodes(){
  eqFiltersOD.forEach((f,i)=>f.gain.value=eqOD[i]);
  eqFiltersOS.forEach((f,i)=>f.gain.value=eqOS[i]);
}

/* ───────────────────────────────────────────────────────────
   GATING
   ─────────────────────────────────────────────────────────── */
function applyGating(){
  if(!actx) return;
  const atten = parseFloat(document.getElementById('gAtten').value);
  const attenLinear = Math.pow(10,-atten/20);
  const lissage = parseFloat(document.getElementById('lissage').value)/1000;
  const tornante = parseFloat(document.getElementById('fTornante').value);
  const fattenStr = document.getElementById('fAtten').value.split(',');
  const fattenMin = parseFloat(fattenStr[0]);
  const fattenMax = parseFloat(fattenStr[1]);
  freqFilterOD.frequency.value = freqFilterOS.frequency.value = tornante;
  freqFilterOD.gain.value = freqFilterOS.gain.value = -((fattenMin+fattenMax)/2);

  if(gateTimer) clearInterval(gateTimer);
  let odHigh=true;
  function tick(){
    if(!sessRunning||sessPaused) return;
    const gMin=parseFloat(document.getElementById('gMin').value)*1000;
    const gMax=parseFloat(document.getElementById('gMax').value)*1000;
    const delay=gAlea?(gMin+Math.random()*(gMax-gMin)):gMin;
    const now=actx.currentTime;
    if(gGD){
      if(odHigh){
        gateGainOD.gain.linearRampToValueAtTime(1.0,now+lissage);
        gateGainOS.gain.linearRampToValueAtTime(attenLinear,now+lissage);
      } else {
        gateGainOD.gain.linearRampToValueAtTime(attenLinear,now+lissage);
        gateGainOS.gain.linearRampToValueAtTime(1.0,now+lissage);
      }
      odHigh=!odHigh;
    } else {
      const amp=Math.random()<0.5?1.0:attenLinear;
      gateGainOD.gain.linearRampToValueAtTime(amp,now+lissage);
      gateGainOS.gain.linearRampToValueAtTime(amp,now+lissage);
    }
    const freqAtten=-((fattenMin+Math.random()*(fattenMax-fattenMin)));
    freqFilterOD.gain.setTargetAtTime(freqAtten,now,lissage+0.05);
    freqFilterOS.gain.setTargetAtTime(freqAtten,now,lissage+0.05);
    setTimeout(tick,delay);
  }
  if(sessRunning) tick();
}

function updLissage(v){
  document.getElementById('lissageV').textContent=v+'ms';
}

/* ───────────────────────────────────────────────────────────
   DELAY
   ─────────────────────────────────────────────────────────── */
function applyDelay(){
  if(!actx) return;
  const air=parseFloat(document.getElementById('delayAir').value)/1000;
  const bone=parseFloat(document.getElementById('delayBone').value)/1000;
  delayNodeAir.delayTime.value=air;
  delayNodeBone.delayTime.value=bone;
}

/* ───────────────────────────────────────────────────────────
   BINAURALE
   ─────────────────────────────────────────────────────────── */
const PRESETS = {
  'Delta (1.5-3 Hz) — Sonno profondo / autoguarigione': {beat:2,carrier:100},
  'Theta (4-7 Hz) — Meditazione / creativita':          {beat:5,carrier:200},
  'Alfa (8-12 Hz) — Rilassamento / creativita':         {beat:10,carrier:200},
  'Beta basso (13-20 Hz) — Focus / concentrazione':     {beat:15,carrier:300},
  'Beta alto (20-39 Hz) — Veglia / attivita fisica':    {beat:25,carrier:300},
  'Gamma (40+ Hz) — Alta cognizione':                   {beat:40,carrier:400},
  'Personalizzato':                                      {beat:10,carrier:200},
};

function loadPreset(){
  const p=document.getElementById('binPreset').value;
  const d=PRESETS[p]||{beat:10,carrier:200};
  document.getElementById('binCarrier').value=d.carrier;
  document.getElementById('binBeat').value=d.beat;
  document.getElementById('binCarrierV').textContent=d.carrier+' Hz';
  document.getElementById('binBeatV').textContent=parseFloat(d.beat).toFixed(1)+' Hz';
  updBinaural();
}

function updBinaural(){
  const carrier=parseFloat(document.getElementById('binCarrier').value);
  const beat=parseFloat(document.getElementById('binBeat').value);
  const vol=parseFloat(document.getElementById('binVol').value);
  document.getElementById('binCarrierV').textContent=Math.round(carrier)+' Hz';
  document.getElementById('binBeatV').textContent=beat.toFixed(1)+' Hz';
  document.getElementById('binVolV').textContent=Math.round(vol)+'%';
  document.getElementById('binInfo').textContent=
    `Carrier OD: ${Math.round(carrier)} Hz — OS: ${Math.round(carrier+beat)} Hz — Beat: ${beat.toFixed(1)} Hz`;
  if(actx && gBinaural){
    if(binOscOD) binOscOD.frequency.value=carrier;
    if(binOscOS) binOscOS.frequency.value=carrier+beat;
    if(binGain)  binGain.gain.value=vol/100*0.15;
  }
  drawBinauralWave(carrier,beat);
}

function connectBinaural(){
  if(binOscOD){try{binOscOD.stop();}catch(e){}}
  if(binOscOS){try{binOscOS.stop();}catch(e){}}
  const carrier=parseFloat(document.getElementById('binCarrier').value);
  const beat=parseFloat(document.getElementById('binBeat').value);
  const vol=parseFloat(document.getElementById('binVol').value);

  binOscOD=actx.createOscillator();
  binOscOS=actx.createOscillator();
  binOscOD.type=binOscOS.type='sine';
  binOscOD.frequency.value=carrier;
  binOscOS.frequency.value=carrier+beat;
  if(!binGain){binGain=actx.createGain();}
  binGain.gain.value=vol/100*0.15;

  const binSplitter=actx.createChannelSplitter(1);
  const binMerger=actx.createChannelMerger(2);
  binOscOD.connect(binGain);
  binOscOS.connect(binGain);
  binGain.connect(merger,0,0);
  binGain.connect(merger,0,1);

  /* Override: OD solo carrier, OS solo carrier+beat */
  binOscOD.disconnect();binOscOS.disconnect();
  const gBinOD=actx.createGain();const gBinOS=actx.createGain();
  gBinOD.gain.value=gBinOS.gain.value=vol/100*0.12;
  binOscOD.connect(gBinOD);
  binOscOS.connect(gBinOS);
  gBinOD.connect(actx.destination); /* canale OD via pannig */
  gBinOS.connect(actx.destination);
  const panOD=actx.createStereoPanner();panOD.pan.value=0.9;
  const panOS=actx.createStereoPanner();panOS.pan.value=-0.9;
  binOscOD.disconnect();binOscOS.disconnect();
  binOscOD.connect(gBinOD);gBinOD.connect(panOD);panOD.connect(masterGain);
  binOscOS.connect(gBinOS);gBinOS.connect(panOS);panOS.connect(masterGain);

  binOscOD.start();binOscOS.start();
  document.getElementById('binInfo').style.cssText='font-size:11px;padding:5px;border-radius:6px;background:#e1f5ee;color:#0f6e56;margin:5px 0';
}

function drawBinauralWave(carrier,beat){
  const cv=document.getElementById('binCanvas');
  const ctx=cv.getContext('2d');
  cv.width=cv.parentElement.clientWidth;cv.height=40;
  const W=cv.width,H=cv.height;
  ctx.clearRect(0,0,W,H);
  /* Simula l'envelope del battimento */
  ctx.beginPath();
  for(let x=0;x<W;x++){
    const t=x/W*4;
    const env=0.5*(1+Math.cos(2*Math.PI*beat*t/carrier*10));
    const y=H/2-env*(H/2-4)*Math.sin(2*Math.PI*t*2);
    x===0?ctx.moveTo(x,y):ctx.lineTo(x,y);
  }
  ctx.strokeStyle='#1d9e75';ctx.lineWidth=1.5;ctx.stroke();
}

/* ───────────────────────────────────────────────────────────
   CARICAMENTO AUDIO
   ─────────────────────────────────────────────────────────── */
function loadAudio(){
  const url=document.getElementById('audioUrl').value.trim();
  if(!url){setSt('audioSt','Inserisci un URL valido.','err');return;}
  setSt('audioSt','Caricamento in corso...','info');
  if(!actx) initAudioGraph();
  fetch(url)
    .then(r=>{
      if(!r.ok) throw new Error('HTTP '+r.status);
      return r.arrayBuffer();
    })
    .then(buf=>actx.decodeAudioData(buf))
    .then(decoded=>{
      audioBuffer=decoded;
      const dur=Math.floor(decoded.duration);
      const m=Math.floor(dur/60),s=dur%60;
      setSt('audioSt',`Caricato: ${decoded.numberOfChannels}ch ${decoded.sampleRate}Hz ${m}m${s}s`,'ok');
      log(`Audio caricato: ${url.split('/').pop()}`);
    })
    .catch(e=>setSt('audioSt','Errore caricamento: '+e.message,'err'));
}

function setMasterVol(v){
  document.getElementById('masterVolV').textContent=Math.round(v)+'%';
  if(masterGain) masterGain.gain.value=v/100;
}

/* ───────────────────────────────────────────────────────────
   SESSIONE
   ─────────────────────────────────────────────────────────── */
function startSess(){
  if(sessPaused){
    sessPaused=false;sessStart+=Date.now()-sessPauseAt;
    if(actx.state==='suspended') actx.resume();
    sessRunning=true;
    document.getElementById('sessStatus').textContent='In esecuzione';
    document.getElementById('btnStart').textContent='Avvia';
    document.getElementById('btnStart').disabled=true;
    applyGating();startVU();
    log('Seduta ripresa.');return;
  }
  if(sessRunning) return;
  if(!audioBuffer){setSt('audioSt','Carica prima un file audio.','warn');return;}
  if(!actx) initAudioGraph();
  if(actx.state==='suspended') actx.resume();

  srcNode=actx.createBufferSource();
  srcNode.buffer=audioBuffer;
  srcNode.loop=true;
  connectGraph();
  srcNode.start();

  sessRunning=true;sessStart=Date.now();
  document.getElementById('sessStatus').textContent='In esecuzione';
  document.getElementById('btnStart').disabled=true;
  sessTimer=setInterval(()=>{
    if(sessPaused) return;
    const el=Math.floor((Date.now()-sessStart)/1000);
    const tot=parseInt(document.getElementById('sessDur').value);
    const h=Math.floor(el/3600),m=Math.floor((el%3600)/60),s=el%60;
    document.getElementById('timerDisp').textContent=
      `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
    if(el>=tot) stopSess();
  },500);

  applyGating();startVU();
  log(`Seduta avviata — ${document.getElementById('sessDur').value/60} min — paziente: ${document.getElementById('pazNome').value||'N/D'}`);
}

function pauseSess(){
  if(!sessRunning) return;
  sessPaused=true;sessPauseAt=Date.now();
  if(actx) actx.suspend();
  document.getElementById('sessStatus').textContent='In pausa';
  document.getElementById('btnStart').textContent='Riprendi';
  document.getElementById('btnStart').disabled=false;
  log('Pausa.');
}

function stopSess(){
  sessRunning=false;sessPaused=false;
  clearInterval(sessTimer);clearTimeout(gateTimer);clearInterval(vuTimer);
  if(srcNode){try{srcNode.stop();}catch(e){}}
  if(binOscOD){try{binOscOD.stop();}catch(e){}}
  if(binOscOS){try{binOscOS.stop();}catch(e){}}
  if(actx) actx.suspend();
  document.getElementById('timerDisp').textContent='00:00:00';
  document.getElementById('sessStatus').textContent='Fermato';
  document.getElementById('btnStart').disabled=false;
  document.getElementById('btnStart').textContent='Avvia';
  document.getElementById('vuOD').style.width='0%';
  document.getElementById('vuOS').style.width='0%';
  log('Seduta terminata.');
}

/* ───────────────────────────────────────────────────────────
   VU METER
   ─────────────────────────────────────────────────────────── */
function startVU(){
  if(vuTimer) clearInterval(vuTimer);
  const dataOD=new Uint8Array(analyserOD.frequencyBinCount);
  const dataOS=new Uint8Array(analyserOS.frequencyBinCount);
  vuTimer=setInterval(()=>{
    if(!sessRunning||sessPaused) return;
    analyserOD.getByteTimeDomainData(dataOD);
    analyserOS.getByteTimeDomainData(dataOS);
    const rmsOD=Math.sqrt(dataOD.reduce((s,v)=>s+(v-128)**2,0)/dataOD.length)/128;
    const rmsOS=Math.sqrt(dataOS.reduce((s,v)=>s+(v-128)**2,0)/dataOS.length)/128;
    document.getElementById('vuOD').style.width=Math.min(100,rmsOD*400)+'%';
    document.getElementById('vuOS').style.width=Math.min(100,rmsOS*400)+'%';
  },60);
}

/* ───────────────────────────────────────────────────────────
   TOGGLES
   ─────────────────────────────────────────────────────────── */
function toggleBtn(id,lblId,fn){
  const t=document.getElementById(id);
  const on=t.classList.contains('on');
  t.className='toggle '+(on?'off':'on');
  fn(!on);
  if(lblId) document.getElementById(lblId).textContent=fn.name.replace('toggle','')+(!on?' attivo':' off');
}
function toggleGD(v){gGD=v;if(sessRunning) applyGating();}
function toggleAlea(v){gAlea=v;}
function toggleBinaural(v){
  gBinaural=v;
  document.getElementById('togBinlbl').textContent='Binaurale '+(v?'attivo':'off');
  if(v&&actx&&sessRunning) connectBinaural();
  else if(!v){if(binOscOD)try{binOscOD.stop();}catch(e){}if(binOscOS)try{binOscOS.stop();}catch(e){}}
}

/* ───────────────────────────────────────────────────────────
   UTILITY
   ─────────────────────────────────────────────────────────── */
function setSt(id,txt,type){
  const el=document.getElementById(id);
  if(!el) return;
  el.textContent=txt;
  el.className='status '+type;
}

function log(msg){
  const el=document.getElementById('sessLog');
  const ts=new Date().toLocaleTimeString('it-IT',{hour12:false});
  el.innerHTML+=`<div>[${ts}] ${msg}</div>`;
  el.scrollTop=el.scrollHeight;
}

/* ───────────────────────────────────────────────────────────
   INIT
   ─────────────────────────────────────────────────────────── */
buildEQSliders();
loadPreset();
drawBinauralWave(200,10);

/* Inietta EQ da Python se disponibile */
document.addEventListener('DOMContentLoaded',()=>{
  if(window._eqOD) loadEQFromProfile();
});
</script></body></html>"""


def _get_eq_paziente(paz_id):
    """Legge l'ultimo profilo EQ dal DB per questo paziente."""
    try:
        import sys, os
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if root not in sys.path: sys.path.insert(0, root)
        from app_patched import get_connection
        conn = get_connection()
        cur  = conn.cursor()
        ph   = "%s" if "Pg" in type(conn).__name__ else "?"
        cur.execute(
            f"SELECT dati_json FROM diagnostica_uditiva "
            f"WHERE paziente_id={ph} AND tipo='Audiogramma' "
            f"ORDER BY id DESC LIMIT 1", (paz_id,))
        row = cur.fetchone()
        if row:
            dati = json.loads(row[0] if not isinstance(row, dict) else row.get("dati_json","{}"))
            eq_od = dati.get("eq_od", [0]*11)
            eq_os = dati.get("eq_os", [0]*11)
            # Normalizza a lista di 11 int
            eq_od = [int(v) if v is not None else 0 for v in eq_od]
            eq_os = [int(v) if v is not None else 0 for v in eq_os]
            return eq_od, eq_os
    except Exception:
        pass
    return [0]*11, [0]*11


def _salva_seduta(conn, paz_id, durata_min, parametri, operatore, note=""):
    """Salva log seduta nel DB."""
    try:
        cur = conn.cursor()
        pg  = "Pg" in type(conn).__name__
        ph  = ", ".join(["%s" if pg else "?"]*6)
        cur.execute(
            f"INSERT INTO stimolazione_uditiva "
            f"(paziente_id, data_seduta, durata_min, operatore, parametri_json, note) "
            f"VALUES ({ph})",
            (paz_id,
             __import__('datetime').date.today().isoformat(),
             durata_min, operatore,
             json.dumps(parametri), note))
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Errore salvataggio seduta: {e}")
        return False


def _init_stim_db(conn):
    """Crea tabella stimolazione se non esiste."""
    try:
        raw = getattr(conn, "_conn", conn)
        cur = raw.cursor() if hasattr(raw, "cursor") else conn.cursor()
        pg  = "Pg" in type(conn).__name__
        if pg:
            cur.execute("""CREATE TABLE IF NOT EXISTS stimolazione_uditiva (
                id BIGSERIAL PRIMARY KEY,
                paziente_id BIGINT,
                data_seduta TEXT,
                durata_min INTEGER,
                operatore TEXT,
                parametri_json TEXT,
                note TEXT)""")
        else:
            cur.execute("""CREATE TABLE IF NOT EXISTS stimolazione_uditiva (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                paziente_id INTEGER,
                data_seduta TEXT,
                durata_min INTEGER,
                operatore TEXT,
                parametri_json TEXT,
                note TEXT)""")
        try: raw.commit()
        except: conn.commit()
    except Exception:
        pass


def ui_stimolazione_passiva(conn=None):
    """UI principale del modulo stimolazione passiva."""
    st.header("Stimolazione Uditiva Passiva")
    st.caption(
        "Motore Hipérion WebAudio · EQ paziente · Gate ampiezza/frequenze · "
        "Binaurale Brainwave Entrainment · Real-time browser"
    )

    if conn is None:
        try:
            import sys, os
            root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            if root not in sys.path: sys.path.insert(0, root)
            from app_patched import get_connection
            conn = get_connection()
        except Exception:
            pass

    if conn:
        _init_stim_db(conn)

    # Selezione paziente
    paz_id = None
    if conn:
        try:
            cur = conn.cursor()
            try:
                cur.execute('SELECT id, "Cognome", "Nome" FROM "Pazienti" ORDER BY "Cognome","Nome"')
            except Exception:
                cur.execute("SELECT id, Cognome, Nome FROM Pazienti ORDER BY Cognome, Nome")
            pazienti = cur.fetchall()
            if pazienti:
                opts = [(int(r[0]), f"{r[1]} {r[2]}") for r in pazienti]
                c1, c2 = st.columns([3,1])
                with c1:
                    sel = st.selectbox("Paziente", options=opts,
                                       format_func=lambda x: x[1],
                                       key="stim_paz")
                    paz_id = sel[0]
                with c2:
                    op = st.text_input("Operatore", "", key="stim_op")
        except Exception as e:
            st.warning(f"Pazienti non disponibili: {e}")
            op = st.text_input("Operatore", "", key="stim_op")
    else:
        op = st.text_input("Operatore", "", key="stim_op")

    # Leggi profilo EQ del paziente
    eq_od, eq_os = [0]*11, [0]*11
    if paz_id and conn:
        eq_od, eq_os = _get_eq_paziente(paz_id)

    # Inietta EQ nel componente HTML via JavaScript
    eq_inject = f"""
<script>
window._eqOD = {json.dumps(eq_od)};
window._eqOS = {json.dumps(eq_os)};
</script>
"""
    full_html = STIM_HTML.replace('</body></html>', eq_inject + '</body></html>')

    import streamlit.components.v1 as components
    components.html(full_html, height=1600, scrolling=True)

    st.divider()

    # Salva configurazione seduta
    with st.expander("Salva configurazione seduta", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            dur_min = st.number_input("Durata seduta (min)", 15, 180, 60,
                                       key="stim_dur_save")
        with c2:
            nota_sed = st.text_input("Note seduta", key="stim_note_save")

        if st.button("Salva seduta nel DB", type="primary", key="stim_save"):
            if conn and paz_id:
                params = {
                    "eq_od": eq_od, "eq_os": eq_os,
                    "note": nota_sed
                }
                if _salva_seduta(conn, paz_id, dur_min, params, op, nota_sed):
                    st.success("Seduta salvata.")
            else:
                st.warning("Seleziona un paziente per salvare la seduta.")
