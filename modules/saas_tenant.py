# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════╗
║  SAAS TENANT — Architettura Multi-Tenant The Organism Platform      ║
║  Meta-DB · Piani abbonamento · Controllo accessi · Onboarding       ║
╚══════════════════════════════════════════════════════════════════════╝

ARCHITETTURA:
  ┌─────────────────────────────────────────────────────┐
  │  META-DB (Neon centrale)                            │
  │  · studi         → ogni studio registrato           │
  │  · abbonamenti   → piano attivo per studio          │
  │  · moduli        → quali sezioni sono abilitate     │
  │  · utenti_meta   → login + studio_id               │
  └────────────────────────┬────────────────────────────┘
                           │ DATABASE_URL per studio
             ┌─────────────┼─────────────┐
             ▼             ▼             ▼
         Studio A      Studio B      Studio C
         (Neon DB)     (Neon DB)     (Neon DB)
         pazienti      pazienti      pazienti
         sedute        sedute        sedute
         ...           ...           ...
"""
from __future__ import annotations
from typing import Optional
import streamlit as st
import json
import datetime
import hashlib
import secrets

# ══════════════════════════════════════════════════════════════════════
#  PIANI DI ABBONAMENTO
# ══════════════════════════════════════════════════════════════════════

PIANI: dict[str, dict] = {
    "base": {
        "nome":          "Base",
        "prezzo_mese":   49,
        "prezzo_anno":   490,
        "max_utenti":    2,
        "max_pazienti":  200,
        "moduli": [
            "pazienti", "sedute", "privacy", "dashboard",
        ],
        "descrizione": "Gestione pazienti e sedute. Ideale per libero professionista.",
    },
    "professional": {
        "nome":          "Professional",
        "prezzo_mese":   99,
        "prezzo_anno":   990,
        "max_utenti":    5,
        "max_pazienti":  1000,
        "moduli": [
            "pazienti", "sedute", "privacy", "dashboard",
            "pnev", "vvf", "osteopatia", "relazioni_ai",
            "lenti_contatto", "referti",
        ],
        "descrizione": "Per ottometristi, neuropsicomotricisti, osteopati.",
    },
    "clinic": {
        "nome":          "Clinic",
        "prezzo_mese":   199,
        "prezzo_anno":   1990,
        "max_utenti":    15,
        "max_pazienti":  5000,
        "moduli": [
            "pazienti", "sedute", "privacy", "dashboard",
            "pnev", "vvf", "osteopatia", "relazioni_ai",
            "lenti_contatto", "referti",
            "nps", "dsa", "test_psy", "funzioni_esecutive",
            "export_statistici", "report_pdf", "piano_vt",
            "gaze_tracking", "reading",
        ],
        "descrizione": "Centro multidisciplinare con psicologi, logopedisti, NPI.",
    },
    "enterprise": {
        "nome":          "Enterprise",
        "prezzo_mese":   0,   # custom
        "prezzo_anno":   0,
        "max_utenti":    999,
        "max_pazienti":  999999,
        "moduli":        ["*"],  # tutti i moduli
        "descrizione":   "Multi-sede, API, white-label. Prezzo su misura.",
    },
}

# Mapping modulo → costante sezione (da app_sections.py)
MODULO_SEZIONE: dict[str, list[str]] = {
    "pazienti":           ["Pazienti"],
    "sedute":             ["Sedute / Terapie"],
    "privacy":            [" Privacy & Consensi (PDF)"],
    "dashboard":          ["Dashboard incassi"],
    "pnev":               ["Valutazione PNEV"],
    "vvf":                ["Valutazioni visive / oculistiche"],
    "osteopatia":         ["Osteopatia"],
    "relazioni_ai":       ["️ Relazioni cliniche"],
    "lenti_contatto":     ["👁️ Lenti a contatto"],
    "referti":            ["️ Debug DB"],
    "nps":                ["🧠 NPS Neuropsicologico"],
    "dsa":                ["📚 DSA — Apprendimento"],
    "test_psy":           ["🔬 Test Psicologici"],
    "funzioni_esecutive": ["⚡ Funzioni Esecutive"],
    "export_statistici":  ["📊 Export Statistici"],
    "report_pdf":         ["📄 Report PDF Clinico"],
    "piano_vt":           ["🎯 Piano Vision Therapy"],
    "gaze_tracking":      [" Eye Tracking"],
    "reading":            [" Lettura Avanzata DOM"],
}


# ══════════════════════════════════════════════════════════════════════
#  SCHEMA META-DB
# ══════════════════════════════════════════════════════════════════════

SQL_SCHEMA_META = """
-- Tabella studi registrati
CREATE TABLE IF NOT EXISTS studi (
    id              BIGSERIAL PRIMARY KEY,
    codice          TEXT UNIQUE NOT NULL,       -- es. "studio_abc123"
    nome            TEXT NOT NULL,
    email_admin     TEXT NOT NULL,
    telefono        TEXT,
    indirizzo       TEXT,
    partita_iva     TEXT,
    db_url          TEXT NOT NULL,             -- DATABASE_URL del DB dello studio
    piano           TEXT NOT NULL DEFAULT 'base',
    stato           TEXT NOT NULL DEFAULT 'attivo',  -- attivo | sospeso | cancellato
    created_at      TIMESTAMP DEFAULT NOW(),
    scadenza_piano  DATE,
    note            TEXT
);

