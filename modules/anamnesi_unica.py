# -*- coding: utf-8 -*-
"""Anamnesi unica del paziente: dalla gravidanza a oggi.

Perche' esiste
--------------
Lo stesso periodo di vita (gravidanza, parto, neonatale, tappe) veniva
chiesto in tre moduli diversi, ognuno con la sua copia dei dati:
  · Anamnesi PNEV (modello Teitelbaum)      → anamnesi.pnev_json["anamnesi_the_organism"]
  · Anamnesi Castagnini (0-2 anni)          → anamnesi.pnev_json["anamnesi_castagnini"]
  · Protocollo di valutazione (testo libero) → protocollo_valutazione.dati
Compilata una, le altre restavano vuote, e relazione e diagnosi leggevano
ognuna una fonte diversa.

Qui c'e' una sola anamnesi per paziente, un solo blocco disegnato uguale in
tutti i moduli, due tabelle con una riga per paziente:
  · anamnesi_prima_infanzia  → gravidanza, parto, 0-3 mesi, 0-24 mesi,
                               famiglia, invio, segnali di allerta
  · anamnesi_sviluppo        → dopo i 2 anni, scuola, schermi, salute, abitudini
                               (il blocco gia' esistente, modules/anamnesi_sviluppo.py)

0-2 anni: tappe in mesi e dati oggettivi dal modello Castagnini, osservazioni
qualitative (raddrizzamento, schema del gattonamento, cammino, profilo emotivo
in gravidanza) e profilo di rischio dal modello Teitelbaum.

Recupero: alla prima apertura per un paziente, se questa anamnesi e' vuota,
si leggono le tre fonti vecchie e si riporta quello che c'e'. Le fonti non
vengono toccate: restano leggibili com'erano.
"""
from __future__ import annotations

import json

import streamlit as st

from .anamnesi_sviluppo import (
    _NO, SEZIONI as SEZIONI_SVILUPPO, carica_anamnesi_sviluppo,
    sintesi_anamnesi_sviluppo, _salva as _salva_sviluppo, _compilato,
)

# ── Campi ─────────────────────────────────────────────────────────────
# (chiave, etichetta, tipo, opzioni)
# tipi: sel · multi · mesi · num (opzioni = massimo) · scala (1-5) · txt · area · chk

_RIFL = [_NO, "Presente normale", "Esagerato", "Ridotto / assente", "Asimmetrico", "Non valutato"]

