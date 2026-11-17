"""Modulo «Studi e ricerca» — archivio degli studi con i partecipanti pseudonimizzati.

Struttura (GDPR, pseudonimizzazione):
  - ricerca_studi_identita: nome, contatti, consensi → solo per il responsabile
  - ricerca_studi_partecipanti / ricerca_studi_dati: dati di ricerca, legati SOLO al codice partecipante
  - ricerca_studi_registro: chi ha fatto cosa e quando (accountability)
Le funzioni ricevono una connessione PostgreSQL (psycopg2) e usano segnaposto %s.
"""
import csv
import io
import random
import secrets
from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo

try:  # dentro il pacchetto modules.studi
    from . import pegasis_code
    from .testi_privacy import CONSENSI, PRIVACY_VERSIONE
except ImportError:  # import diretto dalla cartella
    import pegasis_code
    from testi_privacy import CONSENSI, PRIVACY_VERSIONE

ROMA = ZoneInfo("Europe/Rome")

# ---------------- Accesso al database ----------------
# Il gestionale usa un proprio cursore (righe come tuple o come dizionari, senza «with»):
# queste funzioni funzionano con entrambi e con psycopg2 puro.

def _rows(cur):
    rows = cur.fetchall() or []
    if rows and isinstance(rows[0], dict):
        return [dict(r) for r in rows]
    cols = [d[0] for d in (cur.description or [])]
    return [dict(zip(cols, r)) for r in rows]


def _one(cur):
    """Prima riga come dizionario, o None."""
    r = cur.fetchone()
    if r is None:
        return None
    if isinstance(r, dict):
        return dict(r)
    return dict(zip([d[0] for d in cur.description], r))


def _val(cur):
    """Primo valore della prima riga, o None."""
    r = cur.fetchone()
    if r is None:
        return None
    return list(r.values())[0] if isinstance(r, dict) else r[0]


def _close(cur):
    try:
        cur.close()
    except Exception:
        pass

ALFABETO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # senza 0/O, 1/I: si dettano senza errori

