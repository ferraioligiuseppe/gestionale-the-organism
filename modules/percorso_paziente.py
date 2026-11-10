# -*- coding: utf-8 -*-
"""Il percorso del paziente in sette passi, dalla telefonata ai follow-up.

  1 Telefonata              riga «telefonata» in Oggi in studio
  2 WhatsApp                riga «WhatsApp / email» in Oggi in studio
  3 Appuntamento in agenda  riga «appuntamento fissato» (+ evento su Google Calendar)
  4 Primo colloquio gratuito  colloquio clinico di tipo «Primo colloquio»
  5 Prima visita            anamnesi, questionari, test per l'eta' del paziente
  6 Terapia                 programma o sedute
  7 Follow-up               a 10, 20, 30 e 40 settimane dalla prima seduta

Le due viste si parlano: i primi tre passi SI LEGGONO da «Oggi in studio»
(modules/brogliaccio) e da qui SI SCRIVONO li', cosi' la scheda del paziente
dice «a che punto e' questa persona» e Oggi in studio «cosa c'e' da fare».

Diagnosi e relazione non sono passi obbligati: restano raggiungibili da
«Altri strumenti» sotto il percorso.

Niente tabelle nuove: tutto e' dedotto da cio' che i moduli salvano gia'.
"""
from __future__ import annotations

import datetime as dt
import urllib.parse

import streamlit as st

SETTIMANE_FOLLOWUP = (10, 20, 30, 40)
VOCE_SCHEDA, AREA_SCHEDA = "🏠 Dashboard", "👥 Pazienti"
VOCE_OGGI = "📒 Oggi in studio"
TIPO_PRIMO_COLLOQUIO = "Primo colloquio (anamnestico)"

# voce di menu → tabelle che provano che quella parte e' stata fatta
TABELLE = {
    "📋 Anamnesi PNEV": ("anamnesi_prima_infanzia", "anamnesi_sviluppo"),
    "📋 Questionari remoti": ("questionari_links", "questionari_arrivo"),
    "🧸 Screening 0-4 anni": ("screening_04",),
    "🎧 Screening uditivo": ("screening_uditivo_pnev", "screening_cuffie_pnev"),
    "🧬 Profilo Neuro-Evolutivo": ("inpp_valutazioni",),
    "👁️ Valutazione visuo-percettiva": ("valutazioni_visive",),
    "📊 Audiometria funzionale": ("audiometrie_tonali", "functional_audiograms"),
    "📚 DSA — Apprendimento": ("dsa_valutazioni",),
    "🧩 Programma PNEV": ("terapia_programma", "terapia_sedute", "pnev_casa", "tmr_programmi",
                          "vis_programmi", "piani_vt"),
}


# ── Lettura ────────────────────────────────────────────────────────
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


def _area(voce):
    try:
        from .fascicolo_paziente import _area_di
        return _area_di(voce)
    except Exception:
        return None


def _giorno(v):
    """date da date/datetime/testo; None se non leggibile."""
    if v is None:
        return None
    if isinstance(v, dt.datetime):
        if v.tzinfo is not None:
            try:
                from zoneinfo import ZoneInfo
                v = v.astimezone(ZoneInfo("Europe/Rome"))
            except Exception:
                pass
        return v.date()
    if isinstance(v, dt.date):
        return v
    try:
        return dt.date.fromisoformat(str(v)[:10])
    except Exception:
        return None


def _f(d) -> str:
    d = _giorno(d)
    return d.strftime("%d/%m/%Y") if d else ""


def date_followup(inizio) -> list:
    """Le quattro date dei follow-up, a 10/20/30/40 settimane dall'inizio della terapia."""
    inizio = _giorno(inizio)
    return [(s, inizio + dt.timedelta(weeks=s)) for s in SETTIMANE_FOLLOWUP] if inizio else []


