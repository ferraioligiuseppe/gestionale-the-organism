# -*- coding: utf-8 -*-
"""
modules/questionario_linguaggio.py

Checklist PNEV — Linguaggio 3–6 anni  (osservazione dei genitori)

PERCHÉ ESISTE
Oltre i 36 mesi non è disponibile, in italiano, uno strumento parent-report
validato e liberamente utilizzabile: il PVB si ferma a 36 mesi, QS4-G e ASQ-3
sono commerciali. Questa checklist è quindi uno strumento PNEV, costruito su
tappe di sviluppo documentate in letteratura (intelligibilità attesa per età,
età di acquisizione dei fonemi, comparsa delle subordinate, prerequisiti
metafonologici), NON un test normato.

DICHIARAZIONE ONESTA (da mantenere sempre visibile all'utente)
È uno strumento di orientamento: indica se vale la pena approfondire.
Non produce percentili, non fa diagnosi, non sostituisce la valutazione
logopedica. Quando serve un dato normativo si usano gli strumenti tarati.

LOGICA
Ogni item è un segnale: la risposta "sì" indica uno scostamento dall'atteso.
Gli item sono filtrati per età (alcune cose a 3 anni sono normali e a 5 no).
Il totale dei segnali si confronta con una soglia proporzionale al numero di
item mostrati; le aree vengono restituite separate, perché *dove* si
concentrano i segnali conta più di quanti sono.
"""

import datetime
import streamlit as st

# (chiave, testo, età minima in mesi a cui l'item diventa significativo, area)
ITEM = [
    # ── Intelligibilità e articolazione ──────────────────────────────
    ("int01", "Chi non lo conosce fa fatica a capire cosa dice", 36, "intelligibilita"),
    ("int02", "Anche in famiglia a volte non si capisce cosa dice", 36, "intelligibilita"),
    ("int03", "Semplifica le parole lunghe (dice «tefono» per telefono)", 48, "intelligibilita"),
    ("int04", "Non pronuncia ancora la R o i gruppi con L/R (bro, pla…)", 60, "intelligibilita"),
    ("int05", "Sostituisce suoni in modo costante (dice «tasa» per casa)", 48, "intelligibilita"),
    ("int06", "Si stanca o rinuncia a parlare perché non viene capito", 36, "intelligibilita"),

    # ── Frase e grammatica ───────────────────────────────────────────
    ("fra01", "Parla per parole singole o frasi di due parole", 36, "frase"),
    ("fra02", "Non usa ancora frasi con «perché», «quando», «che»", 54, "frase"),
    ("fra03", "Sbaglia spesso articoli, plurali o tempi dei verbi", 48, "frase"),
    ("fra04", "Mette le parole in ordine strano nella frase", 48, "frase"),
    ("fra05", "Fa fatica a raccontare un fatto in ordine (prima… poi…)", 54, "frase"),
    ("fra06", "Usa molte parole generiche («cosa», «quello») al posto dei nomi", 48, "frase"),

    # ── Comprensione ─────────────────────────────────────────────────
    ("com01", "Fa fatica a eseguire richieste con due passaggi", 36, "comprensione"),
    ("com02", "Non risponde bene alle domande «dove», «chi», «perché»", 42, "comprensione"),
    ("com03", "Sembra non ascoltare o chiede spesso «cosa?»", 36, "comprensione"),
    ("com04", "Capisce meglio se si aggiunge il gesto o si indica", 42, "comprensione"),
    ("com05", "In gruppo o con rumore di fondo capisce molto meno", 36, "comprensione"),

    # ── Basi uditive e attenzione al suono ───────────────────────────
    ("udi01", "Ha avuto otiti ripetute o catarro nell'orecchio", 36, "uditivo"),
    ("udi02", "Alza il volume della TV o si avvicina per sentire", 36, "uditivo"),
    ("udi03", "Si copre le orecchie o si spaventa per suoni comuni", 36, "uditivo"),
    ("udi04", "Non riconosce le rime («sole–mole») nei giochi di parole", 60, "uditivo"),
    ("udi05", "Non riesce a dividere una parola in sillabe battendo le mani", 60, "uditivo"),
    ("udi06", "Non riconosce con che suono inizia una parola", 66, "uditivo"),

    # ── Bocca, respiro, alimentazione ────────────────────────────────
    ("oro01", "Sta spesso con la bocca aperta, anche da svegli", 36, "oromotorio"),
    ("oro02", "Russa, respira dalla bocca o dorme in modo agitato", 36, "oromotorio"),
    ("oro03", "Perde saliva o ha ancora la bava", 36, "oromotorio"),
    ("oro04", "Mangia solo cibi morbidi, evita di masticare", 36, "oromotorio"),
    ("oro05", "Usa ancora ciuccio o biberon, o si succhia il dito", 42, "oromotorio"),
    ("oro06", "Lingua che spinge sui denti o denti che non combaciano", 48, "oromotorio"),

    # ── Fluenza ──────────────────────────────────────────────────────
    ("flu01", "Ripete sillabe o suoni all'inizio delle parole", 36, "fluenza"),
    ("flu02", "Si blocca, resta in tensione prima di riuscire a parlare", 36, "fluenza"),
    ("flu03", "Evita di parlare o cambia parola per non incespicare", 42, "fluenza"),

    # ── Uso sociale del linguaggio ───────────────────────────────────
    ("soc01", "Parla poco con gli estranei o fuori casa", 36, "sociale"),
    ("soc02", "Fa fatica ad aspettare il turno nella conversazione", 42, "sociale"),
    ("soc03", "Racconta in modo che l'altro non riesce a seguirlo", 54, "sociale"),
    ("soc04", "Gli altri bambini fanno fatica a giocare con lui parlando", 42, "sociale"),
]

