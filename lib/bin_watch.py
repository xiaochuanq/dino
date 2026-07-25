"""bin_watch - pure timing/state logic for the Dino bin robot.

No hardware imports: every method takes the current time in ms, so this
logic runs (and is tested) on desktop CPython with plain integers, and on
the Pico with time.ticks_ms() values (wraparound-safe via ticks_diff).
"""
try:
    from time import ticks_diff, ticks_add
except ImportError:  # desktop CPython for tests

    def ticks_diff(a, b):
        return a - b

    def ticks_add(a, b):
        return a + b


class DoorWatch:
    """Debounce a tilt switch and report open->shut transitions."""

    def __init__(self, open_value, debounce_ms, initial_raw, now_ms):
        self._open_value = open_value
        self._debounce = debounce_ms
        self._stable = initial_raw
        self._candidate = initial_raw
        self._since = now_ms

    def closed_event(self, raw, now_ms):
        """Feed one raw pin sample. True once per debounced open->shut."""
        if raw != self._candidate:
            self._candidate = raw
            self._since = now_ms
            return False
        if raw == self._stable:
            return False
        if ticks_diff(now_ms, self._since) < self._debounce:
            return False
        was_open = self._stable == self._open_value
        self._stable = raw
        return was_open and raw != self._open_value
