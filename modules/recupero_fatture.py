# -*- coding: utf-8 -*-
"""🧾 Recupero fatture arretrate da SumUp.

1. Carichi l'export «resoconto vendite» di SumUp (CSV).
2. Il gestionale legge le fatture dell'anno da Fatture in Cloud e impara, per ogni paziente:
   importi abituali, giorni della settimana, numerazione e descrizione dell'ultima fattura.
3. Per ogni pagamento propone i pazienti più probabili: tu scegli (o segni «già fatturata»).
4. Anteprima delle fatture da creare (stessa numerazione e descrizione dell'ultima del paziente).
   La creazione vera arriverà dopo, quando decidi la data con il commercialista.
Gli abbinamenti si salvano nel database: puoi lavorare un po' alla volta.
"""
from __future__ import annotations

import collections
import csv
import datetime as dt
import io
import re

import streamlit as st

from . import fatture_cloud as fc

MESI = {"gen": 1, "feb": 2, "mar": 3, "apr": 4, "mag": 5, "giu": 6, "lug": 7, "ago": 8, "set": 9, "ott": 10, "nov": 11, "dic": 12}
GIORNI = ["lun", "mar", "mer", "gio", "ven", "sab", "dom"]
DA_SCEGLIERE, GIA, ESCLUSO = "— da scegliere —", "✓ già fatturata", "✗ non va fatturata"


# ───────────────────────────── database ─────────────────────────────
def _righe(conn, sql, par=()):
    try:
        c = conn.cursor(); c.execute(sql, par)
        nomi = [d[0] for d in c.description]
        return [r if isinstance(r, dict) else dict(zip(nomi, r)) for r in c.fetchall()]
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return []


def _esegui(conn, sql, par=()):
    try:
        c = conn.cursor(); c.execute(sql, par); conn.commit(); return None
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        return str(e)


def assicura_tabella(conn):
    _esegui(conn, """CREATE TABLE IF NOT EXISTS recupero_pagamenti (
        sumup_id TEXT PRIMARY KEY, quando TIMESTAMP, importo NUMERIC(10,2), metodo TEXT,
        stato TEXT DEFAULT 'da_scegliere', entity_id BIGINT, entity_nome TEXT,
        numerazione TEXT, descrizione TEXT, fattura_id BIGINT, aggiornato_il TIMESTAMPTZ DEFAULT now(), chiave TEXT)""")
    _esegui(conn, "ALTER TABLE recupero_pagamenti ADD COLUMN IF NOT EXISTS chiave TEXT")


# ───────────────────────────── lettura SumUp ─────────────────────────────
def _num(s):
    s = str(s or "").strip()
    return float(s.replace(".", "").replace(",", ".")) if s else 0.0


def _quando(s):
    m = re.match(r"(\d{1,2}) (\w{3})\w* (\d{4}), (\d{1,2}):(\d{2})", str(s).strip())
    if not m:
        return None
    g, mese, a, h, mi = m.groups()
    return dt.datetime(int(a), MESI.get(mese.lower()[:3], 1), int(g), int(h), int(mi))


def leggi_sumup(dati: bytes):
    testo = dati.decode("utf-8-sig", errors="replace")
    out = []
    for r in csv.DictReader(io.StringIO(testo)):
        if (r.get("Tipo") or "").strip().lower() != "vendita":
            continue
        q = _quando(r.get("Data"))
        if not q:
            continue
        out.append({"sumup_id": r.get("ID Transazione") or f"{q.isoformat()}_{r.get('Prezzo (lordo)')}",
                    "quando": q, "importo": _num(r.get("Prezzo (lordo)")), "metodo": r.get("Metodo di pagamento") or ""})
    return sorted(out, key=lambda x: x["quando"])


# ───────────────────────────── storico da Fatture in Cloud ─────────────────────────────
@st.cache_data(ttl=900, show_spinner=False)
def storico_fatture(cid: int, anno: int):
    """Tutte le fatture dell'anno (dettagliate). Ritorna (lista, errore)."""
    docs, pagina = [], 1
    while pagina <= 30:
        d, err = fc.chiama(f"/c/{cid}/issued_documents", {"type": "invoice", "per_page": 100, "page": pagina,
                                                          "fieldset": "detailed", "sort": "-date"})
        if err:
            return docs, err
        blocco = (d or {}).get("data", []) or []
        docs += [x for x in blocco if str(x.get("date", ""))[:4] >= str(anno)]
        if len(blocco) < 100 or (blocco and str(blocco[-1].get("date", ""))[:4] < str(anno)):
            break
        pagina += 1
    return docs, None


