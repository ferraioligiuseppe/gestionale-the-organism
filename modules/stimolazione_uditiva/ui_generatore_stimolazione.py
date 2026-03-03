# modules/stimolazione_uditiva/ui_generatore_stimolazione.py
from __future__ import annotations
import streamlit as st

from .schema import ensure_audio_schema
from .db_eq import list_eq_profiles
from .db_jobs import ensure_jobs_schema, seed_tomatis_presets, list_tomatis_presets, create_render_job, list_render_jobs

def ui_generatore_stimolazione(get_conn, paziente_selector_fn):
    st.header("🎧 Genera stimolazione (JOB) — EQ + Preset Tomatis")

    conn = get_conn()

    # schema ORL/EQ
    ok, msg = ensure_audio_schema(conn)
    if not ok:
        st.error("Errore schema ORL/EQ:")
        st.code(msg)
        return

    # schema jobs/presets
    try:
        ensure_jobs_schema(conn)
        seed_tomatis_presets(conn)
    except Exception as e:
        st.error("Errore creazione schema JOB/preset:")
        st.code(f"{type(e).__name__}: {e}")
        return

    paziente_id, paz_label = paziente_selector_fn(conn)
    if not paziente_id:
        st.info("Seleziona un paziente.")
        return

    st.caption(f"Paziente: **{paz_label}** (id {paziente_id})")

    # 1) scegli profilo EQ
    prof = list_eq_profiles(conn, paziente_id, limit=200)
    if not prof:
        st.warning("Nessun profilo EQ salvato. Prima crea e salva un profilo in 'ORL + EQ (MODULO)'.")
        return

    sel_eq = st.selectbox(
        "Profilo EQ",
        options=prof,
        format_func=lambda r: f"id {r[0]} • {r[1]} • {r[2]}",
    )
    eq_profile_id = int(sel_eq[0])

    # 2) preset Tomatis
    presets = list_tomatis_presets(conn)
    sel_p = st.selectbox(
        "Preset Tomatis",
        options=presets,
        format_func=lambda r: f"{r[1]} (id {r[0]})",
    )
    preset_id = int(sel_p[0])

    st.divider()
    st.subheader("Input audio")

    input_kind = st.radio("Tipo input", options=["Upload (piccolo)", "Dropbox path (testuale)"], horizontal=True)

    input_ref = None
    if input_kind == "Upload (piccolo)":
        up = st.file_uploader("Carica WAV/MP3/OGG (consigliato < 50 MB per TEST)", type=["wav","mp3","ogg"])
        if up is not None:
            # per ora NON salviamo file sul server (Streamlit effimero).
            # creiamo JOB con filename: in Step B2 decideremo dove persist.
            input_ref = up.name
            st.info("Nota: in questa fase il file non viene renderizzato. Creiamo solo il JOB (queued).")
    else:
        input_ref = st.text_input("Dropbox path (es. /INBOX/brano.wav)", value="")

    st.divider()
    st.subheader("Parametri rapidi (override)")

    c1, c2, c3 = st.columns(3)
    with c1:
        dominant_side = st.selectbox("Dominanza", ["DX","SX"])
    with c2:
        bias_mode = st.selectbox("Bias mode", ["fixed","alternate"])
    with c3:
        ratio = st.slider("Ratio dominante", min_value=0.50, max_value=0.90, value=0.70, step=0.05)

    alt_minutes = st.number_input("Switch minuti (se alternate)", value=2.5, step=0.5)

    params = {
        "dominant_side": dominant_side,
        "bias_mode": bias_mode,
        "ratio": float(ratio),
        "alternate_minutes": float(alt_minutes),
        "note": "JOB creato da UI_generatore_stimolazione (Step B1, no render)",
    }

    can_create = bool(input_ref) and eq_profile_id and preset_id

    if st.button("🧾 Crea JOB render (queued)", disabled=not can_create):
        kind = "upload" if input_kind.startswith("Upload") else "dropbox_path"
        jid = create_render_job(
            conn,
            paziente_id=paziente_id,
            eq_profile_id=eq_profile_id,
            preset_id=preset_id,
            input_kind=kind,
            input_ref=str(input_ref),
            params=params,
        )
        st.success(f"JOB creato! id = {jid} (status = queued)")

    st.divider()
    st.subheader("Coda JOB (paziente)")
    jobs = list_render_jobs(conn, paziente_id, limit=50)
    if not jobs:
        st.info("Nessun job per questo paziente.")
    else:
        st.dataframe(
            [
                {
                    "id": r[0],
                    "created_at": r[1],
                    "status": r[2],
                    "progress": float(r[3]) if r[3] is not None else 0,
                    "input_kind": r[4],
                    "input_ref": r[5],
                    "output_ref": r[6],
                    "error": r[7],
                }
                for r in jobs
            ],
            use_container_width=True,
            hide_index=True,
        )
