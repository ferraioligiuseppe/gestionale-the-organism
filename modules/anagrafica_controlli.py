# -*- coding: utf-8 -*-
"""Controlli sull'anagrafica condivisi da scheda completa e modifica rapida.

- trova_doppioni(): stesso codice fiscale, oppure stesso cognome con stessa
  data di nascita o stesso nome → probabilmente lo stesso paziente.
- trova_famiglia(): stessa via e civico (probabile stesso nucleo familiare)
  oppure stessa via con civico diverso, nella stessa città.
  Gli indirizzi vengono normalizzati: «P.zza Roma, n. 5» = «piazza roma 5».
- cerca_indirizzi() / risolvi_indirizzo(): ricerca della via con suggerimenti.
  Fornitore: Google Places se in Secrets c'è la chiave, altrimenti
  OpenStreetMap (Nominatim, gratuito). Si invia SOLO via e città, mai il
  nome del paziente.

Configurazione (Streamlit → Settings → Secrets), tutta facoltativa:

    [indirizzi]
    google_places_api_key = "AIza..."   # se presente si usa Google
    provider = "osm"                     # per forzare OpenStreetMap
"""
from __future__ import annotations

import datetime as _dt
import re
import unicodedata
import uuid

import streamlit as st

# ════════════════════════════════════════════════════════════════════
#  NORMALIZZAZIONE
# ════════════════════════════════════════════════════════════════════

_ABBR = {
    "v": "via", "pza": "piazza", "pzza": "piazza", "pz": "piazza",
    "cso": "corso", "c": "corso", "vle": "viale", "lgo": "largo",
    "vic": "vicolo", "vico": "vicolo", "trav": "traversa", "tr": "traversa",
    "loc": "localita", "fraz": "frazione", "str": "strada", "sp": "strada provinciale",
    "ss": "strada statale", "pta": "piazzetta",
}
_SCARTA = {"n", "nr", "num", "no", "civ", "civico", "snc"}


def _senza_accenti(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s)
                   if not unicodedata.combining(c))


def normalizza_testo(s) -> str:
    s = _senza_accenti(str(s or "")).lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", s)).strip()


def scomponi_indirizzo(s) -> tuple[str, str]:
    """(via normalizzata, civico normalizzato). Es. «P.zza Roma, n. 5/A» → ('piazza roma', '5a')."""
    s = _senza_accenti(str(s or "")).lower()
    s = re.sub(r"[,;:]", " ", s)
    tokens = []
    for t in s.split():
        t = t.replace(".", "").replace("'", " ").strip()
        if not t:
            continue
        for p in t.split():
            if p in _SCARTA:
                continue
            p = re.sub(r"^(n|nr|num|civ)(\d)", r"\2", p)
            tokens.append(_ABBR.get(p, p) if not tokens else p)
    # civico = token finali con cifre (più un'eventuale lettera: «5 a» → «5a»)
    i = len(tokens)
    while i > 1:
        t = tokens[i - 1]
        if re.search(r"\d", t) or (len(t) == 1 and t.isalpha() and i >= 2
                                     and re.search(r"\d", tokens[i - 2])):
            i -= 1
        else:
            break
    via = [re.sub(r"[^a-z0-9 ]", "", t) for t in tokens[:i]]
    civ = [re.sub(r"[^a-z0-9]", "", t) for t in tokens[i:]]
    return " ".join(x for x in via if x), "".join(civ)


def _a_data(v):
    if v is None or v == "":
        return None
    if isinstance(v, _dt.datetime):
        return v.date()
    if isinstance(v, _dt.date):
        return v
    s = str(v).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y"):
        try:
            return _dt.datetime.strptime(s[:10], fmt).date()
        except Exception:
            pass
    return None


def _righe(conn, sql, params) -> list[dict]:
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
        cur.close()
        return [r if isinstance(r, dict) else dict(zip(cols, r)) for r in rows]
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return []


