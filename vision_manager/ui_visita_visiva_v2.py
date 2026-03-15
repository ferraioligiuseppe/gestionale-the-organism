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
    except Exception:
        return {}


# ------------------------------
# DB
# ------------------------------

def apply_pending_visit_load():
    pending = st.session_state.pop("vm_pending_load", None)

    if not pending:
        return

    payload = pending.get("payload", {})
    visit_id = pending.get("visit_id")
    data_visita = pending.get("data_visita")

    load_visit_payload(
        payload=payload,
        visit_id=visit_id,
        data_visita=data_visita,
    )
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
                    "nome": r["nome"],
                })
            except Exception:
                pazienti.append({
                    "id": r[0],
                    "cognome": r[1],
                    "nome": r[2],
                })
        return pazienti

    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise

    finally:
        try:
            cur.close()
        except Exception:
            pass


def list_visite(conn, paziente_id):
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, data_visita, dati_json
            FROM visite_visive
            WHERE paziente_id = %s
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
                    "dati_json": r["dati_json"],
                })
            except Exception:
                visite.append({
                    "id": r[0],
                    "data_visita": r[1],
                    "dati_json": r[2],
                })
        return visite

    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise

    finally:
        try:
            cur.close()
        except Exception:
            pass


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

def _normalize_date_for_widget(dv):
    if isinstance(dv, dt.datetime):
        return dv.date()
    if isinstance(dv, dt.date):
        return dv
    if isinstance(dv, str):
        try:
            return dt.date.fromisoformat(dv[:10])
        except Exception:
            return dt.date.today()
    return dt.date.today()


def load_visit_payload(payload, visit_id=None, data_visita=None):
    reset_form()

    st.session_state["data_visita"] = _normalize_date_for_widget(data_visita)
    st.session_state["anamnesi"] = payload.get("anamnesi", "")

    av = payload.get("acuita", {})
    naturale = av.get("naturale", {}) if isinstance(av, dict) else {}
    corretta = av.get("corretta", {}) if isinstance(av, dict) else {}

    st.session_state["avn_od"] = naturale.get("od", "")
    st.session_state["avn_os"] = naturale.get("os", "")
    st.session_state["avc_od"] = corretta.get("od", "")
    st.session_state["avc_os"] = corretta.get("os", "")

    eo = payload.get("esame_obiettivo", {})
    if not isinstance(eo, dict):
        eo = {}

    st.session_state["iop_od"] = eo.get("pressione_endoculare_od", "")
    st.session_state["iop_os"] = eo.get("pressione_endoculare_os", "")
    st.session_state["pach_od"] = eo.get("pachimetria_od", "")
    st.session_state["pach_os"] = eo.get("pachimetria_os", "")

    ca = payload.get("correzione_abituale", {})
    if not isinstance(ca, dict):
        ca = {}

    st.session_state["sf_ab_od"] = ca.get("od", {}).get("sf", 0.0) if isinstance(ca.get("od", {}), dict) else 0.0
    st.session_state["cil_ab_od"] = ca.get("od", {}).get("cyl", 0.0) if isinstance(ca.get("od", {}), dict) else 0.0
    st.session_state["ax_ab_od"] = ca.get("od", {}).get("ax", 0) if isinstance(ca.get("od", {}), dict) else 0

    st.session_state["sf_ab_os"] = ca.get("os", {}).get("sf", 0.0) if isinstance(ca.get("os", {}), dict) else 0.0
    st.session_state["cil_ab_os"] = ca.get("os", {}).get("cyl", 0.0) if isinstance(ca.get("os", {}), dict) else 0.0
    st.session_state["ax_ab_os"] = ca.get("os", {}).get("ax", 0) if isinstance(ca.get("os", {}), dict) else 0

    cf = payload.get("correzione_finale", {})
    if not isinstance(cf, dict):
        cf = {}

    st.session_state["sf_fin_od"] = cf.get("od", {}).get("sf", 0.0) if isinstance(cf.get("od", {}), dict) else 0.0
    st.session_state["cil_fin_od"] = cf.get("od", {}).get("cyl", 0.0) if isinstance(cf.get("od", {}), dict) else 0.0
    st.session_state["ax_fin_od"] = cf.get("od", {}).get("ax", 0) if isinstance(cf.get("od", {}), dict) else 0

    st.session_state["sf_fin_os"] = cf.get("os", {}).get("sf", 0.0) if isinstance(cf.get("os", {}), dict) else 0.0
    st.session_state["cil_fin_os"] = cf.get("os", {}).get("cyl", 0.0) if isinstance(cf.get("os", {}), dict) else 0.0
    st.session_state["ax_fin_os"] = cf.get("os", {}).get("ax", 0) if isinstance(cf.get("os", {}), dict) else 0

    st.session_state["congiuntiva"] = eo.get("congiuntiva", "")
    st.session_state["cornea"] = eo.get("cornea", "")
    st.session_state["camera_anteriore"] = eo.get("camera_anteriore", "")
    st.session_state["cristallino"] = eo.get("cristallino", "")
    st.session_state["vitreo"] = eo.get("vitreo", "")
    st.session_state["fondo_oculare"] = eo.get("fondo_oculare", "")

    st.session_state["note"] = payload.get("note", "")
    st.session_state["vm_visit_id"] = visit_id
    st.session_state["vm_mode"] = "edit"


