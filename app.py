import streamlit as st

def debug_secrets_auth():
    has_auth = "auth" in st.secrets
    st.write("SECRETS: has [auth] =", has_auth)

    if has_auth:
        u_ok = "username" in st.secrets["auth"]
        p_ok = "password" in st.secrets["auth"]
        st.write("SECRETS auth.username presente =", u_ok)
        st.write("SECRETS auth.password presente =", p_ok)

        if p_ok:
            pw = st.secrets["auth"]["password"]
            st.write("Lunghezza password letta =", len(pw))
            st.write("Password vuota? =", (len(pw) == 0))

# chiama la funzione solo in test o solo per admin
debug_secrets_auth()
import sqlite3
APP_MODE = st.secrets.get("APP_MODE", "prod")
if APP_MODE == "test":
    st.warning("⚠️ MODALITÀ TEST — database separato (Neon TEST).")
from datetime import date, datetime
from typing import Optional, Dict
from letterhead_pdf import build_pdf_with_letterhead
from pdf_templates import build_pdf
# A5

# A4 2×A5

import os
import io
import urllib.parse
import csv
from functools import lru_cache
import math  # <-- aggiungi questa riga se non c'è
import textwrap  # per andare a capo nel referto

# PDF (referti e prescrizioni A4/A5)

# ---- PRINT HELPERS (image background + clean prescription table) ----
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, A5
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader

def _safe_str(x) -> str:
    if x is None:
        return ""
    s = str(x).strip()
    return s

def _blob_to_bytes(v):
    """Converte BLOB/bytea da SQLite/Postgres in bytes."""
    if v is None:
        return None
    if isinstance(v, (bytes, bytearray)):
        return bytes(v)
    # psycopg2 può restituire memoryview
    try:
        if isinstance(v, memoryview):
            return v.tobytes()
    except Exception:
        pass
    return None


def _fmt_num(x) -> str:
    if x is None:
        return ""
    try:
        # keep sign and 2 decimals for floats
        if isinstance(x, (int,)):
            return f"{x:d}"
        xf = float(x)
        return f"{xf:+.2f}"
    except Exception:
        return _safe_str(x)

def _find_bg_image(page_kind: str, variant: str) -> str | None:
    """
    Finds a background image inside common asset folders.
    page_kind: 'a4' or 'a5'
    variant: 'with_cirillo' or 'no_cirillo'
    """
    candidates = []

    # preferred canonical names
    base_names = [
        f"{page_kind}_{variant}",
        f"letterhead_{page_kind}_{variant}",
        f"prescrizione_{page_kind}_{variant}",
    ]
    exts = [".png", ".jpg", ".jpeg", ".webp"]

    # common folders
    folders = [
        "assets/print_bg",
        "assets/print",
        "assets",
        "assets/templates",   # just in case you put them here
    ]

    for folder in folders:
        for bn in base_names:
            for ext in exts:
                candidates.append(os.path.join(folder, bn + ext))

    # also accept your specific filenames (legacy)
    legacy = []
    if page_kind == "a4":
        legacy += [
            "assets/print_bg/CARATA INTESTAT THE ORGANISMA4.jpeg",
            "assets/CARATA INTESTAT THE ORGANISMA4.jpeg",
        ]
    if page_kind == "a5" and variant == "no_cirillo":
        legacy += [
            "assets/print_bg/PRESCRIZIONI THE ORGANISMAA5_no cirillo.png",
            "assets/PRESCRIZIONI THE ORGANISMAA5_no cirillo.png",
        ]
    candidates += legacy

    for p in candidates:
        if os.path.exists(p):
            return p

    # fallback: if with_cirillo missing, try no_cirillo; and vice versa
    if variant == "with_cirillo":
        return _find_bg_image(page_kind, "no_cirillo")
    return _find_bg_image(page_kind, "with_cirillo") if variant == "no_cirillo" else None

def _draw_bg_image_fullpage(c: canvas.Canvas, page_w: float, page_h: float, img_path: str | None):
    if not img_path:
        return
    try:
        img = ImageReader(img_path)
        iw, ih = img.getSize()
        scale = min(page_w / iw, page_h / ih)
        dw, dh = iw * scale, ih * scale
        x = (page_w - dw) / 2
        y = (page_h - dh) / 2
        c.drawImage(img, x, y, width=dw, height=dh, mask="auto")
    except Exception:
        # fail silently: no background
        return


def _draw_tabo_semicircle(c: canvas.Canvas, cx: float, cy: float, r: float, label: str):
    """Disegna semicerchio TABO 180→0 con tick principali e label."""
    c.saveState()
    c.setLineWidth(1)
    # arco superiore (0→180)
    c.arc(cx - r, cy - r, cx + r, cy + r, startAng=0, extent=180)

    # tick ogni 30° (più lunghi ogni 60°)
    for deg in range(0, 181, 10):
        rad = math.radians(deg)
        x1 = cx + r * math.cos(rad)
        y1 = cy + r * math.sin(rad)
        tick = 3*mm if deg % 30 == 0 else 1.8*mm
        if deg % 60 == 0:
            tick = 4*mm
        x2 = cx + (r - tick) * math.cos(rad)
        y2 = cy + (r - tick) * math.sin(rad)
        c.line(x2, y2, x1, y1)

    # labels principali
    c.setFont("Helvetica", 8)
    c.drawString(cx - r - 12*mm, cy + 1*mm, "180")
    c.drawCentredString(cx, cy + r + 3*mm, "90")
    c.drawString(cx + r + 4*mm, cy + 1*mm, "0")

    # label occhio sotto
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(cx, cy - r - 6*mm, label)
    c.restoreState()


def _draw_axis_arrow(c: canvas.Canvas, cx: float, cy: float, r: float, axis_deg, enabled: bool):
    """Disegna freccia direzione asse cilindro su TABO. axis_deg 0..180."""
    if not enabled:
        return
    try:
        ax = int(axis_deg)
    except Exception:
        return
    if ax < 0 or ax > 180:
        return

    c.saveState()
    c.setLineWidth(1.2)
    rad = math.radians(ax)
    x2 = cx + (r - 2*mm) * math.cos(rad)
    y2 = cy + (r - 2*mm) * math.sin(rad)
    c.line(cx, cy, x2, y2)

    # arrow head
    head = 4*mm
    ang1 = rad + math.radians(155)
    ang2 = rad - math.radians(155)
    c.line(x2, y2, x2 + head*math.cos(ang1), y2 + head*math.sin(ang1))
    c.line(x2, y2, x2 + head*math.cos(ang2), y2 + head*math.sin(ang2))
    c.restoreState()

def _draw_prescrizione_clean_table(c: canvas.Canvas, page_w: float, page_h: float, dati: dict, top_offset_mm: float = 60):
    """
    Clean layout (no boxes): writes a readable table with SF/CIL/AX for OD/OS:
    Lontano / Intermedio / Vicino.
    """
    left = 18 * mm
    right = page_w - 18 * mm
    y = page_h - top_offset_mm * mm  # below header line

    # marker di debug: posizione inizio stampa
    c.saveState(); c.setFont('Helvetica', 7); c.drawString(left-8*mm, y+2, '1'); c.restoreState()

    c.setFont("Helvetica", 11)
    c.drawString(left, y, f"Sig.: {_safe_str(dati.get('paziente',''))}")
    c.drawRightString(right, y, f"Data: {_safe_str(dati.get('data',''))}")
    y -= 18*mm

    # headers
    c.setFont("Helvetica-Bold", 10)
    c.drawString(left, y, "PRESCRIZIONE OCCHIALI")
    y -= 7 * mm

    # --- TABO semicircles + axis arrow (asse cilindro) ---
    # Usare asse del LONTANO; freccia solo se CIL != 0
    r_tabo = 24 * mm
    # Spazio extra: evita che Nome/Data coprano i semicerchi
    y -= 20 * mm
    cy_tabo = y - 4 * mm
    cx_od = left + 55 * mm
    cx_os = left + 135 * mm

    _draw_tabo_semicircle(c, cx_od, cy_tabo, r_tabo, "Occhio Destro")
    _draw_tabo_semicircle(c, cx_os, cy_tabo, r_tabo, "Occhio Sinistro")

    # Scegli l'asse da disegnare sui TABO.
    # Regola: usa prima il rigo che ha CIL diverso da 0; se nessuno, usa il primo asse diverso da 0 (se presente).
    def _pick_axis_and_cyl(prefix: str):
        cand = [
            ("lon", dati.get(f"{prefix}_lon_cil"), dati.get(f"{prefix}_lon_ax")),
            ("int", dati.get(f"{prefix}_int_cil"), dati.get(f"{prefix}_int_ax")),
            ("vic", dati.get(f"{prefix}_vic_cil"), dati.get(f"{prefix}_vic_ax")),
        ]
        # 1) priorità: CIL != 0
        for _, cil, ax in cand:
            try:
                if float(cil or 0) != 0.0 and ax is not None and str(ax).strip() != "":
                    return ax, cil
            except Exception:
                pass
        # 2) fallback: asse != 0 (anche se CIL=0) — utile se vuoi indicare comunque la direzione di montaggio
        for _, cil, ax in cand:
            try:
                if ax is not None and str(ax).strip() != "":
                    return ax, cil
            except Exception:
                if ax is not None and str(ax).strip() != "":
                    return ax, cil
        return None, None

    od_ax_pick, od_cil_pick = _pick_axis_and_cyl("od")
    os_ax_pick, os_cil_pick = _pick_axis_and_cyl("os")

    _draw_axis_arrow(c, cx_od, cy_tabo, r_tabo, od_ax_pick, enabled=(od_ax_pick is not None))
    _draw_axis_arrow(c, cx_os, cy_tabo, r_tabo, os_ax_pick, enabled=(os_ax_pick is not None))

    # spazio dopo TABO
    y -= 2 * r_tabo + 10 * mm

    # columns
    col_label = left
    col_od_sf  = left + 28*mm
    col_od_cil = left + 46*mm
    col_od_ax  = left + 64*mm

    col_os_sf  = left + 112*mm
    col_os_cil = left + 130*mm
    col_os_ax  = left + 148*mm

    c.setFont("Helvetica-Bold", 9)
    c.drawString(col_od_sf - 10*mm, y, "OD")
    c.drawString(col_os_sf - 10*mm, y, "OS")
    y -= 5 * mm

    c.setFont("Helvetica-Bold", 9)
    c.drawString(col_label, y, "")
    c.drawString(col_od_sf,  y, "SF")
    c.drawString(col_od_cil, y, "CIL")
    c.drawString(col_od_ax,  y, "AX")
    c.drawString(col_os_sf,  y, "SF")
    c.drawString(col_os_cil, y, "CIL")
    c.drawString(col_os_ax,  y, "AX")
    y -= 6 * mm

    def row(label, od_sf, od_cil, od_ax, os_sf, os_cil, os_ax):
        nonlocal y
        c.setFont("Helvetica", 9)
        c.drawString(col_label, y, label)
        c.drawRightString(col_od_sf + 10*mm, y, _fmt_num(od_sf))
        c.drawRightString(col_od_cil + 10*mm, y, _fmt_num(od_cil))
        c.drawRightString(col_od_ax + 10*mm, y, _safe_str(od_ax))

        c.drawRightString(col_os_sf + 10*mm, y, _fmt_num(os_sf))
        c.drawRightString(col_os_cil + 10*mm, y, _fmt_num(os_cil))
        c.drawRightString(col_os_ax + 10*mm, y, _safe_str(os_ax))
        y -= 6 * mm

    row("Lontano",
        dati.get("od_lon_sf"), dati.get("od_lon_cil"), dati.get("od_lon_ax"),
        dati.get("os_lon_sf"), dati.get("os_lon_cil"), dati.get("os_lon_ax"))
    row("Intermedio",
        dati.get("od_int_sf"), dati.get("od_int_cil"), dati.get("od_int_ax"),
        dati.get("os_int_sf"), dati.get("os_int_cil"), dati.get("os_int_ax"))
    row("Vicino",
        dati.get("od_vic_sf"), dati.get("od_vic_cil"), dati.get("od_vic_ax"),
        dati.get("os_vic_sf"), dati.get("os_vic_cil"), dati.get("os_vic_ax"))

    y -= 8 * mm

    # Lenti / trattamenti
    c.setFont("Helvetica-Bold", 10)
    c.drawString(left, y, "Lenti consigliate / Trattamenti")
    y -= 6 * mm
    c.setFont("Helvetica", 9)
    lenti = ", ".join(dati.get("lenti", []) or [])
    if lenti:
        c.drawString(left, y, f"Lenti: {lenti}")
        y -= 5 * mm
    altri = _safe_str(dati.get("altri_trattamenti", ""))
    if altri:
        c.drawString(left, y, f"Altri trattamenti: {altri}")
        y -= 5 * mm

    note = _safe_str(dati.get("note", ""))
    if note:
        y -= 2 * mm
        c.setFont("Helvetica-Bold", 9)
        c.drawString(left, y, "Note:")
        y -= 5 * mm
        c.setFont("Helvetica", 9)
        max_chars = 110 if page_w >= A4[0] else 70
        for i in range(0, len(note), max_chars):
            c.drawString(left, y, note[i:i+max_chars])
            y -= 5 * mm

def _prescrizione_pdf_imagebg(page_size, page_kind: str, con_cirillo: bool, dati: dict) -> bytes:
    variant = "with_cirillo" if con_cirillo else "no_cirillo"
    bg = _find_bg_image(page_kind, variant)
    page_w, page_h = page_size
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=page_size)
    _draw_bg_image_fullpage(c, page_w, page_h, bg)
    # top offset: A5 has less vertical space
    top_offset = 72 if page_kind == "a4" else 62
    _draw_prescrizione_clean_table(c, page_w, page_h, dati, top_offset_mm=top_offset)
    c.showPage(); c.save()
    buf.seek(0)
    return buf.read()

try:
    from reportlab.lib.pagesizes import A4, A5, landscape
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


# PDF merge (template letterhead)
try:
    from pypdf import PdfReader, PdfWriter
    from pypdf._page import PageObject
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False


