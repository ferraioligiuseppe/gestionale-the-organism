# -*- coding: utf-8 -*-
"""
modules/db_portale_famiglia.py
Portale famiglia: login vero (email + password) per vedere le procedure
da fare a casa, con video how-to e feedback (fatto + valutazione 1-5).
"""
import hashlib
import os
import datetime


def _hash_password(password: str, salt: bytes = None):
    if salt is None:
        salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return salt.hex() + ":" + dk.hex()


def _verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, hash_hex = stored.split(":")
        salt = bytes.fromhex(salt_hex)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
        return dk.hex() == hash_hex
    except Exception:
        return False


def init_db(conn):
    cur = conn.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS portale_accessi (
                id              BIGSERIAL PRIMARY KEY,
                paziente_id     BIGINT NOT NULL,
                email           TEXT NOT NULL UNIQUE,
                password_hash   TEXT NOT NULL,
                creato_il       TIMESTAMPTZ NOT NULL DEFAULT now()
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS procedura_video (
                procedura   TEXT PRIMARY KEY,
                video_url   TEXT
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS programma_casa_feedback (
                id              BIGSERIAL PRIMARY KEY,
                paziente_id     BIGINT NOT NULL,
                procedura       TEXT NOT NULL,
                data            DATE NOT NULL,
                fatto           BOOLEAN NOT NULL DEFAULT FALSE,
                valutazione     INT,
                video_bambino_url TEXT,
                creato_il       TIMESTAMPTZ NOT NULL DEFAULT now(),
                UNIQUE (paziente_id, procedura, data)
            );
        """)
        cur.execute("ALTER TABLE programma_casa_feedback ADD COLUMN IF NOT EXISTS video_bambino_url TEXT;")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS portale_otp (
                id              BIGSERIAL PRIMARY KEY,
                email           TEXT NOT NULL,
                codice          TEXT NOT NULL,
                scade_il        TIMESTAMPTZ NOT NULL,
                usato           BOOLEAN NOT NULL DEFAULT FALSE,
                creato_il       TIMESTAMPTZ NOT NULL DEFAULT now()
            );
        """)
        # Senza un limite ai tentativi, sei cifre si indovinano a forza
        # bruta in pochi minuti: il secondo fattore non protegge niente.
        cur.execute("ALTER TABLE portale_otp ADD COLUMN IF NOT EXISTS tentativi INT DEFAULT 0;")
        conn.commit()
    finally:
        try: cur.close()
        except Exception: pass


def set_credenziali(conn, paziente_id, email, password):
    cur = conn.cursor()
    try:
        pw_hash = _hash_password(password)
        cur.execute("""
            INSERT INTO portale_accessi (paziente_id, email, password_hash)
            VALUES (%s, %s, %s)
            ON CONFLICT (email) DO UPDATE SET password_hash = EXCLUDED.password_hash,
                                               paziente_id = EXCLUDED.paziente_id
        """, (paziente_id, email.strip().lower(), pw_hash))
        conn.commit()
        return True
    except Exception:
        try: conn.rollback()
        except Exception: pass
        return False
    finally:
        try: cur.close()
        except Exception: pass


def get_credenziali_paziente(conn, paziente_id):
    cur = conn.cursor()
    try:
        cur.execute("SELECT email FROM portale_accessi WHERE paziente_id=%s", (paziente_id,))
        row = cur.fetchone()
        return row[0] if row else None
    finally:
        try: cur.close()
        except Exception: pass


def login(conn, email, password):
    """Ritorna paziente_id se le credenziali sono corrette, altrimenti None."""
    cur = conn.cursor()
    try:
        cur.execute("SELECT paziente_id, password_hash FROM portale_accessi WHERE email=%s",
                     (email.strip().lower(),))
        row = cur.fetchone()
        if not row:
            return None
        paziente_id, pw_hash = row
        return paziente_id if _verify_password(password, pw_hash) else None
    finally:
        try: cur.close()
        except Exception: pass


def get_video_url(conn, procedura):
    cur = conn.cursor()
    try:
        cur.execute("SELECT video_url FROM procedura_video WHERE procedura=%s", (procedura,))
        row = cur.fetchone()
        return row[0] if row and row[0] else None
    finally:
        try: cur.close()
        except Exception: pass


def set_video_url(conn, procedura, url):
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO procedura_video (procedura, video_url) VALUES (%s, %s)
            ON CONFLICT (procedura) DO UPDATE SET video_url = EXCLUDED.video_url
        """, (procedura, url.strip() if url else None))
        conn.commit()
        return True
    except Exception:
        try: conn.rollback()
        except Exception: pass
        return False
    finally:
        try: cur.close()
        except Exception: pass


def get_programma_corrente(conn, paziente_id):
    """Ultimo programma 'casa' inviato per il paziente (procedure JSONB)."""
    import json
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, protocollo, settimana, procedure, data_assegnazione
            FROM programma_casa
            WHERE paziente_id=%s AND tipo='casa' AND inviato=TRUE
            ORDER BY creato DESC LIMIT 1
        """, (paziente_id,))
        row = cur.fetchone()
        if not row:
            return None
        pid, protocollo, settimana, procedure, data_ass = row
        if isinstance(procedure, str):
            procedure = json.loads(procedure)
        return {"id": pid, "protocollo": protocollo, "settimana": settimana,
                "procedure": procedure or [], "data_assegnazione": data_ass}
    finally:
        try: cur.close()
        except Exception: pass


