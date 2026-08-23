# -*- coding: utf-8 -*-
"""
modules/screening_uditivo.py

Riceve gli esiti del questionario di screening uditivo compilato su pnev.it
(screening_pnev.html) e li salva collegati all'email del paziente.
Stesso pattern di consenso_ascolti.py / ascolti_maps.py.
"""

import streamlit as st

TOKEN_SEGRETO = "pnev_screening_2026"


def _assicura_tabella(conn):
    cur = conn.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS screening_uditivo_pnev (
                id          BIGSERIAL PRIMARY KEY,
                studio_id   BIGINT NOT NULL DEFAULT current_setting('app.current_studio', true)::bigint,
                email       TEXT NOT NULL,
                paziente_id BIGINT,
                nome        TEXT,
                nascita     TEXT,
                strumento   TEXT,
                esito       TEXT,
                voci        TEXT,
                inviato_il  TIMESTAMPTZ NOT NULL DEFAULT now()
            );
        """)
        cur.execute("""CREATE INDEX IF NOT EXISTS ix_screening_uditivo_email
                       ON screening_uditivo_pnev (email);""")
        cur.execute("ALTER TABLE screening_uditivo_pnev ENABLE ROW LEVEL SECURITY;")
        cur.execute("ALTER TABLE screening_uditivo_pnev FORCE ROW LEVEL SECURITY;")
        cur.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_policies
                               WHERE tablename='screening_uditivo_pnev' AND policyname='screening_uditivo_pnev_studio') THEN
                    CREATE POLICY screening_uditivo_pnev_studio ON screening_uditivo_pnev
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


def _collega_paziente(conn, email):
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM pazienti WHERE lower(email)=lower(%s) LIMIT 1", (email,))
        r = cur.fetchone()
        return int(r[0]) if r else None
    except Exception:
        try: conn.rollback()
        except Exception: pass
        return None


def _notifica_screening(email, nome, strumento, esito):
    try:
        from modules.ui_questionari import _invia_email
        dest = (st.secrets.get("smtp", {}).get("NOTIFICA_A")
                or st.secrets.get("smtp", {}).get("USERNAME"))
        if not dest:
            return
        corpo = (
            f"Nuovo esito di screening uditivo dal sito pnev.it\n\n"
            f"Nome: {nome or '—'}\nEmail: {email}\n"
            f"Strumento: {strumento or '—'}\nEsito: {esito or '—'}\n"
        )
        _invia_email(dest, f"PNEV — Screening uditivo: {nome or email}", corpo)
    except Exception:
        pass


def registra_screening(conn, email, nome, nascita, strumento, esito, voci):
    cur = conn.cursor()
    try:
        pid = _collega_paziente(conn, email)
        cur.execute("""
            INSERT INTO screening_uditivo_pnev (email, paziente_id, nome, nascita, strumento, esito, voci)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (email, pid, nome, nascita, strumento, esito, voci))
        conn.commit()
        return True
    except Exception:
        try: conn.rollback()
        except Exception: pass
        raise
    finally:
        try: cur.close()
        except Exception: pass


def ui_public_screening_hook(get_conn):
    """Endpoint pubblico: ?screening_hook=1&token=...&email=...&nome=...&nascita=...
    &strumento=...&esito=...&voci=..."""
    qs = st.query_params
    def p(k, d=""):
        v = qs.get(k, d)
        return (v[0] if isinstance(v, list) and v else v) or d

    if p("token") != TOKEN_SEGRETO:
        st.write("no")
        return
    email = p("email").strip()
    if not email:
        st.write("no")
        return
    nome = p("nome").strip()
    nascita = p("nascita").strip()
    strumento = p("strumento").strip()
    esito = p("esito").strip()
    voci = p("voci").strip()
    conn = get_conn()
    try:
        _assicura_tabella(conn)
        registra_screening(conn, email, nome, nascita, strumento, esito, voci)
        _notifica_screening(email, nome, strumento, esito)
        st.write("ok")
    except Exception as e:
        st.write(f"errore: {e}")


def render_screening_uditivo(conn):
    st.subheader("🎧 Screening uditivi dal sito")
    st.caption("Esiti dei questionari compilati su pnev.it, con collegamento all'anagrafica quando l'email combacia.")
    try:
        _assicura_tabella(conn)
    except Exception as e:
        st.error(f"Tabella non disponibile: {e}")
        return
    cur = conn.cursor()
    try:
        cur.execute("""SELECT email, nome, nascita, strumento, esito, voci, inviato_il
                       FROM screening_uditivo_pnev ORDER BY inviato_il DESC LIMIT 300""")
        righe = cur.fetchall()
    except Exception as e:
        st.error(f"Errore lettura: {e}")
        return
    if not righe:
        st.info("Nessuno screening ricevuto ancora.")
        return
    import pandas as pd
    df = pd.DataFrame(righe, columns=["Email", "Nome", "Data nascita", "Strumento", "Esito", "Voci segnalate", "Ricevuto il"])
    st.dataframe(df, use_container_width=True, hide_index=True)
