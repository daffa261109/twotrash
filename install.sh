#!/bin/bash
# Pasang sekali di setiap Pi. Setelah itu pemilah menyala sendiri tiap boot.
set -euo pipefail

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Jalankan: sudo ./install.sh"
  exit 1
fi

ROOT="$(cd "$(dirname "$0")" && pwd)"
RUN_USER="${SUDO_USER:-pi}"

apt-get update
apt-get install -y python3-gpiozero python3-pigpio python3-opencv python3-picamera2 python3-pil python3-tflite-runtime || apt-get install -y python3-gpiozero python3-pigpio python3-opencv python3-picamera2 python3-pil
systemctl enable --now pigpiod
raspi-config nonint do_i2c 0 || true
usermod -aG video,i2c,gpio "$RUN_USER"

cat > /etc/systemd/system/trash2trace.service << EOF
[Unit]
Description=TRASH2TRACE pemilah sampah
After=network.target pigpiod.service
Wants=pigpiod.service

[Service]
Type=simple
User=${RUN_USER}
WorkingDirectory=${ROOT}
ExecStartPre=/bin/sleep 8
ExecStart=/usr/bin/python3 -m trash2trace
Restart=on-failure
RestartSec=10
Environment=PYTHONUNBUFFERED=1
EnvironmentFile=-${ROOT}/.env

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable trash2trace.service
if [[ ! -f "${ROOT}/.env" ]]; then
  cp "${ROOT}/.env.example" "${ROOT}/.env"
  chown "${RUN_USER}" "${ROOT}/.env"
  chmod 600 "${ROOT}/.env"
fi

echo "Terpasang untuk ${RUN_USER} di ${ROOT}."
echo "Isi station.txt (flap1 atau flap2) dan .env, lalu reboot. Program menyala sendiri."
