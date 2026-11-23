# -*- coding: utf-8 -*-
"""
ui_pubblico_adhd.py - Le scale del modulo ADHD compilate da casa, con il link
dei questionari (personale o aperto).

- scala_pubblica_ui(...)  disegna la scala nella pagina pubblica. Stessa forma
  degli altri questionari: ritorna (dati, riassunto). Non mostra punteggi a chi compila.
- importa_da_anamnesi(...) porta nel modulo ADHD le scale arrivate con il link
  (stanno in anamnesi.pnev_json -> questionari, come tutti gli altri questionari).

La scala si puo' compilare da casa solo se lo studio ha caricato il testo degli
item (scheda «Testi e licenze»): senza testo il genitore non avrebbe niente da leggere.
"""
import hashlib
import json
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

import streamlit as st

from . import db_adhd as db
from . import scoring_adhd as sc
from .catalogo_adhd import SCALE

TZ = ZoneInfo("Europe/Rome")

# codice del link  ->  (codice della scala, chiave nel JSON dell'anamnesi)
CODICI_LINK = {
    "ADHD_VAND_GEN": ("VAND_GEN", "adhd_vand_gen"),
    "ADHD_VAND_INS": ("VAND_INS", "adhd_vand_ins"),
    "ADHD_SCARED_B": ("SCARED_B", "adhd_scared_b"),
    "ADHD_SCARED_G": ("SCARED_G", "adhd_scared_g"),
}
TITOLI_LINK = {
    "ADHD_VAND_GEN": "Questionario attenzione e comportamento – Genitori (Vanderbilt)",
    "ADHD_VAND_INS": "Questionario attenzione e comportamento – Insegnanti (Vanderbilt)",
    "ADHD_SCARED_B": "Questionario sulle paure e le preoccupazioni – Ragazzo/a (SCARED)",
    "ADHD_SCARED_G": "Questionario sulle paure e le preoccupazioni – Genitori (SCARED)",
}
CHIAVI_JSON = {chiave: scala for scala, chiave in CODICI_LINK.values()}
MINIMO = 0.8          # quota di risposte sotto la quale non si puo' inviare


def testo_caricato(conn, studio_id, codice_scala):
    try:
        testi, _ = db.leggi_testi(conn, studio_id, codice_scala)
    except Exception:
        return []
    return testi if len(testi) == SCALE[codice_scala]["n_item"] else []


def scala_pubblica_ui(codice_link, conn, prefix, existing=None, studio_id=None):
    """
    Ritorna (dati, riassunto). dati e' None se la scala non e' attiva.
    dati["completo"] dice se le risposte bastano per inviare.
    """
    codice, _ = CODICI_LINK[codice_link]
    scala = SCALE[codice]
    studio_id = studio_id or st.session_state.get("studio_id", 1)
    existing = existing or {}
    prec = existing.get("risposte") or {}
    testi = testo_caricato(conn, studio_id, codice)
    if not testi:
        st.warning("Questo questionario non è ancora attivo. Avvisa lo studio: te lo invieremo di nuovo.")
        return None, ""

    chi = st.text_input("Chi compila (nome e ruolo: mamma, papà, insegnante di…)",
                        value=existing.get("informatore", ""), key=prefix + "_chi")
    st.caption("Rispondi pensando a come si comporta di solito. Non ci sono risposte giuste o sbagliate.")
    risposte = {}
    for titolo, items, opzioni in scala["sezioni"]:
        st.markdown("#### %s" % (titolo if len(scala["sezioni"]) > 1 else "Domande"))
        nomi = dict(opzioni)
        valori = [v for v, _ in opzioni]
        for i in items:
            p = prec.get(str(i), prec.get(i))
            risposte[str(i)] = st.radio(
                "**%s** · %s" % (i, testi[i - 1]), valori,
                index=valori.index(p) if p in valori else None, horizontal=True,
                format_func=lambda v, n=nomi: n[v], key="%s_i%s" % (prefix, i))
    date_r = sum(1 for v in risposte.values() if v is not None)
    st.progress(date_r / scala["n_item"], text="Risposte date: %s su %s" % (date_r, scala["n_item"]))

    p = sc.punteggio_scala(codice, risposte)
    dati = {"version": "adhd_%s_v1" % codice.lower(), "strumento": codice,
            "date": date.today().isoformat(), "informatore": chi.strip(),
            "risposte": risposte, "punteggi": p,
            "completo": date_r >= scala["n_item"] * MINIMO}
    if codice.startswith("VAND"):
        riass = "%s: %s" % (scala["nome"], sc.ESITO_ADHD_TESTO.get(p["esito_adhd"], ""))
    else:
        riass = "%s: totale %s (soglia %s)" % (scala["nome"], p["totale"], p["soglia_totale"])
    if chi.strip():
        riass += " — compilato da %s" % chi.strip()
    return dati, riass


# ------------------------------------------------------------- importazione
def _questionari_anamnesi(conn, paziente_id):
    cur = conn.cursor()
    try:
        cur.execute("SELECT pnev_json FROM anamnesi WHERE paziente_id = %s "
                    "ORDER BY data_anamnesi DESC, id DESC LIMIT 1", (paziente_id,))
        r = cur.fetchone()
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return {}
    finally:
        cur.close()
    if not r:
        return {}
    raw = r.get("pnev_json") if hasattr(r, "get") else r[0]
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8", "replace")
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except ValueError:
            return {}
    q = (raw or {}).get("questionari") if isinstance(raw, dict) else None
    return q if isinstance(q, dict) else {}


def importa_da_anamnesi(conn, studio_id, paziente_id):
    """Porta nel modulo le scale arrivate con il link. Ritorna quante ne ha aggiunte."""
    nuove = 0
    for chiave, d in _questionari_anamnesi(conn, paziente_id).items():
        codice = CHIAVI_JSON.get(chiave)
        if not codice or not isinstance(d, dict) or not isinstance(d.get("risposte"), dict):
            continue
        risposte = d["risposte"]
        impronta = hashlib.sha1(json.dumps([chiave, d.get("date"), d.get("informatore"), risposte],
                                           sort_keys=True, default=str).encode("utf-8")).hexdigest()[:20]
        try:
            giorno = date.fromisoformat(str(d.get("date"))[:10])
        except ValueError:
            giorno = datetime.now(TZ).date()
        rid = db.salva(conn, studio_id, paziente_id, "scala", codice,
                       sc.punteggio_scala(codice, risposte), risposte=risposte,
                       informatore=d.get("informatore") or SCALE[codice]["informatore"],
                       data_reg=datetime.combine(giorno, time(12, 0), tzinfo=TZ),
                       note="Compilata da casa con il link", operatore="link",
                       origine_id="link-" + impronta)
        if rid:
            nuove += 1
    return nuove
