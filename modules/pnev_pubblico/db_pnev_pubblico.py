# -*- coding: utf-8 -*-
"""
modules/pnev_pubblico/db_pnev_pubblico.py

Strato dati del percorso pubblico MAPS-CLEAR (pnev.it) dentro il gestionale
The Organism. — MILESTONE 2

Tabelle:
  pnev_pubblico_utenti           anagrafica utenti pubblici (riusabile per altri lead magnet)
  pnev_pubblico_maps_clear       record percorso (orecchio dominante, test LI, giorno, stato)
  pnev_pubblico_questionari_pre  questionario baseline (12 domande, JSONB)
  pnev_pubblico_questionari_post questionario finale (JSONB)
  pnev_pubblico_sessioni         sessioni giornaliere 1-7 (auto-val pre/post, comfort, beneficio)
  pnev_pubblico_magic_links      token di accesso via email (riutilizzabile fino a scadenza)

Convenzioni rispettate (come db_gamecenter):
- connessione passata dal chiamante (conn = get_connection())
- multi-tenant RLS: studio_id con DEFAULT current_setting('app.current_studio', true)
  + ENABLE/FORCE ROW LEVEL SECURITY + policy USING/WITH CHECK
- placeholder psycopg2 %s, BIGSERIAL, TEXT, TIMESTAMPTZ, timezone Europe/Rome lato lettura
- self-init idempotente: init_pnev_pubblico_db(conn) si può chiamare a ogni avvio
- JSONB via json.dumps(..., ensure_ascii=False)
"""

import json
import secrets

# Validità del magic link: 9 giorni (7 del percorso + margine).
# Il token resta riutilizzabile fino alla scadenza: il paziente rientra
# ogni giorno dallo stesso link ricevuto via email.
MAGIC_LINK_VALIDITA = "9 days"

MODALITA = {
    "base":   {"nome": "Base",   "delay_ms": 50},
    "attiva": {"nome": "Attiva", "delay_ms": 75},
    "focus":  {"nome": "Focus",  "delay_ms": 100},
}


# ═══════════════════════════════════════════════════════════════
# SELF-INIT
# ═══════════════════════════════════════════════════════════════