-- Abbonamenti
CREATE TABLE IF NOT EXISTS abbonamenti (
    id              BIGSERIAL PRIMARY KEY,
    studio_id       BIGINT REFERENCES studi(id),
    piano           TEXT NOT NULL,
    inizio          DATE NOT NULL,
    fine            DATE,
    importo_mese    NUMERIC(8,2),
    stato           TEXT DEFAULT 'attivo',   -- attivo | scaduto | cancellato
    created_at      TIMESTAMP DEFAULT NOW()
);

-- Utenti piattaforma (collegati a uno studio)
CREATE TABLE IF NOT EXISTS utenti_meta (
    id              BIGSERIAL PRIMARY KEY,
    studio_id       BIGINT REFERENCES studi(id),
    email           TEXT UNIQUE NOT NULL,
    nome            TEXT,
    cognome         TEXT,
    ruolo           TEXT DEFAULT 'clinico',  -- admin | clinico | segreteria
    password_hash   TEXT NOT NULL,
    salt            TEXT NOT NULL,
    attivo          BOOLEAN DEFAULT TRUE,
    ultimo_accesso  TIMESTAMP,
    created_at      TIMESTAMP DEFAULT NOW()
);

-- Log accessi
CREATE TABLE IF NOT EXISTS log_accessi (
    id          BIGSERIAL PRIMARY KEY,
    studio_id   BIGINT,
    utente_id   BIGINT,
    evento      TEXT,                        -- login | logout | errore
    ip          TEXT,
    created_at  TIMESTAMP DEFAULT NOW()
);

-- Indici
CREATE INDEX IF NOT EXISTS idx_studi_codice ON studi(codice);
CREATE INDEX IF NOT EXISTS idx_utenti_email ON utenti_meta(email);
CREATE INDEX IF NOT EXISTS idx_abbonamenti_studio ON abbonamenti(studio_id);
"""


# ══════════════════════════════════════════════════════════════════════
#  FUNZIONI DI ACCESSO TENANT
# ══════════════════════════════════════════════════════════════════════

def _hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    if salt is None:
        salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(),
                             100_000)
    return h.hex(), salt


def inizializza_meta_db(meta_conn) -> None:
    """Crea le tabelle del meta-DB se non esistono."""
    try:
        cur = meta_conn.cursor()
        cur.execute(SQL_SCHEMA_META)
        meta_conn.commit()
        st.success("✅ Meta-DB inizializzato.")
    except Exception as e:
        st.error(f"Errore inizializzazione meta-DB: {e}")


def registra_studio(meta_conn, nome: str, email_admin: str,
                    db_url: str, piano: str = "base",
                    telefono: str = "", indirizzo: str = "",
                    partita_iva: str = "") -> Optional[str]:
    """
    Registra un nuovo studio e ritorna il codice univoco.
    Chiamare da pannello admin o da form onboarding.
    """
    codice = f"studio_{secrets.token_hex(6)}"
    try:
        cur = meta_conn.cursor()
        cur.execute("""
            INSERT INTO studi (codice, nome, email_admin, db_url, piano,
                               telefono, indirizzo, partita_iva, scadenza_piano)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (codice, nome, email_admin, db_url, piano,
              telefono, indirizzo, partita_iva,
              (datetime.date.today() + datetime.timedelta(days=30)).isoformat()))
        studio_id = cur.fetchone()[0]
        # Abbonamento iniziale
        cur.execute("""
            INSERT INTO abbonamenti (studio_id, piano, inizio, importo_mese)
            VALUES (%s, %s, %s, %s)
        """, (studio_id, piano, datetime.date.today().isoformat(),
              PIANI[piano]["prezzo_mese"]))
        meta_conn.commit()
        return codice
    except Exception as e:
        st.error(f"Errore registrazione studio: {e}")
        return None


