"""
turntable.py — minimal Python driver for ComXim intelligent / programmable
turntables that expose the "CT" command set over USB-serial (or TCP).

Tested command set is documented in HARDWARE_AND_COMMANDS.md.

Quick use
---------
    from turntable import Turntable

    with Turntable("COM3") as tt:
        tt.rotate(36)          # 36 deg, one step, default direction
        tt.spin()              # continuous rotation
        tt.stop()              # stop

Everything is plain ASCII over pyserial at 115200 baud, 8N1.
Every command ends with ';' followed by a carriage return '\\r'.
"""

from __future__ import annotations

import time
from typing import List, Optional

try:
    import serial  # pyserial
    from serial.tools import list_ports
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "pyserial is required.  Install it with:  pip install pyserial"
    ) from exc


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_BAUDRATE = 115200
LINE_TERMINATOR = "\r"

# Direction codes as defined in the ComXim manual.
DIR_LEFT = 0
DIR_RIGHT = 1

# Rotation modes for CT+START / CT+SETMODE.
MODE_CONTINUOUS = 0
MODE_INTERMITTENT = 1
MODE_SWING = 2  # not supported on every model

# Error codes returned by the turntable as "CR+ERR=<n>;".
# Only a few are documented in the manual; extend this table from the
# "CT command list" PDF for your specific model if you need more detail.
ERROR_CODES = {
    31: "command timeout",
    40: "unsupported / unknown command",
}

# --- Commands that are NOT confirmed for every firmware revision ------------
# The manual documents CT+START, CT+SETMODE, CT+SETAUTOSHUTTER, CT+CAMERACTRL,
# CT+HEARTBEAT and CT+ACK.  The stop/speed commands below are the ones used by
# the TurntableX PC software and work on the units we have seen, but if your
# model answers "CR+ERR=40;" (unsupported command) just edit the strings here —
# nothing else in the code needs to change.
CMD_STOP = "CT+STOP();"
CMD_SET_SPEED = "CT+SETSPEED({level});"  # level is model dependent, often 1..10
# ---------------------------------------------------------------------------


class TurntableError(RuntimeError):
    """Raised when the turntable reports an error or cannot be reached."""


def list_serial_ports() -> List[str]:
    """Return a human-readable list of the serial ports on this computer."""
    return [f"{p.device}  —  {p.description}" for p in list_ports.comports()]


