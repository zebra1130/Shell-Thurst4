"""
examples/basic_moves.py — the smallest working examples of every basic action.

Run from the project folder:
    python examples/basic_moves.py

Read it top to bottom; each block is independent.  Comment out what you do not
want to run.
"""

import sys
import os
import time

# Allow "python examples/basic_moves.py" from the project folder.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from turntable import Turntable, DIR_LEFT, DIR_RIGHT


with Turntable(port=config.PORT, dry_run=config.DRY_RUN) as tt:

    # -- 1. Rotate by N degrees and wait until the move is finished ----------
    tt.rotate(36)                       # 36 deg, default direction (right)
    tt.rotate(90, direction=DIR_LEFT)   # 90 deg the other way

    # -- 2. Rotate in several equal steps with a pause between them ---------
    # 10 steps of 36 deg, pausing 3 s at each stop.  This one is run by the
    # turntable's own firmware, so Python just waits for it to finish.
    tt.rotate(36, direction=DIR_RIGHT, pause_s=3, repeat=10)

    # -- 3. Continuous rotation, then stop ----------------------------------
    tt.spin(direction=DIR_RIGHT)
    time.sleep(10)                      # let it turn for 10 seconds
    tt.stop()

    # -- 4. Speed ----------------------------------------------------------
    # Range is model dependent (often 1-10).  Check your model's CT list.
    tt.set_speed(5)

    # -- 5. Camera / shutter trigger output ---------------------------------
    tt.camera(focus=True, capture=False)   # half-press: focus
    time.sleep(0.5)
    tt.camera(focus=False, capture=True)   # full press: shoot
    tt.set_auto_shutter(True)              # or: pulse automatically after
    tt.rotate(36, shutter=True)            #      every rotation step
    tt.set_auto_shutter(False)

    # -- 6. Acknowledgements and heartbeat ----------------------------------
    tt.set_ack(True)        # turntable replies to every command
    tt.set_heartbeat(True)  # keeps the link alive / lets you detect a drop

    # -- 7. Any raw command from the manual ---------------------------------
    # Signature: CT+START(Direction, Mode, AutoShutter, Degree, Pause, Repeat)
    tt.send("CT+START(1,1,0,45,2,4);")
    time.sleep(tt.motion_time(45, pause_s=2, repeat=4))

    # -- 8. Emergency stop ---------------------------------------------------
    tt.stop()

print("Done.")
