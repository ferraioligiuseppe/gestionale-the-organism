# -*- coding: utf-8 -*-
"""
modules/questionari_cartacei.py

Versioni cartacee stampabili dei 7 questionari online (per chi non può
compilare da remoto). Stesse domande della versione digitale — le risposte
date su carta vanno poi trascritte a mano nel gestionale (nessun OCR).
"""
import streamlit as st
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT

_INTESTAZIONE = """
STUDIO THE ORGANISM — Metodo PNEV
Via De Rosa, 46 — 84016 Pagani (SA)  ·  Viale Marconi, 55 — 84013 Cava de' Tirreni (SA)
Tel. 081 515 2334 / 393 5817157  ·  apstheorganism@gmail.com
"""

_STILI = getSampleStyleSheet()
_S_TESTATA = ParagraphStyle("testata", parent=_STILI["Normal"], fontSize=8.5, leading=11, textColor=colors.HexColor("#555555"))
_S_TITOLO = ParagraphStyle("titolo", parent=_STILI["Heading1"], fontSize=15, spaceAfter=2, spaceBefore=0)
_S_SOTTO = ParagraphStyle("sotto", parent=_STILI["Normal"], fontSize=10, textColor=colors.HexColor("#444444"), spaceAfter=8)
_S_H3 = ParagraphStyle("h3", parent=_STILI["Heading3"], fontSize=11.5, spaceBefore=10, spaceAfter=4,
                       borderColor=colors.HexColor("#999999"))
_S_ITEM = ParagraphStyle("item", parent=_STILI["Normal"], fontSize=9.5, leading=13, spaceAfter=2)
_S_RADIO = ParagraphStyle("radio", parent=_STILI["Normal"], fontSize=9, leading=12.5, spaceAfter=3)
_S_LABEL = ParagraphStyle("label", parent=_STILI["Normal"], fontSize=10, spaceAfter=6)


def _pdf_bytes(titolo, sottotitolo, blocchi):
    """blocchi: lista di ('h3', testo) | ('item', [label,...]) | ('radio', [(n,a,b),...])
    | ('label', testo) | ('linea', n_righe) | ('checkbox_inline', testo)."""
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            topMargin=16*mm, bottomMargin=14*mm,
                            leftMargin=16*mm, rightMargin=16*mm)
    flow = []
    flow.append(Paragraph(_INTESTAZIONE.strip().replace("\n", "<br/>"), _S_TESTATA))
    flow.append(Spacer(1, 6))
    flow.append(Paragraph(titolo, _S_TITOLO))
    if sottotitolo:
        flow.append(Paragraph(sottotitolo, _S_SOTTO))
    flow.append(Paragraph("Paziente: ____________________________________&nbsp;&nbsp;&nbsp; Data: ____________", _S_LABEL))

    for kind, payload in blocchi:
        if kind == "h3":
            flow.append(Paragraph(payload, _S_H3))
        elif kind == "label":
            flow.append(Paragraph(payload, _S_LABEL))
        elif kind == "linea":
            for _ in range(payload):
                flow.append(Spacer(1, 4))
                flow.append(Table([[""]], colWidths=[170*mm], rowHeights=[0.1*mm],
                                  style=TableStyle([("LINEBELOW", (0,0), (-1,-1), 0.6, colors.HexColor("#999999"))])))
                flow.append(Spacer(1, 4))
        elif kind == "item":
            for label in payload:
                flow.append(Paragraph(f"☐&nbsp;&nbsp;{label}", _S_ITEM))
        elif kind == "radio":
            for num, a, b in payload:
                flow.append(Paragraph(f"<b>{num}.</b> ○ A: {a}", _S_RADIO))
                flow.append(Paragraph(f"&nbsp;&nbsp;&nbsp;&nbsp;○ B: {b}", _S_RADIO))
    doc.build(flow)
    return buf.getvalue()


