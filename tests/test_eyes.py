from eyes import Eyes


class FakePin:
    def __init__(self):
        self.v = None

    def value(self, x):
        self.v = x


def test_steady_glow_when_quiet():
    pin = FakePin()
    eyes = Eyes(pin, blink_ms=250)
    eyes.update(0, talking=False)
    assert pin.v == 1
    eyes.update(12345, talking=False)
    assert pin.v == 1


def test_blinks_while_talking():
    pin = FakePin()
    eyes = Eyes(pin, blink_ms=250)
    eyes.update(0, talking=True)
    first = pin.v
    eyes.update(250, talking=True)      # next blink phase
    assert pin.v != first
    eyes.update(500, talking=True)      # and back
    assert pin.v == first


def test_glow_returns_after_talking():
    pin = FakePin()
    eyes = Eyes(pin, blink_ms=250)
    eyes.update(250, talking=True)
    eyes.update(300, talking=False)
    assert pin.v == 1
