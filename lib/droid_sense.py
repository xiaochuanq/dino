"""droid_sense - person detection zones and the push-to-talk button.

THE DEVICES
    VL53L1X (used via lib/vl53l1x.py): a laser time-of-flight distance
    sensor from ST - it times an invisible, eye-safe laser pulse and
    reports distance in millimetres, up to ~4 m, regardless of the
    target's colour or ambient light.
      Chip page: https://www.st.com/en/imaging-and-photonics-solutions/vl53l1x.html
      Breakouts: https://www.pololu.com/product/3415
                 https://www.adafruit.com/product/3967
    Push button: any momentary push button.

WIRING (defaults used by the examples)
    VL53L1X                          Button
      VIN -> 3V3 (pin 36)             one leg -> GP15
      GND -> GND                      other leg -> GND
      SDA -> GP4 (I2C0 SDA)           (pressed reads LOW)
      SCL -> GP5 (I2C0 SCL)

ELECTRICAL NOTES
    - I2C needs pull-up resistors on SDA and SCL. Every common VL53L1X
      breakout (Pololu, Adafruit, GY-53) already has ~10 k pull-ups on
      board, so with one breakout you add nothing. If yours is a bare
      module without pull-ups, or the bus is longer than ~20 cm, add
      4.7 k-10 k resistors from SDA->3V3 and SCL->3V3.
    - The button needs NO external resistor: construct its Pin with
      Pin.PULL_UP (the Pico's internal pull-up) and wire the button to
      GND. For very long button wires, a 100 nF capacitor across the
      button legs filters electrical noise and adds hardware debounce.

FILTERING (why readings don't flicker)
    ZoneFilter is pure logic (desktop-testable): median filter over the
    last N readings plus a hold time so a zone change must be stable
    before it is reported. Ranger wraps any sensor object exposing
    read() -> mm.

DISTANCE MODES (set_mode)
    The VL53L1X has three range modes; the chip powers on in "long".
      "short"   up to ~1.3 m   barely bothered by bright light
      "medium"  up to ~2.9 m   good indoor pick for greeting people
      "long"    up to ~3.6 m   needs dim light for the full distance
    Every mode measures down to ~4 cm. The maximums are datasheet values
    for a large white target in the dark: dark clothing roughly halves
    them, and direct sunlight squashes medium/long to under 1 m while
    short keeps nearly its full 1.3 m (short is the outdoor choice).
        set_mode(sensor, "medium")    # right after building the sensor
    Switching modes keeps the measurement budget (default 50 ms) by
    recomputing the chip's timeout registers - pure math, tested on PC.

"FAR AWAY" VS "NO DATA" (read_mm)
    The chip marks every reading with a status byte: "real target seen"
    vs "not enough light came back" (nothing in range) vs "reflection
    from beyond my range folded over". read_mm() returns millimetres
    only for real targets and None otherwise, and Ranger uses it, so a
    person beyond the mode's range simply reads as "far" - never as a
    bogus 0 mm "close".
"""
try:
    from time import ticks_ms, ticks_diff, ticks_add
except ImportError:  # desktop CPython for tests
    import time

    def ticks_ms():
        return int(time.monotonic() * 1000)

    def ticks_diff(a, b):
        return a - b

    def ticks_add(a, b):
        return a + b

FAR = "far"
NEAR = "near"
CLOSE = "close"

# ---- VL53L1X distance modes ------------------------------------------------
# Register recipes from ST's driver code (via the MIT-licensed Pololu
# vl53l1x-arduino library): VCSEL period A, VCSEL period B, valid phase
# high, window-of-interest SD0/SD1, initial phase SD0/SD1.

_MODES = {
    "short":  (0x07, 0x05, 0x38, 0x0705, 0x0606),
    "medium": (0x0B, 0x09, 0x78, 0x0B09, 0x0A0A),
    "long":   (0x0F, 0x0D, 0xB8, 0x0F0D, 0x0E0E),
}
_TIMING_GUARD_US = 4528  # ST's fixed per-measurement ranging overhead


