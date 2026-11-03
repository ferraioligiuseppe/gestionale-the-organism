# -*- coding: utf-8 -*-
"""
ui_brogliaccio.py — 📒 Brogliaccio dello studio.

Cinque viste, una sola schermata:
  ✍️ Annota       — un fatto in 10 secondi (telefonata, visita, relazione…)
  📌 Da fare      — i prossimi passi aperti, per persona, con le scadenze
  🔎 Cosa manca   — controlli automatici: appuntamenti senza traccia,
                    visite senza relazione, cose scadute
  🗓️ Giornata     — per un giorno: chi ha visto chi e chi ha lavorato su chi
  📖 Brogliaccio  — lo storico, con filtri

Si usa una scelta orizzontale invece delle schede di Streamlit: le schede
disegnano tutto ogni volta (anche la lettura dei calendari Google, lenta);
cosi' si calcola solo la vista aperta.
"""
from __future__ import annotations

import datetime as dt

import streamlit as st

from . import db_brogliaccio as db

VISTE = ["✍️ Annota", "📌 Da fare", "🔎 Cosa manca", "🗓️ Giornata", "📖 Brogliaccio"]
NESSUNO = "— nessun paziente / nuovo contatto —"


# ── Utilità ───────────────────────────────────────────────────────────
def _utente() -> str:
    try:
        from ..registro_attivita import nome_utente
        return nome_utente(st.session_state.get("username") or st.session_state.get("user") or "")
    except Exception:
        return str(st.session_state.get("username") or "")


def _professionisti():
    try:
        from ..agenda import PROFESSIONISTI
        return PROFESSIONISTI
    except Exception:
        return []


def _operatori(conn) -> list[str]:
    nomi = [p["nome"] for p in _professionisti() if p.get("nome")]
    for n in sorted(db.operatori_noti(conn)):
        if n not in nomi:
            nomi.append(n)
    if "Segreteria" not in nomi:
        nomi.append("Segreteria")
    return nomi


def _io(operatori: list[str]) -> str:
    """Il nome dell'operatore che corrisponde all'utente collegato."""
    u = (_utente() or "").strip()
    if not u:
        return operatori[0] if operatori else ""
    ul = u.lower()
    for n in operatori:
        if n.lower() == ul:
            return n
    for n in operatori:   # «giuseppe» → «Giuseppe Ferraioli»
        parti = n.lower().replace("'", " ").split()
        if ul in parti or any(p and p in ul for p in parti if len(p) > 3):
            return n
    operatori.append(u)
    return u


def _pazienti(conn):
    try:
        from ..paziente_attivo import _carica_lista_pazienti
        return _carica_lista_pazienti(conn) or []
    except Exception:
        return db._q(conn, "SELECT id, cognome, nome, data_nascita, telefono FROM pazienti "
                           "ORDER BY cognome, nome")


def _etichetta_paz(p) -> str:
    dn = str(p.get("data_nascita") or "")[:10]
    if len(dn) == 10 and dn[4] == "-":
        dn = f"{dn[8:10]}/{dn[5:7]}/{dn[:4]}"
    return f"{(p.get('cognome') or '').title()} {(p.get('nome') or '').title()}" + (f" · {dn}" if dn else "")


def _paz_attivo():
    try:
        from ..paziente_attivo import paziente_attivo_id
        return paziente_attivo_id()
    except Exception:
        return None


def _apri_paziente(conn, pid, voce="🕒 Cronologia"):
    try:
        from ..paziente_attivo import set_paziente_attivo
        from ..app_menu import AREA_PAZIENTI
        set_paziente_attivo(conn, int(pid))
        st.session_state["goto_area"] = AREA_PAZIENTI
        st.session_state["goto_sotto"] = voce
        st.rerun()
    except Exception as e:
        st.error(f"Non riesco ad aprire il paziente: {e}")


def _oggi() -> dt.date:
    return dt.datetime.now(db.TZ).date()


