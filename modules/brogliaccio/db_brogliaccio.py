# -*- coding: utf-8 -*-
"""
db_brogliaccio.py — Il brogliaccio dello studio.

Una riga = un fatto: una telefonata, un appuntamento fissato, una visita
fatta, una relazione da scrivere o consegnata, una nota. Ogni riga dice
CHI l'ha fatto e, se serve, il PROSSIMO PASSO, A CHI tocca ed ENTRO QUANDO.

Convenzioni gestionale: placeholder %s, BIGSERIAL, TEXT, TIMESTAMPTZ,
ZoneInfo("Europe/Rome"). Nessuna RLS: come registro_attivita e
archivio_relazioni, la tabella e' dello studio.

Il trigger di registro_attivita (tracciamento automatico) copre anche questa
tabella da solo, perche' ha la colonna paziente_id.
"""
from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Rome")

# ── Tipi di fatto ──────────────────────────────────────────────────────
T_TEL_IN = "📞 Telefonata ricevuta"
T_TEL_OUT = "📲 Telefonata fatta"
T_MSG = "💬 WhatsApp / email"
T_APP = "📅 Appuntamento fissato"
T_APP_MOD = "🔁 Appuntamento spostato / annullato"
T_VISITA = "🩺 Visita / valutazione fatta"
T_SEDUTA = "🧘 Seduta / terapia fatta"
T_ASSENTE = "🚫 Non si è presentato"
T_REL_DA = "📝 Relazione da scrivere"
T_REL_OK = "✅ Relazione consegnata"
T_REL_NO = "➖ Relazione non necessaria"
T_PAGAM = "💶 Pagamento / fattura"
T_NOTA = "🗒️ Nota"

TIPI = [T_TEL_IN, T_TEL_OUT, T_MSG, T_APP, T_APP_MOD, T_VISITA, T_SEDUTA,
        T_ASSENTE, T_REL_DA, T_REL_OK, T_REL_NO, T_PAGAM, T_NOTA]

TIPI_TELEFONO = {T_TEL_IN, T_TEL_OUT, T_MSG}
TIPI_VISITA = {T_VISITA, T_SEDUTA}
TIPI_REL_CHIUSA = {T_REL_OK, T_REL_NO}

# Prossimo passo proposto in automatico per alcuni tipi.
PASSO_PROPOSTO = {
    T_TEL_IN: "Richiamare",
    T_VISITA: "Scrivere la relazione",
    T_REL_DA: "Scrivere la relazione",
}

SEDI = ["Pagani", "Sant'Agnello", "Avellino", "Napoli", "Telefono / online"]

# ── Costo ─────────────────────────────────────────────────────────────
TIPI_CON_IMPORTO = [T_VISITA, T_SEDUTA, T_PAGAM]
METODI = ["POS", "Contanti", "Bonifico", "Da pagare", "Gratuito"]
INCASSATI = ["POS", "Contanti", "Bonifico"]
FATTURA = ["Da fare", "Fatta", "Non serve"]

STATO_APERTO = "aperto"
STATO_FATTO = "fatto"
STATO_NESSUNO = "nessuno"   # solo annotazione, nessun passo da fare

