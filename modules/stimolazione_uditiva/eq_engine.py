# modules/stimolazione_uditiva/eq_engine.py
from __future__ import annotations

from typing import Dict
from .db_orl import FREQS_STD

def _linear_interp(x0, y0, x1, y1, x):
    if x1 == x0:
        return y0
    t = (x - x0) / (x1 - x0)
    return y0 + t * (y1 - y0)

def _fill_missing(soglie: Dict[int, float | None]) -> Dict[int, float]:
    """Riempie valori mancanti con interpolazione lineare sulle frequenze standard."""
    # punti noti
    known = [(f, soglie.get(f)) for f in FREQS_STD if soglie.get(f) is not None]
    if not known:
        # nessun dato -> 0 (neutro)
        return {f: 0.0 for f in FREQS_STD}

    known.sort(key=lambda t: t[0])
    out: Dict[int, float] = {}

    for f in FREQS_STD:
        v = soglie.get(f)
        if v is not None:
            out[f] = float(v)
            continue
        # trova intervallo
        left = None
        right = None
        for fk, vk in known:
            if fk < f:
                left = (fk, float(vk))
            if fk > f and right is None:
                right = (fk, float(vk))
        if left and right:
            out[f] = float(_linear_interp(left[0], left[1], right[0], right[1], f))
        elif left:
            out[f] = float(left[1])
        else:
            out[f] = float(known[0][1])
    return out

def _smooth_3pt(vals: Dict[int, float]) -> Dict[int, float]:
    """Smoothing semplice 3 punti sulle frequenze standard (media pesata)."""
    out = {}
    freqs = FREQS_STD
    for i, f in enumerate(freqs):
        v = vals[f]
        if 0 < i < len(freqs) - 1:
            v = 0.25 * vals[freqs[i-1]] + 0.5 * vals[f] + 0.25 * vals[freqs[i+1]]
        out[f] = float(v)
    return out
def compute_eq_baseline(
    soglie,
    boost_max_db=12,
    cut_max_db=12,
    smoothing=True,
):
    from .db_orl import FREQS_STD

    TOMATIS_TARGET = {
        125: -5,
        250: -3,
        500: 0,
        1000: 2,
        2000: 4,
        4000: 6,
        6000: 8,
        8000: 6,
    }

    eq = {}

    for f in FREQS_STD:

        soglia = soglie.get(f)

        if soglia is None:
            eq[f] = 0
            continue

        target = TOMATIS_TARGET.get(f, 0)

        # differenza rispetto alla curva target
        gain = target - soglia

        # clamp sicurezza
        if gain > boost_max_db:
            gain = boost_max_db

        if gain < -cut_max_db:
            gain = -cut_max_db

        eq[f] = round(gain, 2)

    return eq
