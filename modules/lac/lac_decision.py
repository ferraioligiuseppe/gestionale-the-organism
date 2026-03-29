from __future__ import annotations

from .lac_engine import (
    esa_lookup,
    toffoli_calc,
    hyperopia_calc,
    astig_calc,
    presbyopia_calc,
    estimate_clearance,
)


def build_curves(
    categoria,
    difetto,
    algoritmo,
    modello_prod,
    rx_sfera,
    rx_cil,
    rx_asse,
    rx_add,
    k1,
    k2,
    hvid,
    pupilla,
    target_orthok,
    e_val,
):
    k1 = float(k1)
    k2 = float(k2)
    k_med = round((k1 + k2) / 2, 2)
    cyl_sig = abs(rx_cil) >= 0.75
    modello = (
        modello_prod
        if modello_prod != "Automatico"
        else ("C6 OBL MF" if abs(rx_add) >= 0.75 else ("C6 AS TI" if cyl_sig else "C6 OBL"))
    )

    if categoria == "Ortho-K / Inversa" and algoritmo == "ESA 002" and rx_sfera < 0:
        esa = esa_lookup(k_med, abs(target_orthok) if target_orthok else abs(rx_sfera))
        fluor = estimate_clearance(k_med, esa, "mio")
        return {
            "modello_prod": modello if modello_prod != "Automatico" else "C6 OBL",
            "sottotipo": "ESA Ortho-6",
            "lente_bc_mm": esa["r0"],
            "lente_rb_mm": esa["r0"],
            "lente_diam_mm": esa["TD"],
            "lente_potere_d": esa["PWR"],
            "lente_cilindro_d": 0.0,
            "lente_asse_cil": None,
            "lente_add_d": 0.0,
            "ordine": esa,
            "fluor": fluor,
            "design": "mio",
        }

    if categoria == "Ortho-K / Inversa" and algoritmo == "Toffoli" and rx_sfera < 0:
        t = toffoli_calc(k_med, abs(target_orthok) if target_orthok else abs(rx_sfera))
        fluor = estimate_clearance(k_med, t, "mio")
        return {
            "modello_prod": modello if modello_prod != "Automatico" else "C6 OBL",
            "sottotipo": "Toffoli-inspired",
            "lente_bc_mm": t["RB"],
            "lente_rb_mm": t["RB"],
            "lente_diam_mm": t["TD"],
            "lente_potere_d": t["PWR"],
            "lente_cilindro_d": 0.0,
            "lente_asse_cil": None,
            "lente_add_d": 0.0,
            "ordine": t,
            "fluor": fluor,
            "design": "mio",
        }

    if rx_sfera > 0 and categoria in ("Custom avanzata", "RGP", "Ortho-K / Inversa"):
        h = hyperopia_calc(k_med, rx_sfera)
        fluor = estimate_clearance(k_med, h, "hyper")
        return {
            "modello_prod": modello if modello_prod != "Automatico" else "C6 OBL",
            "sottotipo": "Ipermetropia inversa",
            "lente_bc_mm": h["RB"],
            "lente_rb_mm": h["RB"],
            "lente_diam_mm": h["TD"],
            "lente_potere_d": round(rx_sfera, 2),
            "lente_cilindro_d": 0.0,
            "lente_asse_cil": None,
            "lente_add_d": 0.0,
            "ordine": h,
            "fluor": fluor,
            "design": "hyper",
        }

    if cyl_sig and categoria in ("Torica", "RGP", "Custom avanzata", "Ortho-K / Inversa"):
        a = astig_calc(min(k1, k2), max(k1, k2), rx_cil)
        fluor = estimate_clearance(k_med, a, "toric")
        fluor["valutazione"] = a["raccomandazione"]
        return {
            "modello_prod": modello if modello_prod != "Automatico" else "C6 AS TI",
            "sottotipo": "Astigmatismo / torica",
            "lente_bc_mm": a["RB_flat"],
            "lente_rb_mm": a["RB_flat"],
            "lente_diam_mm": a["TD"],
            "lente_potere_d": round(rx_sfera, 2),
            "lente_cilindro_d": round(rx_cil, 2),
            "lente_asse_cil": int(rx_asse),
            "lente_add_d": 0.0,
            "ordine": a,
            "fluor": fluor,
            "design": "toric",
        }

    if abs(rx_add) >= 0.75 or categoria == "Multifocale / Presbiopia":
        p = presbyopia_calc(k_med, abs(rx_add))
        fluor = estimate_clearance(k_med, p, "presb")
        return {
            "modello_prod": modello if modello_prod != "Automatico" else "C6 OBL MF",
            "sottotipo": "Presbiopia / multifocale inversa",
            "lente_bc_mm": p["RB"],
            "lente_rb_mm": p["RB"],
            "lente_diam_mm": p["TD"],
            "lente_potere_d": round(rx_sfera, 2),
            "lente_cilindro_d": round(rx_cil, 2) if cyl_sig else 0.0,
            "lente_asse_cil": int(rx_asse) if cyl_sig else None,
            "lente_add_d": round(rx_add, 2),
            "ordine": p,
            "fluor": fluor,
            "design": "presb",
        }

    bc = 8.60 if k_med >= 7.80 else 8.40
    diam = 14.20 if hvid <= 11.8 else 14.40
    ordine = {"BC": bc, "TD": diam}
    fluor = estimate_clearance(k_med, {"RB": bc, "TD": diam, "ZO": 5.6}, "base")
    return {
        "modello_prod": modello,
        "sottotipo": "Sferica base",
        "lente_bc_mm": bc,
        "lente_rb_mm": None,
        "lente_diam_mm": diam,
        "lente_potere_d": round(rx_sfera, 2),
        "lente_cilindro_d": 0.0,
        "lente_asse_cil": None,
        "lente_add_d": 0.0,
        "ordine": ordine,
        "fluor": fluor,
        "design": "base",
    }
