# -*- coding: utf-8 -*-
"""
ui_adhd.py - Interfaccia Streamlit del modulo ADHD (PNEV).

PUNTI DI INTEGRAZIONE
1. Firma: render(conn, studio_id, paziente, carta_intestata=None, operatore=None)
2. RLS: variabile di sessione 'app.studio_id' (impostata da db_adhd._cur)
3. paziente: dict con chiavi 'id', 'nome_completo', 'data_nascita'

SCHEDE
  Quadro · Scale · Criteri · Prove a schermo · Test esterni · Report PDF · Testi e licenze
"""
import os
import re
from datetime import datetime, time
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from . import db_adhd as db
from . import scoring_adhd as sc
from .catalogo_adhd import (SCALE, SCARED_SOTTOSCALE, CRITERI_DISATTENZIONE, CRITERI_IPERATTIVITA,
                            CONTESTI, GRAVITA, PROVE, METRICHE, TEST_ESTERNI, AVVERTENZA)

TZ = ZoneInfo("Europe/Rome")
_componente = None


# ------------------------------------------------------------------ utilita
def _init(conn, studio_id):
    key = "adhd_init_%s" % studio_id
    if not st.session_state.get(key):
        db.init_db(conn, studio_id)
        st.session_state[key] = True


def _quando(giorno):
    return datetime.combine(giorno, time(12, 0), tzinfo=TZ)


def _data(d):
    try:
        return d.astimezone(TZ).strftime("%d/%m/%Y")
    except Exception:
        try:
            return d.strftime("%d/%m/%Y")
        except Exception:
            return str(d or "—")


def _eta(paziente):
    return sc.eta_anni(paziente.get("data_nascita"), datetime.now(TZ).date())


def _nonce(nome):
    return st.session_state.setdefault("adhd_n_" + nome, 0)


def _avanza(nome):
    st.session_state["adhd_n_" + nome] = _nonce(nome) + 1


def _diario(studio_id, pid, rid, titolo, riassunto, operatore):
    """Voce automatica nel diario clinico, se il modulo diario e' disponibile."""
    try:
        from ..diario.db_diario import registra_voce_diario
        registra_voce_diario(studio_id, pid, "valutazione", "adhd", rid, riassunto,
                             titolo=titolo, autore=operatore)
    except Exception:
        pass


def _elimina(conn, studio_id, pid, r, chiave):
    if st.button("Elimina questa registrazione", key="adhd_del_%s_%s" % (chiave, r["id"])):
        db.elimina(conn, studio_id, pid, r["id"])
        st.rerun()


def _prove_componente():
    global _componente
    if _componente is None:
        import streamlit.components.v1 as components
        _componente = components.declare_component(
            "adhd_prove_pnev", path=os.path.join(os.path.dirname(__file__), "prove_component"))
    return _componente


# ====================================================================== render
def render(conn, studio_id, paziente, carta_intestata=None, operatore=None):
    _init(conn, studio_id)
    pid = paziente["id"]
    eta = _eta(paziente)
    st.subheader("ADHD — attenzione, iperattività, autoregolazione · %s" % (paziente.get("nome_completo") or ""))
    st.caption(AVVERTENZA)

    try:
        from .ui_pubblico_adhd import importa_da_anamnesi
        arrivate = importa_da_anamnesi(conn, studio_id, pid)
        if arrivate:
            st.success("Arrivate dal link dei questionari: %s scala/e, aggiunte al quadro." % arrivate)
    except Exception:
        pass
    regs = db.lista(conn, studio_id, pid)
    for r in regs:
        if r["categoria"] == "prova":
            r["strumento_nome"] = PROVE.get(r["strumento"], {}).get("nome", r["strumento"])

    t_q, t_s, t_c, t_p, t_e, t_pdf, t_t = st.tabs(
        ["Quadro", "Scale", "Criteri", "Prove a schermo", "Test esterni", "Report PDF", "Testi e licenze"])

    with t_q:
        _scheda_quadro(regs, eta)
    with t_s:
        _scheda_scale(conn, studio_id, pid, regs, eta, operatore)
    with t_c:
        _scheda_criteri(conn, studio_id, pid, regs, eta, operatore)
    with t_p:
        _scheda_prove(conn, studio_id, pid, regs, eta, operatore)
    with t_e:
        _scheda_esterni(conn, studio_id, pid, regs, operatore)
    with t_pdf:
        _scheda_pdf(paziente, regs, carta_intestata, operatore)
    with t_t:
        _scheda_testi(conn, studio_id)


