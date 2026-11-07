# -*- coding: utf-8 -*-
"""
modules/pei/fonti_pnev.py — porta nel PDF / PEI i dati che lo studio ha già:

  1. l'ultima valutazione del Profilo Neuro-Evolutivo PNEV (tabella
     inpp_valutazioni): percentuali di disfunzione per sezione, distribuite
     sugli assi del Profilo Dinamico Funzionale;
  2. le relazioni del paziente (archivio_relazioni, relazioni_cliniche),
     da cui inserire un estratto.

Il testo inserito è sempre marcato «da rivedere» e va solo nei campi scelti:
nulla viene sovrascritto.

Studio The Organism - Dott. Giuseppe Ferraioli
"""
from __future__ import annotations

from datetime import date, datetime

import streamlit as st

from ..pei_core import db as pei_db
from ..pei_core.schema import ASSI_PDF
from ..pei_core.ui import azzera_widget

# Sezione del Profilo Neuro-Evolutivo -> asse del PDF
SEZIONE_ASSE = {
    "coordinazione_equilibrio": "motorio_prassico",
    "cerebellare": "motorio_prassico",
    "disdiadococinesia": "motorio_prassico",
    "orientamento_propriocezione": "sensoriale",
    "oculomotori": "sensoriale",
    "riflessi": "neuropsicologico",
    "visuo_percettivi": "neuropsicologico",
}
NOMI_ASSI = dict(ASSI_PDF)
MAX_ESTRATTO = 2000


# ------------------------------------------------------------------ lettura
def _righe(conn, sql, par=()):
    cur = conn.cursor()
    try:
        cur.execute(sql, par)
        nomi = [d[0] for d in cur.description]
        return [dict(zip(nomi, tuple(r))) for r in cur.fetchall()]
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return []
    finally:
        try:
            cur.close()
        except Exception:
            pass


def _esiste(conn, tabella) -> bool:
    r = _righe(conn, "SELECT to_regclass(%s) IS NOT NULL AS c", (tabella,))
    return bool(r and r[0]["c"])


def _fmt(d) -> str:
    if isinstance(d, (date, datetime)):
        return d.strftime("%d/%m/%Y")
    return str(d or "")


def livello(perc: float) -> str:
    """Stessa scala del protocollo: 0 nessuna anomalia, 25/50/75/100 % di disfunzione."""
    if perc <= 0:
        return "nessuna anomalia"
    if perc <= 25:
        return "disfunzione minima"
    if perc <= 50:
        return "disfunzione moderata"
    if perc <= 75:
        return "disfunzione marcata"
    return "disfunzione completa"


def ultimo_profilo(conn, paz_id) -> dict | None:
    if not _esiste(conn, "inpp_valutazioni"):
        return None
    r = _righe(conn, """SELECT id, data_valutazione, riepilogo, risultati, note_finali
                        FROM inpp_valutazioni WHERE paziente_id=%s
                        ORDER BY data_valutazione DESC, id DESC LIMIT 1""", (int(paz_id),))
    if not r:
        return None
    v = r[0]
    riep = v.get("riepilogo") or {}
    if not riep and v.get("risultati"):
        try:
            from ..inpp.protocollo import riepilogo_punteggi
            riep = riepilogo_punteggi(v["risultati"])
        except Exception:
            riep = {}
    v["riepilogo"] = riep
    return v


def testi_per_asse(profilo: dict) -> dict[str, str]:
    data = _fmt(profilo.get("data_valutazione"))
    per_asse: dict[str, list[str]] = {}
    for sez_id, r in (profilo.get("riepilogo") or {}).items():
        asse = SEZIONE_ASSE.get(sez_id)
        if not asse or not isinstance(r, dict):
            continue
        perc = float(r.get("perc") or 0)
        per_asse.setdefault(asse, []).append(
            f"{r.get('label', sez_id)}: {livello(perc)} ({perc:g}%)")
    return {a: f"[Profilo Neuro-Evolutivo PNEV del {data} — da rivedere] " + "; ".join(v) + "."
            for a, v in per_asse.items()}


