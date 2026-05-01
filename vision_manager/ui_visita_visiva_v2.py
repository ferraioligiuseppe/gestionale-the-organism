# -*- coding: utf-8 -*-
"""
Vision Manager — Visita Visiva v2 (refactored)

FLUSSO VISITA OCULISTICA A FASI:
  FASE 1: Nominativo + Anamnesi + Visus  → Salva BOZZA (paziente esce per dilatazione)
  (nel frattempo si può visitare un altro paziente)
  FASE 2: Riapri paziente → Fondo oculare + Esame obiettivo + Refrazione → Salva COMPLETA
  FASE 3: PDF referto / prescrizione

Correzioni principali:
  • list_pazienti() filtra stato_paziente = 'ATTIVO' → niente archiviati/duplicati
  • Label paziente include data nascita per distinguere omonimi
  • Nuovo paziente: telefono + email opzionali
  • Flusso multi-fase con stato BOZZA / COMPLETA
  • Pulsante "Riprendi dopo dilatazione" carica la bozza senza perdere nulla
  • Tipo visita non più hardcoded: oculistica / controllo / post-operatorio / urgenza
  • Storico con badge 🟡 BOZZA / 🟢 COMPLETA
"""

import json
import time
import datetime as dt
from datetime import date, datetime
import calendar

import matplotlib.pyplot as plt
import streamlit as st
from streamlit.errors import StreamlitAPIException

from vision_manager.db import get_conn
from vision_manager.pdf_referto_oculistica import build_referto_oculistico_a4
from vision_manager.pdf_prescrizione import build_prescrizione_occhiali_a4
from vision_manager.professionisti_db import get_professionista_default

LETTERHEAD = "vision_manager/assets/letterhead_cirillo_A4.jpeg"

STATO_BOZZA    = "BOZZA"
STATO_COMPLETA = "COMPLETA"


# =========================================================
# HELPERS
# =========================================================

def _is_pg(conn):
    return conn.__class__.__module__.startswith("psycopg2")

def _ph(conn):
    return "%s" if _is_pg(conn) else "?"

def _row_get(row, key, index=None, default=None):
    try:
        if isinstance(row, dict):
            return row.get(key, default)
        if index is not None:
            return row[index]
    except Exception:
        pass
    return default

def _parse_date_safe(value):
    if not value:
        return date.today()
    if isinstance(value, date):
        return value
    s = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s[:10], fmt).date()
        except Exception:
            pass
    return date.today()

def _calculate_age(birth_date):
    if not birth_date:
        return None
    try:
        b = _parse_date_safe(birth_date) if not isinstance(birth_date, date) else birth_date
        today = date.today()
        return today.year - b.year - ((today.month, today.day) < (b.month, b.day))
    except Exception:
        return None

def _safe_float(value, default=0.0):
    try:
        return default if value in (None, "") else float(value)
    except Exception:
        return default

def _safe_int(value, default=0):
    try:
        return default if value in (None, "") else int(float(value))
    except Exception:
        return default

def _fmt_value(value, fallback="-"):
    if value is None:
        return fallback
    s = str(value).strip()
    return s if s else fallback

def _fmt_rx(rx_dict):
    if not isinstance(rx_dict, dict):
        return "-"
    sf  = _safe_float(rx_dict.get("sf"), 0.0)
    cyl = _safe_float(rx_dict.get("cyl"), 0.0)
    ax  = _safe_int(rx_dict.get("ax"), 0)
    return f"{sf:+.2f} ({cyl:+.2f} x {ax})"

def _payload_signature(payload):
    try:
        return json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    except Exception:
        return str(payload)

def _render_dmy_input(label, key_prefix, default_date=None):
    dflt = _parse_date_safe(default_date) if default_date else date.today()
    day_key, month_key, year_key = f"{key_prefix}_day", f"{key_prefix}_month", f"{key_prefix}_year"
    st.session_state.setdefault(day_key,   dflt.day)
    st.session_state.setdefault(month_key, dflt.month)
    st.session_state.setdefault(year_key,  dflt.year)
    month_names = ["Gennaio","Febbraio","Marzo","Aprile","Maggio","Giugno",
                   "Luglio","Agosto","Settembre","Ottobre","Novembre","Dicembre"]
    st.markdown(label)
    c1, c2, c3 = st.columns([1, 1, 1.2])
    year_sel  = c3.selectbox("Anno", list(range(date.today().year, 1899, -1)),
                              index=max(0, date.today().year - st.session_state[year_key]), key=year_key)
    month_sel = c2.selectbox("Mese", list(range(1, 13)),
                              format_func=lambda m: month_names[m-1],
                              index=max(0, min(11, st.session_state[month_key]-1)), key=month_key)
    max_day = calendar.monthrange(int(year_sel), int(month_sel))[1]
    cur_day = int(st.session_state.get(day_key, dflt.day) or dflt.day)
    if cur_day > max_day:
        cur_day = max_day
        st.session_state[day_key] = max_day
    day_sel = c1.selectbox("Giorno", list(range(1, max_day+1)),
                            index=max(0, min(max_day-1, cur_day-1)), key=day_key)
    return date(int(year_sel), int(month_sel), int(day_sel))


# =========================================================
# SESSION STATE
# =========================================================