def _make_overlay_pdf_pagesize(pagesize, draw_fn):
    """Crea un PDF overlay (una pagina) con ReportLab per un pagesize arbitrario."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=pagesize)
    w, h = pagesize
    draw_fn(c, w, h)
    c.showPage()
    c.save()
    buf.seek(0)
    return buf.read()

@lru_cache(maxsize=4)
def _build_a4_landscape_2up_template_bytes(variant: str) -> bytes:
    """Crea un template A4 landscape con 2 template A5 affiancati (sinistra+destra)."""
    if not PYPDF_AVAILABLE:
        raise RuntimeError("pypdf non disponibile")

    a4_w, a4_h = landscape(A4)
    a5_w, a5_h = A5

    a5_path = "assets/letterhead/a5_with_cirillo.pdf" if variant == "with_cirillo" else "assets/letterhead/a5_no_cirillo.pdf"
    reader = PdfReader(a5_path)
    a5_page = reader.pages[0]

    out_page = PageObject.create_blank_page(width=a4_w, height=a4_h)

    # due pannelli A5 affiancati
    out_page.merge_translated_page(a5_page, tx=0, ty=0)
    out_page.merge_translated_page(a5_page, tx=a5_w, ty=0)

    writer = PdfWriter()
    writer.add_page(out_page)
    out = io.BytesIO()
    writer.write(out)
    out.seek(0)
    return out.read()


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



def _is_streamlit_cloud() -> bool:
    """Heuristic check: True when running on Streamlit Cloud."""
    try:
        # Streamlit Cloud mounts the repo under /mount/src
        if os.getcwd().startswith("/mount/src") or os.path.exists("/mount/src"):
            return True
    except Exception:
        pass
    # Fallback heuristics
    for k in ("STREAMLIT_CLOUD", "STREAMLIT_SHARING", "STREAMLIT_RUNTIME_ENV"):
        v = os.getenv(k, "")
        if str(v).lower() in ("1", "true", "yes", "cloud", "sharing"):
            return True
    return False



class _RowCI(dict):
    """Case-insensitive dict for row access.

    The app was written against sqlite3.Row with mixed-case column names (e.g., 'ID', 'CAP').
    PostgreSQL folds unquoted identifiers to lowercase, so DictCursor returns keys like 'id', 'cap'.
    This wrapper allows row['ID'] to resolve to row['id'] transparently.
    """
    def __getitem__(self, key):
        if isinstance(key, str):
            if dict.__contains__(self, key):
                return dict.__getitem__(self, key)
            lk = key.lower()
            if dict.__contains__(self, lk):
                return dict.__getitem__(self, lk)
            uk = key.upper()
            if dict.__contains__(self, uk):
                return dict.__getitem__(self, uk)
        return dict.__getitem__(self, key)

    def get(self, key, default=None):
        try:
            return self.__getitem__(key)
        except KeyError:
            return default

class _PgCursor:
    """Cursor wrapper to:
    - translate SQLite '?' placeholders -> psycopg2 '%s'
    - return psycopg2 DictRow (supports both dict and index access)
    """
    def __init__(self, cur):
        self._cur = cur

    @staticmethod
    def _adapt_sql(sql: str) -> str:
        # naive but effective for this app: replace all '?' placeholders
        return sql.replace("?", "%s")

    def execute(self, sql, params=None):
        sql2 = self._adapt_sql(str(sql))
        if params is None:
            return self._cur.execute(sql2)
        return self._cur.execute(sql2, params)

    def executemany(self, sql, seq_of_params):
        sql2 = self._adapt_sql(str(sql))
        return self._cur.executemany(sql2, seq_of_params)

    def fetchone(self):
        row = self._cur.fetchone()
        if row is None:
            return None
        try:
            return _RowCI(dict(row))
        except Exception:
            return row

    def fetchall(self):
        rows = self._cur.fetchall()
        out = []
        for r in rows:
            try:
                out.append(_RowCI(dict(r)))
            except Exception:
                out.append(r)
        return out

    @property
    def rowcount(self):
        return self._cur.rowcount

    @property
    def description(self):
        return self._cur.description

    def close(self):
        try:
            return self._cur.close()
        except Exception:
            return None


class _PgConn:
    """Connection wrapper to emulate the minimal sqlite3 API used by the app."""
    def __init__(self, conn):
        self._conn = conn

    def cursor(self):
        # DictCursor yields DictRow which supports both mapping and sequence access
        return _PgCursor(self._conn.cursor(cursor_factory=psycopg2.extras.DictCursor))

    def commit(self):
        return self._conn.commit()

    def close(self):
        return self._conn.close()

def _secrets_diagnostics():
    """Return non-sensitive diagnostics about Streamlit secrets/env.

    Non stampa mai valori sensibili (solo presenza/chiavi/lunghezze).
    """
    diag = {
        "secrets_available": False,
        "secrets_keys": [],
        "has_db_section": False,
        "db_keys": [],
        # True se esiste una delle chiavi attese e il valore non è vuoto dopo strip()
        "has_db_database_url": False,
        "db_database_url_key": None,
        "db_database_url_len": 0,
        "has_root_database_url": False,
        "root_database_url_key": None,
        "root_database_url_len": 0,
        "env_database_url": False,
        "env_database_url_len": 0,
    }

    sec = None
    try:
        sec = getattr(st, "secrets", None)
        if sec is not None:
            diag["secrets_available"] = True
            try:
                diag["secrets_keys"] = sorted(list(sec.keys()))
            except Exception:
                diag["secrets_keys"] = ["<unreadable>"]
    except Exception:
        sec = None

    # --- [db] section ---
    try:
        diag["has_db_section"] = bool(sec is not None and ("db" in sec))
    except Exception:
        diag["has_db_section"] = False

    if diag["has_db_section"]:
        try:
            db = sec.get("db", {})
            if isinstance(db, dict):
                diag["db_keys"] = sorted(list(db.keys()))
                for k in ("DATABASE_URL", "database_url", "url", "URL"):
                    v = db.get(k)
                    if v is not None:
                        s = str(v)
                        l = len(s.strip())
                        if l > 0:
                            diag["has_db_database_url"] = True
                            diag["db_database_url_key"] = k
                            diag["db_database_url_len"] = l
                            break
                        else:
                            # chiave presente ma vuota: salva info (se non già trovato nulla)
                            if diag["db_database_url_key"] is None:
                                diag["db_database_url_key"] = k
                                diag["db_database_url_len"] = 0
        except Exception:
            pass

    # --- root keys ---
    if sec is not None:
        try:
            for k in ("DATABASE_URL", "database_url"):
                v = sec.get(k)
                if v is not None:
                    s = str(v)
                    l = len(s.strip())
                    if l > 0:
                        diag["has_root_database_url"] = True
                        diag["root_database_url_key"] = k
                        diag["root_database_url_len"] = l
                        break
                    else:
                        if diag["root_database_url_key"] is None:
                            diag["root_database_url_key"] = k
                            diag["root_database_url_len"] = 0
        except Exception:
            pass

    # --- env ---
    try:
        envv = (os.getenv("DATABASE_URL", "") or os.getenv("database_url", "") or "")
        diag["env_database_url_len"] = len(envv.strip())
        diag["env_database_url"] = diag["env_database_url_len"] > 0
    except Exception:
        diag["env_database_url"] = False
        diag["env_database_url_len"] = 0

    return diag
def _get_database_url() -> str:
    """Return DATABASE_URL from Streamlit secrets or environment.
    Supports either:
      - [db] DATABASE_URL = "..."
      - DATABASE_URL = "..."  (root)
    """
    sec = _safe_secrets()

    # 1) [db].DATABASE_URL (preferred)
    try:
        dbsec = sec.get("db", {})
        if isinstance(dbsec, dict):
            for k in ("DATABASE_URL", "database_url", "url", "URL"):
                v = dbsec.get(k)
                if v:
                    return str(v).strip()
    except Exception:
        pass

    # 2) root DATABASE_URL
    try:
        for k in ("DATABASE_URL", "database_url"):
            v = sec.get(k)
            if v:
                return str(v).strip()
    except Exception:
        pass

    # 3) environment
    return (os.getenv("DATABASE_URL", "") or os.getenv("database_url", "") or "").strip()


def _normalize_db_url(u: str) -> str:
    u = (u or "").strip()
    # strip accidental surrounding quotes
    if (u.startswith('"') and u.endswith('"')) or (u.startswith("'") and u.endswith("'")):
        u = u[1:-1].strip()
    # normalize scheme
    if u.startswith("postgres://"):
        u = "postgresql://" + u[len("postgres://"):]
    return u

_DB_URL = _normalize_db_url(_get_database_url())
_DB_BACKEND = "postgres" if _DB_URL else "sqlite"


def _sidebar_db_indicator():
    """Mostra in sidebar quale database sta usando l'app."""
    try:
        if _is_streamlit_cloud():
            if _DB_BACKEND == "postgres" and _DB_URL:
                st.sidebar.success("🟢 DB: PostgreSQL (Neon)")
            else:
                st.sidebar.error("🔴 DB: PostgreSQL (Neon) NON configurato")
        else:
            if _DB_BACKEND == "postgres" and _DB_URL:
                st.sidebar.success("🟢 DB: PostgreSQL (Neon)")
            else:
                # locale / test
                db_path = os.getenv("SQLITE_DB_PATH", "the_organism_gestionale_TEST.db")
                st.sidebar.warning(f"🟡 DB: SQLite ({db_path})")
    except Exception:
        pass

def _require_postgres_on_cloud():
    # Mostra sempre l'indicatore, anche in caso di errore
    _sidebar_db_indicator()
    if _is_streamlit_cloud() and _DB_BACKEND != "postgres":
        st.error("❌ DATABASE_URL mancante nei Secrets: in Streamlit Cloud il gestionale richiede PostgreSQL (Neon).")
        diag = _secrets_diagnostics()
        st.write("Diagnostica Secrets (senza valori):")
        st.write({
            "secrets_available": diag.get("secrets_available"),
            "secrets_keys": diag.get("secrets_keys"),
            "has_db_section": diag.get("has_db_section"),
            "db_keys": diag.get("db_keys"),
            "has_db_database_url": diag.get("has_db_database_url"),
            "db_database_url_key": diag.get("db_database_url_key"),
            "db_database_url_len": diag.get("db_database_url_len"),
            "has_root_database_url": diag.get("has_root_database_url"),
            "root_database_url_key": diag.get("root_database_url_key"),
            "root_database_url_len": diag.get("root_database_url_len"),
            "env_database_url": diag.get("env_database_url"),
            "env_database_url_len": diag.get("env_database_url_len"),
        })
        st.write("Chiavi in [db]:", diag.get("db_keys"))
        st.write("Lunghezza DATABASE_URL (strip):", diag.get("db_database_url_len"))
        st.write("DATABASE_URL sembra postgresql:// ?", str(_safe_secrets().get("db",{}).get("DATABASE_URL","")).strip().lower().startswith("postgresql://"))
        st.info("""Apri la tua app su Streamlit Cloud → Settings → Secrets e aggiungi:

[db]
DATABASE_URL = \"postgresql://...sslmode=require\"

Poi premi Save e riavvia l'app (Reboot).""")
        st.stop()
