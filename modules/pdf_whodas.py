# -*- coding: utf-8 -*-
"""
modules/whodas/pdf_whodas.py
Referto PDF della somministrazione WHODAS 2.0 (36 item, intervistatore).
ReportLab, verde istituzionale #1D6B44, testo giustificato, carta intestata per studio.
"""

from io import BytesIO
from datetime import datetime
from zoneinfo import ZoneInfo

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle,
    Image, KeepTogether,
)

from .db_whodas import (
    DOMINI, ITEM_TESTO, items_del_dominio, SCALA, ATTRIBUZIONE,
    DOMANDE_ACCESSORIE, calcola_punteggi,
)

TZ = ZoneInfo("Europe/Rome")

VERDE = colors.HexColor("#1D6B44")
VERDE_CHIARO = colors.HexColor("#E8F1EC")
GRIGIO = colors.HexColor("#666666")

ETICHETTE_SITUAZIONE = {
    1: "Indipendente nella comunità",
    2: "Assistito a domicilio",
    3: "Ricoverato in ospedale o ospite di struttura residenziale",
}
ETICHETTE_STATO_CIVILE = {
    1: "Nubile/Celibe", 2: "Attualmente sposato/a", 3: "Separato/a",
    4: "Divorziato/a", 5: "Vedovo/a", 6: "Convivente",
}
ETICHETTE_ATTIVITA = {
    1: "Lavoro retribuito", 2: "Lavoro autonomo", 3: "Lavoro non retribuito",
    4: "Studente/ssa", 5: "Casalingo/a", 6: "In pensione",
    7: "Non occupato/a (motivi di salute)", 8: "Non occupato/a (altri motivi)",
    9: "Altro",
}


def _stili():
    ss = getSampleStyleSheet()
    return {
        "titolo": ParagraphStyle(
            "titolo", parent=ss["Title"], fontName="Helvetica-Bold",
            fontSize=16, textColor=VERDE, spaceAfter=2 * mm,
        ),
        "sottotitolo": ParagraphStyle(
            "sottotitolo", parent=ss["Normal"], fontName="Helvetica",
            fontSize=9.5, textColor=GRIGIO, alignment=TA_CENTER, spaceAfter=6 * mm,
        ),
        "h2": ParagraphStyle(
            "h2", parent=ss["Heading2"], fontName="Helvetica-Bold",
            fontSize=11.5, textColor=VERDE, spaceBefore=5 * mm, spaceAfter=2 * mm,
        ),
        "corpo": ParagraphStyle(
            "corpo", parent=ss["Normal"], fontName="Helvetica", fontSize=9.5,
            leading=13, alignment=TA_JUSTIFY, spaceAfter=2 * mm,
        ),
        "cella": ParagraphStyle(
            "cella", parent=ss["Normal"], fontName="Helvetica", fontSize=8.5, leading=11,
        ),
        "nota": ParagraphStyle(
            "nota", parent=ss["Normal"], fontName="Helvetica-Oblique", fontSize=7.5,
            leading=10, textColor=GRIGIO, alignment=TA_JUSTIFY,
        ),
    }


def _barra(valore_pct, larghezza=45 * mm, altezza=4 * mm):
    """Barra orizzontale proporzionale al punteggio 0-100, come mini-tabella."""
    if valore_pct is None:
        return ""
    pieno = max(0.5, larghezza * float(valore_pct) / 100.0)
    t = Table([[""]], colWidths=[pieno], rowHeights=[altezza])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), VERDE),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return t


