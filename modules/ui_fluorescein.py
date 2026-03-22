# -*- coding: utf-8 -*-
"""
Modulo: Simulazione Fluoresceinogramma LAC Inversa
Gestionale The Organism – PNEV

Genera due visualizzazioni:
  1. Vista frontale – mappa colori clearance (tipo topografo)
  2. Sezione sagittale – profilo cornea/lente con clearance colorata

Design supportati:
  - Miopia (Inversa 6 / ESA)
  - Ipermetropia (steep-flat-steep)
  - Astigmatismo (torico)
  - Presbiopia (multifocale Q)

Scala colori fluorescein standard (lampada a fessura con filtro cobalto):
  Nero/verde scuro   → contatto / compressione
  Verde scuro        → clearance minima  (0–20 µm)
  Verde brillante    → clearance lieve   (20–80 µm)
  Verde chiaro/giallo→ clearance media   (80–200 µm)
  Giallo             → clearance alta    (200–400 µm)
  Arancione          → clearance eccessiva (>400 µm)
"""

import math
import io
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
try:
    from scipy.ndimage import gaussian_filter
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False
from matplotlib.patches import Circle
import streamlit as st

CK = 337.5


# ─────────────────────────────────────────────────────────────────────────────
# Geometria sagittale
# ─────────────────────────────────────────────────────────────────────────────

def sag_sph(r: float, y: float) -> float:
    v = r*r - y*y
    return r - math.sqrt(v) if v >= 0 else float('nan')

def sag_asp(r: float, e: float, y: float) -> float:
    p = 1 - e*e
    if p <= 0: return sag_sph(r, y)
    rp = r / p
    v  = rp*rp - y*y/p
    return rp - math.sqrt(v) if v >= 0 else float('nan')

def sag_Q(r: float, Q: float, y: float) -> float:
    e = math.sqrt(-Q) if Q < 0 else 0.0
    return sag_asp(r, e, y)


# ─────────────────────────────────────────────────────────────────────────────
# Definizione zone lente per design
# ─────────────────────────────────────────────────────────────────────────────

def get_zones(design: str, r0: float, rb: float, zo: float,
              e: float, ast_D: float = 0.0, Q_presb: float = -0.45,
              td: float = 10.8) -> list[dict]:
    """
    Ritorna lista di zone con:
      r, from_y, to_y, label, tipo ('sph'|'asp'|'Q'), parametro (e o Q)
    """
    td2 = td / 2
    zo2 = zo / 2

    if design == "mio":
        return [
            {"r": rb,           "from": 0,       "to": zo2,      "label": "ZO",    "tipo": "sph"},
            {"r": rb * 0.78,    "from": zo2,     "to": zo2+0.8,  "label": "Inv",   "tipo": "sph"},
            {"r": r0 * 1.05,    "from": zo2+0.8, "to": zo2+1.5,  "label": "Ali1",  "tipo": "sph"},
            {"r": r0 * 1.18,    "from": zo2+1.5, "to": zo2+2.2,  "label": "Ali2",  "tipo": "sph"},
            {"r": r0 * 1.32,    "from": zo2+2.2, "to": zo2+2.8,  "label": "Ali3",  "tipo": "sph"},
            {"r": r0 * 1.55,    "from": zo2+2.8, "to": td2,      "label": "Bordo", "tipo": "sph"},
        ]
    elif design == "iper":
        return [
            {"r": rb,           "from": 0,       "to": zo2,      "label": "ZO",      "tipo": "sph"},
            {"r": r0 * 1.18,    "from": zo2,     "to": zo2+1.0,  "label": "Plateau", "tipo": "sph"},
            {"r": rb * 0.82,    "from": zo2+1.0, "to": zo2+1.6,  "label": "Rev",     "tipo": "sph"},
            {"r": r0 * 1.10,    "from": zo2+1.6, "to": zo2+2.3,  "label": "Ali1",    "tipo": "sph"},
            {"r": r0 * 1.28,    "from": zo2+2.3, "to": zo2+2.9,  "label": "Ali2",    "tipo": "sph"},
            {"r": r0 * 1.50,    "from": zo2+2.9, "to": td2,      "label": "Bordo",   "tipo": "sph"},
        ]
    elif design == "ast":
        r_steep = CK / (CK/r0 + ast_D * 0.5) if ast_D > 0 else r0
        return [
            {"r": rb,           "from": 0,       "to": zo2,      "label": "ZO",    "tipo": "sph",
             "r_steep": rb * (r_steep/r0)},
            {"r": rb * 0.80,    "from": zo2,     "to": zo2+0.7,  "label": "Inv",   "tipo": "sph",
             "r_steep": rb * 0.80 * (r_steep/r0)},
            {"r": r0 * 1.06,    "from": zo2+0.7, "to": zo2+1.4,  "label": "Ali1",  "tipo": "sph"},
            {"r": r0 * 1.20,    "from": zo2+1.4, "to": zo2+2.1,  "label": "Ali2",  "tipo": "sph"},
            {"r": r0 * 1.38,    "from": zo2+2.1, "to": zo2+2.7,  "label": "Ali3",  "tipo": "sph"},
            {"r": r0 * 1.58,    "from": zo2+2.7, "to": td2,      "label": "Bordo", "tipo": "sph"},
        ]
    else:  # presb
        return [
            {"r": rb,           "from": 0,       "to": zo2,      "label": "ZO asf", "tipo": "Q", "Q": Q_presb},
            {"r": r0 * 1.14,    "from": zo2,     "to": zo2+0.6,  "label": "Trans",  "tipo": "sph"},
            {"r": rb * 0.86,    "from": zo2+0.6, "to": zo2+1.3,  "label": "Rev",    "tipo": "sph"},
            {"r": r0 * 1.12,    "from": zo2+1.3, "to": zo2+2.0,  "label": "Ali1",   "tipo": "sph"},
            {"r": r0 * 1.30,    "from": zo2+2.0, "to": zo2+2.6,  "label": "Ali2",   "tipo": "sph"},
            {"r": r0 * 1.52,    "from": zo2+2.6, "to": td2,      "label": "Bordo",  "tipo": "sph"},
        ]