# ── Pagina ────────────────────────────────────────────────────────────
def render_brogliaccio(conn):
    st.header("📒 Brogliaccio dello studio")
    st.caption("Ogni telefonata, visita o relazione in una riga: **chi** l'ha fatto e "
               "**chi deve fare il passo dopo**. Così non ci si dimentica più niente.")
    if conn is None:
        st.error("Database non disponibile.")
        return
    if not st.session_state.get("_brogliaccio_ok"):
        if db.init_db(conn):
            st.session_state["_brogliaccio_ok"] = True
        else:
            st.error("Non riesco a creare la tabella del brogliaccio. Riprova tra qualche secondo.")
            return

    operatori = _operatori(conn)
    io = _io(operatori)

    # Riepilogo in alto: cose aperte per persona.
    conteggi = db.conta_aperti(conn)
    miei, miei_scad = conteggi.get(io, (0, 0))
    tot = sum(n for n, _ in conteggi.values())
    scad = sum(s for _, s in conteggi.values())
    c1, c2, c3 = st.columns(3)
    c1.metric(f"Da fare per te ({io.split()[0] if io else '—'})", miei,
              delta=f"{miei_scad} scadute" if miei_scad else None, delta_color="inverse")
    c2.metric("Da fare nello studio", tot)
    c3.metric("Scadute", scad, delta="da guardare" if scad else None, delta_color="inverse")

    vista = st.radio("Vista", VISTE, horizontal=True, key="brog_vista", label_visibility="collapsed")
    st.divider()
    if vista == VISTE[0]:
        _vista_annota(conn, operatori, io)
    elif vista == VISTE[1]:
        _vista_da_fare(conn, operatori, io)
    elif vista == VISTE[2]:
        _vista_cosa_manca(conn, operatori, io)
    elif vista == VISTE[3]:
        _vista_giornata(conn)
    else:
        _vista_storico(conn, operatori)