def relazioni(conn, paz_id) -> list[dict]:
    out = []
    if _esiste(conn, "archivio_relazioni"):
        out += _righe(conn, """SELECT 'a' || id AS chiave, data, titolo, testo FROM archivio_relazioni
                               WHERE paziente_id=%s AND NOT eliminata AND COALESCE(testo,'') <> ''
                               ORDER BY data DESC NULLS LAST, id DESC LIMIT 15""", (int(paz_id),))
    if _esiste(conn, "relazioni_cliniche"):
        out += _righe(conn, """SELECT 'r' || id AS chiave, creato AS data, tipo AS titolo, testo
                               FROM relazioni_cliniche WHERE paziente_id=%s AND COALESCE(testo,'') <> ''
                               ORDER BY id DESC LIMIT 15""", (int(paz_id),))
    return out


# ------------------------------------------------------------------ scrittura
def _aggiungi(contenuto: dict, chiave: str, testo: str) -> bool:
    """Accoda senza duplicare; False se il testo c'era già."""
    attuale = str(contenuto.get(chiave) or "").strip()
    if testo.strip() in attuale:
        return False
    contenuto[chiave] = (attuale + "\n\n" + testo).strip() if attuale else testo
    return True


def pannello(conn, paz_id, utente, tenant_id):
    """Restituisce la callback (doc, prefisso) da passare a pagina_pei(prima_del_modulo=...)."""
    def disegna(doc, pref):
        if doc.tipo not in ("PDF", "PEI"):
            return
        with st.expander("🧬 Dati dello studio: Profilo Neuro-Evolutivo e relazioni"):
            st.caption("Salva prima le modifiche in corso: l'inserimento ricarica il documento dal database.")
            modificato = False

            # 1. Profilo Neuro-Evolutivo -> assi del PDF
            if doc.tipo == "PDF":
                prof = ultimo_profilo(conn, paz_id)
                if not prof or not prof.get("riepilogo"):
                    st.caption("Nessuna valutazione del Profilo Neuro-Evolutivo con punteggi per questo paziente.")
                else:
                    testi = testi_per_asse(prof)
                    st.markdown(f"**Profilo Neuro-Evolutivo del {_fmt(prof.get('data_valutazione'))}**")
                    for asse, t in testi.items():
                        st.write(f"• *{NOMI_ASSI[asse]}* — {t.split('] ', 1)[1]}")
                    scelti = st.multiselect("Assi in cui inserirlo (livello attuale)", list(testi),
                                            default=list(testi), format_func=NOMI_ASSI.get,
                                            key=f"{pref}_pnev_assi")
                    if st.button("Inserisci nel PDF", key=f"{pref}_pnev_ins"):
                        for a in scelti:
                            modificato |= _aggiungi(doc.contenuto, f"{a}_attuale", testi[a])
                        if not modificato:
                            st.info("Questi dati sono già nel PDF.")

            # 2. Relazioni -> campo scelto
            rel = relazioni(conn, paz_id)
            if not rel:
                st.caption("Nessuna relazione con testo in archivio per questo paziente.")
            else:
                st.markdown("**Relazioni dello studio**")
                mappa = {r["chiave"]: r for r in rel}
                k = st.selectbox("Relazione", list(mappa), key=f"{pref}_rel_sel",
                                 format_func=lambda c: f"{_fmt(mappa[c]['data'])} · {mappa[c]['titolo'] or 'Relazione'}")
                r = mappa[k]
                testo = str(r["testo"]).strip()
                st.caption(testo[:500] + ("…" if len(testo) > 500 else ""))
                destinazioni = ({"sintesi": "Sintesi del PDF", "note": "Note del PDF"} if doc.tipo == "PDF"
                                else {"sintesi_profilo": "Sezione 2 — sintesi",
                                      "situazione_familiare": "Sezione 1 — quadro informativo"})
                dest = st.selectbox("Dove inserire l'estratto", list(destinazioni),
                                    format_func=destinazioni.get, key=f"{pref}_rel_dest")
                if st.button("Inserisci l'estratto", key=f"{pref}_rel_ins"):
                    estratto = testo[:MAX_ESTRATTO] + (" […]" if len(testo) > MAX_ESTRATTO else "")
                    blocco = (f"[Estratto da «{r['titolo'] or 'relazione'}» del {_fmt(r['data'])} "
                              f"— da rivedere]\n{estratto}")
                    modificato |= _aggiungi(doc.contenuto, dest, blocco)
                    if not modificato:
                        st.info("Questo estratto è già presente.")

            if modificato:
                pei_db.salva_documento(conn, doc, "paziente", int(paz_id), utente, tenant_id)
                azzera_widget(pref)
                st.rerun()
    return disegna
