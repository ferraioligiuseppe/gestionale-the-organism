# -*- coding: utf-8 -*-
"""
schema_manager.py — Simple, idempotent schema bootstrap for The Organism.

Goal:
- Avoid deploy-time crashes when a DB is empty/new (TEST/PROD).
- Keep it simple (no Alembic), Streamlit-friendly.
- Safe to call multiple times.

Usage (recommended):
    from schema_manager import ensure_all_schemas
    ensure_all_schemas(conn, backend="postgres")  # or "sqlite"
"""

from __future__ import annotations

from typing import Literal, Optional


Backend = Literal["postgres", "sqlite"]


def ensure_all_schemas(conn, backend: Backend = "postgres") -> None:
    """
    Idempotent bootstrap for all schemas used by the app.
    Call once at startup (e.g., inside init_db()).
    """
    ensure_auth_schema(conn, backend=backend)
    ensure_core_schema(conn, backend=backend)
    # Placeholders: keep separated so future refactors are easy.
    ensure_vision_schema(conn, backend=backend)
    ensure_osteo_schema(conn, backend=backend)


def ensure_auth_schema(conn, backend: Backend = "postgres") -> None:
    cur = conn.cursor()
    try:
        if backend == "sqlite":
            cur.execute("""
                CREATE TABLE IF NOT EXISTS auth_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT,
                    password_hash TEXT NOT NULL,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    must_change_password INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT,
                    last_login_at TEXT
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS auth_roles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS auth_user_roles (
                    user_id INTEGER NOT NULL,
                    role_id INTEGER NOT NULL,
                    PRIMARY KEY (user_id, role_id),
                    FOREIGN KEY(user_id) REFERENCES auth_users(id) ON DELETE CASCADE,
                    FOREIGN KEY(role_id) REFERENCES auth_roles(id) ON DELETE CASCADE
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS auth_audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT,
                    user_id INTEGER,
                    action TEXT NOT NULL,
                    entity TEXT,
                    entity_id TEXT,
                    meta TEXT
                );
            """)
            # Seed roles
            for r in ("admin", "vision", "osteo", "segreteria", "clinico"):
                cur.execute("INSERT OR IGNORE INTO auth_roles(name) VALUES (?)", (r,))
        else:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS auth_users (
                  id BIGSERIAL PRIMARY KEY,
                  username TEXT UNIQUE NOT NULL,
                  email TEXT,
                  password_hash TEXT NOT NULL,
                  is_active BOOLEAN NOT NULL DEFAULT TRUE,
                  must_change_password BOOLEAN NOT NULL DEFAULT FALSE,
                  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                  last_login_at TIMESTAMPTZ
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS auth_roles (
                  id BIGSERIAL PRIMARY KEY,
                  name TEXT UNIQUE NOT NULL
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS auth_user_roles (
                  user_id BIGINT NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
                  role_id BIGINT NOT NULL REFERENCES auth_roles(id) ON DELETE CASCADE,
                  PRIMARY KEY (user_id, role_id)
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS auth_audit_log (
                  id BIGSERIAL PRIMARY KEY,
                  ts TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                  user_id BIGINT REFERENCES auth_users(id) ON DELETE SET NULL,
                  action TEXT NOT NULL,
                  entity TEXT,
                  entity_id TEXT,
                  meta JSONB NOT NULL DEFAULT '{}'::jsonb
                );
            """)
            cur.execute("""
                INSERT INTO auth_roles(name) VALUES
                ('admin'),('vision'),('osteo'),('segreteria'),('clinico')
                ON CONFLICT (name) DO NOTHING;
            """)
        conn.commit()
    finally:
        try:
            cur.close()
        except Exception:
            pass


def ensure_core_schema(conn, backend: Backend = "postgres") -> None:
    """
    Core tables shared by modules: Pazienti, Anamnesi, Sedute, Coupons, Consensi_Privacy, relazioni_cliniche.
    Keep aligned with app.py init_db, but minimal and idempotent.
    """
    cur = conn.cursor()
    try:
        if backend == "sqlite":
            # Core
            cur.execute("""
                CREATE TABLE IF NOT EXISTS Pazienti (
                    ID INTEGER PRIMARY KEY AUTOINCREMENT,
                    Cognome TEXT NOT NULL,
                    Nome TEXT NOT NULL,
                    Data_Nascita TEXT,
                    Sesso TEXT,
                    Telefono TEXT,
                    Email TEXT,
                    Indirizzo TEXT,
                    CAP TEXT,
                    Citta TEXT,
                    Provincia TEXT,
                    Codice_Fiscale TEXT,
                    Stato_Paziente TEXT
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS Anamnesi (
                    ID INTEGER PRIMARY KEY AUTOINCREMENT,
                    Paziente_ID INTEGER NOT NULL,
                    Data_Anamnesi TEXT,
                    Motivo TEXT,
                    Storia TEXT,
                    Note TEXT,
                    Perinatale TEXT,
                    Sviluppo TEXT,
                    Scuola TEXT,
                    Emotivo TEXT,
                    Sensoriale TEXT,
                    Stile_Vita TEXT
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS Sedute (
                    ID INTEGER PRIMARY KEY AUTOINCREMENT,
                    Paziente_ID INTEGER NOT NULL,
                    Data_Seduta TEXT,
                    Terapia TEXT,
                    Professionista TEXT,
                    Costo REAL DEFAULT 0,
                    Pagato INTEGER DEFAULT 0,
                    Note TEXT
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS Coupons (
                    ID INTEGER PRIMARY KEY AUTOINCREMENT,
                    Paziente_ID INTEGER NOT NULL,
                    Tipo_Coupon TEXT,
                    Codice_Coupon TEXT,
                    Data_Assegnazione TEXT,
                    Note TEXT,
                    Utilizzato INTEGER DEFAULT 0
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS Consensi_Privacy (
                    ID INTEGER PRIMARY KEY AUTOINCREMENT,
                    Paziente_ID INTEGER NOT NULL,
                    Data_Ora TEXT,
                    Tipo TEXT,
                    Tutore_Nome TEXT,
                    Tutore_CF TEXT,
                    Tutore_Telefono TEXT,
                    Tutore_Email TEXT,
                    Consenso_Trattamento INTEGER DEFAULT 0,
                    Consenso_Comunicazioni INTEGER DEFAULT 0,
                    Consenso_Marketing INTEGER DEFAULT 0,
                    Canale_Email INTEGER DEFAULT 0,
                    Canale_SMS INTEGER DEFAULT 0,
                    Canale_WhatsApp INTEGER DEFAULT 0,
                    Usa_Klaviyo INTEGER DEFAULT 0,
                    Firma_Blob BLOB,
                    Firma_Filename TEXT,
                    Firma_URL TEXT,
                    Firma_Source TEXT,
                    Pdf_Blob BLOB,
                    Pdf_Filename TEXT,
                    Note TEXT
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS relazioni_cliniche (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    paziente_id INTEGER NOT NULL,
                    tipo TEXT NOT NULL,
                    titolo TEXT NOT NULL,
                    data_relazione TEXT NOT NULL,
                    docx_path TEXT NOT NULL,
                    pdf_path TEXT,
                    note TEXT,
                    created_at TEXT NOT NULL
                );
            """)
            # Minimal indexes
            try:
                cur.execute("CREATE INDEX IF NOT EXISTS idx_relazioni_paziente ON relazioni_cliniche(paziente_id)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_relazioni_tipo ON relazioni_cliniche(tipo)")
            except Exception:
                pass
        else:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS Pazienti (
                    ID BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
                    Cognome TEXT NOT NULL,
                    Nome TEXT NOT NULL,
                    Data_Nascita TEXT,
                    Sesso TEXT,
                    Telefono TEXT,
                    Email TEXT,
                    Indirizzo TEXT,
                    CAP TEXT,
                    Citta TEXT,
                    Provincia TEXT,
                    Codice_Fiscale TEXT,
                    Stato_Paziente TEXT NOT NULL DEFAULT 'ATTIVO'
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS Anamnesi (
                    ID BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
                    Paziente_ID BIGINT NOT NULL REFERENCES Pazienti(ID) ON DELETE CASCADE,
                    Data_Anamnesi TEXT,
                    Motivo TEXT,
                    Storia TEXT,
                    Note TEXT,
                    Perinatale TEXT,
                    Sviluppo TEXT,
                    Scuola TEXT,
                    Emotivo TEXT,
                    Sensoriale TEXT,
                    Stile_Vita TEXT
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS Sedute (
                    ID BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
                    Paziente_ID BIGINT NOT NULL REFERENCES Pazienti(ID) ON DELETE CASCADE,
                    Data_Seduta TEXT,
                    Terapia TEXT,
                    Professionista TEXT,
                    Costo REAL,
                    Pagato INTEGER NOT NULL DEFAULT 0,
                    Note TEXT
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS Coupons (
                    ID BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
                    Paziente_ID BIGINT NOT NULL REFERENCES Pazienti(ID) ON DELETE CASCADE,
                    Tipo_Coupon TEXT NOT NULL,
                    Codice_Coupon TEXT,
                    Data_Assegnazione TEXT,
                    Note TEXT,
                    Utilizzato INTEGER NOT NULL DEFAULT 0
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS Consensi_Privacy (
                    ID BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
                    Paziente_ID BIGINT NOT NULL REFERENCES Pazienti(ID) ON DELETE CASCADE,
                    Data_Ora TEXT,
                    Tipo TEXT,
                    Tutore_Nome TEXT,
                    Tutore_CF TEXT,
                    Tutore_Telefono TEXT,
                    Tutore_Email TEXT,
                    Consenso_Trattamento INTEGER NOT NULL DEFAULT 0,
                    Consenso_Comunicazioni INTEGER NOT NULL DEFAULT 0,
                    Consenso_Marketing INTEGER NOT NULL DEFAULT 0,
                    Canale_Email INTEGER NOT NULL DEFAULT 0,
                    Canale_SMS INTEGER NOT NULL DEFAULT 0,
                    Canale_WhatsApp INTEGER NOT NULL DEFAULT 0,
                    Usa_Klaviyo INTEGER NOT NULL DEFAULT 0,
                    Firma_Blob BYTEA,
                    Firma_Filename TEXT,
                    Firma_URL TEXT,
                    Firma_Source TEXT,
                    Pdf_Blob BYTEA,
                    Pdf_Filename TEXT,
                    Note TEXT
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS relazioni_cliniche (
                    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
                    paziente_id BIGINT NOT NULL REFERENCES Pazienti(ID) ON DELETE CASCADE,
                    tipo TEXT NOT NULL,
                    titolo TEXT NOT NULL,
                    data_relazione TEXT NOT NULL,
                    docx_path TEXT NOT NULL,
                    pdf_path TEXT,
                    note TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
            """)
            try:
                cur.execute("CREATE INDEX IF NOT EXISTS idx_relazioni_paziente ON relazioni_cliniche(paziente_id)")
                cur.execute("CREATE INDEX IF NOT EXISTS idx_relazioni_tipo ON relazioni_cliniche(tipo)")
            except Exception:
                pass

        conn.commit()
    finally:
        try:
            cur.close()
        except Exception:
            pass


def ensure_vision_schema(conn, backend: Backend = "postgres") -> None:
    """
    Placeholder for Vision Manager tables.
    Keep it separated so you can progressively migrate vision tables out of app.py.
    """
    # NOTE: Many vision tables are created in app.py init_db().
    # Here we keep a no-op for now (safe).
    return


def ensure_osteo_schema(conn, backend: Backend = "postgres") -> None:
    """
    Placeholder for Osteopatia tables.
    Keep it separated so you can progressively migrate osteo tables out of app.py.
    """
    return
