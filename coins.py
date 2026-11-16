#!/usr/bin/env python3
"""
Coin Rush - roll around the arena grabbing coins before time runs out.
New holes keep opening up (they blink orange before they're live).
Gold coin = 1, blue gem = 3. Falling in a hole costs you time.

  1 player: best score is saved.
  2 players: most coins wins. Bump the other marble into a hole!

Run on its own:  python3 coins.py [--fullscreen] [--vs]
"""

import math
import random
import sys

import pygame

import tiltlib as tl

ROUND_TIME = 45.0
R = 6.0
HOLE_R = 9.0
HOLE_WARN = 1.5     # seconds a new hole blinks before it's dangerous
FALL_TIME = 0.8
SUBSTEPS = 4
NUM_COINS = 4

BORDER = [(0, 0, 320, 4), (0, 236, 320, 4), (0, 0, 4, 240), (316, 0, 4, 240)]
MAPS = [
    dict(name="Classic", desc="Four bars and a centre block",
         walls=[(70, 60, 30, 8), (220, 60, 30, 8), (70, 172, 30, 8), (220, 172, 30, 8), (152, 104, 16, 32)]),
    dict(name="Open Floor", desc="Nothing to hide behind",
         walls=[]),
    dict(name="Crossroads", desc="A big plus sign splits the arena",
         walls=[(60, 116, 80, 8), (180, 116, 80, 8), (156, 30, 8, 70), (156, 140, 8, 70)]),
    dict(name="Rooms", desc="Four rooms with doorways",
         walls=[(100, 4, 8, 80), (212, 4, 8, 80), (100, 156, 8, 80), (212, 156, 8, 80), (130, 116, 60, 8)]),
]


def map_names():
    return [(m["name"], m["desc"]) for m in MAPS]
STARTS = {1: (40, 120), 2: (280, 120)}


class Rush:
    def __init__(self, solo, map_i=0):
        self.solo = solo
        self.map_i = map_i
        self.walls = BORDER + MAPS[map_i]["walls"]
        players = [1] if solo else [1, 2]
        self.balls = {p: tl.Ball(*STARTS[p], r=R, color=tl.PLAYER_COL[p], p=p) for p in players}
        self.score = {p: 0 for p in players}
        self.coins = []     # [x, y, value]
        self.holes = []     # [x, y, age]
        self.pops = []      # [x, y, text, ttl, colour]
        self.time_left = ROUND_TIME
        self.hole_timer = 5.0
        self.t = 0.0
        self.state = "countdown"
        self.timer = 3.0
        self.record = None
        self.winner = None
        for _ in range(NUM_COINS):
            self.spawn_coin()

    def free_spot(self, margin):
        for _ in range(100):
            x, y = random.uniform(16, 304), random.uniform(16, 224)
            if any(wx - margin < x < wx + w + margin and wy - margin < y < wy + h + margin
                   for wx, wy, w, h in self.walls):
                continue
            if any(math.hypot(x - hx, y - hy) < 24 for hx, hy, _a in self.holes):
                continue
            if any(math.hypot(x - b.x, y - b.y) < 30 for b in self.balls.values()):
                continue
            if any(math.hypot(x - sx, y - sy) < 30 for sx, sy in STARTS.values()):
                continue
            if any(math.hypot(x - cx, y - cy) < 20 for cx, cy, _v in self.coins):
                continue
            return x, y
        return None

    def spawn_coin(self):
        spot = self.free_spot(8)
        if spot:
            self.coins.append([*spot, 3 if random.random() < 0.12 else 1])

    def step(self, dt, tilts):
        self.t += dt
        for p in self.pops:
            p[1] -= 25 * dt
            p[3] -= dt
        self.pops = [p for p in self.pops if p[3] > 0]
        if self.state == "countdown":
            self.timer -= dt
            if self.timer <= 0:
                self.state = "play"
            return
        if self.state != "play":
            return

        self.time_left -= dt
        self.hole_timer -= dt
        if self.hole_timer <= 0 and len(self.holes) < 8:
            self.hole_timer = 6.0
            spot = self.free_spot(14)
            if spot:
                self.holes.append([*spot, 0.0])
        for h in self.holes:
            h[2] += dt

        balls = list(self.balls.values())
        hstep = dt / SUBSTEPS
        for _ in range(SUBSTEPS):
            for b in balls:
                if b.falling > 0:
                    continue
                tl.integrate(b, tilts[b.p], hstep)
                for w in self.walls:
                    tl.collide_rect(b, w)
            if len(balls) == 2:
                tl.collide_balls(balls[0], balls[1], restitution=0.95)
            for b in balls:
                if b.falling > 0:
                    continue
                for hx, hy, age in self.holes:
                    if age >= HOLE_WARN and math.hypot(b.x - hx, b.y - hy) < HOLE_R - 1:
                        b.falling = FALL_TIME
                        b.x, b.y, b.vx, b.vy = hx, hy, 0.0, 0.0
                        b.trail = []
                        break
                if b.falling > 0:
                    continue
                for c in self.coins[:]:
                    if math.hypot(b.x - c[0], b.y - c[1]) < R + 5:
                        self.coins.remove(c)
                        self.score[b.p] += c[2]
                        col = (120, 200, 255) if c[2] == 3 else tl.C_GOLD
                        self.pops.append([c[0], c[1], f"+{c[2]}", 0.8, col])
                        self.spawn_coin()
        for b in balls:
            if b.falling > 0:
                b.falling -= dt
                if b.falling <= 0:
                    b.respawn()
            else:
                b.trail.append((b.x, b.y))
                del b.trail[:-8]
        while len(self.coins) < NUM_COINS and self.free_spot(8):
            self.spawn_coin()

        if self.time_left <= 0:
            self.time_left = 0
            self.state = "over"
            if self.solo:
                self.record = tl.submit("coins_best", self.score[1])
            elif self.score[1] != self.score[2]:
                self.winner = 1 if self.score[1] > self.score[2] else 2


