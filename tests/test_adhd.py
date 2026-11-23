# -*- coding: utf-8 -*-
"""Prove dei calcoli del modulo ADHD (senza database). Avvio: pytest tests/test_adhd.py"""
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.adhd import scoring_adhd as sc
from modules.adhd.catalogo_adhd import SCALE, SCARED_SOTTOSCALE


def _risp(n, base=0, **forzati):
    r = {i: base for i in range(1, n + 1)}
    r.update({int(k): v for k, v in forzati.items()})
    return r


def test_catalogo_coerente():
    for cod, s in SCALE.items():
        visti = [i for _, items, _ in s["sezioni"] for i in items]
        assert sorted(visti) == list(range(1, s["n_item"] + 1)), cod
        if s["etichette"]:
            assert len(s["etichette"]) == s["n_item"], cod
    tutti = sorted(i for items, _ in SCARED_SOTTOSCALE.values() for i in items)
    assert tutti == list(range(1, 42))          # ogni item SCARED in una sola sottoscala


def test_vanderbilt_genitori_negativo():
    r = _risp(55, 0)
    for i in range(48, 56):
        r[i] = 3
    p = sc.punteggio_vanderbilt("VAND_GEN", r)
    assert p["esito_adhd"] == "negativo" and not p["compromissione"]


def test_vanderbilt_genitori_disattento():
    r = _risp(55, 0)
    for i in range(1, 7):
        r[i] = 2                       # 6 item di disattenzione "spesso"
    for i in range(48, 56):
        r[i] = 3
    r[49] = 4                          # lettura: qualche problema
    p = sc.punteggio_vanderbilt("VAND_GEN", r)
    assert p["blocchi"]["disattenzione"]["positivi"] == 6
    assert p["esito_adhd"] == "disattento"
    assert p["totale_sintomi_adhd"] == 12


def test_vanderbilt_sintomi_senza_compromissione():
    r = _risp(55, 0)
    for i in range(1, 19):
        r[i] = 3
    for i in range(48, 56):
        r[i] = 3
    p = sc.punteggio_vanderbilt("VAND_GEN", r)
    assert p["esito_adhd"] == "sintomi senza compromissione"


def test_vanderbilt_cinque_non_bastano():
    r = _risp(55, 0)
    for i in range(1, 6):
        r[i] = 3
    r[48] = 5
    assert sc.punteggio_vanderbilt("VAND_GEN", r)["esito_adhd"] == "negativo"


def test_vanderbilt_genitori_comorbilita():
    r = _risp(55, 0)
    for i in (19, 20, 21, 22):          # oppositivita': 4 su 8
        r[i] = 2
    for i in (27, 28):                  # condotta: 2 su 14, non basta
        r[i] = 3
    for i in (41, 42, 43):              # ansia/umore: 3 su 7
        r[i] = 2
    r[54] = 5
    p = sc.punteggio_vanderbilt("VAND_GEN", r)
    assert p["blocchi"]["oppositivita"]["positivo"]
    assert not p["blocchi"]["condotta"]["positivo"]
    assert p["blocchi"]["ansia_umore"]["positivo"]


def test_vanderbilt_insegnanti_combinato_e_stringhe():
    r = {str(i): 0 for i in range(1, 44)}     # dal database le chiavi tornano come testo
    for i in range(1, 19):
        r[str(i)] = 2
    for i in (19, 20, 23):
        r[str(i)] = 3
    for i in range(36, 44):
        r[str(i)] = 3
    r["42"] = 4
    p = sc.punteggio_vanderbilt("VAND_INS", r)
    assert p["esito_adhd"] == "combinato"
    assert p["blocchi"]["oppositivita_condotta"]["positivo"]
    assert not p["blocchi"]["ansia_umore"]["positivo"]


def test_vanderbilt_risposte_mancanti():
    r = _risp(55, 0)
    r[3] = None
    r[50] = None
    p = sc.punteggio_vanderbilt("VAND_GEN", r)
    assert p["mancanti"] == 2 and p["blocchi"]["disattenzione"]["mancanti"] == 1


def test_scared():
    r = _risp(41, 0)
    assert not sc.punteggio_scared(r)["totale_sopra_soglia"]
    for i in SCARED_SOTTOSCALE["Ansia generalizzata"][0]:
        r[i] = 2                        # 9 item x 2 = 18
    for i in (4, 8, 13):
        r[i] = 2                        # separazione = 6
    r[1] = 1                            # totale 25
    p = sc.punteggio_scared(r)
    assert p["totale"] == 25 and p["totale_sopra_soglia"]
    assert p["sottoscale"]["Ansia generalizzata"]["sopra_soglia"]
    assert p["sottoscale"]["Ansia da separazione"]["sopra_soglia"]
    assert not p["sottoscale"]["Ansia sociale"]["sopra_soglia"]


