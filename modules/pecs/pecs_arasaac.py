# -*- coding: utf-8 -*-
"""Pittogrammi PECS in italiano — ricerca su ARASAAC e tessere stampabili.

I pittogrammi vengono dal catalogo ARASAAC (arasaac.org, Governo di Aragona,
licenza CC BY-NC-SA): si cercano per parola italiana, non per ID fisso, così
l'immagine corrisponde sempre al termine. L'ID trovato viene messo in cache nel
database, quindi la ricerca avviene una volta sola per item.

Uso tipico:
    from .pecs_arasaac import url_pittogramma, foglio_tessere_html
    url = url_pittogramma("Acqua")            # cerca, mette in cache, torna l'URL
    html = foglio_tessere_html(items, 6)      # foglio A4 pronto da stampare
"""
from __future__ import annotations
from typing import Dict, List, Optional, Tuple
import json
import urllib.parse
import urllib.request

API_BASE = "https://api.arasaac.org/api/pictograms"
CDN_BASE = "https://static.arasaac.org/pictograms"

# Termine di ricerca da usare su ARASAAC quando il nome della tessera non
# coincide con la voce del catalogo (sinonimi, disambiguazioni).
ALIAS_RICERCA: Dict[str, str] = {
    "Bagno (WC)": "gabinetto",
    "Bagno": "vasca da bagno",
    "Guardare la TV": "televisione",
    "Bolle di sapone": "bolle",
    "Io voglio": "volere",
    "Io vedo": "vedere",
    "Io sento": "sentire",
    "Ho": "avere",
    "E'": "essere",
    "Basta": "finito",
    "Ancora": "di nuovo",
    "Pausa": "riposare",
    "Male": "dolore",
    "Coccole": "abbracciare",
    "Papa'": "papà",
    "Macchinina": "automobile",
    "Pupazzo": "peluche",
    "Colori": "pastelli",
    "Costruzioni": "costruzioni lego",
}

_CACHE_MEMORIA: Dict[str, Optional[int]] = {}


def _termine_ricerca(nome_item: str) -> str:
    return ALIAS_RICERCA.get(nome_item, nome_item).strip().lower()


def cerca_id(nome_item: str, timeout: float = 6.0) -> Optional[int]:
    """Cerca su ARASAAC il pittogramma corrispondente al termine italiano.
    Restituisce l'ID del primo risultato, o None se la ricerca non va a buon fine.
    Il primo risultato di ARASAAC è quello con corrispondenza migliore."""
    if nome_item in _CACHE_MEMORIA:
        return _CACHE_MEMORIA[nome_item]

    termine = urllib.parse.quote(_termine_ricerca(nome_item))
    url = "%s/it/search/%s" % (API_BASE, termine)
    trovato: Optional[int] = None
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "TheOrganism-PECS/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            dati = json.loads(resp.read().decode("utf-8"))
        if isinstance(dati, list) and dati:
            trovato = int(dati[0].get("_id"))
    except Exception:
        trovato = None

    _CACHE_MEMORIA[nome_item] = trovato
    return trovato


def url_da_id(pittogramma_id: int, risoluzione: int = 500,
              colore: bool = True) -> str:
    """URL diretto dell'immagine PNG dal CDN ARASAAC."""
    suffisso = "_500" if risoluzione >= 500 else "_300"
    if not colore:
        return "%s/%s/%s%s_nocolor.png" % (CDN_BASE, pittogramma_id,
                                            pittogramma_id, suffisso)
    return "%s/%s/%s%s.png" % (CDN_BASE, pittogramma_id, pittogramma_id, suffisso)


def url_pittogramma(nome_item: str, risoluzione: int = 500,
                    db_cache=None, studio_id: int = None) -> Optional[str]:
    """URL del pittogramma per un item, cercandolo per parola italiana.

    Se passi db_cache (il modulo db_pecs) e studio_id, l'ID risolto viene
    salvato nel database: la ricerca online avviene una volta sola.
    """
    pid = None
    if db_cache is not None and studio_id is not None:
        try:
            pid = db_cache.get_arasaac_id(studio_id, nome_item)
        except Exception:
            pid = None
    if pid is None:
        pid = cerca_id(nome_item)
        if pid is not None and db_cache is not None and studio_id is not None:
            try:
                db_cache.salva_arasaac_id(studio_id, nome_item, pid)
            except Exception:
                pass
    if pid is None:
        return None
    return url_da_id(pid, risoluzione)


# ---------------------------------------------------------------------------
# TESSERE STAMPABILI
# ---------------------------------------------------------------------------

_MISURE = {
    # nome: (lato mm, tessere per riga, descrizione d'uso)
    "grande": (80, 2, "Fase I-II, prime tessere, difficoltà di manipolazione"),
    "media": (60, 3, "Uso standard nel quaderno"),
    "piccola": (40, 4, "Quaderno ampio, striscia-frase, Fase IV+"),
    "mini": (30, 6, "Striscia-frase, attributi, vocabolario molto ampio"),
}


def misure_disponibili() -> List[Tuple[str, str]]:
    return [(k, "%s — %d mm · %s" % (k.capitalize(), v[0], v[2]))
            for k, v in _MISURE.items()]


