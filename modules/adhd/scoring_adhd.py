# -*- coding: utf-8 -*-
"""
scoring_adhd.py - Calcoli del modulo ADHD. Funzioni pure: niente database,
niente Streamlit, cosi' si possono provare da sole (tests/test_adhd.py).

Le risposte arrivano come dict {numero_item (int o str): valore o None}.
"""
import math
from statistics import mean, median, pstdev

from .catalogo_adhd import (SCALE, SCARED_SOTTOSCALE, SCARED_SOGLIA_TOTALE,
                            METRICHE, TEST_ESTERNI)


def _v(risposte, n):
    x = risposte.get(n, risposte.get(str(n)))
    try:
        return None if x is None or x == "" else int(x)
    except (TypeError, ValueError):
        return None


def _mancanti(risposte, items):
    return [n for n in items if _v(risposte, n) is None]


# ------------------------------------------------------------------ Vanderbilt
def punteggio_vanderbilt(codice, risposte):
    """codice: VAND_GEN | VAND_INS. Ritorna dict con conteggi, medie ed esiti."""
    regole = SCALE[codice]["regole"]
    rend_items = regole["rendimento"]
    rend_problema = [n for n in rend_items if (_v(risposte, n) or 0) >= 4]
    compromissione = bool(rend_problema)

    def blocco(items, soglia):
        val = [_v(risposte, n) for n in items]
        pres = [x for x in val if x is not None]
        positivi = sum(1 for x in pres if x >= 2)
        return {"positivi": positivi, "soglia": soglia, "su": len(items),
                "somma": sum(pres),
                "media": round(mean(pres), 2) if pres else None,
                "mancanti": len(val) - len(pres),
                "sintomi_sopra_soglia": positivi >= soglia,
                "positivo": positivi >= soglia and compromissione}

    out = {"strumento": codice, "blocchi": {}, "compromissione": compromissione,
           "rendimento_problema": rend_problema,
           "rendimento_media": None, "mancanti": len(_mancanti(risposte, range(1, SCALE[codice]["n_item"] + 1)))}
    for nome, reg in regole.items():
        if nome == "rendimento":
            continue
        out["blocchi"][nome] = blocco(*reg)
    r = [_v(risposte, n) for n in rend_items if _v(risposte, n) is not None]
    out["rendimento_media"] = round(mean(r), 2) if r else None

    dis, ipe = out["blocchi"]["disattenzione"], out["blocchi"]["iperattivita"]
    out["totale_sintomi_adhd"] = dis["somma"] + ipe["somma"]
    if dis["positivo"] and ipe["positivo"]:
        out["esito_adhd"] = "combinato"
    elif dis["positivo"]:
        out["esito_adhd"] = "disattento"
    elif ipe["positivo"]:
        out["esito_adhd"] = "iperattivo-impulsivo"
    elif dis["sintomi_sopra_soglia"] or ipe["sintomi_sopra_soglia"]:
        out["esito_adhd"] = "sintomi senza compromissione"
    else:
        out["esito_adhd"] = "negativo"
    return out


ESITO_ADHD_TESTO = {
    "combinato": "Screening positivo: disattenzione e iperattività/impulsività, con compromissione",
    "disattento": "Screening positivo: prevalente disattenzione, con compromissione",
    "iperattivo-impulsivo": "Screening positivo: prevalente iperattività/impulsività, con compromissione",
    "sintomi senza compromissione": "Sintomi sopra soglia ma nessuna area di rendimento segnata come problema",
    "negativo": "Screening negativo",
}
BLOCCO_TESTO = {"disattenzione": "Disattenzione", "iperattivita": "Iperattività / impulsività",
                "oppositivita": "Oppositività", "condotta": "Condotta",
                "oppositivita_condotta": "Oppositività / condotta", "ansia_umore": "Ansia / umore"}


