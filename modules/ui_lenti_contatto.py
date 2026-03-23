# -*- coding: utf-8 -*-
"""
Modulo unificato: Lenti a Contatto
Gestionale The Organism – PNEV

Obiettivo:
- unificare in una sola voce menu tutta la contattologia
- raccogliere in un'unica interfaccia i moduli già esistenti
- mantenere compatibilità con l'architettura attuale senza rompere DB e storici

Questo file NON sostituisce gli algoritmi esistenti:
li orchestra in una sola UI clinica.
"""

from __future__ import annotations

import streamlit as st

# -----------------------------------------------------------------------------
# Import moduli esistenti
# -----------------------------------------------------------------------------

try:
    from modules.ui_lenti_inverse import ui_lenti_inverse
except Exception:
    ui_lenti_inverse = None

try:
    from modules.ui_calcolatore_lac import ui_calcolatore_lac
except Exception:
    ui_calcolatore_lac = None

try:
    from modules.ui_esa_ortho6 import ui_esa_ortho6
except Exception:
    ui_esa_ortho6 = None

try:
    from modules.ui_lac_ametropie import ui_lac_ametropie
except Exception:
    ui_lac_ametropie = None

try:
    from modules.ui_calcolatore_lac_plus import ui_calcolatore_lac_plus
except Exception:
    ui_calcolatore_lac_plus = None

try:
    from modules.ui_fluorescein import ui_fluorescein_simulator
except Exception:
    ui_fluorescein_simulator = None


# -----------------------------------------------------------------------------
# UI helpers
# -----------------------------------------------------------------------------


