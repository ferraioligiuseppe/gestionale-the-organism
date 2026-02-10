
# Estratto dal gestionale The Organism (app.py) – core visivo
# Nota: gli asset grafici (sfondi carta intestata) vanno inseriti in vision_core/assets/print_bg/
# con i nomi coerenti a quelli cercati da _find_bg_image(). Se mancano, il PDF verrà generato senza sfondo.

import os
import math
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, A5
from reportlab.lib.units import mm, cm
from reportlab.lib.utils import ImageReader

def _find_bg_image(page_kind: str, variant: str) -> str | None:
    """
    Finds a background image inside common asset folders.
    page_kind: 'a4' or 'a5'
    variant: 'with_cirillo' or 'no_cirillo'
    """
    candidates = []

    # preferred canonical names
    base_names = [
        f"{page_kind}_{variant}",
        f"letterhead_{page_kind}_{variant}",
        f"prescrizione_{page_kind}_{variant}",
    ]
    exts = [".png", ".jpg", ".jpeg", ".webp"]

    # common folders
    folders = [
        "assets/print_bg",
        "assets/print",
        "assets",
        "assets/templates",   # just in case you put them here
    ]

    for folder in folders:
        for bn in base_names:
            for ext in exts:
                candidates.append(os.path.join(folder, bn + ext))

    # also accept your specific filenames (legacy)
    legacy = []
    if page_kind == "a4":
        legacy += [
            "assets/print_bg/CARATA INTESTAT THE ORGANISMA4.jpeg",
            "assets/CARATA INTESTAT THE ORGANISMA4.jpeg",
        ]
    if page_kind == "a5" and variant == "no_cirillo":
        legacy += [
            "assets/print_bg/PRESCRIZIONI THE ORGANISMAA5_no cirillo.png",
            "assets/PRESCRIZIONI THE ORGANISMAA5_no cirillo.png",
        ]
    candidates += legacy

    for p in candidates:
        if os.path.exists(p):
            return p

    # fallback: if with_cirillo missing, try no_cirillo; and vice versa
    if variant == "with_cirillo":
        return _find_bg_image(page_kind, "no_cirillo")
    return _find_bg_image(page_kind, "with_cirillo") if variant == "no_cirillo" else None


def _draw_bg_image_fullpage(c: canvas.Canvas, page_w: float, page_h: float, img_path: str | None):
    if not img_path:
        return
    try:
        img = ImageReader(img_path)
        iw, ih = img.getSize()
        scale = min(page_w / iw, page_h / ih)
        dw, dh = iw * scale, ih * scale
        x = (page_w - dw) / 2
        y = (page_h - dh) / 2
        c.drawImage(img, x, y, width=dw, height=dh, mask="auto")
    except Exception:
        # fail silently: no background
        return



