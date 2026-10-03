"""
modules/aerosal/db_aerosal.py
Accesso dati del modulo Aerosal (PostgreSQL, placeholder %s).
Tutte le funzioni ricevono la connessione dal chiamante: nessuna connessione
aperta qui dentro, cursori sempre chiusi con il context manager.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import date, datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP
from zoneinfo import ZoneInfo

from modules.crediti import db_crediti as dbc

TZ = ZoneInfo("Europe/Rome")
EMAIL_ORDINI = "ordini@aerosal.it"
FASCE_RITIRO = ("09:00-12:00", "14:00-16:00")
PROVIDER_RATE = ("Klarna", "PayPal", "HeyLight", "Interno")
METODI_PAGAMENTO = ("contanti", "POS", "bonifico", "link", "Klarna", "PayPal", "HeyLight")


# --------------------------------------------------------------------- utils
@contextmanager
def _cur(conn):
    """Il cursore del gestionale (_PgCursor) non si puo' usare con «with
    conn.cursor()»: questo lo apre e lo chiude comunque."""
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

# Pubblicazione delle offerte su www.pnev.it
_SQL_SCHEMA += r"""
ALTER TABLE aerosal_listino ADD COLUMN IF NOT EXISTS pubblica_sito BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE aerosal_listino ADD COLUMN IF NOT EXISTS titolo_sito TEXT;
ALTER TABLE aerosal_listino ADD COLUMN IF NOT EXISTS testo_sito TEXT;
"""

# Open day, crediti cross-settore, convenzioni (modulo v5)
_SQL_SCHEMA += r"""
-- =====================================================================
-- Open day Aerosal + Crediti cross-settore (Aerosal / Ottica / Telefonia / Studio)
-- Da eseguire DOPO 01 e 02.
-- =====================================================================

