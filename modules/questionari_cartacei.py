# -*- coding: utf-8 -*-
"""
modules/questionari_cartacei.py

Versioni cartacee stampabili dei 7 questionari online (per chi non può
compilare da remoto). Stesse domande della versione digitale — le risposte
date su carta vanno poi trascritte a mano nel gestionale (nessun OCR).
"""
import streamlit as st

_INTESTAZIONE = """
STUDIO THE ORGANISM — Metodo PNEV
Via De Rosa, 46 — 84016 Pagani (SA)  ·  Viale Marconi, 55 — 84013 Cava de' Tirreni (SA)
Tel. 081 515 2334 / 393 5817157  ·  apstheorganism@gmail.com
"""

def _html_head(titolo, sottotitolo=""):
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
    b = [_html_head("Anamnesi PNEV", "Gravidanza · Sviluppo · Familiarità · Motivo della richiesta")]
    b.append('<p style="font-size:12px">Fascia d\'età: ☐ 0-2 anni &nbsp; ☐ 2+ anni (bambino) &nbsp; ☐ Adulto</p>')

    b.append("<h3>1. Gravidanza</h3>")
    b.append("<p style='font-size:12.5px'>Termine gestazionale: ☐ Termine (38-42 sett.) ☐ Pre-termine (&lt;38) ☐ Post-termine (&gt;42) ☐ Non so</p>")
    b.append(_checklist_html(["Ipertensione/pre-eclampsia","Diabete gestazionale","Infezioni","Sanguinamenti",
                             "Ricoveri","Farmaci importanti","Fumo/alcol/sostanze","Nessuna complicanza"], cols=2))
    b.append("<p style='font-size:12.5px'>Livello di stress vissuto: ☐ Basso ☐ Medio ☐ Alto ☐ Non so</p>")

    b.append("<h3>2. Parto</h3>")
    b.append("<p style='font-size:12.5px'>Tipo: ☐ Naturale ☐ Cesareo programmato ☐ Cesareo emergenza ☐ Ventosa/forcipe ☐ Non so</p>")
    b.append("<p style='font-size:12.5px'>Pianto immediato: ☐ Sì ☐ No ☐ Tardivo ☐ Non so</p>")
    b.append(_checklist_html(["Sofferenza fetale","Cordone al collo","Necessità di rianimazione",
                             "Ricovero in terapia intensiva neonatale","Nessuna complicanza"], cols=2))

    b.append("<h3>3. Alimentazione e primi mesi (bambini)</h3>")
    b.append("<p style='font-size:12.5px'>Allattamento: ☐ Seno esclusivo ☐ Misto ☐ Artificiale ☐ Non so</p>")
    b.append(_checklist_html(["Reflusso","Coliche intense","Vomito frequente","Rifiuto seno/biberon",
                             "Selettività alimentare marcata","Difficoltà masticazione/deglutizione","Nessuna"], cols=2))

    b.append("<h3>4. Sviluppo motorio (bambini)</h3>")
    b.append("<p style='font-size:12.5px'>Ha gattonato: ☐ Sì ☐ No (saltato) ☐ Parziale ☐ Non ancora</p>")
    b.append("<p style='font-size:12.5px'>Età dei primi passi autonomi (mesi): _________</p>")
    b.append("<p style='font-size:12.5px'>Cadute o goffaggine frequenti: ☐ No ☐ Qualche volta ☐ Spesso</p>")

    b.append("<h3>5. Linguaggio e comunicazione (bambini)</h3>")
    b.append("<p style='font-size:12.5px'>Età delle prime parole (mesi): _________</p>")
    b.append("<p style='font-size:12.5px'>Risponde quando lo si chiama per nome: ☐ Sempre ☐ Qualche volta ☐ Raramente/mai</p>")
    b.append("<p style='font-size:12.5px'>Contatto oculare: ☐ Buono ☐ Ridotto ☐ Assente/intermittente</p>")

    b.append("<h3>6. Segnali che vi hanno preoccupato (bambini)</h3>")
    b.append(_checklist_html(["Perdita di abilità già acquisite","Movimenti ripetitivi","Sonno molto disturbato",
                             "Difficoltà alimentari gravi","Iper/ipo-reattività a rumori o luci",
                             "Cammino in punta di piedi","Nessuno di questi"], cols=2))

    b.append("<h3>3-4. Sviluppo e apprendimento retrospettivo (adulti)</h3>")
    b.append("<p style='font-size:12.5px'>Da bambino/a era descritto/a goffo/a o con scarsa coordinazione: ☐ No ☐ Un po' ☐ Marcatamente ☐ Non ricordo</p>")
    b.append(_checklist_html(["Lettura/scrittura","Matematica","Attenzione/concentrazione",
                             "Organizzazione/pianificazione","Nessuna"], cols=2))
    b.append(_checklist_html(["Sensibilità a rumori/luci forti","Fatica a leggere a lungo",
                             "Mal di testa/affaticamento visivo","Difficoltà di equilibrio","Nessuna di queste"], cols=2))

    b.append("<h3>7. Familiarità (tutte le fasce)</h3>")
    b.append(_checklist_html(["Difficoltà di apprendimento (DSA)","ADHD","Disturbi del linguaggio",
                             "Problemi visivi importanti","Problemi uditivi","Disturbi neurologici",
                             "Ansia/depressione","Nessuna di queste"], cols=2))

    b.append("<h3>8. Perché richiedete la valutazione?</h3>")
    b.append('<p style="font-size:12.5px">Descrivete brevemente la preoccupazione principale:</p>')
    b.append('<div style="border-bottom:1px solid #999;height:20px;margin-bottom:6px"></div>' * 3)
    b.append('<p style="font-size:12.5px">Da quanto tempo (mesi/anni): _________</p>')
    return _doc_html("".join(b))


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

    b = [_html_head("INPP-R — Screening riflessi primitivi", "Questionario di Sally Goddard Blythe (INPP, Chester) — compilato dai genitori")]
    b.append('<p style="font-size:12px">Diagnosi pregresse (dislessia, disprassia, ADHD, ecc.):</p>')
    b.append('<div style="border-bottom:1px solid #999;height:20px;margin-bottom:8px"></div>')
    b.append("<h3>Prima parte — Neurologica / sviluppo / scuola</h3>")
    b.append(_checklist_html(neuro_items))
    b.append("<h3>Seconda parte — Nutrizione / salute</h3>")
    b.append("<p style='font-size:12.5px'><b>Problemi gastro-intestinali</b></p>" + _checklist_html(gi, cols=2))
    b.append("<p style='font-size:12.5px'><b>Problemi di pelle</b></p>" + _checklist_html(skin, cols=2))
    b.append("<p style='font-size:12.5px'><b>Orecchio, Naso e Gola</b></p>" + _checklist_html(ent, cols=2))
    b.append("<p style='font-size:12.5px'><b>Asma — indotto da</b></p>" + _checklist_html(asma, cols=2))
    b.append(_checklist_html(["Sete particolarmente esagerata?"]))
    b.append("<h3>Terza parte — Udito (Madaule)</h3>")
    b.append("<p style='font-size:12.5px'><b>Storia dello sviluppo</b></p>" + _checklist_html(dev_hist))
    b.append("<p style='font-size:12.5px'><b>Ascolto ricettivo (esterno)</b></p>" + _checklist_html(ascolto_ric, cols=2))
    b.append("<p style='font-size:12.5px'><b>Livello di energia</b></p>" + _checklist_html(energia))
    b.append("<p style='font-size:12.5px'><b>Ascolto espressivo (interno)</b></p>" + _checklist_html(espressivo, cols=2))
    b.append("<p style='font-size:12.5px'><b>Comportamento e integrazione sociale</b></p>" + _checklist_html(sociale, cols=2))
    return _doc_html("".join(b))


