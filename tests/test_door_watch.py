from bin_watch import DoorWatch

OPEN, SHUT = 1, 0


def make(now=0):
    return DoorWatch(open_value=OPEN, debounce_ms=50,
                     initial_raw=SHUT, now_ms=now)


def test_no_event_while_door_stays_shut():
    d = make()
    assert d.closed_event(SHUT, 100) is False
    assert d.closed_event(SHUT, 200) is False


def test_open_then_shut_fires_one_event():
    d = make()
    assert d.closed_event(OPEN, 100) is False   # candidate: open
    assert d.closed_event(OPEN, 200) is False   # stable open (no event)
    assert d.closed_event(SHUT, 300) is False   # candidate: shut
    assert d.closed_event(SHUT, 400) is True    # stable shut -> EVENT
    assert d.closed_event(SHUT, 500) is False   # fires only once


def test_opening_alone_fires_no_event():
    d = make()
    d.closed_event(OPEN, 100)
    assert d.closed_event(OPEN, 200) is False


def test_bounce_shorter_than_debounce_is_ignored():
    d = make()
    d.closed_event(OPEN, 100)                   # candidate: open
    assert d.closed_event(OPEN, 120) is False   # only 20ms - not stable yet
    d.closed_event(SHUT, 130)                   # bounced back before 50ms
    assert d.closed_event(SHUT, 300) is False   # never was stably open


def test_two_full_cycles_fire_two_events():
    d = make()
    for raw, t in [(OPEN, 100), (OPEN, 200)]:
        d.closed_event(raw, t)
    assert d.closed_event(SHUT, 300) is False
    assert d.closed_event(SHUT, 400) is True
    for raw, t in [(OPEN, 500), (OPEN, 600)]:
        d.closed_event(raw, t)
    assert d.closed_event(SHUT, 700) is False
    assert d.closed_event(SHUT, 800) is True


def test_boot_with_door_open_fires_on_first_shut():
    d = DoorWatch(open_value=OPEN, debounce_ms=50, initial_raw=OPEN, now_ms=0)
    assert d.closed_event(SHUT, 100) is False   # candidate: shut
    assert d.closed_event(SHUT, 200) is True    # stable shut -> event
