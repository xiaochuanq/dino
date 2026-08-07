"""Dino smart bin robot - every tuning knob lives here.

Change a number, save, redeploy (./deploy.sh) - that's how you tune the robot.
"""

# --- Sounds: track numbers = file names on the DY-SV17F flash -----------
# 00003.wav on the module is track 3. Add a file, add its number to a list,
# and Dino picks one of the list at random every time.
PASSING_TRACKS = [3]       # funny noise when someone walks by (1-3 m)
GREETING_TRACKS = [1]      # "hello!" when someone comes close
GOODBYE_TRACKS = [4]       # "bye!" when they walk away
THANKS_TRACKS = [5]        # "thank you!" when they push the lid
FULL_TRACKS = [2]          # complaints while the bin is stuffed full
VOLUME = 30                # 0-30

# --- Distances (millimetres) ---------------------------------------------
HERE_MM = 1000             # closer than this -> visitor "is here": greet
LEAVE_MM = 1500            # farther than this -> visitor left: goodbye
                           # (the 500 mm gap stops greet/goodbye ping-pong)
PASSING_MM = 3000          # between LEAVE_MM and this -> just passing by
LASER_MODE = "medium"      # "short" ~1.3 m / "medium" ~2.9 m / "long" ~3.6 m
                           # (medium tops out ~2.9 m, so the passing band
                           # really ends at sensor range)

# --- Behavior timing ------------------------------------------------------
PASSING_COOLDOWN_S = 30    # quiet time between two passing noises
MOTION_HOLD_S = 15         # believe the laser this long after the last movement
PIR_WARMUP_S = 60          # PIR settle time after power-on (physics, not a bug)
LID_PUSH_MAX_MS = 2000     # lid open shorter than this, then shut = a push
FULL_AFTER_S = 60          # lid open this many seconds -> bin is FULL
COMPLAIN_EVERY_S = 10      # seconds between complaints while FULL
TALK_BLINK_MS = 250        # eye blink speed while Dino is talking

# --- Pins (GP numbers on the Pico) ----------------------------------------
UART_ID = 0
UART_TX_PIN = 0            # GP0 (UART0 TX) -> DY-SV17F RX
UART_RX_PIN = 1            # GP1 (UART0 RX) -> DY-SV17F TX
BUSY_PIN = 2               # DY-SV17F BUSY output (CON3 pin)
EYES_PIN = 4               # both eye LEDs (in parallel), one GPIO
IR_EMIT_PIN = 5            # IR emitter LED (through 220 ohm)
IR_RECV_PINS = [6, 7, 8]   # IR receiver outputs
PIR_PIN = 10               # HC-SR501 PIR OUT (motion sensor)
I2C_ID = 1                 # GP14/15 belong to I2C1 on the Pico
I2C_SDA_PIN = 14           # VL53L1X SDA
I2C_SCL_PIN = 15           # VL53L1X SCL

# --- Wiring polarity / fine timing -----------------------------------------
IR_BEAM_SEEN_VALUE = 0     # receiver pin reads this when the beam is SEEN
BUSY_ACTIVE = 1            # BUSY pin value while a sound is playing
IR_SETTLE_MS = 1           # emitter-on settle time before reading receiver
IR_SAMPLE_COUNT = 5        # majority vote over this many receiver reads (odd)
IR_SAMPLE_GAP_US = 200     # gap between the receiver reads
BUSY_ASSERT_MS = 300       # after play(), BUSY can't be trusted this long
TALK_FALLBACK_MS = 3000    # assumed talk time if BUSY never asserts
TICK_MS = 50               # main loop tick
