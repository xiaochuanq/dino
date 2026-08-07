from ir_beam import IRBeam


class FakePin:
    def __init__(self):
        self.v = 0

    def value(self, x=None):
        if x is None:
            return self.v
        self.v = x


def test_bare_pin_is_wrapped_into_a_list():
    beam = IRBeam(FakePin(), FakePin())
    assert len(beam._receivers) == 1


def test_single_element_list_is_not_double_wrapped():
    receiver = FakePin()
    beam = IRBeam(FakePin(), [receiver])
    assert beam._receivers == [receiver]


def test_multi_receiver_list_is_kept():
    receivers = [FakePin(), FakePin(), FakePin()]
    beam = IRBeam(FakePin(), receivers)
    assert beam._receivers == receivers
