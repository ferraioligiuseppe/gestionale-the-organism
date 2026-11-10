# -*- coding: utf-8 -*-
"""
ui_incassi.py — Vista «💶 Incassi» del brogliaccio.

1. Riepilogo del mese: incassato per professionista, sede, prestazione e metodo; da pagare.
2. Fatture da fare: Prepara → anteprima → Crea, con lo stesso metodo del recupero SumUp
   (copia dell'ultima fattura del paziente in Fatture in Cloud, data = giorno della seduta,
   totale verificato con /totals). Poi la riga passa a «Fatta» e il passo si chiude.
3. Incassi SumUp del giorno: dalla API SumUp (Secrets [sumup] api_key) oppure dall'export CSV;
   ogni incasso si abbina a una riga del brogliaccio o diventa una riga nuova.
"""
from __future__ import annotations

import datetime as dt
import json
import unicodedata
import urllib.parse
import urllib.request

import streamlit as st

from . import db_brogliaccio as db

MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto",
        "settembre", "ottobre", "novembre", "dicembre"]
NUM_ULTIMA = "(come l'ultima fattura del paziente)"
NUMERAZIONI = [NUM_ULTIMA, "", "/psy", "/ESAMI", "/ONLINE", "/pagani", "/sds"]
NUM_NOMI = {"": "Principale (senza suffisso)", "/psy": "/psy · terapia", "/ESAMI": "/ESAMI · esami strumentali",
            "/ONLINE": "/ONLINE · online", "/pagani": "/pagani", "/sds": "/sds · stanza del sale"}


def _norm(s) -> str:
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().upper()
    return " ".join(s.replace("'", " ").split())


def vista_incassi(conn, operatori, io, pazienti, etichetta_paz, utente):
    t1, t2, t3 = st.tabs(["📊 Riepilogo del mese", "🧾 Fatture da fare", "💳 SumUp del giorno"])
    with t1:
        _riepilogo(conn)
    with t2:
        _fatture(conn, utente)
    with t3:
        _sumup(conn, operatori, io, pazienti, etichetta_paz, utente)


# ═════════════════════════════ 1 · Riepilogo del mese ═════════════════════════════
def _riepilogo(conn):
    oggi = dt.date.today()
    c1, c2 = st.columns(2)
    anno = c1.selectbox("Anno", list(range(oggi.year, oggi.year - 4, -1)), key="inc_anno")
    mese = c2.selectbox("Mese", list(range(1, 13)), index=oggi.month - 1, format_func=lambda m: MESI[m - 1].capitalize(),
                        key="inc_mese")
    da = dt.date(anno, mese, 1)
    a = (dt.date(anno + (mese == 12), mese % 12 + 1, 1) - dt.timedelta(days=1))
    righe = db.righe_con_importo(conn, da, a)
    if not righe:
        st.info(f"Nessuna riga con importo in {MESI[mese - 1]} {anno}. Gli importi si annotano in «✍️ Annota» "
                "per visite, sedute e pagamenti.")
        return
    t = db.riepilogo_importi(righe)
    m = st.columns(5)
    m[0].metric("Incassato", db.euro(t["incassato"]))
    for i, k in enumerate(db.INCASSATI, start=1):
        m[i].metric(k, db.euro(t["per_metodo"][k]))
    m[4].metric("Da pagare", db.euro(t["da_pagare"]), delta=f"{t['n_da_pagare']} da incassare" if t["n_da_pagare"] else None,
                delta_color="inverse")
    st.caption(f"{t['n']} righe con importo · 🧾 fatture ancora da fare: {t['fatture_da_fare']}")

    def tabella(chiave, etichetta):
        g = {}
        for r in righe:
            k = (r.get(chiave) or "—")
            x = g.setdefault(k, {etichetta: k, "Righe": 0, "Incassato": 0.0, "Da pagare": 0.0})
            x["Righe"] += 1
            if (r.get("pagamento") or "") in db.INCASSATI:
                x["Incassato"] += float(r["importo"])
            elif r.get("pagamento") == "Da pagare":
                x["Da pagare"] += float(r["importo"])
        out = sorted(g.values(), key=lambda x: -x["Incassato"])
        for x in out:
            x["Incassato"] = db.euro(x["Incassato"]); x["Da pagare"] = db.euro(x["Da pagare"])
        return out

    a1, a2 = st.columns(2)
    a1.markdown("**Per professionista**"); a1.dataframe(tabella("operatore", "Professionista"), hide_index=True, use_container_width=True)
    a2.markdown("**Per sede**"); a2.dataframe(tabella("sede", "Sede"), hide_index=True, use_container_width=True)
    st.markdown("**Per prestazione**")
    st.dataframe(tabella("prestazione", "Prestazione"), hide_index=True, use_container_width=True)
    da_pagare = [r for r in righe if r.get("pagamento") == "Da pagare"]
    if da_pagare:
        with st.expander(f"⏳ Da pagare ({len(da_pagare)})"):
            for r in da_pagare:
                st.markdown(f"- `{db.fmt(r['quando'])}` · **{db.nome_paziente(r)}** · {db.euro(r['importo'])} · "
                            f"{r.get('operatore') or '—'}")


