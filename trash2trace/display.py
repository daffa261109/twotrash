"""Layar OLED 128x64. Kalau layar tidak ada, mesin tetap jalan."""

from __future__ import annotations

import threading
import time

from trash2trace.settings import (
    OLED_ADDR,
    OLED_HEIGHT,
    OLED_WIDTH,
    WELCOME_SCROLL,
    WELCOME_TITLE,
)

try:
    import adafruit_ssd1306
    import board
    import busio
    from PIL import Image, ImageDraw, ImageFont

    _LIBRARY_READY = True
except Exception:
    _LIBRARY_READY = False

SCROLL_STEP_PX = 4
SCROLL_DELAY_S = 0.03


class Display:
    def __init__(self) -> None:
        self._panel = None
        self._font = None
        self._lock = threading.Lock()
        self._busy = False
        self._idle_thread: threading.Thread | None = None
        self._idle_stop = threading.Event()
        if not _LIBRARY_READY:
            print("[WARN] Library OLED tidak ada. Tampilan dilewati.")
            return
        try:
            i2c = busio.I2C(board.SCL, board.SDA)
            self._panel = adafruit_ssd1306.SSD1306_I2C(
                OLED_WIDTH, OLED_HEIGHT, i2c, addr=OLED_ADDR
            )
            self._font = _load_font()
            self.clear()
        except Exception as exc:
            print(f"[WARN] OLED gagal dimulai: {exc}")
            self._panel = None

    def clear(self) -> None:
        if self._panel is None:
            return
        self._busy = True
        with self._lock:
            self._panel.fill(0)
            self._panel.show()

    def show(self, line1: str, line2: str = "", line3: str = "") -> None:
        """Tampilkan tiga baris. Layar sambutan berhenti sampai idle() dipanggil."""
        if self._panel is None:
            return
        self._busy = True
        image = Image.new("1", (OLED_WIDTH, OLED_HEIGHT), 0)
        draw = ImageDraw.Draw(image)
        small = ImageFont.load_default()
        large = self._font or small
        rows = (
            (str(line1)[:20], 2, large),
            (str(line2)[:20], 27, small),
            (str(line3)[:20], 49, small),
        )
        for text, y, font in rows:
            _draw_centered(draw, text, y, font)
        with self._lock:
            self._panel.image(image)
            self._panel.show()

    def start_idle(self) -> None:
        """Layar sambutan: Welcome, nama mesin, Ready, lalu teks berjalan."""
        if self._panel is None:
            return
        self._busy = False
        if self._idle_thread is not None:
            return
        self._idle_stop.clear()
        self._idle_thread = threading.Thread(target=self._idle_loop, daemon=True)
        self._idle_thread.start()

    def idle(self) -> None:
        """Kembali ke layar sambutan setelah show()."""
        self._busy = False

    def stop_idle(self) -> None:
        self._idle_stop.set()
        if self._idle_thread is not None:
            self._idle_thread.join(timeout=1.5)
            self._idle_thread = None

    def _idle_loop(self) -> None:
        small = ImageFont.load_default()
        large = self._font or small
        box = ImageDraw.Draw(Image.new("1", (1, 1))).textbbox((0, 0), WELCOME_SCROLL, font=small)
        text_width = box[2] - box[0]
        x = OLED_WIDTH
        while not self._idle_stop.is_set():
            if self._busy:
                x = OLED_WIDTH
                time.sleep(0.1)
                continue
            image = Image.new("1", (OLED_WIDTH, OLED_HEIGHT), 0)
            draw = ImageDraw.Draw(image)
            _draw_centered(draw, "Welcome", 0, large)
            _draw_centered(draw, WELCOME_TITLE, 19, large)
            _draw_centered(draw, "Ready", 40, small)
            draw.text((x, 53), WELCOME_SCROLL, font=small, fill=255)
            try:
                with self._lock:
                    if self._busy:
                        continue
                    self._panel.image(image)
                    self._panel.show()
            except Exception as exc:
                print(f"[WARN] OLED: {exc}")
                time.sleep(1.0)
            x -= SCROLL_STEP_PX
            if x < -text_width:
                x = OLED_WIDTH
            time.sleep(SCROLL_DELAY_S)


def _draw_centered(draw, text: str, y: int, font) -> None:
    box = draw.textbbox((0, 0), text, font=font)
    x = max(0, (OLED_WIDTH - (box[2] - box[0])) // 2)
    draw.text((x, y), text, font=font, fill=255)


def _load_font():
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 15)
    except Exception:
        return ImageFont.load_default()
