"""Kendali motor DC di Raspberry Pi Zero lewat modul L298N."""

from __future__ import annotations

import sys
from types import TracebackType


def is_raspberry_pi() -> bool:
    try:
        with open("/proc/device-tree/model", encoding="utf-8") as model:
            return "Raspberry Pi" in model.read()
    except OSError:
        return False


def clamp_speed(speed: float) -> float:
    """Kecepatan 0.0 (diam) sampai 1.0 (penuh)."""
    if speed != speed or speed < 0.0 or speed > 1.0:
        raise ValueError("kecepatan harus di antara 0.0 dan 1.0")
    return float(speed)


class MotorController:
    """Satu motor DC pada kanal A L298N.

    `forward_pin` ke IN1, `backward_pin` ke IN2, `enable_pin` ke ENA.
    Nilai kecepatan positif = maju, negatif = mundur, nol = berhenti.
    """

    def __init__(
        self,
        forward_pin: int,
        backward_pin: int,
        enable_pin: int,
        *,
        dry_run: bool | None = None,
    ) -> None:
        self.forward_pin = forward_pin
        self.backward_pin = backward_pin
        self.enable_pin = enable_pin
        self.dry_run = not is_raspberry_pi() if dry_run is None else dry_run
        self._value = 0.0
        self._motor = None
        if not self.dry_run:
            self._motor = self._open_hardware()

    def _open_hardware(self):
        try:
            from gpiozero import Motor
        except ImportError as exc:
            raise SystemExit(
                "gpiozero belum terpasang. Di Pi jalankan: "
                "sudo apt install python3-gpiozero"
            ) from exc
        return Motor(
            forward=self.forward_pin,
            backward=self.backward_pin,
            enable=self.enable_pin,
            pwm=True,
        )

    @property
    def value(self) -> float:
        """-1.0 mundur penuh, 0 berhenti, 1.0 maju penuh."""
        return self._value

    def set_speed(self, speed: float) -> None:
        """`speed` dari -1.0 sampai 1.0. Tanda menentukan arah."""
        if speed != speed or speed < -1.0 or speed > 1.0:
            raise ValueError("kecepatan harus di antara -1.0 dan 1.0")
        self._value = float(speed)
        if self.dry_run:
            print(
                f"[dry-run] speed={self._value:+.2f} "
                f"IN1=GPIO{self.forward_pin} IN2=GPIO{self.backward_pin} "
                f"ENA=GPIO{self.enable_pin}",
                file=sys.stderr,
            )
            return
        assert self._motor is not None
        self._motor.value = self._value

    def forward(self, speed: float = 0.5) -> None:
        self.set_speed(clamp_speed(speed))

    def backward(self, speed: float = 0.5) -> None:
        self.set_speed(-clamp_speed(speed))

    def stop(self) -> None:
        self.set_speed(0.0)

    def close(self) -> None:
        self.stop()
        if self._motor is not None:
            self._motor.close()
            self._motor = None

    def __enter__(self) -> MotorController:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()
