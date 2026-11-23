#!/usr/bin/env bash
# Accende (o spegne) il gestionale oculistica sul server OVH. Lo chiama server_ovh.sh.
#
# - Parte SOLO se ci sono le sue impostazioni (segreti OCULISTICA_SECRETS e OCULISTICA_PASSWORD
#   su GitHub). Senza, resta spento e non succede niente.
# - Usa le stesse librerie del gestionale: non installa nulla.
# - Se il database non risponde o l'app non parte, la spegne e lo dice. Il gestionale non è toccato.
# - Quando è accesa e sana lascia il file $FLAG: server_ovh.sh lo legge per dare l'indirizzo.
set -euo pipefail
APP=${APP:-/home/ubuntu/app}
VENV=${VENV:-/home/ubuntu/venv}
UNITA=${UNITA:-/etc/systemd/system}
FLAG=${FLAG:-/home/ubuntu/oculistica.attiva}
PORTA=8503
ENVF=$APP/.streamlit/oculistica.env
SEGRETI=$APP/.streamlit/oculistica_secrets.toml

spegni() {
  rm -f "$FLAG"
  if [ -f "$UNITA/oculistica.service" ]; then
    sudo systemctl disable --now oculistica >/dev/null 2>&1 || true
  fi
}

trap 'spegni' ERR      # qualunque intoppo: spenta, mai «mezza accesa»

if [ ! -s "$ENVF" ] || [ ! -s "$SEGRETI" ]; then
  echo "Oculistica: non configurata, resta spenta."
  spegni
  exit 0
fi
chmod 600 "$ENVF" "$SEGRETI"

if ! "$VENV/bin/python" "$APP/scripts/oculistica_env.py" prova-db "$ENVF"; then
  spegni
  exit 1
fi

sudo tee "$UNITA/oculistica.service" >/dev/null <<UNIT
[Unit]
Description=Streamlit oculistica
After=network-online.target

[Service]
User=ubuntu
WorkingDirectory=$APP
Environment=PYTHONUNBUFFERED=1
EnvironmentFile=$ENVF
ExecStart=$VENV/bin/streamlit run vision_manager/app_ovh.py --server.port $PORTA --server.address 127.0.0.1 --server.headless true --browser.gatherUsageStats false --secrets.files $SEGRETI
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
UNIT
sudo systemctl daemon-reload
sudo systemctl enable oculistica >/dev/null 2>&1
sudo systemctl restart oculistica

sana=no
for _ in $(seq 1 20); do
  sleep 2
  if [ "$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$PORTA/_stcore/health" || true)" = "200" ]; then
    sana=si
    break
  fi
done
if [ "$sana" != "si" ]; then
  echo "ERRORE: l'oculistica non è partita. Ultime righe del registro:"
  sudo journalctl -u oculistica -n 25 --no-pager 2>/dev/null | sed 's/postgres[a-z]*:\/\/[^ ]*/[indirizzo database nascosto]/g' || true
  spegni
  exit 1
fi
touch "$FLAG"
echo "Oculistica: accesa."
