# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════╗
║  QUADRO STORICO — vista unica del paziente (Mattone 3)               ║
║                                                                      ║
║  Raccoglie in un'unica schermata tutto ciò che il gestionale sa del  ║
║  paziente, pronto sotto gli occhi quando si scrive la nuova visita:  ║
║    • Documenti clinici caricati + estrazioni AI                      ║
║    • Test visivi/funzionali salvati (DEM, Getman, Groffman, …)       ║
║    • Valutazioni PNEV / anamnesi                                     ║
║                                                                      ║
║  È la base del Mattone 4 (diagnosi assistita): da qui si potrà       ║
║  generare la bozza di diagnosi sullo storico.                        ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import streamlit as st


def _query(conn, sql, params=()):
    """Esegue una SELECT e ritorna lista di dict (None se tabella assente/errore)."""
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return None


def _data_di(d: dict):
    for k in ("data", "data_valutazione", "data_anamnesi", "creato", "created_at"):
        if d.get(k):
            return d[k]
    return None


def _fmt(dt):
    try:
        return dt.strftime("%d/%m/%Y")
    except Exception:
        return str(dt) if dt else ""


def carica_paziente(conn, paz_id):
    """Carica il record del paziente e lo normalizza con le chiavi
    Cognome / Nome / Data_Nascita (robusto a maiuscole/minuscole di colonna).
    Usa prima il paziente attivo in sessione, poi il database."""
    base = None
    try:
        rec = st.session_state.get("paziente_attivo_record")
        if isinstance(rec, dict) and str(rec.get("id")) == str(paz_id):
            base = rec
    except Exception:
        base = None
    if base is None:
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM pazienti WHERE id=%s", (paz_id,))
            row = cur.fetchone()
            if not row:
                return None
            cols = [d[0] for d in cur.description]
            base = dict(zip(cols, row))
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            return None

    def g(*nomi):
        for n in nomi:
            for k, v in base.items():
                if str(k).lower() == n:
                    return v
        return ""

    return {
        "Cognome": g("cognome", "surname"),
        "Nome": g("nome", "name"),
        "Data_Nascita": g("data_nascita", "datanascita", "nascita", "data di nascita"),
    }


