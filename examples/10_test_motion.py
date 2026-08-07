"""Wiring check 10: HC-SR501 PIR motion sensor - after a one-minute
warm-up, wave your hand: the console shouts MOTION! and the EYES light
until the room has been still for ~3 s.

Run:  mpremote run examples/10_test_motion.py

This intentionally avoids Pin("LED"). On a Pico W/2 W the onboard LED is
controlled through CYW43, so a CYW43 timeout can stop an otherwise valid
PIR test and leave the failure looking like a motion-sensor problem.

WIRING (matches config.py / docs/HARDWARE.md)
    HC-SR501 VCC -> VBUS (pin 40, 5 V), OUT -> GP10, GND -> GND.
    On the module: jumper on H (repeat trigger), time-delay pot fully
    counter-clockwise (~3 s hold).
"""
import time
from machine import Pin

import config
from droid_motion import Pir

pir = Pir(pin=config.PIR_PIN, warmup_s=config.PIR_WARMUP_S)
led = Pin(config.EYES_PIN, Pin.OUT, value=0)  # eyes light while motion is seen

print("PIR warming up - the sensor needs about a minute to settle.")
seconds = config.PIR_WARMUP_S
while not pir.ready():
    print("\r  warm-up: %2d s left " % seconds, end="")
    time.sleep(1)
    seconds = max(0, seconds - 1)
print("\nREADY - wave your hand at the sensor!")

count = 0
was_moving = False
while True:
    if pir.motion_started():
        count += 1
        print("MOTION! (#%d)" % count)
    moving = pir.motion()
    if was_moving and not moving:
        print("... quiet again (LED off)")
    led.value(1 if moving else 0)
    was_moving = moving
    time.sleep(0.05)
