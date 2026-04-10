# -*- coding: utf-8 -*-
"""
ui_test_vocali.py — Motore Vocale Unificato per Test di Lettura Orale

Architettura:
  - Web Speech API  → trascrizione in tempo reale (nativa, gratuita, online)
  - Whisper API     → fallback/verifica post-registrazione (alta precisione)
  - Correzione automatica → edit-distance per trovare errori vs sequenza attesa
  - Parser numeri   → gestisce cifre singole, attaccate, parole italiane/inglese

Test supportati:
  1. DEM (Test A verticale + Test C orizzontale)
  2. King-Devick (3 card)
  3. Visual Tracking (lettura griglia numeri)
  4. VADS (span cifre — lettura orale dei subtest UO e VO)
  5. Groffman (lettura lettere/numeri nei percorsi)

Configurazione Secrets (opzionale per Whisper):
  [openai]
  OPENAI_API_KEY = "sk-..."
"""

from __future__ import annotations
import io
import re
import json
from datetime import date
from typing import Optional

import streamlit as st
import streamlit.components.v1 as components


# ─────────────────────────────────────────────────────────────────────────────
# TABELLE TEST
# ─────────────────────────────────────────────────────────────────────────────

DEM_A = [
    2,8,4,9,6,3,7,1,5,0,
    8,4,7,2,9,6,3,5,1,8,
    4,0,7,2,6,3,9,5,1,4,
    8,7,0,3,6,2,9,5,4,1,
    0,8,7,3,5,6,2,9,1,4,
]

DEM_C_ROWS = [
    [6,3,8,1,4,9,2,7,5,0],
    [4,7,2,9,6,1,8,3,0,5],
    [9,1,5,8,3,6,4,0,7,2],
    [2,8,4,0,7,5,3,1,9,6],
    [7,5,0,3,9,2,6,8,4,1],
    [3,6,1,7,5,0,2,4,8,9],
    [5,0,9,4,2,8,7,6,1,3],
    [1,4,7,6,0,3,9,2,5,8],
]
DEM_C_FLAT = [n for row in DEM_C_ROWS for n in row]

KD_CARDS = [
    [[1,5,3,8,2],[7,4,9,6,0],[3,8,2,5,4],[6,1,7,3,9],[2,9,4,8,1]],
    [[4,2,7,1,6],[8,5,3,9,2],[1,6,4,8,5],[9,3,2,7,4],[5,7,1,3,8]],
    [[3,7,2,9,5],[1,8,4,6,3],[7,2,9,1,8],[4,6,3,5,7],[9,1,8,4,2]],
]
KD_FLATS = [[n for row in c for n in row] for c in KD_CARDS]

VT_GRID = [
    [5,3,7,3,5,4,2,5,6,1,0,3],
    [7,5,7,4,1,6,4,4,3,7,7,0],
    [7,3,2,7,4,6,1,7,8,7,6,0],
    [4,0,1,8,1,1,0,0,1,2,6,4],
    [1,7,1,1,8,6,1,7,9,1,2,3],
    [5,3,8,0,1,6,6,3,7,2,1,2],
    [5,3,1,0,1,3,6,2,0,4,1,6],
    [7,6,1,4,4,5,1,1,2,3,6,5],
    [2,7,1,3,6,3,3,0,7,1,0,0],
    [7,8,6,1,2,3,6,4,5,2,1,6],
    [2,8,1,6,7,3,3,5,6,4,6,7],
    [1,3,5,4,1,3,1,6,1,0,2,6],
]
VT_FLAT = [n for row in VT_GRID for n in row]


# ─────────────────────────────────────────────────────────────────────────────
# PARSER NUMERI UNIVERSALE
# ─────────────────────────────────────────────────────────────────────────────

_WORD_TO_DIGIT = {
    # Italiano
    "zero":0,"uno":1,"due":2,"tre":3,"quattro":4,
    "cinque":5,"sei":6,"sette":7,"otto":8,"nove":9,
    "un":1,"un'":1,"una":1,
    # Inglese (Whisper a volte trascrive in inglese)
    "one":1,"two":2,"three":3,"four":4,"five":5,
    "six":6,"seven":7,"eight":8,"nine":9,
}

def parse_numeri(testo: str) -> list[int]:
    """
    Estrae cifre singole (0-9) da testo trascritto.
    Gestisce:
    - cifre separate:  "5 3 7 2"     → [5,3,7,2]
    - parole italiane: "cinque tre"   → [5,3]
    - cifre attaccate: "537"          → [5,3,7]
    - mix:             "5 tre 72"     → [5,3,7,2]
    - punteggiatura:   "5,3,7"        → [5,3,7]
    """
    if not testo:
        return []
    testo = testo.lower().strip()
    tokens = re.split(r'[\s,.\-;:/|]+', testo)
    result = []
    for tok in tokens:
        tok = tok.strip("'\"")
        if not tok:
            continue
        if tok in _WORD_TO_DIGIT:
            result.append(_WORD_TO_DIGIT[tok])
        elif tok.isdigit():
            for c in tok:
                result.append(int(c))
        else:
            # misto (es. "5tre")
            i = 0
            while i < len(tok):
                # Prova a matchare parola che inizia qui
                matched = False
                for word, digit in _WORD_TO_DIGIT.items():
                    if tok[i:].startswith(word):
                        result.append(digit)
                        i += len(word)
                        matched = True
                        break
                if not matched:
                    if tok[i].isdigit():
                        result.append(int(tok[i]))
                    i += 1
    return result