GRUPPI = [
  ("Prima della nascita e nascita", [
    ("🤰 Gravidanza", [
        ("grav_termine", "Termine", "sel",
         [_NO, "A termine (38–42 sett.)", "Pre-termine (<38)", "Post-termine (>42)"]),
        ("grav_settimane", "Settimane (se note)", "num", 45),
        ("grav_tipo", "Gravidanza", "sel", [_NO, "Singola", "Gemellare", "Altro"]),
        ("grav_pianificata", "Desiderio", "sel",
         [_NO, "Pianificata", "Inaspettata ma accettata", "Non desiderata"]),
        ("grav_movimenti", "Movimenti fetali", "sel",
         [_NO, "Normali", "Ridotti", "Eccessivi", "Non valutabili"]),
        ("grav_controlli", "Controlli prenatali", "sel", [_NO, "Regolari", "Parziali", "Assenti"]),
        ("grav_complicanze", "Complicanze", "multi",
         ["Ipertensione / pre-eclampsia", "Diabete gestazionale", "Nausea / vomito grave",
          "Infezioni (TORCH)", "Sanguinamenti", "Minaccia d'aborto", "Placenta previa",
          "Oligoidramnios / polidramnios", "Cadute / traumi addominali", "Ricoveri",
          "Farmaci", "Fumo / alcol / sostanze", "Altro"]),
        ("grav_stato_em", "Stato emotivo della madre (1 molto difficile · 5 sereno)", "scala", None),
        ("grav_coppia", "Qualità della relazione di coppia", "scala", None),
        ("grav_supporto", "Supporto familiare e sociale", "scala", None),
        ("grav_eventi", "Eventi stressanti", "multi",
         ["Lutto in famiglia", "Separazione / divorzio", "Violenza domestica", "Perdita del lavoro",
          "Trasloco / cambio paese", "Conflitti familiari gravi", "Problemi economici",
          "Malattia grave in famiglia", "Altro"]),
        ("grav_note", "Note sulla gravidanza (decorso, terapie, eventi)", "area", None),
    ]),
    ("🏥 Parto", [
        ("parto_tipo", "Tipo di parto", "sel",
         [_NO, "Spontaneo", "Indotto", "Distocico", "Cesareo programmato", "Cesareo d'urgenza"]),
        ("parto_presentazione", "Presentazione", "sel", [_NO, "Cefalica", "Podalica", "Trasversa", "Altro"]),
        ("parto_travaglio", "Travaglio", "sel", [_NO, "Rapido", "Normale", "Prolungato"]),
        ("parto_travaglio_ore", "Durata del travaglio (ore)", "num", 72),
        ("parto_cordone", "Cordone ombelicale", "sel",
         [_NO, "Nessun problema", "Giro di cordone", "Più giri di cordone", "Nodo vero",
          "Cordone corto", "Prolasso"]),
        ("parto_strumenti", "Strumenti", "multi", ["Forcipe", "Ventosa"]),
        ("parto_complicanze", "Complicanze", "multi",
         ["Distress fetale", "Emorragia materna",
          "Anestesia generale", "Rottura prematura delle membrane", "Distocia di spalla", "Altro"]),
        ("parto_peso", "Peso alla nascita (g)", "txt", None),
        ("parto_apgar1", "APGAR a 1'", "num", 10),
        ("parto_apgar5", "APGAR a 5'", "num", 10),
        ("parto_pianto", "Pianto alla nascita", "sel", [_NO, "Immediato", "Tardivo", "Assente"]),
        ("parto_contatto", "Contatto pelle a pelle", "sel", [_NO, "Immediato", "Ritardato", "No"]),
        ("parto_segnalazioni", "Dopo il parto", "multi",
         ["TIN", "Ittero", "Fototerapia", "Incubatrice", "Ossigeno", "Altro"]),
        ("parto_osped_motivo", "Ricovero del neonato — motivo e durata", "txt", None),
        ("parto_note", "Note sul parto", "area", None),
    ]),
    ("👶 Primi tre mesi", [
        ("neo_allattamento", "Allattamento", "sel",
         [_NO, "Seno esclusivo", "Misto", "Artificiale", "Non avviato"]),
        ("neo_durata_allatt", "Durata dell'allattamento al seno", "txt", None),
        ("neo_suzione", "Suzione", "sel",
         [_NO, "Efficace", "Debole", "Difficoltosa", "Con dolore per la madre"]),
        ("neo_coliche", "Coliche", "sel", [_NO, "Assenti", "Lievi", "Severe"]),
        ("neo_sonno", "Sonno", "sel",
         [_NO, "Regolare", "Difficoltà ad addormentarsi", "Risvegli frequenti"]),
        ("neo_pianto", "Pianto", "sel", [_NO, "Normale", "Eccessivo / inconsolabile", "Scarso / assente"]),
        ("neo_tono", "Tono muscolare", "sel", [_NO, "Normale", "Ipotonico", "Ipertonico", "Misto"]),
        ("neo_difficolta", "Difficoltà", "multi",
         ["Reflusso gastroesofageo", "Vomito frequente", "Rifiuto seno / biberon",
          "Difficoltà di deglutizione", "Ipersensibilità orale", "Soffocamento frequente"]),
        ("neo_rifl_moro", "Riflesso di Moro", "sel", _RIFL),
        ("neo_rifl_suzione", "Suzione non nutritiva", "sel", _RIFL),
        ("neo_rifl_prensione", "Prensione palmare", "sel", _RIFL),
        ("neo_rifl_babinski", "Babinski", "sel", _RIFL),
        ("neo_rifl_galant", "Galant", "sel", _RIFL),
        ("neo_rifl_rtln", "RTLN (collo tonico labirintico)", "sel", _RIFL),
        ("neo_note", "Note sui primi mesi", "area", None),
    ]),
  ]),
  ("Primi due anni", [
    ("🏃 Tappe motorie (età in mesi)", [
        ("mot_capo", "Controllo del capo", "mesi", None),
        ("mot_rotolamento", "Rotolamento", "mesi", None),
        ("mot_seduta", "Seduto", "mesi", None),
        ("mot_seduta_tipo", "Seduto", "sel", [_NO, "Con supporto", "Senza supporto"]),
        ("mot_gatt", "Gattonamento", "sel", [_NO, "Sì", "Parziale", "No (saltato)"]),
        ("mot_gatt_mesi", "Gattonamento", "mesi", None),
        ("mot_eretta", "In piedi con appoggio", "mesi", None),
        ("mot_passi", "Primi passi autonomi", "mesi", None),
    ]),
    ("🧭 Qualità del movimento — Teitelbaum", [
        ("mot_simmetria", "Simmetria posturale (0-4 mesi)", "sel",
         [_NO, "Simmetrica", "Asimmetrica DX", "Asimmetrica SX"]),
        ("mot_tilt", "Raddrizzamento (tilt test)", "sel",
         [_NO, "Presente normale", "Ritardato", "Assente", "Non osservato"]),
        ("mot_atnr", "ATNR (posizione dello schermitore)", "sel",
         [_NO, "Fisiologico", "Persistente >6 mesi", "Non osservato"]),
        ("mot_gatt_schema", "Schema del gattonamento", "sel",
         [_NO, "Crociato (normale)", "Omolaterale", "Strisciamento", "Rotolamento"]),
        ("mot_gatt_simm", "Simmetria del gattonamento", "sel",
         [_NO, "Simmetrica", "Asimmetrica", "Non valutabile"]),
        ("mot_appoggio", "Appoggio plantare nel cammino", "sel",
         [_NO, "Tallone-punta (normale)", "Punta-punta", "Piatto"]),
        ("mot_base", "Base d'appoggio", "sel", [_NO, "Normale", "Allargata", "Stretta"]),
        ("mot_cadute", "Cadute", "sel", [_NO, "No", "Sì, rare", "Sì, frequenti"]),
        ("mot_rifl_prot", "Riflessi protettivi", "sel", [_NO, "Presenti", "Ridotti", "Assenti"]),
        ("mot_lateral", "Preferenza di mano prima dei 12 mesi", "sel",
         [_NO, "No", "Sì, destra", "Sì, sinistra"]),
        ("mot_crossing", "Attraversamento della linea mediana — osservazioni", "txt", None),
        ("mot_note", "Note sullo sviluppo motorio", "area", None),
    ]),
    ("👁️ Sensoriale e comunicativo", [
        ("com_sorriso", "Sorriso sociale", "mesi", None),
        ("com_tracking", "Segue gli oggetti con lo sguardo", "mesi", None),
        ("com_lallazione", "Lallazione", "mesi", None),
        ("com_nome", "Risponde al nome", "mesi", None),
        ("com_parole", "Prime parole", "mesi", None),
        ("com_suoni", "Risposta ai suoni", "sel", [_NO, "Normale", "Ridotta", "Esagerata", "Variabile"]),
        ("com_occhi", "Contatto oculare", "sel", [_NO, "Buono", "Ridotto", "Assente", "Intermittente"]),
        ("com_imitazione", "Imitazione di gesti ed espressioni", "sel", [_NO, "Presente", "Parziale", "Assente"]),
        ("com_reattivita", "Reattività sensoriale", "multi",
         ["Ipersensibilità tattile", "Iposensibilità tattile", "Ipersensibilità uditiva",
          "Iposensibilità uditiva", "Ipersensibilità visiva", "Ricerca di stimoli sensoriali",
          "Difficoltà con le consistenze", "Dondolamento / movimenti ritmici",
          "Fascinazione per oggetti rotanti", "Preferenze olfattive intense"]),
        ("com_note", "Note sensoriali e comunicative", "area", None),
    ]),
    ("🍼 Alimentazione e sonno (0-2 anni)", [
        ("al_svez", "Svezzamento", "sel", [_NO, "Tradizionale", "Autosvezzamento (BLW)", "Misto"]),
        ("al_svez_mesi", "Svezzamento", "mesi", None),
        ("al_svez_diff", "Difficoltà nello svezzamento", "sel", [_NO, "No", "Sì"]),
        ("al_mastic", "Masticazione", "sel", [_NO, "Normale", "Difficoltosa"]),
        ("al_selett", "Selettività alimentare", "sel", [_NO, "No", "Lieve", "Marcata"]),
        ("al_selett_desc", "Cosa rifiuta", "txt", None),
        ("al_sonno_ore", "Ore di sonno per notte", "num", 20),
        ("al_sonnellini", "Sonnellini diurni", "sel", [_NO, "Sì", "No", "Ridotti precocemente"]),
        ("al_note", "Note", "area", None),
    ]),
  ]),
]

