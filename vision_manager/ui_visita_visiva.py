import json
import streamlit as st
from datetime import date
from vision_core.pdf_referto import genera_referto_visita_bytes
from db import list_visite_visive, get_visita_corrente, get_versioni_visita, get_visita_versione, soft_delete_visita
from utils import is_pg_conn, ph, json_to_dict, blob_to_bytes
from psycopg2.extras import Json as PgJson

def _date_to_iso(d):
    return d.isoformat() if d else ""

def _date_to_eu(d):
    return d.strftime("%d/%m/%Y") if d else ""

def _diopters(min_d: float, max_d: float, step: float = 0.25):
    vals = []
    v = max_d
    while v >= min_d - 1e-9:
        vals.append(round(v, 2))
        v -= step
    vals = sorted(vals, reverse=True)
    return [""] + [f"{x:+.2f}".replace("+0.00","0.00") for x in vals]

SF_OPTS = _diopters(-30.0, 30.0, 0.25)
CIL_OPTS = _diopters(-15.0, 15.0, 0.25)
AX_OPTS = [""] + list(range(0, 181))


# Session state for editing existing visits
if "vv_selected_visit_id" not in st.session_state:
    st.session_state.vv_selected_visit_id = None
if "vv_show_versioni" not in st.session_state:
    st.session_state.vv_show_versioni = False

def _parse_iso_date(s: str):
    try:
        if not s:
            return None
        return date.fromisoformat(str(s)[:10])
    except Exception:
        return None

def _apply_loaded_visit_to_session(d: dict):
    """Carica dati di una visita esistente nei widget keys usati dalla UI."""
    if not isinstance(d, dict):
        return
    # Data visita (preferisci data_visita_iso, fallback data_visita)
    dv_iso = d.get("data_visita_iso") or d.get("data_visita") or ""
    dv = _parse_iso_date(dv_iso)
    if dv:
        st.session_state["vv_dv"] = dv

    st.session_state["vv_pd"] = d.get("pd_mm", "") or ""

    av = d.get("av_decimi", {}) or {}
    st.session_state["av_l_odx"] = av.get("lontano_odx", "") or ""
    st.session_state["av_l_osn"] = av.get("lontano_osn", "") or ""
    st.session_state["av_i_odx"] = av.get("intermedio_odx", "") or ""
    st.session_state["av_i_osn"] = av.get("intermedio_osn", "") or ""
    st.session_state["av_v_odx"] = av.get("vicino_odx", "") or ""
    st.session_state["av_v_osn"] = av.get("vicino_osn", "") or ""

    ro = (d.get("ref_oggettiva", {}) or {})
    rs = (d.get("ref_soggettiva", {}) or {})

    def set_ref(prefix, obj):
        eye = obj or {}
        st.session_state[f"{prefix}_sf"] = (eye.get("sf", "") or "")
        st.session_state[f"{prefix}_cil"] = (eye.get("cil", "") or "")
        st.session_state[f"{prefix}_ax"] = (eye.get("ax", "") or "")

    set_ref("RO ODX", (ro.get("odx") or {}))
    set_ref("RO OSN", (ro.get("osn") or {}))
    set_ref("RS ODX", (rs.get("odx") or {}))
    set_ref("RS OSN", (rs.get("osn") or {}))

    ker = d.get("cheratometria", {}) or {}
    ton = d.get("tonometria", {}) or {}
    pach = d.get("pachimetria", {}) or {}

    st.session_state["k_odx"] = ker.get("odx", "") or ""
    st.session_state["k_osn"] = ker.get("osn", "") or ""
    st.session_state["ton_odx"] = ton.get("odx", "") or ""
    st.session_state["ton_osn"] = ton.get("osn", "") or ""
    st.session_state["mot"] = d.get("motilita_allineamento", "") or ""
    st.session_state["col"] = d.get("colori", "") or ""
    st.session_state["pach_odx"] = pach.get("odx", "") or ""
    st.session_state["pach_osn"] = pach.get("osn", "") or ""
    st.session_state["note"] = d.get("note", "") or ""

def _ref_eye(prefix: str):
    sf = st.selectbox(f"{prefix} SF", SF_OPTS, key=f"{prefix}_sf")
    cil = st.selectbox(f"{prefix} CIL", CIL_OPTS, key=f"{prefix}_cil")
    ax = st.selectbox(f"{prefix} AX", AX_OPTS, key=f"{prefix}_ax")
    return {"sf": sf, "cil": cil, "ax": ax}

