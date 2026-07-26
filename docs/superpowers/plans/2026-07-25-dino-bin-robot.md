# Dino Smart Bin Robot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A MicroPython robot on a Raspberry Pi Pico 2/2W that plays a voice + lights LEDs when a spring-loaded door swings shut, and beeps + flashes LEDs when an IR beam-break says the bin is full.

**Architecture:** One plain `while True` loop in `main.py` (no asyncio, no interrupts, no network) drives everything on `ticks_ms()` timestamps. All timing/state rules live in `lib/bin_watch.py` as pure-logic classes (`DoorWatch`, `BinWatch`, `FlashBurst`) testable on desktop CPython. The DY-SV17F sound driver is copied verbatim from the sibling `droid` repo.

**Tech Stack:** MicroPython (Pico 2/2W), DY-SV17F UART sound module, pytest on desktop CPython for logic tests, `mpremote` for deploy.

**Spec:** `docs/superpowers/specs/2026-07-25-dino-bin-robot-design.md`

## Global Constraints

- Target: Raspberry Pi Pico 2 or Pico 2 W, MicroPython. No WiFi/network code.
- Simplicity is a hard requirement (kid project): plain main loop, no `uasyncio`, no IRQs, no hardware Timers.
- Every tunable is a named constant in `config.py` — no magic numbers in `main.py` or `lib/`.
- `lib/dysv17f.py` is COPIED from `/mnt/c/Users/qinx/games/droid/lib/dysv17f.py`, byte-for-byte, not referenced or rewritten.
- `lib/bin_watch.py` must import no hardware modules (`machine`, etc.) — desktop-testable.
- Time comparisons in `lib/bin_watch.py` use `ticks_diff`/`ticks_add` (with CPython fallbacks) so device tick wraparound is safe.
- Desktop tests run with plain `pytest` from the repo root; CPython ≥ 3.9, no dependencies beyond pytest.
- Commit after every task (repo already has git initialized with the spec committed).

---

### Task 1: Project scaffolding + copy the DY-SV17F driver

**Files:**
- Create: `.gitignore`
- Create: `requirements-dev.txt`
- Create: `tests/conftest.py`
- Create: `lib/dysv17f.py` (copy from droid)
- Create: `tests/test_dysv17f.py` (copy from droid)

**Interfaces:**
- Consumes: nothing (first task).
- Produces: `lib/` on `sys.path` for tests (flat imports, same as on the Pico); class `DYSV17F(uart, busy_pin=None, busy_active=1)` with methods `play(track)`, `stop()`, `set_volume(vol)`, `is_busy()`, `wait_done(timeout_ms, feed)` available as `from dysv17f import DYSV17F`.

- [ ] **Step 1: Create `.gitignore`**

```gitignore
__pycache__/
.pytest_cache/
```

- [ ] **Step 2: Create `requirements-dev.txt`**

```text
pytest
```

- [ ] **Step 3: Create `tests/conftest.py`**

```python
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Make lib/ modules importable exactly as they are on the Pico (flat names),
# and the repo root so tests can import config.py.
sys.path.insert(0, str(ROOT / "lib"))
sys.path.insert(0, str(ROOT))
```

- [ ] **Step 4: Copy the driver and its tests from the droid repo**

Run:
```bash
cp /mnt/c/Users/qinx/games/droid/lib/dysv17f.py lib/dysv17f.py
cp /mnt/c/Users/qinx/games/droid/tests/test_dysv17f.py tests/test_dysv17f.py
```

Then verify the copy is identical:
```bash
diff /mnt/c/Users/qinx/games/droid/lib/dysv17f.py lib/dysv17f.py && echo IDENTICAL
```
Expected: `IDENTICAL`

- [ ] **Step 5: Run the copied tests**

Run: `python3 -m pytest tests/ -v`
Expected: all `test_dysv17f.py` tests PASS (8 tests). The driver has a built-in
CPython fallback for `sleep_ms`/`ticks_ms`, so it runs on desktop as-is.

- [ ] **Step 6: Commit**