def _nome_paz(r: dict) -> str:
    n = f"{(r.get('cognome') or '').strip()} {(r.get('nome') or '').strip()}".strip()
    stato = (r.get("stato_paziente") or "ATTIVO").upper()
    return n + (f" ({stato.lower()})" if stato != "ATTIVO" else "")


# ════════════════════════════════════════════════════════════════════
#  DOPPIONI
# ════════════════════════════════════════════════════════════════════

def trova_doppioni(conn, cognome="", nome="", data_nascita=None, cf="",
                   escludi_id=None) -> list[dict]:
    """Pazienti (anche archiviati) che sembrano la stessa persona.
    Ogni voce: {id, nome, motivo, certo(bool)}."""
    cog = normalizza_testo(cognome)
    cf = (cf or "").strip().upper()
    if not cog and len(cf) < 16:
        return []
    righe = _righe(
        conn,
        "SELECT id, cognome, nome, data_nascita, codice_fiscale, stato_paziente "
        "FROM pazienti WHERE LOWER(TRIM(cognome)) = %s "
        "OR (%s <> '' AND UPPER(TRIM(COALESCE(codice_fiscale,''))) = %s)",
        ((cognome or "").strip().lower(), cf if len(cf) == 16 else "", cf),
    )
    dn = _a_data(data_nascita)
    nom = normalizza_testo(nome)
    out = []
    for r in righe:
        if escludi_id is not None and int(r["id"]) == int(escludi_id):
            continue
        r_cf = (r.get("codice_fiscale") or "").strip().upper()
        stesso_cog = normalizza_testo(r.get("cognome")) == cog
        r_dn = _a_data(r.get("data_nascita"))
        if len(cf) == 16 and r_cf == cf:
            motivo, certo = "stesso codice fiscale", True
        elif stesso_cog and dn and r_dn == dn:
            motivo, certo = f"stesso cognome e stessa data di nascita ({dn.strftime('%d/%m/%Y')})", True
        elif stesso_cog and nom and normalizza_testo(r.get("nome")) == nom:
            motivo, certo = "stesso cognome e nome", False
        else:
            continue
        out.append({"id": int(r["id"]), "nome": _nome_paz(r), "motivo": motivo, "certo": certo})
    return out


# ════════════════════════════════════════════════════════════════════
#  STESSA FAMIGLIA / STESSA VIA
# ════════════════════════════════════════════════════════════════════

_TIPI_VIA = {"via", "viale", "piazza", "piazzetta", "corso", "largo", "vicolo",
             "traversa", "localita", "frazione", "strada", "contrada", "salita", "rione"}


def vie_uguali(a: str, b: str) -> bool:
    """«via antonio de rosa» = «via de rosa» (il nome proprio spesso si omette)."""
    if not a or not b:
        return False
    if a == b:
        return True
    ta, tb = a.split()[0], b.split()[0]
    if ta in _TIPI_VIA and tb in _TIPI_VIA and ta != tb:
        return False  # «corso Italia» ≠ «via Italia»
    ca = [t for t in a.split() if t not in _TIPI_VIA]
    cb = [t for t in b.split() if t not in _TIPI_VIA]
    if not ca or not cb:
        return False
    corto, lungo = (ca, cb) if len(ca) <= len(cb) else (cb, ca)
    return lungo[-len(corto):] == corto