def test_checklist():
    d = {"disattenzione": [True] * 6 + [False] * 3, "iperattivita": [True] * 5 + [False] * 4,
         "esordio_prima_12": True, "contesti": ["Casa", "Scuola / lavoro"], "compromissione": True,
         "altre_spiegazioni_escluse": True}
    p = sc.esito_checklist(d, eta=10)
    assert p["criteri_soddisfatti"] and p["manifestazione"] == "con disattenzione predominante"
    p = sc.esito_checklist(d, eta=17)           # dai 17 anni bastano 5
    assert p["manifestazione"] == "combinata"
    d["contesti"] = ["Casa"]
    p = sc.esito_checklist(d, eta=10)
    assert not p["criteri_soddisfatti"] and p["mancano"] == ["Sintomi presenti in due o più contesti"]


def test_eta():
    assert sc.eta_anni(date(2016, 7, 7), date(2026, 7, 6)) == 9
    assert sc.eta_anni(date(2016, 7, 7), date(2026, 7, 7)) == 10
    assert sc.eta_anni(None, date(2026, 1, 1)) is None


def test_prova_attenzione():
    t = []
    for i in range(30):
        bers = i % 5 == 0                                   # 6 bersagli, 24 non bersagli
        t.append({"bersaglio": bers, "risposta": bers and i != 25, "rt": 400 + i if bers and i != 25 else None})
    t[1]["risposta"], t[1]["rt"] = True, 300                # una falsa risposta
    m = sc.calcola_prova("attenzione", t)
    assert (m["n_bersagli"], m["omissioni"], m["false_risposte"]) == (6, 1, 1)
    assert m["omissioni_perc"] == 16.7 and m["false_risposte_perc"] == 4.2
    assert m["rt_media"] == 410 and len(m["terzi"]) == 3
    assert m["terzi"][2]["omissioni"] == 1 and m["d_primo"] > 1.5
    assert sc.calcola_prova("gonogo", [])["n_prove"] == 0   # prova vuota: nessun errore


def test_prova_stroop_e_span():
    t = [{"congruente": True, "corretta": True, "rt": 600}, {"congruente": True, "corretta": True, "rt": 700},
         {"congruente": False, "corretta": True, "rt": 900}, {"congruente": False, "corretta": False, "rt": 500},
         {"congruente": False, "corretta": False, "rt": None}]
    m = sc.calcola_prova("stroop", t)
    assert m["interferenza_ms"] == 250 and m["incoerenti"]["errori"] == 2 and m["interferenza_errori"] == 2
    s = [{"verso": "avanti", "lunghezza": 2, "corretta": True}, {"verso": "avanti", "lunghezza": 3, "corretta": True},
         {"verso": "avanti", "lunghezza": 4, "corretta": False}, {"verso": "indietro", "lunghezza": 2, "corretta": False}]
    m = sc.calcola_prova("span", s)
    assert m["avanti"]["span"] == 3 and m["indietro"]["span"] == 0
    assert "span avanti 3" in sc.riga_prova("span", m)


def test_conversioni():
    c = sc.converti_punteggio("T", 79, "alto")              # Conners: T 79
    assert c["z"] == 2.9 and c["fascia"] == "molto elevato" and c["percentile"] > 99
    assert sc.converti_punteggio("T", 60, "alto")["fascia"] == "ai limiti"
    assert sc.converti_punteggio("T", 57, "alto")["fascia"] == "nella norma"
    c = sc.converti_punteggio("QI", 76, "basso")            # indice 76 -> z -1.6, 5° percentile
    assert c["z"] == -1.6 and c["fascia"] == "basso" and 5 <= c["percentile"] <= 6
    assert sc.converti_punteggio("QI", 135, "basso")["fascia"] == "punto di forza"
    assert sc.converti_punteggio("POND", 5, "basso")["z"] == -1.67
    assert sc.converti_punteggio("Z", -3.34, "basso")["fascia"] == "molto basso"
    c = sc.converti_punteggio("PERC", 5, "basso")
    assert abs(c["z"] + 1.64) < 0.02 and c["fascia"] == "basso"
    assert sc.converti_punteggio("GREZZO", 13)["z"] is None


def test_sintesi():
    gen = sc.punteggio_vanderbilt("VAND_GEN", {**_risp(55, 0), **{i: 3 for i in range(1, 19)}, 48: 5})
    ins = sc.punteggio_vanderbilt("VAND_INS", _risp(43, 0))
    regs = [{"categoria": "scala", "strumento": "VAND_GEN", "punteggi": gen},
            {"categoria": "scala", "strumento": "VAND_INS", "punteggi": ins}]
    s = sc.sintesi(regs)
    assert "non concordano" in s["testo"] and "scheda criteri del clinico non è ancora" in s["testo"]
    assert s["informatori"] == {"Genitore": "combinato", "Insegnante": "negativo"}
    assert sc.sintesi([])["righe"] == []
