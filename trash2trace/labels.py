"""Label model dan penggolongan ke organik / nonorganik / other."""

from __future__ import annotations

from pathlib import Path

_NONORGANIC = (
    "nonorganic",
    "non organic",
    "anorganik",
    "inorganic",
    "plastic",
    "plastik",
    "paper",
    "kertas",
    "glass",
    "kaca",
    "metal",
    "logam",
    "kaleng",
    "botol",
    "bottle",
    "jug",
    "jar",
    "cardboard",
    "kardus",
)


def load_labels(path: Path) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(f"Label tidak ketemu: {path}")

    labels: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(maxsplit=1)
        if len(parts) == 2 and parts[0].isdigit():
            labels.append(parts[1].strip())
        else:
            labels.append(line)

    if not labels:
        raise ValueError("labels.txt kosong")
    return labels


def canonical_class(label: str) -> str:
    text = label.strip().lower().replace("_", " ").replace("-", " ")
    if any(word in text for word in _NONORGANIC):
        return "nonorganic"
    if "organic" in text or "organik" in text:
        return "organic"
    return "other"
