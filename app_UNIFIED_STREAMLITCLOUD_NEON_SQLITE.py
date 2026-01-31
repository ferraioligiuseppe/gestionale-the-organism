import streamlit as st
import sqlite3
from datetime import date, datetime
from typing import Optional, Dict
import os
import io
import csv
from functools import lru_cache
import math  # <-- aggiungi questa riga se non c'è
import textwrap  # per andare a capo nel referto

# PDF (referti e prescrizioni A4/A5)
try:
    from reportlab.lib.pagesizes import A4, A5
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


# -----------------------------
# -----------------------------
# Configurazione accesso (login semplice)
# - In locale: fallback admin/admin123
# - In Cloud: usa Secrets [auth] oppure [users]
# -----------------------------

APP_VERSION = "UNIFIED-SQLITE-NEON-2026-01-31"

def _safe_secrets():
    try:
        return getattr(st, "secrets", {}) or {}
    except Exception:
        return {}

def load_users_dynamic() -> dict:
    """Carica credenziali da secrets (Streamlit Cloud o locale), con fallback."""
    sec = _safe_secrets()

    # Multi-utente: [users]
    try:
        users = sec.get("users", {})
        if isinstance(users, dict) and users:
            return {str(k).strip(): str(v).strip() for k, v in users.items()}
    except Exception:
        pass

    # Singolo utente: [auth]
    try:
        auth = sec.get("auth", {})
        if isinstance(auth, dict):
            u = str(auth.get("username", "")).strip()
            p = str(auth.get("password", "")).strip()
            if u and p:
                return {u: p}
    except Exception:
        pass

    # Fallback locale
    return {"admin": "admin123"}

def login() -> bool:
    """Login semplice con username/password."""
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
    if "logged_user" not in st.session_state:
        st.session_state["logged_user"] = None

    if st.session_state["logged_in"]:
        st.sidebar.markdown(f"👤 Utente: **{st.session_state['logged_user']}**")
        if st.sidebar.button("Logout"):
            st.session_state["logged_in"] = False
            st.session_state["logged_user"] = None
            st.rerun()
        return True

    st.title("The Organism – Login")
    st.caption(f"Versione: {APP_VERSION}")

    users = load_users_dynamic()

    user = st.text_input("Username")
    pwd = st.text_input("Password", type="password")

    if st.button("Accedi"):
        if user in users and users[user] == pwd:
            st.session_state["logged_in"] = True
            st.session_state["logged_user"] = user
            st.success("Accesso effettuato.")
            st.rerun()
        else:
            st.error("Credenziali errate.")
    return False


# -----------------------------
# Database (SQLite locale / PostgreSQL-Neon in Cloud)
# -----------------------------

SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", "the_organism_gestionale_v2.db")

try:
    import psycopg2
    import psycopg2.extras
    PSYCOPG2_AVAILABLE = True
except Exception:
    psycopg2 = None
    PSYCOPG2_AVAILABLE = False

def _get_database_url() -> str:
    sec = _safe_secrets()
    # Prefer [db].DATABASE_URL
    try:
        dbsec = sec.get("db", {})
        if isinstance(dbsec, dict) and dbsec.get("DATABASE_URL"):
            return str(dbsec.get("DATABASE_URL")).strip()
    except Exception:
        pass
    # Fallback: top-level key
    try:
        if sec.get("DATABASE_URL"):
            return str(sec.get("DATABASE_URL")).strip()
    except Exception:
        pass
    return (os.getenv("DATABASE_URL", "") or "").strip()

def _is_streamlit_cloud() -> bool:
    # euristiche: su Streamlit Cloud esiste /mount/src e HOME tipicamente /home/...
    return os.path.exists("/mount/src") or bool(os.getenv("STREAMLIT_CLOUD")) or bool(os.getenv("STREAMLIT_SHARING"))

_DB_URL = _get_database_url()
_DB_BACKEND = "postgres" if _DB_URL else "sqlite"

def _require_postgres_on_cloud():
    if _is_streamlit_cloud() and _DB_BACKEND != "postgres":
        st.error("❌ DATABASE_URL mancante nei Secrets: in Streamlit Cloud il gestionale richiede PostgreSQL (Neon).")
        st.stop()

class _PgCursor:
    def __init__(self, cur):
        self._cur = cur
    def execute(self, q, params=None):
        # Convert SQLite placeholders (?) to psycopg2 (%s)
        q2 = q.replace("?", "%s")
        return self._cur.execute(q2, params or ())
    def executemany(self, q, seq):
        q2 = q.replace("?", "%s")
        return self._cur.executemany(q2, seq)
    def fetchone(self):
        return self._cur.fetchone()
    def fetchall(self):
        return self._cur.fetchall()
    def __getattr__(self, name):
        return getattr(self._cur, name)

class _PgConn:
    def __init__(self, conn):
        self._conn = conn
    def cursor(self):
        # RealDictCursor restituisce dict (compatibile con r["ID"])
        cur = self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        return _PgCursor(cur)
    def commit(self):
        return self._conn.commit()
    def close(self):
        return self._conn.close()

@st.cache_resource(show_spinner=False)
def _connect_cached():
    _require_postgres_on_cloud()
    if _DB_BACKEND == "postgres":
        if not PSYCOPG2_AVAILABLE:
            raise RuntimeError("psycopg2 non disponibile. Aggiungi psycopg2-binary a requirements.txt")
        conn = psycopg2.connect(_DB_URL)
        return _PgConn(conn)
    else:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

def get_connection():
    return _connect_cached()