# ── ✍️ Annota ──────────────────────────────────────────────────────────
def _vista_annota(conn, operatori, io):
    if st.session_state.pop("_brog_salvato", None):
        st.success("Annotato ✔")

    pazienti = _pazienti(conn)
    opzioni = [NESSUNO] + [int(p["id"]) for p in pazienti]
    per_id = {int(p["id"]): p for p in pazienti}
    attivo = _paz_attivo()
    idx = opzioni.index(attivo) if attivo in per_id else 0

    tipo = st.selectbox("Cosa è successo", db.TIPI, key="brog_tipo")
    with st.form("brog_form", clear_on_submit=True):
        a1, a2 = st.columns([3, 2])
        pid = a1.selectbox("Paziente (scrivi per cercare)", opzioni, index=idx,
                           format_func=lambda x: x if x == NESSUNO else _etichetta_paz(per_id[x]))
        operatore = a2.selectbox("Chi l'ha fatto", operatori,
                                 index=operatori.index(io) if io in operatori else 0)
        b1, b2, b3 = st.columns([3, 2, 2])
        nominativo = b1.text_input("Nome (se non è in anagrafica)",
                                   placeholder="es. mamma di Luca Rossi, scuola Don Milani…")
        telefono = b2.text_input("Telefono")
        sede = b3.selectbox("Sede", [""] + db.SEDI)
        descrizione = st.text_area("Cosa (in breve)", height=80,
                                   placeholder="es. chiede info sullo screening visivo per il figlio di 7 anni")
        importo, pagamento, fattura = None, None, None
        if tipo in db.TIPI_CON_IMPORTO:
            st.markdown("**💶 Costo**")
            e1, e2, e3 = st.columns([2, 2, 2])
            importo = e1.number_input("Importo (€)", min_value=0.0, step=5.0, value=None, format="%.2f",
                                      placeholder="es. 30", key=f"brog_imp_{tipo}")
            pagamento = e2.selectbox("Come ha pagato", [""] + db.METODI, key=f"brog_pag_{tipo}")
            fattura = e3.selectbox("Fattura", [""] + db.FATTURA, key=f"brog_fat_{tipo}")
        st.markdown("**Prossimo passo** — lascia vuoto se non c'è niente da fare")
        c1, c2, c3 = st.columns([3, 2, 2])
        passo = c1.text_input("Cosa fare", value=db.PASSO_PROPOSTO.get(tipo, ""), key=f"brog_passo_{tipo}")
        a_chi = c2.selectbox("A chi tocca", operatori,
                             index=operatori.index(io) if io in operatori else 0)
        entro = c3.date_input("Entro", value=_oggi() + dt.timedelta(days=2), format="DD/MM/YYYY")
        with st.expander("Data e ora diverse da adesso (per annotare cose già successe)"):
            d1, d2 = st.columns(2)
            giorno = d1.date_input("Giorno", value=_oggi(), format="DD/MM/YYYY", key="brog_g")
            ora = d2.time_input("Ora", value=dt.datetime.now(db.TZ).time().replace(second=0, microsecond=0),
                                key="brog_o")
        ok = st.form_submit_button("💾 Annota", type="primary", use_container_width=True)

    if ok:
        if pid == NESSUNO and not nominativo.strip() and not descrizione.strip():
            st.warning("Scegli un paziente oppure scrivi almeno il nome o cosa è successo.")
            return
        if fattura == "Da fare" and not (passo or "").strip():
            passo = "Fare la fattura"
        quando = dt.datetime.combine(giorno, ora).replace(tzinfo=db.TZ)
        if abs((quando - dt.datetime.now(db.TZ)).total_seconds()) < 600:
            quando = None   # «adesso»: lo mette il database
        rid = db.aggiungi(conn, tipo=tipo, operatore=operatore, utente=_utente(),
                          paziente_id=None if pid == NESSUNO else pid,
                          nominativo=nominativo, telefono=telefono, sede=sede,
                          descrizione=descrizione, prossimo_passo=passo, assegnato_a=a_chi,
                          scadenza=entro, quando=quando,
                          rif_data=giorno if quando is not None else None,
                          importo=importo, pagamento=pagamento or None, fattura=fattura or None)
        if rid:
            st.session_state["_brog_salvato"] = True
            st.rerun()
        else:
            st.error("Salvataggio non riuscito. Riprova.")

    st.markdown("##### Ultime annotazioni di oggi")
    righe = [r for r in db.elenco(conn, giorni=1, limite=15)]
    if not righe:
        st.caption("Ancora niente oggi.")
    for r in righe:
        _riga(r)


# ── 📌 Da fare ─────────────────────────────────────────────────────────
def _vista_da_fare(conn, operatori, io):
    f1, f2 = st.columns([2, 3])
    solo_miei = f1.toggle("Solo le mie", value=True, key="brog_solomiei")
    chi = io if solo_miei else f2.selectbox("Di chi", ["tutti"] + operatori, key="brog_dichi")
    righe = db.da_fare(conn, None if chi == "tutti" else chi)
    if not righe:
        st.success("Niente in sospeso 🎉" if solo_miei else "Niente in sospeso.")
        return
    oggi = _oggi()
    gruppi = {}
    for r in righe:
        gruppi.setdefault(r.get("assegnato_a") or "—", []).append(r)
    for persona, elenco in gruppi.items():
        if not solo_miei:
            st.markdown(f"#### {persona} · {len(elenco)}")
        for r in elenco:
            sc = r.get("scadenza")
            if sc and sc < oggi:
                badge = f"🔴 scaduta il {db.fmt(sc)}"
            elif sc and sc == oggi:
                badge = "🟠 oggi"
            elif sc:
                badge = f"🟢 entro il {db.fmt(sc)}"
            else:
                badge = "⚪ senza scadenza"
            with st.container(border=True):
                t1, t2 = st.columns([5, 2])
                t1.markdown(f"**{r.get('prossimo_passo')}** — {db.nome_paziente(r)}  \n"
                            f"<small>{badge} · {r['tipo']} del {db.fmt(r['quando'], ora=True)} "
                            f"da {r.get('operatore') or '—'}</small>", unsafe_allow_html=True)
                if r.get("descrizione"):
                    t1.caption(r["descrizione"])
                if r.get("telefono"):
                    t1.caption(f"📞 {r['telefono']}")
                k = r["id"]
                esito = t2.text_input("Esito (facoltativo)", key=f"brog_es_{k}",
                                      label_visibility="collapsed", placeholder="esito…")
                if t2.button("✅ Fatto", key=f"brog_ok_{k}", use_container_width=True):
                    db.chiudi(conn, k, io, esito)
                    st.rerun()
                with t2.popover("↪️ Passa a…", use_container_width=True):
                    nuovo = st.selectbox("A chi", operatori, key=f"brog_ra_{k}")
                    nuova_sc = st.date_input("Entro", value=sc or oggi + dt.timedelta(days=2),
                                             format="DD/MM/YYYY", key=f"brog_rs_{k}")
                    if st.button("Passa", key=f"brog_rb_{k}"):
                        db.riassegna(conn, k, nuovo, nuova_sc)
                        st.rerun()
                if r.get("paziente_id") and t2.button("👤 Apri", key=f"brog_ap_{k}", use_container_width=True):
                    _apri_paziente(conn, r["paziente_id"])


