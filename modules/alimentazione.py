# -*- coding: utf-8 -*-
"""Alimentazione — metodo Kousmine.

Cinque schede per paziente:
  1 Valutazione   abitudini, selettivita', intestino, pH, misure di partenza
  2 Esami         pannelli di laboratorio (es. Dott.ssa Scarpa), lettura AI del referto
  3 Piano         i quattro pilastri, crema Budwig, introduzione graduale, firma
  4 Diario        una riga al giorno: Budwig, pH, intestino, sonno, nota
  5 Esiti         stesse misure a settimana 0, 5, 12 ed esami di controllo

Il piano alimentare e l'integrazione vanno firmati da medico, biologo
nutrizionista o dietista: senza firma il PDF per la famiglia non si stampa.
"""
from __future__ import annotations

import datetime
import io
import json
import re

import streamlit as st

_NO = "—"

PANNELLI = {
    "Dott.ssa Chiarina Scarpa — neurosviluppo": [
        ("🦠 Sierologie virali", [
            "Varicella zoster IgG", "Varicella zoster IgM", "Morbillo IgG", "Morbillo IgM",
            "Epstein-Barr VCA IgG", "Epstein-Barr VCA IgM", "Epstein-Barr EBNA", "Epstein-Barr EA"]),
        ("🧫 Streptococco", ["TAS", "Anticorpi anti-DNasi"]),
        ("🔥 Infiammazione e immunità", [
            "Emocromo con formula e piastrine", "VES", "IL-2", "IL-6", "TNF-α", "IgG", "IgA", "IgE"]),
        ("⚡ Stress ossidativo", ["d-ROMs test"]),
        ("🧬 Vitamine e metilazione", [
            "Vitamina D", "Vitamina B12", "Acido folico", "Omocisteina", "Mutazioni MTHFR"]),
        ("🌀 Intestino e istamina", [
            "DAO (diamino-ossidasi)", "Istamina", "Esame parassitologico delle feci",
            "Candida nelle feci (3 campioni a giorni alterni)", "Recaller test"]),
    ],
}
# Proposta: si ripetono al controllo. Modificabile esame per esame.
RIPETERE = {"Vitamina D", "IL-6", "d-ROMs test", "Omocisteina", "VES"}

ABITUDINI = [
    ("colazione", "Colazione", ["latte e biscotti", "merendine / cereali zuccherati", "pane e marmellata",
                                "yogurt e frutta", "crema Budwig", "salta la colazione"]),
    ("raffinati", "Cereali raffinati (pane, pasta bianca)", ["meno di 1 volta al giorno", "1 volta al giorno",
                                                             "2 o più volte al giorno"]),
    ("zuccheri", "Zuccheri e dolci", ["raramente", "qualche volta a settimana", "ogni giorno"]),
    ("bevande", "Bevande zuccherate", ["mai", "qualche volta a settimana", "ogni giorno"]),
    ("verdura_cruda", "Verdura cruda", ["quasi mai", "qualche volta a settimana", "ogni giorno"]),
    ("legumi", "Legumi", ["meno di 1 volta a settimana", "1–2 volte a settimana", "3 o più volte"]),
    ("oli", "Oli spremuti a freddo", ["no", "a volte", "ogni giorno"]),
]
INTESTINO = [
    ("evacuazione", "Evacuazione", ["ogni giorno", "ogni 2–3 giorni", "meno di 2 volte a settimana"]),
    ("feci", "Consistenza delle feci", ["normali", "dure", "molli / diarroiche", "alternate"]),
    ("gonfiore", "Gonfiore o dolore addominale", ["mai", "qualche volta", "spesso"]),
    ("acqua", "Acqua al giorno", ["meno di 1 litro", "1–1,5 litri", "più di 1,5 litri"]),
    ("antibiotici", "Antibiotici nell'ultimo anno", ["nessuno", "1 ciclo", "2 cicli", "3 o più"]),
]
RIFIUTI = ["consistenza", "colore", "odore", "temperatura", "alimenti misti", "novità"]

PILASTRI = [
    ("Pilastro 1", "Alimentazione", [
        ("p1_budwig", "Colazione con crema Budwig"),
        ("p1_integrali", "Cereali integrali al posto dei raffinati, uno per pasto"),
        ("p1_crudo", "Verdura cruda a inizio pasto, anche poca"),
        ("p1_olio", "Olio di lino o girasole spremuto a freddo, crudo"),
        ("p1_zucchero", "Zucchero e dolci industriali: solo nei giorni di festa"),
    ]),
    ("Pilastro 2", "Igiene intestinale", [
        ("p2_acqua", "Acqua: 1,2 litri al giorno"),
        ("p2_fibre", "Fibre da legumi, frutta e verdura"),
        ("p2_orario", "Orario fisso per il bagno dopo colazione"),
        ("p2_movimento", "Movimento all'aperto ogni giorno"),
    ]),
    ("Pilastro 3", "Equilibrio acido-base", [
        ("p3_ph", "pH urine ogni mattina, annotato nel diario"),
        ("p3_verdure", "Più verdura e frutta, meno carne e formaggi stagionati"),
        ("p3_cena", "Cena leggera"),
    ]),
    ("Pilastro 4", "Integrazione", [
        ("p4_controllo", "Controllo a 5 settimane prima di proseguire"),
    ]),
]
BUDWIG = [
    {"Ingrediente": "Yogurt bianco intero (o ricotta)", "Quantità": "4 cucchiai"},
    {"Ingrediente": "Olio di lino spremuto a freddo", "Quantità": "1 cucchiaino"},
    {"Ingrediente": "Banana schiacciata", "Quantità": "½"},
    {"Ingrediente": "Succo di limone", "Quantità": "qualche goccia"},
    {"Ingrediente": "Cereale integrale crudo macinato al momento", "Quantità": "1 cucchiaio"},
    {"Ingrediente": "Semi oleosi macinati (mandorle, noci)", "Quantità": "1 cucchiaino"},
    {"Ingrediente": "Frutta di stagione a pezzi", "Quantità": "a piacere"},
]
GRADINI = ("Settimane 1–2: solo ciò che accetta già, più l'olio.\n"
           "Settimane 3–4: si aggiunge il cereale, macinato fine.\n"
           "Settimane 5–6: semi oleosi.\n"
           "Settimane 7–8: frutta a pezzi.")
