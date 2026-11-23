# Modulo ADHD — dove vanno i file

Tutto nello stesso commit, sul branch `main`.

## File nuovi

Cartella `modules/adhd/` (caricala intera):

- `__init__.py`
- `catalogo_adhd.py` — strumenti, soglie, elenco prove e test esterni
- `scoring_adhd.py` — calcoli (senza database)
- `db_adhd.py` — tabelle `adhd_registrazioni` e `adhd_testi`, create da sole al primo ingresso
- `ui_adhd.py` — le 7 schede
- `ui_pubblico_adhd.py` — le scale compilate da casa con il link, e il loro arrivo nel modulo
- `pdf_adhd.py` — report su carta intestata
- `prove_component/index.html` — le 4 prove a schermo (file unico, offline)

In `tests/`: `test_adhd.py` (15 prove dei calcoli; avvio: `pytest tests/test_adhd.py`).

## File modificati (sostituiscono quelli esistenti)

In `modules/`:

- `app_menu.py` — voce «🎯 ADHD — Valutazione» in Valutazione → Test psicologici
- `app_main_router.py` — apertura del modulo (due punti) e voce tra quelle «con paziente»
- `filtro_eta.py` — la voce compare dai 5 anni; Fisher adulti solo adulti, scale ADHD solo sotto i 17
- `app_core.py` — elenco dei questionari con link (personali e aperti) e pagina pubblica:
  aggiunti Fisher adulti, SCAP-A e le 4 scale ADHD
- `ui_questionari.py` — etichette, riquadro «Fisher adulti» nella scheda, nomi per l'AI
- `questionari_cartacei.py` — Fisher adulti e SCAP-A da stampare
- `lead_sito.py` — Fisher adulti tra i questionari del sito

In `modules/pnev/`:

- `ui_questionari_pnev.py` — nuovi questionari «Fisher adulti» e «SCAP-A» (la versione bambini non è toccata)

Sono partiti dal commit `73195b4` del 21/11/2026. Se dopo quella data hai cambiato uno
di questi file, non sovrascriverlo: dimmelo e rifaccio la modifica sulla versione nuova.

## Questionari con il link

Codici nuovi, validi sia per il link personale sia per il link aperto (senza nome):

| Codice | Questionario | Dove finisce |
|---|---|---|
| `FISHER_ADULTI` | Fisher – problemi uditivi, adulti | scheda Questionari del paziente |
| `SCAP_A` | SCAP-A – ascolto, adulti (12 domande) | scheda Questionari del paziente |
| `ADHD_VAND_GEN` | Vanderbilt genitori | scheda Questionari e modulo ADHD |
| `ADHD_VAND_INS` | Vanderbilt insegnanti | scheda Questionari e modulo ADHD |
| `ADHD_SCARED_B` / `ADHD_SCARED_G` | SCARED ragazzo/a e genitori | scheda Questionari e modulo ADHD |

Le scale ADHD si aprono da casa solo se il testo degli item è stato caricato; altrimenti chi apre
il link legge «questionario non ancora attivo». Quando una scala torna compilata, il modulo ADHD
la prende da solo alla prima apertura della scheda del paziente. A chi compila non viene mostrato
nessun punteggio.

**Fisher adulti** è un adattamento in prima persona dei 25 item della versione bambini: stesso
punteggio (4% per ogni frase non segnata) e stesso profilo di Katz. Non ha norme per adulti: il
riferimento del 72% è quello dei bambini e viene sempre indicato come «indicativo».

## Cosa fa

| Scheda | Contenuto |
|---|---|
| Quadro | cosa è fatto e cosa manca, prossimo passo, quadro d'insieme con concordanza tra informatori |
| Scale | Vanderbilt genitori (55 item) e insegnanti (43), SCARED bambino e genitore (41) |
| Criteri | scheda del clinico: 18 comportamenti, esordio, contesti, compromissione, esclusioni |
| Prove a schermo | attenzione sostenuta, go/no-go, Stroop colori, span di cifre |
| Test esterni | punteggi di Conners 3, WISC-V, BIA, Rey, BVSCO o altro, con z, percentile e fascia |
| Report PDF | tutto insieme, più le considerazioni del clinico |
| Testi e licenze | caricamento del testo degli item e regole di punteggio |

## Tre cose da sapere

1. **Il testo degli item delle scale non è nel codice.** Finché non lo carichi (scheda
   «Testi e licenze», una volta sola per studio), la scala funziona come foglio risposte:
   il genitore compila il cartaceo e in studio si riportano le risposte.
2. **Le prove a schermo non hanno norme.** Danno tempi ed errori del paziente, da confrontare
   nel tempo (prima / dopo, controlli a 10–20–30–40 settimane). Non dicono dove si colloca
   rispetto ai coetanei.
3. **Le soglie Vanderbilt sono quelle originali americane**: non esistono norme italiane.

**SCAP-A** usa le stesse 12 domande e lo stesso punteggio della scheda SCAP-A di Diagnostica uditiva
(0–3 nella norma, 4–6 lieve, 7–9 moderato, 10–12 significativo). Quello compilato con il link si legge
nella scheda Questionari; non compare ancora nello storico di Diagnostica uditiva.

## Non ancora fatto

- Passaggio dei dati del modulo ADHD alla Diagnosi assistita (le scale arrivate con il link,
  invece, l'AI le vede già come gli altri questionari).
- Se la stessa scala viene compilata due volte con il link prima che tu apra il modulo ADHD
  (es. mamma e papà), nell'anamnesi resta solo l'ultima: è il comportamento di tutti i questionari.
- Voce nel diario clinico: il codice la scrive, ma solo se `modules/diario/db_diario.py` riesce
  a importare `get_connection`; altrimenti salta senza errori.
