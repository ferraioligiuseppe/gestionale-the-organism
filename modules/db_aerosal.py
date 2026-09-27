"""
modules/aerosal/db_aerosal.py
Accesso dati del modulo Aerosal (PostgreSQL, placeholder %s).
Tutte le funzioni ricevono la connessione dal chiamante: nessuna connessione
aperta qui dentro, cursori sempre chiusi con il context manager.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Rome")
EMAIL_ORDINI = "ordini@aerosal.it"
FASCE_RITIRO = ("09:00-12:00", "14:00-16:00")
PROVIDER_RATE = ("Klarna", "PayPal", "HeyLight", "Interno")
METODI_PAGAMENTO = ("contanti", "POS", "bonifico", "link", "Klarna", "PayPal", "HeyLight")


# --------------------------------------------------------------------- utils
@contextmanager
def _cur(conn):
    """Il cursore del gestionale (_PgCursor) non si puo' usare con «with»:
    questo lo apre e lo chiude comunque."""
    cur = conn.cursor()
    try:
        yield cur
    finally:
        try:
            cur.close()
        except Exception:
            pass


# Gli SQL stanno qui dentro e non in file .sql separati: caricando su GitHub
# la sottocartella sql/ veniva saltata e la pagina non partiva.
_SQL_SCHEMA = r"""
-- =====================================================================
-- Modulo AEROSAL — schema PostgreSQL (Neon)
-- Studio The Organism · gestionale-the-organism
-- Convenzioni: BIGSERIAL, TEXT, TIMESTAMPTZ, placeholder %s lato Python
-- Multi-tenant: colonna studio_id su tutte le tabelle operative.
-- ⚠ Allineare la policy RLS (in fondo) al nome della variabile di sessione
--   già usata dagli altri moduli.
-- =====================================================================

-- 1. LISTINO (prezzi base + promo storiche) ----------------------------
CREATE TABLE IF NOT EXISTS aerosal_listino (
    id               BIGSERIAL PRIMARY KEY,
    studio_id        TEXT NOT NULL,
    codice           TEXT NOT NULL,              -- es. PKG20, PKG20_PROMO_AGO26
    descrizione      TEXT NOT NULL,
    tipo             TEXT NOT NULL CHECK (tipo IN ('base','promo')),
    n_sedute         INTEGER NOT NULL CHECK (n_sedute > 0),
    prezzo           NUMERIC(10,2) NOT NULL,
    prezzo_pieno_rif NUMERIC(10,2),              -- per le promo: prezzo di riferimento
    promo_nome       TEXT,
    limite_pacchetti INTEGER,                    -- es. 5 per centro
    valido_dal       DATE,
    valido_al        DATE,
    attivo           BOOLEAN NOT NULL DEFAULT TRUE,
    note             TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (studio_id, codice)
);

-- 2. CATEGORIE PRIMA SEDUTA PROVA (allineate a Carta Respiro, dal 18/9/26)
CREATE TABLE IF NOT EXISTS aerosal_categorie_prova (
    codice      TEXT PRIMARY KEY,
    descrizione TEXT NOT NULL,
    adulti      INTEGER NOT NULL DEFAULT 1,
    bambini     INTEGER NOT NULL DEFAULT 0,
    ordine      INTEGER NOT NULL DEFAULT 0
);