def ensure_visit_state():
    defaults = {
        "vm_current_patient_id": None,
        "vm_selected_paziente_label": None,
        "vision_last_pid": None,
        "vm_force_selected_paziente_label": None,
        "vm_tipo_visita": "oculistica",
        "vm_data_visita": date.today(),
        "vm_stato_visita": STATO_BOZZA,
        "vm_anamnesi": "",
        "vm_acuita_naturale_od": "", "vm_acuita_naturale_os": "",
        "vm_acuita_corretta_od": "", "vm_acuita_corretta_os": "",
        "vm_congiuntiva": "", "vm_cornea": "", "vm_camera_anteriore": "",
        "vm_cristallino": "", "vm_vitreo": "", "vm_fondo_oculare": "",
        "vm_iop_od": "", "vm_iop_os": "",
        "vm_pachimetria_od": "", "vm_pachimetria_os": "",
        "vm_ca_od_sf": 0.0, "vm_ca_od_cyl": 0.0, "vm_ca_od_ax": 0,
        "vm_ca_os_sf": 0.0, "vm_ca_os_cyl": 0.0, "vm_ca_os_ax": 0,
        "vm_cf_od_sf": 0.0, "vm_cf_od_cyl": 0.0, "vm_cf_od_ax": 0,
        "vm_cf_os_sf": 0.0, "vm_cf_os_cyl": 0.0, "vm_cf_os_ax": 0,
        "vm_enable_add_vicino": True, "vm_enable_add_intermedio": False,
        "vm_add_vicino": 0.0, "vm_add_intermedio": 0.0,
        "vm_note": "",
        "vm_mode": "new",
        "vm_loaded_visit_id": None,
        "vm_form_dirty": False,
        "vm_pending_action": None,
        "vm_pending_load": None,
        "vm_pending_form_reset": False,
        "vm_history_selected_visit_id": None,
        "vm_autosave_enabled": True,
        "vm_autosave_status": None,
        "vm_last_autosave_at": None,
        "vm_last_saved_hash": None,
        "vm_last_autosave_reason": None,
        "vm_flash_message": None,
        "vm_delete_confirm":         None,
        "vm_confirm_delete_paz":     None,
        "vm_in_dilatazione": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

def mark_visit_dirty():
    st.session_state["vm_form_dirty"] = True

def _apply_form_reset():
    st.session_state.update({
        "vm_tipo_visita": "oculistica", "vm_data_visita": date.today(),
        "vm_stato_visita": STATO_BOZZA, "vm_anamnesi": "",
        "vm_acuita_naturale_od": "", "vm_acuita_naturale_os": "",
        "vm_acuita_corretta_od": "", "vm_acuita_corretta_os": "",
        "vm_congiuntiva": "", "vm_cornea": "", "vm_camera_anteriore": "",
        "vm_cristallino": "", "vm_vitreo": "", "vm_fondo_oculare": "",
        "vm_iop_od": "", "vm_iop_os": "", "vm_pachimetria_od": "", "vm_pachimetria_os": "",
        "vm_ca_od_sf": 0.0, "vm_ca_od_cyl": 0.0, "vm_ca_od_ax": 0,
        "vm_ca_os_sf": 0.0, "vm_ca_os_cyl": 0.0, "vm_ca_os_ax": 0,
        "vm_cf_od_sf": 0.0, "vm_cf_od_cyl": 0.0, "vm_cf_od_ax": 0,
        "vm_cf_os_sf": 0.0, "vm_cf_os_cyl": 0.0, "vm_cf_os_ax": 0,
        "vm_enable_add_vicino": True, "vm_enable_add_intermedio": False,
        "vm_add_vicino": 0.0, "vm_add_intermedio": 0.0, "vm_note": "",
        "vm_loaded_visit_id": None, "vm_mode": "new", "vm_form_dirty": False,
        "vm_in_dilatazione": False,
    })

def clear_visit_form():
    try:
        _apply_form_reset()
        st.session_state["vm_pending_form_reset"] = False
    except StreamlitAPIException:
        st.session_state["vm_pending_form_reset"] = True
        st.session_state["vm_loaded_visit_id"] = None
        st.session_state["vm_mode"] = "new"
        st.session_state["vm_form_dirty"] = False


# =========================================================
# PAYLOAD
# =========================================================

def build_visit_payload():
    return {
        "tipo_visita":  st.session_state.get("vm_tipo_visita", "oculistica"),
        "data":         str(st.session_state.get("vm_data_visita", date.today())),
        "stato_visita": st.session_state.get("vm_stato_visita", STATO_BOZZA),
        "anamnesi":     st.session_state.get("vm_anamnesi", ""),
        "acuita": {
            "naturale": {"od": st.session_state.get("vm_acuita_naturale_od", ""),
                         "os": st.session_state.get("vm_acuita_naturale_os", "")},
            "corretta": {"od": st.session_state.get("vm_acuita_corretta_od", ""),
                         "os": st.session_state.get("vm_acuita_corretta_os", "")},
        },
        "esame_obiettivo": {
            "congiuntiva":             st.session_state.get("vm_congiuntiva", ""),
            "cornea":                  st.session_state.get("vm_cornea", ""),
            "camera_anteriore":        st.session_state.get("vm_camera_anteriore", ""),
            "cristallino":             st.session_state.get("vm_cristallino", ""),
            "vitreo":                  st.session_state.get("vm_vitreo", ""),
            "fondo_oculare":           st.session_state.get("vm_fondo_oculare", ""),
            "pressione_endoculare_od": st.session_state.get("vm_iop_od", ""),
            "pressione_endoculare_os": st.session_state.get("vm_iop_os", ""),
            "pachimetria_od":          st.session_state.get("vm_pachimetria_od", ""),
            "pachimetria_os":          st.session_state.get("vm_pachimetria_os", ""),
        },
        "correzione_abituale": {
            "od": {"sf": st.session_state.get("vm_ca_od_sf", 0.0),
                   "cyl": st.session_state.get("vm_ca_od_cyl", 0.0),
                   "ax": st.session_state.get("vm_ca_od_ax", 0)},
            "os": {"sf": st.session_state.get("vm_ca_os_sf", 0.0),
                   "cyl": st.session_state.get("vm_ca_os_cyl", 0.0),
                   "ax": st.session_state.get("vm_ca_os_ax", 0)},
        },
        "correzione_finale": {
            "od": {"sf": st.session_state.get("vm_cf_od_sf", 0.0),
                   "cyl": st.session_state.get("vm_cf_od_cyl", 0.0),
                   "ax": st.session_state.get("vm_cf_od_ax", 0)},
            "os": {"sf": st.session_state.get("vm_cf_os_sf", 0.0),
                   "cyl": st.session_state.get("vm_cf_os_cyl", 0.0),
                   "ax": st.session_state.get("vm_cf_os_ax", 0)},
            "add_vicino":            _safe_float(st.session_state.get("vm_add_vicino", 0.0)),
            "add_intermedio":        _safe_float(st.session_state.get("vm_add_intermedio", 0.0)),
            "enable_add_vicino":     bool(st.session_state.get("vm_enable_add_vicino", True)),
            "enable_add_intermedio": bool(st.session_state.get("vm_enable_add_intermedio", False)),
        },
        "note": st.session_state.get("vm_note", ""),
    }


def load_visit_payload(payload, visit_id=None):
    acuita = payload.get("acuita", {}) or {}
    nat    = acuita.get("naturale", {}) or {}
    cor    = acuita.get("corretta", {}) or {}
    esame  = payload.get("esame_obiettivo", {}) or {}
    cab    = payload.get("correzione_abituale", {}) or {}
    cab_od = cab.get("od", {}) or {}
    cab_os = cab.get("os", {}) or {}
    cfin   = payload.get("correzione_finale", {}) or {}
    cfin_od = cfin.get("od", {}) or {}
    cfin_os = cfin.get("os", {}) or {}

    st.session_state.update({
        "vm_tipo_visita": payload.get("tipo_visita", "oculistica"),
        "vm_data_visita": _parse_date_safe(payload.get("data")),
        "vm_stato_visita": payload.get("stato_visita", STATO_BOZZA),
        "vm_anamnesi": payload.get("anamnesi", ""),
        "vm_acuita_naturale_od": nat.get("od", ""), "vm_acuita_naturale_os": nat.get("os", ""),
        "vm_acuita_corretta_od": cor.get("od", ""), "vm_acuita_corretta_os": cor.get("os", ""),
        "vm_congiuntiva": esame.get("congiuntiva", ""), "vm_cornea": esame.get("cornea", ""),
        "vm_camera_anteriore": esame.get("camera_anteriore", ""),
        "vm_cristallino": esame.get("cristallino", ""), "vm_vitreo": esame.get("vitreo", ""),
        "vm_fondo_oculare": esame.get("fondo_oculare", ""),
        "vm_iop_od": esame.get("pressione_endoculare_od", ""),
        "vm_iop_os": esame.get("pressione_endoculare_os", ""),
        "vm_pachimetria_od": esame.get("pachimetria_od", ""),
        "vm_pachimetria_os": esame.get("pachimetria_os", ""),
        "vm_ca_od_sf":  _safe_float(cab_od.get("sf", 0.0)),
        "vm_ca_od_cyl": _safe_float(cab_od.get("cyl", 0.0)),
        "vm_ca_od_ax":  _safe_int(cab_od.get("ax", 0)),
        "vm_ca_os_sf":  _safe_float(cab_os.get("sf", 0.0)),
        "vm_ca_os_cyl": _safe_float(cab_os.get("cyl", 0.0)),
        "vm_ca_os_ax":  _safe_int(cab_os.get("ax", 0)),
        "vm_cf_od_sf":  _safe_float(cfin_od.get("sf", 0.0)),
        "vm_cf_od_cyl": _safe_float(cfin_od.get("cyl", 0.0)),
        "vm_cf_od_ax":  _safe_int(cfin_od.get("ax", 0)),
        "vm_cf_os_sf":  _safe_float(cfin_os.get("sf", 0.0)),
        "vm_cf_os_cyl": _safe_float(cfin_os.get("cyl", 0.0)),
        "vm_cf_os_ax":  _safe_int(cfin_os.get("ax", 0)),
        "vm_add_vicino":            _safe_float(cfin.get("add_vicino", 0.0)),
        "vm_add_intermedio":        _safe_float(cfin.get("add_intermedio", 0.0)),
        "vm_enable_add_vicino":     bool(cfin.get("enable_add_vicino", True)),
        "vm_enable_add_intermedio": bool(cfin.get("enable_add_intermedio", False)),
        "vm_note":           payload.get("note", ""),
        "vm_loaded_visit_id": visit_id,
        "vm_mode":           "edit" if visit_id else "new",
        "vm_form_dirty":     False,
        "vm_in_dilatazione": payload.get("stato_visita", STATO_BOZZA) == STATO_BOZZA and visit_id is not None,
    })
    st.session_state["vm_last_saved_hash"] = _payload_signature(build_visit_payload())


def apply_pending_visit_load():
    pending = st.session_state.pop("vm_pending_load", None)
    if not pending:
        return
    raw = pending.get("dati_json")
    visit_id = pending.get("visit_id")
    if not raw:
        return
    try:
        payload = json.loads(raw) if isinstance(raw, str) else raw
        load_visit_payload(payload, visit_id=visit_id)
    except Exception as e:
        st.error(f"Errore nel caricamento della visita: {e}")


# =========================================================
# DB — PAZIENTI
# =========================================================

def list_pazienti(conn):
    """
    Solo pazienti ATTIVI, deduplicati per (cognome, nome, data_nascita).
    In caso di duplicati viene tenuto solo il record con id più alto (più recente).
    """
    cur = conn.cursor()
    try:
        if _is_pg(conn):
            cur.execute(
                """
                SELECT DISTINCT ON (LOWER(TRIM(cognome)), LOWER(TRIM(nome)), COALESCE(TRIM(data_nascita),''))
                    id, cognome, nome, data_nascita
                FROM pazienti
                WHERE COALESCE(stato_paziente,'ATTIVO') = 'ATTIVO'
                ORDER BY LOWER(TRIM(cognome)), LOWER(TRIM(nome)), COALESCE(TRIM(data_nascita),''), id DESC
                """
            )
        else:
            # SQLite: subquery con MAX(id) per gruppo
            cur.execute(
                """
                SELECT id, Cognome AS cognome, Nome AS nome, Data_Nascita AS data_nascita
                FROM Pazienti
                WHERE COALESCE(Stato_Paziente,'ATTIVO') = 'ATTIVO'
                  AND id IN (
                      SELECT MAX(id)
                      FROM Pazienti
                      WHERE COALESCE(Stato_Paziente,'ATTIVO') = 'ATTIVO'
                      GROUP BY LOWER(TRIM(Cognome)), LOWER(TRIM(Nome)), COALESCE(TRIM(Data_Nascita),'')
                  )
                ORDER BY LOWER(TRIM(Cognome)), LOWER(TRIM(Nome))
                """
            )
        return cur.fetchall()
    finally:
        try: cur.close()
        except Exception: pass


def find_duplicati_pazienti(conn):
    """
    Restituisce i gruppi di pazienti duplicati (stesso cognome+nome+data_nascita, id diversi).
    Ogni gruppo è una lista di dict con id, cognome, nome, data_nascita, n_visite.
    """
    cur = conn.cursor()
    try:
        if _is_pg(conn):
            cur.execute(
                """
                SELECT
                    LOWER(TRIM(cognome)) AS cog,
                    LOWER(TRIM(nome))    AS nom,
                    COALESCE(TRIM(data_nascita),'') AS dn,
                    COUNT(*) AS n
                FROM pazienti
                WHERE COALESCE(stato_paziente,'ATTIVO') = 'ATTIVO'
                GROUP BY LOWER(TRIM(cognome)), LOWER(TRIM(nome)), COALESCE(TRIM(data_nascita),'')
                HAVING COUNT(*) > 1
                ORDER BY cog, nom, dn
                """
            )
        else:
            cur.execute(
                """
                SELECT
                    LOWER(TRIM(Cognome)) AS cog,
                    LOWER(TRIM(Nome))    AS nom,
                    COALESCE(TRIM(Data_Nascita),'') AS dn,
                    COUNT(*) AS n
                FROM Pazienti
                WHERE COALESCE(Stato_Paziente,'ATTIVO') = 'ATTIVO'
                GROUP BY LOWER(TRIM(Cognome)), LOWER(TRIM(Nome)), COALESCE(TRIM(Data_Nascita),'')
                HAVING COUNT(*) > 1
                ORDER BY cog, nom, dn
                """
            )
        groups_meta = cur.fetchall()
        groups = []
        for gm in groups_meta:
            cog = _row_get(gm, "cog", 0, "")
            nom = _row_get(gm, "nom", 1, "")
            dn  = _row_get(gm, "dn",  2, "")
            ph  = _ph(conn)
            if _is_pg(conn):
                cur.execute(
                    f"""
                    SELECT p.id, p.cognome, p.nome, p.data_nascita,
                           COUNT(v.id) AS n_visite
                    FROM pazienti p
                    LEFT JOIN visite_visive v ON v.paziente_id = p.id AND COALESCE(v.is_deleted,0)=0
                    WHERE LOWER(TRIM(p.cognome)) = {ph}
                      AND LOWER(TRIM(p.nome))    = {ph}
                      AND COALESCE(TRIM(p.data_nascita),'') = {ph}
                      AND COALESCE(p.stato_paziente,'ATTIVO') = 'ATTIVO'
                    GROUP BY p.id, p.cognome, p.nome, p.data_nascita
                    ORDER BY p.id DESC
                    """,
                    (cog, nom, dn)
                )
            else:
                cur.execute(
                    f"""
                    SELECT p.ID AS id, p.Cognome AS cognome, p.Nome AS nome,
                           p.Data_Nascita AS data_nascita,
                           COUNT(v.id) AS n_visite
                    FROM Pazienti p
                    LEFT JOIN visite_visive v ON v.paziente_id = p.ID AND COALESCE(v.is_deleted,0)=0
                    WHERE LOWER(TRIM(p.Cognome)) = {ph}
                      AND LOWER(TRIM(p.Nome))    = {ph}
                      AND COALESCE(TRIM(p.Data_Nascita),'') = {ph}
                      AND COALESCE(p.Stato_Paziente,'ATTIVO') = 'ATTIVO'
                    GROUP BY p.ID, p.Cognome, p.Nome, p.Data_Nascita
                    ORDER BY p.ID DESC
                    """,
                    (cog, nom, dn)
                )
            rows = cur.fetchall()
            groups.append([
                {"id": _row_get(r,"id",0), "cognome": _row_get(r,"cognome",1,""),
                 "nome": _row_get(r,"nome",2,""), "data_nascita": _row_get(r,"data_nascita",3,""),
                 "n_visite": _row_get(r,"n_visite",4,0)}
                for r in rows
            ])
        return groups
    finally:
        try: cur.close()
        except Exception: pass


def archivia_paziente_duplicato(conn, paziente_id):
    """Archivia il paziente (stato = ARCHIVIATO). Non cancella i dati."""
    ph = _ph(conn)
    cur = conn.cursor()
    try:
        if _is_pg(conn):
            cur.execute(
                f"UPDATE pazienti SET stato_paziente='ARCHIVIATO' WHERE id={ph}",
                (paziente_id,)
            )
        else:
            cur.execute(
                f"UPDATE Pazienti SET Stato_Paziente='ARCHIVIATO' WHERE ID={ph}",
                (paziente_id,)
            )
        conn.commit()
    finally:
        try: cur.close()
        except Exception: pass


def _cancella_paziente(conn, paziente_id):
    """
    Cancella definitivamente il paziente e tutte le sue visite.
    Cancella prima le tabelle figlie poi il paziente (compatibile con
    qualsiasi schema, indipendentemente dal CASCADE definito).
    """
    ph = _ph(conn)
    cur = conn.cursor()
    try:
        # Tabelle figlie — cancella in ordine per evitare FK violations
        tabelle_figlie = [
            "visite_visive",
            "prescrizioni_occhiali",
        ]
        # Aggiungi anche le altre tabelle del gestionale principale se presenti
        tabelle_opzionali = [
            ("Anamnesi",         "Paziente_ID"),
            ("anamnesi",         "paziente_id"),
            ("Sedute",           "Paziente_ID"),
            ("sedute",           "paziente_id"),
            ("Coupons",          "Paziente_ID"),
            ("coupons",          "paziente_id"),
            ("Consensi_Privacy", "paziente_id"),
            ("consensi_privacy", "paziente_id"),
        ]
        for tbl in tabelle_figlie:
            try:
                cur.execute(f"DELETE FROM {tbl} WHERE paziente_id={ph}", (paziente_id,))
            except Exception:
                try: conn.rollback()
                except Exception: pass

        for tbl, col in tabelle_opzionali:
            try:
                cur.execute(f"DELETE FROM {tbl} WHERE {col}={ph}", (paziente_id,))
            except Exception:
                try: conn.rollback()
                except Exception: pass

        # Ora cancella il paziente
        if _is_pg(conn):
            cur.execute(f"DELETE FROM pazienti WHERE id={ph}", (paziente_id,))
        else:
            cur.execute(f"DELETE FROM Pazienti WHERE ID={ph}", (paziente_id,))

        conn.commit()
    except Exception:
        try: conn.rollback()
        except Exception: pass
        raise
    finally:
        try: cur.close()
        except Exception: pass



def _get_available_cols(conn, table):
    cur = conn.cursor()
    try:
        if _is_pg(conn):
            cur.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema='public' AND table_name=%s AND column_name IN ('note','telefono','email')",
                (table,)
            )
            return {r[0] if isinstance(r,(tuple,list)) else r.get("column_name","") for r in cur.fetchall()}
        else:
            cur.execute(f"PRAGMA table_info({table})")
            all_cols = {r[1] for r in cur.fetchall()}
            return all_cols & {"note", "telefono", "email"}
    finally:
        try: cur.close()
        except Exception: pass


