# -*- coding: utf-8 -*-
"""Archivio delle relazioni del paziente.

Qui si conservano le relazioni scritte fuori dal gestionale — con ChatGPT,
Claude o un'altra AI, da un altro professionista, a mano — insieme a quelle
generate dalla Diagnosi assistita. Restano nel database (non su disco, che
su Streamlit Cloud si svuota a ogni riavvio).

Le relazioni segnate «📌 tieni presente» entrano per intero nello storico che
legge la Diagnosi assistita: l'AI ne tiene conto ogni volta. Le altre
compaiono solo con titolo e data.

La vecchia tabella relazioni_cliniche salvava solo il percorso di un file
sul disco del server: dopo un riavvio il file non c'era piu'. Non si usa qui.
"""
from __future__ import annotations

import datetime as dt
import io

import streamlit as st

TIPI = ["Relazione clinica", "Diagnosi", "Progetto psicopedagogico", "Relazione per la scuola",
        "Lettera a un collega", "Referto", "Piano di trattamento", "Altro"]
FONTI = ["Diagnosi assistita del gestionale", "AI esterna (ChatGPT, Claude…)", "Scritta dallo studio",
         "Altro professionista", "Altro"]
MAX_EVIDENZA = 4000   # caratteri per relazione «tieni presente» passati alla diagnosi


def _q(conn, sql, par=()):
    try:
        cur = conn.cursor()
        cur.execute(sql, par)
        r = cur.fetchall() or []
        if r and not isinstance(r[0], dict):
            n = [c[0] for c in cur.description]
            r = [dict(zip(n, x)) for x in r]
        return r
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return []


def _esegui(conn, sql, par=()):
    try:
        cur = conn.cursor()
        cur.execute(sql, par)
        conn.commit()
        return ""
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        return str(e)


def _utente():
    return str(st.session_state.get("username") or st.session_state.get("user") or "")


def _tabella(conn):
    if st.session_state.get("_arch_rel_ok"):
        return
    if not _esegui(conn,
        "CREATE TABLE IF NOT EXISTS archivio_relazioni ("
        " id BIGSERIAL PRIMARY KEY, paziente_id BIGINT NOT NULL, data DATE,"
        " tipo TEXT, titolo TEXT, fonte TEXT, autore TEXT, testo TEXT,"
        " file BYTEA, nome_file TEXT, mime TEXT, in_evidenza BOOLEAN DEFAULT TRUE,"
        " note TEXT, eliminata BOOLEAN DEFAULT FALSE,"
        " creato_il TIMESTAMPTZ DEFAULT NOW(), creato_da TEXT);"
        "CREATE INDEX IF NOT EXISTS archivio_relazioni_paz ON archivio_relazioni (paziente_id, data DESC);"):
        st.session_state["_arch_rel_ok"] = True


def salva_relazione(conn, paz_id, titolo, testo, tipo="Relazione clinica", fonte="Scritta dallo studio",
                    autore="", data=None, file=None, nome_file=None, mime=None, in_evidenza=True, note=""):
    _tabella(conn)
    return _esegui(conn,
        "INSERT INTO archivio_relazioni (paziente_id, data, tipo, titolo, fonte, autore, testo, file, nome_file, "
        "mime, in_evidenza, note, creato_da) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (int(paz_id), data or dt.date.today(), tipo, (titolo or "").strip() or tipo, fonte, autore,
         testo or "", file, nome_file, mime, bool(in_evidenza), note, _utente()))


def _relazioni(conn, paz_id):
    # Mai la colonna file nell'elenco: e' il documento intero.
    return _q(conn, "SELECT id, data, tipo, titolo, fonte, autore, testo, nome_file, mime, in_evidenza, note, "
                    "creato_il, creato_da, octet_length(file) AS peso FROM archivio_relazioni "
                    "WHERE paziente_id=%s AND NOT eliminata ORDER BY data DESC NULLS LAST, id DESC", (int(paz_id),))