```bash
git add .gitignore requirements-dev.txt tests/conftest.py lib/dysv17f.py tests/test_dysv17f.py
git commit -m "chore: scaffold project, copy DY-SV17F driver from droid"
```

---

### Task 2: `config.py` — all the tuning knobs

**Files:**
- Create: `config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Consumes: nothing.
- Produces: module `config` with exactly these names (all later tasks import them):
  `IR_CHECK_INTERVAL_S`, `FULL_AFTER_S`, `ALERT_REPEAT_S`, `FLASH_COUNT`,
  `FLASH_MS`, `VOLUME`, `TRACK_DOOR_VOICE`, `TRACK_BEEP`, `UART_ID`,
  `UART_TX_PIN`, `UART_RX_PIN`, `BUSY_PIN`, `TILT_PIN`, `LED_PINS` (list),
  `IR_EMIT_PIN`, `IR_RECV_PIN`, `DOOR_OPEN_VALUE`, `IR_BEAM_SEEN_VALUE`,
  `BUSY_ACTIVE`, `DOOR_DEBOUNCE_MS`, `IR_SETTLE_MS`, `BUSY_ASSERT_MS`,
  `LED_FALLBACK_ON_MS`, `TICK_MS`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_config.py`:

```python
import config


def test_ir_interval_in_allowed_range():
    # Spec: n is a number between 1 and 10 seconds.
    assert 1 <= config.IR_CHECK_INTERVAL_S <= 10


def test_timing_values_positive():
    assert config.FULL_AFTER_S > 0
    assert config.ALERT_REPEAT_S > 0
    assert config.FLASH_COUNT > 0
    assert config.FLASH_MS > 0
    assert config.DOOR_DEBOUNCE_MS > 0
    assert config.TICK_MS > 0
    assert config.BUSY_ASSERT_MS > 0


def test_volume_in_module_range():
    assert 0 <= config.VOLUME <= 30


def test_tracks_are_distinct():
    assert config.TRACK_DOOR_VOICE >= 1
    assert config.TRACK_BEEP >= 1
    assert config.TRACK_DOOR_VOICE != config.TRACK_BEEP


def test_led_pins_is_a_nonempty_list():
    assert isinstance(config.LED_PINS, list)
    assert len(config.LED_PINS) >= 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'config'`

- [ ] **Step 3: Write `config.py`**

```python
"""Dino smart bin robot - every tuning knob lives here.

Change a number, save, redeploy (./deploy.sh) - that's how you tune the robot.
"""

# --- Behavior tuning -------------------------------------------------
IR_CHECK_INTERVAL_S = 5    # ("n") seconds between IR beam checks, 1-10
FULL_AFTER_S = 60          # beam blocked this many seconds -> bin is FULL
ALERT_REPEAT_S = 10        # ("m") seconds between alert bursts while FULL
FLASH_COUNT = 3            # ("k") LED flashes per alert burst
FLASH_MS = 200             # ("j") each flash: on this many ms, off the same

# --- Sound ------------------------------------------------------------
VOLUME = 25                # 0-30
TRACK_DOOR_VOICE = 1       # 00001.wav on the DY-SV17F flash
TRACK_BEEP = 2             # 00002.wav on the DY-SV17F flash

# --- Pins (GP numbers on the Pico) -------------------------------------
UART_ID = 0
UART_TX_PIN = 0            # Pico GP0 (UART0 TX) -> DY-SV17F RX
UART_RX_PIN = 1            # Pico GP1 (UART0 RX) -> DY-SV17F TX
BUSY_PIN = 2               # DY-SV17F BUSY output
TILT_PIN = 3               # tilt switch, other leg to GND (uses pull-up)
LED_PINS = [4]             # one or more LED pins, all switched together
IR_EMIT_PIN = 5            # IR emitter LED (through a resistor)
IR_RECV_PIN = 6            # IR receiver output

# --- Wiring polarity / fine timing --------------------------------------
DOOR_OPEN_VALUE = 1        # tilt pin reads this while the door is OPEN
IR_BEAM_SEEN_VALUE = 0     # receiver pin reads this when the beam is SEEN
BUSY_ACTIVE = 1            # BUSY pin value while a sound is playing
DOOR_DEBOUNCE_MS = 50      # tilt switch debounce time
IR_SETTLE_MS = 5           # emitter-on settle time before reading receiver
BUSY_ASSERT_MS = 300       # after play(), BUSY can't be trusted this long
LED_FALLBACK_ON_MS = 3000  # LED on-time if BUSY never asserts (module missing)
TICK_MS = 50               # main loop tick
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_config.py -v`
Expected: 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add config.py tests/test_config.py
git commit -m "feat: add config.py with all named tuning constants"
```

---

### Task 3: `DoorWatch` — debounced open→shut detection

**Files:**
- Create: `lib/bin_watch.py`
- Test: `tests/test_door_watch.py`

**Interfaces:**
- Consumes: nothing (pure logic).
- Produces, in `lib/bin_watch.py` (imported as `from bin_watch import DoorWatch`):
  - `DoorWatch(open_value: int, debounce_ms: int, initial_raw: int, now_ms: int)`
  - `DoorWatch.closed_event(raw: int, now_ms: int) -> bool` — feed one raw pin
    sample per tick; returns `True` exactly once per debounced open→shut
    transition. Never `True` on shut→open.
  - Module-level `ticks_diff(a, b)` / `ticks_add(a, b)` shims (MicroPython's
    when available, plain `-`/`+` on CPython) that Tasks 4-5 reuse.

- [ ] **Step 1: Write the failing test**

Create `tests/test_door_watch.py`:

```python
from bin_watch import DoorWatch