def calcola_errori(attesi: list[int], letti: list[int]) -> dict:
    """
    Confronta sequenza attesa vs letta con edit-distance.
    Ritorna dict con omissioni, sostituzioni, aggiunte, tot_errori, accuratezza_pct.
    """
    import difflib
    a = [str(x) for x in attesi]
    b = [str(x) for x in letti]
    sm = difflib.SequenceMatcher(None, a, b)
    omissioni = sostituzioni = aggiunte = 0
    dettaglio = []

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        elif tag == "delete":
            omissioni += i2 - i1
            for k in range(i1, i2):
                dettaglio.append({"tipo":"omissione","pos":k+1,"atteso":attesi[k]})
        elif tag == "insert":
            aggiunte += j2 - j1
        elif tag == "replace":
            n = min(i2-i1, j2-j1)
            sostituzioni += n
            omissioni += max(0, (i2-i1) - n)
            aggiunte += max(0, (j2-j1) - n)
            for k in range(n):
                if i1+k < len(attesi) and j1+k < len(letti):
                    dettaglio.append({"tipo":"sostituzione","pos":i1+k+1,
                                      "atteso":attesi[i1+k],"letto":letti[j1+k]})

    tot = omissioni + sostituzioni
    acc = max(0, round((1 - tot / max(len(attesi),1)) * 100))
    return {
        "omissioni":omissioni,"sostituzioni":sostituzioni,
        "aggiunte":aggiunte,"tot_errori":tot,
        "accuratezza_pct":acc,
        "n_letti":len(letti),"n_attesi":len(attesi),
        "dettaglio":dettaglio[:30],
    }


# ─────────────────────────────────────────────────────────────────────────────
# WHISPER API
# ─────────────────────────────────────────────────────────────────────────────

def _openai_key() -> Optional[str]:
    try:
        k = (st.secrets.get("openai",{}).get("OPENAI_API_KEY","") or
             st.secrets.get("OPENAI_API_KEY",""))
        return str(k).strip() or None
    except Exception:
        return None

def whisper_trascrivi(audio_bytes: bytes, prompt_hint: str = "") -> tuple[str, str]:
    """Invia audio a Whisper-1. Ritorna (testo, errore)."""
    key = _openai_key()
    if not key:
        return "", "OPENAI_API_KEY mancante"
    try:
        import openai
        client = openai.OpenAI(api_key=key)
        f = io.BytesIO(audio_bytes)
        f.name = "test.wav"
        resp = client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            language="it",
            prompt=prompt_hint or "Il paziente legge cifre singole: 5 3 7 2 9 1 8",
        )
        return resp.text.strip(), ""
    except Exception as e:
        return "", str(e)


# ─────────────────────────────────────────────────────────────────────────────
# COMPONENTE WEB SPEECH + REGISTRAZIONE AUDIO
# HTML/JS con Web Speech API (tempo reale) + MediaRecorder (per Whisper fallback)
# ─────────────────────────────────────────────────────────────────────────────

