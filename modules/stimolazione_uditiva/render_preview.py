# modules/stimolazione_uditiva/render_preview.py
from __future__ import annotations

import io, wave, random, json
import numpy as np
from typing import Dict, Any, Tuple

from .audio_dsp import (
    biquad_peaking, biquad_bandpass, apply_cascade, db_to_lin, soft_limiter
)
from .db_orl import FREQS_STD

def _read_wav_bytes(data: bytes, max_seconds: float = 30.0) -> Tuple[np.ndarray, int]:
    """
    Preview B2: supporto SOLO WAV PCM 16-bit (molto comune e stabile su Streamlit).
    Ritorna audio float32 shape (n,2) e sample_rate.
    """
    bio = io.BytesIO(data)
    with wave.open(bio, "rb") as wf:
        ch = wf.getnchannels()
        fs = wf.getframerate()
        sampw = wf.getsampwidth()
        nframes = wf.getnframes()
        nmax = int(min(nframes, max_seconds*fs))
        raw = wf.readframes(nmax)

    if sampw != 2:
        raise ValueError("Preview B2 supporta solo WAV PCM 16-bit. Converti il file in WAV 16-bit.")

    x = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    if ch == 1:
        x = np.stack([x, x], axis=1)
    elif ch == 2:
        x = x.reshape(-1, 2)
    else:
        raise ValueError("Supporto solo mono o stereo.")
    return x, fs

def _envelope(params: Dict[str, Any], total_samples: int, fs: int) -> np.ndarray:
    lam = float(params.get("lambda_events_per_sec", 5.0))

    open_min = float(params["open_state"]["duration_ms"]["min"]) / 1000.0
    open_max = float(params["open_state"]["duration_ms"]["max"]) / 1000.0
    att_min  = float(params["open_state"]["attack_ms"]["min"]) / 1000.0
    att_max  = float(params["open_state"]["attack_ms"]["max"]) / 1000.0

    ref_min  = float(params["closed_state"]["refractory_ms"]["min"]) / 1000.0
    ref_max  = float(params["closed_state"]["refractory_ms"]["max"]) / 1000.0

    closed_att_db = float(params["mix"].get("closed_wet_attenuation_db", -10.0))
    closed_wet = db_to_lin(closed_att_db)

    env = np.full((total_samples,), closed_wet, dtype=np.float32)

    t = 0.0
    while True:
        dt = random.expovariate(lam) if lam > 0 else 1e9
        t += dt
        if int(t*fs) >= total_samples:
            break

        dur = random.uniform(open_min, open_max)
        att = random.uniform(att_min, att_max)
        ref = random.uniform(ref_min, ref_max)

        start = int(t*fs)
        end = min(total_samples, int((t+dur)*fs))
        if end <= start:
            continue

        att_n = max(1, int(att*fs))
        ramp_end = min(end, start+att_n)
        if ramp_end > start:
            ramp = np.linspace(closed_wet, 1.0, ramp_end-start, dtype=np.float32)
            env[start:ramp_end] = np.maximum(env[start:ramp_end], ramp)
        if end > ramp_end:
            env[ramp_end:end] = 1.0

        t = t + dur + ref

    return env

def _choose_band(params: Dict[str, Any]) -> Tuple[float,float]:
    bands = params["bands"]
    choices = [
        ("low",  float(bands["low"]["weight"])),
        ("mid",  float(bands["mid"]["weight"])),
        ("high", float(bands["high"]["weight"])),
    ]
    r = random.random() * sum(w for _,w in choices)
    acc = 0.0
    band_name = "mid"
    for name, w in choices:
        acc += w
        if r <= acc:
            band_name = name
            break
    b = bands[band_name]
    return float(b["min_hz"]), float(b["max_hz"])

def _build_eq_filters(fs: int, gains: Dict[int, float], q: float = 1.0):
    filters = []
    for f in FREQS_STD:
        g = float(gains.get(f, 0.0))
        if abs(g) < 0.01:
            continue
        filters.append(biquad_peaking(fs, float(f), q=float(q), gain_db=g))
    return filters

def render_preview_wav(
    wav_bytes: bytes,
    eq_gain_dx: Dict[int, float],
    eq_gain_sx: Dict[int, float],
    preset_params: Dict[str, Any],
    seconds: float = 30.0,
) -> Tuple[bytes, int]:
    x, fs = _read_wav_bytes(wav_bytes, max_seconds=seconds)
    n = x.shape[0]

    # EQ per canale (0=SX, 1=DX)
    eqL = _build_eq_filters(fs, eq_gain_sx, q=1.0)
    eqR = _build_eq_filters(fs, eq_gain_dx, q=1.0)

    xL = apply_cascade(x[:,0], eqL)
    xR = apply_cascade(x[:,1], eqR)
    dry = np.stack([xL, xR], axis=1)

    env = _envelope(preset_params, total_samples=n, fs=fs)

    q_closed = float(preset_params["closed_state"]["q"].get("value", 2.8))
    center_closed = float(preset_params["closed_state"]["center_hz"].get("value", 1000.0))

    block = 1024
    wet = np.zeros_like(dry, dtype=np.float32)

    bpL = biquad_bandpass(fs, center_closed, q_closed)
    bpR = biquad_bandpass(fs, center_closed, q_closed)

    i = 0
    while i < n:
        j = min(n, i+block)
        e_mean = float(env[i:j].mean())
        if e_mean > 0.75:
            fmin,fmax = _choose_band(preset_params)
            center = random.uniform(fmin, fmax)
            q = random.uniform(float(preset_params["open_state"]["q"]["min"]), float(preset_params["open_state"]["q"]["max"]))
            bpL = biquad_bandpass(fs, center, q)
            bpR = biquad_bandpass(fs, center, q)
        else:
            bpL = biquad_bandpass(fs, center_closed, q_closed)
            bpR = biquad_bandpass(fs, center_closed, q_closed)

        wet[i:j,0] = bpL.process(dry[i:j,0])
        wet[i:j,1] = bpR.process(dry[i:j,1])
        i = j

    wet_mix = float(preset_params["mix"].get("wet_mix", 0.9))
    wet = wet * env[:,None]

    out = dry*(1.0-wet_mix) + wet*wet_mix

    # Bias laterale semplice (solo fixed per preview)
    lb = preset_params.get("lateral_bias", {})
    mode = lb.get("mode", "fixed")
    dom = lb.get("dominant_side", "DX")
    ratio = float(lb.get("ratio", 0.7))
    g_dom = 1.0
    g_oth = max(0.0, min(1.0, (1.0-ratio)/(ratio) )) if ratio > 0 else 1.0

    if mode == "fixed":
        if dom == "DX":
            out[:,1] *= g_dom
            out[:,0] *= g_oth
        else:
            out[:,0] *= g_dom
            out[:,1] *= g_oth

    out = soft_limiter(out, peak_dbfs=float(preset_params.get("safety", {}).get("limiter_peak_dbfs", -1.0)))

    pcm = np.clip(out, -1.0, 1.0)
    pcm16 = (pcm * 32767.0).astype("<i2")

    bio = io.BytesIO()
    with wave.open(bio, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(fs)
        wf.writeframes(pcm16.tobytes())
    return bio.getvalue(), fs