OPEN, SHUT = 1, 0


def make(now=0):
    return DoorWatch(open_value=OPEN, debounce_ms=50,
                     initial_raw=SHUT, now_ms=now)


def test_no_event_while_door_stays_shut():
    d = make()
    assert d.closed_event(SHUT, 100) is False
    assert d.closed_event(SHUT, 200) is False


def test_open_then_shut_fires_one_event():
    d = make()
    assert d.closed_event(OPEN, 100) is False   # candidate: open
    assert d.closed_event(OPEN, 200) is False   # stable open (no event)
    assert d.closed_event(SHUT, 300) is False   # candidate: shut
    assert d.closed_event(SHUT, 400) is True    # stable shut -> EVENT
    assert d.closed_event(SHUT, 500) is False   # fires only once


def test_opening_alone_fires_no_event():
    d = make()
    d.closed_event(OPEN, 100)
    assert d.closed_event(OPEN, 200) is False


def test_bounce_shorter_than_debounce_is_ignored():
    d = make()
    d.closed_event(OPEN, 100)                   # candidate: open
    assert d.closed_event(OPEN, 120) is False   # only 20ms - not stable yet
    d.closed_event(SHUT, 130)                   # bounced back before 50ms
    assert d.closed_event(SHUT, 300) is False   # never was stably open


def test_two_full_cycles_fire_two_events():
    d = make()
    for raw, t in [(OPEN, 100), (OPEN, 200)]:
        d.closed_event(raw, t)
    assert d.closed_event(SHUT, 300) is False
    assert d.closed_event(SHUT, 400) is True
    for raw, t in [(OPEN, 500), (OPEN, 600)]:
        d.closed_event(raw, t)
    assert d.closed_event(SHUT, 700) is False
    assert d.closed_event(SHUT, 800) is True


