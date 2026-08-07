from droid_motion import MotionFilter

T0 = 1000


def test_not_ready_before_first_update():
    f = MotionFilter()
    assert f.ready() is False
    assert f.motion() is False
    assert f.motion_started() is False


def test_warmup_suppresses_motion_and_edges():
    f = MotionFilter(warmup_ms=60_000)
    f.update(1, T0)                       # first update stamps t0
    f.update(0, T0 + 30_000)
    f.update(1, T0 + 40_000)              # a "rise", but still warming up
    assert f.ready() is False
    assert f.motion() is False
    assert f.motion_started() is False


def test_ready_after_warmup_elapses():
    f = MotionFilter(warmup_ms=60_000)
    f.update(0, T0)
    assert f.ready() is False
    f.update(0, T0 + 60_000)
    assert f.ready() is True


def test_high_at_warmup_end_is_baseline_not_edge():
    f = MotionFilter(warmup_ms=60_000)
    f.update(1, T0)
    f.update(1, T0 + 60_000)              # warm-up ends with level HIGH
    assert f.motion() is True             # live state is reported...
    assert f.motion_started() is False    # ...but it is not a fresh edge
    f.update(0, T0 + 61_000)
    f.update(1, T0 + 62_000)              # a REAL LOW->HIGH after warm-up
    assert f.motion_started() is True


def test_edge_latches_until_read_then_clears():
    f = MotionFilter(warmup_ms=0)
    f.update(0, T0)
    f.update(1, T0 + 10)                  # rising edge
    f.update(1, T0 + 20)                  # slow loop keeps polling...
    f.update(1, T0 + 30)
    assert f.motion_started() is True     # ...the event was not lost
    assert f.motion_started() is False    # cleared by the read
    f.update(1, T0 + 40)                  # held HIGH: no re-fire
    assert f.motion_started() is False


def test_falling_edge_is_not_a_start():
    f = MotionFilter(warmup_ms=0)
    f.update(0, T0)
    f.update(1, T0 + 10)
    f.motion_started()                    # consume the rise
    f.update(0, T0 + 20)
    assert f.motion_started() is False
    assert f.motion() is False


def test_zero_warmup_is_live_immediately():
    f = MotionFilter(warmup_ms=0)
    f.update(1, T0)
    assert f.ready() is True
    assert f.motion() is True             # baseline HIGH, live at once
    assert f.motion_started() is False    # but no invented edge


def test_custom_diff_is_used():
    calls = []

    def diff(a, b):
        calls.append((a, b))
        return a - b

    f = MotionFilter(warmup_ms=10, diff=diff)
    f.update(0, T0)
    assert calls                          # warm-up math used the injection


from droid_motion import Pir


# ---- FakePin: an INPUT pin whose level the test sets directly ----

class FakePin:
    def __init__(self, gp):
        self.gp = gp
        self.level = 0

    def value(self):
        return self.level


def make_pir(**kwargs):
    made = {}

    def factory(gp):
        made["pin"] = FakePin(gp)
        return made["pin"]

    return Pir(pin_factory=factory, **kwargs), made


def test_default_pin_is_gp10():
    _, made = make_pir()
    assert made["pin"].gp == 10


def test_custom_pin_reaches_the_factory():
    _, made = make_pir(pin=19)
    assert made["pin"].gp == 19


def test_default_warmup_gates_motion():
    pir, made = make_pir()                # warmup_s=60, real shim clock
    made["pin"].level = 1
    assert pir.ready() is False           # first poll just stamps t0
    assert pir.motion() is False          # gated for a minute


def test_zero_warmup_motion_follows_the_pin():
    pir, made = make_pir(warmup_s=0)
    assert pir.ready() is True
    assert pir.motion() is False
    made["pin"].level = 1
    assert pir.motion() is True
    assert pir.motion_started() is True   # the rise was latched
    assert pir.motion_started() is False  # and clears on read
    made["pin"].level = 0
    assert pir.motion() is False
