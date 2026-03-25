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
    st.caption("Questionario Fisher (bambini) - SCAP-A (adulti) - Primo step della valutazione uditiva")

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
        "Genera toni di riferimento a livello noto - "
        "Misura con fonometro (app smartphone o fonometro fisico) - "
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
        st.caption(f"Tono {cal_freq} Hz a {cal_db} dB HL - {cal_ear}")

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
    """Wizard calibrazione cuffie con SVG animate e profilo globale."""
    import streamlit.components.v1 as _stc_cal
    import json as _json_cal

    _HTML = '<!DOCTYPE html><html><head><meta charset="utf-8">\n<style>\n*{box-sizing:border-box;margin:0;padding:0;font-family:system-ui,sans-serif}\nbody{padding:10px;background:#f8f7f4;color:#1a1a1a}\n.steps{display:flex;gap:0;margin-bottom:14px;position:relative}\n.steps::before{content:\'\';position:absolute;top:17px;left:22px;right:22px;height:2px;background:#d4cec5;z-index:0}\n.step{flex:1;display:flex;flex-direction:column;align-items:center;gap:3px;z-index:1}\n.dot{width:34px;height:34px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:500;border:2px solid #d4cec5;background:#f8f7f4;color:#8a8a8a;transition:all .3s}\n.dot.active{background:#1d9e75;border-color:#1d9e75;color:#fff}\n.dot.done{background:#e1f5ee;border-color:#1d9e75;color:#1d9e75}\n.step-lbl{font-size:9px;color:#8a8a8a;text-align:center;max-width:66px}\n.card{background:#fff;border:1px solid #d4cec5;border-radius:10px;padding:12px 14px;margin-bottom:8px}\nh3{font-size:13px;font-weight:500;margin-bottom:3px}\n.cap{font-size:11px;color:#8a8a8a;margin-bottom:8px;line-height:1.4}\nbutton{font-family:inherit;font-size:12px;padding:5px 10px;border-radius:7px;border:1.5px solid #d4cec5;background:#fff;color:#4a4a4a;cursor:pointer}\nbutton:hover{background:#e1f5ee;border-color:#1d9e75;color:#0f6e56}\nbutton.primary{background:#1d9e75;border-color:#1d9e75;color:#fff}\nbutton:disabled{opacity:.35;cursor:not-allowed}\n.btn-row{display:flex;gap:6px;margin-top:10px;flex-wrap:wrap}\n.sec{display:none}.sec.on{display:block}\n.metric{background:#f8f7f4;border-radius:7px;padding:8px 10px;text-align:center}\n.metric .v{font-size:18px;font-weight:500}.metric .l{font-size:10px;color:#8a8a8a;margin-top:2px}\n.grid3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin:8px 0}\n.row{display:flex;align-items:center;gap:6px;margin:5px 0;font-size:12px}\n.row label{min-width:110px;font-size:11px;color:#4a4a4a}\ninput[type=number]{width:70px;padding:4px 6px;border-radius:6px;border:1px solid #d4cec5;font-size:13px;text-align:center}\ninput[type=text]{flex:1;padding:4px 8px;border-radius:6px;border:1px solid #d4cec5;font-size:12px}\n.status{font-size:12px;padding:5px 9px;border-radius:6px;margin:6px 0}\n.ok{background:#e1f5ee;color:#0f6e56}.warn{background:#fef7ec;color:#7a4f0a}.info{background:#ebf5fb;color:#154360}\n</style></head><body>\n<div class="steps">\n  <div class="step"><div class="dot active" id="d0">1</div><div class="step-lbl">Setup</div></div>\n  <div class="step"><div class="dot" id="d1">2</div><div class="step-lbl">Posizione</div></div>\n  <div class="step"><div class="dot" id="d2">3</div><div class="step-lbl">Misura</div></div>\n  <div class="step"><div class="dot" id="d3">4</div><div class="step-lbl">Profilo</div></div>\n</div>\n<div class="sec on" id="s0">\n<div class="card"><h3>Setup iniziale</h3><p class="cap">Verifica che tutto sia pronto.</p>\n<label style="display:flex;gap:7px;align-items:center;margin:4px 0;font-size:12px;cursor:pointer"><input type="checkbox" id="ck1" onchange="chk()"> Cuffie collegate, volume PC al massimo</label>\n<label style="display:flex;gap:7px;align-items:center;margin:4px 0;font-size:12px;cursor:pointer"><input type="checkbox" id="ck2" onchange="chk()"> EQ sistema e audio enhancer disattivati</label>\n<label style="display:flex;gap:7px;align-items:center;margin:4px 0;font-size:12px;cursor:pointer"><input type="checkbox" id="ck3" onchange="chk()"> Fonometro pronto (Decibel X, NIOSH SLM, Sound Meter)</label>\n<label style="display:flex;gap:7px;align-items:center;margin:4px 0;font-size:12px;cursor:pointer"><input type="checkbox" id="ck4" onchange="chk()"> Stanza silenziosa</label>\n<div id="ckSt" class="status warn" style="margin-top:8px">Spunta tutti i requisiti per continuare.</div></div>\n<div class="btn-row"><button class="primary" id="b0" onclick="go(1)" disabled>Avanti</button></div>\n</div>\n<div class="sec" id="s1">\n<div class="card"><h3>Posizionamento microfono</h3><p class="cap">La posizione esatta del microfono e critica per la misura.</p>\n<svg width="100%" viewBox="0 0 680 180">\n<text x="170" y="16" text-anchor="middle" style="font-size:12px;font-weight:500;fill:#0f6e56">CORRETTO</text>\n<ellipse cx="170" cy="100" rx="55" ry="65" fill="#e1f5ee" stroke="#1d9e75" stroke-width="2"/>\n<ellipse cx="170" cy="100" rx="35" ry="44" fill="#1d9e75" opacity="0.1"/>\n<circle cx="170" cy="100" r="10" fill="#ba7517"><animate attributeName="r" values="10;14;10" dur="1.5s" repeatCount="indefinite"/></circle>\n<circle cx="170" cy="100" r="5" fill="#fff"/>\n<circle cx="252" cy="18" r="12" fill="#1d9e75"/>\n<path d="M245 18 L250 24 L259 12" fill="none" stroke="#fff" stroke-width="2.5" stroke-linecap="round"/>\n<text x="170" y="176" text-anchor="middle" style="font-size:11px;fill:#8a8a8a">Mic al centro del padiglione</text>\n<line x1="340" y1="16" x2="340" y2="168" stroke="#d4cec5" stroke-width="0.5" stroke-dasharray="4,3"/>\n<text x="510" y="16" text-anchor="middle" style="font-size:12px;font-weight:500;fill:#a32d2d">ERRATO</text>\n<ellipse cx="510" cy="100" rx="55" ry="65" fill="#fcebeb" stroke="#e24b4a" stroke-width="2"/>\n<circle cx="548" cy="55" r="10" fill="#ba7517"/><circle cx="548" cy="55" r="5" fill="#fff"/>\n<line x1="546" y1="67" x2="528" y2="84" stroke="#a32d2d" stroke-width="1.5" stroke-dasharray="3,2"/>\n<circle cx="592" cy="18" r="12" fill="#e24b4a"/>\n<line x1="585" y1="12" x2="599" y2="24" stroke="#fff" stroke-width="2.5"/>\n<line x1="599" y1="12" x2="585" y2="24" stroke="#fff" stroke-width="2.5"/>\n<text x="510" y="176" text-anchor="middle" style="font-size:11px;fill:#8a8a8a">Mic fuori asse</text>\n</svg>\n<div class="status info">Premi leggermente il padiglione sul microfono per sigillare e isolare.</div></div>\n<div class="btn-row"><button onclick="go(0)">Indietro</button><button class="primary" onclick="go(2)">Avanti</button></div>\n</div>\n<div class="sec" id="s2">\n<div class="card"><h3>Misura frequenza per frequenza</h3><p class="cap">Per ogni frequenza: invia il tono dalla sezione Test Tonale, leggi il fonometro, inserisci il valore e conferma.</p>\n<div style="display:flex;gap:10px;align-items:center;margin:8px 0">\n  <div id="fchips" style="display:flex;flex-wrap:wrap;gap:4px;flex:1"></div>\n  <div style="text-align:center;min-width:65px"><div style="font-size:26px;font-weight:600;color:#1d9e75" id="curFreq">1000</div><div style="font-size:11px;color:#8a8a8a">Hz</div></div>\n</div>\n<div class="row"><label>dB(A) misurato OD</label><input type="number" id="splOD" value="73" min="30" max="120"><button onclick="adj(\'splOD\',-1)">-1</button><button onclick="adj(\'splOD\',1)">+1</button></div>\n<div class="row"><label>dB(A) misurato OS</label><input type="number" id="splOS" value="72" min="30" max="120"><button onclick="adj(\'splOS\',-1)">-1</button><button onclick="adj(\'splOS\',1)">+1</button></div>\n<div class="btn-row">\n  <button class="primary" onclick="confFreq()">Conferma questa frequenza</button>\n  <button onclick="nextFreq()">Freq. successiva</button>\n</div>\n<div id="misStatus" class="status info">Inserisci il valore letto sul fonometro e conferma.</div>\n<div id="misGrid" style="margin-top:8px;display:none"><div style="font-size:11px;color:#8a8a8a;margin-bottom:4px">Misure confermate:</div><div class="grid3" id="misValues"></div></div>\n</div>\n<div class="btn-row"><button onclick="go(1)">Indietro</button><button class="primary" onclick="go(3)">Salva profilo</button></div>\n</div>\n<div class="sec" id="s3">\n<div class="card"><h3>Salva profilo di calibrazione globale</h3><p class="cap">Questo profilo verra usato per tutti i test finche non viene aggiornato.</p>\n<div id="riepilogo" style="margin-bottom:10px"></div>\n<div class="row"><label>Marca cuffie</label><input type="text" id="brand" value=""></div>\n<div class="row"><label>Modello</label><input type="text" id="model" value=""></div>\n<div class="row"><label>Note</label><input type="text" id="note" placeholder="es. Voltcraft SL-451, foam coupler"></div>\n<div id="salvato" class="status ok" style="display:none">Profilo salvato nel gestionale.</div></div>\n<div class="btn-row"><button onclick="go(2)">Indietro</button><button class="primary" onclick="salva()">Salva profilo globale</button></div>\n</div>\n<script>\nconst FREQS=[1000,2000,4000,6000,8000,500,250];\nlet cur=0,misure={};\nfunction go(n){document.querySelectorAll(\'.sec\').forEach((s,i)=>s.classList.toggle(\'on\',i===n));[0,1,2,3].forEach(i=>{const d=document.getElementById(\'d\'+i);d.classList.remove(\'active\',\'done\');if(i<n)d.classList.add(\'done\');else if(i===n)d.classList.add(\'active\');});if(n===2)buildChips();if(n===3)buildRiep();}\nfunction chk(){const ok=[1,2,3,4].every(i=>document.getElementById(\'ck\'+i).checked);document.getElementById(\'b0\').disabled=!ok;document.getElementById(\'ckSt\').textContent=ok?\'Tutto pronto!\':\'Spunta tutti i requisiti.\';document.getElementById(\'ckSt\').className=\'status \'+(ok?\'ok\':\'warn\');}\nfunction buildChips(){const c=document.getElementById(\'fchips\');c.innerHTML=\'\';FREQS.forEach((f,i)=>{const d=document.createElement(\'div\');const done=misure[f]!==undefined;const isC=i===cur;d.style.cssText=\'padding:3px 8px;border-radius:9px;font-size:11px;cursor:pointer;border:1px solid \'+(isC?\'#1d9e75\':done?\'#1d9e75\':\'#d4cec5\')+\';background:\'+(isC?\'#1d9e75\':done?\'#e1f5ee\':\'#f8f7f4\')+\';color:\'+(isC?\'#fff\':done?\'#0f6e56\':\'#8a8a8a\');d.textContent=(f>=1000?f/1000+\'k\':f)+\'Hz\'+(done?\' v\':\'\');d.onclick=()=>{cur=i;document.getElementById(\'curFreq\').textContent=FREQS[i];buildChips();};c.appendChild(d);});document.getElementById(\'curFreq\').textContent=FREQS[cur];}\nfunction adj(id,d){const el=document.getElementById(id);el.value=parseInt(el.value)+d;}\nfunction confFreq(){const f=FREQS[cur];misure[f]={od:parseInt(document.getElementById(\'splOD\').value),os:parseInt(document.getElementById(\'splOS\').value)};document.getElementById(\'misStatus\').textContent=\'Confermato \'+f+\' Hz - OD:\'+misure[f].od+\' OS:\'+misure[f].os;document.getElementById(\'misStatus\').className=\'status ok\';buildChips();buildMisGrid();if(cur<FREQS.length-1){cur++;document.getElementById(\'curFreq\').textContent=FREQS[cur];buildChips();}}\nfunction nextFreq(){if(cur<FREQS.length-1){cur++;buildChips();}}\nfunction buildMisGrid(){const g=document.getElementById(\'misValues\');g.innerHTML=\'\';document.getElementById(\'misGrid\').style.display=Object.keys(misure).length?\'block\':\'none\';Object.entries(misure).forEach(([f,m])=>{const d=document.createElement(\'div\');d.className=\'metric\';const offOD=m.od-70,offOS=m.os-70;d.innerHTML=\'<div class="v" style="font-size:13px">\'+(f>=1000?f/1000+\'k\':f)+\'Hz</div><div style="font-size:11px;color:\'+(Math.abs(offOD)<3?\'#1d9e75\':\'#ba7517\')+\'">OD \'+(offOD>=0?\'+\':\'\')+offOD+\'</div><div style="font-size:11px;color:\'+(Math.abs(offOS)<3?\'#1d9e75\':\'#ba7517\')+\'">OS \'+(offOS>=0?\'+\':\'\')+offOS+\'</div>\';g.appendChild(d);});}\nfunction buildRiep(){const r=document.getElementById(\'riepilogo\');if(!Object.keys(misure).length){r.innerHTML=\'<div class="status warn">Nessuna misura. Torna al passo precedente.</div>\';return;}const avgOD=Math.round(Object.values(misure).reduce((a,m)=>a+m.od,0)/Object.keys(misure).length);const avgOS=Math.round(Object.values(misure).reduce((a,m)=>a+m.os,0)/Object.keys(misure).length);r.innerHTML=\'<div class="grid3"><div class="metric"><div class="v">\'+avgOD+\'</div><div class="l">Media OD dB</div></div><div class="metric"><div class="v">\'+avgOS+\'</div><div class="l">Media OS dB</div></div><div class="metric"><div class="v">\'+Object.keys(misure).length+\'/7</div><div class="l">Freq. misurate</div></div></div>\';}\nfunction salva(){const data={brand:document.getElementById(\'brand\').value,model:document.getElementById(\'model\').value,note:document.getElementById(\'note\').value,misure:misure};window.parent.postMessage({type:\'streamlit:setComponentValue\',value:JSON.stringify(data)},\'*\');document.getElementById(\'salvato\').style.display=\'block\';[0,1,2,3].forEach(i=>document.getElementById(\'d\'+i).classList.add(\'done\'));}\nbuildChips();\n</script></body></html>'

    result = _stc_cal.html(_HTML, height=700, scrolling=True)

    if result:
        try:
            data = _json_cal.loads(result) if isinstance(result, str) else result
            if data and data.get("misure"):
                misure = data["misure"]
                vals_od = [m["od"] for m in misure.values()]
                vals_os = [m["os"] for m in misure.values()]
                avg_od = round(sum(vals_od)/len(vals_od)) if vals_od else 70
                avg_os = round(sum(vals_os)/len(vals_os)) if vals_os else 70
                st.session_state["cal_profilo_globale"] = {
                    "brand": data.get("brand",""),
                    "model": data.get("model",""),
                    "offset_od": avg_od - 70,
                    "offset_os": avg_os - 70,
                    "misure": misure,
                }
                st.success(
                    f"Profilo salvato: {data.get('brand','')} {data.get('model','')} — "
                    f"OD: {avg_od-70:+d} dB · OS: {avg_os-70:+d} dB"
                )
        except Exception:
            pass

    profilo = st.session_state.get("cal_profilo_globale")
    if profilo:
        st.info(
            f"Profilo attivo: **{profilo.get('brand','')} {profilo.get('model','')}** — "
            f"Offset OD: {profilo.get('offset_od',0):+d} dB · "
            f"OS: {profilo.get('offset_os',0):+d} dB"
        )


