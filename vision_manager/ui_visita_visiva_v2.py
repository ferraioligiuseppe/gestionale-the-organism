import streamlit as st
import json
from datetime import date, datetime


# -----------------------------
# UTIL
# -----------------------------

def _parse_date_safe(v):
    if not v:
        return date.today()
    if isinstance(v, date):
        return v
    try:
        return datetime.strptime(str(v), "%Y-%m-%d").date()
    except:
        return date.today()


def _safe_float(v, default=0.0):
    try:
        if v in (None, ""):
            return default
        return float(v)
    except:
        return default


def _safe_int(v, default=0):
    try:
        if v in (None, ""):
            return default
        return int(float(v))
    except:
        return default


# -----------------------------
# SESSION STATE INIT
# -----------------------------

def ensure_visit_state():

    defaults = {

        "vm_tipo_visita": "oculistica",
        "vm_data_visita": date.today(),
        "vm_anamnesi": "",

        "vm_acuita_naturale_od": "",
        "vm_acuita_naturale_os": "",
        "vm_acuita_corretta_od": "",
        "vm_acuita_corretta_os": "",

        "vm_congiuntiva": "",
        "vm_cornea": "",
        "vm_camera_anteriore": "",
        "vm_cristallino": "",
        "vm_vitreo": "",
        "vm_fondo_oculare": "",
        "vm_iop_od": "",
        "vm_iop_os": "",
        "vm_pachimetria_od": "",
        "vm_pachimetria_os": "",

        "vm_ca_od_sf": 0.0,
        "vm_ca_od_cyl": 0.0,
        "vm_ca_od_ax": 0,

        "vm_ca_os_sf": 0.0,
        "vm_ca_os_cyl": 0.0,
        "vm_ca_os_ax": 0,

        "vm_cf_od_sf": 0.0,
        "vm_cf_od_cyl": 0.0,
        "vm_cf_od_ax": 0,

        "vm_cf_os_sf": 0.0,
        "vm_cf_os_cyl": 0.0,
        "vm_cf_os_ax": 0,

        "vm_note": "",

        "vm_pending_load": None,
        "vm_loaded_visit_id": None,
        "vm_mode": "new"
    }

    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# -----------------------------
# CLEAR FORM
# -----------------------------

def clear_visit_form():

    st.session_state["vm_data_visita"] = date.today()
    st.session_state["vm_anamnesi"] = ""

    st.session_state["vm_acuita_naturale_od"] = ""
    st.session_state["vm_acuita_naturale_os"] = ""
    st.session_state["vm_acuita_corretta_od"] = ""
    st.session_state["vm_acuita_corretta_os"] = ""

    st.session_state["vm_congiuntiva"] = ""
    st.session_state["vm_cornea"] = ""
    st.session_state["vm_camera_anteriore"] = ""
    st.session_state["vm_cristallino"] = ""
    st.session_state["vm_vitreo"] = ""
    st.session_state["vm_fondo_oculare"] = ""

    st.session_state["vm_iop_od"] = ""
    st.session_state["vm_iop_os"] = ""

    st.session_state["vm_pachimetria_od"] = ""
    st.session_state["vm_pachimetria_os"] = ""

    st.session_state["vm_note"] = ""


# -----------------------------
# LOAD VISIT
# -----------------------------

def load_visit_payload(payload, visit_id=None):

    acuita = payload.get("acuita", {})
    naturale = acuita.get("naturale", {})
    corretta = acuita.get("corretta", {})

    esame = payload.get("esame_obiettivo", {})

    st.session_state["vm_data_visita"] = _parse_date_safe(payload.get("data"))
    st.session_state["vm_anamnesi"] = payload.get("anamnesi", "")

    st.session_state["vm_acuita_naturale_od"] = naturale.get("od", "")
    st.session_state["vm_acuita_naturale_os"] = naturale.get("os", "")

    st.session_state["vm_acuita_corretta_od"] = corretta.get("od", "")
    st.session_state["vm_acuita_corretta_os"] = corretta.get("os", "")

    st.session_state["vm_congiuntiva"] = esame.get("congiuntiva", "")
    st.session_state["vm_cornea"] = esame.get("cornea", "")
    st.session_state["vm_camera_anteriore"] = esame.get("camera_anteriore", "")
    st.session_state["vm_cristallino"] = esame.get("cristallino", "")
    st.session_state["vm_vitreo"] = esame.get("vitreo", "")
    st.session_state["vm_fondo_oculare"] = esame.get("fondo_oculare", "")

    st.session_state["vm_iop_od"] = esame.get("pressione_endoculare_od", "")
    st.session_state["vm_iop_os"] = esame.get("pressione_endoculare_os", "")

    st.session_state["vm_pachimetria_od"] = esame.get("pachimetria_od", "")
    st.session_state["vm_pachimetria_os"] = esame.get("pachimetria_os", "")

    st.session_state["vm_note"] = payload.get("note", "")

    st.session_state["vm_loaded_visit_id"] = visit_id


# -----------------------------
# APPLY PENDING LOAD
# -----------------------------

