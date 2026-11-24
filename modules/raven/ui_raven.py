# -*- coding: utf-8 -*-
"""
ui_raven.py - Interfaccia Streamlit delle Matrici di Raven (CPM, SPM).

PUNTI DI INTEGRAZIONE
1. Router: render_raven(conn, paz_id)
2. Firma interna: render(conn, studio_id, paziente, carta_intestata=None, operatore=None)
3. RLS: variabile di sessione 'app.studio_id' (impostata da db_raven._cur)

SCHEDE
  Somministrazioni (foglio di inserimento, punteggio, relazione, PDF) · Norme e chiave
"""
from datetime import datetime, time
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from . import db_raven as db
from . import scoring_raven as sc
from .catalogo_raven import (FORME, PUNTI, SCARTO_MAX, COLLABORAZIONE, ATTENZIONE, STILE, AVVERTENZA)

TZ = ZoneInfo("Europe/Rome")
MODI = {"totali": "Solo i totali per serie",
        "esiti": "Item per item: giusto / sbagliato",
        "risposte": "Item per item: risposta scelta (corregge da solo)"}


# ------------------------------------------------------------------ utilita
def _init(conn, studio_id):
    key = "raven_init_%s" % studio_id
    if not st.session_state.get(key):
        db.init_db(conn, studio_id)
        st.session_state[key] = True


def _data(d):
    try:
        return d.astimezone(TZ).strftime("%d/%m/%Y")
    except Exception:
        try:
            return d.strftime("%d/%m/%Y")
        except Exception:
            return str(d or "—")


def _nonce():
    return st.session_state.setdefault("raven_nonce", 0)


def _num(v):
    """Cella del foglio -> int oppure None (vuota)."""
    try:
        if v is None or v != v:
            return None
        return int(v)
    except (TypeError, ValueError):
        return None


def _tabelle(conn, studio_id, forma):
    norme, fonte = db.leggi_tabella(conn, studio_id, forma, "norme")
    attese, _ = db.leggi_tabella(conn, studio_id, forma, "attese")
    chiave, _ = db.leggi_tabella(conn, studio_id, forma, "chiave")
    return norme or [], fonte, attese or {}, chiave or {}


def _diario(studio_id, pid, rid, titolo, riassunto, operatore):
    """Voce automatica nel diario clinico, se il modulo diario e' disponibile."""
    try:
        from ..diario.db_diario import registra_voce_diario
        registra_voce_diario(studio_id, pid, "valutazione", "raven", rid, riassunto,
                             titolo=titolo, autore=operatore)
    except Exception:
        pass


def _mostra_esito(forma, ris):
    f = FORME[forma]
    col = st.columns(len(f["serie"]) + 1)
    for c, s in zip(col, f["serie"]):
        c.metric("Serie %s" % s, "%d / %d" % (ris["serie"][s], f["item"]))
    col[-1].metric("Totale", "%d / %d" % (ris["totale"], ris["massimo"]))
    if ris.get("grado"):
        st.success("**%s** — grado %s: %s." % (ris["fascia"].capitalize(), ris["grado"], ris["lettura"]))
    else:
        st.info("Punteggio grezzo calcolato. Collocazione rispetto ai coetanei non disponibile: %s."
                % (ris.get("motivo_senza_norma") or "norme non caricate"))
    c = ris.get("composizione")
    if c:
        df = pd.DataFrame({"Serie": list(f["serie"]),
                           "Ottenuto": [ris["serie"][s] for s in f["serie"]],
                           "Atteso per questo totale": [c["attesi"][s] for s in f["serie"]],
                           "Scarto": [("%+d" % c["scarti"][s]) if c["scarti"][s] else "0" for s in f["serie"]]})
        st.dataframe(df, use_container_width=True, hide_index=True)
        if c["atipica"]:
            st.warning("Composizione atipica: scarto oltre %d punti nella serie %s. Il totale va letto "
                       "con cautela." % (SCARTO_MAX, ", ".join(c["serie_fuori"])))
        else:
            st.caption("Composizione coerente con il totale (scarti entro %d punti)." % SCARTO_MAX)