# ── 🔎 Cosa manca ──────────────────────────────────────────────────────
def _vista_cosa_manca(conn, operatori, io):
    st.caption("Controlli automatici. Ogni voce si chiude annotando com'è andata.")
    giorni = st.select_slider("Guarda indietro di", options=[7, 14, 30, 60], value=14,
                              format_func=lambda g: f"{g} giorni", key="brog_cm_gg")
    oggi = _oggi()

    # 1. Appuntamenti passati senza nessuna traccia nel gestionale
    st.markdown("### 1 · Appuntamenti senza traccia")
    st.caption("Appuntamenti in agenda (Google) con un paziente riconosciuto, per cui quel giorno "
               "nel gestionale non risulta niente: né una scheda salvata, né una riga nel brogliaccio.")
    eventi, errori = [], []
    try:
        from ..agenda_sync import appuntamenti
        attivi = [p for p in _professionisti() if (p.get("cal_id") or "").strip()]
        with st.spinner("Leggo le agende…"):
            eventi, errori = appuntamenti(conn, attivi, oggi - dt.timedelta(days=giorni),
                                          oggi - dt.timedelta(days=1))
    except Exception as e:
        errori = [{"nome": "agenda", "motivo": str(e)}]
    for e in errori:
        st.caption(f"⚠️ Agenda di {e['nome']} non leggibile: {e['motivo']}")
    riconosciuti = [e for e in eventi if e.get("paziente") and e["paziente"].get("id")]
    non_ric = [e for e in eventi if not (e.get("paziente") and e["paziente"].get("id")) and not e.get("all_day")]
    tracce = db.pazienti_con_tracce(conn, sorted({e["data"] for e in riconosciuti}))
    senza = [e for e in riconosciuti if (int(e["paziente"]["id"]), e["data"]) not in tracce]
    if not senza:
        st.success("Tutti gli appuntamenti riconosciuti hanno una traccia. ✔")
    for i, e in enumerate(senza):
        p = e["paziente"]
        with st.container(border=True):
            a, b = st.columns([4, 3])
            a.markdown(f"**{p['cognome'].title()} {p['nome'].title()}** — "
                       f"{e['data'].strftime('%a %d/%m')} {e.get('ora') or ''} · {e['prof_nome']}")
            a.caption(e.get("titolo") or "")
            esito = b.radio("Com'è andata", ["Visita fatta", "Seduta fatta", "Non si è presentato",
                                             "Annullato / spostato"],
                            key=f"brog_cm_e_{i}", horizontal=False, label_visibility="collapsed")
            if b.button("💾 Annota", key=f"brog_cm_b_{i}"):
                tipo = {"Visita fatta": db.T_VISITA, "Seduta fatta": db.T_SEDUTA,
                        "Non si è presentato": db.T_ASSENTE}.get(esito, db.T_APP_MOD)
                passo = "Scrivere la relazione" if tipo == db.T_VISITA else (
                    "Richiamare per riprogrammare" if tipo in (db.T_ASSENTE, db.T_APP_MOD) else "")
                prof = e["prof_nome"]
                db.aggiungi(conn, tipo=tipo, operatore=prof, utente=_utente(), paziente_id=p["id"],
                            descrizione=f"Da agenda: {e.get('titolo') or ''} {e.get('ora') or ''}".strip(),
                            prossimo_passo=passo,
                            assegnato_a=prof if tipo == db.T_VISITA else "Segreteria",
                            scadenza=oggi + dt.timedelta(days=7 if tipo == db.T_VISITA else 1),
                            quando=dt.datetime.combine(e["data"], dt.time(12, 0)).replace(tzinfo=db.TZ),
                            rif_data=e["data"])
                st.rerun()
    if non_ric:
        with st.expander(f"⚠️ {len(non_ric)} appuntamenti con un paziente non riconosciuto"):
            st.caption("Il gestionale collega l'appuntamento al paziente se nel titolo dell'evento "
                       "c'è **Cognome Nome** come in anagrafica.")
            for e in non_ric[:100]:
                st.markdown(f"- {e['data'].strftime('%d/%m')} {e.get('ora') or ''} · {e['prof_nome']} · "
                            f"_{e.get('titolo') or '(senza titolo)'}_")

    # 2. Visite senza relazione
    st.markdown("### 2 · Visite senza relazione")
    st.caption("Pazienti con una visita o valutazione negli ultimi 90 giorni e nessuna relazione da allora.")
    mancanti = db.relazioni_mancanti(conn, giorni=90)
    if not mancanti:
        st.success("Nessuna relazione in sospeso. ✔")
    for m in mancanti:
        with st.container(border=True):
            a, b = st.columns([4, 3])
            gg = (dt.datetime.now(db.TZ) - (m["ultima_visita"] if isinstance(m["ultima_visita"], dt.datetime)
                  else dt.datetime.combine(m["ultima_visita"], dt.time()).replace(tzinfo=db.TZ))).days
            a.markdown(f"**{m['cognome'].title()} {m['nome'].title()}** — visita del "
                       f"{db.fmt(m['ultima_visita'])} ({gg} giorni fa)" + (f" · {m['chi']}" if m["chi"] else ""))
            k = m["paziente_id"]
            c1, c2, c3 = b.columns(3)
            if c1.button("✅ Consegnata", key=f"brog_rel_ok_{k}", use_container_width=True):
                db.aggiungi(conn, tipo=db.T_REL_OK, operatore=m["chi"] or _io(operatori),
                            utente=_utente(), paziente_id=k)
                st.rerun()
            if c2.button("➖ Non serve", key=f"brog_rel_no_{k}", use_container_width=True):
                db.aggiungi(conn, tipo=db.T_REL_NO, operatore=_io(operatori), utente=_utente(), paziente_id=k)
                st.rerun()
            if c3.button("📝 Scrivila", key=f"brog_rel_w_{k}", use_container_width=True):
                _apri_paziente(conn, k, "📚 Archivio relazioni")

    # 3. Cose scadute
    st.markdown("### 3 · Cose da fare scadute")
    scadute = [r for r in db.da_fare(conn) if r.get("scadenza") and r["scadenza"] < oggi]
    if not scadute:
        st.success("Nessuna scadenza superata. ✔")
    for r in scadute:
        st.markdown(f"- 🔴 **{r.get('prossimo_passo')}** — {db.nome_paziente(r)} · tocca a "
                    f"**{r.get('assegnato_a') or '—'}** · scaduta il {db.fmt(r['scadenza'])}")
    if scadute:
        st.caption("Si chiudono da «📌 Da fare».")


