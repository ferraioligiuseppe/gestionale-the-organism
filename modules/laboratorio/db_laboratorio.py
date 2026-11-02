"""Laboratorio PNEV — accesso al database.

Salva nel gestionale i risultati della sezione sperimentale (pagina HTML
«Laboratorio PNEV»): A binoculare, B suono e sonno, C memoria iconica,
D ritmo theta.

La pagina HTML impacchetta ogni risultato in un codice testuale:
  "z1." + base64url(deflate-raw(JSON))   oppure   "j1." + base64url(JSON)
Il codice arriva qui tramite il link «Invia al gestionale» (?lab=...) o
incollato a mano.

Convenzioni: segnaposto %s, BIGSERIAL, TEXT, TIMESTAMPTZ, Europe/Rome.
"""
from __future__ import annotations

import base64
import hashlib
import json
import zlib
from datetime import datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Rome")

MODULI = {
    "A Binoculare": "A · Visore binoculare",
    "B Suono e sonno": "B · Suono e sonno",
    "C Memoria iconica": "C · Memoria iconica",
    "D Ritmo theta": "D · Ritmo theta",
}

# Metriche da seguire nel tempo, per modulo: (chiave, etichetta)
METRICHE_ANDAMENTO = {
    "A Binoculare": [
        ("set1_mediana_s", "Emersione set 1 (s)"),
        ("set2_mediana_s", "Emersione set 2 (s)"),
        ("vantaggio_s", "Vantaggio set 1 (s)"),
    ],
    "B Suono e sonno": [
        ("effetto_riattivazione_punti", "Effetto riattivazione (punti %)"),
    ],
    "C Memoria iconica": [
        ("disponibili_subito", "Lettere disponibili subito (su 12)"),
        ("resoconto_totale", "Resoconto totale (lettere)"),
    ],
    "D Ritmo theta": [
        ("dprime_ritmico", "d′ ritmico"),
        ("dprime_irregolare", "d′ irregolare"),
    ],
}

MAX_CODICE = 60_000  # caratteri: oltre è sicuramente un errore

DDL = """
CREATE TABLE IF NOT EXISTS lab_risultati (
    id           BIGSERIAL PRIMARY KEY,
    studio_id    BIGINT      NOT NULL DEFAULT NULLIF(current_setting('app.current_studio', true), '')::bigint,
    paziente_id  BIGINT      NOT NULL,
    modulo       TEXT        NOT NULL,
    seduta       TEXT,
    operatore    TEXT,
    parametri    TEXT,
    risultato    TEXT,
    metriche     JSONB       NOT NULL DEFAULT '{}'::jsonb,
    prove        JSONB       NOT NULL DEFAULT '[]'::jsonb,
    eseguito_il  TIMESTAMPTZ,
    salvato_il   TIMESTAMPTZ NOT NULL DEFAULT now(),
    impronta     TEXT        UNIQUE           -- impedisce di salvare due volte lo stesso risultato
);
CREATE INDEX IF NOT EXISTS lab_risultati_paziente_idx
    ON lab_risultati (studio_id, paziente_id, modulo, eseguito_il)
"""

# Sicurezza multi-studio (RLS): stessa convenzione di PECS e genosociogramma.
# Lo studio arriva dalla connessione (app_core: -c app.current_studio=<id>).
# La prima parte sistema la tabella creata dalla versione precedente del
# modulo, dove studio_id poteva restare vuoto.
RLS_SQL = """
UPDATE lab_risultati SET studio_id = 1 WHERE studio_id IS NULL;
ALTER TABLE lab_risultati ALTER COLUMN studio_id
    SET DEFAULT NULLIF(current_setting('app.current_studio', true), '')::bigint;
ALTER TABLE lab_risultati ALTER COLUMN studio_id SET NOT NULL;
ALTER TABLE lab_risultati ENABLE ROW LEVEL SECURITY;
ALTER TABLE lab_risultati FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS lab_risultati_tenant ON lab_risultati;
CREATE POLICY lab_risultati_tenant ON lab_risultati
    USING (studio_id = NULLIF(current_setting('app.current_studio', true), '')::bigint)
    WITH CHECK (studio_id = NULLIF(current_setting('app.current_studio', true), '')::bigint)
"""

_SCHEMA_PRONTO = False


class CodiceNonValido(ValueError):
    """Il codice incollato o ricevuto non è un risultato del Laboratorio PNEV."""


# ---------------------------------------------------------------- decodifica
def _b64url_decode(s: str) -> bytes:
    s = s.strip()
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def decodifica_codice(codice: str) -> dict:
    """Trasforma il codice della pagina HTML nel dizionario del risultato."""
    if not codice:
        raise CodiceNonValido("Codice vuoto.")
    codice = codice.strip()
    if len(codice) > MAX_CODICE:
        raise CodiceNonValido("Codice troppo lungo.")
    try:
        if codice.startswith("z1."):
            raw = zlib.decompress(_b64url_decode(codice[3:]), -15)
        elif codice.startswith("j1."):
            raw = _b64url_decode(codice[3:])
        else:
            raise CodiceNonValido("Il codice deve iniziare con z1. oppure j1.")
        dati = json.loads(raw.decode("utf-8"))
    except CodiceNonValido:
        raise
    except Exception as exc:  # base64, zlib o JSON rovinati
        raise CodiceNonValido("Codice illeggibile: ricopialo per intero dalla pagina Laboratorio.") from exc

    if not isinstance(dati, dict) or dati.get("app") != "laboratorio-pnev" or dati.get("v") != 1:
        raise CodiceNonValido("Il codice non proviene dal Laboratorio PNEV.")
    if dati.get("modulo") not in MODULI:
        raise CodiceNonValido(f"Modulo sconosciuto: {dati.get('modulo')!r}.")
    if not isinstance(dati.get("metriche", {}), dict) or not isinstance(dati.get("prove", []), list):
        raise CodiceNonValido("Struttura dei dati non valida.")
    return dati


