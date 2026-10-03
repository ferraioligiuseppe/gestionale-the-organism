"""
modules/crediti/db_crediti.py
Crediti cliente spendibili tra settori + convenzioni.
Le funzioni che accettano `cur` lavorano DENTRO la transazione del chiamante
(nessun commit): servono al modulo Aerosal per vendere e scalare in modo atomico.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import date, timedelta
from decimal import Decimal

SETTORI = ("aerosal", "ottica", "telefonia", "studio")
ETICHETTE_SETTORE = {"aerosal": "Aerosal", "ottica": "Ottica",
                     "telefonia": "Telefonia", "studio": "Studio"}


@contextmanager
def _cur(conn):
    """Il cursore del gestionale (_PgCursor) non si puo' usare con «with
    conn.cursor()»: questo lo apre e lo chiude comunque."""
    cur = conn.cursor()
    try:
        yield cur
    finally:
        try:
            cur.close()
        except Exception:
            pass


def _rows(cur):
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


# ---------------------------------------------------- operazioni in transazione
def crea_credito_cur(cur, studio_id: str, c: dict) -> int:
    importo = Decimal(c["importo"])
    cur.execute(
        """INSERT INTO crediti
             (studio_id, paziente_id, nominativo, telefono, tipo, origine, origine_id,
              importo, residuo, settori, emesso_il, scade_il, credito_padre_id,
              consenso_marketing, note)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
        (studio_id, c.get("paziente_id"), c["nominativo"], c.get("telefono"),
         c.get("tipo", "credito"), c["origine"], c.get("origine_id"), importo, importo,
         list(c["settori"]), c["emesso_il"], c["scade_il"], c.get("credito_padre_id"),
         c.get("consenso_marketing", False), c.get("note")),
    )
    return cur.fetchone()[0]


def usa_credito_cur(cur, studio_id: str, credito_id: int, settore: str, importo: Decimal,
                    oggi: date, riferimento: str | None = None, operatore: str | None = None) -> Decimal:
    """Scala `importo` dal credito (bloccando la riga). Ritorna l'importo effettivamente scalato."""
    cur.execute(
        """SELECT residuo, settori, stato, scade_il FROM crediti
           WHERE id=%s AND studio_id=%s FOR UPDATE""",
        (credito_id, studio_id),
    )
    row = cur.fetchone()
    if row is None:
        raise ValueError("Credito non trovato.")
    residuo, settori, stato, scade = row
    if stato != "attivo":
        raise ValueError(f"Credito non utilizzabile (stato: {stato}).")
    if scade < oggi:
        raise ValueError(f"Credito scaduto il {scade:%d/%m/%Y}.")
    if settore not in settori:
        raise ValueError(f"Credito non spendibile nel settore {ETICHETTE_SETTORE[settore]}.")
    usato = min(Decimal(importo), residuo)
    if usato <= 0:
        raise ValueError("Importo non valido.")
    nuovo = residuo - usato
    cur.execute(
        "UPDATE crediti SET residuo=%s, stato=%s WHERE id=%s",
        (nuovo, "usato" if nuovo == 0 else "attivo", credito_id),
    )
    cur.execute(
        """INSERT INTO crediti_movimenti (studio_id, credito_id, data, settore, importo, riferimento, operatore)
           VALUES (%s,%s,%s,%s,%s,%s,%s)""",
        (studio_id, credito_id, oggi, settore, usato, riferimento, operatore),
    )
    return usato


# ------------------------------------------------------ operazioni con commit
def crea_credito(conn, studio_id: str, c: dict) -> int:
    with _cur(conn) as cur:
        cid = crea_credito_cur(cur, studio_id, c)
    conn.commit()
    return cid


def usa_credito(conn, studio_id: str, credito_id: int, settore: str, importo: Decimal,
                oggi: date, riferimento=None, operatore=None) -> Decimal:
    try:
        with _cur(conn) as cur:
            usato = usa_credito_cur(cur, studio_id, credito_id, settore, importo, oggi,
                                    riferimento, operatore)
        conn.commit()
        return usato
    except Exception:
        conn.rollback()
        raise


def crediti_disponibili(conn, studio_id: str, oggi: date, settore: str | None = None,
                        cerca: str | None = None, paziente_id: int | None = None) -> list[dict]:
    sql = """SELECT id, tipo, nominativo, telefono, paziente_id, importo, residuo, settori,
                    emesso_il, scade_il, origine
             FROM crediti WHERE studio_id=%s AND stato='attivo' AND scade_il >= %s"""
    par: list = [studio_id, oggi]
    if settore:
        sql += " AND %s = ANY(settori)"
        par.append(settore)
    if paziente_id:
        sql += " AND paziente_id=%s"
        par.append(paziente_id)
    if cerca:
        sql += " AND (nominativo ILIKE %s OR telefono ILIKE %s)"
        par += [f"%{cerca}%", f"%{cerca}%"]
    sql += " ORDER BY scade_il"
    with _cur(conn) as cur:
        cur.execute(sql, par)
        return _rows(cur)


