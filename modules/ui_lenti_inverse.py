# -*- coding: utf-8 -*-
"""
Modulo: Lenti Inverse / Ortocheratologia
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
# Helpers
# ---------------------------------------------------------------------------

def _is_postgres(conn) -> bool:
    """Rileva PostgreSQL senza fare query (evita loop con _PgCursor)."""
    # 1) controlla il tipo della connessione/cursor
    t = type(conn).__name__
    if "Pg" in t or "pg" in t:
        return True
    # 2) prova a leggere _DB_BACKEND da app_patched (root del progetto)
    try:
        import sys, os
        # aggiungi la root del progetto al path se non c'è
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if root not in sys.path:
            sys.path.insert(0, root)
        from app_patched import _DB_BACKEND
        return _DB_BACKEND == "postgres"
    except Exception:
        pass
    # 3) controlla se psycopg2 è coinvolto guardando il modulo della connessione
    try:
        mod = type(conn).__module__ or ""
        if "psycopg2" in mod or "psycopg" in mod:
            return True
    except Exception:
        pass
    # 4) controlla se il cursore è un _PgCursor (wrapper definito in app_patched)
    try:
        cur = conn.cursor()
        cur_type = type(cur).__name__
        if "Pg" in cur_type:
            return True
    except Exception:
        pass
    return False


def _ph(n: int, conn) -> str:
    """n placeholder separati da virgola."""
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
            return datetime.strptime(s.strip(), fmt).strftime("%Y-%m-%d")
        except Exception:
            pass
    return ""


# ---------------------------------------------------------------------------
# DB init
# ---------------------------------------------------------------------------

_SQL_CREATE_PG = """
CREATE TABLE IF NOT EXISTS lenti_inverse (
    id BIGSERIAL PRIMARY KEY,
    paziente_id BIGINT NOT NULL,
    occhio TEXT NOT NULL,
    data_scheda TEXT,
    topo_k_flat_mm DOUBLE PRECISION,
    topo_k_flat_d DOUBLE PRECISION,
    topo_k_steep_mm DOUBLE PRECISION,
    topo_k_steep_d DOUBLE PRECISION,
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
    rx_miopia_tot DOUBLE PRECISION,
    rx_miopia_ridurre DOUBLE PRECISION,
    rx_avsc TEXT,
    rx_avcc TEXT,
    lente_tipo_zo TEXT,
    lente_r0_mm DOUBLE PRECISION,
    lente_rb_mm DOUBLE PRECISION,
    lente_ecc_zo DOUBLE PRECISION,
    lente_fattore_p DOUBLE PRECISION,
    lente_fattore_appiatt DOUBLE PRECISION,
    lente_zo_diam_mm DOUBLE PRECISION,
    lente_clearance_mm DOUBLE PRECISION,
    lente_c0 DOUBLE PRECISION,
    lente_c1 DOUBLE PRECISION,
    lente_c2 DOUBLE PRECISION,
    lente_c3 DOUBLE PRECISION,
    lente_c4 DOUBLE PRECISION,
    lente_c5 DOUBLE PRECISION,
    lente_c6 DOUBLE PRECISION,
    lente_flange_json TEXT,
    lente_diam_tot_mm DOUBLE PRECISION,
    lente_potere_d DOUBLE PRECISION,
    lente_materiale TEXT,
    lente_dk DOUBLE PRECISION,
    lente_puntino INTEGER DEFAULT 0,
    lente_note TEXT,
    app_data TEXT,
    app_tipo TEXT,
    app_clearance_centrale DOUBLE PRECISION,
    app_clearance_periferica DOUBLE PRECISION,
    app_pattern TEXT,
    app_centratura TEXT,
    app_movimento_mm DOUBLE PRECISION,
    app_valutazione TEXT,
    app_modifiche TEXT,
    app_operatore TEXT,
    app_note_fluoresceina TEXT,
    app_note TEXT,
    created_at TEXT,
    updated_at TEXT
)
"""

_SQL_CREATE_PG_ORDINI = """
CREATE TABLE IF NOT EXISTS lenti_inverse_ordini (
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

_SQL_CREATE_PG_VISITE = """
CREATE TABLE IF NOT EXISTS lenti_inverse_visite (
    id BIGSERIAL PRIMARY KEY,
    scheda_id BIGINT NOT NULL,
    paziente_id BIGINT NOT NULL,
    data_visita TEXT,
    tipo_visita TEXT,
    rx_post_od_sf DOUBLE PRECISION,
    rx_post_od_cil DOUBLE PRECISION,
    rx_post_od_ax INTEGER,
    rx_post_od_avsc TEXT,
    rx_post_os_sf DOUBLE PRECISION,
    rx_post_os_cil DOUBLE PRECISION,
    rx_post_os_ax INTEGER,
    rx_post_os_avsc TEXT,
    effetto_residuo_od DOUBLE PRECISION,
    effetto_residuo_os DOUBLE PRECISION,
    soddisfazione INTEGER,
    operatore TEXT,
    note_visita TEXT,
    created_at TEXT
)
"""

_SQL_CREATE_SL = """
CREATE TABLE IF NOT EXISTS lenti_inverse (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paziente_id INTEGER NOT NULL,
    occhio TEXT NOT NULL,
    data_scheda TEXT,
    topo_k_flat_mm REAL, topo_k_flat_d REAL,
    topo_k_steep_mm REAL, topo_k_steep_d REAL,
    topo_ecc_media REAL, topo_raggio_apicale_mm REAL,
    topo_dev_std_raggio REAL, topo_dev_std_ecc REAL,
    topo_topografo TEXT, topo_data TEXT, topo_misurazioni_json TEXT,
    rx_sfera REAL, rx_cilindro REAL, rx_asse INTEGER,
    rx_miopia_tot REAL, rx_miopia_ridurre REAL, rx_avsc TEXT, rx_avcc TEXT,
    lente_tipo_zo TEXT, lente_r0_mm REAL, lente_rb_mm REAL,
    lente_ecc_zo REAL, lente_fattore_p REAL, lente_fattore_appiatt REAL,
    lente_zo_diam_mm REAL, lente_clearance_mm REAL,
    lente_c0 REAL, lente_c1 REAL, lente_c2 REAL, lente_c3 REAL,
    lente_c4 REAL, lente_c5 REAL, lente_c6 REAL,
    lente_flange_json TEXT, lente_diam_tot_mm REAL, lente_potere_d REAL,
    lente_materiale TEXT, lente_dk REAL,
    lente_puntino INTEGER DEFAULT 0, lente_note TEXT,
    app_data TEXT, app_tipo TEXT,
    app_clearance_centrale REAL, app_clearance_periferica REAL,
    app_pattern TEXT, app_centratura TEXT, app_movimento_mm REAL,
    app_valutazione TEXT, app_modifiche TEXT, app_operatore TEXT,
    app_note_fluoresceina TEXT, app_note TEXT,
    created_at TEXT, updated_at TEXT
)
"""

_SQL_CREATE_SL_ORDINI = """
CREATE TABLE IF NOT EXISTS lenti_inverse_ordini (
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

_SQL_CREATE_SL_VISITE = """
CREATE TABLE IF NOT EXISTS lenti_inverse_visite (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scheda_id INTEGER NOT NULL, paziente_id INTEGER NOT NULL,
    data_visita TEXT, tipo_visita TEXT,
    rx_post_od_sf REAL, rx_post_od_cil REAL, rx_post_od_ax INTEGER, rx_post_od_avsc TEXT,
    rx_post_os_sf REAL, rx_post_os_cil REAL, rx_post_os_ax INTEGER, rx_post_os_avsc TEXT,
    effetto_residuo_od REAL, effetto_residuo_os REAL,
    soddisfazione INTEGER, operatore TEXT, note_visita TEXT, created_at TEXT
)
"""


def init_lenti_inverse_db(conn) -> None:
    pg = _is_postgres(conn)
    # Usa la connessione raw psycopg2 se disponibile, per evitare problemi con _PgCursor/_adapt_sql
    raw_conn = getattr(conn, "_conn", conn)
    try:
        cur = raw_conn.cursor()
    except Exception:
        cur = conn.cursor()
    if pg:
        for sql in [_SQL_CREATE_PG, _SQL_CREATE_PG_ORDINI, _SQL_CREATE_PG_VISITE]:
            try:
                cur.execute(sql)
            except Exception as e:
                try:
                    raw_conn.rollback()
                except Exception:
                    pass
        for col, typ in [("lente_dk", "DOUBLE PRECISION"), ("app_note_fluoresceina", "TEXT")]:
            try:
                cur.execute(f"ALTER TABLE lenti_inverse ADD COLUMN IF NOT EXISTS {col} {typ}")
            except Exception:
                try:
                    raw_conn.rollback()
                except Exception:
                    pass
    else:
        for sql in [_SQL_CREATE_SL, _SQL_CREATE_SL_ORDINI, _SQL_CREATE_SL_VISITE]:
            cur.execute(sql)
    try:
        raw_conn.commit()
    except Exception:
        conn.commit()


# ---------------------------------------------------------------------------
# UI principale
# ---------------------------------------------------------------------------

def ui_lenti_inverse():
    st.header("Lenti Inverse / Ortocheratologia")
    conn = _get_conn()
    init_lenti_inverse_db(conn)
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
    sel = st.selectbox("Seleziona paziente", options, key="li_paz_sel")
    paz_id = int(sel.split(" - ", 1)[0])
    st.divider()

    tab1, tab2, tab3, tab4 = st.tabs([
        "Nuova Scheda Lente", "Schede Esistenti", "Ordini", "Visite di Controllo"])
    with tab1: _ui_nuova_scheda(conn, cur, paz_id)
    with tab2: _ui_storico_schede(conn, cur, paz_id)
    with tab3: _ui_ordini(conn, cur, paz_id)
    with tab4: _ui_visite(conn, cur, paz_id)


# ---------------------------------------------------------------------------
# Tab: Nuova scheda
# ---------------------------------------------------------------------------

def _ui_nuova_scheda(conn, cur, paz_id):
    st.subheader("Nuova scheda lente inversa")
    with st.form("form_nuova_lente_inversa"):
        col_oc, col_data = st.columns(2)
        with col_oc:   occhio      = st.selectbox("Occhio", ["OD","OS","OD+OS"], key="li_occhio")
        with col_data: data_scheda = st.text_input("Data scheda (gg/mm/aaaa)", _today_str(), key="li_data")

        st.markdown("### Topografia corneale")
        c1,c2,c3,c4 = st.columns(4)
        with c1:
            topo_k_flat_mm = st.number_input("K flat (mm)", 6.0, 9.5, 7.80, 0.01, key="li_kflat_mm")
            st.caption(f"= {r_to_d(topo_k_flat_mm):.2f} D")
        with c2:
            topo_k_flat_D = st.number_input("K flat (D)", 35.0, 52.0, r_to_d(st.session_state.get("li_kflat_mm",7.80)), 0.25, key="li_kflat_D")
            st.caption(f"= {d_to_r(topo_k_flat_D):.3f} mm")
        with c3: topo_k_steep_mm = st.number_input("K steep (mm)", 6.0, 9.5,  7.70, 0.01, key="li_ksteep_mm")
        with c4: topo_k_steep_D  = st.number_input("K steep (D)", 35.0, 52.0, 43.75, 0.25, key="li_ksteep_D")

        c5,c6,c7,c8 = st.columns(4)
        with c5: topo_ecc_media = st.number_input("Eccentricita media", 0.0, 1.5, 0.50, 0.01, key="li_ecc_media")
        with c6: topo_raggio_mm = st.number_input("Raggio apicale (mm)", 6.0, 9.5, 7.80, 0.01, key="li_raggio_ap")
        with c7: topo_dev_r = st.number_input("Dev.Std raggio", 0.0, 0.5, 0.05, 0.001, format="%.3f", key="li_dev_r")
        with c8: topo_dev_e = st.number_input("Dev.Std ecc.", 0.0, 0.5, 0.02, 0.001, format="%.3f", key="li_dev_e")

        c9,c10 = st.columns(2)
        with c9:  topo_topografo = st.text_input("Topografo", "", key="li_topografo")
        with c10: topo_data      = st.text_input("Data topografia (gg/mm/aaaa)", _today_str(), key="li_topo_data")

        st.caption("Misurazioni individuali (opzionale)")
        mis_cols = st.columns(4)
        misurazioni = []
        for i in range(4):
            with mis_cols[i]:
                mer = st.text_input(f"Meridiano {i+1}", "", key=f"li_mer_{i}")
                ra  = st.number_input(f"Raggio {i+1} (mm)", 6.0, 9.5, 7.80, 0.01, key=f"li_ra_{i}")
                ec  = st.number_input(f"Ecc. {i+1}", 0.0, 1.5, 0.50, 0.01, key=f"li_ec_{i}")
                if mer.strip():
                    misurazioni.append({"meridiano": mer, "raggio_mm": ra, "eccentricita": ec})

        st.markdown("### Refrazione")
        r1,r2,r3,r4,r5 = st.columns(5)
        with r1: rx_sf   = st.number_input("Sfera (D)", -25.0, 5.0, 0.0, 0.25, key="li_rx_sf")
        with r2: rx_cil  = st.number_input("Cilindro (D)", -8.0, 8.0, 0.0, 0.25, key="li_rx_cil")
        with r3: rx_ax   = st.number_input("Asse gradi", 0, 180, 0, 1, key="li_rx_ax")
        with r4: rx_avsc = st.text_input("AV s.c.", "", key="li_avsc")
        with r5: rx_avcc = st.text_input("AV c.c.", "", key="li_avcc")

        m1,m2 = st.columns(2)
        with m1: rx_miopia_tot = st.number_input("Miopia totale vertice (D)", -25.0, 0.0, 0.0, 0.25, key="li_miot")
        with m2: rx_miopia_rid = st.number_input("Miopia da ridurre (D)", -25.0, 0.0, 0.0, 0.25, key="li_mior")

        st.markdown("### Parametri lente inversa")
        lp1,lp2,lp3 = st.columns(3)
        with lp1: lente_tipo_zo = st.selectbox("Tipo ZO", ["Sferica","Asferica"], key="li_tipo_zo")
        with lp2: lente_r0 = st.number_input("Raggio apicale r0 (mm)", 6.0, 9.5, 7.60, 0.01, key="li_r0")
        with lp3: lente_rb = st.number_input("Raggio base Rb (mm)", 7.0, 11.0, 8.73, 0.001, format="%.3f", key="li_rb")

        lp4,lp5,lp6,lp7 = st.columns(4)
        with lp4: lente_ecc_zo  = st.number_input("Eccentricita ZO", 0.0, 2.0, 0.50, 0.01, key="li_ecc_zo")
        with lp5: lente_p       = st.number_input("Fattore forma p", 0.0, 5.0, 0.75, 0.01, key="li_p")
        with lp6: lente_appiatt = st.number_input("Fattore appiattimento", 0.0, 2.0, 0.50, 0.01, key="li_appiatt")
        with lp7: lente_zo_diam = st.number_input("Diam ZO (mm)", 4.0, 10.0, 5.6, 0.1, key="li_zo_diam")

        cl1,cl2 = st.columns(2)
        with cl1: lente_clearance = st.number_input("Clearance inv (mm)", 0.0, 0.2, 0.054, 0.001, format="%.3f", key="li_clearance")
        with cl2: lente_diam_tot  = st.number_input("Diam Totale (mm)", 8.0, 14.0, 10.8, 0.1, key="li_diam_tot")

        st.markdown("**Curve c0-c6**")
        cc = st.columns(7)
        curve_labels   = ["c0 Base","c1 Inv","c2 2R","c3 3R","c4 4R","c5 5R","c6 Bordo"]
        curve_defaults = [0.005, 0.073, 0.010, 0.010, 0.007, 0.030, 0.155]
        curve_vals = []
        for i, (col, lab, dfl) in enumerate(zip(cc, curve_labels, curve_defaults)):
            with col:
                v = st.number_input(lab, 0.0, 1.0, dfl, 0.001, format="%.3f", key=f"li_c{i}")
                curve_vals.append(v)

        st.markdown("**Flange**")
        flange_data = []
        fl_names    = ["I Flangia","II Flangia","III Flangia","IV Flangia","V Flangia"]
        fl_r_def    = [6.827, 7.639, 8.003, 8.875, 10.987]
        fl_D_def    = [49.44, 44.18, 42.17, 38.03, 30.72]
        fl_amp_def  = [0.8, 0.5, 0.7, 0.2, 0.4]
        fl_diam_def = [7.2, 8.2, 9.6, 10.0, 10.8]
        for i, nome in enumerate(fl_names):
            with st.expander(nome, expanded=(i == 0)):
                fc = st.columns(4)
                with fc[0]: fr = st.number_input(f"{nome} r mm", 5.0, 14.0, fl_r_def[i], 0.001, format="%.3f", key=f"li_fl_r{i}")
                with fc[1]: fD = st.number_input(f"{nome} D", 20.0, 70.0, fl_D_def[i], 0.01, key=f"li_fl_D{i}")
                with fc[2]: fa = st.number_input(f"{nome} amp mm", 0.0, 3.0, fl_amp_def[i], 0.1, key=f"li_fl_a{i}")
                with fc[3]: fd = st.number_input(f"{nome} diam mm", 4.0, 14.0, fl_diam_def[i], 0.1, key=f"li_fl_d{i}")
                flange_data.append({"nome": nome, "raggio_mm": fr, "diottrie": fD, "ampiezza_mm": fa, "diametro_mm": fd})

        pt1,pt2,pt3,pt4 = st.columns(4)
        with pt1: lente_potere    = st.number_input("Potere (D)", -10.0, 10.0, 0.0, 0.25, key="li_potere")
        with pt2: lente_materiale = st.text_input("Materiale", "Boston XO", key="li_materiale")
        with pt3: lente_dk        = st.number_input("DK", 0.0, 200.0, 100.0, 1.0, key="li_dk")
        with pt4: lente_puntino   = st.checkbox("Puntino OD", key="li_puntino")
        lente_note = st.text_area("Note lente", "", key="li_lente_note")

        st.markdown("### Appoggio LAC sulla cornea")
        a1,a2 = st.columns(2)
        with a1:
            app_data = st.text_input("Data valutazione (gg/mm/aaaa)", _today_str(), key="li_app_data")
            app_tipo = st.selectbox("Tipo appoggio", ["para-apicale","apicale","piatto","sollevato"], key="li_app_tipo")
            app_cen  = st.number_input("Clearance centrale um", 0.0, 500.0, 0.0, 1.0, key="li_app_cen")
            app_per  = st.number_input("Clearance periferica um", 0.0, 500.0, 0.0, 1.0, key="li_app_per")
        with a2:
            app_pattern = st.selectbox("Pattern fluoresceinogramma", [
                "ottimale","appoggio_centrale_eccessivo","sollevamento_centrale",
                "appoggio_periferico_stretto","appoggio_periferico_largo",
                "decentramento_superiore","decentramento_inferiore",
                "decentramento_nasale","decentramento_temporale"], key="li_pattern")
            app_centratura = st.selectbox("Centratura", [
                "centrata","decentrata_superiore","decentrata_inferiore",
                "decentrata_nasale","decentrata_temporale"], key="li_centratura")
            app_mov = st.number_input("Movimento ammiccamento mm", 0.0, 5.0, 0.0, 0.1, key="li_mov")
            app_valutazione = st.selectbox("Valutazione globale", [
                "ottimale","accettabile","da_modificare","da_sostituire"], key="li_valut")

        app_modifiche = st.text_input("Modifiche suggerite", "", key="li_modifiche")
        app_operatore = st.text_input("Operatore", "", key="li_operatore")
        app_note_fl   = st.text_area("Note fluoresceinogramma", "", key="li_note_fl")
        app_note      = st.text_area("Note appoggio", "", key="li_app_note")
        submitted = st.form_submit_button("Salva scheda lente")

    if submitted:
        now_iso = datetime.now().isoformat(timespec="seconds")
        params = (
            paz_id, occhio, _parse_date(data_scheda) or date.today().isoformat(),
            topo_k_flat_mm, topo_k_flat_D, topo_k_steep_mm, topo_k_steep_D,
            topo_ecc_media, topo_raggio_mm, topo_dev_r, topo_dev_e,
            topo_topografo, _parse_date(topo_data),
            json.dumps(misurazioni, ensure_ascii=False),
            rx_sf, rx_cil, int(rx_ax), rx_miopia_tot, rx_miopia_rid, rx_avsc, rx_avcc,
            lente_tipo_zo, lente_r0, lente_rb, lente_ecc_zo, lente_p,
            lente_appiatt, lente_zo_diam, lente_clearance,
            curve_vals[0], curve_vals[1], curve_vals[2], curve_vals[3],
            curve_vals[4], curve_vals[5], curve_vals[6],
            json.dumps(flange_data, ensure_ascii=False), lente_diam_tot, lente_potere,
            lente_materiale, lente_dk, 1 if lente_puntino else 0, lente_note,
            _parse_date(app_data), app_tipo, app_cen, app_per,
            app_pattern, app_centratura, app_mov, app_valutazione,
            app_modifiche, app_operatore, app_note_fl, app_note,
            now_iso, now_iso,
        )
        ph = _ph(len(params), conn)
        sql = (
            "INSERT INTO lenti_inverse ("
            "paziente_id,occhio,data_scheda,"
            "topo_k_flat_mm,topo_k_flat_d,topo_k_steep_mm,topo_k_steep_d,"
            "topo_ecc_media,topo_raggio_apicale_mm,topo_dev_std_raggio,topo_dev_std_ecc,"
            "topo_topografo,topo_data,topo_misurazioni_json,"
            "rx_sfera,rx_cilindro,rx_asse,rx_miopia_tot,rx_miopia_ridurre,rx_avsc,rx_avcc,"
            "lente_tipo_zo,lente_r0_mm,lente_rb_mm,lente_ecc_zo,lente_fattore_p,"
            "lente_fattore_appiatt,lente_zo_diam_mm,lente_clearance_mm,"
            "lente_c0,lente_c1,lente_c2,lente_c3,lente_c4,lente_c5,lente_c6,"
            "lente_flange_json,lente_diam_tot_mm,lente_potere_d,"
            "lente_materiale,lente_dk,lente_puntino,lente_note,"
            "app_data,app_tipo,app_clearance_centrale,app_clearance_periferica,"
            "app_pattern,app_centratura,app_movimento_mm,app_valutazione,"
            "app_modifiche,app_operatore,app_note_fluoresceina,app_note,"
            "created_at,updated_at"
            f") VALUES ({ph})"
        )
        try:
            cur.execute(sql, params)
            conn.commit()
            st.success(f"Scheda lente {occhio} salvata.")
        except Exception as e:
            st.error(f"Errore salvataggio: {e}")


# ---------------------------------------------------------------------------
# Tab: Schede esistenti
# ---------------------------------------------------------------------------

def _ui_storico_schede(conn, cur, paz_id):
    st.subheader("Schede lente esistenti")
    ph1 = _ph(1, conn)
    try:
        cur.execute(
            "SELECT * FROM lenti_inverse WHERE paziente_id = " + ph1 + " ORDER BY data_scheda DESC, id DESC",
            (paz_id,))
        schede = cur.fetchall()
    except Exception as e:
        st.error(f"Errore: {e}")
        return
    if not schede:
        st.info("Nessuna scheda lente per questo paziente.")
        return
    for s in schede:
        sid    = _row_get(s, "id")
        rb     = _row_get(s, "lente_rb_mm")
        diam   = _row_get(s, "lente_diam_tot_mm")
        zo     = _row_get(s, "lente_zo_diam_mm")
        potere = _row_get(s, "lente_potere_d")
        label  = f"Occhio {_row_get(s,'occhio','?')} | {_row_get(s,'data_scheda','')} | Rb={rb} | Diam={diam} | {_row_get(s,'lente_materiale','')}"
        with st.expander(label):
            c1,c2,c3,c4 = st.columns(4)
            c1.metric("Rb (mm)",    f"{rb:.3f}"    if rb    else "—")
            c2.metric("Diam (mm)",  f"{diam:.1f}"  if diam  else "—")
            c3.metric("ZO (mm)",    f"{zo:.1f}"    if zo    else "—")
            c4.metric("Potere (D)", f"{potere:+.2f}" if potere else "—")
            kfm = _row_get(s,"topo_k_flat_mm"); ksm = _row_get(s,"topo_k_steep_mm")
            em  = _row_get(s,"topo_ecc_media"); ram = _row_get(s,"topo_raggio_apicale_mm")
            c5,c6,c7,c8 = st.columns(4)
            c5.metric("K flat", f"{kfm:.2f}" if kfm else "—")
            c6.metric("K steep",f"{ksm:.2f}" if ksm else "—")
            c7.metric("Ecc",    f"{em:.2f}"  if em  else "—")
            c8.metric("r ap",   f"{ram:.2f}" if ram else "—")
            st.markdown(f"**Appoggio:** {_row_get(s,'app_tipo','—')} | {_row_get(s,'app_pattern','—')} | {_row_get(s,'app_valutazione','—')}")
            flange_raw = _row_get(s, "lente_flange_json", "[]")
            try:
                flange = json.loads(flange_raw) if flange_raw else []
            except Exception:
                flange = []
            if flange:
                fl_cols = st.columns(len(flange))
                for i, fl in enumerate(flange):
                    with fl_cols[i]:
                        st.caption(fl.get("nome",""))
                        st.write(f"r={fl.get('raggio_mm','?')} mm | amp={fl.get('ampiezza_mm','?')} | diam={fl.get('diametro_mm','?')}")
            if st.button(f"Elimina scheda #{sid}", key=f"li_del_{sid}"):
                try:
                    cur.execute("DELETE FROM lenti_inverse WHERE id = " + ph1, (sid,))
                    conn.commit()
                    st.warning("Scheda eliminata.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore: {e}")


# ---------------------------------------------------------------------------
# Tab: Ordini
# ---------------------------------------------------------------------------

def _ui_ordini(conn, cur, paz_id):
    st.subheader("Storico ordini lenti")
    ph1 = _ph(1, conn)
    cur.execute(
        "SELECT id,occhio,data_scheda,lente_rb_mm,lente_diam_tot_mm FROM lenti_inverse WHERE paziente_id = " + ph1 + " ORDER BY data_scheda DESC",
        (paz_id,))
    schede = cur.fetchall()

    with st.form("form_nuovo_ordine"):
        st.markdown("#### Nuovo ordine")
        if not schede:
            st.info("Crea prima una scheda lente.")
            st.form_submit_button("Salva ordine", disabled=True)
            return
        scheda_opts = [f"#{_row_get(s,'id')} {_row_get(s,'occhio')} {_row_get(s,'data_scheda')}" for s in schede]
        sel_scheda = st.selectbox("Scheda", scheda_opts, key="ord_scheda")
        scheda_id = int(sel_scheda.split("#")[1].split(" ")[0])

        o1,o2,o3 = st.columns(3)
        with o1:
            ord_occhio    = st.selectbox("Occhio", ["OD","OS","OD+OS"], key="ord_occhio")
            ord_data      = st.text_input("Data ordine", _today_str(), key="ord_data")
            ord_data_prev = st.text_input("Consegna prevista", "", key="ord_prev")
        with o2:
            ord_fornitore   = st.text_input("Fornitore", "", key="ord_forn")
            ord_laboratorio = st.text_input("Laboratorio", "", key="ord_lab")
            ord_rif         = st.text_input("Rif. lab", "", key="ord_rif")
        with o3:
            ord_stato    = st.selectbox("Stato", ["in_lavorazione","spedito","consegnato","reso","annullato"], key="ord_stato")
            ord_data_eff = st.text_input("Consegna effettiva", "", key="ord_eff")

        pc = st.columns(5)
        with pc[0]: p_rb   = st.number_input("Rb mm", 7.0, 11.0, 8.73, 0.001, format="%.3f", key="ord_rb")
        with pc[1]: p_zo   = st.number_input("ZO mm", 4.0, 10.0, 5.6, 0.1, key="ord_zo")
        with pc[2]: p_diam = st.number_input("Diam mm", 8.0, 14.0, 10.8, 0.1, key="ord_diam")
        with pc[3]: p_pot  = st.number_input("Potere D", -10.0, 10.0, 0.0, 0.25, key="ord_pot")
        with pc[4]: p_mat  = st.text_input("Materiale", "Boston XO", key="ord_mat")

        fl_cols = st.columns(5)
        fl_vals = []
        for i, (col, n) in enumerate(zip(fl_cols, ["I","II","III","IV","V"])):
            with col:
                v = st.number_input(f"{n} Fl r", 5.0, 14.0, 0.0, 0.001, format="%.3f", key=f"ord_fl{i}")
                fl_vals.append(v)
        p_note = st.text_area("Note parametri", "", key="ord_pnote")

        cc1,cc2,cc3,cc4 = st.columns(4)
        with cc1: costo_u  = st.number_input("Costo unit EUR", 0.0, 2000.0, 0.0, 1.0, key="ord_cu")
        with cc2: costo_cp = st.number_input("Costo coppia EUR", 0.0, 4000.0, 0.0, 1.0, key="ord_cp")
        with cc3: iva      = st.number_input("IVA perc", 0.0, 25.0, 22.0, 0.5, key="ord_iva")
        with cc4: tot_fatt = st.number_input("Totale EUR", 0.0, 5000.0, 0.0, 1.0, key="ord_tot")

        f1,f2 = st.columns(2)
        with f1: num_fatt = st.text_input("N fattura", "", key="ord_nfatt")
        with f2: pag_met  = st.selectbox("Metodo pag", ["contante","carta","bonifico","rateizzato"], key="ord_pmet")

        p1,p2,p3 = st.columns(3)
        with p1: pag_stato = st.selectbox("Stato pag", ["da_pagare","pagato","parziale"], key="ord_pst")
        with p2: pag_data  = st.text_input("Data pagamento", "", key="ord_pdata")
        with p3: ord_note  = st.text_area("Note", "", key="ord_note")

        sub_ord = st.form_submit_button("Salva ordine")

    if sub_ord:
        now_iso = datetime.now().isoformat(timespec="seconds")
        pj = json.dumps({"Rb_mm": p_rb, "zo_mm": p_zo, "diam_mm": p_diam,
                          "potere_D": p_pot, "materiale": p_mat, "flange": fl_vals, "note": p_note}, ensure_ascii=False)
        params = (scheda_id, paz_id, ord_occhio,
                  _parse_date(ord_data), _parse_date(ord_data_prev), _parse_date(ord_data_eff), ord_stato,
                  ord_fornitore, ord_laboratorio, ord_rif, pj,
                  costo_u, costo_cp, iva, tot_fatt,
                  num_fatt, pag_met, pag_stato, _parse_date(pag_data),
                  ord_note, now_iso)
        ph = _ph(len(params), conn)
        sql = (
            "INSERT INTO lenti_inverse_ordini ("
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
        "SELECT * FROM lenti_inverse_ordini WHERE paziente_id = " + ph1 + " ORDER BY data_ordine DESC, id DESC",
        (paz_id,))
    for o in cur.fetchall():
        oid = _row_get(o, "id")
        tot = _row_get(o, "totale_fattura", 0) or 0
        with st.expander(f"#{oid} | {_row_get(o,'occhio','')} | {_row_get(o,'data_ordine','')} | {_row_get(o,'fornitore','')} | {_row_get(o,'stato_ordine','')} | EUR {tot:.2f}"):
            pc = json.loads(_row_get(o, "parametri_json", "{}") or "{}")
            st.write(f"Rb={pc.get('Rb_mm','?')} | Diam={pc.get('diam_mm','?')} | Potere={pc.get('potere_D','?')} | Mat={pc.get('materiale','—')}")
            st.write(f"Fattura: {_row_get(o,'numero_fattura','—')} | {_row_get(o,'pagamento_metodo','')} – {_row_get(o,'pagamento_stato','')}")
            if st.button(f"Elimina ordine #{oid}", key=f"del_ord_{oid}"):
                try:
                    cur.execute("DELETE FROM lenti_inverse_ordini WHERE id = " + ph1, (oid,))
                    conn.commit()
                    st.warning("Ordine eliminato.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore: {e}")


# ---------------------------------------------------------------------------
# Tab: Visite di controllo
# ---------------------------------------------------------------------------

def _ui_visite(conn, cur, paz_id):
    st.subheader("Visite di controllo post-applicazione")
    ph1 = _ph(1, conn)
    cur.execute(
        "SELECT id,occhio,data_scheda FROM lenti_inverse WHERE paziente_id = " + ph1 + " ORDER BY data_scheda DESC",
        (paz_id,))
    schede = cur.fetchall()

    with st.form("form_nuova_visita"):
        st.markdown("#### Nuova visita")
        if not schede:
            st.info("Crea prima una scheda lente.")
            st.form_submit_button("Salva visita", disabled=True)
            return
        scheda_opts = [f"#{_row_get(s,'id')} {_row_get(s,'occhio')} {_row_get(s,'data_scheda')}" for s in schede]
        sel_s     = st.selectbox("Scheda", scheda_opts, key="vis_scheda")
        scheda_id = int(sel_s.split("#")[1].split(" ")[0])

        v1,v2 = st.columns(2)
        with v1:
            vis_data = st.text_input("Data visita", _today_str(), key="vis_data")
            vis_tipo = st.selectbox("Tipo visita", [
                "prima_applicazione","controllo_1_notte","controllo_1_settimana",
                "controllo_1_mese","controllo_3_mesi","controllo_6_mesi",
                "controllo_annuale","urgenza","altro"], key="vis_tipo")
            vis_op = st.text_input("Operatore", "", key="vis_op")
        with v2:
            vis_sodd     = st.slider("Soddisfazione 1-10", 1, 10, 8, key="vis_sodd")
            vis_resid_od = st.number_input("Effetto residuo OD D", -10.0, 10.0, 0.0, 0.25, key="vis_resod")
            vis_resid_os = st.number_input("Effetto residuo OS D", -10.0, 10.0, 0.0, 0.25, key="vis_resos")

        st.markdown("**Refrazione post-OK**")
        rx1,rx2,rx3,rx4 = st.columns(4)
        with rx1: v_od_sf   = st.number_input("OD SF", -20.0, 5.0, 0.0, 0.25, key="vis_od_sf")
        with rx2: v_od_cil  = st.number_input("OD CIL", -5.0, 5.0, 0.0, 0.25, key="vis_od_cil")
        with rx3: v_od_ax   = st.number_input("OD AX", 0, 180, 0, 1, key="vis_od_ax")
        with rx4: v_od_avsc = st.text_input("OD AVSC", "", key="vis_od_av")

        rx5,rx6,rx7,rx8 = st.columns(4)
        with rx5: v_os_sf   = st.number_input("OS SF", -20.0, 5.0, 0.0, 0.25, key="vis_os_sf")
        with rx6: v_os_cil  = st.number_input("OS CIL", -5.0, 5.0, 0.0, 0.25, key="vis_os_cil")
        with rx7: v_os_ax   = st.number_input("OS AX", 0, 180, 0, 1, key="vis_os_ax")
        with rx8: v_os_avsc = st.text_input("OS AVSC", "", key="vis_os_av")

        vis_note = st.text_area("Note visita", "", key="vis_note")
        sub_vis  = st.form_submit_button("Salva visita")

    if sub_vis:
        now_iso = datetime.now().isoformat(timespec="seconds")
        params = (scheda_id, paz_id, _parse_date(vis_data), vis_tipo,
                  v_od_sf, v_od_cil, int(v_od_ax), v_od_avsc,
                  v_os_sf, v_os_cil, int(v_os_ax), v_os_avsc,
                  vis_resid_od, vis_resid_os, vis_sodd,
                  vis_op, vis_note, now_iso)
        ph = _ph(len(params), conn)
        sql = (
            "INSERT INTO lenti_inverse_visite ("
            "scheda_id,paziente_id,data_visita,tipo_visita,"
            "rx_post_od_sf,rx_post_od_cil,rx_post_od_ax,rx_post_od_avsc,"
            "rx_post_os_sf,rx_post_os_cil,rx_post_os_ax,rx_post_os_avsc,"
            "effetto_residuo_od,effetto_residuo_os,soddisfazione,"
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
        "SELECT * FROM lenti_inverse_visite WHERE paziente_id = " + ph1 + " ORDER BY data_visita DESC, id DESC",
        (paz_id,))
    for v in cur.fetchall():
        vid = _row_get(v, "id")
        rod = _row_get(v, "effetto_residuo_od", 0) or 0
        ros = _row_get(v, "effetto_residuo_os", 0) or 0
        with st.expander(f"#{vid} | {_row_get(v,'data_visita','')} | {_row_get(v,'tipo_visita','')} | Sodd {_row_get(v,'soddisfazione','?')}/10"):
            c1,c2,c3,c4 = st.columns(4)
            c1.metric("OD AVSC", _row_get(v,"rx_post_od_avsc","—"))
            c2.metric("OS AVSC", _row_get(v,"rx_post_os_avsc","—"))
            c3.metric("Res OD", f"{rod:+.2f}")
            c4.metric("Res OS", f"{ros:+.2f}")
            st.write(f"Note: {_row_get(v,'note_visita','') or '—'}")
            if st.button(f"Elimina visita #{vid}", key=f"del_vis_{vid}"):
                try:
                    cur.execute("DELETE FROM lenti_inverse_visite WHERE id = " + ph1, (vid,))
                    conn.commit()
                    st.warning("Visita eliminata.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore: {e}")
