#!/usr/bin/env python3
"""Uji satu komponen. Hentikan trash2trace dulu supaya GPIO tidak berebut.

    python3 scripts/test_parts.py buzzer
    python3 scripts/test_parts.py hc
    python3 scripts/test_parts.py ir
    python3 scripts/test_parts.py led
    python3 scripts/test_parts.py lamp
    python3 scripts/test_parts.py servo1
    python3 scripts/test_parts.py servo1_kanan90
    python3 scripts/test_parts.py servo2
    python3 scripts/test_parts.py urut_kiri [--sudut 45] [--turun -45]
    python3 scripts/test_parts.py urut_kanan [--sudut 45] [--turun -45]
    python3 scripts/test_parts.py oled
    sudo python3 scripts/test_parts.py ring
    python3 scripts/test_parts.py webcam [--device 0]
    python3 scripts/test_parts.py webcam --live
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

from gpiozero import Buzzer, Device, LED

from trash2trace.servo_driver import StableServo, connect_pigpio, geser, run_sort, sort_plan
from trash2trace.settings import (
    HC_BARANG_MIN_M,
    HC_PENAMPANG_MAX_M,
    HC_PENAMPANG_MIN_M,
    TILT_DOWN_DEG,
    is_barang,
    is_penampang,
)
from servo.pins import (
    BUZZER_PIN,
    ECHO_PIN,
    ILLUMINATION_PIN,
    IR_OUT_PIN,
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


def hc_status(jarak_cm: float) -> str:
    """56–58 cm hanya penampang. Lebih dekat dari itu ada barang."""
    jarak_m = jarak_cm / 100.0
    if is_penampang(jarak_m):
        return "PENAMPANG"
    if is_barang(jarak_m):
        return "ADA BARANG"
    return "LAIN"


def _jarak_hc_cm(pi, timeout_us: int = 26000) -> float | None:
    """Ukur gema dengan jam pigpio (1 µs). Timeout 26 ms mencakup sekitar 400 cm."""
    import pigpio

    pi.set_mode(TRIG_PIN, pigpio.OUTPUT)
    pi.set_mode(ECHO_PIN, pigpio.INPUT)
    pi.write(TRIG_PIN, 0)
    time.sleep(0.0002)
    edges: list[tuple[int, int]] = []

    def _edge(_gpio: int, level: int, tick: int) -> None:
        edges.append((level, tick))

    callback = pi.callback(ECHO_PIN, pigpio.EITHER_EDGE, _edge)
    try:
        fired = pi.get_current_tick()
        pi.gpio_trigger(TRIG_PIN, 10, 1)
        deadline = time.monotonic() + timeout_us / 1_000_000 + 0.02
        while time.monotonic() < deadline:
            rise = fall = None
            for level, tick in edges:
                if pigpio.tickDiff(fired, tick) < 0:
                    continue
                if level == 1 and rise is None:
                    rise = tick
                elif level == 0 and rise is not None:
                    fall = tick
                    break
            if fall is not None:
                return pigpio.tickDiff(rise, fall) * 0.0343 / 2
            time.sleep(0.001)
        return None
    finally:
        callback.cancel()


def test_hc() -> None:
    print("HC-SR04, TRIG GPIO 17 / pin 11, ECHO GPIO 27 / pin 13. Ctrl+C berhenti.")
    print("Jarak diukur sampai sekitar 400 cm. Angka 12–13 cm berarti gema benar-benar dari situ.")
    print(
        f"PENAMPANG {HC_PENAMPANG_MIN_M * 100:.0f}–{HC_PENAMPANG_MAX_M * 100:.0f} cm. "
        f"ADA BARANG {HC_BARANG_MIN_M * 100:.0f} cm sampai di bawah {HC_PENAMPANG_MIN_M * 100:.0f} cm."
    )
    pi = connect_pigpio()
    if pi is None:
        return
    try:
        while True:
            jarak_cm = _jarak_hc_cm(pi)
            if jarak_cm is None:
                print("TIDAK ADA GEMA   lebih dari 400 cm", flush=True)
            else:
                print(f"{hc_status(jarak_cm):10}  posisi {jarak_cm:6.1f} cm", flush=True)
            time.sleep(0.2)
    except KeyboardInterrupt:
        print()
    finally:
        pi.stop()


def test_ir() -> None:
    print("E18-D80NK, GPIO 27 / pin 13. Angka mentah pin: 0 atau 1. Ctrl+C berhenti.")
    pi = connect_pigpio()
    if pi is None:
        return
    import pigpio

    pi.set_mode(IR_OUT_PIN, pigpio.INPUT)
    pi.set_pull_up_down(IR_OUT_PIN, pigpio.PUD_OFF)
    try:
        while True:
            print(pi.read(IR_OUT_PIN), flush=True)
            time.sleep(0.2)
    except KeyboardInterrupt:
        print()
    finally:
        pi.stop()


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
    print("Servo 1 pelan ke -90°, jeda 5 detik, lalu pelan kembali ke 60°. Sinyal GPIO 18 / pin 12.")
    print("Posisi akhir ditahan di 60°. Ctrl+C berhenti. Catu 6 V dinyalakan setelah Pi hidup.")
    pi = connect_pigpio()
    if pi is None:
        return
    servo = StableServo(pi, SERVO_PIN)
    try:
        servo.angle = 60
        print("  dari 60° pelan ke -90°")
        geser(servo, -90)
        print("  -90°, tunggu 5 detik")
        time.sleep(5)
        print("  pelan kembali ke 60°")
        geser(servo, 60)
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nBerhenti di 60°.")
    finally:
        servo.detach()
        pi.stop()


def test_servo1_kanan90() -> None:
    _test_servo(
        "Servo 1 (putar), kanan 90°",
        SERVO_PIN,
        12,
        (("tengah", 0), ("kanan", 90), ("tengah", 0)),
        hold_s=3.0,
    )


def _test_urut(arah: str, sudut: float, turun: float) -> None:
    """Servo 1 memutar, servo 2 turun-naik, lalu servo 1 kembali. Arah kiri = sudut negatif."""
    angle = -abs(sudut) if arah == "kiri" else abs(sudut)
    print(f"Urutan: servo 1 {arah} {abs(sudut):.0f}°, servo 2 turun {turun:+.0f}° lalu naik, servo 1 kembali.")
    print("Hentikan trash2trace dulu: sudo systemctl stop trash2trace")
    pi = connect_pigpio()
    if pi is None:
        return
    servo1 = StableServo(pi, SERVO_PIN)
    servo2 = StableServo(pi, SERVO_TILT_PIN)
    try:
        print("  kedua servo ke tengah, tunggu 1 detik")
        servo1.angle = 0
        servo2.angle = 0
        time.sleep(1.0)
        print(f"  servo 1 {arah} {angle:+.0f}°, tunggu 1 detik")
        servo1.angle = angle
        time.sleep(1.0)
        print(f"  servo 2 turun {turun:+.0f}°, tunggu 2 detik")
        servo2.angle = turun
        time.sleep(2.0)
        print("  servo 2 naik ke tegak (0°), tunggu 1 detik")
        servo2.angle = 0
        time.sleep(1.0)
        print("  servo 1 kembali ke posisi awal (0°)")
        servo1.angle = 0
        time.sleep(1.0)
    finally:
        servo1.detach()
        servo2.detach()
        pi.stop()
    print("Selesai.")


def test_servo2() -> None:
    print("Servo 2 pelan ke 150°, jeda 5 detik, lalu pelan kembali ke 60°. Sinyal GPIO 13 / pin 33.")
    print("Posisi akhir ditahan di 60°. Ctrl+C berhenti. Catu 6 V dinyalakan setelah Pi hidup.")
    pi = connect_pigpio()
    if pi is None:
        return
    servo = StableServo(pi, SERVO_TILT_PIN)
    try:
        servo.angle = 60
        print("  dari 60° pelan ke 150°")
        geser(servo, 150)
        print("  150°, tunggu 5 detik")
        time.sleep(5)
        print("  pelan kembali ke 60°")
        geser(servo, 60)
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nBerhenti di 60°.")
    finally:
        servo.detach()
        pi.stop()


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


def _video_nodes() -> list[tuple[int, str]]:
    root = Path("/sys/class/video4linux")
    if not root.is_dir():
        return []
    nodes = []
    for entry in root.glob("video*"):
        suffix = entry.name.removeprefix("video")
        if not suffix.isdigit():
            continue
        name_file = entry / "name"
        name = name_file.read_text(encoding="utf-8", errors="replace").strip() if name_file.exists() else entry.name
        nodes.append((int(suffix), name))
    return sorted(nodes)


def _open_webcam(cv2, index: int):
    # OpenCV 4.6 menolak CAP_PROP_OPEN_TIMEOUT_MSEC dan lalu menganggap kamera gagal dibuka.
    return cv2.VideoCapture(index, cv2.CAP_V4L2)


def _frame_usable(frame) -> bool:
    if frame is None or getattr(frame, "size", 0) == 0 or getattr(frame, "ndim", 0) != 3:
        return False
    blue, green, red = (float(frame[:, :, channel].mean()) for channel in range(3))
    # Gambar hijau polos: kanal warna gagal, biasanya karena resolusi USB terlalu besar.
    return not (green > 40 and blue < 15 and red < 15)


def _grab_webcam(cv2, camera):
    # XVV-6320S jatuh dari USB jika diminta 1280×720 tanpa MJPEG, dan fotonya hijau.
    camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    camera.set(cv2.CAP_PROP_FPS, 15)
    frame = None
    for _ in range(15):
        ok, grabbed = camera.read()
        if ok and _frame_usable(grabbed):
            frame = grabbed
        time.sleep(0.05)
    return frame


def _usb_lines() -> list[str]:
    import subprocess

    try:
        result = subprocess.run(["lsusb"], capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _select_webcam(cv2, device: int):
    print("Colokkan kabel USB webcam. Tunggu sampai lampunya merah, lalu uji ini membukanya.")
    print("  menunggu sampai 30 detik...")
    found: list[tuple[int, str]] = []
    nodes: list[tuple[int, str]] = []
    deadline = time.monotonic() + 30
    while True:
        found = _video_nodes()
        nodes = [(index, name) for index, name in found if not name.startswith("bcm2835-")]
        if nodes or time.monotonic() >= deadline:
            break
        time.sleep(0.5)
    if nodes:
        for index, name in nodes:
            print(f"  terlihat /dev/video{index}: {name}")
    elif found:
        print("  tidak ada webcam USB. Yang terlihat hanya perangkat internal Pi.")
    else:
        print("  tidak ada /dev/video*")
    order = []
    seen_names = set()
    for index, name in nodes:
        if name in seen_names:
            continue
        seen_names.add(name)
        order.append(index)
    if device in order:
        order.remove(device)
        order.insert(0, device)
    for index in order:
        camera = _open_webcam(cv2, index)
        if not camera.isOpened():
            print(f"  /dev/video{index} tidak terbuka")
            camera.release()
            continue
        print(f"  membuka /dev/video{index} pada 640×480. Lampu webcam seharusnya hijau.")
        if _grab_webcam(cv2, camera) is None:
            print(f"  /dev/video{index} tidak mengirim gambar berwarna")
            camera.release()
            continue
        return camera, index
    print("Webcam belum dipakai, jadi lampunya tetap merah.")
    usb = _usb_lines()
    if usb:
        print("  lsusb:")
        for line in usb:
            print(f"    {line}")
    else:
        print("  lsusb tidak menampilkan perangkat.")
    print("  Kalau nama webcam tidak ada di lsusb, Pi hanya memberi listrik.")
    print("  Coba porta USB lain. Kamera Pi: sudo python3 scripts/test_parts.py camera")
    return None, None


def test_webcam(device: int = 0) -> Path | None:
    from datetime import datetime

    from trash2trace.settings import CAPTURE_DIR

    print("Webcam USB. Lampu merah = ada listrik. Lampu hijau = kamera sedang dibuka.")
    try:
        import cv2
    except ImportError:
        print("OpenCV belum terpasang. Di Pi jalankan:")
        print("  sudo apt install python3-opencv")
        return None
    camera, used = _select_webcam(cv2, device)
    if camera is None or used is None:
        return None
    try:
        ok, frame = camera.read()
        if not ok or not _frame_usable(frame):
            frame = _grab_webcam(cv2, camera)
        if frame is None:
            print("Gambar berwarna tidak terbaca.")
            return None
        time.sleep(2)
        height, width = frame.shape[:2]
        CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
        path = CAPTURE_DIR / f"test-webcam-{datetime.now():%Y%m%d-%H%M%S}.jpg"
        if not cv2.imwrite(str(path), frame):
            print("Gagal menyimpan foto.")
            return None
    finally:
        camera.release()
    print(f"  dipakai: /dev/video{used}")
    print(f"  ukuran: {width}×{height}")
    print(f"  foto: {path}")
    print("Selesai. Lampu kembali merah karena kamera ditutup.")
    return path


_WEBCAM_PAGE = """<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Webcam</title>
  <style>
    body { margin: 0; background: #111; color: #eee; font-family: sans-serif; }
    main { max-width: 720px; margin: 0 auto; padding: 16px; }
    img { width: 100%; background: #000; }
    button {
      margin-top: 16px;
      background: #2f6fed;
      color: white;
      border: 0;
      border-radius: 8px;
      padding: 12px 16px;
      font-size: 16px;
    }
    button:disabled { background: #555; }
    .kind { font-size: 42px; margin: 16px 0 8px; }
    .detail { color: #bbb; margin: 0; }
  </style>
</head>
<body>
  <main>
    <h1>Webcam langsung</h1>
    <img src="/stream" alt="Gambar webcam">
    <button id="proses" type="button">Proses</button>
    <p class="kind" id="kind">Belum diproses</p>
    <p class="detail" id="detail">Ambil gambar yang sedang tampil dan kirim ke twotrash.wbesoft.com.</p>
  </main>
  <script>
    const button = document.getElementById("proses");
    button.addEventListener("click", async () => {
      button.disabled = true;
      document.getElementById("kind").textContent = "Memproses...";
      document.getElementById("detail").textContent = "Foto dikirim ke API";
      try {
        const data = await fetch("/proses", { method: "POST" }).then((response) => response.json());
        document.getElementById("kind").textContent = data.text;
        document.getElementById("detail").textContent = data.detail;
      } catch (error) {
        document.getElementById("kind").textContent = "Gagal";
        document.getElementById("detail").textContent = "Permintaan tidak selesai";
      }
      button.disabled = false;
    });
  </script>
</body>
</html>
""".encode("utf-8")


def test_webcam_live(device: int = 0, port: int = 8081) -> None:
    import json
    import socket
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    print("Webcam USB, gambar langsung di browser.")
    try:
        import cv2
    except ImportError:
        print("OpenCV belum terpasang. Di Pi jalankan:")
        print("  sudo apt install python3-opencv")
        return
    camera, used = _select_webcam(cv2, device)
    if camera is None or used is None:
        return
    lock = threading.Lock()
    motion_lock = threading.Lock()
    labels = {"organic": "ORGANIK", "nonorganic": "NONORGANIK", "other": "LAINNYA"}
    from trash2trace.settings import SERVO1_KEMBALI

    pi = connect_pigpio()
    servo = StableServo(pi, SERVO_PIN)
    servo2 = StableServo(pi, SERVO_TILT_PIN)
    if pi is not None:
        servo.angle = SERVO1_KEMBALI
        servo2.angle = SERVO1_KEMBALI

    def start_servo(label: str) -> str:
        plan = sort_plan(label)
        if pi is None:
            return "servo mati (pigpiod tidak aktif)"
        if plan is None:
            return "servo diam"
        if not motion_lock.acquire(blocking=False):
            return "servo masih bergerak"

        def job() -> None:
            try:
                run_sort(servo, servo2, label)
            finally:
                motion_lock.release()

        threading.Thread(target=job, daemon=True).start()
        return plan

    def jpeg() -> bytes | None:
        with lock:
            ok, frame = camera.read()
        if not ok or frame is None:
            return None
        ok, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
        if not ok:
            return None
        return encoded.tobytes()

    def classify() -> dict[str, str]:
        image = jpeg()
        if image is None:
            return {"text": "Gagal", "detail": "Gambar webcam tidak terbaca"}
        from trash2trace.bridge import BridgeVision
        from trash2trace.settings import load_bridge_config

        started = time.monotonic()
        try:
            reading = BridgeVision(load_bridge_config()).classify(image)
        except BaseException as exc:
            print(f"[WARN] API: {exc}")
            return {"text": "Gagal", "detail": str(exc)[:180]}
        text = labels.get(reading.label, reading.label.upper())
        took = time.monotonic() - started
        print(f"[HASIL] {text} {reading.item} ({took:.1f} detik)")
        motion = start_servo(reading.label)
        detail = f"{took:.1f} detik · {motion} · https://twotrash.wbesoft.com/classify"
        if reading.item:
            detail = f"{reading.item} · {detail}"
        return {"text": text, "detail": detail}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path.startswith("/stream"):
                self.send_response(200)
                self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
                self.end_headers()
                try:
                    while True:
                        image = jpeg()
                        if image is None:
                            time.sleep(0.1)
                            continue
                        self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\n")
                        self.wfile.write(f"Content-Length: {len(image)}\r\n\r\n".encode())
                        self.wfile.write(image)
                        self.wfile.write(b"\r\n")
                        time.sleep(0.1)
                except (BrokenPipeError, ConnectionResetError):
                    return
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(_WEBCAM_PAGE)))
            self.end_headers()
            self.wfile.write(_WEBCAM_PAGE)

        def do_POST(self) -> None:
            if not self.path.startswith("/proses"):
                self.send_error(404)
                return
            body = json.dumps(classify()).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt: str, *args) -> None:
            return

    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    server.daemon_threads = True
    server.block_on_close = False
    name = socket.gethostname()
    print(f"  dipakai: /dev/video{used}")
    print(f"  buka http://{name}.local:{port}")
    print("  Ctrl+C untuk berhenti. Lampu hijau tetap nyala selama halaman terbuka.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nBerhenti.")
    finally:
        server.server_close()
        camera.release()
        if pi is not None:
            servo.detach()
            servo2.detach()
            pi.stop()
        print("Selesai. Lampu kembali merah karena kamera ditutup.")


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
    from trash2trace.bridge import BridgeVision, ping
    from trash2trace.settings import CAPTURE_DIR, load_bridge_config

    print("API bridge twotrash.wbesoft.com. Butuh internet dan API_TOKEN di file .env.")
    config = load_bridge_config()
    print(f"  endpoint: {config.endpoint}")
    print(f"  token:    ...{config.token[-4:]}" if len(config.token) > 4 else "  token:    (terlalu pendek)")
    try:
        status = ping(config)
        print(f"  server merespons: {status}")
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
        reading = BridgeVision(config).classify(jpeg.tobytes())
    except Exception as exc:
        print(f"  GAGAL klasifikasi: {exc}")
        return False
    print(f"  hasil: {reading.label}  benda={reading.item or '-'}  yakin={reading.confidence:.2f}  ({time.monotonic() - started:.1f} detik)")
    print("Selesai.")
    return True


def test_cek() -> None:
    """Cincin LED, kamera, lalu API dengan foto dari kamera."""
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
    print("\n=== API ===")
    try:
        results["API"] = "OK" if test_api(photo) else "GAGAL"
    except BaseException as exc:
        results["API"] = f"GAGAL: {exc}"
        print(f"  GAGAL: {exc}")
    print("\nRingkasan:")
    for name, state in results.items():
        print(f"  {name}: {state}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Uji satu komponen.")
    parser.add_argument("bagian", choices=("buzzer", "hc", "ir", "infrared", "led", "lamp", "servo", "servo1", "servo1_kanan90", "servo2", "urut_kiri", "urut_kanan", "oled", "ring", "camera", "webcam", "api", "cek"))
    parser.add_argument("--sudut", type=float, default=45.0, help="sudut servo 1 untuk urut_kiri/urut_kanan")
    parser.add_argument("--turun", type=float, default=TILT_DOWN_DEG, help="sudut servo 2 saat turun")
    parser.add_argument("--device", type=int, default=0, help="nomor webcam USB, biasanya 0")
    parser.add_argument("--live", action="store_true", help="tampilkan webcam langsung di browser")
    parser.add_argument("--port", type=int, default=8081, help="port browser untuk webcam --live")
    args = parser.parse_args()
    if args.bagian in ("urut_kiri", "urut_kanan"):
        _test_urut(args.bagian.removeprefix("urut_"), args.sudut, args.turun)
        return
    if args.bagian == "webcam":
        if args.live:
            test_webcam_live(args.device, args.port)
        else:
            test_webcam(args.device)
        return
    {
        "buzzer": test_buzzer,
        "hc": test_hc,
        "ir": test_ir,
        "infrared": test_ir,
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
