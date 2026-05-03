# -*- coding: utf-8 -*-
"""
modules/consensi_costellazioni/services.py

Logica di business del modulo Consensi Costellazioni.

API pubbliche:
    firma_consenso(...)           → registra una firma (con voci atomiche)
    revoca_consenso(...)          → revoca un consenso esistente
    rinnova_consenso(...)         → sostituisce un consenso superato da nuova versione
    verifica_consensi_richiesti(...) → check pre-azione clinica
    consensi_attivi_paziente(...) → query helper per UI
    template_attivo_per_codice(...) → recupera template attivo per codice

Convenzioni rispettate:
- placeholder %s su Postgres / ? su SQLite (auto-detect)
- riusa auth_audit_log (audit centralizzato del gestionale)
- timestamp con zoneinfo Europe/Rome
- gestione transazioni: commit espliciti, rollback in except
- session_state["user"] del login per popolare firmato_da

NOTA F1: questo file assume che F1 sia stato corretto al deploy:
- senza REFERENCES Pazienti(id) (FK rimosse)
- con o senza cf_audit_log (audit duplicato gestito tramite scelta runtime)
"""

from __future__ import annotations

import hashlib
import json
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Iterable
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

ROME_TZ = ZoneInfo("Europe/Rome")


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
    # psycopg2 DictRow supporta già .items()
    try:
        return dict(row)
    except Exception:
        cols = [d[0] for d in cur.description]
        return dict(zip(cols, row))


def _now_rome() -> datetime:
    return datetime.now(ROME_TZ)


def _parse_jsonb(val) -> Any:
    """SQLite: stringa JSON. Postgres: già dict/list (psycopg2 con jsonb)."""
    if val is None:
        return None
    if isinstance(val, (dict, list)):
        return val
    try:
        return json.loads(val)
    except (TypeError, ValueError):
        return val


# =============================================================================
# AUDIT — riuso centralizzato del gestionale
# =============================================================================

def _audit(
    conn: Any,
    action: str,
    entity: str,
    entity_id: Optional[int] = None,
    meta: Optional[dict] = None,
    user_id: Optional[int] = None,
) -> None:
    """
    Wrapper sopra auth_audit_log esistente del gestionale.

    Best-effort: fallisce silenziosamente per non bloccare l'operazione clinica.
    """
    try:
        ph = _placeholder(conn)
        meta_json = json.dumps(meta or {}, ensure_ascii=False, default=str)

        cur = conn.cursor()
        try:
            if _is_postgres(conn):
                cur.execute(
                    f"INSERT INTO auth_audit_log(user_id, action, entity, entity_id, meta) "
                    f"VALUES ({ph}, {ph}, {ph}, {ph}, {ph}::jsonb)",
                    (user_id, action, entity, str(entity_id) if entity_id else None, meta_json),
                )
            else:
                # SQLite: la tabella di audit potrebbe non esistere in dev locale
                try:
                    cur.execute(
                        f"INSERT INTO auth_audit_log(user_id, action, entity, entity_id, meta) "
                        f"VALUES ({ph}, {ph}, {ph}, {ph}, {ph})",
                        (user_id, action, entity, str(entity_id) if entity_id else None, meta_json),
                    )
                except Exception:
                    return
            conn.commit()
        finally:
            try:
                cur.close()
            except Exception:
                pass
    except Exception as e:
        logger.warning(f"Audit log fallito per {action}/{entity}/{entity_id}: {e}")


# =============================================================================
# RECUPERO TEMPLATE
# =============================================================================

