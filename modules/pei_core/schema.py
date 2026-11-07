"""
pei_core.schema — struttura dati di PEI, PDF, DF e PF.

Fonti:
  - PEI: modello nazionale D.I. 182/2020 come modificato dal D.I. 153/2023
    (Allegato A4, secondaria di II grado), verificato sugli articoli 5-16
    del testo coordinato. Ad ogni aggiornamento ministeriale ricontrollare
    e incrementare SCHEMA_VERSION.
  - PDF (Profilo Dinamico Funzionale): assi del D.P.R. 24/02/1994.
    Formalmente assorbito dal Profilo di Funzionamento (D.Lgs. 66/2017),
    ma ancora in uso finché il PF non è disponibile.

Ogni campo: (chiave, etichetta, tipo, opzioni)
tipi: text | textarea | select | multiselect | date | checkbox | number | tabella
(tabella: opzioni = elenco colonne {"key","label","tipo","opzioni"})
"""

SCHEMA_VERSION = "2026.4"   # 2026.3: profilo ICF-CY · 2026.4: relazione di funzionamento ICF-CY

TIPI_DOCUMENTO = {
    "PEI": "Piano Educativo Individualizzato",
    "PDF": "Profilo Dinamico Funzionale",
    "DF":  "Diagnosi Funzionale",
    "PF":  "Profilo di Funzionamento",
    "RICF": "Relazione di funzionamento ICF-CY",
}
# tipi mostrati di default; gli altri solo se l'app li chiede (tipi_extra)
TIPI_BASE = ["PEI", "PDF", "DF", "PF"]

GRADI = ["infanzia", "primaria", "secondaria_I", "secondaria_II"]


def F(key, label, tipo="textarea", opzioni=None):
    return {"key": key, "label": label, "tipo": tipo, "opzioni": opzioni or []}


from .icf import (CAMPO_CONTESTO, CAMPO_FUNZIONAMENTO, COLONNE_CONTESTO,  # noqa: E402
                  COLONNE_FUNZIONAMENTO)

CAMPO_ICF_FUNZ = F(CAMPO_FUNZIONAMENTO, "Profilo ICF-CY: funzioni, strutture, attività e partecipazione",
                   "tabella", COLONNE_FUNZIONAMENTO)
CAMPO_ICF_CONT = F(CAMPO_CONTESTO, "Profilo ICF-CY: fattori ambientali (barriere e facilitatori)",
                   "tabella", COLONNE_CONTESTO)
SEZIONE_ICF = {"id": "icf", "titolo": "Profilo ICF-CY (OMS 2007)",
               "campi": [CAMPO_ICF_FUNZ, CAMPO_ICF_CONT]}


# --------------------------------------------------------------------------
# PROFILO DINAMICO FUNZIONALE — 9 assi, ciascuno con livello attuale e
# potenzialità di sviluppo (breve / medio termine)
# --------------------------------------------------------------------------
ASSI_PDF = [
    ("cognitivo", "Asse cognitivo"),
    ("affettivo_relazionale", "Asse affettivo-relazionale"),
    ("comunicazionale", "Asse comunicazionale"),
    ("linguistico", "Asse linguistico"),
    ("sensoriale", "Asse sensoriale"),
    ("motorio_prassico", "Asse motorio-prassico"),
    ("neuropsicologico", "Asse neuropsicologico"),
    ("autonomia", "Asse dell'autonomia"),
    ("apprendimento", "Asse dell'apprendimento"),
]

SCHEMA_PDF = [
    {"id": "intestazione", "titolo": "Dati generali", "campi": [
        F("soggetto", "Alunno (nome o codice)", "text"),
        F("scuola", "Istituto e classe", "text"),
        F("anno_scolastico", "Anno scolastico", "text"),
        F("data_redazione", "Data di redazione", "date"),
        F("df_riferimento", "Diagnosi Funzionale di riferimento (ente e data)", "text"),
        F("redattori", "Redatto da (GLO / componenti)", "textarea"),
    ]},
] + [
    {"id": f"asse_{k}", "titolo": t, "campi": [
        F(f"{k}_attuale", "Livello di sviluppo attuale"),
        F(f"{k}_breve", "Potenzialità di sviluppo — breve termine (6 mesi)"),
        F(f"{k}_medio", "Potenzialità di sviluppo — medio termine (2 anni)"),
    ]} for k, t in ASSI_PDF
] + [SEZIONE_ICF] + [
    {"id": "sintesi", "titolo": "Sintesi e note", "campi": [
        F("sintesi", "Sintesi complessiva del funzionamento"),
        F("note", "Note"),
    ]},
]

