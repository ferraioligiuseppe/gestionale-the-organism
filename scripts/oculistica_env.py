#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prepara e controlla le impostazioni del gestionale oculistica sul server OVH.

  oculistica_env.py crea  SECRETS.toml  FILE.env
      Legge i Secrets dell'app oculistica (copiati da Streamlit Cloud) e la password
      d'accesso (variabile OCULISTICA_PASSWORD) e scrive il file che il servizio usa.
  oculistica_env.py prova-db  FILE.env
      Controlla che il database risponda, prima di accendere il servizio.

Non stampa mai password o indirizzi del database.
"""
import os
import sys

TABELLE = ("db", "database", "postgres", "postgresql", "connections")
NOMI = ("DATABASE_URL", "database_url", "url", "URL")


def _carica_toml(percorso):
    testo = open(percorso, "rb").read()
    try:
        import tomllib
        return tomllib.loads(testo.decode("utf-8"))
    except ModuleNotFoundError:
        import toml
        return toml.loads(testo.decode("utf-8"))


def trova_database_url(dati):
    """Prima in cima al file (come lo legge l'app su Streamlit Cloud), poi nelle sezioni note."""
    for k in NOMI[:2]:
        if isinstance(dati.get(k), str) and dati[k].strip():
            return dati[k].strip()
    for t in TABELLE:
        sez = dati.get(t)
        if isinstance(sez, dict):
            for k in NOMI:
                if isinstance(sez.get(k), str) and sez[k].strip():
                    return sez[k].strip()
            for sotto in sez.values():          # es. [connections.postgresql] url = "..."
                if isinstance(sotto, dict):
                    for k in NOMI:
                        if isinstance(sotto.get(k), str) and sotto[k].strip():
                            return sotto[k].strip()
    return ""


def riga_env(nome, valore):
    """Riga per un EnvironmentFile di systemd. Ritorna None se il valore non si puo' scrivere."""
    if "\n" in valore or "\r" in valore:
        return None
    if "'" not in valore:
        return "%s='%s'" % (nome, valore)          # tra apici singoli tutto e' letterale
    if '"' not in valore and "\\" not in valore:
        return '%s="%s"' % (nome, valore)
    return None


def leggi_env(percorso):
    out = {}
    for riga in open(percorso, encoding="utf-8"):
        riga = riga.rstrip("\n")
        if not riga or riga.startswith("#") or "=" not in riga:
            continue
        k, v = riga.split("=", 1)
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"":
            v = v[1:-1]
        out[k] = v
    return out


def crea(secrets_toml, file_env):
    try:
        dati = _carica_toml(secrets_toml)
    except Exception as e:
        print("ERRORE: i Secrets dell'oculistica non si leggono (%s)." % type(e).__name__)
        return 1
    url = trova_database_url(dati)
    if not url:
        print("ERRORE: nei Secrets dell'oculistica non trovo DATABASE_URL.")
        return 1
    if not url.lower().startswith(("postgres://", "postgresql://")):
        print("ERRORE: DATABASE_URL non è un indirizzo PostgreSQL.")
        return 1
    pw = os.environ.get("OCULISTICA_PASSWORD", "").strip()
    if len(pw) < 8:
        print("ERRORE: la password d'accesso (OCULISTICA_PASSWORD) deve avere almeno 8 caratteri.")
        return 1
    righe = [riga_env("DATABASE_URL", url), riga_env("OCULISTICA_PASSWORD", pw)]
    if righe[0] is None:
        print("ERRORE: DATABASE_URL contiene caratteri che non posso scrivere.")
        return 1
    if righe[1] is None:
        print("ERRORE: la password non può contenere insieme apici e virgolette. Scegline un'altra.")
        return 1
    fd = os.open(file_env, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write("\n".join(righe) + "\n")
    print("Impostazioni dell'oculistica pronte.")
    return 0


def prova_db(file_env):
    env = leggi_env(file_env)
    url = env.get("DATABASE_URL", "")
    if not url or not env.get("OCULISTICA_PASSWORD"):
        print("ERRORE: impostazioni dell'oculistica incomplete.")
        return 1
    try:
        import psycopg2
        conn = psycopg2.connect(url, connect_timeout=8)
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.fetchone()
        conn.close()
    except Exception as e:
        print("ERRORE: il database dell'oculistica non risponde (%s)." % type(e).__name__)
        return 1
    print("Database dell'oculistica: risponde.")
    return 0


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) == 3 and a[0] == "crea":
        sys.exit(crea(a[1], a[2]))
    if len(a) == 2 and a[0] == "prova-db":
        sys.exit(prova_db(a[1]))
    print(__doc__)
    sys.exit(2)