def apply_pending_visit_load():

    pending = st.session_state.pop("vm_pending_load", None)

    if not pending:
        return

    raw = pending.get("dati_json")
    visit_id = pending.get("visit_id")

    if isinstance(raw, str):
        payload = json.loads(raw)
    else:
        payload = raw

    load_visit_payload(payload, visit_id)


# -----------------------------
# BUILD JSON
# -----------------------------

def build_visit_payload():

    payload = {

        "tipo_visita": "oculistica",

        "data": str(st.session_state["vm_data_visita"]),

        "anamnesi": st.session_state["vm_anamnesi"],

        "acuita": {

            "naturale": {

                "od": st.session_state["vm_acuita_naturale_od"],
                "os": st.session_state["vm_acuita_naturale_os"]
            },

            "corretta": {

                "od": st.session_state["vm_acuita_corretta_od"],
                "os": st.session_state["vm_acuita_corretta_os"]
            }
        },

        "esame_obiettivo": {

            "congiuntiva": st.session_state["vm_congiuntiva"],
            "cornea": st.session_state["vm_cornea"],
            "camera_anteriore": st.session_state["vm_camera_anteriore"],
            "cristallino": st.session_state["vm_cristallino"],
            "vitreo": st.session_state["vm_vitreo"],
            "fondo_oculare": st.session_state["vm_fondo_oculare"],

            "pressione_endoculare_od": st.session_state["vm_iop_od"],
            "pressione_endoculare_os": st.session_state["vm_iop_os"],

            "pachimetria_od": st.session_state["vm_pachimetria_od"],
            "pachimetria_os": st.session_state["vm_pachimetria_os"]
        },

        "note": st.session_state["vm_note"]
    }

    return payload


# -----------------------------
# MAIN UI
# -----------------------------

def ui_visita_visiva_v2(conn):

    ensure_visit_state()
    apply_pending_visit_load()

    st.title("Vision Manager")

    # -------------------------
    # PAZIENTE
    # -------------------------

    cur = conn.cursor()

    cur.execute("""
        SELECT id, cognome, nome
        FROM pazienti
        ORDER BY cognome, nome
    """)

    pazienti = cur.fetchall()

    paz_dict = {
        f"{p[1]} {p[2]}": p[0]
        for p in pazienti
    }

    paziente_nome = st.selectbox(
        "Seleziona paziente",
        list(paz_dict.keys())
    )

    paziente_id = paz_dict[paziente_nome]

    # -------------------------
    # FORM
    # -------------------------

    st.subheader("Visita")

    st.date_input(
        "Data visita",
        key="vm_data_visita"
    )

    st.text_area(
        "Anamnesi",
        key="vm_anamnesi"
    )

    st.subheader("Acuità visiva")

    c1, c2 = st.columns(2)

    with c1:
        st.text_input("AVN OD", key="vm_acuita_naturale_od")

    with c2:
        st.text_input("AVN OS", key="vm_acuita_naturale_os")

    c3, c4 = st.columns(2)

    with c3:
        st.text_input("AVC OD", key="vm_acuita_corretta_od")

    with c4:
        st.text_input("AVC OS", key="vm_acuita_corretta_os")

    st.subheader("Esame obiettivo")

    st.text_input("Congiuntiva", key="vm_congiuntiva")
    st.text_input("Cornea", key="vm_cornea")
    st.text_input("Camera anteriore", key="vm_camera_anteriore")
    st.text_input("Cristallino", key="vm_cristallino")
    st.text_input("Vitreo", key="vm_vitreo")
    st.text_input("Fondo oculare", key="vm_fondo_oculare")

    st.text_input("IOP OD", key="vm_iop_od")
    st.text_input("IOP OS", key="vm_iop_os")

    st.text_input("Pachimetria OD", key="vm_pachimetria_od")
    st.text_input("Pachimetria OS", key="vm_pachimetria_os")

    st.text_area("Note", key="vm_note")

    # -------------------------
    # SALVA
    # -------------------------

    if st.button("Salva visita"):

        payload = build_visit_payload()

        cur.execute("""

        INSERT INTO visite_visive
        (paziente_id, data_visita, dati_json)

        VALUES (%s,%s,%s)

        RETURNING id

        """, (

            paziente_id,
            st.session_state["vm_data_visita"],
            json.dumps(payload)

        ))

        conn.commit()

        st.success("Visita salvata")


    # -------------------------
    # STORICO
    # -------------------------

    st.subheader("Storico visite")

    cur.execute("""

        SELECT id, data_visita, dati_json

        FROM visite_visive

        WHERE paziente_id=%s

        AND COALESCE(is_deleted,0)<>1

        ORDER BY data_visita DESC, id DESC

    """, (paziente_id,))

    rows = cur.fetchall()

    for r in rows:

        visit_id = r[0]
        data = r[1]
        dati_json = r[2]

        with st.expander(f"Visita {data}"):

            if st.button("Carica", key=f"load_{visit_id}"):

                st.session_state["vm_pending_load"] = {

                    "visit_id": visit_id,
                    "dati_json": dati_json

                }

                st.rerun()