GRUPPI_FINALI = [
    ("👨‍👩‍👧 Famiglia e contesto", [
        ("fam_familiarita", "Familiarità per", "multi",
         ["DSA (dislessia, disgrafia, discalculia)", "ADHD / attenzione", "Spettro autistico",
          "Disturbi del linguaggio", "Balbuzie", "Problemi visivi significativi / strabismo",
          "Problemi uditivi", "Disturbi della coordinazione", "Epilessia / disturbi neurologici",
          "Ansia / depressione", "Altro"]),
        ("fam_n_fratelli", "Fratelli e sorelle", "num", 12),
        ("fam_fratelli_simili", "Fratelli con difficoltà simili", "sel", [_NO, "No", "Sì"]),
        ("fam_nido", "Nido", "sel", [_NO, "No", "Sì"]),
        ("fam_nido_mesi", "Ingresso al nido", "mesi", None),
        ("fam_nido_adatt", "Adattamento al nido", "sel", [_NO, "Buono", "Difficile", "Molto difficile"]),
        ("fam_lingua", "Lingua in casa", "sel", [_NO, "Italiano", "Bilingue", "Altra lingua"]),
        ("fam_lingua_note", "Quali lingue, chi le parla", "txt", None),
        ("fam_note", "Note sulla famiglia e sul contesto", "area", None),
    ]),
    ("📋 Motivo dell'invio", [
        ("inv_chi", "Chi invia", "sel",
         [_NO, "Genitori", "Pediatra", "Neuropsichiatra", "Neurologo", "Logopedista",
          "Insegnante", "Oculista / ortottista", "Altro"]),
        ("inv_chi_altro", "Specificare", "txt", None),
        ("inv_da_quanto", "Da quanto tempo c'è la preoccupazione", "txt", None),
        ("inv_preoccupazione", "Preoccupazione principale", "area", None),
        ("inv_valutazioni", "Valutazioni precedenti (chi, quando, esito)", "area", None),
        ("inv_val_visiva", "Valutazione visiva / optometrica precedente", "txt", None),
        ("inv_trattamenti", "Trattamenti fatti o in corso", "multi",
         ["Logopedia", "Psicomotricità", "Neuropsicomotricità", "Fisioterapia",
          "Terapia occupazionale", "Optometria / vision therapy", "Psicoterapia",
          "Sostegno scolastico", "Altro"]),
        ("inv_trattamenti_note", "Trattamenti — durata ed esiti", "area", None),
        ("inv_note", "Note", "area", None),
    ]),
    ("⚠️ Segnali di allerta", [
        ("all_presenti", "Segnali riferiti o osservati", "multi",
         ["Gattonamento assente", "Cammino in punta di piedi persistente",
          "Perdita di abilità già acquisite", "Nessuna parola a 18 mesi",
          "Nessuna frase a 24 mesi", "Contatto oculare scarso", "Non risponde al nome",
          "Movimenti ripetitivi", "Asimmetrie motorie marcate", "Cadute molto frequenti",
          "Episodi di assenza / crisi", "Regressione del linguaggio"]),
        ("all_note", "Note", "area", None),
    ]),
]


def _sezioni_prima_infanzia():
    for _g, sez in GRUPPI:
        yield from sez
    yield from GRUPPI_FINALI


# ── Database ──────────────────────────────────────────────────────────

def _assicura_tabella(conn) -> None:
    if st.session_state.get("_anam_pi_schema_ok"):
        return
    try:
        cur = conn.cursor()
        cur.execute(
            "CREATE TABLE IF NOT EXISTS anamnesi_prima_infanzia ("
            " paziente_id INTEGER PRIMARY KEY,"
            " dati TEXT,"
            " origine TEXT,"
            " aggiornato_il TIMESTAMP DEFAULT CURRENT_TIMESTAMP,"
            " aggiornato_da TEXT)")
        conn.commit()
        st.session_state["_anam_pi_schema_ok"] = True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass


def _riga(conn, paz_id):
    _assicura_tabella(conn)
    try:
        cur = conn.cursor()
        cur.execute("SELECT dati, origine FROM anamnesi_prima_infanzia WHERE paziente_id=%s",
                    (int(paz_id),))
        r = cur.fetchone()
        if not r:
            return None, ""
        raw = r.get("dati") if isinstance(r, dict) else r[0]
        ori = r.get("origine") if isinstance(r, dict) else r[1]
        return (json.loads(raw) if raw else {}), (ori or "")
    except Exception:
        # Errore di lettura: NON va confuso con «riga assente», altrimenti
        # il recupero partirebbe e sovrascriverebbe l'anamnesi salvata.
        try:
            conn.rollback()
        except Exception:
            pass
        return {}, "errore di lettura"


def _salva(conn, paz_id, dati: dict, origine: str = "") -> tuple[bool, str]:
    _assicura_tabella(conn)
    try:
        chi = str(st.session_state.get("username") or st.session_state.get("user") or "")
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO anamnesi_prima_infanzia (paziente_id, dati, origine, aggiornato_il, aggiornato_da) "
            "VALUES (%s, %s, %s, CURRENT_TIMESTAMP, %s) "
            "ON CONFLICT (paziente_id) DO UPDATE SET dati=EXCLUDED.dati, "
            "origine=COALESCE(NULLIF(EXCLUDED.origine, ''), anamnesi_prima_infanzia.origine), "
            "aggiornato_il=CURRENT_TIMESTAMP, aggiornato_da=EXCLUDED.aggiornato_da",
            (int(paz_id), json.dumps(dati, ensure_ascii=False, default=str), origine, chi))
        conn.commit()
        return True, ""
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        return False, str(e)


def carica_prima_infanzia(conn, paz_id) -> dict:
    if conn is None or not paz_id:
        return {}
    dati, _ori = _riga(conn, paz_id)
    if dati is None:
        dati = _recupera_e_salva(conn, paz_id)
    return dati or {}


# ── Recupero dalle tre anamnesi precedenti ────────────────────────────

def _json(v):
    if isinstance(v, dict):
        return v
    if isinstance(v, str) and v.strip():
        try:
            x = json.loads(v)
            return x if isinstance(x, dict) else {}
        except Exception:
            return {}
    return {}


def _leggibile(v):
    """I codici del Castagnini ("cesareo_urgenza") diventano testo."""
    if not isinstance(v, str) or not v.strip():
        return v
    t = v.strip().replace("_", " ")
    return t[0].upper() + t[1:]


def _metti(d: dict, k: str, v):
    """Scrive solo se il campo e' vuoto: la prima fonte che ha il dato vince."""
    if v is None or v == "" or v == [] or v is False:
        return
    if isinstance(v, (int, float)) and not isinstance(v, bool) and v <= 0:
        return
    if not _compilato(d.get(k)):
        d[k] = v


def _aggiungi_lista(d: dict, k: str, voci):
    voci = [x for x in (voci or []) if x]
    if voci:
        d[k] = list(dict.fromkeys((d.get(k) or []) + voci))


def _unisci_note(d: dict, k: str, testo, etichetta: str = ""):
    testo = " ".join(str(testo or "").split())
    if not testo:
        return
    riga = f"{etichetta}: {testo}" if etichetta else testo
    prima = (d.get(k) or "").strip()
    if riga in prima:
        return
    d[k] = f"{prima}\n{riga}".strip()


