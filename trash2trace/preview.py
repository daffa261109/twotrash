"""Pratinjau kamera di browser: gambar langsung, cincin LED, dan pembacaan sampah oleh API."""

from __future__ import annotations

import argparse
import json
import socket
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import cv2
from gpiozero import LED
from trash2trace.camera import open_camera

from servo.pins import ILLUMINATION_PIN
from trash2trace.bridge import BridgeVision, ping
from trash2trace.ring import Ring
from servo.pins import SERVO_PIN, SERVO_TILT_PIN
from trash2trace.servo_driver import StableServo, connect_pigpio
from trash2trace.settings import (
    ROOT,
    SORT_ANGLES,
    SORT_SETTLE_S,
    SORT_WAIT_S,
    TILT_DOWN_DEG,
    TILT_HOLD_S,
    TILT_UP_SETTLE_S,
    load_bridge_config,
)

PREVIEW_SIZE = (640, 480)
CAPTURE_DIR = ROOT / "captures"

PAGE = """<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Kamera Pi Zero</title>
  <style>
    body { margin: 0; background: #111; color: #eee; font-family: sans-serif; }
    main { max-width: 980px; margin: 0 auto; padding: 16px; }
    .row { display: flex; gap: 16px; align-items: stretch; }
    img { width: min(100%, 640px); background: #000; }
    aside {
      flex: 1;
      min-width: 180px;
      background: #1c1c1c;
      border-radius: 12px;
      padding: 20px;
    }
    .kind { font-size: 42px; margin: 0 0 8px; }
    .detail { color: #bbb; margin: 0 0 16px; }
    button {
      background: #2f6fed;
      color: white;
      border: 0;
      border-radius: 8px;
      padding: 12px 16px;
      font-size: 16px;
    }
    button:disabled { background: #555; }
    h2 { font-size: 16px; margin: 20px 0 8px; color: #ddd; }
    .chips { display: flex; flex-wrap: wrap; gap: 8px; }
    .chips button { padding: 8px 12px; font-size: 14px; background: #3a3a3a; }
    .small { font-size: 24px; }
    @media (max-width: 700px) {
      .row { flex-direction: column; }
    }
  </style>
</head>
<body>
  <main>
    <h1>Kamera Pi Zero</h1>
    <div class="row">
      <img src="/stream" alt="Gambar kamera">
      <aside>
        <p class="kind" id="kind">Belum diambil</p>
        <p class="detail" id="detail">Arahkan benda, lalu ambil satu foto.</p>
        <button id="shoot" type="button">Ambil dan analisis</button>
        <h2>Cincin LED</h2>
        <div class="chips" id="ring-buttons">
          <button type="button" data-mode="putih">Putih</button>
          <button type="button" data-mode="merah">Merah</button>
          <button type="button" data-mode="hijau">Hijau</button>
          <button type="button" data-mode="biru">Biru</button>
          <button type="button" data-mode="mati">Mati</button>
        </div>
        <p class="detail" id="ring-state">Memeriksa...</p>
        <h2>API</h2>
        <button id="api" type="button">Tes API dengan gambar ini</button>
        <p class="kind small" id="api-kind">Belum dites</p>
        <p class="detail" id="api-detail"></p>
      </aside>
    </div>
  </main>
  <script>
    const button = document.getElementById("shoot");
    button.addEventListener("click", async () => {
      button.disabled = true;
      document.getElementById("kind").textContent = "Menganalisis...";
      document.getElementById("detail").textContent = "Foto disimpan, model sedang membaca";
      try {
        const data = await fetch("/capture", { method: "POST" }).then((response) => response.json());
        document.getElementById("kind").textContent = data.text;
        document.getElementById("detail").textContent = data.detail;
      } catch (error) {
        document.getElementById("kind").textContent = "Gagal";
        document.getElementById("detail").textContent = "Permintaan tidak selesai";
      }
      button.disabled = false;
    });

    const ringState = document.getElementById("ring-state");
    document.querySelectorAll("#ring-buttons button").forEach((chip) => {
      chip.addEventListener("click", async () => {
        const data = await fetch("/ring/" + chip.dataset.mode, { method: "POST" }).then((r) => r.json());
        ringState.textContent = data.detail;
      });
    });
    fetch("/status").then((r) => r.json()).then((data) => { ringState.textContent = data.ring; });

    const apiButton = document.getElementById("api");
    apiButton.addEventListener("click", async () => {
      apiButton.disabled = true;
      document.getElementById("api-kind").textContent = "Menghubungi API...";
      document.getElementById("api-detail").textContent = "Bisa sampai 45 detik";
      try {
        const data = await fetch("/api", { method: "POST" }).then((r) => r.json());
        document.getElementById("api-kind").textContent = data.text;
        document.getElementById("api-detail").textContent = data.detail;
      } catch (error) {
        document.getElementById("api-kind").textContent = "Gagal";
        document.getElementById("api-detail").textContent = "Permintaan tidak selesai";
      }
      apiButton.disabled = false;
    });
  </script>
</body>
</html>
""".encode("utf-8")

