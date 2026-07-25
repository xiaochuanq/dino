"""Wiring check 2: pulse the IR emitter and print the beam state every second.

Deploy first (./deploy.sh), then run:  mpremote run examples/02_test_ir.py
With a clear bin you should see 'beam SEEN'; put your hand in the beam and
it should flip to 'beam BLOCKED'. If it reads inverted, flip
IR_BEAM_SEEN_VALUE in config.py.
"""
import time
from machine import Pin

import config

ir_emit = Pin(config.IR_EMIT_PIN, Pin.OUT, value=0)
ir_recv = Pin(config.IR_RECV_PIN, Pin.IN)

print("beam check once per second (Ctrl-C to stop)")
while True:
    ir_emit.value(1)
    time.sleep_ms(config.IR_SETTLE_MS)
    seen = ir_recv.value() == config.IR_BEAM_SEEN_VALUE
    ir_emit.value(0)
    print("beam SEEN" if seen else "beam BLOCKED")
    time.sleep(1)