def template_attivo_per_codice(conn: Any, codice: str) -> Optional[dict]:
    """
    Restituisce il template attivo (l'ultima versione attiva) per un codice.

    Returns:
        dict con i campi del template, o None se non trovato.
    """
    ph = _placeholder(conn)
    cur = conn.cursor()
    try:
        cur.execute(
            f"""
            SELECT id, codice, versione, nome, sottocategoria, testo_md,
                   voci, requisiti, base_giuridica, finalita,
                   periodo_conservazione_anni
            FROM cf_template
            WHERE codice = {ph} AND attivo = {'TRUE' if _is_postgres(conn) else '1'}
            ORDER BY data_creazione DESC
            LIMIT 1
            """,
            (codice,)
        )
        row = cur.fetchone()
        if not row:
            return None
        d = _row_to_dict(cur, row)
        d["voci"] = _parse_jsonb(d["voci"])
        d["requisiti"] = _parse_jsonb(d["requisiti"])
        return d
    finally:
        try:
            cur.close()
        except Exception:
            pass


def template_per_id(conn: Any, template_id: int) -> Optional[dict]:
    """Recupera template specifico per id (qualsiasi stato attivo/dismesso)."""
    ph = _placeholder(conn)
    cur = conn.cursor()
    try:
        cur.execute(
            f"""
            SELECT id, codice, versione, nome, sottocategoria, testo_md,
                   voci, requisiti, attivo
            FROM cf_template WHERE id = {ph}
            """,
            (template_id,)
        )
        row = cur.fetchone()
        if not row:
            return None
        d = _row_to_dict(cur, row)
        d["voci"] = _parse_jsonb(d["voci"])
        d["requisiti"] = _parse_jsonb(d["requisiti"])
        return d
    finally:
        try:
            cur.close()
        except Exception:
            pass


# =============================================================================
# VALIDAZIONE VOCI
# =============================================================================

class VoceValidationError(ValueError):
    """Sollevata quando le voci fornite non rispettano i vincoli del template."""


def _valida_voci(template: dict, voci_paziente: dict[str, bool]) -> dict[str, bool]:
    """
    Valida le voci fornite contro la definizione del template.

    Args:
        template: il template (con campo 'voci' parsato come list[dict])
        voci_paziente: dict {codice_voce: True/False} fornito dall'utente

    Returns:
        dict normalizzato con tutte le voci del template (default False per omesse)

    Raises:
        VoceValidationError: se manca una voce obbligatoria o se è False
    """
    voci_definite = template.get("voci") or []
    codici_definiti = {v["codice"] for v in voci_definite}
    codici_obbligatori = {v["codice"] for v in voci_definite if v.get("obbligatorio")}

    # 1. tutte le voci obbligatorie devono essere presenti e True
    for codice_obb in codici_obbligatori:
        valore = voci_paziente.get(codice_obb)
        if valore is None:
            raise VoceValidationError(
                f"Voce obbligatoria '{codice_obb}' non fornita."
            )
        if valore is not True:
            raise VoceValidationError(
                f"Voce obbligatoria '{codice_obb}' deve essere accettata (True)."
            )

    # 2. voci sconosciute (presenti in input ma non nel template) → warning
    voci_sconosciute = set(voci_paziente.keys()) - codici_definiti
    if voci_sconosciute:
        logger.warning(
            f"Voci ignorate (non presenti nel template {template.get('codice')}): "
            f"{voci_sconosciute}"
        )

    # 3. costruisco dict normalizzato: tutte le voci del template, default False
    normalizzato = {}
    for v in voci_definite:
        codice = v["codice"]
        normalizzato[codice] = bool(voci_paziente.get(codice, False))

    return normalizzato


# =============================================================================
# FIRMA CONSENSO
# =============================================================================

