# -*- coding: utf-8 -*-
"""
Modulo: Calcolatore LAC Inverse – Ametropie Avanzate
Gestionale The Organism – PNEV

Algoritmo base: ESA Calossi (hexacurve apical clearance)
Fonte: Calossi A., CRST Global 2010; Contact Lens Spectrum 2016;
       BCLA CLEAR Orthokeratology 2021; Mountford & Noack BE lens 1998.

Ametropie gestite:
  1. Ipermetropia pura     → design steep-flat-steep (opposto alla miopia)
  2. Astigmatismo          → design torico posteriore, soglia sagitta 30 µm
  3. Presbiopia            → multifocale zonale, calcolo Q value e ADD
  4. Ipermetropia+Presbiopia → ESA hexacurve apical clearance combinato

Formule principali:
  - Sagitta sferica:  sag = r - √(r²  - y²)
  - Sagitta asferica: sag = r/p - √((r/p)² - y²/p)   dove p = 1 - e²
  - Q value (asfericità): Q = -(e²)   ↔   e = √(-Q)
  - Steepening ipermetropia: ΔD_centrale = n*D_ipermetropia (n≈1.0–1.5 factor)
  - Zona plateau larghezza: w_plateau = (TD - ZO_diam) / 2 * k_plateau
  - SAG diff torico: ΔSAG = sag_ripido - sag_piatto  →  >30µm = torico obbligatorio
  - ADD presbiopia: Q_target = Q_base - (ADD * k_Q)   dove k_Q ≈ 0.15/D
  - Aberrazione sferica longitudinale: LSA = (n-1)/(2*f²) * ρ² (approssimazione)
"""

import math
import json
try:
    from modules.ui_fluorescein import ui_fluorescein_simulator as _fluor
except ImportError:
    _fluor = None
import streamlit as st
import pandas as pd
from datetime import date

CK   = 337.5   # Costante cheratometrica
N_CL = 1.3375  # Indice rifrazione cornea/lacrima


# ─────────────────────────────────────────────────────────────────────────────
# Funzioni geometriche di base
# ─────────────────────────────────────────────────────────────────────────────

def sag_sferica(r: float, y: float) -> float:
    """Sagitta di una calotta sferica. r=raggio, y=semidiametro."""
    val = r**2 - y**2
    if val < 0:
        return float('nan')
    return r - math.sqrt(val)

def sag_asferica(r: float, e: float, y: float) -> float:
    """Sagitta di una conicoid asferica. e=eccentricità, p=1-e²."""
    p = 1 - e**2
    if p <= 0:
        return sag_sferica(r, y)
    rp = r / p
    val = rp**2 - y**2 / p
    if val < 0:
        return float('nan')
    return rp - math.sqrt(val)

def sag_da_Q(r: float, Q: float, y: float) -> float:
    """Sagitta da Q value (Q = -e², e = √(-Q))."""
    e = math.sqrt(max(-Q, 0)) if Q <= 0 else 0.0
    return sag_asferica(r, e, y)

def r_to_D(r_mm: float) -> float:
    return round(CK / r_mm, 2) if r_mm > 0 else 0.0

def D_to_r(D: float) -> float:
    return round(CK / D, 3) if D > 0 else 0.0

def clearance_um(sag_lente: float, sag_cornea: float) -> float:
    """Clearance in µm tra lente e cornea."""
    return round((sag_lente - sag_cornea) * 1000, 1)


# ─────────────────────────────────────────────────────────────────────────────
# 1. ALGORITMO IPERMETROPIA – ESA steep-flat-steep
# ─────────────────────────────────────────────────────────────────────────────
#
# Design hexacurve per ipermetropia (Calossi):
#   Zona 0 (ZO):     RIPIDA  → steepening centrale
#   Zona 1 (plateau):PIATTA  → compressione paracentrale
#   Zona 2 (reverse):RIPIDA  → raccordo e reservoir lacrimale
#   Zone 3-5 (allineamento + bordo)
#
# Formula Rb per ipermetropia (steepening):
#   Il Rb deve essere PIÙ RIPIDO di r0 (opposto alla miopia).
#   Rb_iper = r0 / (1 + ΔD * r0 / CK)
#   dove ΔD = ipermetropia da correggere (valore positivo)
#
# Clearance apicale target: 5-15 µm (permette il "sucking" centrale)