# ====================================================================== quadro
def _scheda_quadro(regs, eta):
    if not regs:
        st.info("Ancora nessun dato. Il percorso consigliato è qui sotto: parti dalle scale.")
    fatti = {(r["categoria"], r["strumento"]) for r in regs}
    passi = [
        ("Scala genitori", ("scala", "VAND_GEN") in fatti),
        ("Scala insegnanti", ("scala", "VAND_INS") in fatti),
        ("Ansia (SCARED)", any(s.startswith("SCARED") for c, s in fatti if c == "scala")),
        ("Prove a schermo", any(c == "prova" for c, _ in fatti)),
        ("Scheda criteri", ("checklist", "CRITERI") in fatti),
    ]
    cols = st.columns(len(passi))
    for col, (nome, ok) in zip(cols, passi):
        col.metric(nome, "fatto" if ok else "da fare")
    mancano = [n for n, ok in passi if not ok]
    if mancano:
        st.markdown("**Prossimo passo:** %s." % mancano[0])
    if eta is not None and not 6 <= eta <= 12:
        st.caption("Età %s anni: le scale Vanderbilt sono pensate per i 6–12 anni; fuori da questa "
                   "fascia le soglie vanno lette con prudenza." % eta)

    sin = sc.sintesi(regs)
    if regs:
        st.markdown("##### Quadro d'insieme")
        st.write(sin["testo"])
    if sin["righe"]:
        df = pd.DataFrame([{"": "●" if s else "", "Area": a, "Fonte": f, "Esito": e}
                           for a, f, e, s in sin["righe"]])
        st.dataframe(df, hide_index=True, use_container_width=True)
        st.caption("● = elemento che va nella direzione di un approfondimento. "
                   "Per ogni strumento conta l'ultima registrazione.")


# ======================================================================= scale
def _mostra_esito_scala(codice, p):
    if codice.startswith("VAND"):
        st.markdown("**%s**" % sc.ESITO_ADHD_TESTO.get(p.get("esito_adhd"), "—"))
        df = pd.DataFrame([{
            "Area": sc.BLOCCO_TESTO.get(n, n),
            "«Spesso / molto spesso»": "%s su %s" % (d["positivi"], d["su"]),
            "Soglia": d["soglia"], "Media item": d["media"],
            "Screening": "positivo" if d["positivo"] else
                         ("sintomi sopra soglia" if d["sintomi_sopra_soglia"] else "negativo"),
        } for n, d in p.get("blocchi", {}).items()])
        st.dataframe(df, hide_index=True, use_container_width=True)
        st.caption("Aree di rendimento segnate come problema: %s · totale sintomi ADHD %s/54 · "
                   "item senza risposta: %s" % (len(p.get("rendimento_problema") or []),
                                                p.get("totale_sintomi_adhd"), p.get("mancanti", 0)))
    else:
        st.markdown("**Totale %s** (soglia %s): %s" % (
            p.get("totale"), p.get("soglia_totale"),
            "sopra soglia" if p.get("totale_sopra_soglia") else "sotto soglia"))
        df = pd.DataFrame([{"Sottoscala": n, "Punteggio": "%s / %s" % (d["punteggio"], d["massimo"]),
                            "Soglia": d["soglia"],
                            "Esito": "sopra soglia" if d["sopra_soglia"] else "sotto soglia"}
                           for n, d in (p.get("sottoscale") or {}).items()])
        st.dataframe(df, hide_index=True, use_container_width=True)
        if p.get("mancanti"):
            st.caption("Item senza risposta: %s (contati come 0)." % p["mancanti"])