def _connect_cached():
    _require_postgres_on_cloud()
    if _DB_BACKEND == "postgres":
        if not PSYCOPG2_AVAILABLE:
            raise RuntimeError("psycopg2 non disponibile. Aggiungi psycopg2-binary a requirements.txt")

        try:
            conn = psycopg2.connect(_DB_URL)
        except Exception:
            # Non-leak diagnostics (does not print the URL)
            u = _DB_URL or ""
            st.error("❌ Errore connessione PostgreSQL (Neon). La DATABASE_URL non sembra in un formato valido per psycopg2.")
            st.write({
                "db_url_len": len(u),
                "db_url_has_whitespace": any(ch.isspace() for ch in u),
                "db_url_scheme": (u.split("://", 1)[0] if "://" in u else "<missing>"),
                "hint_1": "Verifica che sia su UNA sola riga nei Secrets (nessun a capo).",
                "hint_2": "Usa lo schema 'postgresql://'.",
                "hint_3": "Se la password contiene caratteri speciali (@ : / ? # & %), deve essere URL-encoded (es. @ -> %40).",
            })
            st.stop()

        return _PgConn(conn)

    # SQLite (locale / fallback)
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

        
        # Migrazione campi Esame Obiettivo (SQLite) – aggiunge colonne se mancanti
        try:
            cur.execute("PRAGMA table_info(Valutazioni_Visive)")
            existing_cols = {r[1] for r in cur.fetchall()}
            eo_cols = [
                ("Cornea", "TEXT"),
                ("Camera_Anteriore", "TEXT"),
                ("Cristallino", "TEXT"),
                ("Congiuntiva_Sclera", "TEXT"),
                ("Iride_Pupilla", "TEXT"),
                ("Vitreo", "TEXT"),
            ]
            for col, typ in eo_cols:
                if col not in existing_cols:
                    cur.execute(f"ALTER TABLE Valutazioni_Visive ADD COLUMN {col} {typ}")
        except Exception:
            # Non bloccare l'avvio se la migrazione fallisce
            pass
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

        
        # Consensi privacy (adulto / minore) + marketing (Klaviyo)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS Consensi_Privacy (
                ID                  INTEGER PRIMARY KEY AUTOINCREMENT,
                Paziente_ID         INTEGER NOT NULL,
                Data_Ora            TEXT,
                Tipo                TEXT,   -- ADULTO / MINORE
                Tutore_Nome         TEXT,
                Tutore_CF           TEXT,
                Tutore_Telefono     TEXT,
                Tutore_Email        TEXT,
                Consenso_Trattamento    INTEGER DEFAULT 0,
                Consenso_Comunicazioni  INTEGER DEFAULT 0,
                Consenso_Marketing       INTEGER DEFAULT 0,
                Canale_Email            INTEGER DEFAULT 0,
                Canale_SMS              INTEGER DEFAULT 0,
                Canale_WhatsApp          INTEGER DEFAULT 0,
                Usa_Klaviyo              INTEGER DEFAULT 0,
                Firma_Blob               BLOB,
                Firma_Filename           TEXT,
                Firma_URL                TEXT,
                Firma_Source             TEXT,
                Note                    TEXT
            )
    """
)


        
        # Migrazione Consensi_Privacy (SQLite) – aggiunge colonne firma se mancanti
        try:
            cur.execute("PRAGMA table_info(Consensi_Privacy)")
            existing_cols = {r[1] for r in cur.fetchall()}
            mig_cols = [
                ("Firma_Blob", "BLOB"),
                ("Firma_Filename", "TEXT"),
                ("Firma_URL", "TEXT"),
                ("Firma_Source", "TEXT"),
            ]
            for col, typ in mig_cols:
                if col not in existing_cols:
                    cur.execute(f"ALTER TABLE Consensi_Privacy ADD COLUMN {col} {typ}")
        except Exception:
            pass

        
        # Relazioni Cliniche (SQLite)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS relazioni_cliniche (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        paziente_id  INTEGER NOT NULL,
        tipo         TEXT NOT NULL,
        titolo       TEXT NOT NULL,
        data_relazione TEXT NOT NULL,
        docx_path    TEXT NOT NULL,
        pdf_path     TEXT,
        note         TEXT,
        created_at   TEXT NOT NULL
            )
            """
        )
        try:
            cur.execute("CREATE INDEX IF NOT EXISTS idx_relazioni_paziente ON relazioni_cliniche(paziente_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_relazioni_tipo ON relazioni_cliniche(tipo)")
        except Exception:
            pass
        
        conn.commit()
        return

    # -------------------------
    # PostgreSQL (Neon) init
    # -------------------------
    # Nota: usiamo tipi compatibili e vincoli FK corretti.
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS Pazienti (
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
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS Anamnesi (
            ID              BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
            Paziente_ID     BIGINT NOT NULL REFERENCES Pazienti(ID) ON DELETE CASCADE,
            Data_Anamnesi   TEXT,
            Motivo          TEXT,
            Storia          TEXT,
            Note            TEXT,
            Perinatale      TEXT,
            Sviluppo        TEXT,
            Scuola          TEXT,
            Emotivo         TEXT,
            Sensoriale      TEXT,
            Stile_Vita      TEXT
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS Valutazioni_Visive (
            ID                  BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
            Paziente_ID         BIGINT NOT NULL REFERENCES Pazienti(ID) ON DELETE CASCADE,
            Data_Valutazione    TEXT,
            Tipo_Visita         TEXT,
            Professionista      TEXT,
            Anamnesi            TEXT,
            Acuita_Nat_OD       TEXT, Acuita_Nat_OS       TEXT, Acuita_Nat_OO       TEXT,
            Acuita_Corr_OD      TEXT, Acuita_Corr_OS      TEXT, Acuita_Corr_OO      TEXT,
            SF_Ogg_OD           REAL, CIL_Ogg_OD          REAL, AX_Ogg_OD           INTEGER,
            SF_Ogg_OS           REAL, CIL_Ogg_OS          REAL, AX_Ogg_OS           INTEGER,
            SF_Sogg_OD          REAL, CIL_Sogg_OD         REAL, AX_Sogg_OD          INTEGER,
            SF_Sogg_OS          REAL, CIL_Sogg_OS         REAL, AX_Sogg_OS          INTEGER,
            ADD_Vicino          REAL,
            K1_OD_mm            REAL, K1_OD_D            REAL, K2_OD_mm            REAL, K2_OD_D            REAL,
            K1_OS_mm            REAL, K1_OS_D            REAL, K2_OS_mm            REAL, K2_OS_D            REAL,
            Tono_OD             REAL, Tono_OS             REAL,
            Motilita            TEXT,
            Cover_Test          TEXT,
            Stereopsi           TEXT,
            PPC_cm              REAL,
            Ishihara            TEXT,
            Pachim_OD_um        REAL, Pachim_OS_um        REAL,
            Fondo               TEXT,
            Campo_Visivo        TEXT,
            OCT                 TEXT,
            Topografia          TEXT,
            Costo               REAL,
            Pagato              INTEGER NOT NULL DEFAULT 0,
            Note                TEXT
        )
        """
    )

    
    # Migrazione campi Esame Obiettivo (PostgreSQL) – aggiunge colonne se mancanti
    try:
        cur.execute("""
            ALTER TABLE IF EXISTS Valutazioni_Visive
                ADD COLUMN IF NOT EXISTS Cornea              TEXT,
                ADD COLUMN IF NOT EXISTS Camera_Anteriore    TEXT,
                ADD COLUMN IF NOT EXISTS Cristallino         TEXT,
                ADD COLUMN IF NOT EXISTS Congiuntiva_Sclera  TEXT,
                ADD COLUMN IF NOT EXISTS Iride_Pupilla       TEXT,
                ADD COLUMN IF NOT EXISTS Vitreo              TEXT;
        """)
    except Exception:
        pass

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS Sedute (
            ID              BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
            Paziente_ID     BIGINT NOT NULL REFERENCES Pazienti(ID) ON DELETE CASCADE,
            Data_Seduta     TEXT,
            Terapia         TEXT,
            Professionista  TEXT,
            Costo           REAL,
            Pagato          INTEGER NOT NULL DEFAULT 0,
            Note            TEXT
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS Coupons (
            ID                BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
            Paziente_ID       BIGINT NOT NULL REFERENCES Pazienti(ID) ON DELETE CASCADE,
            Tipo_Coupon       TEXT NOT NULL,     -- OF o SDS
            Codice_Coupon     TEXT,              -- numero / codice coupon
            Data_Assegnazione TEXT,
            Note              TEXT,
            Utilizzato        INTEGER NOT NULL DEFAULT 0
        )
        """
    )

    



    # Consensi privacy (adulto / minore) + marketing (Klaviyo)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS Consensi_Privacy (
            ID                  BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
            Paziente_ID         BIGINT NOT NULL REFERENCES Pazienti(ID) ON DELETE CASCADE,
            Data_Ora            TEXT,
            Tipo                TEXT,   -- ADULTO / MINORE
            Tutore_Nome         TEXT,
            Tutore_CF           TEXT,
            Tutore_Telefono     TEXT,
            Tutore_Email        TEXT,
            Consenso_Trattamento    INTEGER NOT NULL DEFAULT 0,
            Consenso_Comunicazioni  INTEGER NOT NULL DEFAULT 0,
            Consenso_Marketing       INTEGER NOT NULL DEFAULT 0,
            Canale_Email            INTEGER NOT NULL DEFAULT 0,
            Canale_SMS              INTEGER NOT NULL DEFAULT 0,
            Canale_WhatsApp          INTEGER NOT NULL DEFAULT 0,
            Usa_Klaviyo              INTEGER NOT NULL DEFAULT 0,
            Note                    TEXT
        )
        """
    )

    
    # Migrazione Consensi_Privacy (PostgreSQL) – aggiunge colonne firma se mancanti
    try:
        cur.execute(
            """
            ALTER TABLE IF EXISTS Consensi_Privacy
                ADD COLUMN IF NOT EXISTS Firma_Blob BYTEA,
                ADD COLUMN IF NOT EXISTS Firma_Filename TEXT,
                ADD COLUMN IF NOT EXISTS Firma_URL TEXT,
                ADD COLUMN IF NOT EXISTS Firma_Source TEXT;
            """
        )
    except Exception:
        pass

# Relazioni Cliniche (PostgreSQL)
# (Inizializzazione spostata dentro init_db / funzioni helper per evitare NameError in import)


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

# ------------------------------
# Codice Fiscale - tabelle
# ------------------------------
# Mese (01-12) -> lettera
MESE_CF = {
    1: "A", 2: "B", 3: "C", 4: "D", 5: "E", 6: "H",
    7: "L", 8: "M", 9: "P", 10: "R", 11: "S", 12: "T",
}

# Tabelle ufficiali per il carattere di controllo (16° carattere)
CONTROL_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

EVEN_MAP = {
    **{str(i): i for i in range(10)},
    **{chr(ord("A") + i): i for i in range(26)},
}

ODD_MAP = {
    # cifre
    "0": 1, "1": 0, "2": 5, "3": 7, "4": 9,
    "5": 13, "6": 15, "7": 17, "8": 19, "9": 21,
    # lettere
    "A": 1, "B": 0, "C": 5, "D": 7, "E": 9,
    "F": 13, "G": 15, "H": 17, "I": 19, "J": 21,
    "K": 2, "L": 4, "M": 18, "N": 20, "O": 11,
    "P": 3, "Q": 6, "R": 8, "S": 12, "T": 14,
    "U": 16, "V": 10, "W": 22, "X": 25, "Y": 24, "Z": 23,
}


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
    - Usa background letterhead (con/ senza Cirillo) se disponibile
    - Contenuto spostato più in alto di ~2.5 cm rispetto alla versione precedente
    - Stampa SOLO i campi compilati (nessuna riga vuota o con soli separatori)
    """
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Sfondo intestazione (immagine A4)
    try:
        variant = "with_cirillo" if include_header else "no_cirillo"
        bg = _find_bg_image("a4", variant)
        _draw_bg_image_fullpage(c, width, height, bg)
    except Exception:
        pass

    left = 30 * mm
    right = width - 30 * mm

    # ✅ Alza la stampa di 2.5 cm (25mm)
    top_with_header = height - 30 * mm   # prima: 55mm
    top_no_header   = height - 55 * mm   # prima: 80mm
    top = top_with_header if include_header else top_no_header

    bottom = 30 * mm
    y = top

    def _newline(n=12):
        nonlocal y
        y -= n

    def _reset_y_for_new_page():
        nonlocal y
        y = top_with_header if include_header else top_no_header

    def _ensure_space(min_y=bottom + 40):
        nonlocal y
        if y < min_y:
            c.showPage()
            # riapplica background anche sulle pagine successive
            try:
                variant = "with_cirillo" if include_header else "no_cirillo"
                bg = _find_bg_image("a4", variant)
                _draw_bg_image_fullpage(c, width, height, bg)
            except Exception:
                pass
            _reset_y_for_new_page()

    def _draw_header():
        # Header testuale (fallback); normalmente l'intestazione è già nel background.
        yy = height - 18 * mm
        c.setFont("Helvetica-Bold", 14)
        c.drawString(left, yy, "Studio The Organism")
        yy -= 12
        c.setFont("Helvetica", 10)
        c.drawString(left, yy, "Via De Rosa 46 – Pagani (SA)")
        yy -= 11
        c.drawString(left, yy, "www.ferraioligiuseppe.it  |  Tel. 393 581 7157")
        c.line(left, yy - 6, right, yy - 6)

    # Se vuoi un header testuale extra (di solito no), abilitalo qui:
    # if include_header:
    #     _draw_header()
    #     y = top_with_header

    c.setFont("Helvetica-Bold", 12)
    c.drawString(left, y, "Referto oculistico / optometrico")
    _newline(18)

    # Dati paziente (solo se presenti)
    c.setFont("Helvetica", 11)
    nome_paz = f"{paziente.get('Cognome','')} {paziente.get('Nome','')}".strip()
    if nome_paz:
        c.drawString(left, y, f"Paziente: {nome_paz}")
        _newline(14)

    dn = _format_data_it_from_iso(paziente.get("Data_Nascita"))
    if dn:
        c.drawString(left, y, f"Data di nascita: {dn}")
        _newline(14)

    data_vis = _format_data_it_from_iso(valutazione.get("Data_Valutazione"))
    if data_vis:
        c.drawString(left, y, f"Data visita: {data_vis}")
        _newline(14)

    tipo_visita = (valutazione.get("Tipo_Visita") or "").strip()
    if tipo_visita:
        c.drawString(left, y, f"Tipo visita: {tipo_visita}")
        _newline(14)

    prof = (valutazione.get("Professionista") or "").strip()
    if prof:
        c.drawString(left, y, f"Professionista: {prof}")
        _newline(16)

    # -------------------
    # Acuità visiva (solo campi compilati)
    # -------------------
    def _fmt_av_triplet(prefix: str, od, os_, oo):
        parts = []
        if (od or "").strip():
            parts.append(f"OD {str(od).strip()}")
        if (os_ or "").strip():
            parts.append(f"OS {str(os_).strip()}")
        if (oo or "").strip():
            parts.append(f"OO {str(oo).strip()}")
        if not parts:
            return ""
        return f"{prefix}: " + "   ".join(parts)

    av_nat = _fmt_av_triplet(
        "Acuità visiva naturale",
        valutazione.get("Acuita_Nat_OD"),
        valutazione.get("Acuita_Nat_OS"),
        valutazione.get("Acuita_Nat_OO"),
    )
    av_corr = _fmt_av_triplet(
        "Acuità visiva corretta",
        valutazione.get("Acuita_Corr_OD"),
        valutazione.get("Acuita_Corr_OS"),
        valutazione.get("Acuita_Corr_OO"),
    )

    for line in (av_nat, av_corr):
        if line:
            _ensure_space()
            c.drawString(left, y, line)
            _newline(14)
    if av_nat or av_corr:
        _newline(6)

    # -------------------
    # Esame obiettivo (solo campi compilati)
    # -------------------
    eo = [
        ("Cornea", valutazione.get("Cornea")),
        ("Camera anteriore", valutazione.get("Camera_Anteriore")),
        ("Cristallino", valutazione.get("Cristallino")),
        ("Congiuntiva / Sclera", valutazione.get("Congiuntiva_Sclera")),
        ("Iride / Pupilla", valutazione.get("Iride_Pupilla")),
        ("Vitreo", valutazione.get("Vitreo")),
    ]
    eo_items = [(lab, ("" if v is None else str(v).strip())) for lab, v in eo]
    eo_items = [(lab, v) for lab, v in eo_items if v]

    if eo_items:
        c.setFont("Helvetica-Bold", 11)
        _ensure_space()
        c.drawString(left, y, "Esame obiettivo (strutture oculari)")
        _newline(14)
        c.setFont("Helvetica", 11)
        for lab, vv in eo_items:
            _ensure_space()
            c.drawString(left, y, f"- {lab}: {vv}")
            _newline(13)
        _newline(6)

    # -------------------
    # Dettaglio clinico (valutazione['Note']) filtrato: SOLO righe compilate
    # -------------------
    testo_raw = (valutazione.get("Note") or "").strip()

    def _is_filled_line(line: str) -> bool:
        s = (line or "").strip()
        if not s:
            return False
        # Non stampare righe di firma già gestite a parte
        if s.lower().startswith("firma"):
            return False
        # Righe tipo "- Campo:" senza contenuto
        if s.startswith("-"):
            body = s.lstrip("-").strip()
            # "- X:" oppure "- X :" oppure "- X:" + solo spazi
            if ":" in body:
                left_part, right_part = body.split(":", 1)
                if right_part.strip() == "":
                    return False
            else:
                # "- " senza niente
                if body == "":
                    return False
        else:
            # Righe tipo "NOTE LIBERE:" senza contenuto
            if ":" in s:
                left_part, right_part = s.split(":", 1)
                if right_part.strip() == "" and len(left_part.strip()) <= 40:
                    return False
        return True

    def _is_section_header(line: str) -> bool:
        s = (line or "").strip()
        if not s:
            return False
        # Header tipici in maiuscolo (es: "ACUITÀ VISIVA", "TONOMETRIA", ecc.)
        if s == s.upper() and any(ch.isalpha() for ch in s) and ":" not in s and not s.startswith("-"):
            return True
        return False

    def _filter_note_block(raw: str) -> list[str]:
        lines = [ln.rstrip() for ln in raw.splitlines()]
        sections = []
        current_header = None
        current_items = []

        def flush():
            nonlocal current_header, current_items
            if current_items:
                if current_header:
                    sections.append(current_header)
                sections.extend(current_items)
            current_header = None
            current_items = []

        for ln in lines:
            if _is_section_header(ln):
                flush()
                current_header = ln.strip()
                continue
            if _is_filled_line(ln):
                current_items.append(ln.strip())
        flush()
        return sections

    filtered_lines = _filter_note_block(testo_raw)

    if filtered_lines:
        c.setFont("Helvetica-Bold", 11)
        _ensure_space()
        c.drawString(left, y, "Dettaglio clinico")
        _newline(14)

        c.setFont("Helvetica", 11)
        wrapper = textwrap.TextWrapper(width=90)
        for ln in filtered_lines:
            # lascia una piccola distanza prima dei titoli sezione
            if _is_section_header(ln):
                _newline(4)
                c.setFont("Helvetica-Bold", 11)
                _ensure_space()
                c.drawString(left, y, ln)
                _newline(14)
                c.setFont("Helvetica", 11)
                continue

            # wrap normale
            for wline in wrapper.wrap(ln):
                _ensure_space()
                c.drawString(left, y, wline)
                _newline(13)

            _newline(2)

    # Firma (sempre)
    if y < bottom + 60:
        c.showPage()
        try:
            variant = "with_cirillo" if include_header else "no_cirillo"
            bg = _find_bg_image("a4", variant)
            _draw_bg_image_fullpage(c, width, height, bg)
        except Exception:
            pass
        _reset_y_for_new_page()

    y_sig = bottom + 40
    c.line(right - 120, y_sig, right, y_sig)
    c.setFont("Helvetica", 10)
    c.drawString(right - 115, y_sig + 5, "Firma / Timbro")

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.getvalue()


# -----------------------------
# Privacy PDF + Storico Consensi
# -----------------------------

def _now_iso_dt() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def _bool_i(v) -> int:
    try:
        return 1 if bool(v) else 0
    except Exception:
        return 0