def get_zone_at(y: float, zones: list) -> dict:
    for z in zones:
        if z["from"] <= y <= z["to"]:
            return z
    return zones[-1]


def clearance_um(y: float, theta: float, zone: dict,
                 r0: float, e: float, design: str, ast_D: float) -> float:
    """Clearance in µm tra cornea e lente alla posizione (y, theta)."""
    # Cornea: asferica, eventualmente torica
    r0_use, e_use = r0, e
    if design == "ast" and ast_D > 0:
        r_steep = CK / (CK/r0 + ast_D * 0.5)
        e_steep = e * 1.05
        t = abs(math.sin(theta))
        r0_use = r0 + (r_steep - r0) * t
        e_use  = e  + (e_steep - e) * t

    sag_c = sag_asp(r0_use, e_use, y)
    if math.isnan(sag_c):
        return float('nan')

    # Lente
    if zone["tipo"] == "Q":
        sag_l = sag_Q(zone["r"], zone["Q"], y)
    elif zone["tipo"] == "asp":
        sag_l = sag_asp(zone["r"], zone.get("e_zone", 0), y)
    else:
        # Torico: interpola tra flat e steep
        if "r_steep" in zone and ast_D > 0:
            t = abs(math.sin(theta))
            r_use = zone["r"] + (zone["r_steep"] - zone["r"]) * t
            sag_l = sag_sph(r_use, y)
        else:
            sag_l = sag_sph(zone["r"], y)

    return (sag_c - sag_l) * 1000 if not math.isnan(sag_l) else float('nan')


# ─────────────────────────────────────────────────────────────────────────────
# Colormap fluorescein
# ─────────────────────────────────────────────────────────────────────────────

