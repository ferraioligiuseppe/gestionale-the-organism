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

INDIRIZZO = "Via De Rosa 46, Pagani (SA) · Via Tino di Camaino 23, Napoli · Studio Della Ragione, Via Balsamo 19, Sant'Agnello (NA)"
CONTATTI  = "Tel. 0815152334  |  Cell. 3921873914  |  apstheorganism@gmail.com"

def _logo_path():
    base = os.path.dirname(os.path.abspath(__file__))
    p = os.path.join(base, "assets", "logo.png")
    if os.path.exists(p):
        return p
    return None

def _pnev_logo_path():
    base = os.path.dirname(os.path.abspath(__file__))
    p = os.path.join(base, "assets", "pnev_logo.png")
    if os.path.exists(p):
        return p
    return None

def _intestazione_studio():
    """Dati di intestazione dello studio attivo.

    Prima la sessione; se non c'e', si rileggono dal database. Prima si
    guardava SOLO st.session_state["intestazione_studio"], che viene
    riempito al login: se la sessione era ripartita, se l'app si era
    ricaricata o se il login era passato per una strada diversa, quella
    chiave era vuota e i PDF uscivano con l'intestazione di ripiego senza
    che nulla lo segnalasse."""
    try:
        import streamlit as st
    except Exception:
        return {}
    d = st.session_state.get("intestazione_studio")
    # Il dizionario in sessione viene riempito al login. Se l'utente ha
    # caricato la carta intestata DOPO, quel dizionario esiste ma non la
    # contiene: fidarsene qui significava non rileggere mai il database e
    # continuare a stampare l'intestazione di ripiego. Si accetta la copia
    # in sessione solo se la carta c'e' davvero.
    if isinstance(d, dict) and d.get("carta_intestata_base64"):
        return d
    try:
        from modules.app_core import get_connection
        from modules.ui_intestazione_studio import get_intestazione_studio
        sid = int(st.session_state.get("studio_id") or 1)
        d = get_intestazione_studio(get_connection(), sid) or {}
        if d:
            st.session_state["intestazione_studio"] = d
        return d
    except Exception:
        return {}


def _carta_intestata_bytes():
    """Bytes dell'immagine carta intestata dello studio attivo (o None)."""
    try:
        import base64
        b64 = (_intestazione_studio() or {}).get("carta_intestata_base64")
        if b64:
            return base64.b64decode(b64)
    except Exception:
        pass
    return None


def _logo_studio_reader():
    """Logo caricato dallo studio (base64 nel database), se presente."""
    try:
        import base64
        from reportlab.lib.utils import ImageReader
        b64 = (_intestazione_studio() or {}).get("logo_base64")
        if b64:
            return ImageReader(io.BytesIO(base64.b64decode(b64)))
    except Exception:
        pass
    return None

def _draw_bg_carta(c):
    """Disegna la carta intestata a piena pagina se presente. True se disegnata."""
    data = _carta_intestata_bytes()
    if not data:
        return False
    try:
        from reportlab.lib.utils import ImageReader
        img = ImageReader(io.BytesIO(data))
        c.drawImage(img, 0, 0, width=W, height=H,
                    preserveAspectRatio=False, mask="auto")
        return True
    except Exception:
        return False

def draw_intestazione(c, professionista="", titolo=""):
    # Se lo studio ha una carta intestata, la usiamo come sfondo e saltiamo
    # l'intestazione "costruita" (logo+righe), perché la grafica la contiene già.
    if _draw_bg_carta(c):
        return
    # Senza immagine si costruisce l'intestazione. I dati sono quelli salvati
    # in «Intestazione dello studio»: indirizzo, contatti, titolo e logo.
    # Prima venivano ignorati e si stampavano sempre le costanti qui sotto,
    # quindi compilare quella schermata non cambiava nulla nei PDF.
    _d = _intestazione_studio() or {}
    _indirizzo = " · ".join(
        r.strip() for r in str(_d.get("indirizzo") or "").splitlines() if r.strip()
    ) or INDIRIZZO
    _contatti = (str(_d.get("contatti") or "").strip()
                 or str(_d.get("telefono") or "").strip()
                 or CONTATTI)
    titolo = titolo or _d.get("titolo_default") or ""
    logo = _logo_studio_reader() or _logo_path()
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
    c.drawCentredString(W/2, H-3.9*cm, _indirizzo)
    c.drawCentredString(W/2, H-4.25*cm, _contatti)

