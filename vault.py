#!/usr/bin/env python3
"""
Switch Vault (2 players, co-op puzzle) - coloured doors only stay open while
someone is sitting on the plate of the same colour. Take turns holding doors
for each other and get BOTH marbles onto the green goal. 4 vaults; your team
time is saved (lower is better).

Run on its own:  python3 vault.py [--fullscreen]
"""

import math

import pygame

import tiltlib as tl

CELL = 16.0
R = 5.0
SUBSTEPS = 5
PLATE_R = 8.0
DOOR_COL = {"a": (240, 150, 50), "b": (90, 210, 110), "c": (180, 110, 240), "d": (70, 200, 230)}

# 20 x 15.  # wall  1 2 starts  a-d plates  A-D doors  G goal  . floor
LEVELS = [
    ("Hold the Door", [
        "####################",
        "#1.......#.........#",
        "#........#.........#",
        "#...a....A.........#",
        "#........A....b....#",
        "#2.......#.........#",
        "#####BB###.........#",
        "#........#.........#",
        "#........#.........#",
        "#...GG...C.........#",
        "#...GG...C.........#",
        "#........#.........#",
        "#....c...#.........#",
        "#........#.........#",
        "####################"]),
    ("Leapfrog", [
        "####################",
        "#......#......#....#",
        "#.1....#......#....#",
        "#......#..a...#....#",
        "#......A......B....#",
        "#..a...A......B.GG.#",
        "#......#......#.GG.#",
        "#.2....#..b...#....#",
        "#......#......#.b..#",
        "#......#......#....#",
        "#......#......#....#",
        "#......#......#....#",
        "#......#......#....#",
        "#......#......#....#",
        "####################"]),
    ("Four Rooms", [
        "####################",
        "#1.......#.........#",
        "#........#.........#",
        "#........A.........#",
        "#....b...A.........#",
        "#2.......#.........#",
        "#........#.........#",
        "###BB#########CC####",
        "#........#.........#",
        "#..a.....#.........#",
        "#........D....GG...#",
        "#......c.D....GG...#",
        "#........#.......d.#",
        "#........#.........#",
        "####################"]),
    ("Crossed Wires", [
        "####################",
        "#1....#.....#......#",
        "#.....#..a..#..b...#",
        "#.....A.....B......#",
        "#.....A.....B......#",
        "#..c..#.....#..d...#",
        "#2....#..b..#......#",
        "###CC##.....##DD####",
        "#..c..#.....#......#",
        "#.....#.....#......#",
        "#.....#.....#..GG..#",
        "#..a..#.....#..GG..#",
        "#.....#.....#....d.#",
        "#.....#.....#......#",
        "####################"]),
]


def parse(rows):
    walls, doors, plates, goal = [], {}, [], []
    starts = {}
    for r, row in enumerate(rows):
        assert len(row) == 20, (r, row)
        for c, ch in enumerate(row):
            x, y = c * CELL, r * CELL
            if ch == "#":
                walls.append((x, y, CELL, CELL))
            elif ch in "ABCD":
                doors.setdefault(ch.lower(), []).append((x, y, CELL, CELL))
            elif ch in "abcd":
                plates.append((ch, x + CELL / 2, y + CELL / 2))
            elif ch == "G":
                goal.append((x, y, CELL, CELL))
            elif ch in "12":
                starts[int(ch)] = (x + CELL / 2, y + CELL / 2)
    gx0 = min(g[0] for g in goal)
    gy0 = min(g[1] for g in goal)
    gx1 = max(g[0] + g[2] for g in goal)
    gy1 = max(g[1] + g[3] for g in goal)
    return walls, doors, plates, (gx0, gy0, gx1 - gx0, gy1 - gy0), starts


def overlaps(b, rect):
    x, y, w, h = rect
    cx, cy = min(max(b.x, x), x + w), min(max(b.y, y), y + h)
    return math.hypot(b.x - cx, b.y - cy) < b.r


