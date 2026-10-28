"""Layar monitor: kamera langsung, lalu hasil pemilahan. Jendela dibuka penuh saat program menyala."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from trash2trace.screen import screen_command
from trash2trace.settings import MONITOR_PORT

# JPEG 1×1, dipakai hanya sampai frame kamera pertama datang.
_BLANK_JPEG = bytes((
    0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01,
    0x01, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x00, 0xFF, 0xDB, 0x00, 0x43,
    0x00, 0x08, 0x06, 0x06, 0x07, 0x06, 0x05, 0x08, 0x07, 0x07, 0x07, 0x09,
    0x09, 0x08, 0x0A, 0x0C, 0x14, 0x0D, 0x0C, 0x0B, 0x0B, 0x0C, 0x19, 0x12,
    0x13, 0x0F, 0x14, 0x1D, 0x1A, 0x1F, 0x1E, 0x1D, 0x1A, 0x1C, 0x1C, 0x20,
    0x24, 0x2E, 0x27, 0x20, 0x22, 0x2C, 0x23, 0x1C, 0x1C, 0x28, 0x37, 0x29,
    0x2C, 0x30, 0x31, 0x34, 0x34, 0x34, 0x1F, 0x27, 0x39, 0x3D, 0x38, 0x32,
    0x3C, 0x2E, 0x33, 0x34, 0x32, 0xFF, 0xC0, 0x00, 0x0B, 0x08, 0x00, 0x01,
    0x00, 0x01, 0x01, 0x01, 0x11, 0x00, 0xFF, 0xC4, 0x00, 0x14, 0x00, 0x01,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x03, 0xFF, 0xC4, 0x00, 0x14, 0x10, 0x01, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0xFF, 0xDA, 0x00, 0x08, 0x01, 0x01, 0x00, 0x00, 0x3F, 0x00,
    0x37, 0xFF, 0xD9,
))

_LABELS = {"organic": "ORGANIK", "nonorganic": "NONORGANIK", "other": "LAINNYA"}

_PAGE = """<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>TRASH2TRASH</title>
  <style>
    * { box-sizing: border-box; }
    html, body {
      margin: 0; height: 100%; overflow: hidden; background: #07110e; color: #f4fff8;
      font-family: "DejaVu Sans", "Nimbus Sans", sans-serif; cursor: none; user-select: none;
    }
    .screen {
      height: 100%; display: grid; grid-template-columns: 0.9fr 1.1fr;
      gap: 3vh; padding: 4vh 3vw;
    }
    aside { display: flex; flex-direction: column; justify-content: center; min-width: 0; }
    .logo {
      margin: 0; font-size: clamp(64px, 8vw, 120px); font-weight: 800; line-height: 0.86;
      letter-spacing: -0.04em; color: #3ddc6a;
    }
    .logo span { color: #f7fff9; }
    #category {
      margin: 3vh 0 0; font-size: clamp(28px, 3.4vw, 52px); font-weight: 800; letter-spacing: 0.04em;
    }
    #headline { margin: 1.2vh 0 0; font-size: clamp(28px, 3.2vw, 48px); font-weight: 750; line-height: 1.05; }
    #detail { margin: 1.4vh 0 0; font-size: clamp(18px, 2vw, 28px); font-weight: 700; color: #b7c9bf; }
    .lens {
      min-width: 0; min-height: 0; border-radius: 36px; overflow: hidden; background: #000;
      border: 3px solid rgba(61, 220, 106, 0.9);
      box-shadow: 0 0 0 12px rgba(61, 220, 106, 0.14);
    }
    img { width: 100%; height: 100%; object-fit: cover; display: block; }
    body[data-tone="organic"] #category { color: #3ddc6a; }
    body[data-tone="nonorganic"] #category { color: #7ec8ff; }
    body[data-tone="other"] #category { color: #ffb020; }
    body[data-tone="wait"] #headline { font-size: clamp(120px, 16vw, 240px); line-height: 0.9; color: #ffe08a; }
    body[data-tone="organic"] #headline,
    body[data-tone="nonorganic"] #headline,
    body[data-tone="other"] #headline { font-size: clamp(40px, 5vw, 76px); }
  </style>
