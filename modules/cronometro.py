# -*- coding: utf-8 -*-
"""Cronometro dei clic.

Misura, a ogni clic, quanto lavora il server (millisecondi) e quante
richieste partono verso il database. Serve a capire quali schermate sono
lente con i dati veri, invece di andare a impressione.

Cosa viene salvato (tabella crono_clic): ora, studio, utente, area e voce
del menu, millisecondi, numero di richieste. Nessun dato dei pazienti.
Le righe più vecchie di 30 giorni si cancellano da sole.

Regola di sicurezza: qui dentro NIENTE deve poter bloccare il gestionale.
Ogni funzione ingoia i propri errori; se il cronometro si rompe, la pagina
si apre lo stesso, solo senza misura.

Per spegnerlo: Secrets → CRONOMETRO = "off" (oppure variabile d'ambiente).
"""
from __future__ import annotations

import os
import threading
import time

_loc = threading.local()          # Streamlit esegue ogni clic in un suo thread
_pronta = {"tabella": False, "pulizia": 0.0}
_lucchetto = threading.Lock()   # una sola scrittura alla volta sulla connessione del cronometro
GIORNI = 30


def _attivo() -> bool:
    try:
        v = os.environ.get("CRONOMETRO")
        if v is None:
            import streamlit as st
            try:
                v = st.secrets.get("CRONOMETRO")
            except Exception:
                v = None
        return str(v or "on").strip().lower() not in ("off", "0", "no", "false")
    except Exception:
        return True


def conta_sql() -> None:
    """Chiamata dal cursore a ogni richiesta al database. Deve costare nulla."""
    try:
        _loc.n = getattr(_loc, "n", 0) + 1
    except Exception:
        pass


def avvia() -> None:
    """Inizio del clic."""
    try:
        _loc.t0 = time.perf_counter()
        _loc.n = 0
    except Exception:
        pass


def _conn_propria():
    """Connessione riservata al cronometro, in autocommit.

    NON si usa quella delle pagine: quella è condivisa e può avere una
    transazione aperta (una scrittura non ancora confermata). Un commit
    fatto da qui confermerebbe a metà il lavoro della pagina. Con una
    connessione a parte il cronometro non tocca mai i dati clinici."""
    c = _pronta.get("conn")
    if c is not None and not getattr(c, "closed", 1):
        return c
    import psycopg2
    from modules import app_core as _ac
    if getattr(_ac, "_DB_BACKEND", "") != "postgres" or not getattr(_ac, "_DB_URL", ""):
        return None
    c = psycopg2.connect(_ac._DB_URL, connect_timeout=5,
                         options="-c statement_timeout=3000", application_name="cronometro")
    c.autocommit = True
    _pronta["conn"] = c
    _pronta["tabella"] = False
    return c


def _assicura(conn) -> None:
    if _pronta["tabella"]:
        return
    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE IF NOT EXISTS crono_clic ("
        " id BIGSERIAL PRIMARY KEY,"
        " quando TIMESTAMPTZ NOT NULL DEFAULT NOW(),"
        " studio_id INTEGER, utente TEXT, area TEXT, voce TEXT,"
        " ms INTEGER NOT NULL, n_sql INTEGER NOT NULL)")
    cur.execute("CREATE INDEX IF NOT EXISTS crono_clic_quando_idx ON crono_clic (quando)")
    _pronta["tabella"] = True