DDL = """
CREATE TABLE IF NOT EXISTS brogliaccio (
    id              BIGSERIAL PRIMARY KEY,
    quando          TIMESTAMPTZ NOT NULL DEFAULT now(),
    paziente_id     BIGINT,
    nominativo      TEXT,
    telefono        TEXT,
    tipo            TEXT NOT NULL,
    sede            TEXT,
    operatore       TEXT,
    descrizione     TEXT,
    prossimo_passo  TEXT,
    assegnato_a     TEXT,
    scadenza        DATE,
    stato           TEXT NOT NULL DEFAULT 'nessuno',
    esito           TEXT,
    chiuso_da       TEXT,
    chiuso_il       TIMESTAMPTZ,
    rif_data        DATE,
    creato_da       TEXT,
    creato_il       TIMESTAMPTZ NOT NULL DEFAULT now(),
    eliminato       BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS ix_brogliaccio_quando ON brogliaccio (quando DESC);
CREATE INDEX IF NOT EXISTS ix_brogliaccio_paz ON brogliaccio (paziente_id, quando DESC);
CREATE INDEX IF NOT EXISTS ix_brogliaccio_aperti ON brogliaccio (stato, assegnato_a) WHERE stato = 'aperto';
ALTER TABLE brogliaccio ADD COLUMN IF NOT EXISTS importo   NUMERIC(10,2);
ALTER TABLE brogliaccio ADD COLUMN IF NOT EXISTS pagamento TEXT;
ALTER TABLE brogliaccio ADD COLUMN IF NOT EXISTS fattura   TEXT;
"""


# ── Accesso al DB (stesso stile di registro_attivita) ─────────────────
def _pulisci(conn):
    """Se un altro modulo ha lasciato la transazione in errore (es. una
    lettura fallita senza rollback), la chiude: altrimenti ogni query
    successiva fallirebbe in silenzio."""
    try:
        if conn.get_transaction_status() == 3:   # psycopg2 TRANSACTION_STATUS_INERROR
            conn.rollback()
    except Exception:
        pass


def _q(conn, sql, par=()):
    _pulisci(conn)
    try:
        cur = conn.cursor()
        cur.execute(sql, par)
        r = cur.fetchall() or []
        if r and not isinstance(r[0], dict):
            n = [c[0] for c in cur.description]
            r = [dict(zip(n, x)) for x in r]
        else:
            r = [dict(x) for x in r]
        try:
            conn.commit()   # chiude la lettura: niente blocchi lasciati aperti
        except Exception:
            pass
        return r
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return []


def _esegui(conn, sql, par=(), ritorna_id=False):
    _pulisci(conn)
    try:
        cur = conn.cursor()
        cur.execute(sql, par)
        rid = None
        if ritorna_id:
            row = cur.fetchone()
            rid = int(row["id"] if isinstance(row, dict) else row[0])
        conn.commit()
        return rid if ritorna_id else True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return None if ritorna_id else False


def init_db(conn) -> bool:
    return bool(_esegui(conn, "SET LOCAL lock_timeout = '3000ms';" + DDL))


# ── Scrittura ─────────────────────────────────────────────────────────
def aggiungi(conn, *, tipo, operatore, utente, paziente_id=None, nominativo="", telefono="",
             sede="", descrizione="", prossimo_passo="", assegnato_a="", scadenza=None,
             quando=None, rif_data=None, importo=None, pagamento=None, fattura=None):
    """Annota un fatto. Ritorna l'id o None."""
    passo = (prossimo_passo or "").strip()
    stato = STATO_APERTO if passo else STATO_NESSUNO
    if passo and not (assegnato_a or "").strip():
        assegnato_a = operatore
    return _esegui(conn,
        "INSERT INTO brogliaccio (quando, paziente_id, nominativo, telefono, tipo, sede, operatore,"
        " descrizione, prossimo_passo, assegnato_a, scadenza, stato, rif_data, creato_da,"
        " importo, pagamento, fattura)"
        " VALUES (COALESCE(%s, now()), %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
        (quando, int(paziente_id) if paziente_id else None, (nominativo or "").strip() or None,
         (telefono or "").strip() or None, tipo, sede or None, operatore or None,
         (descrizione or "").strip() or None, passo or None,
         ((assegnato_a or "").strip() or None) if passo else None,
         scadenza if passo else None, stato, rif_data, utente or None,
         (round(float(importo), 2) if importo not in (None, "") else None), pagamento or None, fattura or None),
        ritorna_id=True)


def chiudi(conn, rid, utente, esito=""):
    return _esegui(conn,
        "UPDATE brogliaccio SET stato='fatto', chiuso_da=%s, chiuso_il=now(), esito=%s WHERE id=%s",
        (utente or None, (esito or "").strip() or None, int(rid)))


