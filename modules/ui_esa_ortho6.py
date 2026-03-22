# -*- coding: utf-8 -*-
"""
Modulo: ESA Ortho-6 – Serie 002 (Antonio Calossi 2003)
Gestionale The Organism – PNEV

Lookup table completa: 551 combinazioni K corneale × miopia.
K disponibili:  7.20 – 8.60 mm (passo 0.05)
Miopie:        -0.50 – -5.00 D  (passo 0.25)

Per valori intermedi usa interpolazione bilineare.
"""

import math
import json
try:
    from modules.ui_raggio_potere import r_to_d, d_to_r
except ImportError:
    def r_to_d(r): return round(337.5/r, 2) if r and r>0 else 0.0
    def d_to_r(d): return round(337.5/d, 3) if d and d>0 else 0.0
import numpy as np
import io
import streamlit as st
import pandas as pd
from datetime import datetime, date

# ---------------------------------------------------------------------------
# DATABASE ESA – embedded (da ESA_002_assortimento_completo.xls)
# Struttura: ESA_DB[miopia_D][K_mm] = {BOZD, d1-d4, TD, r0-r5, PWR}
# ---------------------------------------------------------------------------

ESA_DB_RAW = {
"-0.5": {"7.2": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 7.35, "r1": 7.22, "r2": 7.22, "r3": 7.6, "r4": 8.38, "r5": 10.13, "PWR": 0.5}, "7.25": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 7.4, "r1": 7.26, "r2": 7.26, "r3": 7.65, "r4": 8.44, "r5": 10.23, "PWR": 0.5}, "7.3": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 7.46, "r1": 7.3, "r2": 7.31, "r3": 7.7, "r4": 8.5, "r5": 10.32, "PWR": 0.5}, "7.35": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 7.51, "r1": 7.34, "r2": 7.35, "r3": 7.75, "r4": 8.55, "r5": 10.42, "PWR": 0.5}, "7.4": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 7.56, "r1": 7.38, "r2": 7.4, "r3": 7.79, "r4": 8.61, "r5": 10.52, "PWR": 0.5}, "7.45": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 7.62, "r1": 7.42, "r2": 7.44, "r3": 7.84, "r4": 8.67, "r5": 10.61, "PWR": 0.5}, "7.5": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 7.67, "r1": 7.46, "r2": 7.49, "r3": 7.89, "r4": 8.73, "r5": 10.71, "PWR": 0.5}, "7.55": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 7.72, "r1": 7.5, "r2": 7.53, "r3": 7.93, "r4": 8.79, "r5": 10.81, "PWR": 0.5}, "7.6": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 7.78, "r1": 7.54, "r2": 7.58, "r3": 7.98, "r4": 8.85, "r5": 10.91, "PWR": 0.5}, "7.65": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 7.83, "r1": 7.58, "r2": 7.62, "r3": 8.03, "r4": 8.91, "r5": 11.01, "PWR": 0.5}, "7.7": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 7.88, "r1": 7.63, "r2": 7.67, "r3": 8.08, "r4": 8.97, "r5": 11.11, "PWR": 0.5}, "7.75": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 7.94, "r1": 7.67, "r2": 7.71, "r3": 8.13, "r4": 9.03, "r5": 11.21, "PWR": 0.5}, "7.8": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 7.99, "r1": 7.71, "r2": 7.76, "r3": 8.17, "r4": 9.09, "r5": 11.31, "PWR": 0.5}, "7.85": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.04, "r1": 7.75, "r2": 7.8, "r3": 8.22, "r4": 9.15, "r5": 11.41, "PWR": 0.5}, "7.9": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.1, "r1": 7.79, "r2": 7.85, "r3": 8.27, "r4": 9.21, "r5": 11.51, "PWR": 0.5}, "7.95": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.15, "r1": 7.83, "r2": 7.89, "r3": 8.32, "r4": 9.27, "r5": 11.62, "PWR": 0.5}, "8.0": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.2, "r1": 7.87, "r2": 7.94, "r3": 8.36, "r4": 9.33, "r5": 11.72, "PWR": 0.5}, "8.05": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.26, "r1": 7.91, "r2": 7.98, "r3": 8.41, "r4": 9.39, "r5": 11.83, "PWR": 0.5}, "8.1": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.31, "r1": 7.95, "r2": 8.03, "r3": 8.46, "r4": 9.45, "r5": 11.93, "PWR": 0.5}, "8.15": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.36, "r1": 7.99, "r2": 8.07, "r3": 8.51, "r4": 9.52, "r5": 12.04, "PWR": 0.5}, "8.2": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.42, "r1": 8.03, "r2": 8.12, "r3": 8.56, "r4": 9.58, "r5": 12.14, "PWR": 0.5}, "8.25": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.47, "r1": 8.07, "r2": 8.16, "r3": 8.6, "r4": 9.64, "r5": 12.25, "PWR": 0.5}, "8.3": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.52, "r1": 8.11, "r2": 8.21, "r3": 8.65, "r4": 9.7, "r5": 12.36, "PWR": 0.5}, "8.35": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.58, "r1": 8.15, "r2": 8.25, "r3": 8.7, "r4": 9.76, "r5": 12.47, "PWR": 0.5}, "8.4": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.63, "r1": 8.19, "r2": 8.3, "r3": 8.75, "r4": 9.82, "r5": 12.58, "PWR": 0.5}, "8.45": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.68, "r1": 8.23, "r2": 8.34, "r3": 8.79, "r4": 9.89, "r5": 12.69, "PWR": 0.5}, "8.5": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.74, "r1": 8.27, "r2": 8.39, "r3": 8.84, "r4": 9.95, "r5": 12.8, "PWR": 0.5}, "8.55": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.79, "r1": 8.31, "r2": 8.43, "r3": 8.89, "r4": 10.01, "r5": 12.91, "PWR": 0.5}, "8.6": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.84, "r1": 8.35, "r2": 8.48, "r3": 8.94, "r4": 10.07, "r5": 13.02, "PWR": 0.5}},
"-0.75": {"7.2": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 7.39, "r1": 7.11, "r2": 7.22, "r3": 7.6, "r4": 8.38, "r5": 10.13, "PWR": 0.5}, "7.25": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 7.44, "r1": 7.15, "r2": 7.26, "r3": 7.65, "r4": 8.44, "r5": 10.23, "PWR": 0.5}, "7.3": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 7.5, "r1": 7.18, "r2": 7.31, "r3": 7.7, "r4": 8.5, "r5": 10.32, "PWR": 0.5}, "7.35": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 7.55, "r1": 7.22, "r2": 7.35, "r3": 7.75, "r4": 8.55, "r5": 10.42, "PWR": 0.5}, "7.4": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 7.61, "r1": 7.26, "r2": 7.4, "r3": 7.79, "r4": 8.61, "r5": 10.52, "PWR": 0.5}, "7.45": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 7.66, "r1": 7.3, "r2": 7.44, "r3": 7.84, "r4": 8.67, "r5": 10.61, "PWR": 0.5}, "7.5": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 7.71, "r1": 7.34, "r2": 7.49, "r3": 7.89, "r4": 8.73, "r5": 10.71, "PWR": 0.5}, "7.55": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 7.77, "r1": 7.38, "r2": 7.53, "r3": 7.93, "r4": 8.79, "r5": 10.81, "PWR": 0.5}, "7.6": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 7.82, "r1": 7.42, "r2": 7.58, "r3": 7.98, "r4": 8.85, "r5": 10.91, "PWR": 0.5}, "7.65": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 7.87, "r1": 7.46, "r2": 7.62, "r3": 8.03, "r4": 8.91, "r5": 11.01, "PWR": 0.5}, "7.7": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 7.93, "r1": 7.5, "r2": 7.67, "r3": 8.08, "r4": 8.97, "r5": 11.11, "PWR": 0.5}, "7.75": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 7.98, "r1": 7.53, "r2": 7.71, "r3": 8.13, "r4": 9.03, "r5": 11.21, "PWR": 0.5}, "7.8": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.04, "r1": 7.57, "r2": 7.76, "r3": 8.17, "r4": 9.09, "r5": 11.31, "PWR": 0.5}, "7.85": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.09, "r1": 7.61, "r2": 7.8, "r3": 8.22, "r4": 9.15, "r5": 11.41, "PWR": 0.5}, "7.9": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.14, "r1": 7.65, "r2": 7.85, "r3": 8.27, "r4": 9.21, "r5": 11.51, "PWR": 0.5}, "7.95": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.2, "r1": 7.69, "r2": 7.89, "r3": 8.32, "r4": 9.27, "r5": 11.62, "PWR": 0.5}, "8.0": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.25, "r1": 7.73, "r2": 7.94, "r3": 8.36, "r4": 9.33, "r5": 11.72, "PWR": 0.5}, "8.05": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.31, "r1": 7.77, "r2": 7.98, "r3": 8.41, "r4": 9.39, "r5": 11.83, "PWR": 0.5}, "8.1": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.36, "r1": 7.8, "r2": 8.03, "r3": 8.46, "r4": 9.45, "r5": 11.93, "PWR": 0.5}, "8.15": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.41, "r1": 7.84, "r2": 8.07, "r3": 8.51, "r4": 9.52, "r5": 12.04, "PWR": 0.5}, "8.2": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.47, "r1": 7.88, "r2": 8.12, "r3": 8.56, "r4": 9.58, "r5": 12.14, "PWR": 0.5}, "8.25": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.52, "r1": 7.92, "r2": 8.16, "r3": 8.6, "r4": 9.64, "r5": 12.25, "PWR": 0.5}, "8.3": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.58, "r1": 7.96, "r2": 8.21, "r3": 8.65, "r4": 9.7, "r5": 12.36, "PWR": 0.5}, "8.35": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.63, "r1": 8.0, "r2": 8.25, "r3": 8.7, "r4": 9.76, "r5": 12.47, "PWR": 0.5}, "8.4": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.68, "r1": 8.04, "r2": 8.3, "r3": 8.75, "r4": 9.82, "r5": 12.58, "PWR": 0.5}, "8.45": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.74, "r1": 8.07, "r2": 8.34, "r3": 8.79, "r4": 9.89, "r5": 12.69, "PWR": 0.5}, "8.5": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.79, "r1": 8.11, "r2": 8.39, "r3": 8.84, "r4": 9.95, "r5": 12.8, "PWR": 0.5}, "8.55": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.85, "r1": 8.15, "r2": 8.43, "r3": 8.89, "r4": 10.01, "r5": 12.91, "PWR": 0.5}, "8.6": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.9, "r1": 8.19, "r2": 8.48, "r3": 8.94, "r4": 10.07, "r5": 13.02, "PWR": 0.5}},
"-1.0": {"7.2": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 7.43, "r1": 7.0, "r2": 7.22, "r3": 7.6, "r4": 8.38, "r5": 10.13, "PWR": 0.5}, "7.25": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 7.49, "r1": 7.04, "r2": 7.26, "r3": 7.65, "r4": 8.44, "r5": 10.23, "PWR": 0.5}, "7.3": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 7.54, "r1": 7.07, "r2": 7.31, "r3": 7.7, "r4": 8.5, "r5": 10.32, "PWR": 0.5}, "7.35": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 7.59, "r1": 7.11, "r2": 7.35, "r3": 7.75, "r4": 8.55, "r5": 10.42, "PWR": 0.5}, "7.4": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 7.65, "r1": 7.15, "r2": 7.4, "r3": 7.79, "r4": 8.61, "r5": 10.52, "PWR": 0.5}, "7.45": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 7.7, "r1": 7.19, "r2": 7.44, "r3": 7.84, "r4": 8.67, "r5": 10.61, "PWR": 0.5}, "7.5": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 7.76, "r1": 7.22, "r2": 7.49, "r3": 7.89, "r4": 8.73, "r5": 10.71, "PWR": 0.5}, "7.55": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 7.81, "r1": 7.26, "r2": 7.53, "r3": 7.93, "r4": 8.79, "r5": 10.81, "PWR": 0.5}, "7.6": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 7.87, "r1": 7.3, "r2": 7.58, "r3": 7.98, "r4": 8.85, "r5": 10.91, "PWR": 0.5}, "7.65": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 7.92, "r1": 7.33, "r2": 7.62, "r3": 8.03, "r4": 8.91, "r5": 11.01, "PWR": 0.5}, "7.7": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 7.98, "r1": 7.37, "r2": 7.67, "r3": 8.08, "r4": 8.97, "r5": 11.11, "PWR": 0.5}, "7.75": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.03, "r1": 7.41, "r2": 7.71, "r3": 8.13, "r4": 9.03, "r5": 11.21, "PWR": 0.5}, "7.8": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.08, "r1": 7.45, "r2": 7.76, "r3": 8.17, "r4": 9.09, "r5": 11.31, "PWR": 0.5}, "7.85": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.14, "r1": 7.48, "r2": 7.8, "r3": 8.22, "r4": 9.15, "r5": 11.41, "PWR": 0.5}, "7.9": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.19, "r1": 7.52, "r2": 7.85, "r3": 8.27, "r4": 9.21, "r5": 11.51, "PWR": 0.5}, "7.95": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.25, "r1": 7.56, "r2": 7.89, "r3": 8.32, "r4": 9.27, "r5": 11.62, "PWR": 0.5}, "8.0": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.3, "r1": 7.6, "r2": 7.94, "r3": 8.36, "r4": 9.33, "r5": 11.72, "PWR": 0.5}, "8.05": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.36, "r1": 7.63, "r2": 7.98, "r3": 8.41, "r4": 9.39, "r5": 11.83, "PWR": 0.5}, "8.1": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.41, "r1": 7.67, "r2": 8.03, "r3": 8.46, "r4": 9.45, "r5": 11.93, "PWR": 0.5}, "8.15": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.47, "r1": 7.71, "r2": 8.07, "r3": 8.51, "r4": 9.52, "r5": 12.04, "PWR": 0.5}, "8.2": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.52, "r1": 7.74, "r2": 8.12, "r3": 8.56, "r4": 9.58, "r5": 12.14, "PWR": 0.5}, "8.25": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.58, "r1": 7.78, "r2": 8.16, "r3": 8.6, "r4": 9.64, "r5": 12.25, "PWR": 0.5}, "8.3": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.63, "r1": 7.82, "r2": 8.21, "r3": 8.65, "r4": 9.7, "r5": 12.36, "PWR": 0.5}, "8.35": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.69, "r1": 7.85, "r2": 8.25, "r3": 8.7, "r4": 9.76, "r5": 12.47, "PWR": 0.5}, "8.4": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.74, "r1": 7.89, "r2": 8.3, "r3": 8.75, "r4": 9.82, "r5": 12.58, "PWR": 0.5}, "8.45": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.8, "r1": 7.93, "r2": 8.34, "r3": 8.79, "r4": 9.89, "r5": 12.69, "PWR": 0.5}, "8.5": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.85, "r1": 7.96, "r2": 8.39, "r3": 8.84, "r4": 9.95, "r5": 12.8, "PWR": 0.5}, "8.55": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.91, "r1": 8.0, "r2": 8.43, "r3": 8.89, "r4": 10.01, "r5": 12.91, "PWR": 0.5}, "8.6": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.96, "r1": 8.04, "r2": 8.48, "r3": 8.94, "r4": 10.07, "r5": 13.02, "PWR": 0.5}},
"-1.25": {"7.2": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 7.47, "r1": 6.89, "r2": 7.22, "r3": 7.6, "r4": 8.38, "r5": 10.13, "PWR": 0.5}, "7.25": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 7.53, "r1": 6.93, "r2": 7.26, "r3": 7.65, "r4": 8.44, "r5": 10.23, "PWR": 0.5}, "7.3": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 7.58, "r1": 6.97, "r2": 7.31, "r3": 7.7, "r4": 8.5, "r5": 10.32, "PWR": 0.5}, "7.35": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 7.64, "r1": 7.0, "r2": 7.35, "r3": 7.75, "r4": 8.55, "r5": 10.42, "PWR": 0.5}, "7.4": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 7.69, "r1": 7.04, "r2": 7.4, "r3": 7.79, "r4": 8.61, "r5": 10.52, "PWR": 0.5}, "7.45": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 7.75, "r1": 7.08, "r2": 7.44, "r3": 7.84, "r4": 8.67, "r5": 10.61, "PWR": 0.5}, "7.5": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 7.8, "r1": 7.11, "r2": 7.49, "r3": 7.89, "r4": 8.73, "r5": 10.71, "PWR": 0.5}, "7.55": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 7.86, "r1": 7.15, "r2": 7.53, "r3": 7.93, "r4": 8.79, "r5": 10.81, "PWR": 0.5}, "7.6": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 7.91, "r1": 7.18, "r2": 7.58, "r3": 7.98, "r4": 8.85, "r5": 10.91, "PWR": 0.5}, "7.65": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 7.97, "r1": 7.22, "r2": 7.62, "r3": 8.03, "r4": 8.91, "r5": 11.01, "PWR": 0.5}, "7.7": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.02, "r1": 7.25, "r2": 7.67, "r3": 8.08, "r4": 8.97, "r5": 11.11, "PWR": 0.5}, "7.75": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.08, "r1": 7.29, "r2": 7.71, "r3": 8.13, "r4": 9.03, "r5": 11.21, "PWR": 0.5}, "7.8": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.13, "r1": 7.33, "r2": 7.76, "r3": 8.17, "r4": 9.09, "r5": 11.31, "PWR": 0.5}, "7.85": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.19, "r1": 7.36, "r2": 7.8, "r3": 8.22, "r4": 9.15, "r5": 11.41, "PWR": 0.5}, "7.9": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.24, "r1": 7.4, "r2": 7.85, "r3": 8.27, "r4": 9.21, "r5": 11.51, "PWR": 0.5}, "7.95": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.3, "r1": 7.43, "r2": 7.89, "r3": 8.32, "r4": 9.27, "r5": 11.62, "PWR": 0.5}, "8.0": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.35, "r1": 7.47, "r2": 7.94, "r3": 8.36, "r4": 9.33, "r5": 11.72, "PWR": 0.5}, "8.05": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.41, "r1": 7.5, "r2": 7.98, "r3": 8.41, "r4": 9.39, "r5": 11.83, "PWR": 0.5}, "8.1": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.46, "r1": 7.54, "r2": 8.03, "r3": 8.46, "r4": 9.45, "r5": 11.93, "PWR": 0.5}, "8.15": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.52, "r1": 7.58, "r2": 8.07, "r3": 8.51, "r4": 9.52, "r5": 12.04, "PWR": 0.5}, "8.2": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.58, "r1": 7.61, "r2": 8.12, "r3": 8.56, "r4": 9.58, "r5": 12.14, "PWR": 0.5}, "8.25": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.63, "r1": 7.65, "r2": 8.16, "r3": 8.6, "r4": 9.64, "r5": 12.25, "PWR": 0.5}, "8.3": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.69, "r1": 7.68, "r2": 8.21, "r3": 8.65, "r4": 9.7, "r5": 12.36, "PWR": 0.5}, "8.35": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.74, "r1": 7.72, "r2": 8.25, "r3": 8.7, "r4": 9.76, "r5": 12.47, "PWR": 0.5}, "8.4": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.8, "r1": 7.75, "r2": 8.3, "r3": 8.75, "r4": 9.82, "r5": 12.58, "PWR": 0.5}, "8.45": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.85, "r1": 7.79, "r2": 8.34, "r3": 8.79, "r4": 9.89, "r5": 12.69, "PWR": 0.5}, "8.5": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.91, "r1": 7.82, "r2": 8.39, "r3": 8.84, "r4": 9.95, "r5": 12.8, "PWR": 0.5}, "8.55": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.96, "r1": 7.86, "r2": 8.43, "r3": 8.89, "r4": 10.01, "r5": 12.91, "PWR": 0.5}, "8.6": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 9.02, "r1": 7.89, "r2": 8.48, "r3": 8.94, "r4": 10.07, "r5": 13.02, "PWR": 0.5}},
"-1.5": {"7.2": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 7.51, "r1": 6.8, "r2": 7.22, "r3": 7.6, "r4": 8.38, "r5": 10.13, "PWR": 0.5}, "7.6": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 7.96, "r1": 7.07, "r2": 7.58, "r3": 7.98, "r4": 8.85, "r5": 10.91, "PWR": 0.5}, "7.8": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.18, "r1": 7.21, "r2": 7.76, "r3": 8.17, "r4": 9.09, "r5": 11.31, "PWR": 0.5}, "8.0": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.41, "r1": 7.35, "r2": 7.94, "r3": 8.36, "r4": 9.33, "r5": 11.72, "PWR": 0.5}, "8.2": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.63, "r1": 7.48, "r2": 8.12, "r3": 8.56, "r4": 9.58, "r5": 12.14, "PWR": 0.5}, "8.4": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.86, "r1": 7.62, "r2": 8.3, "r3": 8.75, "r4": 9.82, "r5": 12.58, "PWR": 0.5}, "8.6": {"BOZD": 6.4, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 9.08, "r1": 7.76, "r2": 8.48, "r3": 8.94, "r4": 10.07, "r5": 13.02, "PWR": 0.5}},
"-2.0": {"7.2": {"BOZD": 6.2, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 7.6, "r1": 6.76, "r2": 7.22, "r3": 7.6, "r4": 8.38, "r5": 10.13, "PWR": 0.5}, "7.6": {"BOZD": 6.2, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.05, "r1": 7.05, "r2": 7.58, "r3": 7.98, "r4": 8.85, "r5": 10.91, "PWR": 0.5}, "7.8": {"BOZD": 6.2, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.28, "r1": 7.19, "r2": 7.76, "r3": 8.17, "r4": 9.09, "r5": 11.31, "PWR": 0.5}, "8.0": {"BOZD": 6.2, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.51, "r1": 7.33, "r2": 7.94, "r3": 8.36, "r4": 9.33, "r5": 11.72, "PWR": 0.5}, "8.2": {"BOZD": 6.2, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.74, "r1": 7.47, "r2": 8.12, "r3": 8.56, "r4": 9.58, "r5": 12.14, "PWR": 0.5}, "8.4": {"BOZD": 6.2, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.97, "r1": 7.61, "r2": 8.3, "r3": 8.75, "r4": 9.82, "r5": 12.58, "PWR": 0.5}, "8.6": {"BOZD": 6.2, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 9.2, "r1": 7.75, "r2": 8.48, "r3": 8.94, "r4": 10.07, "r5": 13.02, "PWR": 0.5}},
"-3.0": {"7.2": {"BOZD": 6.0, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 7.77, "r1": 6.64, "r2": 7.22, "r3": 7.6, "r4": 8.38, "r5": 10.13, "PWR": 0.5}, "7.6": {"BOZD": 6.0, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.25, "r1": 6.92, "r2": 7.58, "r3": 7.98, "r4": 8.85, "r5": 10.91, "PWR": 0.5}, "7.8": {"BOZD": 6.0, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.49, "r1": 7.05, "r2": 7.76, "r3": 8.17, "r4": 9.09, "r5": 11.31, "PWR": 0.5}, "8.0": {"BOZD": 6.0, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.73, "r1": 7.19, "r2": 7.94, "r3": 8.36, "r4": 9.33, "r5": 11.72, "PWR": 0.5}, "8.2": {"BOZD": 6.0, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.97, "r1": 7.33, "r2": 8.12, "r3": 8.56, "r4": 9.58, "r5": 12.14, "PWR": 0.5}, "8.4": {"BOZD": 6.0, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 9.22, "r1": 7.46, "r2": 8.3, "r3": 8.75, "r4": 9.82, "r5": 12.58, "PWR": 0.5}, "8.6": {"BOZD": 6.0, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 9.46, "r1": 7.6, "r2": 8.48, "r3": 8.94, "r4": 10.07, "r5": 13.02, "PWR": 0.5}},
"-4.0": {"7.2": {"BOZD": 5.8, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 7.96, "r1": 6.57, "r2": 7.22, "r3": 7.6, "r4": 8.38, "r5": 10.13, "PWR": 0.5}, "7.6": {"BOZD": 5.8, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.46, "r1": 6.85, "r2": 7.58, "r3": 7.98, "r4": 8.85, "r5": 10.91, "PWR": 0.5}, "7.8": {"BOZD": 5.8, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.71, "r1": 6.98, "r2": 7.76, "r3": 8.17, "r4": 9.09, "r5": 11.31, "PWR": 0.5}, "8.0": {"BOZD": 5.8, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.96, "r1": 7.12, "r2": 7.94, "r3": 8.36, "r4": 9.33, "r5": 11.72, "PWR": 0.5}, "8.2": {"BOZD": 5.8, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 9.22, "r1": 7.26, "r2": 8.12, "r3": 8.56, "r4": 9.58, "r5": 12.14, "PWR": 0.5}, "8.4": {"BOZD": 5.8, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 9.48, "r1": 7.39, "r2": 8.3, "r3": 8.75, "r4": 9.82, "r5": 12.58, "PWR": 0.5}, "8.6": {"BOZD": 5.8, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 9.74, "r1": 7.52, "r2": 8.48, "r3": 8.94, "r4": 10.07, "r5": 13.02, "PWR": 0.5}},
"-5.0": {"7.2": {"BOZD": 5.6, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.15, "r1": 6.54, "r2": 7.22, "r3": 7.6, "r4": 8.38, "r5": 10.13, "PWR": 0.5}, "7.6": {"BOZD": 5.6, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.67, "r1": 6.81, "r2": 7.58, "r3": 7.98, "r4": 8.85, "r5": 10.91, "PWR": 0.5}, "7.8": {"BOZD": 5.6, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 8.94, "r1": 6.95, "r2": 7.76, "r3": 8.17, "r4": 9.09, "r5": 11.31, "PWR": 0.5}, "8.0": {"BOZD": 5.6, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 9.21, "r1": 7.09, "r2": 7.94, "r3": 8.36, "r4": 9.33, "r5": 11.72, "PWR": 0.5}, "8.2": {"BOZD": 5.6, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 9.48, "r1": 7.22, "r2": 8.12, "r3": 8.56, "r4": 9.58, "r5": 12.14, "PWR": 0.5}, "8.4": {"BOZD": 5.6, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 9.75, "r1": 7.36, "r2": 8.3, "r3": 8.75, "r4": 9.82, "r5": 12.58, "PWR": 0.5}, "8.6": {"BOZD": 5.6, "d1": 7.2, "d2": 8.2, "d3": 9.6, "d4": 10.0, "TD": 10.8, "r0": 10.03, "r1": 7.49, "r2": 8.48, "r3": 8.94, "r4": 10.07, "r5": 13.02, "PWR": 0.5}}
}

