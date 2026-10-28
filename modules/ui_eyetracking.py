# -*- coding: utf-8 -*-
"""👁️ Eye tracking PNEV — esami con il Tobii EyeX (ponte PNEV Gaze Bridge) dentro il gestionale.

Prove: lettura, saccadi, saccadi su lettere, inseguimento, allenamento in tempo reale.
Gli esami finiscono nell'archivio comune degli esami strumentali (esami_strumentali.py).
"""
from __future__ import annotations

import datetime as dt
import json
import os

import streamlit as st

from . import esami_strumentali as es

STRUMENTO = "eyetracking"
CARTELLA_PONTE = "static_protocollo/eyetracking"

TIPI = {"lettura": "📖 Lettura", "saccadi": "↔️ Saccadi", "lettere": "🔤 Saccadi su lettere",
        "inseguimento": "〰️ Inseguimento", "allenamento": "🎯 Allenamento"}

# etichette e unità degli indici di sintesi, per tipo (l'ordine è quello di visualizzazione)
ETICHETTE = {
    "lettura": [("durata_lettura_s", "Tempo di lettura", "s", 1), ("parole_min", "Parole al minuto", "", 0),
                ("fissazioni", "Fissazioni", "", 0), ("fissazioni_riga", "Fissazioni per riga", "", 1),
                ("dur_media", "Durata media fissazioni", "ms", 0), ("dur_mediana", "Durata mediana", "ms", 0),
                ("dur_ds", "Deviazione standard", "ms", 0), ("saccadi_avanti", "Saccadi in avanti", "", 0),
                ("regressioni", "Regressioni", "", 0), ("regressioni_riga", "Regressioni per riga", "", 1),
                ("regr_su_fiss", "Regressioni / fissazioni", "%", 1), ("ampiezza_media_avanti", "Ampiezza media saccadi", "°", 1)],
    "saccadi": [("latenza_media", "Latenza media", "ms", 0), ("latenza_mediana", "Latenza mediana", "ms", 0),
                ("latenza_ds", "Deviazione standard", "ms", 0), ("guadagno_medio", "Guadagno medio", "", 2),
                ("ipometrie_pct", "Ipometrie", "%", 0), ("ipermetrie_pct", "Ipermetrie", "%", 0),
                ("correttive_medie", "Correttive per prova", "", 1), ("errore_finale", "Errore finale", "°", 1),
                ("valide", "Prove valide", "", 0), ("anticipate", "Anticipate", "", 0), ("mancate", "Mancate", "", 0)],
    "lettere": [("tempo_s", "Tempo", "s", 1), ("lettere_al_secondo", "Lettere al secondo", "", 2),
                ("lettere_guardate", "Lettere guardate", "", 0), ("fissazioni", "Fissazioni", "", 0),
                ("rifissazioni", "Rifissazioni", "", 0), ("errori_sequenza", "Errori di sequenza", "", 0),
                ("dur_media", "Durata media fissazioni", "ms", 0)],
    "inseguimento": [("guadagno_medio", "Guadagno medio", "", 2), ("saccadi_al_s", "Saccadi di recupero", "/s", 2),
                     ("errore_rms", "Errore medio (RMS)", "°", 1)],
    "allenamento": [("durata_s", "Durata", "s", 0), ("punti", "Punti", "", 0), ("mancati", "Mancati", "", 0),
                    ("tempo_sul_bersaglio", "Tempo sul bersaglio", "%", 0)],
}
# indici in cui un valore più alto è peggiore (per colorare il confronto)
PEGGIO_SE_ALTO = {"durata_lettura_s", "fissazioni", "fissazioni_riga", "dur_media", "dur_mediana", "regressioni",
                  "regressioni_riga", "regr_su_fiss", "latenza_media", "latenza_mediana", "latenza_ds", "ipometrie_pct",
                  "ipermetrie_pct", "correttive_medie", "errore_finale", "mancate", "anticipate", "tempo_s",
                  "rifissazioni", "errori_sequenza", "saccadi_al_s", "errore_rms", "mancati"}


def _num(v, dec=1):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "—"
    if f != f:
        return "—"
    return f"{f:.{dec}f}".replace(".", ",")


