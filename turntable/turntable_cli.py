"""
turntable_cli.py — drive the turntable by hand from a terminal.

Use this for setup, testing and troubleshooting before running an experiment.

    python turntable_cli.py ports                 # list serial ports
    python turntable_cli.py test                  # connect + rotate 36 deg
    python turntable_cli.py rotate 36             # rotate 36 deg forward
    python turntable_cli.py rotate 90 --reverse   # rotate 90 deg backward
    python turntable_cli.py spin                  # rotate continuously
    python turntable_cli.py stop                  # stop
    python turntable_cli.py speed 5               # set speed level
    python turntable_cli.py raw "CT+ACK(1);"      # send any raw CT command
    python turntable_cli.py calibrate             # time a 360 deg turn

Add --port COM7 to any command to override config.PORT.
"""

from __future__ import annotations

import argparse
import sys
import time

import config
from turntable import Turntable, TurntableError, list_serial_ports


def make_table(args) -> Turntable:
    return Turntable(
        port=args.port or config.PORT,
        baudrate=config.BAUDRATE,
        deg_per_sec=config.DEG_PER_SEC,
        move_overhead_s=config.MOVE_OVERHEAD_S,
        dry_run=config.DRY_RUN,
    )


def cmd_ports(_args) -> int:
    ports = list_serial_ports()
    if not ports:
        print("No serial ports found.  Is the turntable powered on and the "
              "USB driver installed?  See README Step 2.")
        return 1
    print("Serial ports on this computer:")
    for p in ports:
        print(f"  {p}")
    return 0


def cmd_test(args) -> int:
    with make_table(args) as tt:
        print("Rotating 36 deg forward — watch the turntable.")
        tt.rotate(36, direction=config.FORWARD_DIRECTION)
        print("If it moved, the connection works.")
        print("If it moved the WRONG way, swap FORWARD_DIRECTION and "
              "REVERSE_DIRECTION in config.py.")
    return 0


def cmd_rotate(args) -> int:
    direction = (
        config.REVERSE_DIRECTION if args.reverse else config.FORWARD_DIRECTION
    )
    with make_table(args) as tt:
        tt.rotate(
            args.degrees,
            direction=direction,
            pause_s=args.pause,
            repeat=args.repeat,
            shutter=args.shutter,
        )
    return 0


def cmd_spin(args) -> int:
    direction = (
        config.REVERSE_DIRECTION if args.reverse else config.FORWARD_DIRECTION
    )
    tt = make_table(args).open()
    try:
        tt.spin(direction=direction)
        print("Spinning.  Press Ctrl+C to stop.")
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print()
    finally:
        tt.stop()
        tt.close()
    return 0


def cmd_stop(args) -> int:
    tt = make_table(args).open()
    tt.stop()
    tt.close()
    return 0


def cmd_speed(args) -> int:
    with make_table(args) as tt:
        tt.set_speed(args.level)
    return 0


def cmd_raw(args) -> int:
    with make_table(args) as tt:
        tt.send(args.command)
    return 0


def cmd_calibrate(args) -> int:
    """Measure deg_per_sec: time a full turn with a stopwatch."""
    degrees = args.degrees
    tt = make_table(args).open()
    try:
        input(f"Mark the current position, then press Enter to rotate "
              f"{degrees} deg.  Start your stopwatch as it begins moving.")
        start = time.time()
        tt.rotate(degrees, direction=config.FORWARD_DIRECTION, wait=False)
        input("Press Enter the moment the turntable stops moving.")
        elapsed = time.time() - start
    finally:
        tt.close()

    if elapsed <= 0:
        print("Measurement failed.")
        return 1
    speed = degrees / elapsed
    print(f"\n  {degrees} deg took {elapsed:.1f} s  ->  {speed:.2f} deg/s")
    print(f"  Put a slightly conservative value in config.py, e.g.")
    print(f"      DEG_PER_SEC = {speed * 0.9:.1f}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Manual control of a ComXim turntable.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--port", help="serial port (overrides config.PORT)")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("ports", help="list serial ports").set_defaults(func=cmd_ports)
    sub.add_parser("test", help="connect and rotate 36 deg").set_defaults(func=cmd_test)

    r = sub.add_parser("rotate", help="rotate by a number of degrees")
    r.add_argument("degrees", type=float)
    r.add_argument("--reverse", action="store_true", help="rotate backwards")
    r.add_argument("--pause", type=int, default=0, help="pause seconds between repeats")
    r.add_argument("--repeat", type=int, default=1, help="number of repeats")
    r.add_argument("--shutter", action="store_true", help="pulse the shutter output")
    r.set_defaults(func=cmd_rotate)

    s = sub.add_parser("spin", help="rotate continuously until Ctrl+C")
    s.add_argument("--reverse", action="store_true")
    s.set_defaults(func=cmd_spin)

    sub.add_parser("stop", help="stop motion").set_defaults(func=cmd_stop)

    sp = sub.add_parser("speed", help="set speed level")
    sp.add_argument("level", type=int)
    sp.set_defaults(func=cmd_speed)

    raw = sub.add_parser("raw", help="send a raw CT command")
    raw.add_argument("command")
    raw.set_defaults(func=cmd_raw)

    c = sub.add_parser("calibrate", help="measure deg/s with a stopwatch")
    c.add_argument("--degrees", type=float, default=360.0)
    c.set_defaults(func=cmd_calibrate)

    return p


def main() -> int:
    args = build_parser().parse_args()
    try:
        return args.func(args)
    except TurntableError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