def elenco_crediti(conn, studio_id: str, stati: tuple = ("attivo",)) -> list[dict]:
    with _cur(conn) as cur:
        cur.execute(
            """SELECT id, tipo, nominativo, telefono, importo, residuo, settori, emesso_il,
                      scade_il, stato, origine, consenso_marketing
               FROM crediti WHERE studio_id=%s AND stato = ANY(%s) ORDER BY scade_il""",
            (studio_id, list(stati)),
        )
        return _rows(cur)


def movimenti(conn, studio_id: str, dal: date, al: date) -> list[dict]:
    with _cur(conn) as cur:
        cur.execute(
            """SELECT m.data, m.settore, m.importo, m.riferimento, m.operatore,
                      c.nominativo, c.tipo, c.origine
               FROM crediti_movimenti m JOIN crediti c ON c.id = m.credito_id
               WHERE m.studio_id=%s AND m.data BETWEEN %s AND %s ORDER BY m.data DESC""",
            (studio_id, dal, al),
        )
        return _rows(cur)


def gestisci_scadenze(conn, studio_id: str, oggi: date, converti: bool,
                      giorni_buono: int, settori_buono=("ottica", "telefonia")) -> dict:
    """Chiude i crediti scaduti. Se `converti`, i crediti Aerosal non usati
    diventano un buono spendibile in ottica/telefonia (solo per il residuo)."""
    esito = {"scaduti": 0, "convertiti": 0}
    try:
        with _cur(conn) as cur:
            cur.execute(
                """SELECT id, paziente_id, nominativo, telefono, residuo, origine, consenso_marketing
                   FROM crediti WHERE studio_id=%s AND stato='attivo' AND scade_il < %s
                   FOR UPDATE""",
                (studio_id, oggi),
            )
            for cid, paz, nom, tel, residuo, origine, consenso in cur.fetchall():
                if converti and origine == "prova_aerosal" and residuo > 0:
                    crea_credito_cur(cur, studio_id, {
                        "paziente_id": paz, "nominativo": nom, "telefono": tel, "tipo": "buono",
                        "origine": "conversione", "origine_id": cid, "importo": residuo,
                        "settori": settori_buono, "emesso_il": oggi,
                        "scade_il": oggi + timedelta(days=giorni_buono),
                        "credito_padre_id": cid, "consenso_marketing": consenso,
                        "note": "Buono da prova Aerosal non convertita"})
                    cur.execute("UPDATE crediti SET stato='convertito' WHERE id=%s", (cid,))
                    esito["convertiti"] += 1
                else:
                    cur.execute("UPDATE crediti SET stato='scaduto' WHERE id=%s", (cid,))
                    esito["scaduti"] += 1
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return esito


def in_scadenza(conn, studio_id: str, oggi: date, giorni: int = 7) -> list[dict]:
    with _cur(conn) as cur:
        cur.execute(
            """SELECT id, tipo, nominativo, telefono, residuo, settori, scade_il, consenso_marketing
               FROM crediti WHERE studio_id=%s AND stato='attivo'
                 AND scade_il BETWEEN %s AND %s ORDER BY scade_il""",
            (studio_id, oggi, oggi + timedelta(days=giorni)),
        )
        return _rows(cur)


# ---------------------------------------------------------------- convenzioni
def convenzioni(conn, studio_id: str, solo_attive: bool = False) -> list[dict]:
    sql = "SELECT * FROM convenzioni WHERE studio_id=%s"
    if solo_attive:
        sql += " AND attiva"
    sql += " ORDER BY settore_origine, codice"
    with _cur(conn) as cur:
        cur.execute(sql, (studio_id,))
        return _rows(cur)


def imposta_convenzione(conn, studio_id: str, conv_id: int, attiva: bool,
                        valore: Decimal | None) -> None:
    with _cur(conn) as cur:
        cur.execute(
            "UPDATE convenzioni SET attiva=%s, valore=%s WHERE id=%s AND studio_id=%s",
            (attiva, valore, conv_id, studio_id),
        )
    conn.commit()


def convenzioni_per_pacchetto_cur(cur, studio_id: str, n_sedute: int) -> list[dict]:
    cur.execute(
        """SELECT * FROM convenzioni
           WHERE studio_id=%s AND attiva AND settore_origine='aerosal'
             AND (min_sedute IS NULL OR min_sedute <= %s)""",
        (studio_id, n_sedute),
    )
    return _rows(cur)
