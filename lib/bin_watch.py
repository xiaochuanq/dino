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


class BinWatch:
    """Track bin fullness from IR beam checks; schedule alert bursts."""

    def __init__(self, full_after_ms, alert_repeat_ms, now_ms):
        self._full_after = full_after_ms
        self._repeat = alert_repeat_ms
        self._last_seen = now_ms
        self._full = False
        self._next_burst = None

    def beam_result(self, seen, now_ms):
        """Feed the result of one IR check."""
        if seen:
            self._last_seen = now_ms
            self._full = False
            self._next_burst = None
        elif (not self._full and
              ticks_diff(now_ms, self._last_seen) >= self._full_after):
            self._full = True
            self._next_burst = now_ms  # first burst is due right away

    def is_full(self):
        return self._full

    def burst_due(self, now_ms):
        """True at most once per repeat interval while full."""
        if not self._full or self._next_burst is None:
            return False
        if ticks_diff(now_ms, self._next_burst) >= 0:
            self._next_burst = ticks_add(now_ms, self._repeat)
            return True
        return False


class FlashBurst:
    """One alert burst: count flashes of flash_ms on / flash_ms off.

    Driven by the main loop calling led_on(now) every tick - never blocks.
    """

    def __init__(self, count, flash_ms):
        self._count = count
        self._flash_ms = flash_ms
        self._start = None

    def start(self, now_ms):
        self._start = now_ms

    def cancel(self):
        self._start = None

    def active(self):
        return self._start is not None

    def led_on(self, now_ms):
        """Desired LED state now; self-deactivates when the burst is done."""
        if self._start is None:
            return False
        phase = ticks_diff(now_ms, self._start) // self._flash_ms
        if phase >= self._count * 2:
            self._start = None
            return False
        return phase % 2 == 0
