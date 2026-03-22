# -*- coding: utf-8 -*-
"""
Modulo: Esami Strumentali Oculistici
Gestionale The Organism – PNEV

Esami gestiti:
  - Campo visivo (Humphrey / Octopus)
  - OCT Retina / RNFL
  - OCT Macula
  - OCT ONH / RNFL circumpapillare

Per ogni esame:
  - Inserimento manuale valori numerici
  - Caricamento immagine
  - Analisi AI dell'immagine (Claude Vision via API Anthropic)
  - Generazione relazione strutturata (canovaccio OCT / CNV)
  - Correlazione con indicatori neurodegenerativi
  - Storico nel tempo per paziente

Canovaccio referto basato su: DR. Mario R Romano, Caserta 2006
"""

import json
import base64
import streamlit as st
import pandas as pd
from datetime import datetime, date


# ---------------------------------------------------------------------------
# Helpers DB
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
    return False

def _ph(n, conn):
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
# DB Init
# ---------------------------------------------------------------------------

_SQL_PG = """
CREATE TABLE IF NOT EXISTS esami_strumentali (
    id                  BIGSERIAL PRIMARY KEY,
    paziente_id         BIGINT NOT NULL,
    data_esame          TEXT,
    tipo_esame          TEXT,
    operatore           TEXT,
    strumento           TEXT,
    cv_md_od            DOUBLE PRECISION,
    cv_md_os            DOUBLE PRECISION,
    cv_psd_od           DOUBLE PRECISION,
    cv_psd_os           DOUBLE PRECISION,
    cv_vfi_od           DOUBLE PRECISION,
    cv_vfi_os           DOUBLE PRECISION,
    cv_pattern_od       TEXT,
    cv_pattern_os       TEXT,
    cv_affidabilita_od  TEXT,
    cv_affidabilita_os  TEXT,
    oct_rnfl_sup_od     DOUBLE PRECISION,
    oct_rnfl_nas_od     DOUBLE PRECISION,
    oct_rnfl_inf_od     DOUBLE PRECISION,
    oct_rnfl_tem_od     DOUBLE PRECISION,
    oct_rnfl_avg_od     DOUBLE PRECISION,
    oct_rnfl_sup_os     DOUBLE PRECISION,
    oct_rnfl_nas_os     DOUBLE PRECISION,
    oct_rnfl_inf_os     DOUBLE PRECISION,
    oct_rnfl_tem_os     DOUBLE PRECISION,
    oct_rnfl_avg_os     DOUBLE PRECISION,
    oct_mac_cst_od      DOUBLE PRECISION,
    oct_mac_cst_os      DOUBLE PRECISION,
    oct_mac_vol_od      DOUBLE PRECISION,
    oct_mac_vol_os      DOUBLE PRECISION,
    oct_mac_settori_od  TEXT,
    oct_mac_settori_os  TEXT,
    oct_onh_cd_od       DOUBLE PRECISION,
    oct_onh_cd_os       DOUBLE PRECISION,
    oct_onh_area_od     DOUBLE PRECISION,
    oct_onh_area_os     DOUBLE PRECISION,
    oct_onh_rim_od      DOUBLE PRECISION,
    oct_onh_rim_os      DOUBLE PRECISION,
    desc_od             TEXT,
    desc_os             TEXT,
    conclusioni_od      TEXT,
    conclusioni_os      TEXT,
    relazione_ai        TEXT,
    flag_neuro          INTEGER DEFAULT 0,
    note                TEXT,
    immagine_od_b64     TEXT,
    immagine_os_b64     TEXT,
    created_at          TEXT
)
"""

_SQL_SL = """
CREATE TABLE IF NOT EXISTS esami_strumentali (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paziente_id INTEGER NOT NULL,
    data_esame TEXT, tipo_esame TEXT, operatore TEXT, strumento TEXT,
    cv_md_od REAL, cv_md_os REAL, cv_psd_od REAL, cv_psd_os REAL,
    cv_vfi_od REAL, cv_vfi_os REAL, cv_pattern_od TEXT, cv_pattern_os TEXT,
    cv_affidabilita_od TEXT, cv_affidabilita_os TEXT,
    oct_rnfl_sup_od REAL, oct_rnfl_nas_od REAL, oct_rnfl_inf_od REAL,
    oct_rnfl_tem_od REAL, oct_rnfl_avg_od REAL,
    oct_rnfl_sup_os REAL, oct_rnfl_nas_os REAL, oct_rnfl_inf_os REAL,
    oct_rnfl_tem_os REAL, oct_rnfl_avg_os REAL,
    oct_mac_cst_od REAL, oct_mac_cst_os REAL,
    oct_mac_vol_od REAL, oct_mac_vol_os REAL,
    oct_mac_settori_od TEXT, oct_mac_settori_os TEXT,
    oct_onh_cd_od REAL, oct_onh_cd_os REAL,
    oct_onh_area_od REAL, oct_onh_area_os REAL,
    oct_onh_rim_od REAL, oct_onh_rim_os REAL,
    desc_od TEXT, desc_os TEXT,
    conclusioni_od TEXT, conclusioni_os TEXT,
    relazione_ai TEXT, flag_neuro INTEGER DEFAULT 0,
    note TEXT, immagine_od_b64 TEXT, immagine_os_b64 TEXT,
    created_at TEXT
)
"""