def draw_footer(c):
    # Con carta intestata il piè di pagina è già nella grafica: non disegnare nulla.
    if _carta_intestata_bytes():
        return
    _d = _intestazione_studio() or {}
    _indirizzo = " · ".join(
        r.strip() for r in str(_d.get("indirizzo") or "").splitlines() if r.strip()
    ) or INDIRIZZO
    _contatti = (str(_d.get("contatti") or "").strip()
                 or str(_d.get("telefono") or "").strip()
                 or CONTATTI)
    c.setStrokeColor(VERDE); c.setLineWidth(0.8)
    c.line(1.8*cm, 2.2*cm, W-1.8*cm, 2.2*cm)
    c.setFont("Helvetica-Bold", 8); c.setFillColor(colors.black)
    c.drawCentredString(W/2, 1.7*cm, _indirizzo)
    c.setFont("Helvetica", 8)
    c.drawCentredString(W/2, 1.2*cm, _contatti)

def genera_ricetta(professionista, titolo, rx) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    draw_intestazione(c, professionista, titolo)
    _draw_corpo_ricetta(c, rx)
    draw_footer(c)
    c.save(); buf.seek(0)
    return buf.read()

def _wrap_width(c, testo, font, size, max_w):
    """Manda a capo 'testo' in righe non piu' larghe di max_w (misura reale)."""
    parole = testo.split(" ")
    righe, cur = [], ""
    for p in parole:
        prova = (cur + " " + p).strip()
        if (not cur) or c.stringWidth(prova, font, size) <= max_w:
            cur = prova
        else:
            righe.append(cur)
            cur = p
    righe.append(cur)
    return righe


def _draw_justified(c, line, x0, yt, font, size, max_w):
    """Disegna 'line' giustificata: allarga gli spazi fino a max_w."""
    words = line.split(" ")
    words = [w for w in words if w != ""]
    if len(words) <= 1:
        c.drawString(x0, yt, line)
        return
    words_w = sum(c.stringWidth(w, font, size) for w in words)
    gaps = len(words) - 1
    normal_space = c.stringWidth(" ", font, size)
    riempimento = words_w / max_w if max_w else 1
    # Riga troppo corta rispetto alla colonna (es. ultima parola andata a capo
    # da sola su poche parole): giustificarla creerebbe spazi enormi. Sotto
    # l'85% di riempimento la disegniamo normale, senza allargare gli spazi.
    if riempimento < 0.85:
        c.drawString(x0, yt, line)
        return
    extra = (max_w - words_w) / gaps
    extra = min(extra, normal_space * 2.5)  # tetto: mai più di 2.5x lo spazio normale
    x = x0
    for w in words:
        c.drawString(x, yt, w)
        x += c.stringWidth(w, font, size) + extra