# ====================================================================== render
def render(conn, studio_id, paziente, carta_intestata=None, operatore=None):
    _init(conn, studio_id)
    pid = paziente["id"]
    st.subheader("Matrici di Raven — CPM · SPM · %s" % (paziente.get("nome_completo") or ""))
    st.caption(AVVERTENZA)

    regs = db.lista(conn, studio_id, pid)
    t_s, t_n = st.tabs(["Somministrazioni", "Norme e chiave"])
    with t_s:
        with st.expander("➕ Nuova somministrazione", expanded=not regs):
            _nuova(conn, studio_id, paziente, operatore)
        if regs:
            st.markdown("#### Somministrazioni registrate")
        for i, r in enumerate(regs):
            _registrazione(conn, studio_id, paziente, r, carta_intestata, operatore, aperta=(i == 0))
    with t_n:
        _scheda_tabelle(conn, studio_id)


# ------------------------------------------------------------ nuova prova
def _nuova(conn, studio_id, paziente, operatore):
    pid, n = paziente["id"], _nonce()
    k = lambda nome: "raven_%s_%s_%s" % (nome, pid, n)
    oggi = datetime.now(TZ).date()
    eta_oggi = sc.eta_mesi(paziente.get("data_nascita"), oggi)
    predef = 0 if (eta_oggi is None or eta_oggi < 12 * 12) else 1

    c1, c2, c3 = st.columns([2, 1, 1])
    forma = c1.radio("Forma", list(FORME), index=predef, horizontal=True, key=k("forma"),
                     format_func=lambda x: FORME[x]["nome"])
    giorno = c2.date_input("Data della prova", value=oggi, format="DD/MM/YYYY", key=k("data"))
    minuti = c3.number_input("Tempo (minuti)", min_value=0, max_value=180, value=0, step=1, key=k("min"),
                             help="Facoltativo. Lascia 0 se non l'hai rilevato.")
    f = FORME[forma]
    mesi = sc.eta_mesi(paziente.get("data_nascita"), giorno)
    st.caption("Età alla prova: %s · %s: %s." % (sc.eta_testo(mesi), f["breve"], f["uso"]))

    norme, fonte, attese, chiave = _tabelle(conn, studio_id, forma)
    # il foglio item per item e' il modo predefinito; i soli totali restano come scorciatoia
    modi = (["risposte"] if chiave else []) + ["esiti", "totali"]
    modo = st.radio("Come inserisci i risultati", modi, format_func=MODI.get, horizontal=True,
                    key=k("modo_" + forma))
    if not chiave:
        st.caption("Per scrivere nel foglio il numero della risposta data (1, 2, 3…) e far correggere al "
                   "gestionale, carica una volta la chiave dal tuo manuale nella scheda «Norme e chiave». "
                   "Fino ad allora nel foglio spunti giusto / sbagliato.")

    righe = ["Item %d" % i for i in range(1, f["item"] + 1)]
    griglia = None
    try:
        if modo == "totali":
            col = st.columns(len(f["serie"]))
            totali = {s: c.number_input("Serie %s" % s, min_value=0, max_value=f["item"], value=0, step=1,
                                        key=k("tot_%s_%s" % (forma, s)))
                      for c, s in zip(col, f["serie"])}
            punteggi = sc.punteggi_da_totali(forma, totali)
        elif modo == "esiti":
            st.caption("Spunta le risposte corrette. Le caselle vuote contano come errore.")
            base = pd.DataFrame(False, index=righe, columns=f["serie"])
            out = st.data_editor(
                base, key=k("gr_esiti_" + forma), use_container_width=True, height=458,
                column_config={s: st.column_config.CheckboxColumn("Serie %s" % s) for s in f["serie"]})
            griglia = {s: [bool(v) for v in out[s].tolist()] for s in f["serie"]}
            punteggi = sc.punteggi_da_esiti(forma, griglia)
        else:
            st.caption("Scrivi il numero dell'alternativa scelta. Cella vuota = nessuna risposta. "
                       "Puoi incollare una colonna da Excel.")
            base = pd.DataFrame({s: pd.Series([None] * f["item"], dtype="float") for s in f["serie"]})
            base.index = righe
            out = st.data_editor(
                base, key=k("gr_risp_" + forma), use_container_width=True, height=458,
                column_config={s: st.column_config.NumberColumn(
                    "Serie %s" % s, min_value=1, max_value=f["alternative"][s], step=1, format="%d")
                    for s in f["serie"]})
            griglia = {s: [_num(v) for v in out[s].tolist()] for s in f["serie"]}
            punteggi = sc.punteggi_da_risposte(forma, griglia, chiave)
    except ValueError as e:
        st.error(str(e))
        return

    st.markdown("**Percentile dal manuale e osservazioni** (facoltativi)")
    c1, c2 = st.columns(2)
    perc = c1.number_input(
        "Percentile esatto letto sul manuale", min_value=0.0, max_value=99.9, value=0.0, step=1.0,
        key=k("perc"), help="Facoltativo. Se lo scrivi, vale al posto della tabella dello studio. "
                            "Lascia 0 per usare la tabella.")
    altro = c2.text_input("Altro punteggio dal manuale", key=k("altro"),
                          placeholder="es. punteggio standard 95",
                          help="Facoltativo: finisce nella relazione così come lo scrivi.")
    c1, c2, c3 = st.columns(3)
    coll = c1.selectbox("Collaborazione", COLLABORAZIONE, key=k("coll"))
    att = c2.selectbox("Attenzione", ATTENZIONE, key=k("att"))
    stile = c3.selectbox("Stile di risposta", STILE, key=k("stile"))
    note = st.text_area("Osservazioni libere (entrano nella relazione)", key=k("note"), height=80)

    ris = sc.valuta(forma, punteggi, mesi, norme, attese, perc or None, fonte)
    if ris["totale"] == 0:
        st.info("Inserisci i risultati qui sopra: punteggio e collocazione compaiono subito.")
    else:
        _mostra_esito(forma, ris)

    if st.button("Salva e prepara la relazione", type="primary", key=k("salva")):
        oss = {"collaborazione": coll, "attenzione": att, "stile": stile, "minuti": int(minuti) or None,
               "note": note.strip() or None, "altro_punteggio": altro.strip() or None}
        testo = sc.relazione(paziente.get("nome_completo"), forma, giorno, ris, oss)
        rid = db.salva(conn, studio_id, pid, forma, ris,
                       risposte={"modo": modo, "griglia": griglia, "osservazioni": oss},
                       relazione=testo, data_reg=datetime.combine(giorno, time(12, 0), tzinfo=TZ),
                       operatore=operatore)
        _diario(studio_id, pid, rid, "Matrici di Raven — %s" % f["breve"], sc.riga_sintesi(ris), operatore)
        st.session_state["raven_nonce"] = n + 1
        st.session_state["raven_nuova_%s" % pid] = rid
        st.rerun()


