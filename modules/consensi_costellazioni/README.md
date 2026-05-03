# Modulo Consensi Costellazioni Familiari — v1.0 COMPLETO

Modulo plug-in per il gestionale Studio The Organism.
Gestisce i consensi privacy specifici per le costellazioni familiari (4 tipologie:
individuali, gruppo, rappresentante, registrazione AV) con firma digitale,
cartacea o a distanza tramite link.

## Architettura

```
modules/consensi_costellazioni/
├── __init__.py                # API pubblica del modulo
├── db_schema.py               # F1: 7 tabelle prefisso cf_
├── seeders/
│   └── costellazioni.py       # F1: seed 4 template
├── services.py                # F2: firma, revoca, validazione, token
├── pdf_generator.py           # F3: PDF branded #1D6B44
├── ui/                        # F4-F6: UI Streamlit
│   ├── pannello_paziente.py   #   Pannello consensi nella scheda paziente
│   ├── form_firma.py          #   Firma click_studio
│   └── form_cartaceo.py       #   Firma cartaceo (download/upload)
└── CORREZIONI_F1_DEPLOY.md    # Note correzioni F1 al deploy

pages/
└── firma_consenso_pubblico.py # F7: pagina pubblica firma a distanza

docs/
└── consensi_costellazioni.md  # Sorgente dei testi (4 documenti)
```

## Integrazione nel gestionale (3 step)

### Step 1 — Aggancia lo schema a `modules/schema_manager.py`

Apri `modules/schema_manager.py` e aggiungi:

```python
# In cima al file
from modules.consensi_costellazioni.db_schema import (
    apply_schema as _apply_consensi_costellazioni_schema,
)


def ensure_consensi_costellazioni_schema(conn, backend: Backend = "postgres") -> None:
    """Schema del modulo consensi costellazioni familiari."""
    _apply_consensi_costellazioni_schema(conn, db_backend=backend)


# Aggiorna la funzione esistente:
def ensure_all_schemas(conn, backend: Backend = "postgres") -> None:
    ensure_auth_schema(conn, backend=backend)
    ensure_core_schema(conn, backend=backend)
    ensure_vision_schema(conn, backend=backend)
    ensure_osteo_schema(conn, backend=backend)
    ensure_consensi_costellazioni_schema(conn, backend=backend)  # ← AGGIUNGI
```

### Step 2 — Aggiungi tab nella scheda paziente

Nel punto del codice del gestionale dove si renderizza la scheda paziente,
ad esempio in `modules/app_core.py` o nel modulo che gestisce le tab paziente:

```python
import streamlit as st

# Esempio: dentro la scheda paziente, aggiungi una tab "Consensi Costellazioni"
tab_anagrafica, tab_anamnesi, tab_consensi_cf, *altre = st.tabs([
    "Anagrafica",
    "Anamnesi",
    "🤝 Consensi Costellazioni",
    # ... altre tab esistenti
])

with tab_consensi_cf:
    from modules.consensi_costellazioni.ui import render_pannello_consensi
    render_pannello_consensi(
        paziente_id=int(paziente_attivo["id"]),
        paziente_nome=f"{paziente_attivo['cognome']} {paziente_attivo['nome']}",
    )
```

### Step 3 — Seed dei template (UNA TANTUM dopo il primo deploy)

Aggiungi un bottone admin in una sezione di gestione, oppure esegui da console:

```python
import streamlit as st

if st.button("🌱 Seed template costellazioni"):
    from modules.app_core import get_connection
    from modules.consensi_costellazioni.seeders.costellazioni import seed_template
    conn = get_connection()
    risultati = seed_template(
        conn,
        percorso_md="docs/consensi_costellazioni.md",
        sovrascrivi=False,
    )
    st.success(f"Template caricati: {risultati}")
```

Il seeder è **idempotente**: se i template esistono già, fa skip.

## Funzionalità principali

### Pannello consensi nella scheda paziente

Mostra i 4 consensi del paziente con badge di stato:
- ⚪ Mancante — bottone "Firma"
- ✅ Attivo (versione) — bottone "Dettagli"
- 🟡 Da rinnovare (versione firmata diversa da attuale)
- 🔴 Revocato
- ⏭️ Sostituito da nuova versione

