"""Registri eventi di Pegasis per la sincronia con l'EEG.

Pegasis li deposita da solo nella «cassetta postale» su Cloudflare (Worker pegasis-eventi + R2 privato).
Il gestionale li legge con due segreti di Streamlit:
    PEGASIS_EVENTI_URL   = "https://pegasis-eventi.<nome>.workers.dev"
    PEGASIS_EVENTI_TOKEN = "<la frase scelta come ADMIN_TOKEN su Cloudflare>"
Solo libreria standard (urllib): nessuna dipendenza nuova.
"""
import json
import os
import urllib.parse
import urllib.request


def _config():
    url = token = ""
    try:
        import streamlit as st
        url = st.secrets.get("PEGASIS_EVENTI_URL", "")
        token = st.secrets.get("PEGASIS_EVENTI_TOKEN", "")
    except Exception:
        pass
    url = (url or os.environ.get("PEGASIS_EVENTI_URL", "")).rstrip("/")
    token = token or os.environ.get("PEGASIS_EVENTI_TOKEN", "")
    return url, token


def configurato() -> bool:
    url, token = _config()
    return bool(url and token)


def _richiesta(percorso: str, metodo: str = "GET", timeout: int = 20) -> bytes:
    url, token = _config()
    req = urllib.request.Request(url + percorso, method=metodo, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def elenco(codice: str = "") -> list[dict]:
    """File presenti (di un codice o di tutti): chiave, byte, caricato."""
    q = "?codice=" + urllib.parse.quote(codice.upper()) if codice else ""
    return json.loads(_richiesta("/eventi" + q)).get("file", [])


def scarica(chiave: str) -> str:
    return _richiesta("/" + urllib.parse.quote(chiave)).decode("utf-8")


def cancella_codice(codice: str) -> int:
    """Ritiro dallo studio: cancella tutti i registri del codice. Restituisce quanti file."""
    return int(json.loads(_richiesta("/eventi?codice=" + urllib.parse.quote(codice.upper()), "DELETE")).get("cancellati", 0))


def riassunto(testo: str) -> dict:
    """Intestazione del registro: brano, inizio, uscita, conteggi e numero di eventi."""
    info = {"brano": "", "inizio": "", "uscita": "", "conteggi": "", "eventi": 0}
    in_tabella = False
    for riga in testo.splitlines():
        parti = riga.split(";")
        if in_tabella:
            if len(parti) > 5 and parti[5] not in ("INIZIO", "FINE"):
                info["eventi"] += 1
        elif parti[0] in ("brano", "inizio", "uscita", "conteggi") and len(parti) > 1:
            info[parti[0]] = parti[1]
        elif parti[0] == "n":
            in_tabella = True
    return info


def codice_da_chiave(chiave: str) -> str:
    parti = chiave.split("/")
    return parti[1] if len(parti) >= 3 else ""