# ---------------------------------------------------------------------- SCARED
def punteggio_scared(risposte):
    tot_val = [_v(risposte, n) for n in range(1, 42)]
    pres = [x for x in tot_val if x is not None]
    out = {"totale": sum(pres), "soglia_totale": SCARED_SOGLIA_TOTALE,
           "totale_sopra_soglia": sum(pres) >= SCARED_SOGLIA_TOTALE,
           "mancanti": 41 - len(pres), "sottoscale": {}}
    for nome, (items, soglia) in SCARED_SOTTOSCALE.items():
        s = sum(_v(risposte, n) or 0 for n in items)
        out["sottoscale"][nome] = {"punteggio": s, "soglia": soglia, "massimo": 2 * len(items),
                                   "sopra_soglia": s >= soglia}
    return out


def punteggio_scala(codice, risposte):
    if codice.startswith("VAND"):
        return punteggio_vanderbilt(codice, risposte)
    if codice.startswith("SCARED"):
        return punteggio_scared(risposte)
    raise ValueError("Scala non in catalogo: %s" % codice)


# ------------------------------------------------------------ checklist criteri
def eta_anni(data_nascita, alla_data):
    if not data_nascita or not alla_data:
        return None
    try:
        a = alla_data.year - data_nascita.year
        if (alla_data.month, alla_data.day) < (data_nascita.month, data_nascita.day):
            a -= 1
        return a
    except AttributeError:
        return None


def esito_checklist(dati, eta=None):
    """
    dati: {"disattenzione": [bool x9], "iperattivita": [bool x9], "esordio_prima_12": bool,
           "contesti": [str], "compromissione": bool, "altre_spiegazioni_escluse": bool}
    Soglia: 6 sintomi per dominio; 5 dai 17 anni in su.
    """
    soglia = 5 if (eta is not None and eta >= 17) else 6
    n_dis = sum(1 for x in dati.get("disattenzione", []) if x)
    n_ipe = sum(1 for x in dati.get("iperattivita", []) if x)
    dis, ipe = n_dis >= soglia, n_ipe >= soglia
    n_cont = len(dati.get("contesti") or [])
    condizioni = {
        "Sintomi sopra soglia in almeno un dominio": dis or ipe,
        "Esordio di alcuni sintomi prima dei 12 anni": bool(dati.get("esordio_prima_12")),
        "Sintomi presenti in due o più contesti": n_cont >= 2,
        "Compromissione del funzionamento": bool(dati.get("compromissione")),
        "Altre spiegazioni escluse": bool(dati.get("altre_spiegazioni_escluse")),
    }
    tutti = all(condizioni.values())
    if dis and ipe:
        quadro = "combinata"
    elif dis:
        quadro = "con disattenzione predominante"
    elif ipe:
        quadro = "con iperattività/impulsività predominante"
    else:
        quadro = None
    return {"soglia": soglia, "n_disattenzione": n_dis, "n_iperattivita": n_ipe,
            "condizioni": condizioni, "criteri_soddisfatti": tutti,
            "manifestazione": quadro if tutti else None,
            "mancano": [k for k, ok in condizioni.items() if not ok]}


# ------------------------------------------------------------- prove a schermo
def _z_inv(p):
    """Inversa della normale standard (Acklam), per d'."""
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    if p < 0.02425:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p > 1 - 0.02425:
        return -_z_inv(1 - p)
    q = p - 0.5
    r = q * q
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / \
           (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)


def _tempi(rt):
    if not rt:
        return {"rt_media": None, "rt_mediana": None, "rt_ds": None, "rt_cv": None}
    m = mean(rt)
    ds = pstdev(rt) if len(rt) > 1 else 0.0
    return {"rt_media": round(m), "rt_mediana": round(median(rt)), "rt_ds": round(ds),
            "rt_cv": round(ds / m, 3) if m else None}


