# -*- coding: utf-8 -*-
# modules/public_questionnaires.py
"""
Sistema unificato per questionari pubblici PNEV / The Organism.

Design:
- Una sola tabella `public_tokens` (sostituisce questionari_links)
- Postgres-native (%s), retrocompatibile SQLite
- Estendibile: aggiungere un questionario = aggiungere una chiave in REGISTRY
- Pagina pubblica: pages/pnev_pubblico.py
"""
from __future__ import annotations

import hmac
import hashlib
import json
import secrets
import string
from datetime import datetime, timedelta, timezone, date
from typing import Any, Dict, Optional, Tuple

import streamlit as st

# ── CONFIGURAZIONE ────────────────────────────────────────────────────────────

def _db_backend() -> str:
    """Rileva se stiamo usando postgres o sqlite."""
    try:
        from modules.app_core import _DB_BACKEND
        return _DB_BACKEND
    except Exception:
        pass
    try:
        url = st.secrets.get("db", {}).get("DATABASE_URL", "") or \
              st.secrets.get("DATABASE_URL", "") or ""
        return "postgres" if url else "sqlite"
    except Exception:
        return "sqlite"

def _ph() -> str:
    """Placeholder corretto per il DB attivo."""
    return "%s" if _db_backend() == "postgres" else "?"

def _get_conn():
    from modules.app_core import get_connection
    return get_connection()

def _token_secret() -> str:
    try:
        return str(st.secrets.get("public_links", {}).get("TOKEN_SECRET", "the-organism-default-secret"))
    except Exception:
        return "the-organism-default-secret"

def _public_base_url() -> str:
    try:
        return str(st.secrets.get("public_links", {}).get("BASE_URL", "")).rstrip("/")
    except Exception:
        return ""

def _default_ttl_days() -> int:
    try:
        return int(st.secrets.get("public_links", {}).get("DEFAULT_TTL_DAYS", 7))
    except Exception:
        return 7

def _hash_token(token: str) -> str:
    key = _token_secret().encode("utf-8")
    return hmac.new(key, token.encode("utf-8"), hashlib.sha256).hexdigest()

# ── REGISTRY QUESTIONARI ──────────────────────────────────────────────────────
# Per aggiungere un nuovo questionario: inserisci una chiave qui.
# "label" = nome leggibile, "page_param" = valore ?q= nel link

REGISTRY: Dict[str, Dict[str, Any]] = {
    "INPPS": {
        "label": "Screening INPPS – Genitori",
        "page_param": "INPPS",
        "descrizione": "Questionario di screening neurosviluppo per i genitori (bambini 4-17 anni).",
    },
    "INPPS_ADULTI": {
        "label": "Screening INPPS – Adulti",
        "page_param": "INPPS_ADULTI",
        "descrizione": "Questionario di screening neurosviluppo autocompilato (adulti).",
    },
    # Aggiungi qui futuri questionari:
    # "MIOFUNZIONALE": {...},
    # "SPORT_VISION": {...},
}

# ── INIT DB ───────────────────────────────────────────────────────────────────

