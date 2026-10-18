"""Cincin WS2812 12 LED di sekeliling kamera, data di GPIO 21 (servo/pins.py).

Butuh root (library menyentuh perangkat keras langsung) dan paket rpi_ws281x:

    sudo apt install python3-dev gcc
    sudo python3 -m pip install --break-system-packages rpi-ws281x

Perangkat PCM yang dipakai GPIO 21 bentrok dengan pigpiod. Hentikan pigpiod
saat cincin dipakai: sudo systemctl stop pigpiod
"""

from __future__ import annotations

import os

from servo.pins import RING_DIN_PIN

RING_LED_COUNT = 12
RING_BRIGHTNESS = 100  # 0 sampai 255. Sekitar 0,28 A untuk 12 LED putih.


class Ring:
    def __init__(self, brightness: int = RING_BRIGHTNESS) -> None:
        if os.geteuid() != 0:
            raise RuntimeError("cincin butuh root, jalankan dengan sudo")
        try:
            from rpi_ws281x import Color, PixelStrip
        except ImportError as exc:
            raise RuntimeError(
                "rpi_ws281x belum dipasang: "
                "sudo python3 -m pip install --break-system-packages rpi-ws281x"
            ) from exc
        self._color = Color
        self._strip = PixelStrip(
            RING_LED_COUNT, RING_DIN_PIN, 800000, 10, False, brightness, 0
        )
        self._strip.begin()

    def fill(self, red: int, green: int, blue: int) -> None:
        color = self._color(red, green, blue)
        for index in range(RING_LED_COUNT):
            self._strip.setPixelColor(index, color)
        self._strip.show()

    def white(self) -> None:
        self.fill(255, 255, 255)

    def off(self) -> None:
        self.fill(0, 0, 0)

    def close(self) -> None:
        self.off()
