import streamlit as st
import datetime as dt
import json

from vision_manager.db import get_conn


# ------------------------------
# UTILS
# ------------------------------

def parse_json(s):
    try:
        return json.loads(s) if s else {}
    except Exception:
        return {}


def list_pazienti(conn):

    cur = conn.cursor()

    cur.execute("""
        SELECT id, cognome, nome, data_nascita
        FROM pazienti
        ORDER BY cognome, nome
    """)

    rows = cur.fetchall()

    pazienti = []
    for r in rows:
        pazienti.append({
            "id": r[0],
            "cognome": r[1],
            "nome": r[2],
            "data_nascita": r[3]
        })

    return pazienti


def list_visite(conn, paziente_id):

    cur = conn.cursor()

    cur.execute("""
        SELECT id, data_visita, dati_json
        FROM visite_visive
        WHERE paziente_id = %s
        AND (is_deleted IS NULL OR is_deleted = FALSE)
        ORDER BY data_visita DESC, id DESC
    """, (paziente_id,))

    rows = cur.fetchall()

    visite = []
    for r in rows:
        visite.append({
            "id": r[0],
            "data_visita": r[1],
            "dati_json": r[2]
        })

    return visite


# ------------------------------
# FORM STATE
# ------------------------------

def reset_form():

    keys = [
        "data_visita",
        "anamnesi",
    ]

    for k in keys:
        if k in st.session_state:
            del st.session_state[k]


def start_new_visit():

    reset_form()

    st.session_state["data_visita"] = dt.date.today()
    st.session_state["anamnesi"] = ""

    st.session_state["vm_mode"] = "new"
    st.session_state["vm_visit_id"] = None


def load_last_visit(conn, paziente_id):

    visite = list_visite(conn, paziente_id)

    if not visite:
        st.warning("Nessuna visita trovata")
        return

    last = visite[0]

    payload = parse_json(last["dati_json"])

    reset_form()

    st.session_state["data_visita"] = last["data_visita"]

    st.session_state["anamnesi"] = payload.get("anamnesi", "")

    st.session_state["vm_visit_id"] = last["id"]
    st.session_state["vm_mode"] = "edit"

    st.success(f"Caricata visita ID {last['id']}")


def save_visit(conn, paziente_id):

    payload = {
        "anamnesi": st.session_state.get("anamnesi", ""),
        "data": str(st.session_state.get("data_visita"))
    }

    payload_json = json.dumps(payload, ensure_ascii=False)

    cur = conn.cursor()

    cur.execute("""
        INSERT INTO visite_visive (paziente_id, data_visita, dati_json)
        VALUES (%s, %s, %s)
        RETURNING id
    """, (
        paziente_id,
        payload["data"],
        payload_json
    ))

    vid = cur.fetchone()[0]

    conn.commit()

    st.session_state["vm_visit_id"] = vid
    st.session_state["vm_mode"] = "edit"

    st.success(f"Visita salvata (ID {vid})")


# ------------------------------
# UI
# ------------------------------

def ui_visita_visiva():

    st.title("Vision Manager")
    st.caption("Visita visiva")

    conn = get_conn()

    pazienti = list_pazienti(conn)

    if not pazienti:
        st.warning("Nessun paziente nel database")
        return

    psel = st.selectbox(
        "Seleziona paziente",
        pazienti,
        format_func=lambda p: f"{p['cognome']} {p['nome']} (ID {p['id']})"
    )

    if not psel:
        st.stop()

    paziente_id = int(psel["id"])

    # reset se cambio paziente
    prev_pid = st.session_state.get("vm_prev_pid")

    if prev_pid != paziente_id:
        reset_form()
        st.session_state["vm_prev_pid"] = paziente_id

    # ------------------------------
    # BUTTONS
    # ------------------------------

    col1, col2 = st.columns(2)

    with col1:
        if st.button("➕ Nuova visita"):
            start_new_visit()

    with col2:
        if st.button("📂 Carica ultima visita"):
            load_last_visit(conn, paziente_id)

    st.divider()

    # ------------------------------
    # FORM
    # ------------------------------

    st.session_state.setdefault("data_visita", dt.date.today())

    st.date_input(
        "Data visita",
        key="data_visita"
    )

    st.session_state.setdefault("anamnesi", "")

    st.text_area(
        "Anamnesi",
        height=200,
        key="anamnesi"
    )

    st.divider()

    if st.button("💾 Salva visita"):
        save_visit(conn, paziente_id)

    st.caption(
        f"MODE: {st.session_state.get('vm_mode')} | "
        f"VISIT_ID: {st.session_state.get('vm_visit_id')}"
    )
