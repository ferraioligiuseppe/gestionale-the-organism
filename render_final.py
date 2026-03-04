# modules/stimolazione_uditiva/render_final.py
from __future__ import annotations

import io
import random
from dataclasses import dataclass
from typing import Any, Dict, Tuple, Optional

import numpy as np

from .audio_dsp import (
    biquad_peaking, biquad_bandpass, db_to_lin, soft_limiter
)
from .db_orl import FREQS_STD


def _read_audio_bytes_any(data: bytes, filename: str) -> Tuple[np.ndarray, int]:
    """
    Best-effort decoder:
      - WAV 16-bit PCM: sempre OK (stdlib wave)
      - FLAC/WAV/OGG/AIFF: se 'soundfile' è disponibile
      - MP3: se 'pydub' + ffmpeg sono disponibili
    Ritorna float32 stereo shape (n,2) e sample_rate.
    """
    name = (filename or "").lower().strip()

    if name.endswith(".wav"):
        import wave
        bio = io.BytesIO(data)
        with wave.open(bio, "rb") as wf:
            ch = wf.getnchannels()
            fs = wf.getframerate()
            sampw = wf.getsampwidth()
            nframes = wf.getnframes()
            raw = wf.readframes(nframes)

        if sampw != 2:
            raise ValueError("WAV input deve essere PCM 16-bit. Converti in WAV 16-bit.")
        x = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
        if ch == 1:
            x = np.stack([x, x], axis=1)
        elif ch == 2:
            x = x.reshape(-1, 2)
        else:
            raise ValueError("Supporto solo mono o stereo.")
        return x, int(fs)

    # soundfile (FLAC ecc.)
    try:
        import soundfile as sf  # type: ignore
        bio = io.BytesIO(data)
        x, fs = sf.read(bio, dtype="float32", always_2d=True)
        if x.shape[1] == 1:
            x = np.repeat(x, 2, axis=1)
        elif x.shape[1] != 2:
            raise ValueError("Supporto solo mono o stereo.")
        return x.astype(np.float32, copy=False), int(fs)
    except Exception:
        pass

    # MP3 via pydub/ffmpeg
    if name.endswith(".mp3"):
        try:
            from pydub import AudioSegment  # type: ignore
        except Exception as e:
            raise ValueError("Per MP3 serve 'pydub' + ffmpeg. Converti MP3→WAV 16-bit e ricarica.") from e
        seg = AudioSegment.from_file(io.BytesIO(data), format="mp3").set_channels(2)
        fs = int(seg.frame_rate)
        samples = np.array(seg.get_array_of_samples()).reshape((-1, 2)).astype(np.float32)
        maxv = float(2 ** (8 * seg.sample_width - 1))
        x = samples / maxv
        return x.astype(np.float32, copy=False), fs

    raise ValueError("Formato non supportato. Usa WAV 16-bit (consigliato) oppure abilita soundfile/pydub.")


