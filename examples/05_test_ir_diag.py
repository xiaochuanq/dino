"""Wiring check 5: IR diagnostic - emitter held ON, raw receiver value streamed.

Run:  mpremote run examples/05_test_ir_diag.py
The emitter stays lit the whole time (check it with a phone camera - it
shows as a purple glow). The line printed is the RAW pin value, before
any config polarity is applied:
    raw=0  -> receiver conducting (light reaching it)
    raw=1  -> receiver dark (pulled up, no light)
Point emitter and receiver face-to-face a few cm apart and cover/uncover
the receiver: the value must flip. If it never leaves 1, work through
the checklist in the README/chat.

WIRING (matches config.py / docs/HARDWARE.md)
    IR emitter LED:  GP5 --[220 ohm]--> anode, cathode -> GND
    IR receiver:     collector -> GP6 (internal pull-up), emitter -> GND
    (comparator break-beam module instead: VCC -> 3V3, GND -> GND,
     OUT -> GP6)
"""
import time
from machine import Pin

import config

ir_emit = Pin(config.IR_EMIT_PIN, Pin.OUT, value=1)   # ON continuously
ir_recv = Pin(config.IR_RECV_PIN, Pin.IN)

print("emitter GP%d held ON, reading receiver GP%d raw value"
      % (config.IR_EMIT_PIN, config.IR_RECV_PIN))
print("(config expects %d = beam seen)" % config.IR_BEAM_SEEN_VALUE)
last = None
try:
    while True:
        raw = ir_recv.value()
        if raw != last:
            print("raw =", raw,
                  "-> SEEN" if raw == config.IR_BEAM_SEEN_VALUE
                  else "-> BLOCKED/dark")
            last = raw
        time.sleep_ms(50)
finally:
    ir_emit.value(0)