QUALIFICHE = ["Medico", "Biologo nutrizionista", "Dietista"]
MISURE = ["Scala comportamentale (punteggio totale)", "Alimenti accettati", "Evacuazioni a settimana",
          "pH urine, media", "Risvegli notturni a settimana"]
SETTIMANE = [0, 5, 12]


# ── Database ──────────────────────────────────────────────────────────

def _assicura_tabelle(conn) -> None:
    if st.session_state.get("_alim_schema_ok"):
        return
    try:
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS alim_valutazione (paziente_id INTEGER PRIMARY KEY, "
                    "dati TEXT, aggiornato_il TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        cur.execute("CREATE TABLE IF NOT EXISTS alim_esami (id SERIAL PRIMARY KEY, paziente_id INTEGER NOT NULL, "
                    "pannello TEXT, gruppo TEXT, esame TEXT, fase TEXT DEFAULT 'iniziale', ordine INTEGER, "
                    "data_richiesta DATE, data_prelievo DATE, valore TEXT, unita TEXT, riferimento TEXT, "
                    "fuori_range BOOLEAN DEFAULT FALSE, ripetere BOOLEAN DEFAULT FALSE, "
                    "aggiornato_il TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        cur.execute("CREATE INDEX IF NOT EXISTS alim_esami_paz ON alim_esami (paziente_id, fase, ordine)")
        cur.execute("CREATE TABLE IF NOT EXISTS alim_piano (paziente_id INTEGER PRIMARY KEY, dati TEXT, "
                    "firmato_da TEXT, qualifica TEXT, firmato_il TIMESTAMP, "
                    "aggiornato_il TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        cur.execute("CREATE TABLE IF NOT EXISTS alim_diario (id SERIAL PRIMARY KEY, paziente_id INTEGER NOT NULL, "
                    "data DATE NOT NULL, budwig BOOLEAN, ph NUMERIC(3,1), intestino BOOLEAN, sonno TEXT, nota TEXT, "
                    "UNIQUE (paziente_id, data))")
        cur.execute("CREATE TABLE IF NOT EXISTS alim_misure (paziente_id INTEGER NOT NULL, misura TEXT NOT NULL, "
                    "settimana INTEGER NOT NULL, valore TEXT, PRIMARY KEY (paziente_id, misura, settimana))")
        conn.commit()
        st.session_state["_alim_schema_ok"] = True
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        st.error(f"Tabelle alimentazione non create: {e}")


def _q(conn, sql, par=()):
    try:
        cur = conn.cursor()
        cur.execute(sql, par)
        righe = cur.fetchall() or []
        if righe and not isinstance(righe[0], dict):
            nomi = [c[0] for c in cur.description]
            righe = [dict(zip(nomi, r)) for r in righe]
        return [dict(r) for r in righe]
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return []


def _esegui(conn, sql, par=()) -> str:
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


def _json(conn, tabella, paz_id) -> dict:
    r = _q(conn, f"SELECT * FROM {tabella} WHERE paziente_id=%s", (int(paz_id),))
    if not r:
        return {}
    try:
        d = json.loads(r[0].get("dati") or "{}")
    except Exception:
        d = {}
    d["_riga"] = r[0]
    return d


def _salva_json(conn, tabella, paz_id, dati, extra_sql="", extra_par=()) -> str:
    dati = {k: v for k, v in dati.items() if not k.startswith("_")}
    return _esegui(conn,
        f"INSERT INTO {tabella} (paziente_id, dati, aggiornato_il) VALUES (%s,%s,CURRENT_TIMESTAMP) "
        f"ON CONFLICT (paziente_id) DO UPDATE SET dati=EXCLUDED.dati, aggiornato_il=CURRENT_TIMESTAMP{extra_sql}",
        (int(paz_id), json.dumps(dati, ensure_ascii=False, default=str)) + tuple(extra_par))


def _fmt_d(d):
    return d.strftime("%d/%m/%Y") if hasattr(d, "strftime") else ""


def _num(s):
    try:
        return float(str(s).replace(",", ".").strip())
    except Exception:
        return None


def fuori_range_auto(valore, riferimento):
    """True/False se valore e riferimento sono leggibili, altrimenti None.
    Riconosce «30–100», «30-100», «< 200», «<= 10», «> 4»."""
    v = _num(re.sub(r"[^\d,.\-]", "", str(valore or "")) or None)
    r = str(riferimento or "").replace(",", ".").replace("–", "-").replace("—", "-").strip()
    if v is None or not r:
        return None
    m = re.match(r"^\s*(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)", r)
    if m:
        return not (float(m.group(1)) <= v <= float(m.group(2)))
    m = re.match(r"^\s*(<=?|≤)\s*(\d+(?:\.\d+)?)", r)
    if m:
        return v > float(m.group(2)) if m.group(1) in ("<=", "≤") else v >= float(m.group(2))
    m = re.match(r"^\s*(>=?|≥)\s*(\d+(?:\.\d+)?)", r)
    if m:
        return v < float(m.group(2)) if m.group(1) in (">=", "≥") else v <= float(m.group(2))
    return None


# ── 1 · Valutazione ───────────────────────────────────────────────────

def _sel(label, opts, val, key):
    o = [_NO] + opts
    return st.selectbox(label, o, index=o.index(val) if val in o else 0, key=key)


def _tab_valutazione(conn, paz_id, px):
    v = _json(conn, "alim_valutazione", paz_id)
    with st.form(f"{px}_val"):
        c1, c2 = st.columns(2)
        avvio = c1.date_input("Inizio del percorso", value=_data(v.get("avvio")) or datetime.date.today(),
                              format="DD/MM/YYYY", key=f"{px}_avvio")
        scala = c2.text_input("Scala comportamentale usata per le misure", v.get("scala", ""),
                              placeholder="es. SNAP-IV, Conners, ABC", key=f"{px}_scala")
        st.markdown("**🍽️ Abitudini alimentari attuali**")
        ab = {}
        cols = st.columns(2)
        for i, (k, l, o) in enumerate(ABITUDINI):
            with cols[i % 2]:
                ab[k] = _sel(l, o, v.get(k), f"{px}_{k}")
        st.markdown("**👅 Selettività alimentare** · livello 3, canali sensoriali")
        rifiuti = st.multiselect("Rifiuta per", RIFIUTI, default=[x for x in v.get("rifiuti", []) if x in RIFIUTI],
                                 key=f"{px}_rif")
        accettati = st.text_area("Alimenti accettati oggi", v.get("accettati", ""), height=70, key=f"{px}_acc")
        n_acc = st.number_input("Numero di alimenti accettati", 0, 300, int(v.get("n_accettati") or 0),
                                key=f"{px}_nacc")
        st.markdown("**🌀 Intestino** · pilastro 2")
        it = {}
        cols = st.columns(2)
        for i, (k, l, o) in enumerate(INTESTINO):
            with cols[i % 2]:
                it[k] = _sel(l, o, v.get(k), f"{px}_{k}")
        st.markdown("**⚖️ Equilibrio acido-base** · pilastro 3")
        ph0 = st.number_input("pH delle urine iniziale (prima urina del mattino, 0 = non misurato)",
                              0.0, 9.0, float(v.get("ph0") or 0.0), 0.1, key=f"{px}_ph0")
        note = st.text_area("Note", v.get("note", ""), height=70, key=f"{px}_note")
        if st.form_submit_button("💾 Salva valutazione", type="primary"):
            dati = {"avvio": avvio.isoformat(), "scala": scala.strip(), **ab, **it, "rifiuti": rifiuti,
                    "accettati": accettati.strip(), "n_accettati": int(n_acc), "ph0": float(ph0),
                    "note": note.strip()}
            err = _salva_json(conn, "alim_valutazione", paz_id, dati)
            if err:
                st.error(f"Non salvata: {err}")
            else:
                # Le misure di partenza si riempiono da qui, se ancora vuote.
                if n_acc:
                    _misura_se_vuota(conn, paz_id, "Alimenti accettati", 0, str(int(n_acc)))
                if ph0:
                    _misura_se_vuota(conn, paz_id, "pH urine, media", 0, f"{ph0:.1f}".replace(".", ","))
                st.success("Valutazione salvata.")


def _data(s):
    try:
        return datetime.date.fromisoformat(str(s)[:10])
    except Exception:
        return None


def settimana_corrente(conn, paz_id):
    avvio = _data(_json(conn, "alim_valutazione", paz_id).get("avvio"))
    if not avvio:
        return None, None
    return avvio, (datetime.date.today() - avvio).days // 7 + 1


# ── 2 · Esami ─────────────────────────────────────────────────────────

def _esami(conn, paz_id, fase=None):
    if fase:
        return _q(conn, "SELECT * FROM alim_esami WHERE paziente_id=%s AND fase=%s ORDER BY ordine, id",
                  (int(paz_id), fase))
    return _q(conn, "SELECT * FROM alim_esami WHERE paziente_id=%s ORDER BY fase, ordine, id", (int(paz_id),))


def _applica_pannello(conn, paz_id, nome, data_rich, fase="iniziale", solo=None) -> str:
    n = 0
    for gruppo, voci in PANNELLI[nome]:
        for esame in voci:
            n += 1
            if solo is not None and esame not in solo:
                continue
            err = _esegui(conn,
                "INSERT INTO alim_esami (paziente_id, pannello, gruppo, esame, fase, ordine, data_richiesta, ripetere) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                (int(paz_id), nome, gruppo, esame, fase, n, data_rich, esame in RIPETERE))
            if err:
                return err
    return ""


_PROMPT_REFERTO = """Qui sotto c'è il testo di un referto di laboratorio.
Per ciascuno degli esami elencati trova, se presente, il valore, l'unità di
misura e l'intervallo di riferimento del laboratorio, copiandoli come sono
scritti. Se un esame non c'è, non includerlo. Non inventare valori.

ESAMI (id: nome):
{elenco}

Rispondi SOLO con un array JSON:
[{"id": 12, "valore": "18", "unita": "ng/mL", "riferimento": "30-100", "data_prelievo": "AAAA-MM-GG o vuoto"}]

REFERTO:
{testo}
"""


def _leggi_referto(conn, paz_id, f, righe) -> tuple[int, str]:
    from .ai_estrazione import ai_disponibile, estrai_da_documento, genera_testo
    if not ai_disponibile():
        return 0, "AI non configurata nei Secrets."
    dati = f.getvalue()
    testo = estrai_da_documento(dati, f.type or "", f.name)
    if testo.startswith("⚠️"):
        return 0, testo
    # Il referto resta anche nell'archivio documenti del paziente.
    _esegui(conn, "INSERT INTO documenti_clinici (paziente_id, tipo, nome_file, mime, dati, data, estratto) "
                  "VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (int(paz_id), "Esami di laboratorio", f.name, f.type or "", dati, datetime.date.today(), testo))
    elenco = "\n".join(f"{r['id']}: {r['esame']}" for r in righe)
    risposta = genera_testo(_PROMPT_REFERTO.replace("{elenco}", elenco).replace("{testo}", testo[:14000]))
    if risposta.startswith("⚠️"):
        return 0, risposta
    t = re.sub(r"^```(?:json)?|```$", "", risposta.strip(), flags=re.M)
    i, j = t.find("["), t.rfind("]")
    try:
        lista = json.loads(t[i:j + 1]) if i >= 0 else []
    except Exception:
        return 0, "L'AI non ha restituito un elenco leggibile: riprova."
    validi = {r["id"] for r in righe}
    n = 0
    for x in lista:
        try:
            rid = int(x.get("id"))
        except Exception:
            continue
        if rid not in validi or not str(x.get("valore") or "").strip():
            continue
        fr = fuori_range_auto(x.get("valore"), x.get("riferimento"))
        err = _esegui(conn,
            "UPDATE alim_esami SET valore=%s, unita=%s, riferimento=%s, fuori_range=%s, "
            "data_prelievo=COALESCE(%s, data_prelievo), aggiornato_il=CURRENT_TIMESTAMP WHERE id=%s",
            (str(x.get("valore")).strip(), str(x.get("unita") or "").strip(),
             str(x.get("riferimento") or "").strip(), bool(fr), _data(x.get("data_prelievo")), rid))
        if not err:
            n += 1
    return n, ""


def _griglia_esami(conn, righe, px, fase):
    import pandas as pd
    per_gruppo = {}
    for r in righe:
        per_gruppo.setdefault(r.get("gruppo") or "Altri esami", []).append(r)
    modifiche = []
    for gruppo, rr in per_gruppo.items():
        st.markdown(f"**{gruppo}**")
        df = pd.DataFrame([{
            "Esame": r["esame"], "Valore": r.get("valore") or "", "Unità": r.get("unita") or "",
            "Riferimento": r.get("riferimento") or "", "Fuori range": bool(r.get("fuori_range")),
            "Ripetere": bool(r.get("ripetere")),
        } for r in rr], index=[r["id"] for r in rr])
        cfg = {"Esame": st.column_config.TextColumn(disabled=True, width="large"),
               "Fuori range": st.column_config.CheckboxColumn(help="Si calcola da solo se valore e riferimento sono numerici"),
               "Ripetere": st.column_config.CheckboxColumn(help="Da ripetere al controllo")}
        if fase == "controllo":
            cfg["Ripetere"] = None
        out = st.data_editor(df, key=f"{px}_ed_{fase}_{gruppo}", hide_index=True,
                             use_container_width=True, column_config=cfg)
        for rid, row in out.iterrows():
            modifiche.append((int(rid), row))
    return modifiche


def _salva_griglia(conn, righe, modifiche) -> str:
    vecchi = {r["id"]: r for r in righe}
    for rid, row in modifiche:
        prima = vecchi.get(rid, {})
        valore = str(row.get("Valore") or "").strip()
        rif = str(row.get("Riferimento") or "").strip()
        fuori = bool(row.get("Fuori range"))
        if valore != (prima.get("valore") or "") or rif != (prima.get("riferimento") or ""):
            auto = fuori_range_auto(valore, rif)
            if auto is not None:
                fuori = auto
        err = _esegui(conn,
            "UPDATE alim_esami SET valore=%s, unita=%s, riferimento=%s, fuori_range=%s, ripetere=%s, "
            "aggiornato_il=CURRENT_TIMESTAMP WHERE id=%s",
            (valore or None, str(row.get("Unità") or "").strip(), rif, fuori,
             bool(row.get("Ripetere", prima.get("ripetere"))), rid))
        if err:
            return err
    return ""


def _proponi_rilievi(conn, paz_id, righe) -> tuple[int, str]:
    try:
        from .rilievi_pnev import aggiungi_rilievo
    except Exception as e:
        return 0, f"Rilievi PNEV non disponibili: {e}"
    ids = [r["id"] for r in righe]
    if ids:
        _esegui(conn, "DELETE FROM rilievi_pnev WHERE paziente_id=%s AND fonte='test' "
                      "AND area='esame di laboratorio' AND stato='proposto'", (int(paz_id),))
    n = 0
    for r in righe:
        if not r.get("fuori_range") or not r.get("valore"):
            continue
        err = aggiungi_rilievo(conn, paz_id, 1, f"{r['esame']} fuori range", "test",
                               area="esame di laboratorio",
                               valore=f"{r['valore']} {r.get('unita') or ''} (rif. {r.get('riferimento') or '—'})".strip(),
                               giudizio="da approfondire", data=r.get("data_prelievo") or r.get("data_richiesta"),
                               autore=r.get("pannello") or "", fonte_id=r["id"], stato="proposto")
        if not err:
            n += 1
    return n, ""


def _tab_esami(conn, paz_id, px):
    tutti = _esami(conn, paz_id)
    if not tutti:
        st.info("Nessun esame registrato. Applica un pannello: gli esami compaiono qui da compilare.")
        c1, c2, c3 = st.columns([4, 2, 2])
        nome = c1.selectbox("Pannello", list(PANNELLI), key=f"{px}_pan")
        data_r = c2.date_input("Data della richiesta", datetime.date.today(), format="DD/MM/YYYY", key=f"{px}_dr")
        c3.markdown("&nbsp;")
        if c3.button("Applica pannello", type="primary", key=f"{px}_app"):
            err = _applica_pannello(conn, paz_id, nome, data_r)
            st.error(err) if err else st.rerun()
        return

    fasi = [f for f in ("iniziale", "controllo") if any(r["fase"] == f for r in tutti)]
    con = sum(1 for r in tutti if r.get("valore"))
    fuori = sum(1 for r in tutti if r.get("fuori_range") and r.get("valore"))
    m1, m2, m3 = st.columns(3)
    m1.metric("Con risultato", con)
    m2.metric("Fuori range", fuori)
    m3.metric("In attesa", len(tutti) - con)
    st.caption(f"{tutti[0].get('pannello') or ''} · richiesta del {_fmt_d(tutti[0].get('data_richiesta'))}")

    fase = st.radio("Esami", fasi, horizontal=True, key=f"{px}_fase",
                    format_func=lambda f: "Iniziali" if f == "iniziale" else "Controllo")
    righe = [r for r in tutti if r["fase"] == fase]

    with st.container(border=True):
        st.markdown("**📎 Carica il referto del laboratorio**")
        st.caption("L'AI legge valori, unità e riferimenti e li mette nella riga giusta. Controlla sempre "
                   "prima di usarli. Il referto resta anche in Documenti clinici.")
        f = st.file_uploader("Referto (PDF o foto)", type=["pdf", "png", "jpg", "jpeg"], key=f"{px}_ref_{fase}")
        if f is not None and st.button("🤖 Leggi il referto", key=f"{px}_leggi_{fase}"):
            with st.spinner("Lettura del referto…"):
                n, err = _leggi_referto(conn, paz_id, f, righe)
            if err:
                st.error(err)
            else:
                st.session_state[f"{px}_msg"] = f"{n} valori inseriti dal referto. Controllali qui sotto."
                st.rerun()
    msg = st.session_state.pop(f"{px}_msg", None)
    if msg:
        st.success(msg)

    modifiche = _griglia_esami(conn, righe, px, fase)
    b1, b2, b3 = st.columns(3)
    if b1.button("💾 Salva esami", type="primary", key=f"{px}_salva_{fase}"):
        err = _salva_griglia(conn, righe, modifiche)
        st.error(err) if err else st.rerun()
    if b2.button("🧩 Fuori range → Rilievi PNEV", key=f"{px}_ril"):
        n, err = _proponi_rilievi(conn, paz_id, _esami(conn, paz_id))
        st.error(err) if err else st.success(f"{n} rilievi proposti in 🧩 Rilievi PNEV, da confermare.")
    if "controllo" not in fasi:
        if b3.button("↻ Crea esami di controllo", key=f"{px}_ctrl"):
            da_rip = {r["esame"] for r in tutti if r.get("ripetere")}
            if not da_rip:
                st.warning("Nessun esame segnato da ripetere.")
            else:
                pan = tutti[0].get("pannello")
                if pan in PANNELLI:
                    err = _applica_pannello(conn, paz_id, pan, datetime.date.today(), "controllo", da_rip)
                else:
                    err = ""
                    for r in tutti:
                        if r["esame"] in da_rip:
                            err = err or _esegui(conn,
                                "INSERT INTO alim_esami (paziente_id, pannello, gruppo, esame, fase, ordine, data_richiesta) "
                                "VALUES (%s,%s,%s,%s,'controllo',%s,%s)",
                                (int(paz_id), pan, r["gruppo"], r["esame"], r["ordine"], datetime.date.today()))
                st.error(err) if err else st.rerun()


# ── 3 · Piano ─────────────────────────────────────────────────────────

def _tab_piano(conn, paz_id, px):
    import pandas as pd
    p = _json(conn, "alim_piano", paz_id)
    riga = p.get("_riga") or {}
    firmato = bool(riga.get("firmato_il"))
    if firmato:
        st.success(f"✍️ Firmato da {riga.get('firmato_da')} ({riga.get('qualifica')}) il "
                   f"{_fmt_d(riga.get('firmato_il'))}. Se modifichi il piano, va firmato di nuovo.")
    else:
        st.warning("Piano in bozza: va firmato da medico, biologo nutrizionista o dietista prima di "
                   "stamparlo per la famiglia.")

    voci = p.get("voci") or {}
    with st.form(f"{px}_piano"):
        cols = st.columns(2)
        nuove, extra = {}, {}
        for i, (n, t, vv) in enumerate(PILASTRI):
            with cols[i % 2]:
                with st.container(border=True):
                    st.markdown(f"**{n} · {t}**")
                    for k, l in vv:
                        nuove[k] = st.checkbox(l, value=voci.get(k, True), key=f"{px}_{k}")
                    extra[n] = st.text_area("Altre indicazioni", (p.get("extra") or {}).get(n, ""),
                                            height=60, key=f"{px}_ex_{n}")
        integr = st.text_area("Integrazione prescritta: prodotto, dose, durata", p.get("integrazione", ""),
                              height=80, key=f"{px}_int")
        st.markdown("**🥣 Crema Budwig**")
        bud = st.data_editor(pd.DataFrame(p.get("budwig") or BUDWIG), num_rows="dynamic",
                             use_container_width=True, hide_index=True, key=f"{px}_bud")
        gradini = st.text_area("🪜 Introduzione graduale", p.get("gradini") or GRADINI, height=110, key=f"{px}_gr")
        if st.form_submit_button("💾 Salva piano", type="primary"):
            dati = {"voci": nuove, "extra": extra, "integrazione": integr.strip(),
                    "budwig": [r for r in bud.fillna("").to_dict("records") if str(r.get("Ingrediente", "")).strip()],
                    "gradini": gradini.strip()}
            err = _salva_json(conn, "alim_piano", paz_id, dati,
                              ", firmato_da=NULL, qualifica=NULL, firmato_il=NULL")
            st.error(err) if err else st.rerun()

    with st.container(border=True):
        st.markdown("**✍️ Firma del piano**")
        c1, c2, c3 = st.columns([3, 2, 2])
        chi = c1.text_input("Nome e cognome", riga.get("firmato_da") or "", key=f"{px}_chi")
        qual = c2.selectbox("Qualifica", QUALIFICHE, key=f"{px}_qual",
                            index=QUALIFICHE.index(riga.get("qualifica")) if riga.get("qualifica") in QUALIFICHE else 0)
        c3.markdown("&nbsp;")
        if c3.button("Firma il piano", key=f"{px}_firma", disabled=not riga or not chi.strip()):
            err = _esegui(conn, "UPDATE alim_piano SET firmato_da=%s, qualifica=%s, firmato_il=CURRENT_TIMESTAMP "
                                "WHERE paziente_id=%s", (chi.strip(), qual, int(paz_id)))
            st.error(err) if err else st.rerun()
        if not riga:
            st.caption("Salva prima il piano.")
    if firmato:
        try:
            st.download_button("🖨️ Piano per la famiglia (PDF)", _pdf_piano(conn, paz_id, p, riga),
                               file_name="piano_alimentare.pdf", mime="application/pdf", key=f"{px}_pdf")
        except Exception as e:
            st.caption(f"PDF non disponibile: {e}")


def _pdf_piano(conn, paz_id, p, riga) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    from xml.sax.saxutils import escape
    from .pdf_templates import draw_intestazione, draw_footer

    verde = colors.HexColor("#1D6B44")
    tit = ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=14, leading=18, spaceAfter=4)
    h = ParagraphStyle("h", fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=verde,
                       spaceBefore=8, spaceAfter=3)
    b = ParagraphStyle("b", fontName="Helvetica", fontSize=10, leading=14)
    nome = ""
    r = _q(conn, "SELECT cognome, nome FROM pazienti WHERE id=%s", (int(paz_id),))
    if r:
        nome = f"{r[0].get('cognome') or ''} {r[0].get('nome') or ''}".strip()

    storia = [Paragraph("Piano alimentare — metodo Kousmine", tit),
              Paragraph(escape(nome), b), Spacer(1, 6)]
    voci = p.get("voci") or {}
    for n, t, vv in PILASTRI:
        righe = [l for k, l in vv if voci.get(k, True)]
        ex = ((p.get("extra") or {}).get(n) or "").strip()
        if n == "Pilastro 4" and p.get("integrazione"):
            righe.append(p["integrazione"])
        if ex:
            righe.append(ex)
        if righe:
            storia.append(Paragraph(f"{t}", h))
            storia += [Paragraph("• " + escape(x).replace("\n", "<br/>"), b) for x in righe]
    bud = p.get("budwig") or BUDWIG
    if bud:
        storia.append(Paragraph("Crema Budwig", h))
        t = Table([[escape(str(x.get("Ingrediente", ""))), escape(str(x.get("Quantità", "")))] for x in bud],
                  colWidths=[11 * cm, 5 * cm])
        t.setStyle(TableStyle([("FONT", (0, 0), (-1, -1), "Helvetica", 10),
                               ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#C9D1CC")),
                               ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
        storia.append(t)
    if p.get("gradini"):
        storia.append(Paragraph("Introduzione graduale", h))
        storia.append(Paragraph(escape(p["gradini"]).replace("\n", "<br/>"), b))
    storia += [Spacer(1, 16), Paragraph(
        f"{escape(riga.get('firmato_da') or '')} — {escape(riga.get('qualifica') or '')} · "
        f"{_fmt_d(riga.get('firmato_il'))}", b)]

    def _pagina(c, doc):
        draw_intestazione(c)
        draw_footer(c)

    buf = io.BytesIO()
    SimpleDocTemplate(buf, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=5.7 * cm,
                      bottomMargin=4.9 * cm, title="Piano alimentare").build(
        storia, onFirstPage=_pagina, onLaterPages=_pagina)
    return buf.getvalue()


# ── 4 · Diario ────────────────────────────────────────────────────────

def _diario(conn, paz_id):
    return _q(conn, "SELECT * FROM alim_diario WHERE paziente_id=%s ORDER BY data DESC", (int(paz_id),))


def _tab_diario(conn, paz_id, px):
    import pandas as pd
    avvio, sett = settimana_corrente(conn, paz_id)
    with st.form(f"{px}_dia", clear_on_submit=True):
        c1, c2, c3, c4 = st.columns([2, 1, 1, 2])
        data = c1.date_input("Giorno", datetime.date.today(), format="DD/MM/YYYY", key=f"{px}_dd")
        bud = c2.checkbox("Budwig", key=f"{px}_db")
        intest = c3.checkbox("Evacuazione", key=f"{px}_di")
        sonno = c4.selectbox("Sonno", [_NO, "buono", "agitato", "risvegli"], key=f"{px}_ds")
        c5, c6 = st.columns([1, 4])
        ph = c5.number_input("pH (0 = non misurato)", 0.0, 9.0, 0.0, 0.1, key=f"{px}_dp")
        nota = c6.text_input("Nota", key=f"{px}_dn", placeholder="es. festa, dolci, niente Budwig")
        if st.form_submit_button("Aggiungi al diario", type="primary"):
            err = _esegui(conn,
                "INSERT INTO alim_diario (paziente_id, data, budwig, ph, intestino, sonno, nota) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (paziente_id, data) DO UPDATE SET "
                "budwig=EXCLUDED.budwig, ph=EXCLUDED.ph, intestino=EXCLUDED.intestino, "
                "sonno=EXCLUDED.sonno, nota=EXCLUDED.nota",
                (int(paz_id), data, bud, ph or None, intest, None if sonno == _NO else sonno, nota.strip()))
            st.error(err) if err else st.success(f"Giorno {_fmt_d(data)} registrato.")

    righe = _diario(conn, paz_id)
    if not righe:
        st.caption("Diario ancora vuoto.")
        return
    ultimi7 = [r for r in righe if r["data"] >= datetime.date.today() - datetime.timedelta(days=6)]
    ader = lambda rr: round(100 * sum(1 for r in rr if r.get("budwig")) / len(rr)) if rr else 0
    m1, m2, m3 = st.columns(3)
    m1.metric("Aderenza Budwig, ultimi 7 giorni", f"{ader(ultimi7)}%")
    m2.metric("Dall'inizio", f"{ader(righe)}%")
    m3.metric("Settimana del percorso", sett or "—")

    if avvio:
        per_sett = {}
        for r in righe:
            if r.get("ph"):
                per_sett.setdefault((r["data"] - avvio).days // 7 + 1, []).append(float(r["ph"]))
        if per_sett:
            st.markdown("**⚖️ pH delle urine, media per settimana** · riferimento del metodo 7")
            st.bar_chart(pd.DataFrame({"pH": {f"sett. {k:02d}": round(sum(v) / len(v), 2)
                                              for k, v in sorted(per_sett.items()) if k > 0}}))
    st.dataframe(pd.DataFrame([{
        "Giorno": _fmt_d(r["data"]), "Budwig": "✅" if r.get("budwig") else "—",
        "pH": str(r["ph"]).replace(".", ",") if r.get("ph") else "", "Evacuazione": "✅" if r.get("intestino") else "—",
        "Sonno": r.get("sonno") or "", "Nota": r.get("nota") or ""} for r in righe[:28]]),
        hide_index=True, use_container_width=True)


# ── 5 · Esiti ─────────────────────────────────────────────────────────

def _misure(conn, paz_id):
    out = {}
    for r in _q(conn, "SELECT * FROM alim_misure WHERE paziente_id=%s", (int(paz_id),)):
        out[(r["misura"], int(r["settimana"]))] = r.get("valore") or ""
    return out


def _misura_se_vuota(conn, paz_id, misura, sett, valore):
    _esegui(conn, "INSERT INTO alim_misure (paziente_id, misura, settimana, valore) VALUES (%s,%s,%s,%s) "
                  "ON CONFLICT (paziente_id, misura, settimana) DO UPDATE SET valore=COALESCE(NULLIF(alim_misure.valore,''), EXCLUDED.valore)",
            (int(paz_id), misura, sett, valore))


def _dal_diario(conn, paz_id, sett):
    avvio, _ = settimana_corrente(conn, paz_id)
    if not avvio or sett == 0:
        return {}
    ini = avvio + datetime.timedelta(days=7 * (sett - 1))
    rr = [r for r in _diario(conn, paz_id) if ini <= r["data"] < ini + datetime.timedelta(days=7)]
    if not rr:
        return {}
    ph = [float(r["ph"]) for r in rr if r.get("ph")]
    out = {"Evacuazioni a settimana": str(sum(1 for r in rr if r.get("intestino")))}
    if ph:
        out["pH urine, media"] = f"{sum(ph) / len(ph):.1f}".replace(".", ",")
    risv = sum(1 for r in rr if r.get("sonno") == "risvegli")
    out["Risvegli notturni a settimana"] = str(risv)
    return out


def _variazione(a, b):
    x, y = _num(a), _num(b)
    if x is None or y is None:
        return ""
    d = y - x
    if x and abs(x) >= 10:
        return f"{d / x * 100:+.0f}%"
    return f"{d:+.1f}".replace(".", ",").replace(",0", "")


def _tab_esiti(conn, paz_id, px):
    import pandas as pd
    val = _json(conn, "alim_valutazione", paz_id)
    if val.get("scala"):
        st.caption(f"Scala comportamentale: {val['scala']}")
    mis = _misure(conn, paz_id)
    df = pd.DataFrame([{
        "Misura": m, "Sett. 0": mis.get((m, 0), ""), "Sett. 5": mis.get((m, 5), ""), "Sett. 12": mis.get((m, 12), ""),
    } for m in MISURE])
    df["Variazione"] = [_variazione(r["Sett. 0"], r["Sett. 12"] or r["Sett. 5"]) for _, r in df.iterrows()]
    out = st.data_editor(df, hide_index=True, use_container_width=True, key=f"{px}_mis",
                         column_config={"Misura": st.column_config.TextColumn(disabled=True, width="large"),
                                        "Variazione": st.column_config.TextColumn(disabled=True)})
    c1, c2, c3 = st.columns(3)
    if c1.button("💾 Salva misure", type="primary", key=f"{px}_smis"):
        err = ""
        for _, r in out.iterrows():
            for s in SETTIMANE:
                err = err or _esegui(conn,
                    "INSERT INTO alim_misure (paziente_id, misura, settimana, valore) VALUES (%s,%s,%s,%s) "
                    "ON CONFLICT (paziente_id, misura, settimana) DO UPDATE SET valore=EXCLUDED.valore",
                    (int(paz_id), r["Misura"], s, str(r[f"Sett. {s}"] or "").strip()))
        st.error(err) if err else st.rerun()
    for col, s in ((c2, 5), (c3, 12)):
        dd = _dal_diario(conn, paz_id, s)
        if dd and col.button(f"Riempi sett. {s} dal diario", key=f"{px}_dd{s}"):
            for m, v in dd.items():
                _misura_se_vuota(conn, paz_id, m, s, v)
            st.rerun()
    st.caption("Variazione tra settimana 0 e l'ultima misura disponibile. Dal diario si riempiono solo le celle vuote.")

    ini = {r["esame"]: r for r in _esami(conn, paz_id, "iniziale")}
    ctrl = _esami(conn, paz_id, "controllo")
    if ctrl:
        st.markdown("**🧪 Esami di controllo**")
        st.dataframe(pd.DataFrame([{
            "Esame": r["esame"], "Iniziale": (ini.get(r["esame"], {}).get("valore") or ""),
            "Controllo": r.get("valore") or "in attesa", "Unità": r.get("unita") or ini.get(r["esame"], {}).get("unita") or "",
            "Riferimento": r.get("riferimento") or ini.get(r["esame"], {}).get("riferimento") or "",
        } for r in ctrl]), hide_index=True, use_container_width=True)


# ── Pagina ────────────────────────────────────────────────────────────

def render_alimentazione(conn, paz_id) -> None:
    st.subheader("🥗 Alimentazione — metodo Kousmine")
    if conn is None or not paz_id:
        st.info("Seleziona un paziente.")
        return
    _assicura_tabelle(conn)
    avvio, sett = settimana_corrente(conn, paz_id)
    st.caption("Valutazione, esami, piano sui quattro pilastri, diario e verifica dei risultati. "
               "Piano e integrazione sono firmati dal professionista abilitato."
               + (f" · Percorso avviato il {_fmt_d(avvio)}, settimana {sett}" if avvio else ""))
    px = f"alim_{paz_id}"
    t1, t2, t3, t4, t5 = st.tabs(["1 · Valutazione", "2 · Esami", "3 · Piano", "4 · Diario", "5 · Esiti"])
    with t1:
        _tab_valutazione(conn, paz_id, px + "_v")
    with t2:
        _tab_esami(conn, paz_id, px + "_e")
    with t3:
        _tab_piano(conn, paz_id, px + "_p")
    with t4:
        _tab_diario(conn, paz_id, px + "_d")
    with t5:
        _tab_esiti(conn, paz_id, px + "_x")


def sintesi_alimentazione(conn, paz_id) -> list[str]:
    """Per diagnosi e relazione: solo cio' che e' compilato."""
    if conn is None or not paz_id:
        return []
    out = []
    v = _json(conn, "alim_valutazione", paz_id)
    abit = [f"{l}: {v[k]}" for k, l, _ in ABITUDINI + INTESTINO if v.get(k) and v[k] != _NO]
    if abit:
        out.append("- " + "; ".join(abit))
    if v.get("rifiuti"):
        out.append(f"- Selettività: rifiuta per {', '.join(v['rifiuti'])}; alimenti accettati {v.get('n_accettati') or '—'}")
    fuori = [r for r in _esami(conn, paz_id) if r.get("fuori_range") and r.get("valore")]
    if fuori:
        out.append("- Esami fuori range: " + "; ".join(
            f"{r['esame']} {r['valore']} {r.get('unita') or ''} (rif. {r.get('riferimento') or '—'})" for r in fuori))
    mis = _misure(conn, paz_id)
    for m in MISURE:
        a, b = mis.get((m, 0)), mis.get((m, 12)) or mis.get((m, 5))
        if a and b:
            out.append(f"- {m}: {a} → {b}")
    return out
