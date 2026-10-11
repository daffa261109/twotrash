"""Pratinjau kamera. Foto diambil sekali, disimpan, lalu dikirim ke Sumopod."""

from __future__ import annotations

import argparse
import json
import socket
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import cv2
from picamera2 import Picamera2

from trash2trace.llm import LlmVision
from trash2trace.settings import ROOT

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
        <p class="detail" id="detail">Arahkan benda, lalu ambil foto.</p>
        <button id="shoot" type="button">Ambil dan analisis</button>
      </aside>
    </div>
  </main>
  <script>
    const button = document.getElementById("shoot");
    button.addEventListener("click", async () => {
      button.disabled = true;
      document.getElementById("kind").textContent = "Menganalisis...";
      document.getElementById("detail").textContent = "Foto disimpan, menunggu Sumopod";
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
        self._camera = Picamera2()
        self._camera.configure(
            self._camera.create_preview_configuration(
                main={"format": "RGB888", "size": PREVIEW_SIZE}
            )
        )
        self._camera.start()
        time.sleep(1.0)

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
        self._camera.stop()


class Capture:
    def __init__(self, camera: Camera) -> None:
        self._camera = camera
        self._llm = LlmVision()
        self._lock = threading.Lock()

    def take(self) -> dict[str, str]:
        with self._lock:
            image = self._camera.jpeg()
            CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
            path = CAPTURE_DIR / f"{datetime.now():%Y%m%d-%H%M%S}.jpg"
            path.write_bytes(image)
            print(f"[FOTO] {path}")
            try:
                label, confidence = self._llm.classify(path.read_bytes())
            except Exception as exc:
                print(f"[WARN] Analisis Sumopod: {exc}")
                return {"text": "Gagal", "detail": str(exc)[:180]}
            text = _LABELS.get(label, label.upper())
            print(f"[HASIL] {text} {confidence:.2f}")
            return {
                "text": text,
                "detail": f"{confidence * 100:.0f}% · {path.name}",
            }


def make_handler(camera: Camera, capture: Capture):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path.startswith("/stream"):
                self._stream()
                return
            self._bytes(PAGE, "text/html; charset=utf-8")

        def do_POST(self) -> None:
            if self.path.startswith("/capture"):
                self._bytes(
                    json.dumps(capture.take()).encode("utf-8"),
                    "application/json",
                )
                return
            self.send_error(404)

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

    camera = Camera()
    capture = Capture(camera)
    server = ThreadingHTTPServer(("0.0.0.0", args.port), make_handler(camera, capture))
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
        camera.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
