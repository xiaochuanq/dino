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
