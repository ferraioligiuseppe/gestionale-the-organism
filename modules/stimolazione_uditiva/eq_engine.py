# modules/stimolazione_uditiva/eq_engine.py
from __future__ import annotations

import math
from typing import Dict

from .db_orl import FREQS_STD

# Target Tomatis-like V1 (preset base)
TOMATIS_TARGET_V1: Dict[int, float] = {
    125: -5.0,
    250: -3.0,
    500: 0.0,
    1000: 2.0,
    2000: 4.0,
    4000: 6.0,
    6000: 8.0,
    8000: 6.0,
}

def _interp_missing_logfreq(vals: Dict[int, float | None]) -> Dict[int, float]:
    """
    Interpolazione lineare su asse log10(freq).
    Se estremi mancanti: nearest.
    """
    freqs = FREQS_STD
    xs = [math.log10(f) for f in freqs]
    ys = [vals.get(f, None) for f in freqs]

    known = [(i, float(ys[i])) for i in range(len(freqs)) if ys[i] is not None]
    if not known:
        return {f: 0.0 for f in freqs}

    out: Dict[int, float] = {}
    for i, f in enumerate(freqs):
        if ys[i] is not None:
            out[f] = float(ys[i])
            continue

        left = [k for k in known if k[0] < i]
        right = [k for k in known if k[0] > i]

        if not left:
            out[f] = float(known[0][1])
            continue
        if not right:
            out[f] = float(known[-1][1])
            continue

        i0, y0 = left[-1]
        i1, y1 = right[0]
        x0, x1 = xs[i0], xs[i1]
        x = xs[i]
        t = (x - x0) / (x1 - x0) if (x1 - x0) != 0 else 0.0
        out[f] = float(y0 + t * (y1 - y0))

    return out

def _smooth_weighted_3pt(vals: Dict[int, float]) -> Dict[int, float]:
    """
    Smoothing 3-punti (0.25, 0.5, 0.25) sulle frequenze standard.
    È una “curva inviluppo” semplice e stabile (ottima per partire).
    """
    freqs = FREQS_STD
    out: Dict[int, float] = {}
    for i, f in enumerate(freqs):
        if i == 0 or i == len(freqs) - 1:
            out[f] = float(vals[f])
        else:
            f0, f1, f2 = freqs[i - 1], freqs[i], freqs[i + 1]
            out[f] = float(0.25 * vals[f0] + 0.5 * vals[f1] + 0.25 * vals[f2])
    return out

def compute_eq_baseline(
    soglie_db_hl: Dict[int, float | None],
    boost_max_db: float = 12.0,
    cut_max_db: float = 12.0,
    smoothing: bool = True,
    target: Dict[int, float] | None = None,
) -> Dict[int, float]:
    """
    EQ baseline Tomatis-like (V1):
    - soglie ORL dB HL (input)
    - inviluppo (interp + smoothing) per stabilità biologica
    - confronto con curva target (Tomatis-like)
    - clamp sicurezza
    Output: gain/cut per frequenza (dB)
    """
    if target is None:
        target = TOMATIS_TARGET_V1

    # 1) fill missing
    filled = _interp_missing_logfreq(soglie_db_hl)

    # 2) inviluppo (smoothing)
    env = _smooth_weighted_3pt(filled) if smoothing else filled

    # 3) differenza target - inviluppo
    eq: Dict[int, float] = {}
    for f in FREQS_STD:
        t = float(target.get(f, 0.0))
        g = t - float(env[f])

        # 4) clamp
        if g > float(boost_max_db):
            g = float(boost_max_db)
        if g < -float(cut_max_db):
            g = -float(cut_max_db)

        eq[f] = float(round(g, 2))

    return eq
