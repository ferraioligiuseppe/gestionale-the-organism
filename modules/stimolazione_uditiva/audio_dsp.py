# modules/stimolazione_uditiva/audio_dsp.py
from __future__ import annotations

import math
import numpy as np
from dataclasses import dataclass
from typing import Tuple, Dict, List

@dataclass
class Biquad:
    b0: float; b1: float; b2: float
    a1: float; a2: float
    z1: float = 0.0
    z2: float = 0.0

    def process(self, x: np.ndarray) -> np.ndarray:
        # Direct Form I transposed
        y = np.empty_like(x, dtype=np.float32)
        b0,b1,b2,a1,a2 = self.b0,self.b1,self.b2,self.a1,self.a2
        z1,z2 = self.z1,self.z2
        for i, xi in enumerate(x.astype(np.float32, copy=False)):
            yi = b0*xi + z1
            z1 = b1*xi - a1*yi + z2
            z2 = b2*xi - a2*yi
            y[i] = yi
        self.z1, self.z2 = float(z1), float(z2)
        return y

def _normalize(b0,b1,b2,a0,a1,a2) -> Tuple[float,float,float,float,float]:
    b0/=a0; b1/=a0; b2/=a0; a1/=a0; a2/=a0
    return b0,b1,b2,a1,a2

def biquad_peaking(fs: float, f0: float, q: float, gain_db: float) -> Biquad:
    # RBJ Audio EQ Cookbook
    A = 10**(gain_db/40.0)
    w0 = 2*math.pi*f0/fs
    alpha = math.sin(w0)/(2*q)
    cosw0 = math.cos(w0)
    b0 = 1 + alpha*A
    b1 = -2*cosw0
    b2 = 1 - alpha*A
    a0 = 1 + alpha/A
    a1 = -2*cosw0
    a2 = 1 - alpha/A
    b0,b1,b2,a1,a2 = _normalize(b0,b1,b2,a0,a1,a2)
    return Biquad(b0,b1,b2,a1,a2)

def biquad_bandpass(fs: float, f0: float, q: float) -> Biquad:
    # RBJ bandpass (constant skirt gain, peak gain = Q)
    w0 = 2*math.pi*f0/fs
    alpha = math.sin(w0)/(2*q)
    cosw0 = math.cos(w0)
    b0 = alpha
    b1 = 0.0
    b2 = -alpha
    a0 = 1 + alpha
    a1 = -2*cosw0
    a2 = 1 - alpha
    b0,b1,b2,a1,a2 = _normalize(b0,b1,b2,a0,a1,a2)
    return Biquad(b0,b1,b2,a1,a2)

def apply_cascade(x: np.ndarray, filters: List[Biquad]) -> np.ndarray:
    y = x.astype(np.float32, copy=False)
    for f in filters:
        y = f.process(y)
    return y

def db_to_lin(db: float) -> float:
    return float(10**(db/20.0))

def soft_limiter(x: np.ndarray, peak_dbfs: float = -1.0) -> np.ndarray:
    # semplice: clamp soft tramite tanh; per preview basta
    peak = db_to_lin(peak_dbfs)
    return (np.tanh(x/peak) * peak).astype(np.float32)