def insert_privacy_consent(cur, paziente_id: int, payload: dict):
    """Inserisce un record in Consensi_Privacy. Payload usa chiavi python-friendly."""
    cur.execute(
        """
        INSERT INTO Consensi_Privacy
        (Paziente_ID, Data_Ora, Tipo, Tutore_Nome, Tutore_CF, Tutore_Telefono, Tutore_Email,
         Consenso_Trattamento, Consenso_Comunicazioni, Consenso_Marketing,
         Canale_Email, Canale_SMS, Canale_WhatsApp, Usa_Klaviyo,
         Firma_Blob, Firma_Filename, Firma_URL, Firma_Source, Note)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            paziente_id,
            payload.get("Data_Ora") or _now_iso_dt(),
            payload.get("Tipo") or "",
            payload.get("Tutore_Nome") or "",
            payload.get("Tutore_CF") or "",
            payload.get("Tutore_Telefono") or "",
            payload.get("Tutore_Email") or "",
            _bool_i(payload.get("Consenso_Trattamento")),
            _bool_i(payload.get("Consenso_Comunicazioni")),
            _bool_i(payload.get("Consenso_Marketing")),
            _bool_i(payload.get("Canale_Email")),
            _bool_i(payload.get("Canale_SMS")),
            _bool_i(payload.get("Canale_WhatsApp")),
            _bool_i(payload.get("Usa_Klaviyo")),
            payload.get("Firma_Blob"),
            payload.get("Firma_Filename") or "",
            payload.get("Firma_URL") or "",
            payload.get("Firma_Source") or "",
            payload.get("Note") or "",
        ),
    )

def fetch_privacy_consents(cur, paziente_id: int):
    cur.execute(
        """SELECT * FROM Consensi_Privacy WHERE Paziente_ID = ? ORDER BY Data_Ora DESC, ID DESC""",
        (paziente_id,),
    )
    return cur.fetchall()


# -----------------------------
# Google Forms (firma remota) + Google Sheets import
# -----------------------------
# I link sotto sono stati ricavati dai tuoi form precompilati (entry.xxx).
# Per usare l'import dallo Sheet ESISTENTE, pubblica il foglio delle risposte come CSV e metti l'URL in Secrets:
#   PRIVACY_SHEET_ADULTO_CSV_URL = "https://docs.google.com/spreadsheets/d/e/.../pub?output=csv"
#   PRIVACY_SHEET_MINORE_CSV_URL = "https://docs.google.com/spreadsheets/d/e/.../pub?output=csv"
#
# Nota sulla firma in Google Forms:
# - Google Forms NON supporta firma grafometrica "disegna qui" in modo nativo.
# - La soluzione pratica è una domanda "Caricamento file" (immagine della firma) oppure usare la firma su canvas nel gestionale.

FORM_MINORE_BASE = "https://docs.google.com/forms/d/e/1FAIpQLSezx9Xk05ok_EYhSJ1OnMAatSJHxLxST2e8-G_SI4Ad_X1_kg/viewform?usp=pp_url"
FORM_ADULTO_BASE = "https://docs.google.com/forms/d/e/1FAIpQLSe_GV962CPAw2osILAbQNqkivCHGSWES1VAdcJw3-f-LeCxbQ/viewform?usp=pp_url"

# Mappatura campi -> entry id (dal link che mi hai fornito)
FORM_MINORE_ENTRY = {
    "nome_cognome": "entry.324079259",
    "comune": "entry.1522430793",
    "data_nascita_iso": "entry.91400366",
    "tutore_nome": "entry.1194585802",
    "codice_fiscale": "entry.947551290",
    "email": "entry.295917843",
    "motivo": "entry.1792109233",
}

FORM_ADULTO_ENTRY = {
    "nome": "entry.1752970381",
    "codice_fiscale": "entry.648905519",
    "email": "entry.2080611620",
    "motivo": "entry.1529138592",
}

def _urlencode_params(params: dict) -> str:
    # Mantiene spazi come + (compatibile Forms)
    return urllib.parse.urlencode({k: (v or "") for k, v in params.items()}, doseq=True)

def build_google_form_url_adulto(paziente: dict, motivo: str = "") -> str:
    nome = f"{(paziente.get('Nome','') or '').strip()} {(paziente.get('Cognome','') or '').strip()}".strip()
    cf = (paziente.get("Codice_Fiscale") or "").strip().upper()
    email = (paziente.get("Email") or "").strip()
    params = {
        FORM_ADULTO_ENTRY["nome"]: nome,
        FORM_ADULTO_ENTRY["codice_fiscale"]: cf,
        FORM_ADULTO_ENTRY["email"]: email,
        FORM_ADULTO_ENTRY["motivo"]: motivo,
    }
    return FORM_ADULTO_BASE + "&" + _urlencode_params(params)

def build_google_form_url_minore(paziente: dict, motivo: str = "", tutore_fallback: dict | None = None) -> str:
    nome = f"{(paziente.get('Nome','') or '').strip()} {(paziente.get('Cognome','') or '').strip()}".strip()
    comune = (paziente.get("Citta") or paziente.get("Città") or "").strip()
    # data nascita attesa in ISO yyyy-mm-dd nel form (dal tuo esempio)
    dn_iso = (paziente.get("Data_Nascita") or "").strip()
    cf = (paziente.get("Codice_Fiscale") or "").strip().upper()
    email = (paziente.get("Email") or "").strip()

    # Se hai già un consenso MINORE salvato, puoi usare i dati tutore da lì.
    tutore_nome = (tutore_fallback or {}).get("Tutore_Nome","") if tutore_fallback else ""
    if not tutore_nome:
        tutore_nome = (tutore_fallback or {}).get("tutore_nome","") if tutore_fallback else ""

    params = {
        FORM_MINORE_ENTRY["nome_cognome"]: nome,
        FORM_MINORE_ENTRY["comune"]: comune,
        FORM_MINORE_ENTRY["data_nascita_iso"]: dn_iso,
        FORM_MINORE_ENTRY["tutore_nome"]: tutore_nome,
        FORM_MINORE_ENTRY["codice_fiscale"]: cf,
        FORM_MINORE_ENTRY["email"]: email,
        FORM_MINORE_ENTRY["motivo"]: motivo,
    }
    return FORM_MINORE_BASE + "&" + _urlencode_params(params)

def _read_csv_url(url: str):
    try:
        import pandas as pd
        return pd.read_csv(url)
    except Exception:
        return None

def import_privacy_from_sheet_csv(cur, paziente: dict, tipo: str) -> int | None:
    """Importa l'ultima risposta dallo Sheet (pubblicato CSV) e la registra in Consensi_Privacy.
    Ritorna l'ID inserito (se disponibile) o None se non trova match.

    Match per Codice Fiscale (preferito) oppure Email.
    """
    sec = _safe_secrets()
    url_key = "PRIVACY_SHEET_MINORE_CSV_URL" if tipo.upper().startswith("M") else "PRIVACY_SHEET_ADULTO_CSV_URL"
    csv_url = (sec.get(url_key) or "").strip()
    if not csv_url:
        return None

    df = _read_csv_url(csv_url)
    if df is None or df.empty:
        return None

    cf = (paziente.get("Codice_Fiscale") or "").strip().upper()
    email = (paziente.get("Email") or "").strip().lower()

    # Normalizza nomi colonne
    cols = {c.lower(): c for c in df.columns}
    # prova colonne comuni
    def col(*names):
        for n in names:
            if n.lower() in cols:
                return cols[n.lower()]
        return None

    col_cf = col("codice fiscale", "cf", "codice_fiscale")
    col_mail = col("email", "e-mail")
    col_ts = col("timestamp", "data/ora", "data ora", "submitted at", "submission time")

    # filtro match
    dff = df
    if col_cf and cf:
        dff = dff[dff[col_cf].astype(str).str.upper().str.strip() == cf]
    elif col_mail and email:
        dff = dff[dff[col_mail].astype(str).str.lower().str.strip() == email]
    else:
        return None

    if dff.empty:
        return None

    # ordina per timestamp se presente
    if col_ts:
        try:
            dff = dff.sort_values(col_ts, ascending=False)
        except Exception:
            pass

    row = dff.iloc[0].to_dict()

    # prova ad estrarre consensi (se presenti nel form); fallback: solo trattamento=1
    def _yn(v):
        s = str(v).strip().lower()
        return 1 if s in ("si","sì","yes","true","1","x","checked") else 0

    # prova colonne possibili
    c_tratt = None
    for n in ("consenso trattamento", "consenso al trattamento", "trattamento dati"):
        c_tratt = col(n)
        if c_tratt: break
    c_mark = None
    for n in ("marketing", "consenso marketing", "offerte", "promozioni"):
        c_mark = col(n)
        if c_mark: break
    c_serv = None
    for n in ("comunicazioni", "comunicazioni di servizio", "promemoria"):
        c_serv = col(n)
        if c_serv: break

    consenso_tratt = _yn(row.get(c_tratt)) if c_tratt else 1
    consenso_mark = _yn(row.get(c_mark)) if c_mark else 0
    consenso_serv = _yn(row.get(c_serv)) if c_serv else 1

    # firma: se nel form c'è "Caricamento file", nel foglio appare spesso come link o nome file.
    firma_url = ""
    for c in df.columns:
        cl = str(c).strip().lower()
        if any(k in cl for k in ("firma", "caric", "upload")):
            v = str(row.get(c) or "").strip()
            if v:
                firma_url = v
                break

    # Klaviyo: lo abilitiamo solo se marketing=1 e firma/consenso presente
    usa_klaviyo = 1 if (consenso_mark == 1) else 0

    paz_id = int(paziente.get("ID") or 0)
    now_iso = datetime.now().isoformat(timespec="seconds")
    tipo_db = "MINORE" if tipo.upper().startswith("M") else "ADULTO"

    # campi tutore: se presenti nel form, prova a leggerli; altrimenti lascia vuoti
    t_nome = ""
    t_cf = ""
    t_tel = ""
    t_mail = ""
    if tipo_db == "MINORE":
        c_tn = col("nome e cognome tutore", "tutore", "genitore/tutore")
        c_tcf = col("codice fiscale tutore", "cf tutore")
        c_ttel = col("telefono tutore", "tel tutore")
        c_tmail = col("email tutore", "mail tutore")
        t_nome = str(row.get(c_tn) or "").strip() if c_tn else ""
        t_cf = str(row.get(c_tcf) or "").strip().upper() if c_tcf else ""
        t_tel = str(row.get(c_ttel) or "").strip() if c_ttel else ""
        t_mail = str(row.get(c_tmail) or "").strip() if c_tmail else ""

    note = "Fonte: Google Form/Sheet; Firma URL: " + (firma_url or "")

    cur.execute(
        """
        INSERT INTO Consensi_Privacy
        (Paziente_ID, Data_Ora, Tipo, Tutore_Nome, Tutore_CF, Tutore_Telefono, Tutore_Email,
         Consenso_Trattamento, Consenso_Comunicazioni, Consenso_Marketing,
         Canale_Email, Canale_SMS, Canale_WhatsApp, Usa_Klaviyo,
         Firma_Blob, Firma_Filename, Firma_URL, Firma_Source, Note)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            paz_id,
            row.get(col_ts) or now_iso,
            tipo_db,
            t_nome, t_cf, t_tel, t_mail,
            consenso_tratt,
            consenso_serv,
            consenso_mark,
            1, 0, 0,
            usa_klaviyo,
            None,
            "",
            firma_url,
            "google_form",
            note,
        ),
    )
    try:
        return int(getattr(cur, "lastrowid", None) or 0) or None
    except Exception:
        return None



def _extract_firma_url(consenso: dict) -> str:
    """Estrae l'eventuale URL/valore firma salvato in Note.
    Formato atteso: '... Firma URL: <valore>' (salvato dall'import Google Sheet)."""
    try:
        note = str(consenso.get("Note") or "")
    except Exception:
        return ""
    if "Firma URL:" not in note:
        return ""
    try:
        return note.split("Firma URL:", 1)[1].strip()
    except Exception:
        return ""

def _is_firmato(consenso: dict) -> bool:
    return bool(_extract_firma_url(consenso))

def _draw_checkbox(c, x, y, checked: bool, label: str):
    box = 4 * mm
    c.rect(x, y - box + 1, box, box, stroke=1, fill=0)
    if checked:
        c.setFont("Helvetica-Bold", 10)
        c.drawString(x + 0.8*mm, y - box + 1.2*mm, "X")
    c.setFont("Helvetica", 10)
    c.drawString(x + box + 2*mm, y - box + 1.2*mm, label)

