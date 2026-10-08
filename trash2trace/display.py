"""Layar OLED 128x64. Kalau layar tidak ada, mesin tetap jalan."""

from __future__ import annotations

from trash2trace.settings import OLED_ADDR, OLED_HEIGHT, OLED_WIDTH

try:
    import adafruit_ssd1306
    import board
    import busio
    from PIL import Image, ImageDraw, ImageFont

    _LIBRARY_READY = True
except Exception:
    _LIBRARY_READY = False


class Display:
    def __init__(self) -> None:
        self._panel = None
        self._font = None
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
        self._panel.fill(0)
        self._panel.show()

    def show(self, line1: str, line2: str = "", line3: str = "") -> None:
        if self._panel is None:
            return
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
            box = draw.textbbox((0, 0), text, font=font)
            x = max(0, (OLED_WIDTH - (box[2] - box[0])) // 2)
            draw.text((x, y), text, font=font, fill=255)
        self._panel.image(image)
        self._panel.show()


def _load_font():
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 15)
    except Exception:
        return ImageFont.load_default()
