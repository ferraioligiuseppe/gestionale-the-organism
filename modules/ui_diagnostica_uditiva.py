# -*- coding: utf-8 -*-
"""
Modulo: Diagnostica Uditiva Funzionale
Gestionale The Organism

Tab:
  1. Fisher (bambini) — layout orizzontale
  2. SCAP-A (adulti) — layout orizzontale
  3. Calibrazione cuffie — wizard SVG
  4. Test Tonale + EQ — WebAudio zero latenza
  5. Lateralità uditiva
  6. Selettività uditiva
  7. Johansen — tracce MP3
  8. Storico
"""

import json
import io
import wave
import math
import streamlit as st
from datetime import date, datetime

import numpy as np
import pandas as pd

# ─────────────────────────────────────────────────────────────────────────────
# Costanti
# ─────────────────────────────────────────────────────────────────────────────

FISHER_ITEMS = [
    (1,  "Ha una storia di perdita dell'udito", None),
    (2,  "Ha una storia di infezioni dell'orecchio", None),
    (3,  "Non presta attenzione alle istruzioni il 50% o piu delle volte", "DIC"),
    (4,  "Non ascolta attentamente le indicazioni, spesso necessario ripetere", "DIC"),
    (5,  'Dice "huh" e "cosa" almeno cinque o piu volte al giorno', "DIC"),
    (6,  "Non puo assistere agli stimoli uditivi per piu di pochi secondi", "TFM"),
    (7,  "Ha un breve intervallo di attenzione", "TFM"),
    (8,  "Sogni ad occhi aperti, attenzione si sposta", None),
    (9,  "E facilmente distratto dai suoni di sottofondo", "TFM"),
    (10, "Ha difficolta con la fonetica", "DIC"),
    (11, "Riscontra problemi di discriminazione acustica", "DIC"),
    (12, "Dimentica cio che viene detto in pochi minuti", "TFM"),
    (13, "Non ricorda semplici cose di routine di giorno in giorno", None),
    (14, "Problemi nel ricordare cio che e stato ascoltato la scorsa settimana", None),
    (15, "Difficolta a ricordare una sequenza che e stata ascoltata", "ORG"),
    (16, "Sperimenta difficolta a seguire le indicazioni uditive", "DIC"),
    (17, "Spesso fraintende cio che viene detto", "DIC"),
    (18, "Non comprende molte parole / concetti verbali per eta", "DIC"),
    (19, "Impara male attraverso il canale uditivo", None),
    (20, "Ha un problema linguistico (morfologia, sintassi, vocabolario)", None),
    (21, "Ha un problema di articolazione (discorso)", "DIC"),
    (22, "Non sempre possibile mettere in relazione cio che si sente con cio che si vede", "INT"),
    (23, "Manca la motivazione per imparare", None),
    (24, "Mostra una risposta lenta o ritardata agli stimoli verbali", "DIC"),
    (25, "Dimostra prestazioni inferiori alla media in aree accademiche", None),
]

FISHER_NORMS = {
    "Prescolare (5.0-5.11)": 92.0,
    "1a elementare (6.0-6.11)": 89.9,
    "2a elementare (7.0-7.11)": 87.0,
    "3a elementare (8.0-8.11)": 85.6,
    "4a elementare (9.0-9.11)": 85.9,
    "5a elementare (10.0-10.11)": 87.4,
    "1a media (11.0-11.11)": 80.0,
}

APD_CATS = {
    "DIC": {"label": "DIC — Discriminazione", "items": [3,4,5,10,11,16,17,18,21,24]},
    "TFM": {"label": "TFM — Memoria/Figura-Terra", "items": [6,7,9,12]},
    "ORG": {"label": "ORG — Organizzazione", "items": [15]},
    "INT": {"label": "INT — Integrazione", "items": [22]},
}

SCAPA_ITEMS = [
    (1,  False, "Hai bisogno di ripetizioni frequenti quando ascolti una persona?",
                "La persona necessita spesso di ripetizioni?"),
    (2,  True,  "Riesci a mantenere l'attenzione su una persona per piu di 10 minuti?",
                "La persona riesce a mantenere l'attenzione per piu di 10 minuti?"),
    (3,  False, "Ti risulta difficile seguire il parlato con rumore di fondo?",
                "La persona trova difficile seguire il parlato con rumore di fondo?"),
    (4,  False, "Hai difficolta a ricordare cio che e stato detto nell'ordine corretto?",
                "La persona ha difficolta a ricordare le cose nell'ordine corretto?"),
    (5,  False, "Dimentichi cio che ti e stato detto molto rapidamente (entro un minuto)?",
                "La persona dimentica rapidamente cio che le e stato detto?"),
    (6,  False, "Hai difficolta a capire il parlato con rumore di fondo intenso?",
                "La persona ha difficolta con rumore di fondo intenso?"),
    (7,  True,  "Riesci a ricordare i nomi di 5 amici di scuola che non vedi da anni?",
                "La persona riesce a ricordare i nomi di 5 amici che non vede da 30 anni?"),
    (8,  False, "Ti e stato detto che impieghi piu tempo del normale per rispondere?",
                "La persona impiega molto piu tempo per rispondere?"),
    (9,  False, "Hai difficolta quando due persone parlano nello stesso momento?",
                "La persona ha difficolta quando due persone parlano insieme?"),
    (10, False, "Difficolta a capire il parlato quando non vedi il volto di chi parla?",
                "La persona ha difficolta a capire il parlato senza vedere il volto?"),
    (11, False, "Hai difficolta a ricordare numeri (telefono, targa, codice)?",
                "La persona ha difficolta a ricordare cifre/numeri?"),
    (12, False, "Altri ti riferiscono che non presti attenzione quando iniziano a parlarti?",
                "La persona non presta attenzione quando le si inizia a parlare?"),
]

FREQS_TON   = [125, 250, 500, 750, 1000, 1500, 2000, 3000, 4000, 6000, 8000]
FLABELS_TON = ['125','250','500','750','1k','1.5k','2k','3k','4k','6k','8k']
FREQ_ORDER  = [8000,6000,4000,3000,2000,1500,1000,750,500,250,125]
TOMATIS_STD = [-5,-8,-10,-12,-14,-15,-14,-15,-12,-8,-5]

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
    {"n":2,"desc":"Compito 1 — OD","dur":"~69s"},
    {"n":3,"desc":"Compito 2 — OS","dur":"~73s"},
    {"n":4,"desc":"Compito 3 — Risposte DX","dur":"~75s"},
    {"n":5,"desc":"Compito 4 — Risposte SX","dur":"~73s"},
    {"n":6,"desc":"Compito 5 — Entrambi","dur":"~100s"},
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
        from modules.app_core import _DB_BACKEND
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
        from modules.app_core import get_connection; return get_connection()
    except Exception: pass
    import sqlite3
    c = sqlite3.connect("organism.db"); c.row_factory = sqlite3.Row; return c

def _init_db(conn):
    raw = getattr(conn, "_conn", conn)
    try: cur = raw.cursor()
    except: cur = conn.cursor()
    pg = _is_pg(conn)
    if pg:
        cur.execute("""CREATE TABLE IF NOT EXISTS diagnostica_uditiva (
            id BIGSERIAL PRIMARY KEY, paziente_id BIGINT NOT NULL,
            tipo TEXT, data_esame TEXT, operatore TEXT,
            dati_json TEXT, punteggio REAL, classificazione TEXT,
            note TEXT, created_at TEXT)""")
    else:
        cur.execute("""CREATE TABLE IF NOT EXISTS diagnostica_uditiva (
            id INTEGER PRIMARY KEY AUTOINCREMENT, paziente_id INTEGER NOT NULL,
            tipo TEXT, data_esame TEXT, operatore TEXT,
            dati_json TEXT, punteggio REAL, classificazione TEXT,
            note TEXT, created_at TEXT)""")
    try: raw.commit()
    except: conn.commit()

def _salva(conn, paz_id, tipo, dati, punteggio, classificazione, operatore="", note=""):
    cur = conn.cursor()
    ph = _ph(9, conn)
    params = (paz_id, tipo, date.today().isoformat(), operatore,
              json.dumps(dati), punteggio, classificazione, note,
              datetime.now().isoformat(timespec="seconds"))
    sql = (f"INSERT INTO diagnostica_uditiva (paziente_id,tipo,data_esame,operatore,"
           f"dati_json,punteggio,classificazione,note,created_at) VALUES ({ph})")
    try:
        cur.execute(sql, params); conn.commit(); return True
    except Exception as e:
        st.error(f"Errore salvataggio: {e}"); return False

def _fetch_pazienti(conn):
    """Recupera (id, cognome, nome) dei pazienti su SQLite o PostgreSQL.

    Nota: su PostgreSQL una query fallita aborta l'intera transazione, quindi
    NON usiamo più 'sqlite_master' come sonda (fallirebbe e bloccherebbe tutto).
    Proviamo prima lo stile PostgreSQL (information_schema) e solo in caso di
    errore ricadiamo su SQLite, con rollback difensivo a ogni fallimento.
    """
    def _safe_rollback():
        try:
            conn.rollback()
        except Exception:
            pass

    # Pulisce un'eventuale transazione già abortita ereditata da query precedenti
    _safe_rollback()
    cur = conn.cursor()

    # ── Elenco tabelle candidate ─────────────────────────────────────────────
    candidates = []
    try:  # stile PostgreSQL — funziona su PG, fallisce (pulito) su SQLite
        cur.execute("SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema='public'")
        for r in cur.fetchall():
            t = r[0] if not isinstance(r, dict) else r.get('table_name', '')
            if t and ('paz' in t.lower() or 'patient' in t.lower()):
                candidates.append(t)
    except Exception:
        _safe_rollback()
        try:  # fallback SQLite
            cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
            for r in cur.fetchall():
                t = r[0] if not isinstance(r, dict) else r.get('name', '')
                if t and ('paz' in t.lower() or 'patient' in t.lower()):
                    candidates.append(t)
        except Exception:
            _safe_rollback()
    for t in ['pazienti', 'Pazienti', 'patients', 'Patients']:
        if t not in candidates:
            candidates.append(t)

    # ── Colonne di una tabella ───────────────────────────────────────────────
    def get_cols(table):
        try:  # stile PostgreSQL
            cur.execute("SELECT column_name FROM information_schema.columns "
                        "WHERE table_schema='public' AND table_name=%s", (table,))
            cols = [r[0] if not isinstance(r, dict) else r.get('column_name', '')
                    for r in cur.fetchall()]
            if cols:
                return cols
        except Exception:
            _safe_rollback()
        try:  # fallback SQLite
            cur.execute(f'PRAGMA table_info("{table}")')
            return [r[1] for r in cur.fetchall()]
        except Exception:
            _safe_rollback()
            return []

    def pick(cols, cands):
        s = set(cols)
        for c in cands:
            if c in s:
                return c
        low = {x.lower(): x for x in cols}
        for c in cands:
            if c.lower() in low:
                return low[c.lower()]
        return None

    # ── Lettura pazienti ─────────────────────────────────────────────────────
    for table in candidates:
        cols = get_cols(table)
        if not cols:
            continue
        idc = pick(cols, ['id'])
        cc = pick(cols, ['Cognome', 'cognome', 'LastName', 'last_name', 'surname'])
        nc = pick(cols, ['Nome', 'nome', 'FirstName', 'first_name'])
        if not (idc and cc and nc):
            continue
        try:
            cur.execute(f'SELECT "{idc}","{cc}","{nc}" FROM "{table}" '
                        f'ORDER BY "{cc}","{nc}"')
            rows = cur.fetchall()
            if rows:
                return rows
        except Exception:
            _safe_rollback()
            continue
    return []

# ─────────────────────────────────────────────────────────────────────────────
# Audio
# ─────────────────────────────────────────────────────────────────────────────