def init_public_tokens_table():
    """Crea la tabella public_tokens se non esiste. Idempotente."""
    conn = _get_conn()
    cur = conn.cursor()
    try:
        if _db_backend() == "postgres":
            cur.execute("""
                CREATE TABLE IF NOT EXISTS public_tokens (
                    id          BIGSERIAL PRIMARY KEY,
                    paziente_id INTEGER   NOT NULL,
                    questionario TEXT     NOT NULL,
                    token_hash  TEXT      NOT NULL UNIQUE,
                    nome_paziente TEXT    NOT NULL DEFAULT '',
                    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
                    expires_at  TIMESTAMPTZ NOT NULL,
                    used_at     TIMESTAMPTZ,
                    meta_json   JSONB
                )
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_public_tokens_hash
                ON public_tokens(token_hash)
            """)
        else:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS public_tokens (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    paziente_id  INTEGER NOT NULL,
                    questionario TEXT    NOT NULL,
                    token_hash   TEXT    NOT NULL UNIQUE,
                    nome_paziente TEXT   NOT NULL DEFAULT '',
                    created_at   TEXT    NOT NULL,
                    expires_at   TEXT    NOT NULL,
                    used_at      TEXT,
                    meta_json    TEXT
                )
            """)
        conn.commit()
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        raise e
    finally:
        cur.close()

# ── CREAZIONE TOKEN ───────────────────────────────────────────────────────────

def create_public_token(
    paziente_id: int,
    questionario: str,
    nome_paziente: str = "",
    ttl_days: Optional[int] = None,
    meta: Optional[Dict] = None,
) -> str:
    """
    Crea un token sicuro per un questionario pubblico.
    Restituisce il token in chiaro (da inviare al paziente).
    Nel DB viene salvato solo l'hash SHA-256.
    """
    if questionario not in REGISTRY:
        raise ValueError(f"Questionario '{questionario}' non nel registry. Aggiungerlo in REGISTRY.")

    ttl = ttl_days or _default_ttl_days()
    token = secrets.token_urlsafe(32)
    token_hash = _hash_token(token)
    expires_at = datetime.now(timezone.utc) + timedelta(days=ttl)
    ph = _ph()

    conn = _get_conn()
    cur = conn.cursor()
    try:
        meta_str = json.dumps(meta or {})
        if _db_backend() == "postgres":
            cur.execute(f"""
                INSERT INTO public_tokens
                    (paziente_id, questionario, token_hash, nome_paziente, expires_at, meta_json)
                VALUES ({ph},{ph},{ph},{ph},{ph},{ph}::jsonb)
            """, (paziente_id, questionario, token_hash, nome_paziente,
                  expires_at.isoformat(), meta_str))
        else:
            cur.execute(f"""
                INSERT INTO public_tokens
                    (paziente_id, questionario, token_hash, nome_paziente, created_at, expires_at, meta_json)
                VALUES ({ph},{ph},{ph},{ph},{ph},{ph},{ph})
            """, (paziente_id, questionario, token_hash, nome_paziente,
                  datetime.now(timezone.utc).isoformat(),
                  expires_at.isoformat(), meta_str))
        conn.commit()
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        raise e
    finally:
        cur.close()

    return token


def build_public_url(token: str, questionario: str) -> str:
    """Costruisce l'URL completo per il paziente."""
    base = _public_base_url()
    if not base:
        return f"[BASE_URL mancante in Secrets] ?q={questionario}&t={token}"
    return f"{base}/pnev_pubblico?q={questionario}&t={token}"


def build_whatsapp_message(token: str, questionario: str, nome_paziente: str, ttl_days: int) -> str:
    """Testo pronto da inviare via WhatsApp/SMS."""
    url = build_public_url(token, questionario)
    reg = REGISTRY.get(questionario, {})
    return (
        f"Gentile {nome_paziente},\n\n"
        f"La invitiamo a compilare il questionario dello Studio The Organism:\n"
        f"📋 {reg.get('label', questionario)}\n\n"
        f"🔗 {url}\n\n"
        f"Il link è valido per {ttl_days} giorni.\n\n"
        f"Cordiali saluti,\n"
        f"Studio The Organism\n"
        f"Dott. Giuseppe Ferraioli\n"
        f"📞 0815152334"
    )

# ── VALIDAZIONE TOKEN ─────────────────────────────────────────────────────────

def validate_public_token(token: str, questionario: str) -> Optional[Dict]:
    """
    Verifica il token. Restituisce il record se valido, None altrimenti.
    """
    token_hash = _hash_token(token)
    ph = _ph()
    conn = _get_conn()
    cur = conn.cursor()
    try:
        cur.execute(f"""
            SELECT id, paziente_id, questionario, nome_paziente,
                   expires_at, used_at, meta_json
            FROM public_tokens
            WHERE token_hash = {ph} AND questionario = {ph}
            LIMIT 1
        """, (token_hash, questionario))
        row = cur.fetchone()
        if not row:
            return None

        # Normalizza a dict
        if hasattr(row, "keys"):
            rec = dict(row)
        else:
            cols = ["id", "paziente_id", "questionario", "nome_paziente",
                    "expires_at", "used_at", "meta_json"]
            rec = dict(zip(cols, row))

        # Già usato
        if rec.get("used_at"):
            return None

        # Scaduto
        exp = rec.get("expires_at")
        if exp:
            try:
                if isinstance(exp, str):
                    exp_dt = datetime.fromisoformat(exp.replace("Z", "+00:00"))
                else:
                    exp_dt = exp
                if not exp_dt.tzinfo:
                    exp_dt = exp_dt.replace(tzinfo=timezone.utc)
                if datetime.now(timezone.utc) > exp_dt:
                    return None
            except Exception:
                return None

        return rec
    finally:
        cur.close()


