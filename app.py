import io
from typing import Callable, Literal
import streamlit as st
import os

st.set_page_config(page_title="The Organism", layout="wide")
st.title("BOOT OK ✅")
st.write("Se vedi questo, il file giusto sta girando.")
st.write("Python:", os.getenv("PYTHON_VERSION", "n/a"))
st.write("CHK 1: imports base ok")

# ---- dopo import pypdf / reportlab / ecc
st.write("CHK 2: imports pdf ok")

# ---- prima di qualunque init_db / migrate / connessione
st.write("CHK 3: prima init_db ok")

# ---- subito prima della funzione login / render login
st.write("CHK 4: prima login ok")

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, A5
from pypdf import PdfReader, PdfWriter

Variant = Literal["with_cirillo", "no_cirillo"]
PageKind = Literal["a4", "a5"]

TEMPLATE_PATHS = {
    ("a4", "with_cirillo"): "assets/letterhead/a4_with_cirillo.pdf",
    ("a5", "with_cirillo"): "assets/letterhead/a5_with_cirillo.pdf",
    ("a4", "no_cirillo"):   "assets/letterhead/a4_no_cirillo.pdf",
    ("a5", "no_cirillo"):   "assets/letterhead/a5_no_cirillo.pdf",
}

PAGESIZES = {
    "a4": A4,
    "a5": A5,
}

def make_overlay_pdf(page_kind: PageKind, draw_fn: Callable[[canvas.Canvas, float, float], None]) -> bytes:
    """Create a single-page transparent PDF overlay (variable text/graphics only)."""
    pagesize = PAGESIZES[page_kind]
    w, h = pagesize
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=pagesize)
    draw_fn(c, w, h)
    c.showPage()
    c.save()
    buf.seek(0)
    return buf.read()

def merge_overlay_on_template(template_pdf_path: str, overlay_pdf_bytes: bytes) -> bytes:
    """Merge overlay (top) onto template PDF (bottom)."""
    tpl_reader = PdfReader(template_pdf_path)
    ov_reader = PdfReader(io.BytesIO(overlay_pdf_bytes))

    tpl_page = tpl_reader.pages[0]
    ov_page = ov_reader.pages[0]

    tpl_page.merge_page(ov_page)

    writer = PdfWriter()
    writer.add_page(tpl_page)

    out = io.BytesIO()
    writer.write(out)
    out.seek(0)
    return out.read()

def build_pdf_with_letterhead(
    page_kind: PageKind,
    variant: Variant,
    draw_fn: Callable[[canvas.Canvas, float, float], None],
) -> bytes:
    """High-level helper: build final PDF = template + overlay."""
    template_path = TEMPLATE_PATHS[(page_kind, variant)]
    overlay = make_overlay_pdf(page_kind, draw_fn)
    return merge_overlay_on_template(template_path, overlay)
