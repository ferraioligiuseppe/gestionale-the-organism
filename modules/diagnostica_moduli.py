# -*- coding: utf-8 -*-
"""
modules/diagnostica_moduli.py

Controllo di salute del gestionale: prova a compilare tutti i file .py di
modules/ e segnala quelli con errori di scrittura (sintassi), con file e riga.

A cosa serve: dopo ogni caricamento su GitHub, invece di scoprire un errore
entrando nella schermata sbagliata, lo vedi subito qui.

Limite da conoscere: cattura gli errori di SCRITTURA del codice, non quelli
che nascono solo mentre la schermata viene disegnata (per esempio due pannelli
uno dentro l'altro, che Streamlit rifiuta solo al momento del disegno).
"""

import os
import py_compile
import tempfile
import importlib
import streamlit as st

CARTELLA = os.path.dirname(os.path.abspath(__file__))

# Moduli che vale la pena provare a importare davvero (non solo compilare):
# se l'import fallisce, la schermata corrispondente non si aprirà.
IMPORT_CHIAVE = [
    "modules.app_menu",
    "modules.app_main_router",
    "modules.lead_sito",
    "modules.ui_anagrafica",
    "modules.paziente_attivo",
    "modules.ui_questionari",
    "modules.questionario_linguaggio",
    "modules.terapia",
    "modules.logopedia",
    "modules.ui_oculistica",
]


def _elenco_file():
    out = []
    for radice, _dirs, files in os.walk(CARTELLA):
        if "__pycache__" in radice:
            continue
        for f in sorted(files):
            if f.endswith(".py"):
                out.append(os.path.join(radice, f))
    return out


def _controlla_sintassi():
    """Compila ogni file. Ritorna (ok, errori) dove errori è lista di dict."""
    errori, n_ok = [], 0
    with tempfile.TemporaryDirectory() as tmp:
        for percorso in _elenco_file():
            rel = os.path.relpath(percorso, os.path.dirname(CARTELLA))
            try:
                py_compile.compile(
                    percorso,
                    cfile=os.path.join(tmp, os.path.basename(percorso) + "c"),
                    doraise=True)
                n_ok += 1
            except py_compile.PyCompileError as e:
                exc = getattr(e, "exc_value", None)
                errori.append({
                    "file": rel,
                    "riga": getattr(exc, "lineno", None),
                    "messaggio": getattr(exc, "msg", str(e)).strip(),
                    "testo": (getattr(exc, "text", "") or "").strip(),
                })
            except Exception as e:
                errori.append({"file": rel, "riga": None,
                               "messaggio": str(e), "testo": ""})
    return n_ok, errori


def _controlla_import():
    """Prova a importare i moduli chiave. Ritorna lista di (nome, errore|None)."""
    out = []
    for nome in IMPORT_CHIAVE:
        try:
            importlib.import_module(nome)
            out.append((nome, None))
        except Exception as e:
            out.append((nome, f"{type(e).__name__}: {e}"))
    return out


def render_diagnostica():
    st.subheader("🩺 Diagnostica moduli")
    st.caption("Controlla che tutti i file del gestionale siano scritti "
              "correttamente. Utile subito dopo ogni caricamento su GitHub.")

    if not st.button("▶️ Avvia controllo", type="primary"):
        st.info("Premi «Avvia controllo» per verificare tutti i file.")
        return

    with st.spinner("Controllo in corso…"):
        n_ok, errori = _controlla_sintassi()
        imports = _controlla_import()

    tot = n_ok + len(errori)

    # ── Sintassi ──────────────────────────────────────────────────────
    st.markdown("##### 1. Scrittura del codice")
    if not errori:
        st.success(f"Tutti i {tot} file compilano correttamente.")
    else:
        st.error(f"{len(errori)} file su {tot} hanno un errore di scrittura.")
        for e in errori:
            st.markdown(f"**{e['file']}**"
                        + (f" — riga {e['riga']}" if e["riga"] else ""))
            st.caption(e["messaggio"])
            if e["testo"]:
                st.code(e["testo"], language="python")

    # ── Import ────────────────────────────────────────────────────────
    st.markdown("##### 2. Moduli principali")
    rotti = [(n, err) for n, err in imports if err]
    if not rotti:
        st.success(f"Tutti i {len(imports)} moduli principali si caricano.")
    else:
        st.error(f"{len(rotti)} moduli non si caricano — le loro schermate "
                 f"non si apriranno.")
        for nome, err in rotti:
            st.markdown(f"**{nome}**")
            st.caption(err)

    st.markdown("---")
    st.caption("Nota: questo controllo cattura gli errori di scrittura e di "
              "caricamento. Non cattura gli errori che compaiono solo usando "
              "una schermata (per esempio due pannelli annidati).")
