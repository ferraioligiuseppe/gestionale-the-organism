# modules/lac/ — che cos'è rimasto e perché

Aggiornato il 2026-09-22.

## In breve

Il modulo LAC vero e proprio **non è qui**: è in `modules/contattologia/`,
ed è raggiungibile dal menu alla voce «👁️ Contattologia». Questa cartella
conserva soltanto la matematica in chiaro.

## Che cosa resta qui, e a che serve

| File | Perché è rimasto |
| --- | --- |
| `lac_engine_sag.py` | 18 funzioni di geometria sagittale in chiaro e commentate: `sag_conica`, `sag_sfera`, `pendenza_conica`, `raggio_2pt`, `calcola_corneale`, `calcola_sclerale`, `stima_sag_oculare`, `stima_clearance`, `lente_lacrimale`, `render_fluorescein` e altre. **Non è codice attivo**: nessun modulo lo importa. È la documentazione eseguibile delle formule che il modulo di contattologia applica in JavaScript. Serve per verificare un calcolo, per riprendere la matematica, e come riferimento per chiunque debba capire su che basi poggia il motore. |
| `lac_engine.py` | Tabelle ESA e calcoli per ipermetropia, astigmatismo, presbiopia. Stessa natura: riferimento, non codice attivo. |
| `lac_decision.py` | `build_curves` — la logica di scelta delle curve. Dipende da `lac_engine`. |
| `__init__.py` | Espone i due sopra. Lasciato perché `from modules.lac import …` continui a funzionare. |

## Che cosa è stato archiviato, e perché

Spostato nel ramo `archivio-lac-2026-09`, fuori da `main`. Recuperabile in
qualsiasi momento, ma non più caricato dall'applicazione.

| File archiviato | Motivo |
| --- | --- |
| `modules/lac/lac_fluoro.py` | Ponte verso `modules/ui_lenti_contatto.py`, **file che non esiste più nel repository**. Chiamarlo sollevava `ImportError`. |
| `modules/lac/lac_storage.py` | Stesso ponte rotto. |
| `modules/lac/lac_topography.py` | Stesso ponte rotto. |
| `modules/lac/MIGRAZIONE_GUIDATA.txt` | Descriveva una migrazione verso `modules/lac/ui_lenti_contatto.py` che non è stata fatta e non serve più: il modulo è stato rifatto da zero come `modules/contattologia/`. Le sue istruzioni ora sono fuorvianti. |
| `modules/ui_calcolatore_lac.py` (36 KB) | Implementazione LAC precedente. Non raggiungibile dal menu né dal router. |
| `modules/ui_calcolatore_lac_plus.py` (42 KB) | Idem. |
| `modules/ui_lac_ametropie.py` (44 KB) | Idem. |
| `modules/app_main.py` | Vecchio router, sostituito da `app_main_router.py`. Nessun file lo importa. Puntava a `ui_lenti_contatto`, che non esiste più. |

Erano circa 160 KB di codice che descriveva lo stesso problema in cinque modi
diversi, nessuno dei quali attivo. Il rischio non era il malfunzionamento — non
girava nulla — ma il dubbio: fra sei mesi non si sarebbe più capito quale fosse
la versione buona.

## Il sorgente del modulo di contattologia

Il file in `modules/contattologia/frontend/index.html` è **offuscato**: non è
leggibile né modificabile. Il sorgente in chiaro esiste e si chiama
`LAC_MASTER_sorgente.html` (3.943 righe, 219 KB), e sta nell'archivio privato
del titolare — **non nel repository**, per scelta.

Dallo stesso sorgente escono tre file che convivono e vanno rigenerati insieme:

| File | Dove va |
| --- | --- |
| `LAC_PRODUZIONE_offuscato.html` | qui, come `modules/contattologia/frontend/index.html` |
| `LAC_VETRINA_pnev.html` | www.pnev.it, cartella pubblica — senza dati paziente |
| `LAC_MASTER_sorgente.html` | archivio privato, non distribuito |

Da questa versione tutti e tre portano in testa un `<meta name="lac-build">`
e una riga di versione visibile in fondo alla schermata. **Prima di modificare
qualcosa, verificare che i tre build coincidano**: se non coincidono, il
sorgente leggibile non descrive più ciò che gira in studio.

Documentazione completa del motore: `Manuale_LAC.pdf` (61 pagine) e
`Dove_va_ogni_file.pdf`, nell'archivio del titolare.

---
Progettato da Dott. Giuseppe Ferraioli — www.pnev.it
© 2026 Giuseppe Ferraioli. Tutti i diritti riservati.
