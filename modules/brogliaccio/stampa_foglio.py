# -*- coding: utf-8 -*-
"""
stampa_foglio.py — Il foglio del brogliaccio da stampare (PDF A4 orizzontale).

pdf_foglio(giorno, righe=None) → bytes
  · righe=None  → foglio vuoto da compilare a mano
  · righe=[...] → foglio del giorno già compilato, più alcune righe vuote e i totali
"""
from __future__ import annotations

import datetime as dt
import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from . import db_brogliaccio as db

VERDE = colors.HexColor("#1D6B44")
GRIGIO = colors.HexColor("#5B6B70")
LINEA = colors.HexColor("#B8C7C2")
CASELLA = "☐"

# (titolo, larghezza in mm) — totale 273 mm
COLONNE = [("Ora", 12), ("Paziente / nome · telefono", 48), ("Cosa è successo", 30), ("Chi", 22),
           ("Descrizione", 49), ("Importo", 17), ("Pagamento", 33), ("Fattura", 22), ("Prossimo passo · a chi · entro", 40)]

_TIPO_BREVE = {db.T_TEL_IN: "Telefonata ricevuta", db.T_TEL_OUT: "Telefonata fatta", db.T_MSG: "WhatsApp / email",
               db.T_APP: "Appuntamento fissato", db.T_APP_MOD: "App. spostato/annullato", db.T_VISITA: "Visita / valutazione",
               db.T_SEDUTA: "Seduta / terapia", db.T_ASSENTE: "Non si è presentato", db.T_REL_DA: "Relazione da scrivere",
               db.T_REL_OK: "Relazione consegnata", db.T_REL_NO: "Relazione non necessaria", db.T_PAGAM: "Pagamento / fattura",
               db.T_NOTA: "Nota"}


def _font():
    """Font con accenti e simboli (DejaVu se disponibile, altrimenti Helvetica)."""
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        import os
        for base in ("/usr/share/fonts/truetype/dejavu/", "/usr/share/fonts/dejavu/"):
            if os.path.exists(base + "DejaVuSans.ttf"):
                if "DVS" not in pdfmetrics.getRegisteredFontNames():
                    pdfmetrics.registerFont(TTFont("DVS", base + "DejaVuSans.ttf"))
                    pdfmetrics.registerFont(TTFont("DVSB", base + "DejaVuSans-Bold.ttf"))
                return "DVS", "DVSB", CASELLA
    except Exception:
        pass
    return "Helvetica", "Helvetica-Bold", "[ ]"


