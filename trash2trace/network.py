"""Cek apakah Wi-Fi sudah terhubung dan punya alamat IP."""

from __future__ import annotations

import subprocess
from pathlib import Path

from trash2trace.settings import WIFI_INTERFACE


def wifi_connected(interface: str = WIFI_INTERFACE) -> bool:
    try:
        state = Path(f"/sys/class/net/{interface}/operstate").read_text().strip()
    except OSError:
        return False
    if state != "up":
        return False
    try:
        result = subprocess.run(
            ["ip", "-4", "-o", "addr", "show", "dev", interface],
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return "inet " in result.stdout
