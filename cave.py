#!/usr/bin/env python3
"""
Cave Flyer - fly through an endless cave. Tilt forward/back to go down/up.
The cave gets narrower and faster.

1 player: survive as long as you can, grab gems for bonus points.
2 players: both ships fly the same cave. Bump the other ship into the rock!
           Last ship flying wins the round. First to 3.

Run on its own:  python3 cave.py [--fullscreen] [--2p]
"""

import math
import random
import sys

import pygame

import tiltlib as tl

COL = 4.0             # cave column width
SHIP_X = 60.0
SHIP_R = 5.0
WIN_SCORE = 3


class Ship:
    def __init__(self, p, y):
        self.p, self.y, self.vy, self.alive = p, y, 0.0, True


class Cave:
    def __init__(self, solo=True):
        self.solo = solo
        self.score2 = {1: 0, 2: 0}
        self.winner = None
        self.record = None
        self.t = 0.0
        self.start_round()

    def start_round(self):
        self.dist = 0.0
        self.speed = 70.0
        self.ships = {1: Ship(1, 120.0)} if self.solo else {1: Ship(1, 105.0), 2: Ship(2, 135.0)}
        self.gems = []          # [x, y]
        self.gem_points = 0
        self.center, self.cdrift = 120.0, 0.0
        self.cols = []          # [x, top, bottom]
        x = 0.0
        while x < tl.FIELD_W + COL:
            self.add_col(x, warmup=True)
            x += COL
        self.state, self.timer = "countdown", 2.5
        self.round_winner = None
        self.sparks = []

    @property
    def over(self):
        return self.state in ("over", "match")

    @property
    def score(self):
        return int(self.dist / 10) + self.gem_points

    def gap(self):
        if self.solo:
            return max(62.0, 150.0 - self.dist * 0.012)
        return max(72.0, 160.0 - self.dist * 0.012)     # a bit roomier: two ships share it

    def add_col(self, x, warmup=False):
        gap = self.gap()
        if not warmup:
            self.cdrift += random.uniform(-0.45, 0.45)
            self.cdrift = max(-2.2, min(2.2, self.cdrift)) * 0.985
            self.center += self.cdrift
        lo, hi = gap / 2 + 6, tl.FIELD_H - gap / 2 - 6
        if self.center < lo or self.center > hi:
            self.center = max(lo, min(hi, self.center))
            self.cdrift = -self.cdrift * 0.5
        wob = math.sin(x * 0.05) * 3
        self.cols.append([x, self.center - gap / 2 + wob, self.center + gap / 2 + wob])
        if self.solo and not warmup and random.random() < 0.02:
            self.gems.append([x, self.center + random.uniform(-gap / 4, gap / 4)])

    def walls_at(self, x):
        for c in self.cols:
            if c[0] <= x < c[0] + COL:
                return c[1], c[2]
        return 0, tl.FIELD_H

    def burst(self, x, y, n, col, sp=(30, 120), ttl=0.8):
        for _ in range(n):
            a = random.uniform(0, math.tau)
            s = random.uniform(*sp)
            self.sparks.append([x, y, math.cos(a) * s, math.sin(a) * s, ttl, col])

    def crashed(self, s):
        for x in (SHIP_X - SHIP_R, SHIP_X, SHIP_X + SHIP_R):
            top, bot = self.walls_at(x)
            if s.y - SHIP_R * 0.8 < top or s.y + SHIP_R * 0.8 > bot:
                return True
        return False

    def step(self, dt, tilts):
        self.t += dt
        for s in self.sparks:
            s[0] += s[2] * dt
            s[1] += s[3] * dt
            s[4] -= dt
        self.sparks = [s for s in self.sparks if s[4] > 0]
        if self.state == "countdown":
            self.timer -= dt
            if self.timer <= 0:
                self.state = "play"
            return
        if self.state == "round":
            self.timer -= dt
            if self.timer <= 0:
                if max(self.score2.values()) >= WIN_SCORE:
                    self.winner = 1 if self.score2[1] > self.score2[2] else 2
                    self.state = "match"
                else:
                    self.start_round()
            return
        if self.state != "play":
            return

        alive = [s for s in self.ships.values() if s.alive]
        for s in alive:
            target = tilts[s.p][1] * 300
            s.vy += (target - s.vy) * min(1.0, 6 * dt)
            s.y += s.vy * dt
        # 2P: ships bump each other up/down
        if len(alive) == 2:
            a, b = sorted(alive, key=lambda s: s.y)
            ov = 2 * SHIP_R + 1 - (b.y - a.y)
            if ov > 0:
                a.y -= ov / 2
                b.y += ov / 2
                rel = a.vy - b.vy
                if rel > 0:
                    a.vy, b.vy = b.vy - 40, a.vy + 40
                    self.burst(SHIP_X, (a.y + b.y) / 2, 4, (255, 255, 255), (20, 60), 0.25)

        self.speed = min(170.0, 70.0 + self.dist * 0.01)
        dx = self.speed * dt
        self.dist += dx
        for c in self.cols:
            c[0] -= dx
        for gm in self.gems:
            gm[0] -= dx
        self.cols = [c for c in self.cols if c[0] > -COL]
        while self.cols[-1][0] < tl.FIELD_W:
            self.add_col(self.cols[-1][0] + COL)
        for gm in self.gems[:]:
            if math.hypot(gm[0] - SHIP_X, gm[1] - self.ships[1].y) < SHIP_R + 5:
                self.gems.remove(gm)
                self.gem_points += 25
                self.burst(gm[0], gm[1], 10, (120, 220, 255), (60, 60), 0.4)
            elif gm[0] < -10:
                self.gems.remove(gm)

        for s in alive:
            if self.crashed(s):
                s.alive = False
                self.burst(SHIP_X, s.y, 30, (255, 170, 60))
        if self.solo:
            if not self.ships[1].alive:
                self.state = "over"
                self.record = tl.submit("cave_best", self.score)
        else:
            left = [s for s in self.ships.values() if s.alive]
            if len(left) < 2:
                self.round_winner = left[0].p if left else None
                if self.round_winner:
                    self.score2[self.round_winner] += 1
                self.state, self.timer = "round", 2.2


