# Dino kid-friendly rewrite — visitor/lid/voice/eyes parts + 3-step loop

Design agreed 2026-08-06. Supersedes the motion-sensor (PIR) work: the PIR is
physically removed and all its code goes away.

## Goal

Make Dino's program readable and evolvable by elementary-school kids. Kids
should see objects named after **concepts** — `visitor`, `lid`, `voice`,
`eyes` — never devices (sensors, LEDs, UART, BUSY pins). The main loop follows
a strict 3-step pattern:

1. **SENSE** — each part reads its hardware and updates its state, translating
   device readings into human-meaning states (a distance becomes "someone is
   here"; a blocked beam becomes "the lid is open").
2. **DECIDE** — plain `if` statements turn states into human events and call
   the matching action.
3. **ACT / SHOW** — `on_<human_event>()` functions that kids fill in, plus the
   eyes following the mood.

Event names describe what a *person* did (`on_donation`), never what a sensor
did (`on_beam_blocked`).

## Behaviors

- **Passing** (person 1–3 m away): play a random "noise" track, then a cooldown
  (`PASSING_COOLDOWN_S = 30`) before the next one. The laser stays in
  `"medium"` mode (~2.9 m indoors), so in practice the passing band ends at
  sensor range; `PASSING_MM = 3000` is the configured ceiling.
- **Arriving** (person closes within `HERE_MM` = 1000): random greeting, once
  per visit — no re-greet until they leave.
- **Leaving** (person moves beyond `LEAVE_MM` = 1500 after being here — the
  1000/1500 gap is hysteresis against boundary flapping): random goodbye,
  re-arms the greeting.
- **Donation** (person is here AND lid opens then closes within
  `LID_PUSH_MAX_MS` = 2000): random appreciation. A lid push with nobody
  close is ignored.
- **Full** (beam blocked ≥ `FULL_AFTER_S` = 60): random complaint, repeated
  every `COMPLAIN_EVERY_S` = 10 until the beam clears.
- **Eyes**: two LEDs on one GPIO. Steady glow always; a distinct blink pattern
  (`TALK_BLINK_MS` = 250) while talking. Replaces the old `FlashBurst` alert
  flashing.
- **Sound priority** (two-tier rule kids can state in one sentence): greeting,
  goodbye, and appreciation are *important* — they interrupt whatever is
  playing. Passing noise and complaints are *polite* — skipped if Dino is
  already talking.

## Sounds

Tracks live on the DY-SV17F flash as `00001.wav`, `00002.wav`, … and are
grouped by explicit lists in `config.py` that kids extend:
`PASSING_TRACKS`, `GREETING_TRACKS`, `GOODBYE_TRACKS`, `THANKS_TRACKS`,
`FULL_TRACKS`. Adding a sound = copy a file onto the module + add its number
to one list. Playback picks randomly within the list.

## Pin map

| GP | Role |
|---|---|
| 0 | UART0 TX → DY-SV17F RX |
| 1 | UART0 RX → DY-SV17F TX |
| 2 | DY-SV17F BUSY (CON3) |
| 4 | `EYES_PIN` — two LEDs in parallel, one GPIO |
| 5 | IR emitter |
| 6, 7, 8 | IR receivers 1–3 |
| 14, 15 | I2C **1** SDA / SCL for VL53L1X (`I2C_ID = 1` — GP14/15 are I2C1 on the Pico) |

`PIR_PIN` and `LED_PINS` are deleted.

## Architecture — the four robot parts

Each part is one small file in `lib/`: a **pure-logic class** (desktop-testable,
fed `now` + raw values, like the existing `bin_watch.py`) plus a **thin
hardware wrapper** owning its device. Kids only touch the wrapper's surface.

### lib/visitor.py
- `VisitorLogic` (pure): fed `(mm_or_None, now_ms)`. Median filter + hold time
  (pattern from `ZoneFilter` in `lib/droid_sense.py`), plus arrive/leave
  hysteresis: `where` becomes `"here"` at ≤ `HERE_MM`, returns to
  `"passing"`/`"away"` only at ≥ `LEAVE_MM`; `"passing"` = between `LEAVE_MM`
  and `PASSING_MM`. Stale/no-target readings fail safe to `"away"`.
  One-tick flags after each update: `just_arrived`, `just_left`,
  `just_passed` (respects the cooldown, then resets it).
- `Visitor` (wrapper): owns the VL53L1X via `read_mm`/`set_mode`/`DeadSensor`
  from `droid_sense.py`. `update(now)` + the states/flags above.

### lib/lid.py (adapted from lib/bin_watch.py, which retires)
- `LidLogic` (pure): fed `(beam_seen, now_ms)`. Beam blocked = lid open.
  `is_open`, `just_pushed` (open→closed in under `LID_PUSH_MAX_MS`),
  `is_full` (open ≥ `FULL_AFTER_S`), `complain_due(now)` (once per
  `COMPLAIN_EVERY_S` while full).
- `Lid` (wrapper): owns the `IRBeam` (unchanged), samples it in `update(now)`.

### lib/voice.py
- `VoiceLogic` (pure): the talking state machine currently inlined in
  `main.py` — `quiet` → `starting` (BUSY untrustworthy for `BUSY_ASSERT_MS`
  after play) → `talking` (BUSY seen) → `quiet`; fixed-time fallback if BUSY
  never asserts (`LED_FALLBACK_ON_MS`).
- `Voice` (wrapper): owns `DYSV17F` (unchanged).
  `say_one_of(tracks, important=False)` — random choice; skipped if talking
  unless important (important: stop, 20 ms gap, play). `update(now)`,
  `is_talking`.

### lib/eyes.py
- `Eyes`: owns the GP4 `Pin`. `update(now, talking)` — steady on when quiet,
  square-wave blink at `TALK_BLINK_MS` while talking. No stored state.

### main.py (the page kids read)

```python
# --- ACT: what Dino does. Kids edit these! -------------------
def on_visitor_passing():  voice.say_one_of(config.PASSING_TRACKS)
def on_visitor_arrives():  voice.say_one_of(config.GREETING_TRACKS, important=True)
def on_visitor_leaves():   voice.say_one_of(config.GOODBYE_TRACKS, important=True)
def on_donation():         voice.say_one_of(config.THANKS_TRACKS, important=True)
def on_bin_full():         voice.say_one_of(config.FULL_TRACKS)

while True:
    now = ticks_ms()
    # 1. SENSE
    visitor.update(now); lid.update(now); voice.update(now)
    # 2. DECIDE
    if lid.just_pushed and visitor.where == "here":
        on_donation()                      # money beats a greeting
    elif visitor.just_arrived:
        on_visitor_arrives()
    if visitor.just_left:
        on_visitor_leaves()
    if visitor.just_passed:
        on_visitor_passing()
    if lid.complain_due(now):
        on_bin_full()
    # 3. SHOW
    eyes.update(now, voice.is_talking)
    time.sleep_ms(config.TICK_MS)
```

## State inventory (deliberately tiny)

Visitor: one zone value + a cooldown timestamp. Lid: open/closed + when it
opened + full flag + next complaint time. Voice: quiet/starting/talking +
start time. Eyes: none.

## Error handling

- Laser missing/dead at boot or mid-run → `Visitor` reads as `"away"`:
  greeting/passing/goodbye go quiet, and lid pushes are no longer
  thanked either (a donation needs `visitor.where == "here"`); only
  the full-bin complaint keeps working (`DeadSensor` + stale-reading
  fallback, both existing patterns).
- Sound module missing → BUSY never asserts; `VoiceLogic`'s fixed-time
  fallback keeps the state machine from wedging.

## Testing

Desktop pytest against the pure-logic classes, following existing `tests/`
conventions:
- `test_visitor.py`: arrive/leave hysteresis, no re-greet while hovering,
  passing cooldown, stale-sensor → away.
- `test_lid.py`: push vs full classification, complaint cadence (port the
  relevant `BinWatch` cases).
- `test_voice_logic.py`: quiet→starting→talking transitions, BUSY-never-asserts
  fallback.

## Out of scope

- `examples/` scripts stay as-is (they exercise raw hardware on purpose).
- No changes to `lib/dysv17f.py`, `lib/ir_beam.py`, `lib/vl53l1x.py`.
- `lib/droid_sense.py` stays for `read_mm`/`set_mode`/`DeadSensor`;
  `ZoneFilter`/`Ranger`/`Button` remain available but unused by `main.py`.
