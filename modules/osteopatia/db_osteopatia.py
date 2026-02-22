from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
import json
import datetime as dt

def _json(v: Any) -> str:
    return json.dumps(v or {}, ensure_ascii=False)

def _row_to_dict(cols: List[str], row: Tuple[Any, ...]) -> Dict[str, Any]:
    return {cols[i]: row[i] for i in range(len(cols))}

# ---------------------------
# ANAMNESI
# ---------------------------

def insert_anamnesi(conn, paziente_id: int, payload: Dict[str, Any]) -> int:
    q = """
    INSERT INTO osteo_anamnesi (
      paziente_id, data_anamnesi,
      motivo, dolore_sede, dolore_intensita, dolore_durata, aggravanti, allevianti,
      storia_clinica, area_neuro_post, stile_vita, area_pediatrica,
      valutazione, ipotesi
    ) VALUES (
      %(paziente_id)s, %(data_anamnesi)s,
      %(motivo)s, %(dolore_sede)s, %(dolore_intensita)s, %(dolore_durata)s, %(aggravanti)s, %(allevianti)s,
      %(storia_clinica)s::jsonb, %(area_neuro_post)s::jsonb, %(stile_vita)s::jsonb, %(area_pediatrica)s::jsonb,
      %(valutazione)s, %(ipotesi)s
    )
    RETURNING id;
    """
    data = {
        "paziente_id": paziente_id,
        "data_anamnesi": payload.get("data_anamnesi") or dt.date.today(),
        "motivo": payload.get("motivo"),
        "dolore_sede": payload.get("dolore_sede"),
        "dolore_intensita": payload.get("dolore_intensita"),
        "dolore_durata": payload.get("dolore_durata"),
        "aggravanti": payload.get("aggravanti"),
        "allevianti": payload.get("allevianti"),
        "storia_clinica": _json(payload.get("storia_clinica")),
        "area_neuro_post": _json(payload.get("area_neuro_post")),
        "stile_vita": _json(payload.get("stile_vita")),
        "area_pediatrica": _json(payload.get("area_pediatrica")),
        "valutazione": payload.get("valutazione"),
        "ipotesi": payload.get("ipotesi"),
    }
    cur = conn.cursor()
    try:
        cur.execute(q, data)
        anamnesi_id = cur.fetchone()[0]
    finally:
        try: cur.close()
        except Exception: pass
    conn.commit()
    return int(anamnesi_id)

def list_anamnesi(conn, paziente_id: int) -> List[Dict[str, Any]]:
    q = """
    SELECT id, data_anamnesi, motivo, dolore_sede, dolore_intensita, created_at
    FROM osteo_anamnesi
    WHERE paziente_id = %s
    ORDER BY data_anamnesi DESC, id DESC;
    """
    cur = conn.cursor()
    try:
        cur.execute(q, (paziente_id,))
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
    finally:
        try: cur.close()
        except Exception: pass
    return [_row_to_dict(cols, r) for r in rows]

def get_anamnesi(conn, anamnesi_id: int) -> Optional[Dict[str, Any]]:
    q = "SELECT * FROM osteo_anamnesi WHERE id = %s;"
    cur = conn.cursor()
    try:
        cur.execute(q, (anamnesi_id,))
        row = cur.fetchone()
        if not row:
            return None
        cols = [d[0] for d in cur.description]
    finally:
        try: cur.close()
        except Exception: pass
    return _row_to_dict(cols, row)

# ---------------------------
# SEDUTE
# ---------------------------

def insert_seduta(conn, paziente_id: int, payload: Dict[str, Any]) -> int:
    q = """
    INSERT INTO osteo_seduta (
      paziente_id, anamnesi_id,
      data_seduta, operatore, tipo_seduta,
      dolore_pre, note_pre,
      tecniche, descrizione,
      risposta, dolore_post, reazioni,
      indicazioni, prossimo_step
    ) VALUES (
      %(paziente_id)s, %(anamnesi_id)s,
      %(data_seduta)s, %(operatore)s, %(tipo_seduta)s,
      %(dolore_pre)s, %(note_pre)s,
      %(tecniche)s::jsonb, %(descrizione)s,
      %(risposta)s, %(dolore_post)s, %(reazioni)s,
      %(indicazioni)s, %(prossimo_step)s
    )
    RETURNING id;
    """
    data = {
        "paziente_id": paziente_id,
        "anamnesi_id": payload.get("anamnesi_id"),
        "data_seduta": payload.get("data_seduta") or dt.date.today(),
        "operatore": payload.get("operatore"),
        "tipo_seduta": payload.get("tipo_seduta"),
        "dolore_pre": payload.get("dolore_pre"),
        "note_pre": payload.get("note_pre"),
        "tecniche": _json(payload.get("tecniche")),
        "descrizione": payload.get("descrizione"),
        "risposta": payload.get("risposta"),
        "dolore_post": payload.get("dolore_post"),
        "reazioni": payload.get("reazioni"),
        "indicazioni": payload.get("indicazioni"),
        "prossimo_step": payload.get("prossimo_step"),
    }
    cur = conn.cursor()
    try:
        cur.execute(q, data)
        seduta_id = cur.fetchone()[0]
    finally:
        try: cur.close()
        except Exception: pass
    conn.commit()
    return int(seduta_id)

def list_sedute(conn, paziente_id: int) -> List[Dict[str, Any]]:
    q = """
    SELECT id, data_seduta, tipo_seduta, operatore, dolore_pre, dolore_post, created_at
    FROM osteo_seduta
    WHERE paziente_id = %s
    ORDER BY data_seduta DESC, id DESC;
    """
    cur = conn.cursor()
    try:
        cur.execute(q, (paziente_id,))
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
    finally:
        try: cur.close()
        except Exception: pass
    return [_row_to_dict(cols, r) for r in rows]

def get_seduta(conn, seduta_id: int) -> Optional[Dict[str, Any]]:
    q = "SELECT * FROM osteo_seduta WHERE id = %s;"
    cur = conn.cursor()
    try:
        cur.execute(q, (seduta_id,))
        row = cur.fetchone()
        if not row:
            return None
        cols = [d[0] for d in cur.description]
    finally:
        try: cur.close()
        except Exception: pass
    return _row_to_dict(cols, row)