# Miopie e K disponibili nel file completo
MIOPIE_DISPONIBILI = [-0.5, -0.75, -1.0, -1.25, -1.5, -1.75, -2.0, -2.25,
                      -2.5, -2.75, -3.0, -3.25, -3.5, -3.75, -4.0, -4.25,
                      -4.5, -4.75, -5.0]
K_DISPONIBILI = [7.20, 7.25, 7.30, 7.35, 7.40, 7.45, 7.50, 7.55, 7.60, 7.65,
                 7.70, 7.75, 7.80, 7.85, 7.90, 7.95, 8.00, 8.05, 8.10, 8.15,
                 8.20, 8.25, 8.30, 8.35, 8.40, 8.45, 8.50, 8.55, 8.60]


# ---------------------------------------------------------------------------
# Helpers DB / interpolazione
# ---------------------------------------------------------------------------

def _is_postgres(conn):
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
    mark = "%s" if _is_postgres(conn) else "?"
    return ", ".join([mark] * n)

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
    conn = sqlite3.connect("organism.db"); conn.row_factory = sqlite3.Row; return conn

def _row_get(row, key, default=None):
    try:
        v = row[key]; return v if v is not None else default
    except Exception:
        try: return row.get(key, default)
        except: return default

def _today_str(): return date.today().strftime("%d/%m/%Y")
def _parse_date(s):
    for fmt in ("%d/%m/%Y","%Y-%m-%d","%d-%m-%Y"):
        try: return datetime.strptime((s or "").strip(),fmt).strftime("%Y-%m-%d")
        except: pass
    return ""


