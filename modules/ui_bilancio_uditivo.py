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

import json
import streamlit as st
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

_HTML_TEMPLATE = '<!DOCTYPE html><html><head><meta charset="utf-8">\n<style>\n*{box-sizing:border-box;margin:0;padding:0;font-family:system-ui,sans-serif}\nbody{padding:12px;background:#f8f7f4;color:#1a1a1a}\n.tabs{display:flex;border-bottom:2px solid #d4cec5;margin-bottom:14px}\n.tab{padding:8px 14px;font-size:12px;cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-2px;color:#8a8a8a}\n.tab.active{color:#2d7d6f;font-weight:600;border-bottom-color:#2d7d6f}\n.section{display:none}.section.active{display:block}\n.card{background:#fff;border:1px solid #d4cec5;border-radius:10px;padding:14px 16px;margin-bottom:10px}\nh3{font-size:14px;font-weight:500;margin-bottom:4px}\n.cap{font-size:11px;color:#8a8a8a;margin-bottom:10px}\n.row{display:flex;align-items:center;gap:8px;margin:5px 0;font-size:12px;color:#4a4a4a}\n.row label{min-width:130px;font-size:11px}\n.row input[type=range]{flex:1;accent-color:#2d7d6f}\n.row span{min-width:48px;font-size:12px;font-weight:500}\n.grid2{display:grid;grid-template-columns:1fr 1fr;gap:10px}\n.ear{background:#f8f7f4;border-radius:8px;padding:10px;text-align:center}\n.ear-l{font-size:10px;font-weight:600;letter-spacing:.05em;text-transform:uppercase;margin-bottom:6px}\n.ear.od .ear-l{color:#c0392b}.ear.os .ear-l{color:#2980b9}\n.big{font-size:24px;font-weight:500}.unit{font-size:10px;color:#8a8a8a;margin-top:2px}\n.btn-row{display:flex;gap:6px;margin:8px 0;flex-wrap:wrap}\nbutton{font-family:inherit;font-size:12px;padding:6px 12px;border-radius:7px;border:1.5px solid #d4cec5;background:#fff;color:#4a4a4a;cursor:pointer}\nbutton:hover{background:#e8f3f1;border-color:#2d7d6f;color:#1a5248}\nbutton.primary{background:#2d7d6f;border-color:#2d7d6f;color:#fff}\nbutton.primary:hover{background:#1a5248}\nbutton:disabled{opacity:.4;cursor:not-allowed}\n.freq-grid{display:grid;grid-template-columns:repeat(8,1fr);gap:3px;margin:6px 0}\n.fq{font-size:10px;padding:4px 2px;border-radius:4px;text-align:center;border:1px solid #d4cec5;cursor:pointer;background:#f8f7f4;color:#8a8a8a}\n.fq.active{background:#e8f3f1;border-color:#2d7d6f;color:#1a5248;font-weight:600}\n.fq.done{background:#eaf5f0;border-color:#2d7d6f;color:#2d7d6f}\n.status{font-size:12px;padding:6px 10px;border-radius:6px;margin:6px 0}\n.ok{background:#e8f3f1;color:#1a5248}.warn{background:#fef7ec;color:#7a4f0a}.info{background:#ebf5fb;color:#154360}\n.meter{display:flex;gap:3px;align-items:flex-end;height:28px;margin:6px 0}\n.mb{width:8px;border-radius:2px 2px 0 0;transition:height .1s;min-height:2px}\n.jrow{display:grid;grid-template-columns:24px 70px 70px 1fr 1fr 1fr;gap:3px;padding:4px 6px;font-size:12px;align-items:center}\n.jrow:nth-child(even){background:#f8f7f4}\n.jhead{font-size:10px;font-weight:600;color:#8a8a8a;text-transform:uppercase;letter-spacing:.04em}\n.resp{font-size:11px;padding:3px 6px;min-width:36px;margin:1px}\n.resp.ok{background:#e8f3f1;border-color:#2d7d6f;color:#1a5248}\n.lat-bar{height:16px;border-radius:8px;background:#ede9e3;margin:6px 0;overflow:hidden}\n.lat-fill{height:100%;border-radius:8px;transition:width .4s;background:#2d7d6f}\n.sbox{background:#f8f7f4;border-radius:8px;padding:8px 12px;margin:5px 0}\n.sbox .sv{font-size:18px;font-weight:500}\n</style></head><body>\n<div class="tabs">\n  <div class="tab active" onclick="sw(\'lat\')">Lateralita</div>\n  <div class="tab" onclick="sw(\'timp\')">Timpano</div>\n  <div class="tab" onclick="sw(\'joh\')">Johansen</div>\n  <div class="tab" onclick="sw(\'ris\')">Risultati</div>\n</div>\n<div class="section active" id="tab-lat">\n<div class="card">\n  <h3>Lateralita uditiva di ricezione</h3>\n  <p class="cap">Il paziente centra il suono. Invia il tono e valida il balance.</p>\n  <div style="font-size:11px;color:#8a8a8a;margin-bottom:4px">Seleziona frequenza:</div>\n  <div class="freq-grid" id="freqGrid"></div>\n  <div class="row"><label>Volume (dB sopra soglia)</label><input type="range" id="vLat" min="10" max="50" value="30" oninput="vLatV.textContent=this.value+\'dB\'"><span id="vLatV">30dB</span></div>\n  <div class="row"><label>Balance</label><input type="range" id="bal" min="-100" max="100" value="0" oninput="updBal(this.value)"><span id="balV">Centro</span></div>\n</div>\n<div class="grid2">\n  <div class="ear od"><div class="ear-l">OD Destro</div><div class="big" id="latOD">-</div><div class="unit">errore medio</div></div>\n  <div class="ear os"><div class="ear-l">OS Sinistro</div><div class="big" id="latOS">-</div><div class="unit">errore medio</div></div>\n</div>\n<div class="btn-row">\n  <button class="primary" onclick="playLat()">Invia tono</button>\n  <button onclick="shiftB(-5)">SX</button>\n  <button onclick="shiftB(5)">DX</button>\n  <button onclick="valLat()" style="border-color:#2d7d6f;color:#2d7d6f">Valida</button>\n  <button onclick="nextFreq()">Freq. succ.</button>\n</div>\n<div id="latSt" class="status info">Seleziona frequenza e invia il tono.</div>\n</div>\n<div class="section" id="tab-timp">\n<div class="card">\n  <h3>Elasticita del timpano</h3>\n  <p class="cap">Rumore da volume basso ad alto. Registra la tolleranza del paziente.</p>\n  <div class="row"><label>Volume (dB)</label><input type="range" id="vTimp" min="-40" max="0" value="-40" oninput="vTimpV.textContent=this.value+\'dB\'"><span id="vTimpV">-40dB</span></div>\n  <div class="row"><label>Tipo rumore</label>\n    <select id="noiseT" style="flex:1;font-size:12px;padding:4px 8px;border-radius:6px;border:1px solid #d4cec5">\n      <option value="white">Bianco</option><option value="pink" selected>Rosa (sim. musica)</option><option value="brown">Marrone (gravi)</option>\n    </select>\n  </div>\n  <div class="meter" id="meter"></div>\n</div>\n<div class="btn-row">\n  <button class="primary" id="btnT" onclick="togTimp()">Start</button>\n  <button onclick="adjV(-3)">-3dB</button><button onclick="adjV(3)">+3dB</button>\n</div>\n<div class="card">\n  <h3>Registra tolleranza</h3>\n  <div class="row"><label>Volume tollerato</label><input type="range" id="tolV" min="-40" max="0" value="-10" oninput="tolVV.textContent=this.value+\'dB\'"><span id="tolVV">-10dB</span></div>\n  <div class="row"><label>Durata (sec)</label><input type="range" id="durV" min="1" max="30" step="1" value="5" oninput="durVV.textContent=this.value+\'s\'"><span id="durVV">5s</span></div>\n  <div class="row"><label>Note</label><input id="timpNote" type="text" placeholder="note cliniche..." style="flex:1;padding:5px 8px;border-radius:6px;border:1px solid #d4cec5;font-size:12px"></div>\n  <div class="btn-row"><button onclick="saveTimp()">Salva timpano</button></div>\n  <div id="tSaved" class="status ok" style="display:none">Salvato</div>\n</div>\n</div>\n<div class="section" id="tab-joh">\n<div class="card">\n  <h3>Test dicotico di Johansen</h3>\n  <p class="cap">20 coppie OD/OS simultanee. Registra le risposte del paziente per ogni compito.</p>\n  <div class="btn-row">\n    <button class="primary" onclick="startJoh()">Avvia</button>\n    <button onclick="resetJoh()">Reset</button>\n  </div>\n  <div id="johSt" class="status info">Premi Avvia per iniziare.</div>\n</div>\n<div style="font-size:11px">\n  <div class="jrow jhead">\n    <div>#</div><div style="color:#c0392b">OD</div><div style="color:#2980b9">OS</div>\n    <div>Comp.3 DX</div><div>Comp.4 SX</div><div>Comp.5 Both</div>\n  </div>\n  <div id="johRows"></div>\n</div>\n<div class="grid2" style="margin-top:8px">\n  <div class="sbox"><div style="font-size:10px;color:#8a8a8a;text-transform:uppercase">Punteggio OD</div><div class="sv" id="jOD" style="color:#c0392b">0</div></div>\n  <div class="sbox"><div style="font-size:10px;color:#8a8a8a;text-transform:uppercase">Punteggio OS</div><div class="sv" id="jOS" style="color:#2980b9">0</div></div>\n</div>\n<div class="sbox">\n  <div style="font-size:10px;color:#8a8a8a">Indice (DX-SX)/(DX+SX)x100</div>\n  <div class="sv" id="jIdx">-</div>\n  <div class="lat-bar"><div class="lat-fill" id="jBar" style="width:50%"></div></div>\n  <div style="display:flex;justify-content:space-between;font-size:10px;color:#8a8a8a"><span>SX</span><span>Centro</span><span>DX</span></div>\n</div>\n</div>\n<div class="section" id="tab-ris">\n<div class="card">\n  <h3>Sintesi bilancio uditivo</h3>\n  <div id="sumContent" style="font-size:13px;color:#4a4a4a">Esegui i test per vedere la sintesi.</div>\n</div>\n<div class="card">\n  <h3>Note cliniche</h3>\n  <textarea id="noteClin" rows="3" style="width:100%;font-size:12px;padding:6px 8px;border-radius:6px;border:1px solid #d4cec5;resize:vertical"></textarea>\n</div>\n<div class="btn-row"><button class="primary" onclick="saveAll()">Salva bilancio completo</button></div>\n<div id="allSaved" class="status ok" style="display:none">Bilancio salvato!</div>\n</div>\n<script>\nconst FREQS=__FREQS__;\nconst JOHANSEN=__JOHANSEN__;\nconst PAZ_ID=__PAZ_ID__;\nlet actx=null,latData={},curF=FREQS[0],curBal=0;\nlet tNode=null,tPlaying=false,mInt=null;\nlet johAns={};\nlet results={};\nfunction getCtx(){if(!actx)actx=new(window.AudioContext||window.webkitAudioContext)();if(actx.state===\'suspended\')actx.resume();return actx;}\nconst fg=document.getElementById(\'freqGrid\');\nFREQS.forEach(f=>{const d=document.createElement(\'div\');d.className=\'fq\'+(f===curF?\' active\':\'\');d.textContent=f>=1000?(f/1000)+\'k\':f;d.onclick=()=>{curF=f;rfg();};fg.appendChild(d);});\nfunction rfg(){Array.from(fg.children).forEach((d,i)=>{const f=FREQS[i];d.className=\'fq\';if(f===curF)d.classList.add(\'active\');else if(latData[f]!==undefined)d.classList.add(\'done\');});}\nfunction updBal(v){curBal=parseInt(v);balV.textContent=v==0?\'Centro\':(v<0?Math.abs(v)+\'% SX\':v+\'% DX\');}\nfunction shiftB(delta){const s=document.getElementById(\'bal\');s.value=Math.max(-100,Math.min(100,parseInt(s.value)+delta));updBal(s.value);}\nfunction playLat(){const ctx=getCtx();const osc=ctx.createOscillator(),g=ctx.createGain(),pan=ctx.createStereoPanner();osc.frequency.value=curF;osc.type=\'sine\';g.gain.value=0.25;pan.pan.value=curBal/100;osc.connect(g);g.connect(pan);pan.connect(ctx.destination);osc.start();osc.stop(ctx.currentTime+2);latSt.textContent=\'Tono \'+curF+\' Hz inviato - Balance: \'+balV.textContent;latSt.className=\'status ok\';}\nfunction valLat(){latData[curF]=curBal;latSt.textContent=\'Validato \'+curF+\' Hz (balance \'+curBal+\')\';rfg();const vals=Object.values(latData);if(vals.length>0){const avg=Math.round(vals.reduce((a,b)=>a+b,0)/vals.length);latOD.textContent=avg>0?\'+\'+avg:\'-\';latOS.textContent=avg<0?Math.abs(avg):\'-\';}results.lat=latData;updSum();}\nfunction nextFreq(){const i=FREQS.indexOf(curF);if(i<FREQS.length-1){curF=FREQS[i+1];document.getElementById(\'bal\').value=0;updBal(0);rfg();}}\nfunction genNoise(ctx,type){const buf=ctx.createBuffer(1,ctx.sampleRate*3,ctx.sampleRate);const d=buf.getChannelData(0);if(type===\'white\'){for(let i=0;i<d.length;i++)d[i]=Math.random()*2-1;}else if(type===\'pink\'){let b0=0,b1=0,b2=0,b3=0,b4=0,b5=0,b6=0;for(let i=0;i<d.length;i++){const w=Math.random()*2-1;b0=.99886*b0+w*.0555179;b1=.99332*b1+w*.0750759;b2=.969*b2+w*.153852;b3=.8665*b3+w*.3104856;b4=.55*b4+w*.5329522;b5=-.7616*b5-w*.016898;d[i]=(b0+b1+b2+b3+b4+b5+b6+w*.5362)*.11;b6=w*.115926;}}else{let last=0;for(let i=0;i<d.length;i++){const w=Math.random()*2-1;last=(last+.02*w)/1.02;d[i]=last*3.5;}}return buf;}\nfunction togTimp(){const ctx=getCtx();if(tPlaying&&tNode){tNode.stop();tPlaying=false;btnT.textContent=\'Start\';clearInterval(mInt);meter.innerHTML=\'\';return;}const v=parseFloat(vTimp.value),nt=document.getElementById(\'noiseT\').value;const buf=genNoise(ctx,nt);const src=ctx.createBufferSource();const g=ctx.createGain();src.buffer=buf;src.loop=true;g.gain.value=Math.pow(10,v/20);src.connect(g);g.connect(ctx.destination);src.start();tNode=src;tPlaying=true;btnT.textContent=\'Stop\';mInt=setInterval(animM,100);}\nfunction animM(){if(!tPlaying)return;const v=(parseFloat(vTimp.value)+40)/40;meter.innerHTML=\'\';for(let i=0;i<14;i++){const b=document.createElement(\'div\');b.className=\'mb\';const h=Math.random()*18*v+3;b.style.height=h+\'px\';b.style.background=v>.8?\'#e74c3c\':v>.5?\'#f39c12\':\'#2d7d6f\';meter.appendChild(b);}}\nfunction updVT(v){vTimpV.textContent=v+\'dB\';}\nfunction adjV(delta){const s=document.getElementById(\'vTimp\');s.value=Math.max(-40,Math.min(0,parseInt(s.value)+delta));updVT(s.value);}\nfunction saveTimp(){results.timp={vol:tolV.value,dur:durV.value,note:document.getElementById(\'timpNote\').value};tSaved.style.display=\'block\';setTimeout(()=>tSaved.style.display=\'none\',2000);updSum();}\nfunction buildJoh(){johRows.innerHTML=\'\';JOHANSEN.forEach((r,i)=>{const d=document.createElement(\'div\');d.className=\'jrow\';d.id=\'jr\'+i;d.innerHTML=\'<span style="color:#8a8a8a;font-size:10px">\'+(i+1)+\'</span><span style="color:#c0392b;font-weight:600">\'+r.od+\'</span><span style="color:#2980b9;font-weight:600">\'+r.os+\'</span><div><button class="resp" id="c3od\'+i+\'" onclick="mk(\'+i+\',\\\'c3\\\',\\\'od\\\')">OD</button><button class="resp" id="c3os\'+i+\'" onclick="mk(\'+i+\',\\\'c3\\\',\\\'os\\\')">OS</button></div><div><button class="resp" id="c4od\'+i+\'" onclick="mk(\'+i+\',\\\'c4\\\',\\\'od\\\')">OD</button><button class="resp" id="c4os\'+i+\'" onclick="mk(\'+i+\',\\\'c4\\\',\\\'os\\\')">OS</button></div><div><button class="resp" id="c5od\'+i+\'" onclick="mk(\'+i+\',\\\'c5\\\',\\\'od\\\')">OD</button><button class="resp" id="c5os\'+i+\'" onclick="mk(\'+i+\',\\\'c5\\\',\\\'os\\\')">OS</button><button class="resp" id="c5b\'+i+\'" onclick="mk(\'+i+\',\\\'c5\\\',\\\'b\\\')">Ent</button></div>\';johRows.appendChild(d);});}\nfunction startJoh(){buildJoh();johSt.textContent=\'Leggi le coppie e registra le risposte.\';johSt.className=\'status ok\';}\nfunction resetJoh(){johAns={};jOD.textContent=\'0\';jOS.textContent=\'0\';jIdx.textContent=\'-\';jBar.style.width=\'50%\';buildJoh();johSt.textContent=\'Premi Avvia.\';johSt.className=\'status info\';}\nfunction mk(i,comp,side){if(!johAns[i])johAns[i]={};johAns[i][comp]=side;[\'od\',\'os\',\'b\'].forEach(s=>{const el=document.getElementById(comp+s+i);if(el)el.classList.remove(\'ok\');});const el=document.getElementById(comp+side+i);if(el)el.classList.add(\'ok\');calcJoh();}\nfunction calcJoh(){let od=0,os=0;JOHANSEN.forEach((r,i)=>{const a=johAns[i]||{};if(a.c3===\'od\')od++;if(a.c4===\'os\')os++;if(a.c5===\'od\'||a.c5===\'b\')od++;if(a.c5===\'os\'||a.c5===\'b\')os++;});jOD.textContent=od;jOS.textContent=os;const tot=od+os;if(tot>0){const idx=Math.round((od-os)*100/tot);jIdx.textContent=(idx>0?\'+\':\'\')+idx+\' (\'+(idx>10?\'Dom DX\':idx<-10?\'Dom SX\':\'Bilanciato\')+\')\';jBar.style.width=((od/tot)*100)+\'%\';jBar.style.background=idx>10?\'#c0392b\':idx<-10?\'#2980b9\':\'#2d7d6f\';}results.joh={od:od,os:os,tot:tot,ans:johAns};updSum();}\nfunction updSum(){let h=\'\';if(results.lat){const vals=Object.values(results.lat),n=vals.length;if(n>0){const avg=Math.round(vals.reduce((a,b)=>a+b,0)/n);h+=\'<p><b>Lateralita:</b> \'+n+\' frequenze - balance medio \'+(avg>0?\'+\'+avg:avg)+\' (\'+( avg>5?\'Dom DX\':avg<-5?\'Dom SX\':\'Bilanciato\')+\')</p>\';}}if(results.timp)h+=\'<p><b>Timpano:</b> volume tollerato \'+results.timp.vol+\'dB per \'+results.timp.dur+\'s\'+(results.timp.note?\' - \'+results.timp.note:\'\')+\'</p>\';if(results.joh&&results.joh.tot>0){const idx=Math.round((results.joh.od-results.joh.os)*100/results.joh.tot);h+=\'<p><b>Johansen:</b> OD=\'+results.joh.od+\' OS=\'+results.joh.os+\' Indice=\'+(idx>0?\'+\':\'\')+idx+\'</p>\';}sumContent.innerHTML=h||\'Esegui i test per vedere la sintesi.\';}\nfunction saveAll(){const data={paz_id:PAZ_ID,lat:results.lat||{},timp:results.timp||{},joh:results.joh||{},note:document.getElementById(\'noteClin\').value};window.parent.postMessage({type:\'streamlit:setComponentValue\',value:JSON.stringify(data)},\'*\');allSaved.style.display=\'block\';setTimeout(()=>allSaved.style.display=\'none\',3000);}\nfunction sw(name){document.querySelectorAll(\'.tab\').forEach((t,i)=>{t.classList.toggle(\'active\',[\'lat\',\'timp\',\'joh\',\'ris\'][i]===name);});document.querySelectorAll(\'.section\').forEach(s=>s.classList.remove(\'active\'));document.getElementById(\'tab-\'+name).classList.add(\'active\');}\nbuildJoh();rfg();\n</script></body></html>'


