# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════╗
║  NSUCO — Northeastern State University College of Optometry          ║
║  Oculomotor Test (Maples) — Saccadi e Inseguimenti                   ║
║                                                                      ║
║  4 parametri standard, ciascuno su scala 1–5:                        ║
║    • Abilità (giri completati)                                       ║
║    • Precisione (mira)                                               ║
║    • Movimento della testa                                           ║
║    • Movimento del corpo                                             ║
║                                                                      ║
║  PASS SCORES (punteggio minimo per "superato") per età e sesso —     ║
║  Saccadi: tabella ufficiale Maples (Figura 4).                       ║
║  Inseguimenti: stessa struttura (da confermare con Figura 2).        ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import streamlit as st

PARAMETRI = ["Abilità", "Precisione", "Mov. testa", "Mov. corpo"]
CHIAVI = ["ab", "pr", "te", "co"]

# Descrizioni della scala 1–5 (per i tooltip)
SCALA = {
    "ab": ["1 — nessun tentativo / <1 giro", "2 — completa 2 giri",
           "3 — completa 3 giri", "4 — completa 4 giri", "5 — completa 5 giri"],
    "pr": ["1 — mira grossolanamente eccessiva/scarsa",
           "2 — mira ampiamente/moderatamente ecc./scarsa",
           "3 — leggero ma costante eccesso/scarsità",
           "4 — leggero intermittente eccesso/scarsità",
           "5 — nessun eccesso o scarsità di mira"],
    "te": ["1 — grossolano movimento testa", "2 — ampio/moderato",
           "3 — costante leggero", "4 — leggero intermittente",
           "5 — nessun movimento della testa"],
    "co": ["1 — grossolano movimento corpo", "2 — ampio/moderato",
           "3 — costante leggero", "4 — leggero intermittente",
           "5 — nessun movimento del corpo"],
}

# ── PASS SCORES SACCADI (Maples, Figura 4) ────────────────────────────
# età: {parametro: (min_M, min_F)}
_SACC = {
    5:  {"ab": (5, 5), "pr": (3, 3), "te": (2, 2), "co": (3, 4)},
    6:  {"ab": (5, 5), "pr": (3, 3), "te": (2, 3), "co": (3, 4)},
    7:  {"ab": (5, 5), "pr": (3, 3), "te": (3, 3), "co": (3, 4)},
    8:  {"ab": (5, 5), "pr": (3, 3), "te": (3, 3), "co": (4, 4)},
    9:  {"ab": (5, 5), "pr": (3, 3), "te": (3, 3), "co": (4, 4)},
    10: {"ab": (5, 5), "pr": (3, 3), "te": (3, 4), "co": (4, 5)},
    11: {"ab": (5, 5), "pr": (3, 3), "te": (3, 4), "co": (4, 5)},
    12: {"ab": (5, 5), "pr": (3, 3), "te": (3, 4), "co": (4, 5)},
    13: {"ab": (5, 5), "pr": (3, 3), "te": (3, 4), "co": (5, 5)},
    14: {"ab": (5, 5), "pr": (4, 3), "te": (3, 4), "co": (5, 5)},
}
# Inseguimenti: in attesa della tabella ufficiale (Figura 2) usiamo gli
# stessi criteri dei saccadi. Aggiornabile senza toccare il resto.
_PURS = _SACC

ETA_MIN, ETA_MAX = 5, 14


def _norma_eta(eta: int):
    return max(ETA_MIN, min(ETA_MAX, int(eta or 8)))


def pass_scores(eta: int, sesso: str, tipo: str = "saccadi") -> dict:
    """Ritorna {chiave: soglia} per età/sesso. sesso 'M'/'F'."""
    e = _norma_eta(eta)
    tab = _SACC if tipo == "saccadi" else _PURS
    idx = 1 if (sesso or "M").upper().startswith("F") else 0
    return {k: tab[e][k][idx] for k in CHIAVI}


def _blocco(titolo, prefix, eta, sesso, tipo, d, skey):
    st.markdown(f"#### {titolo}")
    soglie = pass_scores(eta, sesso, tipo)
    cols = st.columns(4)
    valori = {}
    n_pass = 0
    for i, k in enumerate(CHIAVI):
        with cols[i]:
            v = st.select_slider(
                PARAMETRI[i], options=[1, 2, 3, 4, 5],
                value=int(d.get(f"{prefix}_{k}", 3)),
                key=skey(f"{prefix}_{k}"),
                help="\n".join(SCALA[k]))
            valori[k] = v
            soglia = soglie[k]
            ok = v >= soglia
            n_pass += 1 if ok else 0
            st.caption(("🟢" if ok else "🔴") + f" min {soglia}")
    esito = "🟢 Nella norma" if n_pass == 4 else (
        "🟡 Borderline" if n_pass >= 2 else "🔴 Sotto norma")
    st.markdown(f"**Esito {titolo.lower()}:** {esito}  ({n_pass}/4 parametri ≥ soglia)")
    return valori, n_pass


def render_nsuco(skey, eta, sesso, stored: dict | None = None) -> dict:
    """Disegna il blocco NSUCO (saccadi + inseguimenti) e ritorna i dati.

    skey: funzione che genera una key unica (es. lambda c: _sk('d', c, pid)).
    Ritorna dict salvabile in sez_d.
    """
    d = stored or {}
    c0a, c0b = st.columns([1, 1])
    with c0a:
        st.caption(f"Norme per **{_norma_eta(eta)} anni** · sesso **{sesso or 'M'}** "
                   "(Maples). Ogni parametro 1–5.")
    sacc, ns_p = _blocco("Saccadi", "sac", eta, sesso, "saccadi", d, skey)
    purs, np_p = _blocco("Inseguimenti", "pur", eta, sesso, "inseguimenti", d, skey)

    out = {}
    for k in CHIAVI:
        out[f"sac_{k}"] = sacc[k]
        out[f"pur_{k}"] = purs[k]
    out["sacc_pass"] = ns_p
    out["purs_pass"] = np_p
    return out
