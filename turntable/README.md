# Turntable control for automated Raman measurements

Python control of a **ComXim intelligent / programmable turntable** from a
laptop, for stepping a set of samples through a Raman spectrometer.

You tell it the **total angle** of the run and the **number of samples**; it
works out the step angle, dwells at each position long enough to acquire a
spectrum, then returns the table to its starting position.

No prior knowledge of the turntable is needed — follow this file top to bottom.

> Part of the [Shell-Thurst4](../README.md) instrument-control repository.
> Every command below is run from **inside this `turntable/` folder**:
>
> ```bash
> cd turntable
> ```

---

## Contents

| File | What it is |
|---|---|
| `README.md` | This guide. Start here. |
| `config.py` | **The only file you normally edit.** Port, angles, sample count, timing. |
| `raman_sequence.py` | The experiment. Run this. |
| `turntable_cli.py` | Manual control from the terminal, for setup and testing. |
| `turntable.py` | The driver. You only open this if you are extending it. |
| `examples/basic_moves.py` | One-liner examples of every basic action. |
| `HARDWARE_AND_COMMANDS.md` | Command reference, error codes, WiFi settings. |
| `requirements.txt` | Python dependencies (just `pyserial`). |

---

## Part 1 — One-time setup

### Step 1. Check the model supports computer control

Look at the model label on the turntable. The letters mean:

- `U` = USB, `C` = serial, `W` = WiFi → **programmable, this code works**
- `R` = remote control only, `K` = knob, `A` = AC motor

If the model has no `U`, `C` or `W`, it cannot be driven from a computer at
all — stop here and check with the supplier.

This guide assumes **USB** (`U`). For WiFi see `HARDWARE_AND_COMMANDS.md` §2.

### Step 2. Install the USB driver

The turntable uses a CH340 USB-serial chip. Windows does not always have the
driver.

1. Download it from <https://comxim.com/download-usb-driver/> and install.
2. Connect the USB cable and switch the turntable on.
3. Wait for the self-test — **three beeps means it is ready** (3–9 s).
4. Find the port name:
   - **Windows**: Device Manager → *Ports (COM & LPT)* → something like
     `USB-SERIAL CH340 (COM3)`. The port is `COM3`.
   - **macOS**: `ls /dev/tty.*` → e.g. `/dev/tty.usbserial-1420`
   - **Linux**: `ls /dev/ttyUSB*` → e.g. `/dev/ttyUSB0`

If no new port appears: try another USB cable (some are charge-only), another
USB port, and confirm the driver installed without a warning triangle.

### Step 3. Install Python and the dependency

Python 3.8 or newer. Then, in this folder:

```bash
pip install -r requirements.txt
```

### Step 4. Tell the code which port to use

Open `config.py` and set:

```python
PORT = "COM3"        # whatever you found in Step 2
```

Check the code can see the port:

```bash
python turntable_cli.py ports
```

### Step 5. First move, and finding the direction

**Keep a hand near the power switch the first time.**

```bash
python turntable_cli.py test
```

The turntable should rotate 36°.

- **It did not move** → see Troubleshooting below.
- **It moved the wrong way** → in `config.py`, swap the two lines:
  ```python
  FORWARD_DIRECTION = DIR_LEFT
  REVERSE_DIRECTION = DIR_RIGHT
  ```
  The manual's "left/right" codes map to clockwise/counter-clockwise
  differently on different models, so this has to be found by testing.

### Step 6. Calibrate the rotation speed

The turntable does not report when a move has finished, so the script waits
for an estimated time based on the rotation speed. Measure it once:

```bash
python turntable_cli.py calibrate
```

Press Enter to start, press Enter again the moment the table stops. Put the
suggested value into `config.py`:

```python
DEG_PER_SEC = 12.0
```

Round **down** rather than up — a slightly low value just means the script
waits a little longer than needed, which is harmless. A value that is too
high means the next command arrives while the table is still moving.

Setup is done.

---

## Part 2 — Running an experiment

### Step 7. Describe the run in `config.py`

```python
TOTAL_ANGLE        = 360.0   # degrees swept over the whole run
N_SAMPLES          = 10      # number of samples = number of measurement stops
SPACING            = "wrap"  # "wrap" or "inclusive" — see below
MINUTES_PER_SAMPLE = 5.0     # dwell at each position = your acquisition time
MINUTES_BEFORE_RETURN = 5.0  # hold after the last sample, before going home
N_CYCLES           = 1       # None = repeat forever until Ctrl+C
```

**The step angle is derived, not typed in:**

| `SPACING` | Step angle | Use it when |
|---|---|---|
| `"wrap"` | `TOTAL_ANGLE / N_SAMPLES` | Samples are arranged around a **full circle**. 360° with 10 samples → 36° steps at 0, 36, … 324°. Position 10 is one step short of 360° because 360° *is* position 1. |
| `"inclusive"` | `TOTAL_ANGLE / (N_SAMPLES − 1)` | Samples lie along an **arc** and you want the first and last exactly on the ends. 180° with 5 samples → 45° steps at 0, 45, 90, 135, 180°. |

For a circular sample holder, use `"wrap"`.

### Step 8. Rehearse without hardware (optional but recommended)

Check the timing and the angle list before committing hours of instrument
time. In `config.py`:

```python
DRY_RUN = True
SPEEDUP = 600.0      # 1 minute of waiting becomes 0.1 s
```

```bash
python raman_sequence.py
```

It prints every command and every position. Set `DRY_RUN = False` and
`SPEEDUP = 1.0` again before the real run.

### Step 9. Run it

```bash
python raman_sequence.py
```

The script prints a summary, then works through the cycle:

```
  [1/10] already at 0 deg (start position)
    sample 1/10: waiting 5 min (until 14:32:10) ...
  [2/10] rotating 36 deg -> 36 deg
    sample 2/10: waiting 5 min (until 14:37:14) ...
  ...
    before return: waiting 5 min (until 15:22:41) ...
  returning to start: 324 deg reverse
--- Cycle 1 complete ---
```

Press **Ctrl+C** at any time — the turntable is told to stop and the port is
closed cleanly.

### Step 10. Match spectra to positions

Every measurement position is appended to `turntable_run_log.csv`:

```csv
timestamp,cycle,sample_index,target_angle_deg,commanded_angle_deg,event
2026-08-13T14:27:05,1,1,0.000,0,measure
2026-08-13T14:32:11,1,2,36.000,36,measure
```

Use the timestamps to pair each Raman spectrum with its sample index and
angle. Change or disable the file with `LOG_FILE` in `config.py`.

### Before a long unattended run

- **Disable laptop sleep.** If the laptop sleeps, the script stops mid-run.
  Windows: *Settings → System → Power → Screen and sleep → Sleep: Never* (on
  both battery and plugged in).
- Close TurntableX and the mobile app — only one program can hold the serial
  port at a time.
- Keep the laptop plugged in and make sure the USB cable cannot be pulled.
- Check cables on the sample stage can survive the total rotation. The script
  unwinds to the start after each cycle for exactly this reason.

---

## Part 3 — Manual control

`turntable_cli.py` gives direct control without writing a script:

```bash
python turntable_cli.py ports                  # list serial ports
python turntable_cli.py test                   # connect and rotate 36 deg
python turntable_cli.py rotate 36              # rotate 36 deg forward
python turntable_cli.py rotate 90 --reverse    # rotate 90 deg backward
python turntable_cli.py rotate 36 --repeat 10 --pause 3
python turntable_cli.py spin                   # continuous, Ctrl+C to stop
python turntable_cli.py stop                   # stop now
python turntable_cli.py speed 5                # speed level (model dependent)
python turntable_cli.py raw "CT+ACK(1);"       # any raw command
python turntable_cli.py calibrate              # measure deg/s
```

Add `--port COM7` to any of them to override `config.py`.

### From your own Python

```python
from turntable import Turntable, DIR_LEFT, DIR_RIGHT

with Turntable("COM3") as tt:
    tt.rotate(36)                                   # 36 deg, wait until done
    tt.rotate(90, direction=DIR_LEFT)               # the other way
    tt.rotate(36, pause_s=3, repeat=10)             # 10 steps, 3 s pause each
    tt.spin(direction=DIR_RIGHT)                    # continuous
    tt.stop()
    tt.set_speed(5)
    tt.camera(capture=True)                         # pulse the camera trigger
    tt.send("CT+START(1,1,0,45,2,4);")              # any raw command
```

The `with` block always stops the table and closes the port, even if your code
raises an error. See `examples/basic_moves.py` for the full set.

---

## Troubleshooting

| Symptom | What to do |
|---|---|
| No COM port appears | Driver not installed, or a charge-only USB cable. Redo Step 2 with a different cable. |
| `Could not open COM3` | Wrong port name, or another program (TurntableX, the mobile app, a previous Python run) is holding it. Close them; the available ports are listed in the error message. |
| Port opens, nothing moves | Model may not have `U`/`C`. Confirm with TurntableX that the hardware responds at all. Check the turntable beeped three times at power-on. |
| Moves the wrong direction | Swap `FORWARD_DIRECTION` / `REVERSE_DIRECTION` in `config.py`. |
| `CR+ERR=40` (unsupported command) | That command is not in your model's firmware. If it was `CT+STOP()` or `CT+SETSPEED()`, correct `CMD_STOP` / `CMD_SET_SPEED` at the top of `turntable.py` using your model's CT command list. |
| `CR+ERR=31` (timeout) | A command arrived while the table was still busy. Lower `DEG_PER_SEC` in `config.py` so the script waits longer. |
| Next command sent while still moving | Same fix: lower `DEG_PER_SEC`, or raise `MOVE_OVERHEAD_S`. |
| Positions drift over a long run | The turntable has no position feedback. Reduce `N_CYCLES`, re-zero by eye between cycles, or use a step angle that is a whole number of degrees. |
| Script stopped overnight | Laptop went to sleep. See "Before a long unattended run". |

## Known limitations

- **No absolute position feedback.** The turntable cannot tell you where it
  is. All positioning is relative to wherever it was when the script started,
  so set the start position by hand before running.
- **Whole degrees only.** The firmware rounds to 1°. The script compensates by
  rounding against the running total, keeping total error under 1° per cycle
  rather than accumulating each step.
- **Move completion is estimated, not detected.** This is why `DEG_PER_SEC`
  matters. If your model reports motion status in its CT command list, that
  would be a worthwhile addition to `turntable.py`.

Full command reference, error codes and WiFi settings:
[`HARDWARE_AND_COMMANDS.md`](HARDWARE_AND_COMMANDS.md).

---

## Contributing

Issues and pull requests are welcome — especially:

- confirmed `CT+STOP` / `CT+SETSPEED` syntax and speed ranges for specific models,
- additional `CR+ERR=` codes for the `ERROR_CODES` table,
- a WiFi (TCP) transport alongside the serial one.

If you get it working on a model not mentioned here, please open an issue
saying which model and whether the direction codes matched — that is the part
that costs everyone the most time.

## License and disclaimer

Released under the [MIT License](../LICENSE).

This is an independent, unofficial project. It is not affiliated with,
endorsed by, or supported by ComXim. The command set is used as documented in
the publicly available user guide. Motorised stages can pinch, snag cables and
drop samples — test any new sequence with nothing valuable on the table, and
keep the power switch within reach.
