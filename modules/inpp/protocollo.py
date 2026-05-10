# -*- coding: utf-8 -*-
"""
Definizione completa del protocollo INPP — Formulario di Valutazione
Diagnostica dello Sviluppo Neurologico (rev. 01/22).

Questo file è la SORGENTE DI VERITÀ per tutto il modulo INPP:
- ui_inpp.py legge da qui per costruire i form
- db_inpp.py salva i dati con questi id come chiavi
- pdf_inpp.py legge da qui per costruire il referto

Per modificare/aggiungere una prova, basta cambiare questo file.

Tipi di scoring:
- "0-4"          : scoring INPP standard (legenda in SCORING_LABELS)
- "si_no"        : sì / no
- "lateralita"   : sx / dx (preferenza laterale)
- "numerico"     : campi numerici (es. n.ripetizioni, secondi)
- "testo"        : testo libero
- "scelta"       : una scelta da una lista predefinita (vedi 'opzioni')
"""

from typing import Any

# -----------------------------------------------------------------------------
# Legenda scoring 0-4 ufficiale INPP (pag. 2 del Formulario rev. 01/22)
# -----------------------------------------------------------------------------
SCORING_LABELS: dict[int, str] = {
    0: "Nessuna anomalia",
    1: "Minima presenza residua / Minima difficoltà",
    2: "Riflesso primitivo residuo / Difficoltà a completare",
    3: "Riflesso primitivo presente in gran parte / Marcata difficoltà",
    4: "Riflesso primitivo completamente ritenuto / Incapacità",
}

# -----------------------------------------------------------------------------
# Le 10 sezioni del Formulario INPP
# Ogni sezione ha: id, label, descrizione, e una lista di 'gruppi'.
# Ogni gruppo è un blocco logico di prove (es. "Riflesso Tonico Asimmetrico
# del Collo") che contiene 1+ prove.
# -----------------------------------------------------------------------------

