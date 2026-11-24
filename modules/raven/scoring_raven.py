# -*- coding: utf-8 -*-
"""
scoring_raven.py - Calcoli delle Matrici di Raven (senza database, senza Streamlit).

Tre modi di inserimento:
  totali     solo il numero di risposte corrette per serie
  esiti      item per item, giusto / sbagliato
  risposte   item per item, l'alternativa scelta (serve la chiave caricata dallo studio)

Norme: lista di righe {"da": mesi, "a": mesi, "p5": grezzo, ..., "p95": grezzo},
copiate dal manuale dello studio. Attese: {"totale": [atteso per serie, ...]}.
"""
import re
from datetime import date, datetime

from .catalogo_raven import FORME, PUNTI, GRADI, SCARTO_MAX, AVVERTENZA


# --------------------------------------------------------------------- eta'
def _come_data(d):
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, date):
        return d
    if isinstance(d, str) and d.strip():
        for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
            try:
                return datetime.strptime(d.strip()[:10], fmt).date()
            except ValueError:
                pass
    return None


def eta_mesi(data_nascita, alla_data):
    n, a = _come_data(data_nascita), _come_data(alla_data)
    if not n or not a or a < n:
        return None
    mesi = (a.year - n.year) * 12 + (a.month - n.month)
    if a.day < n.day:
        mesi -= 1
    return mesi


def eta_testo(mesi):
    if mesi is None:
        return "età non disponibile"
    anni, m = divmod(int(mesi), 12)
    t = "%d ann%s" % (anni, "o" if anni == 1 else "i")
    if m:
        t += " e %d mes%s" % (m, "e" if m == 1 else "i")
    return t


# ------------------------------------------------------------------- chiave
def leggi_chiave(forma, per_serie):
    """
    per_serie: {"A": "4 5 1 ...", ...} una cifra per item (spazi e virgole ignorati).
    Ritorna ({"A": [int, ...], ...}, errori).
    """
    f = FORME[forma]
    out, errori = {}, []
    for s in f["serie"]:
        cifre = re.sub(r"[^0-9]", "", str((per_serie or {}).get(s) or ""))
        if len(cifre) != f["item"]:
            errori.append("Serie %s: servono %d cifre, ne ho lette %d." % (s, f["item"], len(cifre)))
            continue
        valori = [int(c) for c in cifre]
        fuori = [i + 1 for i, v in enumerate(valori) if not 1 <= v <= f["alternative"][s]]
        if fuori:
            errori.append("Serie %s: valore fuori da 1-%d agli item %s." % (
                s, f["alternative"][s], ", ".join(map(str, fuori))))
            continue
        out[s] = valori
    return (out if not errori else {}), errori


# ---------------------------------------------------------------- punteggi
def _esito(forma, serie, modo, omessi=0):
    f = FORME[forma]
    return {"forma": forma, "modo": modo, "serie": {s: int(serie[s]) for s in f["serie"]},
            "totale": int(sum(serie[s] for s in f["serie"])),
            "massimo": f["item"] * len(f["serie"]), "omessi": int(omessi)}


def punteggi_da_totali(forma, totali):
    f = FORME[forma]
    serie = {}
    for s in f["serie"]:
        v = totali.get(s)
        v = 0 if v is None else int(v)
        if not 0 <= v <= f["item"]:
            raise ValueError("Serie %s: il punteggio deve stare fra 0 e %d." % (s, f["item"]))
        serie[s] = v
    return _esito(forma, serie, "totali")


def punteggi_da_esiti(forma, esiti):
    """esiti: {"A": [True/False/None x12], ...}"""
    f = FORME[forma]
    serie = {s: sum(1 for v in (esiti.get(s) or [])[:f["item"]] if v is True or v == 1)
             for s in f["serie"]}
    return _esito(forma, serie, "esiti")


