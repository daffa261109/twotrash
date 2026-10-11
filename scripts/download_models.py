#!/usr/bin/env python3
"""Unduh MobileNetV3-Small dan daftar label ImageNet ke folder models/."""

from __future__ import annotations

import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DESTINATION = ROOT / "models"

MODEL_URL = (
    "https://huggingface.co/litert-community/MobileNet-v3-small/resolve/main/"
    "mobilenet_v3_small.tflite"
)
LABEL_URL = "https://storage.googleapis.com/download.tensorflow.org/data/ImageNetLabels.txt"
MODEL_PATH = DESTINATION / "mobilenet_v3_small.tflite"
LABEL_PATH = DESTINATION / "imagenet_labels.txt"


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "twotrash"})
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return response.read()
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", exc)
        if getattr(reason, "errno", None) == -3:
            raise SystemExit(
                "Pi tidak bisa mengubah nama situs menjadi alamat IP.\n"
                "Coba:\n"
                "  ping -c 1 1.1.1.1\n"
                "  printf 'nameserver 1.1.1.1\\nnameserver 8.8.8.8\\n' | sudo tee /etc/resolv.conf\n"
                "Lalu jalankan skrip ini lagi."
            ) from exc
        raise SystemExit(f"Unduhan gagal: {exc}") from exc


def main() -> None:
    DESTINATION.mkdir(parents=True, exist_ok=True)
    print(f"Mengunduh {MODEL_PATH.name} ...")
    MODEL_PATH.write_bytes(fetch(MODEL_URL))
    print(f"Selesai {MODEL_PATH} ({MODEL_PATH.stat().st_size} byte)")

    print(f"Mengunduh {LABEL_PATH.name} ...")
    lines = fetch(LABEL_URL).decode("utf-8").splitlines()
    if lines and lines[0].strip().lower() == "background":
        lines = lines[1:]
    LABEL_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Selesai {LABEL_PATH} ({len(lines)} kelas)")
    print("Model siap. Program utama hanya menulis log, flap belum digerakkan.")


if __name__ == "__main__":
    main()
