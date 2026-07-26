"""Dino smart bin robot - main loop.

Door swings shut  -> play the voice track, LEDs on while it plays.
IR beam blocked FULL_AFTER_S -> FULL: beep + LED flashes every
ALERT_REPEAT_S until the beam is seen again.

All tuning knobs are in config.py.
"""
import time
from machine import Pin, UART

import config
from dysv17f import DYSV17F
from bin_watch import BinWatch, DoorWatch, FlashBurst

# --- hardware setup ---------------------------------------------------
uart = UART(config.UART_ID, baudrate=9600,
            tx=Pin(config.UART_TX_PIN), rx=Pin(config.UART_RX_PIN))
busy = Pin(config.BUSY_PIN, Pin.IN)
tilt = Pin(config.TILT_PIN, Pin.IN, Pin.PULL_UP)
leds = [Pin(n, Pin.OUT, value=0) for n in config.LED_PINS]
ir_emit = Pin(config.IR_EMIT_PIN, Pin.OUT, value=0)
ir_recv = Pin(config.IR_RECV_PIN, Pin.IN)

player = DYSV17F(uart, busy_pin=busy, busy_active=config.BUSY_ACTIVE)
player.set_volume(config.VOLUME)


def set_leds(on):
    for led in leds:
        led.value(1 if on else 0)


def beam_seen():
    """Pulse the IR emitter and sample the receiver once."""
    ir_emit.value(1)
    time.sleep_ms(config.IR_SETTLE_MS)
    seen = ir_recv.value() == config.IR_BEAM_SEEN_VALUE
    ir_emit.value(0)
    return seen


# --- state ------------------------------------------------------------
now = time.ticks_ms()
door = DoorWatch(config.DOOR_OPEN_VALUE, config.DOOR_DEBOUNCE_MS,
                 tilt.value(), now)
watch = BinWatch(config.FULL_AFTER_S * 1000,
                 config.ALERT_REPEAT_S * 1000, now)
burst = FlashBurst(config.FLASH_COUNT, config.FLASH_MS)

next_ir_check = now
voice_started = None   # ticks when the door voice started; None = not playing
voice_saw_busy = False

# --- main loop ----------------------------------------------------------
while True:
    now = time.ticks_ms()

    # Door: on open->shut, interrupt whatever is playing, start the voice.
    if door.closed_event(tilt.value(), now):
        burst.cancel()                 # voice takes the LEDs back
        player.stop()
        time.sleep_ms(20)              # brief gap between UART commands
        player.play(config.TRACK_DOOR_VOICE)
        voice_started = now
        voice_saw_busy = False

    # IR fullness check on its own schedule.
    if time.ticks_diff(now, next_ir_check) >= 0:
        next_ir_check = time.ticks_add(now, config.IR_CHECK_INTERVAL_S * 1000)
        watch.beam_result(beam_seen(), now)
        if not watch.is_full():
            burst.cancel()             # bin emptied: stop any running alert

    # Alert burst when due - skipped entirely if a sound is playing, or a
    # door voice was just started (BUSY takes ~200 ms to assert after a
    # play command, so a False BUSY right after play() cannot be trusted).
    if (watch.burst_due(now) and not player.is_busy()
            and voice_started is None):
        player.play(config.TRACK_BEEP)
        burst.start(now)

    # LEDs: burst pattern wins; else follow the door voice; else off.
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
