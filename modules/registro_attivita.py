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
        "CREATE INDEX IF NOT EXISTS registro_attivita_quando ON registro_attivita (quando DESC);"
        "ALTER TABLE registro_attivita ADD COLUMN IF NOT EXISTS tabella TEXT;"
        "ALTER TABLE registro_attivita ADD COLUMN IF NOT EXISTS operazione TEXT;"
        "ALTER TABLE registro_attivita ADD COLUMN IF NOT EXISTS riga_id TEXT;"):
        st.session_state["_reg_att_ok"] = True


# ── Tracciamento automatico di ogni modulo ─────────────────────────────
# Su ogni tabella clinica (quelle con paziente_id) e su pazienti si mette un
# trigger: ogni INSERT, UPDATE o DELETE scrive una riga in registro_attivita
# con chi l'ha fatto (app.utente, impostato da app_core prima di ogni
# scrittura), la tabella, la riga e — per le modifiche — i campi cambiati.
# Il trigger non puo' mai bloccare un salvataggio: se il registro fallisce,
# il salvataggio va avanti lo stesso.

_NON_TRACCIARE = ("registro_attivita", "schede_aperte", "_storico", "storico_", "_log", "log_", "token",
                  "otp", "cache", "portale_accessi", "magic_links", "registrazioni_ip", "samples",
                  "_points", "captures", "presenza")
_CAMPI_TECNICI = {"updated_at", "aggiornato_il", "updated_by", "aggiornato_da", "ultimo_accesso",
                  "created_at", "creato_il", "created_by", "creato_da"}
_ULTIMO_CONTROLLO = {"t": 0.0}


def _tabelle_da_tracciare(conn):
    righe = _q(conn,
        "SELECT c.table_name, c.column_name, c.data_type FROM information_schema.columns c "
        "JOIN information_schema.tables t ON t.table_name=c.table_name AND t.table_schema=c.table_schema "
        "WHERE c.table_schema='public' AND t.table_type='BASE TABLE' AND c.table_name IN ("
        " SELECT table_name FROM information_schema.columns WHERE table_schema='public' "
        " AND column_name='paziente_id' UNION SELECT 'pazienti')")
    out = {}
    for x in righe:
        out.setdefault(x["table_name"], []).append((x["column_name"], x["data_type"]))
    return {t: c for t, c in out.items() if not any(p in t for p in _NON_TRACCIARE)}


def _sql_trigger(t, colonne):
    nomi = {c for c, _ in colonne}
    pid = "id" if t == "pazienti" else "paziente_id"
    rid = "r.id::text" if "id" in nomi else "NULL"
    confronto = [c for c, ty in colonne if ty != "bytea" and c not in _CAMPI_TECNICI]
    cambi = ", ".join(f"CASE WHEN NEW.\"{c}\" IS DISTINCT FROM OLD.\"{c}\" THEN '{c}' END" for c in confronto)
    fn = ("pnev_traccia_" + t)[:60]
    cambi_sql = cambi or "NULL"
    return f"""
CREATE OR REPLACE FUNCTION "{fn}"() RETURNS trigger LANGUAGE plpgsql AS $f$
DECLARE r RECORD; campi TEXT := '';
BEGIN
  IF TG_OP = 'DELETE' THEN r := OLD; ELSE r := NEW; END IF;
  IF TG_OP = 'UPDATE' THEN
    campi := array_to_string(ARRAY[{cambi_sql}]::text[], ', ');
    IF coalesce(campi, '') = '' THEN RETURN NULL; END IF;
  END IF;
  BEGIN
    INSERT INTO registro_attivita (paziente_id, utente, azione, dettaglio, tabella, operazione, riga_id)
    VALUES (NULLIF(r.{pid}::text, '')::bigint, NULLIF(current_setting('app.utente', true), ''),
            TG_OP, coalesce(campi, ''), TG_TABLE_NAME, TG_OP, {rid});
  EXCEPTION WHEN others THEN NULL;
  END;
  RETURN NULL;
END $f$;
DROP TRIGGER IF EXISTS pnev_traccia ON "{t}";
CREATE TRIGGER pnev_traccia AFTER INSERT OR UPDATE OR DELETE ON "{t}"
  FOR EACH ROW EXECUTE PROCEDURE "{fn}"();
"""


def assicura_tracciamento(conn, forza=False):
    """Mette il trigger sulle tabelle che non l'hanno ancora. Controlla al
    massimo ogni 6 ore, cosi' un modulo nuovo viene coperto da solo."""
    import time
    if conn is None or (not forza and time.time() - _ULTIMO_CONTROLLO["t"] < 6 * 3600):
        return []
    _ULTIMO_CONTROLLO["t"] = time.time()
    _tabella(conn)
    gia = {x["t"] for x in _q(conn, "SELECT c.relname AS t FROM pg_trigger g JOIN pg_class c ON c.oid=g.tgrelid "
                                     "WHERE g.tgname='pnev_traccia'")}
    fatte = []
    for t, cols in _tabelle_da_tracciare(conn).items():
        if t in gia and not forza:
            continue
        if _esegui(conn, _sql_trigger(t, cols)):
            fatte.append(t)
    return fatte