def test_boot_with_door_open_fires_on_first_shut():
    d = DoorWatch(open_value=OPEN, debounce_ms=50, initial_raw=OPEN, now_ms=0)
    assert d.closed_event(SHUT, 100) is False   # candidate: shut
    assert d.closed_event(SHUT, 200) is True    # stable shut -> event
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_door_watch.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'bin_watch'`

- [ ] **Step 3: Create `lib/bin_watch.py` with the shims and `DoorWatch`**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_door_watch.py -v`
Expected: 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add lib/bin_watch.py tests/test_door_watch.py
git commit -m "feat: add DoorWatch debounced open->shut detection"
```

---

### Task 4: `BinWatch` — fullness state + burst scheduling

**Files:**
- Modify: `lib/bin_watch.py` (append the class; keep `DoorWatch` untouched)
- Test: `tests/test_bin_watch.py`

**Interfaces:**
- Consumes: `ticks_diff`/`ticks_add` shims from Task 3 (same module).
- Produces, in `lib/bin_watch.py`:
  - `BinWatch(full_after_ms: int, alert_repeat_ms: int, now_ms: int)`
  - `BinWatch.beam_result(seen: bool, now_ms: int) -> None` — feed one IR
    check result.
  - `BinWatch.is_full() -> bool`
  - `BinWatch.burst_due(now_ms: int) -> bool` — `True` at most once per
    `alert_repeat_ms` while full; first burst is due immediately on
    becoming full; consuming a slot schedules the next one (a skipped
    burst simply isn't started by the caller).

- [ ] **Step 1: Write the failing test**

Create `tests/test_bin_watch.py`:

```python
from bin_watch import BinWatch

S = 1000  # ms per second


def make(now=0):
    return BinWatch(full_after_ms=60 * S, alert_repeat_ms=10 * S, now_ms=now)


def test_starts_not_full():
    assert make().is_full() is False


def test_blocked_59s_is_not_full():
    w = make(now=0)
    w.beam_result(False, 59 * S)
    assert w.is_full() is False


def test_blocked_60s_is_full():
    w = make(now=0)
    w.beam_result(False, 60 * S)
    assert w.is_full() is True


def test_beam_seen_resets_the_clock():
    w = make(now=0)
    w.beam_result(True, 30 * S)
    w.beam_result(False, 89 * S)  # only 59s since last seen
    assert w.is_full() is False
    w.beam_result(False, 90 * S)  # 60s since last seen
    assert w.is_full() is True


def test_beam_seen_clears_full_immediately():
    w = make(now=0)
    w.beam_result(False, 60 * S)
    assert w.is_full() is True
    w.beam_result(True, 61 * S)
    assert w.is_full() is False


def test_no_burst_while_normal():
    w = make(now=0)
    assert w.burst_due(30 * S) is False


def test_first_burst_immediate_then_repeats():
    w = make(now=0)
    w.beam_result(False, 60 * S)
    assert w.burst_due(60 * S) is True     # immediately on going full
    assert w.burst_due(60 * S) is False    # slot consumed
    assert w.burst_due(65 * S) is False    # not due yet
    assert w.burst_due(70 * S) is True     # ALERT_REPEAT later
    assert w.burst_due(71 * S) is False


def test_clearing_full_stops_bursts():
    w = make(now=0)
    w.beam_result(False, 60 * S)
    w.burst_due(60 * S)
    w.beam_result(True, 62 * S)
    assert w.burst_due(70 * S) is False


def test_refilling_after_clear_alerts_again():
    w = make(now=0)
    w.beam_result(False, 60 * S)
    w.beam_result(True, 61 * S)            # emptied
    w.beam_result(False, 121 * S)          # blocked again for 60s
    assert w.is_full() is True
    assert w.burst_due(121 * S) is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_bin_watch.py -v`
Expected: FAIL with `ImportError: cannot import name 'BinWatch'`

- [ ] **Step 3: Append `BinWatch` to `lib/bin_watch.py`**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_bin_watch.py -v`
Expected: 9 tests PASS

- [ ] **Step 5: Run the whole suite (no regressions)**

Run: `python3 -m pytest tests/ -v`
Expected: all tests PASS

- [ ] **Step 6: Commit**

```bash
git add lib/bin_watch.py tests/test_bin_watch.py
git commit -m "feat: add BinWatch fullness state machine and burst scheduler"
```

---

### Task 5: `FlashBurst` — non-blocking LED flash pattern

**Files:**
- Modify: `lib/bin_watch.py` (append the class)
- Test: `tests/test_flash_burst.py`