SCHEMA = """
CREATE TABLE IF NOT EXISTS ricerca_studi (
    id BIGSERIAL PRIMARY KEY,
    titolo TEXT NOT NULL,
    descrizione TEXT DEFAULT '',
    comitato_etico TEXT DEFAULT '',
    sessioni INT NOT NULL DEFAULT 20,
    minuti INT NOT NULL DEFAULT 30,
    attesa_giorni INT NOT NULL DEFAULT 35,
    brani TEXT DEFAULT '',
    gruppi TEXT NOT NULL DEFAULT 'A,B',
    blocco INT NOT NULL DEFAULT 4,
    token_iscrizione TEXT UNIQUE NOT NULL,
    iscrizioni_aperte BOOLEAN NOT NULL DEFAULT TRUE,
    creato TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS ricerca_studi_randomizzazione (
    studio_id BIGINT NOT NULL REFERENCES ricerca_studi(id) ON DELETE CASCADE,
    posizione INT NOT NULL,
    gruppo TEXT NOT NULL,
    usato BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (studio_id, posizione)
);
CREATE TABLE IF NOT EXISTS ricerca_studi_identita (
    id BIGSERIAL PRIMARY KEY,
    studio_id BIGINT NOT NULL REFERENCES ricerca_studi(id) ON DELETE CASCADE,
    codice TEXT NOT NULL,
    nome TEXT NOT NULL,
    cognome TEXT NOT NULL,
    email TEXT DEFAULT '',
    telefono TEXT DEFAULT '',
    consenso_data TIMESTAMPTZ NOT NULL,
    privacy_versione TEXT NOT NULL,
    consensi TEXT NOT NULL,
    ricontatto BOOLEAN NOT NULL DEFAULT FALSE,
    modalita TEXT NOT NULL DEFAULT 'online',
    revocato TIMESTAMPTZ,
    UNIQUE (studio_id, codice)
);
CREATE TABLE IF NOT EXISTS ricerca_studi_partecipanti (
    id BIGSERIAL PRIMARY KEY,
    studio_id BIGINT NOT NULL REFERENCES ricerca_studi(id) ON DELETE CASCADE,
    codice TEXT NOT NULL,
    gruppo TEXT NOT NULL,
    inizio TIMESTAMPTZ NOT NULL,
    fascia_eta TEXT, sesso TEXT, mano TEXT, udito TEXT, acufene TEXT, cuffie TEXT,
    codice_pegasis TEXT NOT NULL,
    iscritto TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (studio_id, codice)
);
CREATE TABLE IF NOT EXISTS ricerca_studi_dati (
    id BIGSERIAL PRIMARY KEY,
    studio_id BIGINT NOT NULL REFERENCES ricerca_studi(id) ON DELETE CASCADE,
    codice TEXT NOT NULL,
    tipo TEXT NOT NULL,
    data DATE,
    sessioni INT,
    punteggio NUMERIC,
    valori TEXT,
    ricevuto TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (studio_id, codice, tipo, data, sessioni, valori)
);
CREATE TABLE IF NOT EXISTS ricerca_studi_registro (
    id BIGSERIAL PRIMARY KEY,
    studio_id BIGINT,
    codice TEXT,
    azione TEXT NOT NULL,
    operatore TEXT DEFAULT '',
    quando TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


def _rollback_su_errore(fn):
    """Se una scrittura fallisce, annulla la transazione: la connessione del gestionale resta utilizzabile."""
    import functools

    @functools.wraps(fn)
    def wrap(conn, *a, **k):
        # «sveglia» la connessione prima di scrivere: se il server l'aveva chiusa, il gestionale la riapre ORA,
        # e tutte le istruzioni che seguono girano sulla stessa connessione (niente righe «sparite» a metà)
        try:
            c = conn.cursor(); c.execute("SELECT 1"); c.fetchone(); _close(c)
        except Exception:
            pass
        try:
            return fn(conn, *a, **k)
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            raise
    return wrap


@_rollback_su_errore
def crea_tabelle(conn):
    cur = conn.cursor()
    try:
        cur.execute(SCHEMA)
    finally:
        _close(cur)
    conn.commit()


def _log(cur, studio_id, codice, azione, operatore=""):
    cur.execute("INSERT INTO ricerca_studi_registro (studio_id, codice, azione, operatore) VALUES (%s,%s,%s,%s)",
                (studio_id, codice, azione, operatore))


# ---------------- Randomizzazione ----------------

def lista_blocchi(gruppi: list[str], blocco: int, n: int, seed: int) -> list[str]:
    """Randomizzazione a blocchi permutati: in ogni blocco ogni gruppo compare lo stesso numero di volte."""
    if blocco % len(gruppi):
        raise ValueError("la dimensione del blocco deve essere un multiplo del numero di gruppi")
    rnd = random.Random(seed)
    out: list[str] = []
    while len(out) < n:
        b = [g for g in gruppi for _ in range(blocco // len(gruppi))]
        rnd.shuffle(b)
        out += b
    return out[:n]


@_rollback_su_errore
def crea_studio(conn, titolo, descrizione="", sessioni=20, minuti=30, attesa_giorni=35, brani="",
                gruppi="A,B", blocco=4, posti=200, comitato_etico="", operatore=""):
    token = secrets.token_urlsafe(12)
    seed = secrets.randbits(32)
    elenco = [g.strip() for g in gruppi.split(",") if g.strip()]
    lista = lista_blocchi(elenco, blocco, posti, seed)
    cur = conn.cursor()
    try:
        # un'unica istruzione: studio, lista di randomizzazione e registro nascono insieme o per niente
        cur.execute("""
            WITH s AS (
                INSERT INTO ricerca_studi (titolo, descrizione, sessioni, minuti, attesa_giorni, brani, gruppi, blocco,
                                           token_iscrizione, comitato_etico)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id
            ), r AS (
                INSERT INTO ricerca_studi_randomizzazione (studio_id, posizione, gruppo)
                SELECT s.id, x.pos, x.gruppo FROM s, unnest(%s, %s) AS x(pos, gruppo)
            ), l AS (
                INSERT INTO ricerca_studi_registro (studio_id, codice, azione, operatore)
                SELECT s.id, NULL, %s, %s FROM s
            )
            SELECT id FROM s""",
                    (titolo, descrizione, sessioni, minuti, attesa_giorni, brani, ",".join(elenco), blocco, token, comitato_etico,
                     list(range(len(lista))), lista,
                     f"studio creato (lista di randomizzazione: {posti} posti, blocchi da {blocco})", operatore))
        sid = _val(cur)
    finally:
        _close(cur)
    conn.commit()
    return sid


def elenco_studi(conn):
    cur = conn.cursor()
    try:
        cur.execute("""SELECT s.id, s.titolo, s.sessioni, s.attesa_giorni, s.token_iscrizione, s.iscrizioni_aperte,
                       (SELECT count(*) FROM ricerca_studi_partecipanti p WHERE p.studio_id = s.id) AS iscritti
                       FROM ricerca_studi s ORDER BY s.creato DESC""")
        return _rows(cur)
    finally:
        _close(cur)


def studio(conn, sid=None, token=None):
    cur = conn.cursor()
    try:
        if token is not None:
            cur.execute("SELECT * FROM ricerca_studi WHERE token_iscrizione = %s", (token,))
        else:
            cur.execute("SELECT * FROM ricerca_studi WHERE id = %s", (sid,))
        return _one(cur)
    finally:
        _close(cur)


@_rollback_su_errore
def imposta_iscrizioni(conn, sid, aperte: bool, operatore=""):
    cur = conn.cursor()
    try:
        cur.execute("UPDATE ricerca_studi SET iscrizioni_aperte = %s WHERE id = %s", (aperte, sid))
        _log(cur, sid, None, "iscrizioni aperte" if aperte else "iscrizioni chiuse", operatore)
    finally:
        _close(cur)
    conn.commit()


# ---------------- Iscrizione ----------------

def nuovo_codice(cur, sid) -> str:
    while True:
        c = "".join(secrets.choice(ALFABETO) for _ in range(6))
        cur.execute("SELECT 1 FROM ricerca_studi_identita WHERE studio_id = %s AND codice = %s", (sid, c))
        if cur.fetchone() is None:
            return c


def data_partenza(gruppo: str, primo_gruppo: str, attesa_giorni: int, ora: datetime) -> datetime:
    """Il primo gruppo parte subito; gli altri dopo [attesa_giorni], alle 00:00 ora italiana."""
    if gruppo == primo_gruppo:
        return ora
    giorno = (ora.astimezone(ROMA) + timedelta(days=attesa_giorni)).date()
    return datetime.combine(giorno, time(0, 0), ROMA)


@_rollback_su_errore
def iscrivi(conn, sid, nome, cognome, email, telefono, dati_base: dict, consensi: dict,
            modalita="online", operatore=""):
    """Iscrive un partecipante: verifica i consensi, crea il codice, assegna il gruppo, genera il codice Pegasis.
    Restituisce dict con codice, gruppo, inizio e codice_pegasis."""
    mancanti = [k for k, _, obbl in CONSENSI if obbl and not consensi.get(k)]
    if mancanti:
        raise ValueError("Mancano i consensi obbligatori: " + ", ".join(mancanti))
    s = studio(conn, sid)
    if s is None or not s["iscrizioni_aperte"]:
        raise ValueError("Le iscrizioni a questo studio sono chiuse.")
    ora = datetime.now(ROMA)
    cur = conn.cursor()
    try:
        cur.execute("""SELECT posizione, gruppo FROM ricerca_studi_randomizzazione WHERE studio_id = %s AND NOT usato
                       ORDER BY posizione LIMIT 1 FOR UPDATE""", (sid,))
        r = _one(cur)
        if r is None:
            raise ValueError("Posti esauriti: allunga la lista di randomizzazione.")
        pos, gruppo = r["posizione"], r["gruppo"]
        cur.execute("UPDATE ricerca_studi_randomizzazione SET usato = TRUE WHERE studio_id = %s AND posizione = %s", (sid, pos))
        codice = nuovo_codice(cur, sid)
        primo = s["gruppi"].split(",")[0]
        inizio = data_partenza(gruppo, primo, s["attesa_giorni"], ora)
        start_ms = 0 if gruppo == primo else int(inizio.timestamp() * 1000)
        brani = [b.strip() for b in (s["brani"] or "").split(",") if b.strip()]
        cp = pegasis_code.study_program(f"Studio Pegasis · gruppo {gruppo}", codice, gruppo, start_ms,
                                        s["sessioni"], s["minuti"], brani,
                                        "Una sessione al giorno, con le cuffie, in un posto tranquillo. Grazie per partecipare!")
        cur.execute("""INSERT INTO ricerca_studi_identita (studio_id, codice, nome, cognome, email, telefono, consenso_data,
                       privacy_versione, consensi, ricontatto, modalita) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (sid, codice, nome.strip(), cognome.strip(), email.strip(), telefono.strip(), ora, PRIVACY_VERSIONE,
                     ",".join(k for k, v in consensi.items() if v), bool(consensi.get("ricontatto")), modalita))
        cur.execute("""INSERT INTO ricerca_studi_partecipanti (studio_id, codice, gruppo, inizio, fascia_eta, sesso, mano, udito,
                       acufene, cuffie, codice_pegasis) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (sid, codice, gruppo, inizio, dati_base.get("fascia_eta"), dati_base.get("sesso"), dati_base.get("mano"),
                     dati_base.get("udito"), dati_base.get("acufene"), dati_base.get("cuffie"), cp))
        _log(cur, sid, codice, f"iscrizione ({modalita}), gruppo {gruppo}, privacy {PRIVACY_VERSIONE}", operatore)
    finally:
        _close(cur)
    conn.commit()
    return {"codice": codice, "gruppo": gruppo, "inizio": inizio, "codice_pegasis": cp}


# ---------------- Dati inviati dall'app ----------------

def leggi_csv_pegasis(testo: str):
    """Legge il testo di «Invia i dati allo studio». Restituisce (codice, righe) con righe = dict tipo/data/sessioni/punteggio/valori."""
    codice = None
    righe = []
    intestazioni = {}
    for row in csv.reader(io.StringIO(testo.strip()), delimiter=";"):
        if not row or not row[0]:
            continue
        k = row[0]
        if k == "partecipante":
            codice = row[1].strip().upper()
        elif k in ("tipo", "prove", "ascolto", "aderenza"):
            intestazioni[k] = row
        elif k in ("WHO5", "PNEV"):
            righe.append({"tipo": k, "data": row[1], "sessioni": int(row[2] or 0), "punteggio": float(row[3] or 0), "valori": row[4]})
        elif k == "COLORE":
            righe.append({"tipo": "COLORE", "data": row[1], "sessioni": None, "punteggio": None, "valori": row[4]})
        elif k == "PROVE":
            nomi = intestazioni.get("prove", [])[3:]
            valori = ";".join(f"{n}={v}" for n, v in zip(nomi, row[3:]))
            righe.append({"tipo": "PROVE", "data": row[1], "sessioni": int(row[2] or 0), "punteggio": None, "valori": valori})
        elif k == "ASCOLTO":
            # test di ascolto con il modello di cuffie: cuffie, tipo, soglie dx/sx, selettività, lateralità…
            nomi = intestazioni.get("ascolto", [])[3:]
            valori = ";".join(f"{n}={v}" for n, v in zip(nomi, row[3:]))
            righe.append({"tipo": "ASCOLTO", "data": row[1], "sessioni": int(row[2] or 0), "punteggio": None, "valori": valori})
        elif k == "ADERENZA":
            # riepilogo dell'aderenza (serie, riposi, scudi, giorni saltati, promemoria): sostituisce il precedente
            nomi = intestazioni.get("aderenza", [])[3:]
            valori = ";".join(f"{n}={v}" for n, v in zip(nomi, row[3:]))
            righe.append({"tipo": "ADERENZA", "data": row[1], "sessioni": int(row[2] or 0), "punteggio": None, "valori": valori})
        elif k == "GIORNO":
            # stato di ogni giorno del percorso: ASCOLTO, RIPOSO, SCUDO, SALTATO
            righe.append({"tipo": "GIORNO", "data": row[1], "sessioni": None, "punteggio": None, "valori": row[4].strip()})
        elif k == "versione_app":
            righe.append({"tipo": "VERSIONE", "data": None, "sessioni": None, "punteggio": None, "valori": row[1].strip()})
        elif k == "sessioni_fatte":
            righe.append({"tipo": "SESSIONI", "data": None, "sessioni": int(row[1] or 0), "punteggio": None, "valori": ""})
    if not codice:
        raise ValueError("Nel testo manca la riga «partecipante».")
    return codice, righe


@_rollback_su_errore
def importa_dati(conn, sid, testo, operatore=""):
    codice, righe = leggi_csv_pegasis(testo)
    cur = conn.cursor()
    try:
        cur.execute("SELECT 1 FROM ricerca_studi_partecipanti WHERE studio_id = %s AND codice = %s", (sid, codice))
        if cur.fetchone() is None:
            raise ValueError(f"Il codice {codice} non è iscritto a questo studio.")
        nuovi = 0
        for r in righe:
            if r["tipo"] in ("SESSIONI", "ADERENZA"):
                cur.execute("DELETE FROM ricerca_studi_dati WHERE studio_id = %s AND codice = %s AND tipo = %s", (sid, codice, r["tipo"]))
            elif r["tipo"] == "GIORNO":
                # un solo stato per giorno: se è cambiato si sostituisce
                cur.execute("""DELETE FROM ricerca_studi_dati WHERE studio_id = %s AND codice = %s AND tipo = 'GIORNO'
                               AND data = %s::date AND valori IS DISTINCT FROM %s::text""", (sid, codice, r["data"], r["valori"]))
            # niente doppioni anche quando qualche campo è vuoto (colori senza sessioni): l'invio automatico ripete tutto
            cur.execute("""INSERT INTO ricerca_studi_dati (studio_id, codice, tipo, data, sessioni, punteggio, valori)
                           SELECT %s,%s,%s,%s,%s,%s,%s
                           WHERE NOT EXISTS (SELECT 1 FROM ricerca_studi_dati WHERE studio_id = %s AND codice = %s AND tipo = %s
                                 AND data IS NOT DISTINCT FROM %s::date AND sessioni IS NOT DISTINCT FROM %s::int
                                 AND valori IS NOT DISTINCT FROM %s::text)""",
                        (sid, codice, r["tipo"], r["data"], r["sessioni"], r["punteggio"], r["valori"],
                         sid, codice, r["tipo"], r["data"], r["sessioni"], r["valori"]))
            if r["tipo"] not in ("SESSIONI", "ADERENZA", "GIORNO"):
                nuovi += max(int(getattr(cur, "rowcount", 0) or 0), 0)
        _log(cur, sid, codice, f"importati {nuovi} dati nuovi", operatore)
    finally:
        _close(cur)
    conn.commit()
    return codice, nuovi


def decodifica_pacchetto(d: str) -> str:
    """Testo dei dati inviato da Pegasis con il link (deflate senza intestazione + base64 URL)."""
    import base64
    import zlib
    d = (d or "").strip()
    raw = base64.urlsafe_b64decode(d + "=" * (-len(d) % 4))
    if len(raw) > 200_000:
        raise ValueError("Pacchetto troppo grande.")
    return zlib.decompress(raw, -15).decode("utf-8")


@_rollback_su_errore
def importa_automatico(conn, d: str):
    """Riceve i dati dal link dell'app: trova lo studio dal codice partecipante e li salva.
    Restituisce (codice, nuovi, titolo_studio). Accetta solo codici iscritti (e non ritirati)."""
    testo = decodifica_pacchetto(d)
    codice, _ = leggi_csv_pegasis(testo)
    cur = conn.cursor()
    try:
        cur.execute("""SELECT p.studio_id, s.titolo FROM ricerca_studi_partecipanti p JOIN ricerca_studi s ON s.id = p.studio_id
                       WHERE p.codice = %s ORDER BY p.iscritto DESC LIMIT 1""", (codice,))
        r = _one(cur)
    finally:
        _close(cur)
    if r is None:
        raise ValueError("Codice partecipante non iscritto a nessuno studio.")
    codice, nuovi = importa_dati(conn, r["studio_id"], testo, "invio dall'app")
    return codice, nuovi, r["titolo"]


# ---------------- Avanzamento ed esportazione ----------------

def avanzamento(conn, sid):
    """Una riga per partecipante, con nome (solo uso interno) e stato delle misure."""
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT p.codice, i.nome || ' ' || i.cognome AS nome, p.gruppo, p.inizio,
                   COALESCE((SELECT max(sessioni) FROM ricerca_studi_dati d WHERE d.studio_id = p.studio_id AND d.codice = p.codice
                             AND d.tipo = 'SESSIONI'), 0) AS sessioni,
                   (SELECT count(DISTINCT d.data) FROM ricerca_studi_dati d WHERE d.studio_id = p.studio_id AND d.codice = p.codice
                    AND d.tipo = 'WHO5') AS questionari,
                   (SELECT count(*) FROM ricerca_studi_dati d WHERE d.studio_id = p.studio_id AND d.codice = p.codice
                    AND d.tipo = 'PROVE') AS prove,
                   (SELECT substring(d.valori from 'serie=([0-9]+)')::int FROM ricerca_studi_dati d WHERE d.studio_id = p.studio_id
                    AND d.codice = p.codice AND d.tipo = 'ADERENZA' LIMIT 1) AS serie,
                   (SELECT count(*) FROM ricerca_studi_dati d WHERE d.studio_id = p.studio_id AND d.codice = p.codice
                    AND d.tipo = 'GIORNO' AND d.valori = 'SALTATO') AS giorni_saltati,
                   (SELECT round(100.0 * count(*) FILTER (WHERE d.valori = 'ASCOLTO') / NULLIF(count(*), 0))::int
                    FROM ricerca_studi_dati d WHERE d.studio_id = p.studio_id AND d.codice = p.codice
                    AND d.tipo = 'GIORNO') AS aderenza_pct,
                   i.revocato
            FROM ricerca_studi_partecipanti p JOIN ricerca_studi_identita i ON i.studio_id = p.studio_id AND i.codice = p.codice
            WHERE p.studio_id = %s ORDER BY p.iscritto""", (sid,))
        return _rows(cur)
    finally:
        _close(cur)