def calcola_lac_ipermetropia(
    r0: float,       # raggio apicale cornea (mm)
    e: float,        # eccentricità corneale
    ipermetropia_D: float,  # ipermetropia da correggere (+D, valore positivo)
    zo_diam: float = 5.0,   # diametro zona ottica (mm)
    clear_apicale: float = 0.010,  # clearance apicale target (mm) = 10 µm
    td: float = 10.8,       # diametro totale
    add: float = 0.0,       # ADD presbiopia (0 se solo ipermetropia)
) -> dict:
    """
    Calcola parametri ESA hexacurve per ipermetropia.
    Rb più ripido di r0 → steepening centrale.
    """
    CK = 337.5
    y_zo = zo_diam / 2

    # Sagitta corneale alla ZO (asferica)
    sag_c_zo = sag_asferica(r0, e, y_zo)

    # Il raggio base Rb deve produrre una sagitta MINORE di quella corneale
    # (la lente è più ripida → apical clearance positiva → "sucking")
    # sag_lente_zo = sag_c_zo - clear_apicale
    sag_l_zo = sag_c_zo - clear_apicale  # lente più piatta all'apice → clearance

    # Rb dalla sagitta lente alla ZO
    if y_zo**2 > sag_l_zo * (2 * r0 - sag_l_zo):
        # Approssimazione parabolica
        Rb = (y_zo**2 + sag_l_zo**2) / (2 * sag_l_zo)
    else:
        Rb = (y_zo**2 + sag_l_zo**2) / (2 * sag_l_zo)

    Rb_D = r_to_D(Rb)
    r0_D = r_to_D(r0)

    # Verifica: il Rb deve essere PIÙ PICCOLO (più ripido) di r0
    # per indurre steepening centrale
    if Rb >= r0:
        # Forza Rb più ripido
        Rb = r0 * (1 - ipermetropia_D / (CK * 2))
        Rb_D = r_to_D(Rb)

    # Potere correttivo stimato (Jessen factor per ipermetropia)
    delta_K = r0_D - Rb_D
    potere_correttivo = round(delta_K * 1.25, 2)  # Jessen factor 1.25 per iper

    # ── Zone hexacurve (steep-flat-steep-flat-steep-flat) ──────────────────
    # Zona 0: ZO  → Rb (ripido)
    # Zona 1: plateau piatto → r1 > r0 (appiattimento paracentrale)
    # Zona 2: reverse ripido → r2 < r1
    # Zona 3: allineamento 1
    # Zona 4: allineamento 2
    # Zona 5: bordo

    # Larghezze zone (mm da bordo a bordo)
    w_zo      = zo_diam
    w_plateau = 1.0          # zona plateau
    w_rev     = 0.6          # reverse
    w_ali1    = 0.8
    w_ali2    = 0.6
    w_bordo   = td - w_zo - w_plateau - w_rev - w_ali1 - w_ali2

    # Diametri cumulativi
    d0 = w_zo
    d1 = d0 + w_plateau
    d2 = d1 + w_rev
    d3 = d2 + w_ali1
    d4 = d3 + w_ali2
    d5 = td

    # Raggi zone
    # r1 plateau: più piatto di r0 (compressione paracentrale)
    r1 = round(r0 * 1.15 + 0.3, 2)   # appiattimento ~+0.6 mm

    # r2 reverse: ripido per raccordo
    r2 = round(r0 * 0.85 - 0.2, 2)

    # r3, r4 allineamento: seguono la cornea
    sag_c_d3 = sag_asferica(r0, e, d3/2)
    # raggio di allineamento tangente alla cornea a d3
    r3 = round((d3/2)**2 / (2 * sag_c_d3) + sag_c_d3/2, 2) if sag_c_d3 > 0 else round(r0 * 1.05, 2)

    sag_c_d4 = sag_asferica(r0, e, d4/2)
    r4 = round((d4/2)**2 / (2 * sag_c_d4) + sag_c_d4/2, 2) if sag_c_d4 > 0 else round(r0 * 1.15, 2)

    # r5 bordo: molto piatto
    r5 = round(r0 * 1.4 + 1.0, 2)

    # ── Q value e presbiopia ───────────────────────────────────────────────
    # La ZO asferica induce aberrazione sferica positiva → aumento profondità campo
    # Per ipermetropia: Q_zo iniziale neutro (-0.2 / -0.3)
    # Per ipermetropia + presbiopia: Q più negativo per più aberrazione
    Q_base = -0.3
    if add > 0:
        # k_Q = 0.15 per diottria di ADD (Calossi 2007, 2009)
        Q_target = Q_base - (add * 0.15)
        e_zo = math.sqrt(-Q_target) if Q_target < 0 else 0.0
    else:
        Q_target = Q_base
        e_zo = math.sqrt(-Q_base)

    # LSA stimata (aberrazione sferica longitudinale) per pupilla 5 mm
    # LSA ≈ (n-1) * e² / (2 * r0³) * y²  (Calossi 2007)
    y_pupilla = 2.5  # mm (pupilla 5 mm)
    lsa_D = round((N_CL - 1) * e_zo**2 / (2 * (r0/1000)**3) / 1e9
                  if e_zo > 0 else 0, 2)
    # Stima più pratica:
    lsa_D = round(e_zo**2 * (r0_D - Rb_D) * 0.8, 2)

    # Controllo clearance al bordo ZO
    sag_l_zo2 = sag_sferica(Rb, y_zo)
    clear_zo_um = clearance_um(sag_c_zo, sag_l_zo2)

    flange = [
        {"nome": "Plateau (r1)", "raggio_mm": r1, "diottrie": r_to_D(r1),
         "diametro_in": d0, "diametro_out": d1},
        {"nome": "Reverse (r2)", "raggio_mm": r2, "diottrie": r_to_D(r2),
         "diametro_in": d1, "diametro_out": d2},
        {"nome": "Allineamento 1 (r3)", "raggio_mm": r3, "diottrie": r_to_D(r3),
         "diametro_in": d2, "diametro_out": d3},
        {"nome": "Allineamento 2 (r4)", "raggio_mm": r4, "diottrie": r_to_D(r4),
         "diametro_in": d3, "diametro_out": d4},
        {"nome": "Bordo (r5)", "raggio_mm": r5, "diottrie": r_to_D(r5),
         "diametro_in": d4, "diametro_out": d5},
    ]

    return {
        "tipo": "Ipermetropia" + (" + Presbiopia" if add > 0 else ""),
        "Rb_mm": round(Rb, 3),
        "Rb_D": round(Rb_D, 2),
        "r0_mm": r0,
        "r0_D": r0_D,
        "zo_diam": zo_diam,
        "td": td,
        "clear_apicale_um": round(clear_apicale * 1000, 1),
        "clear_zo_um": clear_zo_um,
        "potere_correttivo_D": potere_correttivo,
        "Q_target": round(Q_target, 3),
        "e_zo": round(e_zo, 3),
        "lsa_stim_D": lsa_D,
        "add_D": add,
        "flange": flange,
        "note": (f"Design steep-flat-steep (Calossi ESA). "
                 f"Rb {Rb:.3f} mm ({Rb_D:.2f} D) più ripido di r0 {r0:.2f} mm ({r0_D:.2f} D). "
                 f"Clearance apicale {clear_apicale*1000:.0f} µm."),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 2. ALGORITMO ASTIGMATISMO – Design torico posteriore
# ─────────────────────────────────────────────────────────────────────────────
#
# Criterio torico (Kojima et al. 2016):
#   ΔSAG = sag_ripido - sag_piatto  a corda 8-9 mm
#   Se ΔSAG > 30 µm → design torico posteriore obbligatorio
#
# Il design torico calcola Rb separatamente per i due meridiani:
#   Meridiano piatto (K flat): Rb_flat = calcolato come per miopia normale
#   Meridiano ripido (K steep): Rb_steep = calcolato per K steep
#   Toricitá posteriore = Rb_steep - Rb_flat

def calcola_sagitta_diff(
    r_flat: float, r_steep: float,
    e_flat: float, e_steep: float,
    chord: float = 8.5,
) -> dict:
    """
    Calcola la differenza sagittale tra meridiano piatto e ripido
    a una data corda (default 8.5 mm = tipico punto di appoggio).
    """
    y = chord / 2
    sag_f = sag_asferica(r_flat,  e_flat,  y)
    sag_s = sag_asferica(r_steep, e_steep, y)
    delta = round((sag_s - sag_f) * 1000, 1)  # µm
    torico_obbligatorio = delta > 30

    return {
        "sag_flat_mm":  round(sag_f, 4),
        "sag_steep_mm": round(sag_s, 4),
        "delta_sag_um": delta,
        "chord_mm": chord,
        "torico_obbligatorio": torico_obbligatorio,
        "raccomandazione": (
            f"ΔSAG = {delta:.1f} µm — "
            + ("Design TORICO POSTERIORE necessario (>30 µm)" if torico_obbligatorio
               else "Design sferico accettabile (<30 µm)")
        ),
    }

def calcola_lac_astigmatismo(
    r_flat: float, r_steep: float,
    e_flat: float, e_steep: float,
    miopia_D: float = 0.0,
    astigm_D: float = 0.0,
    zo_diam: float = 5.6,
    clear_inv: float = 0.054,
    td: float = 10.8,
) -> dict:
    """
    Calcola Rb per i due meridiani + toricitá posteriore.
    Basa sul modello BE/ESA adattato per astigmatismo.
    """
    # Effetto refrattivo per meridiano
    # Meridiano piatto corregge la miopia base
    # Meridiano ripido corregge miopia + astigmatismo
    D_flat  = -miopia_D                        # miopia (positivo = da correggere)
    D_steep = -miopia_D + abs(astigm_D)        # miopia + componente astigmatica

    y_zo = zo_diam / 2

    def _calcola_Rb(r0, e, corr_D):
        sag_c = sag_asferica(r0, e, y_zo)
        delta_r0 = CK / (r_to_D(r0) + corr_D) - r0 if corr_D != 0 else 0
        sag_l = sag_c + clear_inv + delta_r0 * 0.01  # approx
        Rb = (y_zo**2 + sag_l**2) / (2 * sag_l)
        return round(Rb, 3)

    Rb_flat  = _calcola_Rb(r_flat,  e_flat,  D_flat)
    Rb_steep = _calcola_Rb(r_steep, e_steep, D_steep)
    toricity = round(Rb_steep - Rb_flat, 3)

    # Sagitta diff al punto di appoggio
    sag_info = calcola_sagitta_diff(r_flat, r_steep, e_flat, e_steep)

    # Zone (sferico medio per le zone di allineamento)
    r0_medio = (r_flat + r_steep) / 2
    e_medio  = (e_flat + e_steep) / 2

    # Flange (basate sul meridiano medio)
    sag_c3 = sag_asferica(r0_medio, e_medio, td/2 * 0.75)
    r3 = round((td/2 * 0.75)**2 / (2 * sag_c3) + sag_c3/2, 2) if sag_c3 > 0 else round(r0_medio * 1.1, 2)
    r4 = round(r0_medio * 1.25 + 0.5, 2)
    r5 = round(r0_medio * 1.45 + 1.0, 2)

    d1 = zo_diam + 1.0
    d2 = d1 + 0.7
    d3 = d2 + 0.8
    d4 = d3 + 0.6
    d5 = td

    raccomandazione_fit = []
    if sag_info["torico_obbligatorio"]:
        raccomandazione_fit.append(
            f"⚠️ Design torico obbligatorio (ΔSAG={sag_info['delta_sag_um']:.1f} µm > 30 µm)")
        raccomandazione_fit.append(
            f"Toricitá posteriore Rb_steep - Rb_flat = {toricity:+.3f} mm")
    else:
        raccomandazione_fit.append(
            f"Design sferico accettabile (ΔSAG={sag_info['delta_sag_um']:.1f} µm ≤ 30 µm)")
        raccomandazione_fit.append(
            "Un design sferico centrerà correttamente se astigm. ≤ 1.50 D WTR o ≤ 0.75 D ATR")

    if abs(astigm_D) > 1.50:
        raccomandazione_fit.append(
            "Astigmatismo > 1.50 D: valutare design FOKX o zone ottiche toriche")

    return {
        "tipo": "Astigmatismo",
        "Rb_flat_mm":  Rb_flat,
        "Rb_flat_D":   r_to_D(Rb_flat),
        "Rb_steep_mm": Rb_steep,
        "Rb_steep_D":  r_to_D(Rb_steep),
        "toricity_mm": toricity,
        "toricity_D":  round(r_to_D(Rb_flat) - r_to_D(Rb_steep), 2),
        "sag_info": sag_info,
        "zo_diam": zo_diam,
        "td": td,
        "flange": [
            {"nome": "r1", "raggio_flat": round(r_flat * 1.10, 2),
             "raggio_steep": round(r_steep * 1.08, 2), "diametro": d1},
            {"nome": "r2", "raggio_flat": round(r_flat * 0.90, 2),
             "raggio_steep": round(r_steep * 0.88, 2), "diametro": d2},
            {"nome": "r3", "raggio_flat": r3, "raggio_steep": round(r3 * 0.98, 2),
             "diametro": d3},
            {"nome": "r4", "raggio_flat": r4, "raggio_steep": r4, "diametro": d4},
            {"nome": "r5", "raggio_flat": r5, "raggio_steep": r5, "diametro": d5},
        ],
        "raccomandazione": raccomandazione_fit,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 3. ALGORITMO PRESBIOPIA – Multifocale zonale (Q value)
# ─────────────────────────────────────────────────────────────────────────────
#
# Meccanismo: la ZO asferica con Q negativo induce aberrazione sferica positiva
# che aumenta la profondità di campo (pseudo-accomodazione).
# Formula Q target (Calossi 2007, 2009):
#   LSA = depth_of_focus / ADD_richiesto  →  Q = -LSA * factor
#
# Criteri clinici:
#   ADD ≤ +1.00 D: solo multifocale zonale
#   ADD +1.25 – +2.00 D: multifocale + eventuale monovisione leggera
#   ADD > +2.00 D: monovisione + prescrizione occhiali per vicino

def calcola_lac_presbiopia(
    r0: float,
    e: float,
    add: float,         # ADD richiesta (+D, positivo)
    miopia_D: float = 0.0,   # miopia concomitante (negativo)
    ipermetropia_D: float = 0.0,  # ipermetropia concomitante (positivo)
    zo_diam: float = 5.6,
    td: float = 10.8,
    clear_inv: float = 0.054,
    strategia: str = "multifocale",  # "multifocale" / "monovisione"
) -> dict:
    """
    Calcola Q value target per presbiopia e parametri ESA.
    """
    r0_D = r_to_D(r0)
    y_zo = zo_diam / 2

    # Q value target (Calossi):
    # Ogni 0.10 di variazione Q produce ~0.15 D di aberrazione sferica
    # ADD target ≈ LSA per pupilla fisiologica (3-4 mm fotopica)
    k_Q = 0.15   # D per unità di Q
    # Q base corneale tipico: -0.26 (media popolazione)
    Q_corneale = -(e**2)
    # Q target: deve produrre abbastanza LSA per l'ADD
    # Attenzione: aumentare troppo Q peggiora la qualità visiva a distanza
    Q_target = Q_corneale - (add / k_Q)
    # Limite clinico: Q non oltre -1.0 (troppa aberrazione)
    Q_target = max(Q_target, -1.0)
    e_target = math.sqrt(-Q_target) if Q_target < 0 else 0.0

    # ADD effettivamente correggibile
    add_correggibile = round(-(Q_target - Q_corneale) * k_Q, 2)
    add_residuo = round(add - add_correggibile, 2)

    # Strategia
    if add > 2.0:
        strategia_consigliata = "monovisione"
        note_add = (f"ADD +{add:.2f} D > +2.00 D: multifocale zonale insufficiente. "
                    "Considerare monovisione (occhio non dominante per il vicino) "
                    "± occhiali per attività prolungate.")
    elif add > 1.25:
        strategia_consigliata = "multifocale + monovisione leggera"
        note_add = (f"ADD +{add:.2f} D: multifocale zonale + lieve monovisione "
                    "(–0.50/–0.75 D occhio non dominante).")
    else:
        strategia_consigliata = "multifocale zonale"
        note_add = (f"ADD +{add:.2f} D ≤ +1.25 D: multifocale zonale sufficiente "
                    "(aumento aberrazione sferica via Q value).")

    # Rb per la correzione della miopia/ipermetropia di base
    corr_sferico = miopia_D if miopia_D != 0 else -ipermetropia_D
    y_zo_rb = y_zo
    sag_c_zo = sag_asferica(r0, e, y_zo_rb)
    sag_l_zo = sag_c_zo + clear_inv + corr_sferico * (-0.012)
    Rb = round((y_zo_rb**2 + sag_l_zo**2) / (2 * sag_l_zo), 3)

    # Zona di transizione (tra ZO multifocale e allineamento)
    # La zona di transizione ha Q intermedio per raccordo morbido
    Q_transiz = (Q_target + 0) / 2
    w_transiz = 0.5  # mm

    # Flange
    d1 = zo_diam + 0.6
    d2 = d1 + 0.7
    d3 = d2 + 0.8
    d4 = d3 + 0.6
    d5 = td

    r1 = round(r0 * 1.12 + 0.3, 2)
    r2 = round(r0 * 0.88 - 0.1, 2)
    sag_c3 = sag_asferica(r0, e, d3/2)
    r3 = round((d3/2)**2 / (2 * sag_c3) + sag_c3/2, 2) if sag_c3 > 0 else round(r0 * 1.1, 2)
    r4 = round(r0 * 1.3 + 0.6, 2)
    r5 = round(r0 * 1.5 + 1.2, 2)

    # Pupilla fotopica stimata per calcolo area multifocale
    y_pupilla = 1.75  # mm (pupilla 3.5 mm fotopica)
    area_zo_utile = math.pi * y_zo**2
    area_pupilla  = math.pi * y_pupilla**2
    ratio_pupilla = round(area_pupilla / area_zo_utile * 100, 1)

    return {
        "tipo": "Presbiopia",
        "strategia_consigliata": strategia_consigliata,
        "Rb_mm": Rb,
        "Rb_D": r_to_D(Rb),
        "r0_mm": r0,
        "r0_D": r0_D,
        "Q_corneale": round(Q_corneale, 3),
        "Q_target": round(Q_target, 3),
        "e_target": round(e_target, 3),
        "add_D": add,
        "add_correggibile_D": add_correggibile,
        "add_residuo_D": max(add_residuo, 0),
        "Q_transizione": round(Q_transiz, 3),
        "zo_diam": zo_diam,
        "td": td,
        "area_zo_pct_pupilla": ratio_pupilla,
        "note_add": note_add,
        "flange": [
            {"nome": "r1", "raggio_mm": r1, "diottrie": r_to_D(r1), "diametro": d1},
            {"nome": "r2", "raggio_mm": r2, "diottrie": r_to_D(r2), "diametro": d2},
            {"nome": "r3", "raggio_mm": r3, "diottrie": r_to_D(r3), "diametro": d3},
            {"nome": "r4", "raggio_mm": r4, "diottrie": r_to_D(r4), "diametro": d4},
            {"nome": "r5", "raggio_mm": r5, "diottrie": r_to_D(r5), "diametro": d5},
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Grafico profilo sagittale
# ─────────────────────────────────────────────────────────────────────────────

def _grafico_profilo(r0, e, Rb, zo_diam, td, label_lente="Lente"):
    """Genera grafico profilo cornea vs lente."""
    n = 80
    y_max = td / 2
    ys = [y_max * i / n for i in range(n + 1)]

    sag_cornea = [sag_asferica(r0, e, y) for y in ys]
    sag_lente  = [sag_sferica(Rb, y) if y <= zo_diam/2
                  else None for y in ys]
    # Estende la lente oltre la ZO con una sfera di raccordo
    sag_lente_full = []
    for i, y in enumerate(ys):
        if y <= zo_diam / 2:
            sag_lente_full.append(sag_sferica(Rb, y))
        else:
            sag_lente_full.append(sag_cornea[i])  # approssima allineamento

    clearance = [round((sc - sl) * 1000, 1)
                 for sc, sl in zip(sag_cornea, sag_lente_full)]

    df = pd.DataFrame({
        "y (mm)": [round(y, 2) for y in ys],
        "Cornea (mm)": [round(s, 4) for s in sag_cornea],
        f"{label_lente} (mm)": [round(s, 4) for s in sag_lente_full],
        "Clearance (µm)": clearance,
    })

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Profilo sagittale**")
        st.line_chart(df.set_index("y (mm)")[["Cornea (mm)", f"{label_lente} (mm)"]])
    with col2:
        st.markdown("**Clearance (µm)**")
        st.line_chart(df.set_index("y (mm)")[["Clearance (µm)"]])

    # Metriche clearance
    m1, m2, m3 = st.columns(3)
    idx_zo = min(range(len(ys)), key=lambda i: abs(ys[i] - zo_diam / 2))
    m1.metric("Clearance apicale", f"{clearance[0]:.0f} µm")
    m2.metric(f"Clearance bordo ZO ({zo_diam:.1f} mm)", f"{clearance[idx_zo]:.0f} µm")
    m3.metric("Clearance bordo TD", f"{clearance[-1]:.0f} µm")

    return df


# ─────────────────────────────────────────────────────────────────────────────
# Schema laboratorio
# ─────────────────────────────────────────────────────────────────────────────

def _schema_laboratorio(res: dict, r0: float, e: float,
                         medico: str = "", paziente: str = "") -> str:
    tipo = res.get("tipo", "LAC Inversa")
    righe = [
        "═══════════════════════════════════════════",
        f"  LAC INVERSA – {tipo.upper()}",
        f"  Paziente: {paziente or '—'}",
        f"  Medico: {medico or '—'}",
        f"  Data: {date.today().strftime('%d/%m/%Y')}",
        "═══════════════════════════════════════════",
        f"  r0 corneale: {r0:.2f} mm ({r_to_D(r0):.2f} D)  e={e:.2f}",
    ]
    if "Rb_mm" in res:
        righe += [
            f"  BOZR Rb:     {res['Rb_mm']:.3f} mm ({res['Rb_D']:.2f} D)",
            f"  ZO diam:     {res.get('zo_diam', '—')} mm",
            f"  TD:          {res.get('td', '—')} mm",
        ]
    if "Rb_flat_mm" in res:
        righe += [
            f"  Rb flat:     {res['Rb_flat_mm']:.3f} mm ({res['Rb_flat_D']:.2f} D)",
            f"  Rb steep:    {res['Rb_steep_mm']:.3f} mm ({res['Rb_steep_D']:.2f} D)",
            f"  Toricitá:    {res['toricity_mm']:+.3f} mm ({res['toricity_D']:+.2f} D)",
        ]
    if res.get("Q_target"):
        righe.append(f"  Q ZO target: {res['Q_target']:.3f}  e ZO={res.get('e_target', res.get('e_zo','—'))}")
    if res.get("add_D"):
        righe.append(f"  ADD:         +{res['add_D']:.2f} D")
    righe.append("───────────────────────────────────────────")
    for fl in res.get("flange", []):
        nome = fl.get("nome", "")
        if "raggio_flat" in fl:
            righe.append(
                f"  {nome:20s} flat={fl['raggio_flat']:.2f} steep={fl['raggio_steep']:.2f} mm  Ø={fl['diametro']:.1f}")
        else:
            righe.append(
                f"  {nome:20s} r={fl['raggio_mm']:.2f} mm ({fl.get('diottrie',0):.2f} D)  Ø={fl.get('diametro_out', fl.get('diametro','—'))}")
    if res.get("note"):
        righe += ["───────────────────────────────────────────", f"  {res['note']}"]
    righe.append("═══════════════════════════════════════════")
    return "\n".join(righe)


# ─────────────────────────────────────────────────────────────────────────────
# UI principale
# ─────────────────────────────────────────────────────────────────────────────

def ui_calcolatore_lac_plus():
    st.header("Calcolatore LAC Inverse – Ametropie Avanzate")
    st.caption("Algoritmo ESA Calossi (hexacurve apical clearance) · "
               "Ipermetropia · Astigmatismo · Presbiopia · Combinata")

    # Dati corneali comuni (fuori dai tab, on_change bidirezionale)
    CK2 = 337.5
    st.markdown("### Dati corneali di base")
    for k, v in [("lcp_r0", 7.70), ("lcp_r0_D", round(CK2/7.70, 2)),
                 ("lcp_r_flat", 7.70), ("lcp_r_flat_D", round(CK2/7.70, 2)),
                 ("lcp_r_steep", 7.60), ("lcp_r_steep_D", round(CK2/7.60, 2))]:
        if k not in st.session_state:
            st.session_state[k] = v

    def _sync_lcp(km, kD):
        def _mm():
            v = st.session_state.get(km, 0)
            if v > 0: st.session_state[kD] = round(CK2/v, 2)
        def _D():
            v = st.session_state.get(kD, 0)
            if v > 0: st.session_state[km] = round(CK2/v, 3)
        return _mm, _D

    _r0_mm, _r0_D = _sync_lcp("lcp_r0", "lcp_r0_D")
    _rf_mm, _rf_D = _sync_lcp("lcp_r_flat", "lcp_r_flat_D")
    _rs_mm, _rs_D = _sync_lcp("lcp_r_steep", "lcp_r_steep_D")

    bc = st.columns(6)
    with bc[0]: st.number_input("r0 (mm)", 6.0, 9.5, step=0.01, format="%.2f",
                                 key="lcp_r0", on_change=_r0_mm)
    with bc[1]: st.number_input("r0 (D)",  35.0,52.0,step=0.25, format="%.2f",
                                 key="lcp_r0_D", on_change=_r0_D)
    with bc[2]: st.number_input("K flat (mm)", 6.0, 9.5, step=0.01, format="%.2f",
                                 key="lcp_r_flat", on_change=_rf_mm)
    with bc[3]: st.number_input("K flat (D)",  35.0,52.0,step=0.25, format="%.2f",
                                 key="lcp_r_flat_D", on_change=_rf_D)
    with bc[4]: st.number_input("K steep (mm)", 6.0, 9.5, step=0.01, format="%.2f",
                                 key="lcp_r_steep", on_change=_rs_mm)
    with bc[5]: st.number_input("K steep (D)",  35.0,52.0,step=0.25, format="%.2f",
                                 key="lcp_r_steep_D", on_change=_rs_D)

    ast_D = abs(st.session_state.get("lcp_r_flat_D", 0)
                - st.session_state.get("lcp_r_steep_D", 0))
    ec = st.columns(3)
    with ec[0]: e_val = st.number_input("Eccentricità media", 0.0, 1.5, 0.50, 0.01,
                                         key="lcp_e")
    with ec[1]: e_flat  = st.number_input("e flat",  0.0, 1.5, 0.48, 0.01, key="lcp_ef")
    with ec[2]: e_steep = st.number_input("e steep", 0.0, 1.5, 0.52, 0.01, key="lcp_es")

    if ast_D > 0.05:
        st.info(f"Astigmatismo corneale rilevato: **{ast_D:.2f} D**")

    medico   = st.text_input("Medico esaminatore", "", key="lcp_medico")
    paziente = st.text_input("Paziente (nome)", "",   key="lcp_paz")

    st.divider()

    tab_iper, tab_ast, tab_presb, tab_comb = st.tabs([
        "🔴 Ipermetropia", "⬡ Astigmatismo",
        "👓 Presbiopia", "✨ Combinata (ESA Calossi)"])

    r0    = st.session_state.get("lcp_r0", 7.70)
    r_fl  = st.session_state.get("lcp_r_flat", 7.70)
    r_st  = st.session_state.get("lcp_r_steep", 7.60)

    # ── Tab 1: Ipermetropia ────────────────────────────────────────────────
    with tab_iper:
        st.subheader("Ipermetropia pura – Design steep-flat-steep")
        st.caption("Il Rb è più ripido di r0 → steepening centrale → effetto plus")
        i1,i2,i3,i4 = st.columns(4)
        with i1: iper_D = st.number_input("Ipermetropia (D)", 0.25, 4.0, 1.50, 0.25, key="lcp_iper_D")
        with i2: zo_i   = st.number_input("ZO diam (mm)", 4.0, 7.0, 5.0, 0.1, key="lcp_iper_zo")
        with i3: cl_i   = st.number_input("Clearance apicale (µm)", 3.0, 20.0, 10.0, 1.0, key="lcp_iper_cl")
        with i4: td_i   = st.number_input("TD (mm)", 9.0, 12.0, 10.8, 0.1, key="lcp_iper_td")

        if st.button("Calcola Ipermetropia", type="primary", key="btn_iper"):
            res = calcola_lac_ipermetropia(
                r0=r0, e=e_val, ipermetropia_D=iper_D,
                zo_diam=zo_i, clear_apicale=cl_i/1000, td=td_i)
            st.session_state["_res_iper"] = res

        if "_res_iper" in st.session_state:
            res = st.session_state["_res_iper"]
            _mostra_risultati(res, r0, e_val, medico, paziente, "Ipermetropia")

    # ── Tab 2: Astigmatismo ────────────────────────────────────────────────
    with tab_ast:
        st.subheader("Astigmatismo – Design torico posteriore")
        st.caption("Criterio Kojima: ΔSAG > 30 µm → design torico obbligatorio")

        a1,a2,a3,a4 = st.columns(4)
        with a1: ast_corr = st.number_input("Astigmatismo (D)", 0.25, 7.0, 1.25, 0.25, key="lcp_ast_D")
        with a2: mio_ast  = st.number_input("Miopia assoc. (D)", -8.0, 0.0, -2.0, 0.25, key="lcp_ast_mio")
        with a3: zo_a     = st.number_input("ZO diam (mm)", 4.0, 7.0, 5.6, 0.1, key="lcp_ast_zo")
        with a4: chord_a  = st.number_input("Corda valut. ΔSAG (mm)", 7.0, 10.0, 8.5, 0.5, key="lcp_ast_chord")

        # Calcolo ΔSAG sempre visibile
        sag_info = calcola_sagitta_diff(r_fl, r_st, e_flat, e_steep, chord_a)
        delta_col = st.columns(3)
        delta_col[0].metric("Sag meridiano piatto", f"{sag_info['sag_flat_mm']*1000:.0f} µm")
        delta_col[1].metric("Sag meridiano ripido", f"{sag_info['sag_steep_mm']*1000:.0f} µm")
        delta_col[2].metric("ΔSAG", f"{sag_info['delta_sag_um']:.0f} µm",
                             delta="TORICO" if sag_info["torico_obbligatorio"] else "sferico OK",
                             delta_color="inverse" if sag_info["torico_obbligatorio"] else "normal")

        if sag_info["torico_obbligatorio"]:
            st.error(f"⚠️ {sag_info['raccomandazione']}")
        else:
            st.success(f"✅ {sag_info['raccomandazione']}")

        if st.button("Calcola Astigmatismo", type="primary", key="btn_ast"):
            res = calcola_lac_astigmatismo(
                r_flat=r_fl, r_steep=r_st,
                e_flat=e_flat, e_steep=e_steep,
                miopia_D=mio_ast, astigm_D=ast_corr,
                zo_diam=zo_a, td=st.session_state.get("lcp_iper_td", 10.8))
            st.session_state["_res_ast"] = res

        if "_res_ast" in st.session_state:
            res = st.session_state["_res_ast"]
            _mostra_risultati_torico(res, r_fl, r_st, e_flat, e_steep,
                                     medico, paziente)

    # ── Tab 3: Presbiopia ──────────────────────────────────────────────────
    with tab_presb:
        st.subheader("Presbiopia – Multifocale zonale (Q value)")
        st.caption("Induzione aberrazione sferica via ZO asferica con Q negativo")

        p1,p2,p3,p4 = st.columns(4)
        with p1: add_P   = st.number_input("ADD (D)", 0.50, 3.50, 1.50, 0.25, key="lcp_add")
        with p2: mio_P   = st.number_input("Miopia assoc. (D)", -6.0, 0.0, 0.0, 0.25, key="lcp_presb_mio")
        with p3: zo_P    = st.number_input("ZO diam (mm)", 4.0, 7.0, 5.6, 0.1, key="lcp_presb_zo")
        with p4: td_P    = st.number_input("TD (mm)", 9.0, 12.0, 10.8, 0.1, key="lcp_presb_td")

        if st.button("Calcola Presbiopia", type="primary", key="btn_presb"):
            res = calcola_lac_presbiopia(
                r0=r0, e=e_val, add=add_P,
                miopia_D=mio_P, zo_diam=zo_P, td=td_P)
            st.session_state["_res_presb"] = res

        if "_res_presb" in st.session_state:
            res = st.session_state["_res_presb"]
            _mostra_risultati_presbiopia(res, r0, e_val, medico, paziente)

    # ── Tab 4: Combinata ───────────────────────────────────────────────────
    with tab_comb:
        st.subheader("Ipermetropia + Presbiopia – ESA Calossi hexacurve")
        st.caption("Caso clinico: correzione ipermetropia + ADD presbiopia "
                   "con design steep-flat-steep + Q asfericitá ZO")

        cb1,cb2,cb3,cb4 = st.columns(4)
        with cb1: iper_C = st.number_input("Ipermetropia (D)", 0.25, 4.0, 1.50, 0.25, key="lcp_comb_iper")
        with cb2: add_C  = st.number_input("ADD presbiopia (D)", 0.50, 3.0, 1.50, 0.25, key="lcp_comb_add")
        with cb3: zo_C   = st.number_input("ZO diam (mm)", 4.0, 7.0, 5.0, 0.1, key="lcp_comb_zo")
        with cb4: cl_C   = st.number_input("Clearance apicale (µm)", 3.0, 20.0, 10.0, 1.0, key="lcp_comb_cl")

        st.info(
            "**Step-by-step Calossi:**\n"
            "1. Indurre multifocalità corneale (Q target) → profondità di campo\n"
            "2. Se insufficiente: aggiungere lieve monovisione (–0.50D occhio non dominante)\n"
            "3. Se entrambi falliscono: ottimizzare per distanza + occhiali per vicino"
        )

        if st.button("Calcola Combinata", type="primary", key="btn_comb"):
            res = calcola_lac_ipermetropia(
                r0=r0, e=e_val, ipermetropia_D=iper_C,
                zo_diam=zo_C, clear_apicale=cl_C/1000,
                td=st.session_state.get("lcp_presb_td", 10.8),
                add=add_C)
            # Arricchisce con dati presbiopia
            res_presb = calcola_lac_presbiopia(
                r0=r0, e=e_val, add=add_C,
                ipermetropia_D=iper_C, zo_diam=zo_C)
            res["Q_target"]         = res_presb["Q_target"]
            res["e_target"]         = res_presb["e_target"]
            res["add_correggibile_D"] = res_presb["add_correggibile_D"]
            res["add_residuo_D"]    = res_presb["add_residuo_D"]
            res["strategia"]        = res_presb["strategia_consigliata"]
            res["note_add"]         = res_presb["note_add"]
            st.session_state["_res_comb"] = res

        if "_res_comb" in st.session_state:
            res = st.session_state["_res_comb"]
            st.success(f"**Strategia consigliata:** {res.get('strategia','—')}")
            if res.get("note_add"):
                st.info(res["note_add"])
            _mostra_risultati(res, r0, e_val, medico, paziente, "Combinata")


# ─────────────────────────────────────────────────────────────────────────────
# Helper display
# ─────────────────────────────────────────────────────────────────────────────

def _mostra_risultati(res, r0, e, medico, paziente, label):
    st.success(f"Calcolo completato – {label}")
    m = st.columns(4)
    m[0].metric("Rb (mm)", f"{res['Rb_mm']:.3f}")
    m[1].metric("Rb (D)",  f"{res['Rb_D']:.2f}")
    m[2].metric("ZO (mm)", f"{res.get('zo_diam','—')}")
    m[3].metric("TD (mm)", f"{res.get('td','—')}")

    if res.get("Q_target"):
        q1,q2,q3 = st.columns(3)
        q1.metric("Q target ZO", f"{res['Q_target']:.3f}")
        q2.metric("e ZO", f"{res.get('e_target', res.get('e_zo','—'))}")
        if res.get("add_correggibile_D"):
            q3.metric("ADD correggibile", f"+{res['add_correggibile_D']:.2f} D")

    if res.get("potere_correttivo_D"):
        st.metric("Potere correttivo stimato", f"{res['potere_correttivo_D']:+.2f} D")

    # Flange
    st.markdown("**Zone e raggi**")
    fl_data = []
    for fl in res.get("flange", []):
        fl_data.append({
            "Zona": fl.get("nome"),
            "Raggio (mm)": fl.get("raggio_mm", "—"),
            "D": fl.get("diottrie", "—"),
            "Ø in (mm)": fl.get("diametro_in", "—"),
            "Ø out (mm)": fl.get("diametro_out", fl.get("diametro", "—")),
        })
    if fl_data:
        st.dataframe(pd.DataFrame(fl_data), use_container_width=True, hide_index=True)

    # Profilo
    Rb = res["Rb_mm"]
    zo = res.get("zo_diam", 5.6)
    td = res.get("td", 10.8)
    _grafico_profilo(r0, e, Rb, zo, td, label)

    # Schema
    with st.expander("📋 Schema per il laboratorio"):
        st.code(_schema_laboratorio(res, r0, e, medico, paziente), language=None)
    if _fluor:
        with st.expander("🔬 Fluoresceinogramma simulato"):
            Q_v = res.get("Q_target", -0.45)
            _fluor("presb", r0, res["Rb_mm"], res.get("zo_diam",5.6), e,
                   Q_presb=Q_v, key_prefix="fluor_presb", show_controls=False)
    if _fluor:
        with st.expander("🔬 Fluoresceinogramma simulato"):
            design_map = {"Ipermetropia":"iper","Ipermetropia + Presbiopia":"iper","Combinata":"iper"}
            _fluor(design_map.get(res.get("tipo",""),"mio"), r0, res["Rb_mm"],
                   res.get("zo_diam",5.6), e, key_prefix="fluor_plus", show_controls=False)


def _mostra_risultati_torico(res, r_fl, r_st, e_fl, e_st, medico, paziente):
    st.success("Calcolo astigmatismo completato")

    for msg in res.get("raccomandazione", []):
        if "TORICO" in msg or "⚠️" in msg:
            st.warning(msg)
        else:
            st.info(msg)

    t1,t2,t3,t4 = st.columns(4)
    t1.metric("Rb flat (mm)",  f"{res['Rb_flat_mm']:.3f}")
    t2.metric("Rb flat (D)",   f"{res['Rb_flat_D']:.2f}")
    t3.metric("Rb steep (mm)", f"{res['Rb_steep_mm']:.3f}")
    t4.metric("Rb steep (D)",  f"{res['Rb_steep_D']:.2f}")

    st.metric("Toricitá posteriore", f"{res['toricity_mm']:+.3f} mm ({res['toricity_D']:+.2f} D)")

    st.markdown("**Zone torico**")
    fl_data = [{"Zona": fl["nome"],
                "r flat (mm)": fl["raggio_flat"],
                "r steep (mm)": fl["raggio_steep"],
                "Ø (mm)": fl["diametro"]} for fl in res.get("flange", [])]
    if fl_data:
        st.dataframe(pd.DataFrame(fl_data), use_container_width=True, hide_index=True)

    # Profilo sul meridiano piatto
    _grafico_profilo(r_fl, e_fl, res["Rb_flat_mm"], res["zo_diam"], res["td"], "Lente flat")

    with st.expander("📋 Schema per il laboratorio"):
        st.code(_schema_laboratorio(res, r_fl, e_fl, medico, paziente), language=None)
    if _fluor:
        with st.expander("🔬 Fluoresceinogramma simulato (meridiano flat)"):
            ast_D_val = abs(res.get("toricity_D", 0))
            _fluor("ast", r_fl, res["Rb_flat_mm"], res.get("zo_diam",5.6),
                   e_fl, ast_D=ast_D_val, key_prefix="fluor_ast", show_controls=False)


def _mostra_risultati_presbiopia(res, r0, e, medico, paziente):
    st.success(f"Calcolo presbiopia — Strategia: **{res['strategia_consigliata']}**")
    st.info(res["note_add"])

    p1,p2,p3,p4 = st.columns(4)
    p1.metric("Rb (mm)", f"{res['Rb_mm']:.3f}")
    p2.metric("Rb (D)",  f"{res['Rb_D']:.2f}")
    p3.metric("Q corneale", f"{res['Q_corneale']:.3f}")
    p4.metric("Q target ZO", f"{res['Q_target']:.3f}")

    q1,q2,q3,q4 = st.columns(4)
    q1.metric("e ZO target", f"{res['e_target']:.3f}")
    q2.metric("ADD correggibile", f"+{res['add_correggibile_D']:.2f} D")
    q3.metric("ADD residuo", f"+{res['add_residuo_D']:.2f} D",
              delta_color="inverse" if res["add_residuo_D"] > 0 else "normal")
    q4.metric("ZO / pupilla fotopica", f"{res['area_zo_pct_pupilla']:.0f}%")

    if res["add_residuo_D"] > 0.25:
        st.warning(
            f"⚠️ ADD residua +{res['add_residuo_D']:.2f} D non correggibile con multifocale puro. "
            "Valutare monovisione (–0.50 D occhio non dominante).")

    st.markdown("**Zone**")
    fl_data = [{"Zona": fl["nome"], "r (mm)": fl["raggio_mm"],
                "D": fl["diottrie"], "Ø (mm)": fl["diametro"]}
               for fl in res.get("flange", [])]
    if fl_data:
        st.dataframe(pd.DataFrame(fl_data), use_container_width=True, hide_index=True)

    _grafico_profilo(r0, e, res["Rb_mm"], res["zo_diam"], res["td"], "Lente presbiopia")

    with st.expander("📋 Schema per il laboratorio"):
        st.code(_schema_laboratorio(res, r0, e, medico, paziente), language=None)
    if _fluor:
        with st.expander("🔬 Fluoresceinogramma simulato"):
            Q_v = res.get("Q_target", -0.45)
            _fluor("presb", r0, res["Rb_mm"], res.get("zo_diam",5.6), e,
                   Q_presb=Q_v, key_prefix="fluor_presb", show_controls=False)