def _data(d):
    try:
        return (d if isinstance(d, dt.date) else dt.date.fromisoformat(str(d)[:10])).strftime("%d/%m/%Y")
    except Exception:
        return str(d or "")


def _nome_paziente(conn, paz_id) -> str:
    r = es._righe(conn, "SELECT cognome, nome FROM pazienti WHERE id=%s", (int(paz_id),))
    return f"{(r[0].get('cognome') or '').upper()} {(r[0].get('nome') or '').upper()}".strip() if r else ""


# ─────────────────────────── componente (la pagina dentro il gestionale) ───────────────────────────
_componente = None


def _app():
    global _componente
    if _componente is None:
        import streamlit.components.v1 as components
        _componente = components.declare_component(
            "eyetracking_pnev", path=os.path.join(os.path.dirname(__file__), "eyetracking_component"))
    return _componente


def _scheda_esegui(conn, paz_id, nome):
    st.caption("1) Avvia «Avvia ponte.bat» sul PC con la barra · 2) «Apri lo schermo paziente» e portalo sul monitor "
               "con la barra · 3) calibrazione fine · 4) scegli la prova. A fine prova premi **💾 Salva**.")
    k = f"et_ult_{paz_id}"
    msg = st.session_state.pop(f"et_msg_{paz_id}", None)
    if msg:
        st.success(msg)
    try:
        val = _app()(paziente=nome, salvato=st.session_state.get(k), key=f"et_{paz_id}", default=None)
    except Exception as e:
        st.error(f"La pagina dell'eye tracking non si è caricata: {e}")
        return
    if isinstance(val, dict) and val.get("azione") == "salva" and val.get("t") != st.session_state.get(k):
        st.session_state[k] = val.get("t")
        rec = val.get("record") or {}
        err = es.salva(conn, paz_id, rec)
        if err:
            st.error(f"Salvataggio non riuscito: {err}")
        else:
            st.session_state[f"et_msg_{paz_id}"] = (f"✓ {TIPI.get(rec.get('tipo'), 'Esame')} del {_data(rec.get('data'))} "
                                                    f"salvato nella scheda di {nome}. Lo trovi in «📋 Esami».")
            st.rerun()


# ─────────────────────────── elenco e dettaglio ───────────────────────────
def _metriche(tipo, sintesi):
    righe = [(et, f"{_num(sintesi.get(k), dec)}{(' ' + u) if u and u not in ('%', '°', '/s') else u}")
             for k, et, u, dec in ETICHETTE.get(tipo, []) if sintesi.get(k) is not None]
    if tipo == "inseguimento":
        for q in sintesi.get("per_frequenza") or []:
            righe.append((f"{_num(q.get('freq'))} Hz · guadagno", _num(q.get("guadagno"), 2)))
            righe.append((f"{_num(q.get('freq'))} Hz · saccadi/s", _num(q.get("saccadi_al_s"), 2)))
    for i in range(0, len(righe), 4):
        cols = st.columns(4)
        for c, (et, v) in zip(cols, righe[i:i + 4]):
            c.metric(et, v)