AREE = {
    "intelligibilita": "Intelligibilità e articolazione",
    "frase":           "Frase e grammatica",
    "comprensione":    "Comprensione",
    "uditivo":         "Basi uditive e consapevolezza dei suoni",
    "oromotorio":      "Bocca, respiro e alimentazione",
    "fluenza":         "Fluenza",
    "sociale":         "Uso del linguaggio con gli altri",
}

# Lettura clinica per area: cosa suggerisce una concentrazione di segnali
NOTA_AREA = {
    "intelligibilita": "Quadro fonetico-fonologico da valutare: intelligibilità ridotta "
                       "oltre i 4 anni non è più un ritardo che «si sistema da solo».",
    "frase":           "Versante morfosintattico: da distinguere fra ritardo espressivo "
                       "e disturbo primario del linguaggio.",
    "comprensione":    "Comprensione coinvolta: quadro più impegnativo del ritardo "
                       "espressivo puro, va approfondito prima.",
    "uditivo":         "Basi uditive da verificare: audiometria, timpanometria ed "
                       "elaborazione uditiva centrale prima del lavoro sul linguaggio.",
    "oromotorio":      "Squilibrio oro-mio-funzionale: respirazione orale e postura "
                       "linguale condizionano articolazione e crescita cranio-facciale. "
                       "Valutare anche con odontoiatra/ORL.",
    "fluenza":         "Segnali di disfluenza: distinguere le disfluenze fisiologiche "
                       "dalla balbuzie che si struttura. La tensione e l'evitamento "
                       "sono i segnali che pesano.",
    "sociale":         "Versante pragmatico: da leggere insieme al profilo comunicativo "
                       "generale.",
}


def _items_per_eta(eta_mesi):
    return [i for i in ITEM if eta_mesi >= i[2]]


