from voice import VoiceLogic, Voice, ticks_ms


def make():
    return VoiceLogic(busy_assert_ms=300, fallback_ms=3000)


def test_quiet_at_start():
    v = make()
    assert v.update(False, 0) is False


def test_trusts_the_clock_right_after_play():
    v = make()
    v.started(1000)
    # BUSY hasn't woken up yet - Dino is still talking
    assert v.update(False, 1100) is True


def test_busy_keeps_talking_then_release_ends_it():
    v = make()
    v.started(0)
    assert v.update(True, 400) is True
    assert v.update(True, 2000) is True
    assert v.update(False, 2500) is False


def test_fallback_when_busy_never_asserts():
    v = make()
    v.started(0)
    assert v.update(False, 400) is True      # module missing? assume talking
    assert v.update(False, 2999) is True
    assert v.update(False, 3000) is False    # ...but not forever


def test_long_talk_outlasts_fallback_once_busy_seen():
    v = make()
    v.started(0)
    v.update(True, 400)
    assert v.update(True, 10000) is True


class FakePlayer:
    def __init__(self):
        self.played = []
        self.stops = 0
        self.busy = False

    def play(self, track):
        self.played.append(track)

    def stop(self):
        self.stops += 1

    def is_busy(self):
        return self.busy


def make_voice(player):
    # pick=min makes the random choice deterministic for tests
    return Voice(player, busy_assert_ms=300, fallback_ms=3000, pick=min)


def test_say_one_of_plays_a_track_from_the_list():
    p = FakePlayer()
    v = make_voice(p)
    assert v.say_one_of([7, 9]) is True
    assert p.played == [7]
    assert v.is_talking is True


def test_polite_line_is_skipped_while_talking():
    p = FakePlayer()
    v = make_voice(p)
    v.say_one_of([7])
    assert v.say_one_of([9]) is False
    assert p.played == [7]              # nothing new played
    assert p.stops == 0


def test_important_line_interrupts():
    p = FakePlayer()
    v = make_voice(p)
    v.say_one_of([7])
    assert v.say_one_of([9], important=True) is True
    assert p.stops == 1                 # cut off the old line
    assert p.played == [7, 9]


def test_update_follows_the_player_busy_wire():
    p = FakePlayer()
    v = make_voice(p)
    v.update(0)
    assert v.is_talking is False


def test_then_say_plays_after_the_current_line():
    p = FakePlayer()
    v = Voice(p, busy_assert_ms=0, fallback_ms=0, pick=min)
    v.say_one_of([7])
    v.then_say_one_of([9])
    assert p.played == [7]          # follow-up waits its turn
    p.busy = True                   # module is playing track 7
    v.update(ticks_ms())
    assert p.played == [7]          # still track 7's turn
    p.busy = False                  # track 7 finished
    v.update(ticks_ms())
    assert p.played == [7, 9]       # follow-up takes the mic
    assert v.is_talking is True


def test_then_say_speaks_now_when_quiet():
    p = FakePlayer()
    v = Voice(p, busy_assert_ms=0, fallback_ms=0, pick=min)
    v.then_say_one_of([9])
    assert p.played == [9]          # nobody talking: your turn is now


def test_interruption_forgets_the_waiting_line():
    p = FakePlayer()
    v = Voice(p, busy_assert_ms=0, fallback_ms=0, pick=min)
    v.say_one_of([7])
    v.then_say_one_of([9])
    v.say_one_of([5], important=True)   # a new event interrupts
    p.busy = True
    v.update(ticks_ms())
    p.busy = False
    v.update(ticks_ms())
    assert p.played == [7, 5]           # 9 belonged to the old event: gone
    assert v.is_talking is False
