# -*- coding: utf-8 -*-
"""
modules/whodas/db_whodas.py
WHODAS 2.0 — Versione a 36 item, somministrata da un intervistatore.

Strumento: World Health Organization Disability Assessment Schedule 2.0 (OMS, 2010).
Edizione italiana a cura di Lucilla Frattura, Paula Tonel e Carlo Zavaroni,
Regione Autonoma Friuli Venezia Giulia — Centro Collaboratore Italiano dell'OMS
per la Famiglia delle Classificazioni Internazionali (2018/2019).
Licenza CC BY-NC-ND. Gli item sono riprodotti verbatim, senza modifiche.

Algoritmo di punteggio complesso (IRT) ripreso dalla sintassi SPSS del Capitolo 8
del manuale (edizione italiana, con le correzioni introdotte dai traduttori).
"""

from datetime import datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Rome")

VERSIONE = "36-intervistatore"

ATTRIBUZIONE = (
    "WHODAS 2.0 © Organizzazione Mondiale della Sanità. Edizione italiana a cura di "
    "Lucilla Frattura, Paula Tonel e Carlo Zavaroni — Centro Collaboratore Italiano "
    "dell'OMS per la Famiglia delle Classificazioni Internazionali. Licenza CC BY-NC-ND."
)

# --------------------------------------------------------------------------- #
# Scala di risposta
# --------------------------------------------------------------------------- #

SCALA = {
    1: "Nessuna",
    2: "Poca",
    3: "Moderata",
    4: "Molta",
    5: "Moltissima o non posso farlo",
}

# --------------------------------------------------------------------------- #
# Struttura dello strumento
# --------------------------------------------------------------------------- #

DOMINI = {
    "1": {
        "titolo": "Attività cognitive",
        "introduzione": "Ora le farò alcune domande su comprensione e comunicazione.",
        "prompt": "Negli ultimi 30 giorni, quanta difficoltà ha avuto nel:",
    },
    "2": {
        "titolo": "Mobilità",
        "introduzione": "Ora le farò qualche domanda sulle difficoltà negli spostamenti.",
        "prompt": "Negli ultimi 30 giorni, quanta difficoltà ha avuto nel:",
    },
    "3": {
        "titolo": "Cura di sé",
        "introduzione": "Ora le farò qualche domanda sulle difficoltà nel prendersi cura di sé.",
        "prompt": "Negli ultimi 30 giorni, quanta difficoltà ha avuto nel:",
    },
    "4": {
        "titolo": "Relazioni interpersonali",
        "introduzione": (
            "Ora le farò qualche domanda sulle difficoltà nel relazionarsi con le persone. "
            "Si ricordi che le sto chiedendo solo di difficoltà che sono in relazione a "
            "problemi di salute. Con ciò intendo malattie, traumi, problemi mentali o "
            "emotivi e problemi con alcol o droghe."
        ),
        "prompt": "Negli ultimi 30 giorni, quanta difficoltà ha avuto nel:",
    },
    "5(1)": {
        "titolo": "Attività della vita quotidiana — cura della casa e della famiglia",
        "introduzione": (
            "Ora le farò qualche domanda sulle attività relative alla gestione della casa e "
            "al prendersi cura delle persone con cui vive o di quelle a lei care. Queste "
            "attività includono cucinare, pulire, fare la spesa, e prendersi cura degli "
            "altri e delle proprie cose."
        ),
        "prompt": "Tenendo conto delle sue condizioni di salute, negli ultimi 30 giorni, quanta difficoltà ha avuto nel:",
    },
    "5(2)": {
        "titolo": "Attività della vita quotidiana — attività lavorative o scolastiche",
        "introduzione": "Ora le farò qualche domanda sulle sua attività lavorativa o scolastica.",
        "prompt": "Tenendo conto delle sue condizioni di salute, negli ultimi 30 giorni, quanta difficoltà ha avuto nel:",
    },
    "6": {
        "titolo": "Partecipazione",
        "introduzione": (
            "Ora le farò delle domande sulla sua partecipazione alla vita sociale e "
            "sull'impatto dei suoi problemi di salute su di lei e sulla sua famiglia. Alcune "
            "di queste domande possono riguardare problemi che vanno oltre gli ultimi 30 "
            "giorni, tuttavia, nel rispondere, la prego di concentrarsi solo sugli ultimi 30 "
            "giorni. Le ricordo ancora una volta di rispondere a queste domande pensando ai "
            "problemi di salute fisici, mentali o emotivi, o relativi all'uso di alcol o droghe."
        ),
        "prompt": "Negli ultimi 30 giorni:",
    },
}

