# PATCH UI — modules/stimolazione_uditiva/ui_generatore_stimolazione.py

Incolla QUESTO BLOCCO sotto la Preview B2 (o prima della coda JOB):

st.divider()
st.subheader("Render file finale (B3) — WAV / FLAC / MP3")

final_secs = st.number_input("Limita durata (secondi) per test (0 = tutto il file)", value=0, step=30)

out_wav = st.checkbox("Output WAV", value=True)
out_flac = st.checkbox("Output FLAC", value=True)
out_mp3 = st.checkbox("Output MP3", value=False)
mp3_bitrate = st.selectbox("Bitrate MP3", ["128k", "192k", "256k"], index=1)

audio_final = st.file_uploader(
    "Carica file audio (consigliato WAV 16-bit; MP3/FLAC best-effort)",
    type=["wav", "mp3", "flac"],
    key="audio_final"
)

if st.button("🏁 Render file finale adesso", disabled=(audio_final is None)):
    from .db_eq import read_eq_profile
    from .db_jobs import read_tomatis_preset
    from .render_final import render_full

    eq = read_eq_profile(conn, eq_profile_id)
    if not eq:
        st.error("EQ profile non trovato.")
    else:
        _, _, gain_dx, gain_sx = eq
        pres = read_tomatis_preset(conn, preset_id)
        if not pres:
            st.error("Preset Tomatis non trovato.")
        else:
            _, preset_params = pres
            try:
                fmts = []
                if out_wav: fmts.append("wav")
                if out_flac: fmts.append("flac")
                if out_mp3: fmts.append("mp3")
                if not fmts:
                    st.warning("Seleziona almeno un formato di output.")
                else:
                    max_s = float(final_secs) if float(final_secs) > 0 else None
                    outs = render_full(
                        audio_final.getvalue(),
                        filename=audio_final.name,
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
                        st.download_button("⬇️ Scarica WAV", data=outs["wav"], file_name=f"{base}.wav", mime="audio/wav")
                    if "flac" in outs:
                        st.download_button("⬇️ Scarica FLAC", data=outs["flac"], file_name=f"{base}.flac", mime="audio/flac")
                    if "mp3" in outs:
                        st.download_button("⬇️ Scarica MP3", data=outs["mp3"], file_name=f"{base}.mp3", mime="audio/mpeg")
            except Exception as e:
                st.error("Errore render file finale (B3).")
                st.code(f"{type(e).__name__}: {e}")
