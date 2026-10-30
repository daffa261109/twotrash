"""Servo stabil. Pulsa dikirim pigpio (DMA, ketepatan 1 µs), tanpa PWM software.

Pulsa tidak dikirim ulang kalau sudutnya sama, jadi servo tidak digeser-geser.
Kalau pigpiod tidak aktif, servo dibiarkan mati supaya tidak bergetar.
"""

from __future__ import annotations

import time


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
        max_angle: float = 180,
        min_us: int = 1000,
        max_us: int = 2500,
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


def geser(servo: StableServo, target: float) -> None:
    """Pindah pelan, derajat demi derajat. Kecepatan dari SERVO_KECEPATAN."""
    from trash2trace.settings import SERVO_KECEPATAN

    if servo._pi is None:
        return
    start = target if servo.angle is None else servo.angle
    jarak = abs(target - start)
    steps = max(1, int(round(jarak)))
    speed = SERVO_KECEPATAN if SERVO_KECEPATAN > 0 else 45.0
    pause = (jarak / speed) / steps
    for step in range(1, steps + 1):
        servo.angle = start + (target - start) * step / steps
        time.sleep(pause)


def sort_plan(label: str) -> str | None:
    from trash2trace.settings import (
        SERVO1_ANGLES,
        SERVO1_KEMBALI,
        SERVO1_WAIT_S,
        SERVO2_BUANG,
        SERVO2_WAIT_S,
    )

    angle = SERVO1_ANGLES.get(label)
    if angle is None:
        return None
    return (
        f"servo 1 ke {angle:+.0f}°, tunggu {SERVO1_WAIT_S:g} detik, "
        f"servo 2 buang {SERVO2_BUANG:+.0f}°, tunggu {SERVO2_WAIT_S:g} detik, "
        f"servo 2 ke {SERVO1_KEMBALI:+.0f}°, lalu servo 1 ke {SERVO1_KEMBALI:+.0f}°"
    )


def run_sort(servo1: StableServo, servo2: StableServo, label: str) -> str:
    """Servo 1 ke tempat sampah, servo 2 buang, lalu keduanya kembali. Gerakan pelan."""
    from trash2trace.settings import (
        SERVO1_ANGLES,
        SERVO1_KEMBALI,
        SERVO1_WAIT_S,
        SERVO2_BUANG,
        SERVO2_WAIT_S,
    )

    if servo1._pi is None:
        return "servo mati (pigpiod tidak aktif)"
    angle = SERVO1_ANGLES.get(label)
    if angle is None:
        return "servo diam"
    print(f"[SERVO] servo 1 ke {angle:+.0f}°")
    geser(servo1, angle)
    time.sleep(max(0.0, SERVO1_WAIT_S))
    print(f"[SERVO] servo 2 buang ke {SERVO2_BUANG:+.0f}°")
    geser(servo2, SERVO2_BUANG)
    time.sleep(max(0.0, SERVO2_WAIT_S))
    print(f"[SERVO] servo 2 kembali ke {SERVO1_KEMBALI:+.0f}°")
    geser(servo2, SERVO1_KEMBALI)
    print(f"[SERVO] servo 1 kembali ke {SERVO1_KEMBALI:+.0f}°")
    geser(servo1, SERVO1_KEMBALI)
    return sort_plan(label) or "servo diam"
