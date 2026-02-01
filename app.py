# FINAL MERGED APP – The Organism
# Base: app ONLINE (Neon/PostgreSQL) – connection untouched
# Added: PDF graphics from app_test_old_ultimo.py + Esame Obiettivo fields
# Notes: 2xA5 on A4 clean (no crop marks)

# --- IMPORTS (unchanged connection stack) ---
import os, io, datetime
import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, A5
from reportlab.lib.units import mm

# =========================
# DATABASE CONNECTION (UNCHANGED)
# =========================

_DB_URL = os.getenv("DATABASE_URL") or st.secrets.get("DATABASE_URL")

@st.cache_resource

def get_connection():
    return psycopg2.connect(_DB_URL, cursor_factory=RealDictCursor)

# =========================
# DB MIGRATION – ESAME OBIETTIVO
# =========================

def migrate_esame_obiettivo():
    fields = [
        "cornea TEXT",
        "camera_anteriore TEXT",
        "cristallino TEXT",
        "congiuntiva_sclera TEXT",
        "iride_pupilla TEXT",
        "vitreo TEXT",
    ]
    with get_connection() as conn:
        with conn.cursor() as cur:
            for f in fields:
                name = f.split()[0]
                cur.execute(f"ALTER TABLE valutazioni_visive ADD COLUMN IF NOT EXISTS {f}")
        conn.commit()

# =========================
# PDF GRAPHICS – FROM APP_TEST (CLEAN)
# =========================

def draw_prescrizione_a5(c, data):
    w, h = A5
    c.setFont("Helvetica", 10)
    y = h - 25*mm
    for k, v in data.items():
        if v:
            c.drawString(20*mm, y, f"{k}: {v}")
            y -= 7*mm


def pdf_prescrizione_a5(data):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A5)
    draw_prescrizione_a5(c, data)
    c.showPage(); c.save()
    buf.seek(0)
    return buf.read()


def pdf_prescrizione_2a5_a4(data):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w5, h5 = A5
    w4, h4 = A4
    x = (w4 - w5) / 2
    c.translate(x, 0)
    draw_prescrizione_a5(c, data)
    c.translate(0, h4/2)
    draw_prescrizione_a5(c, data)
    c.showPage(); c.save()
    buf.seek(0)
    return buf.read()

# =========================
# STREAMLIT UI
# =========================

def main():
    st.title("The Organism – Gestionale")
    migrate_esame_obiettivo()

    st.header("Esame Obiettivo")
    cornea = st.text_input("Cornea")
    camera = st.text_input("Camera Anteriore")
    cristallino = st.text_input("Cristallino")
    cong = st.text_input("Congiuntiva / Sclera")
    iride = st.text_input("Iride / Pupilla")
    vitreo = st.text_input("Vitreo")

    data = {
        "Cornea": cornea,
        "Camera Anteriore": camera,
        "Cristallino": cristallino,
        "Congiuntiva/Sclera": cong,
        "Iride/Pupilla": iride,
        "Vitreo": vitreo,
    }

    st.subheader("Stampa Prescrizione")
    mode = st.selectbox("Formato", ["A5", "A4 (2×A5)"])

    if st.button("Genera PDF"):
        if mode == "A5":
            pdf = pdf_prescrizione_a5(data)
        else:
            pdf = pdf_prescrizione_2a5_a4(data)
        st.download_button("Scarica PDF", pdf, file_name="prescrizione.pdf")


if __name__ == "__main__":
    main()
