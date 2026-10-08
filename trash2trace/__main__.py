"""Menjalankan pemilah. Station dibaca dari station.txt."""

from __future__ import annotations

import argparse
import signal

from trash2trace.settings import STATIONS, load_station
from trash2trace.sorter import Sorter


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pemilah sampah. Jalan otomatis lewat station.txt.")
    parser.add_argument("--station", choices=sorted(STATIONS), help="flap1 atau flap2")
    args = parser.parse_args(argv)

    sorter = Sorter(load_station(args.station))

    def stop(signum, frame) -> None:
        sorter.stop()

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    try:
        sorter.run()
        return 0
    except KeyboardInterrupt:
        return 0
    except Exception as exc:
        print("[FATAL]", exc)
        return 1
    finally:
        sorter.close()


if __name__ == "__main__":
    raise SystemExit(main())
