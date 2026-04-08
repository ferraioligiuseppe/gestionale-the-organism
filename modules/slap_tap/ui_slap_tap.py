import streamlit as st
import streamlit.components.v1 as components

from modules.slap_tap.config_slap_tap import LETTER_MAPPING
from modules.slap_tap.logic_slap_tap import (
    generate_sequence,
    parse_operator_input,
    evaluate_response,
    expected_tick_times,
    compute_timing_errors,
    merge_scoring,
    now_ts,
)
from modules.slap_tap.db_slap_tap import (
    ensure_slap_tap_tables,
    save_slap_tap_session,
)
from modules.slap_tap.report_slap_tap import build_slap_tap_report


def render_metronome_widget(bpm: int, mode: str, steps: int):
    interval_ms = int(60000 / max(bpm, 1))
    visual_interval_ms = interval_ms * 2 if mode == "1:2" else interval_ms

    html = f"""
    <div style="display:flex;flex-direction:column;gap:12px;align-items:center;justify-content:center;padding:10px;">
      <div id="beatLamp" style="
          width:90px;height:90px;border-radius:999px;
          background:#d9d9d9;border:3px solid #999;transition:all .08s ease;
      "></div>
      <div style="font-family:sans-serif;font-size:18px;">Metronomo attivo: {bpm} BPM • modalità {mode}</div>
      <button onclick="startMetro()" style="padding:10px 18px;border:none;border-radius:10px;cursor:pointer;">Avvia metronomo</button>
      <button onclick="stopMetro()" style="padding:10px 18px;border:none;border-radius:10px;cursor:pointer;">Stop</button>
    </div>

    <script>
    let metroTimer = null;
    let ctx = null;

    function beep() {{
        try {{
            if (!ctx) {{
                ctx = new (window.AudioContext || window.webkitAudioContext)();
            }}
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.type = "sine";
            osc.frequency.value = 880;
            gain.gain.value = 0.03;
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.start();
            setTimeout(() => {{
                osc.stop();
            }}, 70);
        }} catch (e) {{
            console.log(e);
        }}
    }}

    function lampFlash() {{
        const lamp = document.getElementById("beatLamp");
        lamp.style.background = "#3cb371";
        lamp.style.transform = "scale(1.08)";
        setTimeout(() => {{
            lamp.style.background = "#d9d9d9";
            lamp.style.transform = "scale(1)";
        }}, 120);
    }}

    function tick() {{
        beep();
        lampFlash();
    }}

    function startMetro() {{
        stopMetro();
        tick();
        metroTimer = setInterval(tick, {visual_interval_ms});
    }}

    function stopMetro() {{
        if (metroTimer) {{
            clearInterval(metroTimer);
            metroTimer = null;
        }}
    }}
    </script>
    """
    components.html(html, height=220)


