"""Klasifikasi satu foto dengan MobileNetV3-Small dalam berkas TFLite."""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from trash2trace.labels import canonical_class, load_labels
from trash2trace.settings import LABEL_PATH, MIN_CONFIDENCE, MODEL_PATH, ROI


@dataclass(frozen=True)
class Prediction:
    label: str
    confidence: float
    raw_label: str = ""


class Classifier:
    def __init__(self) -> None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Model tidak ketemu: {MODEL_PATH}\n"
                "Taruh MobileNetV3-Small .tflite hasil latihan sampah di sana."
            )
        self._labels = load_labels(LABEL_PATH)
        self._interpreter = _load_interpreter(MODEL_PATH)
        self._input = self._interpreter.get_input_details()[0]
        self._output = self._interpreter.get_output_details()[0]

    def predict(self, frame_rgb: np.ndarray) -> Prediction:
        tensor = _prepare(frame_rgb, self._input)
        self._interpreter.set_tensor(self._input["index"], tensor)
        self._interpreter.invoke()
        scores = _probabilities(self._interpreter.get_tensor(self._output["index"]), self._output)
        index = int(np.argmax(scores))
        if index >= len(self._labels):
            raise RuntimeError(
                f"Model mengeluarkan kelas {index}, labels.txt hanya punya {len(self._labels)}."
            )
        raw_label = self._labels[index]
        return Prediction(canonical_class(raw_label), float(scores[index]), raw_label)

    def predict_file(self, path) -> Prediction:
        encoded = np.fromfile(path, dtype=np.uint8)
        image = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
        if image is None:
            raise RuntimeError(f"Foto tidak bisa dibaca: {path}")
        return self.predict(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))

    def decide(self, frames: list[np.ndarray]) -> Prediction:
        samples = [self.predict(frame) for frame in frames]
        confident = [item for item in samples if item.confidence >= MIN_CONFIDENCE]
        if not confident:
            best = max(samples, key=lambda item: item.confidence)
            return Prediction("other", best.confidence, best.raw_label)
        counts: dict[str, list[Prediction]] = {}
        for item in confident:
            counts.setdefault(item.label, []).append(item)
        winner = max(counts, key=lambda label: len(counts[label]))
        chosen = counts[winner]
        confidence = sum(item.confidence for item in chosen) / len(chosen)
        raw_label = max(chosen, key=lambda item: item.confidence).raw_label
        return Prediction(winner, confidence, raw_label)


def _load_interpreter(path):
    try:
        from tflite_runtime.interpreter import Interpreter
    except ImportError:
        try:
            import tensorflow as tf

            Interpreter = tf.lite.Interpreter
        except ImportError as exc:
            raise SystemExit(
                "Pasang interpreter di Pi: sudo apt install python3-tflite-runtime"
            ) from exc
    interpreter = Interpreter(model_path=str(path))
    interpreter.allocate_tensors()
    return interpreter


def _prepare(frame_rgb: np.ndarray, details: dict) -> np.ndarray:
    _, height, width, _ = details["shape"]
    image = cv2.resize(_crop(frame_rgb), (int(width), int(height)), interpolation=cv2.INTER_AREA)
    if details["dtype"] == np.uint8:
        tensor = image.astype(np.uint8)
    else:
        scale, zero_point = details["quantization"]
        if scale:
            tensor = image.astype(np.float32) / scale + zero_point
        else:
            # Standar Keras MobileNetV3: piksel 0..255 menjadi -1..1.
            tensor = image.astype(np.float32) / 127.5 - 1.0
    return np.expand_dims(tensor, 0)


def _probabilities(raw: np.ndarray, details: dict) -> np.ndarray:
    values = np.asarray(raw, dtype=np.float32).reshape(-1)
    scale, zero_point = details["quantization"]
    if details["dtype"] == np.uint8 and scale:
        values = scale * (values - zero_point)
    if values.min() < 0 or values.max() > 1:
        values = values - np.max(values)
        values = np.exp(values)
    total = float(values.sum())
    if total <= 0:
        return np.ones_like(values) / max(len(values), 1)
    return values / total


def _crop(frame_rgb: np.ndarray) -> np.ndarray:
    height, width = frame_rgb.shape[:2]
    rx, ry, rw, rh = ROI
    x1 = max(0, int(width * rx))
    y1 = max(0, int(height * ry))
    x2 = min(width, int(width * (rx + rw)))
    y2 = min(height, int(height * (ry + rh)))
    return frame_rgb[y1:y2, x1:x2]
