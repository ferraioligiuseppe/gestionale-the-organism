# -*- coding: utf-8 -*-
"""
scripts/promemoria_ascolti_maps.py

Cron giornaliero: manda il promemoria dell'ascolto a chi non ha ancora
ascoltato oggi, e un riepilogo allo studio. Da eseguire una volta al giorno,
in tarda mattinata (es. 11:00), via GitHub Actions — stesso meccanismo di
scripts/sync_pnev.py.

Secrets necessari (gli stessi già usati dal gestionale):
  DB_* (connessione PostgreSQL OVH) + smtp.* per l'invio email,
  più EMAIL_STUDIO per il riepilogo a Giuseppe.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.app_core import get_connection  # riusa la connessione già configurata
from modules.ascolti_maps import invia_promemoria_giornalieri

if __name__ == "__main__":
    conn = get_connection()
    email_studio = os.environ.get("EMAIL_STUDIO") or "info@pnev.it"
    n = invia_promemoria_giornalieri(conn, email_studio=email_studio)
    print(f"CRON_RESULT: {n} promemoria inviati, riepilogo a {email_studio}")