_LABELS = {
    "organic": "ORGANIK",
    "nonorganic": "NONORGANIK",
    "other": "LAINNYA",
}


class Camera:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._camera = open_camera(PREVIEW_SIZE)
        self._lamp_lock = threading.Lock()
        self._lamp = _lamp_on()
        time.sleep(1.0)

    def ring_status(self) -> str:
        if isinstance(self._lamp, Ring):
            return "Cincin LED siap, putih menyala"
        if self._lamp is not None:
            return "Cincin tidak aktif, lampu GPIO 24 yang menyala (jalankan dengan sudo untuk cincin)"
        return "Cincin tidak aktif: jalankan dengan sudo dan hentikan pigpiod"

    def set_ring(self, mode: str) -> str:
        colours = {
            "putih": (255, 255, 255),
            "merah": (255, 0, 0),
            "hijau": (0, 255, 0),
            "biru": (0, 0, 255),
            "mati": (0, 0, 0),
        }
        if mode not in colours:
            return "Warna tidak dikenal"
        with self._lamp_lock:
            if isinstance(self._lamp, Ring):
                self._lamp.fill(*colours[mode])
                return f"Cincin {mode}"
            if self._lamp is not None:
                (self._lamp.off if mode == "mati" else self._lamp.on)()
                return f"Lampu GPIO 24 {'mati' if mode == 'mati' else 'nyala'}. Warna butuh cincin."
        return self.ring_status()

    def jpeg(self) -> bytes:
        with self._lock:
            frame = self._camera.capture_array()
        ok, encoded = cv2.imencode(
            ".jpg",
            cv2.cvtColor(frame, cv2.COLOR_RGB2BGR),
            [int(cv2.IMWRITE_JPEG_QUALITY), 80],
        )
        if not ok:
            raise RuntimeError("Gagal membuat JPEG dari kamera")
        return encoded.tobytes()

    def close(self) -> None:
        if self._lamp is not None:
            try:
                self._lamp.off()
                self._lamp.close()
            except Exception as exc:
                print(f"[WARN] Mematikan lampu: {exc}")
        with self._lock:
            self._camera.close()


def _lamp_on():
    """Nyalakan cincin putih. Kalau cincin tidak bisa, pakai lampu satu LED lama."""
    try:
        ring = Ring()
        ring.white()
        print("Cincin LED putih nyala.")
        return ring
    except Exception as exc:
        print(f"[WARN] Cincin LED: {exc}")
    try:
        lamp = LED(ILLUMINATION_PIN)
        lamp.on()
        print("Lampu penerangan GPIO 24 nyala.")
        return lamp
    except Exception as exc:
        print(f"[WARN] Lampu penerangan: {exc}")
        return None



class SortMotion:
    """Gerakan servo setelah sampah terbaca. Butuh pigpiod aktif.

    Servo 1 memutar ke sudut jenis sampah dan tetap di sana. Servo 2 turun lalu naik
    lagi ke tegak. Setelah jeda, servo 1 kembali ke titik awal.
    """

    def __init__(self) -> None:
        self._pi = connect_pigpio()
        self._busy = threading.Lock()
        self._servo1 = StableServo(self._pi, SERVO_PIN)
        self._servo2 = StableServo(self._pi, SERVO_TILT_PIN)
        self._servo1.angle = 0
        self._servo2.angle = 0

    def start(self, label: str) -> str:
        if self._pi is None:
            return "servo mati (pigpiod tidak aktif)"
        angle = SORT_ANGLES.get(label)
        if angle is None:
            return "servo diam"
        if not self._busy.acquire(blocking=False):
            return "servo masih bergerak"
        threading.Thread(target=self._sequence, args=(angle,), daemon=True).start()
        return f"servo 1 ke {angle:+.0f}°, servo 2 turun-naik"

    def _sequence(self, angle: float) -> None:
        try:
            print(f"[SERVO] servo 1 ke {angle:+.0f}°")
            self._servo1.angle = angle
            time.sleep(SORT_SETTLE_S)
            print(f"[SERVO] servo 2 turun {TILT_DOWN_DEG:+.0f}°")
            self._servo2.angle = TILT_DOWN_DEG
            time.sleep(TILT_HOLD_S)
            print("[SERVO] servo 2 naik, tegak")
            self._servo2.angle = 0
            time.sleep(TILT_UP_SETTLE_S + SORT_WAIT_S)
            print("[SERVO] servo 1 kembali ke titik awal")
            self._servo1.angle = 0
            time.sleep(SORT_SETTLE_S)
        except Exception as exc:
            print(f"[WARN] Gerakan servo: {exc}")
        finally:
            self._busy.release()
            print("[SERVO] selesai")

    def close(self) -> None:
        if self._pi is None:
            return
        self._servo1.angle = 0
        self._servo2.angle = 0
        time.sleep(0.4)
        self._servo1.detach()
        self._servo2.detach()
        self._pi.stop()


