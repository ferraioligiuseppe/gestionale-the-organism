# -*- coding: utf-8 -*-
"""
modules/pnev_gamecenter/ui_gamecenter.py

Interfaccia del PNEV Game Center dentro il gestionale.

Tre sezioni:
  1) Apri un gioco  -> link ai giochi su pnev.it, con paziente in coda all'URL
  2) Salva risultato -> incolli il testo di "Copia risultati" del gioco e lo salvi
                        nella cartella (parsato in metriche JSONB)
  3) Storico         -> le partite del paziente, con le metriche e l'eliminazione

Aggancio nel router del gestionale (come gli altri moduli):
    from modules.pnev_gamecenter.ui_gamecenter import ui_gamecenter
    ui_gamecenter(conn=get_connection(), paziente_id=paz_id, paziente_nome=paz_nome)

Se paziente_id non viene passato, la UI mostra un campo per inserirlo (fallback).
"""

import streamlit as st

try:
    from zoneinfo import ZoneInfo
    _TZ = ZoneInfo("Europe/Rome")
except Exception:
    _TZ = None

try:
    from .db_gamecenter import (
        init_gamecenter_db, salva_sessione, lista_sessioni_paziente,
        elimina_sessione, GIOCHI,
    )
except Exception:  # se importato in modo assoluto
    from modules.pnev_gamecenter.db_gamecenter import (
        init_gamecenter_db, salva_sessione, lista_sessioni_paziente,
        elimina_sessione, GIOCHI,
    )

try:
    from modules.app_core import get_connection
except Exception:
    get_connection = None

# URL base dove hai caricato i giochi su pnev.it. Adegua se la cartella è diversa.
GIOCHI_BASE_URL = "https://www.pnev.it/wp-content/uploads/giochi"

# Ordine di presentazione dei giochi
ORDINE = ["gonogo", "talpa", "coppie", "palloncini", "labirinto"]

# slug -> file html su pnev.it
FILE_GIOCO = {
    "gonogo": "gonogo.html",
    "talpa": "acchiappatalpa.html",
    "coppie": "trovacoppie.html",
    "palloncini": "palloncini.html",
    "labirinto": "labirinto.html",
}


# ---------------------------------------------------------------- parsing incolla
def rileva_gioco(testo):
    """Riconosce lo slug del gioco dal testo incollato."""
    t = (testo or "").lower()
    if "go/no-go" in t or "premi o fermati" in t:
        return "gonogo"
    if "acchiappa la talpa" in t:
        return "talpa"
    if "trova le coppie" in t:
        return "coppie"
    if "palloncini" in t:
        return "palloncini"
    if "labirinto" in t:
        return "labirinto"
    return None


def parse_incolla(testo):
    """
    Trasforma il testo 'Copia risultati' in (metriche:dict, modalita:str|None).
    Ogni riga 'Chiave: Valore' diventa una voce; la riga di modalità
    (Difficoltà/Velocità/Livello/Modalità) viene usata anche come 'modalita'.
    """
    metriche = {}
    modalita = None
    righe = [r.strip() for r in (testo or "").splitlines() if r.strip()]
    for r in righe:
        if r.lower().startswith("pnev game center"):
            continue
        if ":" not in r:
            continue
        k, v = r.split(":", 1)
        k = k.strip()
        v = v.strip()
        if not k:
            continue
        metriche[k] = v
        kl = k.lower()
        if modalita is None and (kl.startswith("difficolt") or kl.startswith("velocit")
                                 or kl.startswith("livello") or kl.startswith("modalit")):
            modalita = v
    return metriche, modalita


def _fmt_data(dt):
    if dt is None:
        return ""
    try:
        if _TZ is not None and dt.tzinfo is not None:
            dt = dt.astimezone(_TZ)
        return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return str(dt)


# ---------------------------------------------------------------- sezioni UI
def _sezione_apri(paziente_id, paziente_nome):
    st.write("Apri un gioco in una nuova scheda. Fai giocare il bambino, poi torna qui "
             "e usa **Salva risultato** per incollare l'esito nella cartella.")
    suffix = ""
    if paziente_id:
        suffix = f"?paz={int(paziente_id)}"
        if paziente_nome:
            try:
                from urllib.parse import quote
                suffix += "&nome=" + quote(str(paziente_nome))
            except Exception:
                pass
    cols = st.columns(2)
    for i, slug in enumerate(ORDINE):
        info = GIOCHI.get(slug, {"nome": slug, "categoria": ""})
        url = f"{GIOCHI_BASE_URL}/{FILE_GIOCO.get(slug, slug + '.html')}{suffix}"
        with cols[i % 2]:
            try:
                st.link_button(f"▶ {info['nome']}", url, use_container_width=True)
            except Exception:
                st.markdown(f"- [{info['nome']}]({url})")
            st.caption(info.get("categoria", ""))


