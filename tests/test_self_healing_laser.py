from droid_sense import SelfHealingLaser

S = 1000  # ms per second


class FlakySensor:
    """Scripted laser stand-in: .read() returns the next scripted value.
    "dead" raises OSError - exactly what a wedged I2C bus does, which
    read_mm() turns into None."""

    def __init__(self, values):
        self.values = list(values)

    def read(self):
        value = self.values.pop(0) if self.values else None
        if value == "dead":
            raise OSError("bus gone")
        return value


class Factory:
    """Scripted build function: each call consumes one plan entry -
    a FlakySensor to hand out, or "fail" to raise (no sensor on the bus)."""

    def __init__(self, plan):
        self.plan = list(plan)
        self.builds = 0

    def __call__(self):
        self.builds += 1
        step = self.plan.pop(0) if self.plan else "fail"
        if step == "fail":
            raise OSError("no sensor on the bus")
        return step


def test_builds_on_first_use_and_reads():
    factory = Factory([FlakySensor([500, 600])])
    laser = SelfHealingLaser(factory)
    assert laser.mm(0) == 500
    assert laser.mm(50) == 600
    assert factory.builds == 1


def test_boot_failure_reads_none_then_retries_later():
    factory = Factory(["fail", FlakySensor([700])])
    laser = SelfHealingLaser(factory, heal_after_ms=10 * S,
                             retry_every_ms=10 * S)
    assert laser.mm(0) is None          # nothing on the bus at boot
    assert laser.mm(5 * S) is None      # too soon to try again
    assert factory.builds == 1
    assert laser.mm(10 * S) == 700      # retry window open: rebuilt, alive
    assert factory.builds == 2


def test_short_quiet_spell_is_not_a_failure():
    factory = Factory([FlakySensor([500, None, None, None, 800])])
    laser = SelfHealingLaser(factory, heal_after_ms=10 * S)
    assert laser.mm(0) == 500
    assert laser.mm(2 * S) is None      # nobody in range - normal
    assert laser.mm(4 * S) is None
    assert laser.mm(6 * S) is None
    assert laser.mm(8 * S) == 800       # they came back
    assert factory.builds == 1          # never rebuilt


def test_long_silence_rebuilds_the_sensor():
    factory = Factory([FlakySensor([500, "dead", "dead", "dead"]),
                       FlakySensor([650])])
    laser = SelfHealingLaser(factory, heal_after_ms=10 * S,
                             retry_every_ms=5 * S)
    assert laser.mm(0) == 500
    assert laser.mm(4 * S) is None       # silence begins
    assert laser.mm(8 * S) is None       # not silent long enough yet
    assert factory.builds == 1
    assert laser.mm(14 * S) is None      # 10 s of silence: rebuilds now
    assert factory.builds == 2
    assert laser.mm(14 * S + 50) == 650  # next tick reads the new sensor


def test_rebuild_attempts_are_throttled():
    factory = Factory([FlakySensor([500, "dead"]), "fail", "fail"])
    laser = SelfHealingLaser(factory, heal_after_ms=4 * S,
                             retry_every_ms=10 * S)
    assert laser.mm(0) == 500
    for t in range(1 * S, 21 * S, S):    # dead sensor, ticking every second
        laser.mm(t)
    # one build at boot, then retries only at t=10 s and t=20 s
    assert factory.builds == 3