def pdf_foglio(giorno: dt.date | None = None, righe: list | None = None, sede: str = "", righe_vuote: int | None = None) -> bytes:
    f, fb, box = _font()
    st_cella = ParagraphStyle("c", fontName=f, fontSize=7.6, leading=9.4)
    st_testa = ParagraphStyle("h", fontName=fb, fontSize=7.6, leading=9.2, textColor=colors.white)
    st_tit = ParagraphStyle("t", fontName=fb, fontSize=14, leading=17, textColor=VERDE)
    st_sotto = ParagraphStyle("s", fontName=f, fontSize=8.5, leading=11, textColor=GRIGIO)

    def P(t, s=st_cella):
        return Paragraph(str(t or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"), s)

    st_box = ParagraphStyle("b", fontName=f, fontSize=7, leading=9.2, textColor=GRIGIO)
    pag_vuoto = Paragraph(f"{box} POS&nbsp;&nbsp;{box} Contanti<br/>{box} Bonifico&nbsp;&nbsp;{box} Da pagare", st_box)
    fat_vuoto = Paragraph(f"{box} Da fare<br/>{box} Fatta&nbsp;&nbsp;{box} No", st_box)
    dati = [[P(t, st_testa) for t, _ in COLONNE]]
    compilate = 0
    for r in (righe or []):
        q = r.get("quando")
        ora = q.astimezone(db.TZ).strftime("%H:%M") if hasattr(q, "astimezone") else ""
        chi_paz = db.nome_paziente(r) + (f" · {r['telefono']}" if r.get("telefono") else "")
        imp = db.euro(r["importo"]) if r.get("importo") is not None else ""
        cosa = _TIPO_BREVE.get(r.get("tipo"), r.get("tipo") or "")
        cosa_p = Paragraph(cosa.replace("&", "&amp;") + (f"<br/><font color='#5B6B70'>{r['prestazione']}</font>" if r.get("prestazione") else ""), st_cella)
        passo = ""
        if r.get("prossimo_passo"):
            passo = r["prossimo_passo"] + (f" · {r['assegnato_a']}" if r.get("assegnato_a") else "") + \
                    (f" · entro {db.fmt(r['scadenza'])}" if r.get("scadenza") else "") + (" ✔" if r.get("stato") == "fatto" else "")
        fat = r.get("fattura") or ""
        if r.get("fattura_rif"):
            fat = f"Fatta {r['fattura_rif']}"
        dati.append([P(ora), P(chi_paz), cosa_p, P(r.get("operatore")),
                     P(r.get("descrizione")), P(imp), P(r.get("pagamento")), P(fat), P(passo)])
        compilate += 1
    vuote = righe_vuote if righe_vuote is not None else (16 if righe is None else max(4, 14 - compilate))
    for _ in range(vuote):
        dati.append(["", "", "", "", "", "", pag_vuoto, fat_vuoto, ""])

    tab = Table(dati, colWidths=[w * mm for _, w in COLONNE], repeatRows=1,
                rowHeights=[None] + [None] * compilate + [10.5 * mm] * vuote)
    tab.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), VERDE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, LINEA),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F3F7F5")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
    ]))

    if giorno and righe is not None:
        titolo = f"Brogliaccio dello studio · {db.fmt(giorno)}"
    else:
        titolo = "Brogliaccio dello studio · giorno ____ / ____ / ________"
    sede_txt = sede or "____________________"
    elementi = [P(titolo, st_tit),
                P(f"Sede: {sede_txt}   ·   Compilato da: ____________________   ·   "
                  "Una riga per ogni fatto: telefonate, appuntamenti, visite, sedute, pagamenti, relazioni, note.", st_sotto),
                Spacer(1, 3 * mm), tab, Spacer(1, 4 * mm)]

    if righe:
        t = db.riepilogo_importi(righe)
        riep = (f"Incassato {db.euro(t['incassato'])}  (POS {db.euro(t['per_metodo']['POS'])} · contanti "
                f"{db.euro(t['per_metodo']['Contanti'])} · bonifico {db.euro(t['per_metodo']['Bonifico'])})   ·   "
                f"da pagare {db.euro(t['da_pagare'])}   ·   fatture da fare {t['fatture_da_fare']}")
        elementi.append(P(riep, ParagraphStyle("r", fontName=fb, fontSize=9, leading=12, textColor=VERDE)))
        elementi.append(P("Totali delle righe già nel gestionale; le righe scritte a mano vanno aggiunte nel 📋 Foglio.", st_sotto))
    else:
        elementi.append(P("Totale incassato:  POS € ________   Contanti € ________   Bonifico € ________   "
                          "Da pagare € ________   Fatture da fare n. ____", ParagraphStyle("r", fontName=fb, fontSize=9,
                                                                                         leading=12, textColor=VERDE)))
        elementi.append(P("A fine giornata ricopiare le righe nel gestionale: 📒 Brogliaccio → 📋 Foglio.", st_sotto))

    def piede(c, d):
        c.saveState(); c.setFont(f, 7); c.setFillColor(GRIGIO)
        c.drawString(12 * mm, 7 * mm, "Studio The Organism · Metodo PNEV · brogliaccio dello studio")
        c.drawRightString(landscape(A4)[0] - 12 * mm, 7 * mm, f"pag. {d.page}")
        c.restoreState()

    buf = io.BytesIO()
    SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=12 * mm, rightMargin=12 * mm, topMargin=10 * mm,
                      bottomMargin=12 * mm, title="Brogliaccio dello studio").build(elementi, onFirstPage=piede, onLaterPages=piede)
    return buf.getvalue()