def salva_feedback(conn, paziente_id, procedura, data, fatto, valutazione, video_url=None):
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO programma_casa_feedback (paziente_id, procedura, data, fatto, valutazione, video_bambino_url)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (paziente_id, procedura, data) DO UPDATE
                SET fatto = EXCLUDED.fatto, valutazione = EXCLUDED.valutazione,
                    video_bambino_url = COALESCE(EXCLUDED.video_bambino_url, programma_casa_feedback.video_bambino_url)
        """, (paziente_id, procedura, data, fatto, valutazione, video_url))
        conn.commit()
        return True
    except Exception:
        try: conn.rollback()
        except Exception: pass
        return False
    finally:
        try: cur.close()
        except Exception: pass


def get_feedback_settimana(conn, paziente_id, data_da, data_a):
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT procedura, data, fatto, valutazione
            FROM programma_casa_feedback
            WHERE paziente_id=%s AND data BETWEEN %s AND %s
            ORDER BY data DESC
        """, (paziente_id, data_da, data_a))
        return cur.fetchall()
    finally:
        try: cur.close()
        except Exception: pass


def get_video_bambino_recenti(conn, paziente_id, giorni=30):
    """Video caricati dal genitore (esecuzione del bambino), più recenti prima —
    da rivedere in studio."""
    cur = conn.cursor()
    try:
        soglia = datetime.date.today() - datetime.timedelta(days=giorni)
        cur.execute("""
            SELECT procedura, data, video_bambino_url, valutazione
            FROM programma_casa_feedback
            WHERE paziente_id=%s AND data >= %s AND video_bambino_url IS NOT NULL
            ORDER BY data DESC
        """, (paziente_id, soglia))
        return cur.fetchall()
    finally:
        try: cur.close()
        except Exception: pass


def get_aderenza_riepilogo(conn, paziente_id, giorni=30):
    """% di procedure segnate 'fatto' negli ultimi N giorni + media valutazione."""
    cur = conn.cursor()
    try:
        soglia = datetime.date.today() - datetime.timedelta(days=giorni)
        cur.execute("""
            SELECT COUNT(*) FILTER (WHERE fatto), COUNT(*), AVG(valutazione)
            FROM programma_casa_feedback
            WHERE paziente_id=%s AND data >= %s
        """, (paziente_id, soglia))
        fatti, totali, media = cur.fetchone()
        pct = round(100 * fatti / totali) if totali else None
        return {"fatti": fatti or 0, "totali": totali or 0, "pct": pct,
                "media_valutazione": round(media, 1) if media else None}
    finally:
        try: cur.close()
        except Exception: pass


# ── Codice via email (OTP), richiesto ad ogni login ──────────────────
MAX_TENTATIVI_OTP = 5


def genera_otp(conn, email):
    """Genera un codice e annulla i precedenti dello stesso indirizzo.

    Prima restavano validi tutti insieme: chiedendo cinque codici se ne
    ottenevano cinque funzionanti, e la finestra di dieci minuti si
    allungava a piacere."""
    import random
    cur = conn.cursor()
    try:
        email = email.strip().lower()
        cur.execute("UPDATE portale_otp SET usato=TRUE WHERE email=%s AND usato=FALSE",
                     (email,))
        # I codici scaduti non servono a nessuno e la tabella cresce a ogni
        # accesso: si buttano qui, senza bisogno di un cron dedicato.
        cur.execute("DELETE FROM portale_otp WHERE scade_il < now() - interval '1 day'")
        codice = f"{random.randint(0, 999999):06d}"
        scade = datetime.datetime.now() + datetime.timedelta(minutes=10)
        cur.execute("INSERT INTO portale_otp (email, codice, scade_il) VALUES (%s, %s, %s)",
                     (email, codice, scade))
        conn.commit()
        return codice
    finally:
        try: cur.close()
        except Exception: pass


def verifica_otp(conn, email, codice):
    """Ritorna (ok, motivo). Il motivo distingue il codice sbagliato dal
    codice scaduto e dai tentativi esauriti: senza, chi sbaglia non sa
    se deve riprovare o richiedere il codice."""
    cur = conn.cursor()
    try:
        email = email.strip().lower()
        cur.execute("""
            SELECT id, codice, tentativi, scade_il > now() AS valido
            FROM portale_otp
            WHERE email=%s AND usato=FALSE
            ORDER BY id DESC LIMIT 1
        """, (email,))
        row = cur.fetchone()
        if not row:
            return False, "Nessun codice attivo: richiedine uno nuovo."
        rid, atteso, tentativi, valido = row
        if not valido:
            return False, "Codice scaduto: richiedine uno nuovo."
        if (tentativi or 0) >= MAX_TENTATIVI_OTP:
            cur.execute("UPDATE portale_otp SET usato=TRUE WHERE id=%s", (rid,))
            conn.commit()
            return False, "Troppi tentativi. Richiedi un codice nuovo."
        if (codice or "").strip() != atteso:
            cur.execute("UPDATE portale_otp SET tentativi=COALESCE(tentativi,0)+1 WHERE id=%s",
                         (rid,))
            conn.commit()
            rimasti = MAX_TENTATIVI_OTP - (tentativi or 0) - 1
            if rimasti <= 0:
                return False, "Troppi tentativi. Richiedi un codice nuovo."
            return False, f"Codice non corretto. Tentativi rimasti: {rimasti}."
        cur.execute("UPDATE portale_otp SET usato=TRUE WHERE id=%s", (rid,))
        conn.commit()
        return True, ""
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        return False, f"Verifica non riuscita: {e}"
    finally:
        try: cur.close()
        except Exception: pass