def profili(docs):
    """Per ogni cliente: importi, giorni della settimana, ultima fattura."""
    P = {}
    for d in docs:
        e = d.get("entity") or {}
        k = str(e.get("id") or (e.get("name") or "").strip().upper())
        if not k:
            continue
        try:
            giorno = dt.date.fromisoformat(str(d.get("date"))[:10])
        except Exception:
            continue
        p = P.setdefault(k, {"id": e.get("id"), "nome": (e.get("name") or "").strip(), "n": 0, "importi": collections.Counter(),
                             "giorni": collections.Counter(), "ultima": None, "ultima_data": dt.date(1900, 1, 1)})
        p["n"] += 1
        p["importi"][round(float(d.get("amount_gross") or 0), 2)] += 1
        p["giorni"][giorno.weekday()] += 1
        if giorno >= p["ultima_data"]:
            voci = d.get("items_list") or []
            p["ultima_data"] = giorno
            p["ultima"] = {"id": d.get("id"), "numerazione": d.get("numeration") or "", "importo": float(d.get("amount_gross") or 0),
                           "descrizione": (voci[0].get("name") if voci else "") or "", "cassa": d.get("cassa"), "data": giorno}
    return P


def candidati(P, pag, gia_scelti_oggi=(), quanti=6):
    """Pazienti più probabili per un pagamento (punteggio semplice e spiegabile)."""
    imp, wd, giorno = round(pag["importo"], 2), pag["quando"].weekday(), pag["quando"].date()
    out = []
    for k, p in P.items():
        if k in gia_scelti_oggi:
            continue
        s, motivi = 0.0, []
        if p["importi"].get(imp):
            s += 3 + min(p["importi"][imp], 10) / 10; motivi.append(f"paga {imp:.0f} €")
        quota = p["giorni"].get(wd, 0) / max(p["n"], 1)
        if quota >= 0.3:
            s += 2 * quota; motivi.append(f"viene di solito di {GIORNI[wd]}")
        giorni_fa = (giorno - p["ultima_data"]).days
        if 0 <= giorni_fa <= 45:
            s += 1; motivi.append(f"ultima fattura {giorni_fa} giorni prima")
        if s >= 3:
            out.append((s, k, p, ", ".join(motivi)))
    out.sort(key=lambda x: -x[0])
    return out[:quanti]


# ───────────────────────────── creazione delle fatture ─────────────────────────────
def _metodo_pos(cid):
    d, err = fc.chiama(f"/c/{cid}/settings/payment_methods")
    for m in ((d or {}).get("data") or []):
        if "pos" in str(m.get("name", "")).lower():
            return {"id": m["id"]}
    return None


