# -*- coding: utf-8 -*-
"""
Modulo: Diagnostica Uditiva Funzionale
Gestionale The Organism

Questionari:
  - Fisher Auditory Problems Checklist (bambini, 25 item)
  - SCAP-A Screening (adulti, 12 item + anamnesi)

Salvataggio DB: tabella diagnostica_uditiva
"""

import json
import streamlit as st
from datetime import date, datetime

FISHER_ITEMS = [
    (1,  "Ha una storia di perdita dell'udito", None),
    (2,  "Ha una storia di infezioni dell'orecchio", None),
    (3,  "Non presta attenzione alle istruzioni il 50% o piu delle volte", "DIC"),
    (4,  "Non ascolta attentamente le indicazioni, spesso necessario ripetere", "DIC"),
    (5,  'Dice "huh" e "cosa" almeno cinque o piu volte al giorno', "DIC"),
    (6,  "Non e possibile assistere agli stimoli uditivi per piu di pochi secondi", "TFM"),
    (7,  "Ha un breve intervallo di attenzione", "TFM"),
    (8,  "Sogni ad occhi aperti, l'attenzione si sposta a volte", None),
    (9,  "E facilmente distratto dai suoni di sottofondo", "TFM"),
    (10, "Ha difficolta con la fonetica", "DIC"),
    (11, "Riscontra problemi di discriminazione acustica", "DIC"),
    (12, "Dimentica cio che viene detto in pochi minuti", "TFM"),
    (13, "Non ricorda semplici cose di routine di giorno in giorno", None),
    (14, "Problemi nel ricordare cio che e stato ascoltato la scorsa settimana/mese/anno", None),
    (15, "Difficolta a ricordare una sequenza che e stata ascoltata", "ORG"),
    (16, "Sperimenta difficolta a seguire le indicazioni uditive", "DIC"),
    (17, "Spesso fraintende cio che viene detto", "DIC"),
    (18, "Non comprende molte parole / concetti verbali per eta", "DIC"),
    (19, "Impara male attraverso il canale uditivo", None),
    (20, "Ha un problema linguistico (morfologia, sintassi, vocabolario, fonologia)", None),
    (21, "Ha un problema di articolazione (discorso)", "DIC"),
    (22, "Non e sempre possibile mettere in relazione cio che si sente con cio che si vede", "INT"),
    (23, "Manca la motivazione per imparare", None),
    (24, "Mostra una risposta lenta o ritardata agli stimoli verbali", "DIC"),
    (25, "Dimostra prestazioni inferiori alla media in una o piu aree accademiche", None),
]

FISHER_NORMS = {
    "Prescolare (5.0-5.11)":   92.0,
    "1a elementare (6.0-6.11)": 89.9,
    "2a elementare (7.0-7.11)": 87.0,
    "3a elementare (8.0-8.11)": 85.6,
    "4a elementare (9.0-9.11)": 85.9,
    "5a elementare (10.0-10.11)": 87.4,
    "1a media (11.0-11.11)":    80.0,
}

APD_CATS = {
    "DIC": {"label": "DIC — Discriminazione",     "items": [3,4,5,10,11,16,17,18,21,24]},
    "TFM": {"label": "TFM — Memoria/Figura-Terra", "items": [6,7,9,12]},
    "ORG": {"label": "ORG — Organizzazione",       "items": [15]},
    "INT": {"label": "INT — Integrazione",         "items": [22]},
}

SCAPA_ITEMS = [
    (1,  False, "Hai bisogno di ripetizioni frequenti quando ascolti una persona che parla chiaramente?",
                "La persona necessita spesso di ripetizioni mentre ascoltate?"),
    (2,  True,  "Riesci a mantenere l'attenzione su una persona che parla per piu di 10 minuti?",
                "La persona riesce a mantenere l'attenzione per piu di 10 minuti?"),
    (3,  False, "Ti risulta difficile seguire il parlato in presenza di rumore di fondo?",
                "La persona trova difficile seguire il parlato con rumore di fondo?"),
    (4,  False, "Hai difficolta a ricordare cio che e stato detto nell'ordine corretto?",
                "La persona ha difficolta a ricordare le cose nell'ordine corretto?"),
    (5,  False, "Dimentichi cio che ti e stato detto molto rapidamente (entro un minuto)?",
                "La persona dimentica molto rapidamente cio che le e stato detto?"),
    (6,  False, "Hai difficolta a capire il parlato in presenza di rumore di fondo intenso?",
                "La persona ha difficolta con il parlato in presenza di rumore intenso?"),
    (7,  True,  "Riesci a ricordare i nomi di 5 amici di scuola che non vedi da molti anni?",
                "La persona riesce a ricordare i nomi di 5 amici che non vede da oltre 30 anni?"),
    (8,  False, "Ti e stato detto che impieghi piu tempo del normale per rispondere?",
                "La persona impiega molto piu tempo (quasi il doppio) per rispondere?"),
    (9,  False, "Hai difficolta a rispondere quando due persone parlano nello stesso momento?",
                "La persona ha difficolta quando due persone parlano quasi nello stesso momento?"),
    (10, False, "Ti risulta difficile capire il parlato quando non puoi vedere il volto di chi parla?",
                "La persona ha difficolta a capire il parlato quando non vede il volto di chi parla?"),
    (11, False, "Hai difficolta a ricordare numeri (telefono, targa, codice porta)?",
                "La persona ha difficolta a ricordare cifre/numeri?"),
    (12, False, "Altri ti riferiscono che non presti attenzione quando iniziano a parlarti?",
                "La persona non presta attenzione quando le si inizia a parlare all'improvviso?"),
]

# ─────────────────────────────────────────────────────────────────────────────
# DB helpers
# ─────────────────────────────────────────────────────────────────────────────

def _is_pg(conn):
    t = type(conn).__name__
    if "Pg" in t or "pg" in t: return True
    try:
        import sys, os
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if root not in sys.path: sys.path.insert(0, root)
        from app_patched import _DB_BACKEND
        return _DB_BACKEND == "postgres"
    except Exception: pass
    return False

def _ph(n, conn):
    return ", ".join(["%s" if _is_pg(conn) else "?"] * n)

def _rg(row, key, default=None):
    try: v = row[key]; return v if v is not None else default
    except Exception:
        try: return row.get(key, default)
        except: return default

def _get_conn():
    try:
        import sys, os
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if root not in sys.path: sys.path.insert(0, root)
        from app_patched import get_connection; return get_connection()
    except Exception: pass
    import sqlite3
    c = sqlite3.connect("organism.db"); c.row_factory = sqlite3.Row; return c

