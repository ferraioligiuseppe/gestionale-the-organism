# -*- coding: utf-8 -*-
"""
Modulo: LAC per Ipermetropia, Astigmatismo e Presbiopia
Gestionale The Organism – PNEV
Compatibile con SQLite e PostgreSQL (Neon).
"""

import json
import streamlit as st
try:
    from modules.ui_raggio_potere import r_to_d, d_to_r
except ImportError:
    def r_to_d(r): return round(337.5/r, 2) if r and r>0 else 0.0
    def d_to_r(d): return round(337.5/d, 3) if d and d>0 else 0.0
from datetime import datetime, date


# ---------------------------------------------------------------------------
# Helpers (stesso pattern di ui_lenti_inverse.py)
# ---------------------------------------------------------------------------

def _is_postgres(conn) -> bool:
    t = type(conn).__name__
    if "Pg" in t or "pg" in t:
        return True
    try:
        import sys, os
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if root not in sys.path:
            sys.path.insert(0, root)
        from app_patched import _DB_BACKEND
        return _DB_BACKEND == "postgres"
    except Exception:
        pass
    try:
        mod = type(conn).__module__ or ""
        if "psycopg2" in mod or "psycopg" in mod:
            return True
    except Exception:
        pass
    try:
        cur_type = type(conn.cursor()).__name__
        if "Pg" in cur_type:
            return True
    except Exception:
        pass
    return False


def _ph(n: int, conn) -> str:
    mark = "%s" if _is_postgres(conn) else "?"
    return ", ".join([mark] * n)


def _get_conn():
    try:
        from modules.app_core import get_connection
        return get_connection()
    except Exception:
        pass
    try:
        import sys, os
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if root not in sys.path:
            sys.path.insert(0, root)
        from app_patched import get_connection
        return get_connection()
    except Exception:
        pass
    import sqlite3
    conn = sqlite3.connect("organism.db")
    conn.row_factory = sqlite3.Row
    return conn


def _row_get(row, key, default=None):
    try:
        v = row[key]
        return v if v is not None else default
    except Exception:
        try:
            return row.get(key, default)
        except Exception:
            return default


def _today_str():
    return date.today().strftime("%d/%m/%Y")


def _parse_date(s):
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime((s or "").strip(), fmt).strftime("%Y-%m-%d")
        except Exception:
            pass
    return ""


# ---------------------------------------------------------------------------
# Costanti
# ---------------------------------------------------------------------------

TIPI_AMETROPIA = ["Ipermetropia", "Astigmatismo", "Ipermetropia + Astigmatismo", "Presbiopia",
                  "Presbiopia + Ipermetropia", "Presbiopia + Astigmatismo", "Presbiopia + Mista"]

TIPI_LENTE = ["LAC morbida giornaliera", "LAC morbida mensile/quindicinale",
              "LAC morbida multifocale", "LAC morbida torica",
              "LAC morbida torica multifocale",
              "RGP (rigida gas-permeabile)", "RGP torica", "RGP multifocale",
              "Ortocheratologia inversa (ipermetropia)", "Lente sclerale",
              "Lente sclerale torica", "Lente sclerale multifocale",
              "Monovisione OD lontano", "Monovisione OS lontano"]

DESIGN_MULTIFOCALE = ["—", "centro-lontano", "centro-vicino", "anulare alternante", "progressivo", "diffrattivo"]

TIPI_APPOGGIO = ["para-apicale", "apicale", "piatto", "sollevato", "N/A"]
PATTERN_FLUOR = ["ottimale", "appoggio_centrale_eccessivo", "sollevamento_centrale",
                 "appoggio_periferico_stretto", "appoggio_periferico_largo",
                 "decentramento_superiore", "decentramento_inferiore",
                 "decentramento_nasale", "decentramento_temporale", "N/A"]
CENTRATURA    = ["centrata", "decentrata_superiore", "decentrata_inferiore",
                 "decentrata_nasale", "decentrata_temporale"]
VALUTAZIONE   = ["ottimale", "accettabile", "da_modificare", "da_sostituire"]


# ---------------------------------------------------------------------------
# SQL CREATE TABLE
# ---------------------------------------------------------------------------

_SQL_PG_SCHEDE = """
CREATE TABLE IF NOT EXISTS lac_ametropie (
    id BIGSERIAL PRIMARY KEY,
    paziente_id BIGINT NOT NULL,
    occhio TEXT NOT NULL,
    data_scheda TEXT,
    ametropia TEXT,
    tipo_lente TEXT,

    topo_k_flat_mm DOUBLE PRECISION,
    topo_k_flat_d DOUBLE PRECISION,
    topo_k_steep_mm DOUBLE PRECISION,
    topo_k_steep_d DOUBLE PRECISION,
    topo_asse_steep INTEGER,
    topo_ecc_media DOUBLE PRECISION,
    topo_raggio_apicale_mm DOUBLE PRECISION,
    topo_dev_std_raggio DOUBLE PRECISION,
    topo_dev_std_ecc DOUBLE PRECISION,
    topo_topografo TEXT,
    topo_data TEXT,
    topo_misurazioni_json TEXT,

    rx_sfera DOUBLE PRECISION,
    rx_cilindro DOUBLE PRECISION,
    rx_asse INTEGER,
    rx_add DOUBLE PRECISION,
    rx_miopia_equiv DOUBLE PRECISION,
    rx_avsc_lon TEXT,
    rx_avcc_lon TEXT,
    rx_avsc_vic TEXT,
    rx_avcc_vic TEXT,
    rx_dominanza_oculare TEXT,

    lente_rb_mm DOUBLE PRECISION,
    lente_diam_mm DOUBLE PRECISION,
    lente_potere_lon_d DOUBLE PRECISION,
    lente_potere_vic_d DOUBLE PRECISION,
    lente_add_lente DOUBLE PRECISION,
    lente_design_multifoc TEXT,
    lente_cilindro DOUBLE PRECISION,
    lente_asse_cil INTEGER,
    lente_zo_mm DOUBLE PRECISION,
    lente_sag_mm DOUBLE PRECISION,
    lente_clearance_mm DOUBLE PRECISION,
    lente_materiale TEXT,
    lente_dk DOUBLE PRECISION,
    lente_sostituzione TEXT,
    lente_soluzione TEXT,
    lente_puntino INTEGER DEFAULT 0,
    lente_note TEXT,

    app_data TEXT,
    app_tipo TEXT,
    app_clearance_centrale DOUBLE PRECISION,
    app_clearance_periferica DOUBLE PRECISION,
    app_pattern TEXT,
    app_centratura TEXT,
    app_movimento_mm DOUBLE PRECISION,
    app_rotazione_gradi DOUBLE PRECISION,
    app_stabilizzazione TEXT,
    app_valutazione TEXT,
    app_modifiche TEXT,
    app_operatore TEXT,
    app_note_fluoresceina TEXT,
    app_note TEXT,

    created_at TEXT,
    updated_at TEXT
)
"""