def stato_tracciamento(conn):
    tutte = _tabelle_da_tracciare(conn)
    gia = {x["t"] for x in _q(conn, "SELECT c.relname AS t FROM pg_trigger g JOIN pg_class c ON c.oid=g.tgrelid "
                                     "WHERE g.tgname='pnev_traccia'")}
    return sorted(tutte), gia


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
    for r in _q(conn, "SELECT quando, utente, azione, dettaglio, tabella, operazione, riga_id FROM registro_attivita "
                      "WHERE paziente_id=%s ORDER BY quando DESC LIMIT %s", (int(paz_id), limite)):
        ev.append({"quando": r["quando"], "chi": r.get("utente") or "", "fonte": r.get("tabella") or "registro",
                   "cosa": descrivi(r), "riga": r.get("riga_id"), "op": r.get("operazione")})
    inizio = _q(conn, "SELECT MIN(quando) AS t FROM registro_attivita WHERE tabella IS NOT NULL")
    inizio = inizio[0]["t"] if inizio and inizio[0].get("t") else None
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
            # Da quando c'e' il tracciamento, questi eventi sono gia' nel registro.
            if inizio is not None and isinstance(q, dt.datetime) and ts:
                try:
                    if q >= inizio:
                        continue
                except TypeError:
                    pass
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


_OP = {"INSERT": "nuovo", "UPDATE": "modificato", "DELETE": "eliminato"}


def _nome_tabella(t):
    try:
        from .fascicolo_paziente import ETICHETTE
        if t in ETICHETTE:
            return ETICHETTE[t][0]
    except Exception:
        pass
    if t == "pazienti":
        return "Anagrafica"
    return (t or "").replace("_", " ").capitalize()


def descrivi(r):
    t = r.get("tabella")
    if not t:
        return (r.get("azione") or "") + (f" — {r['dettaglio']}" if r.get("dettaglio") else "")
    op = _OP.get(r.get("operazione"), (r.get("operazione") or "").lower())
    testo = f"{_nome_tabella(t)} · {op}"
    if r.get("operazione") == "UPDATE" and r.get("dettaglio"):
        testo += f" ({r['dettaglio']})"
    return testo


def _compatta(ev):
    """Salvataggi ripetuti dello stesso utente sulla stessa scheda entro 15
    minuti diventano una riga sola, con il numero di volte."""
    out = []
    for e in ev:
        p = out[-1] if out else None
        if (p and e.get("op") == "UPDATE" and p.get("op") == "UPDATE" and e.get("fonte") == p.get("fonte")
                and e.get("riga") == p.get("riga") and e.get("chi") == p.get("chi")
                and isinstance(e["quando"], dt.datetime) and isinstance(p["quando"], dt.datetime)
                and abs((p["quando"] - e["quando"]).total_seconds()) < 900):
            p["n"] = p.get("n", 1) + 1
            continue
        out.append(dict(e))
    return out


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
        utenti = [x["u"] for x in _q(conn, "SELECT DISTINCT utente AS u FROM registro_attivita "
                                           "WHERE utente IS NOT NULL AND utente<>'' ORDER BY 1")]
        f1, f2, f3 = st.columns(3)
        chi = f1.selectbox("Chi", ["tutti"] + utenti, key="cron_chi")
        giorni = f2.selectbox("Periodo", [1, 7, 30, 90], index=1, key="cron_gg",
                              format_func=lambda g: "oggi" if g == 1 else f"ultimi {g} giorni")
        cerca = f3.text_input("Modulo o paziente contiene", key="cron_cerca")
        sql = ("SELECT r.quando, r.utente, r.azione, r.dettaglio, r.tabella, r.operazione, r.riga_id, "
               "p.cognome, p.nome, r.paziente_id FROM registro_attivita r LEFT JOIN pazienti p ON p.id = r.paziente_id "
               "WHERE r.quando > NOW() - (%s || ' days')::interval")
        par = [str(giorni)]
        if chi != "tutti":
            sql += " AND r.utente=%s"
            par.append(chi)
        righe = _q(conn, sql + " ORDER BY r.quando DESC LIMIT 1000", tuple(par))
        if cerca.strip():
            c = cerca.strip().lower()
            righe = [x for x in righe if c in (descrivi(x) + " " + (x.get("cognome") or "") + " " +
                                               (x.get("nome") or "")).lower()]
        st.caption(f"{len(righe)} attività.")
        if not righe:
            st.info("Nessuna attività in questo periodo.")
        for x in righe[:500]:
            nome = f"{(x.get('cognome') or '').title()} {(x.get('nome') or '').title()}".strip() \
                or (f"ID {x['paziente_id']}" if x.get("paziente_id") else "—")
            st.markdown(f"`{_fmt(x['quando'], ora=True)}` · **{nome}** · {descrivi(x)}"
                        + (f" · _{x['utente']}_" if x.get("utente") else " · _utente non registrato_"))
        with st.expander("🛡️ Tracciamento dei moduli"):
            tutte, gia = stato_tracciamento(conn)
            mancano = [t for t in tutte if t not in gia]
            st.caption(f"Moduli tracciati: {len(tutte) - len(mancano)} su {len(tutte)}.")
            if mancano:
                st.caption("Non ancora tracciati: " + ", ".join(mancano))
            if st.button("Attiva su tutti i moduli adesso", key="cron_attiva"):
                fatte = assicura_tracciamento(conn, forza=True)
                st.success(f"Tracciamento attivo su {len(fatte)} tabelle.")
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

    ev = _compatta(cronologia(conn, paz_id))
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
        st.markdown(f"`{ora}` · {e['cosa']}" + (f" ×{e['n']}" if e.get("n") else "")
                    + (f" · _{e['chi']}_" if e.get("chi") else ""))