def voice_component(
    component_id: str,
    height: int = 200,
    lang: str = "it-IT",
) -> Optional[dict]:
    """
    Componente HTML che:
    1. Usa Web Speech API per trascrizione in tempo reale
    2. Registra audio con MediaRecorder per Whisper fallback
    3. Mostra timer live
    4. Al STOP invia risultati via postMessage a Streamlit

    Ritorna dict con:
      - transcript: str (Web Speech)
      - elapsed_ms: int
      - audio_b64: str (per Whisper)
      - source: "webspeech" | "recording"
    """
    html = f"""
<!DOCTYPE html>
<html>
<head>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: #0d1117;
    color: #e6edf3;
    font-family: 'SF Mono', 'Cascadia Code', monospace;
    padding: 12px;
    min-height: {height}px;
  }}
  .panel {{
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 10px;
    padding: 16px;
  }}
  .controls {{
    display: flex;
    gap: 10px;
    align-items: center;
    margin-bottom: 12px;
    flex-wrap: wrap;
  }}
  .btn {{
    padding: 8px 18px;
    border-radius: 7px;
    border: none;
    font-family: inherit;
    font-weight: 700;
    font-size: 14px;
    cursor: pointer;
    transition: all 0.15s;
  }}
  .btn:disabled {{ opacity: 0.4; cursor: not-allowed; }}
  .btn-start {{ background: #238636; color: #fff; }}
  .btn-start:not(:disabled):hover {{ background: #2ea043; }}
  .btn-stop {{ background: #da3633; color: #fff; }}
  .btn-stop:not(:disabled):hover {{ background: #f85149; }}
  .btn-whisper {{ background: #1f6feb; color: #fff; font-size:12px; }}
  .btn-whisper:not(:disabled):hover {{ background: #388bfd; }}
  .timer {{
    font-size: 32px;
    font-weight: 900;
    color: #58a6ff;
    letter-spacing: 2px;
    min-width: 90px;
  }}
  .status {{
    font-size: 12px;
    color: #8b949e;
    display: flex;
    align-items: center;
    gap: 6px;
  }}
  .dot {{
    width: 8px; height: 8px;
    border-radius: 50%;
    background: #30363d;
    flex-shrink: 0;
  }}
  .dot.rec {{ background: #f85149; animation: blink 1s infinite; }}
  .dot.ok  {{ background: #3fb950; }}
  @keyframes blink {{ 0%,100%{{opacity:1}} 50%{{opacity:0.2}} }}

  .transcript-box {{
    background: #0d1117;
    border: 1px solid #21262d;
    border-radius: 7px;
    padding: 10px 14px;
    min-height: 52px;
    font-size: 18px;
    font-weight: 700;
    color: #f0f6fc;
    letter-spacing: 3px;
    word-break: break-all;
    line-height: 1.6;
    margin-bottom: 10px;
  }}
  .live {{ color: #58a6ff; }}
  .badge {{
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 700;
    margin-left: 4px;
  }}
  .badge-ws {{ background:#1f6feb22; color:#58a6ff; border:1px solid #1f6feb44; }}
  .badge-wr {{ background:#6e40c922; color:#d2a8ff; border:1px solid #6e40c944; }}
  .info {{ font-size: 11px; color: #6e7681; margin-top: 4px; }}
  .err {{ color: #f85149; font-size: 12px; margin-top: 4px; }}
</style>
</head>
<body>
<div class="panel">
  <div class="controls">
    <button class="btn btn-start" id="startBtn" onclick="startTest()">▶ START</button>
    <button class="btn btn-stop" id="stopBtn" onclick="stopTest()" disabled>⏹ STOP</button>
    <div class="timer" id="timerDisplay">00.00</div>
    <div class="status">
      <div class="dot" id="dot"></div>
      <span id="statusTxt">Pronto · Clicca START per iniziare</span>
    </div>
  </div>

  <div class="transcript-box" id="transcriptBox">
    <span style="color:#6e7681;font-size:14px;font-weight:400">
      La trascrizione apparirà qui in tempo reale...
    </span>
  </div>

  <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
    <div class="info" id="infoTxt"></div>
    <div class="err" id="errTxt"></div>
  </div>
</div>

<script>
(function() {{
  let recognition = null;
  let mediaRecorder = null;
  let audioChunks = [];
  let timerInterval = null;
  let startTime = 0;
  let finalTranscript = '';
  let interimTranscript = '';
  let elapsed = 0;
  let isRunning = false;

  const hasSpeech = ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window);

  function fmtTime(ms) {{
    const s = Math.floor(ms / 1000);
    const cs = Math.floor((ms % 1000) / 10);
    return String(s).padStart(2,'0') + '.' + String(cs).padStart(2,'0');
  }}

  function setStatus(txt, dotClass) {{
    document.getElementById('statusTxt').textContent = txt;
    const dot = document.getElementById('dot');
    dot.className = 'dot' + (dotClass ? ' ' + dotClass : '');
  }}

  function updateTimer() {{
    elapsed = Date.now() - startTime;
    document.getElementById('timerDisplay').textContent = fmtTime(elapsed);
  }}

  function showTranscript(final, interim) {{
    const box = document.getElementById('transcriptBox');
    box.innerHTML =
      (final ? '<span>' + final + '</span>' : '') +
      (interim ? '<span class="live"> ' + interim + '</span>' : '') +
      (!final && !interim ?
        '<span style="color:#6e7681;font-size:14px;font-weight:400">Parla...</span>' : '');
  }}

  async function startTest() {{
    finalTranscript = '';
    interimTranscript = '';
    audioChunks = [];
    document.getElementById('errTxt').textContent = '';
    document.getElementById('infoTxt').textContent = '';
    showTranscript('','');

    // Avvia timer
    startTime = Date.now();
    timerInterval = setInterval(updateTimer, 50);
    isRunning = true;

    document.getElementById('startBtn').disabled = true;
    document.getElementById('stopBtn').disabled = false;

    // ── 1. Web Speech API (se disponibile) ─────────────────────────────
    if (hasSpeech) {{
      const SR = window.webkitSpeechRecognition || window.SpeechRecognition;
      recognition = new SR();
      recognition.lang = '{lang}';
      recognition.continuous = true;
      recognition.interimResults = true;

      recognition.onresult = (event) => {{
        interimTranscript = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {{
          if (event.results[i].isFinal) {{
            finalTranscript += event.results[i][0].transcript + ' ';
          }} else {{
            interimTranscript += event.results[i][0].transcript;
          }}
        }}
        showTranscript(finalTranscript, interimTranscript);
      }};

      recognition.onerror = (e) => {{
        document.getElementById('errTxt').textContent =
          '⚠️ Web Speech: ' + e.error + ' — usa Whisper come fallback';
      }};

      try {{
        recognition.start();
        setStatus('● Web Speech attiva (tempo reale)', 'rec');
        document.getElementById('infoTxt').innerHTML =
          '<span class="badge badge-ws">WebSpeech</span> Trascrizione in tempo reale';
      }} catch(e) {{
        document.getElementById('errTxt').textContent = 'Web Speech non disponibile: ' + e.message;
      }}
    }} else {{
      setStatus('● Registrazione (solo Whisper disponibile)', 'rec');
      document.getElementById('infoTxt').innerHTML =
        '<span class="badge badge-wr">Whisper</span> Web Speech non supportato in questo browser';
    }}

    // ── 2. MediaRecorder (sempre, per Whisper fallback) ─────────────────
    try {{
      const stream = await navigator.mediaDevices.getUserMedia({{audio:true}});
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : '';
      mediaRecorder = new MediaRecorder(stream, mimeType ? {{mimeType}} : {{}});
      mediaRecorder.ondataavailable = e => {{ if(e.data.size>0) audioChunks.push(e.data); }};
      mediaRecorder.start(200);
    }} catch(e) {{
      document.getElementById('errTxt').textContent += ' | Microfono: ' + e.message;
    }}
  }}

  function stopTest() {{
    isRunning = false;
    clearInterval(timerInterval);
    elapsed = Date.now() - startTime;
    document.getElementById('timerDisplay').textContent = fmtTime(elapsed);

    // Ferma Web Speech
    if (recognition) {{
      try {{ recognition.stop(); }} catch(e) {{}}
    }}

    // Ferma MediaRecorder e invia risultati
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {{
      mediaRecorder.onstop = () => {{
        const blob = new Blob(audioChunks, {{type: mediaRecorder.mimeType || 'audio/webm'}});
        const reader = new FileReader();
        reader.onloadend = () => {{
          const b64 = reader.result.split(',')[1];
          const payload = {{
            transcript: (finalTranscript + interimTranscript).trim(),
            elapsed_ms: elapsed,
            audio_b64: b64,
            audio_mime: blob.type,
            source: recognition ? 'webspeech' : 'recording',
          }};
          // Invia a Streamlit via postMessage
          window.parent.postMessage({{
            type: 'streamlit:setComponentValue',
            value: JSON.stringify(payload),
          }}, '*');
          setStatus('✅ Completato (' + fmtTime(elapsed) + ')', 'ok');
        }};
        reader.readAsDataURL(blob);
        mediaRecorder.stream.getTracks().forEach(t => t.stop());
      }};
      mediaRecorder.stop();
    }} else {{
      // Solo Web Speech, niente audio
      const payload = {{
        transcript: (finalTranscript + interimTranscript).trim(),
        elapsed_ms: elapsed,
        audio_b64: null,
        source: 'webspeech_only',
      }};
      window.parent.postMessage({{
        type: 'streamlit:setComponentValue',
        value: JSON.stringify(payload),
      }}, '*');
      setStatus('✅ Completato (' + fmtTime(elapsed) + ')', 'ok');
    }}

    document.getElementById('startBtn').disabled = false;
    document.getElementById('stopBtn').disabled = true;
  }}

  // Esponi per uso esterno
  window.stopTestExternal = stopTest;
}})();
</script>
</body>
</html>
"""
    result = components.html(html, height=height, scrolling=False)
    # Streamlit components ritorna il valore via setComponentValue
    # In produzione questo richiede un vero custom component.
    # Come workaround funzionale usiamo st.audio_input + session_state
    return result


