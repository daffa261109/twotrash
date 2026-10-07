"""CLI: python3 -m servo angle --degrees 90"""

from __future__ import annotations

import argparse
import time

from servo.controller import ServoController
from servo.pins import SERVO_PIN


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Gerakkan servo MG996R dari Raspberry Pi Zero."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="cetak perintah tanpa menggerakkan GPIO (otomatis di luar Pi)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    angle = sub.add_parser("angle", help="tahan servo di sudut tertentu")
    angle.add_argument("--degrees", type=float, required=True, help="0 sampai 180")
    angle.add_argument(
        "--seconds",
        type=float,
        default=None,
        help="lama menahan posisi. Kosongkan untuk menahan sampai Ctrl+C",
    )

    center = sub.add_parser("center", help="tahan di 90 derajat")
    center.add_argument("--seconds", type=float, default=None)

    sweep = sub.add_parser("sweep", help="sapuan dari 0 ke 180 lalu kembali")
    sweep.add_argument("--step", type=float, default=10, help="langkah derajat")
    sweep.add_argument("--delay", type=float, default=0.05, help="jeda tiap langkah, detik")

    sub.add_parser("off", help="hentikan pulsa supaya servo lepas")
    return parser


def _hold(seconds: float | None) -> None:
    if seconds is None:
        print("Menahan posisi. Tekan Ctrl+C untuk melepas.", flush=True)
        while True:
            time.sleep(0.5)
    if seconds < 0:
        raise SystemExit("--seconds tidak boleh negatif")
    time.sleep(seconds)


def _travel(start: float, end: float, step: float) -> list[float]:
    points = [start]
    if start == end:
        return points
    direction = 1.0 if end > start else -1.0
    degrees = start
    while (direction > 0 and degrees < end) or (direction < 0 and degrees > end):
        degrees = degrees + direction * step
        if direction > 0 and degrees > end:
            degrees = end
        elif direction < 0 and degrees < end:
            degrees = end
        points.append(degrees)
        if degrees == end:
            break
    return points


def _sweep(servo: ServoController, step: float, delay: float) -> None:
    if step <= 0 or delay < 0:
        raise SystemExit("--step harus lebih dari 0 dan --delay tidak boleh negatif")
    for degrees in _travel(servo.min_angle, servo.max_angle, step):
        servo.set_angle(degrees)
        time.sleep(delay)
    for degrees in _travel(servo.max_angle, servo.min_angle, step)[1:]:
        servo.set_angle(degrees)
        time.sleep(delay)


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    dry_run = True if args.dry_run else None
    with ServoController(SERVO_PIN, dry_run=dry_run) as servo:
        try:
            if args.command == "off":
                servo.detach()
            elif args.command == "sweep":
                _sweep(servo, args.step, args.delay)
            elif args.command == "center":
                servo.center()
                _hold(args.seconds)
            else:
                servo.set_angle(args.degrees)
                _hold(args.seconds)
        except KeyboardInterrupt:
            pass
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
