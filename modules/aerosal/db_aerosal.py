"""
modules/aerosal/db_aerosal.py
Accesso dati del modulo Aerosal (PostgreSQL, placeholder %s).
Tutte le funzioni ricevono la connessione dal chiamante: nessuna connessione
aperta qui dentro, cursori sempre chiusi con il context manager.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Rome")
EMAIL_ORDINI = "ordini@aerosal.it"
FASCE_RITIRO = ("09:00-12:00", "14:00-16:00")
PROVIDER_RATE = ("Klarna", "PayPal", "HeyLight", "Interno")
METODI_PAGAMENTO = ("contanti", "POS", "bonifico", "link", "Klarna", "PayPal", "HeyLight")


# --------------------------------------------------------------------- utils
@contextmanager
def _cur(conn):
    """Il cursore del gestionale (_PgCursor) non si puo' usare con «with»:
    questo lo apre e lo chiude comunque."""
    cur = conn.cursor()
    try:
        yield cur
    finally:
        try:
            cur.close()
        except Exception:
            pass


_SQL = Path(__file__).with_name("sql")


def _statement(testo: str) -> list[str]:
    righe = [l.split("--", 1)[0] for l in testo.splitlines()]
    return [s.strip() for s in "\n".join(righe).split(";") if s.strip()]


def assicura_schema(conn, studio_id: str) -> str:
    """Crea le tabelle e carica listino, categorie e date ritiro la prima
    volta. Si puo' rilanciare: tutto e' IF NOT EXISTS / ON CONFLICT."""
    try:
        with _cur(conn) as cur:
            for s in _statement((_SQL / "01_aerosal_schema.sql").read_text(encoding="utf-8")):
                cur.execute(s)
            seed = (_SQL / "02_aerosal_seed.sql").read_text(encoding="utf-8")
            # Con i parametri psycopg2 legge ogni % come segnaposto: «Sconto 20%»
            # nelle note delle promo va raddoppiato prima.
            for s in _statement(seed.replace("%", "%%").replace("'THE_ORGANISM'", "%s")):
                if "%s" in s:
                    cur.execute(s, (studio_id,) * s.count("%s"))
                else:
                    cur.execute(s.replace("%%", "%"))
        conn.commit()
        return ""
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        return str(e)


def _rows(cur) -> list[dict]:
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def _one(cur) -> dict | None:
    r = cur.fetchone()
    if r is None:
        return None
    return dict(zip([c[0] for c in cur.description], r))


def ora_roma() -> datetime:
    return datetime.now(TZ)


def piano_rate(totale: Decimal, n_rate: int, prima_scadenza: date) -> list[dict]:
    """Divide il totale in n rate mensili; l'arrotondamento finisce sull'ultima."""
    totale = Decimal(totale)
    base = (totale / n_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    rate = []
    for i in range(n_rate):
        mese = prima_scadenza.month - 1 + i
        anno = prima_scadenza.year + mese // 12
        mese = mese % 12 + 1
        giorno = min(prima_scadenza.day, 28)
        importo = base if i < n_rate - 1 else totale - base * (n_rate - 1)
        rate.append({"scadenza": date(anno, mese, giorno), "importo": importo})
    return rate


# ------------------------------------------------------------------ listino
def listino(conn, studio_id: str, solo_attivi: bool = True) -> list[dict]:
    sql = """SELECT id, codice, descrizione, tipo, n_sedute, prezzo, prezzo_pieno_rif,
                    promo_nome, limite_pacchetti, valido_dal, valido_al, attivo, note
             FROM aerosal_listino WHERE studio_id = %s"""
    if solo_attivi:
        sql += " AND attivo"
    sql += " ORDER BY tipo, n_sedute, codice"
    with _cur(conn) as cur:
        cur.execute(sql, (studio_id,))
        return _rows(cur)


def salva_voce_listino(conn, studio_id: str, v: dict) -> int:
    with _cur(conn) as cur:
        cur.execute(
            """INSERT INTO aerosal_listino
                 (studio_id, codice, descrizione, tipo, n_sedute, prezzo, prezzo_pieno_rif,
                  promo_nome, limite_pacchetti, valido_dal, valido_al, attivo, note)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
               ON CONFLICT (studio_id, codice) DO UPDATE SET
                 descrizione=EXCLUDED.descrizione, tipo=EXCLUDED.tipo,
                 n_sedute=EXCLUDED.n_sedute, prezzo=EXCLUDED.prezzo,
                 prezzo_pieno_rif=EXCLUDED.prezzo_pieno_rif, promo_nome=EXCLUDED.promo_nome,
                 limite_pacchetti=EXCLUDED.limite_pacchetti, valido_dal=EXCLUDED.valido_dal,
                 valido_al=EXCLUDED.valido_al, attivo=EXCLUDED.attivo, note=EXCLUDED.note
               RETURNING id""",
            (studio_id, v["codice"], v["descrizione"], v["tipo"], v["n_sedute"], v["prezzo"],
             v.get("prezzo_pieno_rif"), v.get("promo_nome"), v.get("limite_pacchetti"),
             v.get("valido_dal"), v.get("valido_al"), v.get("attivo", True), v.get("note")),
        )
        new_id = cur.fetchone()[0]
    conn.commit()
    return new_id


def promo_vendute(conn, studio_id: str, listino_id: int) -> int:
    """Quanti pacchetti di una promo sono già stati venduti (limite 5 per centro)."""
    with _cur(conn) as cur:
        cur.execute(
            """SELECT COUNT(*) FROM aerosal_pacchetti
               WHERE studio_id=%s AND listino_id=%s AND stato <> 'annullato'""",
            (studio_id, listino_id),
        )
        return cur.fetchone()[0]


# ------------------------------------------------------------- prime prove
def categorie_prova(conn) -> list[dict]:
    with _cur(conn) as cur:
        cur.execute("SELECT codice, descrizione, adulti, bambini FROM aerosal_categorie_prova ORDER BY ordine")
        return _rows(cur)


def registra_prova(conn, studio_id: str, p: dict) -> int:
    with _cur(conn) as cur:
        cur.execute(
            """INSERT INTO aerosal_prove
                 (studio_id, paziente_id, nominativo, telefono, categoria, origine,
                  data_prova, registrata_carta_respiro, note)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
            (studio_id, p.get("paziente_id"), p["nominativo"], p.get("telefono"),
             p["categoria"], p["origine"], p["data_prova"],
             p.get("registrata_carta_respiro", False), p.get("note")),
        )
        new_id = cur.fetchone()[0]
    conn.commit()
    return new_id