def _encode_timeout(mclks):
    # timeout register format: (LSByte * 2^MSByte) + 1 macro periods
    if mclks <= 0:
        return 0
    ls, ms = mclks - 1, 0
    while ls > 0xFF:
        ls >>= 1
        ms += 1
    return (ms << 8) | ls


def _macro_period_us(fast_osc, vcsel_period):
    # one ranging macro period in 12.12 fixed-point microseconds
    pll_period = (1 << 30) // fast_osc
    pclks = (vcsel_period + 1) << 1
    return (((2304 * pll_period) >> 6) * pclks) >> 6


def _timeout_mclks(us, macro_period_us):
    return ((us << 12) + (macro_period_us >> 1)) // macro_period_us


def _mode_register_writes(mode, fast_osc, budget_ms=50):
    """Pure logic: the (register, value, byte-width) writes that move a
    VL53L1X into `mode` while keeping a `budget_ms` measurement window."""
    if mode not in _MODES:
        raise ValueError("mode must be one of: " + ", ".join(sorted(_MODES)))
    if not 15 <= budget_ms <= 500:
        raise ValueError("budget_ms must be between 15 and 500")
    vcsel_a, vcsel_b, phase_high, woi, initial_phase = _MODES[mode]
    # the five timeout registers below count macro periods, whose real
    # duration just changed with the VCSEL periods - recompute them so
    # the measurement still takes budget_ms
    range_us = (budget_ms * 1000 - _TIMING_GUARD_US) // 2
    macro_a = _macro_period_us(fast_osc, vcsel_a)
    macro_b = _macro_period_us(fast_osc, vcsel_b)
    return [
        (0x0060, vcsel_a, 1),
        (0x0063, vcsel_b, 1),
        (0x0069, phase_high, 1),
        (0x0078, woi, 2),
        (0x007A, initial_phase, 2),
        (0x004B, min(_timeout_mclks(1000, macro_a), 0xFF), 1),
        (0x005A, _encode_timeout(_timeout_mclks(1, macro_a)), 2),
        (0x005E, _encode_timeout(_timeout_mclks(range_us, macro_a)), 2),
        (0x005C, _encode_timeout(_timeout_mclks(1, macro_b)), 2),
        (0x0061, _encode_timeout(_timeout_mclks(range_us, macro_b)), 2),
    ]


def set_mode(sensor, mode, budget_ms=50):
    """Switch a VL53L1X between "short" (~1.3 m), "medium" (~2.9 m) and
    "long" (~3.6 m, the power-on default). `sensor` is the vendored
    vl53l1x.VL53L1X object - a LaserArray .sensor(name) works too."""
    fast_osc = sensor.readReg16Bit(0x0006)  # this chip's oscillator speed
    writes = _mode_register_writes(mode, fast_osc, budget_ms)
    sensor.writeReg(0x0087, 0x00)           # stop ranging
    for reg, value, width in writes:
        if width == 1:
            sensor.writeReg(reg, value)
        else:
            sensor.writeReg16Bit(reg, value)
    sensor.writeReg(0x0086, 0x01)           # clear stale interrupt
    sensor.writeReg(0x0087, 0x40)           # start ranging again


# ---- trustworthy readings --------------------------------------------------

_GOOD_STATUS = (9, 8)  # 9 = range valid; 8 = valid but target very close


def parse_result(data):
    """Pure logic: one 17-byte VL53L1X result block -> millimetres, or
    None when the chip itself says there was no real target (too little
    light came back, or a beyond-range reflection folded over)."""
    if data is None or len(data) < 17:
        return None
    if data[0] not in _GOOD_STATUS:
        return None
    return (data[13] << 8) + data[14]


def read_mm(sensor):
    """One distance in millimetres, or None for "no real target".
    Checks the chip's status byte when the sensor exposes its I2C bus
    (the vendored VL53L1X does); other objects fall back to read()."""
    try:
        i2c = getattr(sensor, "i2c", None)
        if i2c is None:
            return sensor.read()
        return parse_result(
            i2c.readfrom_mem(sensor.address, 0x0089, 17, addrsize=16))
    except OSError:
        return None


