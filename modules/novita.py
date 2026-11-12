# -*- coding: utf-8 -*-
"""Novita': tutto cio' che ARRIVA nel gestionale da fuori, in un posto solo.

Perche' esiste
--------------
Questionari, iscrizioni e contatti entrano da soli (link, QR, sito) e
finivano ognuno nella sua pagina: non c'era modo di accorgersi che era
arrivato qualcosa, ne' di capire da dove veniva e dove andare a vederlo.

Cosa raccoglie (ogni fonte e' indipendente: se una tabella manca, le altre funzionano)
  · questionari dal link aperto / QR      questionari_arrivo
  · questionari dal link personale        questionari_links (completati)
  · iscrizioni agli eventi                ev_iscrizioni
  · contatti dal sito pnev.it             lead_sito
  · questionari compilati sul sito        questionari_pubblici

Ogni voce dice: quando, cosa, di chi, DA DOVE arriva e DOVE si apre.
«Nuovo» vuol dire arrivato dopo l'ultima volta che l'utente ha premuto
«Segna tutto come visto» (tabella novita_viste, una riga per utente).
"""
from __future__ import annotations

import datetime as dt

import streamlit as st

GIORNI = 14
VALIDITA_SECONDI = 60


def _q(conn, sql, par=()):
    try:
        cur = conn.cursor()
        cur.execute(sql, par)
        r = cur.fetchall() or []
        if r and not isinstance(r[0], dict):
            n = [c[0] for c in cur.description]
            r = [dict(zip(n, x)) for x in r]
        return [dict(x) for x in r]
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return []


def _esegui(conn, sql, par=()) -> bool:
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


def _utc(v):
    """datetime con fuso UTC da datetime/testo; None se non leggibile."""
    if not v:
        return None
    try:
        d = dt.datetime.fromisoformat(v.replace("Z", "+00:00")) if isinstance(v, str) else v
        if not isinstance(d, dt.datetime):
            d = dt.datetime.combine(d, dt.time())
        if d.tzinfo is None:
            d = d.replace(tzinfo=dt.timezone.utc)
        return d.astimezone(dt.timezone.utc)
    except Exception:
        return None


def _ora_italiana(d) -> str:
    try:
        from zoneinfo import ZoneInfo
        return d.astimezone(ZoneInfo("Europe/Rome")).strftime("%d/%m %H:%M")
    except Exception:
        return d.strftime("%d/%m %H:%M")


def _nome_questionario(codice) -> str:
    try:
        from .ui_questionari import _Q_LABELS
        n = _Q_LABELS.get(codice, "")
        n = n.split(" ", 1)[1] if n and not n[0].isalnum() else n
        n = n or str(codice or "").replace("_", " ").title()
    except Exception:
        n = str(codice or "").replace("_", " ").title()
    return n[len("Questionario "):] if n.startswith("Questionario ") else n


def _utente() -> str:
    return str(st.session_state.get("username") or st.session_state.get("user") or "utente")


def _visto_il(conn):
    _esegui(conn, "CREATE TABLE IF NOT EXISTS novita_viste "
                  "(utente TEXT PRIMARY KEY, visto_il TIMESTAMPTZ NOT NULL DEFAULT now())")
    r = _q(conn, "SELECT visto_il FROM novita_viste WHERE utente=%s", (_utente(),))
    return _utc(r[0].get("visto_il")) if r else None


def segna_viste(conn) -> None:
    _esegui(conn, "INSERT INTO novita_viste (utente, visto_il) VALUES (%s, now()) "
                  "ON CONFLICT (utente) DO UPDATE SET visto_il = now()", (_utente(),))
    st.session_state.pop("_novita_cache", None)


