# -*- coding: utf-8 -*-
"""
Modulo: Lenti Inverse / Ortocheratologia
Gestionale The Organism – PNEV
Autore: generato automaticamente
Compatibile con SQLite (?) e PostgreSQL (%s) via _DB_BACKEND.
"""

import json
import streamlit as st
from datetime import datetime, date

# ---------------------------------------------------------------------------
# Helpers interni (copiano il pattern di app_patched.py)
# ---------------------------------------------------------------------------

def _ph(n: int = 1) -> str:
    """Ritorna placeholder SQL: '?' per SQLite, '%s' per PostgreSQL."""
    try:
        from app_patched import _DB_BACKEND
        ph = "?" if _DB_BACKEND == "sqlite" else "%s"
    except Exception:
        ph = "?"
    return ", ".join([ph] * n)

def _phv() -> str:
    """Singolo placeholder."""
    return _ph(1)

def _get_conn():
    try:
        from app_patched import get_connection
        return get_connection()
    except Exception:
        import sqlite3
        conn = sqlite3.connect("organism.db")
        conn.row_factory = sqlite3.Row
        return conn

def _row_get(row, key, default=None):
    """Accesso uniforme a sqlite3.Row e psycopg2 DictRow."""
    try:
        v = row[key]
        return v if v is not None else default
    except Exception:
        try:
            v = row.get(key)
            return v if v is not None else default
        except Exception:
            return default

def _today_str() -> str:
    return date.today().strftime("%d/%m/%Y")

def _parse_date(s: str) -> str:
    """gg/mm/aaaa → ISO. Ritorna stringa vuota se non valida."""
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(s.strip(), fmt).strftime("%Y-%m-%d")
        except Exception:
            pass
    return ""

# ---------------------------------------------------------------------------
# Inizializzazione DB
# ---------------------------------------------------------------------------

