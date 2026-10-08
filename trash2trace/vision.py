"""Foto dari kamera dikirim ke LLM, lalu digolongkan organic / nonorganic / other."""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from trash2trace.llm import LlmVision
from trash2trace.settings import MIN_CONFIDENCE, ROI


@dataclass(frozen=True)
class Prediction:
    label: str
    confidence: float


class Classifier:
    def __init__(self) -> None:
        self._llm = LlmVision()

    def predict(self, frame_rgb: np.ndarray) -> Prediction:
        ok, encoded = cv2.imencode(
            ".jpg",
            cv2.cvtColor(_crop(frame_rgb), cv2.COLOR_RGB2BGR),
            [int(cv2.IMWRITE_JPEG_QUALITY), 70],
        )
        if not ok:
            raise RuntimeError("Foto kamera gagal dijadikan JPEG")
        label, confidence = self._llm.classify(encoded.tobytes())
        return Prediction(label, confidence)

    def decide(self, frames: list[np.ndarray]) -> Prediction:
        samples = [self.predict(frame) for frame in frames]
        confident = [item for item in samples if item.confidence >= MIN_CONFIDENCE]
        if not confident:
            best = max(samples, key=lambda item: item.confidence)
            return Prediction("other", best.confidence)
        counts: dict[str, list[float]] = {}
        for item in confident:
            counts.setdefault(item.label, []).append(item.confidence)
        winner = max(counts, key=lambda label: len(counts[label]))
        scores = counts[winner]
        return Prediction(winner, sum(scores) / len(scores))


def _crop(frame_rgb: np.ndarray) -> np.ndarray:
    height, width = frame_rgb.shape[:2]
    rx, ry, rw, rh = ROI
    x1 = max(0, int(width * rx))
    y1 = max(0, int(height * ry))
    x2 = min(width, int(width * (rx + rw)))
    y2 = min(height, int(height * (ry + rh)))
    return frame_rgb[y1:y2, x1:x2]
