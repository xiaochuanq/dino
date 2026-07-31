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


class BinWatch:
    """Classify IR beam samples: short blocks are drop-throughs ("passes"),
    a long continuous block means the bin is full; schedule alert bursts."""

    def __init__(self, full_after_ms, alert_repeat_ms, pass_max_ms, now_ms):
        self._full_after = full_after_ms
        self._repeat = alert_repeat_ms
        self._pass_max = pass_max_ms
        self._last_seen = now_ms
        self._blocked_since = None
        self._full = False
        self._next_burst = None

    def beam_result(self, seen, now_ms):
        """Feed one beam sample. Returns True once when a block shorter
        than pass_max_ms clears - something passed through the beam."""
        passed = False
        if seen:
            if (self._blocked_since is not None and not self._full and
                    ticks_diff(now_ms, self._blocked_since) < self._pass_max):
                passed = True
            self._blocked_since = None
            self._last_seen = now_ms
            self._full = False
            self._next_burst = None
        else:
            if self._blocked_since is None:
                self._blocked_since = now_ms
            if (not self._full and
                    ticks_diff(now_ms, self._last_seen) >= self._full_after):
                self._full = True
                self._next_burst = now_ms  # first burst is due right away
        return passed

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