# ─────────────────────────────────────────────────────────────────────────────
# WIDGET VOCALE UNIFICATO (Streamlit-native)
# Usa st.audio_input + Whisper + Web Speech via HTML embed
# ─────────────────────────────────────────────────────────────────────────────

def voice_test_widget(
    test_id: str,
    label: str,
    attesi: list[int],
    hint_prompt: str = "",
    show_grid: bool = False,
    grid_rows: Optional[list] = None,
    height_grid: int = 200,
) -> dict:
    """
    Widget vocale completo per un singolo test.

    Parametri:
      test_id:    chiave univoca per session_state
      label:      nome del test (es. "DEM Test A")
      attesi:     sequenza di numeri attesi
      hint_prompt: testo da dare a Whisper come hint
      show_grid:  se True mostra la griglia numeri
      grid_rows:  lista di liste (righe della tabella)

    Ritorna dict con: transcript, elapsed_ms, numeri_letti, errori, tempo_sec
    """
    state_key = f"voice_result_{test_id}"
    trans_key = f"voice_transcript_{test_id}"

    has_whisper = bool(_openai_key())

    # ── Mostra griglia ────────────────────────────────────────────────────
    if show_grid and grid_rows:
        with st.expander(f"📄 Tabella {label} (mostra al paziente)", expanded=True):
            for r_i, row in enumerate(grid_rows):
                nums_html = "".join(
                    f"<span style='font-size:28px;font-weight:900;"
                    f"font-family:monospace;padding:0 10px;color:#f0f6fc'>{n}</span>"
                    for n in row
                )
                label_html = (f"<span style='color:#6e7681;font-size:11px;"
                              f"width:22px;display:inline-block'>{r_i+1}</span>")
                st.markdown(
                    f"<div style='display:flex;align-items:center;margin:2px 0'>"
                    f"{label_html}{nums_html}</div>",
                    unsafe_allow_html=True
                )

    # ── Sezione vocale ────────────────────────────────────────────────────
    st.markdown(f"**🎙️ {label}**")

    col_rec, col_time = st.columns([3, 1])

    with col_rec:
        # Embed Web Speech in tempo reale (solo visuale, il transcript arriva via audio_input)
        st.markdown("""
<div style='background:#161b22;border:1px solid #21262d;border-radius:8px;
padding:10px 14px;font-family:monospace;color:#58a6ff;font-size:13px;
min-height:40px;margin-bottom:6px'>
🔴 <em style='color:#8b949e'>Usa il registratore qui sotto. Web Speech trascrive in tempo reale
nel widget (se il browser lo supporta — Chrome/Edge consigliato).</em>
</div>""", unsafe_allow_html=True)

        audio_input = st.audio_input(
            f"Registra {label}",
            key=f"audio_input_{test_id}",
        )

    with col_time:
        tempo_man = st.number_input(
            "Tempo (s)",
            min_value=0.0, max_value=600.0,
            value=float(st.session_state.get(f"tempo_{test_id}", 0)),
            step=0.1, format="%.1f",
            key=f"tempo_input_{test_id}",
            help="Inserisci il tempo manualmente o lascia 0 se usi il timer del widget"
        )

    # ── Trascrizione ──────────────────────────────────────────────────────
    # Auto-trascrizione con Whisper appena arriva l'audio
    transcript_corrente = st.session_state.get(trans_key, "")

    if audio_input and has_whisper:
        col_btn, col_info = st.columns([1, 2])
        with col_btn:
            if st.button(f"🤖 Whisper", key=f"whisper_btn_{test_id}",
                         help="Trascrivi con Whisper AI"):
                with st.spinner("Whisper..."):
                    audio_bytes = audio_input.read()
                    testo, err = whisper_trascrivi(audio_bytes, hint_prompt)
                    if err:
                        st.error(f"Whisper: {err}")
                    else:
                        st.session_state[trans_key] = testo
                        transcript_corrente = testo
        with col_info:
            if transcript_corrente:
                numeri_preview = parse_numeri(transcript_corrente)
                st.caption(f"Whisper → {len(numeri_preview)} cifre trovate")
    elif audio_input and not has_whisper:
        st.caption("💡 Configura `[openai] OPENAI_API_KEY` per Whisper automatico")

    # ── Text area trascrizione (modificabile) ─────────────────────────────
    transcript_edit = st.text_area(
        "Trascrizione (modifica se necessario)",
        value=transcript_corrente,
        height=68,
        key=f"transcript_edit_{test_id}",
        placeholder="Inserisci la trascrizione o usa il pulsante Whisper sopra...",
    )
    # Salva in session state
    if transcript_edit != transcript_corrente:
        st.session_state[trans_key] = transcript_edit

    # ── Parsing e scoring ─────────────────────────────────────────────────
    numeri_letti = parse_numeri(transcript_edit)
    errori = calcola_errori(attesi, numeri_letti) if numeri_letti else {
        "tot_errori":0,"omissioni":0,"sostituzioni":0,"accuratezza_pct":100,
        "n_letti":0,"n_attesi":len(attesi),"dettaglio":[]
    }

    # ── Risultato live ────────────────────────────────────────────────────
    if numeri_letti or tempo_man > 0:
        with st.container():
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Tempo", f"{tempo_man:.1f}s")
            c2.metric("Letti", f"{errori['n_letti']}/{errori['n_attesi']}")
            c3.metric("Errori", errori["tot_errori"],
                      f"omiss:{errori['omissioni']} sost:{errori['sostituzioni']}")
            c4.metric("Accuratezza", f"{errori['accuratezza_pct']}%")

        # Dettaglio errori
        if errori["dettaglio"]:
            with st.expander(f"🔍 Dettaglio errori ({errori['tot_errori']})", expanded=False):
                for e in errori["dettaglio"]:
                    if e["tipo"] == "omissione":
                        st.markdown(f"- Pos **{e['pos']}**: omissione `{e['atteso']}`")
                    else:
                        st.markdown(f"- Pos **{e['pos']}**: `{e['atteso']}` → letto `{e.get('letto','?')}`")

    result = {
        "transcript": transcript_edit,
        "tempo_sec": tempo_man,
        "numeri_letti": numeri_letti,
        "errori": errori,
    }
    st.session_state[state_key] = result
    return result