# ═════════════════════════════ 2 · Fatture da fare ═════════════════════════════
def _cid():
    from ..recupero_fatture import _cid as cid
    return cid()


@st.cache_data(ttl=900, show_spinner="Leggo le fatture da Fatture in Cloud…")
def _profili(cid: int, anno: int):
    from .. import recupero_fatture as rf
    docs, err = rf.storico_fatture(cid, anno - 1)   # anno in corso e precedente: così si trova anche chi torna dopo l'estate
    return rf.profili(docs), err


def _metodo(cid, pagamento):
    """Metodo di pagamento di Fatture in Cloud che corrisponde a POS / contanti / bonifico."""
    from .. import fatture_cloud as fc
    cerca = {"POS": "pos", "Contanti": "contant", "Bonifico": "bonific"}.get(pagamento or "")
    if not cerca:
        return None
    d, _err = fc.chiama(f"/c/{cid}/settings/payment_methods")
    for m in ((d or {}).get("data") or []):
        if cerca in str(m.get("name", "")).lower():
            return {"id": m["id"]}
    return None


def trova_cliente(P, riga):
    """Clienti di Fatture in Cloud che corrispondono al paziente della riga (cognome e nome, in qualsiasi ordine)."""
    parole = [w for w in _norm(f"{riga.get('cognome') or ''} {riga.get('nome') or ''} {riga.get('nominativo') or ''}").split()
              if len(w) > 1]
    if not parole:
        return []
    out = []
    for k, p in P.items():
        nome = _norm(p.get("nome"))
        if all(w in nome.split() for w in parole[:2]):
            out.append((k, p))
    return sorted(out, key=lambda kp: -kp[1]["n"])


def prepara(riga, numerazione=NUM_ULTIMA):
    """Ritorna (documento, informazioni, errore)."""
    from .. import recupero_fatture as rf
    cid, err = _cid()
    if err:
        return None, None, f"Fatture in Cloud non collegato: {err}"
    giorno = riga["quando"].astimezone(db.TZ).date() if hasattr(riga["quando"], "astimezone") else riga["quando"]
    P, err = _profili(cid, giorno.year)
    if err and not P:
        return None, None, f"lettura delle fatture: {err}"
    trovati = trova_cliente(P, riga)
    if not trovati:
        return None, None, (f"Non trovo fatture precedenti per «{db.nome_paziente(riga)}» in Fatture in Cloud: "
                            "la prima fattura di un paziente nuovo va fatta a mano, poi le successive si fanno da qui.")
    k, p = trovati[0]
    r = {"_ultima_id": p["ultima"]["id"], "quando": giorno.isoformat(), "importo": float(riga["importo"])}
    doc, err = rf.prepara_fattura(cid, r, _metodo(cid, riga.get("pagamento")))
    if err:
        return None, None, err
    if numerazione != NUM_ULTIMA:
        doc["numeration"] = numerazione
    info = {"cid": cid, "cliente": p["nome"], "omonimi": len(trovati) - 1, "descrizione": p["ultima"]["descrizione"],
            "numerazione": doc.get("numeration") or "", "data": giorno, "importo": float(riga["importo"])}
    return doc, info, None