def _init_db(conn):
    cur = conn.cursor()
    if _is_postgres(conn):
        cur.execute(_SQL_PG)
    else:
        cur.execute(_SQL_SL)
    conn.commit()


# ---------------------------------------------------------------------------
# Classificazione rischio neurodegenerativo
# ---------------------------------------------------------------------------

SOGLIE_RNFL = {
    "normale":    95,   # µm
    "borderline": 80,
    "ridotto":    70,
}

PATTERN_CV_NEURO = [
    "difetto centrale", "scotoma paracentrale", "allargamento macchia cieca",
    "difetto arcuato", "emianopsia", "quadrantopsia",
]

def _flag_neuro(data: dict) -> tuple[bool, list[str]]:
    """
    Valuta indicatori di rischio neurodegenerativo.
    Ritorna (flag, lista_motivi).
    Basato su: Hinton et al. 2017, Thomson et al. 2015,
               Alber et al. 2020 (Alzheimer's & Dementia).
    """
    motivi = []

    # RNFL ridotto – marker precoce Alzheimer/Parkinson
    for occhio, suf in [("OD", "od"), ("OS", "os")]:
        avg = data.get(f"oct_rnfl_avg_{suf}")
        if avg and avg < SOGLIE_RNFL["borderline"]:
            motivi.append(f"RNFL medio {occhio} ridotto ({avg:.0f} µm < {SOGLIE_RNFL['borderline']} µm)")
        inf = data.get(f"oct_rnfl_inf_{suf}")
        if inf and inf < SOGLIE_RNFL["ridotto"]:
            motivi.append(f"RNFL inferiore {occhio} significativamente ridotto ({inf:.0f} µm)")

    # Spessore maculare ridotto – marker Alzheimer
    for occhio, suf in [("OD", "od"), ("OS", "os")]:
        cst = data.get(f"oct_mac_cst_{suf}")
        if cst and cst < 230:
            motivi.append(f"Spessore maculare centrale {occhio} ridotto ({cst:.0f} µm)")

    # Campo visivo – MD molto negativo o pattern compatibile
    for occhio, suf in [("OD", "od"), ("OS", "os")]:
        md = data.get(f"cv_md_{suf}")
        if md is not None and md < -6:
            motivi.append(f"MD campo visivo {occhio} marcatamente alterato ({md:.1f} dB)")
        pat = (data.get(f"cv_pattern_{suf}") or "").lower()
        for p in PATTERN_CV_NEURO:
            if p in pat:
                motivi.append(f"Pattern CV {occhio} compatibile con deficit neuronale: {p}")
                break

    # C/D ratio elevato (ONH)
    for occhio, suf in [("OD", "od"), ("OS", "os")]:
        cd = data.get(f"oct_onh_cd_{suf}")
        if cd and cd > 0.7:
            motivi.append(f"C/D ratio {occhio} elevato ({cd:.2f}) – possibile perdita RNFL")

    return len(motivi) > 0, motivi


# ---------------------------------------------------------------------------
# Analisi AI immagine (Claude Vision)
# ---------------------------------------------------------------------------

