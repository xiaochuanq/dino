# Kid-Friendly Robot Parts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite Dino around four kid-named robot parts (`visitor`, `lid`, `voice`, `eyes`) and a SENSE → DECIDE → ACT main loop with `on_<human_event>()` handlers kids edit.

**Architecture:** Each part is one small file in `lib/`: a pure-logic class (desktop pytest-able, fed `now_ms` + raw values — the existing `bin_watch.py` pattern) plus a thin wrapper owning its device. `main.py` shrinks to a hardware-assembly block, five `on_*` handlers, and a three-step loop. Spec: `docs/superpowers/specs/2026-08-06-kid-friendly-parts-design.md`.

**Tech Stack:** MicroPython (Pico 2 W), desktop CPython + pytest for logic tests, `mpremote`/`deploy.sh` for deployment.

## Global Constraints

- Kid-facing names are concepts, never devices: `visitor`/`lid`/`voice`/`eyes`; event handlers are `on_<human_event>()` (e.g. `on_donation`, never `on_beam_blocked`).
- `machine` imports appear ONLY in `main.py`'s hardware section. Every `lib/` logic class must import cleanly on desktop CPython (use the `try: from time import ticks_diff ... except ImportError:` shim, as in `lib/bin_watch.py`).
- Sound priority: greeting/goodbye/appreciation are *important* (interrupt); passing noise and complaints are *polite* (skipped if talking).
- Distances: `HERE_MM = 1000`, `LEAVE_MM = 1500`, `PASSING_MM = 3000`. Pins: UART 0/1, BUSY 2, eyes 4, IR emit 5, IR receive 6/7/8, I2C1 on 14/15.
- Tests live in `tests/`, import lib modules flat (`from lid import LidLogic`) via the existing `tests/conftest.py`. Run with `python3 -m pytest tests/ -v`.
- Do not modify `lib/dysv17f.py`, `lib/ir_beam.py`, `lib/vl53l1x.py`, `lib/droid_sense.py`, or `examples/`.
- Commit after every green task; end commit messages with `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.

---

### Task 1: config.py rewrite

**Files:**
- Modify: `config.py` (full rewrite, content below)
- Test: `tests/test_config.py` (full rewrite, content below)

**Interfaces:**
- Consumes: nothing.
- Produces (names every later task uses): `PASSING_TRACKS`, `GREETING_TRACKS`, `GOODBYE_TRACKS`, `THANKS_TRACKS`, `FULL_TRACKS` (lists of int ≥ 1); `VOLUME`; `HERE_MM`, `LEAVE_MM`, `PASSING_MM`, `LASER_MODE`; `PASSING_COOLDOWN_S`, `LID_PUSH_MAX_MS`, `FULL_AFTER_S`, `COMPLAIN_EVERY_S`, `TALK_BLINK_MS`; `UART_ID`, `UART_TX_PIN`, `UART_RX_PIN`, `BUSY_PIN`, `EYES_PIN`, `IR_EMIT_PIN`, `IR_RECV_PINS` (list), `I2C_ID`, `I2C_SDA_PIN`, `I2C_SCL_PIN`; `IR_BEAM_SEEN_VALUE`, `BUSY_ACTIVE`, `IR_SETTLE_MS`, `IR_SAMPLE_COUNT`, `IR_SAMPLE_GAP_US`, `BUSY_ASSERT_MS`, `TALK_FALLBACK_MS`, `TICK_MS`.
- Removed (later tasks must not reference): `PIR_PIN`, `LED_PINS`, `IR_RECV1/2/3_PIN`, `TRACK_PASS_VOICE`, `TRACK_BEEP`, `TRACK_MOTION_VOICE`, `GREET_NEAR_MM`, `GREET_CLOSE_MM`, `FLASH_COUNT`, `FLASH_MS`, `ALERT_REPEAT_S`, `IR_PASS_MAX_MS`, `LED_FALLBACK_ON_MS`.

- [ ] **Step 1: Rewrite the test file**

Replace the entire content of `tests/test_config.py` with:

```python
import config


def test_track_lists_nonempty():
    for tracks in (config.PASSING_TRACKS, config.GREETING_TRACKS,
                   config.GOODBYE_TRACKS, config.THANKS_TRACKS,
                   config.FULL_TRACKS):
        assert isinstance(tracks, list)
        assert len(tracks) >= 1
        assert all(isinstance(t, int) and t >= 1 for t in tracks)


def test_distances_are_ordered():
    # here < leave gives the hysteresis gap; leave < passing gives the band
    assert 0 < config.HERE_MM < config.LEAVE_MM < config.PASSING_MM


def test_push_window_shorter_than_full_threshold():
    assert config.LID_PUSH_MAX_MS < config.FULL_AFTER_S * 1000


def test_push_window_spans_several_ticks():
    assert config.LID_PUSH_MAX_MS >= 2 * config.TICK_MS


