# pei_core

Nucleo comune per **PEI, Profilo Dinamico Funzionale (PDF), Diagnosi Funzionale (DF),
Profilo di Funzionamento (PF)** e **allegati PDF**.
Va copiato identico in due repo:

- `gestionale-the-organism` → `modules/pei_core/`
- `tfa-manager` → `pei_core/`

## File
| File | Cosa fa |
|---|---|
| `schema.py` | Sezioni e campi: PEI (12 sezioni, secondaria II grado), PDF (9 assi), DF/PF |
| `model.py` | `Documento`, precompilazione sez. 2 del PEI da PF/PDF/DF, controllo anonimato |
| `pdf_io.py` | Export PDF (ReportLab, verde #1D6B44), validazione PDF caricati, unione PDF |
| `db.py` | Funzioni PostgreSQL (`%s`, JSONB, BYTEA) |
| `schema.sql` | Tabelle `pei_documenti` e `pei_allegati` |
| `ui.py` | Pagina Streamlit completa: `pagina_pei(...)` |

## Requisiti (`requirements.txt`)
```
reportlab
pypdf
psycopg2-binary
streamlit
```

## Installazione
1. Copia la cartella nel repo (via GitHub web: «Add file → Upload files»).
2. Una sola volta: `db.crea_tabelle(conn)`.
3. Nella pagina dell'app:

TFA Manager (anonimato obbligatorio):
```python
from pei_core.ui import pagina_pei
pagina_pei(conn, rif_tipo="corsista", rif_id=utente_id, utente=username,
           anonimo_obbligatorio=True)
```
Gestionale (paziente, carta intestata, RLS):
```python
from modules.pei_core.ui import pagina_pei
pagina_pei(conn, rif_tipo="paziente", rif_id=paziente_id, utente=operatore,
           tenant_id=studio_id, intestazione=disegna_carta_intestata)
```
`intestazione` è una funzione `(canvas, doc)`: usa quella della carta intestata già esistente.

## Note
- Il modello PEI va ricontrollato sul modello ministeriale ufficiale;
  quando cambia, aggiorna `schema.py` e `SCHEMA_VERSION`.
- I vecchi documenti restano leggibili: il contenuto è JSONB, i campi nuovi risultano vuoti.
- Il controllo anonimato segnala CF, telefoni, email, date e nomi propri: avvisa, non corregge.
