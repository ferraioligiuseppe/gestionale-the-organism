# -*- coding: utf-8 -*-
"""
🔎 Cerca nel gestionale — casella di ricerca in cima al menu laterale.

Scrivi una parola («alimentazione», «dieta», «fattura», «riflessi»…) e
compaiono le sezioni che c'entrano, con scritto DOVE stanno
(Area › Ramo). Un clic e il menu si apre lì.

Come funziona
- L'elenco delle sezioni NON è scritto qui: viene letto da app_menu
  (AREE_ORDINE, SOTTOSEZIONI, RAMI_PER_AREA). Una voce nuova nel menu è
  quindi cercabile da subito, senza toccare questo file.
- PAROLE_CHIAVE aggiunge i sinonimi: le parole con cui una sezione viene
  cercata ma che non compaiono nel suo nome (es. «dieta» → Alimentazione).
  Per farne trovare una in più basta aggiungere una parola lì.
- La ricerca ignora maiuscole, accenti ed emoji e tollera gli errori di
  battitura («alimentazoine» trova lo stesso Alimentazione).
- Il salto usa lo stesso meccanismo del resto del gestionale
  (goto_area / goto_sotto in sessione, letto da build_smart_menu).
"""
from __future__ import annotations

import difflib
import re
import unicodedata
from typing import Callable, Iterable