def prove(conn, studio_id: str, dal: date, al: date) -> list[dict]:
    with _cur(conn) as cur:
        cur.execute(
            """SELECT p.id, p.data_prova, p.nominativo, p.telefono, c.descrizione AS categoria,
                      p.origine, p.registrata_carta_respiro, p.convertita, p.pacchetto_id, p.note
               FROM aerosal_prove p JOIN aerosal_categorie_prova c ON c.codice = p.categoria
               WHERE p.studio_id=%s AND p.data_prova BETWEEN %s AND %s
               ORDER BY p.data_prova DESC, p.id DESC""",
            (studio_id, dal, al),
        )
        return _rows(cur)


def segna_carta_respiro(conn, studio_id: str, prova_id: int, valore: bool) -> None:
    with _cur(conn) as cur:
        cur.execute(
            "UPDATE aerosal_prove SET registrata_carta_respiro=%s WHERE id=%s AND studio_id=%s",
            (valore, prova_id, studio_id),
        )
    conn.commit()


def tasso_conversione(conn, studio_id: str, dal: date, al: date) -> dict:
    with _cur(conn) as cur:
        cur.execute(
            """SELECT COUNT(*) AS prove, COUNT(*) FILTER (WHERE convertita) AS convertite
               FROM aerosal_prove WHERE studio_id=%s AND data_prova BETWEEN %s AND %s""",
            (studio_id, dal, al),
        )
        r = _one(cur)
    r["tasso"] = round(100 * r["convertite"] / r["prove"], 1) if r["prove"] else 0.0
    return r