**Interfaces:**
- Consumes: `ticks_diff` shim from Task 3 (same module).
- Produces, in `lib/bin_watch.py`:
  - `FlashBurst(count: int, flash_ms: int)`
  - `FlashBurst.start(now_ms: int) -> None`
  - `FlashBurst.cancel() -> None`
  - `FlashBurst.active() -> bool`
  - `FlashBurst.led_on(now_ms: int) -> bool` — desired LED state right now;
    advances the pattern and self-deactivates after `count` on/off flashes.

- [ ] **Step 1: Write the failing test**

Create `tests/test_flash_burst.py`:

```python
from bin_watch import FlashBurst


def test_inactive_until_started():
    f = FlashBurst(count=3, flash_ms=200)
    assert f.active() is False
    assert f.led_on(0) is False


def test_pattern_alternates_on_off():
    f = FlashBurst(count=2, flash_ms=200)
    f.start(1000)
    assert f.active() is True
    assert f.led_on(1000) is True     # flash 1: on
    assert f.led_on(1199) is True
    assert f.led_on(1200) is False    # flash 1: off-gap
    assert f.led_on(1400) is True     # flash 2: on
    assert f.led_on(1600) is False    # flash 2: off-gap


def test_finishes_after_count_flashes():
    f = FlashBurst(count=2, flash_ms=200)
    f.start(0)
    assert f.led_on(800) is False     # 2 * (200 on + 200 off) elapsed
    assert f.active() is False


def test_cancel_stops_immediately():
    f = FlashBurst(count=3, flash_ms=200)
    f.start(0)
    assert f.led_on(0) is True
    f.cancel()
    assert f.active() is False
    assert f.led_on(50) is False


def test_restart_after_finish_works():
    f = FlashBurst(count=1, flash_ms=100)
    f.start(0)
    assert f.led_on(200) is False     # finished
    f.start(1000)
    assert f.led_on(1000) is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_flash_burst.py -v`
Expected: FAIL with `ImportError: cannot import name 'FlashBurst'`

- [ ] **Step 3: Append `FlashBurst` to `lib/bin_watch.py`**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_flash_burst.py -v`
Expected: 5 tests PASS

- [ ] **Step 5: Run the whole suite**

Run: `python3 -m pytest tests/ -v`
Expected: all tests PASS

- [ ] **Step 6: Commit**

```bash
git add lib/bin_watch.py tests/test_flash_burst.py
git commit -m "feat: add FlashBurst non-blocking LED flash pattern"
```

---

### Task 6: `main.py` — the robot's main loop

**Files:**
- Create: `main.py`

**Interfaces:**
- Consumes: everything from Tasks 2-5 — `config` constants,
  `DYSV17F(uart, busy_pin, busy_active)` / `.play()` / `.stop()` /
  `.set_volume()` / `.is_busy()`,
  `DoorWatch(open_value, debounce_ms, initial_raw, now_ms)` / `.closed_event(raw, now)`,
  `BinWatch(full_after_ms, alert_repeat_ms, now_ms)` / `.beam_result(seen, now)` /
  `.is_full()` / `.burst_due(now)`,
  `FlashBurst(count, flash_ms)` / `.start(now)` / `.cancel()` / `.active()` /
  `.led_on(now)`.
- Produces: the deployable entry point. No desktop test (imports `machine`);
  verified by syntax check here and by the Task 7 example scripts on hardware.

- [ ] **Step 1: Write `main.py`**

```python
"""Dino smart bin robot - main loop.

Door swings shut  -> play the voice track, LEDs on while it plays.
IR beam blocked FULL_AFTER_S -> FULL: beep + LED flashes every
ALERT_REPEAT_S until the beam is seen again.

All tuning knobs are in config.py.
"""
import time
from machine import Pin, UART

import config
from dysv17f import DYSV17F
from bin_watch import BinWatch, DoorWatch, FlashBurst

# --- hardware setup ---------------------------------------------------
uart = UART(config.UART_ID, baudrate=9600,
            tx=Pin(config.UART_TX_PIN), rx=Pin(config.UART_RX_PIN))