def linguaggio_pnev_ui(prefix, existing=None, eta_mesi=None, compatta=False):
    """Rende la checklist. Ritorna (dati, sintesi, n_positivi)."""
    existing = existing or {}
    risposte = dict(existing.get("risposte", {}))

    if eta_mesi is None:
        eta_mesi = int(existing.get("eta_mesi") or 48)
        eta_mesi = st.number_input(
            "Età del bambino (mesi)", 36, 84, eta_mesi, 1, key=f"{prefix}_eta",
            help="Le domande cambiano con l'età: alcune cose a 3 anni sono attese "
                 "e a 5 no.")

    items = _items_per_eta(eta_mesi)
    st.caption(f"{len(items)} domande, adattate a {eta_mesi} mesi "
              f"({eta_mesi // 12} anni e {eta_mesi % 12} mesi). "
              "Rispondi «sì» solo se è qualcosa che noti spesso, non una volta.")

    per_area = {}
    for chiave, testo, _eta, area in items:
        per_area.setdefault(area, []).append((chiave, testo))

    for area, elenco in per_area.items():
        if compatta:
            st.markdown(f"**{AREE[area]}**")
        else:
            st.markdown(f"##### {AREE[area]}")
        for chiave, testo in elenco:
            risposte[chiave] = st.checkbox(
                testo, value=bool(risposte.get(chiave)), key=f"{prefix}_{chiave}")

    # ── Conteggio ─────────────────────────────────────────────────────
    positivi_area, totale = {}, 0
    for chiave, testo, _e, area in items:
        if risposte.get(chiave):
            positivi_area[area] = positivi_area.get(area, 0) + 1
            totale += 1

    # Soglia proporzionale: ~25% degli item mostrati, minimo 5
    soglia = max(5, round(len(items) * 0.25))
    oltre = totale >= soglia
    # Un'area con 3+ segnali è significativa anche se il totale è basso
    aree_calde = [a for a, n in positivi_area.items() if n >= 3]

    dati = {
        "strumento": "checklist_linguaggio_pnev",
        "versione": "1.0",
        "data": datetime.date.today().isoformat(),
        "eta_mesi": int(eta_mesi),
        "risposte": risposte,
        "n_item": len(items),
        "positivi": totale,
        "positivi_per_area": positivi_area,
        "soglia": soglia,
        "oltre_soglia": bool(oltre),
        "aree_calde": aree_calde,
    }

    righe = [f"Checklist linguaggio PNEV ({eta_mesi} mesi): {totale}/{len(items)} "
             f"segnali (soglia {soglia})."]
    for a, n in sorted(positivi_area.items(), key=lambda x: -x[1]):
        righe.append(f"- {AREE[a]}: {n}")
    sintesi = "\n".join(righe)

    return dati, sintesi, totale


def mostra_esito(dati, pubblico=False):
    """Riquadro di lettura. pubblico=True → linguaggio per il genitore."""
    tot = dati.get("positivi", 0)
    soglia = dati.get("soglia", 5)
    calde = dati.get("aree_calde", [])
    per_area = dati.get("positivi_per_area", {})

    if tot == 0:
        st.success("Nessun segnale rilevato in questa checklist.")
        return
    if dati.get("oltre_soglia") or calde:
        if pubblico:
            st.warning(
                f"Sono emersi **{tot} segnali** su {dati.get('n_item')} domande. "
                "Non è una diagnosi — è il tipo di quadro per cui vale la pena "
                "una valutazione, che spesso serve anche solo a escludere."
            )
        else:
            st.warning(f"⚠️ {tot}/{dati.get('n_item')} segnali (soglia ≥ {soglia}). "
                      "Profilo da approfondire.")
    else:
        st.info(f"{tot} segnali su {dati.get('n_item')}: sotto la soglia di "
               f"attenzione ({soglia}). Utile una rivalutazione a distanza.")

    if not pubblico:
        for a, n in sorted(per_area.items(), key=lambda x: -x[1]):
            if n >= 2:
                st.markdown(f"**{AREE.get(a, a)}** — {n} segnali")
                st.caption(NOTA_AREA.get(a, ""))

    st.caption("Strumento di orientamento PNEV costruito su tappe di sviluppo "
              "documentate. Non è un test normato: non produce percentili e non "
              "sostituisce la valutazione logopedica.")


