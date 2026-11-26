# -*- coding: utf-8 -*-
"""
apps/ricerca_api.py — servizio dati di PNEV Academy · Ricerca scuola

Riceve dai giochi (giochi.pnev.it) i risultati delle partite fatte in classe e li
salva nelle tabelle ric_* del database del gestionale. Gira sul server OVH accanto
al gestionale (porta 8504, dietro Caddy: dati.pnev.it).

Cosa accetta: solo dati anonimi — codice classe, codice alunno, gioco, livello,
condizione, percentuale di errori, conteggi, durata, data. Una sessione viene
salvata solo se il codice classe esiste ed è attivo e il codice alunno appartiene
a quella classe. Gli invii ripetuti (stesso client_id) non creano doppioni.

Avvio sul server (lo fa scripts/server_ovh.sh):
    uvicorn apps.ricerca_api:app --host 127.0.0.1 --port 8504

La connessione al database usa lo stesso DATABASE_URL del gestionale
(.streamlit/secrets.toml, chiave [db].DATABASE_URL o DATABASE_URL).
"""

import os
import re
import sys
import time
from pathlib import Path
from collections import defaultdict, deque

import psycopg2
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

RADICE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADICE))
from modules.ricerca_scuola.db_ricerca import (  # noqa: E402
    init_ricerca_db, classe_da_codice, salva_sessione_ricerca,
)

STUDIO_ID = int(os.environ.get("RICERCA_STUDIO_ID", "1"))
ORIGINI = [o.strip() for o in os.environ.get(
    "RICERCA_ORIGINI",
    "https://giochi.pnev.it,https://www.pnev.it,https://pnev.it,"
    "https://giochi.91-134-106-98.sslip.io").split(",") if o.strip()]


def _database_url():
    u = os.environ.get("DATABASE_URL", "").strip()
    if not u:
        try:
            import tomllib
        except ImportError:  # Python < 3.11
            import tomli as tomllib
        f = RADICE / ".streamlit" / "secrets.toml"
        if f.exists():
            sec = tomllib.loads(f.read_text(encoding="utf-8"))
            db = sec.get("db", {}) if isinstance(sec.get("db"), dict) else {}
            u = (db.get("DATABASE_URL") or db.get("database_url") or db.get("url")
                 or sec.get("DATABASE_URL") or sec.get("database_url") or "")
    u = str(u).strip().strip('"').strip("'")
    if u.startswith("postgres://"):
        u = "postgresql://" + u[len("postgres://"):]
    if not u:
        raise RuntimeError("DATABASE_URL non trovato (né variabile d'ambiente né .streamlit/secrets.toml)")
    return u


DB_URL = None


def _conn():
    return psycopg2.connect(DB_URL, connect_timeout=10,
                            options=f"-c statement_timeout=15000 -c app.current_studio={STUDIO_ID}")


app = FastAPI(title="PNEV Academy · Ricerca scuola", docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(CORSMiddleware, allow_origins=ORIGINI, allow_methods=["GET", "POST"],
                   allow_headers=["Content-Type"], max_age=86400)


@app.on_event("startup")
def _avvio():
    global DB_URL
    DB_URL = _database_url()
    c = _conn()
    try:
        init_ricerca_db(c)
    finally:
        c.close()


# ── Limite di richieste: 120 al minuto per indirizzo (una classe intera dietro lo stesso Wi-Fi) ──
_FINESTRA, _MAX = 60, 120
_storia = defaultdict(deque)


def _limita(req: Request):
    ip = req.headers.get("x-forwarded-for", req.client.host if req.client else "?").split(",")[0].strip()
    ora = time.time()
    q = _storia[ip]
    while q and q[0] < ora - _FINESTRA:
        q.popleft()
    if len(q) >= _MAX:
        raise HTTPException(429, "Troppe richieste, riprova tra poco")
    q.append(ora)


# ── Modelli ─────────────────────────────────────────────────────────────
RE_CODICE = re.compile(r"^[A-Za-z0-9 _.\-]{1,24}$")
RE_GIOCO = re.compile(r"^[a-z0-9][a-z0-9\-]{0,39}$")
RE_CLIENT = re.compile(r"^[A-Za-z0-9\-]{8,64}$")


class Sessione(BaseModel):
    client_id: str
    alunno: str
    gioco: str
    t: int = Field(..., description="millisecondi dall'epoca, quando è stata giocata")
    err_pct: float | None = None
    corrette: int | None = None
    totali: int | None = None
    durata_s: float | None = None
    livello: str | None = None
    condizione: str | None = None
    metriche: dict | None = None
    dispositivo: str | None = None


class Invio(BaseModel):
    classe: str
    sessioni: list[Sessione] = Field(..., max_length=50)


def _valida(s: Sessione, alunni):
    if not RE_CLIENT.match(s.client_id):
        return "client_id non valido"
    if not RE_CODICE.match(s.alunno) or s.alunno not in alunni:
        return "codice alunno non appartiene alla classe"
    if not RE_GIOCO.match(s.gioco):
        return "gioco non valido"
    ora_ms = time.time() * 1000
    if not (ora_ms - 400 * 86400_000 < s.t < ora_ms + 86400_000):
        return "data non plausibile"
    if s.err_pct is not None and not (0 <= s.err_pct <= 100):
        return "err_pct fuori intervallo"
    if s.metriche is not None and len(str(s.metriche)) > 4000:
        return "metriche troppo lunghe"
    return None


def _pulisci(s: Sessione):
    d = s.model_dump()
    for k in ("livello", "condizione", "dispositivo"):
        if d.get(k) is not None:
            d[k] = str(d[k])[:40]
    for k in ("corrette", "totali"):
        if d.get(k) is not None and not (0 <= d[k] <= 100000):
            d[k] = None
    if d.get("durata_s") is not None and not (0 <= d["durata_s"] <= 36000):
        d["durata_s"] = None
    return d


# ── Rotte ───────────────────────────────────────────────────────────────
@app.get("/salute")
def salute():
    return {"ok": True}


@app.get("/v1/classe/{codice}")
def classe(codice: str, request: Request):
    _limita(request)
    if not RE_CODICE.match(codice):
        raise HTTPException(404, "Codice classe non trovato")
    c = _conn()
    try:
        cl = classe_da_codice(c, codice)
    finally:
        c.close()
    if not cl or not cl["attiva"]:
        raise HTTPException(404, "Codice classe non trovato o non attivo")
    return {"classe": cl["nome"], "alunni": cl["alunni"]}


@app.post("/v1/sessioni")
def sessioni(inv: Invio, request: Request):
    _limita(request)
    c = _conn()
    try:
        cl = classe_da_codice(c, inv.classe)
        if not cl or not cl["attiva"]:
            raise HTTPException(404, "Codice classe non trovato o non attivo")
        alunni = set(cl["alunni"])
        salvate, gia, scartate = 0, 0, []
        for s in inv.sessioni:
            motivo = _valida(s, alunni)
            if motivo:
                scartate.append({"client_id": s.client_id, "motivo": motivo})
                continue
            if salva_sessione_ricerca(c, cl["id"], _pulisci(s)):
                salvate += 1
            else:
                gia += 1
        return {"salvate": salvate, "gia_presenti": gia, "scartate": scartate}
    finally:
        c.close()