def _risposta_bersaglio(trials):
    """Attenzione sostenuta e go/no-go: trial = {bersaglio: bool, risposta: bool, rt: ms|None}."""
    bers = [t for t in trials if t.get("bersaglio")]
    altri = [t for t in trials if not t.get("bersaglio")]
    colpi = [t for t in bers if t.get("risposta")]
    false_r = [t for t in altri if t.get("risposta")]
    rt = [float(t["rt"]) for t in colpi if t.get("rt") is not None]
    nb, na = len(bers), len(altri)
    # d' con correzione log-lineare (evita infinito con 0 o 100%)
    ph = (len(colpi) + 0.5) / (nb + 1) if nb else None
    pf = (len(false_r) + 0.5) / (na + 1) if na else None
    out = {"n_prove": len(trials), "n_bersagli": nb, "colpi": len(colpi),
           "omissioni": nb - len(colpi),
           "omissioni_perc": round(100.0 * (nb - len(colpi)) / nb, 1) if nb else None,
           "n_non_bersagli": na, "false_risposte": len(false_r),
           "false_risposte_perc": round(100.0 * len(false_r) / na, 1) if na else None,
           "anticipazioni": sum(1 for x in rt if x < 150),
           "d_primo": round(_z_inv(ph) - _z_inv(pf), 2) if ph and pf else None}
    out.update(_tempi(rt))
    # tenuta nel tempo: tre terzi
    terzi = []
    k = len(trials) // 3
    if k >= 5:
        for i in range(3):
            parte = trials[i * k:(i + 1) * k] if i < 2 else trials[2 * k:]
            b = [t for t in parte if t.get("bersaglio")]
            c = [t for t in b if t.get("risposta")]
            r = [float(t["rt"]) for t in c if t.get("rt") is not None]
            terzi.append({"omissioni": len(b) - len(c),
                          "false_risposte": sum(1 for t in parte if not t.get("bersaglio") and t.get("risposta")),
                          "rt_media": round(mean(r)) if r else None})
    out["terzi"] = terzi
    return out


def _stroop(trials):
    """trial = {congruente: bool, corretta: bool, rt: ms|None (None = tempo scaduto)}."""
    out = {"n_prove": len(trials)}
    medie = {}
    for nome, flag in (("coerenti", True), ("incoerenti", False)):
        p = [t for t in trials if bool(t.get("congruente")) == flag]
        ok = [t for t in p if t.get("corretta")]
        rt = [float(t["rt"]) for t in ok if t.get("rt") is not None]
        medie[nome] = mean(rt) if rt else None
        out[nome] = {"n": len(p), "corrette": len(ok), "errori": len(p) - len(ok),
                     "accuratezza_perc": round(100.0 * len(ok) / len(p), 1) if p else None,
                     "rt_media": round(medie[nome]) if rt else None}
    if medie["coerenti"] is not None and medie["incoerenti"] is not None:
        out["interferenza_ms"] = round(medie["incoerenti"] - medie["coerenti"])
    else:
        out["interferenza_ms"] = None
    out["interferenza_errori"] = out["incoerenti"]["errori"] - out["coerenti"]["errori"]
    return out


def _span(trials):
    """trial = {verso: 'avanti'|'indietro', lunghezza: int, corretta: bool}."""
    out = {"n_prove": len(trials)}
    for verso in ("avanti", "indietro"):
        p = [t for t in trials if t.get("verso") == verso]
        ok = [int(t["lunghezza"]) for t in p if t.get("corretta")]
        out[verso] = {"span": max(ok) if ok else 0, "sequenze_corrette": len(ok), "sequenze": len(p)}
    return out


def calcola_prova(prova, trials):
    trials = trials or []
    if prova in ("attenzione", "gonogo"):
        return _risposta_bersaglio(trials)
    if prova == "stroop":
        return _stroop(trials)
    if prova == "span":
        return _span(trials)
    raise ValueError("Prova non in catalogo: %s" % prova)


