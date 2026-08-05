"""dysv17f - UART driver for the DY-SV17F voice playback module.

THE DEVICE
    The DY-SV17F is a small, cheap sound-playing board with its own 4 MB
    flash memory and a built-in 3-5 W amplifier: plug it into USB and it
    shows up as a flash drive - drop WAV/MP3 files on it - then it plays
    them all by itself when the Pico asks over UART. Because it plays
    independently, a long greeting never blocks your program.
    More info / protocol docs (covers the whole DY module family):
      https://github.com/SnijderC/dyplayer
    Search "DY-SV17F manual" for the vendor PDF.

WIRING (defaults used by the examples)
    VCC   -> 5 V (Pico VBUS pin 40); UART logic is 3.3 V TTL - safe to
             connect straight to the Pico, no level shifter needed
    GND   -> GND
    RX    -> Pico GP0 (UART0 TX)      TX -> Pico GP1 (UART0 RX)
    BUSY  -> Pico GP2 (any free GPIO; lets wait_done() work). No pin is
             labeled BUSY: the CON3 strap pin BECOMES the busy output
             after boot - GP2 goes on CON3 (see mode select below).
    SPK+/SPK- -> a 4-8 ohm speaker (this module has its own amp)
    Mode select for UART control (CON1=0, CON2=0, CON3=1 - sampled only
    in the first ~30 ms after MODULE power-on):
      CON1 -> GND direct,  CON2 -> GND direct,
      CON3 -> 3.3 V through 4.7 kohm (two 10 k in parallel = 5 k is
      fine). Not a direct tie - CON3 must stay free to be driven as
      BUSY after boot; not 10 k or more - the divider against the
      chip's internal pull can land under the 2.7 V "high" threshold.
    After changing straps, unplug the module's power completely - a
    soft reboot does not re-strap it.

ELECTRICAL NOTES
    - No series resistors on CON1/CON2: against the chip's internal
      pull-up they form a divider in the undefined logic band and the
      mode bits misread at power-on.
    - Missed-strap signature: the module boots into IO-trigger mode,
      where RX/IO1 (the pin wired to Pico TX) is the hardware "play
      track 2" button - ANY serial traffic then plays track 2, whatever
      track number the code asked for. Only ever hearing the 2nd file
      means the straps, not the files, are wrong.
    - The UART lines themselves need no pull-ups (idle high) and the
      BUSY output is push-pull.
    - The amp draws current spikes at high volume: if the sound crackles
      or the Pico browns out, add a 220-470 uF electrolytic capacitor
      across the module's VCC/GND, close to the module.

PROTOCOL
    9600 baud. Frames: AA <cmd> <len> <data...> <checksum(low byte of sum)>.
    Audio files live on the module's own flash (copy over its USB port)
    named 00001.wav / 00001.mp3, 00002..., addressed here by track number.
"""
try:
    from time import sleep_ms, ticks_ms, ticks_diff
except ImportError:  # desktop CPython for tests
    import time

    def sleep_ms(ms):
        time.sleep(ms / 1000)

    def ticks_ms():
        return int(time.monotonic() * 1000)

    def ticks_diff(a, b):
        return a - b


class DYSV17F:
    def __init__(self, uart, busy_pin=None, busy_active=1):
        self._uart = uart
        self._busy = busy_pin
        self._busy_active = busy_active

    @staticmethod
    def _frame(cmd, data=b""):
        body = bytes([0xAA, cmd, len(data)]) + data
        return body + bytes([sum(body) & 0xFF])

    def play(self, track):
        """Select track (1-based) and start playing. Returns immediately."""
        self._uart.write(self._frame(0x07, bytes([(track >> 8) & 0xFF,
                                                  track & 0xFF])))

    def stop(self):
        self._uart.write(self._frame(0x04))

    def set_volume(self, vol):
        vol = max(0, min(30, int(vol)))
        self._uart.write(self._frame(0x13, bytes([vol])))

    def is_busy(self):
        if self._busy is None:
            return False
        return self._busy.value() == self._busy_active

    def wait_done(self, timeout_ms=20000, feed=None):
        """Block until playback finishes (or timeout). Feeds WDT if given."""
        sleep_ms(200)  # give the module time to assert BUSY after play()
        start = ticks_ms()
        while self.is_busy():
            if feed:
                feed()
            if ticks_diff(ticks_ms(), start) > timeout_ms:
                return
            sleep_ms(50)

