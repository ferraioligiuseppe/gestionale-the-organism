from __future__ import annotations

ESA_DATA = {
  "0.50": [
    {"K": 7.27, "BOZD": 5.0, "d1": 6.5, "d2": 8.3, "d3": 9.6, "d4": 10.0, "TD": 10.5, "r0": 7.59, "r1": 7.27, "r2": 7.86, "r3": 8.83, "r4": 10.26, "r5": 14.26, "PWR": 0.75},
    {"K": 7.45, "BOZD": 5.0, "d1": 6.5, "d2": 8.3, "d3": 9.6, "d4": 10.0, "TD": 10.5, "r0": 7.74, "r1": 7.45, "r2": 8.02, "r3": 8.97, "r4": 10.38, "r5": 14.38, "PWR": 0.75},
    {"K": 7.62, "BOZD": 5.0, "d1": 6.5, "d2": 8.3, "d3": 9.6, "d4": 10.0, "TD": 10.5, "r0": 7.89, "r1": 7.62, "r2": 8.17, "r3": 9.11, "r4": 10.5, "r5": 14.5, "PWR": 0.75},
    {"K": 7.8, "BOZD": 5.0, "d1": 6.5, "d2": 8.3, "d3": 9.6, "d4": 10.0, "TD": 10.5, "r0": 8.04, "r1": 7.8, "r2": 8.33, "r3": 9.26, "r4": 10.63, "r5": 14.63, "PWR": 0.75},
    {"K": 7.97, "BOZD": 5.0, "d1": 6.5, "d2": 8.3, "d3": 9.6, "d4": 10.0, "TD": 10.5, "r0": 8.19, "r1": 7.97, "r2": 8.48, "r3": 9.4, "r4": 10.75, "r5": 14.75, "PWR": 0.75},
    {"K": 8.14, "BOZD": 5.0, "d1": 6.5, "d2": 8.3, "d3": 9.6, "d4": 10.0, "TD": 10.5, "r0": 8.34, "r1": 8.14, "r2": 8.63, "r3": 9.54, "r4": 10.87, "r5": 14.87, "PWR": 0.75}
  ],
  "1.00": [
    {"K": 7.27, "BOZD": 5.0, "d1": 6.5, "d2": 8.3, "d3": 9.6, "d4": 10.0, "TD": 10.5, "r0": 7.64, "r1": 7.27, "r2": 7.86, "r3": 8.83, "r4": 10.26, "r5": 14.26, "PWR": 0.75},
    {"K": 7.45, "BOZD": 5.0, "d1": 6.5, "d2": 8.3, "d3": 9.6, "d4": 10.0, "TD": 10.5, "r0": 7.79, "r1": 7.45, "r2": 8.02, "r3": 8.97, "r4": 10.38, "r5": 14.38, "PWR": 0.75},
    {"K": 7.62, "BOZD": 5.0, "d1": 6.5, "d2": 8.3, "d3": 9.6, "d4": 10.0, "TD": 10.5, "r0": 7.94, "r1": 7.62, "r2": 8.17, "r3": 9.11, "r4": 10.5, "r5": 14.5, "PWR": 0.75},
    {"K": 7.8, "BOZD": 5.0, "d1": 6.5, "d2": 8.3, "d3": 9.6, "d4": 10.0, "TD": 10.5, "r0": 8.09, "r1": 7.8, "r2": 8.33, "r3": 9.26, "r4": 10.63, "r5": 14.63, "PWR": 0.75},
    {"K": 7.97, "BOZD": 5.0, "d1": 6.5, "d2": 8.3, "d3": 9.6, "d4": 10.0, "TD": 10.5, "r0": 8.24, "r1": 7.97, "r2": 8.48, "r3": 9.4, "r4": 10.75, "r5": 14.75, "PWR": 0.75},
    {"K": 8.14, "BOZD": 5.0, "d1": 6.5, "d2": 8.3, "d3": 9.6, "d4": 10.0, "TD": 10.5, "r0": 8.39, "r1": 8.14, "r2": 8.63, "r3": 9.54, "r4": 10.87, "r5": 14.87, "PWR": 0.75}
  ],
  "2.00": [
    {"K": 7.27, "BOZD": 5.2, "d1": 6.7, "d2": 8.4, "d3": 9.7, "d4": 10.1, "TD": 10.6, "r0": 7.74, "r1": 7.27, "r2": 7.92, "r3": 8.92, "r4": 10.34, "r5": 14.34, "PWR": 0.75},
    {"K": 7.45, "BOZD": 5.2, "d1": 6.7, "d2": 8.4, "d3": 9.7, "d4": 10.1, "TD": 10.6, "r0": 7.89, "r1": 7.45, "r2": 8.08, "r3": 9.06, "r4": 10.46, "r5": 14.46, "PWR": 0.75},
    {"K": 7.62, "BOZD": 5.2, "d1": 6.7, "d2": 8.4, "d3": 9.7, "d4": 10.1, "TD": 10.6, "r0": 8.04, "r1": 7.62, "r2": 8.23, "r3": 9.2, "r4": 10.58, "r5": 14.58, "PWR": 0.75},
    {"K": 7.8, "BOZD": 5.2, "d1": 6.7, "d2": 8.4, "d3": 9.7, "d4": 10.1, "TD": 10.6, "r0": 8.19, "r1": 7.8, "r2": 8.39, "r3": 9.35, "r4": 10.71, "r5": 14.71, "PWR": 0.75},
    {"K": 7.97, "BOZD": 5.2, "d1": 6.7, "d2": 8.4, "d3": 9.7, "d4": 10.1, "TD": 10.6, "r0": 8.34, "r1": 7.97, "r2": 8.54, "r3": 9.49, "r4": 10.83, "r5": 14.83, "PWR": 0.75},
    {"K": 8.14, "BOZD": 5.2, "d1": 6.7, "d2": 8.4, "d3": 9.7, "d4": 10.1, "TD": 10.6, "r0": 8.49, "r1": 8.14, "r2": 8.69, "r3": 9.63, "r4": 10.95, "r5": 14.95, "PWR": 0.75}
  ],
  "3.00": [
    {"K": 7.27, "BOZD": 5.6, "d1": 7.0, "d2": 8.6, "d3": 9.8, "d4": 10.2, "TD": 10.8, "r0": 7.84, "r1": 7.27, "r2": 7.98, "r3": 9.0, "r4": 10.42, "r5": 14.42, "PWR": 0.75},
    {"K": 7.45, "BOZD": 5.6, "d1": 7.0, "d2": 8.6, "d3": 9.8, "d4": 10.2, "TD": 10.8, "r0": 7.99, "r1": 7.45, "r2": 8.14, "r3": 9.14, "r4": 10.54, "r5": 14.54, "PWR": 0.75},
    {"K": 7.62, "BOZD": 5.6, "d1": 7.0, "d2": 8.6, "d3": 9.8, "d4": 10.2, "TD": 10.8, "r0": 8.14, "r1": 7.62, "r2": 8.29, "r3": 9.28, "r4": 10.66, "r5": 14.66, "PWR": 0.75},
    {"K": 7.8, "BOZD": 5.6, "d1": 7.0, "d2": 8.6, "d3": 9.8, "d4": 10.2, "TD": 10.8, "r0": 8.29, "r1": 7.8, "r2": 8.45, "r3": 9.43, "r4": 10.79, "r5": 14.79, "PWR": 0.75},
    {"K": 7.97, "BOZD": 5.6, "d1": 7.0, "d2": 8.6, "d3": 9.8, "d4": 10.2, "TD": 10.8, "r0": 8.44, "r1": 7.97, "r2": 8.6, "r3": 9.57, "r4": 10.91, "r5": 14.91, "PWR": 0.75},
    {"K": 8.14, "BOZD": 5.6, "d1": 7.0, "d2": 8.6, "d3": 9.8, "d4": 10.2, "TD": 10.8, "r0": 8.59, "r1": 8.14, "r2": 8.75, "r3": 9.71, "r4": 11.03, "r5": 15.03, "PWR": 0.75}
  ]
}