def genera_pdf(paziente, testata, risposte, carta_intestata=None,
               includi_dettaglio_item=True, storico=None):
    """
    paziente: dict con almeno {"nome_completo": str, "data_nascita": date|None,
                               "codice": str|None}
    testata:  dict restituito da carica_somministrazione()
    risposte: dict {codice_item: 1-5}
    carta_intestata: path o file-like dell'immagine di intestazione dello studio
    storico:  output di serie_storica() per la tabella di andamento (opzionale)

    Restituisce BytesIO pronto per il download.
    """
    st = _stili()
    buf = BytesIO()

    margine_sup = 42 * mm if carta_intestata else 20 * mm

    doc = BaseDocTemplate(
        buf, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=margine_sup, bottomMargin=18 * mm,
        title=f"WHODAS 2.0 — {paziente.get('nome_completo', '')}",
        author="Studio The Organism",
    )

    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="corpo")

    def _decora(canvas, documento):
        canvas.saveState()
        if carta_intestata:
            try:
                canvas.drawImage(
                    carta_intestata, doc.leftMargin, A4[1] - 36 * mm,
                    width=doc.width, height=24 * mm,
                    preserveAspectRatio=True, anchor="nw", mask="auto",
                )
            except Exception:
                pass
        canvas.setStrokeColor(VERDE)
        canvas.setLineWidth(0.6)
        canvas.line(doc.leftMargin, 14 * mm, A4[0] - doc.rightMargin, 14 * mm)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(GRIGIO)
        canvas.drawString(doc.leftMargin, 10 * mm, "WHODAS 2.0 — versione a 36 item, somministrata da un intervistatore")
        canvas.drawRightString(A4[0] - doc.rightMargin, 10 * mm, f"Pag. {documento.page}")
        canvas.restoreState()

    doc.addPageTemplates([PageTemplate(id="std", frames=[frame], onPage=_decora)])

    punteggi = calcola_punteggi(risposte, testata.get("lavora_studia", True))
    el = []

    # --- Intestazione ------------------------------------------------------ #
    el.append(Paragraph("WHODAS 2.0 — Profilo di funzionamento", st["titolo"]))
    el.append(Paragraph(
        "World Health Organization Disability Assessment Schedule 2.0 · "
        "versione a 36 item, somministrata da un intervistatore",
        st["sottotitolo"],
    ))

    data_somm = testata.get("data_somministrazione")
    data_txt = data_somm.strftime("%d/%m/%Y") if data_somm else "—"
    nascita = paziente.get("data_nascita")
    nascita_txt = nascita.strftime("%d/%m/%Y") if nascita else "—"

    anagrafica = [
        ["Paziente", paziente.get("nome_completo", "—"), "Data somministrazione", data_txt],
        ["Data di nascita", nascita_txt, "N. intervista", str(testata.get("numero_intervista") or "—")],
        ["Età", str(testata.get("eta") or "—"), "Anni di scuola", str(testata.get("anni_scuola") or "—")],
        ["Stato civile", ETICHETTE_STATO_CIVILE.get(testata.get("stato_civile"), "—"),
         "Attività lavorativa", ETICHETTE_ATTIVITA.get(testata.get("attivita_lavorativa"), "—")],
        ["Situazione di vita", ETICHETTE_SITUAZIONE.get(testata.get("situazione_vita"), "—"),
         "Intervistatore", testata.get("id_intervistatore") or "—"],
    ]
    t = Table(anagrafica, colWidths=[30 * mm, 52 * mm, 34 * mm, 58 * mm])
    t.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "Helvetica", 8.5),
        ("FONT", (0, 0), (0, -1), "Helvetica-Bold", 8.5),
        ("FONT", (2, 0), (2, -1), "Helvetica-Bold", 8.5),
        ("TEXTCOLOR", (0, 0), (0, -1), VERDE),
        ("TEXTCOLOR", (2, 0), (2, -1), VERDE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("LINEBELOW", (0, 0), (-1, -2), 0.25, colors.HexColor("#DDDDDD")),
        ("BOX", (0, 0), (-1, -1), 0.5, VERDE),
    ]))
    el.append(t)

    # --- Punteggi di dominio ----------------------------------------------- #
    el.append(Paragraph("Punteggi per dominio", st["h2"]))

    righe = [["Dominio", "Item", "Somma\ngrezza", "Semplice\n(0-100)", "IRT\n(0-100)", ""]]
    for dominio, meta in DOMINI.items():
        p = punteggi["domini"].get(dominio)
        if p is None:
            if dominio == "5(2)" and not testata.get("lavora_studia", True):
                righe.append([Paragraph(f"{dominio} — {meta['titolo']}", st["cella"]),
                              "—", "n.a.", "n.a.", "n.a.", ""])
            else:
                righe.append([Paragraph(f"{dominio} — {meta['titolo']}", st["cella"]),
                              "—", "incompleto", "—", "—", ""])
            continue
        righe.append([
            Paragraph(f"{dominio} — {meta['titolo']}", st["cella"]),
            str(p["n_item"]),
            str(p["semplice_grezzo"]),
            f"{p['semplice_pct']:.1f}",
            f"{p['irt']:.1f}",
            _barra(p["irt"]),
        ])

    t = Table(righe, colWidths=[58 * mm, 11 * mm, 16 * mm, 19 * mm, 16 * mm, 48 * mm])
    t.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8),
        ("FONT", (0, 1), (-1, -1), "Helvetica", 8.5),
        ("BACKGROUND", (0, 0), (-1, 0), VERDE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (1, 0), (4, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, VERDE_CHIARO]),
        ("GRID", (0, 0), (4, -1), 0.4, colors.HexColor("#CCCCCC")),
        ("BOX", (0, 0), (-1, -1), 0.5, VERDE),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    el.append(t)

    # --- Punteggio totale --------------------------------------------------- #
    el.append(Paragraph("Punteggio totale", st["h2"]))
    tot = punteggi["totale"]
    if tot is None:
        el.append(Paragraph(
            "Il punteggio totale non è calcolabile: mancano le risposte agli item "
            + ", ".join(punteggi["item_mancanti"]) + ".",
            st["corpo"],
        ))
    else:
        base = "36 item (lavoro/studio inclusi)" if testata.get("lavora_studia", True) \
            else "32 item (lavoro/studio non applicabili)"
        griglia = [
            ["Base di calcolo", base],
            ["Punteggio semplice (somma)",
             f"{tot['semplice_grezzo']} su un intervallo {tot['semplice_min']}–{tot['semplice_max']}"],
            ["Punteggio semplice normalizzato", f"{tot['semplice_pct']:.1f} / 100"],
            ["Punteggio complesso (IRT)", f"{tot['irt']:.1f} / 100"],
            ["Percentile di popolazione generale", f"{tot['percentile']:.1f}°"],
        ]
        t = Table(griglia, colWidths=[68 * mm, 106 * mm])
        t.setStyle(TableStyle([
            ("FONT", (0, 0), (-1, -1), "Helvetica", 9),
            ("FONT", (0, 0), (0, -1), "Helvetica-Bold", 9),
            ("FONT", (0, 3), (-1, 4), "Helvetica-Bold", 9.5),
            ("TEXTCOLOR", (0, 0), (0, -1), VERDE),
            ("BACKGROUND", (0, 3), (-1, 4), VERDE_CHIARO),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CCCCCC")),
            ("BOX", (0, 0), (-1, -1), 0.5, VERDE),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        el.append(t)
        el.append(Spacer(1, 2 * mm))
        el.append(Paragraph(
            "Su entrambe le scale 0 indica assenza di disabilità e 100 disabilità totale. "
            "Il punteggio semplice è specifico del campione esaminato e non è indicato per "
            "confronti tra popolazioni; il punteggio complesso basato sulla teoria della "
            "risposta all'item pondera item e livelli di gravità ed è quello impiegato per "
            "il confronto con le norme di popolazione (Tabella 6.1 del manuale).",
            st["nota"],
        ))

    # --- Giorni di difficoltà ---------------------------------------------- #
    giorni = [
        ("H1", testata.get("h1_giorni")),
        ("H2", testata.get("h2_giorni")),
        ("H3", testata.get("h3_giorni")),
    ]
    if any(v is not None for _c, v in giorni):
        el.append(Paragraph("Giorni di difficoltà negli ultimi 30 giorni", st["h2"]))
        righe = [[Paragraph(DOMANDE_ACCESSORIE[c], st["cella"]),
                  str(v) if v is not None else "—"] for c, v in giorni]
        t = Table(righe, colWidths=[152 * mm, 22 * mm])
        t.setStyle(TableStyle([
            ("FONT", (0, 0), (-1, -1), "Helvetica", 8.5),
            ("ALIGN", (1, 0), (1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CCCCCC")),
            ("BOX", (0, 0), (-1, -1), 0.5, VERDE),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        el.append(t)

    # --- Andamento nel tempo ------------------------------------------------ #
    if storico and len(storico) > 1:
        intest = ["Dominio"] + [s["data"].strftime("%d/%m/%y") for s in storico]
        righe = [intest]
        for dominio, meta in DOMINI.items():
            riga = [Paragraph(f"{dominio} — {meta['titolo']}", st["cella"])]
            for s in storico:
                p = s["punteggi"]["domini"].get(dominio)
                riga.append(f"{p['irt']:.1f}" if p else "—")
            righe.append(riga)
        riga_tot = [Paragraph("<b>Totale (IRT)</b>", st["cella"])]
        for s in storico:
            t_ = s["punteggi"]["totale"]
            riga_tot.append(f"{t_['irt']:.1f}" if t_ else "—")
        righe.append(riga_tot)

        larghezza_col = min(20 * mm, (174 * mm - 62 * mm) / max(1, len(storico)))
        t = Table(righe, colWidths=[62 * mm] + [larghezza_col] * len(storico))
        t.setStyle(TableStyle([
            ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8),
            ("FONT", (0, 1), (-1, -1), "Helvetica", 8.5),
            ("BACKGROUND", (0, 0), (-1, 0), VERDE),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("BACKGROUND", (0, -1), (-1, -1), VERDE_CHIARO),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CCCCCC")),
            ("BOX", (0, 0), (-1, -1), 0.5, VERDE),
        ]))
        el.append(KeepTogether([
            Paragraph("Andamento nel tempo", st["h2"]),
            t,
            Spacer(1, 1.5 * mm),
            Paragraph(
                "Valori sulla scala IRT 0-100: una riduzione indica un miglioramento del "
                "funzionamento rispetto alla somministrazione precedente.",
                st["nota"],
            ),
        ]))

    # --- Dettaglio item ----------------------------------------------------- #
    if includi_dettaglio_item:
        el.append(Paragraph("Dettaglio delle risposte", st["h2"]))
        for dominio, meta in DOMINI.items():
            if dominio == "5(2)" and not testata.get("lavora_studia", True):
                continue
            righe = [["", f"{dominio} — {meta['titolo']}", "Risposta"]]
            for codice, testo in items_del_dominio(dominio):
                v = risposte.get(codice)
                righe.append([
                    codice,
                    Paragraph(testo, st["cella"]),
                    Paragraph(f"{v} · {SCALA[v]}" if v else "—", st["cella"]),
                ])
            t = Table(righe, colWidths=[13 * mm, 111 * mm, 50 * mm])
            t.setStyle(TableStyle([
                ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8.5),
                ("FONT", (0, 1), (0, -1), "Helvetica-Bold", 8),
                ("BACKGROUND", (0, 0), (-1, 0), VERDE_CHIARO),
                ("TEXTCOLOR", (0, 0), (-1, 0), VERDE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#DDDDDD")),
                ("BOX", (0, 0), (-1, -1), 0.5, VERDE),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]))
            el.append(KeepTogether([t, Spacer(1, 3 * mm)]))

    if testata.get("note"):
        el.append(Paragraph("Note del clinico", st["h2"]))
        el.append(Paragraph(testata["note"], st["corpo"]))

    # --- Attribuzione ------------------------------------------------------- #
    el.append(Spacer(1, 4 * mm))
    el.append(Paragraph(ATTRIBUZIONE, st["nota"]))
    el.append(Paragraph(
        f"Referto generato il {datetime.now(TZ).strftime('%d/%m/%Y alle %H:%M')}.",
        st["nota"],
    ))

    doc.build(el)
    buf.seek(0)
    return buf