def firma_consenso(
    conn: Any,
    paziente_id: int,
    codice_template: str,
    voci: dict[str, bool],
    modalita_firma: str,
    *,
    operatore_username: Optional[str] = None,
    operatore_user_id: Optional[int] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    pdf_blob: Optional[bytes] = None,
    pdf_filename: Optional[str] = None,
    note: Optional[str] = None,
    sostituisce_id: Optional[int] = None,
    token_id: Optional[int] = None,
) -> dict:
    """
    Registra una firma di consenso del paziente.

    Args:
        conn: connessione DB del gestionale
        paziente_id: id del paziente
        codice_template: es. 'costellazioni_individuali'
        voci: dict {codice_voce: True/False} delle risposte del paziente
        modalita_firma: 'cartaceo' | 'click_studio' | 'link_paziente'
        operatore_username: username dell'operatore (da session_state["user"]["username"])
        operatore_user_id: id dell'operatore (per audit log)
        ip_address, user_agent: tracciamento (auto-popolato dalla UI)
        pdf_blob: bytes del PDF (firmato a penna o generato post-firma digitale)
        pdf_filename: nome file PDF
        note: note libere
        sostituisce_id: se rinnovo, id del consenso precedente
        token_id: se firma via link, id del token (cf_token_firma) consumato

    Returns:
        dict con {firma_id, template_id, paziente_id, codice, versione,
                  data_accettazione, voci_normalizzate, pdf_hash}

    Raises:
        ValueError: paziente_id None, modalita_firma non valida
        LookupError: template non trovato per codice
        VoceValidationError: voci non conformi al template
    """
    # --- Validazione input ---
    if not paziente_id:
        raise ValueError("paziente_id è obbligatorio")
    if modalita_firma not in ("cartaceo", "click_studio", "link_paziente"):
        raise ValueError(f"modalita_firma non valida: {modalita_firma}")

    # --- Recupero template attivo ---
    template = template_attivo_per_codice(conn, codice_template)
    if not template:
        raise LookupError(
            f"Nessun template attivo trovato per codice '{codice_template}'. "
            f"Eseguire seed_hook() per popolare i template."
        )

    # --- Validazione voci ---
    voci_normalizzate = _valida_voci(template, voci)

    # --- Calcolo PDF hash (se PDF fornito) ---
    pdf_hash = None
    if pdf_blob:
        pdf_hash = hashlib.sha256(pdf_blob).hexdigest()

    # --- Inserimento atomico (firma + voci + eventuale sostituzione) ---
    ph = _placeholder(conn)
    is_pg = _is_postgres(conn)
    cur = conn.cursor()
    try:
        # 1. Insert in cf_firme con RETURNING (PG) o lastrowid (SQLite)
        if is_pg:
            cur.execute(
                f"""
                INSERT INTO cf_firme (
                    paziente_id, template_id, template_codice, template_versione,
                    modalita_firma, ip_address, user_agent, firmato_da,
                    pdf_blob, pdf_filename, pdf_hash,
                    stato, note, sostituisce_id, firmato_token
                ) VALUES (
                    {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph},
                    {ph}, {ph}, {ph}, 'attivo', {ph}, {ph}, {ph}
                ) RETURNING id, data_accettazione
                """,
                (
                    paziente_id, template["id"], template["codice"], template["versione"],
                    modalita_firma, ip_address, user_agent, operatore_username,
                    pdf_blob, pdf_filename, pdf_hash,
                    note, sostituisce_id,
                    str(token_id) if token_id else None,
                )
            )
            row = cur.fetchone()
            firma_id = row[0]
            data_acc = row[1]
        else:
            cur.execute(
                f"""
                INSERT INTO cf_firme (
                    paziente_id, template_id, template_codice, template_versione,
                    modalita_firma, ip_address, user_agent, firmato_da,
                    pdf_blob, pdf_filename, pdf_hash,
                    stato, note, sostituisce_id, firmato_token
                ) VALUES (
                    {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph},
                    {ph}, {ph}, {ph}, 'attivo', {ph}, {ph}, {ph}
                )
                """,
                (
                    paziente_id, template["id"], template["codice"], template["versione"],
                    modalita_firma, ip_address, user_agent, operatore_username,
                    pdf_blob, pdf_filename, pdf_hash,
                    note, sostituisce_id,
                    str(token_id) if token_id else None,
                )
            )
            firma_id = cur.lastrowid
            data_acc = _now_rome()

        # 2. Insert delle voci atomiche
        for codice_voce, valore in voci_normalizzate.items():
            cur.execute(
                f"""
                INSERT INTO cf_voci (firma_id, codice_voce, valore)
                VALUES ({ph}, {ph}, {ph})
                """,
                (firma_id, codice_voce, valore if is_pg else (1 if valore else 0))
            )

        # 3. Se c'è sostituisce_id, marco il vecchio come 'superseduto'
        if sostituisce_id:
            cur.execute(
                f"""
                UPDATE cf_firme
                SET stato = 'superseduto', sostituito_da_id = {ph}
                WHERE id = {ph} AND stato = 'attivo'
                """,
                (firma_id, sostituisce_id)
            )

        # 4. Se firma via token, marco token consumato
        if token_id:
            cur.execute(
                f"""
                UPDATE cf_token_firma
                SET stato = 'consumato', data_consumo = {'NOW()' if is_pg else 'CURRENT_TIMESTAMP'},
                    firma_id = {ph}
                WHERE id = {ph} AND stato = 'attivo'
                """,
                (firma_id, token_id)
            )

        conn.commit()

        # 5. Audit log (best-effort, fuori transazione)
        _audit(
            conn,
            action="CF_FIRMA_CREATA",
            entity="cf_firme",
            entity_id=firma_id,
            user_id=operatore_user_id,
            meta={
                "paziente_id": paziente_id,
                "codice": template["codice"],
                "versione": template["versione"],
                "modalita": modalita_firma,
                "voci_si": [k for k, v in voci_normalizzate.items() if v],
                "voci_no": [k for k, v in voci_normalizzate.items() if not v],
                "pdf_hash": pdf_hash,
            }
        )

        return {
            "firma_id": firma_id,
            "template_id": template["id"],
            "paziente_id": paziente_id,
            "codice": template["codice"],
            "versione": template["versione"],
            "data_accettazione": data_acc,
            "voci_normalizzate": voci_normalizzate,
            "pdf_hash": pdf_hash,
        }

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
# REVOCA CONSENSO
# =============================================================================

