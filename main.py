"""Dino smart bin robot - main loop.

The IR beam does double duty (no tilt switch):
  - blocked briefly then clear  -> something dropped in: play the voice
    track, LEDs on while it plays.
  - blocked FULL_AFTER_S        -> FULL: beep + LED flashes every
    ALERT_REPEAT_S until the beam is seen again.

The PIR motion sensor greets people: a new motion event calls
on_motion_detected() (plays sound 1), and the eye LEDs stay lit for as
long as motion is seen.

All tuning knobs are in config.py.
"""
import time
from machine import Pin, UART

import config
from dysv17f import DYSV17F
from bin_watch import BinWatch, FlashBurst
from ir_beam import IRBeam
from droid_motion import Pir

# --- hardware setup ---------------------------------------------------
uart = UART(config.UART_ID, baudrate=9600,
            tx=Pin(config.UART_TX_PIN), rx=Pin(config.UART_RX_PIN))
busy = Pin(config.BUSY_PIN, Pin.IN)
#leds = [Pin(n, Pin.OUT, value=0) for n in config.LED_PINS]
ir_emit = Pin(config.IR_EMIT_PIN, Pin.OUT, value=0)
ir_recv1 = Pin(config.IR_RECV1_PIN, Pin.IN, pull=Pin.PULL_UP)
ir_recv2 = Pin(config.IR_RECV2_PIN, Pin.IN, pull=Pin.PULL_UP)
ir_recv3 = Pin(config.IR_RECV3_PIN, Pin.IN, pull=Pin.PULL_UP)
ir_beam = IRBeam(ir_emit, [ir_recv1, ir_recv2, ir_recv3], config.IR_BEAM_SEEN_VALUE,
                 config.IR_SETTLE_MS, config.IR_SAMPLE_COUNT,
                 config.IR_SAMPLE_GAP_US)
eyes = Pin(config.EYES_PIN, Pin.OUT, value=0)   # both eye LEDs on one GPIO
pir = Pir(pin=config.PIR_PIN, warmup_s=config.PIR_WARMUP_S)

player = DYSV17F(uart, busy_pin=busy, busy_active=config.BUSY_ACTIVE)
player.set_volume(config.VOLUME)


def set_leds(on):
    for led in leds:
        led.value(1 if on else 0)


def on_motion_detected():
    """A human was spotted by the PIR: play sound 1."""
    player.play(config.TRACK_MOTION_VOICE)


def beam_seen():
    """Pulse the IR emitter and return a noise-filtered beam sample."""
    return ir_beam.seen()


# --- state ------------------------------------------------------------
now = time.ticks_ms()
watch = BinWatch(config.FULL_AFTER_S * 1000,
                 config.ALERT_REPEAT_S * 1000,
                 config.IR_PASS_MAX_MS, now)
burst = FlashBurst(config.FLASH_COUNT, config.FLASH_MS)

voice_started = None   # ticks when the pass voice started; None = not playing
voice_saw_busy = False

# --- main loop ----------------------------------------------------------
while True:
    now = time.ticks_ms()
    
    # Update state
    motion_started = pir.motion_started()
    
    
    # Make decisions


    # Do actions
    
    
    # Sample the beam every tick: a short block that clears is a
    # drop-through -> interrupt whatever is playing, start the voice.
    if watch.beam_result(beam_seen(), now):
        burst.cancel()                 # voice takes the LEDs back
        player.stop()
        time.sleep_ms(20)              # brief gap between UART commands
        player.play(config.TRACK_PASS_VOICE)
        voice_started = now
        voice_saw_busy = False
    if not watch.is_full():
        burst.cancel()                 # bin emptied: stop any running alert

    # New motion event -> greet, unless a sound is already playing (a
    # drop-through voice or the full-bin beep keeps priority).
    if (pir.motion_started() and voice_started is None
            and not player.is_busy() and not burst.active()):
        on_motion_detected()
        voice_started = now            # reuse the voice/LED tracking below
        voice_saw_busy = False

    # Eyes stay lit while motion is seen (always off during PIR warm-up).
    eyes.value(1 if pir.motion() else 0)

    # Alert burst when due - skipped entirely if a sound is playing, or a
    # pass voice was just started (BUSY takes ~200 ms to assert after a
    # play command, so a False BUSY right after play() cannot be trusted).
    if (watch.burst_due(now) and not player.is_busy()
            and voice_started is None):
        player.play(config.TRACK_BEEP)
        burst.start(now)

    # LEDs: burst pattern wins; else follow the pass voice; else off.
    if burst.active():
        set_leds(burst.led_on(now))
    elif voice_started is not None:
        if time.ticks_diff(now, voice_started) < config.BUSY_ASSERT_MS:
            set_leds(True)             # BUSY can't be trusted yet after play()
        elif player.is_busy():
            voice_saw_busy = True
            set_leds(True)
        elif voice_saw_busy:
            set_leds(False)            # playback just finished
            voice_started = None
        elif time.ticks_diff(now, voice_started) < config.LED_FALLBACK_ON_MS:
            set_leds(True)             # BUSY never asserted: fixed on-time
        else:
            set_leds(False)
            voice_started = None
    else:
        set_leds(False)

    time.sleep_ms(config.TICK_MS)