# (codice item, dominio, testo verbatim)
ITEMS = [
    ("D1.1", "1", "Concentrarsi nel fare qualcosa per dieci minuti?"),
    ("D1.2", "1", "Ricordarsi di fare cose importanti?"),
    ("D1.3", "1", "Analizzare e trovare soluzioni ai problemi della vita quotidiana?"),
    ("D1.4", "1", "Imparare cose nuove, come, per esempio, imparare a raggiungere un posto nuovo?"),
    ("D1.5", "1", "Capire quello che dicono gli altri?"),
    ("D1.6", "1", "Iniziare e portare avanti una conversazione?"),

    ("D2.1", "2", "Stare in piedi per un lungo periodo, come per 30 minuti?"),
    ("D2.2", "2", "Alzarsi da una posizione seduta?"),
    ("D2.3", "2", "Muoversi dentro casa?"),
    ("D2.4", "2", "Uscire di casa?"),
    ("D2.5", "2", "Camminare per una lunga distanza, come per un chilometro?"),

    ("D3.1", "3", "Lavarsi tutto il corpo?"),
    ("D3.2", "3", "Vestirsi?"),
    ("D3.3", "3", "Mangiare?"),
    ("D3.4", "3", "Stare da solo per qualche giorno?"),

    ("D4.1", "4", "Interagire con persone che non conosce?"),
    ("D4.2", "4", "Mantenere un'amicizia?"),
    ("D4.3", "4", "Relazionarsi con persone a cui è legato affettivamente?"),
    ("D4.4", "4", "Fare nuove amicizie?"),
    ("D4.5", "4", "Attività sessuale?"),

    ("D5.1", "5(1)", "Prendersi cura della casa e della famiglia per quanto è di sua responsabilità?"),
    ("D5.2", "5(1)", "Svolgere bene le attività più importanti che spettano a lei, relativamente alla cura della casa e della famiglia?"),
    ("D5.3", "5(1)", "Portare a termine tutte le attività che deve svolgere, relativamente alla cura della casa e della famiglia?"),
    ("D5.4", "5(1)", "Portare a termine con la rapidità necessaria le attività che spettano a lei, relativamente alla cura della casa e della famiglia?"),

    ("D5.5", "5(2)", "Svolgere l'attività lavorativa/scolastica quotidiana?"),
    ("D5.6", "5(2)", "Svolgere bene i suoi compiti lavorativi/scolastici più importanti?"),
    ("D5.7", "5(2)", "Portare a termine tutto quello che deve fare a livello lavorativo/scolastico?"),
    ("D5.8", "5(2)", "Portare a termine con la rapidità necessaria l'attività lavorativa/scolastica?"),

    ("D6.1", "6", "Quanti problemi ha avuto nel partecipare ad attività comunitarie (per esempio, feste, attività religiose o di altro tipo) come chiunque altro?"),
    ("D6.2", "6", "Quanti problemi ha avuto a causa di barriere o ostacoli nel mondo che la circonda?"),
    ("D6.3", "6", "Quanti problemi ha avuto nel vivere con dignità a causa di atteggiamenti e azioni di altre persone nei suoi confronti?"),
    ("D6.4", "6", "Quanto tempo ha dedicato al suo problema di salute o alle sue conseguenze?"),
    ("D6.5", "6", "Quanto è stato coinvolto emotivamente dal suo problema di salute?"),
    ("D6.6", "6", "Quanto la sua salute ha prosciugato le risorse economiche sue o della sua famiglia?"),
    ("D6.7", "6", "Quanti problemi ha avuto la sua famiglia a causa dei suoi problemi di salute?"),
    ("D6.8", "6", "Quanti problemi ha avuto nel fare da solo qualcosa per svagarsi o per piacere?"),
]

ITEM_TESTO = {codice: testo for codice, _dom, testo in ITEMS}
ITEM_DOMINIO = {codice: dom for codice, dom, _t in ITEMS}

def items_del_dominio(dominio):
    return [(c, t) for c, d, t in ITEMS if d == dominio]

ITEM_LAVORO_SCUOLA = ["D5.5", "D5.6", "D5.7", "D5.8"]
ITEM_BASE_32 = [c for c, _d, _t in ITEMS if c not in ITEM_LAVORO_SCUOLA]

