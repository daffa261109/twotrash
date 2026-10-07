"""Kontrol servo 3 kabel di Raspberry Pi Zero."""

from servo.controller import ServoController, is_raspberry_pi
from servo.pins import SIGNAL_PIN

__all__ = [
    "SIGNAL_PIN",
    "ServoController",
    "is_raspberry_pi",
]
