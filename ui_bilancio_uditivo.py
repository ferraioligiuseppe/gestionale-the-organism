# -*- coding: utf-8 -*-
"""
Modulo: Bilancio Uditivo — Metodo Tomatis/Hiperion
Gestionale The Organism – PNEV

Test implementati:
  1. Lateralita uditiva di ricezione (WebAudio browser, 16 frequenze)
  2. Elasticita del timpano (noise generator + registrazione tolleranza)
  3. Test dicotico di Johansen (20 coppie sillabe, punteggio OD/OS)
  4. Sintesi + storico nel tempo con grafici

Salvataggio DB: tabella bilanci_uditivi
"""

import json
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from datetime import date, datetime

JOHANSEN_COPPIE = [
    {"od":"DAT","os":"SOT"},{"od":"MYL","os":"GIF"},{"od":"NIK","os":"VEF"},
    {"od":"GIF","os":"KIT"},{"od":"FAK","os":"BAT"},{"od":"NUR","os":"NIK"},
    {"od":"SOT","os":"VYF"},{"od":"GEP","os":"RIS"},{"od":"VYF","os":"MYL"},
    {"od":"POS","os":"LIR"},{"od":"BOT","os":"TIK"},{"od":"VEF","os":"FAK"},
    {"od":"KIR","os":"DAT"},{"od":"KIT","os":"NUR"},{"od":"TIK","os":"BOT"},
    {"od":"LYM","os":"LYM"},{"od":"TOS","os":"HUT"},{"od":"BAT","os":"GEP"},
    {"od":"RIS","os":"POS"},{"od":"HUT","os":"TOS"},
]

FREQS_16 = [125,250,500,750,1000,1500,2000,3000,4000,6000,8000,10500,12000,14000,16000,18000]

_HTML_TEMPLATE = """ + repr(HTML_TEMPLATE) + """


def _html_bilancio(paz_id: int) -> str:
    return (_HTML_TEMPLATE
            .replace("__FREQS__", json.dumps(FREQS_16))
            .replace("__JOHANSEN__", json.dumps(JOHANSEN_COPPIE))
            .replace("__PAZ_ID__", str(paz_id)))


def _is_postgres(conn) -> bool:
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
    return ", ".join(["%s" if _is_postgres(conn) else "?"] * n)

def _get_conn():
    try:
        from modules.app_core import get_connection; return get_connection()
    except Exception: pass
    try:
        import sys, os
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if root not in sys.path: sys.path.insert(0, root)
        from app_patched import get_connection; return get_connection()
    except Exception: pass
    import sqlite3
    conn = sqlite3.connect("organism.db"); conn.row_factory = sqlite3.Row; return conn

def _row_get(row, key, default=None):
    try: v = row[key]; return v if v is not None else default
    except Exception:
        try: return row.get(key, default)
        except: return default

def _init_db(conn):
    raw = getattr(conn, "_conn", conn)
    try: cur = raw.cursor()
    except: cur = conn.cursor()
    pg = _is_postgres(conn)
    if pg:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS bilanci_uditivi (
            id BIGSERIAL PRIMARY KEY,
            paziente_id BIGINT NOT NULL,
            data_bilancio TEXT, operatore TEXT,
            lat_balance_json TEXT, lat_balance_medio DOUBLE PRECISION, lat_dominanza TEXT,
            timp_vol_tollerato DOUBLE PRECISION, timp_durata_sec DOUBLE PRECISION, timp_note TEXT,
            joh_od INTEGER, joh_os INTEGER,
            joh_indice DOUBLE PRECISION, joh_dominanza TEXT, joh_risposte_json TEXT,
            note_cliniche TEXT, created_at TEXT
        )""")
    else:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS bilanci_uditivi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paziente_id INTEGER NOT NULL,
            data_bilancio TEXT, operatore TEXT,
            lat_balance_json TEXT, lat_balance_medio REAL, lat_dominanza TEXT,
            timp_vol_tollerato REAL, timp_durata_sec REAL, timp_note TEXT,
            joh_od INTEGER, joh_os INTEGER,
            joh_indice REAL, joh_dominanza TEXT, joh_risposte_json TEXT,
            note_cliniche TEXT, created_at TEXT
        )""")
    try: raw.commit()
    except: conn.commit()

def _salva_bilancio(conn, paz_id: int, data: dict, operatore: str = ""):
    cur = conn.cursor()
    lat = data.get("lat", {})
    lat_vals = [v for v in lat.values() if v is not None] if lat else []
    lat_medio = round(sum(lat_vals) / len(lat_vals), 2) if lat_vals else None
    lat_dom = (None if lat_medio is None else
               "DX" if lat_medio > 5 else "SX" if lat_medio < -5 else "Bilanciato")
    timp = data.get("timp", {})
    joh = data.get("joh", {})
    jod = int(joh.get("od", 0))
    jos = int(joh.get("os", 0))
    jtot = int(joh.get("tot", 0))
    jidx = round((jod - jos) * 100 / jtot, 1) if jtot > 0 else None
    jdom = (None if jidx is None else
            "DX" if jidx > 10 else "SX" if jidx < -10 else "Bilanciato")
    ph = _ph(17, conn)
    params = (
        paz_id, date.today().isoformat(), operatore,
        json.dumps(lat), lat_medio, lat_dom,
        float(timp.get("vol", 0)) if timp.get("vol") else None,
        float(timp.get("dur", 0)) if timp.get("dur") else None,
        timp.get("note", ""),
        jod, jos, jidx, jdom,
        json.dumps(joh.get("ans", {})),
        data.get("note", ""),
        datetime.now().isoformat(timespec="seconds"),
    )
    sql = (
        "INSERT INTO bilanci_uditivi (paziente_id, data_bilancio, operatore, "
        "lat_balance_json, lat_balance_medio, lat_dominanza, "
        "timp_vol_tollerato, timp_durata_sec, timp_note, "
        "joh_od, joh_os, joh_indice, joh_dominanza, joh_risposte_json, "
        f"note_cliniche, created_at) VALUES ({ph})"
    )
    try:
        cur.execute(sql, params)
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Errore salvataggio: {e}")
        return False