def init_db() -> None:
    conn = get_connection()
    cur = conn.cursor()

    if _DB_BACKEND == "sqlite":

        # Pazienti
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS Pazienti (
                ID              INTEGER PRIMARY KEY AUTOINCREMENT,
                Cognome         TEXT NOT NULL,
                Nome            TEXT NOT NULL,
                Data_Nascita    TEXT,
                Sesso           TEXT,
                Telefono        TEXT,
                Email           TEXT,
                Indirizzo       TEXT,
                CAP             TEXT,
                Citta           TEXT,
                Provincia       TEXT,
                Codice_Fiscale  TEXT,
                Stato_Paziente  TEXT
            )
            """
        )

        # Anamnesi
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS Anamnesi (
                ID              INTEGER PRIMARY KEY AUTOINCREMENT,
                Paziente_ID     INTEGER NOT NULL,
                Data_Anamnesi   TEXT,
                Motivo          TEXT,
                Storia          TEXT,
                Note            TEXT,
                -- campi strutturati
                Perinatale      TEXT,
                Sviluppo        TEXT,
                Scuola          TEXT,
                Emotivo         TEXT,
                Sensoriale      TEXT,
                Stile_Vita      TEXT
            )
            """
        )

        # Valutazioni visive / oculistiche
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS Valutazioni_Visive (
                ID                  INTEGER PRIMARY KEY AUTOINCREMENT,
                Paziente_ID         INTEGER NOT NULL,
                Data_Valutazione    TEXT,
                Tipo_Visita         TEXT,
                Professionista      TEXT,

                Anamnesi            TEXT,

                Acuita_Nat_OD       TEXT, Acuita_Nat_OS       TEXT, Acuita_Nat_OO       TEXT,
                Acuita_Corr_OD      TEXT, Acuita_Corr_OS      TEXT, Acuita_Corr_OO      TEXT,

                OD_SF_OBJ           REAL, OD_CIL_OBJ          REAL, OD_AX_OBJ           INTEGER,
                OS_SF_OBJ           REAL, OS_CIL_OBJ          REAL, OS_AX_OBJ           INTEGER,

                OD_SF_SOGG          REAL, OD_CIL_SOGG         REAL, OD_AX_SOGG          INTEGER,
                OS_SF_SOGG          REAL, OS_CIL_SOGG         REAL, OS_AX_SOGG          INTEGER,

                OD_K1_MM            REAL, OD_K1_D             REAL,
                OD_K2_MM            REAL, OD_K2_D             REAL,
                OS_K1_MM            REAL, OS_K1_D             REAL,
                OS_K2_MM            REAL, OS_K2_D             REAL,

                Tonometria_OD       REAL,
                Tonometria_OS       REAL,

                Motilita            TEXT,
                Cover_Test          TEXT,
                Stereopsi           TEXT,
                PPC                 REAL,

                Ishihara            TEXT,
                Pachimetria_OD      REAL,
                Pachimetria_OS      REAL,
                Fondo               TEXT,
                Campo_Visivo        TEXT,
                OCT                 TEXT,
                Topografia          TEXT,

                Costo               REAL DEFAULT 0,
                Pagato              INTEGER DEFAULT 0,
                Stato               TEXT DEFAULT 'BOZZA',

                Esame               TEXT,
                Conclusioni         TEXT,
                Note                TEXT
            )
            """
        )

        # Sedute / terapie
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS Sedute (
                ID              INTEGER PRIMARY KEY AUTOINCREMENT,
                Paziente_ID     INTEGER NOT NULL,
                Data_Seduta     TEXT,
                Terapia         TEXT,
                Professionista  TEXT,
                Costo           REAL DEFAULT 0,
                Pagato          INTEGER DEFAULT 0,
                Note            TEXT
            )
            """
        )

        # Coupons
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS Coupons (
                ID                  INTEGER PRIMARY KEY AUTOINCREMENT,
                Paziente_ID         INTEGER NOT NULL,
                Tipo_Coupon         TEXT,
                Codice_Coupon       TEXT,
                Data_Assegnazione   TEXT,
                Note                TEXT,
                Utilizzato          INTEGER DEFAULT 0
            )
            """
        )

        conn.commit()
        return

    # -------------------------
    # PostgreSQL (Neon) init
    # -------------------------
    cur.execute('''CREATE TABLE IF NOT EXISTS Pazienti (
            ID              BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
            Cognome         TEXT NOT NULL,
            Nome            TEXT NOT NULL,
            Data_Nascita    TEXT,
            Sesso           TEXT,
            Telefono        TEXT,
            Email           TEXT,
            Indirizzo       TEXT,
            CAP             TEXT,
            Citta           TEXT,
            Provincia       TEXT,
            Codice_Fiscale  TEXT,
            Stato_Paziente  TEXT NOT NULL DEFAULT 'ATTIVO'
        )''')


    cur.execute('''CREATE TABLE IF NOT EXISTS Anamnesi (
            ID              BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
            Paziente_ID     INTEGER NOT NULL,
            Data_Anamnesi   TEXT,
            Motivo          TEXT,
            Storia          TEXT,
            Note            TEXT,
            FOREIGN KEY (Paziente_ID) ''')


    cur.execute('''CREATE TABLE IF NOT EXISTS Valutazioni_Visive (
            ID                      BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
            Paziente_ID             INTEGER NOT NULL,
            Data_Valutazione        TEXT,
            Tipo_Visita             TEXT,
            Professionista          TEXT,
            Acuita_Nat_OD           TEXT,
            Acuita_Nat_OS           TEXT,
            Acuita_Nat_OO           TEXT,
            Acuita_Corr_OD          TEXT,
            Acuita_Corr_OS          TEXT,
            Acuita_Corr_OO          TEXT,
            Costo                   REAL,
            Pagato                  INTEGER NOT NULL DEFAULT 0,
            Note                    TEXT,
            FOREIGN KEY (Paziente_ID) ''')


    cur.execute('''CREATE TABLE IF NOT EXISTS Sedute (
            ID              BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
            Paziente_ID     INTEGER NOT NULL,
            Data_Seduta     TEXT,
            Terapia         TEXT,
            Professionista  TEXT,
            Costo           REAL,
            Pagato          INTEGER NOT NULL DEFAULT 0,
            Note            TEXT,
            FOREIGN KEY (Paziente_ID) ''')


    cur.execute('''CREATE TABLE IF NOT EXISTS Coupons (
            ID                BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
            Paziente_ID       INTEGER NOT NULL,
            Tipo_Coupon       TEXT NOT NULL,     -- OF o SDS
            Codice_Coupon     TEXT,              -- numero / codice coupon
            Data_Assegnazione TEXT,
            Note              TEXT,
            Utilizzato        INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (Paziente_ID) ''')

    conn.commit()


def _solo_lettere(s: str) -> str:
    return "".join(ch for ch in s.upper() if ch.isalpha())

def _codice_cognome(cognome: str) -> str:
    s = _solo_lettere(cognome)
    consonanti = [c for c in s if c not in "AEIOU"]
    vocali = [c for c in s if c in "AEIOU"]
    codice = "".join(consonanti + vocali)[:3]
    return (codice + "XXX")[:3]

def _codice_nome(nome: str) -> str:
    s = _solo_lettere(nome)
    consonanti = [c for c in s if c not in "AEIOU"]
    vocali = [c for c in s if c in "AEIOU"]
    if len(consonanti) >= 4:
        # regola CF: 1a, 3a e 4a consonante
        codice = consonanti[0] + consonanti[2] + consonanti[3]
    else:
        codice = "".join(consonanti + vocali)[:3]
    return (codice + "XXX")[:3]

def _codice_data_sesso(d: date, sesso: str) -> str:
    yy = f"{d.year % 100:02d}"
    mm = MESE_CF[d.month]
    giorno = d.day + (40 if sesso.upper().startswith("F") else 0)
    gg = f"{giorno:02d}"
    return yy + mm + gg

def parse_data_it(data_str: str, campo: str = "Data"):
    """
    Prova a interpretare una data scritta in vari modi:
    - gg/mm/aaaa
    - gg-mm-aaaa
    - gg.mm.aaaa
    - gg mm aaaa

    Ritorna:
      - oggetto date se va bene
      - None se non riesce a interpretarla
    """
    if not data_str:
        return None

    s = data_str.strip()

    # unifichiamo i separatori a "/"
    for sep in ["-", ".", " "]:
        s = s.replace(sep, "/")

    # ora ci aspettiamo sempre gg/mm/aaaa
    try:
        d = datetime.strptime(s, "%d/%m/%Y").date()
        return d
    except ValueError:
        return None

CODICI_CATASTALI_CSV = "codici_catastali_comuni.csv"

@lru_cache(maxsize=1)
def load_codici_catastali() -> Dict[tuple, str]:
    """
    Carica i codici catastali da codici_catastali_comuni.csv.

    Formato richiesto (con header):
    paese;prov;codice_catastale
    ABANO TERME;PD;A001
    ...
    """
    mapping: Dict[tuple, str] = {}
    if not os.path.exists(CODICI_CATASTALI_CSV):
        return mapping

    try:
        with open(CODICI_CATASTALI_CSV, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter=";")
            for row in reader:
                comune = (row.get("paese") or "").strip().upper()
                prov = (row.get("prov") or "").strip().upper()
                codice = (row.get("codice_catastale") or "").strip().upper()
                if comune and prov and codice:
                    mapping[(comune, prov)] = codice
    except Exception:
        # in caso di errore restituisce mappa vuota
        return {}

    return mapping


def _codice_catastale(comune: str, provincia: str) -> Optional[str]:
    """
    Ritorna il codice catastale leggendo dal CSV.

    comune: es. 'ABANO TERME'
    provincia: es. 'PD'
    """
    mapping = load_codici_catastali()
    key = (comune.strip().upper(), provincia.strip().upper())
    return mapping.get(key)



def _calcola_carattere_controllo(primi15: str) -> str:
    total = 0
    for i, ch in enumerate(primi15):
        if (i + 1) % 2 == 1:  # posizioni dispari (1-based)
            total += ODD_MAP.get(ch, 0)
        else:
            total += EVEN_MAP.get(ch, 0)
    resto = total % 26
    return CONTROL_CHARS[resto]

def genera_codice_fiscale(
    cognome: str,
    nome: str,
    data_nascita_str: str,
    sesso: str,
    comune_nascita: str,
    provincia_nascita: str,
) -> Optional[str]:
    """
    Genera un codice fiscale di supporto.
    Ritorna None se i dati non sono sufficienti/validi o se il comune non è noto.
    """

    cognome = (cognome or "").strip()
    nome = (nome or "").strip()
    data_nascita_str = (data_nascita_str or "").strip()
    sesso = (sesso or "").strip()
    comune_nascita = (comune_nascita or "").strip()
    provincia_nascita = (provincia_nascita or "").strip()

    if not (cognome and nome and data_nascita_str and sesso and comune_nascita and provincia_nascita):
        return None

    try:
        d = datetime.strptime(data_nascita_str, "%d/%m/%Y").date()
    except ValueError:
        return None

    cod_cat = _codice_catastale(comune_nascita, provincia_nascita)
    if not cod_cat:
        return None

    parte1 = _codice_cognome(cognome)
    parte2 = _codice_nome(nome)
    parte3 = _codice_data_sesso(d, sesso)
    primi15 = (parte1 + parte2 + parte3 + cod_cat).upper()
    if len(primi15) != 15:
        return None

    controllo = _calcola_carattere_controllo(primi15)
    return primi15 + controllo

def valida_codice_fiscale(cf: str) -> bool:
    cf = (cf or "").strip().upper()
    if len(cf) != 16:
        return False
    if not cf.isalnum():
        return False
    primi15 = cf[:15]
    expected = _calcola_carattere_controllo(primi15)
    return cf[-1] == expected

# -----------------------------
# Helpers: Cheratometria & CL tools
# -----------------------------

def cherato_mm_to_D(raggio_mm: float) -> float:
    """
    Conversione approssimata raggio (mm) -> diottrie.
    Formula: D ≈ 337.5 / r (mm)
    """
    if raggio_mm <= 0:
        return 0.0
    return 337.5 / raggio_mm

def cherato_D_to_mm(D: float) -> float:
    """
    Conversione approssimata diottrie -> raggio (mm).
    Formula: r (mm) ≈ 337.5 / D
    """
    if D <= 0:
        return 0.0
    return 337.5 / D

def convert_occhiali_to_cl(sphere_glasses: float, cyl_glasses: float, axis: float, vertex_mm: float = 12.0):
    """
    Conversione approssimata occhiali -> lenti a contatto (sfera + cilindro).
    Usa la formula del potere efficace: F_cl = F_g / (1 - d * F_g), con d in metri.
    Calcola il potere in due meridiani e ricostruisce sfera e cilindro CL.
    """
    d = vertex_mm / 1000.0  # mm -> m
    F1 = sphere_glasses
    F2 = sphere_glasses + cyl_glasses

    def eff(F):
        return F / (1 - d * F) if (1 - d * F) != 0 else F

    F1c = eff(F1)
    F2c = eff(F2)

    sphere_cl = F1c
    cyl_cl = F2c - F1c

    # arrotonda a step 0.25
    sphere_cl = round(sphere_cl * 4) / 4.0
    cyl_cl = round(cyl_cl * 4) / 4.0
    axis_cl = axis  # asse invariato (approssimazione)

    return sphere_cl, cyl_cl, axis_cl

# -----------------------------
# Helpers: Acuità visiva (lista valori)
# -----------------------------

AV_OPTIONS = [
    "NV - non vedente",
    "PL - percezione luce",
    "ML/HM - moto mano",
    "CF 30 cm",
    "CF 50 cm",
    "CF 1 m",
    "1/50",
    "1/20",
    "1/10",
    "2/10",
    "3/10",
    "4/10",
    "5/10",
    "6/10",
    "7/10",
    "8/10",
    "9/10",
    "10/10",
    "12/10",
    "14/10",
    "16/10",
]

def av_select(label: str, current_value: Optional[str], key: str) -> str:
    """
    Selectbox per acuità visiva.
    Mantiene il valore salvato anche se non è in AV_OPTIONS (lo mette in cima).
    """
    base = AV_OPTIONS.copy()
    if current_value and current_value not in base:
        options = [current_value] + base
    else:
        options = [""] + base
    index = 0
    if current_value and current_value in options:
        index = options.index(current_value)
    return st.selectbox(label, options, index=index, key=key)

# -----------------------------
# UI: Pazienti
# -----------------------------

def _format_data_it_from_iso(iso_str: Optional[str]) -> str:
    """
    Converte una data ISO (aaaa-mm-gg) in formato italiano gg/mm/aaaa.
    Se non valida, restituisce la stringa originale.
    """
    if not iso_str:
        return ""
    try:
        d = datetime.strptime(iso_str, "%Y-%m-%d").date()
        return d.strftime("%d/%m/%Y")
    except Exception:
        return iso_str


def genera_referto_oculistico_pdf(paziente, valutazione, include_header: bool) -> bytes:
    """
    Genera un referto oculistico/optometrico in PDF A4.
    Usa solo i dati presenti in anagrafica + valutazione.
    """
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    left = 30 * mm
    right = width - 30 * mm
    top = height - 30 * mm
    bottom = 30 * mm

    y = top

    # Intestazione opzionale (per carta intestata la puoi togliere)
    if include_header:
        c.setFont("Helvetica-Bold", 14)
        c.drawString(left, y, "Studio The Organism")
        y -= 14
        c.setFont("Helvetica", 10)
        c.drawString(left, y, "Via De Rosa 46 – Pagani (SA)")
        y -= 12
        c.drawString(left, y, "Tel: __________   Email: __________   Web: __________")
        y -= 20

    c.setFont("Helvetica-Bold", 12)
    c.drawString(left, y, "Referto oculistico / optometrico")
    y -= 20

    # Dati paziente
    c.setFont("Helvetica", 11)
    nome_paz = f"{paziente['Cognome']} {paziente['Nome']}"
    c.drawString(left, y, f"Paziente: {nome_paz}")
    y -= 14

    dn = _format_data_it_from_iso(paziente["Data_Nascita"])
    if dn:
        c.drawString(left, y, f"Data di nascita: {dn}")
        y -= 14

    # Dati visita
    data_vis = _format_data_it_from_iso(valutazione["Data_Valutazione"])
    if data_vis:
        c.drawString(left, y, f"Data visita: {data_vis}")
        y -= 14

    if valutazione["Tipo_Visita"]:
        c.drawString(left, y, f"Tipo visita: {valutazione['Tipo_Visita']}")
        y -= 14

    if valutazione["Professionista"]:
        c.drawString(left, y, f"Professionista: {valutazione['Professionista']}")
        y -= 18

    # Acuità visiva solo se presenti
    av_lines = []
    if valutazione["Acuita_Nat_OD"] or valutazione["Acuita_Nat_OS"] or valutazione["Acuita_Nat_OO"]:
        av_lines.append(
            "Acuità visiva naturale: "
            f"OD {valutazione['Acuita_Nat_OD'] or '-'}   "
            f"OS {valutazione['Acuita_Nat_OS'] or '-'}   "
            f"OO {valutazione['Acuita_Nat_OO'] or '-'}"
        )
    if valutazione["Acuita_Corr_OD"] or valutazione["Acuita_Corr_OS"] or valutazione["Acuita_Corr_OO"]:
        av_lines.append(
            "Acuità visiva corretta: "
            f"OD {valutazione['Acuita_Corr_OD'] or '-'}   "
            f"OS {valutazione['Acuita_Corr_OS'] or '-'}   "
            f"OO {valutazione['Acuita_Corr_OO'] or '-'}"
        )

    c.setFont("Helvetica", 11)
    for line in av_lines:
        c.drawString(left, y, line)
        y -= 14
    if av_lines:
        y -= 6

    # Corpo del referto: uso il campo Note della valutazione
    testo = valutazione["Note"] or ""
    if testo.strip():
        wrapper = textwrap.TextWrapper(width=90)
        for par in testo.split("\n"):
            par = par.strip()
            if not par:
                y -= 6
                continue
            lines = wrapper.wrap(par)
            for line in lines:
                if y < bottom + 40:
                    c.showPage()
                    c.setFont("Helvetica", 11)
                    y = top
                c.drawString(left, y, line)
                y -= 13
            y -= 4

    # Spazio firma
    if y < bottom + 60:
        c.showPage()
        c.setFont("Helvetica", 11)
        y = top

    y = bottom + 40
    c.line(right - 120, y, right, y)
    c.drawString(right - 110, y + 5, "Firma / Timbro")

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.getvalue()

def draw_axis_arrow(c, center_x, center_y, radius, axis_deg: int):
    """
    Disegna una freccia sulla semicirconferenza per indicare l'asse (0–180°).
    0° = lato destro, 90° = alto, 180° = sinistra.
    """
    axis_deg = max(0, min(180, int(axis_deg)))  # clamp di sicurezza
    angle_rad = math.radians(axis_deg)

    # Punto interno e punto sulla circonferenza
    r1 = radius * 0.7
    r2 = radius * 0.95
    x1 = center_x + r1 * math.cos(angle_rad)
    y1 = center_y + r1 * math.sin(angle_rad)
    x2 = center_x + r2 * math.cos(angle_rad)
    y2 = center_y + r2 * math.sin(angle_rad)

    c.setLineWidth(1)
    # stelo della freccia
    c.line(x1, y1, x2, y2)

    # testa della freccia (due segmentini inclinati)
    head_len = radius * 0.15
    for delta in (-20, 20):
        ang = angle_rad + math.radians(delta)
        hx = x2 - head_len * math.cos(ang)
        hy = y2 - head_len * math.sin(ang)
        c.line(x2, y2, hx, hy)

def draw_axis_arrow(c, center_x, center_y, radius, axis_deg: int):
    """
    Disegna una freccia sulla semicirconferenza per indicare l'asse (0–180°).
    0° = lato destro, 90° = alto, 180° = sinistra.
    """
    axis_deg = max(0, min(180, int(axis_deg)))  # clamp di sicurezza
    angle_rad = math.radians(axis_deg)

    # Punto interno e punto sulla circonferenza
    r1 = radius * 0.7
    r2 = radius * 0.95
    x1 = center_x + r1 * math.cos(angle_rad)
    y1 = center_y + r1 * math.sin(angle_rad)
    x2 = center_x + r2 * math.cos(angle_rad)
    y2 = center_y + r2 * math.sin(angle_rad)

    c.setLineWidth(1)
    # stelo della freccia
    c.line(x1, y1, x2, y2)

    # testa della freccia (due segmentini inclinati)
    head_len = radius * 0.15
    for delta in (-20, 20):
        ang = angle_rad + math.radians(delta)
        hx = x2 - head_len * math.cos(ang)
        hy = y2 - head_len * math.sin(ang)
        c.line(x2, y2, hx, hy)


def genera_prescrizione_occhiali_a5_pdf(
    paziente,
    data_prescrizione_iso: Optional[str],
    sf_lon_od: float, cil_lon_od: float, ax_lon_od: int,
    sf_lon_os: float, cil_lon_os: float, ax_lon_os: int,
    sf_int_od: float, cil_int_od: float, ax_int_od: int,
    sf_int_os: float, cil_int_os: float, ax_int_os: int,
    sf_vic_od: float, cil_vic_od: float, ax_vic_od: int,
    sf_vic_os: float, cil_vic_os: float, ax_vic_os: int,
    lenti_scelte: list,
    altri_trattamenti: str,
    note: str,
) -> bytes:
    """
    Genera una prescrizione occhiali in formato A5 con:
    - margini 3 cm alto/basso, 2 cm dx/sn
    - data in alto a destra
    - nome paziente
    - due semicerchi con gradi (schema TABO semplificato) + freccia dell'asse di LONTANO
    - tre righe LONTANO / INTERMEDIO / VICINO (SF, CIL, AX per OD/OS)
    - lenti consigliate (check)
    - campo note
    """
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A5)
    width, height = A5

    left = 20 * mm
    right = width - 20 * mm
    top = height - 30 * mm
    bottom = 30 * mm

    # Data prescrizione
    c.setFont("Helvetica", 10)
    data_it = _format_data_it_from_iso(data_prescrizione_iso) if data_prescrizione_iso else ""
    if data_it:
        c.drawRightString(right, top, f"Data: {data_it}")

    # Nome paziente
    y = top - 15
    c.setFont("Helvetica-Bold", 11)
    nome_paz = f"{paziente['Cognome']} {paziente['Nome']}"
    c.drawString(left, y, f"Paziente: {nome_paz}")
    y -= 20

    # Semicerchi TABO semplificati per OD e OS
    c.setFont("Helvetica", 8)
    radius = 22 * mm
    center_y = y - radius - 5 * mm
    center_x_os = left + radius
    center_x_od = right - radius

    # OS – semicirconferenza + etichette
    c.arc(
        center_x_os - radius,
        center_y - radius,
        center_x_os + radius,
        center_y + radius,
        0,
        180,
    )
    c.drawString(center_x_os - radius - 4 * mm, center_y, "180° / 0°")
    c.drawString(center_x_os - 5, center_y + radius + 3 * mm, "90°")

    # OD – semicirconferenza + etichette
    c.arc(
        center_x_od - radius,
        center_y - radius,
        center_x_od + radius,
        center_y + radius,
        0,
        180,
    )
    c.drawString(center_x_od - radius - 4 * mm, center_y, "180° / 0°")
    c.drawString(center_x_od - 5, center_y + radius + 3 * mm, "90°")

    # Frecce sull'asse (uso gli assi di LONTANO: ax_lon_os / ax_lon_od)
    try:
        draw_axis_arrow(c, center_x_os, center_y, radius, ax_lon_os)
        draw_axis_arrow(c, center_x_od, center_y, radius, ax_lon_od)
    except Exception:
        # se per qualunque motivo qualcosa va storto, non blocchiamo la prescrizione
        pass

    y = center_y - radius - 10

    # Funzione di utilità per disegnare una riga LONTANO/INTERMEDIO/VICINO
    def draw_riga_prescr(y_start, label, sf_od, cil_od, ax_od, sf_os, cil_os, ax_os):
        # se tutti zero, saltiamo la riga
        if (
            abs(sf_od) < 0.001 and abs(cil_od) < 0.001 and int(ax_od) == 0 and
            abs(sf_os) < 0.001 and abs(cil_os) < 0.001 and int(ax_os) == 0
        ):
            return y_start

        c.setFont("Helvetica-Bold", 9)
        c.drawString(left, y_start, label)
        y = y_start - 11
        c.setFont("Helvetica", 9)
        c.drawString(
            left + 5 * mm,
            y,
            f"OD: SF {sf_od:+.2f}  CIL {cil_od:+.2f}  AX {int(ax_od)}°",
        )
        y -= 10
        c.drawString(
            left + 5 * mm,
            y,
            f"OS: SF {sf_os:+.2f}  CIL {cil_os:+.2f}  AX {int(ax_os)}°",
        )
        return y - 8

    y = draw_riga_prescr(y, "LONTANO", sf_lon_od, cil_lon_od, ax_lon_od, sf_lon_os, cil_lon_os, ax_lon_os)
    y = draw_riga_prescr(y, "INTERMEDIO", sf_int_od, cil_int_od, ax_int_od, sf_int_os, cil_int_os, ax_int_os)
    y = draw_riga_prescr(y, "VICINO", sf_vic_od, cil_vic_od, ax_vic_od, sf_vic_os, cil_vic_os, ax_vic_os)

    y -= 5

    # Lenti consigliate
    c.setFont("Helvetica-Bold", 9)
    c.drawString(left, y, "Lenti consigliate:")
    y -= 12
    c.setFont("Helvetica", 9)

    tutte_lenti = [
        "Progressive",
        "Per vicino/intermedio",
        "Fotocromatiche",
        "Polarizzate",
        "Controllo miopia",
        "Trattamento antiriflesso",
    ]

    for voce in tutte_lenti:
        mark = "[x]" if voce in lenti_scelte else "[ ]"
        c.drawString(left + 5 * mm, y, f"{mark} {voce}")
        y -= 10

    if altri_trattamenti:
        c.drawString(left + 5 * mm, y, f"Altri trattamenti: {altri_trattamenti}")
        y -= 12

    # Note
    if note.strip():
        c.setFont("Helvetica-Bold", 9)
        c.drawString(left, y, "Note:")
        y -= 10
        c.setFont("Helvetica", 9)
        wrapper = textwrap.TextWrapper(width=70)
        for line in wrapper.wrap(note.strip()):
            if y < bottom + 40:
                c.showPage()
                c.setFont("Helvetica", 9)
                y = top
            c.drawString(left + 5 * mm, y, line)
            y -= 11

    # Firma
    if y < bottom + 50:
        c.showPage()
        c.setFont("Helvetica", 9)
        y = top

    c.line(right - 100, bottom + 30, right, bottom + 30)
    c.drawString(right - 95, bottom + 35, "Firma / Timbro")

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.getvalue()
def genera_referto_oculistico_a4_pdf(paziente, valutazione, with_header: bool) -> bytes:
    """
    Genera un referto oculistico/optometrico in formato A4.
    - with_header = True  → stampa anche l'intestazione dello studio
    - with_header = False → niente intestazione (usa carta intestata)
    Stampa solo i campi realmente compilati (non vuoti).
    """
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    left = 25 * mm
    right = width - 25 * mm
    top = height - 25 * mm
    bottom = 25 * mm

    y = top

    # Intestazione opzionale
    if with_header:
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(width / 2.0, y, "The Organism – Centro di Neuropsicologia e Sviluppo")
        y -= 14
        c.setFont("Helvetica", 9)
        c.drawCentredString(width / 2.0, y, "Via De Rosa, 46 – 84016 Pagani (SA)")
        y -= 18

    # Data referto = data valutazione
    data_iso = valutazione["Data_Valutazione"]
    data_it = _format_data_it_from_iso(data_iso) if data_iso else ""
    c.setFont("Helvetica", 10)
    if data_it:
        c.drawRightString(right, y, f"Data referto: {data_it}")
    y -= 20

    # Titolo
    c.setFont("Helvetica-Bold", 14)
    c.drawString(left, y, "Referto oculistico / optometrico")
    y -= 20

    # Dati paziente
    c.setFont("Helvetica", 11)
    nome_paz = f"{paziente['Cognome']} {paziente['Nome']}"
    c.drawString(left, y, f"Paziente: {nome_paz}")
    y -= 14

    # Data nascita + CF se presenti
    dn = paziente["Data_Nascita"]
    cf = (paziente["Codice_Fiscale"] or "").upper() if paziente["Codice_Fiscale"] else ""
    extra_parts = []
    if dn:
        try:
            dn_it = _format_data_it_from_iso(dn)
        except Exception:
            dn_it = dn
        extra_parts.append(f"Nato il: {dn_it}")
    if cf:
        extra_parts.append(f"CF: {cf}")
    if extra_parts:
        c.setFont("Helvetica", 10)
        c.drawString(left, y, " – ".join(extra_parts))
        y -= 14

    # Tipo visita e professionista
    tipo = valutazione["Tipo_Visita"] or ""
    prof = valutazione["Professionista"] or ""
    if tipo:
        c.drawString(left, y, f"Tipo visita: {tipo}")
        y -= 14
    if prof:
        c.drawString(left, y, f"Professionista: {prof}")
        y -= 18

    # Acuità visiva (stampata solo se è stato scritto qualcosa)
    ac_nat_od = valutazione["Acuita_Nat_OD"] or ""
    ac_nat_os = valutazione["Acuita_Nat_OS"] or ""
    ac_nat_oo = valutazione["Acuita_Nat_OO"] or ""
    ac_cor_od = valutazione["Acuita_Corr_OD"] or ""
    ac_cor_os = valutazione["Acuita_Corr_OS"] or ""
    ac_cor_oo = valutazione["Acuita_Corr_OO"] or ""

    if any([ac_nat_od, ac_nat_os, ac_nat_oo, ac_cor_od, ac_cor_os, ac_cor_oo]):
        c.setFont("Helvetica-Bold", 11)
        c.drawString(left, y, "Acuità visiva")
        y -= 14
        c.setFont("Helvetica", 10)

        if any([ac_nat_od, ac_nat_os, ac_nat_oo]):
            parts = []
            if ac_nat_od:
                parts.append(f"OD {ac_nat_od}")
            if ac_nat_os:
                parts.append(f"OS {ac_nat_os}")
            if ac_nat_oo:
                parts.append(f"OO {ac_nat_oo}")
            c.drawString(left + 10, y, "Naturale: " + " – ".join(parts))
            y -= 12

        if any([ac_cor_od, ac_cor_os, ac_cor_oo]):
            parts = []
            if ac_cor_od:
                parts.append(f"OD {ac_cor_od}")
            if ac_cor_os:
                parts.append(f"OS {ac_cor_os}")
            if ac_cor_oo:
                parts.append(f"OO {ac_cor_oo}")
            c.drawString(left + 10, y, "Corretta: " + " – ".join(parts))
            y -= 16

    # Blocco NOTE / refertazione
    note = valutazione["Note"] or ""
    if note.strip():
        c.setFont("Helvetica-Bold", 11)
        c.drawString(left, y, "Esame e refertazione")
        y -= 14
        c.setFont("Helvetica", 10)

        wrapper = textwrap.TextWrapper(width=90)
        for paragraph in note.split("\n"):
            paragraph = paragraph.strip()
            if not paragraph:
                y -= 6
                continue
            for line in wrapper.wrap(paragraph):
                if y < bottom + 50:
                    c.showPage()
                    y = top
                    if with_header:
                        c.setFont("Helvetica-Bold", 12)
                        c.drawCentredString(width / 2.0, y, "The Organism – Centro di Neuropsicologia e Sviluppo")
                        y -= 14
                        c.setFont("Helvetica", 9)
                        c.drawCentredString(width / 2.0, y, "Via De Rosa, 46 – 84016 Pagani (SA)")
                        y -= 18
                        c.setFont("Helvetica", 10)
                c.drawString(left, y, line)
                y -= 12

    # Spazio firma
    if y < bottom + 60:
        c.showPage()
        y = top

    c.setFont("Helvetica", 10)
    c.drawRightString(right, bottom + 40, "_____________________________")
    c.drawRightString(right, bottom + 26, "Firma / Timbro")

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.getvalue()


def ui_pazienti():
    st.header("Pazienti")

    conn = get_connection()
    cur = conn.cursor()

    # --- Tool CF separato (facoltativo) ---
    with st.expander("Tool di supporto per generare il Codice Fiscale"):
        st.write("Usalo come aiuto quando il paziente non ricorda il CF. Copia il risultato nel campo CF dell'anagrafica.")
        with st.form("cf_tool"):
            cogn_t = st.text_input("Cognome", key="cf_cognome")
            nome_t = st.text_input("Nome", key="cf_nome")
            data_t = st.text_input("Data di nascita (gg/mm/aaaa)", key="cf_data")
            sesso_t = st.selectbox("Sesso", ["", "M", "F", "Altro"], key="cf_sesso")
            comune_n_t = st.text_input("Comune di nascita (es. Pagani)", key="cf_comune")
            prov_n_t = st.text_input("Provincia di nascita (sigla, es. SA)", key="cf_prov")
            calcola = st.form_submit_button("Calcola CF")
            if calcola:
                cf_gen = genera_codice_fiscale(
                    cognome=cogn_t,
                    nome=nome_t,
                    data_nascita_str=data_t,
                    sesso=sesso_t,
                    comune_nascita=comune_n_t,
                    provincia_nascita=prov_n_t,
                )
                if cf_gen is None:
                    st.error(
                        "Impossibile generare il codice fiscale: controlla i dati e che il comune sia previsto nel file dei codici catastali."
                    )
                else:
                    st.success(f"Codice fiscale generato: **{cf_gen}**")
                    st.info("Copia questo codice nel campo 'Codice fiscale' del paziente.")

    st.markdown("---")
    st.subheader("Nuovo paziente")

    # --- Nuovo paziente ---
    with st.form("nuovo_paziente"):
        col1, col2 = st.columns(2)
        with col1:
            cognome = st.text_input("Cognome", "")
            data_nascita_str = st.text_input("Data di nascita (gg/mm/aaaa)", "")
        with col2:
            nome = st.text_input("Nome", "")
            sesso = st.selectbox("Sesso", ["", "M", "F", "Altro"])

        col3, col4, col5 = st.columns(3)
        with col3:
            indirizzo = st.text_input("Indirizzo (via, numero civico)", "")
        with col4:
            cap = st.text_input("CAP", "")
        with col5:
            provincia = st.text_input("Provincia (sigla, es. SA)", "")

        col6, col7 = st.columns(2)
        with col6:
            citta = st.text_input("Città / Comune di residenza", "")
        with col7:
            codice_fiscale = st.text_input("Codice fiscale", "").upper()

        col8, col9 = st.columns(2)
        with col8:
            telefono = st.text_input("Telefono", "")
        with col9:
            email = st.text_input("Email", "")

        salva = st.form_submit_button("Salva paziente")

    # --- Salvataggio nuovo paziente ---
    if salva:
        if not cognome or not nome:
            st.error("Cognome e Nome sono obbligatori.")
        else:
            # Gestione data di nascita (formato gg/mm/aaaa)
            data_iso = None
            if data_nascita_str.strip():
                try:
                    d = datetime.strptime(data_nascita_str.strip(), "%d/%m/%Y").date()
                    data_iso = d.isoformat()
                except ValueError:
                    st.error("Data di nascita non valida. Usa il formato gg/mm/aaaa (es. 19/01/1975).")
                    conn.close()
                    return

            # Codice fiscale (opzionale) con controllo
            cf_clean = (codice_fiscale or "").strip().upper()
            if cf_clean and not valida_codice_fiscale(cf_clean):
                st.warning(
                    "Il codice fiscale inserito non sembra valido rispetto all'algoritmo di controllo. "
                    "Puoi comunque salvarlo, ma verifica con attenzione."
                )

            cur.execute(
                """
                INSERT INTO Pazienti
                (Cognome, Nome, Data_Nascita, Sesso, Telefono, Email,
                 Indirizzo, CAP, Citta, Provincia, Codice_Fiscale, Stato_Paziente)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    cognome.strip(),
                    nome.strip(),
                    data_iso,
                    sesso,
                    telefono.strip(),
                    email.strip(),
                    indirizzo.strip(),
                    cap.strip(),
                    citta.strip(),
                    provincia.strip().upper(),
                    cf_clean or None,
                    "ATTIVO",
                ),
            )
            conn.commit()
            st.success("Paziente salvato correttamente.")

    st.markdown("---")
    st.subheader("Elenco pazienti")

    # Filtro ricerca
    filtro = st.text_input("Cerca per cognome/nome/codice fiscale", "")

    query = "SELECT * FROM Pazienti"
    params = []
    if filtro.strip():
        query += " WHERE Cognome LIKE ? OR Nome LIKE ? OR Codice_Fiscale LIKE ?"
        like = f"%{filtro.strip()}%"
        params = [like, like, like]
    query += " ORDER BY Cognome, Nome"

    cur.execute(query, params)
    rows = cur.fetchall()

    if not rows:
        st.info("Nessun paziente trovato.")
        conn.close()
        return

    # Etichette ricche: ID + Cognome Nome + data nascita + CF
    options = []
    for r in rows:
        nascita_it = ""
        if r["Data_Nascita"]:
            try:
                nascita_it = datetime.strptime(r["Data_Nascita"], "%Y-%m-%d").strftime("%d/%m/%Y")
            except Exception:
                nascita_it = r["Data_Nascita"]
        cf = (r["Codice_Fiscale"] or "").upper()
        label = f"{r['ID']} - {r['Cognome']} {r['Nome']}"
        extra = []
        if nascita_it:
            extra.append(f"nato il {nascita_it}")
        if cf:
            extra.append(f"CF: {cf}")
        if extra:
            label += " (" + " | ".join(extra) + ")"
        options.append(label)

    selected = st.selectbox("Seleziona un paziente per modificare / archiviare", options)
    sel_id = int(selected.split(" - ", 1)[0])
    rec = next(r for r in rows if r["ID"] == sel_id)

    st.write(f"Stato attuale: **{rec['Stato_Paziente']}**")

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        if st.button("Archivia paziente", key="archivia"):
            cur.execute("UPDATE Pazienti SET Stato_Paziente = 'ARCHIVIATO' WHERE ID = ?", (sel_id,))
            conn.commit()
            st.success("Paziente archiviato.")
            st.experimental_rerun() if hasattr(st, "experimental_rerun") else st.rerun()
    with col_b:
        if st.button("Riattiva paziente", key="riattiva"):
            cur.execute("UPDATE Pazienti SET Stato_Paziente = 'ATTIVO' WHERE ID = ?", (sel_id,))
            conn.commit()
            st.success("Paziente riattivato.")
            st.experimental_rerun() if hasattr(st, "experimental_rerun") else st.rerun()
    with col_c:
        if st.button("Elimina definitivamente", key="elimina"):
            cur.execute("DELETE FROM Anamnesi WHERE Paziente_ID = ?", (sel_id,))
            cur.execute("DELETE FROM Valutazioni_Visive WHERE Paziente_ID = ?", (sel_id,))
            cur.execute("DELETE FROM Sedute WHERE Paziente_ID = ?", (sel_id,))
            cur.execute("DELETE FROM Coupons WHERE Paziente_ID = ?", (sel_id,))
            cur.execute("DELETE FROM Pazienti WHERE ID = ?", (sel_id,))
            conn.commit()
            st.success("Paziente e dati associati eliminati.")
            conn.close()
            st.stop()

    st.markdown("### Modifica dati paziente")
    with st.form("modifica_paziente"):
        col1, col2 = st.columns(2)
        with col1:
            cognome_m = st.text_input("Cognome", rec["Cognome"] or "", key="m_cognome")
            data_nascita_m = st.text_input(
                "Data di nascita (gg/mm/aaaa)",
                datetime.strptime(rec["Data_Nascita"], "%Y-%m-%d").strftime("%d/%m/%Y")
                if rec["Data_Nascita"] else "",
                key="m_data_nascita",
            )
        with col2:
            nome_m = st.text_input("Nome", rec["Nome"] or "", key="m_nome")
            sesso_m = st.selectbox(
                "Sesso",
                ["", "M", "F", "Altro"],
                index=(["", "M", "F", "Altro"].index(rec["Sesso"]) if rec["Sesso"] in ["", "M", "F", "Altro"] else 0),
                key="m_sesso",
            )

        col3, col4, col5 = st.columns(3)
        with col3:
            indirizzo_m = st.text_input("Indirizzo", rec["Indirizzo"] or "", key="m_indirizzo")
        with col4:
            cap_m = st.text_input("CAP", rec["CAP"] or "", key="m_cap")
        with col5:
            provincia_m = st.text_input("Provincia", rec["Provincia"] or "", key="m_provincia")

        col6, col7 = st.columns(2)
        with col6:
            citta_m = st.text_input("Città", rec["Citta"] or "", key="m_citta")
        with col7:
            cf_m = st.text_input("Codice fiscale", (rec["Codice_Fiscale"] or "").upper(), key="m_cf")

        col8, col9 = st.columns(2)
        with col8:
            telefono_m = st.text_input("Telefono", rec["Telefono"] or "", key="m_tel")
        with col9:
            email_m = st.text_input("Email", rec["Email"] or "", key="m_email")

        stato_m = st.selectbox(
            "Stato paziente",
            ["ATTIVO", "ARCHIVIATO"],
            index=(0 if (rec["Stato_Paziente"] or "ATTIVO") == "ATTIVO" else 1),
            key="m_stato",
        )

        salva_mod = st.form_submit_button("Salva modifiche")

    if salva_mod:
        if not cognome_m or not nome_m:
            st.error("Cognome e Nome sono obbligatori.")
        else:
            data_iso_m = None
            if data_nascita_m.strip():
                try:
                    d = datetime.strptime(data_nascita_m.strip(), "%d/%m/%Y").date()
                    data_iso_m = d.isoformat()
                except ValueError:
                    st.error("Data di nascita non valida. Usa il formato gg/mm/aaaa.")
                    conn.close()
                    return

            cf_clean_m = (cf_m or "").strip().upper()
            if cf_clean_m and not valida_codice_fiscale(cf_clean_m):
                st.warning(
                    "Il codice fiscale inserito non sembra valido rispetto all'algoritmo di controllo. "
                    "Puoi comunque salvarlo, ma verifica con attenzione."
                )

            cur.execute(
                """
                UPDATE Pazienti
                SET Cognome = ?, Nome = ?, Data_Nascita = ?, Sesso = ?,
                    Telefono = ?, Email = ?, Indirizzo = ?, CAP = ?, Citta = ?, Provincia = ?,
                    Codice_Fiscale = ?, Stato_Paziente = ?
                WHERE ID = ?
                """,
                (
                    cognome_m.strip(),
                    nome_m.strip(),
                    data_iso_m,
                    sesso_m,
                    telefono_m.strip(),
                    email_m.strip(),
                    indirizzo_m.strip(),
                    cap_m.strip(),
                    citta_m.strip(),
                    provincia_m.strip().upper(),
                    cf_clean_m or None,
                    stato_m,
                    sel_id,
                ),
            )
            conn.commit()
            st.success("Dati paziente aggiornati.")

    conn.close()



