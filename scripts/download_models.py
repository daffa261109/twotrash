#!/usr/bin/env python3
"""Unduh MobileNetV3-Small dan daftar label ImageNet ke folder models/."""

from __future__ import annotations

import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DESTINATION = ROOT / "models"

FILES = (
    (
        "https://huggingface.co/litert-community/MobileNet-v3-small/resolve/main/mobilenet_v3_small.tflite",
        DESTINATION / "mobilenet_v3_small.tflite",
    ),
    (
        "https://raw.githubusercontent.com/tensorflow/tensorflow/v2.16.1/tensorflow/lite/java/demo/app/src/main/assets/labels.txt",
        DESTINATION / "imagenet_labels.txt",
    ),
)


def download(url: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    print(f"Mengunduh {path.name} ...")
    urllib.request.urlretrieve(url, path)
    print(f"Selesai {path} ({path.stat().st_size} byte)")


def main() -> None:
    for url, path in FILES:
        download(url, path)
    print("Model siap. Program utama hanya menulis log, flap belum digerakkan.")


if __name__ == "__main__":
    main()
