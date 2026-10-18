"""
Genosociogramma — report PDF (ReportLab).

A4 verticale, come gli altri PDF del gestionale.
Pagina 1: il genogramma disegnato con la stessa geometria dell'SVG.
Pagine seguenti: ripetizioni da esplorare ed elenco delle persone.
Carta intestata: per default draw_intestazione/draw_footer di modules.pdf_templates
(immagine dello studio a piena pagina, oppure intestazione costruita).
"""
import io
import math
from datetime import datetime
from zoneinfo import ZoneInfo

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (Flowable, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle)
from xml.sax.saxutils import escape

from .render_genosociogramma import (GEN, H, INK, MUTED, anni_label, geometria, ripetizioni,
                                     tracciati_legame)

BRAND = colors.HexColor("#1D6B44")
TZ = ZoneInfo("Europe/Rome")


class GenogrammaFlowable(Flowable):
    """Disegna il genogramma scalato per stare nello spazio disponibile."""

    def __init__(self, g, max_w, max_h):
        super().__init__()
        self.el = geometria(g)
        self.scale = min(max_w / self.el["w"], max_h / self.el["h"], 1.6)
        self.width, self.height = self.el["w"] * self.scale, self.el["h"] * self.scale

    def wrap(self, aw, ah):
        return self.width, self.height

    def draw(self):
        c, el, k = self.canv, self.el, self.scale
        c.saveState()
        c.translate(0, self.height)
        c.scale(k, -k)  # coordinate come nell'SVG (y verso il basso)
        ink, muted, gen = colors.HexColor(INK), colors.HexColor(MUTED), colors.HexColor(GEN)
        c.setStrokeColor(ink)
        c.setLineWidth(1.6)
        for (x1, y1), (x2, y2) in el["segmenti"]:
            c.line(x1, y1, x2, y2)
        c.setDash(6, 4)
        for (x1, y1), (x2, y2) in el["tratteggi"]:
            c.line(x1, y1, x2, y2)
        c.setDash()
        c.setStrokeColor(gen)
        for lg in el["legami"]:
            linee, freccia = tracciati_legame(lg)
            for pts in linee:
                p = c.beginPath()
                p.moveTo(*pts[0])
                for x, y in pts[1:]:
                    p.lineTo(x, y)
                c.drawPath(p, stroke=1, fill=0)
            if freccia:
                (x0, y0), (x1, y1) = linee[0][-2], linee[0][-1]
                ang = math.atan2(y1 - y0, x1 - x0)
                p = c.beginPath()
                p.moveTo(x1, y1)
                p.lineTo(x1 - 8 * math.cos(ang - 0.4), y1 - 8 * math.sin(ang - 0.4))
                p.lineTo(x1 - 8 * math.cos(ang + 0.4), y1 - 8 * math.sin(ang + 0.4))
                p.close()
                c.setFillColor(gen)
                c.drawPath(p, stroke=0, fill=1)
        c.setStrokeColor(ink)
        c.setFillColor(colors.white)
        for f in el["figure"]:
            x, y = f["x"], f["y"]
            c.setLineWidth(1.8)
            if f["sesso"] == "F":
                c.circle(x, y, H, stroke=1, fill=1)
                if f["indice"]:
                    c.setLineWidth(1.4)
                    c.circle(x, y, H - 5, stroke=1, fill=0)
            elif f["sesso"] == "M":
                c.rect(x - H, y - H, 2 * H, 2 * H, stroke=1, fill=1)
                if f["indice"]:
                    c.setLineWidth(1.4)
                    c.rect(x - H + 5, y - H + 5, 2 * H - 10, 2 * H - 10, stroke=1, fill=0)
            else:
                p = c.beginPath()
                p.moveTo(x, y - H); p.lineTo(x + H, y); p.lineTo(x, y + H); p.lineTo(x - H, y); p.close()
                c.drawPath(p, stroke=1, fill=1)
            if f["morto"]:
                c.setLineWidth(1.6)
                c.line(x - H + 3, y - H + 3, x + H - 3, y + H - 3)
                c.line(x + H - 3, y - H + 3, x - H + 3, y + H - 3)
        # testi: si annulla il ribaltamento verticale solo localmente
        for f in el["figure"]:
            if f["eta"] is not None:
                self._testo(f["x"], f["y"] + 4, str(f["eta"]), 12, ink, True)
        for x, y, t, size, col, bold in el["testi"]:
            self._testo(x, y, str(t), size, colors.HexColor(col), bold)
        c.restoreState()

    def _testo(self, x, y, t, size, col, bold):
        c = self.canv
        c.saveState()
        c.translate(x, y)
        c.scale(1, -1)
        font = "Helvetica-Bold" if bold else "Helvetica"
        w = c.stringWidth(t, font, size)
        c.setFillColor(colors.white)
        c.rect(-w / 2 - 1.5, -size * 0.25, w + 3, size * 1.05, stroke=0, fill=1)
        c.setFillColor(col)
        c.setFont(font, size)
        c.drawCentredString(0, 0, t)
        c.restoreState()