def _analisi_ai_immagine(
    img_od_b64: str | None,
    img_os_b64: str | None,
    tipo_esame: str,
    dati_numerici: dict,
    medico: str = "",
    paziente_label: str = "",
) -> str:
    """
    Chiama Claude Sonnet via API Anthropic con le immagini OCT/CV
    e genera un referto strutturato seguendo il canovaccio.
    """
    try:
        import requests

        # Costruisce il prompt clinico
        num_txt = ""
        if dati_numerici:
            num_txt = "\n\nDati numerici registrati:\n"
            for k, v in dati_numerici.items():
                if v not in (None, "", 0):
                    num_txt += f"  {k}: {v}\n"

        prompt_sistema = (
            "Sei un assistente oftalmologico specializzato in refertazione di esami strumentali. "
            "Redigi referti clinici professionali seguendo il canovaccio standard italiano. "
            "Usa terminologia medica appropriata. Sii preciso, conciso e clinicamente rilevante. "
            "Non inventare dati non presenti nell'immagine o nei valori forniti."
        )

        canovaccio = f"""Redigi un referto strutturato per il seguente esame: {tipo_esame}

Paziente: {paziente_label or 'N/D'}
Medico esaminatore: {medico or 'N/D'}
Data: {date.today().strftime('%d/%m/%Y')}
{num_txt}

Il referto deve seguire questa struttura:

**{tipo_esame.upper()}**

**ODx (Occhio Destro)**
[Descrizione dettagliata dei reperti morfologici e funzionali rilevati]

**OSn (Occhio Sinistro)**
[Descrizione dettagliata dei reperti morfologici e funzionali rilevati]

**CONCLUSIONI**

**ODx** [Diagnosi/interpretazione clinica concisa]

**OSn** [Diagnosi/interpretazione clinica concisa]

Se rilevante, aggiungi una nota su eventuali correlazioni con patologie neurodegenerative (Alzheimer, Parkinson, demenza vascolare) basandoti sui dati RNFL e maculari."""

        # Costruisce i messaggi con le immagini
        content = []

        if img_od_b64:
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": img_od_b64,
                }
            })
            content.append({"type": "text", "text": "Immagine Occhio Destro (ODx)"})

        if img_os_b64:
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": img_os_b64,
                }
            })
            content.append({"type": "text", "text": "Immagine Occhio Sinistro (OSn)"})

        content.append({"type": "text", "text": canovaccio})

        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"Content-Type": "application/json"},
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 1500,
                "system": prompt_sistema,
                "messages": [{"role": "user", "content": content}],
            },
            timeout=60,
        )
        data = response.json()
        testo = "".join(
            b.get("text", "") for b in data.get("content", [])
            if b.get("type") == "text"
        )
        return testo.strip() if testo else "Nessuna risposta dall'AI."

    except Exception as e:
        return f"Errore generazione AI: {e}"


def _img_to_b64(uploaded_file) -> str | None:
    """Converte un file Streamlit uploadato in base64 JPEG."""
    if uploaded_file is None:
        return None
    try:
        from PIL import Image
        import io
        img = Image.open(uploaded_file)
        if img.mode != "RGB":
            img = img.convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return base64.b64encode(buf.getvalue()).decode("utf-8")
    except Exception:
        # Fallback: usa i bytes direttamente
        try:
            uploaded_file.seek(0)
            return base64.b64encode(uploaded_file.read()).decode("utf-8")
        except Exception:
            return None


# ---------------------------------------------------------------------------
# UI principale
# ---------------------------------------------------------------------------

def ui_esami_strumentali():
    st.header("Esami Strumentali Oculistici")
    st.caption("Campo visivo · OCT Retina/RNFL · OCT Macula · OCT ONH — con analisi AI e correlazione neurodegenerativa")

    conn = _get_conn()
    _init_db(conn)
    cur = conn.cursor()

    # Seleziona paziente
    try:
        cur.execute('SELECT id, "Cognome", "Nome" FROM "Pazienti" ORDER BY "Cognome", "Nome"')
        pazienti = cur.fetchall()
    except Exception:
        try:
            cur.execute("SELECT id, Cognome, Nome FROM Pazienti ORDER BY Cognome, Nome")
            pazienti = cur.fetchall()
        except Exception as e:
            st.error(f"Errore accesso Pazienti: {e}")
            return

    if not pazienti:
        st.info("Nessun paziente registrato.")
        return

    opts = [f"{_row_get(p,'id')} - {_row_get(p,'Cognome','')} {_row_get(p,'Nome','')}".strip()
            for p in pazienti]
    sel = st.selectbox("Seleziona paziente", opts, key="es_paz")
    paz_id = int(sel.split(" - ", 1)[0])
    paz_label = sel.split(" - ", 1)[1] if " - " in sel else ""

    st.divider()

    tab_nuovo, tab_storico = st.tabs(["📋 Nuovo Esame", "📈 Storico & Andamento"])

    with tab_nuovo:
        _ui_nuovo_esame(conn, cur, paz_id, paz_label)
    with tab_storico:
        _ui_storico(conn, cur, paz_id)