def punteggi_da_risposte(forma, risposte, chiave):
    """risposte: {"A": [alternativa scelta o None x12], ...}; chiave: da leggi_chiave."""
    f = FORME[forma]
    if not chiave or any(len(chiave.get(s) or []) != f["item"] for s in f["serie"]):
        raise ValueError("Chiave di correzione non caricata per %s." % forma)
    serie, omessi = {}, 0
    for s in f["serie"]:
        date_ = list(risposte.get(s) or []) + [None] * f["item"]
        n = 0
        for i in range(f["item"]):
            v = date_[i]
            try:
                v = None if v is None or v != v else int(v)      # v != v: NaN
            except (TypeError, ValueError):
                v = None
            if v is None:
                omessi += 1
            elif v == chiave[s][i]:
                n += 1
        serie[s] = n
    return _esito(forma, serie, "risposte", omessi)


# -------------------------------------------------------------------- norme
def controlla_norme(forma, righe):
    """Ripulisce le righe della tabella normativa. Ritorna (righe_valide, errori)."""
    massimo = FORME[forma]["item"] * len(FORME[forma]["serie"])
    buone, errori = [], []
    for n, r in enumerate(righe or [], 1):
        punti = {}
        for p in PUNTI:
            v = r.get("p%d" % p)
            if v is None or v != v or v == "":
                continue
            punti["p%d" % p] = int(v)
        da, a = r.get("da"), r.get("a")
        if da is None and a is None and not punti:
            continue                                         # riga vuota
        if da is None or a is None or da > a:
            errori.append("Riga %d: fascia d'età mancante o rovesciata." % n)
            continue
        if len(punti) < 3:
            errori.append("Riga %d: servono almeno tre punti percentili." % n)
            continue
        valori = [punti[k] for k in ("p%d" % p for p in PUNTI) if k in punti]
        if any(not 0 <= v <= massimo for v in valori) or valori != sorted(valori):
            errori.append("Riga %d: i grezzi devono crescere con il percentile e stare fra 0 e %d."
                          % (n, massimo))
            continue
        buone.append(dict(da=int(da), a=int(a), **punti))
    buone.sort(key=lambda x: x["da"])
    for prima, dopo in zip(buone, buone[1:]):
        if dopo["da"] <= prima["a"]:
            errori.append("Le fasce %s e %s si sovrappongono." % (
                _fascia(prima), _fascia(dopo)))
    return buone, errori


def _fascia(r):
    def am(m):
        return "%d;%d" % divmod(int(m), 12)
    return "%s–%s" % (am(r["da"]), am(r["a"]))


def cerca_norma(norme, mesi):
    if mesi is None:
        return None
    for r in norme or []:
        if r["da"] <= mesi <= r["a"]:
            return r
    return None


def grado_da_punti(grezzo, riga):
    """Grado di Raven confrontando il grezzo con i punti percentili della fascia d'eta'."""
    g = lambda p: riga.get("p%d" % p)
    for p, grado in ((95, "I"), (90, "II+"), (75, "II")):
        if g(p) is not None and grezzo >= g(p):
            return grado
    for p, grado in ((5, "V"), (10, "IV-"), (25, "IV")):
        if g(p) is not None and grezzo <= g(p):
            return grado
    if g(50) is None:
        return None
    # fra 25° e 75°: serve che i due estremi mancanti non lascino il dubbio
    if grezzo > g(50):
        return "III+" if g(75) is not None else None
    if grezzo < g(50):
        return "III-" if g(25) is not None else None
    return "III"


def grado_da_percentile(p):
    p = float(p)
    if p >= 95: return "I"
    if p >= 90: return "II+"
    if p >= 75: return "II"
    if p > 50:  return "III+"
    if p == 50: return "III"
    if p > 25:  return "III-"
    if p > 10:  return "IV"
    if p > 5:   return "IV-"
    return "V"


# -------------------------------------------------------------- composizione
def composizione(forma, punteggi, attese):
    """Confronto fra i punteggi di serie osservati e quelli attesi per quel totale."""
    att = (attese or {}).get(str(punteggi["totale"]))
    serie = FORME[forma]["serie"]
    if not att or len(att) != len(serie):
        return None
    scarti = {s: punteggi["serie"][s] - int(a) for s, a in zip(serie, att)}
    fuori = [s for s in serie if abs(scarti[s]) > SCARTO_MAX]
    return {"attesi": dict(zip(serie, [int(a) for a in att])), "scarti": scarti,
            "serie_fuori": fuori, "atipica": bool(fuori)}


