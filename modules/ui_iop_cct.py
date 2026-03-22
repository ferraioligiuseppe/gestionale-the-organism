# -*- coding: utf-8 -*-
"""
Modulo: IOP Corretta – Relazione Pressione / Spessore Corneale
Gestionale The Organism – PNEV

Formula di correzione: Ehlers (1975) modificata, usata in pratica clinica:
  IOPc = IOP + k * (CCT_ref - CCT) / 10
  dove k ≈ 0.071 mmHg/µm (Ehlers) oppure
  tabella di Dresdner lookup (più precisa per range estremi).

Classi di rischio glaucoma basate su IOPc (linee guida EGS 2020):
  < 12         : Bassa (possibile ipotonia)
  12 – 17.9    : Normale
  18 – 21.9    : Borderline
  22 – 29.9    : Elevata – monitoraggio
  ≥ 30         : Molto elevata – approfondimento urgente
"""

import math
import pandas as pd
import streamlit as st

# ── Riferimento CCT standard ─────────────────────────────────────────────
CCT_REF = 545  # µm — media popolazione (Ehlers)

# ── Tabella di correzione Dresdner (lookup discreta) ─────────────────────
# Correzione IOP (da sommare) in base al CCT misurato
# Fonte: Dresdner Korrekturtabelle, versione semplificata
DRESDNER_TABLE = [
    (395, +5.0), (405, +4.5), (415, +4.0), (425, +3.5),
    (435, +3.0), (445, +2.5), (455, +2.0), (465, +1.5),
    (475, +1.0), (485, +0.5), (495, +0.5),
    (505,  0.0), (515,  0.0), (525,  0.0), (535,  0.0),
    (545,  0.0), (555,  0.0), (565, -0.5),
    (575, -0.5), (585, -1.0), (595, -1.0), (605, -1.5),
    (615, -1.5), (625, -2.0), (635, -2.5), (645, -3.0),
    (655, -3.5), (665, -4.0), (675, -4.5), (685, -5.0),
    (695, -5.5),
]

# ── Classificazione rischio ───────────────────────────────────────────────
def classifica_rischio(iopc: float) -> tuple[str, str]:
    """Ritorna (label, colore_streamlit)."""
    if iopc < 12:
        return "Bassa – possibile ipotonia", "🔵"
    elif iopc < 18:
        return "Normale", "🟢"
    elif iopc < 22:
        return "Borderline – monitoraggio", "🟡"
    elif iopc < 30:
        return "Elevata – approfondimento", "🟠"
    else:
        return "Molto elevata – urgente", "🔴"


def corr_ehlers(iop: float, cct: float) -> float:
    """Correzione Ehlers lineare: 0.071 mmHg per µm."""
    return round(iop + 0.071 * (CCT_REF - cct), 2)


def corr_dresdner(iop: float, cct: float) -> float:
    """Correzione con tabella Dresdner (lookup + interpolazione lineare)."""
    cct_vals = [r[0] for r in DRESDNER_TABLE]
    cor_vals = [r[1] for r in DRESDNER_TABLE]
    # Clamp ai bordi
    if cct <= cct_vals[0]:
        delta = cor_vals[0]
    elif cct >= cct_vals[-1]:
        delta = cor_vals[-1]
    else:
        # Interpolazione lineare tra due punti vicini
        for i in range(len(cct_vals) - 1):
            if cct_vals[i] <= cct <= cct_vals[i+1]:
                t = (cct - cct_vals[i]) / (cct_vals[i+1] - cct_vals[i])
                delta = cor_vals[i] + t * (cor_vals[i+1] - cor_vals[i])
                break
        else:
            delta = 0.0
    return round(iop + delta, 2)


