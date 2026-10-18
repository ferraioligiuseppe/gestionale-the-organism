"""
Genosociogramma — accesso ai dati (PostgreSQL).

Convenzioni del gestionale: placeholder %s, BIGSERIAL, TEXT, TIMESTAMPTZ,
fuso orario Europe/Rome, multi-tenant con RLS su studio_id.

Le funzioni ricevono una connessione psycopg2 già aperta (con app.studio_id
impostato dal login, come negli altri moduli) e non la chiudono.
"""
import hashlib
import hmac
import secrets as _secrets
from datetime import datetime, timedelta
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

-- Link per la compilazione a casa. Senza RLS, come questionari_links: la pagina
-- pubblica deve leggerlo prima di sapere di quale studio è il paziente.
-- Contiene solo l'hash del token e gli id, nessun dato clinico.
CREATE TABLE IF NOT EXISTS geno_link (
    id             BIGSERIAL PRIMARY KEY,
    studio_id      BIGINT NOT NULL,
    paziente_id    BIGINT NOT NULL,
    genogramma_id  BIGINT NOT NULL REFERENCES geno_genogrammi(id) ON DELETE CASCADE,
    token_hash     TEXT NOT NULL UNIQUE,
    stato          TEXT NOT NULL DEFAULT 'attivo' CHECK (stato IN ('attivo','inviato','revocato')),
    creato_il      TIMESTAMPTZ NOT NULL DEFAULT now(),
    scade_il       TIMESTAMPTZ NOT NULL,
    consenso_il    TIMESTAMPTZ,
    consenso_nome  TEXT NOT NULL DEFAULT '',
    inviato_il     TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS ix_geno_link_paz ON geno_link (studio_id, paziente_id);
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


# ---------------------------------------------------------------- compilazione a casa
def hash_token(token, secret):
    key = (secret or "genosociogramma").encode("utf-8")
    return hmac.new(key, token.encode("utf-8"), hashlib.sha256).hexdigest()


def crea_link(conn, studio_id, paziente_id, secret, giorni=14):
    """Crea un genosociogramma vuoto «compilato dal paziente» e il link per compilarlo.
    Restituisce (token, genogramma_id). In DB si salva solo l'hash del token."""
    gid = crea_genogramma(conn, studio_id, paziente_id,
                          titolo=f"Compilato dal paziente — {_now():%d/%m/%Y}")
    token = _secrets.token_urlsafe(32)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO geno_link (studio_id, paziente_id, genogramma_id, token_hash, creato_il, scade_il) "
        "VALUES (%s, %s, %s, %s, %s, %s)",
        (studio_id, paziente_id, gid, hash_token(token, secret), _now(), _now() + timedelta(days=giorni)),
    )
    conn.commit()
    return token, gid


def link_da_token(conn, token, secret):
    """Riga del link come dict (anche se scaduto o già inviato), oppure None."""
    cur = conn.cursor()
    cur.execute(
        "SELECT id, studio_id, paziente_id, genogramma_id, stato, scade_il, consenso_il, inviato_il "
        "FROM geno_link WHERE token_hash = %s",
        (hash_token(token, secret),),
    )
    r = cur.fetchone()
    if not r:
        return None
    return {"id": r[0], "studio_id": r[1], "paziente_id": r[2], "genogramma_id": r[3], "stato": r[4],
            "scade_il": r[5], "consenso_il": r[6], "inviato_il": r[7],
            "scaduto": r[5] is not None and r[5] < _now()}


def lista_link(conn, paziente_id):
    cur = conn.cursor()
    cur.execute(
        "SELECT l.id, l.genogramma_id, l.stato, l.creato_il, l.scade_il, l.consenso_nome, l.inviato_il, g.titolo "
        "FROM geno_link l JOIN geno_genogrammi g ON g.id = l.genogramma_id "
        "WHERE l.paziente_id = %s ORDER BY l.creato_il DESC",
        (paziente_id,),
    )
    return [{"id": r[0], "genogramma_id": r[1], "stato": r[2], "creato_il": r[3], "scade_il": r[4],
             "consenso_nome": r[5], "inviato_il": r[6], "titolo": r[7]} for r in cur.fetchall()]


def registra_consenso(conn, link_id, nome):
    cur = conn.cursor()
    cur.execute("UPDATE geno_link SET consenso_il = %s, consenso_nome = %s WHERE id = %s AND stato = 'attivo'",
                (_now(), nome.strip(), link_id))
    conn.commit()


def segna_inviato(conn, link_id):
    cur = conn.cursor()
    cur.execute("UPDATE geno_link SET stato = 'inviato', inviato_il = %s WHERE id = %s AND stato = 'attivo'",
                (_now(), link_id))
    conn.commit()


def revoca_link(conn, link_id):
    cur = conn.cursor()
    cur.execute("UPDATE geno_link SET stato = 'revocato' WHERE id = %s AND stato = 'attivo'", (link_id,))
    conn.commit()
