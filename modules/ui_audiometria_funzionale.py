# -*- coding: utf-8 -*-
"""
Modulo: Audiometria Funzionale + Test Dicotico Johansen
Gestionale The Organism — PNEV

Generazione toni: WAV sintetizzato in Python → st.audio() (funziona su Streamlit Cloud)
Frequenze: 125 250 500 750 1000 1500 2000 3000 4000 6000 8000 10500 Hz
Metodo: start 30 dB → scende a -20 dB → risale di 5 dB fino alla soglia (metodo Hiperion)
"""

import io
import wave
import json
import math
import streamlit as st
import pandas as pd
from datetime import date, datetime

import numpy as np

# ─────────────────────────────────────────────────────────────────────────────
# Costanti
# ─────────────────────────────────────────────────────────────────────────────

FREQS    = [125, 250, 500, 750, 1000, 1500, 2000, 3000, 4000, 6000, 8000, 10500]
FLABELS  = ['125','250','500','750','1k','1.5k','2k','3k','4k','6k','8k','10.5k']
FREQS_11 = FREQS[:11]   # per grafico e EQ (senza 10.5k)

# Ordine test Hiperion: da acuti a gravi
FREQ_ORDER = [10500, 8000, 6000, 4000, 3000, 2000, 1500, 1000, 750, 500, 250, 125]

TOMATIS_STD = [-5, -8, -10, -12, -14, -15, -14, -15, -12, -8, -5]  # 11 valori

JOHANSEN_COPPIE = [
    {"od":"DAT","os":"SOT"},{"od":"MYL","os":"GIF"},{"od":"NIK","os":"VEF"},
    {"od":"GIF","os":"KIT"},{"od":"FAK","os":"BAT"},{"od":"NUR","os":"NIK"},
    {"od":"SOT","os":"VYF"},{"od":"GEP","os":"RIS"},{"od":"VYF","os":"MYL"},
    {"od":"POS","os":"LIR"},{"od":"BOT","os":"TIK"},{"od":"VEF","os":"FAK"},
    {"od":"KIR","os":"DAT"},{"od":"KIT","os":"NUR"},{"od":"TIK","os":"BOT"},
    {"od":"LYM","os":"LYM"},{"od":"TOS","os":"HUT"},{"od":"BAT","os":"GEP"},
    {"od":"RIS","os":"POS"},{"od":"HUT","os":"TOS"},
]

JOHANSEN_TRACCE = [
    {"n":1,"desc":"Istruzioni","dur":"10s"},
    {"n":2,"desc":"Compito 1 — OD","dur":"69s"},
    {"n":3,"desc":"Compito 2 — OS","dur":"73s"},
    {"n":4,"desc":"Compito 3 — Risposte DX","dur":"75s"},
    {"n":5,"desc":"Compito 4 — Risposte SX","dur":"73s"},
    {"n":6,"desc":"Compito 5 — Entrambi","dur":"100s"},
]

# ─────────────────────────────────────────────────────────────────────────────
# Generazione tono WAV (funziona su Streamlit Cloud)
# ─────────────────────────────────────────────────────────────────────────────

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

def _is_pg(conn):
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
    return ", ".join(["%s" if _is_pg(conn) else "?"] * n)

def _rg(row, key, default=None):
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
    c = sqlite3.connect("organism.db"); c.row_factory = sqlite3.Row; return c