def draw_ship(view, g, s):
    tilt = max(-0.5, min(0.5, s.vy / 400))
    ca, sa = math.cos(tilt), math.sin(tilt)
    pts = [view.P(SHIP_X + ax * ca - ay * sa, s.y + ax * sa + ay * ca)
           for ax, ay in ((9, 0), (-6, -5), (-3, 0), (-6, 5))]
    if int(g.t * 20 + s.p) % 2:
        pygame.draw.circle(view.screen, (255, 160, 60), view.P(SHIP_X - 7, s.y), view.L(2.5))
    pygame.draw.polygon(view.screen, tl.PLAYER_COL[s.p], pts)
    pygame.draw.polygon(view.screen, (255, 255, 255), pts, 1)


def draw(view, g, ctrl, end):
    view.update()
    scr, W, H = view.screen, view.W, view.H
    scr.fill(tl.C_BG)
    view.field((12, 14, 24))
    rock, edge = (70, 62, 80), (130, 115, 150)
    for x, top, bot in g.cols:
        w = view.L(COL) + 1
        px, py = view.P(x, 0)
        pygame.draw.rect(scr, rock, (px, py, w, view.L(top)))
        pygame.draw.rect(scr, rock, (px, view.P(0, bot)[1], w, view.L(tl.FIELD_H - bot)))
        pygame.draw.rect(scr, edge, (px, view.P(0, top)[1] - view.L(1.5), w, view.L(1.5)))
        pygame.draw.rect(scr, edge, (px, view.P(0, bot)[1], w, view.L(1.5)))
    for x, y in g.gems:
        pts = [view.P(x, y - 5), view.P(x + 4, y), view.P(x, y + 5), view.P(x - 4, y)]
        pygame.draw.polygon(scr, (120, 220, 255), pts)
    for x, y, _vx, _vy, ttl, col in g.sparks:
        pygame.draw.circle(scr, col, view.P(x, y), view.L(1.5))
    for s in g.ships.values():
        if s.alive:
            draw_ship(view, g, s)

    if g.solo:
        hy = view.hud * 0.42
        bt = tl.best("cave_best")
        view.text(f"SCORE  {g.score}", tl.C_GOLD, (W * 0.2, hy), 0.06)
        view.text(f"{g.dist / 100:.0f} m", tl.C_TEXT, (W * 0.5, hy), 0.05)
        view.text(f"best {bt}" if bt is not None else "no best yet", tl.C_DIM, (W * 0.8, hy), 0.045)
    else:
        tl.hud_scores(view, ctrl, g.score2, f"{g.dist / 100:.0f} m  -  first to {WIN_SCORE}")

    if g.state == "countdown":
        tl.draw_countdown(view, g.timer, "tilt forward / back to fly down / up" if g.solo
                          else "bump them into the rock - last ship flying wins")
    elif g.state == "round":
        view.panel(0.22)
        if g.round_winner:
            view.text(f"{tl.PLAYER_NAME[g.round_winner]} SURVIVES!", tl.PLAYER_COL[g.round_winner],
                      (W / 2, H / 2), 0.1)
        else:
            view.text("BOTH CRASHED!", tl.C_TEXT, (W / 2, H / 2), 0.1)
    elif g.state == "over":
        tl.draw_solo_result(view, f"{g.score} points", g.record)
    elif g.state == "match":
        tl.draw_match(view, g.winner, f"{g.score2[1]} - {g.score2[2]}")
    if end:
        end.draw(view, 0.72)


def run(ctrl, solo=True):
    tl.game_loop(ctrl, lambda: Cave(solo), draw, solo=solo)


if __name__ == "__main__":
    two = "--2p" in sys.argv
    if two:
        sys.argv.remove("--2p")
    tl.run_standalone(lambda c: run(c, solo=not two))