def _sezione_salva(conn, paziente_id):
    st.write("Incolla qui il testo copiato dal gioco (pulsante **Copia risultati**).")
    testo = st.text_area("Risultato del gioco", height=180, key="gc_incolla",
                         placeholder="PNEV Game Center — ...")
    if testo and testo.strip():
        slug = rileva_gioco(testo)
        metriche, modalita = parse_incolla(testo)
        if slug is None:
            st.warning("Non riconosco il gioco dal testo. Controlla di aver incollato tutto.")
        else:
            nome = GIOCHI.get(slug, {}).get("nome", slug)
            st.success(f"Rilevato: **{nome}**" + (f" · {modalita}" if modalita else ""))
            if metriche:
                st.table([{"Voce": k, "Valore": v} for k, v in metriche.items()])
        note = st.text_input("Nota (facoltativa)", key="gc_nota")
        disabilita = slug is None or not paziente_id
        if st.button("💾 Salva nella cartella", type="primary", disabled=disabilita):
            try:
                new_id = salva_sessione(
                    conn, paziente_id=int(paziente_id), gioco=slug,
                    modalita=modalita, metriche=metriche,
                    sintesi=testo.strip(), note=(note or None),
                )
                st.success(f"Salvato nella cartella (sessione #{new_id}).")
                st.session_state.pop("gc_incolla", None)
                st.session_state.pop("gc_nota", None)
                st.rerun()
            except Exception as e:
                st.error(f"Errore nel salvataggio: {e}")


def _sezione_storico(conn, paziente_id):
    if not paziente_id:
        st.info("Seleziona un paziente per vedere lo storico.")
        return
    try:
        righe = lista_sessioni_paziente(conn, int(paziente_id))
    except Exception as e:
        st.error(f"Errore nel leggere lo storico: {e}")
        return
    if not righe:
        st.info("Ancora nessuna partita salvata per questo paziente.")
        return
    st.caption(f"{len(righe)} partite salvate")
    for r in righe:
        nome = r["gioco_nome"] or GIOCHI.get(r["gioco"], {}).get("nome", r["gioco"])
        data = _fmt_data(r["creato_il"])
        modal = f" · {r['modalita']}" if r["modalita"] else ""
        with st.expander(f"{data} — {nome}{modal}"):
            metr = r["metriche"] or {}
            if isinstance(metr, dict) and metr:
                st.table([{"Voce": k, "Valore": v} for k, v in metr.items()])
            elif r["sintesi"]:
                st.code(r["sintesi"])
            if r["note"]:
                st.caption(f"Nota: {r['note']}")
            if st.button("🗑️ Elimina", key=f"gc_del_{r['id']}"):
                try:
                    elimina_sessione(conn, int(r["id"]))
                    st.rerun()
                except Exception as e:
                    st.error(f"Errore: {e}")


# ---------------------------------------------------------------- entry point
def ui_gamecenter(conn=None, paziente_id=None, paziente_nome=None):
    st.header("🎮 PNEV Game Center")

    if conn is None:
        if get_connection is None:
            st.error("Connessione al database non disponibile.")
            return
        conn = get_connection()

    try:
        init_gamecenter_db(conn)
    except Exception as e:
        st.warning(f"Inizializzazione Game Center: {e}")

    if paziente_id is None:
        paziente_id = st.number_input("ID paziente", min_value=1, step=1, value=1)
        st.caption("In produzione questo id arriva dal paziente selezionato nel gestionale "
                   "(passa paziente_id a ui_gamecenter, come per gli altri moduli).")
    else:
        st.caption(f"Paziente: {paziente_nome or ''} (id {int(paziente_id)})")

    t_apri, t_salva, t_storico = st.tabs(["▶️ Apri un gioco", "📋 Salva risultato", "🕓 Storico"])
    with t_apri:
        _sezione_apri(paziente_id, paziente_nome)
    with t_salva:
        _sezione_salva(conn, paziente_id)
    with t_storico:
        _sezione_storico(conn, paziente_id)
