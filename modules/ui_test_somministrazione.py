# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════╗
║  UI TEST SOMMINISTRAZIONE                                           ║
║  Somministrazione interattiva — 1 monitor o 2 monitor              ║
║                                                                     ║
║  MODALITÀ:                                                          ║
║  • 1 monitor → stimoli incorporati nella stessa finestra           ║
║  • 2 monitor → stimoli in nuova finestra (secondo monitor)         ║
║                                                                     ║
║  TEST: Rey AVLT · TMT A/B · Cancellazione · RAN                   ║
║        Alpha Span · Updating · Fluenza · Switch · Numerazione      ║
║        Five Point Test · Stroop                                     ║
╚══════════════════════════════════════════════════════════════════════╝
"""
from __future__ import annotations
import streamlit as st
import streamlit.components.v1 as components
import json
import datetime
import random
import math
from typing import Optional

# ══════════════════════════════════════════════════════════════════════
#  COSTANTI E UTILITY
# ══════════════════════════════════════════════════════════════════════

_BG_PAZ  = "#0d1117"   # sfondo schermata paziente
_FG_PAZ  = "#f0f6fc"   # testo schermata paziente
_ACCENT  = "#2ea44f"   # verde azione

def _base_html(body: str,
               bg: str = _BG_PAZ,
               fg: str = _FG_PAZ,
               extra_css: str = "") -> str:
    """Template HTML base per schermate paziente — grande, pulita, leggibile."""
    return f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
* {{ box-sizing:border-box; margin:0; padding:0; }}
body {{
  background:{bg}; color:{fg};
  font-family:'Segoe UI',Arial,sans-serif;
  display:flex; flex-direction:column;
  align-items:center; justify-content:center;
  min-height:100vh; padding:40px;
  user-select:none;
}}
.title {{ font-size:1.4rem; color:#8b949e; margin-bottom:30px; letter-spacing:2px; text-transform:uppercase; }}
.main  {{ font-size:5rem; font-weight:700; text-align:center; min-height:120px;
           display:flex; align-items:center; justify-content:center; }}
.sub   {{ font-size:1.3rem; color:#8b949e; margin-top:20px; text-align:center; }}
.btn-row {{ display:flex; gap:16px; margin-top:36px; flex-wrap:wrap; justify-content:center; }}
button {{
  background:#238636; color:#fff; border:none;
  padding:14px 36px; border-radius:10px;
  font-size:1.3rem; font-weight:600; cursor:pointer;
  transition:background .15s;
}}
button:hover    {{ background:#2ea44f; }}
button.stop     {{ background:#b91c1c; }}
button.stop:hover {{ background:#dc2626; }}
button.neutral  {{ background:#374151; }}
button.neutral:hover {{ background:#4b5563; }}
{extra_css}
</style>
</head>
<body>{body}</body>
</html>"""


def _launch_js(html_content: str) -> str:
    """Genera lo snippet JS per aprire html_content in una nuova finestra."""
    safe = (html_content
            .replace("\\", "\\\\")
            .replace("`",  "\\`")
            .replace("$",  "\\$"))
    return f"""
<script>
function openMonitor() {{
  const html = `{safe}`;
  const blob = new Blob([html], {{type:'text/html'}});
  const url  = URL.createObjectURL(blob);
  const w = window.open(url, '_blank',
    'width=1280,height=800,menubar=no,toolbar=no,location=no,status=no');
  if (!w) alert('Popup bloccato! Consenti popup per questo sito nelle impostazioni del browser.');
}}
</script>
<button onclick="openMonitor()"
  style="background:#0969da;color:#fff;border:none;padding:10px 22px;
         border-radius:8px;font-size:14px;font-weight:700;cursor:pointer">
  🖥️ Apri su secondo monitor
</button>
"""


def _selettore_monitor(key_prefix: str) -> str:
    """
    Widget radio per scegliere 1 o 2 monitor.
    Ritorna '1' oppure '2'.
    """
    scelta = st.radio(
        "Modalità monitor",
        ["🖥️ 1 monitor — stimoli qui", "🖥️🖥️ 2 monitor — stimoli in nuova finestra"],
        horizontal=True,
        key=f"{key_prefix}_monitor_mode",
    )
    return "1" if "1 monitor" in scelta else "2"


def _mostra_stimolo(paziente_html: str,
                    monitor_mode: str,
                    height_1mon: int = 480) -> None:
    """
    In base alla modalità:
    - '1': incorpora l'HTML nella stessa pagina
    - '2': mostra il pulsante per aprire in nuova finestra
    """
    if monitor_mode == "1":
        components.html(paziente_html, height=height_1mon, scrolling=False)
    else:
        components.html(_launch_js(paziente_html), height=70)


