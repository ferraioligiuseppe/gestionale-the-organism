import streamlit as st
import datetime as dt
import json
from vision_manager.db import get_conn


# ------------------------------
# JSON
# ------------------------------

def parse_json(s):
    try:
        return json.loads(s) if s else {}
    except:
        return {}


# ------------------------------
# DB
# ------------------------------

def list_pazienti(conn):

    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT id, cognome, nome
            FROM pazienti
            ORDER BY cognome, nome
        """)

        rows = cur.fetchall()

        pazienti = []

        for r in rows:
            try:
                pazienti.append({
                    "id": r["id"],
                    "cognome": r["cognome"],
                    "nome": r["nome"]
                })
            except Exception:
                pazienti.append({
                    "id": r[0],
                    "cognome": r[1],
                    "nome": r[2]
                })

        return pazienti

    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise

def list_visite(conn, paziente_id):

    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT id, data_visita, dati_json
            FROM visite_visive
            WHERE paziente_id=%s
            AND COALESCE(is_deleted, 0) <> 1
            ORDER BY data_visita DESC, id DESC
        """, (paziente_id,))

        rows = cur.fetchall()

        visite = []

        for r in rows:
            try:
                visite.append({
                    "id": r["id"],
                    "data_visita": r["data_visita"],
                    "dati_json": r["dati_json"]
                })
            except Exception:
                visite.append({
                    "id": r[0],
                    "data_visita": r[1],
                    "dati_json": r[2]
                })

        return visite

    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise

# ------------------------------
# FORM
# ------------------------------

def reset_form():

    keys = list(st.session_state.keys())

    for k in keys:

        if k.startswith("vm_"):
            continue

        if k in ["data_visita"]:
            continue

        del st.session_state[k]


def start_new_visit():

    reset_form()

    st.session_state["data_visita"] = dt.date.today()
    st.session_state["vm_mode"] = "new"
    st.session_state["vm_visit_id"] = None


# ------------------------------
# LOAD VISIT
# ------------------------------

def load_last_visit(conn, paziente_id):

    visite = list_visite(conn, paziente_id)

    if not visite:
        st.warning("Nessuna visita trovata")
        return

    last = visite[0]

    payload = parse_json(last["dati_json"])

    reset_form()

    st.session_state["data_visita"] = last["data_visita"]

    st.session_state["anamnesi"] = payload.get("anamnesi","")

    av = payload.get("acuita",{})

    st.session_state["avn_od"] = av.get("naturale",{}).get("od","")
    st.session_state["avn_os"] = av.get("naturale",{}).get("os","")

    st.session_state["avc_od"] = av.get("corretta",{}).get("od","")
    st.session_state["avc_os"] = av.get("corretta",{}).get("os","")

    eo = payload.get("esame_obiettivo",{})

    st.session_state["iop_od"] = eo.get("pressione_endoculare_od","")
    st.session_state["iop_os"] = eo.get("pressione_endoculare_os","")

    st.session_state["pach_od"] = eo.get("pachimetria_od","")
    st.session_state["pach_os"] = eo.get("pachimetria_os","")

    corr = payload.get("correzione_finale",{})

    st.session_state["sf_od"] = corr.get("od",{}).get("sf","")
    st.session_state["cil_od"] = corr.get("od",{}).get("cyl","")
    st.session_state["ax_od"] = corr.get("od",{}).get("ax","")

    st.session_state["sf_os"] = corr.get("os",{}).get("sf","")
    st.session_state["cil_os"] = corr.get("os",{}).get("cyl","")
    st.session_state["ax_os"] = corr.get("os",{}).get("ax","")

    st.session_state["note"] = payload.get("note","")

    st.session_state["vm_visit_id"] = last["id"]
    st.session_state["vm_mode"] = "edit"

    st.success(f"Caricata visita {last['id']}")


# ------------------------------
# SAVE
# ------------------------------

