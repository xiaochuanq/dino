"""Dino smart bin robot - every tuning knob lives here.

Change a number, save, redeploy (./deploy.sh) - that's how you tune the robot.
"""

# --- Behavior tuning -------------------------------------------------
FULL_AFTER_S = 60          # beam blocked this many seconds -> bin is FULL
IR_PASS_MAX_MS = 2000      # block shorter than this that clears = a drop-through
ALERT_REPEAT_S = 10        # ("m") seconds between alert bursts while FULL
FLASH_COUNT = 3            # ("k") LED flashes per alert burst
FLASH_MS = 200             # ("j") each flash: on this many ms, off the same

# --- Sound ------------------------------------------------------------
VOLUME = 25                # 0-30
TRACK_PASS_VOICE = 1       # 00001.wav on the DY-SV17F flash
TRACK_BEEP = 2             # 00002.wav on the DY-SV17F flash
TRACK_MOTION_VOICE = 1     # played by on_motion_detected() (sound 1)

# --- Person detection (VL53L1X laser distance sensor) -------------------
GREET_NEAR_MM = 1000       # someone closer than this -> greet (play sound 1)
GREET_CLOSE_MM = 500       # inner "right at the bin" zone (must be < GREET_NEAR_MM)
LASER_MODE = "medium"      # "short" ~1.3 m / "medium" ~2.9 m / "long" ~3.6 m

# --- Pins (GP numbers on the Pico) -------------------------------------
UART_ID = 0
UART_TX_PIN = 0            # Pico GP0 (UART0 TX) -> DY-SV17F RX
UART_RX_PIN = 1            # Pico GP1 (UART0 RX) -> DY-SV17F TX
BUSY_PIN = 2               # DY-SV17F BUSY output (CON3 pin)
LED_PINS = [4]             # one or more LED pins, all switched together
IR_EMIT_PIN = 5            # IR emitter LED (through 220 ohm)
IR_RECV_PIN = 6            # IR receiver output
EYES_PIN = 7               # both eye LEDs, driven together by this one GPIO
                           # (GP8-GP9 reserved for future LEDs with GP4/GP5)
I2C_ID = 0                 # I2C bus for the VL53L1X laser distance sensor
I2C_SDA_PIN = 16           # VL53L1X SDA
I2C_SCL_PIN = 17           # VL53L1X SCL

# --- Wiring polarity / fine timing --------------------------------------
IR_BEAM_SEEN_VALUE = 0     # receiver pin reads this when the beam is SEEN
BUSY_ACTIVE = 0            # BUSY pin value while a sound is playing
IR_SETTLE_MS = 1           # emitter-on settle time before reading receiver
IR_SAMPLE_COUNT = 5        # majority vote over this many receiver reads (odd)
IR_SAMPLE_GAP_US = 200     # gap between the receiver reads
BUSY_ASSERT_MS = 300       # after play(), BUSY can't be trusted this long
LED_FALLBACK_ON_MS = 3000  # LED on-time if BUSY never asserts (module missing)
TICK_MS = 50               # main loop tick