def esporta_anonimo(conn, sid):
    """Dati per l'analisi SENZA nomi né contatti: codice, gruppo, dati di base e misure."""
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT p.codice, p.gruppo, p.fascia_eta, p.sesso, p.mano, p.udito, p.acufene, p.cuffie,
                   d.tipo, d.data, d.sessioni, d.punteggio, d.valori
            FROM ricerca_studi_partecipanti p
            JOIN ricerca_studi_identita i ON i.studio_id = p.studio_id AND i.codice = p.codice AND i.revocato IS NULL
            LEFT JOIN ricerca_studi_dati d ON d.studio_id = p.studio_id AND d.codice = p.codice
            WHERE p.studio_id = %s ORDER BY p.codice, d.tipo, d.data""", (sid,))
        return _rows(cur)
    finally:
        _close(cur)


@_rollback_su_errore
def revoca(conn, sid, codice, operatore=""):
    """Ritiro del partecipante: cancella i dati di ricerca e l'anagrafica; resta solo la traccia della revoca."""
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM ricerca_studi_dati WHERE studio_id = %s AND codice = %s", (sid, codice))
        cur.execute("DELETE FROM ricerca_studi_partecipanti WHERE studio_id = %s AND codice = %s", (sid, codice))
        cur.execute("""UPDATE ricerca_studi_identita SET nome = '(ritirato)', cognome = '', email = '', telefono = '',
                       revocato = now() WHERE studio_id = %s AND codice = %s""", (sid, codice))
        _log(cur, sid, codice, "ritiro: dati cancellati", operatore)
    finally:
        _close(cur)
    conn.commit()


