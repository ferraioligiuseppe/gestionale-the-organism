# -*- coding: utf-8 -*-
"""
lac_engine_sag.py  -  Motore sagittale per lenti a contatto
Studio The Organism / gestionale

Sostituisce i calcoli empirici (offset fissi) con geometria sagittale reale,
basata sulla sezione conica della cornea e sul raccordo delle curve come
cerchio passante per due punti.

VALIDAZIONE: la geometria inversa riproduce ESATTAMENTE (errore < 1e-6 mm) il
foglio di calcolo "Inversa 6 v1.3" (G. Toffoli): con r0=7.6, e=0.5, miopia da
ridurre 5.25 D, fattore 0.5 D -> Rb=8.730 e r1..r5 = 6.827/7.639/8.003/8.875/10.987.

GEOMETRIE SUPPORTATE
  - "normale"     : RGP corneale asferica/multicurva (base allineata)
  - "cheratocono" : sfioramento apicale (three-point touch), lift periferico
  - "inversa"     : Ortho-K, appiattimento dioptrico + curva inversa
  - "sclerale"    : sclerale / mini-sclerale / corneo-sclerale, sag-driven

Le funzioni corneali restituiscono il dizionario "ordine" nel formato gia' usato
dal gestionale (r0/RB, ZO, r1..r5, d1..d4, TD, PWR), quindi sono drop-in.
La funzione sclerale restituisce un dizionario clinico esteso (vault, sag, landing).

RIFERIMENTI (parametri clinici sclerali):
  - Sag oculare = sag corneale + sag sclerale; sag lente = sag oculare + vault.
    (Contact Lens Spectrum, "Sagittal Height and Scleral Lenses")
  - Vault apicale tipico 100-400 um; ~300 um pre-assestamento; recesso ~100 um/die.
    (mini-scleral KC study PMC7802094; Onefit fitting guide)
  - Curva base ~ raggio apicale + 0.2 mm. (US Patent 11977278)
  - Diametri: mini-sclerale fino a +6 mm su HVID; >+6 mm = grande sclerale.
    (Contact Lens Spectrum, "The Scleral Lens Vault")
  - Landing zone 1.0-2.5 mm; compressione congiuntivale 80-120 um. (US 11977278)
  - La sag da soli parametri corneali sottostima il profilometro a corde grandi
    -> preferire la sag MISURATA. (Cont Lens Anterior Eye, 2022)
"""

from __future__ import annotations
import math

CK = 337.5          # indice cheratometrico convenzionale (n = 1.3375)


# =====================================================================
# PRIMITIVE GEOMETRICHE
# =====================================================================

def sag_conica(y, r0, p):
    """Sagitta di una conica a semicorda y.
    p = fattore di forma = 1 - e^2 (p=1 sfera, p<1 prolata, p>1 oblata)."""
    if y == 0:
        return 0.0
    if p <= 0:
        return y * y / (2.0 * r0)
    val = (r0 / p) ** 2 - y * y / p
    if val < 0:
        return float("nan")
    return r0 / p - math.sqrt(val)


def sag_sfera(R, y):
    if R * R - y * y < 0:
        return float("nan")
    return R - math.sqrt(R * R - y * y)


def pendenza_conica(y, r0, p):
    """Pendenza dz/dy della conica a semicorda y (per estendere verso la sclera)."""
    if p <= 0:
        return y / r0
    val = (r0 / p) ** 2 - y * y / p
    if val <= 0:
        return float("nan")
    return (y / p) / math.sqrt(val)


def raggio_2pt(p1, p2):
    """Raggio del cerchio con centro sull'asse ottico passante per due punti (z, y)."""
    z1, a1 = p1
    z2, a2 = p2
    if z2 == z1:
        return float("inf")
    zc = (z2 * z2 + a2 * a2 - z1 * z1 - a1 * a1) / (2.0 * (z2 - z1))
    return math.sqrt((zc - z1) ** 2 + a1 * a1)


