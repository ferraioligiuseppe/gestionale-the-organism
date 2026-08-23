# -*- coding: utf-8 -*-
"""
modules/cuffie_uditivo.py

Riceve gli esiti dello screening uditivo in cuffia (screening_cuffie_pnev.html)
compilato su pnev.it e li salva collegati all'email del paziente.
Stesso pattern di consenso_ascolti.py / screening_uditivo.py.
"""

import streamlit as st

TOKEN_SEGRETO = "pnev_cuffie_2026"


def _assicura_tabella(conn):
    cur = conn.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS screening_cuffie_pnev (
                id          BIGSERIAL PRIMARY KEY,
                studio_id   BIGINT NOT NULL DEFAULT current_setting('app.current_studio', true)::bigint,
                email       TEXT NOT NULL,
                paziente_id BIGINT,
                nome        TEXT,
                soglie      TEXT,
                inviato_il  TIMESTAMPTZ NOT NULL DEFAULT now()
            );
        """)
        cur.execute("""CREATE INDEX IF NOT EXISTS ix_screening_cuffie_email
                       ON screening_cuffie_pnev (email);""")
        cur.execute("ALTER TABLE screening_cuffie_pnev ENABLE ROW LEVEL SECURITY;")
        cur.execute("ALTER TABLE screening_cuffie_pnev FORCE ROW LEVEL SECURITY;")
        cur.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_policies
                               WHERE tablename='screening_cuffie_pnev' AND policyname='screening_cuffie_pnev_studio') THEN
                    CREATE POLICY screening_cuffie_pnev_studio ON screening_cuffie_pnev
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


def _notifica_cuffie(email, nome, soglie):
    try:
        from modules.ui_questionari import _invia_email
        dest = (st.secrets.get("smtp", {}).get("NOTIFICA_A")
                or st.secrets.get("smtp", {}).get("USERNAME"))
        if not dest:
            return
        corpo = (
            f"Nuovo screening uditivo in cuffia dal sito pnev.it\n\n"
            f"Nome: {nome or '—'}\nEmail: {email}\nSoglie: {soglie or '—'}\n"
        )
        _invia_email(dest, f"PNEV — Screening cuffia: {nome or email}", corpo)
    except Exception:
        pass


def registra_cuffie(conn, email, nome, soglie):
    cur = conn.cursor()
    try:
        pid = _collega_paziente(conn, email)
        cur.execute("""
            INSERT INTO screening_cuffie_pnev (email, paziente_id, nome, soglie)
            VALUES (%s,%s,%s,%s)
        """, (email, pid, nome, soglie))
        conn.commit()
        return True
    except Exception:
        try: conn.rollback()
        except Exception: pass
        raise
    finally:
        try: cur.close()
        except Exception: pass


def ui_public_cuffie_hook(get_conn):
    """Endpoint pubblico: ?cuffie_hook=1&token=...&email=...&nome=...&soglie=..."""
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
    soglie = p("soglie").strip()
    conn = get_conn()
    try:
        _assicura_tabella(conn)
        registra_cuffie(conn, email, nome, soglie)
        _notifica_cuffie(email, nome, soglie)
        st.write("ok")
    except Exception as e:
        st.write(f"errore: {e}")


def render_screening_cuffie(conn):
    st.subheader("🎧 Screening cuffie dal sito")
    st.caption("Esiti della calibrazione/screening in cuffia compilati su pnev.it.")
    try:
        _assicura_tabella(conn)
    except Exception as e:
        st.error(f"Tabella non disponibile: {e}")
        return
    cur = conn.cursor()
    try:
        cur.execute("""SELECT email, nome, soglie, inviato_il
                       FROM screening_cuffie_pnev ORDER BY inviato_il DESC LIMIT 300""")
        righe = cur.fetchall()
    except Exception as e:
        st.error(f"Errore lettura: {e}")
        return
    if not righe:
        st.info("Nessuno screening cuffie ricevuto ancora.")
        return
    import pandas as pd
    df = pd.DataFrame(righe, columns=["Email", "Nome", "Soglie", "Ricevuto il"])
    st.dataframe(df, use_container_width=True, hide_index=True)
