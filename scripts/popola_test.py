#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/popola_test.py

Aggiunge pazienti finti al database DI TEST per fare prove, SENZA cancellare
nulla di esistente. Sicuro: si rifiuta di girare se il bersaglio non è un DB
di test (il nome deve contenere 'test').

Parametri (variabili d'ambiente, opzionali):
  TEST_DATABASE_URL  -> connessione al DB di test (obbligatoria)
  NUMERO             -> quanti pazienti creare (default 10)
  STUDIO             -> studio_id a cui assegnarli (default 1)
"""
from __future__ import annotations
import os
import re
import sys
import random
from datetime import date

COGNOMI = ["Rossi", "Russo", "Ferrari", "Esposito", "Bianchi", "Romano", "Colombo",
           "Ricci", "Marino", "Greco", "Bruno", "Gallo", "Conti", "De Luca", "Costa",
           "Giordano", "Mancini", "Rizzo", "Lombardi", "Moretti", "Barbieri", "Fontana"]
NOMI_M = ["Luca", "Marco", "Giuseppe", "Antonio", "Francesco", "Matteo", "Alessandro",
          "Davide", "Simone", "Lorenzo", "Andrea", "Gabriele", "Riccardo", "Tommaso"]
NOMI_F = ["Giulia", "Sofia", "Aurora", "Alice", "Martina", "Sara", "Chiara", "Anna",
          "Francesca", "Elena", "Beatrice", "Greta", "Noemi", "Emma"]


def log(m): print(m, flush=True)


def norm(u: str) -> str:
    raw = (u or "").strip()
    m = re.search(r'postgres(?:ql)?://[^\s"\']+', raw)
    x = m.group(0) if m else raw.strip().strip('"').strip("'")
    return ("postgresql://" + x[len("postgres://"):]) if x.startswith("postgres://") else x


def dbname_of(url: str) -> str:
    m = re.search(r"/([^/?]+)(\?|$)", url)
    return m.group(1) if m else ""


def make_value(dtype, label, sesso=None):
    d = (dtype or "").lower()
    if any(x in d for x in ("char", "text")):
        return label
    if "bool" in d:
        return False
    if any(x in d for x in ("int", "numeric", "double", "real", "decimal")):
        return 0
    if "date" in d or "time" in d:
        return "2000-01-01"
    return label


def main() -> int:
    test = norm(os.getenv("TEST_DATABASE_URL", ""))
    try:
        numero = int(os.getenv("NUMERO", "10"))
    except ValueError:
        numero = 10
    try:
        studio = int(os.getenv("STUDIO", "1"))
    except ValueError:
        studio = 1

    if not test:
        log("ERRORE: manca TEST_DATABASE_URL.")
        return 2
    tn = dbname_of(test)
    if "test" not in tn.lower():
        log(f"BLOCCO DI SICUREZZA: il DB '{tn}' non contiene 'test'. Interrompo (non tocco la produzione).")
        return 2

    import psycopg2
    import psycopg2.extras
    conn = psycopg2.connect(test, cursor_factory=psycopg2.extras.DictCursor, connect_timeout=15)
    conn.autocommit = True
    cur = conn.cursor()

    # imposta il contesto studio: gli insert finiscono in questo studio e la RLS li ammette
    cur.execute("SET app.current_studio = %s", (studio,))

    # colonne reali della tabella pazienti
    cur.execute("""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_schema='public' AND lower(table_name)='pazienti'
          AND column_name NOT IN ('id','studio_id')
    """)
    cols_info = cur.fetchall()
    by_name = {c[0].lower(): c for c in cols_info}

    log(f"Creo {numero} pazienti finti nello studio {studio} (senza cancellare nulla)...")
    creati = 0
    for _ in range(numero):
        sesso = random.choice(["M", "F"])
        cognome = random.choice(COGNOMI)
        nome = random.choice(NOMI_M if sesso == "M" else NOMI_F)
        nascita = date(random.randint(1995, 2020), random.randint(1, 12), random.randint(1, 28)).isoformat()

        valori = {}
        # campi anagrafici comuni se esistono
        if "cognome" in by_name: valori["cognome"] = cognome
        if "nome" in by_name: valori["nome"] = nome
        if "sesso" in by_name: valori["sesso"] = sesso
        if "data_nascita" in by_name: valori["data_nascita"] = nascita

        # riempi tutte le altre colonne OBBLIGATORIE (NOT NULL senza default)
        for cname, dtype, nullable, default in cols_info:
            lc = cname.lower()
            if lc in valori:
                continue
            if nullable == "NO" and default is None:
                valori[lc] = make_value(dtype, f"{cognome} {nome}", sesso)

        cols = ", ".join(f'"{c}"' for c in valori.keys())
        ph = ", ".join(["%s"] * len(valori))
        try:
            cur.execute(f"INSERT INTO pazienti ({cols}) VALUES ({ph})", list(valori.values()))
            creati += 1
        except Exception as e:
            log(f"  (saltato un paziente: {str(e)[:120]})")

    cur.execute("SELECT count(*) FROM pazienti")
    tot = cur.fetchone()[0]
    log(f"Fatto: creati {creati} pazienti. Totale visibile per lo studio {studio}: {tot}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
