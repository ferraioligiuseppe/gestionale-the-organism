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

def list_anamnesi(conn, paziente_id: int, include_deleted: bool = False) -> List[Dict[str, Any]]:
    where = "WHERE paziente_id = %s"
    # se la colonna is_deleted esiste, filtriamo (Postgres: la condizione su colonna inesistente darebbe errore)
    # quindi facciamo una query robusta che tenta prima con is_deleted e, se fallisce, ripiega.
    base_select = """
    SELECT id, data_anamnesi, tipo_seduta, operatore, dolore_pre, dolore_post, created_at
    FROM osteo_anamnesi
    {where_clause}
    ORDER BY data_anamnesi DESC, id DESC;
    """
    if "osteo_anamnesi" == "osteo_anamnesi":
        base_select = """
        SELECT id, data_anamnesi, motivo, dolore_sede, dolore_intensita, created_at
        FROM osteo_anamnesi
        {where_clause}
        ORDER BY data_anamnesi DESC, id DESC;
        """

    def _run(where_clause: str):
        q = base_select.format(where_clause=where_clause)
        cur = conn.cursor()
        try:
            cur.execute(q, (paziente_id,))
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]
        finally:
            try: cur.close()
            except Exception: pass
        return [_row_to_dict(cols, r) for r in rows]

    if include_deleted:
        return _run(where)
    # prova con filtro is_deleted
    try:
        return _run(where + " AND is_deleted = FALSE")
    except Exception:
        # fallback per schema vecchio (senza colonna)
        return _run(where)




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

def list_sedute(conn, paziente_id: int, include_deleted: bool = False) -> List[Dict[str, Any]]:
    where = "WHERE paziente_id = %s"
    # se la colonna is_deleted esiste, filtriamo (Postgres: la condizione su colonna inesistente darebbe errore)
    # quindi facciamo una query robusta che tenta prima con is_deleted e, se fallisce, ripiega.
    base_select = """
    SELECT id, data_seduta, tipo_seduta, operatore, dolore_pre, dolore_post, created_at
    FROM osteo_seduta
    {where_clause}
    ORDER BY data_seduta DESC, id DESC;
    """
    if "osteo_seduta" == "osteo_anamnesi":
        base_select = """
        SELECT id, data_anamnesi, motivo, dolore_sede, dolore_intensita, created_at
        FROM osteo_anamnesi
        {where_clause}
        ORDER BY data_anamnesi DESC, id DESC;
        """

    def _run(where_clause: str):
        q = base_select.format(where_clause=where_clause)
        cur = conn.cursor()
        try:
            cur.execute(q, (paziente_id,))
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]
        finally:
            try: cur.close()
            except Exception: pass
        return [_row_to_dict(cols, r) for r in rows]

    if include_deleted:
        return _run(where)
    # prova con filtro is_deleted
    try:
        return _run(where + " AND is_deleted = FALSE")
    except Exception:
        # fallback per schema vecchio (senza colonna)
        return _run(where)




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


# ---------------------------
# UPDATE / DELETE (soft) / RESTORE
# ---------------------------

def update_anamnesi(conn, anamnesi_id: int, payload: Dict[str, Any], updated_by: Optional[str] = None) -> None:
    q = """
    UPDATE osteo_anamnesi SET
      data_anamnesi=%(data_anamnesi)s,
      motivo=%(motivo)s,
      dolore_sede=%(dolore_sede)s,
      dolore_intensita=%(dolore_intensita)s,
      dolore_durata=%(dolore_durata)s,
      aggravanti=%(aggravanti)s,
      allevianti=%(allevianti)s,
      storia_clinica=%(storia_clinica)s::jsonb,
      area_neuro_post=%(area_neuro_post)s::jsonb,
      stile_vita=%(stile_vita)s::jsonb,
      area_pediatrica=%(area_pediatrica)s::jsonb,
      valutazione=%(valutazione)s,
      ipotesi=%(ipotesi)s,
      updated_by=%(updated_by)s
    WHERE id=%(id)s;
    """
    data = dict(payload)
    data["id"] = anamnesi_id
    data["updated_by"] = updated_by
    # normalizza json
    data["storia_clinica"] = _json(payload.get("storia_clinica"))
    data["area_neuro_post"] = _json(payload.get("area_neuro_post"))
    data["stile_vita"] = _json(payload.get("stile_vita"))
    data["area_pediatrica"] = _json(payload.get("area_pediatrica"))

    cur = conn.cursor()
    try:
        cur.execute(q, data)
    finally:
        try: cur.close()
        except Exception: pass
    conn.commit()

def soft_delete_anamnesi(conn, anamnesi_id: int, deleted_by: Optional[str] = None) -> None:
    q = """
    UPDATE osteo_anamnesi
    SET is_deleted=TRUE, deleted_at=NOW(), deleted_by=%s
    WHERE id=%s;
    """
    cur = conn.cursor()
    try:
        cur.execute(q, (deleted_by, anamnesi_id))
    finally:
        try: cur.close()
        except Exception: pass
    conn.commit()

def restore_anamnesi(conn, anamnesi_id: int) -> None:
    q = """
    UPDATE osteo_anamnesi
    SET is_deleted=FALSE, deleted_at=NULL, deleted_by=NULL
    WHERE id=%s;
    """
    cur = conn.cursor()
    try:
        cur.execute(q, (anamnesi_id,))
    finally:
        try: cur.close()
        except Exception: pass
    conn.commit()

def update_seduta(conn, seduta_id: int, payload: Dict[str, Any], updated_by: Optional[str] = None) -> None:
    q = """
    UPDATE osteo_seduta SET
      anamnesi_id=%(anamnesi_id)s,
      data_seduta=%(data_seduta)s,
      operatore=%(operatore)s,
      tipo_seduta=%(tipo_seduta)s,
      dolore_pre=%(dolore_pre)s,
      note_pre=%(note_pre)s,
      tecniche=%(tecniche)s::jsonb,
      descrizione=%(descrizione)s,
      risposta=%(risposta)s,
      dolore_post=%(dolore_post)s,
      reazioni=%(reazioni)s,
      indicazioni=%(indicazioni)s,
      prossimo_step=%(prossimo_step)s,
      updated_by=%(updated_by)s
    WHERE id=%(id)s;
    """
    data = dict(payload)
    data["id"] = seduta_id
    data["updated_by"] = updated_by
    data["tecniche"] = _json(payload.get("tecniche"))

    cur = conn.cursor()
    try:
        cur.execute(q, data)
    finally:
        try: cur.close()
        except Exception: pass
    conn.commit()

def soft_delete_seduta(conn, seduta_id: int, deleted_by: Optional[str] = None) -> None:
    q = """
    UPDATE osteo_seduta
    SET is_deleted=TRUE, deleted_at=NOW(), deleted_by=%s
    WHERE id=%s;
    """
    cur = conn.cursor()
    try:
        cur.execute(q, (deleted_by, seduta_id))
    finally:
        try: cur.close()
        except Exception: pass
    conn.commit()

def restore_seduta(conn, seduta_id: int) -> None:
    q = """
    UPDATE osteo_seduta
    SET is_deleted=FALSE, deleted_at=NULL, deleted_by=NULL
    WHERE id=%s;
    """
    cur = conn.cursor()
    try:
        cur.execute(q, (seduta_id,))
    finally:
        try: cur.close()
        except Exception: pass
    conn.commit()