_SQL_SL_SCHEDE = """
CREATE TABLE IF NOT EXISTS lac_ametropie (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paziente_id INTEGER NOT NULL,
    occhio TEXT NOT NULL,
    data_scheda TEXT,
    ametropia TEXT,
    tipo_lente TEXT,
    topo_k_flat_mm REAL, topo_k_flat_d REAL,
    topo_k_steep_mm REAL, topo_k_steep_d REAL, topo_asse_steep INTEGER,
    topo_ecc_media REAL, topo_raggio_apicale_mm REAL,
    topo_dev_std_raggio REAL, topo_dev_std_ecc REAL,
    topo_topografo TEXT, topo_data TEXT, topo_misurazioni_json TEXT,
    rx_sfera REAL, rx_cilindro REAL, rx_asse INTEGER,
    rx_add REAL, rx_miopia_equiv REAL,
    rx_avsc_lon TEXT, rx_avcc_lon TEXT, rx_avsc_vic TEXT, rx_avcc_vic TEXT,
    rx_dominanza_oculare TEXT,
    lente_rb_mm REAL, lente_diam_mm REAL,
    lente_potere_lon_d REAL, lente_potere_vic_d REAL, lente_add_lente REAL,
    lente_design_multifoc TEXT, lente_cilindro REAL, lente_asse_cil INTEGER,
    lente_zo_mm REAL, lente_sag_mm REAL, lente_clearance_mm REAL,
    lente_materiale TEXT, lente_dk REAL, lente_sostituzione TEXT,
    lente_soluzione TEXT, lente_puntino INTEGER DEFAULT 0, lente_note TEXT,
    app_data TEXT, app_tipo TEXT,
    app_clearance_centrale REAL, app_clearance_periferica REAL,
    app_pattern TEXT, app_centratura TEXT,
    app_movimento_mm REAL, app_rotazione_gradi REAL, app_stabilizzazione TEXT,
    app_valutazione TEXT, app_modifiche TEXT, app_operatore TEXT,
    app_note_fluoresceina TEXT, app_note TEXT,
    created_at TEXT, updated_at TEXT
)
"""

_SQL_PG_ORDINI = """
CREATE TABLE IF NOT EXISTS lac_ametropie_ordini (
    id BIGSERIAL PRIMARY KEY,
    scheda_id BIGINT NOT NULL,
    paziente_id BIGINT NOT NULL,
    occhio TEXT,
    data_ordine TEXT,
    data_consegna_prev TEXT,
    data_consegna_eff TEXT,
    stato_ordine TEXT,
    fornitore TEXT,
    laboratorio TEXT,
    rif_laboratorio TEXT,
    parametri_json TEXT,
    costo_unitario DOUBLE PRECISION,
    costo_coppia DOUBLE PRECISION,
    iva_percent DOUBLE PRECISION,
    totale_fattura DOUBLE PRECISION,
    numero_fattura TEXT,
    pagamento_metodo TEXT,
    pagamento_stato TEXT,
    pagamento_data TEXT,
    note_ordine TEXT,
    created_at TEXT
)
"""

_SQL_SL_ORDINI = """
CREATE TABLE IF NOT EXISTS lac_ametropie_ordini (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scheda_id INTEGER NOT NULL, paziente_id INTEGER NOT NULL, occhio TEXT,
    data_ordine TEXT, data_consegna_prev TEXT, data_consegna_eff TEXT,
    stato_ordine TEXT, fornitore TEXT, laboratorio TEXT, rif_laboratorio TEXT,
    parametri_json TEXT, costo_unitario REAL, costo_coppia REAL,
    iva_percent REAL, totale_fattura REAL, numero_fattura TEXT,
    pagamento_metodo TEXT, pagamento_stato TEXT, pagamento_data TEXT,
    note_ordine TEXT, created_at TEXT
)
"""

_SQL_PG_VISITE = """
CREATE TABLE IF NOT EXISTS lac_ametropie_visite (
    id BIGSERIAL PRIMARY KEY,
    scheda_id BIGINT NOT NULL,
    paziente_id BIGINT NOT NULL,
    data_visita TEXT,
    tipo_visita TEXT,
    rx_post_od_sf DOUBLE PRECISION, rx_post_od_cil DOUBLE PRECISION,
    rx_post_od_ax INTEGER, rx_post_od_add DOUBLE PRECISION,
    rx_post_od_avsc_lon TEXT, rx_post_od_avsc_vic TEXT,
    rx_post_os_sf DOUBLE PRECISION, rx_post_os_cil DOUBLE PRECISION,
    rx_post_os_ax INTEGER, rx_post_os_add DOUBLE PRECISION,
    rx_post_os_avsc_lon TEXT, rx_post_os_avsc_vic TEXT,
    soddisfazione INTEGER,
    soddisfazione_vicino INTEGER,
    soddisfazione_lontano INTEGER,
    comfort INTEGER,
    operatore TEXT,
    note_visita TEXT,
    created_at TEXT
)
"""

_SQL_SL_VISITE = """
CREATE TABLE IF NOT EXISTS lac_ametropie_visite (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scheda_id INTEGER NOT NULL, paziente_id INTEGER NOT NULL,
    data_visita TEXT, tipo_visita TEXT,
    rx_post_od_sf REAL, rx_post_od_cil REAL, rx_post_od_ax INTEGER,
    rx_post_od_add REAL, rx_post_od_avsc_lon TEXT, rx_post_od_avsc_vic TEXT,
    rx_post_os_sf REAL, rx_post_os_cil REAL, rx_post_os_ax INTEGER,
    rx_post_os_add REAL, rx_post_os_avsc_lon TEXT, rx_post_os_avsc_vic TEXT,
    soddisfazione INTEGER, soddisfazione_vicino INTEGER,
    soddisfazione_lontano INTEGER, comfort INTEGER,
    operatore TEXT, note_visita TEXT, created_at TEXT
)
"""


