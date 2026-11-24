# Matrici di Raven (CPM · SPM) — dove vanno i file

Tutto nello stesso commit, sul branch `main`. Partito dal commit `f8dd7fc`.

## File nuovi

Cartella `modules/raven/` (caricala intera):

- `__init__.py`
- `catalogo_raven.py` — struttura delle due forme (serie, item, alternative), gradi, testi fissi
- `scoring_raven.py` — calcoli e testo della relazione (senza database)
- `db_raven.py` — tabelle `raven_registrazioni` e `raven_tabelle`, create da sole al primo ingresso
- `ui_raven.py` — foglio di inserimento, esito, relazione, scheda «Norme e chiave»
- `pdf_raven.py` — relazione su carta intestata

In `tests/`: `test_raven.py` (36 prove dei calcoli; avvio: `pytest tests/test_raven.py`).

## File modificati (sostituiscono quelli esistenti)

In `modules/`:

- `app_menu.py` — voce «🧩 Matrici di Raven (CPM · SPM)» in Valutazione → Test psicologici
- `app_main_router.py` — apertura del modulo (due punti) e voce tra quelle «con paziente»
- `filtro_eta.py` — la voce compare dai 3 anni
- `cerca_menu.py` — parole per la ricerca (raven, matrici, cpm, spm…)

Se dopo il commit `f8dd7fc` hai cambiato uno di questi quattro file, non sovrascriverlo:
dimmelo e rifaccio la modifica sulla versione nuova.

## Cosa fa

1. **Foglio di inserimento**, tre modi: solo i totali per serie; item per item giusto/sbagliato;
   item per item con l'alternativa scelta (corregge da solo, serve la chiave).
2. **Punteggio**: corrette per serie e totale (CPM 36, SPM 60), item omessi.
3. **Collocazione**: fascia percentile e grado (I … V) per l'età alla data della prova, dalla
   tabella normativa dello studio; oppure dal percentile esatto letto sul manuale.
4. **Composizione**: confronto fra punteggi di serie ottenuti e attesi per quel totale
   (scarto oltre 2 punti = totale da leggere con cautela).
5. **Relazione**: testo già scritto, da correggere a schermo (si salva da solo), poi PDF.
6. Voce automatica nel diario clinico, se il modulo diario è disponibile.

## Tre cose da sapere

1. **Figure, chiave e norme non sono nel codice** (il repository è pubblico e sono materiale
   dell'editore). Si caricano una volta per studio nella scheda «Norme e chiave» e restano nel
   database dello studio. Senza norme il modulo dà punteggio grezzo e relazione descrittiva.
2. **Norme**: una riga per fascia d'età, con il grezzo ai percentili 5, 10, 25, 50, 75, 90, 95.
   Il grado segue lo schema di Raven: I ≥95°, II ≥75° (II+ ≥90°), III fra 25° e 75°,
   IV ≤25° (IV− ≤10°), V ≤5°.
3. **I numeri in `tests/test_raven.py` sono inventati**: servono solo a provare i calcoli.

## Non ancora fatto

- Passaggio del risultato alla Diagnosi assistita.
- Importazione di norme e chiave da file (oggi: scrittura o incolla da Excel nella tabella).