busy = Pin(config.BUSY_PIN, Pin.IN)
tilt = Pin(config.TILT_PIN, Pin.IN, Pin.PULL_UP)
leds = [Pin(n, Pin.OUT, value=0) for n in config.LED_PINS]
ir_emit = Pin(config.IR_EMIT_PIN, Pin.OUT, value=0)
ir_recv = Pin(config.IR_RECV_PIN, Pin.IN)

player = DYSV17F(uart, busy_pin=busy, busy_active=config.BUSY_ACTIVE)
player.set_volume(config.VOLUME)


def set_leds(on):
    for led in leds:
        led.value(1 if on else 0)


def beam_seen():
    """Pulse the IR emitter and sample the receiver once."""
    ir_emit.value(1)
    time.sleep_ms(config.IR_SETTLE_MS)
    seen = ir_recv.value() == config.IR_BEAM_SEEN_VALUE
    ir_emit.value(0)
    return seen


# --- state ------------------------------------------------------------
now = time.ticks_ms()
door = DoorWatch(config.DOOR_OPEN_VALUE, config.DOOR_DEBOUNCE_MS,
                 tilt.value(), now)
watch = BinWatch(config.FULL_AFTER_S * 1000,
                 config.ALERT_REPEAT_S * 1000, now)
burst = FlashBurst(config.FLASH_COUNT, config.FLASH_MS)

next_ir_check = now
voice_started = None   # ticks when the door voice started; None = not playing
voice_saw_busy = False

# --- main loop ----------------------------------------------------------
while True:
    now = time.ticks_ms()

    # Door: on open->shut, interrupt whatever is playing, start the voice.
    if door.closed_event(tilt.value(), now):
        burst.cancel()                 # voice takes the LEDs back
        player.stop()
        time.sleep_ms(20)              # brief gap between UART commands
        player.play(config.TRACK_DOOR_VOICE)
        voice_started = now
        voice_saw_busy = False

    # IR fullness check on its own schedule.
    if time.ticks_diff(now, next_ir_check) >= 0:
        next_ir_check = time.ticks_add(now, config.IR_CHECK_INTERVAL_S * 1000)
        watch.beam_result(beam_seen(), now)
        if not watch.is_full():
            burst.cancel()             # bin emptied: stop any running alert

    # Alert burst when due - skipped entirely if a sound is playing, or a
    # door voice was just started (BUSY takes ~200 ms to assert after a
    # play command, so a False BUSY right after play() cannot be trusted).
    if (watch.burst_due(now) and not player.is_busy()
            and voice_started is None):
        player.play(config.TRACK_BEEP)
        burst.start(now)

    # LEDs: burst pattern wins; else follow the door voice; else off.
    if burst.active():
        set_leds(burst.led_on(now))
    elif voice_started is not None:
        if time.ticks_diff(now, voice_started) < config.BUSY_ASSERT_MS:
            set_leds(True)             # BUSY can't be trusted yet after play()
        elif player.is_busy():
            voice_saw_busy = True
            set_leds(True)
        elif voice_saw_busy:
            set_leds(False)            # playback just finished
            voice_started = None
        elif time.ticks_diff(now, voice_started) < config.LED_FALLBACK_ON_MS:
            set_leds(True)             # BUSY never asserted: fixed on-time
        else:
            set_leds(False)
            voice_started = None
    else:
        set_leds(False)

    time.sleep_ms(config.TICK_MS)
```

- [ ] **Step 2: Syntax-check it on desktop**

`main.py` can't run on CPython (`machine` doesn't exist), but it must compile:

Run: `python3 -m py_compile main.py && echo OK`
Expected: `OK`

- [ ] **Step 3: Run the whole test suite (nothing broken)**

Run: `python3 -m pytest tests/ -v`
Expected: all tests PASS

- [ ] **Step 4: Commit**

```bash
git add main.py
git commit -m "feat: add main loop wiring door, fullness, and alert behavior"
```

---

### Task 7: Hardware check scripts in `examples/`

**Files:**
- Create: `examples/01_test_tilt.py`
- Create: `examples/02_test_ir.py`
- Create: `examples/03_test_sound.py`

**Interfaces:**
- Consumes: `config` constants; `DoorWatch` (from Task 3); `DYSV17F` (Task 1).
- Produces: three standalone scripts run on the Pico with
  `mpremote run examples/<name>.py` AFTER `./deploy.sh` has copied `lib/` and
  `config.py` to the device. Each verifies one piece of wiring.

- [ ] **Step 1: Create `examples/01_test_tilt.py`**

```python
"""Wiring check 1: print every tilt change and each debounced door-close.

Deploy first (./deploy.sh), then run:  mpremote run examples/01_test_tilt.py
Open and release the door: you should see raw OPEN/SHUT lines and exactly
one '>>> door closed' per swing. If OPEN/SHUT look inverted, flip
DOOR_OPEN_VALUE in config.py.
"""
import time
from machine import Pin