def init_lac_ametropie_db(conn) -> None:
    pg = _is_postgres(conn)
    raw_conn = getattr(conn, "_conn", conn)
    try:
        cur = raw_conn.cursor()
    except Exception:
        cur = conn.cursor()
    if pg:
        cur.execute(_SQL_PG_SCHEDE)
        cur.execute(_SQL_PG_ORDINI)
        cur.execute(_SQL_PG_VISITE)
        for col, typ in [
            ("topo_asse_steep", "INTEGER"),
            ("rx_add", "DOUBLE PRECISION"),
            ("rx_miopia_equiv", "DOUBLE PRECISION"),
            ("rx_avsc_vic", "TEXT"), ("rx_avcc_vic", "TEXT"),
            ("rx_dominanza_oculare", "TEXT"),
            ("lente_sag_mm", "DOUBLE PRECISION"),
            ("lente_add_lente", "DOUBLE PRECISION"),
            ("lente_design_multifoc", "TEXT"),
            ("lente_cilindro", "DOUBLE PRECISION"),
            ("lente_asse_cil", "INTEGER"),
            ("lente_sostituzione", "TEXT"), ("lente_soluzione", "TEXT"),
            ("app_rotazione_gradi", "DOUBLE PRECISION"),
            ("app_stabilizzazione", "TEXT"),
        ]:
            try:
                cur.execute(f"ALTER TABLE lac_ametropie ADD COLUMN IF NOT EXISTS {col} {typ}")
            except Exception:
                pass
    else:
        cur.execute(_SQL_SL_SCHEDE)
        cur.execute(_SQL_SL_ORDINI)
        cur.execute(_SQL_SL_VISITE)
    conn.commit()


# ---------------------------------------------------------------------------
# UI principale
# ---------------------------------------------------------------------------

def ui_lac_ametropie():
    st.header("LAC - Ipermetropia / Astigmatismo / Presbiopia")

    conn = _get_conn()
    init_lac_ametropie_db(conn)
    cur = conn.cursor()

    try:
        cur.execute('SELECT id, "Cognome", "Nome" FROM "Pazienti" ORDER BY "Cognome", "Nome"')
        pazienti = cur.fetchall()
    except Exception:
        try:
            cur.execute("SELECT id, Cognome, Nome FROM Pazienti ORDER BY Cognome, Nome")
            pazienti = cur.fetchall()
        except Exception as e:
            st.error(f"Errore accesso tabella Pazienti: {e}")
            return

    if not pazienti:
        st.info("Nessun paziente registrato.")
        return

    options = [f"{_row_get(p,'id')} - {_row_get(p,'Cognome','')} {_row_get(p,'Nome','')}".strip() for p in pazienti]
    sel    = st.selectbox("Seleziona paziente", options, key="lam_paz_sel")
    paz_id = int(sel.split(" - ", 1)[0])
    st.divider()

    tab1, tab2, tab3, tab4 = st.tabs([
        "Nuova Scheda", "Schede Esistenti", "Ordini", "Visite di Controllo"])
    with tab1: _ui_nuova_scheda(conn, cur, paz_id)
    with tab2: _ui_storico(conn, cur, paz_id)
    with tab3: _ui_ordini(conn, cur, paz_id)
    with tab4: _ui_visite(conn, cur, paz_id)


# ---------------------------------------------------------------------------
# Tab: Nuova scheda
# ---------------------------------------------------------------------------