def crea(conn, riga, doc, info, utente):
    from .. import fatture_cloud as fc
    res, err = fc.scrivi("POST", f"/c/{info['cid']}/issued_documents", {"data": doc})
    if err:
        return None, err
    nuovo = (res or {}).get("data") or {}
    rif = f"{nuovo.get('number', '')}{nuovo.get('numeration', '')}".strip() or str(nuovo.get("id", ""))
    db.segna_fattura(conn, riga["id"], rif, utente)
    return rif, None


def _fatture(conn, utente):
    righe = db.fatture_da_fare(conn)
    if not righe:
        st.success("Nessuna fattura da fare: tutte le righe con «fattura da fare» sono state sistemate.")
        return
    st.caption("Ogni fattura copia l'**ultima fattura del paziente** in Fatture in Cloud (stessa descrizione, stessa "
               "numerazione, stesso cliente) con **data = giorno della seduta** e **importo = quello annotato**. "
               "Prima vedi l'anteprima, poi la crei.")
    for r in righe:
        chiave = f"inc_doc_{r['id']}"
        with st.expander(f"{db.fmt(r['quando'])} · {db.nome_paziente(r)} · {db.euro(r['importo'])} · {r.get('pagamento') or '—'}"
                         f" · {r.get('prestazione') or r['tipo']}"):
            num = st.selectbox("Numerazione", NUMERAZIONI, key=f"inc_num_{r['id']}",
                               format_func=lambda n: n if n == NUM_ULTIMA else NUM_NOMI.get(n, n))
            if st.button("🔎 Prepara la fattura", key=f"inc_prep_{r['id']}"):
                st.session_state[chiave] = prepara(r, num)
            doc, info, err = st.session_state.get(chiave, (None, None, None))
            if err:
                st.warning(err)
            if doc and info:
                st.markdown(f"**Cliente:** {info['cliente']}" + (f" _(ci sono altri {info['omonimi']} clienti simili: controlla)_" if info["omonimi"] else "")
                            + f"  \n**Descrizione:** {info['descrizione'] or '—'}  \n**Numerazione:** {info['numerazione'] or 'Principale'}"
                            + f"  \n**Data:** {info['data'].strftime('%d/%m/%Y')} · **Totale:** {db.euro(info['importo'])} (verificato da Fatture in Cloud)")
                if st.button("✅ Crea la fattura in Fatture in Cloud", key=f"inc_crea_{r['id']}", type="primary"):
                    rif, err = crea(conn, r, doc, info, utente)
                    st.session_state.pop(chiave, None)
                    if err:
                        st.error(f"Fattura non creata: {err}")
                    else:
                        st.success(f"Fattura {rif} creata ✔")
                        st.rerun()


# ═════════════════════════════ 3 · SumUp del giorno ═════════════════════════════
def _chiave_sumup():
    try:
        return (dict(st.secrets.get("sumup", {})).get("api_key") or "").strip()
    except Exception:
        return ""


