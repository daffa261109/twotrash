"""Loop pemilah: sensor melihat sampah, kamera memutuskan, servo bergerak."""

from __future__ import annotations

import time

from gpiozero import AngularServo, Buzzer, Device, DistanceSensor, LED
from picamera2 import Picamera2

from trash2trace.display import Display
from trash2trace.settings import (
    CAMERA_SIZE,
    CLEAR_DISTANCE_M,
    DETECT_DISTANCE_M,
    FRAME_GAP_S,
    FRAMES_PER_DECISION,
    PREVIEW_EVERY_S,
    SERVO_HOLD_S,
    SETTLE_AFTER_DETECT_S,
    Station,
)
from trash2trace.vision import Classifier, Prediction
from servo.pins import BUZZER_PIN, ECHO_PIN, LED_GREEN_PIN, LED_RED_PIN, SERVO_PIN, TRIG_PIN


class Sorter:
    def __init__(self, station: Station) -> None:
        self.station = station
        self.running = True
        print(f"[INFO] Menyala sebagai {station.title}")
        _use_pigpio_if_available()

        self.display = Display()
        self.distance = DistanceSensor(
            echo=ECHO_PIN,
            trigger=TRIG_PIN,
            max_distance=2.0,
            queue_len=5,
            partial=True,
        )
        self.servo = AngularServo(
            SERVO_PIN,
            min_angle=-90,
            max_angle=90,
            initial_angle=0,
            min_pulse_width=0.001,
            max_pulse_width=0.002,
        )
        self.led_green = LED(LED_GREEN_PIN)
        self.led_red = LED(LED_RED_PIN)
        self.buzzer = Buzzer(BUZZER_PIN)
        self.camera = Picamera2()
        self.camera.configure(
            self.camera.create_preview_configuration(
                main={"format": "RGB888", "size": CAMERA_SIZE}
            )
        )
        self.camera.start()
        time.sleep(1.2)
        self.classifier = Classifier()
        self._armed = True
        self._last_preview = 0.0
        self._rest("Menunggu sampah")

    def run(self) -> None:
        print(f"[INFO] {self.station.title} jalan.")
        self.display.show(self.station.title, "AI aktif", "Menunggu sampah")
        while self.running:
            if self._item_arrived():
                self._sort_one_item()
            elif self._preview_due():
                self._log_preview()
            time.sleep(0.05)

    def stop(self) -> None:
        self.running = False

    def close(self) -> None:
        self.stop()
        print("[INFO] Berhenti.")
        self._safe(self._release_outputs)
        self._safe(self.distance.close)
        self._safe(self.camera.stop)
        self.display.clear()

    def _item_arrived(self) -> bool:
        return self._armed and self.distance.distance <= DETECT_DISTANCE_M

    def _sort_one_item(self) -> None:
        self._armed = False
        distance_m = self.distance.distance
        print(f"[TRIGGER] {self.station.title} sampah terdeteksi: {distance_m:.3f} m")
        time.sleep(SETTLE_AFTER_DETECT_S)

        frames = []
        for _ in range(FRAMES_PER_DECISION):
            frames.append(self.camera.capture_array())
            time.sleep(FRAME_GAP_S)
        try:
            decision = self.classifier.decide(frames)
        except Exception as exc:
            print(f"[WARN] LLM: {exc}")
            decision = Prediction("other", 0.0)
        self._actuate(decision.label, decision.confidence)
        self._wait_until_clear()
        self._armed = True
        self._rest("Menunggu sampah")

    def _actuate(self, label: str, confidence: float) -> None:
        angle = self.station.angle_for(label)
        text = self.station.text_for(label)
        print(f"[SORT] {self.station.title} {label} | yakin={confidence:.2f} | servo={angle:+.0f}°")
        self.display.show(text, f"AI {confidence * 100:.0f}%", self.station.title)
        self._set_leds(label)
        self._beep()
        self.servo.angle = angle
        time.sleep(SERVO_HOLD_S)
        self.servo.angle = 0
        time.sleep(0.25)

    def _wait_until_clear(self) -> None:
        while self.running and self.distance.distance < CLEAR_DISTANCE_M:
            time.sleep(0.08)

    def _preview_due(self) -> bool:
        return time.monotonic() - self._last_preview >= PREVIEW_EVERY_S

    def _log_preview(self) -> None:
        self._last_preview = time.monotonic()
        print(f"[AI] {self.station.title} menunggu | jarak={self.distance.distance:.2f} m")

    def _set_leds(self, label: str) -> None:
        self.led_green.off()
        self.led_red.off()
        if label == "organic":
            self.led_green.on()
        else:
            self.led_red.on()

    def _beep(self) -> None:
        try:
            self.buzzer.on()
            time.sleep(0.08)
            self.buzzer.off()
        except Exception as exc:
            print(f"[WARN] Buzzer: {exc}")

    def _rest(self, message: str) -> None:
        self.led_green.off()
        self.led_red.off()
        self.servo.angle = 0
        self.display.show(self.station.title, message, "")

    def _release_outputs(self) -> None:
        self.led_green.off()
        self.led_red.off()
        self.buzzer.off()
        self.servo.angle = 0
        time.sleep(0.2)
        self.servo.detach()

    @staticmethod
    def _safe(action) -> None:
        try:
            action()
        except Exception as exc:
            print(f"[WARN] {exc}")


def _use_pigpio_if_available() -> None:
    try:
        from gpiozero.pins.pigpio import PiGPIOFactory

        Device.pin_factory = PiGPIOFactory()
    except Exception as exc:
        print(f"[WARN] pigpio tidak aktif, servo bisa sedikit bergetar: {exc}")