def revoca_consenso(
    conn: Any,
    firma_id: int,
    motivazione: str,
    *,
    modalita_revoca: str = "verbale",
    operatore_username: Optional[str] = None,
    operatore_user_id: Optional[int] = None,
) -> dict:
    """
    Revoca un consenso esistente. Non distruttivo: aggiorna stato e campi revoca.

    Args:
        conn: connessione DB
        firma_id: id del record cf_firme da revocare
        motivazione: testo libero della motivazione
        modalita_revoca: 'scritta' | 'verbale' | 'online' | 'altro'
        operatore_username: chi registra la revoca

    Returns:
        dict con {firma_id, paziente_id, codice, data_revoca, stato_precedente}

    Raises:
        LookupError: firma non trovata
        ValueError: firma già revocata o in stato non revocabile
    """
    if modalita_revoca not in ("scritta", "verbale", "online", "altro"):
        raise ValueError(f"modalita_revoca non valida: {modalita_revoca}")

    ph = _placeholder(conn)
    is_pg = _is_postgres(conn)
    cur = conn.cursor()
    try:
        # Recupero stato corrente
        cur.execute(
            f"""
            SELECT id, paziente_id, template_codice, template_versione, stato
            FROM cf_firme WHERE id = {ph}
            """,
            (firma_id,)
        )
        row = cur.fetchone()
        if not row:
            raise LookupError(f"Firma con id={firma_id} non trovata")

        d = _row_to_dict(cur, row)
        stato_attuale = d["stato"]

        if stato_attuale == "revocato":
            raise ValueError(f"Firma {firma_id} già revocata in precedenza.")
        if stato_attuale == "superseduto":
            raise ValueError(
                f"Firma {firma_id} è già stata sostituita da una versione successiva. "
                f"Revocare la versione attiva."
            )

        # Update revoca
        cur.execute(
            f"""
            UPDATE cf_firme SET
                stato = 'revocato',
                data_revoca = {'NOW()' if is_pg else 'CURRENT_TIMESTAMP'},
                revocato_da = {ph},
                motivazione_revoca = {ph},
                modalita_revoca = {ph}
            WHERE id = {ph}
            """,
            (operatore_username, motivazione, modalita_revoca, firma_id)
        )

        conn.commit()

        _audit(
            conn,
            action="CF_FIRMA_REVOCATA",
            entity="cf_firme",
            entity_id=firma_id,
            user_id=operatore_user_id,
            meta={
                "paziente_id": d["paziente_id"],
                "codice": d["template_codice"],
                "versione": d["template_versione"],
                "modalita_revoca": modalita_revoca,
                "motivazione": motivazione,
                "stato_precedente": stato_attuale,
            }
        )

        return {
            "firma_id": firma_id,
            "paziente_id": d["paziente_id"],
            "codice": d["template_codice"],
            "data_revoca": _now_rome(),
            "stato_precedente": stato_attuale,
        }

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


