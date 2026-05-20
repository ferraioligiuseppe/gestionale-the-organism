# -*- coding: utf-8 -*-
"""
modules/eventi/db_eventi.py

CRUD del modulo Eventi.

API pubbliche:

    # --- Eventi ---
    crea_evento(...)                  → inserisce un nuovo evento
    get_evento_by_id(conn, id)        → singolo evento per id
    get_evento_by_slug(conn, slug)    → singolo evento per slug (pagina pubblica)
    lista_eventi(conn, ...)           → lista filtrata
    aggiorna_evento(conn, id, ...)    → update campi
    toggle_evento_attivo(...)         → mostra/nascondi
    toggle_iscrizioni_aperte(...)     → apri/chiudi iscrizioni
    elimina_evento(...)               → hard delete (cascade su iscrizioni)
    posti_rimasti(...)                → int o None (se illimitati)
    conta_iscritti(...)               → count per stato

    # --- Iscrizioni ---
    crea_iscrizione(...)              → registra iscritto (auto conferma/lista_attesa)
    get_iscrizione_by_id(conn, id)    → singola iscrizione
    lista_iscrizioni(conn, evento_id) → tutte le iscrizioni di un evento
    email_gia_iscritta(...)           → check pre-form
    annulla_iscrizione(...)           → soft (stato=annullata)
    aggiorna_stato_iscrizione(...)    → cambio stato (es. lista_attesa→confermata)
    promuovi_da_lista_attesa(...)     → promuove il primo iscritto in lista
    aggancia_paziente(...)            → set paziente_id
    mark_email_conferma_inviata(...)  → flag tracking
    mark_email_promemoria_inviata(...)→ flag tracking

    # --- Helper ---
    genera_slug(titolo, data_ora)     → slug url-safe univoco

Convenzioni rispettate:
- placeholder %s su Postgres / ? su SQLite (auto-detect)
- timestamp con zoneinfo Europe/Rome
- gestione transazioni: commit espliciti, rollback in except
- funzioni restituiscono dict, mai tuple grezze
"""

from __future__ import annotations

import logging
import re
import unicodedata
from datetime import datetime, timezone
from typing import Any, Optional
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

ROME_TZ = ZoneInfo("Europe/Rome")

TIPI_VALIDI = ("costellazioni", "webinar", "workshop", "altro")
STATI_VALIDI = ("confermata", "lista_attesa", "annullata")


# =============================================================================
# UTILITY DB (compat Postgres/SQLite)
# =============================================================================

def _is_postgres(conn: Any) -> bool:
    """Heuristic: il wrapper _PgConn del gestionale ha _conn (psycopg2)."""
    return hasattr(conn, "_conn") or "psycopg" in str(type(conn)).lower()


def _placeholder(conn: Any) -> str:
    return "%s" if _is_postgres(conn) else "?"


def _row_to_dict(cur, row) -> Optional[dict]:
    """Converte una row in dict usando cur.description; gestisce DictRow di psycopg2."""
    if row is None:
        return None
    try:
        return dict(row)
    except Exception:
        cols = [d[0] for d in cur.description]
        return dict(zip(cols, row))


def _rows_to_dicts(cur, rows) -> list[dict]:
    if not rows:
        return []
    out = []
    for r in rows:
        d = _row_to_dict(cur, r)
        if d is not None:
            out.append(d)
    return out


def _now_rome() -> datetime:
    return datetime.now(ROME_TZ)


# =============================================================================
# HELPER: SLUG
# =============================================================================

def genera_slug(titolo: str, data_ora: Optional[datetime] = None) -> str:
    """
    Genera uno slug url-safe da titolo + data.
    Esempio: "Costellazione di Gruppo Maggio" + 2025-06-15
             → "costellazione-di-gruppo-maggio-20250615"
    """
    # Normalizza: rimuovi accenti
    t = unicodedata.normalize("NFKD", titolo or "").encode("ascii", "ignore").decode("ascii")
    t = t.lower()
    # Solo alfanumerici e trattini
    t = re.sub(r"[^a-z0-9]+", "-", t).strip("-")
    if not t:
        t = "evento"

    if data_ora is not None:
        t += "-" + data_ora.strftime("%Y%m%d")

    return t[:90]  # max 90 char, lasciamo margine sui 100 dello schema