def chiudi(get_connection=None) -> None:
    """Fine del clic: salva la misura. Va chiamata in un «finally»."""
    try:
        t0 = getattr(_loc, "t0", None)
        if t0 is None:
            return
        ms = int(round((time.perf_counter() - t0) * 1000))
        n = int(getattr(_loc, "n", 0))
        _loc.t0 = None
        import streamlit as st
        ss = st.session_state
        area = ss.get("nav_area") or ""
        voce = ss.get("_crono_voce") or ""
        # Il clic appena chiuso si mostra al prossimo giro (vedi riquadro()).
        ss["_crono_ultimo"] = {"ms": ms, "n": n, "area": area, "voce": voce}
        if not _attivo():
            return
        u = ss.get("user") or {}
        utente = (u.get("username") or u.get("email") or "") if isinstance(u, dict) else ""
        try:
            sid = int(ss.get("studio_id") or 1)
        except Exception:
            sid = 1
        with _lucchetto:
            try:
                conn = _conn_propria()
                if conn is None:
                    return
                _assicura(conn)
                cur = conn.cursor()
                cur.execute("INSERT INTO crono_clic (studio_id, utente, area, voce, ms, n_sql) "
                            "VALUES (%s,%s,%s,%s,%s,%s)",
                            (sid, str(utente)[:80], str(area)[:80], str(voce)[:120], ms, n))
                # Pulizia: al massimo una volta all'ora per processo.
                if time.time() - _pronta["pulizia"] > 3600:
                    _pronta["pulizia"] = time.time()
                    cur.execute(f"DELETE FROM crono_clic WHERE quando < NOW() - INTERVAL '{GIORNI} days'")
                cur.close()
            except Exception:
                # Connessione caduta o altro: si butta e si riapre al prossimo clic.
                try:
                    c = _pronta.pop("conn", None)
                    if c is not None:
                        c.close()
                except Exception:
                    pass
    except Exception:
        pass


def riepilogo(conn, giorni: int = 7, minimo: int = 3) -> list[dict]:
    """Schermate degli ultimi `giorni`, dalla più lenta. Tempo tipico = mediana."""
    cur = conn.cursor()
    cur.execute(
        "SELECT area, voce, COUNT(*) AS clic,"
        " ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ms)) AS tipico,"
        " ROUND(PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY ms)) AS lento,"
        " MAX(ms) AS massimo, ROUND(AVG(n_sql)) AS richieste"
        " FROM crono_clic WHERE quando > NOW() - (%s * INTERVAL '1 day')"
        " GROUP BY area, voce HAVING COUNT(*) >= %s"
        " ORDER BY tipico DESC LIMIT 25", (int(giorni), int(minimo)))
    out = []
    for r in cur.fetchall() or []:
        g = (lambda k, i: r.get(k) if hasattr(r, "get") else r[i])
        out.append({"Area": g("area", 0), "Schermata": g("voce", 1), "Clic": int(g("clic", 2) or 0),
                    "Tempo tipico (ms)": int(g("tipico", 3) or 0),
                    "1 clic su 10 oltre (ms)": int(g("lento", 4) or 0),
                    "Massimo (ms)": int(g("massimo", 5) or 0),
                    "Richieste al database": int(g("richieste", 6) or 0)})
    return out


def riquadro(get_connection, is_admin: bool) -> None:
    """In fondo al menu, solo per l'amministratore: il clic precedente e,
    a richiesta, la classifica delle schermate lente."""
    if not is_admin:
        return
    try:
        import streamlit as st
        with st.sidebar.expander("⏱️ Cronometro"):
            u = st.session_state.get("_crono_ultimo")
            if u:
                st.caption(f"Clic precedente — {u.get('voce') or u.get('area') or 'pagina'}: "
                           f"**{u['ms']} ms** di lavoro del server, {u['n']} richieste al database.")
            else:
                st.caption("La misura compare dal secondo clic.")
            if not _attivo():
                st.caption("Registrazione spenta (CRONOMETRO = off).")
                return
            if st.checkbox("Mostra le schermate più lente (ultimi 7 giorni)", key="_crono_mostra"):
                try:
                    righe = riepilogo(get_connection())
                except Exception as e:
                    try:
                        get_connection().rollback()
                    except Exception:
                        pass
                    righe = []
                    st.caption(f"Ancora nessun dato leggibile ({e}).")
                if righe:
                    import pandas as pd
                    st.dataframe(pd.DataFrame(righe), hide_index=True, use_container_width=True)
                    st.caption("Solo schermate con almeno 3 clic. È il tempo del server: "
                               "non comprende rete e browser.")
                else:
                    st.caption("Servono almeno 3 clic sulla stessa schermata.")
    except Exception:
        pass
