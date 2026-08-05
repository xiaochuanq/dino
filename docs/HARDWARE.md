# Dino — Hardware Summary

Devices, pin assignments, and wiring for the smart bin robot. Pin numbers
are the single source of truth in `config.py`; this file mirrors them.

Drivers `lib/dysv17f.py` and `lib/droid_motion.py` are imported from the
[pico-droid](../../pico-droid) project — re-copy them from there when that
project updates them (last synced 2026-08-04). `lib/ir_beam.py` is authored
here and copied the other way, into pico-droid.

## Devices

| Device | Role | Interface |
|---|---|---|
| Raspberry Pi Pico 2 / 2 W | Controller running MicroPython (`main.py`) | — |
| DY-SV17F voice module | Plays pass voice + full-bin beep from its own 4 MB flash; built-in 3–5 W amp | UART0 @ 9600 baud + BUSY GPIO |
| 4–8 Ω speaker | Sound output | DY-SV17F SPK+/SPK− terminals |
| LED(s) | Lit while voice plays; flash during full-bin alert | GPIO (one pin per LED, all switched together) |
| IR emitter LED | One side of the beam across the bin opening | GPIO (through 220 Ω) |
| IR receiver | Bare phototransistor/photodiode break-beam sensor; a short block = something dropped in (voice); blocked ≥ 60 s = bin FULL (alert) | GPIO input |
| HC-SR501 PIR | Wide-angle human-motion sensor; a new motion event plays sound 1 (`on_motion_detected`) | GPIO input |
| 2× eye LEDs | The dino's eyes; lit while motion is seen | One shared GPIO |

## Pico pin assignments

| GP pin | Config constant | Function |
|---|---|---|
| GP0 | `UART_TX_PIN` | UART0 TX → DY-SV17F RX |
| GP1 | `UART_RX_PIN` | UART0 RX ← DY-SV17F TX |
| GP2 | `BUSY_PIN` | DY-SV17F BUSY input (high while playing, `BUSY_ACTIVE = 1`) |
| GP3 | `PIR_PIN` | HC-SR501 PIR OUT input (no internal pull) |
| GP4 | `LED_PINS` | LED output (add more GP numbers to the list for more LEDs) |
| GP5 | `IR_EMIT_PIN` | IR emitter output (briefly pulsed for each receiver sample) |
| GP6 | `IR_RECV_PIN` | IR receiver input (`IR_BEAM_SEEN_VALUE = 0`) |
| GP7 | `EYES_PIN` | Both eye LEDs, switched together by this one pin |

The IR blink test uses the external LED on the first pin in `LED_PINS` (GP4
by default). It deliberately does not use `Pin("LED")`: on Pico W / Pico 2 W
the onboard LED is reached through CYW43, and a CYW43 I/O timeout would stop
the sensor test.

## Connection table

| From (Pico) | To (device) | Notes |
|---|---|---|
| GP0 | DY-SV17F RX | 3.3 V TTL, direct — no level shifter needed |
| GP1 | DY-SV17F TX | |
| GP2 | DY-SV17F CON3 pin | No pin is labeled "BUSY" — CON3 (module pin 12) doubles as the busy output in UART mode. 3.3 V logic. |
| VBUS (pin 40, 5 V) | DY-SV17F VCC | 5 V recommended for the onboard amp (see power note) |
| GND | DY-SV17F GND | |
| — | DY-SV17F SPK+/SPK− → speaker | 4–8 Ω, driven by the module's own amp |
| GP4 | LED anode | Series resistor → cathode → GND |
| GP5 | IR emitter LED anode | **220 Ω** series resistor → cathode → GND (Vf ≈ 1.3 V → ~9 mA; never below 150 Ω, never resistor-less) |
| GP6 | IR receiver OUT | Bare phototransistor: collector → GP6, emitter → GND. The code enables GP6's internal pull-up; an external **10 kΩ pull-up to 3V3** gives a stronger, more predictable signal. A simple comparator break-beam module may use VCC → 3V3, GND → GND, OUT → GP6. |
| GP3 | HC-SR501 OUT | Push-pull 3.3 V output from the module — no pulls, no series resistor. VCC → VBUS (5 V), GND → GND. Jumper on H (repeat trigger), time-delay pot fully counter-clockwise (~3 s). Needs ~60 s warm-up after power-on; keep it away from the Pico W antenna and speaker wires. |
| GP7 | Eye LED anodes (×2) | Two LEDs in parallel, **each with its own series resistor** (e.g. 220 Ω) → cathodes → GND. Two standard LEDs ≈ 2×10 mA is at the edge of one GPIO's comfort; use ≥ 330 Ω resistors or an NPN driver if you want them bright. |
| 3V3 / GND | Sensor power | IR receiver parts |

