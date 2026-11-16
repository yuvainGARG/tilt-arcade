# Tilt Arcade

> **Made with AI - this project is vibecoded.** All the code, the controller firmware, the 3D-printed
> case files and this README were written by an AI (Claude) from my ideas and testing. I built and
> played it on real hardware, but I didn't hand-write the code, so expect rough edges.

Tilt games for the **Raspberry Pi 5**, played with **ESP32 + ADXL345** controllers over Bluetooth.

**Start it:** double-click **Tilt Arcade** on the desktop (or Menu → Games → Tilt Arcade), or:

```bash
python3 arcade.py
```

## Download

Ready-made files are on the **[Releases page](https://github.com/yuvainGARG/tilt-arcade/releases/latest)**:
a Windows app (no Python needed: unzip and run `TiltArcade.exe`), a Raspberry Pi package with an installer
(`bash install_pi.sh`), ready-made controller firmware for both boards (flash from the browser), and the case files.

### On Windows (or another computer)

Needs Python 3.10+ and a PC with Bluetooth (Bluetooth LE).

```
pip install -r requirements.txt
python arcade.py
```

Add `--window` to play in a window instead of fullscreen. The controllers connect over Bluetooth on their own, the same as on the Pi (don't pair them in Windows settings). With no controllers, the keyboard works: WASD and the arrow keys.

## Games

At the top of the menu, **Random 1P game**, **Random 2P game** (versus) and **Random Co-op game** spin through that group of games and pick one for you.
Games with maps or levels ask you to pick one first (tilt forward/back, hold RIGHT to play, hold LEFT to go back).

| Game | Players | How it works | Maps / levels |
|---|---|---|---|
| Tilt Dodge | 1 | Steer left/right, dodge falling blocks, grab coins. Speeds up. | |
| Maze Time Trial | 1 | Fastest run through the marble maze. | Classic, Zigzag, Pillars, Columns |
| Coin Rush | 1 | Grab coins for 45 s while new holes open up. | Classic, Open Floor, Crossroads, Rooms |
| Tilt Snake | 1 | Eat apples, grow, don't bite yourself. Gold apples = 3. | Open, Walled, Obstacles, Tunnels |
| Brick Breaker | 1 | Tilt the paddle, clear the bricks. Catch W / + capsules. | 6 levels, then they loop faster |
| Cave Flyer | 1 | Fly through an endless cave that narrows and speeds up. | |
| Pong vs CPU | 1 | Tilt forward/back to move your paddle. First to 7. | Easy, Normal, Hard |
| Hole Maze | 1 | Wooden tilt labyrinth: reach the goal without dropping into a hole. Flags are checkpoints. Total time saved. | First Steps, Zig Zag, Holey Moley, Spiral, Tightrope |
| Meteor Storm | 1 | Dodge meteors flying across the arena, grab stars. | |
| Fruit Catch | 1 | Slide the basket, catch fruit (1/2/5), avoid bombs. 60 s. | |
| Highway | 1 | Weave through traffic; tilt up to go faster, grab coins. | |
| Star Shooter | 1 | Auto-fire space shooter. Waves, a boss every 5th wave. Blue capsules stack guns: 2x, 3x ... 5x, no timer, lost when you die. + is an extra life. | |
| Lap Race Time Trial | 1 | 3 laps clockwise against the clock. Mud slows, boost pads speed up. | Oval, Chicane, Pinball |
| Target Rush | 1 | Hit targets fast for combos in 40 s. Red X spots cost 3 s. | |
| Balance Beam | 1 | Tip the beam to keep the ball in the moving zone. Wind gusts! | |
| Marble Race | 2 | Race down mirrored mazes, first to 3 goals. | same 4 mazes |
| Sumo | 2 | Knock the other marble off. First to 3. | Classic Ring, Square, Donut, Ice Rink |
| Coin Rush VS | 2 | Most coins in 45 s wins. Bump the other player into holes. | same 4 arenas |
| Marble Hockey | 2 | Smash the puck into their goal. First to 5. | |
| Paint Wars | 2 | Paint more of the floor in 45 s. Stars splat a big area. | |
| Hot Potato | 2 | Bump to pass the bomb. Holding it when it blows loses. First to 3. | |
| Trail Duel | 2 | You leave a wall behind you. Make them crash. First to 3. | |
| Pong | 2 | BLUE left paddle, RED right. First to 7. | |
| Cave Flyer VS | 2 | Same cave, bump the other ship into the rock. First to 3. | |
| Meteor Storm VS | 2 | Last marble standing. First to 3. | |
| Fruit Catch VS | 2 | Two baskets, one sky. Most points in 60 s. | |
| Tank Duel | 2 | Tilt to drive, auto-fire, shells bounce once. First to 5. | Bunkers, Corridors, Open Field |
| King of the Hill | 2 | Score while you're alone in the zone. First to 20 s. | |
| Lap Race | 2 | 3 laps, bumping allowed. | Oval, Chicane, Pinball |
| Target Rush VS | 2 | Race to the same target. First to 15. | |
| **Co-op** (team up, shared score) | | | |
| Star Shooter Co-op | 2 | Two ships, shared lives and score. A blue capsule gives both ships +1 gun (up to 5x); when a ship dies, only that ship drops back to 1x. | |
| Tether | 2 | Your marbles are tied with a rope. Get both into the goal; one falls, you both restart. Team time saved. | First Knot, Two Lanes, Swiss Cheese, The Gate |
| Laser Link | 2 | A laser joins your marbles. Sweep it across the bugs before they touch you. Gold bugs = +1 life. | |
| Core Defense | 2 | Squash the slimes before they reach the crystal. Big slimes take 2 hits. Waves. | |
| Switch Vault | 2 | Puzzle: doors stay open only while someone sits on the same-colour plate. Team time saved. | Hold the Door, Leapfrog, Four Rooms, Crossed Wires |
| Paint Together | 2 | Paint 75% of the floor before time runs out. Bump the eraser robots to stun them. | endless levels, +1 robot each |
| Meteor Storm Co-op | 2 | Survive together. If one is hit, the other rolls onto the ghost to revive them. | |

Best scores are saved in `scores.json`.

## Controls

| | Controller | Keyboard |
|---|---|---|
| Menu: choose | tilt forward / back | ↑ ↓ |
| Menu: start | hold tilt RIGHT (bar fills) | Enter |
| Game over: play again | hold tilt RIGHT | Space |
| Game over: back to menu | hold tilt LEFT | Esc |
| Quit | pick "Quit" in the menu | Esc in the menu |

Keyboard play: **WASD** for blue, **arrow keys** for red. In 1-player games, either set works. `F11` toggles fullscreen.
1-player games use whichever controller is connected (blue first).

## Controllers

| Player | Board | Port when plugged in |
|---|---|---|
| 1 (BLUE) | ESP32-S3 | `/dev/ttyACM0` |
| 2 (RED) | ESP32 38-pin | `/dev/ttyUSB0` |

### ADXL345 wiring

| ADXL345 pin | ESP32-S3 | ESP32 38-pin |
|---|---|---|
| VCC | 3V3 | 3V3 |
| GND | GND | GND |
| SDA | GPIO 8 | GPIO 21 |
| SCL | GPIO 9 | GPIO 22 |
| CS  | 3V3 | 3V3 |
| SDO | GND | GND |

Hold each controller **flat** when it powers on, because it calibrates then. Press **BOOT** to recalibrate.

### Re-flashing

```bash
~/.local/bin/arduino-cli compile --fqbn esp32:esp32:esp32s3 --output-dir build-s3 MarbleController && ~/.local/bin/arduino-cli upload --fqbn esp32:esp32:esp32s3 -p /dev/ttyACM0 --input-dir build-s3 MarbleController
```

```bash
~/.local/bin/arduino-cli compile --fqbn esp32:esp32:esp32 --build-property "compiler.cpp.extra_flags=-DPLAYER_ID=2" --output-dir build-p2 MarbleController && ~/.local/bin/arduino-cli upload --fqbn esp32:esp32:esp32 -p /dev/ttyUSB0 --input-dir build-p2 MarbleController
```

### Also works with PCMonitorX

The same controllers can play portrait versions of these games (Dodge, Catch, Highway, Star Shooter,
Cave Flyer, Pong) on a small ESP32-S3 touch display: **[PCMonitorX](https://github.com/yuvainGARG/pcmonitorx)**,
a desk PC monitor with apps and games. The controllers connect to it directly over Bluetooth, with no Pi needed.
A controller connects to one device at a time, so close the arcade first.

## 3D-printed cases

`case/` has a screw-together case for each controller (base + lid), already sized for each board:

| File | For |
|---|---|
| `P1_ESP32-S3_base.stl` / `_lid.stl` | ESP32-S3, ~65 x 25 mm board (one dot on the lid), case 101 x 47 x 33 mm |
| `P2_ESP32-38pin_base.stl` / `_lid.stl` | ESP32 38-pin, ~50 x 25 mm board (two dots), case 86 x 47 x 33 mm |

- **Screws:** 4 x M3 x 12 mm countersunk (flat head) per case. They self-tap into the corner posts.
  For heat-set inserts, set `INSERTS = True` in `case/make_cases.py`.
- **Inside:** the ESP32 sits on two supports 21 mm up, so jumper wires fit underneath. The USB port faces the slot
  in the end wall. The ADXL345 drops into the pocket at the other end, pins facing the ESP32;
  fix it with double-sided tape or hot glue so it can't move.
- **Printing:** base opening up, lid outer face down (as they import). PLA or PETG, 0.2 mm layers,
  15-20 % infill, no supports needed.
- **Doesn't fit?** Measure your board, change `BOARDS` in `case/make_cases.py`, then run
  `python3 case/make_cases.py`.
- After mounting the ADXL in the case, if a direction is wrong, fix it on the **Settings** page in the arcade.

## Tuning (`tiltlib.py`)

- **Moves the wrong way / holding it sideways / players swapped?** Use **Settings** at the bottom of the arcade menu:
  pick which board is player 1, player 1's colour, and for each board how you hold it
  (normal, sideways left/right, upside down) and whether up/down or left/right is inverted.
  Each board has a live test box: tilt it and the dot should go the same way. Saved in `settings.json`.
- **Too sensitive or too sluggish?** Change `SENSITIVITY`.

## Files

`arcade.py` menu · `settings_page.py` controller settings · `tiltlib.py` shared code (Bluetooth, physics, drawing, map picker, scores) · one file per game (`dodge.py`, `marble_race.py`, `coins.py`, `snake.py`, `bricks.py`, `cave.py`, `pong.py`, `sumo.py`, `hockey.py`, `paint.py`, `potato.py`, `trail_duel.py`, `hole_maze.py`, `meteor.py`, `catch.py`, `highway.py`, `shooter.py`, `laprace.py`, `targets.py`, `balance.py`, `tanks.py`, `koth.py`, co-op: `tether.py`, `laser.py`, `defend.py`, `vault.py`, `paint_coop.py`) · `MarbleController/` ESP32 sketch · `case/` 3D-printed cases

## License

Copyright (C) 2026 yuvainGARG. Tilt Arcade (code, 3D models and docs) is licensed under
**[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/)**:

- **You can** build it, use it, change it and share it for free.
- **Give credit**: link back to this repo.
- **Non-commercial**: no selling devices, kits, cases or products that use it without my written
  permission. Ask me if you would like to.
- **Share alike**: if you share a changed version, use the same license.

Full text: [LICENSE](LICENSE). Versions published before this change were briefly GPL-3.0.
