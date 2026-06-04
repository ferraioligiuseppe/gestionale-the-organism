#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/setup_test_mt.py

Prepara e COLLAUDA l'ambiente multi-tenant nel database DI TEST.
NON tocca mai la produzione: dalla produzione legge SOLO lo schema (struttura),
mai i dati. Scrive esclusivamente sul database di test.

Cosa fa:
  1. Sicurezza: si rifiuta di partire se il DB di test non sembra di test
     (deve contenere 'test' nel nome ed essere diverso dal DB di produzione).
  2. Esporta lo SCHEMA della produzione (pg_dump --schema-only, sola struttura).
  3. Ricrea lo schema 'public' del DB di test e ci applica la struttura.
  4. Aggiunge studio_id + Row-Level Security (FORCE) a tutte le tabelle dei
     pazienti; lascia globali le tabelle di sistema e il catalogo proprietario.
  5. Crea 2 studi finti con pazienti finti.
  6. Esegue il test di isolamento e stampa PASS/FAIL.

Sorgenti:
  - PROD: DATABASE_URL letto da .streamlit/secrets.toml ([db].DATABASE_URL)
  - TEST: variabile d'ambiente TEST_DATABASE_URL (secret GitHub)

Exit code: 0 se PASS, 1 se il test di isolamento fallisce, 2 errore di config/sistema.
"""
from __future__ import annotations
import os
import re
import sys
import subprocess
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECRETS_PATH = os.path.join(ROOT, ".streamlit", "secrets.toml")

# Tabelle che NON ricevono studio_id (restano comuni)
SYSTEM = {
    "studi", "utenti_meta", "abbonamenti",
    "auth_users", "auth_roles", "auth_user_roles", "auth_audit_log",
    "log_accessi",
}
# Catalogo proprietario di piattaforma (IP di Giuseppe): globale, non per-studio
CATALOG = {
    "cf_template", "cf_voci",
    "reading_stimuli",
    "tomatis_presets",
    "audio_calibration_profiles", "audio_calibration_profiles2",
    "audio_devices", "audio_headphones",
}


def log(m): print(m, flush=True)


def load_prod_url() -> str:
    try:
        import tomllib
        with open(SECRETS_PATH, "rb") as f:
            sec = tomllib.load(f)
    except Exception as e:
        log(f"ERRORE lettura secrets: {e}")
        return ""
    db = sec.get("db", {})
    for k in ("DATABASE_URL", "database_url"):
        if isinstance(db, dict) and db.get(k):
            return str(db[k]).strip()
        if sec.get(k):
            return str(sec[k]).strip()
    return ""


def clean_url(raw: str) -> str:
    """Estrae una stringa di connessione pulita, anche se incollata come
    DATABASE_URL = "postgresql://..." o con virgolette/spazi attorno."""
    raw = (raw or "").strip()
    m = re.search(r'postgres(?:ql)?://[^\s"\']+', raw)
    u = m.group(0) if m else raw.strip().strip('"').strip("'")
    if u.startswith("postgres://"):
        u = "postgresql://" + u[len("postgres://"):]
    return u


def norm(u: str) -> str:
    return clean_url(u)


def dbname_of(url: str) -> str:
    m = re.search(r"/([^/?]+)(\?|$)", url)
    return m.group(1) if m else ""


def main() -> int:
    prod = norm(load_prod_url())
    test = norm((os.getenv("TEST_DATABASE_URL") or "").strip())
    if not prod:
        log("ERRORE: DATABASE_URL di produzione non trovato nei secrets.")
        return 2
    if not test:
        log("ERRORE: manca il secret TEST_DATABASE_URL.")
        return 2

    # --- SICUREZZA: mai toccare la produzione ---
    pn, tn = dbname_of(prod), dbname_of(test)
    if tn == pn:
        log(f"BLOCCO DI SICUREZZA: il DB di test ha lo stesso nome del prod ({tn}). Interrompo.")
        return 2
    if "test" not in tn.lower():
        log(f"BLOCCO DI SICUREZZA: il nome del DB di test ('{tn}') non contiene 'test'. Interrompo.")
        return 2
    log(f"Prod (sola lettura schema): {pn}  |  Test (destinazione): {tn}")

    import psycopg2
    import psycopg2.extras

    # --- 1) Dump schema della produzione (solo struttura) ---
    tmp = tempfile.mkdtemp(prefix="mt_")
    schema_sql = os.path.join(tmp, "schema.sql")
    log("Esporto lo schema della produzione (solo struttura, niente dati)...")
    r = subprocess.run(
        ["pg_dump", "--schema-only", "--no-owner", "--no-acl", "--no-comments",
         "--file", schema_sql, "--dbname", prod],
        capture_output=True, text=True, timeout=600,
    )
    if r.returncode != 0:
        log("ERRORE pg_dump schema:")
        log(r.stderr[:3000])
        return 2
    log(f"Schema esportato ({os.path.getsize(schema_sql)} byte).")

    # --- 2) Ripulisco il TEST (drop delle sole tabelle, senza toccare lo schema) e applico la struttura ---
    # Nota: su OVH l'utente di solito NON è proprietario dello schema 'public',
    # quindi non si può fare DROP SCHEMA. Droppiamo invece le tabelle di cui è proprietario.
    log("Ripulisco il database di test (drop delle tabelle esistenti) e applico la struttura...")
    drop_sql = (
        "DO $$ DECLARE r record; BEGIN "
        "FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname='public') LOOP "
        "EXECUTE 'DROP TABLE IF EXISTS public.\"' || r.tablename || '\" CASCADE'; "
        "END LOOP; END $$;"
    )
    rp = subprocess.run(
        ["psql", "--dbname", test, "-v", "ON_ERROR_STOP=0", "-c", drop_sql],
        capture_output=True, text=True, timeout=120,
    )
    if rp.returncode != 0:
        log("ERRORE pulizia tabelle test:")
        log(rp.stderr[:2000])
        return 2
    ra = subprocess.run(
        ["psql", "--dbname", test, "-v", "ON_ERROR_STOP=0", "-f", schema_sql],
        capture_output=True, text=True, timeout=600,
    )
    # ON_ERROR_STOP=0: alcune righe (es. estensioni non disponibili) possono fallire senza bloccare
    log("Struttura applicata al database di test.")

    # --- 3) Connessione al test e migrazione multi-tenant ---
    conn = psycopg2.connect(test, cursor_factory=psycopg2.extras.DictCursor, connect_timeout=15)
    conn.autocommit = True
    cur = conn.cursor()

    cur.execute("SELECT current_setting('is_superuser')")
    if str(cur.fetchone()[0]).lower() == "on":
        log("ATTENZIONE: l'utente del DB è SUPERUSER → la RLS viene scavalcata e il test "
            "di isolamento non è significativo. In produzione l'app usa un utente normale, "
            "quindi la RLS funziona. (Su OVH l'utente non è superuser: nessun problema.)")

    cur.execute("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema='public' AND table_type='BASE TABLE'
        ORDER BY table_name
    """)
    all_tables = [r[0] for r in cur.fetchall()]
    per_studio = [t for t in all_tables if t.lower() not in SYSTEM and t.lower() not in CATALOG]
    log(f"Tabelle totali: {len(all_tables)} | per-studio: {len(per_studio)} | "
        f"sistema: {len([t for t in all_tables if t.lower() in SYSTEM])} | "
        f"catalogo: {len([t for t in all_tables if t.lower() in CATALOG])}")

    # serve almeno la tabella studi per la FK
    if "studi" not in [t.lower() for t in all_tables]:
        cur.execute("CREATE TABLE IF NOT EXISTS studi (id bigserial PRIMARY KEY, nome text)")

    migrate_ok, migrate_skip = 0, 0
    for t in per_studio:
        q = '"%s"' % t
        try:
            cur.execute(f"ALTER TABLE {q} ADD COLUMN IF NOT EXISTS studio_id bigint "
                        f"DEFAULT current_setting('app.current_studio', true)::bigint")
            cur.execute(f"UPDATE {q} SET studio_id = 1 WHERE studio_id IS NULL")
            cur.execute(f"ALTER TABLE {q} ALTER COLUMN studio_id SET NOT NULL")
            cur.execute(f"CREATE INDEX IF NOT EXISTS idx_{t.lower()}_studio ON {q}(studio_id)")
            cur.execute(f"ALTER TABLE {q} ENABLE ROW LEVEL SECURITY")
            cur.execute(f"ALTER TABLE {q} FORCE ROW LEVEL SECURITY")
            cur.execute(f"DROP POLICY IF EXISTS p_studio ON {q}")
            cur.execute(f"CREATE POLICY p_studio ON {q} "
                        f"USING (studio_id = current_setting('app.current_studio', true)::bigint) "
                        f"WITH CHECK (studio_id = current_setting('app.current_studio', true)::bigint)")
            migrate_ok += 1
        except Exception as e:
            migrate_skip += 1
            log(f"  (saltata {t}: {str(e)[:120]})")
    log(f"Migrazione applicata: {migrate_ok} tabelle ok, {migrate_skip} saltate.")

    # --- 4) Studi + pazienti finti ---
    cur.execute("INSERT INTO studi(nome) VALUES ('Studio Test 1') ON CONFLICT DO NOTHING")
    cur.execute("INSERT INTO studi(nome) VALUES ('Studio Test 2') ON CONFLICT DO NOTHING")
    cur.execute("SELECT id FROM studi ORDER BY id LIMIT 2")
    ids = [r[0] for r in cur.fetchall()]
    s1, s2 = (ids + [1, 2])[:2]

    # nomi colonne di "pazienti" che sono OBBLIGATORIE (NOT NULL) e senza default:
    # vanno riempite tutte, altrimenti l'insert finto fallisce.
    cur.execute("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema='public' AND lower(table_name)='pazienti'
          AND is_nullable='NO'
          AND column_default IS NULL
          AND column_name <> 'studio_id'
          AND NOT (column_name='id')
    """)
    required = cur.fetchall()

    def add_paz(studio, etichetta):
        cur.execute(f"SET app.current_studio = '{studio}'")
        cols, vals = [], []
        for cname, dtype in required:
            cols.append(f'"{cname}"')
            d = (dtype or "").lower()
            if any(t in d for t in ("char", "text")):
                vals.append(etichetta)
            elif "bool" in d:
                vals.append(False)
            elif any(t in d for t in ("int", "numeric", "double", "real", "decimal")):
                vals.append(0)
            elif "date" in d or "time" in d:
                vals.append("2000-01-01")
            else:
                vals.append(etichetta)
        if cols:
            ph = ", ".join(["%s"] * len(vals))
            cur.execute(f'INSERT INTO pazienti ({", ".join(cols)}) VALUES ({ph})', vals)
        else:
            cur.execute("INSERT INTO pazienti DEFAULT VALUES")

    try:
        add_paz(s1, "PazienteStudio1_A")
        add_paz(s1, "PazienteStudio1_B")
        add_paz(s2, "PazienteStudio2_X")
    except Exception as e:
        log(f"ERRORE inserimento pazienti finti: {e}")
        return 2

    # --- 5) Diagnostica RLS prima del test ---
    cur.execute("SELECT relrowsecurity, relforcerowsecurity FROM pg_class WHERE relname='pazienti'")
    diag = cur.fetchone()
    cur.execute("SELECT current_user, current_setting('is_superuser')")
    who = cur.fetchone()
    cur.execute("SELECT rolbypassrls FROM pg_roles WHERE rolname = current_user")
    bypass = cur.fetchone()
    cur.execute("SELECT pg_get_userbyid(relowner) FROM pg_class WHERE relname='pazienti'")
    owner = cur.fetchone()[0]
    log(f"\nDiagnostica: utente={who[0]} superuser={who[1]} "
        f"BYPASSRLS={bypass[0] if bypass else '?'} | proprietario tabella pazienti={owner}")
    if diag:
        log(f"Diagnostica pazienti: RLS attiva={diag[0]}  FORCE attiva={diag[1]}")
    cur.execute("SELECT current_setting('app.current_studio', true)")
    log(f"Diagnostica: app.current_studio attualmente = {cur.fetchone()[0]!r}")

    # Elenco TUTTE le policy presenti su pazienti (per scoprire policy preesistenti permissive)
    cur.execute("""
        SELECT policyname, permissive, cmd, qual
        FROM pg_policies WHERE schemaname='public' AND tablename='pazienti'
        ORDER BY policyname
    """)
    pols = cur.fetchall()
    log(f"Diagnostica: policy su pazienti = {len(pols)}")
    for p in pols:
        log(f"   - {p[0]} | permissive={p[1]} | cmd={p[2]} | qual={p[3]}")

    # --- 6) Test di isolamento ---
    log("\n===== TEST DI ISOLAMENTO =====")

    # Diagnostica chirurgica: distribuzione reale degli studio_id nei pazienti finti.
    # La leggo come PROPRIETARIO con RLS momentaneamente "vista piena": uso una query
    # che mostra studio_id riga per riga sotto ciascun contesto.
    for sx in (s1, s2):
        cur.execute(f"SET app.current_studio = '{sx}'")
        cur.execute("SELECT studio_id, count(*) FROM pazienti GROUP BY studio_id ORDER BY studio_id")
        righe = cur.fetchall()
        dett = ", ".join(f"studio_id={r[0]}→{r[1]}" for r in righe) or "(nessuna riga)"
        log(f"Con app.current_studio={sx}: la query vede [{dett}]")

    cur.execute(f"SET app.current_studio = '{s1}'")
    cur.execute("SELECT count(*) FROM pazienti")
    n1 = cur.fetchone()[0]
    cur.execute(f"SET app.current_studio = '{s2}'")
    cur.execute("SELECT count(*) FROM pazienti")
    n2 = cur.fetchone()[0]

    log(f"Studio 1 vede {n1} pazienti (atteso 2).")
    log(f"Studio 2 vede {n2} pazienti (atteso 1).")

    ok = (n1 == 2 and n2 == 1)
    # controllo catalogo globale visibile a entrambi (se esiste cf_template)
    if "cf_template" in [t.lower() for t in all_tables]:
        cur.execute("SELECT count(*) FROM cf_template")
        log(f"Catalogo proprietario (cf_template) visibile: {cur.fetchone()[0]} righe (comune, ok).")

    log("==============================")
    if ok:
        log("RISULTATO: PASS — isolamento dei dati per studio funzionante.")
        return 0
    else:
        log("RISULTATO: FAIL — l'isolamento non è corretto, da verificare.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
