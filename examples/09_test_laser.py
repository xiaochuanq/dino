"""Wiring check 9: VL53L1X laser distance sensor - distance streamed.

Deploy first (./deploy.sh), then run:  mpremote run examples/09_test_laser.py
Move your hand toward and away from the sensor: the millimetre value
must follow it. "no target" means the chip saw nothing real in range
(normal when pointing at open space). An OSError at start means the
sensor is not answering on I2C: check the SDA/SCL wiring (pins are
printed at start, from config.py), 3V3 power, and GND.

WIRING (matches config.py / docs/HARDWARE.md)
    VL53L1X                      Pico
      VIN  ------------------->  3V3 (pin 36)
      GND  ------------------->  GND
      SDA  ------------------->  GP16 (I2C0 SDA)
      SCL  ------------------->  GP17 (I2C0 SCL)
    Pololu/Adafruit/GY-53 breakouts have I2C pull-ups on board - add
    nothing. Bare module or bus over ~20 cm: 4.7-10 k from SDA and SCL
    to 3V3.
"""
import time
from machine import I2C, Pin

import config
from droid_sense import read_mm, set_mode
from vl53l1x import VL53L1X

laser = VL53L1X(I2C(config.I2C_ID, sda=Pin(config.I2C_SDA_PIN),
                    scl=Pin(config.I2C_SCL_PIN)))
set_mode(laser, config.LASER_MODE)

print("VL53L1X on I2C%d (SDA=GP%d, SCL=GP%d), mode=%s"
      % (config.I2C_ID, config.I2C_SDA_PIN, config.I2C_SCL_PIN,
         config.LASER_MODE))
while True:
    mm = read_mm(laser)
    if mm is None:
        print("distance: no target")
    else:
        print("distance: %4d mm" % mm)
    time.sleep_ms(200)