def _label_of(it):
    return it[1] if isinstance(it, tuple) else it
    return f"""
    <div style="border-bottom:2px solid #333;padding-bottom:8px;margin-bottom:14px">
      <div style="font-size:11px;color:#555;white-space:pre-line">{_INTESTAZIONE.strip()}</div>
      <h2 style="margin:10px 0 2px 0">{titolo}</h2>
      {f'<div style="font-size:13px;color:#444">{sottotitolo}</div>' if sottotitolo else ''}
      <div style="font-size:12px;margin-top:8px">
        Paziente: ______________________________________&nbsp;&nbsp;&nbsp;
        Data: ______________
      </div>
    </div>
    """

def _checklist_html(items, cols=1):
    """items: lista di stringhe (o tuple code,label -> usa label)."""
    righe = []
    for it in items:
        label = it[1] if isinstance(it, tuple) else it
        righe.append(
            f'<div style="display:flex;gap:8px;padding:3px 0;font-size:13px">'
            f'<span style="display:inline-block;width:14px;height:14px;border:1.3px solid #333;flex-shrink:0"></span>'
            f'<span>{label}</span></div>'
        )
    if cols == 1:
        return "".join(righe)
    # 2 colonne
    metà = (len(righe) + 1) // 2
    c1 = "".join(righe[:metà]); c2 = "".join(righe[metà:])
    return (f'<div style="display:flex;gap:24px">'
           f'<div style="flex:1">{c1}</div><div style="flex:1">{c2}</div></div>')


def _radio_riga_html(num, testo_a, testo_b):
    return (
        f'<div style="font-size:12.5px;padding:5px 0;border-bottom:1px solid #eee">'
        f'<b>{num}.</b> '
        f'<span style="display:inline-block;width:13px;height:13px;border:1.2px solid #333;'
        f'border-radius:50%;margin-right:4px;vertical-align:-2px"></span> A: {testo_a}'
        f'&nbsp;&nbsp;&nbsp;'
        f'<span style="display:inline-block;width:13px;height:13px;border:1.2px solid #333;'
        f'border-radius:50%;margin-right:4px;vertical-align:-2px"></span> B: {testo_b}'
        f'</div>'
    )


