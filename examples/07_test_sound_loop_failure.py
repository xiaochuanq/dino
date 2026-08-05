"""Sound stress test: rapid play/stop commands against the DY-SV17F.

WIRING (matches config.py / docs/HARDWARE.md)
    DY-SV17F:  VCC -> VBUS (pin 40, 5 V), GND -> GND,
               RX -> GP0 (UART0 TX), TX -> GP1 (UART0 RX),
               CON3 -> GP2 (becomes BUSY; strap 4.7 k to 3.3 V),
               CON1 + CON2 -> GND direct (no resistor),
               SPK+/SPK- -> 4-8 ohm speaker
"""
import time
from machine import Pin, UART

import config
from dysv17f import DYSV17F

uart = UART(
    config.UART_ID,
    baudrate=9600,
    tx=Pin(config.UART_TX_PIN),
    rx=Pin(config.UART_RX_PIN),
)

busy = Pin(config.BUSY_PIN, Pin.IN)

# BUSY is active-low on the DY-SV17F.
player = DYSV17F(uart, busy_pin=busy, busy_active=0)

player.set_volume(config.VOLUME)
time.sleep_ms(100)

# Files 1 through 9.
for track in range(1, 10):
    print("\nSelecting stored track", track)

    # Ensure the previous track cannot block the new selection.
    player.stop()
    time.sleep_ms(100)

    player.play(track)

    # BUSY can take a while to become low.
    started = False
    deadline = time.ticks_add(time.ticks_ms(), 2000)

    while time.ticks_diff(deadline, time.ticks_ms()) > 0:
        if busy.value() == 0:
            started = True
            break
        time.sleep_ms(20)

    if not started:
        print("Track", track, "did not assert BUSY")
    else:
        print("Track", track, "started")

        # Wait for completion, with a 30-second safety timeout.
        deadline = time.ticks_add(time.ticks_ms(), 30000)

        while busy.value() == 0:
            if time.ticks_diff(deadline, time.ticks_ms()) <= 0:
                print("Playback timeout")
                player.stop()
                break
            time.sleep_ms(50)

        print("Track", track, "finished")

    time.sleep(1)

print("\nSound test complete")

"""
Thonny execution logs
MPY: soft reboot

Selecting stored track 1
Track 1 did not assert BUSY

Selecting stored track 2
Track 2 did not assert BUSY

Selecting stored track 3
Track 3 did not assert BUSY

Selecting stored track 4
Track 4 started
Playback timeout
Track 4 finished

Selecting stored track 5
Track 5 started
Playback timeout
Track 5 finished

Selecting stored track 6
Track 6 started
Playback timeout
Track 6 finished

Selecting stored track 7
Track 7 did not assert BUSY

Selecting stored track 8
Track 8 did not assert BUSY

Selecting stored track 9
Track 9 started
Playback timeout
Track 9 finished

Sound test complete
"""