# ---------------------------------------------------------------------------
# Tab: Nuovo esame
# ---------------------------------------------------------------------------

def _ui_nuovo_esame(conn, cur, paz_id, paz_label):
    st.subheader("Registra nuovo esame strumentale")

    # Intestazione
    h1, h2, h3, h4 = st.columns(4)
    with h1: tipo_esame  = st.selectbox("Tipo esame", [
        "OCT Retina/RNFL", "OCT Macula", "OCT ONH/RNFL circumpapillare",
        "Campo Visivo (Humphrey)", "Campo Visivo (Octopus)",
        "OCT completo (RNFL + Macula + ONH)", "Campo Visivo + OCT"
    ], key="es_tipo")
    with h2: data_esame  = st.text_input("Data esame (gg/mm/aaaa)", _today_str(), key="es_data")
    with h3: operatore   = st.text_input("Medico esaminatore", "", key="es_op")
    with h4: strumento   = st.text_input("Strumento (es. Cirrus HD-OCT)", "", key="es_strum")

    st.divider()

    # ── Sezioni in base al tipo selezionato ──────────────────────────────
    mostra_cv   = "Campo Visivo" in tipo_esame or tipo_esame == "Campo Visivo + OCT"
    mostra_rnfl = "RNFL" in tipo_esame or "completo" in tipo_esame or "OCT Retina" in tipo_esame
    mostra_mac  = "Macula" in tipo_esame or "completo" in tipo_esame
    mostra_onh  = "ONH" in tipo_esame or "completo" in tipo_esame

    dati = {}

    # ── CAMPO VISIVO ────────────────────────────────────────────────────
    if mostra_cv:
        st.markdown("### 👁️ Campo Visivo")
        cv1, cv2 = st.columns(2)
        with cv1:
            st.markdown("**OD – Occhio Destro**")
            dati["cv_md_od"]  = st.number_input("MD OD (dB)", -35.0, 5.0, 0.0, 0.1, key="cv_md_od")
            dati["cv_psd_od"] = st.number_input("PSD OD (dB)", 0.0, 20.0, 0.0, 0.1, key="cv_psd_od")
            dati["cv_vfi_od"] = st.number_input("VFI OD (%)", 0.0, 100.0, 100.0, 1.0, key="cv_vfi_od")
            dati["cv_pattern_od"] = st.text_input("Pattern difetto OD", "", key="cv_pat_od",
                help="es. difetto arcuato, scotoma paracentrale, emianopsia...")
            dati["cv_affidabilita_od"] = st.selectbox("Affidabilità OD",
                ["Affidabile", "Borderline", "Non affidabile"], key="cv_aff_od")
        with cv2:
            st.markdown("**OS – Occhio Sinistro**")
            dati["cv_md_os"]  = st.number_input("MD OS (dB)", -35.0, 5.0, 0.0, 0.1, key="cv_md_os")
            dati["cv_psd_os"] = st.number_input("PSD OS (dB)", 0.0, 20.0, 0.0, 0.1, key="cv_psd_os")
            dati["cv_vfi_os"] = st.number_input("VFI OS (%)", 0.0, 100.0, 100.0, 1.0, key="cv_vfi_os")
            dati["cv_pattern_os"] = st.text_input("Pattern difetto OS", "", key="cv_pat_os")
            dati["cv_affidabilita_os"] = st.selectbox("Affidabilità OS",
                ["Affidabile", "Borderline", "Non affidabile"], key="cv_aff_os")

    # ── OCT RNFL ────────────────────────────────────────────────────────
    if mostra_rnfl:
        st.markdown("### 🔬 OCT Retina – RNFL (µm)")
        r1, r2 = st.columns(2)
        with r1:
            st.markdown("**OD – Quadranti**")
            dati["oct_rnfl_sup_od"] = st.number_input("Superiore OD", 0.0, 200.0, 0.0, 1.0, key="rnfl_sup_od")
            dati["oct_rnfl_nas_od"] = st.number_input("Nasale OD",    0.0, 200.0, 0.0, 1.0, key="rnfl_nas_od")
            dati["oct_rnfl_inf_od"] = st.number_input("Inferiore OD", 0.0, 200.0, 0.0, 1.0, key="rnfl_inf_od")
            dati["oct_rnfl_tem_od"] = st.number_input("Temporale OD", 0.0, 200.0, 0.0, 1.0, key="rnfl_tem_od")
            dati["oct_rnfl_avg_od"] = st.number_input("Medio OD",     0.0, 200.0, 0.0, 1.0, key="rnfl_avg_od")
        with r2:
            st.markdown("**OS – Quadranti**")
            dati["oct_rnfl_sup_os"] = st.number_input("Superiore OS", 0.0, 200.0, 0.0, 1.0, key="rnfl_sup_os")
            dati["oct_rnfl_nas_os"] = st.number_input("Nasale OS",    0.0, 200.0, 0.0, 1.0, key="rnfl_nas_os")
            dati["oct_rnfl_inf_os"] = st.number_input("Inferiore OS", 0.0, 200.0, 0.0, 1.0, key="rnfl_inf_os")
            dati["oct_rnfl_tem_os"] = st.number_input("Temporale OS", 0.0, 200.0, 0.0, 1.0, key="rnfl_tem_os")
            dati["oct_rnfl_avg_os"] = st.number_input("Medio OS",     0.0, 200.0, 0.0, 1.0, key="rnfl_avg_os")

    # ── OCT MACULA ──────────────────────────────────────────────────────
    if mostra_mac:
        st.markdown("### 🔬 OCT Macula (µm)")
        m1, m2 = st.columns(2)
        with m1:
            st.markdown("**OD**")
            dati["oct_mac_cst_od"] = st.number_input("Spessore centrale (CST) OD", 0.0, 600.0, 0.0, 1.0, key="mac_cst_od")
            dati["oct_mac_vol_od"] = st.number_input("Volume maculare OD (mm³)",   0.0,  20.0, 0.0, 0.1, key="mac_vol_od")
            st.caption("Settori ETDRS OD (µm)")
            sc = st.columns(3)
            s_od = {}
            for i, nome in enumerate(["Sup","Nas","Inf","Tem","Anello sup","Anello nas","Anello inf","Anello tem"]):
                with sc[i % 3]:
                    s_od[nome] = st.number_input(nome, 0.0, 600.0, 0.0, 1.0, key=f"mac_od_{i}")
            dati["oct_mac_settori_od"] = json.dumps(s_od)
        with m2:
            st.markdown("**OS**")
            dati["oct_mac_cst_os"] = st.number_input("Spessore centrale (CST) OS", 0.0, 600.0, 0.0, 1.0, key="mac_cst_os")
            dati["oct_mac_vol_os"] = st.number_input("Volume maculare OS (mm³)",   0.0,  20.0, 0.0, 0.1, key="mac_vol_os")
            st.caption("Settori ETDRS OS (µm)")
            sc2 = st.columns(3)
            s_os = {}
            for i, nome in enumerate(["Sup","Nas","Inf","Tem","Anello sup","Anello nas","Anello inf","Anello tem"]):
                with sc2[i % 3]:
                    s_os[nome] = st.number_input(nome, 0.0, 600.0, 0.0, 1.0, key=f"mac_os_{i}")
            dati["oct_mac_settori_os"] = json.dumps(s_os)

    # ── OCT ONH ─────────────────────────────────────────────────────────
    if mostra_onh:
        st.markdown("### 🔬 OCT Testa del Nervo Ottico (ONH)")
        o1, o2 = st.columns(2)
        with o1:
            st.markdown("**OD**")
            dati["oct_onh_cd_od"]   = st.number_input("C/D ratio OD",       0.0, 1.0, 0.0, 0.01, format="%.2f", key="onh_cd_od")
            dati["oct_onh_area_od"] = st.number_input("Area disco OD (mm²)",0.0, 5.0, 0.0, 0.01, key="onh_area_od")
            dati["oct_onh_rim_od"]  = st.number_input("Rim area OD (mm²)",  0.0, 4.0, 0.0, 0.01, key="onh_rim_od")
        with o2:
            st.markdown("**OS**")
            dati["oct_onh_cd_os"]   = st.number_input("C/D ratio OS",       0.0, 1.0, 0.0, 0.01, format="%.2f", key="onh_cd_os")
            dati["oct_onh_area_os"] = st.number_input("Area disco OS (mm²)",0.0, 5.0, 0.0, 0.01, key="onh_area_os")
            dati["oct_onh_rim_os"]  = st.number_input("Rim area OS (mm²)",  0.0, 4.0, 0.0, 0.01, key="onh_rim_os")

    # ── Descrizione libera ───────────────────────────────────────────────
    st.markdown("### 📝 Descrizione morfologica")
    d1, d2 = st.columns(2)
    with d1:
        dati["desc_od"] = st.text_area("Descrizione OD", "", height=120, key="desc_od",
            help="Descrizione dettagliata reperti morfologici OD (seguire canovaccio OCT)")
    with d2:
        dati["desc_os"] = st.text_area("Descrizione OS", "", height=120, key="desc_os")

    st.markdown("### ✅ Conclusioni")
    c1, c2 = st.columns(2)
    with c1:
        dati["conclusioni_od"] = st.text_area("Conclusioni OD", "", height=80, key="concl_od")
    with c2:
        dati["conclusioni_os"] = st.text_area("Conclusioni OS", "", height=80, key="concl_os")

    dati["note"] = st.text_area("Note aggiuntive", "", key="es_note")

    # ── Caricamento immagini ─────────────────────────────────────────────
    st.markdown("### 🖼️ Immagini esame")
    img_cols = st.columns(2)
    with img_cols[0]:
        img_od_file = st.file_uploader("Immagine OD (JPG/PNG/PDF)", type=["jpg","jpeg","png","pdf"], key="img_od")
        if img_od_file:
            st.image(img_od_file, caption="OD – anteprima", use_container_width=True)
    with img_cols[1]:
        img_os_file = st.file_uploader("Immagine OS (JPG/PNG/PDF)", type=["jpg","jpeg","png","pdf"], key="img_os")
        if img_os_file:
            st.image(img_os_file, caption="OS – anteprima", use_container_width=True)

    # ── Analisi AI ───────────────────────────────────────────────────────
    st.divider()
    st.markdown("### 🤖 Generazione Relazione AI")
    st.caption("Claude analizza le immagini e i valori numerici e genera un referto strutturato seguendo il canovaccio clinico.")

    col_ai1, col_ai2 = st.columns([3,1])
    with col_ai1:
        genera_ai = st.button("Genera relazione con AI", type="primary", key="btn_genera_ai",
            help="Richiede almeno un'immagine caricata o dati numerici compilati")
    with col_ai2:
        salva_btn = st.button("💾 Salva esame", key="btn_salva_esame")

    # Genera relazione AI
    if genera_ai:
        with st.spinner("Analisi AI in corso — elaborazione immagini e generazione referto..."):
            img_od_b64 = _img_to_b64(img_od_file) if img_od_file else None
            img_os_b64 = _img_to_b64(img_os_file) if img_os_file else None

            relazione = _analisi_ai_immagine(
                img_od_b64=img_od_b64,
                img_os_b64=img_os_b64,
                tipo_esame=tipo_esame,
                dati_numerici={k: v for k, v in dati.items()
                               if not k.endswith("_json") and v not in (None, 0, 0.0, "")},
                medico=operatore,
                paziente_label=paz_label,
            )

        st.session_state["_es_relazione"] = relazione
        st.session_state["_es_img_od_b64"] = img_od_b64
        st.session_state["_es_img_os_b64"] = img_os_b64

    # Mostra relazione generata
    if "_es_relazione" in st.session_state:
        rel = st.session_state["_es_relazione"]
        st.markdown("#### Relazione generata")
        relazione_edit = st.text_area("Relazione (modificabile prima di salvare)",
                                      rel, height=400, key="es_relazione_edit")
        st.session_state["_es_relazione_edit"] = relazione_edit

        # Analisi rischio neuro
        flag_n, motivi_n = _flag_neuro(dati)
        if flag_n:
            st.warning(
                "⚠️ **Indicatori compatibili con patologia neurodegenerativa rilevati:**\n\n" +
                "\n".join(f"- {m}" for m in motivi_n) +
                "\n\n*Nota: questa è una valutazione di screening basata sui dati numerici. "
                "Non sostituisce la valutazione clinica.*"
            )
        else:
            st.success("✅ Nessun indicatore di rischio neurodegenerativo rilevato nei dati inseriti.")

    # Salva
    if salva_btn:
        relazione_finale = st.session_state.get("_es_relazione_edit",
                           st.session_state.get("_es_relazione", ""))
        img_od_b64 = st.session_state.get("_es_img_od_b64") or (
            _img_to_b64(img_od_file) if img_od_file else None)
        img_os_b64 = st.session_state.get("_es_img_os_b64") or (
            _img_to_b64(img_os_file) if img_os_file else None)

        flag_n, _ = _flag_neuro(dati)
        now_iso = datetime.now().isoformat(timespec="seconds")

        params = (
            paz_id, _parse_date(data_esame) or date.today().isoformat(),
            tipo_esame, operatore, strumento,
            dati.get("cv_md_od"), dati.get("cv_md_os"),
            dati.get("cv_psd_od"), dati.get("cv_psd_os"),
            dati.get("cv_vfi_od"), dati.get("cv_vfi_os"),
            dati.get("cv_pattern_od"), dati.get("cv_pattern_os"),
            dati.get("cv_affidabilita_od"), dati.get("cv_affidabilita_os"),
            dati.get("oct_rnfl_sup_od"), dati.get("oct_rnfl_nas_od"),
            dati.get("oct_rnfl_inf_od"), dati.get("oct_rnfl_tem_od"),
            dati.get("oct_rnfl_avg_od"),
            dati.get("oct_rnfl_sup_os"), dati.get("oct_rnfl_nas_os"),
            dati.get("oct_rnfl_inf_os"), dati.get("oct_rnfl_tem_os"),
            dati.get("oct_rnfl_avg_os"),
            dati.get("oct_mac_cst_od"), dati.get("oct_mac_cst_os"),
            dati.get("oct_mac_vol_od"), dati.get("oct_mac_vol_os"),
            dati.get("oct_mac_settori_od"), dati.get("oct_mac_settori_os"),
            dati.get("oct_onh_cd_od"), dati.get("oct_onh_cd_os"),
            dati.get("oct_onh_area_od"), dati.get("oct_onh_area_os"),
            dati.get("oct_onh_rim_od"), dati.get("oct_onh_rim_os"),
            dati.get("desc_od"), dati.get("desc_os"),
            dati.get("conclusioni_od"), dati.get("conclusioni_os"),
            relazione_finale, 1 if flag_n else 0,
            dati.get("note"), img_od_b64, img_os_b64, now_iso,
        )
        ph = _ph(len(params), conn)
        sql = (
            "INSERT INTO esami_strumentali ("
            "paziente_id, data_esame, tipo_esame, operatore, strumento,"
            "cv_md_od, cv_md_os, cv_psd_od, cv_psd_os, cv_vfi_od, cv_vfi_os,"
            "cv_pattern_od, cv_pattern_os, cv_affidabilita_od, cv_affidabilita_os,"
            "oct_rnfl_sup_od, oct_rnfl_nas_od, oct_rnfl_inf_od, oct_rnfl_tem_od, oct_rnfl_avg_od,"
            "oct_rnfl_sup_os, oct_rnfl_nas_os, oct_rnfl_inf_os, oct_rnfl_tem_os, oct_rnfl_avg_os,"
            "oct_mac_cst_od, oct_mac_cst_os, oct_mac_vol_od, oct_mac_vol_os,"
            "oct_mac_settori_od, oct_mac_settori_os,"
            "oct_onh_cd_od, oct_onh_cd_os, oct_onh_area_od, oct_onh_area_os,"
            "oct_onh_rim_od, oct_onh_rim_os,"
            "desc_od, desc_os, conclusioni_od, conclusioni_os,"
            "relazione_ai, flag_neuro, note, immagine_od_b64, immagine_os_b64, created_at"
            f") VALUES ({ph})"
        )
        try:
            cur.execute(sql, params)
            conn.commit()
            # Pulisci sessione
            for k in ["_es_relazione", "_es_relazione_edit", "_es_img_od_b64", "_es_img_os_b64"]:
                st.session_state.pop(k, None)
            st.success("✅ Esame salvato correttamente.")
        except Exception as e:
            st.error(f"Errore salvataggio: {e}")


