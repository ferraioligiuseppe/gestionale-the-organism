# -*- coding: utf-8 -*-
"""Anamnesi dello sviluppo dopo il primo anno — blocco condiviso.

Le due anamnesi del gestionale si fermavano presto: il Protocollo di
valutazione al periodo neonatale (poi due righe libere per tappe motorie e
prime parole), la Castagnini a 24 mesi. Dai 2 anni in poi — linguaggio,
autonomie, scuola dell'infanzia, apprendimenti, salute, abitudini — non
c'era un posto dove scriverlo.

Questo blocco si compila UNA volta per paziente e compare uguale ovunque:
  - Protocollo di valutazione (scheda)
  - Anamnesi PNEV — Castagnini
  - Diagnosi assistita, dentro lo storico che legge l'AI

I dati stanno in una tabella propria, `anamnesi_sviluppo`, una riga per
paziente: chi apre il blocco da un modulo vede quello che e' stato scritto
dall'altro.

Esposto:
  render_anamnesi_sviluppo(conn, paz_id, px) -> dict
  carica_anamnesi_sviluppo(conn, paz_id)    -> dict
  sintesi_anamnesi_sviluppo(dati)           -> list[str]   (solo campi compilati)
"""
from __future__ import annotations

import json
import streamlit as st

_NO = ""

