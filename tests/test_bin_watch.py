from bin_watch import BinWatch

S = 1000  # ms per second


def make(now=0):
    return BinWatch(full_after_ms=60 * S, alert_repeat_ms=10 * S,
                    pass_max_ms=2 * S, now_ms=now)


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


# --- pass detection (something dropped through the beam) ----------------

def test_short_block_then_clear_is_a_pass():
    w = make(now=0)
    assert w.beam_result(False, 10 * S) is False        # block starts
    assert w.beam_result(True, 10 * S + 300) is True    # cleared fast: PASS


def test_pass_fires_only_once_per_block():
    w = make(now=0)
    w.beam_result(False, 10 * S)
    assert w.beam_result(True, 10 * S + 300) is True
    assert w.beam_result(True, 10 * S + 400) is False   # still clear: no event


def test_steady_beam_is_never_a_pass():
    w = make(now=0)
    assert w.beam_result(True, 1 * S) is False
    assert w.beam_result(True, 2 * S) is False


def test_block_at_pass_max_is_not_a_pass():
    w = make(now=0)
    w.beam_result(False, 10 * S)
    assert w.beam_result(True, 12 * S) is False          # exactly 2s: too long


def test_long_block_then_clear_is_not_a_pass():
    w = make(now=0)
    w.beam_result(False, 10 * S)                         # e.g. hand hovering
    w.beam_result(False, 40 * S)
    assert w.beam_result(True, 40 * S + 100) is False


def test_full_clearing_is_not_a_pass():
    w = make(now=0)
    w.beam_result(False, 60 * S)                         # full
    assert w.beam_result(True, 61 * S) is False          # emptied, no voice


def test_multiple_samples_inside_one_block_still_one_pass():
    w = make(now=0)
    assert w.beam_result(False, 10 * S) is False
    assert w.beam_result(False, 10 * S + 100) is False
    assert w.beam_result(False, 10 * S + 200) is False
    assert w.beam_result(True, 10 * S + 300) is True


def test_two_drops_fire_two_passes():
    w = make(now=0)
    w.beam_result(False, 10 * S)
    assert w.beam_result(True, 10 * S + 200) is True
    w.beam_result(False, 20 * S)
    assert w.beam_result(True, 20 * S + 200) is True