def _da_castagnini(d: dict, c: dict):
    g = c.get("gravidanza") or {}
    _metti(d, "grav_termine", {"termine": "A termine (38–42 sett.)",
                               "pretermine": "Pre-termine (<38)",
                               "posttermine": "Post-termine (>42)"}.get(g.get("settimane"),
                                                                       _leggibile(g.get("settimane"))))
    _metti(d, "grav_settimane", g.get("settimane_numero"))
    _metti(d, "grav_tipo", _leggibile(g.get("tipo")))
    _metti(d, "grav_movimenti", _leggibile(g.get("movimenti_fetali")))
    _metti(d, "grav_controlli", _leggibile(g.get("controlli_regolari")))
    comp = g.get("complicanze") or {}
    etich = {"ipertensione": "Ipertensione / pre-eclampsia", "nausea_grave": "Nausea / vomito grave",
             "infezioni": "Infezioni (TORCH)", "farmaci": "Farmaci",
             "cadute_traumi": "Cadute / traumi addominali", "altro": "Altro"}
    _aggiungi_lista(d, "grav_complicanze", [etich[k] for k in etich if comp.get(k)])
    if comp.get("stress_emotivo"):
        _unisci_note(d, "grav_note", "stress emotivo / lutto in gravidanza")
    _unisci_note(d, "grav_note", comp.get("altro_desc"), "Altre complicanze")
    _unisci_note(d, "grav_note", g.get("note"))

    p = c.get("parto") or {}
    _metti(d, "parto_tipo", {"spontaneo": "Spontaneo", "indotto": "Indotto",
                             "cesareo_programmato": "Cesareo programmato",
                             "cesareo_urgenza": "Cesareo d'urgenza"}.get(p.get("tipo"), _leggibile(p.get("tipo"))))
    _metti(d, "parto_presentazione", _leggibile(p.get("presentazione")))
    _metti(d, "parto_travaglio", _leggibile(p.get("durata_travaglio")))
    s = p.get("strumenti") or {}
    _aggiungi_lista(d, "parto_strumenti", [x for x, k in (("Forcipe", "forcipe"), ("Ventosa", "ventosa")) if s.get(k)])
    pc = p.get("complicanze") or {}
    _aggiungi_lista(d, "parto_complicanze",
                    [x for x, k in (("Distress fetale", "distress_fetale"),
                                    ("Emorragia materna", "emorragia"), ("Altro", "altro")) if pc.get(k)])
    if pc.get("cordone"):
        _metti(d, "parto_cordone", "Giro di cordone")
    _unisci_note(d, "parto_note", pc.get("altro_desc"), "Altre complicanze")
    _metti(d, "parto_apgar1", p.get("apgar_1"))
    _metti(d, "parto_apgar5", p.get("apgar_5"))
    if str(p.get("ospedalizzazione_neonato", "")).lower().startswith("s"):
        _aggiungi_lista(d, "parto_segnalazioni", ["TIN"])
    _metti(d, "parto_osped_motivo", p.get("ospedalizzazione_motivo"))
    _unisci_note(d, "parto_note", p.get("note"))

    n = c.get("neonatale") or {}
    for k, src in (("neo_allattamento", "allattamento"), ("neo_suzione", "difficolta_suzione"),
                   ("neo_coliche", "coliche"), ("neo_sonno", "sonno"), ("neo_pianto", "pianto"),
                   ("neo_tono", "tono_nascita")):
        _metti(d, k, _leggibile(n.get(src)))
    r = n.get("riflessi") or {}
    for k, src in (("neo_rifl_moro", "moro"), ("neo_rifl_suzione", "suzione"),
                   ("neo_rifl_prensione", "prensione"), ("neo_rifl_babinski", "babinski"),
                   ("neo_rifl_galant", "galant"), ("neo_rifl_rtln", "tonic_neck")):
        v = r.get(src)
        if v and v not in ("presente", "non valutato"):   # i default del modulo, non dati
            _metti(d, k, _leggibile(v))
    _unisci_note(d, "neo_note", n.get("note"))

    m = c.get("sviluppo_motorio") or {}
    for k, src in (("mot_capo", "controllo_capo_mesi"), ("mot_rotolamento", "rotolamento_mesi"),
                   ("mot_seduta", "stazione_seduta_mesi"), ("mot_gatt_mesi", "gattonamento_mesi"),
                   ("mot_eretta", "posizione_eretta_mesi"), ("mot_passi", "primi_passi_mesi")):
        _metti(d, k, m.get(src))
    _metti(d, "mot_seduta_tipo", _leggibile(m.get("stazione_seduta_tipo")))
    gf = m.get("gattonamento_fatto")
    _metti(d, "mot_gatt", {"si": "Sì", "sì": "Sì", "no": "No (saltato)", "saltato": "No (saltato)",
                           "strisciamento": "Parziale"}.get(gf, _leggibile(gf)))
    if gf == "strisciamento":
        _metti(d, "mot_gatt_schema", "Strisciamento")
    _metti(d, "mot_lateral", {"no": "No", "si_dx": "Sì, destra", "si_sx": "Sì, sinistra"}
           .get(m.get("lateralizzazione_precoce"), _leggibile(m.get("lateralizzazione_precoce"))))
    _unisci_note(d, "mot_note", m.get("qualita_movimento"), "Qualità del movimento")
    _unisci_note(d, "mot_note", m.get("note"))

    ss = c.get("sviluppo_sensoriale") or {}
    for k, src in (("com_tracking", "tracking_mesi"), ("com_sorriso", "sorriso_sociale_mesi"),
                   ("com_lallazione", "lallazione_mesi"), ("com_parole", "prime_parole_mesi"),
                   ("com_nome", "risposta_nome_mesi")):
        _metti(d, k, ss.get(src))
    _metti(d, "com_suoni", _leggibile(ss.get("risposta_suoni")))
    _metti(d, "com_occhi", _leggibile(ss.get("contatto_oculare")))
    _metti(d, "com_imitazione", _leggibile(ss.get("imitazione")))
    _unisci_note(d, "com_note", ss.get("note"))

    a = c.get("alimentazione_sonno") or {}
    _metti(d, "al_svez_mesi", a.get("svezzamento_mesi"))
    _metti(d, "al_svez_diff", _leggibile(a.get("svezzamento_difficolta")))
    _metti(d, "al_mastic", _leggibile(a.get("masticazione")))
    _metti(d, "al_selett", _leggibile(a.get("selettivita_alimentare")))
    _metti(d, "al_selett_desc", a.get("selettivita_desc"))
    _metti(d, "al_sonno_ore", a.get("sonno_ore_notte"))
    _metti(d, "al_sonnellini", _leggibile(a.get("sonnellini")))
    _unisci_note(d, "al_note", a.get("sonno_note"), "Sonno")

    f = c.get("storia_familiare") or {}
    fam = []
    if str(f.get("familiarita_apprendimento", "")).lower().startswith("s"):
        fam.append("DSA (dislessia, disgrafia, discalculia)")
    if str(f.get("familiarita_dsa_adhd", "")).lower().startswith("s"):
        fam += ["DSA (dislessia, disgrafia, discalculia)", "ADHD / attenzione"]
    if str(f.get("familiarita_autismo", "")).lower().startswith("s"):
        fam.append("Spettro autistico")
    _aggiungi_lista(d, "fam_familiarita", fam)
    _metti(d, "fam_fratelli_simili", _leggibile(f.get("fratelli_difficolta")))
    _metti(d, "fam_nido", _leggibile(f.get("nido")))
    _metti(d, "fam_nido_mesi", f.get("nido_eta_mesi"))
    _metti(d, "fam_nido_adatt", _leggibile(f.get("nido_adattamento")))
    _metti(d, "fam_lingua", _leggibile(f.get("lingua_casa")))
    _metti(d, "fam_lingua_note", f.get("lingua_altro"))
    _unisci_note(d, "fam_note", f.get("note"))

    mi = c.get("motivo_invio") or {}
    _metti(d, "inv_chi", _leggibile(mi.get("inviante")))
    _metti(d, "inv_chi_altro", mi.get("inviante_altro"))
    _metti(d, "inv_preoccupazione", mi.get("preoccupazione_principale"))
    _unisci_note(d, "inv_valutazioni", mi.get("valutazioni_tipo"))
    _unisci_note(d, "inv_trattamenti_note", mi.get("terapie_tipo"), "In corso")
    _unisci_note(d, "inv_note", mi.get("note"))