# Testi delle domande accessorie (non entrano nel punteggio)
DOMANDE_ACCESSORIE = {
    "D5.01": "Negli ultimi 30 giorni, per quanti giorni ha ridotto o non è riuscito del tutto a svolgere le attività relative alla cura della casa e della famiglia a causa delle sue condizioni di salute?",
    "D5.9": "Ha dovuto ridurre l'attività lavorativa/scolastica a causa delle sue condizioni di salute?",
    "D5.10": "Ha guadagnato di meno a causa delle sue condizioni di salute?",
    "D5.02": "Negli ultimi 30 giorni, per quanti giorni non ha lavorato o non ha frequentato la scuola/università, per mezza giornata o più a causa delle sue condizioni di salute?",
    "H1": "Complessivamente, negli ultimi 30 giorni, per quanti giorni ha avuto queste difficoltà?",
    "H2": "Negli ultimi 30 giorni, per quanti giorni è stato impossibilitato a svolgere le attività o il lavoro abituali a causa delle sue condizioni di salute?",
    "H3": "Negli ultimi 30 giorni, senza contare i giorni in cui è stato impossibilitato, per quanti giorni ha diminuito o ridotto le attività o il lavoro abituali a causa delle sue condizioni di salute?",
}

# --------------------------------------------------------------------------- #
# Punteggio complesso (IRT) — Capitolo 8 del manuale
# Due schemi di ricodifica: "lineare" 0-1-2-3-4 e "compresso" 0-1-1-2-2
# --------------------------------------------------------------------------- #

_RIC_LINEARE = {1: 0, 2: 1, 3: 2, 4: 3, 5: 4}
_RIC_COMPRESSA = {1: 0, 2: 1, 3: 1, 4: 2, 5: 2}

RICODIFICA_ITEM = {
    "D1.1": _RIC_LINEARE, "D1.2": _RIC_LINEARE, "D1.3": _RIC_LINEARE,
    "D1.4": _RIC_LINEARE, "D1.5": _RIC_COMPRESSA, "D1.6": _RIC_COMPRESSA,

    "D2.1": _RIC_LINEARE, "D2.2": _RIC_COMPRESSA, "D2.3": _RIC_COMPRESSA,
    "D2.4": _RIC_LINEARE, "D2.5": _RIC_LINEARE,

    "D3.1": _RIC_COMPRESSA, "D3.2": _RIC_LINEARE, "D3.3": _RIC_COMPRESSA,
    "D3.4": _RIC_COMPRESSA,

    "D4.1": _RIC_COMPRESSA, "D4.2": _RIC_COMPRESSA, "D4.3": _RIC_COMPRESSA,
    "D4.4": _RIC_LINEARE, "D4.5": _RIC_COMPRESSA,

    "D5.1": _RIC_COMPRESSA, "D5.2": _RIC_COMPRESSA, "D5.3": _RIC_LINEARE,
    "D5.4": _RIC_COMPRESSA,

    "D5.5": _RIC_COMPRESSA, "D5.6": _RIC_LINEARE, "D5.7": _RIC_LINEARE,
    "D5.8": _RIC_LINEARE,

    "D6.1": _RIC_COMPRESSA, "D6.2": _RIC_LINEARE, "D6.3": _RIC_COMPRESSA,
    "D6.4": _RIC_LINEARE, "D6.5": _RIC_LINEARE, "D6.6": _RIC_COMPRESSA,
    "D6.7": _RIC_LINEARE, "D6.8": _RIC_COMPRESSA,
}

# Denominatori del Capitolo 8 (massimo teorico del dominio dopo ricodifica)
DENOMINATORE_DOMINIO = {
    "1": 20,
    "2": 16,
    "3": 10,
    "4": 12,
    "5(1)": 10,
    "5(2)": 14,
    "6": 24,
}

DENOMINATORE_TOTALE_32 = 92    # senza item lavoro/scuola
DENOMINATORE_TOTALE_36 = 106   # con item lavoro/scuola

# Tabella 6.1 — norme di popolazione per il punteggio IRT (36 item)
NORME_POPOLAZIONE = [
    (0, 40.00), (1, 46.83), (2, 52.08), (3, 56.20), (4, 59.58),
    (5, 62.46), (6, 64.94), (7, 67.12), (8, 69.05), (9, 70.78),
    (10, 72.35), (15, 78.42), (20, 82.66), (25, 85.85), (30, 88.35),
    (35, 90.38), (50, 94.69), (70, 98.14), (90, 99.90), (100, 100.00),
]