# =============================================================================
# EVENTI — CRUD
# =============================================================================

def crea_evento(
    conn: Any,
    titolo: str,
    tipo: str,
    data_ora: datetime,
    slug: Optional[str] = None,
    durata_minuti: Optional[int] = None,
    sede: Optional[str] = None,
    descrizione: Optional[str] = None,
    posti_max: Optional[int] = None,
    prezzo: Optional[float] = None,
    fb_event_url: Optional[str] = None,
    immagine_url: Optional[str] = None,
    conduttore: Optional[str] = None,
    attivo: bool = True,
    iscrizioni_aperte: bool = True,
    note_interne: Optional[str] = None,
) -> dict:
    """
    Crea un nuovo evento. Restituisce il dict completo del record creato.
    Se slug non viene passato, viene generato da titolo + data_ora.
    """
    if tipo not in TIPI_VALIDI:
        raise ValueError(f"Tipo non valido: {tipo}. Validi: {TIPI_VALIDI}")
    if not titolo or not titolo.strip():
        raise ValueError("Il titolo è obbligatorio")
    if data_ora is None:
        raise ValueError("data_ora è obbligatoria")

    if not slug:
        slug = genera_slug(titolo, data_ora)

    ph = _placeholder(conn)
    cur = conn.cursor()
    try:
        sql = f"""
            INSERT INTO ev_eventi (
                slug, titolo, tipo, data_ora, durata_minuti, sede,
                descrizione, posti_max, prezzo, fb_event_url, immagine_url,
                conduttore, attivo, iscrizioni_aperte, note_interne
            ) VALUES (
                {ph}, {ph}, {ph}, {ph}, {ph}, {ph},
                {ph}, {ph}, {ph}, {ph}, {ph},
                {ph}, {ph}, {ph}, {ph}
            )
            RETURNING id;
        """
        cur.execute(sql, (
            slug, titolo.strip(), tipo, data_ora, durata_minuti, sede,
            descrizione, posti_max, prezzo, fb_event_url, immagine_url,
            conduttore, attivo, iscrizioni_aperte, note_interne,
        ))
        new_id = cur.fetchone()[0]
        conn.commit()
        logger.info(f"Evento creato: id={new_id}, slug={slug}")
        return get_evento_by_id(conn, new_id)
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            cur.close()
        except Exception:
            pass


def get_evento_by_id(conn: Any, evento_id: int) -> Optional[dict]:
    """Singolo evento per id, None se non esiste."""
    ph = _placeholder(conn)
    cur = conn.cursor()
    try:
        cur.execute(f"SELECT * FROM ev_eventi WHERE id = {ph};", (evento_id,))
        return _row_to_dict(cur, cur.fetchone())
    finally:
        try:
            cur.close()
        except Exception:
            pass


def get_evento_by_slug(conn: Any, slug: str) -> Optional[dict]:
    """Singolo evento per slug (usato dalla pagina pubblica di iscrizione)."""
    ph = _placeholder(conn)
    cur = conn.cursor()
    try:
        cur.execute(f"SELECT * FROM ev_eventi WHERE slug = {ph};", (slug,))
        return _row_to_dict(cur, cur.fetchone())
    finally:
        try:
            cur.close()
        except Exception:
            pass


