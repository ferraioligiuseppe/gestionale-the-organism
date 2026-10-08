"""
Modulo Grafomotricità e prove touch — database
Studio The Organism · www.pnev.it

Riceve le sessioni prodotte dalle prove HTML basate su PNEV Touch Engine
(corsivo, collega in ordine, linea dei numeri, ...) e le lega al paziente.

Convenzioni del gestionale: segnaposto %s, BIGSERIAL, TEXT, TIMESTAMPTZ, Europe/Rome.
Le funzioni ricevono la connessione `conn` dal chiamante (come pnev_pubblico).

RLS multi-tenant: allineare alle altre tabelle cliniche (vedi TODO_RLS in fondo).
"""
import base64
import json
import secrets
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Rome")
MAX_PAYLOAD_BYTES = 400_000
_ALFABETO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # senza 0/O e 1/I

# URL pubblici delle prove su pnev.it (cartella gestita col Gestore di file WP)
BASE_URL = "https://www.pnev.it/wp-content/uploads/giochi/touch/"

# Catalogo: chiave = campo "task" del payload. Le metriche indicate sono quelle mostrate
# nell'andamento; "meglio" dice in che direzione va il miglioramento (None = nessuna).
CATALOGO = {
    "corsivo": {
        "nome": "Corsivo", "area": "Pregrafismo e scrittura", "file": "pnev-corsivo.html",
        "metriche": [
            ("sintesi.stelle_medie", "Stelle medie", "su"),
            ("prove.precisione", "Precisione media (%)", "su"),
            ("prove.cinematica.vel_media_mm_s", "Velocità media (mm/s)", None),
            ("prove.cinematica.niv_per_10mm", "Picchi di velocità ogni 10 mm", "giu"),
            ("prove.cinematica.jerk_log_mediano", "Jerk (log)", "giu"),
            ("prove.cinematica.rapporto_aria_foglio", "Tempo in aria / sul foglio", "giu"),
        ],
    },
    "collega": {
        "nome": "Collega in ordine", "area": "Funzioni esecutive", "file": "pnev-collega.html",
        "metriche": [
            ("sintesi.tempo_numeri_s", "Tempo numeri (s)", "giu"),
            ("sintesi.tempo_numeri_lettere_s", "Tempo numeri e lettere (s)", "giu"),
            ("sintesi.rapporto_BA", "Rapporto parte 2 / parte 1", "giu"),
            ("sintesi.errori_numeri_lettere", "Errori numeri e lettere", "giu"),
            ("prove.cinematica.niv_per_10mm", "Picchi di velocità ogni 10 mm", "giu"),
        ],
    },
    "linea_numeri": {
        "nome": "Linea dei numeri", "area": "Calcolo", "file": "pnev-linea-numeri.html",
        "metriche": [
            ("sintesi.pae_medio", "PAE medio (%)", "giu"),
            ("sintesi.r2_lineare", "R² lineare", "su"),
            ("sintesi.r2_logaritmico", "R² logaritmico", None),
            ("sintesi.tr_mediano_ms", "Tempo mediano (ms)", "giu"),
        ],
    },
    "lettura_decodifica": {
        "nome": "Parole e non parole", "area": "Lettura", "file": "pnev-lettura.html?es=decodifica",
        "metriche": [
            ("sintesi.accuratezza_pct", "Accuratezza (%)", "su"),
            ("sintesi.sillabe_al_s_parole", "Sillabe/s parole", "su"),
            ("sintesi.sillabe_al_s_non_parole", "Sillabe/s non parole", "su"),
            ("sintesi.tr_mediano_non_parole_ms", "Tempo mediano non parole (ms)", "giu"),
        ],
    },
    "lettura_ran": {
        "nome": "Denominazione rapida (RAN)", "area": "Lettura", "file": "pnev-lettura.html?es=ran",
        "metriche": [
            ("sintesi.tempo_s", "Tempo (s)", "giu"),
            ("sintesi.elementi_al_s", "Elementi al secondo", "su"),
            ("sintesi.errori", "Errori", "giu"),
        ],
    },
    "lettura_bdpq": {
        "nome": "Trova la lettera (b d p q)", "area": "Lettura", "file": "pnev-lettura.html?es=bdpq",
        "metriche": [
            ("sintesi.accuratezza_pct", "Indice (%)", "su"),
            ("sintesi.omissioni", "Omissioni", "giu"),
            ("sintesi.falsi_allarmi", "Scambi", "giu"),
            ("sintesi.tempo_s", "Tempo (s)", "giu"),
        ],
    },
    "lettura_sillabe": {
        "nome": "Sillabe (segmentazione e fusione)", "area": "Lettura", "file": "pnev-lettura.html?es=sillabe",
        "metriche": [
            ("sintesi.accuratezza_pct", "Accuratezza (%)", "su"),
            ("sintesi.tr_mediano_ms", "Tempo mediano (ms)", "giu"),
        ],
    },
    "lettura_frasi": {
        "nome": "Vero o falso", "area": "Lettura", "file": "pnev-lettura.html?es=frasi",
        "metriche": [
            ("sintesi.accuratezza_pct", "Accuratezza (%)", "su"),
            ("sintesi.tr_mediano_ms", "Tempo mediano (ms)", "giu"),
        ],
    },
    "lettura_oculari": {
        "nome": "Movimenti oculari in lettura", "area": "Lettura", "file": "pnev-lettura.html?es=oculari",
        "metriche": [
            ("sintesi.tempo_colonne_s", "Tempo in colonna (s)", "giu"),
            ("sintesi.tempo_righe_corretto_s", "Tempo in riga corretto (s)", "giu"),
            ("sintesi.rapporto_righe_colonne", "Rapporto riga/colonna", "giu"),
            ("sintesi.errori", "Errori", "giu"),
        ],
    },
    "lettura_brano": {
        "nome": "Lettura di un brano", "area": "Lettura", "file": "pnev-lettura.html?es=brano",
        "metriche": [
            ("sintesi.sillabe_al_s", "Sillabe al secondo", "su"),
            ("sintesi.parole_al_minuto", "Parole al minuto", "su"),
            ("sintesi.errori", "Errori", "giu"),
        ],
    },
}

