# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════╗
║  PNEV CAPTURE — strato riutilizzabile di analisi del movimento       ║
║                                                                      ║
║  Cattura in background (webcam ora, Tobii in seguito) durante un     ║
║  test e ne ricava metriche del movimento:                            ║
║    • Occhi: posizione iride (sguardo), apertura palpebrale,          ║
║      fissazioni/saccadi stimate                                      ║
║    • Volto/bocca: apertura bocca (jawOpen), simmetria, blendshapes   ║
║      (base per lingua/muscoli che aggiungeremo)                      ║
║                                                                      ║
║  USO (da qualsiasi test):                                            ║
║      from modules.pnev_capture import render_capture                 ║
║      render_capture("DEM", paziente_nome="Rossi Mario", height=560)  ║
║                                                                      ║
║  Tecnica: MediaPipe FaceLandmarker (browser, CDN) + MediaRecorder    ║
║  per il video. A fine sessione il clinico scarica:                   ║
║    • <sessione>.json  (serie temporali + metriche)                   ║
║    • <sessione>.webm  (video grezzo, opzionale)                      ║
║  Il salvataggio automatico nella cartella sarà il passo successivo.  ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import json
import streamlit as st
import streamlit.components.v1 as components


def render_capture(test_id: str, paziente_nome: str = "",
                   height: int = 150, salva_video: bool = True):
    """Inserisce il pulsante che apre l'analisi movimento in una finestra a sé.

    La cattura webcam richiede un contesto top-level (l'iframe di Streamlit
    non concede la telecamera), quindi l'app si apre in una finestra popup.
    """
    cfg = {
        "testId": test_id,
        "paziente": paziente_nome or "paziente",
        "salvaVideo": bool(salva_video),
    }
    app = _CAPTURE_APP.replace("__CFG__", json.dumps(cfg))
    app = app.replace("__VIDBTN__", "inline-block" if salva_video else "none")
    launcher = _LAUNCHER.replace("__APP__", json.dumps(app).replace("</", "<\\/"))
    components.html(launcher, height=height)


