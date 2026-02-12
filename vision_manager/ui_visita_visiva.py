import json
import streamlit as st
from datetime import date

from vision_core.pdf_referto import genera_referto_visita_bytes
from utils import is_pg_conn, ph
from psycopg2.extras import Json as PgJson

from vision_manager.db import (
    list_visite_by_paziente,
    get_visita_corrente_pg,
    list_versioni_pg,
    load_version_pg,
    delete_visita,
)


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
    return [""] + [f"{x:+.2f}".replace("+0.00", "0.00") for x in vals]


SF_OPTS = _diopters(-30.0, 30.0, 0.25)
CIL_OPTS = _diopters(-15.0, 15.0, 0.25)
AX_OPTS = [""] + list(range(0, 181))


def _ref_eye(prefix: str):
    sf = st.selectbox(f"{prefix} SF", SF_OPTS, key=f"{prefix}_sf")
    cil = st.selectbox(f"{prefix} CIL", CIL_OPTS, key=f"{prefix}_cil")
    ax = st.selectbox(f"{prefix} AX", AX_OPTS, key=f"{prefix}_ax")
    return {"sf": sf, "cil": cil, "ax": ax}


def ui_visita_visiva(conn):
    # === UI ORIGINALE (creazione nuova visita) ===
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

    st.subheader("Distanza interpupillare (PD)")
    pd_mm = st.text_input("PD (mm) – es. 62", key="vv_pd")

    st.subheader("Acuità visiva (decimi) – ODX / OSN")
    av_opts = ["", "ONV", "NV", "1/10", "2/10", "3/10", "4/10", "5/10", "6/10", "7/10", "8/10", "9/10", "10/10", "11/10", "12/10"]
    c1, c2, c3 = st.columns(3)
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
    c1, c2 = st.columns(2)
    with c1:
        ro_odx = _ref_eye("RO ODX")
    with c2:
        ro_osn = _ref_eye("RO OSN")

    st.subheader("Refrazione soggettiva (SF / CIL x AX)")
    c1, c2 = st.columns(2)
    with c1:
        rs_odx = _ref_eye("RS ODX")
    with c2:
        rs_osn = _ref_eye("RS OSN")

    st.subheader("Cheratometria (campo libero)")
    c1, c2 = st.columns(2)
    with c1:
        k_odx = st.text_input("ODX (es. K1 ...; K2 ...)", key="k_odx")
    with c2:
        k_osn = st.text_input("OSN (es. K1 ...; K2 ...)", key="k_osn")

    st.subheader("Tonometria")
    c1, c2 = st.columns(2)
    with c1:
        ton_odx = st.text_input("ODX (mmHg)", key="ton_odx")
    with c2:
        ton_osn = st.text_input("OSN (mmHg)", key="ton_osn")

    st.subheader("Motilità / Allineamento")
    mot = st.text_area("PPC / cover test / note", key="mot")

    st.subheader("Colori / Pachimetria")
    col = st.text_input("Colori (note)", key="col")
    c1, c2 = st.columns(2)
    with c1:
        pach_odx = st.text_input("Pachimetria ODX (µm)", key="pach_odx")
    with c2:
        pach_osn = st.text_input("Pachimetria OSN (µm)", key="pach_osn")

    note = st.text_area("Note", key="note")

    if st.button("Genera referto PDF + salva nel DB", key="save_referto"):
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

        sql = f"INSERT INTO visite_visive (paziente_id, data_visita, dati_json, pdf_bytes) VALUES ({p},{p},{p},{p})"
        cur = conn.cursor()
        cur.execute(sql, (paz[0], data_visita_iso, json_val, blob))
        conn.commit()

        safe = f"{paz[1]}_{paz[2]}".replace(" ", "_")
        st.success("Visita salvata nel DB ✅")
        st.download_button("Scarica referto PDF", data=pdf_bytes, file_name=f"referto_visita_{safe}_{data_visita_iso}.pdf")

    # === NUOVA SEZIONE: VISITE ESISTENTI (senza alterare flusso originale) ===
    st.divider()
    st.subheader("Visite esistenti (Versioni / Elimina)")

    try:
        rows = list_visite_by_paziente(conn, paz[0], include_deleted=False)
    except Exception:
        rows = []

    if not rows:
        st.info("Nessuna visita salvata per questo paziente.")
        return

    def _fmt_row(r):
        vid = r[0]
        d = r[1] or ""
        cv = r[2] if r[2] is not None else 1
        return f"ID {vid} — {d} — v{cv}"

    sel = st.selectbox("Seleziona visita", rows, format_func=_fmt_row, key="vv_sel_visita")
    visita_id = sel[0]

    colA, colB, colC = st.columns([1, 1, 2])

    with colA:
        if st.button("📄 PDF corrente", key="vv_open_current"):
            if is_pg_conn(conn):
                try:
                    rec = get_visita_corrente_pg(conn, visita_id)
                    # rec: (..., vv.pdf_bytes is index 6)
                    if rec and rec[6]:
                        st.download_button(
                            "Scarica PDF (corrente)",
                            data=rec[6],
                            file_name=f"referto_visita_{visita_id}_corrente.pdf",
                            key=f"dl_curr_{visita_id}",
                        )
                    else:
                        st.warning("PDF non disponibile per questa visita.")
                except Exception as e:
                    st.error(f"Errore apertura visita: {e}")
            else:
                st.info("Storico versioni disponibile solo su PostgreSQL (Neon).")

    with colB:
        if st.button("🗑 Elimina", key="vv_del"):
            try:
                delete_visita(conn, visita_id)
                st.success("Visita eliminata (soft delete) ✅")
                st.rerun()
            except Exception as e:
                st.error(f"Errore eliminazione: {e}")

    with colC:
        with st.expander("🕘 Versioni", expanded=False):
            if not is_pg_conn(conn):
                st.info("Versioni disponibili solo su PostgreSQL (Neon).")
            else:
                try:
                    vers = list_versioni_pg(conn, visita_id)
                except Exception as e:
                    st.error(f"Errore caricamento versioni: {e}")
                    vers = []

                if not vers:
                    st.info("Nessuna versione trovata.")
                else:
                    options = [(v[0], v[1], v[2], v[3]) for v in vers]
                    def _fmt_v(x):
                        vno, created_at, created_by, note_mod = x
                        return f"V{vno} — {created_at} — {created_by} — {note_mod or ''}"

                    vsel = st.selectbox("Seleziona versione", options, format_func=_fmt_v, key=f"vv_sel_ver_{visita_id}")
                    vno = int(vsel[0])
                    if st.button(f"Scarica PDF V{vno}", key=f"vv_dl_ver_{visita_id}_{vno}"):
                        try:
                            rec = load_version_pg(conn, visita_id, vno)
                            # rec: (..., vv.pdf_bytes is index 5)
                            if rec and rec[5]:
                                st.download_button(
                                    f"Download PDF V{vno}",
                                    data=rec[5],
                                    file_name=f"referto_visita_{visita_id}_V{vno}.pdf",
                                    key=f"dl_ver_{visita_id}_{vno}",
                                )
                            else:
                                st.warning("PDF non disponibile per questa versione.")
                        except Exception as e:
                            st.error(f"Errore apertura versione: {e}")
