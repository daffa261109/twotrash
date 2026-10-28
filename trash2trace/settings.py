"""Pengaturan mesin. Sudut ada di STATIONS. Token API diisi lewat file .env."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / ".env"
STATION_PATH = ROOT / "station.txt"
MODEL_PATH = ROOT / "models" / "mobilenet_v3_small.tflite"
LABEL_PATH = ROOT / "models" / "imagenet_labels.txt"
CAPTURE_DIR = ROOT / "captures"
# Flap tidak digerakkan. Hasil model hanya ditulis ke log dulu.
MOVE_FLAP = False

CAMERA_SIZE = (640, 480)  # USB MJPEG; unggahan API tetap dikecilkan terpisah.
MIN_CONFIDENCE = 0.60
# HC-SR04 dekat sering membaca sedikit di atas 3 cm. Pemicu 1–6 cm.
DETECT_MIN_M = 0.01
DETECT_MAX_M = 0.06
CLEAR_DISTANCE_M = 0.10
SETTLE_AFTER_DETECT_S = 0.18
# Setelah HC melihat sampah, layar menghitung mundur selama ini baru foto dikirim.
PLACE_WAIT_S = 3.0
MONITOR_PORT = 8080
# Satu foto per sampah, dibaca API bridge.
FRAMES_PER_DECISION = 1
FRAME_GAP_S = 0.07
SERVO_HOLD_S = 1.45
PREVIEW_EVERY_S = 1.0

OLED_WIDTH = 128
OLED_HEIGHT = 64
OLED_ADDR = 0x3C
# True kalau OLED terpasang terbalik: tampilan diputar 180 derajat.
OLED_FLIP = True
# Layar sambutan setelah Wi-Fi terhubung. Teks bawah berjalan dari kanan ke kiri.
WELCOME_TITLE = "TRASH2TRACE"
WELCOME_SCROLL = "Buang sampah pada tempatnya"
WIFI_INTERFACE = "wlan0"
# Foto ke API dikecilkan dulu supaya unggahan lebih cepat.
LLM_IMAGE_WIDTH = 320
BRIDGE_TIMEOUT_S = 45
# Gerakan setelah AI membaca sampah (dipakai preview). Jenis "other" tidak menggerakkan servo.
# Servo 1 memutar ke sudut ini dan menunggu. Servo 2 turun, naik lagi ke tegak (0),
# lalu setelah jeda servo 1 kembali ke 0.
SORT_ANGLES = {"organic": -45.0, "nonorganic": 45.0}
SORT_SETTLE_S = 1.0
TILT_DOWN_DEG = -45.0
TILT_HOLD_S = 1.5
TILT_UP_SETTLE_S = 1.0
SORT_WAIT_S = 3.0
LLM_IMAGE_QUALITY = 70
ROI = (0.08, 0.05, 0.84, 0.90)


@dataclass(frozen=True)
class Station:
    """Satu Pi, satu flap. Sudut diukur dari posisi tengah servo."""

    name: str
    title: str
    organic: float
    nonorganic: float
    other: float

    def angle_for(self, label: str) -> float:
        if label == "organic":
            return self.organic
        if label == "nonorganic":
            return self.nonorganic
        return self.other

    def text_for(self, label: str) -> str:
        if label == "organic":
            return "ORGANIK"
        return "NONORGANIK"


# Negatif = kiri, positif = kanan, 0 = tengah.
STATIONS = {
    "flap1": Station("flap1", "FLAP 1", organic=-60.0, nonorganic=60.0, other=0.0),
    "flap2": Station("flap2", "FLAP 2", organic=-60.0, nonorganic=60.0, other=0.0),
}


@dataclass(frozen=True)
class BridgeConfig:
    endpoint: str
    token: str


def load_bridge_config() -> BridgeConfig:
    _load_env_file(ENV_PATH)
    config = BridgeConfig(
        endpoint=os.environ.get("API_ENDPOINT", "https://twotrash.wbesoft.com/classify").strip(),
        token=os.environ.get("API_TOKEN", "").strip(),
    )
    if not config.token:
        raise SystemExit("Isi API_TOKEN di file .env, sama dengan token di server.")
    return config


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def load_station(name: str | None) -> Station:
    if name is None and STATION_PATH.exists():
        name = STATION_PATH.read_text(encoding="utf-8").strip().split()[0]
    station_name = (name or "flap1").lower()
    try:
        return STATIONS[station_name]
    except KeyError as exc:
        known = ", ".join(STATIONS)
        raise SystemExit(f"station harus salah satu dari: {known}") from exc
