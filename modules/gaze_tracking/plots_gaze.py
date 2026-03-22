from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd


def build_heatmap_figure(fix_df: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(8, 5))
    if not fix_df.empty:
        sizes = fix_df["dur_ms"].fillna(50).clip(lower=20)
        ax.scatter(fix_df["x"], fix_df["y"], s=sizes, alpha=0.5)
    ax.set_title("Heatmap fissazioni")
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.invert_yaxis()
    ax.grid(True, alpha=0.2)
    return fig


def build_scanpath_figure(fix_df: pd.DataFrame, trans_df: pd.DataFrame | None = None):
    fig, ax = plt.subplots(figsize=(8, 5))
    if not fix_df.empty:
        ax.plot(fix_df["x"], fix_df["y"], marker="o")
        for _, row in fix_df.iterrows():
            ax.text(row["x"], row["y"], str(int(row["fix_id"])), fontsize=8)
    ax.set_title("Scanpath")
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.invert_yaxis()
    ax.grid(True, alpha=0.2)
    return fig


def build_fixation_histogram_figure(fix_df: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(8, 5))
    if not fix_df.empty and "dur_ms" in fix_df.columns:
        ax.hist(fix_df["dur_ms"].dropna(), bins=20)
    ax.set_title("Distribuzione durata fissazioni")
    ax.set_xlabel("ms")
    ax.set_ylabel("Frequenza")
    ax.grid(True, alpha=0.2)
    return fig


def build_saccade_histogram_figure(sac_df: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(8, 5))
    if not sac_df.empty and "amp" in sac_df.columns:
        ax.hist(sac_df["amp"].dropna(), bins=20)
    ax.set_title("Distribuzione ampiezza saccadi")
    ax.set_xlabel("Ampiezza")
    ax.set_ylabel("Frequenza")
    ax.grid(True, alpha=0.2)
    return fig


def build_timeline_figure(raw_df: pd.DataFrame, fix_df: pd.DataFrame, trans_df: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(10, 4))

    if not raw_df.empty and "tracking_ok" in raw_df.columns:
        ok = raw_df[raw_df["tracking_ok"]]
        bad = raw_df[~raw_df["tracking_ok"]]
        if not ok.empty:
            ax.scatter(ok["ts_ms"], [1] * len(ok), s=6, label="tracking_ok")
        if not bad.empty:
            ax.scatter(bad["ts_ms"], [0.8] * len(bad), s=6, label="tracking_loss")

    if not fix_df.empty:
        for _, row in fix_df.iterrows():
            ax.hlines(y=1.2, xmin=row["start_ms"], xmax=row["end_ms"], linewidth=3)

    ax.set_title("Timeline eventi")
    ax.set_xlabel("Tempo (ms)")
    ax.set_yticks([])
    ax.grid(True, alpha=0.2)
    ax.legend()
    return fig
