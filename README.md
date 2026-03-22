# The Organism – Gestionale Studio

Gestionale clinico per studi di neuropsicomotricità, osteopatia e riabilitazione uditiva. Costruito con Streamlit e PostgreSQL (Neon).

---

## Funzionalità principali

- **Anagrafica pazienti** — ricerca, scheda completa, archiviazione
- **PNEV** — valutazione psico-neuro-evolutiva con questionari strutturati
- **Valutazioni visive** — schede cliniche per optometria e vision therapy
- **Sedute** — gestione appuntamenti, costi e pagamenti
- **Osteopatia** — schede anamnesi e trattamento osteopatico
- **Stimolazione uditiva** — generatore stimoli Tomatis con EQ personalizzabile
- **Eye Tracking** — gaze tracking browser-based via MediaPipe JS con filtro pazienti
- **Privacy** — generazione e firma digitale consensi GDPR
- **Referti e prescrizioni** — generazione PDF e Word da template
- **Assistente AI** — supporto alla stesura di relazioni cliniche
- **Dashboard** — statistiche e KPI dello studio
- **Multi-utente** — gestione ruoli (admin, clinico, segreteria, vision, osteo)

---

## Setup locale

```bash
git clone https://github.com/tuo-utente/gestionale-the-organism.git
cd gestionale-the-organism
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Compila secrets.toml con le tue credenziali
streamlit run app.py
```

---

## Deploy su Streamlit Cloud

1. Push del repo su GitHub
2. Connetti su [share.streamlit.io](https://share.streamlit.io)
3. In **App Settings → Secrets**, incolla il contenuto di `.streamlit/secrets.toml.example` compilato
4. File principale: `app.py`

---

## Struttura del progetto

```
├── app.py                          # Entry point Streamlit
├── modules/                        # Codice sorgente (unica fonte di verità)
│   ├── app_core.py                 # Logica principale e routing
│   ├── schema_manager.py           # Bootstrap schema DB (idempotente)
│   ├── anamnesi/
│   ├── pazienti/
│   ├── pnev/
│   ├── osteopatia/
│   ├── stimolazione_uditiva/
│   ├── gaze_tracking/
│   ├── privacy/
│   ├── referti/
│   ├── assistant_ai/
│   └── dashboard/
├── assets/                         # CSS, PDF template, immagini
├── templates/                      # Template Word relazioni cliniche
├── .streamlit/
│   ├── config.toml
│   └── secrets.toml.example
├── _archive/                       # Versioni precedenti (solo riferimento)
├── requirements.txt
└── .gitignore
```

> I file Python nella root sono shim di compatibilità che re-esportano da `modules/`. Il codice attivo vive esclusivamente in `modules/`.

---

## Variabili d'ambiente richieste

| Variabile | Descrizione | Obbligatoria |
|-----------|-------------|:---:|
| `db.url` | Connection string PostgreSQL Neon | ✅ |
| `auth.token_secret` | Chiave HMAC token pubblici | ✅ |
| `openai.api_key` | Chiave API OpenAI | Solo con modulo AI |
| `app.mode` | `prod` o `test` | ✅ |
| `app.public_base_url` | URL app per link firma privacy | Consigliata |

---

## Licenza

Software proprietario – © The Organism. Tutti i diritti riservati.
