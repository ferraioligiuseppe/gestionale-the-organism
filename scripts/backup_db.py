#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/backup_db.py

Backup AUTOMATICO e CIFRATO del database PostgreSQL su storage S3-compatibile
(Cloudflare R2). Pensato per girare dentro GitHub Actions, in modo indipendente
dal provider del database (OVH) e dall'app Streamlit.

Cosa fa, ad ogni esecuzione:
  1. pg_dump completo in formato custom compresso (-Fc), senza owner/privilegi
     (così il dump è ripristinabile anche su un'altra installazione → utile per
     migrazioni e per replicare l'ambiente di un cliente).
  2. Cifratura AES-256 con passphrase (openssl), se BACKUP_PASSPHRASE è impostata.
  3. Upload su R2 sotto backup/daily/ con data e ora nel nome.
  4. Se è domenica → copia anche in backup/weekly/.
     Se è il primo del mese → copia anche in backup/monthly/.
  5. Pulizia: tiene gli ultimi N di ogni livello, cancella i più vecchi.

Le credenziali (DATABASE_URL e sezione [storage]) vengono lette da
.streamlit/secrets.toml, scritto a runtime dal workflow a partire dal
secret di repository STREAMLIT_SECRETS. La passphrase arriva dal secret
BACKUP_PASSPHRASE via variabile d'ambiente.

Variabili d'ambiente opzionali (con default):
  KEEP_DAILY=14   KEEP_WEEKLY=8   KEEP_MONTHLY=12
  DB_LABEL=prod   (etichetta nel nome file)

Exit code:
  0  ok
  2  errore di configurazione / dump / connessione (niente è stato caricato)
"""
from __future__ import annotations

import os
import sys
import subprocess
import tempfile
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECRETS_PATH = os.path.join(ROOT, ".streamlit", "secrets.toml")
ROME = ZoneInfo("Europe/Rome")

KEEP_DAILY = int(os.getenv("KEEP_DAILY", "14"))
KEEP_WEEKLY = int(os.getenv("KEEP_WEEKLY", "8"))
KEEP_MONTHLY = int(os.getenv("KEEP_MONTHLY", "12"))
DB_LABEL = os.getenv("DB_LABEL", "prod")

PREFIX_DAILY = "backup/daily/"
PREFIX_WEEKLY = "backup/weekly/"
PREFIX_MONTHLY = "backup/monthly/"


def log(msg: str) -> None:
    print(msg, flush=True)


def load_secrets() -> dict:
    try:
        import tomllib
    except Exception:
        log("ERRORE: serve Python 3.11+ (tomllib).")
        return {}
    if not os.path.exists(SECRETS_PATH):
        log(f"ERRORE: secrets non trovato in {SECRETS_PATH}")
        return {}
    try:
        with open(SECRETS_PATH, "rb") as f:
            return tomllib.load(f)
    except Exception as e:
        log(f"ERRORE lettura secrets.toml: {e}")
        return {}


def database_url(secrets: dict) -> str:
    db = secrets.get("db", {})
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


def storage_cfg(secrets: dict) -> dict:
    cfg = secrets.get("storage", {})
    return cfg if isinstance(cfg, dict) else {}


def s3_client(cfg: dict):
    import boto3
    endpoint = cfg.get("S3_ENDPOINT_URL")
    if endpoint and not str(endpoint).startswith(("http://", "https://")):
        endpoint = "https://" + str(endpoint)
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        region_name=cfg.get("S3_REGION") or "auto",
        aws_access_key_id=cfg.get("S3_ACCESS_KEY"),
        aws_secret_access_key=cfg.get("S3_SECRET_KEY"),
    )


def run_pg_dump(url: str, out_path: str) -> bool:
    """Esegue pg_dump in formato custom compresso. True se ok."""
    cmd = [
        "pg_dump",
        "--format=custom",
        "--no-owner",
        "--no-acl",
        "--file", out_path,
        "--dbname", url,
    ]
    log("Avvio pg_dump...")
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
    except FileNotFoundError:
        log("ERRORE: pg_dump non trovato. Il workflow deve installare postgresql-client.")
        return False
    except subprocess.TimeoutExpired:
        log("ERRORE: pg_dump è andato in timeout (oltre 60 min).")
        return False
    if proc.returncode != 0:
        log(f"ERRORE pg_dump (exit {proc.returncode}):")
        log(proc.stderr.strip()[:4000])
        return False
    size = os.path.getsize(out_path) if os.path.exists(out_path) else 0
    if size < 1024:
        log(f"ERRORE: dump sospettosamente piccolo ({size} byte). Interrompo per sicurezza.")
        return False
    log(f"pg_dump OK ({size/1024/1024:.2f} MB).")
    return True


def encrypt(in_path: str, out_path: str, passphrase: str) -> bool:
    cmd = [
        "openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-iter", "200000", "-salt",
        "-in", in_path, "-out", out_path, "-pass", "env:BACKUP_PASSPHRASE",
    ]
    env = dict(os.environ)
    env["BACKUP_PASSPHRASE"] = passphrase
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=600)
    except Exception as e:
        log(f"ERRORE cifratura: {e}")
        return False
    if proc.returncode != 0:
        log(f"ERRORE openssl (exit {proc.returncode}): {proc.stderr.strip()[:2000]}")
        return False
    log("Cifratura AES-256 OK.")
    return True


def prune(s3, bucket: str, prefix: str, keep: int) -> None:
    """Tiene i 'keep' oggetti più recenti sotto prefix, cancella i più vecchi."""
    try:
        objs = []
        token = None
        while True:
            kwargs = {"Bucket": bucket, "Prefix": prefix}
            if token:
                kwargs["ContinuationToken"] = token
            resp = s3.list_objects_v2(**kwargs)
            for o in resp.get("Contents", []):
                # ignora eventuali "cartelle" vuote
                if not o["Key"].endswith("/"):
                    objs.append(o)
            if resp.get("IsTruncated"):
                token = resp.get("NextContinuationToken")
            else:
                break
        # il nome contiene il timestamp → ordino per Key (equivalente a cronologico)
        objs.sort(key=lambda o: o["Key"])
        da_cancellare = objs[:-keep] if keep > 0 else []
        for o in da_cancellare:
            s3.delete_object(Bucket=bucket, Key=o["Key"])
            log(f"  pulizia: rimosso {o['Key']}")
        log(f"{prefix}: {len(objs)} backup, tenuti {min(len(objs), keep)}, rimossi {len(da_cancellare)}.")
    except Exception as e:
        log(f"ATTENZIONE: pulizia di {prefix} non riuscita: {e}")


def main() -> int:
    now = datetime.now(ROME)
    stamp = now.strftime("%Y%m%d_%H%M%S")
    base_name = f"the_organism_{DB_LABEL}_{stamp}.dump"

    secrets = load_secrets()
    if not secrets:
        return 2

    url = database_url(secrets)
    if not url:
        log("ERRORE: DATABASE_URL non trovato nei secrets ([db].DATABASE_URL).")
        return 2
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]

    cfg = storage_cfg(secrets)
    bucket = cfg.get("S3_BUCKET")
    if not bucket or not cfg.get("S3_ENDPOINT_URL") or not cfg.get("S3_ACCESS_KEY"):
        log("ERRORE: configurazione [storage] incompleta (servono S3_ENDPOINT_URL, S3_BUCKET, S3_ACCESS_KEY, S3_SECRET_KEY).")
        return 2

    passphrase = os.getenv("BACKUP_PASSPHRASE", "").strip()

    tmpdir = tempfile.mkdtemp(prefix="dbbackup_")
    dump_path = os.path.join(tmpdir, base_name)

    # 1) dump
    if not run_pg_dump(url, dump_path):
        return 2

    # 2) cifratura (se passphrase presente)
    if passphrase:
        enc_path = dump_path + ".enc"
        if not encrypt(dump_path, enc_path, passphrase):
            return 2
        upload_path = enc_path
        key_name = base_name + ".enc"
    else:
        log("ATTENZIONE: BACKUP_PASSPHRASE non impostata → backup NON cifrato.")
        upload_path = dump_path
        key_name = base_name

    # 3) upload su daily/
    try:
        s3 = s3_client(cfg)
        daily_key = PREFIX_DAILY + key_name
        s3.upload_file(upload_path, bucket, daily_key)
        log(f"Upload OK → s3://{bucket}/{daily_key}")
    except Exception as e:
        log(f"ERRORE upload su R2: {e}")
        return 2

    # 4) copie settimanale / mensile (copia server-side, niente ri-upload)
    try:
        if now.weekday() == 6:  # domenica
            wk = PREFIX_WEEKLY + key_name
            s3.copy_object(Bucket=bucket, CopySource={"Bucket": bucket, "Key": daily_key}, Key=wk)
            log(f"Copia settimanale → s3://{bucket}/{wk}")
        if now.day == 1:
            mo = PREFIX_MONTHLY + key_name
            s3.copy_object(Bucket=bucket, CopySource={"Bucket": bucket, "Key": daily_key}, Key=mo)
            log(f"Copia mensile → s3://{bucket}/{mo}")
    except Exception as e:
        log(f"ATTENZIONE: copia settimanale/mensile non riuscita: {e}")

    # 5) pulizia retention
    log("--- Pulizia retention ---")
    prune(s3, bucket, PREFIX_DAILY, KEEP_DAILY)
    prune(s3, bucket, PREFIX_WEEKLY, KEEP_WEEKLY)
    prune(s3, bucket, PREFIX_MONTHLY, KEEP_MONTHLY)

    log(f"BACKUP_RESULT ok file={key_name} cifrato={'si' if passphrase else 'no'}")
    log("Backup completato con successo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