def _ui_nuova_scheda(conn, cur, paz_id):
    st.subheader("Nuova scheda LAC")

    with st.form("form_lac_ametropie"):

        # Intestazione
        h1, h2, h3 = st.columns(3)
        with h1: occhio      = st.selectbox("Occhio", ["OD","OS","OD+OS"], key="lam_occhio")
        with h2: ametropia   = st.selectbox("Tipo ametropia", TIPI_AMETROPIA, key="lam_ametropia")
        with h3: data_scheda = st.text_input("Data scheda (gg/mm/aaaa)", _today_str(), key="lam_data")

        tipo_lente = st.selectbox("Tipo di lente", TIPI_LENTE, key="lam_tipo_lente")

        # ── TOPOGRAFIA ──────────────────────────────────────────────────
        st.markdown("### Topografia corneale")
        c1,c2,c3,c4,c5 = st.columns(5)
        with c1:
            topo_k_flat_mm = st.number_input("K flat (mm)", 6.0, 9.5, 7.80, 0.01, key="lam_kflat_mm")
            st.caption(f"= {r_to_d(topo_k_flat_mm):.2f} D")
        with c2:
            topo_k_flat_D = st.number_input("K flat (D)", 35.0, 52.0, r_to_d(st.session_state.get("lam_kflat_mm",7.80)), 0.25, key="lam_kflat_D")
            st.caption(f"= {d_to_r(topo_k_flat_D):.3f} mm")
        with c3:
            topo_k_steep_mm = st.number_input("K steep (mm)", 6.0, 9.5, 7.70, 0.01, key="lam_ksteep_mm")
            st.caption(f"= {r_to_d(topo_k_steep_mm):.2f} D")
        with c4:
            topo_k_steep_D = st.number_input("K steep (D)", 35.0, 52.0, r_to_d(st.session_state.get("lam_ksteep_mm",7.70)), 0.25, key="lam_ksteep_D")
            st.caption(f"= {d_to_r(topo_k_steep_D):.3f} mm")
        with c5: topo_asse_steep = st.number_input("Asse steep (gradi)", 0, 180, 90, 1,     key="lam_asse_steep")

        c6,c7,c8,c9 = st.columns(4)
        with c6: topo_ecc_media = st.number_input("Eccentricita media", 0.0, 1.5, 0.50, 0.01, key="lam_ecc_media")
        with c7: topo_raggio_mm = st.number_input("Raggio apicale (mm)", 6.0, 9.5, 7.80, 0.01, key="lam_raggio_ap")
        with c8: topo_dev_r     = st.number_input("Dev.Std raggio", 0.0, 0.5, 0.05, 0.001, format="%.3f", key="lam_dev_r")
        with c9: topo_dev_e     = st.number_input("Dev.Std ecc.", 0.0, 0.5, 0.02, 0.001, format="%.3f", key="lam_dev_e")

        ct1, ct2 = st.columns(2)
        with ct1: topo_topografo = st.text_input("Topografo", "", key="lam_topografo")
        with ct2: topo_data      = st.text_input("Data topografia (gg/mm/aaaa)", _today_str(), key="lam_topo_data")

        st.caption("Misurazioni individuali (opzionale)")
        mis_cols = st.columns(4)
        misurazioni = []
        for i in range(4):
            with mis_cols[i]:
                mer = st.text_input(f"Meridiano {i+1}", "", key=f"lam_mer_{i}")
                ra  = st.number_input(f"Raggio {i+1} mm", 6.0, 9.5, 7.80, 0.01, key=f"lam_ra_{i}")
                ec  = st.number_input(f"Ecc. {i+1}", 0.0, 1.5, 0.50, 0.01, key=f"lam_ec_{i}")
                if mer.strip():
                    misurazioni.append({"meridiano": mer, "raggio_mm": ra, "eccentricita": ec})

        # ── REFRAZIONE ──────────────────────────────────────────────────
        st.markdown("### Refrazione")
        r1,r2,r3,r4 = st.columns(4)
        with r1: rx_sf  = st.number_input("Sfera (D)", -10.0, 20.0, 0.0, 0.25, key="lam_rx_sf")
        with r2: rx_cil = st.number_input("Cilindro (D)", -8.0, 8.0, 0.0, 0.25, key="lam_rx_cil")
        with r3: rx_ax  = st.number_input("Asse gradi", 0, 180, 0, 1,           key="lam_rx_ax")
        with r4: rx_add = st.number_input("ADD (D) – presbiopia", 0.0, 4.0, 0.0, 0.25, key="lam_rx_add")

        r5,r6 = st.columns(2)
        with r5: rx_equiv = st.number_input("Equivalente sferico (D)", -15.0, 20.0, 0.0, 0.25, key="lam_rx_equiv")
        with r6: rx_dom   = st.selectbox("Occhio dominante", ["—","OD","OS"], key="lam_rx_dom")

        st.markdown("**Acuita visiva**")
        av1,av2,av3,av4 = st.columns(4)
        with av1: rx_avsc_lon = st.text_input("AVSC lontano", "", key="lam_avsc_lon")
        with av2: rx_avcc_lon = st.text_input("AVCC lontano", "", key="lam_avcc_lon")
        with av3: rx_avsc_vic = st.text_input("AVSC vicino", "", key="lam_avsc_vic")
        with av4: rx_avcc_vic = st.text_input("AVCC vicino", "", key="lam_avcc_vic")

        # ── PARAMETRI LENTE ─────────────────────────────────────────────
        st.markdown("### Parametri lente")

        lp1,lp2,lp3,lp4 = st.columns(4)
        with lp1: lente_rb   = st.number_input("Raggio base (mm)", 7.0, 10.5, 8.60, 0.01, format="%.2f", key="lam_rb")
        with lp2: lente_diam = st.number_input("Diametro (mm)", 8.0, 22.0, 14.0, 0.1,                    key="lam_diam")
        with lp3: lente_potere_lon = st.number_input("Potere lontano (D)", -20.0, 20.0, 0.0, 0.25,       key="lam_pot_lon")
        with lp4: lente_potere_vic = st.number_input("Potere vicino (D)", -20.0, 20.0, 0.0, 0.25,        key="lam_pot_vic")

        lp5,lp6,lp7,lp8 = st.columns(4)
        with lp5: lente_add      = st.number_input("ADD lente (D)", 0.0, 4.0, 0.0, 0.25,                 key="lam_add_lente")
        with lp6: lente_design   = st.selectbox("Design multifocale", DESIGN_MULTIFOCALE,                 key="lam_design")
        with lp7: lente_cil      = st.number_input("Cilindro lente (D)", -8.0, 8.0, 0.0, 0.25,           key="lam_cil_lente")
        with lp8: lente_asse_cil = st.number_input("Asse cil. lente (gradi)", 0, 180, 0, 1,              key="lam_asse_cil")

        lp9,lp10,lp11 = st.columns(3)
        with lp9:  lente_zo        = st.number_input("Zona ottica (mm)", 4.0, 12.0, 8.0, 0.1,            key="lam_zo")
        with lp10: lente_sag       = st.number_input("Sagitta (mm) – sclerali", 0.0, 8.0, 0.0, 0.01, format="%.2f", key="lam_sag")
        with lp11: lente_clearance = st.number_input("Clearance (mm)", 0.0, 1.0, 0.0, 0.001, format="%.3f", key="lam_clearance")

        lp12,lp13,lp14,lp15 = st.columns(4)
        with lp12: lente_materiale   = st.text_input("Materiale", "", key="lam_materiale")
        with lp13: lente_dk          = st.number_input("DK", 0.0, 200.0, 100.0, 1.0,                     key="lam_dk")
        with lp14: lente_sostituzione = st.selectbox("Sostituzione", ["giornaliera","quindicinale","mensile","trimestrale","annuale","altro"], key="lam_sost")
        with lp15: lente_soluzione    = st.text_input("Soluzione/sistema", "", key="lam_sol")

        lente_puntino = st.checkbox("Puntino di centratura OD", key="lam_puntino")
        lente_note    = st.text_area("Note lente", "", key="lam_lente_note")

        # ── APPOGGIO LAC ────────────────────────────────────────────────
        st.markdown("### Appoggio LAC sulla cornea")

        aa1, aa2 = st.columns(2)
        with aa1:
            app_data  = st.text_input("Data valutazione (gg/mm/aaaa)", _today_str(), key="lam_app_data")
            app_tipo  = st.selectbox("Tipo appoggio", TIPI_APPOGGIO,   key="lam_app_tipo")
            app_cen   = st.number_input("Clearance centrale (um)",  0.0, 500.0, 0.0, 1.0, key="lam_app_cen")
            app_per   = st.number_input("Clearance periferica (um)", 0.0, 500.0, 0.0, 1.0, key="lam_app_per")
            app_rot   = st.number_input("Rotazione lente torica (gradi)", -180.0, 180.0, 0.0, 0.5, key="lam_app_rot")
        with aa2:
            app_pattern     = st.selectbox("Pattern fluoresceinogramma", PATTERN_FLUOR, key="lam_pattern")
            app_centratura  = st.selectbox("Centratura", CENTRATURA,                   key="lam_centratura")
            app_mov         = st.number_input("Movimento ammiccamento (mm)", 0.0, 5.0, 0.0, 0.1, key="lam_mov")
            app_stabiliz    = st.selectbox("Stabilizzazione torica", ["—","buona","scarsa","eccessiva","inversione"], key="lam_stabiliz")
            app_valutazione = st.selectbox("Valutazione globale", VALUTAZIONE, key="lam_valut")

        app_modifiche = st.text_input("Modifiche suggerite", "", key="lam_modifiche")
        app_operatore = st.text_input("Operatore", "", key="lam_operatore")
        app_note_fl   = st.text_area("Note fluoresceinogramma", "", key="lam_note_fl")
        app_note      = st.text_area("Note appoggio", "", key="lam_app_note")

        submitted = st.form_submit_button("Salva scheda LAC")

    if submitted:
        now_iso = datetime.now().isoformat(timespec="seconds")
        params = (
            paz_id, occhio, _parse_date(data_scheda) or date.today().isoformat(),
            ametropia, tipo_lente,
            topo_k_flat_mm, topo_k_flat_D, topo_k_steep_mm, topo_k_steep_D, int(topo_asse_steep),
            topo_ecc_media, topo_raggio_mm, topo_dev_r, topo_dev_e,
            topo_topografo, _parse_date(topo_data),
            json.dumps(misurazioni, ensure_ascii=False),
            rx_sf, rx_cil, int(rx_ax), rx_add, rx_equiv,
            rx_avsc_lon, rx_avcc_lon, rx_avsc_vic, rx_avcc_vic, rx_dom,
            lente_rb, lente_diam, lente_potere_lon, lente_potere_vic, lente_add,
            lente_design, lente_cil, int(lente_asse_cil),
            lente_zo, lente_sag, lente_clearance,
            lente_materiale, lente_dk, lente_sostituzione, lente_soluzione,
            1 if lente_puntino else 0, lente_note,
            _parse_date(app_data), app_tipo, app_cen, app_per,
            app_pattern, app_centratura, app_mov, app_rot, app_stabiliz,
            app_valutazione, app_modifiche, app_operatore, app_note_fl, app_note,
            now_iso, now_iso,
        )
        ph = _ph(len(params), conn)
        sql = (
            "INSERT INTO lac_ametropie ("
            "paziente_id,occhio,data_scheda,ametropia,tipo_lente,"
            "topo_k_flat_mm,topo_k_flat_d,topo_k_steep_mm,topo_k_steep_d,topo_asse_steep,"
            "topo_ecc_media,topo_raggio_apicale_mm,topo_dev_std_raggio,topo_dev_std_ecc,"
            "topo_topografo,topo_data,topo_misurazioni_json,"
            "rx_sfera,rx_cilindro,rx_asse,rx_add,rx_miopia_equiv,"
            "rx_avsc_lon,rx_avcc_lon,rx_avsc_vic,rx_avcc_vic,rx_dominanza_oculare,"
            "lente_rb_mm,lente_diam_mm,lente_potere_lon_d,lente_potere_vic_d,lente_add_lente,"
            "lente_design_multifoc,lente_cilindro,lente_asse_cil,"
            "lente_zo_mm,lente_sag_mm,lente_clearance_mm,"
            "lente_materiale,lente_dk,lente_sostituzione,lente_soluzione,"
            "lente_puntino,lente_note,"
            "app_data,app_tipo,app_clearance_centrale,app_clearance_periferica,"
            "app_pattern,app_centratura,app_movimento_mm,app_rotazione_gradi,app_stabilizzazione,"
            "app_valutazione,app_modifiche,app_operatore,app_note_fluoresceina,app_note,"
            "created_at,updated_at"
            f") VALUES ({ph})"
        )
        try:
            cur.execute(sql, params)
            conn.commit()
            st.success(f"Scheda LAC {occhio} – {ametropia} salvata.")
        except Exception as e:
            st.error(f"Errore salvataggio: {e}")