# -----------------------------
# UI: Anamnesi
# -----------------------------

def ui_anamnesi():
    st.header("Anamnesi")

    conn = get_connection()
    cur = conn.cursor()

    # Seleziona paziente
    cur.execute("SELECT ID, Cognome, Nome FROM Pazienti ORDER BY Cognome, Nome")
    pazienti = cur.fetchall()
    if not pazienti:
        st.info("Nessun paziente registrato.")
        conn.close()
        return

    options = [f"{p['ID']} - {p['Cognome']} {p['Nome']}" for p in pazienti]
    sel = st.selectbox("Seleziona paziente", options)
    paz_id = int(sel.split(" - ", 1)[0])

    with st.form("nuova_anamnesi"):
        st.subheader("Nuova anamnesi")

        data_str = st.text_input("Data (gg/mm/aaaa)", datetime.today().strftime("%d/%m/%Y"))
        motivo = st.text_area("Motivo dell'invio / richiesta principale")

        st.markdown("**Area perinatale e sviluppo**")
        grav = st.text_area("Gravidanza e parto")
        svil = st.text_area("Sviluppo psicomotorio (tappe motorie, controllo del capo, seduto, gattonare, cammino)")
        linguaggio = st.text_area("Sviluppo del linguaggio (prime parole, frasi, eventuali difficoltà)")

        st.markdown("**Area scolastica / apprendimenti**")
        scuola = st.text_area("Scuola, rendimento, eventuali DSA / difficoltà specifiche")

        st.markdown("**Area emotivo-relazionale / comportamento**")
        relazioni = st.text_area("Relazioni con pari e adulti, comportamento, regolazione emotiva")
        sensoriale = st.text_area("Profilo sensoriale (udito, vista, tatto, gusto, olfatto, vestibolare, propriocezione)")

        st.markdown("**Stile di vita e salute**")
        sonno = st.text_area("Sonno (addormentamento, risvegli, qualità del sonno)")
        alimentazione = st.text_area("Alimentazione (selettività, appetito, ritmi)")
        familiarita = st.text_area("Familiarità per disturbi neurologici, psichiatrici, dell'apprendimento, visivi, uditivi…")
        patologie = st.text_area("Patologie pregresse / interventi / ricoveri")
        terapie = st.text_area("Terapie pregresse e in corso (logopedia, TNPEE, psicoterapia, optometria, ecc.)")
        farmaci = st.text_area("Farmaci in uso")
        allergie = st.text_area("Allergie")

        storia_libera = st.text_area("Storia libera / osservazioni genitori (narrazione aperta)")
        note = st.text_area("Note cliniche aggiuntive (per uso interno)")

        salva = st.form_submit_button("Salva anamnesi")

    if salva:
        data_iso = None
        if data_str.strip():
            try:
                d = datetime.strptime(data_str.strip(), "%d/%m/%Y").date()
                data_iso = d.isoformat()
            except ValueError:
                st.error("Data non valida. Usa il formato gg/mm/aaaa.")
                conn.close()
                return

        storia_completa = f"""
Gravidanza e parto:
{grav}

Sviluppo psicomotorio:
{svil}

Linguaggio:
{linguaggio}

Scuola / apprendimenti:
{scuola}

Area emotivo-relazionale / comportamento:
{relazioni}

Profilo sensoriale:
{sensoriale}

Sonno:
{sonno}

Alimentazione:
{alimentazione}

Familiarità:
{familiarita}

Patologie pregresse:
{patologie}

Terapie pregresse / in corso:
{terapie}

Farmaci:
{farmaci}

Allergie:
{allergie}

Storia libera (narrazione):
{storia_libera}
        """.strip()

        cur.execute(
            """
            INSERT INTO Anamnesi (Paziente_ID, Data_Anamnesi, Motivo, Storia, Note)
            VALUES (?,?,?,?,?)
            """,
            (paz_id, data_iso, motivo, storia_completa, note),
        )
        conn.commit()
        st.success("Anamnesi salvata.")

    st.markdown("---")
    st.subheader("Anamnesi esistenti")

    cur.execute(
        "SELECT * FROM Anamnesi WHERE Paziente_ID = ? ORDER BY Data_Anamnesi DESC, ID DESC",
        (paz_id,),
    )
    rows = cur.fetchall()
    if not rows:
        st.info("Nessuna anamnesi per questo paziente.")
        conn.close()
        return

    labels = [
        f"{r['ID']} - {r['Data_Anamnesi'] or ''} - { (r['Motivo'][:40] + '...') if r['Motivo'] and len(r['Motivo'])>40 else (r['Motivo'] or '') }"
        for r in rows
    ]
    sel_an = st.selectbox("Seleziona un'anamnesi da modificare/cancellare", labels)
    an_id = int(sel_an.split(" - ", 1)[0])
    rec = next(r for r in rows if r["ID"] == an_id)

    with st.form("modifica_anamnesi"):
        data_m = st.text_input(
            "Data (gg/mm/aaaa)",
            datetime.strptime(rec["Data_Anamnesi"], "%Y-%m-%d").strftime("%d/%m/%Y")
            if rec["Data_Anamnesi"] else "",
        )
        motivo_m = st.text_area("Motivo", rec["Motivo"] or "")
        storia_m = st.text_area("Storia (testo completo)", rec["Storia"] or "")
        note_m = st.text_area("Note", rec["Note"] or "")
        col1, col2 = st.columns(2)
        with col1:
            salva_m = st.form_submit_button("Salva modifiche")
        with col2:
            cancella = st.form_submit_button("Elimina anamnesi")

    if salva_m:
        data_iso_m = None
        if data_m.strip():
            try:
                d = datetime.strptime(data_m.strip(), "%d/%m/%Y").date()
                data_iso_m = d.isoformat()
            except ValueError:
                st.error("Data non valida.")
                conn.close()
                return
        cur.execute(
            """
            UPDATE Anamnesi
            SET Data_Anamnesi = ?, Motivo = ?, Storia = ?, Note = ?
            WHERE ID = ?
            """,
            (data_iso_m, motivo_m, storia_m, note_m, an_id),
        )
        conn.commit()
        st.success("Anamnesi aggiornata.")

    if cancella:
        cur.execute("DELETE FROM Anamnesi WHERE ID = ?", (an_id,))
        conn.commit()
        st.success("Anamnesi eliminata.")

    conn.close()