def _salva_test(conn, paziente_id: int, nome_test: str, dati: dict) -> None:
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS somministrazioni_test (
                id BIGSERIAL PRIMARY KEY,
                paziente_id BIGINT NOT NULL,
                nome_test TEXT NOT NULL,
                dati_json TEXT,
                data_somm DATE DEFAULT CURRENT_DATE,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        cur.execute(
            "INSERT INTO somministrazioni_test "
            "(paziente_id, nome_test, dati_json, data_somm) VALUES (%s,%s,%s,%s)",
            (paziente_id, nome_test,
             json.dumps(dati, ensure_ascii=False, default=str),
             datetime.date.today().isoformat())
        )
        conn.commit()
        st.success(f"✅ {nome_test} salvato.")
    except Exception as e:
        st.error(f"Errore salvataggio: {e}")


# ══════════════════════════════════════════════════════════════════════
#  PANNELLO CLINICO CONDIVISO — timer + note
# ══════════════════════════════════════════════════════════════════════

def _timer_html(label: str = "Timer") -> str:
    """Timer HTML standalone per il pannello clinico."""
    return f"""
<div style="font-family:monospace;text-align:center;padding:10px 0">
  <div id="disp" style="font-size:2.8rem;font-weight:700;color:#2ea44f;min-width:160px">
    00:00.0
  </div>
  <div style="font-size:.85rem;color:#8b949e;margin-bottom:8px">{label}</div>
  <div style="display:flex;gap:10px;justify-content:center">
    <button onclick="startT()"
      style="background:#238636;color:#fff;border:none;padding:8px 18px;
             border-radius:6px;font-size:14px;font-weight:600;cursor:pointer">
      ▶ Avvia
    </button>
    <button onclick="stopT()"
      style="background:#b91c1c;color:#fff;border:none;padding:8px 18px;
             border-radius:6px;font-size:14px;font-weight:600;cursor:pointer">
      ⏹ Stop
    </button>
    <button onclick="resetT()"
      style="background:#374151;color:#fff;border:none;padding:8px 18px;
             border-radius:6px;font-size:14px;font-weight:600;cursor:pointer">
      ↺ Reset
    </button>
  </div>
</div>
<script>
let t0=null, iv=null, el=0;
function fmt(ms){{
  let s=ms/1000, m=Math.floor(s/60); s=s%60;
  return String(m).padStart(2,'0')+':'+s.toFixed(1).padStart(4,'0');
}}
function tick(){{
  el=Date.now()-t0;
  document.getElementById('disp').textContent=fmt(el);
}}
function startT(){{
  if(iv) return;
  t0=Date.now()-el; iv=setInterval(tick,100);
}}
function stopT(){{
  if(iv){{clearInterval(iv);iv=null;}}
}}
function resetT(){{
  if(iv){{clearInterval(iv);iv=null;}}
  el=0; document.getElementById('disp').textContent='00:00.0';
}}
</script>"""


# ══════════════════════════════════════════════════════════════════════
#  1. REY AVLT
# ══════════════════════════════════════════════════════════════════════

_REY_A = ["TAMBURO","TENDA","CAMPANA","CAFFÈ","SCOLARO",
          "GENITORE","LUNA","GIARDINO","CAPPELLO","FERMO",
          "CONTADINO","NASO","TURCHIA","COLORE","CASA"]
_REY_B = ["GIORNO","ELEFANTE","FORESTA","COLTELLO","BAMBINO",
          "MELA","PARLAMENTO","MUCCA","SCARPA","LAMPADINA"]


def _rey_paziente(lista: list, titolo: str, ms: int) -> str:
    parole_js = json.dumps(lista)
    body = f"""
<div class="title">{titolo}</div>
<div class="main" id="parola">Premi START</div>
<div class="sub"  id="stato">— / {len(lista)}</div>
<div class="btn-row">
  <button onclick="avvia()">▶ START</button>
  <button class="stop"    onclick="ferma()">⏹ STOP</button>
  <button class="neutral" onclick="reset_()">↺ RESET</button>
</div>
<script>
const P={parole_js}, MS={ms};
let idx=-1, tmr=null;
function show(i){{
  document.getElementById('parola').textContent = i<P.length ? P[i] : '✓ FINE';
  document.getElementById('stato').textContent  = (i+1)+' / '+P.length;
}}
function avvia(){{
  if(tmr) clearInterval(tmr);
  idx=0; show(idx);
  tmr=setInterval(()=>{{
    idx++;
    if(idx>=P.length){{clearInterval(tmr);tmr=null;
      document.getElementById('parola').textContent='✓ COMPLETATA';
    }} else show(idx);
  }},MS);
}}
function ferma(){{ if(tmr){{clearInterval(tmr);tmr=null;}}
  document.getElementById('parola').textContent='⏸ PAUSA'; }}
function reset_(){{ ferma();
  document.getElementById('parola').textContent='Premi START';
  document.getElementById('stato').textContent='— / '+P.length; idx=-1; }}
</script>"""
    return _base_html(body)


def render_rey_avlt_som(conn, paziente_id: int) -> None:
    st.subheader("📋 Rey AVLT — Somministrazione")
    mm = _selettore_monitor("rey")

    c_sx, c_dx = st.columns([1, 1])
    with c_sx:
        st.markdown("**Stimoli paziente**")
        lista_sel  = st.radio("Lista", ["Lista A (15 parole)", "Lista B (interferenza)"],
                              horizontal=True, key="rey_lista_sel")
        intervallo = st.slider("Intervallo tra parole (sec)", 0.5, 3.0, 1.0, 0.5, key="rey_ms")
        lista = _REY_A if "A" in lista_sel else _REY_B
        titolo = f"Rey AVLT — {lista_sel}"

        paz_html = _rey_paziente(lista, titolo, int(intervallo * 1000))
        _mostra_stimolo(paz_html, mm, height_1mon=360)

    with c_dx:
        st.markdown("**Pannello clinico**")
        components.html(_timer_html("Tempo prova"), height=130)
        prova_n = st.selectbox("Prova n°", ["I","II","III","IV","V","Interferenza B",
                                             "Richiamo differito","Riconoscimento"],
                               key="rey_prova_n")
        corretti = st.number_input("Parole corrette", 0, 15, 0, 1, key="rey_corr")
        intrusi  = st.number_input("Intrusioni",      0, 20, 0, 1, key="rey_intr")
        note     = st.text_area("Note", height=68, key="rey_note")

    if st.button("💾 Salva questa prova", key="rey_salva"):
        _salva_test(conn, paziente_id, "Rey-AVLT", {
            "lista": lista_sel, "prova": prova_n,
            "corretti": corretti, "intrusioni": intrusi,
            "note": note, "data": datetime.date.today().isoformat()
        })


# ══════════════════════════════════════════════════════════════════════
#  2. TMT A / B
# ══════════════════════════════════════════════════════════════════════

def _tmt_paziente(versione: str) -> str:
    """
    TMT interattivo: il paziente clicca i cerchi nell'ordine corretto.
    Versione A: 1-2-3-...-25
    Versione B: 1-A-2-B-3-C-...-13
    """
    n = 25
    random.seed(42 if versione == "A" else 99)
    positions = [(random.randint(60, 880), random.randint(60, 560)) for _ in range(n)]

    if versione == "A":
        labels = [str(i) for i in range(1, n + 1)]
        sequence = list(range(n))
    else:
        nums = list(range(1, 14))
        lets = list("ABCDEFGHIJKLM")
        seq_labels = []
        for i in range(13):
            seq_labels.append(str(nums[i]))
            seq_labels.append(lets[i])
        labels = seq_labels
        sequence = list(range(len(labels)))

    n_nodes = len(labels)
    positions_ext = [(random.randint(60, 880), random.randint(60, 560))
                     for _ in range(n_nodes)]

    nodes_js = json.dumps([{"x": x, "y": y, "label": l}
                            for (x, y), l in zip(positions_ext, labels)])
    seq_js   = json.dumps(sequence)

    body = f"""
<div class="title">TMT — Versione {versione}</div>
<div class="sub" id="stato">Tocca i cerchi nell'ordine corretto</div>
<svg id="canvas" width="940" height="620"
     style="background:#161b22;border-radius:12px;cursor:pointer;display:block;margin:16px auto">
</svg>
<div class="sub" id="result" style="color:#f0f6fc"></div>
<div class="btn-row">
  <button onclick="restart()">↺ Ricomincia</button>
</div>
<script>
const NODES  = {nodes_js};
const SEQ    = {seq_js};
const svg    = document.getElementById('canvas');
let step=0, errori=0, t0=null, lines=[];

function mkSvgEl(tag,attrs){{
  const el=document.createElementNS('http://www.w3.org/2000/svg',tag);
  for(const[k,v] of Object.entries(attrs)) el.setAttribute(k,v);
  return el;
}}

function draw(){{
  svg.innerHTML='';
  // linee già tracciate
  for(const[a,b] of lines){{
    const na=NODES[a],nb=NODES[b];
    const l=mkSvgEl('line',{{x1:na.x,y1:na.y,x2:nb.x,y2:nb.y,
      stroke:'#2ea44f','stroke-width':3}});
    svg.appendChild(l);
  }}
  // nodi
  NODES.forEach((n,i)=>{{
    const g=mkSvgEl('g',{{}});
    const done=lines.some(([a])=>a===i)||step>i;
    const c=mkSvgEl('circle',{{cx:n.x,cy:n.y,r:28,
      fill: done?'#2ea44f': i===SEQ[step]?'#0969da':'#21262d',
      stroke: i===SEQ[step]?'#58a6ff':'#444c56','stroke-width':2,
      style:'cursor:pointer'}});
    const t=mkSvgEl('text',{{x:n.x,y:n.y+1,
      'text-anchor':'middle','dominant-baseline':'central',
      fill:'#f0f6fc','font-size':16,'font-weight':'bold',
      style:'pointer-events:none'}});
    t.textContent=n.label;
    g.appendChild(c); g.appendChild(t);
    g.addEventListener('click',()=>click(i));
    svg.appendChild(g);
  }});
}}

function click(i){{
  if(i===SEQ[step]){{
    if(step===0) t0=Date.now();
    if(step>0) lines.push([SEQ[step-1],SEQ[step]]);
    step++;
    if(step>=SEQ.length){{
      const sec=((Date.now()-t0)/1000).toFixed(2);
      document.getElementById('result').textContent=
        `✓ Completato in ${{sec}}s — Errori: ${{errori}}`;
      document.getElementById('stato').textContent='✓ Fine!';
    }} else {{
      document.getElementById('stato').textContent=
        `Prossimo: ${{NODES[SEQ[step]].label}} — Errori: ${{errori}}`;
    }}
  }} else {{
    errori++;
    document.getElementById('stato').textContent=
      `❌ Errore! Prossimo: ${{NODES[SEQ[step]].label}} — Errori: ${{errori}}`;
  }}
  draw();
}}

function restart(){{
  step=0; errori=0; t0=null; lines=[];
  document.getElementById('stato').textContent='Tocca i cerchi nell\\'ordine corretto';
  document.getElementById('result').textContent='';
  draw();
}}

draw();
</script>"""
    return _base_html(body, extra_css="""
    svg text { font-family:'Segoe UI',Arial,sans-serif; }
    """)


def render_tmt_som(conn, paziente_id: int) -> None:
    st.subheader("⏱️ TMT A/B — Somministrazione Interattiva")
    mm = _selettore_monitor("tmt")

    versione = st.radio("Versione", ["A (numeri)", "B (numeri + lettere)"],
                        horizontal=True, key="tmt_vers")
    v = "A" if "A" in versione else "B"

    paz_html = _tmt_paziente(v)
    c_sx, c_dx = st.columns([2, 1])
    with c_sx:
        st.markdown(f"**Stimolo paziente — TMT {v}**")
        _mostra_stimolo(paz_html, mm, height_1mon=680)
    with c_dx:
        st.markdown("**Pannello clinico**")
        components.html(_timer_html(f"TMT {v}"), height=130)
        st.caption("Il TMT interattivo registra tempo ed errori autonomamente. "
                   "Inserisci qui i valori dopo la sessione.")
        tempo  = st.number_input("Tempo (sec)", 0.0, 600.0, 0.0, 0.5, key="tmt_t")
        errori = st.number_input("Errori",      0,   30,    0,   1,   key="tmt_e")
        note   = st.text_area("Note", height=80, key="tmt_note")

    if st.button("💾 Salva TMT", key="tmt_salva"):
        _salva_test(conn, paziente_id, f"TMT-{v}", {
            "versione": v, "tempo_sec": float(tempo), "errori": int(errori),
            "note": note, "data": datetime.date.today().isoformat()
        })


# ══════════════════════════════════════════════════════════════════════
#  3. TEST DI CANCELLAZIONE (Benso)
# ══════════════════════════════════════════════════════════════════════

_CAN_SIMBOLI = ["★","●","▲","■","◆","✦","○","△","□","◇"]

def _cancellazione_paziente(target_idx: int = 0, n_col: int = 20,
                             n_righe: int = 12) -> str:
    """Griglia di simboli interattiva. Il paziente clicca sul simbolo target."""
    random.seed(7)
    target = _CAN_SIMBOLI[target_idx]
    altri  = [s for i, s in enumerate(_CAN_SIMBOLI) if i != target_idx]
    n_tot  = n_col * n_righe
    n_target = int(n_tot * 0.25)  # ~25% target

    cella = (["T"] * n_target + ["D"] * (n_tot - n_target))
    random.shuffle(cella)

    rows_html = ""
    for r in range(n_righe):
        rows_html += "<tr>"
        for c in range(n_col):
            i = r * n_col + c
            sim = target if cella[i] == "T" else random.choice(altri)
            cls = "t" if cella[i] == "T" else "d"
            rows_html += f'<td class="{cls}" onclick="click_cell(this,\'{cls}\')">{sim}</td>'
        rows_html += "</tr>"

    body = f"""
<div class="title">Cancella: <span style="color:#f7c948;font-size:3rem">{target}</span></div>
<div class="sub" id="stato">Clicca su tutti i <strong>{target}</strong></div>
<div style="overflow:auto;max-height:75vh;margin:16px 0">
<table id="grid" style="border-collapse:collapse;margin:auto">
{rows_html}
</table>
</div>
<div id="score" style="font-size:1.4rem;color:#8b949e;text-align:center;margin-top:8px">
  Corretti: 0 | Falsi: 0 | Omissioni: {n_target}
</div>
<script>
let corr=0, falsi=0, omiss={n_target};
function click_cell(el, tipo){{
  if(el.classList.contains('done')) return;
  el.classList.add('done');
  if(tipo==='t'){{ corr++; omiss--; el.style.background='#2ea44f'; el.style.color='#0d1117'; }}
  else{{ falsi++; el.style.background='#b91c1c'; }}
  document.getElementById('score').textContent=
    `Corretti: ${{corr}} | Falsi: ${{falsi}} | Omissioni: ${{omiss}}`;
}}
</script>"""

    extra = """
table td {
  font-size:1.6rem; width:42px; height:42px; text-align:center;
  cursor:pointer; border-radius:4px; transition:background .1s;
  color:#f0f6fc;
}
table td:hover { background:#21262d; }
table td.done  { cursor:default; }"""

    return _base_html(body, extra_css=extra)


def render_cancellazione_som(conn, paziente_id: int) -> None:
    st.subheader("🎯 Test di Cancellazione — Somministrazione Interattiva")
    mm = _selettore_monitor("can")

    c_sx, c_dx = st.columns([2, 1])
    with c_sx:
        st.markdown("**Stimolo paziente**")
        target_label = st.selectbox("Simbolo target",
                                    _CAN_SIMBOLI, index=0, key="can_target")
        target_idx = _CAN_SIMBOLI.index(target_label)
        paz_html = _cancellazione_paziente(target_idx)
        _mostra_stimolo(paz_html, mm, height_1mon=620)

    with c_dx:
        st.markdown("**Pannello clinico**")
        components.html(_timer_html("Tempo cancellazione"), height=130)
        st.caption("Il test interattivo conta autonomamente corretti/falsi/omissioni. "
                   "Inserisci qui i valori finali.")
        corretti  = st.number_input("Hit (corretti)",    0, 200, 0, 1, key="can_hit")
        falsi     = st.number_input("Falsi allarmi",     0, 100, 0, 1, key="can_fa")
        omissioni = st.number_input("Omissioni",         0, 100, 0, 1, key="can_om")
        tempo     = st.number_input("Tempo (sec)",  0.0, 600.0, 0.0, 0.5, key="can_t")
        note      = st.text_area("Note", height=68, key="can_note")

    if st.button("💾 Salva Cancellazione", key="can_salva"):
        _salva_test(conn, paziente_id, "Test-Cancellazione-Interattivo", {
            "target": target_label, "hit": int(corretti),
            "falsi_allarmi": int(falsi), "omissioni": int(omissioni),
            "tempo_sec": float(tempo), "note": note,
            "data": datetime.date.today().isoformat()
        })


# ══════════════════════════════════════════════════════════════════════
#  4. RAN / NOMINAZIONE VELOCE
# ══════════════════════════════════════════════════════════════════════

_RAN_GRIDS = {
    "Colori":   ["🔴","🔵","🟡","🟢","⚫"],
    "Numeri":   ["2","5","8","3","6"],
    "Oggetti":  ["🏠","☀️","🐟","🍎","✈️"],
    "Lettere":  ["A","O","S","P","R"],
}
_RAN_LABELS_TEXT = {
    "Colori":  ["ROSSO","BLU","GIALLO","VERDE","NERO"],
    "Numeri":  ["DUE","CINQUE","OTTO","TRE","SEI"],
    "Oggetti": ["CASA","SOLE","PESCE","MELA","AEREO"],
    "Lettere": ["A","O","S","P","R"],
}


def _ran_paziente(tipo: str, n_col: int = 10, n_righe: int = 5) -> str:
    """Griglia RAN — il paziente nomina ogni elemento da sx a dx."""
    random.seed(12)
    simboli   = _RAN_GRIDS[tipo]
    n_tot     = n_col * n_righe
    griglia   = [random.choice(simboli) for _ in range(n_tot)]
    label_corrente = _RAN_LABELS_TEXT[tipo]

    rows_html = ""
    for r in range(n_righe):
        rows_html += "<tr>"
        for c in range(n_col):
            i = r * n_col + c
            rows_html += (f'<td id="c{i}" onclick="advance({i})">'
                          f'{griglia[i]}</td>')
        rows_html += "</tr>"

    body = f"""
<div class="title">RAN — {tipo}</div>
<div class="sub">Nomina ogni elemento da sinistra a destra</div>
<div style="overflow:auto;margin:20px 0">
  <table id="grid" style="border-collapse:collapse;margin:auto">
  {rows_html}
  </table>
</div>
<div id="pos" style="font-size:1.2rem;color:#8b949e;text-align:center">
  Posizione: 1 / {n_tot}
</div>
<script>
let cur=0, errs=0, t0=null;
function advance(i){{
  if(i!==cur) return;
  if(cur===0) t0=Date.now();
  document.getElementById('c'+cur).style.background='#2ea44f';
  document.getElementById('c'+cur).style.color='#0d1117';
  cur++;
  if(cur>={n_tot}){{
    const s=((Date.now()-t0)/1000).toFixed(2);
    document.getElementById('pos').textContent='✓ Fine — '+s+'s';
  }} else {{
    document.getElementById('c'+cur).style.outline='3px solid #f7c948';
    document.getElementById('pos').textContent='Posizione: '+(cur+1)+' / {n_tot}';
  }}
}}
document.getElementById('c0').style.outline='3px solid #f7c948';
</script>"""

    extra = """
table td {
  font-size:2.2rem; width:74px; height:74px; text-align:center;
  cursor:pointer; border-radius:6px; transition:background .1s;
  color:#f0f6fc; border:1px solid #21262d;
}
table td:hover { background:#21262d; }"""
    return _base_html(body, extra_css=extra)


def render_ran_som(conn, paziente_id: int) -> None:
    st.subheader("⚡ RAN — Somministrazione Interattiva")
    mm = _selettore_monitor("ran")

    c_sx, c_dx = st.columns([2, 1])
    with c_sx:
        tipo = st.selectbox("Tipo stimolo", list(_RAN_GRIDS.keys()), key="ran_tipo")
        paz_html = _ran_paziente(tipo)
        _mostra_stimolo(paz_html, mm, height_1mon=520)

    with c_dx:
        st.markdown("**Pannello clinico**")
        components.html(_timer_html("Tempo RAN"), height=130)
        tempo  = st.number_input("Tempo (sec)", 0.0, 300.0, 0.0, 0.5, key="ran_t")
        errori = st.number_input("Errori",      0,   30,    0,   1,   key="ran_e")
        note   = st.text_area("Note", height=68, key="ran_note")

    if st.button("💾 Salva RAN", key="ran_salva"):
        _salva_test(conn, paziente_id, "RAN-Interattivo", {
            "tipo": tipo, "tempo_sec": float(tempo), "errori": int(errori),
            "note": note, "data": datetime.date.today().isoformat()
        })


# ══════════════════════════════════════════════════════════════════════
#  5. ALPHA SPAN
# ══════════════════════════════════════════════════════════════════════

_ALPHA_PAROLE = [
    "MELA","CASA","LUNA","FIORE","PANE","TRENO","BOSCO","MARE",
    "NOTTE","SOLE","VENTO","PIETRA","FIUME","CAMPO","STELLA",
    "PORTA","NUVOLA","SEDIA","FUOCO","LIBRO","ALBERO","ACQUA"
]


def _alpha_paziente(parole: list) -> str:
    pw_js = json.dumps(parole)
    body = f"""
<div class="title">Alpha Span</div>
<div class="main" id="word">Premi START</div>
<div class="sub"  id="stato">Ricorda e riordina in ordine alfabetico</div>
<div class="btn-row">
  <button onclick="avvia()">▶ START</button>
  <button class="stop" onclick="ferma()">⏹ STOP</button>
</div>
<script>
const W={pw_js};
let idx=0, tmr=null;
function show(i){{
  document.getElementById('word').textContent = i<W.length ? W[i] : '✓ ORA RISPONDI';
  document.getElementById('stato').textContent = (i+1)+' / '+W.length;
}}
function avvia(){{
  if(tmr) clearInterval(tmr);
  idx=0; show(0);
  tmr=setInterval(()=>{{
    idx++;
    if(idx>=W.length){{clearInterval(tmr);tmr=null;
      document.getElementById('word').textContent='✓ ORA RISPONDI';
    }} else show(idx);
  }},2000);
}}
function ferma(){{ if(tmr){{clearInterval(tmr);tmr=null;}}
  document.getElementById('word').textContent='⏸ PAUSA'; }}
</script>"""
    return _base_html(body)


def render_alpha_span_som(conn, paziente_id: int) -> None:
    st.subheader("🔤 Alpha Span — Somministrazione")
    mm = _selettore_monitor("alpha")

    span = st.slider("Lunghezza sequenza (span)", 2, 7, 3, key="alpha_span")
    random.seed(span * 17)
    parole_sel = random.sample(_ALPHA_PAROLE, span)

    c_sx, c_dx = st.columns([1, 1])
    with c_sx:
        st.markdown(f"**Sequenza da presentare:** `{'  →  '.join(parole_sel)}`")
        st.caption("Risposta corretta (ord. alfabetico): " +
                   "  →  ".join(sorted(parole_sel)))
        paz_html = _alpha_paziente(parole_sel)
        _mostra_stimolo(paz_html, mm, height_1mon=340)

    with c_dx:
        components.html(_timer_html("Tempo Alpha Span"), height=130)
        corretto = st.radio("Risposta", ["✅ Corretta", "❌ Errore"],
                            horizontal=True, key="alpha_risp")
        risposta_paziente = st.text_input("Risposta del paziente (trascrivi)",
                                          key="alpha_risp_testo")
        note = st.text_area("Note", height=68, key="alpha_note")

    if st.button("💾 Salva Alpha Span", key="alpha_salva"):
        _salva_test(conn, paziente_id, "Alpha-Span-Interattivo", {
            "span": span, "parole": parole_sel,
            "risposta_corretta": sorted(parole_sel),
            "risposta_paziente": risposta_paziente,
            "esito": corretto, "note": note,
            "data": datetime.date.today().isoformat()
        })


# ══════════════════════════════════════════════════════════════════════
#  6. UPDATING
# ══════════════════════════════════════════════════════════════════════

def _updating_paziente(sequenza: list, n_ricordare: int) -> str:
    seq_js = json.dumps(sequenza)
    body = f"""
<div class="title">Updating — ricorda gli ultimi {n_ricordare}</div>
<div class="main" id="item" style="font-size:6rem">—</div>
<div class="sub"  id="stato">Premi START · Ricorda solo gli ultimi {n_ricordare}</div>
<div class="btn-row">
  <button onclick="avvia()">▶ START</button>
  <button class="stop" onclick="ferma()">⏹ STOP</button>
</div>
<script>
const SEQ={seq_js}, N={n_ricordare};
let idx=0, tmr=null;
function avvia(){{
  if(tmr) clearInterval(tmr);
  idx=0;
  document.getElementById('item').textContent=SEQ[0];
  document.getElementById('stato').textContent='1 / '+SEQ.length;
  tmr=setInterval(()=>{{
    idx++;
    if(idx>=SEQ.length){{
      clearInterval(tmr); tmr=null;
      document.getElementById('item').textContent='✓';
      document.getElementById('stato').textContent='Dimmi gli ultimi '+N;
    }} else {{
      document.getElementById('item').textContent=SEQ[idx];
      document.getElementById('stato').textContent=(idx+1)+' / '+SEQ.length;
    }}
  }},1500);
}}
function ferma(){{ if(tmr){{clearInterval(tmr);tmr=null;}} }}
</script>"""
    return _base_html(body)


def render_updating_som(conn, paziente_id: int) -> None:
    st.subheader("🔃 Updating — Somministrazione")
    mm = _selettore_monitor("upd")

    n_ricordare = st.radio("N da ricordare", [3, 4, 5], horizontal=True, key="upd_n")
    n_sequenza  = st.slider("Lunghezza sequenza", 6, 15, 9, key="upd_len")
    random.seed(n_ricordare * 100 + n_sequenza)
    sequenza = [str(random.randint(1, 9)) for _ in range(n_sequenza)]
    corretta = sequenza[-n_ricordare:]

    c_sx, c_dx = st.columns([1, 1])
    with c_sx:
        st.markdown(f"**Sequenza:** `{' - '.join(sequenza)}`")
        st.caption(f"Risposta attesa (ultimi {n_ricordare}): `{' - '.join(corretta)}`")
        paz_html = _updating_paziente(sequenza, n_ricordare)
        _mostra_stimolo(paz_html, mm, height_1mon=340)

    with c_dx:
        components.html(_timer_html("Tempo Updating"), height=130)
        risposta = st.text_input("Risposta paziente", key="upd_risp")
        corretto = st.radio("Esito", ["✅ Corretto", "❌ Errore"],
                            horizontal=True, key="upd_esito")
        note = st.text_area("Note", height=68, key="upd_note")

    if st.button("💾 Salva Updating", key="upd_salva"):
        _salva_test(conn, paziente_id, "Updating-Interattivo", {
            "n_ricordare": n_ricordare, "sequenza": sequenza,
            "risposta_attesa": corretta, "risposta_paziente": risposta,
            "esito": corretto, "note": note,
            "data": datetime.date.today().isoformat()
        })


# ══════════════════════════════════════════════════════════════════════
#  7. FLUENZA VERBALE
# ══════════════════════════════════════════════════════════════════════

def _fluenza_paziente(lettera_o_categoria: str, tipo: str) -> str:
    body = f"""
<div class="title">Fluenza {tipo}</div>
<div class="main" style="font-size:7rem;letter-spacing:8px;color:#f7c948">
  {lettera_o_categoria}
</div>
<div class="sub" id="stato">
  {"Dì tutte le parole che iniziano con" if tipo=="Fonemica" else "Dì tutte le"} 
  <strong>{lettera_o_categoria}</strong> in 60 secondi
</div>
<div id="timer_big" style="font-size:3.5rem;font-weight:700;color:#2ea44f;margin:20px 0">60.0</div>
<div class="btn-row">
  <button onclick="avvia()">▶ START</button>
  <button class="stop" onclick="ferma()">⏹ STOP</button>
</div>
<script>
let t=60000, iv=null, start=null;
function avvia(){{
  if(iv) return;
  start=Date.now();
  iv=setInterval(()=>{{
    t=60000-(Date.now()-start);
    if(t<=0){{t=0;clearInterval(iv);iv=null;
      document.getElementById('timer_big').style.color='#b91c1c';
      document.getElementById('stato').textContent='⏱ Tempo scaduto!';
    }}
    document.getElementById('timer_big').textContent=(t/1000).toFixed(1);
  }},100);
}}
function ferma(){{ if(iv){{clearInterval(iv);iv=null;}} }}
</script>"""
    return _base_html(body)


def render_fluenza_som(conn, paziente_id: int) -> None:
    st.subheader("🗣️ Fluenza Verbale — Somministrazione")
    mm = _selettore_monitor("fl")

    tipo = st.radio("Tipo", ["Fonemica (lettera)", "Semantica (categoria)"],
                    horizontal=True, key="fl_tipo")
    if "Fonemica" in tipo:
        stimolo = st.selectbox("Lettera", list("FSAPRCLMGB"), key="fl_lettera")
        tipo_label = "Fonemica"
    else:
        stimolo = st.selectbox("Categoria",
                               ["ANIMALI","CIBO","VEICOLI","FIORI","COLORI",
                                "SPORT","VESTITI","MOBILI"], key="fl_cat")
        tipo_label = "Semantica"

    c_sx, c_dx = st.columns([1, 1])
    with c_sx:
        paz_html = _fluenza_paziente(stimolo, tipo_label)
        _mostra_stimolo(paz_html, mm, height_1mon=420)

    with c_dx:
        components.html(_timer_html("Timer backup clinico"), height=130)
        n_parole = st.number_input("Parole prodotte", 0, 60, 0, 1, key="fl_n")
        intrusioni = st.number_input("Intrusioni / ripetizioni", 0, 20, 0, 1, key="fl_intr")
        elenco = st.text_area("Elenco parole (trascrivi)", height=100, key="fl_elenco")
        note   = st.text_area("Note", height=68, key="fl_note")

    if st.button("💾 Salva Fluenza", key="fl_salva"):
        _salva_test(conn, paziente_id, f"Fluenza-{tipo_label}", {
            "tipo": tipo_label, "stimolo": stimolo,
            "n_parole": int(n_parole), "intrusioni": int(intrusioni),
            "elenco": elenco, "note": note,
            "data": datetime.date.today().isoformat()
        })


# ══════════════════════════════════════════════════════════════════════
#  8. SWITCH DI CALCOLO
# ══════════════════════════════════════════════════════════════════════

def _switch_operazioni(foglio: str, n: int = 30) -> list:
    """Genera operazioni per foglio B (same) o C (alternato)."""
    random.seed(42 if foglio == "B" else 99)
    ops = []
    for i in range(n):
        a = random.randint(2, 12)
        b = random.randint(2, 12)
        if foglio == "B":
            ops.append(f"{a} + {b}")
        else:
            op = "+" if i % 2 == 0 else "-"
            if op == "-" and a < b:
                a, b = b, a
            ops.append(f"{a} {op} {b}")
    return ops


def _switch_paziente(foglio: str, operazioni: list) -> str:
    ops_html = "".join(
        f'<div class="op" id="op{i}" onclick="avanza({i})">{op} = ?</div>'
        for i, op in enumerate(operazioni)
    )
    body = f"""
<div class="title">Switch di Calcolo — Foglio {foglio}</div>
<div class="sub">Risolvi ogni operazione, tocca per passare alla successiva</div>
<div id="current" style="font-size:4.5rem;font-weight:700;margin:24px 0;
     min-height:80px;text-align:center;color:#f7c948">
  {operazioni[0]} = ?
</div>
<div class="sub" id="pos">1 / {len(operazioni)}</div>
<div class="btn-row">
  <button onclick="avanza_btn()">→ Avanti</button>
  <button class="stop" onclick="reset_()">↺ Reset</button>
</div>
<script>
const OPS={json.dumps(operazioni)};
let cur=0, t0=null, errs=0;
function show(i){{
  document.getElementById('current').textContent = i<OPS.length ? OPS[i]+' = ?' : '✓ FINE';
  document.getElementById('pos').textContent = (i+1)+' / '+OPS.length;
}}
function avanza(i){{ if(i!==cur) return; avanza_comune(); }}
function avanza_btn(){{ avanza_comune(); }}
function avanza_comune(){{
  if(cur===0) t0=Date.now();
  cur++;
  if(cur>=OPS.length){{
    const s=((Date.now()-t0)/1000).toFixed(2);
    document.getElementById('current').textContent='✓ Fine — '+s+'s';
    document.getElementById('pos').textContent='Completato';
  }} else show(cur);
}}
function reset_(){{ cur=0; t0=null; show(0); }}
show(0);
</script>"""
    return _base_html(body, extra_css="""
.op { display:none; }
""")


def render_switch_som(conn, paziente_id: int) -> None:
    st.subheader("🔄 Switch di Calcolo — Somministrazione")
    mm = _selettore_monitor("sw")

    foglio = st.radio("Foglio", ["B (operazioni omogenee)", "C (operazioni alternate)"],
                      horizontal=True, key="sw_foglio")
    f = "B" if "B" in foglio else "C"
    n_op = st.slider("Numero operazioni", 10, 40, 30, key="sw_nop")
    ops = _switch_operazioni(f, n_op)

    c_sx, c_dx = st.columns([2, 1])
    with c_sx:
        paz_html = _switch_paziente(f, ops)
        _mostra_stimolo(paz_html, mm, height_1mon=420)

    with c_dx:
        components.html(_timer_html(f"Tempo Foglio {f}"), height=130)
        tempo  = st.number_input("Tempo (sec)", 0.0, 600.0, 0.0, 0.5, key="sw_t")
        errori = st.number_input("Errori",      0,   50,    0,   1,   key="sw_e")
        note   = st.text_area("Note", height=68, key="sw_note")

    if st.button(f"💾 Salva Foglio {f}", key="sw_salva"):
        _salva_test(conn, paziente_id, f"Switch-Calcolo-F{f}", {
            "foglio": f, "tempo_sec": float(tempo), "errori": int(errori),
            "n_operazioni": n_op, "note": note,
            "data": datetime.date.today().isoformat()
        })


# ══════════════════════════════════════════════════════════════════════
#  9. NUMERAZIONE
# ══════════════════════════════════════════════════════════════════════

def _numerazione_paziente(direzione: str) -> str:
    testo = "Conta da 1 a 100" if direzione == "avanti" else "Conta da 100 a 1"
    inizio = "1" if direzione == "avanti" else "100"
    body = f"""
<div class="title">Numerazione</div>
<div class="main" style="font-size:5rem;color:#f7c948">{testo}</div>
<div class="sub" style="margin-top:30px">il più velocemente possibile</div>
<div id="timer_disp" style="font-size:3rem;font-weight:700;color:#2ea44f;margin:24px 0">00.0s</div>
<div class="btn-row">
  <button onclick="avvia()">▶ START</button>
  <button class="stop" onclick="ferma()">⏹ STOP</button>
</div>
<script>
let t0=null,iv=null;
function avvia(){{
  if(iv) return;
  t0=Date.now();
  iv=setInterval(()=>{{
    document.getElementById('timer_disp').textContent=
      ((Date.now()-t0)/1000).toFixed(1)+'s';
  }},100);
}}
function ferma(){{
  if(iv){{clearInterval(iv);iv=null;
    document.getElementById('timer_disp').style.color='#b91c1c';
  }}
}}
</script>"""
    return _base_html(body)


def render_numerazione_som(conn, paziente_id: int) -> None:
    st.subheader("🔢 Numerazione — Somministrazione")
    mm = _selettore_monitor("num")

    direzione = st.radio("Direzione", ["1 → 100 (avanti)", "100 → 1 (indietro)"],
                         horizontal=True, key="num_dir")
    d = "avanti" if "avanti" in direzione else "indietro"

    c_sx, c_dx = st.columns([1, 1])
    with c_sx:
        paz_html = _numerazione_paziente(d)
        _mostra_stimolo(paz_html, mm, height_1mon=380)

    with c_dx:
        components.html(_timer_html(f"Numerazione {d}"), height=130)
        tempo  = st.number_input("Tempo (sec)", 0.0, 300.0, 0.0, 0.5, key="num_t")
        errori = st.number_input("Errori",      0,   20,    0,   1,   key="num_e")
        note   = st.text_area("Note", height=68, key="num_note")

    if st.button("💾 Salva Numerazione", key="num_salva"):
        _salva_test(conn, paziente_id, f"Numerazione-{d}", {
            "direzione": d, "tempo_sec": float(tempo), "errori": int(errori),
            "note": note, "data": datetime.date.today().isoformat()
        })


# ══════════════════════════════════════════════════════════════════════
#  10. STROOP
# ══════════════════════════════════════════════════════════════════════

_STROOP_COLORI = ["ROSSO","BLU","VERDE","GIALLO","NERO"]
_STROOP_HEX    = {"ROSSO":"#ef4444","BLU":"#3b82f6",
                  "VERDE":"#22c55e","GIALLO":"#f7c948","NERO":"#9ca3af"}


def _stroop_paziente(parte: str, n: int = 50) -> str:
    random.seed({"P": 1, "C": 2, "PC": 3}[parte])
    if parte == "P":
        items = [(w, "#f0f6fc", w) for w in
                 [random.choice(_STROOP_COLORI) for _ in range(n)]]
        istr = "Leggi la PAROLA"
    elif parte == "C":
        items = [("█████", _STROOP_HEX[c], c)
                 for c in [random.choice(_STROOP_COLORI) for _ in range(n)]]
        istr = "Nomina il COLORE"
    else:
        parole = [random.choice(_STROOP_COLORI) for _ in range(n)]
        colori = [random.choice(_STROOP_COLORI) for _ in range(n)]
        items  = [(p, _STROOP_HEX[c], c)
                  for p, c in zip(parole, colori)]
        istr = "Nomina il COLORE DELL'INCHIOSTRO (ignora la parola)"

    cols = 10
    righe_html = ""
    for r in range(math.ceil(n / cols)):
        righe_html += "<tr>"
        for c in range(cols):
            i = r * cols + c
            if i >= n:
                break
            parola, hex_col, _ = items[i]
            righe_html += (f'<td style="color:{hex_col};font-size:1.5rem;'
                           f'font-weight:700;padding:6px 10px;white-space:nowrap">'
                           f'{parola}</td>')
        righe_html += "</tr>"

    body = f"""
<div class="title">Stroop — Parte {parte}</div>
<div class="sub" style="font-size:1.3rem;margin-bottom:20px">{istr}</div>
<div style="overflow:auto">
  <table style="border-collapse:collapse;margin:auto">{righe_html}</table>
</div>"""
    return _base_html(body, bg="#161b22")


def render_stroop_som(conn, paziente_id: int) -> None:
    st.subheader("🎨 Stroop — Somministrazione")
    mm = _selettore_monitor("stroop")

    parte = st.radio("Parte", ["P (parole)", "C (colori)", "PC (interferenza)"],
                     horizontal=True, key="stroop_parte")
    p = parte.split(" ")[0]

    c_sx, c_dx = st.columns([2, 1])
    with c_sx:
        paz_html = _stroop_paziente(p)
        _mostra_stimolo(paz_html, mm, height_1mon=520)

    with c_dx:
        components.html(_timer_html(f"Stroop {p}"), height=130)
        tempo  = st.number_input("Tempo (sec)", 0.0, 300.0, 0.0, 0.5, key="stroop_t")
        errori = st.number_input("Errori",      0,   30,    0,   1,   key="stroop_e")
        note   = st.text_area("Note", height=68, key="stroop_note")

    if st.button(f"💾 Salva Stroop {p}", key="stroop_salva"):
        _salva_test(conn, paziente_id, f"Stroop-{p}", {
            "parte": p, "tempo_sec": float(tempo), "errori": int(errori),
            "note": note, "data": datetime.date.today().isoformat()
        })


# ══════════════════════════════════════════════════════════════════════
#  ENTRY POINT PRINCIPALE
# ══════════════════════════════════════════════════════════════════════

_TEST_LISTA = {
    "Rey AVLT":            render_rey_avlt_som,
    "TMT A/B":             render_tmt_som,
    "Cancellazione":       render_cancellazione_som,
    "RAN":                 render_ran_som,
    "Alpha Span":          render_alpha_span_som,
    "Updating":            render_updating_som,
    "Fluenza Verbale":     render_fluenza_som,
    "Switch di Calcolo":   render_switch_som,
    "Numerazione":         render_numerazione_som,
    "Stroop":              render_stroop_som,
}


def render_somministrazione(conn, paziente_id: int) -> None:
    """
    Entry point. Aggiungilo in app_main_router.py:
        from .ui_test_somministrazione import render_somministrazione
    """
    st.title("🖥️ Somministrazione Interattiva Test")
    st.caption(
        "Ogni test ha una schermata per il paziente (stimoli grandi, puliti) "
        "e un pannello clinico (timer, punteggi, note). "
        "Scegli la modalità monitor prima di ogni test."
    )

    st.info(
        "**Come usare il secondo monitor:**\n"
        "1. Seleziona *🖥️🖥️ 2 monitor*\n"
        "2. Clicca **Apri su secondo monitor** → si apre una nuova finestra del browser\n"
        "3. Trascina la nuova finestra sul secondo schermo e mettila a schermo intero (F11)\n"
        "4. Il pannello clinico rimane su questo schermo"
    )

    test_sel = st.selectbox(
        "Seleziona test da somministrare",
        list(_TEST_LISTA.keys()),
        key="som_test_sel"
    )
    st.markdown("---")

    fn = _TEST_LISTA.get(test_sel)
    if fn:
        fn(conn, paziente_id)
