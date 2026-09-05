# -*- coding: utf-8 -*-
"""
db_diario.py — Livello dati del Diario Clinico
Studio The Organism — gestionale
© 2026 Giuseppe Ferraioli · www.pnev.it

Diario clinico ibrido:
  - voci AUTOMATICHE generate dai moduli al salvataggio (riassunto + narrativa)
  - voci MANUALI scritte liberamente dal clinico
Una voce automatica modificata a mano diventa 'auto_modificato'
e non viene piu' sovrascritta dalle rigenerazioni.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

# ---------------------------------------------------------------------------
# ADATTARE QUESTA RIGA al nome reale dell'helper di connessione del gestionale
# (es. `from db import get_connection` oppure `from database import get_conn`)
# ---------------------------------------------------------------------------
from db import get_connection

TZ = ZoneInfo("Europe/Rome")


def _adesso():
    return datetime.now(TZ)


# ---------------------------------------------------------------------------
# Tipi di voce ammessi
# ---------------------------------------------------------------------------
TIPI_VOCE = {
    "anamnesi": "Anamnesi",
    "valutazione": "Valutazione / Testing",
    "seduta": "Seduta",
    "verifica": "Verifica intermedia",
    "colloquio": "Colloquio famiglia",
    "programma": "Programma / Piano di lavoro",
    "comunicazione": "Comunicazione esterna",
    "chiusura": "Chiusura percorso",
    "nota": "Nota libera",
}

GENERATO_DA = ("auto", "manuale", "auto_modificato")


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------
DDL = """
CREATE TABLE IF NOT EXISTS diario_clinico (
    id                  BIGSERIAL PRIMARY KEY,
    studio_id           BIGINT      NOT NULL,
    paziente_id         BIGINT      NOT NULL,
    data_voce           TIMESTAMPTZ NOT NULL DEFAULT now(),
    tipo_voce           TEXT        NOT NULL,
    titolo              TEXT,
    riassunto           TEXT,
    testo               TEXT,
    generato_da         TEXT        NOT NULL DEFAULT 'manuale',
    modulo_origine      TEXT,
    riferimento_id      BIGINT,
    autore              TEXT,
    visibile_in_referto BOOLEAN     NOT NULL DEFAULT TRUE,
    eliminato           BOOLEAN     NOT NULL DEFAULT FALSE,
    creato_il           TIMESTAMPTZ NOT NULL DEFAULT now(),
    aggiornato_il       TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_diario_tipo
        CHECK (tipo_voce IN ('anamnesi','valutazione','seduta','verifica',
                             'colloquio','programma','comunicazione',
                             'chiusura','nota')),
    CONSTRAINT chk_diario_generato
        CHECK (generato_da IN ('auto','manuale','auto_modificato'))
);

CREATE INDEX IF NOT EXISTS idx_diario_paziente
    ON diario_clinico (studio_id, paziente_id, data_voce DESC);

CREATE INDEX IF NOT EXISTS idx_diario_tipo
    ON diario_clinico (studio_id, tipo_voce);

-- Una sola voce di diario per record di modulo: la seconda chiamata aggiorna.
CREATE UNIQUE INDEX IF NOT EXISTS idx_diario_origine
    ON diario_clinico (studio_id, modulo_origine, riferimento_id)
    WHERE modulo_origine IS NOT NULL AND riferimento_id IS NOT NULL;
"""

DDL_RLS = """
ALTER TABLE diario_clinico ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS pol_diario_tenant ON diario_clinico;
CREATE POLICY pol_diario_tenant ON diario_clinico
    USING (studio_id = current_setting('app.studio_id')::BIGINT)
    WITH CHECK (studio_id = current_setting('app.studio_id')::BIGINT);
"""


def init_diario(abilita_rls=True):
    """Crea tabella, indici e policy RLS. Idempotente."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(DDL)
            if abilita_rls:
                cur.execute(DDL_RLS)
        conn.commit()