def render_quadro(conn=None, paz_id=None, paziente=None):
    st.header("🧩 Quadro storico del paziente")
    st.caption("Tutto lo storico in un colpo d'occhio: documenti, test, valutazioni. "
               "Pronto per scrivere la nuova diagnosi.")

    if conn is None or not paz_id:
        st.info("Seleziona prima un paziente.")
        return

    if not isinstance(paziente, dict) or not (paziente.get("Cognome") or paziente.get("Nome")):
        p = carica_paziente(conn, paz_id)
        if p:
            paziente = p

    nome = ""
    if isinstance(paziente, dict):
        nome = f"{paziente.get('Cognome','')} {paziente.get('Nome','')}".strip()
    if nome:
        st.markdown(f"### {nome}")

    trovato = False

    # ── Documenti clinici + estrazioni AI ─────────────────────────────
    docs = _query(conn, "SELECT * FROM documenti_clinici WHERE paziente_id=%s", (paz_id,))
    if docs:
        trovato = True
        docs.sort(key=lambda d: str(_data_di(d)), reverse=True)
        st.markdown(f"#### 📎 Documenti clinici ({len(docs)})")
        for d in docs:
            tipo = d.get("tipo") or "Documento"
            nomef = d.get("nome_file") or ""
            st.markdown(f"**{tipo}** — {nomef}  ·  _{_fmt(_data_di(d))}_")
            estr = d.get("estratto")
            if estr:
                with st.expander("🤖 Dati estratti dall'AI"):
                    st.markdown(estr)
        st.markdown("---")

    # ── Test funzionali salvati ───────────────────────────────────────
    blocchi = []

    g = _query(conn, "SELECT * FROM getman_risultati WHERE paziente_id=%s", (paz_id,))
    if g:
        for r in sorted(g, key=lambda x: str(_data_di(x)), reverse=True):
            blocchi.append(("👁️ Getman (manipolazione visiva)",
                            f"Punteggio {r.get('punteggio','?')}/12"
                            + (f" · classe {r.get('classe')}" if r.get('classe') else "")
                            + f"  ·  _{_fmt(_data_di(r))}_"))

    gr = _query(conn, "SELECT * FROM groffman_risultati WHERE paziente_id=%s", (paz_id,))
    if gr:
        for r in sorted(gr, key=lambda x: str(_data_di(x)), reverse=True):
            extra = []
            if r.get("forma"):
                extra.append(f"tavola {r['forma']}")
            if r.get("eta"):
                extra.append(f"{r['eta']} anni")
            blocchi.append(("👁️ Groffman (visual tracing)",
                            f"Punteggio {r.get('punteggio','?')}"
                            + (" · " + " · ".join(extra) if extra else "")
                            + f"  ·  _{_fmt(_data_di(r))}_"))

    dem = _query(conn, "SELECT * FROM dem_risultati WHERE paziente_id=%s", (paz_id,))
    if dem:
        for r in sorted(dem, key=lambda x: str(_data_di(x)), reverse=True):
            blocchi.append(("🔢 DEM",
                            "Risultato registrato  ·  _" + _fmt(_data_di(r)) + "_"))

    if blocchi:
        trovato = True
        st.markdown("#### 👁️ Test funzionali")
        for titolo, riga in blocchi:
            st.markdown(f"- **{titolo}** — {riga}")
        st.markdown("---")

    # ── Valutazioni visuo-percettive ──────────────────────────────────
    vv = _query(conn, "SELECT * FROM valutazioni_visive WHERE paziente_id=%s", (paz_id,))
    if vv:
        trovato = True
        vv.sort(key=lambda d: str(_data_di(d)), reverse=True)
        st.markdown(f"#### 👁️ Valutazioni visuo-percettive ({len(vv)})")
        for r in vv:
            st.markdown(f"- Valutazione del _{_fmt(_data_di(r))}_")
        st.markdown("---")

    # ── Valutazioni PNEV / anamnesi ───────────────────────────────────
    an = _query(conn, "SELECT * FROM anamnesi WHERE paziente_id=%s", (paz_id,))
    if an:
        trovato = True
        an.sort(key=lambda d: str(_data_di(d)), reverse=True)
        st.markdown(f"#### 📋 Valutazioni PNEV / Anamnesi ({len(an)})")
        for r in an:
            riassunto = (r.get("pnev_summary") or r.get("Motivo") or "").strip()
            riga = f"- _{_fmt(_data_di(r))}_"
            if riassunto:
                riga += f": {riassunto[:160]}" + ("…" if len(riassunto) > 160 else "")
            st.markdown(riga)
        st.markdown("---")

    # ── Logopedia / SMOF ──────────────────────────────────────────────
    lo = _query(conn, "SELECT * FROM logopedia_valutazioni WHERE paziente_id=%s", (paz_id,))
    if lo:
        trovato = True
        lo.sort(key=lambda d: str(_data_di(d)), reverse=True)
        st.markdown(f"#### 🗣️ Logopedia / SMOF ({len(lo)})")
        for r in lo:
            riga = f"- _{_fmt(_data_di(r))}_"
            if r.get("sintesi"):
                riga += f": {r['sintesi']}"
            st.markdown(riga)
        st.markdown("---")

    # ── Esiti / Follow-up ─────────────────────────────────────────────
    es = _query(conn, "SELECT * FROM esiti_pnev WHERE paziente_id=%s", (paz_id,))
    if es:
        trovato = True
        es.sort(key=lambda d: str(_data_di(d)), reverse=True)
        st.markdown(f"#### 📈 Esiti / Follow-up ({len(es)})")
        for r in es:
            riga = f"- **{r.get('esito','')}** — {r.get('intervento','')}  ·  _{_fmt(_data_di(r))}_"
            st.markdown(riga)
            if r.get("note"):
                st.caption(r["note"])
        st.markdown("---")

    if not trovato:
        st.info("Nessuno storico ancora presente per questo paziente "
                "(documenti, test o valutazioni).")