PROTOCOLLO_INPP: list[dict[str, Any]] = [
    # =========================================================================
    # SEZIONE 2 — COORDINAZIONE GROSSO-MOTORIA ED EQUILIBRIO
    # =========================================================================
    {
        "id": "coordinazione_equilibrio",
        "label": "Coordinazione grosso-motoria ed equilibrio",
        "icon": "🚶",
        "gruppi": [
            {
                "id": "recupero",
                "label": "Recupero della posizione verticale",
                "prove": [
                    {"id": "rec_supino", "label": "Da supino", "scoring": "0-4"},
                    {"id": "rec_prono", "label": "Da prono", "scoring": "0-4"},
                ],
            },
            {
                "id": "romberg",
                "label": "Test di Romberg",
                "prove": [
                    {"id": "romberg_aperti", "label": "Occhi aperti", "scoring": "0-4"},
                    {"id": "romberg_chiusi", "label": "Occhi chiusi", "scoring": "0-4"},
                ],
            },
            {
                "id": "mann",
                "label": "Test di Mann (Romberg avanzato)",
                "prove": [
                    {"id": "mann_aperti", "label": "Occhi aperti", "scoring": "0-4"},
                    {"id": "mann_chiusi", "label": "Occhi chiusi", "scoring": "0-4"},
                ],
            },
            {
                "id": "cammino_mezzo_giro",
                "label": "Cammino e mezzo giro",
                "prove": [
                    {"id": "cammino_mezzo_giro", "label": "Cammino e mezzo giro", "scoring": "0-4"},
                ],
            },
            {
                "id": "punte",
                "label": "Camminare sulle punte",
                "prove": [
                    {"id": "punte_avanti", "label": "Avanti", "scoring": "0-4"},
                    {"id": "punte_indietro", "label": "Indietro", "scoring": "0-4"},
                ],
            },
            {
                "id": "tandem",
                "label": "Tallone-Punta (tandem walk)",
                "prove": [
                    {"id": "tandem_avanti", "label": "Avanti", "scoring": "0-4"},
                    {"id": "tandem_indietro", "label": "Indietro", "scoring": "0-4"},
                ],
            },
            {
                "id": "fog",
                "label": "Camminare sull'esterno dei piedi (Fog walk)",
                "prove": [
                    {"id": "fog_avanti", "label": "Avanti", "scoring": "0-4"},
                    {"id": "fog_indietro", "label": "Indietro", "scoring": "0-4"},
                ],
            },
            {
                "id": "slalom",
                "label": "Camminare in slalom",
                "prove": [
                    {"id": "slalom_avanti", "label": "Avanti", "scoring": "0-4"},
                    {"id": "slalom_indietro", "label": "Indietro", "scoring": "0-4"},
                ],
            },
            {
                "id": "talloni",
                "label": "Camminare sui talloni (ginocchio in alto)",
                "prove": [
                    {"id": "talloni", "label": "Camminare sui talloni", "scoring": "0-4"},
                ],
            },
            {
                "id": "saltellare",
                "label": "Saltellare su una gamba",
                "prove": [
                    {"id": "saltellare_dx", "label": "Gamba destra", "scoring": "0-4"},
                    {"id": "saltellare_sx", "label": "Gamba sinistra", "scoring": "0-4"},
                ],
            },
            {
                "id": "schema_incrociato",
                "label": "Trotterellare in schema incrociato",
                "prove": [
                    {"id": "schema_incrociato", "label": "Trotterellare in schema incrociato", "scoring": "0-4"},
                ],
            },
        ],
    },
    # =========================================================================
    # SEZIONE 3 — SCHEMI DI SVILUPPO MOTORIO
    # (radio button: presente / atipico / assente, come da scelta utente)
    # =========================================================================
    {
        "id": "schemi_sviluppo",
        "label": "Schemi di sviluppo motorio",
        "icon": "🌀",
        "no_total": True,  # niente totale numerico
        "gruppi": [
            {
                "id": "striscio",
                "label": "Striscio",
                "prove": [
                    {"id": "striscio_omologo", "label": "Omologo", "scoring": "scelta",
                     "opzioni": ["presente", "atipico", "assente"]},
                    {"id": "striscio_omolaterale", "label": "Omolaterale", "scoring": "scelta",
                     "opzioni": ["presente", "atipico", "assente"]},
                    {"id": "striscio_incrociato", "label": "Incrociato", "scoring": "scelta",
                     "opzioni": ["presente", "atipico", "assente"]},
                ],
            },
            {
                "id": "carponi",
                "label": "Carponi",
                "prove": [
                    {"id": "carponi_omologo", "label": "Omologo", "scoring": "scelta",
                     "opzioni": ["presente", "atipico", "assente"]},
                    {"id": "carponi_omolaterale", "label": "Omolaterale", "scoring": "scelta",
                     "opzioni": ["presente", "atipico", "assente"]},
                    {"id": "carponi_incrociato", "label": "Incrociato", "scoring": "scelta",
                     "opzioni": ["presente", "atipico", "assente"]},
                ],
            },
            {
                "id": "schemi_note",
                "label": "Note osservative",
                "prove": [
                    {"id": "schemi_note", "label": "Note", "scoring": "testo"},
                ],
            },
        ],
    },
    # =========================================================================
    # SEZIONE 4 — FUNZIONALITÀ CEREBELLARE
    # =========================================================================
    {
        "id": "cerebellare",
        "label": "Funzionalità cerebellare",
        "icon": "🧠",
        "gruppi": [
            {
                "id": "tallone_tibia",
                "label": "Tallone su tibia",
                "prove": [
                    {"id": "tallone_sx_su_dx", "label": "Sx su Dx", "scoring": "0-4"},
                    {"id": "tallone_dx_su_sx", "label": "Dx su Sx", "scoring": "0-4"},
                ],
            },
            {
                "id": "approssimazione",
                "label": "Approssimazione digitale (linea mediana)",
                "prove": [
                    {"id": "appr_aperti", "label": "Occhi aperti", "scoring": "0-4"},
                    {"id": "appr_chiusi", "label": "Occhi chiusi", "scoring": "0-4"},
                ],
            },
            {
                "id": "dito_naso",
                "label": "Dito-naso",
                "prove": [
                    {"id": "dn_aperti", "label": "Occhi aperti", "scoring": "0-4"},
                    {"id": "dn_chiusi", "label": "Occhi chiusi", "scoring": "0-4"},
                ],
            },
        ],
    },
    # =========================================================================
    # SEZIONE 5 — DISDIADOCOCINESIA (manuale + orale)
    # =========================================================================
    {
        "id": "disdiadococinesia",
        "label": "Disdiadococinesia",
        "icon": "✋",
        "gruppi": [
            {
                "id": "dita",
                "label": "Dita",
                "prove": [
                    {"id": "dita_sx", "label": "Mano sinistra", "scoring": "0-4"},
                    {"id": "dita_dx", "label": "Mano destra", "scoring": "0-4"},
                ],
            },
            {
                "id": "mani",
                "label": "Mani",
                "prove": [
                    {"id": "mani_sx", "label": "Sinistra", "scoring": "0-4"},
                    {"id": "mani_dx", "label": "Destra", "scoring": "0-4"},
                ],
            },
            {
                "id": "piedi",
                "label": "Piedi",
                "prove": [
                    {"id": "piedi_sx", "label": "Sinistro", "scoring": "0-4"},
                    {"id": "piedi_dx", "label": "Destro", "scoring": "0-4"},
                ],
            },
            {
                "id": "orale",
                "label": "Disdiadococinesia orale (registrare ripetizioni e secondi)",
                "prove": [
                    {"id": "orale_pa_rep", "label": "/pʌ/ — n. ripetizioni", "scoring": "numerico"},
                    {"id": "orale_pa_sec", "label": "/pʌ/ — secondi", "scoring": "numerico"},
                    {"id": "orale_ta_rep", "label": "/tʌ/ — n. ripetizioni", "scoring": "numerico"},
                    {"id": "orale_ta_sec", "label": "/tʌ/ — secondi", "scoring": "numerico"},
                    {"id": "orale_ka_rep", "label": "/kʌ/ — n. ripetizioni", "scoring": "numerico"},
                    {"id": "orale_ka_sec", "label": "/kʌ/ — secondi", "scoring": "numerico"},
                    {"id": "orale_pata_rep", "label": "/pʌtə/ — n. ripetizioni", "scoring": "numerico"},
                    {"id": "orale_pata_sec", "label": "/pʌtə/ — secondi", "scoring": "numerico"},
                    {"id": "orale_pataka_rep", "label": "/pʌtəkə/ — n. ripetizioni", "scoring": "numerico"},
                    {"id": "orale_pataka_sec", "label": "/pʌtəkə/ — secondi", "scoring": "numerico"},
                ],
            },
        ],
    },
    # =========================================================================
    # SEZIONE 6 — ORIENTAMENTO SPAZIALE + PROPRIOCEZIONE
    # =========================================================================
    {
        "id": "orientamento_propriocezione",
        "label": "Orientamento spaziale e propriocezione",
        "icon": "🧭",
        "gruppi": [
            {
                "id": "orientamento",
                "label": "Orientamento spaziale (sì/no)",
                "prove": [
                    {"id": "orient_dx_sx", "label": "Problemi di discriminazione destra/sinistra",
                     "scoring": "si_no"},
                    {"id": "orient_orientamento", "label": "Problemi di orientamento", "scoring": "si_no"},
                    {"id": "orient_spaziali", "label": "Problemi spaziali", "scoring": "si_no"},
                ],
            },
            {
                "id": "gold",
                "label": "Test di Gold (toccare e indicare)",
                "prove": [
                    {"id": "gold_dx_su_sx", "label": "Destra su sinistra", "scoring": "0-4"},
                    {"id": "gold_sx_su_dx", "label": "Sinistra su destra", "scoring": "0-4"},
                ],
            },
            {
                "id": "specchio",
                "label": "Test dei movimenti a specchio",
                "prove": [
                    {"id": "specchio_sx", "label": "Sinistra", "scoring": "0-4"},
                    {"id": "specchio_dx", "label": "Destra", "scoring": "0-4"},
                ],
            },
        ],
    },
    # =========================================================================
    # SEZIONE 7 — RIFLESSI DELLO SVILUPPO (la più grande)
    # =========================================================================
    {
        "id": "riflessi",
        "label": "Riflessi dello sviluppo",
        "icon": "🧬",
        "gruppi": [
            {
                "id": "rtac",
                "label": "Riflesso Tonico Asimmetrico del Collo (RTAC)",
                "prove": [
                    {"id": "rtac_std_br_sx", "label": "Standard — Braccio sinistro", "scoring": "0-4"},
                    {"id": "rtac_std_gb_sx", "label": "Standard — Gamba sinistra", "scoring": "0-4"},
                    {"id": "rtac_std_br_dx", "label": "Standard — Braccio destro", "scoring": "0-4"},
                    {"id": "rtac_std_gb_dx", "label": "Standard — Gamba destra", "scoring": "0-4"},
                    {"id": "rtac_ayres1_br_sx", "label": "Test di Ayres (n.1) — Braccio sinistro", "scoring": "0-4"},
                    {"id": "rtac_ayres1_br_dx", "label": "Test di Ayres (n.1) — Braccio destro", "scoring": "0-4"},
                    {"id": "rtac_ayres2_br_sx", "label": "Test di Ayres (n.2) — Braccio sinistro", "scoring": "0-4"},
                    {"id": "rtac_ayres2_br_dx", "label": "Test di Ayres (n.2) — Braccio destro", "scoring": "0-4"},
                    {"id": "rtac_schidler_br_sx", "label": "Test di Schidler — Braccio sinistro", "scoring": "0-4"},
                    {"id": "rtac_schidler_br_dx", "label": "Test di Schidler — Braccio destro", "scoring": "0-4"},
                ],
            },
            {
                "id": "rtc_trasformato",
                "label": "Riflesso Tonico Trasformato del Collo",
                "prove": [
                    {"id": "rtc_dx_sx", "label": "Destra a sinistra", "scoring": "0-4"},
                    {"id": "rtc_sx_dx", "label": "Sinistra a destra", "scoring": "0-4"},
                ],
            },
            {
                "id": "rtsc",
                "label": "Riflesso Tonico Simmetrico del Collo (RTSC)",
                "prove": [
                    {"id": "rtsc_piedi_sedere", "label": "Coinvolgimento dei piedi o del sedere", "scoring": "0-4"},
                    {"id": "rtsc_braccia", "label": "Coinvolgimento delle braccia", "scoring": "0-4"},
                    {"id": "rtsc_carponi", "label": "Evidenza durante il carponi", "scoring": "0-4"},
                ],
            },
            {
                "id": "galant",
                "label": "Riflesso Spinale di Galant",
                "prove": [
                    {"id": "galant_sx", "label": "Lato sinistro", "scoring": "0-4"},
                    {"id": "galant_dx", "label": "Lato destro", "scoring": "0-4"},
                ],
            },
            {
                "id": "rtl",
                "label": "Riflesso Tonico Labirintico del Collo (RTL)",
                "prove": [
                    {"id": "rtl_std", "label": "Test Standard", "scoring": "0-4"},
                    {"id": "rtl_piedi_aperti_flex", "label": "In piedi (occhi aperti) — Flessione", "scoring": "0-4"},
                    {"id": "rtl_piedi_aperti_ext", "label": "In piedi (occhi aperti) — Estensione", "scoring": "0-4"},
                    {"id": "rtl_piedi_chiusi_flex", "label": "In piedi (occhi chiusi) — Flessione", "scoring": "0-4"},
                    {"id": "rtl_piedi_chiusi_ext", "label": "In piedi (occhi chiusi) — Estensione", "scoring": "0-4"},
                    {"id": "rtl_ayres", "label": "Test di Ayres", "scoring": "0-4"},
                    {"id": "rtl_fiorentino", "label": "Test di Fiorentino", "scoring": "0-4"},
                ],
            },
            {
                "id": "moro",
                "label": "Riflesso di Moro",
                "prove": [
                    {"id": "moro_std", "label": "Test Standard", "scoring": "0-4"},
                    {"id": "moro_piede", "label": "Test in piede", "scoring": "0-4"},
                ],
            },
            {
                "id": "sostegno_oculare",
                "label": "Riflesso di Sostegno Cefalico Oculare",
                "prove": [
                    {"id": "sost_oc_sx", "label": "A sinistra", "scoring": "0-4"},
                    {"id": "sost_oc_dx", "label": "A destra", "scoring": "0-4"},
                    {"id": "sost_oc_indietro", "label": "All'indietro", "scoring": "0-4"},
                    {"id": "sost_oc_avanti", "label": "In avanti", "scoring": "0-4"},
                ],
            },
            {
                "id": "sostegno_labirintico",
                "label": "Riflesso di Sostegno Cefalico Labirintico",
                "prove": [
                    {"id": "sost_lb_sx", "label": "A sinistra", "scoring": "0-4"},
                    {"id": "sost_lb_dx", "label": "A destra", "scoring": "0-4"},
                    {"id": "sost_lb_indietro", "label": "All'indietro", "scoring": "0-4"},
                    {"id": "sost_lb_avanti", "label": "In avanti", "scoring": "0-4"},
                ],
            },
            {
                "id": "anfibio",
                "label": "Riflesso Anfibio",
                "prove": [
                    {"id": "anf_prono_sx", "label": "Prono — Lato sinistro", "scoring": "0-4"},
                    {"id": "anf_prono_dx", "label": "Prono — Lato destro", "scoring": "0-4"},
                    {"id": "anf_supino_sx", "label": "Supino — Lato sinistro", "scoring": "0-4"},
                    {"id": "anf_supino_dx", "label": "Supino — Lato destro", "scoring": "0-4"},
                ],
            },
            {
                "id": "rotazione_seg",
                "label": "Riflesso di rotazione segmentaria",
                "prove": [
                    {"id": "rot_anche_sx", "label": "Dalle anche — Lato sinistro", "scoring": "0-4"},
                    {"id": "rot_anche_dx", "label": "Dalle anche — Lato destro", "scoring": "0-4"},
                    {"id": "rot_spalle_sx", "label": "Dalle spalle — Lato sinistro", "scoring": "0-4"},
                    {"id": "rot_spalle_dx", "label": "Dalle spalle — Lato destro", "scoring": "0-4"},
                ],
            },
            {
                "id": "babinsky",
                "label": "Riflesso di Babinsky",
                "prove": [
                    {"id": "bab_sx", "label": "Piede sinistro", "scoring": "0-4"},
                    {"id": "bab_dx", "label": "Piede destro", "scoring": "0-4"},
                ],
            },
            {
                "id": "addominale_landau",
                "label": "Riflessi Addominale e Landau",
                "prove": [
                    {"id": "addominale", "label": "Riflesso Addominale", "scoring": "0-4"},
                    {"id": "landau", "label": "Riflesso di Landau", "scoring": "0-4"},
                ],
            },
            {
                "id": "rooting",
                "label": "Riflesso di Ricerca / punti cardinali (Rooting)",
                "prove": [
                    {"id": "rooting_sx", "label": "Sinistra", "scoring": "0-4"},
                    {"id": "rooting_dx", "label": "Destra", "scoring": "0-4"},
                ],
            },
            {
                "id": "suzione",
                "label": "Riflessi di suzione",
                "prove": [
                    {"id": "suzione", "label": "Riflesso di suzione", "scoring": "0-4"},
                    {"id": "suzione_adulta", "label": "Riflesso di suzione adulta", "scoring": "scelta",
                     "opzioni": ["assente", "debole", "presente"]},
                ],
            },
            {
                "id": "prensile_mano",
                "label": "Riflesso Prensile (mano)",
                "prove": [
                    {"id": "prens_mano_sx", "label": "Mano sinistra", "scoring": "0-4"},
                    {"id": "prens_mano_dx", "label": "Mano destra", "scoring": "0-4"},
                ],
            },
            {
                "id": "prensile_piede",
                "label": "Riflesso Prensile (piede)",
                "prove": [
                    {"id": "prens_piede_sx", "label": "Piede sinistro", "scoring": "0-4"},
                    {"id": "prens_piede_dx", "label": "Piede destro", "scoring": "0-4"},
                ],
            },
        ],
    },
    # =========================================================================
    # SEZIONE 8 — LATERALITÀ (preferenza laterale, no scoring numerico)
    # =========================================================================
    {
        "id": "lateralita",
        "label": "Lateralità",
        "icon": "↔️",
        "no_total": True,
        "gruppi": [
            {
                "id": "lat_piede",
                "label": "Lateralità di piede",
                "prove": [
                    {"id": "lat_piede_palla", "label": "Calciare la palla", "scoring": "lateralita"},
                    {"id": "lat_piede_calcio", "label": "Calcio sul pavimento", "scoring": "lateralita"},
                    {"id": "lat_piede_sedia", "label": "Salire sulla sedia", "scoring": "lateralita"},
                    {"id": "lat_piede_saltell", "label": "Saltellare su una gamba", "scoring": "lateralita"},
                ],
            },
            {
                "id": "lat_mano",
                "label": "Lateralità di mano",
                "prove": [
                    {"id": "lat_mano_palla", "label": "Prendere una palla", "scoring": "lateralita"},
                    {"id": "lat_mano_applauso", "label": "Applauso", "scoring": "lateralita"},
                    {"id": "lat_mano_scrittura", "label": "Scrittura", "scoring": "lateralita"},
                    {"id": "lat_mano_telescopio", "label": "Telescopio", "scoring": "lateralita"},
                ],
            },
            {
                "id": "lat_occhio_lontano",
                "label": "Lateralità di occhio (da lontano)",
                "prove": [
                    {"id": "lat_occ_lont_telescopio", "label": "Telescopio", "scoring": "lateralita"},
                    {"id": "lat_occ_lont_anello", "label": "Anello", "scoring": "lateralita"},
                ],
            },
            {
                "id": "lat_occhio_vicino",
                "label": "Lateralità di occhio (da vicino)",
                "prove": [
                    {"id": "lat_occ_vic_buco", "label": "Buco nella carta", "scoring": "lateralita"},
                    {"id": "lat_occ_vic_anello", "label": "Anello", "scoring": "lateralita"},
                ],
            },
            {
                "id": "lat_orecchio",
                "label": "Lateralità di orecchio",
                "prove": [
                    {"id": "lat_or_conchiglia", "label": "Conchiglia", "scoring": "lateralita"},
                    {"id": "lat_or_chiamata", "label": "Chiamata da dietro", "scoring": "lateralita"},
                    {"id": "lat_or_ascolto", "label": "Ascolto sotto il tavolo", "scoring": "lateralita"},
                ],
            },
        ],
    },
    # =========================================================================
    # SEZIONE 9 — TEST OCULO-MOTORI
    # =========================================================================
    {
        "id": "oculomotori",
        "label": "Test oculo-motori",
        "icon": "👁",
        "gruppi": [
            {
                "id": "oculo_base",
                "label": "Funzionalità oculo-motoria di base",
                "prove": [
                    {"id": "oc_fissazione", "label": "Difficoltà di fissazione", "scoring": "0-4"},
                    {"id": "oc_inseguimento", "label": "Difficoltà di inseguimento (tracking orizzontale)", "scoring": "0-4"},
                    {"id": "oc_occhio_mano", "label": "Inseguimento occhio-mano", "scoring": "0-4"},
                    {"id": "oc_conv_latente", "label": "Convergenza latente", "scoring": "0-4"},
                    {"id": "oc_div_latente", "label": "Divergenza latente", "scoring": "0-4"},
                ],
            },
            {
                "id": "oculo_lateralizzati",
                "label": "Test bilaterali",
                "prove": [
                    {"id": "oc_conv_sx", "label": "Convergenza — Occhio sinistro", "scoring": "0-4"},
                    {"id": "oc_conv_dx", "label": "Convergenza — Occhio destro", "scoring": "0-4"},
                    {"id": "oc_chius_sx", "label": "Chiusura indipendente — Occhio sinistro", "scoring": "0-4"},
                    {"id": "oc_chius_dx", "label": "Chiusura indipendente — Occhio destro", "scoring": "0-4"},
                    {"id": "oc_yoking_sx", "label": "Yoking — Occhio sinistro", "scoring": "0-4"},
                    {"id": "oc_yoking_dx", "label": "Yoking — Occhio destro", "scoring": "0-4"},
                    {"id": "oc_perif_sx", "label": "Visione periferica amplificata — Sinistra", "scoring": "0-4"},
                    {"id": "oc_perif_dx", "label": "Visione periferica amplificata — Destra", "scoring": "0-4"},
                ],
            },
            {
                "id": "oculo_accomodazione",
                "label": "Accomodazione",
                "prove": [
                    {"id": "oc_accomod", "label": "Ristabilimento della visione binoculare", "scoring": "0-4"},
                ],
            },
            {
                "id": "pupillare",
                "label": "Riflesso pupillare (annotazione testuale)",
                "prove": [
                    {"id": "pup_prima_sx", "label": "Prima stimolazione — Sx", "scoring": "testo"},
                    {"id": "pup_prima_dx", "label": "Prima stimolazione — Dx", "scoring": "testo"},
                    {"id": "pup_seconda_sx", "label": "Seconda stimolazione — Sx", "scoring": "testo"},
                    {"id": "pup_seconda_dx", "label": "Seconda stimolazione — Dx", "scoring": "testo"},
                ],
            },
        ],
    },
    # =========================================================================
    # SEZIONE 10 — TEST VISUO-PERCETTIVI
    # =========================================================================
    {
        "id": "visuo_percettivi",
        "label": "Test visuo-percettivi",
        "icon": "🎨",
        "gruppi": [
            {
                "id": "vp_principali",
                "label": "Test visuo-percettivi",
                "prove": [
                    {"id": "vp_stimulous_bound", "label": "Indicazioni di Stimulous bound", "scoring": "0-4"},
                    {"id": "vp_discriminazione", "label": "Problemi di discriminazione visiva", "scoring": "0-4"},
                    {"id": "vp_integrazione", "label": "Difficoltà di integrazione viso-motoria", "scoring": "0-4"},
                    {"id": "vp_spaziali", "label": "Problemi spaziali", "scoring": "0-4"},
                ],
            },
        ],
    },
    # =========================================================================
    # SEZIONE 11 — GOODENOUGH (Indice di Aston, disegno della figura umana)
    # =========================================================================
    {
        "id": "goodenough",
        "label": "Test di Goodenough (Indice di Aston)",
        "icon": "🧒",
        "no_total": True,
        "gruppi": [
            {
                "id": "good_score",
                "label": "Punteggio Goodenough",
                "prove": [
                    {"id": "good_punteggio", "label": "Punteggio totale (somma dei criteri)",
                     "scoring": "numerico"},
                    {"id": "good_eta_mentale", "label": "Età mentale corrispondente (anni;mesi)",
                     "scoring": "testo"},
                    {"id": "good_note", "label": "Note osservative sul disegno",
                     "scoring": "testo"},
                ],
            },
        ],
    },
]