class Vault:
    def __init__(self):
        self.level = 0
        self.total = 0.0
        self.t = 0.0
        self.record = None
        self.load()

    @property
    def over(self):
        return self.state == "over"

    def load(self):
        name, rows = LEVELS[self.level]
        self.name = name
        self.walls, self.doors, self.plates, self.goal, starts = parse(rows)
        self.balls = {p: tl.Ball(*starts[p], r=R, color=tl.PLAYER_COL[p], p=p) for p in (1, 2)}
        self.open = {k: False for k in self.doors}
        self.door_amt = {k: 0.0 for k in self.doors}
        self.pressed = set()
        self.level_time = 0.0
        self.state, self.timer = "ready", 1.5

    def in_goal(self, b):
        x, y, w, h = self.goal
        return x + 2 < b.x < x + w - 2 and y + 2 < b.y < y + h - 2

    def step(self, dt, tilts):
        self.t += dt
        if self.state == "ready":
            self.timer -= dt
            if self.timer <= 0:
                self.state = "play"
            return
        if self.state == "cleared":
            self.timer -= dt
            if self.timer <= 0:
                self.level += 1
                if self.level >= len(LEVELS):
                    self.state = "over"
                    self.record = tl.submit("vault_time", round(self.total, 2), higher_better=False)
                else:
                    self.load()
            return
        if self.state != "play":
            return
        self.level_time += dt
        self.total += dt
        bl = list(self.balls.values())

        # plates -> doors.  A door stays open while a marble is still in the doorway.
        self.pressed = {k for k, px, py in self.plates
                        if any(math.hypot(b.x - px, b.y - py) < PLATE_R for b in bl)}
        for k, rects in self.doors.items():
            blocked = any(overlaps(b, r) for b in bl for r in rects)
            self.open[k] = k in self.pressed or (self.open[k] and blocked)
            target = 1.0 if self.open[k] else 0.0
            self.door_amt[k] += (target - self.door_amt[k]) * min(1.0, 12 * dt)

        solid = self.walls + [r for k, rects in self.doors.items() if not self.open[k] for r in rects]
        h = dt / SUBSTEPS
        for _ in range(SUBSTEPS):
            for b in bl:
                tl.integrate(b, tilts[b.p], h, accel=360, friction=2.0, max_speed=170)
                c0, r0 = b.x // CELL, b.y // CELL
                for w in solid:
                    if abs(w[0] // CELL - c0) <= 1 and abs(w[1] // CELL - r0) <= 1:
                        tl.collide_rect(b, w, bounce=0.25)
            tl.collide_balls(bl[0], bl[1], restitution=0.5)
        for b in bl:
            b.trail.append((b.x, b.y))
            del b.trail[:-5]
        if all(self.in_goal(b) for b in bl):
            self.state, self.timer = "cleared", 1.8


def draw(view, g, ctrl, end):
    view.update()
    scr, W, H = view.screen, view.W, view.H
    scr.fill(tl.C_BG)
    view.field((44, 46, 58))
    for r in range(15):
        for c in range(20):
            if (r + c) % 2:
                pygame.draw.rect(scr, (48, 50, 63), (*view.P(c * CELL, r * CELL), view.L(CELL) + 1, view.L(CELL) + 1))
    gx, gy, gw, gh = g.goal
    pygame.draw.rect(scr, (20, 110, 50), (*view.P(gx, gy), view.L(gw), view.L(gh)), border_radius=int(view.L(4)))
    pygame.draw.rect(scr, tl.C_GOAL, (*view.P(gx, gy), view.L(gw), view.L(gh)), max(2, int(view.L(1.5))),
                     border_radius=int(view.L(4)))
    for k, px, py in g.plates:
        col = DOOR_COL[k]
        on = k in g.pressed
        pygame.draw.circle(scr, tuple(c // 3 for c in col), view.P(px, py), view.L(PLATE_R))
        pygame.draw.circle(scr, col, view.P(px, py), view.L(PLATE_R - (3 if on else 1.5)), 0 if on else 2)
    for w in g.walls:
        pygame.draw.rect(scr, tl.C_WALL, (*view.P(w[0], w[1]), view.L(w[2]) + 1, view.L(w[3]) + 1))
    for k, rects in g.doors.items():
        col = DOOR_COL[k]
        amt = g.door_amt[k]
        for x, y, w, hh in rects:
            if amt > 0.95:
                pygame.draw.rect(scr, tuple(c // 4 for c in col), (*view.P(x, y), view.L(w) + 1, view.L(hh) + 1), 1)
                continue
            # bars slide away as the door opens
            shrink = amt * 0.5
            rx, ry = x + w * shrink * (1 if w <= hh else 0), y + hh * shrink * (1 if hh < w else 0)
            rw, rh = (w * (1 - amt) if w <= hh else w), (hh * (1 - amt) if hh < w else hh)
            pygame.draw.rect(scr, col, (*view.P(rx, ry), view.L(rw) + 1, view.L(rh) + 1))
            pygame.draw.rect(scr, tuple(c // 2 for c in col), (*view.P(rx, ry), view.L(rw) + 1, view.L(rh) + 1), 1)
    if g.state != "over":
        for b in g.balls.values():
            view.ball(b)

    tl.hud_solo(view, f"{g.total:.1f} s", f"Vault {min(g.level + 1, len(LEVELS))}: {g.name}",
                "vault_time", "{:.1f} s")
    if g.state == "ready" and g.level == 0:
        view.text("sit on a plate to open its door - help each other to the goal", tl.C_TEXT, (W / 2, H * 0.94), 0.04)
    elif g.state == "cleared":
        view.panel(0.22)
        view.text(f"VAULT {g.level + 1} OPEN  -  {g.level_time:.1f} s", tl.C_GOAL, (W / 2, H / 2), 0.08)
    elif g.over:
        tl.draw_solo_result(view, f"{g.total:.1f} s", g.record, "{:.1f} s")
    if end:
        end.draw(view, 0.75)


def run(ctrl):
    tl.game_loop(ctrl, Vault, draw)


if __name__ == "__main__":
    tl.run_standalone(run)