# ══════════════════════════════════════════════════════════════════════
#  VERSIONE BREVE (per il sito) — risposte graduate 0/1/2 e fasce
#  Struttura ispirata ai questionari divulgativi a punteggio, contenuto
#  PNEV: alle tre aree classiche (comprensione, produzione, intelligibilità)
#  si aggiungono uditivo, oro-motorio e fluenza, che sono le basi su cui
#  il metodo legge il linguaggio.
# ══════════════════════════════════════════════════════════════════════

BREVE = [
    ("b1", "comprensione",
     "Se gli dai due indicazioni di seguito senza indicare con il dito "
     "(«prendi le scarpe e mettile vicino alla porta»), cosa fa?",
     ["Le esegue tutte e due senza esitare",
      "Ne fa una sola, o ha bisogno che io indichi",
      "Non esegue, o fa una cosa diversa"]),

    ("b2", "comprensione",
     "Quando leggete una storia illustrata adatta alla sua età, mostra di aver capito?",
     ["Sì, risponde a domande semplici sulla storia",
      "Guarda le figure ma perde il filo del racconto",
      "Perde subito l'attenzione e non risponde"]),

    ("b3", "produzione",
     "Come sono le frasi che dice spontaneamente in casa?",
     ["Frasi complete di 3–4 parole o più",
      "Frasi corte o spezzettate («papà macchina»)",
      "Soprattutto gesti o parole isolate"]),

    ("b4", "produzione",
     "Riesce a raccontarti una cosa che ha fatto (all'asilo, dai nonni)?",
     ["Sì, si capisce e sta in ordine",
      "Dice parole sparse: devo fare molte domande",
      "No, non racconta quello che ha fatto"]),

    ("b5", "intelligibilita",
     "Chi non vive in casa (maestre, parenti, altri bambini) lo capisce quando parla?",
     ["Sì, capiscono quasi tutto",
      "Lo capiscono solo se ci sono io a «tradurre»",
      "Quasi nessuno lo capisce, tranne noi genitori"]),

    ("b6", "intelligibilita",
     "Come pronuncia i suoni dentro le parole?",
     ["Bene, con qualche incertezza solo su R, S, Z",
      "Storpia molte parole o cambia le lettere («tola» per scuola)",
      "Salta molte consonanti: le parole non si riconoscono"]),

    ("b7", "uditivo",
     "Come sta con l'ascolto e con i suoni?",
     ["Sente bene, gioca volentieri con rime e filastrocche",
      "Ha avuto otiti ripetute, oppure chiede spesso «cosa?», "
      "o in mezzo al rumore capisce molto meno",
      "Sembra spesso non sentire, o si copre le orecchie per suoni comuni"]),

    ("b8", "oromotorio",
     "Come sta con bocca, respiro e masticazione?",
     ["Respira dal naso, mangia di tutto, bocca chiusa a riposo",
      "Sta spesso con la bocca aperta, russa, o evita i cibi da masticare",
      "Bocca sempre aperta, perde saliva, mangia solo cibi morbidi"]),

    ("b9", "fluenza",
     "Quando parla, gli capita di incespicare?",
     ["No, parla scorrevole",
      "A volte ripete sillabe o suoni all'inizio delle parole",
      "Si blocca in tensione, oppure evita di parlare per non incespicare"]),
]

# Item su cui una risposta al livello peggiore pesa da sola
CRITICI = {"b5", "b6", "b7"}


