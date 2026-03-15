from __future__ import annotations
import datetime as dt
import json
import streamlit as st

from vision_manager.db import get_conn
import datetime as dt
import json
import streamlit as st

# ------------------------------
# STATE
# ------------------------------
def _parse_json(s):
    try:
        return json.loads(s) if s else {}
    except Exception:
        return {}

def _list_visite(conn, paziente_id):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, data_visita, dati_json
        FROM visite_visive
        WHERE paziente_id=%s
        ORDER BY data_visita DESC, id DESC
        LIMIT 200
        """,
        (paziente_id,),
    )
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]

    return [dict(zip(cols, r)) for r in rows]


def _load_pazienti(conn):

    cur = conn.cursor()

    cur.execute(
        """
        SELECT id, cognome, nome, data_nascita
        FROM pazienti
        ORDER BY cognome, nome
        """
    )

    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]

    return [dict(zip(cols, r)) for r in rows]


def _reset_visita_form_state():

    keys = [
        "data_visita",
        "anamnesi",
    ]

    for k in keys:
        if k in st.session_state:
            del st.session_state[k]


def _load_payload_into_form(pj):

    st.session_state["anamnesi"] = pj.get("anamnesi", "")

    d = pj.get("data")

    if d:
        try:
            st.session_state["data_visita"] = dt.date.fromisoformat(str(d)[:10])
        except Exception:
            st.session_state["data_visita"] = dt.date.today()
def _init_state():
    st.session_state.setdefault("vm_mode", "new")
    st.session_state.setdefault("vm_current_visit_id", None)
    st.session_state.setdefault("data_visita", dt.date.today())
    st.session_state.setdefault("anamnesi", "")


# ------------------------------
# NEW VISIT
# ------------------------------

def _start_new_visit():
    _reset_visita_form_state()
    st.session_state["vm_mode"] = "new"
    st.session_state["vm_current_visit_id"] = None
    st.session_state["data_visita"] = dt.date.today()


# ------------------------------
# LOAD LAST VISIT
# ------------------------------

def _load_last_visit(conn, paziente_id):

    visite = _list_visite(conn, paziente_id, include_deleted=False)

    if not visite:
        st.warning("Nessuna visita trovata")
        return

    last = visite[0]

    payload = _parse_json(last.get("dati_json") or "")

    if not isinstance(payload, dict):
        st.error("Payload visita non valido")
        return

    _reset_visita_form_state()
    _load_payload_into_form(payload)

    st.session_state["vm_current_visit_id"] = last["id"]
    st.session_state["vm_mode"] = "edit"

    d = last.get("data_visita") or payload.get("data")
    if d:
        try:
            st.session_state["data_visita"] = dt.date.fromisoformat(str(d)[:10])
        except Exception:
            st.session_state["data_visita"] = dt.date.today()

    st.success(f"Caricata visita #{last['id']}")


# ------------------------------
# SAVE VISIT
# ------------------------------

def _save_visit(conn, paziente_id):

    payload = {
        "data": str(st.session_state.get("data_visita")),
        "anamnesi": st.session_state.get("anamnesi", ""),
    }

    payload_json = json.dumps(payload, ensure_ascii=False)

    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO visite_visive (paziente_id, data_visita, dati_json)
        VALUES (%s,%s,%s)
        RETURNING id
        """,
        (paziente_id, payload["data"], payload_json),
    )

    vid = cur.fetchone()[0]
    conn.commit()

    st.session_state["vm_current_visit_id"] = vid
    st.session_state["vm_mode"] = "edit"

    st.success(f"Visita salvata (ID {vid})")


# ------------------------------
# MAIN UI
# ------------------------------

def ui_visita_visiva():

    _init_state()

    topbar("Vision Manager", "Visita oculistica")

    conn = get_conn()

    pazienti = _load_pazienti(conn)

    if not pazienti:
        st.warning("Nessun paziente nel database")
        return

    psel = st.selectbox(
        "Seleziona paziente",
        pazienti,
        format_func=lambda p: f"{p['cognome']} {p['nome']} (ID {p['id']})",
    )

    paziente_id = int(psel["id"])

    badge(f"Paziente ID {paziente_id}")

    # reset se cambio paziente
    prev_pid = st.session_state.get("vm_prev_pid")

    if prev_pid != paziente_id:
        _reset_visita_form_state()
        st.session_state["vm_prev_pid"] = paziente_id
        st.session_state["vm_mode"] = "new"

    # ------------------------------
    # ACTION BUTTONS
    # ------------------------------

    col1, col2 = st.columns(2)

    with col1:
        if st.button("➕ Nuova visita"):
            _start_new_visit()

    with col2:
        if st.button("📂 Carica ultima visita"):
            _load_last_visit(conn, paziente_id)

    st.divider()

    # ------------------------------
    # FORM
    # ------------------------------

    st.session_state.setdefault("data_visita", dt.date.today())
    data_visita = st.date_input("Data visita", key="data_visita")

    st.session_state.setdefault("anamnesi", "")
    anamnesi = st.text_area(
        "Anamnesi",
        height=150,
        key="anamnesi",
    )

    st.divider()

    if st.button("💾 Salva visita"):
        _save_visit(conn, paziente_id)

    st.caption(
        f"MODE: {st.session_state.get('vm_mode')} | "
        f"VISIT_ID: {st.session_state.get('vm_current_visit_id')}"
    )
