# Modulo Osteopatia (A4) — integrazione nel Gestionale TEST

Questa cartella contiene un modulo completo per:
- Anamnesi osteopatica
- Seduta osteopatica
- Storico + PDF A4 per seduta
- Dashboard (dolore pre/post)

## 1) Copia i file nel repo del gestionale TEST

Copia la cartella:
`modules/osteopatia/`
dentro il tuo progetto (stesso livello dove hai già `modules/` o equivalente).

Struttura:
modules/
  osteopatia/
    __init__.py
    osteo_schema.sql
    db_osteopatia.py
    ui_osteopatia.py
    pdf_osteopatia.py
    dashboard_osteopatia.py

## 2) Esegui la migrazione SQL su Neon (una volta sola)

Apri Neon (SQL editor) e incolla il contenuto di:
`modules/osteopatia/osteo_schema.sql`
Esegui.

✅ A fine run devono esistere:
- osteo_anamnesi
- osteo_seduta

## 3) Dipendenze (requirements)

Assicurati che nel tuo `requirements.txt` ci siano:
- reportlab
- pandas
- matplotlib

Se già li usi, ok.

## 4) Integra la tab "Osteopatia" nella schermata paziente

Nel file dove costruisci la UI del paziente (es. `ui_pazienti()` o tab visite),
aggiungi import e chiamata.

Esempio (pseudo):

from modules.osteopatia.ui_osteopatia import ui_osteopatia
from db import get_conn  # LA TUA funzione che ritorna una conn psycopg2

# ... quando hai paziente selezionato
tabs = st.tabs(["Dati", "Visita", "Visione", "Osteopatia"])  # aggiungi tab
with tabs[3]:
    ui_osteopatia(
        paziente_id=selected_patient_id,
        get_conn=get_conn,
        paziente_label=f"{cognome} {nome}"
    )

NOTA: `selected_patient_id` deve essere l'ID numerico che usi nel DB.

## 5) Test rapido (checklist)

1) Apri un paziente
2) Tab Osteopatia -> salva una anamnesi
3) Tab Osteopatia -> salva una seduta (anche senza collegarla all'anamnesi)
4) Storico -> genera PDF A4 e scaricalo
5) Dashboard -> vedi il grafico dolore

## 6) Se qualcosa non va

- Errore "relation osteo_anamnesi does not exist":
  => non hai eseguito lo SQL su Neon (step 2) o sei su DB diverso.

- Errore import modules:
  => controlla che `modules/osteopatia/__init__.py` esista (anche vuoto).

- PDF vuoto / campi mancanti:
  => la seduta deve essere presa con `get_seduta()` (già fatto nello storico).

## 7) Upgrade intestazione The Organism

Questo PDF è "pulito" A4.
Se vuoi lo stesso identico layout dei tuoi referti (logo + margini), dimmi:
- hai un template PDF A4 già pronto?
- oppure preferisci header immagine (logo) e footer?