def _raccogli(conn) -> list[dict]:
    """Tutti gli arrivi degli ultimi GIORNI giorni, dal piu' recente."""
    da = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=GIORNI)
    out = []

    def nomi_pazienti(ids):
        ids = sorted({int(i) for i in ids if i is not None})
        if not ids:
            return {}
        r = _q(conn, "SELECT id, Cognome, Nome FROM Pazienti WHERE id = ANY(%s)", (ids,))
        m = {}
        for x in r:
            v = {k.lower(): val for k, val in x.items()}
            m[int(v["id"])] = f"{v.get('cognome') or ''} {v.get('nome') or ''}".strip()
        return m

    # 1) link aperto / QR
    arr = _q(conn, "SELECT questionario, anagrafica, paziente_id, stato, creato_il FROM questionari_arrivo "
                   "WHERE creato_il >= %s AND stato <> 'scartato' ORDER BY creato_il DESC LIMIT 60", (da,))
    # 2) link personale
    lk = _q(conn, "SELECT questionario, paziente_id, used_at FROM questionari_links "
                  "WHERE used_at IS NOT NULL ORDER BY id DESC LIMIT 80")
    nomi = nomi_pazienti([x.get("paziente_id") for x in arr] + [x.get("paziente_id") for x in lk])

    for x in arr:
        q = _utc(x.get("creato_il"))
        if not q:
            continue
        an = x.get("anagrafica") or {}
        if isinstance(an, str):
            try:
                import json
                an = json.loads(an)
            except Exception:
                an = {}
        chi = nomi.get(x.get("paziente_id")) or f"{an.get('cognome', '')} {an.get('nome', '')}".strip() or "senza nome"
        da_verificare = (x.get("stato") == "da_verificare") or not x.get("paziente_id")
        out.append({
            "quando": q, "icona": "📋", "cosa": f"Questionario {_nome_questionario(x.get('questionario'))}",
            "chi": chi, "da_dove": "compilato da un link aperto (QR)",
            "dove": ("va verificato: non è ancora collegato a un paziente" if da_verificare
                     else "già nella scheda del paziente"),
            "area": "📋 Questionari",
            "voce": "🔗 Link aperti e arrivi" if da_verificare else "📋 Questionari remoti",
            "paziente_id": None if da_verificare else x.get("paziente_id"),
        })
    for x in lk:
        q = _utc(x.get("used_at"))
        if not q or q < da:
            continue
        out.append({
            "quando": q, "icona": "📋", "cosa": f"Questionario {_nome_questionario(x.get('questionario'))}",
            "chi": nomi.get(x.get("paziente_id")) or "paziente", "da_dove": "compilato dal link personale che hai inviato",
            "dove": "già nella scheda del paziente", "area": "📋 Questionari", "voce": "📋 Questionari remoti",
            "paziente_id": x.get("paziente_id"),
        })

    # 3) iscrizioni agli eventi
    for x in _q(conn, "SELECT i.nome, i.cognome, i.stato, i.created_at, e.titolo FROM ev_iscrizioni i "
                      "JOIN ev_eventi e ON e.id = i.evento_id ORDER BY i.id DESC LIMIT 80"):
        q = _utc(x.get("created_at"))
        if not q or q < da:
            continue
        out.append({
            "quando": q, "icona": "🎟️", "cosa": f"Iscrizione a «{(x.get('titolo') or 'evento')[:60]}»",
            "chi": f"{x.get('cognome') or ''} {x.get('nome') or ''}".strip(),
            "da_dove": "dalla pagina pubblica dell'evento",
            "dove": "nell'elenco iscritti dell'evento" + (" (lista d'attesa)" if x.get("stato") == "lista_attesa" else ""),
            "area": None, "voce": "📅 Eventi e iscrizioni", "paziente_id": None,
        })

    # 4) contatti dal sito
    for x in _q(conn, "SELECT nome, cognome, src_gioco, stato, creato_il FROM lead_sito "
                      "WHERE creato_il >= %s ORDER BY creato_il DESC LIMIT 60", (da,)):
        q = _utc(x.get("creato_il"))
        if not q:
            continue
        out.append({
            "quando": q, "icona": "📨", "cosa": "Nuovo contatto dal sito",
            "chi": f"{x.get('cognome') or ''} {x.get('nome') or ''}".strip() or "senza nome",
            "da_dove": "da pnev.it" + (f" (gioco: {x['src_gioco']})" if x.get("src_gioco") else ""),
            "dove": "tra i contatti dal sito, da richiamare", "area": "👥 Pazienti",
            "voce": "📨 Contatti dal sito", "paziente_id": None,
        })

    # 5) questionari compilati sul sito
    for x in _q(conn, "SELECT tipo, nome, esito, creato_il FROM questionari_pubblici "
                      "WHERE creato_il >= %s ORDER BY creato_il DESC LIMIT 60", (da,)):
        q = _utc(x.get("creato_il"))
        if not q:
            continue
        out.append({
            "quando": q, "icona": "🌐", "cosa": f"Questionario del sito ({x.get('tipo') or 'pubblico'})",
            "chi": x.get("nome") or "senza nome", "da_dove": "compilato su pnev.it",
            "dove": "tra i questionari dal sito", "area": "👥 Pazienti",
            "voce": "📋 Questionari dal sito", "paziente_id": None,
        })

    out.sort(key=lambda v: v["quando"], reverse=True)
    return out