# --------------------------------------------------------------------------
# PEI — modello nazionale, secondaria di II grado
# --------------------------------------------------------------------------
DIMENSIONI_PEI = [
    ("relazione", "A. Dimensione della relazione, dell'interazione e della socializzazione"),
    ("comunicazione", "B. Dimensione della comunicazione e del linguaggio"),
    ("autonomia", "C. Dimensione dell'autonomia e dell'orientamento"),
    ("cognitiva", "D. Dimensione cognitiva, neuropsicologica e dell'apprendimento"),
]

# Art. 8 c.2 D.I. 182/2020: quali assi del PDF confluiscono in ogni dimensione
ASSI_PER_DIMENSIONE = {
    "relazione": ["affettivo_relazionale"],
    "comunicazione": ["comunicazionale", "linguistico"],
    "autonomia": ["autonomia", "motorio_prassico", "sensoriale"],
    "cognitiva": ["cognitivo", "neuropsicologico", "apprendimento"],
}

# Art. 10 c.2 (secondaria II grado: niente esonero dopo il D.I. 153/2023)
OPZIONI_DISCIPLINA = [
    "A - segue la progettazione della classe",
    "B - personalizzata, verifiche identiche o equipollenti",
    "C - differenziata, verifiche non equipollenti",
]
# Art. 10 c.3
PERCORSI = ["ordinario", "personalizzato (con prove equipollenti)", "differenziato"]
ENTITA_DIFFICOLTA = ["assente", "lieve", "media", "elevata", "molto elevata"]
DOMINI = [("cognitiva", "Apprendimento"), ("comunicazione", "Comunicazione"),
          ("relazione", "Relazioni e socializzazione"),
          ("autonomia", "Autonomia personale e sociale")]