def ui_slap_tap(conn=None):
    st.title("🧠 SLAP TAP – Gestione esercizi")
    st.caption("Protocollo PNEV visuo-motorio, ritmico e simbolico")

    if conn is not None:
        try:
            ensure_slap_tap_tables(conn)
        except Exception as e:
            st.warning(f"Tabelle SLAP TAP non inizializzate: {e}")

    if "slap_sequence" not in st.session_state:
        st.session_state.slap_sequence = []

    if "slap_started_at" not in st.session_state:
        st.session_state.slap_started_at = None

    if "slap_response_times" not in st.session_state:
        st.session_state.slap_response_times = []

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        patient_id = st.text_input("Patient ID", "")
    with c2:
        visit_id = st.text_input("Visit ID", "")
    with c3:
        operator_name = st.text_input("Operatore", "")
    with c4:
        sequence_length = st.slider("Lunghezza", 1, 12, 4)

    c5, c6, c7 = st.columns(3)
    with c5:
        bpm = st.slider("BPM", 40, 120, 60)
    with c6:
        mode = st.selectbox("Modalità metronomo", ["1:1", "1:2"])
    with c7:
        tolerance_ms = st.slider("Tolleranza timing (ms)", 100, 800, 350, 50)

    st.markdown("---")

    left, right = st.columns([1, 1])

    with left:
        if st.button("🎲 Genera nuova sequenza", use_container_width=True):
            st.session_state.slap_sequence = generate_sequence(sequence_length)
            st.session_state.slap_started_at = None
            st.session_state.slap_response_times = []

        if st.session_state.slap_sequence:
            st.subheader("Sequenza target")
            cols = st.columns(len(st.session_state.slap_sequence))
            for i, letter in enumerate(st.session_state.slap_sequence):
                with cols[i]:
                    st.markdown(f"## {letter.upper()}")
                    st.caption(LETTER_MAPPING[letter]["label"])

    with right:
        st.subheader("Metronomo")
        render_metronome_widget(bpm=bpm, mode=mode, steps=sequence_length)

        c8, c9 = st.columns(2)
        with c8:
            if st.button("▶️ Registra inizio prova", use_container_width=True):
                st.session_state.slap_started_at = now_ts()
                st.session_state.slap_response_times = []
                st.success("Inizio prova registrato.")
        with c9:
            if st.button("⏱ Registra tempo risposta", use_container_width=True):
                if st.session_state.slap_started_at is None:
                    st.warning("Prima registra l'inizio prova.")
                else:
                    st.session_state.slap_response_times.append(now_ts())
                    st.info(f"Tempi registrati: {len(st.session_state.slap_response_times)}")

    st.markdown("---")

    st.subheader("Inserimento risposta operatore")
    operator_response = st.text_input(
        "Risposta simbolica",
        placeholder="Esempio: b d p q"
    )
    notes = st.text_area("Note operatore", height=100)

    if st.button("✅ Valuta esercizio", use_container_width=True):
        expected = st.session_state.slap_sequence
        actual = parse_operator_input(operator_response)

        if not expected:
            st.error("Genera prima una sequenza.")
            st.stop()

        symbol_eval = evaluate_response(expected, actual)

        if st.session_state.slap_started_at is not None:
            exp_times = expected_tick_times(
                start_ts=st.session_state.slap_started_at,
                bpm=bpm,
                n_items=len(expected),
                mode=mode
            )
        else:
            exp_times = []

        timing_eval = compute_timing_errors(
            expected_times=exp_times,
            actual_times=st.session_state.slap_response_times,
            tolerance_ms=tolerance_ms,
        ) if exp_times else [
            {
                "index": i,
                "timing_label": "",
                "delta_ms": None,
                "in_tolerance": False,
            }
            for i in range(len(expected))
        ]

        scoring = merge_scoring(symbol_eval, timing_eval)

        st.success(
            f"Accuratezza simbolica: {scoring['symbol_accuracy']}% • "
            f"Accuratezza timing: {scoring['timing_accuracy']}%"
        )

        rows = scoring["rows"]
        for row in rows:
            icon = "✔" if row["correct"] else "❌"
            st.write(
                f"{icon} Pos {row['index'] + 1} | "
                f"atteso={row['expected']} | "
                f"risposta={row.get('actual')} | "
                f"errore={row.get('error_type') or '-'} | "
                f"timing={row.get('timing_label') or '-'} | "
                f"delta={row.get('delta_ms') if row.get('delta_ms') is not None else '-'} ms"
            )

        report_text = build_slap_tap_report(
            scoring=scoring,
            bpm=bpm,
            mode=mode,
            notes=notes
        )

        st.markdown("### Referto sintetico")
        st.text_area("Report", value=report_text, height=320)

        if conn is not None:
            try:
                session_id = save_slap_tap_session(
                    conn=conn,
                    patient_id=int(patient_id) if str(patient_id).strip().isdigit() else None,
                    visit_id=int(visit_id) if str(visit_id).strip().isdigit() else None,
                    operator_name=operator_name or None,
                    bpm=bpm,
                    mode=mode,
                    sequence=expected,
                    response=actual,
                    response_times=st.session_state.slap_response_times,
                    scoring=scoring,
                    notes=notes or None,
                )
                st.success(f"Sessione salvata con ID {session_id}")
            except Exception as e:
                st.error(f"Errore salvataggio sessione: {e}")
