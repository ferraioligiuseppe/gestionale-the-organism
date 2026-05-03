# Note per il deploy: correzioni F1 da applicare

F2 (`services.py`) è stato scritto contro la struttura di F1 esistente.
Quando deployi sul gestionale OVH, applica queste 3 correzioni a F1 per allinearlo
alle convenzioni del gestionale.

## 1. Aggancia il modulo a `modules/schema_manager.py`

Il pattern del gestionale prevede che ogni modulo registri il proprio schema in
`modules/schema_manager.py::ensure_all_schemas()`. Aggiungi:

```python
# In modules/schema_manager.py, in cima al file
from modules.consensi_costellazioni.db_schema import (
    apply_schema as _apply_consensi_costellazioni_schema,
)


def ensure_consensi_costellazioni_schema(conn, backend: Backend = "postgres") -> None:
    """Schema del modulo consensi costellazioni familiari."""
    _apply_consensi_costellazioni_schema(conn, db_backend=backend)


def ensure_all_schemas(conn, backend: Backend = "postgres") -> None:
    ensure_auth_schema(conn, backend=backend)
    ensure_core_schema(conn, backend=backend)
    ensure_vision_schema(conn, backend=backend)
    ensure_osteo_schema(conn, backend=backend)
    ensure_consensi_costellazioni_schema(conn, backend=backend)  # ← AGGIUNGI
```

In questo modo lo schema del modulo si crea automaticamente al primo avvio.

## 2. Rimuovi le FK verso `Pazienti` (opzionale ma consigliato)

Il gestionale non usa FK rigorose verso `Pazienti` per gestire la variabilità
del nome tabella tra dev (SQLite, lowercase) e prod (Postgres, mixed case).
Modifica in `db_schema.py`:

**Cerca queste righe nel DDL Postgres e SQLite e rimuovi `REFERENCES Pazienti(id)`:**

```python
# Prima:
paziente_id BIGINT NOT NULL REFERENCES Pazienti(id) ON DELETE CASCADE,

# Dopo:
paziente_id BIGINT NOT NULL,
```

Le FK da rimuovere sono in:
- `cf_firme.paziente_id`
- `cf_gruppi_partecipanti.paziente_id`
- `cf_token_firma.paziente_id`
- `cf_audit_log.paziente_id` (se mantieni la tabella)

La validazione che il paziente esista è gestita applicativamente da F2 (`services.py`)
e dalla UI (F4-F5).

## 3. Decidi su `cf_audit_log`

F2 usa l'audit centralizzato `auth_audit_log` (tabella già esistente nel gestionale,
funzione `_audit` di `modules/app_core.py`). Ha senso eliminare `cf_audit_log` per
evitare duplicazione. Due opzioni:

**Opzione A — Elimina `cf_audit_log` (consigliata):**
Rimuovi la sezione `DDL_PG_AUDIT` e `DDL_SQLITE_ALL` (la riga `cf_audit_log`).
Tutto l'audit passa per `auth_audit_log` con prefisso azione `CF_*`.

**Opzione B — Mantieni `cf_audit_log` per audit specifici del modulo:**
Lascialo. F2 attualmente usa solo `auth_audit_log`, quindi `cf_audit_log` resta
inutilizzata. Potrebbe servire in futuro per audit più dettagliati.

## 4. Seeding una tantum

Dopo il primo deploy con schema creato, esegui il seed dei 4 template.
Aggiungi un bottone admin in una sezione gestione del gestionale, oppure usa
una console Streamlit:

```python
import streamlit as st
from modules.app_core import get_connection
from modules.consensi_costellazioni.seeders.costellazioni import seed_template

if st.button("Seed template costellazioni"):
    conn = get_connection()
    risultati = seed_template(
        conn,
        percorso_md='docs/consensi_costellazioni.md',
        sovrascrivi=False
    )
    st.success(f"Template caricati: {risultati}")
```

## 5. Verifica funzionamento

Dopo il deploy, da una sezione admin esegui:

```python
from modules.consensi_costellazioni import services

# Test 1: template caricato?
tpl = services.template_attivo_per_codice(conn, 'costellazioni_individuali')
st.json(tpl)

# Test 2: firma di prova su un paziente test
ris = services.firma_consenso(
    conn,
    paziente_id=PAZIENTE_TEST_ID,
    codice_template='costellazioni_individuali',
    voci={'B.1': True, 'B.2': True, 'B.3': True, 'B.4': True, 'B.5': False},
    modalita_firma='click_studio',
    operatore_username=st.session_state['user']['username'],
    operatore_user_id=st.session_state['user']['id'],
)
st.json(ris)

# Test 3: validazione
check = services.verifica_consensi_richiesti(
    conn, PAZIENTE_TEST_ID, 'sessione_costellazioni_individuali'
)
st.json(check)
```