def prepara_fattura(cid, r, metodo_pos=None):
    """Copia l'ultima fattura del paziente e la adatta a questo pagamento (data = data del pagamento)."""
    prof = r.get("_ultima_id")
    d, err = fc.chiama(f"/c/{cid}/issued_documents/{prof}", {"fieldset": "detailed"})
    if err:
        return None, f"lettura dell'ultima fattura: {err}"
    u = (d or {}).get("data") or {}
    giorno = str(r["quando"])[:10]
    imp = round(float(r["importo"]), 2)
    voce0 = dict((u.get("items_list") or [{}])[0])
    cassa = float(u.get("cassa") or 0); rivalsa = float(u.get("rivalsa") or 0)
    netto = round(imp / (1 + cassa / 100) / (1 + rivalsa / 100), 2)
    voce = {k: voce0.get(k) for k in ("product_id", "code", "name", "description", "measure", "vat", "not_taxable", "apply_withholding_taxes",
                                       "category") if voce0.get(k) is not None}
    voce.update({"qty": 1, "net_price": netto, "discount": 0})
    conto = ((u.get("payments_list") or [{}])[0] or {}).get("payment_account")
    doc = {"type": "invoice", "entity": u.get("entity"), "date": giorno, "numeration": u.get("numeration") or "",
           "currency": u.get("currency"), "language": u.get("language"), "subject": u.get("subject") or "",
           "visible_subject": u.get("visible_subject") or "", "notes": u.get("notes") or "", "rivalsa": u.get("rivalsa"),
           "cassa": u.get("cassa"), "cassa_taxable": u.get("cassa_taxable"), "global_cassa_taxable": u.get("global_cassa_taxable"),
           "withholding_tax": u.get("withholding_tax"), "stamp_duty": u.get("stamp_duty") or 0, "use_gross_prices": False,
           "e_invoice": bool(u.get("e_invoice")), "payment_method": metodo_pos or u.get("payment_method"),
           "show_payments": u.get("show_payments"), "show_payment_method": u.get("show_payment_method"),
           "template": u.get("template"), "extra_data": u.get("extra_data"), "items_list": [voce],
           "payments_list": [{"amount": imp, "due_date": giorno, "paid_date": giorno, "status": "paid",
                              **({"payment_account": {"id": conto["id"]}} if conto and conto.get("id") else {})}]}
    doc = {k: v for k, v in doc.items() if v is not None}
    # verifica dei totali con Fatture in Cloud: il totale deve essere esattamente l'importo pagato
    for _ in range(4):
        t, err = fc.scrivi("POST", f"/c/{cid}/issued_documents/totals", {"data": doc})
        if err:
            return None, f"calcolo dei totali: {err}"
        dovuto = round(float(((t or {}).get("data") or {}).get("amount_due") or 0), 2)
        if abs(dovuto - imp) < 0.005:
            return doc, None
        doc["items_list"][0]["net_price"] = round(doc["items_list"][0]["net_price"] + (imp - dovuto) / (1 + cassa / 100), 2)
    return None, f"il totale calcolato ({dovuto:.2f} €) non coincide con il pagamento ({imp:.2f} €)"


def crea_fatture(conn, cid, righe):
    """Crea le fatture in ordine di data. Si ferma al primo errore."""
    pos = _metodo_pos(cid)
    fatte = []
    for r in sorted(righe, key=lambda x: str(x["quando"])):
        doc, err = prepara_fattura(cid, r, pos)
        if err:
            return fatte, f"{str(r['quando'])[:16]} · {r['entity_nome']}: {err}"
        res, err = fc.scrivi("POST", f"/c/{cid}/issued_documents", {"data": doc})
        if err:
            return fatte, f"{str(r['quando'])[:16]} · {r['entity_nome']}: {err}"
        nuovo = (res or {}).get("data") or {}
        _esegui(conn, "UPDATE recupero_pagamenti SET stato='creata', fattura_id=%s, aggiornato_il=now() WHERE sumup_id=%s",
                (nuovo.get("id"), r["sumup_id"]))
        fatte.append(f"{nuovo.get('number', '')}/{nuovo.get('numeration', '')} · {str(r['quando'])[:10]} · {r['entity_nome']} · {float(r['importo']):.2f} €")
    return fatte, None


# ───────────────────────────── interfaccia ─────────────────────────────
def _cid():
    lista, err = fc.aziende()
    if err or not lista:
        return None, err or "nessuna azienda"
    cfg = fc._cfg().get("company_id")
    return (int(cfg) if cfg else int(lista[0]["id"])), None


