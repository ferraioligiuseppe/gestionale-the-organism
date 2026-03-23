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
    with st.expander("🎵 Test Tonale Audiometrico + EQ", expanded=False):
        ui_test_tonale(conn, paz_id, op)

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


def ui_test_tonale(conn, paz_id, operatore=""):
    st.subheader("Test tonale audiometrico")
    st.caption("Via aerea e ossea · Metodo Hipérion · Curva Tomatis")

    col1, col2, col3 = st.columns(3)
    with col1:
        ear = st.selectbox("Orecchio", ["OD - Destro", "OS - Sinistro"], key="diag_ton_ear_v2")
        ear_code = "OD" if "OD" in ear else "OS"
    with col2:
        via = st.selectbox("Via", ["AC - Aerea", "BC - Ossea"], key="diag_ton_via_v2")
        via_code = "ac" if "AC" in via else "bc"
    with col3:
        cur_f = st.selectbox("Frequenza Hz", FREQS_TON,
                             format_func=lambda f: str(f) if f < 1000 else f"{f//1000}k",
                             key="diag_ton_freq_v2")

    cur_db = st.slider("Livello dB HL", min_value=-20, max_value=90,
                       value=30, step=5, key="diag_ton_db_v2")

    dur_str = st.select_slider("Durata", options=["1.0","1.5","2.0","2.5","3.0"],
                               value="2.0", key="diag_ton_dur_v2")
    dur = float(dur_str)

    if st.button("Invia tono", type="primary", key="diag_ton_play_v2", use_container_width=True):
        wav = _genera_tono_wav(int(cur_f), float(cur_db), ear_code, float(dur))
        st.audio(wav, format="audio/wav")

    st.divider()
    st.markdown("**Risposta paziente**")
    b1, b2, b3 = st.columns(3)
    with b1:
        risp = st.button("Risponde", key="diag_ton_si_v2", use_container_width=True)
    with b2:
        no_risp = st.button("Non risponde", key="diag_ton_no_v2", use_container_width=True)
    with b3:
        valida = st.button("Valida soglia", key="diag_ton_val_v2", type="primary",
                           use_container_width=True)

    if risp:
        st.info(f"Risponde a {cur_db} dB — abbassa il livello e reinvia il tono")
    if no_risp:
        st.warning(f"Non risponde a {cur_db} dB — alza il livello e reinvia il tono")
    if valida:
        key_s = f"diag_ton_soglie_{ear_code}_{via_code}"
        if key_s not in st.session_state:
            st.session_state[key_s] = {}
        fidx = FREQS_TON.index(int(cur_f))
        st.session_state[key_s][fidx] = int(cur_db)
        st.success(f"Soglia validata: {cur_f} Hz {ear_code} {via_code.upper()} = {cur_db} dB HL")

    # Soglie registrate
    st.divider()
    st.markdown("**Soglie registrate**")
    cols = st.columns(4)
    for col, (ek, vk, label, color) in zip(cols, [
        ("OD","ac","OD AC","#c0392b"), ("OS","ac","OS AC","#2980b9"),
        ("OD","bc","OD BC","#8e44ad"), ("OS","bc","OS BC","#16a085"),
    ]):
        col.markdown(f"<b style='color:{color};font-size:11px'>{label}</b>",
                     unsafe_allow_html=True)
        soglie = st.session_state.get(f"diag_ton_soglie_{ek}_{vk}", {})
        for fi, v in sorted(soglie.items()):
            col.markdown(
                f"<span style='border:1px solid {color};border-radius:6px;"
                f"padding:2px 5px;font-size:11px;color:{color};"
                f"display:inline-block;margin:1px'>{FLABELS_TON[fi]}:{v}</span>",
                unsafe_allow_html=True)

    # Tomatis
    st.markdown("**Curva Tomatis** (modifica valori target)")
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

    # Grafico
    od_ac = [st.session_state.get("diag_ton_soglie_OD_ac",{}).get(i) for i in range(11)]
    os_ac = [st.session_state.get("diag_ton_soglie_OS_ac",{}).get(i) for i in range(11)]
    tom   = st.session_state.get("diag_ton_tomatis_v2", list(TOMATIS_STD))

    if any(v is not None for v in od_ac + os_ac):
        st.divider()
        _mostra_audiogramma(od_ac, os_ac, tom)
        eq_od, eq_os = _calc_eq_tomatis(od_ac, os_ac, tom)
        st.markdown("**Delta EQ terapeutico**")
        ec = st.columns(11)
        for i, (lbl, vod, vos) in enumerate(zip(FLABELS_TON, eq_od, eq_os)):
            v = vod if vod is not None else vos
            if v is not None:
                cc = "green" if v > 3 else "red" if v < -3 else "orange"
                ec[i].markdown(
                    f"<div style='text-align:center'>"
                    f"<b style='color:{cc}'>{v:+.0f}</b>"
                    f"<br><small style='color:#888'>{lbl}</small></div>",
                    unsafe_allow_html=True)

    # Salvataggio
    st.divider()
    nota_ton = st.text_input("Note audiogramma", key="diag_ton_note_v2")
    if st.button("Salva audiogramma", type="primary", key="diag_ton_save_v2"):
        od_bc = [st.session_state.get("diag_ton_soglie_OD_bc",{}).get(i) for i in range(11)]
        os_bc = [st.session_state.get("diag_ton_soglie_OS_bc",{}).get(i) for i in range(11)]
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