def lista_eventi(
    conn: Any,
    solo_attivi: bool = False,
    tipo: Optional[str] = None,
    solo_futuri: bool = False,
    limit: Optional[int] = None,
    ordina_desc: bool = True,
) -> list[dict]:
    """
    Lista eventi con filtri opzionali.

    Args:
        solo_attivi: solo eventi con attivo=TRUE
        tipo: filtra per tipo (costellazioni/webinar/workshop/altro)
        solo_futuri: solo data_ora >= ora corrente
        limit: max numero di record
        ordina_desc: True = più recenti prima, False = più vecchi prima
    """
    ph = _placeholder(conn)
    where = []
    params: list[Any] = []

    if solo_attivi:
        where.append("attivo = TRUE" if _is_postgres(conn) else "attivo = 1")
    if tipo:
        if tipo not in TIPI_VALIDI:
            raise ValueError(f"Tipo non valido: {tipo}")
        where.append(f"tipo = {ph}")
        params.append(tipo)
    if solo_futuri:
        where.append(f"data_ora >= {ph}")
        params.append(_now_rome())

    sql = "SELECT * FROM ev_eventi"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY data_ora " + ("DESC" if ordina_desc else "ASC")
    if limit:
        sql += f" LIMIT {int(limit)}"

    cur = conn.cursor()
    try:
        cur.execute(sql, tuple(params))
        return _rows_to_dicts(cur, cur.fetchall())
    finally:
        try:
            cur.close()
        except Exception:
            pass


# Campi modificabili da aggiorna_evento
_CAMPI_AGGIORNABILI = {
    "titolo", "tipo", "data_ora", "durata_minuti", "sede", "descrizione",
    "posti_max", "prezzo", "fb_event_url", "immagine_url", "conduttore",
    "attivo", "iscrizioni_aperte", "note_interne", "slug",
}


def aggiorna_evento(conn: Any, evento_id: int, **campi) -> Optional[dict]:
    """
    Aggiorna i campi passati come kwargs. I campi non passati restano invariati.

    Esempio:
        aggiorna_evento(conn, 5, titolo="Nuovo titolo", posti_max=20)
    """
    if not campi:
        return get_evento_by_id(conn, evento_id)

    sconosciuti = set(campi.keys()) - _CAMPI_AGGIORNABILI
    if sconosciuti:
        raise ValueError(f"Campi non aggiornabili: {sconosciuti}")

    if "tipo" in campi and campi["tipo"] not in TIPI_VALIDI:
        raise ValueError(f"Tipo non valido: {campi['tipo']}")

    ph = _placeholder(conn)
    set_clauses = [f"{k} = {ph}" for k in campi.keys()]
    set_clauses.append("updated_at = NOW()" if _is_postgres(conn) else "updated_at = CURRENT_TIMESTAMP")
    params = list(campi.values()) + [evento_id]

    sql = f"UPDATE ev_eventi SET {', '.join(set_clauses)} WHERE id = {ph};"

    cur = conn.cursor()
    try:
        cur.execute(sql, tuple(params))
        conn.commit()
        logger.info(f"Evento aggiornato: id={evento_id}, campi={list(campi.keys())}")
        return get_evento_by_id(conn, evento_id)
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            cur.close()
        except Exception:
            pass


def toggle_evento_attivo(conn: Any, evento_id: int, attivo: bool) -> bool:
    """Attiva/disattiva visibilità dell'evento. Restituisce True se ha aggiornato una riga."""
    ph = _placeholder(conn)
    cur = conn.cursor()
    try:
        sql_now = "NOW()" if _is_postgres(conn) else "CURRENT_TIMESTAMP"
        cur.execute(
            f"UPDATE ev_eventi SET attivo = {ph}, updated_at = {sql_now} WHERE id = {ph};",
            (attivo, evento_id),
        )
        conn.commit()
        return cur.rowcount > 0
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            cur.close()
        except Exception:
            pass


def toggle_iscrizioni_aperte(conn: Any, evento_id: int, aperte: bool) -> bool:
    """Apri/chiudi le iscrizioni a un evento."""
    ph = _placeholder(conn)
    cur = conn.cursor()
    try:
        sql_now = "NOW()" if _is_postgres(conn) else "CURRENT_TIMESTAMP"
        cur.execute(
            f"UPDATE ev_eventi SET iscrizioni_aperte = {ph}, updated_at = {sql_now} WHERE id = {ph};",
            (aperte, evento_id),
        )
        conn.commit()
        return cur.rowcount > 0
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            cur.close()
        except Exception:
            pass


