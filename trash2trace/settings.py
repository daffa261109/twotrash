"""Pengaturan mesin. Sudut ada di STATIONS. LLM diisi lewat file .env."""

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

CAMERA_SIZE = (320, 240)
MIN_CONFIDENCE = 0.60
DETECT_DISTANCE_M = 0.18
CLEAR_DISTANCE_M = 0.28
SETTLE_AFTER_DETECT_S = 0.18
# Satu foto per sampah, dibaca model di Pi.
FRAMES_PER_DECISION = 1
FRAME_GAP_S = 0.07
SERVO_HOLD_S = 1.45
PREVIEW_EVERY_S = 1.0

OLED_WIDTH = 128
OLED_HEIGHT = 64
OLED_ADDR = 0x3C
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
class LlmConfig:
    provider: str
    endpoint: str
    api_key: str
    model: str


def load_llm_config() -> LlmConfig:
    _load_env_file(ENV_PATH)
    config = LlmConfig(
        provider=os.environ.get("LLM_PROVIDER", "").strip(),
        endpoint=os.environ.get("LLM_ENDPOINT", "").strip(),
        api_key=os.environ.get("LLM_API_KEY", "").strip(),
        model=os.environ.get("LLM_MODEL", "").strip(),
    )
    missing = [
        name
        for name, value in (
            ("LLM_PROVIDER", config.provider),
            ("LLM_ENDPOINT", config.endpoint),
            ("LLM_API_KEY", config.api_key),
            ("LLM_MODEL", config.model),
        )
        if not value
    ]
    if missing:
        joined = ", ".join(missing)
        raise SystemExit(f"Isi {joined} di file .env")
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
