# -*- coding: utf-8 -*-
"""
MAPS — Stimolazione uditiva adattiva (motore browser), con cornice dal paziente.

Legge l'ultima audiometria funzionale del paziente attivo e ne ricava la cornice
clinica (orecchio da privilegiare, tornante, attenuazione), che inietta nel motore
MAPS (assets/maps.html). Decisione clinica: si privilegia l'orecchio destro.
"""
import json
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components

FREQS = [125, 250, 500, 750, 1000, 1500, 2000, 3000, 4000, 6000, 8000]


def _get_conn():
    try:
        import sys, os
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if root not in sys.path:
            sys.path.insert(0, root)
        from app_patched import get_connection
        return get_connection()
    except Exception:
        pass
    import sqlite3
    c = sqlite3.connect("organism.db")
    c.row_factory = sqlite3.Row
    return c


def _ultima_audiometria(conn, paz_id):
    sql = ("SELECT od_json, os_json, eq_od_json, eq_os_json, joh_dominanza, data_esame "
           "FROM audiometrie_funzionali WHERE paziente_id = {ph} ORDER BY id DESC LIMIT 1")
    for ph in ("%s", "?"):
        try:
            cur = conn.cursor()
            cur.execute(sql.format(ph=ph), (paz_id,))
            return cur.fetchone()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
    return None


def _costruisci_cornice(row, nome=""):
    if not row:
        return None

    def col(i):
        try:
            return row[i]
        except Exception:
            return None

    try:
        eqod = json.loads(col(2) or "[]")
    except Exception:
        eqod = []
    dom = col(4) or "n/d"
    data = col(5) or ""

    # banda di maggior deficit sull'orecchio destro: Delta EQ piu' positivo = piu' sotto
    # il target Tomatis = dove serve piu' rinforzo. La uso come tornante "di riposo".
    tornante, atten = 1000, 12
    valid = [(FREQS[i], eqod[i]) for i in range(min(len(FREQS), len(eqod)))
             if eqod[i] is not None]
    if valid:
        tornante = max(valid, key=lambda t: t[1])[0]
        mean_abs = sum(abs(v) for _, v in valid) / len(valid)
        atten = int(max(4, min(24, round(mean_abs))))

    return {
        "paziente": nome,
        "lateralita": "dx",            # decisione clinica: si privilegia il destro
        "tornante_hz": int(tornante),
        "atten_freq_db": int(atten),
        "dominanza": dom,
        "data_esame": data,
    }


def ui_maps(conn=None):
    st.header("\U0001F3A7 MAPS \u2014 Stimolazione uditiva adattiva")
    st.caption("Music \u00b7 Adapted \u00b7 Psychacustic \u00b7 System \u2014 impostazioni dai test del paziente attivo")

    if conn is None:
        conn = _get_conn()

    cornice = None
    try:
        from modules.paziente_attivo import paziente_attivo_id, paziente_attivo_record
        paz_id = paziente_attivo_id()
        if not paz_id:
            st.info("Impostazioni generiche — nessun paziente attivo. Seleziona un paziente per usare le sue impostazioni dai test.")
        else:
            rec = paziente_attivo_record() or {}
            nome = (str(rec.get("cognome", "")) + " " + str(rec.get("nome", ""))).strip()
            row = _ultima_audiometria(conn, paz_id)
            if row:
                cornice = _costruisci_cornice(row, nome)
                if cornice:
                    st.success(
                        f"Cornice dall'audiometria di {nome or paz_id} \u2014 "
                        f"privilegia destro \u00b7 tornante {cornice['tornante_hz']} Hz \u00b7 "
                        f"attenuazione {cornice['atten_freq_db']} dB \u00b7 dominanza {cornice['dominanza']}."
                    )
            else:
                st.info("Impostazioni generiche — nessun test audiometrico per questo paziente.")
    except Exception as e:
        st.caption(f"(impostazioni del paziente non disponibili: {e})")

    html_path = Path(__file__).resolve().parent.parent / "assets" / "maps.html"
    if not html_path.exists():
        st.error(f"File MAPS non trovato: {html_path}")
        st.info("Carica assets/maps.html nel repository, poi ricarica la pagina.")
        return

    html = html_path.read_text(encoding="utf-8")
    if cornice:
        html = html.replace("window.MAPS_CORNICE = null;",
                            "window.MAPS_CORNICE = " + json.dumps(cornice) + ";")
    components.html(html, height=1750, scrolling=True)