def _genera_tono_wav(freq_hz, db_hl, orecchio, secondi=2.0, sr=44100):
    dbfs = db_hl - 90.0
    amp  = max(0.001, min(0.95, 10**(dbfs/20.0)))
    t    = np.linspace(0, secondi, int(sr*secondi), endpoint=False)
    sig  = amp * np.sin(2*math.pi*freq_hz*t)
    fade = int(sr*0.02)
    if len(sig) > 2*fade:
        sig[:fade] *= np.linspace(0,1,fade)
        sig[-fade:] *= np.linspace(1,0,fade)
    if orecchio == "OD":   L, R = np.zeros_like(sig), sig
    elif orecchio == "OS": L, R = sig, np.zeros_like(sig)
    else:                  L, R = sig, sig
    stereo = np.stack([L,R], axis=1)
    pcm = np.int16(np.clip(stereo,-1,1)*32767)
    buf = io.BytesIO()
    with wave.open(buf,"wb") as wf:
        wf.setnchannels(2); wf.setsampwidth(2)
        wf.setframerate(sr); wf.writeframes(pcm.tobytes())
    return buf.getvalue()

def _load_johansen_track(n):
    import pathlib
    base = pathlib.Path(__file__).parent.parent / "assets" / "johansen"
    path = base / f"traccia_{n:02d}.mp3"
    if path.exists(): return path.read_bytes(), "audio/mp3"
    return None, None

# ─────────────────────────────────────────────────────────────────────────────
# UI principale
# ─────────────────────────────────────────────────────────────────────────────

def ui_diagnostica_uditiva(conn=None):
    st.header("Diagnostica Uditiva Funzionale")
    st.caption("Fisher · SCAP-A · Calibrazione · Test Tonale · Lateralità · Selettività · Johansen")

    ss = st.session_state
    if conn is None: conn = _get_conn()
    # init una sola volta per sessione (evita un giro DB a ogni rerun)
    if not ss.get("_du_init"):
        _init_db(conn); ss["_du_init"] = True
    cur = conn.cursor()

    # Selezione paziente — usa il paziente attivo selezionato nel banner in alto

    try:
        from .paziente_attivo import get_paziente_attivo
        paz_id = get_paziente_attivo(conn)
    except Exception:
        paz_id = None
    if not paz_id:
        return
    op = st.text_input("Operatore", "", key="du_op")

    st.divider()

    tabs = st.tabs([
        "📋 Fisher", "📋 SCAP-A", "🔧 Calibrazione",
        "🎵 Test Tonale", "🎧 Lateralità", "📊 Selettività",
        "🎧 Johansen", "📈 Storico"
    ])

    with tabs[0]: _ui_fisher(conn, paz_id, op)
    with tabs[1]: _ui_scapa(conn, paz_id, op)
    with tabs[2]: _ui_calibrazione(conn)
    with tabs[3]: _ui_test_tonale(conn, paz_id, op)
    with tabs[4]: _ui_lateralita(conn, paz_id, op)
    with tabs[5]: _ui_selettivita(conn, paz_id, op)
    with tabs[6]: _ui_johansen(conn, paz_id, op)
    with tabs[7]: _ui_storico(conn, cur, paz_id)

# ─────────────────────────────────────────────────────────────────────────────
# Tab 1: Fisher
# ─────────────────────────────────────────────────────────────────────────────

def _ui_fisher(conn, paz_id, operatore):
    st.subheader("Elenco di controllo dei problemi uditivi di Fisher")
    st.caption("25 item · Punteggio = elementi NON spuntati × 4 · Soglia: 72%")

    # Dati bambino — riga orizzontale
    c1,c2,c3 = st.columns(3)
    with c1: f_nome    = st.text_input("Nome bambino", key="f_nome_i")
    with c2: f_nascita = st.date_input("Data di nascita", key="f_nasc_i", value=None)
    with c3: f_scuola  = st.text_input("Scuola / Classe", key="f_scuola_i")

    c1,c2 = st.columns(2)
    with c1: fascia     = st.selectbox("Fascia d'eta", list(FISHER_NORMS.keys()), key="f_fascia_i")
    with c2: compilatore = st.selectbox("Chi compila", ["Genitore","Insegnante","Terapeuta"], key="f_comp_i")

    st.markdown("---")
    st.markdown("**Spunta ogni elemento che è considerato un problema:**")

    # 25 item in 2 colonne
    checked = []
    col_sx, col_dx = st.columns(2)
    for idx, (n, testo, cat) in enumerate(FISHER_ITEMS):
        label = f"{n}. {testo}" + (f" `{cat}`" if cat else "")
        col = col_sx if idx < 13 else col_dx
        val = col.checkbox(label, key=f"fi_{n}_v2")
        checked.append(val)

    # Calcolo
    st.markdown("---")
    n_checked  = sum(checked)
    n_unchecked = 25 - n_checked
    score = n_unchecked * 4
    mean  = FISHER_NORMS[fascia]
    sd    = 18.2

    if score >= 72:          cls, col = "WNL", "green"
    elif score >= mean - sd: cls, col = "Sotto soglia", "orange"
    elif score >= mean - 2*sd: cls, col = "1 DS sotto", "orange"
    elif score >= mean - 3*sd: cls, col = "2 DS sotto", "red"
    else:                    cls, col = "3 DS sotto", "red"

    m1,m2,m3 = st.columns(3)
    m1.metric("Punteggio", f"{score}%")
    m2.metric("Item spuntati", f"{n_checked}/25")
    m3.metric("Classificazione", cls)
    st.progress(min(score/100.0, 1.0))
    st.caption(f"Media gruppo {fascia}: {mean}% · Soglia: 72% · SD: {sd}")

    # APD
    st.markdown("**Profilo APD (classificazione Katz):**")
    ac1,ac2,ac3,ac4 = st.columns(4)
    for col_apd, (cat, info) in zip([ac1,ac2,ac3,ac4], APD_CATS.items()):
        v = sum(1 for num in info["items"] if checked[num-1])
        col_apd.metric(cat, f"{v}/{len(info['items'])}", help=info["label"])

    nota = st.text_input("Note Fisher", key="f_note_i_v2")
    if st.button("Salva Fisher", type="primary", key="f_save_v2"):
        dati = {"nome":f_nome,"nascita":str(f_nascita) if f_nascita else "",
                "scuola":f_scuola,"fascia":fascia,"compilatore":compilatore,
                "checked":checked,"apd":{c:sum(1 for n in i["items"] if checked[n-1])
                                          for c,i in APD_CATS.items()}}
        if _salva(conn, paz_id, "Fisher", dati, score, cls, operatore, nota):
            st.success(f"Fisher salvato — {score}% ({cls})")

# ─────────────────────────────────────────────────────────────────────────────
# Tab 2: SCAP-A
# ─────────────────────────────────────────────────────────────────────────────

def _ui_scapa(conn, paz_id, operatore):
    st.subheader("SCAP-A — Screening funzionamento uditivo adulto")
    st.caption("12 domande Presente/Assente · Q2 e Q7 scoring invertito")

    chi = st.radio("Chi compila?", ["Autovalutazione","Familiare / Caregiver"],
                   horizontal=True, key="a_chi_v2")
    is_fam = (chi == "Familiare / Caregiver")

    c1,c2 = st.columns(2)
    with c1: a_nome = st.text_input("Nome (facoltativo)", key="a_nome_v2")
    with c2: a_eta  = st.number_input("Eta", 0, 120, 0, key="a_eta_v2", format="%d")

    # Anamnesi in 2 colonne
    with st.expander("Anamnesi clinica", expanded=False):
        ac1,ac2 = st.columns(2)
        with ac1:
            audiom    = st.radio("Controllo audiometrico ultimi 24 mesi", ["Si","No","Non so"], index=1, key="a_audiom_v2", horizontal=True)
            acufeni   = st.radio("Acufeni", ["Si","No","Occasionali"], index=1, key="a_acuf_v2", horizontal=True)
            iperacusia = st.radio("Iperacusia", ["Si","No","Occasionale"], index=1, key="a_iper_v2", horizontal=True)
        with ac2:
            vertigini = st.radio("Vertigini", ["Si","No","Occasionali"], index=1, key="a_vert_v2", horizontal=True)
            protesi   = st.radio("Protesi / impianto", ["No","Protesi","Impianto"], index=0, key="a_prot_v2", horizontal=True)
            rumore    = st.radio("Esposizione rumore", ["Regolare","Occasionale","No"], index=2, key="a_rum_v2", horizontal=True)
        an1,an2 = st.columns(2)
        with an1:
            an_otiti = st.checkbox("Otiti ricorrenti", key="an_ot_v2")
            an_chir  = st.checkbox("Interventi chirurgici ORL", key="an_ch_v2")
        with an2:
            an_trauma   = st.checkbox("Trauma cranico", key="an_tr_v2")
            an_sinusiti = st.checkbox("Infezioni ORL ricorrenti", key="an_si_v2")

    st.markdown("---")
    st.markdown("**Checklist — 12 domande** (2 colonne):")

    opts = ["Presente","Assente"]
    answers = []

    # Domande in 2 colonne
    col_sx, col_dx = st.columns(2)
    for idx, (n, inv, q_auto, q_fam) in enumerate(SCAPA_ITEMS):
        domanda = q_fam if is_fam else q_auto
        inv_tag = " *(invertito)*" if inv else ""
        col = col_sx if idx < 6 else col_dx
        val = col.radio(
            f"Q{n}. {domanda}{inv_tag}",
            opts, index=None, key=f"sq_{n}_v2", horizontal=True
        )
        answers.append(val)

    # Calcolo
    st.markdown("---")
    score = 0
    answered = sum(1 for v in answers if v is not None)
    for i, (_, inv, _, _) in enumerate(SCAPA_ITEMS):
        v = answers[i]
        if v is None: continue
        if not inv and v == "Presente": score += 1
        elif inv and v == "Assente":    score += 1

    if answered == 12:
        if score <= 3:   cls, col_c = "Nella norma", "green"
        elif score <= 6: cls, col_c = "Lieve", "orange"
        elif score <= 9: cls, col_c = "Moderato", "orange"
        else:            cls, col_c = "Significativo", "red"
    else:
        cls, col_c = "—", "gray"

    m1,m2,m3 = st.columns(3)
    m1.metric("Punteggio", f"{score}/12" + ("*" if answered<12 else ""))
    m2.metric("% difficolta", f"{round(score/12*100)}%" if answered==12 else "—")
    m3.metric("Livello", cls)
    if answered < 12:
        st.caption(f"Risposte mancanti: {12-answered}")

    nota = st.text_input("Note SCAP-A", key="a_note_v2")
    if st.button("Salva SCAP-A", type="primary", key="a_save_v2"):
        dati = {"chi":chi,"nome":a_nome,"eta":int(a_eta) if a_eta else None,
                "risposte":answers}
        if _salva(conn, paz_id, "SCAP-A", dati, score, cls, operatore, nota):
            st.success(f"SCAP-A salvato — {score}/12 ({cls})")

# ─────────────────────────────────────────────────────────────────────────────
# Tab 3: Calibrazione cuffie
# ─────────────────────────────────────────────────────────────────────────────

