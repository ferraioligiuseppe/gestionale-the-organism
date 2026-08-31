# -*- coding: utf-8 -*-
"""Fasce orarie (slot) per eventi a prenotazione — es. screening scolastico:
4 slot all'ora, ogni 15 minuti. Non tocca le tabelle esistenti: aggiunge solo
colonne nuove, in modo idempotente."""
from __future__ import annotations
from datetime import datetime, timedelta, time as dtime

ROME_TZ_NAME = "Europe/Rome"


def ensure_slot_schema(conn) -> None:
    """Aggiunge le colonne slot a ev_eventi e ev_iscrizioni se non esistono già.
    Va richiamata una volta (es. da un bottone admin o al primo uso)."""
    cur = conn.cursor()
    try:
        cur.execute("""
            ALTER TABLE ev_eventi
                ADD COLUMN IF NOT EXISTS slot_abilitati BOOLEAN DEFAULT FALSE,
                ADD COLUMN IF NOT EXISTS slot_durata_minuti INTEGER,
                ADD COLUMN IF NOT EXISTS slot_ora_inizio TIME,
                ADD COLUMN IF NOT EXISTS slot_ora_fine TIME,
                ADD COLUMN IF NOT EXISTS slot_posti INTEGER DEFAULT 1;
        """)
        cur.execute("""
            ALTER TABLE ev_iscrizioni
                ADD COLUMN IF NOT EXISTS slot_orario TIMESTAMP,
                ADD COLUMN IF NOT EXISTS gcal_event_id TEXT;
        """)
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
        except Exception:
            pass


def _placeholder(conn) -> str:
    return "%s" if "psycopg" in str(type(conn)).lower() or hasattr(conn, "_conn") else "?"


def genera_slot(ev: dict) -> list[datetime]:
    """Genera la lista di orari per un evento a slot (stesso giorno di ev['data_ora'])."""
    if not ev.get("slot_abilitati"):
        return []
    data_ora = ev["data_ora"]
    giorno = data_ora.date() if hasattr(data_ora, "date") else data_ora
    ora_i: dtime = ev["slot_ora_inizio"]
    ora_f: dtime = ev["slot_ora_fine"]
    if not ora_i or not ora_f:
        return []
    durata = int(ev.get("slot_durata_minuti") or 15)

    cur_dt = datetime.combine(giorno, ora_i)
    fine_dt = datetime.combine(giorno, ora_f)

    slots = []
    while cur_dt < fine_dt:
        slots.append(cur_dt)
        cur_dt += timedelta(minutes=durata)
    return slots


def posti_occupati_slot(conn, evento_id: int, slot_orario: datetime) -> int:
    """Conta le iscrizioni non annullate per un singolo slot."""
    ph = _placeholder(conn)
    cur = conn.cursor()
    try:
        cur.execute(
            f"""SELECT COUNT(*) FROM ev_iscrizioni
                WHERE evento_id = {ph} AND slot_orario = {ph} AND stato != 'annullata';""",
            (evento_id, slot_orario),
        )
        row = cur.fetchone()
        return int(row[0] if not isinstance(row, dict) else list(row.values())[0])
    finally:
        try:
            cur.close()
        except Exception:
            pass


def slot_con_disponibilita(conn, ev: dict) -> list[dict]:
    """Ritorna [{'orario', 'posti_max', 'occupati', 'liberi'}, ...] per ogni slot del giorno."""
    posti_max = int(ev.get("slot_posti") or 1)
    out = []
    for orario in genera_slot(ev):
        occ = posti_occupati_slot(conn, ev["id"], orario)
        out.append({
            "orario": orario,
            "posti_max": posti_max,
            "occupati": occ,
            "liberi": max(0, posti_max - occ),
        })
    return out


def assegna_slot(conn, iscrizione_id: int, slot_orario: datetime) -> None:
    ph = _placeholder(conn)
    cur = conn.cursor()
    try:
        cur.execute(f"UPDATE ev_iscrizioni SET slot_orario = {ph} WHERE id = {ph};",
                    (slot_orario, iscrizione_id))
        conn.commit()
    finally:
        try:
            cur.close()
        except Exception:
            pass


def salva_gcal_event_id(conn, iscrizione_id: int, gcal_event_id: str) -> None:
    ph = _placeholder(conn)
    cur = conn.cursor()
    try:
        cur.execute(f"UPDATE ev_iscrizioni SET gcal_event_id = {ph} WHERE id = {ph};",
                    (gcal_event_id, iscrizione_id))
        conn.commit()
    finally:
        try:
            cur.close()
        except Exception:
            pass