def riapri(conn, rid):
    return _esegui(conn,
        "UPDATE brogliaccio SET stato='aperto', chiuso_da=NULL, chiuso_il=NULL WHERE id=%s", (int(rid),))


def riassegna(conn, rid, a_chi, scadenza=None):
    return _esegui(conn, "UPDATE brogliaccio SET assegnato_a=%s, scadenza=%s WHERE id=%s",
                   (a_chi, scadenza, int(rid)))


def elimina(conn, rid):
    return _esegui(conn, "UPDATE brogliaccio SET eliminato=TRUE WHERE id=%s", (int(rid),))


# ── Lettura ───────────────────────────────────────────────────────────
_SEL = ("SELECT b.*, p.cognome, p.nome FROM brogliaccio b "
        "LEFT JOIN pazienti p ON p.id = b.paziente_id WHERE NOT b.eliminato")


def da_fare(conn, assegnato_a=None):
    sql = _SEL + " AND b.stato='aperto'"
    par = []
    if assegnato_a:
        sql += " AND b.assegnato_a=%s"
        par.append(assegnato_a)
    return _q(conn, sql + " ORDER BY b.scadenza NULLS LAST, b.quando", tuple(par))


def conta_aperti(conn):
    """{assegnato_a: (aperti, scaduti)}"""
    out = {}
    for r in _q(conn,
            "SELECT COALESCE(assegnato_a,'—') AS a, COUNT(*) AS n,"
            " COUNT(*) FILTER (WHERE scadenza < (now() AT TIME ZONE 'Europe/Rome')::date) AS s"
            " FROM brogliaccio WHERE NOT eliminato AND stato='aperto' GROUP BY 1"):
        out[r["a"]] = (int(r["n"] or 0), int(r["s"] or 0))
    return out


def elenco(conn, giorni=7, operatore=None, tipo=None, paziente_id=None, limite=500):
    sql = _SEL + " AND b.quando > now() - (%s || ' days')::interval"
    par = [str(int(giorni))]
    if operatore:
        sql += " AND (b.operatore=%s OR b.assegnato_a=%s OR b.chiuso_da=%s)"
        par += [operatore, operatore, operatore]
    if tipo:
        sql += " AND b.tipo=%s"
        par.append(tipo)
    if paziente_id:
        sql += " AND b.paziente_id=%s"
        par.append(int(paziente_id))
    return _q(conn, sql + " ORDER BY b.quando DESC LIMIT %s", tuple(par) + (int(limite),))


def euro(v) -> str:
    """30.5 → «30,50 €»."""
    try:
        return f"{float(v):,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return "—"


def riepilogo_importi(righe) -> dict:
    """Totali delle righe con importo: incassato (per metodo), da pagare, gratuito, fatture da fare."""
    r = {"incassato": 0.0, "per_metodo": {m: 0.0 for m in INCASSATI}, "da_pagare": 0.0,
         "n_da_pagare": 0, "fatture_da_fare": 0, "n": 0}
    for x in righe:
        if x.get("fattura") == "Da fare":
            r["fatture_da_fare"] += 1
        if x.get("importo") is None:
            continue
        v = float(x["importo"]); m = x.get("pagamento") or ""
        r["n"] += 1
        if m in INCASSATI:
            r["incassato"] += v; r["per_metodo"][m] += v
        elif m == "Da pagare":
            r["da_pagare"] += v; r["n_da_pagare"] += 1
    return r


def del_giorno(conn, giorno: dt.date):
    """Righe del brogliaccio di quel giorno (per data del fatto o data di riferimento)."""
    return _q(conn, _SEL + " AND ((b.quando AT TIME ZONE 'Europe/Rome')::date = %s OR b.rif_data = %s)"
                    " ORDER BY b.quando", (giorno, giorno))


