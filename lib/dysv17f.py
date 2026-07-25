"""dysv17f - UART driver for the DY-SV17F voice playback module.

Wire the module for UART control (CON1=0, CON2=0, CON3=1 on most boards),
9600 baud. Frames: AA <cmd> <len> <data...> <checksum(low byte of sum)>.
Audio files live on the module's own flash (copy over its USB port) named
00001.wav / 00001.mp3, 00002..., addressed here by track number.
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
