# Vision Manager v3 – Fix DB + Referto stile 'buono'

- Fix migrazione Postgres: ALTER TABLE ADD COLUMN IF NOT EXISTS (evita UndefinedColumn)
- Referto A4 stile 'Dettaglio clinico'
- Prescrizione invariata (TABO solo OSN)
- Storico + confronto + grafici + export CSV ottico

## Diottrie (selettori)
- SF: da -30.00 a +30.00 (step 0.25)
- CIL: da -15.00 a +15.00 (step 0.25)
- AX: 0–180

## Carta intestata (PDF template)
Metti i PDF in `vision_core/assets/`:
- `letterhead_referto_A4.pdf`
- `letterhead_prescrizione_A4.pdf`
(opzionale) `letterhead_prescrizione_A5.pdf`

Se mancano, il sistema usa intestazione testuale.
