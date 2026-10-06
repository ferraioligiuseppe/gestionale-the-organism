# -*- coding: utf-8 -*-
"""Fascicolo del paziente: tutto quello che il gestionale sa di una persona.

Perche' esiste
--------------
Ogni modulo salva nella sua tabella. La Diagnosi assistita e il Quadro
storico leggevano un elenco di tabelle scritto a mano, fermo a quando sono
nati: INPP, anamnesi unica, rilievi, colloqui, TMR, stimolazione visiva,
alimentazione, Buteyko, prismi, NPS, WHODAS, osteopatia, PECS, audiometrie…
restavano fuori. Ogni modulo nuovo era un'isola.

Qui l'elenco non e' scritto a mano: si chiede al database quali tabelle
hanno una colonna paziente_id, e si conta cosa c'e' per quel paziente. Un
modulo aggiunto domani compare da solo. I nomi leggibili e il collegamento
al menu sono in ETICHETTE: una tabella non elencata compare col suo nome.
"""
from __future__ import annotations

import datetime as dt

import streamlit as st

# tabella → (nome leggibile, voce di menu da aprire o None)
ETICHETTE = {
    "anamnesi_prima_infanzia": ("Anamnesi (gravidanza, prima infanzia)", "📋 Anamnesi PNEV"),
    "anamnesi_sviluppo": ("Anamnesi (dopo i 2 anni)", "📋 Anamnesi PNEV"),
    "anamnesi": ("Anamnesi PNEV (vecchia)", "📋 Anamnesi PNEV"),
    "inpp_valutazioni": ("INPP — riflessi e sviluppo neurologico", "🧬 INPP — Valutazione diagnostica"),
    "valutazioni_visive": ("Valutazione visuo-percettiva", "👁️ Valutazione visuo-percettiva"),
    "dem_risultati": ("DEM", "🔢 DEM interattivo"),
    "getman_risultati": ("Getman", None),
    "groffman_risultati": ("Groffman", None),
    "audiometrie_tonali": ("Audiometria tonale", "📊 Audiometria funzionale"),
    "functional_audiograms": ("Audiometria funzionale", "📊 Audiometria funzionale"),
    "external_orl_audiograms": ("Audiogrammi ORL esterni", None),
    "screening_uditivo_pnev": ("Screening uditivo", None),
    "screening_cuffie_pnev": ("Screening con cuffie", None),
    "logopedia_valutazioni": ("Logopedia — valutazioni", "🗣️ Logopedia / SMOF"),
    "logopedia_sedute": ("Logopedia — sedute", "🗣️ Logopedia / SMOF"),
    "logopedia_obiettivi": ("Logopedia — obiettivi", "🗣️ Logopedia / SMOF"),
    "nps_valutazioni": ("NPS — neuropsicologica", None),
    "whodas_somministrazioni": ("WHODAS 2.0", None),
    "pvb_schede": ("Scheda PVB", None),
    "prismi_posturali": ("Prismi posturali", None),
    "rilievi_pnev": ("Rilievi PNEV", "🧩 Rilievi PNEV"),
    "colloqui_clinici": ("Colloqui clinici", None),
    "documenti_clinici": ("Documenti clinici", "📎 Documenti clinici"),
    "diario_clinico": ("Diario clinico", "🗓️ Diario clinico"),
    "esiti_pnev": ("Esiti / follow-up", "📈 Esiti / Follow-up"),
    "terapia_sedute": ("Sedute di terapia", "📅 Sedute / Terapie"),
    "terapia_obiettivi": ("Obiettivi di terapia", None),
    "terapia_programma": ("Programma PNEV", "🧩 Programma PNEV"),
    "piani_vt": ("Piano Vision Therapy", "🎯 Piano Vision Therapy"),
    "tmr_programmi": ("TMR — movimenti ritmici", "🎵 TMR — Movimenti ritmici"),
    "vis_programmi": ("Stimolazione visiva a casa", "👁️ Stimolazione visiva a casa"),
    "pnev_casa": ("Programma PNEV a casa", "🏠 Programma PNEV a casa"),
    "ascolti_maps": ("Ascolti MAPS", None),
    "buteyko_diario": ("Buteyko — diario", None),
    "alim_valutazione": ("Alimentazione — valutazione", None),
    "alim_esami": ("Alimentazione — esami", None),
    "alim_piano": ("Alimentazione — piano", None),
    "alim_diario": ("Alimentazione — diario", None),
    "osteo_anamnesi": ("Osteopatia — anamnesi", None),
    "osteo_seduta": ("Osteopatia — sedute", None),
    "pecs_sessioni": ("PECS — sessioni", None),
    "contattologia_progetti": ("Contattologia — progetti LAC", None),
    "gaze_sessions": ("Eye tracking", None),
    "reading_sessions": ("Lettura (eye tracking)", None),
    "photoref_sessions": ("Fotorefrazione", None),
    "questionari_pubblici": ("Questionari compilati", None),
    "diagnosi_assistita": ("Diagnosi salvate", "📝 Diagnosi assistita"),
    "relazioni_cliniche": ("Relazioni cliniche", None),
    "consensi_privacy": ("Consensi privacy", "🔒 Privacy & Consensi"),
}

