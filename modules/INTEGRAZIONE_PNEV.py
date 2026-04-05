# ══════════════════════════════════════════════════════════════════════════════
# INTEGRAZIONE PNEV IN app_core.py
# (aggiornamento del file INTEGRAZIONE_APP_CORE.py precedente)
# ══════════════════════════════════════════════════════════════════════════════

# 1. COSTANTI (aggiungere dopo le altre SECTION_*)
SECTION_VT          = "Visual Training"
SECTION_MIOFUNZ     = "Terapia Miofunzionale"
SECTION_SPORTIVI    = "Sport Vision"
SECTION_PNEV        = "Questionario PNEV"

# 2. IMPORT
from modules.vt import render_vt
from modules.miofunzionale import render_miofunzionale
from modules.sportivi import render_sportivi
from modules.pnev import render_pnev

# 3. Nel dict sections di build_sections():
#    SECTION_VT:       lambda pid, nome: render_vt(pid, nome),
#    SECTION_MIOFUNZ:  lambda pid, nome: render_miofunzionale(pid, nome),
#    SECTION_SPORTIVI: lambda pid, nome: render_sportivi(pid, nome),
#    SECTION_PNEV:     lambda pid, nome: render_pnev(pid, nome),

# ══════════════════════════════════════════════════════════════════════════════
# APP PUBBLICA PNEV — deployment separato
# ══════════════════════════════════════════════════════════════════════════════
#
# File: pnev_public/app_pnev.py
# Lanciare con:
#   streamlit run pnev_public/app_pnev.py --server.port 8502
#
# Su Streamlit Cloud: deployare come app separata dallo stesso repo.
# Configurare la variabile PNEV_PUBLIC_URL in modules/pnev/ui_pnev.py
# con l'URL pubblico dell'app (es. https://theorganism-pnev.streamlit.app)
#
# CONDIVISIONE DATABASE:
# L'app pubblica usa lo stesso DB (Neon postgres o SQLite).
# Le tabelle pnev_token e pnev_risposte sono create automaticamente
# al primo avvio di entrambe le app.
#
# FLUSSO COMPLETO:
# 1. Terapista: apre scheda paziente → PNEV → "Genera Link"
# 2. Sistema: crea token 8 char + scadenza → terapista copia testo WhatsApp
# 3. Paziente: riceve codice → va su app pubblica → inserisce codice → compila
# 4. Terapista: torna nella scheda PNEV → "Risposte" → vede tutto pre-caricato
