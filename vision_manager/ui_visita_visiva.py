import json
import streamlit as st
from datetime import date
from vision_core.pdf_referto import genera_referto_visita_bytes
from utils import is_pg_conn, ph
from psycopg2.extras import Json as PgJson  # used only in Postgres path

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

def _ref_eye(prefix: str):
    sf = st.selectbox(f"{prefix} SF", SF_OPTS, key=f"{prefix}_sf")
    cil = st.selectbox(f"{prefix} CIL", CIL_OPTS, key=f"{prefix}_cil")
    ax = st.selectbox(f"{prefix} AX", AX_OPTS, key=f"{prefix}_ax")
    return {"sf": sf, "cil": cil, "ax": ax}

def ui_visita_visiva(conn):
    st.header("Visita visiva – Referto clinico A4 (stile pulito)")

    cur = conn.cursor()
    cur.execute("SELECT id, cognome, nome, data_nascita FROM pazienti_visivi ORDER BY cognome, nome")
    pazienti = cur.fetchall()
    if not pazienti:
        st.warning("Prima crea almeno un paziente.")
        return

    paz = st.selectbox("Paziente", pazienti, format_func=lambda x: f"{x[1]} {x[2]}", key="vv_paz")
    data_nascita_iso = paz[3] or ""

    dv = st.date_input("Data visita", value=date.today(), key="vv_dv")
    data_visita_iso = _date_to_iso(dv)
    data_visita_eu = _date_to_eu(dv)

    st.subheader("Acuità visiva (decimi) – selezione rapida")
    av_opts = ["", "ONV", "NV","1/10","2/10","3/10","4/10","5/10","6/10","7/10","8/10","9/10","10/10","11/10","12/10"]
    c1,c2,c3 = st.columns(3)
    with c1:
        av_lont_odx = st.selectbox("Lontano ODX", av_opts, index=0, key="av_l_odx")
        av_lont_osn = st.selectbox("Lontano OSN", av_opts, index=0, key="av_l_osn")
    with c2:
        av_vic_odx = st.selectbox("Vicino ODX", av_opts, index=0, key="av_v_odx")
        av_vic_osn = st.selectbox("Vicino OSN", av_opts, index=0, key="av_v_osn")
    with c3:
        av_int_odx = st.selectbox("Intermedio ODX", av_opts, index=0, key="av_i_odx")
        av_int_osn = st.selectbox("Intermedio OSN", av_opts, index=0, key="av_i_osn")

    st.subheader("Acuità visiva (come nel tuo modello – campi liberi)")
    c1,c2,c3 = st.columns(3)
    with c1:
        nat_odx = st.text_input("NAT ODX", key="nat_odx")
        nat_osn = st.text_input("NAT OSN", key="nat_osn")
        nat_oo = st.text_input("NAT OO", key="nat_oo")
    with c2:
        corr_odx = st.text_input("CORR ODX", key="corr_odx")
        corr_osn = st.text_input("CORR OSN", key="corr_osn")
        corr_oo = st.text_input("CORR OO", key="corr_oo")
    with c3:
        st.caption("Formato libero (es. 10/10, 8/10, 0.8, ecc.)")

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
    mot = st.text_area("PPC / cover test / note", key="mot_all")

    st.subheader("Colori / Pachimetria")
    col = st.text_input("Colori (note)", key="col")
    c1,c2 = st.columns(2)
    with c1: pach_odx = st.text_input("Pachimetria ODX (µm)", key="pach_odx")
    with c2: pach_osn = st.text_input("Pachimetria OSN (µm)", key="pach_osn")

    st.subheader("Tipo occhiale (checkbox + note)")
    c1, c2 = st.columns([2,3])
    with c1:
        tipi = {
            "Monofocale": st.checkbox("Monofocale", key="t_mono_vv"),
            "Progressivo": st.checkbox("Progressivo", key="t_prog_vv"),
            "Bifocale": st.checkbox("Bifocale", key="t_bi_vv"),
            "Office/Intermedio": st.checkbox("Office/Intermedio", key="t_off_vv"),
            "Da sole": st.checkbox("Da sole", key="t_sole_vv"),
            "Altro": st.checkbox("Altro", key="t_altro_vv"),
        }
    with c2:
        tipo_note = st.text_area("Note lente (campo libero)", key="tipo_note_vv")

    note = st.text_area("Note", key="note_vv")

    if st.button("Genera referto PDF + salva nel DB", key="btn_referto_save"):
        tipi_sel = [k for k,v in tipi.items() if v]
        dati = {
            "paziente_id": paz[0],
            "paziente_label": f"{paz[1]} {paz[2]}",
            "data_nascita": data_nascita_iso,
            "data_visita": data_visita_eu,
            "data_visita_iso": data_visita_iso,
            "av": {
                "nat_odx": nat_odx, "nat_osn": nat_osn, "nat_oo": nat_oo,
                "corr_odx": corr_odx, "corr_osn": corr_osn, "corr_oo": corr_oo,
            },
            "av_decimi": {
                "lontano_odx": av_lont_odx, "lontano_osn": av_lont_osn,
                "vicino_odx": av_vic_odx, "vicino_osn": av_vic_osn,
                "intermedio_odx": av_int_odx, "intermedio_osn": av_int_osn,
            },
            "ref_oggettiva": {"odx": ro_odx, "osn": ro_osn},
            "ref_soggettiva": {"odx": rs_odx, "osn": rs_osn},
            "cheratometria": {"odx": k_odx, "osn": k_osn},
            "tonometria": {"odx": ton_odx, "osn": ton_osn},
            "motilita_allineamento": mot,
            "colori": col,
            "pachimetria": {"odx": pach_odx, "osn": pach_osn},
            "tipi_selezionati": tipi_sel,
            "tipo_note": tipo_note,
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