# Tecniche, amministrative o figlie di un'altra tabella: non sono clinica.
_ESCLUSE_PAROLE = ("storico", "_log", "log_", "token", "otp", "cache", "audit", "auth_",
                   "samples", "_points", "schede_aperte", "privacy_richieste", "portale_accessi",
                   "magic", "registrazioni_ip", "lead_", "aerosal_", "crediti", "coupons",
                   "ev_", "cf_", "studi", "abbonamenti", "utenti_meta", "pagamenti", "captures",
                   "pubblico_", "public_tokens", "presenza", "calibraz", "gc_")

# Gia' riassunte per esteso dalla Diagnosi assistita: non le ripetiamo in forma generica.
GIA_RIASSUNTE = {"documenti_clinici", "getman_risultati", "groffman_risultati", "valutazioni_visive",
                 "anamnesi", "esiti_pnev", "logopedia_valutazioni", "logopedia_sedute",
                 "logopedia_obiettivi", "terapia_sedute", "terapia_obiettivi", "terapia_programma",
                 "anamnesi_prima_infanzia", "anamnesi_sviluppo", "inpp_valutazioni", "rilievi_pnev",
                 "colloqui_clinici", "diagnosi_assistita", "consensi_privacy", "pnev_casa",
                 "relazioni_cliniche"}

_DATE_PREFERITE = ("data", "data_valutazione", "data_seduta", "data_esame", "data_ora", "data_anamnesi",
                   "creato_il", "creata_il", "created_at", "aggiornato_il", "updated_at", "inizio")
_COLONNE_TECNICHE = {"id", "paziente_id", "created_by", "updated_by", "creato_da", "aggiornato_da",
                     "created_at", "updated_at", "creato_il", "aggiornato_il", "token", "token_hash"}


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


def _tabelle(conn):
    """{tabella: colonna_data} di tutte le tabelle cliniche con paziente_id."""
    if "_fascicolo_tabelle" in st.session_state:
        return st.session_state["_fascicolo_tabelle"]
    righe = _q(conn,
        "SELECT table_name, column_name, data_type FROM information_schema.columns "
        "WHERE table_schema='public' AND table_name IN ("
        " SELECT table_name FROM information_schema.columns "
        " WHERE table_schema='public' AND column_name='paziente_id')")
    col = {}
    for r in righe:
        col.setdefault(r["table_name"], []).append((r["column_name"], r["data_type"]))
    out = {}
    for t, cc in col.items():
        if t != "pazienti" and any(p in t for p in _ESCLUSE_PAROLE) and t not in ETICHETTE:
            continue
        if t == "pazienti":
            continue
        date = [c for c, ty in cc if "date" in ty or "timestamp" in ty]
        scelta = next((c for c in _DATE_PREFERITE if c in date), date[0] if date else None)
        out[t] = scelta
    st.session_state["_fascicolo_tabelle"] = out
    return out


def riepilogo(conn, paz_id, forza=False):
    """[{tabella, nome, voce, n, ultima}] solo per le tabelle con dati."""
    k = f"_fascicolo_{paz_id}"
    if not forza and k in st.session_state:
        return st.session_state[k]
    out = []
    for t, dcol in sorted(_tabelle(conn).items()):
        sel = f"COUNT(*) AS n" + (f", MAX({dcol}) AS ultima" if dcol else "")
        r = _q(conn, f'SELECT {sel} FROM "{t}" WHERE paziente_id=%s', (int(paz_id),))
        n = int((r[0].get("n") if r else 0) or 0)
        if not n:
            continue
        nome, voce = ETICHETTE.get(t, (t.replace("_", " ").capitalize(), None))
        out.append({"tabella": t, "nome": nome, "voce": voce, "n": n,
                    "ultima": (r[0].get("ultima") if r else None)})
    out.sort(key=lambda x: str(x["ultima"] or ""), reverse=True)
    st.session_state[k] = out
    return out


