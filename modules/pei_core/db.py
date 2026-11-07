"""
pei_core.db — accesso a PostgreSQL (psycopg2, placeholder %s).
Ogni funzione riceve una connessione già aperta: ciascuna app usa la sua.

Compatibile sia con una connessione psycopg2 «nuda» (TFA Manager) sia con il
wrapper _PgConn del gestionale, il cui cursor() non accetta argomenti e non
supporta «with»: per questo niente cursor_factory, righe convertite a mano.
Nessun «?» nel testo SQL: il wrapper del gestionale lo trasformerebbe in %s.
"""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

from psycopg2.extras import Json


@contextmanager
def _cur(conn):
    cur = conn.cursor()
    try:
        yield cur
    finally:
        try:
            cur.close()
        except Exception:
            pass


def _righe(cur) -> list[dict]:
    nomi = [d[0] for d in cur.description]
    return [dict(zip(nomi, tuple(r))) for r in cur.fetchall()]

from .model import Documento, adesso
from .pdf_io import leggi_allegato


def crea_tabelle(conn):
    ddl = (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8")
    with _cur(conn) as cur:
        cur.execute("SELECT pg_advisory_xact_lock(724502)")  # avvii concorrenti
        cur.execute(ddl)
    conn.commit()


def salva_documento(conn, doc: Documento, rif_tipo: str, rif_id: int,
                    utente: str = "", tenant_id: int | None = None,
                    sorgente_id: int | None = None) -> int:
    r = doc.to_row()
    with _cur(conn) as cur:
        if doc.id is None:
            cur.execute("""
                INSERT INTO pei_documenti (tenant_id, rif_tipo, rif_id, tipo, anno_scolastico,
                    grado, anonimo, stato, schema_version, contenuto, sorgente_id, creato_da)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
            """, (tenant_id, rif_tipo, rif_id, r["tipo"], r["anno_scolastico"], r["grado"],
                  r["anonimo"], r["stato"], r["schema_version"], Json(r["contenuto"]),
                  sorgente_id, utente))
            doc.id = cur.fetchone()[0]
        else:
            cur.execute("""
                UPDATE pei_documenti SET anno_scolastico=%s, grado=%s, anonimo=%s, stato=%s,
                    schema_version=%s, contenuto=%s, sorgente_id=COALESCE(%s, sorgente_id),
                    aggiornato_il=%s
                WHERE id=%s AND rif_tipo=%s AND rif_id=%s
            """, (r["anno_scolastico"], r["grado"], r["anonimo"], r["stato"],
                  r["schema_version"], Json(r["contenuto"]), sorgente_id, adesso(),
                  doc.id, rif_tipo, rif_id))
            if cur.rowcount == 0:
                raise PermissionError("Documento non trovato o non tuo.")
    conn.commit()
    return doc.id


def elenco_documenti(conn, rif_tipo: str, rif_id: int, tipo: str | None = None) -> list[dict]:
    sql = """SELECT id, tipo, anno_scolastico, stato, anonimo, aggiornato_il,
                    contenuto->>'soggetto' AS soggetto
             FROM pei_documenti WHERE rif_tipo=%s AND rif_id=%s"""
    par = [rif_tipo, rif_id]
    if tipo:
        sql += " AND tipo=%s"
        par.append(tipo)
    sql += " ORDER BY aggiornato_il DESC"
    with _cur(conn) as cur:
        cur.execute(sql, par)
        return _righe(cur)


def carica_documento(conn, doc_id: int, rif_tipo: str, rif_id: int) -> Documento | None:
    with _cur(conn) as cur:
        cur.execute("SELECT * FROM pei_documenti WHERE id=%s AND rif_tipo=%s AND rif_id=%s",
                    (doc_id, rif_tipo, rif_id))
        righe = _righe(cur)
    return Documento.from_row(righe[0]) if righe else None


def elimina_documento(conn, doc_id: int, rif_tipo: str, rif_id: int):
    with _cur(conn) as cur:
        cur.execute("DELETE FROM pei_documenti WHERE id=%s AND rif_tipo=%s AND rif_id=%s",
                    (doc_id, rif_tipo, rif_id))
    conn.commit()


# ---------------------------- allegati -----------------------------------
def aggiungi_allegato(conn, documento_id: int, dati: bytes, nome_file: str,
                      utente: str = "") -> dict:
    info = leggi_allegato(dati, nome_file)          # valida prima di scrivere
    with _cur(conn) as cur:
        cur.execute("""
            INSERT INTO pei_allegati (documento_id, nome_file, sha256, dimensione, pagine,
                testo_estratto, scansione, dati, caricato_da)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (documento_id, sha256) DO NOTHING RETURNING id
        """, (documento_id, info["nome_file"], info["sha256"], info["dimensione"],
              info["pagine"], info["testo_estratto"], info["scansione"], dati, utente))
        riga = cur.fetchone()
    conn.commit()
    info["id"] = riga[0] if riga else None
    info["duplicato"] = riga is None
    return info


def elenco_allegati(conn, documento_id: int) -> list[dict]:
    with _cur(conn) as cur:
        cur.execute("""SELECT id, nome_file, dimensione, pagine, scansione, caricato_il
                       FROM pei_allegati WHERE documento_id=%s ORDER BY caricato_il""",
                    (documento_id,))
        return _righe(cur)


# rif_tipo/rif_id verificano che l'allegato appartenga a chi lo chiede
_PROPRIETA = """FROM pei_allegati a JOIN pei_documenti d ON d.id = a.documento_id
               WHERE a.id=%s AND d.rif_tipo=%s AND d.rif_id=%s"""


def leggi_allegato_db(conn, allegato_id: int, rif_tipo: str, rif_id: int) -> tuple[str, bytes]:
    with _cur(conn) as cur:
        cur.execute("SELECT a.nome_file, a.dati " + _PROPRIETA, (allegato_id, rif_tipo, rif_id))
        riga = cur.fetchone()
    if not riga:
        raise PermissionError("Allegato non trovato o non tuo.")
    return riga[0], bytes(riga[1])


def elimina_allegato(conn, allegato_id: int, rif_tipo: str, rif_id: int):
    with _cur(conn) as cur:
        cur.execute("DELETE FROM pei_allegati WHERE id IN (SELECT a.id " + _PROPRIETA + ")",
                    (allegato_id, rif_tipo, rif_id))
    conn.commit()


# ------------------------- privacy: esporta / cancella tutto -------------
def esporta_tutto(conn, rif_tipo: str, rif_id: int) -> list[dict]:
    """Tutti i documenti (con allegati in bytes) di un paziente o corsista."""
    with _cur(conn) as cur:
        cur.execute("SELECT * FROM pei_documenti WHERE rif_tipo=%s AND rif_id=%s ORDER BY id",
                    (rif_tipo, rif_id))
        docs = _righe(cur)
        for d in docs:
            cur.execute("SELECT nome_file, dati FROM pei_allegati WHERE documento_id=%s", (d["id"],))
            d["allegati"] = [(r["nome_file"], bytes(r["dati"])) for r in _righe(cur)]
    return docs


def elimina_tutto(conn, rif_tipo: str, rif_id: int) -> int:
    with _cur(conn) as cur:
        cur.execute("DELETE FROM pei_documenti WHERE rif_tipo=%s AND rif_id=%s", (rif_tipo, rif_id))
        n = cur.rowcount
    conn.commit()
    return n
