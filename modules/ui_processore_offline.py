# -*- coding: utf-8 -*-
"""
Processore Offline — Metodo Hipérion
Gestionale The Organism

Prende un file audio (WAV/MP3/FLAC), applica:
  - EQ paziente (delta Tomatis, 11 bande per canale)
  - Gate Ampiezza (Bascula Ampiezza Hipérion)
  - Gate Frequenze (Bascula Frequenze tornante)
  - Gate G/D (alternanza OD/OS)
  - Lissage (smoothing)
  - Binaurale beats (Delta/Theta/Alfa/Beta/Gamma)
Esporta WAV stereo processato, pronto per piattaforma.
"""

import io
import math
import json
import numpy as np
import streamlit as st


# ─────────────────────────────────────────────────────────────────────────────
# Costanti
# ─────────────────────────────────────────────────────────────────────────────

FREQS_EQ = [125, 250, 500, 750, 1000, 1500, 2000, 3000, 4000, 6000, 8000]
FLABELS  = ['125','250','500','750','1k','1.5k','2k','3k','4k','6k','8k']

BINAURAL_PRESETS = {
    "Delta 2 Hz — Sonno / autoguarigione":      2.0,
    "Theta 5 Hz — Meditazione profonda":         5.0,
    "Alfa 10 Hz — Rilassamento / creativita":   10.0,
    "Beta basso 15 Hz — Focus / concentrazione": 15.0,
    "Beta alto 25 Hz — Veglia / attivita":       25.0,
    "Gamma 40 Hz — Alta cognizione":             40.0,
}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers DSP
# ─────────────────────────────────────────────────────────────────────────────

def _load_audio(uploaded_file):
    """Carica file audio uploadato → (samples_float32, samplerate, n_channels)."""
    data = uploaded_file.read()
    ext  = uploaded_file.name.rsplit(".", 1)[-1].lower()

    try:
        import soundfile as sf
        buf = io.BytesIO(data)
        samples, sr = sf.read(buf, dtype="float32", always_2d=True)
        return samples, sr, samples.shape[1]
    except Exception:
        pass

    # Fallback: pydub → numpy
    try:
        from pydub import AudioSegment
        buf = io.BytesIO(data)
        seg = AudioSegment.from_file(buf, format=ext)
        seg = seg.set_channels(2).set_sample_width(4)
        arr = np.frombuffer(seg.raw_data, dtype=np.float32)
        sr  = seg.frame_rate
        arr = arr.reshape(-1, 2) / 32768.0
        return arr, sr, 2
    except Exception as e:
        raise RuntimeError(f"Impossibile caricare il file audio: {e}")


def _ensure_stereo(samples):
    """Se mono → duplica in stereo."""
    if samples.ndim == 1:
        samples = np.stack([samples, samples], axis=1)
    if samples.shape[1] == 1:
        samples = np.concatenate([samples, samples], axis=1)
    return samples


def _peaking_eq(samples, sr, freq_hz, gain_db, Q=1.4):
    """Applica filtro peaking EQ (biquad) a un canale mono."""
    from scipy.signal import lfilter, bilinear_zpk, zpk2sos, sosfilt
    if abs(gain_db) < 0.1:
        return samples
    try:
        from scipy.signal import sosfilt, iirpeak
        A  = 10**(gain_db/40.0)
        w0 = 2 * math.pi * freq_hz / sr
        alpha = math.sin(w0) / (2 * Q)
        b0 =  1 + alpha * A
        b1 = -2 * math.cos(w0)
        b2 =  1 - alpha * A
        a0 =  1 + alpha / A
        a1 = -2 * math.cos(w0)
        a2 =  1 - alpha / A
        b = np.array([b0, b1, b2]) / a0
        a = np.array([1.0, a1/a0, a2/a0])
        return lfilter(b, a, samples)
    except Exception:
        return samples


def _apply_eq_channel(ch, sr, gains):
    """Applica 11 bande EQ a un canale."""
    out = ch.copy()
    for i, freq in enumerate(FREQS_EQ):
        if abs(gains[i]) > 0.1:
            out = _peaking_eq(out, sr, freq, gains[i])
    return out


