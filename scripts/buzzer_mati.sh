#!/bin/bash
# GPIO 5 tertarik tinggi saat listrik masuk, jadi buzzer bunyi sampai program jalan.
# Baris gpio= membuat pin rendah sejak bootloader. Service menutup sisa jeda setelah kernel naik.
set -euo pipefail

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Jalankan: sudo ./scripts/buzzer_mati.sh"
  exit 1
fi

BOOT=""
if [[ -f /boot/firmware/config.txt ]]; then
  BOOT=/boot/firmware/config.txt
elif [[ -f /boot/config.txt ]]; then
  BOOT=/boot/config.txt
fi
if [[ -n "$BOOT" ]] && ! grep -q '^gpio=5=op,dl$' "$BOOT"; then
  printf '\n# Buzzer GPIO 5 rendah sejak boot.\ngpio=5=op,dl\n' >> "$BOOT"
  echo "Ditambah di $BOOT"
fi

cat > /etc/systemd/system/buzzer-mati.service << 'EOF'
[Unit]
Description=Matikan buzzer GPIO 5 saat boot
DefaultDependencies=no
After=sysinit.target
Before=basic.target

[Service]
Type=oneshot
ExecStart=/bin/sh -c 'if command -v pinctrl >/dev/null; then pinctrl set 5 op dl; elif command -v raspi-gpio >/dev/null; then raspi-gpio set 5 op dl; else python3 -c "from gpiozero import Buzzer; b=Buzzer(5, initial_value=False); b.off(); b.close()"; fi'
RemainAfterExit=yes

[Install]
WantedBy=sysinit.target
EOF

systemctl daemon-reload
systemctl enable buzzer-mati.service
if command -v pinctrl >/dev/null; then
  pinctrl set 5 op dl
elif command -v raspi-gpio >/dev/null; then
  raspi-gpio set 5 op dl
else
  python3 -c 'from gpiozero import Buzzer; b=Buzzer(5, initial_value=False); b.off(); b.close()'
fi
echo "Buzzer dimatikan. Reboot sekali supaya pin langsung rendah saat Pi menyala."
