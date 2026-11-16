"""Testi del foglio informativo, dell'informativa privacy e dei consensi.

Ogni modifica ai testi va fatta cambiando PRIVACY_VERSIONE: il gestionale registra
per ogni partecipante la versione che ha accettato.
Bozza da far verificare (titolare del trattamento, comitato etico) prima dell'uso.
"""

PRIVACY_VERSIONE = "2026-11-16 v1"

TITOLARE = ("Dott. Giuseppe Ferraioli, Studio The Organism, Via De Rosa 46, 84016 Pagani (SA) — "
            "apstheorganism@gmail.com")

FOGLIO_INFORMATIVO = """
**Studio pilota sull'uso dell'app di ascolto Pegasis in adulti volontari**

**Responsabile:** Dott. Giuseppe Ferraioli, psicologo (Albo n. 9267), Studio The Organism, Pagani (SA).

**Scopo.** Verificare l'ipotesi che 20 sessioni di ascolto con Pegasis migliorino attenzione, memoria di lavoro e
benessere, e se sono facili da seguire.

**Cosa ti chiediamo**
- Sarai assegnato a sorte al gruppo A (inizia subito) o al gruppo B (inizia dopo alcune settimane).
- 20 sessioni di 30 minuti, una al giorno, con cuffie o auricolari, sul tuo telefono Android.
- Due o tre volte: un questionario di circa 2 minuti e tre prove di attenzione e memoria sul telefono (circa 10 minuti).
- Facoltativo: un test di ascolto di circa 12 minuti all'inizio e alla fine.

**Possibili fastidi.** Stanchezza, mal di testa o fastidio alle orecchie, di solito lievi e passeggeri: abbassa il volume
o sospendi, e avvisa il responsabile.

**Chi deve parlarne prima con il responsabile.** Chi ha ipoacusia, acufene, iperacusia, otiti in corso, epilessia,
o è in gravidanza.

**Benefici.** Non sono garantiti benefici personali. Pegasis non è un dispositivo medico; lo studio non è una diagnosi
né una terapia.

**Partecipazione.** Libera e gratuita; ti puoi ritirare in qualsiasi momento senza dare spiegazioni e senza conseguenze.
La partecipazione non ha alcun legame con il percorso TFA né con le sue valutazioni.
"""

INFORMATIVA = f"""
**Informativa sul trattamento dei dati personali (artt. 13 e 9 GDPR)**

- **Titolare:** {TITOLARE}.
- **Dati trattati:** nome, cognome e contatti (solo per gestire la partecipazione, conservati separatamente);
  codice partecipante; fascia d'età, sesso, mano dominante, disturbi uditivi noti, tipo di cuffie;
  risposte ai questionari WHO-5 e PNEV; risultati delle prove di attenzione e memoria; sessioni fatte;
  colori scelti; se lo fai, test di ascolto.
- **Dati relativi alla salute:** i questionari sul benessere e le informazioni sull'udito rientrano nell'art. 9 GDPR.
- **Finalità:** ricerca scientifica; pubblicazione solo in forma aggregata e anonima.
- **Base giuridica:** consenso esplicito (art. 6.1.a e 9.2.a GDPR).
- **Pseudonimizzazione:** i dati della ricerca sono registrati solo con il codice; nome e contatti stanno in un archivio
  separato, accessibile solo al responsabile.
- **Destinatari:** responsabile dello studio ed eventuali collaboratori alla ricerca, tenuti alla riservatezza.
  Nessuna cessione a terzi né uso commerciale.
- **Conservazione:** dati di contatto e consensi per 5 anni dalla fine dello studio; dati con codice fino alla
  pubblicazione, poi solo in forma anonima.
- **Diritti:** accesso, rettifica, cancellazione, limitazione, opposizione e revoca del consenso in ogni momento
  (artt. 15-22), scrivendo al titolare; reclamo al Garante per la protezione dei dati personali (www.garanteprivacy.it).
- **Ritiro:** se ti ritiri, i tuoi dati vengono cancellati, salvo quelli già resi anonimi in risultati pubblicati.
"""

# chiave, testo, obbligatorio
CONSENSI = [
    ("letto", "Ho letto il foglio informativo e l'informativa privacy e ho potuto fare domande.", True),
    ("partecipo", "Acconsento a partecipare allo studio pilota Pegasis.", True),
    ("dati_salute", "Acconsento al trattamento dei miei dati, compresi quelli relativi alla salute, per la ricerca descritta.", True),
    ("ritiro", "So che posso ritirarmi in qualsiasi momento, senza motivazioni e senza conseguenze.", True),
    ("maggiorenne", "Dichiaro di essere maggiorenne.", True),
    ("ricontatto", "(Facoltativo) Acconsento a essere ricontattato per studi futuri.", False),
]

FASCE_ETA = ["18-24", "25-34", "35-44", "45-54", "55-64", "65+"]
SESSO = ["Femmina", "Maschio", "Altro / preferisco non dirlo"]
MANO = ["Destra", "Sinistra", "Entrambe"]
SI_NO = ["No", "Sì", "Non so"]
CUFFIE = ["Cuffie con filo", "Auricolari con filo", "Cuffie bluetooth", "Auricolari bluetooth"]
