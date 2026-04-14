# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════╗
║  NPS COMPLETO — Valutazione Neuropsicologica                        ║
║  WISC-IV · WIPPSI-IV · Funzioni Esecutive · Test PSY               ║
║  Autore: The Organism Gestionale                                     ║
╚══════════════════════════════════════════════════════════════════════╝
"""
from __future__ import annotations
from typing import Optional
import streamlit as st
import json
import datetime
import math


# ══════════════════════════════════════════════════════════════════════
#  UTILITÀ COMUNI
# ══════════════════════════════════════════════════════════════════════

def _pct_da_z(z: float) -> float:
    t = 1 / (1 + 0.2316419 * abs(z))
    poly = t * (0.319381530 + t * (-0.356563782 + t * (1.781477937
           + t * (-1.821255978 + t * 1.330274429))))
    p = 1 - (1 / math.sqrt(2 * math.pi)) * math.exp(-0.5 * z * z) * poly
    return round((p if z >= 0 else 1 - p) * 100, 1)


def _classifica_ci(ci: float) -> tuple[str, str]:
    """Ritorna (classificazione, colore_hex)."""
    tabella = [
        (130, 999, "Molto superiore",    "#1a7f37"),
        (120, 129, "Superiore",          "#2ea44f"),
        (110, 119, "Medio-alto",         "#0969da"),
        (90,  109, "Nella media",        "#444444"),
        (80,   89, "Medio-basso",        "#9a6700"),
        (70,   79, "Limite",             "#cf222e"),
        (0,    69, "Estremamente basso", "#82071e"),
    ]
    for lo, hi, label, col in tabella:
        if lo <= ci <= hi:
            return label, col
    return "n.d.", "#888"


def _badge(label: str, valore, colore: str = "#0969da") -> None:
    st.markdown(
        f"<span style='background:{colore};color:#fff;padding:4px 12px;"
        f"border-radius:6px;font-weight:bold;font-size:1.05em'>"
        f"{label}: {valore}</span>",
        unsafe_allow_html=True
    )
    st.markdown("")


def _ci_da_scalati(scalati: list[float], media: float = 10.0, ds: float = 3.0) -> float:
    """Converte media punteggi scalati in indice composito (μ=100, σ=15)."""
    if not scalati:
        return 100.0
    m = sum(scalati) / len(scalati)
    return round(100 + (m - media) / ds * 15, 1)


def _salva_nps(conn, paziente_id: int, tipo: str, dati: dict) -> None:
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS nps_valutazioni (
                id BIGSERIAL PRIMARY KEY,
                paziente_id BIGINT NOT NULL,
                tipo TEXT NOT NULL,
                dati_json TEXT,
                data_valutazione DATE DEFAULT CURRENT_DATE,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        cur.execute(
            "INSERT INTO nps_valutazioni (paziente_id, tipo, dati_json, data_valutazione)"
            " VALUES (%s, %s, %s, %s)",
            (paziente_id, tipo,
             json.dumps(dati, ensure_ascii=False, default=str),
             datetime.date.today().isoformat())
        )
        conn.commit()
        st.success(f"✅ {tipo} salvato.")
    except Exception as e:
        st.error(f"Errore salvataggio: {e}")


def _carica_nps(conn, paziente_id: int, tipo: str) -> Optional[dict]:
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT dati_json FROM nps_valutazioni "
            "WHERE paziente_id=%s AND tipo=%s "
            "ORDER BY created_at DESC LIMIT 1",
            (paziente_id, tipo)
        )
        row = cur.fetchone()
        if row:
            raw = row[0] if not isinstance(row, dict) else row["dati_json"]
            return json.loads(raw)
    except Exception:
        pass
    return None


# ══════════════════════════════════════════════════════════════════════
#  WISC-IV  (bambini 6–16 anni)
# ══════════════════════════════════════════════════════════════════════

_WISC4_SUBTEST = {
    "ICV — Comprensione Verbale": {
        "chiave": "ICV",
        "principali": [
            ("Similitudini",      "sim"),
            ("Vocabolario",       "voc"),
            ("Comprensione",      "com"),
        ],
        "supplementari": [
            ("Informazioni",                  "inf"),
            ("Ragionamento con le parole",    "rap"),
        ],
    },
    "IRP — Ragionamento Percettivo": {
        "chiave": "IRP",
        "principali": [
            ("Disegno con cubi",        "dc"),
            ("Concetti per immagini",   "cpi"),
            ("Matrici",                 "mat"),
        ],
        "supplementari": [
            ("Completamento di figure", "cf"),
        ],
    },
    "IMT — Memoria di Lavoro": {
        "chiave": "IMT",
        "principali": [
            ("Memoria di cifre",               "mc"),
            ("Ragionamento lettere-numeri",    "rln"),
        ],
        "supplementari": [
            ("Aritmetica", "ar"),
        ],
    },
    "IVE — Velocità di Elaborazione": {
        "chiave": "IVE",
        "principali": [
            ("Cifrario",            "cif"),
            ("Ricerca di simboli",  "rs"),
        ],
        "supplementari": [
            ("Cancellazione", "can"),
        ],
    },
}

_WISC4_CLASSI_SCALATO = [
    (16, 19, "Molto superiore"),
    (13, 15, "Superiore"),
    (12, 12, "Medio-alto"),
    (8,  11, "Nella media"),
    (7,   7, "Medio-basso"),
    (4,   6, "Limite"),
    (1,   3, "Estremamente basso"),
]

def _classe_scalato(ps: int) -> str:
    for lo, hi, lbl in _WISC4_CLASSI_SCALATO:
        if lo <= ps <= hi:
            return lbl
    return "n.d."


def render_wisc4(conn, paziente_id: int) -> None:
    st.subheader("🧩 WISC-IV — Wechsler Intelligence Scale for Children (4ª ed.)")
    st.caption("Bambini 6;0–16;11 anni · Orsini & Pezzuti 2013")

    precedente = _carica_nps(conn, paziente_id, "WISC-IV")
    if precedente:
        with st.expander("📋 Ultima valutazione salvata"):
            st.json(precedente)

    dati_subtest: dict[str, int] = {}
    indici: dict[str, float] = {}

    for titolo_indice, cfg in _WISC4_SUBTEST.items():
        chiave_indice = cfg["chiave"]
        with st.expander(f"📊 {titolo_indice}", expanded=True):
            scalati_principali: list[float] = []
            n_col = len(cfg["principali"]) + len(cfg["supplementari"])
            cols = st.columns(max(n_col, 2))
            col_idx = 0

            for nome, chiave in cfg["principali"]:
                with cols[col_idx]:
                    v = st.number_input(nome, min_value=1, max_value=19,
                                        value=10, step=1,
                                        key=f"w4_{chiave_indice}_{chiave}")
                    dati_subtest[chiave] = int(v)
                    scalati_principali.append(float(v))
                    st.caption(_classe_scalato(int(v)))
                col_idx += 1

            for nome, chiave in cfg["supplementari"]:
                with cols[col_idx]:
                    v = st.number_input(f"🔸 {nome}", min_value=1,
                                        max_value=19, value=10, step=1,
                                        key=f"w4_{chiave_indice}_{chiave}")
                    dati_subtest[chiave] = int(v)
                    st.caption(f"Suppl. · {_classe_scalato(int(v))}")
                col_idx += 1

            ci = _ci_da_scalati(scalati_principali)
            indici[chiave_indice] = ci
            cl, col = _classifica_ci(ci)
            pct = _pct_da_z((ci - 100) / 15)
            _badge(f"{chiave_indice}", f"{ci:.0f}  ·  {cl}  ·  {pct:.0f}°pct", col)

    # QI Totale
    st.markdown("---")
    st.markdown("#### QI Totale (QIT)")
    qi = _ci_da_scalati(list(indici.values()), media=100.0, ds=15.0)
    # approx: media degli indici
    qi = round(sum(indici.values()) / len(indici), 1) if indici else 100.0
    cl, col = _classifica_ci(qi)
    pct = _pct_da_z((qi - 100) / 15)
    _badge("QI Totale", f"{qi:.0f}  ·  {cl}  ·  {pct:.0f}°pct", col)

    # Profilo grafico semplice
    st.markdown("**Profilo indici:**")
    for nome_i, val in indici.items():
        pct_bar = max(0, min(100, int((val - 55) / 90 * 100)))
        cl_i, col_i = _classifica_ci(val)
        st.markdown(
            f"`{nome_i}` &nbsp; "
            f"<span style='background:{col_i};color:#fff;padding:1px 8px;"
            f"border-radius:4px;font-size:.9em'>{val:.0f}</span> "
            f"{'█' * (pct_bar // 10)}{'░' * (10 - pct_bar // 10)} "
            f"<span style='color:#888;font-size:.85em'>{cl_i}</span>",
            unsafe_allow_html=True
        )

    st.markdown("---")
    note = st.text_area("Note cliniche WISC-IV", height=80, key="wisc4_note")

    if st.button("💾 Salva WISC-IV", type="primary"):
        _salva_nps(conn, paziente_id, "WISC-IV", {
            "subtest": dati_subtest,
            "indici": indici,
            "qi_totale": qi,
            "note": note,
            "data": datetime.date.today().isoformat(),
        })


# ══════════════════════════════════════════════════════════════════════
#  WIPPSI-IV  (placeholder — manuale in arrivo)
# ══════════════════════════════════════════════════════════════════════

def render_wippsi4(conn, paziente_id: int) -> None:
    st.subheader("🧸 WIPPSI-IV — Wechsler Preschool & Primary Scale of Intelligence (4ª ed.)")
    st.caption("Bambini 2;6–7;7 anni")
    st.info(
        "⏳ **Modulo in attesa del manuale.**\n\n"
        "Appena disponibile il manuale con le tabelle normative italiane, "
        "il modulo verrà completato con:\n"
        "- Indici: IVG (Verbale), IRL (Nonverbale), ILG (Linguaggio), "
        "IVS (Visuo-Spaziale), IVE (Velocità Elaborazione), QIT\n"
        "- Subtest per fascia 2;6–3;11 e 4;0–7;7\n"
        "- Normative italiane da tavole standardizzazione"
    )
    note = st.text_area("Note provvisorie", height=80, key="wippsi_note")
    if st.button("💾 Salva nota WIPPSI-IV"):
        _salva_nps(conn, paziente_id, "WIPPSI-IV-placeholder",
                   {"note": note, "data": datetime.date.today().isoformat()})


# ══════════════════════════════════════════════════════════════════════
#  FUNZIONI ESECUTIVE
# ══════════════════════════════════════════════════════════════════════

# ── Rey AVLT Bambini ────────────────────────────────────────────────

_REY_NORME_BAMBINI = {
    # (fascia_eta): (media_tot_I_V, ds_tot_I_V, media_richiamo, ds_richiamo)
    "5-6 aa":    (28.5, 7.1, 6.2, 2.8),
    "7-8 aa":    (36.2, 7.4, 8.1, 3.0),
    "9-10 aa":   (42.3, 7.8, 10.2, 3.1),
    "11-12 aa":  (47.1, 7.2, 11.5, 2.9),
    "13-14 aa":  (50.8, 7.0, 12.3, 2.8),
}

def render_rey_bambini(conn, paziente_id: int) -> None:
    st.subheader("📋 Rey AVLT — Bambini")
    st.caption("Lista di 15 parole, 5 prove di apprendimento + interferenza B + richiamo differito")

    fascia = st.selectbox("Fascia d'età", list(_REY_NORME_BAMBINI.keys()),
                          key="rey_b_fascia")
    st.markdown("##### Prove di apprendimento (Lista A — 15 parole max)")
    prove_labels = ["I", "II", "III", "IV", "V"]
    cols = st.columns(7)
    prove: list[int] = []
    for i, lbl in enumerate(prove_labels):
        with cols[i]:
            v = st.number_input(f"Prova {lbl}", min_value=0, max_value=15,
                                value=0, step=1, key=f"rey_b_p{i}")
            prove.append(int(v))
    with cols[5]:
        int_b = st.number_input("Lista B", min_value=0, max_value=15,
                                value=0, step=1, key="rey_b_intb")
    with cols[6]:
        richiamo = st.number_input("Richiamo", min_value=0, max_value=15,
                                   value=0, step=1, key="rey_b_rich")
    ric30 = st.number_input("Riconoscimento (30 item)", min_value=0,
                            max_value=30, value=0, step=1, key="rey_b_ric30")

    tot_I_V = sum(prove)
    curva = " → ".join(str(p) for p in prove)
    st.caption(f"Totale I–V = **{tot_I_V}** | Curva: {curva}")

    # classificazione
    m_tot, ds_tot, m_rich, ds_rich = _REY_NORME_BAMBINI[fascia]
    z_tot  = (tot_I_V - m_tot) / ds_tot if ds_tot else 0
    z_rich = (richiamo - m_rich) / ds_rich if ds_rich else 0
    pct_tot  = _pct_da_z(z_tot)
    pct_rich = _pct_da_z(z_rich)

    col1, col2 = st.columns(2)
    col1.metric("Totale I–V", tot_I_V,
                f"z={z_tot:.2f}  ·  {pct_tot:.0f}°pct")
    col2.metric("Richiamo differito", richiamo,
                f"z={z_rich:.2f}  ·  {pct_rich:.0f}°pct")

    if pct_tot < 5:
        st.error("🔴 Totale I–V sotto il 5° percentile — deficit memoria verbale")
    elif pct_tot < 16:
        st.warning("🟡 Totale I–V tra 5°–16° percentile — lieve difficoltà")
    else:
        st.success("🟢 Totale I–V nella norma")

    note = st.text_area("Note", height=68, key="rey_b_note")
    if st.button("💾 Salva Rey AVLT Bambini", key="salva_rey_b"):
        _salva_nps(conn, paziente_id, "Rey-AVLT-Bambini", {
            "fascia": fascia, "prove": prove, "interferenza_B": int(int_b),
            "richiamo": int(richiamo), "riconoscimento": int(ric30),
            "tot_I_V": tot_I_V, "z_tot": round(z_tot, 2),
            "z_rich": round(z_rich, 2), "pct_tot": pct_tot,
            "pct_rich": pct_rich, "note": note,
            "data": datetime.date.today().isoformat(),
        })


# ── TMT Bambini ────────────────────────────────────────────────────

# Norme semplificate per età (Reitan & Wolfson; norma italiana Riva et al.)
_TMT_NORME = {
    "6-7 aa":   {"A": (70, 25), "B": (None, None)},
    "8-9 aa":   {"A": (52, 20), "B": (160, 60)},
    "10-11 aa": {"A": (38, 14), "B": (110, 42)},
    "12-13 aa": {"A": (30, 11), "B":  (80, 32)},
    "14-15 aa": {"A": (26,  9), "B":  (65, 28)},
}

def render_tmt(conn, paziente_id: int) -> None:
    st.subheader("⏱️ Trail Making Test (TMT)")
    st.caption("Attenzione, flessibilità cognitiva, velocità di elaborazione")

    fascia = st.selectbox("Fascia d'età", list(_TMT_NORME.keys()), key="tmt_fascia")
    c1, c2 = st.columns(2)
    with c1:
        tmt_a = st.number_input("TMT-A (secondi)", min_value=0.0, max_value=600.0,
                                value=0.0, step=0.5, key="tmt_a_sec")
        err_a = st.number_input("Errori A", min_value=0, max_value=20,
                                value=0, step=1, key="tmt_err_a")
    with c2:
        tmt_b = st.number_input("TMT-B (secondi)", min_value=0.0, max_value=600.0,
                                value=0.0, step=0.5, key="tmt_b_sec")
        err_b = st.number_input("Errori B", min_value=0, max_value=20,
                                value=0, step=1, key="tmt_err_b")

    ratio = round(tmt_b / tmt_a, 2) if tmt_a > 0 else 0.0
    st.metric("Rapporto B/A", f"{ratio:.2f}",
              help="Norma attesa ≤ 3.0 (flessibilità cognitiva)")

    norme = _TMT_NORME[fascia]
    for parte, val_sec in [("A", tmt_a), ("B", tmt_b)]:
        m, ds = norme[parte]
        if m and val_sec > 0:
            z = (val_sec - m) / ds
            pct = _pct_da_z(-z)  # tempi alti = peggio
            flag = "🔴" if pct < 5 else ("🟡" if pct < 16 else "🟢")
            st.caption(f"TMT-{parte}: z={z:.2f} · {pct:.0f}°pct {flag}")

    note = st.text_area("Note TMT", height=68, key="tmt_note")
    if st.button("💾 Salva TMT", key="salva_tmt"):
        _salva_nps(conn, paziente_id, "TMT", {
            "fascia": fascia, "TMT_A": float(tmt_a), "TMT_B": float(tmt_b),
            "errori_A": int(err_a), "errori_B": int(err_b),
            "ratio_BA": ratio, "note": note,
            "data": datetime.date.today().isoformat(),
        })


# ── RAN (Denominazione Rapida Automatizzata) ─────────────────────────

# Norme italiane semplificate per classe (Brizzolara et al.)
# Norme RAN reali — Benso/UNIGE (tempo compensato in secondi, 50 stimoli)
# Fonte: Attribuzione punteggi.xls + standard.xls
_RAN_NORME = {
    # fascia: (media_tempo_comp_sec, ds)
    "Materna":         (86.62, 17.74),
    "1ª primaria":     (84.38, 20.13),
    "2ª primaria":     (76.80, 16.33),
    "4ª primaria":     (26.56,  4.71),
    # Nominazione Veloce UNIGE (30 stimoli, norme separate)
    "__nom_veloce__": {
        "Materna":    (45.87, 18.42),
        "1ª primaria": (32.06, 11.41),
        "2ª primaria": (18.51,  3.68),
        "4ª primaria": (13.87,  3.10),
    }
}

def render_ran(conn, paziente_id: int) -> None:
    st.subheader("⚡ RAN / Nominazione Veloce (Benso-UNIGE)")
    st.caption("Norme reali da Benso/UNIGE · Attribuzione punteggi.xls")

    versione = st.radio("Versione test", ["RAN (50 stimoli)", "Nominazione Veloce UNIGE (30 stimoli)"],
                        horizontal=True, key="ran_versione")

    if versione == "RAN (50 stimoli)":
        fasce = [k for k in _RAN_NORME if not k.startswith("__")]
    else:
        fasce = list(_RAN_NORME["__nom_veloce__"].keys())

    fascia = st.selectbox("Fascia scolastica", fasce, key="ran_fascia")

    st.markdown("#### Tempo compensato (sec)")
    st.caption("Tempo compensato = tempo grezzo + (errori × tempo_medio_per_stimolo)")

    c1, c2, c3 = st.columns(3)
    with c1:
        tempo = st.number_input("Tempo compensato (sec)", min_value=0.0,
                                max_value=300.0, value=0.0, step=0.5, key="ran_tempo")
    with c2:
        errori = st.number_input("Errori totali", min_value=0, max_value=30,
                                 value=0, step=1, key="ran_errori")
    with c3:
        tipo_stimolo = st.selectbox("Tipo stimolo", ["Colori", "Numeri", "Oggetti", "Lettere"],
                                    key="ran_tipo")

    if tempo > 0:
        if versione == "RAN (50 stimoli)":
            m, ds = _RAN_NORME.get(fascia, (80, 20))
        else:
            m, ds = _RAN_NORME["__nom_veloce__"].get(fascia, (40, 15))
        z = (tempo - m) / ds if ds else 0
        pct = _pct_da_z(-z)  # tempi alti = prestazione peggiore
        flag = "🔴" if pct < 5 else ("🟡" if pct < 16 else "🟢")
        col1, col2 = st.columns(2)
        col1.metric("Tempo compensato", f"{tempo:.1f}s")
        col2.metric("Classificazione", f"{pct:.0f}°pct {flag}")
        st.caption(f"Norma fascia {fascia}: M={m:.1f}s, DS={ds:.1f} | z={z:.2f}")
        if pct < 5:
            st.error("🔴 Prestazione deficitaria (<5° pct) — difficoltà accesso lessicale automatico")
        elif pct < 16:
            st.warning("🟡 Prestazione sotto la norma (5°–16° pct)")
        else:
            st.success("🟢 Nella norma")

    note = st.text_area("Note RAN", height=68, key="ran_note")
    if st.button("💾 Salva RAN", key="salva_ran"):
        _salva_nps(conn, paziente_id, "RAN", {
            "versione": versione, "fascia": fascia, "tipo_stimolo": tipo_stimolo,
            "tempo_comp": float(tempo), "errori": int(errori),
            "note": note, "data": datetime.date.today().isoformat(),
        })


# ── Switch di Calcolo (Benso) ────────────────────────────────────────

def render_switch_calcolo(conn, paziente_id: int) -> None:
    st.subheader("🔄 Switch di Calcolo (Benso)")
    st.caption("Flessibilità cognitiva: costo dello switch tra operazioni diverse")

    st.markdown("""
    **Procedura:** Serie A = operazioni dello stesso tipo (es. tutte addizioni).
    Serie B = operazioni alternate (addizioni e sottrazioni). Misura il tempo in secondi.
    """)
    c1, c2 = st.columns(2)
    with c1:
        tempo_a = st.number_input("Tempo Serie A (sec)", min_value=0.0,
                                  max_value=300.0, value=0.0, step=0.5,
                                  key="sw_tempo_a")
        err_a = st.number_input("Errori A", min_value=0, max_value=30,
                                value=0, step=1, key="sw_err_a")
    with c2:
        tempo_b = st.number_input("Tempo Serie B (sec)", min_value=0.0,
                                  max_value=300.0, value=0.0, step=0.5,
                                  key="sw_tempo_b")
        err_b = st.number_input("Errori B", min_value=0, max_value=30,
                                value=0, step=1, key="sw_err_b")

    switch_cost = round(tempo_b - tempo_a, 2) if tempo_a > 0 else 0.0

    # Norme reali Switch - I media (Benso/UNIGE)
    _SW_NORME = {
        "I media (Benso)": {"TcB": (276.5, 117.4), "diff_CB": (5.2, 72.7)},
    }

    classe = st.selectbox("Classe / Fascia normativa",
                          ["I media (Benso)", "Altra classe (inserisci manuale)"],
                          key="sw_classe")
    st.metric("Switch Cost (C-B)", f"{switch_cost:.1f}s",
              help="Costo della flessibilità cognitiva")

    if classe in _SW_NORME and tempo_b > 0:
        m_b, ds_b = _SW_NORME[classe]["TcB"]
        m_diff, ds_diff = _SW_NORME[classe]["diff_CB"]
        z_b    = (tempo_b - m_b) / ds_b if ds_b else 0
        z_diff = (switch_cost - m_diff) / ds_diff if ds_diff else 0
        pct_b    = _pct_da_z(-z_b)
        pct_diff = _pct_da_z(-z_diff) if switch_cost > m_diff else _pct_da_z(-z_diff)
        col1, col2 = st.columns(2)
        col1.caption(f"Velocità Foglio C: {pct_b:.0f}°pct (norma M={m_b:.0f}s, DS={ds_b:.0f})")
        col2.caption(f"Switch cost: z={z_diff:.2f}")
    note = st.text_area("Note Switch", height=68, key="sw_note")
    if st.button("💾 Salva Switch di Calcolo", key="salva_sw"):
        _salva_nps(conn, paziente_id, "Switch-Calcolo", {
            "classe": classe, "tempo_A": float(tempo_a), "tempo_B": float(tempo_b),
            "errori_A": int(err_a), "errori_B": int(err_b),
            "switch_cost": switch_cost, "note": note,
            "data": datetime.date.today().isoformat(),
        })


# ── Alpha Span ───────────────────────────────────────────────────────

def render_alpha_span(conn, paziente_id: int) -> None:
    st.subheader("🔤 Alpha Span — Memoria di Lavoro Verbale")
    st.caption("Sequenze di parole da riordinare in ordine alfabetico")

    st.markdown("""
    **Procedura:** Leggi ad alta voce sequenze di parole.
    Il paziente deve ripeterle in ordine alfabetico.
    Inizia da 2 parole, aumenta di 1 fino a fallimento in entrambi i tentativi per una lunghezza.
    """)

    spans = []
    for n in range(2, 8):
        st.markdown(f"**Lunghezza {n}**")
        c1, c2 = st.columns(2)
        with c1:
            t1 = st.selectbox(f"Tentativo 1 (span {n})", ["—", "✅ Corretto", "❌ Errore"],
                              key=f"as_{n}_t1")
        with c2:
            t2 = st.selectbox(f"Tentativo 2 (span {n})", ["—", "✅ Corretto", "❌ Errore"],
                              key=f"as_{n}_t2")
        spans.append({"span": n, "t1": t1, "t2": t2})

    # calcola span massimo (passa se almeno 1/2 corretti)
    span_max = 1
    for s in spans:
        if "Corretto" in s["t1"] or "Corretto" in s["t2"]:
            span_max = s["span"]
    st.metric("Alpha Span massimo", span_max,
              help="Norma adulti: 4–5; bambini 10aa: 3–4")

    note = st.text_area("Note Alpha Span", height=68, key="as_note")
    if st.button("💾 Salva Alpha Span", key="salva_as"):
        _salva_nps(conn, paziente_id, "Alpha-Span", {
            "span_max": span_max, "dettaglio": spans, "note": note,
            "data": datetime.date.today().isoformat(),
        })


# ── Updating ─────────────────────────────────────────────────────────

def render_updating(conn, paziente_id: int) -> None:
    st.subheader("🔃 Updating — Aggiornamento della Memoria di Lavoro")
    st.caption("Tenere in memoria solo gli ultimi N stimoli di una sequenza")

    st.markdown("""
    **Procedura:** Viene letta una lista di elementi (es. numeri o parole).
    Il paziente deve ricordare solo gli **ultimi N** della serie.
    """)

    n_da_ricordare = st.radio("N da ricordare", [3, 4, 5], horizontal=True,
                              key="upd_n")
    n_prove = st.number_input("Numero di prove", min_value=2, max_value=10,
                              value=5, step=1, key="upd_n_prove")

    corretti = st.number_input("Risposte corrette", min_value=0,
                               max_value=int(n_prove), value=0, step=1,
                               key="upd_corretti")
    accuratezza = round(corretti / n_prove * 100, 1) if n_prove > 0 else 0.0
    st.metric("Accuratezza", f"{accuratezza:.1f}%")

    if accuratezza >= 80:
        st.success("🟢 Prestazione adeguata")
    elif accuratezza >= 60:
        st.warning("🟡 Prestazione borderline")
    else:
        st.error("🔴 Difficoltà nel mantenimento e aggiornamento")

    note = st.text_area("Note Updating", height=68, key="upd_note")
    if st.button("💾 Salva Updating", key="salva_upd"):
        _salva_nps(conn, paziente_id, "Updating", {
            "n_da_ricordare": int(n_da_ricordare), "n_prove": int(n_prove),
            "corretti": int(corretti), "accuratezza": accuratezza,
            "note": note, "data": datetime.date.today().isoformat(),
        })


# ── Test di Cancellazione (Benso) ────────────────────────────────────

# Norme Cancellazione Benso — velocità pagina 2 (t/pt = sec per punto target)
# Fonte: Attribuzione punteggi.xls, Foglio1
_CANCELLAZIONE_NORME = {
    "Materna":  (1.3433, 0.2309),
    "Prima":    (1.2857, 0.3477),
    "Seconda":  (0.9471, 0.2233),
    "Terza":    (0.77,   0.12  ),
    "Quarta":   (0.6678, 0.1158),
    "I media":  (0.624,  0.130 ),
}


def render_cancellazione(conn, paziente_id: int) -> None:
    st.subheader("🎯 Test di Cancellazione (Benso)")
    st.caption("Attenzione selettiva visiva · Norme reali da Attribuzione punteggi.xls")

    st.markdown("""
    **Procedura (Benso):** 10 fogli con simboli/figure in righe.
    Il paziente cancella il simbolo bersaglio il più velocemente possibile.
    Calcola velocità: **t/pt = tempo (sec) / punti target presenti nel foglio**.
    """)

    fascia = st.selectbox("Fascia", list(_CANCELLAZIONE_NORME.keys()), key="can_fascia")
    pagina = st.selectbox("Pagina di riferimento", ["Pag 2", "Pag 3", "Pag 5", "Pag 7", "Pag 8", "Pag 10"],
                          key="can_pagina")

    c1, c2, c3 = st.columns(3)
    with c1:
        tempo = st.number_input("Tempo (sec)", min_value=0.0, max_value=600.0,
                                value=0.0, step=0.5, key="can_tempo")
    with c2:
        n_target = st.number_input("Target presenti nel foglio",
                                   min_value=1, max_value=200, value=50, step=1, key="can_ntarget")
        omissioni = st.number_input("Omissioni (target non cancellati)",
                                    min_value=0, max_value=200, value=0, step=1, key="can_omiss")
    with c3:
        errori = st.number_input("Falsi allarmi (non-target cancellati)",
                                 min_value=0, max_value=100, value=0, step=1, key="can_err")

    if tempo > 0 and n_target > 0:
        t_pt = tempo / n_target
        m, ds = _CANCELLAZIONE_NORME[fascia]
        z = (t_pt - m) / ds if ds else 0
        pct_vel = _pct_da_z(-z)  # t/pt alto = più lento = peggio
        flag = "🔴" if pct_vel < 5 else ("🟡" if pct_vel < 16 else "🟢")

        accuratezza = round((n_target - omissioni) / n_target * 100, 1)
        col1, col2, col3 = st.columns(3)
        col1.metric("t/pt (sec/target)", f"{t_pt:.3f}")
        col2.metric("Norma fascia", f"M={m:.3f}, DS={ds:.3f}")
        col3.metric("Velocità", f"{pct_vel:.0f}°pct {flag}")
        st.caption(f"z={z:.2f} | Accuratezza: {accuratezza:.1f}%")

        if pct_vel < 5:
            st.error("🔴 Velocità deficitaria (<5° pct)")
        elif pct_vel < 16:
            st.warning("🟡 Velocità sotto la norma (5°–16° pct)")
        else:
            st.success("🟢 Velocità nella norma")
    else:
        t_pt = 0.0
        accuratezza = 0.0

    note = st.text_area("Note Cancellazione", height=68, key="can_note")
    if st.button("💾 Salva Test Cancellazione", key="salva_can"):
        _salva_nps(conn, paziente_id, "Test-Cancellazione", {
            "fascia": fascia, "pagina": pagina,
            "tempo": float(tempo), "n_target": int(n_target),
            "omissioni": int(omissioni), "errori": int(errori),
            "t_pt": round(t_pt, 4), "accuratezza": accuratezza,
            "note": note, "data": datetime.date.today().isoformat(),
        })



# ── Five Point Test (Benso) ──────────────────────────────────────────

# Norme Five Point Test — Prima media, UNIGE (Benso)
# Fonte: PRIMA MEDIA (1) (1).xls / medie e ds di tutti i test
_FPT_NORME = {
    "I media (Benso)": {
        "tot_figure":  (47.4,  15.65),
        "tot_errori":  (0.62,   2.24),
        "tot_persev":  (3.98,   3.86),
        "prova1_fig":  (11.09,  4.21),
        "prova2_fig":  (11.95,  4.35),
        "prova3_fig":  (12.44,  4.41),
        "prova4_fig":  (11.93,  4.75),
    }
}


def render_five_point(conn, paziente_id: int) -> None:
    st.subheader("⭐ Five Point Test (Benso)")
    st.caption("Fluenza figurale, pianificazione, creatività · Norme I media UNIGE")

    st.markdown("""
    **Procedura:** 4 fogli con 40 punti ciascuno.
    Il paziente disegna il maggior numero possibile di figure connettendo i punti.
    **Conta:** figure uniche valide, errori (figure ripetute), perseverazioni.
    """)

    fascia = st.selectbox("Fascia normativa", list(_FPT_NORME.keys()), key="fpt_fascia")

    st.markdown("#### Punteggi per prova")
    prove_dati: dict[str, dict] = {}
    tot_fig = 0
    for i in range(1, 5):
        with st.expander(f"Prova {i}", expanded=i == 1):
            c1, c2, c3 = st.columns(3)
            fig  = c1.number_input(f"Figure (prova {i})", min_value=0, max_value=40,
                                   value=0, step=1, key=f"fpt_p{i}_fig")
            err  = c2.number_input(f"Errori",              min_value=0, max_value=20,
                                   value=0, step=1, key=f"fpt_p{i}_err")
            perv = c3.number_input(f"Perseverazioni",      min_value=0, max_value=20,
                                   value=0, step=1, key=f"fpt_p{i}_per")
            prove_dati[f"prova{i}"] = {"figure": int(fig), "errori": int(err),
                                        "perseverazioni": int(perv)}
            tot_fig += fig
            # classificazione figure per prova
            norme_prova = _FPT_NORME.get(fascia, {})
            key_p = f"prova{i}_fig"
            if key_p in norme_prova and fig > 0:
                m, ds = norme_prova[key_p]
                z = (fig - m) / ds
                pct = _pct_da_z(z)
                flag = "🔴" if pct < 5 else ("🟡" if pct < 16 else "🟢")
                st.caption(f"Figure prova {i}: {pct:.0f}°pct {flag} (norma M={m:.1f})")

    st.markdown("---")
    st.markdown("#### Totali")
    tot_err  = sum(v["errori"]         for v in prove_dati.values())
    tot_per  = sum(v["perseverazioni"] for v in prove_dati.values())

    col1, col2, col3 = st.columns(3)
    col1.metric("Totale figure", tot_fig)
    col2.metric("Totale errori", tot_err)
    col3.metric("Totale persev.", tot_per)

    norme = _FPT_NORME.get(fascia, {})
    if norme and tot_fig > 0:
        for label, chiave, val in [
            ("Figure", "tot_figure", tot_fig),
            ("Errori", "tot_errori", tot_err),
            ("Persev.", "tot_persev", tot_per),
        ]:
            if chiave in norme:
                m, ds = norme[chiave]
                z = (val - m) / ds if ds else 0
                # per figure: alto = meglio; per err/persev: basso = meglio
                pct = _pct_da_z(z) if chiave == "tot_figure" else _pct_da_z(-z)
                flag = "🔴" if pct < 5 else ("🟡" if pct < 16 else "🟢")
                st.caption(f"{label}: z={z:.2f}, {pct:.0f}°pct {flag} (norma M={m:.1f}, DS={ds:.1f})")

    note = st.text_area("Note Five Point Test", height=68, key="fpt_note")
    if st.button("💾 Salva Five Point Test", key="salva_fpt"):
        _salva_nps(conn, paziente_id, "Five-Point-Test", {
            "fascia": fascia, "prove": prove_dati,
            "tot_figure": int(tot_fig), "tot_errori": int(tot_err),
            "tot_persev": int(tot_per),
            "note": note, "data": datetime.date.today().isoformat(),
        })


# ── Fluenza Verbale ───────────────────────────────────────────────────

# Norme fluenza fonemica (F+A+S) e semantica — I media UNIGE
_FLUENZA_NORME = {
    "I media (Benso)": {
        "fonemica_totale":   (17.2, 6.0),   # F+A+S totale
        "semantica_totale":  (31.0, 8.7),   # catena semantica totale
    }
}


def render_fluenza_verbale(conn, paziente_id: int) -> None:
    st.subheader("🗣️ Fluenza Verbale (Fonemica e Semantica)")
    st.caption("Test di generazione di parole · Norme I media UNIGE/Benso")

    fascia = st.selectbox("Fascia normativa", list(_FLUENZA_NORME.keys()), key="fl_fascia")

    st.markdown("#### Fluenza Fonemica (1 minuto per lettera)")
    c1, c2, c3 = st.columns(3)
    f_F = c1.number_input("Parole con F", min_value=0, max_value=40, value=0, step=1, key="fl_F")
    f_A = c2.number_input("Parole con A", min_value=0, max_value=40, value=0, step=1, key="fl_A")
    f_S = c3.number_input("Parole con S", min_value=0, max_value=40, value=0, step=1, key="fl_S")
    tot_fon = f_F + f_A + f_S
    st.caption(f"Totale F+A+S = **{tot_fon}**")

    st.markdown("#### Fluenza Semantica (1 minuto per categoria)")
    c4, c5, c6 = st.columns(3)
    s_1 = c4.number_input("Categoria 1 (es. animali)", min_value=0, max_value=60, value=0, step=1, key="fl_s1")
    s_2 = c5.number_input("Categoria 2 (es. cibo)",    min_value=0, max_value=60, value=0, step=1, key="fl_s2")
    s_3 = c6.number_input("Categoria 3 (es. veicoli)", min_value=0, max_value=60, value=0, step=1, key="fl_s3")
    tot_sem = s_1 + s_2 + s_3
    st.caption(f"Totale semantica = **{tot_sem}**")

    norme = _FLUENZA_NORME.get(fascia, {})
    for label, chiave, val in [
        ("Fonemica (F+A+S)", "fonemica_totale",  tot_fon),
        ("Semantica",         "semantica_totale", tot_sem),
    ]:
        if chiave in norme and val > 0:
            m, ds = norme[chiave]
            z = (val - m) / ds if ds else 0
            pct = _pct_da_z(z)
            flag = "🔴" if pct < 5 else ("🟡" if pct < 16 else "🟢")
            st.caption(f"{label}: z={z:.2f}, {pct:.0f}°pct {flag} (M={m:.1f}, DS={ds:.1f})")

    note = st.text_area("Note Fluenza Verbale", height=68, key="fl_note")
    if st.button("💾 Salva Fluenza Verbale", key="salva_fl"):
        _salva_nps(conn, paziente_id, "Fluenza-Verbale", {
            "fascia": fascia,
            "fonemica": {"F": int(f_F), "A": int(f_A), "S": int(f_S), "totale": int(tot_fon)},
            "semantica": {"cat1": int(s_1), "cat2": int(s_2), "cat3": int(s_3), "totale": int(tot_sem)},
            "note": note, "data": datetime.date.today().isoformat(),
        })


# ── Numerazione 1→100 / 100→1 ────────────────────────────────────────

# Norme reali — I media UNIGE (Benso)
# Fonte: Numerazione sheet, Attribuzione punteggi.xls
_NUMERAZIONE_NORME = {
    "I media (Benso)": {
        "avanti":  (51.2, 7.94),   # media e DS tempo 1→100
        "indietro": (72.5, 17.9),  # media e DS tempo 100→1
        "diff":    (21.3, 15.6),   # differenza (indietro-avanti) = switch cost
    }
}


def render_numerazione(conn, paziente_id: int) -> None:
    st.subheader("🔢 Numerazione (1→100 / 100→1)")
    st.caption("Automatismo numerico e flessibilità · Norme I media UNIGE/Benso")

    fascia = st.selectbox("Fascia normativa", list(_NUMERAZIONE_NORME.keys()), key="num_fascia")

    c1, c2 = st.columns(2)
    with c1:
        t_av  = st.number_input("Tempo 1→100 (sec)", min_value=0.0, max_value=300.0,
                                value=0.0, step=0.5, key="num_av_t")
        err_av = st.number_input("Errori 1→100", min_value=0, max_value=20, value=0, step=1, key="num_av_e")
    with c2:
        t_ind  = st.number_input("Tempo 100→1 (sec)", min_value=0.0, max_value=600.0,
                                 value=0.0, step=0.5, key="num_ind_t")
        err_ind = st.number_input("Errori 100→1", min_value=0, max_value=20, value=0, step=1, key="num_ind_e")

    if t_av > 0 and t_ind > 0:
        diff = round(t_ind - t_av, 2)
        st.metric("Switch cost (100→1 meno 1→100)", f"{diff:.1f}s")
        norme = _NUMERAZIONE_NORME.get(fascia, {})
        for label, chiave, val in [
            ("1→100",  "avanti",  t_av),
            ("100→1",  "indietro", t_ind),
            ("Diff",   "diff",    diff),
        ]:
            if chiave in norme:
                m, ds = norme[chiave]
                z = (val - m) / ds if ds else 0
                pct = _pct_da_z(-z)  # tempi alti = peggio
                flag = "🔴" if pct < 5 else ("🟡" if pct < 16 else "🟢")
                st.caption(f"{label}: z={z:.2f}, {pct:.0f}°pct {flag} (norma M={m:.1f}s)")

    note = st.text_area("Note Numerazione", height=68, key="num_note")
    if st.button("💾 Salva Numerazione", key="salva_num"):
        _salva_nps(conn, paziente_id, "Numerazione", {
            "fascia": fascia,
            "avanti":   {"tempo": float(t_av),  "errori": int(err_av)},
            "indietro": {"tempo": float(t_ind), "errori": int(err_ind)},
            "switch_cost": diff if t_av > 0 and t_ind > 0 else None,
            "note": note, "data": datetime.date.today().isoformat(),
        })

def render_funzioni_esecutive(conn, paziente_id: int) -> None:
    """Contenitore per tutti i test di funzioni esecutive."""
    st.subheader("🧠 Funzioni Esecutive")

    test_fe = st.radio(
        "Seleziona test",
        ["Rey AVLT Bambini", "TMT", "RAN / Nominazione Veloce",
         "Five Point Test (Benso)", "Fluenza Verbale",
         "Switch di Calcolo", "Numerazione 1→100",
         "Alpha Span", "Updating", "Test di Cancellazione (Benso)"],
        horizontal=False, key="fe_test_sel"
    )
    st.markdown("---")

    if test_fe == "Rey AVLT Bambini":
        render_rey_bambini(conn, paziente_id)
    elif test_fe == "TMT":
        render_tmt(conn, paziente_id)
    elif test_fe == "RAN / Nominazione Veloce":
        render_ran(conn, paziente_id)
    elif test_fe == "Five Point Test (Benso)":
        render_five_point(conn, paziente_id)
    elif test_fe == "Fluenza Verbale":
        render_fluenza_verbale(conn, paziente_id)
    elif test_fe == "Switch di Calcolo":
        render_switch_calcolo(conn, paziente_id)
    elif test_fe == "Numerazione 1→100":
        render_numerazione(conn, paziente_id)
    elif test_fe == "Alpha Span":
        render_alpha_span(conn, paziente_id)
    elif test_fe == "Updating":
        render_updating(conn, paziente_id)
    elif test_fe == "Test di Cancellazione (Benso)":
        render_cancellazione(conn, paziente_id)


# ══════════════════════════════════════════════════════════════════════
#  TEST PSY
# ══════════════════════════════════════════════════════════════════════

# ── CBCL 6–18 (scale T-score) ────────────────────────────────────────

_CBCL618_SCALE = [
    ("Ansioso/Depresso",                "anx_dep",   65, 70),
    ("Ritiro/Depressione",              "withdrawn",  65, 70),
    ("Lamentele somatiche",             "somatic",    65, 70),
    ("Problemi sociali",                "social",     65, 70),
    ("Problemi di pensiero",            "thought",    65, 70),
    ("Problemi di attenzione",          "attention",  65, 70),
    ("Comportamento trasgressivo",      "rule_break", 65, 70),
    ("Comportamento aggressivo",        "aggress",    65, 70),
]

_CBCL618_COMP = [
    ("Internalizzante",  "int",  60, 64),
    ("Esternalizzante",  "ext",  60, 64),
    ("Totale problemi",  "tot",  60, 64),
]

def render_cbcl618(conn, paziente_id: int) -> None:
    st.subheader("📋 CBCL 6–18 (Achenbach)")
    st.caption("Scala compilata dal genitore/caregiver — inserisci i T-score dal protocollo cartaceo")

    st.markdown("#### Scale sindromiche (T-score)")
    st.caption("T < 65 = nella norma | T 65–69 = borderline | T ≥ 70 = clinicamente significativo")

    dati: dict[str, int] = {}
    col1, col2 = st.columns(2)
    for i, (nome, chiave, cut_border, cut_clin) in enumerate(_CBCL618_SCALE):
        with (col1 if i % 2 == 0 else col2):
            val = st.number_input(nome, min_value=50, max_value=100,
                                  value=50, step=1, key=f"cbcl618_{chiave}")
            dati[chiave] = int(val)
            if val >= cut_clin:
                st.error(f"⚠️ T={val} — clinicamente significativo")
            elif val >= cut_border:
                st.warning(f"T={val} — borderline")
            else:
                st.caption(f"T={val} — nella norma")

    st.markdown("#### Punteggi compositi")
    dati_comp: dict[str, int] = {}
    cols = st.columns(3)
    for i, (nome, chiave, cut_b, cut_c) in enumerate(_CBCL618_COMP):
        with cols[i]:
            val = st.number_input(nome, min_value=30, max_value=100,
                                  value=50, step=1, key=f"cbcl618_c_{chiave}")
            dati_comp[chiave] = int(val)
            if val >= cut_c:
                st.error(f"T={val} ≥ {cut_c}")
            elif val >= cut_b:
                st.warning(f"T={val} borderline")
            else:
                st.caption(f"T={val} ok")

    st.markdown("#### Competenze sociali")
    c1, c2, c3 = st.columns(3)
    attivita  = c1.number_input("Scala Attività",  min_value=0, max_value=100, value=50, step=1, key="cbcl618_att")
    sociale   = c2.number_input("Scala Sociale",   min_value=0, max_value=100, value=50, step=1, key="cbcl618_soc")
    scolastico = c3.number_input("Scala Scolastica", min_value=0, max_value=100, value=50, step=1, key="cbcl618_sco")

    note = st.text_area("Osservazioni cliniche CBCL 6-18", height=80, key="cbcl618_note")
    if st.button("💾 Salva CBCL 6–18", type="primary", key="salva_cbcl618"):
        _salva_nps(conn, paziente_id, "CBCL-618", {
            "scale_sindromiche": dati,
            "compositi": dati_comp,
            "competenze": {"attivita": int(attivita), "sociale": int(sociale),
                           "scolastico": int(scolastico)},
            "note": note,
            "data": datetime.date.today().isoformat(),
        })


# ── CBCL 1½–5 ────────────────────────────────────────────────────────

_CBCL15_SCALE = [
    ("Reattività emotiva",         "emot_react",  65, 70),
    ("Ansioso/Depresso",           "anx_dep",     65, 70),
    ("Lamentele somatiche",        "somatic",     65, 70),
    ("Ritiro",                     "withdrawn",   65, 70),
    ("Problemi del sonno",         "sleep",       65, 70),
    ("Problemi dell'attenzione",   "attention",   65, 70),
    ("Comportamento aggressivo",   "aggress",     65, 70),
]

def render_cbcl15(conn, paziente_id: int) -> None:
    st.subheader("📋 CBCL 1½–5 (Achenbach)")
    st.caption("Per bambini 18 mesi–5 anni · T-score dal protocollo cartaceo")

    dati: dict[str, int] = {}
    col1, col2 = st.columns(2)
    for i, (nome, chiave, cut_b, cut_c) in enumerate(_CBCL15_SCALE):
        with (col1 if i % 2 == 0 else col2):
            val = st.number_input(nome, min_value=50, max_value=100,
                                  value=50, step=1, key=f"cbcl15_{chiave}")
            dati[chiave] = int(val)
            if val >= cut_c:
                st.error(f"T={val} — clinicamente significativo")
            elif val >= cut_b:
                st.warning(f"T={val} — borderline")
            else:
                st.caption(f"T={val} — ok")

    st.markdown("#### Compositi")
    c1, c2, c3 = st.columns(3)
    int_t = c1.number_input("Internalizzante", min_value=30, max_value=100,
                             value=50, step=1, key="cbcl15_int")
    ext_t = c2.number_input("Esternalizzante", min_value=30, max_value=100,
                             value=50, step=1, key="cbcl15_ext")
    tot_t = c3.number_input("Totale problemi", min_value=30, max_value=100,
                             value=50, step=1, key="cbcl15_tot")

    note = st.text_area("Note CBCL 1½-5", height=68, key="cbcl15_note")
    if st.button("💾 Salva CBCL 1½–5", type="primary", key="salva_cbcl15"):
        _salva_nps(conn, paziente_id, "CBCL-15", {
            "scale": dati,
            "compositi": {"int": int(int_t), "ext": int(ext_t), "tot": int(tot_t)},
            "note": note,
            "data": datetime.date.today().isoformat(),
        })


# ── MOAS (Modified Overt Aggression Scale) ───────────────────────────

_MOAS_DOMINI = [
    ("Aggressività verbale",            "AV", 1,
     ["0 = Nessuna", "1 = Grida irosamente, impreca",
      "2 = Insulta verbalmente gli altri",
      "3 = Minacce esplicite di violenza", "4 = Minacce di panico"]),
    ("Aggressività contro oggetti",     "AO", 2,
     ["0 = Nessuna", "1 = Sbatte porte, strappa abiti",
      "2 = Rompe oggetti, frantuma finestre",
      "3 = Incendia oggetti, butta cibo addosso", "4 = Danni gravi e dispendiosi"]),
    ("Auto-aggressività",               "AA", 3,
     ["0 = Nessuna", "1 = Si graffia, si pizzica (senza danno)",
      "2 = Si colpisce, si morde (senza lesioni gravi)",
      "3 = Si infligge lievi ferite / lividi", "4 = Lesioni gravi"]),
    ("Aggressività eterodiretta",       "AE", 4,
     ["0 = Nessuna", "1 = Gesti minacciosi, spinge / afferra vesti",
      "2 = Colpisce, calcia (senza lesioni)",
      "3 = Attacca causando lievi lesioni", "4 = Attacca causando lesioni gravi"]),
]

def render_moas(conn, paziente_id: int) -> None:
    st.subheader("⚡ MOAS — Modified Overt Aggression Scale")
    st.caption("Valutazione comportamento aggressivo osservato")

    punteggi: dict[str, int] = {}
    for nome, sigla, peso, descrizioni in _MOAS_DOMINI:
        with st.expander(f"{nome} (peso ×{peso})", expanded=True):
            val = st.radio(
                f"Livello {sigla}",
                options=list(range(5)),
                format_func=lambda x, d=descrizioni: d[x],
                horizontal=False, key=f"moas_{sigla}"
            )
            punteggi[sigla] = int(val)
            st.caption(f"Contributo al totale: {val} × {peso} = **{val * peso}**")

    score_pesato = sum(
        punteggi[s] * p
        for _, s, p, _ in _MOAS_DOMINI
    )
    st.markdown("---")
    col1, col2 = st.columns(2)
    col1.metric("Score MOAS (pesato)", score_pesato)
    if score_pesato == 0:
        col2.success("🟢 Nessuna aggressività")
    elif score_pesato <= 4:
        col2.warning("🟡 Aggressività lieve")
    elif score_pesato <= 8:
        col2.error("🟠 Aggressività moderata")
    else:
        col2.error("🔴 Aggressività grave")

    note = st.text_area("Note MOAS", height=68, key="moas_note")
    if st.button("💾 Salva MOAS", type="primary", key="salva_moas"):
        _salva_nps(conn, paziente_id, "MOAS", {
            "punteggi_grezzi": punteggi,
            "score_pesato": score_pesato,
            "note": note,
            "data": datetime.date.today().isoformat(),
        })


# ── Leiter-R ─────────────────────────────────────────────────────────

_LEITER_VR = [
    ("Figura Sfondo",          "fs"),
    ("Completamento Forme",    "cf"),
    ("Analogie Sequenziali",   "as_"),
    ("Ripetizione Disegni",    "rd"),
    ("Diagramma a Carte",      "dc"),
    ("Ripetizione Figure",     "rf"),
    ("Rotazione Mentale",      "rm"),
]
_LEITER_AM = [
    ("Memoria Associata",       "ma"),
    ("Memoria di Numeri",       "mn"),
    ("Memoria Sequenziale",     "ms"),
    ("Riconoscimento",          "ric"),
    ("Attenzione Sostenuta",    "att"),
    ("Memoria Spaziale",        "msp"),
]

def render_leiter(conn, paziente_id: int) -> None:
    st.subheader("🔵 Leiter-R — Intelligence Non Verbale")
    st.caption("Bambini/adolescenti 2–21 aa · Nessun requisito linguistico")

    tab_vr, tab_am = st.tabs(["VR — Visualizzazione e Ragionamento",
                               "AM — Attenzione e Memoria"])

    scalati_vr: list[float] = []
    scalati_am: list[float] = []

    with tab_vr:
        st.caption("Punteggi scalati (media 10, DS 3)")
        cols = st.columns(len(_LEITER_VR))
        for i, (nome, chiave) in enumerate(_LEITER_VR):
            with cols[i]:
                v = st.number_input(nome, min_value=1, max_value=19, value=10,
                                    step=1, key=f"leiter_vr_{chiave}")
                scalati_vr.append(float(v))
        ci_vr = _ci_da_scalati(scalati_vr)
        cl, col = _classifica_ci(ci_vr)
        _badge("QI VR", f"{ci_vr:.0f} — {cl}", col)

    with tab_am:
        st.caption("Punteggi scalati (media 10, DS 3)")
        cols = st.columns(len(_LEITER_AM))
        for i, (nome, chiave) in enumerate(_LEITER_AM):
            with cols[i]:
                v = st.number_input(nome, min_value=1, max_value=19, value=10,
                                    step=1, key=f"leiter_am_{chiave}")
                scalati_am.append(float(v))
        ci_am = _ci_da_scalati(scalati_am)
        cl, col = _classifica_ci(ci_am)
        _badge("Indice AM", f"{ci_am:.0f} — {cl}", col)

    note = st.text_area("Note Leiter-R", height=68, key="leiter_note")
    if st.button("💾 Salva Leiter-R", type="primary", key="salva_leiter"):
        _salva_nps(conn, paziente_id, "Leiter-R", {
            "scalati_VR": scalati_vr, "CI_VR": ci_vr,
            "scalati_AM": scalati_am, "CI_AM": ci_am,
            "note": note, "data": datetime.date.today().isoformat(),
        })


# ── K-SADS (screening domini) ────────────────────────────────────────

_KSADS_DOMINI = [
    "Depressione maggiore",
    "Distimia",
    "Mania / Ipomania",
    "Disturbo Bipolare",
    "Fobia specifica",
    "Fobia sociale",
    "Disturbo di panico",
    "Agorafobia",
    "DOC (Ossessioni/Compulsioni)",
    "PTSD",
    "ADHD — Inattenzione",
    "ADHD — Iperattività/Impulsività",
    "Disturbo oppositivo provocatorio",
    "Disturbo della condotta",
    "Anoressia nervosa",
    "Bulimia nervosa",
    "Tic / Tourette",
    "Enuresi / Encopresi",
    "Disturbo da uso di sostanze",
]

_KSADS_RATING = {
    0: "0 — Nessuna informazione",
    1: "1 — Assente",
    2: "2 — Sottosoglia",
    3: "3 — Presente (soglia diagnostica)",
}

def render_ksads(conn, paziente_id: int) -> None:
    st.subheader("🔍 K-SADS — Screening Diagnostico Psicopatologico")
    st.caption("Intervista semi-strutturata · Per clinici formati · 6–18 anni")
    st.info("Inserisci i rating per ciascun dominio dopo la somministrazione dell'intervista.")

    dati: dict[str, int] = {}
    col1, col2 = st.columns(2)
    presenti: list[str] = []
    for i, dominio in enumerate(_KSADS_DOMINI):
        with (col1 if i % 2 == 0 else col2):
            val = st.selectbox(dominio, options=[0, 1, 2, 3],
                               format_func=lambda x: _KSADS_RATING[x],
                               key=f"ksads_{i}")
            dati[dominio] = int(val)
            if val == 3:
                presenti.append(dominio)

    if presenti:
        st.markdown("---")
        st.markdown("**Diagnosi presenti (rating = 3):**")
        for d in presenti:
            st.error(f"⚠️ {d}")

    note = st.text_area("Note K-SADS", height=80, key="ksads_note")
    if st.button("💾 Salva K-SADS", type="primary", key="salva_ksads"):
        _salva_nps(conn, paziente_id, "K-SADS", {
            "domini": dati, "diagnosi_presenti": presenti,
            "note": note, "data": datetime.date.today().isoformat(),
        })


# ── MMPI-A (scale cliniche T-score) ──────────────────────────────────

_MMPLA_SCALE = [
    ("Ipocondria (Hs)",           "hs"),
    ("Depressione (D)",           "d"),
    ("Isteria (Hy)",              "hy"),
    ("Deviazione psicopatica (Pd)", "pd"),
    ("Mascolinità-Femminilità (Mf)", "mf"),
    ("Paranoia (Pa)",             "pa"),
    ("Psicastenia (Pt)",          "pt"),
    ("Schizofrenia (Sc)",         "sc"),
    ("Ipomania (Ma)",             "ma"),
    ("Introversione sociale (Si)", "si"),
]

_MMPLA_VALIDITA = [
    ("? (Non risponde)", "q"),
    ("L (Lie)",          "l"),
    ("F (Infrequenza)",  "f"),
    ("K (Correzione)",   "k"),
]

def render_mmpia(conn, paziente_id: int) -> None:
    st.subheader("📊 MMPI-A — Inventario Multifasico di Personalità (Adolescenti)")
    st.caption("14–18 anni · 478 item · T-score dal software di scoring ASEBA")

    st.markdown("#### Scale di validità (T-score)")
    val_dati: dict[str, int] = {}
    cols = st.columns(4)
    for i, (nome, chiave) in enumerate(_MMPLA_VALIDITA):
        with cols[i]:
            v = st.number_input(nome, min_value=30, max_value=120, value=50,
                                step=1, key=f"mmpia_v_{chiave}")
            val_dati[chiave] = int(v)

    st.markdown("#### Scale cliniche (T-score)")
    st.caption("T ≥ 65 = elevazione clinicamente significativa")
    clin_dati: dict[str, int] = {}
    col1, col2 = st.columns(2)
    for i, (nome, chiave) in enumerate(_MMPLA_SCALE):
        with (col1 if i % 2 == 0 else col2):
            v = st.number_input(nome, min_value=30, max_value=120, value=50,
                                step=1, key=f"mmpia_c_{chiave}")
            clin_dati[chiave] = int(v)
            if v >= 65:
                st.error(f"T={v} — elevazione significativa")
            elif v >= 60:
                st.warning(f"T={v} — lieve elevazione")

    note = st.text_area("Note MMPI-A", height=80, key="mmpia_note")
    if st.button("💾 Salva MMPI-A", type="primary", key="salva_mmpia"):
        _salva_nps(conn, paziente_id, "MMPI-A", {
            "scale_validita": val_dati, "scale_cliniche": clin_dati,
            "note": note, "data": datetime.date.today().isoformat(),
        })


# ── BVSC placeholder ──────────────────────────────────────────────────

def render_bvsc(conn, paziente_id: int) -> None:
    st.subheader("🔬 BVSC — Batteria Valutazione Sindromi Cliniche")
    st.info("Mandami il nome completo del test e il manuale per implementare il modulo completo.")
    note = st.text_area("Note provvisorie BVSC", height=80, key="bvsc_note")
    if st.button("💾 Salva nota BVSC"):
        _salva_nps(conn, paziente_id, "BVSC-placeholder",
                   {"note": note, "data": datetime.date.today().isoformat()})


def render_test_psy(conn, paziente_id: int) -> None:
    """Contenitore per i test psicologici."""
    st.subheader("🧬 Test Psicologici")
    test_psy = st.radio(
        "Seleziona test",
        ["CBCL 6–18", "CBCL 1½–5", "MOAS", "K-SADS",
         "Leiter-R", "MMPI-A", "BVSC"],
        horizontal=False, key="psy_test_sel"
    )
    st.markdown("---")
    if test_psy == "CBCL 6–18":
        render_cbcl618(conn, paziente_id)
    elif test_psy == "CBCL 1½–5":
        render_cbcl15(conn, paziente_id)
    elif test_psy == "MOAS":
        render_moas(conn, paziente_id)
    elif test_psy == "K-SADS":
        render_ksads(conn, paziente_id)
    elif test_psy == "Leiter-R":
        render_leiter(conn, paziente_id)
    elif test_psy == "MMPI-A":
        render_mmpia(conn, paziente_id)
    elif test_psy == "BVSC":
        render_bvsc(conn, paziente_id)


# ══════════════════════════════════════════════════════════════════════
#  ENTRY POINT PRINCIPALE
# ══════════════════════════════════════════════════════════════════════

def render_nps_completo(conn, paziente_id: int) -> None:
    """
    Entry point. Chiama da app_main_router.py:
        from .ui_nps_completo import render_nps_completo
        render_nps_completo(conn, paziente_id)
    """
    st.title("🧠 Valutazione Neuropsicologica Completa")
    st.caption(f"Paziente ID: {paziente_id}")

    area = st.radio(
        "Area",
        ["WISC-IV (6–16 aa)", "WIPPSI-IV (2;6–7;7 aa)",
         "Funzioni Esecutive", "Test PSY"],
        horizontal=True, key="nps_area_sel"
    )
    st.markdown("---")

    if area == "WISC-IV (6–16 aa)":
        render_wisc4(conn, paziente_id)
    elif area == "WIPPSI-IV (2;6–7;7 aa)":
        render_wippsi4(conn, paziente_id)
    elif area == "Funzioni Esecutive":
        render_funzioni_esecutive(conn, paziente_id)
    elif area == "Test PSY":
        render_test_psy(conn, paziente_id)
