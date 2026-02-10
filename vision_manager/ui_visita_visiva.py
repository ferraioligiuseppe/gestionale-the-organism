import json
import streamlit as st
from datetime import datetime
from vision_core.pdf_referto import genera_referto_visita_bytes
from utils import is_pg_conn, ph
from psycopg2.extras import Json as PgJson  # used only in Postgres path

def _diopters(min_d: float, max_d: float, step: float = 0.25):
    # returns list of strings: +0.25, 0.00, -0.25 ... within range (inclusive)
    vals = []
    v = max_d
    # go downward so 0.00 stays near top if max_d>0; we will later reorder
    while v >= min_d - 1e-9:
        vals.append(round(v, 2))
        v -= step
    # sort descending (e.g., +30 -> -30)
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

    paz = st.selectbox("Paziente", pazienti, format_func=lambda x: f"{x[1]} {x[2]}")
    data_nascita = paz[3] or ""
    data_visita = st.text_input("Data visita (YYYY-MM-DD)", value=datetime.now().strftime("%Y-%m-%d"))

    st.subheader("Acuità visiva (come nel tuo modello)")
    c1,c2,c3 = st.columns(3)
    with c1:
        nat_odx = st.text_input("NAT ODX")
        nat_osn = st.text_input("NAT OSN")
        nat_oo = st.text_input("NAT OO")
    with c2:
        corr_odx = st.text_input("CORR ODX")
        corr_osn = st.text_input("CORR OSN")
        corr_oo = st.text_input("CORR OO")
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
    with c1: k_odx = st.text_input("ODX (es. K1 ...; K2 ...)")
    with c2: k_osn = st.text_input("OSN (es. K1 ...; K2 ...)")

    st.subheader("Tonometria")
    c1,c2 = st.columns(2)
    with c1: ton_odx = st.text_input("ODX (mmHg)")
    with c2: ton_osn = st.text_input("OSN (mmHg)")

    st.subheader("Motilità / Allineamento")
    mot = st.text_area("PPC / cover test / note")

    st.subheader("Colori / Pachimetria")
    col = st.text_input("Colori (note)")
    c1,c2 = st.columns(2)
    with c1: pach_odx = st.text_input("Pachimetria ODX (µm)")
    with c2: pach_osn = st.text_input("Pachimetria OSN (µm)")

    st.subheader("Tipo occhiale (checkbox + note)")
    c1, c2 = st.columns([2,3])
    with c1:
        tipi = {
            "Monofocale": st.checkbox("Monofocale"),
            "Progressivo": st.checkbox("Progressivo"),
            "Bifocale": st.checkbox("Bifocale"),
            "Office/Intermedio": st.checkbox("Office/Intermedio"),
            "Da sole": st.checkbox("Da sole"),
            "Altro": st.checkbox("Altro"),
        }
    with c2:
        tipo_note = st.text_area("Note lente (campo libero)")

    note = st.text_area("Note")

    if st.button("Genera referto PDF + salva nel DB"):
        tipi_sel = [k for k,v in tipi.items() if v]
        dati = {
            "paziente_id": paz[0],
            "paziente_label": f"{paz[1]} {paz[2]}",
            "data_nascita": data_nascita,
            "data_visita": data_visita,
            "av": {
                "nat_odx": nat_odx, "nat_osn": nat_osn, "nat_oo": nat_oo,
                "corr_odx": corr_odx, "corr_osn": corr_osn, "corr_oo": corr_oo,
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
        cur.execute(sql, (paz[0], data_visita, json_val, blob))
        conn.commit()

        safe = f"{paz[1]}_{paz[2]}".replace(" ", "_")
        st.success("Visita salvata nel DB ✅")
        st.download_button("Scarica referto PDF", data=pdf_bytes, file_name=f"referto_visita_{safe}_{data_visita}.pdf")