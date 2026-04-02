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
        "vm_delete_confirm": None,
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
    """Solo pazienti ATTIVI, con data nascita per distinguere omonimi."""
    ph = _ph(conn)
    cur = conn.cursor()
    try:
        if _is_pg(conn):
            cur.execute(
                "SELECT id, cognome, nome, data_nascita FROM pazienti "
                "WHERE COALESCE(stato_paziente,'ATTIVO')='ATTIVO' ORDER BY cognome, nome"
            )
        else:
            cur.execute(
                "SELECT ID AS id, Cognome AS cognome, Nome AS nome, Data_Nascita AS data_nascita "
                "FROM Pazienti WHERE COALESCE(Stato_Paziente,'ATTIVO')='ATTIVO' ORDER BY Cognome, Nome"
            )
        return cur.fetchall()
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


def _build_prescrizione_pdf(payload, patient_label="Paziente"):
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
    return build_prescrizione_occhiali_a4(data_pdf, LETTERHEAD)


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

def ui_visita_visiva_v2(conn):
    ensure_visit_state()

    if st.session_state.get("vm_pending_form_reset"):
        _apply_form_reset()
        st.session_state["vm_pending_form_reset"] = False

    apply_pending_visit_load()

    st.title("Vision Manager")

    # Flash
    flash = st.session_state.pop("vm_flash_message", None)
    if flash:
        getattr(st, flash[0], st.info)(flash[1])
    autosave_status = st.session_state.pop("vm_autosave_status", None)
    if autosave_status:
        getattr(st, autosave_status[0], st.info)(autosave_status[1])

    # ── NUOVO PAZIENTE ────────────────────────────────────────
    with st.expander("Registra nuovo paziente", expanded=False):
        np1, np2, np3 = st.columns(3)
        nome_nuovo    = np1.text_input("Nome *",    key="vm_new_nome")
        cognome_nuovo = np2.text_input("Cognome *", key="vm_new_cognome")
        with np3:
            dn_new = _render_dmy_input("Data di nascita *", "vm_new_dn",
                                       st.session_state.get("vm_new_dn_default", date(2000,1,1)))
        eta_n = _calculate_age(dn_new)
        if eta_n is not None:
            st.caption(f"Eta: {eta_n} anni")
        np4, np5 = st.columns(2)
        tel_nuovo  = np4.text_input("Telefono", key="vm_new_tel")
        mail_nuovo = np5.text_input("Email",    key="vm_new_mail")
        note_nuovo = st.text_area("Note", key="vm_new_note", height=60)
        if st.button("Salva nuovo paziente", key="vm_save_new_patient"):
            try:
                pid = insert_paziente(conn, nome_nuovo, cognome_nuovo,
                                      dn_new.isoformat() if dn_new else "",
                                      telefono=tel_nuovo, email=mail_nuovo, note=note_nuovo)
                st.session_state["vision_last_pid"] = int(pid) if pid is not None else None
                st.success(f"Paziente registrato (ID: {pid})")
                st.rerun()
            except ValueError as ve:
                st.error(str(ve))
            except Exception as e:
                st.error(f"Errore: {e}")

    st.divider()

    # ── SELETTORE PAZIENTE ────────────────────────────────────
    pazienti = list_pazienti(conn)
    if not pazienti:
        st.warning("Nessun paziente attivo. Registra prima un paziente.")
        return

    pazienti_options, pazienti_map = [], {}
    for row in pazienti:
        label = _label_paziente(row)
        pid   = _row_get(row, "id", 0)
        pazienti_options.append(label)
        pazienti_map[label] = pid

    # Ricorda ultimo paziente
    default_idx = 0
    last_pid = st.session_state.get("vision_last_pid")
    if last_pid is not None:
        for i, row in enumerate(pazienti):
            try:
                if int(_row_get(row, "id", 0)) == int(last_pid):
                    default_idx = i; break
            except Exception:
                pass

    forced = st.session_state.pop("vm_force_selected_paziente_label", None)
    if forced and forced in pazienti_map:
        st.session_state["vm_selected_paziente_label"] = forced
    elif (not st.session_state.get("vm_selected_paziente_label")
          or st.session_state.get("vm_selected_paziente_label") not in pazienti_map):
        st.session_state["vm_selected_paziente_label"] = pazienti_options[default_idx]

    selected_label = st.selectbox("Seleziona paziente", pazienti_options,
                                  key="vm_selected_paziente_label")
    requested_pid = pazienti_map[selected_label]

    if st.session_state.get("vm_current_patient_id") is None:
        st.session_state["vm_current_patient_id"] = requested_pid
        st.session_state["vision_last_pid"] = requested_pid

    paziente_id   = st.session_state["vm_current_patient_id"]
    current_label = _label_for_pid(pazienti_map, paziente_id) or selected_label

    # Gestione cambio paziente
    if requested_pid != paziente_id:
        if st.session_state.get("vm_form_dirty") and st.session_state.get("vm_autosave_enabled"):
            maybe_autosave(conn, paziente_id, reason="prima cambio paziente")
            clear_visit_form()
            st.session_state.update({"vm_current_patient_id": requested_pid,
                                     "vision_last_pid": requested_pid,
                                     "vm_flash_message": ("success", "Bozza autosalvata.")})
            st.rerun()
        elif st.session_state.get("vm_form_dirty"):
            st.warning("Modifiche non salvate. Come vuoi procedere?")
            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("Autosalva e cambia", key="vm_force_switch"):
                    persist_current_visit(conn, paziente_id, reason="prima cambio paziente")
                    clear_visit_form()
                    st.session_state.update({"vm_current_patient_id": requested_pid,
                                             "vision_last_pid": requested_pid,
                                             "vm_force_selected_paziente_label": selected_label})
                    st.rerun()
            with c2:
                if st.button("Cambia senza salvare", key="vm_discard_switch"):
                    clear_visit_form()
                    st.session_state.update({"vm_current_patient_id": requested_pid,
                                             "vision_last_pid": requested_pid,
                                             "vm_force_selected_paziente_label": selected_label})
                    st.rerun()
            with c3:
                if st.button("Rimani qui", key="vm_cancel_switch"):
                    cl = _label_for_pid(pazienti_map, paziente_id)
                    if cl:
                        st.session_state["vm_force_selected_paziente_label"] = cl
                    st.rerun()
            st.stop()
        else:
            clear_visit_form()
            st.session_state.update({"vm_current_patient_id": requested_pid,
                                     "vision_last_pid": requested_pid})
            st.rerun()

    # Recupera anagrafica paziente corrente
    selected_row = None
    for row in pazienti:
        try:
            if int(_row_get(row, "id", 0)) == int(paziente_id):
                selected_row = row; break
        except Exception:
            if _row_get(row, "id", 0) == paziente_id:
                selected_row = row; break

    cognome_paz  = _row_get(selected_row, "cognome", 1, "") if selected_row else ""
    nome_paz     = _row_get(selected_row, "nome", 2, "") if selected_row else ""
    dn_paz       = _row_get(selected_row, "data_nascita", 3, "") if selected_row else ""
    eta_paz = _calculate_age(dn_paz)

    ci1, ci2 = st.columns([3, 1])
    with ci1:
        st.markdown(f"### {cognome_paz} {nome_paz}")
    with ci2:
        if eta_paz is not None:
            st.metric("Eta", f"{eta_paz} anni")

    # Modifica anagrafica
    with st.expander("Modifica anagrafica", expanded=False):
        ea1, ea2, ea3 = st.columns(3)
        nome_e    = ea1.text_input("Nome",    value=nome_paz,    key=f"vm_en_{paziente_id}")
        cognome_e = ea2.text_input("Cognome", value=cognome_paz, key=f"vm_ec_{paziente_id}")
        with ea3:
            dn_e = _render_dmy_input("Data di nascita", f"vm_edn_{paziente_id}",
                                     _parse_date_safe(dn_paz))
        ea4, ea5 = st.columns(2)
        tel_e  = ea4.text_input("Telefono", key=f"vm_etel_{paziente_id}")
        mail_e = ea5.text_input("Email",    key=f"vm_eml_{paziente_id}")
        note_e = st.text_area("Note", key=f"vm_enote_{paziente_id}", height=60)
        if st.button("Salva", key=f"vm_esave_{paziente_id}"):
            try:
                update_paziente(conn, paziente_id, nome_e, cognome_e,
                                dn_e.isoformat() if dn_e else "",
                                telefono=tel_e, email=mail_e, note=note_e)
                st.session_state["vision_last_pid"] = int(paziente_id)
                st.success("Anagrafica aggiornata.")
                st.rerun()
            except (ValueError, Exception) as ex:
                st.error(str(ex))

    st.divider()

    # ── PULSANTI AZIONE VISITA ────────────────────────────────
    bozza_row = _find_bozza(conn, paziente_id)
    loaded_id = st.session_state.get("vm_loaded_visit_id")

    tc1, tc2, tc3, tc4, tc5 = st.columns([1, 1.6, 1.6, 0.8, 1])

    with tc1:
        if st.button("Nuova visita", key="vm_btn_new"):
            if st.session_state.get("vm_form_dirty") and st.session_state.get("vm_autosave_enabled"):
                maybe_autosave(conn, paziente_id, reason="prima di nuova visita")
            clear_visit_form()
            st.rerun()

    with tc2:
        if (bozza_row is not None
                and (_row_get(bozza_row, "id", 0) != loaded_id
                     or not st.session_state.get("vm_in_dilatazione"))):
            bozza_id   = _row_get(bozza_row, "id", 0)
            bozza_data = str(_row_get(bozza_row, "data_visita", 1, ""))[:10]
            if st.button(f"Riprendi dopo dilatazione  (bozza #{bozza_id}  {bozza_data})",
                         key="vm_btn_riprendi", type="primary"):
                raw = _row_get(bozza_row, "dati_json", 2)
                try:
                    load_visit_payload(json.loads(raw) if isinstance(raw, str) else raw,
                                       visit_id=bozza_id)
                    st.session_state["vm_flash_message"] = ("success",
                        f"Visita #{bozza_id} riaperta. Compila il fondo oculare e l'esame obiettivo.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore riapertura bozza: {e}")

    with tc3:
        if st.button("Carica ultima visita completa", key="vm_btn_last"):
            for v in list_visite(conn, paziente_id):
                raw = _row_get(v, "dati_json", 2)
                try:
                    p = json.loads(raw) if isinstance(raw, str) else raw
                    if isinstance(p, dict) and p.get("stato_visita") == STATO_COMPLETA:
                        load_visit_payload(p, visit_id=_row_get(v, "id", 0))
                        st.rerun()
                        break
                except Exception:
                    continue
            else:
                st.info("Nessuna visita completa trovata.")

    with tc4:
        st.checkbox("Autosave", key="vm_autosave_enabled")

    with tc5:
        mode = st.session_state.get("vm_mode", "new")
        stato_v = st.session_state.get("vm_stato_visita", STATO_BOZZA)
        if mode == "edit" and loaded_id:
            badge = "Bozza" if stato_v == STATO_BOZZA else "Completa"
            col   = "warning" if stato_v == STATO_BOZZA else "success"
            getattr(st, col)(f"Visita #{loaded_id} - {badge}")
        else:
            st.info("Nuova visita")

    if st.session_state.get("vm_in_dilatazione") and loaded_id:
        st.warning(
            f"Paziente in dilatazione — Visita #{loaded_id} aperta. "
            "Compila fondo oculare ed esame obiettivo, poi salva come COMPLETA."
        )

    st.divider()

    # =========================================================
    # FASE 1 — ANAMNESI E VISUS
    # =========================================================
    st.subheader("Fase 1 — Anamnesi e Visus")

    f1a, f1b = st.columns(2)
    with f1a:
        st.selectbox("Tipo visita",
                     ["oculistica", "controllo", "post-operatorio", "urgenza"],
                     key="vm_tipo_visita", on_change=mark_visit_dirty)
    with f1b:
        st.date_input("Data visita", key="vm_data_visita", on_change=mark_visit_dirty)

    st.text_area("Anamnesi (motivo visita, storia, farmaci)",
                 key="vm_anamnesi", height=100, on_change=mark_visit_dirty)

    st.markdown("**Acuita visiva**")
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

    st.divider()
    bz1, bz2 = st.columns([1.5, 3])
    with bz1:
        if st.button("Salva BOZZA — paziente va a dilatarsi", key="vm_save_bozza",
                     type="primary",
                     help="Salva anamnesi + visus. Il paziente esce. Poi clicca Riprendi dopo dilatazione."):
            st.session_state["vm_stato_visita"] = STATO_BOZZA
            vid, act = persist_current_visit(conn, paziente_id, reason="bozza fase 1")
            st.session_state["vm_in_dilatazione"] = True
            st.session_state["vm_flash_message"] = ("success",
                f"Bozza salvata (ID: {vid}). Puoi visitare un altro paziente.")
            st.rerun()
    with bz2:
        st.caption("Dopo aver salvato la bozza, seleziona un altro paziente. "
                   "Al ritorno del paziente usa 'Riprendi dopo dilatazione'.")

    st.divider()

    # =========================================================
    # FASE 2 — ESAME OBIETTIVO E FONDO OCULARE
    # =========================================================
    st.subheader("Fase 2 — Esame obiettivo e Fondo oculare")

    if (st.session_state.get("vm_stato_visita") == STATO_BOZZA
            and not st.session_state.get("vm_in_dilatazione")
            and not loaded_id):
        st.info("Questa sezione si compila dopo il ritorno del paziente dalla dilatazione.")

    eo1, eo2 = st.columns(2)
    with eo1:
        st.text_input("Congiuntiva",      key="vm_congiuntiva",      on_change=mark_visit_dirty)
        st.text_input("Cornea",           key="vm_cornea",           on_change=mark_visit_dirty)
        st.text_input("Camera anteriore", key="vm_camera_anteriore", on_change=mark_visit_dirty)
        st.text_input("Cristallino",      key="vm_cristallino",      on_change=mark_visit_dirty)
        st.text_input("Vitreo",           key="vm_vitreo",           on_change=mark_visit_dirty)
    with eo2:
        st.text_input("Fondo oculare (dopo dilatazione)", key="vm_fondo_oculare",
                      on_change=mark_visit_dirty)
        st.text_input("IOP OD (mmHg)",      key="vm_iop_od",       on_change=mark_visit_dirty)
        st.text_input("IOP OS (mmHg)",      key="vm_iop_os",       on_change=mark_visit_dirty)
        st.text_input("Pachimetria OD (um)", key="vm_pachimetria_od", on_change=mark_visit_dirty)
        st.text_input("Pachimetria OS (um)", key="vm_pachimetria_os", on_change=mark_visit_dirty)

    iop_od = _safe_float(st.session_state.get("vm_iop_od"), None)
    iop_os = _safe_float(st.session_state.get("vm_iop_os"), None)
    cct_od = _safe_float(st.session_state.get("vm_pachimetria_od"), None)
    cct_os = _safe_float(st.session_state.get("vm_pachimetria_os"), None)
    att = _clinical_attention(iop_od, iop_os, cct_od, cct_os)

    if any(v is not None for v in [iop_od, iop_os, cct_od, cct_os]):
        with st.expander("Rapporto IOP / Pachimetria (CCT)", expanded=False):
            st.caption("Indicatore orientativo. Non sostituisce la valutazione specialistica.")
            r1, r2 = st.columns(2)
            for col, eye in [(r1, "od"), (r2, "os")]:
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
    st.subheader("Fase 3 — Refrazione finale e Prescrizione")

    cf1, cf2, cf3 = st.columns(3)
    with cf1:
        st.number_input("OD SF finale", key="vm_cf_od_sf", step=0.25, format="%.2f", on_change=mark_visit_dirty)
        st.number_input("OS SF finale", key="vm_cf_os_sf", step=0.25, format="%.2f", on_change=mark_visit_dirty)
    with cf2:
        st.number_input("OD CIL finale", key="vm_cf_od_cyl", step=0.25, format="%.2f", on_change=mark_visit_dirty)
        st.number_input("OS CIL finale", key="vm_cf_os_cyl", step=0.25, format="%.2f", on_change=mark_visit_dirty)
    with cf3:
        st.number_input("OD AX finale", key="vm_cf_od_ax", step=1, min_value=0, max_value=180, on_change=mark_visit_dirty)
        st.number_input("OS AX finale", key="vm_cf_os_ax", step=1, min_value=0, max_value=180, on_change=mark_visit_dirty)

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

    # ── PULSANTI SALVATAGGIO E PDF ────────────────────────────
    sv1, sv2, sv3, sv4 = st.columns([1.5, 1, 1, 1])
    payload_now = build_visit_payload()
    mode = st.session_state.get("vm_mode", "new")

    with sv1:
        lbl = f"Salva COMPLETA (#{loaded_id})" if (mode == "edit" and loaded_id) else "Salva visita COMPLETA"
        if st.button(lbl, key="vm_save_completa", type="primary"):
            st.session_state["vm_stato_visita"] = STATO_COMPLETA
            payload_fin = build_visit_payload()
            vid, act = persist_current_visit(conn, paziente_id, payload=payload_fin,
                                             reason="salvataggio completo")
            st.session_state["vm_in_dilatazione"] = False
            st.session_state["vm_flash_message"] = ("success", f"Visita {act} come COMPLETA (ID: {vid}).")
            st.rerun()

    with sv2:
        if st.session_state.get("vm_autosave_enabled") and st.session_state.get("vm_form_dirty"):
            if st.button("Autosalva ora", key="vm_autosave_now"):
                vid, act = persist_current_visit(conn, paziente_id, reason="autosalvataggio manuale")
                st.success(f"Salvato (ID: {vid}).")
                st.rerun()

    with sv3:
        try:
            pdf_r = _build_referto_pdf(payload_now, patient_label=current_label, visit_id=loaded_id)
            st.download_button("PDF Referto", data=pdf_r,
                               file_name=f"referto_{current_label.replace(' ','_')}.pdf",
                               mime="application/pdf", key="vm_dl_ref")
        except Exception as e:
            st.caption(f"PDF non disponibile: {e}")

    with sv4:
        try:
            pdf_p = _build_prescrizione_pdf(payload_now, patient_label=current_label)
            st.download_button("PDF Prescrizione", data=pdf_p,
                               file_name=f"prescrizione_{current_label.replace(' ','_')}.pdf",
                               mime="application/pdf", key="vm_dl_pr")
        except Exception as e:
            st.caption(f"PDF non disponibile: {e}")

    st.divider()

    # =========================================================
    # STORICO VISITE
    # =========================================================
    st.subheader("Storico visite")

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
            d0 = dt.date.fromisoformat(str(_row_get(row0, "data_visita", 1, ""))[:10])
            trend.append((d0, iop_od0, iop_os0))
        except Exception:
            continue

    if len(trend) > 1:
        trend.sort(key=lambda x: x[0])
        fig, ax = plt.subplots(figsize=(8, 3))
        ax.plot([t[0] for t in trend], [t[1] for t in trend], marker="o", label="IOP OD")
        ax.plot([t[0] for t in trend], [t[2] for t in trend], marker="o", label="IOP OS")
        ax.axhline(21, linestyle="--", linewidth=1, color="red", alpha=0.5, label="Soglia 21 mmHg")
        ax.set_ylabel("mmHg"); ax.legend(); ax.grid(True, alpha=0.2)
        fig.autofmt_xdate()
        st.pyplot(fig, clear_figure=True)

    # Lista navigabile
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
        st.session_state["vm_history_selected_visit_id"] = _row_get(visite[0], "id", 0)

    cur_hist_label = next(
        (lbl for lbl, row in visit_lookup.items()
         if _row_get(row,"id",0) == st.session_state.get("vm_history_selected_visit_id")),
        visit_choices[0]
    )

    hn1, hn2, hn3 = st.columns([1, 3, 1])
    with hn1:
        if st.button("Prec.", key="vm_hist_prev"):
            idx = visit_choices.index(cur_hist_label)
            if idx < len(visit_choices)-1:
                new_l = visit_choices[idx+1]
                st.session_state["vm_history_selected_visit_id"] = _row_get(visit_lookup[new_l],"id",0)
                st.rerun()
    with hn2:
        chosen = st.selectbox("Naviga storico", visit_choices,
                              index=visit_choices.index(cur_hist_label),
                              key="vm_history_selected_label")
        st.session_state["vm_history_selected_visit_id"] = _row_get(visit_lookup[chosen],"id",0)
    with hn3:
        if st.button("Succ.", key="vm_hist_next"):
            idx = visit_choices.index(chosen)
            if idx > 0:
                new_l = visit_choices[idx-1]
                st.session_state["vm_history_selected_visit_id"] = _row_get(visit_lookup[new_l],"id",0)
                st.rerun()

    sel_row  = visit_lookup[chosen]
    sel_vid  = _row_get(sel_row, "id", 0)
    sel_dv   = _row_get(sel_row, "data_visita", 1, "")
    sel_raw  = _row_get(sel_row, "dati_json", 2)
    try:
        sel_preview = json.loads(sel_raw) if isinstance(sel_raw, str) else sel_raw
    except Exception:
        sel_preview = None

    if sel_preview:
        with st.expander(f"Dettaglio visita #{sel_vid}  {sel_dv}", expanded=True):
            dp1, dp2, dp3 = st.columns(3)
            with dp1:
                st.write("**Tipo:**",  sel_preview.get("tipo_visita", "-"))
                st.write("**Stato:**", sel_preview.get("stato_visita", STATO_COMPLETA))
                st.write("**Anamnesi:**", _fmt_value(sel_preview.get("anamnesi")))
            with dp2:
                acuita = sel_preview.get("acuita", {}) or {}
                nat = acuita.get("naturale", {}) or {}
                cor = acuita.get("corretta", {}) or {}
                st.write("**AVN OD:**", _fmt_value(nat.get("od")))
                st.write("**AVN OS:**", _fmt_value(nat.get("os")))
                st.write("**AVC OD:**", _fmt_value(cor.get("od")))
                st.write("**AVC OS:**", _fmt_value(cor.get("os")))
            with dp3:
                eo = sel_preview.get("esame_obiettivo", {}) or {}
                st.write("**IOP OD:**",  _fmt_value(eo.get("pressione_endoculare_od")))
                st.write("**IOP OS:**",  _fmt_value(eo.get("pressione_endoculare_os")))
                st.write("**Fondo:**",   _fmt_value(eo.get("fondo_oculare")))
                cf = sel_preview.get("correzione_finale", {}) or {}
                st.write("**RX OD:**", _fmt_rx(cf.get("od")))
                st.write("**RX OS:**", _fmt_rx(cf.get("os")))

    ha1, ha2, ha3, ha4 = st.columns([1.2, 1, 1, 0.8])
    with ha1:
        if st.button("Carica questa visita", key=f"vm_load_h_{sel_vid}"):
            if st.session_state.get("vm_form_dirty"):
                maybe_autosave(conn, paziente_id, reason="prima di caricare storico")
            payload_load = json.loads(sel_raw) if isinstance(sel_raw, str) else sel_raw
            load_visit_payload(payload_load, visit_id=sel_vid)
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
                pdf_ph = _build_prescrizione_pdf(sel_preview, patient_label=current_label)
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
            if st.button("Conferma", key="vm_del_yes", type="primary"):
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