def test_timing_values_positive():
    assert config.FULL_AFTER_S > 0
    assert config.COMPLAIN_EVERY_S > 0
    assert config.PASSING_COOLDOWN_S > 0
    assert config.TALK_BLINK_MS > 0
    assert config.TICK_MS > 0
    assert config.BUSY_ASSERT_MS > 0
    assert config.TALK_FALLBACK_MS > config.BUSY_ASSERT_MS
    assert config.IR_SAMPLE_COUNT > 0
    assert config.IR_SAMPLE_COUNT % 2 == 1
    assert config.IR_SAMPLE_GAP_US >= 0


def test_volume_in_module_range():
    assert 0 <= config.VOLUME <= 30


def test_ir_receiver_pins_listed():
    assert isinstance(config.IR_RECV_PINS, list)
    assert len(config.IR_RECV_PINS) >= 1


def test_old_device_names_are_gone():
    for name in ("PIR_PIN", "LED_PINS", "TRACK_PASS_VOICE", "TRACK_BEEP",
                 "GREET_NEAR_MM", "FLASH_COUNT", "ALERT_REPEAT_S",
                 "IR_PASS_MAX_MS", "LED_FALLBACK_ON_MS"):
        assert not hasattr(config, name)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_config.py -v`
Expected: FAIL (`AttributeError: ... 'PASSING_TRACKS'`, and `test_old_device_names_are_gone` fails on `PIR_PIN` etc.)

- [ ] **Step 3: Rewrite config.py**

Replace the entire content of `config.py` with:

```python
"""Dino smart bin robot - every tuning knob lives here.

Change a number, save, redeploy (./deploy.sh) - that's how you tune the robot.
"""

# --- Sounds: track numbers = file names on the DY-SV17F flash -----------
# 00003.wav on the module is track 3. Add a file, add its number to a list,
# and Dino picks one of the list at random every time.
PASSING_TRACKS = [3]       # funny noise when someone walks by (1-3 m)
GREETING_TRACKS = [1]      # "hello!" when someone comes close
GOODBYE_TRACKS = [4]       # "bye!" when they walk away
THANKS_TRACKS = [5]        # "thank you!" when they push the lid
FULL_TRACKS = [2]          # complaints while the bin is stuffed full
VOLUME = 30                # 0-30

# --- Distances (millimetres) ---------------------------------------------
HERE_MM = 1000             # closer than this -> visitor "is here": greet
LEAVE_MM = 1500            # farther than this -> visitor left: goodbye
                           # (the 500 mm gap stops greet/goodbye ping-pong)
PASSING_MM = 3000          # between LEAVE_MM and this -> just passing by
LASER_MODE = "medium"      # "short" ~1.3 m / "medium" ~2.9 m / "long" ~3.6 m
                           # (medium tops out ~2.9 m, so the passing band
                           # really ends at sensor range)

# --- Behavior timing ------------------------------------------------------
PASSING_COOLDOWN_S = 30    # quiet time between two passing noises
LID_PUSH_MAX_MS = 2000     # lid open shorter than this, then shut = a push
FULL_AFTER_S = 60          # lid open this many seconds -> bin is FULL
COMPLAIN_EVERY_S = 10      # seconds between complaints while FULL
TALK_BLINK_MS = 250        # eye blink speed while Dino is talking

# --- Pins (GP numbers on the Pico) ----------------------------------------
UART_ID = 0
UART_TX_PIN = 0            # GP0 (UART0 TX) -> DY-SV17F RX
UART_RX_PIN = 1            # GP1 (UART0 RX) -> DY-SV17F TX
BUSY_PIN = 2               # DY-SV17F BUSY output (CON3 pin)
EYES_PIN = 4               # both eye LEDs (in parallel), one GPIO
IR_EMIT_PIN = 5            # IR emitter LED (through 220 ohm)
IR_RECV_PINS = [6, 7, 8]   # IR receiver outputs
I2C_ID = 1                 # GP14/15 belong to I2C1 on the Pico
I2C_SDA_PIN = 14           # VL53L1X SDA
I2C_SCL_PIN = 15           # VL53L1X SCL

# --- Wiring polarity / fine timing -----------------------------------------
IR_BEAM_SEEN_VALUE = 0     # receiver pin reads this when the beam is SEEN
BUSY_ACTIVE = 1            # BUSY pin value while a sound is playing
IR_SETTLE_MS = 1           # emitter-on settle time before reading receiver
IR_SAMPLE_COUNT = 5        # majority vote over this many receiver reads (odd)
IR_SAMPLE_GAP_US = 200     # gap between the receiver reads
BUSY_ASSERT_MS = 300       # after play(), BUSY can't be trusted this long
TALK_FALLBACK_MS = 3000    # assumed talk time if BUSY never asserts
TICK_MS = 50               # main loop tick
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_config.py -v`
Expected: PASS (all). Note: `tests/test_bin_watch.py` and `tests/test_flash_burst.py` still pass — they don't import config. `main.py` is now broken (references deleted names) — that is expected until Task 6; nothing on desktop imports it.

- [ ] **Step 5: Commit**

```bash
git add config.py tests/test_config.py
git commit -m "feat: config for kid-friendly parts - sound lists, distance knobs, new pin map

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: lib/lid.py — LidLogic + Lid

