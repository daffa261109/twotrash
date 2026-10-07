"""CLI: python3 -m motor forward --speed 0.4 --seconds 3"""

from __future__ import annotations

import argparse
import time

from motor.controller import MotorController
from motor.pins import BACKWARD_PIN, ENABLE_PIN, FORWARD_PIN


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Putar motor DC di Raspberry Pi Zero lewat L298N."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="cetak perintah tanpa menggerakkan GPIO (otomatis di luar Pi)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    for name, help_text in (
        ("forward", "putar maju"),
        ("backward", "putar mundur"),
    ):
        cmd = sub.add_parser(name, help=help_text)
        cmd.add_argument(
            "--speed",
            type=float,
            default=0.4,
            help="0.0 sampai 1.0 (default 0.4)",
        )
        cmd.add_argument(
            "--seconds",
            type=float,
            default=2.0,
            help="lama berputar, lalu berhenti (default 2)",
        )

    sub.add_parser("stop", help="paksa motor berhenti")

    demo = sub.add_parser("demo", help="maju, berhenti, mundur, berhenti")
    demo.add_argument("--speed", type=float, default=0.4)
    demo.add_argument(
        "--seconds",
        type=float,
        default=2.0,
        help="lama tiap arah (default 2)",
    )
    return parser


def _spin(motor: MotorController, direction: str, speed: float, seconds: float) -> None:
    if seconds < 0:
        raise SystemExit("--seconds tidak boleh negatif")
    if direction == "forward":
        motor.forward(speed)
    else:
        motor.backward(speed)
    time.sleep(seconds)
    motor.stop()


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    dry_run = True if args.dry_run else None
    with MotorController(
        FORWARD_PIN,
        BACKWARD_PIN,
        ENABLE_PIN,
        dry_run=dry_run,
    ) as motor:
        try:
            if args.command == "stop":
                motor.stop()
            elif args.command == "demo":
                _spin(motor, "forward", args.speed, args.seconds)
                time.sleep(0.5)
                _spin(motor, "backward", args.speed, args.seconds)
            else:
                _spin(motor, args.command, args.speed, args.seconds)
        except KeyboardInterrupt:
            motor.stop()


if __name__ == "__main__":
    main()
