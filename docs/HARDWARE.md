# Dino — Hardware Summary

Devices, pin assignments, and wiring for the smart bin robot. Pin numbers
are the single source of truth in `config.py`; this file mirrors them.

Driver `lib/dysv17f.py` is imported from the
[pico-droid](../../pico-droid) project — re-copy it from there when that
project updates it (last synced 2026-07-30).

## Devices

| Device | Role | Interface |
|---|---|---|
| Raspberry Pi Pico 2 / 2 W | Controller running MicroPython (`main.py`) | — |
| DY-SV17F voice module | Plays pass voice + full-bin beep from its own 4 MB flash; built-in 3–5 W amp | UART0 @ 9600 baud + BUSY GPIO |
| 4–8 Ω speaker | Sound output | DY-SV17F SPK+/SPK− terminals |
| LED(s) | Lit while voice plays; flash during full-bin alert | GPIO (one pin per LED, all switched together) |
| IR emitter LED | One side of the beam across the bin opening | GPIO (through 220 Ω) |
| IR receiver | Reads the beam — a short block = something dropped in (voice); blocked ≥ 60 s = bin FULL (alert) | GPIO input |

## Pico pin assignments

| GP pin | Config constant | Function |
|---|---|---|
| GP0 | `UART_TX_PIN` | UART0 TX → DY-SV17F RX |
| GP1 | `UART_RX_PIN` | UART0 RX ← DY-SV17F TX |
| GP2 | `BUSY_PIN` | DY-SV17F BUSY input (high while playing, `BUSY_ACTIVE = 1`) |
| GP4 | `LED_PINS` | LED output (add more GP numbers to the list for more LEDs) |
| GP5 | `IR_EMIT_PIN` | IR emitter output (pulsed 5 ms per 50 ms tick) |
| GP6 | `IR_RECV_PIN` | IR receiver input (`IR_BEAM_SEEN_VALUE = 0`) |

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
| GP6 | IR receiver OUT | Module: VCC → 3V3 (not 5 V), OUT → GP6 direct. Bare phototransistor: collector → GP6 + **10 kΩ pull-up to 3V3**, emitter → GND (code enables no internal pull-up) |
| 3V3 / GND | Sensor power | IR receiver parts |

### DY-SV17F setup

- Mode straps for UART control: **CON1=0, CON2=0, CON3=1** — i.e. CON1
  and CON2 to GND and CON3 to 3.3 V (the module's V33 pin), each through
  a **10 kΩ resistor**. Use resistors, not direct ties: CON3 is dual-use
  (module pin 12) and becomes the **BUSY output** after boot, so it must
  stay free to be driven — wire it to Pico GP2. If busy reads inverted
  on your board, flip `BUSY_ACTIVE` in `config.py`.
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