def fluor_color(um: float, design: str = "mio",
               noise: bool = True) -> tuple:
    """
    Colore RGBA realistico per simulazione fluorescein.
    Basato su legge di Beer-Lambert per assorbimento/emissione lacrimale:
      I = I0 * (1 - exp(-um/lambda))
    Con gradiente tonalità:
      contatto/compressione → nero
      0-30 µm              → verde scuro (film minimo)
      30-100 µm            → verde vivo (allineamento)
      100-300 µm           → verde brillante/giallo-verde (riserva lacrimale)
      300-600 µm           → giallo brillante
      >600 µm              → bianco-giallo (eccessivo)
    """
    import random
    if math.isnan(um):
        return (0.0, 0.0, 0.0, 1.0)

    if um < -5:
        return (0.0, 0.0, 0.0, 1.0)
    if um < 0:
        t = max(0.0, (um + 5) / 5.0)
        return (0.0, t * 0.12, 0.0, 1.0)

    # Rumore film lacrimale
    n = (random.random() - 0.5) * 0.03 if noise else 0.0

    if um < 30:
        t = um / 30.0
        r, g, b = 0.0, 0.04 + t * 0.32, 0.0
    elif um < 100:
        t = (um - 30) / 70.0
        r, g, b = t * 0.08, 0.36 + t * 0.48, t * 0.04
    elif um < 300:
        t = (um - 100) / 200.0
        r, g, b = 0.08 + t * 0.52, 0.84 + t * 0.11, 0.04 - t * 0.04
    elif um < 600:
        t = (um - 300) / 300.0
        r, g, b = 0.60 + t * 0.28, 0.95, 0.0
    else:
        r, g, b = 0.90, 0.96, 0.18

    return (
        min(1.0, max(0.0, r + n)),
        min(1.0, max(0.0, g + n * 0.5)),
        min(1.0, max(0.0, b)),
        1.0
    )


# ─────────────────────────────────────────────────────────────────────────────
# Rendering vista frontale
# ─────────────────────────────────────────────────────────────────────────────

def render_frontale(r0, rb, zo, e, design, ast_D=0.0,
                    Q_presb=-0.45, td=10.8, res=180) -> plt.Figure:
    """Genera mappa fluorescein vista frontale."""
    zones = get_zones(design, r0, rb, zo, e, ast_D, Q_presb, td)
    td2   = td / 2

    img = np.zeros((res, res, 4))
    for ix in range(res):
        for iy in range(res):
            dx = (ix - res/2) / (res/2) * td2
            dy = (iy - res/2) / (res/2) * td2
            y  = math.sqrt(dx*dx + dy*dy)
            if y > td2:
                img[iy, ix] = (0, 0, 0, 0)
                continue
            theta = math.atan2(dy, dx)
            zone  = get_zone_at(y, zones)
            cl    = clearance_um(y, theta, zone, r0, e, design, ast_D)
            img[iy, ix] = fluor_color(cl, design)

    fig, ax = plt.subplots(figsize=(5, 5), facecolor='black')
    ax.set_facecolor('black')
    ax.imshow(img, extent=[-td2, td2, -td2, td2], origin='lower')

    # Cerchi zone
    for z in zones:
        circle = Circle((0, 0), z["to"],
                        fill=False, edgecolor='white', alpha=0.2, linewidth=0.5)
        ax.add_patch(circle)
        ax.text(z["to"] * 0.7, z["to"] * 0.7,
                z["label"], color='white', fontsize=6, alpha=0.5)

    # Cerchio pupilla (3.5 mm diam = raggio 1.75)
    pupilla = Circle((0, 0), 1.75,
                     fill=False, edgecolor='white', alpha=0.6,
                     linewidth=0.8, linestyle='--')
    ax.add_patch(pupilla)
    ax.text(0, -1.9, 'pupilla', color='white', fontsize=6,
            ha='center', alpha=0.7)

    ax.set_xlim(-td2, td2)
    ax.set_ylim(-td2, td2)
    ax.set_aspect('equal')
    ax.set_xlabel('mm', color='white', fontsize=8)
    ax.set_ylabel('mm', color='white', fontsize=8)
    ax.tick_params(colors='white', labelsize=7)
    for spine in ax.spines.values():
        spine.set_edgecolor('white')

    # Colorbar legenda
    from matplotlib.patches import Patch
    handles = [
        Patch(facecolor=col, label=f"{lo}–{hi} µm")
        for lo, hi, col in [
            (0, 20, "#005000"), (20, 80, "#009900"),
            (80, 200, "#44cc00"), (200, 400, "#bbee00"),
            (400, 700, "#ffee00"), (700, 9999, "#ff7700"),
        ]
    ]
    leg = ax.legend(handles=handles, loc='lower right',
                    fontsize=6, facecolor='#111',
                    labelcolor='white', framealpha=0.8)

    # Sfocatura gaussiana (simula diffusione ottica fluorescein)
    if HAS_SCIPY:
        for c in range(3):
            img[:, :, c] = gaussian_filter(img[:, :, c], sigma=1.2)

    # Riflesso cornea (arco chiaro in alto-sx)
    ax.contourf(
        np.linspace(-td2, td2, res),
        np.linspace(-td2, td2, res),
        np.fromfunction(
            lambda i, j: np.exp(
                -((i/res - 0.25)**2 + (j/res - 0.32)**2) / 0.004
            ), (res, res)
        ),
        levels=[0.85, 1.0], colors=['white'], alpha=0.10
    )

    fig.tight_layout(pad=0.5)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# Rendering sezione sagittale