def nearest_sheet_key(power_abs: float) -> str:
    vals = sorted(float(k) for k in ESA_DATA.keys())
    target = max(min(round(abs(power_abs) * 4) / 4, max(vals)), min(vals))
    nearest = min(vals, key=lambda x: abs(x - target))
    return f"{nearest:.2f}"


def interp_row_by_k(rows, k):
    rows = sorted(rows, key=lambda r: r["K"])
    if k <= rows[0]["K"]:
        return dict(rows[0])
    if k >= rows[-1]["K"]:
        return dict(rows[-1])
    for a, b in zip(rows[:-1], rows[1:]):
        if a["K"] <= k <= b["K"]:
            t = 0 if b["K"] == a["K"] else (k - a["K"]) / (b["K"] - a["K"])
            out = {}
            for key in a.keys():
                out[key] = round(a[key] + t * (b[key] - a[key]), 3)
            return out
    return dict(rows[0])


def esa_lookup(k_med: float, power_abs: float):
    sk = nearest_sheet_key(abs(power_abs))
    rows = ESA_DATA.get(sk)
    if not rows:
        return None
    res = interp_row_by_k(rows, float(k_med))
    res["sheet_power"] = -abs(float(sk))
    return res


def toffoli_calc(k_med: float, target_myopia: float):
    target = abs(target_myopia) if target_myopia else 1.0
    r0 = round(k_med + 0.22 + 0.04 * target, 2)
    return {
        "RB": r0,
        "ZO": 6.0 if target <= 3 else 5.6,
        "r1": round(r0 - 0.85, 2),
        "r2": round(r0 - 0.40, 2),
        "r3": round(r0 - 0.05, 2),
        "r4": round(r0 + 1.55, 2),
        "r5": round(r0 + 1.85, 2),
        "d1": 7.2,
        "d2": 8.6,
        "d3": 9.8,
        "d4": 10.2,
        "TD": 10.8,
        "PWR": 0.75,
    }