def stato(conn, paz_id) -> list[dict]:
    """I sette passi: [{n, nome, icona, fatto, dettaglio, parti, azione, voce, area}].
    fatto: True / False. parti: [{nome, voce, area, fatto}] per i passi composti."""
    paz_id = int(paz_id)
    try:
        from .brogliaccio import db_brogliaccio as ob
        righe_ob = _q(conn, "SELECT tipo, quando, descrizione, prossimo_passo, scadenza, stato "
                            "FROM brogliaccio WHERE paziente_id=%s ORDER BY quando", (paz_id,))
        T_TEL, T_MSG, T_APP = {ob.T_TEL_IN, ob.T_TEL_OUT}, {ob.T_MSG}, {ob.T_APP}
    except Exception:
        righe_ob, T_TEL, T_MSG, T_APP = [], set(), set(), set()

    def prima(tipi):
        return next((r for r in righe_ob if r.get("tipo") in tipi), None)

    try:
        from .fascicolo_paziente import riepilogo
        presenti = {r["tabella"] for r in riepilogo(conn, paz_id)}
    except Exception:
        presenti = set()
    try:
        from .filtro_eta import eta_paziente_attivo, percorso_valutazione
        valut = [p for p in percorso_valutazione(eta_paziente_attivo()) if p[2] != "📝 Diagnosi assistita"]
    except Exception:
        valut = []

    tel, msg, app = prima(T_TEL), prima(T_MSG), prima(T_APP)
    coll = _q(conn, "SELECT data FROM colloqui_clinici WHERE paziente_id=%s AND tipo=%s "
                    "ORDER BY data LIMIT 1", (paz_id, TIPO_PRIMO_COLLOQUIO))
    sed = _q(conn, "SELECT MIN(data_seduta) AS inizio, COUNT(*) AS n FROM terapia_sedute "
                   "WHERE paziente_id=%s", (paz_id,))
    inizio = _giorno(sed[0].get("inizio")) if sed else None
    n_sedute = int((sed[0].get("n") if sed else 0) or 0)
    n_esiti = 0
    if inizio:
        es = _q(conn, "SELECT COUNT(*) AS n FROM esiti_pnev WHERE paziente_id=%s AND data >= %s",
                (paz_id, inizio))
        n_esiti = int((es[0].get("n") if es else 0) or 0)

    def parte(nome, voce, area=None):
        tab = TABELLE.get(voce)
        return {"nome": nome, "voce": voce, "area": area or _area(voce),
                "fatto": (any(t in presenti for t in tab) if tab else None)}

    parti_visita = [parte("Anamnesi", "📋 Anamnesi PNEV"), parte("Questionari", "📋 Questionari remoti")]
    for nome, area, voce in valut:
        if voce not in [p["voce"] for p in parti_visita]:
            parti_visita.append(parte(nome, voce, area))
    parti_visita = [p for p in parti_visita if p["area"]]
    noti = [p["fatto"] for p in parti_visita if p["fatto"] is not None]

    fu = date_followup(inizio)
    parti_fu = [{"nome": f"{s} settimane · {_f(d)}", "voce": "📈 Esiti / Follow-up",
                 "area": _area("📈 Esiti / Follow-up"), "fatto": i < n_esiti, "data": d}
                for i, (s, d) in enumerate(fu)]

    terapia_fatta = any(t in presenti for t in TABELLE["🧩 Programma PNEV"])
    passi = [
        {"nome": "Telefonata", "icona": "📞", "fatto": bool(tel), "azione": "telefonata",
         "dettaglio": f"Registrata il {_f(tel['quando'])}" if tel else "Registrare chi ha chiamato e perché"},
        {"nome": "WhatsApp", "icona": "💬", "fatto": bool(msg), "azione": "whatsapp",
         "dettaglio": f"Inviato il {_f(msg['quando'])}" if msg else "Messaggio di conferma già scritto: basta inviarlo"},
        {"nome": "Appuntamento in agenda", "icona": "📅", "fatto": bool(app), "azione": "appuntamento",
         "dettaglio": (app.get("descrizione") or f"Fissato il {_f(app['quando'])}") if app
         else "Fissare il primo colloquio"},
        {"nome": "Primo colloquio gratuito", "icona": "🗣️", "fatto": bool(coll),
         "voce": "🎙️ Colloqui clinici", "area": _area("🎙️ Colloqui clinici"),
         "dettaglio": f"Fatto il {_f(coll[0].get('data'))}" if coll else "Registri o scrivi: si salva da solo"},
        {"nome": "Prima visita", "icona": "🩺", "fatto": bool(noti) and all(noti), "parti": parti_visita,
         "dettaglio": "Anamnesi, questionari e test"},
        {"nome": "Terapia", "icona": "🧘", "fatto": terapia_fatta,
         "voce": "🧩 Programma PNEV", "area": _area("🧩 Programma PNEV"),
         "dettaglio": (f"Iniziata il {_f(inizio)} · {n_sedute} sedut{'a' if n_sedute == 1 else 'e'}" if inizio
                       else ("Programma impostato, nessuna seduta registrata" if terapia_fatta
                             else "Programma e sedute"))},
        {"nome": "Follow-up", "icona": "📈", "fatto": bool(fu) and n_esiti >= len(fu), "parti": parti_fu,
         "voce": "📈 Esiti / Follow-up", "area": _area("📈 Esiti / Follow-up"), "inizio": inizio,
         "dettaglio": ("A 10, 20, 30 e 40 settimane dalla prima seduta" if fu
                       else "Le date si calcolano dalla prima seduta di terapia registrata")},
    ]
    # Pazienti già seguiti prima che esistesse il percorso: se c'è la prova di
    # un passo successivo, quelli iniziali si considerano fatti (altrimenti
    # ogni paziente in terapia risulterebbe fermo alla telefonata).
    clinico = (terapia_fatta or n_sedute > 0
               or any(x["fatto"] for x in parti_visita if x["voce"] != "📋 Questionari remoti"))
    fino_a = 4 if clinico else (3 if coll else 0)
    for p in passi[:fino_a]:
        if not p["fatto"]:
            p["fatto"] = True
            p["dettaglio"] = "Già fatto (risulta un passo successivo)"
    for i, p in enumerate(passi):
        p["n"] = i + 1
        p.setdefault("parti", [])
        p.setdefault("azione", None)
        p.setdefault("voce", None)
        p.setdefault("area", None)
    return passi