def mark_token_used(token_id: int):
    """Segna il token come usato dopo la compilazione."""
    ph = _ph()
    conn = _get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            f"UPDATE public_tokens SET used_at = {ph} WHERE id = {ph}",
            (datetime.now(timezone.utc).isoformat(), token_id)
        )
        conn.commit()
    finally:
        cur.close()

# ── SALVATAGGIO RISPOSTE ──────────────────────────────────────────────────────

def save_inpps_response(paziente_id: int, inpps_data: dict, inpps_summary: str):
    """
    Salva le risposte INPPS nella tabella anamnesi (struttura esistente).
    Aggiorna il record più recente se esiste, altrimenti ne crea uno nuovo.
    """
    import pnev_module as pnev_mod
    ph = _ph()
    conn = _get_conn()
    cur = conn.cursor()
    try:
        cur.execute(f"""
            SELECT id, pnev_json, pnev_summary FROM anamnesi
            WHERE paziente_id = {ph}
            ORDER BY data_anamnesi DESC, id DESC
            LIMIT 1
        """, (paziente_id,))
        last = cur.fetchone()

        pnev_obj: Dict = {}
        if last:
            raw = last[1] if not hasattr(last, "get") else last.get("pnev_json")
            if raw:
                pnev_obj = pnev_mod.pnev_load(raw)

        pnev_obj.setdefault("questionari", {})
        pnev_obj["questionari"]["inpps_screening_genitori"] = inpps_data
        dump = pnev_mod.pnev_dump(pnev_obj)

        prev_sum = ""
        if last:
            prev_sum = (last[2] if not hasattr(last, "get") else last.get("pnev_summary")) or ""
        summary = (prev_sum.strip() + "\n" + inpps_summary).strip() if prev_sum.strip() else inpps_summary

        if last:
            an_id = int(last[0] if not hasattr(last, "get") else last.get("id"))
            cur.execute(f"""
                UPDATE anamnesi SET pnev_json = {ph}, pnev_summary = {ph}
                WHERE id = {ph}
            """, (dump, summary, an_id))
        else:
            cur.execute(f"""
                INSERT INTO anamnesi
                    (paziente_id, data_anamnesi, motivo, storia, note, pnev_json, pnev_summary)
                VALUES ({ph},{ph},{ph},{ph},{ph},{ph},{ph})
            """, (paziente_id, date.today().isoformat(),
                  "INPPS (genitori)", summary, "", dump, summary))

        conn.commit()
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        raise e
    finally:
        cur.close()

# ── UI GESTIONALE: GENERA LINK ────────────────────────────────────────────────

def ui_genera_link_pubblico(paz_id: int, nome_paziente: str):
    """
    Widget per il gestionale: genera link pubblici per tutti i questionari del registry.
    Incollare nella sezione PNEV al posto del vecchio expander "Link INPPS".
    """
    st.markdown("#### 🔗 Link pubblici questionari")

    for q_key, q_info in REGISTRY.items():
        with st.expander(f"Link: {q_info['label']}", expanded=False):
            st.caption(q_info.get("descrizione", ""))

            ttl = st.number_input(
                "Validità (giorni)", min_value=1, max_value=30,
                value=_default_ttl_days(), key=f"ttl_{q_key}_{paz_id}"
            )

            if st.button(f"Genera link — {q_info['label']}", key=f"gen_{q_key}_{paz_id}"):
                try:
                    init_public_tokens_table()
                    token = create_public_token(
                        paziente_id=paz_id,
                        questionario=q_key,
                        nome_paziente=nome_paziente,
                        ttl_days=int(ttl),
                    )
                    url = build_public_url(token, q_key)
                    st.code(url, language="text")
                    msg = build_whatsapp_message(token, q_key, nome_paziente, int(ttl))
                    st.text_area(
                        "📱 Testo WhatsApp/SMS (copia e invia):",
                        value=msg, height=180,
                        key=f"msg_{q_key}_{paz_id}"
                    )
                    st.success(f"✅ Link creato — valido per {ttl} giorni.")
                except Exception as e:
                    st.error(f"Errore: {e}")