# ── 🗓️ Giornata ────────────────────────────────────────────────────────
def _vista_giornata(conn):
    giorno = st.date_input("Giorno", value=_oggi(), format="DD/MM/YYYY", key="brog_giorno")
    st.caption("Per ogni paziente di quel giorno: chi l'aveva in agenda, chi ha lavorato sulla sua "
               "scheda nel gestionale e cosa è stato annotato nel brogliaccio.")
    per_paz: dict = {}

    def _p(pid, cognome="", nome=""):
        d = per_paz.setdefault(pid, {"nome": f"{cognome.title()} {nome.title()}".strip(),
                                     "agenda": [], "gestionale": set(), "moduli": set(), "note": []})
        if not d["nome"] and (cognome or nome):
            d["nome"] = f"{cognome.title()} {nome.title()}".strip()
        return d

    try:
        from ..agenda_sync import appuntamenti
        attivi = [p for p in _professionisti() if (p.get("cal_id") or "").strip()]
        eventi, _err = appuntamenti(conn, attivi, giorno, giorno)
    except Exception:
        eventi = []
    altri = []
    for e in eventi:
        p = e.get("paziente")
        if p and p.get("id"):
            _p(int(p["id"]), p.get("cognome", ""), p.get("nome", ""))["agenda"].append(
                f"{e.get('ora') or ''} {e['prof_nome']}".strip())
        elif not e.get("all_day"):
            altri.append(e)

    for pid, t in db.tracce_del_giorno(conn, giorno).items():
        d = _p(pid)
        d["gestionale"] |= t["utenti"]
        d["moduli"] |= t["tabelle"]

    for r in db.del_giorno(conn, giorno):
        key = int(r["paziente_id"]) if r.get("paziente_id") else f"n{r['id']}"
        d = _p(key, r.get("cognome") or "", r.get("nome") or "")
        if not d["nome"]:
            d["nome"] = (r.get("nominativo") or "—")
        d["note"].append(f"{r['tipo']} · {r.get('operatore') or '—'}"
                         + (f" — {r['descrizione']}" if r.get("descrizione") else ""))

    _box_incassi(db.del_giorno(conn, giorno), f"💶 Incassi del {db.fmt(giorno)}")

    if not per_paz and not altri:
        st.info("Nessuna attività registrata per questo giorno.")
        return

    # Nomi mancanti (pazienti visti solo nel registro automatico)
    senza_nome = [k for k, v in per_paz.items() if isinstance(k, int) and not v["nome"]]
    if senza_nome:
        for r in db._q(conn, "SELECT id, cognome, nome FROM pazienti WHERE id = ANY(%s)", (senza_nome,)):
            per_paz[int(r["id"])]["nome"] = f"{(r['cognome'] or '').title()} {(r['nome'] or '').title()}".strip()

    try:
        from ..registro_attivita import _nome_tabella, nome_utente
    except Exception:
        _nome_tabella = lambda t: t  # noqa: E731
        nome_utente = str

    righe = []
    for k, v in sorted(per_paz.items(), key=lambda kv: kv[1]["nome"] or ""):
        righe.append({
            "Paziente": v["nome"] or "—",
            "In agenda con": ", ".join(v["agenda"]) or "—",
            "Scheda lavorata da": ", ".join(sorted(nome_utente(u) for u in v["gestionale"])) or "—",
            "Moduli": ", ".join(sorted(_nome_tabella(t) for t in v["moduli"])) or "—",
            "Brogliaccio": " | ".join(v["note"]) or "—",
            "⚠️": "senza traccia" if v["agenda"] and not v["gestionale"] and not v["note"] else "",
        })
    st.dataframe(righe, use_container_width=True, hide_index=True)
    if altri:
        with st.expander(f"{len(altri)} appuntamenti senza paziente riconosciuto"):
            for e in altri:
                st.markdown(f"- {e.get('ora') or ''} · {e['prof_nome']} · _{e.get('titolo') or ''}_")


