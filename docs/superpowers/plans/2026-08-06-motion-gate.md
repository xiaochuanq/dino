# Motion-Gated Visitor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring back the HC-SR501 PIR (on GP10) as a gate inside the `visitor` part: the laser is only believed while something warm has moved within `MOTION_HOLD_S`, so parked objects stop triggering passing noises and greetings.

**Architecture:** Restore the proven `lib/droid_motion.py` (MotionFilter + Pir) from commit `0f745c4` with a GP3→GP10 adaptation; add a three-line gate to `VisitorLogic.update()` that forces `mm = None` when nothing has moved lately (reusing the existing stale→away path); wire the `Pir` into `Visitor` and `main.py`. Spec: `docs/superpowers/specs/2026-08-06-motion-gated-visitor-design.md`.

**Tech Stack:** MicroPython (Pico 2 W), desktop CPython + pytest, `mpremote`/`deploy.sh`.

## Global Constraints

- Kid-facing rule, stated everywhere it matters: "Dino only believes the laser when something warm has moved in the last 15 seconds."
- `machine` imports only in `main.py` and inside `droid_motion._default_pin_factory` (lazy import, desktop-safe — that's how the restored file already does it).
- New config names: `PIR_PIN = 10`, `PIR_WARMUP_S = 60`, `MOTION_HOLD_S = 15`. GP10 everywhere; GP3 appears nowhere.
- `VisitorLogic.update` signature becomes `update(self, mm, moving, now_ms)`; `Visitor` becomes `Visitor(sensor, pir, here_mm, leave_mm, passing_mm, cooldown_ms, motion_hold_ms)`.
- Do not modify lid, voice, eyes, the DECIDE block, or `lib/droid_sense.py`.
- Tests run from the repo root: `python3 -m pytest tests/ -q`. Suite currently has 56 tests; it grows with each task and must be fully green at every commit.
- Commit after every green task; end commit messages with `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.

---

### Task 1: Restore lib/droid_motion.py + port its tests

**Files:**
- Create: `lib/droid_motion.py` (from git history, two small edits)
- Test: `tests/test_droid_motion.py` (ported from ../pico-droid, one small edit)

**Interfaces:**
- Consumes: nothing.
- Produces (Tasks 3–4 depend on): `MotionFilter(warmup_ms=60_000, diff=None)` with `update(level, now_ms)`, `ready()`, `motion()`, `motion_started()`; `Pir(pin=10, warmup_s=60, pin_factory=None)` with `ready()`, `motion()`, `motion_started()` — each `Pir` method polls the pin itself.

- [ ] **Step 1: Restore the module from history**

```bash
git show 0f745c4:lib/droid_motion.py > lib/droid_motion.py
```

- [ ] **Step 2: Adapt GP3 → GP10 (three spots)**

In `lib/droid_motion.py`:
1. Docstring WIRING block: `OUT  ------------------>  GP3` → `OUT  ------------------>  GP10`
2. `Pir` class docstring: `pir = Pir()                  # OUT on GP3, 60 s warm-up` → `# OUT on GP10, 60 s warm-up`
3. `Pir.__init__` signature: `def __init__(self, pin=3, warmup_s=60, pin_factory=None):` → `def __init__(self, pin=10, warmup_s=60, pin_factory=None):`

Verify no `GP3`/`pin=3` remains: `grep -n "GP3\|pin=3" lib/droid_motion.py` → empty.

- [ ] **Step 3: Port the tests**

```bash
cp /mnt/c/Users/qinx/games/pico-droid/tests/test_droid_motion.py tests/test_droid_motion.py
```

Then edit the one pin-default test to match GP10:

```python
def test_default_pin_is_gp10():
    _, made = make_pir()
    assert made["pin"].gp == 10
```

(replaces `test_default_pin_is_gp3`, which asserted `== 3`).

- [ ] **Step 4: Run the tests**

Run: `python3 -m pytest tests/test_droid_motion.py -v`
Expected: PASS (13 tests). Then `python3 -m pytest tests/ -q` → 69 passed.

- [ ] **Step 5: Commit**

```bash
git add lib/droid_motion.py tests/test_droid_motion.py
git commit -m "feat: restore droid_motion (HC-SR501 Pir) from history, now on GP10

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: config knobs + config tests

**Files:**
- Modify: `config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces (Tasks 4–5 depend on): `config.PIR_PIN = 10`, `config.PIR_WARMUP_S = 60`, `config.MOTION_HOLD_S = 15`.

- [ ] **Step 1: Update the tests first**

In `tests/test_config.py`:

1. In `test_old_device_names_are_gone`, remove `"PIR_PIN", ` from the tuple (the PIR is back). The tuple becomes:

```python
    for name in ("LED_PINS", "TRACK_PASS_VOICE", "TRACK_BEEP",
                 "GREET_NEAR_MM", "FLASH_COUNT", "ALERT_REPEAT_S",
                 "IR_PASS_MAX_MS", "LED_FALLBACK_ON_MS"):
```

2. Append a new test at the end of the file:

```python
def test_motion_knobs():
    assert config.PIR_PIN >= 0
    assert config.PIR_WARMUP_S >= 0
    assert config.MOTION_HOLD_S > 0
    # the gate must outlive the stale window or visitors flicker away
    assert config.MOTION_HOLD_S * 1000 > 2000
```

- [ ] **Step 2: Run tests to verify the new one fails**

Run: `python3 -m pytest tests/test_config.py -v`
Expected: `test_motion_knobs` FAILS with AttributeError (PIR_PIN missing); the rest pass.

- [ ] **Step 3: Add the knobs to config.py**

1. In the `# --- Behavior timing ---` section, after the `PASSING_COOLDOWN_S` line, insert:

```python
MOTION_HOLD_S = 15         # believe the laser this long after the last movement
PIR_WARMUP_S = 60          # PIR settle time after power-on (physics, not a bug)
```

2. In the `# --- Pins ---` section, after the `IR_RECV_PINS` line, insert:

```python
PIR_PIN = 10               # HC-SR501 PIR OUT (motion sensor)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_config.py -v`
Expected: PASS (9 tests).

- [ ] **Step 5: Commit**

```bash
git add config.py tests/test_config.py
git commit -m "feat: config knobs for the motion gate - PIR_PIN, PIR_WARMUP_S, MOTION_HOLD_S

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: the motion gate in lib/visitor.py

**Files:**
- Modify: `lib/visitor.py`
- Test: `tests/test_visitor.py`

**Interfaces:**
- Consumes: `Pir.motion() -> bool` from Task 1 (wrapper only).
- Produces (Task 4 depends on): `VisitorLogic(here_mm, leave_mm, passing_mm, cooldown_ms, motion_hold_ms, samples=5, hold_ms=300, stale_ms=2000)` with `update(mm, moving, now_ms)`; `Visitor(sensor, pir, here_mm, leave_mm, passing_mm, cooldown_ms, motion_hold_ms)` with `update(now_ms)`.

- [ ] **Step 1: Rewrite the test file**

Replace the entire content of `tests/test_visitor.py` with:

```python
from visitor import VisitorLogic, AWAY, PASSING, HERE

S = 1000  # ms per second


def make(**kw):
    """samples=1 + hold_ms=0 so plain logic tests need only two updates
    per reading (first proposes the zone, second accepts it)."""
    args = dict(here_mm=1000, leave_mm=1500, passing_mm=3000,
                cooldown_ms=30 * S, motion_hold_ms=15 * S,
                samples=1, hold_ms=0)
    args.update(kw)
    return VisitorLogic(**args)


def settle(v, mm, t):
    """Feed the same reading twice (with movement) so the zone change is
    accepted; returns the visitor so flag asserts read naturally."""
    v.update(mm, True, t)
    v.update(mm, True, t + 1)
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
    v.update(800, True, 100)            # still standing there
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
    v.update(None, True, 1 * S)         # nothing in sight, not stale yet
    assert v.where == HERE
    v.update(None, True, 4 * S)         # stale: they are gone
    assert v.where == AWAY
    assert v.just_left is True


def test_passing_band_fires_noise_with_cooldown():
    v = make()
    settle(v, 2000, 0)                  # walks into the 1.5-3 m band
    assert v.where == PASSING
    assert v.just_passed is True
    v.update(2000, True, 10 * S)        # still in the band, too soon
    assert v.just_passed is False
    v.update(2000, True, 31 * S)        # cooldown over
    assert v.just_passed is True


def test_beyond_passing_band_is_away():
    v = make()
    settle(v, 3500, 0)
    assert v.where == AWAY
    assert v.just_passed is False


def test_median_ignores_one_wild_reading():
    v = make(samples=5)
    for i, mm in enumerate([800, 800, 4000, 800, 800]):
        v.update(mm, True, i * 100)
    assert v.where == HERE              # the 4000 outlier never wins


def test_hold_time_delays_zone_changes():
    v = make(hold_ms=300)
    v.update(800, True, 0)              # proposes HERE
    v.update(800, True, 100)
    assert v.where == AWAY              # not held long enough yet
    v.update(800, True, 400)
    assert v.where == HERE
    assert v.just_arrived is True


def test_still_object_is_never_a_visitor():
    v = make()
    v.update(800, False, 0)             # something close, but never moving
    v.update(800, False, 1)
    v.update(800, False, 400)
    assert v.where == AWAY
    assert v.just_arrived is False


def test_stopping_moving_fades_to_away_after_hold_plus_stale():
    v = make(stale_ms=2 * S)            # motion_hold_ms=15s from make()
    settle(v, 800, 0)                   # arrives while moving
    left_at = None
    for t in range(2 * S, 20 * S, S):   # then stands perfectly still
        v.update(800, False, t)
        if v.just_left:
            left_at = t
    assert v.where == AWAY
    assert left_at == 18 * S            # ~ hold (15 s) + stale (2 s)


def test_movement_wakes_the_gate_again():
    v = make(stale_ms=2 * S)
    settle(v, 800, 0)
    for t in range(2 * S, 20 * S, S):
        v.update(800, False, t)
    assert v.where == AWAY
    settle(v, 800, 21 * S)              # they wave - back in business
    assert v.where == HERE
    assert v.just_arrived is True


def test_visitor_wrapper_reads_its_own_laser_and_pir():
    from visitor import Visitor

    class FakeLaser:
        """read_mm() falls back to .read() for objects without an i2c."""

        def __init__(self):
            self.mm = 800

        def read(self):
            return self.mm

    class FakePir:
        def __init__(self):
            self.moving = True

        def motion(self):
            return self.moving

    v = Visitor(FakeLaser(), FakePir(), here_mm=1000, leave_mm=1500,
                passing_mm=3000, cooldown_ms=30 * S,
                motion_hold_ms=15 * S)
    # defaults samples=5, hold_ms=300: feed enough ticks to settle
    for t in range(0, 1000, 50):
        v.update(t)
    assert v.where == HERE
```

- [ ] **Step 2: Run tests to verify the new/changed ones fail**

Run: `python3 -m pytest tests/test_visitor.py -v`
Expected: FAIL — `TypeError` on the new `motion_hold_ms` kwarg / 3-arg `update` (current code has the old signatures).

- [ ] **Step 3: Apply the gate to lib/visitor.py**

Four edits:

1. Module docstring — after the paragraph listing the steadiness tricks (ends with `...fade to "away" after stale_ms.`), append a new paragraph:

```
The motion gate: Dino only believes the laser when something warm has
moved within motion_hold_ms (the HC-SR501 PIR supplies the `moving`
flag). With no recent movement, readings are treated as "nothing in
sight" - so a parked bag fades to "away" instead of being greeted over
and over, and anything it triggered self-heals.
```

2. `VisitorLogic.__init__` — new `motion_hold_ms` parameter and two state fields:

```python
    def __init__(self, here_mm, leave_mm, passing_mm, cooldown_ms,
                 motion_hold_ms, samples=5, hold_ms=300, stale_ms=2000):
```

and alongside the existing assignments add:

```python
        self._motion_hold = motion_hold_ms
        self._last_motion = None
```

3. `VisitorLogic.update` — new signature and the gate at the very top (before `was = self.where`):

```python
    def update(self, mm, moving, now_ms):
        """Feed one distance (mm, or None for "nothing in sight") plus
        one "did anything warm move?" flag from the motion sensor."""
        if moving:
            self._last_motion = now_ms
        if (self._last_motion is None or
                ticks_diff(now_ms, self._last_motion) > self._motion_hold):
            mm = None   # nothing warm moved lately: don't believe the laser
        was = self.where
        ...rest of the method body unchanged...
```

4. `Visitor` wrapper — replace the whole class with:

```python
class Visitor(VisitorLogic):
    """VisitorLogic plus the real laser and motion sensor: update(now)
    reads them both for you."""

    def __init__(self, sensor, pir, here_mm, leave_mm, passing_mm,
                 cooldown_ms, motion_hold_ms):
        super().__init__(here_mm, leave_mm, passing_mm, cooldown_ms,
                         motion_hold_ms)
        self._sensor = sensor
        self._pir = pir

    def update(self, now_ms):
        VisitorLogic.update(self, read_mm(self._sensor),
                            self._pir.motion(), now_ms)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_visitor.py -v`
Expected: PASS (14 tests). Note: `main.py` calls the old `Visitor(...)` signature until Task 4 — expected; nothing on desktop imports it.

- [ ] **Step 5: Commit**

```bash
git add lib/visitor.py tests/test_visitor.py
git commit -m "feat: motion gate in visitor - the laser is only believed while something moves

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 4: wire the Pir into main.py

**Files:**
- Modify: `main.py`

**Interfaces:**
- Consumes: `Pir` (Task 1), config knobs (Task 2), new `Visitor` signature (Task 3).

- [ ] **Step 1: Edit main.py (four spots)**

1. Docstring, DINO'S BODY PARTS block — replace the `visitor` line with:

```
  visitor - a laser tape-measure plus a motion sensor: is someone
            away / passing / here? (only MOVING things count)
```

2. Docstring, WIRING block — add after the VL53L1X line:

```
    HC-SR501   VCC -> VBUS (5 V), OUT -> GP10, GND -> GND
               (jumper on H, time-delay pot ~3 s; needs ~60 s warm-up)
```

3. Imports — extend the droid imports:

```python
from droid_motion import Pir
```

(placed with the other `lib` imports, e.g. after `from droid_sense import ...`).

4. Hardware section — replace the current `visitor = Visitor(...)` assignment with:

```python
pir = Pir(pin=config.PIR_PIN, warmup_s=config.PIR_WARMUP_S)
visitor = Visitor(laser, pir, config.HERE_MM, config.LEAVE_MM,
                  config.PASSING_MM, config.PASSING_COOLDOWN_S * 1000,
                  config.MOTION_HOLD_S * 1000)
```

Nothing else changes — SENSE / DECIDE / ACT stay identical.

- [ ] **Step 2: Verify**

Run: `python3 -m py_compile main.py && echo OK` → `OK`
Run: `python3 -m pytest tests/ -q` → 73 passed
Run: `grep -n "GP3\|PIR_PIN = 3" main.py config.py lib/droid_motion.py` → empty

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "feat: wire the PIR into main - visitor now needs movement to engage

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 5: docs + wiring-check example

**Files:**
- Create: `examples/10_test_motion.py`
- Modify: `README.md`, `docs/HARDWARE.md`

- [ ] **Step 1: Create examples/10_test_motion.py**

```python
# Wiring check 10: HC-SR501 PIR motion sensor - after a one-minute
# warm-up, wave your hand: the console shouts MOTION! and the Pico W's
# onboard LED lights until the room has been still for ~3 seconds.
# Wire first (see docs/HARDWARE.md):
#   HC-SR501 VCC -> VBUS (pin 40), OUT -> GP10, GND -> GND.
#   On the module: jumper on H (repeat trigger),
#   time-delay pot fully counter-clockwise (~3 s hold).
# Run: mpremote run examples/10_test_motion.py
import sys
from time import sleep

sys.path.append("/lib")
from machine import Pin

import config
from droid_motion import Pir

pir = Pir(pin=config.PIR_PIN, warmup_s=config.PIR_WARMUP_S)
led = Pin("LED", Pin.OUT)

print("PIR warming up - the sensor needs about a minute to settle.")
seconds = config.PIR_WARMUP_S
while not pir.ready():
    print("\r  warm-up: %2d s left " % seconds, end="")
    sleep(1)
    seconds = max(0, seconds - 1)
print("\nREADY - wave your hand at the sensor!")

count = 0
was_moving = False
while True:
    if pir.motion_started():
        count += 1
        print("MOTION! (#%d)" % count)
    moving = pir.motion()
    if was_moving and not moving:
        print("... quiet again (LED off)")
    led.value(1 if moving else 0)
    was_moving = moving
    sleep(0.05)
```

Before writing it, check how an existing example (e.g. `examples/09_test_laser.py`) imports `config` and lib modules when run via `mpremote run`; if its preamble differs from the above (`sys.path.append("/lib")` + plain `import config`), match the existing pattern instead.

Verify: `python3 -m py_compile examples/10_test_motion.py` → OK.

- [ ] **Step 2: Update README.md (four edits)**

1. Behavior list at the top — add after the "Someone walks by" bullet:

```markdown
- Only *moving* people count: a parked bag or stroller stops mattering
  about 17 s after it stops moving (motion gate).
```

2. Wiring table — add after the `GP6, GP7, GP8` row:

```markdown
| GP10 | HC-SR501 PIR OUT (motion sensor; VCC → VBUS 5 V) |
```

3. Tuning table — add after the `PASSING_COOLDOWN_S` row:

```markdown
| `MOTION_HOLD_S` | believe the laser this long after the last movement | 15 |
```

4. "Check the wiring one piece at a time" block — add:

```markdown
mpremote run examples/10_test_motion.py   # PIR motion sensor
```

Keep everything else as-is. Note the greeter is quiet for the PIR's
~60 s warm-up after power-on — add one sentence to the behavior list
or the deploy section, wherever it reads most naturally.

- [ ] **Step 3: Update docs/HARDWARE.md**

Read the current file first and match its structure. Add the HC-SR501:
1. A device/pin row wherever the other sensors are listed: GP10, `PIR_PIN`, "HC-SR501 PIR OUT input (no internal pull)".
2. A connection/electrical entry with this prose (adapted from the pre-rewrite version of this file):

```
GP10 | HC-SR501 OUT | Push-pull 3.3 V output from the module - no pulls, no series resistor. VCC -> VBUS (5 V), GND -> GND. Jumper on H (repeat trigger), time-delay pot fully counter-clockwise (~3 s). Needs ~60 s warm-up after power-on; keep it away from the Pico W antenna and speaker wires.
```

- [ ] **Step 4: Verify and commit**

Run: `python3 -m pytest tests/ -q` → 73 passed (docs don't affect tests; this is the final green check).

```bash
git add examples/10_test_motion.py README.md docs/HARDWARE.md
git commit -m "docs: PIR wiring, motion-gate behavior, and a motion wiring-check example

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

## Verification (after all tasks)

1. `python3 -m pytest tests/ -q` → 73 passed.
2. `grep -rn "GP3\|pin=3\b" lib/droid_motion.py main.py config.py` → empty.
3. On hardware: `./deploy.sh`, wait out the 60 s warm-up, then: stand still in front of the bin holding a box at ~2 m — after ~17 s the passing noises stop; walk by → noise; approach → greeting; place a bag at 0.5 m and step away → at most one greeting, then silence until the bag is removed; lid behaviors work during warm-up.
