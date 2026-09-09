# -*- coding: utf-8 -*-
"""
modules/pecs/db_pecs.py
-----------------------
Accesso ai dati del modulo PECS.

CONVENZIONI GESTIONALE
  - placeholder %s, BIGSERIAL, TEXT, TIMESTAMPTZ
  - RLS multi-tenant su studio_id, tenant impostato con
    set_config('app.studio_id', ..., true)
  - fuso orario applicativo: ZoneInfo("Europe/Rome")
  - nessun cursore lasciato aperto: tutto dentro il context manager _cursor()

PUNTI DA VERIFICARE AL MOMENTO DELL'INNESTO (unici adattamenti previsti):
  1. la funzione di connessione: viene cercata come get_connection() in
     `db`, `database` o `core.db`. Se nel gestionale ha un altro nome,
     chiamare db_pecs.configura(get_connection=...) all'avvio.
  2. TABELLA_PAZIENTI / COL_PAZIENTE_* qui sotto, se la tabella anagrafica
     non si chiama "pazienti".

Studio The Organism - Dott. Giuseppe Ferraioli
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence
from zoneinfo import ZoneInfo

import psycopg2
from psycopg2.extras import Json, RealDictCursor

TZ = ZoneInfo("Europe/Rome")

# --- anagrafica: adattare qui se i nomi nel gestionale sono diversi --------
TABELLA_PAZIENTI = "pazienti"
COL_PAZIENTE_ID = "id"
COL_PAZIENTE_NOME = "nome"
COL_PAZIENTE_COGNOME = "cognome"

# ---------------------------------------------------------------------------
# Connessione
# ---------------------------------------------------------------------------

_get_connection = None
_chiudi_connessione = False

for _modulo in ("db", "database", "core.db"):
    try:
        _mod = __import__(_modulo, fromlist=["get_connection"])
        _get_connection = getattr(_mod, "get_connection")
        break
    except Exception:  # pragma: no cover - dipende dal gestionale ospite
        continue


def configura(get_connection=None, chiudi_connessione: Optional[bool] = None) -> None:
    """Consente al gestionale di iniettare la propria funzione di connessione."""
    global _get_connection, _chiudi_connessione
    if get_connection is not None:
        _get_connection = get_connection
    if chiudi_connessione is not None:
        _chiudi_connessione = chiudi_connessione


def _conn():
    if _get_connection is not None:
        return _get_connection()
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        raise RuntimeError(
            "Nessuna connessione disponibile: chiamare db_pecs.configura("
            "get_connection=...) oppure impostare DATABASE_URL."
        )
    return psycopg2.connect(dsn)


@contextmanager
def _cursor(studio_id: Optional[int] = None, commit: bool = False):
    conn = _conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        if studio_id is not None:
            cur.execute("SELECT set_config('app.studio_id', %s, true)",
                        (str(studio_id),))
        yield cur
        if commit:
            conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            cur.close()
        finally:
            if _chiudi_connessione:
                conn.close()


def adesso() -> datetime:
    return datetime.now(TZ)


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

def inizializza_schema() -> None:
    """Esegue schema_pecs.sql. Idempotente."""
    percorso = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "schema_pecs.sql")
    with open(percorso, "r", encoding="utf-8") as f:
        ddl = f.read()
    with _cursor(commit=True) as cur:
        cur.execute(ddl)


# ---------------------------------------------------------------------------
# Protocolli
# ---------------------------------------------------------------------------

def get_protocollo_attivo(studio_id: int, paziente_id: int) -> Optional[Dict[str, Any]]:
    with _cursor(studio_id) as cur:
        cur.execute(
            """
            SELECT * FROM pecs_protocolli
             WHERE studio_id = %s AND paziente_id = %s AND stato = 'attivo'
             ORDER BY data_inizio DESC
             LIMIT 1
            """,
            (studio_id, paziente_id),
        )
        row = cur.fetchone()
    return dict(row) if row else None


def lista_protocolli(studio_id: int, solo_attivi: bool = True) -> List[Dict[str, Any]]:
    sql = """
        SELECT p.*,
               a.{cognome} AS paziente_cognome,
               a.{nome}    AS paziente_nome
          FROM pecs_protocolli p
          LEFT JOIN {tab} a ON a.{pid} = p.paziente_id
         WHERE p.studio_id = %s
    """.format(tab=TABELLA_PAZIENTI, pid=COL_PAZIENTE_ID,
               nome=COL_PAZIENTE_NOME, cognome=COL_PAZIENTE_COGNOME)
    params: List[Any] = [studio_id]
    if solo_attivi:
        sql += " AND p.stato = 'attivo'"
    sql += " ORDER BY a.{cognome} NULLS LAST, p.data_inizio DESC".format(
        cognome=COL_PAZIENTE_COGNOME)
    with _cursor(studio_id) as cur:
        cur.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]


def crea_protocollo(studio_id: int, paziente_id: int, operatore: str = "",
                    data_inizio: Optional[date] = None,
                    obiettivo: str = "", note: str = "") -> int:
    with _cursor(studio_id, commit=True) as cur:
        cur.execute(
            """
            INSERT INTO pecs_protocolli
                (studio_id, paziente_id, data_inizio, fase_corrente,
                 stato, obiettivo, note, creato_da)
            VALUES (%s, %s, COALESCE(%s, CURRENT_DATE), 'I',
                    'attivo', %s, %s, %s)
            RETURNING id
            """,
            (studio_id, paziente_id, data_inizio, obiettivo, note, operatore),
        )
        nuovo = cur.fetchone()["id"]
        cur.execute(
            """
            INSERT INTO pecs_transizioni
                (studio_id, protocollo_id, da_fase, a_fase, data,
                 criterio_soddisfatto, motivazione, operatore)
            VALUES (%s, %s, NULL, 'I', COALESCE(%s, CURRENT_DATE), FALSE,
                    'Avvio del protocollo', %s)
            """,
            (studio_id, nuovo, data_inizio, operatore),
        )
    return int(nuovo)


def aggiorna_protocollo(studio_id: int, protocollo_id: int, **campi) -> None:
    ammessi = {"fase_corrente", "stato", "obiettivo", "note", "data_inizio"}
    campi = {k: v for k, v in campi.items() if k in ammessi}
    if not campi:
        return
    set_sql = ", ".join("%s = %%s" % k for k in campi)
    valori = list(campi.values()) + [studio_id, protocollo_id]
    with _cursor(studio_id, commit=True) as cur:
        cur.execute(
            "UPDATE pecs_protocolli SET " + set_sql +
            ", aggiornato_il = NOW() WHERE studio_id = %s AND id = %s",
            valori,
        )


# ---------------------------------------------------------------------------
# Rinforzatori
# ---------------------------------------------------------------------------

def lista_rinforzatori(studio_id: int, protocollo_id: int,
                       solo_attivi: bool = False) -> List[Dict[str, Any]]:
    sql = ("SELECT * FROM pecs_rinforzatori "
           "WHERE studio_id = %s AND protocollo_id = %s")
    if solo_attivi:
        sql += " AND attivo = TRUE"
    sql += " ORDER BY gerarchia, item"
    with _cursor(studio_id) as cur:
        cur.execute(sql, (studio_id, protocollo_id))
        return [dict(r) for r in cur.fetchall()]


def aggiungi_rinforzatore(studio_id: int, protocollo_id: int, item: str,
                          categoria: str = "", gerarchia: int = 1,
                          data_verifica: Optional[date] = None,
                          note: str = "") -> int:
    with _cursor(studio_id, commit=True) as cur:
        cur.execute(
            """
            INSERT INTO pecs_rinforzatori
                (studio_id, protocollo_id, item, categoria, gerarchia,
                 data_verifica, attivo, note)
            VALUES (%s, %s, %s, %s, %s, COALESCE(%s, CURRENT_DATE), TRUE, %s)
            RETURNING id
            """,
            (studio_id, protocollo_id, item.strip(), categoria or None,
             gerarchia, data_verifica, note or None),
        )
        return int(cur.fetchone()["id"])


def aggiorna_rinforzatore(studio_id: int, rinforzatore_id: int, **campi) -> None:
    ammessi = {"item", "categoria", "gerarchia", "data_verifica", "attivo", "note"}
    campi = {k: v for k, v in campi.items() if k in ammessi}
    if not campi:
        return
    set_sql = ", ".join("%s = %%s" % k for k in campi)
    with _cursor(studio_id, commit=True) as cur:
        cur.execute(
            "UPDATE pecs_rinforzatori SET " + set_sql +
            " WHERE studio_id = %s AND id = %s",
            list(campi.values()) + [studio_id, rinforzatore_id],
        )


def elimina_rinforzatore(studio_id: int, rinforzatore_id: int) -> None:
    with _cursor(studio_id, commit=True) as cur:
        cur.execute(
            "DELETE FROM pecs_rinforzatori WHERE studio_id = %s AND id = %s",
            (studio_id, rinforzatore_id),
        )


def rinforzatori_da_riverificare(studio_id: int, protocollo_id: int,
                                 giorni: int = 7) -> List[Dict[str, Any]]:
    with _cursor(studio_id) as cur:
        cur.execute(
            """
            SELECT * FROM pecs_rinforzatori
             WHERE studio_id = %s AND protocollo_id = %s AND attivo = TRUE
               AND data_verifica < CURRENT_DATE - %s::int
             ORDER BY data_verifica
            """,
            (studio_id, protocollo_id, giorni),
        )
        return [dict(r) for r in cur.fetchall()]


# ---------------------------------------------------------------------------
# Sessioni e prove
# ---------------------------------------------------------------------------

def salva_sessione(studio_id: int, protocollo_id: int, fase: str,
                   data_sessione: Optional[date] = None,
                   operatore: str = "", partner: str = "", prompter: str = "",
                   contesto: str = "", item_usati: Optional[Sequence[str]] = None,
                   prove: Optional[Iterable[Dict[str, Any]]] = None,
                   n_opportunita: Optional[int] = None,
                   n_autonome: Optional[int] = None,
                   n_prompt: Optional[int] = None,
                   n_errori: Optional[int] = None,
                   parametri: Optional[Dict[str, Any]] = None,
                   fedelta: Optional[Dict[str, bool]] = None,
                   note: str = "") -> int:
    """
    Salva una sessione. Se `prove` e' fornito, i conteggi vengono calcolati
    dalle prove e il dettaglio prova-per-prova viene registrato.
    """
    prove = list(prove or [])
    if prove:
        n_opportunita = len(prove)
        n_autonome = sum(1 for p in prove if p.get("esito") == "autonoma")
        n_prompt = sum(1 for p in prove if p.get("esito") == "prompt")
        n_errori = sum(1 for p in prove if p.get("esito") == "errore")

    n_opportunita = int(n_opportunita or 0)
    n_autonome = int(n_autonome or 0)
    n_prompt = int(n_prompt or 0)
    n_errori = int(n_errori or 0)
    if n_autonome > n_opportunita:
        raise ValueError("Le risposte autonome non possono superare le opportunita'.")

    with _cursor(studio_id, commit=True) as cur:
        cur.execute(
            """
            INSERT INTO pecs_sessioni
                (studio_id, protocollo_id, data, fase, operatore, partner,
                 prompter, contesto, item_usati, n_opportunita, n_autonome,
                 n_prompt, n_errori, parametri, fedelta, note)
            VALUES (%s, %s, COALESCE(%s, CURRENT_DATE), %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (studio_id, protocollo_id, data_sessione, fase, operatore or None,
             partner or None, prompter or None, contesto or None,
             list(item_usati or []), n_opportunita, n_autonome, n_prompt,
             n_errori, Json(parametri or {}), Json(fedelta or {}),
             note or None),
        )
        sessione_id = int(cur.fetchone()["id"])

        for i, p in enumerate(prove, start=1):
            cur.execute(
                """
                INSERT INTO pecs_prove
                    (studio_id, sessione_id, ordine, esito, item, note)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (studio_id, sessione_id, p.get("ordine", i), p.get("esito"),
                 p.get("item") or None, p.get("note") or None),
            )
    return sessione_id


def elimina_sessione(studio_id: int, sessione_id: int) -> None:
    with _cursor(studio_id, commit=True) as cur:
        cur.execute("DELETE FROM pecs_sessioni WHERE studio_id = %s AND id = %s",
                    (studio_id, sessione_id))


def lista_sessioni(studio_id: int, protocollo_id: int,
                   fase: Optional[str] = None,
                   limite: Optional[int] = None) -> List[Dict[str, Any]]:
    """Sessioni ordinate dalla piu' recente alla piu' vecchia."""
    sql = ("SELECT * FROM pecs_sessioni "
           "WHERE studio_id = %s AND protocollo_id = %s")
    params: List[Any] = [studio_id, protocollo_id]
    if fase:
        sql += " AND fase = %s"
        params.append(fase)
    sql += " ORDER BY data DESC, id DESC"
    if limite:
        sql += " LIMIT %s"
        params.append(limite)
    with _cursor(studio_id) as cur:
        cur.execute(sql, params)
        righe = [dict(r) for r in cur.fetchall()]
    for r in righe:
        r["item_usati"] = list(r.get("item_usati") or [])
        r["parametri"] = r.get("parametri") or {}
        r["fedelta"] = r.get("fedelta") or {}
    return righe


def lista_prove(studio_id: int, sessione_id: int) -> List[Dict[str, Any]]:
    with _cursor(studio_id) as cur:
        cur.execute(
            "SELECT * FROM pecs_prove WHERE studio_id = %s AND sessione_id = %s "
            "ORDER BY ordine",
            (studio_id, sessione_id),
        )
        return [dict(r) for r in cur.fetchall()]


def andamento(studio_id: int, protocollo_id: int) -> List[Dict[str, Any]]:
    """Serie storica percentuale di autonomia per data, utile per il grafico."""
    with _cursor(studio_id) as cur:
        cur.execute(
            """
            SELECT data, fase,
                   SUM(n_opportunita) AS opportunita,
                   SUM(n_autonome)    AS autonome
              FROM pecs_sessioni
             WHERE studio_id = %s AND protocollo_id = %s
             GROUP BY data, fase
             ORDER BY data
            """,
            (studio_id, protocollo_id),
        )
        righe = [dict(r) for r in cur.fetchall()]
    for r in righe:
        opp = r.get("opportunita") or 0
        r["percentuale"] = round(100.0 * (r.get("autonome") or 0) / opp, 1) if opp else 0.0
    return righe


# ---------------------------------------------------------------------------
# Transizioni di fase
# ---------------------------------------------------------------------------

def registra_transizione(studio_id: int, protocollo_id: int, da_fase: Optional[str],
                         a_fase: str, criterio_soddisfatto: bool,
                         forzata: bool = False, motivazione: str = "",
                         evidenza: Optional[Dict[str, Any]] = None,
                         operatore: str = "",
                         data_transizione: Optional[date] = None) -> int:
    with _cursor(studio_id, commit=True) as cur:
        cur.execute(
            """
            INSERT INTO pecs_transizioni
                (studio_id, protocollo_id, da_fase, a_fase, data,
                 criterio_soddisfatto, forzata, motivazione, evidenza, operatore)
            VALUES (%s, %s, %s, %s, COALESCE(%s, CURRENT_DATE),
                    %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (studio_id, protocollo_id, da_fase, a_fase, data_transizione,
             criterio_soddisfatto, forzata, motivazione or None,
             Json(evidenza or {}), operatore or None),
        )
        nuovo = int(cur.fetchone()["id"])
        cur.execute(
            "UPDATE pecs_protocolli SET fase_corrente = %s, aggiornato_il = NOW() "
            "WHERE studio_id = %s AND id = %s",
            (a_fase, studio_id, protocollo_id),
        )
    return nuovo


def lista_transizioni(studio_id: int, protocollo_id: int) -> List[Dict[str, Any]]:
    with _cursor(studio_id) as cur:
        cur.execute(
            "SELECT * FROM pecs_transizioni "
            "WHERE studio_id = %s AND protocollo_id = %s "
            "ORDER BY data, id",
            (studio_id, protocollo_id),
        )
        return [dict(r) for r in cur.fetchall()]


# ---------------------------------------------------------------------------
# Anagrafica (lettura minima, per il selettore paziente)
# ---------------------------------------------------------------------------

def lista_pazienti(studio_id: int) -> List[Dict[str, Any]]:
    sql = """
        SELECT {pid} AS id, {nome} AS nome, {cognome} AS cognome
          FROM {tab}
         WHERE studio_id = %s
         ORDER BY {cognome}, {nome}
    """.format(tab=TABELLA_PAZIENTI, pid=COL_PAZIENTE_ID,
               nome=COL_PAZIENTE_NOME, cognome=COL_PAZIENTE_COGNOME)
    with _cursor(studio_id) as cur:
        cur.execute(sql, (studio_id,))
        return [dict(r) for r in cur.fetchall()]


def get_paziente(studio_id: int, paziente_id: int) -> Optional[Dict[str, Any]]:
    sql = """
        SELECT {pid} AS id, {nome} AS nome, {cognome} AS cognome
          FROM {tab}
         WHERE studio_id = %s AND {pid} = %s
    """.format(tab=TABELLA_PAZIENTI, pid=COL_PAZIENTE_ID,
               nome=COL_PAZIENTE_NOME, cognome=COL_PAZIENTE_COGNOME)
    with _cursor(studio_id) as cur:
        cur.execute(sql, (studio_id, paziente_id))
        row = cur.fetchone()
    return dict(row) if row else None