def _attuale(passi):
    return next((p for p in passi if not p["fatto"]), None)


def _destinazione(p):
    """(area, voce, nome) dove andare per fare questo passo, o None se si fa qui."""
    if p["parti"]:
        da_fare = next((x for x in p["parti"] if x["fatto"] is False and x["area"]), None)
        if da_fare:
            return da_fare["area"], da_fare["voce"], da_fare["nome"]
    if p["voce"] and p["area"]:
        return p["area"], p["voce"], p["nome"]
    return None


def _vai(area, voce, paz_id):
    st.session_state["goto_area"] = area
    st.session_state["goto_sotto"] = voce
    st.session_state["paziente_attivo_id"] = paz_id
    st.rerun()


# ── Scrittura in «Oggi in studio» ─────────────────────────────────────
def _io(conn) -> str:
    try:
        from .brogliaccio.ui_brogliaccio import _operatori, _io as _chi
        return _chi(_operatori(conn))
    except Exception:
        return str(st.session_state.get("username") or st.session_state.get("user") or "")


def _annota(conn, paz_id, tipo, descrizione, prossimo_passo="", scadenza=None):
    """Scrive una riga in Oggi in studio. Ritorna True se riuscito."""
    try:
        from .brogliaccio import db_brogliaccio as ob
        ob.init_db(conn)
        io = _io(conn)
        rid = ob.aggiungi(conn, tipo=tipo, operatore=io,
                          utente=str(st.session_state.get("username") or st.session_state.get("user") or ""),
                          paziente_id=paz_id, descrizione=descrizione, prossimo_passo=prossimo_passo,
                          assegnato_a=io if prossimo_passo else "", scadenza=scadenza)
        st.session_state.pop(f"_fascicolo_quando_{paz_id}", None)
        return bool(rid)
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False


def _paziente():
    try:
        from .paziente_attivo import paziente_attivo_record
        return paziente_attivo_record() or {}
    except Exception:
        return {}


