#!/usr/bin/env python3
"""Cek posisi servo 1 dan servo 2 lewat pigpiod.

Servo MG996R tidak punya sensor posisi. Posisi di sini adalah perintah terakhir
yang dikirim ke servo (lebar pulsa), diubah ke sudut dengan pemetaan yang sama
seperti program utama: 1000 µs = -90°, 1500 µs = 0°, 2000 µs = +90°.

    python3 scripts/cek_servo.py            tampilkan posisi sekarang sekali
    python3 scripts/cek_servo.py live       tampilkan terus, Ctrl+C untuk berhenti
    python3 scripts/cek_servo.py atur       gerakkan servo dengan ketikan

Mode "status" dan "live" tidak menggerakkan servo, jadi aman dipakai saat
trash2trace jalan. Mode "atur" menggerakkan servo, hentikan trash2trace dulu:
    sudo systemctl stop trash2trace
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from servo.pins import SERVO_PIN, SERVO_TILT_PIN
from trash2trace.servo_driver import StableServo, connect_pigpio

SERVOS = {
    1: ("Servo 1 (putar)", SERVO_PIN, 12),
    2: ("Servo 2 (miring)", SERVO_TILT_PIN, 33),
}
MIN_US, MAX_US = 1000, 2000
MIN_ANGLE, MAX_ANGLE = -90, 90


def us_to_angle(us: int) -> float:
    return MIN_ANGLE + (us - MIN_US) / (MAX_US - MIN_US) * (MAX_ANGLE - MIN_ANGLE)


def describe(pi, number: int) -> str:
    name, pin, physical = SERVOS[number]
    us = pi.get_servo_pulsewidth(pin)
    if us == 0:
        state = "lepas (tidak ada sinyal)"
    else:
        state = f"{us_to_angle(us):+6.1f}°  ({us} µs)"
    return f"{name}  GPIO{pin} / pin {physical}:  {state}"


def show_status(pi) -> None:
    for number in SERVOS:
        print(describe(pi, number))


def run_live(pi) -> None:
    print("Ctrl+C untuk berhenti.")
    try:
        while True:
            parts = [f"{n}: {describe(pi, n).split(':  ', 1)[1]}" for n in SERVOS]
            print("\r" + "     ".join(parts) + "        ", end="", flush=True)
            time.sleep(0.5)
    except KeyboardInterrupt:
        print()


def run_atur(pi) -> None:
    servos = {n: StableServo(pi, pin) for n, (_, pin, _) in SERVOS.items()}
    print("Ketik: '<servo> <sudut>'  contoh: 1 45   atau  2 -30")
    print("       tengah = kedua servo ke 0°,  status,  lepas = matikan sinyal,  q = keluar")
    try:
        while True:
            try:
                text = input("> ").strip().lower()
            except EOFError:
                break
            if text in ("q", "keluar"):
                break
            if text == "status":
                show_status(pi)
            elif text == "tengah":
                for servo in servos.values():
                    servo.angle = 0
                show_status(pi)
            elif text == "lepas":
                for servo in servos.values():
                    servo.detach()
                show_status(pi)
            else:
                parts = text.split()
                try:
                    number, angle = int(parts[0]), float(parts[1])
                    servo = servos[number]
                except (ValueError, IndexError, KeyError):
                    print("Tidak dikenal. Contoh: 1 45")
                    continue
                servo.angle = angle
                time.sleep(0.8)
                print(describe(pi, number))
    finally:
        for servo in servos.values():
            servo.detach()


def main() -> int:
    parser = argparse.ArgumentParser(description="Cek posisi servo 1 dan 2.")
    parser.add_argument("mode", nargs="?", default="status", choices=("status", "live", "atur"))
    args = parser.parse_args()
    pi = connect_pigpio()
    if pi is None:
        return 1
    try:
        {"status": show_status, "live": run_live, "atur": run_atur}[args.mode](pi)
    finally:
        pi.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