# ── Sinonimi: voce del menu → parole con cui la si cerca ──────────────
# Le chiavi devono essere IDENTICHE alle etichette di app_menu.py.
# Una chiave che non esiste più nel menu viene semplicemente ignorata.
PAROLE_CHIAVE: dict[str, str] = {
    # Agenda
    "📒 Oggi in studio": "brogliaccio telefonate cose da fare chi ha fatto cosa promemoria novita incassi quote",
    "📅 Agenda appuntamenti": "calendario appuntamento prenotazione google calendar orari visite",
    # Pazienti
    "🏠 Dashboard": "home bacheca inizio riepilogo percorso prossimo passo",
    "👤 Anagrafica pazienti": "nuovo paziente scheda dati indirizzo telefono codice fiscale genitori famiglia doppioni",
    "🧩 Quadro storico": "storia riassunto cronistoria paziente",
    "🕒 Cronologia": "registro attivita storico chi ha fatto log",
    "🧭 Bussola degli esiti": "statistiche efficacia risultati trattamenti",
    "📊 Aderenza dello studio": "aderenza compliance esercizi casa statistiche",
    "📎 Documenti clinici": "allegati referti file caricare upload pdf esami",
    "🧩 Rilievi PNEV": "sette livelli profilo osservazioni modello pnev",
    "🎙️ Colloqui clinici": "registrazione audio colloquio trascrizione mamma genitori intervista",
    "🌳 Genosociogramma": "albero genealogico famiglia costellazioni narrazione familiare schutzenberger antenati",
    "🥗 Alimentazione": "dieta nutrizione cibo kousmine alimentare mangiare pasti intolleranze microbiota intestino piano alimentare diario alimentare nutrizionale",
    "🧬 Genetica PNEV": "sindromi genetiche rare hpo volto foto genetista atlante profilo di funzionamento",
    "🗓️ Diario clinico": "note sedute appunti anamnesi voci narrativa",
    "📝 Diagnosi assistita": "diagnosi ai intelligenza artificiale ipotesi sintesi",
    "📚 Archivio relazioni": "relazioni salvate vecchie relazioni storico pdf",
    "📅 Sedute / Terapie": "seduta terapia presenze trattamenti incontri",
    "📈 Esiti / Follow-up": "controllo follow up risultati rivalutazione settimane",
    "🔒 Privacy & Consensi": "consenso informato gdpr privacy firma modulo trattamento dati",
    "✍️ Firme privacy in attesa": "firma consenso da firmare sospeso",
    "💡 Assistente PNEV": "aiuto ai assistente domande suggerimenti",
    "📄 Modulistica / Schede da stampare": "moduli stampa schede carta cartaceo pdf",
    "🎟️ Coupon OF / SDS": "coupon buono sconto",
    "📨 Contatti dal sito": "richieste informazioni messaggi sito pnev lead",
    "📋 Questionari dal sito": "questionari arrivati sito pnev compilati",
    "🎧 Aderenza ascolti MAPS": "ascolti maps casa aderenza",
    "📝 Consensi ascolti MAPS": "consenso maps ascolti",
    "🔗 Sincronizza pnev.it": "sync sincronizzazione sito",
    "🚀 Trasferisci a pnev.it": "trasferimento paziente sito invio",
    "🩺 Stato del sito pnev.it": "sito funziona controllo stato",
    "📥 Import pazienti": "importa excel csv caricare elenco pazienti",
    # Questionari
    "📋 Questionari remoti": "inviare questionario link email whatsapp genitori casa",
    "🔗 Link aperti e arrivi": "link aperto qr code questionario pubblico arrivi",
    "🖨️ Questionari cartacei": "questionario carta stampa inserire a mano",
    "📋 Consenso screening scolastico": "scuola consenso screening genitori",
    # Valutazione PNEV
    "📋 Anamnesi PNEV": "anamnesi prima visita storia gravidanza parto sviluppo",
    "🧬 Profilo Neuro-Evolutivo": "inpp riflessi primitivi neuromotorio moro atnr stnr tlr maturita neuro-psico-motoria",
    "👁️ Anamnesi visiva": "anamnesi occhi vista optometria",
    "👁️ Valutazione visuo-percettiva": "pvpmf optometria comportamentale percezione visiva vmi tvps",
    "🔢 DEM interattivo": "dem movimenti oculari saccadi lettura numeri",
    "👁️ Getman (manipolazione visiva)": "getman visualizzazione",
    "👁️ Groffman (visual tracing)": "groffman tracing inseguimento",
    "👁️ Eye tracking": "eyetracking tobii sguardo movimenti oculari webcam gaze",
    "🩶 Postura (Wii Balance Board)": "stabilometria pedana equilibrio wii postura baricentro",
    "⚡ Protocollo Epilessia": "epilessia mozart crisi",
    "🔉 Diagnostica uditiva completa": "udito audiometria calibrazione cuffie esame uditivo orecchio",
    "📊 Audiometria funzionale": "audiogramma udito curva tomatis",
    "🎧 Bilancio uditivo": "udito ascolto lateralita test di ascolto",
    "🎧 Audiometria tonale calibrata": "audiometria tonale soglia udito db",
    "🌐 Curve cuffie condivise (pnev.it)": "cuffie calibrazione curve",
    "📚 Strumenti open": "apprendimento test gratuiti lettura scrittura calcolo",
    "📚 DSA — Apprendimento": "dislessia disgrafia discalculia disortografia dsa lettura scrittura calcolo",
    "📖 Lettura avanzata": "lettura velocita testo leggio",
    "🧠 NPS — Neuropsicologica": "neuropsicologia test cognitivi memoria attenzione funzioni esecutive qi",
    "🌐 WHODAS 2.0": "whodas disabilita oms funzionamento",
    "🧩 Matrici di Raven (CPM · SPM)": "raven matrici progressive cpm spm colorate intelligenza ragionamento non verbale qi",
    "🎯 ADHD — Valutazione": "adhd attenzione iperattivita conners scale genitori insegnanti",
    "🧪 Laboratorio PNEV": "laboratorio sperimentale prove",
    # Terapia
    "🎯 Piano di trattamento": "piano terapia obiettivi programma settimana",
    "🏠 Programma PNEV a casa": "esercizi casa compiti programma domiciliare",
    "🧘 Percorsi terapeutici": "percorso terapia disciplina protocollo",
    "🧩 Programma PNEV": "programma esercizi riflessi integrazione",
    "🎵 TMR — Movimenti ritmici": "rmt blomberg movimenti ritmici riflessi",
    "✍️ Giochiamo imparando (prove touch)": "pregrafismo corsivo scrittura disprassia touch tablet bambini",
    "🎧 MAPS-CLEAR Lab": "balbuzie maps clear fluenza interaurale",
    "🎯 Piano Vision Therapy": "vision therapy training visivo esercizi occhi",
    "👁️ Stimolazione visiva a casa": "frattale stimolazione visiva esercizi occhi casa",
    "🎧 MAPS": "stimolazione uditiva ascolto musica filtrata tomatis",
    "🗂 Programmi MAPS": "programmi ascolto musica brani",
    "🧭 Percorsi MAPS": "percorsi ascolto",
    "🎧 MAPS-CLEAR in studio": "balbuzie maps clear studio",
    "🎧 MAPS-CLEAR pubblico": "balbuzie maps clear pubblico area personale",
    "🔤 MAPS-Read": "lettura maps read",
    # Respirazione
    "🫁 Valutazione e programma Buteyko": "buteyko respiro respirazione naso bocca apnea",
    "📈 Diario Pausa Controllo": "pausa controllo buteyko diario respiro",
    # Oculistica
    "👁️ Visita oculistica / optometrica": "visita occhi oculista optometrista refrazione occhiali prescrizione oct tono fondo vergenze",
    "👁️ Contattologia": "lenti a contatto lac rgp sclerali ortocheratologia multicurva",
    # Logopedia / TNPEE
    "🗣️ Logopedia / SMOF": "logopedia miofunzionale deglutizione lingua linguaggio cartella logopedica squilibrio muscolare",
    "🔤 Impostazione fonemi": "fonemi suoni pronuncia articolazione prompt",
    "🤸 Psicomotricità funzionale": "psicomotricita tnpee motorio",
    "🖼️ PECS — CAA": "pecs comunicazione aumentativa immagini autismo",
    # Osteopatia
    "🦴 Osteopatia": "osteopata valutazione osteopatica manuale",
    # Screening
    "🩺 Screening rapido": "screening veloce primo controllo",
    "🩺 Screening breve (20 min)": "screening 20 minuti",
    "🧑 Screening adulti — funzionale": "adulti screening",
    "🧠 Screening adulti — neurologico": "adulti neurologico screening",
    "🧑 Valutazione adulti — funzionale completa": "adulti valutazione completa",
    "🧠 Valutazione adulti — neurologica completa": "adulti neurologica completa",
    "🔺 Prismi posturali": "prismi postura lenti prismatiche",
    "👅 Valutazione del frenulo": "frenulo linguale lingua anchiloglossia",
    "🧸 Screening 0-4 anni": "prima infanzia neonati piccoli bambini 0 4",
    "🎧 Screening uditivo": "udito screening orecchio",
    "🩺 Screening completo": "protocollo valutazione funzionale completo scheda",
    # Materiali
    "📐 PNEV-Chart (schede stampabili)": "tabelle chart ottotipo schede stampa hart",
    "🥁 PNEV Metronomo": "metronomo ritmo battiti tempo",
    "🎯 Segui la pallina": "inseguimento pallina occhi pursuit",
    "🎬 Animazioni dei riflessi": "video animazioni riflessi primitivi spiegare genitori",
    "🕹️ PNEV Game Center": "giochi game esercizi gioco",
    "🎮 Esercizi Wordwall": "wordwall giochi esercizi interattivi",
    "🏃 PNEV Sport Vision": "sport vision atleti visione sportiva",
    # Test live
    "🖥️ Somministrazione test": "test a schermo somministrare prova live",
    "📸 Photoref AI": "foto photoref fotorefrazione immagine volto occhi",
    # Relazioni & studio clinico
    "📝 Relazione clinica": "relazione referto scrivere relazione carta intestata diagnosi pdf",
    "🏫 PEI e PDF (scuola)": "pei scuola profilo dinamico funzionale glo sostegno insegnanti",
    "📄 Report PDF con grafici": "report pdf grafici stampa",
    "📊 Export statistici": "esporta excel csv dati statistiche",
    "🧪 Caso demo": "demo esempio prova paziente finto",
    "🔬 Studi e ricerca": "ricerca studio partecipanti pseudonimi sperimentazione",
    # Academy
    "📅 Eventi e iscrizioni": "corsi eventi iscrizioni serate costellazioni formazione open day",
    "🔬 Ricerca · Frenulo come perturbazione": "frenulo ricerca articolo",
    # Aerosal
    "🌬️ Aerosal · Haloterapia": "stanza del sale haloterapia sale aerosal sedute",
    "💳 Crediti e convenzioni": "crediti pacchetti convenzioni abbonamento aerosal",
    # Studio
    "📊 Dashboard incassi": "incassi soldi pagamenti entrate guadagni contanti pos",
    "🧾 Fatture in Cloud": "fattura fatturazione fatture ricevuta sistema ts",
    "🧾 Recupero fatture SumUp": "sumup pos pagamento carta fatture",
    "🏥 Il mio studio": "studio sedi carta intestata logo impostazioni listino prezzi",
    "👤 Il mio profilo": "profilo password timbro firma professionista",
    "👥 Utenti / Ruoli": "utenti account permessi collaboratori segretaria accessi",
    "⚙️ Platform Admin": "amministrazione saas studi abbonamenti",
    "🐛 Debug DB": "database errori tecnico",
    "🩺 Diagnostica moduli": "moduli errori controllo tecnico",
}