def trova_famiglia(conn, indirizzo="", citta="", escludi_id=None) -> dict:
    """{'stesso_indirizzo': [...], 'stessa_via': [...]} — pazienti attivi e non."""
    via, civ = scomponi_indirizzo(indirizzo)
    if not via:
        return {"stesso_indirizzo": [], "stessa_via": []}
    citta_n = normalizza_testo(citta)
    sql = ("SELECT id, cognome, nome, indirizzo, citta, stato_paziente FROM pazienti "
           "WHERE COALESCE(TRIM(indirizzo),'') <> ''")
    params: tuple = ()
    if citta_n:
        sql += " AND LOWER(TRIM(COALESCE(citta,''))) IN (%s, '')"
        params = ((citta or "").strip().lower(),)
    stesso, stessa_via = [], []
    for r in _righe(conn, sql, params):
        if escludi_id is not None and int(r["id"]) == int(escludi_id):
            continue
        r_via, r_civ = scomponi_indirizzo(r.get("indirizzo"))
        if not vie_uguali(r_via, via):
            continue
        voce = {"id": int(r["id"]), "nome": _nome_paz(r), "indirizzo": r.get("indirizzo") or ""}
        if civ and r_civ == civ or (not civ and not r_civ):
            stesso.append(voce)
        else:
            stessa_via.append(voce)
    return {"stesso_indirizzo": stesso, "stessa_via": stessa_via}


def mostra_avvisi(conn, *, cognome="", nome="", data_nascita=None, cf="",
                  indirizzo="", citta="", escludi_id=None) -> list[dict]:
    """Mostra a schermo gli avvisi e ritorna i doppioni trovati
    (il chiamante decide se bloccare il salvataggio)."""
    doppioni = trova_doppioni(conn, cognome, nome, data_nascita, cf, escludi_id)
    for d in doppioni:
        icona = "⚠️" if d["certo"] else "🔎"
        st.warning(f"{icona} **Possibile doppione:** esiste già **{d['nome']}** "
                   f"(ID {d['id']}) — {d['motivo']}.")
    fam = trova_famiglia(conn, indirizzo, citta, escludi_id)
    if fam["stesso_indirizzo"]:
        nomi = ", ".join(f"**{x['nome']}**" for x in fam["stesso_indirizzo"])
        st.info(f"🏠 **Stessa famiglia?** Allo stesso indirizzo vive già: {nomi}.")
    if fam["stessa_via"]:
        nomi = ", ".join(f"{x['nome']} ({x['indirizzo']})" for x in fam["stessa_via"][:5])
        altri = len(fam["stessa_via"]) - 5
        st.caption(f"📍 Nella stessa via: {nomi}" + (f" e altri {altri}" if altri > 0 else "") + ".")
    return doppioni


# ════════════════════════════════════════════════════════════════════
#  RICERCA INDIRIZZO
# ════════════════════════════════════════════════════════════════════

def _cfg() -> dict:
    try:
        return dict(st.secrets.get("indirizzi", {}))
    except Exception:
        return {}


def fornitore() -> str:
    c = _cfg()
    if (c.get("provider") or "").lower() == "osm":
        return "osm"
    return "google" if c.get("google_places_api_key") else "osm"


def _civico_dal_testo(testo: str) -> str:
    m = re.search(r"(\d+\s*[/]?\s*[a-zA-Z]?)\s*$", (testo or "").strip())
    return m.group(1).replace(" ", "") if m else ""


@st.cache_data(ttl=86400, show_spinner=False)
def _cerca_osm(testo: str, comune: str, prov: str) -> list[dict]:
    import requests
    q = ", ".join(x for x in (testo, comune, prov, "Italia") if x)
    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": q, "format": "json", "addressdetails": 1,
                    "limit": 6, "countrycodes": "it"},
            headers={"User-Agent": "GestionaleStudioTheOrganism/1.0 (www.pnev.it)"},
            timeout=6,
        )
        dati = resp.json() if resp.status_code == 200 else []
    except Exception:
        return []
    civ_utente = _civico_dal_testo(testo)
    out, visti = [], set()
    for d in dati:
        a = d.get("address") or {}
        via = a.get("road") or a.get("pedestrian") or a.get("square") or ""
        if not via:
            continue
        civ = a.get("house_number") or civ_utente
        citta = (a.get("city") or a.get("town") or a.get("village")
                 or a.get("municipality") or "")
        cap = a.get("postcode") or ""
        indirizzo = f"{via}, {civ}" if civ else via
        etichetta = f"{indirizzo} — {cap} {citta}".strip()
        if etichetta in visti:
            continue
        visti.add(etichetta)
        out.append({"etichetta": etichetta, "ref": None,
                    "dati": {"indirizzo": indirizzo, "cap": cap if len(cap) == 5 else "",
                             "citta": citta, "prov": ""}})
    return out