def ui_visita_visiva(conn):
    st.header("Visita visiva – Referto A4")

    cur = conn.cursor()
    cur.execute("SELECT id, cognome, nome, data_nascita FROM pazienti_visivi ORDER BY cognome, nome")
    pazienti = cur.fetchall()
    if not pazienti:
        st.warning("Prima crea almeno un paziente.")
        return

    paz = st.selectbox("Paziente", pazienti, format_func=lambda x: f"{x[1]} {x[2]}", key="vv_paz")
    dn_iso = paz[3] or ""

    dv = st.date_input("Data visita", value=date.today(), key="vv_dv")
    data_visita_iso = _date_to_iso(dv)
    data_visita_eu = _date_to_eu(dv)


    # ----------------------------
    # Gestione visita esistente (Modifica / Elimina / Versioni)
    # ----------------------------
    st.markdown("---")
    st.subheader("Gestione visita esistente")

    # elenco visite per paziente (solo attive)
    try:
        visits_rows = list_visite_visive(conn, paz[0])
    except Exception:
        visits_rows = []

    visits_ids = [r[0] for r in visits_rows] if visits_rows else []
    if visits_ids:
        sel_id = st.selectbox("Seleziona visita da modificare", [""] + visits_ids, format_func=lambda x: "" if x=="" else f"Visita #{x}", key="vv_sel_visita")
        cA, cB, cC = st.columns([1,1,2])

        with cA:
            if st.button("📥 Carica", key="vv_load_btn") and sel_id != "":
                row = get_visita_corrente(conn, int(sel_id))
                if row:
                    # row: (visita_id, paziente_id, data_visita, current_version, dati_json, pdf_bytes, ...)
                    dati_loaded = json_to_dict(row[4])
                    st.session_state.vv_selected_visit_id = int(sel_id)
                    _apply_loaded_visit_to_session(dati_loaded)
                    st.success(f"Caricata visita #{sel_id} (puoi modificare i campi sotto).")
                    st.rerun()

        with cB:
            if st.button("🗑 Elimina", key="vv_del_btn") and sel_id != "":
                soft_delete_visita(conn, int(sel_id))
                st.session_state.vv_selected_visit_id = None
                st.success("Visita eliminata (soft delete).")
                st.rerun()

        with cC:
            if st.button("🕘 Versioni", key="vv_ver_btn") and sel_id != "":
                st.session_state.vv_show_versioni = True
                st.session_state.vv_selected_visit_id = int(sel_id)
                st.rerun()

    else:
        st.info("Nessuna visita salvata per questo paziente (ancora).")

    if st.session_state.get("vv_show_versioni") and st.session_state.get("vv_selected_visit_id"):
        vid = int(st.session_state.vv_selected_visit_id)
        st.markdown("#### 🕘 Storico versioni")
        vers = get_versioni_visita(conn, vid) or []
        if not vers:
            st.info("Nessuna versione trovata (tabella versioni non disponibile o vuota).")
        else:
            # scegli versione
            vnos = [v[0] for v in vers]
            pick = st.selectbox("Apri versione", vnos, format_func=lambda x: f"Versione {x}", key="vv_pick_version")
            rowv = get_visita_versione(conn, vid, int(pick))
            if rowv:
                pdfb = blob_to_bytes(rowv[5])
                st.caption(f"Versione {rowv[3]} • by {rowv[7]} • {rowv[6]}")
                if pdfb:
                    st.download_button("Scarica PDF di questa versione", data=pdfb, file_name=f"referto_visita_{vid}_v{pick}.pdf")
                else:
                    st.warning("PDF non presente per questa versione.")
            if st.button("Chiudi versioni", key="vv_close_versioni"):
                st.session_state.vv_show_versioni = False
                st.rerun()

        st.markdown("---")

        st.subheader("Distanza interpupillare (PD)")
        pd_mm = st.text_input("PD (mm) – es. 62", key="vv_pd")

        st.subheader("Acuità visiva (decimi) – ODX / OSN")
        av_opts = ["", "ONV", "NV","1/10","2/10","3/10","4/10","5/10","6/10","7/10","8/10","9/10","10/10","11/10","12/10"]
        c1,c2,c3 = st.columns(3)
        with c1:
            av_l_odx = st.selectbox("Lontano ODX", av_opts, 0, key="av_l_odx")
            av_l_osn = st.selectbox("Lontano OSN", av_opts, 0, key="av_l_osn")
        with c2:
            av_i_odx = st.selectbox("Intermedio ODX", av_opts, 0, key="av_i_odx")
            av_i_osn = st.selectbox("Intermedio OSN", av_opts, 0, key="av_i_osn")
        with c3:
            av_v_odx = st.selectbox("Vicino ODX", av_opts, 0, key="av_v_odx")
            av_v_osn = st.selectbox("Vicino OSN", av_opts, 0, key="av_v_osn")

        st.subheader("Refrazione oggettiva (SF / CIL x AX)")
        c1,c2 = st.columns(2)
        with c1: ro_odx = _ref_eye("RO ODX")
        with c2: ro_osn = _ref_eye("RO OSN")

        st.subheader("Refrazione soggettiva (SF / CIL x AX)")
        c1,c2 = st.columns(2)
        with c1: rs_odx = _ref_eye("RS ODX")
        with c2: rs_osn = _ref_eye("RS OSN")

        st.subheader("Cheratometria (campo libero)")
        c1,c2 = st.columns(2)
        with c1: k_odx = st.text_input("ODX (es. K1 ...; K2 ...)", key="k_odx")
        with c2: k_osn = st.text_input("OSN (es. K1 ...; K2 ...)", key="k_osn")

        st.subheader("Tonometria")
        c1,c2 = st.columns(2)
        with c1: ton_odx = st.text_input("ODX (mmHg)", key="ton_odx")
        with c2: ton_osn = st.text_input("OSN (mmHg)", key="ton_osn")

        st.subheader("Motilità / Allineamento")
        mot = st.text_area("PPC / cover test / note", key="mot")

        st.subheader("Colori / Pachimetria")
        col = st.text_input("Colori (note)", key="col")
        c1,c2 = st.columns(2)
        with c1: pach_odx = st.text_input("Pachimetria ODX (µm)", key="pach_odx")
        with c2: pach_osn = st.text_input("Pachimetria OSN (µm)", key="pach_osn")

        note = st.text_area("Note", key="note")


        col_save1, col_save2 = st.columns(2)
        with col_save1:
            do_new = st.button("➕ Genera referto PDF + salva NUOVA visita", key="save_referto_new")
        with col_save2:
            do_upd = st.button(
                "✏️ Genera referto PDF + salva MODIFICA (nuova versione)",
                key="save_referto_update",
                disabled=(st.session_state.get("vv_selected_visit_id") is None)
            )

        if do_new or do_upd:
            dati = {
                "paziente_id": paz[0],
                "paziente_label": f"{paz[1]} {paz[2]}",
                "data_nascita": dn_iso,
                "data_visita": data_visita_eu,
                "data_visita_iso": data_visita_iso,
                "pd_mm": pd_mm,
                "av_decimi": {
                    "lontano_odx": av_l_odx, "lontano_osn": av_l_osn,
                    "intermedio_odx": av_i_odx, "intermedio_osn": av_i_osn,
                    "vicino_odx": av_v_odx, "vicino_osn": av_v_osn,
                },
                "ref_oggettiva": {"odx": ro_odx, "osn": ro_osn},
                "ref_soggettiva": {"odx": rs_odx, "osn": rs_osn},
                "cheratometria": {"odx": k_odx, "osn": k_osn},
                "tonometria": {"odx": ton_odx, "osn": ton_osn},
                "motilita_allineamento": mot,
                "colori": col,
                "pachimetria": {"odx": pach_odx, "osn": pach_osn},
                "note": note,
            }
            pdf_bytes = genera_referto_visita_bytes(dati)


            is_pg = is_pg_conn(conn)
            p = ph(conn)
            if is_pg:
                import psycopg2
                json_val = PgJson(dati)
                blob = psycopg2.Binary(pdf_bytes)
            else:
                json_val = json.dumps(dati, ensure_ascii=False)
                blob = pdf_bytes

            cur = conn.cursor()
            if do_upd and st.session_state.get("vv_selected_visit_id"):
                vid = int(st.session_state.vv_selected_visit_id)
                sql = f"UPDATE visite_visive SET paziente_id={p}, data_visita={p}, dati_json={p}, pdf_bytes={p} WHERE id={p}"
                cur.execute(sql, (paz[0], data_visita_iso, json_val, blob, vid))
                conn.commit()
                st.success(f"Visita #{vid} aggiornata ✅ (creata nuova versione)")
            else:
                sql = f"INSERT INTO visite_visive (paziente_id, data_visita, dati_json, pdf_bytes) VALUES ({p},{p},{p},{p})"
                cur.execute(sql, (paz[0], data_visita_iso, json_val, blob))
                conn.commit()
                st.success("Visita salvata nel DB ✅")

            safe = f"{paz[1]}_{paz[2]}".replace(" ", "_")
            st.download_button(
                "Scarica referto PDF",
                data=pdf_bytes,
                file_name=f"referto_visita_{safe}_{data_visita_iso}.pdf"
            )
