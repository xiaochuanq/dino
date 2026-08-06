# Dino — Smart Donation Bin Robot

A MicroPython robot for a Raspberry Pi Pico 2 / 2 W on a donation bin.
Dino watches with a laser tape-measure and an invisible IR light beam:

- Someone walks by (1.5–3 m) → a random funny noise (then a cooldown).
- Someone comes close (< 1 m) → a random greeting, once per visit.
- They walk away (> 1.5 m) → a random goodbye.
- They push the lid flap while standing close → a random thank-you.
- The lid is stuck open 60 s → the bin is FULL → complaints every 10 s
  until it closes.
- Eyes glow steadily, and blink while Dino talks.

Design spec: `docs/superpowers/specs/2026-08-06-kid-friendly-parts-design.md`

## How the code thinks (read `main.py`!)

Dino has four body parts — `visitor`, `lid`, `voice`, `eyes` — and one
loop with three steps every tick:

1. **SENSE** — each part looks at the world and updates its state.
2. **DECIDE** — simple ifs turn states into human events.
3. **ACT** — the `on_...()` functions say what Dino does. **Edit these!**

## Wiring

| Pico pin | Goes to |
|---|---|
| GP0 (UART0 TX) | DY-SV17F RX |
| GP1 (UART0 RX) | DY-SV17F TX |
| GP2 | DY-SV17F CON3 (doubles as BUSY output in UART mode) |
| GP4 | Both eye LEDs in parallel, each through its own resistor → GND |
| GP5 | IR emitter LED (+ 220 Ω resistor) |
| GP6, GP7, GP8 | IR receiver outputs |
| GP14 / GP15 | VL53L1X SDA / SCL (I2C1) |
| VBUS (5 V) / GND | DY-SV17F power (UART is 3.3 V-safe) |
| 3V3 / GND | VL53L1X power |

DY-SV17F straps for UART mode: CON1=0, CON2=0, CON3=1. Speaker on the
module's speaker terminals.

## Sounds

Connect the DY-SV17F over USB and copy WAV files named `00001.wav`,
`00002.wav`, … onto it. Each mood is a list of track numbers in
`config.py` — Dino picks one at random every time:

| List | Played when |
|---|---|
| `GREETING_TRACKS` | someone comes close |
| `GOODBYE_TRACKS` | they walk away |
| `THANKS_TRACKS` | they push the lid |
| `PASSING_TRACKS` | someone walks by |
| `FULL_TRACKS` | the bin is stuffed full |

Add a sound = copy the file + add its number to a list.

Manners: greetings, goodbyes and thank-yous are *important* — they
interrupt whatever is playing. Passing noises and complaints are
*polite* — they skip their turn if Dino is already talking.

## Tuning (edit `config.py`)

| Constant | What it does | Default |
|---|---|---|
| `HERE_MM` | closer than this = the visitor is here | 1000 |
| `LEAVE_MM` | farther than this = they left (hysteresis gap) | 1500 |
| `PASSING_MM` | outer edge of the walking-by band | 3000 |
| `PASSING_COOLDOWN_S` | quiet time between passing noises | 30 |
| `LID_PUSH_MAX_MS` | lid open shorter than this = a push | 2000 |
| `FULL_AFTER_S` | lid open this long = FULL | 60 |
| `COMPLAIN_EVERY_S` | seconds between complaints while FULL | 10 |
| `TALK_BLINK_MS` | eye blink speed while talking | 250 |
| `VOLUME` | loudness 0–30 | 30 |

If the beam reads backwards, flip `IR_BEAM_SEEN_VALUE`.

## Deploy

```bash
./deploy.sh        # copies lib/, main.py, config.py to the Pico
mpremote repl      # watch it run (Ctrl-D to soft-reboot)
```

If a Pico was deployed before this rewrite, remove the retired module
once: `mpremote rm :lib/bin_watch.py`

## Check the wiring one piece at a time

```bash
mpremote run examples/02_test_ir.py       # IR beam (prints state)
mpremote run examples/03_test_sound.py    # sound + LEDs
mpremote run examples/09_test_laser.py    # laser distance sensor
```

## Desktop tests (no hardware needed)

```bash
pip install -r requirements-dev.txt
python3 -m pytest tests/ -v
```