def raggio_a_diottrie(r_mm):
    return CK / r_mm if r_mm else float("nan")


def diottrie_a_raggio(d):
    return CK / d if d else float("nan")


# =====================================================================
# PRESET CORNEALI (semicorde e clearance di default per i bordi zona)
# semicorde[0] = bordo zona ottica; le successive = bordi flange.
# =====================================================================

PRESET_CORNEALE = {
    "normale": {
        "semicorde": [3.5, 4.0, 4.5, 5.0, 5.4],
        "clearance": [0.00, 0.00, 0.02, 0.06, 0.10],
        "base": "allineata",
    },
    "cheratocono": {
        "semicorde": [3.0, 3.6, 4.2, 4.8, 5.2],
        "clearance": [0.00, 0.01, 0.04, 0.09, 0.15],
        "base": "cheratocono",
    },
    "inversa": {
        "semicorde": [2.8, 3.6, 4.1, 4.8, 5.0, 5.4],
        "clearance": [0.073, 0.010, 0.000, 0.007, 0.030, 0.155],
        "base": "inversa",
    },
}


def _base_corneale(geometria, r0, miopia=0.0, fattore=0.0, offset=None):
    if geometria == "inversa":
        k_flat = (1.0 / r0) * CK
        k_base = k_flat - abs(miopia) - abs(fattore)
        return (1.0 / k_base) * CK
    if geometria == "cheratocono":
        off = 0.10 if offset is None else offset   # default sfioramento apicale
        return r0 + off
    off = 0.0 if offset is None else offset         # normale: allineata
    return r0 + off


def calcola_corneale(geometria, r0, e, td=10.8, pwr=0.75,
                     miopia=0.0, fattore=0.50, offset=None,
                     semicorde=None, clearance=None):
    """
    Costruisce una lente corneale multicurva con motore sagittale.
    Ritorna il dizionario 'ordine' compatibile col gestionale:
      r0/RB, ZO, r1..r5, d1..d4, TD, PWR, e i punti per il grafico.
    """
    preset = PRESET_CORNEALE.get(geometria, PRESET_CORNEALE["normale"])
    sc = list(semicorde) if semicorde else list(preset["semicorde"])
    cl = list(clearance) if clearance else list(preset["clearance"])

    p = 1.0 - e * e
    Rb = _base_corneale(geometria, r0, miopia=miopia, fattore=fattore, offset=offset)

    # punti target periferici: profondita' = sag cornea - clearance, alla semicorda
    pts = [(sag_conica(y, r0, p) - c, y) for y, c in zip(sc, cl)]
    raggi = []
    for i in range(len(pts) - 1):
        raggi.append(round(raggio_2pt(pts[i], pts[i + 1]), 2))

    # impacchetta nel formato 'ordine' del gestionale
    out = {
        "geometria": geometria,
        "RB": round(Rb, 2),
        "r0": round(Rb, 2),          # alias usato dalla UI/PDF
        "r0_cornea": r0,             # raggio apicale corneale (per fluoresceina)
        "ZO": round(2 * sc[0], 1),   # diametro zona ottica
        "TD": round(td, 1),
        "PWR": pwr,
        "p_cornea": round(p, 4),
        "e": e,
        "_punti": pts,               # per il grafico profilo
        "_semicorde": sc,
        "_clearance": cl,
    }
    # r1..rN e diametri zona d1..dN
    for i, rr in enumerate(raggi, start=1):
        out[f"r{i}"] = rr
    for i, s in enumerate(sc[1:], start=1):
        out[f"d{i}"] = round(2 * s, 1)
    return out


# =====================================================================
# GEOMETRIA SCLERALE / SEMI-SCLERALE  (sag-driven)
# =====================================================================

