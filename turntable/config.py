"""
config.py — every setting you normally need to change lives here.

Edit this file, then run the scripts.  Nothing else should need editing.
"""

from turntable import DIR_LEFT, DIR_RIGHT  # noqa: F401  (re-exported for convenience)

# ---------------------------------------------------------------------------
# 1. Connection
# ---------------------------------------------------------------------------

# Windows: "COM3", "COM5", ...   (Device Manager -> Ports (COM & LPT))
# macOS:   "/dev/tty.usbserial-1420"
# Linux:   "/dev/ttyUSB0"
PORT = "COM3"

BAUDRATE = 115200  # fixed by the manufacturer — do not change

# Set True to rehearse a run with no hardware attached: commands are printed,
# waits still happen.  Use SPEEDUP below to make a dry run finish fast.
DRY_RUN = False

# ---------------------------------------------------------------------------
# 2. Mechanical calibration
# ---------------------------------------------------------------------------

# Measured rotation speed in degrees per second.
# See README section "Calibrating deg_per_sec".  Err on the LOW side: too low
# only means the script waits a bit longer than the move actually takes.
DEG_PER_SEC = 12.0

# Extra seconds added to every move for acceleration and settling.
MOVE_OVERHEAD_S = 1.5

# Which direction code moves the sample the way you want to index samples?
# The manual defines 0 = left, 1 = right, but whether that is clockwise or
# counter-clockwise depends on the model.  Test it once (see README Step 5)
# and set it here.
FORWARD_DIRECTION = DIR_RIGHT
REVERSE_DIRECTION = DIR_LEFT

# ---------------------------------------------------------------------------
# 3. Raman measurement sequence
# ---------------------------------------------------------------------------

# Total angle swept over the whole run, in degrees (e.g. 360 for a full circle).
TOTAL_ANGLE = 360.0

# How many samples sit on the turntable, i.e. how many measurement positions.
N_SAMPLES = 10

# How the positions are spread over TOTAL_ANGLE:
#   "wrap"      — the last position is one step short of TOTAL_ANGLE.
#                 step = TOTAL_ANGLE / N_SAMPLES.
#                 Correct for a full circle: 360 deg, 10 samples -> 36 deg steps
#                 at 0, 36, ..., 324.
#   "inclusive" — the first and last positions sit exactly on 0 and TOTAL_ANGLE.
#                 step = TOTAL_ANGLE / (N_SAMPLES - 1).
#                 Correct for an arc: 180 deg, 5 samples -> 45 deg steps
#                 at 0, 45, 90, 135, 180.
SPACING = "wrap"

# Minutes to dwell at each position (this is your Raman acquisition window).
MINUTES_PER_SAMPLE = 5.0

# Minutes to wait after the last position before returning to the start.
MINUTES_BEFORE_RETURN = 5.0

# How many complete cycles to run.  Use None for "repeat forever until Ctrl+C".
N_CYCLES = 1

# Pulse the camera/shutter output when arriving at each position.
# Leave False unless the trigger cable is wired to your Raman system.
TRIGGER_SHUTTER = False

# ---------------------------------------------------------------------------
# 4. Logging
# ---------------------------------------------------------------------------

# CSV file recording the time and angle of every position, so the Raman
# spectra can be matched to sample positions afterwards.  None disables it.
LOG_FILE = "turntable_run_log.csv"

# ---------------------------------------------------------------------------
# 5. Debug
# ---------------------------------------------------------------------------

# Divide every wait by this number.  Keep at 1.0 for real experiments;
# set to e.g. 600 together with DRY_RUN = True to test the logic in seconds.
SPEEDUP = 1.0
