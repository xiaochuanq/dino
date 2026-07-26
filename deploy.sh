#!/usr/bin/env bash
# Deploy the Dino bin robot to an attached Pico 2 / 2 W.
set -euo pipefail
cd "$(dirname "$0")"

mpremote cp -r lib :
mpremote cp main.py config.py :
echo "Deployed. main.py runs on next power-up."
echo "Watch it now with:  mpremote repl  (then Ctrl-D to soft-reboot)"