def draw(view, g, ctrl, end):
    view.update()
    scr, W, H = view.screen, view.W, view.H
    scr.fill(tl.C_BG)
    view.field()
    for hx, hy, age in g.holes:
        if age < HOLE_WARN:
            if int(age * 6) % 2 == 0:
                pygame.draw.circle(scr, (240, 140, 40), view.P(hx, hy), view.L(HOLE_R * age / HOLE_WARN + 2),
                                   max(1, int(view.s)))
        else:
            view.hole(hx, hy, HOLE_R)
    for w in g.walls:
        view.wall(w)
    for x, y, v in g.coins:
        bob = math.sin(g.t * 5 + x) * 0.8
        if v == 3:
            pts = [view.P(x, y - 6 + bob), view.P(x + 5, y + bob), view.P(x, y + 6 + bob), view.P(x - 5, y + bob)]
            pygame.draw.polygon(scr, (120, 200, 255), pts)
            pygame.draw.polygon(scr, (220, 240, 255), pts, max(1, int(view.s / 2)))
        else:
            pygame.draw.circle(scr, (150, 110, 20), view.P(x, y + bob), view.L(5))
            pygame.draw.circle(scr, tl.C_GOLD, view.P(x, y + bob), view.L(4))
    for b in g.balls.values():
        view.ball(b, b.falling / FALL_TIME if b.falling > 0 else 1.0)
    for x, y, txt, ttl, col in g.pops:
        view.text(txt, col, view.P(x, y), 0.045)

    hy = view.hud * 0.42
    tcol = (240, 90, 90) if g.time_left < 10 and g.state == "play" else tl.C_TEXT
    view.text(f"{math.ceil(g.time_left)}s", tcol, (W / 2, hy), 0.07)
    if g.solo:
        bt = tl.best("coins_best")
        view.text(f"COINS  {g.score[1]}", tl.C_GOLD, (W * 0.2, hy), 0.06)
        view.text(f"best {bt}" if bt is not None else "no best yet", tl.C_DIM, (W * 0.8, hy), 0.045)
    else:
        for p, side in ((1, 0.2), (2, 0.8)):
            view.text(f"{tl.PLAYER_NAME[p]}  {g.score[p]}", tl.PLAYER_COL[p], (W * side, hy), 0.06)
            view.text(ctrl.label(p), tl.C_TEXT if ctrl.connected(p) else tl.C_DIM,
                      (W * side, view.hud * 0.85), 0.032)

    if g.state == "countdown":
        n = math.ceil(g.timer)
        view.text(str(n) if n > 0 else "GO!", tl.C_TEXT, (W / 2, H * 0.45), 0.22)
        view.text("grab coins - avoid holes", tl.C_DIM, (W / 2, H * 0.62), 0.045)
    elif g.state == "over":
        view.panel(0.6)
        if g.solo:
            is_new, rec = g.record
            view.text(f"{g.score[1]} coins", tl.C_GOLD, (W / 2, H * 0.36), 0.14)
            view.text("NEW HIGH SCORE!" if is_new else f"best: {rec}",
                      tl.C_GOLD if is_new else tl.C_DIM, (W / 2, H * 0.53), 0.06)
        else:
            if g.winner:
                view.text(f"{tl.PLAYER_NAME[g.winner]} WINS!", tl.PLAYER_COL[g.winner], (W / 2, H * 0.36), 0.16)
            else:
                view.text("DRAW!", tl.C_TEXT, (W / 2, H * 0.36), 0.16)
            view.text(f"{g.score[1]} - {g.score[2]}", tl.C_TEXT, (W / 2, H * 0.53), 0.07)
    if end:
        end.draw(view, 0.72)


def run(ctrl, solo=True, map_i=None):
    if map_i is None:
        map_i = tl.pick(ctrl, "Coin Rush - pick an arena", map_names())
        if map_i is None:
            return
    view = tl.View()
    clock = pygame.time.Clock()
    g, end = Rush(solo, map_i), None
    while True:
        dt = min(clock.tick(60) / 1000.0, 1 / 30)
        keys = tl.events()
        if pygame.K_ESCAPE in keys and g.state != "over":
            return
        tilts = {1: tl.solo_tilt(ctrl)} if solo else {p: tl.player_tilt(ctrl, p) for p in (1, 2)}
        g.step(dt, tilts)
        if g.state == "over":
            end = end or tl.EndChoice()
            choice = end.update(ctrl, dt, keys)
            if choice == "again":
                g, end = Rush(solo, map_i), None
            elif choice == "menu":
                return
        draw(view, g, ctrl, end)
        pygame.display.flip()


if __name__ == "__main__":
    tl.run_standalone(run, solo="--vs" not in sys.argv)