def _cerca_google(testo: str, comune: str, chiave: str, sessione: str) -> list[dict]:
    import requests
    try:
        resp = requests.post(
            "https://places.googleapis.com/v1/places:autocomplete",
            json={"input": ", ".join(x for x in (testo, comune) if x),
                  "includedRegionCodes": ["it"], "languageCode": "it",
                  "sessionToken": sessione},
            headers={"X-Goog-Api-Key": chiave}, timeout=6,
        )
        dati = resp.json() if resp.status_code == 200 else {}
    except Exception:
        return []
    out = []
    for s in dati.get("suggestions", []):
        p = s.get("placePrediction") or {}
        if p.get("placeId"):
            out.append({"etichetta": (p.get("text") or {}).get("text", ""),
                        "ref": p["placeId"], "dati": None})
    return out


def _dettagli_google(place_id: str, chiave: str, sessione: str, testo: str) -> dict | None:
    import requests
    try:
        resp = requests.get(
            f"https://places.googleapis.com/v1/places/{place_id}",
            params={"languageCode": "it", "sessionToken": sessione},
            headers={"X-Goog-Api-Key": chiave, "X-Goog-FieldMask": "addressComponents"},
            timeout=6,
        )
        comp = (resp.json() if resp.status_code == 200 else {}).get("addressComponents", [])
    except Exception:
        return None
    def _c(tipo, corto=False):
        for c in comp:
            if tipo in c.get("types", []):
                return c.get("shortText" if corto else "longText", "")
        return ""
    via = _c("route")
    if not via:
        return None
    civ = _c("street_number") or _civico_dal_testo(testo)
    return {"indirizzo": f"{via}, {civ}" if civ else via,
            "cap": _c("postal_code"),
            "citta": _c("locality") or _c("administrative_area_level_3"),
            "prov": _c("administrative_area_level_2", corto=True)}


def cerca_indirizzi(testo: str, comune: str = "", prov: str = "",
                    chiave_sessione: str = "_ind_sess") -> tuple[list[dict], str]:
    """(risultati, fornitore usato). Con Google, se non risponde, ripiega su OSM."""
    testo = (testo or "").strip()
    if len(testo) < 3:
        return [], fornitore()
    if fornitore() == "google":
        if chiave_sessione not in st.session_state:
            st.session_state[chiave_sessione] = str(uuid.uuid4())
        ris = _cerca_google(testo, comune, _cfg()["google_places_api_key"],
                            st.session_state[chiave_sessione])
        if ris:
            return ris, "google"
    return _cerca_osm(testo, comune, prov), "osm"


def risolvi_indirizzo(voce: dict, testo: str = "",
                      chiave_sessione: str = "_ind_sess") -> dict | None:
    if voce.get("dati"):
        return voce["dati"]
    if voce.get("ref"):
        dati = _dettagli_google(voce["ref"], _cfg().get("google_places_api_key", ""),
                                st.session_state.get(chiave_sessione, ""), testo)
        st.session_state.pop(chiave_sessione, None)  # la sessione Google si chiude qui
        return dati
    return None


NOME_FORNITORE = {"google": "Google", "osm": "OpenStreetMap"}