# ─────────────────────────────────────────────────────────────────────────────

def render_sagittale(r0, rb, zo, e, design, ast_D=0.0,
                     Q_presb=-0.45, td=10.8, n=200) -> plt.Figure:
    """Genera sezione sagittale con clearance colorata."""
    zones = get_zones(design, r0, rb, zo, e, ast_D, Q_presb, td)
    td2   = td / 2

    ys      = np.linspace(0, td2, n)
    sag_c   = np.array([sag_asp(r0, e, float(y)) for y in ys])
    sag_l   = np.zeros(n)
    clr_um  = np.zeros(n)

    for i, y in enumerate(ys):
        zone = get_zone_at(float(y), zones)
        sl = (sag_Q(zone["r"], zone["Q"], float(y))
              if zone["tipo"] == "Q"
              else sag_sph(zone["r"], float(y)))
        sag_l[i] = sl
        clr_um[i] = (sag_c[i] - sl) * 1000 if not math.isnan(sl) else 0.0

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(7, 5),
                                    facecolor='black',
                                    gridspec_kw={'height_ratios': [3, 1]})

    for ax in [ax1, ax2]:
        ax.set_facecolor('black')
        ax.tick_params(colors='white', labelsize=7)
        for sp in ax.spines.values(): sp.set_edgecolor('#444')

    # ── Profilo sagittale ──────────────────────────────────────────────────
    # Fill clearance colorata
    for i in range(n-1):
        y1, y2 = ys[i], ys[i+1]
        sc1, sc2 = sag_c[i], sag_c[i+1]
        sl1, sl2 = sag_l[i], sag_l[i+1]
        cl = clr_um[i]
        color = fluor_color(float(cl), design, noise=False)[:3]
        ax1.fill_betweenx([sl1, sl2], [y1, y2], [y1, y2],
                          alpha=0)  # placeholder
        ax1.fill([y1, y2, y2, y1], [sc1, sc2, sl2, sl1],
                 color=color, alpha=0.85)

    # Linee profilo
    valid = ~np.isnan(sag_c)
    ax1.plot(ys[valid], sag_c[valid], color='#00ddff',
             linewidth=1.8, label='Cornea', zorder=5)
    ax1.plot(ys, sag_l, color='white',
             linewidth=1.8, label='Lente', zorder=5)

    # Linee verticali zone
    for z in zones:
        ax1.axvline(x=z["to"], color='white', alpha=0.15,
                    linewidth=0.5, linestyle='--')
        ax1.text(z["to"], max(sag_c[~np.isnan(sag_c)]) * 0.1,
                 z["label"], color='white', fontsize=6,
                 alpha=0.5, ha='center', rotation=90)

    # ZO marker
    ax1.axvline(x=zo/2, color='#ffff00', alpha=0.5,
                linewidth=0.8, linestyle=':')

    ax1.set_ylabel('Sagitta (mm)', color='white', fontsize=8)
    ax1.legend(loc='upper left', fontsize=7,
               facecolor='#111', labelcolor='white', framealpha=0.7)
    ax1.set_xlim(0, td2)
    ax1.invert_yaxis()

    # ── Clearance (µm) ────────────────────────────────────────────────────
    colors_line = [fluor_color(float(c), design, noise=False) for c in clr_um]
    for i in range(n-1):
        ax2.plot([ys[i], ys[i+1]], [clr_um[i], clr_um[i+1]],
                 color=colors_line[i][:3], linewidth=1.5)

    ax2.axhline(y=0,   color='#444', linewidth=0.5)
    ax2.axhline(y=80,  color='#44cc00', linewidth=0.5,
                linestyle='--', alpha=0.5)
    ax2.axhline(y=200, color='#bbee00', linewidth=0.5,
                linestyle='--', alpha=0.5)
    ax2.axhline(y=400, color='#ffee00', linewidth=0.5,
                linestyle='--', alpha=0.5)
    ax2.text(td2, 80,  ' 80µm', color='#44cc00', fontsize=6, va='center')
    ax2.text(td2, 200, ' 200µm', color='#bbee00', fontsize=6, va='center')
    ax2.text(td2, 400, ' 400µm', color='#ffee00', fontsize=6, va='center')
    ax2.set_ylabel('Clearance µm', color='white', fontsize=8)
    ax2.set_xlabel('Semidiametro (mm)', color='white', fontsize=8)
    ax2.set_xlim(0, td2)
    ax2.set_ylim(-50, min(max(clr_um) * 1.2, 800))

    fig.tight_layout(pad=0.5)
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# Metriche clearance
# ─────────────────────────────────────────────────────────────────────────────

