# Modulo «Studi e ricerca» per il gestionale

## File
- `modules/studi/db_studi.py` — tabelle e funzioni (PostgreSQL, segnaposto %s; le tabelle si creano da sole al primo uso)
- `modules/studi/ui_studi.py` — pagine Streamlit: interna (`render`) e pubblica di iscrizione (`render_iscrizione_pubblica`)
- `modules/studi/pegasis_code.py` — genera il codice «PGS1.» che il partecipante incolla in Pegasis
- `modules/studi/testi_privacy.py` — foglio informativo, informativa privacy, consensi (con versione)
- `tests/test_studi.py` — prove automatiche (`python3 tests/test_studi.py`)

## Collegamento (due righe da aggiungere)
1. **Menu del gestionale** — dove sono le altre voci:
   ```python
   from modules.studi.ui_studi import render as render_studi
   render_studi(get_conn, operatore=utente_corrente)   # usa la funzione di connessione già presente
   ```
2. **Area pubblica** (`apps/pnev_pubblico.py`), all'inizio della pagina:
   ```python
   from modules.studi.ui_studi import render_iscrizione_pubblica
   token = st.query_params.get("studio")
   if token:
       render_iscrizione_pubblica(get_conn, token)
       st.stop()
   ```
   Il link da mandare al gruppo è mostrato nella scheda «Iscrizione» dello studio.

## Privacy
- Nomi e contatti in `studi_identita`; dati di ricerca in `studi_partecipanti` e `studi_dati`, legati solo al codice.
- Ogni iscrizione registra data, versione dei testi e consensi; ogni operazione finisce in `studi_registro`.
- Il ritiro cancella dati di ricerca e anagrafica (resta solo la traccia del ritiro).
- Se il gestionale usa la sicurezza per riga (RLS) per studio, aggiungere alle tabelle la colonna e la regola come negli altri moduli.
