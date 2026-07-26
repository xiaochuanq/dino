from bin_watch import FlashBurst


def test_inactive_until_started():
    f = FlashBurst(count=3, flash_ms=200)
    assert f.active() is False
    assert f.led_on(0) is False


def test_pattern_alternates_on_off():
    f = FlashBurst(count=2, flash_ms=200)
    f.start(1000)
    assert f.active() is True
    assert f.led_on(1000) is True     # flash 1: on
    assert f.led_on(1199) is True
    assert f.led_on(1200) is False    # flash 1: off-gap
    assert f.led_on(1400) is True     # flash 2: on
    assert f.led_on(1600) is False    # flash 2: off-gap


def test_finishes_after_count_flashes():
    f = FlashBurst(count=2, flash_ms=200)
    f.start(0)
    assert f.led_on(800) is False     # 2 * (200 on + 200 off) elapsed
    assert f.active() is False


def test_cancel_stops_immediately():
    f = FlashBurst(count=3, flash_ms=200)
    f.start(0)
    assert f.led_on(0) is True
    f.cancel()
    assert f.active() is False
    assert f.led_on(50) is False


def test_restart_after_finish_works():
    f = FlashBurst(count=1, flash_ms=100)
    f.start(0)
    assert f.led_on(200) is False     # finished
    f.start(1000)
    assert f.led_on(1000) is True