def _init_db(conn):
    raw = getattr(conn, "_conn", conn)
    try: cur = raw.cursor()
    except: cur = conn.cursor()
    pg = _is_pg(conn)
    if pg:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS diagnostica_uditiva (
            id BIGSERIAL PRIMARY KEY,
            paziente_id BIGINT NOT NULL,
            tipo TEXT NOT NULL,
            data_esame TEXT,
            operatore TEXT,
            dati_json TEXT,
            punteggio REAL,
            classificazione TEXT,
            note TEXT,
            created_at TEXT
        )""")
    else:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS diagnostica_uditiva (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paziente_id INTEGER NOT NULL,
            tipo TEXT NOT NULL,
            data_esame TEXT,
            operatore TEXT,
            dati_json TEXT,
            punteggio REAL,
            classificazione TEXT,
            note TEXT,
            created_at TEXT
        )""")
    try: raw.commit()
    except: conn.commit()

def _salva(conn, paz_id, tipo, dati, punteggio, classificazione, operatore="", note=""):
    cur = conn.cursor()
    ph = _ph(9, conn)
    params = (
        paz_id, tipo, date.today().isoformat(), operatore,
        json.dumps(dati), punteggio, classificazione, note,
        datetime.now().isoformat(timespec="seconds"),
    )
    sql = (f"INSERT INTO diagnostica_uditiva "
           f"(paziente_id, tipo, data_esame, operatore, dati_json, punteggio, "
           f"classificazione, note, created_at) VALUES ({ph})")
    try:
        cur.execute(sql, params)
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Errore salvataggio: {e}")
        return False

# ─────────────────────────────────────────────────────────────────────────────
# Calcoli Fisher
# ─────────────────────────────────────────────────────────────────────────────

def _calc_fisher(checked: list, fascia: str):
    n_checked = sum(checked)
    n_unchecked = 25 - n_checked
    score = n_unchecked * 4
    mean = FISHER_NORMS.get(fascia, 86.8)
    sd = 18.2
    cutoff = 72.0
    if score >= cutoff:
        cls = "WNL"; interp = "Nella norma per fascia d'eta."
    elif score >= mean - sd:
        cls = "Sotto soglia"; interp = "Sotto il punteggio limite — approfondimento consigliato."
    elif score >= mean - 2*sd:
        cls = "1 DS sotto"; interp = "1 deviazione standard sotto la media — valutazione APD indicata."
    elif score >= mean - 3*sd:
        cls = "2 DS sotto"; interp = "2 deviazioni standard — difficolta significative."
    else:
        cls = "3 DS sotto"; interp = "3 deviazioni standard — deficit grave di elaborazione uditiva."
    apd = {}
    for cat, info in APD_CATS.items():
        apd[cat] = sum(1 for n in info["items"] if checked[n-1])
    return score, cls, interp, apd

# ─────────────────────────────────────────────────────────────────────────────
# Calcoli SCAP-A
# ─────────────────────────────────────────────────────────────────────────────

def _calc_scapa(answers: list):
    score = 0
    for i, (_, inv, _, _) in enumerate(SCAPA_ITEMS):
        v = answers[i]
        if v is None: continue
        if not inv and v == "Presente": score += 1
        elif inv and v == "Assente": score += 1
    if score <= 3:   cls, interp = "Nella norma", "Nessuna difficolta significativa."
    elif score <= 6: cls, interp = "Lieve", "Difficolta lievi-moderate — approfondimento consigliato."
    elif score <= 9: cls, interp = "Moderato", "Difficolta moderate — valutazione audiologica indicata."
    else:            cls, interp = "Significativo", "Difficolta significative — valutazione prioritaria."
    return score, cls, interp