def init_pnev_pubblico_db(conn):
    """Crea le 6 tabelle pnev_pubblico_* con RLS multi-tenant. Idempotente."""
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS pnev_pubblico_utenti (
            id              BIGSERIAL PRIMARY KEY,
            studio_id       BIGINT      NOT NULL DEFAULT current_setting('app.current_studio', true)::bigint,
            nome            TEXT        NOT NULL,
            email           TEXT        NOT NULL,
            eta             INTEGER,
            mano            TEXT,
            origine         TEXT        NOT NULL DEFAULT 'maps_clear',
            gdpr_accettato  BOOLEAN     NOT NULL DEFAULT FALSE,
            gdpr_data       TIMESTAMPTZ,
            creato_il       TIMESTAMPTZ NOT NULL DEFAULT now(),
            aggiornato_il   TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE (studio_id, email, origine)
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS pnev_pubblico_maps_clear (
            id                  BIGSERIAL PRIMARY KEY,
            studio_id           BIGINT      NOT NULL DEFAULT current_setting('app.current_studio', true)::bigint,
            utente_id           BIGINT      NOT NULL REFERENCES pnev_pubblico_utenti(id) ON DELETE CASCADE,
            orecchio_dominante  CHAR(1)     CHECK (orecchio_dominante IN ('R','L')),
            test_li             NUMERIC,
            test_dettaglio      JSONB,
            giorno_corrente     INTEGER     NOT NULL DEFAULT 1 CHECK (giorno_corrente BETWEEN 1 AND 8),
            stato               TEXT        NOT NULL DEFAULT 'attivo'
                                CHECK (stato IN ('attivo','completato','abbandonato')),
            iniziato_il         TIMESTAMPTZ NOT NULL DEFAULT now(),
            completato_il       TIMESTAMPTZ,
            creato_il           TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE (utente_id)
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS pnev_pubblico_questionari_pre (
            id          BIGSERIAL PRIMARY KEY,
            studio_id   BIGINT      NOT NULL DEFAULT current_setting('app.current_studio', true)::bigint,
            utente_id   BIGINT      NOT NULL REFERENCES pnev_pubblico_utenti(id) ON DELETE CASCADE,
            risposte    JSONB       NOT NULL,
            creato_il   TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE (utente_id)
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS pnev_pubblico_questionari_post (
            id          BIGSERIAL PRIMARY KEY,
            studio_id   BIGINT      NOT NULL DEFAULT current_setting('app.current_studio', true)::bigint,
            utente_id   BIGINT      NOT NULL REFERENCES pnev_pubblico_utenti(id) ON DELETE CASCADE,
            risposte    JSONB       NOT NULL,
            creato_il   TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE (utente_id)
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS pnev_pubblico_sessioni (
            id              BIGSERIAL PRIMARY KEY,
            studio_id       BIGINT      NOT NULL DEFAULT current_setting('app.current_studio', true)::bigint,
            utente_id       BIGINT      NOT NULL REFERENCES pnev_pubblico_utenti(id) ON DELETE CASCADE,
            giorno          INTEGER     NOT NULL CHECK (giorno BETWEEN 1 AND 7),
            data_sessione   TIMESTAMPTZ NOT NULL DEFAULT now(),
            modalita        TEXT,
            delay_ms        INTEGER,
            orecchio        CHAR(1),
            fluency_pre     INTEGER     CHECK (fluency_pre BETWEEN 1 AND 10),
            fluency_post    INTEGER     CHECK (fluency_post BETWEEN 1 AND 10),
            comfort         INTEGER     CHECK (comfort BETWEEN 1 AND 10),
            beneficio       INTEGER     CHECK (beneficio BETWEEN 1 AND 10),
            note            TEXT,
            durate_blocchi  JSONB,
            creato_il       TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE (utente_id, giorno)
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS pnev_pubblico_magic_links (
            id          BIGSERIAL PRIMARY KEY,
            studio_id   BIGINT      NOT NULL DEFAULT current_setting('app.current_studio', true)::bigint,
            utente_id   BIGINT      NOT NULL REFERENCES pnev_pubblico_utenti(id) ON DELETE CASCADE,
            token       TEXT        NOT NULL UNIQUE,
            scade_il    TIMESTAMPTZ NOT NULL,
            usato_il    TIMESTAMPTZ,
            creato_il   TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS ix_pnev_pubblico_utenti_email
        ON pnev_pubblico_utenti (email);
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS ix_pnev_pubblico_sessioni_utente
        ON pnev_pubblico_sessioni (utente_id, giorno);
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS ix_pnev_pubblico_magic_links_token
        ON pnev_pubblico_magic_links (token);
    """)

    # RLS come sulle altre tabelle del gestionale
    tabelle = [
        "pnev_pubblico_utenti",
        "pnev_pubblico_maps_clear",
        "pnev_pubblico_questionari_pre",
        "pnev_pubblico_questionari_post",
        "pnev_pubblico_sessioni",
        "pnev_pubblico_magic_links",
    ]
    for t in tabelle:
        cur.execute(f"ALTER TABLE {t} ENABLE ROW LEVEL SECURITY;")
        cur.execute(f"ALTER TABLE {t} FORCE ROW LEVEL SECURITY;")
        cur.execute(f"""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_policies
                    WHERE tablename = '{t}' AND policyname = '{t}_studio'
                ) THEN
                    CREATE POLICY {t}_studio ON {t}
                        USING      (studio_id = current_setting('app.current_studio', true)::bigint)
                        WITH CHECK (studio_id = current_setting('app.current_studio', true)::bigint);
                END IF;
            END $$;
        """)

    conn.commit()


# ═══════════════════════════════════════════════════════════════
# UTENTI
# ═══════════════════════════════════════════════════════════════

def crea_utente(conn, nome, email, eta=None, mano=None, gdpr=True):
    """
    Crea (o aggiorna) un utente pubblico e il suo record percorso.
    Ritorna l'id utente. studio_id lo mette il DEFAULT dalla connessione (RLS).
    """
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO pnev_pubblico_utenti (nome, email, eta, mano, gdpr_accettato, gdpr_data)
        VALUES (%s, lower(%s), %s, %s, %s, now())
        ON CONFLICT (studio_id, email, origine) DO UPDATE
            SET nome = EXCLUDED.nome,
                eta = EXCLUDED.eta,
                mano = EXCLUDED.mano,
                aggiornato_il = now()
        RETURNING id
    """, (nome, email, eta, mano, gdpr))
    utente_id = cur.fetchone()[0]
    cur.execute("""
        INSERT INTO pnev_pubblico_maps_clear (utente_id)
        VALUES (%s)
        ON CONFLICT (utente_id) DO NOTHING
    """, (utente_id,))
    conn.commit()
    return utente_id


def get_utente_by_email(conn, email):
    """Utente + stato percorso per email (o None)."""
    cur = conn.cursor()
    cur.execute("""
        SELECT u.id, u.nome, u.email, u.eta, u.mano, u.gdpr_accettato, u.creato_il,
               mc.orecchio_dominante, mc.test_li, mc.giorno_corrente, mc.stato
        FROM pnev_pubblico_utenti u
        LEFT JOIN pnev_pubblico_maps_clear mc ON mc.utente_id = u.id
        WHERE u.email = lower(%s) AND u.origine = 'maps_clear'
    """, (email,))
    return cur.fetchone()


def get_utente_by_id(conn, utente_id):
    """Utente + stato percorso per id (o None)."""
    cur = conn.cursor()
    cur.execute("""
        SELECT u.id, u.nome, u.email, u.eta, u.mano, u.gdpr_accettato, u.creato_il,
               mc.orecchio_dominante, mc.test_li, mc.test_dettaglio,
               mc.giorno_corrente, mc.stato
        FROM pnev_pubblico_utenti u
        LEFT JOIN pnev_pubblico_maps_clear mc ON mc.utente_id = u.id
        WHERE u.id = %s
    """, (utente_id,))
    return cur.fetchone()


# ═══════════════════════════════════════════════════════════════
# PERCORSO MAPS-CLEAR
# ═══════════════════════════════════════════════════════════════

def set_orecchio_dominante(conn, utente_id, orecchio, test_li=None, test_dettaglio=None):
    """orecchio: 'R' o 'L'. test_dettaglio: dict -> JSONB ({nR,nL,nC,nU,byFreq,date})."""
    cur = conn.cursor()
    cur.execute("""
        UPDATE pnev_pubblico_maps_clear
        SET orecchio_dominante = %s,
            test_li = %s,
            test_dettaglio = %s
        WHERE utente_id = %s
    """, (
        orecchio, test_li,
        json.dumps(test_dettaglio, ensure_ascii=False) if test_dettaglio is not None else None,
        utente_id,
    ))
    conn.commit()


def aggiorna_stato_percorso(conn, utente_id):
    """Ricalcola giorno_corrente e stato dalle sessioni salvate. Ritorna (giorno, stato)."""
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM pnev_pubblico_sessioni WHERE utente_id = %s", (utente_id,))
    fatte = int(cur.fetchone()[0])
    nuovo_giorno = min(fatte + 1, 8)
    stato = "completato" if fatte >= 7 else "attivo"
    cur.execute("""
        UPDATE pnev_pubblico_maps_clear
        SET giorno_corrente = %s,
            stato = %s,
            completato_il = CASE WHEN %s = 'completato' AND completato_il IS NULL
                                 THEN now() ELSE completato_il END
        WHERE utente_id = %s
    """, (nuovo_giorno, stato, stato, utente_id))
    conn.commit()
    return nuovo_giorno, stato


# ═══════════════════════════════════════════════════════════════
# QUESTIONARI
# ═══════════════════════════════════════════════════════════════

def salva_questionario_pre(conn, utente_id, risposte):
    """risposte: dict {q1:.., ... q12:..} -> JSONB."""
    _salva_questionario(conn, "pnev_pubblico_questionari_pre", utente_id, risposte)


def salva_questionario_post(conn, utente_id, risposte):
    _salva_questionario(conn, "pnev_pubblico_questionari_post", utente_id, risposte)
    aggiorna_stato_percorso(conn, utente_id)


def _salva_questionario(conn, tabella, utente_id, risposte):
    cur = conn.cursor()
    cur.execute(f"""
        INSERT INTO {tabella} (utente_id, risposte)
        VALUES (%s, %s)
        ON CONFLICT (utente_id) DO UPDATE
            SET risposte = EXCLUDED.risposte, creato_il = now()
    """, (utente_id, json.dumps(risposte, ensure_ascii=False)))
    conn.commit()


def get_questionari(conn, utente_id):
    """Ritorna {'pre': row|None, 'post': row|None}."""
    cur = conn.cursor()
    out = {}
    for chiave, tab in (("pre", "pnev_pubblico_questionari_pre"),
                        ("post", "pnev_pubblico_questionari_post")):
        cur.execute(f"SELECT risposte, creato_il FROM {tab} WHERE utente_id = %s", (utente_id,))
        out[chiave] = cur.fetchone()
    return out


# ═══════════════════════════════════════════════════════════════
# SESSIONI GIORNALIERE
# ═══════════════════════════════════════════════════════════════

def salva_sessione(conn, utente_id, giorno, modalita, delay_ms, orecchio,
                   fluency_pre, fluency_post, comfort, beneficio,
                   note=None, durate_blocchi=None):
    """
    Salva (o sovrascrive) la sessione del giorno. Ritorna (giorno_corrente, stato)
    aggiornati. durate_blocchi: lista [sec_b1, sec_b2, sec_b3] -> JSONB.
    """
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO pnev_pubblico_sessioni
            (utente_id, giorno, modalita, delay_ms, orecchio,
             fluency_pre, fluency_post, comfort, beneficio, note, durate_blocchi)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (utente_id, giorno) DO UPDATE
            SET modalita = EXCLUDED.modalita,
                delay_ms = EXCLUDED.delay_ms,
                orecchio = EXCLUDED.orecchio,
                fluency_pre = EXCLUDED.fluency_pre,
                fluency_post = EXCLUDED.fluency_post,
                comfort = EXCLUDED.comfort,
                beneficio = EXCLUDED.beneficio,
                note = EXCLUDED.note,
                durate_blocchi = EXCLUDED.durate_blocchi,
                data_sessione = now()
    """, (
        utente_id, giorno, modalita, delay_ms, orecchio,
        fluency_pre, fluency_post, comfort, beneficio, note,
        json.dumps(durate_blocchi, ensure_ascii=False) if durate_blocchi is not None else None,
    ))
    conn.commit()
    return aggiorna_stato_percorso(conn, utente_id)


def get_sessioni(conn, utente_id):
    """Tutte le sessioni del percorso, in ordine di giorno."""
    cur = conn.cursor()
    cur.execute("""
        SELECT id, giorno, data_sessione, modalita, delay_ms, orecchio,
               fluency_pre, fluency_post, comfort, beneficio, note, durate_blocchi
        FROM pnev_pubblico_sessioni
        WHERE utente_id = %s
        ORDER BY giorno
    """, (utente_id,))
    return cur.fetchall()


# ═══════════════════════════════════════════════════════════════
# MAGIC LINKS
# ═══════════════════════════════════════════════════════════════

def crea_magic_link(conn, utente_id):
    """Genera un token sicuro valido 9 giorni. Ritorna il token (da mettere nell'URL email)."""
    token = secrets.token_urlsafe(32)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO pnev_pubblico_magic_links (utente_id, token, scade_il)
        VALUES (%s, %s, now() + interval %s)
    """, (utente_id, token, MAGIC_LINK_VALIDITA))
    conn.commit()
    return token


def valida_magic_link(conn, token):
    """
    Se il token è valido e non scaduto ritorna utente_id (e aggiorna usato_il),
    altrimenti None. Il token resta riutilizzabile fino alla scadenza:
    il paziente rientra ogni giorno dallo stesso link.
    """
    cur = conn.cursor()
    cur.execute("""
        UPDATE pnev_pubblico_magic_links
        SET usato_il = now()
        WHERE token = %s AND scade_il > now()
        RETURNING utente_id
    """, (token,))
    row = cur.fetchone()
    conn.commit()
    return row[0] if row else None


# ═══════════════════════════════════════════════════════════════
# ADMIN (base per MILESTONE 5)
# ═══════════════════════════════════════════════════════════════

def admin_lista_utenti(conn):
    """Panoramica utenti per il modulo admin del gestionale."""
    cur = conn.cursor()
    cur.execute("""
        SELECT u.id, u.nome, u.email, u.eta, u.mano, u.creato_il,
               mc.orecchio_dominante, mc.test_li, mc.giorno_corrente, mc.stato,
               (SELECT count(*) FROM pnev_pubblico_sessioni s
                WHERE s.utente_id = u.id) AS sessioni_fatte,
               (SELECT round(avg(s.fluency_post - s.fluency_pre), 2)
                FROM pnev_pubblico_sessioni s
                WHERE s.utente_id = u.id) AS delta_fluency_medio
        FROM pnev_pubblico_utenti u
        LEFT JOIN pnev_pubblico_maps_clear mc ON mc.utente_id = u.id
        WHERE u.origine = 'maps_clear'
        ORDER BY u.creato_il DESC
    """)
    return cur.fetchall()