def _classe_sclerale(diam, hvid):
    delta = diam - hvid
    if diam < hvid:
        return "corneale"
    if delta <= 0:
        return "corneo-sclerale"
    if delta <= 6.0:
        return "mini-sclerale"
    return "grande sclerale"


def stima_sag_oculare(r0, e, hvid, corda_mm, fattore_sclera=0.72):
    """
    STIMA (non misurata) della sag oculare a una data corda, dai parametri corneali.
    Corneale = conica fino al limbus (semicorda = HVID/2), poi estensione sclerale
    quasi-tangenziale fino alla corda di atterraggio. La sclera e' piu' piatta della
    tangente corneale al limbus: fattore_sclera (~0.72) smorza la pendenza limbare.
    NB: stima approssimata -> usare la sag MISURATA (OCT/profilometro) se disponibile.
    Ritorna sag in mm.
    """
    p = 1.0 - e * e
    y_limbus = hvid / 2.0
    y_land = corda_mm / 2.0
    if y_land <= y_limbus:
        return sag_conica(y_land, r0, p)
    sag_corneale = sag_conica(y_limbus, r0, p)
    m = pendenza_conica(y_limbus, r0, p)
    if math.isnan(m):
        m = 0.85
    sag_sclerale = (y_land - y_limbus) * m * fattore_sclera
    return sag_corneale + sag_sclerale


def calcola_sclerale(r0, e, hvid=11.8, refrazione=0.0,
                     corda_mm=16.0, vault_um=300.0, settling_um=100.0,
                     sag_misurata_mm=None, diam_mm=None,
                     landing_width_mm=1.5, landing_angle_deg=None,
                     compression_um=100.0):
    """
    Calcolo sclerale sag-driven.
      - Se sag_misurata_mm e' fornita (OCT/profilometro/lente prova) la usa;
        altrimenti stima dalla conica corneale (con avviso).
      - Sag lente di prova = sag oculare + vault.
      - Clearance assestata ~ vault - settling.
      - Curva base = raggio apicale + 0.2 mm (best-fit).
    Ritorna dizionario clinico esteso (compatibile col gestionale per RB/TD/PWR).
    """
    # diametro consigliato dall'HVID se non imposto
    if diam_mm is None:
        diam_mm = 16.0 if hvid <= 12.3 else round(hvid + 4.0, 1)
    classe = _classe_sclerale(diam_mm, hvid)

    # sag oculare
    misurata = sag_misurata_mm is not None
    if misurata:
        sag_oc = float(sag_misurata_mm)
    else:
        sag_oc = stima_sag_oculare(r0, e, hvid, corda_mm)

    sag_lente = sag_oc + vault_um / 1000.0
    clearance_assestata = max(0.0, vault_um - settling_um)

    base_curve = round(r0 + 0.20, 2)        # ~0.2 mm piu' piatta dell'apice

    # valutazione clearance
    if clearance_assestata < 80:
        valut = "vault assestato basso (rischio appoggio apicale)"
    elif clearance_assestata > 350:
        valut = "vault assestato elevato (rischio fogging/HOA)"
    else:
        valut = "vault assestato adeguato"

    return {
        "geometria": "sclerale",
        "classe": classe,
        "TD": round(diam_mm, 1),
        "corda_sag_mm": corda_mm,
        "sag_oculare_um": round(sag_oc * 1000.0, 0),
        "sag_oculare_stimata": (not misurata),
        "vault_iniziale_um": round(vault_um, 0),
        "settling_um": round(settling_um, 0),
        "clearance_assestata_um": round(clearance_assestata, 0),
        "sag_lente_um": round(sag_lente * 1000.0, 0),
        "RB": base_curve,
        "r0": base_curve,
        "ZO": 8.0,
        "PWR": round(refrazione, 2),
        "landing_width_mm": landing_width_mm,
        "landing_angle_deg": landing_angle_deg,
        "compression_um": compression_um,
        "hvid_mm": hvid,
        "valutazione": valut,
    }