def rinnova_consenso(
    conn: Any,
    paziente_id: int,
    codice_template: str,
    voci: dict[str, bool],
    modalita_firma: str,
    **kwargs,
) -> dict:
    """
    Sostituisce il consenso attivo del paziente per quel codice con una nuova firma.

    Equivale a firma_consenso() con sostituisce_id pre-popolato dalla firma
    attiva precedente (se esiste).
    """
    # Trova firma attiva precedente
    ph = _placeholder(conn)
    cur = conn.cursor()
    try:
        cur.execute(
            f"""
            SELECT id FROM cf_firme
            WHERE paziente_id = {ph}
              AND template_codice = {ph}
              AND stato = 'attivo'
            ORDER BY data_accettazione DESC
            LIMIT 1
            """,
            (paziente_id, codice_template)
        )
        row = cur.fetchone()
        sostituisce = row[0] if row else None
    finally:
        try:
            cur.close()
        except Exception:
            pass

    return firma_consenso(
        conn=conn,
        paziente_id=paziente_id,
        codice_template=codice_template,
        voci=voci,
        modalita_firma=modalita_firma,
        sostituisce_id=sostituisce,
        **kwargs
    )


# =============================================================================
# QUERY: CONSENSI DEL PAZIENTE
# =============================================================================

def consensi_attivi_paziente(
    conn: Any,
    paziente_id: int,
    *,
    include_storico: bool = False,
) -> list[dict]:
    """
    Restituisce i consensi del paziente con stato e versione.

    Args:
        paziente_id: id paziente
        include_storico: se True, include anche revocati e superseduti

    Returns:
        lista di dict ordinati per data_accettazione DESC, ciascuno con:
            firma_id, codice, versione_firmata, versione_attiva_template,
            stato, da_rinnovare (bool), data_accettazione, modalita_firma,
            voci_si (list[str])
    """
    ph = _placeholder(conn)
    cur = conn.cursor()
    try:
        if include_storico:
            stato_filter = ""
        else:
            stato_filter = "AND f.stato = 'attivo'"

        cur.execute(
            f"""
            SELECT
                f.id AS firma_id,
                f.template_codice,
                f.template_versione,
                f.stato,
                f.data_accettazione,
                f.modalita_firma,
                f.data_revoca,
                t_attivo.versione AS versione_attiva
            FROM cf_firme f
            LEFT JOIN LATERAL (
                SELECT versione FROM cf_template
                WHERE codice = f.template_codice
                  AND attivo = {'TRUE' if _is_postgres(conn) else '1'}
                ORDER BY data_creazione DESC LIMIT 1
            ) t_attivo ON TRUE
            WHERE f.paziente_id = {ph}
              {stato_filter}
            ORDER BY f.data_accettazione DESC
            """
            if _is_postgres(conn) else
            f"""
            SELECT
                f.id AS firma_id,
                f.template_codice,
                f.template_versione,
                f.stato,
                f.data_accettazione,
                f.modalita_firma,
                f.data_revoca,
                (SELECT versione FROM cf_template
                 WHERE codice = f.template_codice AND attivo = 1
                 ORDER BY data_creazione DESC LIMIT 1) AS versione_attiva
            FROM cf_firme f
            WHERE f.paziente_id = {ph}
              {stato_filter}
            ORDER BY f.data_accettazione DESC
            """,
            (paziente_id,)
        )

        rows = cur.fetchall()
        risultati = []
        for row in rows:
            d = _row_to_dict(cur, row)
            d["da_rinnovare"] = (
                d["stato"] == "attivo"
                and d.get("versione_attiva")
                and d["template_versione"] != d["versione_attiva"]
            )
            risultati.append(d)

        # Aggiungo voci_si per ogni firma
        for r in risultati:
            cur.execute(
                f"""
                SELECT codice_voce FROM cf_voci
                WHERE firma_id = {ph} AND valore = {'TRUE' if _is_postgres(conn) else '1'}
                """,
                (r["firma_id"],)
            )
            r["voci_si"] = [v[0] for v in cur.fetchall()]

        return risultati
    finally:
        try:
            cur.close()
        except Exception:
            pass