def insert_paziente(conn, nome, cognome, data_nascita, telefono="", email="", note=""):
    nome, cognome = (nome or "").strip(), (cognome or "").strip()
    telefono, email, note = (telefono or "").strip(), (email or "").strip(), (note or "").strip()
    data_nascita = (data_nascita or "").strip()
    if not cognome: raise ValueError("Cognome obbligatorio")
    if not nome:    raise ValueError("Nome obbligatorio")
    if not data_nascita: raise ValueError("Data di nascita obbligatoria")

    ph = _ph(conn)
    available = _get_available_cols(conn, "pazienti" if _is_pg(conn) else "Pazienti")
    cur = conn.cursor()
    try:
        if _is_pg(conn):
            cols = ["cognome","nome","data_nascita","stato_paziente"]
            vals = [cognome, nome, data_nascita, "ATTIVO"]
            for c, v in [("telefono", telefono), ("email", email), ("note", note)]:
                if c in available:
                    cols.append(c); vals.append(v)
            phs = ", ".join([ph]*len(vals))
            cur.execute(f"INSERT INTO pazienti ({','.join(cols)}) VALUES ({phs}) RETURNING id", vals)
            row = cur.fetchone()
            new_id = _row_get(row, "id", 0, None)
        else:
            cur.execute(
                f"INSERT INTO Pazienti (Cognome,Nome,Data_Nascita,Note) VALUES ({ph},{ph},{ph},{ph})",
                (cognome, nome, data_nascita, note)
            )
            new_id = getattr(cur, "lastrowid", None)
        conn.commit()
        return new_id
    except Exception:
        try: conn.rollback()
        except Exception: pass
        raise
    finally:
        try: cur.close()
        except Exception: pass


def update_paziente(conn, paziente_id, nome, cognome, data_nascita, telefono="", email="", note=""):
    nome, cognome = (nome or "").strip(), (cognome or "").strip()
    telefono, email, note = (telefono or "").strip(), (email or "").strip(), (note or "").strip()
    data_nascita = (data_nascita or "").strip()
    if not cognome: raise ValueError("Cognome obbligatorio")
    if not nome:    raise ValueError("Nome obbligatorio")
    if not data_nascita: raise ValueError("Data di nascita obbligatoria")

    ph = _ph(conn)
    available = _get_available_cols(conn, "pazienti" if _is_pg(conn) else "Pazienti")
    cur = conn.cursor()
    try:
        if _is_pg(conn):
            sets = [f"cognome={ph}", f"nome={ph}", f"data_nascita={ph}"]
            vals = [cognome, nome, data_nascita]
            for c, v in [("telefono", telefono), ("email", email), ("note", note)]:
                if c in available:
                    sets.append(f"{c}={ph}"); vals.append(v)
            vals.append(paziente_id)
            cur.execute(f"UPDATE pazienti SET {','.join(sets)} WHERE id={ph}", vals)
        else:
            cur.execute(
                f"UPDATE Pazienti SET Cognome={ph},Nome={ph},Data_Nascita={ph},Note={ph} WHERE ID={ph}",
                (cognome, nome, data_nascita, note, paziente_id)
            )
        conn.commit()
    except Exception:
        try: conn.rollback()
        except Exception: pass
        raise
    finally:
        try: cur.close()
        except Exception: pass