def novita(conn, forza=False) -> tuple[list, int]:
    """(tutti gli arrivi recenti, quanti sono nuovi). In cache per un minuto."""
    import time
    c = st.session_state.get("_novita_cache")
    if not forza and c and (time.time() - c["t"]) < VALIDITA_SECONDI:
        return c["voci"], c["n"]
    visto = _visto_il(conn)
    voci = _raccogli(conn)
    for v in voci:
        v["nuovo"] = visto is None or v["quando"] > visto
    n = sum(1 for v in voci if v["nuovo"])
    st.session_state["_novita_cache"] = {"t": time.time(), "voci": voci, "n": n}
    return voci, n


def _vai(v):
    area = v.get("area")
    if not area:
        try:
            from .fascicolo_paziente import _area_di
            area = _area_di(v["voce"])
        except Exception:
            area = None
    if not area:
        return
    st.session_state["goto_area"] = area
    st.session_state["goto_sotto"] = v["voce"]
    if v.get("paziente_id"):
        st.session_state["paziente_attivo_id"] = int(v["paziente_id"])
    st.rerun()


def _riga(v, chiave):
    a, b = st.columns([6, 1])
    a.markdown(f"{'🆕 ' if v.get('nuovo') else ''}{v['icona']} **{v['cosa']}** · {v['chi']}  \n"
               f"<span style='font-size:.85rem;color:#55606e'>{_ora_italiana(v['quando'])} · "
               f"arriva {v['da_dove']} · {v['dove']}</span>", unsafe_allow_html=True)
    if b.button("Apri", key=chiave, use_container_width=True):
        _vai(v)


def render_novita(conn, chiave="nov") -> None:
    """Il riquadro delle novità (in cima a «Oggi in studio»)."""
    if conn is None:
        return
    voci, n = novita(conn)
    with st.container(border=True):
        c1, c2, c3 = st.columns([4, 1.6, 1])
        c1.markdown(f"**🔔 Novità** · " + (f"{n} da vedere" if n else "niente di nuovo")
                    + f" · ultimi {GIORNI} giorni")
        if n and c2.button("Segna tutto come visto", key=f"{chiave}_visto", use_container_width=True):
            segna_viste(conn)
            st.rerun()
        if c3.button("Aggiorna", key=f"{chiave}_agg", use_container_width=True):
            novita(conn, forza=True)
            st.rerun()
        nuove = [v for v in voci if v["nuovo"]]
        viste = [v for v in voci if not v["nuovo"]]
        if not voci:
            st.caption("Negli ultimi giorni non è arrivato nulla da link, QR, eventi o sito.")
        for i, v in enumerate(nuove[:30]):
            _riga(v, f"{chiave}_n{i}")
        if viste:
            with st.expander(f"Già viste ({len(viste)})", expanded=False):
                for i, v in enumerate(viste[:40]):
                    _riga(v, f"{chiave}_v{i}")


def bottone_sidebar(conn) -> None:
    """In cima al menu, in ogni pagina: quante novità ci sono e un clic per vederle."""
    if conn is None:
        return
    try:
        _voci, n = novita(conn)
    except Exception:
        return
    etichetta = f"🔔 Novità ({n})" if n else "🔔 Novità"
    if st.sidebar.button(etichetta, key="novita_sidebar", use_container_width=True,
                         type="primary" if n else "secondary"):
        try:
            from .fascicolo_paziente import _area_di
            area = _area_di("📒 Oggi in studio")
        except Exception:
            area = None
        if area:
            st.session_state["goto_area"] = area
            st.session_state["goto_sotto"] = "📒 Oggi in studio"
            st.rerun()
