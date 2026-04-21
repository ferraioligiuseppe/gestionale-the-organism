# -*- coding: utf-8 -*-
"""
Template PDF The Organism - carta intestata condivisa.
Usato da: ricetta ottica, relazione clinica, lettera invio.
"""
from __future__ import annotations
import math, io, os
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas

W, H = A4
VERDE    = colors.HexColor("#1D6B44")
GRIGIO   = colors.HexColor("#888780")
GRIGIO_L = colors.HexColor("#D3D1C7")

INDIRIZZO = "Via De Rosa, 46 - 84016 Pagani (SA)  |  Viale Marconi, 55 - 84013 Cava de Tirreni SA"
CONTATTI  = "Tel. 0815152334  |  Cell. 3921873914  |  apstheorganism@gmail.com"

def _logo_path():
    base = os.path.dirname(os.path.abspath(__file__))
    p = os.path.join(base, "assets", "logo.png")
    if os.path.exists(p):
        return p
    return None

def draw_intestazione(c, professionista="", titolo=""):
    logo = _logo_path()
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(colors.black)
    c.drawString(1.8*cm, H - 1.3*cm, professionista)
    c.setFont("Helvetica", 9)
    c.setFillColor(GRIGIO)
    c.drawString(1.8*cm, H - 1.9*cm, titolo)
    if logo:
        lw, lh = 6.0*cm, 2.2*cm
        c.drawImage(logo, W-1.8*cm-lw, H-0.8*cm-lh,
                    width=lw, height=lh, preserveAspectRatio=True, mask="auto")
    c.setStrokeColor(VERDE)
    c.setLineWidth(3)
    c.line(1.8*cm, H-3.1*cm, W-1.8*cm, H-3.1*cm)
    c.setLineWidth(0.8)
    c.line(1.8*cm, H-3.4*cm, W-1.8*cm, H-3.4*cm)
    c.setFont("Helvetica", 7); c.setFillColor(GRIGIO)
    c.drawCentredString(W/2, H-3.9*cm, INDIRIZZO)
    c.drawCentredString(W/2, H-4.25*cm, CONTATTI)

def draw_footer(c):
    c.setStrokeColor(VERDE); c.setLineWidth(0.8)
    c.line(1.8*cm, 2.2*cm, W-1.8*cm, 2.2*cm)
    c.setFont("Helvetica-Bold", 8); c.setFillColor(colors.black)
    c.drawCentredString(W/2, 1.7*cm, INDIRIZZO)
    c.setFont("Helvetica", 8)
    c.drawCentredString(W/2, 1.2*cm, CONTATTI)

def genera_ricetta(professionista, titolo, rx) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    draw_intestazione(c, professionista, titolo)
    _draw_corpo_ricetta(c, rx)
    draw_footer(c)
    c.save(); buf.seek(0)
    return buf.read()

def genera_carta_intestata(professionista, titolo,
                            paziente, data, titolo_doc,
                            corpo_testo="") -> bytes:
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_LEFT, TA_JUSTIFY

    buf = io.BytesIO()

    sB = ParagraphStyle("b", fontSize=10, fontName="Helvetica",
                         spaceAfter=8, leading=16, alignment=TA_JUSTIFY)
    sH = ParagraphStyle("h", fontSize=12, fontName="Helvetica-Bold",
                         textColor=VERDE, spaceAfter=6, spaceBefore=12)

    # Usiamo canvas diretto per l intestazione + frame per il testo
    c = canvas.Canvas(buf, pagesize=A4)
    draw_intestazione(c, professionista, titolo)

    # Titolo documento
    y = H - 5.2*cm
    c.setFont("Helvetica-Bold", 14); c.setFillColor(VERDE)
    c.drawCentredString(W/2, y, titolo_doc)
    c.setStrokeColor(GRIGIO_L); c.setLineWidth(0.5)
    c.line(1.8*cm, y-0.3*cm, W-1.8*cm, y-0.3*cm)

    y2 = y - 1.0*cm
    c.setFont("Helvetica-Bold", 10); c.setFillColor(colors.black)
    c.drawString(1.8*cm, y2, "Paziente:")
    c.setFont("Helvetica", 10)
    c.drawString(4.0*cm, y2, paziente)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(W-5*cm, y2, "Data:")
    c.setFont("Helvetica", 10)
    c.drawString(W-3.5*cm, y2, data)
    c.setStrokeColor(GRIGIO_L); c.setLineWidth(0.3)
    c.line(1.8*cm, y2-0.4*cm, W-1.8*cm, y2-0.4*cm)

    # Corpo testo (semplice, riga per riga)
    if corpo_testo:
        yt = y2 - 0.9*cm
        c.setFont("Helvetica", 10); c.setFillColor(colors.black)
        for riga in corpo_testo.split("\n"):
            if riga.startswith("###"):
                c.setFont("Helvetica-Bold", 11)
                c.setFillColor(VERDE)
                c.drawString(1.8*cm, yt, riga.replace("###","").strip())
                c.setFont("Helvetica", 10); c.setFillColor(colors.black)
            else:
                c.drawString(1.8*cm, yt, riga[:110])
            yt -= 0.55*cm
            if yt < 3.5*cm:
                draw_footer(c)
                c.showPage()
                draw_intestazione(c, professionista, titolo)
                yt = H - 4.5*cm

    # Firma
    yt_firma = 5.5*cm
    c.setStrokeColor(GRIGIO_L); c.setLineWidth(0.5)
    c.line(1.8*cm, yt_firma, W/2-1*cm, yt_firma)
    c.setFont("Helvetica", 8); c.setFillColor(GRIGIO)
    c.drawString(1.8*cm, yt_firma-0.4*cm, "Firma e timbro")
    c.line(W/2+1*cm, yt_firma, W-1.8*cm, yt_firma)
    c.drawString(W/2+1*cm, yt_firma-0.4*cm, professionista)

    draw_footer(c)
    c.save(); buf.seek(0)
    return buf.read()