**Files:**
- Create: `lib/lid.py`
- Test: `tests/test_lid.py`

**Interfaces:**
- Consumes: `IRBeam.seen() -> bool` from `lib/ir_beam.py` (wrapper only).
- Produces: `LidLogic(push_max_ms, full_after_ms, complain_every_ms, now_ms)` with `update(beam_seen, now_ms)`, one-tick flag `just_pushed`, properties `is_open`, `is_full`, method `complain_due(now_ms) -> bool`. `Lid(beam, push_max_ms, full_after_ms, complain_every_ms, now_ms)` — same surface but `update(now_ms)` samples the beam itself. Task 6 builds `Lid(...)` and reads `lid.just_pushed`, `lid.complain_due(now)`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_lid.py`:

```python
from lid import LidLogic

S = 1000  # ms per second


def make(now=0):
    return LidLogic(push_max_ms=2 * S, full_after_ms=60 * S,
                     complain_every_ms=10 * S, now_ms=now)


def test_starts_closed_and_not_full():
    d = make()
    assert d.is_open is False
    assert d.is_full is False
    assert d.just_pushed is False


def test_blocked_beam_means_open():
    d = make()
    d.update(False, 1 * S)          # beam blocked = lid pushed open
    assert d.is_open is True
    d.update(True, 2 * S)           # beam seen = lid closed
    assert d.is_open is False


def test_quick_open_then_close_is_a_push():
    d = make()
    d.update(False, 0)
    d.update(True, 1 * S)           # closed after 1s < 2s window
    assert d.just_pushed is True


def test_push_flag_lasts_one_tick():
    d = make()
    d.update(False, 0)
    d.update(True, 1 * S)
    assert d.just_pushed is True
    d.update(True, 1 * S + 50)
    assert d.just_pushed is False


def test_slow_close_is_not_a_push():
    d = make()
    d.update(False, 0)
    d.update(True, 3 * S)           # closed after 3s > 2s window
    assert d.just_pushed is False


def test_open_59s_is_not_full():
    d = make()
    d.update(False, 59 * S)
    assert d.is_full is False


def test_open_60s_is_full():
    d = make()
    d.update(False, 60 * S)
    assert d.is_full is True


def test_closing_resets_the_full_clock():
    d = make()
    d.update(True, 30 * S)
    d.update(False, 89 * S)         # only 59s since last closed
    assert d.is_full is False
    d.update(False, 90 * S)         # 60s since last closed
    assert d.is_full is True


def test_closing_clears_full_immediately():
    d = make()
    d.update(False, 60 * S)
    assert d.is_full is True
    d.update(True, 61 * S)
    assert d.is_full is False


def test_closing_a_full_lid_is_not_a_push():
    d = make()
    d.update(False, 60 * S)         # full now
    d.update(True, 61 * S)          # emptied/cleared - not a donation push
    assert d.just_pushed is False


def test_no_complaints_while_normal():
    d = make()
    assert d.complain_due(30 * S) is False


def test_first_complaint_immediate_then_repeats():
    d = make()
    d.update(False, 60 * S)
    assert d.complain_due(60 * S) is True     # right when it goes full
    assert d.complain_due(60 * S) is False    # slot consumed
    assert d.complain_due(65 * S) is False    # not due yet
    assert d.complain_due(70 * S) is True     # COMPLAIN_EVERY later
    assert d.complain_due(71 * S) is False


def test_closing_stops_complaints():
    d = make()
    d.update(False, 60 * S)
    assert d.complain_due(60 * S) is True
    d.update(True, 62 * S)
    assert d.complain_due(70 * S) is False


def test_lid_wrapper_samples_its_own_beam():
    from lid import Lid

    class FakeBeam:
        def __init__(self):
            self.value = True

        def seen(self):
            return self.value

    beam = FakeBeam()
    d = Lid(beam, push_max_ms=2 * S, full_after_ms=60 * S,
             complain_every_ms=10 * S, now_ms=0)
    beam.value = False
    d.update(1 * S)
    assert d.is_open is True
    beam.value = True
    d.update(2 * S)
    assert d.just_pushed is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_lid.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'lid'`

- [ ] **Step 3: Write lib/lid.py**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_lid.py -v`
Expected: PASS (all 14)

- [ ] **Step 5: Commit**

