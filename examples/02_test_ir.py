"""Wiring check 2: pulse the IR emitter and print the beam state every second.

Deploy first (./deploy.sh), then run:  mpremote run examples/02_test_ir.py
With a clear bin you should see 'beam SEEN'; put your hand in the beam and
it should flip to 'beam BLOCKED'. If it reads inverted, flip
IR_BEAM_SEEN_VALUE in config.py.
"""
import time
from machine import Pin

import config
from ir_beam import IRBeam

ir_emit = Pin(config.IR_EMIT_PIN, Pin.OUT, value=0)
ir_recv = Pin(config.IR_RECV_PIN, Pin.IN, pull=Pin.PULL_UP)
ir_beam = IRBeam(ir_emit, ir_recv, config.IR_BEAM_SEEN_VALUE,
                 config.IR_SETTLE_MS, config.IR_SAMPLE_COUNT,
                 config.IR_SAMPLE_GAP_US)

print("beam check once per second (Ctrl-C to stop)")
while True:
    seen = ir_beam.seen()
    print("beam SEEN" if seen else "beam BLOCKED")
    time.sleep(1)