def _scheda_scale(conn, studio_id, pid, regs, eta, operatore):
    codice = st.selectbox("Scala", list(SCALE), format_func=lambda k: SCALE[k]["nome"], key="adhd_scala_sel")
    scala = SCALE[codice]
    testi, _fonte = db.leggi_testi(conn, studio_id, codice)
    ha_testi = len(testi) == scala["n_item"]
    a, b = scala["eta"]
    avviso_eta = "" if eta is None or a <= eta <= b else " · **età del paziente fuori fascia (%s anni)**" % eta
    st.caption("Fascia d'età %s–%s anni%s. %s" % (a, b, avviso_eta, scala["nota"]))
    if ha_testi:
        st.success("Testo degli item caricato: la scala si può compilare qui (anche da tablet) oppure da casa. "
                   "Per mandarla a casa: sezione Questionari → crea il link «%s»; quando torna compilata "
                   "la ritrovi qui da sola." % scala["nome"])
    else:
        st.warning("Testo degli item non caricato: questa scheda funziona come **foglio risposte**. "
                   "Fai compilare il modulo cartaceo e riporta qui le risposte, numero per numero. "
                   "Per compilarla a schermo carica il testo nella scheda «Testi e licenze».")

    n = _nonce("scala_" + codice)
    with st.form("adhd_f_scala_%s_%s" % (codice, n)):
        c1, c2 = st.columns(2)
        informatore = c1.text_input("Compilata da", value=scala["informatore"])
        giorno = c2.date_input("Data di compilazione", value=datetime.now(TZ).date(), format="DD/MM/YYYY")
        risposte = {}
        for titolo, items, opzioni in scala["sezioni"]:
            st.markdown("**%s** — %s" % (titolo, " · ".join("%s = %s" % (v, t) for v, t in opzioni)))
            for i in items:
                if ha_testi:
                    etichetta = "**%s** · %s" % (i, testi[i - 1])
                elif scala["etichette"]:
                    etichetta = "**%s** · _%s_" % (i, scala["etichette"][i - 1])
                else:
                    etichetta = "**%s**" % i
                risposte[i] = st.radio(etichetta, [v for v, _ in opzioni], index=None, horizontal=True,
                                       key="adhd_r_%s_%s_%s" % (codice, n, i))
        note = st.text_area("Note (opzionale)", height=70)
        invia = st.form_submit_button("Calcola e salva", type="primary")

    if invia:
        date = [v for v in risposte.values() if v is not None]
        if len(date) < scala["n_item"] * 0.8:
            st.error("Risposte date: %s su %s. Ne servono almeno l'80%% per salvare." % (len(date), scala["n_item"]))
        else:
            p = sc.punteggio_scala(codice, risposte)
            rid = db.salva(conn, studio_id, pid, "scala", codice, p, risposte=risposte,
                           informatore=informatore, data_reg=_quando(giorno), note=note, operatore=operatore)
            riass = sc.ESITO_ADHD_TESTO.get(p.get("esito_adhd")) if codice.startswith("VAND") else \
                "SCARED totale %s (soglia %s)" % (p["totale"], p["soglia_totale"])
            _diario(studio_id, pid, rid, scala["nome"], riass, operatore)
            _avanza("scala_" + codice)
            st.session_state["adhd_msg_scala"] = "Salvata: %s — %s" % (scala["nome"], riass)
            st.rerun()
    msg = st.session_state.pop("adhd_msg_scala", None)
    if msg:
        st.success(msg)

    storico = [r for r in regs if r["categoria"] == "scala" and r["strumento"] == codice]
    if storico:
        st.markdown("##### Compilazioni salvate")
    for r in storico:
        with st.expander("%s · %s" % (_data(r["data_reg"]), r.get("informatore") or "—")):
            _mostra_esito_scala(codice, r["punteggi"])
            if r.get("note"):
                st.write("Note: %s" % r["note"])
            _elimina(conn, studio_id, pid, r, "scala")


