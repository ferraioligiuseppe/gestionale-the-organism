# -*- coding: utf-8 -*-
"""Programma PNEV a casa: un solo link per la famiglia.

Riunisce i programmi gia' attivi del paziente nell'ordine PNEV:
  1 · Movimento  — TMR (tabella tmr_programmi)
  2 · Vista      — esercizi visivi (tabella vis_programmi)
  3 · Ascolto    — MAPS (indirizzo e minuti, salvati qui)
La famiglia apre una pagina sola, con un diario unico.
Il link non contiene dati del paziente.

Gli esercizi non si scelgono qui: si scelgono nelle voci TMR e
Stimolazione visiva a casa. Questa pagina li mette insieme.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import json
import secrets as _secrets
import urllib.parse
import urllib.request

import streamlit as st

PAGINA = "https://www.pnev.it/wp-content/uploads/pnev-casa/programma.html"
API = "https://www.pnev.it/wp-json/pnev/v1/diario"


def _segreto() -> str:
    try:
        return str((st.secrets.get("pnev_casa", {}) or {}).get("SECRET") or "")
    except Exception:
        return ""


def nuovo_token() -> str:
    """Token per il diario sul sito: 12 caratteri casuali + firma.
    Il sito (mu-plugin pnev-diario.php) accetta solo token firmati con la
    stessa chiave, cosi' nessuno puo' riempire il database con diari inventati."""
    s = _segreto()
    if not s:
        return ""
    alfabeto = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"
    ident = "".join(_secrets.choice(alfabeto) for _ in range(12))
    firma = hmac.new(s.encode(), ident.encode(), hashlib.sha256).hexdigest()[:16]
    return f"{ident}-{firma}"


@st.cache_data(ttl=120, show_spinner=False)
def leggi_diario(token: str):
    if not token:
        return None, "nessun token"
    try:
        req = urllib.request.Request(API + "?k=" + urllib.parse.quote(token),
                                     headers={"User-Agent": "TheOrganism/1.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            d = json.loads(r.read().decode("utf-8")).get("diario") or {}
        return (d if isinstance(d, dict) else {}), ""
    except Exception as e:
        return None, str(e)


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
        return ""
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        return str(e)


def _tabella(conn):
    if st.session_state.get("_casa_ok"):
        return
    if not _esegui(conn,
        "CREATE TABLE IF NOT EXISTS pnev_casa ("
        " paziente_id INTEGER PRIMARY KEY, maps_url TEXT, maps_min INTEGER, maps_nota TEXT,"
        " volte INTEGER, giorni INTEGER, settimane INTEGER, nota TEXT, link TEXT,"
        " aggiornato_il TIMESTAMP DEFAULT NOW())"):
        _esegui(conn, "ALTER TABLE pnev_casa ADD COLUMN IF NOT EXISTS token TEXT")
        st.session_state["_casa_ok"] = True


def _json(v, d):
    try:
        return json.loads(v) if isinstance(v, str) else (v if v is not None else d)
    except Exception:
        return d


def render_programma_casa(conn, paz_id):
    st.subheader("🏠 Programma PNEV a casa")
    st.caption("Un solo link per la famiglia: movimento, poi vista, poi ascolto, con un diario unico. "
               "Gli esercizi si scelgono nelle voci «🎵 TMR» e «👁️ Stimolazione visiva a casa».")
    if conn is None or not paz_id:
        st.info("Seleziona un paziente.")
        return
    _tabella(conn)
    tmr = (_q(conn, "SELECT * FROM tmr_programmi WHERE paziente_id=%s AND attivo ORDER BY id DESC LIMIT 1",
              (int(paz_id),)) or [None])[0]
    vis = (_q(conn, "SELECT * FROM vis_programmi WHERE paziente_id=%s AND attivo ORDER BY id DESC LIMIT 1",
              (int(paz_id),)) or [None])[0]
    casa = (_q(conn, "SELECT * FROM pnev_casa WHERE paziente_id=%s", (int(paz_id),)) or [{}])[0]
    t_es = _json((tmr or {}).get("esercizi"), [])
    v_es = _json((vis or {}).get("esercizi"), [])
    v_imp = _json((vis or {}).get("impostazioni"), {})

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**1 · Movimento (TMR)**")
        if t_es:
            st.markdown(", ".join(f"{x['codice']}{x.get('variante') or ''} ×{x['cicli']}" for x in t_es))
        else:
            st.caption("Nessun programma TMR attivo.")
    with c2:
        st.markdown("**2 · Vista**")
        if v_es:
            st.markdown(", ".join(f"{x['codice']} {x['minuti']}′" for x in v_es)
                        + f" · livello {v_imp.get('livello', 1)}"
                        + (f" · filtro {v_imp['filtro']}" if v_imp.get("filtro") else ""))
        else:
            st.caption("Nessun programma visivo attivo.")

    st.markdown("**3 · Ascolto (MAPS)**")
    k = f"casa_{paz_id}"
    a, b = st.columns([3, 1])
    murl = a.text_input("Indirizzo del programma di ascolto del paziente", casa.get("maps_url") or "",
                        key=f"{k}_mu", placeholder="https://www.pnev.it/... (il link MAPS che usi già)")
    mmin = b.number_input("Minuti", 0, 90, int(casa.get("maps_min") or 0), key=f"{k}_mm",
                          help="0 = nessun ascolto in questo programma")
    mnota = st.text_input("Indicazioni per l'ascolto (facoltative)", casa.get("maps_nota") or "", key=f"{k}_mn",
                          placeholder="es. cuffie consegnate in studio, volume basso, mai prima di dormire")

    d1, d2, d3 = st.columns(3)
    volte = d1.number_input("Volte al giorno", 1, 3, int(casa.get("volte") or (tmr or {}).get("volte_giorno") or 1), key=f"{k}_v")
    giorni = d2.number_input("Giorni a settimana", 1, 7, int(casa.get("giorni") or (tmr or {}).get("giorni_settimana") or 5), key=f"{k}_g")
    sett = d3.number_input("Settimane", 1, 26, int(casa.get("settimane") or (tmr or {}).get("settimane") or 4), key=f"{k}_s")
    nota = st.text_area("Nota per la famiglia (facoltativa)", casa.get("nota") or "", key=f"{k}_n", height=70)

    vuoto = not t_es and not v_es and not (murl.strip() or mmin)
    if st.button("💾 Crea il link unico", type="primary", key=f"{k}_salva", disabled=vuoto):
        q = {}
        if t_es:
            q["t"] = ",".join(f"{x['codice']}{x.get('variante') or ''}.{int(x['cicli'])}" for x in t_es)
        if v_es:
            q["e"] = ",".join(f"{x['codice']}.{int(x['minuti'])}" for x in v_es)
            q["l"] = v_imp.get("livello") or 1
            if v_imp.get("filtro"):
                q["f"] = v_imp["filtro"]
            if any(x["codice"] == "V9" for x in v_es):
                q["c"] = v_imp.get("colore") or "verde"
            if any(x["codice"] == "V10" for x in v_es):
                q["b"] = v_imp.get("bpm") or 60
            if v_imp.get("numeri"):
                q["t2"] = "n"
        if murl.strip():
            q["mu"] = murl.strip()
        if mmin:
            q["mm"] = int(mmin)
        if mnota.strip():
            q["mn"] = mnota.strip()[:200]
        q.update({"v": int(volte), "g": int(giorni), "s": int(sett)})
        # Il token resta lo stesso per il paziente anche se rifai il link:
        # il diario continua senza ripartire da zero.
        token = casa.get("token") or nuovo_token()
        if token:
            q["k"] = token
        if nota.strip():
            q["n"] = nota.strip()[:300]
        link = PAGINA + "?" + urllib.parse.urlencode(q, quote_via=urllib.parse.quote, safe=",.")
        err = _esegui(conn,
            "INSERT INTO pnev_casa (paziente_id, maps_url, maps_min, maps_nota, volte, giorni, settimane, nota, link, token, aggiornato_il) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW()) ON CONFLICT (paziente_id) DO UPDATE SET "
            "maps_url=EXCLUDED.maps_url, maps_min=EXCLUDED.maps_min, maps_nota=EXCLUDED.maps_nota, volte=EXCLUDED.volte, "
            "giorni=EXCLUDED.giorni, settimane=EXCLUDED.settimane, nota=EXCLUDED.nota, link=EXCLUDED.link, "
            "token=COALESCE(pnev_casa.token, EXCLUDED.token), aggiornato_il=NOW()",
            (int(paz_id), murl.strip(), int(mmin), mnota.strip(), int(volte), int(giorni), int(sett), nota.strip(), link,
             token or None))
        if err:
            st.error(f"Non salvato: {err}")
        else:
            st.success("Link creato.")
            st.rerun()
    if vuoto:
        st.caption("Serve almeno un programma attivo (TMR o vista) oppure l'ascolto.")

    link = casa.get("link")
    if link:
        st.markdown("---")
        st.markdown("**🔗 Il link per la famiglia**")
        st.code(link, language=None)
        x, y, z = st.columns(3)
        x.link_button("Apri / prova", link, use_container_width=True)
        msg = urllib.parse.quote("Ecco il programma da fare a casa, tutto in una pagina: " + link)
        y.link_button("WhatsApp", f"https://wa.me/?text={msg}", use_container_width=True)
        mail = z.text_input("Email", key=f"{k}_mail", label_visibility="collapsed", placeholder="email")
        if z.button("📧 Invia", key=f"{k}_inv", use_container_width=True):
            try:
                from modules.email_otp import invia_email
                ok, mot = invia_email(mail.strip(), "Il programma PNEV a casa — Studio The Organism",
                                      "Gentile famiglia,\n\nqui trovate tutto il programma da fare a casa, in una sola pagina:\n\n"
                                      + link + "\n\nStudio The Organism · www.pnev.it", dettaglio=True)
                (st.success if ok else st.error)(mot)
            except Exception as e:
                st.error(f"Email non disponibile: {e}")
        st.caption("Se cambi gli esercizi in TMR o in Stimolazione visiva, torna qui e premi di nuovo "
                   "«Crea il link unico»: il link vecchio mostra ancora il programma di prima. "
                   "Il diario invece continua: è legato al paziente, non al link.")
        if not casa.get("token"):
            st.warning("Diario solo sul dispositivo della famiglia: manca [pnev_casa] SECRET nei Secrets "
                       "oppure il link è stato creato prima. Aggiungi la chiave e ricrea il link.")
        else:
            _diario(casa["token"], t_es, v_es, mmin)


def _diario(token, t_es, v_es, mmin):
    st.markdown("---")
    st.markdown("**📓 Diario della famiglia** · lo stesso su ogni dispositivo")
    d, err = leggi_diario(token)
    if d is None:
        st.caption(f"Diario non raggiungibile ({err}). Controlla che pnev-diario.php sia in wp-content/mu-plugins/.")
        return
    fasi = []
    if t_es:
        fasi.append(("Movimento", lambda g: bool(g.get("mov"))))
    if v_es:
        codici = [x["codice"].lower() for x in v_es]
        fasi.append(("Vista", lambda g, c=codici: all(k in g for k in c)))
    if mmin:
        fasi.append(("Ascolto", lambda g: bool(g.get("asc"))))
    oggi = dt.date.today()
    giorni = [oggi - dt.timedelta(days=i) for i in range(13, -1, -1)]
    righe = []
    for nome, fatto in fasi:
        riga = {"Fase": nome}
        for g in giorni:
            riga[g.strftime("%d/%m")] = "✓" if fatto(d.get(g.isoformat(), {})) else ""
        righe.append(riga)
    if righe:
        st.dataframe(righe, hide_index=True, use_container_width=True)
    completi = sum(1 for g in giorni if fasi and all(f(d.get(g.isoformat(), {})) for _n, f in fasi))
    st.caption(f"Giorni con tutto il programma fatto, ultime due settimane: {completi} su 14.")
    risultati = []
    for g in sorted(d)[-14:]:
        r = [f"{k.upper()}: {v}" for k, v in (d[g] or {}).items() if k.startswith("v") and isinstance(v, str) and v]
        if r:
            risultati.append(f"- {g[8:]}/{g[5:7]} · " + " · ".join(r))
    if risultati:
        with st.expander("Risultati degli esercizi visivi"):
            st.markdown("\n".join(risultati))
    if st.button("🔄 Aggiorna il diario", key=f"dia_{token[:6]}"):
        leggi_diario.clear()
        st.rerun()