def firma_attiva_per_codice(
    conn: Any,
    paziente_id: int,
    codice_template: str,
) -> Optional[dict]:
    """
    Restituisce la firma attiva del paziente per un codice template, o None.
    Helper per validazioni rapide.
    """
    ph = _placeholder(conn)
    cur = conn.cursor()
    try:
        cur.execute(
            f"""
            SELECT id, template_versione, data_accettazione, modalita_firma, stato
            FROM cf_firme
            WHERE paziente_id = {ph}
              AND template_codice = {ph}
              AND stato = 'attivo'
            ORDER BY data_accettazione DESC
            LIMIT 1
            """,
            (paziente_id, codice_template)
        )
        row = cur.fetchone()
        return _row_to_dict(cur, row) if row else None
    finally:
        try:
            cur.close()
        except Exception:
            pass


# =============================================================================
# VALIDAZIONE PRE-AZIONE CLINICA
# =============================================================================

# Mappa azione clinica → consensi richiesti.
# Estendibile in futuro per altre azioni del gestionale.
AZIONI_CONSENSI_RICHIESTI = {
    "sessione_costellazioni_individuali": ["costellazioni_individuali"],
    "sessione_costellazioni_gruppo": [
        "costellazioni_individuali",
        "costellazioni_gruppo",
    ],
    "ruolo_rappresentante": [
        "costellazioni_individuali",
        "costellazioni_gruppo",
        "costellazioni_rappresentante",
    ],
    "registrazione_sessione_costellazioni": [
        "costellazioni_individuali",
        "costellazioni_registrazione",
    ],
}


def verifica_consensi_richiesti(
    conn: Any,
    paziente_id: int,
    azione: str,
) -> dict:
    """
    Verifica se il paziente ha tutti i consensi richiesti per un'azione clinica.

    Args:
        azione: chiave di AZIONI_CONSENSI_RICHIESTI

    Returns:
        {
          'ok': bool,
          'azione': str,
          'mancanti': [{'codice', 'motivo'}, ...],
          'da_rinnovare': [{'codice', 'versione_firmata', 'versione_attiva'}, ...],
          'attivi': [{'codice', 'versione', 'firma_id'}, ...],
        }
    """
    if azione not in AZIONI_CONSENSI_RICHIESTI:
        raise ValueError(
            f"Azione '{azione}' sconosciuta. "
            f"Disponibili: {list(AZIONI_CONSENSI_RICHIESTI.keys())}"
        )

    codici_richiesti = AZIONI_CONSENSI_RICHIESTI[azione]
    risultato = {
        "ok": True,
        "azione": azione,
        "mancanti": [],
        "da_rinnovare": [],
        "attivi": [],
    }

    for codice in codici_richiesti:
        firma = firma_attiva_per_codice(conn, paziente_id, codice)

        if not firma:
            risultato["ok"] = False
            risultato["mancanti"].append({
                "codice": codice,
                "motivo": "Nessuna firma attiva per questo consenso",
            })
            continue

        # Confronto versione firmata vs versione attiva
        template_attivo = template_attivo_per_codice(conn, codice)
        if template_attivo and firma["template_versione"] != template_attivo["versione"]:
            risultato["da_rinnovare"].append({
                "codice": codice,
                "firma_id": firma["id"],
                "versione_firmata": firma["template_versione"],
                "versione_attiva": template_attivo["versione"],
            })

        risultato["attivi"].append({
            "codice": codice,
            "firma_id": firma["id"],
            "versione": firma["template_versione"],
            "data_accettazione": firma["data_accettazione"],
        })

    return risultato