def percentile_popolazione(punteggio_irt):
    """Percentile di popolazione generale per un punteggio IRT 0-100 (Tabella 6.1),
    con interpolazione lineare fra i valori tabulati."""
    if punteggio_irt is None:
        return None
    x = max(0.0, min(100.0, float(punteggio_irt)))
    for i in range(len(NORME_POPOLAZIONE) - 1):
        x0, y0 = NORME_POPOLAZIONE[i]
        x1, y1 = NORME_POPOLAZIONE[i + 1]
        if x0 <= x <= x1:
            if x1 == x0:
                return y0
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return 100.00


def calcola_punteggi(risposte, lavora_studia=True):
    """
    risposte: dict {codice_item: valore 1-5}
    lavora_studia: se False, il punteggio totale è calcolato su 32 item
                   e il dominio 5(2) non viene prodotto.

    Restituisce un dict con:
      - domini: {dominio: {"semplice_grezzo", "semplice_pct", "irt", "n_item"}}
      - totale: {"semplice_grezzo", "semplice_pct", "irt", "n_item", "percentile"}
      - item_mancanti: lista dei codici non compilati
    """
    attesi = [c for c, _d, _t in ITEMS]
    if not lavora_studia:
        attesi = ITEM_BASE_32

    mancanti = [c for c in attesi if risposte.get(c) is None]

    ris = {}
    for dominio in DOMINI:
        if dominio == "5(2)" and not lavora_studia:
            continue
        codici = [c for c, _t in items_del_dominio(dominio)]
        valori = [risposte.get(c) for c in codici]
        if any(v is None for v in valori):
            ris[dominio] = None
            continue
        n = len(codici)
        grezzo = sum(valori)
        pct_semplice = (grezzo - n) * 100.0 / (4 * n)
        ric = sum(RICODIFICA_ITEM[c][risposte[c]] for c in codici)
        irt = ric * 100.0 / DENOMINATORE_DOMINIO[dominio]
        ris[dominio] = {
            "n_item": n,
            "semplice_grezzo": grezzo,
            "semplice_pct": round(pct_semplice, 1),
            "irt": round(irt, 1),
        }

    totale = None
    if not mancanti:
        codici = attesi
        n = len(codici)
        grezzo = sum(risposte[c] for c in codici)
        pct_semplice = (grezzo - n) * 100.0 / (4 * n)
        ric = sum(RICODIFICA_ITEM[c][risposte[c]] for c in codici)
        den = DENOMINATORE_TOTALE_36 if lavora_studia else DENOMINATORE_TOTALE_32
        irt = ric * 100.0 / den
        totale = {
            "n_item": n,
            "semplice_grezzo": grezzo,
            "semplice_min": n,
            "semplice_max": 5 * n,
            "semplice_pct": round(pct_semplice, 1),
            "irt": round(irt, 1),
            "percentile": round(percentile_popolazione(irt), 1),
        }

    return {"domini": ris, "totale": totale, "item_mancanti": mancanti}


# --------------------------------------------------------------------------- #
# Schema PostgreSQL
# --------------------------------------------------------------------------- #