def _numero_whatsapp(tel) -> str:
    c = "".join(ch for ch in str(tel or "") if ch.isdigit())
    if not c:
        return ""
    if c.startswith("00"):
        c = c[2:]
    if c.startswith("3") and len(c) in (9, 10):      # cellulare italiano senza prefisso
        c = "39" + c
    return c


def _azione_telefonata(conn, paz_id, k):
    nota = st.text_input("Chi ha chiamato e perché", key=f"{k}_tel_nota",
                         placeholder="es. la mamma, difficoltà di lettura segnalate dalla scuola")
    if st.button("📞 Registra la telefonata", key=f"{k}_tel_ok", type="primary"):
        if not nota.strip():
            st.error("Scrivi due parole sulla telefonata.")
            return
        try:
            from .brogliaccio import db_brogliaccio as ob
            tipo = ob.T_TEL_IN
        except Exception:
            st.error("«Oggi in studio» non è disponibile.")
            return
        if _annota(conn, paz_id, tipo, nota.strip()):
            st.rerun()
        else:
            st.error("Non sono riuscito a scriverla in «Oggi in studio».")


def _azione_whatsapp(conn, paz_id, k):
    rec = _paziente()
    nome = f"{rec.get('nome') or rec.get('Nome') or ''}".strip()
    num = _numero_whatsapp(rec.get("telefono") or rec.get("Telefono") or rec.get("cellulare"))
    testo = st.text_area("Messaggio", key=f"{k}_wa_testo", height=110, value=(
        "Buongiorno, qui è lo Studio The Organism. Le confermiamo il primo colloquio gratuito"
        + (f" per {nome}" if nome else "") + ". A breve le comunichiamo giorno e orario. "
        "Per qualsiasi necessità può rispondere a questo messaggio."))
    c1, c2 = st.columns(2)
    if num:
        c1.link_button("💬 Apri WhatsApp con il messaggio",
                       f"https://wa.me/{num}?text={urllib.parse.quote(testo, safe='')}",
                       use_container_width=True)
    else:
        c1.warning("Nella scheda manca il numero di telefono: aggiungilo dall'anagrafica.")
    if c2.button("✅ Segna come inviato", key=f"{k}_wa_ok", use_container_width=True):
        try:
            from .brogliaccio import db_brogliaccio as ob
            tipo = ob.T_MSG
        except Exception:
            st.error("«Oggi in studio» non è disponibile.")
            return
        if _annota(conn, paz_id, tipo, "WhatsApp di conferma del primo colloquio"):
            st.rerun()
        else:
            st.error("Non sono riuscito a scriverlo in «Oggi in studio».")
    st.caption("WhatsApp si apre con il testo già scritto: l'invio lo premi tu. Poi torna qui e segna «inviato».")


def _azione_appuntamento(conn, paz_id, k):
    try:
        from .agenda import PROFESSIONISTI
        prof = [p for p in PROFESSIONISTI if (p.get("cal_id") or "").strip()]
    except Exception:
        prof = []
    rec = _paziente()
    nome = f"{rec.get('cognome') or rec.get('Cognome') or ''} {rec.get('nome') or rec.get('Nome') or ''}".strip()
    c1, c2, c3 = st.columns([2, 1, 1])
    giorno = c1.date_input("Giorno", dt.date.today() + dt.timedelta(days=1), key=f"{k}_app_g", format="DD/MM/YYYY")
    ora = c2.time_input("Ora", dt.time(16, 0), key=f"{k}_app_o", step=900)
    durata = c3.number_input("Minuti", 15, 180, 45, 15, key=f"{k}_app_d")
    con = st.selectbox("Con", [p["nome"] for p in prof] or ["—"], key=f"{k}_app_c") if prof else None
    cal_id = next((p["cal_id"] for p in prof if p["nome"] == con), None) if prof else None
    if st.button("📅 Fissa l'appuntamento", key=f"{k}_app_ok", type="primary"):
        inizio = dt.datetime.combine(giorno, ora)
        scritto = False
        if cal_id:
            try:
                from .eventi.google_calendar import crea_evento_calendario
                scritto = bool(crea_evento_calendario(f"Primo colloquio · {nome}", inizio, int(durata),
                                                      "Primo colloquio gratuito (creato dal gestionale)",
                                                      calendar_id=cal_id))
            except Exception:
                scritto = False
        descr = (f"Primo colloquio gratuito il {giorno.strftime('%d/%m/%Y')} alle {ora.strftime('%H:%M')}"
                 + (f" con {con}" if con else "")
                 + (" · scritto su Google Calendar" if scritto else " · DA SCRIVERE A MANO su Google Calendar"))
        try:
            from .brogliaccio import db_brogliaccio as ob
            tipo = ob.T_APP
        except Exception:
            st.error("«Oggi in studio» non è disponibile.")
            return
        if _annota(conn, paz_id, tipo, descr):
            st.session_state[f"{k}_app_esito"] = scritto
            st.rerun()
        else:
            st.error("Non sono riuscito a scriverlo in «Oggi in studio».")
    st.caption("Il gestionale prova a scrivere l'appuntamento sul calendario Google del professionista. "
               "Se non ci riesce lo segna comunque qui, e ti avvisa di metterlo in calendario a mano.")