# ══════════════════════════════════════════════════════════════════
#  3. MELILLO ADULTI (100 A/B) — importa le domande dal modulo esistente
# ══════════════════════════════════════════════════════════════════
def _pdf_melillo_adulti():
    try:
        from modules.pnev.ui_questionari_pnev import MELILLO_ADULTI_DOMANDE
    except Exception:
        return _doc_html(_html_head("Melillo Adulti") + "<p>Domande non disponibili.</p>")
    b = [_html_head("Melillo Cognitive Style Assessment — Adulti",
                    "Cerchia A o B per ogni riga. Scegli in base alla tendenza naturale, non a quella appresa.")]
    for num, a, bb in MELILLO_ADULTI_DOMANDE:
        b.append(_radio_riga_html(num, a, bb))
    b.append('<p style="font-size:12px;margin-top:14px">Totale A: _____ &nbsp;&nbsp; Totale B: _____ '
             '&nbsp;&nbsp; Differenza: _____ &nbsp;&nbsp; Dominanza: ☐ Sinistra (A) ☐ Destra (B)</p>')
    return _doc_html("".join(b))


# ══════════════════════════════════════════════════════════════════
#  4. MELILLO BAMBINI (checklist D/S)
# ══════════════════════════════════════════════════════════════════
def _pdf_melillo_bambini():
    try:
        from modules.pnev.ui_questionari_pnev import MELILLO_BAMBINI_DESTRO, MELILLO_BAMBINI_SINISTRO
    except Exception:
        return _doc_html(_html_head("Melillo Bambini") + "<p>Domande non disponibili.</p>")
    b = [_html_head("Melillo — Checklist Squilibrio Cerebrale Bambini",
                    "Seleziona le caratteristiche che descrivono il bambino/a")]
    b.append("<h3>🔴 Ritardo Cerebrale Destro</h3>")
    for categoria, voci in MELILLO_BAMBINI_DESTRO.items():
        b.append(f"<p style='font-size:12.5px;margin:8px 0 2px 0'><b>{categoria}</b></p>")
        b.append(_checklist_html(voci, cols=2))
    b.append("<h3>🔵 Ritardo Cerebrale Sinistro</h3>")
    for categoria, voci in MELILLO_BAMBINI_SINISTRO.items():
        b.append(f"<p style='font-size:12.5px;margin:8px 0 2px 0'><b>{categoria}</b></p>")
        b.append(_checklist_html(voci, cols=2))
    return _doc_html("".join(b))