def _intestazione_studio(canvas, doc):
    """Carta intestata del gestionale; se il modulo non c'è (test locali) non disegna nulla."""
    try:
        from modules.pdf_templates import draw_footer, draw_intestazione
    except Exception:
        return
    canvas.saveState()
    try:
        draw_intestazione(canvas, titolo="Genosociogramma")
        draw_footer(canvas)
    except Exception:
        pass
    canvas.restoreState()


def genera_pdf(g, paziente_label="", studio_label="", on_page=None):
    """Restituisce i byte del PDF. on_page(canvas, doc) disegna la carta intestata."""
    buf = io.BytesIO()
    pagesize = A4
    doc = SimpleDocTemplate(buf, pagesize=pagesize, leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=48 * mm, bottomMargin=50 * mm,
                            title=g.get("titolo", "Genosociogramma"), author=studio_label)
    ss = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=ss["Heading1"], textColor=BRAND, fontSize=16, spaceAfter=2)
    h2 = ParagraphStyle("h2", parent=ss["Heading2"], textColor=BRAND, fontSize=12, spaceBefore=10, spaceAfter=4)
    body = ParagraphStyle("b", parent=ss["BodyText"], fontSize=9.5, leading=13, alignment=TA_LEFT)
    small = ParagraphStyle("s", parent=body, fontSize=8.5, textColor=colors.HexColor(MUTED))

    oggi = datetime.now(TZ).strftime("%d/%m/%Y")
    st = [Paragraph(escape(g.get("titolo") or "Genosociogramma"), h1),
          Paragraph(escape(" · ".join(x for x in (paziente_label, f"aggiornato al {oggi}") if x)), small),
          Spacer(1, 4 * mm)]
    aw = pagesize[0] - 36 * mm
    ah = pagesize[1] - 48 * mm - 50 * mm - 45 * mm
    if g["persone"]:
        st.append(GenogrammaFlowable(g, aw, ah))
        st.append(Spacer(1, 3 * mm))
        st.append(Paragraph("Quadrato = maschio · cerchio = femmina · rombo = non noto · doppio contorno = paziente · "
                            "X = deceduto · numero = età attuale o alla morte. Legami in viola: due linee = stretto, "
                            "tre = fusionale, zig-zag = conflitto, linea con trattini = rottura, freccia = unidirezionale.",
                            small))
    else:
        st.append(Paragraph("Nessuna persona inserita.", body))

    st.append(PageBreak())
    r = ripetizioni(g)
    st.append(Paragraph("Ripetizioni da esplorare", h2))
    st.append(Paragraph("Spunti per il colloquio, non prove: le coincidenze sono frequenti in ogni famiglia.", small))
    sezioni = []
    if r["indice_eta"] is not None:
        sezioni.append((f"Alla stessa età del paziente ({r['indice_eta']} anni)", r["indice"]))
    sezioni += [("Stessa età alla morte", r["eta"]), ("Stesso giorno e mese", r["date"]), ("Nomi che ritornano", r["nomi"])]
    for titolo, voci in sezioni:
        st.append(Paragraph(f"<b>{escape(titolo)}</b>", body))
        for v in (voci or ["Nessuna rilevata."]):
            st.append(Paragraph("• " + escape(v), body))
        st.append(Spacer(1, 2 * mm))

    if g["persone"]:
        st.append(Paragraph("Persone", h2))
        by = {p["id"]: p for p in g["persone"]}
        rows = [["Nome", "Anni", "Causa / malattia", "Padre", "Madre", "Note"]]
        for p in g["persone"]:
            rows.append([
                Paragraph(escape((p.get("nome") or "") + (" (paziente)" if p.get("indice") else "")), body),
                anni_label(p),
                Paragraph(escape(p.get("causa") or ""), body),
                Paragraph(escape(by[p["padre"]]["nome"]) if p.get("padre") in by else "", body),
                Paragraph(escape(by[p["madre"]]["nome"]) if p.get("madre") in by else "", body),
                Paragraph(escape(p.get("note") or ""), body),
            ])
        t = Table(rows, colWidths=[30 * mm, 20 * mm, 30 * mm, 24 * mm, 24 * mm, aw - 128 * mm], repeatRows=1)
        t.setStyle(TableStyle([
            ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
            ("TEXTCOLOR", (0, 0), (-1, 0), BRAND),
            ("LINEBELOW", (0, 0), (-1, 0), 0.8, BRAND),
            ("LINEBELOW", (0, 1), (-1, -1), 0.3, colors.HexColor("#CAD4D2")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("FONTSIZE", (0, 1), (-1, -1), 9),
        ]))
        st.append(t)

    if g.get("note"):
        st.append(Paragraph("Note del clinico", h2))
        st.append(Paragraph(escape(g["note"]).replace("\n", "<br/>"), body))

    cb = on_page or _intestazione_studio
    doc.build(st, onFirstPage=cb, onLaterPages=cb)
    return buf.getvalue()


# ---------------------------------------------------------------- scheda cartacea
class _Legenda(Flowable):
    """Simboli da usare nel disegno a mano."""
    VOCI = [("M", "Maschio"), ("F", "Femmina"), ("X", "Deceduto (anno e causa accanto)"),
            ("P", "Tu (doppio contorno)"), ("U", "Coppia sposata (anno sopra)"), ("S", "Separati: una barra; divorziati: due"),
            ("C", "Figli, dal più grande a sinistra"), ("A", "Aborto o figlio nato morto: triangolo piccolo")]

    def __init__(self, width):
        super().__init__()
        self.width, self.height = width, 4 * 13 * mm

    def wrap(self, aw, ah):
        return self.width, self.height

    def draw(self):
        c = self.canv
        c.setStrokeColor(colors.HexColor(INK))
        c.setLineWidth(1.2)
        col_w = self.width / 2
        for i, (k, t) in enumerate(self.VOCI):
            x = (i % 2) * col_w + 6 * mm
            y = self.height - (i // 2) * 13 * mm - 8 * mm
            s = 3.2 * mm
            if k in ("M", "X"):
                c.rect(x - s, y - s, 2 * s, 2 * s)
                if k == "X":
                    c.line(x - s, y - s, x + s, y + s); c.line(x - s, y + s, x + s, y - s)
            elif k == "F":
                c.circle(x, y, s)
            elif k == "P":
                c.circle(x, y, s); c.circle(x, y, s - 1.2 * mm)
            elif k in ("U", "S"):
                c.line(x - 4 * mm, y + s, x - 4 * mm, y - s); c.line(x + 4 * mm, y + s, x + 4 * mm, y - s)
                c.line(x - 4 * mm, y - s, x + 4 * mm, y - s)
                if k == "S":
                    c.line(x - 1 * mm, y - s - 2 * mm, x + 1 * mm, y - s + 2 * mm)
            elif k == "C":
                c.line(x, y + s, x, y); c.line(x - 4 * mm, y, x + 4 * mm, y)
                c.line(x - 4 * mm, y, x - 4 * mm, y - s); c.line(x + 4 * mm, y, x + 4 * mm, y - s)
            elif k == "A":
                p = c.beginPath(); p.moveTo(x, y + 2 * mm); p.lineTo(x + 2 * mm, y - 1.5 * mm)
                p.lineTo(x - 2 * mm, y - 1.5 * mm); p.close(); c.drawPath(p, stroke=1, fill=0)
            c.setFont("Helvetica", 9)
            c.setFillColor(colors.HexColor(INK))
            c.drawString(x + 8 * mm, y - 1.2 * mm, t)


class _AreaDisegno(Flowable):
    """Riquadro per disegnare l'albero, con le righe delle generazioni."""
    RIGHE = ["Nonni", "Genitori, zii", "Tu, fratelli e sorelle, cugini", "Figli, nipoti"]

    def __init__(self, width, height):
        super().__init__()
        self.width, self.height = width, height

    def wrap(self, aw, ah):
        return self.width, self.height

    def draw(self):
        c = self.canv
        c.setStrokeColor(colors.HexColor("#9AA8A6"))
        c.setLineWidth(0.8)
        c.roundRect(0, 0, self.width, self.height, 3 * mm)
        step = self.height / len(self.RIGHE)
        c.setFont("Helvetica", 8.5)
        for i, t in enumerate(self.RIGHE):
            y = self.height - step * (i + 0.5)
            c.setDash(2, 3)
            c.line(4 * mm, y, self.width - 4 * mm, y)
            c.setDash()
            c.setFillColor(colors.HexColor(MUTED))
            c.drawString(4 * mm, y + 2 * mm, t)


def genera_scheda_cartacea(paziente_label="", on_page=None, righe_persone=24):
    """Scheda da stampare e compilare a mano. Restituisce i byte del PDF."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=48 * mm, bottomMargin=50 * mm, title="Genosociogramma — scheda da compilare")
    ss = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=ss["Heading1"], textColor=BRAND, fontSize=16, spaceAfter=4)
    h2 = ParagraphStyle("h2", parent=ss["Heading2"], textColor=BRAND, fontSize=12, spaceBefore=8, spaceAfter=4)
    body = ParagraphStyle("b", parent=ss["BodyText"], fontSize=10, leading=14)
    small = ParagraphStyle("s", parent=body, fontSize=8.5, leading=11, textColor=colors.HexColor(MUTED))
    aw = A4[0] - 36 * mm
    st = [Paragraph("Il tuo albero di famiglia", h1)]
    if paziente_label:
        st.append(Paragraph(escape(paziente_label), small))
    st += [
        Spacer(1, 3 * mm),
        Paragraph("Questa scheda serve a raccogliere la storia della tua famiglia su tre o quattro generazioni: "
                  "nonni, genitori e zii, tu con fratelli e sorelle, i figli. La guarderemo insieme in seduta.", body),
        Spacer(1, 2 * mm),
        Paragraph("<b>Come procedere</b>", body),
        Paragraph("1. Disegna prima l’albero a memoria, senza chiedere a nessuno: anche quello che non ricordi è utile.", body),
        Paragraph("2. Poi compila la tabella delle persone, una riga per ciascuna.", body),
        Paragraph("3. Nei giorni seguenti puoi verificare date e fatti con i familiari, documenti o fotografie. "
                  "Scrivi le correzioni con un altro colore, senza cancellare la prima versione.", body),
        Paragraph("4. Se non conosci una data o un fatto, metti un punto interrogativo.", body),
        Paragraph("Simboli da usare", h2),
        _Legenda(aw),
        Paragraph("Domande che possono aiutarti", h2),
    ]
    for d in ("Chi porta il tuo nome, o un nome simile, prima di te?",
              "Quali date della tua famiglia ti vengono in mente per prime?",
              "C’è qualcuno di cui in famiglia non si parla, o che è stato dimenticato?",
              "C’è un evento della tua vita che ti sembra ripetere qualcosa già successo ad altri?",
              "Alla tua età di oggi, che cosa stava succedendo ai tuoi genitori e ai tuoi nonni?"):
        st.append(Paragraph("• " + escape(d), body))
    st += [PageBreak(), Paragraph("Disegna qui il tuo albero", h1),
           Paragraph("Una figura per persona, sulla riga della sua generazione. Accanto a ciascuna scrivi nome, "
                     "anno di nascita e, se è morta, anno e causa.", small),
           Spacer(1, 3 * mm), _AreaDisegno(aw, A4[1] - 48 * mm - 50 * mm - 30 * mm), PageBreak(),
           Paragraph("Le persone della famiglia", h1),
           Paragraph("Una riga per persona. Date come gg/mm/aaaa quando le conosci, altrimenti solo l’anno.", small),
           Spacer(1, 3 * mm)]
    head = ["Nome e cognome", "Parentela con te", "Nascita", "Morte (data e causa)",
            "Malattie, eventi, mestiere", "Note"]
    hst = ParagraphStyle("hd", parent=body, fontName="Helvetica-Bold", fontSize=8, leading=9.5, textColor=BRAND)
    rows = [[Paragraph(h, hst) for h in head]] + [[""] * 6 for _ in range(righe_persone)]
    t = Table(rows, colWidths=[32 * mm, 24 * mm, 20 * mm, 28 * mm, 34 * mm, aw - 138 * mm],
              rowHeights=[None] + [11 * mm] * righe_persone, repeatRows=1)
    t.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8.5),
        ("TEXTCOLOR", (0, 0), (-1, 0), BRAND),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#9AA8A6")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEF5F1")),
    ]))
    st += [t, PageBreak(), Paragraph("Altro che vuoi raccontare", h1),
           Paragraph("Rapporti stretti o difficili, rotture, persone escluse, segreti, traslochi ed emigrazioni, "
                     "guerre, lutti, eredità: tutto quello che senti importante.", small), Spacer(1, 4 * mm)]
    righe = Table([[""] for _ in range(16)], colWidths=[aw], rowHeights=[9 * mm] * 16)
    righe.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#9AA8A6"))]))
    st.append(righe)
    st += [Spacer(1, 6 * mm),
           Paragraph("I dati che scrivi, anche quelli sulla salute dei tuoi familiari, restano nello studio e servono "
                     "solo al tuo percorso clinico.", small)]
    cb = on_page or _intestazione_studio
    doc.build(st, onFirstPage=cb, onLaterPages=cb)
    return buf.getvalue()