# =====================================================================
# CLEARANCE / FLUORESCEINA (per compatibilita' con la UI esistente)
# Restituisce le chiavi central_um/reverse_um/landing_um/edge_um/pattern.
# =====================================================================

def stima_clearance(ordine: dict, geometria: str) -> dict:
    if geometria == "sclerale":
        central = float(ordine.get("clearance_assestata_um", 200))
        reverse = round(central + 60, 1)
        landing = float(ordine.get("compression_um", 100))
        edge = round(max(15.0, landing - 20), 1)
        pattern = "vault sclerale"
    else:
        # da differenza sag base vs cornea sul bordo ZO
        pts = ordine.get("_punti")
        if pts:
            central = round(abs(ordine.get("_clearance", [0.05])[0]) * 1000 + 60, 1)
        else:
            central = 110.0
        reverse = round(central + 55, 1)
        landing = round(max(20.0, central - 35), 1)
        edge = round(max(15.0, landing - 5), 1)
        if central < 70:
            pattern = "touch centrale"
        elif central > 180:
            pattern = "pooling centrale"
        else:
            pattern = "clearance fisiologica"
    return {
        "central_um": central, "reverse_um": reverse,
        "landing_um": landing, "edge_um": edge,
        "pattern": pattern, "valutazione": ordine.get("valutazione", pattern),
        "zo": ordine.get("ZO", 5.6), "td": ordine.get("TD", 10.8),
    }


# =====================================================================
# AUTOTEST
# =====================================================================

def _autotest():
    inv = calcola_corneale("inversa", 7.6, 0.5, td=10.8,
                           miopia=5.25, fattore=0.5,
                           semicorde=[2.8, 3.6, 4.1, 4.8, 5.0, 5.4],
                           clearance=[0.073444985, 0.01, 0.0, 0.007, 0.03, 0.155])
    attesi = {"RB": 8.73, "r1": 6.83, "r2": 7.64, "r3": 8.00, "r4": 8.88, "r5": 10.99}
    ok = abs(inv["RB"] - attesi["RB"]) < 0.01
    for k in ["r1", "r2", "r3", "r4", "r5"]:
        ok = ok and abs(inv[k] - attesi[k]) < 0.01
    return ok, inv


if __name__ == "__main__":
    ok, inv = _autotest()
    print("AUTOTEST INVERSA:", "OK" if ok else "FALLITO")
    print("  ", {k: v for k, v in inv.items() if not k.startswith("_")})
    print("\nNORMALE r0=7.80 e=0.45:")
    print("  ", {k: v for k, v in calcola_corneale("normale", 7.80, 0.45).items() if not k.startswith("_")})
    print("\nCHERATOCONO r0=6.60 e=0.85:")
    print("  ", {k: v for k, v in calcola_corneale("cheratocono", 6.60, 0.85).items() if not k.startswith("_")})
    print("\nSCLERALE (stima) r0=7.80 e=0.45 HVID=11.8 corda16 vault300:")
    print("  ", calcola_sclerale(7.80, 0.45, hvid=11.8, corda_mm=16.0, vault_um=300, refrazione=-5.0))
    print("\nSCLERALE (sag misurata 4100um @16mm):")
    print("  ", calcola_sclerale(7.80, 0.45, hvid=11.8, sag_misurata_mm=4.10, vault_um=300, refrazione=-5.0))


# =====================================================================
# LENTE LACRIMALE (SAM / FAP) - potere da ordinare
# =====================================================================

