# -*- coding: utf-8 -*-
"""Registro delle attività e cronologia del paziente.

Due fonti, una sola linea del tempo:
  1. registro_attivita — gli eventi che il gestionale annota da solo:
     paziente creato, scheda aperta, anagrafica modificata (con chi e quando).
  2. le tabelle cliniche — ogni valutazione, seduta, documento, diario…
     ha una data: si legge da li', cosi' la cronologia c'e' anche per
     quello che e' stato salvato prima che esistesse questo registro.

Nota sulle date di registrazione: la colonna pazienti.creato_il e' stata
aggiunta in un secondo momento con DEFAULT NOW(): tutti i pazienti che
esistevano gia' hanno ricevuto la stessa data, quella dell'aggiunta. Qui
quella data viene riconosciuta e mostrata come «non registrata».
"""
from __future__ import annotations

import datetime as dt

import streamlit as st

_TS_PREFERITE = ("created_at", "creato_il", "creata_il", "data_ora", "updated_at", "aggiornato_il")
_D_PREFERITE = ("data", "data_valutazione", "data_seduta", "data_esame", "data_anamnesi", "inizio")


def _q(conn, sql, par=()):
    try:
        cur = conn.cursor()
        cur.execute(sql, par)
        r = cur.fetchall() or []
        if r and not isinstance(r[0], dict):
            n = [c[0] for c in cur.description]
            r = [dict(zip(n, x)) for x in r]
        return r
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return []


def _esegui(conn, sql, par=()):
    try:
        cur = conn.cursor()
        cur.execute(sql, par)
        conn.commit()
        return True
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False


def _utente():
    return str(st.session_state.get("username") or st.session_state.get("user") or "")


def _tabella(conn):
    if st.session_state.get("_reg_att_ok"):
        return
    if _esegui(conn,
        "CREATE TABLE IF NOT EXISTS registro_attivita ("
        " id BIGSERIAL PRIMARY KEY, paziente_id BIGINT, quando TIMESTAMPTZ DEFAULT NOW(),"
        " utente TEXT, azione TEXT, dettaglio TEXT);"
        "CREATE INDEX IF NOT EXISTS registro_attivita_paz ON registro_attivita (paziente_id, quando DESC);"
        "CREATE INDEX IF NOT EXISTS registro_attivita_quando ON registro_attivita (quando DESC);"):
        st.session_state["_reg_att_ok"] = True


def registra(conn, paz_id, azione, dettaglio="", ogni_minuti=None):
    """Annota un evento. Con ogni_minuti non ripete lo stesso evento dello
    stesso utente sullo stesso paziente entro quel tempo (es. «scheda aperta»)."""
    if conn is None:
        return
    _tabella(conn)
    utente = _utente()
    if ogni_minuti:
        r = _q(conn, "SELECT 1 FROM registro_attivita WHERE paziente_id=%s AND azione=%s AND utente=%s "
                     "AND quando > NOW() - (%s || ' minutes')::interval LIMIT 1",
               (int(paz_id) if paz_id else None, azione, utente, str(int(ogni_minuti))))
        if r:
            return
    _esegui(conn, "INSERT INTO registro_attivita (paziente_id, utente, azione, dettaglio) VALUES (%s,%s,%s,%s)",
            (int(paz_id) if paz_id else None, utente, azione, (dettaglio or "")[:500]))


def _data_alter(conn):
    """La data in cui creato_il e' stata aggiunta: la condividono molti pazienti."""
    if "_reg_data_alter" in st.session_state:
        return st.session_state["_reg_data_alter"]
    r = _q(conn, "SELECT date_trunc('minute', creato_il) AS t, COUNT(*) AS n FROM pazienti "
                 "WHERE creato_il IS NOT NULL GROUP BY 1 HAVING COUNT(*) >= 5 ORDER BY 2 DESC LIMIT 1")
    v = r[0]["t"] if r else None
    st.session_state["_reg_data_alter"] = v
    return v


def data_registrazione(conn, rec):
    """(testo, affidabile) della data di registrazione del paziente."""
    c = (rec or {}).get("creato_il")
    if not c:
        return "non registrata", False
    alt = _data_alter(conn)
    try:
        if alt is not None and abs((c - alt).total_seconds()) < 60:
            return "non registrata (paziente inserito prima che il gestionale annotasse la data)", False
    except Exception:
        pass
    return _fmt(c, ora=True), True


def _fmt(v, ora=False):
    if v is None:
        return "—"
    if isinstance(v, dt.datetime):
        try:
            from zoneinfo import ZoneInfo
            if v.tzinfo:
                v = v.astimezone(ZoneInfo("Europe/Rome"))
        except Exception:
            pass
        return v.strftime("%d/%m/%Y %H:%M" if ora else "%d/%m/%Y")
    if hasattr(v, "strftime"):
        return v.strftime("%d/%m/%Y")
    return str(v)[:16]


def _colonne_tempo(conn):
    if "_reg_col_tempo" in st.session_state:
        return st.session_state["_reg_col_tempo"]
    righe = _q(conn,
        "SELECT table_name, column_name, data_type FROM information_schema.columns "
        "WHERE table_schema='public' AND (data_type LIKE 'timestamp%%' OR data_type='date')")
    per = {}
    for r in righe:
        per.setdefault(r["table_name"], []).append((r["column_name"], r["data_type"]))
    out = {}
    for t, cc in per.items():
        nomi = [c for c, _ in cc]
        ts = next((c for c in _TS_PREFERITE if c in nomi), None)
        d = next((c for c in _D_PREFERITE if c in nomi), None)
        out[t] = (ts, d)
    st.session_state["_reg_col_tempo"] = out
    return out