_schema_pronto = False


def init_db(conn):
    """Crea le tabelle se mancano. Idempotente."""
    global _schema_pronto
    if _schema_pronto:
        return
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS grafo_token (
            id          BIGSERIAL PRIMARY KEY,
            token       TEXT NOT NULL UNIQUE,
            paziente_id BIGINT NOT NULL,
            compiti     TEXT,
            scadenza    TIMESTAMPTZ NOT NULL,
            attivo      BOOLEAN NOT NULL DEFAULT TRUE,
            creato_da   TEXT,
            creato_il   TIMESTAMPTZ NOT NULL DEFAULT now()
        )""")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS grafo_sessioni (
            id                 BIGSERIAL PRIMARY KEY,
            paziente_id        BIGINT NOT NULL,
            token_id           BIGINT REFERENCES grafo_token(id) ON DELETE SET NULL,
            task               TEXT NOT NULL,
            versione           INTEGER,
            contesto           TEXT,
            avvio              TIMESTAMPTZ,
            fine               TIMESTAMPTZ,
            input_tipo         TEXT,
            calibrato          BOOLEAN,
            sintesi            JSONB,
            prove              JSONB,
            parametri          JSONB,
            dispositivo        JSONB,
            eta_mesi           INTEGER,
            classe             TEXT,
            consenso_normativo BOOLEAN NOT NULL DEFAULT FALSE,
            note               TEXT,
            creato_il          TIMESTAMPTZ NOT NULL DEFAULT now()
        )""")
    cur.execute("CREATE INDEX IF NOT EXISTS grafo_sessioni_paz_idx ON grafo_sessioni (paziente_id, task, avvio)")
    conn.commit()
    cur.close()
    _schema_pronto = True


# ── TOKEN ─────────────────────────────────────────────────────────────────────

def crea_token(conn, paziente_id, giorni=30, compiti=None, creato_da=""):
    """Token riutilizzabile per tutta la durata (le prove a casa sono più sedute)."""
    init_db(conn)
    token = "".join(secrets.choice(_ALFABETO) for _ in range(8))
    scadenza = datetime.now(TZ) + timedelta(days=int(giorni))
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO grafo_token (token, paziente_id, compiti, scadenza, creato_da) VALUES (%s,%s,%s,%s,%s) RETURNING id",
        (token, paziente_id, ",".join(compiti or []), scadenza, creato_da))
    conn.commit()
    cur.close()
    return token


def verifica_token(conn, token):
    """Record del token se attivo e non scaduto, altrimenti None."""
    if not token:
        return None
    init_db(conn)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, token, paziente_id, compiti, scadenza FROM grafo_token "
        "WHERE token=%s AND attivo AND scadenza > now()",
        (token.upper().strip(),))
    row = cur.fetchone()
    cur.close()
    if not row:
        return None
    return dict(zip(["id", "token", "paziente_id", "compiti", "scadenza"], row))


def token_paziente(conn, paziente_id):
    init_db(conn)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, token, compiti, scadenza, attivo, creato_il FROM grafo_token "
        "WHERE paziente_id=%s ORDER BY id DESC", (paziente_id,))
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    cur.close()
    return rows


def disattiva_token(conn, token_id):
    cur = conn.cursor()
    cur.execute("UPDATE grafo_token SET attivo=FALSE WHERE id=%s", (token_id,))
    conn.commit()
    cur.close()


