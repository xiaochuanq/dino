# Dino — Smart Bin Robot

A MicroPython robot for a Raspberry Pi Pico 2 / 2 W on a bin with a
spring-loaded door:

- Door swings shut → plays a voice clip, LEDs on while it plays.
- IR beam across the bin blocked for 60 s → bin is FULL → beeps and
  flashes the LEDs until the beam is seen again.

Design spec: `docs/superpowers/specs/2026-07-25-dino-bin-robot-design.md`

## Wiring

| Pico pin | Goes to |
|---|---|
| GP0 (UART0 TX) | DY-SV17F RX |
| GP1 (UART0 RX) | DY-SV17F TX |
| GP2 | DY-SV17F BUSY |
| GP3 | Tilt switch (other leg → GND) |
| GP4 | LED (+ resistor → GND). Add more pins to `LED_PINS` for more LEDs |
| GP5 | IR emitter LED (+ resistor) |
| GP6 | IR receiver output |
| 3V3 / GND | Module + sensor power |

DY-SV17F straps for UART mode: CON1=0, CON2=0, CON3=1. Speaker on the
module's speaker terminals.

## Sounds

Connect the DY-SV17F over its USB port and copy two files onto it:

- `00001.wav` — the door voice ("thank you!")
- `00002.wav` — the full-bin beep

The door voice always wins the speaker: a new door close cuts off whatever is playing, and the full-bin beep never interrupts the voice — a skipped beep just waits for the next alert.

## Tuning (edit `config.py`)

| Constant | What it does | Default |
|---|---|---|
| `IR_CHECK_INTERVAL_S` | seconds between beam checks (1–10) | 5 |
| `FULL_AFTER_S` | beam blocked this long → FULL | 60 |
| `ALERT_REPEAT_S` | seconds between alert bursts | 10 |
| `FLASH_COUNT` | flashes per burst | 3 |
| `FLASH_MS` | each flash: ms on, then ms off | 200 |
| `VOLUME` | loudness 0–30 | 25 |

If a sensor reads backwards, flip `DOOR_OPEN_VALUE` or
`IR_BEAM_SEEN_VALUE`.

## Deploy

```bash
./deploy.sh        # copies lib/, main.py, config.py to the Pico
mpremote repl      # watch it run (Ctrl-D to soft-reboot)
```

## Check the wiring one piece at a time

```bash
mpremote run examples/01_test_tilt.py    # door switch
mpremote run examples/02_test_ir.py      # IR beam
mpremote run examples/03_test_sound.py   # sound + LEDs
```

## Desktop tests (no hardware needed)

```bash
pip install -r requirements-dev.txt
python3 -m pytest tests/ -v
```
