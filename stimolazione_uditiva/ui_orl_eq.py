# modules/stimolazione_uditiva/ui_orl_eq.py
from __future__ import annotations

import io
import json
from datetime import date
from typing import Dict, Tuple

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

from .schema import ensure_audio_schema
from .db_orl import FREQS_STD, list_orl_esami, get_orl_soglie, upsert_orl_esame
from .eq_engine import compute_eq_baseline
from .db_eq import save_eq_profile, list_eq_profiles


def _df_from_soglie(soglie: Dict[str, Dict[int, float | None]]) -> pd.DataFrame:
    rows = []
    for f in FREQS_STD:
        rows.append({"Freq (Hz)": f, "DX (dB HL)": soglie["DX"].get(f), "SX (dB HL)": soglie["SX"].get(f)})
    return pd.DataFrame(rows).set_index("Freq (Hz)")


def _soglie_from_df(df: pd.DataFrame) -> Tuple[Dict[int, float | None], Dict[int, float | None]]:
    def _coerce(v):
        if v is None:
            return None
        s = str(v).strip()
        if s == "" or s.lower() == "nan":
            return None
        try:
            return float(v)
        except Exception:
            return None

    dx: Dict[int, float | None] = {}
    sx: Dict[int, float | None] = {}
    for f in FREQS_STD:
        vdx = df.loc[f, "DX (dB HL)"] if f in df.index else None
        vsx = df.loc[f, "SX (dB HL)"] if f in df.index else None
        dx[f] = _coerce(vdx)
        sx[f] = _coerce(vsx)
    return dx, sx


def _plot_eq(gain_dx: Dict[int, float], gain_sx: Dict[int, float]) -> None:
    freqs = FREQS_STD
    y_dx = [gain_dx.get(f, 0.0) for f in freqs]
    y_sx = [gain_sx.get(f, 0.0) for f in freqs]

    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.plot(freqs, y_dx, marker="o", label="EQ DX")
    ax.plot(freqs, y_sx, marker="o", label="EQ SX")
    ax.axhline(0, linewidth=1)
    ax.set_xscale("log")
    ax.set_xticks(freqs)
    ax.get_xaxis().set_major_formatter(lambda x, pos: f"{int(x)}")
    ax.set_xlabel("Frequenza (Hz)")
    ax.set_ylabel("Gain/Cut (dB)")
    ax.set_title("EQ baseline (clampata)")
    ax.grid(True, which="both", linestyle="--", linewidth=0.5)
    ax.legend()
    st.pyplot(fig)


def _download_json(label: str, obj: dict, filename: str):
    payload = json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8")
    st.download_button(label, data=payload, file_name=filename, mime="application/json")


def _download_csv(label: str, gain_dx: Dict[int, float], gain_sx: Dict[int, float], filename: str):
    out = io.StringIO()
    out.write("freq_hz,gain_dx_db,gain_sx_db\n")
    for f in FREQS_STD:
        out.write(f"{f},{gain_dx.get(f, '')},{gain_sx.get(f, '')}\n")
    st.download_button(label, data=out.getvalue().encode("utf-8"), file_name=filename, mime="text/csv")