```bash
git add lib/lid.py tests/test_lid.py
git commit -m "feat: lid part - open/pushed/full from the IR beam, kid-facing names

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: lib/visitor.py — VisitorLogic + Visitor

**Files:**
- Create: `lib/visitor.py`
- Test: `tests/test_visitor.py`

**Interfaces:**
- Consumes: `read_mm(sensor) -> int|None` from `lib/droid_sense.py:168` (wrapper only).
- Produces: constants `AWAY = "away"`, `PASSING = "passing"`, `HERE = "here"`; `VisitorLogic(here_mm, leave_mm, passing_mm, cooldown_ms, samples=5, hold_ms=300, stale_ms=2000)` with `update(mm_or_None, now_ms)`, state `where`, one-tick flags `just_arrived`, `just_left`, `just_passed`. `Visitor(sensor, here_mm, leave_mm, passing_mm, cooldown_ms)` — same surface, `update(now_ms)` reads the laser itself. Task 6 builds `Visitor(...)` and reads `visitor.where`, `visitor.just_arrived/just_left/just_passed`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_visitor.py`:

```python
from visitor import VisitorLogic, AWAY, PASSING, HERE

S = 1000  # ms per second


def make(**kw):
    """samples=1 + hold_ms=0 so plain logic tests need only two updates
    per reading (first proposes the zone, second accepts it)."""
    args = dict(here_mm=1000, leave_mm=1500, passing_mm=3000,
                cooldown_ms=30 * S, samples=1, hold_ms=0)
    args.update(kw)
    return VisitorLogic(**args)


def settle(v, mm, t):
    """Feed the same reading twice so the zone change is accepted;
    returns the visitor so flag asserts read naturally."""
    v.update(mm, t)
    v.update(mm, t + 1)
    return v


def test_starts_away():
    v = make()
    assert v.where == AWAY
    assert v.just_arrived is False


def test_arriving_close_fires_once():
    v = make()
    settle(v, 800, 0)
    assert v.where == HERE
    assert v.just_arrived is True
    v.update(800, 100)                  # still standing there
    assert v.just_arrived is False      # no re-greet


def test_hovering_at_the_boundary_stays_here():
    v = make()
    settle(v, 800, 0)
    settle(v, 1200, 1 * S)              # between HERE_MM and LEAVE_MM
    assert v.where == HERE              # hysteresis holds them "here"
    assert v.just_left is False


def test_stepping_past_leave_mm_is_leaving():
    v = make()
    settle(v, 800, 0)
    settle(v, 1600, 5 * S)              # beyond LEAVE_MM
    assert v.where == PASSING
    assert v.just_left is True


def test_leaving_re_arms_the_greeting():
    v = make()
    settle(v, 800, 0)
    settle(v, 1600, 5 * S)
    settle(v, 900, 10 * S)              # comes back
    assert v.just_arrived is True


def test_vanishing_readings_mean_they_left():
    v = make(stale_ms=2 * S)
    settle(v, 800, 0)
    v.update(None, 1 * S)               # nothing in sight, not stale yet
    assert v.where == HERE
    v.update(None, 4 * S)               # stale: they are gone
    assert v.where == AWAY
    assert v.just_left is True


def test_passing_band_fires_noise_with_cooldown():
    v = make()
    settle(v, 2000, 0)                  # walks into the 1.5-3 m band
    assert v.where == PASSING
    assert v.just_passed is True
    v.update(2000, 10 * S)              # still in the band, too soon
    assert v.just_passed is False
    v.update(2000, 31 * S)              # cooldown over
    assert v.just_passed is True


def test_beyond_passing_band_is_away():
    v = make()
    settle(v, 3500, 0)
    assert v.where == AWAY
    assert v.just_passed is False


def test_median_ignores_one_wild_reading():
    v = make(samples=5)
    for i, mm in enumerate([800, 800, 4000, 800, 800]):
        v.update(mm, i * 100)
    assert v.where == HERE              # the 4000 outlier never wins


def test_hold_time_delays_zone_changes():
    v = make(hold_ms=300)
    v.update(800, 0)                    # proposes HERE
    v.update(800, 100)
    assert v.where == AWAY              # not held long enough yet
    v.update(800, 400)
    assert v.where == HERE
    assert v.just_arrived is True


def test_visitor_wrapper_reads_its_own_laser():
    from visitor import Visitor

    class FakeLaser:
        """read_mm() falls back to .read() for objects without an i2c."""

        def __init__(self):
            self.mm = 800

        def read(self):
            return self.mm

    v = Visitor(FakeLaser(), here_mm=1000, leave_mm=1500, passing_mm=3000,
                cooldown_ms=30 * S)
    # defaults samples=5, hold_ms=300: feed enough ticks to settle
    for t in range(0, 1000, 50):
        v.update(t)
    assert v.where == HERE
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_visitor.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'visitor'`

- [ ] **Step 3: Write lib/visitor.py**