SEZIONI = [
    ("🧒 Dai 2 ai 6 anni", [
        ("frasi_mesi", "Prime frasi di 2-3 parole (mesi)", "mesi", None),
        ("comprensibilita", "A 3-4 anni parlava in modo", "sel",
         [_NO, "comprensibile a tutti", "comprensibile solo ai familiari", "poco comprensibile"]),
        ("balbuzie", "Balbuzie", "sel", [_NO, "no", "sì, passata", "sì, attuale"]),
        ("ling_note", "Linguaggio — note (logopedia, suoni difficili)", "txt", None),
        ("motricita_globale", "Corsa, salto, equilibrio", "sel",
         [_NO, "nei tempi", "impacciato, cadeva spesso", "in ritardo"]),
        ("bici", "Triciclo / bicicletta senza rotelle (età)", "txt", None),
        ("motricita_fine", "Disegno, forbici, bottoni", "sel",
         [_NO, "nei tempi", "fatica", "evita queste attività"]),
        ("sfint_giorno_mesi", "Controllo sfinterico di giorno (mesi)", "mesi", None),
        ("sfint_notte_mesi", "Controllo sfinterico di notte (mesi)", "mesi", None),
        ("enuresi", "Enuresi", "sel", [_NO, "no", "sì, occasionale", "sì, frequente"]),
        ("autonomie", "Autonomie (vestirsi, mangiare da solo)", "sel",
         [_NO, "adeguate all'età", "parziali", "dipende dall'adulto"]),
        ("gioco", "Gioco", "multi",
         ["gioca volentieri con altri", "preferisce giocare da solo", "gioco di finzione",
          "gioco ripetitivo", "difficoltà con i coetanei"]),
        ("lateralita", "Mano preferita", "sel", [_NO, "destra", "sinistra", "incerta / alterna"]),
        ("infanzia", "Scuola dell'infanzia — età di ingresso e adattamento", "txt", None),
        ("infanzia_segn", "Segnalazioni delle maestre", "area", None),
    ]),
    ("🎒 Età scolare (dai 6 anni)", [
        ("ingresso_primaria", "Ingresso alla primaria", "sel",
         [_NO, "regolare", "in anticipo", "posticipato", "con una ripetenza"]),
        ("lettura", "Imparare a leggere", "sel",
         [_NO, "senza difficoltà", "lento ma corretto", "con errori", "molto faticoso"]),
        ("scrittura", "Imparare a scrivere", "sel",
         [_NO, "senza difficoltà", "lento ma corretto", "con errori", "molto faticoso"]),
        ("calcolo", "Imparare a contare e calcolare", "sel",
         [_NO, "senza difficoltà", "lento ma corretto", "con errori", "molto faticoso"]),
        ("segn_insegnanti", "Segnalazioni degli insegnanti", "area", None),
        ("certificazioni", "Certificazioni", "multi", ["DSA", "ADHD", "L.104", "BES / PDP", "altro"]),
        ("cert_note", "Certificazioni — chi le ha fatte e quando", "txt", None),
        ("attenzione", "Attenzione e comportamento", "sel",
         [_NO, "adeguati", "si distrae facilmente", "agitato, impulsivo", "lento, «sognatore»"]),
        ("compiti", "Compiti a casa", "sel",
         [_NO, "autonomo", "serve aiuto", "tempi molto lunghi", "motivo di litigi"]),
        ("scuola_umore", "Rapporto con la scuola", "sel",
         [_NO, "ci va volentieri", "indifferente", "rifiuto, ansia"]),
    ]),
    ("📚 Scuola nel dettaglio", [
        ("classe", "Scuola e classe attuale", "txt", None),
        ("tempo_scuola", "Orario", "sel", [_NO, "tempo normale", "tempo pieno", "tempo prolungato"]),
        ("cambi_scuola", "Cambi di scuola o di insegnanti (quando, perché)", "txt", None),
        ("lettura_voce", "Lettura ad alta voce", "sel",
         [_NO, "fluente", "lenta", "sillabata", "con errori", "la evita"]),
        ("comprensione", "Comprensione del testo", "sel",
         [_NO, "buona", "capisce se ascolta ma non se legge", "fatica", "molto difficile"]),
        ("ortografia", "Ortografia", "sel", [_NO, "corretta", "errori occasionali", "molti errori"]),
        ("grafia", "Grafia", "sel",
         [_NO, "leggibile", "disordinata", "poco leggibile", "scrive con fatica o dolore"]),
        ("copia", "Copia dalla lavagna", "sel",
         [_NO, "senza problemi", "lenta", "perde il segno", "con errori"]),
        ("tabelline", "Tabelline e fatti aritmetici", "sel",
         [_NO, "apprese", "in parte", "non apprese"]),
        ("problemi", "Problemi di matematica", "sel",
         [_NO, "li risolve", "capisce ma sbaglia i calcoli", "non capisce il testo", "molto difficile"]),
        ("memoria", "Memoria di lavoro", "sel",
         [_NO, "adeguata", "dimentica le consegne", "fatica a memorizzare", "dimentica materiale e compiti"]),
        ("stanchezza", "Stanchezza a scuola", "sel",
         [_NO, "no", "a fine giornata", "già a metà mattina"]),
        ("materie_facili", "Materie in cui va bene", "txt", None),
        ("materie_difficili", "Materie in cui fatica", "txt", None),
        ("aiuti", "Aiuti in atto", "multi",
         ["insegnante di sostegno", "PDP applicato", "strumenti compensativi",
          "doposcuola / tutor", "logopedia in orario scolastico"]),
        ("andamento", "Andamento e voti dell'ultimo anno", "txt", None),
        ("compagni", "Rapporto con i compagni", "sel",
         [_NO, "buono", "pochi amici", "tende a isolarsi", "conflitti frequenti", "subisce prese in giro / bullismo"]),
        ("scuola_note", "Note sulla scuola", "area", None),
    ]),
    ("📱 Schermi e tecnologia", [
        ("schermi", "Schermi nei giorni di scuola", "sel",
         [_NO, "meno di 1 ora", "1–2 ore", "2–4 ore", "oltre 4 ore"]),
        ("schermi_weekend", "Schermi nel fine settimana", "sel",
         [_NO, "meno di 1 ora", "1–2 ore", "2–4 ore", "oltre 4 ore"]),
        ("schermi_dispositivi", "Dispositivi", "multi",
         ["TV", "tablet", "smartphone", "console", "computer"]),
        ("schermi_inizio", "Età del primo uso regolare", "txt", None),
        ("schermi_contenuti", "Cosa guarda o fa", "multi",
         ["cartoni / film", "video brevi (YouTube, TikTok)", "videogiochi", "social",
          "studio / compiti", "videochiamate"]),
        ("schermi_sera", "Schermi la sera", "sel",
         [_NO, "no", "sì, fino a un'ora prima di dormire", "sì, anche a letto"]),
        ("schermi_pasti", "Schermi durante i pasti", "sel", [_NO, "mai", "a volte", "sempre"]),
        ("schermi_controllo", "Uso", "sel", [_NO, "con un adulto", "in parte da solo", "da solo"]),
        ("schermi_reazione", "Quando si spegne lo schermo", "sel",
         [_NO, "accetta", "protesta", "crisi di rabbia o pianto"]),
        ("schermi_postura", "Distanza e postura", "sel",
         [_NO, "adeguate", "molto vicino allo schermo", "sdraiato / postura scorretta"]),
        ("schermi_note", "Note", "txt", None),
    ]),
    ("🩺 Salute dopo il primo anno", [
        ("malattie", "Malattie importanti, ricoveri, interventi", "area", None),
        ("traumi", "Traumi cranici", "chk", None),
        ("convulsioni", "Convulsioni (anche febbrili)", "chk", None),
        ("allergie", "Allergie, asma", "txt", None),
        ("respirazione", "Respirazione e ORL", "multi",
         ["respira a bocca aperta", "russa", "pause nel respiro di notte",
          "adenoidi / tonsille operate", "otiti ricorrenti"]),
        ("ortodonzia", "Ortodonzia / apparecchio", "txt", None),
        ("vista", "Occhiali, visite oculistiche, bende", "txt", None),
        ("udito", "Udito — controlli ed esiti", "txt", None),
        ("farmaci", "Farmaci in corso", "txt", None),
    ]),
    ("🌙 Abitudini di oggi", [
        ("sonno", "Sonno: ore per notte e ora in cui si addormenta", "txt", None),
        ("sonno_qualita", "Sonno — cosa succede", "multi",
         ["fatica ad addormentarsi", "risvegli notturni", "incubi / terrori notturni",
          "dorme con i genitori", "sonnambulismo", "digrigna i denti"]),
        ("aperto", "Gioco all'aperto", "sel",
         [_NO, "ogni giorno", "qualche volta a settimana", "raramente"]),
        ("sport", "Sport e attività extrascolastiche", "txt", None),
        ("alimentazione", "Alimentazione — selettività, difficoltà", "txt", None),
    ]),
]