def transazioni_sumup(giorno: dt.date):
    """Incassi riusciti di quel giorno dalla API SumUp. Ritorna (lista, errore)."""
    chiave = _chiave_sumup()
    if not chiave:
        return None, "chiave mancante"
    inizio = dt.datetime.combine(giorno, dt.time(0, 0), tzinfo=db.TZ)
    fine = inizio + dt.timedelta(days=1)
    q = urllib.parse.urlencode([("oldest_time", inizio.isoformat()), ("newest_time", fine.isoformat()),
                                ("limit", "100"), ("statuses[]", "SUCCESSFUL"), ("types[]", "PAYMENT")])
    req = urllib.request.Request(f"https://api.sumup.com/v0.1/me/transactions/history?{q}",
                                 headers={"Authorization": f"Bearer {chiave}", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as risp:
            dati = json.loads(risp.read().decode("utf-8"))
    except Exception as e:
        return None, f"SumUp non ha risposto ({e})"
    out = []
    for x in dati.get("items", []) or []:
        try:
            quando = dt.datetime.fromisoformat(str(x.get("timestamp")).replace("Z", "+00:00")).astimezone(db.TZ)
        except Exception:
            continue
        out.append({"codice": x.get("transaction_code") or x.get("id"), "quando": quando,
                    "importo": round(float(x.get("amount") or 0), 2), "metodo": x.get("payment_type") or "POS"})
    return sorted(out, key=lambda t: t["quando"]), None


def _da_csv(dati: bytes, giorno: dt.date):
    from ..recupero_fatture import leggi_sumup
    return [{"codice": p["sumup_id"], "quando": p["quando"].replace(tzinfo=db.TZ), "importo": round(p["importo"], 2),
             "metodo": p.get("metodo") or "POS"} for p in leggi_sumup(dati) if p["quando"].date() == giorno]


def _sumup(conn, operatori, io, pazienti, etichetta_paz, utente):
    giorno = st.date_input("Giorno", value=dt.date.today(), format="DD/MM/YYYY", key="inc_su_g")
    trans, err = transazioni_sumup(giorno)
    if err == "chiave mancante":
        st.info("Per avere gli incassi **in automatico** serve la chiave API di SumUp: dal sito SumUp → "
                "*Sviluppatori* → *Chiavi API* → crea una chiave e mettila nei Secrets del gestionale come  \n"
                "`[sumup]`  \n`api_key = \"sup_sk_…\"`  \nIntanto puoi caricare l'**export delle transazioni** del giorno.")
        f = st.file_uploader("Export SumUp (CSV)", type=["csv"], key="inc_su_csv")
        trans = _da_csv(f.getvalue(), giorno) if f else None
    elif err:
        st.warning(err)
    if not trans:
        if trans is not None:
            st.info("Nessun incasso SumUp in questo giorno.")
        return
    usati = db.codici_sumup(conn)
    righe_giorno = [r for r in db.del_giorno(conn, giorno) if r.get("importo") is not None]
    st.caption(f"{len(trans)} incassi · totale {db.euro(sum(t['importo'] for t in trans))}")
    per_id = {int(p["id"]): p for p in pazienti}
    for t in trans:
        testa = f"`{t['quando'].strftime('%H:%M')}` · **{db.euro(t['importo'])}** · {t['metodo']}"
        if t["codice"] in usati:
            rr = next((r for r in db.del_giorno(conn, giorno) if int(r["id"]) == usati[t["codice"]]), None)
            st.markdown(f"✅ {testa} → {db.nome_paziente(rr) if rr else 'abbinato'}")
            continue
        proposte = [r for r in righe_giorno if not r.get("sumup_code") and abs(float(r["importo"]) - t["importo"]) < 0.005]
        with st.expander(f"🟡 {t['quando'].strftime('%H:%M')} · {db.euro(t['importo'])} · da abbinare"):
            if proposte:
                etichette = {int(r["id"]): f"{db.fmt(r['quando'], ora=True)} · {db.nome_paziente(r)} · {r.get('operatore') or '—'}"
                             for r in proposte}
                scelta = st.selectbox("Riga di «Oggi in studio»", list(etichette), key=f"inc_ab_{t['codice']}",
                                      format_func=lambda i, _e=etichette: _e.get(i, f"riga {i}"))
                if st.button("🔗 Abbina", key=f"inc_abb_{t['codice']}"):
                    db.abbina_sumup(conn, scelta, t["codice"]); st.rerun()
            else:
                st.caption("Nessuna riga di quel giorno con lo stesso importo: annotala qui.")
            c1, c2 = st.columns([3, 2])
            pid = c1.selectbox("Paziente", [None] + list(per_id), key=f"inc_pz_{t['codice']}",
                               format_func=lambda x: "— scegli —" if x is None else (etichetta_paz(per_id[x]) if x in per_id else str(x)))
            chi = c2.selectbox("Chi", operatori, index=operatori.index(io) if io in operatori else 0, key=f"inc_op_{t['codice']}")
            prest = st.selectbox("Prestazione", db.PRESTAZIONI, key=f"inc_pr_{t['codice']}")
            if st.button("➕ Annota come nuova riga (fattura da fare)", key=f"inc_new_{t['codice']}", disabled=pid is None):
                db.aggiungi(conn, tipo=db.T_SEDUTA, operatore=chi, utente=utente, paziente_id=pid, quando=t["quando"],
                            importo=t["importo"], pagamento="POS", fattura="Da fare", prestazione=prest,
                            prossimo_passo="Fare la fattura", assegnato_a=chi, scadenza=giorno + dt.timedelta(days=2),
                            sumup_code=t["codice"], descrizione="incasso SumUp")
                st.rerun()