SCHEMA_PEI = [
    {"id": "frontespizio", "titolo": "Intestazione e composizione del GLO", "campi": [
        F("soggetto", "Studente (nome o codice)", "text"),
        F("scuola", "Istituto, indirizzo di studi e classe", "text"),
        F("anno_scolastico", "Anno scolastico", "text"),
        F("tipo_pei", "Tipo di PEI", "select", ["definitivo", "provvisorio (entro il 30 giugno)"]),
        F("accertamento", "Verbale di accertamento della condizione di disabilità (data, scadenza)", "text"),
        F("pf_disponibile", "Profilo di Funzionamento disponibile", "checkbox"),
        F("pf_data", "Profilo di Funzionamento: data di redazione", "text"),
        F("df_riferimento", "Se PF non disponibile: Diagnosi Funzionale (data) e PDF (data)", "text"),
        F("progetto_individuale", "Progetto Individuale", "select",
          ["redatto", "richiesto e non ancora redatto", "non richiesto"]),
        F("glo", "Composizione del GLO (nome, ruolo)", "tabella", [
            {"key": "nome", "label": "Nome e cognome", "tipo": "text"},
            {"key": "ruolo", "label": "Qualifica / ruolo", "tipo": "text"}]),
        F("data_approvazione", "Data di approvazione e prima sottoscrizione", "date"),
    ]},
    {"id": "s1", "titolo": "1. Quadro informativo", "campi": [
        F("situazione_familiare", "Situazione familiare e descrizione dello studente (a cura dei genitori o componenti esterni del GLO)"),
        F("descrizione_di_se", "Descrizione di sé dello studente (interviste o colloqui)"),
    ]},
    {"id": "s2", "titolo": "2. Elementi generali desunti dal Profilo di Funzionamento (o da DF e PDF)", "campi": [
        F("sintesi_profilo", "Sintesi"),
        F("dimensioni_interessate", "Dimensioni per cui è prevista una progettazione specifica", "multiselect",
          [t for _, t in DIMENSIONI_PEI]),
        CAMPO_ICF_FUNZ,
    ]},
    {"id": "s3", "titolo": "3. Raccordo con il Progetto Individuale", "campi": [
        F("raccordo", "Sintesi dei contenuti del Progetto Individuale e modalità di coordinamento con il PEI"),
        F("indicazioni_progetto", "Se richiesto e non redatto: indicazioni utili alla sua redazione"),
    ]},
    {"id": "s4", "titolo": "4. Osservazioni sullo studente per progettare gli interventi di sostegno didattico", "campi": [
        F(f"oss_{k}", t) for k, t in DIMENSIONI_PEI
    ] + [F("revisione_s4", "Revisione (verifica intermedia)")]},
    {"id": "s5", "titolo": "5. Interventi per lo studente: obiettivi educativi e didattici, strumenti, strategie e modalità", "campi": sum([[
        F(f"obiettivi_{k}", f"{t[:2]} Obiettivi ed esiti attesi"),
        F(f"attivita_{k}", f"{t[:2]} Interventi didattici e metodologici: attività"),
        F(f"strategie_{k}", f"{t[:2]} Interventi didattici e metodologici: strategie e strumenti"),
        F(f"verifica_{k}", f"{t[:2]} Verifica: metodi, criteri e strumenti"),
    ] for k, t in DIMENSIONI_PEI], []) + [
        F("revisione_s5", "Revisione (verifica intermedia)"),
        F("verifica_conclusiva_s5", "Verifica conclusiva degli esiti"),
    ]},
    {"id": "s6", "titolo": "6. Osservazioni sul contesto: barriere e facilitatori", "campi": [
        CAMPO_ICF_CONT,
        F("barriere", "Barriere (contesto fisico, organizzativo, relazionale)"),
        F("facilitatori", "Facilitatori"),
        F("indicazioni_studente_contesto", "Indicazioni fornite dallo studente"),
    ]},
    {"id": "s7", "titolo": "7. Interventi sul contesto per realizzare un ambiente di apprendimento inclusivo", "campi": [
        F("interventi_contesto", "Obiettivi didattici, strumenti, strategie e modalità"),
        F("revisione_s7", "Revisione (verifica intermedia)"),
        F("verifica_conclusiva_s7", "Verifica conclusiva degli esiti"),
    ]},
    {"id": "s8", "titolo": "8. Interventi sul percorso curricolare", "campi": [
        F("modalita_sostegno", "8.1 Modalità di sostegno didattico e ulteriori interventi di inclusione"),
        F("modalita_verifica", "8.2 Modalità di verifica (personalizzazioni rispetto alla classe)"),
        F("progettazione_disciplinare", "8.3 Progettazione disciplinare", "tabella", [
            {"key": "disciplina", "label": "Disciplina", "tipo": "text"},
            {"key": "opzione", "label": "Progettazione", "tipo": "select", "opzioni": OPZIONI_DISCIPLINA},
            {"key": "dettaglio", "label": "Obiettivi, risultati attesi e criteri di valutazione (se B o C)", "tipo": "text"}]),
        F("percorso", "Percorso didattico complessivo (art. 10 c.3)", "select", PERCORSI),
        F("pcto_tipologia", "PCTO (dal terzo anno) — tipologia", "select", ["aziendale", "scolastico", "altra tipologia"]),
        F("pcto_progetto", "PCTO — obiettivi di competenza, contesto con barriere e facilitatori, attività e fasi"),
        F("pcto_monitoraggio", "PCTO — indicatori di monitoraggio, rete dei servizi territoriali, osservazioni dello studente"),
        F("comportamento", "Criteri di valutazione del comportamento", "select",
          ["stessi criteri della classe", "criteri personalizzati con obiettivi specifici"]),
        F("comportamento_obiettivi", "Obiettivi specifici sul comportamento (se personalizzati)"),
        F("revisione_s8", "Revisione (verifica intermedia)"),
        F("verifica_conclusiva_s8", "Verifica conclusiva degli esiti"),
    ]},
    {"id": "s9", "titolo": "9. Organizzazione generale del progetto di inclusione e utilizzo delle risorse", "campi": [
        F("orario_presenza", "Presenza a scuola", "select",
          ["intero orario", "assenze continuative per documentate esigenze sanitarie"]),
        F("orario_motivazione", "Se assenze continuative: motivazione e accordi"),
        F("ore_sostegno", "Ore settimanali di sostegno", "number"),
        F("assistenza_base", "Assistenza igienica e di base (collaboratori scolastici)"),
        F("assistenza_specialistica", "Assistenza specialistica all'autonomia e/o alla comunicazione (figura e ore)"),
        F("altre_risorse", "Altre risorse professionali nella scuola o nella classe"),
        F("uscite", "Uscite didattiche, visite guidate e viaggi di istruzione"),
        F("comportamenti_problema", "Strategie di prevenzione e gestione di comportamenti problematici"),
        F("progetti_classe", "Attività o progetti per l'inclusione rivolti alla classe"),
        F("trasporto", "Trasporto scolastico"),
        F("extrascolastico", "Interventi e attività extrascolastiche e raccordi con il PEI"),
    ]},
    {"id": "s10", "titolo": "10. Certificazione delle competenze con eventuali note esplicative", "campi": [
        F("certificazione", "Note esplicative (anche in funzione orientativa)"),
    ]},
    {"id": "s11", "titolo": "11. Verifica finale / proposte per le risorse professionali e i servizi di supporto", "campi": [
        F("verifica_finale", "Verifica finale: valutazione globale dei risultati"),
        F("aggiornamento_contesto", "Aggiornamento delle condizioni di contesto per l'anno successivo"),
        F("debito_funzionamento", "Entità delle difficoltà per dominio (Allegato C — se PF disponibile)", "tabella", [
            {"key": "dominio", "label": "Dominio / dimensione", "tipo": "text"},
            {"key": "entita", "label": "Entità", "tipo": "select", "opzioni": ENTITA_DIFFICOLTA}]),
        F("proposta_ore_sostegno", "Proposta ore di sostegno per l'anno successivo", "number"),
        F("motivazione_ore", "Motivazione della proposta"),
        F("proposta_assistenza", "Proposta assistenza igienica e di base e assistenza specialistica (figura e ore)"),
        F("proposta_trasporto", "Esigenze di trasporto"),
    ]},
    {"id": "s12", "titolo": "12. PEI provvisorio per l'anno scolastico successivo", "campi": [
        F("pei_provvisorio", "Proposte di sostegno didattico e altri supporti"),
        F("provv_ore_sostegno", "Proposta ore di sostegno", "number"),
        F("provv_assistenza", "Proposta assistenza di base e specialistica"),
    ]},
]