def _da_teitelbaum(d: dict, t: dict):
    g = t.get("gravidanza") or {}
    _metti(d, "grav_termine", {"Termine (38-42 sett.)": "A termine (38–42 sett.)"}
           .get(g.get("termine"), g.get("termine")))
    try:
        _metti(d, "grav_settimane", int(str(g.get("sett") or "0").strip() or 0))
    except Exception:
        _unisci_note(d, "grav_note", g.get("sett"), "Settimane")
    _metti(d, "grav_tipo", g.get("tipo_grav"))
    _metti(d, "grav_pianificata", g.get("pianificata"))
    _metti(d, "grav_movimenti", g.get("movimenti"))
    _metti(d, "grav_controlli", g.get("controlli"))
    _aggiungi_lista(d, "grav_complicanze", g.get("complicanze"))
    for k, src in (("grav_stato_em", "stato_em"), ("grav_coppia", "qualita_coppia"), ("grav_supporto", "supporto")):
        _metti(d, k, g.get(src))
    _aggiungi_lista(d, "grav_eventi", g.get("eventi"))
    _unisci_note(d, "grav_note", g.get("note"))

    p = t.get("parto") or {}
    tipo = p.get("tipo")
    if tipo == "Ventosa/forcipe":
        _metti(d, "parto_tipo", "Distocico")
    else:
        _metti(d, "parto_tipo", {"Naturale": "Spontaneo", "Cesareo emergenza": "Cesareo d'urgenza"}.get(tipo, tipo))
    _metti(d, "parto_presentazione", p.get("pres"))
    comp_t = p.get("complicanze") or []
    if "Cordone al collo" in comp_t:
        _metti(d, "parto_cordone", "Giro di cordone")
    elif "Prolasso del cordone" in comp_t:
        _metti(d, "parto_cordone", "Prolasso")
    _aggiungi_lista(d, "parto_complicanze",
                    [{"Rottura prematura membrane": "Rottura prematura delle membrane"}.get(x, x)
                     for x in comp_t if x not in ("Cordone al collo", "Prolasso del cordone")])
    for k, src in (("parto_apgar1", "apgar1"), ("parto_apgar5", "apgar5")):
        try:
            _metti(d, k, int(p.get(src) or 0))
        except Exception:
            pass
    _metti(d, "parto_pianto", {"Si": "Immediato", "No": "Assente", "Tardivo": "Tardivo"}.get(p.get("pianto"), p.get("pianto")))
    _metti(d, "parto_contatto", {"Si": "Immediato", "No": "No", "Ritardato": "Ritardato"}.get(p.get("contatto"), p.get("contatto")))
    _metti(d, "neo_suzione", p.get("suzione"))
    _unisci_note(d, "parto_note", p.get("durata"), "Durata")
    _unisci_note(d, "parto_note", p.get("note"))

    n = t.get("neonatale") or {}
    _metti(d, "neo_tono", {"Ipotonia": "Ipotonico", "Ipertonia": "Ipertonico"}.get(n.get("tono"), n.get("tono")))
    _metti(d, "neo_pianto", n.get("pianto"))
    rif = n.get("riflessi") or {}
    if isinstance(rif, dict):
        for src, v in rif.items():
            s = src.lower()
            k = ("neo_rifl_moro" if "moro" in s else "neo_rifl_suzione" if "suz" in s else
                 "neo_rifl_prensione" if "prens" in s or "grasp" in s else
                 "neo_rifl_babinski" if "babin" in s else "neo_rifl_galant" if "galant" in s else
                 "neo_rifl_rtln" if "rtl" in s or "tlr" in s or "tonic" in s else None)
            if k:
                _metti(d, k, v)
    _unisci_note(d, "neo_note", n.get("note"))

    a = t.get("alimentazione") or {}
    _metti(d, "neo_allattamento", a.get("allatt"))
    _metti(d, "neo_durata_allatt", a.get("durata_allatt"))
    _metti(d, "neo_suzione", a.get("suzione"))
    _metti(d, "al_svez", {"BLW": "Autosvezzamento (BLW)"}.get(a.get("svez"), a.get("svez")))
    _metti(d, "al_svez_mesi", _int(a.get("eta_svez")))
    diff = a.get("difficolta") or []
    _aggiungi_lista(d, "neo_difficolta", [x for x in diff if x not in (
        "Coliche intense", "Masticazione difficoltosa", "Selettivita' alimentare", "Texture rifiutate")])
    if "Coliche intense" in diff:
        _metti(d, "neo_coliche", "Severe")
    if "Masticazione difficoltosa" in diff:
        _metti(d, "al_mastic", "Difficoltosa")
    sel = a.get("selettivita")
    if isinstance(sel, (int, float)) and sel >= 4:
        _metti(d, "al_selett", "Marcata")
    elif "Selettivita' alimentare" in diff or "Texture rifiutate" in diff:
        _metti(d, "al_selett", "Lieve")
    _unisci_note(d, "al_note", a.get("note"))

    m = t.get("motorio") or {}
    for src, v in (m.get("tappe") or {}).items():
        s = src.lower()
        k = ("mot_capo" if "capo" in s or "testa" in s else "mot_rotolamento" if "rotol" in s else
             "mot_seduta" if "sed" in s else "mot_gatt_mesi" if "gatt" in s else
             "mot_eretta" if "eret" in s or "piedi" in s else
             "mot_passi" if "pass" in s or "cammin" in s else None)
        if k:
            _metti(d, k, _int(v))
    for k, src in (("mot_simmetria", "simmetria"), ("mot_tilt", "tilt"), ("mot_atnr", "atnr"),
                   ("mot_gatt", "gatt_pres"), ("mot_gatt_schema", "gatt_schema"), ("mot_gatt_simm", "gatt_simm"),
                   ("mot_appoggio", "appoggio"), ("mot_base", "base"), ("mot_rifl_prot", "rifl_prot"),
                   ("mot_crossing", "crossing")):
        _metti(d, k, m.get(src))
    _metti(d, "mot_cadute", {"Si - rare": "Sì, rare", "Si - frequenti": "Sì, frequenti"}.get(m.get("cadute"), m.get("cadute")))
    _unisci_note(d, "mot_note", m.get("note"))

    s = t.get("sensoriale") or {}
    _metti(d, "com_parole", _int(s.get("prime_parole")))
    _metti(d, "com_suoni", s.get("suoni"))
    _metti(d, "com_occhi", s.get("occhi"))
    if s.get("nome"):
        _unisci_note(d, "com_note", s.get("nome"), "Risposta al nome")
    _aggiungi_lista(d, "com_reattivita", s.get("sensoriale"))
    _unisci_note(d, "com_note", s.get("note"))

    al = t.get("allerta") or {}
    _aggiungi_lista(d, "all_presenti", al.get("presenti"))
    _unisci_note(d, "all_note", al.get("note"))

    f = t.get("famiglia") or {}
    _metti(d, "fam_n_fratelli", _int(f.get("n_fratelli")))
    _metti(d, "fam_fratelli_simili", f.get("fratelli_simili"))
    _aggiungi_lista(d, "fam_familiarita", [{"ADHD / deficit attenzione": "ADHD / attenzione",
                                            "Disturbo spettro autistico": "Spettro autistico",
                                            "Problemi visivi significativi": "Problemi visivi significativi / strabismo",
                                            "Problemi uditivi / sordita'": "Problemi uditivi",
                                            "Disturbi movimento / coordinazione": "Disturbi della coordinazione"}.get(x, x)
                                           for x in (f.get("familiarita") or [])])
    _metti(d, "fam_lingua", f.get("lingua"))
    _unisci_note(d, "fam_note", f.get("note"))

    i = t.get("invio") or {}
    _metti(d, "inv_chi", {"Neuropsichiatra": "Neuropsichiatra"}.get(i.get("chi_invia"), i.get("chi_invia")))
    _metti(d, "inv_da_quanto", i.get("da_quanto"))
    _metti(d, "inv_preoccupazione", i.get("preoccupazione"))
    _aggiungi_lista(d, "inv_trattamenti", [x.replace("a'", "à") for x in (i.get("trattamenti") or [])])
    _unisci_note(d, "inv_note", i.get("note"))
    return s.get("prime_frasi")


