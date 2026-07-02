# -*- coding: utf-8 -*-
"""
modules/pnev_gamecenter/db_gamecenter.py

Strato dati del PNEV Game Center dentro il gestionale The Organism.

Salva una riga per ogni partita giocata (gc_sessioni), legata al paziente
(riferimento soft a pazienti.id) e, se disponibile, alla visita.
Le metriche di ogni gioco sono in JSONB: così ogni gioco salva il suo set
senza dover cambiare lo schema.

Convenzioni rispettate (come nel resto del gestionale):
- connessione passata dal chiamante (conn = get_connection())
- multi-tenant RLS: studio_id con DEFAULT current_setting('app.current_studio', true)
  + ENABLE/FORCE ROW LEVEL SECURITY + policy USING/WITH CHECK
- placeholder psycopg2 %s, BIGSERIAL, TEXT, TIMESTAMPTZ, timezone Europe/Rome lato lettura
- self-init idempotente: init_gamecenter_db(conn) si può chiamare a ogni avvio
"""

import json

# Catalogo dei giochi (slug -> nome, categoria). Tenuto in codice: niente tabella
# da mantenere. Lo slug è quello che ogni gioco scrive nella colonna "gioco".
GIOCHI = {
    "gonogo":     {"nome": "Premi o fermati (Go/No-Go)", "categoria": "Controllo degli impulsi"},
    "talpa":      {"nome": "Acchiappa la talpa",          "categoria": "Attenzione selettiva"},
    "coppie":     {"nome": "Trova le coppie",             "categoria": "Memoria di lavoro"},
    "palloncini": {"nome": "Palloncini",                  "categoria": "Attenzione selettiva"},
    "labirinto":  {"nome": "Labirinto",                   "categoria": "Coordinazione occhio-mano"},
}


def init_gamecenter_db(conn):
    """Crea la tabella gc_sessioni con RLS multi-tenant. Idempotente."""
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS gc_sessioni (
            id           BIGSERIAL PRIMARY KEY,
            studio_id    BIGINT      NOT NULL DEFAULT current_setting('app.current_studio', true)::bigint,
            paziente_id  BIGINT,
            visita_id    BIGINT,
            gioco        TEXT        NOT NULL,
            gioco_nome   TEXT,
            modalita     TEXT,
            metriche     JSONB,
            sintesi      TEXT,
            note         TEXT,
            creato_il    TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS ix_gc_sessioni_paziente
        ON gc_sessioni (paziente_id, creato_il DESC);
    """)
    # RLS come sulle altre tabelle del gestionale
    cur.execute("ALTER TABLE gc_sessioni ENABLE ROW LEVEL SECURITY;")
    cur.execute("ALTER TABLE gc_sessioni FORCE ROW LEVEL SECURITY;")
    cur.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_policies
                WHERE tablename = 'gc_sessioni' AND policyname = 'gc_sessioni_studio'
            ) THEN
                CREATE POLICY gc_sessioni_studio ON gc_sessioni
                    USING      (studio_id = current_setting('app.current_studio', true)::bigint)
                    WITH CHECK (studio_id = current_setting('app.current_studio', true)::bigint);
            END IF;
        END $$;
    """)
    conn.commit()


def salva_sessione(conn, paziente_id, gioco,
                   gioco_nome=None, modalita=None, metriche=None,
                   sintesi=None, note=None, visita_id=None):
    """
    Inserisce una partita e restituisce l'id.
    studio_id lo mette il DEFAULT dalla connessione (RLS), non va passato.
    metriche: dict Python -> salvato come JSONB.
    """
    if gioco_nome is None and gioco in GIOCHI:
        gioco_nome = GIOCHI[gioco]["nome"]
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO gc_sessioni
            (paziente_id, visita_id, gioco, gioco_nome, modalita, metriche, sintesi, note)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (
        paziente_id, visita_id, gioco, gioco_nome, modalita,
        json.dumps(metriche, ensure_ascii=False) if metriche is not None else None,
        sintesi, note,
    ))
    new_id = cur.fetchone()[0]
    conn.commit()
    return new_id


def lista_sessioni_paziente(conn, paziente_id, gioco=None, limite=100):
    """Ritorna le partite di un paziente, più recenti prima. Filtro opzionale per gioco."""
    cur = conn.cursor()
    if gioco:
        cur.execute("""
            SELECT id, paziente_id, visita_id, gioco, gioco_nome, modalita,
                   metriche, sintesi, note, creato_il
            FROM gc_sessioni
            WHERE paziente_id = %s AND gioco = %s
            ORDER BY creato_il DESC
            LIMIT %s
        """, (paziente_id, gioco, limite))
    else:
        cur.execute("""
            SELECT id, paziente_id, visita_id, gioco, gioco_nome, modalita,
                   metriche, sintesi, note, creato_il
            FROM gc_sessioni
            WHERE paziente_id = %s
            ORDER BY creato_il DESC
            LIMIT %s
        """, (paziente_id, limite))
    return cur.fetchall()


def get_sessione(conn, sessione_id):
    """Una singola partita per id (o None)."""
    cur = conn.cursor()
    cur.execute("""
        SELECT id, paziente_id, visita_id, gioco, gioco_nome, modalita,
               metriche, sintesi, note, creato_il
        FROM gc_sessioni
        WHERE id = %s
    """, (sessione_id,))
    return cur.fetchone()


def elimina_sessione(conn, sessione_id):
    """Cancella una partita (l'RLS garantisce che sia dello studio corrente)."""
    cur = conn.cursor()
    cur.execute("DELETE FROM gc_sessioni WHERE id = %s", (sessione_id,))
    conn.commit()
    return cur.rowcount


def conta_sessioni_paziente(conn, paziente_id):
    """Numero di partite totali del paziente (per badge/riassunti)."""
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM gc_sessioni WHERE paziente_id = %s", (paziente_id,))
    row = cur.fetchone()
    return int(row[0]) if row else 0
