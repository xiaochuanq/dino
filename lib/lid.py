"""lid - Dino's flappy lid, watched by an invisible IR light beam.

The beam shines across the lid opening: lid pushed open = beam blocked,
lid closed = beam seen. LidLogic is pure logic (desktop-testable, fed
times in ms); Lid adds the real beam doing the looking.

States and news after every update():
    is_open      the lid is pushed open right now
    just_pushed  (one tick) it was open briefly and closed - a donation!
    is_full      the lid has been stuck open so long the bin must be full
    complain_due(now)  True once per complain interval while full
"""
try:
    from time import ticks_diff, ticks_add
except ImportError:  # desktop CPython for tests

    def ticks_diff(a, b):
        return a - b

    def ticks_add(a, b):
        return a + b


class LidLogic:
    def __init__(self, push_max_ms, full_after_ms, complain_every_ms, now_ms):
        self._push_max = push_max_ms
        self._full_after = full_after_ms
        self._every = complain_every_ms
        self._last_closed = now_ms
        self._opened_at = None
        self._full = False
        self._next_complaint = None
        self.just_pushed = False

    @property
    def is_open(self):
        return self._opened_at is not None

    @property
    def is_full(self):
        return self._full

    def update(self, beam_seen, now_ms):
        """Feed one beam sample (beam seen = lid closed)."""
        self.just_pushed = False
        if beam_seen:
            if (self._opened_at is not None and not self._full and
                    ticks_diff(now_ms, self._opened_at) < self._push_max):
                self.just_pushed = True
            self._opened_at = None
            self._last_closed = now_ms
            self._full = False
            self._next_complaint = None
        else:
            if self._opened_at is None:
                self._opened_at = now_ms
            if (not self._full and
                    ticks_diff(now_ms, self._last_closed) >= self._full_after):
                self._full = True
                self._next_complaint = now_ms  # first complaint right away

    def complain_due(self, now_ms):
        """True at most once per complain interval while full."""
        if not self._full or self._next_complaint is None:
            return False
        if ticks_diff(now_ms, self._next_complaint) >= 0:
            self._next_complaint = ticks_add(now_ms, self._every)
            return True
        return False


class Lid(LidLogic):
    """LidLogic plus the real IR beam: update(now) samples it for you."""

    def __init__(self, beam, push_max_ms, full_after_ms, complain_every_ms,
                 now_ms):
        super().__init__(push_max_ms, full_after_ms, complain_every_ms,
                         now_ms)
        self._beam = beam

    def update(self, now_ms):
        LidLogic.update(self, self._beam.seen(), now_ms)