# ─────────────────────────────────────────────────────────────────────────────
# UI principale
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_pazienti(conn):
    """Carica lista pazienti senza dipendere da app_core."""
    cur = conn.cursor()
    # Prova a scoprire il nome reale della tabella
    candidates = ['Pazienti','pazienti','Patients','patients']
    try:
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]
        for t in tables:
            if 'paz' in t.lower() or 'patient' in t.lower():
                if t not in candidates:
                    candidates.insert(0, t)
    except Exception:
        try:
            cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
            tables = [r[0] for r in cur.fetchall()]
            for t in tables:
                if 'paz' in t.lower() or 'patient' in t.lower():
                    if t not in candidates:
                        candidates.insert(0, t)
        except Exception:
            pass

    col_id = ['id']
    col_cogn = ['Cognome','cognome','LastName','last_name']
    col_nome = ['Nome','nome','FirstName','first_name']

    def get_cols(table):
        try:
            cur.execute(f'PRAGMA table_info("{table}")')
            return [r[1] for r in cur.fetchall()]
        except Exception:
            try:
                cur.execute(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema='public' AND table_name=%s", (table,))
                return [r[0] for r in cur.fetchall()]
            except Exception:
                return []

    def pick(cols, candidates):
        s = set(cols)
        for c in candidates:
            if c in s: return c
        low = {x.lower(): x for x in cols}
        for c in candidates:
            if c.lower() in low: return low[c.lower()]
        return None

    for table in candidates:
        cols = get_cols(table)
        if not cols: continue
        idc  = pick(cols, col_id)
        cc   = pick(cols, col_cogn)
        nc   = pick(cols, col_nome)
        if not (idc and cc and nc): continue
        try:
            cur.execute(f'SELECT "{idc}","{cc}","{nc}" FROM "{table}" ORDER BY "{cc}","{nc}"')
            return cur.fetchall()
        except Exception:
            continue
    return []


def ui_diagnostica_uditiva(conn=None):
    st.header("Diagnostica Uditiva Funzionale")
    st.caption("Questionario Fisher (bambini) · SCAP-A (adulti) · Primo step della valutazione uditiva")

    if conn is None:
        conn = _get_conn()
    _init_db(conn)
    cur = conn.cursor()

    try:
        rows = _fetch_pazienti(conn)
    except Exception as e:
        st.error(f"Errore caricamento pazienti: {e}"); return

    if not rows:
        st.info("Nessun paziente registrato."); return

    options = [(int(r[0]), f"{r[1]} {r[2]}") for r in rows]

    c1, c2 = st.columns([3, 1])
    with c1:
        sel = st.selectbox("Paziente", options=options,
                           format_func=lambda x: x[1], key="du_paz")
    with c2:
        op = st.text_input("Operatore", "", key="du_op")
    paz_id = sel[0]

    st.divider()

    tab_fisher, tab_scapa, tab_storico = st.tabs([
        "Fisher — Bambini", "SCAP-A — Adulti", "Storico"
    ])

    with tab_fisher:
        _ui_fisher(conn, paz_id, op)

    with tab_scapa:
        _ui_scapa(conn, paz_id, op)

    with tab_storico:
        _ui_storico(conn, cur, paz_id)

    st.divider()
    with st.expander("🔧 Calibrazione Cuffie", expanded=False):
        _ui_calibrazione_semplice()

    with st.expander("🔧 Calibrazione cuffie", expanded=False):
        _ui_calibrazione_rapida()

    with st.expander("🎵 Test Tonale Audiometrico + EQ", expanded=False):
        ui_test_tonale(conn, paz_id, op)

    with st.expander("🎧 Test Dicotico Johansen", expanded=False):
        ui_test_johansen(conn, paz_id, op)

# ─────────────────────────────────────────────────────────────────────────────
# Tab Fisher
# ─────────────────────────────────────────────────────────────────────────────

def _ui_fisher(conn, paz_id, operatore):
    st.subheader("Elenco di controllo dei problemi uditivi di Fisher")
    st.caption("25 item — Punteggio = elementi NON spuntati × 4 — Soglia approfondimento: 72%")

    c1, c2, c3 = st.columns(3)
    with c1: f_nome = st.text_input("Nome bambino", key="f_nome_i")
    with c2: f_nascita = st.date_input("Data di nascita", key="f_nasc_i", value=None)
    with c3: f_scuola = st.text_input("Scuola / Classe", key="f_scuola_i")

    c1, c2 = st.columns(2)
    with c1:
        fascia = st.selectbox("Fascia d'eta", list(FISHER_NORMS.keys()),
                              key="f_fascia_i")
    with c2:
        compilatore = st.selectbox("Chi compila", ["Genitore","Insegnante","Terapeuta"],
                                   key="f_comp_i")

    st.markdown("---")
    st.markdown("**Spunta ogni elemento che e considerato un problema dall'osservatore:**")

    checked = []
    cat_colors = {"DIC":"🟢","TFM":"🔵","ORG":"🟡","INT":"🟣"}

    for n, testo, cat in FISHER_ITEMS:
        label = f"{n}. {testo}"
        if cat:
            label += f"  `{cat}`"
        val = st.checkbox(label, key=f"fi_{n}", value=False)
        checked.append(val)

    st.markdown("---")
    score, cls, interp, apd = _calc_fisher(checked, fascia)
    n_checked = sum(checked)

    col1, col2, col3 = st.columns(3)
    col1.metric("Punteggio", f"{score}%")
    col2.metric("Item spuntati", f"{n_checked}/25")
    col3.metric("Classificazione", cls)

    mean = FISHER_NORMS[fascia]
    progress = min(score / 100.0, 1.0)
    st.progress(progress)
    st.caption(f"Media gruppo {fascia}: {mean}% | Soglia: 72% | SD: 18.2")

    color = "green" if score >= 72 else "orange" if score >= 50 else "red"
    st.markdown(f"<p style='color:{color};font-weight:500'>{interp}</p>",
                unsafe_allow_html=True)

    st.markdown("**Profilo APD (classificazione Katz):**")
    apc1, apc2, apc3, apc4 = st.columns(4)
    for col, (cat, info) in zip([apc1,apc2,apc3,apc4], APD_CATS.items()):
        col.metric(info["label"], f"{apd[cat]}/{len(info['items'])}")

    nota = st.text_area("Note Fisher", key="f_note_i", height=80)

    if st.button("Salva Fisher", type="primary", key="f_save"):
        dati = {
            "nome": f_nome,
            "nascita": str(f_nascita) if f_nascita else "",
            "scuola": f_scuola,
            "fascia": fascia,
            "compilatore": compilatore,
            "checked": checked,
            "apd": apd,
        }
        if _salva(conn, paz_id, "Fisher", dati, score, cls, operatore, nota):
            st.success(f"Fisher salvato — Punteggio: {score}% ({cls})")

# ─────────────────────────────────────────────────────────────────────────────
# Tab SCAP-A
# ─────────────────────────────────────────────────────────────────────────────

def _ui_scapa(conn, paz_id, operatore):
    st.subheader("SCAP-A — Screening funzionamento uditivo adulto")
    st.caption("12 domande Presente/Assente. Q2 e Q7 hanno scoring invertito.")

    chi = st.radio("Chi compila?", ["Autovalutazione", "Familiare / Caregiver"],
                   horizontal=True, key="a_chi")
    is_fam = (chi == "Familiare / Caregiver")

    c1, c2 = st.columns(2)
    with c1: a_nome = st.text_input("Nome (facoltativo)", key="a_nome_i")
    with c2: a_eta = st.number_input("Eta (facoltativa)", 0, 120, 0,
                                     key="a_eta_i", format="%d")

    with st.expander("Anamnesi clinica", expanded=True):
        ac1, ac2 = st.columns(2)
        with ac1:
            audiom = st.radio("Controllo audiometrico ultimi 24 mesi",
                              ["Si","No","Non so"], index=1, key="a_audiom",
                              horizontal=True)
            acufeni = st.radio("Acufeni (fischi/ronzii)",
                               ["Si","No","Occasionali"], index=1, key="a_acuf",
                               horizontal=True)
            iperacusia = st.radio("Iperacusia / fastidio suoni comuni",
                                  ["Si","No","Occasionale"], index=1, key="a_iper",
                                  horizontal=True)
        with ac2:
            vertigini = st.radio("Vertigini / instabilita",
                                 ["Si","No","Occasionali"], index=1, key="a_vert",
                                 horizontal=True)
            protesi = st.radio("Protesi / impianto cocleare",
                               ["No","Protesi acustiche","Impianto cocleare"], index=0,
                               key="a_prot", horizontal=True)
            rumore = st.radio("Esposizione a rumore",
                              ["Regolare","Occasionale","No"], index=2, key="a_rum",
                              horizontal=True)

        st.markdown("**Anamnesi** (seleziona tutto ciò che si applica)")
        an1, an2 = st.columns(2)
        with an1:
            an_otiti = st.checkbox("Otiti ricorrenti", key="an_ot")
            an_chir = st.checkbox("Interventi chirurgici ORL", key="an_ch")
        with an2:
            an_trauma = st.checkbox("Trauma cranico / colpo di frusta", key="an_tr")
            an_sinusiti = st.checkbox("Infezioni ORL ricorrenti", key="an_si")

    st.markdown("---")
    st.markdown("**Checklist — 12 domande:**")
    answers = []
    opts_pres = ["Presente", "Assente"]

    for n, inv, q_auto, q_fam in SCAPA_ITEMS:
        domanda = q_fam if is_fam else q_auto
        label = f"**Q{n}.** {domanda}"
        if inv:
            label += "  *(scoring invertito)*"
        val = st.radio(label, opts_pres, index=None,
                       key=f"sq_{n}", horizontal=True)
        answers.append(val)

    st.markdown("---")
    answered = sum(1 for v in answers if v is not None)
    score, cls, interp = _calc_scapa(answers)

    col1, col2, col3 = st.columns(3)
    col1.metric("Punteggio", f"{score}/12" + ("*" if answered < 12 else ""))
    col2.metric("% difficolta", f"{round(score/12*100)}%" if answered == 12 else "—")
    col3.metric("Livello", cls)

    if answered < 12:
        st.caption(f"Risposte mancanti: {12-answered} — completare per il punteggio finale")
    else:
        color = "green" if score<=3 else "orange" if score<=6 else "red"
        st.markdown(f"<p style='color:{color};font-weight:500'>{interp}</p>",
                    unsafe_allow_html=True)

    nota = st.text_area("Note SCAP-A", key="a_note_i", height=80)

    if st.button("Salva SCAP-A", type="primary", key="a_save"):
        dati = {
            "chi": chi,
            "nome": a_nome,
            "eta": int(a_eta) if a_eta else None,
            "anamnesi": {
                "audiometrico": audiom,
                "acufeni": acufeni,
                "iperacusia": iperacusia,
                "vertigini": vertigini,
                "protesi": protesi,
                "rumore": rumore,
                "otiti": an_otiti,
                "chirurgia": an_chir,
                "trauma": an_trauma,
                "sinusiti": an_sinusiti,
            },
            "risposte": answers,
        }
        if _salva(conn, paz_id, "SCAP-A", dati, score, cls, operatore, nota):
            st.success(f"SCAP-A salvato — Punteggio: {score}/12 ({cls})")

# ─────────────────────────────────────────────────────────────────────────────
# Storico
# ─────────────────────────────────────────────────────────────────────────────

def _ui_storico(conn, cur, paz_id):
    ph1 = _ph(1, conn)
    try:
        cur.execute(
            "SELECT * FROM diagnostica_uditiva WHERE paziente_id = " + ph1 +
            " ORDER BY data_esame DESC, id DESC LIMIT 30", (paz_id,))
        rows = cur.fetchall()
    except Exception as e:
        st.error(f"Errore storico: {e}"); return

    if not rows:
        st.info("Nessun questionario registrato per questo paziente."); return

    for r in rows:
        eid   = _rg(r, "id")
        tipo  = _rg(r, "tipo", "")
        data  = _rg(r, "data_esame", "")
        score = _rg(r, "punteggio")
        cls   = _rg(r, "classificazione", "")
        note  = _rg(r, "note", "")

        with st.expander(f"#{eid} | {tipo} | {data} | {cls}"):
            c1, c2 = st.columns(2)
            c1.metric("Punteggio", f"{score}" + ("%" if tipo=="Fisher" else "/12"))
            c2.metric("Classificazione", cls)
            if note:
                st.caption(f"Note: {note}")
            try:
                dati = json.loads(_rg(r, "dati_json", "{}") or "{}")
                if tipo == "Fisher" and "apd" in dati:
                    st.markdown("**Profilo APD:**")
                    cols = st.columns(4)
                    for col, (cat, info) in zip(cols, APD_CATS.items()):
                        v = dati["apd"].get(cat, 0)
                        col.metric(cat, f"{v}/{len(info['items'])}")
            except Exception:
                pass


# ─────────────────────────────────────────────────────────────────────────────
# TEST TONALE AUDIOMETRICO
# ─────────────────────────────────────────────────────────────────────────────

import io, wave, math
import numpy as np

FREQS_TON    = [125, 250, 500, 750, 1000, 1500, 2000, 3000, 4000, 6000, 8000]
FLABELS_TON  = ['125','250','500','750','1k','1.5k','2k','3k','4k','6k','8k']
FREQ_ORDER   = [8000, 6000, 4000, 3000, 2000, 1500, 1000, 750, 500, 250, 125]
TOMATIS_STD  = [-5, -8, -10, -12, -14, -15, -14, -15, -12, -8, -5]


def _genera_tono_wav(freq_hz: int, db_hl: float, orecchio: str,
                     secondi: float = 2.5, sr: int = 44100) -> bytes:
    """Genera tono WAV stereo: OD = canale destro, OS = sinistro."""
    dbfs = db_hl - 90.0
    amp  = 10 ** (dbfs / 20.0)
    amp  = max(0.001, min(0.95, amp))
    t    = np.linspace(0, secondi, int(sr * secondi), endpoint=False)
    sig  = amp * np.sin(2 * math.pi * freq_hz * t)
    fade = int(sr * 0.02)
    if len(sig) > 2 * fade:
        sig[:fade]  *= np.linspace(0, 1, fade)
        sig[-fade:] *= np.linspace(1, 0, fade)
    # Stereo: OD = R, OS = L
    if orecchio == "OD":
        L = np.zeros_like(sig)
        R = sig
    elif orecchio == "OS":
        L = sig
        R = np.zeros_like(sig)
    else:  # Binaurale
        L = sig
        R = sig
    stereo = np.stack([L, R], axis=1)
    pcm = np.int16(np.clip(stereo, -1, 1) * 32767)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())
    return buf.getvalue()