def _int(v):
    try:
        return int(float(str(v).replace(",", ".").strip()))
    except Exception:
        return None


def _trova_anamnesi_protocollo(x):
    """Il blocco anamnesi del protocollo, ovunque sia annidato nei dati."""
    if isinstance(x, dict):
        if "parto_tipo" in x and "gravidanza" in x:
            return x
        for v in x.values():
            r = _trova_anamnesi_protocollo(v)
            if r:
                return r
    return None


def _da_protocollo(d: dict, sv: dict, a: dict):
    _unisci_note(d, "grav_note", a.get("gravidanza"))
    _metti(d, "parto_tipo", {"Eutocico": "Spontaneo"}.get(a.get("parto_tipo"), a.get("parto_tipo")))
    if a.get("giro_cordone"):
        _metti(d, "parto_cordone", "Giro di cordone")
    _metti(d, "parto_peso", a.get("peso_nascita"))
    ap = str(a.get("apgar") or "").replace(" ", "")
    if "/" in ap:
        p1, _, p5 = ap.partition("/")
        _metti(d, "parto_apgar1", _int(p1))
        _metti(d, "parto_apgar5", _int(p5))
    _aggiungi_lista(d, "parto_segnalazioni", a.get("tin_ittero"))
    _unisci_note(d, "neo_note", a.get("periodo_neonatale"))
    _unisci_note(d, "mot_note", a.get("tappe_motorie"), "Tappe (dal protocollo)")
    _unisci_note(d, "com_note", a.get("prime_parole"), "Prime parole / frasi (dal protocollo)")
    fam = a.get("familiarita")
    _unisci_note(d, "fam_note", fam, "Familiarità (dal protocollo)")
    _unisci_note(d, "fam_lingua_note", a.get("bilinguismo"))
    _unisci_note(d, "inv_trattamenti_note", a.get("trattamenti_pregressi"))
    _metti(d, "inv_val_visiva", a.get("valutazione_visiva_pregressa"))
    # Questi appartengono al dopo i 2 anni
    _metti(sv, "malattie", a.get("patologie_note"))
    _metti(sv, "udito", a.get("otiti"))
    _metti(sv, "sport", a.get("hobby"))


def _recupera_e_salva(conn, paz_id) -> dict:
    d: dict = {}
    sv = dict(carica_anamnesi_sviluppo(conn, paz_id) or {})
    sv_prima = dict(sv)
    fonti = []
    try:
        cur = conn.cursor()
        cur.execute("SELECT pnev_json FROM anamnesi WHERE paziente_id=%s "
                    "ORDER BY data_anamnesi DESC, id DESC", (int(paz_id),))
        righe = cur.fetchall() or []
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        righe = []
    cast = teit = None
    for r in righe:
        pj = _json(r.get("pnev_json") if isinstance(r, dict) else r[0])
        c = _json(pj.get("anamnesi_castagnini")) or _json(pj.get("anamnesi_catagnini"))
        t = _json(pj.get("anamnesi_the_organism"))
        if cast is None and c:
            cast = c
        if teit is None and t:
            teit = t
    if cast:
        _da_castagnini(d, cast)
        fonti.append("anamnesi Castagnini")
    if teit:
        frasi = _da_teitelbaum(d, teit)
        _metti(sv, "frasi_mesi", _int(frasi))
        fonti.append("anamnesi PNEV (Teitelbaum)")
    try:
        cur = conn.cursor()
        cur.execute("SELECT dati FROM protocollo_valutazione WHERE paziente_id=%s "
                    "ORDER BY data_valutazione DESC, id DESC LIMIT 1", (int(paz_id),))
        r = cur.fetchone()
        raw = (r.get("dati") if isinstance(r, dict) else r[0]) if r else None
        a = _trova_anamnesi_protocollo(_json(raw))
        if a:
            _da_protocollo(d, sv, a)
            fonti.append("protocollo di valutazione")
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass

    origine = ("Recuperata da: " + ", ".join(fonti)) if fonti else "nuova"
    _salva(conn, paz_id, d, origine)
    if sv != sv_prima:
        _salva_sviluppo(conn, paz_id, sv)
    return d


# ── Disegno ───────────────────────────────────────────────────────────

