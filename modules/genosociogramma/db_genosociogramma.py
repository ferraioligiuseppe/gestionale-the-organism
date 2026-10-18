"""
Genosociogramma — accesso ai dati (PostgreSQL).

Convenzioni del gestionale: placeholder %s, BIGSERIAL, TEXT, TIMESTAMPTZ,
fuso orario Europe/Rome, multi-tenant con RLS su studio_id.

Le funzioni ricevono una connessione psycopg2 già aperta (con app.studio_id
impostato dal login, come negli altri moduli) e non la chiudono.
"""
from datetime import datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Rome")

SESSI = ("M", "F", "?")
TIPI_UNIONE = ("matrimonio", "convivenza", "separazione", "divorzio")
TIPI_LEGAME = ("stretto", "fusione", "conflitto", "rottura", "uni")

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS geno_genogrammi (
    id           BIGSERIAL PRIMARY KEY,
    studio_id    BIGINT NOT NULL DEFAULT NULLIF(current_setting('app.current_studio', true), '')::bigint,
    paziente_id  BIGINT NOT NULL,
    titolo       TEXT NOT NULL DEFAULT 'Genosociogramma',
    note         TEXT NOT NULL DEFAULT '',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_geno_genogrammi_paz ON geno_genogrammi (studio_id, paziente_id);

CREATE TABLE IF NOT EXISTS geno_persone (
    id             BIGSERIAL PRIMARY KEY,
    studio_id      BIGINT NOT NULL DEFAULT NULLIF(current_setting('app.current_studio', true), '')::bigint,
    genogramma_id  BIGINT NOT NULL REFERENCES geno_genogrammi(id) ON DELETE CASCADE,
    nome           TEXT NOT NULL DEFAULT '',
    sesso          TEXT NOT NULL DEFAULT 'M' CHECK (sesso IN ('M','F','?')),
    nascita        TEXT NOT NULL DEFAULT '',
    morte          TEXT NOT NULL DEFAULT '',
    causa          TEXT NOT NULL DEFAULT '',
    padre_id       BIGINT REFERENCES geno_persone(id) ON DELETE SET NULL,
    madre_id       BIGINT REFERENCES geno_persone(id) ON DELETE SET NULL,
    indice         BOOLEAN NOT NULL DEFAULT false,
    note           TEXT NOT NULL DEFAULT '',
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_geno_persone_g ON geno_persone (genogramma_id);

CREATE TABLE IF NOT EXISTS geno_unioni (
    id             BIGSERIAL PRIMARY KEY,
    studio_id      BIGINT NOT NULL DEFAULT NULLIF(current_setting('app.current_studio', true), '')::bigint,
    genogramma_id  BIGINT NOT NULL REFERENCES geno_genogrammi(id) ON DELETE CASCADE,
    a_id           BIGINT NOT NULL REFERENCES geno_persone(id) ON DELETE CASCADE,
    b_id           BIGINT NOT NULL REFERENCES geno_persone(id) ON DELETE CASCADE,
    tipo           TEXT NOT NULL DEFAULT 'matrimonio'
                   CHECK (tipo IN ('matrimonio','convivenza','separazione','divorzio')),
    anno           TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS ix_geno_unioni_g ON geno_unioni (genogramma_id);

CREATE TABLE IF NOT EXISTS geno_legami (
    id             BIGSERIAL PRIMARY KEY,
    studio_id      BIGINT NOT NULL DEFAULT NULLIF(current_setting('app.current_studio', true), '')::bigint,
    genogramma_id  BIGINT NOT NULL REFERENCES geno_genogrammi(id) ON DELETE CASCADE,
    a_id           BIGINT NOT NULL REFERENCES geno_persone(id) ON DELETE CASCADE,
    b_id           BIGINT NOT NULL REFERENCES geno_persone(id) ON DELETE CASCADE,
    tipo           TEXT NOT NULL DEFAULT 'stretto'
                   CHECK (tipo IN ('stretto','fusione','conflitto','rottura','uni'))
);
CREATE INDEX IF NOT EXISTS ix_geno_legami_g ON geno_legami (genogramma_id);
"""

# RLS: stessa convenzione di PECS e degli altri moduli recenti. Il tenant è
# impostato sulla connessione da app_core (-c app.current_studio=<id>).
RLS_SQL = """
DO $$
DECLARE t TEXT;
BEGIN
  FOREACH t IN ARRAY ARRAY['geno_genogrammi','geno_persone','geno_unioni','geno_legami'] LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', t);
    EXECUTE format('DROP POLICY IF EXISTS %I ON %I', t || '_tenant', t);
    EXECUTE format($f$
      CREATE POLICY %I ON %I
      USING (studio_id = NULLIF(current_setting('app.current_studio', true), '')::bigint)
      WITH CHECK (studio_id = NULLIF(current_setting('app.current_studio', true), '')::bigint)
    $f$, t || '_tenant', t);
  END LOOP;
END $$;
"""


def ensure_schema(conn):
    """Crea tabelle e policy se mancano. Idempotente."""
    try:
        cur = conn.cursor()
        cur.execute(SCHEMA_SQL)
        cur.execute(RLS_SQL)
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def studio_corrente(conn):
    """studio_id della connessione (app.current_studio), come fa PECS."""
    try:
        cur = conn.cursor()
        cur.execute("SELECT NULLIF(current_setting('app.current_studio', true), '')::bigint")
        row = cur.fetchone()
        return row[0] if row else None
    except Exception:
        conn.rollback()
        return None


def _now():
    return datetime.now(TZ)


def _touch(cur, gid):
    cur.execute("UPDATE geno_genogrammi SET updated_at = %s WHERE id = %s", (_now(), gid))


# ---------------------------------------------------------------- genogrammi
def lista_genogrammi(conn, paziente_id):
    cur = conn.cursor()
    cur.execute(
        "SELECT id, titolo, updated_at FROM geno_genogrammi "
        "WHERE paziente_id = %s ORDER BY updated_at DESC",
        (paziente_id,),
    )
    return [{"id": r[0], "titolo": r[1], "updated_at": r[2]} for r in cur.fetchall()]


def crea_genogramma(conn, studio_id, paziente_id, titolo="Genosociogramma"):
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO geno_genogrammi (studio_id, paziente_id, titolo, created_at, updated_at) "
        "VALUES (%s, %s, %s, %s, %s) RETURNING id",
        (studio_id, paziente_id, titolo, _now(), _now()),
    )
    gid = cur.fetchone()[0]
    conn.commit()
    return gid


def rinomina_genogramma(conn, gid, titolo, note=None):
    cur = conn.cursor()
    if note is None:
        cur.execute("UPDATE geno_genogrammi SET titolo = %s, updated_at = %s WHERE id = %s",
                    (titolo, _now(), gid))
    else:
        cur.execute("UPDATE geno_genogrammi SET titolo = %s, note = %s, updated_at = %s WHERE id = %s",
                    (titolo, note, _now(), gid))
    conn.commit()


def elimina_genogramma(conn, gid):
    cur = conn.cursor()
    cur.execute("DELETE FROM geno_genogrammi WHERE id = %s", (gid,))
    conn.commit()


def carica_genogramma(conn, gid):
    """Restituisce il genogramma come dict, nella forma usata da render_genosociogramma."""
    cur = conn.cursor()
    cur.execute("SELECT id, paziente_id, titolo, note, updated_at FROM geno_genogrammi WHERE id = %s", (gid,))
    g = cur.fetchone()
    if not g:
        return None
    cur.execute(
        "SELECT id, nome, sesso, nascita, morte, causa, padre_id, madre_id, indice, note "
        "FROM geno_persone WHERE genogramma_id = %s ORDER BY id",
        (gid,),
    )
    persone = [
        {"id": r[0], "nome": r[1], "sesso": r[2], "nascita": r[3], "morte": r[4], "causa": r[5],
         "padre": r[6], "madre": r[7], "indice": r[8], "note": r[9]}
        for r in cur.fetchall()
    ]
    cur.execute("SELECT id, a_id, b_id, tipo, anno FROM geno_unioni WHERE genogramma_id = %s ORDER BY id", (gid,))
    unioni = [{"id": r[0], "a": r[1], "b": r[2], "tipo": r[3], "anno": r[4]} for r in cur.fetchall()]
    cur.execute("SELECT id, a_id, b_id, tipo FROM geno_legami WHERE genogramma_id = %s ORDER BY id", (gid,))
    legami = [{"id": r[0], "a": r[1], "b": r[2], "tipo": r[3]} for r in cur.fetchall()]
    return {"id": g[0], "paziente_id": g[1], "titolo": g[2], "note": g[3], "updated_at": g[4],
            "persone": persone, "unioni": unioni, "legami": legami}


# ---------------------------------------------------------------- persone
def salva_persona(conn, studio_id, gid, p):
    """Inserisce (p senza 'id') o aggiorna una persona. Restituisce l'id."""
    sesso = p.get("sesso") if p.get("sesso") in SESSI else "M"
    vals = (p.get("nome", "").strip(), sesso, p.get("nascita", "").strip(), p.get("morte", "").strip(),
            p.get("causa", "").strip(), p.get("padre") or None, p.get("madre") or None,
            bool(p.get("indice")), p.get("note", ""))
    cur = conn.cursor()
    if p.get("indice"):
        cur.execute("UPDATE geno_persone SET indice = false WHERE genogramma_id = %s", (gid,))
    if p.get("id"):
        cur.execute(
            "UPDATE geno_persone SET nome=%s, sesso=%s, nascita=%s, morte=%s, causa=%s, "
            "padre_id=%s, madre_id=%s, indice=%s, note=%s WHERE id=%s AND genogramma_id=%s",
            vals + (p["id"], gid),
        )
        pid = p["id"]
    else:
        cur.execute(
            "INSERT INTO geno_persone (studio_id, genogramma_id, nome, sesso, nascita, morte, causa, "
            "padre_id, madre_id, indice, note, created_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
            (studio_id, gid) + vals + (_now(),),
        )
        pid = cur.fetchone()[0]
    _touch(cur, gid)
    conn.commit()
    return pid


def elimina_persona(conn, gid, pid):
    cur = conn.cursor()
    cur.execute("DELETE FROM geno_persone WHERE id = %s AND genogramma_id = %s", (pid, gid))
    _touch(cur, gid)
    conn.commit()


# ---------------------------------------------------------------- unioni e legami
def aggiungi_unione(conn, studio_id, gid, a, b, tipo="matrimonio", anno=""):
    if a == b or tipo not in TIPI_UNIONE:
        raise ValueError("Unione non valida")
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO geno_unioni (studio_id, genogramma_id, a_id, b_id, tipo, anno) "
        "VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
        (studio_id, gid, a, b, tipo, anno.strip()),
    )
    uid = cur.fetchone()[0]
    _touch(cur, gid)
    conn.commit()
    return uid


def aggiorna_unione(conn, gid, uid, tipo, anno):
    cur = conn.cursor()
    cur.execute("UPDATE geno_unioni SET tipo = %s, anno = %s WHERE id = %s AND genogramma_id = %s",
                (tipo, anno.strip(), uid, gid))
    _touch(cur, gid)
    conn.commit()


def elimina_unione(conn, gid, uid):
    cur = conn.cursor()
    cur.execute("DELETE FROM geno_unioni WHERE id = %s AND genogramma_id = %s", (uid, gid))
    _touch(cur, gid)
    conn.commit()


def aggiungi_legame(conn, studio_id, gid, a, b, tipo="stretto"):
    if a == b or tipo not in TIPI_LEGAME:
        raise ValueError("Legame non valido")
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO geno_legami (studio_id, genogramma_id, a_id, b_id, tipo) "
        "VALUES (%s, %s, %s, %s, %s) RETURNING id",
        (studio_id, gid, a, b, tipo),
    )
    lid = cur.fetchone()[0]
    _touch(cur, gid)
    conn.commit()
    return lid


def elimina_legame(conn, gid, lid):
    cur = conn.cursor()
    cur.execute("DELETE FROM geno_legami WHERE id = %s AND genogramma_id = %s", (lid, gid))
    _touch(cur, gid)
    conn.commit()
