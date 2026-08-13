"""
raman_sequence.py — main experiment script.

Steps the turntable through N_SAMPLES measurement positions spread over
TOTAL_ANGLE degrees, dwelling MINUTES_PER_SAMPLE at each one so the Raman
system can acquire, then returns to the starting position.

You set the TOTAL ANGLE and the NUMBER OF SAMPLES in config.py.
The step angle is derived from those two — you never type it in.

Run it with:      python raman_sequence.py
Stop it with:     Ctrl+C   (the turntable is told to stop before exiting)
"""

from __future__ import annotations

import csv
import os
import sys
import time
from datetime import datetime, timedelta

import config
from turntable import Turntable, TurntableError


# ---------------------------------------------------------------------------
# Plan
# ---------------------------------------------------------------------------


def build_positions(total_angle: float, n_samples: int, spacing: str):
    """Return (step_angle, [absolute angle of each measurement position])."""
    if n_samples < 1:
        raise ValueError("N_SAMPLES must be at least 1")
    if total_angle <= 0:
        raise ValueError("TOTAL_ANGLE must be positive")

    if spacing == "wrap":
        step = total_angle / n_samples
    elif spacing == "inclusive":
        if n_samples == 1:
            raise ValueError("'inclusive' spacing needs at least 2 samples")
        step = total_angle / (n_samples - 1)
    else:
        raise ValueError("SPACING must be 'wrap' or 'inclusive'")

    return step, [i * step for i in range(n_samples)]


def sleep_minutes(minutes: float, label: str) -> None:
    """Wait, printing the time the wait will end.  Honours config.SPEEDUP."""
    seconds = minutes * 60.0 / config.SPEEDUP
    if seconds <= 0:
        return
    ends = datetime.now() + timedelta(seconds=seconds)
    print(f"    {label}: waiting {minutes:g} min (until {ends:%H:%M:%S}) ...")
    time.sleep(seconds)


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------


class RunLog:
    """Appends one CSV row per measurement position."""

    HEADER = [
        "timestamp",
        "cycle",
        "sample_index",
        "target_angle_deg",
        "commanded_angle_deg",
        "event",
    ]

    def __init__(self, path):
        self.path = path
        self._fh = None
        self._writer = None
        if not path:
            return
        is_new = not os.path.exists(path)
        self._fh = open(path, "a", newline="", encoding="utf-8")
        self._writer = csv.writer(self._fh)
        if is_new:
            self._writer.writerow(self.HEADER)
            self._fh.flush()

    def write(self, cycle, index, target, commanded, event):
        if self._writer is None:
            return
        self._writer.writerow(
            [
                datetime.now().isoformat(timespec="seconds"),
                cycle,
                index,
                f"{target:.3f}",
                commanded,
                event,
            ]
        )
        self._fh.flush()

    def close(self):
        if self._fh is not None:
            self._fh.close()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    step, positions = build_positions(
        config.TOTAL_ANGLE, config.N_SAMPLES, config.SPACING
    )

    print("=" * 68)
    print("Turntable Raman sequence")
    print("=" * 68)
    print(f"  Port                : {config.PORT}"
          f"{'   (DRY RUN — no hardware)' if config.DRY_RUN else ''}")
    print(f"  Total angle         : {config.TOTAL_ANGLE:g} deg")
    print(f"  Samples             : {config.N_SAMPLES}")
    print(f"  Spacing             : {config.SPACING}")
    print(f"  -> step angle       : {step:g} deg")
    print(f"  -> positions        : "
          f"{', '.join(f'{p:g}' for p in positions)} deg")
    print(f"  Dwell per sample    : {config.MINUTES_PER_SAMPLE:g} min")
    print(f"  Wait before return  : {config.MINUTES_BEFORE_RETURN:g} min")
    print(f"  Cycles              : {config.N_CYCLES or 'unlimited'}")
    cycle_min = (
        config.N_SAMPLES * config.MINUTES_PER_SAMPLE + config.MINUTES_BEFORE_RETURN
    )
    print(f"  ~ one cycle         : {cycle_min:g} min "
          f"(plus a few seconds of motion per step)")
    print("=" * 68)

    log = RunLog(config.LOG_FILE)
    cycle = 0

    try:
        with Turntable(
            port=config.PORT,
            baudrate=config.BAUDRATE,
            deg_per_sec=config.DEG_PER_SEC,
            move_overhead_s=config.MOVE_OVERHEAD_S,
            dry_run=config.DRY_RUN,
            time_scale=config.SPEEDUP,
        ) as tt:
            while config.N_CYCLES is None or cycle < config.N_CYCLES:
                cycle += 1
                print(f"\n--- Cycle {cycle} ---")

                # Degrees actually commanded so far this cycle.  The firmware
                # only accepts whole degrees, so each move is rounded against
                # this running total instead of on its own.  That keeps the
                # rounding error below 1 deg for the whole run rather than
                # letting it accumulate step by step.
                commanded = 0

                for index, target in enumerate(positions):
                    if index > 0:
                        move = int(round(target)) - commanded
                        print(f"  [{index + 1}/{len(positions)}] rotating "
                              f"{move} deg -> {target:g} deg")
                        tt.rotate(
                            move,
                            direction=config.FORWARD_DIRECTION,
                            shutter=config.TRIGGER_SHUTTER,
                        )
                        commanded += move
                    else:
                        print(f"  [1/{len(positions)}] already at "
                              f"{target:g} deg (start position)")
                        if config.TRIGGER_SHUTTER:
                            tt.camera(capture=True)

                    log.write(cycle, index + 1, target, commanded, "measure")
                    sleep_minutes(
                        config.MINUTES_PER_SAMPLE,
                        f"sample {index + 1}/{len(positions)}",
                    )

                # All samples measured — hold, then unwind to the start.
                sleep_minutes(config.MINUTES_BEFORE_RETURN, "before return")

                if commanded > 0:
                    print(f"  returning to start: {commanded} deg reverse")
                    tt.rotate(commanded, direction=config.REVERSE_DIRECTION)
                log.write(cycle, 0, 0.0, 0, "returned_to_start")
                print(f"--- Cycle {cycle} complete ---")

            print("\nAll cycles finished.")
            return 0

    except KeyboardInterrupt:
        print("\nInterrupted by user — turntable stopped.")
        return 130
    except TurntableError as exc:
        print(f"\nTurntable error: {exc}", file=sys.stderr)
        return 1
    finally:
        log.close()


if __name__ == "__main__":
    sys.exit(main())
