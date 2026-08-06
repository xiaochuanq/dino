"""Wiring check 3: play both tracks; LEDs mirror the BUSY pin.

Deploy first (./deploy.sh), then run:  mpremote run examples/03_test_sound.py
You should hear the pass voice then the beep, with LEDs lit during each.
No sound: check UART wiring, CON1/2/3 straps, and that 00001/00002 files
are on the module's flash. LEDs never light: check BUSY_PIN / BUSY_ACTIVE.

WIRING (matches config.py / docs/HARDWARE.md)
    DY-SV17F:  VCC -> VBUS (pin 40, 5 V), GND -> GND,
               RX -> GP0 (UART0 TX), TX -> GP1 (UART0 RX),
               CON3 -> GP2 (becomes BUSY; strap 4.7 k to 3.3 V),
               CON1 + CON2 -> GND direct (no resistor),
               SPK+/SPK- -> 4-8 ohm speaker
    LED:             GP4 --[series resistor]--> anode, cathode -> GND
"""
import time
from machine import Pin, UART

import config
from dysv17f import DYSV17F

uart = UART(config.UART_ID, baudrate=9600,
            tx=Pin(config.UART_TX_PIN), rx=Pin(config.UART_RX_PIN))
busy = Pin(config.BUSY_PIN, Pin.IN)
leds = [Pin(n, Pin.OUT, value=0) for n in [config.EYES_PIN]]

player = DYSV17F(uart, busy_pin=busy, busy_active=config.BUSY_ACTIVE)
player.set_volume(config.VOLUME)

for track, name in ((config.THANKS_TRACKS[0], "pass voice"),
                    (config.FULL_TRACKS[0], "beep")):
    print("playing track %d (%s)..." % (track, name))
    player.play(track)
    time.sleep_ms(300)                 # give BUSY time to assert
    while player.is_busy():
        for led in leds:
            led.value(1)
        time.sleep_ms(50)
    for led in leds:
        led.value(0)
    print("  done")
    time.sleep(1)

print("sound test complete")