def operatori_noti(conn):
    """Nomi gia' usati nel brogliaccio e utenti del gestionale."""
    nomi = set()
    for r in _q(conn, "SELECT DISTINCT operatore AS n FROM brogliaccio WHERE operatore IS NOT NULL "
                      "UNION SELECT DISTINCT assegnato_a FROM brogliaccio WHERE assegnato_a IS NOT NULL"):
        if r.get("n"):
            nomi.add(r["n"])
    return nomi


# ── Controlli «cosa manca» ────────────────────────────────────────────
# Tabelle in cui un nuovo inserimento vuol dire «e' stata fatta una
# valutazione/visita». Se una tabella non esiste, viene ignorata.
TABELLE_VALUTAZIONE = (
    "inpp_valutazioni", "valutazioni_visive", "dem_risultati", "getman_risultati",
    "groffman_risultati", "audiometrie_tonali", "functional_audiograms",
    "logopedia_valutazioni", "nps_valutazioni", "whodas_somministrazioni",
    "pvb_schede", "prismi_posturali", "protocollo_valutazione", "osteo_anamnesi",
    "anamnesi_prima_infanzia", "anamnesi_sviluppo", "alim_valutazione",
    "screening_uditivo_pnev",
)
TABELLE_RELAZIONE = ("archivio_relazioni", "relazioni_cliniche", "relazioni_funzionali")


def tracce_del_giorno(conn, giorno: dt.date):
    """{paziente_id: {utenti:set, tabelle:set}} dal registro automatico."""
    out = {}
    for r in _q(conn,
            "SELECT paziente_id, utente, tabella FROM registro_attivita"
            " WHERE paziente_id IS NOT NULL AND tabella IS NOT NULL AND tabella <> 'brogliaccio'"
            " AND operazione IN ('INSERT','UPDATE')"
            " AND (quando AT TIME ZONE 'Europe/Rome')::date = %s", (giorno,)):
        d = out.setdefault(int(r["paziente_id"]), {"utenti": set(), "tabelle": set()})
        if r.get("utente"):
            d["utenti"].add(r["utente"])
        d["tabelle"].add(r["tabella"])
    return out


def pazienti_con_tracce(conn, giorni: list[dt.date]):
    """{(paziente_id, giorno)} con almeno una traccia (registro o brogliaccio)."""
    if not giorni:
        return set()
    out = set()
    for r in _q(conn,
            "SELECT DISTINCT paziente_id, (quando AT TIME ZONE 'Europe/Rome')::date AS g"
            " FROM registro_attivita WHERE paziente_id IS NOT NULL AND tabella IS NOT NULL"
            " AND operazione IN ('INSERT','UPDATE')"
            " AND (quando AT TIME ZONE 'Europe/Rome')::date = ANY(%s)", (list(giorni),)):
        out.add((int(r["paziente_id"]), r["g"]))
    for r in _q(conn,
            "SELECT DISTINCT paziente_id, COALESCE(rif_data, (quando AT TIME ZONE 'Europe/Rome')::date) AS g"
            " FROM brogliaccio WHERE NOT eliminato AND paziente_id IS NOT NULL"
            " AND COALESCE(rif_data, (quando AT TIME ZONE 'Europe/Rome')::date) = ANY(%s)", (list(giorni),)):
        out.add((int(r["paziente_id"]), r["g"]))
    return out


