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
