import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "modules" / "studi"))
from collections import Counter
from datetime import datetime
from zoneinfo import ZoneInfo
import pegasis_code, db_studi, testi_privacy

def test_round_trip():
    c = pegasis_code.study_program("Studio Pegasis · gruppo B", "K7QX2M", "B", 1_800_000_000_000, 20, 30, [], "Grazie & a presto = ok")
    f = pegasis_code.decode("Ecco il codice:\n" + c + "\nciao")
    assert c.startswith("PGS1.") and f["pc"] == "K7QX2M" and f["gr"] == "B" and f["da"] == "1800000000000"
    assert f["no"] == "Grazie & a presto = ok" and f["lv"] == "BASIC"

def test_blocchi_bilanciati():
    l = db_studi.lista_blocchi(["A", "B"], 4, 200, seed=42)
    assert len(l) == 200
    for i in range(0, 200, 4):
        assert Counter(l[i:i+4]) == Counter({"A": 2, "B": 2})
    assert l != db_studi.lista_blocchi(["A", "B"], 4, 200, seed=43)

def test_partenza():
    roma = ZoneInfo("Europe/Rome"); ora = datetime(2026, 11, 20, 18, 30, tzinfo=roma)
    assert db_studi.data_partenza("A", "A", 35, ora) == ora
    b = db_studi.data_partenza("B", "A", 35, ora)
    assert (b.year, b.month, b.day, b.hour) == (2026, 12, 25, 0)

def test_csv():
    testo = """partecipante;K7QX2M
sessioni_fatte;7
tipo;data;sessioni;punteggio;risposte
WHO5;2026-11-20;0;60;3,3,3,3,3
PNEV;2026-11-20;0;54;2,1,3,2,2,3,2,2,3,2,1,3
COLORE;2026-11-21;;;BLU
prove;data;sessioni;pvt_mediana_ms;pvt_cali;pvt_anticipi;gng_accuratezza;gng_errori_commissione;gng_omissioni;gng_tr_medio_ms;span_avanti;span_indietro
PROVE;2026-11-20;0;301;2;1;0.97;3;2;412;6;5
"""
    cod, righe = db_studi.leggi_csv_pegasis(testo)
    assert cod == "K7QX2M"
    tipi = Counter(r["tipo"] for r in righe)
    assert tipi == Counter({"SESSIONI": 1, "WHO5": 1, "PNEV": 1, "COLORE": 1, "PROVE": 1})
    prove = next(r for r in righe if r["tipo"] == "PROVE")
    assert "pvt_mediana_ms=301" in prove["valori"] and "span_indietro=5" in prove["valori"]

def test_consensi_obbligatori():
    obbl = [k for k, _, o in testi_privacy.CONSENSI if o]
    assert "dati_salute" in obbl and "ricontatto" not in obbl

if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"):
            f(); print("OK  ", n)
    # codice per la verifica incrociata con l'app
    print("CODICE", pegasis_code.study_program("Studio Pegasis · gruppo B", "K7QX2M", "B", 1_800_000_000_000, 20, 30, [], "Grazie & a presto = ok"))
