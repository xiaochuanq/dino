"""voice - Dino's mouth: picks a random line from a list and speaks it.

The DY-SV17F sound board plays files from its own memory, so Dino keeps
thinking while it talks. VoiceLogic (pure logic, desktop-testable) tracks
one question - is Dino still talking? - using the board's BUSY wire, which
takes ~300 ms to wake up after play(), so right after a play we trust the
clock instead. If BUSY never wakes (board unplugged) a fallback timer
stops "talking" from sticking forever.

Voice adds the real board and Dino's manners:
    say_one_of(tracks)                 polite - waits its turn (skipped
                                       if Dino is already talking)
    say_one_of(tracks, important=True) interrupts whatever is playing
    then_say_one_of(tracks)            speaks AFTER the current line
                                       finishes (right away if quiet) -
                                       chain two lines without the
                                       second cutting off the first
"""
import random

try:
    from time import ticks_ms, ticks_diff, sleep_ms
except ImportError:  # desktop CPython for tests
    import time

    def ticks_ms():
        return int(time.monotonic() * 1000)

    def ticks_diff(a, b):
        return a - b

    def sleep_ms(ms):
        time.sleep(ms / 1000)


class VoiceLogic:
    def __init__(self, busy_assert_ms, fallback_ms):
        self._assert = busy_assert_ms
        self._fallback = fallback_ms
        self._started = None     # when play() was sent; None = quiet
        self._saw_busy = False
        self.is_talking = False

    def started(self, now_ms):
        """A track was just started."""
        self._started = now_ms
        self._saw_busy = False
        self.is_talking = True

    def update(self, busy, now_ms):
        """Feed one BUSY sample; returns (and stores) is_talking."""
        if self._started is None:
            self.is_talking = False
        elif ticks_diff(now_ms, self._started) < self._assert:
            self.is_talking = True       # BUSY can't be trusted yet
        elif busy:
            self._saw_busy = True
            self.is_talking = True
        elif self._saw_busy:
            self._started = None         # playback finished
            self.is_talking = False
        elif ticks_diff(now_ms, self._started) < self._fallback:
            self.is_talking = True       # BUSY never woke: trust the clock
        else:
            self._started = None
            self.is_talking = False
        return self.is_talking


class Voice:
    def __init__(self, player, busy_assert_ms, fallback_ms, pick=None):
        self._player = player
        self._logic = VoiceLogic(busy_assert_ms, fallback_ms)
        self._pick = pick or random.choice
        self._queued = None              # one follow-up line, at most

    @property
    def is_talking(self):
        return self._logic.is_talking

    def update(self, now_ms):
        self._logic.update(self._player.is_busy(), now_ms)
        if not self.is_talking and self._queued is not None:
            tracks, self._queued = self._queued, None
            self._player.play(self._pick(tracks))
            self._logic.started(now_ms)

    def say_one_of(self, tracks, important=False):
        """Speak a random track from the list. Returns True if it played."""
        if self.is_talking:
            if not important:
                return False             # polite: wait for the next chance
            self._player.stop()
            sleep_ms(20)                 # brief gap between UART commands
        self._queued = None              # a fresh line forgets any follow-up
        self._player.play(self._pick(tracks))
        self._logic.started(ticks_ms())
        return True

    def then_say_one_of(self, tracks):
        """Speak a random track AFTER the current line finishes (right
        away if nobody is talking). A newer say_one_of replaces it."""
        if not self.is_talking:
            return self.say_one_of(tracks)
        self._queued = tracks
        return True