def _draw_prescrizione_clean_table(c: canvas.Canvas, page_w: float, page_h: float, dati: dict, top_offset_mm: float = 60):
    """
    Clean layout (no boxes): writes a readable table with SF/CIL/AX for OD/OS:
    Lontano / Intermedio / Vicino.
    """
    left = 18 * mm
    right = page_w - 18 * mm
    y = page_h - top_offset_mm * mm  # below header line

    # marker di debug: posizione inizio stampa
    c.saveState(); c.setFont('Helvetica', 7); c.drawString(left-8*mm, y+2, '1'); c.restoreState()

    c.setFont("Helvetica", 11)
    c.drawString(left, y, f"Sig.: {_safe_str(dati.get('paziente',''))}")
    c.drawRightString(right, y, f"Data: {_safe_str(dati.get('data',''))}")
    y -= 18*mm

    # headers
    c.setFont("Helvetica-Bold", 10)
    c.drawString(left, y, "PRESCRIZIONE OCCHIALI")
    y -= 7 * mm

    # --- TABO semicircles + axis arrow (asse cilindro) ---
    # Usare asse del LONTANO; freccia solo se CIL != 0
    r_tabo = 24 * mm
    # Spazio extra: evita che Nome/Data coprano i semicerchi
    y -= 20 * mm
    cy_tabo = y - 4 * mm
    cx_od = left + 55 * mm
    cx_os = left + 135 * mm

    _draw_tabo_semicircle(c, cx_od, cy_tabo, r_tabo, "Occhio Destro")
    _draw_tabo_semicircle(c, cx_os, cy_tabo, r_tabo, "Occhio Sinistro")

    # Scegli l'asse da disegnare sui TABO.
    # Regola: usa prima il rigo che ha CIL diverso da 0; se nessuno, usa il primo asse diverso da 0 (se presente).
    def _pick_axis_and_cyl(prefix: str):
        cand = [
            ("lon", dati.get(f"{prefix}_lon_cil"), dati.get(f"{prefix}_lon_ax")),
            ("int", dati.get(f"{prefix}_int_cil"), dati.get(f"{prefix}_int_ax")),
            ("vic", dati.get(f"{prefix}_vic_cil"), dati.get(f"{prefix}_vic_ax")),
        ]
        # 1) priorità: CIL != 0
        for _, cil, ax in cand:
            try:
                if float(cil or 0) != 0.0 and ax is not None and str(ax).strip() != "":
                    return ax, cil
            except Exception:
                pass
        # 2) fallback: asse != 0 (anche se CIL=0) — utile se vuoi indicare comunque la direzione di montaggio
        for _, cil, ax in cand:
            try:
                if ax is not None and str(ax).strip() != "":
                    return ax, cil
            except Exception:
                if ax is not None and str(ax).strip() != "":
                    return ax, cil
        return None, None

    od_ax_pick, od_cil_pick = _pick_axis_and_cyl("od")
    os_ax_pick, os_cil_pick = _pick_axis_and_cyl("os")

    _draw_axis_arrow(c, cx_od, cy_tabo, r_tabo, od_ax_pick, enabled=(od_ax_pick is not None))
    _draw_axis_arrow(c, cx_os, cy_tabo, r_tabo, os_ax_pick, enabled=(os_ax_pick is not None))

    # spazio dopo TABO
    y -= 2 * r_tabo + 10 * mm

    # columns
    col_label = left
    col_od_sf  = left + 28*mm
    col_od_cil = left + 46*mm
    col_od_ax  = left + 64*mm

    col_os_sf  = left + 112*mm
    col_os_cil = left + 130*mm
    col_os_ax  = left + 148*mm

    c.setFont("Helvetica-Bold", 9)
    c.drawString(col_od_sf - 10*mm, y, "OD")
    c.drawString(col_os_sf - 10*mm, y, "OS")
    y -= 5 * mm

    c.setFont("Helvetica-Bold", 9)
    c.drawString(col_label, y, "")
    c.drawString(col_od_sf,  y, "SF")
    c.drawString(col_od_cil, y, "CIL")
    c.drawString(col_od_ax,  y, "AX")
    c.drawString(col_os_sf,  y, "SF")
    c.drawString(col_os_cil, y, "CIL")
    c.drawString(col_os_ax,  y, "AX")
    y -= 6 * mm

    def row(label, od_sf, od_cil, od_ax, os_sf, os_cil, os_ax):
        nonlocal y
        c.setFont("Helvetica", 9)
        c.drawString(col_label, y, label)
        c.drawRightString(col_od_sf + 10*mm, y, _fmt_num(od_sf))
        c.drawRightString(col_od_cil + 10*mm, y, _fmt_num(od_cil))
        c.drawRightString(col_od_ax + 10*mm, y, _safe_str(od_ax))

        c.drawRightString(col_os_sf + 10*mm, y, _fmt_num(os_sf))
        c.drawRightString(col_os_cil + 10*mm, y, _fmt_num(os_cil))
        c.drawRightString(col_os_ax + 10*mm, y, _safe_str(os_ax))
        y -= 6 * mm

    row("Lontano",
        dati.get("od_lon_sf"), dati.get("od_lon_cil"), dati.get("od_lon_ax"),
        dati.get("os_lon_sf"), dati.get("os_lon_cil"), dati.get("os_lon_ax"))
    row("Intermedio",
        dati.get("od_int_sf"), dati.get("od_int_cil"), dati.get("od_int_ax"),
        dati.get("os_int_sf"), dati.get("os_int_cil"), dati.get("os_int_ax"))
    row("Vicino",
        dati.get("od_vic_sf"), dati.get("od_vic_cil"), dati.get("od_vic_ax"),
        dati.get("os_vic_sf"), dati.get("os_vic_cil"), dati.get("os_vic_ax"))

    y -= 8 * mm

    # Lenti / trattamenti
    c.setFont("Helvetica-Bold", 10)
    c.drawString(left, y, "Lenti consigliate / Trattamenti")
    y -= 6 * mm
    c.setFont("Helvetica", 9)
    lenti = ", ".join(dati.get("lenti", []) or [])
    if lenti:
        c.drawString(left, y, f"Lenti: {lenti}")
        y -= 5 * mm
    altri = _safe_str(dati.get("altri_trattamenti", ""))
    if altri:
        c.drawString(left, y, f"Altri trattamenti: {altri}")
        y -= 5 * mm

    note = _safe_str(dati.get("note", ""))
    if note:
        y -= 2 * mm
        c.setFont("Helvetica-Bold", 9)
        c.drawString(left, y, "Note:")
        y -= 5 * mm
        c.setFont("Helvetica", 9)
        max_chars = 110 if page_w >= A4[0] else 70
        for i in range(0, len(note), max_chars):
            c.drawString(left, y, note[i:i+max_chars])
            y -= 5 * mm


