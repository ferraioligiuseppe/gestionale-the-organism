# -*- coding: utf-8 -*-
"""Prove dei calcoli delle Matrici di Raven (senza database). Avvio: pytest tests/test_raven.py

ATTENZIONE: norme, composizione attesa e chiave usate qui sono NUMERI INVENTATI,
servono solo a provare i calcoli. Non sono quelli del manuale.
"""
import os
import sys
from datetime import date

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.raven import scoring_raven as sc
from modules.raven.catalogo_raven import FORME, GRADI

NORME = [{"da": 72, "a": 83, "p5": 10, "p10": 12, "p25": 15, "p50": 19, "p75": 23, "p90": 27, "p95": 30},
         {"da": 84, "a": 95, "p5": 12, "p10": 14, "p25": 18, "p50": 22, "p75": 26, "p90": 30, "p95": 32}]
CHIAVE = {"A": [1] * 12, "Ab": [2] * 12, "B": [3] * 12}


def test_catalogo():
    assert sum(FORME["CPM"]["item"] for _ in FORME["CPM"]["serie"]) == 36
    assert sum(FORME["SPM"]["item"] for _ in FORME["SPM"]["serie"]) == 60
    for f in FORME.values():
        assert set(f["alternative"]) == set(f["serie"])


def test_eta():
    assert sc.eta_mesi(date(2019, 3, 15), date(2026, 3, 14)) == 83
    assert sc.eta_mesi(date(2019, 3, 15), date(2026, 3, 15)) == 84
    assert sc.eta_mesi("2019-03-15", "15/03/2026") == 84
    assert sc.eta_mesi(None, date(2026, 1, 1)) is None
    assert sc.eta_testo(85) == "7 anni e 1 mese"
    assert sc.eta_testo(12) == "1 anno"


def test_totali():
    p = sc.punteggi_da_totali("CPM", {"A": 10, "Ab": 8, "B": 5})
    assert p["totale"] == 23 and p["massimo"] == 36
    with pytest.raises(ValueError):
        sc.punteggi_da_totali("CPM", {"A": 13, "Ab": 0, "B": 0})


def test_esiti():
    p = sc.punteggi_da_esiti("SPM", {"A": [True] * 12, "B": [True] * 6 + [False] * 6, "C": [None] * 12})
    assert p["serie"] == {"A": 12, "B": 6, "C": 0, "D": 0, "E": 0} and p["totale"] == 18


def test_risposte_con_chiave():
    r = {"A": [1] * 12, "Ab": [2] * 6 + [5] * 6, "B": [3, 3, None, float("nan")] + [1] * 8}
    p = sc.punteggi_da_risposte("CPM", r, CHIAVE)
    assert p["serie"] == {"A": 12, "Ab": 6, "B": 2} and p["omessi"] == 2
    with pytest.raises(ValueError):
        sc.punteggi_da_risposte("CPM", r, {})


def test_leggi_chiave():
    ok, err = sc.leggi_chiave("CPM", {"A": "1 2 3 4 5 6 1 2 3 4 5 6", "Ab": "123456123456", "B": "1,2,3,4,5,6,1,2,3,4,5,6"})
    assert not err and ok["A"][:3] == [1, 2, 3]
    _, err = sc.leggi_chiave("CPM", {"A": "123", "Ab": "123456123457", "B": "123456123456"})
    assert len(err) == 2                      # A corta, Ab con un 7 (alternative 1-6)
    ok, err = sc.leggi_chiave("SPM", {s: "8" * 12 if s in "CDE" else "6" * 12 for s in "ABCDE"})
    assert not err


@pytest.mark.parametrize("grezzo,grado", [(30, "I"), (35, "I"), (27, "II+"), (23, "II"), (26, "II"),
                                          (20, "III+"), (19, "III"), (17, "III-"), (15, "IV"),
                                          (13, "IV"), (12, "IV-"), (11, "IV-"), (10, "V"), (3, "V")])
def test_grado_da_punti(grezzo, grado):
    assert sc.grado_da_punti(grezzo, NORME[0]) == grado


@pytest.mark.parametrize("p,grado", [(99, "I"), (95, "I"), (90, "II+"), (75, "II"), (60, "III+"), (50, "III"),
                                     (30, "III-"), (25, "IV"), (10, "IV-"), (5, "V"), (1, "V")])
