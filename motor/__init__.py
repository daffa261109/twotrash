"""Kontrol motor DC Raspberry Pi Zero."""

from motor.controller import MotorController, clamp_speed, is_raspberry_pi
from motor.pins import BACKWARD_PIN, ENABLE_PIN, FORWARD_PIN

__all__ = [
    "BACKWARD_PIN",
    "ENABLE_PIN",
    "FORWARD_PIN",
    "MotorController",
    "clamp_speed",
    "is_raspberry_pi",
]
