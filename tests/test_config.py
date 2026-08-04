import config


def test_timing_values_positive():
    assert config.FULL_AFTER_S > 0
    assert config.ALERT_REPEAT_S > 0
    assert config.FLASH_COUNT > 0
    assert config.FLASH_MS > 0
    assert config.IR_PASS_MAX_MS > 0
    assert config.TICK_MS > 0
    assert config.BUSY_ASSERT_MS > 0
    assert config.IR_SAMPLE_COUNT > 0
    assert config.IR_SAMPLE_COUNT % 2 == 1
    assert config.IR_SAMPLE_GAP_US >= 0


def test_pass_window_shorter_than_full_threshold():
    # A "drop-through" must be classified long before the FULL timer fires.
    assert config.IR_PASS_MAX_MS < config.FULL_AFTER_S * 1000


def test_pass_window_spans_several_ticks():
    # Pass detection samples once per tick; the window must cover a few.
    assert config.IR_PASS_MAX_MS >= 2 * config.TICK_MS


def test_volume_in_module_range():
    assert 0 <= config.VOLUME <= 30


def test_tracks_are_distinct():
    assert config.TRACK_PASS_VOICE >= 1
    assert config.TRACK_BEEP >= 1
    assert config.TRACK_PASS_VOICE != config.TRACK_BEEP


def test_led_pins_is_a_nonempty_list():
    assert isinstance(config.LED_PINS, list)
    assert len(config.LED_PINS) >= 1