import config
from bin_watch import DoorWatch

tilt = Pin(config.TILT_PIN, Pin.IN, Pin.PULL_UP)
now = time.ticks_ms()
door = DoorWatch(config.DOOR_OPEN_VALUE, config.DOOR_DEBOUNCE_MS,
                 tilt.value(), now)
last_raw = tilt.value()

print("watching tilt switch on GP%d (Ctrl-C to stop)" % config.TILT_PIN)
while True:
    now = time.ticks_ms()
    raw = tilt.value()
    if raw != last_raw:
        print("raw:", "OPEN" if raw == config.DOOR_OPEN_VALUE else "SHUT")
        last_raw = raw
    if door.closed_event(raw, now):
        print(">>> door closed - the voice would play now")
    time.sleep_ms(10)
```

- [ ] **Step 2: Create `examples/02_test_ir.py`**

```python
"""Wiring check 2: pulse the IR emitter and print the beam state every second.

Deploy first (./deploy.sh), then run:  mpremote run examples/02_test_ir.py
With a clear bin you should see 'beam SEEN'; put your hand in the beam and
it should flip to 'beam BLOCKED'. If it reads inverted, flip
IR_BEAM_SEEN_VALUE in config.py.
"""
import time
from machine import Pin

import config

ir_emit = Pin(config.IR_EMIT_PIN, Pin.OUT, value=0)
ir_recv = Pin(config.IR_RECV_PIN, Pin.IN)

print("beam check once per second (Ctrl-C to stop)")
while True:
    ir_emit.value(1)
    time.sleep_ms(config.IR_SETTLE_MS)
    seen = ir_recv.value() == config.IR_BEAM_SEEN_VALUE
    ir_emit.value(0)
    print("beam SEEN" if seen else "beam BLOCKED")
    time.sleep(1)
```

- [ ] **Step 3: Create `examples/03_test_sound.py`**

```python
"""Wiring check 3: play both tracks; LEDs mirror the BUSY pin.

Deploy first (./deploy.sh), then run:  mpremote run examples/03_test_sound.py
You should hear the door voice then the beep, with LEDs lit during each.
No sound: check UART wiring, CON1/2/3 straps, and that 00001/00002 files
are on the module's flash. LEDs never light: check BUSY_PIN / BUSY_ACTIVE.
"""
import time
from machine import Pin, UART

import config
from dysv17f import DYSV17F

uart = UART(config.UART_ID, baudrate=9600,
            tx=Pin(config.UART_TX_PIN), rx=Pin(config.UART_RX_PIN))
busy = Pin(config.BUSY_PIN, Pin.IN)
leds = [Pin(n, Pin.OUT, value=0) for n in config.LED_PINS]

player = DYSV17F(uart, busy_pin=busy, busy_active=config.BUSY_ACTIVE)
player.set_volume(config.VOLUME)

for track, name in ((config.TRACK_DOOR_VOICE, "door voice"),
                    (config.TRACK_BEEP, "beep")):
    print("playing track %d (%s)..." % (track, name))
    player.play(track)
    time.sleep_ms(300)                 # give BUSY time to assert
    while player.is_busy():
        for led in leds:
            led.value(1)
        time.sleep_ms(50)
    for led in leds:
        led.value(0)
    print("  done")
    time.sleep(1)