def cronologia(conn, paz_id, limite=300):
    """[{quando, chi, cosa, fonte}] dal piu' recente."""
    ev = []
    _tabella(conn)
    for r in _q(conn, "SELECT quando, utente, azione, dettaglio FROM registro_attivita WHERE paziente_id=%s "
                      "ORDER BY quando DESC LIMIT %s", (int(paz_id), limite)):
        ev.append({"quando": r["quando"], "chi": r.get("utente") or "", "fonte": "registro",
                   "cosa": r["azione"] + (f" — {r['dettaglio']}" if r.get("dettaglio") else "")})
    p = _q(conn, "SELECT creato_il FROM pazienti WHERE id=%s", (int(paz_id),))
    if p and p[0].get("creato_il"):
        _t, ok = data_registrazione(conn, p[0])
        if ok and not any(e["cosa"].startswith("Paziente creato") for e in ev):
            ev.append({"quando": p[0]["creato_il"], "chi": "", "fonte": "pazienti",
                       "cosa": "Paziente registrato in anagrafica"})
    try:
        from .fascicolo_paziente import riepilogo
        moduli = riepilogo(conn, paz_id)
    except Exception:
        moduli = []
    tempo = _colonne_tempo(conn)
    for m in moduli:
        t = m["tabella"]
        ts, d = tempo.get(t, (None, None))
        col = ts or d
        if not col:
            continue
        righe = _q(conn, f'SELECT * FROM "{t}" WHERE paziente_id=%s ORDER BY {col} DESC NULLS LAST LIMIT 40',
                   (int(paz_id),))
        for x in righe:
            q = x.get(ts) if ts else None
            if q is None and d:
                q = x.get(d)
            if q is None:
                continue
            chi = x.get("updated_by") or x.get("created_by") or x.get("creato_da") or x.get("aggiornato_da") or ""
            cosa = m["nome"]
            if ts and d and x.get(d) and x.get(ts) and hasattr(x.get(d), "strftime"):
                giorno = x[d].date() if isinstance(x[d], dt.datetime) else x[d]
                if giorno != (x[ts].date() if isinstance(x[ts], dt.datetime) else x[ts]):
                    cosa += f" (riferita al {_fmt(x[d])})"
            ev.append({"quando": q, "chi": str(chi), "cosa": cosa, "fonte": t})

    def chiave(e):
        q = e["quando"]
        if isinstance(q, dt.datetime):
            return q.replace(tzinfo=None) if q.tzinfo is None else q.astimezone(dt.timezone.utc).replace(tzinfo=None)
        if isinstance(q, dt.date):
            return dt.datetime(q.year, q.month, q.day)
        return dt.datetime.min
    ev.sort(key=chiave, reverse=True)
    return ev[:limite]


def _ha_ora(q):
    return isinstance(q, dt.datetime)


def render_cronologia(conn, paz_id):
    st.subheader("🕒 Cronologia")
    st.caption("Tutto quello che è successo, con data e ora: creazione, aperture della scheda, "
               "modifiche dell'anagrafica e ogni dato salvato nei moduli.")
    if conn is None:
        return
    vista = st.radio("Mostra", ["Questo paziente", "Tutti i pazienti (ultime attività)"],
                     horizontal=True, key="cron_vista")
    if vista.startswith("Tutti"):
        _tabella(conn)
        righe = _q(conn, "SELECT r.quando, r.utente, r.azione, r.dettaglio, p.cognome, p.nome, r.paziente_id "
                         "FROM registro_attivita r LEFT JOIN pazienti p ON p.id = r.paziente_id "
                         "ORDER BY r.quando DESC LIMIT 300")
        if not righe:
            st.info("Il registro è vuoto: si riempie da quando questo aggiornamento è attivo.")
        for r in righe:
            nome = f"{(r.get('cognome') or '').title()} {(r.get('nome') or '').title()}".strip() or f"ID {r.get('paziente_id')}"
            st.markdown(f"`{_fmt(r['quando'], ora=True)}` · **{nome}** · {r['azione']}"
                        + (f" — {r['dettaglio']}" if r.get("dettaglio") else "")
                        + (f" · _{r['utente']}_" if r.get("utente") else ""))
        return
    if not paz_id:
        st.info("Seleziona un paziente.")
        return
    rec = _q(conn, "SELECT cognome, nome, creato_il, ultimo_accesso FROM pazienti WHERE id=%s", (int(paz_id),))
    rec = rec[0] if rec else {}
    reg, ok = data_registrazione(conn, rec)
    _tabella(conn)
    aperture = _q(conn, "SELECT quando, utente FROM registro_attivita WHERE paziente_id=%s AND azione='Scheda aperta' "
                        "ORDER BY quando DESC LIMIT 2", (int(paz_id),))
    c1, c2, c3 = st.columns(3)
    c1.metric("Registrato il", reg if ok else "non registrata")
    if not ok:
        c1.caption(reg)
    c2.metric("Aperto l'ultima volta", _fmt(aperture[0]["quando"], ora=True) if aperture
              else _fmt(rec.get("ultimo_accesso"), ora=True))
    if aperture and aperture[0].get("utente"):
        c2.caption("da " + aperture[0]["utente"])
    c3.metric("Apertura precedente", _fmt(aperture[1]["quando"], ora=True) if len(aperture) > 1 else "—")

    ev = cronologia(conn, paz_id)
    if not ev:
        st.info("Ancora nessun evento.")
        return
    giorno = None
    for e in ev:
        q = e["quando"]
        g = _fmt(q)
        if g != giorno:
            st.markdown(f"#### {g}")
            giorno = g
        ora = _fmt(q, ora=True)[11:] if _ha_ora(q) else "—"
        st.markdown(f"`{ora}` · {e['cosa']}" + (f" · _{e['chi']}_" if e.get("chi") else ""))
