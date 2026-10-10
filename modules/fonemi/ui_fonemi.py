# -*- coding: utf-8 -*-
"""
ui_fonemi.py - Interfaccia Streamlit del modulo Impostazione fonemi (PNEV).

PUNTI DI INTEGRAZIONE
1. Firma: render(conn, studio_id, paziente, carta_intestata=None, operatore=None)
2. RLS: variabile di sessione 'app.studio_id' (impostata da db_fonemi._cur)
3. paziente: dict con chiavi 'id', 'nome_completo', 'data_nascita'
"""
from datetime import datetime, time
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from . import db_fonemi as db
from .catalogo_fonemi import (APPOGGI, APPOGGI_LABEL, FONEMI, LIVELLI,
                              CRITERIO_PERC, CRITERIO_MIN_PROVE, CRITERIO_SEDUTE,
                              etichetta)
from .pdf_fonemi import genera_pdf

TZ = ZoneInfo("Europe/Rome")

# Tavole illustrate (una per fonema), nella cartella tavole/ accanto a questo file.
import os as _os
_TAVOLE = _os.path.join(_os.path.dirname(__file__), "tavole")


def _tavola(cod):
    """Il disegno SVG del fonema, oppure None."""
    try:
        for f in sorted(_os.listdir(_TAVOLE)):
            if f.lower().endswith(".svg") and f[:-4].split("_", 1)[-1] == cod:
                with open(_os.path.join(_TAVOLE, f), encoding="utf-8") as h:
                    return h.read()
    except Exception:
        return None
    return None


def _mostra_tavola(cod, chiave=""):
    svg = _tavola(cod)
    if not svg:
        st.caption("Tavola non disponibile per questo fonema.")
        return
    svg = svg.replace("<svg ", '<svg style="width:100%;height:auto" ', 1)
    st.markdown('<div style="max-width:760px;margin:6px 0 12px">' + svg + '</div>',
                unsafe_allow_html=True)


def _init(conn, studio_id):
    key = f"fon_init_{studio_id}"
    if not st.session_state.get(key):
        db.init_db(conn, studio_id)
        st.session_state[key] = True


