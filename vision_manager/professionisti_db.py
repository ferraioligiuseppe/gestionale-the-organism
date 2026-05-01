# -*- coding: utf-8 -*-
"""
modules/professionisti_db.py — Funzioni di accesso DB per la tabella `professionisti`.

Tutte le funzioni accettano una connessione PostgreSQL già aperta (psycopg2).
Lo schema della tabella è documentato in step3_migration.sql.

Convenzioni usate nel resto del gestionale (rispettate qui):
  - placeholder %s per Postgres
  - timestamps in TIMESTAMPTZ (zoneinfo Europe/Rome lato lettura se servisse)
  - ritorno funzioni di lettura: list[dict] o dict | None
  - ritorno funzioni di scrittura: int (id) o bool
"""

from __future__ import annotations

from typing import Optional, List, Dict, Any
from datetime import datetime


# =============================================================================
#  LETTURE
# =============================================================================

def list_professionisti(
    conn,
    studio_id: Optional[int] = None,
    solo_attivi: bool = True,
) -> List[Dict[str, Any]]:
    """Ritorna l'elenco dei professionisti, ordinato per ordine_visualizzazione poi nome.

    Args:
        conn: connessione psycopg2
        studio_id: se valorizzato, filtra per studio. Se None, ritorna tutti.
        solo_attivi: se True (default), esclude i professionisti disattivati.

    Returns:
        list di dict con tutte le colonne (esclusa firma_immagine, troppo grossa).
    """
    where = []
    params: List[Any] = []

    if solo_attivi:
        where.append("attivo = TRUE")

    if studio_id is not None:
        where.append("(studio_id = %s OR studio_id IS NULL)")
        params.append(studio_id)

    where_clause = ("WHERE " + " AND ".join(where)) if where else ""

    sql = f"""
        SELECT
            id, studio_id, auth_user_id,
            nome_completo, qualifica_riga_1, qualifica_riga_2,
            ordine_albo, numero_albo,
            email_professionale, telefono,
            firma_filename, firma_caricata_at,
            (firma_immagine IS NOT NULL) AS ha_firma,
            attivo, is_default, ordine_visualizzazione,
            created_at, updated_at
        FROM professionisti
        {where_clause}
        ORDER BY ordine_visualizzazione ASC, nome_completo ASC, id ASC
    """

    with conn.cursor() as cur:
        cur.execute(sql, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def get_professionista(conn, professionista_id: int, *, includi_firma: bool = False) -> Optional[Dict[str, Any]]:
    """Ritorna un singolo professionista per id, oppure None se non esiste.

    Args:
        professionista_id: id del professionista
        includi_firma: se True, include il blob firma_immagine (default False per
                       performance — la firma serve solo durante la generazione PDF)
    """
    cols_extra = ", firma_immagine" if includi_firma else ""

    sql = f"""
        SELECT
            id, studio_id, auth_user_id,
            nome_completo, qualifica_riga_1, qualifica_riga_2,
            ordine_albo, numero_albo,
            email_professionale, telefono,
            firma_filename, firma_caricata_at,
            (firma_immagine IS NOT NULL) AS ha_firma,
            attivo, is_default, ordine_visualizzazione,
            created_at, updated_at
            {cols_extra}
        FROM professionisti
        WHERE id = %s
    """

    with conn.cursor() as cur:
        cur.execute(sql, (professionista_id,))
        row = cur.fetchone()
        if not row:
            return None
        cols = [d[0] for d in cur.description]
        return dict(zip(cols, row))


def get_professionista_default(conn, studio_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """Ritorna il professionista di default (is_default=TRUE), oppure None se non c'è."""
    where_studio = ""
    params: List[Any] = []
    if studio_id is not None:
        where_studio = "AND (studio_id = %s OR studio_id IS NULL)"
        params.append(studio_id)

    sql = f"""
        SELECT
            id, nome_completo, qualifica_riga_1, qualifica_riga_2,
            ordine_albo, numero_albo,
            (firma_immagine IS NOT NULL) AS ha_firma,
            attivo, is_default
        FROM professionisti
        WHERE attivo = TRUE AND is_default = TRUE
        {where_studio}
        LIMIT 1
    """
    with conn.cursor() as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
        if not row:
            return None
        cols = [d[0] for d in cur.description]
        return dict(zip(cols, row))


# =============================================================================
#  SCRITTURE
# =============================================================================

def crea_professionista(
    conn,
    *,
    nome_completo: str,
    qualifica_riga_1: Optional[str] = None,
    qualifica_riga_2: Optional[str] = None,
    ordine_albo: Optional[str] = None,
    numero_albo: Optional[str] = None,
    email_professionale: Optional[str] = None,
    telefono: Optional[str] = None,
    studio_id: Optional[int] = None,
    auth_user_id: Optional[int] = None,
    attivo: bool = True,
    is_default: bool = False,
    ordine_visualizzazione: int = 0,
    created_by: Optional[int] = None,
) -> int:
    """Crea un nuovo professionista. Ritorna l'id generato.

    Se is_default=True, prima rimette is_default=FALSE su tutti gli altri professionisti
    (dello stesso studio_id) per rispettare il vincolo di unicità.
    """
    if not nome_completo or not nome_completo.strip():
        raise ValueError("Il nome del professionista è obbligatorio")

    with conn.cursor() as cur:
        if is_default:
            cur.execute("""
                UPDATE professionisti
                SET is_default = FALSE
                WHERE is_default = TRUE
                AND COALESCE(studio_id, 0) = COALESCE(%s, 0)
            """, (studio_id,))

        cur.execute("""
            INSERT INTO professionisti (
                studio_id, auth_user_id,
                nome_completo, qualifica_riga_1, qualifica_riga_2,
                ordine_albo, numero_albo,
                email_professionale, telefono,
                attivo, is_default, ordine_visualizzazione,
                created_by, updated_by
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            RETURNING id
        """, (
            studio_id, auth_user_id,
            nome_completo.strip(),
            (qualifica_riga_1 or None),
            (qualifica_riga_2 or None),
            (ordine_albo or None),
            (numero_albo or None),
            (email_professionale or None),
            (telefono or None),
            bool(attivo), bool(is_default), int(ordine_visualizzazione or 0),
            created_by, created_by,
        ))
        new_id = cur.fetchone()[0]
        conn.commit()
        return int(new_id)


def aggiorna_professionista(
    conn,
    professionista_id: int,
    *,
    nome_completo: Optional[str] = None,
    qualifica_riga_1: Optional[str] = None,
    qualifica_riga_2: Optional[str] = None,
    ordine_albo: Optional[str] = None,
    numero_albo: Optional[str] = None,
    email_professionale: Optional[str] = None,
    telefono: Optional[str] = None,
    studio_id: Optional[int] = None,
    attivo: Optional[bool] = None,
    is_default: Optional[bool] = None,
    ordine_visualizzazione: Optional[int] = None,
    updated_by: Optional[int] = None,
) -> bool:
    """Aggiorna i campi specificati. Solo i parametri non-None vengono modificati.

    Per is_default=True, rimette is_default=FALSE su tutti gli altri prima.
    """
    if nome_completo is not None and not nome_completo.strip():
        raise ValueError("Il nome del professionista non può essere vuoto")

    sets: List[str] = []
    params: List[Any] = []

    def _add(field: str, value: Any):
        sets.append(f"{field} = %s")
        params.append(value)

    if nome_completo is not None:        _add("nome_completo", nome_completo.strip())
    if qualifica_riga_1 is not None:     _add("qualifica_riga_1", (qualifica_riga_1 or None))
    if qualifica_riga_2 is not None:     _add("qualifica_riga_2", (qualifica_riga_2 or None))
    if ordine_albo is not None:          _add("ordine_albo", (ordine_albo or None))
    if numero_albo is not None:          _add("numero_albo", (numero_albo or None))
    if email_professionale is not None:  _add("email_professionale", (email_professionale or None))
    if telefono is not None:             _add("telefono", (telefono or None))
    if studio_id is not None:            _add("studio_id", studio_id)
    if attivo is not None:               _add("attivo", bool(attivo))
    if ordine_visualizzazione is not None: _add("ordine_visualizzazione", int(ordine_visualizzazione))
    if updated_by is not None:           _add("updated_by", updated_by)

    if is_default is True:
        # prima rimuovo il default agli altri
        with conn.cursor() as cur:
            cur.execute("""
                SELECT studio_id FROM professionisti WHERE id = %s
            """, (professionista_id,))
            row = cur.fetchone()
            if row:
                target_studio = row[0]
                cur.execute("""
                    UPDATE professionisti
                    SET is_default = FALSE
                    WHERE is_default = TRUE
                    AND id <> %s
                    AND COALESCE(studio_id, 0) = COALESCE(%s, 0)
                """, (professionista_id, target_studio))
        _add("is_default", True)
    elif is_default is False:
        _add("is_default", False)

    if not sets:
        return False  # nulla da aggiornare

    sql = f"UPDATE professionisti SET {', '.join(sets)} WHERE id = %s"
    params.append(professionista_id)

    with conn.cursor() as cur:
        cur.execute(sql, params)
        affected = cur.rowcount
    conn.commit()
    return affected > 0


def imposta_default(conn, professionista_id: int, updated_by: Optional[int] = None) -> bool:
    """Imposta un professionista come default (rimette gli altri a FALSE)."""
    return aggiorna_professionista(conn, professionista_id, is_default=True, updated_by=updated_by)


def disattiva_professionista(conn, professionista_id: int, updated_by: Optional[int] = None) -> bool:
    """Disattiva un professionista senza cancellarlo. Le prescrizioni storiche restano linkate."""
    return aggiorna_professionista(conn, professionista_id, attivo=False, is_default=False, updated_by=updated_by)


def riattiva_professionista(conn, professionista_id: int, updated_by: Optional[int] = None) -> bool:
    """Riattiva un professionista precedentemente disattivato."""
    return aggiorna_professionista(conn, professionista_id, attivo=True, updated_by=updated_by)


# =============================================================================
#  FIRMA
# =============================================================================

def carica_firma(
    conn,
    professionista_id: int,
    png_bytes: bytes,
    filename: str,
    updated_by: Optional[int] = None,
) -> bool:
    """Salva la firma scansionata (immagine PNG) per un professionista.

    Args:
        png_bytes: bytes dell'immagine già processata (idealmente PNG, max ~500KB).
        filename: nome originale del file caricato (per UX).
    """
    if not png_bytes:
        raise ValueError("png_bytes vuoto")

    sql = """
        UPDATE professionisti
        SET firma_immagine = %s,
            firma_filename = %s,
            firma_caricata_at = NOW(),
            updated_by = %s
        WHERE id = %s
    """
    with conn.cursor() as cur:
        cur.execute(sql, (
            psycopg2_bytea(png_bytes),
            filename,
            updated_by,
            professionista_id,
        ))
        ok = cur.rowcount > 0
    conn.commit()
    return ok


def get_firma(conn, professionista_id: int) -> Optional[bytes]:
    """Ritorna i bytes della firma, oppure None se non c'è."""
    with conn.cursor() as cur:
        cur.execute("SELECT firma_immagine FROM professionisti WHERE id = %s", (professionista_id,))
        row = cur.fetchone()
        if not row or row[0] is None:
            return None
        # psycopg2 ritorna memoryview per bytea: convertiamo a bytes
        return bytes(row[0])


def cancella_firma(conn, professionista_id: int, updated_by: Optional[int] = None) -> bool:
    """Rimuove la firma (la riga del professionista resta)."""
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE professionisti
            SET firma_immagine = NULL,
                firma_filename = NULL,
                firma_caricata_at = NULL,
                updated_by = %s
            WHERE id = %s
        """, (updated_by, professionista_id))
        ok = cur.rowcount > 0
    conn.commit()
    return ok


# =============================================================================
#  ELIMINAZIONE
# =============================================================================

def cancella_professionista(conn, professionista_id: int) -> tuple[bool, str]:
    """Elimina definitivamente un professionista.

    NON elimina se ci sono prescrizioni che lo referenziano (per integrità storica).
    In quel caso suggerisce di disattivare invece.

    Returns:
        (success, messaggio). Messaggio è vuoto se success=True.
    """
    with conn.cursor() as cur:
        # Controllo riferimenti
        cur.execute("""
            SELECT count(*) FROM prescrizioni_occhiali
            WHERE professionista_id = %s
        """, (professionista_id,))
        n_ref = cur.fetchone()[0]

        if n_ref > 0:
            return (False,
                    f"Impossibile eliminare: ci sono {n_ref} prescrizioni storiche "
                    f"che fanno riferimento a questo professionista. "
                    f"Disattivalo invece di eliminarlo.")

        cur.execute("DELETE FROM professionisti WHERE id = %s", (professionista_id,))
        ok = cur.rowcount > 0
    conn.commit()
    return (ok, "" if ok else "Prescrittore non trovato")


# =============================================================================
#  Helper interno
# =============================================================================

def psycopg2_bytea(b: bytes):
    """Wrappa bytes per psycopg2 BYTEA insert. Dipende dalla versione di psycopg2."""
    try:
        import psycopg2
        return psycopg2.Binary(b)
    except ImportError:
        # Fallback: alcuni driver accettano bytes direttamente
        return b
