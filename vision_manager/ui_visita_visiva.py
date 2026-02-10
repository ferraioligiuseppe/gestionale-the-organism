import json
import streamlit as st
from datetime import datetime
from vision_core.pdf_referto import genera_referto_visita_bytes
from utils import is_pg_conn, ph
from psycopg2.extras import Json as PgJson  # used only in Postgres path

def _av_options():
    return ["", "NV","1/10","2/10","3/10","4/10","5/10","6/10","7/10","8/10","9/10","10/10","11/10","12/10"]

def _axis_options():
    return list(range(0, 181))

def _ref_eye(prefix: str):
    sf = st.text_input(f"{prefix} SF", key=f"{prefix}_sf")
    cil = st.text_input(f"{prefix} CIL", key=f"{prefix}_cil")
    ax = st.selectbox(f"{prefix} AX", _axis_options(), key=f"{prefix}_ax")
    return {"sf": sf, "cil": cil, "ax": ax}

def ui_visita_visiva(conn):
    st.header("Visita visiva (Referto A4: stampa solo campi compilati)")

    cur = conn.cursor()
    cur.execute("SELECT id, cognome, nome FROM pazienti_visivi ORDER BY cognome, nome")
    pazienti = cur.fetchall()
    if not pazienti:
        st.warning("Prima crea almeno un paziente.")
        return

    paz = st.selectbox("Paziente", pazienti, format_func=lambda x: f"{x[1]} {x[2]}")
    data_visita = st.text_input("Data visita (YYYY-MM-DD)", value=datetime.now().strftime("%Y-%m-%d"))

    st.subheader("Acuità visiva (decimi)")
    av_opts = _av_options()
    c1,c2,c3 = st.columns(3)
    with c1:
        lont_odx = st.selectbox("Lontano ODX", av_opts, index=0)
        lont_osn = st.selectbox("Lontano OSN", av_opts, index=0)
    with c2:
        vic_odx = st.selectbox("Vicino ODX", av_opts, index=0)
        vic_osn = st.selectbox("Vicino OSN", av_opts, index=0)
    with c3:
        int_odx = st.selectbox("Intermedio ODX", av_opts, index=0)
        int_osn = st.selectbox("Intermedio OSN", av_opts, index=0)

    st.subheader("Esame obiettivo")
    eo1, eo2 = st.columns(2)
    with eo1:
        congiuntiva = st.text_input("Congiuntiva")
        cornea = st.text_input("Cornea")
        cristallino = st.text_input("Cristallino")
    with eo2:
        fondo = st.text_input("Fondo oculare")
        pressione = st.text_input("Pressione oculare (mmHg ODX/OSN)")
        pachimetria = st.text_input("Pachimetria (µm ODX/OSN)")

    st.subheader("Motilità / Foria-Tropia")
    motilita = st.text_area("Motilità oculare")
    foria = st.text_area("Foria/Tropia in diottrie prismatiche (Δ)")

    def ref_block(title: str, prefix: str):
        st.subheader(title)
        tab1, tab2, tab3 = st.tabs(["Lontano","Intermedio","Vicino"])
        out = {}
        with tab1:
            c1,c2 = st.columns(2)
            with c1: odx = _ref_eye(f"{prefix}_lont_odx")
            with c2: osn = _ref_eye(f"{prefix}_lont_osn")
            out["lontano"] = {"odx": odx, "osn": osn}
        with tab2:
            c1,c2 = st.columns(2)
            with c1: odx = _ref_eye(f"{prefix}_int_odx")
            with c2: osn = _ref_eye(f"{prefix}_int_osn")
            out["intermedio"] = {"odx": odx, "osn": osn}
        with tab3:
            c1,c2 = st.columns(2)
            with c1: odx = _ref_eye(f"{prefix}_vic_odx")
            with c2: osn = _ref_eye(f"{prefix}_vic_osn")
            add = st.text_input("ADD (vicino)", key=f"{prefix}_add_vic")
            out["vicino"] = {"odx": odx, "osn": osn, "add": add}
        return out

    ref_ab = ref_block("Refrazione abituale", "ab")
    ref_cor = ref_block("Refrazione corretta", "cor")

    st.subheader("Tipo occhiale (per export/prescrizione)")
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
    conclusioni = st.text_area("Conclusioni / Indicazioni terapeutiche")

    if st.button("Genera referto PDF + salva nel DB"):
        tipi_sel = [k for k,v in tipi.items() if v]
        dati = {
            "paziente_id": paz[0],
            "paziente_label": f"{paz[1]} {paz[2]}",
            "data_visita": data_visita,
            "av": {
                "lontano_odx": lont_odx, "lontano_osn": lont_osn,
                "vicino_odx": vic_odx, "vicino_osn": vic_osn,
                "intermedio_odx": int_odx, "intermedio_osn": int_osn,
            },
            "esame_obiettivo": {
                "congiuntiva": congiuntiva,
                "cornea": cornea,
                "cristallino": cristallino,
                "fondo_oculare": fondo,
                "pressione_oculare": pressione,
                "pachimetria": pachimetria,
            },
            "motilita_oculare": motilita,
            "foria_tropia": foria,
            "ref_abituale": ref_ab,
            "ref_corretta": ref_cor,
            "tipi_selezionati": tipi_sel,
            "tipo_note": tipo_note,
            "note": note,
            "conclusioni": conclusioni,
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