def _widget(label, tipo, opts, val, key):
    if key not in st.session_state:
        if tipo in ("mesi", "num"):
            massimo = 144 if tipo == "mesi" else int(opts or 999)
            st.session_state[key] = max(0, min(_int(val) or 0, massimo))
        elif tipo == "scala":
            st.session_state[key] = int(val) if isinstance(val, (int, float)) and 1 <= val <= 5 else 0
        elif tipo == "chk":
            st.session_state[key] = bool(val)
        elif tipo == "multi":
            st.session_state[key] = list(val or [])
        elif tipo == "sel":
            st.session_state[key] = val or _NO
        else:
            st.session_state[key] = val or ""
    if tipo == "mesi":
        etich = label if "mesi" in label.lower() else f"{label} (mesi)"
        return st.number_input(etich, min_value=0, max_value=144, step=1, key=key,
                               help="0 = non noto")
    if tipo == "num":
        return st.number_input(label, min_value=0, max_value=int(opts or 999), step=1, key=key,
                               help="0 = non noto")
    if tipo == "scala":
        return st.select_slider(label, options=[0, 1, 2, 3, 4, 5], key=key,
                                format_func=lambda x: "non valutato" if x == 0 else str(x))
    if tipo == "chk":
        return st.checkbox(label, key=key)
    if tipo == "multi":
        # Le voci recuperate dalle anamnesi vecchie restano, anche se scritte
        # in modo diverso da quelle proposte qui.
        extra = [x for x in (st.session_state.get(key) or []) if x not in opts]
        return st.multiselect(label, list(opts) + extra, key=key)
    if tipo == "sel":
        cur = st.session_state.get(key)
        o = list(opts) + ([cur] if cur and cur not in opts else [])
        return st.selectbox(label, o, key=key)
    if tipo == "area":
        return st.text_area(label, key=key, height=68)
    return st.text_input(label, key=key)


def _disegna_sezione(titolo, campi, salvati, px, out):
    n = sum(1 for k, *_ in campi if _compilato(salvati.get(k)))
    with st.expander(titolo + (f" · {n} compilati" if n else ""), expanded=False):
        cols = st.columns(2)
        i = 0
        for k, label, tipo, opts in campi:
            if tipo in ("area", "multi", "scala"):
                out[k] = _widget(label, tipo, opts, salvati.get(k), f"{px}_{k}")
                i = 0
                continue
            with cols[i % 2]:
                out[k] = _widget(label, tipo, opts, salvati.get(k), f"{px}_{k}")
            i += 1


def render_anamnesi_unica(conn, paz_id, px: str = "an") -> tuple[dict, dict]:
    """Disegna l'anamnesi completa. Restituisce (prima_infanzia, sviluppo)."""
    if conn is None or not paz_id:
        st.info("Seleziona un paziente per compilare l'anamnesi.")
        return {}, {}

    pi = carica_prima_infanzia(conn, paz_id)
    _d, origine = _riga(conn, paz_id)
    sv_salv = carica_anamnesi_sviluppo(conn, paz_id) or {}
    px = f"{px}_{paz_id}"

    tot = sum(1 for _t, c in _sezioni_prima_infanzia() for k, *_ in c if _compilato(pi.get(k)))
    tot += sum(1 for _t, c in SEZIONI_SVILUPPO for k, *_ in c if _compilato(sv_salv.get(k)))
    st.caption("Un'unica anamnesi per paziente: la stessa in Anamnesi PNEV, Castagnini, "
               "Protocollo di valutazione e Diagnosi assistita. Tutti i campi sono facoltativi."
               + (f" · {tot} campi compilati" if tot else ""))
    if origine.startswith("Recuperata"):
        st.info(f"📥 {origine}. Controlla i campi e premi «Salva anamnesi» per confermarli.")

    nuovo_pi: dict = {}
    for gruppo, sezioni in GRUPPI:
        st.markdown(f"**{gruppo}**")
        for titolo, campi in sezioni:
            _disegna_sezione(titolo, campi, pi, px, nuovo_pi)

    st.markdown("**Dopo i 2 anni**")
    nuovo_sv: dict = {}
    for titolo, campi in SEZIONI_SVILUPPO:
        # stesse chiavi del blocco originale: i dati gia' salvati restano
        _disegna_sezione(titolo, [(k, l, t, o) for k, l, t, o in campi], sv_salv, f"{px}_sv", nuovo_sv)

    st.markdown("**Contesto e invio**")
    for titolo, campi in GRUPPI_FINALI:
        _disegna_sezione(titolo, campi, pi, px, nuovo_pi)

    _profilo_rischio(nuovo_pi, nuovo_sv)

    # Documenti pregressi: stessa funzione della pagina Rilievi PNEV.
    try:
        from .rilievi_pnev import render_documenti_pregressi
        render_documenti_pregressi(conn, paz_id, f"{px}_doc")
    except Exception as e:
        st.caption(f"Documenti pregressi non disponibili: {e}")

    # Il colloquio anamnestico: stessa funzione della pagina Colloqui clinici.
    try:
        from .colloqui_clinici import render_colloqui
        render_colloqui(conn, paz_id, f"{px}_coll", tipo_default="Primo colloquio (anamnestico)")
    except Exception as e:
        st.caption(f"Colloqui clinici non disponibili: {e}")

    if st.button("💾 Salva anamnesi", key=f"{px}_salva", type="primary"):
        ok1, e1 = _salva(conn, paz_id, nuovo_pi, "confermata")
        ok2, e2 = _salva_sviluppo(conn, paz_id, nuovo_sv)
        if ok1 and ok2:
            st.success("Anamnesi salvata. È la stessa in tutti i moduli.")
            st.session_state.pop(f"diag_storico_{paz_id}", None)
        else:
            st.error(f"Salvataggio non riuscito: {e1 or e2}")
    else:
        cambi = any(_compilato(v) != _compilato(pi.get(k)) or (_compilato(v) and v != pi.get(k))
                    for k, v in nuovo_pi.items())
        cambi = cambi or any(_compilato(v) != _compilato(sv_salv.get(k)) or (_compilato(v) and v != sv_salv.get(k))
                             for k, v in nuovo_sv.items())
        if cambi:
            st.caption("⚠️ Ci sono modifiche non ancora salvate nell'anamnesi.")
    return nuovo_pi, nuovo_sv


# ── Profilo di rischio (modello Teitelbaum) ───────────────────────────