def _init_db(conn):
    raw = getattr(conn, "_conn", conn)
    try: cur = raw.cursor()
    except: cur = conn.cursor()
    pg = _is_pg(conn)
    if pg:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS audiometrie_funzionali (
            id BIGSERIAL PRIMARY KEY,
            paziente_id BIGINT NOT NULL,
            data_esame TEXT, operatore TEXT,
            od_json TEXT, os_json TEXT,
            tomatis_json TEXT, eq_od_json TEXT, eq_os_json TEXT,
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
            tomatis_json TEXT, eq_od_json TEXT, eq_os_json TEXT,
            sel_json TEXT, lat_json TEXT,
            joh_od INTEGER, joh_os INTEGER,
            joh_indice REAL, joh_dominanza TEXT,
            note TEXT, created_at TEXT
        )""")
    try: raw.commit()
    except: conn.commit()

def _salva(conn, paz_id, data, operatore=""):
    cur = conn.cursor()
    joh  = data.get("joh", {})
    jod  = int(joh.get("od", 0))
    jos  = int(joh.get("os", 0))
    jtot = jod + jos
    jidx = round((jod-jos)*100/jtot, 1) if jtot > 0 else None
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

# ─────────────────────────────────────────────────────────────────────────────
# Grafico audiogramma (matplotlib)
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

def ui_audiometria_funzionale():
    st.header("📊 Audiometria Funzionale")
    st.caption("Test tonale liminare · Curva Tomatis · Delta EQ · Selettività · Lateralità · Test dicotico Johansen")

    conn = _get_conn()
    _init_db(conn)
    cur = conn.cursor()

    # Selezione paziente
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

    opts = [f"{_rg(p,'id')} - {_rg(p,'Cognome','')} {_rg(p,'Nome','')}".strip()
            for p in pazienti]
    c1, c2 = st.columns([3,1])
    with c1: sel = st.selectbox("Paziente", opts, key="af_paz")
    with c2: op  = st.text_input("Operatore", "", key="af_op")
    paz_id = int(sel.split(" - ", 1)[0])

    st.divider()

    tab_test, tab_joh, tab_storico = st.tabs([
        "🎵 Test Tonale + EQ", "📋 Test Johansen", "📈 Storico"
    ])

    with tab_test:
        _ui_test_tonale(conn, paz_id, op)

    with tab_joh:
        _ui_johansen(conn, cur, paz_id)

    with tab_storico:
        _ui_storico(conn, cur, paz_id)


# ─────────────────────────────────────────────────────────────────────────────
# Test tonale con generazione WAV
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
    cur_f  = FREQS[ss.af_fidx]
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

    cur_f  = FREQS[ss.af_fidx]
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
                wav = _tone_wav(FREQS[ss.af_fidx], float(ss.af_db), float(
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
                wav = _tone_wav(FREQS[ss.af_fidx], float(ss.af_db), 2.0)
                st.audio(wav, format="audio/wav", autoplay=True)
            st.rerun()

    with rc2:
        if st.button("✗ Non risponde", key="af_resp_no",
                     use_container_width=True):
            ss.af_db = min(90, ss.af_db + 5)
            if ss.af_db >= 50:
                st.warning("Perdita > 50 dB — frequenza non validata")
            if ss.af_mode == "Automatico":
                wav = _tone_wav(FREQS[ss.af_fidx], float(ss.af_db), 2.0)
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
            cur_f_now = FREQS[ss.af_fidx]
            order_idx = FREQ_ORDER.index(cur_f_now) if cur_f_now in FREQ_ORDER else -1
            if order_idx >= 0 and order_idx < len(FREQ_ORDER) - 1:
                next_f = FREQ_ORDER[order_idx + 1]
                if next_f in FREQS:
                    ss.af_fidx = FREQS.index(next_f)
            st.success(f"Soglia {cur_f_now} Hz = {db_val} dB HL registrata")
            st.rerun()

    with rc4:
        if st.button("→ Freq. successiva", key="af_next",
                     use_container_width=True):
            cur_f_now = FREQS[ss.af_fidx]
            order_idx = FREQ_ORDER.index(cur_f_now) if cur_f_now in FREQ_ORDER else -1
            if order_idx >= 0 and order_idx < len(FREQ_ORDER) - 1:
                next_f = FREQ_ORDER[order_idx + 1]
                if next_f in FREQS:
                    ss.af_fidx = FREQS.index(next_f)
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
                    f"{FLABELS[i]}: {v} dB</span>",
                    unsafe_allow_html=True)
    with sc2:
        st.markdown("🔵 **OS — Orecchio sinistro**")
        for i, v in enumerate(ss.af_os):
            if v is not None:
                st.markdown(
                    f"<span style='background:#eaf4fb;border:1px solid #2980b9;"
                    f"border-radius:10px;padding:2px 8px;font-size:12px;"
                    f"color:#2980b9;margin:2px;display:inline-block'>"
                    f"{FLABELS[i]}: {v} dB</span>",
                    unsafe_allow_html=True)

    # ── Grafico + EQ ──────────────────────────────────────────────────────
    if any(v is not None for v in ss.af_od + ss.af_os):
        st.divider()
        st.markdown("**Audiogramma + curva Tomatis**")

        with st.expander("Modifica curva Tomatis", expanded=False):
            tom_cols = st.columns(11)
            for i, (f, lbl) in enumerate(zip(FREQS_11, FLABELS[:11])):
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
        for i, (lbl, vod, vos) in enumerate(zip(FLABELS[:11], eq_od, eq_os)):
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
            for i, lbl in enumerate(FLABELS[:11]):
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
            for i, lbl in enumerate(FLABELS[:11]):
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

def _ui_johansen(conn, cur, paz_id):
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

def _ui_storico(conn, cur, paz_id):
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