# ===================================================================== criteri
def _scheda_criteri(conn, studio_id, pid, regs, eta, operatore):
    soglia = 5 if (eta is not None and eta >= 17) else 6
    st.caption("Scheda per il clinico, da compilare dopo colloquio, scale e osservazione. Segna i "
               "comportamenti presenti da almeno 6 mesi, in misura non coerente con il livello di "
               "sviluppo. Soglia per dominio: %s%s." % (soglia, " (dai 17 anni in su)" if soglia == 5 else ""))
    n = _nonce("criteri")
    with st.form("adhd_f_criteri_%s" % n):
        c1, c2 = st.columns(2)
        c1.markdown("**Disattenzione**")
        dis = [c1.checkbox(t, key="adhd_cd_%s_%s" % (n, i)) for i, t in enumerate(CRITERI_DISATTENZIONE)]
        c2.markdown("**Iperattività / impulsività**")
        ipe = [c2.checkbox(t, key="adhd_ci_%s_%s" % (n, i)) for i, t in enumerate(CRITERI_IPERATTIVITA)]
        st.markdown("**Condizioni**")
        esordio = st.checkbox("Alcuni sintomi erano presenti prima dei 12 anni", key="adhd_c_es_%s" % n)
        contesti = st.multiselect("Contesti in cui i sintomi sono presenti", CONTESTI, key="adhd_c_co_%s" % n)
        compr = st.checkbox("I sintomi interferiscono con il funzionamento scolastico, sociale o lavorativo",
                            key="adhd_c_cm_%s" % n)
        escl = st.checkbox("Altre spiegazioni sono state considerate ed escluse (ansia, umore, sonno, vista e "
                           "udito, apprendimento, contesto)", key="adhd_c_ex_%s" % n)
        g1, g2 = st.columns(2)
        gravita = g1.selectbox("Gravità (se i criteri sono soddisfatti)", [""] + GRAVITA, key="adhd_c_gr_%s" % n)
        giorno = g2.date_input("Data", value=datetime.now(TZ).date(), format="DD/MM/YYYY", key="adhd_c_dt_%s" % n)
        note = st.text_area("Note cliniche", height=90, key="adhd_c_nt_%s" % n)
        invia = st.form_submit_button("Salva la scheda criteri", type="primary")
    if invia:
        dati = {"disattenzione": dis, "iperattivita": ipe, "esordio_prima_12": esordio,
                "contesti": contesti, "compromissione": compr, "altre_spiegazioni_escluse": escl,
                "gravita": gravita or None}
        p = sc.esito_checklist(dati, eta)
        rid = db.salva(conn, studio_id, pid, "checklist", "CRITERI", p, risposte=dati,
                       data_reg=_quando(giorno), note=note, operatore=operatore)
        riass = ("Criteri soddisfatti, manifestazione %s" % p["manifestazione"]) if p["criteri_soddisfatti"] \
            else "Criteri non tutti soddisfatti"
        _diario(studio_id, pid, rid, "ADHD — scheda criteri", riass, operatore)
        _avanza("criteri")
        st.session_state["adhd_msg_crit"] = riass
        st.rerun()
    msg = st.session_state.pop("adhd_msg_crit", None)
    if msg:
        st.success("Salvata. %s." % msg)

    for r in [x for x in regs if x["categoria"] == "checklist"]:
        p = r["punteggi"]
        with st.expander("%s · disattenzione %s/9 · iperattività %s/9 · %s" % (
                _data(r["data_reg"]), p.get("n_disattenzione"), p.get("n_iperattivita"),
                "criteri soddisfatti" if p.get("criteri_soddisfatti") else "criteri non tutti soddisfatti")):
            for k, ok in (p.get("condizioni") or {}).items():
                st.write("%s %s" % ("✅" if ok else "◻️", k))
            if p.get("manifestazione"):
                st.write("Manifestazione **%s**%s" % (p["manifestazione"],
                         " · gravità %s" % r["risposte"]["gravita"].lower() if r["risposte"].get("gravita") else ""))
            if r.get("note"):
                st.write("Note: %s" % r["note"])
            _elimina(conn, studio_id, pid, r, "crit")


# ======================================================================= prove
def _tabella_prove(prova, righe):
    out = []
    for r in reversed(righe):
        m = r["punteggi"]
        base = {"Data": _data(r["data_reg"])}
        if prova in ("attenzione", "gonogo"):
            base.update({"Omissioni %": m.get("omissioni_perc"),
                         "False risposte %": m.get("false_risposte_perc"),
                         "Tempo medio ms": m.get("rt_media"), "Variabilità (ds) ms": m.get("rt_ds"),
                         "d′": m.get("d_primo")})
        elif prova == "stroop":
            base.update({"Coerenti ms": m["coerenti"]["rt_media"], "Incoerenti ms": m["incoerenti"]["rt_media"],
                         "Interferenza ms": m.get("interferenza_ms"),
                         "Errori coerenti": m["coerenti"]["errori"], "Errori incoerenti": m["incoerenti"]["errori"]})
        else:
            base.update({"Span avanti": m["avanti"]["span"], "Span indietro": m["indietro"]["span"]})
        out.append(base)
    return pd.DataFrame(out)