def _azione_followup(conn, paz_id, passo, k):
    """Mette i follow-up non ancora presenti tra le cose da fare di Oggi in studio."""
    futuri = [x for x in passo["parti"] if not x["fatto"]]
    if not futuri:
        return
    gia = {r.get("prossimo_passo") for r in _q(
        conn, "SELECT prossimo_passo FROM brogliaccio WHERE paziente_id=%s "
              "AND prossimo_passo LIKE %s", (int(paz_id), "Follow-up a % settimane"))}
    mancano = [x for x in futuri if f"Follow-up a {x['nome'].split(' ')[0]} settimane" not in gia]
    if not mancano:
        st.caption("📌 I follow-up sono già tra le cose da fare di «Oggi in studio».")
        return
    if st.button(f"📌 Metti {len(mancano)} follow-up tra le cose da fare di «Oggi in studio»", key=f"{k}_fu"):
        try:
            from .brogliaccio import db_brogliaccio as ob
            tipo = ob.T_NOTA
        except Exception:
            st.error("«Oggi in studio» non è disponibile.")
            return
        ok = 0
        for x in mancano:
            sett = x["nome"].split(" ")[0]
            ok += bool(_annota(conn, paz_id, tipo, f"Controllo a {sett} settimane dall'inizio della terapia",
                               prossimo_passo=f"Follow-up a {sett} settimane", scadenza=x["data"]))
        (st.rerun() if ok == len(mancano) else st.error("Non tutti i follow-up sono stati scritti: riprova."))


