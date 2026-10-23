#!/usr/bin/env python3
"""Uji satu komponen. Hentikan trash2trace dulu supaya GPIO tidak berebut.

    python3 scripts/test_parts.py buzzer
    python3 scripts/test_parts.py hc
    python3 scripts/test_parts.py led
    python3 scripts/test_parts.py lamp
    python3 scripts/test_parts.py servo1
    python3 scripts/test_parts.py servo1_kanan90
    python3 scripts/test_parts.py servo2
    python3 scripts/test_parts.py oled
    sudo python3 scripts/test_parts.py ring
    sudo python3 scripts/test_parts.py camera
    sudo python3 scripts/test_parts.py api
    sudo python3 scripts/test_parts.py cek
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from gpiozero import Buzzer, Device, DistanceSensor, LED

from trash2trace.servo_driver import StableServo, connect_pigpio
from servo.pins import (
    BUZZER_PIN,
    ECHO_PIN,
    ILLUMINATION_PIN,
    LED_GREEN_PIN,
    LED_RED_PIN,
    RING_DIN_PIN,
    SERVO_PIN,
    SERVO_TILT_PIN,
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


def _test_servo(
    title: str, pin: int, physical: int, steps: tuple[tuple[str, int], ...], hold_s: float = 1.5
) -> None:
    print(f"{title}, sinyal GPIO {pin} / pin {physical}. Catu 5 V bawah harus nyala.")
    print("Hanya servo ini yang digerakkan. Servo lain diam.")
    pi = connect_pigpio()
    if pi is None:
        return
    servo = StableServo(pi, pin)
    try:
        for label, angle in steps:
            print(f"  {label} {angle:+d}°")
            servo.angle = angle
            time.sleep(hold_s)
    finally:
        servo.detach()
        pi.stop()
    print("Selesai.")


def test_servo1() -> None:
    _test_servo(
        "Servo 1 (putar 360°, pemilih jalur)",
        SERVO_PIN,
        12,
        (("tengah", 0), ("kiri", -60), ("tengah", 0), ("kanan", 60), ("tengah", 0)),
    )


def test_servo1_kanan90() -> None:
    _test_servo(
        "Servo 1 (putar), kanan 90°",
        SERVO_PIN,
        12,
        (("tengah", 0), ("kanan", 90), ("tengah", 0)),
        hold_s=3.0,
    )


def test_servo2() -> None:
    _test_servo(
        "Servo 2 (miring atas-bawah, buang sampah)",
        SERVO_TILT_PIN,
        33,
        (("rata", 0), ("miring atas", 45), ("rata", 0), ("miring bawah", -45), ("rata", 0)),
    )


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


RING_LED_COUNT = 12
RING_BRIGHTNESS = 40  # 0 sampai 255. Rendah supaya catu dan mata aman.


def test_ring() -> None:
    print(f"Cincin WS2812 {RING_LED_COUNT} LED, data GPIO {RING_DIN_PIN} / pin 40.")
    if os.geteuid() != 0:
        print("Butuh root. Jalankan dengan sudo:")
        print("  sudo python3 scripts/test_parts.py ring")
        return
    try:
        from rpi_ws281x import Color, PixelStrip
    except ImportError:
        print("Library rpi_ws281x belum ada. Pasang dulu:")
        print("  sudo apt install python3-dev gcc")
        print("  sudo python3 -m pip install --break-system-packages rpi-ws281x")
        return
    print("Kalau pigpiod jalan, hentikan dulu: sudo systemctl stop pigpiod")
    strip = PixelStrip(RING_LED_COUNT, RING_DIN_PIN, 800000, 10, False, RING_BRIGHTNESS, 0)
    strip.begin()

    def isi(color) -> None:
        for index in range(RING_LED_COUNT):
            strip.setPixelColor(index, color)
        strip.show()

    try:
        for name, color in (
            ("merah", Color(255, 0, 0)),
            ("hijau", Color(0, 255, 0)),
            ("biru", Color(0, 0, 255)),
            ("putih", Color(255, 255, 255)),
        ):
            print(f"  semua {name}")
            isi(color)
            time.sleep(1.2)
        print("  satu titik berputar")
        for _ in range(2):
            for index in range(RING_LED_COUNT):
                isi(Color(0, 0, 0))
                strip.setPixelColor(index, Color(255, 255, 255))
                strip.show()
                time.sleep(0.1)
    finally:
        isi(Color(0, 0, 0))
    print("Selesai.")


def test_camera() -> Path | None:
    from datetime import datetime

    from picamera2 import Picamera2

    from trash2trace.ring import Ring
    from trash2trace.settings import CAPTURE_DIR

    print("Kamera Pi dengan cincin LED putih. Satu foto disimpan di captures/.")
    ring = None
    try:
        ring = Ring()
        ring.white()
        print("  cincin putih nyala")
    except Exception as exc:
        print(f"  cincin tidak menyala ({exc}). Foto tetap diambil tanpa cincin.")
        print("  Untuk cincin: sudo systemctl stop pigpiod, lalu sudo python3 scripts/test_parts.py camera")

    path = None
    camera = Picamera2()
    try:
        camera.configure(camera.create_still_configuration(main={"size": (1280, 960)}))
        camera.start()
        try:
            camera.set_controls({"AwbEnable": True, "AwbMode": 4})
        except Exception as exc:
            print(f"  [WARN] Warna kamera: {exc}")
        time.sleep(2.0)
        CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
        path = CAPTURE_DIR / f"test-kamera-{datetime.now():%Y%m%d-%H%M%S}.jpg"
        camera.capture_file(str(path))
        print(f"  foto: {path}")
        print(f"  ambil ke Mac: scp zero@hosttrashid.local:{path} ~/Desktop/")
    finally:
        camera.stop()
        camera.close()
        if ring is not None:
            ring.close()
    print("Selesai.")
    return path


def test_api(photo: Path | None = None) -> bool:
    import json
    import urllib.error
    import urllib.request

    from trash2trace.llm import LlmVision
    from trash2trace.settings import CAPTURE_DIR, load_llm_config

    print("API Sumopod (LLM pembaca gambar). Butuh internet dan LLM_API_KEY di file .env.")
    config = load_llm_config()
    key = config.api_key
    print(f"  endpoint: {config.endpoint}")
    print(f"  model:    {config.model}")
    print(f"  kunci:    ...{key[-4:]}" if len(key) > 4 else "  kunci:    (terlalu pendek)")

    request = urllib.request.Request(
        config.endpoint.rstrip("/") + "/models",
        headers={"Authorization": f"Bearer {key}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            models = [item.get("id") for item in json.loads(response.read()).get("data", [])]
        print(f"  koneksi dan kunci OK, {len(models)} model tersedia")
        if config.model not in models:
            print(f"  [WARN] model {config.model} tidak ada di daftar Sumopod")
    except urllib.error.HTTPError as exc:
        print(f"  GAGAL: server menjawab {exc.code}. Kunci salah atau akun tidak aktif.")
        return False
    except Exception as exc:
        print(f"  GAGAL terhubung: {exc}")
        return False

    if photo is None:
        photos = sorted(CAPTURE_DIR.glob("*.jpg"), key=lambda item: item.stat().st_mtime)
        if not photos:
            print("  Belum ada foto di captures/. Jalankan dulu: sudo python3 scripts/test_parts.py camera")
            return False
        photo = photos[-1]
    print(f"  foto: {photo.name}")

    import cv2

    frame = cv2.imread(str(photo))
    if frame is None:
        print("  GAGAL: foto tidak terbaca")
        return False
    height, width = frame.shape[:2]
    if width > 640:
        frame = cv2.resize(frame, (640, round(height * 640 / width)))
    ok, jpeg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
    if not ok:
        print("  GAGAL: foto tidak bisa dikecilkan")
        return False

    started = time.monotonic()
    try:
        label, confidence = LlmVision(config).classify(jpeg.tobytes())
    except Exception as exc:
        print(f"  GAGAL klasifikasi: {exc}")
        return False
    print(f"  hasil: {label}  yakin={confidence:.2f}  ({time.monotonic() - started:.1f} detik)")
    print("Selesai.")
    return True


def test_cek() -> None:
    """Cincin LED, kamera, lalu API Sumopod dengan foto dari kamera."""
    results: dict[str, str] = {}
    photo = None
    for name, action in (("cincin LED", test_ring), ("kamera", test_camera)):
        print(f"\n=== {name} ===")
        try:
            outcome = action()
            results[name] = "dilewati, butuh sudo" if name == "cincin LED" and os.geteuid() != 0 else "jalan"
            if name == "kamera":
                photo = outcome
        except BaseException as exc:
            results[name] = f"GAGAL: {exc}"
            print(f"  GAGAL: {exc}")
    print("\n=== API Sumopod ===")
    try:
        results["API Sumopod"] = "OK" if test_api(photo) else "GAGAL"
    except BaseException as exc:
        results["API Sumopod"] = f"GAGAL: {exc}"
        print(f"  GAGAL: {exc}")
    print("\nRingkasan:")
    for name, state in results.items():
        print(f"  {name}: {state}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Uji satu komponen.")
    parser.add_argument("bagian", choices=("buzzer", "hc", "led", "lamp", "servo", "servo1", "servo1_kanan90", "servo2", "oled", "ring", "camera", "api", "cek"))
    args = parser.parse_args()
    {
        "buzzer": test_buzzer,
        "hc": test_hc,
        "led": test_led,
        "lamp": test_lamp,
        "servo": test_servo1,
        "servo1": test_servo1,
        "servo1_kanan90": test_servo1_kanan90,
        "servo2": test_servo2,
        "oled": test_oled,
        "ring": test_ring,
        "camera": test_camera,
        "api": test_api,
        "cek": test_cek,
    }[args.bagian]()


if __name__ == "__main__":
    main()