_LAUNCHER = r"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
  body{font-family:-apple-system,Segoe UI,Roboto,sans-serif;margin:0;padding:10px;color:#e6edf3}
  button{padding:11px 18px;border:none;border-radius:8px;cursor:pointer;font-size:15px;font-weight:bold;background:#6e40c9;color:#fff}
  p{font-size:12.5px;color:#8b949e;margin:8px 2px 0}
</style></head><body>
<button onclick="openCap()">🎥 Apri analisi movimenti (finestra a tutto schermo)</button>
<p>Si apre in una finestra separata (puoi metterla sul monitor del paziente). Consenti telecamera e popup.</p>
<script>
const APP = __APP__;
function openCap(){
  const w = window.open('', 'pnev_capture', 'width=980,height=760');
  if(!w){ alert('Consenti le finestre popup per aprire l\'analisi.'); return; }
  w.document.open(); w.document.write(APP); w.document.close();
  w.focus();
}
</script></body></html>"""


_CAPTURE_APP = r"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>PNEV Capture</title><style>
  body{font-family:-apple-system,Segoe UI,Roboto,sans-serif;margin:0;padding:12px;background:#0d1117;color:#e6edf3}
  .bar{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:10px}
  button{padding:9px 15px;border:none;border-radius:7px;cursor:pointer;font-size:14px;font-weight:bold;color:#fff}
  #start{background:#2ea44f}#stop{background:#cf222e}#dl{background:#0969da}#dlv{background:#6e40c9}
  button:disabled{opacity:.4;cursor:not-allowed}
  .pill{display:inline-flex;align-items:center;gap:6px;font-size:13px;padding:4px 10px;border-radius:20px;background:#161b22;border:1px solid #30363d}
  .rec{width:10px;height:10px;border-radius:50%;background:#cf222e;animation:b 1s infinite}
  @keyframes b{50%{opacity:.25}}
  .wrap{display:flex;gap:14px;flex-wrap:wrap}
  .vid{position:relative;width:340px;height:255px;background:#000;border-radius:8px;overflow:hidden}
  video,canvas{position:absolute;left:0;top:0;width:100%;height:100%}
  .stats{flex:1;min-width:240px;font-size:13px;line-height:1.7}
  .stats b{color:#7ee787}
  .k{display:inline-block;min-width:160px;color:#8b949e}
  .src{font-size:12px;color:#8b949e}
  .msg{font-size:13px;color:#f0883e;margin-top:8px}
</style></head><body>
<div class="bar">
  <button id="start">▶ Avvia cattura</button>
  <button id="stop" disabled>⏹ Stop</button>
  <span class="pill"><span id="srcdot" class="rec" style="background:#8b949e;animation:none"></span><span id="src" class="src">sorgente: —</span></span>
  <span class="pill" id="recpill" style="display:none"><span class="rec"></span> registrazione</span>
  <button id="dl" disabled>⬇️ Dati (JSON)</button>
  <button id="dlv" disabled style="display:__VIDBTN__">⬇️ Video</button>
</div>
<div class="wrap">
  <div class="vid"><video id="cam" autoplay playsinline muted></video><canvas id="ov"></canvas></div>
  <div class="stats">
    <div><span class="k">Stato</span> <b id="st">in attesa</b></div>
    <div><span class="k">Frame analizzati</span> <b id="nf">0</b></div>
    <div><span class="k">Sguardo (x,y)</span> <b id="gz">—</b></div>
    <div><span class="k">Apertura occhi</span> <b id="eo">—</b></div>
    <div><span class="k">Apertura bocca</span> <b id="mo">—</b></div>
    <div><span class="k">Simmetria volto</span> <b id="sy">—</b></div>
    <div><span class="k">Saccadi stimate</span> <b id="sc">0</b></div>
    <div class="msg" id="msg"></div>
  </div>
</div>
<script type="module">
const CFG = __CFG__;
document.getElementById('src').textContent = 'sorgente: rilevamento…';
const msg = (t)=>document.getElementById('msg').textContent=t;

let landmarker=null, stream=null, raf=null, running=false;
let rec=null, chunks=[], videoBlob=null;
let series=[], nframes=0, saccades=0, lastGaze=null, t0=0;

// 1) Rilevamento sorgente: prova il "ponte Tobii" locale, altrimenti webcam
async function detectSource(){
  try{
    const r = await Promise.race([
      fetch('http://127.0.0.1:9111/ping', {mode:'cors'}),
      new Promise((_,x)=>setTimeout(()=>x('to'),600))
    ]);
    if(r && r.ok){ return 'tobii'; }
  }catch(e){}
  return 'webcam';
}

async function loadLandmarker(){
  const vision = await import('https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/vision_bundle.mjs');
  const { FaceLandmarker, FilesetResolver } = vision;
  const fileset = await FilesetResolver.forVisionTasks(
    'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/wasm');
  landmarker = await FaceLandmarker.createFromOptions(fileset, {
    baseOptions:{ modelAssetPath:'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task' },
    outputFaceBlendshapes:true, runningMode:'VIDEO', numFaces:1
  });
}

const cam = document.getElementById('cam');
const ov = document.getElementById('ov');
const octx = ov.getContext('2d');

function dist(a,b){return Math.hypot(a.x-b.x,a.y-b.y);}

function analyze(res, ts){
  if(!res || !res.faceLandmarks || !res.faceLandmarks.length) return;
  const L = res.faceLandmarks[0];
  if(!L || L.length < 468) return;
  const irisL = L[468]||L[159], irisR = L[473]||L[386];
  if(!irisL || !irisR) return;
  const gx = ((irisL.x + irisR.x)/2);
  const gy = ((irisL.y + irisR.y)/2);
  // apertura occhi: distanza palpebra sup/inf (33-159 sx, 263-386 dx) normalizzata
  const eo = ((dist(L[159],L[145]) + dist(L[386],L[374]))/2);
  // apertura bocca / simmetria da blendshapes se presenti
  let jaw=0, sym=0;
  const bs = res.faceBlendshapes && res.faceBlendshapes[0];
  if(bs){
    const get=(n)=>{const c=bs.categories.find(x=>x.categoryName===n);return c?c.score:0;};
    jaw = get('jawOpen');
    sym = Math.abs(get('mouthLeft')-get('mouthRight')) + Math.abs(get('eyeBlinkLeft')-get('eyeBlinkRight'));
  }
  // saccade stimata: salto di sguardo sopra soglia
  if(lastGaze){ const d=Math.hypot(gx-lastGaze.x, gy-lastGaze.y); if(d>0.03) saccades++; }
  lastGaze={x:gx,y:gy};
  nframes++;
  series.push({t:+(ts-t0).toFixed(0), gx:+gx.toFixed(4), gy:+gy.toFixed(4),
               eo:+eo.toFixed(4), jaw:+jaw.toFixed(3), sym:+sym.toFixed(3)});
  // UI
  document.getElementById('nf').textContent=nframes;
  document.getElementById('gz').textContent=gx.toFixed(2)+', '+gy.toFixed(2);
  document.getElementById('eo').textContent=eo.toFixed(3);
  document.getElementById('mo').textContent=jaw.toFixed(2);
  document.getElementById('sy').textContent=sym.toFixed(2);
  document.getElementById('sc').textContent=saccades;
  // overlay puntino sguardo
  octx.clearRect(0,0,ov.width,ov.height);
  octx.fillStyle='#2ea44f';
  octx.beginPath(); octx.arc(gx*ov.width, gy*ov.height, 6, 0, 6.28); octx.fill();
}

function loop(){
  if(!running) return;
  try{
    if(landmarker && cam.readyState>=2){
      const ts = performance.now();
      const res = landmarker.detectForVideo(cam, ts);
      analyze(res, ts);
    }
  }catch(e){ /* salta la frame problematica, non fermare la cattura */ }
  raf = requestAnimationFrame(loop);
}

document.getElementById('start').onclick = async ()=>{
  document.getElementById('st').textContent='avvio…';
  const src = await detectSource();
  document.getElementById('src').textContent = 'sorgente: '+(src==='tobii'?'Tobii (ponte locale)':'webcam');
  document.getElementById('srcdot').style.background = src==='tobii' ? '#7ee787':'#0969da';
  document.getElementById('srcdot').style.animation='none';
  if(src==='tobii'){ msg('Ponte Tobii rilevato: integrazione dedicata in arrivo. Per ora uso la webcam come fallback.'); }
  try{
    if(!landmarker){ document.getElementById('st').textContent='carico modello…'; await loadLandmarker(); }
    stream = await navigator.mediaDevices.getUserMedia({video:true, audio:false});
    cam.srcObject = stream;
    await cam.play();
    ov.width=cam.videoWidth||340; ov.height=cam.videoHeight||255;
    // video opzionale
    if(CFG.salvaVideo && window.MediaRecorder){
      chunks=[]; rec=new MediaRecorder(stream,{mimeType:'video/webm'});
      rec.ondataavailable=e=>{if(e.data.size)chunks.push(e.data);};
      rec.onstop=()=>{ videoBlob=new Blob(chunks,{type:'video/webm'}); document.getElementById('dlv').disabled=false; };
      rec.start();
      document.getElementById('recpill').style.display='inline-flex';
    }
    series=[]; nframes=0; saccades=0; lastGaze=null; t0=performance.now();
    running=true; document.getElementById('st').textContent='registrazione attiva';
    document.getElementById('start').disabled=true; document.getElementById('stop').disabled=false;
    loop();
  }catch(e){
    document.getElementById('st').textContent='errore';
    let extra='';
    if(e && (e.name==='NotReadableError'||/Could not start/i.test(e.message)))
      extra=' — la telecamera è occupata da un\'altra app o scheda (FaceTime, Zoom, Photo Booth, un altro tab): chiudila e riprova.';
    else if(e && e.name==='NotAllowedError')
      extra=' — permesso negato: consenti la telecamera al browser (Impostazioni macOS → Privacy → Fotocamera).';
    else if(e && e.name==='NotFoundError')
      extra=' — nessuna telecamera trovata.';
    msg('Impossibile avviare: '+(e?e.message:e)+'.'+extra);
  }
};

document.getElementById('stop').onclick = ()=>{
  running=false; if(raf) cancelAnimationFrame(raf);
  if(rec && rec.state!=='inactive') rec.stop();
  if(stream) stream.getTracks().forEach(t=>t.stop());
  document.getElementById('st').textContent='terminata';
  document.getElementById('recpill').style.display='none';
  document.getElementById('start').disabled=false; document.getElementById('stop').disabled=true;
  document.getElementById('dl').disabled=false;
};

document.getElementById('dl').onclick = ()=>{
  const dur = series.length? series[series.length-1].t : 0;
  const out = {
    test: CFG.testId, paziente: CFG.paziente, creato: new Date().toISOString(),
    durata_ms: dur, n_frame: nframes, saccadi_stimate: saccades,
    fps_medio: dur? +(nframes/(dur/1000)).toFixed(1):0,
    serie: series
  };
  const b = new Blob([JSON.stringify(out)], {type:'application/json'});
  const a = document.createElement('a'); a.href=URL.createObjectURL(b);
  a.download = 'pnev_'+CFG.testId+'_'+CFG.paziente.replace(/\s+/g,'_')+'.json'; a.click();
};
document.getElementById('dlv').onclick = ()=>{
  if(!videoBlob) return;
  const a=document.createElement('a'); a.href=URL.createObjectURL(videoBlob);
  a.download='pnev_'+CFG.testId+'_'+CFG.paziente.replace(/\s+/g,'_')+'.webm'; a.click();
};

detectSource().then(s=>{ document.getElementById('src').textContent='sorgente: '+(s==='tobii'?'Tobii pronto':'webcam'); });
</script></body></html>"""
