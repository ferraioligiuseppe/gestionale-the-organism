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

_HTML_AUDIOGRAMMA = '<!DOCTYPE html><html><head><meta charset="utf-8">\n<style>\n*{box-sizing:border-box;margin:0;padding:0;font-family:system-ui,sans-serif}\nbody{padding:10px;background:#f8f7f4;color:#1a1a1a}\n.tabs{display:flex;border-bottom:2px solid #d4cec5;margin-bottom:12px}\n.tab{padding:7px 13px;font-size:12px;cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-2px;color:#8a8a8a}\n.tab.active{color:#2d7d6f;font-weight:600;border-bottom-color:#2d7d6f}\n.section{display:none}.section.active{display:block}\n.card{background:#fff;border:1px solid #d4cec5;border-radius:10px;padding:12px 16px;margin-bottom:10px}\nh3{font-size:13px;font-weight:500;margin-bottom:3px}\n.cap{font-size:11px;color:#8a8a8a;margin-bottom:8px;line-height:1.4}\nbutton{font-family:inherit;font-size:11px;padding:5px 10px;border-radius:6px;border:1.5px solid #d4cec5;background:#fff;color:#4a4a4a;cursor:pointer;margin:2px}\nbutton:hover{background:#e8f3f1;border-color:#2d7d6f;color:#1a5248}\nbutton.primary{background:#2d7d6f;border-color:#2d7d6f;color:#fff}\nbutton.ear-od{border-color:#c0392b;color:#c0392b}button.ear-od.active{background:#c0392b;color:#fff}\nbutton.ear-os{border-color:#2980b9;color:#2980b9}button.ear-os.active{background:#2980b9;color:#fff}\n.fi-grid{display:grid;grid-template-columns:repeat(11,1fr);gap:3px;margin:5px 0}\n.fi{display:flex;flex-direction:column;align-items:center;gap:2px}\n.fi label{font-size:9px;color:#8a8a8a}\n.fi input{width:100%;padding:2px;border-radius:3px;border:1px solid #d4cec5;font-size:11px;text-align:center;background:#fff;color:#1a1a1a}\n.fi input.od{border-color:#c0392b;color:#c0392b}.fi input.os{border-color:#2980b9;color:#2980b9}\n.fi input.tom{border-color:#2d7d6f;color:#2d7d6f}\ncanvas{display:block;width:100%;border-radius:6px}\n.legend{display:flex;gap:14px;flex-wrap:wrap;margin:6px 0;font-size:10px;color:#8a8a8a}\n.leg{display:flex;align-items:center;gap:4px}\n.ll{width:20px;height:2px;border-radius:1px}\n.eq-grid{display:flex;gap:6px;justify-content:center;flex-wrap:wrap;margin:8px 0}\n.eq-bar{display:flex;flex-direction:column;align-items:center;gap:2px}\n.eq-track{width:18px;height:70px;background:#f0ede8;border-radius:3px;position:relative;overflow:hidden}\n.eq-fill{position:absolute;width:100%;border-radius:2px;transition:height .3s}\n.eq-val{font-size:11px;font-weight:500}\n.eq-lbl{font-size:9px;color:#8a8a8a}\n.sel-table{width:100%;border-collapse:collapse;font-size:11px;margin-top:6px}\n.sel-table th{background:#f0ede8;padding:4px 6px;text-align:center;font-weight:500;font-size:10px}\n.sel-table td{padding:2px 4px;text-align:center;border:0.5px solid #d4cec5}\n.sel-table td:first-child{text-align:left;font-weight:500;background:#f8f7f4;white-space:nowrap;padding:4px 8px}\nselect.sel{font-size:11px;padding:1px 2px;border-radius:3px;border:1px solid #d4cec5;background:#fff;color:#1a1a1a;width:42px}\n.status{font-size:11px;padding:5px 9px;border-radius:6px;margin:6px 0}\n.ok{background:#e8f3f1;color:#1a5248}.warn{background:#fef7ec;color:#7a4f0a}.info{background:#ebf5fb;color:#154360}\n.grid2{display:grid;grid-template-columns:1fr 1fr;gap:8px}\n.metric{background:#f8f7f4;border-radius:6px;padding:7px 10px}\n.metric .v{font-size:16px;font-weight:500}.metric .l{font-size:10px;color:#8a8a8a;margin-top:1px}\n</style></head><body>\n<div class="tabs">\n  <div class="tab active" onclick="sw(0)">Audiogramma</div>\n  <div class="tab" onclick="sw(1)">Delta EQ</div>\n  <div class="tab" onclick="sw(2)">Selettivita</div>\n  <div class="tab" onclick="sw(3)">Lateralita</div>\n</div>\n\n<div class="section active" id="t0">\n<div class="card">\n  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">\n    <div><h3>Audiogramma funzionale + curva Tomatis</h3>\n    <p class="cap">O = OD (rosso) &nbsp; X = OS (blu) &nbsp; Verde tratteggiato = target Tomatis</p></div>\n    <div>\n      <button class="ear-od active" id="bOD" onclick="setEar(\'OD\')">OD</button>\n      <button class="ear-os" id="bOS" onclick="setEar(\'OS\')">OS</button>\n      <button onclick="reset()" style="border-color:#e24b4a;color:#e24b4a;margin-left:4px">Reset</button>\n    </div>\n  </div>\n  <canvas id="cvA" height="300"></canvas>\n  <div class="legend">\n    <div class="leg"><div class="ll" style="background:#c0392b"></div>OD</div>\n    <div class="leg"><div class="ll" style="background:#2980b9"></div>OS</div>\n    <div class="leg"><div class="ll" style="background:#2d7d6f;border-top:2px dashed #2d7d6f;height:0"></div>Tomatis</div>\n  </div>\n</div>\n<div class="card">\n  <h3>Soglie dB HL &mdash; <span id="earLbl" style="color:#c0392b">OD</span></h3>\n  <div class="fi-grid" id="fiGrid"></div>\n</div>\n<div class="card">\n  <h3>Curva Tomatis (modificabile)</h3>\n  <p class="cap">Valori dB HL target per ogni frequenza. Default = curva standard Tomatis.</p>\n  <div class="fi-grid" id="tomGrid"></div>\n  <button onclick="resetTom()" style="margin-top:5px;font-size:10px">Ripristina standard</button>\n</div>\n</div>\n\n<div class="section" id="t1">\n<div class="card">\n  <h3>Delta EQ (curva Tomatis &minus; soglia paziente)</h3>\n  <p class="cap">Positivo = rinforzo (paziente sotto target) &nbsp; Negativo = attenuazione (paziente sopra target)</p>\n  <canvas id="cvEQ" height="240"></canvas>\n</div>\n<div class="card">\n  <h3>Barre EQ per frequenza</h3>\n  <div class="eq-grid" id="eqGrid"></div>\n  <div class="grid2" style="margin-top:8px">\n    <div class="metric"><div class="v" id="eqNote">-</div><div class="l">Indicazione clinica</div></div>\n    <div class="metric"><div class="v" id="eqDom">-</div><div class="l">Orecchio da privilegiare</div></div>\n  </div>\n  <div id="eqSt" class="status info">Inserisci le soglie per generare l EQ.</div>\n</div>\n</div>\n\n<div class="section" id="t2">\n<div class="card">\n  <h3>Selettivita uditiva</h3>\n  <p class="cap">BC = via ossea &nbsp; AC = via aerea &nbsp; O = ODX &nbsp; X = OSN &nbsp; OX = Entrambi</p>\n  <table class="sel-table">\n    <thead><tr><th></th><th>125</th><th>250</th><th>500</th><th>750</th><th>1k</th><th>1.5k</th><th>2k</th><th>3k</th><th>4k</th><th>6k</th><th>8k</th></tr></thead>\n    <tbody id="selBody"></tbody>\n  </table>\n</div>\n</div>\n\n<div class="section" id="t3">\n<div class="card">\n  <h3>Lateralita uditiva binaurale</h3>\n  <p class="cap">BPTA a 20 dB e a soglia &nbsp; O = ODX &nbsp; X = OSN &nbsp; OX = Entrambi</p>\n  <table class="sel-table">\n    <thead><tr><th></th><th>125</th><th>250</th><th>500</th><th>750</th><th>1k</th><th>1.5k</th><th>2k</th><th>3k</th><th>4k</th><th>6k</th><th>8k</th></tr></thead>\n    <tbody id="latBody"></tbody>\n  </table>\n</div>\n<div class="card" style="margin-top:8px">\n  <h3>Sintesi lateralita</h3>\n  <div class="grid2">\n    <div class="metric"><div class="v" id="latDom">-</div><div class="l">Orecchio dominante</div></div>\n    <div class="metric"><div class="v" id="latIdx">-</div><div class="l">Indice lateralita</div></div>\n  </div>\n</div>\n<div class="btn-row" style="margin-top:10px">\n  <button class="primary" onclick="saveAll()">Salva bilancio completo</button>\n</div>\n<div id="saved" class="status ok" style="display:none;margin-top:6px">Dati salvati nel gestionale.</div>\n</div>\n\n<script>\nconst FR=[125,250,500,750,1000,1500,2000,3000,4000,6000,8000];\nconst FL=[\'125\',\'250\',\'500\',\'750\',\'1k\',\'1.5k\',\'2k\',\'3k\',\'4k\',\'6k\',\'8k\'];\nconst TOM_STD=[-5,-8,-10,-12,-14,-15,-14,-15,-12,-8,-5];\nlet tom=[...TOM_STD];\nlet od=new Array(11).fill(null);\nlet os=new Array(11).fill(null);\nlet ear=\'OD\';\nlet eqOD=new Array(11).fill(0);\nlet eqOS=new Array(11).fill(0);\n\nfunction sw(n){document.querySelectorAll(\'.section\').forEach((s,i)=>s.classList.toggle(\'active\',i===n));document.querySelectorAll(\'.tab\').forEach((t,i)=>t.classList.toggle(\'active\',i===n));if(n===1){drawEQ();buildEQGrid();}if(n===2)buildSel();if(n===3)buildLat();}\n\nfunction setEar(e){ear=e;document.getElementById(\'bOD\').classList.toggle(\'active\',e===\'OD\');document.getElementById(\'bOS\').classList.toggle(\'active\',e===\'OS\');document.getElementById(\'earLbl\').textContent=e;document.getElementById(\'earLbl\').style.color=e===\'OD\'?\'#c0392b\':\'#2980b9\';buildFiGrid();}\n\nfunction buildFiGrid(){\n  const g=document.getElementById(\'fiGrid\');g.innerHTML=\'\';\n  FR.forEach((_,i)=>{const d=document.createElement(\'div\');d.className=\'fi\';\n    const cls=ear===\'OD\'?\'od\':\'os\';\n    const v=ear===\'OD\'?od[i]:os[i];\n    d.innerHTML=`<label>${FL[i]}</label><input type="number" class="${cls}" id="fi_${i}" value="${v??\'\'}" min="-20" max="90" step="5" placeholder="-" oninput="setV(${i},this.value)">`;\n    g.appendChild(d);});\n}\n\nfunction buildTomGrid(){\n  const g=document.getElementById(\'tomGrid\');g.innerHTML=\'\';\n  FR.forEach((_,i)=>{const d=document.createElement(\'div\');d.className=\'fi\';\n    d.innerHTML=`<label>${FL[i]}</label><input type="number" class="tom" id="tom_${i}" value="${tom[i]}" min="-30" max="10" step="1" oninput="setTom(${i},this.value)">`;\n    g.appendChild(d);});\n}\n\nfunction setV(i,v){const n=v===\'\'?null:parseFloat(v);if(ear===\'OD\')od[i]=n;else os[i]=n;drawA();calcEQ();}\nfunction setTom(i,v){tom[i]=parseFloat(v)||0;drawA();calcEQ();}\nfunction resetTom(){tom=[...TOM_STD];FR.forEach((_,i)=>{const e=document.getElementById(\'tom_\'+i);if(e)e.value=tom[i];});drawA();calcEQ();}\nfunction reset(){od=new Array(11).fill(null);os=new Array(11).fill(null);buildFiGrid();drawA();calcEQ();}\n\nfunction drawA(){\n  const cv=document.getElementById(\'cvA\');\n  cv.width=cv.parentElement.clientWidth-32;\n  const ctx=cv.getContext(\'2d\');\n  const W=cv.width,H=cv.height;\n  const pL=44,pR=12,pT=18,pB=24;\n  const cw=W-pL-pR,ch=H-pT-pB;\n  ctx.clearRect(0,0,W,H);\n  ctx.fillStyle=\'#fff\';ctx.fillRect(0,0,W,H);\n  const mn=-20,mx=90;\n  const tx=i=>pL+i*(cw/(FR.length-1));\n  const ty=d=>pT+(d-mn)/(mx-mn)*ch;\n  ctx.strokeStyle=\'rgba(128,128,128,0.12)\';ctx.lineWidth=0.5;\n  for(let d=mn;d<=mx;d+=10){ctx.beginPath();ctx.moveTo(pL,ty(d));ctx.lineTo(W-pR,ty(d));ctx.stroke();}\n  FR.forEach((_,i)=>{ctx.beginPath();ctx.moveTo(tx(i),pT);ctx.lineTo(tx(i),pT+ch);ctx.stroke();});\n  ctx.strokeStyle=\'rgba(128,128,128,0.45)\';ctx.lineWidth=1;\n  ctx.beginPath();ctx.moveTo(pL,ty(0));ctx.lineTo(W-pR,ty(0));ctx.stroke();\n  ctx.fillStyle=\'#aaa\';ctx.font=\'9px sans-serif\';ctx.textAlign=\'right\';\n  for(let d=mn;d<=mx;d+=10)ctx.fillText(d,pL-3,ty(d)+3);\n  ctx.textAlign=\'center\';FR.forEach((_,i)=>ctx.fillText(FL[i],tx(i),pT+ch+13));\n  ctx.fillStyle=\'rgba(45,125,111,0.05)\';ctx.fillRect(pL,pT,cw,ty(0)-pT);\n  ctx.fillStyle=\'#2d7d6f\';ctx.font=\'9px sans-serif\';ctx.textAlign=\'left\';\n  ctx.fillText(\'Iperudizione\',pL+3,pT+9);\n  ctx.strokeStyle=\'#2d7d6f\';ctx.lineWidth=2;ctx.setLineDash([5,4]);\n  ctx.beginPath();tom.forEach((v,i)=>i===0?ctx.moveTo(tx(i),ty(v)):ctx.lineTo(tx(i),ty(v)));\n  ctx.stroke();ctx.setLineDash([]);\n  function dc(vals,col,sym){\n    const pts=vals.map((v,i)=>v!==null?[tx(i),ty(v)]:null).filter(Boolean);\n    if(!pts.length)return;\n    ctx.strokeStyle=col;ctx.lineWidth=2;\n    ctx.beginPath();pts.forEach(([x,y],i)=>i===0?ctx.moveTo(x,y):ctx.lineTo(x,y));ctx.stroke();\n    ctx.fillStyle=col;ctx.font=\'bold 13px sans-serif\';ctx.textAlign=\'center\';\n    pts.forEach(([x,y])=>ctx.fillText(sym,x,y+4));\n  }\n  dc(od,\'#c0392b\',\'O\');dc(os,\'#2980b9\',\'X\');\n}\n\nfunction calcEQ(){\n  eqOD=FR.map((_,i)=>od[i]!==null?Math.round(tom[i]-od[i]):0);\n  eqOS=FR.map((_,i)=>os[i]!==null?Math.round(tom[i]-os[i]):0);\n  const active=od.filter(v=>v!==null);\n  if(active.length===0){document.getElementById(\'eqSt\').textContent=\'Inserisci le soglie per generare l EQ.\';document.getElementById(\'eqSt\').className=\'status info\';return;}\n  const avg=eqOD.filter((_,i)=>od[i]!==null).reduce((a,b)=>a+b,0)/Math.max(1,active.length);\n  document.getElementById(\'eqNote\').textContent=avg>5?\'Ipouduzione — rinforzo\':avg<-5?\'Iperudizione — attenuazione\':\'Vicino al target Tomatis\';\n  document.getElementById(\'eqDom\').textContent=\'OD da privilegiare\';\n  document.getElementById(\'eqSt\').textContent=\'EQ generato. Aggiusta manualmente se necessario.\';\n  document.getElementById(\'eqSt\').className=\'status ok\';\n  buildEQGrid();drawEQ();\n}\n\nfunction buildEQGrid(){\n  const g=document.getElementById(\'eqGrid\');g.innerHTML=\'\';\n  FR.forEach((_,i)=>{\n    const v=od[i]!==null?eqOD[i]:eqOS[i];\n    const col=v>3?\'#1d9e75\':v<-3?\'#e24b4a\':\'#ba7517\';\n    const h=Math.min(32,Math.abs(v)*2.5);\n    const pos=v>=0?`bottom:50%;height:${h}px`:`top:50%;height:${h}px`;\n    const d=document.createElement(\'div\');d.className=\'eq-bar\';\n    d.innerHTML=`<div class="eq-track"><div class="eq-fill" style="${pos};background:${col}"></div></div><div class="eq-val" style="color:${col}">${v>0?\'+\'+v:v}</div><div class="eq-lbl">${FL[i]}</div>`;\n    g.appendChild(d);});\n}\n\nfunction drawEQ(){\n  const cv=document.getElementById(\'cvEQ\');\n  cv.width=cv.parentElement.clientWidth-32;\n  const ctx=cv.getContext(\'2d\');\n  const W=cv.width,H=cv.height;\n  const pL=44,pR=12,pT=16,pB=22;\n  const cw=W-pL-pR,ch=H-pT-pB;\n  ctx.clearRect(0,0,W,H);ctx.fillStyle=\'#fff\';ctx.fillRect(0,0,W,H);\n  const mn=-25,mx=25;\n  const tx=i=>pL+i*(cw/(FR.length-1));\n  const ty=d=>pT+(d-mx)/(mn-mx)*ch;\n  ctx.strokeStyle=\'rgba(128,128,128,0.12)\';ctx.lineWidth=0.5;\n  for(let d=mn;d<=mx;d+=5){ctx.beginPath();ctx.moveTo(pL,ty(d));ctx.lineTo(W-pR,ty(d));ctx.stroke();}\n  FR.forEach((_,i)=>{ctx.beginPath();ctx.moveTo(tx(i),pT);ctx.lineTo(tx(i),pT+ch);ctx.stroke();});\n  ctx.strokeStyle=\'rgba(128,128,128,0.5)\';ctx.lineWidth=1;\n  ctx.beginPath();ctx.moveTo(pL,ty(0));ctx.lineTo(W-pR,ty(0));ctx.stroke();\n  ctx.fillStyle=\'rgba(29,158,117,0.07)\';ctx.fillRect(pL,pT,cw,ty(0)-pT);\n  ctx.fillStyle=\'rgba(226,75,74,0.07)\';ctx.fillRect(pL,ty(0),cw,ch-(ty(0)-pT));\n  ctx.fillStyle=\'#aaa\';ctx.font=\'9px sans-serif\';ctx.textAlign=\'right\';\n  for(let d=mn;d<=mx;d+=10)ctx.fillText(d,pL-3,ty(d)+3);\n  ctx.textAlign=\'center\';FR.forEach((_,i)=>ctx.fillText(FL[i],tx(i),pT+ch+13));\n  function db(vals,dataArr,col){\n    FR.forEach((_,i)=>{if(vals[i]===null)return;const v=dataArr[i];const x=tx(i);const bw=cw/FR.length*0.5;const y0=ty(0);\n      if(v>=0){const h2=ty(0)-ty(v);ctx.fillStyle=col+\'88\';ctx.fillRect(x-bw/2,y0-h2,bw,h2);}\n      else{const h2=ty(v)-ty(0);ctx.fillStyle=col+\'55\';ctx.fillRect(x-bw/2,y0,bw,h2);}\n      ctx.fillStyle=col;ctx.font=\'bold 10px sans-serif\';ctx.textAlign=\'center\';\n      ctx.fillText((v>0?\'+\':\'\')+v,x,v>=0?ty(v)-3:ty(v)+11);});\n  }\n  db(od,eqOD,\'#c0392b\');db(os,eqOS,\'#2980b9\');\n}\n\nconst SEL_ROWS=[\'LE BC\',\'LE AC\',\'RE BC\',\'RE AC\'];\nconst LAT_ROWS=[\'BPTA 20dB\',\'A soglia\'];\nconst OPTS=[\'\',\'O\',\'X\',\'OX\'];\n\nfunction buildSel(){\n  const b=document.getElementById(\'selBody\');b.innerHTML=\'\';\n  SEL_ROWS.forEach(r=>{const tr=document.createElement(\'tr\');\n    tr.innerHTML=`<td>${r}</td>`+FR.map((_,i)=>`<td><select class="sel" id="sl_${r.replace(/\\s/g,\'_\')}_${i}">${OPTS.map(o=>`<option>${o}</option>`).join(\'\')}</select></td>`).join(\'\');\n    b.appendChild(tr);});\n}\n\nfunction buildLat(){\n  const b=document.getElementById(\'latBody\');b.innerHTML=\'\';\n  LAT_ROWS.forEach(r=>{const tr=document.createElement(\'tr\');\n    tr.innerHTML=`<td>${r}</td>`+FR.map((_,i)=>`<td><select class="sel" id="lt_${r.replace(/\\s/g,\'_\')}_${i}" onchange="calcLat()">${OPTS.map(o=>`<option>${o}</option>`).join(\'\')}</select></td>`).join(\'\');\n    b.appendChild(tr);});\n}\n\nfunction calcLat(){\n  let odC=0,osC=0;\n  FR.forEach((_,i)=>{\n    LAT_ROWS.forEach(r=>{const v=document.getElementById(`lt_${r.replace(/\\s/g,\'_\')}_${i}`)?.value||\'\';\n      if(v===\'O\')odC++;else if(v===\'X\')osC++;else if(v===\'OX\'){odC++;osC++;}});\n  });\n  const tot=odC+osC;\n  document.getElementById(\'latDom\').textContent=odC>osC?\'OD dominante\':osC>odC?\'OS dominante\':\'Bilanciato\';\n  document.getElementById(\'latIdx\').textContent=tot?Math.round((odC-osC)*100/tot)+\'/100\':\'-\';\n}\n\nfunction saveAll(){\n  const selData={};\n  SEL_ROWS.forEach(r=>FR.forEach((_,i)=>{const v=document.getElementById(`sl_${r.replace(/\\s/g,\'_\')}_${i}`)?.value;if(v)selData[r+\'_\'+i]=v;}));\n  const latData={};\n  LAT_ROWS.forEach(r=>FR.forEach((_,i)=>{const v=document.getElementById(`lt_${r.replace(/\\s/g,\'_\')}_${i}`)?.value;if(v)latData[r+\'_\'+i]=v;}));\n  const data={od:od,os:os,tom:tom,eqOD:eqOD,eqOS:eqOS,sel:selData,lat:latData};\n  window.parent.postMessage({type:\'streamlit:setComponentValue\',value:JSON.stringify(data)},\'*\');\n  document.getElementById(\'saved\').style.display=\'block\';\n  setTimeout(()=>document.getElementById(\'saved\').style.display=\'none\',3000);\n}\n\n// Init\nbuildFiGrid();buildTomGrid();buildSel();buildLat();\nwindow.addEventListener(\'resize\',()=>{drawA();drawEQ();});\nsetTimeout(()=>{drawA();drawEQ();},120);\n</script></body></html>'


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