def relazioni_mancanti(conn, giorni=90):
    """Pazienti con una visita/valutazione negli ultimi `giorni` e nessuna
    relazione (scritta, consegnata o dichiarata non necessaria) da allora.
    Ritorna [{paziente_id, cognome, nome, ultima_visita, chi}]."""
    # Ultima visita per paziente: dal brogliaccio e dal registro automatico.
    visite = {}

    def _metti(pid, quando, chi):
        if pid is None or quando is None:
            return
        pid = int(pid)
        if pid not in visite or quando > visite[pid][0]:
            visite[pid] = (quando, chi or "")

    for r in _q(conn,
            "SELECT paziente_id, COALESCE(rif_data::timestamptz, quando) AS q, operatore FROM brogliaccio"
            " WHERE NOT eliminato AND paziente_id IS NOT NULL AND tipo = ANY(%s)"
            " AND quando > now() - (%s || ' days')::interval",
            (list(TIPI_VISITA - {T_SEDUTA}), str(int(giorni)))):
        _metti(r["paziente_id"], r["q"], r.get("operatore"))
    for r in _q(conn,
            "SELECT paziente_id, MAX(quando) AS q, (array_agg(utente ORDER BY quando DESC))[1] AS u"
            " FROM registro_attivita WHERE operazione='INSERT' AND paziente_id IS NOT NULL"
            " AND tabella = ANY(%s) AND quando > now() - (%s || ' days')::interval GROUP BY paziente_id",
            (list(TABELLE_VALUTAZIONE), str(int(giorni)))):
        _metti(r["paziente_id"], r["q"], r.get("u"))
    if not visite:
        return []

    # Ultima relazione per paziente.
    relaz = {}

    def _rel(pid, quando):
        if pid is None or quando is None:
            return
        pid = int(pid)
        if pid not in relaz or quando > relaz[pid]:
            relaz[pid] = quando

    ids = list(visite)
    for r in _q(conn,
            "SELECT paziente_id, MAX(quando) AS q FROM brogliaccio WHERE NOT eliminato"
            " AND tipo = ANY(%s) AND paziente_id = ANY(%s) GROUP BY paziente_id",
            (list(TIPI_REL_CHIUSA), ids)):
        _rel(r["paziente_id"], r["q"])
    for r in _q(conn,
            "SELECT paziente_id, MAX(quando) AS q FROM registro_attivita WHERE operazione='INSERT'"
            " AND tabella = ANY(%s) AND paziente_id = ANY(%s) GROUP BY paziente_id",
            (list(TABELLE_RELAZIONE), ids)):
        _rel(r["paziente_id"], r["q"])
    for r in _q(conn,
            "SELECT paziente_id, MAX(creato_il) AS q FROM archivio_relazioni"
            " WHERE NOT COALESCE(eliminata, FALSE) AND paziente_id = ANY(%s) GROUP BY paziente_id", (ids,)):
        _rel(r["paziente_id"], r["q"])

    def _ts(x):
        if isinstance(x, dt.datetime):
            return x if x.tzinfo else x.replace(tzinfo=TZ)
        return dt.datetime(x.year, x.month, x.day, tzinfo=TZ)

    mancano = [pid for pid, (q, _c) in visite.items()
               if pid not in relaz or _ts(relaz[pid]) < _ts(q) - dt.timedelta(hours=1)]
    if not mancano:
        return []
    nomi = {int(r["id"]): r for r in _q(conn, "SELECT id, cognome, nome FROM pazienti WHERE id = ANY(%s)",
                                         (mancano,))}
    out = []
    for pid in mancano:
        p = nomi.get(pid, {})
        out.append({"paziente_id": pid, "cognome": p.get("cognome") or "", "nome": p.get("nome") or "",
                    "ultima_visita": visite[pid][0], "chi": visite[pid][1]})
    out.sort(key=lambda x: _ts(x["ultima_visita"]))
    return out


def nome_paziente(r) -> str:
    n = f"{(r.get('cognome') or '').title()} {(r.get('nome') or '').title()}".strip()
    return n or (r.get("nominativo") or "").strip() or "—"


def fmt(v, ora=False) -> str:
    if v is None:
        return "—"
    if isinstance(v, dt.datetime):
        if v.tzinfo:
            v = v.astimezone(TZ)
        return v.strftime("%d/%m %H:%M" if ora else "%d/%m/%Y")
    if hasattr(v, "strftime"):
        return v.strftime("%d/%m/%Y")
    return str(v)
