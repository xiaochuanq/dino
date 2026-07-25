"""Wiring check 1: print every tilt change and each debounced door-close.

Deploy first (./deploy.sh), then run:  mpremote run examples/01_test_tilt.py
Open and release the door: you should see raw OPEN/SHUT lines and exactly
one '>>> door closed' per swing. If OPEN/SHUT look inverted, flip
DOOR_OPEN_VALUE in config.py.
"""
import time
from machine import Pin

import config
from bin_watch import DoorWatch

tilt = Pin(config.TILT_PIN, Pin.IN, Pin.PULL_UP)
now = time.ticks_ms()
door = DoorWatch(config.DOOR_OPEN_VALUE, config.DOOR_DEBOUNCE_MS,
                 tilt.value(), now)
last_raw = tilt.value()

print("watching tilt switch on GP%d (Ctrl-C to stop)" % config.TILT_PIN)
while True:
    now = time.ticks_ms()
    raw = tilt.value()
    if raw != last_raw:
        print("raw:", "OPEN" if raw == config.DOOR_OPEN_VALUE else "SHUT")
        last_raw = raw
    if door.closed_event(raw, now):
        print(">>> door closed - the voice would play now")
    time.sleep_ms(10)
