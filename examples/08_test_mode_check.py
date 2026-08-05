"""Wiring check 8: is the DY-SV17F actually in UART mode?

Run:  mpremote run examples/08_test_mode_check.py   (or via Thonny)

Background: on the DY-SV17F the CON3 strap and the BUSY output are the
SAME physical pin. It is read as a mode strap only in the first ~30 ms
after MODULE power-on (needs to be high, via ~4.7 k to 3.3 V, with
CON1=CON2=0, for UART mode) and only then becomes BUSY. The TX/RX pins
are dual-use too: in IO-trigger mode, RX/IO1 - the pin the Pico's TX is
wired to - is the hardware "play track 2" button. A module that missed
the strap at power-on therefore plays track 2 in response to ANY serial
traffic, whatever track the code asked for.

Three phases:
  A. Query the file count over UART. A reply proves UART mode + wiring.
  B. Send a burst of 0x00 bytes. UART mode ignores them completely
     (never a valid frame); IO-trigger mode hears a button press on IO1.
     LISTEN: sound during this phase = module is in IO-trigger mode.
  C. If A replied: play the beep track and measure which level BUSY has
     while sound is audible, so BUSY_ACTIVE can be set from evidence.

Straps are sampled at POWER-ON only: after changing them, unplug the
module's power completely - a soft reboot is not enough.
"""
import time
from machine import Pin, UART

import config
from dysv17f import DYSV17F

uart = UART(config.UART_ID, baudrate=9600,
            tx=Pin(config.UART_TX_PIN), rx=Pin(config.UART_RX_PIN))
busy = Pin(config.BUSY_PIN, Pin.IN)
player = DYSV17F(uart, busy_pin=busy, busy_active=config.BUSY_ACTIVE)


def query(cmd, reply_len, tries=3):
    """Send a query frame, return the reply's data bytes (or None)."""
    for _ in range(tries):
        while uart.any():                     # drain stale bytes
            uart.read()
        uart.write(DYSV17F._frame(cmd))
        deadline = time.ticks_add(time.ticks_ms(), 1000)
        buf = b""
        while time.ticks_diff(deadline, time.ticks_ms()) > 0:
            if uart.any():
                buf += uart.read()
                i = buf.find(b"\xaa")         # frame: AA cmd len data crc
                if i >= 0 and len(buf) >= i + 3 + reply_len + 1:
                    frame = buf[i:i + 3 + reply_len + 1]
                    if sum(frame[:-1]) & 0xFF == frame[-1]:
                        return frame[3:-1]
            time.sleep_ms(10)
    return None


print("=== A: UART query (0x0C = file count) ===")
time.sleep_ms(500)
count = query(0x0C, 2)
if count is None:
    print("NO REPLY -> module is NOT talking UART.")
    print("Either it booted into the wrong mode (strap problem) or its")
    print("TX -> Pico GP%d wire is broken." % config.UART_RX_PIN)
else:
    n = (count[0] << 8) | count[1]
    print("REPLY: module sees %d file(s). UART mode CONFIRMED." % n)

print()
print("=== B: IO-trigger probe - LISTEN for sound now ===")
print("Sending 3 bursts of 0x00 bytes (invalid as UART frames, look like")
print("button presses on RX/IO1 if the module is in IO-trigger mode)...")
for i in range(3):
    uart.write(b"\x00" * 200)                 # ~200 ms mostly-low burst
    time.sleep(2)
    print("  burst %d sent" % (i + 1))
print("Heard the same old sound just now?  -> module is in IO-TRIGGER")
print("mode: fix the straps (CON1, CON2 -> GND; CON3 -> 3.3 V via 4.7k)")
print("and UNPLUG MODULE POWER before retrying. Silence here is correct.")

if count is not None:
    print()
    print("=== C: BUSY polarity (playing beep, track %d) ==="
          % config.TRACK_BEEP)
    idle = busy.value()
    print("BUSY at idle: %d" % idle)
    player.play(config.TRACK_BEEP)
    time.sleep_ms(500)                        # let playback start
    playing = busy.value()
    print("BUSY while playing: %d" % playing)
    time.sleep(3)
    player.stop()
    if playing != idle:
        print("-> set BUSY_ACTIVE = %d in config.py" % playing)
    else:
        print("-> BUSY did not change; pin not strapped/wired as expected")
        print("   (or the track made no sound - was it audible?)")

print("\nmode check complete")
