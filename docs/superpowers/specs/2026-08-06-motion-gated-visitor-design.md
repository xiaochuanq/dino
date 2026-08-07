# Motion-gated visitor — HC-SR501 PIR returns as a believe-the-laser gate

> **SUPERSEDED 2026-08-07.** The PIR was removed again: its hardware
> limits (~3 s re-trigger block time, near-blindness to head-on
> approach, 30-60 s warm-up) made detection too slow for the goal of
> reacting to a visitor immediately. The visitor is laser-only again;
> the code lives in git history (and pico-droid) if it's ever wanted.

Design agreed 2026-08-06, follow-up to the kid-friendly parts rewrite
(`2026-08-06-kid-friendly-parts-design.md`).

## Problem

The laser alone cannot tell a person from a parked object. A bag left
1–3 m away fires `just_passed` every cooldown forever; one left inside
1 m gets greeted and then occupies `where == "here"`, blocking every
later greeting. The old robot's PIR motion sensor comes back to fix
this.

## Rule (the kid-sized sentence)

**Dino only believes the laser when something warm has moved in the
last `MOTION_HOLD_S` (15) seconds.**

No recent motion → laser readings are treated as "nothing in sight" →
the visitor fades to `away` through the existing stale-reading path
(firing a normal goodbye if they had been greeted). A parked object
gets at most one greeting, then self-heals in about
`MOTION_HOLD_S + stale` ≈ 17 s. A person standing statue-still that
long gets an early goodbye — accepted trade-off; the HC-SR501 in
repeat-trigger mode re-fires on small fidgets, and the hold time is a
config knob.

## Hardware

HC-SR501 PIR: VCC → VBUS (5 V), OUT → **GP10**, GND → GND. Module
straps: jumper on H (repeat trigger), time-delay pot fully
counter-clockwise (~3 s), sensitivity mid. The sensing element needs
~60 s to settle after power-on (`PIR_WARMUP_S`); during warm-up the
greeter side of Dino is quiet (as in the old robot) while the lid
behaviors work immediately.

New config knobs: `PIR_PIN = 10`, `PIR_WARMUP_S = 60`,
`MOTION_HOLD_S = 15`.

## Architecture

- **`lib/droid_motion.py` restored from commit `0f745c4`** (it already
  follows the Logic/wrapper pattern): `MotionFilter` (pure logic:
  warm-up gating + latched LOW→HIGH edge) + `Pir` (polled pin wrapper
  with injectable pin factory). Two adaptations: default pin and
  docstring wiring change GP3 → GP10. Its desktop tests are ported
  from `../pico-droid/tests/test_droid_motion.py` (same GP10
  adaptation).
- **`lib/visitor.py` gains the gate.** `VisitorLogic.__init__` takes a
  new `motion_hold_ms`; `update(mm, now_ms)` becomes
  `update(mm, moving, now_ms)` with three lines at the top: remember
  `now_ms` when `moving`; if no remembered motion within
  `motion_hold_ms`, force `mm = None`. Everything downstream is
  untouched. `Visitor` (wrapper) takes the `pir` and feeds
  `pir.motion()` in: `Visitor(sensor, pir, here_mm, leave_mm,
  passing_mm, cooldown_ms, motion_hold_ms)`.
- **`main.py`**: two lines in the hardware section (build `Pir`, pass
  it to `Visitor`) plus docstring wiring. SENSE / DECIDE / ACT and all
  five `on_*` handlers unchanged.
- **`examples/10_test_motion.py`**: wiring-check script adapted from
  pico-droid's `14_test_motion.py`, using `config.PIR_PIN` /
  `config.PIR_WARMUP_S`.

## Why mm = None is the right gate

The existing `None` path already does exactly what we want: short
dropouts are forgiven for `stale_ms` (2 s) with `where` frozen;
persistent `None` snaps to `away` (bypassing median buffer and hold
debounce, firing `just_left` if they were here); recovery re-runs the
full arrive pipeline (buffer refill, hold, fresh `just_arrived`).
During the hold window readings are still believed, so `_last_good`
stays fresh and the stale clock only starts when the gate actually
engages — no instant-drop path.

## Testing

- Ported `tests/test_droid_motion.py` (warm-up gating, baseline-not-edge,
  latched edges, pin factory).
- `tests/test_visitor.py`: existing cases pass `moving=True`; new
  cases: a still object never becomes a visitor; a greeted visitor who
  stops moving fades to `away` at hold+stale and fires `just_left`;
  movement re-engages with a fresh greeting; wrapper reads its own
  `pir`.

## Out of scope

- No dead-PIR fallback: the module drives OUT push-pull; if unwired the
  pin floats and behavior is undefined (same as the old robot).
- No changes to lid, voice, eyes, or the DECIDE block.