def _write_wav16_bytes(x: np.ndarray, fs: int) -> bytes:
    import wave
    x = np.clip(x, -1.0, 1.0)
    pcm16 = (x * 32767.0).astype("<i2")
    bio = io.BytesIO()
    with wave.open(bio, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(int(fs))
        wf.writeframes(pcm16.tobytes())
    return bio.getvalue()


def _write_flac_bytes(x: np.ndarray, fs: int) -> bytes:
    try:
        import soundfile as sf  # type: ignore
    except Exception as e:
        raise ValueError("Per esportare FLAC serve 'soundfile' (libsndfile).") from e
    bio = io.BytesIO()
    sf.write(bio, np.clip(x, -1.0, 1.0), int(fs), format="FLAC", subtype="PCM_16")
    return bio.getvalue()


def _write_mp3_bytes(x: np.ndarray, fs: int, bitrate: str = "192k") -> bytes:
    try:
        from pydub import AudioSegment  # type: ignore
    except Exception as e:
        raise ValueError("Per esportare MP3 serve 'pydub' + ffmpeg.") from e
    x = np.clip(x, -1.0, 1.0)
    pcm16 = (x * 32767.0).astype(np.int16)
    seg = AudioSegment(
        data=pcm16.tobytes(),
        sample_width=2,
        frame_rate=int(fs),
        channels=2,
    )
    out = io.BytesIO()
    seg.export(out, format="mp3", bitrate=str(bitrate))
    return out.getvalue()


@dataclass
class GateState:
    mode: str = "closed_wait"   # closed_wait -> open -> closed
    time_left_s: float = 0.0
    attack_left_s: float = 0.0


def _build_eq_filters(fs: int, gains: Dict[int, float], q: float = 1.0):
    filters = []
    for f in FREQS_STD:
        g = float(gains.get(f, 0.0))
        if abs(g) < 0.01:
            continue
        filters.append(biquad_peaking(fs, float(f), q=float(q), gain_db=g))
    return filters


def _choose_band(params: Dict[str, Any]) -> Tuple[float, float]:
    bands = params["bands"]
    choices = [
        ("low",  float(bands["low"]["weight"])),
        ("mid",  float(bands["mid"]["weight"])),
        ("high", float(bands["high"]["weight"])),
    ]
    r = random.random() * sum(w for _, w in choices)
    acc = 0.0
    pick = "mid"
    for name, w in choices:
        acc += w
        if r <= acc:
            pick = name
            break
    b = bands[pick]
    return float(b["min_hz"]), float(b["max_hz"])


def _dominant_at_time(lb: Dict[str, Any], t_s: float) -> str:
    mode = lb.get("mode", "fixed")
    dom = lb.get("dominant_side", "DX")
    if mode != "alternate":
        return dom
    mins = float(lb.get("alternate_minutes", 2.5))
    if mins <= 0:
        return dom
    period = mins * 60.0
    return dom if (int(t_s // period) % 2 == 0) else ("SX" if dom == "DX" else "DX")


def render_full(
    audio_bytes: bytes,
    filename: str,
    eq_gain_dx: Dict[int, float],
    eq_gain_sx: Dict[int, float],
    preset_params: Dict[str, Any],
    *,
    limiter_peak_dbfs: float = -1.0,
    out_formats: Tuple[str, ...] = ("wav", "flac"),
    mp3_bitrate: str = "192k",
    max_seconds: Optional[float] = None,
) -> Dict[str, bytes]:
    """
    Render file finale in memoria (best-effort).
    Nota: file lunghi possono essere pesanti su Streamlit Cloud.
    """
    x, fs = _read_audio_bytes_any(audio_bytes, filename)
    if max_seconds is not None:
        x = x[: int(max_seconds * fs), :]

    n = x.shape[0]
    if n <= 0:
        raise ValueError("Audio vuoto.")

    # EQ filters (stateful)
    eqL = _build_eq_filters(fs, eq_gain_sx, q=1.0)  # 0=SX
    eqR = _build_eq_filters(fs, eq_gain_dx, q=1.0)  # 1=DX

    # closed bandpass default
    q_closed = float(preset_params["closed_state"]["q"].get("value", 2.8))
    center_closed = float(preset_params["closed_state"]["center_hz"].get("value", 1000.0))

    # gating params
    lam = float(preset_params.get("lambda_events_per_sec", 5.0))
    open_min = float(preset_params["open_state"]["duration_ms"]["min"]) / 1000.0
    open_max = float(preset_params["open_state"]["duration_ms"]["max"]) / 1000.0
    att_min  = float(preset_params["open_state"]["attack_ms"]["min"]) / 1000.0
    att_max  = float(preset_params["open_state"]["attack_ms"]["max"]) / 1000.0
    ref_min  = float(preset_params["closed_state"]["refractory_ms"]["min"]) / 1000.0
    ref_max  = float(preset_params["closed_state"]["refractory_ms"]["max"]) / 1000.0

    wet_mix = float(preset_params["mix"].get("wet_mix", 0.9))
    closed_att_db = float(preset_params["mix"].get("closed_wet_attenuation_db", -10.0))
    closed_wet = db_to_lin(closed_att_db)

    # bias
    lb = preset_params.get("lateral_bias", {})
    ratio = float(lb.get("ratio", 0.7))
    g_dom = 1.0
    g_oth = max(0.0, min(1.0, (1.0 - ratio) / ratio)) if ratio > 0 else 1.0

    # bandpass stateful
    bpL = biquad_bandpass(fs, center_closed, q_closed)
    bpR = biquad_bandpass(fs, center_closed, q_closed)

    st = GateState(
        mode="closed_wait",
        time_left_s=(random.expovariate(lam) if lam > 0 else 1e9),
        attack_left_s=0.0,
    )
    t_s = 0.0

    out = np.zeros_like(x, dtype=np.float32)
    block = 2048
    i = 0
    while i < n:
        j = min(n, i + block)
        block_n = j - i

        # EQ block (keep states)
        L = x[i:j, 0].astype(np.float32, copy=True)
        R = x[i:j, 1].astype(np.float32, copy=True)
        for f in eqL:
            L = f.process(L)
        for f in eqR:
            R = f.process(R)
        dryL, dryR = L, R

        env = np.empty((block_n,), dtype=np.float32)
        for k in range(block_n):
            dt = 1.0 / fs

            if st.time_left_s <= 0.0:
                if st.mode == "closed_wait":
                    # start OPEN
                    st.mode = "open"
                    st.time_left_s = random.uniform(open_min, open_max)
                    st.attack_left_s = random.uniform(att_min, att_max)

                    fmin, fmax = _choose_band(preset_params)
                    center = random.uniform(fmin, fmax)
                    q = random.uniform(
                        float(preset_params["open_state"]["q"]["min"]),
                        float(preset_params["open_state"]["q"]["max"]),
                    )
                    bpL = biquad_bandpass(fs, center, q)
                    bpR = biquad_bandpass(fs, center, q)

                elif st.mode == "open":
                    # go CLOSED refractory
                    st.mode = "closed"
                    st.time_left_s = random.uniform(ref_min, ref_max)
                    st.attack_left_s = 0.0
                    bpL = biquad_bandpass(fs, center_closed, q_closed)
                    bpR = biquad_bandpass(fs, center_closed, q_closed)

                elif st.mode == "closed":
                    # schedule next OPEN (Poisson)
                    st.mode = "closed_wait"
                    st.time_left_s = random.expovariate(lam) if lam > 0 else 1e9
                    st.attack_left_s = 0.0

            # env value
            if st.mode == "open":
                if st.attack_left_s > 0.0:
                    # linear ramp closed_wet -> 1
                    # fraction based on remaining in attack window (approx.)
                    frac = 1.0 - max(0.0, min(1.0, st.attack_left_s / max(att_max, 1e-6)))
                    env[k] = closed_wet + (1.0 - closed_wet) * frac
                    st.attack_left_s -= dt
                else:
                    env[k] = 1.0
            else:
                env[k] = closed_wet

            st.time_left_s -= dt
            t_s += dt

        wetL = bpL.process(dryL) * env
        wetR = bpR.process(dryR) * env

        oL = dryL * (1.0 - wet_mix) + wetL * wet_mix
        oR = dryR * (1.0 - wet_mix) + wetR * wet_mix

        dom = _dominant_at_time(lb, t_s)
        if dom == "DX":
            oR *= g_dom
            oL *= g_oth
        else:
            oL *= g_dom
            oR *= g_oth

        out[i:j, 0] = oL
        out[i:j, 1] = oR
        i = j

    out = soft_limiter(out, peak_dbfs=float(limiter_peak_dbfs))

    outputs: Dict[str, bytes] = {}
    if "wav" in out_formats:
        outputs["wav"] = _write_wav16_bytes(out, fs)
    if "flac" in out_formats:
        outputs["flac"] = _write_flac_bytes(out, fs)
    if "mp3" in out_formats:
        outputs["mp3"] = _write_mp3_bytes(out, fs, bitrate=str(mp3_bitrate))
    return outputs
