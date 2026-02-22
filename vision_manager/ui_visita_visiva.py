from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Optional

import streamlit as st

from .db import get_conn, init_db
from .pdf_referto import genera_referto_visita_bytes


def _is_pg(conn) -> bool:
    return conn.__class__.__module__.startswith("psycopg2")


def _ph(conn) -> str:
    return "%s" if _is_pg(conn) else "?"


def _dict_row(cur, row):
    cols = [d[0] for d in cur.description]
    return {cols[i]: row[i] for i in range(len(cols))}


def _safe_date(v) -> str:
    if isinstance(v, (dt.date, dt.datetime)):
        return v.date().isoformat() if isinstance(v, dt.datetime) else v.isoformat()
    return str(v) if v is not None else ""


def _load_pazienti(conn) -> List[Dict[str, Any]]:
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, cognome, nome, data_nascita, note FROM pazienti_visivi ORDER BY cognome, nome")
        rows = cur.fetchall()
        return [_dict_row(cur, r) for r in rows]
    finally:
        try: cur.close()
        except Exception: pass


def _insert_paziente(conn, nome: str, cognome: str, data_nascita: str, note: str) -> int:
    cur = conn.cursor()
    ph = _ph(conn)
    try:
        cur.execute(
            f"INSERT INTO pazienti_visivi (nome, cognome, data_nascita, note) VALUES ({ph},{ph},{ph},{ph}) RETURNING id" if _is_pg(conn)
            else f"INSERT INTO pazienti_visivi (nome, cognome, data_nascita, note) VALUES ({ph},{ph},{ph},{ph})",
            (nome, cognome, data_nascita or None, note),
        )
        if _is_pg(conn):
            pid = cur.fetchone()[0]
        else:
            pid = cur.lastrowid
        conn.commit()
        return int(pid)
    finally:
        try: cur.close()
        except Exception: pass


def _insert_visita(conn, paziente_id: int, data_visita: str, dati: str) -> int:
    cur = conn.cursor()
    ph = _ph(conn)
    try:
        cur.execute(
            f"INSERT INTO visite_visive (paziente_id, data_visita, dati_json) VALUES ({ph},{ph},{ph}) RETURNING id" if _is_pg(conn)
            else f"INSERT INTO visite_visive (paziente_id, data_visita, dati_json) VALUES ({ph},{ph},{ph})",
            (paziente_id, data_visita, dati),
        )
        vid = cur.fetchone()[0] if _is_pg(conn) else cur.lastrowid
        conn.commit()
        return int(vid)
    finally:
        try: cur.close()
        except Exception: pass


def _list_visite(conn, paziente_id: int) -> List[Dict[str, Any]]:
    cur = conn.cursor()
    ph = _ph(conn)
    try:
        cur.execute(f"SELECT id, data_visita, dati_json FROM visite_visive WHERE paziente_id={ph} ORDER BY data_visita DESC, id DESC LIMIT 200", (paziente_id,))
        rows = cur.fetchall()
        return [_dict_row(cur, r) for r in rows]
    finally:
        try: cur.close()
        except Exception: pass


def ui_visita_visiva():
    st.subheader("🩺 Visita visiva (Cirillo)")

    conn = get_conn()
    init_db(conn)

    tab_paz, tab_vis = st.tabs(["👤 Paziente", "🗓️ Visite & Referti"])

    with tab_paz:
        st.markdown("### Aggiungi paziente (database Vision separato)")
        c1, c2, c3 = st.columns([1, 1, 1])
        nome = c1.text_input("Nome")
        cognome = c2.text_input("Cognome")
        data_nascita = c3.text_input("Data nascita (YYYY-MM-DD)", value="")
        note = st.text_area("Note", height=90)

        if st.button("💾 Salva paziente"):
            if not nome.strip() or not cognome.strip():
                st.error("Nome e cognome sono obbligatori.")
            else:
                pid = _insert_paziente(conn, nome.strip(), cognome.strip(), data_nascita.strip(), note.strip())
                st.success(f"Paziente salvato (ID {pid}).")

        st.markdown("### Elenco pazienti")
        paz = _load_pazienti(conn)
        st.dataframe(paz, use_container_width=True)

    with tab_vis:
        paz = _load_pazienti(conn)
        if not paz:
            st.info("Prima crea almeno un paziente nella tab 'Paziente'.")
            return

        def fmt(p):
            dn = p.get("data_nascita") or ""
            return f"{p['cognome']} {p['nome']} (ID {p['id']}) {dn}".strip()

        psel = st.selectbox("Seleziona paziente", paz, format_func=fmt)
        paziente_id = int(psel["id"])

        st.markdown("### Nuova visita")
        c1, c2 = st.columns([1, 2])
        data_visita = c1.date_input("Data visita", value=dt.date.today())
        dati_json = c2.text_area(
            "Dati visita (testo/JSON)",
            height=150,
            placeholder="Puoi incollare un JSON o scrivere testo strutturato. (Versione minima)",
        )

        if st.button("💾 Salva visita"):
            vid = _insert_visita(conn, paziente_id, _safe_date(data_visita), dati_json)
            st.success(f"Visita salvata (ID {vid}).")

        st.markdown("### Storico visite")
        visite = _list_visite(conn, paziente_id)

        for v in visite:
            with st.expander(f"Visita #{v['id']} — {v.get('data_visita','')}"):
                st.code(v.get("dati_json") or "", language="json")
                # PDF generation expects a dict; we pass a minimal dict
                dati = {
                    "paziente": {
                        "nome": psel.get("nome"),
                        "cognome": psel.get("cognome"),
                        "data_nascita": psel.get("data_nascita"),
                    },
                    "visita": {
                        "id": v["id"],
                        "data_visita": v.get("data_visita"),
                        "dati_json": v.get("dati_json"),
                    },
                    "note": "",
                }
                try:
                    pdf_bytes = genera_referto_visita_bytes(dati)
                    st.download_button(
                        "⬇️ Scarica Referto A4 (Cirillo)",
                        data=pdf_bytes,
                        file_name=f"referto_visivo_cirillo_{paziente_id}_{v['id']}.pdf",
                        mime="application/pdf",
                    )
                except Exception as e:
                    st.error("Errore generazione PDF (mancano template/asset o campi).")
                    st.exception(e)
