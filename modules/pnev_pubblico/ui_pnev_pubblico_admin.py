# -*- coding: utf-8 -*-
"""
modules/pnev_pubblico/ui_pnev_pubblico_admin.py — MILESTONE 5

Modulo ADMIN del percorso pubblico MAPS-CLEAR dentro il gestionale The Organism.
Dashboard iscritti, dettaglio paziente con grafici, questionari pre/post, export CSV.

Uso dal gestionale (stesso pattern degli altri moduli):

    from modules.pnev_pubblico.ui_pnev_pubblico_admin import render_pnev_pubblico_admin
    ...
    render_pnev_pubblico_admin(conn)   # conn = get_connection() del gestionale

Convenzioni: conn dal chiamante, %s psycopg2, timezone Europe/Rome in lettura,
brand green #1D6B44. Self-init dello schema alla prima apertura (idempotente).
"""

import io
import json
import csv as csv_mod
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from modules.pnev_pubblico import db_pnev_pubblico as db

TZ = ZoneInfo("Europe/Rome")
VERDE = "#1D6B44"

ETICHETTE_BASELINE = {
    "q1": "Quanto la balbuzie incide sulla tua vita (1-10)",
    "q2": "Frequenza dei blocchi (1-10)",
    "q3": "Disagio nel parlare con estranei (1-10)",
}


# ═══════════════════════════════════════════════════════════════
# QUERY LOCALI (di sola lettura, per report ed export)
# ═══════════════════════════════════════════════════════════════

def _tutte_le_sessioni(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT s.utente_id, u.nome, u.email, s.giorno,
               s.data_sessione AT TIME ZONE 'Europe/Rome' AS data_sessione,
               s.modalita, s.delay_ms, s.orecchio,
               s.fluency_pre, s.fluency_post, s.comfort, s.beneficio, s.note
        FROM pnev_pubblico_sessioni s
        JOIN pnev_pubblico_utenti u ON u.id = s.utente_id
        ORDER BY u.nome, s.giorno
    """)
    colonne = [d[0] for d in cur.description]
    return pd.DataFrame(cur.fetchall(), columns=colonne)


def _iscrizioni_per_giorno(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT date(creato_il AT TIME ZONE 'Europe/Rome') AS giorno, count(*) AS iscritti
        FROM pnev_pubblico_utenti
        WHERE origine = 'maps_clear'
        GROUP BY 1 ORDER BY 1
    """)
    return pd.DataFrame(cur.fetchall(), columns=["giorno", "iscritti"])


# ═══════════════════════════════════════════════════════════════
# RENDER PRINCIPALE
# ═══════════════════════════════════════════════════════════════