def controlla_attese(forma, righe):
    """righe: [{"totale": n, "A": x, ...}] -> ({"n": [x, ...]}, errori)"""
    f = FORME[forma]
    out, errori = {}, []
    for n, r in enumerate(righe or [], 1):
        vals = [r.get(s) for s in f["serie"]]
        tot = r.get("totale")
        if tot is None and all(v is None for v in vals):
            continue
        if tot is None or any(v is None for v in vals):
            errori.append("Riga %d: incompleta." % n)
            continue
        vals = [int(v) for v in vals]
        if sum(vals) != int(tot) or any(not 0 <= v <= f["item"] for v in vals):
            errori.append("Riga %d: la somma delle serie non dà il totale %s." % (n, int(tot)))
            continue
        out[str(int(tot))] = vals
    return out, errori


# ------------------------------------------------------------------- sintesi
def valuta(forma, punteggi, mesi, norme=None, attese=None, percentile_manuale=None, fonte=None):
    """Mette insieme punteggio, collocazione normativa e composizione."""
    ris = dict(punteggi)
    ris.update({"eta_mesi": mesi, "grado": None, "fascia": None, "lettura": None,
                "origine_norma": None, "fascia_eta": None, "fonte": fonte or None,
                "percentile_manuale": None, "motivo_senza_norma": None})
    if percentile_manuale not in (None, "", 0):
        ris["percentile_manuale"] = float(percentile_manuale)
        ris["grado"] = grado_da_percentile(percentile_manuale)
        ris["origine_norma"] = "manuale"
    else:
        riga = cerca_norma(norme, mesi)
        if riga:
            ris["grado"] = grado_da_punti(ris["totale"], riga)
            ris["origine_norma"] = "tabella"
            ris["fascia_eta"] = _fascia(riga)
            if ris["grado"] is None:
                ris["motivo_senza_norma"] = "la riga della tabella per questa età è incompleta"
        elif not norme:
            ris["motivo_senza_norma"] = "la tabella normativa non è ancora caricata"
        elif mesi is None:
            ris["motivo_senza_norma"] = "manca la data di nascita"
        else:
            ris["motivo_senza_norma"] = "l'età non rientra nelle fasce della tabella caricata"
    if ris["grado"]:
        ris["fascia"], ris["lettura"] = GRADI[ris["grado"]]
        if ris["percentile_manuale"] is not None:
            p = ris["percentile_manuale"]
            ris["fascia"] = "al %s° percentile" % (int(p) if p == int(p) else p)
    ris["composizione"] = composizione(forma, punteggi, attese)
    return ris


def riga_sintesi(ris):
    t = "%s: %d/%d" % (FORME[ris["forma"]]["breve"], ris["totale"], ris["massimo"])
    if ris.get("grado"):
        t += " · %s (grado %s)" % (ris["fascia"], ris["grado"])
    return t


# ----------------------------------------------------------------- relazione
_LETTURE = {
    "I": "La prestazione è molto superiore a quella attesa per l'età: il ragionamento non verbale "
         "è un punto di forza marcato.",
    "II+": "La prestazione è superiore alla media dei coetanei: il ragionamento non verbale è un "
           "punto di forza.",
    "II": "La prestazione è superiore alla media dei coetanei: il ragionamento non verbale è un "
          "punto di forza.",
    "III+": "La prestazione è nella media, nella sua parte alta: le capacità di ragionamento non "
            "verbale sono adeguate all'età.",
    "III": "La prestazione è nella media: le capacità di ragionamento non verbale sono adeguate "
           "all'età.",
    "III-": "La prestazione è nella media, nella sua parte bassa: le capacità di ragionamento non "
            "verbale rientrano in quanto atteso per l'età.",
    "IV": "La prestazione è inferiore alla media dei coetanei e indica una fragilità nel "
          "ragionamento non verbale, da approfondire con le altre prove della valutazione.",
    "IV-": "La prestazione è nettamente inferiore alla media dei coetanei e indica una difficoltà "
           "nel ragionamento non verbale, da approfondire con una valutazione cognitiva più ampia.",
    "V": "La prestazione è molto inferiore a quella attesa per l'età. Prima di trarne conclusioni "
         "va verificato che non abbiano pesato la comprensione della consegna, l'attenzione, la "
         "funzione visiva o la collaborazione; è indicato un approfondimento con una scala "
         "cognitiva multicomponenziale e con la valutazione del funzionamento adattivo.",
}


