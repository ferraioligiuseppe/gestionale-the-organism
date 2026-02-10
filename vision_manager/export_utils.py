from __future__ import annotations
import csv
from io import StringIO
from typing import Any, Dict

def build_export_ottico_csv(dati_visita: Dict[str, Any]) -> bytes:
    out = StringIO()
    w = csv.writer(out, delimiter=";")

    paz = dati_visita.get("paziente_label","")
    data = dati_visita.get("data_visita","")
    w.writerow(["Paziente", paz])
    w.writerow(["Data visita", data])
    w.writerow([])

    ref = dati_visita.get("ref_corretta", {}) or {}
    for dist_key, dist_label in [("lontano","Lontano"), ("intermedio","Intermedio"), ("vicino","Vicino")]:
        d = ref.get(dist_key, {}) or {}
        odx = d.get("odx", {}) or {}
        osn = d.get("osn", {}) or {}
        if not any([odx.get("sf"), odx.get("cil"), odx.get("ax"), osn.get("sf"), osn.get("cil"), osn.get("ax"), d.get("add")]):
            continue
        w.writerow([dist_label, "SF", "CIL", "AX"])
        w.writerow(["ODX", odx.get("sf",""), odx.get("cil",""), odx.get("ax","")])
        w.writerow(["OSN", osn.get("sf",""), osn.get("cil",""), osn.get("ax","")])
        if d.get("add"):
            w.writerow(["ADD", d.get("add")])
        w.writerow([])

    tipi = dati_visita.get("tipi_selezionati", []) or []
    note = dati_visita.get("tipo_note", "") or ""
    if tipi:
        w.writerow(["Tipo occhiale", ", ".join([str(x) for x in tipi])])
    if note.strip():
        w.writerow(["Note lente", note.strip()])

    return out.getvalue().encode("utf-8-sig")