def _draw_tabo_semicircle(c: canvas.Canvas, cx: float, cy: float, r: float, label: str):
    """Disegna semicerchio TABO 180→0 con tick principali e label."""
    c.saveState()
    c.setLineWidth(1)
    # arco superiore (0→180)
    c.arc(cx - r, cy - r, cx + r, cy + r, startAng=0, extent=180)

    # tick ogni 30° (più lunghi ogni 60°)
    for deg in range(0, 181, 10):
        rad = math.radians(deg)
        x1 = cx + r * math.cos(rad)
        y1 = cy + r * math.sin(rad)
        tick = 3*mm if deg % 30 == 0 else 1.8*mm
        if deg % 60 == 0:
            tick = 4*mm
        x2 = cx + (r - tick) * math.cos(rad)
        y2 = cy + (r - tick) * math.sin(rad)
        c.line(x2, y2, x1, y1)

    # labels principali
    c.setFont("Helvetica", 8)
    c.drawString(cx - r - 12*mm, cy + 1*mm, "180")
    c.drawCentredString(cx, cy + r + 3*mm, "90")
    c.drawString(cx + r + 4*mm, cy + 1*mm, "0")

    # label occhio sotto
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(cx, cy - r - 6*mm, label)
    c.restoreState()



def _prescrizione_pdf_imagebg(page_size, page_kind: str, con_cirillo: bool, dati: dict) -> bytes:
    variant = "with_cirillo" if con_cirillo else "no_cirillo"
    bg = _find_bg_image(page_kind, variant)
    page_w, page_h = page_size
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=page_size)
    _draw_bg_image_fullpage(c, page_w, page_h, bg)
    # top offset: A5 has less vertical space
    top_offset = 72 if page_kind == "a4" else 62
    _draw_prescrizione_clean_table(c, page_w, page_h, dati, top_offset_mm=top_offset)
    c.showPage(); c.save()
    buf.seek(0)
    return buf.read()

try:
    from reportlab.lib.pagesizes import A4, A5, landscape
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


# PDF merge (template letterhead)
try:
    from pypdf import PdfReader, PdfWriter
    from pypdf._page import PageObject
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False



def genera_prescrizione_occhiali_bytes(
    formato: str,
    dati: dict,
    with_cirillo: bool = True,
    assets_dir: str | None = None
) -> bytes:
    """Genera PDF prescrizione occhiali (A4/A5) usando lo stesso motore del gestionale.
    - assets_dir: cartella dove sono presenti gli sfondi (default: vision_core/assets/print_bg)
    """
    if assets_dir is None:
        assets_dir = os.path.join(os.path.dirname(__file__), "assets", "print_bg")

    # La funzione estratta _prescrizione_pdf_imagebg usa _find_bg_image() con path relativi.
    # Per renderla indipendente, impostiamo una variabile d'ambiente temporanea (fallback).
    os.environ["VISION_PRINT_BG_DIR"] = assets_dir

    # Costruiamo un PDF in memoria
    buf = BytesIO()
    pagesize = A4 if formato.upper() == "A4" else A5
    c = canvas.Canvas(buf, pagesize=pagesize)

    # Chiamata alla routine estratta: costruisce layout + tabella
    _prescrizione_pdf_imagebg(c, formato.upper(), dati, with_cirillo=with_cirillo)

    c.showPage()
    c.save()
    return buf.getvalue()