def save_visit(conn, paziente_id):

    payload = {

        "data": str(st.session_state.get("data_visita")),

        "anamnesi": st.session_state.get("anamnesi",""),

        "acuita": {
            "naturale":{
                "od": st.session_state.get("avn_od",""),
                "os": st.session_state.get("avn_os","")
            },
            "corretta":{
                "od": st.session_state.get("avc_od",""),
                "os": st.session_state.get("avc_os","")
            }
        },

        "esame_obiettivo":{
            "pressione_endoculare_od": st.session_state.get("iop_od",""),
            "pressione_endoculare_os": st.session_state.get("iop_os",""),
            "pachimetria_od": st.session_state.get("pach_od",""),
            "pachimetria_os": st.session_state.get("pach_os","")
        },

        "correzione_finale":{
            "od":{
                "sf": st.session_state.get("sf_od",""),
                "cyl": st.session_state.get("cil_od",""),
                "ax": st.session_state.get("ax_od","")
            },
            "os":{
                "sf": st.session_state.get("sf_os",""),
                "cyl": st.session_state.get("cil_os",""),
                "ax": st.session_state.get("ax_os","")
            }
        },

        "note": st.session_state.get("note","")
    }

    payload_json = json.dumps(payload,ensure_ascii=False)

    cur = conn.cursor()

    cur.execute("""
        INSERT INTO visite_visive (paziente_id,data_visita,dati_json)
        VALUES (%s,%s,%s)
        RETURNING id
    """,(paziente_id,payload["data"],payload_json))

    vid = cur.fetchone()[0]

    conn.commit()

    st.session_state["vm_visit_id"] = vid
    st.session_state["vm_mode"] = "edit"

    st.success(f"Visita salvata ID {vid}")


# ------------------------------
# UI
# ------------------------------

def ui_visita_visiva():

    st.title("Vision Manager")

    conn = get_conn()

    pazienti = list_pazienti(conn)

    psel = st.selectbox(
        "Paziente",
        pazienti,
        format_func=lambda p: f"{p['cognome']} {p['nome']} (ID {p['id']})"
    )

    paziente_id = int(psel["id"])

    prev_pid = st.session_state.get("vm_prev_pid")

    if prev_pid != paziente_id:
        reset_form()
        st.session_state["vm_prev_pid"] = paziente_id

    col1,col2 = st.columns(2)

    with col1:
        if st.button("➕ Nuova visita"):
            start_new_visit()

    with col2:
        if st.button("📂 Carica ultima visita"):
            load_last_visit(conn,paziente_id)

    st.divider()

    st.date_input("Data visita",key="data_visita")

    st.text_area("Anamnesi",height=150,key="anamnesi")

    st.subheader("Acuità visiva")

    c1,c2 = st.columns(2)

    with c1:
        st.text_input("AVN OD",key="avn_od")
        st.text_input("AVC OD",key="avc_od")

    with c2:
        st.text_input("AVN OS",key="avn_os")
        st.text_input("AVC OS",key="avc_os")

    st.subheader("Pressione")

    c1,c2 = st.columns(2)

    with c1:
        st.text_input("IOP OD",key="iop_od")
        st.text_input("Pachimetria OD",key="pach_od")

    with c2:
        st.text_input("IOP OS",key="iop_os")
        st.text_input("Pachimetria OS",key="pach_os")

    st.subheader("Correzione finale")

    c1,c2 = st.columns(2)

    with c1:
        st.number_input("SF OD",key="sf_od")
        st.number_input("CIL OD",key="cil_od")
        st.number_input("AX OD",key="ax_od")

    with c2:
        st.number_input("SF OS",key="sf_os")
        st.number_input("CIL OS",key="cil_os")
        st.number_input("AX OS",key="ax_os")

    st.text_area("Note",key="note")

    st.divider()

    if st.button("💾 Salva visita"):
        save_visit(conn,paziente_id)
