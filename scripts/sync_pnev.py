#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/sync_pnev.py

Esecuzione AUTONOMA del sync pazienti pnev.it -> gestionale.
Pensata per girare dentro GitHub Actions, SENZA usare Streamlit come server:
si collega direttamente al database PostgreSQL (OVH) e riusa la stessa logica
del gestionale (processa_sync_pnev): legge gli iscritti MAPS, esclude spam/test,
salta chi c'e' gia' (per email) e importa i nuovi.

Le credenziali (DB + [pnev_wp]) vengono lette da .streamlit/secrets.toml, che il
workflow GitHub scrive a runtime dal secret di repository STREAMLIT_SECRETS.

Uso:
    python scripts/sync_pnev.py
    DRY_RUN=1 python scripts/sync_pnev.py   # prova senza importare nulla

Exit code:
    0  -> ok (anche se "nessun nuovo paziente")
    1  -> errori applicativi durante l'elaborazione
    2  -> errore di configurazione / connessione DB
"""
from __future__ import annotations

import os
import sys
import traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

SECRETS_PATH = os.path.join(ROOT, ".streamlit", "secrets.toml")


def _load_secrets_toml() -> dict:
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
        print(">>> MODALITA' DRY RUN: non importo davvero, mostro solo cosa farei.", flush=True)

    secrets = _load_secrets_toml()
    if not secrets:
        return 2

    url = _database_url(secrets)
    if not url:
        print("ERRORE: DATABASE_URL non trovato nei secrets ([db] DATABASE_URL).", flush=True)
        return 2
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]

    try:
        import psycopg2
        import psycopg2.extras
        conn = psycopg2.connect(
            url,
            cursor_factory=psycopg2.extras.DictCursor,
            connect_timeout=15,
            options="-c statement_timeout=60000",
        )
        conn.autocommit = False
    except Exception as e:
        print(f"ERRORE connessione DB: {e}", flush=True)
        return 2

    print("Connessione DB OK. Avvio sync pazienti pnev.it...", flush=True)

    try:
        from modules.ui_sync_pnev import processa_sync_pnev
        report = processa_sync_pnev(conn, dry_run=dry_run)
    except Exception as e:
        print(f"ERRORE esecuzione sync: {e}", flush=True)
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

    try:
        conn.close()
    except Exception:
        pass

    letti = report.get("letti", 0)
    gia = report.get("gia_presenti", 0)
    esclusi = report.get("esclusi_test", 0)
    importati = report.get("importati", 0)
    errori = report.get("errori", []) or []
    dettaglio = report.get("dettaglio", []) or []

    print("---------- REPORT ----------", flush=True)
    print(f"Letti da MAPS   : {letti}", flush=True)
    print(f"Gia' presenti   : {gia}", flush=True)
    print(f"Esclusi (test)  : {esclusi}", flush=True)
    print(f"Importati       : {importati}", flush=True)
    if dettaglio:
        print("Dettaglio:", flush=True)
        for d in dettaglio:
            print(f"  - {d}", flush=True)
    if errori:
        print("ERRORI:", flush=True)
        for err in errori:
            print(f"  ! {err}", flush=True)
    print(f"CRON_RESULT letti={letti} gia_presenti={gia} "
          f"esclusi_test={esclusi} importati={importati}", flush=True)
    print("----------------------------", flush=True)

    # Se non ha letto NESSUNO ma non ci sono errori, e' sospetto (blocco totale):
    # lo segnalo come errore cosi' te ne accorgi dai log.
    if errori:
        return 1
    if letti == 0:
        print("ATTENZIONE: 0 iscritti letti da pnev.it (possibile blocco).", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
