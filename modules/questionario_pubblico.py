# -*- coding: utf-8 -*-
"""
modules/questionario_pubblico.py

Questionari pubblici PNEV (Fisher bambino, Potenziale adulto) — pagine autonome
sul sito, nessun login. Stesso pattern di consenso_ascolti.py.
"""
import streamlit as st

TOKEN_SEGRETO = "pnev_questionario_2026"


def _assicura_tabella(conn):
    cur = conn.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS questionari_pubblici (
                id           BIGSERIAL PRIMARY KEY,
                studio_id    BIGINT NOT NULL DEFAULT current_setting('app.current_studio', true)::bigint,
                tipo         TEXT NOT NULL,
                nome         TEXT,
                email        TEXT NOT NULL,
                punteggio    TEXT,
                esito        TEXT,
                paziente_id  BIGINT,
                creato_il    TIMESTAMPTZ NOT NULL DEFAULT now()
            );
        """)
        cur.execute("""CREATE INDEX IF NOT EXISTS ix_questionari_pubblici_email
                       ON questionari_pubblici (email);""")
        cur.execute("ALTER TABLE questionari_pubblici ENABLE ROW LEVEL SECURITY;")
        cur.execute("ALTER TABLE questionari_pubblici FORCE ROW LEVEL SECURITY;")
        cur.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_policies
                               WHERE tablename='questionari_pubblici' AND policyname='questionari_pubblici_studio') THEN
                    CREATE POLICY questionari_pubblici_studio ON questionari_pubblici
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


def registra_questionario(conn, tipo, nome, email, punteggio, esito):
    cur = conn.cursor()
    try:
        pid = _collega_paziente(conn, email)
        cur.execute("""
            INSERT INTO questionari_pubblici (tipo, nome, email, punteggio, esito, paziente_id)
            VALUES (%s,%s,%s,%s,%s,%s)
        """, (tipo, nome, email, punteggio, esito, pid))
        conn.commit()
        return True
    except Exception:
        try: conn.rollback()
        except Exception: pass
        raise
    finally:
        try: cur.close()
        except Exception: pass


def ui_public_questionario_hook(get_conn):
    """Endpoint pubblico: ?questionario_hook=1&token=...&tipo=...&nome=...&email=...&punteggio=...&esito=..."""
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
    conn = get_conn()
    try:
        _assicura_tabella(conn)
        registra_questionario(conn, p("tipo") or "sconosciuto", p("nome").strip(), email,
                               p("punteggio"), p("esito"))
        st.write("ok")
    except Exception as e:
        st.write(f"errore: {e}")


def render_questionari_pubblici(conn):
    st.subheader("📋 Questionari compilati dal sito")
    st.caption("Fisher (bambino) e Potenziale (adulto), compilati autonomamente su pnev.it.")
    try:
        _assicura_tabella(conn)
    except Exception as e:
        st.error(f"Tabella non disponibile: {e}")
        return
    cur = conn.cursor()
    try:
        cur.execute("""SELECT tipo, nome, email, punteggio, esito, creato_il
                       FROM questionari_pubblici ORDER BY creato_il DESC LIMIT 300""")
        righe = cur.fetchall()
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        st.error(f"Errore lettura: {e}")
        return
    if not righe:
        st.info("Nessun questionario ancora ricevuto dal sito.")
        return
    for r in righe:
        tipo, nome, email, punteggio, esito, creato_il = r
        bollino = "🟠" if esito == "da_approfondire" else "🟢"
        st.markdown(f"{bollino} **{nome or '—'}** · {email} — *{tipo}* · punteggio {punteggio} · "
                    f"{creato_il.strftime('%d/%m/%Y %H:%M') if creato_il else ''}")