def link_prova(task, token=None, contesto=None):
    url = BASE_URL + CATALOGO[task]["file"]
    q = []
    if token:
        q.append("t=" + token)
    if contesto:
        q.append("ctx=" + contesto)
    if not q:
        return url
    return url + ("&" if "?" in url else "?") + "&".join(q)


# ── PAYLOAD ───────────────────────────────────────────────────────────────────

def decodifica_payload(d):
    """Parametro d (base64url di JSON) → dict. Solleva ValueError se non valido."""
    if not d or len(d) > MAX_PAYLOAD_BYTES * 2:
        raise ValueError("Dati mancanti o troppo grandi")
    raw = base64.urlsafe_b64decode(d + "=" * (-len(d) % 4))
    if len(raw) > MAX_PAYLOAD_BYTES:
        raise ValueError("Dati troppo grandi")
    return valida_payload(json.loads(raw.decode("utf-8")))


def valida_payload(p):
    if not isinstance(p, dict) or p.get("v") != 1:
        raise ValueError("Formato non riconosciuto")
    if p.get("task") not in CATALOGO:
        raise ValueError("Prova sconosciuta: %s" % p.get("task"))
    if not isinstance(p.get("prove"), list):
        raise ValueError("Prove mancanti")
    return p


def _ts(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(TZ)
    except ValueError:
        return None


def salva_sessione(conn, paziente_id, payload, token_id=None, contesto=None,
                   eta_mesi=None, classe=None, consenso_normativo=False, note=None):
    """Salva una sessione. Evita i doppioni (stessa prova, stesso avvio, stesso paziente)."""
    init_db(conn)
    p = valida_payload(payload)
    disp = p.get("dispositivo") or {}
    avvio = _ts(p.get("avvio"))
    cur = conn.cursor()
    cur.execute(
        "SELECT id FROM grafo_sessioni WHERE paziente_id=%s AND task=%s AND avvio=%s",
        (paziente_id, p["task"], avvio))
    dup = cur.fetchone()
    if dup:
        cur.close()
        return dup[0], False
    cur.execute(
        """INSERT INTO grafo_sessioni
           (paziente_id, token_id, task, versione, contesto, avvio, fine, input_tipo, calibrato,
            sintesi, prove, parametri, dispositivo, eta_mesi, classe, consenso_normativo, note)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
        (paziente_id, token_id, p["task"], p.get("versione"), contesto or p.get("contesto"),
         avvio, _ts(p.get("fine")), disp.get("input"), bool(disp.get("calibrato")),
         json.dumps(p.get("sintesi") or {}), json.dumps(p["prove"]), json.dumps(p.get("parametri") or {}),
         json.dumps(disp), eta_mesi, classe, bool(consenso_normativo), note))
    sid = cur.fetchone()[0]
    conn.commit()
    cur.close()
    return sid, True


def sessioni_paziente(conn, paziente_id, task=None):
    init_db(conn)
    cur = conn.cursor()
    sql = ("SELECT id, task, versione, contesto, avvio, fine, input_tipo, calibrato, sintesi, prove, "
           "parametri, dispositivo, note FROM grafo_sessioni WHERE paziente_id=%s")
    args = [paziente_id]
    if task:
        sql += " AND task=%s"
        args.append(task)
    cur.execute(sql + " ORDER BY avvio DESC NULLS LAST, id DESC", args)
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    cur.close()
    for r in rows:
        for k in ("sintesi", "prove", "parametri", "dispositivo"):
            if isinstance(r[k], str):
                r[k] = json.loads(r[k])
    return rows


def elimina_sessione(conn, sessione_id, paziente_id):
    cur = conn.cursor()
    cur.execute("DELETE FROM grafo_sessioni WHERE id=%s AND paziente_id=%s", (sessione_id, paziente_id))
    conn.commit()
    cur.close()


def valore_metrica(sessione, percorso):
    """'sintesi.x' → valore; 'prove.a.b' → media sulle prove che lo hanno."""
    parti = percorso.split(".")
    if parti[0] == "sintesi":
        v = (sessione.get("sintesi") or {}).get(parti[1])
        return v if isinstance(v, (int, float)) else None
    vals = []
    for pr in sessione.get("prove") or []:
        v = pr
        for k in parti[1:]:
            v = v.get(k) if isinstance(v, dict) else None
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            vals.append(v)
    return round(sum(vals) / len(vals), 3) if vals else None


# TODO_RLS: se le tabelle cliniche usano la colonna dello studio e la policy RLS
# (es. studio_id + current_setting('app.studio_id')), aggiungere qui la stessa colonna
# e la stessa policy, copiandole da un modulo esistente (es. modules/anamnesi/db_anamnesi.py).