def _grafico(tipo, dati):
    """Un grafico essenziale per tipo (gli stessi della pagina, in versione statica)."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return
    S = dati.get("campioni") or []
    if not S:
        return
    t0 = S[0][0]
    fig, ax = plt.subplots(figsize=(9, 2.8))
    if tipo in ("saccadi", "inseguimento"):
        M = dati.get("meta") or {}
        ppd = M.get("ppd") or 1
        asse = 2 if M.get("direzione") == "vert" else 1
        cen = (M.get("h", 0) if asse == 2 else M.get("w", 0)) / 2
        ax.plot([(p[0] - t0) / 1000 for p in S], [(p[asse] - cen) / ppd for p in S], color="#1D6B44", lw=1, label="occhio")
        if tipo == "saccadi":
            st_ = dati.get("stim") or []
            xs, ys = [], []
            for i, q in enumerate(st_):
                v = ((q["x"] if asse == 1 else q["y"]) - cen) / ppd
                if i:
                    xs.append((q["t"] - t0) / 1000); ys.append(ys[-1])
                xs.append((q["t"] - t0) / 1000); ys.append(v)
            ax.plot(xs, ys, color="#B5461F", lw=1.6, label="bersaglio")
        ax.set_ylabel("posizione (°)")
        ax.legend(loc="upper right", fontsize=8)
    else:
        ax.plot([(p[0] - t0) / 1000 for p in S], [p[1] for p in S], color="#1D6B44", lw=1)
        ax.set_ylabel("posizione x (px)")
    ax.set_xlabel("tempo (s)")
    ax.grid(alpha=.25)
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)


def _scheda_esami(conn, paz_id):
    esami = es.elenco(conn, paz_id, STRUMENTO)
    if not esami:
        st.info("Nessun esame di eye tracking per questo paziente. Fanne uno nella scheda «👁️ Esegui».")
        return
    filtro = st.selectbox("Tipo", ["Tutti"] + [TIPI[t] for t in TIPI if any(e["tipo"] == t for e in esami)], key="et_filtro")
    lista = [e for e in esami if filtro == "Tutti" or TIPI.get(e["tipo"]) == filtro]
    scelta = st.selectbox("Esame", lista, key="et_sel",
                          format_func=lambda e: f"{_data(e['data_esame'])} · {TIPI.get(e['tipo'], e['tipo'])}")
    if not scelta:
        return
    _metriche(scelta["tipo"], scelta["sintesi"])
    with st.spinner("Carico il tracciato…"):
        d = es.dati(conn, scelta["id"])
    _grafico(scelta["tipo"], d)
    nuovo = st.text_area("Commento", value=scelta.get("commento") or "", key=f"et_comm_{scelta['id']}")
    c1, c2, c3 = st.columns(3)
    if c1.button("💾 Salva il commento", key=f"et_sc_{scelta['id']}"):
        err = es.aggiorna_commento(conn, scelta["id"], nuovo)
        st.success("Commento salvato.") if not err else st.error(err)
    c2.download_button("⬇️ Dati (JSON)", json.dumps({"strumento": STRUMENTO, "tipo": scelta["tipo"], "data": str(scelta["data_esame"]),
                                                    "sintesi": scelta["sintesi"], "dati": d}),
                       file_name=f"eyetracking_{scelta['tipo']}_{scelta['data_esame']}.json", mime="application/json",
                       key=f"et_dl_{scelta['id']}")
    if c3.button("🗑️ Elimina questo esame", key=f"et_del_{scelta['id']}"):
        st.session_state["et_conferma"] = scelta["id"]
    if st.session_state.get("et_conferma") == scelta["id"]:
        st.warning("Eliminare definitivamente questo esame?")
        a, b = st.columns(2)
        if a.button("Sì, elimina", key="et_si"):
            es.elimina(conn, scelta["id"]); st.session_state.pop("et_conferma", None); st.rerun()
        if b.button("No", key="et_no"):
            st.session_state.pop("et_conferma", None); st.rerun()


def _scheda_confronto(conn, paz_id):
    esami = es.elenco(conn, paz_id, STRUMENTO)
    tipi = [t for t in TIPI if sum(e["tipo"] == t for e in esami) >= 2]
    if not tipi:
        st.info("Servono almeno due esami dello stesso tipo per il confronto.")
        return
    tipo = st.selectbox("Prova", tipi, format_func=lambda t: TIPI[t], key="et_ct")
    lista = sorted([e for e in esami if e["tipo"] == tipo], key=lambda e: str(e["data_esame"]))
    fmt = lambda e: f"{_data(e['data_esame'])} (n. {lista.index(e) + 1})"
    c1, c2 = st.columns(2)
    a = c1.selectbox("Prima", lista, index=0, format_func=fmt, key="et_ca")
    b = c2.selectbox("Dopo", lista, index=len(lista) - 1, format_func=fmt, key="et_cb")
    righe = []
    for k, et, u, dec in ETICHETTE.get(tipo, []):
        va, vb = a["sintesi"].get(k), b["sintesi"].get(k)
        try:
            va, vb = float(va), float(vb)
        except (TypeError, ValueError):
            continue
        diff = (vb - va) / abs(va) * 100 if va else None
        meglio = None if diff is None or abs(diff) < 5 else ((diff < 0) == (k in PEGGIO_SE_ALTO))
        righe.append({"Indice": et, "Prima": f"{_num(va, dec)} {u}".strip(), "Dopo": f"{_num(vb, dec)} {u}".strip(),
                      "Variazione": "—" if diff is None else f"{'+' if diff > 0 else ''}{_num(diff, 0)} %",
                      "Esito": "" if meglio is None else ("🟢 migliorato" if meglio else "🔴 peggiorato")})
    import pandas as pd
    st.dataframe(pd.DataFrame(righe), use_container_width=True, hide_index=True)
    st.caption("🟢/🔴 solo per variazioni oltre il 5%. Confronta esami fatti con la stessa prova e le stesse impostazioni.")


def _scheda_carica(conn, paz_id):
    st.caption("Per gli esami fatti con la pagina fuori dal gestionale: premi «💾 Salva» (scarica un file) e caricalo qui.")
    f = st.file_uploader("File dell'esame (.json)", type=["json"], key="et_up")
    if f is not None:
        try:
            rec = json.loads(f.getvalue().decode("utf-8"))
        except Exception:
            st.error("File non leggibile.")
            return
        if rec.get("formato") != "pnev-esame" or rec.get("strumento") != STRUMENTO:
            st.error("Non è un file di esame eye tracking PNEV.")
            return
        st.write(f"**{TIPI.get(rec.get('tipo'), rec.get('tipo'))}** del {_data(rec.get('data'))} · nome nel file: {rec.get('paziente') or '—'}")
        if st.button("Salva nella scheda del paziente", type="primary", key="et_up_ok"):
            err = es.salva(conn, paz_id, rec)
            st.success("Esame salvato.") if not err else st.error(err)


def _file_ponte(nome="PNEV Gaze Bridge.zip"):
    for base in (CARTELLA_PONTE, os.path.join(os.path.dirname(__file__), "..", CARTELLA_PONTE)):
        p = os.path.join(base, nome)
        if os.path.exists(p):
            with open(p, "rb") as f:
                return f.read()
    return None


def _scheda_ponte():
    st.markdown("""