def _lookup_esa(K_mm: float, miopia_D: float) -> dict | None:
    """Cerca il record esatto o interpola bilinearmente."""
    def _key_m(m): return str(round(m, 2))
    def _key_k(k): return str(round(k, 2))

    # trova K e miopia vicini
    K_vals  = sorted(K_DISPONIBILI, key=lambda x: abs(x - K_mm))
    m_vals  = sorted(MIOPIE_DISPONIBILI, key=lambda x: abs(x - miopia_D))

    # lookup esatta
    mk = _key_m(miopia_D)
    kk = _key_k(K_mm)
    if mk in ESA_DB_RAW and kk in ESA_DB_RAW[mk]:
        r = ESA_DB_RAW[mk][kk].copy()
        r["interpolato"] = False
        return r

    # interpolazione bilineare sui 4 angoli più vicini
    K_sorted  = sorted(K_DISPONIBILI)
    m_sorted  = sorted(MIOPIE_DISPONIBILI)

    k_lo = max([k for k in K_sorted if k <= K_mm], default=K_sorted[0])
    k_hi = min([k for k in K_sorted if k >= K_mm], default=K_sorted[-1])
    m_lo = max([m for m in m_sorted if m >= miopia_D], default=m_sorted[0])
    m_hi = min([m for m in m_sorted if m <= miopia_D], default=m_sorted[-1])

    def _get(m, k):
        return ESA_DB_RAW.get(_key_m(m), {}).get(_key_k(k))

    # raccoglie i 4 angoli disponibili
    corners = {}
    for m in ([m_lo] if m_lo == m_hi else [m_lo, m_hi]):
        for k in ([k_lo] if k_lo == k_hi else [k_lo, k_hi]):
            d = _get(m, k)
            if d: corners[(m, k)] = d

    if not corners:
        # usa il più vicino disponibile
        best = None; best_d = 999
        for mk2 in ESA_DB_RAW:
            for kk2 in ESA_DB_RAW[mk2]:
                d = abs(float(mk2)-miopia_D) + abs(float(kk2)-K_mm)
                if d < best_d:
                    best_d = d; best = ESA_DB_RAW[mk2][kk2]
        if best:
            r = best.copy(); r["interpolato"] = True; r["avviso"] = "Valore più vicino disponibile"
            return r
        return None

    if len(corners) == 1:
        r = list(corners.values())[0].copy()
        r["interpolato"] = False; return r

    # interpolazione sui campi numerici
    fields = ["BOZD","d1","d2","d3","d4","TD","r0","r1","r2","r3","r4","r5","PWR"]
    result = {}
    total_w = 0
    for (m, k), data in corners.items():
        w = 1.0 / (abs(m - miopia_D) + abs(k - K_mm) + 1e-9)
        total_w += w
        for f in fields:
            result[f] = result.get(f, 0) + data.get(f, 0) * w
    for f in fields:
        result[f] = round(result[f] / total_w, 2)
    result["interpolato"] = True
    return result