def _testo_da_file(nome, dati):
    """Il testo di un file caricato, se si riesce a leggerlo senza AI."""
    n = (nome or "").lower()
    try:
        if n.endswith(".txt") or n.endswith(".md"):
            return dati.decode("utf-8", errors="replace")
        if n.endswith(".docx"):
            from docx import Document
            doc = Document(io.BytesIO(dati))
            return "\n".join(p.text for p in doc.paragraphs)
        if n.endswith(".pdf"):
            try:
                from pypdf import PdfReader
            except Exception:
                from PyPDF2 import PdfReader
            return "\n".join((pg.extract_text() or "") for pg in PdfReader(io.BytesIO(dati)).pages)
    except Exception:
        return ""
    return ""


def _fmt(d):
    return d.strftime("%d/%m/%Y") if hasattr(d, "strftime") else (str(d)[:10] if d else "—")


def render_archivio(conn, paz_id):
    st.subheader("📚 Archivio relazioni")
    st.caption("Le relazioni del paziente in un posto solo: quelle scritte con un'AI esterna, da altri "
               "professionisti o dallo studio, e quelle salvate dalla Diagnosi assistita. "
               "Quelle con 📌 la Diagnosi assistita le legge per intero ogni volta.")
    if conn is None or not paz_id:
        st.info("Seleziona un paziente.")
        return
    _tabella(conn)
    k = f"arch_{paz_id}"

    with st.expander("➕ Aggiungi una relazione", expanded=not _relazioni(conn, paz_id)):
        c1, c2, c3 = st.columns([2, 2, 1])
        tipo = c1.selectbox("Tipo", TIPI, key=f"{k}_tipo")
        fonte = c2.selectbox("Da dove viene", FONTI, index=1, key=f"{k}_fonte")
        data = c3.date_input("Data", dt.date.today(), key=f"{k}_data", format="DD/MM/YYYY")
        titolo = st.text_input("Titolo", key=f"{k}_tit", placeholder="es. Relazione PNEV di sintesi — ottobre 2026")
        autore = st.text_input("Autore o strumento (facoltativo)", key=f"{k}_aut",
                               placeholder="es. ChatGPT su indicazione del Dott. Ferraioli · Dott.ssa Rossi, NPI")
        modo = st.radio("Contenuto", ["Incolla il testo", "Carica un file (PDF, Word, testo)"],
                        horizontal=True, key=f"{k}_modo")
        testo, f = "", None
        if modo.startswith("Incolla"):
            testo = st.text_area("Testo della relazione", height=260, key=f"{k}_txt")
        else:
            f = st.file_uploader("File", type=["pdf", "docx", "txt", "md"], key=f"{k}_file")
            if f is not None:
                letto = _testo_da_file(f.name, f.getvalue())
                if letto.strip():
                    st.caption(f"Testo letto dal file: {len(letto)} caratteri. Puoi correggerlo qui sotto.")
                else:
                    st.caption("Non riesco a leggere il testo di questo file (es. una scansione): lo conservo "
                               "come allegato. Se vuoi che la Diagnosi lo legga, incolla qui sotto il testo.")
                testo = st.text_area("Testo (per la ricerca e per la Diagnosi assistita)", value=letto,
                                     height=220, key=f"{k}_txt_f_{f.name}")
        evid = st.checkbox("📌 Tieni presente nella Diagnosi assistita", value=True, key=f"{k}_ev")
        note = st.text_input("Note (facoltative)", key=f"{k}_note")
        if st.button("💾 Salva nell'archivio", type="primary", key=f"{k}_salva",
                     disabled=not (testo.strip() or f is not None)):
            err = salva_relazione(conn, paz_id, titolo, testo, tipo, fonte, autore, data,
                                  f.getvalue() if f is not None else None, f.name if f is not None else None,
                                  (f.type if f is not None else None), evid, note)
            if err:
                st.error(f"Non salvata: {err}")
            else:
                st.session_state.pop(f"diag_storico_{paz_id}", None)
                st.session_state.pop(f"_fascicolo_{paz_id}", None)
                st.success("Relazione salvata.")
                st.rerun()

    righe = _relazioni(conn, paz_id)
    if not righe:
        st.info("Nessuna relazione in archivio per questo paziente.")
        return
    cerca = st.text_input("🔎 Cerca nelle relazioni", key=f"{k}_cerca")
    if cerca.strip():
        c = cerca.strip().lower()
        righe = [r for r in righe if c in " ".join(str(r.get(x) or "") for x in ("titolo", "testo", "tipo",
                                                                                 "autore", "note")).lower()]
    st.caption(f"{len(righe)} relazioni · 📌 = la Diagnosi assistita le legge per intero")
    for r in righe:
        testa = (f"{'📌 ' if r.get('in_evidenza') else ''}{_fmt(r.get('data'))} · {r.get('titolo') or r.get('tipo')}"
                 f" · {r.get('tipo')}")
        with st.expander(testa):
            st.caption(" · ".join(x for x in (r.get("fonte") or "", r.get("autore") or "",
                                              f"inserita da {r['creato_da']}" if r.get("creato_da") else "",
                                              r.get("note") or "") if x))
            if r.get("testo"):
                st.text(r["testo"])
            a, b, c, d = st.columns(4)
            if a.button("📌 Togli" if r.get("in_evidenza") else "📌 Tieni presente", key=f"{k}_ev_{r['id']}",
                        use_container_width=True):
                _esegui(conn, "UPDATE archivio_relazioni SET in_evidenza = NOT in_evidenza WHERE id=%s", (r["id"],))
                st.session_state.pop(f"diag_storico_{paz_id}", None)
                st.rerun()
            b.download_button("⬇️ Testo", data=r.get("testo") or "", key=f"{k}_dlt_{r['id']}",
                              file_name=f"relazione_{r['id']}.txt", mime="text/plain", use_container_width=True)
            if r.get("peso"):
                if c.button(f"📎 {r.get('nome_file') or 'file'}", key=f"{k}_fl_{r['id']}", use_container_width=True):
                    x = _q(conn, "SELECT file FROM archivio_relazioni WHERE id=%s", (r["id"],))
                    if x and x[0].get("file"):
                        st.download_button("Scarica il file originale", data=bytes(x[0]["file"]),
                                           file_name=r.get("nome_file") or "relazione",
                                           mime=r.get("mime") or "application/octet-stream",
                                           key=f"{k}_fd_{r['id']}")
            if d.button("🗑 Elimina", key=f"{k}_del_{r['id']}", use_container_width=True):
                st.session_state[f"{k}_conf_{r['id']}"] = True
            if st.session_state.get(f"{k}_conf_{r['id']}"):
                st.warning("Eliminare questa relazione? Resta recuperabile dal database, ma sparisce da qui.")
                y, n = st.columns(2)
                if y.button("Sì, elimina", key=f"{k}_si_{r['id']}", type="primary"):
                    _esegui(conn, "UPDATE archivio_relazioni SET eliminata=TRUE WHERE id=%s", (r["id"],))
                    st.session_state.pop(f"{k}_conf_{r['id']}", None)
                    st.session_state.pop(f"diag_storico_{paz_id}", None)
                    st.rerun()
                if n.button("Annulla", key=f"{k}_no_{r['id']}"):
                    st.session_state.pop(f"{k}_conf_{r['id']}", None)
                    st.rerun()


def sintesi_archivio(conn, paz_id) -> list[str]:
    """Per la Diagnosi assistita: le 📌 per intero, le altre solo titolo e data."""
    righe = _relazioni(conn, paz_id)
    if not righe:
        return []
    out = []
    for r in righe:
        testa = f"- {_fmt(r.get('data'))} · {r.get('tipo')} · {r.get('titolo')}" + \
                (f" ({r['fonte']}" + (f", {r['autore']}" if r.get("autore") else "") + ")" if r.get("fonte") else "")
        if r.get("in_evidenza") and (r.get("testo") or "").strip():
            t = " ".join(r["testo"].split())
            out.append(testa + ":\n  " + t[:MAX_EVIDENZA] + ("…" if len(t) > MAX_EVIDENZA else ""))
        else:
            out.append(testa)
    return out
