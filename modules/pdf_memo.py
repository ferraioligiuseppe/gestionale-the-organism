# -*- coding: utf-8 -*-
"""PDF da scaricare senza rifarli a ogni clic.

st.download_button vuole i byte del file già pronti: scritto in modo
diretto, il PDF viene rigenerato a OGNI clic sulla pagina (anche su un
campo che non c'entra), e ogni volta costa da 50 a 250 ms.

scarica_pdf() conserva il PDF nella sessione e lo rifà solo quando cambia
la «firma», cioè l'insieme delle cose da cui il contenuto dipende
(paziente, settimana, nome da stampare…). Il pulsante resta uno solo.

Uso:
    scarica_pdf("Scarica la scheda", lambda: genera(...),
                firma=(paziente_id, lunedi), file_name="scheda.pdf", key="k")

Regola: nella firma va messo TUTTO ciò che cambia il PDF. Se il PDF legge
dati che l'utente modifica nella stessa pagina, quei dati vanno nella firma.
"""
from __future__ import annotations

import streamlit as st


def _studio() -> int:
    try:
        return int(st.session_state.get("studio_id") or 1)
    except Exception:
        return 1


def pdf_in_memoria(key: str, genera, firma=()) -> bytes:
    """I byte del PDF: presi dalla sessione se la firma è la stessa, altrimenti rigenerati."""
    chiave = f"_pdfmemo_{key}"
    firma_piena = (_studio(), repr(firma))
    tenuto = st.session_state.get(chiave)
    if isinstance(tenuto, tuple) and len(tenuto) == 2 and tenuto[0] == firma_piena and tenuto[1]:
        return tenuto[1]
    dati = genera()
    if isinstance(dati, (bytes, bytearray)) and dati:
        st.session_state[chiave] = (firma_piena, bytes(dati))
    return dati


def scarica_pdf(label: str, genera, *, firma=(), file_name: str, key: str,
                mime: str = "application/pdf", contenitore=None, **kw):
    """download_button che non rigenera il PDF a ogni clic."""
    dove = contenitore if contenitore is not None else st
    return dove.download_button(label, pdf_in_memoria(key, genera, firma),
                                file_name=file_name, mime=mime, key=key, **kw)
