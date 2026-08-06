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