</head>
<body data-tone="idle">
  <div class="screen">
    <aside>
      <h1 class="logo">TRASH<span>2</span><br>TRASH</h1>
      <p id="category"></p>
      <h2 id="headline">MENUNGGU</h2>
      <p id="detail">Wi-Fi belum terhubung</p>
    </aside>
    <section class="lens">
      <img src="/stream" alt="Kamera">
    </section>
  </div>
  <script>
    const category = document.getElementById("category");
    const headline = document.getElementById("headline");
    const detail = document.getElementById("detail");
    async function tick() {
      try {
        const data = await fetch("/status", { cache: "no-store" }).then((response) => response.json());
        const showCategory = data.title && data.title !== data.headline && !["idle", "wait", "reading"].includes(data.tone);
        category.hidden = !showCategory;
        category.textContent = showCategory ? data.title : "";
        headline.textContent = data.headline;
        detail.textContent = data.detail;
        document.body.dataset.tone = data.tone;
      } catch (error) {}
    }
    tick();
    setInterval(tick, 200);
    document.documentElement.requestFullscreen?.().catch(() => {});
  </script>
</body>
</html>
""".encode("utf-8")


def display_env(base: dict | None = None) -> dict:
    env = dict(base if base is not None else os.environ)
    env.setdefault("DISPLAY", ":0")
    env.setdefault("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
    runtime = env.get("XDG_RUNTIME_DIR", "")
    if "WAYLAND_DISPLAY" not in env and os.path.exists(os.path.join(runtime, "wayland-0")):
        env["WAYLAND_DISPLAY"] = "wayland-0"
    auth = os.path.join(os.path.expanduser("~"), ".Xauthority")
    if "XAUTHORITY" not in env and os.path.exists(auth):
        env["XAUTHORITY"] = auth
    return env


def display_ready(env: dict) -> bool:
    runtime = env.get("XDG_RUNTIME_DIR", "")
    if runtime and os.path.exists(os.path.join(runtime, env.get("WAYLAND_DISPLAY", "wayland-0"))):
        return True
    number = env.get("DISPLAY", ":0").split(":")[-1].split(".")[0] or "0"
    return os.path.exists(f"/tmp/.X11-unix/X{number}")


class Monitor:
    def __init__(self, camera, port: int = MONITOR_PORT) -> None:
        self._camera = camera
        self.port = port
        self._lock = threading.Lock()
        self._frame = None
        self._jpeg = _BLANK_JPEG
        self._view = {
            "tone": "idle",
            "title": "SIAP",
            "headline": "MENUNGGU",
            "detail": "Wi-Fi belum terhubung",
        }
        self._stop = threading.Event()
        self._server: ThreadingHTTPServer | None = None
        self._http: threading.Thread | None = None
        self._pump: threading.Thread | None = None
        self._browser: subprocess.Popen | None = None
        self._opener: threading.Thread | None = None

    def start(self) -> None:
        handler = self._handler()
        try:
            self._server = ThreadingHTTPServer(("0.0.0.0", self.port), handler)
        except OSError as exc:
            raise OSError(
                f"Port {self.port} sedang dipakai. Hentikan preview lama: sudo systemctl stop trash2trace"
            ) from exc
        self._server.daemon_threads = True
        self._server.block_on_close = False
        self.port = self._server.server_address[1]
        if self._camera is not None:
            self._pump = threading.Thread(target=self._read_camera, daemon=True)
            self._pump.start()
        self._http = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._http.start()
        name = socket.gethostname()
        print(f"[MONITOR] http://{name}.local:{self.port}")

    def open_fullscreen(self) -> None:
        self._opener = threading.Thread(target=self._open_when_ready, daemon=True)
        self._opener.start()

    def ready(self) -> None:
        self._set("idle", "SIAP", "LETAKKAN SAMPAH", "Sensor menunggu benda")

    def waiting_wifi(self) -> None:
        self._set("idle", "SIAP", "MENUNGGU", "Wi-Fi belum terhubung")

    def waiting(self, seconds: int) -> None:
        self._set("wait", "TUNGGU", str(int(seconds)), "detik")

    def reading(self) -> None:
        self._set("reading", "MEMBACA", "MEMBACA", "Foto sedang dikirim")

    def result(self, label: str, detail: str, item: str = "") -> None:
        text = _LABELS.get(label, "LAINNYA")
        tone = label if label in ("organic", "nonorganic") else "other"
        self._set(tone, text, item or text, detail)

    def fail(self, detail: str) -> None:
        self._set("other", "GAGAL", "GAGAL", detail[:80])

    def frame_bgr(self):
        with self._lock:
            frame = self._frame
        if frame is not None:
            return frame.copy()
        # Tanpa aliran layar, foto tetap diambil langsung dari kamera.
        if self._camera is None or (self._pump is not None and self._pump.is_alive()):
            return None
        return self._camera.read_bgr()

    def close(self) -> None:
        self._stop.set()
        browser = self._browser
        if browser is not None and browser.poll() is None:
            browser.terminate()
        server = self._server
        if server is not None:
            server.shutdown()
            server.server_close()
            self._server = None
        if self._pump is not None:
            self._pump.join(timeout=1.5)

    def _set(self, tone: str, title: str, headline: str, detail: str) -> None:
        with self._lock:
            self._view = {"tone": tone, "title": title, "headline": headline, "detail": detail}

    def _status(self) -> dict:
        with self._lock:
            return dict(self._view)

    def _jpeg_bytes(self) -> bytes:
        with self._lock:
            return self._jpeg

    def _read_camera(self) -> None:
        import cv2

        warned = False
        while not self._stop.is_set():
            try:
                frame = self._camera.read_bgr().copy()
                ok, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
                if not ok:
                    raise RuntimeError("JPEG kamera gagal dibuat")
            except Exception as exc:
                if not warned:
                    print(f"[WARN] Layar kamera: {exc}")
                    warned = True
                time.sleep(0.2)
                continue
            warned = False
            with self._lock:
                self._frame = frame
                self._jpeg = encoded.tobytes()

    def _open_when_ready(self) -> None:
        for _ in range(40):
            if self._stop.is_set():
                return
            env = display_env()
            if display_ready(env):
                break
            time.sleep(0.5)
        if self._stop.is_set():
            return
        print("[MONITOR] Membuka layar penuh")
        self._browser = subprocess.Popen(screen_command(self.port), env=display_env())
        time.sleep(0.8)
        if self._browser.poll() is not None:
            print("[MONITOR] Jendela gagal dibuka. Pasang dulu:")
            print("  sudo apt install python3-tk python3-pil.imagetk")

    def _handler(self):
        monitor = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                if self.path.startswith("/stream"):
                    self._stream()
                    return
                if self.path.startswith("/status"):
                    body = json.dumps(monitor._status()).encode("utf-8")
                    self._bytes(body, "application/json")
                    return
                if self.path.startswith("/frame.jpg"):
                    self._bytes(monitor._jpeg_bytes(), "image/jpeg")
                    return
                self._bytes(_PAGE, "text/html; charset=utf-8")

            def _bytes(self, body: bytes, content_type: str) -> None:
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _stream(self) -> None:
                self.send_response(200)
                self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                try:
                    while not monitor._stop.is_set():
                        image = monitor._jpeg_bytes()
                        self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\n")
                        self.wfile.write(f"Content-Length: {len(image)}\r\n\r\n".encode())
                        self.wfile.write(image)
                        self.wfile.write(b"\r\n")
                        time.sleep(0.1)
                except (BrokenPipeError, ConnectionResetError):
                    return

            def log_message(self, fmt: str, *args) -> None:
                return

        return Handler