# ---------------------------------------------------------------------------
# Tab: Schede esistenti
# ---------------------------------------------------------------------------

def _ui_storico(conn, cur, paz_id):
    st.subheader("Schede LAC esistenti")
    ph1 = _ph(1, conn)
    try:
        cur.execute(
            "SELECT * FROM lac_ametropie WHERE paziente_id = " + ph1 + " ORDER BY data_scheda DESC, id DESC",
            (paz_id,))
        schede = cur.fetchall()
    except Exception as e:
        st.error(f"Errore: {e}")
        return

    if not schede:
        st.info("Nessuna scheda LAC per questo paziente.")
        return

    for s in schede:
        sid      = _row_get(s, "id")
        occhio   = _row_get(s, "occhio", "?")
        ametr    = _row_get(s, "ametropia", "")
        tipo_l   = _row_get(s, "tipo_lente", "")
        data_s   = _row_get(s, "data_scheda", "")
        rb       = _row_get(s, "lente_rb_mm")
        diam     = _row_get(s, "lente_diam_mm")
        pot_lon  = _row_get(s, "lente_potere_lon_d")
        add_l    = _row_get(s, "lente_add_lente")
        mat      = _row_get(s, "lente_materiale", "")

        label = f"{occhio} | {data_s} | {ametr} | {tipo_l} | Rb={rb} | Diam={diam} | {pot_lon:+.2f}D | {mat}" if rb and pot_lon else f"{occhio} | {data_s} | {ametr} | {tipo_l}"
        with st.expander(label):
            c1,c2,c3,c4 = st.columns(4)
            c1.metric("Rb (mm)",     f"{rb:.2f}"      if rb      else "—")
            c2.metric("Diam (mm)",   f"{diam:.1f}"    if diam    else "—")
            c3.metric("Pot. lon (D)",f"{pot_lon:+.2f}" if pot_lon else "—")
            c4.metric("ADD lente",   f"{add_l:+.2f}"  if add_l   else "—")

            st.markdown("#### Refrazione")
            rf1,rf2,rf3,rf4 = st.columns(4)
            sf = _row_get(s,"rx_sfera"); ci = _row_get(s,"rx_cilindro")
            ax = _row_get(s,"rx_asse");  ad = _row_get(s,"rx_add")
            rf1.metric("Sfera",    f"{sf:+.2f}" if sf is not None else "—")
            rf2.metric("Cilindro", f"{ci:+.2f}" if ci is not None else "—")
            rf3.metric("Asse",     str(ax)      if ax is not None else "—")
            rf4.metric("ADD",      f"{ad:+.2f}" if ad             else "—")

            st.markdown("#### Topografia")
            t1,t2,t3,t4 = st.columns(4)
            kfm=_row_get(s,"topo_k_flat_mm"); ksm=_row_get(s,"topo_k_steep_mm")
            em=_row_get(s,"topo_ecc_media");  ast_top=_row_get(s,"topo_asse_steep")
            t1.metric("K flat", f"{kfm:.2f}" if kfm else "—")
            t2.metric("K steep",f"{ksm:.2f}" if ksm else "—")
            t3.metric("Ecc",    f"{em:.2f}"  if em  else "—")
            t4.metric("Asse steep", str(ast_top) if ast_top else "—")

            st.markdown("#### Appoggio")
            aa1,aa2,aa3,aa4 = st.columns(4)
            aa1.metric("Tipo",         _row_get(s,"app_tipo","—"))
            aa2.metric("Pattern",      _row_get(s,"app_pattern","—"))
            aa3.metric("Valutazione",  _row_get(s,"app_valutazione","—"))
            aa4.metric("Rotazione",    f"{_row_get(s,'app_rotazione_gradi',0) or 0:.1f} gradi")

            st.markdown(f"**Design multifocale:** {_row_get(s,'lente_design_multifoc','—')} | "
                        f"**Sostituzione:** {_row_get(s,'lente_sostituzione','—')} | "
                        f"**Soluzione:** {_row_get(s,'lente_soluzione','—')}")
            st.markdown(f"**Note lente:** {_row_get(s,'lente_note','') or '—'}")
            st.markdown(f"**Note appoggio:** {_row_get(s,'app_note','') or '—'}")

            if st.button(f"Elimina scheda #{sid}", key=f"lam_del_{sid}"):
                try:
                    cur.execute("DELETE FROM lac_ametropie WHERE id = " + ph1, (sid,))
                    conn.commit()
                    st.warning("Scheda eliminata.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore: {e}")