# ── Disegno ───────────────────────────────────────────────────────
def render_percorso(conn, paz_id, chiave="perc") -> None:
    """Nella scheda del paziente: i sette passi in colonna, con l'azione del passo attuale."""
    if conn is None or not paz_id:
        return
    passi = stato(conn, paz_id)
    att = _attuale(passi)
    k = f"{chiave}_{paz_id}"
    with st.container(border=True):
        fatti = sum(1 for p in passi if p["fatto"])
        st.markdown(f"**A che punto siamo** · {fatti} passi fatti su {len(passi)}")
        if st.session_state.pop(f"{k}_app_esito", None) is False:
            st.warning("Appuntamento segnato in «Oggi in studio», ma NON scritto su Google Calendar: "
                       "mettilo in calendario a mano. Per farlo scrivere al gestionale serve collegare "
                       "i calendari (te lo spiega Claude).")
        for p in passi:
            qui = p is att
            segno = "✅" if p["fatto"] else ("▶️" if qui else "⚪")
            riga = f"{segno} **{p['n']} · {p['nome']}**" + (" — _sei qui_" if qui else "")
            st.markdown(riga)
            det = p["dettaglio"]
            if p["parti"]:
                det += " · " + " · ".join(
                    ("✓ " if x["fatto"] else ("" if x["fatto"] is None else "○ ")) + x["nome"] for x in p["parti"])
            st.caption(det)
            if not qui:
                continue
            if p["azione"] == "telefonata":
                _azione_telefonata(conn, paz_id, k)
            elif p["azione"] == "whatsapp":
                _azione_whatsapp(conn, paz_id, k)
            elif p["azione"] == "appuntamento":
                _azione_appuntamento(conn, paz_id, k)
            else:
                dest = _destinazione(p)
                if dest and st.button(f"▶ Prossimo passo: {dest[2]}", key=f"{k}_prox",
                                      type="primary", use_container_width=True):
                    _vai(dest[0], dest[1], paz_id)
            if p["n"] <= 3:
                if st.button("Salta questo passo (già fatto fuori dal gestionale)", key=f"{k}_salta_{p['n']}"):
                    try:
                        from .brogliaccio import db_brogliaccio as ob
                        tipo = {1: ob.T_TEL_IN, 2: ob.T_MSG, 3: ob.T_APP}[p["n"]]
                        if _annota(conn, paz_id, tipo, f"{p['nome']}: già fatto, segnato dal percorso"):
                            st.rerun()
                    except Exception:
                        st.error("«Oggi in studio» non è disponibile.")
        fu = passi[-1]
        if fu["parti"]:
            _azione_followup(conn, paz_id, fu, k)
        if not att:
            st.success("Percorso completo.")

        with st.expander("Altri strumenti e passi", expanded=False):
            voci = [("Diagnosi assistita", "📝 Diagnosi assistita"), ("Relazione clinica", "📝 Relazione clinica"),
                    ("Oggi in studio", VOCE_OGGI)]
            for p in passi:
                if p["parti"]:
                    voci += [(x["nome"].split(" · ")[0] if p["n"] != 7 else "Esiti e follow-up", x["voce"])
                             for x in p["parti"]]
                elif p["voce"]:
                    voci.append((p["nome"], p["voce"]))
            visti, bottoni = set(), []
            for nome, voce in voci:
                if voce in visti or not _area(voce):
                    continue
                visti.add(voce)
                bottoni.append((nome, voce))
            cc = st.columns(4)
            for j, (nome, voce) in enumerate(bottoni):
                if cc[j % 4].button(nome, key=f"{k}_altro_{j}", use_container_width=True):
                    _vai(_area(voce), voce, paz_id)


def bottone_in_fondo(conn, sotto) -> None:
    """In fondo alle pagine del percorso: avanti al prossimo passo, o ritorno alla scheda."""
    paz_id = st.session_state.get("paziente_attivo_id")
    if conn is None or not paz_id or not sotto or sotto in (VOCE_SCHEDA, VOCE_OGGI):
        return
    passi = stato(conn, paz_id)
    voci = []
    for p in passi:
        voci += [x["voce"] for x in p["parti"]] or ([p["voce"]] if p["voce"] else [])
    if sotto not in voci:
        return
    # il prossimo: la prima cosa non fatta che non sia la pagina in cui sono
    prox = None
    for p in passi:
        if p["fatto"]:
            continue
        if p["azione"]:
            prox = (AREA_SCHEDA, VOCE_SCHEDA, p["nome"])
            break
        cand = [x for x in p["parti"] if x["fatto"] is False and x["voce"] != sotto and x["area"]]
        if cand:
            prox = (cand[0]["area"], cand[0]["voce"], cand[0]["nome"])
            break
        if not p["parti"] and p["voce"] and p["voce"] != sotto and p["area"]:
            prox = (p["area"], p["voce"], p["nome"])
            break
    st.markdown("---")
    a, b = st.columns([3, 1])
    if prox:
        if a.button(f"▶ Prossimo passo: {prox[2]}", key="perc_fondo_prox", type="primary",
                    use_container_width=True):
            _vai(prox[0], prox[1], paz_id)
    else:
        a.caption("Non ci sono altri passi da fare dopo questo.")
    if b.button("🏠 Scheda del paziente", key="perc_fondo_scheda", use_container_width=True):
        _vai(AREA_SCHEDA, VOCE_SCHEDA, paz_id)