# Art. 16 c.3: sezioni prescrittive del PEI provvisorio
SEZIONI_PEI_PROVVISORIO = ["frontespizio", "s1", "s2", "s4", "s6", "s12"]

# DF e PF: per ora si archiviano come allegato + sintesi libera
SCHEMA_ALLEGATO_SEMPLICE = [
    {"id": "dati", "titolo": "Dati del documento", "campi": [
        F("soggetto", "Alunno (nome o codice)", "text"),
        F("ente", "Ente / Unità di valutazione", "text"),
        F("data_redazione", "Data di redazione", "date"),
        F("sintesi", "Sintesi"),
    ]},
]

# PF: redatto secondo l'ICF (D.Lgs. 66/2017 art. 5), quindi con il profilo ICF-CY
SCHEMA_PF = SCHEMA_ALLEGATO_SEMPLICE + [SEZIONE_ICF]

# Relazione di funzionamento ICF-CY: contributo dello studio per famiglia, UVM e GLO.
# Non è il Profilo di Funzionamento (D.Lgs. 66/2017 art. 5), che redige l'UVM dell'ASL.
SCHEMA_RICF = [
    {"id": "dati", "titolo": "Dati generali", "campi": [
        F("soggetto", "Paziente (nome o codice)", "text"),
        F("scuola", "Scuola e classe", "text"),
        F("data_redazione", "Data di redazione", "date"),
        F("redatto_da", "Redatta da", "text"),
        F("motivo", "Motivo della valutazione e richiesta"),
        F("strumenti", "Valutazioni e strumenti utilizzati", "tabella", [
            {"key": "strumento", "label": "Valutazione / strumento", "tipo": "text"},
            {"key": "data", "label": "Data", "tipo": "text"},
            {"key": "esito", "label": "Esito sintetico", "tipo": "text"}]),
    ]},
    SEZIONE_ICF,
    {"id": "sintesi", "titolo": "Sintesi e indicazioni", "campi": [
        F("sintesi", "Sintesi del funzionamento"),
        F("punti_forza", "Punti di forza e risorse"),
        F("indicazioni_scuola", "Indicazioni per la scuola (utili al PEI)"),
        F("indicazioni_famiglia", "Indicazioni per la famiglia"),
        F("percorso", "Percorso proposto dallo studio"),
    ]},
]

NOTE_FINALI = {
    "RICF": ("Relazione redatta dallo studio come contributo alla valutazione. Codifica secondo "
             "ICF-CY (OMS, 2007). Non sostituisce il Profilo di Funzionamento redatto dall'Unità "
             "di valutazione multidisciplinare (D.Lgs. 66/2017, art. 5)."),
}

SCHEMI = {
    "PEI": SCHEMA_PEI,
    "PDF": SCHEMA_PDF,
    "DF": SCHEMA_ALLEGATO_SEMPLICE,
    "PF": SCHEMA_PF,
    "RICF": SCHEMA_RICF,
}


def schema_per(tipo: str):
    if tipo not in SCHEMI:
        raise ValueError(f"Tipo documento sconosciuto: {tipo}")
    return SCHEMI[tipo]


def campi_flat(tipo: str):
    return [c for sez in schema_per(tipo) for c in sez["campi"]]