# ══════════════════════════════════════════════════════════════════
#  5. FISHER AUDITIVO BAMBINI
# ══════════════════════════════════════════════════════════════════
def _pdf_fisher():
    try:
        from modules.pnev.ui_questionari_pnev import FISHER_ITEMS
    except Exception:
        return _doc_html(_html_head("Fisher Auditivo") + "<p>Domande non disponibili.</p>")
    b = [_html_head("Elenco di Controllo dei Problemi Uditivi di Fisher — Bambini",
                    "Metti un segno di spunta prima di ogni elemento considerato un problema")]
    b.append('<p style="font-size:12px">Grado scolastico: ______________________</p>')
    b.append(_checklist_html([f"{n}. {label}" for n, label in FISHER_ITEMS]))
    return _doc_html("".join(b))


# ══════════════════════════════════════════════════════════════════
#  6. VISIONE BAMBINI
# ══════════════════════════════════════════════════════════════════
def _pdf_visione_bambini():
    try:
        from modules.pnev.ui_questionari_pnev import (
            VISIONE_BAMBINI_SINTOMI, VISIONE_BAMBINI_OSSERVATI, VISIONE_BAMBINI_SVILUPPO)
    except Exception:
        return _doc_html(_html_head("Visione Bambini") + "<p>Domande non disponibili.</p>")
    b = [_html_head("Questionario per la Visione del/la Bambino/a", "Fino a 11-12 anni")]
    b.append("<h3>Sintomi lamentati dal bambino</h3>")
    b.append(_checklist_html(VISIONE_BAMBINI_SINTOMI, cols=2))
    b.append("<h3>Problemi osservati dai genitori</h3>")
    b.append(_checklist_html(VISIONE_BAMBINI_OSSERVATI, cols=2))
    b.append("<h3>Ritardi di sviluppo</h3>")
    b.append(_checklist_html(VISIONE_BAMBINI_SVILUPPO, cols=2))
    return _doc_html("".join(b))


# ══════════════════════════════════════════════════════════════════
#  7. VISIONE ADULTI
# ══════════════════════════════════════════════════════════════════
def _pdf_visione_adulti():
    try:
        from modules.pnev.ui_questionari_pnev import VISIONE_ADULTI_SINTOMI, VISIONE_ADULTI_ANAMNESI
    except Exception:
        return _doc_html(_html_head("Visione Adulti") + "<p>Domande non disponibili.</p>")
    b = [_html_head("Questionario per la Visione dell'Adulto")]
    b.append("<h3>Sintomi visivi presenti</h3>")
    b.append(_checklist_html(VISIONE_ADULTI_SINTOMI, cols=2))
    b.append("<h3>Anamnesi patologie (paziente/familiari)</h3>")
    b.append(_checklist_html(VISIONE_ADULTI_ANAMNESI, cols=2))
    b.append('<p style="font-size:12px;margin-top:10px">Occupazione / lavoro prevalente: ______________________</p>')
    b.append('<p style="font-size:12px">Ore/giorno al videoterminale: _____</p>')
    b.append('<p style="font-size:12px">Note aggiuntive:</p>')
    b.append('<div style="border-bottom:1px solid #999;height:20px;margin-bottom:6px"></div>' * 2)
    return _doc_html("".join(b))


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
    """Pannello: scegli un questionario, scarica/stampa la versione cartacea
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
    html = fn()
    st.download_button(
        f"⬇️ Scarica {label} (HTML, da stampare)",
        data=html.encode("utf-8"),
        file_name=f"{q_code.lower()}_cartaceo.html",
        mime="text/html",
        key=f"qc_dl_{q_code}",
    )
    st.caption("Apri il file scaricato nel browser e stampalo (Ctrl/Cmd+P) — oppure guarda l'anteprima sotto.")
    with st.expander("👀 Anteprima", expanded=False):
        st.components.v1.html(html, height=600, scrolling=True)