class SelfHealingLaser:
    """Owns the laser through a build-it function and keeps it alive.

    mm(now_ms) -> millimetres, or None for "nothing in range".

    Why: a supply dip (loud speaker, brown-out) resets the VL53L1X into
    standby, and an I2C glitch can wedge the bus - either way the sensor
    goes silent until someone re-initializes it. This wrapper rebuilds
    it after heal_after_ms of unbroken silence, trying at most once per
    retry_every_ms, so the robot never needs a reboot. An empty room is
    also "silence", so the occasional needless rebuild is by design -
    it costs a few milliseconds of register writes.
    """

    def __init__(self, build, heal_after_ms=10_000, retry_every_ms=10_000):
        self._build = build          # () -> ranging sensor; may raise
        self._heal_after = heal_after_ms
        self._retry_every = retry_every_ms
        self._sensor = None
        self._quiet_since = None     # when the current silence started
        self._next_retry = None      # None = allowed to (re)build now

    def mm(self, now_ms):
        """One reading. Rebuilds the sensor first if it is missing or
        has been silent too long; a rebuilt sensor answers next call."""
        if self._sensor is None:
            self._rebuild(now_ms)
            if self._sensor is None:
                return None
        value = read_mm(self._sensor)
        if value is not None:
            self._quiet_since = None
            return value
        if self._quiet_since is None:
            self._quiet_since = now_ms
        elif ticks_diff(now_ms, self._quiet_since) >= self._heal_after:
            self._rebuild(now_ms)
        return None

    def _rebuild(self, now_ms):
        if (self._next_retry is not None and
                ticks_diff(now_ms, self._next_retry) < 0):
            return                   # tried recently: wait our turn
        self._next_retry = ticks_add(now_ms, self._retry_every)
        self._quiet_since = now_ms   # fresh grace period either way
        try:
            self._sensor = self._build()
        except (OSError, RuntimeError, ValueError):
            self._sensor = None      # still gone; mm() keeps saying None


class ZoneFilter:
    def __init__(self, near_mm=1000, close_mm=500, samples=5,
                 hold_ms=300, stale_ms=2000, diff=None):
        self._near = near_mm
        self._close = close_mm
        self._samples = samples
        self._hold = hold_ms
        self._stale = stale_ms
        self._diff = diff or ticks_diff
        self._buf = []
        self._zone = FAR
        self._cand = FAR
        self._cand_since = 0
        self._last_good = 0

    def update(self, mm, now_ms):
        if mm is None:
            if self._diff(now_ms, self._last_good) > self._stale:
                # sensor dead: fail safe to "far" (robot still answers
                # on button press, it just stops auto-greeting)
                self._zone = self._cand = FAR
                self._buf = []
            return self._zone
        self._last_good = now_ms
        self._buf.append(mm)
        if len(self._buf) > self._samples:
            self._buf.pop(0)
        median = sorted(self._buf)[len(self._buf) // 2]
        if median <= self._close:
            zone = CLOSE
        elif median <= self._near:
            zone = NEAR
        else:
            zone = FAR
        if zone != self._cand:
            self._cand = zone
            self._cand_since = now_ms
        elif zone != self._zone and \
                self._diff(now_ms, self._cand_since) >= self._hold:
            self._zone = zone
        return self._zone


class Ranger:
    def __init__(self, sensor, zone_filter=None):
        self._sensor = sensor
        self._filter = zone_filter or ZoneFilter()

    def zone(self):
        return self._filter.update(read_mm(self._sensor), ticks_ms())


class DeadSensor:
    """Stand-in when the real distance sensor fails to initialize.
    Ranger degrades it to permanent "far": greeting is disabled but the
    robot still answers on button press."""

    def read(self):
        raise OSError("sensor unavailable")


class Button:
    """Push-to-talk button wired pin -> GND with internal pull-up."""

    def __init__(self, pin):
        self._pin = pin

    def is_pressed(self):
        return self._pin.value() == 0