def impronta(codice: str) -> str:
    return hashlib.sha256(codice.strip().encode("utf-8")).hexdigest()


def data_esecuzione(dati: dict) -> datetime | None:
    ts = dati.get("ts")
    if not ts:
        return None
    try:
        return datetime.fromisoformat(str(ts).replace("Z", "+00:00")).astimezone(TZ)
    except ValueError:
        return None


def paziente_dal_codice(dati: dict) -> int | None:
    """Il campo «Codice paziente» della pagina deve contenere l'ID del gestionale."""
    valore = "".join(ch for ch in str(dati.get("paziente", "")) if ch.isdigit())
    return int(valore) if valore else None

# ---------------------------------------------------------------- database
# Il gestionale avvolge le connessioni in un suo cursore (_PgCursor) che non
# supporta «with conn.cursor() as cur»: qui il cursore si apre e si chiude a mano.
def _cursore(conn):
    return conn.cursor()


def _chiudi(cur) -> None:
    try:
        cur.close()
    except Exception:
        pass


def _valore(riga, indice: int, chiave: str):
    """Legge un campo sia da righe-tupla sia da righe-dizionario."""
    if riga is None:
        return None
    if isinstance(riga, dict):
        return riga.get(chiave)
    try:
        return riga[indice]
    except (KeyError, IndexError, TypeError):
        try:
            return riga[chiave]
        except Exception:
            return None


_COLONNE = ["id", "modulo", "seduta", "operatore", "parametri", "risultato",
            "metriche", "prove", "eseguito_il", "salvato_il"]


def crea_tabella(conn) -> None:
    """Crea tabella e protezione RLS se mancano. Lavora una sola volta per avvio:
    gli ALTER TABLE bloccano la tabella e non vanno ripetuti a ogni pagina."""
    global _SCHEMA_PRONTO
    if _SCHEMA_PRONTO:
        return
    cur = _cursore(conn)
    try:
        for istruzione in [x.strip() for x in DDL.split(";") if x.strip()]:
            cur.execute(istruzione)
        conn.commit()
        cur.execute("SELECT relrowsecurity, relforcerowsecurity FROM pg_class "
                    "WHERE relname = 'lab_risultati' AND relkind = 'r'")
        stato = cur.fetchone()
        protetta = bool(_valore(stato, 0, "relrowsecurity")) and bool(_valore(stato, 1, "relforcerowsecurity"))
        if not protetta:
            for istruzione in [x.strip() for x in RLS_SQL.split(";") if x.strip()]:
                cur.execute(istruzione)
            conn.commit()
        _SCHEMA_PRONTO = True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        _chiudi(cur)


def salva_risultato(conn, paziente_id: int, dati: dict, codice: str, studio_id: int | None = None) -> int | None:
    """Salva un risultato. Restituisce l'id, oppure None se era già stato salvato."""
    cur = _cursore(conn)
    try:
        cur.execute(
            """
            INSERT INTO lab_risultati
                (studio_id, paziente_id, modulo, seduta, operatore, parametri, risultato,
                 metriche, prove, eseguito_il, impronta)
            VALUES (COALESCE(%s::bigint, NULLIF(current_setting('app.current_studio', true), '')::bigint),
                    %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s)
            ON CONFLICT (impronta) DO NOTHING
            RETURNING id
            """,
            (
                studio_id,
                int(paziente_id),
                dati["modulo"],
                (dati.get("seduta") or "")[:200],
                (dati.get("operatore") or "")[:200],
                (dati.get("parametri") or "")[:1000],
                (dati.get("risultato") or "")[:1000],
                json.dumps(dati.get("metriche", {}), ensure_ascii=False),
                json.dumps(dati.get("prove", [])[:200], ensure_ascii=False),
                data_esecuzione(dati),
                impronta(codice),
            ),
        )
        riga = cur.fetchone()
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        _chiudi(cur)
    return _valore(riga, 0, "id")


def elenco_risultati(conn, paziente_id: int, modulo: str | None = None) -> list[dict]:
    sql = (
        "SELECT " + ", ".join(_COLONNE) + " FROM lab_risultati WHERE paziente_id = %s"
    )
    params: list = [int(paziente_id)]
    if modulo:
        sql += " AND modulo = %s"
        params.append(modulo)
    sql += " ORDER BY COALESCE(eseguito_il, salvato_il) DESC"
    cur = _cursore(conn)
    try:
        cur.execute(sql, tuple(params))
        grezze = cur.fetchall() or []
    finally:
        _chiudi(cur)
    righe = [{c: _valore(r, i, c) for i, c in enumerate(_COLONNE)} for r in grezze]
    for r in righe:  # alcuni driver restituiscono JSONB come stringa
        for k in ("metriche", "prove"):
            if isinstance(r[k], str):
                try:
                    r[k] = json.loads(r[k])
                except ValueError:
                    r[k] = {} if k == "metriche" else []
            elif r[k] is None:
                r[k] = {} if k == "metriche" else []
    return righe


def elimina_risultato(conn, risultato_id: int) -> None:
    cur = _cursore(conn)
    try:
        cur.execute("DELETE FROM lab_risultati WHERE id = %s", (int(risultato_id),))
        conn.commit()
    finally:
        _chiudi(cur)
