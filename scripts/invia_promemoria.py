#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/invia_promemoria.py

Esecuzione AUTONOMA dei promemoria eventi (finestre 48h / 24h).
Pensata per girare dentro GitHub Actions, SENZA usare Streamlit come server:
si collega direttamente al database PostgreSQL (OVH) e a Gmail (SMTP),
riutilizzando la stessa logica del gestionale (processa_promemoria_automatici).

Le credenziali vengono lette da .streamlit/secrets.toml, che il workflow GitHub
scrive a runtime a partire dal secret di repository STREAMLIT_SECRETS.
Questo bypassa completamente il problema dell'app Streamlit privata:
non c'è nessuna pagina web da raggiungere, è solo Python che parla col DB e con l'SMTP.

Uso:
    python scripts/invia_promemoria.py
    DRY_RUN=1 python scripts/invia_promemoria.py   # prova senza inviare nulla

Exit code:
    0  -> tutto ok (anche se "nessun promemoria da inviare")
    1  -> ci sono stati errori applicativi durante l'elaborazione
    2  -> errore di configurazione / connessione DB (non è partito niente)
"""
from __future__ import annotations

import os
import sys
import traceback

# Mette la root del repo sul path, così "import modules..." funziona
# (lo script sta in scripts/, la root è la cartella superiore).
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

SECRETS_PATH = os.path.join(ROOT, ".streamlit", "secrets.toml")


def _load_secrets_toml() -> dict:
    """Legge .streamlit/secrets.toml con la libreria standard tomllib (Python 3.11+)."""
    try:
        import tomllib  # stdlib da Python 3.11
    except Exception:
        print("ERRORE: serve Python 3.11+ (tomllib non disponibile).", flush=True)
        return {}
    if not os.path.exists(SECRETS_PATH):
        print(f"ERRORE: secrets non trovato in {SECRETS_PATH}", flush=True)
        return {}
    try:
        with open(SECRETS_PATH, "rb") as f:
            return tomllib.load(f)
    except Exception as e:
        print(f"ERRORE lettura secrets.toml: {e}", flush=True)
        return {}


def _database_url(secrets: dict) -> str:
    """Ricava la stringa di connessione: [db].DATABASE_URL, poi DATABASE_URL root, poi env."""
    db = secrets.get("db", {}) if isinstance(secrets, dict) else {}
    if isinstance(db, dict):
        for k in ("DATABASE_URL", "database_url", "url", "URL"):
            v = db.get(k)
            if v:
                return str(v).strip().strip('"').strip("'")
    for k in ("DATABASE_URL", "database_url"):
        v = secrets.get(k)
        if v:
            return str(v).strip().strip('"').strip("'")
    return (os.getenv("DATABASE_URL") or "").strip()


def main() -> int:
    dry_run = os.getenv("DRY_RUN", "").strip().lower() in ("1", "true", "yes", "y")
    if dry_run:
        print(">>> MODALITA' DRY RUN: non invio realmente, mostro solo cosa farei.", flush=True)

    secrets = _load_secrets_toml()
    if not secrets:
        return 2

    url = _database_url(secrets)
    if not url:
        print("ERRORE: DATABASE_URL non trovato nei secrets. "
              "Controlla che il secret STREAMLIT_SECRETS contenga [db] DATABASE_URL.", flush=True)
        return 2
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]

    # --- Connessione diretta al DB ---
    try:
        import psycopg2
        import psycopg2.extras
        conn = psycopg2.connect(
            url,
            cursor_factory=psycopg2.extras.DictCursor,  # come nel gestionale
            connect_timeout=15,
            options="-c statement_timeout=60000",
        )
        conn.autocommit = False  # la logica fa commit espliciti
    except Exception as e:
        print(f"ERRORE connessione DB: {e}", flush=True)
        return 2

    print("Connessione DB OK. Avvio elaborazione promemoria...", flush=True)

    # --- Elaborazione (riusa la logica del gestionale) ---
    try:
        from modules.eventi.promemoria_eventi import processa_promemoria_automatici
        report = processa_promemoria_automatici(conn, dry_run=dry_run)
    except Exception as e:
        print(f"ERRORE esecuzione promemoria: {e}", flush=True)
        traceback.print_exc()
        try:
            conn.rollback()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass
        return 1
    finally:
        try:
            conn.commit()  # belt & suspenders: la logica committa già da sola
        except Exception:
            pass

    try:
        conn.close()
    except Exception:
        pass

    # --- Report ---
    eventi = report.get("eventi_processati", 0)
    inviate = report.get("email_inviate", 0)
    fallite = report.get("email_fallite", 0)
    errori = report.get("errori", []) or []
    dettaglio = report.get("dettaglio", []) or []

    print("---------- REPORT ----------", flush=True)
    print(f"Eventi processati : {eventi}", flush=True)
    print(f"Email inviate     : {inviate}", flush=True)
    print(f"Email fallite     : {fallite}", flush=True)
    if dettaglio:
        print("Dettaglio:", flush=True)
        for d in dettaglio:
            print(f"  - {d}", flush=True)
    else:
        print("Nessun promemoria da inviare in questo momento.", flush=True)
    if errori:
        print("ERRORI:", flush=True)
        for err in errori:
            print(f"  ! {err}", flush=True)
    # Riga machine-readable (utile nei log Actions)
    print(f"CRON_RESULT eventi={eventi} inviate={inviate} fallite={fallite}", flush=True)
    print("----------------------------", flush=True)

    # Fallisce il job SOLO in caso di errori applicativi veri.
    # Le singole email fallite vengono segnalate ma non fanno fallire tutto.
    if errori:
        return 1
    if fallite and not inviate:
        # tutte le email tentate sono fallite -> qualcosa non va (es. SMTP)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
