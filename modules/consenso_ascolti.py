# -*- coding: utf-8 -*-
"""
modules/consenso_ascolti.py

Consenso informato per il percorso di ascolti MAPS (pnev.it).
Stesso pattern di modules/ascolti_maps.py: endpoint pubblico "a pixel"
chiamato dal browser del sito, nessun login richiesto.
"""

import datetime
import streamlit as st

TOKEN_SEGRETO = "pnev_consenso_2026"
VERSIONE_TESTO = "v1-2026-08"  # aggiorna se cambi il testo del disclaimer sul sito


def _assicura_tabella(conn):
    cur = conn.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS consensi_ascolti_maps (
                id            BIGSERIAL PRIMARY KEY,
                studio_id     BIGINT NOT NULL DEFAULT current_setting('app.current_studio', true)::bigint,
                email         TEXT NOT NULL,
                nome          TEXT,
                paziente_id   BIGINT,
                versione_testo TEXT,
                pagina        TEXT,
                accettato_il  TIMESTAMPTZ NOT NULL DEFAULT now()
            );
        """)
        cur.execute("""CREATE INDEX IF NOT EXISTS ix_consensi_ascolti_email
                       ON consensi_ascolti_maps (email);""")
        cur.execute("ALTER TABLE consensi_ascolti_maps ENABLE ROW LEVEL SECURITY;")
        cur.execute("ALTER TABLE consensi_ascolti_maps FORCE ROW LEVEL SECURITY;")
        cur.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_policies
                               WHERE tablename='consensi_ascolti_maps' AND policyname='consensi_ascolti_maps_studio') THEN
                    CREATE POLICY consensi_ascolti_maps_studio ON consensi_ascolti_maps
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


def registra_consenso(conn, email, nome, pagina, versione):
    cur = conn.cursor()
    try:
        pid = _collega_paziente(conn, email)
        cur.execute("""
            INSERT INTO consensi_ascolti_maps (email, nome, paziente_id, versione_testo, pagina)
            VALUES (%s,%s,%s,%s,%s)
        """, (email, nome, pid, versione, pagina))
        conn.commit()
        return True
    except Exception:
        try: conn.rollback()
        except Exception: pass
        raise
    finally:
        try: cur.close()
        except Exception: pass


def ui_public_consenso_hook(get_conn):
    """Endpoint pubblico: ?consenso_hook=1&token=...&email=...&nome=...&pagina=..."""
    qs = st.query_params
    def p(k, d=""):
        v = qs.get(k, d)
        return (v[0] if isinstance(v, list) and v else v) or d

    if p("token") != TOKEN_SEGRETO:
        st.write("no")
        return
    email = p("email").strip()
    nome = p("nome").strip()
    pagina = p("pagina").strip() or "percorso-uditivo-maps"
    if not email:
        st.write("no")
        return
    conn = get_conn()
    try:
        _assicura_tabella(conn)
        registra_consenso(conn, email, nome, pagina, VERSIONE_TESTO)
        st.write("ok")
    except Exception as e:
        st.write(f"errore: {e}")


def render_consensi_ascolti(conn):
    st.subheader("📝 Consensi ascolti MAPS")
    st.caption("Chi ha confermato di aver letto l'avviso prima di iniziare gli ascolti, e quando.")
    try:
        _assicura_tabella(conn)
    except Exception as e:
        st.error(f"Tabella non disponibile: {e}")
        return
    cur = conn.cursor()
    try:
        cur.execute("""SELECT email, nome, versione_testo, pagina, accettato_il
                       FROM consensi_ascolti_maps ORDER BY accettato_il DESC LIMIT 300""")
        righe = cur.fetchall()
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        st.error(f"Errore lettura: {e}")
        return
    if not righe:
        st.info("Nessun consenso ancora registrato.")
        return
    for r in righe:
        email, nome, versione, pagina, accettato_il = r[0], r[1], r[2], r[3], r[4]
        st.markdown(f"**{nome or '—'}** · {email} — *{versione}* · {pagina} · {accettato_il.strftime('%d/%m/%Y %H:%M') if accettato_il else ''}")