def _calc_eq_tomatis(soglie_od, soglie_os, tomatis):
    """Calcola delta EQ = Tomatis - soglia paziente per ogni frequenza."""
    eq_od = [round(tomatis[i] - soglie_od[i], 1)
             if soglie_od[i] is not None else None
             for i in range(len(FREQS_TON))]
    eq_os = [round(tomatis[i] - soglie_os[i], 1)
             if soglie_os[i] is not None else None
             for i in range(len(FREQS_TON))]
    return eq_od, eq_os



# ─────────────────────────────────────────────────────────────────────────────
# CALIBRAZIONE CUFFIE (wizard semplificato con fonometro)
# ─────────────────────────────────────────────────────────────────────────────

def _ui_calibrazione_semplice():
    """Wizard calibrazione cuffie con toni di riferimento e fonometro."""

    st.subheader("Calibrazione cuffie")
    st.caption(
        "Genera toni di riferimento a livello noto · "
        "Misura con fonometro (app smartphone o fonometro fisico) · "
        "Salva il profilo di calibrazione"
    )

    CALIB_FREQS = [125, 250, 500, 1000, 2000, 4000, 8000]
    CALIB_LABELS = ['125','250','500','1k','2k','4k','8k']

    st.markdown("**Step 1 — Setup**")
    cc1, cc2 = st.columns(2)
    with cc1:
        device = st.text_input("Nome device/PC", "PC Studio", key="cal_device")
        marca  = st.text_input("Marca cuffie", key="cal_marca")
    with cc2:
        modello = st.text_input("Modello cuffie", key="cal_modello")
        st.markdown(
            "<div style='font-size:12px;color:var(--color-text-secondary);"
            "padding-top:8px'>App fonometro consigliate:<br>"
            "iOS: Decibel X, NIOSH SLM<br>"
            "Android: Sound Meter, DecibelMeter Pro</div>",
            unsafe_allow_html=True)

    st.divider()
    st.markdown("**Step 2 — Genera tono di riferimento**")
    st.caption("Posiziona il microfono al centro del padiglione, premi il tono, leggi il valore sul fonometro.")

    cc3, cc4, cc5 = st.columns(3)
    with cc3:
        cal_freq = st.selectbox("Frequenza", CALIB_FREQS,
                                format_func=lambda f: str(f) if f<1000 else f"{f//1000}k",
                                key="diag_cal_freq_v3")
    with cc4:
        cal_db = st.slider("Livello dB HL", 0, 80, 60, 5, key="cal_db")
    with cc5:
        cal_ear = st.radio("Orecchio", ["OD","OS"], horizontal=True, key="diag_cal_ear_v3")

    if st.button("▶ Genera tono calibrazione", type="primary", key="diag_cal_play_v3",
                 use_container_width=True):
        wav = _genera_tono_wav(int(cal_freq), float(cal_db), cal_ear, 3.0)
        st.audio(wav, format="audio/wav")
        st.caption(f"Tono {cal_freq} Hz a {cal_db} dB HL · {cal_ear}")

    st.divider()
    st.markdown("**Step 3 — Registra misura fonometro**")

    if "cal_misure" not in st.session_state:
        st.session_state.cal_misure = {}

    cm1, cm2, cm3 = st.columns([2,2,1])
    with cm1:
        cal_freq2 = st.selectbox("Frequenza misurata", CALIB_FREQS,
                                 format_func=lambda f: str(f) if f<1000 else f"{f//1000}k",
                                 key="cal_freq2")
    with cm2:
        cal_spl = st.number_input("dB(A) letto sul fonometro",
                                  30.0, 120.0, 75.0, 0.5, key="cal_spl")
    with cm3:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        if st.button("Registra", key="cal_reg", use_container_width=True):
            st.session_state.cal_misure[cal_freq2] = float(cal_spl)
            st.success(f"Registrato: {cal_freq2} Hz = {cal_spl} dB(A)")

    # Mostra misure registrate
    if st.session_state.cal_misure:
        st.markdown("**Misure registrate:**")
        ref_dbhl = 60.0
        cols = st.columns(len(st.session_state.cal_misure))
        for col, (f, spl) in zip(cols, sorted(st.session_state.cal_misure.items())):
            offset = round(spl - ref_dbhl, 1)
            color = "green" if abs(offset) < 3 else "orange" if abs(offset) < 6 else "red"
            col.markdown(
                f"<div style='text-align:center'>"
                f"<b style='color:{color}'>{offset:+.1f} dB</b>"
                f"<br><span style='font-size:11px'>{f if f<1000 else str(f//1000)+'k'} Hz</span>"
                f"<br><span style='font-size:10px;color:#888'>{spl} dB(A)</span>"
                f"</div>",
                unsafe_allow_html=True)
        st.caption(f"Offset = dB(A) misurato − {ref_dbhl} dB HL di riferimento")

    st.divider()
    nota_cal = st.text_input("Note calibrazione", key="cal_note")
    if st.button("Salva profilo calibrazione", type="primary", key="diag_cal_save_v3"):
        st.success(f"Profilo salvato: {marca} {modello} su {device} — "
                   f"{len(st.session_state.cal_misure)} frequenze misurate")