def relazione(nome, forma, data_prova, ris, osservazioni=None):
    """Testo della relazione, a paragrafi separati da una riga vuota. Il clinico lo puo' correggere."""
    f = FORME[forma]
    o = osservazioni or {}
    d = _come_data(data_prova)
    par = [f["descrizione"]]

    p2 = "La prova è stata somministrata%s a %s%s." % (
        " il " + d.strftime("%d/%m/%Y") if d else "", nome or "il/la paziente",
        ", di %s" % eta_testo(ris.get("eta_mesi")) if ris.get("eta_mesi") is not None else "")
    oss = []
    if o.get("collaborazione") and o["collaborazione"] != "—":
        oss.append("la collaborazione è stata %s" % o["collaborazione"])
    if o.get("attenzione") and o["attenzione"] != "—":
        oss.append("l'attenzione %s" % o["attenzione"])
    if o.get("stile") and o["stile"] != "—":
        oss.append("lo stile di risposta %s" % o["stile"].split(" (")[0])
    if oss:
        p2 += " Durante la prova " + ", ".join(oss) + "."
    if o.get("minuti"):
        p2 += " Tempo impiegato: circa %d minuti." % int(o["minuti"])
    par.append(p2)

    p3 = "Il punteggio grezzo è di %d risposte corrette su %d (%s)." % (
        ris["totale"], ris["massimo"],
        "; ".join("serie %s: %d" % (s, ris["serie"][s]) for s in f["serie"]))
    if ris.get("omessi"):
        p3 += " Item senza risposta: %d." % ris["omessi"]
    if ris.get("grado"):
        if ris.get("origine_norma") == "manuale":
            p3 += " Secondo le norme del manuale il punteggio si colloca %s (grado %s): %s." % (
                ris["fascia"], ris["grado"], ris["lettura"])
        else:
            p3 += (" Rispetto al campione normativo di pari età (fascia %s%s) il punteggio si "
                   "colloca %s (grado %s): %s." % (
                       ris.get("fascia_eta") or "—",
                       ", fonte: %s" % ris["fonte"] if ris.get("fonte") else "",
                       ris["fascia"], ris["grado"], ris["lettura"]))
    else:
        p3 += (" Il punteggio non è stato confrontato con le norme%s: il dato va inteso come "
               "descrittivo." % (" (%s)" % ris["motivo_senza_norma"] if ris.get("motivo_senza_norma") else ""))
    if o.get("altro_punteggio"):
        p3 += " Altro punteggio ricavato dal manuale: %s." % str(o["altro_punteggio"]).strip().rstrip(".")
    par.append(p3)

    if ris.get("grado"):
        par.append(_LETTURE[ris["grado"]])

    c = ris.get("composizione")
    if c:
        if c["atipica"]:
            par.append(
                "La distribuzione dei punteggi nelle serie si discosta da quella attesa per questo "
                "totale (%s): il risultato va letto con cautela, perché un andamento irregolare può "
                "dipendere da cali di attenzione, risposte date a caso o comprensione incompleta "
                "della consegna." % "; ".join(
                    "serie %s: %d contro %d attesi" % (s, ris["serie"][s], c["attesi"][s])
                    for s in c["serie_fuori"]))
        else:
            par.append("La distribuzione dei punteggi nelle serie è coerente con quella attesa per "
                       "questo totale: il risultato può essere considerato attendibile.")

    if o.get("note"):
        par.append(str(o["note"]).strip())
    par.append(AVVERTENZA)
    return "\n\n".join(par)