DDL = """
CREATE TABLE IF NOT EXISTS whodas_somministrazioni (
    id                     BIGSERIAL PRIMARY KEY,
    studio_id              BIGINT NOT NULL,
    paziente_id            BIGINT NOT NULL,
    versione               TEXT NOT NULL DEFAULT '36-intervistatore',
    data_somministrazione  DATE NOT NULL,
    numero_intervista      INTEGER,
    id_intervistato        TEXT,
    id_intervistatore      TEXT,
    situazione_vita        SMALLINT,      -- F5: 1 indipendente, 2 assistito, 3 ricoverato
    sesso                  SMALLINT,      -- A1: 1 femmina, 2 maschio
    eta                    INTEGER,       -- A2
    anni_scuola            INTEGER,       -- A3
    stato_civile           SMALLINT,      -- A4: 1-6
    attivita_lavorativa    SMALLINT,      -- A5: 1-9
    attivita_altro         TEXT,          -- A5 opzione 9
    lavora_studia          BOOLEAN NOT NULL DEFAULT TRUE,
    d5_01_giorni           INTEGER,
    d5_02_giorni           INTEGER,
    d5_9_ridotto           SMALLINT,      -- 1 no, 2 si
    d5_10_guadagnato_meno  SMALLINT,      -- 1 no, 2 si
    h1_giorni              INTEGER,
    h2_giorni              INTEGER,
    h3_giorni              INTEGER,
    note                   TEXT,
    completata             BOOLEAN NOT NULL DEFAULT FALSE,
    creato_il              TIMESTAMPTZ NOT NULL DEFAULT now(),
    aggiornato_il          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_whodas_somm_paziente
    ON whodas_somministrazioni (studio_id, paziente_id, data_somministrazione DESC);

CREATE TABLE IF NOT EXISTS whodas_risposte (
    id                   BIGSERIAL PRIMARY KEY,
    somministrazione_id  BIGINT NOT NULL
        REFERENCES whodas_somministrazioni(id) ON DELETE CASCADE,
    item_code            TEXT NOT NULL,
    valore               SMALLINT NOT NULL CHECK (valore BETWEEN 1 AND 5),
    UNIQUE (somministrazione_id, item_code)
);

ALTER TABLE whodas_somministrazioni ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS whodas_somm_tenant ON whodas_somministrazioni;
CREATE POLICY whodas_somm_tenant ON whodas_somministrazioni
    USING (studio_id = current_setting('app.studio_id')::BIGINT)
    WITH CHECK (studio_id = current_setting('app.studio_id')::BIGINT);
"""


def crea_schema(conn):
    """Crea tabelle, indici e policy RLS se non esistono."""
    with conn.cursor() as cur:
        cur.execute(DDL)
    conn.commit()


# --------------------------------------------------------------------------- #
# CRUD
# --------------------------------------------------------------------------- #