def _doc_html(body_html):
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
    <style>
      body{{font-family:Arial,Helvetica,sans-serif;color:#111;max-width:760px;margin:0 auto;padding:24px}}
      h3{{margin:16px 0 6px 0;font-size:15px;border-left:3px solid #999;padding-left:8px}}
      @media print{{ body{{padding:0}} }}
    </style></head><body>{body_html}</body></html>"""


# ══════════════════════════════════════════════════════════════════
#  1. ANAMNESI PNEV
# ══════════════════════════════════════════════════════════════════
def _pdf_anamnesi_pnev():
    b = []
    b.append(("label", "Fascia d'età: ☐ 0-2 anni &nbsp; ☐ 2+ anni (bambino) &nbsp; ☐ Adulto"))
    b.append(("h3", "1. Gravidanza"))
    b.append(("label", "Termine gestazionale: ☐ Termine (38-42 sett.) ☐ Pre-termine (&lt;38) ☐ Post-termine (&gt;42) ☐ Non so"))
    b.append(("item", ["Ipertensione/pre-eclampsia","Diabete gestazionale","Infezioni","Sanguinamenti",
                       "Ricoveri","Farmaci importanti","Fumo/alcol/sostanze","Nessuna complicanza"]))
    b.append(("label", "Livello di stress vissuto: ☐ Basso ☐ Medio ☐ Alto ☐ Non so"))

    b.append(("h3", "2. Parto"))
    b.append(("label", "Tipo: ☐ Naturale ☐ Cesareo programmato ☐ Cesareo emergenza ☐ Ventosa/forcipe ☐ Non so"))
    b.append(("label", "Pianto immediato: ☐ Sì ☐ No ☐ Tardivo ☐ Non so"))
    b.append(("item", ["Sofferenza fetale","Cordone al collo","Necessità di rianimazione",
                       "Ricovero in terapia intensiva neonatale","Nessuna complicanza"]))

    b.append(("h3", "3. Alimentazione e primi mesi (bambini)"))
    b.append(("label", "Allattamento: ☐ Seno esclusivo ☐ Misto ☐ Artificiale ☐ Non so"))
    b.append(("item", ["Reflusso","Coliche intense","Vomito frequente","Rifiuto seno/biberon",
                       "Selettività alimentare marcata","Difficoltà masticazione/deglutizione","Nessuna"]))

    b.append(("h3", "4. Sviluppo motorio (bambini)"))
    b.append(("label", "Ha gattonato: ☐ Sì ☐ No (saltato) ☐ Parziale ☐ Non ancora"))
    b.append(("label", "Età dei primi passi autonomi (mesi): _________"))
    b.append(("label", "Cadute o goffaggine frequenti: ☐ No ☐ Qualche volta ☐ Spesso"))

    b.append(("h3", "5. Linguaggio e comunicazione (bambini)"))
    b.append(("label", "Età delle prime parole (mesi): _________"))
    b.append(("label", "Risponde quando lo si chiama per nome: ☐ Sempre ☐ Qualche volta ☐ Raramente/mai"))
    b.append(("label", "Contatto oculare: ☐ Buono ☐ Ridotto ☐ Assente/intermittente"))

    b.append(("h3", "6. Segnali che vi hanno preoccupato (bambini)"))
    b.append(("item", ["Perdita di abilità già acquisite","Movimenti ripetitivi","Sonno molto disturbato",
                       "Difficoltà alimentari gravi","Iper/ipo-reattività a rumori o luci",
                       "Cammino in punta di piedi","Nessuno di questi"]))

    b.append(("h3", "3-4. Sviluppo e apprendimento retrospettivo (adulti)"))
    b.append(("label", "Da bambino/a era descritto/a goffo/a o con scarsa coordinazione: ☐ No ☐ Un po' ☐ Marcatamente ☐ Non ricordo"))
    b.append(("item", ["Lettura/scrittura","Matematica","Attenzione/concentrazione",
                       "Organizzazione/pianificazione","Nessuna"]))
    b.append(("item", ["Sensibilità a rumori/luci forti","Fatica a leggere a lungo",
                       "Mal di testa/affaticamento visivo","Difficoltà di equilibrio","Nessuna di queste"]))

    b.append(("h3", "7. Familiarità (tutte le fasce)"))
    b.append(("item", ["Difficoltà di apprendimento (DSA)","ADHD","Disturbi del linguaggio",
                       "Problemi visivi importanti","Problemi uditivi","Disturbi neurologici",
                       "Ansia/depressione","Nessuna di queste"]))

    b.append(("h3", "8. Perché richiedete la valutazione?"))
    b.append(("label", "Descrivete brevemente la preoccupazione principale:"))
    b.append(("linea", 3))
    b.append(("label", "Da quanto tempo (mesi/anni): _________"))
    return _pdf_bytes("Anamnesi PNEV", "Gravidanza · Sviluppo · Familiarità · Motivo della richiesta", b)


# ══════════════════════════════════════════════════════════════════
#  2. INPP-R SCREENING (genitori)
# ══════════════════════════════════════════════════════════════════
def _pdf_inpps():
    neuro_items = [
        "C'è qualche caso di difficoltà di apprendimento fra i genitori o le loro famiglie?",
        "Durante la gravidanza c'è stato qualche problema medico? (pressione alta, nausea eccessiva, infezioni, stress)",
        "È stata una gravidanza a termine, pre-termine o post-termine?",
        "È stata la nascita particolarmente difficoltosa o anomala in qualche senso?",
        "Il bimbo era particolarmente piccolo per la età gestazionale?",
        "L'allattamento ha presentato particolari difficoltà?",
        "Il bimbo soffriva di coliche?",
        "Il bimbo ha avuto difficoltà a dormire (frequenti risvegli, addormentamento difficile)?",
        "Il bimbo ha avuto difficoltà nell'alimentazione (suzione, deglutizione, masticazione, selettività)?",
        "Ha gattonato? (se no, ha strisciato o ha saltato la fase?)",
        "Ha camminato tardi rispetto ai coetanei?",
        "È stato lento a diventare autonomo (vestirsi, allacciarsi, usare posate)?",
        "È goffo / inciampa spesso?",
        "Ha difficoltà con equilibrio (bicicletta, saltare, stare su un piede)?",
        "Ha difficoltà a prendere / lanciare / colpire una palla?",
        "Ha difficoltà con coordinazione fine (scrittura, forbici, puzzle)?",
        "Ha difficoltà a stare seduto fermo a lungo?",
        "È facilmente distraibile?",
        "È impulsivo / agisce senza riflettere?",
        "Ha difficoltà a seguire istruzioni (specialmente in sequenza)?",
        "Ha difficoltà a organizzare i compiti / pianificare?",
        "Ha difficoltà di lettura / comprensione del testo?",
        "Ha difficoltà di scrittura / ortografia?",
        "Ha difficoltà a copiare dalla lavagna?",
        "Ha difficoltà con matematica / calcolo?",
        "Ha difficoltà a ricordare ciò che ha letto/ascoltato?",
        "Ha difficoltà nelle relazioni con i pari (amicizie, integrazione)?",
        "Si frustra facilmente / scatti emotivi?",
        "Se c'è un rumore o movimento inaspettato, si spaventa facilmente?",
    ]
    gi = ["Colica","Dolori addominali o aerofagia","Frequenza anomala movimenti intestinali",
         "Stitichezza ricorrente","Diarrea"]
    skin = ["Eczema","Zone secche in viso o braccia","\u201cPelle di gallina\u201d su braccia/cosce","Dermatite","Altro"]
    ent = ["Ulcere sulla bocca","Respirazione difficoltosa","Tonsillite","Dolori di orecchie","Sinusite",
          "Muco persistente","Russa","Respirazione con la bocca","Febbre da fieno (rinite allergica)"]
    asma = ["Esercizio","Infezioni","Polvere","Muffa","Animali","Alimenti","Altro"]
    dev_hist = ["C'è stato un ritardo nello sviluppo motorio?","C'è stato un ritardo nello sviluppo del linguaggio?",
               "Otite di ripetizione?","Sospetti di difficoltà uditive con accertamenti?"]
    ascolto_ric = ["Brevi tempi di attenzione","Distraibilità","Ipersensibile ai suoni","Mal intende le domande",
                  "Confonde parole simili / necessita spesso ripetizioni","Incapace di seguire ordini in sequenza"]
    energia = ["Stanchezza alla fine della giornata","Iperattività","Tendenze depressive"]
    espressivo = ["Voce piatta e monotona","Discorso dubitativo","Scarso vocabolario","Povera costruzione delle frasi",
                 "Incapacità a cantare intonato","Confusione o inversione di lettere","Scarsa comprensione della lettura",
                 "Povera lettura ad alta voce","Povera ortografia"]
    sociale = ["Scarsa tollerabilità per la frustrazione","Povera immagine di sé","Difficoltà a fare amici",
              "Tendenza a rinchiudersi / evitare gli altri","Scarsa motivazione / disinteresse nei compiti scolastici",
              "Immaturità","Irritabilità","Timidezza"]

    b = [("label", "Diagnosi pregresse (dislessia, disprassia, ADHD, ecc.):"), ("linea", 1)]
    b.append(("h3", "Prima parte — Neurologica / sviluppo / scuola"))
    b.append(("item", neuro_items))
    b.append(("h3", "Seconda parte — Nutrizione / salute"))
    b.append(("label", "<b>Problemi gastro-intestinali</b>")); b.append(("item", gi))
    b.append(("label", "<b>Problemi di pelle</b>")); b.append(("item", skin))
    b.append(("label", "<b>Orecchio, Naso e Gola</b>")); b.append(("item", ent))
    b.append(("label", "<b>Asma — indotto da</b>")); b.append(("item", asma))
    b.append(("item", ["Sete particolarmente esagerata?"]))
    b.append(("h3", "Terza parte — Udito (Madaule)"))
    b.append(("label", "<b>Storia dello sviluppo</b>")); b.append(("item", dev_hist))
    b.append(("label", "<b>Ascolto ricettivo (esterno)</b>")); b.append(("item", ascolto_ric))
    b.append(("label", "<b>Livello di energia</b>")); b.append(("item", energia))
    b.append(("label", "<b>Ascolto espressivo (interno)</b>")); b.append(("item", espressivo))
    b.append(("label", "<b>Comportamento e integrazione sociale</b>")); b.append(("item", sociale))
    return _pdf_bytes("INPP-R — Screening riflessi primitivi",
                      "Questionario di Sally Goddard Blythe (INPP, Chester) — compilato dai genitori", b)


# ══════════════════════════════════════════════════════════════════
#  3. MELILLO ADULTI (100 A/B)
# ══════════════════════════════════════════════════════════════════
def _pdf_melillo_adulti():
    try:
        from modules.pnev.ui_questionari_pnev import MELILLO_ADULTI_DOMANDE
    except Exception:
        return _pdf_bytes("Melillo Adulti", "", [("label", "Domande non disponibili.")])
    b = [("radio", MELILLO_ADULTI_DOMANDE)]
    b.append(("label", "Totale A: _____ &nbsp;&nbsp; Totale B: _____ &nbsp;&nbsp; Differenza: _____ "
                       "&nbsp;&nbsp; Dominanza: ☐ Sinistra (A) ☐ Destra (B)"))
    return _pdf_bytes("Melillo Cognitive Style Assessment — Adulti",
                      "Cerchia A o B per ogni riga. Scegli in base alla tendenza naturale, non a quella appresa.", b)


# ══════════════════════════════════════════════════════════════════
#  4. MELILLO BAMBINI (checklist D/S)
# ══════════════════════════════════════════════════════════════════
def _pdf_melillo_bambini():
    try:
        from modules.pnev.ui_questionari_pnev import MELILLO_BAMBINI_DESTRO, MELILLO_BAMBINI_SINISTRO
    except Exception:
        return _pdf_bytes("Melillo Bambini", "", [("label", "Domande non disponibili.")])
    b = [("h3", "🔴 Ritardo Cerebrale Destro")]
    for categoria, voci in MELILLO_BAMBINI_DESTRO.items():
        b.append(("label", f"<b>{categoria}</b>")); b.append(("item", voci))
    b.append(("h3", "🔵 Ritardo Cerebrale Sinistro"))
    for categoria, voci in MELILLO_BAMBINI_SINISTRO.items():
        b.append(("label", f"<b>{categoria}</b>")); b.append(("item", voci))
    return _pdf_bytes("Melillo — Checklist Squilibrio Cerebrale Bambini",
                      "Seleziona le caratteristiche che descrivono il bambino/a", b)


# ══════════════════════════════════════════════════════════════════
#  5. FISHER AUDITIVO BAMBINI
# ══════════════════════════════════════════════════════════════════
def _pdf_fisher():
    try:
        from modules.pnev.ui_questionari_pnev import FISHER_ITEMS
    except Exception:
        return _pdf_bytes("Fisher Auditivo", "", [("label", "Domande non disponibili.")])
    b = [("label", "Grado scolastico: ______________________")]
    b.append(("item", [f"{n}. {label}" for n, label in FISHER_ITEMS]))
    return _pdf_bytes("Elenco di Controllo dei Problemi Uditivi di Fisher — Bambini",
                      "Metti un segno di spunta prima di ogni elemento considerato un problema", b)


# ══════════════════════════════════════════════════════════════════
#  6. VISIONE BAMBINI
# ══════════════════════════════════════════════════════════════════
def _pdf_visione_bambini():
    try:
        from modules.pnev.ui_questionari_pnev import (
            VISIONE_BAMBINI_SINTOMI, VISIONE_BAMBINI_OSSERVATI, VISIONE_BAMBINI_SVILUPPO)
    except Exception:
        return _pdf_bytes("Visione Bambini", "", [("label", "Domande non disponibili.")])
    b = [("h3", "Sintomi lamentati dal bambino"), ("item", [_label_of(x) for x in VISIONE_BAMBINI_SINTOMI])]
    b.append(("h3", "Problemi osservati dai genitori"))
    b.append(("item", [_label_of(x) for x in VISIONE_BAMBINI_OSSERVATI]))
    b.append(("h3", "Ritardi di sviluppo"))
    b.append(("item", [_label_of(x) for x in VISIONE_BAMBINI_SVILUPPO]))
    return _pdf_bytes("Questionario per la Visione del/la Bambino/a", "Fino a 11-12 anni", b)


# ══════════════════════════════════════════════════════════════════
#  7. VISIONE ADULTI
# ══════════════════════════════════════════════════════════════════
def _pdf_visione_adulti():
    try:
        from modules.pnev.ui_questionari_pnev import VISIONE_ADULTI_SINTOMI, VISIONE_ADULTI_ANAMNESI
    except Exception:
        return _pdf_bytes("Visione Adulti", "", [("label", "Domande non disponibili.")])
    b = [("h3", "Sintomi visivi presenti"), ("item", [_label_of(x) for x in VISIONE_ADULTI_SINTOMI])]
    b.append(("h3", "Anamnesi patologie (paziente/familiari)"))
    b.append(("item", [_label_of(x) for x in VISIONE_ADULTI_ANAMNESI]))
    b.append(("label", "Occupazione / lavoro prevalente: ______________________"))
    b.append(("label", "Ore/giorno al videoterminale: _____"))
    b.append(("label", "Note aggiuntive:"))
    b.append(("linea", 2))
    return _pdf_bytes("Questionario per la Visione dell'Adulto", "", b)


_GENERATORI = {
    "ANAMNESI_PNEV":   ("📋 Anamnesi PNEV", _pdf_anamnesi_pnev),
    "INPPS":           ("📋 INPP-R Screening (genitori)", _pdf_inpps),
    "MELILLO_ADULTI":  ("🧠 Melillo Adulti", _pdf_melillo_adulti),
    "MELILLO_BAMBINI": ("🧒 Melillo Bambini", _pdf_melillo_bambini),
    "FISHER":          ("👂 Fisher Auditivo", _pdf_fisher),
    "VISIONE_BAMBINI": ("👁️ Visione Bambini", _pdf_visione_bambini),
    "VISIONE_ADULTI":  ("👁️ Visione Adulti", _pdf_visione_adulti),
}


def render_questionari_cartacei():
    """Pannello: scegli un questionario, scarica la versione cartacea in PDF
    (stesse domande della versione online, in bianco)."""
    st.subheader("🖨️ Questionari — Versione cartacea")
    st.caption(
        "Stesse domande della versione online, da stampare e far compilare a mano "
        "quando il genitore/paziente non può farlo da remoto. Le risposte su carta "
        "vanno poi trascritte a mano nel questionario online per entrare nella relazione AI."
    )
    q_code = st.selectbox("Scegli il questionario", list(_GENERATORI.keys()),
                          format_func=lambda k: _GENERATORI[k][0], key="qc_scelta")
    label, fn = _GENERATORI[q_code]
    pdf_bytes = fn()
    st.download_button(
        f"⬇️ Scarica {label} (PDF)",
        data=pdf_bytes,
        file_name=f"{q_code.lower()}_cartaceo.pdf",
        mime="application/pdf",
        key=f"qc_dl_{q_code}",
    )