```python
"""visitor - who is near Dino, told by an invisible laser tape-measure.

The VL53L1X laser distance sensor times an eye-safe light pulse and
reports how far away the nearest person is, in millimetres. VisitorLogic
(pure logic, desktop-testable) turns those raw distances into one simple
answer - where is the visitor? - plus one-tick news flags:

    where         "away" (or nobody), "passing" (walking by, 1.5-3 m),
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

from droid_sense import read_mm

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

    def __init__(self, sensor, here_mm, leave_mm, passing_mm, cooldown_ms):
        super().__init__(here_mm, leave_mm, passing_mm, cooldown_ms)
        self._sensor = sensor

    def update(self, now_ms):
        VisitorLogic.update(self, read_mm(self._sensor), now_ms)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_visitor.py -v`
Expected: PASS (all 12). Note `test_stepping_past_leave_mm_is_leaving`: the same tick also sets `just_passed` (they stepped into the passing band with the cooldown fresh) — that is by design; goodbye is *important* and wins the speaker, the noise politely skips.

- [ ] **Step 5: Commit**

```bash
git add lib/visitor.py tests/test_visitor.py
git commit -m "feat: visitor part - away/passing/here zones with hysteresis and noise cooldown

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 4: lib/voice.py — VoiceLogic + Voice

**Files:**
- Create: `lib/voice.py`
- Test: `tests/test_voice.py`

**Interfaces:**
- Consumes: `DYSV17F.play(track)`, `.stop()`, `.is_busy()` from `lib/dysv17f.py` (wrapper only).
- Produces: `VoiceLogic(busy_assert_ms, fallback_ms)` with `started(now_ms)`, `update(busy, now_ms) -> bool`, attribute `is_talking`. `Voice(player, busy_assert_ms, fallback_ms, pick=None)` with `say_one_of(tracks, important=False) -> bool`, `update(now_ms)`, property `is_talking`. Task 6 builds `Voice(player, config.BUSY_ASSERT_MS, config.TALK_FALLBACK_MS)`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_voice.py`:

```python
from voice import VoiceLogic, Voice


def make():
    return VoiceLogic(busy_assert_ms=300, fallback_ms=3000)


def test_quiet_at_start():
    v = make()
    assert v.update(False, 0) is False


def test_trusts_the_clock_right_after_play():
    v = make()
    v.started(1000)
    # BUSY hasn't woken up yet - Dino is still talking
    assert v.update(False, 1100) is True


def test_busy_keeps_talking_then_release_ends_it():
    v = make()
    v.started(0)
    assert v.update(True, 400) is True
    assert v.update(True, 2000) is True
    assert v.update(False, 2500) is False


def test_fallback_when_busy_never_asserts():
    v = make()
    v.started(0)
    assert v.update(False, 400) is True      # module missing? assume talking
    assert v.update(False, 2999) is True
    assert v.update(False, 3000) is False    # ...but not forever


def test_long_talk_outlasts_fallback_once_busy_seen():
    v = make()
    v.started(0)
    v.update(True, 400)
    assert v.update(True, 10000) is True


class FakePlayer:
    def __init__(self):
        self.played = []
        self.stops = 0
        self.busy = False

    def play(self, track):
        self.played.append(track)

    def stop(self):
        self.stops += 1

    def is_busy(self):
        return self.busy


def make_voice(player):
    # pick=min makes the random choice deterministic for tests
    return Voice(player, busy_assert_ms=300, fallback_ms=3000, pick=min)


def test_say_one_of_plays_a_track_from_the_list():
    p = FakePlayer()
    v = make_voice(p)
    assert v.say_one_of([7, 9]) is True
    assert p.played == [7]
    assert v.is_talking is True


def test_polite_line_is_skipped_while_talking():
    p = FakePlayer()
    v = make_voice(p)
    v.say_one_of([7])
    assert v.say_one_of([9]) is False
    assert p.played == [7]              # nothing new played
    assert p.stops == 0


def test_important_line_interrupts():
    p = FakePlayer()
    v = make_voice(p)
    v.say_one_of([7])
    assert v.say_one_of([9], important=True) is True
    assert p.stops == 1                 # cut off the old line
    assert p.played == [7, 9]


def test_update_follows_the_player_busy_wire():
    p = FakePlayer()
    v = make_voice(p)
    v.update(0)
    assert v.is_talking is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_voice.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'voice'`

- [ ] **Step 3: Write lib/voice.py**

```python
"""voice - Dino's mouth: picks a random line from a list and speaks it.

The DY-SV17F sound board plays files from its own memory, so Dino keeps
thinking while it talks. VoiceLogic (pure logic, desktop-testable) tracks
one question - is Dino still talking? - using the board's BUSY wire, which
takes ~300 ms to wake up after play(), so right after a play we trust the
clock instead. If BUSY never wakes (board unplugged) a fallback timer
stops "talking" from sticking forever.

Voice adds the real board and Dino's one manners rule:
    say_one_of(tracks)                 polite - waits its turn (skipped
                                       if Dino is already talking)
    say_one_of(tracks, important=True) interrupts whatever is playing
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

    @property
    def is_talking(self):
        return self._logic.is_talking

    def update(self, now_ms):
        self._logic.update(self._player.is_busy(), now_ms)

    def say_one_of(self, tracks, important=False):
        """Speak a random track from the list. Returns True if it played."""
        if self.is_talking:
            if not important:
                return False             # polite: wait for the next chance
            self._player.stop()
            sleep_ms(20)                 # brief gap between UART commands
        self._player.play(self._pick(tracks))
        self._logic.started(ticks_ms())
        return True
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_voice.py -v`
Expected: PASS (all 9)