def _label_paziente(row):
    cognome = _row_get(row, "cognome", 1, "") or ""
    nome    = _row_get(row, "nome", 2, "") or ""
    dn      = _row_get(row, "data_nascita", 3, "") or ""
    label   = f"{cognome} {nome}".strip()
    if dn:
        try:
            dn_fmt = datetime.strptime(str(dn)[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
        except Exception:
            dn_fmt = str(dn)[:10]
        label = f"{label}  ({dn_fmt})"
    return label


def _label_for_pid(pazienti_map, pid):
    for label, _id in pazienti_map.items():
        try:
            if int(_id) == int(pid):
                return label
        except Exception:
            if _id == pid:
                return label
    return None


# =========================================================
# DB — VISITE
# =========================================================

def list_visite(conn, paziente_id):
    ph = _ph(conn)
    cur = conn.cursor()
    try:
        cur.execute(
            f"SELECT id, data_visita, dati_json FROM visite_visive "
            f"WHERE paziente_id={ph} AND COALESCE(is_deleted,0)=0 ORDER BY data_visita DESC, id DESC",
            (paziente_id,)
        )
        return cur.fetchall()
    finally:
        try: cur.close()
        except Exception: pass


def _find_bozza(conn, paziente_id):
    """Visita piu recente in stato BOZZA per questo paziente."""
    ph = _ph(conn)
    cur = conn.cursor()
    try:
        cur.execute(
            f"SELECT id, data_visita, dati_json FROM visite_visive "
            f"WHERE paziente_id={ph} AND COALESCE(is_deleted,0)=0 ORDER BY id DESC LIMIT 30",
            (paziente_id,)
        )
        for row in cur.fetchall():
            raw = _row_get(row, "dati_json", 2)
            try:
                p = json.loads(raw) if isinstance(raw, str) else raw
                if isinstance(p, dict) and p.get("stato_visita") == STATO_BOZZA:
                    return row
            except Exception:
                continue
        return None
    finally:
        try: cur.close()
        except Exception: pass


def persist_current_visit(conn, paziente_id, payload=None, reason=None):
    if payload is None:
        payload = build_visit_payload()
    data_visita = st.session_state.get("vm_data_visita", date.today())
    ph = _ph(conn)
    loaded_id = st.session_state.get("vm_loaded_visit_id")
    cur = conn.cursor()
    try:
        if loaded_id:
            cur.execute(
                f"UPDATE visite_visive SET dati_json={ph}, data_visita={ph} WHERE id={ph}",
                (json.dumps(payload), str(data_visita), loaded_id)
            )
            conn.commit()
            visit_id, action = loaded_id, "aggiornata"
        else:
            if _is_pg(conn):
                cur.execute(
                    f"INSERT INTO visite_visive (paziente_id,data_visita,dati_json) VALUES ({ph},{ph},{ph}) RETURNING id",
                    (paziente_id, str(data_visita), json.dumps(payload))
                )
                row = cur.fetchone()
                visit_id = _row_get(row, "id", 0, None)
            else:
                cur.execute(
                    f"INSERT INTO visite_visive (paziente_id,data_visita,dati_json) VALUES ({ph},{ph},{ph})",
                    (paziente_id, str(data_visita), json.dumps(payload))
                )
                visit_id = getattr(cur, "lastrowid", None)
            conn.commit()
            action = "creata"
            st.session_state["vm_loaded_visit_id"] = visit_id
            st.session_state["vm_mode"] = "edit"
        st.session_state.update({
            "vm_form_dirty": False,
            "vm_last_saved_hash": _payload_signature(payload),
            "vm_last_autosave_at": time.time(),
            "vm_last_autosave_reason": reason,
        })
        return visit_id, action
    except Exception:
        try: conn.rollback()
        except Exception: pass
        raise
    finally:
        try: cur.close()
        except Exception: pass


def delete_visit(conn, visit_id):
    ph = _ph(conn)
    cur = conn.cursor()
    try:
        cur.execute(
            f"UPDATE visite_visive SET is_deleted=1, deleted_at={ph} WHERE id={ph}",
            (str(datetime.now()), visit_id)
        )
        conn.commit()
    finally:
        try: cur.close()
        except Exception: pass


def maybe_autosave(conn, paziente_id, reason="automatico"):
    if not st.session_state.get("vm_autosave_enabled"):
        return False, None, None
    if not paziente_id or not st.session_state.get("vm_form_dirty"):
        return False, None, None
    payload = build_visit_payload()
    if _payload_signature(payload) == st.session_state.get("vm_last_saved_hash"):
        st.session_state["vm_form_dirty"] = False
        return False, st.session_state.get("vm_loaded_visit_id"), "nessuna modifica"
    visit_id, action = persist_current_visit(conn, paziente_id, payload=payload, reason=reason)
    st.session_state["vm_autosave_status"] = ("success", f"Autosalvataggio {action}. ID: {visit_id}.")
    return True, visit_id, action


def _autosave_caption():
    ts = st.session_state.get("vm_last_autosave_at")
    if not ts:
        return None
    when = datetime.fromtimestamp(ts).strftime("%d/%m/%Y %H:%M:%S")
    reason = st.session_state.get("vm_last_autosave_reason")
    return f"Ultimo salvataggio: {when}" + (f"  ({reason})" if reason else "")


# =========================================================
# PDF
# =========================================================

def _build_referto_pdf(payload, patient_label="Paziente", visit_id=None):
    data_pdf = {
        "data": str(payload.get("data", "")), "paziente": patient_label,
        "anamnesi": payload.get("anamnesi", ""),
        "acuita": payload.get("acuita", {}) or {},
        "esame_obiettivo": payload.get("esame_obiettivo", {}) or {},
        "note": payload.get("note", ""),
    }
    return build_referto_oculistico_a4(data_pdf, LETTERHEAD)


def _rx_add(rx, add_value):
    rx = rx or {}
    try: add_num = float(add_value or 0.0)
    except Exception: add_num = 0.0
    return {"sf": _safe_float(rx.get("sf",0.0)) + add_num,
            "cyl": _safe_float(rx.get("cyl",0.0)), "ax": _safe_int(rx.get("ax",0))}


def _build_prescrizione_pdf(payload, patient_label="Paziente", conn=None):
    cfin = payload.get("correzione_finale", {}) or {}
    od, os_ = cfin.get("od", {}) or {}, cfin.get("os", {}) or {}
    add_v = _safe_float(cfin.get("add_vicino", 0.0))
    add_i = _safe_float(cfin.get("add_intermedio", 0.0))
    en_v  = bool(cfin.get("enable_add_vicino", True)) and add_v > 0.0
    en_i  = bool(cfin.get("enable_add_intermedio", False)) and add_i > 0.0
    rx_blank = {"sf": None, "cyl": None, "ax": None}
    data_pdf = {
        "data": str(payload.get("data","")), "paziente": patient_label,
        "lontano": {
            "od": {"sf": _safe_float(od.get("sf")), "cyl": _safe_float(od.get("cyl")), "ax": _safe_int(od.get("ax"))},
            "os": {"sf": _safe_float(os_.get("sf")), "cyl": _safe_float(os_.get("cyl")), "ax": _safe_int(os_.get("ax"))},
        },
        "intermedio": {"od": _rx_add(od, add_i) if en_i else dict(rx_blank),
                       "os": _rx_add(os_, add_i) if en_i else dict(rx_blank)},
        "vicino": {"od": _rx_add(od, add_v) if en_v else dict(rx_blank),
                   "os": _rx_add(os_, add_v) if en_v else dict(rx_blank)},
        "lenti": [], "add": add_v if en_v else 0.0,
        "add_od": add_v if en_v else 0.0, "add_os": add_v if en_v else 0.0,
    }
    # leggo il professionista di default dal DB (se conn disponibile)
    professionista = None
    if conn is not None:
        try:
            professionista = get_professionista_default(conn)
        except Exception:
            professionista = None
    return build_prescrizione_occhiali_a4(data_pdf, LETTERHEAD, professionista=professionista)


# =========================================================
# IOP / CCT
# =========================================================

def _clinical_attention(iop_od, iop_os, cct_od, cct_os):
    out = {"od": {"flag": False, "reason": "", "adj": None},
           "os": {"flag": False, "reason": "", "adj": None}}
    for eye, iop, cct in [("od", iop_od, cct_od), ("os", iop_os, cct_os)]:
        flag, reasons, adj = False, [], None
        if iop is not None and iop >= 21:
            flag = True; reasons.append(f"IOP >= 21 mmHg ({iop:.1f})")
        if iop is not None and cct is not None and cct > 0:
            corr = (cct - 540) * 0.0423
            adj = round(iop - corr, 1)
            if cct < 500 and iop >= 18:
                flag = True; reasons.append("CCT < 500 um con IOP >= 18")
            if adj >= 21:
                flag = True; reasons.append(f"IOP stimata da CCT ~{adj:.1f} mmHg")
        out[eye] = {"flag": flag, "reason": "; ".join(reasons), "adj": adj}
    return out


# =========================================================
# UI PRINCIPALE
# =========================================================


# =========================================================
# CSS — TEMA CLINICO
# =========================================================

def _inject_css():
    st.markdown("""
<style>
/* Font di sistema — nessuna richiesta di rete, caricamento istantaneo */

/* 1. SFONDO */
html, body { background: #f0f4f8 !important; }
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
.main, .block-container, section.main {
    background: #f0f4f8 !important;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif !important;
}
[data-testid="stHeader"] { background: transparent !important; }

/* 2. FONT GLOBALE */
* { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif !important; box-sizing: border-box; }

/* 3. TESTO GLOBALE — risolve bianco su bianco su Chrome/Windows */
p, span, div, label, li, td, th, h1, h2, h3, h4, h5, h6, small, strong, em, a {
    color: #1e293b;
    -webkit-text-fill-color: #1e293b;
}

/* 4. INPUT / TEXTAREA */
input, textarea, select {
    background: #ffffff !important;
    color: #1e293b !important;
    -webkit-text-fill-color: #1e293b !important;
    border: 1.5px solid #cbd5e1 !important;
    border-radius: 8px !important;
    font-size: 0.93rem !important;
}
input:focus, textarea:focus {
    border-color: #2563a8 !important;
    box-shadow: 0 0 0 3px rgba(37,99,168,0.12) !important;
    outline: none !important;
}
input::placeholder, textarea::placeholder {
    color: #94a3b8 !important;
    -webkit-text-fill-color: #94a3b8 !important;
}

/* 5. NUMBER INPUT — pulsanti +/- */
[data-testid="stNumberInput"] button {
    background: #f1f5f9 !important;
    color: #334155 !important;
    -webkit-text-fill-color: #334155 !important;
    border: 1px solid #e2e8f0 !important;
}

/* 6. SELECTBOX */
[data-baseweb="select"] > div,
[data-baseweb="select"] > div > div {
    background: #ffffff !important;
    border: 1.5px solid #cbd5e1 !important;
    border-radius: 8px !important;
}
[data-baseweb="select"] *,
[data-baseweb="popover"] *,
[role="listbox"], [role="listbox"] *,
[role="option"] {
    background: #ffffff !important;
    color: #1e293b !important;
    -webkit-text-fill-color: #1e293b !important;
}
[role="option"]:hover, [role="option"][aria-selected="true"] {
    background: #eff6ff !important;
}

/* 7. METRICHE */
[data-testid="stMetric"] {
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 12px !important;
    padding: 14px 16px !important;
}
[data-testid="stMetric"] * {
    color: #1e293b !important;
    -webkit-text-fill-color: #1e293b !important;
}
[data-testid="stMetricLabel"], [data-testid="stMetricLabel"] * {
    color: #64748b !important;
    -webkit-text-fill-color: #64748b !important;
    font-size: 0.8rem !important;
}
[data-testid="stMetricValue"], [data-testid="stMetricValue"] * {
    color: #0f172a !important;
    -webkit-text-fill-color: #0f172a !important;
    font-size: 1.4rem !important;
    font-weight: 700 !important;
}

/* 8. WIDGET LABELS */
[data-testid="stWidgetLabel"], [data-testid="stWidgetLabel"] * {
    color: #475569 !important;
    -webkit-text-fill-color: #475569 !important;
    font-size: 0.85rem !important;
    font-weight: 500 !important;
}

/* 9. CAPTION */
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] * {
    color: #64748b !important;
    -webkit-text-fill-color: #64748b !important;
    font-size: 0.82rem !important;
}

/* 10. EXPANDER */
[data-testid="stExpander"] {
    background: #ffffff !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 12px !important;
}
[data-testid="stExpander"] summary {
    font-size: 0.9rem !important;
    font-weight: 500 !important;
    color: #334155 !important;
    -webkit-text-fill-color: #334155 !important;
    padding: 12px 16px !important;
}
[data-testid="stExpander"] summary * {
    color: #334155 !important;
    -webkit-text-fill-color: #334155 !important;
}
/* Freccia expander — forza colore visibile */
[data-testid="stExpander"] summary svg {
    fill: #64748b !important;
    color: #64748b !important;
    flex-shrink: 0 !important;
}

/* 11. BOTTONI — forza testo scuro su sfondo chiaro su tutti i tipi */
button,
.stButton > button,
.stDownloadButton > button,
[data-testid="stBaseButton-secondary"],
[data-testid="stBaseButton-minimal"],
[data-testid="stDownloadButton"] button {
    background: #f1f5f9 !important;
    color: #1e293b !important;
    -webkit-text-fill-color: #1e293b !important;
    border: 1.5px solid #e2e8f0 !important;
    border-radius: 10px !important;
    font-weight: 500 !important;
    font-size: 0.88rem !important;
}
button:hover,
.stButton > button:hover,
.stDownloadButton > button:hover {
    background: #e2e8f0 !important;
    color: #1e293b !important;
    -webkit-text-fill-color: #1e293b !important;
}
/* Testo dentro i bottoni — qualsiasi elemento figlio */
.stButton > button *,
.stDownloadButton > button *,
[data-testid="stBaseButton-secondary"] *,
[data-testid="stDownloadButton"] button * {
    color: #1e293b !important;
    -webkit-text-fill-color: #1e293b !important;
}
/* Bottone primario */
.stButton > button[kind="primary"],
[data-testid="stBaseButton-primary"] {
    background: #2563a8 !important;
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
    border: none !important;
}
.stButton > button[kind="primary"] *,
[data-testid="stBaseButton-primary"] * {
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
}
.stButton > button[kind="primary"]:hover,
[data-testid="stBaseButton-primary"]:hover {
    background: #1d4ed8 !important;
}
/* Bottone cancella/pericoloso */
.stButton > button[kind="primary"].danger {
    background: #dc2626 !important;
}


/* 12. ALERT */
[data-testid="stAlert"] * { -webkit-text-fill-color: inherit !important; }

/* 13. DIVIDER */
hr { border-color: #e2e8f0 !important; margin: 20px 0 !important; }

/* 14. SIDEBAR */
[data-testid="stSidebar"] {
    background: #0f1923 !important;
    border-right: 1px solid #1e2d3d;
}
[data-testid="stSidebar"] * {
    color: #c8d6e5 !important;
    -webkit-text-fill-color: #c8d6e5 !important;
}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
    font-size: 1rem !important;
}
[data-testid="stSidebar"] input {
    background: #1a2a3a !important;
    border: 1px solid #2a3d52 !important;
    color: #e2eaf2 !important;
    -webkit-text-fill-color: #e2eaf2 !important;
    border-radius: 8px !important;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label *,
[data-testid="stSidebar"] [data-testid="stRadio"] span {
    color: #c8d6e5 !important;
    -webkit-text-fill-color: #c8d6e5 !important;
    font-size: 0.87rem !important;
}

/* 15. CLASSI CUSTOM */
.vm-patient-header {
    background: linear-gradient(135deg, #1e3a5f 0%, #2563a8 100%);
    border-radius: 16px; padding: 20px 28px; margin-bottom: 20px;
}
.vm-patient-header * {
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
}
.vm-patient-name { font-size: 1.5rem !important; font-weight: 600 !important; }
.vm-patient-meta {
    font-size: 0.85rem !important;
    color: #a8c4e0 !important;
    -webkit-text-fill-color: #a8c4e0 !important;
    margin-top: 4px; font-family: 'Consolas', 'Courier New', monospace !important;
}
.vm-section-title {
    font-size: 0.72rem; font-weight: 700; letter-spacing: 0.09em;
    text-transform: uppercase;
    color: #64748b !important; -webkit-text-fill-color: #64748b !important;
    margin: 20px 0 10px; padding-bottom: 8px; border-bottom: 2px solid #e2e8f0;
}
.vm-badge-bozza {
    display: inline-block; background: #fef3c7;
    color: #92400e !important; -webkit-text-fill-color: #92400e !important;
    border-radius: 20px; padding: 3px 12px; font-size: 0.78rem; font-weight: 600;
}
.vm-badge-completa {
    display: inline-block; background: #d1fae5;
    color: #065f46 !important; -webkit-text-fill-color: #065f46 !important;
    border-radius: 20px; padding: 3px 12px; font-size: 0.78rem; font-weight: 600;
}
.vm-badge-new {
    display: inline-block; background: #dbeafe;
    color: #1e40af !important; -webkit-text-fill-color: #1e40af !important;
    border-radius: 20px; padding: 3px 12px; font-size: 0.78rem; font-weight: 600;
}
.vm-dilation-alert {
    background: #fffbeb; border: 1.5px solid #f59e0b;
    border-radius: 12px; padding: 14px 18px; margin-bottom: 16px;
    font-size: 0.92rem;
    color: #78350f !important; -webkit-text-fill-color: #78350f !important;
}
</style>
""", unsafe_allow_html=True)

def _render_nuovo_paziente_form(conn):
    """Form registrazione nuovo paziente — usato sia nella sidebar che nella pagina principale."""
    np1, np2, np3 = st.columns(3)
    nome_nuovo    = np1.text_input("Nome *",    key="vm_new_nome")
    cognome_nuovo = np2.text_input("Cognome *", key="vm_new_cognome")
    with np3:
        dn_new = _render_dmy_input("Data di nascita *", "vm_new_dn",
                                   st.session_state.get("vm_new_dn_default", date(2000, 1, 1)))
    eta_n = _calculate_age(dn_new)
    if eta_n is not None:
        st.caption(f"Età: {eta_n} anni")
    np4, np5 = st.columns(2)
    tel_nuovo  = np4.text_input("Telefono", key="vm_new_tel")
    mail_nuovo = np5.text_input("Email",    key="vm_new_mail")
    note_nuovo = st.text_area("Note", key="vm_new_note", height=60)
    if st.button("Salva paziente", key="vm_save_new_patient", type="primary"):
        try:
            pid = insert_paziente(conn, nome_nuovo, cognome_nuovo,
                                  dn_new.isoformat() if dn_new else "",
                                  telefono=tel_nuovo, email=mail_nuovo, note=note_nuovo)
            st.session_state["vision_last_pid"] = int(pid) if pid is not None else None
            st.session_state["vm_current_patient_id"] = int(pid) if pid is not None else None
            st.success(f"Paziente registrato (ID: {pid})")
            st.rerun()
        except ValueError as ve:
            st.error(str(ve))
        except Exception as e:
            st.error(f"Errore: {e}")


def _sidebar_lista_pazienti(conn, paziente_id_corrente):
    """
    Sidebar con lista pazienti via radio button — leggibile su qualsiasi tema.
    Restituisce il paziente_id selezionato.
    """
    st.sidebar.markdown("## Vision Manager")
    st.sidebar.caption("Dr. Ferraioli Giuseppe")
    st.sidebar.divider()

    ricerca = st.sidebar.text_input("🔍 Cerca", key="vm_sidebar_search",
                                    placeholder="Nome o cognome...")
    pazienti = list_pazienti(conn)

    if ricerca.strip():
        q = ricerca.strip().lower()
        pazienti = [
            r for r in pazienti
            if q in (_row_get(r,"cognome",1,"") or "").lower()
            or q in (_row_get(r,"nome",2,"") or "").lower()
        ]

    if not pazienti:
        st.sidebar.caption("Nessun paziente trovato.")
        return paziente_id_corrente

    # Bozze attive — UNA query sola per tutti i pazienti (molto più veloce)
    bozze_pids = set()
    try:
        cur_b = conn.cursor()
        cur_b.execute(
            """
            SELECT DISTINCT paziente_id
            FROM visite_visive
            WHERE COALESCE(is_deleted,0)=0
            """
        )
        pids_con_visite = {_row_get(r,"paziente_id",0) for r in cur_b.fetchall()}
        cur_b.close()
        # Controlla bozze solo per chi ha visite — query singola con JSON check
        if pids_con_visite:
            ph = _ph(conn)
            pids_list = list(pids_con_visite)
            if _is_pg(conn):
                placeholders = ",".join([ph]*len(pids_list))
                cur_b2 = conn.cursor()
                cur_b2.execute(
                    f"""
                    SELECT DISTINCT paziente_id
                    FROM visite_visive
                    WHERE paziente_id IN ({placeholders})
                      AND COALESCE(is_deleted,0)=0
                      AND dati_json::text LIKE '%"stato_visita": "BOZZA"%'
                    """,
                    pids_list,
                )
            else:
                placeholders = ",".join(["?"]*len(pids_list))
                cur_b2 = conn.cursor()
                cur_b2.execute(
                    f"""
                    SELECT DISTINCT paziente_id
                    FROM visite_visive
                    WHERE paziente_id IN ({placeholders})
                      AND COALESCE(is_deleted,0)=0
                      AND dati_json LIKE '%"stato_visita": "BOZZA"%'
                    """,
                    pids_list,
                )
            bozze_pids = {_row_get(r,"paziente_id",0) for r in cur_b2.fetchall()}
            cur_b2.close()
    except Exception:
        pass

    st.sidebar.caption(f"{len(pazienti)} pazienti attivi")

    labels = []
    pid_map = {}
    default_idx = 0
    for i, row in enumerate(pazienti):
        pid     = _row_get(row, "id", 0)
        cognome = (_row_get(row, "cognome", 1, "") or "").title()
        nome    = (_row_get(row, "nome", 2, "") or "").title()
        dn      = _row_get(row, "data_nascita", 3, "") or ""
        try:
            dn_fmt = datetime.strptime(str(dn)[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
        except Exception:
            dn_fmt = str(dn)[:10] if dn else ""
        badge = " 🟡" if pid in bozze_pids else ""
        label = f"{cognome} {nome}{badge} — {dn_fmt}" if dn_fmt else f"{cognome} {nome}{badge}"
        labels.append(label)
        pid_map[label] = pid
        if pid == paziente_id_corrente:
            default_idx = i

    chosen_label = st.sidebar.radio(
        "Pazienti",
        labels,
        index=default_idx,
        key="vm_sidebar_radio",
        label_visibility="collapsed",
    )

    st.sidebar.divider()
    st.sidebar.caption("● = bozza aperta (in dilatazione)")
    st.sidebar.divider()
    mostra_np = st.sidebar.checkbox("Nuovo paziente", key="vm_sb_nuovo_paz", value=False)
    if mostra_np:
        _render_nuovo_paziente_form(conn)

    return pid_map.get(chosen_label, paziente_id_corrente)

def ui_visita_visiva_v2(conn):
    ensure_visit_state()
    _inject_css()

    if st.session_state.get("vm_pending_form_reset"):
        _apply_form_reset()
        st.session_state["vm_pending_form_reset"] = False

    apply_pending_visit_load()

    # ── SIDEBAR — lista pazienti ─────────────────────────────
    sid_pid = _sidebar_lista_pazienti(conn, st.session_state.get("vm_current_patient_id"))

    # Gestione selezione dalla sidebar
    if sid_pid is not None and sid_pid != st.session_state.get("vm_current_patient_id"):
        if st.session_state.get("vm_form_dirty") and st.session_state.get("vm_autosave_enabled"):
            maybe_autosave(conn, st.session_state.get("vm_current_patient_id"), reason="cambio da sidebar")
        clear_visit_form()
        st.session_state["vm_current_patient_id"] = sid_pid
        st.session_state["vision_last_pid"] = sid_pid
        st.rerun()

    # Flash messages
    flash = st.session_state.pop("vm_flash_message", None)
    if flash:
        getattr(st, flash[0], st.info)(flash[1])
    autosave_status = st.session_state.pop("vm_autosave_status", None)
    if autosave_status:
        getattr(st, autosave_status[0], st.info)(autosave_status[1])

    # ── PULIZIA DUPLICATI ────────────────────────────────────
    try:
        gruppi_dup = find_duplicati_pazienti(conn)
    except Exception:
        gruppi_dup = []

    if gruppi_dup:
        n_dup = sum(len(g) - 1 for g in gruppi_dup)
        st.markdown(f'<div style="background:#fffbeb;border:1.5px solid #f59e0b;border-radius:10px;padding:10px 16px;margin-bottom:8px;font-weight:600;color:#78350f;">{len(gruppi_dup)} gruppi duplicati ({n_dup} record in eccesso)</div>', unsafe_allow_html=True)
        st.caption("Viene conservato il paziente con più visite. L'archiviazione non cancella i dati.")
        for idx_g, gruppo in enumerate(gruppi_dup):
            gruppo_sorted = sorted(gruppo, key=lambda r: (-(r.get("n_visite") or 0), -r["id"]))
            principale = gruppo_sorted[0]
            duplicati  = gruppo_sorted[1:]
            dn_fmt = ""
            if principale.get("data_nascita"):
                try:
                    dn_fmt = datetime.strptime(str(principale["data_nascita"])[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
                except Exception:
                    dn_fmt = str(principale["data_nascita"])[:10]
            st.markdown(f"**{str(principale.get('cognome','')).title()} {str(principale.get('nome','')).title()}** · {dn_fmt}")
            for dup in duplicati:
                d1, d2 = st.columns([4, 1])
                with d1:
                    st.success(f"Conserva — ID {principale['id']} ({principale.get('n_visite',0)} visite)")
                    st.warning(f"Archivia — ID {dup['id']} ({dup.get('n_visite',0)} visite)")
                with d2:
                    if st.button(f"Archivia", key=f"vm_dup_{dup['id']}_{idx_g}"):
                        try:
                            archivia_paziente_duplicato(conn, dup["id"])
                            st.success(f"ID {dup['id']} archiviato.")
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))
            st.markdown("---")

    # ── PAZIENTE NON SELEZIONATO ─────────────────────────────
    paziente_id = st.session_state.get("vm_current_patient_id")
    if paziente_id is None:
        st.markdown("""
        <div style="text-align:center;padding:80px 20px;">
            <div style="font-size:3rem;margin-bottom:16px;">👁️</div>
            <div style="font-size:1.1rem;font-weight:500;color:#64748b;">
                Seleziona un paziente dalla lista a sinistra
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.divider()
        mostra_rnp = st.checkbox("Registra nuovo paziente", key="vm_show_rnp", value=False)
        if mostra_rnp:
            _render_nuovo_paziente_form(conn)
        return

    # Recupera anagrafica
    pazienti_tutti = list_pazienti(conn)
    selected_row = None
    for row in pazienti_tutti:
        try:
            if int(_row_get(row,"id",0)) == int(paziente_id):
                selected_row = row; break
        except Exception:
            if _row_get(row,"id",0) == paziente_id:
                selected_row = row; break

    if selected_row is None:
        st.error("Paziente non trovato. Selezionane un altro dalla lista.")
        return

    cognome_paz = _row_get(selected_row, "cognome", 1, "") or ""
    nome_paz    = _row_get(selected_row, "nome", 2, "") or ""
    dn_paz      = _row_get(selected_row, "data_nascita", 3, "") or ""
    eta_paz     = _calculate_age(dn_paz)
    try:
        dn_paz_fmt = datetime.strptime(str(dn_paz)[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
    except Exception:
        dn_paz_fmt = str(dn_paz)[:10] if dn_paz else ""

    current_label = f"{cognome_paz.title()} {nome_paz.title()}".strip()

    # ── HEADER PAZIENTE ──────────────────────────────────────
    mode      = st.session_state.get("vm_mode", "new")
    loaded_id = st.session_state.get("vm_loaded_visit_id")
    stato_v   = st.session_state.get("vm_stato_visita", STATO_BOZZA)

    if mode == "edit" and loaded_id:
        if stato_v == STATO_BOZZA:
            stato_str, stato_color, stato_tc = f"BOZZA  #{loaded_id}", "#fef3c7", "#92400e"
        else:
            stato_str, stato_color, stato_tc = f"COMPLETA  #{loaded_id}", "#d1fae5", "#065f46"
    else:
        stato_str, stato_color, stato_tc = "NUOVA VISITA", "#dbeafe", "#1e40af"

    nome_display = f"{cognome_paz.title()} {nome_paz.title()}"
    meta_parts = []
    if dn_paz_fmt:
        meta_parts.append(f"Nato/a il {dn_paz_fmt}")
    if eta_paz:
        meta_parts.append(f"{eta_paz} anni")
    meta_display = "&nbsp;&nbsp;·&nbsp;&nbsp;".join(meta_parts)

    st.markdown(f"""
    <div class="vm-patient-header">
        <div class="vm-patient-name">{nome_display}</div>
        <div class="vm-patient-meta">{meta_display}</div>
        <div style="margin-top:12px;">
            <span style="display:inline-block;
                         background:{stato_color};
                         color:{stato_tc};
                         border-radius:20px;
                         padding:4px 16px;
                         font-size:0.75rem;
                         font-weight:700;
                         letter-spacing:0.05em;">
                {stato_str}
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── AZIONI VISITA (sotto l'header, chiare) ───────────────
    bozza_row = _find_bozza(conn, paziente_id)

    ac1, ac2, ac3, ac4 = st.columns([1, 2, 2, 1])
    with ac1:
        if st.button("Nuova visita", key="vm_btn_new"):
            if st.session_state.get("vm_form_dirty") and st.session_state.get("vm_autosave_enabled"):
                maybe_autosave(conn, paziente_id, reason="prima di nuova visita")
            clear_visit_form()
            st.rerun()

    with ac2:
        if (bozza_row is not None and
                (_row_get(bozza_row,"id",0) != loaded_id or not st.session_state.get("vm_in_dilatazione"))):
            bozza_id   = _row_get(bozza_row, "id", 0)
            bozza_data = str(_row_get(bozza_row, "data_visita", 1, ""))[:10]
            if st.button(f"Riprendi dopo dilatazione  (#{bozza_id} · {bozza_data})",
                         key="vm_btn_riprendi", type="primary"):
                raw = _row_get(bozza_row, "dati_json", 2)
                try:
                    st.session_state["vm_pending_load"] = {
                        "dati_json": raw,
                        "visit_id": bozza_id,
                    }
                    st.session_state["vm_flash_message"] = ("success",
                        f"Visita #{bozza_id} riaperta. Compila il fondo oculare.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore riapertura: {e}")

    with ac3:
        if st.button("Carica ultima visita completa", key="vm_btn_last"):
            for v in list_visite(conn, paziente_id):
                raw = _row_get(v, "dati_json", 2)
                try:
                    p = json.loads(raw) if isinstance(raw, str) else raw
                    if isinstance(p, dict) and p.get("stato_visita") == STATO_COMPLETA:
                        st.session_state["vm_pending_load"] = {
                            "dati_json": raw,
                            "visit_id": _row_get(v, "id", 0),
                        }
                        st.rerun()
                        break
                except Exception:
                    continue
            else:
                st.info("Nessuna visita completa trovata.")

    with ac4:
        st.checkbox("Autosave", key="vm_autosave_enabled",
                    help="Salva automaticamente prima di cambiare paziente")

    # ── MODIFICA ANAGRAFICA — checkbox invece di expander ─────
    mostra_ana = st.checkbox("Modifica dati anagrafici", key=f"vm_show_ana_{paziente_id}", value=False)
    if mostra_ana:
        st.markdown('<div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:12px;padding:16px 20px;margin-bottom:12px;">', unsafe_allow_html=True)
        ea1, ea2, ea3 = st.columns(3)
        nome_e    = ea1.text_input("Nome",    value=nome_paz,    key=f"vm_en_{paziente_id}")
        cognome_e = ea2.text_input("Cognome", value=cognome_paz, key=f"vm_ec_{paziente_id}")
        with ea3:
            dn_e = _render_dmy_input("Data di nascita", f"vm_edn_{paziente_id}", _parse_date_safe(dn_paz))
        ea4, ea5 = st.columns(2)
        tel_e  = ea4.text_input("Telefono", key=f"vm_etel_{paziente_id}")
        mail_e = ea5.text_input("Email",    key=f"vm_eml_{paziente_id}")
        note_e = st.text_area("Note anagrafiche", key=f"vm_enote_{paziente_id}", height=60)

        col_save, col_del = st.columns([2, 1])
        with col_save:
            if st.button("Salva modifiche anagrafiche", key=f"vm_esave_{paziente_id}"):
                try:
                    update_paziente(conn, paziente_id, nome_e, cognome_e,
                                    dn_e.isoformat() if dn_e else "",
                                    telefono=tel_e, email=mail_e, note=note_e)
                    st.session_state["vision_last_pid"] = int(paziente_id)
                    st.success("Anagrafica aggiornata.")
                    st.rerun()
                except (ValueError, Exception) as ex:
                    st.error(str(ex))
        with col_del:
            if st.button("Cancella paziente", key=f"vm_del_paz_btn_{paziente_id}",
                         help="Elimina definitivamente il paziente e tutte le sue visite"):
                st.session_state["vm_confirm_delete_paz"] = paziente_id

        st.markdown('</div>', unsafe_allow_html=True)

    # ── CONFERMA CANCELLAZIONE PAZIENTE ──────────────────────
    if st.session_state.get("vm_confirm_delete_paz") == paziente_id:
        st.markdown("""
        <div style="background:#fef2f2;border:2px solid #ef4444;border-radius:12px;
                    padding:16px 20px;margin-bottom:12px;">
            <div style="font-weight:700;color:#991b1b;font-size:1rem;margin-bottom:6px;">
                Stai per eliminare questo paziente
            </div>
            <div style="color:#7f1d1d;font-size:0.88rem;">
                Verranno cancellati il paziente e tutte le sue visite. Questa operazione non e reversibile.
            </div>
        </div>
        """, unsafe_allow_html=True)

        nome_conferma = st.text_input(
            f"Scrivi il cognome del paziente ({cognome_paz.upper()}) per confermare:",
            key="vm_del_paz_conferma"
        )

        dc1, dc2 = st.columns(2)
        with dc1:
            conferma_ok = nome_conferma.strip().upper() == cognome_paz.strip().upper()
            if st.button("Elimina definitivamente", key="vm_del_paz_confirm",
                         disabled=not conferma_ok):
                try:
                    _cancella_paziente(conn, paziente_id)
                    st.session_state["vm_confirm_delete_paz"] = None
                    st.session_state["vm_current_patient_id"] = None
                    st.session_state["vision_last_pid"] = None
                    clear_visit_form()
                    st.success(f"Paziente {cognome_paz} {nome_paz} eliminato.")
                    st.rerun()
                except Exception as ex:
                    st.error(f"Errore cancellazione: {ex}")
        with dc2:
            if st.button("Annulla", key="vm_del_paz_cancel"):
                st.session_state["vm_confirm_delete_paz"] = None
                st.rerun()

    # Alert dilatazione attiva
    if st.session_state.get("vm_in_dilatazione") and loaded_id:
        st.markdown(f"""
        <div class="vm-dilation-alert">
            <strong>Paziente in dilatazione</strong> &mdash; Visita #{loaded_id} aperta.<br>
            Compila il fondo oculare e l'esame obiettivo, poi salva come COMPLETA.
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # =========================================================
    # FASE 1 — ANAMNESI E VISUS
    # =========================================================
    st.markdown('<div class="vm-section-title">Fase 1 — Anamnesi e Visus</div>', unsafe_allow_html=True)

    f1a, f1b = st.columns(2)
    with f1a:
        st.selectbox("Tipo visita",
                     ["oculistica", "controllo", "post-operatorio", "urgenza"],
                     key="vm_tipo_visita", on_change=mark_visit_dirty)
    with f1b:
        st.date_input("Data visita", key="vm_data_visita", on_change=mark_visit_dirty)

    st.text_area("Anamnesi (motivo visita, storia, farmaci)",
                 key="vm_anamnesi", height=100, on_change=mark_visit_dirty)

    st.markdown("**Acuità visiva**")
    av1, av2, av3, av4 = st.columns(4)
    with av1: st.text_input("AVN OD", key="vm_acuita_naturale_od", on_change=mark_visit_dirty, help="Es. 10/10")
    with av2: st.text_input("AVN OS", key="vm_acuita_naturale_os", on_change=mark_visit_dirty)
    with av3: st.text_input("AVC OD", key="vm_acuita_corretta_od", on_change=mark_visit_dirty)
    with av4: st.text_input("AVC OS", key="vm_acuita_corretta_os", on_change=mark_visit_dirty)

    st.markdown("**Correzione abituale**")
    ca1, ca2, ca3 = st.columns(3)
    with ca1:
        st.number_input("OD SF", key="vm_ca_od_sf", step=0.25, format="%.2f", on_change=mark_visit_dirty)
        st.number_input("OS SF", key="vm_ca_os_sf", step=0.25, format="%.2f", on_change=mark_visit_dirty)
    with ca2:
        st.number_input("OD CIL", key="vm_ca_od_cyl", step=0.25, format="%.2f", on_change=mark_visit_dirty)
        st.number_input("OS CIL", key="vm_ca_os_cyl", step=0.25, format="%.2f", on_change=mark_visit_dirty)
    with ca3:
        st.number_input("OD AX", key="vm_ca_od_ax", step=1, min_value=0, max_value=180, on_change=mark_visit_dirty)
        st.number_input("OS AX", key="vm_ca_os_ax", step=1, min_value=0, max_value=180, on_change=mark_visit_dirty)

    bz1, bz2 = st.columns([2, 3])
    with bz1:
        if st.button("Salva BOZZA — paziente esce per dilatazione", key="vm_save_bozza", type="primary"):
            st.session_state["vm_stato_visita"] = STATO_BOZZA
            vid, _ = persist_current_visit(conn, paziente_id, reason="bozza fase 1")
            st.session_state["vm_in_dilatazione"] = True
            st.session_state["vm_flash_message"] = ("success",
                f"Bozza salvata (ID: {vid}). Puoi visitare un altro paziente dalla sidebar.")
            st.rerun()
    with bz2:
        st.caption("Salva e seleziona un altro paziente dalla lista a sinistra. Al ritorno usa 'Riprendi dopo dilatazione'.")

    st.divider()

    # =========================================================
    # FASE 2 — ESAME OBIETTIVO E FONDO OCULARE
    # =========================================================
    st.markdown('<div class="vm-section-title">Fase 2 — Esame obiettivo e Fondo oculare</div>', unsafe_allow_html=True)

    if (st.session_state.get("vm_stato_visita") == STATO_BOZZA
            and not st.session_state.get("vm_in_dilatazione")
            and not loaded_id):
        st.info("Compilare dopo il ritorno del paziente dalla dilatazione.")

    eo1, eo2 = st.columns(2)
    with eo1:
        st.text_input("Congiuntiva",      key="vm_congiuntiva",      on_change=mark_visit_dirty)
        st.text_input("Cornea",           key="vm_cornea",           on_change=mark_visit_dirty)
        st.text_input("Camera anteriore", key="vm_camera_anteriore", on_change=mark_visit_dirty)
        st.text_input("Cristallino",      key="vm_cristallino",      on_change=mark_visit_dirty)
        st.text_input("Vitreo",           key="vm_vitreo",           on_change=mark_visit_dirty)
    with eo2:
        st.text_input("Fondo oculare (dopo dilatazione)", key="vm_fondo_oculare", on_change=mark_visit_dirty)
        st.text_input("IOP OD (mmHg)",       key="vm_iop_od",        on_change=mark_visit_dirty)
        st.text_input("IOP OS (mmHg)",       key="vm_iop_os",        on_change=mark_visit_dirty)
        st.text_input("Pachimetria OD (µm)", key="vm_pachimetria_od", on_change=mark_visit_dirty)
        st.text_input("Pachimetria OS (µm)", key="vm_pachimetria_os", on_change=mark_visit_dirty)

    iop_od = _safe_float(st.session_state.get("vm_iop_od"), None)
    iop_os = _safe_float(st.session_state.get("vm_iop_os"), None)
    cct_od = _safe_float(st.session_state.get("vm_pachimetria_od"), None)
    cct_os = _safe_float(st.session_state.get("vm_pachimetria_os"), None)
    att = _clinical_attention(iop_od, iop_os, cct_od, cct_os)

    if any(v is not None for v in [iop_od, iop_os, cct_od, cct_os]):
        mostra_iop = st.checkbox("Mostra rapporto IOP / Pachimetria", key="vm_iop_detail", value=False)
        if mostra_iop:
            st.caption("Indicatore orientativo. Non sostituisce la valutazione specialistica.")
            r1, r2 = st.columns(2)
            for col, eye in [(r1,"od"), (r2,"os")]:
                with col:
                    st.write(f"**{eye.upper()}**")
                    if att[eye]["adj"] is not None:
                        st.write(f"IOP stimata da CCT: **{att[eye]['adj']:.1f} mmHg**")
                    if att[eye]["flag"]:
                        st.warning(att[eye]["reason"])
                    else:
                        st.success("Nessun flag.")

    st.divider()

    # =========================================================
    # FASE 3 — REFRAZIONE FINALE E PRESCRIZIONE
    # =========================================================
    st.markdown('<div class="vm-section-title">Fase 3 — Refrazione finale e Prescrizione</div>', unsafe_allow_html=True)

    cf1, cf2, cf3 = st.columns(3)
    with cf1:
        st.number_input("OD SF finale",  key="vm_cf_od_sf",  step=0.25, format="%.2f", on_change=mark_visit_dirty)
        st.number_input("OS SF finale",  key="vm_cf_os_sf",  step=0.25, format="%.2f", on_change=mark_visit_dirty)
    with cf2:
        st.number_input("OD CIL finale", key="vm_cf_od_cyl", step=0.25, format="%.2f", on_change=mark_visit_dirty)
        st.number_input("OS CIL finale", key="vm_cf_os_cyl", step=0.25, format="%.2f", on_change=mark_visit_dirty)
    with cf3:
        st.number_input("OD AX finale",  key="vm_cf_od_ax",  step=1, min_value=0, max_value=180, on_change=mark_visit_dirty)
        st.number_input("OS AX finale",  key="vm_cf_os_ax",  step=1, min_value=0, max_value=180, on_change=mark_visit_dirty)

    st.markdown("**Addizioni**")
    ad1, ad2 = st.columns(2)
    with ad1:
        st.checkbox("ADD vicino", key="vm_enable_add_vicino", on_change=mark_visit_dirty)
        st.number_input("ADD vicino", key="vm_add_vicino", step=0.25, format="%.2f", min_value=0.0,
                        disabled=not st.session_state.get("vm_enable_add_vicino", True),
                        on_change=mark_visit_dirty)
    with ad2:
        st.checkbox("ADD intermedio", key="vm_enable_add_intermedio", on_change=mark_visit_dirty)
        st.number_input("ADD intermedio", key="vm_add_intermedio", step=0.25, format="%.2f", min_value=0.0,
                        disabled=not st.session_state.get("vm_enable_add_intermedio", False),
                        on_change=mark_visit_dirty)

    st.text_area("Note cliniche libere", key="vm_note", height=90, on_change=mark_visit_dirty)

    autosave_cap = _autosave_caption()
    if autosave_cap:
        st.caption(autosave_cap)

    st.divider()

    # ── SALVATAGGIO E PDF ─────────────────────────────────────
    payload_now = build_visit_payload()
    sv1, sv2, sv3, sv4 = st.columns([2, 1, 1, 1])

    with sv1:
        lbl = f"Salva COMPLETA (#{loaded_id})" if (mode == "edit" and loaded_id) else "Salva visita COMPLETA"
        if st.button(lbl, key="vm_save_completa", type="primary"):
            st.session_state["vm_stato_visita"] = STATO_COMPLETA
            payload_fin = build_visit_payload()
            vid, act = persist_current_visit(conn, paziente_id, payload=payload_fin, reason="salvataggio completo")
            st.session_state["vm_in_dilatazione"] = False
            st.session_state["vm_flash_message"] = ("success", f"Visita {act} come COMPLETA (ID: {vid}).")
            st.rerun()

    with sv2:
        if st.session_state.get("vm_autosave_enabled") and st.session_state.get("vm_form_dirty"):
            if st.button("⚡ Autosalva", key="vm_autosave_now"):
                vid, _ = persist_current_visit(conn, paziente_id, reason="autosalvataggio manuale")
                st.success(f"Salvato (ID: {vid}).")
                st.rerun()

    with sv3:
        try:
            pdf_r = _build_referto_pdf(payload_now, patient_label=current_label, visit_id=loaded_id)
            st.download_button("PDF Referto", data=pdf_r,
                               file_name=f"referto_{current_label.replace(' ','_')}.pdf",
                               mime="application/pdf", key="vm_dl_ref")
        except Exception as e:
            st.caption(f"PDF: {e}")

    with sv4:
        try:
            pdf_p = _build_prescrizione_pdf(payload_now, patient_label=current_label, conn=conn)
            st.download_button("PDF Prescrizione", data=pdf_p,
                               file_name=f"prescrizione_{current_label.replace(' ','_')}.pdf",
                               mime="application/pdf", key="vm_dl_pr")
        except Exception as e:
            st.caption(f"PDF: {e}")

    st.divider()

    # =========================================================
    # STORICO VISITE
    # =========================================================
    st.markdown('<div class="vm-section-title">Storico visite</div>', unsafe_allow_html=True)

    visite = list_visite(conn, paziente_id)
    if not visite:
        st.info("Nessuna visita salvata per questo paziente.")
        return

    # Grafico IOP
    trend = []
    for row0 in visite:
        raw0 = _row_get(row0, "dati_json", 2)
        try:
            p0 = json.loads(raw0) if isinstance(raw0, str) else raw0
            if not isinstance(p0, dict): continue
            eo0 = p0.get("esame_obiettivo") or {}
            iop_od0 = _safe_float(eo0.get("pressione_endoculare_od"), None)
            iop_os0 = _safe_float(eo0.get("pressione_endoculare_os"), None)
            if iop_od0 is None and iop_os0 is None: continue
            d0 = dt.date.fromisoformat(str(_row_get(row0,"data_visita",1,""))[:10])
            trend.append((d0, iop_od0, iop_os0))
        except Exception:
            continue

    if len(trend) > 1:
        trend.sort(key=lambda x: x[0])
        fig, ax = plt.subplots(figsize=(8, 3))
        fig.patch.set_facecolor("#f8fafc")
        ax.set_facecolor("#f8fafc")
        ax.plot([t[0] for t in trend], [t[1] for t in trend], marker="o", color="#2563a8", label="IOP OD", linewidth=2)
        ax.plot([t[0] for t in trend], [t[2] for t in trend], marker="o", color="#0ea5e9", label="IOP OS", linewidth=2)
        ax.axhline(21, linestyle="--", linewidth=1, color="#ef4444", alpha=0.6, label="Soglia 21 mmHg")
        ax.set_ylabel("mmHg"); ax.legend(fontsize=9); ax.grid(True, alpha=0.15, color="#cbd5e1")
        ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color("#e2e8f0"); ax.spines["bottom"].set_color("#e2e8f0")
        fig.autofmt_xdate()
        st.pyplot(fig, clear_figure=True)

    # Lista visite
    visit_choices, visit_lookup = [], {}
    for row in visite:
        vid = _row_get(row, "id", 0)
        dv  = _row_get(row, "data_visita", 1, "")
        raw = _row_get(row, "dati_json", 2)
        stato_badge = ""
        try:
            p = json.loads(raw) if isinstance(raw, str) else raw
            stato = p.get("stato_visita", STATO_COMPLETA) if isinstance(p, dict) else STATO_COMPLETA
            stato_badge = "  [BOZZA]" if stato == STATO_BOZZA else "  [COMPLETA]"
        except Exception:
            pass
        label = f"Visita #{vid}  {str(dv)[:10]}{stato_badge}"
        visit_choices.append(label)
        visit_lookup[label] = row

    cur_hist_id = st.session_state.get("vm_history_selected_visit_id")
    if cur_hist_id is None or all(_row_get(r,"id",0) != cur_hist_id for r in visite):
        st.session_state["vm_history_selected_visit_id"] = _row_get(visite[0],"id",0)

    cur_hist_label = next(
        (lbl for lbl, row in visit_lookup.items()
         if _row_get(row,"id",0) == st.session_state.get("vm_history_selected_visit_id")),
        visit_choices[0]
    )

    hn1, hn2, hn3 = st.columns([1, 3, 1])
    with hn1:
        if st.button("⬅️", key="vm_hist_prev"):
            idx = visit_choices.index(cur_hist_label)
            if idx < len(visit_choices)-1:
                new_l = visit_choices[idx+1]
                st.session_state["vm_history_selected_visit_id"] = _row_get(visit_lookup[new_l],"id",0)
                st.rerun()
    with hn2:
        chosen = st.selectbox("Seleziona visita", visit_choices,
                              index=visit_choices.index(cur_hist_label),
                              key="vm_history_selected_label")
        st.session_state["vm_history_selected_visit_id"] = _row_get(visit_lookup[chosen],"id",0)
    with hn3:
        if st.button("➡️", key="vm_hist_next"):
            idx = visit_choices.index(chosen)
            if idx > 0:
                new_l = visit_choices[idx-1]
                st.session_state["vm_history_selected_visit_id"] = _row_get(visit_lookup[new_l],"id",0)
                st.rerun()

    sel_row = visit_lookup[chosen]
    sel_vid = _row_get(sel_row, "id", 0)
    sel_dv  = _row_get(sel_row, "data_visita", 1, "")
    sel_raw = _row_get(sel_row, "dati_json", 2)
    try:
        sel_preview = json.loads(sel_raw) if isinstance(sel_raw, str) else sel_raw
    except Exception:
        sel_preview = None

    if sel_preview:
        st.markdown(f'<div style="font-weight:600;color:#334155;margin:8px 0 4px;">Visita #{sel_vid} — {sel_dv}</div>', unsafe_allow_html=True)
        dp1, dp2, dp3 = st.columns(3)
        with dp1:
            stato_sel = sel_preview.get("stato_visita", STATO_COMPLETA)
            badge_sel = f'<span class="vm-badge-bozza">BOZZA</span>' if stato_sel == STATO_BOZZA else f'<span class="vm-badge-completa">COMPLETA</span>'
            st.markdown(badge_sel, unsafe_allow_html=True)
            st.write("**Tipo:**", sel_preview.get("tipo_visita","-"))
            st.write("**Anamnesi:**", _fmt_value(sel_preview.get("anamnesi")))
        with dp2:
            acuita = sel_preview.get("acuita",{}) or {}
            nat = acuita.get("naturale",{}) or {}
            cor = acuita.get("corretta",{}) or {}
            st.write("**AVN OD:**", _fmt_value(nat.get("od")))
            st.write("**AVN OS:**", _fmt_value(nat.get("os")))
            st.write("**AVC OD:**", _fmt_value(cor.get("od")))
            st.write("**AVC OS:**", _fmt_value(cor.get("os")))
        with dp3:
            eo = sel_preview.get("esame_obiettivo",{}) or {}
            st.write("**IOP OD:**",  _fmt_value(eo.get("pressione_endoculare_od")))
            st.write("**IOP OS:**",  _fmt_value(eo.get("pressione_endoculare_os")))
            st.write("**Fondo:**",   _fmt_value(eo.get("fondo_oculare")))
            cf = sel_preview.get("correzione_finale",{}) or {}
            st.write("**RX OD:**", _fmt_rx(cf.get("od")))
            st.write("**RX OS:**", _fmt_rx(cf.get("os")))

    ha1, ha2, ha3, ha4 = st.columns([1.5, 1, 1, 0.8])
    with ha1:
        if st.button("Carica questa visita", key=f"vm_load_h_{sel_vid}"):
            if st.session_state.get("vm_form_dirty"):
                maybe_autosave(conn, paziente_id, reason="prima di caricare storico")
            st.session_state["vm_pending_load"] = {
                "dati_json": sel_raw,
                "visit_id": sel_vid,
            }
            st.rerun()
    with ha2:
        if sel_preview is not None:
            try:
                pdf_rh = _build_referto_pdf(sel_preview, patient_label=current_label, visit_id=sel_vid)
                st.download_button("PDF Referto", data=pdf_rh,
                                   file_name=f"referto_{sel_vid}_{current_label.replace(' ','_')}.pdf",
                                   mime="application/pdf", key=f"vm_pdf_h_{sel_vid}")
            except Exception: pass
    with ha3:
        if sel_preview is not None:
            try:
                pdf_ph = _build_prescrizione_pdf(sel_preview, patient_label=current_label, conn=conn)
                st.download_button("PDF Prescrizione", data=pdf_ph,
                                   file_name=f"prescrizione_{sel_vid}_{current_label.replace(' ','_')}.pdf",
                                   mime="application/pdf", key=f"vm_pr_h_{sel_vid}")
            except Exception: pass
    with ha4:
        if st.button("Cancella", key=f"vm_del_{sel_vid}"):
            st.session_state["vm_delete_confirm"] = sel_vid

    delete_id = st.session_state.get("vm_delete_confirm")
    if delete_id:
        st.warning(f"Stai per cancellare la visita #{delete_id}. Confermi?")
        dc1, dc2 = st.columns(2)
        with dc1:
            if st.button("Conferma cancellazione", key="vm_del_yes", type="primary"):
                delete_visit(conn, delete_id)
                if st.session_state.get("vm_loaded_visit_id") == delete_id:
                    clear_visit_form()
                st.session_state["vm_delete_confirm"] = None
                st.success("Visita cancellata.")
                st.rerun()
        with dc2:
            if st.button("Annulla", key="vm_del_no"):
                st.session_state["vm_delete_confirm"] = None
                st.rerun()


def ui_visita_visiva():
    conn = get_conn()
    return ui_visita_visiva_v2(conn)