def render(conn, studio_id, paziente, carta_intestata=None, operatore=None):
    _init(conn, studio_id)
    pid = paziente["id"]
    st.subheader(f"Impostazione fonemi — {paziente.get('nome_completo', '')}")

    t_ob, t_sed, t_sto, t_sch, t_pdf = st.tabs(
        ["Obiettivi", "Nuova seduta", "Storico", "Scheda fonemi", "Report PDF"])

    obiettivi = db.lista_obiettivi(conn, studio_id, pid)

    # ------------------------------------------------------------ OBIETTIVI
    with t_ob:
        with st.form("fon_nuovo_ob", clear_on_submit=True):
            c1, c2 = st.columns([2, 1])
            gia = {o["fonema"] for o in obiettivi if o["stato"] == "attivo"}
            scelte = [k for k in FONEMI if k not in gia]
            fon = c1.selectbox("Fonema", scelte, format_func=etichetta) if scelte else None
            liv = c2.selectbox("Livello di partenza", list(LIVELLI),
                               format_func=lambda n: f"{n} · {LIVELLI[n][0]}")
            nota = st.text_input("Note (opzionale)")
            if st.form_submit_button("Aggiungi obiettivo") and fon:
                db.crea_obiettivo(conn, studio_id, pid, fon, liv, nota or None)
                st.success("Obiettivo aggiunto.")
                st.rerun()

        if not obiettivi:
            st.info("Nessun obiettivo fonetico impostato.")
        for o in obiettivi:
            f = FONEMI[o["fonema"]]
            with st.expander(f"{f['simbolo']}  ·  livello {o['livello']} "
                             f"({LIVELLI[o['livello']][0]})  ·  {o['stato']}"):
                st.caption(f"{f['punto_modo']} — {f['facilitazione']}")
                if o["stato"] == "attivo":
                    pronto, motivo = db.valuta_passaggio(conn, studio_id, pid, o)
                    (st.success if pronto else st.info)(motivo)
                c1, c2, c3 = st.columns(3)
                nuovo_liv = c1.selectbox("Livello", list(LIVELLI), index=o["livello"] - 1,
                                         key=f"liv_{o['id']}",
                                         format_func=lambda n: f"{n} · {LIVELLI[n][0]}")
                stati = ["attivo", "raggiunto", "sospeso"]
                nuovo_st = c2.selectbox("Stato", stati, index=stati.index(o["stato"]),
                                        key=f"st_{o['id']}")
                if c3.button("Salva", key=f"sv_{o['id']}"):
                    db.aggiorna_obiettivo(conn, studio_id, o["id"], nuovo_liv, nuovo_st)
                    st.rerun()

    # ------------------------------------------------------------ NUOVA SEDUTA
    with t_sed:
        attivi = [o for o in obiettivi if o["stato"] == "attivo"]
        if not attivi:
            st.info("Imposta prima almeno un obiettivo attivo.")
        else:
            c1, c2 = st.columns(2)
            data = c1.date_input("Data seduta", datetime.now(TZ).date(), format="DD/MM/YYYY")
            op = c2.text_input("Operatore", value=operatore or "")
            prove = []
            for o in attivi:
                f = FONEMI[o["fonema"]]
                st.markdown(f"**{f['simbolo']}** — livello {o['livello']} · "
                            f"{LIVELLI[o['livello']][0]}")
                st.caption(f"Facilitazione: {f['facilitazione']} · Appoggio: {f['appoggio']}")
                k = o["id"]
                with st.expander("🖼️ Tavola del fonema"):
                    _mostra_tavola(o["fonema"])
                a, b, c = st.columns([1, 1, 3])
                n = a.number_input("Prove", 0, 200, 0, key=f"n_{k}")
                ok = b.number_input("Corrette", 0, 200, 0, key=f"ok_{k}")
                app = c.multiselect("Appoggi usati", APPOGGI, key=f"ap_{k}",
                                    format_func=lambda x: APPOGGI_LABEL[x])
                ctx = st.text_input("Contesto (sillabe/parole usate)", key=f"cx_{k}")
                if n:
                    pc = db.perc(min(ok, n), n)
                    st.progress(min(pc / 100, 1.0), text=f"{pc}%")
                if ok > n:
                    st.warning("Le corrette superano le prove.")
                prove.append(dict(obiettivo_id=k, livello=o["livello"], n_prove=n,
                                  n_corrette=min(ok, n), appoggi=app, contesto=ctx or None))
                st.divider()
            note = st.text_area("Note di seduta")
            if st.button("Registra seduta", type="primary"):
                if not any(p["n_prove"] for p in prove):
                    st.error("Inserisci almeno una prova.")
                else:
                    dt = datetime.combine(data, time(12, 0), tzinfo=TZ)
                    db.salva_seduta(conn, studio_id, pid, prove, op or None, note or None, dt)
                    st.success("Seduta registrata.")
                    st.rerun()

    # ------------------------------------------------------------ STORICO
    storico = db.storico_prove(conn, studio_id, pid)
    with t_sto:
        if not storico:
            st.info("Nessuna seduta registrata.")
        else:
            for o in obiettivi:
                righe = [r for r in storico if r["obiettivo_id"] == o["id"]]
                if not righe:
                    continue
                st.markdown(f"**{FONEMI[o['fonema']]['simbolo']}**")
                df = pd.DataFrame([{
                    "Data": r["data_seduta"].astimezone(TZ).strftime("%d/%m/%Y"),
                    "Livello": r["livello"], "Prove": r["n_prove"],
                    "Corrette": r["n_corrette"], "%": r["perc"],
                    "Appoggi": ", ".join(APPOGGI_LABEL.get(a, a) for a in r["appoggi"]),
                    "Contesto": r["contesto"] or ""} for r in righe])
                st.line_chart(df.set_index("Data")["%"], height=180)
                st.dataframe(df, hide_index=True, use_container_width=True)
            with st.expander("Elimina una seduta"):
                sed = db.lista_sedute(conn, studio_id, pid)
                sid = st.selectbox("Seduta", [s["id"] for s in sed],
                                   format_func=lambda i: next(
                                       s["data_seduta"].astimezone(TZ).strftime("%d/%m/%Y")
                                       + f" · {s['n_obiettivi']} fonemi" for s in sed if s["id"] == i))
                if st.checkbox("Confermo l'eliminazione") and st.button("Elimina"):
                    db.elimina_seduta(conn, studio_id, sid)
                    st.rerun()

    # ------------------------------------------------------------ SCHEDA
    with t_sch:
        st.caption(f"Criterio di passaggio: ≥{CRITERIO_PERC}% su almeno {CRITERIO_MIN_PROVE} "
                   f"prove, per {CRITERIO_SEDUTE} sedute consecutive allo stesso livello.")
        st.dataframe(pd.DataFrame([{
            "Fonema": f["simbolo"], "Gruppo": f["gruppo"], "Punto / modo": f["punto_modo"],
            "Facilitazione tattile": f["facilitazione"], "Appoggio": f["appoggio"],
            "Vocale favorevole": f["vocale_favorevole"]} for f in FONEMI.values()]),
            hide_index=True, use_container_width=True)
        st.markdown("**Tavola illustrata**")
        _cod = st.selectbox("Fonema", list(FONEMI.keys()), key="fon_tav_sel",
                            format_func=lambda k: f"{FONEMI[k]['simbolo']} — {FONEMI[k]['punto_modo']}")
        _mostra_tavola(_cod)
        _svg = _tavola(_cod)
        if _svg:
            st.download_button("⬇️ Scarica la tavola (SVG)", _svg, file_name=f"tavola_{_cod}.svg",
                               mime="image/svg+xml", key=f"fon_tav_dl_{_cod}")
        _pdf_tav = _os.path.join(_TAVOLE, "PNEV_tavole_fonemi.pdf")
        if _os.path.exists(_pdf_tav):
            with open(_pdf_tav, "rb") as h:
                st.download_button("🖨️ Tutte le tavole in PDF, da stampare", h.read(),
                                   file_name="PNEV_tavole_fonemi.pdf", mime="application/pdf", key="fon_tav_pdf")
        _pdf_fac = _os.path.join(_TAVOLE, "PNEV_facilitazioni_tattili_fonemi.pdf")
        if _os.path.exists(_pdf_fac):
            with open(_pdf_fac, "rb") as h:
                st.download_button("📘 Scheda operativa: facilitazioni tattili-cinestesiche (PDF)", h.read(),
                                   file_name="PNEV_facilitazioni_tattili_fonemi.pdf", mime="application/pdf",
                                   key="fon_fac_pdf")
        st.caption("Materiale originale PNEV. Non riproduce il protocollo PROMPT®.")

    # ------------------------------------------------------------ PDF
    with t_pdf:
        if not obiettivi:
            st.info("Nessun dato da esportare.")
        else:
            pdf = genera_pdf(paziente, obiettivi, storico, carta_intestata, operatore)
            st.download_button("Scarica report PDF", pdf, mime="application/pdf",
                               file_name=f"fonemi_{pid}_{datetime.now(TZ):%Y%m%d}.pdf")
