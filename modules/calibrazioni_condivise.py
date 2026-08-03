# -*- coding: utf-8 -*-
"""
modules/calibrazioni_condivise.py

Libreria condivisa di calibrazioni cuffie (crowd-sourced) — ogni volta che
qualcuno calibra un modello di cuffia su PNEV-audiometria-v1.html, la curva
biologica (soglie per frequenza/orecchio) viene inviata qui. Più calibrazioni
per lo stesso modello arrivano, più affidabile diventa il profilo medio,
utilizzabile in futuro come "calibrazione generica" migliorata.
"""
import json
import streamlit as st

TOKEN_SEGRETO = "pnev_calibrazione_2026"
FREQS = [125, 250, 500, 750, 1000, 1500, 2000, 3000, 4000, 6000, 8000]


def _assicura_tabella(conn):
    cur = conn.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS calibrazioni_cuffie_condivise (
                id           BIGSERIAL PRIMARY KEY,
                studio_id    BIGINT NOT NULL DEFAULT current_setting('app.current_studio', true)::bigint,
                modello      TEXT NOT NULL,
                tipo         TEXT NOT NULL,
                dispositivo  TEXT,
                soglie_json  JSONB NOT NULL,
                creato_il    TIMESTAMPTZ NOT NULL DEFAULT now()
            );
        """)
        cur.execute("""CREATE INDEX IF NOT EXISTS ix_calibrazioni_modello
                       ON calibrazioni_cuffie_condivise (lower(modello));""")
        cur.execute("ALTER TABLE calibrazioni_cuffie_condivise ENABLE ROW LEVEL SECURITY;")
        cur.execute("ALTER TABLE calibrazioni_cuffie_condivise FORCE ROW LEVEL SECURITY;")
        cur.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_policies
                               WHERE tablename='calibrazioni_cuffie_condivise' AND policyname='calibrazioni_cuffie_condivise_studio') THEN
                    CREATE POLICY calibrazioni_cuffie_condivise_studio ON calibrazioni_cuffie_condivise
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


def registra_calibrazione(conn, modello, tipo, dispositivo, soglie: dict):
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO calibrazioni_cuffie_condivise (modello, tipo, dispositivo, soglie_json)
            VALUES (%s,%s,%s,%s)
        """, (modello, tipo, dispositivo, json.dumps(soglie)))
        conn.commit()
        return True
    except Exception:
        try: conn.rollback()
        except Exception: pass
        raise
    finally:
        try: cur.close()
        except Exception: pass


def ui_public_calibrazione_hook(get_conn):
    """Endpoint pubblico: ?calibrazione_hook=1&token=...&modello=...&tipo=...&dispositivo=...&soglie=<json-urlencoded>"""
    qs = st.query_params
    def p(k, d=""):
        v = qs.get(k, d)
        return (v[0] if isinstance(v, list) and v else v) or d

    if p("token") != TOKEN_SEGRETO:
        st.write("no")
        return
    modello = p("modello").strip()
    tipo = p("tipo").strip()
    dispositivo = p("dispositivo").strip()
    soglie_raw = p("soglie")
    if not modello or not soglie_raw:
        st.write("no")
        return
    try:
        soglie = json.loads(soglie_raw)
    except Exception:
        st.write("errore: soglie non valide")
        return
    conn = get_conn()
    try:
        _assicura_tabella(conn)
        registra_calibrazione(conn, modello, tipo, dispositivo, soglie)
        st.write("ok")
    except Exception as e:
        st.write(f"errore: {e}")


def _media_soglie(righe_soglie):
    """Media aritmetica per frequenza/orecchio su una lista di dict {R:{},L:{}}."""
    somma = {"R": {}, "L": {}}
    conteggio = {"R": {}, "L": {}}
    for soglie in righe_soglie:
        for ear in ("R", "L"):
            for f_str, v in (soglie.get(ear) or {}).items():
                try:
                    f = int(f_str)
                    val = float(v)
                except Exception:
                    continue
                somma[ear][f] = somma[ear].get(f, 0.0) + val
                conteggio[ear][f] = conteggio[ear].get(f, 0) + 1
    media = {"R": {}, "L": {}}
    for ear in ("R", "L"):
        for f, tot in somma[ear].items():
            media[ear][f] = round(tot / conteggio[ear][f], 1)
    return media


def render_calibrazioni_condivise(conn):
    st.subheader("🎧 Libreria calibrazioni cuffie (condivisa)")
    st.caption("Ogni volta che un utente calibra una cuffia su PNEV-audiometria-v1.html, la curva arriva qui. "
               "Più calibrazioni per lo stesso modello, più affidabile diventa il profilo medio.")
    try:
        _assicura_tabella(conn)
    except Exception as e:
        st.error(f"Tabella non disponibile: {e}")
        return
    cur = conn.cursor()
    try:
        cur.execute("""SELECT modello, tipo, soglie_json, creato_il
                       FROM calibrazioni_cuffie_condivise ORDER BY modello, creato_il DESC""")
        righe = cur.fetchall()
    except Exception as e:
        try: conn.rollback()
        except Exception: pass
        st.error(f"Errore lettura: {e}")
        return
    if not righe:
        st.info("Nessuna calibrazione ancora ricevuta.")
        return

    per_modello = {}
    for modello, tipo, soglie_json, creato_il in righe:
        soglie = soglie_json if isinstance(soglie_json, dict) else json.loads(soglie_json)
        chiave = modello.strip().lower()
        per_modello.setdefault(chiave, {"nome": modello, "tipo": tipo, "soglie": [], "ultima": creato_il})
        per_modello[chiave]["soglie"].append(soglie)
        if creato_il and creato_il > per_modello[chiave]["ultima"]:
            per_modello[chiave]["ultima"] = creato_il

    for chiave, info in sorted(per_modello.items(), key=lambda kv: -len(kv[1]["soglie"])):
        n = len(info["soglie"])
        with st.expander(f"{info['nome']} ({info['tipo']}) — {n} calibrazion{'e' if n==1 else 'i'}", expanded=False):
            media = _media_soglie(info["soglie"])
            cols = st.columns(2)
            for i, ear in enumerate(("R", "L")):
                with cols[i]:
                    st.markdown(f"**{'Destro' if ear=='R' else 'Sinistro'}**")
                    if media[ear]:
                        for f in sorted(media[ear].keys()):
                            st.caption(f"{f} Hz — {media[ear][f]:.1f} dBFS (soglia media)")
                    else:
                        st.caption("—")
            st.caption(f"Ultima calibrazione ricevuta: {info['ultima'].strftime('%d/%m/%Y %H:%M') if info['ultima'] else '—'}")
