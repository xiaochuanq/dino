"""Wiring check 6: sound diagnostic - what does the DY-SV17F actually see?

Run:  mpremote run examples/06_test_sound_diag.py

Answers three questions the normal sound test can't:
  1. How many files does the module think it has?  The DY family indexes
     tracks by the ORDER files were copied onto flash - NOT by filename.
     Renaming changes nothing; deleting and re-copying shuffles the order.
  2. Which track numbers actually start playback?  BUSY asserting means
     the module accepted that number and is decoding something.
  3. Does a track assert BUSY but stay silent?  That points at a file the
     chip can't decode - re-export it as 16-bit 44.1 kHz WAV or plain
     constant-bitrate MP3.

Write down which SOUND you hear at each track number: that mapping is the
module's real index order, whatever the files are named.

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

CMD_GAP_MS = 200          # generous pause between UART commands
TRACKS_TO_TRY = 5
LISTEN_S = 6              # max seconds to watch each track play

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


time.sleep_ms(500)                            # let the module finish booting
player.set_volume(config.VOLUME)
time.sleep_ms(CMD_GAP_MS)

count = query(0x0C, 2)                        # 0x0C = query number of files
if count is None:
    print("file count query: NO REPLY")
    print("  -> module TX -> Pico GP%d wiring problem, wrong CON1/2/3"
          % config.UART_RX_PIN)
    print("     straps (UART mode needs CON1=0 CON2=0 CON3=1), or no power")
else:
    n = (count[0] << 8) | count[1]
    print("module reports %d file(s) on its flash" % n)
    print("  (more than you copied? -> leftover/hidden files are eating")
    print("   the low track numbers)")

for track in range(1, TRACKS_TO_TRY + 1):
    time.sleep_ms(CMD_GAP_MS)
    print("track %d: play sent -> " % track, end="")
    player.play(track)
    t0 = time.ticks_ms()
    t_assert = None
    while time.ticks_diff(time.ticks_ms(), t0) < LISTEN_S * 1000:
        if busy.value() == config.BUSY_ACTIVE:
            if t_assert is None:
                t_assert = time.ticks_ms()
        elif t_assert is not None:
            break                             # finished playing
        time.sleep_ms(20)
    if t_assert is not None:
        dur = time.ticks_diff(time.ticks_ms(), t_assert)
        print("BUSY asserted, played ~%d ms  <- note WHICH sound this was"
              % dur)
    else:
        print("no BUSY - no track %d on flash (or command ignored)" % track)
    player.stop()

print("""
How to read this:
 - file count > files you copied   -> junk entries. Plug the module into
   USB, delete EVERYTHING (enable 'show hidden files'!), then copy your
   files back ONE AT A TIME in playback order. Renaming does NOT reorder.
 - BUSY asserts but stays silent   -> that file's format is bad:
   re-export as 16-bit 44.1 kHz WAV or constant-bitrate MP3.
 - sound on a DIFFERENT number than the filename suggests -> index order
   is copy order; fix by re-copying in order (above), not by renaming.
 - no BUSY on any track but the file count query works -> BUSY pin wiring.
""")