def _profilo_cornea_sferica(K_mm, y_max, n=60):
    ys, zs = [], []
    for i in range(n+1):
        y = y_max * i / n
        z = K_mm - math.sqrt(max(K_mm**2 - y**2, 0))
        ys.append(round(y,3)); zs.append(round(z,4))
    return ys, zs

def _profilo_lente_esa(res, y_max, n=60):
    """Profilo sagittale dalla lente ESA a zone sferiche."""
    # zone: [0, BOZD/2] r0; [BOZD/2, d1/2] r1; ... ecc
    zones = [
        (res["BOZD"]/2, res["r0"]),
        (res["d1"]/2,   res["r1"]),
        (res["d2"]/2,   res["r2"]),
        (res["d3"]/2,   res["r3"]),
        (res["d4"]/2,   res["r4"]),
        (res["TD"]/2,   res["r5"]),
    ]
    ys, zs = [0.0], [0.0]
    z_acc = 0.0
    prev_y = 0.0
    for (y_bord, r) in zones:
        for i in range(1, 11):
            y = prev_y + (y_bord - prev_y) * i / 10
            if y > y_max: break
            dy = y - prev_y
            delta_z = r - math.sqrt(max(r**2 - dy**2, 0))
            ys.append(round(y, 3))
            zs.append(round(z_acc + delta_z, 4))
        z_acc += zones[zones.index((y_bord,r))][1] - math.sqrt(
            max(zones[zones.index((y_bord,r))][1]**2 - (y_bord-prev_y)**2, 0))
        prev_y = y_bord
    return ys, zs