def load_last_visit(conn, paziente_id):
    visite = list_visite(conn, paziente_id)

    if not visite:
        st.warning("Nessuna visita trovata")
        return

    last = visite[0]
    payload = parse_json(last["dati_json"])

    load_visit_payload(
        payload=payload,
        visit_id=last["id"],
        data_visita=last["data_visita"],
    )

    st.success(f"Caricata visita {last['id']}")


def load_selected_visit(conn, paziente_id, visita_id):
    visite = list_visite(conn, paziente_id)

    target = None
    for v in visite:
        try:
            if int(v["id"]) == int(visita_id):
                target = v
                break
        except Exception:
            pass

    if not target:
        st.error("Visita non trovata")
        return

    payload = parse_json(target["dati_json"])

    load_visit_payload(
        payload=payload,
        visit_id=target["id"],
        data_visita=target["data_visita"],
    )

    st.success(f"Caricata visita selezionata {target['id']}")


# ------------------------------
# SAVE
# ------------------------------

def save_visit(conn, paziente_id):
    payload = {
        "tipo_visita": "oculistica",
        "data": str(st.session_state.get("data_visita")),
        "anamnesi": st.session_state.get("anamnesi", ""),
        "acuita": {
            "naturale": {
                "od": st.session_state.get("avn_od", ""),
                "os": st.session_state.get("avn_os", ""),
            },
            "corretta": {
                "od": st.session_state.get("avc_od", ""),
                "os": st.session_state.get("avc_os", ""),
            },
        },
        "esame_obiettivo": {
            "congiuntiva": st.session_state.get("congiuntiva", ""),
            "cornea": st.session_state.get("cornea", ""),
            "camera_anteriore": st.session_state.get("camera_anteriore", ""),
            "cristallino": st.session_state.get("cristallino", ""),
            "vitreo": st.session_state.get("vitreo", ""),
            "fondo_oculare": st.session_state.get("fondo_oculare", ""),
            "pressione_endoculare_od": st.session_state.get("iop_od", ""),
            "pressione_endoculare_os": st.session_state.get("iop_os", ""),
            "pachimetria_od": st.session_state.get("pach_od", ""),
            "pachimetria_os": st.session_state.get("pach_os", ""),
        },
        "correzione_abituale": {
            "od": {
                "sf": st.session_state.get("sf_ab_od", 0.0),
                "cyl": st.session_state.get("cil_ab_od", 0.0),
                "ax": st.session_state.get("ax_ab_od", 0),
            },
            "os": {
                "sf": st.session_state.get("sf_ab_os", 0.0),
                "cyl": st.session_state.get("cil_ab_os", 0.0),
                "ax": st.session_state.get("ax_ab_os", 0),
            },
        },
        "correzione_finale": {
            "od": {
                "sf": st.session_state.get("sf_fin_od", 0.0),
                "cyl": st.session_state.get("cil_fin_od", 0.0),
                "ax": st.session_state.get("ax_fin_od", 0),
            },
            "os": {
                "sf": st.session_state.get("sf_fin_os", 0.0),
                "cyl": st.session_state.get("cil_fin_os", 0.0),
                "ax": st.session_state.get("ax_fin_os", 0),
            },
        },
        "note": st.session_state.get("note", ""),
    }

    payload_json = json.dumps(payload, ensure_ascii=False)

    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO visite_visive (paziente_id, data_visita, dati_json)
            VALUES (%s, %s, %s)
            RETURNING id
        """, (
            paziente_id,
            payload["data"],
            payload_json,
        ))

        row = cur.fetchone()
        try:
            vid = row["id"]
        except Exception:
            vid = row[0]

        conn.commit()

        st.session_state["vm_visit_id"] = vid
        st.session_state["vm_mode"] = "edit"

        st.success(f"Visita salvata ID {vid}")

    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        st.error("Errore durante il salvataggio della visita.")
        st.exception(e)

    finally:
        try:
            cur.close()
        except Exception:
            pass


# ------------------------------
# UI
# ------------------------------

def ui_visita_visiva():
    st.title("Vision Manager")
    st.caption("Visita oculistica V2")

    conn = get_conn()
    try:
        conn.rollback()
    except Exception:
        pass

    pazienti = list_pazienti(conn)

    if not pazienti:
        st.warning("Nessun paziente nel database")
        return

    psel = st.selectbox(
        "Paziente",
        pazienti,
        format_func=lambda p: f"{p['cognome']} {p['nome']} (ID {p['id']})"
    )

    if not psel:
        st.warning("Seleziona un paziente")
        st.stop()

    paziente_id = int(psel["id"])

    prev_pid = st.session_state.get("vm_prev_pid")
    if prev_pid != paziente_id:
        reset_form()
        st.session_state["vm_prev_pid"] = paziente_id
        st.session_state["vm_mode"] = "new"
        st.session_state["vm_visit_id"] = None

    col1, col2 = st.columns(2)

    with col1:
        if st.button("➕ Nuova visita"):
            start_new_visit()

    with col2:
        if st.button("📂 Carica ultima visita"):
            load_last_visit(conn, paziente_id)

    st.divider()

    st.session_state.setdefault("data_visita", dt.date.today())
    st.date_input("Data visita", key="data_visita")

    st.session_state.setdefault("anamnesi", "")
    st.text_area("Anamnesi", height=140, key="anamnesi")

    st.subheader("Acuità visiva")
    c1, c2 = st.columns(2)
    with c1:
        st.session_state.setdefault("avn_od", "")
        st.session_state.setdefault("avc_od", "")
        st.text_input("AVN OD", key="avn_od")
        st.text_input("AVC OD", key="avc_od")
    with c2:
        st.session_state.setdefault("avn_os", "")
        st.session_state.setdefault("avc_os", "")
        st.text_input("AVN OS", key="avn_os")
        st.text_input("AVC OS", key="avc_os")

    st.subheader("Esame obiettivo")
    c1, c2 = st.columns(2)
    with c1:
        st.session_state.setdefault("congiuntiva", "")
        st.session_state.setdefault("cornea", "")
        st.session_state.setdefault("camera_anteriore", "")
        st.text_input("Congiuntiva", key="congiuntiva")
        st.text_input("Cornea", key="cornea")
        st.text_input("Camera anteriore", key="camera_anteriore")
    with c2:
        st.session_state.setdefault("cristallino", "")
        st.session_state.setdefault("vitreo", "")
        st.session_state.setdefault("fondo_oculare", "")
        st.text_input("Cristallino", key="cristallino")
        st.text_input("Vitreo", key="vitreo")
        st.text_input("Fondo oculare", key="fondo_oculare")

    st.subheader("IOP e Pachimetria")
    c1, c2 = st.columns(2)
    with c1:
        st.session_state.setdefault("iop_od", "")
        st.session_state.setdefault("pach_od", "")
        st.text_input("IOP OD", key="iop_od")
        st.text_input("Pachimetria OD", key="pach_od")
    with c2:
        st.session_state.setdefault("iop_os", "")
        st.session_state.setdefault("pach_os", "")
        st.text_input("IOP OS", key="iop_os")
        st.text_input("Pachimetria OS", key="pach_os")

    st.subheader("Correzione abituale")
    c1, c2 = st.columns(2)
    with c1:
        st.session_state.setdefault("sf_ab_od", 0.0)
        st.session_state.setdefault("cil_ab_od", 0.0)
        st.session_state.setdefault("ax_ab_od", 0)
        st.number_input("SF abituale OD", key="sf_ab_od", step=0.25, format="%0.2f")
        st.number_input("CIL abituale OD", key="cil_ab_od", step=0.25, format="%0.2f")
        st.number_input("AX abituale OD", key="ax_ab_od", min_value=0, max_value=180, step=1)
    with c2:
        st.session_state.setdefault("sf_ab_os", 0.0)
        st.session_state.setdefault("cil_ab_os", 0.0)
        st.session_state.setdefault("ax_ab_os", 0)
        st.number_input("SF abituale OS", key="sf_ab_os", step=0.25, format="%0.2f")
        st.number_input("CIL abituale OS", key="cil_ab_os", step=0.25, format="%0.2f")
        st.number_input("AX abituale OS", key="ax_ab_os", min_value=0, max_value=180, step=1)

    st.subheader("Correzione finale")
    c1, c2 = st.columns(2)
    with c1:
        st.session_state.setdefault("sf_fin_od", 0.0)
        st.session_state.setdefault("cil_fin_od", 0.0)
        st.session_state.setdefault("ax_fin_od", 0)
        st.number_input("SF finale OD", key="sf_fin_od", step=0.25, format="%0.2f")
        st.number_input("CIL finale OD", key="cil_fin_od", step=0.25, format="%0.2f")
        st.number_input("AX finale OD", key="ax_fin_od", min_value=0, max_value=180, step=1)
    with c2:
        st.session_state.setdefault("sf_fin_os", 0.0)
        st.session_state.setdefault("cil_fin_os", 0.0)
        st.session_state.setdefault("ax_fin_os", 0)
        st.number_input("SF finale OS", key="sf_fin_os", step=0.25, format="%0.2f")
        st.number_input("CIL finale OS", key="cil_fin_os", step=0.25, format="%0.2f")
        st.number_input("AX finale OS", key="ax_fin_os", min_value=0, max_value=180, step=1)

    st.subheader("Note")
    st.session_state.setdefault("note", "")
    st.text_area("Note visita", key="note", height=100)

    st.divider()

    if st.button("💾 Salva visita"):
        save_visit(conn, paziente_id)

    st.caption(
        f"MODE: {st.session_state.get('vm_mode', 'new')} | "
        f"VISIT_ID: {st.session_state.get('vm_visit_id')}"
    )

    st.divider()
    st.subheader("📚 Storico visite")

    visite = list_visite(conn, paziente_id)

    if not visite:
        st.info("Nessuna visita disponibile per questo paziente.")
    else:
        for visita in visite:
            vid = visita["id"]
            data_v = visita["data_visita"]
            data_label = _normalize_date_for_widget(data_v).strftime("%d/%m/%Y")

            with st.expander(f"Visita ID {vid} — {data_label}"):
                payload = parse_json(visita["dati_json"])

                st.write(f"**Data visita:** {data_label}")
                st.write(f"**Anamnesi:** {payload.get('anamnesi', '')}")

                col_a, col_b = st.columns([1, 3])

                with col_a:
                    if st.button(f"📥 Carica {vid}", key=f"load_visit_{vid}"):
                        load_selected_visit(conn, paziente_id, vid)

                with col_b:
                    st.caption(f"Modalità corrente: {st.session_state.get('vm_mode', 'new')}")
