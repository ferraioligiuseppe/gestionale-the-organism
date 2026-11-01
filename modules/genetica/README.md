# Modulo Genetica PNEV (`modules/genetica/`)

Confronta il profilo PNEV di un paziente con le **8.512 sindromi genetiche** della Human Phenotype Ontology (HPO) e restituisce una classifica di somiglianza. È il «livello 2 e 3» descritto nell'*Atlante PNEV delle sindromi genetiche*.

> Strumento di **orientamento all'invio al genetista**. Non ha valore diagnostico.

## File

| File | Contenuto |
|---|---|
| `engine_genetica.py` | Motore di calcolo: somiglianza HPO (Resnik pesato per frequenza, nelle due direzioni), penalità per i segni assenti, p empirico, apprendimento bayesiano dai casi confermati |
| `db_genetica.py` | Tabelle PostgreSQL `genetica_profilo`, `genetica_esito`, `genetica_analisi` e relative funzioni |
| `ui_genetica.py` | Interfaccia Streamlit in 4 schede: Segni PNEV · Altri segni HPO · Analisi · Esiti genetici |
| `ponte_pnev.py` | Tabella ponte: 79 reperti PNEV → codici HPO (la stessa dell'Atlante) |
| `data/hpo_genetica.json.gz` | Dati HPO compressi (1,1 MB): 19.178 termini, 8.512 sindromi |
| `../../apps/demo_genetica.py` | Demo autonoma, senza database |

## Installazione (via GitHub web, branch `main`)

1. Carica la cartella `modules/genetica/` nel repo, compresa la sottocartella `data/`.
2. Se `modules/__init__.py` non c'è già, caricalo (anche vuoto).
3. Controlla che `requirements.txt` contenga `numpy` e `pandas`; di solito ci sono già.
4. Nella pagina del paziente aggiungi:

```python
from modules.genetica.ui_genetica import render_genetica
render_genetica(conn, paziente_id, paziente_nome, studio_id)
```

Le tabelle vengono create in automatico al primo accesso (`CREATE TABLE IF NOT EXISTS`).

**Multi-tenant / RLS**: le tabelle hanno la colonna `studio_id TEXT`. Allinea tipo e policy alla convenzione degli altri moduli. Trovi un modello in `db_genetica.RLS_TEMPLATE`.

## Come funziona il punteggio

- **IC (contenuto informativo)**: un segno presente in poche sindromi pesa di più. La disabilità intellettiva (oltre 2.000 sindromi) pesa poco; un'aprassia oculomotoria pesa molto.
- **Somiglianza**: per ogni segno del paziente si cerca nella sindrome il termine comune più informativo, pesato per la frequenza del segno nella sindrome (70%). A questo si aggiunge quanto il paziente ha i segni tipici della sindrome (30%).
- **Segni assenti**: penalizzano le sindromi in cui quel segno è frequente.
- **Informatività del profilo**: somma degli IC dei segni presenti. Sotto 8 è bassa, tra 8 e 16 è media, sopra 16 è alta.
- **p\***: confronto con 300 profili casuali della stessa dimensione. Non è corretto per i confronti multipli: è un'indicazione, non una prova.

### Apprendimento (livello 3)

Le diagnosi genetiche registrate come **confermate** e con **consenso alla ricerca** aggiornano le frequenze dei segni con una media bayesiana:

`f_post = (f_letteratura × 5 + casi con il segno) / (5 + casi totali)`

In questo modo i segni PNEV (convergenza, RTAC, stereopsi…), che la letteratura genetica quasi non descrive, entrano nel modello man mano che si raccolgono casi. Il paziente in analisi non viene mai usato per «insegnare» a sé stesso.

## Test eseguiti

- Profili costruiti con i 5–6 segni più caratteristici: Williams-Beuren, Floating-Harbor, Rett e Sotos risultano **al 1° posto**, MED13L al 2°. Williams resta 1° anche con 2 segni estranei aggiunti come «rumore».
- Apprendimento: con 3 casi simulati di MED13L con segni PNEV, MED13L sale tra i primi 3 per un profilo PNEV che prima non la individuava.
- Database: creazione delle tabelle, inserimento e aggiornamento dei segni, esiti, casi confermati e storico, testati su PostgreSQL 16.
- Interfaccia: testata nel browser in modalità database e in modalità demo.

## Aggiornare i dati HPO

L'HPO esce con nuove versioni circa ogni 2 mesi. Gli script `prep_hpo.py` e poi `export_data.py` (file sorgente nella cartella `hpo_sorgenti/`) rigenerano `hpo_genetica.json.gz` dai file ufficiali `hp.json`, `phenotype.hpoa`, `genes_to_disease.txt` e dalla traduzione italiana.

## Normativa

- Finché non è certificato, il modulo va presentato come **supporto all'invio e alla ricerca**, non come software diagnostico (Regolamento UE 2017/745, MDR).
- Dati sanitari e genetici: GDPR art. 9. Per l'apprendimento servono consenso specifico e pseudonimizzazione.

Fonte dei dati: Human Phenotype Ontology (hpo.jax.org), release 2026-09-01. Gargano MA et al., *Nucleic Acids Res* 2024.
