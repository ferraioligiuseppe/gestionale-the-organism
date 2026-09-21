# -*- coding: utf-8 -*-
"""
scripts/promemoria_aderenza.py

Cron giornaliero: contatta le famiglie il cui lavoro a casa e' sotto
soglia o ferma da giorni, e manda un riepilogo allo studio. Stesso
meccanismo di scripts/promemoria_ascolti_maps.py.

Secret necessario: STREAMLIT_SECRETS (lo stesso gia' usato dall'app) —
contiene DB e SMTP in formato TOML. Viene scritto in
.streamlit/secrets.toml prima di importare l'app, cosi' get_connection()
lo trova esattamente come in produzione.

Variabili d'ambiente opzionali:
    EMAIL_STUDIO   destinatario del riepilogo (default info@pnev.it)
    DRY_RUN=1      calcola tutto senza inviare niente
    SOGLIA         percentuale sotto cui scatta il messaggio (default 70)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_secrets_toml = os.environ.get("STREAMLIT_SECRETS", "")
if _secrets_toml:
    os.makedirs(".streamlit", exist_ok=True)
    with open(".streamlit/secrets.toml", "w") as f:
        f.write(_secrets_toml)

from modules.app_core import get_connection
from modules.promemoria_aderenza import processa_promemoria_aderenza

if __name__ == "__main__":
    conn = get_connection()
    email_studio = os.environ.get("EMAIL_STUDIO") or "info@pnev.it"
    dry_run = os.environ.get("DRY_RUN") == "1"
    try:
        soglia = int(os.environ.get("SOGLIA", "70"))
    except ValueError:
        soglia = 70

    report = processa_promemoria_aderenza(
        conn, dry_run=dry_run, email_studio=email_studio, soglia=soglia)

    for voce in report["dettaglio"]:
        print(f"  {voce['tipo']:13} {voce['paziente']:30} {voce['esito']}")
    for err in report["errori"]:
        print(f"  ERRORE: {err}")

    print(f"CRON_RESULT candidati={report['candidati']} "
          f"inviate={report['email_inviate']} "
          f"fallite={report['email_fallite']} "
          f"saltati_cooldown={report['saltati_cooldown']}"
          f"{' (DRY RUN)' if dry_run else ''}")