def linguaggio_breve_ui(prefix, eta_mesi=None, pubblico=True):
    """Versione breve a punteggio (0/1/2). Ritorna (dati, sintesi, punteggio)."""
    if eta_mesi is None:
        eta_mesi = st.number_input("Età del bambino (mesi)", 36, 84, 48, 1,
                                   key=f"{prefix}_eta_b")

    st.caption("Nove domande, due minuti. Scegli la risposta che descrive meglio "
              "come è **adesso**, non come è stato o come sarà.")

    risposte, punteggio, gravi = {}, 0, []
    for chiave, area, domanda, opzioni in BREVE:
        scelta = st.radio(domanda, opzioni, index=0, key=f"{prefix}_{chiave}")
        livello = opzioni.index(scelta)          # 0 = meglio, 2 = peggio
        punti = 2 - livello
        risposte[chiave] = {"area": area, "livello": livello, "punti": punti}
        punteggio += punti
        if livello == 2 and chiave in CRITICI:
            gravi.append(area)
        st.markdown("")

    massimo = len(BREVE) * 2
    quota = punteggio / massimo if massimo else 1

    if gravi:
        fascia = "approfondire"
    elif quota >= 0.81:
        fascia = "linea"
    elif quota >= 0.50:
        fascia = "monitorare"
    else:
        fascia = "approfondire"

    per_area = {}
    for chiave, r in risposte.items():
        if r["livello"] > 0:
            per_area[r["area"]] = per_area.get(r["area"], 0) + r["livello"]

    dati = {
        "strumento": "screening_linguaggio_pnev_breve",
        "versione": "1.0",
        "data": datetime.date.today().isoformat(),
        "eta_mesi": int(eta_mesi),
        "risposte": risposte,
        "punteggio": punteggio,
        "massimo": massimo,
        "fascia": fascia,
        "segnali_per_area": per_area,
        "aree_critiche": sorted(set(gravi)),
    }

    righe = [f"Screening linguaggio PNEV breve ({eta_mesi} mesi): "
             f"{punteggio}/{massimo} punti — fascia «{fascia}»."]
    for a, n in sorted(per_area.items(), key=lambda x: -x[1]):
        righe.append(f"- {AREE.get(a, a)}: {n}")
    sintesi = "\n".join(righe)

    return dati, sintesi, punteggio


FASCE_TESTO = {
    "linea": (
        "Sviluppo in linea",
        "Il linguaggio appare in linea con quanto atteso a questa età. "
        "Continua a leggere insieme a lui e a parlargli durante le attività "
        "di ogni giorno: è la cosa che funziona di più."),
    "monitorare": (
        "Qualche fragilità da tenere d'occhio",
        "Emergono alcune fragilità. Spesso sono variazioni individuali dello "
        "sviluppo, ma a questa età non conviene attendere passivamente: "
        "meglio riguardarlo fra tre mesi con un occhio informato, o togliersi "
        "il dubbio con una valutazione."),
    "approfondire": (
        "Meglio approfondire",
        "Sono presenti diversi segnali di quelli che, dopo i 3 anni, tendono a "
        "non risolversi da soli. Intervenire prima della scuola primaria cambia "
        "molto il percorso — e in buona parte dei casi la valutazione serve "
        "proprio a escludere un problema."),
}


def mostra_esito_breve(dati, pubblico=True):
    fascia = dati.get("fascia", "monitorare")
    titolo, testo = FASCE_TESTO.get(fascia, FASCE_TESTO["monitorare"])
    p, m = dati.get("punteggio", 0), dati.get("massimo", 18)

    if fascia == "linea":
        st.success(f"**{titolo}** — {p}/{m} punti\n\n{testo}")
    elif fascia == "monitorare":
        st.warning(f"**{titolo}** — {p}/{m} punti\n\n{testo}")
    else:
        st.error(f"**{titolo}** — {p}/{m} punti\n\n{testo}")

    crit = dati.get("aree_critiche") or []
    if crit:
        nomi = ", ".join(AREE.get(a, a).lower() for a in crit)
        st.info(f"In particolare andrebbe guardata l'area: **{nomi}**.")

    if not pubblico:
        for a, n in sorted((dati.get("segnali_per_area") or {}).items(),
                           key=lambda x: -x[1]):
            st.markdown(f"**{AREE.get(a, a)}** — peso {n}")
            st.caption(NOTA_AREA.get(a, ""))

    st.caption(
        "**Avviso** — Questo questionario ha scopo informativo e di orientamento. "
        "Non sostituisce una diagnosi clinica, un parere medico o una valutazione "
        "logopedica formale. In caso di dubbi sullo sviluppo del bambino, "
        "consulta sempre il pediatra."
    )
