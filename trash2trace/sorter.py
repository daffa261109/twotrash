"""Loop pemilah: sensor melihat sampah, kamera memutuskan, servo bergerak."""

from __future__ import annotations

import math
import time
from datetime import datetime

import cv2
from gpiozero import Buzzer, Device, DistanceSensor, LED
from trash2trace.camera import open_camera

from trash2trace.display import Display
from trash2trace.monitor import Monitor
from trash2trace.bridge import BridgeVision
from trash2trace.network import wifi_connected
from trash2trace.servo_driver import StableServo, connect_pigpio, run_sort
from trash2trace.settings import (
    CAMERA_SIZE,
    CAPTURE_DIR,
    is_barang,
    is_penampang,
    FRAME_GAP_S,
    FRAMES_PER_DECISION,
    MOVE_FLAP,
    PLACE_WAIT_S,
    PREVIEW_EVERY_S,
    SERVO1_KEMBALI,
    SETTLE_AFTER_DETECT_S,
    WELCOME_TITLE,
    Station,
)
from servo.pins import (
    BUZZER_PIN,
    ECHO_PIN,
    ILLUMINATION_PIN,
    LED_GREEN_PIN,
    LED_RED_PIN,
    SERVO_PIN,
    SERVO_TILT_PIN,
    TRIG_PIN,
)


