"""eyes - Dino's two LED eyes (wired in parallel on one pin).

A steady glow while quiet, a lively blink while talking. No memory:
each update() computes the eye state straight from the clock.
"""


class Eyes:
    def __init__(self, pin, blink_ms):
        self._pin = pin
        self._blink = blink_ms

    def update(self, now_ms, talking):
        if talking:
            self._pin.value(1 if (now_ms // self._blink) % 2 == 0 else 0)
        else:
            self._pin.value(1)