def foglio_tessere_html(tessere: List[dict], misura: str = "media",
                        mostra_bordo_taglio: bool = True) -> str:
    """Foglio A4 di tessere PECS pronto da stampare.

    tessere: lista di dict con chiavi 'nome' e 'url' (URL immagine o data-URI).
    """
    lato_mm, per_riga, _ = _MISURE.get(misura, _MISURE["media"])
    bordo = "1px dashed #999" if mostra_bordo_taglio else "1px solid transparent"
    celle = []
    for t in tessere:
        nome = (t.get("nome") or "").strip()
        url = t.get("url") or ""
        if url:
            img = ('<img src="%s" alt="%s" '
                   'style="width:100%%;height:%dmm;object-fit:contain;">'
                   % (url, nome.replace('"', "&quot;"), lato_mm - 12))
        else:
            img = ('<div style="width:100%%;height:%dmm;display:flex;'
                   'align-items:center;justify-content:center;color:#bbb;'
                   'font-size:9pt;text-align:center;">pittogramma<br>non trovato'
                   '</div>' % (lato_mm - 12))
        celle.append(
            '<div class="tessera">%s<div class="etichetta">%s</div></div>'
            % (img, nome.upper()))

    return """<!DOCTYPE html>
<html lang="it"><head><meta charset="utf-8">
<title>Tessere PECS</title>
<style>
  @page {{ size: A4; margin: 10mm; }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; font-family: Arial, Helvetica, sans-serif; background:#fff; }}
  .barra {{ padding:6px 0 10px; font-size:10pt; color:#444;
            display:flex; justify-content:space-between; align-items:center; }}
  .barra button {{ background:#14502F; color:#fff; border:0; border-radius:4px;
                   padding:6px 14px; font-size:10pt; cursor:pointer; }}
  .griglia {{ display:grid; grid-template-columns: repeat({per_riga}, {lato}mm);
              gap:4mm; justify-content:start; }}
  .tessera {{ width:{lato}mm; height:{lato}mm; border:{bordo}; border-radius:2mm;
              padding:2mm; display:flex; flex-direction:column;
              align-items:center; justify-content:space-between;
              page-break-inside:avoid; break-inside:avoid; background:#fff; }}
  .etichetta {{ font-weight:bold; font-size:{font}pt; text-align:center;
                line-height:1.1; width:100%; }}
  @media print {{ .barra {{ display:none; }} }}
</style></head><body>
<div class="barra">
  <span>Tessere PECS · {n} tessere · {lato}×{lato} mm · pittogrammi ARASAAC (CC BY-NC-SA)</span>
  <button onclick="window.print()">Stampa</button>
</div>
<div class="griglia">{celle}</div>
</body></html>""".format(
        per_riga=per_riga, lato=lato_mm, bordo=bordo,
        font=max(7, min(14, lato_mm // 6)),
        n=len(tessere), celle="".join(celle))


def striscia_frase_html(altezza_mm: int = 55) -> str:
    """Striscia-frase da stampare e applicare al quaderno (Fase IV+)."""
    return """<!DOCTYPE html>
<html lang="it"><head><meta charset="utf-8"><title>Striscia-frase PECS</title>
<style>
  @page {{ size: A4 landscape; margin: 12mm; }}
  body {{ margin:0; font-family: Arial, Helvetica, sans-serif; }}
  .barra {{ padding:6px 0 12px; font-size:10pt; color:#444;
            display:flex; justify-content:space-between; }}
  .barra button {{ background:#14502F; color:#fff; border:0; border-radius:4px;
                   padding:6px 14px; cursor:pointer; }}
  .striscia {{ height:{h}mm; border:2px solid #333; border-radius:3mm;
               display:flex; align-items:center; padding:3mm;
               margin-bottom:8mm; background:#fff;
               page-break-inside:avoid; break-inside:avoid; }}
  .slot {{ width:{s}mm; height:{s}mm; border:1px dashed #aaa; border-radius:2mm;
           margin-right:3mm; }}
  .slot.avvio {{ border:2px solid #14502F; }}
  .nota {{ font-size:9pt; color:#777; margin-bottom:3mm; }}
  @media print {{ .barra {{ display:none; }} }}
</style></head><body>
<div class="barra">
  <span>Striscia-frase PECS · stampare su cartoncino e applicare velcro</span>
  <button onclick="window.print()">Stampa</button>
</div>
<div class="nota">Il primo riquadro (bordo verde) è per la tessera di avvio
  «IO VOGLIO». Applicare velcro maschio sulla striscia e femmina sul retro
  delle tessere.</div>
<div class="striscia"><div class="slot avvio"></div><div class="slot"></div>
  <div class="slot"></div><div class="slot"></div><div class="slot"></div></div>
<div class="striscia"><div class="slot avvio"></div><div class="slot"></div>
  <div class="slot"></div><div class="slot"></div><div class="slot"></div></div>
<div class="striscia"><div class="slot avvio"></div><div class="slot"></div>
  <div class="slot"></div><div class="slot"></div><div class="slot"></div></div>
</body></html>""".format(h=altezza_mm, s=altezza_mm - 12)
