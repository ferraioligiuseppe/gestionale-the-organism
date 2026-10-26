# -*- coding: utf-8 -*-
"""Stato del sito pnev.it — legge il resoconto del plugin «PNEV Stato del sito».

Il plugin (pnev-stato.php, installato su WordPress) espone in SOLA LETTURA:
file HTML/JS in uploads (offuscati, in chiaro, vuoti, dove sono usati),
lettore MAPS in uso, plugin da aggiornare, punti di sicurezza.
Nessun dato di pazienti.

Secrets (Streamlit → Settings → Secrets), sezione già esistente:

    [pnev_wp]
    base_url  = "https://www.pnev.it"
    stato_key = "la chiave mostrata in WordPress → Strumenti → PNEV Stato del sito"
"""
from __future__ import annotations

import streamlit as st


def _config() -> tuple[str, str]:
    try:
        cfg = dict(st.secrets.get("pnev_wp", {}))
    except Exception:
        cfg = {}
    return (str(cfg.get("base_url") or "https://www.pnev.it").rstrip("/"), str(cfg.get("stato_key") or ""))


@st.cache_data(ttl=300, show_spinner="Leggo lo stato del sito…")
def _scarica(base: str, chiave: str) -> dict:
    import requests
    ultimo = {"errore": "il sito non risponde"}
    for url in (f"{base}/wp-json/pnev/v1/stato", f"{base}/?rest_route=/pnev/v1/stato"):
        try:
            r = requests.get(url, params={"chiave": chiave}, timeout=40,
                             headers={"User-Agent": "GestionaleTheOrganism/1.0"})
        except Exception as e:
            ultimo = {"errore": f"il sito non risponde ({e.__class__.__name__})"}
            continue
        if r.status_code == 403:
            return {"errore": "chiave non accettata: controlla stato_key nei Secrets"}
        if r.status_code == 200:
            try:
                return r.json()
            except Exception:
                ultimo = {"errore": "risposta non valida dal sito"}
                continue
        ultimo = {"errore": f"il sito ha risposto {r.status_code}: il plugin «PNEV Stato del sito» è attivo?"}
    return ultimo


def _semaforo(ok: bool, avviso: bool = False) -> str:
    return "🟢" if ok else ("🟡" if avviso else "🔴")


def render_stato_sito(conn=None) -> None:
    st.header("🩺 Stato del sito pnev.it")
    try:
        from .app_core import is_admin
        if not is_admin():
            st.info("Pagina riservata agli amministratori.")
            return
    except Exception:
        pass
    base, chiave = _config()
    if not chiave:
        st.warning("Manca la chiave. In WordPress apri **Strumenti → PNEV Stato del sito**, copia la chiave "
                   "e aggiungila nei Secrets del gestionale, nella sezione `[pnev_wp]`, come `stato_key = \"…\"`.")
        return
    c1, c2 = st.columns([1, 3])
    if c1.button("🔄 Aggiorna adesso"):
        _scarica.clear()
    c2.caption("Resoconto in sola lettura, aggiornato al massimo ogni 5 minuti. Non contiene dati di pazienti.")
    r = _scarica(base, chiave)
    if r.get("errore"):
        st.error(f"Non riesco a leggere lo stato del sito: {r['errore']}.")
        return

    v, s, n = r.get("versioni", {}), r.get("sicurezza", {}), r.get("riepilogo", {})
    st.caption(f"Generato il {r.get('generato_il', '')} · WordPress {v.get('wordpress', '?')} · "
               f"PHP {v.get('php', '?')} · tema {v.get('tema', '?')}"
               + (f" (base {v['tema_padre']})" if v.get("tema_padre") else ""))

    m = st.columns(5)
    m[0].metric("File offuscati", n.get("offuscato", 0))
    m[1].metric("In chiaro", n.get("in_chiaro", 0))
    m[2].metric("Vuoti (rotti)", n.get("vuoto", 0))
    m[3].metric("Non usati", n.get("non_usati", 0))
    m[4].metric("Plugin da aggiornare", n.get("plugin_da_aggiornare", 0))

    st.subheader("Sicurezza")
    archivi = s.get("archivi_in_uploads") or []
    php_up = s.get("php_in_uploads") or []
    righe = [
        (_semaforo(not s.get("php_vecchio")), f"PHP {v.get('php', '?')}",
         "da aggiornare a 8.2/8.3 (Rossi Web)" if s.get("php_vecchio") else "aggiornato"),
        (_semaforo(not s.get("wp_file_manager_attivo"), True), "WP File Manager",
         "attivo: disattivalo quando non serve" if s.get("wp_file_manager_attivo") else "non attivo"),
        (_semaforo(not php_up), "File PHP in uploads", ", ".join(php_up) if php_up else "nessuno"),
        (_semaforo(not archivi), "Archivi (zip/sql) in uploads",
         ", ".join(f"{a['file']} ({a['kb']} KB)" for a in archivi) if archivi else "nessuno"),
        (_semaforo(not s.get("debug_attivo"), True), "Modalità debug", "attiva" if s.get("debug_attivo") else "spenta"),
    ]
    for sem, cosa, dett in righe:
        st.markdown(f"{sem} **{cosa}** — {dett}")

    maps = r.get("lettore_maps") or []
    if maps:
        st.subheader("Lettore MAPS")
        import pandas as pd
        df = pd.DataFrame(maps).rename(columns={"file": "File", "stato": "Stato", "lezioni": "Lezioni che lo usano",
                                                 "usi_totali": "Usi totali"})
        st.dataframe(df.sort_values("Lezioni che lo usano", ascending=False), use_container_width=True, hide_index=True)
        in_uso = [x["file"] for x in maps if x.get("lezioni")]
        if in_uso:
            st.caption("In uso nelle lezioni: " + ", ".join(in_uso) + ". Le altre versioni si possono cancellare.")

    st.subheader("File HTML e JS in uploads")
    import pandas as pd
    filtro = st.radio("Mostra", ["Da sistemare", "Non usati", "Tutti"], horizontal=True, key="stato_sito_filtro")
    fl = r.get("file") or []
    if filtro == "Da sistemare":
        fl = [f for f in fl if f.get("stato") != "offuscato"]
    elif filtro == "Non usati":
        fl = [f for f in fl if not f.get("usato_in")]
    etichetta = {"offuscato": "🟢 offuscato", "in_chiaro": "🔴 in chiaro", "vuoto": "🔴 vuoto"}
    df = pd.DataFrame([{"File": f["file"], "Stato": etichetta.get(f["stato"], f["stato"]), "KB": f["kb"],
                        "Modificato": f["modificato"],
                        "Usato in": " ; ".join(f.get("usato_in") or []) or "— non usato"} for f in fl])
    if df.empty:
        st.success("Niente da sistemare. 🎉")
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)

    with st.expander("Plugin installati"):
        pl = r.get("plugin") or []
        st.dataframe(pd.DataFrame([{"Plugin": p["nome"], "Versione": p["versione"], "Attivo": "sì" if p["attivo"] else "no",
                                    "Aggiornamento": p.get("aggiornamento") or ""} for p in pl]),
                     use_container_width=True, hide_index=True)
