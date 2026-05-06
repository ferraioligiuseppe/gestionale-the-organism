# -*- coding: utf-8 -*-
"""
modules/consensi_costellazioni/seeders/costellazioni.py

Seeder dei 4 template di consenso per costellazioni familiari:
1. Individuali (1:1)         → codice: costellazioni_individuali
2. Gruppo                    → codice: costellazioni_gruppo
3. Rappresentante            → codice: costellazioni_rappresentante
4. Registrazione AV          → codice: costellazioni_registrazione

Idempotente: se (codice, versione) esiste, salta.

I testi completi sono nel file:
    docs/consensi_costellazioni.md (sezione DOCUMENTO 1..4)
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# DEFINIZIONE TEMPLATE
# =============================================================================

TEMPLATE_INDIVIDUALI = {
    "codice": "costellazioni_individuali",
    "versione": "1.0",
    "nome": "Informativa privacy e consenso – Costellazioni familiari individuali (1:1)",
    "sottocategoria": "individuali",
    "voci": [
        {"codice": "B.1", "testo": "Acconsento al trattamento dei miei dati identificativi e amministrativi per le finalità di cui all'informativa.", "obbligatorio": True, "ordine": 1},
        {"codice": "B.2", "testo": "Acconsento espressamente al trattamento di dati di categoria particolare (salute, vita affettiva e sessuale, convinzioni filosofiche/religiose, origine etnica) ai sensi dell'art. 9.2.a GDPR.", "obbligatorio": True, "ordine": 2},
        {"codice": "B.3", "testo": "Prendo atto che, nel corso dell'intervento, condividerò informazioni relative a familiari e terzi, e dichiaro di averli, ove possibile e opportuno, informati di tale possibilità; autorizzo il titolare al trattamento di tali dati per le sole finalità terapeutiche, nei limiti del legittimo interesse.", "obbligatorio": True, "ordine": 3},
        {"codice": "B.4", "testo": "Acconsento alla comunicazione dei dati ai responsabili esterni (commercialista, software gestionale, archiviazione cloud) ove necessario.", "obbligatorio": True, "ordine": 4},
        {"codice": "B.5", "testo": "Acconsento alla conservazione dei miei dati di contatto per finalità di mantenimento del rapporto professionale.", "obbligatorio": False, "ordine": 5},
    ],
    "requisiti": {
        "prerequisiti_codici": [],
        "et_minima_autonomia": 18,
        "implica_codici": []
    },
    "base_giuridica": "Art. 6.1.b (esecuzione contratto), Art. 6.1.c (obblighi di legge), Art. 9.2.a GDPR (consenso esplicito) per dati di categoria particolare; Art. 6.1.f GDPR (legittimo interesse) per dati di terzi familiari.",
    "finalita": "Erogazione di intervento esperienziale-riflessivo di costellazioni familiari individuali (setting 1:1).",
    "periodo_conservazione_anni": 10,
}

TEMPLATE_GRUPPO = {
    "codice": "costellazioni_gruppo",
    "versione": "1.0",
    "nome": "Consenso – Costellazioni familiari di gruppo",
    "sottocategoria": "gruppo",
    "voci": [
        {"codice": "B.1", "testo": "Acconsento a partecipare alle sessioni di costellazioni familiari di gruppo presso lo Studio, alle condizioni descritte.", "obbligatorio": True, "ordine": 1},
        {"codice": "B.2", "testo": "Sono consapevole che, portando il mio caso, dati personali e familiari saranno condivisi con gli altri partecipanti, e accetto tale condizione come parte costitutiva del lavoro.", "obbligatorio": True, "ordine": 2},
        {"codice": "B.3", "testo": "Mi impegno al rispetto del patto di riservatezza verso tutti gli altri partecipanti, anche dopo la conclusione del gruppo.", "obbligatorio": True, "ordine": 3},
        {"codice": "B.4", "testo": "Sono consapevole che il titolare del trattamento non risponde di eventuali violazioni del patto da parte di altri partecipanti, fermi restando i loro obblighi di legge.", "obbligatorio": True, "ordine": 4},
    ],
    "requisiti": {
        "prerequisiti_codici": ["costellazioni_individuali"],
        "et_minima_autonomia": 18,
        "implica_codici": []
    },
    "base_giuridica": "Art. 6.1.b GDPR (esecuzione contratto), Art. 9.2.a GDPR (consenso esplicito) per dati di categoria particolare condivisi nel setting gruppale.",
    "finalita": "Partecipazione a sessioni di costellazioni familiari in setting di gruppo, con esposizione consapevole dei propri dati ad altri partecipanti.",
    "periodo_conservazione_anni": 10,
}

TEMPLATE_RAPPRESENTANTE = {
    "codice": "costellazioni_rappresentante",
    "versione": "1.0",
    "nome": "Consenso al ruolo di rappresentante",
    "sottocategoria": "rappresentante",
    "voci": [
        {"codice": "C.1", "testo": "Acconsento a essere chiamato/a a fungere da rappresentante nei lavori di altri partecipanti, ferma restando la mia facoltà di rifiutare di volta in volta.", "obbligatorio": True, "ordine": 1},
        {"codice": "C.2", "testo": "Mi impegno al patto di riservatezza assoluta sui dati e sui contenuti di cui verrò a conoscenza in tale ruolo.", "obbligatorio": True, "ordine": 2},
        {"codice": "C.3", "testo": "Acconsento al trattamento, da parte del titolare, dei dati che potrò conferire durante il ruolo (sensazioni, percezioni riportate), per le sole finalità del processo gruppale.", "obbligatorio": True, "ordine": 3},
    ],
    "requisiti": {
        "prerequisiti_codici": ["costellazioni_gruppo"],
        "et_minima_autonomia": 18,
        "implica_codici": []
    },
    "base_giuridica": "Art. 6.1.a GDPR (consenso) per la partecipazione al ruolo di rappresentante; Art. 9.2.a GDPR per i contenuti emozionali/percettivi conferiti.",
    "finalita": "Partecipazione, su invito del conduttore, in qualità di rappresentante di figure del sistema familiare di altri partecipanti.",
    "periodo_conservazione_anni": 10,
}

TEMPLATE_REGISTRAZIONE = {
    "codice": "costellazioni_registrazione",
    "versione": "1.0",
    "nome": "Consenso alla registrazione audio/video/fotografica",
    "sottocategoria": "registrazione",
    "voci": [
        {"codice": "B.1", "testo": "Acconsento alla registrazione audio della/e sessione/i.", "obbligatorio": False, "ordine": 1},
        {"codice": "B.2", "testo": "Acconsento alla registrazione video della/e sessione/i.", "obbligatorio": False, "ordine": 2},
        {"codice": "B.3", "testo": "Acconsento alla realizzazione di fotografie durante la/e sessione/i.", "obbligatorio": False, "ordine": 3},
        {"codice": "B.4", "testo": "Acconsento all'uso del materiale per le finalità barrate (supervisione, formazione, divulgazione, uso personale).", "obbligatorio": False, "ordine": 4},
        {"codice": "B.5", "testo": "Acconsento all'uso del materiale in forma anonimizzata in contesti formativi/divulgativi.", "obbligatorio": False, "ordine": 5},
        {"codice": "B.6", "testo": "Acconsento all'uso del materiale in forma riconoscibile (sconsigliato; richiede valutazione caso per caso).", "obbligatorio": False, "ordine": 6},
    ],
    "requisiti": {
        "prerequisiti_codici": ["costellazioni_individuali"],
        "et_minima_autonomia": 18,
        "implica_codici": [],
        "note_speciali": "Tutte le voci sono opzionali. Almeno una tra B.1, B.2, B.3 deve essere TRUE perché il consenso abbia significato; in caso contrario il record è di rifiuto totale."
    },
    "base_giuridica": "Art. 6.1.a GDPR (consenso esplicito), Art. 9.2.a GDPR per il trattamento di immagini/voce qualificabili come dati biometrici e di categoria particolare.",
    "finalita": "Registrazione di sessioni per supervisione, formazione, divulgazione anonimizzata o uso personale del partecipante.",
    "periodo_conservazione_anni": 5,
}


TUTTI_I_TEMPLATE = [
    TEMPLATE_INDIVIDUALI,
    TEMPLATE_GRUPPO,
    TEMPLATE_RAPPRESENTANTE,
    TEMPLATE_REGISTRAZIONE,
]


# =============================================================================
# CARICAMENTO TESTI MD
# =============================================================================

def _carica_testo_md(percorso: str, sottocategoria: str) -> str:
    """
    Estrae il testo del documento per la sottocategoria specificata
    dal file unico docs/consensi_costellazioni.md.

    I documenti sono delimitati da marker '# DOCUMENTO N'.
    """
    map_sottocat = {
        "individuali":     "DOCUMENTO 1",
        "gruppo":          "DOCUMENTO 2",
        "rappresentante":  "DOCUMENTO 3",
        "registrazione":   "DOCUMENTO 4",
    }
    marker = map_sottocat[sottocategoria]

    with open(percorso, "r", encoding="utf-8") as f:
        contenuto = f.read()

    parti = contenuto.split(f"# {marker}")
    if len(parti) < 2:
        raise ValueError(f"Sezione '{marker}' non trovata in {percorso}")

    testo = parti[1]
    # Tronca al successivo "# DOCUMENTO" se presente
    for n in range(1, 10):
        nxt = f"# DOCUMENTO {n}"
        if nxt == f"# {marker}":
            continue
        if nxt in testo:
            testo = testo.split(nxt)[0]
            break

    return testo.strip().rstrip("-").strip()


# =============================================================================
# SEEDING
# =============================================================================

def _is_postgres(conn: Any) -> bool:
    """Heuristic: il wrapper _PgConn del gestionale ha attributo ._conn (psycopg2)."""
    return hasattr(conn, "_conn") or "psycopg" in str(type(conn)).lower()


def _placeholder(conn: Any) -> str:
    """Restituisce il placeholder corretto per il backend del gestionale."""
    return "%s" if _is_postgres(conn) else "?"


def seed_template(
    conn: Any,
    percorso_md: Optional[str] = None,
    sovrascrivi: bool = False,
) -> dict:
    """
    Carica i 4 template costellazioni nel DB.

    Args:
        conn: connessione DB (Postgres o SQLite)
        percorso_md: path a docs/consensi_costellazioni.md. Se None,
            carica testi placeholder (utile in test).
        sovrascrivi: se True, fa UPDATE su (codice, versione) esistenti.

    Returns:
        {'inserted': N, 'skipped': N, 'updated': N}
    """
    cur = conn.cursor()
    risultati = {"inserted": 0, "skipped": 0, "updated": 0}
    ph = _placeholder(conn)
    is_pg = _is_postgres(conn)

    try:
        for tpl in TUTTI_I_TEMPLATE:
            codice = tpl["codice"]
            versione = tpl["versione"]
            sottocat = tpl["sottocategoria"]

            if percorso_md and os.path.exists(percorso_md):
                testo_md = _carica_testo_md(percorso_md, sottocat)
            else:
                testo_md = (
                    f"[TESTO PLACEHOLDER per {codice} v{versione} - "
                    "ricaricare seeder con percorso_md valido]"
                )

            # Verifica esistenza
            cur.execute(
                f"SELECT id FROM cf_template WHERE codice = {ph} AND versione = {ph}",
                (codice, versione),
            )
            row = cur.fetchone()
            esistente_id = row[0] if row else None

            if esistente_id and not sovrascrivi:
                logger.info(f"Skip {codice} v{versione} (già presente, id={esistente_id})")
                risultati["skipped"] += 1
                continue

            voci_json = json.dumps(tpl["voci"], ensure_ascii=False)
            req_json  = json.dumps(tpl["requisiti"], ensure_ascii=False)

            if esistente_id and sovrascrivi:
                if is_pg:
                    cur.execute(
                        f"""
                        UPDATE cf_template SET
                            nome = {ph},
                            sottocategoria = {ph},
                            testo_md = {ph},
                            voci = {ph}::jsonb,
                            requisiti = {ph}::jsonb,
                            base_giuridica = {ph},
                            finalita = {ph},
                            periodo_conservazione_anni = {ph}
                        WHERE id = {ph}
                        """,
                        (tpl["nome"], sottocat, testo_md, voci_json, req_json,
                         tpl["base_giuridica"], tpl["finalita"],
                         tpl["periodo_conservazione_anni"], esistente_id),
                    )
                else:
                    cur.execute(
                        f"""
                        UPDATE cf_template SET
                            nome = {ph},
                            sottocategoria = {ph},
                            testo_md = {ph},
                            voci = {ph},
                            requisiti = {ph},
                            base_giuridica = {ph},
                            finalita = {ph},
                            periodo_conservazione_anni = {ph}
                        WHERE id = {ph}
                        """,
                        (tpl["nome"], sottocat, testo_md, voci_json, req_json,
                         tpl["base_giuridica"], tpl["finalita"],
                         tpl["periodo_conservazione_anni"], esistente_id),
                    )
                risultati["updated"] += 1
                logger.info(f"Updated {codice} v{versione}")
            else:
                if is_pg:
                    cur.execute(
                        f"""
                        INSERT INTO cf_template (
                            codice, versione, nome, sottocategoria, testo_md,
                            voci, requisiti, base_giuridica, finalita,
                            periodo_conservazione_anni, attivo
                        ) VALUES (
                            {ph}, {ph}, {ph}, {ph}, {ph},
                            {ph}::jsonb, {ph}::jsonb, {ph}, {ph},
                            {ph}, TRUE
                        )
                        """,
                        (codice, versione, tpl["nome"], sottocat, testo_md,
                         voci_json, req_json, tpl["base_giuridica"],
                         tpl["finalita"], tpl["periodo_conservazione_anni"]),
                    )
                else:
                    cur.execute(
                        f"""
                        INSERT INTO cf_template (
                            codice, versione, nome, sottocategoria, testo_md,
                            voci, requisiti, base_giuridica, finalita,
                            periodo_conservazione_anni, attivo
                        ) VALUES (
                            {ph}, {ph}, {ph}, {ph}, {ph},
                            {ph}, {ph}, {ph}, {ph}, {ph}, 1
                        )
                        """,
                        (codice, versione, tpl["nome"], sottocat, testo_md,
                         voci_json, req_json, tpl["base_giuridica"],
                         tpl["finalita"], tpl["periodo_conservazione_anni"]),
                    )
                risultati["inserted"] += 1
                logger.info(f"Inserted {codice} v{versione}")

        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            cur.close()
        except Exception:
            pass

    return risultati


def seed_hook():
    """
    Hook utilizzabile da app_core.py o da uno script di setup.

    Esempio:
        from modules.consensi_costellazioni.seeders.costellazioni import seed_hook
        seed_hook()
    """
    try:
        from modules.app_core import get_connection
    except ImportError:
        logger.warning("Impossibile importare modules.app_core; skip seed.")
        return

    conn = get_connection()
    # Path canonico del file md nel repo
    candidati = [
        "docs/consensi_costellazioni.md",
        "modules/consensi_costellazioni/docs/consensi_costellazioni.md",
    ]
    percorso = None
    for c in candidati:
        if os.path.exists(c):
            percorso = c
            break

    risultati = seed_template(conn, percorso_md=percorso, sovrascrivi=False)
    logger.info(f"Seed costellazioni: {risultati}")
    return risultati