# ─────────────────────────────────────────────────────────────────────────────
# CALIBRAZIONE CUFFIE (wizard rapido con fonometro)
# ─────────────────────────────────────────────────────────────────────────────

import io as _io_calib
import wave as _wave_calib
import math as _math_calib

def _tone_calib(freq_hz, dbfs=-20.0, seconds=2.0, sr=44100):
    """Genera tono di calibrazione WAV."""
    amp = 10**(dbfs/20.0)
    amp = max(0.001, min(0.95, amp))
    t = np.linspace(0, seconds, int(sr*seconds), endpoint=False)
    sig = amp * np.sin(2*_math_calib.pi*freq_hz*t)
    fade = int(sr*0.02)
    if len(sig) > 2*fade:
        sig[:fade] *= np.linspace(0,1,fade)
        sig[-fade:] *= np.linspace(1,0,fade)
    pcm = np.int16(np.clip(sig,-1,1)*32767)
    buf = _io_calib.BytesIO()
    with _wave_calib.open(buf,"wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2)
        wf.setframerate(sr); wf.writeframes(pcm.tobytes())
    return buf.getvalue()


def _ui_calibrazione_rapida():
    """Wizard calibrazione cuffie con fonometro."""
    st.markdown("**Wizard calibrazione cuffie**")
    st.caption(
        "Posiziona il microfono al centro del padiglione. "
        "Invia il tono di riferimento, leggi il valore sul fonometro "
        "(o app: Decibel X, NIOSH SLM) e inserisci il valore misurato."
    )

    CALIB_FREQS = [1000, 2000, 4000, 500, 250]
    CALIB_LABELS = ["1 kHz","2 kHz","4 kHz","500 Hz","250 Hz"]

    col1, col2, col3 = st.columns(3)
    with col1:
        calib_freq = st.selectbox("Frequenza di calibrazione",
                                  CALIB_FREQS,
                                  format_func=lambda f: f"{f} Hz" if f<1000 else f"{f//1000} kHz",
                                  key="diag_cal_freq_v3")
    with col2:
        calib_ear = st.radio("Orecchio", ["OD","OS","Entrambi"],
                             horizontal=True, key="diag_cal_ear_v3")
    with col3:
        calib_dur = st.radio("Durata", ["1s","2s","3s"],
                             horizontal=True, key="diag_cal_dur_v3",
                             index=1)
        dur_sec = int(calib_dur[0])

    # Genera tono di riferimento a -20 dBFS
    if st.button("▶ Invia tono di riferimento (-20 dBFS)",
                 type="primary", key="diag_cal_play_v3", use_container_width=True):
        ear_map = {"OD":"OD","OS":"OS","Entrambi":"OD"}
        wav = _genera_tono_wav(calib_freq, 70.0,
                               ear_map[calib_ear], float(dur_sec))
        st.audio(wav, format="audio/wav")

    st.divider()
    st.markdown("**Inserisci il valore letto sul fonometro:**")

    c1, c2 = st.columns(2)
    with c1:
        spl_od = st.number_input("dB(A) misurato OD",
                                  min_value=30, max_value=120,
                                  value=75, step=1, key="diag_cal_spl_od_v3")
    with c2:
        spl_os = st.number_input("dB(A) misurato OS",
                                  min_value=30, max_value=120,
                                  value=75, step=1, key="diag_cal_spl_os_v3")

    offset_od = spl_od - 70
    offset_os = spl_os - 70
    st.info(
        f"Offset calibrazione → OD: {offset_od:+d} dB · OS: {offset_os:+d} dB  "
        f"(verranno applicati automaticamente al test tonale)"
    )

    if st.button("Salva calibrazione", key="diag_cal_save_v3"):
        st.session_state["cal_offset_od"] = offset_od
        st.session_state["cal_offset_os"] = offset_os
        st.success(
            f"Calibrazione salvata — OD: {offset_od:+d} dB · OS: {offset_os:+d} dB")

    # Procedura posizionamento
    with st.expander("Come posizionare il microfono", expanded=False):
        st.markdown("""
**Procedura:**
1. Collega le cuffie al PC con volume al massimo e EQ sistema disattivato
2. Posiziona il microfono dello smartphone esattamente **al centro del padiglione**
3. Premi leggermente il padiglione sul microfono per isolare i rumori esterni
4. Invia il tono di riferimento e leggi il valore sull'app fonometro
5. Ripeti per OD e OS separatamente

**App consigliate:** Decibel X (iOS) · NIOSH SLM (iOS) · Sound Meter (Android)
        """)


def ui_test_tonale(conn, paz_id, operatore=""):
    st.subheader("Test tonale audiometrico")
    st.caption("Via aerea e ossea · Metodo Hipérion · Curva Tomatis")

    # ── Shortcut tastiera via JavaScript ─────────────────────────────────
    import streamlit.components.v1 as _components
    _components.html("""
    <script>
    const doc = window.parent.document;
    doc.addEventListener('keydown', function(e) {
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
        if (e.code === 'Space') {
            e.preventDefault();
            const btns = doc.querySelectorAll('button');
            for (const b of btns) {
                if (b.innerText.includes('Invia tono')) { b.click(); break; }
            }
        }
        if (e.code === 'ArrowUp') {
            e.preventDefault();
            const btns = doc.querySelectorAll('button');
            for (const b of btns) {
                if (b.innerText.trim() === '+5') { b.click(); break; }
            }
        }
        if (e.code === 'ArrowDown') {
            e.preventDefault();
            const btns = doc.querySelectorAll('button');
            for (const b of btns) {
                if (b.innerText.trim() === '-5') { b.click(); break; }
            }
        }
        if (e.code === 'KeyR') {
            const btns = doc.querySelectorAll('button');
            for (const b of btns) {
                if (b.innerText.includes('Risponde') && !b.innerText.includes('Non')) { b.click(); break; }
            }
        }
        if (e.code === 'KeyN') {
            const btns = doc.querySelectorAll('button');
            for (const b of btns) {
                if (b.innerText.includes('Non risponde')) { b.click(); break; }
            }
        }
        if (e.code === 'KeyV') {
            const btns = doc.querySelectorAll('button');
            for (const b of btns) {
                if (b.innerText.includes('Valida')) { b.click(); break; }
            }
        }
    });
    </script>
    <div style="font-size:11px;color:#888;padding:4px 0">
      <b>Shortcut:</b> Spazio = invia tono &nbsp;|&nbsp;
      ↑↓ = ±5 dB &nbsp;|&nbsp;
      R = risponde &nbsp;|&nbsp; N = non risponde &nbsp;|&nbsp; V = valida
    </div>
    """, height=30)

    # ── Controlli ────────────────────────────────────────────────────────
    col1, col2, col3 = st.columns(3)
    with col1:
        ear = st.selectbox("Orecchio", ["OD - Destro","OS - Sinistro"], key="tt_ear")
        ear_code = "OD" if "OD" in ear else "OS"
    with col2:
        via = st.selectbox("Via", ["AC - Aerea","BC - Ossea"], key="tt_via")
        via_code = "ac" if "AC" in via else "bc"
    with col3:
        cur_f = st.selectbox("Frequenza Hz", FREQS_TON,
                             format_func=lambda f: str(f) if f<1000 else f"{f//1000}k",
                             key="tt_freq")

    # Durata fissa — scelta una volta sola
    dur_opt = st.select_slider(
        "Durata tono (fissa per tutta la sessione)",
        options=["0.5s","1.0s","1.5s","2.0s","2.5s","3.0s"],
        value="2.0s", key="tt_dur_fixed")
    dur = float(dur_opt.replace("s",""))

    # Livello dB
    cur_db = st.slider("Livello dB HL", -20, 90, 30, 5, key="tt_db")

    # ── Invia tono ───────────────────────────────────────────────────────
    c_play, c_m5, c_p5, c_m1, c_p1 = st.columns([3,1,1,1,1])
    with c_play:
        if st.button("▶  Invia tono  [SPAZIO]", type="primary",
                     key="tt_play", use_container_width=True):
            wav = _genera_tono_wav(int(cur_f), float(cur_db), ear_code, dur)
            st.audio(wav, format="audio/wav")
    with c_m5:
        st.button("-5  [↓]", key="tt_m5", use_container_width=True)
    with c_p5:
        st.button("+5  [↑]", key="tt_p5", use_container_width=True)
    with c_m1:
        st.button("-1", key="tt_m1", use_container_width=True)
    with c_p1:
        st.button("+1", key="tt_p1", use_container_width=True)

    # ── PAD risposta + keyboard shortcuts ───────────────────────────────
    st.divider()
    st.markdown("**Risposta paziente**")
    st.caption("⌨️ SPAZIO = invia tono · ↑ = +5dB · ↓ = -5dB · R = risponde · N = non risponde")

    # JS per keyboard shortcuts
    import streamlit.components.v1 as _stc_kbd
    _stc_kbd.html("""
<script>
(function(){
  if(window._kbdBound) return;
  window._kbdBound = true;
  document.addEventListener('keydown', function(e){
    const tag = document.activeElement ? document.activeElement.tagName : '';
    if(tag==='INPUT'||tag==='TEXTAREA'||tag==='SELECT') return;
    if(e.code==='Space'){
      e.preventDefault();
      // Clicca il pulsante Invia tono
      const btns = window.parent.document.querySelectorAll('button');
      btns.forEach(b=>{ if(b.textContent.includes('Invia tono')) b.click(); });
    }
    if(e.code==='ArrowUp'){
      e.preventDefault();
      const btns = window.parent.document.querySelectorAll('button');
      btns.forEach(b=>{ if(b.textContent.trim()==='+5') b.click(); });
    }
    if(e.code==='ArrowDown'){
      e.preventDefault();
      const btns = window.parent.document.querySelectorAll('button');
      btns.forEach(b=>{ if(b.textContent.trim()==='-5') b.click(); });
    }
    if(e.key==='r'||e.key==='R'){
      const btns = window.parent.document.querySelectorAll('button');
      btns.forEach(b=>{ if(b.textContent.includes('RISPONDE') && !b.textContent.includes('NON')) b.click(); });
    }
    if(e.key==='n'||e.key==='N'){
      const btns = window.parent.document.querySelectorAll('button');
      btns.forEach(b=>{ if(b.textContent.includes('NON RISPONDE')) b.click(); });
    }
    if(e.key==='v'||e.key==='V'){
      const btns = window.parent.document.querySelectorAll('button');
      btns.forEach(b=>{ if(b.textContent.includes('VALIDA')) b.click(); });
    }
  });
})();
</script>
""", height=0, key="ton_kbd_js")

    # Pad grande touch-friendly
    pad_css = """
    <style>
    div[data-testid="column"] button {
        height: 70px !important;
        font-size: 16px !important;
        font-weight: 600 !important;
        border-radius: 12px !important;
    }
    </style>
    """
    st.markdown(pad_css, unsafe_allow_html=True)

    p1, p2, p3 = st.columns(3)
    with p1:
        risp = st.button("✓  RISPONDE  [R]",
                         key="tt_si", use_container_width=True)
    with p2:
        no_risp = st.button("✗  NON RISPONDE  [N]",
                            key="tt_no", use_container_width=True)
    with p3:
        valida = st.button("✅  VALIDA SOGLIA  [V]",
                           key="tt_val", type="primary",
                           use_container_width=True)

    # Feedback risposta
    if risp:
        new_db = -20 if int(cur_db)==30 else max(-20, int(cur_db)-5)
        st.session_state["tt_last_resp"] = int(cur_db)
        st.info(f"✓ Risponde a {cur_db} dB → nuovo livello suggerito: {new_db} dB")
    if no_risp:
        new_db = min(90, int(cur_db)+5)
        st.warning(f"✗ Non risponde a {cur_db} dB → nuovo livello suggerito: {new_db} dB")
    if valida:
        last = st.session_state.get("tt_last_resp", int(cur_db))
        key_s = f"tt_soglie_{ear_code}_{via_code}"
        if key_s not in st.session_state:
            st.session_state[key_s] = {}
        fidx = FREQS_TON.index(int(cur_f))
        st.session_state[key_s][fidx] = last
        st.session_state["tt_last_resp"] = None
        st.success(f"✅ Soglia validata: {cur_f} Hz {ear_code} {via_code.upper()} = {last} dB HL")

    last_resp = st.session_state.get("tt_last_resp")
    if last_resp is not None:
        st.info(f"Ultima risposta registrata: **{last_resp} dB HL** — premi Valida per confermare")

    # ── Soglie registrate ─────────────────────────────────────────────────
    st.divider()
    st.markdown("**Soglie registrate**")
    sc1,sc2,sc3,sc4 = st.columns(4)
    for col, (ek,vk,label,color) in zip([sc1,sc2,sc3,sc4],[
        ("OD","ac","OD AC","#c0392b"),("OS","ac","OS AC","#2980b9"),
        ("OD","bc","OD BC","#8e44ad"),("OS","bc","OS BC","#16a085"),
    ]):
        col.markdown(f"<b style='color:{color};font-size:11px'>{label}</b>",
                     unsafe_allow_html=True)
        soglie = st.session_state.get(f"tt_soglie_{ek}_{vk}", {})
        for fi,v in sorted(soglie.items()):
            col.markdown(
                f"<span style='border:1px solid {color};border-radius:6px;"
                f"padding:2px 5px;font-size:11px;color:{color};"
                f"display:inline-block;margin:1px'>{FLABELS_TON[fi]}:{v}</span>",
                unsafe_allow_html=True)

    # ── Curva Tomatis ────────────────────────────────────────────────────
    st.divider()
    st.markdown("**Curva Tomatis** (modifica valori target per questo paziente)")
    if "diag_ton_tomatis_v2" not in st.session_state:
        st.session_state["diag_ton_tomatis_v2"] = list(TOMATIS_STD)
    tc = st.columns(11)
    for i, lbl in enumerate(FLABELS_TON):
        v = tc[i].number_input(lbl, min_value=-30, max_value=10,
                               value=int(st.session_state["diag_ton_tomatis_v2"][i]),
                               step=1, key=f"diag_ton_tm{i}_v2")
        st.session_state["diag_ton_tomatis_v2"][i] = int(v)
    if st.button("Ripristina standard", key="diag_ton_tm_rst_v2"):
        st.session_state["diag_ton_tomatis_v2"] = list(TOMATIS_STD)

    # ── Grafico + EQ ─────────────────────────────────────────────────────
    od_ac = [st.session_state.get("tt_soglie_OD_ac",{}).get(i) for i in range(11)]
    os_ac = [st.session_state.get("tt_soglie_OS_ac",{}).get(i) for i in range(11)]
    tom   = st.session_state.get("diag_ton_tomatis_v2", list(TOMATIS_STD))

    if any(v is not None for v in od_ac+os_ac):
        st.divider()
        _mostra_audiogramma(od_ac, os_ac, tom)
        eq_od, eq_os = _calc_eq_tomatis(od_ac, os_ac, tom)
        st.markdown("**Delta EQ terapeutico** (Tomatis − soglia paziente)")
        ec = st.columns(11)
        for i,(lbl,vod,vos) in enumerate(zip(FLABELS_TON,eq_od,eq_os)):
            v = vod if vod is not None else vos
            if v is not None:
                cc = "green" if v>3 else "red" if v<-3 else "orange"
                ec[i].markdown(
                    f"<div style='text-align:center'>"
                    f"<b style='color:{cc}'>{v:+.0f}</b>"
                    f"<br><small style='color:#888'>{lbl}</small></div>",
                    unsafe_allow_html=True)

    # ── Salvataggio ───────────────────────────────────────────────────────
    st.divider()
    nota_ton = st.text_input("Note audiogramma", key="diag_ton_note_v2")
    if st.button("Salva audiogramma", type="primary", key="diag_ton_save_v2"):
        od_bc = [st.session_state.get("tt_soglie_OD_bc",{}).get(i) for i in range(11)]
        os_bc = [st.session_state.get("tt_soglie_OS_bc",{}).get(i) for i in range(11)]
        eq_od, eq_os = _calc_eq_tomatis(od_ac, os_ac, tom)
        n = sum(1 for v in od_ac+os_ac if v is not None)
        dati = {"od_ac":od_ac,"os_ac":os_ac,"od_bc":od_bc,"os_bc":os_bc,
                "tomatis":tom,"eq_od":eq_od,"eq_os":eq_os}
        if _salva(conn, paz_id, "Audiogramma", dati, float(n),
                  f"{n} soglie", operatore, nota_ton):
            st.success(f"Salvato — {n} soglie.")


def _mostra_audiogramma(od, os_, tom):
    """Disegna audiogramma con matplotlib."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(9, 4), facecolor="white")
        ax.set_facecolor("white")
        ax.set_ylim(90, -20)
        ax.set_xlim(-0.5, 10.5)
        ax.set_xticks(range(11))
        ax.set_xticklabels(FLABELS_TON, fontsize=8)
        ax.set_yticks(range(-20, 91, 10))
        ax.set_ylabel("dB HL", fontsize=9)
        ax.axhline(0, color="gray", lw=0.8, ls="--", alpha=0.5)
        ax.grid(True, alpha=0.15, lw=0.5)
        ax.fill_between(range(11), -20, 0, alpha=0.04, color="#2d7d6f")
        ax.text(0.01, 0.02, "Iperudizione", transform=ax.transAxes,
                fontsize=7, color="#2d7d6f", alpha=0.7)

        # Tomatis
        ax.plot(range(len(tom)), tom, color="#2d7d6f", lw=2,
                ls="--", label="Tomatis (target)", zorder=3)

        # OD AC
        pts_od = [(i, v) for i, v in enumerate(od) if v is not None]
        if pts_od:
            xi, yi = zip(*pts_od)
            ax.plot(xi, yi, color="#c0392b", lw=1.8,
                    marker="o", ms=6, label="OD AC", zorder=4)
            for x, y in pts_od:
                ax.text(x, y-4, "O", ha="center", fontsize=9,
                        color="#c0392b", fontweight="bold")

        # OS AC
        pts_os = [(i, v) for i, v in enumerate(os_) if v is not None]
        if pts_os:
            xi, yi = zip(*pts_os)
            ax.plot(xi, yi, color="#2980b9", lw=1.8,
                    marker="x", ms=6, label="OS AC", zorder=4)
            for x, y in pts_os:
                ax.text(x, y+5, "X", ha="center", fontsize=9,
                        color="#2980b9", fontweight="bold")

        ax.legend(fontsize=8, loc="lower right")
        fig.tight_layout(pad=0.5)
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=110, bbox_inches="tight",
                    facecolor="white")
        plt.close(fig)
        buf.seek(0)
        st.image(buf, use_container_width=True)
    except Exception as e:
        st.warning(f"Grafico non disponibile: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# TEST DICOTICO JOHANSEN
# ─────────────────────────────────────────────────────────────────────────────

JOHANSEN_COPPIE = [
    {"od":"DAT","os":"SOT"},{"od":"MYL","os":"GIF"},{"od":"NIK","os":"VEF"},
    {"od":"GIF","os":"KIT"},{"od":"FAK","os":"BAT"},{"od":"NUR","os":"NIK"},
    {"od":"SOT","os":"VYF"},{"od":"GEP","os":"RIS"},{"od":"VYF","os":"MYL"},
    {"od":"POS","os":"LIR"},{"od":"BOT","os":"TIK"},{"od":"VEF","os":"FAK"},
    {"od":"KIR","os":"DAT"},{"od":"KIT","os":"NUR"},{"od":"TIK","os":"BOT"},
    {"od":"LYM","os":"LYM"},{"od":"TOS","os":"HUT"},{"od":"BAT","os":"GEP"},
    {"od":"RIS","os":"POS"},{"od":"HUT","os":"TOS"},
]

JOHANSEN_TRACCE = [
    {"n":1,"desc":"Istruzioni","dur":"~10s"},
    {"n":2,"desc":"Compito 1 — risposta OD","dur":"~69s"},
    {"n":3,"desc":"Compito 2 — risposta OS","dur":"~73s"},
    {"n":4,"desc":"Compito 3 — risposte DX","dur":"~75s"},
    {"n":5,"desc":"Compito 4 — risposte SX","dur":"~73s"},
    {"n":6,"desc":"Compito 5 — entrambi","dur":"~100s"},
]


def _load_johansen_track(n: int):
    """Carica traccia Johansen da assets/johansen/ nel repo."""
    import pathlib
    # Cerca nella cartella assets/johansen relativa al modulo
    base = pathlib.Path(__file__).parent.parent / "assets" / "johansen"
    path = base / f"traccia_{n:02d}.mp3"
    if path.exists():
        return path.read_bytes(), "audio/mp3"
    return None, None


def ui_test_johansen(conn, paz_id, operatore=""):
    """Test dicotico di Johansen con tracce audio incorporate."""

    st.subheader("Test dicotico di Johansen")
    st.caption(
        "20 coppie sillabe OD/OS simultanee · 5 compiti · "
        "Calcolo automatico indice di lateralità"
    )

    # ── Tracce audio ──────────────────────────────────────────────────────
    st.markdown("**Riproduci le tracce in ordine:**")
    for info in JOHANSEN_TRACCE:
        n = info["n"]
        data, mime = _load_johansen_track(n)
        c1, c2 = st.columns([3, 2])
        with c1:
            st.markdown(
                f"**Traccia {n}** — {info['desc']} ({info['dur']})")
        with c2:
            if data:
                st.audio(data, format=mime)
            else:
                st.warning(f"File non trovato: traccia_{n:02d}.mp3")

    st.divider()

    # ── Tabella risposte ──────────────────────────────────────────────────
    st.markdown("**Registra le risposte del paziente**")
    st.caption("Comp.3 = risposta DX · Comp.4 = risposta SX · Comp.5 = entrambi")

    if "joh_risposte" not in st.session_state:
        st.session_state.joh_risposte = {}

    opts = ["", "OD", "OS", "Entrambi"]

    # Header
    h = st.columns([0.4, 0.7, 0.7, 1.2, 1.2, 1.2])
    for lbl, col in zip(["#","OD","OS","Comp.3 DX","Comp.4 SX","Comp.5 Both"], h):
        col.markdown(f"<div style='font-size:11px;font-weight:600;"
                     f"color:var(--color-text-secondary)'>{lbl}</div>",
                     unsafe_allow_html=True)

    for i, coppia in enumerate(JOHANSEN_COPPIE):
        c0,c1,c2,c3,c4,c5 = st.columns([0.4,0.7,0.7,1.2,1.2,1.2])
        c0.markdown(f"<div style='font-size:11px;color:var(--color-text-secondary);"
                    f"padding-top:8px'>{i+1}</div>", unsafe_allow_html=True)
        c1.markdown(f"<div style='color:#c0392b;font-weight:600;font-size:13px;"
                    f"padding-top:6px'>{coppia['od']}</div>", unsafe_allow_html=True)
        c2.markdown(f"<div style='color:#2980b9;font-weight:600;font-size:13px;"
                    f"padding-top:6px'>{coppia['os']}</div>", unsafe_allow_html=True)

        r = st.session_state.joh_risposte.get(i, {})
        for comp, col in [("c3",c3),("c4",c4),("c5",c5)]:
            cur_v = r.get(comp, "")
            idx = opts.index(cur_v) if cur_v in opts else 0
            v = col.selectbox("", opts, index=idx,
                              key=f"joh_{comp}_{i}",
                              label_visibility="collapsed")
            if v:
                st.session_state.joh_risposte.setdefault(i, {})[comp] = v

    # ── Calcolo punteggi ─────────────────────────────────────────────────
    jod, jos = 0, 0
    for i, r in st.session_state.joh_risposte.items():
        if r.get("c3") == "OD": jod += 1
        if r.get("c4") == "OS": jos += 1
        if r.get("c5") in ["OD","Entrambi"]: jod += 1
        if r.get("c5") in ["OS","Entrambi"]: jos += 1

    tot = jod + jos
    idx_lat = round((jod-jos)*100/tot, 1) if tot > 0 else 0
    dom = "OD dominante" if idx_lat > 10 else "OS dominante" if idx_lat < -10 else "Bilanciato"

    st.divider()
    m1,m2,m3 = st.columns(3)
    m1.metric("Punteggio OD", jod)
    m2.metric("Punteggio OS", jos)
    m3.metric("Indice lateralità", f"{idx_lat:+.1f}" if tot > 0 else "—")

    if tot > 0:
        color = "#c0392b" if idx_lat > 10 else "#2980b9" if idx_lat < -10 else "#2d7d6f"
        st.markdown(
            f"<div style='padding:8px 12px;border-radius:8px;"
            f"border-left:4px solid {color};font-size:13px;"
            f"background:var(--color-background-secondary);margin:8px 0'>"
            f"<b style='color:{color}'>{dom}</b> "
            f"(indice {idx_lat:+.1f}/100)</div>",
            unsafe_allow_html=True)

    nota_joh = st.text_input("Note Johansen", key="joh_note_v2")

    if st.button("Salva test Johansen", type="primary", key="joh_save_v2"):
        data = {
            "jod": jod, "jos": jos,
            "indice": idx_lat, "dominanza": dom,
            "risposte": {str(k): v for k,v in
                         st.session_state.joh_risposte.items()}
        }
        if _salva(conn, paz_id, "Johansen", data, idx_lat, dom,
                  operatore, nota_joh):
            st.success(f"Test Johansen salvato — {dom} (indice {idx_lat:+.1f})")

    if st.button("Reset risposte", key="joh_reset_v2"):
        st.session_state.joh_risposte = {}