# ------------------------------------------------------- una registrazione
def _registrazione(conn, studio_id, paziente, r, carta_intestata, operatore, aperta):
    pid, rid = paziente["id"], r["id"]
    ris, forma = r["punteggi"], r["forma"]
    appena = st.session_state.get("raven_nuova_%s" % pid) == rid
    with st.expander("%s · %s" % (_data(r["data_reg"]), sc.riga_sintesi(ris)), expanded=aperta or appena):
        if appena:
            st.success("Salvata. Qui sotto trovi la relazione: correggila se serve, poi scarica il PDF.")
        _mostra_esito(forma, ris)

        k_txt = "raven_txt_%s" % rid

        def _salva_testo():
            db.aggiorna_relazione(conn, studio_id, pid, rid, st.session_state.get(k_txt) or "")

        st.text_area("Relazione", value=r.get("relazione") or "", height=380, key=k_txt,
                     on_change=_salva_testo,
                     help="Il testo si salva da solo quando esci dal riquadro.")

        c1, c2, c3 = st.columns(3)
        if c1.button("Prepara il PDF", type="primary", key="raven_pdf_%s" % rid):
            from .pdf_raven import genera_pdf
            testo = st.session_state.get(k_txt, r.get("relazione") or "")
            db.aggiorna_relazione(conn, studio_id, pid, rid, testo)
            try:
                st.session_state["raven_pdfb_%s" % rid] = genera_pdf(
                    paziente, dict(r, relazione=testo), carta_intestata, operatore)
            except Exception as e:
                st.error("Non sono riuscito a preparare il PDF: %s" % e)
        pdf = st.session_state.get("raven_pdfb_%s" % rid)
        if pdf:
            nome = "".join(ch if ch.isalnum() else "_" for ch in (paziente.get("nome_completo") or "paziente"))
            c1.download_button("Scarica il PDF", pdf, mime="application/pdf", key="raven_dl_%s" % rid,
                               file_name="Raven_%s_%s_%s.pdf" % (forma, nome, _data(r["data_reg"]).replace("/", "")))
        if c2.button("Ricalcola con le norme di oggi", key="raven_ric_%s" % rid,
                     help="Da usare se hai caricato o corretto le tabelle dopo aver salvato la prova. "
                          "Riscrive anche la relazione: le correzioni fatte a mano si perdono."):
            norme, fonte, attese, _ = _tabelle(conn, studio_id, forma)
            base = {x: ris[x] for x in ("forma", "modo", "serie", "totale", "massimo", "omessi") if x in ris}
            nuovo = sc.valuta(forma, base, ris.get("eta_mesi"), norme, attese,
                              ris.get("percentile_manuale"), fonte)
            testo = sc.relazione(paziente.get("nome_completo"), forma, r["data_reg"], nuovo,
                                 (r.get("risposte") or {}).get("osservazioni"))
            db.aggiorna_punteggi(conn, studio_id, pid, rid, nuovo, testo)
            st.session_state.pop(k_txt, None)
            st.session_state.pop("raven_pdfb_%s" % rid, None)
            st.rerun()
        if c3.checkbox("Voglio eliminarla", key="raven_delc_%s" % rid):
            if c3.button("Elimina definitivamente", key="raven_del_%s" % rid):
                db.elimina(conn, studio_id, pid, rid)
                st.rerun()


