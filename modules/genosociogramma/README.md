# Modulo genosociogramma

Genosociogramma (Schützenberger) per paziente: persone su più generazioni, unioni, legami affettivi, mappa disegnata automaticamente, ripetizioni da esplorare, PDF con carta intestata, riassunto per il diario clinico.

## File

| File | Contenuto |
| --- | --- |
| `db_genosociogramma.py` | Schema PostgreSQL (4 tabelle `geno_*`), RLS su `studio_id`, funzioni CRUD |
| `render_genosociogramma.py` | Impaginazione per generazioni, SVG, ripetizioni, testo per il diario (nessuna dipendenza da Streamlit) |
| `pdf_genosociogramma.py` | Report ReportLab: mappa in orizzontale, ripetizioni, elenco persone, note |
| `ui_genosociogramma.py` | Interfaccia Streamlit a schede: Mappa, Persone, Unioni, Legami, Ripetizioni, A casa, Esporta; editor condivisi con la pagina pubblica |
| `../../pages/genosociogramma_pubblico.py` | Pagina pubblica (senza login) dove il paziente compila da casa con il link |

## Integrazione nel gestionale (branch `test`)

Già agganciato: voce «🌳 Genosociogramma» in Pazienti → Scheda clinica, subito dopo Colloqui clinici.

- `modules/app_menu.py`: aggiunta la voce nel ramo «📁 Scheda clinica».
- `modules/app_main_router.py`: voce aggiunta a `VOCI_CON_PAZIENTE` e al gruppo Rilievi / Colloqui / Alimentazione, che chiama `render_genosociogramma_router(conn, paz_id)`.

Convenzioni seguite (come PECS):

- Tenant da `app.current_studio`, impostato sulla connessione in `app_core`; RLS con `FORCE` e `NULLIF(current_setting('app.current_studio', true), '')`.
- Tabelle create al primo accesso da `ensure_schema()` (idempotente).
- PDF in A4 verticale con `draw_intestazione` e `draw_footer` di `modules/pdf_templates.py`.
- Diario: `registra_voce_diario(conn, studio_id, paz_id, "valutazione", "genosociogramma", <id>, ...)`; ripremendo il pulsante la voce si aggiorna, non si duplica.

## Date

Le date si inseriscono come anno (`1952`) o giorno/mese/anno (`12/03/1952`). Con la data completa il modulo trova anche le coincidenze di giorno e mese; l'età mostrata dentro la figura è quella attuale o quella alla morte.

## Compilazione a casa

Scheda «A casa» del modulo:

- **Link online:** «Crea link per il paziente» crea un genosociogramma vuoto «Compilato dal paziente — data» e un link `…/genosociogramma_pubblico?t=<token>` valido N giorni (default 14), con pulsante WhatsApp. Il paziente accetta il consenso (nome e spunta), compila vedendo il disegno, può tornare sul link più volte e alla fine preme «Invia allo studio»; da quel momento il link non permette più modifiche e arriva una email allo studio. Il token si vede una sola volta: in `geno_link` c'è solo il suo hash (HMAC con `public_links.TOKEN_SECRET`).
- **Scheda cartacea:** PDF da stampare con istruzioni, simboli, area per il disegno, tabella di 24 persone e spazio per il racconto.

`geno_link` non ha RLS (come `questionari_links`): la pagina pubblica deve leggerlo prima di sapere lo studio. Contiene solo id e hash, nessun dato clinico. Dopo la verifica la pagina imposta `studio_id` in sessione e usa la connessione di quello studio, quindi le altre tabelle restano protette da RLS.
