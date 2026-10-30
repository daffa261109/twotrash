#!/bin/bash
# Desktop kadang belum siap saat Pi baru dinyalakan. Tunggu sebentar, lalu lanjut.
runtime="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
for _ in $(seq 1 90); do
  if [[ -S /tmp/.X11-unix/X0 ]] || [[ -S "${runtime}/wayland-0" ]] || [[ -S "${runtime}/wayland-1" ]]; then
    exit 0
  fi
  sleep 1
done
exit 0