def salva_somministrazione(conn, studio_id, paziente_id, anagrafica, risposte,
                           accessorie, somministrazione_id=None):
    """
    Inserisce o aggiorna una somministrazione completa (testata + risposte).
    Restituisce l'id della somministrazione.

    anagrafica: dict con data_somministrazione, numero_intervista, id_intervistato,
                id_intervistatore, situazione_vita, sesso, eta, anni_scuola,
                stato_civile, attivita_lavorativa, attivita_altro, lavora_studia, note
    risposte:   dict {codice_item: 1-5}
    accessorie: dict con d5_01_giorni, d5_02_giorni, d5_9_ridotto,
                d5_10_guadagnato_meno, h1_giorni, h2_giorni, h3_giorni
    """
    ora = datetime.now(TZ)
    campi = dict(anagrafica)
    campi.update(accessorie)

    with conn.cursor() as cur:
        if somministrazione_id is None:
            cur.execute(
                """
                INSERT INTO whodas_somministrazioni
                    (studio_id, paziente_id, versione, data_somministrazione,
                     numero_intervista, id_intervistato, id_intervistatore,
                     situazione_vita, sesso, eta, anni_scuola, stato_civile,
                     attivita_lavorativa, attivita_altro, lavora_studia,
                     d5_01_giorni, d5_02_giorni, d5_9_ridotto, d5_10_guadagnato_meno,
                     h1_giorni, h2_giorni, h3_giorni, note, completata,
                     creato_il, aggiornato_il)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    studio_id, paziente_id, VERSIONE,
                    campi.get("data_somministrazione"),
                    campi.get("numero_intervista"),
                    campi.get("id_intervistato"),
                    campi.get("id_intervistatore"),
                    campi.get("situazione_vita"),
                    campi.get("sesso"), campi.get("eta"), campi.get("anni_scuola"),
                    campi.get("stato_civile"), campi.get("attivita_lavorativa"),
                    campi.get("attivita_altro"), campi.get("lavora_studia", True),
                    campi.get("d5_01_giorni"), campi.get("d5_02_giorni"),
                    campi.get("d5_9_ridotto"), campi.get("d5_10_guadagnato_meno"),
                    campi.get("h1_giorni"), campi.get("h2_giorni"), campi.get("h3_giorni"),
                    campi.get("note"), campi.get("completata", False),
                    ora, ora,
                ),
            )
            somministrazione_id = cur.fetchone()[0]
        else:
            cur.execute(
                """
                UPDATE whodas_somministrazioni SET
                    data_somministrazione = %s, numero_intervista = %s,
                    id_intervistato = %s, id_intervistatore = %s,
                    situazione_vita = %s, sesso = %s, eta = %s, anni_scuola = %s,
                    stato_civile = %s, attivita_lavorativa = %s, attivita_altro = %s,
                    lavora_studia = %s, d5_01_giorni = %s, d5_02_giorni = %s,
                    d5_9_ridotto = %s, d5_10_guadagnato_meno = %s,
                    h1_giorni = %s, h2_giorni = %s, h3_giorni = %s,
                    note = %s, completata = %s, aggiornato_il = %s
                WHERE id = %s AND studio_id = %s
                """,
                (
                    campi.get("data_somministrazione"), campi.get("numero_intervista"),
                    campi.get("id_intervistato"), campi.get("id_intervistatore"),
                    campi.get("situazione_vita"), campi.get("sesso"), campi.get("eta"),
                    campi.get("anni_scuola"), campi.get("stato_civile"),
                    campi.get("attivita_lavorativa"), campi.get("attivita_altro"),
                    campi.get("lavora_studia", True),
                    campi.get("d5_01_giorni"), campi.get("d5_02_giorni"),
                    campi.get("d5_9_ridotto"), campi.get("d5_10_guadagnato_meno"),
                    campi.get("h1_giorni"), campi.get("h2_giorni"), campi.get("h3_giorni"),
                    campi.get("note"), campi.get("completata", False), ora,
                    somministrazione_id, studio_id,
                ),
            )

        for codice, valore in risposte.items():
            if valore is None:
                continue
            cur.execute(
                """
                INSERT INTO whodas_risposte (somministrazione_id, item_code, valore)
                VALUES (%s, %s, %s)
                ON CONFLICT (somministrazione_id, item_code)
                DO UPDATE SET valore = EXCLUDED.valore
                """,
                (somministrazione_id, codice, int(valore)),
            )

    conn.commit()
    return somministrazione_id


def carica_somministrazione(conn, studio_id, somministrazione_id):
    """Restituisce (testata_dict, risposte_dict) oppure (None, {})."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, paziente_id, versione, data_somministrazione, numero_intervista,
                   id_intervistato, id_intervistatore, situazione_vita, sesso, eta,
                   anni_scuola, stato_civile, attivita_lavorativa, attivita_altro,
                   lavora_studia, d5_01_giorni, d5_02_giorni, d5_9_ridotto,
                   d5_10_guadagnato_meno, h1_giorni, h2_giorni, h3_giorni,
                   note, completata, creato_il, aggiornato_il
            FROM whodas_somministrazioni
            WHERE id = %s AND studio_id = %s
            """,
            (somministrazione_id, studio_id),
        )
        riga = cur.fetchone()
        if riga is None:
            return None, {}
        colonne = [d[0] for d in cur.description]
        testata = dict(zip(colonne, riga))

        cur.execute(
            "SELECT item_code, valore FROM whodas_risposte WHERE somministrazione_id = %s",
            (somministrazione_id,),
        )
        risposte = {c: v for c, v in cur.fetchall()}

    return testata, risposte


def lista_somministrazioni(conn, studio_id, paziente_id):
    """Elenco cronologico delle somministrazioni di un paziente."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, data_somministrazione, numero_intervista, lavora_studia, completata
            FROM whodas_somministrazioni
            WHERE studio_id = %s AND paziente_id = %s
            ORDER BY data_somministrazione DESC, id DESC
            """,
            (studio_id, paziente_id),
        )
        colonne = [d[0] for d in cur.description]
        return [dict(zip(colonne, r)) for r in cur.fetchall()]


def elimina_somministrazione(conn, studio_id, somministrazione_id):
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM whodas_somministrazioni WHERE id = %s AND studio_id = %s",
            (somministrazione_id, studio_id),
        )
    conn.commit()


def serie_storica(conn, studio_id, paziente_id):
    """
    Andamento nel tempo: lista di dict {data, punteggi} per ogni somministrazione
    completata del paziente, ordinata cronologicamente. Utile per il confronto pre/post.
    """
    out = []
    for s in reversed(lista_somministrazioni(conn, studio_id, paziente_id)):
        if not s["completata"]:
            continue
        testata, risposte = carica_somministrazione(conn, studio_id, s["id"])
        if testata is None:
            continue
        punteggi = calcola_punteggi(risposte, testata["lavora_studia"])
        out.append({
            "id": s["id"],
            "data": testata["data_somministrazione"],
            "punteggi": punteggi,
        })
    return out