print("sound test complete")
```

- [ ] **Step 4: Syntax-check all three**

Run: `python3 -m py_compile examples/01_test_tilt.py examples/02_test_ir.py examples/03_test_sound.py && echo OK`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add examples/
git commit -m "feat: add per-part hardware check scripts"
```

---

### Task 8: `deploy.sh` + `README.md`

**Files:**
- Create: `deploy.sh` (mode 755)
- Create: `README.md`

**Interfaces:**
- Consumes: the file layout from all earlier tasks (`lib/`, `main.py`,
  `config.py`, `examples/`).
- Produces: one-command deploy and the kid-facing documentation.

- [ ] **Step 1: Create `deploy.sh`**

```bash
#!/usr/bin/env bash
# Deploy the Dino bin robot to an attached Pico 2 / 2 W.
set -euo pipefail
cd "$(dirname "$0")"

mpremote cp -r lib :
mpremote cp main.py config.py :
echo "Deployed. main.py runs on next power-up."
echo "Watch it now with:  mpremote repl  (then Ctrl-D to soft-reboot)"
```

Then: `chmod +x deploy.sh`

- [ ] **Step 2: Create `README.md`**

```markdown
# Dino — Smart Bin Robot

A MicroPython robot for a Raspberry Pi Pico 2 / 2 W on a bin with a
spring-loaded door:

- Door swings shut → plays a voice clip, LEDs on while it plays.
- IR beam across the bin blocked for 60 s → bin is FULL → beeps and
  flashes the LEDs until the beam is seen again.

Design spec: `docs/superpowers/specs/2026-07-25-dino-bin-robot-design.md`

## Wiring

| Pico pin | Goes to |
|---|---|
| GP0 (UART0 TX) | DY-SV17F RX |
| GP1 (UART0 RX) | DY-SV17F TX |
| GP2 | DY-SV17F BUSY |
| GP3 | Tilt switch (other leg → GND) |
| GP4 | LED (+ resistor → GND). Add more pins to `LED_PINS` for more LEDs |
| GP5 | IR emitter LED (+ resistor) |
| GP6 | IR receiver output |
| 3V3 / GND | Module + sensor power |

DY-SV17F straps for UART mode: CON1=0, CON2=0, CON3=1. Speaker on the
module's speaker terminals.

## Sounds

Connect the DY-SV17F over its USB port and copy two files onto it:

- `00001.wav` — the door voice ("thank you!")
- `00002.wav` — the full-bin beep

## Tuning (edit `config.py`)

| Constant | What it does | Default |
|---|---|---|
| `IR_CHECK_INTERVAL_S` | seconds between beam checks (1–10) | 5 |
| `FULL_AFTER_S` | beam blocked this long → FULL | 60 |
| `ALERT_REPEAT_S` | seconds between alert bursts | 10 |
| `FLASH_COUNT` | flashes per burst | 3 |
| `FLASH_MS` | each flash: ms on, then ms off | 200 |
| `VOLUME` | loudness 0–30 | 25 |

If a sensor reads backwards, flip `DOOR_OPEN_VALUE` or
`IR_BEAM_SEEN_VALUE`.

## Deploy

```bash
./deploy.sh        # copies lib/, main.py, config.py to the Pico
mpremote repl      # watch it run (Ctrl-D to soft-reboot)
```

## Check the wiring one piece at a time

```bash
mpremote run examples/01_test_tilt.py    # door switch
mpremote run examples/02_test_ir.py      # IR beam
mpremote run examples/03_test_sound.py   # sound + LEDs
```

## Desktop tests (no hardware needed)

```bash
pip install -r requirements-dev.txt
python3 -m pytest tests/ -v
```
```

- [ ] **Step 3: Verify deploy.sh is executable and sane**

Run: `bash -n deploy.sh && test -x deploy.sh && echo OK`
Expected: `OK`

- [ ] **Step 4: Run the full test suite one last time**

Run: `python3 -m pytest tests/ -v`
Expected: all tests PASS (dysv17f 8, config 5, door 5, bin 9, flash 5 = 32)

- [ ] **Step 5: Commit**

```bash
git add deploy.sh README.md
git commit -m "docs: add README and deploy script"
```