def _scheda_prove(conn, studio_id, pid, regs, eta, operatore):
    st.caption("Prove costruite dallo studio su paradigmi classici. **Non hanno norme**: danno tempi ed "
               "errori del paziente, utili per confrontarlo con se stesso (prima / dopo il percorso).")
    c1, c2 = st.columns(2)
    prova = c1.selectbox("Prova", list(PROVE), format_func=lambda k: PROVE[k]["nome"], key="adhd_prova_sel")
    info = PROVE[prova]
    durata = c2.selectbox("Durata", list(info["durate"]), index=min(1, len(info["durate"]) - 1),
                          key="adhd_prova_dur_%s" % prova)
    st.write("%s  \n_Misura:_ %s" % (info["cosa"], info["misura"]))
    if eta is not None and eta < info["eta_min"]:
        st.warning("Età %s anni: questa prova è pensata dai %s anni in su." % (eta, info["eta_min"]))

    k_att = "adhd_prova_attiva_%s" % pid
    if st.button("Prepara la prova", type="primary", key="adhd_prova_go"):
        cfg = dict(info["config"])
        if info["durate"][durata]:
            cfg["n_prove"] = info["durate"][durata]
        st.session_state[k_att] = {"prova": prova, "config": cfg,
                                   "giro": st.session_state.get(k_att, {}).get("giro", 0) + 1}
    att = st.session_state.get(k_att)
    if att:
        st.caption("Passa il dispositivo al paziente. La prova parte quando preme «Inizia».")
        v = _prove_componente()(prova=att["prova"], config=att["config"], giro=att["giro"],
                                key="adhd_comp_%s_%s" % (pid, att["giro"]), default=None)
        salvati = st.session_state.setdefault("adhd_prove_salvate", set())
        if isinstance(v, dict) and v.get("azione") == "salva" and v.get("id") not in salvati:
            salvati.add(v["id"])
            m = sc.calcola_prova(v["prova"], v.get("trials"))
            rid = db.salva(conn, studio_id, pid, "prova", v["prova"], m,
                           risposte={"config": v.get("config"), "durata_s": v.get("durata_s"),
                                     "schermo": v.get("schermo"), "trials": v.get("trials")},
                           operatore=operatore, origine_id=v["id"])
            if rid:
                _diario(studio_id, pid, rid, "Prova a schermo — %s" % PROVE[v["prova"]]["nome"],
                        sc.riga_prova(v["prova"], m), operatore)
                st.session_state["adhd_msg_prova"] = "%s salvata: %s" % (
                    PROVE[v["prova"]]["nome"], sc.riga_prova(v["prova"], m))
            st.rerun()
    msg = st.session_state.pop("adhd_msg_prova", None)
    if msg:
        st.success(msg)

    righe = [r for r in regs if r["categoria"] == "prova" and r["strumento"] == prova]
    if righe:
        st.markdown("##### %s — andamento" % info["nome"])
        st.dataframe(_tabella_prove(prova, righe), hide_index=True, use_container_width=True)
        ult = righe[0]["punteggi"]
        if prova in ("attenzione", "gonogo") and ult.get("terzi"):
            st.caption("Ultima prova, tenuta nel tempo (inizio → metà → fine): omissioni %s · tempo medio %s ms" % (
                " → ".join(str(t["omissioni"]) for t in ult["terzi"]),
                " → ".join(str(t["rt_media"]) for t in ult["terzi"])))
        with st.expander("Elimina una prova"):
            for r in righe:
                st.write("%s — %s" % (_data(r["data_reg"]), sc.riga_prova(prova, r["punteggi"])))
                _elimina(conn, studio_id, pid, r, "prova")