class Sorter:
    def __init__(self, station: Station) -> None:
        self.station = station
        self.running = True
        print(f"[INFO] Menyala sebagai {station.title}")
        lamp_pins = Device.pin_factory
        # LED status dibuat pertama: merah menyala segera, hijau menunggu Wi-Fi.
        self.led_red = LED(LED_RED_PIN, pin_factory=lamp_pins)
        self.led_green = LED(LED_GREEN_PIN, pin_factory=lamp_pins)
        self.led_green.off()
        self.led_red.on()
        self._net_ok = False
        self._last_net_check = 0.0
        self._clear_streak = 0
        _use_pigpio_if_available()
        # Matikan dulu, sebelum kamera dan sensor. Restart sering meninggalkan pin ini HIGH.
        self.buzzer = Buzzer(BUZZER_PIN, initial_value=False)
        self.buzzer.off()

        self.display = Display()
        self.distance = DistanceSensor(
            echo=ECHO_PIN,
            trigger=TRIG_PIN,
            max_distance=2.0,
            queue_len=5,
            partial=True,
        )
        self._pi = connect_pigpio()
        self.servo = StableServo(self._pi, SERVO_PIN)
        self.tilt = StableServo(self._pi, SERVO_TILT_PIN)
        self.servo.angle = SERVO1_KEMBALI
        self.tilt.angle = SERVO1_KEMBALI
        self.illumination = LED(ILLUMINATION_PIN, pin_factory=lamp_pins)
        self.monitor = Monitor(None)
        try:
            self.monitor.start()
            self.monitor.open_fullscreen()
            self.camera = open_camera(CAMERA_SIZE)
            self.monitor.attach_camera(self.camera)
        except Exception:
            self.monitor.close()
            raise
        time.sleep(1.2)
        self.vision = _load_bridge()
        # Baru aktif setelah jarak kosong terbaca stabil, supaya restart tidak membunyikan buzzer.
        self._armed = False
        self._oled_result = False
        self._lamp_on = False
        self._lamp_hold = False
        self._last_preview = 0.0
        self._rest("Menunggu sampah")

    def run(self) -> None:
        print(f"[INFO] {self.station.title} jalan.")
        self._show_idle()
        while self.running:
            self._check_network()
            distance_m = self.distance.distance
            ada_barang = is_barang(distance_m)
            if ada_barang:
                self._lamp_hold = True
                self._clear_streak = 0
            elif is_penampang(distance_m):
                self._lamp_hold = False
                if not self._armed:
                    self._clear_streak += 1
                    if self._clear_streak >= 4:
                        self._rest("Menunggu sampah")
                        self._armed = True
            self._set_illumination(self._lamp_hold)
            if ada_barang and self._armed:
                self._sort_one_item(distance_m)
            time.sleep(0.05)

    def stop(self) -> None:
        self.running = False

    def close(self) -> None:
        self.stop()
        print("[INFO] Berhenti.")
        self._safe(self._release_outputs)
        self._safe(self.distance.close)
        self._safe(self.monitor.close)
        self._safe(self.camera.close)
        self._safe(self.display.stop_idle)
        self.display.clear()

    def _item_arrived(self) -> bool:
        distance_m = self.distance.distance
        return self._armed and is_barang(distance_m)

    def _sort_one_item(self, distance_m: float) -> None:
        self._armed = False
        self._oled_result = False
        pertama_cm = distance_m * 100
        time.sleep(0.12)
        kedua_cm = self.distance.distance * 100
        print(f"[HC] {self.station.title} barang: {pertama_cm:.1f} cm, {kedua_cm:.1f} cm")
        if is_penampang(self.distance.distance):
            self._show_idle()
            return
        seconds = max(1, math.ceil(PLACE_WAIT_S))
        self.monitor.waiting(seconds)
        self.display.show("TUNGGU", f"{seconds}")
        if self._wait_before_capture():
            self._show_idle()
            return
        frame = self.monitor.frame_bgr()
        path = None
        if frame is None:
            print("[WARN] Foto: gambar tidak terbaca")
            self.monitor.fail("Gambar tidak terbaca")
            self.display.show("GAGAL", "Kamera")
        else:
            try:
                path = self._save_frame(frame)
            except Exception as exc:
                print(f"[WARN] Foto: {exc}")
                self.monitor.fail("Foto gagal disimpan")
                self.display.show("GAGAL", "Foto")
        if path is not None:
            self._read_with_bridge(path)

    def _wait_before_capture(self) -> bool:
        """True kalau benda disingkirkan sebelum waktu tunggu selesai."""
        deadline = time.monotonic() + PLACE_WAIT_S
        shown = None
        while self.running:
            left = deadline - time.monotonic()
            if left <= 0:
                return is_penampang(self.distance.distance)
            if is_penampang(self.distance.distance):
                return True
            seconds = max(1, math.ceil(left))
            self.monitor.waiting(seconds)
            if seconds != shown:
                self.display.show("TUNGGU", f"{seconds}")
                shown = seconds
            time.sleep(0.1)
        return True

    def _read_with_bridge(self, path) -> None:
        """Kirim foto ke API bridge dan tampilkan jenis sampah di OLED."""
        if self.vision is None:
            self.monitor.fail("API belum siap")
            return
        self.display.show("MEMBACA", "API...", path.name)
        self.monitor.reading()
        started = time.monotonic()
        try:
            reading = self.vision.classify(path.read_bytes())
        except Exception as exc:
            print(f"[WARN] API: {exc}")
            self.display.show("AI GAGAL", str(exc)[:20], path.name)
            self.monitor.fail(str(exc)[:80])
            return
        took = time.monotonic() - started
        label = reading.label
        text = _LABEL_TEXT.get(label, label.upper())
        item = " ".join(reading.item.replace("_", " ").split())
        print(f"[AI] {label} | {item or '-'} | {took:.1f} detik | foto={path.name}")
        self.display.show_result(text, item)
        self._oled_result = True
        self.monitor.result(label, f"{took:.1f} detik", item)
        print("[BUZZER] jawaban API")
        self._beep()
        print(f"[SERVO] {run_sort(self.servo, self.tilt, label)}")

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

    def _save_frame(self, frame_bgr):
        CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
        path = CAPTURE_DIR / f"{datetime.now():%Y%m%d-%H%M%S}.jpg"
        ok = cv2.imwrite(str(path), frame_bgr)
        if not ok:
            raise RuntimeError(f"Gagal menyimpan {path}")
        print(f"[FOTO] {path}")
        return path

    def _actuate(self, label: str, confidence: float) -> None:
        text = self.station.text_for(label)
        print(f"[SORT] {self.station.title} {label} | yakin={confidence:.2f}")
        self.display.show(text, f"AI {confidence * 100:.0f}%", self.station.title)
        run_sort(self.servo, self.tilt, label)

    def _wait_until_clear(self) -> None:
        while self.running and not is_penampang(self.distance.distance):
            time.sleep(0.08)

    def _preview_due(self) -> bool:
        return time.monotonic() - self._last_preview >= PREVIEW_EVERY_S

    def _log_preview(self) -> None:
        self._last_preview = time.monotonic()

    def _check_network(self) -> None:
        """Merah menyala sampai Wi-Fi terhubung, lalu hijau menyala terus."""
        if self._net_ok:
            return
        now = time.monotonic()
        if now - self._last_net_check < 1.0:
            return
        self._last_net_check = now
        if not wifi_connected():
            return
        self._net_ok = True
        self.led_red.off()
        self.led_green.on()
        print("[WIFI] terhubung, LED hijau menyala")
        self.display.start_idle()

    def _show_idle(self) -> None:
        if self._net_ok:
            if not self._oled_result:
                self.display.idle()
            self.monitor.ready()
        else:
            self.display.show(WELCOME_TITLE, "Menunggu Wi-Fi")
            self.monitor.waiting_wifi()

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
        self._alert_off()
        self.servo.angle = SERVO1_KEMBALI
        self.tilt.angle = SERVO1_KEMBALI
        print(f"[AI] {self.station.title} {message}")
        self._show_idle()

    def _release_outputs(self) -> None:
        # LED hijau/merah dibiarkan menyala sampai proses berhenti.
        self.illumination.off()
        self.buzzer.off()
        self.servo.angle = SERVO1_KEMBALI
        self.tilt.angle = SERVO1_KEMBALI
        time.sleep(0.2)
        self.servo.detach()
        self.tilt.detach()
        if self._pi is not None:
            self._pi.stop()

    @staticmethod
    def _safe(action) -> None:
        try:
            action()
        except Exception as exc:
            print(f"[WARN] {exc}")


_LABEL_TEXT = {"organic": "ORGANIK", "nonorganic": "NONORGANIK", "other": "LAINNYA"}


def _load_bridge():
    """Pembaca sampah: API bridge lewat internet. Tanpa token, foto tetap disimpan."""
    try:
        return BridgeVision()
    except (Exception, SystemExit) as exc:
        print(f"[WARN] API belum siap, sampah tidak dibaca: {exc}")
        return None


def _use_pigpio_if_available() -> None:
    try:
        from gpiozero.pins.pigpio import PiGPIOFactory

        Device.pin_factory = PiGPIOFactory()
    except Exception as exc:
        print(f"[WARN] pigpio tidak aktif, servo bisa sedikit bergetar: {exc}")
