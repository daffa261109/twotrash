"""Pratinjau kamera di browser. Hentikan pemilah dulu supaya kamera bebas."""

from __future__ import annotations

import argparse
import socket
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import cv2
from picamera2 import Picamera2

PREVIEW_SIZE = (640, 480)
BOUNDARY = b"frame"

PAGE = """<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Kamera Pi Zero</title>
  <style>
    body { margin: 0; background: #111; color: #eee; font-family: sans-serif; }
    main { max-width: 720px; margin: 0 auto; padding: 16px; }
    img { width: 100%; background: #000; }
  </style>
</head>
<body>
  <main>
    <h1>Kamera Pi Zero</h1>
    <img src="/stream" alt="Gambar kamera">
  </main>
</body>
</html>
""".encode("utf-8")


class Camera:
    def __init__(self) -> None:
        self._camera = Picamera2()
        self._camera.configure(
            self._camera.create_preview_configuration(
                main={"format": "RGB888", "size": PREVIEW_SIZE}
            )
        )
        self._camera.start()
        time.sleep(1.0)

    def jpeg(self) -> bytes:
        frame = self._camera.capture_array()
        ok, encoded = cv2.imencode(
            ".jpg",
            cv2.cvtColor(frame, cv2.COLOR_RGB2BGR),
            [int(cv2.IMWRITE_JPEG_QUALITY), 60],
        )
        if not ok:
            raise RuntimeError("Gagal membuat JPEG dari kamera")
        return encoded.tobytes()

    def close(self) -> None:
        self._camera.stop()


def make_handler(camera: Camera):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path.startswith("/stream"):
                self._stream()
                return
            body = PAGE
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _stream(self) -> None:
            self.send_response(200)
            self.send_header(
                "Content-Type",
                "multipart/x-mixed-replace; boundary=frame",
            )
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
    server = ThreadingHTTPServer(("0.0.0.0", args.port), make_handler(camera))
    name = socket.gethostname()
    print(f"Kamera siap. Buka http://{name}.local:{args.port}")
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
