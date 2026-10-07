"""Kendali servo MG996R dari Raspberry Pi Zero."""

from __future__ import annotations

import sys
from types import TracebackType


def is_raspberry_pi() -> bool:
    try:
        with open("/proc/device-tree/model", encoding="utf-8") as model:
            return "Raspberry Pi" in model.read()
    except OSError:
        return False


# MG996R, 50 Hz: 500 µs = 0°, 1500 µs = 90°, 2500 µs = 180°.
MIN_PULSE_WIDTH = 0.5 / 1000
MAX_PULSE_WIDTH = 2.5 / 1000
FRAME_WIDTH = 20 / 1000


class ServoController:
    """Servo posisi MG996R.

    `signal_pin` ke kabel sinyal. Daya 5 V eksternal dan ground tidak dikontrol dari kode.
    Sudut ditahan hanya selama objek ini masih hidup.
    """

    def __init__(
        self,
        signal_pin: int,
        *,
        min_angle: float = 0,
        max_angle: float = 180,
        dry_run: bool | None = None,
    ) -> None:
        if min_angle >= max_angle:
            raise ValueError("min_angle harus lebih kecil dari max_angle")
        self.signal_pin = signal_pin
        self.min_angle = float(min_angle)
        self.max_angle = float(max_angle)
        self.dry_run = not is_raspberry_pi() if dry_run is None else dry_run
        self._angle: float | None = None
        self._servo = None
        if not self.dry_run:
            self._servo = self._open_hardware()

    def _open_hardware(self):
        try:
            from gpiozero import AngularServo
        except ImportError as exc:
            raise SystemExit(
                "gpiozero belum terpasang. Di Pi jalankan: "
                "sudo apt install python3-gpiozero"
            ) from exc

        factory = None
        try:
            from gpiozero.pins.pigpio import PiGPIOFactory

            factory = PiGPIOFactory()
        except Exception:
            print(
                "pigpio tidak aktif, memakai software PWM. Servo bisa sedikit bergetar.\n"
                "Lebih halus: sudo apt install python3-pigpio && "
                "sudo systemctl enable --now pigpiod",
                file=sys.stderr,
            )

        kwargs = {
            "initial_angle": None,
            "min_angle": self.min_angle,
            "max_angle": self.max_angle,
            "min_pulse_width": MIN_PULSE_WIDTH,
            "max_pulse_width": MAX_PULSE_WIDTH,
            "frame_width": FRAME_WIDTH,
        }
        if factory is not None:
            kwargs["pin_factory"] = factory
        return AngularServo(self.signal_pin, **kwargs)

    @property
    def angle(self) -> float | None:
        """Sudut terakhir, atau None jika pulsa sudah dilepas."""
        return self._angle

    def set_angle(self, degrees: float) -> None:
        if degrees != degrees or degrees < self.min_angle or degrees > self.max_angle:
            raise ValueError(
                f"sudut harus di antara {self.min_angle:g} dan {self.max_angle:g}"
            )
        self._angle = float(degrees)
        if self.dry_run:
            print(
                f"[dry-run] angle={self._angle:.0f} sinyal=GPIO{self.signal_pin}",
                file=sys.stderr,
            )
            return
        assert self._servo is not None
        self._servo.angle = self._angle

    def center(self) -> None:
        self.set_angle((self.min_angle + self.max_angle) / 2)

    def detach(self) -> None:
        """Hentikan pulsa. Servo tidak lagi menahan posisi."""
        self._angle = None
        if self.dry_run:
            print(
                f"[dry-run] detach sinyal=GPIO{self.signal_pin}",
                file=sys.stderr,
            )
            return
        if self._servo is not None:
            self._servo.detach()

    def close(self) -> None:
        if self._angle is not None or self._servo is not None:
            self.detach()
        if self._servo is not None:
            self._servo.close()
            self._servo = None

    def __enter__(self) -> ServoController:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()