# ── 📖 Brogliaccio (storico) ───────────────────────────────────────────
def _vista_storico(conn, operatori):
    f1, f2, f3, f4 = st.columns([2, 2, 3, 2])
    giorni = f1.selectbox("Periodo", [1, 7, 30, 90, 365], index=1, key="brog_st_gg",
                          format_func=lambda g: "oggi" if g == 1 else f"ultimi {g} giorni")
    chi = f2.selectbox("Chi", ["tutti"] + operatori, key="brog_st_chi")
    tipo = f3.selectbox("Tipo", ["tutti"] + db.TIPI, key="brog_st_tipo")
    attivo = _paz_attivo()
    solo_paz = f4.toggle("Solo paziente attivo", value=False, key="brog_st_paz", disabled=not attivo)
    cerca = st.text_input("Cerca (nome, telefono, testo)", key="brog_st_cerca")
    righe = db.elenco(conn, giorni=giorni, operatore=None if chi == "tutti" else chi,
                      tipo=None if tipo == "tutti" else tipo,
                      paziente_id=attivo if solo_paz else None, limite=1000)
    if cerca.strip():
        c = cerca.strip().lower()
        righe = [r for r in righe if c in " ".join(str(r.get(x) or "") for x in
                 ("cognome", "nome", "nominativo", "telefono", "descrizione", "prossimo_passo", "esito")).lower()]
    st.caption(f"{len(righe)} righe")
    if any(r.get("importo") is not None for r in righe):
        _box_incassi(righe, "💶 Importi delle righe qui sotto")
    if not righe:
        st.info("Nessuna annotazione con questi filtri.")
    for r in righe:
        _riga(r, conn=conn)


