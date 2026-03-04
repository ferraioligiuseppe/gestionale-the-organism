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
    st.subheader("Preview render (B2) — WAV 16-bit")

    st.caption(
        "Preview veloce in Streamlit: applica EQ (DX/SX) + gating Tomatis-like su una clip breve.\n"
        "⚠️ In questa fase supporto SOLO WAV PCM 16-bit per stabilità."
    )

    prev_secs = st.slider("Durata preview (secondi)", 5, 60, 30)

    wav_prev = st.file_uploader(
        "Carica WAV 16-bit per preview",
        type=["wav"],
        key="wav_prev"
    )

    if st.button("🎧 Render preview adesso", disabled=(wav_prev is None)):
        # Import locali: se manca un file, non crasha tutta la pagina
        try:
            from .db_eq import read_eq_profile
            from .db_jobs import read_tomatis_preset
            from .render_preview import render_preview_wav
        except Exception as e:
            st.error("Manca qualche file della patch B2 (render_preview/db_eq/db_jobs).")
            st.code(f"{type(e).__name__}: {e}")
        else:
            eq = read_eq_profile(conn, int(eq_profile_id))
            if not eq:
                st.error("EQ profile non trovato.")
            else:
                _, _params_eq, gain_dx, gain_sx = eq
                pres = read_tomatis_preset(conn, int(preset_id))
                if not pres:
                    st.error("Preset Tomatis non trovato.")
                else:
                    _pname, preset_params = pres
                    try:
                        out_bytes, _fs = render_preview_wav(
                            wav_prev.getvalue(),
                            eq_gain_dx=gain_dx,
                            eq_gain_sx=gain_sx,
                            preset_params=preset_params,
                            seconds=float(prev_secs),
                        )
                        st.success("Preview pronta!")
                        st.audio(out_bytes, format="audio/wav")
                        st.download_button(
                            "⬇️ Scarica preview WAV",
                            data=out_bytes,
                            file_name=f"preview_paz{paziente_id}_eq{eq_profile_id}_preset{preset_id}.wav",
                            mime="audio/wav",
                        )
                    except Exception as e:
                        st.error("Errore render preview (B2).")
                        st.code(f"{type(e).__name__}: {e}")

    
st.divider()
st.subheader("Render file finale (B3) — WAV / FLAC / MP3")

st.caption(
    "Render completo in Streamlit (best-effort). Per file lunghi può essere pesante su Streamlit Cloud.\n"
    "• WAV: sempre OK\n"
    "• FLAC: richiede 'soundfile'\n"
    "• MP3: richiede 'pydub' + ffmpeg"
)

final_secs = st.number_input(
    "Limita durata (secondi) per test (0 = tutto il file)",
    value=0,
    step=30,
)

cfmt1, cfmt2, cfmt3 = st.columns(3)
with cfmt1:
    out_wav = st.checkbox("Output WAV", value=True)
with cfmt2:
    out_flac = st.checkbox("Output FLAC", value=True)
with cfmt3:
    out_mp3 = st.checkbox("Output MP3", value=False)

mp3_bitrate = st.selectbox("Bitrate MP3", ["128k", "192k", "256k"], index=1)

audio_final = st.file_uploader(
    "Carica file audio (consigliato WAV 16-bit; MP3/FLAC best-effort)",
    type=["wav", "mp3", "flac"],
    key="audio_final",
)

if st.button("🏁 Render file finale adesso", disabled=(audio_final is None)):
    try:
        from .db_eq import read_eq_profile
        from .db_jobs import read_tomatis_preset
        from .render_final import render_full
    except Exception as e:
        st.error("Manca qualche file della patch B3 (render_final/db_eq/db_jobs) oppure dipendenze audio non installate.")
        st.code(f"{type(e).__name__}: {e}")
    else:
        eq = read_eq_profile(conn, int(eq_profile_id))
        if not eq:
            st.error("EQ profile non trovato.")
        else:
            _, _params_eq, gain_dx, gain_sx = eq
            pres = read_tomatis_preset(conn, int(preset_id))
            if not pres:
                st.error("Preset Tomatis non trovato.")
            else:
                _pname, preset_params = pres
                try:
                    fmts = []
                    if out_wav:
                        fmts.append("wav")
                    if out_flac:
                        fmts.append("flac")
                    if out_mp3:
                        fmts.append("mp3")
                    if not fmts:
                        st.warning("Seleziona almeno un formato di output.")
                    else:
                        max_s = float(final_secs) if float(final_secs) > 0 else None
                        outs = render_full(
                            audio_final.getvalue(),
                            filename=getattr(audio_final, "name", "input"),
                            eq_gain_dx=gain_dx,
                            eq_gain_sx=gain_sx,
                            preset_params=preset_params,
                            limiter_peak_dbfs=float(preset_params.get("safety", {}).get("limiter_peak_dbfs", -1.0)),
                            out_formats=tuple(fmts),
                            mp3_bitrate=str(mp3_bitrate),
                            max_seconds=max_s,
                        )

                        st.success("Render completato!")
                        base = f"stim_paz{paziente_id}_eq{eq_profile_id}_preset{preset_id}"

                        if "wav" in outs:
                            st.audio(outs["wav"], format="audio/wav")
                            st.download_button(
                                "⬇️ Scarica WAV",
                                data=outs["wav"],
                                file_name=f"{base}.wav",
                                mime="audio/wav",
                            )
                        if "flac" in outs:
                            st.download_button(
                                "⬇️ Scarica FLAC",
                                data=outs["flac"],
                                file_name=f"{base}.flac",
                                mime="audio/flac",
                            )
                        if "mp3" in outs:
                            st.download_button(
                                "⬇️ Scarica MP3",
                                data=outs["mp3"],
                                file_name=f"{base}.mp3",
                                mime="audio/mpeg",
                            )

                except Exception as e:
                    st.error("Errore render file finale (B3).")
                    st.code(f"{type(e).__name__}: {e}")

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
