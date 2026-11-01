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
    studio_id    BIGINT,                      -- ADATTA: colonna tenant usata dalle policy RLS
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
    ON lab_risultati (paziente_id, modulo, eseguito_il);
"""


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
def crea_tabella(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(DDL)
    conn.commit()


def salva_risultato(conn, paziente_id: int, dati: dict, codice: str, studio_id: int | None = None) -> int | None:
    """Salva un risultato. Restituisce l'id, oppure None se era già stato salvato."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO lab_risultati
                (studio_id, paziente_id, modulo, seduta, operatore, parametri, risultato,
                 metriche, prove, eseguito_il, impronta)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s)
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
    return riga[0] if riga else None


def elenco_risultati(conn, paziente_id: int, modulo: str | None = None) -> list[dict]:
    sql = """
        SELECT id, modulo, seduta, operatore, parametri, risultato, metriche, prove,
               eseguito_il, salvato_il
        FROM lab_risultati
        WHERE paziente_id = %s
    """
    params: list = [int(paziente_id)]
    if modulo:
        sql += " AND modulo = %s"
        params.append(modulo)
    sql += " ORDER BY COALESCE(eseguito_il, salvato_il) DESC"
    with conn.cursor() as cur:
        cur.execute(sql, params)
        colonne = [c[0] for c in cur.description]
        righe = [dict(zip(colonne, r)) for r in cur.fetchall()]
    for r in righe:  # alcuni driver restituiscono JSONB come stringa
        for k in ("metriche", "prove"):
            if isinstance(r[k], str):
                r[k] = json.loads(r[k])
    return righe


def elimina_risultato(conn, risultato_id: int) -> None:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM lab_risultati WHERE id = %s", (int(risultato_id),))
    conn.commit()
