# PATCH UI — modules/stimolazione_uditiva/ui_generatore_stimolazione.py

1) Aggiungi questi import in alto:
   from .db_eq import read_eq_profile
   from .db_jobs import read_tomatis_preset
   from .render_preview import render_preview_wav

2) Sotto la sezione "Input audio" (o subito prima della coda JOB) aggiungi:

    st.divider()
    st.subheader("Preview render (B2) — WAV 16-bit, clip breve")

    prev_secs = st.slider("Durata preview (secondi)", 5, 60, 30)
    wav_prev = st.file_uploader("Carica WAV 16-bit per preview", type=["wav"], key="wav_prev")

    if st.button("🎧 Render preview adesso", disabled=(wav_prev is None)):
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

NOTE: Preview B2 accetta SOLO WAV 16-bit.