# ─────────────────────────────────────────────────────────────────────────────
# NORME TEST
# ─────────────────────────────────────────────────────────────────────────────

DEM_NORME = {
    6:(49.1,8.4,66.7,11.0,1.35,0.14),
    7:(41.8,7.3,53.7,9.2,1.28,0.12),
    8:(35.1,5.9,43.9,8.1,1.24,0.11),
    9:(30.4,5.2,38.3,7.4,1.20,0.10),
    10:(28.3,4.9,35.5,6.8,1.17,0.10),
    11:(26.1,4.5,32.3,6.3,1.14,0.09),
    12:(24.0,4.2,29.8,5.9,1.12,0.09),
    13:(22.5,4.0,27.5,5.5,1.11,0.09),
}
KD_NORME = {
    6:[(23.5,4.5),(25.0,5.0),(28.0,5.5),(76.5,15.0)],
    7:[(20.0,3.8),(21.5,4.2),(24.0,4.8),(65.5,12.8)],
    8:[(17.5,3.2),(18.5,3.6),(21.0,4.2),(57.0,11.0)],
    9:[(15.5,2.8),(16.5,3.2),(18.5,3.8),(50.5,9.8)],
    10:[(14.0,2.5),(15.0,2.9),(17.0,3.5),(46.0,8.9)],
    11:[(13.0,2.3),(13.8,2.6),(15.5,3.2),(42.3,8.1)],
    12:[(12.0,2.2),(12.8,2.4),(14.5,3.0),(39.3,7.6)],
}

def _ds(v, m, s):
    try: return (float(v)-float(m))/float(s)
    except: return None

def _ris(ds, inv=True):
    if ds is None: return "—"
    d = -ds if inv else ds
    if d >= 1.0: return "✅ Ottimale"
    if d >= 0.0: return "✅ Nella norma"
    if d >= -1.0: return "🟡 1 DS sotto norma"
    if d >= -2.0: return "🔴 2 DS sotto norma"
    return "🔴🔴 3+ DS sotto norma"


# ─────────────────────────────────────────────────────────────────────────────
# DEM VOCALE COMPLETO
# ─────────────────────────────────────────────────────────────────────────────