def genera_carta_intestata(professionista, titolo,
                            paziente, data, titolo_doc,
                            corpo_testo="", timbro_bytes=None) -> bytes:
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
    has_carta = bool(_carta_intestata_bytes())
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
    # Tronca paziente se troppo lungo
    paz_display = paziente[:70] if len(paziente)>70 else paziente
    c.drawString(4.0*cm, y2, paz_display)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(W-4.5*cm, y2, "Data:")
    c.setFont("Helvetica", 10)
    c.drawString(W-3.2*cm, y2, data)
    c.setStrokeColor(GRIGIO_L); c.setLineWidth(0.3)
    c.line(1.8*cm, y2-0.4*cm, W-1.8*cm, y2-0.4*cm)

    # Intro PNEV in TESTA e Bibliografia in CODA (testi da relazione_testi.py)
    try:
        from modules.relazione_testi import intro_pnev, bibliografia
        corpo_testo = intro_pnev() + "\n" + (corpo_testo or "") + "\n\n" + bibliografia()
    except Exception:
        pass

    # Corpo testo: a-capo per larghezza + giustificato (tranne titoli e ultime righe)
    if corpo_testo:
        x0 = 1.8*cm
        max_w = W - x0 - 4.2*cm   # margine destro ampio: libera la fascia della grafica
        yt = y2 - 0.9*cm
        for riga in corpo_testo.split("\n"):
            if riga.startswith("###"):
                font, size, col, heading = "Helvetica-Bold", 11, VERDE, True
                testo = riga.replace("###", "").strip()
            else:
                font, size, col, heading = "Helvetica", 10, colors.black, False
                testo = riga
            c.setFont(font, size); c.setFillColor(col)
            lines = _wrap_width(c, testo, font, size, max_w)
            for idx, sl in enumerate(lines):
                is_last = (idx == len(lines) - 1)
                if (not heading) and (not is_last) and sl.strip():
                    _draw_justified(c, sl, x0, yt, font, size, max_w)
                else:
                    c.drawString(x0, yt, sl)
                yt -= 0.55*cm
                if yt < 5.5*cm:
                    draw_footer(c)
                    c.showPage()
                    draw_intestazione(c, professionista, titolo)
                    yt = H - 5.0*cm

    # Firma
    yt_firma = 6.5*cm if has_carta else 5.5*cm
    # Timbro e firma del professionista (immagine), sopra la riga di destra.
    # Usa il timbro caricato dal professionista se presente, altrimenti
    # il timbro di default (modules/assets/timbro.png).
    try:
        from reportlab.lib.utils import ImageReader
        import os as _os
        if timbro_bytes:
            _timbro_src = ImageReader(io.BytesIO(timbro_bytes))
            _tw = 3.2*cm; _th = _tw  # proporzione gestita da preserveAspectRatio
        else:
            _tp = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "assets", "timbro.png")
            _timbro_src = ImageReader(_tp) if _os.path.exists(_tp) else None
            _tw = 3.2*cm; _th = _tw * 1918/1982
        if _timbro_src is not None:
            _tx = W/2 + 1*cm + ((W-1.8*cm) - (W/2+1*cm) - _tw)/2
            c.drawImage(_timbro_src, _tx, yt_firma+0.15*cm, width=_tw, height=_th,
                        preserveAspectRatio=True, mask="auto")
    except Exception:
        pass
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

    def _fax(v):
        # L'asse è in gradi (0–180): niente segno, niente decimali.
        if v is None or v == "" or v == 0: return ""
        try:
            return str(int(round(float(v))))
        except: return str(v).lstrip("+")

    def tabo(cx, cy, r=2.3*cm, label="", asse=None, cilindro=None):
        """Schema TABO con l'asse del cilindro effettivamente disegnato.

        Due correzioni rispetto a prima.

        1. L'asse non veniva disegnato. La riga verticale che si vedeva e'
           la tacca fissa dei 90 gradi, parte della griglia: quando l'asse
           era 90 sembrava indicato, per pura coincidenza, e con qualunque
           altro valore lo schema restava vuoto. Ora la linea dell'asse si
           disegna davvero, in verde e con il valore in gradi accanto.

        2. Le tacche erano specchiate. Il codice calcolava la posizione con
           (180 - gradi), quindi scriveva «30» dove sta il meridiano a 150 e
           viceversa, pur avendo 0 a destra e 180 a sinistra. Finche' non
           c'era una linea da leggerci contro non si notava; adesso si',
           quindi vanno rimesse al loro posto. La convenzione corretta e'
           quella TABO: 0 a destra, si sale in senso antiorario, 90 in alto,
           180 a sinistra.
        """
        c.setStrokeColor(GRIGIO_L); c.setLineWidth(0.5)
        c.arc(cx-r, cy-r, cx+r, cy+r, startAng=0, extent=180)
        c.line(cx-r-0.3*cm, cy, cx+r+0.3*cm, cy)
        c.line(cx, cy, cx, cy+r+0.2*cm)
        c.setFont("Helvetica",6); c.setFillColor(GRIGIO)
        for deg in [30,60,90,120,150]:
            rad = math.radians(deg)
            xp = cx+r*math.cos(rad); yp = cy+r*math.sin(rad)
            c.line(xp, yp, cx+(r+0.12*cm)*math.cos(rad),
                           cy+(r+0.12*cm)*math.sin(rad))
            c.drawCentredString(cx+(r+0.4*cm)*math.cos(rad),
                                cy+(r+0.4*cm)*math.sin(rad), str(deg))
        c.drawString(cx-r-0.65*cm, cy-0.1*cm, "180")
        c.drawString(cx+r+0.1*cm,  cy-0.1*cm, "0")
        c.setFont("Helvetica",7); c.drawCentredString(cx, cy+0.5*cm, "TABO")

        # ── L'asse misurato ───────────────────────────────────────────
        # Si disegna solo se c'e' un cilindro: un asse senza cilindro non
        # significa niente, e stamparlo sarebbe un dato inventato.
        _a = None
        try:
            if cilindro not in (None, "", 0) and float(cilindro) != 0.0:
                _a = float(asse) % 180
        except Exception:
            _a = None
        if _a is not None:
            _rad = math.radians(_a)
            _xe = cx + r*math.cos(_rad); _ye = cy + r*math.sin(_rad)
            c.setStrokeColor(VERDE); c.setLineWidth(1.6)
            c.line(cx, cy, _xe, _ye)
            c.setFillColor(VERDE); c.circle(_xe, _ye, 2.0, fill=1)
            # Il numero appena fuori dalla circonferenza, sulla direzione
            # dell'asse: si legge senza doverlo cercare fra le tacche.
            _lx = cx + (r+0.78*cm)*math.cos(_rad)
            _ly = cy + (r+0.78*cm)*math.sin(_rad)
            c.setFont("Helvetica-Bold", 8)
            c.drawCentredString(_lx, _ly-0.08*cm, f"{int(round(_a))}°")

        c.setFillColor(colors.black); c.circle(cx, cy, 1.5, fill=1)
        c.setFont("Helvetica",9); c.setFillColor(colors.black)
        c.drawCentredString(cx, cy-0.65*cm, label)

    y_sig = H - 5.0*cm
    c.setFont("Helvetica",10); c.setFillColor(colors.black)
    c.drawString(W-7*cm, y_sig+0.5*cm, "Data")
    c.setStrokeColor(GRIGIO_L); c.setLineWidth(0.5)
    c.line(W-6*cm, y_sig+0.5*cm, W-1.8*cm, y_sig+0.5*cm)
    c.setFont("Helvetica",13)
    c.drawString(1.8*cm, y_sig, "Sig.")
    c.line(3.5*cm, y_sig, W-1.8*cm, y_sig)

    # Riempie le righe Sig. e Data col nome paziente e la data
    _paz = str(rx.get("paziente", "")).strip()
    _dat = str(rx.get("data", "")).strip()
    if _paz:
        c.setFont("Helvetica", 12); c.setFillColor(colors.black)
        c.drawString(3.7*cm, y_sig+0.08*cm, _paz)
    if _dat:
        c.setFont("Helvetica", 10); c.setFillColor(colors.black)
        c.drawString(W-5.9*cm, y_sig+0.58*cm, _dat)

    y_tabo = H - 9.2*cm
    # L'asse mostrato e' quello della correzione per lontano, che e' la
    # riga di riferimento della ricetta.
    _lon = rx.get("lontano", {}) or {}
    _od_l = _lon.get("od", {}) or {}
    _os_l = _lon.get("os", {}) or {}
    tabo(W/2-5.5*cm, y_tabo, label="Occhio Destro",
         asse=_od_l.get("ax"), cilindro=_od_l.get("cil"))
    tabo(W/2+5.5*cm, y_tabo, label="Occhio Sinistro",
         asse=_os_l.get("ax"), cilindro=_os_l.get("cil"))

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
            v = _fax(od.get(k)) if k == "ax" else _f(od.get(k))
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
            v = _fax(os.get(k)) if k == "ax" else _f(os.get(k))
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