# ---------------------------------------------------------------- pacchetti
def vendi_pacchetto(conn, studio_id: str, d: dict) -> int:
    """Crea il pacchetto e il relativo piano pagamenti in un'unica transazione."""
    try:
        with _cur(conn) as cur:
            cur.execute(
                """INSERT INTO aerosal_pacchetti
                     (studio_id, paziente_id, listino_id, descrizione, n_sedute, prezzo_totale,
                      data_acquisto, modalita, provider_rate, n_rate, detraibile, note)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                (studio_id, d["paziente_id"], d.get("listino_id"), d["descrizione"],
                 d["n_sedute"], d["prezzo_totale"], d["data_acquisto"], d["modalita"],
                 d.get("provider_rate"), d.get("n_rate"), d.get("detraibile", True), d.get("note")),
            )
            pid = cur.fetchone()[0]

            if d["modalita"] == "rateale" and d.get("provider_rate") == "Interno":
                for r in piano_rate(d["prezzo_totale"], d["n_rate"], d["data_acquisto"]):
                    cur.execute(
                        """INSERT INTO aerosal_pagamenti (studio_id, pacchetto_id, scadenza, importo, pagato)
                           VALUES (%s,%s,%s,%s,FALSE)""",
                        (studio_id, pid, r["scadenza"], r["importo"]),
                    )
            else:
                # Pagamento unico, oppure rateale con finanziaria esterna:
                # il centro incassa l'intero importo in un'unica volta.
                cur.execute(
                    """INSERT INTO aerosal_pagamenti
                         (studio_id, pacchetto_id, scadenza, data_pagamento, importo, metodo, pagato)
                       VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                    (studio_id, pid, d["data_acquisto"],
                     d["data_acquisto"] if d.get("pagato_subito") else None,
                     d["prezzo_totale"], d.get("metodo"), bool(d.get("pagato_subito"))),
                )

            if d.get("prova_id"):
                cur.execute(
                    "UPDATE aerosal_prove SET convertita=TRUE, pacchetto_id=%s WHERE id=%s AND studio_id=%s",
                    (pid, d["prova_id"], studio_id),
                )
        conn.commit()
        return pid
    except Exception:
        conn.rollback()
        raise


def pacchetti_paziente(conn, studio_id: str, paziente_id: int) -> list[dict]:
    with _cur(conn) as cur:
        cur.execute(
            """SELECT * FROM aerosal_v_residuo
               WHERE studio_id=%s AND paziente_id=%s ORDER BY data_acquisto DESC""",
            (studio_id, paziente_id),
        )
        return _rows(cur)


def pacchetti_attivi(conn, studio_id: str) -> list[dict]:
    with _cur(conn) as cur:
        cur.execute(
            """SELECT * FROM aerosal_v_residuo
               WHERE studio_id=%s AND stato='attivo' ORDER BY sedute_residue ASC""",
            (studio_id,),
        )
        return _rows(cur)


def cambia_stato_pacchetto(conn, studio_id: str, pacchetto_id: int, stato: str) -> None:
    with _cur(conn) as cur:
        cur.execute(
            "UPDATE aerosal_pacchetti SET stato=%s WHERE id=%s AND studio_id=%s",
            (stato, pacchetto_id, studio_id),
        )
    conn.commit()


