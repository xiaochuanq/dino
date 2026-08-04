"""Wiring check 4: blink the GP4 indicator while the IR beam is blocked.

Wire the emitter to GP5 (through 220 ohm) and the receiver to GP6 as in
docs/HARDWARE.md, then run:  mpremote run examples/04_test_ir_blink.py
Clear beam -> LED off. Put your hand in the beam -> GP4 LED blinks fast.
If it behaves inverted, flip IR_BEAM_SEEN_VALUE in config.py.

This intentionally avoids Pin("LED"). On a Pico W/2 W the onboard LED is
controlled through CYW43, so a CYW43 timeout can stop an otherwise valid IR
test and leave the failure looking like an IR problem.
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
led = Pin(config.LED_PINS[0], Pin.OUT, value=0)  # external LED + resistor

CHECK_MS = 100   # beam sample period; LED toggles once per sample -> 5 Hz blink


def beam_seen():
    """Pulse the emitter and return a noise-filtered beam sample."""
    return ir_beam.seen()


print("blocking the beam blinks the GP%d LED (Ctrl-C to stop)"
      % config.LED_PINS[0])
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
    ir_beam.stop()