def init_lenti_inverse_db(conn) -> None:
    """Crea le tabelle se non esistono. Sicuro da chiamare più volte."""
    cur = conn.cursor()

    # Tabella principale: scheda lente per occhio per paziente
    cur.execute("""
        CREATE TABLE IF NOT EXISTS Lenti_Inverse (
            id                      INTEGER PRIMARY KEY AUTOINCREMENT,
            paziente_id             INTEGER NOT NULL,
            occhio                  TEXT NOT NULL,
            data_scheda             TEXT,

            -- Topografia corneale
            topo_k_flat_mm          REAL,
            topo_k_flat_D           REAL,
            topo_k_steep_mm         REAL,
            topo_k_steep_D          REAL,
            topo_ecc_media          REAL,
            topo_raggio_apicale_mm  REAL,
            topo_dev_std_raggio     REAL,
            topo_dev_std_ecc        REAL,
            topo_topografo          TEXT,
            topo_data               TEXT,
            topo_misurazioni_json   TEXT,

            -- Refrazione
            rx_sfera                REAL,
            rx_cilindro             REAL,
            rx_asse                 INTEGER,
            rx_miopia_tot           REAL,
            rx_miopia_ridurre       REAL,
            rx_avsc                 TEXT,
            rx_avcc                 TEXT,

            -- Parametri lente
            lente_tipo_zo           TEXT,
            lente_r0_mm             REAL,
            lente_rb_mm             REAL,
            lente_ecc_zo            REAL,
            lente_fattore_p         REAL,
            lente_fattore_appiatt   REAL,
            lente_zo_diam_mm        REAL,
            lente_clearance_mm      REAL,
            lente_c0                REAL,
            lente_c1                REAL,
            lente_c2                REAL,
            lente_c3                REAL,
            lente_c4                REAL,
            lente_c5                REAL,
            lente_c6                REAL,
            lente_flange_json       TEXT,
            lente_diam_tot_mm       REAL,
            lente_potere_D          REAL,
            lente_materiale         TEXT,
            lente_dk                REAL,
            lente_puntino           INTEGER DEFAULT 0,
            lente_note              TEXT,

            -- Appoggio LAC
            app_data                TEXT,
            app_tipo                TEXT,
            app_clearance_centrale  REAL,
            app_clearance_periferica REAL,
            app_pattern             TEXT,
            app_centratura          TEXT,
            app_movimento_mm        REAL,
            app_valutazione         TEXT,
            app_modifiche           TEXT,
            app_operatore           TEXT,
            app_note_fluoresceina   TEXT,
            app_note                TEXT,

            created_at              TEXT,
            updated_at              TEXT
        )
    """)

    # Tabella storico ordini (N ordini per scheda)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS Lenti_Inverse_Ordini (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            scheda_id           INTEGER NOT NULL,
            paziente_id         INTEGER NOT NULL,
            occhio              TEXT,
            data_ordine         TEXT,
            data_consegna_prev  TEXT,
            data_consegna_eff   TEXT,
            stato_ordine        TEXT,
            fornitore           TEXT,
            laboratorio         TEXT,
            rif_laboratorio     TEXT,
            parametri_json      TEXT,
            costo_unitario      REAL,
            costo_coppia        REAL,
            iva_percent         REAL,
            totale_fattura      REAL,
            numero_fattura      TEXT,
            pagamento_metodo    TEXT,
            pagamento_stato     TEXT,
            pagamento_data      TEXT,
            note_ordine         TEXT,
            created_at          TEXT
        )
    """)

    # Tabella visite di controllo
    cur.execute("""
        CREATE TABLE IF NOT EXISTS Lenti_Inverse_Visite (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            scheda_id           INTEGER NOT NULL,
            paziente_id         INTEGER NOT NULL,
            data_visita         TEXT,
            tipo_visita         TEXT,
            rx_post_od_sf       REAL,
            rx_post_od_cil      REAL,
            rx_post_od_ax       INTEGER,
            rx_post_od_avsc     TEXT,
            rx_post_os_sf       REAL,
            rx_post_os_cil      REAL,
            rx_post_os_ax       INTEGER,
            rx_post_os_avsc     TEXT,
            effetto_residuo_od  REAL,
            effetto_residuo_os  REAL,
            soddisfazione       INTEGER,
            operatore           TEXT,
            note_visita         TEXT,
            created_at          TEXT
        )
    """)

    conn.commit()

    # Migrazioni sicure: aggiunta colonne mancanti
    _migrate_add_columns(cur, conn)


def _migrate_add_columns(cur, conn):
    """Aggiunge colonne mancanti senza distruggere dati esistenti."""
    try:
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='lenti_inverse'")
        existing = {r[0] for r in cur.fetchall()}
        is_pg = True
    except Exception:
        try:
            cur.execute("PRAGMA table_info(Lenti_Inverse)")
            existing = {r[1] for r in cur.fetchall()}
            is_pg = False
        except Exception:
            return

    extra_cols = [
        ("lente_dk", "REAL"),
        ("app_note_fluoresceina", "TEXT"),
    ]
    for col, typ in extra_cols:
        if col not in existing and col.lower() not in {e.lower() for e in existing}:
            try:
                if is_pg:
                    cur.execute(f'ALTER TABLE Lenti_Inverse ADD COLUMN IF NOT EXISTS "{col}" {typ}')
                else:
                    cur.execute(f"ALTER TABLE Lenti_Inverse ADD COLUMN {col} {typ}")
                conn.commit()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# UI principale
# ---------------------------------------------------------------------------

def ui_lenti_inverse():
    st.header("👁️ Lenti Inverse / Ortocheratologia")

    conn = _get_conn()
    init_lenti_inverse_db(conn)
    cur = conn.cursor()

    # --- Seleziona paziente ---
    try:
        cur.execute('SELECT id, Cognome, Nome FROM Pazienti ORDER BY Cognome, Nome')
        pazienti = cur.fetchall()
    except Exception as e:
        st.error(f"Errore accesso tabella Pazienti: {e}")
        return

    if not pazienti:
        st.info("Nessun paziente registrato.")
        return

    options = [f"{_row_get(p,'id')} - {_row_get(p,'Cognome','')} {_row_get(p,'Nome','')}" for p in pazienti]
    sel = st.selectbox("Seleziona paziente", options, key="li_paz_sel")
    paz_id = int(sel.split(" - ", 1)[0])

    st.divider()

    tab_nuova, tab_storico, tab_ordini, tab_visite = st.tabs([
        "📋 Nuova Scheda Lente",
        "📁 Schede Esistenti",
        "🛒 Ordini",
        "🩺 Visite di Controllo",
    ])

    # ======================================================================
    with tab_nuova:
        _ui_nuova_scheda(conn, cur, paz_id)

    # ======================================================================
    with tab_storico:
        _ui_storico_schede(conn, cur, paz_id)

    # ======================================================================
    with tab_ordini:
        _ui_ordini(conn, cur, paz_id)

    # ======================================================================
    with tab_visite:
        _ui_visite(conn, cur, paz_id)


# ---------------------------------------------------------------------------
# Tab: Nuova scheda lente
# ---------------------------------------------------------------------------

def _ui_nuova_scheda(conn, cur, paz_id: int):
    st.subheader("Nuova scheda lente inversa")

    with st.form("form_nuova_lente_inversa"):

        col_oc, col_data = st.columns(2)
        with col_oc:
            occhio = st.selectbox("Occhio", ["OD", "OS", "OD+OS"], key="li_occhio")
        with col_data:
            data_scheda = st.text_input("Data scheda (gg/mm/aaaa)", _today_str(), key="li_data")

        # ---- TOPOGRAFIA ----
        st.markdown("### 🔬 Topografia corneale")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            topo_k_flat_mm  = st.number_input("K flat (mm)", 6.0, 9.5, 7.80, 0.01, key="li_kflat_mm")
        with col2:
            topo_k_flat_D   = st.number_input("K flat (D)", 35.0, 52.0, 43.25, 0.25, key="li_kflat_D")
        with col3:
            topo_k_steep_mm = st.number_input("K steep (mm)", 6.0, 9.5, 7.70, 0.01, key="li_ksteep_mm")
        with col4:
            topo_k_steep_D  = st.number_input("K steep (D)", 35.0, 52.0, 43.75, 0.25, key="li_ksteep_D")

        col5, col6, col7, col8 = st.columns(4)
        with col5:
            topo_ecc_media = st.number_input("Eccentricità media", 0.0, 1.5, 0.50, 0.01, key="li_ecc_media")
        with col6:
            topo_raggio_mm = st.number_input("Raggio apicale (mm)", 6.0, 9.5, 7.80, 0.01, key="li_raggio_ap")
        with col7:
            topo_dev_r = st.number_input("Dev.Std raggio", 0.0, 0.5, 0.05, 0.001, format="%.3f", key="li_dev_r")
        with col8:
            topo_dev_e = st.number_input("Dev.Std ecc.", 0.0, 0.5, 0.02, 0.001, format="%.3f", key="li_dev_e")

        col9, col10 = st.columns(2)
        with col9:
            topo_topografo = st.text_input("Topografo", "", key="li_topografo")
        with col10:
            topo_data = st.text_input("Data topografia (gg/mm/aaaa)", _today_str(), key="li_topo_data")

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

        # ---- REFRAZIONE ----
        st.markdown("### 👓 Refrazione")
        col_r1, col_r2, col_r3, col_r4, col_r5 = st.columns(5)
        with col_r1:
            rx_sf  = st.number_input("Sfera (D)", -25.0, 5.0, 0.0, 0.25, key="li_rx_sf")
        with col_r2:
            rx_cil = st.number_input("Cilindro (D)", -8.0, 8.0, 0.0, 0.25, key="li_rx_cil")
        with col_r3:
            rx_ax  = st.number_input("Asse (°)", 0, 180, 0, 1, key="li_rx_ax")
        with col_r4:
            rx_avsc = st.text_input("AV s.c.", "", key="li_avsc")
        with col_r5:
            rx_avcc = st.text_input("AV c.c.", "", key="li_avcc")

        col_m1, col_m2 = st.columns(2)
        with col_m1:
            rx_miopia_tot   = st.number_input("Miopia totale al vertice (D)", -25.0, 0.0, 0.0, 0.25, key="li_miot")
        with col_m2:
            rx_miopia_rid   = st.number_input("Miopia da ridurre (D)", -25.0, 0.0, 0.0, 0.25, key="li_mior")

        # ---- PARAMETRI LENTE ----
        st.markdown("### 🔵 Parametri lente inversa")

        col_lp1, col_lp2, col_lp3 = st.columns(3)
        with col_lp1:
            lente_tipo_zo = st.selectbox("Tipo ZO", ["Sferica", "Asferica"], key="li_tipo_zo")
        with col_lp2:
            lente_r0   = st.number_input("Raggio apicale r₀ (mm)", 6.0, 9.5, 7.60, 0.01, key="li_r0")
        with col_lp3:
            lente_rb   = st.number_input("Raggio base Rb (mm)", 7.0, 11.0, 8.73, 0.001, format="%.3f", key="li_rb")

        col_lp4, col_lp5, col_lp6, col_lp7 = st.columns(4)
        with col_lp4:
            lente_ecc_zo   = st.number_input("Eccentricità ZO", 0.0, 2.0, 0.50, 0.01, key="li_ecc_zo")
        with col_lp5:
            lente_p        = st.number_input("Fattore forma p", 0.0, 5.0, 0.75, 0.01, key="li_p")
        with col_lp6:
            lente_appiatt  = st.number_input("Fattore appiattimento", 0.0, 2.0, 0.50, 0.01, key="li_appiatt")
        with col_lp7:
            lente_zo_diam  = st.number_input("Ø Zona Ottica (mm)", 4.0, 10.0, 5.6, 0.1, key="li_zo_diam")

        col_cl1, col_cl2 = st.columns(2)
        with col_cl1:
            lente_clearance = st.number_input("Clearance punto inversione (mm)", 0.0, 0.2, 0.054, 0.001, format="%.3f", key="li_clearance")
        with col_cl2:
            lente_diam_tot = st.number_input("Ø Totale (mm)", 8.0, 14.0, 10.8, 0.1, key="li_diam_tot")

        st.markdown("**Curve (c₀ … c₆)**")
        cc = st.columns(7)
        curve_labels = ["c₀ Curva base", "c₁ Inv.", "c₂ 2°Racc.", "c₃ 3°Racc.", "c₄ 4°Racc.", "c₅ 5°Racc.", "c₆ Bordo"]
        curve_defaults = [0.005, 0.073, 0.010, 0.010, 0.007, 0.030, 0.155]
        curve_vals = []
        for i, (col, lab, dfl) in enumerate(zip(cc, curve_labels, curve_defaults)):
            with col:
                v = st.number_input(lab, 0.0, 1.0, dfl, 0.001, format="%.3f", key=f"li_c{i}")
                curve_vals.append(v)

        st.markdown("**Flange**")
        flange_data = []
        fl_names = ["I Flangia", "II Flangia", "III Flangia", "IV Flangia", "V Flangia"]
        fl_r_def  = [6.827, 7.639, 8.003, 8.875, 10.987]
        fl_D_def  = [49.44, 44.18, 42.17, 38.03, 30.72]
        fl_amp_def = [0.8, 0.5, 0.7, 0.2, 0.4]
        fl_diam_def = [7.2, 8.2, 9.6, 10.0, 10.8]

        for i, nome in enumerate(fl_names):
            with st.expander(nome, expanded=(i == 0)):
                fc = st.columns(4)
                with fc[0]:
                    fr = st.number_input(f"{nome} – Raggio (mm)", 5.0, 14.0, fl_r_def[i], 0.001, format="%.3f", key=f"li_fl_r{i}")
                with fc[1]:
                    fD = st.number_input(f"{nome} – Diottrie", 20.0, 70.0, fl_D_def[i], 0.01, key=f"li_fl_D{i}")
                with fc[2]:
                    fa = st.number_input(f"{nome} – Ampiezza (mm)", 0.0, 3.0, fl_amp_def[i], 0.1, key=f"li_fl_a{i}")
                with fc[3]:
                    fd = st.number_input(f"{nome} – Ø (mm)", 4.0, 14.0, fl_diam_def[i], 0.1, key=f"li_fl_d{i}")
                flange_data.append({"nome": nome, "raggio_mm": fr, "diottrie": fD, "ampiezza_mm": fa, "diametro_mm": fd})

        col_pot, col_mat, col_dk, col_punt = st.columns(4)
        with col_pot:
            lente_potere    = st.number_input("Potere (D)", -10.0, 10.0, 0.0, 0.25, key="li_potere")
        with col_mat:
            lente_materiale = st.text_input("Materiale", "Boston XO", key="li_materiale")
        with col_dk:
            lente_dk        = st.number_input("DK", 0.0, 200.0, 100.0, 1.0, key="li_dk")
        with col_punt:
            lente_puntino   = st.checkbox("Puntino OD", key="li_puntino")

        lente_note = st.text_area("Note lente", "", key="li_lente_note")

        # ---- APPOGGIO LAC ----
        st.markdown("### 🩻 Appoggio LAC sulla cornea")

        col_a1, col_a2 = st.columns(2)
        with col_a1:
            app_data  = st.text_input("Data valutazione (gg/mm/aaaa)", _today_str(), key="li_app_data")
            app_tipo  = st.selectbox("Tipo appoggio", ["para-apicale", "apicale", "piatto", "sollevato"], key="li_app_tipo")
            app_cen   = st.number_input("Clearance centrale (µm)", 0.0, 500.0, 0.0, 1.0, key="li_app_cen")
            app_per   = st.number_input("Clearance periferica (µm)", 0.0, 500.0, 0.0, 1.0, key="li_app_per")
        with col_a2:
            app_pattern = st.selectbox("Pattern fluoresceinogramma", [
                "ottimale", "appoggio_centrale_eccessivo", "sollevamento_centrale",
                "appoggio_periferico_stretto", "appoggio_periferico_largo",
                "decentramento_superiore", "decentramento_inferiore",
                "decentramento_nasale", "decentramento_temporale"
            ], key="li_pattern")
            app_centratura = st.selectbox("Centratura", [
                "centrata", "decentrata_superiore", "decentrata_inferiore",
                "decentrata_nasale", "decentrata_temporale"
            ], key="li_centratura")
            app_mov = st.number_input("Movimento all'ammiccamento (mm)", 0.0, 5.0, 0.0, 0.1, key="li_mov")
            app_valutazione = st.selectbox("Valutazione globale", [
                "ottimale", "accettabile", "da_modificare", "da_sostituire"
            ], key="li_valut")

        app_modifiche    = st.text_input("Modifiche suggerite", "", key="li_modifiche")
        app_operatore    = st.text_input("Operatore", "", key="li_operatore")
        app_note_fl      = st.text_area("Note fluoresceinogramma", "", key="li_note_fl")
        app_note         = st.text_area("Note appoggio", "", key="li_app_note")

        # ---- SALVA ----
        submitted = st.form_submit_button("💾 Salva scheda lente")

    if submitted:
        data_iso        = _parse_date(data_scheda) or date.today().isoformat()
        topo_data_iso   = _parse_date(topo_data) or ""
        app_data_iso    = _parse_date(app_data) or ""
        now_iso         = datetime.now().isoformat(timespec="seconds")

        flange_json  = json.dumps(flange_data, ensure_ascii=False)
        mis_json     = json.dumps(misurazioni, ensure_ascii=False)

        try:
            ph = _ph(46)
            cur.execute(f"""
                INSERT INTO Lenti_Inverse (
                    paziente_id, occhio, data_scheda,
                    topo_k_flat_mm, topo_k_flat_D, topo_k_steep_mm, topo_k_steep_D,
                    topo_ecc_media, topo_raggio_apicale_mm, topo_dev_std_raggio, topo_dev_std_ecc,
                    topo_topografo, topo_data, topo_misurazioni_json,
                    rx_sfera, rx_cilindro, rx_asse, rx_miopia_tot, rx_miopia_ridurre, rx_avsc, rx_avcc,
                    lente_tipo_zo, lente_r0_mm, lente_rb_mm, lente_ecc_zo, lente_fattore_p,
                    lente_fattore_appiatt, lente_zo_diam_mm, lente_clearance_mm,
                    lente_c0, lente_c1, lente_c2, lente_c3, lente_c4, lente_c5, lente_c6,
                    lente_flange_json, lente_diam_tot_mm, lente_potere_D,
                    lente_materiale, lente_dk, lente_puntino, lente_note,
                    app_data, app_tipo, app_clearance_centrale, app_clearance_periferica,
                    app_pattern, app_centratura, app_movimento_mm, app_valutazione,
                    app_modifiche, app_operatore, app_note_fluoresceina, app_note,
                    created_at, updated_at
                ) VALUES ({_ph(58)})
            """, (
                paz_id, occhio, data_iso,
                topo_k_flat_mm, topo_k_flat_D, topo_k_steep_mm, topo_k_steep_D,
                topo_ecc_media, topo_raggio_mm, topo_dev_r, topo_dev_e,
                topo_topografo, topo_data_iso, mis_json,
                rx_sf, rx_cil, int(rx_ax), rx_miopia_tot, rx_miopia_rid, rx_avsc, rx_avcc,
                lente_tipo_zo, lente_r0, lente_rb, lente_ecc_zo, lente_p,
                lente_appiatt, lente_zo_diam, lente_clearance,
                curve_vals[0], curve_vals[1], curve_vals[2], curve_vals[3],
                curve_vals[4], curve_vals[5], curve_vals[6],
                flange_json, lente_diam_tot, lente_potere,
                lente_materiale, lente_dk, 1 if lente_puntino else 0, lente_note,
                app_data_iso, app_tipo, app_cen, app_per,
                app_pattern, app_centratura, app_mov, app_valutazione,
                app_modifiche, app_operatore, app_note_fl, app_note,
                now_iso, now_iso,
            ))
            conn.commit()
            st.success(f"✅ Scheda lente {occhio} salvata correttamente.")
        except Exception as e:
            st.error(f"Errore salvataggio: {e}")


# ---------------------------------------------------------------------------
# Tab: Schede esistenti
# ---------------------------------------------------------------------------

def _ui_storico_schede(conn, cur, paz_id: int):
    st.subheader("Schede lente esistenti")

    try:
        cur.execute(
            "SELECT * FROM Lenti_Inverse WHERE paziente_id = ? ORDER BY data_scheda DESC, id DESC",
            (paz_id,)
        )
    except Exception:
        cur.execute(
            "SELECT * FROM Lenti_Inverse WHERE paziente_id = %s ORDER BY data_scheda DESC, id DESC",
            (paz_id,)
        )

    schede = cur.fetchall()

    if not schede:
        st.info("Nessuna scheda lente per questo paziente.")
        return

    for s in schede:
        sid        = _row_get(s, "id")
        occhio     = _row_get(s, "occhio", "?")
        data_s     = _row_get(s, "data_scheda", "")
        rb         = _row_get(s, "lente_rb_mm")
        zo         = _row_get(s, "lente_zo_diam_mm")
        diam       = _row_get(s, "lente_diam_tot_mm")
        potere     = _row_get(s, "lente_potere_D")
        mat        = _row_get(s, "lente_materiale", "")
        valut      = _row_get(s, "app_valutazione", "")

        label = f"🔵 {occhio} | {data_s} | Rb={rb} mm | Ø={diam} mm | ZO={zo} mm | {potere} D | {mat}"
        with st.expander(label):
            st.markdown("#### Parametri principali")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Rb (mm)", f"{rb:.3f}" if rb else "—")
            c2.metric("Ø tot (mm)", f"{diam:.1f}" if diam else "—")
            c3.metric("ZO (mm)", f"{zo:.1f}" if zo else "—")
            c4.metric("Potere (D)", f"{potere:+.2f}" if potere else "—")

            st.markdown("#### Topografia")
            c5, c6, c7, c8 = st.columns(4)
            c5.metric("K flat (mm)", f"{_row_get(s,'topo_k_flat_mm'):.2f}" if _row_get(s,'topo_k_flat_mm') else "—")
            c6.metric("K steep (mm)", f"{_row_get(s,'topo_k_steep_mm'):.2f}" if _row_get(s,'topo_k_steep_mm') else "—")
            c7.metric("Ecc. media", f"{_row_get(s,'topo_ecc_media'):.2f}" if _row_get(s,'topo_ecc_media') else "—")
            c8.metric("Raggio apicale", f"{_row_get(s,'topo_raggio_apicale_mm'):.2f}" if _row_get(s,'topo_raggio_apicale_mm') else "—")

            st.markdown("#### Refrazione")
            c9, c10, c11 = st.columns(3)
            c9.metric("Miopia tot (D)", f"{_row_get(s,'rx_miopia_tot'):+.2f}" if _row_get(s,'rx_miopia_tot') else "—")
            c10.metric("Miopia da ridurre (D)", f"{_row_get(s,'rx_miopia_ridurre'):+.2f}" if _row_get(s,'rx_miopia_ridurre') else "—")
            c11.metric("AVSC", _row_get(s,'rx_avsc','—'))

            st.markdown("#### Appoggio LAC")
            ca1, ca2, ca3 = st.columns(3)
            ca1.metric("Tipo", _row_get(s,'app_tipo','—'))
            ca2.metric("Pattern", _row_get(s,'app_pattern','—'))
            ca3.metric("Valutazione", valut or "—")

            # Flange
            flange_raw = _row_get(s, "lente_flange_json", "[]")
            try:
                flange = json.loads(flange_raw) if flange_raw else []
            except Exception:
                flange = []
            if flange:
                st.markdown("#### Flange")
                fl_cols = st.columns(len(flange))
                for i, fl in enumerate(flange):
                    with fl_cols[i]:
                        st.caption(fl.get("nome",""))
                        st.write(f"r={fl.get('raggio_mm','?')} mm")
                        st.write(f"amp={fl.get('ampiezza_mm','?')} mm")
                        st.write(f"Ø={fl.get('diametro_mm','?')} mm")

            st.markdown("#### Curve (c₀…c₆)")
            curve_row = [_row_get(s, f"lente_c{i}") for i in range(7)]
            curve_cols = st.columns(7)
            for i, (col, v) in enumerate(zip(curve_cols, curve_row)):
                col.metric(f"c{i}", f"{v:.3f}" if v is not None else "—")

            st.markdown(f"**Note lente:** {_row_get(s,'lente_note','') or '—'}")
            st.markdown(f"**Note appoggio:** {_row_get(s,'app_note','') or '—'}")

            # Elimina
            if st.button(f"🗑️ Elimina scheda #{sid}", key=f"li_del_{sid}"):
                try:
                    cur.execute("DELETE FROM Lenti_Inverse WHERE id = ?", (sid,))
                except Exception:
                    cur.execute("DELETE FROM Lenti_Inverse WHERE id = %s", (sid,))
                conn.commit()
                st.warning("Scheda eliminata.")
                st.rerun()


# ---------------------------------------------------------------------------
# Tab: Ordini
# ---------------------------------------------------------------------------

def _ui_ordini(conn, cur, paz_id: int):
    st.subheader("Storico ordini lenti")

    # Recupera schede per collegare l'ordine
    try:
        cur.execute(
            "SELECT id, occhio, data_scheda, lente_rb_mm, lente_diam_tot_mm FROM Lenti_Inverse WHERE paziente_id = ? ORDER BY data_scheda DESC",
            (paz_id,)
        )
    except Exception:
        cur.execute(
            "SELECT id, occhio, data_scheda, lente_rb_mm, lente_diam_tot_mm FROM Lenti_Inverse WHERE paziente_id = %s ORDER BY data_scheda DESC",
            (paz_id,)
        )
    schede = cur.fetchall()

    with st.form("form_nuovo_ordine"):
        st.markdown("#### Nuovo ordine")

        if schede:
            scheda_opts = [f"#{_row_get(s,'id')} – {_row_get(s,'occhio')} | {_row_get(s,'data_scheda')} | Rb={_row_get(s,'lente_rb_mm')} Ø={_row_get(s,'lente_diam_tot_mm')}" for s in schede]
            sel_scheda = st.selectbox("Collega a scheda", scheda_opts, key="ord_scheda")
            scheda_id = int(sel_scheda.split("#")[1].split(" ")[0])
        else:
            st.info("Nessuna scheda presente. Crea prima una scheda lente.")
            scheda_id = None
            st.form_submit_button("Salva ordine", disabled=True)
            return

        col_o1, col_o2, col_o3 = st.columns(3)
        with col_o1:
            ord_occhio        = st.selectbox("Occhio", ["OD", "OS", "OD+OS"], key="ord_occhio")
            ord_data          = st.text_input("Data ordine (gg/mm/aaaa)", _today_str(), key="ord_data")
            ord_data_prev     = st.text_input("Consegna prevista (gg/mm/aaaa)", "", key="ord_prev")
        with col_o2:
            ord_fornitore     = st.text_input("Fornitore", "", key="ord_forn")
            ord_laboratorio   = st.text_input("Laboratorio", "", key="ord_lab")
            ord_rif           = st.text_input("Rif. laboratorio", "", key="ord_rif")
        with col_o3:
            ord_stato         = st.selectbox("Stato", ["in_lavorazione","spedito","consegnato","reso","annullato"], key="ord_stato")
            ord_data_eff      = st.text_input("Consegna effettiva (gg/mm/aaaa)", "", key="ord_eff")

        st.markdown("**Parametri ordinati**")
        pc = st.columns(5)
        with pc[0]: p_rb   = st.number_input("Rb (mm)", 7.0, 11.0, 8.73, 0.001, format="%.3f", key="ord_rb")
        with pc[1]: p_zo   = st.number_input("ZO (mm)", 4.0, 10.0, 5.6, 0.1, key="ord_zo")
        with pc[2]: p_diam = st.number_input("Ø tot (mm)", 8.0, 14.0, 10.8, 0.1, key="ord_diam")
        with pc[3]: p_pot  = st.number_input("Potere (D)", -10.0, 10.0, 0.0, 0.25, key="ord_pot")
        with pc[4]: p_mat  = st.text_input("Materiale", "Boston XO", key="ord_mat")

        fl_cols = st.columns(5)
        fl_vals = []
        for i, (col, nome) in enumerate(zip(fl_cols, ["I","II","III","IV","V"])):
            with col:
                v = st.number_input(f"{nome} Fl r (mm)", 5.0, 14.0, 0.0, 0.001, format="%.3f", key=f"ord_fl{i}")
                fl_vals.append(v)
        p_note = st.text_area("Note parametri", "", key="ord_pnote")

        st.markdown("**Costi e fattura**")
        col_c1, col_c2, col_c3, col_c4 = st.columns(4)
        with col_c1: costo_u  = st.number_input("Costo unitario (€)", 0.0, 2000.0, 0.0, 1.0, key="ord_cu")
        with col_c2: costo_cp = st.number_input("Costo coppia (€)", 0.0, 4000.0, 0.0, 1.0, key="ord_cp")
        with col_c3: iva      = st.number_input("IVA (%)", 0.0, 25.0, 22.0, 0.5, key="ord_iva")
        with col_c4: tot_fatt = st.number_input("Totale fattura (€)", 0.0, 5000.0, 0.0, 1.0, key="ord_tot")

        col_f1, col_f2 = st.columns(2)
        with col_f1: num_fatt = st.text_input("N° fattura", "", key="ord_nfatt")
        with col_f2: pag_met  = st.selectbox("Metodo pagamento", ["contante","carta","bonifico","rateizzato"], key="ord_pmet")

        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1: pag_stato = st.selectbox("Stato pagamento", ["da_pagare","pagato","parziale"], key="ord_pst")
        with col_p2: pag_data  = st.text_input("Data pagamento (gg/mm/aaaa)", "", key="ord_pdata")
        with col_p3: ord_note  = st.text_area("Note ordine", "", key="ord_note")

        sub_ord = st.form_submit_button("💾 Salva ordine")

    if sub_ord and scheda_id:
        now_iso = datetime.now().isoformat(timespec="seconds")
        params_json = json.dumps({
            "Rb_mm": p_rb, "zona_ottica_mm": p_zo, "diametro_totale_mm": p_diam,
            "potere_D": p_pot, "materiale": p_mat,
            "flange_r_mm": fl_vals, "note": p_note
        }, ensure_ascii=False)
        try:
            cur.execute(f"""
                INSERT INTO Lenti_Inverse_Ordini (
                    scheda_id, paziente_id, occhio,
                    data_ordine, data_consegna_prev, data_consegna_eff, stato_ordine,
                    fornitore, laboratorio, rif_laboratorio, parametri_json,
                    costo_unitario, costo_coppia, iva_percent, totale_fattura,
                    numero_fattura, pagamento_metodo, pagamento_stato, pagamento_data,
                    note_ordine, created_at
                ) VALUES ({_ph(21)})
            """, (
                scheda_id, paz_id, ord_occhio,
                _parse_date(ord_data), _parse_date(ord_data_prev), _parse_date(ord_data_eff), ord_stato,
                ord_fornitore, ord_laboratorio, ord_rif, params_json,
                costo_u, costo_cp, iva, tot_fatt,
                num_fatt, pag_met, pag_stato, _parse_date(pag_data),
                ord_note, now_iso
            ))
            conn.commit()
            st.success("✅ Ordine salvato.")
        except Exception as e:
            st.error(f"Errore salvataggio ordine: {e}")

    st.divider()
    st.markdown("#### Ordini registrati")
    try:
        cur.execute(
            "SELECT * FROM Lenti_Inverse_Ordini WHERE paziente_id = ? ORDER BY data_ordine DESC, id DESC",
            (paz_id,)
        )
    except Exception:
        cur.execute(
            "SELECT * FROM Lenti_Inverse_Ordini WHERE paziente_id = %s ORDER BY data_ordine DESC, id DESC",
            (paz_id,)
        )
    ordini = cur.fetchall()
    if not ordini:
        st.info("Nessun ordine registrato.")
    else:
        for o in ordini:
            oid   = _row_get(o, "id")
            label = (
                f"📦 #{oid} | {_row_get(o,'occhio','?')} | {_row_get(o,'data_ordine','')} | "
                f"{_row_get(o,'fornitore','')} – {_row_get(o,'laboratorio','')} | "
                f"Stato: {_row_get(o,'stato_ordine','')} | "
                f"Tot: €{_row_get(o,'totale_fattura',0):.2f} | {_row_get(o,'pagamento_stato','')}"
            )
            with st.expander(label):
                pc = json.loads(_row_get(o, "parametri_json", "{}") or "{}")
                c1, c2, c3 = st.columns(3)
                c1.metric("Rb", f"{pc.get('Rb_mm','?')} mm")
                c2.metric("Ø tot", f"{pc.get('diametro_totale_mm','?')} mm")
                c3.metric("Potere", f"{pc.get('potere_D','?')} D")
                st.write(f"**Materiale:** {pc.get('materiale','—')}  |  **Note:** {pc.get('note','—')}")
                st.write(f"**Fattura:** {_row_get(o,'numero_fattura','—')}  |  **Pagamento:** {_row_get(o,'pagamento_metodo','')} – {_row_get(o,'pagamento_stato','')}")
                if st.button(f"🗑️ Elimina ordine #{oid}", key=f"del_ord_{oid}"):
                    try:
                        cur.execute("DELETE FROM Lenti_Inverse_Ordini WHERE id = ?", (oid,))
                    except Exception:
                        cur.execute("DELETE FROM Lenti_Inverse_Ordini WHERE id = %s", (oid,))
                    conn.commit()
                    st.warning("Ordine eliminato.")
                    st.rerun()


# ---------------------------------------------------------------------------
# Tab: Visite di controllo
# ---------------------------------------------------------------------------

def _ui_visite(conn, cur, paz_id: int):
    st.subheader("Visite di controllo post-applicazione")

    try:
        cur.execute(
            "SELECT id, occhio, data_scheda FROM Lenti_Inverse WHERE paziente_id = ? ORDER BY data_scheda DESC",
            (paz_id,)
        )
    except Exception:
        cur.execute(
            "SELECT id, occhio, data_scheda FROM Lenti_Inverse WHERE paziente_id = %s ORDER BY data_scheda DESC",
            (paz_id,)
        )
    schede = cur.fetchall()

    with st.form("form_nuova_visita"):
        st.markdown("#### Nuova visita di controllo")

        if not schede:
            st.info("Crea prima una scheda lente.")
            st.form_submit_button("Salva visita", disabled=True)
            return

        scheda_opts = [f"#{_row_get(s,'id')} – {_row_get(s,'occhio')} | {_row_get(s,'data_scheda')}" for s in schede]
        sel_s = st.selectbox("Scheda di riferimento", scheda_opts, key="vis_scheda")
        scheda_id = int(sel_s.split("#")[1].split(" ")[0])

        col_v1, col_v2 = st.columns(2)
        with col_v1:
            vis_data = st.text_input("Data visita (gg/mm/aaaa)", _today_str(), key="vis_data")
            vis_tipo = st.selectbox("Tipo visita", [
                "prima_applicazione", "controllo_1_notte", "controllo_1_settimana",
                "controllo_1_mese", "controllo_3_mesi", "controllo_6_mesi",
                "controllo_annuale", "urgenza", "altro"
            ], key="vis_tipo")
            vis_op   = st.text_input("Operatore", "", key="vis_op")
        with col_v2:
            vis_sodd = st.slider("Soddisfazione paziente (1–10)", 1, 10, 8, key="vis_sodd")
            vis_resid_od = st.number_input("Effetto residuo OD (D)", -10.0, 10.0, 0.0, 0.25, key="vis_resod")
            vis_resid_os = st.number_input("Effetto residuo OS (D)", -10.0, 10.0, 0.0, 0.25, key="vis_resos")

        st.markdown("**Refrazione post-OK**")
        rx_cols = st.columns(4)
        with rx_cols[0]: v_od_sf   = st.number_input("OD SF (D)", -20.0, 5.0, 0.0, 0.25, key="vis_od_sf")
        with rx_cols[1]: v_od_cil  = st.number_input("OD CIL (D)", -5.0, 5.0, 0.0, 0.25, key="vis_od_cil")
        with rx_cols[2]: v_od_ax   = st.number_input("OD AX (°)", 0, 180, 0, 1, key="vis_od_ax")
        with rx_cols[3]: v_od_avsc = st.text_input("OD AVSC", "", key="vis_od_av")

        rx_cols2 = st.columns(4)
        with rx_cols2[0]: v_os_sf   = st.number_input("OS SF (D)", -20.0, 5.0, 0.0, 0.25, key="vis_os_sf")
        with rx_cols2[1]: v_os_cil  = st.number_input("OS CIL (D)", -5.0, 5.0, 0.0, 0.25, key="vis_os_cil")
        with rx_cols2[2]: v_os_ax   = st.number_input("OS AX (°)", 0, 180, 0, 1, key="vis_os_ax")
        with rx_cols2[3]: v_os_avsc = st.text_input("OS AVSC", "", key="vis_os_av")

        vis_note = st.text_area("Note visita", "", key="vis_note")

        sub_vis = st.form_submit_button("💾 Salva visita")

    if sub_vis:
        now_iso = datetime.now().isoformat(timespec="seconds")
        try:
            cur.execute(f"""
                INSERT INTO Lenti_Inverse_Visite (
                    scheda_id, paziente_id, data_visita, tipo_visita,
                    rx_post_od_sf, rx_post_od_cil, rx_post_od_ax, rx_post_od_avsc,
                    rx_post_os_sf, rx_post_os_cil, rx_post_os_ax, rx_post_os_avsc,
                    effetto_residuo_od, effetto_residuo_os, soddisfazione,
                    operatore, note_visita, created_at
                ) VALUES ({_ph(18)})
            """, (
                scheda_id, paz_id, _parse_date(vis_data), vis_tipo,
                v_od_sf, v_od_cil, int(v_od_ax), v_od_avsc,
                v_os_sf, v_os_cil, int(v_os_ax), v_os_avsc,
                vis_resid_od, vis_resid_os, vis_sodd,
                vis_op, vis_note, now_iso
            ))
            conn.commit()
            st.success("✅ Visita di controllo salvata.")
        except Exception as e:
            st.error(f"Errore salvataggio visita: {e}")

    st.divider()
    st.markdown("#### Visite registrate")
    try:
        cur.execute(
            "SELECT * FROM Lenti_Inverse_Visite WHERE paziente_id = ? ORDER BY data_visita DESC, id DESC",
            (paz_id,)
        )
    except Exception:
        cur.execute(
            "SELECT * FROM Lenti_Inverse_Visite WHERE paziente_id = %s ORDER BY data_visita DESC, id DESC",
            (paz_id,)
        )
    visite = cur.fetchall()
    if not visite:
        st.info("Nessuna visita registrata.")
    else:
        for v in visite:
            vid   = _row_get(v, "id")
            label = (
                f"🩺 #{vid} | {_row_get(v,'data_visita','')} | "
                f"{_row_get(v,'tipo_visita','')} | "
                f"Soddisfazione: {_row_get(v,'soddisfazione','?')}/10 | "
                f"Res OD={_row_get(v,'effetto_residuo_od',0):+.2f}D  OS={_row_get(v,'effetto_residuo_os',0):+.2f}D"
            )
            with st.expander(label):
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("OD AVSC", _row_get(v,'rx_post_od_avsc','—'))
                c2.metric("OS AVSC", _row_get(v,'rx_post_os_avsc','—'))
                c3.metric("Res. OD (D)", f"{_row_get(v,'effetto_residuo_od',0):+.2f}")
                c4.metric("Res. OS (D)", f"{_row_get(v,'effetto_residuo_os',0):+.2f}")
                st.write(f"**Note:** {_row_get(v,'note_visita','') or '—'}")
                if st.button(f"🗑️ Elimina visita #{vid}", key=f"del_vis_{vid}"):
                    try:
                        cur.execute("DELETE FROM Lenti_Inverse_Visite WHERE id = ?", (vid,))
                    except Exception:
                        cur.execute("DELETE FROM Lenti_Inverse_Visite WHERE id = %s", (vid,))
                    conn.commit()
                    st.warning("Visita eliminata.")
                    st.rerun()