def ui_orl_eq(get_conn, paziente_selector_fn):
    st.header("🎧 Stimolazione uditiva — ORL + EQ baseline (MODULO)")

    conn = get_conn()

    ok, msg = ensure_audio_schema(conn)
    if not ok:
        st.error("Errore creazione tabelle ORL/EQ (mostro SQL):")
        st.code(msg)
        return

    paziente_id, paz_label = paziente_selector_fn(conn)
    if not paziente_id:
        st.info("Seleziona un paziente per gestire esami ORL e profili EQ.")
        return

    st.caption(f"Paziente: **{paz_label}** (id {paziente_id})")

    tab1, tab2, tab3 = st.tabs(["1) Inserimento ORL", "2) EQ baseline", "3) Profili EQ"])

    with tab1:
        st.subheader("Nuovo esame ORL (griglia DX/SX)")

        df_blank = _df_from_soglie({"DX": {f: 0.0 for f in FREQS_STD}, "SX": {f: 0.0 for f in FREQS_STD}})

        with st.form("orl_new_editor"):
            c1, c2 = st.columns(2)
            with c1:
                d = st.date_input("Data esame", value=date.today())
            with c2:
                fonte = st.text_input("Fonte", value="ORL")
            note = st.text_area("Note (opzionale)", value="")

            st.markdown("### Soglie (dB HL)")
            df_edit = st.data_editor(
                df_blank,
                use_container_width=True,
                num_rows="fixed",
                column_config={
                    "DX (dB HL)": st.column_config.NumberColumn(step=5.0),
                    "SX (dB HL)": st.column_config.NumberColumn(step=5.0),
                },
            )

            ok_save = st.form_submit_button("💾 Salva esame ORL")

        if ok_save:
            soglie_dx, soglie_sx = _soglie_from_df(df_edit)
            esame_id = upsert_orl_esame(conn, paziente_id, d, fonte, note, soglie_dx, soglie_sx)
            st.success(f"Esame ORL salvato (id {esame_id}).")

        st.divider()
        st.subheader("Esami ORL presenti")
        esami = list_orl_esami(conn, paziente_id, limit=50)
        if not esami:
            st.info("Nessun esame ORL presente.")
        else:
            sel = st.selectbox(
                "Seleziona esame",
                options=esami,
                format_func=lambda r: f"{r[1]} • id {r[0]} • {r[2] or ''}",
            )
            esame_id = int(sel[0])
            soglie = get_orl_soglie(conn, esame_id)
            st.dataframe(_df_from_soglie(soglie), use_container_width=True)

    with tab2:
        st.subheader("Calcolo EQ baseline + grafico + export")

        esami = list_orl_esami(conn, paziente_id, limit=50)
        if not esami:
            st.warning("Inserisci prima almeno un esame ORL.")
            return

        sel = st.selectbox(
            "Esame ORL",
            options=esami,
            format_func=lambda r: f"{r[1]} • id {r[0]} • {r[2] or ''}",
            key="eq_esame_sel",
        )
        esame_id = int(sel[0])
        soglie = get_orl_soglie(conn, esame_id)

        st.markdown("### Soglie usate per il calcolo")
        st.dataframe(_df_from_soglie(soglie), use_container_width=True)

        c1, c2, c3 = st.columns(3)
        with c1:
            boost_max = st.number_input("BoostMax (dB)", value=12.0, step=1.0)
        with c2:
            cut_max = st.number_input("CutMax (dB)", value=12.0, step=1.0)
        with c3:
            smoothing = st.checkbox("Smoothing inviluppo", value=True)

        if st.button("⚙️ Calcola EQ", key="btn_calc_eq"):
            gain_dx = compute_eq_baseline(soglie["DX"], boost_max_db=float(boost_max), cut_max_db=float(cut_max), smoothing=bool(smoothing))
            gain_sx = compute_eq_baseline(soglie["SX"], boost_max_db=float(boost_max), cut_max_db=float(cut_max), smoothing=bool(smoothing))

            st.session_state["eq_last"] = {
                "paziente_id": int(paziente_id),
                "esame_id": int(esame_id),
                "params": {
                    "engine": "EQ_V0",
                    "boost_max_db": float(boost_max),
                    "cut_max_db": float(cut_max),
                    "smoothing": bool(smoothing),
                    "freqs_hz": FREQS_STD,
                },
                "gain_dx": gain_dx,
                "gain_sx": gain_sx,
            }

        eq_last = st.session_state.get("eq_last")
        if not eq_last or int(eq_last.get("esame_id", -1)) != esame_id:
            st.info("Premi **Calcola EQ** per vedere risultato, grafico ed export.")
        else:
            df_eq = pd.DataFrame(
                [{"Freq (Hz)": f, "Gain DX (dB)": eq_last["gain_dx"][f], "Gain SX (dB)": eq_last["gain_sx"][f]} for f in FREQS_STD]
            ).set_index("Freq (Hz)")
            st.dataframe(df_eq, use_container_width=True)

            _plot_eq(eq_last["gain_dx"], eq_last["gain_sx"])

            base = f"eq_paz{paziente_id}_esame{esame_id}"
            _download_json("⬇️ Scarica JSON (EQ)", eq_last, filename=f"{base}.json")
            _download_csv("⬇️ Scarica CSV (EQ)", eq_last["gain_dx"], eq_last["gain_sx"], filename=f"{base}.csv")

            st.divider()
            st.subheader("Salva profilo EQ")
            nome = st.text_input("Nome profilo", value=f"EQ ORL {sel[1]} (V0)")
            if st.button("💾 Salva profilo EQ", key="btn_save_eq"):
                pid = save_eq_profile(
                    conn,
                    paziente_id=paziente_id,
                    esame_id=esame_id,
                    nome=nome,
                    params=eq_last["params"],
                    gain_dx=eq_last["gain_dx"],
                    gain_sx=eq_last["gain_sx"],
                )
                st.success(f"Profilo EQ salvato (id {pid}).")

    with tab3:
        st.subheader("Profili EQ salvati (per paziente)")
        prof = list_eq_profiles(conn, paziente_id, limit=100)
        if not prof:
            st.info("Nessun profilo EQ salvato.")
        else:
            st.dataframe(
                [{"id": r[0], "nome": r[1], "created_at": str(r[2]), "esame_id": r[3]} for r in prof],
                use_container_width=True,
                hide_index=True,
            )
