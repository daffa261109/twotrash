"""Kontrol servo 3 kabel di Raspberry Pi Zero."""

from servo.controller import ServoController, is_raspberry_pi
from servo.pins import SERVO_PIN

__all__ = [
    "SERVO_PIN",
    "ServoController",
    "is_raspberry_pi",
]