def render_pnev_pubblico_admin(conn):
    """Dashboard admin del percorso pubblico MAPS-CLEAR."""
    db.init_pnev_pubblico_db(conn)  # self-init idempotente

    st.title("🎧 MAPS-CLEAR · Percorso pubblico")
    st.caption("Iscritti dal sito pnev.it — 7 giorni per parlare chiaro")

    utenti = db.admin_lista_utenti(conn)

    if not utenti:
        st.info("Nessun iscritto ancora. Quando i primi pazienti si registreranno "
                "da pnev.it, li vedrai qui.")
        return

    colonne = ["id", "nome", "email", "eta", "mano", "iscritto_il",
               "orecchio", "test_li", "giorno", "stato",
               "sessioni_fatte", "delta_fluency_medio"]
    df = pd.DataFrame(utenti, columns=colonne)

    # ── Metriche generali ──────────────────────────────────────
    tot = len(df)
    attivi = int((df["stato"] == "attivo").sum())
    completati = int((df["stato"] == "completato").sum())
    con_sessioni = int((df["sessioni_fatte"] > 0).sum())
    delta_globale = df["delta_fluency_medio"].dropna()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Iscritti totali", tot)
    c2.metric("Percorsi attivi", attivi)
    c3.metric("Completati", f"{completati}",
              help=f"Tasso di completamento: {completati / tot * 100:.0f}%")
    c4.metric("Δ fluenza medio",
              f"{float(delta_globale.mean()):+.2f}" if len(delta_globale) else "—",
              help="Media dei delta (dopo − prima) di tutte le sessioni, scala 1-10")

    # ── Funnel ─────────────────────────────────────────────────
    with st.expander("📉 Funnel del percorso"):
        f_orecchio = int(df["orecchio"].notna().sum())
        passi = [
            ("Registrati", tot),
            ("Orecchio impostato", f_orecchio),
            ("Almeno 1 sessione", con_sessioni),
            ("Percorso completato", completati),
        ]
        for nome, valore in passi:
            pct = valore / tot * 100 if tot else 0
            st.write(f"**{nome}**: {valore} ({pct:.0f}%)")
            st.progress(min(pct / 100, 1.0))

    # ── Iscrizioni nel tempo ───────────────────────────────────
    df_isc = _iscrizioni_per_giorno(conn)
    if len(df_isc) > 1:
        st.markdown("#### 📈 Iscrizioni per giorno")
        st.bar_chart(df_isc.set_index("giorno")["iscritti"], height=180)

    st.divider()

    # ── Tabella iscritti ───────────────────────────────────────
    st.markdown("#### 👥 Iscritti")
    filtro_stato = st.multiselect("Filtra per stato",
                                  ["attivo", "completato", "abbandonato"],
                                  default=[])
    df_vista = df[df["stato"].isin(filtro_stato)] if filtro_stato else df

    df_show = df_vista.copy()
    df_show["orecchio"] = df_show["orecchio"].map({"R": "Destro", "L": "Sinistro"}).fillna("—")
    st.dataframe(
        df_show[["nome", "email", "eta", "orecchio", "test_li",
                 "giorno", "stato", "sessioni_fatte", "delta_fluency_medio"]],
        use_container_width=True, hide_index=True,
        column_config={
            "giorno": st.column_config.NumberColumn("Giorno", help="Giorno corrente del percorso (8 = finito)"),
            "sessioni_fatte": st.column_config.ProgressColumn(
                "Sessioni", min_value=0, max_value=7, format="%d/7"),
            "delta_fluency_medio": st.column_config.NumberColumn("Δ fluenza", format="%+.2f"),
            "test_li": st.column_config.NumberColumn("LI", help="Laterality Index dal test binaurale"),
        },
    )

    # ── Dettaglio paziente ─────────────────────────────────────
    st.divider()
    st.markdown("#### 🔍 Dettaglio iscritto")
    opzioni = {f"{r['nome']} — {r['email']}": r["id"]
               for _, r in df_vista.iterrows()}
    if not opzioni:
        return
    scelto = st.selectbox("Scegli un iscritto", list(opzioni.keys()))
    _dettaglio_utente(conn, opzioni[scelto])

    # ── Export CSV ─────────────────────────────────────────────
    st.divider()
    st.markdown("#### 📤 Export")
    col_a, col_b = st.columns(2)
    with col_a:
        st.download_button(
            "⬇️ Iscritti (CSV)",
            df.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
            file_name="maps_clear_iscritti.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with col_b:
        df_sess = _tutte_le_sessioni(conn)
        st.download_button(
            "⬇️ Tutte le sessioni (CSV)",
            df_sess.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
            file_name="maps_clear_sessioni.csv",
            mime="text/csv",
            use_container_width=True,
        )
    st.caption("CSV con separatore «;» e decimali con virgola: si aprono direttamente in Excel italiano.")


# ═══════════════════════════════════════════════════════════════
# DETTAGLIO SINGOLO UTENTE
# ═══════════════════════════════════════════════════════════════

def _dettaglio_utente(conn, utente_id):
    u = db.get_utente_by_id(conn, utente_id)
    if not u:
        st.warning("Utente non trovato.")
        return
    # id, nome, email, eta, mano, gdpr, creato_il, orecchio, li, dettaglio, giorno, stato
    (_, nome, email, eta, mano, _gdpr, creato_il,
     orecchio, test_li, test_dettaglio, giorno, stato) = u

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Età", eta or "—")
    c2.metric("Mano", (mano or "—").capitalize())
    c3.metric("Orecchio DAF", {"R": "Destro", "L": "Sinistro"}.get(orecchio, "—"))
    c4.metric("LI binaurale", f"{float(test_li):+.2f}" if test_li is not None else "—")

    st.caption(f"Iscritto il {creato_il.astimezone(TZ):%d/%m/%Y %H:%M} · "
               f"Stato: **{stato}** · Giorno corrente: **{giorno}**")

    if test_dettaglio:
        with st.expander("🎧 Dettaglio test binaurale"):
            det = test_dettaglio if isinstance(test_dettaglio, dict) else json.loads(test_dettaglio)
            st.json(det)

    # ── Sessioni ───────────────────────────────────────────────
    sessioni = db.get_sessioni(conn, utente_id)
    if not sessioni:
        st.info("Nessuna sessione salvata online per questo iscritto.")
    else:
        df_s = pd.DataFrame(sessioni, columns=[
            "id", "giorno", "data", "modalita", "delay_ms", "orecchio",
            "fluency_pre", "fluency_post", "comfort", "beneficio", "note", "durate"])

        st.markdown("**📈 Fluenza per sessione (prima → dopo)**")
        graf = df_s.set_index("giorno")[["fluency_pre", "fluency_post"]]
        graf.columns = ["Prima", "Dopo"]
        st.line_chart(graf, height=220)

        st.markdown("**📋 Sessioni**")
        df_tab = df_s.copy()
        df_tab["data"] = pd.to_datetime(df_tab["data"], utc=True).dt.tz_convert(TZ).dt.strftime("%d/%m %H:%M")
        df_tab["Δ"] = df_tab["fluency_post"] - df_tab["fluency_pre"]
        st.dataframe(
            df_tab[["giorno", "data", "modalita", "delay_ms",
                    "fluency_pre", "fluency_post", "Δ", "comfort", "beneficio", "note"]],
            use_container_width=True, hide_index=True,
        )

    # ── Questionari ────────────────────────────────────────────
    quest = db.get_questionari(conn, utente_id)
    if quest["pre"] or quest["post"]:
        with st.expander("📝 Questionari"):
            col_pre, col_post = st.columns(2)
            for col, chiave, titolo in ((col_pre, "pre", "Baseline (pre)"),
                                        (col_post, "post", "Finale (post)")):
                with col:
                    st.markdown(f"**{titolo}**")
                    if quest[chiave]:
                        risposte = quest[chiave][0]
                        if not isinstance(risposte, dict):
                            risposte = json.loads(risposte)
                        for k in sorted(risposte, key=lambda x: int(x[1:]) if x[1:].isdigit() else 0):
                            etichetta = ETICHETTE_BASELINE.get(k, k.upper())
                            st.write(f"{etichetta}: **{risposte[k]}**")
                    else:
                        st.caption("Non compilato")