def elimina_evento(conn: Any, evento_id: int) -> bool:
    """
    Elimina definitivamente l'evento e tutte le sue iscrizioni (cascade).
    Usa con cautela. Per nascondere senza eliminare, usa toggle_evento_attivo(False).
    """
    ph = _placeholder(conn)
    cur = conn.cursor()
    try:
        cur.execute(f"DELETE FROM ev_eventi WHERE id = {ph};", (evento_id,))
        conn.commit()
        logger.warning(f"Evento eliminato (hard delete): id={evento_id}")
        return cur.rowcount > 0
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            cur.close()
        except Exception:
            pass


def conta_iscritti(conn: Any, evento_id: int, stato: str = "confermata") -> int:
    """Conta iscritti per evento, filtrato per stato (default: confermata)."""
    if stato not in STATI_VALIDI:
        raise ValueError(f"Stato non valido: {stato}")
    ph = _placeholder(conn)
    cur = conn.cursor()
    try:
        cur.execute(
            f"SELECT COUNT(*) FROM ev_iscrizioni WHERE evento_id = {ph} AND stato = {ph};",
            (evento_id, stato),
        )
        return int(cur.fetchone()[0])
    finally:
        try:
            cur.close()
        except Exception:
            pass


def posti_rimasti(conn: Any, evento_id: int) -> Optional[int]:
    """
    Posti ancora disponibili.
    - Restituisce None se l'evento ha posti_max NULL (= illimitati).
    - Restituisce 0 se sold out.
    """
    ev = get_evento_by_id(conn, evento_id)
    if not ev:
        return None
    if ev.get("posti_max") is None:
        return None
    confermati = conta_iscritti(conn, evento_id, "confermata")
    return max(0, int(ev["posti_max"]) - confermati)


# =============================================================================
# ISCRIZIONI — CRUD
# =============================================================================

def email_gia_iscritta(conn: Any, evento_id: int, email: str) -> bool:
    """
    True se quell'email è già iscritta a quell'evento (in stato non-annullata).
    Case-insensitive sull'email.
    """
    ph = _placeholder(conn)
    cur = conn.cursor()
    try:
        if _is_postgres(conn):
            cur.execute(
                f"""SELECT 1 FROM ev_iscrizioni
                    WHERE evento_id = {ph}
                      AND lower(email) = lower({ph})
                      AND stato != 'annullata'
                    LIMIT 1;""",
                (evento_id, email),
            )
        else:
            cur.execute(
                f"""SELECT 1 FROM ev_iscrizioni
                    WHERE evento_id = {ph}
                      AND LOWER(email) = LOWER({ph})
                      AND stato != 'annullata'
                    LIMIT 1;""",
                (evento_id, email),
            )
        return cur.fetchone() is not None
    finally:
        try:
            cur.close()
        except Exception:
            pass