def test_grado_da_percentile(p, grado):
    assert sc.grado_da_percentile(p) == grado
    assert grado in GRADI


def test_riga_incompleta():
    riga = {"da": 36, "a": 47, "p25": 8, "p50": 11, "p75": 14}
    assert sc.grado_da_punti(20, riga) == "II"
    assert sc.grado_da_punti(12, riga) == "III+"
    assert sc.grado_da_punti(5, riga) == "IV"
    assert sc.grado_da_punti(12, {"da": 36, "a": 47, "p5": 3, "p50": 11, "p95": 20}) is None


def test_controlla_norme():
    buone, err = sc.controlla_norme("CPM", NORME + [{"da": None, "a": None}])
    assert not err and len(buone) == 2
    _, err = sc.controlla_norme("CPM", [dict(NORME[0], p50=40)])
    assert err                                 # 40 > 36 e non crescente
    _, err = sc.controlla_norme("CPM", [NORME[0], dict(NORME[1], da=80)])
    assert any("sovrappongono" in e for e in err)


def test_valuta_e_norme():
    p = sc.punteggi_da_totali("CPM", {"A": 9, "Ab": 6, "B": 4})          # 19
    r = sc.valuta("CPM", p, 78, NORME)
    assert r["grado"] == "III" and r["fascia_eta"] == "6;0–6;11"
    assert sc.valuta("CPM", p, 90, NORME)["grado"] == "III-"              # stessa prova, fascia successiva
    fuori = sc.valuta("CPM", p, 200, NORME)
    assert fuori["grado"] is None and "non rientra" in fuori["motivo_senza_norma"]
    assert "non è ancora caricata" in sc.valuta("CPM", p, 78, [])["motivo_senza_norma"]
    man = sc.valuta("CPM", p, 78, NORME, percentile_manuale=8)
    assert man["grado"] == "IV-" and man["origine_norma"] == "manuale" and "8°" in man["fascia"]


def test_composizione():
    attese, err = sc.controlla_attese("CPM", [{"totale": 19, "A": 9, "Ab": 6, "B": 4},
                                              {"totale": None, "A": None, "Ab": None, "B": None}])
    assert not err and attese == {"19": [9, 6, 4]}
    _, err = sc.controlla_attese("CPM", [{"totale": 19, "A": 9, "Ab": 6, "B": 5}])
    assert err
    ok = sc.composizione("CPM", sc.punteggi_da_totali("CPM", {"A": 10, "Ab": 5, "B": 4}), attese)
    assert not ok["atipica"] and ok["scarti"] == {"A": 1, "Ab": -1, "B": 0}
    ko = sc.composizione("CPM", sc.punteggi_da_totali("CPM", {"A": 12, "Ab": 2, "B": 5}), attese)
    assert ko["atipica"] and ko["serie_fuori"] == ["A", "Ab"]
    assert sc.composizione("CPM", sc.punteggi_da_totali("CPM", {"A": 1, "Ab": 1, "B": 1}), attese) is None


def test_relazione():
    p = sc.punteggi_da_totali("CPM", {"A": 12, "Ab": 2, "B": 5})
    r = sc.valuta("CPM", p, 78, NORME, {"19": [9, 6, 4]}, fonte="norme di prova")
    t = sc.relazione("Rossi Mario", "CPM", date(2026, 11, 24), r,
                     {"collaborazione": "adeguata", "attenzione": "—", "minuti": 18, "note": "Porta gli occhiali."})
    assert "Rossi Mario" in t and "24/11/2026" in t and "6 anni e 6 mesi" in t
    assert "19 risposte corrette su 36" in t and "grado III" in t and "norme di prova" in t
    assert "si discosta" in t and "Porta gli occhiali." in t and "18 minuti" in t
    senza = sc.relazione("Rossi Mario", "SPM", date(2026, 11, 24),
                         sc.valuta("SPM", sc.punteggi_da_totali("SPM", dict.fromkeys("ABCDE", 8)), 200))
    assert "40 risposte corrette su 60" in senza and "non è stato confrontato" in senza and "grado" not in senza
