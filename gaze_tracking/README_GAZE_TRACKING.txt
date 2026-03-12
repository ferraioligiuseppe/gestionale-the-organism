Modulo Gaze Tracking - prototipo webcam-based

1) Copia la cartella modules/gaze_tracking e components/gaze_tracker_component nel repo.
2) Esegui app una volta: il modulo crea automaticamente le tabelle se mancano.
3) In alternativa lancia il file gaze_schema.sql.
4) Serve accesso browser alla webcam.
5) Il componente carica WebGazer da CDN: se vuoi evitare dipendenze esterne, vendorizza la libreria nel frontend.

NOTE
- E' un prototipo funzionale, non un eye tracker medicale certificato.
- Le metriche sono base: fixation_total_ms, saccade_count, target_hit_rate, tracking_loss_pct.