def genera_privacy_pdf(paziente: dict, consenso: dict, include_header: bool = True) -> bytes:
    """PDF privacy adulti/minori firmabile con spazi Firma + Timbro.
    NOTE: testo base (da personalizzare se vuoi una versione legale 'chiusa')."""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # background letterhead (A4)
    try:
        variant = "with_cirillo" if include_header else "no_cirillo"
        bg = _find_bg_image('a4', variant)
        _draw_bg_image_fullpage(c, width, height, bg)
    except Exception:
        pass

    left = 22 * mm
    right = width - 22 * mm
    top = height - (55 * mm if include_header else 35 * mm)
    bottom = 20 * mm
    y = top

    def nl(h=12):
        nonlocal y
        y -= h

    def ensure(min_y=bottom + 55):
        nonlocal y
        if y < min_y:
            c.showPage()
            # su pagine successive NON ripetiamo il background per non 'sporcare' la firma
            y = height - 25*mm

    tipo = (consenso.get("Tipo") or "").upper()  # ADULTO / MINORE
    data_ora = _safe_str(consenso.get("Data_Ora"))
    data_str = data_ora.split(" ")[0] if data_ora else datetime.now().strftime("%Y-%m-%d")
    data_it = _format_data_it_from_iso(data_str) if data_str else datetime.now().strftime("%d/%m/%Y")

    nome_paz = f"{_safe_str(paziente.get('Cognome'))} {_safe_str(paziente.get('Nome'))}".strip()
    dn = _format_data_it_from_iso(paziente.get("Data_Nascita"))

    c.setFont("Helvetica-Bold", 12)
    c.drawString(left, y, "INFORMATIVA PRIVACY E CONSENSO AL TRATTAMENTO DEI DATI (GDPR)")
    nl(16)

    c.setFont("Helvetica", 10.5)
    c.drawString(left, y, f"Paziente: {nome_paz}")
    nl(12)
    if dn:
        c.drawString(left, y, f"Data di nascita: {dn}")
        nl(12)
    c.drawString(left, y, f"Data: {data_it}   |   Luogo: Pagani (SA)")
    nl(16)
    # Se presente, riporta riferimento a firma digitale (Google Form / upload firma)
    firma_val = _extract_firma_url(consenso)
    if firma_val:
        c.setFont("Helvetica-Bold", 10.5)
        c.drawString(left, y, "Firma digitale acquisita (Google Form):")
        nl(12)
        c.setFont("Helvetica", 9.5)
        # spezza su più righe se lungo
        maxw = 95
        s = str(firma_val)
        for i in range(0, len(s), maxw):
            ensure()
            c.drawString(left, y, s[i:i+maxw])
            nl(11)
        nl(6)


    if tipo == "MINORE":
        c.setFont("Helvetica-Bold", 11)
        c.drawString(left, y, "Dati del genitore/tutore legale")
        nl(14)
        c.setFont("Helvetica", 10.5)
        c.drawString(left, y, f"Nome e Cognome: {_safe_str(consenso.get('Tutore_Nome'))}")
        nl(12)
        cf_t = _safe_str(consenso.get("Tutore_CF"))
        if cf_t:
            c.drawString(left, y, f"Codice Fiscale: {cf_t}")
            nl(12)
        tel_t = _safe_str(consenso.get("Tutore_Telefono"))
        em_t = _safe_str(consenso.get("Tutore_Email"))
        if tel_t:
            c.drawString(left, y, f"Telefono: {tel_t}")
            nl(12)
        if em_t:
            c.drawString(left, y, f"Email: {em_t}")
            nl(14)

    # Testo informativa (breve ma completa per uso studio; se vuoi la 'versione lunga' la mettiamo)
    c.setFont("Helvetica", 10)
    testo = (
        "Titolare del trattamento: Studio The Organism. Finalità: gestione clinica/assistenziale, " 
        "amministrativa e organizzativa delle prestazioni; adempimenti di legge. Base giuridica: " 
        "consenso (ove richiesto) e/o esecuzione del rapporto di cura/servizio. Conservazione: " 
        "per il tempo necessario alle finalità e secondo obblighi di legge. Diritti: accesso, " 
        "rettifica, cancellazione nei limiti di legge, limitazione, opposizione, portabilità; " 
        "reclamo al Garante Privacy. I dati possono essere comunicati a fornitori/Responsabili esterni " 
        "per servizi tecnici/gestionali (es. hosting, email, backup).\n\n"
        "Marketing (facoltativo): se autorizzato, i contatti possono essere gestiti tramite Klaviyo " 
        "(piattaforma email/SMS marketing) per invio di comunicazioni promozionali e contenuti informativi. " 
        "Il consenso marketing è revocabile in qualsiasi momento."
    )
    wrapper = textwrap.TextWrapper(width=105)
    for line in wrapper.wrap(testo):
        ensure()
        c.drawString(left, y, line)
        nl(12)
    nl(8)

    # Consensi (checkbox)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(left, y, "Consensi")
    nl(12)

    def g(k):
        v = consenso.get(k)
        try:
            return bool(int(v))
        except Exception:
            return bool(v)

    _draw_checkbox(c, left, y, g("Consenso_Trattamento"), "Consenso al trattamento dati per finalità cliniche/gestionali (obbligatorio)")
    nl(12)
    _draw_checkbox(c, left, y, g("Consenso_Comunicazioni"), "Consenso a comunicazioni di servizio (appuntamenti, referti, promemoria)")
    nl(12)
    _draw_checkbox(c, left, y, g("Consenso_Marketing"), "Consenso a comunicazioni promozionali/offerte (facoltativo)")
    nl(14)

    c.setFont("Helvetica-Bold", 11)
    c.drawString(left, y, "Canali autorizzati")
    nl(12)
    _draw_checkbox(c, left, y, g("Canale_Email"), "Email")
    nl(12)
    _draw_checkbox(c, left, y, g("Canale_SMS"), "SMS")
    nl(12)
    _draw_checkbox(c, left, y, g("Canale_WhatsApp"), "WhatsApp")
    nl(14)

    _draw_checkbox(c, left, y, g("Usa_Klaviyo"), "Autorizzo l'uso di Klaviyo per newsletter/SMS marketing (solo se marketing attivo)")
    nl(16)

    note = _safe_str(consenso.get("Note"))
    if note:
        c.setFont("Helvetica-Bold", 10.5)
        c.drawString(left, y, "Note:")
        nl(12)
        c.setFont("Helvetica", 10)
        for line in textwrap.TextWrapper(width=105).wrap(note.replace("\n", " ")):
            ensure()
            c.drawString(left, y, line)
            nl(12)
        nl(8)

    # Firme
    ensure(bottom + 80)
    y_sig = bottom + 55
    c.setFont("Helvetica", 10)

    # Linea firma paziente/tutore
    label_firma = "Firma Paziente" if tipo != "MINORE" else "Firma Genitore/Tutore"
    c.drawString(left, y_sig + 22, label_firma)
    c.line(left, y_sig + 18, left + 80*mm, y_sig + 18)

    # Linea firma professionista + timbro
    c.drawString(right - 95*mm, y_sig + 22, "Firma Professionista")
    c.line(right - 95*mm, y_sig + 18, right - 15*mm, y_sig + 18)

    c.setFont("Helvetica", 9)
    c.drawString(right - 40*mm, y_sig - 2, "Timbro")
    c.rect(right - 45*mm, y_sig - 22, 40*mm, 18*mm, stroke=1, fill=0)

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



def _draw_prescrizione_values_only_on_canvas(
    c,
    width: float,
    height: float,
    paziente,
    data_prescrizione_iso: Optional[str],
    # lontano/intermedio/vicino OD/OS
    sf_lon_od: float, cil_lon_od: float, ax_lon_od: int,
    sf_lon_os: float, cil_lon_os: float, ax_lon_os: int,
    sf_int_od: float, cil_int_od: float, ax_int_od: int,
    sf_int_os: float, cil_int_os: float, ax_int_os: int,
    sf_vic_od: float, cil_vic_od: float, ax_vic_od: int,
    sf_vic_os: float, cil_vic_os: float, ax_vic_os: int,
    lenti_scelte: list,
    altri_trattamenti: str,
    note: str,
):
    """Overlay SOLO VALORI: non disegna linee/archi/riquadri (quelli sono nel template)."""

    # Helper formatting
    def fmt_sphere_cyl(v):
        if v is None or v == "": 
            return ""
        try:
            v = float(v)
        except Exception:
            return str(v)
        # +0.00 / -0.50
        if abs(v) < 1e-9:
            v = 0.0
        return f"{v:+.2f}"

    def fmt_axis(v):
        if v is None or v == "": 
            return ""
        try:
            iv = int(float(v))
            return str(iv)
        except Exception:
            return str(v)

    # Font
    c.setFont("Helvetica", 10)

    # Data (linea 'Data')
    data_it = _format_data_it_from_iso(data_prescrizione_iso) if data_prescrizione_iso else ""
    if data_it:
        c.drawString(105 * mm, height - 30 * mm, data_it)

    # Paziente (linea 'Sig.')
    try:
        nome_paz = f"{paziente.get('Cognome','')} {paziente.get('Nome','')}".strip()
    except Exception:
        nome_paz = str(paziente)
    if nome_paz:
        c.setFont("Helvetica-Bold", 11)
        c.drawString(20 * mm, height - 45 * mm, nome_paz)
        c.setFont("Helvetica", 10)

    # Coordinate centri box (mm -> punti) calibrate sul tuo template A5
    # OD (sinistra)
    od_x_sf  = 45 * mm
    od_x_cil = 68 * mm
    od_x_ax  = 91 * mm

    # OS (destra)
    os_x_sf  = 96 * mm
    os_x_cil = 119 * mm
    os_x_ax  = 142 * mm

    # Y dei tre righi (Lontano / Intermedio / Vicino)
    y_lon = 104 * mm
    y_int = 85 * mm
    y_vic = 66 * mm

    def put_triplet(xsf, xcil, xax, y, sf, cil, ax):
        s = fmt_sphere_cyl(sf)
        c1 = fmt_sphere_cyl(cil)
        a1 = fmt_axis(ax)
        if s:
            c.drawCentredString(xsf, y, s)
        if c1:
            c.drawCentredString(xcil, y, c1)
        if a1:
            c.drawCentredString(xax, y, a1)

    # OD
    put_triplet(od_x_sf, od_x_cil, od_x_ax, y_lon, sf_lon_od, cil_lon_od, ax_lon_od)
    put_triplet(od_x_sf, od_x_cil, od_x_ax, y_int, sf_int_od, cil_int_od, ax_int_od)
    put_triplet(od_x_sf, od_x_cil, od_x_ax, y_vic, sf_vic_od, cil_vic_od, ax_vic_od)

    # OS
    put_triplet(os_x_sf, os_x_cil, os_x_ax, y_lon, sf_lon_os, cil_lon_os, ax_lon_os)
    put_triplet(os_x_sf, os_x_cil, os_x_ax, y_int, sf_int_os, cil_int_os, ax_int_os)
    put_triplet(os_x_sf, os_x_cil, os_x_ax, y_vic, sf_vic_os, cil_vic_os, ax_vic_os)

    # Checkboxes lenti consigliate (metti "X" a sinistra delle voci)
    checks = set([str(x).strip().lower() for x in (lenti_scelte or [])])

    # Colonna sinistra (progressive, vicino/intermedio, fotocromatiche, polarizzate)
    base_x = 23 * mm
    base_y = 48 * mm
    dy = 6 * mm
    left_labels = [
        ("progressive", 0),
        ("per vicino/intermedio", 1),
        ("fotocromatiche", 2),
        ("polarizzate", 3),
    ]
    c.setFont("Helvetica-Bold", 10)
    for lab, i in left_labels:
        if any(lab in s for s in checks):
            c.drawString(base_x, base_y - i * dy, "X")

    # Colonna destra (trattamento antiriflesso, altri trattamenti)
    right_x = 112 * mm
    right_y = 48 * mm
    if any("trattamento antiriflesso" in s for s in checks):
        c.drawString(right_x, right_y, "X")
    # altri trattamenti: c'è una checkbox e riga testo
    if (altri_trattamenti or "").strip():
        c.drawString(right_x, right_y - 6 * mm, "X")
        c.setFont("Helvetica", 9)
        c.drawString(112 * mm, 35 * mm, str(altri_trattamenti)[:60])

    # NOTE
    if (note or "").strip():
        c.setFont("Helvetica", 9)
        # area note in basso a sinistra
        c.drawString(15 * mm, 20 * mm, (str(note).replace("\n", " "))[:120])


def _draw_prescrizione_occhiali_a5_on_canvas(
    c,
    width: float,
    height: float,
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
):
    """Disegna la prescrizione (layout A5) sul canvas corrente, senza fare showPage/save."""
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
                break
            c.drawString(left + 5 * mm, y, line)
            y -= 11

    # Firma
    if y < bottom + 50:
        pass

        # Firma: se presente un'immagine (upload in gestionale) la inseriamo; altrimenti lasciamo la riga.
    c.line(right - 100, bottom + 30, right, bottom + 30)
    c.drawString(right - 95, bottom + 35, "Firma / Timbro")

    firma_bytes = _blob_to_bytes(consenso.get("Firma_Blob"))
    firma_url = _safe_str(consenso.get("Firma_URL"))
    if firma_bytes:
        try:
            img = ImageReader(io.BytesIO(firma_bytes))
            # riquadro firma: 100mm x 25mm circa
            c.drawImage(img, right - 100, bottom + 32, width=100, height=22, preserveAspectRatio=True, mask='auto')
        except Exception:
            pass
    elif firma_url:
        # se la firma arriva da Google Form (file upload), lasciamo il riferimento nel PDF
        c.setFont("Helvetica", 7)
        c.drawString(left, bottom + 15, "Firma digitale (Google Form): " + firma_url[:110])






def genera_prescrizione_occhiali_a4_pdf(
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
    con_cirillo: bool = True,
) -> bytes:
    """A4: sfondo intestazione (immagine) + prescrizione pulita + TABO con freccia asse cilindro."""
    dati = {
        "paziente": f"{paziente.get('Cognome','')} {paziente.get('Nome','')}".strip() if isinstance(paziente, dict) else _safe_str(paziente),
        "data": _safe_str(data_prescrizione_iso),
        "od_lon_sf": sf_lon_od, "od_lon_cil": cil_lon_od, "od_lon_ax": ax_lon_od,
        "os_lon_sf": sf_lon_os, "os_lon_cil": cil_lon_os, "os_lon_ax": ax_lon_os,
        "od_int_sf": sf_int_od, "od_int_cil": cil_int_od, "od_int_ax": ax_int_od,
        "os_int_sf": sf_int_os, "os_int_cil": cil_int_os, "os_int_ax": ax_int_os,
        "od_vic_sf": sf_vic_od, "od_vic_cil": cil_vic_od, "od_vic_ax": ax_vic_od,
        "os_vic_sf": sf_vic_os, "os_vic_cil": cil_vic_os, "os_vic_ax": ax_vic_os,
        "lenti": lenti_scelte,
        "altri_trattamenti": altri_trattamenti,
        "note": note,
    }
    return _prescrizione_pdf_imagebg(A4, "a4", con_cirillo, dati)

def genera_prescrizione_occhiali_a4_pdf(
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
    con_cirillo: bool = True,
) -> bytes:
    """
    A5: SFONDO = immagine letterhead (The Organism) + overlay SOLO valori (tabella pulita).
    Niente riquadri: zero accavallamenti.
    """
    dati = {
        "paziente": f"{paziente.get('Cognome','')} {paziente.get('Nome','')}".strip() if isinstance(paziente, dict) else _safe_str(paziente),
        "data": _safe_str(data_prescrizione_iso),
        "od_lon_sf": sf_lon_od, "od_lon_cil": cil_lon_od, "od_lon_ax": ax_lon_od,
        "os_lon_sf": sf_lon_os, "os_lon_cil": cil_lon_os, "os_lon_ax": ax_lon_os,
        "od_int_sf": sf_int_od, "od_int_cil": cil_int_od, "od_int_ax": ax_int_od,
        "os_int_sf": sf_int_os, "os_int_cil": cil_int_os, "os_int_ax": ax_int_os,
        "od_vic_sf": sf_vic_od, "od_vic_cil": cil_vic_od, "od_vic_ax": ax_vic_od,
        "os_vic_sf": sf_vic_os, "os_vic_cil": cil_vic_os, "os_vic_ax": ax_vic_os,
        "lenti": lenti_scelte,
        "altri_trattamenti": altri_trattamenti,
        "note": note,
    }
    return _prescrizione_pdf_imagebg(A5, "a5", con_cirillo, dati)

def _draw_crop_marks_for_rect(c, x0, y0, w, h, mark_len_mm: float = 4, inset_mm: float = 2):
    """Crop marks (segni di taglio) ai 4 angoli di un rettangolo."""
    L = mark_len_mm * mm
    inset = inset_mm * mm

    # Bottom-left
    c.line(x0 - L, y0 + inset, x0, y0 + inset)
    c.line(x0 + inset, y0 - L, x0 + inset, y0)

    # Bottom-right
    c.line(x0 + w, y0 + inset, x0 + w + L, y0 + inset)
    c.line(x0 + w - inset, y0 - L, x0 + w - inset, y0)

    # Top-left
    c.line(x0 - L, y0 + h - inset, x0, y0 + h - inset)
    c.line(x0 + inset, y0 + h, x0 + inset, y0 + h + L)

    # Top-right
    c.line(x0 + w, y0 + h - inset, x0 + w + L, y0 + h - inset)
    c.line(x0 + w - inset, y0 + h, x0 + w - inset, y0 + h + L)


def _draw_mid_cut_marks(c, page_w, page_h, mark_len_mm: float = 8):
    """Tacche centrali sui bordi sinistro e destro per taglio a metà pagina."""
    y = page_h / 2.0
    L = mark_len_mm * mm
    c.line(0, y, L, y)
    c.line(page_w - L, y, page_w, y)