def _area_di(voce):
    """L'area del menu che contiene una voce (per il collegamento)."""
    try:
        from . import app_menu as m
    except Exception:
        return None

    def cerca(obj):
        if isinstance(obj, str):
            return obj == voce
        if isinstance(obj, dict):
            return any(cerca(v) for v in obj.values())
        if isinstance(obj, (list, tuple)):
            return any(cerca(v) for v in obj)
        return False
    for nome in ("SOTTOSEZIONI", "RAMI_PER_AREA"):
        d = getattr(m, nome, None)
        if isinstance(d, dict):
            for area, contenuto in d.items():
                if cerca(contenuto):
                    return area
    return None


def _fmt(v):
    if hasattr(v, "strftime"):
        return v.strftime("%d/%m/%Y")
    return str(v)[:10] if v else "—"


def render_fascicolo(conn, paz_id, chiave="fasc", aperto=False):
    """Il riquadro «tutto quello che c'e' per questo paziente», con i collegamenti."""
    if conn is None or not paz_id:
        return
    righe = riepilogo(conn, paz_id)
    with st.expander(f"📂 Fascicolo: tutto quello che c'è per questo paziente ({len(righe)} moduli)",
                     expanded=aperto):
        if not righe:
            st.caption("Ancora nessun dato salvato per questo paziente.")
        for i, r in enumerate(righe):
            a, b = st.columns([5, 1])
            a.markdown(f"**{r['nome']}** · {r['n']} {'voce' if r['n'] == 1 else 'voci'} · "
                       f"ultima {_fmt(r['ultima'])}")
            area = _area_di(r["voce"]) if r["voce"] else None
            if area and b.button("Apri", key=f"{chiave}_{i}_{r['tabella']}", use_container_width=True):
                st.session_state["goto_area"] = area
                st.session_state["goto_sotto"] = r["voce"]
                st.session_state["paziente_attivo_id"] = paz_id
                st.rerun()
        if st.button("🔄 Aggiorna", key=f"{chiave}_agg"):
            st.session_state.pop("_fascicolo_tabelle", None)
            riepilogo(conn, paz_id, forza=True)
            st.rerun()


def _valore(v):
    if v is None or v == "" or isinstance(v, (bytes, bytearray, memoryview)):
        return None
    if hasattr(v, "strftime"):
        return v.strftime("%d/%m/%Y")
    s = " ".join(str(v).split())
    if s in ("{}", "[]", "None", "null"):
        return None
    return s[:300] + ("…" if len(s) > 300 else "")


def testo_altri_dati(conn, paz_id, max_char=7000) -> list[str]:
    """Per la Diagnosi: le tabelle non gia' riassunte, in forma generica
    (ultime 3 voci, colonne non tecniche), cosi' nessun modulo resta fuori."""
    out, tot = [], 0
    tab = _tabelle(conn)
    for r in riepilogo(conn, paz_id):
        t = r["tabella"]
        if t in GIA_RIASSUNTE:
            continue
        dcol = tab.get(t)
        righe = _q(conn, f'SELECT * FROM "{t}" WHERE paziente_id=%s'
                         + (f" ORDER BY {dcol} DESC NULLS LAST" if dcol else "") + " LIMIT 3", (int(paz_id),))
        if not righe:
            continue
        blocco = [f"{r['nome'].upper()} ({r['n']} in tutto, ultime {len(righe)}):"]
        for x in righe:
            campi = [f"{k}: {_valore(v)}" for k, v in x.items()
                     if k.lower() not in _COLONNE_TECNICHE and _valore(v) is not None]
            if campi:
                blocco.append("- " + " · ".join(campi))
        testo = "\n".join(blocco)
        if tot + len(testo) > max_char:
            out.append(f"(altri moduli con dati: {', '.join(x['nome'] for x in riepilogo(conn, paz_id) if x['tabella'] not in GIA_RIASSUNTE and x['nome'] not in ' '.join(out))})")
            break
        out.append(testo)
        tot += len(testo)
    return out
