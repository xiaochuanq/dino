"""Wiring check 4: blink the Pico's onboard LED while the IR beam is blocked.

Wire the emitter to GP5 (through 220 ohm) and the receiver to GP6 as in
docs/HARDWARE.md, then run:  mpremote run examples/04_test_ir_blink.py
Clear beam -> LED off. Put your hand in the beam -> LED blinks fast.
If it behaves inverted, flip IR_BEAM_SEEN_VALUE in config.py.
"""
import time
from machine import Pin

import config

ir_emit = Pin(config.IR_EMIT_PIN, Pin.OUT, value=0)
ir_recv = Pin(config.IR_RECV_PIN, Pin.IN)
led = Pin("LED", Pin.OUT, value=0)  # onboard LED (Pico 2 and 2 W)

CHECK_MS = 100   # beam sample period; LED toggles once per sample -> 5 Hz blink


def beam_seen():
    """Pulse the emitter and read the receiver once."""
    ir_emit.value(1)
    time.sleep_ms(config.IR_SETTLE_MS)
    seen = ir_recv.value() == config.IR_BEAM_SEEN_VALUE
    ir_emit.value(0)
    return seen


print("blocking the beam blinks the onboard LED (Ctrl-C to stop)")
was_seen = None
try:
    while True:
        seen = beam_seen()
        if seen != was_seen:
            print("beam SEEN" if seen else "beam BLOCKED")
            was_seen = seen
        if seen:
            led.value(0)
        else:
            led.toggle()
        time.sleep_ms(CHECK_MS)
finally:
    led.value(0)
    ir_emit.value(0)