def _assicura_tabella(conn) -> None:
    # Una volta per sessione: il DDL a ogni rerun era la causa dei lock.
    if st.session_state.get("_anam_sviluppo_schema_ok"):
        return
    try:
        cur = conn.cursor()
        cur.execute(
            "CREATE TABLE IF NOT EXISTS anamnesi_sviluppo ("
            " paziente_id INTEGER PRIMARY KEY,"
            " dati TEXT,"
            " aggiornato_il TIMESTAMP DEFAULT CURRENT_TIMESTAMP,"
            " aggiornato_da TEXT)")
        conn.commit()
        st.session_state["_anam_sviluppo_schema_ok"] = True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass


def carica_anamnesi_sviluppo(conn, paz_id) -> dict:
    if conn is None or not paz_id:
        return {}
    _assicura_tabella(conn)
    try:
        cur = conn.cursor()
        cur.execute("SELECT dati FROM anamnesi_sviluppo WHERE paziente_id=%s", (int(paz_id),))
        r = cur.fetchone()
        if not r:
            return {}
        raw = r.get("dati") if isinstance(r, dict) else r[0]
        return json.loads(raw) if raw else {}
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return {}


def _salva(conn, paz_id, dati: dict) -> tuple[bool, str]:
    _assicura_tabella(conn)
    try:
        chi = str(st.session_state.get("username") or st.session_state.get("user") or "")
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO anamnesi_sviluppo (paziente_id, dati, aggiornato_il, aggiornato_da) "
            "VALUES (%s, %s, CURRENT_TIMESTAMP, %s) "
            "ON CONFLICT (paziente_id) DO UPDATE SET dati=EXCLUDED.dati, "
            "aggiornato_il=CURRENT_TIMESTAMP, aggiornato_da=EXCLUDED.aggiornato_da",
            (int(paz_id), json.dumps(dati, ensure_ascii=False), chi))
        conn.commit()
        return True, ""
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        return False, str(e)


