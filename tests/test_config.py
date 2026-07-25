import config


def test_ir_interval_in_allowed_range():
    # Spec: n is a number between 1 and 10 seconds.
    assert 1 <= config.IR_CHECK_INTERVAL_S <= 10


def test_timing_values_positive():
    assert config.FULL_AFTER_S > 0
    assert config.ALERT_REPEAT_S > 0
    assert config.FLASH_COUNT > 0
    assert config.FLASH_MS > 0
    assert config.DOOR_DEBOUNCE_MS > 0
    assert config.TICK_MS > 0


def test_volume_in_module_range():
    assert 0 <= config.VOLUME <= 30


def test_tracks_are_distinct():
    assert config.TRACK_DOOR_VOICE >= 1
    assert config.TRACK_BEEP >= 1
    assert config.TRACK_DOOR_VOICE != config.TRACK_BEEP


def test_led_pins_is_a_nonempty_list():
    assert isinstance(config.LED_PINS, list)
    assert len(config.LED_PINS) >= 1