# ================================================================ test esterni
def _scheda_esterni(conn, studio_id, pid, regs, operatore):
    st.caption("Per i test che somministri su materiale originale (Conners 3, BIA, WISC-V, Rey, BVSCO…): "
               "qui entrano solo i punteggi che hai già calcolato. Il gestionale non contiene gli item.")
    strumento = st.selectbox("Test", list(TEST_ESTERNI), key="adhd_est_sel")
    preset = TEST_ESTERNI[strumento]
    n = _nonce("esterno")
    with st.form("adhd_f_est_%s_%s" % (strumento, n)):
        c1, c2 = st.columns(2)
        if strumento == "Altro test":
            nome = c1.text_input("Nome del test")
            scala = c2.text_input("Scala / indice")
            verso = st.radio("Un punteggio problematico è…", ["basso", "alto"], horizontal=True,
                             format_func=lambda v: "basso (prove di abilità)" if v == "basso"
                             else "alto (scale di sintomi)")
        else:
            nome = strumento
            scala = c1.selectbox("Scala / indice", preset["scale"])
            verso = preset["verso"]
            c2.text_input("Informatore (se serve)", key="adhd_est_inf_%s" % n)
        d1, d2, d3 = st.columns(3)
        metrica = d1.selectbox("Tipo di punteggio", list(METRICHE), format_func=lambda k: METRICHE[k][0],
                               index=list(METRICHE).index(preset["metrica"]))
        valore = d2.number_input("Valore", value=None, step=1.0, format="%.2f")
        perc_man = d3.text_input("Percentile del manuale (se c'è)")
        e1, e2 = st.columns(2)
        giorno = e1.date_input("Data", value=datetime.now(TZ).date(), format="DD/MM/YYYY")
        note = e2.text_input("Note")
        invia = st.form_submit_button("Aggiungi punteggio", type="primary")
    if invia:
        if valore is None or not nome or not scala:
            st.error("Servono test, scala e valore.")
        else:
            p = {"scala": scala, "metrica": metrica, "valore": valore, "verso": verso,
                 "percentile_manuale": perc_man.strip() or None}
            p.update(sc.converti_punteggio(metrica, valore, verso))
            db.salva(conn, studio_id, pid, "esterno", nome, p,
                     informatore=st.session_state.get("adhd_est_inf_%s" % n) or None,
                     data_reg=_quando(giorno), note=note, operatore=operatore)
            _avanza("esterno")
            st.rerun()

    righe = [r for r in regs if r["categoria"] == "esterno"]
    if righe:
        st.dataframe(pd.DataFrame([{
            "Data": _data(r["data_reg"]), "Test": r["strumento"], "Scala": r["punteggi"].get("scala"),
            "Punteggio": r["punteggi"].get("valore"),
            "Tipo": METRICHE.get(r["punteggi"].get("metrica"), ("",))[0].split(" (")[0],
            "z": r["punteggi"].get("z"),
            "Percentile": r["punteggi"].get("percentile_manuale") or r["punteggi"].get("percentile"),
            "Fascia": r["punteggi"].get("fascia"), "Note": r.get("note") or ""} for r in righe]),
            hide_index=True, use_container_width=True)
        st.caption("z e percentile sono quelli teorici della curva normale, salvo dove hai scritto il "
                   "percentile del manuale. La fascia è indicativa: vale la classificazione del manuale.")
        with st.expander("Elimina un punteggio"):
            for r in righe:
                st.write("%s — %s · %s: %s" % (_data(r["data_reg"]), r["strumento"],
                                               r["punteggi"].get("scala"), r["punteggi"].get("valore")))
                _elimina(conn, studio_id, pid, r, "est")


# ========================================================================= pdf
def _scheda_pdf(paziente, regs, carta_intestata, operatore):
    if not regs:
        st.info("Il report si può creare quando c'è almeno un dato salvato.")
        return
    concl = st.text_area("Considerazioni del clinico (entrano nel report, in fondo)", height=140,
                         key="adhd_pdf_concl_%s" % paziente["id"])
    if st.button("Prepara il report PDF", type="primary", key="adhd_pdf_go"):
        from .pdf_adhd import genera_pdf
        try:
            st.session_state["adhd_pdf_%s" % paziente["id"]] = genera_pdf(
                paziente, regs, carta_intestata=carta_intestata, operatore=operatore, conclusioni=concl)
        except Exception as e:
            st.error("Non sono riuscito a creare il PDF: %s" % e)
    pdf = st.session_state.get("adhd_pdf_%s" % paziente["id"])
    if pdf:
        nome = re.sub(r"[^A-Za-z0-9]+", "_", paziente.get("nome_completo") or "paziente").strip("_")
        st.download_button("Scarica il report", pdf, file_name="ADHD_%s_%s.pdf" % (
            nome, datetime.now(TZ).strftime("%Y%m%d")), mime="application/pdf", key="adhd_pdf_dl")