@_rollback_su_errore
def elimina_studio(conn, sid, operatore=""):
    """Cancella uno studio senza iscritti (per esempio creato due volte per errore). Con iscritti non si può."""
    cur = conn.cursor()
    try:
        # si può cancellare se non ha iscritti attivi: nessuno, oppure tutti già ritirati (dati già cancellati)
        cur.execute("SELECT count(*) FROM ricerca_studi_identita WHERE studio_id = %s AND revocato IS NULL", (sid,))
        if (_val(cur) or 0) > 0:
            raise ValueError("Lo studio ha ancora iscritti attivi: ritirali prima (scheda Partecipanti) e poi cancellalo.")
        for t in ("ricerca_studi_dati", "ricerca_studi_partecipanti", "ricerca_studi_identita", "ricerca_studi_randomizzazione"):
            cur.execute(f"DELETE FROM {t} WHERE studio_id = %s", (sid,))
        cur.execute("DELETE FROM ricerca_studi WHERE id = %s", (sid,))
        _log(cur, sid, None, "studio cancellato (senza iscritti)", operatore)
    finally:
        _close(cur)
    conn.commit()


def registro(conn, sid, limite=200):
    cur = conn.cursor()
    try:
        cur.execute("""SELECT quando, codice, azione, operatore FROM ricerca_studi_registro WHERE studio_id = %s
                       ORDER BY quando DESC LIMIT %s""", (sid, limite))
        return _rows(cur)
    finally:
        _close(cur)