class Turntable:
    """A ComXim turntable on a serial port.

    Parameters
    ----------
    port
        Serial port name, e.g. ``"COM3"`` on Windows,
        ``"/dev/tty.usbserial-1420"`` on macOS, ``"/dev/ttyUSB0"`` on Linux.
    baudrate
        115200 for all ComXim units; do not change unless the manual says so.
    deg_per_sec
        Measured rotation speed, used to estimate how long a move takes so the
        script can wait for the move to finish.  Calibrate it once with a
        stopwatch (see README, "Calibrating deg_per_sec") and put the value in
        config.py.  Being 20 % too slow here is harmless — it only makes the
        script wait a little longer than necessary.
    move_overhead_s
        Fixed extra wait added to every move (acceleration, settling).
    dry_run
        If True, no serial port is opened and commands are only printed.
        Useful for checking a script's timing logic without hardware.
    time_scale
        Divides the waits after each move.  Leave at 1.0 for real runs; raise
        it during a dry run so a rehearsal finishes in seconds.
    verbose
        Print every command and reply.
    """

    def __init__(
        self,
        port: str,
        baudrate: int = DEFAULT_BAUDRATE,
        timeout: float = 1.0,
        deg_per_sec: float = 12.0,
        move_overhead_s: float = 1.5,
        dry_run: bool = False,
        time_scale: float = 1.0,
        verbose: bool = True,
    ) -> None:
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.deg_per_sec = float(deg_per_sec)
        self.move_overhead_s = float(move_overhead_s)
        self.dry_run = dry_run
        self.time_scale = max(float(time_scale), 1e-9)
        self.verbose = verbose
        self._ser: Optional["serial.Serial"] = None

    # -- connection ---------------------------------------------------------

    def open(self) -> "Turntable":
        if self.dry_run:
            self._log(f"[dry-run] pretending to open {self.port}")
            return self
        try:
            self._ser = serial.Serial(
                self.port, self.baudrate, timeout=self.timeout
            )
        except serial.SerialException as exc:
            raise TurntableError(
                f"Could not open {self.port}: {exc}\n"
                f"Available ports:\n  " + "\n  ".join(list_serial_ports())
            ) from exc
        # The USB-serial bridge (CH340) needs a moment before it accepts data.
        time.sleep(2.0)
        self._ser.reset_input_buffer()
        self._log(f"Connected to {self.port} at {self.baudrate} baud.")
        return self

    def close(self) -> None:
        if self._ser is not None and self._ser.is_open:
            self._ser.close()
            self._log("Serial port closed.")
        self._ser = None

    def __enter__(self) -> "Turntable":
        return self.open()

    def __exit__(self, *exc_info) -> None:
        # Always try to leave the table stopped, even after an error.
        try:
            self.stop()
        except Exception:  # noqa: BLE001 — never mask the original exception
            pass
        self.close()

    # -- raw I/O ------------------------------------------------------------

    def send(self, command: str, read_reply: bool = True) -> List[str]:
        """Send one raw CT command and return the reply lines.

        The trailing ';' and '\\r' are added automatically if missing.
        """
        if not command.endswith(";"):
            command += ";"
        payload = command + LINE_TERMINATOR

        self._log(f"-> {command}")
        if self.dry_run:
            return []
        if self._ser is None:
            raise TurntableError("Not connected — call open() first.")

        self._ser.write(payload.encode("ascii"))
        self._ser.flush()

        replies: List[str] = []
        if read_reply:
            # Replies are optional (they only arrive when ACK is on), so a
            # short read with a timeout is enough — never block forever.
            deadline = time.time() + self.timeout
            while time.time() < deadline:
                line = self._ser.readline().decode("ascii", "replace").strip()
                if not line:
                    break
                replies.append(line)
                self._log(f"<- {line}")
                self._raise_on_error(line)
        return replies

    @staticmethod
    def _raise_on_error(line: str) -> None:
        if "CR+ERR=" in line:
            digits = "".join(c for c in line.split("CR+ERR=")[1] if c.isdigit())
            code = int(digits) if digits else -1
            raise TurntableError(
                f"Turntable returned error {code} "
                f"({ERROR_CODES.get(code, 'see the CT command list for your model')})"
            )

    # -- motion -------------------------------------------------------------

    def rotate(
        self,
        degrees: float,
        direction: int = DIR_RIGHT,
        pause_s: int = 0,
        repeat: int = 1,
        shutter: bool = False,
        wait: bool = True,
    ) -> None:
        """Rotate by ``degrees`` and (by default) block until the move is done.

        ``degrees`` is rounded to the nearest whole degree because the firmware
        only accepts integers.  Use :meth:`rotate_sequence` or the helper in
        raman_sequence.py if you need fractional steps without drift.
        """
        deg = int(round(degrees))
        if deg <= 0:
            self._log("rotate(): nothing to do (0 deg).")
            return
        if direction not in (DIR_LEFT, DIR_RIGHT):
            raise ValueError("direction must be DIR_LEFT (0) or DIR_RIGHT (1)")

        self.send(
            f"CT+START({direction},{MODE_INTERMITTENT},{int(shutter)},"
            f"{deg},{int(pause_s)},{int(repeat)});"
        )
        if wait:
            time.sleep(self.motion_time(deg, pause_s, repeat) / self.time_scale)

    def motion_time(self, degrees: float, pause_s: int = 0, repeat: int = 1) -> float:
        """Estimated seconds for a move, from the calibrated speed."""
        per_move = abs(degrees) / self.deg_per_sec + self.move_overhead_s
        return repeat * (per_move + pause_s)

    def spin(self, direction: int = DIR_RIGHT, shutter: bool = False) -> None:
        """Rotate continuously until :meth:`stop` is called."""
        self.send(
            f"CT+START({direction},{MODE_CONTINUOUS},{int(shutter)},0,0,0);"
        )

    def stop(self) -> None:
        """Stop any motion immediately."""
        self.send(CMD_STOP)

    def set_speed(self, level: int) -> None:
        """Set the rotation speed level (range is model dependent)."""
        self.send(CMD_SET_SPEED.format(level=int(level)))

    # -- settings -----------------------------------------------------------

    def set_ack(self, on: bool = True) -> None:
        """Turn command acknowledgements (CR+... replies) on or off."""
        self.send(f"CT+ACK({int(on)});")

    def set_heartbeat(self, on: bool = True) -> None:
        self.send(f"CT+HEARTBEAT({int(on)});")

    def set_mode(self, mode: int) -> None:
        self.send(f"CT+SETMODE({int(mode)});")

    def set_auto_shutter(self, on: bool) -> None:
        """Emit a camera shutter pulse after every rotation step."""
        self.send(f"CT+SETAUTOSHUTTER({int(on)});")

    def camera(self, focus: bool = False, capture: bool = False) -> None:
        """Drive the camera trigger output directly."""
        self.send(f"CT+CAMERACTRL({int(focus)},{int(capture)});")

    # -- misc ---------------------------------------------------------------

    def _log(self, message: str) -> None:
        if self.verbose:
            print(message)