def _compilato(v) -> bool:
    if v is None or v is False:
        return False
    if isinstance(v, (list, str)):
        return bool(v)
    if isinstance(v, (int, float)):
        return v > 0
    return True


def _widget(k, label, tipo, opts, val, key):
    # Il valore salvato fa da default solo al primo disegno: dopo comanda
    # quello che l'operatore sta scrivendo.
    if key not in st.session_state:
        if tipo == "mesi":
            st.session_state[key] = int(val or 0)
        elif tipo == "chk":
            st.session_state[key] = bool(val)
        elif tipo == "multi":
            st.session_state[key] = [x for x in (val or []) if x in opts]
        elif tipo == "sel":
            st.session_state[key] = val if val in opts else _NO
        else:
            st.session_state[key] = val or ""
    if tipo == "mesi":
        return st.number_input(label, min_value=0, max_value=144, step=1, key=key,
                               help="0 = non noto")
    if tipo == "chk":
        return st.checkbox(label, key=key)
    if tipo == "multi":
        return st.multiselect(label, opts, key=key)
    if tipo == "sel":
        return st.selectbox(label, opts, key=key)
    if tipo == "area":
        return st.text_area(label, key=key, height=68)
    return st.text_input(label, key=key)


def render_anamnesi_sviluppo(conn, paz_id, px: str) -> dict:
    """Disegna il blocco e lo restituisce. Il salvataggio ha il suo bottone,
    perche' i dati sono condivisi fra moduli: non devono dipendere dal
    salvataggio della scheda in cui ci si trova."""
    if conn is None or not paz_id:
        st.info("Seleziona un paziente per compilare l'anamnesi dello sviluppo.")
        return {}

    salvati = carica_anamnesi_sviluppo(conn, paz_id)
    px = f"{px}_{paz_id}"
    st.caption("Compilata una volta, compare uguale nel Protocollo di valutazione, "
               "nell'anamnesi Castagnini e nella Diagnosi assistita. "
               "Tutti i campi sono facoltativi.")

    dati: dict = {}
    for titolo, campi in SEZIONI:
        n = sum(1 for k, *_ in campi if _compilato(salvati.get(k)))
        with st.expander(f"{titolo}" + (f" · {n} compilati" if n else ""), expanded=False):
            cols = st.columns(2)
            i = 0
            for k, label, tipo, opts in campi:
                if tipo in ("area", "multi"):
                    dati[k] = _widget(k, label, tipo, opts, salvati.get(k), f"{px}_{k}")
                    i = 0
                    continue
                with cols[i % 2]:
                    dati[k] = _widget(k, label, tipo, opts, salvati.get(k), f"{px}_{k}")
                i += 1

    if st.button("💾 Salva anamnesi dello sviluppo", key=f"{px}_salva"):
        ok, err = _salva(conn, paz_id, dati)
        if ok:
            st.success("Anamnesi dello sviluppo salvata.")
        else:
            st.error(f"Salvataggio non riuscito: {err}")
    elif any((_compilato(v) or _compilato(salvati.get(k))) and v != salvati.get(k) for k, v in dati.items()):
        st.caption("⚠️ Ci sono modifiche non ancora salvate in questo blocco.")
    return dati


def sintesi_anamnesi_sviluppo(dati: dict) -> list[str]:
    """Righe leggibili, solo per i campi compilati, raggruppate per sezione."""
    out = []
    for titolo, campi in SEZIONI:
        righe = []
        for k, label, tipo, _opts in campi:
            v = (dati or {}).get(k)
            if not _compilato(v):
                continue
            if tipo == "chk":
                righe.append(label)
            elif tipo == "multi":
                righe.append(f"{label}: {', '.join(v)}")
            elif tipo == "mesi":
                righe.append(f"{label.replace(' (mesi)', '')}: {int(v)} mesi")
            else:
                righe.append(f"{label}: {' '.join(str(v).split())}")
        if righe:
            out.append(titolo.split(" ", 1)[1].upper())
            out.extend("- " + r for r in righe)
    return out
