import config


def test_track_lists_nonempty():
    for tracks in (config.PASSING_TRACKS, config.GREETING_TRACKS,
                   config.ASK_HELP_TRACKS, config.POST_EATING_TRACKS,
                   config.THANKS_TRACKS, config.GOODBYE_TRACKS,
                   config.CHOKE_TRACKS):
        assert isinstance(tracks, list)
        assert len(tracks) >= 1
        assert all(isinstance(t, int) and t >= 1 for t in tracks)


def test_distances_are_ordered():
    # here < leave gives the hysteresis gap; leave < passing gives the band
    assert 0 < config.HERE_MM < config.LEAVE_MM < config.PASSING_MM


def test_push_window_shorter_than_full_threshold():
    assert config.LID_PUSH_MAX_MS < config.FULL_AFTER_S * 1000


def test_push_window_spans_several_ticks():
    assert config.LID_PUSH_MAX_MS >= 2 * config.TICK_MS


def test_timing_values_positive():
    assert config.FULL_AFTER_S > 0
    assert config.COMPLAIN_EVERY_S > 0
    assert config.PASSING_COOLDOWN_S > 0
    assert config.TALK_BLINK_MS > 0
    assert config.TICK_MS > 0
    assert config.BUSY_ASSERT_MS > 0
    assert config.TALK_FALLBACK_MS > config.BUSY_ASSERT_MS
    assert config.IR_SAMPLE_COUNT > 0
    assert config.IR_SAMPLE_COUNT % 2 == 1
    assert config.IR_SAMPLE_GAP_US >= 0


def test_volume_in_module_range():
    assert 0 <= config.VOLUME <= 30


def test_ir_receiver_pins_listed():
    assert isinstance(config.IR_RECV_PINS, list)
    assert len(config.IR_RECV_PINS) >= 1


def test_old_device_names_are_gone():
    for name in ("LED_PINS", "TRACK_PASS_VOICE", "TRACK_BEEP",
                 "GREET_NEAR_MM", "FLASH_COUNT", "ALERT_REPEAT_S",
                 "IR_PASS_MAX_MS", "LED_FALLBACK_ON_MS"):
        assert not hasattr(config, name)


def test_motion_knobs():
    import inspect
    from visitor import VisitorLogic

    assert config.PIR_PIN >= 0
    assert config.PIR_WARMUP_S >= 0
    assert config.MOTION_HOLD_S > 0
    # the gate must outlive the stale window or visitors flicker away
    stale_default = inspect.signature(
        VisitorLogic.__init__).parameters["stale_ms"].default
    assert config.MOTION_HOLD_S * 1000 > stale_default