def ricerca_indirizzo_ui(key: str, comune: str, prov: str, on_scelto) -> None:
    """Riquadro «Trova l'indirizzo»: casella + Cerca + elenco risultati.
    on_scelto(dati) viene chiamata in un callback (può scrivere nello state
    dei widget del form). dati = {indirizzo, cap, citta, prov}."""
    k_q, k_ris, k_sel = f"{key}_ricind_q", f"{key}_ricind_ris", f"{key}_ricind_sel"
    k_sess = f"{key}_ricind_sess"

    def _cerca():
        ris, forn = cerca_indirizzi(st.session_state.get(k_q, ""), comune, prov, k_sess)
        st.session_state[k_ris] = (ris, forn)

    def _usa():
        ris, _ = st.session_state.get(k_ris, ([], ""))
        etichetta = st.session_state.get(k_sel)
        voce = next((r for r in ris if r["etichetta"] == etichetta), None)
        dati = risolvi_indirizzo(voce, st.session_state.get(k_q, ""), k_sess) if voce else None
        if dati:
            on_scelto(dati)
            st.session_state.pop(k_ris, None)
            st.session_state[k_q] = ""

    c1, c2 = st.columns([4, 1])
    with c1:
        st.text_input("🔍 Trova l'indirizzo", key=k_q,
                      placeholder=f"Via e civico{' a ' + comune.title() if comune else ''} — es. via De Rosa 46")
    with c2:
        st.markdown("<div style='height: 28px'></div>", unsafe_allow_html=True)
        st.button("Cerca", key=f"{key}_ricind_btn", on_click=_cerca, use_container_width=True)
    ris, forn = st.session_state.get(k_ris, ([], ""))
    if k_ris in st.session_state and not ris:
        st.caption("Nessun indirizzo trovato: prova a scrivere la via in un altro modo, "
                   "oppure compila il campo Indirizzo a mano.")
    if ris:
        c3, c4 = st.columns([4, 1])
        with c3:
            st.selectbox(f"Risultati ({NOME_FORNITORE.get(forn, forn)})",
                         [r["etichetta"] for r in ris], key=k_sel)
        with c4:
            st.markdown("<div style='height: 28px'></div>", unsafe_allow_html=True)
            st.button("✓ Usa", key=f"{key}_ricind_usa", on_click=_usa,
                      type="primary", use_container_width=True)


# ════════════════════════════════════════════════════════════════════
#  ELENCO COMUNI (stesso file usato per il codice fiscale)
# ════════════════════════════════════════════════════════════════════

@st.cache_data(show_spinner=False)
def opzioni_comuni() -> list[str]:
    """Etichette «COMUNE (PR)» ordinate, dal CSV dei codici catastali."""
    import csv
    import os
    qui = os.path.dirname(__file__)
    for path in ("codici_catastali_comuni.csv",
                 os.path.join(qui, "..", "codici_catastali_comuni.csv"),
                 os.path.join(qui, "codici_catastali_comuni.csv")):
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                righe = [(r.get("paese", "").strip().upper(), r.get("prov", "").strip().upper())
                         for r in csv.DictReader(f, delimiter=";")]
            return sorted(f"{c} ({p})" for c, p in righe if c and p)
    return []


@st.cache_data(show_spinner=False)
def _cap_per_comune() -> dict:
    import json
    import os
    path = os.path.join(os.path.dirname(__file__), "comuni.json")
    try:
        with open(path, encoding="utf-8") as f:
            return {(c["nome"].upper(), c["sigla"].upper()): c.get("cap", [])
                    for c in json.load(f)}
    except Exception:
        return {}


def cap_unico(comune: str, prov: str) -> str:
    """CAP se il comune ne ha uno solo, altrimenti stringa vuota."""
    caps = _cap_per_comune().get(((comune or "").upper(), (prov or "").upper()), [])
    return caps[0] if len(caps) == 1 else ""


def separa_etichetta(lab: str) -> tuple[str, str]:
    if lab and " (" in lab and lab.endswith(")"):
        return lab.rsplit(" (", 1)[0], lab.rsplit(" (", 1)[1].rstrip(")")
    return "", ""
