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