# ---------------------------------------------------------------------------
# Tab: Storico
# ---------------------------------------------------------------------------

def _ui_storico(conn, cur, paz_id):
    st.subheader("Storico esami strumentali")
    ph1 = _ph(1, conn)

    try:
        cur.execute(
            "SELECT * FROM esami_strumentali WHERE paziente_id = " + ph1 +
            " ORDER BY data_esame DESC, id DESC",
            (paz_id,)
        )
        esami = cur.fetchall()
    except Exception as e:
        st.error(f"Errore lettura storico: {e}")
        return

    if not esami:
        st.info("Nessun esame strumentale registrato per questo paziente.")
        return

    # Grafici andamento RNFL e MD nel tempo
    rnfl_rows = []
    cv_rows   = []
    for e in esami:
        data = _row_get(e, "data_esame", "")
        avg_od = _row_get(e, "oct_rnfl_avg_od")
        avg_os = _row_get(e, "oct_rnfl_avg_os")
        md_od  = _row_get(e, "cv_md_od")
        md_os  = _row_get(e, "cv_md_os")
        if avg_od or avg_os:
            rnfl_rows.append({"Data": data,
                               "RNFL medio OD (µm)": avg_od or 0,
                               "RNFL medio OS (µm)": avg_os or 0})
        if md_od or md_os:
            cv_rows.append({"Data": data,
                             "MD OD (dB)": md_od or 0,
                             "MD OS (dB)": md_os or 0})

    if rnfl_rows or cv_rows:
        st.markdown("#### Andamento nel tempo")
        cg1, cg2 = st.columns(2)
        if rnfl_rows:
            with cg1:
                st.markdown("**RNFL medio (µm)**")
                df_r = pd.DataFrame(rnfl_rows).sort_values("Data")
                st.line_chart(df_r.set_index("Data"))
                # Soglia normale
                st.caption("Soglia normale: > 95 µm | Borderline: 80–95 µm | Ridotto: < 80 µm")
        if cv_rows:
            with cg2:
                st.markdown("**MD Campo Visivo (dB)**")
                df_c = pd.DataFrame(cv_rows).sort_values("Data")
                st.line_chart(df_c.set_index("Data"))
                st.caption("Normale: > −2 dB | Lieve: −2 / −6 | Moderato: −6 / −12 | Grave: < −12")

    st.divider()

    # Elenco esami
    for e in esami:
        eid   = _row_get(e, "id")
        tipo  = _row_get(e, "tipo_esame", "Esame")
        data  = _row_get(e, "data_esame", "")
        flag  = _row_get(e, "flag_neuro", 0)
        tag   = " 🧠" if flag else ""
        label = f"#{eid} | {data} | {tipo}{tag}"

        with st.expander(label):
            # Metriche principali
            c1, c2, c3, c4 = st.columns(4)
            avg_od = _row_get(e, "oct_rnfl_avg_od")
            avg_os = _row_get(e, "oct_rnfl_avg_os")
            md_od  = _row_get(e, "cv_md_od")
            md_os  = _row_get(e, "cv_md_os")
            c1.metric("RNFL medio OD", f"{avg_od:.0f} µm" if avg_od else "—")
            c2.metric("RNFL medio OS", f"{avg_os:.0f} µm" if avg_os else "—")
            c3.metric("MD OD",         f"{md_od:.1f} dB"  if md_od is not None else "—")
            c4.metric("MD OS",         f"{md_os:.1f} dB"  if md_os is not None else "—")

            # Descrizioni
            desc_od = _row_get(e, "desc_od", "")
            desc_os = _row_get(e, "desc_os", "")
            concl_od = _row_get(e, "conclusioni_od", "")
            concl_os = _row_get(e, "conclusioni_os", "")

            if desc_od or desc_os:
                st.markdown("**Descrizione morfologica**")
                if desc_od: st.markdown(f"*ODx:* {desc_od}")
                if desc_os: st.markdown(f"*OSn:* {desc_os}")
            if concl_od or concl_os:
                st.markdown("**Conclusioni**")
                if concl_od: st.markdown(f"*ODx:* {concl_od}")
                if concl_os: st.markdown(f"*OSn:* {concl_os}")

            # Relazione AI
            rel = _row_get(e, "relazione_ai", "")
            if rel:
                with st.expander("📄 Relazione AI completa"):
                    st.markdown(rel)

            # Immagini salvate
            img_od_b64 = _row_get(e, "immagine_od_b64")
            img_os_b64 = _row_get(e, "immagine_os_b64")
            if img_od_b64 or img_os_b64:
                st.markdown("**Immagini**")
                ic1, ic2 = st.columns(2)
                if img_od_b64:
                    with ic1:
                        import base64
                        img_bytes = base64.b64decode(img_od_b64)
                        st.image(img_bytes, caption="OD", use_container_width=True)
                if img_os_b64:
                    with ic2:
                        img_bytes = base64.b64decode(img_os_b64)
                        st.image(img_bytes, caption="OS", use_container_width=True)

            # Flag neuro
            if flag:
                st.warning("🧠 Questo esame presenta indicatori compatibili con patologia neurodegenerativa.")

            # Elimina
            if st.button(f"🗑️ Elimina esame #{eid}", key=f"del_es_{eid}"):
                try:
                    cur.execute(
                        "DELETE FROM esami_strumentali WHERE id = " + ph1, (eid,))
                    conn.commit()
                    st.warning("Esame eliminato.")
                    st.rerun()
                except Exception as ex:
                    st.error(f"Errore: {ex}")
