"""Menjalankan pemilah. Station dibaca dari station.txt."""

from __future__ import annotations

import argparse
import signal

from trash2trace.settings import STATIONS, load_station


def _nyalakan_led_awal():
    """Merah nyala sebelum impor berat, supaya lampu hidup begitu proses mulai."""
    print("[INFO] trash2trace mulai", flush=True)
    try:
        from gpiozero import LED
        from servo.pins import LED_GREEN_PIN, LED_RED_PIN

        hijau = LED(LED_GREEN_PIN)
        merah = LED(LED_RED_PIN)
        hijau.off()
        merah.on()
        print("[LED] merah nyala", flush=True)
        return merah, hijau
    except Exception as exc:
        print(f"[WARN] LED: {exc}", flush=True)
        return None


def _lepas_led_awal(lampu) -> None:
    if not lampu:
        return
    for led in lampu:
        try:
            led.close()
        except Exception:
            pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pemilah sampah. Jalan otomatis lewat station.txt.")
    parser.add_argument("--station", choices=sorted(STATIONS), help="flap1 atau flap2")
    args = parser.parse_args(argv)

    lampu = _nyalakan_led_awal()
    from trash2trace.sorter import Sorter

    _lepas_led_awal(lampu)
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
