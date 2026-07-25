# Dino — Smart Bin Robot (Design)

Date: 2026-07-25
Status: Approved design, pending implementation plan

## Overview

"Dino" (project ID only, no meaning) is a simple MicroPython robot for a
Raspberry Pi Pico 2 or Pico 2 W, built as a kid project. It lives on a
container with a spring-loaded, self-shutting door:

1. When the door is opened and swings back shut, the robot plays a
   pre-recorded voice clip and lights its LEDs for the duration of playback.
2. An IR beam across the container interior detects fullness (beam-break).
   When the beam has been blocked continuously for a timeout, the robot
   enters a FULL state and periodically flashes its LEDs and plays a beep
   until the beam is seen again.

Simplicity is a hard requirement: plain main loop, no asyncio, no
interrupts, no networking. All tunables are named constants in one file.

## Hardware

| Part | Connection | Notes |
|---|---|---|
| Raspberry Pi Pico 2 / 2 W | — | No WiFi used; identical code on both |
| Tilt switch | GPIO input, internal pull-up | Door position sensor; software debounce ~50 ms |
| DY-SV17F voice module | UART0 @ 9600 baud (TX/RX) + BUSY pin on GPIO input | Wired for UART control (CON1=0, CON2=0, CON3=1). Tracks stored on module flash: `00001` = door voice, `00002` = beep |
| LEDs | One or more GPIO outputs (each with resistor) | All driven together as a single logical channel |
| IR emitter | GPIO output | On only during each measurement pulse |
| IR receiver | GPIO input | Faces the emitter across the bin (beam-break) |

All pin assignments are constants in `config.py`.

## Configuration (`config.py`)

The user-facing tuning file. Every behavior parameter is a named constant:

| Original letter | Constant | Meaning | Default |
|---|---|---|---|
| n | `IR_CHECK_INTERVAL_S` | Seconds between IR beam checks (1–10) | 5 |
| — | `FULL_AFTER_S` | Continuous beam-blocked seconds before FULL | 60 |
| m | `ALERT_REPEAT_S` | Seconds between alert bursts while FULL | 10 |
| k | `FLASH_COUNT` | Flashes per alert burst | 3 |
| j | `FLASH_MS` | Each flash: on this many ms, then off the same | 200 |

Also in `config.py`: pin numbers, `VOLUME` (0–30), `TRACK_DOOR_VOICE = 1`,
`TRACK_BEEP = 2`, `DOOR_DEBOUNCE_MS = 50`, `BUSY_ASSERT_MS = 300`,
`LED_FALLBACK_ON_MS = 3000`, and the input polarity constants
(`DOOR_OPEN_VALUE`, `IR_BEAM_SEEN_VALUE`) so the code adapts to how the
switch and receiver are wired.

## Behavior

Single `while True` loop in `main.py`, ticking every ~50 ms, scheduling
everything with `time.ticks_ms()` timestamps. No interrupts, no timers,
no asyncio.

### Door (voice + LEDs)

- The tilt switch is read every tick and debounced (`DOOR_DEBOUNCE_MS`).
- On the **open → shut** transition (door swings back closed), play
  `TRACK_DOOR_VOICE`. Playback is NOT triggered on door open.
- A door-close event **always interrupts any current playback**: the code
  calls `stop()` then `play(TRACK_DOOR_VOICE)`, so a rapid second
  open/close cuts off the previous voice (or a beep) and restarts the
  voice from the beginning.
- LEDs turn on when playback starts and stay on while the DY-SV17F BUSY
  pin reports playing, then turn off. Because LEDs simply follow BUSY,
  a playback restart keeps them lit with no extra logic. If BUSY never
  asserts (module missing/miswired), LEDs fall back to
  `LED_FALLBACK_ON_MS` on-time. LEDs are held on for the first
  `BUSY_ASSERT_MS` after a play command, because the DY-SV17F's BUSY pin
  cannot be trusted during its ~200 ms assertion latency (this also
  prevents a stale BUSY reading from an interrupted previous track).

### Fullness detection (IR beam-break)

- Every `IR_CHECK_INTERVAL_S`: turn the IR emitter on, read the receiver,
  turn the emitter off. Record the timestamp whenever the beam is seen.
