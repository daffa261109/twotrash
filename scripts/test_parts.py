#!/usr/bin/env python3
"""Uji satu komponen. Hentikan trash2trace dulu supaya GPIO tidak berebut.

    python3 scripts/test_parts.py buzzer
    python3 scripts/test_parts.py hc
    python3 scripts/test_parts.py led
    python3 scripts/test_parts.py lamp
    python3 scripts/test_parts.py servo
    python3 scripts/test_parts.py oled
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from gpiozero import AngularServo, Buzzer, Device, DistanceSensor, LED

from servo.pins import (
    BUZZER_PIN,
    ECHO_PIN,
    ILLUMINATION_PIN,
    LED_GREEN_PIN,
    LED_RED_PIN,
    SERVO_PIN,
    TRIG_PIN,
)


def test_buzzer() -> None:
    print("Buzzer, GPIO 5 / pin 29. Bunyi 3 kali.")
    buzzer = Buzzer(BUZZER_PIN)
    try:
        for number in range(1, 4):
            print(f"  bunyi {number}")
            buzzer.on()
            time.sleep(0.5)
            buzzer.off()
            time.sleep(0.4)
    finally:
        buzzer.off()
        buzzer.close()
    print("Selesai.")


def test_hc() -> None:
    print("HC-SR04, TRIG GPIO 17 / pin 11, ECHO GPIO 27 / pin 13. Ctrl+C berhenti.")
    print("Kalau ada barang, jarak dibaca dua kali. Buzzer bunyi sekali jika bukan di bawah 4,5 cm.")
    sensor = DistanceSensor(
        echo=ECHO_PIN,
        trigger=TRIG_PIN,
        max_distance=2.0,
        queue_len=5,
        partial=True,
    )
    buzzer = Buzzer(BUZZER_PIN)
    print("Menunggu barang.")
    try:
        while True:
            jarak_cm = sensor.distance * 100
            if jarak_cm < 1 or jarak_cm > 6:
                time.sleep(0.05)
                continue
            time.sleep(0.12)
            kedua = sensor.distance * 100
            print(f"barang: {jarak_cm:.1f} cm, {kedua:.1f} cm")
            if jarak_cm >= 4.5 or kedua >= 4.5:
                print("  buzzer")
                buzzer.on()
                time.sleep(0.2)
                buzzer.off()
            while sensor.distance * 100 <= 10:
                time.sleep(0.08)
            print("Menunggu barang.")
    except KeyboardInterrupt:
        print()
    finally:
        buzzer.off()
        buzzer.close()
        sensor.close()


def test_led() -> None:
    print("LED hijau GPIO 22 / pin 15, lalu LED merah GPIO 23 / pin 16.")
    green = LED(LED_GREEN_PIN)
    red = LED(LED_RED_PIN)
    try:
        for name, led in (("hijau", green), ("merah", red)):
            print(f"  {name} nyala")
            led.on()
            time.sleep(1.2)
            led.off()
            time.sleep(0.3)
    finally:
        green.off()
        red.off()
        green.close()
        red.close()
    print("Selesai.")


def test_lamp() -> None:
    print("Lampu penerangan, GPIO 24 / pin 18. Nyala 3 detik.")
    lamp = LED(ILLUMINATION_PIN)
    try:
        lamp.on()
        time.sleep(3)
    finally:
        lamp.off()
        lamp.close()
    print("Selesai.")


def test_servo() -> None:
    print("Servo MG996R, sinyal GPIO 18 / pin 12. Tengah, kiri, kanan, lalu tengah.")
    try:
        from gpiozero.pins.pigpio import PiGPIOFactory

        Device.pin_factory = PiGPIOFactory()
    except Exception as exc:
        print(f"pigpio tidak aktif, servo bisa sedikit bergetar: {exc}")
    servo = AngularServo(
        SERVO_PIN,
        min_angle=-90,
        max_angle=90,
        initial_angle=0,
        min_pulse_width=0.001,
        max_pulse_width=0.002,
    )
    try:
        for label, angle in (
            ("tengah", 0),
            ("kiri", -60),
            ("tengah", 0),
            ("kanan", 60),
            ("tengah", 0),
        ):
            print(f"  {label} {angle:+d}°")
            servo.angle = angle
            time.sleep(1.2)
    finally:
        servo.detach()
        servo.close()
    print("Selesai.")


def test_oled() -> None:
    from trash2trace.display import Display

    print("OLED SSD1306, SDA GPIO 2 / pin 3, SCL GPIO 3 / pin 5, alamat 0x3C.")
    display = Display()
    if display._panel is None:
        print("Layar tidak menyala. Pasang library, lalu uji lagi:")
        print("  sudo apt install python3-pil i2c-tools")
        print("  python3 -m pip install --break-system-packages adafruit-circuitpython-ssd1306 adafruit-blinka")
        return
    try:
        for lines in (("OLED", "0x3C", "nyala"), ("TRASH2TRACE", "FLAP", "siap")):
            print(f"  tampil {' / '.join(lines)}")
            display.show(*lines)
            time.sleep(2)
    finally:
        display.clear()
    print("Selesai.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Uji satu komponen.")
    parser.add_argument("bagian", choices=("buzzer", "hc", "led", "lamp", "servo", "oled"))
    args = parser.parse_args()
    {
        "buzzer": test_buzzer,
        "hc": test_hc,
        "led": test_led,
        "lamp": test_lamp,
        "servo": test_servo,
        "oled": test_oled,
    }[args.bagian]()


if __name__ == "__main__":
    main()