def _generate_gate_envelope(n_samples, sr,
                             t_min, t_max, atten_db,
                             lissage_ms, gd_mode, alea):
    """
    Genera envelope gate ampiezza.
    Ritorna array (n_samples,) con valori 0..1.
    """
    fade_n  = max(1, int(lissage_ms / 1000 * sr))
    atten_l = 10 ** (-abs(atten_db) / 20.0)
    env     = np.ones(n_samples, dtype=np.float32)
    i       = 0
    high    = True

    while i < n_samples:
        if alea:
            dur_s = t_min + np.random.random() * (t_max - t_min)
        else:
            dur_s = (t_min + t_max) / 2
        seg_n = min(int(dur_s * sr), n_samples - i)
        if seg_n <= 0:
            break

        level = 1.0 if high else atten_l
        seg   = np.full(seg_n, level, dtype=np.float32)

        # Fade in
        fade_in  = min(fade_n, seg_n // 4)
        prev_lvl = atten_l if high else 1.0
        seg[:fade_in] = np.linspace(prev_lvl, level, fade_in)

        # Fade out
        fade_out = min(fade_n, seg_n // 4)
        seg[-fade_out:] = np.linspace(level, atten_l if high else 1.0, fade_out)

        env[i:i+seg_n] = seg
        i    += seg_n
        high  = not high

    return env


def _generate_freq_gate_envelope(n_samples, sr,
                                  tornante_hz, atten_range,
                                  t_min_ms, t_max_ms, alea):
    """
    Genera gain envelope per gate frequenza (oscillazione attorno a tornante).
    Ritorna array (n_samples,) con valori -max_atten..0 dB.
    """
    env = np.zeros(n_samples, dtype=np.float32)
    i   = 0
    while i < n_samples:
        if alea:
            dur_ms = t_min_ms + np.random.random() * (t_max_ms - t_min_ms)
        else:
            dur_ms = (t_min_ms + t_max_ms) / 2
        seg_n  = min(int(dur_ms / 1000 * sr), n_samples - i)
        if seg_n <= 0:
            break
        atten  = np.random.uniform(-atten_range[1], -atten_range[0])
        env[i:i+seg_n] = atten
        i += seg_n
    return env


def _apply_freq_gate(ch, sr, tornante_hz, gain_db_arr):
    """Applica modulazione frequenza tornante campione per campione con lfilter."""
    # Approssimazione: applica EQ a blocchi con guadagno variabile
    block = max(256, sr // 20)
    out   = ch.copy()
    for start in range(0, len(ch), block):
        end   = min(start + block, len(ch))
        g_db  = float(np.mean(gain_db_arr[start:end]))
        seg   = _peaking_eq(ch[start:end], sr, tornante_hz, g_db, Q=2.0)
        out[start:end] = seg
    return out


def _generate_binaural(n_samples, sr, carrier_hz, beat_hz, amplitude=0.08):
    """
    Genera toni binaurali: OD = carrier, OS = carrier + beat.
    Ritorna (tone_od, tone_os) array float32.
    """
    t      = np.arange(n_samples) / sr
    tone_od = amplitude * np.sin(2 * math.pi * carrier_hz * t).astype(np.float32)
    tone_os = amplitude * np.sin(2 * math.pi * (carrier_hz + beat_hz) * t).astype(np.float32)
    # Fade in/out 2 sec
    fade_n = min(2 * sr, n_samples // 4)
    fade   = np.linspace(0, 1, fade_n).astype(np.float32)
    tone_od[:fade_n]  *= fade;  tone_od[-fade_n:]  *= fade[::-1]
    tone_os[:fade_n]  *= fade;  tone_os[-fade_n:]  *= fade[::-1]
    return tone_od, tone_os


def _samples_to_wav(samples_stereo, sr):
    """Converte array float32 stereo → bytes WAV."""
    import wave
    pcm = np.int16(np.clip(samples_stereo, -1.0, 1.0) * 32767)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────────────────────────────────────

def ui_processore_offline(eq_od_default=None, eq_os_default=None):
    """
    Tab processore offline.
    eq_od_default, eq_os_default: liste di 11 float (delta Tomatis dal profilo paziente).
    """
    st.subheader("Processore offline — Esporta audio Hipérion")
    st.caption(
        "Carica un file WAV/MP3/FLAC, configura i parametri e scarica il file "
        "processato con gating Hipérion + EQ paziente + binaurale."
    )

    eq_od = eq_od_default or [0]*11
    eq_os = eq_os_default or [0]*11

    # ── Caricamento file ─────────────────────────────────────────────────────
    st.markdown("**1. File sorgente**")
    uploaded = st.file_uploader(
        "Carica file audio (WAV, MP3, FLAC — max 200MB)",
        type=["wav","mp3","flac","ogg","aiff","aif"],
        key="proc_upload"
    )

    if not uploaded:
        st.info("Carica un file audio per iniziare.")
        return

    st.success(f"File caricato: {uploaded.name}")

    # ── EQ Paziente ──────────────────────────────────────────────────────────
    st.markdown("**2. Profilo EQ paziente**")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("*OD — canale destro*")
        eq_od_edit = []
        cols = st.columns(11)
        for i, (lbl, v) in enumerate(zip(FLABELS, eq_od)):
            val = cols[i].number_input(lbl, -30, 30, int(v), 1,
                                        key=f"proc_od_{i}")
            eq_od_edit.append(int(val))
    with c2:
        st.markdown("*OS — canale sinistro*")
        eq_os_edit = []
        cols = st.columns(11)
        for i, (lbl, v) in enumerate(zip(FLABELS, eq_os)):
            val = cols[i].number_input(lbl, -30, 30, int(v), 1,
                                        key=f"proc_os_{i}")
            eq_os_edit.append(int(val))

    # ── Gating Hipérion ───────────────────────────────────────────────────────
    st.markdown("**3. Gating Hipérion**")
    ga1, ga2 = st.columns(2)

    with ga1:
        st.markdown("*Bascula Ampiezza*")
        g_atten   = st.selectbox("Attenuazione", [0,3,6,9,12,15,20], index=3,
                                  format_func=lambda x: f"{x} dB",
                                  key="proc_gatten")
        g_tmin    = st.select_slider("Tempo min", [0.2,0.5,1.0,1.5,2.0,3.0,5.0],
                                      value=1.0, key="proc_gtmin",
                                      format_func=lambda x: f"{x}s")
        g_tmax    = st.select_slider("Tempo max", [0.5,1.0,1.5,2.0,3.0,5.0],
                                      value=0.5, key="proc_gtmax",
                                      format_func=lambda x: f"{x}s")
        lissage_ms = st.slider("Lissage (ms)", 0, 500, 30, 10,
                                key="proc_lissage")
        gd_mode   = st.toggle("Gate G/D (alternanza OD/OS)", value=True,
                               key="proc_gd")
        alea      = st.toggle("Alea (timing random)", value=True,
                               key="proc_alea")

    with ga2:
        st.markdown("*Bascula Frequenze*")
        tornante  = st.selectbox("Frequenza tornante",
                                  [750,1000,1500,2000,2500,3000,3500,4000],
                                  index=2,
                                  format_func=lambda x: f"{x} Hz",
                                  key="proc_tornante")
        f_range   = st.selectbox("Range attenuazione",
                                  ["0-9 dB","3-13 dB","6-16 dB",
                                   "9-20 dB","12-25 dB","15-30 dB","25-35 dB"],
                                  key="proc_frange")
        f_tmin_ms = st.select_slider("Tempo min freq",
                                      [100,150,200,300,500,1000],
                                      value=100, key="proc_ftmin",
                                      format_func=lambda x: f"{x}ms")
        f_tmax_ms = st.select_slider("Tempo max freq",
                                      [500,1000,1500,2000,3000],
                                      value=1500, key="proc_ftmax",
                                      format_func=lambda x: f"{x}ms")

    # ── Binaurale ─────────────────────────────────────────────────────────────
    st.markdown("**4. Effetto binaurale**")
    bin_on = st.toggle("Abilita binaurale", value=True, key="proc_bin_on")
    if bin_on:
        bc1, bc2, bc3 = st.columns(3)
        with bc1:
            bin_preset = st.selectbox("Preset onda",
                                       list(BINAURAL_PRESETS.keys()),
                                       index=2, key="proc_bin_preset")
            beat_hz = BINAURAL_PRESETS[bin_preset]
        with bc2:
            carrier_hz = st.number_input("Carrier (Hz)", 50, 500, 200, 10,
                                          key="proc_carrier")
        with bc3:
            bin_vol = st.slider("Volume binaurale %", 1, 30, 8,
                                 key="proc_bin_vol")
        st.caption(
            f"OD: {carrier_hz} Hz · OS: {carrier_hz + beat_hz} Hz · "
            f"Beat: {beat_hz} Hz"
        )

    # ── Elaborazione ─────────────────────────────────────────────────────────
    st.markdown("**5. Elabora e scarica**")
    col_info, col_btn = st.columns([3,1])

    with col_info:
        st.caption(
            "L'elaborazione avviene completamente server-side in Python. "
            "Per file lunghi (60 min) può richiedere 30-60 secondi."
        )

    with col_btn:
        proc_btn = st.button("Elabora file", type="primary",
                              key="proc_run", use_container_width=True)

    if proc_btn:
        # Parse range attenuazione frequenze
        parts      = f_range.replace(" dB","").split("-")
        f_atten_min = abs(float(parts[0])) if parts[0] else 0.0
        f_atten_max = abs(float(parts[1])) if len(parts) > 1 else 9.0

        progress = st.progress(0, text="Caricamento file...")

        try:
            # 1. Carica audio
            uploaded.seek(0)
            samples, sr, n_ch = _load_audio(uploaded)
            samples = _ensure_stereo(samples)
            n_samples = len(samples)
            dur_sec   = n_samples / sr
            progress.progress(10, text=f"Audio caricato: {dur_sec:.0f}s, {sr}Hz")

            # 2. EQ OD
            progress.progress(20, text="Applicazione EQ OD...")
            ch_od = _apply_eq_channel(samples[:,0], sr, eq_od_edit)

            # 3. EQ OS
            progress.progress(30, text="Applicazione EQ OS...")
            ch_os = _apply_eq_channel(samples[:,1], sr, eq_os_edit)

            # 4. Gate Ampiezza
            progress.progress(40, text="Generazione gate ampiezza...")
            g_tmin_f = float(g_tmin)
            g_tmax_f = float(g_tmax)
            if g_tmin_f > g_tmax_f:
                g_tmin_f, g_tmax_f = g_tmax_f, g_tmin_f

            if gd_mode:
                # Canali alternati
                env_od = _generate_gate_envelope(
                    n_samples, sr, g_tmin_f, g_tmax_f,
                    g_atten, lissage_ms, True, alea)
                env_os = 1.0 - env_od + (10**(-g_atten/20))
                env_os = np.clip(env_os, 10**(-g_atten/20), 1.0)
            else:
                env_od = _generate_gate_envelope(
                    n_samples, sr, g_tmin_f, g_tmax_f,
                    g_atten, lissage_ms, False, alea)
                env_os = env_od.copy()

            ch_od *= env_od
            ch_os *= env_os

            # 5. Gate Frequenze
            progress.progress(55, text="Applicazione gate frequenze...")
            freq_env = _generate_freq_gate_envelope(
                n_samples, sr, tornante,
                (f_atten_min, f_atten_max),
                f_tmin_ms, f_tmax_ms, alea)
            ch_od = _apply_freq_gate(ch_od, sr, tornante, freq_env)
            ch_os = _apply_freq_gate(ch_os, sr, tornante, freq_env)

            # 6. Binaurale
            if bin_on:
                progress.progress(70, text="Generazione binaurale...")
                amp_bin = bin_vol / 100.0 * 0.3
                tone_od, tone_os = _generate_binaural(
                    n_samples, sr, carrier_hz, beat_hz, amp_bin)
                ch_od = ch_od + tone_od
                ch_os = ch_os + tone_os

            # 7. Normalizzazione
            progress.progress(85, text="Normalizzazione...")
            peak = max(np.abs(ch_od).max(), np.abs(ch_os).max())
            if peak > 0.95:
                ch_od = ch_od / peak * 0.95
                ch_os = ch_os / peak * 0.95

            # 8. Export WAV
            progress.progress(92, text="Export WAV...")
            stereo = np.stack([ch_od, ch_os], axis=1).astype(np.float32)
            wav_bytes = _samples_to_wav(stereo, sr)

            progress.progress(100, text="Completato!")

            # Nome file output
            base_name = uploaded.name.rsplit(".", 1)[0]
            out_name  = f"{base_name}_hiperion.wav"

            st.success(
                f"Elaborazione completata — {dur_sec/60:.1f} min · "
                f"{len(wav_bytes)//1024//1024} MB"
            )

            st.download_button(
                label=f"Scarica {out_name}",
                data=wav_bytes,
                file_name=out_name,
                mime="audio/wav",
                type="primary",
                key="proc_download"
            )

            # Anteprima
            st.markdown("**Anteprima** (primi 30 secondi)")
            preview_n = min(30 * sr, n_samples)
            preview   = stereo[:preview_n]
            st.audio(_samples_to_wav(preview, sr), format="audio/wav")

        except Exception as e:
            progress.empty()
            st.error(f"Errore elaborazione: {e}")
            import traceback
            st.code(traceback.format_exc())
