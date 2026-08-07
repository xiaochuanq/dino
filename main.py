"""Dino the smart donation bin - main program.

HOW DINO THINKS - the loop at the bottom, three steps every tick:
  1. SENSE  - each body part looks at the world and updates its state.
  2. DECIDE - simple ifs turn those states into human events.
  3. ACT    - the on_...() functions say what Dino does. Edit them!

DINO'S BODY PARTS (built in the hardware section - the only place
device names appear):
  visitor - a laser tape-measure: is someone away / passing / here?
  lid    - an IR light beam across the flap: open? pushed? stuck-open full?
  voice   - a sound board: speaks random lines, knows if it's talking
  eyes    - two LEDs: steady glow, lively blink while talking

WIRING (GP numbers; tuning knobs in config.py)
    DY-SV17F   VCC -> VBUS (5 V), GND -> GND,
               RX -> GP0 (UART0 TX), TX -> GP1 (UART0 RX),
               CON3 -> GP2 (becomes BUSY; strap 4.7 k to 3.3 V),
               CON1 + CON2 -> GND direct, SPK+/SPK- -> speaker
    Eyes       GP4 -> two LEDs in parallel, EACH through its own
               resistor -> GND
    IR beam    emitter: GP5 --[220 ohm]--> anode, cathode -> GND
               receivers: -> GP6, GP7, GP8 (internal pull-ups)
    VL53L1X    VIN -> 3V3, GND -> GND, SDA -> GP14, SCL -> GP15 (I2C1)
"""
import time
from machine import Pin, UART, I2C

import config
from dysv17f import DYSV17F
from ir_beam import IRBeam
from vl53l1x import VL53L1X
from droid_sense import SelfHealingLaser, set_mode
from visitor import Visitor
from lid import Lid
from voice import Voice
from eyes import Eyes

# --- hardware: build Dino's body parts ----------------------------------
now = time.ticks_ms()

uart = UART(config.UART_ID, baudrate=9600,
            tx=Pin(config.UART_TX_PIN), rx=Pin(config.UART_RX_PIN))
player = DYSV17F(uart, busy_pin=Pin(config.BUSY_PIN, Pin.IN),
                 busy_active=config.BUSY_ACTIVE)
player.set_volume(config.VOLUME)
voice = Voice(player, config.BUSY_ASSERT_MS, config.TALK_FALLBACK_MS)

beam = IRBeam(Pin(config.IR_EMIT_PIN, Pin.OUT, value=0),
              [Pin(n, Pin.IN, pull=Pin.PULL_UP) for n in config.IR_RECV_PINS],
              config.IR_BEAM_SEEN_VALUE, config.IR_SETTLE_MS,
              config.IR_SAMPLE_COUNT, config.IR_SAMPLE_GAP_US)
lid = Lid(beam, config.LID_PUSH_MAX_MS, config.FULL_AFTER_S * 1000,
          config.COMPLAIN_EVERY_S * 1000, now)

def build_laser():
    """Wake the laser and set its range mode. SelfHealingLaser calls
    this at boot AND again whenever the sensor goes silent too long
    (power dip, I2C hiccup) - so a flaky laser recovers on its own."""
    sensor = VL53L1X(I2C(config.I2C_ID, sda=Pin(config.I2C_SDA_PIN),
                         scl=Pin(config.I2C_SCL_PIN)))
    set_mode(sensor, config.LASER_MODE)
    return sensor


laser = SelfHealingLaser(build_laser)  # laser gone: greetings pause, lid works
visitor = Visitor(laser, config.HERE_MM, config.LEAVE_MM,
                  config.PASSING_MM, config.PASSING_COOLDOWN_S * 1000)

eyes = Eyes(Pin(config.EYES_PIN, Pin.OUT, value=1), config.TALK_BLINK_MS)


# --- ACT: what Dino does. Kids, edit these! ------------------------------
def on_visitor_passing():
    print("Someone walks by, 1-3 m away.")
    voice.say_one_of(config.PASSING_TRACKS)


def on_visitor_arrives():
    print("Someone comes close - say hello!")
    voice.say_one_of(config.GREETING_TRACKS, important=True)
    voice.then_say_one_of(config.ASK_HELP_TRACKS)   # after the hello ends

def on_visitor_leaves():
    print("They walk away - say goodbye!")
    voice.say_one_of(config.GOODBYE_TRACKS, important=True)


def on_donation():
    print("They pushed the lid - thank them!")
    voice.say_one_of(config.POST_EATING_TRACKS, important=True)
    voice.then_say_one_of(config.THANKS_TRACKS)     # after the gulp ends


def on_bin_full():
    print("The lid is stuck open - Dino is stuffed. Complain!")
    voice.say_one_of(config.CHOKE_TRACKS)


# --- the loop: SENSE -> DECIDE -> ACT ------------------------------------
while True:
    now = time.ticks_ms()

    # 1. SENSE - every part looks at the world
    visitor.update(now)
    lid.update(now)
    voice.update(now)

    # 2. DECIDE - turn states into human events
    if lid.just_pushed and visitor.where == "here":
        on_donation()              # a donation beats a greeting
    elif visitor.just_arrived:
        on_visitor_arrives()
    if visitor.just_left:
        on_visitor_leaves()
    if visitor.just_passed:
        on_visitor_passing()
    if lid.complain_due(now):
        on_bin_full()

    # 3. SHOW - the eyes follow the mood
    eyes.update(now, voice.is_talking)

    time.sleep_ms(config.TICK_MS)