def _inject_css() -> None:
    st.markdown(
        """
        <style>
        .lac-wrap {
            border: 1px solid #d9e3dc;
            background: linear-gradient(180deg, #fbfcfb 0%, #f5f8f6 100%);
            border-radius: 16px;
            padding: 18px 18px 14px 18px;
            margin-bottom: 14px;
        }
        .lac-title {
            font-size: 1.35rem;
            font-weight: 700;
            color: #1d4f43;
            margin-bottom: 4px;
        }
        .lac-sub {
            font-size: 0.95rem;
            color: #55756a;
            margin-bottom: 10px;
        }
        .lac-chip-row {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 8px;
        }
        .lac-chip {
            background: #eaf3ef;
            border: 1px solid #cfe0d8;
            color: #28584b;
            border-radius: 999px;
            padding: 6px 10px;
            font-size: 0.83rem;
            line-height: 1.1rem;
        }
        .lac-note {
            border-left: 4px solid #2d7d6f;
            background: #f7fbf9;
            padding: 10px 12px;
            border-radius: 10px;
            margin: 8px 0 14px 0;
            color: #34564c;
        }
        .lac-mini {
            font-size: 0.88rem;
            color: #546960;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )



def _module_missing(label: str) -> None:
    st.error(f"Modulo non disponibile: {label}")
    st.caption("Controlla che il file esista nella cartella modules e che gli import siano corretti.")



def _render_intro() -> None:
    st.markdown(
        """
        <div class="lac-wrap">
            <div class="lac-title">Lenti a contatto</div>
            <div class="lac-sub">
                Hub clinico unificato per lenti inverse, non inverse, toriche,
                multifocali e su misura.
            </div>
            <div class="lac-chip-row">
                <div class="lac-chip">Ortho-K / inverse</div>
                <div class="lac-chip">Morbide e RGP</div>
                <div class="lac-chip">Toriche</div>
                <div class="lac-chip">Presbiopia / multifocali</div>
                <div class="lac-chip">Toffoli</div>
                <div class="lac-chip">Calossi / ESA</div>
                <div class="lac-chip">Fluoresceina</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="lac-note">
            <strong>Logica del modulo unico:</strong><br>
            qui dentro trovi tutta la contattologia raccolta in un solo punto.
            Le vecchie voci separate del menu possono essere rimosse e rimpiazzate
            da questa sola voce.
        </div>
        """,
        unsafe_allow_html=True,
    )



def _render_overview() -> None:
    c1, c2 = st.columns([1.1, 1])
    with c1:
        st.markdown("### Percorso clinico consigliato")
        st.markdown(
            """
1. Seleziona il paziente nel modulo clinico specifico.
2. Scegli il ramo corretto: inverse, standard, toriche o multifocali.
3. Calcola la lente con il modello più adatto.
4. Verifica il fitting con fluoresceina/sagitta quando serve.
5. Salva scheda, ordine e follow-up nello storico.
            """
        )
    with c2:
        st.markdown("### Modelli inclusi")
        st.markdown(
            """
- **Toffoli / Inversa 6** per ortho-k e geometrie inverse
- **ESA Ortho-6** per lookup e confronto rapido
- **Calossi / ESA hexacurve** per ametropie avanzate
- **LAC morbide / RGP / toriche / multifocali** con salvataggio clinico
            """
        )

    st.caption(
        "Suggerimento operativo: usa le prime tab per il calcolo e le ultime per verifica, fitting e storico."
    )


# -----------------------------------------------------------------------------
# Entrypoint principale
# -----------------------------------------------------------------------------


def ui_lenti_contatto() -> None:
    _inject_css()
    _render_intro()

    with st.expander("Guida rapida del modulo unico", expanded=False):
        _render_overview()

    tabs = st.tabs(
        [
            "Panoramica",
            "Inverse / Ortho-K",
            "Calcolo Inverse (Toffoli)",
            "ESA Ortho-6",
            "Morbide / RGP / Toriche / Presbiopia",
            "Ametropie avanzate (Calossi)",
            "Fluoresceina",
        ]
    )

    with tabs[0]:
        st.markdown("### Hub Lenti a Contatto")
        st.info(
            "Questa pagina riunisce tutti i moduli LAC del gestionale. "
            "Per eliminare le vecchie voci del menu, collega soltanto `ui_lenti_contatto()` alla sidebar."
        )
        _render_overview()

    with tabs[1]:
        st.markdown("### Inverse / Ortocheratologia")
        st.caption(
            "Gestione clinica completa: schede, ordini, visite e storico delle lenti inverse."
        )
        if ui_lenti_inverse is None:
            _module_missing("ui_lenti_inverse.py")
        else:
            ui_lenti_inverse()

    with tabs[2]:
        st.markdown("### Calcolo LAC Inversa — algoritmo Toffoli")
        st.caption(
            "Motore di calcolo tecnico per lente inversa, import topografia, profilo sagittale e salvataggio parametri."
        )
        if ui_calcolatore_lac is None:
            _module_missing("ui_calcolatore_lac.py")
        else:
            ui_calcolatore_lac()

    with tabs[3]:
        st.markdown("### ESA Ortho-6")
        st.caption(
            "Lookup clinico per assortimento ESA, utile come riferimento rapido e confronto costruttivo."
        )
        if ui_esa_ortho6 is None:
            _module_missing("ui_esa_ortho6.py")
        else:
            ui_esa_ortho6()

    with tabs[4]:
        st.markdown("### LAC morbide / RGP / toriche / multifocali")
        st.caption(
            "Gestione integrata per miopia, ipermetropia, astigmatismo e presbiopia con storico clinico dedicato."
        )
        if ui_lac_ametropie is None:
            _module_missing("ui_lac_ametropie.py")
        else:
            ui_lac_ametropie()

    with tabs[5]:
        st.markdown("### Ametropie avanzate — schema Calossi / ESA")
        st.caption(
            "Calcolo avanzato per ipermetropia, toriche, presbiopia e combinazioni su misura."
        )
        if ui_calcolatore_lac_plus is None:
            _module_missing("ui_calcolatore_lac_plus.py")
        else:
            ui_calcolatore_lac_plus()

    with tabs[6]:
        st.markdown("### Simulazione fluoresceina")
        st.caption(
            "Verifica qualitativa del fitting e della clearance per design miopici, ipermetropici, torici e presbiopici."
        )
        if ui_fluorescein_simulator is None:
            _module_missing("ui_fluorescein.py")
        else:
            ui_fluorescein_simulator()


__all__ = ["ui_lenti_contatto"]
