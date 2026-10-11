"""Pratinjau kamera di browser, dengan jenis sampah dari LLM Sumopod."""

from __future__ import annotations

import argparse
import json
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import cv2
from picamera2 import Picamera2

from trash2trace.vision import Classifier, Prediction

PREVIEW_SIZE = (640, 480)
ANALYZE_EVERY_S = 4.0

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
    .detail { color: #bbb; margin: 0; }
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
        <p class="kind" id="kind">Menganalisis...</p>
        <p class="detail" id="detail">Menunggu jawaban Sumopod</p>
      </aside>
    </div>
  </main>
  <script>
    async function refresh() {
      try {
        const data = await fetch("/result").then((response) => response.json());
        document.getElementById("kind").textContent = data.text;
        document.getElementById("detail").textContent = data.detail;
      } catch (error) {
        document.getElementById("detail").textContent = "Gagal membaca hasil";
      }
    }
    refresh();
    setInterval(refresh, 2000);
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

    def frame(self):
        with self._lock:
            return self._camera.capture_array()

    def jpeg(self) -> bytes:
        ok, encoded = cv2.imencode(
            ".jpg",
            cv2.cvtColor(self.frame(), cv2.COLOR_RGB2BGR),
            [int(cv2.IMWRITE_JPEG_QUALITY), 60],
        )
        if not ok:
            raise RuntimeError("Gagal membuat JPEG dari kamera")
        return encoded.tobytes()

    def close(self) -> None:
        self._camera.stop()


class Analysis:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.text = "Menganalisis..."
        self.detail = "Menunggu jawaban Sumopod"

    def update(self, prediction: Prediction) -> None:
        text = _LABELS.get(prediction.label, prediction.label.upper())
        detail = f"{prediction.confidence * 100:.0f}% menurut model"
        with self._lock:
            self.text = text
            self.detail = detail

    def fail(self, message: str) -> None:
        with self._lock:
            self.text = "Gagal"
            self.detail = message[:180]

    def snapshot(self) -> dict[str, str]:
        with self._lock:
            return {"text": self.text, "detail": self.detail}


def _watch(camera: Camera, analysis: Analysis, stop: threading.Event) -> None:
    classifier = Classifier()
    while not stop.is_set():
        started = time.monotonic()
        try:
            analysis.update(classifier.predict(camera.frame()))
        except Exception as exc:
            print(f"[WARN] Analisis Sumopod: {exc}")
            analysis.fail(str(exc))
        remaining = ANALYZE_EVERY_S - (time.monotonic() - started)
        if remaining > 0:
            stop.wait(remaining)


def make_handler(camera: Camera, analysis: Analysis):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path.startswith("/stream"):
                self._stream()
                return
            if self.path.startswith("/result"):
                self._json(analysis.snapshot())
                return
            self._bytes(PAGE, "text/html; charset=utf-8")

        def _json(self, payload: dict[str, str]) -> None:
            self._bytes(json.dumps(payload).encode("utf-8"), "application/json")

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
    analysis = Analysis()
    stop = threading.Event()
    worker = threading.Thread(target=_watch, args=(camera, analysis, stop), daemon=True)
    worker.start()

    server = ThreadingHTTPServer(("0.0.0.0", args.port), make_handler(camera, analysis))
    name = socket.gethostname()
    print(f"Kamera siap. Buka http://{name}.local:{args.port}")
    print("Ctrl+C untuk berhenti.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nBerhenti.")
    finally:
        stop.set()
        server.server_close()
        camera.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