_CAL_CONSOLE_HTML = r"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
*{box-sizing:border-box;margin:0;padding:0;font-family:system-ui,sans-serif}
body{padding:8px;background:#f8f7f4;color:#1a1a1a}
.card{background:#fff;border:1px solid #d4cec5;border-radius:10px;padding:12px 16px}
.freq{font-size:28px;font-weight:600;color:#1d9e75;text-align:center;line-height:1}
.sub{font-size:11px;color:#8a8a8a;text-align:center;margin:3px 0 10px}
button{font-family:inherit;font-size:16px;padding:12px;border-radius:8px;border:1.5px solid #1d9e75;background:#1d9e75;color:#fff;cursor:pointer;width:100%}
button.off{background:#fff;color:#0f6e56}
button.on{background:#c0392b;border-color:#c0392b;color:#fff}
.hint{font-size:10.5px;color:#8a8a8a;margin-top:9px;text-align:center;line-height:1.4}
</style></head><body>
<div class="card">
  <div class="freq">__FREQLBL__</div>
  <div class="sub">Orecchio __EAR__ &middot; livello __LEVEL__ dB HL</div>
  <button class="off" id="btn" onclick="toggle()">&#9654;&nbsp; Avvia tono continuo</button>
  <div class="hint">Tieni il fonometro al centro del padiglione, leggi i dB(A) stabili,<br>poi ferma il tono e inserisci il valore qui sotto.</div>
</div>
<script>
var FREQ=__FREQ__, PAN=__PAN__, LEVEL=__LEVEL__;
var actx=null, osc=null, g=null, playing=false;
function getCtx(){if(!actx)actx=new(window.AudioContext||window.webkitAudioContext)();if(actx.state==='suspended')actx.resume();return actx;}
function start(){
  var ctx=getCtx();
  var amp=Math.pow(10,(LEVEL-90)/20)*0.85;amp=Math.max(0.0008,Math.min(0.95,amp));
  osc=ctx.createOscillator();g=ctx.createGain();var p=ctx.createStereoPanner();
  p.pan.value=PAN;osc.frequency.value=FREQ;osc.type='sine';
  g.gain.setValueAtTime(0,ctx.currentTime);g.gain.linearRampToValueAtTime(amp,ctx.currentTime+0.06);
  osc.connect(g);g.connect(p);p.connect(ctx.destination);osc.start();playing=true;
  var b=document.getElementById('btn');b.textContent='\u25A0  Ferma tono';b.className='on';
}
function stop(){
  try{var ctx=getCtx();if(g)g.gain.linearRampToValueAtTime(0,ctx.currentTime+0.06);if(osc)osc.stop(ctx.currentTime+0.12);}catch(e){}
  osc=null;g=null;playing=false;
  var b=document.getElementById('btn');b.textContent='\u25B6  Avvia tono continuo';b.className='off';
}
function toggle(){if(playing)stop();else start();}
</script></body></html>"""



# ── Da dB SPL letti al fonometro a dB HL ─────────────────────────────
# Lo zero audiometrico non è lo zero fisico: 0 dB HL corrisponde a una
# pressione sonora diversa a ogni frequenza, perché l'orecchio umano non
# è ugualmente sensibile. I valori qui sotto (RETSPL — Reference
# Equivalent Threshold SPL) sono quelli normativi per tipo di cuffia:
#   dB HL = dB SPL misurato − RETSPL(frequenza)
# Senza questa conversione il numero mostrato non è dB HL, ed è per
# questo che i livelli sembrano "bassi": a 125 Hz servono 45 dB SPL per
# fare 0 dB HL con una cuffia sovraurale.
RETSPL = {
    # ISO 389-1 — sovraurali tipo TDH-39, cuscinetto su padiglione
    "sovraurale": {125: 45.0, 250: 25.5, 500: 11.5, 750: 8.0, 1000: 7.0,
                   1500: 6.5, 2000: 9.0, 3000: 10.0, 4000: 9.5,
                   6000: 15.5, 8000: 13.0},
    # ISO 389-8 — circumaurali tipo HDA200, padiglione racchiuso
    "circumaurale": {125: 30.5, 250: 18.0, 500: 11.0, 750: 6.0, 1000: 5.5,
                     1500: 5.5, 2000: 4.5, 3000: 2.5, 4000: 9.5,
                     6000: 17.0, 8000: 17.5},
    # ISO 389-2 — auricolari a inserzione tipo ER-3A
    "inserzione": {125: 26.0, 250: 14.0, 500: 5.5, 750: 2.0, 1000: 0.0,
                   1500: 2.0, 2000: 3.0, 3000: 3.5, 4000: 5.5,
                   6000: 2.0, 8000: 0.0},
}

ETICHETTE_TRASDUTTORE = {
    "sovraurale": "Sovraurale (cuscinetto appoggiato sull'orecchio)",
    "circumaurale": "Circumaurale (padiglione racchiuso — la maggior parte delle cuffie da studio)",
    "inserzione": "Auricolari a inserzione (in-ear)",
}


def _retspl(tipo, freq):
    """RETSPL alla frequenza indicata; interpola se la frequenza non è in tabella."""
    tab = RETSPL.get(tipo) or RETSPL["circumaurale"]
    if freq in tab:
        return tab[freq]
    note = sorted(tab)
    if freq <= note[0]:
        return tab[note[0]]
    if freq >= note[-1]:
        return tab[note[-1]]
    for a, b in zip(note, note[1:]):
        if a <= freq <= b:
            q = (freq - a) / (b - a)
            return tab[a] + q * (tab[b] - tab[a])
    return 0.0


def _ui_calibrazione(conn):
    st.subheader("Calibrazione cuffie")
    st.caption("Misura l'uscita reale delle cuffie con un fonometro e salva l'offset globale")
    ss = st.session_state
    import streamlit.components.v1 as _sc

    with st.expander("Requisiti prima di iniziare", expanded=False):
        st.markdown(
            "- Cuffie collegate, **volume del PC al massimo**\n"
            "- EQ di sistema e \"audio enhancer\" **disattivati**\n"
            "- Fonometro impostato su **ponderazione C oppure Z (flat)**, "
            "risposta **slow**\n"
            "- Stanza silenziosa\n"
            "- Microfono al **centro del padiglione**, premuto leggermente per sigillare")
        st.warning(
            "**Non usare la ponderazione A.** La curva A attenua di proposito i "
            "gravi (−16 dB a 125 Hz, −8,6 a 250) per imitare la sensibilità "
            "dell'orecchio a basso volume: applicarla qui significa misurare "
            "soglie sbagliate di quindici decibel proprio dove la cuffia è più "
            "debole. Serve la pressione reale: C o Z.")
        st.caption(
            "Nota onesta sui limiti: una calibrazione a norma si fa con orecchio "
            "artificiale e accoppiatore (IEC 60318). Un fonometro appoggiato al "
            "padiglione dà una stima utile e ripetibile per uso funzionale — che "
            "è lo scopo qui — non un certificato metrologico.")

    _tipo_cuffia = st.selectbox(
        "Tipo di cuffia", list(RETSPL.keys()),
        format_func=lambda k: ETICHETTE_TRASDUTTORE[k],
        index=1, key="cal_tipo_trasd",
        help="Determina i valori RETSPL con cui la pressione misurata diventa dB HL.")
    ss["cal_tipo_trasduttore"] = _tipo_cuffia

    c1, c2, c3 = st.columns(3)
    with c1:
        cf = st.selectbox("Frequenza", FREQS_TON,
                          format_func=lambda f: f"{f//1000}k Hz" if f >= 1000 else f"{f} Hz",
                          key="cal_f")
    with c2:
        ce = st.selectbox("Orecchio", ["OD - Destro", "OS - Sinistro"], key="cal_ear")
    with c3:
        level = st.number_input("Livello presentato (dB HL)", 50, 90, 80, 5, key="cal_level",
                                help="Livello a cui la console emette il tono. Usa 80-90 per leggere bene il fonometro.")
    ce_code = "OD" if "OD" in ce else "OS"
    pan = 0.9 if ce_code == "OD" else -0.9
    flbl = f"{cf//1000}k Hz" if cf >= 1000 else f"{cf} Hz"

    console = (_CAL_CONSOLE_HTML
               .replace("__FREQ__", str(int(cf)))
               .replace("__FREQLBL__", flbl)
               .replace("__EAR__", ce_code)
               .replace("__PAN__", str(pan))
               .replace("__LEVEL__", str(int(level))))
    _sc.html(console, height=210)

    # Inserimento misura (nativo → salva davvero)
    if "cal_misure" not in ss:
        ss["cal_misure"] = {}  # "freq_ear" -> {"measured": x, "level": y}
    m1, m2 = st.columns([2, 1])
    with m1:
        measured = st.number_input(
            f"dB SPL letto sul fonometro (pond. C o Z) — {flbl} {ce_code}",
            20, 130, int(level), 1, key="cal_meas")
        _atteso = int(round(level + _retspl(_tipo_cuffia, cf)))
        st.caption(f"Con questa cuffia, {int(level)} dB HL a {flbl} dovrebbe leggere "
                   f"circa **{_atteso} dB SPL** (RETSPL {_retspl(_tipo_cuffia, cf):.1f}).")
    with m2:
        st.write("")
        st.write("")
        if st.button("Registra misura", use_container_width=True, key="cal_reg"):
            _off = int(round((level + _retspl(_tipo_cuffia, cf)) - measured))
            ss["cal_misure"][f"{cf}_{ce_code}"] = {
                "measured": int(measured), "level": int(level),
                "freq": int(cf), "tipo": _tipo_cuffia, "offset": _off}
            st.success(f"Registrata: {flbl} {ce_code} → letto {int(measured)} dB SPL · "
                       f"scarto {_off:+d} dB da correggere")

    # ── Misure registrate, frequenza per frequenza ──────────────────
    # La correzione resta legata alla singola frequenza. Mediarla su tutta
    # la banda, come si faceva prima, butta via proprio il dato raccolto:
    # nessuna cuffia ha risposta piatta, e lo scarto fra 125 Hz e 4 kHz
    # arriva facilmente a quindici o venti decibel.
    def _off_misura(v):
        if "offset" in v:
            return int(v["offset"])
        return int(v["level"] - v["measured"])

    if ss["cal_misure"]:
        st.markdown("**Curva di correzione misurata**")
        _righe_cal = []
        for k, v in sorted(ss["cal_misure"].items(), key=lambda x: (x[0].split("_")[1], int(x[0].split("_")[0]))):
            _f, _e = k.split("_")
            _righe_cal.append({
                "Frequenza": f"{int(_f)//1000}k" if int(_f) >= 1000 else _f,
                "Orecchio": _e,
                "Letto (dB SPL)": v["measured"],
                "Correzione": f"{_off_misura(v):+d} dB",
            })
        st.dataframe(pd.DataFrame(_righe_cal), hide_index=True, use_container_width=True)

        _mancanti = [f for f in FREQS_TON
                     if not any(k.startswith(f"{f}_") for k in ss["cal_misure"])]
        if _mancanti:
            st.caption("Frequenze non ancora misurate (useranno la correzione "
                       "interpolata dalle vicine): "
                       + ", ".join(f"{f//1000}k" if f >= 1000 else str(f) for f in _mancanti))

        if st.button("Azzera misure", key="cal_clear"):
            ss["cal_misure"] = {}
            st.rerun()

    od = [_off_misura(v) for k, v in ss["cal_misure"].items() if k.endswith("_OD")]
    os_ = [_off_misura(v) for k, v in ss["cal_misure"].items() if k.endswith("_OS")]
    off_od = round(sum(od) / len(od)) if od else 0
    off_os = round(sum(os_) / len(os_)) if os_ else 0

    st.divider()
    _studio_id = ss.get("studio_id", 1)

    # ── Cuffie già calibrate ─────────────────────────────────────────
    _profili = _elenco_profili_cuffie(conn, _studio_id)
    if _profili:
        st.markdown("**Cuffie calibrate**")
        _nomi = [p["nome"] for p in _profili]
        _attivo = ss.get("cal_profilo_globale", {}).get("nome")
        pc1, pc2, pc3 = st.columns([3, 1, 1])
        with pc1:
            _sel = st.selectbox(
                "Cuffia in uso", _nomi,
                index=_nomi.index(_attivo) if _attivo in _nomi else 0,
                key="cal_profilo_sel", label_visibility="collapsed")
        _p = next(p for p in _profili if p["nome"] == _sel)
        with pc2:
            if st.button("Usa questa", key="cal_usa", use_container_width=True,
                         type="primary" if _sel != _attivo else "secondary"):
                ss["cal_profilo_globale"] = {
                    "nome": _p["nome"], "brand": _p.get("marca", ""),
                    "model": _p.get("modello", ""),
                    "offset_od": int(_p.get("offset_od") or 0),
                    "offset_os": int(_p.get("offset_os") or 0),
                    "misure": _p.get("misure") or {},
                }
                st.rerun()
        with pc3:
            if st.button("Elimina", key="cal_del", use_container_width=True):
                _elimina_profilo_cuffie(conn, _studio_id, _sel)
                if _attivo == _sel:
                    ss.pop("cal_profilo_globale", None)
                st.rerun()
        st.caption(f"«{_p['nome']}» — {_p.get('marca','')} {_p.get('modello','')} · "
                   f"OD {int(_p.get('offset_od') or 0):+d} dB · "
                   f"OS {int(_p.get('offset_os') or 0):+d} dB")
        st.divider()

    # ── Salva la calibrazione appena misurata ────────────────────────
    st.markdown("**Salva questa calibrazione**")
    prev = ss.get("cal_profilo_globale", {})
    cc1, cc2, cc3 = st.columns(3)
    brand = cc1.text_input("Marca cuffie", prev.get("brand", ""), key="cal_brand")
    model = cc2.text_input("Modello", prev.get("model", ""), key="cal_model")
    cc3.metric("Offset OD / OS", f"{off_od:+d} / {off_os:+d} dB")

    _nome_sugg = (f"{brand} {model}".strip() or "Cuffia senza nome")
    cn1, cn2 = st.columns([3, 1])
    with cn1:
        nome_prof = st.text_input(
            "Nome con cui ritrovarla", _nome_sugg, key="cal_nome_prof",
            help="Se in studio hai più cuffie, dai a ognuna un nome riconoscibile "
                 "(es. «Sennheiser studio 1», «Cuffia bambini»).")
    with cn2:
        st.write("")
        st.write("")
        _salva = st.button("💾 Salva", type="primary", key="cal_save",
                           use_container_width=True)

    if _salva:
        if not nome_prof.strip():
            st.warning("Dai un nome alla cuffia prima di salvare.")
        elif _salva_profilo_cuffie(conn, _studio_id, nome_prof.strip(), brand,
                                    model, off_od, off_os, dict(ss["cal_misure"])):
            ss["cal_profilo_globale"] = {
                "nome": nome_prof.strip(), "brand": brand, "model": model,
                "offset_od": off_od, "offset_os": off_os,
                "misure": dict(ss["cal_misure"]),
            }
            st.success(f"«{nome_prof.strip()}» salvata — OD {off_od:+d} dB · OS {off_os:+d} dB. "
                       "Resta nel database: non va rifatta a ogni sessione.")
            st.rerun()

    profilo = ss.get("cal_profilo_globale")
    if profilo:
        st.info(
            f"Attiva nel Test tonale: **{profilo.get('nome') or profilo.get('brand','')}** — "
            f"OD {profilo.get('offset_od',0):+d} dB · OS {profilo.get('offset_os',0):+d} dB")


# ── Profili di calibrazione cuffie, salvati sul database ─────────────
# Prima il profilo viveva solo in st.session_state: bastava un riavvio
# dell'app o una sessione scaduta e la calibrazione spariva, costringendo
# a rifarla da capo. Ora sta in tabella, e se ne possono tenere diversi —
# uno per ogni cuffia usata in studio — scegliendo di volta in volta
# quale è attivo.

def _assicura_tabella_cuffie(conn):
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS calibrazioni_cuffie_studio (
                id          BIGSERIAL PRIMARY KEY,
                studio_id   BIGINT NOT NULL DEFAULT 1,
                nome        TEXT NOT NULL,
                marca       TEXT,
                modello     TEXT,
                offset_od   INT NOT NULL DEFAULT 0,
                offset_os   INT NOT NULL DEFAULT 0,
                misure      JSONB,
                creato_il   TIMESTAMPTZ NOT NULL DEFAULT now(),
                UNIQUE (studio_id, nome)
            );
        """)
        conn.commit()
        return True
    except Exception:
        try: conn.rollback()
        except Exception: pass
        return False


def _salva_profilo_cuffie(conn, studio_id, nome, marca, modello, off_od, off_os, misure):
    if not _assicura_tabella_cuffie(conn):
        return False
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO calibrazioni_cuffie_studio
                (studio_id, nome, marca, modello, offset_od, offset_os, misure)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (studio_id, nome) DO UPDATE SET
                marca = EXCLUDED.marca, modello = EXCLUDED.modello,
                offset_od = EXCLUDED.offset_od, offset_os = EXCLUDED.offset_os,
                misure = EXCLUDED.misure, creato_il = now();
        """, (studio_id, nome, marca, modello, int(off_od), int(off_os),
              json.dumps(misure or {})))
        conn.commit()
        return True
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        st.error(f"Errore salvataggio profilo: {e}")
        return False


def _elenco_profili_cuffie(conn, studio_id):
    if not _assicura_tabella_cuffie(conn):
        return []
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT nome, marca, modello, offset_od, offset_os, misure
              FROM calibrazioni_cuffie_studio
             WHERE studio_id = %s ORDER BY nome;
        """, (studio_id,))
        righe = cur.fetchall() or []
    except Exception:
        try: conn.rollback()
        except Exception: pass
        return []
    fuori = []
    for r in righe:
        if hasattr(r, "get"):
            fuori.append(dict(r))
        else:
            fuori.append({"nome": r[0], "marca": r[1], "modello": r[2],
                          "offset_od": r[3], "offset_os": r[4], "misure": r[5]})
    return fuori


def _elimina_profilo_cuffie(conn, studio_id, nome):
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM calibrazioni_cuffie_studio "
                    "WHERE studio_id = %s AND nome = %s;", (studio_id, nome))
        conn.commit()
        return True
    except Exception:
        try: conn.rollback()
        except Exception: pass
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Tab 4: Test Tonale
# ─────────────────────────────────────────────────────────────────────────────

_TONALE_CONSOLE_HTML = r"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
*{box-sizing:border-box;margin:0;padding:0;font-family:system-ui,sans-serif}
body{padding:8px;background:#f8f7f4;color:#1a1a1a}
.card{background:#fff;border:1px solid #d4cec5;border-radius:10px;padding:12px 16px}
.freq{font-size:30px;font-weight:600;color:#1d9e75;text-align:center;line-height:1}
.sub{font-size:11px;color:#8a8a8a;text-align:center;margin:2px 0 8px}
.db{font-size:46px;font-weight:600;text-align:center;line-height:1.05}
.dblbl{font-size:11px;color:#8a8a8a;text-align:center;margin-bottom:8px}
input[type=range]{width:100%;accent-color:#1d9e75;margin:2px 0}
button{font-family:inherit;font-size:13px;padding:7px 10px;border-radius:8px;border:1.5px solid #d4cec5;background:#fff;color:#4a4a4a;cursor:pointer}
button:hover{background:#e1f5ee;border-color:#1d9e75;color:#0f6e56}
button.primary{background:#1d9e75;border-color:#1d9e75;color:#fff;font-size:16px;padding:11px;width:100%;margin-top:8px}
.row{display:flex;gap:6px;margin-top:8px}
.row button{flex:1}
.hint{font-size:10.5px;color:#8a8a8a;margin-top:8px;text-align:center;line-height:1.4}
</style></head><body>
<div class="card">
  <div class="freq">__FREQLBL__</div>
  <div class="sub">Orecchio __EAR__ &middot; Via __VIA__ &middot; durata __DUR__s</div>
  <div class="db" id="dbVal">__DBINIT__</div>
  <div class="dblbl">dB HL &middot; offset cuffie __CALOFF__ dB</div>
  <input type="range" id="dbSlider" min="-20" max="__DBMAX__" step="5" value="__DBINIT__" oninput="setDb(this.value)">
  <button class="primary" onclick="play()">&#9654;&nbsp; Invia tono &nbsp;<small style="opacity:.8">[Spazio]</small></button>
  <div class="row">
    <button onclick="step(-5)">&minus;5</button>
    <button onclick="step(-1)">&minus;1</button>
    <button onclick="step(1)">+1</button>
    <button onclick="step(5)">+5</button>
    <button onclick="stopTone()">&#9632; Stop</button>
  </div>
  <div class="hint">Cerca la soglia qui: l'audio &egrave; istantaneo, nessuna ricarica.<br>Trovata la soglia, registra il valore con &laquo;Valida soglia&raquo; qui sotto.</div>
</div>
<script>
var FREQ=__FREQ__, PAN=__PAN__, DUR=__DUR__, CALOFF=__CALOFFNUM__;
var db=__DBINIT__, actx=null, curO=null, curG=null;
function getCtx(){if(!actx)actx=new(window.AudioContext||window.webkitAudioContext)();if(actx.state==='suspended')actx.resume();return actx;}
function render(){document.getElementById('dbVal').textContent=db;var s=document.getElementById('dbSlider');if(s&&parseInt(s.value)!==db)s.value=db;}
function setDb(v){db=parseInt(v);render();}
function step(d){db=Math.max(-20,Math.min(90,db+d));render();}
function stopTone(){try{var t=getCtx().currentTime;if(curG){curG.gain.cancelScheduledValues(t);curG.gain.setTargetAtTime(0,t,0.01);}if(curO){curO.stop(t+0.05);}}catch(e){}curO=null;curG=null;}
function play(){
  var ctx=getCtx();stopTone();
  var dbEff=db+CALOFF;
  var amp=Math.pow(10,(dbEff-90)/20)*0.85;amp=Math.max(0.0008,Math.min(0.95,amp));
  var o=ctx.createOscillator(),g=ctx.createGain(),p=ctx.createStereoPanner();
  p.pan.value=PAN;o.frequency.value=FREQ;o.type='sine';
  var t0=ctx.currentTime;
  g.gain.setValueAtTime(0,t0);
  g.gain.linearRampToValueAtTime(amp,t0+0.02);
  g.gain.setValueAtTime(amp,t0+DUR-0.05);
  g.gain.linearRampToValueAtTime(0,t0+DUR);
  o.connect(g);g.connect(p);p.connect(ctx.destination);
  o.start();o.stop(t0+DUR+0.02);
  curO=o;curG=g;
}
document.addEventListener('keydown',function(e){
  if(e.code==='Space'){e.preventDefault();play();}
  else if(e.code==='ArrowUp'){e.preventDefault();step(5);}
  else if(e.code==='ArrowDown'){e.preventDefault();step(-5);}
});
render();
</script></body></html>"""


def _carica_ultimo_audiogramma(conn, paz_id):
    """Ultimo audiogramma CON ALMENO UNA SOGLIA reale per il paziente
    (salta eventuali salvataggi vuoti/accidentali più recenti)."""
    try:
        cur = conn.cursor()
        ph1 = _ph(1, conn)
        cur.execute(
            "SELECT dati_json FROM diagnostica_uditiva WHERE paziente_id = " + ph1 +
            " AND tipo = 'Audiogramma' ORDER BY data_esame DESC, id DESC LIMIT 20",
            (paz_id,))
        for (raw,) in cur.fetchall():
            if not raw:
                continue
            try:
                d = json.loads(raw)
            except Exception:
                continue
            liste = [d.get("od_ac") or [], d.get("os_ac") or [],
                    d.get("od_bc") or [], d.get("os_bc") or []]
            if any(v is not None for lst in liste for v in lst):
                return d
    except Exception:
        pass
    return None


# Ordine clinico standard di somministrazione (dalle centrali alle estreme)
FREQ_ORDER_AUTO = [1000, 2000, 4000, 8000, 500, 250, 125, 750, 1500, 3000, 6000]


# ── Parametri del metodo ascendente (Tomatis) ────────────────────────
# Si parte sotto la soglia attesa e si sale: la soglia è il primo livello
# udito. Ripetendo la prova e prendendo il valore PIÙ ALTO si ottiene il
# livello a cui il suono è percepito con chiarezza in tutte le
# presentazioni — che è ciò che serve per calcolare il delta EQ, non il
# minimo appena rilevabile.
_TT_PARTENZA   = 0    # dB HL di partenza di ogni prova ascendente
_TT_PASSO      = 5    # incremento dopo ogni "non sentito"
_TT_RIPARTENZA = 15   # di quanto si scende per ricominciare la prova
_TT_PROVE      = 2    # prove ascendenti per frequenza
_TT_MIN        = -20
_TT_MAX        = 120


def _ui_test_tonale(conn, paz_id, operatore):
    st.subheader("Test tonale audiometrico")
    st.caption("Via aerea (AC) e ossea (BC) · WebAudio istantaneo · Metodo Hipérion · Curva Tomatis")

    import streamlit.components.v1 as _sc
    ss = st.session_state

    # ── Cuffia calibrata: si riprende dal database all'apertura ─────────────
    # Se non lo facessimo, dopo ogni riavvio dell'app il test partirebbe
    # senza offset e le soglie sarebbero falsate senza che nulla lo segnali.
    if "cal_profilo_globale" not in ss:
        _prof = _elenco_profili_cuffie(conn, ss.get("studio_id", 1))
        if len(_prof) == 1:
            _p = _prof[0]
            ss["cal_profilo_globale"] = {
                "nome": _p["nome"], "brand": _p.get("marca", ""),
                "model": _p.get("modello", ""),
                "offset_od": int(_p.get("offset_od") or 0),
                "offset_os": int(_p.get("offset_os") or 0),
                "misure": _p.get("misure") or {},
            }
        elif len(_prof) > 1:
            st.warning("Più cuffie calibrate e nessuna attiva: scegline una in "
                       "**Calibrazione cuffie**, altrimenti il test gira senza offset.")

    # ── Ricarica automatica dell'ultimo audiogramma di QUESTO paziente ───────
    # (evita che le soglie di un paziente restino a video passando a un altro,
    # e fa sì che tornando sul paziente si veda subito l'ultimo esame fatto)
    if ss.get("_tt_loaded_for") != paz_id:
        for k in list(ss.keys()):
            if k.startswith("tt_soglie_") or k == "tt_tomatis_v3":
                del ss[k]
        ultimo = _carica_ultimo_audiogramma(conn, paz_id)
        if ultimo:
            if ultimo.get("od_ac"): ss["tt_soglie_OD_ac_v3"] = {i: v for i, v in enumerate(ultimo["od_ac"]) if v is not None}
            if ultimo.get("os_ac"): ss["tt_soglie_OS_ac_v3"] = {i: v for i, v in enumerate(ultimo["os_ac"]) if v is not None}
            if ultimo.get("od_bc"): ss["tt_soglie_OD_bc_v3"] = {i: v for i, v in enumerate(ultimo["od_bc"]) if v is not None}
            if ultimo.get("os_bc"): ss["tt_soglie_OS_bc_v3"] = {i: v for i, v in enumerate(ultimo["os_bc"]) if v is not None}
            if ultimo.get("tomatis"): ss["tt_tomatis_v3"] = list(ultimo["tomatis"])
            st.info("📥 Caricato automaticamente l'ultimo audiogramma salvato per questo paziente.")
        ss["_tt_loaded_for"] = paz_id

    modalita = st.radio("Modalità di ricerca soglia", ["🤖 Automatica (assistita)", "🖱️ Manuale"],
                        horizontal=True, key="tt_modalita_v3")

    # ── Grafico SEMPRE in cima e sempre aggiornato (anche per esami già
    # salvati, appena apri la scheda, e live mentre confermi nuove soglie) ───
    _od_ac_live = [ss.get("tt_soglie_OD_ac_v3", {}).get(i) for i in range(11)]
    _os_ac_live = [ss.get("tt_soglie_OS_ac_v3", {}).get(i) for i in range(11)]
    _od_bc_live = [ss.get("tt_soglie_OD_bc_v3", {}).get(i) for i in range(11)]
    _os_bc_live = [ss.get("tt_soglie_OS_bc_v3", {}).get(i) for i in range(11)]
    _tom_live = ss.get("tt_tomatis_v3", list(TOMATIS_STD))
    if any(v is not None for v in _od_ac_live + _os_ac_live + _od_bc_live + _os_bc_live):
        st.markdown("**📈 Audiogramma** (aggiornato in tempo reale)")
        _disegna_audiogramma(_od_ac_live, _os_ac_live, _tom_live, _od_bc_live, _os_bc_live)
    else:
        st.caption("Il grafico comparirà qui appena confermi la prima soglia.")
    st.divider()

    # ── Parametri di stimolo (nativi: cambiano di rado) ──────────────────────
    c1, c2, c3 = st.columns(3)
    with c1: ear = st.selectbox("Orecchio", ["OD - Destro", "OS - Sinistro"], key="tt_ear_v3")
    with c2: via = st.selectbox("Via", ["AC - Aerea", "BC - Ossea"], key="tt_via_v3")
    with c3: dur_str = st.select_slider("Durata tono", ["1.0", "1.5", "2.0", "2.5", "3.0"],
                                        value="2.0", key="tt_dur_v3")
    ear_code = "OD" if "OD" in ear else "OS"
    via_code = "ac" if "AC" in via else "bc"
    dur = float(dur_str)

    if modalita.startswith("🤖"):
        st.markdown("##### Ricerca automatica della soglia — metodo ascendente (Tomatis)")
        st.caption("Si parte da un livello inudibile e si sale di 5 dB per volta finché il paziente "
                   "sente: quella è la soglia ascendente. La prova si ripete due volte partendo più "
                   "in basso. **Si adotta il valore più alto fra le prove**, non il minimo udibile: "
                   "è la convenzione Tomatis, dove conta il livello a cui il suono è percepito con "
                   "chiarezza, non quello appena rilevabile. La soglia proposta resta modificabile "
                   "prima di confermarla.")
        auto_key = f"tt_auto_{ear_code}_{via_code}"
        if auto_key not in ss or ss[auto_key].get("freq_seq_i") is None:
            ss[auto_key] = {"freq_seq_i": 0, "level": _TT_PARTENZA,
                            "prove": [], "found": None}
        auto = ss[auto_key]
        fi = FREQS_TON.index(FREQ_ORDER_AUTO[auto["freq_seq_i"] % len(FREQ_ORDER_AUTO)])
        cur_f = FREQS_TON[fi]
        st.progress((auto["freq_seq_i"] % len(FREQ_ORDER_AUTO)) / len(FREQ_ORDER_AUTO),
                    text=f"Frequenza {auto['freq_seq_i'] % len(FREQ_ORDER_AUTO) + 1} di {len(FREQ_ORDER_AUTO)}")
        db_init = int(auto["level"])
        _n_prova = len(auto.get("prove", [])) + 1
        if auto.get("prove"):
            st.caption(f"Prova {_n_prova} di {_TT_PROVE} · già rilevate: "
                       + ", ".join(f"{v} dB" for v in auto["prove"]))
        else:
            st.caption(f"Prova {_n_prova} di {_TT_PROVE} · si sale di "
                       f"{_TT_PASSO} dB finché il paziente sente")
    else:
        cur_f = st.selectbox("Frequenza", FREQS_TON,
                             format_func=lambda f: str(f) if f < 1000 else f"{f//1000}k Hz",
                             key="tt_freq_v3")
        fi = FREQS_TON.index(cur_f)

    # Offset di calibrazione della FREQUENZA in corso, non la media di banda.
    def _offset_calibrato(profilo, orecchio, freq):
        if not profilo:
            return 0
        misure = profilo.get("misure") or {}
        punti = []
        for chiave, v in misure.items():
            try:
                f_txt, e_txt = str(chiave).split("_")
                if e_txt != orecchio:
                    continue
                off = v.get("offset")
                if off is None:
                    off = v.get("level", 0) - v.get("measured", 0)
                punti.append((int(f_txt), int(off)))
            except Exception:
                continue
        if not punti:
            # Nessuna misura per frequenza: resta la media salvata nel profilo.
            return int(profilo.get(f"offset_{orecchio.lower()}", 0) or 0)
        punti.sort()
        if len(punti) == 1 or freq <= punti[0][0]:
            return punti[0][1]
        if freq >= punti[-1][0]:
            return punti[-1][1]
        for (fa, oa), (fb, ob) in zip(punti, punti[1:]):
            if fa <= freq <= fb:
                q = (freq - fa) / (fb - fa) if fb != fa else 0
                return int(round(oa + q * (ob - oa)))
        return punti[-1][1]

    cal_offset = _offset_calibrato(ss.get("cal_profilo_globale"), ear_code, int(cur_f))
    pan_val = 0.9 if ear_code == "OD" else -0.9

    if modalita.startswith("🤖"):
        db_init = int(auto["level"])
    else:
        db_init = int(ss.get(f"tt_soglie_{ear_code}_{via_code}_v3", {}).get(fi, 30))

    # ── Massimo livello realmente erogabile ─────────────────────────────────
    # Il motore audio mappa 90 dB HL sul fondo scala digitale: oltre non si
    # va, si distorce soltanto. Con la correzione di calibrazione il tetto si
    # sposta — cuffie deboli, che vanno spinte (+dB), arrivano più in basso;
    # cuffie efficienti (−dB) arrivano più in alto. Mostrarlo evita di credere
    # che un "non sentito" a 90 sia una soglia, quando è il limite dell'hardware.
    _FONDO_SCALA_DB = 91
    _max_reale = int(_FONDO_SCALA_DB - cal_offset)
    _max_reale = max(40, min(120, _max_reale))

    # ── Console audio autonoma: AudioContext persistente, zero ricariche ─────
    console = (_TONALE_CONSOLE_HTML
               .replace("__FREQ__", str(int(cur_f)))
               .replace("__FREQLBL__", FLABELS_TON[fi] + " Hz")
               .replace("__EAR__", ear_code)
               .replace("__VIA__", via_code.upper())
               .replace("__PAN__", str(pan_val))
               .replace("__DUR__", str(dur))
               .replace("__CALOFF__", f"{cal_offset:+d}")
               .replace("__CALOFFNUM__", str(cal_offset))
               .replace("__DBMAX__", str(_max_reale))
               .replace("__DBINIT__", str(min(db_init, _max_reale))))
    _sc.html(console, height=340)

    _prof_att = ss.get("cal_profilo_globale") or {}
    if cal_offset:
        st.caption(f"🎧 {_prof_att.get('nome') or _prof_att.get('brand') or 'Cuffia calibrata'} — "
                   f"correzione {cal_offset:+d} dB a {FLABELS_TON[fi]} Hz su {ear_code} "
                   "(propria di questa frequenza, non una media)")
    elif not _prof_att:
        st.caption("⚠️ Nessuna cuffia calibrata: i valori sono relativi all'uscita del "
                   "dispositivo, non a dB HL reali. Calibra in «Calibrazione cuffie».")

    st.caption(f"Massimo erogabile a {FLABELS_TON[fi]} Hz su {ear_code}: "
               f"**{_max_reale} dB HL**" +
               ("" if cal_offset == 0 else
                f" (fondo scala {_FONDO_SCALA_DB} dB meno {cal_offset:+d} dB di correzione)"))
    if _max_reale < 80:
        st.warning(
            f"Oltre {_max_reale} dB HL queste cuffie non vanno: a questa frequenza "
            "il sistema è già al massimo. Un «non sentito» qui indica il limite "
            "dell'apparecchiatura, non necessariamente una soglia del paziente — "
            "per soglie più profonde serve una cuffia più efficiente o un "
            "amplificatore.")

    key_s = f"tt_soglie_{ear_code}_{via_code}_v3"
    if key_s not in ss:
        ss[key_s] = {}

    if modalita.startswith("🤖"):
        bc1, bc2, bc3 = st.columns([1, 1, 1])
        with bc1:
            sentito = st.button("🔊 Ho sentito", type="primary", use_container_width=True, key="tt_auto_yes")
        with bc2:
            non_sentito = st.button("🔇 Non ho sentito", use_container_width=True, key="tt_auto_no")
        with bc3:
            salta = st.button("⏭️ Salta frequenza", use_container_width=True, key="tt_auto_skip")

        if non_sentito:
            # Non sentito: si sale. È l'unico movimento del metodo ascendente.
            auto["level"] = min(_max_reale, auto["level"] + _TT_PASSO)
            if auto["level"] >= _max_reale:
                st.info(f"Raggiunto il massimo erogabile ({_max_reale} dB HL): se il "
                        "paziente non sente, registra «non testabile» invece di una soglia.")
            st.rerun()

        if sentito:
            # Sentito: questa prova ascendente è conclusa, il livello attuale
            # è la sua soglia. Si riparte più in basso per una nuova prova.
            auto["prove"].append(int(auto["level"]))

            if len(auto["prove"]) >= _TT_PROVE:
                # Convenzione Tomatis: fra le prove si prende la PIÙ ALTA,
                # cioè il livello a cui il suono è percepito con chiarezza in
                # tutte le presentazioni — non il minimo appena rilevabile,
                # che sovrastima l'udito utile ai fini dell'equalizzazione.
                soglia_auto = max(auto["prove"])
                ss[key_s][fi] = int(soglia_auto)
                _dettaglio = " / ".join(f"{v} dB" for v in auto["prove"])
                st.success(
                    f"Soglia proposta: {FLABELS_TON[fi]} Hz {ear_code} {via_code.upper()} "
                    f"= {int(soglia_auto)} dB HL — prove: {_dettaglio}, adottata la più alta "
                    "(modificabile qui sotto prima di confermare)")
                auto["freq_seq_i"] += 1
                auto["level"] = _TT_PARTENZA
                auto["prove"] = []
            else:
                # Nuova prova ascendente: si riparte sotto la soglia trovata.
                auto["level"] = max(_TT_MIN, int(auto["level"]) - _TT_RIPARTENZA)
            st.rerun()

        if salta:
            auto["freq_seq_i"] += 1
            auto["level"] = _TT_PARTENZA
            auto["prove"] = []
            st.rerun()

    # ── Inserimento rapido di tutte le frequenze (solo in manuale) ──────────
    # Una frequenza per volta vuol dire undici conferme e undici ricariche
    # per orecchio: qui la griglia le prende tutte insieme, con una sola
    # ricarica alla fine.
    if not modalita.startswith("🤖"):
        with st.expander("⌨️ Inserimento rapido — tutte le frequenze insieme", expanded=False):
            st.caption(f"{ear_code} · via {via_code.upper()} — lascia vuoto ciò che non hai misurato. "
                       "Muoviti con Tab.")
            _riga = {FLABELS_TON[i]: ss[key_s].get(i) for i in range(len(FREQS_TON))}
            _out = st.data_editor(
                pd.DataFrame([_riga]),
                key=f"tt_griglia_{ear_code}_{via_code}",
                hide_index=True, use_container_width=True,
                column_config={
                    lbl: st.column_config.NumberColumn(
                        lbl, min_value=-20, max_value=120, step=5, format="%d")
                    for lbl in FLABELS_TON
                },
            )
            if st.button("✓ Registra tutte", key=f"tt_griglia_ok_{ear_code}_{via_code}",
                         type="primary"):
                _n = 0
                for i, lbl in enumerate(FLABELS_TON):
                    _v = _out.iloc[0][lbl]
                    if pd.isna(_v):
                        ss[key_s].pop(i, None)
                    else:
                        ss[key_s][i] = int(_v)
                        _n += 1
                st.success(f"{_n} soglie registrate su {ear_code} {via_code.upper()}.")
                st.rerun()

    # ── Registrazione / conferma soglia (sempre visibile e modificabile) ─────
    valore_proposto = ss[key_s].get(fi, db_init)
    rc1, rc2 = st.columns([2, 1])
    with rc1:
        soglia = st.number_input(
            f"Soglia — {FLABELS_TON[fi]} Hz {ear_code} {via_code.upper()} (dB HL) · "
            "modificabile col mouse o a tastiera",
            -20, 120, int(valore_proposto), 5, key=f"tt_soglia_in_{fi}_v3")
    with rc2:
        st.write("")
        st.write("")
        if st.button("✓ Conferma soglia", type="primary", use_container_width=True, key="tt_val_v3"):
            ss[key_s][fi] = int(soglia)
            st.success(f"Registrata: {FLABELS_TON[fi]} Hz {ear_code} {via_code.upper()} = {int(soglia)} dB HL")
            _od_bc_auto = [ss.get("tt_soglie_OD_bc_v3", {}).get(i) for i in range(11)]
            _os_bc_auto = [ss.get("tt_soglie_OS_bc_v3", {}).get(i) for i in range(11)]
            _od_ac_auto = [ss.get("tt_soglie_OD_ac_v3", {}).get(i) for i in range(11)]
            _os_ac_auto = [ss.get("tt_soglie_OS_ac_v3", {}).get(i) for i in range(11)]
            _tom_auto = ss.get("tt_tomatis_v3", list(TOMATIS_STD))
            _eq_od_auto = [round(_tom_auto[i] - _od_ac_auto[i], 1) if _od_ac_auto[i] is not None else 0 for i in range(11)]
            _n_auto = sum(1 for v in _od_ac_auto + _os_ac_auto if v is not None)
            _dati_auto = {"od_ac": _od_ac_auto, "os_ac": _os_ac_auto, "od_bc": _od_bc_auto,
                         "os_bc": _os_bc_auto, "tomatis": _tom_auto, "eq_od": _eq_od_auto}
            _salva(conn, paz_id, "Audiogramma", _dati_auto, float(_n_auto), f"{_n_auto} soglie",
                  operatore, ss.get("tt_note_v3", "") or "(salvataggio automatico)")

    # ── Soglie registrate ────────────────────────────────────────────────────
    st.divider()
    st.markdown("**Soglie registrate**")
    sc1, sc2, sc3, sc4 = st.columns(4)
    for col, (ek, vk, label, color) in zip([sc1, sc2, sc3, sc4], [
        ("OD", "ac", "OD AC", "#c0392b"), ("OS", "ac", "OS AC", "#2980b9"),
        ("OD", "bc", "OD BC", "#8e44ad"), ("OS", "bc", "OS BC", "#16a085"),
    ]):
        col.markdown(f"<b style='color:{color};font-size:11px'>{label}</b>", unsafe_allow_html=True)
        soglie = ss.get(f"tt_soglie_{ek}_{vk}_v3", {})
        for fii, v in sorted(soglie.items()):
            col.markdown(
                f"<span style='border:1px solid {color};border-radius:6px;"
                f"padding:1px 5px;font-size:11px;color:{color};"                f"display:inline-block;margin:1px'>{FLABELS_TON[fii]}:{v}</span>",
                unsafe_allow_html=True)

    # ── Curva Tomatis ─────────────────────────────────────────────────────────
    st.divider()
    st.markdown("**Curva Tomatis** (valori target dB HL)")
    if "tt_tomatis_v3" not in ss:
        ss["tt_tomatis_v3"] = list(TOMATIS_STD)
    tc = st.columns(11)
    for i, lbl in enumerate(FLABELS_TON):
        v = tc[i].number_input(lbl, -30, 10, int(ss["tt_tomatis_v3"][i]), 1, key=f"tt_tm{i}_v3")
        ss["tt_tomatis_v3"][i] = int(v)
    if st.button("Ripristina standard", key="tt_tm_rst_v3"):
        ss["tt_tomatis_v3"] = list(TOMATIS_STD)

    # ── Grafico + EQ ──────────────────────────────────────────────────────────
    od_ac = [ss.get("tt_soglie_OD_ac_v3", {}).get(i) for i in range(11)]
    os_ac = [ss.get("tt_soglie_OS_ac_v3", {}).get(i) for i in range(11)]
    tom = ss.get("tt_tomatis_v3", list(TOMATIS_STD))

    if any(v is not None for v in od_ac + os_ac):
        st.divider()
        _disegna_audiogramma(od_ac, os_ac, tom)
        eq_od = [round(tom[i] - od_ac[i], 1) if od_ac[i] is not None else None for i in range(11)]
        eq_os = [round(tom[i] - os_ac[i], 1) if os_ac[i] is not None else None for i in range(11)]
        st.markdown("**Delta EQ terapeutico** (Tomatis − soglia paziente)")
        ec = st.columns(11)
        for i, (lbl, vod, vos) in enumerate(zip(FLABELS_TON, eq_od, eq_os)):
            v = vod if vod is not None else vos
            if v is not None:
                cc = "green" if v > 3 else "red" if v < -3 else "orange"
                ec[i].markdown(
                    f"<div style='text-align:center'><b style='color:{cc}'>{v:+.0f}</b>"
                    f"<br><small style='color:#888'>{lbl}</small></div>",
                    unsafe_allow_html=True)

    st.divider()
    nota_ton = st.text_input("Note audiogramma", key="tt_note_v3")
    if st.button("Salva audiogramma", type="primary", key="tt_save_v3"):
        od_bc = [ss.get("tt_soglie_OD_bc_v3", {}).get(i) for i in range(11)]
        os_bc = [ss.get("tt_soglie_OS_bc_v3", {}).get(i) for i in range(11)]
        eq_od2 = [round(tom[i] - od_ac[i], 1) if od_ac[i] is not None else 0 for i in range(11)]
        n = sum(1 for v in od_ac + os_ac if v is not None)
        dati = {"od_ac": od_ac, "os_ac": os_ac, "od_bc": od_bc, "os_bc": os_bc,
                "tomatis": tom, "eq_od": eq_od2}
        if _salva(conn, paz_id, "Audiogramma", dati, float(n), f"{n} soglie", operatore, nota_ton):
            st.success(f"Audiogramma salvato — {n} soglie.")


def _disegna_audiogramma(od, os_, tom, od_bc=None, os_bc=None):
    try:
        import matplotlib; matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(9,4), facecolor="white")
        ax.set_facecolor("white"); ax.set_ylim(90,-20); ax.set_xlim(-0.5,10.5)
        ax.set_xticks(range(11)); ax.set_xticklabels(FLABELS_TON, fontsize=8)
        ax.set_yticks(range(-20,91,10)); ax.set_ylabel("dB HL", fontsize=9)
        ax.axhline(0, color="gray", lw=0.8, ls="--", alpha=0.5)
        ax.grid(True, alpha=0.15, lw=0.5)
        ax.fill_between(range(11),-20,0,alpha=0.04,color="#2d7d6f")
        ax.plot(range(len(tom)),tom,color="#2d7d6f",lw=2,ls="--",label="Tomatis",zorder=3)
        pts_od=[(i,v) for i,v in enumerate(od) if v is not None]
        if pts_od:
            xi,yi=zip(*pts_od); ax.plot(xi,yi,color="#c0392b",lw=1.8,marker="o",ms=6,label="OD AC",zorder=4)
            for x,y in pts_od: ax.text(x,y-4,"O",ha="center",fontsize=9,color="#c0392b",fontweight="bold")
        pts_os=[(i,v) for i,v in enumerate(os_) if v is not None]
        if pts_os:
            xi,yi=zip(*pts_os); ax.plot(xi,yi,color="#2980b9",lw=1.8,marker="x",ms=6,label="OS AC",zorder=4)
            for x,y in pts_os: ax.text(x,y+5,"X",ha="center",fontsize=9,color="#2980b9",fontweight="bold")
        pts_odbc=[(i,v) for i,v in enumerate(od_bc or [])if v is not None]
        if pts_odbc:
            xi,yi=zip(*pts_odbc); ax.scatter(xi,yi,color="#c0392b",marker="<",s=60,label="OD BC",zorder=4)
        pts_osbc=[(i,v) for i,v in enumerate(os_bc or [])if v is not None]
        if pts_osbc:
            xi,yi=zip(*pts_osbc); ax.scatter(xi,yi,color="#2980b9",marker=">",s=60,label="OS BC",zorder=4)
        ax.legend(fontsize=8,loc="lower right"); fig.tight_layout(pad=0.5)
        buf = io.BytesIO(); fig.savefig(buf,format="png",dpi=110,bbox_inches="tight",facecolor="white")
        plt.close(fig); buf.seek(0); st.image(buf, use_container_width=True)
    except Exception as e:
        st.warning(f"Grafico non disponibile: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# Tab 5: Lateralità uditiva
# ─────────────────────────────────────────────────────────────────────────────

LAT_HTML = r"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
*{box-sizing:border-box;margin:0;padding:0;font-family:system-ui,sans-serif}
body{padding:10px;background:#f8f7f4;color:#1a1a1a}
.card{background:#fff;border:1px solid #d4cec5;border-radius:10px;padding:12px 14px;margin-bottom:8px}
h3{font-size:13px;font-weight:500;margin-bottom:3px}
.cap{font-size:11px;color:#8a8a8a;margin-bottom:8px}
button{font-family:inherit;font-size:12px;padding:5px 10px;border-radius:7px;border:1.5px solid #d4cec5;background:#fff;color:#4a4a4a;cursor:pointer}
button:hover{background:#e1f5ee;border-color:#1d9e75;color:#0f6e56}
button.primary{background:#1d9e75;border-color:#1d9e75;color:#fff}
.btn-row{display:flex;gap:6px;margin-top:8px;flex-wrap:wrap}
.fchips{display:flex;flex-wrap:wrap;gap:4px;margin:6px 0}
.fc{padding:3px 8px;border-radius:9px;font-size:11px;cursor:pointer;border:1px solid #d4cec5;background:#f8f7f4;color:#8a8a8a}
.fc.active{background:#1d9e75;border-color:#1d9e75;color:#fff}
.fc.done-od{background:#fdecea;border-color:#c0392b;color:#c0392b}
.fc.done-os{background:#eaf4fb;border-color:#2980b9;color:#2980b9}
.fc.done-b{background:#e1f5ee;border-color:#1d9e75;color:#0f6e56}
.bal-wrap{margin:10px 0}
.bal-track{height:12px;background:#ede9e3;border-radius:6px;position:relative;overflow:hidden;margin:6px 0}
.bal-fill-od{position:absolute;right:50%;height:100%;border-radius:6px 0 0 6px;background:#c0392b;transition:width .2s}
.bal-fill-os{position:absolute;left:50%;height:100%;border-radius:0 6px 6px 0;background:#2980b9;transition:width .2s}
.bal-center{position:absolute;left:50%;top:-2px;width:2px;height:16px;background:#888;transform:translateX(-50%)}
.db-large{font-size:36px;font-weight:600;text-align:center;padding:8px 0}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:8px 0}
.ear-box{background:#f8f7f4;border-radius:8px;padding:10px;text-align:center}
.ear-box .lbl{font-size:10px;font-weight:600;letter-spacing:.05em;text-transform:uppercase;margin-bottom:4px}
.ear-box .val{font-size:22px;font-weight:500}
.status{font-size:12px;padding:5px 9px;border-radius:6px;margin:6px 0}
.ok{background:#e1f5ee;color:#0f6e56}.info{background:#ebf5fb;color:#154360}.warn{background:#fef7ec;color:#7a4f0a}
.lat-bar{height:14px;background:#ede9e3;border-radius:7px;margin:6px 0;overflow:hidden}
.lat-fill{height:100%;border-radius:7px;transition:width .4s,background .4s}
</style></head><body>
<div class="card">
  <h3>Lateralita uditiva di ricezione</h3>
  <p class="cap">Il paziente centra il suono. Invia il tono e regola il balance finche il paziente sente il suono al centro. Valida per ogni frequenza.</p>
  <div style="font-size:11px;color:#8a8a8a;margin-bottom:4px">Frequenza (click per selezionare):</div>
  <div class="fchips" id="freqChips"></div>
  <div style="display:flex;align-items:center;gap:12px;margin:8px 0">
    <div style="flex:1">
      <div style="font-size:11px;color:#8a8a8a;margin-bottom:3px">Volume (dB sopra soglia)</div>
      <input type="range" id="vol" min="5" max="50" value="30" oninput="volV.textContent=this.value+'dB'" style="width:100%;accent-color:#1d9e75">
      <span id="volV" style="font-size:12px;font-weight:500">30dB</span>
    </div>
    <button class="primary" onclick="playLat()" style="padding:10px 18px;font-size:14px">&#9654; Invia tono</button>
  </div>
  <div style="font-size:11px;color:#8a8a8a;margin-bottom:3px">Balance (negativo = SX, positivo = DX)</div>
  <input type="range" id="bal" min="-100" max="100" value="0" oninput="updBal(this.value)" style="width:100%;accent-color:#1d9e75">
  <div class="bal-wrap">
    <div style="display:flex;justify-content:space-between;font-size:10px;color:#8a8a8a;margin-bottom:2px"><span style="color:#2980b9">OS SX</span><span>Centro</span><span style="color:#c0392b">OD DX</span></div>
    <div class="bal-track">
      <div class="bal-center"></div>
      <div class="bal-fill-od" id="fillOD" style="width:0%"></div>
      <div class="bal-fill-os" id="fillOS" style="width:0%"></div>
    </div>
    <div id="balTxt" style="text-align:center;font-size:13px;font-weight:500;color:#1d9e75">Centro (0)</div>
  </div>
  <div class="btn-row">
    <button onclick="shiftB(-10)">&#8592; SX 10</button>
    <button onclick="shiftB(-5)">&#8592; SX 5</button>
    <button onclick="shiftB(-1)">&#8592; 1</button>
    <button onclick="shiftB(1)">1 &#8594;</button>
    <button onclick="shiftB(5)">5 &#8594;</button>
    <button onclick="shiftB(10)">DX 10 &#8594;</button>
    <button class="primary" onclick="valLat()" style="margin-left:auto">&#10003; Valida</button>
    <button onclick="nextF()">Freq. succ. &#8594;</button>
  </div>
  <div id="latSt" class="status info">Seleziona frequenza e invia il tono.</div>
</div>
<div class="card">
  <h3>Risultati lateralita</h3>
  <div class="grid2">
    <div class="ear-box"><div class="lbl" style="color:#c0392b">OD Destro</div><div class="val" id="resOD">—</div><div style="font-size:10px;color:#8a8a8a">balance medio</div></div>
    <div class="ear-box"><div class="lbl" style="color:#2980b9">OS Sinistro</div><div class="val" id="resOS">—</div><div style="font-size:10px;color:#8a8a8a">balance medio</div></div>
  </div>
  <div id="domTxt" style="font-size:13px;font-weight:500;margin:6px 0"></div>
  <div class="lat-bar"><div class="lat-fill" id="domBar" style="width:50%;background:#1d9e75"></div></div>
  <div style="display:flex;justify-content:space-between;font-size:10px;color:#8a8a8a"><span style="color:#2980b9">OS dom</span><span>Bilanciato</span><span style="color:#c0392b">OD dom</span></div>
  <div id="freqResults" style="margin-top:8px;display:flex;flex-wrap:wrap;gap:4px"></div>
</div>
<div class="card">
  <div style="display:flex;gap:8px">
    <button class="primary" onclick="saveAll()">Salva lateralita</button>
    <button onclick="resetAll()">Reset</button>
  </div>
  <div id="saved" class="status ok" style="display:none;margin-top:6px">Salvato.</div>
</div>
<script>
const FREQS=[125,250,500,750,1000,1500,2000,3000,4000,6000,8000,10500];
const FL=['125','250','500','750','1k','1.5k','2k','3k','4k','6k','8k','10.5k'];
let curFI=0,latData={},curBal=0;
let actx=null;
function getCtx(){if(!actx)actx=new(window.AudioContext||window.webkitAudioContext)();if(actx.state==='suspended')actx.resume();return actx;}

function buildChips(){
  const c=document.getElementById('freqChips');c.innerHTML='';
  FREQS.forEach((f,i)=>{
    const d=document.createElement('div');
    d.className='fc'+(i===curFI?' active':latData[f]!==undefined?' done-'+(latData[f]>0?'od':'os'):'');
    d.textContent=FL[i]+(latData[f]!==undefined?' v':'');
    d.onclick=()=>{curFI=i;buildChips();};
    c.appendChild(d);
  });
}

function updBal(v){
  curBal=parseInt(v);
  const pct=Math.abs(curBal)/2;
  if(curBal>0){document.getElementById('fillOD').style.width=pct+'%';document.getElementById('fillOS').style.width='0%';}
  else if(curBal<0){document.getElementById('fillOS').style.width=pct+'%';document.getElementById('fillOD').style.width='0%';}
  else{document.getElementById('fillOD').style.width='0%';document.getElementById('fillOS').style.width='0%';}
  document.getElementById('balTxt').textContent=curBal===0?'Centro (0)':(curBal>0?'DX +'+curBal:'SX '+curBal);
  document.getElementById('balTxt').style.color=curBal>5?'#c0392b':curBal<-5?'#2980b9':'#1d9e75';
}

function shiftB(d){const s=document.getElementById('bal');s.value=Math.max(-100,Math.min(100,parseInt(s.value)+d));updBal(s.value);}

function playLat(){
  const ctx=getCtx();const f=FREQS[curFI];
  const vol=parseInt(document.getElementById('vol').value);
  const amp=Math.pow(10,(vol-40)/20)*0.5;
  const osc=ctx.createOscillator(),g=ctx.createGain(),pan=ctx.createStereoPanner();
  pan.pan.value=curBal/100;osc.frequency.value=f;osc.type='sine';
  g.gain.setValueAtTime(0,ctx.currentTime);g.gain.linearRampToValueAtTime(amp,ctx.currentTime+0.02);
  g.gain.setValueAtTime(amp,ctx.currentTime+1.8);g.gain.linearRampToValueAtTime(0,ctx.currentTime+2);
  osc.connect(g);g.connect(pan);pan.connect(ctx.destination);osc.start();osc.stop(ctx.currentTime+2);
  document.getElementById('latSt').textContent='Tono '+f+' Hz inviato - Balance: '+document.getElementById('balTxt').textContent;
  document.getElementById('latSt').className='status ok';
}

function valLat(){
  const f=FREQS[curFI];latData[f]=curBal;
  document.getElementById('latSt').textContent='Validato '+f+' Hz (balance '+curBal+')';
  buildChips();updResults();
  if(curFI<FREQS.length-1){curFI++;buildChips();document.getElementById('bal').value=0;updBal(0);}
}

function nextF(){if(curFI<FREQS.length-1){curFI++;buildChips();}}

function updResults(){
  const vals=Object.values(latData);if(!vals.length)return;
  const avg=Math.round(vals.reduce((a,b)=>a+b,0)/vals.length);
  const posVals=vals.filter(v=>v>0),negVals=vals.filter(v=>v<0);
  const avgOD=posVals.length?Math.round(posVals.reduce((a,b)=>a+b,0)/posVals.length):0;
  const avgOS=negVals.length?Math.round(Math.abs(negVals.reduce((a,b)=>a+b,0)/negVals.length)):0;
  document.getElementById('resOD').textContent=avgOD?'+'+avgOD:'0';
  document.getElementById('resOS').textContent=avgOS?'-'+avgOS:'0';
  const dom=avg>5?'OD Dominante':avg<-5?'OS Dominante':'Bilanciato';
  const col=avg>5?'#c0392b':avg<-5?'#2980b9':'#1d9e75';
  document.getElementById('domTxt').innerHTML='<span style="color:'+col+'">'+dom+'</span> (media: '+(avg>0?'+':'')+avg+')';
  document.getElementById('domBar').style.width=((avg+100)/200*100)+'%';
  document.getElementById('domBar').style.background=col;
  const fr=document.getElementById('freqResults');fr.innerHTML='';
  Object.entries(latData).forEach(([f,v])=>{
    const s=document.createElement('span');
    const col2=v>0?'#c0392b':v<0?'#2980b9':'#1d9e75';
    s.style.cssText='padding:2px 7px;border-radius:8px;font-size:11px;border:1px solid '+col2+';color:'+col2;
    s.textContent=(f>=1000?f/1000+'k':f)+'Hz:'+(v>0?'+':'')+v;
    fr.appendChild(s);
  });
}

function resetAll(){latData={};buildChips();document.getElementById('resOD').textContent='—';document.getElementById('resOS').textContent='—';document.getElementById('domTxt').textContent='';document.getElementById('freqResults').innerHTML='';document.getElementById('domBar').style.width='50%';document.getElementById('bal').value=0;updBal(0);}

function saveAll(){
  const vals=Object.values(latData);
  const avg=vals.length?Math.round(vals.reduce((a,b)=>a+b,0)/vals.length):0;
  const dom=avg>5?'OD':avg<-5?'OS':'Bilanciato';
  window.parent.postMessage({type:'streamlit:setComponentValue',value:JSON.stringify({lat:latData,avg:avg,dominanza:dom})},'*');
  document.getElementById('saved').style.display='block';
  setTimeout(()=>document.getElementById('saved').style.display='none',3000);
}

buildChips();updBal(0);
</script></body></html>"""

def _ui_lateralita(conn, paz_id, operatore):
    st.subheader("Lateralita uditiva di ricezione")
    st.caption("Toni stereo via WebAudio · Balance DX/SX per frequenza · 12 frequenze inclusa 10.5 kHz")

    import streamlit.components.v1 as _stc_lat
    result = _stc_lat.html(LAT_HTML, height=680, scrolling=True)

    if result:
        try:
            data = json.loads(result) if isinstance(result, str) else result
            if data and data.get("lat"):
                nota = st.text_input("Note lateralita", key="lat_note_v3")
                if _salva(conn, paz_id, "Lateralita", data,
                          float(data.get("avg", 0)),
                          data.get("dominanza",""), operatore, ""):
                    st.success(f"Lateralita salvata — {data.get('dominanza','')} (media {data.get('avg',0):+d})")
        except Exception:
            pass

# ─────────────────────────────────────────────────────────────────────────────
# Tab 6: Selettività uditiva
# ─────────────────────────────────────────────────────────────────────────────

def _ui_selettivita(conn, paz_id, operatore):
    st.subheader("Selettivita uditiva")
    st.caption("LE BC = orecchio sinistro via ossea · LE AC = via aerea · RE BC/AC = orecchio destro · O=ODX X=OSN OX=Entrambi")

    SEL_ROWS = ["LE BC","LE AC","RE BC","RE AC"]
    OPTS     = ["","O","X","OX"]
    FREQS_S  = [125,250,500,750,1000,1500,2000,3000,4000,6000,8000]
    FLABELS_S= ["125","250","500","750","1k","1.5k","2k","3k","4k","6k","8k"]

    # Tabella selettività
    header_cols = st.columns([2]+[1]*11)
    header_cols[0].markdown("**Via**")
    for i, lbl in enumerate(FLABELS_S):
        header_cols[i+1].markdown(f"<div style='text-align:center;font-size:11px;font-weight:500'>{lbl}</div>",
                                   unsafe_allow_html=True)

    sel_data = {}
    for row in SEL_ROWS:
        cols = st.columns([2]+[1]*11)
        cols[0].markdown(f"**{row}**")
        for i, lbl in enumerate(FLABELS_S):
            key = f"sel_{row.replace(' ','_')}_{i}_v3"
            v = cols[i+1].selectbox("", OPTS, key=key, label_visibility="collapsed")
            if v: sel_data[f"{row}_{i}"] = v

    # Lateralità binaurale
    st.divider()
    st.markdown("**Lateralita uditiva binaurale**")
    st.caption("BPTA a 20 dB e a soglia · O=ODX X=OSN OX=Entrambi")

    LAT_ROWS = ["BPTA 20dB","A soglia"]
    lat_data = {}

    header_cols2 = st.columns([2]+[1]*11)
    header_cols2[0].markdown("**Condizione**")
    for i, lbl in enumerate(FLABELS_S):
        header_cols2[i+1].markdown(f"<div style='text-align:center;font-size:11px;font-weight:500'>{lbl}</div>",
                                    unsafe_allow_html=True)

    for row in LAT_ROWS:
        cols = st.columns([2]+[1]*11)
        cols[0].markdown(f"**{row}**")
        for i, lbl in enumerate(FLABELS_S):
            key = f"lat_{row.replace(' ','_')}_{i}_v3"
            v = cols[i+1].selectbox("", OPTS, key=key, label_visibility="collapsed")
            if v: lat_data[f"{row}_{i}"] = v

    # Calcolo lateralità
    if lat_data:
        od_c = sum(1 for v in lat_data.values() if v in ["O","OX"])
        os_c = sum(1 for v in lat_data.values() if v in ["X","OX"])
        tot  = od_c + os_c
        idx  = round((od_c-os_c)*100/tot) if tot > 0 else 0
        dom  = "OD dominante" if idx>10 else "OS dominante" if idx<-10 else "Bilanciato"
        m1,m2,m3 = st.columns(3)
        m1.metric("Punteggio OD", od_c)
        m2.metric("Punteggio OS", os_c)
        m3.metric("Dominanza", dom)

    st.divider()
    nota_sel = st.text_input("Note selettivita", key="sel_note_v3")
    if st.button("Salva selettivita", type="primary", key="sel_save_v3"):
        dati = {"selettivita": sel_data, "lateralita_binaurale": lat_data}
        if _salva(conn, paz_id, "Selettivita", dati, 0.0, "compilata", operatore, nota_sel):
            st.success("Selettivita salvata.")

# ─────────────────────────────────────────────────────────────────────────────
# Tab 7: Johansen
# ─────────────────────────────────────────────────────────────────────────────

def _ui_johansen(conn, paz_id, operatore):
    st.subheader("Test dicotico di Johansen")
    st.caption("20 coppie sillabe OD/OS simultanee · 5 compiti · Tracce MP3 stereo")

    # Tracce audio
    st.markdown("**Riproduci le tracce in ordine:**")
    for info in JOHANSEN_TRACCE:
        n = info["n"]
        data, mime = _load_johansen_track(n)
        c1,c2 = st.columns([3,2])
        c1.markdown(f"**Traccia {n}** — {info['desc']} ({info['dur']})")
        with c2:
            if data: c2.audio(data, format=mime)
            else: c2.caption("File non trovato")

    st.divider()
    st.markdown("**Registra le risposte** — Comp.3=DX · Comp.4=SX · Comp.5=Entrambi")

    if "joh_risp_v3" not in st.session_state:
        st.session_state.joh_risp_v3 = {}

    opts = ["","OD","OS","Entrambi"]

    # Header
    h = st.columns([0.4,0.7,0.7,1.2,1.2,1.2])
    for lbl,col in zip(["#","OD","OS","Comp.3","Comp.4","Comp.5"],h):
        col.markdown(f"<div style='font-size:11px;font-weight:600;color:var(--color-text-secondary)'>{lbl}</div>",
                     unsafe_allow_html=True)

    for i, coppia in enumerate(JOHANSEN_COPPIE):
        c0,c1,c2,c3,c4,c5 = st.columns([0.4,0.7,0.7,1.2,1.2,1.2])
        c0.markdown(f"<div style='font-size:11px;color:#888;padding-top:8px'>{i+1}</div>", unsafe_allow_html=True)
        c1.markdown(f"<div style='color:#c0392b;font-weight:600;font-size:13px;padding-top:6px'>{coppia['od']}</div>", unsafe_allow_html=True)
        c2.markdown(f"<div style='color:#2980b9;font-weight:600;font-size:13px;padding-top:6px'>{coppia['os']}</div>", unsafe_allow_html=True)
        r = st.session_state.joh_risp_v3.get(i, {})
        for comp,col in [("c3",c3),("c4",c4),("c5",c5)]:
            cur_v = r.get(comp,"")
            idx_v = opts.index(cur_v) if cur_v in opts else 0
            v = col.selectbox("", opts, index=idx_v, key=f"joh_{comp}_{i}_v3",
                               label_visibility="collapsed")
            if v: st.session_state.joh_risp_v3.setdefault(i,{})[comp] = v

    # Punteggi
    jod, jos = 0, 0
    for i, r in st.session_state.joh_risp_v3.items():
        if r.get("c3")=="OD": jod+=1
        if r.get("c4")=="OS": jos+=1
        if r.get("c5") in ["OD","Entrambi"]: jod+=1
        if r.get("c5") in ["OS","Entrambi"]: jos+=1

    tot = jod+jos
    idx_j = round((jod-jos)*100/tot,1) if tot>0 else 0
    dom_j = "OD dominante" if idx_j>10 else "OS dominante" if idx_j<-10 else "Bilanciato"

    st.divider()
    m1,m2,m3 = st.columns(3)
    m1.metric("Punteggio OD", jod)
    m2.metric("Punteggio OS", jos)
    m3.metric("Indice lateralita", f"{idx_j:+.1f}" if tot>0 else "—")
    if tot>0:
        color = "#c0392b" if idx_j>10 else "#2980b9" if idx_j<-10 else "#2d7d6f"
        st.markdown(f"<div style='padding:8px;border-radius:8px;border-left:4px solid {color};"
                    f"background:var(--color-background-secondary);font-size:13px'>"
                    f"<b style='color:{color}'>{dom_j}</b> (indice {idx_j:+.1f}/100)</div>",
                    unsafe_allow_html=True)

    nota_j = st.text_input("Note Johansen", key="joh_note_v3")
    c1,c2 = st.columns(2)
    if c1.button("Salva Johansen", type="primary", key="joh_save_v3"):
        dati = {"jod":jod,"jos":jos,"indice":idx_j,"dominanza":dom_j,
                "risposte":{str(k):v for k,v in st.session_state.joh_risp_v3.items()}}
        if _salva(conn, paz_id, "Johansen", dati, idx_j, dom_j, operatore, nota_j):
            st.success(f"Johansen salvato — {dom_j} (indice {idx_j:+.1f})")
    if c2.button("Reset risposte", key="joh_reset_v3"):
        st.session_state.joh_risp_v3 = {}

# ─────────────────────────────────────────────────────────────────────────────
# Tab 8: Storico
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
        st.info("Nessun dato registrato per questo paziente."); return

    for r in rows:
        eid  = _rg(r,"id"); tipo = _rg(r,"tipo",""); data = _rg(r,"data_esame","")
        cls  = _rg(r,"classificazione",""); score = _rg(r,"punteggio")
        note = _rg(r,"note","")

        with st.expander(f"#{eid} | {tipo} | {data} | {cls}"):
            c1,c2 = st.columns(2)
            if score is not None:
                c1.metric("Punteggio", f"{score}")
            c2.metric("Classificazione", cls or "—")
            if note: st.caption(f"Note: {note}")
            try:
                dati = json.loads(_rg(r,"dati_json","{}") or "{}")
                if tipo == "Fisher" and "apd" in dati:
                    st.markdown("**Profilo APD:**")
                    acols = st.columns(4)
                    for col_a,(cat,info) in zip(acols, APD_CATS.items()):
                        col_a.metric(cat, f"{dati['apd'].get(cat,0)}/{len(info['items'])}")
                elif tipo == "Audiogramma":
                    od_ac = dati.get("od_ac",[])
                    os_ac = dati.get("os_ac",[])
                    tom   = dati.get("tomatis", list(TOMATIS_STD))
                    if any(v is not None for v in od_ac+os_ac):
                        _disegna_audiogramma(od_ac, os_ac, tom)
            except Exception: pass