def crea_iscrizione(
    conn: Any,
    evento_id: int,
    nome: str,
    cognome: str,
    email: str,
    telefono: Optional[str] = None,
    note: Optional[str] = None,
    paziente_id: Optional[int] = None,
    consenso_privacy: bool = False,
    consenso_marketing: bool = False,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    sorgente: str = "web",
    forza_stato: Optional[str] = None,
) -> dict:
    """
    Crea una nuova iscrizione.

    Lo stato viene calcolato automaticamente:
    - 'confermata' se ci sono posti disponibili (o posti_max è NULL)
    - 'lista_attesa' se l'evento è sold out

    Args:
        forza_stato: se passato, ignora il calcolo automatico (es. registrazione admin)

    Raises:
        ValueError: evento non esiste, iscrizioni chiuse, email duplicata,
                    consenso_privacy mancante
    """
    # Validazioni base
    if not nome or not nome.strip():
        raise ValueError("Nome obbligatorio")
    if not cognome or not cognome.strip():
        raise ValueError("Cognome obbligatorio")
    if not email or "@" not in email:
        raise ValueError("Email non valida")
    if not consenso_privacy and forza_stato is None:
        raise ValueError("Il consenso privacy è obbligatorio per le iscrizioni pubbliche")

    evento = get_evento_by_id(conn, evento_id)
    if not evento:
        raise ValueError(f"Evento {evento_id} non trovato")
    if not evento.get("attivo"):
        raise ValueError("Evento non attivo")
    if not evento.get("iscrizioni_aperte") and forza_stato is None:
        raise ValueError("Iscrizioni chiuse per questo evento")

    if email_gia_iscritta(conn, evento_id, email):
        raise ValueError("Questa email è già iscritta a questo evento")

    # Determina stato
    if forza_stato:
        if forza_stato not in STATI_VALIDI:
            raise ValueError(f"Stato non valido: {forza_stato}")
        stato = forza_stato
    else:
        rimasti = posti_rimasti(conn, evento_id)
        stato = "confermata" if rimasti is None or rimasti > 0 else "lista_attesa"

    ph = _placeholder(conn)
    cur = conn.cursor()
    try:
        sql = f"""
            INSERT INTO ev_iscrizioni (
                evento_id, nome, cognome, email, telefono, note,
                paziente_id, stato, consenso_privacy, consenso_marketing,
                ip_address, user_agent, sorgente
            ) VALUES (
                {ph}, {ph}, {ph}, {ph}, {ph}, {ph},
                {ph}, {ph}, {ph}, {ph},
                {ph}, {ph}, {ph}
            )
            RETURNING id;
        """
        cur.execute(sql, (
            evento_id, nome.strip(), cognome.strip(), email.strip().lower(),
            telefono, note, paziente_id, stato,
            consenso_privacy, consenso_marketing,
            ip_address, user_agent, sorgente,
        ))
        new_id = cur.fetchone()[0]
        conn.commit()
        logger.info(f"Iscrizione creata: id={new_id}, evento={evento_id}, stato={stato}")
        return get_iscrizione_by_id(conn, new_id)
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            cur.close()
        except Exception:
            pass


def get_iscrizione_by_id(conn: Any, iscrizione_id: int) -> Optional[dict]:
    ph = _placeholder(conn)
    cur = conn.cursor()
    try:
        cur.execute(f"SELECT * FROM ev_iscrizioni WHERE id = {ph};", (iscrizione_id,))
        return _row_to_dict(cur, cur.fetchone())
    finally:
        try:
            cur.close()
        except Exception:
            pass


def lista_iscrizioni(
    conn: Any,
    evento_id: int,
    stato: Optional[str] = None,
    ordina_per: str = "created_at",
    ordina_desc: bool = False,
) -> list[dict]:
    """
    Lista iscrizioni di un evento. Filtrabile per stato.
    Ordinabile per created_at (default), cognome, email.
    """
    if stato and stato not in STATI_VALIDI:
        raise ValueError(f"Stato non valido: {stato}")
    if ordina_per not in ("created_at", "cognome", "email", "stato"):
        raise ValueError(f"Ordinamento non valido: {ordina_per}")

    ph = _placeholder(conn)
    where = [f"evento_id = {ph}"]
    params: list[Any] = [evento_id]
    if stato:
        where.append(f"stato = {ph}")
        params.append(stato)

    sql = f"""
        SELECT * FROM ev_iscrizioni
        WHERE {' AND '.join(where)}
        ORDER BY {ordina_per} {'DESC' if ordina_desc else 'ASC'};
    """

    cur = conn.cursor()
    try:
        cur.execute(sql, tuple(params))
        return _rows_to_dicts(cur, cur.fetchall())
    finally:
        try:
            cur.close()
        except Exception:
            pass


def annulla_iscrizione(conn: Any, iscrizione_id: int) -> bool:
    """Soft delete: imposta stato='annullata'. Restituisce True se modificata."""
    return aggiorna_stato_iscrizione(conn, iscrizione_id, "annullata")


