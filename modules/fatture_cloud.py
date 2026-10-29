# -*- coding: utf-8 -*-
"""🧾 Collegamento con Fatture in Cloud (API v2).

Fase 1: prova del collegamento in SOLA LETTURA (azienda, ultime fatture, metodi di pagamento,
aliquote IVA). Nessuna scrittura: le fatture si creeranno nella fase successiva, partendo da bozze.
Token: Secrets → [fattureincloud] access_token = "..."  (facoltativo: company_id = 123)
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

import streamlit as st

API = "https://api-v2.fattureincloud.it"


def _cfg():
    try:
        return dict(st.secrets.get("fattureincloud", {}))
    except Exception:
        return {}


def chiama(percorso: str, parametri: dict | None = None):
    """GET sull'API. Ritorna (dati, errore leggibile)."""
    tok = _cfg().get("access_token")
    if not tok:
        return None, "manca il token nei Secrets ([fattureincloud] access_token)"
    url = API + percorso + ("?" + urllib.parse.urlencode(parametri) if parametri else "")
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {tok}", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode("utf-8")), None
    except urllib.error.HTTPError as e:
        motivo = {401: "token non valido o revocato: rigeneralo in Fatture in Cloud (Applicazioni collegate)",
                  403: "permesso mancante sul token: ricrealo spuntando anche questa voce",
                  404: "risorsa non trovata (azienda sbagliata?)",
                  429: "troppe richieste ravvicinate: riprova fra un minuto"}.get(e.code, f"errore {e.code}")
        return None, motivo
    except Exception as e:
        return None, f"collegamento non riuscito: {e}"


def aziende():
    d, err = chiama("/user/companies")
    if err:
        return [], err
    return (d or {}).get("data", {}).get("companies", []) or [], None


def _euro(v):
    try:
        return f"{float(v):,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "—"


def render_fatture_cloud(conn=None, is_admin: bool = True):
    st.header("🧾 Fatture in Cloud · prova del collegamento")
    st.caption("Sola lettura: questa pagina non crea né modifica nulla in Fatture in Cloud.")
    if not is_admin:
        st.info("Pagina riservata all'amministratore."); return
    if not _cfg().get("access_token"):
        st.warning("Manca il token. Nei Secrets aggiungi:\n\n```\n[fattureincloud]\naccess_token = \"...\"\n```")
        return

    with st.spinner("Mi collego a Fatture in Cloud…"):
        lista, err = aziende()
    if err:
        st.error(f"❌ Collegamento non riuscito: {err}."); return
    if not lista:
        st.error("Il token funziona ma non vede nessuna azienda: ricrealo scegliendo l'azienda giusta."); return
    st.success(f"✅ Collegato. Aziende visibili con questo token: {len(lista)}.")

    cid_cfg = _cfg().get("company_id")
    nomi = {int(a["id"]): f"{a.get('name', '')} (id {a['id']})" for a in lista}
    if cid_cfg and int(cid_cfg) in nomi:
        cid = int(cid_cfg)
    elif len(nomi) == 1:
        cid = next(iter(nomi))
    else:
        cid = st.selectbox("Azienda", list(nomi), format_func=lambda k: nomi[k])
        st.caption(f"Per fissarla, aggiungi nei Secrets sotto [fattureincloud]: company_id = {cid}")
    st.subheader(nomi[cid])

    info, err = chiama(f"/c/{cid}/company/info")
    if not err:
        dati = (info or {}).get("data", {}) or {}
        sotto = dati.get("info") or dati.get("company_info") or {}
        piva = dati.get("vat_number") or sotto.get("vat_number") or "—"
        cf = dati.get("tax_code") or sotto.get("tax_code") or "—"
        st.caption(f"Partita IVA {piva} · Codice fiscale {cf}")

    st.markdown("#### Ultime 10 fatture emesse")
    docs, err = chiama(f"/c/{cid}/issued_documents", {"type": "invoice", "per_page": 10, "page": 1, "sort": "-date"})
    if err:
        st.error(f"Fatture: {err}.")
    else:
        righe = []
        for d in (docs or {}).get("data", []) or []:
            ent = d.get("entity") or {}
            righe.append({"Numero": f"{d.get('number', '')}{d.get('numeration', '') or ''}", "Data": d.get("date", ""),
                          "Cliente": ent.get("name", ""), "Totale": _euro(d.get("amount_gross")),
                          "Netto": _euro(d.get("amount_net"))})
        if righe:
            import pandas as pd
            st.dataframe(pd.DataFrame(righe), use_container_width=True, hide_index=True)
        else:
            st.info("Nessuna fattura trovata (o non ancora emesse quest'anno).")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Metodi di pagamento")
        pm, err = chiama(f"/c/{cid}/settings/payment_methods")
        if err:
            st.error(err)
        else:
            for m in (pm or {}).get("data", []) or []:
                st.write(f"• {m.get('name')} (id {m.get('id')})")
    with c2:
        st.markdown("#### Aliquote IVA / esenzioni")
        iva, err = chiama(f"/c/{cid}/info/vat_types")
        if err:
            st.error(err)
        else:
            for v in ((iva or {}).get("data", []) or [])[:25]:
                st.write(f"• {v.get('value', '')}% — {v.get('description', '')} (id {v.get('id')})")
    st.caption("Se vedi azienda, fatture, metodi di pagamento e aliquote, il collegamento è pronto per la fase 2: "
               "creare le fatture dal gestionale (prima come bozze).")