# ------------------------------------------------------------ norme e chiave
def _scheda_tabelle(conn, studio_id):
    st.markdown(
        "Figure, chiave di correzione e tabelle normative delle Matrici di Raven sono dell'editore: "
        "nel gestionale **non ci sono**. Le copi tu, una volta sola, dal manuale che hai acquistato; "
        "restano nel database del tuo studio e non vengono condivise con altri studi.")
    forma = st.radio("Forma", list(FORME), horizontal=True, key="raven_tab_forma",
                     format_func=lambda x: FORME[x]["nome"])
    f = FORME[forma]
    massimo = f["item"] * len(f["serie"])
    norme, fonte, attese, chiave = _tabelle(conn, studio_id, forma)
    stato = lambda ok: "✅ caricata" if ok else "⬜ da caricare"
    st.caption("Norme: %s · Composizione attesa: %s · Chiave: %s" % (stato(norme), stato(attese), stato(chiave)))

    # ---- norme
    st.markdown("#### 1 · Tabella normativa")
    st.caption("Una riga per fascia d'età. In ogni colonna scrivi il punteggio grezzo che nel manuale "
               "corrisponde a quel percentile. Se il manuale non riporta un percentile, lascia la cella "
               "vuota. Puoi incollare da Excel.")
    colp = ["%d°" % p for p in PUNTI]
    righe = [[r["da"] // 12, r["da"] % 12, r["a"] // 12, r["a"] % 12] + [r.get("p%d" % p) for p in PUNTI]
             for r in norme] or [[None] * (4 + len(PUNTI))] * 6
    df = pd.DataFrame(righe, columns=["Da anni", "Da mesi", "A anni", "A mesi"] + colp, dtype="float")
    cfg = {c: st.column_config.NumberColumn(c, min_value=0, max_value=massimo, step=1, format="%d") for c in colp}
    cfg.update({"Da anni": st.column_config.NumberColumn("Da anni", min_value=0, max_value=99, step=1, format="%d"),
                "A anni": st.column_config.NumberColumn("A anni", min_value=0, max_value=99, step=1, format="%d"),
                "Da mesi": st.column_config.NumberColumn("Da mesi", min_value=0, max_value=11, step=1, format="%d"),
                "A mesi": st.column_config.NumberColumn("A mesi", min_value=0, max_value=11, step=1, format="%d")})
    out = st.data_editor(df, key="raven_norme_%s" % forma, num_rows="dynamic", hide_index=True,
                         use_container_width=True, column_config=cfg)
    nuova_fonte = st.text_input("Fonte delle norme (compare nella relazione)", value=fonte or "",
                                key="raven_fonte_%s" % forma, placeholder="es. taratura italiana, anno, editore")
    c1, c2 = st.columns([1, 3])
    if c1.button("Salva le norme", type="primary", key="raven_norme_s_%s" % forma):
        grezze = []
        for _, r in out.iterrows():
            da_a, da_m, a_a, a_m = (_num(r[c]) for c in ("Da anni", "Da mesi", "A anni", "A mesi"))
            riga = {"da": None if da_a is None else da_a * 12 + (da_m or 0),
                    "a": None if a_a is None else a_a * 12 + (11 if a_m is None else a_m)}
            riga.update({"p%d" % p: _num(r["%d°" % p]) for p in PUNTI})
            grezze.append(riga)
        buone, errori = sc.controlla_norme(forma, grezze)
        if errori:
            for e in errori:
                st.error(e)
        elif not buone:
            st.warning("La tabella è vuota: non ho salvato niente.")
        else:
            db.salva_tabella(conn, studio_id, forma, "norme", buone, nuova_fonte.strip())
            st.success("Norme salvate: %d fasce d'età." % len(buone))
    if norme and c2.button("Cancella le norme", key="raven_norme_d_%s" % forma):
        db.elimina_tabella(conn, studio_id, forma, "norme")
        st.rerun()

    # ---- attese
    st.markdown("#### 2 · Composizione attesa del punteggio (facoltativa)")
    st.caption("È la tabella del manuale che, per ogni totale, dà il punteggio atteso in ciascuna serie. "
               "Serve a segnalare i totali «irregolari» (scarto oltre %d punti in una serie)." % SCARTO_MAX)
    righe = [[int(t)] + v for t, v in sorted(attese.items(), key=lambda x: int(x[0]))] \
        or [[None] * (1 + len(f["serie"]))] * 6
    df2 = pd.DataFrame(righe, columns=["Totale"] + f["serie"], dtype="float")
    cfg2 = {c: st.column_config.NumberColumn("Serie %s" % c, min_value=0, max_value=f["item"], step=1, format="%d")
            for c in f["serie"]}
    cfg2["Totale"] = st.column_config.NumberColumn("Totale", min_value=0, max_value=massimo, step=1, format="%d")
    out2 = st.data_editor(df2, key="raven_att_%s" % forma, num_rows="dynamic", hide_index=True,
                          use_container_width=True, column_config=cfg2)
    c1, c2 = st.columns([1, 3])
    if c1.button("Salva la composizione", key="raven_att_s_%s" % forma):
        grezze = [dict({"totale": _num(r["Totale"])}, **{s: _num(r[s]) for s in f["serie"]})
                  for _, r in out2.iterrows()]
        buone, errori = sc.controlla_attese(forma, grezze)
        if errori:
            for e in errori:
                st.error(e)
        elif not buone:
            st.warning("La tabella è vuota: non ho salvato niente.")
        else:
            db.salva_tabella(conn, studio_id, forma, "attese", buone)
            st.success("Composizione salvata per %d totali." % len(buone))
    if attese and c2.button("Cancella la composizione", key="raven_att_d_%s" % forma):
        db.elimina_tabella(conn, studio_id, forma, "attese")
        st.rerun()

    # ---- chiave
    st.markdown("#### 3 · Chiave di correzione (facoltativa)")
    st.caption("Per ogni serie scrivi di seguito le %d risposte corrette, una cifra per item "
               "(es. 4 5 1 2 6 3 …). Con la chiave caricata puoi inserire l'alternativa scelta dal "
               "paziente e il gestionale corregge da solo. Per sicurezza la chiave non viene mai "
               "mostrata a schermo dopo il salvataggio." % f["item"])
    col = st.columns(len(f["serie"]))
    testi = {s: c.text_input("Serie %s" % s, key="raven_ch_%s_%s" % (forma, s), type="password")
             for c, s in zip(col, f["serie"])}
    c1, c2 = st.columns([1, 3])
    if c1.button("Salva la chiave", key="raven_ch_s_%s" % forma):
        letta, errori = sc.leggi_chiave(forma, testi)
        if errori:
            for e in errori:
                st.error(e)
        else:
            db.salva_tabella(conn, studio_id, forma, "chiave", letta)
            st.success("Chiave salvata.")
    if chiave and c2.button("Cancella la chiave", key="raven_ch_d_%s" % forma):
        db.elimina_tabella(conn, studio_id, forma, "chiave")
        st.rerun()


# ================================================================== router
def render_raven(conn, paz_id):
    """Chiamata dal router: ricava da sola paziente, studio, carta intestata e operatore."""
    paz = {"id": paz_id, "nome_completo": "", "data_nascita": None}
    try:
        c = conn.cursor()
        c.execute("SELECT cognome, nome, data_nascita FROM pazienti WHERE id=%s", (paz_id,))
        r = c.fetchone()
        if r:
            r = r if isinstance(r, dict) else dict(zip(("cognome", "nome", "data_nascita"), r))
            paz["nome_completo"] = ("%s %s" % (r.get("cognome") or "", r.get("nome") or "")).strip().title()
            paz["data_nascita"] = r.get("data_nascita")
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
    carta = None
    try:
        from ..pdf_templates import _carta_intestata_bytes
        carta = _carta_intestata_bytes()
    except Exception:
        pass
    render(conn, st.session_state.get("studio_id", 1), paz, carta_intestata=carta,
           operatore=str(st.session_state.get("username") or st.session_state.get("user") or ""))