def riga_prova(prova, m):
    """Una riga leggibile del risultato di una prova."""
    if prova in ("attenzione", "gonogo"):
        etic = "false risposte" if prova == "attenzione" else "risposte non trattenute"
        return ("omissioni %s/%s (%s%%) · %s %s/%s (%s%%) · tempo medio %s ms (ds %s)" % (
            m.get("omissioni"), m.get("n_bersagli"), m.get("omissioni_perc"), etic,
            m.get("false_risposte"), m.get("n_non_bersagli"), m.get("false_risposte_perc"),
            m.get("rt_media"), m.get("rt_ds")))
    if prova == "stroop":
        return ("coerenti %s ms, %s errori · incoerenti %s ms, %s errori · interferenza %s ms" % (
            m["coerenti"]["rt_media"], m["coerenti"]["errori"], m["incoerenti"]["rt_media"],
            m["incoerenti"]["errori"], m.get("interferenza_ms")))
    if prova == "span":
        return "span avanti %s · span indietro %s" % (m["avanti"]["span"], m["indietro"]["span"])
    return ""


# ----------------------------------------------------------- test esterni
def _phi(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def converti_punteggio(metrica, valore, verso="basso"):
    """
    Ritorna {"z", "percentile", "fascia"}. Il percentile e' quello TEORICO della curva
    normale (non quello del manuale): se il manuale ne riporta uno, vale quello.
    """
    if valore is None or metrica not in METRICHE or metrica == "GREZZO":
        return {"z": None, "percentile": None, "fascia": None}
    valore = float(valore)
    if metrica == "PERC":
        p = min(max(valore, 0.1), 99.9)
        z = _z_inv(p / 100.0)
    else:
        _, m, ds = METRICHE[metrica]
        z = (valore - m) / ds
        p = 100.0 * _phi(z)
    # zs: z "nel verso della difficolta'" (positivo = difficolta')
    zs = z if verso == "alto" else -z
    if verso == "alto":
        fascia = ("molto elevato" if zs >= 2 else "elevato" if zs >= 1.5
                  else "ai limiti" if zs >= 1 else "nella norma")
    else:
        fascia = ("molto basso" if zs >= 2 else "basso" if zs >= 1.5
                  else "ai limiti inferiori" if zs >= 1
                  else "punto di forza" if zs <= -1.5 else "nella norma")
    return {"z": round(z, 2), "percentile": round(p, 1), "fascia": fascia}


def verso_test(strumento):
    return (TEST_ESTERNI.get(strumento) or {}).get("verso", "basso")


# ------------------------------------------------------------------ sintesi
def sintesi(registrazioni):
    """
    registrazioni: lista di dict (da db_adhd.lista) gia' con 'punteggi' decodificato,
    ordinate dalla piu' recente. Usa, per ogni strumento, l'ultima registrazione.
    Ritorna {"righe": [(area, fonte, esito, segnale)], "testo": str, "informatori": {...}}.
    segnale: True = elemento a favore di un approfondimento, False = no, None = neutro.
    """
    ultimi = {}
    for r in registrazioni:
        chiave = (r["categoria"], r["strumento"]) if r["categoria"] != "esterno" \
            else (r["categoria"], r["strumento"], (r.get("punteggi") or {}).get("scala"))
        ultimi.setdefault(chiave, r)

    righe, informatori = [], {}
    for (cat, *_), r in ultimi.items():
        p = r.get("punteggi") or {}
        s = r["strumento"]
        if cat == "scala" and s.startswith("VAND"):
            esito = p.get("esito_adhd")
            informatori[SCALE[s]["informatore"]] = esito
            pos = esito in ("combinato", "disattento", "iperattivo-impulsivo")
            b = p.get("blocchi", {})
            righe.append(("Sintomi ADHD", SCALE[s]["nome"],
                          "%s (disattenzione %s/9, iperattività %s/9)" % (
                              ESITO_ADHD_TESTO.get(esito, esito),
                              b.get("disattenzione", {}).get("positivi"),
                              b.get("iperattivita", {}).get("positivi")), pos))
            for nome, d in b.items():
                if nome in ("disattenzione", "iperattivita"):
                    continue
                if d.get("positivo"):
                    righe.append(("Comorbilità", SCALE[s]["nome"],
                                  "%s: screening positivo (%s/%s)" % (BLOCCO_TESTO[nome], d["positivi"], d["su"]),
                                  None))
        elif cat == "scala" and s.startswith("SCARED"):
            sopra = [k for k, d in (p.get("sottoscale") or {}).items() if d.get("sopra_soglia")]
            righe.append(("Ansia", SCALE[s]["nome"],
                          "totale %s (soglia %s)%s" % (p.get("totale"), p.get("soglia_totale"),
                                                       "; sopra soglia: " + ", ".join(sopra) if sopra else ""),
                          None))
        elif cat == "checklist":
            righe.append(("Criteri (clinico)", "Scheda criteri",
                          ("criteri soddisfatti — manifestazione %s" % p.get("manifestazione"))
                          if p.get("criteri_soddisfatti")
                          else "criteri non tutti soddisfatti (disattenzione %s, iperattività %s; manca: %s)" % (
                              p.get("n_disattenzione"), p.get("n_iperattivita"),
                              "; ".join(p.get("mancano") or []) or "—"),
                          bool(p.get("criteri_soddisfatti"))))
        elif cat == "prova":
            righe.append(("Prove a schermo", r.get("strumento_nome") or s, riga_prova(s, p), None))
        elif cat == "esterno":
            f = p.get("fascia")
            segn = f in ("elevato", "molto elevato", "basso", "molto basso") if f else None
            righe.append(("Test esterni", "%s — %s" % (s, p.get("scala") or ""),
                          "%s %s%s" % (METRICHE.get(p.get("metrica"), ("",))[0], p.get("valore"),
                                       " → %s" % f if f else ""), segn if segn else None))

    ordine = {"Criteri (clinico)": 0, "Sintomi ADHD": 1, "Comorbilità": 2, "Ansia": 3,
              "Prove a schermo": 4, "Test esterni": 5}
    righe.sort(key=lambda x: ordine.get(x[0], 9))

    frasi = []
    if informatori:
        pos = [k for k, e in informatori.items() if e in ("combinato", "disattento", "iperattivo-impulsivo")]
        if len(informatori) >= 2 and len(pos) == len(informatori):
            frasi.append("Le scale di %s concordano su uno screening positivo per i sintomi ADHD."
                         % " e ".join(k.lower() for k in informatori))
        elif pos and len(informatori) >= 2:
            frasi.append("Le scale non concordano: screening positivo per %s, non per gli altri informatori. "
                         "La discordanza tra contesti va approfondita."
                         % ", ".join(k.lower() for k in pos))
        elif pos:
            frasi.append("Screening positivo per %s; manca un secondo informatore." % pos[0].lower())
        else:
            frasi.append("Le scale compilate non raggiungono la soglia di screening per i sintomi ADHD.")
        if len(informatori) < 2:
            frasi.append("Serve almeno un secondo informatore (genitore e insegnante) per valutare i contesti.")
    else:
        frasi.append("Nessuna scala per genitori o insegnanti ancora registrata.")
    chk = ultimi.get(("checklist", "CRITERI"))
    if chk:
        p = chk.get("punteggi") or {}
        frasi.append("Secondo la scheda criteri compilata dal clinico, i criteri %s."
                     % ("risultano soddisfatti (manifestazione %s)" % p.get("manifestazione")
                        if p.get("criteri_soddisfatti") else "non risultano tutti soddisfatti"))
    else:
        frasi.append("La scheda criteri del clinico non è ancora compilata.")
    if any(c[0] == "prova" for c in ultimi):
        frasi.append("Le prove a schermo non hanno norme di riferimento: i valori servono per il "
                     "confronto del paziente con se stesso nel tempo.")
    return {"righe": righe, "testo": " ".join(frasi), "informatori": informatori}
