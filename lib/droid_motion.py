"""droid_motion - the HC-SR501 PIR "did a warm body move?" sensor.

THE DEVICE
    A PIR (passive infrared) sensor watches the heat pattern of a room
    through a faceted plastic dome. When something warm MOVES across
    its ~110 degree view - a person up to ~7 m away - its OUT pin snaps
    HIGH. It cannot see distance or direction (that is the laser's job);
    it is the classic wide-angle "someone walked in" detector, and it
    costs about a dollar.
      Datasheet: https://www.mpja.com/download/31227sc.pdf
      Tutorial:  https://lastminuteengineers.com/pir-sensor-arduino-tutorial/
      PIR guide: https://learn.adafruit.com/pir-passive-infrared-proximity-motion-sensor

WIRING (defaults used by the examples)
    HC-SR501                    Pico
      VCC  ------------------>  VBUS (pin 40, 5 V from USB)
      OUT  ------------------>  GP3
      GND  ------------------>  GND (pin 38)

    Settings on the module itself:
      - Jumper on H (repeat trigger): OUT stays HIGH while motion
        continues. (L fires one fixed pulse and goes blind during it.)
      - Time-delay pot fully counter-clockwise: ~3 s hold - this
        library wants fresh state, not a five-minute latched HIGH.
      - Sensitivity pot mid-way to start (end to end is ~3-7 m).

ELECTRICAL NOTES
    - Pull-up / pull-down resistors: none needed - the module drives
      OUT push-pull. Do NOT enable the Pico's internal pulls.
    - Series resistors: none needed.
    - Capacitors: none required. If you see ghost triggers on a messy
      breadboard, 100 nF + 10 uF across VCC/GND at the sensor can help,
      but fix placement first (next line).
    - Keep it a few cm from the Pico W's antenna (the end with the
      metal shield) and away from speaker/servo wires - 2.4 GHz bursts
      and motor spikes are the classic causes of PIR false alarms.
    - Logic level: SAFE. The module eats 5 V but its onboard regulator
      runs the sensor chip at 3.3 V, so OUT never rises above 3.3 V.
    - Warm-up is physics, not a bug: the sensing element needs up to
      ~60 s after power-on to settle, and OUT flails meanwhile. This
      library hides that minute behind ready().
"""
try:
    from time import ticks_ms, ticks_diff
except ImportError:  # desktop CPython for tests
    import time

    def ticks_ms():
        return int(time.monotonic() * 1000)

    def ticks_diff(a, b):
        return a - b


class MotionFilter:
    """Pure logic (desktop-testable): warm-up gating + a latched edge.

    Feed it the raw pin level with update(level, now_ms); it ignores
    everything during the sensor's flaky first minute, then tracks the
    live level and remembers each new LOW->HIGH rise until you ask.
    """

    def __init__(self, warmup_ms=60_000, diff=None):
        self._warmup = warmup_ms
        self._diff = diff or ticks_diff
        self._t0 = None          # stamped by the first update()
        self._ready = False
        self._level = False
        self._started = False

    def update(self, level, now_ms):
        """One raw reading. During warm-up nothing is recorded; the
        reading that ENDS the warm-up becomes the baseline (already-HIGH
        does not count as somebody arriving)."""
        if self._t0 is None:
            self._t0 = now_ms
        if not self._ready:
            if self._diff(now_ms, self._t0) >= self._warmup:
                self._ready = True
                self._level = bool(level)   # baseline, not an edge
            return
        level = bool(level)
        if level and not self._level:
            self._started = True            # latched until read
        self._level = level

    def ready(self):
        """True once the warm-up minute has passed."""
        return self._ready

    def motion(self):
        """Is motion seen RIGHT NOW? (Always False during warm-up.)"""
        return self._level if self._ready else False

    def motion_started(self):
        """True ONCE per new motion event, then clears - a slow loop
        cannot miss a short wave."""
        started = self._started
        self._started = False
        return started


def _default_pin_factory(gp):
    # imported lazily so this module stays desktop-testable
    from machine import Pin
    return Pin(gp, Pin.IN)   # no internal pull: the module drives push-pull


class Pir:
    """The HC-SR501 on one input pin, polled - no interrupts, no magic.

    pir = Pir()                  # OUT on GP3, 60 s warm-up
    pir.ready()                  # has the warm-up minute passed?
    pir.motion()                 # is motion seen right now?
    pir.motion_started()         # True once per NEW motion event
    """

    def __init__(self, pin=3, warmup_s=60, pin_factory=None):
        self._pin = (pin_factory or _default_pin_factory)(pin)
        self._filter = MotionFilter(warmup_ms=int(warmup_s * 1000))

    def _poll(self):
        self._filter.update(self._pin.value(), ticks_ms())

    def ready(self):
        """True once the sensor's settle time has passed."""
        self._poll()
        return self._filter.ready()

    def motion(self):
        """Is motion seen RIGHT NOW? (False during warm-up.)"""
        self._poll()
        return self._filter.motion()

    def motion_started(self):
        """Did a NEW motion event begin since you last asked?
        Latched, so a busy loop cannot miss a short wave."""
        self._poll()
        return self._filter.motion_started()