def genera_prescrizione_occhiali_a4_pdf(
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
    divider_line: bool = False,
    con_cirillo: bool = True,
) -> bytes:
    """
    A4: SFONDO = immagine letterhead A4 (The Organism) + overlay SOLO valori (tabella pulita).
    Nota: il nome della funzione resta per compatibilità con la UI.
    """
    dati = {
        "paziente": f"{paziente.get('Cognome','')} {paziente.get('Nome','')}".strip() if isinstance(paziente, dict) else _safe_str(paziente),
        "data": _safe_str(data_prescrizione_iso),
        "od_lon_sf": sf_lon_od, "od_lon_cil": cil_lon_od, "od_lon_ax": ax_lon_od,
        "os_lon_sf": sf_lon_os, "os_lon_cil": cil_lon_os, "os_lon_ax": ax_lon_os,
        "od_int_sf": sf_int_od, "od_int_cil": cil_int_od, "od_int_ax": ax_int_od,
        "os_int_sf": sf_int_os, "os_int_cil": cil_int_os, "os_int_ax": ax_int_os,
        "od_vic_sf": sf_vic_od, "od_vic_cil": cil_vic_od, "od_vic_ax": ax_vic_od,
        "os_vic_sf": sf_vic_os, "os_vic_cil": cil_vic_os, "os_vic_ax": ax_vic_os,
        "lenti": lenti_scelte,
        "altri_trattamenti": altri_trattamenti,
        "note": note,
    }
    return _prescrizione_pdf_imagebg(A4, "a4", con_cirillo, dati)

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
    # Sfondo intestazione (immagine A4)
    try:
        variant = "with_cirillo" if with_header else "no_cirillo"
        bg = _find_bg_image('a4', variant)
        _draw_bg_image_fullpage(c, width, height, bg)
    except Exception:
        pass


    left = 25 * mm
    right = width - 25 * mm
    top = height - 40 * mm
    bottom = 25 * mm

    y = top
    # marker di debug: posizione inizio stampa
    c.saveState(); c.setFont('Helvetica', 7); c.drawString(left-8*mm, y+2, '1'); c.restoreState()

    # Intestazione opzionale
    if False and with_header:
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



# -----------------------------
# 🧹 Tool: Pulizia duplicati (solo TEST)
# -----------------------------

def _patient_child_tables():
    # tabelle che referenziano Pazienti(ID) via Paziente_ID
    return [
        ("Anamnesi", "Paziente_ID"),
        ("Valutazioni_Visive", "Paziente_ID"),
        ("Sedute", "Paziente_ID"),
        ("Coupons", "Paziente_ID"),
        ("Consensi_Privacy", "Paziente_ID"),
    ]


def _fetchall_dicts(cur, sql: str, params=()):
    cur.execute(sql, params)
    rows = cur.fetchall()
    out = []
    for r in rows:
        try:
            out.append(dict(r))
        except Exception:
            out.append({str(i): v for i, v in enumerate(r)})
    return out


def db_find_duplicate_cf(cur):
    # duplicati solo per CF non vuoto
    rows = _fetchall_dicts(
        cur,
        '''
        SELECT UPPER(TRIM(Codice_Fiscale)) AS CF, COUNT(*) AS N
        FROM Pazienti
        WHERE Codice_Fiscale IS NOT NULL AND TRIM(Codice_Fiscale) <> ''
        GROUP BY UPPER(TRIM(Codice_Fiscale))
        HAVING COUNT(*) > 1
        ORDER BY N DESC, CF
        ''',
        (),
    )
    groups = []
    for r in rows:
        cf = r.get("CF") or r.get("cf")
        det = _fetchall_dicts(
            cur,
            '''
            SELECT ID, Cognome, Nome, Data_Nascita, Email, Telefono, Stato_Paziente, Codice_Fiscale
            FROM Pazienti
            WHERE UPPER(TRIM(Codice_Fiscale)) = ?
            ORDER BY ID
            ''',
            (cf,),
        )
        groups.append({"key": cf, "kind": "CF", "rows": det})
    return groups


def db_find_duplicate_identity(cur):
    # duplicati per (Cognome, Nome, Data_Nascita) quando presenti
    rows = _fetchall_dicts(
        cur,
        '''
        SELECT
          UPPER(TRIM(Cognome)) AS COG,
          UPPER(TRIM(Nome)) AS NOM,
          COALESCE(TRIM(Data_Nascita),'') AS DN,
          COUNT(*) AS N
        FROM Pazienti
        WHERE TRIM(Cognome) <> '' AND TRIM(Nome) <> ''
        GROUP BY UPPER(TRIM(Cognome)), UPPER(TRIM(Nome)), COALESCE(TRIM(Data_Nascita),'')
        HAVING COUNT(*) > 1
        ORDER BY N DESC, COG, NOM, DN
        ''',
        (),
    )
    groups = []
    for r in rows:
        cog = r.get("COG") or r.get("cog")
        nom = r.get("NOM") or r.get("nom")
        dn = r.get("DN") or r.get("dn") or ""
        det = _fetchall_dicts(
            cur,
            '''
            SELECT ID, Cognome, Nome, Data_Nascita, Email, Telefono, Stato_Paziente, Codice_Fiscale
            FROM Pazienti
            WHERE UPPER(TRIM(Cognome)) = ?
              AND UPPER(TRIM(Nome)) = ?
              AND COALESCE(TRIM(Data_Nascita),'') = ?
            ORDER BY ID
            ''',
            (cog, nom, dn),
        )
        groups.append({"key": f"{cog} | {nom} | {dn or 'SENZA_DATA'}", "kind": "IDENTITA", "rows": det})
    return groups


def _count_refs(cur, paziente_id: int) -> dict:
    counts = {}
    for tbl, col in _patient_child_tables():
        try:
            cur.execute(f"SELECT COUNT(*) AS N FROM {tbl} WHERE {col} = ?", (paziente_id,))
            r = cur.fetchone()
            try:
                n = int(r["N"]) if isinstance(r, dict) else int(r[0])
            except Exception:
                n = int(r[0]) if r else 0
            counts[tbl] = n
        except Exception:
            counts[tbl] = 0
    return counts


def db_merge_patients(cur, master_id: int, dup_ids: list):
    """Sposta tutti i riferimenti (Paziente_ID) dai duplicati verso master_id e cancella i duplicati."""
    report = {"master": int(master_id), "moved": {}, "deleted": [], "errors": []}
    for dup_id in dup_ids:
        dup_id = int(dup_id)
        if dup_id == int(master_id):
            continue
        for tbl, col in _patient_child_tables():
            try:
                cur.execute(f"UPDATE {tbl} SET {col} = ? WHERE {col} = ?", (master_id, dup_id))
                moved = getattr(cur, "rowcount", None)
                report["moved"].setdefault(tbl, 0)
                if moved is not None and moved >= 0:
                    report["moved"][tbl] += int(moved)
            except Exception as e:
                report["errors"].append(f"{tbl}: {e}")
        try:
            cur.execute("DELETE FROM Pazienti WHERE ID = ?", (dup_id,))
            report["deleted"].append(dup_id)
        except Exception as e:
            report["errors"].append(f"DELETE Pazienti({dup_id}): {e}")
    return report


def db_keep_latest_privacy_consent(cur, paziente_id: int):
    """Mantiene SOLO l'ultimo consenso privacy del paziente (per Data_Ora/ID) ed elimina i precedenti."""
    cur.execute(
        "SELECT ID, Data_Ora FROM Consensi_Privacy WHERE Paziente_ID=? ORDER BY COALESCE(Data_Ora,'') DESC, ID DESC",
        (paziente_id,),
    )
    rows = cur.fetchall() or []
    if not rows:
        return {"kept": None, "deleted": 0}

    keep_id = rows[0]["ID"]
    deleted = 0
    if len(rows) > 1:
        cur.execute(
            "DELETE FROM Consensi_Privacy WHERE Paziente_ID=? AND ID<>?",
            (paziente_id, keep_id),
        )
        deleted = len(rows) - 1
    return {"kept": keep_id, "deleted": deleted}


def db_compact_all_privacy_consents(cur):
    """Per ogni paziente, mantiene SOLO l'ultimo consenso privacy."""
    cur.execute("SELECT DISTINCT Paziente_ID FROM Consensi_Privacy")
    pids = [r["Paziente_ID"] for r in (cur.fetchall() or [])]
    total_deleted = 0
    total_patients = 0
    for pid in pids:
        rep = db_keep_latest_privacy_consent(cur, int(pid))
        total_deleted += int(rep.get("deleted", 0))
        total_patients += 1
    return {"patients": total_patients, "deleted": total_deleted}