class Capture:
    """Simpan satu foto, minta API membacanya, lalu gerakkan servo."""

    def __init__(self, camera: Camera, motion: SortMotion) -> None:
        self._camera = camera
        self._motion = motion
        self._lock = threading.Lock()

    def take(self) -> dict[str, str]:
        with self._lock:
            image = self._camera.jpeg()
            CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
            path = CAPTURE_DIR / f"{datetime.now():%Y%m%d-%H%M%S}.jpg"
            path.write_bytes(image)
            print(f"[FOTO] {path}")
            started = time.monotonic()
            try:
                label, _confidence = BridgeVision().classify(image)
            except (Exception, SystemExit) as exc:
                print(f"[WARN] API: {exc}")
                return {"text": "Foto disimpan", "detail": f"{path.name} · API gagal: {str(exc)[:140]}"}
            took = time.monotonic() - started
            text = _LABELS.get(label, label.upper())
            print(f"[HASIL] {text} ({took:.1f} detik)")
            motion = self._motion.start(label)
            return {
                "text": text,
                "detail": f"{took:.1f} detik · {motion}",
            }


class ApiCheck:
    """Kirim gambar kamera saat ini ke API, lapor hasilnya, lalu gerakkan servo."""

    def __init__(self, camera: Camera, motion: SortMotion) -> None:
        self._camera = camera
        self._motion = motion
        self._lock = threading.Lock()

    def run(self) -> dict[str, str]:
        with self._lock:
            try:
                config = load_bridge_config()
            except BaseException as exc:
                return {"text": "Belum diatur", "detail": str(exc)[:180]}
            try:
                status = ping(config)
            except Exception as exc:
                return {"text": "Gagal terhubung", "detail": str(exc)[:180]}
            started = time.monotonic()
            try:
                label, _confidence = BridgeVision(config).classify(self._camera.jpeg())
            except Exception as exc:
                return {"text": "Gagal klasifikasi", "detail": str(exc)[:180]}
            took = time.monotonic() - started
            text = _LABELS.get(label, label.upper())
            print(f"[API] {text} ({took:.1f} detik)")
            motion = self._motion.start(label)
            return {
                "text": text,
                "detail": f"{status} · {took:.1f} detik · {motion}",
            }


def make_handler(camera: Camera, capture: Capture, api: ApiCheck):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path.startswith("/stream"):
                self._stream()
                return
            if self.path.startswith("/status"):
                self._json({"ring": camera.ring_status()})
                return
            self._bytes(PAGE, "text/html; charset=utf-8")

        def do_POST(self) -> None:
            if self.path.startswith("/capture"):
                self._json(capture.take())
                return
            if self.path.startswith("/api"):
                self._json(api.run())
                return
            if self.path.startswith("/ring/"):
                mode = self.path.rsplit("/", 1)[-1]
                self._json({"detail": camera.set_ring(mode)})
                return
            self.send_error(404)

        def _json(self, data: dict) -> None:
            self._bytes(json.dumps(data).encode("utf-8"), "application/json")

        def _bytes(self, body: bytes, content_type: str) -> None:
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _stream(self) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
            self.end_headers()
            try:
                while True:
                    image = camera.jpeg()
                    self.wfile.write(b"--frame\r\n")
                    self.wfile.write(b"Content-Type: image/jpeg\r\n")
                    self.wfile.write(f"Content-Length: {len(image)}\r\n\r\n".encode())
                    self.wfile.write(image)
                    self.wfile.write(b"\r\n")
                    time.sleep(0.2)
            except (BrokenPipeError, ConnectionResetError):
                return

        def log_message(self, fmt: str, *args) -> None:
            return

    return Handler


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Buka kamera Pi Zero di browser.")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args(argv)

    try:
        camera = Camera()
    except RuntimeError as exc:
        print(f"\n[GAGAL] Kamera tidak bisa dibuka: {exc}")
        print("Kamera dipakai program lain (biasanya trash2trace atau preview lama). Bebaskan dulu:")
        print("  sudo systemctl stop trash2trace")
        print("  sudo pkill -f trash2trace.preview")
        print("  sudo fuser -v /dev/media0 /dev/media1   # lihat siapa yang masih memakai")
        return 1
    motion = SortMotion()
    capture = Capture(camera, motion)
    server = ThreadingHTTPServer(("0.0.0.0", args.port), make_handler(camera, capture, ApiCheck(camera, motion)))
    # Aliran gambar di browser tidak pernah selesai sendiri. Tanpa dua baris ini,
    # server_close() menunggu aliran itu dan Ctrl+C tidak pernah berhenti.
    server.daemon_threads = True
    server.block_on_close = False
    name = socket.gethostname()
    print(f"Kamera siap. Buka http://{name}.local:{args.port}")
    print(f"Foto disimpan di {CAPTURE_DIR}")
    print("Ctrl+C untuk berhenti.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nBerhenti.")
    finally:
        server.server_close()
        motion.close()
        camera.close()
        print("Kamera dan servo dilepas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