def aggiorna_stato_iscrizione(conn: Any, iscrizione_id: int, nuovo_stato: str) -> bool:
    if nuovo_stato not in STATI_VALIDI:
        raise ValueError(f"Stato non valido: {nuovo_stato}")
    ph = _placeholder(conn)
    cur = conn.cursor()
    try:
        cur.execute(
            f"UPDATE ev_iscrizioni SET stato = {ph} WHERE id = {ph};",
            (nuovo_stato, iscrizione_id),
        )
        conn.commit()
        logger.info(f"Iscrizione {iscrizione_id}: stato → {nuovo_stato}")
        return cur.rowcount > 0
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            cur.close()
        except Exception:
            pass


def promuovi_da_lista_attesa(conn: Any, evento_id: int) -> Optional[dict]:
    """
    Promuove a 'confermata' la prima iscrizione in 'lista_attesa' (per created_at).
    Da usare quando qualcuno annulla e si libera un posto.

    Restituisce l'iscrizione promossa, o None se la lista d'attesa è vuota.
    """
    iscrizioni_attesa = lista_iscrizioni(conn, evento_id, stato="lista_attesa")
    if not iscrizioni_attesa:
        return None
    # La più vecchia (lista già ordinata per created_at ASC di default)
    prima = iscrizioni_attesa[0]
    aggiorna_stato_iscrizione(conn, prima["id"], "confermata")
    logger.info(f"Promossa da lista_attesa → confermata: iscrizione {prima['id']}")
    return get_iscrizione_by_id(conn, prima["id"])


def aggancia_paziente(conn: Any, iscrizione_id: int, paziente_id: Optional[int]) -> bool:
    """Collega l'iscrizione a un paziente esistente (o scollega passando None)."""
    ph = _placeholder(conn)
    cur = conn.cursor()
    try:
        cur.execute(
            f"UPDATE ev_iscrizioni SET paziente_id = {ph} WHERE id = {ph};",
            (paziente_id, iscrizione_id),
        )
        conn.commit()
        return cur.rowcount > 0
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            cur.close()
        except Exception:
            pass


def mark_email_conferma_inviata(conn: Any, iscrizione_id: int) -> bool:
    """Marca l'email di conferma come inviata, registra timestamp."""
    ph = _placeholder(conn)
    cur = conn.cursor()
    try:
        sql_now = "NOW()" if _is_postgres(conn) else "CURRENT_TIMESTAMP"
        true_val = True if _is_postgres(conn) else 1
        cur.execute(
            f"""UPDATE ev_iscrizioni
                SET email_conferma_inviata = {ph}, email_conferma_ts = {sql_now}
                WHERE id = {ph};""",
            (true_val, iscrizione_id),
        )
        conn.commit()
        return cur.rowcount > 0
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            cur.close()
        except Exception:
            pass


def mark_email_promemoria_inviata(conn: Any, iscrizione_id: int) -> bool:
    """Marca l'email di promemoria come inviata, registra timestamp."""
    ph = _placeholder(conn)
    cur = conn.cursor()
    try:
        sql_now = "NOW()" if _is_postgres(conn) else "CURRENT_TIMESTAMP"
        true_val = True if _is_postgres(conn) else 1
        cur.execute(
            f"""UPDATE ev_iscrizioni
                SET email_promemoria_inviata = {ph}, email_promemoria_ts = {sql_now}
                WHERE id = {ph};""",
            (true_val, iscrizione_id),
        )
        conn.commit()
        return cur.rowcount > 0
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            cur.close()
        except Exception:
            pass


# =============================================================================
# PROMEMORIA AUTOMATICI (48h / 24h prima evento)
# =============================================================================

