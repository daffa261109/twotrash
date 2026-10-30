#!/bin/bash
# Pasang sekali di setiap Pi. Setelah itu pemilah menyala sendiri tiap boot.
set -euo pipefail

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Jalankan: sudo ./install.sh"
  exit 1
fi

ROOT="$(cd "$(dirname "$0")" && pwd)"
RUN_USER="${SUDO_USER:-pi}"
RUN_UID="$(id -u "$RUN_USER")"

apt-get update
apt-get install -y pigpio python3-gpiozero python3-pigpio python3-opencv python3-picamera2 python3-pil python3-pil.imagetk python3-tk libatomic1
ATOMIC=""
if [[ -e /usr/lib/arm-linux-gnueabihf/libatomic.so.1 ]]; then
  ATOMIC=/usr/lib/arm-linux-gnueabihf/libatomic.so.1
elif [[ -e /usr/lib/aarch64-linux-gnu/libatomic.so.1 ]]; then
  ATOMIC=/usr/lib/aarch64-linux-gnu/libatomic.so.1
fi
systemctl enable --now pigpiod
raspi-config nonint do_i2c 0 || true
usermod -aG video,i2c,gpio "$RUN_USER"

cat > /etc/systemd/system/trash2trace.service << EOF
[Unit]
Description=TRASH2TRACE pemilah sampah
After=pigpiod.service
Wants=pigpiod.service

[Service]
Type=simple
User=${RUN_USER}
WorkingDirectory=${ROOT}
ExecStartPre=/bin/bash ${ROOT}/scripts/tunggu_layar.sh
ExecStart=/usr/bin/python3 -m trash2trace
Restart=always
RestartSec=8
StartLimitIntervalSec=0
Environment=PYTHONUNBUFFERED=1
Environment=DISPLAY=:0
Environment=XAUTHORITY=/home/${RUN_USER}/.Xauthority
Environment=XDG_RUNTIME_DIR=/run/user/${RUN_UID}
${ATOMIC:+Environment=LD_PRELOAD=${ATOMIC}}
EnvironmentFile=-${ROOT}/.env

[Install]
WantedBy=graphical.target
EOF

systemctl daemon-reload
systemctl disable trash2trace.service || true
systemctl enable trash2trace.service
systemctl restart trash2trace.service || true
bash "${ROOT}/scripts/buzzer_mati.sh"
if [[ ! -f "${ROOT}/.env" ]]; then
  cp "${ROOT}/.env.example" "${ROOT}/.env"
  chown "${RUN_USER}" "${ROOT}/.env"
  chmod 600 "${ROOT}/.env"
fi

echo "Terpasang untuk ${RUN_USER} di ${ROOT}."
echo "Isi station.txt (flap1 atau flap2) dan .env, lalu reboot. Program menyala sendiri."
