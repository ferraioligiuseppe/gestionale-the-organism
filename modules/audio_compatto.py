# -*- coding: utf-8 -*-
"""Audio compatto per le registrazioni di seduta.

Il registratore del browser (st.audio_input) produce WAV non compresso a
44-48 kHz: circa 5-6 MB al minuto. Una seduta di mezz'ora superava i 25 MB,
il limite oltre cui la trascrizione rifiuta il file, e pesava sul database.

Qui l'audio diventa:
  · mono, 16 kHz (quanto basta per la voce: la trascrizione lavora a 16 kHz)
  · MP3 a 32 kbps con lameenc  → circa 240 KB al minuto, 100 minuti stanno in 25 MB
  · se lameenc non c'e', WAV 16 kHz mono → circa 1,9 MB al minuto (3 volte meno)
"""
from __future__ import annotations

import io
import wave

FREQ = 16000
KBPS = 32


def _pcm16k(dati: bytes) -> bytes | None:
    try:
        import numpy as np
        with wave.open(io.BytesIO(dati)) as w:
            ch, sw, sr, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
            raw = w.readframes(n)
        if sw == 2:
            a = np.frombuffer(raw, dtype="<i2").astype(np.float32)
        elif sw == 4:
            a = np.frombuffer(raw, dtype="<i4").astype(np.float32) / 65536.0
        elif sw == 1:
            a = (np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 128.0) * 256.0
        else:
            return None
        if ch > 1:
            a = a[: len(a) - len(a) % ch].reshape(-1, ch).mean(axis=1)
        if sr != FREQ and len(a) > 1:
            # filtro passa-basso semplice prima di ridurre, per non «sporcare» la voce
            k = max(1, int(round(sr / FREQ)))
            if k > 1:
                a = np.convolve(a, np.ones(k, dtype=np.float32) / k, mode="same")
            m = max(1, int(len(a) * FREQ / sr))
            a = np.interp(np.linspace(0, len(a) - 1, m), np.arange(len(a)), a)
        return np.clip(a, -32768, 32767).astype("<i2").tobytes()
    except Exception:
        return None


def comprimi(dati: bytes, mime: str = "audio/wav") -> tuple[bytes, str]:
    """(dati, mime) compressi. Se il formato non e' WAV lo lascia com'e'."""
    if not dati:
        return dati, mime or "audio/wav"
    if "wav" not in (mime or "").lower() and dati[:4] != b"RIFF":
        return dati, mime or "audio/webm"
    pcm = _pcm16k(dati)
    if pcm is None:
        return dati, "audio/wav"
    try:
        import lameenc
        enc = lameenc.Encoder()
        enc.set_bit_rate(KBPS)
        enc.set_in_sample_rate(FREQ)
        enc.set_channels(1)
        enc.set_quality(5)
        mp3 = bytes(enc.encode(pcm)) + bytes(enc.flush())
        if mp3:
            return mp3, "audio/mpeg"
    except Exception:
        pass
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(FREQ)
        w.writeframes(pcm)
    return buf.getvalue(), "audio/wav"


def nome_file(mime: str) -> str:
    m = (mime or "").lower()
    return "seduta.mp3" if "mpeg" in m or "mp3" in m else "seduta.webm" if "webm" in m else "seduta.wav"


def peso(n: int) -> str:
    return f"{n / 1024:.0f} KB" if n < 1024 * 1024 else f"{n / 1024 / 1024:.1f} MB"
