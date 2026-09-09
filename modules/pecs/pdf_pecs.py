# -*- coding: utf-8 -*-
"""
modules/pecs/pdf_pecs.py
------------------------
Report PDF del percorso PECS di un paziente.
ReportLab, verde istituzionale #1D6B44, compatibile con la carta intestata
per-studio gia' caricata al login del gestionale.

Uso:
    pdf_bytes = genera_report(protocollo, paziente, sessioni, transizioni,
                              esito_criterio, carta_intestata=bytes_o_path)

Studio The Organism - Dott. Giuseppe Ferraioli
"""

from __future__ import annotations

import io
from datetime import datetime
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (BaseDocTemplate, Frame, PageTemplate, Paragraph,
                                Spacer, Table, TableStyle)

from . import pecs_contenuti as pc

TZ = ZoneInfo("Europe/Rome")

VERDE = colors.HexColor("#1D6B44")
VERDE_CHIARO = colors.HexColor("#EAF2ED")
INK = colors.HexColor("#1a1a1a")
MUTED = colors.HexColor("#6b6b6b")
RULE = colors.HexColor("#c9c9c9")
ROSSO = colors.HexColor("#8a3324")

_ss = getSampleStyleSheet()
H1 = ParagraphStyle("PecsH1", parent=_ss["Normal"], fontName="Helvetica-Bold",
                    fontSize=15, leading=18, textColor=INK)
H2 = ParagraphStyle("PecsH2", parent=_ss["Normal"], fontName="Helvetica-Bold",
                    fontSize=10.5, leading=13, textColor=VERDE,
                    spaceBefore=10, spaceAfter=4)
BODY = ParagraphStyle("PecsBody", parent=_ss["Normal"], fontName="Helvetica",
                      fontSize=9, leading=12.2, textColor=INK, alignment=TA_JUSTIFY)
SMALL = ParagraphStyle("PecsSmall", parent=BODY, fontSize=7.8, leading=10,
                       textColor=MUTED)
CELL = ParagraphStyle("PecsCell", parent=BODY, fontSize=8.2, leading=10.4,
                      alignment=0)
CELLB = ParagraphStyle("PecsCellB", parent=CELL, fontName="Helvetica-Bold")

LARGHEZZA = 170 * mm


def _tabella(dati, larghezze, intestazione=True):
    t = Table(dati, colWidths=larghezze, repeatRows=1 if intestazione else 0)
    stile = [
        ("GRID", (0, 0), (-1, -1), 0.4, RULE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
    ]
    if intestazione:
        stile.append(("BACKGROUND", (0, 0), (-1, 0), VERDE_CHIARO))
    t.setStyle(TableStyle(stile))
    return t


def _fascia(testo, colore=VERDE_CHIARO, bordo=VERDE):
    t = Table([[Paragraph(testo, ParagraphStyle("F", parent=BODY,
                                                fontName="Helvetica-Bold",
                                                fontSize=9, leading=12))]],
              colWidths=[LARGHEZZA])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colore),
        ("LINEBEFORE", (0, 0), (0, -1), 2, bordo),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t


def _perc(s: Dict[str, Any]) -> str:
    opp = s.get("n_opportunita") or 0
    if not opp:
        return "-"
    return "%.0f%%" % (100.0 * (s.get("n_autonome") or 0) / opp)


def _fmt_data(d) -> str:
    if not d:
        return "-"
    try:
        return d.strftime("%d/%m/%Y")
    except Exception:
        return str(d)


def _parametri_leggibili(fase: str, parametri: Dict[str, Any]) -> str:
    if not parametri:
        return "-"
    try:
        campi = {c.chiave: c.etichetta for c in pc.get_fase(fase).campi}
    except KeyError:
        campi = {}
    pezzi = []
    for k, v in parametri.items():
        etichetta = campi.get(k, k)
        if isinstance(v, bool):
            v = "si" if v else "no"
        pezzi.append("%s: %s" % (etichetta, v))
    return "; ".join(pezzi)


