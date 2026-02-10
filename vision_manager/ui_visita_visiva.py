import json
import streamlit as st
from datetime import datetime
from vision_core.pdf_referto import genera_referto_visita_bytes

def _av_options():
    return ["NV","1/10","2/10","3/10","4/10","5/10","6/10","7/10","8/10","9/10","10/10","11/10","12/10"]

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
        lont_od = st.selectbox("Lontano OD", av_opts, index=0)
        lont_os = st.selectbox("Lontano OS", av_opts, index=0)
    with c2:
        vic_od = st.selectbox("Vicino OD", av_opts, index=0)
        vic_os = st.selectbox("Vicino OS", av_opts, index=0)
    with c3:
        int_od = st.selectbox("Intermedio OD", av_opts, index=0)
        int_os = st.selectbox("Intermedio OS", av_opts, index=0)

    st.subheader("Esame obiettivo")
    eo1, eo2 = st.columns(2)
    with eo1:
        congiuntiva = st.text_input("Congiuntiva")
        cornea = st.text_input("Cornea")
        cristallino = st.text_input("Cristallino")
    with eo2:
        fondo = st.text_input("Fondo oculare")
        pressione = st.text_input("Pressione oculare (mmHg OD/OS)")
        pachimetria = st.text_input("Pachimetria (µm OD/OS)")

    st.subheader("Motilità / Foria-Tropia")
    motilita = st.text_area("Motilità oculare")
    foria = st.text_area("Foria/Tropia in diottrie prismatiche (Δ)")

    st.subheader("Refrazione abituale")
    tab1, tab2, tab3 = st.tabs(["Lontano","Intermedio","Vicino"])
    ref_ab = {}
    with tab1:
        c1,c2 = st.columns(2)
        with c1: od = _ref_eye("ab_lont_od")
        with c2: os_ = _ref_eye("ab_lont_os")
        ref_ab["lontano"] = {"od": od, "os": os_}
    with tab2:
        c1,c2 = st.columns(2)
        with c1: od = _ref_eye("ab_int_od")
        with c2: os_ = _ref_eye("ab_int_os")
        ref_ab["intermedio"] = {"od": od, "os": os_}
    with tab3:
        c1,c2 = st.columns(2)
        with c1: od = _ref_eye("ab_vic_od")
        with c2: os_ = _ref_eye("ab_vic_os")
        add = st.text_input("ADD (vicino)")
        ref_ab["vicino"] = {"od": od, "os": os_, "add": add}

    st.subheader("Refrazione corretta")
    tab1, tab2, tab3 = st.tabs(["Lontano ","Intermedio ","Vicino "])
    ref_cor = {}
    with tab1:
        c1,c2 = st.columns(2)
        with c1: od = _ref_eye("cor_lont_od")
        with c2: os_ = _ref_eye("cor_lont_os")
        ref_cor["lontano"] = {"od": od, "os": os_}
    with tab2:
        c1,c2 = st.columns(2)
        with c1: od = _ref_eye("cor_int_od")
        with c2: os_ = _ref_eye("cor_int_os")
        ref_cor["intermedio"] = {"od": od, "os": os_}
    with tab3:
        c1,c2 = st.columns(2)
        with c1: od = _ref_eye("cor_vic_od")
        with c2: os_ = _ref_eye("cor_vic_os")
        add = st.text_input("ADD (vicino) ", key="add_cor")
        ref_cor["vicino"] = {"od": od, "os": os_, "add": add}

    note = st.text_area("Note")
    conclusioni = st.text_area("Conclusioni / Indicazioni terapeutiche")

    if st.button("Genera referto PDF + salva nel DB"):
        dati = {
            "paziente_id": paz[0],
            "paziente_label": f"{paz[1]} {paz[2]}",
            "data_visita": data_visita,
            "av": {
                "lontano_od": lont_od, "lontano_os": lont_os,
                "vicino_od": vic_od, "vicino_os": vic_os,
                "intermedio_od": int_od, "intermedio_os": int_os,
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
            "note": note,
            "conclusioni": conclusioni,
        }
        pdf_bytes = genera_referto_visita_bytes(dati)

        is_pg = conn.__class__.__module__.startswith("psycopg2")
        ph = "%s" if is_pg else "?"

        if is_pg:
            import psycopg2
            from psycopg2.extras import Json
            json_val = Json(dati)
            blob = psycopg2.Binary(pdf_bytes)
        else:
            json_val = json.dumps(dati, ensure_ascii=False)
            blob = pdf_bytes

        sql = f"INSERT INTO visite_visive (paziente_id, data_visita, dati_json, pdf_bytes) VALUES ({ph},{ph},{ph},{ph})"
        cur = conn.cursor()
        cur.execute(sql, (paz[0], data_visita, json_val, blob))
        conn.commit()

        safe = f"{paz[1]}_{paz[2]}".replace(" ", "_")
        st.success("Visita salvata nel DB ✅")
        st.download_button("Scarica referto PDF", data=pdf_bytes, file_name=f"referto_visita_{safe}_{data_visita}.pdf")