def eventi_con_promemoria_da_inviare(conn: Any) -> list[dict]:
    """
    Ritorna gli eventi futuri per cui c'è almeno un promemoria da inviare ORA.

    Per ogni evento calcola le finestre temporali:
      - 48h: evento tra ~46h e ~50h da adesso → manda promemoria '48h'
      - 24h: evento tra ~22h e ~26h da adesso → manda promemoria '24h'

    Le finestre larghe (±2h) garantiscono che un cron giornaliero non perda
    eventi anche se gira a orari leggermente diversi.

    Ritorna lista di dict: {evento: {...}, tipi: ['48h', '24h']}
    """
    from datetime import timedelta

    now = datetime.now(ROME_TZ)
    ph = _placeholder(conn)

    cur = conn.cursor()
    try:
        # Prendo tutti gli eventi futuri (entro 3 giorni) con iscrizioni aperte/confermabili
        limite = now + timedelta(days=3)
        cur.execute(
            f"""SELECT * FROM ev_eventi
                WHERE data_ora >= {ph} AND data_ora <= {ph}
                ORDER BY data_ora ASC;""",
            (now, limite),
        )
        eventi = _rows_to_dicts(cur, cur.fetchall())
    finally:
        try:
            cur.close()
        except Exception:
            pass

    risultati = []
    for ev in eventi:
        dt = ev["data_ora"]
        # SQLite restituisce stringhe ISO; Postgres restituisce datetime.
        if isinstance(dt, str):
            try:
                dt = datetime.fromisoformat(dt)
            except ValueError:
                # Formato non standard: salto questo evento
                continue
        # Normalizzo a aware Rome
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc).astimezone(ROME_TZ)
        else:
            dt = dt.astimezone(ROME_TZ)

        ore_mancanti = (dt - now).total_seconds() / 3600.0

        tipi = []
        # Finestra 48h: tra 46 e 50 ore
        if 46 <= ore_mancanti <= 50:
            tipi.append("48h")
        # Finestra 24h: tra 22 e 26 ore
        if 22 <= ore_mancanti <= 26:
            tipi.append("24h")

        if tipi:
            risultati.append({"evento": ev, "tipi": tipi, "ore_mancanti": round(ore_mancanti, 1)})

    return risultati


def iscritti_senza_promemoria(conn: Any, evento_id: int, tipo: str) -> list[dict]:
    """
    Ritorna gli iscritti confermati di un evento che NON hanno ancora ricevuto
    il promemoria del tipo specificato ('48h' o '24h').
    """
    if tipo not in ("48h", "24h"):
        raise ValueError(f"Tipo promemoria non valido: {tipo}")

    col = "promemoria_48h_inviato" if tipo == "48h" else "promemoria_24h_inviato"
    ph = _placeholder(conn)
    false_val = False if _is_postgres(conn) else 0

    cur = conn.cursor()
    try:
        cur.execute(
            f"""SELECT * FROM ev_iscrizioni
                WHERE evento_id = {ph}
                  AND stato = 'confermata'
                  AND {col} = {ph}
                ORDER BY created_at ASC;""",
            (evento_id, false_val),
        )
        return _rows_to_dicts(cur, cur.fetchall())
    finally:
        try:
            cur.close()
        except Exception:
            pass


def marca_promemoria_inviato(conn: Any, iscrizione_id: int, tipo: str) -> bool:
    """
    Segna che il promemoria (48h o 24h) è stato inviato a una iscrizione.
    """
    if tipo not in ("48h", "24h"):
        raise ValueError(f"Tipo promemoria non valido: {tipo}")

    col_flag = "promemoria_48h_inviato" if tipo == "48h" else "promemoria_24h_inviato"
    col_ts = "promemoria_48h_ts" if tipo == "48h" else "promemoria_24h_ts"
    ph = _placeholder(conn)
    sql_now = "NOW()" if _is_postgres(conn) else "CURRENT_TIMESTAMP"
    true_val = True if _is_postgres(conn) else 1

    cur = conn.cursor()
    try:
        cur.execute(
            f"""UPDATE ev_iscrizioni
                SET {col_flag} = {ph}, {col_ts} = {sql_now}
                WHERE id = {ph};""",
            (true_val, iscrizione_id),
        )
        conn.commit()
        return cur.rowcount > 0
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            cur.close()
        except Exception:
            pass
