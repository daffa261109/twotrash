"""Kirim foto sampah ke API bridge twotrash.wbesoft.com."""

from __future__ import annotations

import json
import uuid
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# Cloudflare menolak User-Agent Python-urllib dengan 403 kode 1010 sebelum permintaan sampai ke server.
_USER_AGENT = "Mozilla/5.0 (X11; Linux aarch64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

from trash2trace.settings import (
    BRIDGE_TIMEOUT_S,
    LLM_IMAGE_QUALITY,
    LLM_IMAGE_WIDTH,
    load_bridge_config,
)


class BridgeVision:
    def __init__(self, config=None) -> None:
        self.config = config or load_bridge_config()
        print(f"[INFO] Bridge {self.config.endpoint}")

    def classify(self, jpeg: bytes) -> tuple[str, float]:
        jpeg = _shrink(jpeg)
        boundary = f"----trash2trace{uuid.uuid4().hex}"
        body = _multipart(boundary, jpeg)
        request = Request(
            self.config.endpoint,
            data=body,
            headers={
                "User-Agent": _USER_AGENT,
                "X-API-Token": self.config.token,
                "Content-Type": f"multipart/form-data; boundary={boundary}",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=BRIDGE_TIMEOUT_S) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:300]
            raise RuntimeError(f"Bridge menolak permintaan ({exc.code}): {detail}") from exc
        except URLError as exc:
            raise RuntimeError(f"Bridge tidak terjangkau: {exc.reason}") from exc
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Jawaban bridge bukan JSON: {exc}") from exc
        return _parse_flags(payload)


def ping(config=None) -> str:
    """Cek server merespons. Tanpa token yang benar biasanya 401, itu sudah cukup."""
    config = config or load_bridge_config()
    request = Request(config.endpoint, method="GET", headers={"User-Agent": _USER_AGENT})
    try:
        with urlopen(request, timeout=10) as response:
            return f"HTTP {response.status}"
    except HTTPError as exc:
        return f"HTTP {exc.code}"
    except URLError as exc:
        raise RuntimeError(f"Bridge tidak terjangkau: {exc.reason}") from exc


def _parse_flags(payload: dict) -> tuple[str, float]:
    organic = bool(payload.get("organic"))
    anorganic = bool(payload.get("anorganic") or payload.get("nonorganic"))
    other = bool(payload.get("other"))
    chosen = [name for name, flag in (("organic", organic), ("nonorganic", anorganic), ("other", other)) if flag]
    if len(chosen) == 1:
        return chosen[0], 1.0
    if not chosen:
        raise RuntimeError(f"Bridge tidak menandai jenis sampah: {payload}")
    raise RuntimeError(f"Bridge menandai lebih dari satu jenis: {payload}")


def _multipart(boundary: str, jpeg: bytes) -> bytes:
    crlf = b"\r\n"
    lines = [
        f"--{boundary}".encode(),
        b"Content-Disposition: form-data; name=image; filename=foto.jpg",
        b"Content-Type: image/jpeg",
        b"",
        jpeg,
        f"--{boundary}--".encode(),
        b"",
    ]
    return crlf.join(lines)


def _shrink(jpeg: bytes) -> bytes:
    """Kecilkan foto sebelum dikirim. Unggahan kecil lebih cepat di Pi Zero."""
    try:
        import cv2
        import numpy as np

        image = cv2.imdecode(np.frombuffer(jpeg, dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            return jpeg
        height, width = image.shape[:2]
        if width > LLM_IMAGE_WIDTH:
            image = cv2.resize(
                image,
                (LLM_IMAGE_WIDTH, round(height * LLM_IMAGE_WIDTH / width)),
                interpolation=cv2.INTER_AREA,
            )
        ok, encoded = cv2.imencode(".jpg", image, [int(cv2.IMWRITE_JPEG_QUALITY), LLM_IMAGE_QUALITY])
        return encoded.tobytes() if ok else jpeg
    except Exception:
        return jpeg