-- 1. IMPOSTAZIONI OPEN DAY (una riga per studio, tutte modificabili da UI)
CREATE TABLE IF NOT EXISTS aerosal_impostazioni (
    studio_id               TEXT PRIMARY KEY,
    modalita_prezzo         TEXT NOT NULL DEFAULT 'slot'
                            CHECK (modalita_prezzo IN ('slot','persona','adulto_bambino')),
    prezzo_prova_adulto     NUMERIC(10,2) NOT NULL DEFAULT 15.00,
    prezzo_prova_bambino    NUMERIC(10,2) NOT NULL DEFAULT 10.00,  -- usato solo in 'adulto_bambino'
    prova_scala_seduta      BOOLEAN NOT NULL DEFAULT FALSE,        -- FALSE = scala solo i soldi
    giorni_validita_credito INTEGER NOT NULL DEFAULT 30,
    converti_in_buono       BOOLEAN NOT NULL DEFAULT TRUE,         -- credito scaduto -> buono ottica/telefonia
    giorni_validita_buono   INTEGER NOT NULL DEFAULT 60,
    durata_slot_min         INTEGER NOT NULL DEFAULT 30,
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 2. GIORNATE DI OPEN DAY ----------------------------------------------
CREATE TABLE IF NOT EXISTS aerosal_open_day (
    id            BIGSERIAL PRIMARY KEY,
    studio_id     TEXT NOT NULL,
    data          DATE NOT NULL,
    sede          TEXT NOT NULL,
    ora_inizio    TIME NOT NULL,
    ora_fine      TIME NOT NULL,
    durata_slot   INTEGER NOT NULL DEFAULT 30,
    screening_visivo BOOLEAN NOT NULL DEFAULT TRUE,   -- controllo visivo bambini in attesa
    note          TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (studio_id, data, sede)
);

-- 3. ESTENSIONE PROVE: prenotazione slot + pagamento -------------------
ALTER TABLE aerosal_prove ADD COLUMN IF NOT EXISTS open_day_id  BIGINT REFERENCES aerosal_open_day(id);
ALTER TABLE aerosal_prove ADD COLUMN IF NOT EXISTS ora_slot     TIME;
ALTER TABLE aerosal_prove ADD COLUMN IF NOT EXISTS importo      NUMERIC(10,2);
ALTER TABLE aerosal_prove ADD COLUMN IF NOT EXISTS pagata       BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE aerosal_prove ADD COLUMN IF NOT EXISTS metodo       TEXT;
ALTER TABLE aerosal_prove ADD COLUMN IF NOT EXISTS presentato   BOOLEAN;           -- NULL = non ancora
ALTER TABLE aerosal_prove ADD COLUMN IF NOT EXISTS screening_visivo_fatto BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE aerosal_prove ADD COLUMN IF NOT EXISTS consenso_marketing BOOLEAN NOT NULL DEFAULT FALSE;
CREATE UNIQUE INDEX IF NOT EXISTS ux_aer_slot
    ON aerosal_prove(open_day_id, ora_slot) WHERE open_day_id IS NOT NULL;

-- 4. ESTENSIONE PACCHETTI: credito scalato -----------------------------
ALTER TABLE aerosal_pacchetti ADD COLUMN IF NOT EXISTS prezzo_listino NUMERIC(10,2);
ALTER TABLE aerosal_pacchetti ADD COLUMN IF NOT EXISTS credito_scalato NUMERIC(10,2) NOT NULL DEFAULT 0;
ALTER TABLE aerosal_pacchetti ADD COLUMN IF NOT EXISTS credito_id BIGINT;

-- 5. CREDITI CLIENTE (cross-settore, modulo generico) ------------------
CREATE TABLE IF NOT EXISTS crediti (
    id                 BIGSERIAL PRIMARY KEY,
    studio_id          TEXT NOT NULL,
    paziente_id        BIGINT,
    nominativo         TEXT NOT NULL,
    telefono           TEXT,
    tipo               TEXT NOT NULL CHECK (tipo IN ('credito','buono')),
    origine            TEXT NOT NULL,        -- 'prova_aerosal', 'conversione', 'convenzione', 'manuale'
    origine_id         BIGINT,
    importo            NUMERIC(10,2) NOT NULL CHECK (importo > 0),
    residuo            NUMERIC(10,2) NOT NULL,
    settori            TEXT[] NOT NULL,      -- sottoinsieme di {aerosal, ottica, telefonia, studio}
    emesso_il          DATE NOT NULL,
    scade_il           DATE NOT NULL,
    stato              TEXT NOT NULL DEFAULT 'attivo'
                       CHECK (stato IN ('attivo','usato','scaduto','convertito','annullato')),
    credito_padre_id   BIGINT REFERENCES crediti(id),
    consenso_marketing BOOLEAN NOT NULL DEFAULT FALSE,
    note               TEXT,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (residuo >= 0 AND residuo <= importo),
    CHECK (settori <@ ARRAY['aerosal','ottica','telefonia','studio']::TEXT[])
);

CREATE TABLE IF NOT EXISTS crediti_movimenti (
    id           BIGSERIAL PRIMARY KEY,
    studio_id    TEXT NOT NULL,
    credito_id   BIGINT NOT NULL REFERENCES crediti(id) ON DELETE CASCADE,
    data         DATE NOT NULL,
    settore      TEXT NOT NULL CHECK (settore IN ('aerosal','ottica','telefonia','studio')),
    importo      NUMERIC(10,2) NOT NULL CHECK (importo > 0),
    riferimento  TEXT,                        -- n. pacchetto / scontrino / ordine
    operatore    TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 6. CONVENZIONI / VANTAGGI CROSS-SETTORE -----------------------------
CREATE TABLE IF NOT EXISTS convenzioni (
    id              BIGSERIAL PRIMARY KEY,
    studio_id       TEXT NOT NULL,
    codice          TEXT NOT NULL,
    nome            TEXT NOT NULL,
    settore_origine TEXT NOT NULL CHECK (settore_origine IN ('aerosal','ottica','telefonia','studio')),
    settore_vantaggio TEXT NOT NULL CHECK (settore_vantaggio IN ('aerosal','ottica','telefonia','studio')),
    condizione      TEXT,                     -- descrizione leggibile (es. "pacchetto >= 40 sedute")
    min_sedute      INTEGER,                  -- condizione automatica per Aerosal
    tipo_vantaggio  TEXT NOT NULL CHECK (tipo_vantaggio IN ('omaggio','sconto_pct','buono_euro','prezzo_speciale')),
    valore          NUMERIC(10,2),
    validita_giorni INTEGER NOT NULL DEFAULT 90,
    attiva          BOOLEAN NOT NULL DEFAULT FALSE,
    note            TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (studio_id, codice)
);

CREATE INDEX IF NOT EXISTS ix_crediti_attivi ON crediti(studio_id, stato, scade_il);
CREATE INDEX IF NOT EXISTS ix_crediti_tel    ON crediti(studio_id, telefono);
CREATE INDEX IF NOT EXISTS ix_credmov        ON crediti_movimenti(credito_id);


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

-- 7. SEED (sostituire THE_ORGANISM) — convenzioni in BOZZA (attiva = FALSE)
INSERT INTO aerosal_impostazioni (studio_id) VALUES ('THE_ORGANISM') ON CONFLICT DO NOTHING;

INSERT INTO convenzioni (studio_id, codice, nome, settore_origine, settore_vantaggio, condizione,
                         min_sedute, tipo_vantaggio, valore, validita_giorni, attiva, note) VALUES
 ('THE_ORGANISM','AER40_OTTICA','Pacchetto 40+ sedute: sconto occhiali/LAC','aerosal','ottica',
  'Acquisto pacchetto Aerosal da almeno 40 sedute',40,'sconto_pct',15,180,FALSE,'Percentuale da confermare con l''ottica'),
 ('THE_ORGANISM','AER78_OTTICA','Pacchetto 78 sedute: buono ottica','aerosal','ottica',
  'Acquisto pacchetto Aerosal da 78 sedute',78,'buono_euro',30,180,FALSE,'Importo da confermare'),
 ('THE_ORGANISM','AER40_TEL','Pacchetto 40+ sedute: sconto accessori telefonia','aerosal','telefonia',
  'Acquisto pacchetto Aerosal da almeno 40 sedute',40,'sconto_pct',10,180,FALSE,'Percentuale da confermare'),
 ('THE_ORGANISM','OTT_OPENDAY','Clienti ottica: open day Aerosal a prezzo ridotto','ottica','aerosal',
  'Cliente ottica con consenso marketing',NULL,'prezzo_speciale',10,60,FALSE,'Prova a 10 € invece di 15 €'),
 ('THE_ORGANISM','TEL_OPENDAY','Clienti telefonia: open day Aerosal a prezzo ridotto','telefonia','aerosal',
  'Cliente telefonia con consenso marketing',NULL,'prezzo_speciale',10,60,FALSE,'Prova a 10 € invece di 15 €')
ON CONFLICT (studio_id, codice) DO NOTHING;
-- Nota: nessuna convenzione con vantaggio economico su prestazioni sanitarie dello studio
-- (pubblicità sanitaria: solo informativa). Lo screening visivo all'open day è gestito
-- come servizio informativo gratuito, non come sconto.


-- =====================================================================
-- Promo "Il tuo autunno con Aerosal" (comunicazione Aerosal del 30/09/2026)
-- Sconto crescente, max 5 abbonamenti TOTALI per centro (somma dei 3 formati).
-- Aerosal la indica fino a sabato 10/10/2026. Per regola dello studio una promo
-- resta in vigore finché non arriva una nuova comunicazione: valido_al resta NULL.
-- Sostituisce la promo "Ricomincia ora". Sostituire 'THE_ORGANISM'.
-- =====================================================================
UPDATE aerosal_listino
   SET attivo = FALSE, valido_al = '2026-09-29',
       note = 'Sostituita dalla promo Autunno (comunicazione Aerosal del 30/09/2026)'
 WHERE studio_id = 'THE_ORGANISM' AND promo_nome = 'Ricomincia ora' AND attivo;

INSERT INTO aerosal_listino (studio_id, codice, descrizione, tipo, n_sedute, prezzo, prezzo_pieno_rif,
                             promo_nome, limite_pacchetti, valido_dal, valido_al, attivo, note) VALUES
 ('THE_ORGANISM','PKG20_PROMO_AUT26','20 sedute — promo Autunno (-15%)','promo',20, 442.00, 520.00,'Autunno 2026',5,'2026-09-30',NULL,TRUE,'Aerosal: fino al 10/10/2026, resta valida fino a nuova comunicazione'),
 ('THE_ORGANISM','PKG40_PROMO_AUT26','40 sedute — promo Autunno (-20%)','promo',40, 744.00, 930.00,'Autunno 2026',5,'2026-09-30',NULL,TRUE,'Aerosal: fino al 10/10/2026, resta valida fino a nuova comunicazione'),
 ('THE_ORGANISM','PKG78_PROMO_AUT26','78 sedute — promo Autunno (-30%)','promo',78,1148.00,1640.00,'Autunno 2026',5,'2026-09-30',NULL,TRUE,'Aerosal: fino al 10/10/2026, resta valida fino a nuova comunicazione')
ON CONFLICT (studio_id, codice) DO NOTHING;

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
    """Pacchetti già venduti con la stessa promo, sommando tutti i formati
    (il limite Aerosal di 5 abbonamenti è per centro, non per formato)."""
    with _cur(conn) as cur:
        cur.execute(
            """SELECT COUNT(*) FROM aerosal_pacchetti p
               JOIN aerosal_listino l ON l.id = p.listino_id
               WHERE p.studio_id=%s AND p.stato <> 'annullato'
                 AND l.promo_nome = (SELECT promo_nome FROM aerosal_listino WHERE id=%s)""",
            (studio_id, listino_id),
        )
        return cur.fetchone()[0]


def prove_da_ricontattare(conn, studio_id: str) -> list[dict]:
    """Chi ha fatto la prova ma non ha comprato: il target dell'offerta Autunno.
    Solo chi ha dato il consenso marketing."""
    with _cur(conn) as cur:
        cur.execute(
            """SELECT p.data_prova, p.nominativo, p.telefono, c.descrizione AS categoria
               FROM aerosal_prove p JOIN aerosal_categorie_prova c ON c.codice = p.categoria
               WHERE p.studio_id=%s AND NOT p.convertita AND p.consenso_marketing
               ORDER BY p.data_prova DESC""",
            (studio_id,),
        )
        return _rows(cur)


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
def vendi_pacchetto(conn, studio_id: str, d: dict) -> dict:
    """Crea il pacchetto, scala l'eventuale credito della prova, genera il piano
    pagamenti sul NETTO e applica le convenzioni attive. Tutto in una transazione.
    Ritorna {'pacchetto_id', 'netto', 'credito_scalato', 'convenzioni'}."""
    oggi = d["data_acquisto"]
    prezzo_listino = Decimal(d["prezzo_totale"])
    scalato = Decimal("0")
    prova = None
    try:
        with _cur(conn) as cur:
            cur.execute(
                """INSERT INTO aerosal_pacchetti
                     (studio_id, paziente_id, listino_id, descrizione, n_sedute, prezzo_totale,
                      prezzo_listino, data_acquisto, modalita, provider_rate, n_rate,
                      detraibile, note)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                (studio_id, d["paziente_id"], d.get("listino_id"), d["descrizione"],
                 d["n_sedute"], prezzo_listino, prezzo_listino, oggi, d["modalita"],
                 d.get("provider_rate"), d.get("n_rate"), d.get("detraibile", True), d.get("note")),
            )
            pid = cur.fetchone()[0]

            # 1. Credito della prova: scalato SOLO sui pacchetti a prezzo pieno.
            #    Sui pacchetti in promo non si somma: diventa subito un buono ottica/telefonia.
            tipo_listino = "base"
            if d.get("listino_id"):
                cur.execute("SELECT tipo FROM aerosal_listino WHERE id=%s", (d["listino_id"],))
                r = cur.fetchone()
                tipo_listino = r[0] if r else "base"
            buono_da_promo = None
            if d.get("credito_id") and tipo_listino == "promo":
                buono_da_promo = _converti_credito_in_buono_cur(cur, studio_id, d["credito_id"], oggi, pid)
            elif d.get("credito_id"):
                scalato = dbc.usa_credito_cur(cur, studio_id, d["credito_id"], "aerosal",
                                              prezzo_listino, oggi, f"Pacchetto n. {pid}",
                                              d.get("operatore"))
                cur.execute("SELECT origine, origine_id FROM crediti WHERE id=%s", (d["credito_id"],))
                origine, origine_id = cur.fetchone()
                if origine == "prova_aerosal" and origine_id:
                    cur.execute(
                        """UPDATE aerosal_prove SET convertita=TRUE, pacchetto_id=%s, paziente_id=%s
                           WHERE id=%s AND studio_id=%s RETURNING data_prova, ora_slot""",
                        (pid, d["paziente_id"], origine_id, studio_id),
                    )
                    prova = cur.fetchone()

            netto = prezzo_listino - scalato
            cur.execute(
                "UPDATE aerosal_pacchetti SET prezzo_totale=%s, credito_scalato=%s, credito_id=%s WHERE id=%s",
                (netto, scalato, d.get("credito_id") if scalato else None, pid),
            )

            # 2. La prova conta come prima seduta? (impostazione)
            imp = _impostazioni_cur(cur, studio_id)
            if prova and imp["prova_scala_seduta"]:
                data_p, ora_p = prova
                quando = datetime.combine(data_p, ora_p or datetime.min.time(), tzinfo=TZ)
                cur.execute(
                    """INSERT INTO aerosal_sedute (studio_id, pacchetto_id, paziente_id, data_ora, note)
                       VALUES (%s,%s,%s,%s,'Prova open day conteggiata come seduta')""",
                    (studio_id, pid, d["paziente_id"], quando),
                )

            # 3. Piano pagamenti sul netto
            if netto > 0:
                if d["modalita"] == "rateale" and d.get("provider_rate") == "Interno":
                    for r in piano_rate(netto, d["n_rate"], oggi):
                        cur.execute(
                            """INSERT INTO aerosal_pagamenti (studio_id, pacchetto_id, scadenza, importo, pagato)
                               VALUES (%s,%s,%s,%s,FALSE)""",
                            (studio_id, pid, r["scadenza"], r["importo"]),
                        )
                else:
                    cur.execute(
                        """INSERT INTO aerosal_pagamenti
                             (studio_id, pacchetto_id, scadenza, data_pagamento, importo, metodo, pagato)
                           VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                        (studio_id, pid, oggi, oggi if d.get("pagato_subito") else None,
                         netto, d.get("metodo"), bool(d.get("pagato_subito"))),
                    )

            # 4. Convenzioni cross-settore attive per questa fascia di pacchetto
            applicate = []
            for c in dbc.convenzioni_per_pacchetto_cur(cur, studio_id, d["n_sedute"]):
                voce = {"nome": c["nome"], "settore": c["settore_vantaggio"],
                        "tipo": c["tipo_vantaggio"], "valore": c["valore"]}
                if c["tipo_vantaggio"] == "buono_euro" and c["valore"]:
                    voce["credito_id"] = dbc.crea_credito_cur(cur, studio_id, {
                        "paziente_id": d["paziente_id"], "nominativo": d["nominativo"],
                        "telefono": d.get("telefono"), "tipo": "buono", "origine": "convenzione",
                        "origine_id": c["id"], "importo": c["valore"],
                        "settori": [c["settore_vantaggio"]], "emesso_il": oggi,
                        "scade_il": oggi + timedelta(days=c["validita_giorni"]),
                        "consenso_marketing": d.get("consenso_marketing", False),
                        "note": f"{c['codice']} — pacchetto n. {pid}"})
                applicate.append(voce)
        conn.commit()
        return {"pacchetto_id": pid, "netto": netto, "credito_scalato": scalato,
                "convenzioni": applicate, "buono_da_promo": buono_da_promo}
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


# ============================================================ OPEN DAY
MODALITA_PREZZO = {
    "slot": "Prezzo unico per slot",
    "persona": "Prezzo per ogni persona",
    "adulto_bambino": "Adulto + supplemento per bambino",
}


def _impostazioni_cur(cur, studio_id: str) -> dict:
    cur.execute("SELECT * FROM aerosal_impostazioni WHERE studio_id=%s", (studio_id,))
    r = cur.fetchone()
    if r is None:
        cur.execute("INSERT INTO aerosal_impostazioni (studio_id) VALUES (%s) RETURNING *", (studio_id,))
        r = cur.fetchone()
    return dict(zip([c[0] for c in cur.description], r))


def impostazioni(conn, studio_id: str) -> dict:
    with _cur(conn) as cur:
        imp = _impostazioni_cur(cur, studio_id)
    conn.commit()
    return imp


def salva_impostazioni(conn, studio_id: str, v: dict) -> None:
    with _cur(conn) as cur:
        cur.execute(
            """INSERT INTO aerosal_impostazioni
                 (studio_id, modalita_prezzo, prezzo_prova_adulto, prezzo_prova_bambino,
                  prova_scala_seduta, giorni_validita_credito, converti_in_buono,
                  giorni_validita_buono, durata_slot_min, updated_at)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s, now())
               ON CONFLICT (studio_id) DO UPDATE SET
                 modalita_prezzo=EXCLUDED.modalita_prezzo,
                 prezzo_prova_adulto=EXCLUDED.prezzo_prova_adulto,
                 prezzo_prova_bambino=EXCLUDED.prezzo_prova_bambino,
                 prova_scala_seduta=EXCLUDED.prova_scala_seduta,
                 giorni_validita_credito=EXCLUDED.giorni_validita_credito,
                 converti_in_buono=EXCLUDED.converti_in_buono,
                 giorni_validita_buono=EXCLUDED.giorni_validita_buono,
                 durata_slot_min=EXCLUDED.durata_slot_min, updated_at=now()""",
            (studio_id, v["modalita_prezzo"], v["prezzo_prova_adulto"], v["prezzo_prova_bambino"],
             v["prova_scala_seduta"], v["giorni_validita_credito"], v["converti_in_buono"],
             v["giorni_validita_buono"], v["durata_slot_min"]),
        )
    conn.commit()


def prezzo_prova(imp: dict, bambini: int, prezzo_speciale: Decimal | None = None) -> Decimal:
    adulto = Decimal(prezzo_speciale) if prezzo_speciale is not None else Decimal(imp["prezzo_prova_adulto"])
    if imp["modalita_prezzo"] == "persona":
        return adulto * (1 + bambini)
    if imp["modalita_prezzo"] == "adulto_bambino":
        return adulto + Decimal(imp["prezzo_prova_bambino"]) * bambini
    return adulto


def crea_open_day(conn, studio_id: str, g: dict) -> int:
    with _cur(conn) as cur:
        cur.execute(
            """INSERT INTO aerosal_open_day
                 (studio_id, data, sede, ora_inizio, ora_fine, durata_slot, screening_visivo, note)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
            (studio_id, g["data"], g["sede"], g["ora_inizio"], g["ora_fine"],
             g["durata_slot"], g.get("screening_visivo", True), g.get("note")),
        )
        oid = cur.fetchone()[0]
    conn.commit()
    return oid


def open_day(conn, studio_id: str, da: date) -> list[dict]:
    with _cur(conn) as cur:
        cur.execute(
            """SELECT o.*, (SELECT COUNT(*) FROM aerosal_prove p WHERE p.open_day_id=o.id) AS prenotati
               FROM aerosal_open_day o WHERE o.studio_id=%s AND o.data >= %s ORDER BY o.data""",
            (studio_id, da),
        )
        return _rows(cur)


def slot_open_day(conn, studio_id: str, open_day_id: int) -> list[dict]:
    """Tutti gli slot della giornata con l'eventuale prenotazione."""
    with _cur(conn) as cur:
        cur.execute("SELECT data, ora_inizio, ora_fine, durata_slot FROM aerosal_open_day WHERE id=%s AND studio_id=%s",
                    (open_day_id, studio_id))
        g = cur.fetchone()
        if g is None:
            return []
        data_g, inizio, fine, durata = g
        cur.execute(
            """SELECT p.id AS prova_id, p.ora_slot, p.nominativo, p.telefono, c.descrizione AS categoria,
                      p.importo, p.pagata, p.presentato, p.convertita, p.screening_visivo_fatto,
                      p.registrata_carta_respiro
               FROM aerosal_prove p JOIN aerosal_categorie_prova c ON c.codice = p.categoria
               WHERE p.open_day_id=%s""",
            (open_day_id,),
        )
        occupati = {r["ora_slot"]: r for r in _rows(cur)}
    slots, t = [], datetime.combine(data_g, inizio)
    while t + timedelta(minutes=durata) <= datetime.combine(data_g, fine):
        s = {"ora": t.time()}
        s.update(occupati.get(t.time(), {}))
        slots.append(s)
        t += timedelta(minutes=durata)
    return slots


def prenota_slot(conn, studio_id: str, p: dict) -> int:
    """Prenota uno slot. Se pagato subito, emette il credito da scalare sul pacchetto."""
    try:
        with _cur(conn) as cur:
            cur.execute(
                """INSERT INTO aerosal_prove
                     (studio_id, paziente_id, nominativo, telefono, categoria, origine, data_prova,
                      open_day_id, ora_slot, importo, pagata, metodo, consenso_marketing, note)
                   VALUES (%s,%s,%s,%s,%s,'open_day',%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                (studio_id, p.get("paziente_id"), p["nominativo"], p.get("telefono"), p["categoria"],
                 p["data_prova"], p["open_day_id"], p["ora_slot"], p["importo"],
                 p.get("pagata", False), p.get("metodo"), p.get("consenso_marketing", False),
                 p.get("note")),
            )
            prova_id = cur.fetchone()[0]
            if p.get("pagata"):
                _emetti_credito_prova_cur(cur, studio_id, prova_id)
        conn.commit()
        return prova_id
    except Exception:
        conn.rollback()
        raise


def _emetti_credito_prova_cur(cur, studio_id: str, prova_id: int) -> int:
    imp = _impostazioni_cur(cur, studio_id)
    cur.execute(
        """SELECT paziente_id, nominativo, telefono, importo, data_prova, consenso_marketing
           FROM aerosal_prove WHERE id=%s AND studio_id=%s""",
        (prova_id, studio_id),
    )
    paz, nom, tel, importo, data_p, consenso = cur.fetchone()
    return dbc.crea_credito_cur(cur, studio_id, {
        "paziente_id": paz, "nominativo": nom, "telefono": tel, "tipo": "credito",
        "origine": "prova_aerosal", "origine_id": prova_id, "importo": importo,
        "settori": ["aerosal"], "emesso_il": data_p,
        "scade_il": data_p + timedelta(days=imp["giorni_validita_credito"]),
        "consenso_marketing": consenso, "note": "Prova open day — da scalare sul pacchetto"})


def incassa_prova(conn, studio_id: str, prova_id: int, metodo: str) -> None:
    try:
        with _cur(conn) as cur:
            cur.execute(
                """UPDATE aerosal_prove SET pagata=TRUE, metodo=%s
                   WHERE id=%s AND studio_id=%s AND NOT pagata RETURNING id""",
                (metodo, prova_id, studio_id),
            )
            if cur.fetchone():
                _emetti_credito_prova_cur(cur, studio_id, prova_id)
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def aggiorna_prova(conn, studio_id: str, prova_id: int, **campi) -> None:
    ammessi = {"presentato", "screening_visivo_fatto", "registrata_carta_respiro"}
    campi = {k: v for k, v in campi.items() if k in ammessi}
    if not campi:
        return
    sets = ", ".join(f"{k}=%s" for k in campi)
    with _cur(conn) as cur:
        cur.execute(f"UPDATE aerosal_prove SET {sets} WHERE id=%s AND studio_id=%s",
                    (*campi.values(), prova_id, studio_id))
    conn.commit()


def _converti_credito_in_buono_cur(cur, studio_id: str, credito_id: int, oggi: date, pacchetto_id: int) -> dict:
    """Pacchetto in promo: il credito della prova non si scala, diventa un buono
    ottica/telefonia. La prova risulta comunque convertita in pacchetto."""
    imp = _impostazioni_cur(cur, studio_id)
    cur.execute(
        """SELECT paziente_id, nominativo, telefono, residuo, origine, origine_id,
                  consenso_marketing, stato, scade_il
           FROM crediti WHERE id=%s AND studio_id=%s FOR UPDATE""",
        (credito_id, studio_id),
    )
    row = cur.fetchone()
    if row is None:
        raise ValueError("Credito non trovato.")
    paz, nom, tel, residuo, origine, origine_id, consenso, stato, scade = row
    if stato != "attivo" or scade < oggi:
        raise ValueError("Credito non più utilizzabile.")
    buono_id = dbc.crea_credito_cur(cur, studio_id, {
        "paziente_id": paz, "nominativo": nom, "telefono": tel, "tipo": "buono",
        "origine": "conversione", "origine_id": credito_id, "importo": residuo,
        "settori": ["ottica", "telefonia"], "emesso_il": oggi,
        "scade_il": oggi + timedelta(days=imp["giorni_validita_buono"]),
        "credito_padre_id": credito_id, "consenso_marketing": consenso,
        "note": f"Prova open day: pacchetto in promo n. {pacchetto_id}, credito non cumulabile"})
    cur.execute("UPDATE crediti SET stato='convertito' WHERE id=%s", (credito_id,))
    if origine == "prova_aerosal" and origine_id:
        cur.execute(
            "UPDATE aerosal_prove SET convertita=TRUE, pacchetto_id=%s WHERE id=%s AND studio_id=%s",
            (pacchetto_id, origine_id, studio_id),
        )
    return {"credito_id": buono_id, "importo": residuo,
            "scade_il": oggi + timedelta(days=imp["giorni_validita_buono"])}


# ------------------------------------------------ offerte su www.pnev.it
def imposta_pubblicazione(conn, studio_id: str, listino_id: int, pubblica: bool,
                          titolo: str | None, testo: str | None) -> None:
    with _cur(conn) as cur:
        cur.execute("""UPDATE aerosal_listino SET pubblica_sito=%s, titolo_sito=%s, testo_sito=%s
                       WHERE id=%s AND studio_id=%s""",
                    (bool(pubblica), titolo or None, testo or None, listino_id, studio_id))
    conn.commit()


def voci_sito(conn, studio_id: str) -> list[dict]:
    """Le promo con i campi di pubblicazione, per la scheda del gestionale."""
    with _cur(conn) as cur:
        cur.execute("""SELECT id, codice, descrizione, n_sedute, prezzo, prezzo_pieno_rif, promo_nome,
                              limite_pacchetti, valido_dal, valido_al, attivo, note,
                              pubblica_sito, titolo_sito, testo_sito
                       FROM aerosal_listino WHERE studio_id=%s AND tipo='promo'
                       ORDER BY valido_dal DESC NULLS LAST, n_sedute""", (studio_id,))
        return _rows(cur)


def offerte_pubbliche(conn, studio_id: str | None = None, oggi: date | None = None) -> list[dict]:
    """Le offerte da mostrare su pnev.it OGGI: attive, spuntate per il sito,
    dentro le date di validita' e non esaurite. Programmare un'offerta vuol
    dire darle le date: compare e sparisce da sola."""
    oggi = oggi or date.today()
    sql = """SELECT l.id, l.codice, l.descrizione, l.n_sedute, l.prezzo, l.prezzo_pieno_rif,
                    l.promo_nome, l.limite_pacchetti, l.valido_dal, l.valido_al, l.note,
                    l.titolo_sito, l.testo_sito,
                    (SELECT COUNT(*) FROM aerosal_pacchetti p
                      WHERE p.listino_id=l.id AND p.stato <> 'annullato') AS vendute
             FROM aerosal_listino l
             WHERE l.tipo='promo' AND l.attivo AND l.pubblica_sito
               AND (l.valido_dal IS NULL OR l.valido_dal <= %s)
               AND (l.valido_al  IS NULL OR l.valido_al  >= %s)"""
    par = [oggi, oggi]
    if studio_id:
        sql += " AND l.studio_id=%s"
        par.append(studio_id)
    sql += " ORDER BY l.promo_nome, l.n_sedute"
    with _cur(conn) as cur:
        cur.execute(sql, tuple(par))
        righe = _rows(cur)
    return [r for r in righe if not r.get("limite_pacchetti") or r["vendute"] < r["limite_pacchetti"]]


