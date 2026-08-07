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
    assert left_at == 18 * S            # hold (15 s) + stale (2 s) + the
    # extra 1 s comes from this test's 1 s stepping, not the logic; at the
    # robot's real 50 ms tick the fade lands at ~17.05 s.


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

    pir = FakePir()
    v = Visitor(FakeLaser(), pir, here_mm=1000, leave_mm=1500,
                passing_mm=3000, cooldown_ms=30 * S,
                motion_hold_ms=15 * S)
    # defaults samples=5, hold_ms=300: feed enough ticks to settle
    for t in range(0, 1000, 50):
        v.update(t)
    assert v.where == HERE

    # Now flip the PIR seam off: with nothing warm moving, Visitor.update
    # must stop trusting the laser, and the visitor fades to AWAY once
    # motion_hold_ms (15 s) + stale_ms (2 s, the VisitorLogic default) has
    # passed. If Visitor.update ever hardcoded the moving flag to True,
    # this half would fail (where would stay HERE forever).
    pir.moving = False
    for t in range(1000, 20 * S, 50):
        v.update(t)
    assert v.where == AWAY

    # And flip it back on: with motion resuming, the laser is trusted
    # again and the visitor comes back to HERE. If Visitor.update ever
    # hardcoded the moving flag to False, this half would fail (where
    # would stay AWAY forever).
    pir.moving = True
    for t in range(20 * S, 21 * S, 50):
        v.update(t)
    assert v.where == HERE