def hyperopia_calc(k_med: float, hyper_d: float):
    rb = round(k_med - 0.08 - 0.03 * abs(hyper_d), 2)
    return {
        "RB": rb,
        "ZO": 5.0,
        "r1": round(rb + 0.65, 2),
        "r2": round(rb + 1.05, 2),
        "r3": round(rb + 1.40, 2),
        "r4": round(rb + 2.00, 2),
        "r5": round(rb + 2.35, 2),
        "d1": 6.8,
        "d2": 7.8,
        "d3": 9.0,
        "d4": 10.0,
        "TD": 10.8,
        "PWR": 0.50,
    }


def astig_calc(k_flat: float, k_steep: float, cyl: float):
    rb_flat = round(k_flat + 0.10, 2)
    rb_steep = round(k_steep + 0.10, 2)
    return {
        "RB_flat": rb_flat,
        "RB_steep": rb_steep,
        "ZO": 5.6,
        "d1": 7.2,
        "d2": 8.2,
        "d3": 9.6,
        "d4": 10.0,
        "TD": 10.8,
        "PWR": 0.50,
        "raccomandazione": "Design torico / AS TI consigliato",
    }


def presbyopia_calc(k_med: float, add_d: float):
    rb = round(k_med + 0.05, 2)
    q = round(-0.35 - max(abs(add_d) - 1.0, 0) * 0.10, 2)
    return {
        "RB": rb,
        "ZO": 5.6,
        "Q_target": q,
        "r1": round(rb - 0.45, 2),
        "r2": round(rb + 0.05, 2),
        "r3": round(rb + 0.55, 2),
        "r4": round(rb + 1.35, 2),
        "r5": round(rb + 1.95, 2),
        "d1": 7.2,
        "d2": 8.2,
        "d3": 9.6,
        "d4": 10.0,
        "TD": 10.8,
        "PWR": 0.50,
    }


def estimate_clearance(k_med: float, ordine: dict, design: str) -> dict:
    rb = ordine.get("r0", ordine.get("RB", ordine.get("RB_flat", k_med)))
    zo = ordine.get("BOZD", ordine.get("ZO", 5.6))
    td = ordine.get("TD", 10.8)
    sag_delta = (float(rb) - float(k_med)) * 1000.0
    base_central = 110.0 + sag_delta * 0.80
    if design == "hyper":
        base_central += 30.0
    if design == "presb":
        base_central += 20.0
    if design == "toric":
        base_central += 10.0
    central = round(base_central, 1)
    reverse_zone = round(max(40.0, central + 55.0), 1)
    landing = round(max(20.0, central - 35.0), 1)
    edge = round(max(15.0, landing - 5.0), 1)

    if central < 70:
        pattern = "touch centrale"
        valutazione = "lente stretta / appoggio centrale"
    elif central > 180:
        pattern = "pooling centrale marcato"
        valutazione = "clearance eccessiva"
    else:
        pattern = "clearance centrale fisiologica"
        valutazione = "assetto centrale adeguato"

    return {
        "central_um": central,
        "reverse_um": reverse_zone,
        "landing_um": landing,
        "edge_um": edge,
        "pattern": pattern,
        "valutazione": valutazione,
        "zo": zo,
        "td": td,
    }
