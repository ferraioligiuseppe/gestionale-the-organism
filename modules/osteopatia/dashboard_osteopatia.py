import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

def render_dashboard_osteo(sedute_rows):
    st.markdown("### Dashboard osteopatia")

    if not sedute_rows:
        st.info("Nessuna seduta per calcolare la dashboard.")
        return

    df = pd.DataFrame(sedute_rows).copy()
    df["data_seduta"] = pd.to_datetime(df.get("data_seduta"), errors="coerce")
    df = df.sort_values("data_seduta")

    c1, c2, c3 = st.columns(3)
    c1.metric("Sedute totali", int(len(df)))
    if "dolore_pre" in df and df["dolore_pre"].notna().any():
        c2.metric("Dolore pre (ultimo)", int(df["dolore_pre"].dropna().iloc[-1]))
    if "dolore_post" in df and df["dolore_post"].notna().any():
        c3.metric("Dolore post (ultimo)", int(df["dolore_post"].dropna().iloc[-1]))

    st.markdown("#### Andamento dolore (pre vs post)")
    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.plot(df["data_seduta"], df.get("dolore_pre"), marker="o", label="Dolore pre")
    ax.plot(df["data_seduta"], df.get("dolore_post"), marker="o", label="Dolore post")
    ax.set_xlabel("Data")
    ax.set_ylabel("Dolore (0-10)")
    ax.legend()
    st.pyplot(fig, clear_figure=True)

    st.markdown("#### Tabella sedute (ultime 20)")
    st.dataframe(df.sort_values("data_seduta", ascending=False).head(20), use_container_width=True)
