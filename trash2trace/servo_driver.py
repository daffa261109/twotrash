"""Servo stabil. Pulsa dikirim pigpio (DMA, ketepatan 1 µs), tanpa PWM software.

Pulsa tidak dikirim ulang kalau sudutnya sama, jadi servo tidak digeser-geser.
Kalau pigpiod tidak aktif, servo dibiarkan mati supaya tidak bergetar.
"""

from __future__ import annotations


def connect_pigpio():
    try:
        import pigpio
    except Exception as exc:
        print(f"[WARN] Modul pigpio tidak ada, servo dimatikan: {exc}")
        return None
    pi = pigpio.pi()
    if not pi.connected:
        print("[WARN] pigpiod tidak aktif, servo dimatikan. Jalankan: sudo systemctl enable --now pigpiod")
        return None
    return pi


class StableServo:
    def __init__(
        self,
        pi,
        pin: int,
        min_angle: float = -90,
        max_angle: float = 90,
        min_us: int = 1000,
        max_us: int = 2000,
    ) -> None:
        self._pi = pi
        self._pin = pin
        self._min_angle = min_angle
        self._max_angle = max_angle
        self._min_us = min_us
        self._max_us = max_us
        self._angle: float | None = None

    @property
    def angle(self) -> float | None:
        return self._angle

    @angle.setter
    def angle(self, value: float) -> None:
        if self._pi is None:
            return
        value = max(self._min_angle, min(self._max_angle, value))
        if value == self._angle:
            return
        span = self._max_angle - self._min_angle
        us = self._min_us + (value - self._min_angle) / span * (self._max_us - self._min_us)
        self._pi.set_servo_pulsewidth(self._pin, round(us))
        self._angle = value

    def detach(self) -> None:
        if self._pi is None:
            return
        self._pi.set_servo_pulsewidth(self._pin, 0)
        self._angle = None