# ======================================================================= testi
_NUMERO = re.compile(r"^\s*\d{1,2}\s*[\.\)\-–:]\s*")


def _scheda_testi(conn, studio_id):
    st.markdown(
        "Il testo degli item **non è dentro il gestionale**: lo carica ogni studio, una volta, dalla "
        "versione ufficiale che ha il diritto di usare. Resta nel database dello studio.")
    st.markdown(
        "- **Vanderbilt (NICHQ)**: l'edizione 2002 si può usare e distribuire citando NICHQ come fonte. "
        "Per una traduzione italiana dentro un software venduto a terzi conviene avere una conferma scritta.\n"
        "- **SCARED**: gli autori la distribuiscono gratis; per l'uso in un prodotto a pagamento conviene "
        "scrivere a Boris Birmaher (Università di Pittsburgh).\n"
        "- **Conners 3, BIA, BVSCO, EQ-i:YV, Rey**: proprietari. Qui entrano solo come punteggi, nella "
        "scheda «Test esterni».")
    for codice, scala in SCALE.items():
        testi, fonte = db.leggi_testi(conn, studio_id, codice)
        stato = "caricato" if len(testi) == scala["n_item"] else "non caricato"
        with st.expander("%s — %s item · testo %s" % (scala["nome"], scala["n_item"], stato)):
            st.caption(scala["credito"])
            incolla = st.text_area(
                "Incolla gli item, uno per riga, nell'ordine del modulo (%s righe). "
                "Il numero davanti, se c'è, viene tolto." % scala["n_item"],
                value="\n".join(testi), height=220, key="adhd_txt_%s" % codice)
            f = st.text_input("Fonte / versione (es. traduzione, anno, da chi l'hai avuta)",
                              value=fonte or "", key="adhd_txt_f_%s" % codice)
            c1, c2 = st.columns(2)
            if c1.button("Salva il testo", key="adhd_txt_s_%s" % codice):
                righe = [_NUMERO.sub("", x).strip() for x in incolla.splitlines() if x.strip()]
                if len(righe) != scala["n_item"]:
                    st.error("Ho trovato %s righe: ne servono %s." % (len(righe), scala["n_item"]))
                else:
                    db.salva_testi(conn, studio_id, codice, righe, f)
                    st.success("Testo salvato.")
                    st.rerun()
            if testi and c2.button("Togli il testo", key="adhd_txt_d_%s" % codice):
                db.elimina_testi(conn, studio_id, codice)
                st.rerun()
    with st.expander("Come sono calcolati i punteggi"):
        st.markdown(
            "**Vanderbilt** — un item conta se la risposta è «spesso» o «molto spesso». Screening positivo "
            "per disattenzione o iperattività con almeno 6 item su 9 **e** almeno un'area di rendimento "
            "segnata 4 o 5. Genitori: oppositività 4 su 8, condotta 3 su 14, ansia/umore 3 su 7. "
            "Insegnanti: oppositività/condotta 3 su 10, ansia/umore 3 su 7.")
        st.markdown("**SCARED** — totale ≥ 25. " + " · ".join(
            "%s ≥ %s" % (n, s) for n, (_, s) in SCARED_SOTTOSCALE.items()) + ".")
        st.markdown("**Test esterni** — z = (valore − media) / deviazione standard; percentile dalla curva "
                    "normale. Scale di sintomi: z ≥ 1 ai limiti, ≥ 1,5 elevato, ≥ 2 molto elevato "
                    "(T 60 / 65 / 70). Prove di abilità: z ≤ −1 ai limiti inferiori, ≤ −1,5 basso, ≤ −2 molto basso.")


# ============================================================ ingresso dal router
def render_adhd(conn, paz_id):
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