- [ ] **Step 5: Commit**

```bash
git add lib/voice.py tests/test_voice.py
git commit -m "feat: voice part - random lines, polite-vs-important manners, BUSY state machine

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 5: lib/eyes.py — Eyes

**Files:**
- Create: `lib/eyes.py`
- Test: `tests/test_eyes.py`

**Interfaces:**
- Consumes: a `Pin`-like object with `.value(x)` (injected).
- Produces: `Eyes(pin, blink_ms)` with `update(now_ms, talking)`. Task 6 builds `Eyes(Pin(config.EYES_PIN, ...), config.TALK_BLINK_MS)`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_eyes.py`:

```python
from eyes import Eyes


class FakePin:
    def __init__(self):
        self.v = None

    def value(self, x):
        self.v = x


def test_steady_glow_when_quiet():
    pin = FakePin()
    eyes = Eyes(pin, blink_ms=250)
    eyes.update(0, talking=False)
    assert pin.v == 1
    eyes.update(12345, talking=False)
    assert pin.v == 1


def test_blinks_while_talking():
    pin = FakePin()
    eyes = Eyes(pin, blink_ms=250)
    eyes.update(0, talking=True)
    first = pin.v
    eyes.update(250, talking=True)      # next blink phase
    assert pin.v != first
    eyes.update(500, talking=True)      # and back
    assert pin.v == first


def test_glow_returns_after_talking():
    pin = FakePin()
    eyes = Eyes(pin, blink_ms=250)
    eyes.update(250, talking=True)
    eyes.update(300, talking=False)
    assert pin.v == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_eyes.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'eyes'`

- [ ] **Step 3: Write lib/eyes.py**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_eyes.py -v`
Expected: PASS (all 3)

- [ ] **Step 5: Commit**

```bash
git add lib/eyes.py tests/test_eyes.py
git commit -m "feat: eyes part - steady glow, blink while talking

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 6: main.py rewrite + retire the old machinery

**Files:**
- Modify: `main.py` (full rewrite, content below)
- Delete: `lib/bin_watch.py`, `tests/test_bin_watch.py`, `tests/test_flash_burst.py`, `config_REMOTE_1092.py`

**Interfaces:**
- Consumes everything Tasks 1–5 produced: `Lid(beam, push_max_ms, full_after_ms, complain_every_ms, now_ms)`, `Visitor(sensor, here_mm, leave_mm, passing_mm, cooldown_ms)`, `Voice(player, busy_assert_ms, fallback_ms)`, `Eyes(pin, blink_ms)`; plus unchanged `DYSV17F`, `IRBeam`, `VL53L1X`, `DeadSensor`, `set_mode`.
- Produces: the program kids read. No later task consumes it.

- [ ] **Step 1: Rewrite main.py**

Replace the entire content of `main.py` with:

```python
"""Dino the smart donation bin - main program.

HOW DINO THINKS - the loop at the bottom, three steps every tick:
  1. SENSE  - each body part looks at the world and updates its state.
  2. DECIDE - simple ifs turn those states into human events.
  3. ACT    - the on_...() functions say what Dino does. Edit them!

DINO'S BODY PARTS (built in the hardware section - the only place
device names appear):
  visitor - a laser tape-measure: is someone away / passing / here?
  lid    - an IR light beam across the flap: open? pushed? stuck-open full?
  voice   - a sound board: speaks random lines, knows if it's talking
  eyes    - two LEDs: steady glow, lively blink while talking

WIRING (GP numbers; tuning knobs in config.py)
    DY-SV17F   VCC -> VBUS (5 V), GND -> GND,
               RX -> GP0 (UART0 TX), TX -> GP1 (UART0 RX),
               CON3 -> GP2 (becomes BUSY; strap 4.7 k to 3.3 V),
               CON1 + CON2 -> GND direct, SPK+/SPK- -> speaker
    Eyes       GP4 -> two LEDs in parallel, EACH through its own
               resistor -> GND
    IR beam    emitter: GP5 --[220 ohm]--> anode, cathode -> GND
               receivers: -> GP6, GP7, GP8 (internal pull-ups)
    VL53L1X    VIN -> 3V3, GND -> GND, SDA -> GP14, SCL -> GP15 (I2C1)
"""
import time
from machine import Pin, UART, I2C

import config
from dysv17f import DYSV17F
from ir_beam import IRBeam
from vl53l1x import VL53L1X
from droid_sense import DeadSensor, set_mode
from visitor import Visitor
from lid import Lid
from voice import Voice
from eyes import Eyes

# --- hardware: build Dino's body parts ----------------------------------
now = time.ticks_ms()

uart = UART(config.UART_ID, baudrate=9600,
            tx=Pin(config.UART_TX_PIN), rx=Pin(config.UART_RX_PIN))
player = DYSV17F(uart, busy_pin=Pin(config.BUSY_PIN, Pin.IN),
                 busy_active=config.BUSY_ACTIVE)
player.set_volume(config.VOLUME)
voice = Voice(player, config.BUSY_ASSERT_MS, config.TALK_FALLBACK_MS)

beam = IRBeam(Pin(config.IR_EMIT_PIN, Pin.OUT, value=0),
              [Pin(n, Pin.IN, pull=Pin.PULL_UP) for n in config.IR_RECV_PINS],
              config.IR_BEAM_SEEN_VALUE, config.IR_SETTLE_MS,
              config.IR_SAMPLE_COUNT, config.IR_SAMPLE_GAP_US)
lid = Lid(beam, config.LID_PUSH_MAX_MS, config.FULL_AFTER_S * 1000,
            config.COMPLAIN_EVERY_S * 1000, now)

try:
    laser = VL53L1X(I2C(config.I2C_ID, sda=Pin(config.I2C_SDA_PIN),
                        scl=Pin(config.I2C_SCL_PIN)))
    set_mode(laser, config.LASER_MODE)
except OSError:
    laser = DeadSensor()   # no laser: lid still works, greetings off
visitor = Visitor(laser, config.HERE_MM, config.LEAVE_MM,
                  config.PASSING_MM, config.PASSING_COOLDOWN_S * 1000)

eyes = Eyes(Pin(config.EYES_PIN, Pin.OUT, value=1), config.TALK_BLINK_MS)


# --- ACT: what Dino does. Kids, edit these! ------------------------------
def on_visitor_passing():
    """Someone walks by, 1.5-3 m away."""
    voice.say_one_of(config.PASSING_TRACKS)


def on_visitor_arrives():
    """Someone comes close - say hello!"""
    voice.say_one_of(config.GREETING_TRACKS, important=True)


def on_visitor_leaves():
    """They walk away - say goodbye!"""
    voice.say_one_of(config.GOODBYE_TRACKS, important=True)


def on_donation():
    """They pushed the lid - thank them!"""
    voice.say_one_of(config.THANKS_TRACKS, important=True)


def on_bin_full():
    """The lid is stuck open - Dino is stuffed. Complain!"""
    voice.say_one_of(config.FULL_TRACKS)


# --- the loop: SENSE -> DECIDE -> ACT ------------------------------------
while True:
    now = time.ticks_ms()

    # 1. SENSE - every part looks at the world
    visitor.update(now)
    lid.update(now)
    voice.update(now)

    # 2. DECIDE - turn states into human events
    if lid.just_pushed and visitor.where == "here":
        on_donation()              # a donation beats a greeting
    elif visitor.just_arrived:
        on_visitor_arrives()
    if visitor.just_left:
        on_visitor_leaves()
    if visitor.just_passed:
        on_visitor_passing()
    if lid.complain_due(now):
        on_bin_full()

    # 3. SHOW - the eyes follow the mood
    eyes.update(now, voice.is_talking)

    time.sleep_ms(config.TICK_MS)
```

- [ ] **Step 2: Delete the retired files**

```bash
git rm lib/bin_watch.py tests/test_bin_watch.py tests/test_flash_burst.py config_REMOTE_1092.py
```

- [ ] **Step 3: Verify nothing still references the removed pieces**

Run: `grep -rn "bin_watch\|BinWatch\|FlashBurst\|set_leds\|pir\." main.py lib/ tests/ deploy.sh`
Expected: no output. (`examples/` is exempt — it exercises raw hardware.)

- [ ] **Step 4: Run the whole desktop suite**

Run: `python3 -m pytest tests/ -v`
Expected: PASS — test_config, test_lid, test_visitor, test_voice, test_eyes, test_dysv17f all green; the two deleted test files gone from collection.