- If the beam has not been seen for `FULL_AFTER_S` continuous seconds,
  state becomes **FULL**.
- The moment any check sees the beam again, state returns to **NORMAL**
  immediately (auto-clear, no debounce) and any running alert stops.

### Full alert

- While FULL, every `ALERT_REPEAT_S` seconds run one **burst**:
  - Play `TRACK_BEEP`.
  - Flash the LEDs `FLASH_COUNT` times: `FLASH_MS` on, `FLASH_MS` off each.
- Flashes are advanced by the main loop using timestamps (non-blocking),
  so the door keeps being polled during a burst.
- Shared-speaker priority (highest first): (1) a new door-close voice
  overrides anything already playing — a previous voice or a beep;
  (2) the door voice is never interrupted by a beep. A due beep is skipped
  when the module is busy playing OR when a voice was just started and the
  BUSY pin has not asserted yet (the DY-SV17F takes ~200 ms to raise BUSY
  after a play command — the beep gate must not trust a False BUSY during
  that window). Beeps repeat every burst, so a skipped beep simply
  postpones to the next one. Door open/close works normally while FULL.
- **LED ownership rule:** exactly one mode drives the LEDs at a time.
  During an alert burst the flash pattern owns them (the beep's BUSY
  signal is ignored for LEDs). When a door-close fires, any burst in
  progress is cancelled and the LEDs switch to following BUSY for the
  voice. When neither is active, LEDs are off.

## Architecture & files

Structure mirrors the sibling `droid` repo (`lib/` drivers, desktop tests,
examples):

```
dino/
├── config.py            # all named constants — the tuning file
├── main.py              # hardware setup + main loop (thin glue)
├── lib/
│   ├── dysv17f.py       # COPIED verbatim from ../droid/lib/dysv17f.py
│   └── bin_watch.py     # pure timing/state logic, no hardware imports
├── examples/
│   ├── 01_test_tilt.py  # print door open/shut transitions
│   ├── 02_test_ir.py    # print beam seen/blocked each check
│   └── 03_test_sound.py # play both tracks, exercise BUSY/LED follow
├── tests/               # desktop pytest for bin_watch.py
└── README.md            # wiring guide + tuning instructions
```

### `lib/bin_watch.py` — the testable core

A small class holding the fullness state machine and alert scheduler.
It takes timestamps as arguments (injected clock, same pattern as
`dysv17f.py`'s CPython fallback) and returns simple decisions:

- `beam_result(seen: bool, now_ms)` → updates last-seen time and state.
- `is_full()` → current state.
- `burst_due(now_ms)` → True when an alert burst should start.

`main.py` owns all `machine.Pin`/`machine.UART` objects and translates
`bin_watch` decisions into hardware actions. This keeps every timing rule
testable on a desktop with a fake clock.

### `lib/dysv17f.py`

Copied (not referenced) from `/mnt/c/Users/qinx/games/droid/lib/dysv17f.py`.
Already self-contained with a CPython fallback for tests. Used as-is:
`play(track)`, `stop()`, `set_volume(vol)`, `is_busy()`.

## Error handling

- DY-SV17F absent or miswired: `play()` writes to UART and returns; nothing
  blocks or crashes. LEDs use the `LED_FALLBACK_ON_MS` fallback when BUSY
  never asserts.
- Tilt switch bounce: handled by `DOOR_DEBOUNCE_MS` software debounce.
- The main loop never blocks: flash bursts and LED timing are driven by
  timestamps, and there are no operations that can hang it (no network,
  no waits on external input).

## Testing

- **Desktop (pytest, CPython):** `tests/test_bin_watch.py` covers the
  timing rules — beam blocked 59 s → not full; 60 s → full; beam restored
  → immediately normal; bursts due every `ALERT_REPEAT_S` while full and
  never while normal.
- **On device (manual):** the three `examples/` scripts verify each piece
  of wiring independently (tilt, IR pair, sound+LED) before running
  `main.py`.

## Out of scope (YAGNI)

- WiFi/network features, logging, buttons, displays.
- Queueing or prioritizing multiple sounds beyond the interrupt/skip rules
  above.
- Fill-level percentage — fullness is binary.
- NeoPixels or per-LED control — one logical LED channel only.
