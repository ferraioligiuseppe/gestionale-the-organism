# -*- coding: utf-8 -*-
"""Valutazioni adulti complete: risultati già presenti negli altri moduli.

Le valutazioni complete (funzionale e neurologica) non ripetono i test che
il gestionale ha già: DEM interattivo, INPP, Audiometria tonale, Diagnostica
uditiva (test tonale Tomatis e le altre prove), WHODAS 2.0. Qui si leggono
gli ultimi risultati salvati per il paziente, si mostrano sopra l'app e si
passano all'app stessa, che li riporta nella sezione giusta e nella
relazione. Ogni lettura è indipendente: se una tabella non esiste o è
vuota, quella voce semplicemente non compare.
"""
from __future__ import annotations

import json

import streamlit as st


def _righe(conn, sql, par):
    try:
        cur = conn.cursor()
        cur.execute(sql, par)
        r = cur.fetchall() or []
        if r and not isinstance(r[0], dict):
            nomi = [c[0] for c in cur.description]
            r = [dict(zip(nomi, x)) for x in r]
        return r
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return []


def _d(v):
    return str(v)[:10] if v else ""


def _num(v, dec=1):
    try:
        return f"{float(v):.{dec}f}".replace(".", ",")
    except Exception:
        return str(v) if v not in (None, "") else "—"


def _json(v):
    if isinstance(v, dict):
        return v
    try:
        x = json.loads(v or "{}")
        return x if isinstance(x, dict) else {}
    except Exception:
        return {}


def risultati(conn, paz_id) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    if conn is None or not paz_id:
        return out
    pid = int(paz_id)

    r = _righe(conn, "SELECT data, vt, ht, aht, ratio, errori_totali FROM dem_risultati "
                     "WHERE paziente_id=%s ORDER BY data DESC LIMIT 1", (pid,))
    if r:
        x = r[0]
        out["dem"] = [f"DEM del {_d(x.get('data'))}: verticale {_num(x.get('vt'))} s, orizzontale corretto "
                      f"{_num(x.get('aht'))} s, rapporto {_num(x.get('ratio'), 2)}, errori {x.get('errori_totali') or 0}"]

    r = _righe(conn, "SELECT data_valutazione, riepilogo, note_finali FROM inpp_valutazioni "
                     "WHERE paziente_id=%s ORDER BY data_valutazione DESC, id DESC LIMIT 1", (pid,))
    if r:
        x = r[0]
        rie = _json(x.get("riepilogo"))
        voci = [f"{k}: {v}" for k, v in rie.items() if v not in (None, "", [], {})][:10]
        out["inpp"] = [f"INPP del {_d(x.get('data_valutazione'))}"] + voci
        if x.get("note_finali"):
            out["inpp"].append(f"Note: {str(x['note_finali'])[:200]}")

    r = _righe(conn, "SELECT creato_il, pta_od, pta_os, modalita FROM audiometrie_tonali "
                     "WHERE paziente_id=%s ORDER BY creato_il DESC LIMIT 1", (pid,))
    if r:
        x = r[0]
        out["audio"] = [f"Audiometria tonale del {_d(x.get('creato_il'))}: media OD {_num(x.get('pta_od'))} dB, "
                        f"OS {_num(x.get('pta_os'))} dB" + (f" ({x['modalita']})" if x.get("modalita") else "")]

    r = _righe(conn, "SELECT tipo, data_esame, punteggio, classificazione FROM diagnostica_uditiva "
                     "WHERE paziente_id=%s ORDER BY id DESC LIMIT 20", (pid,))
    visti, righe = set(), []
    for x in r:
        t = x.get("tipo") or "esame"
        if t in visti:
            continue
        visti.add(t)
        righe.append(f"{t} del {_d(x.get('data_esame'))}"
                     + (f": punteggio {_num(x.get('punteggio'))}" if x.get("punteggio") is not None else "")
                     + (f" — {x['classificazione']}" if x.get("classificazione") else ""))
    if righe:
        out["uditiva"] = righe

    r = _righe(conn, "SELECT * FROM whodas_somministrazioni WHERE paziente_id=%s "
                     "ORDER BY data_somministrazione DESC, id DESC LIMIT 1", (pid,))
    if r:
        x = r[0]
        pt = [f"{k.replace('_', ' ')}: {_num(v)}" for k, v in x.items()
              if any(s in k.lower() for s in ("punteggio", "totale", "score")) and v is not None][:6]
        out["whodas"] = [f"WHODAS 2.0 del {_d(x.get('data_somministrazione'))}"] + pt
    return out


def script_risultati(conn, paz_id) -> str:
    dati = json.dumps(risultati(conn, paz_id), ensure_ascii=False).replace("</", "<\\/")
    return f"<script>window.PNEV_ESTERNI = {dati};</script>"


NOMI = {"dem": "DEM interattivo", "inpp": "INPP", "audio": "Audiometria tonale",
        "uditiva": "Diagnostica uditiva (test tonale e altre prove)", "whodas": "WHODAS 2.0"}


def riquadro(conn, paz_id, chiavi) -> None:
    ris = risultati(conn, paz_id)
    with st.expander("📥 Risultati già presenti nel gestionale", expanded=False):
        for k in chiavi:
            if ris.get(k):
                st.markdown(f"**{NOMI[k]}**")
                for riga in ris[k]:
                    st.markdown(f"- {riga}")
            else:
                st.caption(f"{NOMI[k]}: nessun risultato salvato per questo paziente. "
                           "Esegui il test dal suo modulo e riapri questa pagina.")


def render_valutazione_adulti(conn, paz_id, tipo: str) -> None:
    from .ui_protocollo_pdf_app import render_protocollo_pdf_app
    if tipo == "funzionale":
        riquadro(conn, paz_id, ["dem", "inpp", "audio", "uditiva"])
        render_protocollo_pdf_app(
            conn, paz_id,
            html_file="Valutazione_ADULTI_funzionale_MASTER.html",
            pdf_file="Valutazione_ADULTI_funzionale.pdf",
            titolo="🧑 Valutazione adulti — funzionale completa",
            sottotitolo="17–64 anni. Optometria, oculomotricità, visuo-percezione, vestibolare, riflessi, "
                        "uditivo, miofunzionale e ATM, posturologia.",
            kp="vaf", extra_js=script_risultati(conn, paz_id))
    else:
        riquadro(conn, paz_id, ["whodas"])
        render_protocollo_pdf_app(
            conn, paz_id,
            html_file="Valutazione_ADULTI_neurologica_MASTER.html",
            pdf_file="Valutazione_ADULTI_neurologica.pdf",
            titolo="🧠 Valutazione adulti — neurologica completa",
            sottotitolo="17–64 anni. Esame neurologico per distretti, neuropsicologia, scale motorie, "
                        "umore, sonno, funzionamento.",
            kp="van", extra_js=script_risultati(conn, paz_id))