def render_recupero(conn=None, is_admin=True):
    st.header("🧾 Recupero fatture da SumUp")
    st.caption("Abbini ogni pagamento SumUp al paziente; il gestionale prepara la fattura uguale all'ultima di quel paziente. "
               "In questa versione NON crea fatture: prepara l'elenco da controllare.")
    if not is_admin:
        st.info("Pagina riservata all'amministratore."); return
    if conn is None:
        st.info("Database non disponibile."); return
    assicura_tabella(conn)

    f = st.file_uploader("Export SumUp («resoconto-vendite…csv»)", type=["csv"], key="rec_csv")
    if f is not None:
        pag = leggi_sumup(f.getvalue())
        nuovi = 0
        for p in pag:
            if not _righe(conn, "SELECT 1 AS x FROM recupero_pagamenti WHERE sumup_id=%s", (p["sumup_id"],)):
                _esegui(conn, "INSERT INTO recupero_pagamenti (sumup_id, quando, importo, metodo) VALUES (%s,%s,%s,%s)",
                        (p["sumup_id"], p["quando"], p["importo"], p["metodo"])); nuovi += 1
        st.success(f"File letto: {len(pag)} pagamenti ({nuovi} nuovi, gli altri erano già caricati).")

    tutti = _righe(conn, "SELECT * FROM recupero_pagamenti ORDER BY quando")
    if not tutti:
        st.info("Carica l'export di SumUp per cominciare."); return

    cid, err = _cid()
    cid_g = cid
    if err:
        st.error(f"Fatture in Cloud non raggiungibile: {err}"); return
    anno = min(r["quando"] for r in tutti).year if isinstance(tutti[0]["quando"], dt.datetime) else dt.date.today().year
    with st.spinner("Leggo le tue fatture da Fatture in Cloud per imparare le abitudini dei pazienti…"):
        docs, err = storico_fatture(cid, anno)
    if err:
        st.error(f"Lettura fatture: {err}"); return
    P = profili(docs)
    nomi_tutti = sorted({(p["nome"], k) for k, p in P.items() if p["nome"]})

    fatti = sum(r["stato"] in ("abbinato", "gia_fatturata", "escluso", "creata") for r in tutti)
    st.progress(fatti / len(tutti), text=f"Pagamenti sistemati: {fatti} su {len(tutti)} · fatture lette da Fatture in Cloud: {len(docs)}")

    # già fatturate: fatture di Fatture in Cloud con stessa data e importo (suggerimento)
    fatt_giorno = collections.Counter((str(d.get("date"))[:10], round(float(d.get("amount_gross") or 0), 2)) for d in docs)

    giorni = collections.OrderedDict()
    for r in tutti:
        q = r["quando"] if isinstance(r["quando"], dt.datetime) else dt.datetime.fromisoformat(str(r["quando"]))
        r["_q"] = q; giorni.setdefault(q.date(), []).append(r)

    solo_aperti = st.toggle("Mostra solo i giorni con pagamenti ancora da sistemare", value=True)
    for g, lista in giorni.items():
        aperti = sum(r["stato"] == "da_scegliere" for r in lista)
        if solo_aperti and not aperti:
            continue
        gia_fatt = {}
        with st.expander(f"{GIORNI[g.weekday()]} {g:%d/%m} · {len(lista)} pagamenti · {aperti} da sistemare", expanded=aperti > 0):
            scelti_oggi = {r["chiave"] for r in lista if r.get("chiave")}
            for r in lista:
                imp = round(float(r["importo"]), 2)
                if r["stato"] == "creata":
                    st.markdown(f"**{r['_q']:%H:%M}** · **{imp:.2f} €** · ✅ fattura creata · {r.get('entity_nome') or ''}")
                    continue
                chiave_g = (g.isoformat(), imp)
                n_fatt = fatt_giorno.get(chiave_g, 0) - gia_fatt.get(chiave_g, 0)
                cand = candidati(P, {"importo": imp, "quando": r["_q"]}, scelti_oggi - {r.get("chiave")})
                opz = [DA_SCEGLIERE, GIA, ESCLUSO] + [f"{p['nome']} — {mot}" for _, _, p, mot in cand] + ["🔍 Altro paziente…"]
                chiavi = [None, "GIA", "NO"] + [k for _, k, _, _ in cand] + ["ALTRO"]
                attuale = {"gia_fatturata": "GIA", "escluso": "NO"}.get(r["stato"]) or (r.get("chiave") if r["stato"] == "abbinato" else None)
                if attuale and attuale not in chiavi and attuale in P:     # scelto prima con «altro paziente»: lo rimetto tra le opzioni
                    opz.insert(3, f"{P[attuale]['nome']} — scelto da te"); chiavi.insert(3, attuale)
                idx = chiavi.index(attuale) if attuale in chiavi else 0
                c1, c2 = st.columns([1, 4])
                c1.markdown(f"**{r['_q']:%H:%M}** · **{imp:.2f} €**" + ("  \n🟢 forse già fatturata" if n_fatt > 0 and r["stato"] == "da_scegliere" else ""))
                if n_fatt > 0:
                    gia_fatt[chiave_g] = gia_fatt.get(chiave_g, 0) + 1
                scelta = c2.selectbox("Paziente", opz, index=idx, key=f"rec_{r['sumup_id']}", label_visibility="collapsed")
                k = chiavi[opz.index(scelta)]
                if k == "ALTRO":
                    nome = c2.selectbox("Cerca il paziente", [n for n, _ in nomi_tutti], index=None, key=f"rec_altro_{r['sumup_id']}",
                                        placeholder="Scrivi il cognome…")
                    k = next((kk for n, kk in nomi_tutti if n == nome), None) if nome else None
                    if not k:
                        continue
                nuovo_stato = {None: "da_scegliere", "GIA": "gia_fatturata", "NO": "escluso"}.get(k, "abbinato")
                if nuovo_stato == "abbinato":
                    p = P[k]; u = p["ultima"] or {}
                    if r["stato"] != "abbinato" or r.get("chiave") != k:
                        _esegui(conn, "UPDATE recupero_pagamenti SET stato='abbinato', chiave=%s, entity_id=%s, entity_nome=%s, numerazione=%s, "
                                      "descrizione=%s, aggiornato_il=now() WHERE sumup_id=%s",
                                (k, p["id"], p["nome"], u.get("numerazione"), u.get("descrizione"), r["sumup_id"]))
                        r.update(stato="abbinato", chiave=k)
                    c2.caption(f"→ fattura «{u.get('descrizione') or '—'}» · numerazione {u.get('numerazione') or 'principale'} · "
                               f"come l'ultima del {u.get('data'):%d/%m}" if u.get("data") else "→ nessuna fattura precedente da copiare")
                elif nuovo_stato != r["stato"]:
                    _esegui(conn, "UPDATE recupero_pagamenti SET stato=%s, chiave=NULL, entity_id=NULL, entity_nome=NULL, aggiornato_il=now() "
                                  "WHERE sumup_id=%s", (nuovo_stato, r["sumup_id"]))
                    r["stato"] = nuovo_stato

    st.markdown("### Anteprima delle fatture da creare")
    da_fare = _righe(conn, "SELECT * FROM recupero_pagamenti WHERE stato='abbinato' ORDER BY quando")
    for r in da_fare:      # id dell'ultima fattura del paziente, da copiare
        p = P.get(r.get("chiave") or "")
        r["_ultima_id"] = (p or {}).get("ultima", {}).get("id") if p else None
    if da_fare:
        import pandas as pd
        st.dataframe(pd.DataFrame([{"Data pagamento": str(r["quando"])[:16], "Paziente": r["entity_nome"],
                                    "Importo": f"{float(r['importo']):.2f} €", "Numerazione": r["numerazione"] or "principale",
                                    "Descrizione": r["descrizione"]} for r in da_fare]), hide_index=True, use_container_width=True)
        st.caption(f"{len(da_fare)} fatture pronte da creare, per {sum(float(r['importo']) for r in da_fare):.2f} €. "
                   "Data della fattura = data del pagamento. Si creano in ordine di data, così i numeri restano in sequenza.")
        senza = [r for r in da_fare if not r.get("_ultima_id")]
        if senza:
            st.warning(f"{len(senza)} pazienti non hanno fatture precedenti da copiare: per ora si saltano.")
        pronti = [r for r in da_fare if r.get("_ultima_id")]
        primo_ok = st.session_state.get("rec_prova_ok")
        st.markdown("**1 · Prima una sola fattura di prova**: controllala in Fatture in Cloud (numero, data, importi, ENPAP, diciture).")
        if st.button("🧪 Crea SOLO la prima fattura (prova)", disabled=not pronti, key="rec_prova"):
            with st.spinner("Creo la fattura di prova…"):
                fatte, err = crea_fatture(conn, cid_g, pronti[:1])
            if err:
                st.error(f"Non creata: {err}")
            else:
                st.session_state["rec_prova_ok"] = fatte[0]; st.rerun()
        if primo_ok:
            st.success(f"Fattura di prova creata: {primo_ok}. Aprila in Fatture in Cloud e confrontala con una delle tue.")
            st.markdown("**2 · Se è identica alle tue, crea tutte le altre.**")
            conferma = st.checkbox("Ho controllato la fattura di prova in Fatture in Cloud ed è corretta", key="rec_conf")
            if st.button(f"✅ Crea le altre {len(pronti)} fatture", type="primary", disabled=not (conferma and pronti), key="rec_tutte"):
                with st.spinner("Creo le fatture in ordine di data…"):
                    fatte, err = crea_fatture(conn, cid_g, pronti)
                st.success(f"Create {len(fatte)} fatture.")
                if err:
                    st.error(f"Mi sono fermato qui: {err}. Le fatture create prima restano valide; correggi e riprova.")
                with st.expander("Elenco delle fatture create"):
                    for x in fatte:
                        st.write("• " + x)
    else:
        st.caption("Nessun pagamento abbinato per ora.")