# ── Normalizzazione ───────────────────────────────────────────────────
def _norm(testo: str) -> str:
    """minuscole, senza accenti, senza emoji/punteggiatura, spazi singoli."""
    t = unicodedata.normalize("NFKD", str(testo or ""))
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"[^a-z0-9]+", " ", t.lower())
    return t.strip()


# ── Indice delle voci ─────────────────────────────────────────────────
def costruisci_indice(aree: Iterable[str], sottosezioni: dict, rami_per_area: dict) -> list[dict]:
    """Una riga per ogni voce del menu: dove sta e con che parole si trova."""
    indice: list[dict] = []
    for area in aree:
        if area in rami_per_area:
            gruppi = [(ramo, voci) for ramo, voci in rami_per_area[area].items()]
        else:
            gruppi = [(None, sottosezioni.get(area, []))]
        for ramo, voci in gruppi:
            for voce in voci:
                nome = _norm(voce)
                dove = _norm(area) + " " + _norm(ramo or "")
                chiavi = _norm(PAROLE_CHIAVE.get(voce, ""))
                indice.append({
                    "area": area, "ramo": ramo, "voce": voce,
                    "nome": nome, "dove": dove, "chiavi": chiavi,
                    "parole_nome": nome.split(),
                    "parole_altre": (dove + " " + chiavi).split(),
                })
    return indice