# -----------------------------------------------------------------------------
# UTILITY: lookup veloci e calcolo punteggi
# -----------------------------------------------------------------------------

def itera_prove(scoring_filter: str | None = None):
    """
    Generatore: per ogni prova del protocollo, restituisce
    (sezione_id, gruppo_id, prova_dict).
    Se scoring_filter è dato, filtra solo le prove con quel tipo di scoring.
    """
    for sezione in PROTOCOLLO_INPP:
        for gruppo in sezione["gruppi"]:
            for prova in gruppo["prove"]:
                if scoring_filter is None or prova.get("scoring") == scoring_filter:
                    yield sezione["id"], gruppo["id"], prova


def calcola_punteggio_sezione(sezione_id: str, valori: dict) -> tuple[int, int]:
    """
    Calcola (punteggio_ottenuto, punteggio_massimo) per una sezione,
    considerando solo le prove con scoring '0-4'.

    Restituisce (0, 0) se la sezione non esiste o non ha prove 0-4.
    """
    sezione = next((s for s in PROTOCOLLO_INPP if s["id"] == sezione_id), None)
    if sezione is None or sezione.get("no_total"):
        return 0, 0

    ottenuto = 0
    massimo = 0
    for gruppo in sezione["gruppi"]:
        for prova in gruppo["prove"]:
            if prova.get("scoring") == "0-4":
                massimo += 4
                v = valori.get(prova["id"])
                if isinstance(v, (int, float)):
                    ottenuto += int(v)
    return ottenuto, massimo


def riepilogo_punteggi(valori: dict) -> dict[str, dict]:
    """
    Costruisce il riepilogo finale: per ogni sezione, punteggio e percentuale.

    Ritorna: {sezione_id: {"label": str, "ottenuto": int, "massimo": int, "perc": float}}
    """
    out: dict[str, dict] = {}
    for sezione in PROTOCOLLO_INPP:
        if sezione.get("no_total"):
            continue
        ott, mx = calcola_punteggio_sezione(sezione["id"], valori)
        if mx > 0:
            out[sezione["id"]] = {
                "label": sezione["label"],
                "ottenuto": ott,
                "massimo": mx,
                "perc": round(100.0 * ott / mx, 1),
            }
    return out


def conta_prove_totali() -> int:
    """Numero totale di prove nel protocollo (utile per debug/info)."""
    return sum(1 for _ in itera_prove())