# -----------------------------
# UI: Valutazioni visive / oculistiche
# -----------------------------

def ui_valutazioni_visive():
    st.header("Valutazioni visive / oculistiche")

    conn = get_connection()
    cur = conn.cursor()

    # Seleziona paziente
    cur.execute("SELECT ID, Cognome, Nome FROM Pazienti ORDER BY Cognome, Nome")
    pazienti = cur.fetchall()
    if not pazienti:
        st.info("Nessun paziente registrato.")
        conn.close()
        return

    options = [f"{p['ID']} - {p['Cognome']} {p['Nome']}" for p in pazienti]
    sel = st.selectbox("Seleziona paziente", options)
    paz_id = int(sel.split(" - ", 1)[0])
    # Recupero anagrafica completa del paziente (serve per referti e prescrizioni)
    cur.execute("SELECT * FROM Pazienti WHERE ID = ?", (paz_id,))
    paziente = cur.fetchone()


    with st.form("nuova_val_visiva"):
        st.subheader("Nuova valutazione visiva / oculistica")
        data_str = st.text_input("Data (gg/mm/aaaa)", datetime.today().strftime("%d/%m/%Y"))
        tipo = st.text_input("Tipo visita (es. Valutazione optometrica, controllo, ecc.)")
        professionista = st.text_input("Professionista", "")

        st.markdown("### Acuità visiva")

        st.markdown("**Acuità naturale**")
        col1, col2, col3 = st.columns(3)
        with col1:
            ac_nat_od = av_select("OD (naturale)", "", key="ac_nat_od_new")
        with col2:
            ac_nat_os = av_select("OS (naturale)", "", key="ac_nat_os_new")
        with col3:
            ac_nat_oo = av_select("OO (naturale)", "", key="ac_nat_oo_new")

        st.markdown("**Acuità corretta**")
        col4, col5, col6 = st.columns(3)
        with col4:
            ac_cor_od = av_select("OD (corretta)", "", key="ac_cor_od_new")
        with col5:
            ac_cor_os = av_select("OS (corretta)", "", key="ac_cor_os_new")
        with col6:
            ac_cor_oo = av_select("OO (corretta)", "", key="ac_cor_oo_new")

        st.markdown("### Refrazione")

        st.markdown("**Refrazione oggettiva (SF / CIL / AX)**")
        col_od1, col_od2, col_od3 = st.columns(3)
        with col_od1:
            sf_ogg_od = st.number_input("OD SF oggettiva (D)", -30.0, 30.0, 0.0, 0.25, key="sf_ogg_od")
        with col_od2:
            cil_ogg_od = st.number_input("OD CIL oggettiva (D)", -10.0, 10.0, 0.0, 0.25, key="cil_ogg_od")
        with col_od3:
            ax_ogg_od = st.number_input("OD AX oggettiva (°)", 0, 180, 0, 1, key="ax_ogg_od")

        col_os1, col_os2, col_os3 = st.columns(3)
        with col_os1:
            sf_ogg_os = st.number_input("OS SF oggettiva (D)", -30.0, 30.0, 0.0, 0.25, key="sf_ogg_os")
        with col_os2:
            cil_ogg_os = st.number_input("OS CIL oggettiva (D)", -10.0, 10.0, 0.0, 0.25, key="cil_ogg_os")
        with col_os3:
            ax_ogg_os = st.number_input("OS AX oggettiva (°)", 0, 180, 0, 1, key="ax_ogg_os")

        st.markdown("**Refrazione soggettiva (SF / CIL / AX)**")
        col_od4, col_od5, col_od6 = st.columns(3)
        with col_od4:
            sf_sogg_od = st.number_input("OD SF soggettiva (D)", -30.0, 30.0, 0.0, 0.25, key="sf_sogg_od")
        with col_od5:
            cil_sogg_od = st.number_input("OD CIL soggettiva (D)", -10.0, 10.0, 0.0, 0.25, key="cil_sogg_od")
        with col_od6:
            ax_sogg_od = st.number_input("OD AX soggettiva (°)", 0, 180, 0, 1, key="ax_sogg_od")

        col_os4, col_os5, col_os6 = st.columns(3)
        with col_os4:
            sf_sogg_os = st.number_input("OS SF soggettiva (D)", -30.0, 30.0, 0.0, 0.25, key="sf_sogg_os")
        with col_os5:
            cil_sogg_os = st.number_input("OS CIL soggettiva (D)", -10.0, 10.0, 0.0, 0.25, key="cil_sogg_os")
        with col_os6:
            ax_sogg_os = st.number_input("OS AX soggettiva (°)", 0, 180, 0, 1, key="ax_sogg_os")

        st.markdown("### Cheratometria")
        col_kod1, col_kod2, col_kod3, col_kod4 = st.columns(4)
        with col_kod1:
            k1_od_mm = st.number_input("OD K1 (mm)", 6.0, 9.5, 7.80, 0.01, key="k1_od_mm")
        with col_kod2:
            k1_od_D = st.number_input("OD K1 (D)", 35.0, 50.0, 43.00, 0.25, key="k1_od_D")
        with col_kod3:
            k2_od_mm = st.number_input("OD K2 (mm)", 6.0, 9.5, 7.80, 0.01, key="k2_od_mm")
        with col_kod4:
            k2_od_D = st.number_input("OD K2 (D)", 35.0, 50.0, 43.00, 0.25, key="k2_od_D")

        col_kos1, col_kos2, col_kos3, col_kos4 = st.columns(4)
        with col_kos1:
            k1_os_mm = st.number_input("OS K1 (mm)", 6.0, 9.5, 7.80, 0.01, key="k1_os_mm")
        with col_kos2:
            k1_os_D = st.number_input("OS K1 (D)", 35.0, 50.0, 43.00, 0.25, key="k1_os_D")
        with col_kos3:
            k2_os_mm = st.number_input("OS K2 (mm)", 6.0, 9.5, 7.80, 0.01, key="k2_os_mm")
        with col_kos4:
            k2_os_D = st.number_input("OS K2 (D)", 35.0, 50.0, 43.00, 0.25, key="k2_os_D")

        st.markdown("### Tonometria / Pressione oculare")
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            tono_od = st.number_input("Tonometria OD (mmHg)", 0.0, 60.0, 15.0, 0.5, key="tono_od")
        with col_t2:
            tono_os = st.number_input("Tonometria OS (mmHg)", 0.0, 60.0, 15.0, 0.5, key="tono_os")

        st.markdown("### Motilità, cover test, stereopsi, PPC")
        motilita = st.text_input("Motilità oculare", "")
        cover_test = st.text_input("Cover test (lontano/vicino, OD/OS)", "")
        stereopsi = st.text_input("Stereopsi (secondi d'arco / test)", "")
        ppc_cm = st.number_input("PPC (punto prossimo di convergenza, cm)", 0.0, 50.0, 10.0, 0.5, key="ppc_cm")

        st.markdown("### Colori, pachimetria, esami di struttura/funzione")
        ishihara = st.text_input("Tavole di Ishihara (esito)", "")
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            pachim_od = st.number_input("Pachimetria OD (µm)", 400.0, 700.0, 540.0, 1.0, key="pachim_od")
        with col_p2:
            pachim_os = st.number_input("Pachimetria OS (µm)", 400.0, 700.0, 540.0, 1.0, key="pachim_os")

        fondo = st.text_area("Fondo oculare (descrizione)", "")
        campo_visivo = st.text_area("Campo visivo (descrizione / esito)", "")
        oct = st.text_area("OCT (descrizione)", "")
        topo = st.text_area("Topografia corneale (descrizione)", "")

        col7, col8 = st.columns(2)
        with col7:
            costo = st.number_input("Costo visita", min_value=0.0, step=5.0, value=0.0)
        with col8:
            pagato = st.checkbox("Pagato", value=False)

        note_libere = st.text_area("Note cliniche libere (aggiuntive)")

        salva = st.form_submit_button("Salva valutazione visiva")

    if salva:
        data_iso = None
        if data_str.strip():
            try:
                d = datetime.strptime(data_str.strip(), "%d/%m/%Y").date()
                data_iso = d.isoformat()
            except ValueError:
                st.error("Data non valida. Usa il formato gg/mm/aaaa.")
                conn.close()
                return

        # Prepariamo un blocco strutturato con tutti i dati oculistici
        dettaglio = f"""
ACUITÀ VISIVA
- NAT: OD {ac_nat_od} | OS {ac_nat_os} | OO {ac_nat_oo}
- CORR: OD {ac_cor_od} | OS {ac_cor_os} | OO {ac_cor_oo}

REFRAZIONE OGGETTIVA (SF / CIL x AX)
- OD: {sf_ogg_od:+.2f} ({cil_ogg_od:+.2f} x {ax_ogg_od}°)
- OS: {sf_ogg_os:+.2f} ({cil_ogg_os:+.2f} x {ax_ogg_os}°)

REFRAZIONE SOGGETTIVA (SF / CIL x AX)
- OD: {sf_sogg_od:+.2f} ({cil_sogg_od:+.2f} x {ax_sogg_od}°)
- OS: {sf_sogg_os:+.2f} ({cil_sogg_os:+.2f} x {ax_sogg_os}°)

CHERATOMETRIA
- OD: K1 {k1_od_mm:.2f} mm / {k1_od_D:.2f} D; K2 {k2_od_mm:.2f} mm / {k2_od_D:.2f} D
- OS: K1 {k1_os_mm:.2f} mm / {k1_os_D:.2f} D; K2 {k2_os_mm:.2f} mm / {k2_os_D:.2f} D

TONOMETRIA
- OD: {tono_od:.1f} mmHg
- OS: {tono_os:.1f} mmHg

MOTILITÀ / ALLINEAMENTO
- Motilità oculare: {motilita}
- Cover test: {cover_test}
- Stereopsi: {stereopsi}
- PPC: {ppc_cm:.1f} cm

COLORI / PACHIMETRIA
- Ishihara: {ishihara}
- Pachimetria OD: {pachim_od:.0f} µm
- Pachimetria OS: {pachim_os:.0f} µm

ESAMI STRUTTURALI / FUNZIONALI
- Fondo oculare: {fondo}
- Campo visivo: {campo_visivo}
- OCT: {oct}
- Topografia corneale: {topo}
        """.strip()

        note_finali = dettaglio + "\n\nNOTE LIBERE:\n" + (note_libere or "")

        cur.execute(
            """
            INSERT INTO Valutazioni_Visive
            (Paziente_ID, Data_Valutazione, Tipo_Visita, Professionista,
             Acuita_Nat_OD, Acuita_Nat_OS, Acuita_Nat_OO,
             Acuita_Corr_OD, Acuita_Corr_OS, Acuita_Corr_OO,
             Costo, Pagato, Note)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                paz_id,
                data_iso,
                tipo,
                professionista,
                ac_nat_od,
                ac_nat_os,
                ac_nat_oo,
                ac_cor_od,
                ac_cor_os,
                ac_cor_oo,
                float(costo),
                1 if pagato else 0,
                note_finali,
            ),
        )
        conn.commit()
        st.success("Valutazione visiva salvata.")

    # -------- Strumenti optometrici/oculistici stand-alone --------
    st.markdown("---")
    st.subheader("Strumenti di supporto optometrici / oculistici")

    # Cheratometria
    with st.expander("Cheratometria rapida (mm ⇄ diottrie)"):
        modo = st.radio("Tipo di conversione", ["mm → diottrie", "diottrie → mm"], key="cherato_modo")
        if modo == "mm → diottrie":
            raggio = st.number_input("Raggio corneale (mm)", min_value=6.0, max_value=9.5, value=7.80, step=0.01, key="cherato_r_mm")
            if st.button("Calcola potere (D)", key="btn_cherato_mmD"):
                D = cherato_mm_to_D(raggio)
                st.success(f"Potere corneale ≈ {D:.2f} D")
        else:
            D_val = st.number_input("Potere corneale (D)", min_value=35.0, max_value=50.0, value=43.00, step=0.25, key="cherato_D")
            if st.button("Calcola raggio (mm)", key="btn_cherato_Dmm"):
                r = cherato_D_to_mm(D_val)
                st.success(f"Raggio corneale ≈ {r:.2f} mm")

    # Conversione occhiali → CL
    with st.expander("Conversione occhiali → lenti a contatto (sfera + cilindro)"):
        st.write("Conversione approssimata, da verificare sempre con la prova in studio.")
        vertex = st.number_input("Distanza vertebrale occhiali (mm)", min_value=8.0, max_value=16.0, value=12.0, step=0.5, key="cl_vertex")

        st.markdown("**Occhio destro (OD)**")
        col_od1, col_od2, col_od3 = st.columns(3)
        with col_od1:
            sph_od = st.number_input("Sfera occhiali OD (D)", min_value=-30.0, max_value=30.0, value=0.0, step=0.25, key="sph_od")
        with col_od2:
            cyl_od = st.number_input("Cilindro occhiali OD (D)", min_value=-10.0, max_value=10.0, value=0.0, step=0.25, key="cyl_od")
        with col_od3:
            ax_od = st.number_input("Asse occhiali OD (°)", min_value=0, max_value=180, value=0, step=1, key="ax_od")

        st.markdown("**Occhio sinistro (OS)**")
        col_os1, col_os2, col_os3 = st.columns(3)
        with col_os1:
            sph_os = st.number_input("Sfera occhiali OS (D)", min_value=-30.0, max_value=30.0, value=0.0, step=0.25, key="sph_os")
        with col_os2:
            cyl_os = st.number_input("Cilindro occhiali OS (D)", min_value=-10.0, max_value=10.0, value=0.0, step=0.25, key="cyl_os")
        with col_os3:
            ax_os = st.number_input("Asse occhiali OS (°)", min_value=0, max_value=180, value=0, step=1, key="ax_os")

        if st.button("Calcola lenti a contatto", key="btn_cl_conv"):
            sph_cl_od, cyl_cl_od, ax_cl_od = convert_occhiali_to_cl(sph_od, cyl_od, ax_od, vertex_mm=vertex)
            sph_cl_os, cyl_cl_os, ax_cl_os = convert_occhiali_to_cl(sph_os, cyl_os, ax_os, vertex_mm=vertex)

            st.success(
                f"**OD (CL):** {sph_cl_od:+.2f} D  {cyl_cl_od:+.2f} D x {ax_cl_od:.0f}°"
            )
            st.success(
                f"**OS (CL):** {sph_cl_os:+.2f} D  {cyl_cl_os:+.2f} D x {ax_cl_os:.0f}°"
            )
            st.info("Puoi arrotondare ulteriormente secondo le disponibilità reali delle lenti a contatto.")

    # -------- Valutazioni esistenti --------
    st.markdown("---")
    st.subheader("Valutazioni esistenti")

    cur.execute(
        "SELECT * FROM Valutazioni_Visive WHERE Paziente_ID = ? ORDER BY Data_Valutazione DESC, ID DESC",
        (paz_id,),
    )
    rows = cur.fetchall()
    if not rows:
        st.info("Nessuna valutazione per questo paziente.")
        conn.close()
        return

    labels = [
        f"{r['ID']} - {r['Data_Valutazione'] or ''} - { (r['Tipo_Visita'][:40] + '...') if r['Tipo_Visita'] and len(r['Tipo_Visita'])>40 else (r['Tipo_Visita'] or '') }"
        for r in rows
    ]
    sel_v = st.selectbox("Seleziona una valutazione da modificare/cancellare", labels)
    val_id = int(sel_v.split(" - ", 1)[0])
    rec = next(r for r in rows if r["ID"] == val_id)
    st.markdown("#### Referto oculistico in PDF (A4)")

    if not REPORTLAB_AVAILABLE:
        st.info("Per generare il referto in PDF installa il pacchetto 'reportlab' (es. `pip install reportlab`).")
    else:
        pdf_bytes_int = genera_referto_oculistico_pdf(paziente, rec, include_header=True)
        pdf_bytes_no = genera_referto_oculistico_pdf(paziente, rec, include_header=False)
        base_name = f"{paziente['Cognome']}_{paziente['Nome']}_{val_id}"

        colr1, colr2 = st.columns(2)
        with colr1:
            st.download_button(
                "Scarica referto A4 (con intestazione)",
                data=pdf_bytes_int,
                file_name=f"referto_{base_name}_intestazione.pdf",
                mime="application/pdf",
                key=f"dl_ref_int_{val_id}",
            )
        with colr2:
            st.download_button(
                "Scarica referto A4 (senza intestazione)",
                data=pdf_bytes_no,
                file_name=f"referto_{base_name}_senza_intestazione.pdf",
                mime="application/pdf",
                key=f"dl_ref_no_{val_id}",
            )

    with st.form("modifica_val_visiva"):
        data_m = st.text_input(
            "Data (gg/mm/aaaa)",
            datetime.strptime(rec["Data_Valutazione"], "%Y-%m-%d").strftime("%d/%m/%Y")
            if rec["Data_Valutazione"] else "",
        )
        tipo_m = st.text_input("Tipo visita", rec["Tipo_Visita"] or "")
        professionista_m = st.text_input("Professionista", rec["Professionista"] or "")

        st.markdown("**Acuità naturale**")
        col1, col2, col3 = st.columns(3)
        with col1:
            ac_nat_od_m = av_select("OD (naturale)", rec["Acuita_Nat_OD"], key="ac_nat_od_m")
        with col2:
            ac_nat_os_m = av_select("OS (naturale)", rec["Acuita_Nat_OS"], key="ac_nat_os_m")
        with col3:
            ac_nat_oo_m = av_select("OO (naturale)", rec["Acuita_Nat_OO"], key="ac_nat_oo_m")

        st.markdown("**Acuità corretta**")
        col4, col5, col6 = st.columns(3)
        with col4:
            ac_cor_od_m = av_select("OD (corretta)", rec["Acuita_Corr_OD"], key="ac_cor_od_m")
        with col5:
            ac_cor_os_m = av_select("OS (corretta)", rec["Acuita_Corr_OS"], key="ac_cor_os_m")
        with col6:
            ac_cor_oo_m = av_select("OO (corretta)", rec["Acuita_Corr_OO"], key="ac_cor_oo_m")

        costo_m = st.number_input(
            "Costo visita",
            min_value=0.0,
            step=5.0,
            value=float(rec["Costo"] or 0.0),
            key="costo_m",
        )
        pagato_m = st.checkbox("Pagato", value=bool(rec["Pagato"]), key="pagato_m")

        note_m = st.text_area("Note (blocco completo, inclusi dati oculistici strutturati)", rec["Note"] or "")

        col9, col10 = st.columns(2)
        with col9:
            salva_m = st.form_submit_button("Salva modifiche")
        with col10:
            cancella = st.form_submit_button("Elimina valutazione")

    if salva_m:
        data_iso_m = None
        if data_m.strip():
            try:
                d = datetime.strptime(data_m.strip(), "%d/%m/%Y").date()
                data_iso_m = d.isoformat()
            except ValueError:
                st.error("Data non valida.")
                conn.close()
                return
        cur.execute(
            """
            UPDATE Valutazioni_Visive
            SET Data_Valutazione = ?, Tipo_Visita = ?, Professionista = ?,
                Acuita_Nat_OD = ?, Acuita_Nat_OS = ?, Acuita_Nat_OO = ?,
                Acuita_Corr_OD = ?, Acuita_Corr_OS = ?, Acuita_Corr_OO = ?,
                Costo = ?, Pagato = ?, Note = ?
            WHERE ID = ?
            """,
            (
                data_iso_m,
                tipo_m,
                professionista_m,
                ac_nat_od_m,
                ac_nat_os_m,
                ac_nat_oo_m,
                ac_cor_od_m,
                ac_cor_os_m,
                ac_cor_oo_m,
                float(costo_m),
                1 if pagato_m else 0,
                note_m,
                val_id,
            ),
        )
        conn.commit()
        st.success("Valutazione aggiornata.")

    if cancella:
        cur.execute("DELETE FROM Valutazioni_Visive WHERE ID = ?", (val_id,))
        conn.commit()
        st.success("Valutazione eliminata.")
    st.markdown("---")
    st.subheader("Prescrizione occhiali (formato A5)")

    if not REPORTLAB_AVAILABLE:
        st.info("Per generare la prescrizione in PDF installa il pacchetto 'reportlab' (es. `pip install reportlab`).")
    else:
        st.write("Compila la prescrizione finale e scarica un PDF A5 pronto per la stampa.")

        with st.form("prescrizione_a5_form"):
            data_prescr_str = st.text_input(
                "Data prescrizione (gg/mm/aaaa)",
                datetime.today().strftime("%d/%m/%Y"),
                key="data_prescr_a5",
            )

            st.markdown("**LONTANO**")
            colL1, colL2 = st.columns(2)
            with colL1:
                sf_lon_od = st.number_input("OD SF lontano (D)", -30.0, 30.0, 0.0, 0.25, key="sf_lon_od_a5")
                cil_lon_od = st.number_input("OD CIL lontano (D)", -10.0, 10.0, 0.0, 0.25, key="cil_lon_od_a5")
                ax_lon_od = st.number_input("OD AX lontano (°)", 0, 180, 0, 1, key="ax_lon_od_a5")
            with colL2:
                sf_lon_os = st.number_input("OS SF lontano (D)", -30.0, 30.0, 0.0, 0.25, key="sf_lon_os_a5")
                cil_lon_os = st.number_input("OS CIL lontano (D)", -10.0, 10.0, 0.0, 0.25, key="cil_lon_os_a5")
                ax_lon_os = st.number_input("OS AX lontano (°)", 0, 180, 0, 1, key="ax_lon_os_a5")

            st.markdown("**INTERMEDIO**")
            colI1, colI2 = st.columns(2)
            with colI1:
                sf_int_od = st.number_input("OD SF intermedio (D)", -30.0, 30.0, 0.0, 0.25, key="sf_int_od_a5")
                cil_int_od = st.number_input("OD CIL intermedio (D)", -10.0, 10.0, 0.0, 0.25, key="cil_int_od_a5")
                ax_int_od = st.number_input("OD AX intermedio (°)", 0, 180, 0, 1, key="ax_int_od_a5")
            with colI2:
                sf_int_os = st.number_input("OS SF intermedio (D)", -30.0, 30.0, 0.0, 0.25, key="sf_int_os_a5")
                cil_int_os = st.number_input("OS CIL intermedio (D)", -10.0, 10.0, 0.0, 0.25, key="cil_int_os_a5")
                ax_int_os = st.number_input("OS AX intermedio (°)", 0, 180, 0, 1, key="ax_int_os_a5")

            st.markdown("**VICINO**")
            colV1, colV2 = st.columns(2)
            with colV1:
                sf_vic_od = st.number_input("OD SF vicino (D)", -30.0, 30.0, 0.0, 0.25, key="sf_vic_od_a5")
                cil_vic_od = st.number_input("OD CIL vicino (D)", -10.0, 10.0, 0.0, 0.25, key="cil_vic_od_a5")
                ax_vic_od = st.number_input("OD AX vicino (°)", 0, 180, 0, 1, key="ax_vic_od_a5")
            with colV2:
                sf_vic_os = st.number_input("OS SF vicino (D)", -30.0, 30.0, 0.0, 0.25, key="sf_vic_os_a5")
                cil_vic_os = st.number_input("OS CIL vicino (D)", -10.0, 10.0, 0.0, 0.25, key="cil_vic_os_a5")
                ax_vic_os = st.number_input("OS AX vicino (°)", 0, 180, 0, 1, key="ax_vic_os_a5")

            lenti_possibili = [
                "Progressive",
                "Per vicino/intermedio",
                "Fotocromatiche",
                "Polarizzate",
                "Controllo miopia",
                "Trattamento antiriflesso",
            ]
            lenti_scelte = st.multiselect(
                "Lenti consigliate",
                options=lenti_possibili,
                key="lenti_scelte_a5",
            )

            altri_trattamenti = st.text_input(
                "Altri trattamenti (facoltativo)",
                key="altro_tratt_a5",
            )

            note_prescrizione = st.text_area(
                "Note aggiuntive per la prescrizione",
                key="note_prescr_a5",
            )

            genera_pdf = st.form_submit_button("Genera PDF A5")

        if genera_pdf:
            data_iso_prescr = None
            if data_prescr_str.strip():
                try:
                    d = datetime.strptime(data_prescr_str.strip(), "%d/%m/%Y").date()
                    data_iso_prescr = d.isoformat()
                except ValueError:
                    st.error("Data prescrizione non valida. Usa il formato gg/mm/aaaa.")
                    data_iso_prescr = None

            pdf_bytes = genera_prescrizione_occhiali_a5_pdf(
                paziente=paziente,
                data_prescrizione_iso=data_iso_prescr,
                sf_lon_od=sf_lon_od, cil_lon_od=cil_lon_od, ax_lon_od=ax_lon_od,
                sf_lon_os=sf_lon_os, cil_lon_os=cil_lon_os, ax_lon_os=ax_lon_os,
                sf_int_od=sf_int_od, cil_int_od=cil_int_od, ax_int_od=ax_int_od,
                sf_int_os=sf_int_os, cil_int_os=cil_int_os, ax_int_os=ax_int_os,
                sf_vic_od=sf_vic_od, cil_vic_od=cil_vic_od, ax_vic_od=ax_vic_od,
                sf_vic_os=sf_vic_os, cil_vic_os=cil_vic_os, ax_vic_os=ax_vic_os,
                lenti_scelte=lenti_scelte,
                altri_trattamenti=altri_trattamenti,
                note=note_prescrizione,
            )

            filename = f"prescrizione_occhiali_{paziente['Cognome']}_{paziente['Nome']}.pdf"
            st.download_button(
                "Scarica prescrizione occhiali (A5)",
                data=pdf_bytes,
                file_name=filename,
                mime="application/pdf",
                key="dl_prescr_a5",
            )
    st.markdown("---")
    st.subheader("Referto oculistico / optometrico (PDF A4)")

    if not REPORTLAB_AVAILABLE:
        st.info(
            "Per generare il referto in PDF è necessario avere installato il pacchetto "
            "`reportlab`.\n"
            "Da terminale: `pip install reportlab`."
        )
    else:
        col_r1, col_r2 = st.columns([2, 1])
        with col_r1:
            with_header = st.checkbox(
                "Stampa con intestazione dello studio (usa carta bianca)",
                value=False,
                key=f"hdr_referto_{val_id}",
            )

        if st.button("Genera referto A4 per questa valutazione", key=f"btn_referto_{val_id}"):
            # Ricarico i dati aggiornati dal DB
            cur.execute("SELECT * FROM Pazienti WHERE ID = ?", (paz_id,))
            paziente = cur.fetchone()
            cur.execute("SELECT * FROM Valutazioni_Visive WHERE ID = ?", (val_id,))
            valutazione = cur.fetchone()

            if not paziente or not valutazione:
                st.error("Errore nel recupero dei dati dal database.")
            else:
                pdf_bytes = genera_referto_oculistico_a4_pdf(
                    paziente=paziente,
                    valutazione=valutazione,
                    with_header=with_header,
                )
                st.download_button(
                    "Scarica referto A4 (PDF)",
                    data=pdf_bytes,
                    file_name=f"referto_visivo_{paziente['Cognome']}_{paziente['Nome']}.pdf",
                    mime="application/pdf",
                    key=f"download_referto_{val_id}",
                )

    conn.close()

# -----------------------------
# UI: Sedute / Terapie
# -----------------------------

def ui_sedute():
    st.header("Sedute / Terapie")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT ID, Cognome, Nome FROM Pazienti ORDER BY Cognome, Nome")
    pazienti = cur.fetchall()
    if not pazienti:
        st.info("Nessun paziente registrato.")
        conn.close()
        return

    options = [f"{p['ID']} - {p['Cognome']} {p['Nome']}" for p in pazienti]
    sel = st.selectbox("Seleziona paziente", options)
    paz_id = int(sel.split(" - ", 1)[0])

    with st.form("nuova_seduta"):
        st.subheader("Nuova seduta")
        data_str = st.text_input("Data (gg/mm/aaaa)", datetime.today().strftime("%d/%m/%Y"))
        terapia = st.text_input("Tipo di terapia (es. logopedia, neuropsicomotricità, optometria...)", "")
        professionista = st.text_input("Professionista", "")
        col1, col2 = st.columns(2)
        with col1:
            costo = st.number_input("Costo seduta", min_value=0.0, step=5.0, value=0.0)
        with col2:
            pagato = st.checkbox("Pagato", value=False)
        note = st.text_area("Note")
        salva = st.form_submit_button("Salva seduta")

    if salva:
        data_iso = None
        if data_str.strip():
            try:
                d = datetime.strptime(data_str.strip(), "%d/%m/%Y").date()
                data_iso = d.isoformat()
            except ValueError:
                st.error("Data non valida. Usa il formato gg/mm/aaaa.")
                conn.close()
                return
        cur.execute(
            """
            INSERT INTO Sedute
            (Paziente_ID, Data_Seduta, Terapia, Professionista, Costo, Pagato, Note)
            VALUES (?,?,?,?,?,?,?)
            """,
            (
                paz_id,
                data_iso,
                terapia,
                professionista,
                float(costo),
                1 if pagato else 0,
                note,
            ),
        )
        conn.commit()
        st.success("Seduta salvata.")

    st.markdown("---")
    st.subheader("Sedute esistenti")

    cur.execute(
        "SELECT * FROM Sedute WHERE Paziente_ID = ? ORDER BY Data_Seduta DESC, ID DESC",
        (paz_id,),
    )
    rows = cur.fetchall()
    if not rows:
        st.info("Nessuna seduta per questo paziente.")
        conn.close()
        return

    labels = [
        f"{r['ID']} - {r['Data_Seduta'] or ''} - { (r['Terapia'][:40] + '...') if r['Terapia'] and len(r['Terapia'])>40 else (r['Terapia'] or '') }"
        for r in rows
    ]
    sel_s = st.selectbox("Seleziona una seduta da modificare/cancellare", labels)
    sed_id = int(sel_s.split(" - ", 1)[0])
    rec = next(r for r in rows if r["ID"] == sed_id)

    with st.form("modifica_seduta"):
        data_m = st.text_input(
            "Data (gg/mm/aaaa)",
            datetime.strptime(rec["Data_Seduta"], "%Y-%m-%d").strftime("%d/%m/%Y")
            if rec["Data_Seduta"] else "",
        )
        terapia_m = st.text_input("Terapia", rec["Terapia"] or "")
        professionista_m = st.text_input("Professionista", rec["Professionista"] or "")
        col1, col2 = st.columns(2)
        with col1:
            costo_m = st.number_input(
                "Costo seduta",
                min_value=0.0,
                step=5.0,
                value=float(rec["Costo"] or 0.0),
                key="costo_sed_m",
            )
        with col2:
            pagato_m = st.checkbox("Pagato", value=bool(rec["Pagato"]), key="pagato_sed_m")
        note_m = st.text_area("Note", rec["Note"] or "")

        col3, col4 = st.columns(2)
        with col3:
            salva_m = st.form_submit_button("Salva modifiche")
        with col4:
            cancella = st.form_submit_button("Elimina seduta")

    if salva_m:
        data_iso_m = None
        if data_m.strip():
            try:
                d = datetime.strptime(data_m.strip(), "%d/%m/%Y").date()
                data_iso_m = d.isoformat()
            except ValueError:
                st.error("Data non valida.")
                conn.close()
                return
        cur.execute(
            """
            UPDATE Sedute
            SET Data_Seduta = ?, Terapia = ?, Professionista = ?, Costo = ?, Pagato = ?, Note = ?
            WHERE ID = ?
            """,
            (
                data_iso_m,
                terapia_m,
                professionista_m,
                float(costo_m),
                1 if pagato_m else 0,
                note_m,
                sed_id,
            ),
        )
        conn.commit()
        st.success("Seduta aggiornata.")

    if cancella:
        cur.execute("DELETE FROM Sedute WHERE ID = ?", (sed_id,))
        conn.commit()
        st.success("Seduta eliminata.")

    conn.close()
def ui_coupons():
    st.header("Gestione coupon OF / SDS")

    conn = get_connection()
    cur = conn.cursor()

    # Elenco pazienti
    cur.execute("SELECT ID, Cognome, Nome FROM Pazienti ORDER BY Cognome, Nome")
    pazienti = cur.fetchall()
    if not pazienti:
        st.info("Nessun paziente registrato.")
        conn.close()
        return

    opt_paz = [f"{p['ID']} - {p['Cognome']} {p['Nome']}" for p in pazienti]
    sel = st.selectbox("Seleziona paziente", opt_paz)
    paz_id = int(sel.split(" - ", 1)[0])

    st.markdown("### Aggiungi nuovo coupon")

    with st.form("form_nuovo_coupon"):
        col1, col2 = st.columns(2)
        with col1:
            tipo_coupon = st.selectbox("Tipo coupon", ["OF", "SDS"], key="tipo_coupon_new")
        with col2:
            codice_coupon = st.text_input("Codice / numero coupon", key="codice_coupon_new")

        col3, col4 = st.columns(2)
        with col3:
            data_c_str = st.text_input(
                "Data assegnazione (gg/mm/aaaa)",
                datetime.today().strftime("%d/%m/%Y"),
                key="data_coupon_new",
            )
        with col4:
            usato_flag = st.checkbox("Già utilizzato", value=False, key="usato_coupon_new")

        note_coupon = st.text_input("Note coupon (facoltative)", key="note_coupon_new")

        salva_c = st.form_submit_button("Aggiungi coupon")

    if salva_c:
        data_c_iso = None
        if data_c_str.strip():
            try:
                d = datetime.strptime(data_c_str.strip(), "%d/%m/%Y").date()
                data_c_iso = d.isoformat()
            except ValueError:
                st.error("Data coupon non valida. Usa il formato gg/mm/aaaa.")
                conn.close()
                return

        cur.execute(
            """
            INSERT INTO Coupons
            (Paziente_ID, Tipo_Coupon, Codice_Coupon, Data_Assegnazione, Note, Utilizzato)
            VALUES (?,?,?,?,?,?)
            """,
            (
                paz_id,
                tipo_coupon,
                codice_coupon.strip() or None,
                data_c_iso,
                note_coupon.strip() or None,
                1 if usato_flag else 0,
            ),
        )
        conn.commit()
        st.success("Coupon aggiunto correttamente.")
        st.rerun()

    st.markdown("---")
    st.subheader("Coupon del paziente selezionato")

    cur.execute(
        "SELECT * FROM Coupons WHERE Paziente_ID = ? ORDER BY Data_Assegnazione DESC, ID DESC",
        (paz_id,),
    )
    coupons = cur.fetchall()

    if not coupons:
        st.info("Nessun coupon per questo paziente.")
        conn.close()
        return

    for c in coupons:
        data_it = ""
        if c["Data_Assegnazione"]:
            try:
                data_it = datetime.strptime(c["Data_Assegnazione"], "%Y-%m-%d").strftime("%d/%m/%Y")
            except Exception:
                data_it = c["Data_Assegnazione"]

        stato = "USATO" if c["Utilizzato"] else "NON USATO"

        col1, col2, col3, col4 = st.columns([4, 2, 2, 2])
        with col1:
            st.write(
                f"**ID {c['ID']}** – {c['Tipo_Coupon']} – "
                f"{c['Codice_Coupon'] or '-'} – {data_it or 'data n/d'}"
            )
            if c["Note"]:
                st.caption(f"Note: {c['Note']}")
        with col2:
            st.write(f"Stato: **{stato}**")
        with col3:
            if c["Utilizzato"]:
                if st.button("Segna NON usato", key=f"c_notused_{c['ID']}"):
                    cur.execute(
                        "UPDATE Coupons SET Utilizzato = 0 WHERE ID = ?",
                        (c["ID"],),
                    )
                    conn.commit()
                    st.rerun()
            else:
                if st.button("Segna USATO", key=f"c_used_{c['ID']}"):
                    cur.execute(
                        "UPDATE Coupons SET Utilizzato = 1 WHERE ID = ?",
                        (c["ID"],),
                    )
                    conn.commit()
                    st.rerun()
        with col4:
            if st.button("Elimina", key=f"c_del_{c['ID']}"):
                cur.execute("DELETE FROM Coupons WHERE ID = ?", (c["ID"],))
                conn.commit()
                st.rerun()

    conn.close()


   
# -----------------------------
# UI: Dashboard incassi
# -----------------------------

def ui_dashboard():
    st.header("Dashboard incassi")

    conn = get_connection()
    cur = conn.cursor()

    st.subheader("Filtri")

    oggi = date.today()
    col1, col2, col3 = st.columns(3)
    with col1:
        data_da_str = st.text_input("Dal (gg/mm/aaaa)", oggi.strftime("%d/%m/%Y"))
    with col2:
        data_a_str = st.text_input("Al (gg/mm/aaaa)", oggi.strftime("%d/%m/%Y"))
    with col3:
        professionista_f = st.text_input("Filtra per professionista (facoltativo)", "")

    try:
        data_da = datetime.strptime(data_da_str.strip(), "%d/%m/%Y").date()
        data_a = datetime.strptime(data_a_str.strip(), "%d/%m/%Y").date()
    except ValueError:
        st.error("Formato data non valido. Usa gg/mm/aaaa.")
        conn.close()
        return

    if data_a < data_da:
        st.error("La data finale non può essere precedente a quella iniziale.")
        conn.close()
        return

    data_da_iso = data_da.isoformat()
    data_a_iso = data_a.isoformat()

    # --- Incassi da Valutazioni Visive ---
    st.markdown("### Incassi da valutazioni visive / oculistiche")

    query_v = """
        SELECT Data_Valutazione AS Data, Professionista, Costo, Pagato
        FROM Valutazioni_Visive
        WHERE Data_Valutazione BETWEEN ? AND ?
    """
    params_v = [data_da_iso, data_a_iso]
    if professionista_f.strip():
        query_v += " AND Professionista LIKE ?"
        params_v.append(f"%{professionista_f.strip()}%")

    cur.execute(query_v, params_v)
    vis = cur.fetchall()

    incasso_vis = sum((r["Costo"] or 0.0) for r in vis if r["Pagato"])
    st.write(f"**Totale incassi visite (periodo): € {incasso_vis:.2f}**")

    # --- Incassi da Sedute ---
    st.markdown("### Incassi da sedute / terapie")

    query_s = """
        SELECT Data_Seduta AS Data, Professionista, Terapia, Costo, Pagato
        FROM Sedute
        WHERE Data_Seduta BETWEEN ? AND ?
    """
    params_s = [data_da_iso, data_a_iso]
    if professionista_f.strip():
        query_s += " AND Professionista LIKE ?"
        params_s.append(f"%{professionista_f.strip()}%")

    cur.execute(query_s, params_s)
    sed = cur.fetchall()

    incasso_sed = sum((r["Costo"] or 0.0) for r in sed if r["Pagato"])
    st.write(f"**Totale incassi sedute (periodo): € {incasso_sed:.2f}**")

    st.markdown("### Totale studio")
    st.success(f"**Totale generale incassato: € {incasso_vis + incasso_sed:.2f}**")

    conn.close()

# -----------------------------
# Main
# -----------------------------

def main():
    st.set_page_config(
        page_title="The Organism – Gestionale Studio",
        layout="wide"
    )

    # inizializza il database (se le tabelle non ci sono le crea)
    init_db()

    # login obbligatorio
    if not login():
        return

    # menu laterale
    st.sidebar.title("Navigazione")
    sezione = st.sidebar.radio(
        "Vai a",
        [
            "Pazienti",
            "Anamnesi",
            "Valutazioni visive / oculistiche",
            "Sedute / Terapie",
            "Coupon OF / SDS",
            "Dashboard incassi",
        ],
    )

    # routing alle varie sezioni
    if sezione == "Pazienti":
        ui_pazienti()
    elif sezione == "Anamnesi":
        ui_anamnesi()
    elif sezione == "Valutazioni visive / oculistiche":
        ui_valutazioni_visive()
    elif sezione == "Sedute / Terapie":
        ui_sedute()
    elif sezione == "Coupon OF / SDS":
        ui_coupons()
    elif sezione == "Dashboard incassi":
        ui_dashboard()


if __name__ == "__main__":
    main()

