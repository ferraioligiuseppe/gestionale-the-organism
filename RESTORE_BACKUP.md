# Ripristino di un backup del database — The Organism

Questa guida spiega come ripristinare il database da un backup cifrato salvato su
Cloudflare R2. Serve nei casi di emergenza (dati persi, migrazione su un nuovo
server, replica dell'ambiente per un nuovo studio cliente).

I backup vengono creati automaticamente ogni notte dal workflow GitHub Actions
"Backup Database" e salvati sul bucket R2 in tre cartelle:

- `backup/daily/`   → ultimi 14 giorni
- `backup/weekly/`  → ultime 8 domeniche
- `backup/monthly/` → ultimi 12 mesi (primo del mese)

Ogni file ha un nome tipo: `the_organism_prod_20260602_023000.dump.enc`
- `.dump` = formato custom di PostgreSQL (compresso)
- `.enc`  = cifrato con AES-256 (serve la passphrase per aprirlo)

---

## Cosa serve

1. Il **file di backup** scaricato da R2 (dalla dashboard Cloudflare R2, oppure
   con uno strumento come `rclone`/`aws cli`).
2. La **passphrase di cifratura** (la stessa salvata nel secret `BACKUP_PASSPHRASE`
   su GitHub). ⚠️ Senza questa il backup NON è recuperabile: custodiscila in un
   posto sicuro (password manager).
3. Un computer con installati `openssl` e gli strumenti PostgreSQL
   (`pg_restore`, `psql`). Su Mac: `brew install postgresql openssl`.

---

## Passo 1 — Decifrare il backup

```bash
# Sostituisci il nome del file con quello scaricato.
# Ti verrà chiesta la passphrase (oppure usala via variabile come sotto).
export BACKUP_PASSPHRASE='la-tua-passphrase'

openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 \
  -in  the_organism_prod_20260602_023000.dump.enc \
  -out ripristino.dump \
  -pass env:BACKUP_PASSPHRASE
```

Ora hai `ripristino.dump` (il dump in chiaro, ma ancora compresso).

> Se il backup non fosse cifrato (file senza `.enc`), salta questo passo:
> il file è già il `.dump` pronto.

---

## Passo 2 — Ripristinare in un database

### Opzione A — In un database NUOVO e vuoto (consigliata)

```bash
# Crea un database vuoto di destinazione (cambia nome/host secondo necessità)
createdb -h HOST -U UTENTE organism_ripristino

# Ripristina dentro al database vuoto
pg_restore -h HOST -U UTENTE -d organism_ripristino --no-owner ripristino.dump
```

### Opzione B — Sovrascrivere il database esistente

⚠️ **Operazione distruttiva**: cancella i dati attuali e li sostituisce con quelli
del backup. Fallo solo se sei sicuro (es. dopo aver perso i dati).

```bash
pg_restore -h HOST -U UTENTE -d organism --clean --if-exists --no-owner ripristino.dump
```

`HOST` e `UTENTE` sono gli stessi presenti nel `DATABASE_URL` del database
(li trovi nei secret, sezione `[db]`).

---

## Passo 3 — Verifica

```bash
psql -h HOST -U UTENTE -d organism_ripristino -c "SELECT count(*) FROM pazienti;"
```

Se il numero di righe è coerente con quello atteso, il ripristino è riuscito.

---

## Note operative

- **Prova periodica:** ogni tanto conviene fare una prova di ripristino su un
  database "usa e getta" (Opzione A). Un backup che non è mai stato ripristinato
  non è un backup affidabile.
- **Passphrase:** se la cambi nel secret `BACKUP_PASSPHRASE`, i backup creati con
  la passphrase vecchia restano decifrabili solo con quella vecchia. Tieni traccia
  di quale passphrase apre quali file.
- **Conservazione:** i numeri (14 / 8 / 12) sono regolabili dalle variabili
  `KEEP_DAILY`, `KEEP_WEEKLY`, `KEEP_MONTHLY` nel workflow `backup_db.yml`.