def genera_report(protocollo: Dict[str, Any],
                  paziente: Optional[Dict[str, Any]],
                  sessioni: List[Dict[str, Any]],
                  transizioni: Optional[List[Dict[str, Any]]] = None,
                  esito_criterio: Optional[pc.EsitoCriterio] = None,
                  operatore: str = "",
                  carta_intestata: Optional[Any] = None,
                  nome_studio: str = "Studio The Organism") -> bytes:
    """Restituisce il PDF come bytes, pronto per st.download_button."""

    transizioni = transizioni or []
    fase_corrente = protocollo.get("fase_corrente", "I")
    buffer = io.BytesIO()
    story = []

    # ---- intestazione ----
    nominativo = "-"
    if paziente:
        nominativo = ("%s %s" % (paziente.get("cognome") or "",
                                 paziente.get("nome") or "")).strip() or "-"

    story.append(Paragraph("Percorso PECS - Report clinico", H1))
    story.append(Spacer(1, 2))
    story.append(Paragraph(
        "Sistema di comunicazione per scambio di immagini (Bondy &amp; Frost) "
        "&nbsp;|&nbsp; %s" % nome_studio, SMALL))
    riga = Table([[""]], colWidths=[LARGHEZZA], rowHeights=[1.2])
    riga.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), VERDE)]))
    story += [Spacer(1, 4), riga, Spacer(1, 8)]

    anagrafica = [[
        Paragraph("Paziente", CELLB), Paragraph(nominativo, CELL),
        Paragraph("Inizio", CELLB), Paragraph(_fmt_data(protocollo.get("data_inizio")), CELL),
        Paragraph("Fase", CELLB), Paragraph(fase_corrente, CELL),
    ], [
        Paragraph("Operatore", CELLB), Paragraph(operatore or "-", CELL),
        Paragraph("Stato", CELLB), Paragraph(protocollo.get("stato", "-"), CELL),
        Paragraph("Report del", CELLB),
        Paragraph(datetime.now(TZ).strftime("%d/%m/%Y"), CELL),
    ]]
    t = _tabella(anagrafica, [22 * mm, 46 * mm, 20 * mm, 30 * mm, 22 * mm, 30 * mm],
                 intestazione=False)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, -1), VERDE_CHIARO),
                           ("BACKGROUND", (2, 0), (2, -1), VERDE_CHIARO),
                           ("BACKGROUND", (4, 0), (4, -1), VERDE_CHIARO)]))
    story += [t, Spacer(1, 6)]

    # ---- fase corrente ----
    try:
        fase_obj = pc.get_fase(fase_corrente)
        story.append(_fascia("FASE ATTUALE &mdash; %s: %s<br/><font size=8>%s</font>"
                             % (fase_corrente, fase_obj.nome, fase_obj.obiettivo)))
    except KeyError:
        pass

    # ---- criterio ----
    if esito_criterio is not None:
        story.append(Paragraph("Criterio di passaggio", H2))
        righe = [[Paragraph("Requisito", CELLB), Paragraph("Esito", CELLB),
                  Paragraph("Dato rilevato", CELLB)]]
        for r in esito_criterio.requisiti:
            esito = "RAGGIUNTO" if r.soddisfatto else "NON raggiunto"
            stile = CELL if r.soddisfatto else ParagraphStyle(
                "no", parent=CELL, textColor=ROSSO)
            righe.append([Paragraph(r.etichetta, CELL),
                          Paragraph(esito, stile),
                          Paragraph(str(r.valore or "-"), CELL)])
        story.append(_tabella(righe, [88 * mm, 27 * mm, 55 * mm]))
        story.append(Spacer(1, 5))
        story.append(_fascia(
            "Criterio complessivo: %s" %
            ("SODDISFATTO - possibile il passaggio alla fase successiva"
             if esito_criterio.soddisfatto
             else "non ancora soddisfatto - proseguire nella fase attuale"),
            VERDE_CHIARO if esito_criterio.soddisfatto else colors.HexColor("#FBEDE9"),
            VERDE if esito_criterio.soddisfatto else ROSSO))

    # ---- sessioni ----
    story.append(Paragraph("Sessioni registrate", H2))
    if not sessioni:
        story.append(Paragraph("Nessuna sessione registrata.", BODY))
    else:
        righe = [[Paragraph("Data", CELLB), Paragraph("Fase", CELLB),
                  Paragraph("Partner", CELLB), Paragraph("Contesto", CELLB),
                  Paragraph("Prove", CELLB), Paragraph("Autonome", CELLB),
                  Paragraph("%", CELLB)]]
        for s in sessioni:
            righe.append([
                Paragraph(_fmt_data(s.get("data")), CELL),
                Paragraph(str(s.get("fase") or "-"), CELL),
                Paragraph(str(s.get("partner") or "-"), CELL),
                Paragraph(str(s.get("contesto") or "-"), CELL),
                Paragraph(str(s.get("n_opportunita") or 0), CELL),
                Paragraph(str(s.get("n_autonome") or 0), CELL),
                Paragraph(_perc(s), CELL),
            ])
        story.append(_tabella(righe, [22 * mm, 16 * mm, 32 * mm, 40 * mm,
                                      18 * mm, 22 * mm, 20 * mm]))

        # dettaglio parametri dell'ultima sessione
        ultima = sessioni[0]
        story.append(Spacer(1, 5))
        story.append(Paragraph(
            "<b>Ultima sessione (%s)</b> &mdash; %s" %
            (_fmt_data(ultima.get("data")),
             _parametri_leggibili(ultima.get("fase", fase_corrente),
                                  ultima.get("parametri") or {})), BODY))
        if ultima.get("note"):
            story.append(Paragraph("<b>Note:</b> %s" % ultima["note"], BODY))

    # ---- transizioni ----
    if transizioni:
        story.append(Paragraph("Storico delle fasi", H2))
        righe = [[Paragraph("Data", CELLB), Paragraph("Passaggio", CELLB),
                  Paragraph("Criterio", CELLB), Paragraph("Motivazione", CELLB)]]
        for tr in transizioni:
            passaggio = "%s &rarr; %s" % (tr.get("da_fase") or "avvio",
                                          tr.get("a_fase"))
            crit = "soddisfatto" if tr.get("criterio_soddisfatto") else (
                "forzato" if tr.get("forzata") else "non verificato")
            righe.append([Paragraph(_fmt_data(tr.get("data")), CELL),
                          Paragraph(passaggio, CELL),
                          Paragraph(crit, CELL),
                          Paragraph(str(tr.get("motivazione") or "-"), CELL)])
        story.append(_tabella(righe, [24 * mm, 40 * mm, 30 * mm, 76 * mm]))

    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "PECS&reg; e' un protocollo di A. Bondy e L. Frost (Pyramid Educational "
        "Consultants). Il presente report documenta l'andamento del percorso e "
        "non sostituisce la valutazione clinica complessiva.", SMALL))

    # ---- pagina ----
    def _decorazioni(canvas, doc):
        canvas.saveState()
        if carta_intestata is not None:
            try:
                from reportlab.lib.utils import ImageReader
                canvas.drawImage(ImageReader(carta_intestata), 0, 0,
                                 width=A4[0], height=A4[1], mask="auto")
            except Exception:
                pass
        canvas.setStrokeColor(RULE)
        canvas.setLineWidth(0.4)
        canvas.line(20 * mm, 13 * mm, 190 * mm, 13 * mm)
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(MUTED)
        canvas.drawString(20 * mm, 9 * mm, "%s - Percorso PECS" % nome_studio)
        canvas.drawRightString(190 * mm, 9 * mm, "Pagina %d" % doc.page)
        canvas.restoreState()

    doc = BaseDocTemplate(buffer, pagesize=A4,
                          leftMargin=20 * mm, rightMargin=20 * mm,
                          topMargin=16 * mm, bottomMargin=18 * mm,
                          title="Percorso PECS - %s" % nominativo)
    frame = Frame(20 * mm, 18 * mm, LARGHEZZA, A4[1] - 34 * mm, id="corpo",
                  leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates([PageTemplate(id="std", frames=[frame],
                                       onPage=_decorazioni)])
    doc.build(story)
    return buffer.getvalue()