Azioni disponibili: firma, rinnova, revoca (con motivazione), scarica PDF,
storico completo (incluso revocati).

### Tre modalità di firma

**Click in studio** — il paziente legge sul tablet/PC dello studio, l'operatore
(o il paziente) spunta le voci, sistema genera PDF con timbro digitale che
include hash SHA-256 del PDF, dati operatore, timestamp Europe/Rome, IP+UA.

**Cartaceo** — operatore scarica PDF stampabile vuoto, paziente firma a penna,
operatore scansiona, ricarica PDF firmato e ricopia nel sistema le voci spuntate
dal paziente. Il sistema calcola hash SHA-256 della scansione.

**Link al paziente** — operatore genera token monouso (scadenza 72h
configurabile), paziente firma sul proprio dispositivo dalla pagina pubblica
`/firma_consenso_pubblico?t=<token>`, sistema genera PDF e lo salva nel record.

### Validazione pre-azione clinica

```python
from modules.consensi_costellazioni import verifica_consensi_richiesti

check = verifica_consensi_richiesti(
    conn, paziente_id=42, azione="sessione_costellazioni_gruppo"
)
if not check["ok"]:
    st.warning(f"Mancanti: {check['mancanti']}, da rinnovare: {check['da_rinnovare']}")
```

Le azioni configurate (estendibili in `services.py`):
- `sessione_costellazioni_individuali` → richiede `costellazioni_individuali`
- `sessione_costellazioni_gruppo` → richiede individuali + gruppo
- `ruolo_rappresentante` → richiede individuali + gruppo + rappresentante
- `registrazione_sessione_costellazioni` → richiede individuali + registrazione

### Audit log

Tutte le operazioni (firma, revoca, generazione token) sono loggate in
`auth_audit_log` (tabella audit centralizzata del gestionale già esistente)
con prefisso `CF_*` (es. `CF_FIRMA_CREATA`, `CF_FIRMA_REVOCATA`).

## Coesistenza con `Consensi_Privacy` legacy

Il modulo NON tocca la tabella `Consensi_Privacy` esistente. La tua gestione
attuale (consensi adulto/minore con PDF firmati a penna, canali di
comunicazione) continua a funzionare invariata.

Questo modulo gestisce solo i 4 consensi specifici per costellazioni familiari.

## Test post-deploy

### Test 1 — Schema applicato
```python
from modules.app_core import get_connection
from modules.consensi_costellazioni import services
conn = get_connection()
print(services.template_attivo_per_codice(conn, 'costellazioni_individuali'))
```
Se restituisce `None`: eseguire seeding (Step 3).

### Test 2 — Firma di prova
```python
from modules.consensi_costellazioni import firma_consenso
ris = firma_consenso(
    conn,
    paziente_id=PAZIENTE_TEST_ID,
    codice_template='costellazioni_individuali',
    voci={'B.1': True, 'B.2': True, 'B.3': True, 'B.4': True, 'B.5': False},
    modalita_firma='click_studio',
    operatore_username='admin',
)
print(f"Firma OK: id={ris['firma_id']}")
```

### Test 3 — Visualizzazione pannello
Naviga alla scheda paziente di test → tab "Consensi Costellazioni" → dovresti
vedere il pannello con tutti i consensi in stato "Mancante".

## Spec multi-tenancy (futuro)

Lo schema attuale è single-tenant. L'isolamento multi-studio è già garantito
dal pattern multi-DB del tuo `modules/saas_tenant.py` (un DB fisico per studio).

Se in futuro consoliderai in unico DB con RLS, vedi le note in
`CORREZIONI_F1_DEPLOY.md`.

## Versione

`1.0.0-mvp-completo` — F1+F2+F3+F4+F5+F6+F7 implementati, testati end-to-end,
~2000 righe di codice.

## Roadmap futura (non prevista nel MVP)

- F8 — gestione minori e nuclei familiari (genitore firma per il minore)
- F9 — assorbimento progressivo di `Consensi_Privacy` legacy
- F10 — UI admin gestione template (CRUD versionamento)
- F11 — dashboard reporting consensi (statistiche per categoria, scadenze)