# ------------------------------------------------------------------- sedute
def registra_seduta(conn, studio_id: str, s: dict) -> int:
    """Registra una seduta; se il pacchetto è esaurito lo chiude come 'completato'."""
    try:
        with _cur(conn) as cur:
            cur.execute(
                "SELECT sedute_residue FROM aerosal_v_residuo WHERE pacchetto_id=%s AND studio_id=%s",
                (s["pacchetto_id"], studio_id),
            )
            row = cur.fetchone()
            if row is None:
                raise ValueError("Pacchetto non trovato.")
            if row[0] <= 0:
                raise ValueError("Il pacchetto non ha sedute residue.")

            cur.execute(
                """INSERT INTO aerosal_sedute
                     (studio_id, pacchetto_id, paziente_id, data_ora, durata_min, operatore,
                      tollerata, sintomi, interrotta, note)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                (studio_id, s["pacchetto_id"], s["paziente_id"], s.get("data_ora", ora_roma()),
                 s.get("durata_min", 30), s.get("operatore"), s.get("tollerata", True),
                 s.get("sintomi"), s.get("interrotta", False), s.get("note")),
            )
            sid = cur.fetchone()[0]
            if row[0] - 1 == 0:
                cur.execute(
                    "UPDATE aerosal_pacchetti SET stato='completato' WHERE id=%s AND studio_id=%s",
                    (s["pacchetto_id"], studio_id),
                )
        conn.commit()
        return sid
    except Exception:
        conn.rollback()
        raise


def sedute_pacchetto(conn, studio_id: str, pacchetto_id: int) -> list[dict]:
    with _cur(conn) as cur:
        cur.execute(
            """SELECT id, data_ora, durata_min, operatore, tollerata, sintomi, interrotta, note
               FROM aerosal_sedute WHERE studio_id=%s AND pacchetto_id=%s ORDER BY data_ora""",
            (studio_id, pacchetto_id),
        )
        return _rows(cur)


# ---------------------------------------------------------------- pagamenti
def rate_in_scadenza(conn, studio_id: str, entro: date) -> list[dict]:
    with _cur(conn) as cur:
        cur.execute(
            """SELECT g.id, g.scadenza, g.importo, p.paziente_id, p.descrizione, g.pacchetto_id
               FROM aerosal_pagamenti g JOIN aerosal_pacchetti p ON p.id = g.pacchetto_id
               WHERE g.studio_id=%s AND NOT g.pagato AND g.scadenza <= %s
               ORDER BY g.scadenza""",
            (studio_id, entro),
        )
        return _rows(cur)


def segna_pagato(conn, studio_id: str, pagamento_id: int, metodo: str,
                 data_pag: date, riferimento: str | None = None) -> None:
    with _cur(conn) as cur:
        cur.execute(
            """UPDATE aerosal_pagamenti SET pagato=TRUE, metodo=%s, data_pagamento=%s, riferimento=%s
               WHERE id=%s AND studio_id=%s""",
            (metodo, data_pag, riferimento, pagamento_id, studio_id),
        )
    conn.commit()


# --------------------------------------------------------------------- sale
def date_ritiro_future(conn, da: date | None = None) -> list[date]:
    with _cur(conn) as cur:
        cur.execute(
            "SELECT data_ritiro FROM aerosal_date_ritiro WHERE data_ritiro >= %s ORDER BY data_ritiro",
            (da or ora_roma().date(),),
        )
        return [r[0] for r in cur.fetchall()]


def aggiungi_data_ritiro(conn, d: date, note: str | None = None) -> None:
    with _cur(conn) as cur:
        cur.execute(
            "INSERT INTO aerosal_date_ritiro (data_ritiro, note) VALUES (%s,%s) ON CONFLICT DO NOTHING",
            (d, note),
        )
    conn.commit()


def salva_ordine_sale(conn, studio_id: str, o: dict) -> int:
    with _cur(conn) as cur:
        cur.execute(
            """INSERT INTO aerosal_ordini_sale
                 (studio_id, data_ordine, quantita, importo, data_pagamento,
                  email_inviata, data_ritiro, fascia, stato, note)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
            (studio_id, o["data_ordine"], o.get("quantita"), o.get("importo"),
             o.get("data_pagamento"), o.get("email_inviata", False), o.get("data_ritiro"),
             o.get("fascia"), o.get("stato", "da_pagare"), o.get("note")),
        )
        new_id = cur.fetchone()[0]
    conn.commit()
    return new_id


def ordini_sale(conn, studio_id: str) -> list[dict]:
    with _cur(conn) as cur:
        cur.execute(
            """SELECT id, data_ordine, quantita, importo, data_pagamento, email_inviata,
                      data_ritiro, fascia, stato, note
               FROM aerosal_ordini_sale WHERE studio_id=%s ORDER BY data_ordine DESC""",
            (studio_id,),
        )
        return _rows(cur)


def aggiorna_stato_ordine(conn, studio_id: str, ordine_id: int, stato: str) -> None:
    with _cur(conn) as cur:
        cur.execute(
            "UPDATE aerosal_ordini_sale SET stato=%s WHERE id=%s AND studio_id=%s",
            (stato, ordine_id, studio_id),
        )
    conn.commit()
