# Hardware and CT command reference

Reference notes for the ComXim intelligent / programmable turntable, taken from
the *Intelligent Programmable Turntable User Guide V1.5* and the MT-series
manual. Keep this next to the code; it is what you need when a command does
not behave as expected.

---

## 1. Which models can be controlled from a computer

The letters in the model name tell you what the unit supports:

| Letter | Meaning |
|---|---|
| `A` | AC motor — spins in an arbitrary direction when powered on |
| `K` | Knob for speed adjustment |
| `R` | Infrared remote control |
| `U` | **USB** — secondary development (this is what the code here uses) |
| `C` | **Serial (RS-232/485)** — secondary development |
| `W` | **WiFi** — secondary development over TCP |

Example: `MT320RUBL40` → remote + USB, 40 kg load.

**Only models containing `U`, `C` or `W` can be programmed.** If your model has
none of those letters, it is remote-control only and this code cannot drive it.

---

## 2. Connection settings

### USB / serial (models with `U` or `C`)

| Setting | Value |
|---|---|
| Driver | CH340 USB-serial (from ComXim's download page) |
| Baud rate | **115200** |
| Data bits / parity / stop bits | 8 / none / 1 |
| Flow control | none |
| Line ending | `;` then **CR** (`\r`) — *not* CRLF, *not* LF |

### WiFi (models with `W`)

| Setting | Value |
|---|---|
| Access point password | `88889999` |
| Default IP | `192.168.181.181` |
| Default TCP port | `8181` |

The command syntax is identical over TCP. To use WiFi instead of USB, replace
the `serial.Serial(...)` object in `turntable.py` with a `socket` connected to
that IP and port — the rest of the driver is unchanged.

### Power-on behaviour

On power-up the turntable runs a 3–9 s self-test. **Three beeps means it
passed.** Wait for the beeps before sending commands.

---

## 3. CT command set

All commands are ASCII, uppercase, terminated with `;` and a carriage return.

### `CT+START(Direction, Mode, AutoShutter, Degree, PauseTime, RepeatTimes);`

The one command that does all the moving.

| Parameter | Values |
|---|---|
| `Direction` | `0` = left, `1` = right (whether that is CW or CCW depends on the model — test it) |
| `Mode` | `0` = continuous, `1` = intermittent (step-and-pause), `2` = swing (not on all models) |
| `AutoShutter` | `0` = no shutter pulse, `1` = pulse the camera trigger after each step |
| `Degree` | rotation angle per step, **whole degrees** |
| `PauseTime` | seconds to hold still after each step |
| `RepeatTimes` | how many steps to perform |

Examples:

```
CT+START(1,1,0,36,0,1);      one 36 deg step to the right, no pause
CT+START(0,1,0,45,4,8);      eight 45 deg steps left, 4 s pause each
CT+START(1,0,0,0,0,0);       continuous rotation to the right
```

For a continuous turn, `Degree`, `PauseTime` and `RepeatTimes` are ignored.

### Other documented commands

| Command | Meaning |
|---|---|
| `CT+SETMODE(mode);` | set rotation mode: `0` continuous, `1` intermittent, `2` swing |
| `CT+SETAUTOSHUTTER(onOff);` | shutter pulse after every rotation, `0`/`1` |
| `CT+CAMERACTRL(focus, capture);` | drive the camera trigger directly, `0`/`1` each |
| `CT+HEARTBEAT(onOff);` | periodic keep-alive so you can detect a dropped link |
| `CT+ACK(onOff);` | turn command replies on or off |

### Commands used by the PC software but not in the printed manual

These are the two the driver flags as unverified. They are defined at the top
of `turntable.py` as `CMD_STOP` and `CMD_SET_SPEED`:

```
CT+STOP();
CT+SETSPEED(level);      level range is model dependent, often 1..10
```

If your unit answers `CR+ERR=40;` (unsupported command) to either of them,
download the **CT command list** PDF for your exact model from ComXim's
download page and correct those two strings. Nothing else in the code refers
to them.

---

## 4. Replies and error codes

Replies only arrive when acknowledgements are enabled (`CT+ACK(1);`). They
take the form `CR+...;`.

| Code | Meaning |
|---|---|
| `CR+ERR=31;` | command timeout |
| `CR+ERR=40;` | unsupported / unknown command |

Other codes exist per model — see the CT command list PDF. Add them to the
`ERROR_CODES` dictionary in `turntable.py` so they print a readable message.

---

## 5. Things worth knowing

- **No absolute position feedback.** The turntable does not report where it
  is. Positioning is relative: you count degrees yourself. That is why
  `raman_sequence.py` tracks the total commanded angle and unwinds by exactly
  that amount to return to the start.
- **Whole degrees only.** `Degree` is an integer. `raman_sequence.py` handles
  fractional step angles by rounding against the running total rather than
  rounding each step, so the error stays below 1° over the whole run.
- **The remote's "Store" key writes settings to internal flash**, and the
  stored values are reapplied at the next power-up. If the table behaves
  oddly on startup, check whether someone stored a mode with the remote.
- **Manufacturer software**: "TurntableX" for PC, "Turntableplus" for
  Android/iOS. Useful for a quick sanity check that the hardware works before
  blaming the code. Close them before running Python — a serial port can only
  be opened by one program at a time.

---

## 6. Official downloads

- Manual (EN): <https://comxim.com/wp-content/uploads/2025/06/Intelligent-Programmable-Turntable-User-Guide-V1.5.pdf>
- USB driver: <https://comxim.com/download-usb-driver/>
- Model-specific CT command list, TurntableX, mobile apps: ComXim download page
