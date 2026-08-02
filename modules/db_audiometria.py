# -*- coding: utf-8 -*-
"""
modules/db_audiometria.py

Storage per gli esami di Audiometria Tonale con Calibrazione (PNEV-audiometria-v1.html).
Il paziente/esaminatore compila l'esame nel file HTML autonomo, copia il codice JSON
e lo incolla nel campo "Importa esame" del modulo Diagnostica Uditiva.
"""
import json
import streamlit as st


def assicura_tabella(conn):
    cur = conn.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS audiometrie_tonali (
                id           BIGSERIAL PRIMARY KEY,
                studio_id    BIGINT NOT NULL DEFAULT current_setting('app.current_studio', true)::bigint,
                paziente_id  BIGINT NOT NULL,
                modalita     TEXT,
                cuffia       TEXT,
                tipo_cuffia  TEXT,
                dispositivo  TEXT,
                volume       TEXT,
                calibrazione TEXT,
                cal_data     TEXT,
                canali_swap  BOOLEAN DEFAULT FALSE,
                pta_od       NUMERIC,
                pta_os       NUMERIC,
                falsi_pos    INTEGER,
                dati_json    JSONB NOT NULL,
                creato_il    TIMESTAMPTZ NOT NULL DEFAULT now()
            );
        """)
        cur.execute("""CREATE INDEX IF NOT EXISTS ix_audiometrie_paziente
                       ON audiometrie_tonali (paziente_id);""")
        cur.execute("ALTER TABLE audiometrie_tonali ENABLE ROW LEVEL SECURITY;")
        cur.execute("ALTER TABLE audiometrie_tonali FORCE ROW LEVEL SECURITY;")
        cur.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_policies
                               WHERE tablename='audiometrie_tonali' AND policyname='audiometrie_tonali_studio') THEN
                    CREATE POLICY audiometrie_tonali_studio ON audiometrie_tonali
                        USING      (studio_id = current_setting('app.current_studio', true)::bigint)
                        WITH CHECK (studio_id = current_setting('app.current_studio', true)::bigint);
                END IF;
            END $$;
        """)
        conn.commit()
    except Exception:
        try: conn.rollback()
        except Exception: pass
        raise
    finally:
        try: cur.close()
        except Exception: pass


def salva_esame(conn, paziente_id, dati: dict):
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO audiometrie_tonali
                (paziente_id, modalita, cuffia, tipo_cuffia, dispositivo, volume,
                 calibrazione, cal_data, canali_swap, pta_od, pta_os, falsi_pos, dati_json)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            paziente_id,
            dati.get("mode"),
            dati.get("cuffia"),
            dati.get("tipo"),
            dati.get("dispositivo"),
            dati.get("volume"),
            dati.get("cal"),
            dati.get("calData"),
            bool(dati.get("swap")),
            (dati.get("pta") or {}).get("od"),
            (dati.get("pta") or {}).get("os"),
            dati.get("fp"),
            json.dumps(dati),
        ))
        conn.commit()
        return True
    except Exception:
        try: conn.rollback()
        except Exception: pass
        raise
    finally:
        try: cur.close()
        except Exception: pass


def lista_esami(conn, paziente_id):
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id, modalita, cuffia, calibrazione, pta_od, pta_os, falsi_pos, dati_json, creato_il
            FROM audiometrie_tonali
            WHERE paziente_id=%s
            ORDER BY creato_il DESC
        """, (paziente_id,))
        return cur.fetchall()
    except Exception:
        try: conn.rollback()
        except Exception: pass
        return []
    finally:
        try: cur.close()
        except Exception: pass


def elimina_esame(conn, esame_id):
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM audiometrie_tonali WHERE id=%s", (esame_id,))
        conn.commit()
        return True
    except Exception:
        try: conn.rollback()
        except Exception: pass
        raise
    finally:
        try: cur.close()
        except Exception: pass