# =============================================================================
# TOKEN PER FIRMA A DISTANZA
# =============================================================================

def crea_token_firma(
    conn: Any,
    paziente_id: int,
    codice_template: str,
    *,
    durata_ore: int = 72,
    operatore_username: Optional[str] = None,
) -> dict:
    """
    Crea un token monouso per firma via link inviato al paziente.

    Returns:
        {token, scadenza, paziente_id, template_codice, url_path}

    Il token va incorporato in un URL come:
        https://gestionale.../firma_pubblica?t=<token>
    e la pagina pubblica (F7) lo userà per renderizzare il form di firma.
    """
    template = template_attivo_per_codice(conn, codice_template)
    if not template:
        raise LookupError(f"Template '{codice_template}' non trovato")

    token = secrets.token_urlsafe(32)
    scadenza = _now_rome() + timedelta(hours=durata_ore)

    ph = _placeholder(conn)
    is_pg = _is_postgres(conn)
    cur = conn.cursor()
    try:
        if is_pg:
            cur.execute(
                f"""
                INSERT INTO cf_token_firma (
                    token, paziente_id, template_id, creato_da, data_scadenza, stato
                ) VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, 'attivo')
                RETURNING id
                """,
                (token, paziente_id, template["id"], operatore_username, scadenza)
            )
            token_id = cur.fetchone()[0]
        else:
            cur.execute(
                f"""
                INSERT INTO cf_token_firma (
                    token, paziente_id, template_id, creato_da, data_scadenza, stato
                ) VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, 'attivo')
                """,
                (token, paziente_id, template["id"], operatore_username, scadenza.isoformat())
            )
            token_id = cur.lastrowid

        conn.commit()

        return {
            "token_id": token_id,
            "token": token,
            "scadenza": scadenza,
            "paziente_id": paziente_id,
            "template_codice": codice_template,
            "url_path": f"/firma_pubblica?t={token}",
        }
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


def valida_token_firma(conn: Any, token: str) -> Optional[dict]:
    """
    Valida un token (esistenza, stato, scadenza). Non lo consuma.

    Returns:
        dict con info per renderizzare il form pubblico, o None se invalido.
    """
    ph = _placeholder(conn)
    is_pg = _is_postgres(conn)
    now_clause = "NOW()" if is_pg else "CURRENT_TIMESTAMP"

    cur = conn.cursor()
    try:
        cur.execute(
            f"""
            SELECT t.id, t.paziente_id, t.template_id, t.data_scadenza, t.stato,
                   tpl.codice, tpl.versione, tpl.nome, tpl.testo_md, tpl.voci
            FROM cf_token_firma t
            JOIN cf_template tpl ON tpl.id = t.template_id
            WHERE t.token = {ph}
              AND t.stato = 'attivo'
              AND t.data_scadenza > {now_clause}
            """,
            (token,)
        )
        row = cur.fetchone()
        if not row:
            return None
        d = _row_to_dict(cur, row)
        d["voci"] = _parse_jsonb(d["voci"])
        return d
    finally:
        try:
            cur.close()
        except Exception:
            pass