### IR part compatibility and emitter drive

This project uses a plain optical break beam: a 940 nm emitter faces a bare
phototransistor/photodiode or simple comparator module. The program briefly
turns the emitter on, samples the detector, and turns it off; no carrier or IR
remote-control protocol is involved.

The direct GP5 circuit supplies only about 9 mA and is intended for short
distances. For a wider bin, use a 940 nm emitter through an NPN low-side
driver: `3V3 -> LED series resistor -> LED anode`, LED cathode to collector,
emitter to GND, and GP5 through 1 kΩ to base. Add a 10 kΩ base-to-GND resistor.
Keep Pico and driver grounds common. Size the resistor conservatively and
never omit it. GP5 high must turn the transistor and LED on.

A faint deep-red dot from some 850 nm emitters is normal. A 940 nm emitter is
usually invisible to the eye (check it with a phone camera). A bright red LED
is likely the wrong part or is being overdriven; switch power off and verify
its part number, polarity, and series resistor.

### DY-SV17F setup

- Mode straps for UART control: **CON1=0, CON2=0, CON3=1** — i.e. **CON1
  and CON2 directly to GND with plain wire (no series resistor!)** and
  CON3 to 3.3 V (the module's V33 pin) through a **4.7 kΩ resistor**
  (two 10 k in parallel = 5 k works). A series resistor on CON1/CON2
  forms a divider against the chip's internal pull-up that lands in the
  undefined logic band (0.8–2.7 V), so the mode bits misread at
  power-on. CON3 is the opposite case — it needs its resistor (and 10 kΩ
  or more is too weak) because the pin is dual-use (module pin 12) and
  becomes the **BUSY output** after boot, so it must stay free to be
  driven — wire it to Pico GP2. If busy reads inverted on your board,
  flip `BUSY_ACTIVE` in `config.py`.
- **Straps are sampled only in the first ~30 ms after module power-on.**
  After changing them, unplug the module's power completely; a Pico soft
  reboot does not re-strap it. Symptom of a missed strap: the module
  boots into IO-trigger mode, where RX/IO1 (the pin on Pico TX) is the
  hardware "play track 2" button — any UART traffic then plays track 2,
  whatever track the code requested (`examples/08_test_mode_check.py`
  detects this).
- Audio files: plug the module into USB (it mounts as a flash drive) and
  copy `00001.wav` (pass voice) and `00002.wav` (full-bin beep).
- **Power note:** the upstream driver docs recommend VCC from **5 V
  (Pico VBUS)** — the UART logic is still 3.3 V-safe. The amp draws
  current spikes at high volume; if sound crackles or the Pico browns
  out, add a 220–470 µF electrolytic capacitor across the module's
  VCC/GND, close to the module. (README previously listed 3V3 power;
  5 V per the upstream docs gives the amp proper headroom.)

## Wiring polarity (flip in `config.py` if a sensor reads backwards)

| Constant | Meaning | Default |
|---|---|---|
| `IR_BEAM_SEEN_VALUE` | receiver value when the beam is SEEN | 0 |
| `BUSY_ACTIVE` | BUSY value while a sound is playing | 1 |