def ui_db_cleanup():
    st.header("🧹 Pulizia DB (solo TEST)")
    st.warning("Usa questa sezione SOLO in APP_MODE=test (DB TEST).")

    conn = get_connection()
    cur = conn.cursor()

    tab1, tab2 = st.tabs(["Duplicati per Codice Fiscale", "Duplicati per Identità (nome/cognome/data)"])

    with st.expander("🧾 Compatta consensi privacy (tieni solo l'ultimo)", expanded=False):
        st.write("Elimina i consensi privacy precedenti e lascia SOLO l'ultimo per ogni paziente (DB TEST).")
        conf = st.text_input("Per confermare scrivi: COMPACT", key="compact_confirm")
        if st.button("Esegui compattazione consensi (tutti i pazienti)", disabled=(conf.strip().upper() != "COMPACT")):
            try:
                repc = db_compact_all_privacy_consents(cur)
                conn.commit()
                st.success(f"Compattazione completata: pazienti analizzati={repc['patients']}, consensi eliminati={repc['deleted']}.")
            except Exception as e:
                try:
                    conn.rollback()
                except Exception:
                    pass
                st.error(f"Errore compattazione: {e}")


    def _render(groups, key_prefix: str):
        if not groups:
            st.success("Nessun duplicato trovato 🎉")
            return

        keys = [f"{g['kind']}: {g['key']} ({len(g['rows'])} record)" for g in groups]
        sel = st.selectbox("Seleziona un gruppo da analizzare", keys, key=f"{key_prefix}_grp")
        g = groups[keys.index(sel)]
        rows = g["rows"]

        st.markdown("### Record nel gruppo")
        for r in rows:
            pid = int(r.get("ID") or r.get("id") or 0)
            st.write(
                f"**ID {pid}** — {r.get('Cognome','')} {r.get('Nome','')} | DN: {r.get('Data_Nascita','') or ''} | CF: {r.get('Codice_Fiscale','') or ''} | Email: {r.get('Email','') or ''}"
            )
            counts = _count_refs(cur, pid)
            st.caption("Riferimenti: " + ", ".join([f"{k}={v}" for k, v in counts.items()]))

        ids = [int(r.get("ID") or r.get("id")) for r in rows]
        master_id = st.selectbox("Scegli il record MASTER (quello da tenere)", ids, key=f"{key_prefix}_master")
        dup_ids = [i for i in ids if i != master_id]

        st.info(f"Sposterò i riferimenti da {dup_ids} verso MASTER {master_id}, poi eliminerò i duplicati.")

        confirm = st.text_input("Per confermare scrivi: MERGE", key=f"{key_prefix}_confirm")
        if st.button("Esegui MERGE", type="primary", key=f"{key_prefix}_go", disabled=(confirm.strip().upper() != "MERGE")):
            try:
                rep = db_merge_patients(cur, master_id=master_id, dup_ids=dup_ids)
                conn.commit()
                st.success(f"Merge completato. Master: {master_id}. Eliminati: {rep['deleted']}")
                # Dopo merge: mantieni SOLO l'ultimo consenso privacy (come richiesto)
                try:
                    rep2 = db_keep_latest_privacy_consent(cur, paziente_id=master_id)
                    conn.commit()
                    st.info(f"Consensi_Privacy: tenuto ID {rep2.get('kept')} — eliminati {rep2.get('deleted')} consensi precedenti.")
                except Exception as e:
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                    st.warning(f"Merge ok, ma non sono riuscito a compattare i consensi privacy: {e}")
                if rep["moved"]:
                    st.write("Spostamenti:", rep["moved"])
                if rep["errors"]:
                    st.error("Alcuni errori:")
                    for e in rep["errors"]:
                        st.write(e)
            except Exception as e:
                try:
                    conn.rollback()
                except Exception:
                    pass
                st.error(f"Merge fallito: {e}")

    with tab1:
        _render(db_find_duplicate_cf(cur), "cf")

    with tab2:
        _render(db_find_duplicate_identity(cur), "id")

    conn.close()


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


        st.markdown("### Privacy e Consensi (GDPR)")
        st.caption("I consensi vengono registrati nel gestionale. Le opzioni marketing fanno riferimento a Klaviyo (piattaforma e-mail/SMS marketing) per l'invio di comunicazioni e offerte, solo se autorizzato.")

        tipo_privacy = st.radio("Tipo di privacy", ["Adulto", "Minore"], horizontal=True)

        tutore_nome = tutore_cf = tutore_tel = tutore_email = ""
        if tipo_privacy == "Minore":
            st.markdown("**Dati del genitore/tutore**")
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                tutore_nome = st.text_input("Nome e cognome tutore", "")
                tutore_tel = st.text_input("Telefono tutore", "")
            with col_t2:
                tutore_cf = st.text_input("Codice fiscale tutore", "").upper()
                tutore_email = st.text_input("Email tutore", "")

        st.markdown("**Consensi**")
        consenso_trattamento = st.checkbox("✅ Consenso al trattamento dei dati personali per finalità cliniche/gestionali (obbligatorio)", value=False)
        consenso_comunicazioni = st.checkbox("Consenso a comunicazioni di servizio (appuntamenti, referti, promemoria)", value=True)

        st.markdown("**Canali di comunicazione autorizzati**")
        col_c1, col_c2, col_c3 = st.columns(3)
        with col_c1:
            canale_email = st.checkbox("Email", value=True)
        with col_c2:
            canale_sms = st.checkbox("SMS", value=False)
        with col_c3:
            canale_whatsapp = st.checkbox("WhatsApp", value=True)

        st.markdown("**Marketing / offerte (facoltativo)**")
        consenso_marketing = st.checkbox("Consenso a ricevere comunicazioni promozionali, offerte e contenuti informativi", value=False)
        usa_klaviyo = st.checkbox("Autorizzo l'uso di Klaviyo per la gestione di newsletter/SMS marketing (solo se marketing attivo)", value=False)

        note_privacy = st.text_area("Note privacy (facoltative)", "")

        salva = st.form_submit_button("Salva paziente")

    # --- Salvataggio nuovo paziente ---
    
    # --- Salvataggio nuovo paziente ---
    if salva:
        if not cognome or not nome:
            st.error("Cognome e Nome sono obbligatori.")
            conn.close()
            return

        if not consenso_trattamento:
            st.error("Per salvare il paziente devi acquisire il consenso al trattamento dati (obbligatorio).")
            conn.close()
            return

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

        # Inserimento paziente + recupero ID
        paz_id = None
        try:
            if _DB_BACKEND == "postgres":
                cur.execute(
                    """
                    INSERT INTO Pazienti
                    (Cognome, Nome, Data_Nascita, Sesso, Telefono, Email,
                     Indirizzo, CAP, Citta, Provincia, Codice_Fiscale, Stato_Paziente)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                    RETURNING ID
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
                row = cur.fetchone()
                # RowCI wrapper supports ["ID"] and ["id"]
                paz_id = int(row["ID"]) if isinstance(row, dict) else int(row[0])
            else:
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
                try:
                    paz_id = int(getattr(cur, "lastrowid", None) or 0) or None
                except Exception:
                    paz_id = None

            now_iso = datetime.now().isoformat(timespec="seconds")
            tipo_db = "MINORE" if (tipo_privacy == "Minore") else "ADULTO"
            cur.execute(
                """
                INSERT INTO Consensi_Privacy
                (Paziente_ID, Data_Ora, Tipo, Tutore_Nome, Tutore_CF, Tutore_Telefono, Tutore_Email,
                 Consenso_Trattamento, Consenso_Comunicazioni, Consenso_Marketing,
                 Canale_Email, Canale_SMS, Canale_WhatsApp, Usa_Klaviyo, Note)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    paz_id,
                    now_iso,
                    tipo_db,
                    (tutore_nome or "").strip(),
                    (tutore_cf or "").strip().upper(),
                    (tutore_tel or "").strip(),
                    (tutore_email or "").strip(),
                    1 if consenso_trattamento else 0,
                    1 if consenso_comunicazioni else 0,
                    1 if consenso_marketing else 0,
                    1 if canale_email else 0,
                    1 if canale_sms else 0,
                    1 if canale_whatsapp else 0,
                    1 if (usa_klaviyo and consenso_marketing) else 0,
                    (note_privacy or "").strip(),
                ),
            )

            conn.commit()
            st.success("Paziente salvato correttamente (privacy registrata).")

        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass
            st.error("Errore durante il salvataggio del paziente/privacy.")
            st.write(str(e))

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

    selected = st.selectbox("Seleziona un paziente per modificare / archiviare", options, key="pz_sel_mod")
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
            cognome_m = st.text_input("Cognome", rec["Cognome"] or "", key=f"m_cognome_{sel_id}")
            data_nascita_m = st.text_input(
                "Data di nascita (gg/mm/aaaa)",
                datetime.strptime(rec["Data_Nascita"], "%Y-%m-%d").strftime("%d/%m/%Y")
                if rec["Data_Nascita"] else "",
                key=f"m_data_nascita_{sel_id}",
            )
        with col2:
            nome_m = st.text_input("Nome", rec["Nome"] or "", key=f"m_nome_{sel_id}")
            sesso_m = st.selectbox(
                "Sesso",
                ["", "M", "F", "Altro"],
                index=(["", "M", "F", "Altro"].index(rec["Sesso"]) if rec["Sesso"] in ["", "M", "F", "Altro"] else 0),
                key=f"m_sesso_{sel_id}",
            )

        col3, col4, col5 = st.columns(3)
        with col3:
            indirizzo_m = st.text_input("Indirizzo", rec["Indirizzo"] or "", key=f"m_indirizzo_{sel_id}")
        with col4:
            cap_m = st.text_input("CAP", rec["CAP"] or "", key=f"m_cap_{sel_id}")
        with col5:
            provincia_m = st.text_input("Provincia", rec["Provincia"] or "", key=f"m_provincia_{sel_id}")

        col6, col7 = st.columns(2)
        with col6:
            citta_m = st.text_input("Città", rec["Citta"] or "", key=f"m_citta_{sel_id}")
        with col7:
            cf_m = st.text_input("Codice fiscale", (rec["Codice_Fiscale"] or "").upper(), key=f"m_cf_{sel_id}")

        col8, col9 = st.columns(2)
        with col8:
            telefono_m = st.text_input("Telefono", rec["Telefono"] or "", key=f"m_tel_{sel_id}")
        with col9:
            email_m = st.text_input("Email", rec["Email"] or "", key=f"m_email_{sel_id}")

        stato_m = st.selectbox(
            "Stato paziente",
            ["ATTIVO", "ARCHIVIATO"],
            index=(0 if (rec["Stato_Paziente"] or "ATTIVO") == "ATTIVO" else 1),
            key=f"m_stato_{sel_id}",
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


        st.markdown("### Esame obiettivo (strutture oculari)")
        cornea = st.text_area("Cornea", "")
        camera_ant = st.text_area("Camera anteriore", "")
        cristallino = st.text_area("Cristallino", "")
        congiuntiva = st.text_area("Congiuntiva / Sclera", "")
        iride_pupilla = st.text_area("Iride / Pupilla", "")
        vitreo = st.text_area("Vitreo", "")


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


ESAME OBIETTIVO (STRUTTURE OCULARI)
- Cornea: {cornea}
- Camera anteriore: {camera_ant}
- Cristallino: {cristallino}
- Congiuntiva / Sclera: {congiuntiva}
- Iride / Pupilla: {iride_pupilla}
- Vitreo: {vitreo}

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
             Cornea, Camera_Anteriore, Cristallino, Congiuntiva_Sclera, Iride_Pupilla, Vitreo,
             Costo, Pagato, Note)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
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
                cornea,
                camera_ant,
                cristallino,
                congiuntiva,
                iride_pupilla,
                vitreo,
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

    # 
    # -------- Privacy & Consensi (storico + stampa PDF) --------
    st.markdown("---")
    st.subheader("Privacy e Consensi (storico)")

    cons_rows = fetch_privacy_consents(cur, paz_id)
    if not cons_rows:
        st.info("Nessun consenso privacy registrato per questo paziente.")
    else:
        # tabella compatta
        def _yesno(v):
            try:
                return "SI" if int(v) == 1 else "NO"
            except Exception:
                return "SI" if v else "NO"

        preview = []
        for r in cons_rows:
            preview.append({
                "ID": r["ID"],
                "Data/Ora": r.get("Data_Ora",""),
                "Tipo": r.get("Tipo",""),
                "Firmato": "✅" if _is_firmato(r) else "—",
                "Trattamento": _yesno(r.get("Consenso_Trattamento")),
                "Servizio": _yesno(r.get("Consenso_Comunicazioni")),
                "Marketing": _yesno(r.get("Consenso_Marketing")),
                "Klaviyo": _yesno(r.get("Usa_Klaviyo")),
                "Email": _yesno(r.get("Canale_Email")),
                "SMS": _yesno(r.get("Canale_SMS")),
                "WhatsApp": _yesno(r.get("Canale_WhatsApp")),
            })
        st.dataframe(preview, use_container_width=True, hide_index=True)

        ids = [str(r["ID"]) for r in cons_rows]
        sel_cons_id = st.selectbox("Seleziona un consenso per stampare il PDF", ids, key="sel_privacy_id")
        cons_rec = next(r for r in cons_rows if str(r["ID"]) == str(sel_cons_id))

        # Badge firma digitale (se presente URL firma importato da Google Sheet)
        firma_val = _extract_firma_url(cons_rec)
        if firma_val:
            st.success("✅ Consenso firmato (firma acquisita via Google Form).")
            st.caption(f"Firma (valore/link): {firma_val}")
        else:
            st.info("ℹ️ Nessuna firma digitale registrata per questo consenso (se usi Google Form, assicurati che nel form ci sia un campo 'Caricamento file' per la firma e che lo Sheet lo riporti).")


        colp1, colp2 = st.columns(2)
        with colp1:
            pdf_priv_int = genera_privacy_pdf(paziente, cons_rec, include_header=True)
            st.download_button(
                "Scarica Privacy PDF (con intestazione)",
                data=pdf_priv_int,
                file_name=f"privacy_{paziente['Cognome']}_{paziente['Nome']}_{sel_cons_id}_intestazione.pdf",
                mime="application/pdf",
                key=f"dl_priv_int_{sel_cons_id}",
            )
        with colp2:
            pdf_priv_no = genera_privacy_pdf(paziente, cons_rec, include_header=False)
            st.download_button(
                "Scarica Privacy PDF (senza intestazione)",
                data=pdf_priv_no,
                file_name=f"privacy_{paziente['Cognome']}_{paziente['Nome']}_{sel_cons_id}_senza_intestazione.pdf",
                mime="application/pdf",
                key=f"dl_priv_no_{sel_cons_id}",
            )

    

        st.markdown("#### Firma digitale da remoto (Google Form)")
        st.caption("Apri il modulo Google con i campi precompilati. Per una firma 'grafometrica' vera, usa la firma su tablet direttamente nel PDF in studio; su Google Forms la firma è tipicamente tramite caricamento file (foto della firma).")

        # Motivo/contesto (es. Visita oculistica)
        motivo_default = "Visita Oculistica/esame oggettivo"
        motivo = st.text_input("Motivo/contesto (precompila nel form)", value=motivo_default, key="privacy_motivo_prefill")

        # se esiste un consenso MINORE, usa l'ultimo tutore come fallback per precompilare
        tut_fallback = {}
        try:
            last_min = next((r for r in cons_rows if str(r.get("Tipo","")).upper().startswith("MIN")), None)
            if last_min:
                tut_fallback = dict(last_min)
        except Exception:
            tut_fallback = {}

        colf1, colf2 = st.columns(2)
        with colf1:
            url_ad = build_google_form_url_adulto(paziente, motivo=motivo)
            st.link_button("Apri Google Form – Privacy ADULTO", url_ad)
        with colf2:
            url_mi = build_google_form_url_minore(paziente, motivo=motivo, tutore_fallback=tut_fallback)
            st.link_button("Apri Google Form – Privacy MINORE", url_mi)

        st.markdown("#### Importa dallo Sheet (risposte Google Forms) nello storico")
        st.caption("Usa gli Sheet ESISTENTI: pubblica il foglio risposte come CSV e inserisci l'URL in Secrets (PRIVACY_SHEET_ADULTO_CSV_URL / PRIVACY_SHEET_MINORE_CSV_URL).")
        colim1, colim2 = st.columns(2)
        with colim1:
            if st.button("Importa ultima risposta ADULTO per questo paziente", key="imp_priv_ad"):
                try:
                    ins_id = import_privacy_from_sheet_csv(cur, paziente, tipo="ADULTO")
                    if ins_id:
                        st.success(f"Import riuscito (ID consenso: {ins_id}). Aggiorna la pagina per vederlo nello storico.")
                    else:
                        st.warning("Nessun match trovato nello Sheet (per CF o Email) oppure CSV non configurato nei Secrets.")
                except Exception as e:
                    st.error(f"Errore import: {e}")
        with colim2:
            if st.button("Importa ultima risposta MINORE per questo paziente", key="imp_priv_min"):
                try:
                    ins_id = import_privacy_from_sheet_csv(cur, paziente, tipo="MINORE")
                    if ins_id:
                        st.success(f"Import riuscito (ID consenso: {ins_id}). Aggiorna la pagina per vederlo nello storico.")
                    else:
                        st.warning("Nessun match trovato nello Sheet (per CF o Email) oppure CSV non configurato nei Secrets.")
                except Exception as e:
                    st.error(f"Errore import: {e}")

    st.markdown("#### Registra un nuovo consenso (se cambiano le scelte)")
    with st.form("privacy_update_form"):
        tipo_priv = st.radio("Tipo", ["Adulto", "Minore"], horizontal=True, key="upd_tipo_priv")

        t_nome = t_cf = t_tel = t_mail = ""
        if tipo_priv == "Minore":
            st.markdown("**Dati del genitore/tutore**")
            c1, c2 = st.columns(2)
            with c1:
                t_nome = st.text_input("Nome e cognome tutore", "", key="upd_t_nome")
                t_tel = st.text_input("Telefono tutore", "", key="upd_t_tel")
            with c2:
                t_cf = st.text_input("Codice fiscale tutore", "", key="upd_t_cf").upper()
                t_mail = st.text_input("Email tutore", "", key="upd_t_mail")

        st.markdown("**Consensi**")
        c_tratt = st.checkbox("✅ Consenso trattamento dati (obbligatorio)", value=True, key="upd_c_tratt")
        c_serv = st.checkbox("Consenso comunicazioni di servizio", value=True, key="upd_c_serv")

        st.markdown("**Canali autorizzati**")
        cc1, cc2, cc3 = st.columns(3)
        with cc1:
            ch_email = st.checkbox("Email", value=True, key="upd_ch_email")
        with cc2:
            ch_sms = st.checkbox("SMS", value=False, key="upd_ch_sms")
        with cc3:
            ch_wa = st.checkbox("WhatsApp", value=True, key="upd_ch_wa")

        st.markdown("**Marketing / Klaviyo**")
        c_mark = st.checkbox("Consenso marketing/offerte", value=False, key="upd_c_mark")
        use_kl = st.checkbox("Autorizzo uso Klaviyo (solo se marketing attivo)", value=False, key="upd_use_kl")
        n_priv = st.text_area("Note (facoltative)", "", key="upd_note")
        firma_file = st.file_uploader("Firma (immagine PNG/JPG) – opzionale (se firmi in studio)", type=["png","jpg","jpeg"], key="upd_firma_img")

        save_priv = st.form_submit_button("Registra consenso")

    if save_priv:
        if not c_tratt:
            st.error("Il consenso al trattamento dati è obbligatorio.")
        else:
            payload = {
                "Data_Ora": _now_iso_dt(),
                "Tipo": "MINORE" if tipo_priv == "Minore" else "ADULTO",
                "Tutore_Nome": t_nome,
                "Tutore_CF": t_cf,
                "Tutore_Telefono": t_tel,
                "Tutore_Email": t_mail,
                "Consenso_Trattamento": c_tratt,
                "Consenso_Comunicazioni": c_serv,
                "Consenso_Marketing": c_mark,
                "Canale_Email": ch_email,
                "Canale_SMS": ch_sms,
                "Canale_WhatsApp": ch_wa,
                "Usa_Klaviyo": (use_kl and c_mark),
                "Firma_Blob": (firma_file.getvalue() if firma_file is not None else None),
                "Firma_Filename": (firma_file.name if firma_file is not None else ""),
                "Firma_URL": "",
                "Firma_Source": ("upload" if firma_file is not None else ""),
                "Note": n_priv,
            }
            insert_privacy_consent(cur, paz_id, payload)
            conn.commit()
            st.success("Consenso registrato nello storico.")
            st.rerun()
    # Conversione occhiali -> CL
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

        st.markdown("### Esame obiettivo (strutture oculari)")
        cornea_m = st.text_area("Cornea", rec.get("Cornea") or "", key="cornea_m")
        camera_ant_m = st.text_area("Camera anteriore", rec.get("Camera_Anteriore") or "", key="camera_ant_m")
        cristallino_m = st.text_area("Cristallino", rec.get("Cristallino") or "", key="cristallino_m")
        congiuntiva_m = st.text_area("Congiuntiva / Sclera", rec.get("Congiuntiva_Sclera") or "", key="congiuntiva_m")
        iride_pupilla_m = st.text_area("Iride / Pupilla", rec.get("Iride_Pupilla") or "", key="iride_pupilla_m")
        vitreo_m = st.text_area("Vitreo", rec.get("Vitreo") or "", key="vitreo_m")

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
                Cornea = ?, Camera_Anteriore = ?, Cristallino = ?, Congiuntiva_Sclera = ?, Iride_Pupilla = ?, Vitreo = ?,
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
                cornea_m,
                camera_ant_m,
                cristallino_m,
                congiuntiva_m,
                iride_pupilla_m,
                vitreo_m,
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
    st.subheader("Prescrizione occhiali (stampa A5 / A4 2×A5)")

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

            # SOLO A4: nessuna scelta formato
            formato_stampa = "A4"
            divider_line = False

            con_cirillo = st.checkbox(
                "Intestazione con Dott. Cirillo",
                value=True,
                key="prescr_con_cirillo",
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

            genera_pdf = st.form_submit_button("Genera PDF")

        if genera_pdf:
            data_iso_prescr = None
            if data_prescr_str.strip():
                try:
                    d = datetime.strptime(data_prescr_str.strip(), "%d/%m/%Y").date()
                    data_iso_prescr = d.isoformat()
                except ValueError:
                    st.error("Data prescrizione non valida. Usa il formato gg/mm/aaaa.")
                    data_iso_prescr = None

            
            common_kwargs = dict(
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

            # SOLO FORMATO A4 (niente A5)
            pdf_bytes = genera_prescrizione_occhiali_a4_pdf(**common_kwargs, con_cirillo=con_cirillo)
            filename = f"prescrizione_occhiali_{paziente['Cognome']}_{paziente['Nome']}_A4.pdf"
            label_btn = "Scarica prescrizione occhiali (A4)"

            st.download_button(
                label_btn,
                data=pdf_bytes,
                file_name=filename,
                mime="application/pdf",
                key="dl_prescr",
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


# ==========================
# Dashboard Evolutiva Paziente
# ==========================
def ui_dashboard_evolutiva():
    """Dashboard evolutiva basata su relazioni_cliniche."""
    import streamlit as st
    import os

    conn = get_connection()
    cur = conn.cursor()

    st.header("📊 Dashboard evolutiva")

    # Selezione paziente (indipendente dalla sezione Pazienti)
    try:
        cur.execute("SELECT ID, Cognome, Nome, Data_Nascita FROM Pazienti ORDER BY Cognome, Nome")
        paz_list = cur.fetchall()
    except Exception:
        st.error("Tabella Pazienti non disponibile.")
        return

    if not paz_list:
        st.info("Nessun paziente presente.")
        return

    def _label(p):
        pid, cogn, nome, dn = p
        dn_s = dn or ""
        return f"{cogn} {nome} (ID {pid}) {dn_s}".strip()

    sel = st.selectbox("Seleziona paziente", paz_list, format_func=_label)
    # robust handling for dict / tuple / sqlite Row
    if isinstance(sel, dict):
        paziente_id = sel.get("id") or sel.get("paziente_id")
    else:
        try:
            paziente_id = sel[0]
        except Exception:
            paziente_id = None

    if not paziente_id:
        st.error("Errore: ID paziente non determinabile dalla selezione.")
        return

    # Carica relazioni
    cur.execute(
        """
        SELECT id, titolo, tipo, data_relazione, docx_path, pdf_path
        FROM relazioni_cliniche
        WHERE paziente_id = %s
        ORDER BY data_relazione ASC
        """ % ("?" if _DB_BACKEND == "sqlite" else "%s"),
        (paziente_id,)
    )
    rows = cur.fetchall()

    if not rows:
        st.info("Nessuna relazione presente per questo paziente.")
        return

    def area_from_title(titolo: str) -> str:
        t = (titolo or "").lower()
        if "follow" in t: return "🔁 Follow-up"
        if "linguaggio" in t: return "🗣️ Linguaggio"
        if "neuropsico" in t: return "🧠 Neuropsicologica"
        if "neuroevol" in t: return "🌱 Neuroevolutiva"
        if "sensori" in t or "psico-motor" in t: return "🧍 Sensori-motoria"
        if "smof" in t or "oro" in t: return "👅 SMOF / Oro-linguale"
        if "scuola" in t: return "🏫 Scuola / ASL"
        return "📄 Altro"

    grouped = {}
    for r in rows:
        area = area_from_title(r[1])
        grouped.setdefault(area, []).append(r)

    for area, items in grouped.items():
        with st.expander(area, expanded=True):
            for r in items:
                rid, titolo, tipo, data_rel, docx_path, pdf_path = r
                st.markdown(f"**{data_rel} – {titolo}**")
                cols = st.columns(2)

                if docx_path and os.path.exists(docx_path):
                    with cols[0]:
                        with open(docx_path, "rb") as f:
                            st.download_button("⬇️ Word", f, file_name=os.path.basename(docx_path), key=f"dw_{rid}")
                else:
                    with cols[0]:
                        st.caption("Word non disponibile")

                if pdf_path and os.path.exists(pdf_path):
                    with cols[1]:
                        with open(pdf_path, "rb") as f:
                            st.download_button("⬇️ PDF", f, file_name=os.path.basename(pdf_path), key=f"dp_{rid}")
                else:
                    with cols[1]:
                        st.caption("PDF non disponibile (cloud)")



def main():
    st.set_page_config(
        page_title="The Organism – Gestionale Studio",
        layout="wide"
    )

    _sidebar_db_indicator()

    # inizializza il database (se le tabelle non ci sono le crea)
    init_db()

    # login obbligatorio
    if not login():
        return

    # menu laterale
    st.sidebar.title("Navigazione")
    sections = [
        "Pazienti",
        "Anamnesi",
        "Valutazioni visive / oculistiche",
        "Sedute / Terapie",
        "Coupon OF / SDS",
        "Dashboard incassi",
        "📊 Dashboard evolutiva",
    ]
    if APP_MODE == "test":
        sections.append("🧹 Pulizia DB (TEST)")
    sezione = st.sidebar.radio("Vai a", sections)

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
    elif sezione == "🗂️ Relazioni cliniche":
        ui_relazioni_cliniche()
    elif sezione == "📊 Dashboard evolutiva":
        ui_dashboard_evolutiva()
    elif sezione == "🧹 Pulizia DB (TEST)":
        ui_db_cleanup()


# ================================
# RELAZIONI CLINICHE - THE ORGANISM
# ================================
import shutil as _shutil

try:
    from docxtpl import DocxTemplate
except Exception:
    DocxTemplate = None

def _ensure_relazioni_cliniche_table(conn):
    """Crea la tabella relazioni_cliniche sia su SQLite che su PostgreSQL (Neon)."""
    cur = conn.cursor()
    # Prova prima sintassi PostgreSQL (psycopg2)
    try:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS relazioni_cliniche (
          id BIGSERIAL PRIMARY KEY,
          paziente_id BIGINT NOT NULL,
          tipo TEXT NOT NULL,
          titolo TEXT NOT NULL,
          data_relazione DATE NOT NULL,
          docx_path TEXT NOT NULL,
          pdf_path TEXT NOT NULL,
          note TEXT,
          created_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
        """)
        try:
            cur.execute("CREATE INDEX IF NOT EXISTS idx_relazioni_paziente ON relazioni_cliniche(paziente_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_relazioni_tipo ON relazioni_cliniche(tipo)")
        except Exception:
            pass
        conn.commit()
        return
    except Exception:
        # Fallback SQLite
        pass

    try:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS relazioni_cliniche (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          paziente_id INTEGER NOT NULL,
          tipo TEXT NOT NULL,
          titolo TEXT NOT NULL,
          data_relazione TEXT NOT NULL,
          docx_path TEXT NOT NULL,
          pdf_path TEXT NOT NULL,
          note TEXT,
          created_at TEXT NOT NULL
        )
        """)
        try:
            cur.execute("CREATE INDEX IF NOT EXISTS idx_relazioni_paziente ON relazioni_cliniche(paziente_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_relazioni_tipo ON relazioni_cliniche(tipo)")
        except Exception:
            pass
        conn.commit()
    except Exception:
        # ultima risorsa: non bloccare l'app
        try:
            conn.rollback()
        except Exception:
            pass

def _render_docx_docxtpl(template_path, out_docx_path, context):
    if DocxTemplate is None:
        raise RuntimeError("Dipendenza mancante: docxtpl. Aggiungi a requirements.txt: docxtpl")
    doc = DocxTemplate(template_path)
    doc.render(context)
    os.makedirs(os.path.dirname(out_docx_path), exist_ok=True)
    doc.save(out_docx_path)

def _convert_pdf_if_possible(docx_path, out_pdf_path):
    # Streamlit Cloud: spesso NON disponibile. In locale funziona se LibreOffice è installato.
    soffice_ok = _shutil.which("soffice") is not None
    if not soffice_ok:
        return False, ""
    import subprocess, shutil
    out_dir = os.path.dirname(out_pdf_path)
    os.makedirs(out_dir, exist_ok=True)
    cmd = [
        "soffice","--headless","--nologo","--nolockcheck","--nodefault","--norestore",
        "--convert-to","pdf","--outdir", out_dir, docx_path
    ]
    subprocess.run(cmd, check=True)
    gen = os.path.join(out_dir, os.path.splitext(os.path.basename(docx_path))[0] + ".pdf")
    if not os.path.exists(gen):
        return False, ""
    shutil.move(gen, out_pdf_path)
    return True, out_pdf_path

TEMPLATES = {
  # Linguaggio (ospedaliero) - unico template
  "linguaggio_invio_ospedaliero": {
    "titolo": "Relazione Linguaggio – Invio Ospedaliero",
    "files": {"std": "relazione_linguaggio_invio_ospedaliero.docx"}
  },
  # Neuropsicologica
  "neuropsicologica_3_6": {
    "titolo": "Relazione Neuropsicologica – Invio Ospedaliero (3–6)",
    "files": {"std": "relazione_neuropsicologica_invio_ospedaliero_3_6.docx"}
  },
  "neuropsicologica_6_10": {
    "titolo": "Relazione Neuropsicologica – Invio Ospedaliero (6–10)",
    "files": {"std": "relazione_neuropsicologica_invio_ospedaliero_6_10.docx"}
  },
  # Neuroevolutiva integrata
  "neuroevolutiva_3_6": {
    "titolo": "Relazione Neuroevolutiva Integrata (3–6)",
    "files": {"std": "relazione_neuroevolutiva_integrata_3_6.docx"}
  },
  "neuroevolutiva_6_10": {
    "titolo": "Relazione Neuroevolutiva Integrata (6–10)",
    "files": {"std": "relazione_neuroevolutiva_integrata_6_10.docx"}
  },
  # Scuola / ASL
  "scuola_asl_3_6": {
    "titolo": "Relazione Scuola / ASL (3–6)",
    "files": {"std": "relazione_scuola_asl_3_6.docx"}
  },
  "scuola_asl_6_10": {
    "titolo": "Relazione Scuola / ASL (6–10)",
    "files": {"std": "relazione_scuola_asl_6_10.docx"}
  },
  # Sensori-motoria / Neuro-psico-motoria
  "sensori_motorio_3_6": {
    "titolo": "Relazione Sensori-motoria / Neuro-psico-motoria (3–6)",
    "files": {"std": "relazione_sensori_motorio_neuropsicomotorio_3_6.docx"}
  },
  "sensori_motorio_6_10": {
    "titolo": "Relazione Sensori-motoria / Neuro-psico-motoria (6–10)",
    "files": {"std": "relazione_sensori_motorio_neuropsicomotorio_6_10.docx"}
  },
  # SMOF
  "smof_3_6": {
    "titolo": "Relazione SMOF / Oro-linguale (3–6)",
    "files": {"std": "relazione_smof_oro_linguale_3_6.docx"}
  },
  "smof_6_10": {
    "titolo": "Relazione SMOF / Oro-linguale (6–10)",
    "files": {"std": "relazione_smof_oro_linguale_6_10.docx"}
  },
  # Follow-up
  "followup_3_6": {
    "titolo": "Relazione Follow-up (3–6)",
    "files": {"std": "relazione_followup_3_6.docx"}
  },
  "followup_6_10": {
    "titolo": "Relazione Follow-up (6–10)",
    "files": {"std": "relazione_followup_6_10.docx"}
  },
}

def ui_relazioni_cliniche(templates_dir="templates", output_base="output"):
    import streamlit as st
    from datetime import date


    # conn & selezione paziente (indipendente dalla sezione Pazienti)
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT ID, Cognome, Nome, Data_Nascita FROM Pazienti ORDER BY Cognome, Nome")
        paz_list = cur.fetchall()
    except Exception:
        st.error("Tabella Pazienti non disponibile.")
        return
    if not paz_list:
        st.info("Nessun paziente presente.")
        return

    def _label(p):
        pid, cogn, nome, dn = p
        dn_s = dn or ""
        return f"{cogn} {nome} (ID {pid}) {dn_s}".strip()

    sel = st.selectbox("Seleziona paziente", paz_list, format_func=_label)
    try:
        paziente_id = sel[0]
    except Exception:
        paziente_id = None
    if not paziente_id:
        st.error("Errore: ID paziente non determinabile.")
        return

    # carica dati base paziente (nome/cognome/data nascita) per template
    paziente = {"id": paziente_id, "cognome": sel[1], "nome": sel[2], "data_nascita": sel[3]}

    _ensure_relazioni_cliniche_table(conn)

    st.header("🗂️ Relazioni cliniche")
    st.caption("Generazione: Word sempre (cloud) • PDF solo in locale se LibreOffice è disponibile")

    # Selezione tipo relazione
    keys = list(TEMPLATES.keys())
    labels = [TEMPLATES[k]["titolo"] for k in keys]
    idx = 0
    scelta = st.selectbox("Tipo relazione", options=list(range(len(keys))), format_func=lambda i: labels[i])
    rel_key = keys[scelta]
    rel = TEMPLATES[rel_key]

    c1, c2 = st.columns(2)
    with c1:
        data_valutazione = st.date_input("Data valutazione", value=date.today())
    with c2:
        data_relazione = st.date_input("Data relazione", value=date.today())

    periodo_followup = ""
    if "followup" in rel_key:
        periodo_followup = st.text_input("Periodo follow-up (es. Gen–Mar 2026)", value="")

    note = st.text_area("Note cliniche (facoltative)", height=140)

    # Context placeholder comune
    nome_cognome = f"{paziente.get('cognome','')} {paziente.get('nome','')}".strip()
    context = {
        "NOME_COGNOME": nome_cognome,
        "DATA_NASCITA": paziente.get("data_nascita",""),
        "ETA": paziente.get("eta",""),
        "SCUOLA": paziente.get("scuola",""),
        "DATA_VALUTAZIONE": data_valutazione.strftime("%d/%m/%Y"),
        "DATA_RELAZIONE": data_relazione.strftime("%d/%m/%Y"),
        "NOTE_CLINICHE": note.strip(),
        "PERIODO_FOLLOWUP": periodo_followup.strip(),
    }

    template_file = rel["files"]["std"]
    template_path = os.path.join(templates_dir, template_file)

    if st.button("📄 Genera Word ( + PDF se disponibile )", type="primary"):
        if not os.path.exists(template_path):
            st.error(f"Template mancante: {template_path}")
            st.stop()

        pid = paziente.get("id")
        safe_name = (nome_cognome.replace(" ", "_") or f"PAZ_{pid}")
        out_dir = os.path.join(output_base, f"{pid}_{safe_name}", "relazioni_cliniche")
        os.makedirs(out_dir, exist_ok=True)

        base = f"{data_relazione.strftime('%Y-%m-%d')}_{rel_key}_{safe_name}"
        out_docx = os.path.join(out_dir, base + ".docx")
        out_pdf  = os.path.join(out_dir, base + ".pdf")

        try:
            _render_docx_docxtpl(template_path, out_docx, context)
        except Exception as e:
            st.error(f"Errore Word: {e}")
            st.stop()

        pdf_ok, pdf_path = _convert_pdf_if_possible(out_docx, out_pdf)
        if not pdf_ok:
            pdf_path = ""  # cloud-safe

        # salva DB
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO relazioni_cliniche (paziente_id, tipo, titolo, data_relazione, docx_path, pdf_path, note, created_at) VALUES (?,?,?,?,?,?,?,?)",
            (pid, rel_key, rel["titolo"], data_relazione.strftime("%Y-%m-%d"), out_docx, pdf_path, note.strip(), datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()

        st.success("Relazione generata ✅")
        with open(out_docx, "rb") as f:
            st.download_button("⬇️ Scarica Word", f, file_name=os.path.basename(out_docx), key=f"dw_{rel_key}_{pid}")
        if pdf_path and os.path.exists(pdf_path):
            with open(pdf_path, "rb") as f:
                st.download_button("⬇️ Scarica PDF", f, file_name=os.path.basename(pdf_path), key=f"dp_{rel_key}_{pid}")
        else:
            st.info("PDF non disponibile in cloud: apri il Word e salva in PDF dal PC in studio.")

if __name__ == "__main__":
    main()