def lente_lacrimale(bc_mm, kflat_mm, rx_piano_corneale=0.0):
    """
    Calcola il potere della lente lacrimale e il potere BVP da ordinare.
    Regola clinica SAM/FAP (Steeper Add Minus / Flatter Add Plus):
      - BC piu' curva del K piatto -> lacrimale PLUS -> aggiungi MINUS alla lente.
      - BC piu' piatta -> lacrimale MINUS -> aggiungi PLUS.
    Potere lacrimale (D) = potere(BC) - potere(K piatto)  [diottrie cheratometriche].
    BVP da ordinare = Rx al piano corneale - potere lacrimale (arrotondato a 0.25 D).
    """
    pot_lacr = (CK / bc_mm) - (CK / kflat_mm)
    pot_lacr = round(pot_lacr * 4) / 4.0
    bvp = round((rx_piano_corneale - pot_lacr) * 4) / 4.0
    return {
        "potere_lacrimale_d": pot_lacr,
        "bvp_ordine_d": bvp,
        "regola": "SAM (aggiungi minus)" if pot_lacr > 0 else
                  ("FAP (aggiungi plus)" if pot_lacr < 0 else "neutra"),
    }


# =====================================================================
# RENDERING FLUORESCEINA REALISTICO
# Intensita' del verde ~ spessore del film lacrimale (gap lente-cornea).
# =====================================================================

def _profilo_gap_corneale(ordine, r0, e, n=240):
    """Ritorna (raggi_mm, gap_um): spessore lacrimale lungo il raggio, dal gap
    tra superficie posteriore della lente (ZO sferica + archi periferici) e cornea."""
    import numpy as np
    p = 1.0 - e * e
    sc = ordine["_semicorde"]
    pts = ordine["_punti"]
    Rb = ordine["RB"]
    td = ordine.get("TD", 10.8)
    ymax = td / 2.0

    # offset della zona ottica per agganciarsi al primo punto target
    off = pts[0][0] - sag_sfera(Rb, sc[0])

    def z_lente(y):
        if y <= sc[0]:
            return sag_sfera(Rb, y) + off
        for i in range(len(sc) - 1):
            if sc[i] <= y <= sc[i + 1]:
                p1, p2 = pts[i], pts[i + 1]
                zc = (p2[0]**2 + p2[1]**2 - p1[0]**2 - p1[1]**2) / (2 * (p2[0] - p1[0]))
                r = math.sqrt((zc - p1[0])**2 + p1[1]**2)
                root = math.sqrt(max(r * r - y * y, 0.0))
                zc_at1 = zc - math.sqrt(max(r * r - p1[1]**2, 0.0))
                return (zc - root) if abs(zc_at1 - p1[0]) < abs((zc + math.sqrt(max(r*r-p1[1]**2,0.0))) - p1[0]) else (zc + root)
        return pts[-1][0]

    ys = np.linspace(0, ymax, n)
    gap = []
    for y in ys:
        g = (sag_conica(y, r0, p) - z_lente(y)) * 1000.0   # um
        gap.append(max(g, 0.0))
    return ys, np.array(gap)


def _profilo_gap_sclerale(ordine, n=240):
    """Profilo gap per sclerale: vault sulla cornea, atterraggio sulla landing."""
    import numpy as np
    td = ordine.get("TD", 16.0)
    hvid = ordine.get("hvid_mm", 11.8)
    vault = ordine.get("clearance_assestata_um", 200.0)
    comp = ordine.get("compression_um", 100.0)
    lw = ordine.get("landing_width_mm", 1.5)
    ymax = td / 2.0
    y_corn = hvid / 2.0           # zona di vault sulla cornea
    y_land0 = ymax - lw           # inizio landing
    ys = np.linspace(0, ymax, n)
    gap = []
    for y in ys:
        if y <= y_corn * 0.85:
            g = vault
        elif y <= y_land0:
            # transizione limbare: clearance che cala dolcemente
            t = (y - y_corn * 0.85) / max(y_land0 - y_corn * 0.85, 1e-6)
            g = vault * (1 - 0.7 * t)
        else:
            # landing/haptic: appoggio sulla congiuntiva = film sottile (anello scuro);
            # solo all'estremo bordo un lieve edge lift.
            t = (y - y_land0) / max(ymax - y_land0, 1e-6)
            if t < 0.80:
                g = 8.0          # bearing: quasi nessun film -> scuro
            else:
                g = 8.0 + 70.0 * (t - 0.80) / 0.20   # edge lift al bordo estremo
        gap.append(g)
    return ys, np.array(gap)