def _punti_parola(q: str, riga: dict) -> int:
    """Quanto una singola parola cercata c'entra con una voce (0 = niente)."""
    if q in riga["parole_nome"]:
        return 100
    if any(p.startswith(q) for p in riga["parole_nome"]):
        return 85
    if q in riga["nome"]:
        return 70
    if q in riga["parole_altre"]:
        return 60
    if any(p.startswith(q) for p in riga["parole_altre"]):
        return 50
    if len(q) >= 4 and (q in riga["chiavi"] or q in riga["dove"]):
        return 40
    # Errori di battitura: solo da 4 lettere in su, altrimenti trova di tutto.
    if len(q) >= 4:
        if difflib.get_close_matches(q, riga["parole_nome"], n=1, cutoff=0.78):
            return 35
        if difflib.get_close_matches(q, riga["parole_altre"], n=1, cutoff=0.82):
            return 25
    return 0


def cerca(testo: str, indice: list[dict], massimo: int = 8) -> list[dict]:
    """Le voci che c'entrano con `testo`, dalla più pertinente."""
    parole = [p for p in _norm(testo).split() if len(p) >= 2]
    if not parole:
        return []
    tutte, alcune = [], []
    for riga in indice:
        punti = [_punti_parola(q, riga) for q in parole]
        if max(punti) == 0:
            continue
        media = sum(punti) / len(punti)
        (tutte if min(punti) > 0 else alcune).append((media, riga))
    # Prima le voci che c'entrano con TUTTE le parole («piano alimentare»);
    # se non ce ne sono, quelle che c'entrano almeno con una
    # («tipo alimentazione» trova comunque Alimentazione).
    trovate = tutte or alcune
    trovate.sort(key=lambda x: -x[0])
    return [r for _, r in trovate[:massimo]]


# ── Interfaccia nella barra laterale ──────────────────────────────────
_CHIAVE_TESTO = "cerca_menu_testo"


def _vai(area: str, voce: str) -> None:
    """Callback del clic su un risultato: prenota il salto e svuota la casella."""
    import streamlit as st
    st.session_state["goto_area"] = area
    st.session_state["goto_sotto"] = voce
    st.session_state[_CHIAVE_TESTO] = ""


def casella_ricerca(aree, sottosezioni, rami_per_area,
                    filtra: Callable[[list], list] | None = None) -> None:
    """Disegna «🔎 Cerca nel gestionale» in cima al menu laterale.

    `filtra` è lo stesso filtro che il menu applica alle voci (admin, età
    del paziente): così la ricerca non propone sezioni che poi il menu
    non mostrerebbe.
    """
    import streamlit as st

    testo = st.sidebar.text_input(
        "🔎 Cerca nel gestionale",
        key=_CHIAVE_TESTO,
        placeholder="es. alimentazione, fattura, riflessi…",
        help="Scrivi una parola e premi Invio: ti dico dove si trova e ti ci porto.",
    )
    if not (testo or "").strip():
        return

    indice = costruisci_indice(aree, sottosezioni, rami_per_area)
    if filtra is not None:
        visibili = set(filtra([r["voce"] for r in indice]))
        indice = [r for r in indice if r["voce"] in visibili]

    risultati = cerca(testo, indice)
    if not risultati:
        st.sidebar.caption(
            f"Nessuna sezione trovata per «{testo.strip()}». "
            "Prova con un'altra parola.")
        st.sidebar.markdown("---")
        return

    for i, r in enumerate(risultati):
        dove = r["area"] + (f" › {r['ramo']}" if r["ramo"] else "")
        st.sidebar.button(
            r["voce"], key=f"cerca_menu_ris_{i}", use_container_width=True,
            on_click=_vai, args=(r["area"], r["voce"]), help=f"Si trova in: {dove}")
        st.sidebar.caption(f"↳ {dove}")
    st.sidebar.markdown("---")