def calcola_rischio(pi: dict, sv: dict | None = None) -> tuple[int, list[str]]:
    pi = pi or {}
    score, flags = 0, []

    def _s(k):
        v = pi.get(k)
        return v if isinstance(v, (int, float)) and 1 <= v <= 5 else None

    if (_s("grav_stato_em") or 5) <= 2:
        score += 2; flags.append("Stress emotivo materno in gravidanza")
    if (_s("grav_coppia") or 5) <= 2:
        score += 1; flags.append("Conflittualità di coppia in gravidanza")
    if len(pi.get("grav_eventi") or []) >= 2:
        score += 1; flags.append("Più eventi stressanti in gravidanza")
    if "Pre-termine" in str(pi.get("grav_termine") or ""):
        score += 2; flags.append("Nascita pre-termine")
    a1 = _int(pi.get("parto_apgar1"))
    if a1 and a1 < 7:
        score += 2; flags.append(f"APGAR basso a 1' ({a1})")
    if pi.get("parto_pianto") in ("Tardivo", "Assente"):
        score += 1; flags.append("Pianto non immediato")
    n_comp = len(pi.get("parto_complicanze") or [])
    if pi.get("parto_cordone") not in (None, "", "Nessun problema"):
        n_comp += 1
    ore = _int(pi.get("parto_travaglio_ore"))
    if pi.get("parto_travaglio") == "Prolungato" or (ore and ore > 12):
        n_comp += 1
    if n_comp >= 2 or pi.get("parto_strumenti"):
        score += 1; flags.append("Parto complicato o strumentale")
    if pi.get("mot_gatt") == "No (saltato)":
        score += 2; flags.append("Gattonamento saltato")
    if pi.get("mot_gatt_schema") in ("Omolaterale", "Strisciamento"):
        score += 1; flags.append("Schema del gattonamento atipico")
    if pi.get("mot_atnr") == "Persistente >6 mesi":
        score += 2; flags.append("ATNR persistente")
    if pi.get("mot_simmetria") in ("Asimmetrica DX", "Asimmetrica SX"):
        score += 1; flags.append("Asimmetria posturale")
    if pi.get("mot_appoggio") == "Punta-punta":
        score += 1; flags.append("Cammino sulle punte")
    passi = _int(pi.get("mot_passi"))
    if passi and passi > 18:
        score += 1; flags.append(f"Primi passi tardivi ({passi} mesi)")
    parole = _int(pi.get("com_parole"))
    if parole and parole > 18:
        score += 1; flags.append(f"Prime parole tardive ({parole} mesi)")
    if pi.get("al_selett") == "Marcata":
        score += 1; flags.append("Selettività alimentare marcata")
    n_all = len(pi.get("all_presenti") or [])
    if n_all:
        score += n_all; flags.append(f"{n_all} segnal{'e' if n_all == 1 else 'i'} di allerta")
    return score, flags


def _profilo_rischio(pi, sv):
    score, flags = calcola_rischio(pi, sv)
    if not flags:
        return
    livello = "🟢 basso" if score <= 2 else "🟡 moderato" if score <= 5 else "🔴 elevato"
    with st.expander(f"🧮 Profilo di rischio (Teitelbaum) · {livello} · punteggio {score}", expanded=False):
        for f in flags:
            st.markdown(f"- {f}")
        st.caption("Calcolato dai campi compilati. È un indice di attenzione, non una diagnosi.")


# ── Lettura per gli altri moduli ──────────────────────────────────────

def _righe(sezioni, dati):
    out = []
    for titolo, campi in sezioni:
        righe = []
        for k, label, tipo, _o in campi:
            v = (dati or {}).get(k)
            if not _compilato(v):
                continue
            if tipo == "chk":
                righe.append(label)
            elif tipo == "multi":
                righe.append(f"{label}: {', '.join(v)}")
            elif tipo == "mesi":
                righe.append(f"{label}: {int(v)} mesi")
            elif tipo == "scala":
                righe.append(f"{label.split(' (')[0]}: {int(v)}/5")
            else:
                righe.append(f"{label}: {' '.join(str(v).split())}")
        if righe:
            out.append(titolo.split(" ", 1)[1].upper())
            out.extend("- " + r for r in righe)
    return out


def sintesi_anamnesi_unica(conn, paz_id) -> list[str]:
    """Tutta l'anamnesi in righe leggibili, solo i campi compilati."""
    if conn is None or not paz_id:
        return []
    pi = carica_prima_infanzia(conn, paz_id)
    sv = carica_anamnesi_sviluppo(conn, paz_id) or {}
    out = _righe([s for _g, sez in GRUPPI for s in sez], pi)
    out += sintesi_anamnesi_sviluppo(sv)
    out += _righe(GRUPPI_FINALI, pi)
    score, flags = calcola_rischio(pi, sv)
    if flags:
        out.append(f"PROFILO DI RISCHIO (Teitelbaum): punteggio {score}")
        out.extend("- " + f for f in flags)
    return out


def sintesi_testo(conn, paz_id) -> str:
    righe = sintesi_anamnesi_unica(conn, paz_id)
    return "\n".join(r[2:] if r.startswith("- ") else r for r in righe)


def valori_protocollo(pi: dict, sv: dict) -> dict:
    """I campi che il Protocollo di valutazione salvava a testo libero,
    ricostruiti dall'anamnesi unica: la relazione del protocollo continua a
    trovarli con lo stesso nome."""
    def unisci(sezione_titolo, dati, sezioni):
        for t, c in sezioni:
            if t == sezione_titolo:
                return "; ".join(r[2:] for r in _righe([(t, c)], dati)[1:])
        return ""
    tutte = [s for _g, sez in GRUPPI for s in sez]
    comp = pi.get("parto_complicanze") or []
    a1, a5 = _int(pi.get("parto_apgar1")), _int(pi.get("parto_apgar5"))
    parole = _int(pi.get("com_parole"))
    frasi = _int(sv.get("frasi_mesi"))
    orl = [x for x in (sv.get("respirazione") or []) if "otit" in x]
    return {
        "gravidanza": unisci("🤰 Gravidanza", pi, tutte),
        "parto_tipo": pi.get("parto_tipo") or "",
        "giro_cordone": (pi.get("parto_cordone") not in (None, "", "Nessun problema"))
                        or any("cordone" in x.lower() for x in comp),
        "peso_nascita": pi.get("parto_peso") or "",
        "apgar": f"{a1 or '_'}/{a5 or '_'}" if (a1 or a5) else "",
        "tin_ittero": pi.get("parto_segnalazioni") or [],
        "periodo_neonatale": unisci("👶 Primi tre mesi", pi, tutte),
        "tappe_motorie": unisci("🏃 Tappe motorie (età in mesi)", pi, tutte),
        "prime_parole": ", ".join(x for x in (f"parole {parole} mesi" if parole else "",
                                              f"frasi {frasi} mesi" if frasi else "") if x),
        "otiti": "; ".join(x for x in (", ".join(orl), sv.get("udito") or "") if x),
        "familiarita": ", ".join(pi.get("fam_familiarita") or []),
        "bilinguismo": " — ".join(x for x in (pi.get("fam_lingua") or "", pi.get("fam_lingua_note") or "") if x),
        "patologie_note": "; ".join(x for x in (sv.get("malattie") or "", sv.get("farmaci") or "") if x),
        "trattamenti_pregressi": "; ".join(x for x in (", ".join(pi.get("inv_trattamenti") or []),
                                                       pi.get("inv_trattamenti_note") or "") if x),
        "valutazione_visiva_pregressa": pi.get("inv_val_visiva") or sv.get("vista") or "",
        "hobby": sv.get("sport") or "",
        "sviluppo": sv,
        "prima_infanzia": pi,
    }