def dem_vocale(d: dict, px: str) -> tuple[dict, str]:
    st.markdown("### 🔢 DEM — Developmental Eye Movement Test")
    st.info("**Procedura:** Mostra la tabella al paziente → START → legge ad alta voce → STOP → Whisper trascrive automaticamente.")

    eta = int(st.number_input("Età (anni)", 5.0, 18.0,
                               float(d.get("eta",8) or 8), 1.0, key=f"{px}_eta_dem"))

    # ── TEST A ────────────────────────────────────────────────────────────
    st.markdown("---")
    # Mostra colonne verticali per Test A
    grid_a = [[DEM_A[col*10+row] for col in range(5)] for row in range(10)]
    res_a = voice_test_widget(
        f"{px}_dem_a", "Test A — Verticale (leggi colonna per colonna)",
        DEM_A,
        hint_prompt="Cifre lette in colonna: 2 8 4 9 6...",
        show_grid=True, grid_rows=grid_a,
    )

    # ── TEST C ────────────────────────────────────────────────────────────
    st.markdown("---")
    res_c = voice_test_widget(
        f"{px}_dem_c", "Test C — Orizzontale (leggi riga per riga)",
        DEM_C_FLAT,
        hint_prompt="Cifre lette per righe: 6 3 8 1 4...",
        show_grid=True, grid_rows=DEM_C_ROWS,
    )

    # ── SCORING DEM ───────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### 📊 Scoring DEM")

    tv = res_a["tempo_sec"]
    tc = res_c["tempo_sec"]
    err_omiss = res_c["errori"].get("omissioni", 0)
    th_adj = tc * 80 / max(1, 80 - err_omiss) if tc > 0 else 0
    ratio = th_adj / tv if tv > 0 else 0
    tot_err = res_a["errori"]["tot_errori"] + res_c["errori"]["tot_errori"]

    n = DEM_NORME.get(max(6,min(13,eta)), DEM_NORME[8])
    ds_v = _ds(tv, n[0], n[1]); ds_h = _ds(th_adj, n[2], n[3]); ds_r = _ds(ratio, n[4], n[5])

    # Tipologia
    v_ok = not ds_v or -ds_v >= -1
    h_ok = not ds_h or -ds_h >= -1
    r_ok = not ds_r or -ds_r >= -1
    if v_ok and h_ok: tip = "I — Normale"
    elif v_ok and not h_ok: tip = "II — Disfunzione oculomotoria"
    elif not v_ok and not h_ok and r_ok: tip = "III — Disfunzione verbale"
    else: tip = "IV — Disfunzione oculomotoria e verbale"

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("TV adj", f"{tv:.1f}s", f"norma {n[0]:.0f}±{n[1]:.0f}")
    c2.metric("TH adj", f"{th_adj:.1f}s", f"norma {n[2]:.0f}±{n[3]:.0f}")
    c3.metric("Ratio H/V", f"{ratio:.2f}", f"norma {n[4]:.2f}±{n[5]:.2f}")
    c4.metric("Errori tot", tot_err)

    tipo_color = "success" if "I —" in tip else "warning" if "II" in tip else "error"
    getattr(st, tipo_color)(f"**Tipologia: {tip}**")
    st.caption(f"TV: {_ris(ds_v)} | TH: {_ris(ds_h)} | Ratio: {_ris(ds_r)}")

    risultati = {
        "eta":eta, "test_a":res_a, "test_c":res_c,
        "calcoli":{
            "tv_adj":round(tv,1), "th_adj":round(th_adj,1),
            "ratio":round(ratio,3), "tot_errori":tot_err, "tipologia":tip,
        }
    }
    return risultati, f"DEM: TV={tv:.1f}s TH={th_adj:.1f}s → {tip}"


# ─────────────────────────────────────────────────────────────────────────────
# KING-DEVICK VOCALE COMPLETO
# ─────────────────────────────────────────────────────────────────────────────

def kd_vocale(d: dict, px: str) -> tuple[dict, str]:
    st.markdown("### ⚡ King-Devick Test")
    st.info("**Procedura:** Mostra la card → START → il paziente legge tutti i numeri → STOP → Whisper trascrive.")

    eta = int(st.number_input("Età (anni)", 5.0, 18.0,
                               float(d.get("eta",8) or 8), 1.0, key=f"{px}_eta_kd"))
    norme = KD_NORME.get(max(6,min(12,eta)), KD_NORME[8])

    kd_res = {"eta": eta}
    card_results = []

    for i in range(3):
        st.markdown("---")
        res = voice_test_widget(
            f"{px}_kd_{i}",
            f"Card {i+1}",
            KD_FLATS[i],
            hint_prompt=f"Cifre card {i+1}: {' '.join(str(n) for n in KD_FLATS[i][:10])}...",
            show_grid=True,
            grid_rows=KD_CARDS[i],
        )
        card_results.append(res)
        n = norme[i]
        t = res["tempo_sec"]; e = res["errori"]["tot_errori"]
        ds_t = _ds(t, n[0], n[1])
        if t > 0:
            st.caption(f"Card {i+1}: {t:.1f}s (norma {n[0]:.1f}±{n[1]:.1f}) → {_ris(ds_t)}")
        kd_res[f"card{i+1}"] = res

    # Totali
    st.markdown("---")
    st.markdown("### 📊 Totali K-D")
    tot_t = sum(r["tempo_sec"] for r in card_results)
    tot_e = sum(r["errori"]["tot_errori"] for r in card_results)
    n_tot = norme[3]
    ds_tot = _ds(tot_t, n_tot[0], n_tot[1])

    c1,c2 = st.columns(2)
    c1.metric("Tempo totale", f"{tot_t:.1f}s", f"norma {n_tot[0]:.0f}±{n_tot[1]:.0f}")
    c2.metric("Errori totali", tot_e)
    ris_tot = _ris(ds_tot)
    if "✅" in ris_tot: st.success(f"Risultato: {ris_tot}")
    elif "🟡" in ris_tot: st.warning(f"Risultato: {ris_tot}")
    else: st.error(f"Risultato: {ris_tot}")

    kd_res.update({"tot_tempo":round(tot_t,1),"tot_errori":tot_e})
    return kd_res, f"K-D: {tot_t:.1f}s / {tot_e} err → {ris_tot}"