# ---------------------------------------------------------------------------
# Scrittura
# ---------------------------------------------------------------------------
def registra_voce_diario(studio_id, paziente_id, tipo_voce, modulo_origine,
                         riferimento_id, riassunto, testo=None, titolo=None,
                         autore=None, data_voce=None):
    """
    Chiamata dai moduli in coda al salvataggio.
    Se la voce esiste gia' per (modulo_origine, riferimento_id):
      - la aggiorna se e' 'auto'
      - la lascia intatta se e' 'auto_modificato' (il clinico l'ha corretta)
    Ritorna l'id della voce, o None se non e' stata toccata.
    """
    if tipo_voce not in TIPI_VOCE:
        raise ValueError("tipo_voce non valido: %s" % tipo_voce)

    data_voce = data_voce or _adesso()

    sql = """
        INSERT INTO diario_clinico
            (studio_id, paziente_id, data_voce, tipo_voce, titolo,
             riassunto, testo, generato_da, modulo_origine, riferimento_id,
             autore)
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'auto', %s, %s, %s)
        ON CONFLICT (studio_id, modulo_origine, riferimento_id)
        DO UPDATE SET
            data_voce     = EXCLUDED.data_voce,
            tipo_voce     = EXCLUDED.tipo_voce,
            titolo        = EXCLUDED.titolo,
            riassunto     = EXCLUDED.riassunto,
            testo         = EXCLUDED.testo,
            aggiornato_il = now()
        WHERE diario_clinico.generato_da = 'auto'
        RETURNING id;
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (studio_id, paziente_id, data_voce, tipo_voce,
                              titolo, riassunto, testo, modulo_origine,
                              riferimento_id, autore))
            row = cur.fetchone()
        conn.commit()
    return row[0] if row else None


def aggiungi_nota(studio_id, paziente_id, tipo_voce, testo, titolo=None,
                  riassunto=None, autore=None, data_voce=None):
    """Voce scritta a mano dal clinico."""
    if tipo_voce not in TIPI_VOCE:
        raise ValueError("tipo_voce non valido: %s" % tipo_voce)

    data_voce = data_voce or _adesso()
    if not riassunto:
        riassunto = (testo or "")[:200]

    sql = """
        INSERT INTO diario_clinico
            (studio_id, paziente_id, data_voce, tipo_voce, titolo,
             riassunto, testo, generato_da, autore)
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'manuale', %s)
        RETURNING id;
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (studio_id, paziente_id, data_voce, tipo_voce,
                              titolo, riassunto, testo, autore))
            nuovo_id = cur.fetchone()[0]
        conn.commit()
    return nuovo_id


def aggiorna_voce(studio_id, voce_id, titolo=None, riassunto=None, testo=None,
                  tipo_voce=None, visibile_in_referto=None):
    """
    Modifica una voce. Se era 'auto' passa a 'auto_modificato'
    e da quel momento e' protetta dalle rigenerazioni.
    """
    campi, valori = [], []
    for nome, val in (("titolo", titolo), ("riassunto", riassunto),
                      ("testo", testo), ("tipo_voce", tipo_voce),
                      ("visibile_in_referto", visibile_in_referto)):
        if val is not None:
            campi.append("%s = %%s" % nome)
            valori.append(val)

    if not campi:
        return False

    campi.append("aggiornato_il = now()")
    campi.append("generato_da = CASE WHEN generato_da = 'auto' "
                 "THEN 'auto_modificato' ELSE generato_da END")

    sql = ("UPDATE diario_clinico SET " + ", ".join(campi) +
           " WHERE id = %s AND studio_id = %s AND eliminato = FALSE;")
    valori.extend([voce_id, studio_id])

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, tuple(valori))
            ok = cur.rowcount > 0
        conn.commit()
    return ok


def elimina_voce(studio_id, voce_id):
    """Cancellazione logica: il diario clinico non perde mai righe."""
    sql = """
        UPDATE diario_clinico
           SET eliminato = TRUE, aggiornato_il = now()
         WHERE id = %s AND studio_id = %s;
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (voce_id, studio_id))
            ok = cur.rowcount > 0
        conn.commit()
    return ok


# ---------------------------------------------------------------------------
# Lettura
# ---------------------------------------------------------------------------
_COLONNE = """id, paziente_id, data_voce, tipo_voce, titolo, riassunto, testo,
              generato_da, modulo_origine, riferimento_id, autore,
              visibile_in_referto, creato_il, aggiornato_il"""


def _riga_dict(r):
    chiavi = [c.strip() for c in _COLONNE.replace("\n", "").split(",")]
    return dict(zip(chiavi, r))


def lista_voci(studio_id, paziente_id, tipi=None, dal=None, al=None,
               solo_referto=False, limite=None):
    """Timeline del paziente, dalla piu' recente."""
    sql = ("SELECT " + _COLONNE + " FROM diario_clinico "
           "WHERE studio_id = %s AND paziente_id = %s AND eliminato = FALSE")
    valori = [studio_id, paziente_id]

    if tipi:
        sql += " AND tipo_voce = ANY(%s)"
        valori.append(list(tipi))
    if dal:
        sql += " AND data_voce >= %s"
        valori.append(dal)
    if al:
        sql += " AND data_voce <= %s"
        valori.append(al)
    if solo_referto:
        sql += " AND visibile_in_referto = TRUE"

    sql += " ORDER BY data_voce DESC, id DESC"
    if limite:
        sql += " LIMIT %s"
        valori.append(limite)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, tuple(valori))
            righe = cur.fetchall()
    return [_riga_dict(r) for r in righe]


def get_voce(studio_id, voce_id):
    sql = ("SELECT " + _COLONNE + " FROM diario_clinico "
           "WHERE id = %s AND studio_id = %s AND eliminato = FALSE;")
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (voce_id, studio_id))
            r = cur.fetchone()
    return _riga_dict(r) if r else None


def conteggio_per_tipo(studio_id, paziente_id):
    """Per i badge di riepilogo in testa alla timeline."""
    sql = """
        SELECT tipo_voce, COUNT(*)
          FROM diario_clinico
         WHERE studio_id = %s AND paziente_id = %s AND eliminato = FALSE
      GROUP BY tipo_voce;
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (studio_id, paziente_id))
            righe = cur.fetchall()
    return {t: n for t, n in righe}