# ---------------------------------------------------------------------------
# UI principale
# ---------------------------------------------------------------------------

def ui_esa_ortho6():
    st.header("ESA Ortho-6 – Serie 002")
    st.caption("Assortimento precalcolato · A. Calossi 2003 · 551 combinazioni K×Miopia")

    conn = _get_conn()
    cur  = conn.cursor()

    # Seleziona paziente
    try:
        cur.execute('SELECT id, "Cognome", "Nome" FROM "Pazienti" ORDER BY "Cognome", "Nome"')
        pazienti = cur.fetchall()
    except Exception:
        try:
            cur.execute("SELECT id, Cognome, Nome FROM Pazienti ORDER BY Cognome, Nome")
            pazienti = cur.fetchall()
        except Exception:
            pazienti = []

    paz_options = ["— nessuno —"] + [
        f"{_row_get(p,'id')} - {_row_get(p,'Cognome','')} {_row_get(p,'Nome','')}".strip()
        for p in pazienti]
    sel_paz = st.selectbox("Paziente (opzionale, per salvare)", paz_options, key="esa_paz")
    paz_id  = None if sel_paz.startswith("—") else int(sel_paz.split(" - ")[0])

    st.divider()
    tab_calc, tab_tabella, tab_confronto = st.tabs([
        "Ricerca e Calcolo", "Tabella assortimento", "Confronto varianti"])

    with tab_calc:    _ui_calcolo(conn, cur, paz_id)
    with tab_tabella: _ui_tabella()
    with tab_confronto: _ui_confronto()