def crea_utente(meta_conn, studio_id: int, email: str, nome: str,
                cognome: str, password: str, ruolo: str = "clinico") -> bool:
    """Crea un utente nella piattaforma."""
    pwd_hash, salt = _hash_password(password)
    try:
        cur = meta_conn.cursor()
        cur.execute("""
            INSERT INTO utenti_meta (studio_id, email, nome, cognome,
                                     ruolo, password_hash, salt)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (studio_id, email, nome, cognome, ruolo, pwd_hash, salt))
        meta_conn.commit()
        return True
    except Exception as e:
        st.error(f"Errore creazione utente: {e}")
        return False


def verifica_login(meta_conn, email: str, password: str) -> Optional[dict]:
    """
    Verifica credenziali. Ritorna dict con info studio/utente o None.
    """
    try:
        cur = meta_conn.cursor()
        cur.execute("""
            SELECT u.id, u.studio_id, u.nome, u.cognome, u.ruolo,
                   u.password_hash, u.salt, s.codice, s.nome as nome_studio,
                   s.piano, s.stato, s.db_url
            FROM utenti_meta u
            JOIN studi s ON s.id = u.studio_id
            WHERE u.email = %s AND u.attivo = TRUE
        """, (email,))
        row = cur.fetchone()
        if not row:
            return None
        if isinstance(row, dict):
            h = row["password_hash"]
            salt = row["salt"]
            info = row
        else:
            cols = ["id", "studio_id", "nome", "cognome", "ruolo",
                    "password_hash", "salt", "codice_studio", "nome_studio",
                    "piano", "stato_studio", "db_url"]
            info = dict(zip(cols, row))
            h    = info["password_hash"]
            salt = info["salt"]

        pwd_test, _ = _hash_password(password, salt)
        if pwd_test != h:
            return None

        if info.get("stato_studio") != "attivo":
            return None

        # Aggiorna ultimo accesso
        cur.execute("UPDATE utenti_meta SET ultimo_accesso=NOW() WHERE id=%s",
                    (info["id"],))
        meta_conn.commit()
        return info
    except Exception as e:
        st.error(f"Errore login: {e}")
        return None


def moduli_attivi(piano: str) -> list[str]:
    """Ritorna lista dei moduli abilitati per un piano."""
    cfg = PIANI.get(piano, PIANI["base"])
    if cfg["moduli"] == ["*"]:
        return list(MODULO_SEZIONE.keys())
    return cfg["moduli"]


def sezioni_abilitate(piano: str) -> list[str]:
    """Ritorna la lista di sezioni (label menu) abilitate per il piano."""
    sezioni: list[str] = []
    for modulo in moduli_attivi(piano):
        sezioni.extend(MODULO_SEZIONE.get(modulo, []))
    return sezioni


def studio_ha_modulo(piano: str, modulo: str) -> bool:
    attivi = moduli_attivi(piano)
    return modulo in attivi or attivi == ["*"]


# ══════════════════════════════════════════════════════════════════════
#  PANNELLO ADMIN — GESTIONE STUDI E UTENTI
# ══════════════════════════════════════════════════════════════════════

def render_admin_saas(meta_conn) -> None:
    """Pannello di amministrazione SaaS."""
    st.title("⚙️ The Organism Platform — Admin SaaS")
    tabelle_ok = _ensure_saas_tables(meta_conn)
    if not tabelle_ok:
        st.warning(
            "⚠️ Tabelle SaaS non ancora inizializzate. "
            "Vai alla tab **🔧 Init DB** e clicca il pulsante per crearle."
        )
    st.caption("Pannello riservato all'amministratore della piattaforma")

    tab_studi, tab_crea, tab_piani, tab_init = st.tabs([
        "📋 Studi registrati",
        "➕ Nuovo studio",
        "💳 Piani",
        "🔧 Init DB",
    ])

    with tab_studi:
        try:
            cur = meta_conn.cursor()
            cur.execute("""
                SELECT s.codice, s.nome, s.email_admin, s.piano,
                       s.stato, s.scadenza_piano, s.created_at
                FROM studi s ORDER BY s.created_at DESC
            """)
            rows = cur.fetchall()
            if rows:
                import pandas as pd
                cols = ["Codice", "Studio", "Email admin", "Piano",
                        "Stato", "Scadenza", "Registrato il"]
                df = pd.DataFrame(rows, columns=cols)
                st.dataframe(df, use_container_width=True)
                st.caption(f"Totale studi: {len(rows)}")
            else:
                st.info("Nessuno studio registrato.")
        except Exception as e:
            st.error(f"Errore: {e}")

    with tab_crea:
        st.subheader("Registra nuovo studio")
        with st.form("form_nuovo_studio"):
            nome_s     = st.text_input("Nome studio *")
            email_a    = st.text_input("Email admin *")
            tel        = st.text_input("Telefono")
            indirizzo  = st.text_input("Indirizzo")
            piva       = st.text_input("Partita IVA")
            db_url_s   = st.text_input("DATABASE_URL Neon dello studio *",
                                       type="password")
            piano_s    = st.selectbox("Piano", list(PIANI.keys()))
            # Password iniziale admin dello studio
            pwd_admin  = st.text_input("Password admin iniziale *", type="password")
            nome_admin = st.text_input("Nome admin")
            cog_admin  = st.text_input("Cognome admin")

            submitted = st.form_submit_button("✅ Registra studio")

        if submitted:
            if not all([nome_s, email_a, db_url_s, pwd_admin]):
                st.error("Compila tutti i campi obbligatori (*)")
            else:
                codice = registra_studio(
                    meta_conn, nome_s, email_a, db_url_s, piano_s,
                    tel, indirizzo, piva
                )
                if codice:
                    # Recupera studio_id
                    cur2 = meta_conn.cursor()
                    cur2.execute("SELECT id FROM studi WHERE codice=%s", (codice,))
                    sid = cur2.fetchone()
                    sid = sid[0] if sid else None
                    if sid:
                        ok = crea_utente(meta_conn, sid, email_a,
                                         nome_admin, cog_admin,
                                         pwd_admin, ruolo="admin")
                        if ok:
                            st.success(f"✅ Studio creato! Codice: **{codice}**")
                            st.code(f"Codice studio: {codice}\nEmail: {email_a}")

    with tab_piani:
        st.subheader("Piani di abbonamento")
        for piano_id, cfg in PIANI.items():
            with st.expander(f"**{cfg['nome']}** — "
                             f"€{cfg['prezzo_mese']}/mese"):
                c1, c2 = st.columns(2)
                c1.metric("Prezzo/mese", f"€{cfg['prezzo_mese']}")
                c1.metric("Prezzo/anno", f"€{cfg['prezzo_anno']}")
                c2.metric("Max utenti", cfg["max_utenti"])
                c2.metric("Max pazienti", cfg["max_pazienti"])
                st.markdown(f"**Descrizione:** {cfg['descrizione']}")
                st.markdown("**Moduli inclusi:** " +
                            ", ".join(cfg["moduli"]))

    with tab_init:
        st.subheader("Inizializzazione meta-DB")
        st.warning("⚠️ Esegui solo la prima volta su un meta-DB vuoto.")
        if st.button("🔧 Crea tabelle meta-DB", type="primary"):
            inizializza_meta_db(meta_conn)


# ══════════════════════════════════════════════════════════════════════
#  PANNELLO STUDIO — Gestione utenti del singolo studio
# ══════════════════════════════════════════════════════════════════════

def _ensure_saas_tables(conn) -> bool:
    """
    Tenta di creare le tabelle SaaS usando una savepoint
    per non sporcare la transazione corrente.
    Ritorna True se le tabelle esistono, False altrimenti.
    """
    try:
        cur = conn.cursor()
        cur.execute("SAVEPOINT sp_saas_check")
        cur.execute("SELECT 1 FROM studi LIMIT 1")
        cur.execute("RELEASE SAVEPOINT sp_saas_check")
        return True
    except Exception:
        try:
            cur.execute("ROLLBACK TO SAVEPOINT sp_saas_check")
            cur.execute("RELEASE SAVEPOINT sp_saas_check")
        except Exception:
            pass
        return False



def render_gestione_studio(meta_conn, studio_id: int, piano: str) -> None:
    """Pannello per l'admin di un singolo studio."""
    st.title("🏥 Il mio studio")

    cfg = PIANI.get(piano, PIANI["professional"])
    tab_piano, tab_utenti, tab_moduli = st.tabs([
        "💳 Piano attivo", "👥 Utenti", "📦 Moduli abilitati"
    ])

    with tab_piano:
        st.markdown(f"### Piano: **{cfg['nome']}**")
        c1, c2, c3 = st.columns(3)
        c1.metric("Prezzo mensile",  f"€{cfg['prezzo_mese']}")
        c2.metric("Max utenti",       cfg["max_utenti"])
        c3.metric("Max pazienti",     cfg["max_pazienti"])
        st.markdown(f"_{cfg['descrizione']}_")
        st.info("Per cambiare piano o per assistenza: **info@theorganism.it**")

    with tab_utenti:
        if not tabelle_ok:
            st.info(
                "Le tabelle SaaS non sono ancora state create. "
                "Vai su **⚙️ Platform Admin → 🔧 Init DB** e clicca il pulsante."
            )
            rows = []
        else:
            rows = []
            try:
                cur = meta_conn.cursor()
                cur.execute(
                    "SELECT nome, cognome, email, ruolo, attivo, ultimo_accesso "
                    "FROM utenti_meta WHERE studio_id = %s ORDER BY ruolo, cognome",
                    (studio_id,)
                )
                rows = cur.fetchall() or []
            except Exception:
                rows = []

        if rows:
            try:
                import pandas as pd
                df = pd.DataFrame(rows, columns=["Nome","Cognome","Email",
                                                  "Ruolo","Attivo","Ultimo accesso"])
                st.dataframe(df, use_container_width=True)
            except Exception:
                for r in rows:
                    st.write(r)
        else:
            st.info("Nessun utente registrato per questo studio.")

        st.markdown("---")
        st.subheader("Aggiungi utente")
        n_utenti = len(rows)
        max_u    = cfg["max_utenti"]
        if n_utenti >= max_u:
            st.warning(f"Limite {max_u} utenti raggiunto per il piano {cfg['nome']}.")
        else:
            with st.form("form_add_user"):
                nu_nome  = st.text_input("Nome")
                nu_cog   = st.text_input("Cognome")
                nu_email = st.text_input("Email")
                nu_ruolo = st.selectbox("Ruolo", ["clinico","segreteria","admin"])
                nu_pwd   = st.text_input("Password temporanea", type="password")
                if st.form_submit_button("➕ Aggiungi"):
                    if all([nu_nome, nu_email, nu_pwd]):
                        ok = crea_utente(meta_conn, studio_id, nu_email,
                                         nu_nome, nu_cog, nu_pwd, nu_ruolo)
                        if ok:
                            st.success(f"Utente {nu_email} creato.")
                            st.rerun()
                    else:
                        st.error("Compila tutti i campi.")

    with tab_moduli:
        moduli = moduli_attivi(piano)
        st.markdown(f"**{len(moduli)} moduli abilitati** con il piano {cfg['nome']}:")
        for modulo in moduli:
            sezioni = MODULO_SEZIONE.get(modulo, [])
            etichette = ", ".join(sezioni) if sezioni else modulo
            st.markdown(f"✅ **{modulo}** → {etichette}")
        non_attivi = [m for m in MODULO_SEZIONE if m not in moduli]
        if non_attivi:
            st.markdown("---")
            st.markdown("**Moduli non inclusi nel piano attuale:**")
            for m in non_attivi:
                st.markdown(f"🔒 _{m}_")
            st.info("Fai l'upgrade del piano per sbloccarli.")


# ══════════════════════════════════════════════════════════════════════
#  FILTRO MENU IN BASE AL PIANO
# ══════════════════════════════════════════════════════════════════════

def filtra_sezioni_per_piano(sezioni: list[str], piano: str) -> list[str]:
    """
    Dato l'elenco completo delle sezioni del menu e il piano dello studio,
    ritorna solo le sezioni abilitate.

    Uso in app_menu.py → build_sections():
        from modules.saas_tenant import filtra_sezioni_per_piano
        sezioni = filtra_sezioni_per_piano(sezioni, st.session_state.get("piano", "base"))
    """
    abilitate = sezioni_abilitate(piano)
    # Sezioni sempre visibili indipendentemente dal piano
    sempre_visibili = ["Pazienti", "Dashboard incassi",
                       " Privacy & Consensi (PDF)"]
    return [s for s in sezioni
            if s in abilitate or any(v in s for v in sempre_visibili)]