def _box_incassi(righe, titolo):
    t = db.riepilogo_importi(righe)
    if not t["n"] and not t["fatture_da_fare"]:
        return
    st.markdown(f"##### {titolo}")
    c = st.columns(5)
    c[0].metric("Incassato", db.euro(t["incassato"]))
    for i, m in enumerate(db.INCASSATI, start=1):
        c[i].metric(m, db.euro(t["per_metodo"][m]))
    c[4].metric("Da pagare", db.euro(t["da_pagare"]), delta=f"{t['n_da_pagare']} da incassare" if t["n_da_pagare"] else None,
                delta_color="inverse")
    if t["fatture_da_fare"]:
        st.caption(f"🧾 Fatture ancora da fare: **{t['fatture_da_fare']}**")


def _riga(r, conn=None):
    stato = {"aperto": "⏳", "fatto": "✔"}.get(r.get("stato"), "")
    testo = (f"`{db.fmt(r['quando'], ora=True)}` · {r['tipo']} · **{db.nome_paziente(r)}** · "
             f"_{r.get('operatore') or '—'}_")
    if r.get("descrizione"):
        testo += f" — {r['descrizione']}"
    if r.get("importo") is not None or r.get("pagamento") or r.get("fattura"):
        pezzi = [db.euro(r["importo"]) if r.get("importo") is not None else None, r.get("pagamento"),
                 f"fattura {r['fattura'].lower()}" if r.get("fattura") else None]
        testo += "  \n&nbsp;&nbsp;💶 " + " · ".join(p for p in pezzi if p)
    if r.get("prossimo_passo"):
        testo += f"  \n&nbsp;&nbsp;{stato} {r['prossimo_passo']} → **{r.get('assegnato_a') or '—'}**"
        if r.get("stato") == "fatto":
            testo += f" (fatto da {r.get('chiuso_da') or '—'} il {db.fmt(r.get('chiuso_il'), ora=True)}"
            testo += f": {r['esito']})" if r.get("esito") else ")"
        elif r.get("scadenza"):
            testo += f" entro il {db.fmt(r['scadenza'])}"
    if conn is None:
        st.markdown(testo)
        return
    a, b = st.columns([12, 1])
    a.markdown(testo)
    with b.popover("⋯"):
        if r.get("stato") == "fatto" and st.button("Riapri", key=f"brog_ri_{r['id']}"):
            db.riapri(conn, r["id"])
            st.rerun()
        if st.button("🗑️ Elimina", key=f"brog_del_{r['id']}"):
            db.elimina(conn, r["id"])
            st.rerun()