def ui_bilancio_uditivo():
    try:
        from modules.ui_calibrazione_cuffie import ui_calibrazione_cuffie, ui_fonometro_wizard
        _has_calib = True
    except Exception:
        _has_calib = False

    st.header("Bilancio Uditivo")
    st.caption("Lateralita uditiva · Elasticita timpano · Test dicotico Johansen — Metodo Tomatis/Hiperion")

    conn = _get_conn()
    _init_db(conn)
    cur = conn.cursor()

    try:
        cur.execute('SELECT id, "Cognome", "Nome" FROM "Pazienti" ORDER BY "Cognome", "Nome"')
        pazienti = cur.fetchall()
    except Exception:
        try:
            cur.execute("SELECT id, Cognome, Nome FROM Pazienti ORDER BY Cognome, Nome")
            pazienti = cur.fetchall()
        except Exception as e:
            st.error(f"Errore pazienti: {e}"); return

    if not pazienti:
        st.info("Nessun paziente registrato."); return

    opts = [f"{_row_get(p,'id')} - {_row_get(p,'Cognome','')} {_row_get(p,'Nome','')}".strip()
            for p in pazienti]
    sel = st.selectbox("Paziente", opts, key="bu_paz")
    paz_id = int(sel.split(" - ", 1)[0])
    op = st.text_input("Operatore", "", key="bu_op")
    st.divider()

    result = components.html(_html_bilancio(paz_id), height=720, scrolling=True)

    if result:
        try:
            data = json.loads(result) if isinstance(result, str) else result
            if data and data.get("paz_id"):
                if _salva_bilancio(conn, paz_id, data, op):
                    st.success("Bilancio uditivo salvato correttamente.")
                    st.rerun()
        except Exception:
            pass

    st.divider()
    with st.expander("Storico bilanci uditivi", expanded=False):
        _ui_storico(conn, cur, paz_id)

    st.divider()
    with st.expander("🔧 Calibrazione cuffie con fonometro", expanded=False):
        if _has_calib:
            tab_fon, tab_classic = st.tabs(["Fonometro wizard", "Wizard classico + profili"])
            with tab_fon:
                ui_fonometro_wizard()
            with tab_classic:
                ui_calibrazione_cuffie(conn)
        else:
            st.info("Modulo calibrazione non disponibile.")


def _ui_storico(conn, cur, paz_id):
    ph1 = _ph(1, conn)
    try:
        cur.execute(
            "SELECT * FROM bilanci_uditivi WHERE paziente_id = " + ph1 +
            " ORDER BY data_bilancio DESC, id DESC LIMIT 20",
            (paz_id,)
        )
        rows = cur.fetchall()
    except Exception as e:
        st.error(f"Errore storico: {e}"); return

    if not rows:
        st.info("Nessun bilancio registrato per questo paziente."); return

    lat_rows, joh_rows = [], []
    for r in rows:
        d = _row_get(r, "data_bilancio", "")
        lm = _row_get(r, "lat_balance_medio")
        ji = _row_get(r, "joh_indice")
        if lm is not None: lat_rows.append({"Data": d, "Balance medio": lm})
        if ji is not None: joh_rows.append({"Data": d, "Indice Johansen": ji})

    if lat_rows or joh_rows:
        cg1, cg2 = st.columns(2)
        if lat_rows:
            with cg1:
                st.markdown("**Lateralita uditiva nel tempo**")
                st.line_chart(pd.DataFrame(lat_rows).sort_values("Data").set_index("Data"))
                st.caption(">+5 = Dom DX | <-5 = Dom SX")
        if joh_rows:
            with cg2:
                st.markdown("**Indice Johansen nel tempo**")
                st.line_chart(pd.DataFrame(joh_rows).sort_values("Data").set_index("Data"))
                st.caption(">+10 = Dom DX | <-10 = Dom SX")

    for r in rows:
        eid = _row_get(r, "id")
        data_b = _row_get(r, "data_bilancio", "")
        ld = _row_get(r, "lat_dominanza", "-")
        jd = _row_get(r, "joh_dominanza", "-")
        lm = _row_get(r, "lat_balance_medio")
        ji = _row_get(r, "joh_indice")
        with st.expander(f"#{eid} | {data_b} — Lat: {ld} | Johansen: {jd}"):
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Balance medio", f"{lm:+.1f}" if lm is not None else "-")
            c2.metric("Dom. lateralita", ld or "-")
            c3.metric("Indice Johansen", f"{ji:+.1f}" if ji is not None else "-")
            c4.metric("Dom. Johansen", jd or "-")
            jod = _row_get(r, "joh_od")
            jos = _row_get(r, "joh_os")
            tv = _row_get(r, "timp_vol_tollerato")
            td = _row_get(r, "timp_durata_sec")
            tn = _row_get(r, "timp_note", "")
            if jod is not None: st.markdown(f"**Johansen:** OD={jod} OS={jos}")
            if tv is not None: st.markdown(f"**Timpano:** {tv} dB per {td}s{' - '+tn if tn else ''}")
            note = _row_get(r, "note_cliniche", "")
            if note: st.markdown(f"**Note:** {note}")