# ---------------------------------------------------------------------------
# Tab: Ordini
# ---------------------------------------------------------------------------

def _ui_ordini(conn, cur, paz_id):
    st.subheader("Storico ordini LAC")
    ph1 = _ph(1, conn)

    cur.execute(
        "SELECT id,occhio,data_scheda,ametropia,tipo_lente,lente_rb_mm,lente_diam_mm FROM lac_ametropie WHERE paziente_id = " + ph1 + " ORDER BY data_scheda DESC",
        (paz_id,))
    schede = cur.fetchall()

    with st.form("form_lac_ordine"):
        st.markdown("#### Nuovo ordine")
        if not schede:
            st.info("Crea prima una scheda LAC.")
            st.form_submit_button("Salva ordine", disabled=True)
            return

        scheda_opts = [f"#{_row_get(s,'id')} {_row_get(s,'occhio')} | {_row_get(s,'ametropia')} | {_row_get(s,'tipo_lente')} | {_row_get(s,'data_scheda')}" for s in schede]
        sel_scheda = st.selectbox("Scheda", scheda_opts, key="lam_ord_scheda")
        scheda_id  = int(sel_scheda.split("#")[1].split(" ")[0])

        o1,o2,o3 = st.columns(3)
        with o1:
            ord_occhio    = st.selectbox("Occhio", ["OD","OS","OD+OS"], key="lam_ord_occhio")
            ord_data      = st.text_input("Data ordine", _today_str(), key="lam_ord_data")
            ord_data_prev = st.text_input("Consegna prevista", "", key="lam_ord_prev")
        with o2:
            ord_fornitore   = st.text_input("Fornitore", "", key="lam_ord_forn")
            ord_laboratorio = st.text_input("Laboratorio", "", key="lam_ord_lab")
            ord_rif         = st.text_input("Rif. lab", "", key="lam_ord_rif")
        with o3:
            ord_stato    = st.selectbox("Stato", ["in_lavorazione","spedito","consegnato","reso","annullato"], key="lam_ord_stato")
            ord_data_eff = st.text_input("Consegna effettiva", "", key="lam_ord_eff")

        st.markdown("**Parametri ordinati**")
        pp1,pp2,pp3,pp4,pp5 = st.columns(5)
        with pp1: p_rb      = st.number_input("Rb mm",   7.0, 10.5, 8.60, 0.01, format="%.2f", key="lam_ord_rb")
        with pp2: p_diam    = st.number_input("Diam mm", 8.0, 22.0, 14.0, 0.1,                 key="lam_ord_diam")
        with pp3: p_pot_lon = st.number_input("Pot. lon D", -20.0, 20.0, 0.0, 0.25,            key="lam_ord_pot_lon")
        with pp4: p_add     = st.number_input("ADD D",    0.0, 4.0, 0.0, 0.25,                 key="lam_ord_add")
        with pp5: p_mat     = st.text_input("Materiale", "", key="lam_ord_mat")

        pp6,pp7,pp8 = st.columns(3)
        with pp6: p_cil  = st.number_input("Cilindro D", -8.0, 8.0, 0.0, 0.25,                key="lam_ord_cil")
        with pp7: p_ax   = st.number_input("Asse cil.", 0, 180, 0, 1,                          key="lam_ord_ax")
        with pp8: p_sost = st.selectbox("Sostituzione", ["giornaliera","quindicinale","mensile","trimestrale","annuale","altro"], key="lam_ord_sost")
        p_note = st.text_area("Note parametri", "", key="lam_ord_pnote")

        st.markdown("**Costi e fattura**")
        cc1,cc2,cc3,cc4 = st.columns(4)
        with cc1: costo_u  = st.number_input("Costo unit EUR", 0.0, 500.0, 0.0, 0.5,  key="lam_ord_cu")
        with cc2: costo_cp = st.number_input("Costo coppia EUR", 0.0, 1000.0, 0.0, 1.0, key="lam_ord_cp")
        with cc3: iva      = st.number_input("IVA perc", 0.0, 25.0, 22.0, 0.5,        key="lam_ord_iva")
        with cc4: tot_fatt = st.number_input("Totale EUR", 0.0, 2000.0, 0.0, 1.0,     key="lam_ord_tot")

        f1,f2 = st.columns(2)
        with f1: num_fatt  = st.text_input("N fattura", "", key="lam_ord_nfatt")
        with f2: pag_met   = st.selectbox("Metodo pag", ["contante","carta","bonifico","rateizzato"], key="lam_ord_pmet")

        p1,p2,p3 = st.columns(3)
        with p1: pag_stato = st.selectbox("Stato pag", ["da_pagare","pagato","parziale"], key="lam_ord_pst")
        with p2: pag_data  = st.text_input("Data pagamento", "", key="lam_ord_pdata")
        with p3: ord_note  = st.text_area("Note", "", key="lam_ord_note")

        sub_ord = st.form_submit_button("Salva ordine")

    if sub_ord:
        now_iso = datetime.now().isoformat(timespec="seconds")
        pj = json.dumps({"rb_mm": p_rb, "diam_mm": p_diam, "potere_lon_d": p_pot_lon,
                          "add_d": p_add, "cilindro": p_cil, "asse_cil": int(p_ax),
                          "materiale": p_mat, "sostituzione": p_sost, "note": p_note}, ensure_ascii=False)
        params = (scheda_id, paz_id, ord_occhio,
                  _parse_date(ord_data), _parse_date(ord_data_prev), _parse_date(ord_data_eff), ord_stato,
                  ord_fornitore, ord_laboratorio, ord_rif, pj,
                  costo_u, costo_cp, iva, tot_fatt,
                  num_fatt, pag_met, pag_stato, _parse_date(pag_data),
                  ord_note, now_iso)
        ph = _ph(len(params), conn)
        sql = (
            "INSERT INTO lac_ametropie_ordini ("
            "scheda_id,paziente_id,occhio,data_ordine,data_consegna_prev,data_consegna_eff,stato_ordine,"
            "fornitore,laboratorio,rif_laboratorio,parametri_json,costo_unitario,costo_coppia,"
            "iva_percent,totale_fattura,numero_fattura,pagamento_metodo,pagamento_stato,"
            f"pagamento_data,note_ordine,created_at) VALUES ({ph})"
        )
        try:
            cur.execute(sql, params)
            conn.commit()
            st.success("Ordine salvato.")
        except Exception as e:
            st.error(f"Errore: {e}")

    st.divider()
    st.markdown("#### Ordini registrati")
    cur.execute(
        "SELECT * FROM lac_ametropie_ordini WHERE paziente_id = " + ph1 + " ORDER BY data_ordine DESC, id DESC",
        (paz_id,))
    for o in cur.fetchall():
        oid = _row_get(o, "id")
        tot = _row_get(o, "totale_fattura", 0) or 0
        with st.expander(f"#{oid} | {_row_get(o,'occhio','')} | {_row_get(o,'data_ordine','')} | {_row_get(o,'fornitore','')} | {_row_get(o,'stato_ordine','')} | EUR {tot:.2f}"):
            pc = json.loads(_row_get(o, "parametri_json", "{}") or "{}")
            st.write(f"Rb={pc.get('rb_mm','?')} | Diam={pc.get('diam_mm','?')} | Pot={pc.get('potere_lon_d','?')}D | ADD={pc.get('add_d','?')}D | Mat={pc.get('materiale','—')}")
            st.write(f"Cil={pc.get('cilindro','?')} ax {pc.get('asse_cil','?')} | Sost={pc.get('sostituzione','—')}")
            st.write(f"Fattura: {_row_get(o,'numero_fattura','—')} | {_row_get(o,'pagamento_metodo','')} – {_row_get(o,'pagamento_stato','')}")
            if st.button(f"Elimina ordine #{oid}", key=f"lam_del_ord_{oid}"):
                try:
                    cur.execute("DELETE FROM lac_ametropie_ordini WHERE id = " + ph1, (oid,))
                    conn.commit()
                    st.warning("Ordine eliminato.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore: {e}")