**Una volta per computer**
1. Installa il driver Tobii EyeX e calibra la barra.
2. Installa **Python a 32 bit** (python.org → Windows installer 32-bit, spunta «Add python.exe to PATH»).
3. Scarica il ponte qui sotto ed estrailo (per esempio sul desktop).

**Ogni volta**: doppio clic su **«Avvia ponte.bat»** e lascia aperta la finestra nera, che deve dire «Tobii EyeX: COLLEGATO».
""")
    g = _file_ponte("guida_eyetracking.pdf")
    if g:
        st.download_button("📘 Guida all'eye tracking (PDF)", g, file_name="Guida eye tracking PNEV.pdf", mime="application/pdf")
    z = _file_ponte()
    if z:
        st.download_button("⬇️ PNEV Gaze Bridge (ponte + pagina indipendente)", z, file_name="PNEV Gaze Bridge.zip", mime="application/zip")
    else:
        st.caption(f"Pacchetto del ponte non trovato in `{CARTELLA_PONTE}`.")
    st.caption("Con l'EyeX lo sguardo è uno solo (media dei due occhi): disparità, foria, convergenza e pupille "
               "restano nel programma Thomson.")


def render_eyetracking(conn=None, paz_id=None) -> None:
    st.header("👁️ Eye tracking PNEV")
    paz_id = paz_id or st.session_state.get("paziente_attivo_id")
    if conn is None:
        st.info("Connessione al database non disponibile.")
        return
    if not paz_id:
        st.info("Seleziona un paziente qui sopra.")
        return
    es.assicura_tabella(conn)
    nome = _nome_paziente(conn, paz_id) or f"Paziente {paz_id}"
    n = len(es.elenco(conn, paz_id, STRUMENTO))
    t = st.tabs(["👁️ Esegui", f"📋 Esami ({n})", "📈 Confronto", "📥 Carica file", "⚙️ Ponte e guida", "🎥 Webcam e importazione"])
    with t[0]:
        _scheda_esegui(conn, paz_id, nome)
    with t[1]:
        _scheda_esami(conn, paz_id)
    with t[2]:
        _scheda_confronto(conn, paz_id)
    with t[3]:
        _scheda_carica(conn, paz_id)
    with t[4]:
        _scheda_ponte()
    with t[5]:
        try:
            from .sections.ui_cliniche import render_gaze_section
            render_gaze_section()
        except Exception as e:
            st.info(f"Strumenti webcam non disponibili: {e}")