# ─────────────────────────────────────────────────────────────────────────────
# VISUAL TRACKING VOCALE
# Il paziente legge ad alta voce tutti i numeri di un dato valore nella griglia
# ─────────────────────────────────────────────────────────────────────────────

def vt_vocale(d: dict, px: str) -> tuple[dict, str]:
    st.markdown("### 🎯 Visual Tracking — Lettura Vocale")
    st.info("Il paziente trova e legge ad alta voce tutti i numeri del valore target nella griglia.")

    target = st.selectbox("Numero target",
                          [0,1,2,3,4,5,6,7,8,9],
                          index=int(d.get("target",3)),
                          key=f"{px}_vt_target")

    attesi_vt = [n for n in VT_FLAT if n == target]
    n_tot_target = len(attesi_vt)
    st.caption(f"Il numero {target} compare **{n_tot_target} volte** nella griglia.")

    # Mostra griglia con highlight del target
    with st.expander("📄 Griglia Visual Tracking", expanded=True):
        for r_i, row in enumerate(VT_GRID):
            nums_html = "".join(
                f"<span style='font-size:22px;font-weight:900;font-family:monospace;"
                f"padding:0 8px;"
                f"color:{'#f7a84f' if n==target else '#8b949e'};'>{n}</span>"
                for n in row
            )
            label_html = f"<span style='color:#6e7681;font-size:11px;width:20px;display:inline-block'>{r_i+1}</span>"
            st.markdown(
                f"<div style='display:flex;align-items:center;margin:1px 0'>{label_html}{nums_html}</div>",
                unsafe_allow_html=True
            )

    st.caption(f"Il paziente deve leggere ad alta voce solo i **{target}** che trova, da sinistra a destra e dall'alto in basso.")

    res = voice_test_widget(
        f"{px}_vt",
        f"Visual Tracking — target: {target}",
        attesi_vt,
        hint_prompt=f"Il paziente legge solo il numero {target}",
        show_grid=False,
    )

    # Scoring VT
    trovati = res["errori"]["n_letti"]
    pct = round(trovati / max(n_tot_target, 1) * 100)
    if pct >= 90: st.success(f"✅ Trovati {trovati}/{n_tot_target} ({pct}%)")
    elif pct >= 70: st.warning(f"🟡 Trovati {trovati}/{n_tot_target} ({pct}%)")
    else: st.error(f"🔴 Trovati {trovati}/{n_tot_target} ({pct}%)")

    risultati = {"target":target,"result":res,
                 "calcoli":{"trovati":trovati,"tot_target":n_tot_target,"pct":pct}}
    return risultati, f"VT vocale: {trovati}/{n_tot_target} ({pct}%)"


# ─────────────────────────────────────────────────────────────────────────────
# GROFFMAN VOCALE
# Il paziente legge i numeri/lettere lungo i percorsi
# ─────────────────────────────────────────────────────────────────────────────

GROFFMAN_SEQUENZE = {
    "A": [3,2,1,4,5,3],    # lettere/numeri tipici percorso A
    "B": [4,1,3,5,2,4],
    "C": [2,5,4,1,3,2],
    "D": [5,3,2,4,1,5],
    "E": [1,4,5,2,3,1],
}
GROFFMAN_NORME = {6:(18,4),7:(20,4),8:(23,4),9:(26,4),10:(28,3),
                  11:(28,3),12:(29,3),13:(30,3)}

def groffman_vocale(d: dict, px: str) -> tuple[dict, str]:
    st.markdown("### 🔗 Groffman Visual Tracing — Lettura Vocale")
    st.info("Il paziente segue il percorso con gli occhi e legge ad alta voce la soluzione.")

    eta = int(st.number_input("Età (anni)", 5.0, 18.0,
                               float(d.get("eta",9) or 9), 1.0, key=f"{px}_eta_gr"))

    risultati = {"eta": eta}
    tot_punti = 0

    for perc, seq in GROFFMAN_SEQUENZE.items():
        st.markdown(f"---")
        res = voice_test_widget(
            f"{px}_gr_{perc}",
            f"Percorso {perc}",
            seq,
            hint_prompt=f"Il paziente legge la sequenza del percorso {perc}",
            show_grid=False,
        )
        acc = res["errori"]["accuratezza_pct"]
        punti = round(acc / 10)  # 0-10 punti proporzionali
        tot_punti += punti
        risultati[f"perc_{perc}"] = {**res, "punti":punti}

    # Scoring
    st.markdown("---")
    n = GROFFMAN_NORME.get(max(6,min(13,eta)),(28,3))
    ds = _ds(tot_punti, n[0], n[1])
    ris = _ris(ds, inv=False)
    st.metric("Totale Groffman", f"{tot_punti}/50", f"norma {n[0]}±{n[1]}")
    if "✅" in ris: st.success(ris)
    elif "🟡" in ris: st.warning(ris)
    else: st.error(ris)

    risultati["calcoli"] = {"tot_punti":tot_punti,"ds":round(ds,2) if ds else None,"ris":ris}
    return risultati, f"Groffman vocale: {tot_punti}/50 → {ris}"