# ---------------------------------------------------------------------------
# Tab: Visite di controllo
# ---------------------------------------------------------------------------

def _ui_visite(conn, cur, paz_id):
    st.subheader("Visite di controllo")
    ph1 = _ph(1, conn)

    cur.execute(
        "SELECT id,occhio,ametropia,tipo_lente,data_scheda FROM lac_ametropie WHERE paziente_id = " + ph1 + " ORDER BY data_scheda DESC",
        (paz_id,))
    schede = cur.fetchall()

    with st.form("form_lac_visita"):
        st.markdown("#### Nuova visita")
        if not schede:
            st.info("Crea prima una scheda LAC.")
            st.form_submit_button("Salva visita", disabled=True)
            return

        scheda_opts = [f"#{_row_get(s,'id')} {_row_get(s,'occhio')} | {_row_get(s,'ametropia')} | {_row_get(s,'data_scheda')}" for s in schede]
        sel_s     = st.selectbox("Scheda", scheda_opts, key="lam_vis_scheda")
        scheda_id = int(sel_s.split("#")[1].split(" ")[0])

        v1,v2 = st.columns(2)
        with v1:
            vis_data = st.text_input("Data visita", _today_str(), key="lam_vis_data")
            vis_tipo = st.selectbox("Tipo visita", [
                "prima_applicazione","controllo_1_settimana","controllo_1_mese",
                "controllo_3_mesi","controllo_6_mesi","controllo_annuale",
                "adattamento_presbiopia","verifica_monovisione","urgenza","altro"],
                key="lam_vis_tipo")
            vis_op = st.text_input("Operatore", "", key="lam_vis_op")
        with v2:
            vis_sodd     = st.slider("Soddisfazione globale 1-10", 1, 10, 8, key="lam_vis_sodd")
            vis_sodd_lon = st.slider("Soddisfazione lontano 1-10", 1, 10, 8, key="lam_vis_sodd_lon")
            vis_sodd_vic = st.slider("Soddisfazione vicino 1-10",  1, 10, 8, key="lam_vis_sodd_vic")
            vis_comfort  = st.slider("Comfort lente 1-10",         1, 10, 8, key="lam_vis_comfort")

        st.markdown("**Refrazione post-applicazione**")
        st.caption("OD")
        rx1,rx2,rx3,rx4,rx5,rx6 = st.columns(6)
        with rx1: v_od_sf   = st.number_input("OD SF",  -10.0, 20.0, 0.0, 0.25, key="lam_vis_od_sf")
        with rx2: v_od_cil  = st.number_input("OD CIL",  -8.0,  8.0, 0.0, 0.25, key="lam_vis_od_cil")
        with rx3: v_od_ax   = st.number_input("OD AX",      0,  180,   0,    1,  key="lam_vis_od_ax")
        with rx4: v_od_add  = st.number_input("OD ADD",   0.0,  4.0, 0.0, 0.25,  key="lam_vis_od_add")
        with rx5: v_od_avsc_lon = st.text_input("OD AVSC lon", "", key="lam_vis_od_avsc_lon")
        with rx6: v_od_avsc_vic = st.text_input("OD AVSC vic", "", key="lam_vis_od_avsc_vic")

        st.caption("OS")
        rx7,rx8,rx9,rx10,rx11,rx12 = st.columns(6)
        with rx7:  v_os_sf   = st.number_input("OS SF",  -10.0, 20.0, 0.0, 0.25, key="lam_vis_os_sf")
        with rx8:  v_os_cil  = st.number_input("OS CIL",  -8.0,  8.0, 0.0, 0.25, key="lam_vis_os_cil")
        with rx9:  v_os_ax   = st.number_input("OS AX",      0,  180,   0,    1,  key="lam_vis_os_ax")
        with rx10: v_os_add  = st.number_input("OS ADD",   0.0,  4.0, 0.0, 0.25,  key="lam_vis_os_add")
        with rx11: v_os_avsc_lon = st.text_input("OS AVSC lon", "", key="lam_vis_os_avsc_lon")
        with rx12: v_os_avsc_vic = st.text_input("OS AVSC vic", "", key="lam_vis_os_avsc_vic")

        vis_note = st.text_area("Note visita", "", key="lam_vis_note")
        sub_vis  = st.form_submit_button("Salva visita")

    if sub_vis:
        now_iso = datetime.now().isoformat(timespec="seconds")
        params = (scheda_id, paz_id, _parse_date(vis_data), vis_tipo,
                  v_od_sf, v_od_cil, int(v_od_ax), v_od_add, v_od_avsc_lon, v_od_avsc_vic,
                  v_os_sf, v_os_cil, int(v_os_ax), v_os_add, v_os_avsc_lon, v_os_avsc_vic,
                  vis_sodd, vis_sodd_vic, vis_sodd_lon, vis_comfort,
                  vis_op, vis_note, now_iso)
        ph = _ph(len(params), conn)
        sql = (
            "INSERT INTO lac_ametropie_visite ("
            "scheda_id,paziente_id,data_visita,tipo_visita,"
            "rx_post_od_sf,rx_post_od_cil,rx_post_od_ax,rx_post_od_add,rx_post_od_avsc_lon,rx_post_od_avsc_vic,"
            "rx_post_os_sf,rx_post_os_cil,rx_post_os_ax,rx_post_os_add,rx_post_os_avsc_lon,rx_post_os_avsc_vic,"
            "soddisfazione,soddisfazione_vicino,soddisfazione_lontano,comfort,"
            f"operatore,note_visita,created_at) VALUES ({ph})"
        )
        try:
            cur.execute(sql, params)
            conn.commit()
            st.success("Visita salvata.")
        except Exception as e:
            st.error(f"Errore: {e}")

    st.divider()
    st.markdown("#### Visite registrate")
    cur.execute(
        "SELECT * FROM lac_ametropie_visite WHERE paziente_id = " + ph1 + " ORDER BY data_visita DESC, id DESC",
        (paz_id,))
    for v in cur.fetchall():
        vid  = _row_get(v, "id")
        sodd = _row_get(v, "soddisfazione", "?")
        sl   = _row_get(v, "soddisfazione_lontano", "?")
        sv   = _row_get(v, "soddisfazione_vicino", "?")
        com  = _row_get(v, "comfort", "?")
        with st.expander(f"#{vid} | {_row_get(v,'data_visita','')} | {_row_get(v,'tipo_visita','')} | Globale {sodd}/10 | Lon {sl}/10 | Vic {sv}/10 | Comfort {com}/10"):
            c1,c2,c3,c4 = st.columns(4)
            c1.metric("OD AVSC lon", _row_get(v,"rx_post_od_avsc_lon","—"))
            c2.metric("OD AVSC vic", _row_get(v,"rx_post_od_avsc_vic","—"))
            c3.metric("OS AVSC lon", _row_get(v,"rx_post_os_avsc_lon","—"))
            c4.metric("OS AVSC vic", _row_get(v,"rx_post_os_avsc_vic","—"))
            od_add = _row_get(v,"rx_post_od_add"); os_add = _row_get(v,"rx_post_os_add")
            if od_add or os_add:
                c5,c6 = st.columns(2)
                c5.metric("ADD OD", f"{od_add:+.2f}" if od_add else "—")
                c6.metric("ADD OS", f"{os_add:+.2f}" if os_add else "—")
            st.write(f"Note: {_row_get(v,'note_visita','') or '—'}")
            if st.button(f"Elimina visita #{vid}", key=f"lam_del_vis_{vid}"):
                try:
                    cur.execute("DELETE FROM lac_ametropie_visite WHERE id = " + ph1, (vid,))
                    conn.commit()
                    st.warning("Visita eliminata.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore: {e}")