-- 3. PRIME SEDUTE DI PROVA / OPEN DAY ----------------------------------
CREATE TABLE IF NOT EXISTS aerosal_prove (
    id              BIGSERIAL PRIMARY KEY,
    studio_id       TEXT NOT NULL,
    paziente_id     BIGINT,                      -- NULL se non ancora in anagrafica
    nominativo      TEXT NOT NULL,
    telefono        TEXT,
    categoria       TEXT NOT NULL REFERENCES aerosal_categorie_prova(codice),
    origine         TEXT NOT NULL CHECK (origine IN ('open_day','prima_seduta')),
    data_prova      DATE NOT NULL,
    registrata_carta_respiro BOOLEAN NOT NULL DEFAULT FALSE,
    convertita      BOOLEAN NOT NULL DEFAULT FALSE,
    pacchetto_id    BIGINT,                      -- pacchetto acquistato dopo la prova
    note            TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 4. PACCHETTI VENDUTI -------------------------------------------------
CREATE TABLE IF NOT EXISTS aerosal_pacchetti (
    id               BIGSERIAL PRIMARY KEY,
    studio_id        TEXT NOT NULL,
    paziente_id      BIGINT NOT NULL,
    listino_id       BIGINT REFERENCES aerosal_listino(id),
    descrizione      TEXT NOT NULL,              -- copia congelata dal listino
    n_sedute         INTEGER NOT NULL CHECK (n_sedute > 0),
    prezzo_totale    NUMERIC(10,2) NOT NULL,
    data_acquisto    DATE NOT NULL,
    modalita         TEXT NOT NULL CHECK (modalita IN ('unica','rateale')),
    provider_rate    TEXT CHECK (provider_rate IN ('Klarna','PayPal','HeyLight','Interno')),
    n_rate           INTEGER,
    stato            TEXT NOT NULL DEFAULT 'attivo'
                     CHECK (stato IN ('attivo','sospeso','completato','annullato')),
    detraibile       BOOLEAN NOT NULL DEFAULT TRUE, -- dispositivo medico
    note             TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 5. PAGAMENTI / RATE --------------------------------------------------
CREATE TABLE IF NOT EXISTS aerosal_pagamenti (
    id            BIGSERIAL PRIMARY KEY,
    studio_id     TEXT NOT NULL,
    pacchetto_id  BIGINT NOT NULL REFERENCES aerosal_pacchetti(id) ON DELETE CASCADE,
    scadenza      DATE,
    data_pagamento DATE,
    importo       NUMERIC(10,2) NOT NULL,
    metodo        TEXT CHECK (metodo IN ('contanti','POS','bonifico','link','Klarna','PayPal','HeyLight')),
    riferimento   TEXT,
    pagato        BOOLEAN NOT NULL DEFAULT FALSE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 6. SEDUTE EFFETTUATE (scalano dal pacchetto) -------------------------
CREATE TABLE IF NOT EXISTS aerosal_sedute (
    id            BIGSERIAL PRIMARY KEY,
    studio_id     TEXT NOT NULL,
    pacchetto_id  BIGINT NOT NULL REFERENCES aerosal_pacchetti(id) ON DELETE CASCADE,
    paziente_id   BIGINT NOT NULL,
    data_ora      TIMESTAMPTZ NOT NULL,
    durata_min    INTEGER NOT NULL DEFAULT 30,
    operatore     TEXT,
    tollerata     BOOLEAN NOT NULL DEFAULT TRUE,
    sintomi       TEXT,                          -- tosse, dispnea, altro
    interrotta    BOOLEAN NOT NULL DEFAULT FALSE,
    note          TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 7. ORDINI E RITIRO SALE ----------------------------------------------
CREATE TABLE IF NOT EXISTS aerosal_date_ritiro (
    data_ritiro DATE PRIMARY KEY,
    fasce       TEXT NOT NULL DEFAULT '09:00-12:00 / 14:00-16:00',
    note        TEXT
);

CREATE TABLE IF NOT EXISTS aerosal_ordini_sale (
    id               BIGSERIAL PRIMARY KEY,
    studio_id        TEXT NOT NULL,
    data_ordine      DATE NOT NULL,
    quantita         TEXT,                       -- es. "10 kg" / n. confezioni
    importo          NUMERIC(10,2),
    data_pagamento   DATE,
    email_inviata    BOOLEAN NOT NULL DEFAULT FALSE,   -- a ordini@aerosal.it con copia pagamento
    data_ritiro      DATE REFERENCES aerosal_date_ritiro(data_ritiro),
    fascia           TEXT CHECK (fascia IN ('09:00-12:00','14:00-16:00')),
    stato            TEXT NOT NULL DEFAULT 'da_pagare'
                     CHECK (stato IN ('da_pagare','pagato','appuntamento','ritirato')),
    note             TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 8. VISTA: SEDUTE RESIDUE PER PACCHETTO -------------------------------
CREATE OR REPLACE VIEW aerosal_v_residuo AS
SELECT p.id AS pacchetto_id,
       p.studio_id,
       p.paziente_id,
       p.descrizione,
       p.n_sedute,
       COUNT(s.id)                          AS sedute_fatte,
       p.n_sedute - COUNT(s.id)             AS sedute_residue,
       p.prezzo_totale,
       COALESCE((SELECT SUM(g.importo) FROM aerosal_pagamenti g
                 WHERE g.pacchetto_id = p.id AND g.pagato), 0) AS incassato,
       p.stato,
       p.data_acquisto
FROM aerosal_pacchetti p
LEFT JOIN aerosal_sedute s ON s.pacchetto_id = p.id
GROUP BY p.id;

CREATE INDEX IF NOT EXISTS ix_aer_pacc_paz   ON aerosal_pacchetti(studio_id, paziente_id);
CREATE INDEX IF NOT EXISTS ix_aer_sed_pacc   ON aerosal_sedute(pacchetto_id);
CREATE INDEX IF NOT EXISTS ix_aer_pag_pacc   ON aerosal_pagamenti(pacchetto_id);
CREATE INDEX IF NOT EXISTS ix_aer_prove_data ON aerosal_prove(studio_id, data_prova);

-- 9. RLS (modello — ADATTARE alla variabile di sessione già in uso) ----
-- ALTER TABLE aerosal_listino     ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE aerosal_prove       ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE aerosal_pacchetti   ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE aerosal_pagamenti   ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE aerosal_sedute      ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE aerosal_ordini_sale ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY aer_tenant ON aerosal_pacchetti
--     USING (studio_id = current_setting('app.studio_id', true));
-- (ripetere per ogni tabella)

"""

_SQL_SEED = r"""
-- =====================================================================
-- Modulo AEROSAL — dati iniziali da chat "Aerosal Family" (lug–set 2026)
-- Sostituire 'THE_ORGANISM' con lo studio_id reale.
-- =====================================================================

-- Categorie "Prima Seduta Prova" (Carta Respiro, dal 18/09/2026)
INSERT INTO aerosal_categorie_prova (codice, descrizione, adulti, bambini, ordine) VALUES
 ('ADULTO',        'Adulto singolo',        1, 0, 1),
 ('ADULTO_1BIMBO', 'Adulto con bambino',    1, 1, 2),
 ('ADULTO_2BIMBI', 'Adulto con 2 bambini',  1, 2, 3),
 ('ADULTO_3BIMBI', 'Adulto con 3 bambini',  1, 3, 4)
ON CONFLICT (codice) DO NOTHING;

-- Listino BASE (prezzo pieno)
INSERT INTO aerosal_listino (studio_id, codice, descrizione, tipo, n_sedute, prezzo, attivo, note) VALUES
 ('THE_ORGANISM','PKG20','Pacchetto 20 sedute','base',20, 520.00, TRUE,'26,00 €/seduta'),
 ('THE_ORGANISM','PKG40','Pacchetto 40 sedute','base',40, 930.00, TRUE,'23,25 €/seduta'),
 ('THE_ORGANISM','PKG78','Pacchetto 78 sedute','base',78,1640.00, TRUE,'21,03 €/seduta')
ON CONFLICT (studio_id, codice) DO NOTHING;

-- Promo "Ricomincia ora" 24/08–05/09/2026 (storico, scaduta)
INSERT INTO aerosal_listino (studio_id, codice, descrizione, tipo, n_sedute, prezzo, prezzo_pieno_rif,
                             promo_nome, limite_pacchetti, valido_dal, valido_al, attivo) VALUES
 ('THE_ORGANISM','PKG20_PROMO_AGO26','20 sedute — promo rientro','promo',20, 442.00, 520.00,'Ricomincia ora',5,'2026-08-24','2026-09-05',FALSE),
 ('THE_ORGANISM','PKG40_PROMO_AGO26','40 sedute — promo rientro','promo',40, 790.00, 930.00,'Ricomincia ora',5,'2026-08-24','2026-09-05',FALSE),
 ('THE_ORGANISM','PKG78_PROMO_AGO26','78 sedute — promo rientro','promo',78,1312.00,1640.00,'Ricomincia ora',5,'2026-08-24','2026-09-05',FALSE)
ON CONFLICT (studio_id, codice) DO NOTHING;

-- Promo "Settembre parte da oggi" 23/07–09/08/2026 (storico, scaduta; sconto % sul formato)
INSERT INTO aerosal_listino (studio_id, codice, descrizione, tipo, n_sedute, prezzo, promo_nome,
                             limite_pacchetti, valido_dal, valido_al, attivo, note) VALUES
 ('THE_ORGANISM','TRIM_PROMO_LUG26','Trimestrale -20%','promo',1,0,'Settembre parte da oggi',5,'2026-07-23','2026-08-09',FALSE,'Sconto 20% — sedute e prezzo definiti dal centro'),
 ('THE_ORGANISM','SEM_PROMO_LUG26', 'Semestrale -25%', 'promo',1,0,'Settembre parte da oggi',5,'2026-07-23','2026-08-09',FALSE,'Sconto 25% — sedute e prezzo definiti dal centro'),
 ('THE_ORGANISM','ANN_PROMO_LUG26', 'Annuale -30%',    'promo',1,0,'Settembre parte da oggi',5,'2026-07-23','2026-08-09',FALSE,'Sconto 30% — sedute e prezzo definiti dal centro')
ON CONFLICT (studio_id, codice) DO NOTHING;

-- Date ritiro sale (prenotare via ordini@aerosal.it allegando il pagamento)
INSERT INTO aerosal_date_ritiro (data_ritiro) VALUES
 ('2026-09-21'),('2026-09-28'),('2026-10-05'),('2026-10-19'),('2026-10-26')
ON CONFLICT (data_ritiro) DO NOTHING;

"""


def _statement(testo: str) -> list[str]:
    righe = [l.split("--", 1)[0] for l in testo.splitlines()]
    return [s.strip() for s in "\n".join(righe).split(";") if s.strip()]


def assicura_schema(conn, studio_id: str) -> str:
    """Crea le tabelle e carica listino, categorie e date ritiro la prima
    volta. Si puo' rilanciare: tutto e' IF NOT EXISTS / ON CONFLICT."""
    try:
        with _cur(conn) as cur:
            for s in _statement(_SQL_SCHEMA):
                cur.execute(s)
            seed = _SQL_SEED
            # Con i parametri psycopg2 legge ogni % come segnaposto: «Sconto 20%»
            # nelle note delle promo va raddoppiato prima.
            for s in _statement(seed.replace("%", "%%").replace("'THE_ORGANISM'", "%s")):
                if "%s" in s:
                    cur.execute(s, (studio_id,) * s.count("%s"))
                else:
                    cur.execute(s.replace("%%", "%"))
        conn.commit()
        return ""
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        return str(e)


def _rows(cur) -> list[dict]:
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def _one(cur) -> dict | None:
    r = cur.fetchone()
    if r is None:
        return None
    return dict(zip([c[0] for c in cur.description], r))


def ora_roma() -> datetime:
    return datetime.now(TZ)


def piano_rate(totale: Decimal, n_rate: int, prima_scadenza: date) -> list[dict]:
    """Divide il totale in n rate mensili; l'arrotondamento finisce sull'ultima."""
    totale = Decimal(totale)
    base = (totale / n_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    rate = []
    for i in range(n_rate):
        mese = prima_scadenza.month - 1 + i
        anno = prima_scadenza.year + mese // 12
        mese = mese % 12 + 1
        giorno = min(prima_scadenza.day, 28)
        importo = base if i < n_rate - 1 else totale - base * (n_rate - 1)
        rate.append({"scadenza": date(anno, mese, giorno), "importo": importo})
    return rate


# ------------------------------------------------------------------ listino
def listino(conn, studio_id: str, solo_attivi: bool = True) -> list[dict]:
    sql = """SELECT id, codice, descrizione, tipo, n_sedute, prezzo, prezzo_pieno_rif,
                    promo_nome, limite_pacchetti, valido_dal, valido_al, attivo, note
             FROM aerosal_listino WHERE studio_id = %s"""
    if solo_attivi:
        sql += " AND attivo"
    sql += " ORDER BY tipo, n_sedute, codice"
    with _cur(conn) as cur:
        cur.execute(sql, (studio_id,))
        return _rows(cur)


def salva_voce_listino(conn, studio_id: str, v: dict) -> int:
    with _cur(conn) as cur:
        cur.execute(
            """INSERT INTO aerosal_listino
                 (studio_id, codice, descrizione, tipo, n_sedute, prezzo, prezzo_pieno_rif,
                  promo_nome, limite_pacchetti, valido_dal, valido_al, attivo, note)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (studio_id, codice) DO UPDATE SET
                 descrizione=EXCLUDED.descrizione, tipo=EXCLUDED.tipo,
                 n_sedute=EXCLUDED.n_sedute, prezzo=EXCLUDED.prezzo,
                 prezzo_pieno_rif=EXCLUDED.prezzo_pieno_rif, promo_nome=EXCLUDED.promo_nome,
                 limite_pacchetti=EXCLUDED.limite_pacchetti, valido_dal=EXCLUDED.valido_dal,
                 valido_al=EXCLUDED.valido_al, attivo=EXCLUDED.attivo, note=EXCLUDED.note
               RETURNING id""",
            (studio_id, v["codice"], v["descrizione"], v["tipo"], v["n_sedute"], v["prezzo"],
             v.get("prezzo_pieno_rif"), v.get("promo_nome"), v.get("limite_pacchetti"),
             v.get("valido_dal"), v.get("valido_al"), v.get("attivo", True), v.get("note")),
        )
        new_id = cur.fetchone()[0]
    conn.commit()
    return new_id


def promo_vendute(conn, studio_id: str, listino_id: int) -> int:
    """Quanti pacchetti di una promo sono già stati venduti (limite 5 per centro)."""
    with _cur(conn) as cur:
        cur.execute(
            """SELECT COUNT(*) FROM aerosal_pacchetti
               WHERE studio_id=%s AND listino_id=%s AND stato <> 'annullato'""",
            (studio_id, listino_id),
        )
        return cur.fetchone()[0]


# ------------------------------------------------------------- prime prove
def categorie_prova(conn) -> list[dict]:
    with _cur(conn) as cur:
        cur.execute("SELECT codice, descrizione, adulti, bambini FROM aerosal_categorie_prova ORDER BY ordine")
        return _rows(cur)


def registra_prova(conn, studio_id: str, p: dict) -> int:
    with _cur(conn) as cur:
        cur.execute(
            """INSERT INTO aerosal_prove
                 (studio_id, paziente_id, nominativo, telefono, categoria, origine,
                  data_prova, registrata_carta_respiro, note)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
            (studio_id, p.get("paziente_id"), p["nominativo"], p.get("telefono"),
             p["categoria"], p["origine"], p["data_prova"],
             p.get("registrata_carta_respiro", False), p.get("note")),
        )
        new_id = cur.fetchone()[0]
    conn.commit()
    return new_id


def prove(conn, studio_id: str, dal: date, al: date) -> list[dict]:
    with _cur(conn) as cur:
        cur.execute(
            """SELECT p.id, p.data_prova, p.nominativo, p.telefono, c.descrizione AS categoria,
                      p.origine, p.registrata_carta_respiro, p.convertita, p.pacchetto_id, p.note
               FROM aerosal_prove p JOIN aerosal_categorie_prova c ON c.codice = p.categoria
               WHERE p.studio_id=%s AND p.data_prova BETWEEN %s AND %s
               ORDER BY p.data_prova DESC, p.id DESC""",
            (studio_id, dal, al),
        )
        return _rows(cur)


def segna_carta_respiro(conn, studio_id: str, prova_id: int, valore: bool) -> None:
    with _cur(conn) as cur:
        cur.execute(
            "UPDATE aerosal_prove SET registrata_carta_respiro=%s WHERE id=%s AND studio_id=%s",
            (valore, prova_id, studio_id),
        )
    conn.commit()


def tasso_conversione(conn, studio_id: str, dal: date, al: date) -> dict:
    with _cur(conn) as cur:
        cur.execute(
            """SELECT COUNT(*) AS prove, COUNT(*) FILTER (WHERE convertita) AS convertite
               FROM aerosal_prove WHERE studio_id=%s AND data_prova BETWEEN %s AND %s""",
            (studio_id, dal, al),
        )
        r = _one(cur)
    r["tasso"] = round(100 * r["convertite"] / r["prove"], 1) if r["prove"] else 0.0
    return r


# ---------------------------------------------------------------- pacchetti
def vendi_pacchetto(conn, studio_id: str, d: dict) -> int:
    """Crea il pacchetto e il relativo piano pagamenti in un'unica transazione."""
    try:
        with _cur(conn) as cur:
            cur.execute(
                """INSERT INTO aerosal_pacchetti
                     (studio_id, paziente_id, listino_id, descrizione, n_sedute, prezzo_totale,
                      data_acquisto, modalita, provider_rate, n_rate, detraibile, note)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                (studio_id, d["paziente_id"], d.get("listino_id"), d["descrizione"],
                 d["n_sedute"], d["prezzo_totale"], d["data_acquisto"], d["modalita"],
                 d.get("provider_rate"), d.get("n_rate"), d.get("detraibile", True), d.get("note")),
            )
            pid = cur.fetchone()[0]

            if d["modalita"] == "rateale" and d.get("provider_rate") == "Interno":
                for r in piano_rate(d["prezzo_totale"], d["n_rate"], d["data_acquisto"]):
                    cur.execute(
                        """INSERT INTO aerosal_pagamenti (studio_id, pacchetto_id, scadenza, importo, pagato)
                           VALUES (%s,%s,%s,%s,FALSE)""",
                        (studio_id, pid, r["scadenza"], r["importo"]),
                    )
            else:
                # Pagamento unico, oppure rateale con finanziaria esterna:
                # il centro incassa l'intero importo in un'unica volta.
                cur.execute(
                    """INSERT INTO aerosal_pagamenti
                         (studio_id, pacchetto_id, scadenza, data_pagamento, importo, metodo, pagato)
                       VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                    (studio_id, pid, d["data_acquisto"],
                     d["data_acquisto"] if d.get("pagato_subito") else None,
                     d["prezzo_totale"], d.get("metodo"), bool(d.get("pagato_subito"))),
                )

            if d.get("prova_id"):
                cur.execute(
                    "UPDATE aerosal_prove SET convertita=TRUE, pacchetto_id=%s WHERE id=%s AND studio_id=%s",
                    (pid, d["prova_id"], studio_id),
                )
        conn.commit()
        return pid
    except Exception:
        conn.rollback()
        raise


def pacchetti_paziente(conn, studio_id: str, paziente_id: int) -> list[dict]:
    with _cur(conn) as cur:
        cur.execute(
            """SELECT * FROM aerosal_v_residuo
               WHERE studio_id=%s AND paziente_id=%s ORDER BY data_acquisto DESC""",
            (studio_id, paziente_id),
        )
        return _rows(cur)


def pacchetti_attivi(conn, studio_id: str) -> list[dict]:
    with _cur(conn) as cur:
        cur.execute(
            """SELECT * FROM aerosal_v_residuo
               WHERE studio_id=%s AND stato='attivo' ORDER BY sedute_residue ASC""",
            (studio_id,),
        )
        return _rows(cur)


def cambia_stato_pacchetto(conn, studio_id: str, pacchetto_id: int, stato: str) -> None:
    with _cur(conn) as cur:
        cur.execute(
            "UPDATE aerosal_pacchetti SET stato=%s WHERE id=%s AND studio_id=%s",
            (stato, pacchetto_id, studio_id),
        )
    conn.commit()


# ------------------------------------------------------------------- sedute
def registra_seduta(conn, studio_id: str, s: dict) -> int:
    """Registra una seduta; se il pacchetto è esaurito lo chiude come 'completato'."""
    try:
        with _cur(conn) as cur:
            cur.execute(
                "SELECT sedute_residue FROM aerosal_v_residuo WHERE pacchetto_id=%s AND studio_id=%s",
                (s["pacchetto_id"], studio_id),
            )
            row = cur.fetchone()
            if row is None:
                raise ValueError("Pacchetto non trovato.")
            if row[0] <= 0:
                raise ValueError("Il pacchetto non ha sedute residue.")

            cur.execute(
                """INSERT INTO aerosal_sedute
                     (studio_id, pacchetto_id, paziente_id, data_ora, durata_min, operatore,
                      tollerata, sintomi, interrotta, note)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                (studio_id, s["pacchetto_id"], s["paziente_id"], s.get("data_ora", ora_roma()),
                 s.get("durata_min", 30), s.get("operatore"), s.get("tollerata", True),
                 s.get("sintomi"), s.get("interrotta", False), s.get("note")),
            )
            sid = cur.fetchone()[0]
            if row[0] - 1 == 0:
                cur.execute(
                    "UPDATE aerosal_pacchetti SET stato='completato' WHERE id=%s AND studio_id=%s",
                    (s["pacchetto_id"], studio_id),
                )
        conn.commit()
        return sid
    except Exception:
        conn.rollback()
        raise


def sedute_pacchetto(conn, studio_id: str, pacchetto_id: int) -> list[dict]:
    with _cur(conn) as cur:
        cur.execute(
            """SELECT id, data_ora, durata_min, operatore, tollerata, sintomi, interrotta, note
               FROM aerosal_sedute WHERE studio_id=%s AND pacchetto_id=%s ORDER BY data_ora""",
            (studio_id, pacchetto_id),
        )
        return _rows(cur)


# ---------------------------------------------------------------- pagamenti
def rate_in_scadenza(conn, studio_id: str, entro: date) -> list[dict]:
    with _cur(conn) as cur:
        cur.execute(
            """SELECT g.id, g.scadenza, g.importo, p.paziente_id, p.descrizione, g.pacchetto_id
               FROM aerosal_pagamenti g JOIN aerosal_pacchetti p ON p.id = g.pacchetto_id
               WHERE g.studio_id=%s AND NOT g.pagato AND g.scadenza <= %s
               ORDER BY g.scadenza""",
            (studio_id, entro),
        )
        return _rows(cur)


def segna_pagato(conn, studio_id: str, pagamento_id: int, metodo: str,
                 data_pag: date, riferimento: str | None = None) -> None:
    with _cur(conn) as cur:
        cur.execute(
            """UPDATE aerosal_pagamenti SET pagato=TRUE, metodo=%s, data_pagamento=%s, riferimento=%s
               WHERE id=%s AND studio_id=%s""",
            (metodo, data_pag, riferimento, pagamento_id, studio_id),
        )
    conn.commit()


# --------------------------------------------------------------------- sale
def date_ritiro_future(conn, da: date | None = None) -> list[date]:
    with _cur(conn) as cur:
        cur.execute(
            "SELECT data_ritiro FROM aerosal_date_ritiro WHERE data_ritiro >= %s ORDER BY data_ritiro",
            (da or ora_roma().date(),),
        )
        return [r[0] for r in cur.fetchall()]


def aggiungi_data_ritiro(conn, d: date, note: str | None = None) -> None:
    with _cur(conn) as cur:
        cur.execute(
            "INSERT INTO aerosal_date_ritiro (data_ritiro, note) VALUES (%s,%s) ON CONFLICT DO NOTHING",
            (d, note),
        )
    conn.commit()


def salva_ordine_sale(conn, studio_id: str, o: dict) -> int:
    with _cur(conn) as cur:
        cur.execute(
            """INSERT INTO aerosal_ordini_sale
                 (studio_id, data_ordine, quantita, importo, data_pagamento,
                  email_inviata, data_ritiro, fascia, stato, note)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
            (studio_id, o["data_ordine"], o.get("quantita"), o.get("importo"),
             o.get("data_pagamento"), o.get("email_inviata", False), o.get("data_ritiro"),
             o.get("fascia"), o.get("stato", "da_pagare"), o.get("note")),
        )
        new_id = cur.fetchone()[0]
    conn.commit()
    return new_id


def ordini_sale(conn, studio_id: str) -> list[dict]:
    with _cur(conn) as cur:
        cur.execute(
            """SELECT id, data_ordine, quantita, importo, data_pagamento, email_inviata,
                      data_ritiro, fascia, stato, note
               FROM aerosal_ordini_sale WHERE studio_id=%s ORDER BY data_ordine DESC""",
            (studio_id,),
        )
        return _rows(cur)


def aggiorna_stato_ordine(conn, studio_id: str, ordine_id: int, stato: str) -> None:
    with _cur(conn) as cur:
        cur.execute(
            "UPDATE aerosal_ordini_sale SET stato=%s WHERE id=%s AND studio_id=%s",
            (stato, ordine_id, studio_id),
        )
    conn.commit()