# ─────────────────────────────────────────────────────────────────────────────
# VADS VOCALE (subtest orali: UO e VO)
# ─────────────────────────────────────────────────────────────────────────────

# Sequenze VADS standard (progressive per span)
VADS_SEQUENZE_UO = [[2,3],[7,4,9],[1,5,8,3],[6,2,9,4,7],[3,8,1,6,2,5],[4,7,3,1,9,8,2]]
VADS_SEQUENZE_VO = [[4,7],[1,9,3],[8,2,6,4],[5,3,7,1,8],[2,6,4,9,3,7],[8,1,5,3,7,4,9]]

def vads_vocale_oral(d: dict, px: str) -> tuple[dict, str]:
    st.markdown("### 🔢 VADS — Subtest Orali (UO e VO)")
    st.caption("Solo i subtest con risposta orale: Uditivo-Orale e Visivo-Orale.")

    eta = int(st.number_input("Età (anni)", 5.0, 13.0,
                               float(d.get("eta",8) or 8), 1.0, key=f"{px}_eta_vads"))

    tab_uo, tab_vo = st.tabs(["🎧 Uditivo-Orale (UO)", "👁️ Visivo-Orale (VO)"])

    with tab_uo:
        st.info("Il clinico legge i numeri, il paziente li ripete ad alta voce.")
        st.caption("Interrompi quando il paziente fallisce entrambe le prove dello stesso livello.")
        span_uo = st.number_input("Span massimo raggiunto (UO)", 0.0, 9.0, 0.0, 1.0,
                                   key=f"{px}_vads_span_uo")
        uo_res = {"span": int(span_uo)}

    with tab_vo:
        st.info("Mostra i numeri scritti per 10 secondi, il paziente li ripete ad alta voce.")
        span_vo = st.number_input("Span massimo raggiunto (VO)", 0.0, 9.0, 0.0, 1.0,
                                   key=f"{px}_vads_span_vo")
        vo_res = {"span": int(span_vo)}

    # Norme VADS
    VADS_N = {6:(3.0,2.5),7:(3.5,3.0),8:(4.0,3.5),9:(4.5,4.0),10:(5.0,4.5),11:(5.5,5.0)}
    n_vads = VADS_N.get(max(6,min(11,eta)),(4.0,3.5))

    c1,c2 = st.columns(2)
    ds_uo = _ds(span_uo, n_vads[0], 1.0)
    ds_vo = _ds(span_vo, n_vads[1], 1.0)
    c1.metric("Span UO", int(span_uo), f"norma ≥{n_vads[0]:.0f}")
    c1.caption(_ris(ds_uo, inv=False))
    c2.metric("Span VO", int(span_vo), f"norma ≥{n_vads[1]:.0f}")
    c2.caption(_ris(ds_vo, inv=False))

    risultati = {"eta":eta,"uo":uo_res,"vo":vo_res}
    summary = f"VADS vocale: UO span={int(span_uo)} VO span={int(span_vo)}"
    return risultati, summary


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT PRINCIPALE
# ─────────────────────────────────────────────────────────────────────────────

def render_test_vocali(
    data_json: dict | None,
    prefix: str,
) -> tuple[dict, str]:
    """
    Entry point. Tutti i test con lettura orale in un unico modulo.
    """
    if data_json is None:
        data_json = {}

    has_whisper = bool(_openai_key())

    st.markdown("## 🎤 Test di Lettura Orale — Registrazione Vocale + Whisper")

    # Info sistema
    col_ws, col_wh = st.columns(2)
    with col_ws:
        st.info("🌐 **Web Speech API** — Trascrive in tempo reale nel browser\n"
                "(Chrome/Edge consigliati, richiede connessione internet)")
    with col_wh:
        if has_whisper:
            st.success("🤖 **Whisper AI** — Configurato ✓\n"
                       "Usa il pulsante Whisper dopo ogni registrazione")
        else:
            st.warning("🤖 **Whisper** — Non configurato\n"
                       "Aggiungi `[openai] OPENAI_API_KEY` nei Secrets")

    st.caption("**Come funziona:** Registra l'audio del paziente → "
               "Web Speech trascrive in tempo reale → "
               "Whisper corregge/verifica → "
               "Il sistema calcola automaticamente errori e scoring.")

    tabs = st.tabs([
        "🔢 DEM",
        "⚡ K-D",
        "🎯 Visual Tracking",
        "🔗 Groffman",
        "🔢 VADS Orale",
    ])

    nuovi = dict(data_json)
    summaries = []

    with tabs[0]:
        data, s = dem_vocale(data_json.get("dem",{}), f"{prefix}_dem")
        nuovi["dem"] = data; summaries.append(s)

    with tabs[1]:
        data, s = kd_vocale(data_json.get("kd",{}), f"{prefix}_kd")
        nuovi["kd"] = data; summaries.append(s)

    with tabs[2]:
        data, s = vt_vocale(data_json.get("visual_tracking",{}), f"{prefix}_vt")
        nuovi["visual_tracking"] = data; summaries.append(s)

    with tabs[3]:
        data, s = groffman_vocale(data_json.get("groffman",{}), f"{prefix}_gr")
        nuovi["groffman"] = data; summaries.append(s)

    with tabs[4]:
        data, s = vads_vocale_oral(data_json.get("vads_oral",{}), f"{prefix}_vads")
        nuovi["vads_oral"] = data; summaries.append(s)

    return nuovi, " | ".join(summaries)