def metriche_clearance(r0, rb, zo, e, design, ast_D=0.0,
                        Q_presb=-0.45, td=10.8) -> dict:
    zones = get_zones(design, r0, rb, zo, e, ast_D, Q_presb, td)
    td2   = td / 2

    def cl(y):
        zone = get_zone_at(y, zones)
        return clearance_um(y, 0, zone, r0, e, design, ast_D)

    # Punti chiave
    y_apice  = 0.05
    y_zo     = zo / 2
    y_rev    = zones[1]["to"] if len(zones) > 1 else zo/2 + 0.8
    y_ali    = zones[2]["to"] if len(zones) > 2 else zo/2 + 1.5
    y_bordo  = zones[-1]["to"] * 0.95

    # Pattern qualitativo
    c_apice = cl(y_apice)
    c_zo    = cl(y_zo)
    c_rev   = cl(y_rev)

    if design == "mio":
        pattern = (
            "Applanazione centrale" if c_apice < 10 else
            "Fluorescein centrale ottimale" if c_apice < 80 else
            "Clearance apicale eccessiva"
        )
    elif design == "iper":
        pattern = (
            "Steepening centrale adeguato" if c_apice < 0 else
            "Clearance apicale OK per steepening" if c_apice < 15 else
            "Clearance apicale eccessiva — ridurre Rb"
        )
    elif design == "ast":
        pattern = "Design torico — verificare assi"
    else:
        pattern = f"Multifocale zonale — Q={Q_presb:.2f}"

    return {
        "clearance_apice_um":  round(c_apice, 1),
        "clearance_zo_um":     round(c_zo, 1),
        "clearance_rev_um":    round(c_rev, 1),
        "clearance_ali_um":    round(cl(y_ali), 1),
        "clearance_bordo_um":  round(cl(y_bordo), 1),
        "pattern": pattern,
        "valutazione": _valuta_fit(design, c_apice, c_zo, c_rev),
    }

def _valuta_fit(design, c_apice, c_zo, c_rev):
    if design == "mio":
        if c_apice < 0:
            return "⚠️ Contatto apicale — aumentare Rb"
        if c_apice < 5:
            return "✅ Applanazione centrale ottimale"
        if c_apice < 25:
            return "✅ Fit corretto"
        return "⚠️ Clearance apicale eccessiva — diminuire Rb"
    elif design == "iper":
        if c_apice > 20:
            return "⚠️ Clearance apicale troppo alta — aumentare Rb"
        if 0 <= c_apice <= 15:
            return "✅ Apical clearance ottimale per ipermetropia"
        return "⚠️ Contatto apicale — diminuire Rb"
    elif design == "ast":
        return "ℹ️ Verificare toricità e centramento su entrambi i meridiani"
    else:
        return "ℹ️ Valutare profondità di campo su topografia differenziale"


# ─────────────────────────────────────────────────────────────────────────────
# Widget Streamlit principale
# ─────────────────────────────────────────────────────────────────────────────

