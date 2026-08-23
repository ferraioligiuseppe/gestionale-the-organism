# -*- coding: utf-8 -*-
"""
scripts/promemoria_ascolti_maps.py

Cron giornaliero: manda il promemoria dell'ascolto a chi non ha ancora
ascoltato oggi, e un riepilogo allo studio. Da eseguire una volta al giorno,
in tarda mattinata (es. 11:00), via GitHub Actions — stesso meccanismo di
scripts/sync_pnev.py.

Secret necessario: STREAMLIT_SECRETS (lo stesso già usato dall'app e da
sync_pnev.py) — contiene DB e SMTP in formato TOML. Viene scritto in
.streamlit/secrets.toml prima di importare l'app, così get_connection()
lo trova esattamente come in produzione.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_secrets_toml = os.environ.get("STREAMLIT_SECRETS", "")
if _secrets_toml:
    os.makedirs(".streamlit", exist_ok=True)
    with open(".streamlit/secrets.toml", "w") as f:
        f.write(_secrets_toml)

from modules.app_core import get_connection  # riusa la connessione già configurata
from modules.ascolti_maps import invia_promemoria_giornalieri

if __name__ == "__main__":
    conn = get_connection()
    email_studio = os.environ.get("EMAIL_STUDIO") or "info@pnev.it"
    n = invia_promemoria_giornalieri(conn, email_studio=email_studio)
    print(f"CRON_RESULT: {n} promemoria inviati, riepilogo a {email_studio}")
