import io
from typing import Callable, Literal
from reportlab.pdfgen import canvas
from pypdf import PdfReader, PdfWriter

Variant = Literal["with_cirillo", "no_cirillo"]
Kind = Literal["a5", "a4_2up"]

TEMPLATE_PATHS = {
    ("a5", "with_cirillo"): "assets/templates/prescrizione_A5_with_cirillo.pdf",
    ("a5", "no_cirillo"):   "assets/templates/prescrizione_A5_no_cirillo.pdf",
    ("a4_2up", "with_cirillo"): "assets/templates/prescrizione_A4_2xA5_with_cirillo.pdf",
    ("a4_2up", "no_cirillo"):   "assets/templates/prescrizione_A4_2xA5_no_cirillo.pdf",
}

def make_overlay_pdf(page_w: float, page_h: float, draw_fn: Callable[[canvas.Canvas, float, float], None]) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(page_w, page_h))
    draw_fn(c, page_w, page_h)
    c.showPage()
    c.save()
    buf.seek(0)
    return buf.read()

def merge_overlay_on_template(template_pdf_path: str, overlay_pdf_bytes: bytes) -> bytes:
    tpl = PdfReader(template_pdf_path)
    ov = PdfReader(io.BytesIO(overlay_pdf_bytes))
    page = tpl.pages[0]
    page.merge_page(ov.pages[0])
    w = PdfWriter()
    w.add_page(page)
    out = io.BytesIO()
    w.write(out)
    out.seek(0)
    return out.read()

def build_pdf(kind: Kind, variant: Variant, draw_overlay_fn: Callable[[canvas.Canvas, float, float], None]) -> bytes:
    template_path = TEMPLATE_PATHS[(kind, variant)]
    tpl = PdfReader(template_path)
    page = tpl.pages[0]
    page_w = float(page.mediabox.width)
    page_h = float(page.mediabox.height)
    overlay = make_overlay_pdf(page_w, page_h, draw_overlay_fn)
    return merge_overlay_on_template(template_path, overlay)