def _ui_calcolo(conn, cur, paz_id):
    st.subheader("Ricerca parametri ESA")

    col1, col2, col3 = st.columns(3)
    with col1:
        occhio  = st.selectbox("Occhio", ["OD","OS"], key="esa_occhio")
        K_input = st.number_input("K corneale (mm)", 7.20, 8.60, 7.60, 0.01,
                                   format="%.2f", key="esa_K",
                                   help="K flat dal topografo o dalla cheratometria")
        st.caption(f"K = {r_to_d(K_input):.2f} D")
    with col2:
        miopia  = st.number_input("Miopia da correggere (D)", -5.0, -0.5, -3.0, 0.25,
                                   key="esa_mio",
                                   help="Valore negativo, es. -3.00")
        k_steep = st.number_input("K steep (mm) – opzionale", 7.0, 9.0, 7.60, 0.01,
                                   format="%.2f", key="esa_kst",
                                   help="Solo per calcolo astigmatismo (uguale a K flat se non astigmatico)")
    with col3:
        materiale = st.text_input("Materiale lente", "Boston XO", key="esa_mat")
        dk        = st.number_input("DK", 0.0, 200.0, 100.0, 1.0, key="esa_dk")

    cerca = st.button("Cerca parametri ESA", type="primary", key="btn_esa")

    if cerca:
        res = _lookup_esa(K_input, miopia)
        if not res:
            st.error("Nessun dato trovato per questi parametri.")
            return
        st.session_state["esa_result"] = res
        st.session_state["esa_K_save"] = K_input
        st.session_state["esa_mio_save"] = miopia
        st.session_state["esa_kst_save"] = k_steep
        st.session_state["esa_occhio_save"] = occhio

    if "esa_result" in st.session_state:
        res = st.session_state["esa_result"]
        _mostra_risultato_esa(res, conn, cur, paz_id, materiale, dk)


