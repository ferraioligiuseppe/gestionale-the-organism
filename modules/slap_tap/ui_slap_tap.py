import json
import streamlit as st

from modules.slap_tap.logic_slap_tap import (
    generate_sequence,
    parse_operator_input,
    evaluate_response,
)

from modules.slap_tap.report_slap_tap import build_slap_tap_report
from modules.slap_tap.db_slap_tap import ensure_slap_tap_tables
from modules.slap_tap.config_slap_tap import LETTER_MAPPING


def ui_slap_tap(conn=None):
    st.title("SLAP TAP")

    try:
        ensure_slap_tap_tables(conn)
    except Exception as e:
        st.warning(f"Tabelle SLAP TAP non inizializzate: {e}")

    if "slap_sequence" not in st.session_state:
        st.session_state.slap_sequence = []

    length = st.slider("Lunghezza sequenza", 1, 10, 4)

    if st.button("Genera Sequenza"):
        st.session_state.slap_sequence = generate_sequence(length)

    if st.session_state.slap_sequence:
        st.subheader("Sequenza")

        cols = st.columns(len(st.session_state.slap_sequence))

        for i, letter in enumerate(st.session_state.slap_sequence):
            with cols[i]:
                st.markdown(f"## {letter.upper()}")
                st.caption(LETTER_MAPPING[letter]["label"])

    response = st.text_input("Risposta operatore (es. b d p q)")

    if st.button("Valuta"):
        actual = parse_operator_input(response)

        scoring = evaluate_response(
            st.session_state.slap_sequence,
            actual
        )

        st.success(f"Accuratezza: {scoring['accuracy']}%")

        report = build_slap_tap_report(scoring)
        st.text_area("Report", report, height=220)

        if conn is not None:
            cur = conn.cursor()
            try:
                cur.execute("""
                    INSERT INTO slap_tap_sessions (
                        sequence_json,
                        response_json,
                        accuracy
                    )
                    VALUES (%s,%s,%s)
                """, (
                    json.dumps(st.session_state.slap_sequence),
                    json.dumps(actual),
                    scoring["accuracy"]
                ))
                conn.commit()
                st.success("Sessione salvata.")
            except Exception as e:
                st.error(f"Errore salvataggio sessione: {e}")
            finally:
                try:
                    cur.close()
                except Exception:
                    pass