def _html_bilancio(paz_id: int) -> str:
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
        _ui_storico(conn, cur, paz_id)

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


def _ui_storico(conn, cur, paz_id):
    ph1 = _ph(1, conn)
    try:
        cur.execute(
            "SELECT * FROM bilanci_uditivi WHERE paziente_id = " + ph1 +
            " ORDER BY data_bilancio DESC, id DESC LIMIT 20",
            (paz_id,)
        )
        rows = cur.fetchall()
    except Exception as e:
        st.error(f"Errore storico: {e}"); return

    if not rows:
        st.info("Nessun bilancio registrato per questo paziente."); return

    lat_rows, joh_rows = [], []
    for r in rows:
        d = _row_get(r, "data_bilancio", "")
        lm = _row_get(r, "lat_balance_medio")
        ji = _row_get(r, "joh_indice")
        if lm is not None: lat_rows.append({"Data": d, "Balance medio": lm})
        if ji is not None: joh_rows.append({"Data": d, "Indice Johansen": ji})

    if lat_rows or joh_rows:
        cg1, cg2 = st.columns(2)
        if lat_rows:
            with cg1:
                st.markdown("**Lateralita uditiva nel tempo**")
                st.line_chart(pd.DataFrame(lat_rows).sort_values("Data").set_index("Data"))
                st.caption(">+5 = Dom DX | <-5 = Dom SX")
        if joh_rows:
            with cg2:
                st.markdown("**Indice Johansen nel tempo**")
                st.line_chart(pd.DataFrame(joh_rows).sort_values("Data").set_index("Data"))
                st.caption(">+10 = Dom DX | <-10 = Dom SX")

    for r in rows:
        eid = _row_get(r, "id")
        data_b = _row_get(r, "data_bilancio", "")
        ld = _row_get(r, "lat_dominanza", "-")
        jd = _row_get(r, "joh_dominanza", "-")
        lm = _row_get(r, "lat_balance_medio")
        ji = _row_get(r, "joh_indice")
        with st.expander(f"#{eid} | {data_b} — Lat: {ld} | Johansen: {jd}"):
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Balance medio", f"{lm:+.1f}" if lm is not None else "-")
            c2.metric("Dom. lateralita", ld or "-")
            c3.metric("Indice Johansen", f"{ji:+.1f}" if ji is not None else "-")
            c4.metric("Dom. Johansen", jd or "-")
            jod = _row_get(r, "joh_od")
            jos = _row_get(r, "joh_os")
            tv = _row_get(r, "timp_vol_tollerato")
            td = _row_get(r, "timp_durata_sec")
            tn = _row_get(r, "timp_note", "")
            if jod is not None: st.markdown(f"**Johansen:** OD={jod} OS={jos}")
            if tv is not None: st.markdown(f"**Timpano:** {tv} dB per {td}s{' - '+tn if tn else ''}")
            note = _row_get(r, "note_cliniche", "")
            if note: st.markdown(f"**Note:** {note}")
