"""visitor - who is near Dino, told by an invisible laser tape-measure.

The VL53L1X laser distance sensor times an eye-safe light pulse and
reports how far away the nearest person is, in millimetres. VisitorLogic
(pure logic, desktop-testable) turns those raw distances into one simple
answer - where is the visitor? - plus one-tick news flags:

    where         "away" (or nobody), "passing" (walking by, 1-3 m),
                  or "here" (close enough to talk to, under 1 m)
    just_arrived  (one tick) they came close - greet them!
    just_left     (one tick) they walked away - say goodbye!
    just_passed   (one tick) someone in the passing band, and the noise
                  cooldown has expired - make a funny noise!

Steadiness tricks (all tunable): a median over the last few readings
ignores one wild reading; a zone change must hold for hold_ms before it
counts; "here" only ends past leave_mm (farther than here_mm), so a
visitor hovering at the boundary is not greeted twice; readings of None
(nothing in sight / sensor unplugged) fade to "away" after stale_ms.
"""
try:
    from time import ticks_diff
except ImportError:  # desktop CPython for tests

    def ticks_diff(a, b):
        return a - b

AWAY = "away"
PASSING = "passing"
HERE = "here"


class VisitorLogic:
    def __init__(self, here_mm, leave_mm, passing_mm, cooldown_ms,
                 samples=5, hold_ms=300, stale_ms=2000):
        self._here = here_mm
        self._leave = leave_mm
        self._passing = passing_mm
        self._cooldown = cooldown_ms
        self._samples = samples
        self._hold = hold_ms
        self._stale = stale_ms
        self._buf = []
        self._cand = AWAY
        self._cand_since = 0
        self._last_good = 0
        self._last_noise = None
        self.where = AWAY
        self.just_arrived = False
        self.just_left = False
        self.just_passed = False

    def update(self, mm, now_ms):
        """Feed one distance (mm, or None for "nothing in sight")."""
        was = self.where
        self.just_arrived = self.just_left = self.just_passed = False
        if mm is None:
            if ticks_diff(now_ms, self._last_good) > self._stale:
                self.where = self._cand = AWAY
                self._buf = []
        else:
            self._last_good = now_ms
            self._buf.append(mm)
            if len(self._buf) > self._samples:
                self._buf.pop(0)
            median = sorted(self._buf)[len(self._buf) // 2]
            zone = self._classify(median)
            if zone != self._cand:
                self._cand = zone
                self._cand_since = now_ms
            elif zone != self.where and \
                    ticks_diff(now_ms, self._cand_since) >= self._hold:
                self.where = zone
        if self.where == HERE and was != HERE:
            self.just_arrived = True
        if was == HERE and self.where != HERE:
            self.just_left = True
        if self.where == PASSING and (
                self._last_noise is None or
                ticks_diff(now_ms, self._last_noise) >= self._cooldown):
            self.just_passed = True
            self._last_noise = now_ms

    def _classify(self, mm):
        if mm <= self._here:
            return HERE
        if self.where == HERE and mm < self._leave:
            return HERE          # hysteresis: "here" ends past leave_mm
        if mm <= self._passing:
            return PASSING
        return AWAY


class Visitor(VisitorLogic):
    """VisitorLogic plus the real laser: update(now) reads it for you."""

    def __init__(self, laser, here_mm, leave_mm, passing_mm, cooldown_ms):
        super().__init__(here_mm, leave_mm, passing_mm, cooldown_ms)
        self._laser = laser      # answers mm(now_ms); heals itself

    def update(self, now_ms):
        VisitorLogic.update(self, self._laser.mm(now_ms), now_ms)

