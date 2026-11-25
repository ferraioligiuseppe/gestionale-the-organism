#!/usr/bin/env bash
# Installa (la prima volta) e aggiorna (le volte successive) il gestionale sul server OVH.
# Lo lancia da solo l'azione «Server OVH: installa e aggiorna»: non serve usarlo a mano.
# Ogni app Streamlit gira come servizio di sistema; Caddy davanti fa HTTPS in automatico.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
APP=/home/ubuntu/app
VENV=/home/ubuntu/venv
DOMINI_FILE=$APP/scripts/server_domini.txt

echo "== 1. Programmi di base"
if ! command -v caddy >/dev/null 2>&1; then
  sudo apt-get update -y
  sudo apt-get install -y python3-venv python3-dev build-essential libpq-dev curl gnupg ufw \
       debian-keyring debian-archive-keyring apt-transport-https
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --batch --yes --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list >/dev/null
  sudo apt-get update -y
  sudo apt-get install -y caddy
fi
if [ -f "$APP/packages.txt" ]; then
  grep -v '^\s*#' "$APP/packages.txt" | grep -v '^\s*$' | xargs -r sudo apt-get install -y || true
fi

echo "== 2. Librerie Python"
[ -d "$VENV" ] || python3 -m venv "$VENV"
"$VENV/bin/pip" install -q --upgrade pip
"$VENV/bin/pip" install -q -r "$APP/requirements.txt"

echo "== 3. Servizi"
crea_servizio() {
  local nome=$1 file=$2 porta=$3
  sudo tee /etc/systemd/system/$nome.service >/dev/null <<EOF
[Unit]
Description=Streamlit $nome
After=network-online.target

[Service]
User=ubuntu
WorkingDirectory=$APP
Environment=PYTHONUNBUFFERED=1
ExecStart=$VENV/bin/streamlit run $file --server.port $porta --server.address 127.0.0.1 --server.headless true --browser.gatherUsageStats false
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
}
crea_servizio gestionale app.py 8501
crea_servizio iscrizioni apps/pnev_pubblico.py 8502

# PNEV Academy · Ricerca scuola: servizio dati che riceve le partite dai giochi (porta 8504)
sudo tee /etc/systemd/system/ricerca-api.service >/dev/null <<SERVIZIO
[Unit]
Description=PNEV Academy - servizio dati ricerca scuola
After=network-online.target

[Service]
User=ubuntu
WorkingDirectory=$APP
Environment=PYTHONUNBUFFERED=1
ExecStart=$VENV/bin/uvicorn apps.ricerca_api:app --host 127.0.0.1 --port 8504 --proxy-headers --forwarded-allow-ips 127.0.0.1
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
SERVIZIO

# Giochi PNEV: file statici serviti direttamente da Caddy (veloci, niente WordPress)
GIOCHI_DIR=/var/www/pnev-giochi
sudo mkdir -p "$GIOCHI_DIR"
sudo rsync -a --delete "$APP/static_giochi/" "$GIOCHI_DIR/"
sudo chmod -R a+rX "$GIOCHI_DIR"

echo "== 3b. Oculistica (solo se configurata)"
# Script a parte: se qualcosa non va l'oculistica resta spenta e il gestionale prosegue.
bash "$APP/scripts/server_oculistica.sh" </dev/null \
  || echo "ATTENZIONE: oculistica non avviata (vedi sopra). Il gestionale non è toccato."

echo "== 4. Indirizzi e HTTPS (Caddy)"
IPD=$(echo "$SERVER_IP" | tr . -)
{
  # indirizzi provvisori, funzionano subito senza toccare i DNS
  printf 'gestionale.%s.sslip.io {\n  reverse_proxy 127.0.0.1:8501\n}\n' "$IPD"
  printf 'iscrizioni.%s.sslip.io {\n  reverse_proxy 127.0.0.1:8502\n}\n' "$IPD"
  printf 'dati.%s.sslip.io {\n  reverse_proxy 127.0.0.1:8504\n}\n' "$IPD"
  printf 'giochi.%s.sslip.io {\n  root * %s\n  encode gzip\n  header Cache-Control "public, max-age=3600"\n  file_server\n}\n' "$IPD" "$GIOCHI_DIR"
  if [ -f /home/ubuntu/oculistica.attiva ]; then
    printf 'oculistica.%s.sslip.io {\n  reverse_proxy 127.0.0.1:8503\n}\n' "$IPD"
  fi
  # domini veri, quando i DNS puntano qui: righe «dominio porta» in scripts/server_domini.txt
  if [ -f "$DOMINI_FILE" ]; then
    { grep -v '^\s*#' "$DOMINI_FILE" || true; } | while read -r dominio porta; do
      if [ "${porta:-}" = "8503" ] && [ ! -f /home/ubuntu/oculistica.attiva ]; then continue; fi
      if [ "${porta:-}" = "giochi" ] && [ -n "${dominio:-}" ]; then
        printf '%s {\n  root * %s\n  encode gzip\n  header Cache-Control "public, max-age=3600"\n  file_server\n}\n' "$dominio" "$GIOCHI_DIR"
      elif [ -n "${dominio:-}" ] && [ -n "${porta:-}" ]; then
        printf '%s {\n  reverse_proxy 127.0.0.1:%s\n}\n' "$dominio" "$porta"
      fi
    done
  fi
} | sudo tee /etc/caddy/Caddyfile >/dev/null

echo "== 5. Porte aperte: solo SSH, 80 e 443"
sudo ufw allow OpenSSH >/dev/null
sudo ufw allow 80/tcp >/dev/null
sudo ufw allow 443/tcp >/dev/null
sudo ufw --force enable >/dev/null

echo "== 6. Avvio"
sudo systemctl daemon-reload
sudo systemctl enable gestionale iscrizioni ricerca-api caddy >/dev/null 2>&1
sudo systemctl restart gestionale iscrizioni
sudo systemctl restart ricerca-api || echo "ATTENZIONE: servizio dati ricerca non avviato. Il gestionale non è toccato."
sudo systemctl reload caddy || sudo systemctl restart caddy
sleep 8
for s in gestionale iscrizioni ricerca-api caddy; do
  printf '%-12s %s\n' "$s" "$(systemctl is-active $s)"
done
for p in 8501 8502; do
  printf 'porta %s → HTTP %s\n' "$p" "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:$p/_stcore/health || echo errore)"
done
printf 'porta 8504 (dati ricerca) → HTTP %s\n' "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8504/salute || echo errore)"
echo "Indirizzi provvisori:"
echo "  https://giochi.$IPD.sslip.io/classe.html"
echo "  https://dati.$IPD.sslip.io/salute"
echo "  https://gestionale.$IPD.sslip.io"
echo "  https://iscrizioni.$IPD.sslip.io"
if [ -f /home/ubuntu/oculistica.attiva ]; then
  printf 'oculistica   %s · porta 8503 → HTTP %s\n' "$(systemctl is-active oculistica)" \
    "$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8503/_stcore/health || echo errore)"
  echo "  https://oculistica.$IPD.sslip.io   (chiede la password)"
fi
