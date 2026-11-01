# Modulo Laboratorio PNEV (`modules/laboratorio/`)

Sezione sperimentale: A visore binoculare, B suono e sonno, C memoria iconica, D ritmo theta.
Le prove girano nella pagina HTML; il gestionale salva i risultati nella scheda del paziente e ne mostra l'andamento.

## File

| File | A cosa serve |
| --- | --- |
| `db_laboratorio.py` | Tabella `lab_risultati`, decodifica del codice, salvataggio, elenco, eliminazione |
| `ui_laboratorio.py` | Pagina Streamlit: risultato in arrivo, codice incollato, andamento, storico |
| `sql/001_lab_risultati.sql` | Creazione tabella + modello di policy RLS |
| `static/laboratorio-pnev.html` | La pagina del Laboratorio da pubblicare su pnev.it (file unico, funziona anche offline, tranne i font) |

## Come si collega (5 passi su GitHub, branch `main`)

1. Carica la cartella `modules/laboratorio/` nel repository `gestionale-the-organism`.
2. Esegui `sql/001_lab_risultati.sql` sul database OVH e copia la tua policy RLS (le righe segnate **ADATTA**).
3. Nel file principale dell'app, **prima del login**, aggiungi:

   ```python
   from modules.laboratorio.ui_laboratorio import cattura_codice_da_url
   cattura_codice_da_url()
   ```

   Così il risultato che arriva dal link non si perde durante l'accesso.
4. Nella scheda del paziente aggiungi una voce di menu che chiama:

   ```python
   from modules.laboratorio.ui_laboratorio import render_laboratorio
   render_laboratorio(conn, paziente_id=paziente_id, studio_id=studio_id)
   ```

5. In `ui_laboratorio.py` imposta `LAB_URL` con l'indirizzo dove pubblichi la pagina (es. `https://www.pnev.it/laboratorio/`).

## Come si usa

1. Nel Laboratorio scrivi nel campo «Codice paziente» l'**ID del paziente nel gestionale** e, una volta sola, l'indirizzo della pagina Laboratorio del gestionale.
2. Fai la prova. Nel Registro compare «Invia al gestionale».
3. Il link apre il gestionale con il risultato pronto: controlli il paziente e premi **Salva nella scheda**.
4. Senza collegamento (es. visore senza rete): «Copia codice» e lo incolli nel gestionale, sezione «Incolla un codice».

Lo stesso risultato non può essere salvato due volte (impronta univoca).

## Cosa viene salvato

- **Metriche** (JSONB), seguite nel tempo con un grafico:
  - A: emersione set 1 e set 2, vantaggio in secondi
  - B: effetto della riattivazione in punti percentuali
  - C: lettere disponibili subito, resoconto totale
  - D: d′ ritmico e d′ irregolare
- **Prove** (JSONB): il dettaglio di ogni prova, fino a 120.
- Seduta, operatore, parametri, data di esecuzione.

Nessun dato passa da servizi esterni: il codice viaggia solo dentro il link tra la pagina e il tuo gestionale.

## Stato

Modulo **sperimentale**: da tenere fuori dalla versione commerciale finché i protocolli non sono stabili.