def _mostra_risultato_esa(res, conn, cur, paz_id, materiale, dk):
    interp = res.get("interpolato", False)
    if interp:
        st.warning("Valori interpolati (K o miopia fuori dai passi standard 0.05/0.25)")
    else:
        st.success("Parametri trovati in tabella ESA")

    st.markdown("### Parametri lente")
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("BOZR r₀ (mm)", f"{res['r0']:.2f}", 
              delta=f"= {r_to_d(res['r0']):.2f} D")
    c2.metric("BOZD Ø₀ (mm)", f"{res['BOZD']:.1f}")
    c3.metric("Diam. totale (mm)", f"{res['TD']:.1f}")
    c4.metric("Potere (D)", f"{res['PWR']:+.2f}")

    st.markdown("### Zone e raggi")
    zone_data = [
        {"Zona": "Zona Ottica (BOZR)", "Raggio (mm)": res["r0"], "Ø bordo (mm)": res["BOZD"]},
        {"Zona": "I Flangia (r1)",     "Raggio (mm)": res["r1"], "Ø bordo (mm)": res["d1"]},
        {"Zona": "II Flangia (r2)",    "Raggio (mm)": res["r2"], "Ø bordo (mm)": res["d2"]},
        {"Zona": "III Flangia (r3)",   "Raggio (mm)": res["r3"], "Ø bordo (mm)": res["d3"]},
        {"Zona": "IV Flangia (r4)",    "Raggio (mm)": res["r4"], "Ø bordo (mm)": res["d4"]},
        {"Zona": "V Flangia (r5)",     "Raggio (mm)": res["r5"], "Ø bordo (mm)": res["TD"]},
    ]
    st.dataframe(pd.DataFrame(zone_data), use_container_width=True, hide_index=True)

    # Astigmatismo corneale
    K_val  = st.session_state.get("esa_K_save", 7.6)
    K_st   = st.session_state.get("esa_kst_save", 0.0) or 0.0
    if K_st and K_st != K_val and K_st > 6.5:
        ast_D = abs(337.5/K_val - 337.5/K_st)
        if ast_D > 0.01:
            st.info(f"Astigmatismo corneale stimato: **{ast_D:.2f} D** (K flat {K_val:.2f} – K steep {K_st:.2f} mm)")

    # Schema per laboratorio
    st.markdown("### Schema per il laboratorio")
    K_val_d = round(337.5 / K_val, 2) if K_val else 0
    schema = (
        f"═══════════════════════════════════════\n"
        f"  ESA Ortho-6 Serie 002\n"
        f"  K={K_val:.2f} mm ({K_val_d:.2f} D)   Miopia={st.session_state.get('esa_mio_save', '?')} D\n"
        f"═══════════════════════════════════════\n"
        f"  BOZR (r0): {res['r0']:.2f} mm\n"
        f"  BOZD (Ø0): {res['BOZD']:.1f} mm\n"
        f"───────────────────────────────────────\n"
        f"  r1={res['r1']:.2f}  Ø1={res['d1']:.1f} mm\n"
        f"  r2={res['r2']:.2f}  Ø2={res['d2']:.1f} mm\n"
        f"  r3={res['r3']:.2f}  Ø3={res['d3']:.1f} mm\n"
        f"  r4={res['r4']:.2f}  Ø4={res['d4']:.1f} mm\n"
        f"  r5={res['r5']:.2f}  ØT={res['TD']:.1f} mm\n"
        f"───────────────────────────────────────\n"
        f"  Potere: {res['PWR']:+.2f} D   Materiale: {materiale}\n"
        f"═══════════════════════════════════════\n"
    )
    st.code(schema, language=None)

    # Profilo sagittale
    st.markdown("### Profilo sagittale – Cornea vs ESA")
    y_max = res["TD"] / 2
    ys_c, zs_c = _profilo_cornea_sferica(K_val, y_max)
    # profilo lente (approssimazione a zone)
    ys_l = []
    zs_l = []
    zones = [
        (0,              res["BOZD"]/2, res["r0"]),
        (res["BOZD"]/2,  res["d1"]/2,  res["r1"]),
        (res["d1"]/2,    res["d2"]/2,  res["r2"]),
        (res["d2"]/2,    res["d3"]/2,  res["r3"]),
        (res["d3"]/2,    res["d4"]/2,  res["r4"]),
        (res["d4"]/2,    res["TD"]/2,  res["r5"]),
    ]
    z_acc = 0.0
    for (y_in, y_out, r) in zones:
        for i in range(11):
            y = y_in + (y_out - y_in) * i / 10
            if y > y_max + 0.01: break
            dy = y - y_in
            z = z_acc + (r - math.sqrt(max(r**2 - dy**2, 0.0)))
            ys_l.append(round(y, 3))
            zs_l.append(round(z, 4))
        dy_tot = y_out - y_in
        z_acc += r - math.sqrt(max(r**2 - dy_tot**2, 0.0))

    # interpolazione ys_l su ys_c
    ys_arr = np.array(ys_c)
    zs_c_arr = np.array(zs_c)
    zs_l_interp = np.interp(ys_arr, ys_l, zs_l)
    clearance_um = [(zl - zc)*1000 for zc, zl in zip(zs_c_arr, zs_l_interp)]

    df_plot = pd.DataFrame({
        "y (mm)": ys_c,
        "Cornea (mm)": zs_c,
        "ESA lente (mm)": list(zs_l_interp),
        "Clearance µm": [round(c,1) for c in clearance_um],
    })

    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.markdown("**Profilo sagittale**")
        st.line_chart(df_plot.set_index("y (mm)")[["Cornea (mm)","ESA lente (mm)"]])
    with col_g2:
        st.markdown("**Clearance (µm)**")
        st.line_chart(df_plot.set_index("y (mm)")[["Clearance µm"]])

    # Metriche clearance
    cm1,cm2,cm3 = st.columns(3)
    cm1.metric("Clearance centrale (µm)", f"{clearance_um[0]:.0f}")
    idx_zo = min(range(len(ys_c)), key=lambda i: abs(ys_c[i] - res["BOZD"]/2))
    cm2.metric(f"Clearance bordo ZO (y={res['BOZD']/2:.1f}mm)", f"{clearance_um[idx_zo]:.0f}")
    cm3.metric("Clearance al bordo TD", f"{clearance_um[-1]:.0f}")

    # Salvataggio
    if paz_id:
        st.divider()
        st.markdown("#### Salva in scheda Lenti Inverse")
        occhio_sal = st.session_state.get("esa_occhio_save", "OD")
        note_sal   = st.text_area("Note", "", key="esa_note_sal")
        if st.button("Salva parametri ESA nella scheda paziente", key="btn_esa_salva"):
            _salva_esa_in_lenti_inverse(conn, cur, paz_id, occhio_sal, res,
                                        K_val, materiale, dk, note_sal,
                                        st.session_state.get("esa_mio_save", 0.0))


