"""
Progetto multicurva RGP — pagina Streamlit.

Progettato da Dott. Giuseppe Ferraioli — www.pnev.it
© 2026 Giuseppe Ferraioli. Tutti i diritti riservati.

Il modulo di progettazione è un componente bidirezionale: manda indietro
un valore SOLO quando l'utente salva un progetto o genera un ordine, mai
a ogni ricalcolo. Altrimenti Streamlit rieseguirebbe lo script a ogni
movimento di cursore.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

import streamlit as st
import streamlit.components.v1 as components

from . import db_contattologia as db

_QUI = Path(__file__).parent
_FRONTEND = _QUI / "frontend"

# Il componente viene dichiarato una volta sola per processo.
_componente = components.declare_component("multicurva_rgp", path=str(_FRONTEND))


def _modulo(record: dict[str, Any] | None = None, altezza: int = 2400, key: str = "lac"):
    """Disegna il progettista e restituisce l'ultimo evento ricevuto."""
    return _componente(record=record, altezza=altezza, key=key, default=None)


def _scarica_pdf(nome_file: str, b64: str, etichetta: str = "Scarica l'ordine") -> None:
    st.download_button(etichetta, base64.b64decode(b64), file_name=nome_file,
                       mime="application/pdf", use_container_width=True)


def pagina(conn, studio_id: int, paziente_id: int | None = None,
           paziente_label: str | None = None) -> None:
    """
    Punto d'ingresso. `conn` è la connessione PostgreSQL già impostata
    sullo studio corrente (app.studio_id), come negli altri moduli.
    """
    st.subheader("Contattologia · progettista di lenti")

    if paziente_label:
        st.caption(f"Paziente in cartella: **{paziente_label}**")
    else:
        st.info("Nessun paziente selezionato: i progetti verranno salvati senza collegamento "
                "alla cartella. Seleziona un paziente per collegarli.")

    # ---------------------------------------------------------------- archivio
    with st.expander("Progetti salvati", expanded=False):
        righe = db.elenco_progetti(conn, studio_id, paziente_id)
        if not righe:
            st.caption("Nessun progetto ancora salvato per questa selezione.")
        else:
            for r in righe:
                c1, c2 = st.columns([5, 1])
                with c1:
                    st.markdown(
                        f"**{r['etichetta'] or 'senza nome'}** — {r['sintesi'] or ''}  \n"
                        f"<span style='color:#6B7A71;font-size:.85em'>"
                        f"{r['occhio'] or ''} · {r['aggiornato_il']:%d/%m/%Y %H:%M}</span>",
                        unsafe_allow_html=True)
                with c2:
                    if st.button("Riapri", key=f"apri_{r['rec_id']}", use_container_width=True):
                        st.session_state["lac_record"] = db.leggi_progetto(
                            conn, studio_id, r["rec_id"])
                        st.rerun()

    # ------------------------------------------------------ importa dal sito
    with st.expander("Importa dal sito", expanded=False):
        st.caption("Il file scaricato con \"Scarica per il gestionale\" dalla versione su pnev.it.")
        caricato = st.file_uploader("Progetto (.json)", type="json", key="lac_import")
        if caricato is not None:
            try:
                dati = json.load(caricato)
                record = dati.get("record") if isinstance(dati, dict) and "record" in dati else dati
                if not isinstance(record, dict) or not record.get("id"):
                    st.error("File non riconosciuto: non contiene un progetto valido.")
                else:
                    db.salva_progetto(conn, studio_id, paziente_id, record)
                    st.success(f"Importato: {record.get('etichetta', 'senza nome')} — "
                               f"assegnalo al paziente giusto se necessario.")
            except Exception as e:                                # noqa: BLE001
                st.error(f"Importazione non riuscita: {e}")

    # ---------------------------------------------------------------- modulo
    evento = _modulo(record=st.session_state.get("lac_record"), key="lac")

    # ---------------------------------------------------------------- eventi
    if not evento or not isinstance(evento, dict):
        return

    tipo = evento.get("type")
    # lo stesso evento tornerebbe a ogni rerun: si scarta quello già trattato
    firma = f"{tipo}:{evento.get('stamp') or evento.get('filename') or ''}"
    if st.session_state.get("lac_ultimo") == firma:
        return
    st.session_state["lac_ultimo"] = firma

    if tipo == "rgp:save":
        record = evento.get("record")
        try:
            db.salva_progetto(conn, studio_id, paziente_id, record)
            st.success(f"Progetto salvato in cartella: {record.get('sintesi', '')}")
        except Exception as e:                                   # noqa: BLE001
            st.error(f"Salvataggio non riuscito: {e}")

    elif tipo == "rgp:order":
        record = evento.get("record") or {}
        nome = evento.get("filename") or "ordine.pdf"
        b64 = evento.get("pdfBase64") or ""
        if not b64:
            st.error("Ordine ricevuto senza PDF.")
            return
        try:
            db.salva_progetto(conn, studio_id, paziente_id, record)
            db.salva_ordine(conn, studio_id, paziente_id, record.get("id"),
                            (nome.replace("ordine_", "").replace(".pdf", "")),
                            nome, base64.b64decode(b64))
            st.success(f"Ordine allegato alla cartella: {nome}")
        except Exception as e:                                   # noqa: BLE001
            st.error(f"Ordine non archiviato: {e}")
        _scarica_pdf(nome, b64)


def inizializza(conn) -> None:
    """Da chiamare una volta all'avvio dell'app, come per gli altri moduli."""
    db.crea_schema(conn)