# ── Widget inline (dentro il form della valutazione visiva) ─────────────
def ui_iop_cct_inline(
    tono_od: float,
    tono_os: float,
    pachim_od: float,
    pachim_os: float,
) -> dict:
    """
    Mostra il calcolo IOP corretta direttamente dentro il form.
    Riceve i valori già letti dal form (IOP e CCT).
    Ritorna dict con i valori calcolati per eventuale salvataggio.
    """
    st.markdown("### 👁️ IOP Corretta per Spessore Corneale")

    formula = st.selectbox(
        "Formula di correzione",
        ["Dresdner (tabella lookup)", "Ehlers lineare (0.071 mmHg/µm)"],
        key="iop_formula",
        help="Dresdner è più accurata per CCT estremi; Ehlers è la formula lineare classica."
    )

    use_dresdner = formula.startswith("Dresdner")

    # Calcolo
    if use_dresdner:
        iopc_od = corr_dresdner(tono_od, pachim_od)
        iopc_os = corr_dresdner(tono_os, pachim_os)
    else:
        iopc_od = corr_ehlers(tono_od, pachim_od)
        iopc_os = corr_ehlers(tono_os, pachim_os)

    delta_od = round(iopc_od - tono_od, 2)
    delta_os = round(iopc_os - tono_os, 2)

    label_od, icon_od = classifica_rischio(iopc_od)
    label_os, icon_os = classifica_rischio(iopc_os)

    # Display
    col_od, col_os = st.columns(2)

    with col_od:
        st.markdown("**OD – Occhio Destro**")
        m1, m2, m3 = st.columns(3)
        m1.metric("IOP misurata", f"{tono_od:.1f} mmHg")
        m2.metric("CCT", f"{pachim_od:.0f} µm")
        m3.metric("IOPc corretta", f"{iopc_od:.1f} mmHg",
                  delta=f"{delta_od:+.1f} mmHg",
                  delta_color="inverse")
        st.markdown(f"**Rischio:** {icon_od} {label_od}")

    with col_os:
        st.markdown("**OS – Occhio Sinistro**")
        m4, m5, m6 = st.columns(3)
        m4.metric("IOP misurata", f"{tono_os:.1f} mmHg")
        m5.metric("CCT", f"{pachim_os:.0f} µm")
        m6.metric("IOPc corretta", f"{iopc_os:.1f} mmHg",
                  delta=f"{delta_os:+.1f} mmHg",
                  delta_color="inverse")
        st.markdown(f"**Rischio:** {icon_os} {label_os}")

    # Alert se rischio elevato
    max_iopc = max(iopc_od, iopc_os)
    if max_iopc >= 30:
        st.error(f"⚠️ IOPc molto elevata ({max_iopc:.1f} mmHg) — approfondimento urgente consigliato.")
    elif max_iopc >= 22:
        st.warning(f"⚠️ IOPc elevata ({max_iopc:.1f} mmHg) — monitoraggio ravvicinato consigliato.")
    elif max_iopc >= 18:
        st.info(f"ℹ️ IOPc borderline ({max_iopc:.1f} mmHg) — rivalutare periodicamente.")

    # Nota CCT
    if pachim_od < 480 or pachim_os < 480:
        st.warning("Cornea sottile (CCT < 480 µm): la IOP misurata sottostima la pressione reale.")
    elif pachim_od > 610 or pachim_os > 610:
        st.info("Cornea spessa (CCT > 610 µm): la IOP misurata sovrastima la pressione reale.")

    return {
        "iopc_od": iopc_od,
        "iopc_os": iopc_os,
        "delta_od": delta_od,
        "delta_os": delta_os,
        "formula": "dresdner" if use_dresdner else "ehlers",
        "rischio_od": label_od,
        "rischio_os": label_os,
    }


# ── Storico IOP nel tempo (fuori dal form) ───────────────────────────────
def ui_iop_storico(rows: list, paz_label: str = "") -> None:
    """
    Mostra il grafico storico IOP (misurata e corretta) per il paziente.
    `rows` è la lista di record Valutazioni_Visive già fetchati.
    """
    st.markdown("### 📈 Andamento IOP nel tempo")

    if not rows:
        st.info("Nessuna valutazione disponibile per lo storico.")
        return

    # Raccoglie i dati dalle valutazioni esistenti
    storico = []
    for r in rows:
        try:
            data   = r["Data_Valutazione"] or ""
            iop_od = r["Tonometria_OD"]
            iop_os = r["Tonometria_OS"]
            # Tenta di leggere anche la pachimetria se salvata
            cct_od = r.get("Pachimetria_OD") or r.get("pachimetria_od") or 545
            cct_os = r.get("Pachimetria_OS") or r.get("pachimetria_os") or 545
            if iop_od is None and iop_os is None:
                continue
            iopc_od = corr_dresdner(float(iop_od or 0), float(cct_od))
            iopc_os = corr_dresdner(float(iop_os or 0), float(cct_os))
            storico.append({
                "Data": data,
                "IOP OD (mmHg)": float(iop_od or 0),
                "IOP OS (mmHg)": float(iop_os or 0),
                "IOPc OD (mmHg)": iopc_od,
                "IOPc OS (mmHg)": iopc_os,
            })
        except Exception:
            continue

    if not storico:
        st.info("Dati IOP insufficienti per lo storico.")
        return

    df = pd.DataFrame(storico).sort_values("Data")

    # Grafico andamento
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.markdown("**IOP misurata (mmHg)**")
        st.line_chart(df.set_index("Data")[["IOP OD (mmHg)", "IOP OS (mmHg)"]])
    with col_g2:
        st.markdown("**IOPc corretta (mmHg)**")
        st.line_chart(df.set_index("Data")[["IOPc OD (mmHg)", "IOPc OS (mmHg)"]])

    # Soglie di riferimento
    st.caption("Soglie: normale < 18 mmHg | borderline 18–21.9 | elevata ≥ 22 mmHg (valori corretti per CCT)")

    # Tabella riepilogativa
    with st.expander("Tabella dati completa"):
        st.dataframe(df, use_container_width=True, hide_index=True)


# ── Tabella di correzione Dresdner (consultazione) ───────────────────────
def ui_dresdner_table() -> None:
    """Mostra la tabella di correzione Dresdner completa."""
    st.markdown("### Tabella di correzione Dresdner")
    st.caption("Correzione da applicare alla IOP misurata in base al CCT. CCT di riferimento: 545 µm.")
    rows = [
        {"CCT (µm)": cct, "Correzione IOP (mmHg)": f"{delta:+.1f}"}
        for cct, delta in DRESDNER_TABLE
    ]
    df = pd.DataFrame(rows)
    # Evidenzia riga normale (545 µm)
    st.dataframe(df, use_container_width=True, hide_index=True, height=300)
