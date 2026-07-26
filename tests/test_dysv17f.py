from dysv17f import DYSV17F


class FakeUART:
    def __init__(self):
        self.written = []

    def write(self, data):
        self.written.append(bytes(data))


class FakePin:
    """busy pin returning a scripted sequence of values (last repeats)."""
    def __init__(self, seq):
        self.seq = list(seq)

    def value(self):
        return self.seq.pop(0) if len(self.seq) > 1 else self.seq[0]


def test_frame_checksum_play_track_1():
    # AA 07 02 00 01 -> checksum B4
    assert DYSV17F._frame(0x07, b"\x00\x01") == b"\xaa\x07\x02\x00\x01\xb4"


def test_frame_stop():
    assert DYSV17F._frame(0x04) == b"\xaa\x04\x00\xae"


def test_play_writes_select_and_play_frame():
    uart = FakeUART()
    DYSV17F(uart).play(1)
    assert uart.written == [b"\xaa\x07\x02\x00\x01\xb4"]


def test_play_track_260_splits_high_low_bytes():
    uart = FakeUART()
    DYSV17F(uart).play(260)  # 260 = 0x0104
    frame = uart.written[0]
    assert frame[3:5] == b"\x01\x04"


def test_set_volume_clamps_to_30():
    uart = FakeUART()
    DYSV17F(uart).set_volume(99)
    # AA 13 01 1E -> checksum DC
    assert uart.written == [b"\xaa\x13\x01\x1e\xdc"]


def test_is_busy_respects_polarity():
    high = FakePin([1])
    assert DYSV17F(FakeUART(), busy_pin=high, busy_active=1).is_busy() is True
    assert DYSV17F(FakeUART(), busy_pin=high, busy_active=0).is_busy() is False


def test_is_busy_without_pin_is_false():
    assert DYSV17F(FakeUART()).is_busy() is False


def test_wait_done_polls_until_idle():
    ticks = []
    pin = FakePin([1, 1, 1, 0])
    d = DYSV17F(FakeUART(), busy_pin=pin)
    d.wait_done(timeout_ms=5000, feed=lambda: ticks.append(1))
    assert pin.seq == [0]      # consumed the busy readings
    assert len(ticks) >= 3     # feed called while polling