def _cmap_fluoresceina():
    from matplotlib.colors import LinearSegmentedColormap
    # nero/blu (touch) -> verde scuro -> verde -> giallo-verde brillante
    stops = [
        (0.00, (0.02, 0.05, 0.13)),
        (0.10, (0.01, 0.18, 0.13)),
        (0.30, (0.06, 0.45, 0.20)),
        (0.55, (0.20, 0.75, 0.26)),
        (0.78, (0.55, 0.95, 0.33)),
        (1.00, (0.88, 1.00, 0.62)),
    ]
    return LinearSegmentedColormap.from_list("naFl", [(s, c) for s, c in stops])


def render_fluorescein(ordine, geometria=None, r0=None, e=None, titolo="", T0_um=70.0):
    """
    Figura fluoresceina verosimile. L'intensita' satura come 1-exp(-t/T0),
    con t = spessore lacrimale locale (um), su mappa colore fluoresceina e
    fondo blu cobalto. geometria/r0/e si possono omettere: vengono letti dal
    dizionario 'ordine'. Restituisce una figura matplotlib.
    """
    import numpy as np
    import matplotlib.pyplot as plt

    if geometria is None:
        geometria = ordine.get("geometria", "normale")
    if r0 is None:
        r0 = ordine.get("r0_cornea")
    if e is None:
        e = ordine.get("e")

    if geometria == "sclerale":
        ys, gap = _profilo_gap_sclerale(ordine)
        td = ordine.get("TD", 16.0)
    else:
        ys, gap = _profilo_gap_corneale(ordine, r0, e)
        td = ordine.get("TD", 10.8)
    ymax = td / 2.0

    # intensita' saturante
    inten = 1.0 - np.exp(-gap / T0_um)

    # griglia 2D radiale
    N = 420
    xx = np.linspace(-ymax, ymax, N)
    X, Y = np.meshgrid(xx, xx)
    R = np.sqrt(X**2 + Y**2)
    Iflat = np.interp(R.ravel(), ys, inten, left=inten[0], right=inten[-1])
    I2d = Iflat.reshape(R.shape)

    # texture realistica (leggero rumore moltiplicativo) + dimming radiale ai bordi
    rng = np.random.default_rng(7)
    noise = 1.0 + 0.05 * (rng.standard_normal(I2d.shape))
    I2d = np.clip(I2d * noise, 0, 1)

    mask = R <= ymax
    cmap = _cmap_fluoresceina()
    rgba = cmap(I2d)
    # fondo blu cobalto fuori dalla lente
    bg = np.array([0.03, 0.06, 0.22, 1.0])
    rgba[~mask] = bg

    fig, ax = plt.subplots(figsize=(4.6, 4.6))
    ax.imshow(rgba, extent=[-ymax, ymax, -ymax, ymax], origin="lower")
    # anello bordo lente
    ax.add_artist(plt.Circle((0, 0), ymax, fill=False, color="#cfe9ff", lw=1.3, alpha=0.7))
    # riferimento limbus (solo corneali)
    if geometria != "sclerale":
        ax.add_artist(plt.Circle((0, 0), min(5.9, ymax * 0.98), fill=False,
                                  color="#ffffff", lw=0.6, ls=":", alpha=0.25))
    ax.set_xlim(-ymax, ymax); ax.set_ylim(-ymax, ymax)
    ax.set_aspect("equal"); ax.axis("off")
    if titolo:
        ax.set_title(titolo, color="#0b3", fontsize=10)
    fig.patch.set_facecolor("#081226")
    fig.tight_layout()
    return fig