def ui_fluorescein_simulator(
    design: str = "mio",
    r0: float = 7.70,
    rb: float = 8.73,
    zo: float = 5.6,
    e: float  = 0.50,
    ast_D: float = 0.0,
    Q_presb: float = -0.45,
    td: float = 10.8,
    key_prefix: str = "fluor",
    show_controls: bool = True,
):
    """
    Widget completo simulazione fluoresceinogramma.
    Può essere chiamato standalone o integrato nei calcolatori.

    Parametri:
      design       : 'mio' | 'iper' | 'ast' | 'presb'
      r0, rb, zo, e: parametri lente
      ast_D        : astigmatismo corneale (D) per design torico
      Q_presb      : Q value zona ottica per presbiopia
      key_prefix   : prefisso chiavi session_state per evitare duplicati
      show_controls: mostra slider interattivi
    """
    st.markdown("### Simulazione fluoresceinogramma")

    if show_controls:
        cc = st.columns(3)
        with cc[0]:
            design  = st.selectbox("Design", ["mio","iper","ast","presb"],
                format_func=lambda x: {
                    "mio":"Miopia (Inversa 6)",
                    "iper":"Ipermetropia",
                    "ast":"Astigmatismo",
                    "presb":"Presbiopia"
                }[x], key=f"{key_prefix}_design")
        with cc[1]:
            r0  = st.number_input("r0 (mm)", 6.5, 9.0, r0, 0.05,
                                   format="%.2f", key=f"{key_prefix}_r0")
        with cc[2]:
            rb  = st.number_input("Rb lente (mm)", 7.0, 11.0, rb, 0.05,
                                   format="%.2f", key=f"{key_prefix}_rb")
        cc2 = st.columns(3)
        with cc2[0]:
            e   = st.number_input("Eccentricità e", 0.1, 0.9, e, 0.05,
                                   key=f"{key_prefix}_e")
        with cc2[1]:
            zo  = st.number_input("ZO diam (mm)", 4.5, 7.0, zo, 0.1,
                                   key=f"{key_prefix}_zo")
        with cc2[2]:
            if design == "ast":
                ast_D = st.number_input("Astigmatismo K (D)", 0.0, 4.0, ast_D, 0.25,
                                         key=f"{key_prefix}_ast")
            elif design == "presb":
                Q_presb = st.number_input("Q value ZO", -1.2, -0.1, Q_presb, 0.05,
                                           key=f"{key_prefix}_Q")

    # Metriche
    met = metriche_clearance(r0, rb, zo, e, design, ast_D, Q_presb, td)

    m1,m2,m3,m4,m5 = st.columns(5)
    m1.metric("Apice",       f"{met['clearance_apice_um']:.0f} µm")
    m2.metric("Bordo ZO",    f"{met['clearance_zo_um']:.0f} µm")
    m3.metric("Zona rev.",   f"{met['clearance_rev_um']:.0f} µm")
    m4.metric("Allineam.",   f"{met['clearance_ali_um']:.0f} µm")
    m5.metric("Bordo",       f"{met['clearance_bordo_um']:.0f} µm")

    # Valutazione fit
    val = met["valutazione"]
    if "✅" in val: st.success(val)
    elif "⚠️" in val: st.warning(val)
    else: st.info(val)
    st.caption(f"Pattern: {met['pattern']}")

    # Generazione figure
    col_f, col_s = st.columns(2)

    with col_f:
        st.caption("Vista frontale – mappa clearance (simulazione lampada cobalto)")
        with st.spinner("Rendering vista frontale..."):
            fig_f = render_frontale(r0, rb, zo, e, design, ast_D, Q_presb, td, res=160)
            buf_f = io.BytesIO()
            fig_f.savefig(buf_f, format="png", dpi=120,
                          facecolor='black', bbox_inches='tight')
            plt.close(fig_f)
            buf_f.seek(0)
            st.image(buf_f, use_container_width=True)

    with col_s:
        st.caption("Sezione sagittale – profilo cornea/lente + clearance (µm)")
        with st.spinner("Rendering sezione sagittale..."):
            fig_s = render_sagittale(r0, rb, zo, e, design, ast_D, Q_presb, td)
            buf_s = io.BytesIO()
            fig_s.savefig(buf_s, format="png", dpi=120,
                          facecolor='black', bbox_inches='tight')
            plt.close(fig_s)
            buf_s.seek(0)
            st.image(buf_s, use_container_width=True)

    # Scala colori
    st.caption(
        "Scala colori fluorescein: "
        "🟫 contatto/compressione · "
        "🟢 0–20 µm · "
        "🟩 20–80 µm (ottimale) · "
        "🟡 80–200 µm · "
        "🟠 200–400 µm · "
        "🔴 >400 µm (eccessiva)"
    )

    # Download
    dcol1, dcol2 = st.columns(2)
    with dcol1:
        buf_f.seek(0)
        st.download_button(
            "Scarica mappa frontale (PNG)",
            buf_f.getvalue(), f"fluorescein_frontale_{design}.png",
            "image/png", key=f"{key_prefix}_dl_f"
        )
    with dcol2:
        buf_s.seek(0)
        st.download_button(
            "Scarica sezione sagittale (PNG)",
            buf_s.getvalue(), f"fluorescein_sagittale_{design}.png",
            "image/png", key=f"{key_prefix}_dl_s"
        )
