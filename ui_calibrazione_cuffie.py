# -*- coding: utf-8 -*-
"""
Modulo: Calibrazione Cuffie
Gestionale The Organism – PNEV

Wizard step-by-step per calibrare qualsiasi coppia cuffie/device.
Due modalita:
  1. Con fonometro dB(A) — calibrazione oggettiva precisa
  2. Senza fonometro   — calibrazione soggettiva (volume comfort)

Salva profili nel DB: tabelle audio_devices, audio_headphones, audio_calibration_profiles2
"""

import streamlit as st
import json
from datetime import datetime


def _tone_wav_bytes(freq_hz: int, dbfs: float, seconds: float = 0.6, sr: int = 44100) -> bytes:
    import io, wave
    import numpy as _np
    # dbfs -> amp lineare
    amp = 10 ** (float(dbfs) / 20.0)
    amp = max(0.0, min(0.9, amp))
    t = _np.linspace(0, seconds, int(sr * seconds), endpoint=False)
    x = amp * _np.sin(2 * _np.pi * float(freq_hz) * t)
    fade = int(sr * 0.02)
    if fade > 0 and len(x) > 2 * fade:
        w = _np.ones_like(x)
        w[:fade] = _np.linspace(0, 1, fade)
        w[-fade:] = _np.linspace(1, 0, fade)
        x = x * w
    pcm = _np.int16(_np.clip(x, -1, 1) * 32767)

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())
    return buf.getvalue()


# ======================================
# WIZARD CALIBRAZIONE CUFFIE + DEVICE (TEST)
# ======================================
# - Device preset: PC 50% / iPad 70%
# - Fonometro solo dB(A): ok per uso funzionale (non certificato)
# - Streamlit st.audio non può autoplay: l'utente clicca Play ad ogni step.


