VERSIONE PULITA DEL PROGETTO — NOTE OPERATIVE

Questa copia parte dalla repo PROD ed è stata pulita/integrata senza sovrascrivere vision_manager.

Modifiche applicate:
- mantenuta intatta la cartella vision_manager/
- corretto st.set_page_config() per evitare StreamlitAPIException
- applicato tema globale con assets/ui.css + assets/pnev.css
- corretta la pagina pubblica firma/privacy per non richiamare set_page_config una seconda volta
- corretta l'indentazione del blocco invio email nella pagina firma online
- copiati dalla TEST solo i moduli sicuri:
  - pnev_ai.py
  - pnev_module.py
  - schema_manager.py
  - render_final.py
  - ui_generatore_stimolazione.py
  - modules/stimolazione_uditiva/
  - templates *_BIBLIO.docx

Cosa NON è stato fatto volutamente:
- nessuna sovrascrittura completa di app.py con la versione TEST
- nessuna sostituzione di vision_manager/
- nessun cambio a secrets, database o workflow GitHub

Passo consigliato:
1) prova questa copia in locale / branch test
2) se parte bene, usa questa come base per il prossimo merge in produzione
3) integra nel menu le nuove sezioni solo dopo verifica funzionale