def _salva_esa_in_lenti_inverse(conn, cur, paz_id, occhio, res, K_mm, materiale, dk, note, miopia):
    try:
        from modules.ui_lenti_inverse import init_lenti_inverse_db
        init_lenti_inverse_db(conn)
    except Exception:
        pass
    now_iso     = datetime.now().isoformat(timespec="seconds")
    CK          = 337.5
    flange_json = json.dumps([
        {"nome": "I Flangia",  "raggio_mm": res["r1"], "diottrie": round(CK/res["r1"],2), "ampiezza_mm": round((res["d1"]-res["BOZD"])/2,1), "diametro_mm": res["d1"]},
        {"nome": "II Flangia", "raggio_mm": res["r2"], "diottrie": round(CK/res["r2"],2), "ampiezza_mm": round((res["d2"]-res["d1"])/2,1),   "diametro_mm": res["d2"]},
        {"nome": "III Flangia","raggio_mm": res["r3"], "diottrie": round(CK/res["r3"],2), "ampiezza_mm": round((res["d3"]-res["d2"])/2,1),   "diametro_mm": res["d3"]},
        {"nome": "IV Flangia", "raggio_mm": res["r4"], "diottrie": round(CK/res["r4"],2), "ampiezza_mm": round((res["d4"]-res["d3"])/2,1),   "diametro_mm": res["d4"]},
        {"nome": "V Flangia",  "raggio_mm": res["r5"], "diottrie": round(CK/res["r5"],2), "ampiezza_mm": round((res["TD"]-res["d4"])/2,1),   "diametro_mm": res["TD"]},
    ], ensure_ascii=False)
    params = (
        paz_id, occhio, date.today().isoformat(),
        K_mm, round(CK/K_mm,2), 0.0, 0.0,
        0.0, K_mm, 0.0, 0.0, "ESA Ortho-6 Serie 002", "", "[]",
        0.0, 0.0, 0, miopia, miopia, "", "",
        "Sferica", K_mm, res["r0"], 0.0, 0.0, 0.0,
        res["BOZD"], 0.0,
        0.005, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
        flange_json, res["TD"], res["PWR"],
        materiale, dk, 0, f"ESA Ortho-6 Serie 002 | {note}",
        "", "", 0.0, 0.0, "", "", 0.0, "", "", "", "", "",
        now_iso, now_iso,
    )
    ph = _ph(len(params), conn)
    sql = (
        "INSERT INTO lenti_inverse (paziente_id,occhio,data_scheda,"
        "topo_k_flat_mm,topo_k_flat_d,topo_k_steep_mm,topo_k_steep_d,"
        "topo_ecc_media,topo_raggio_apicale_mm,topo_dev_std_raggio,topo_dev_std_ecc,"
        "topo_topografo,topo_data,topo_misurazioni_json,"
        "rx_sfera,rx_cilindro,rx_asse,rx_miopia_tot,rx_miopia_ridurre,rx_avsc,rx_avcc,"
        "lente_tipo_zo,lente_r0_mm,lente_rb_mm,lente_ecc_zo,lente_fattore_p,"
        "lente_fattore_appiatt,lente_zo_diam_mm,lente_clearance_mm,"
        "lente_c0,lente_c1,lente_c2,lente_c3,lente_c4,lente_c5,lente_c6,"
        "lente_flange_json,lente_diam_tot_mm,lente_potere_d,"
        "lente_materiale,lente_dk,lente_puntino,lente_note,"
        "app_data,app_tipo,app_clearance_centrale,app_clearance_periferica,"
        "app_pattern,app_centratura,app_movimento_mm,app_valutazione,"
        "app_modifiche,app_operatore,app_note_fluoresceina,app_note,"
        f"created_at,updated_at) VALUES ({ph})"
    )
    try:
        cur.execute(sql, params); conn.commit()
        st.success("Parametri ESA salvati nella scheda Lenti Inverse.")
    except Exception as e:
        st.error(f"Errore: {e}")


def _ui_tabella():
    st.subheader("Tabella assortimento completa")
    st.caption("Filtra per K e miopia per vedere i parametri disponibili")

    col1, col2 = st.columns(2)
    with col1:
        k_range = st.slider("K corneale (mm)", 7.20, 8.60, (7.50, 7.80), 0.05, key="tab_k")
    with col2:
        m_range = st.slider("Miopia (D)", -5.0, -0.5, (-3.0, -1.0), 0.25, key="tab_m")

    rows = []
    for mk_str, kdict in ESA_DB_RAW.items():
        m = float(mk_str)
        if not (m_range[0] <= m <= m_range[1]): continue
        for kk_str, data in kdict.items():
            k = float(kk_str)
            if not (k_range[0] <= k <= k_range[1]): continue
            rows.append({
                "K (mm)": k, "Miopia (D)": m,
                "BOZD (mm)": data["BOZD"],
                "BOZR r0 (mm)": data["r0"],
                "r1 (mm)": data["r1"], "r2 (mm)": data["r2"],
                "r3 (mm)": data["r3"], "r4 (mm)": data["r4"],
                "r5 (mm)": data["r5"],
                "TD (mm)": data["TD"], "PWR (D)": data["PWR"],
            })

    if rows:
        df = pd.DataFrame(rows).sort_values(["K (mm)","Miopia (D)"])
        st.dataframe(df, use_container_width=True, hide_index=True)
        buf = io.StringIO(); df.to_csv(buf, index=False)
        st.download_button("Esporta CSV", buf.getvalue().encode(), "esa_tabella.csv", "text/csv", key="dl_tab")
    else:
        st.info("Nessun dato per i filtri selezionati.")


def _ui_confronto():
    st.subheader("Confronto varianti per stesso K")
    K_conf = st.number_input("K corneale fisso (mm)", 7.20, 8.60, 7.60, 0.05,
                              format="%.2f", key="conf_K")
    st.markdown("Confronto al variare della miopia:")
    rows = []
    for m in MIOPIE_DISPONIBILI:
        res = _lookup_esa(K_conf, m)
        if res:
            rows.append({
                "Miopia (D)": m, "BOZR r0": res["r0"], "BOZD": res["BOZD"],
                "r1": res["r1"], "r2": res["r2"], "r3": res["r3"],
                "r4": res["r4"], "r5": res["r5"], "TD": res["TD"],
            })
    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.markdown("**BOZR r₀ al variare della miopia (K fisso)**")
        st.line_chart(df.set_index("Miopia (D)")[["BOZR r0","r1","r2"]])