def ui_test_tonale(conn, paz_id, operatore=""):
    st.subheader("Test tonale audiometrico")
    st.caption("Via aerea e ossea - Metodo Hipérion - Curva Tomatis")

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

    # ── Invia tono (WebAudio — zero latenza) ─────────────────────────────
    cal_offset = st.session_state.get("cal_profilo_globale", {}).get(
        f"offset_{ear_code.lower()}", 0)
    db_eff = int(cur_db) + cal_offset

    # Componente WebAudio: tono istantaneo nel browser
    import streamlit.components.v1 as _sc
    _sc.html(f"""<script>
(function(){{
  var _a=new(window.AudioContext||window.webkitAudioContext)();
  if(_a.state==='suspended')_a.resume();
  var _o=_a.createOscillator(),_g=_a.createGain(),_p=_a.createStereoPanner();
  _p.pan.value={0.9 if ear_code=='OD' else -0.9};
  _o.frequency.value={int(cur_f)};_o.type='sine';
  var _amp=Math.pow(10,({db_eff}-90)/20)*0.85;
  _amp=Math.max(0.001,Math.min(0.95,_amp));
  _g.gain.setValueAtTime(0,_a.currentTime);
  _g.gain.linearRampToValueAtTime(_amp,_a.currentTime+0.02);
  _g.gain.setValueAtTime(_amp,_a.currentTime+{dur}-0.05);
  _g.gain.linearRampToValueAtTime(0,_a.currentTime+{dur});
  _o.connect(_g);_g.connect(_p);_p.connect(_a.destination);
  _o.start();_o.stop(_a.currentTime+{dur});
}})();
</script><div style="display:none">t</div>""", height=0)

    c_play, c_m5, c_p5, c_m1, c_p1 = st.columns([3,1,1,1,1])
    with c_play:
        tono_inviato = st.button("▶  Invia tono  [SPAZIO]", type="primary",
                     key="tt_play", use_container_width=True)
        if tono_inviato:
            st.session_state["tt_play_now"] = True
    # Il tono parte AUTOMATICAMENTE al caricamento del componente html sopra
    # Il pulsante serve per rigenerarlo
    if st.session_state.get("tt_play_now"):
        st.session_state["tt_play_now"] = False
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
    st.caption("⌨️ SPAZIO = invia tono - ↑ = +5dB - ↓ = -5dB - R = risponde - N = non risponde")

    # JS per keyboard shortcuts
    import streamlit.components.v1 as _stc_kbd
    _stc_kbd.html("""
<style>
body{margin:0;padding:0;background:transparent}
</style>
<script>
(function(){
  if(window._kbdBound) return;
  window._kbdBound = true;
  var actx = null;
  var curOsc = null;

  function getCtx(){
    if(!actx) actx = new(window.AudioContext||window.webkitAudioContext)();
    if(actx.state==='suspended') actx.resume();
    return actx;
  }

  // Legge freq e dB dalla pagina parent
  function getParams(){
    try {
      var doc = window.parent.document;
      // Frequenza dal selectbox
      var freqSel = doc.querySelector('select[data-testid="stSelectbox"]');
      var freqVal = 1000;
      if(freqSel) freqVal = parseInt(freqSel.value) || 1000;

      // dB dallo slider
      var dbSlider = doc.querySelector('input[type="range"]');
      var dbVal = 30;
      if(dbSlider) dbVal = parseFloat(dbSlider.value) || 30;

      // Orecchio
      var earRadios = doc.querySelectorAll('input[type="radio"]:checked');
      var ear = 'OD';
      earRadios.forEach(function(r){ if(r.value==='OD'||r.value==='OS') ear=r.value; });

      return {freq: freqVal, db: dbVal, ear: ear};
    } catch(e){ return {freq:1000, db:30, ear:'OD'}; }
  }

  function playTone(freq, dbHL, ear, dur){
    if(curOsc){ try{curOsc.stop();}catch(e){} curOsc=null; }
    var ctx = getCtx();
    var dbfs = dbHL - 90.0;
    var amp = Math.pow(10, dbfs/20) * 0.85;
    amp = Math.max(0.001, Math.min(0.95, amp));

    var osc = ctx.createOscillator();
    var gain = ctx.createGain();
    var pan = ctx.createStereoPanner();

    pan.pan.value = ear==='OD' ? 0.9 : -0.9;
    osc.frequency.value = freq;
    osc.type = 'sine';

    gain.gain.setValueAtTime(0, ctx.currentTime);
    gain.gain.linearRampToValueAtTime(amp, ctx.currentTime + 0.02);
    gain.gain.setValueAtTime(amp, ctx.currentTime + dur - 0.05);
    gain.gain.linearRampToValueAtTime(0, ctx.currentTime + dur);

    osc.connect(gain);
    gain.connect(pan);
    pan.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + dur);
    curOsc = osc;
  }

  // Esponi funzione globale per il pulsante Streamlit
  window._playTone = function(freq, db, ear, dur){
    playTone(freq, db, ear, dur || 2.0);
  };

  document.addEventListener('keydown', function(e){
    var tag = document.activeElement ? document.activeElement.tagName : '';
    if(tag==='INPUT'||tag==='TEXTAREA'||tag==='SELECT') return;

    if(e.code==='Space'){
      e.preventDefault();
      var p = getParams();
      playTone(p.freq, p.db, p.ear, 2.0);
    }
    if(e.code==='ArrowUp'){
      e.preventDefault();
      var btns = window.parent.document.querySelectorAll('button');
      btns.forEach(function(b){ if(b.textContent.trim()==='+5') b.click(); });
    }
    if(e.code==='ArrowDown'){
      e.preventDefault();
      var btns = window.parent.document.querySelectorAll('button');
      btns.forEach(function(b){ if(b.textContent.trim()==='-5') b.click(); });
    }
    if(e.key==='r'||e.key==='R'){
      var btns = window.parent.document.querySelectorAll('button');
      btns.forEach(function(b){ if(b.textContent.includes('RISPONDE')&&!b.textContent.includes('NON')) b.click(); });
    }
    if(e.key==='n'||e.key==='N'){
      var btns = window.parent.document.querySelectorAll('button');
      btns.forEach(function(b){ if(b.textContent.includes('NON RISPONDE')) b.click(); });
    }
    if(e.key==='v'||e.key==='V'){
      var btns = window.parent.document.querySelectorAll('button');
      btns.forEach(function(b){ if(b.textContent.includes('VALIDA')) b.click(); });
    }
  });
})();
</script>
""", height=0)

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
        "20 coppie sillabe OD/OS simultanee - 5 compiti - "
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
    st.caption("Comp.3 = risposta DX - Comp.4 = risposta SX - Comp.5 = entrambi")

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