- [ ] **Step 5: Compile-check main.py for syntax (it can't run on desktop — `machine` is Pico-only)**

Run: `python3 -m py_compile main.py && echo OK`
Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add main.py
git commit -m "feat: rewrite main as SENSE/DECIDE/ACT with kid-facing parts; retire bin_watch

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 7: README + on-hardware verification

**Files:**
- Modify: `README.md` (full rewrite of the affected sections, content below)

**Interfaces:**
- Consumes: everything above. Produces: docs only.

- [ ] **Step 1: Rewrite README.md**

Replace the entire content of `README.md` with:

````markdown
# Dino — Smart Donation Bin Robot

A MicroPython robot for a Raspberry Pi Pico 2 / 2 W on a donation bin.
Dino watches with a laser tape-measure and an invisible IR light beam:

- Someone walks by (1.5–3 m) → a random funny noise (then a cooldown).
- Someone comes close (< 1 m) → a random greeting, once per visit.
- They walk away (> 1.5 m) → a random goodbye.
- They push the lid flap while standing close → a random thank-you.
- The lid is stuck open 60 s → the bin is FULL → complaints every 10 s
  until it closes.
- Eyes glow steadily, and blink while Dino talks.

Design spec: `docs/superpowers/specs/2026-08-06-kid-friendly-parts-design.md`

## How the code thinks (read `main.py`!)

Dino has four body parts — `visitor`, `lid`, `voice`, `eyes` — and one
loop with three steps every tick:

1. **SENSE** — each part looks at the world and updates its state.
2. **DECIDE** — simple ifs turn states into human events.
3. **ACT** — the `on_...()` functions say what Dino does. **Edit these!**

## Wiring

| Pico pin | Goes to |
|---|---|
| GP0 (UART0 TX) | DY-SV17F RX |
| GP1 (UART0 RX) | DY-SV17F TX |
| GP2 | DY-SV17F CON3 (doubles as BUSY output in UART mode) |
| GP4 | Both eye LEDs in parallel, each through its own resistor → GND |
| GP5 | IR emitter LED (+ 220 Ω resistor) |
| GP6, GP7, GP8 | IR receiver outputs |
| GP14 / GP15 | VL53L1X SDA / SCL (I2C1) |
| VBUS (5 V) / GND | DY-SV17F power (UART is 3.3 V-safe) |
| 3V3 / GND | VL53L1X power |

DY-SV17F straps for UART mode: CON1=0, CON2=0, CON3=1. Speaker on the
module's speaker terminals.

## Sounds

Connect the DY-SV17F over USB and copy WAV files named `00001.wav`,
`00002.wav`, … onto it. Each mood is a list of track numbers in
`config.py` — Dino picks one at random every time:

| List | Played when |
|---|---|
| `GREETING_TRACKS` | someone comes close |
| `GOODBYE_TRACKS` | they walk away |
| `THANKS_TRACKS` | they push the lid |
| `PASSING_TRACKS` | someone walks by |
| `FULL_TRACKS` | the bin is stuffed full |

Add a sound = copy the file + add its number to a list.

Manners: greetings, goodbyes and thank-yous are *important* — they
interrupt whatever is playing. Passing noises and complaints are
*polite* — they skip their turn if Dino is already talking.

## Tuning (edit `config.py`)

| Constant | What it does | Default |
|---|---|---|
| `HERE_MM` | closer than this = the visitor is here | 1000 |
| `LEAVE_MM` | farther than this = they left (hysteresis gap) | 1500 |
| `PASSING_MM` | outer edge of the walking-by band | 3000 |
| `PASSING_COOLDOWN_S` | quiet time between passing noises | 30 |
| `LID_PUSH_MAX_MS` | lid open shorter than this = a push | 2000 |
| `FULL_AFTER_S` | lid open this long = FULL | 60 |
| `COMPLAIN_EVERY_S` | seconds between complaints while FULL | 10 |
| `TALK_BLINK_MS` | eye blink speed while talking | 250 |
| `VOLUME` | loudness 0–30 | 30 |

If the beam reads backwards, flip `IR_BEAM_SEEN_VALUE`.

## Deploy

```bash
./deploy.sh        # copies lib/, main.py, config.py to the Pico
mpremote repl      # watch it run (Ctrl-D to soft-reboot)
```

If a Pico was deployed before this rewrite, remove the retired module
once: `mpremote rm :lib/bin_watch.py`

## Check the wiring one piece at a time

```bash
mpremote run examples/02_test_ir.py       # IR beam (prints state)
mpremote run examples/03_test_sound.py    # sound + LEDs
mpremote run examples/09_test_laser.py    # laser distance sensor
```

## Desktop tests (no hardware needed)

```bash
pip install -r requirements-dev.txt
python3 -m pytest tests/ -v
```
````

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: README for the kid-friendly parts rewrite

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

- [ ] **Step 3: Deploy and verify on hardware (needs the physical bin)**

```bash
./deploy.sh
mpremote rm :lib/bin_watch.py   # only if this Pico was deployed before
mpremote repl                   # Ctrl-D to soft-reboot into main.py
```

Walk-test checklist (from the spec's Verification section):
- Walk by 1.5–3 m away → one noise, then silence for 30 s even if you keep pacing.
- Walk up close (< 1 m) → greeting; hover around the 1 m line → no re-greet.
- Step back past 1.5 m → goodbye, and the next approach greets again.
- Stand close and push the lid flap briefly → thank-you. Push it with nobody close → silence.
- Hold the lid open 60 s → complaint immediately, then every 10 s; let it close → complaints stop.
- Eyes: steady glow when quiet, blinking during every sound.
- Unplug the laser, reboot → lid behaviors still work, greetings silently off.

Report any hardware-test failures back rather than marking this step done.