def _ensure_calibration_tables(conn):
    cur = conn.cursor()
    try:
        # PostgreSQL
        cur.execute("""
        CREATE TABLE IF NOT EXISTS audio_devices (
            id BIGSERIAL PRIMARY KEY,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            label TEXT NOT NULL,
            volume_note TEXT,
            notes TEXT
        );
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS audio_headphones (
            id BIGSERIAL PRIMARY KEY,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            brand TEXT NOT NULL,
            model TEXT NOT NULL,
            hp_type TEXT NOT NULL DEFAULT 'over-ear',
            notes TEXT
        );
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS audio_calibration_profiles2 (
            id BIGSERIAL PRIMARY KEY,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            device_id BIGINT NOT NULL REFERENCES audio_devices(id) ON DELETE CASCADE,
            headphones_id BIGINT NOT NULL REFERENCES audio_headphones(id) ON DELETE CASCADE,
            ref_dbfs REAL NOT NULL DEFAULT -20,
            weighting TEXT NOT NULL DEFAULT 'A',
            offsets_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            notes TEXT
        );
        """)
        try:
            cur.execute("CREATE INDEX IF NOT EXISTS idx_cal2_device_hp ON audio_calibration_profiles2(device_id, headphones_id)")
        except Exception:
            pass
        conn.commit()
        try: cur.close()
        except Exception: pass
        return
    except Exception:
        # SQLite fallback (se mai usato)
        pass

    try:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS audio_devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            label TEXT NOT NULL,
            volume_note TEXT,
            notes TEXT
        );
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS audio_headphones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            brand TEXT NOT NULL,
            model TEXT NOT NULL,
            hp_type TEXT NOT NULL,
            notes TEXT
        );
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS audio_calibration_profiles2 (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            device_id INTEGER NOT NULL,
            headphones_id INTEGER NOT NULL,
            ref_dbfs REAL NOT NULL,
            weighting TEXT NOT NULL,
            offsets_json TEXT NOT NULL,
            is_active INTEGER NOT NULL,
            notes TEXT
        );
        """)
        conn.commit()
    finally:
        try: cur.close()
        except Exception: pass



def _seed_default_devices_if_empty(conn):
    cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) FROM audio_devices")
        n = int(cur.fetchone()[0])
    except Exception:
        n = 0

    if n > 0:
        try: cur.close()
        except Exception: pass
        return

    now = datetime.now().isoformat(timespec="seconds")
    rows = [
        ("PC Studio (Chrome)", "50%", "Preset PNEV: PC 50% (EQ OFF)"),
        ("iPad Studio (Safari)", "70%", "Preset PNEV: iPad 70% (suono standard)"),
    ]
    for label, vol, notes in rows:
        try:
            cur.execute("INSERT INTO audio_devices (label, volume_note, notes) VALUES (%s,%s,%s)", (label, vol, notes))
        except Exception:
            cur.execute("INSERT INTO audio_devices (created_at, label, volume_note, notes) VALUES (%s,%s,%s,%s)",
                        (now, label, vol, notes))
    conn.commit()
    try: cur.close()
    except Exception: pass



def ui_calibrazione_cuffie(conn=None):
    # Tab Fonometro wizard aggiunta all inizio
    _tab_list = ["Fonometro Wizard", "Wizard classico", "Devices", "Cuffie", "Profili"]

    import json
    from datetime import datetime

    st.header("🔧 Calibrazione cuffie (TEST)")
    st.caption("Wizard per calibrare CUFFIE + DEVICE con fonometro dB(A). Uso funzionale (non certificato).")

    if conn is None:
        try:
            from modules.app_core import get_connection; conn = get_connection()
        except Exception:
            import sys, os; root=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0,root)
            from app_patched import get_connection; conn = get_connection()
    _ensure_calibration_tables(conn)
    _seed_default_devices_if_empty(conn)

    tab_wiz, tab_device, tab_hp, tab_prof = st.tabs(["🧙 Wizard", "🖥️ Devices", "🎧 Cuffie", "📚 Profili"])

    # ---------- Devices ----------
    with tab_device:
        st.subheader("Devices")
        cur = conn.cursor()
        try:
            cur.execute("SELECT id, label, volume_note, notes, created_at FROM audio_devices ORDER BY created_at DESC")
        except Exception:
            cur.execute("SELECT id, label, volume_note, notes, created_at FROM audio_devices ORDER BY id DESC")
        dev_rows = cur.fetchall() or []
        try: cur.close()
        except Exception: pass
        if dev_rows:
            st.dataframe(dev_rows, use_container_width=True)
        else:
            st.info("Nessun device registrato.")

        with st.expander("➕ Aggiungi device", expanded=False):
            label = st.text_input("Nome device", value="PC Studio (Chrome)")
            vol = st.text_input("Volume (nota)", value="50%")
            notes = st.text_area("Note", value="EQ OFF, nessun enhancer")
            if st.button("Salva device", key="save_device"):
                cur = conn.cursor()
                try:
                    cur.execute("INSERT INTO audio_devices (label, volume_note, notes) VALUES (%s,%s,%s)", (label, vol, notes))
                except Exception:
                    cur.execute("INSERT INTO audio_devices (created_at, label, volume_note, notes) VALUES (%s,%s,%s,%s)",
                                (datetime.now().isoformat(timespec="seconds"), label, vol, notes))
                conn.commit()
                try: cur.close()
                except Exception: pass
                st.success("Device salvato")
                st.rerun()

    # ---------- Headphones ----------
    with tab_hp:
        st.subheader("Cuffie")
        cur = conn.cursor()
        try:
            cur.execute("SELECT id, brand, model, hp_type, notes, created_at FROM audio_headphones ORDER BY created_at DESC")
        except Exception:
            cur.execute("SELECT id, brand, model, hp_type, notes, created_at FROM audio_headphones ORDER BY id DESC")
        hp_rows = cur.fetchall() or []
        try: cur.close()
        except Exception: pass
        if hp_rows:
            st.dataframe(hp_rows, use_container_width=True)
        else:
            st.info("Nessuna cuffia registrata.")

        with st.expander("➕ Aggiungi cuffie", expanded=False):
            brand = st.text_input("Marca", value="Sony")
            model = st.text_input("Modello", value="MDR-ZX110")
            hp_type = st.selectbox("Tipo", ["over-ear", "on-ear", "in-ear"], index=0)
            notes = st.text_area("Note", value="Cablata")
            if st.button("Salva cuffie", key="save_hp"):
                cur = conn.cursor()
                try:
                    cur.execute("INSERT INTO audio_headphones (brand, model, hp_type, notes) VALUES (%s,%s,%s,%s)",
                                (brand, model, hp_type, notes))
                except Exception:
                    cur.execute("INSERT INTO audio_headphones (created_at, brand, model, hp_type, notes) VALUES (%s,%s,%s,%s,%s)",
                                (datetime.now().isoformat(timespec="seconds"), brand, model, hp_type, notes))
                conn.commit()
                try: cur.close()
                except Exception: pass
                st.success("Cuffie salvate")
                st.rerun()

    def _load_devices():
        cur = conn.cursor()
        try:
            cur.execute("SELECT id, label, volume_note FROM audio_devices ORDER BY created_at DESC")
        except Exception:
            cur.execute("SELECT id, label, volume_note FROM audio_devices ORDER BY id DESC")
        rows = cur.fetchall() or []
        try: cur.close()
        except Exception: pass
        out = []
        for r in rows:
            if isinstance(r, dict):
                out.append((r.get("id"), r.get("label"), r.get("volume_note")))
            else:
                out.append((r[0], r[1], r[2]))
        return out

    def _load_headphones():
        cur = conn.cursor()
        try:
            cur.execute("SELECT id, brand, model, hp_type FROM audio_headphones ORDER BY created_at DESC")
        except Exception:
            cur.execute("SELECT id, brand, model, hp_type FROM audio_headphones ORDER BY id DESC")
        rows = cur.fetchall() or []
        try: cur.close()
        except Exception: pass
        out = []
        for r in rows:
            if isinstance(r, dict):
                out.append((r.get("id"), r.get("brand"), r.get("model"), r.get("hp_type")))
            else:
                out.append((r[0], r[1], r[2], r[3]))
        return out

    with tab_prof:
        st.subheader("Profili calibrazione")
        cur = conn.cursor()
        try:
            cur.execute("""
                SELECT p.id, p.created_at, d.label, d.volume_note, h.brand, h.model, h.hp_type,
                       p.ref_dbfs, p.weighting, p.is_active, p.offsets_json, p.notes
                FROM audio_calibration_profiles2 p
                JOIN audio_devices d ON d.id=p.device_id
                JOIN audio_headphones h ON h.id=p.headphones_id
                ORDER BY p.created_at DESC
            """)
            rows = cur.fetchall() or []
        except Exception:
            rows = []
        try: cur.close()
        except Exception: pass
        if rows:
            st.dataframe(rows, use_container_width=True)
        else:
            st.info("Nessun profilo calibrazione salvato.")

    # ---------- Wizard ----------
    with tab_wiz:
        st.subheader("🧙 Wizard (automatico)")
        st.info("Per policy browser devi cliccare ▶️ Play su ogni tono. Il wizard avanza automaticamente quando confermi la misura.")

        devices = _load_devices()
        hps = _load_headphones()
        if not devices:
            st.warning("Crea almeno un device nella tab 'Devices'.")
            return
        if not hps:
            st.warning("Crea almeno una cuffia nella tab 'Cuffie'.")
            return

        dev = st.selectbox("Device", devices, format_func=lambda d: f"{d[1]} • vol {d[2] or 'n/d'} • id {d[0]}", key="cal_dev_sel")
        hp = st.selectbox("Cuffie", hps, format_func=lambda h: f"{h[1]} {h[2]} ({h[3]}) • id {h[0]}", key="cal_hp_sel")

        ref_dbfs = st.number_input("Livello digitale di riferimento (dBFS)", value=-20.0, step=1.0)
        tone_seconds = st.number_input("Durata tono (secondi)", value=2.0, min_value=0.5, max_value=6.0, step=0.5)
        include_250 = st.checkbox("Includi 250 Hz (meno affidabile con dB(A))", value=False)
        include_125 = st.checkbox("Includi 125 Hz (molto meno affidabile con dB(A))", value=False)

        freqs = [1000, 2000, 4000, 6000, 8000, 500] + ([250] if include_250 else []) + ([125] if include_125 else [])
        st.caption("Frequenze: " + " → ".join(str(f) for f in freqs))

        if "cal_wiz_running" not in st.session_state:
            st.session_state.cal_wiz_running = False
        if "cal_idx" not in st.session_state:
            st.session_state.cal_idx = 0
        if "cal_values" not in st.session_state:
            st.session_state.cal_values = {}

        cA, cB, cC = st.columns([1,1,2])
        with cA:
            if st.button("▶️ Avvia", type="primary"):
                st.session_state.cal_wiz_running = True
                st.session_state.cal_idx = 0
                st.session_state.cal_values = {}
                st.rerun()
        with cB:
            if st.button("⏹ Reset"):
                st.session_state.cal_wiz_running = False
                st.session_state.cal_idx = 0
                st.session_state.cal_values = {}
                st.rerun()
        with cC:
            st.caption("Inserisci SPL in dB(A) letto sul fonometro. Usa +/- per velocizzare.")

        if not st.session_state.cal_wiz_running:
            st.stop()

        idx = int(st.session_state.cal_idx)
        if idx >= len(freqs):
            st.success("✅ Wizard completato. Salva il profilo.")
            offsets = {str(int(f)): float(spl) - float(ref_dbfs) for f, spl in st.session_state.cal_values.items()}
            st.json({"device_id": dev[0], "headphones_id": hp[0], "ref_dbfs": ref_dbfs, "offsets": offsets})

            notes = st.text_area("Note profilo (opzionale)", value="Fonometro dB(A). Coupler foam. Volume come preset.")
            if st.button("💾 Salva profilo calibrazione"):
                cur = conn.cursor()
                try:
                    cur.execute("UPDATE audio_calibration_profiles2 SET is_active=FALSE WHERE device_id=%s AND headphones_id=%s",
                                (int(dev[0]), int(hp[0])))
                except Exception:
                    cur.execute("UPDATE audio_calibration_profiles2 SET is_active=0 WHERE device_id=%s AND headphones_id=%s",
                                (int(dev[0]), int(hp[0])))

                payload = json.dumps(offsets)
                try:
                    cur.execute("""
                        INSERT INTO audio_calibration_profiles2
                        (device_id, headphones_id, ref_dbfs, weighting, offsets_json, is_active, notes)
                        VALUES (%s,%s,%s,%s,%s,TRUE,%s)
                    """, (int(dev[0]), int(hp[0]), float(ref_dbfs), "A", payload, notes))
                except Exception:
                    cur.execute("""
                        INSERT INTO audio_calibration_profiles2
                        (created_at, device_id, headphones_id, ref_dbfs, weighting, offsets_json, is_active, notes)
                        VALUES (?,?,?,?,?,?,?,?)
                    """, (datetime.now().isoformat(timespec="seconds"), int(dev[0]), int(hp[0]),
                          float(ref_dbfs), "A", payload, 1, notes))
                conn.commit()
                try: cur.close()
                except Exception: pass
                st.success("Profilo salvato ✅")
                st.session_state.cal_wiz_running = False
                st.rerun()
            st.stop()

        f = freqs[idx]
        st.markdown(f"### Step {idx+1}/{len(freqs)} — **{f} Hz**")
        st.caption("1) Clicca ▶️ Play, 2) leggi dB(A) sul fonometro, 3) inserisci e conferma.")
        st.audio(_tone_wav_bytes(int(f), float(ref_dbfs), seconds=float(tone_seconds)), format="audio/wav")

        key = f"cal_spl_{f}"
        if key not in st.session_state:
            st.session_state[key] = 75.0

        b1, b2, b3, b4, b5 = st.columns([1,1,2,1,1])
        with b1:
            if st.button("−5", key=f"m5_{f}"):
                st.session_state[key] = float(st.session_state[key]) - 5.0
        with b2:
            if st.button("−1", key=f"m1_{f}"):
                st.session_state[key] = float(st.session_state[key]) - 1.0
        with b3:
            st.session_state[key] = st.number_input("SPL (dB(A))", value=float(st.session_state[key]), step=0.5, key=f"num_{f}")
        with b4:
            if st.button("+1", key=f"p1_{f}"):
                st.session_state[key] = float(st.session_state[key]) + 1.0
        with b5:
            if st.button("+5", key=f"p5_{f}"):
                st.session_state[key] = float(st.session_state[key]) + 5.0

        bb1, bb2, bb3 = st.columns([1,1,2])
        with bb1:
            if st.button("✅ Conferma e avanti", type="primary", key=f"ok_{f}"):
                st.session_state.cal_values[int(f)] = float(st.session_state[key])
                st.session_state.cal_idx = idx + 1
                st.rerun()
        with bb2:
            if st.button("⬅️ Indietro", disabled=(idx == 0), key=f"back_{f}"):
                st.session_state.cal_idx = max(0, idx - 1)
                st.rerun()
        with bb3:
            st.caption("Suggerimento: premi leggermente la cuffia sul coupler per sigillare.")




def ui_calibrazione_cuffie_standalone():
    """Entry point come sezione standalone nel menu."""
    ui_calibrazione_cuffie()


def ui_fonometro_wizard():
    """Wizard completo calibrazione cuffie con fonometro live via microfono."""
    import streamlit.components.v1 as components
    import json

    _HTML = """ + repr(HTML_FONOMETRO) + """

    st.subheader("Wizard calibrazione cuffie — fonometro integrato")
    st.caption(
        "5 passi guidati: setup → posizione microfono → verifica ambiente → "
        "misura frequenza per frequenza → salvataggio profilo. "
        "Usa il microfono del browser come fonometro oppure inserisci manualmente "
        "i valori letti su app esterna (Decibel X, NIOSH SLM, Sound Meter)."
    )

    result = components.html(_HTML, height=750, scrolling=True)

    if result:
        try:
            data = json.loads(result) if isinstance(result, str) else result
            if data and data.get("misure"):
                st.success(
                    f"Profilo salvato: {data.get('brand','')} {data.get('model','')} "
                    f"su {data.get('device','')} — "
                    f"{len(data['misure'])} frequenze misurate"
                )
                with st.expander("Dettaglio misure"):
                    for f, db in data["misure"].items():
                        off = round(db - (-20), 1)
                        st.write(f"{int(f):>6} Hz: {db} dB(A)  offset {off:+.1f} dB")
        except Exception:
            pass
