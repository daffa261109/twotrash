"""Loop pemilah: sensor melihat sampah, kamera memutuskan, servo bergerak."""

from __future__ import annotations

import time
from datetime import datetime

import cv2
from gpiozero import AngularServo, Buzzer, Device, DistanceSensor, LED
from picamera2 import Picamera2

from trash2trace.display import Display
from trash2trace.settings import (
    BUZZER_FROM_M,
    CAMERA_SIZE,
    CAPTURE_DIR,
    CLEAR_DISTANCE_M,
    DETECT_MAX_M,
    DETECT_MIN_M,
    FRAME_GAP_S,
    FRAMES_PER_DECISION,
    MOVE_FLAP,
    PREVIEW_EVERY_S,
    SERVO_HOLD_S,
    SETTLE_AFTER_DETECT_S,
    Station,
)
from trash2trace.vision import Classifier, Prediction
from servo.pins import (
    BUZZER_PIN,
    ECHO_PIN,
    ILLUMINATION_PIN,
    LED_GREEN_PIN,
    LED_RED_PIN,
    SERVO_PIN,
    TRIG_PIN,
)


class Sorter:
    def __init__(self, station: Station) -> None:
        self.station = station
        self.running = True
        print(f"[INFO] Menyala sebagai {station.title}")
        lamp_pins = Device.pin_factory
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
        self.illumination = LED(ILLUMINATION_PIN, pin_factory=lamp_pins)
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
        self._lamp_on = False
        self._lamp_hold = False
        self._last_preview = 0.0
        self._rest("Menunggu sampah")

    def run(self) -> None:
        print(f"[INFO] {self.station.title} jalan.")
        self.display.clear()
        while self.running:
            distance_m = self.distance.distance
            ada_barang = DETECT_MIN_M <= distance_m <= DETECT_MAX_M
            if ada_barang:
                self._lamp_hold = True
            elif distance_m > CLEAR_DISTANCE_M:
                self._lamp_hold = False
            self._set_illumination(self._lamp_hold)
            if ada_barang and self._armed:
                self._sort_one_item(distance_m)
            elif distance_m > CLEAR_DISTANCE_M and not self._armed:
                self._rest("Menunggu sampah")
                self._armed = True
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
        distance_m = self.distance.distance
        return self._armed and DETECT_MIN_M <= distance_m <= DETECT_MAX_M

    def _sort_one_item(self, distance_m: float) -> None:
        self._armed = False
        pertama_cm = distance_m * 100
        time.sleep(0.12)
        kedua_cm = self.distance.distance * 100
        print(f"[HC] {self.station.title} barang: {pertama_cm:.1f} cm, {kedua_cm:.1f} cm")
        self.display.show("BENDA", f"{pertama_cm:.1f} / {kedua_cm:.1f}", self.station.title)
        if pertama_cm >= BUZZER_FROM_M * 100 or kedua_cm >= BUZZER_FROM_M * 100:
            print("[BUZZER] sekali")
            self._beep()

    def _set_illumination(self, ada_barang: bool) -> None:
        if ada_barang == self._lamp_on:
            return
        try:
            if ada_barang:
                self.illumination.on()
            else:
                self.illumination.off()
        except Exception as exc:
            print(f"[WARN] Lampu: {exc}")
            return
        self._lamp_on = ada_barang
        print("[LAMPU] nyala" if ada_barang else "[LAMPU] mati")

    def _save_frame(self, frame_rgb) -> str:
        CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
        path = CAPTURE_DIR / f"{datetime.now():%Y%m%d-%H%M%S}.jpg"
        ok = cv2.imwrite(str(path), cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR))
        if not ok:
            raise RuntimeError(f"Gagal menyimpan {path}")
        print(f"[FOTO] {path}")
        return path

    def _log_model(self, decision: Prediction, path, distance_m: float) -> None:
        print(
            f"[HASIL] {decision.label} | jarak={distance_m * 100:.1f} cm | "
            f"mentah={decision.raw_label} | yakin={decision.confidence:.2f} | foto={path.name}"
        )

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

    def _set_leds(self, label: str) -> None:
        self.led_green.off()
        self.led_red.off()
        if label == "organic":
            self.led_green.on()
        else:
            self.led_red.on()

    def _alert_off(self) -> None:
        self._safe(self.buzzer.off)

    def _beep(self) -> None:
        try:
            self.buzzer.on()
            time.sleep(0.2)
            self.buzzer.off()
        except Exception as exc:
            print(f"[WARN] Buzzer: {exc}")

    def _rest(self, message: str) -> None:
        self.led_green.off()
        self.led_red.off()
        self._alert_off()
        self.servo.angle = 0
        print(f"[AI] {self.station.title} {message}")
        self.display.clear()

    def _release_outputs(self) -> None:
        self.led_green.off()
        self.led_red.off()
        self.illumination.off()
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
