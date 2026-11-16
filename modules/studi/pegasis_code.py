"""Codici di programma Pegasis (formato «PGS1.») generati dal gestionale.

Stesso formato dell'app: campi chiave=valore uniti da «&», valori codificati come URL,
compressi con deflate senza intestazione e scritti in base64 URL senza «=» finali.
Il codice non contiene il nome del partecipante: solo programma, codice anonimo, gruppo e data di partenza.
"""
import base64
import zlib
from urllib.parse import quote_plus, unquote_plus

PREFIX = "PGS1."


def encode(fields: dict) -> str:
    text = "&".join(f"{k}={quote_plus(str(v), safe='')}" for k, v in fields.items())
    comp = zlib.compressobj(9, zlib.DEFLATED, -15)
    raw = comp.compress(text.encode("utf-8")) + comp.flush()
    return PREFIX + base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode(code: str) -> dict:
    """Legge un codice (anche dentro un messaggio). Solleva ValueError se non è valido."""
    start = code.find(PREFIX)
    if start < 0:
        raise ValueError("codice senza PGS1.")
    body = ""
    for ch in code[start + len(PREFIX):]:
        if ch.isalnum() or ch in "-_":
            body += ch
        else:
            break
    raw = base64.urlsafe_b64decode(body + "=" * (-len(body) % 4))
    text = zlib.decompress(raw, -15).decode("utf-8")
    out = {}
    for part in text.split("&"):
        k, _, v = part.partition("=")
        out[k] = unquote_plus(v)
    return out


def study_program(nome: str, codice: str, gruppo: str, start_ms: int, sessioni: int = 20,
                  minuti: int = 30, brani: list[str] | None = None, nota: str = "") -> str:
    """Programma dello studio: livello Basic, uguale per tutti; [start_ms] = 0 per partire subito."""
    return encode({
        "n": nome,
        "no": nota,
        "m": minuti,
        "s": sessioni,
        "t": ",".join(brani or []),
        "lv": "BASIC",
        "at": "true",
        "pc": codice,
        "gr": gruppo,
        "da": int(start_ms),
    })