def _draw_corpo_ricetta(c, rx):
    def _f(v):
        if v is None or v == "" or v == 0: return ""
        try:
            f = float(v)
            return f"+{f:.2f}" if f>0 else f"{f:.2f}"
        except: return str(v)

    def tabo(cx, cy, r=2.3*cm, label=""):
        c.setStrokeColor(GRIGIO_L); c.setLineWidth(0.5)
        c.arc(cx-r, cy-r, cx+r, cy+r, startAng=0, extent=180)
        c.line(cx-r-0.3*cm, cy, cx+r+0.3*cm, cy)
        c.line(cx, cy, cx, cy+r+0.2*cm)
        c.setFont("Helvetica",6); c.setFillColor(GRIGIO)
        for deg in [30,60,90,120,150]:
            rad = math.radians(deg)
            xp = cx+r*math.cos(math.pi-rad); yp = cy+r*math.sin(math.pi-rad)
            c.line(xp,yp,cx+(r+0.12*cm)*math.cos(math.pi-rad),
                         cy+(r+0.12*cm)*math.sin(math.pi-rad))
            c.drawCentredString(cx+(r+0.4*cm)*math.cos(math.pi-rad),
                                cy+(r+0.4*cm)*math.sin(math.pi-rad), str(deg))
        c.drawString(cx-r-0.65*cm, cy-0.1*cm, "180")
        c.drawString(cx+r+0.1*cm,  cy-0.1*cm, "0")
        c.setFont("Helvetica",7); c.drawCentredString(cx, cy+0.5*cm, "TABO")
        c.setFillColor(colors.black); c.circle(cx, cy, 1.5, fill=1)
        c.setFont("Helvetica",9); c.drawCentredString(cx, cy-0.65*cm, label)

    y_sig = H - 5.0*cm
    c.setFont("Helvetica",10); c.setFillColor(colors.black)
    c.drawString(W-7*cm, y_sig+0.5*cm, "Data")
    c.setStrokeColor(GRIGIO_L); c.setLineWidth(0.5)
    c.line(W-6*cm, y_sig+0.5*cm, W-1.8*cm, y_sig+0.5*cm)
    c.setFont("Helvetica",13)
    c.drawString(1.8*cm, y_sig, "Sig.")
    c.line(3.5*cm, y_sig, W-1.8*cm, y_sig)

    y_tabo = H - 9.2*cm
    tabo(W/2-5.5*cm, y_tabo, label="Occhio Destro")
    tabo(W/2+5.5*cm, y_tabo, label="Occhio Sinistro")

    y_tab = y_tabo - 1.9*cm
    cw = 1.45*cm; gap = 0.08*cm
    c.setFont("Helvetica",7); c.setFillColor(GRIGIO)
    x0 = 1.8*cm
    for lbl in ["SFERO","CILINDRO","ASSE"]:
        c.drawCentredString(x0+cw/2, y_tab+0.3*cm, lbl); x0+=cw+gap
    x0 = W/2+2.5*cm
    for lbl in ["SFERO","CILINDRO","ASSE"]:
        c.drawCentredString(x0+cw/2, y_tab+0.3*cm, lbl); x0+=cw+gap

    righe = [
        ("LONTANO",             rx.get("lontano",{})),
        ("INTERMEDIO\n(COMPUTER)", rx.get("intermedio",{})),
        ("VICINO\n(LETTURA)",  rx.get("vicino",{})),
    ]
    yr = y_tab
    for etichetta, vals in righe:
        yr -= 1.2*cm
        od = vals.get("od",{}); os = vals.get("os",{})
        c.setStrokeColor(GRIGIO_L); c.setLineWidth(0.5)
        x0 = 1.8*cm
        for k in ["sf","cil","ax"]:
            c.rect(x0, yr-0.38*cm, cw, 0.65*cm)
            v = _f(od.get(k))
            if v:
                c.setFont("Helvetica",9); c.setFillColor(colors.black)
                c.drawCentredString(x0+cw/2, yr-0.05*cm, v)
            x0 += cw+gap
        c.setFont("Helvetica",7); c.setFillColor(GRIGIO)
        for i,riga in enumerate(etichetta.split("\n")):
            c.drawCentredString(W/2, yr+0.1*cm-i*0.3*cm, riga)
        x0 = W/2+2.5*cm
        for k in ["sf","cil","ax"]:
            c.rect(x0, yr-0.38*cm, cw, 0.65*cm)
            v = _f(os.get(k))
            if v:
                c.setFont("Helvetica",9); c.setFillColor(colors.black)
                c.drawCentredString(x0+cw/2, yr-0.05*cm, v)
            x0 += cw+gap

    yp = yr - 1.3*cm
    c.setFont("Helvetica",7); c.setFillColor(GRIGIO)
    c.drawString(1.8*cm, yp+0.25*cm, "PRISMA")
    c.drawString(4.2*cm, yp+0.25*cm, "BASE")
    c.setStrokeColor(GRIGIO_L); c.setLineWidth(0.5)
    c.line(1.8*cm, yp, 3.8*cm, yp)
    c.line(4.2*cm, yp, 6.8*cm, yp)
    c.drawString(W/2+0.5*cm, yp+0.25*cm, "PRISMA")
    c.drawString(W/2+3.0*cm, yp+0.25*cm, "BASE")
    c.line(W/2+0.5*cm, yp, W/2+2.7*cm, yp)
    c.line(W/2+3.0*cm, yp, W/2+5.5*cm, yp)

    yl = yp - 1.5*cm
    c.setFont("Helvetica-Bold",10); c.setFillColor(colors.black)
    c.drawString(1.8*cm, yl, "LENTI CONSIGLIATE")
    lenti_sx = ["PROGRESSIVE","PER VICINO / INTERMEDIO","FOTOCROMATICHE","POLARIZZATE"]
    lenti_dx = ["TRATTAMENTO ANTIRIFLESSO","ALTRI TRATTAMENTI"]
    lenti_sel = rx.get("lenti",[])
    yl2 = yl - 0.65*cm
    c.setFont("Helvetica",8)
    for opt in lenti_sx:
        sel = opt in lenti_sel
        c.setFillColor(VERDE if sel else GRIGIO_L)
        c.roundRect(1.8*cm, yl2-0.05*cm, 4.8*cm, 0.42*cm, 2, fill=1, stroke=0)
        c.setFillColor(colors.white if sel else colors.black)
        c.drawString(2.1*cm, yl2+0.06*cm, opt)
        yl2 -= 0.58*cm
    yl3 = yl - 0.65*cm
    for opt in lenti_dx:
        sel = opt in lenti_sel
        c.setStrokeColor(GRIGIO_L); c.setLineWidth(0.5)
        c.rect(W/2+0.5*cm, yl3-0.02*cm, 0.32*cm, 0.32*cm)
        if sel:
            c.setFillColor(VERDE)
            c.rect(W/2+0.53*cm, yl3+0.01*cm, 0.26*cm, 0.26*cm, fill=1, stroke=0)
        c.setFillColor(colors.black); c.setFont("Helvetica",8)
        c.drawString(W/2+1.0*cm, yl3+0.05*cm, opt)
        c.setStrokeColor(GRIGIO_L)
        c.line(W/2+4.5*cm, yl3+0.1*cm, W-1.8*cm, yl3+0.1*cm)
        yl3 -= 0.78*cm

    yn = yl2 - 0.4*cm
    c.setFont("Helvetica",7); c.setFillColor(GRIGIO)
    c.drawString(1.8*cm, yn,
        "Correzioni ottenute in base ai dati rifrattometrici ed alle indicazioni del paziente")
    c.drawString(1.8*cm, yn-0.35*cm, "nell esame soggettivo del visus. Validita 1 anno.")
    dp = rx.get("dp","")
    if dp:
        c.setFont("Helvetica",8); c.setFillColor(colors.black)
        c.drawString(1.8*cm, yn-0.8*cm, f"Distanza interpupillare: {dp} mm")
    note = rx.get("note","")
    if note:
        c.setFont("Helvetica",8)
        c.drawString(1.8*cm, yn-1.2*cm, f"NOTE: {note}")

    yf = 3.8*cm
    c.setStrokeColor(GRIGIO_L); c.setLineWidth(0.5)
    for _ in range(3):
        c.line(1.8*cm, yf, W-1.8*cm, yf)
        yf -= 0.5*cm
