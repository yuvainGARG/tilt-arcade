#!/usr/bin/env python3
"""
Paint Together (2 players, co-op) - roll around to paint the floor. Paint
75% of it before the clock runs out to clear the level. Grey eraser robots
wipe your paint off - bump into one to knock it out for a few seconds.
Every level adds another robot. Best score is saved.

Run on its own:  python3 paint_coop.py [--fullscreen]
"""

import math
import random

import pygame

import tiltlib as tl

R = 7.0
CELL = 10
GW, GH = 32, 24
TARGET = 0.75
LEVEL_TIME = 40.0
SUBSTEPS = 4
BORDER = [(0, 0, 320, 4), (0, 236, 320, 4), (0, 0, 4, 240), (316, 0, 4, 240)]
PAINT_R = 10.0
ERASE_R = 11.0


class PaintCoop:
    def __init__(self):
        self.balls = {p: tl.Ball(100.0 + (p - 1) * 120, 120.0, r=R, color=tl.PLAYER_COL[p], p=p) for p in (1, 2)}
        self.level = 0
        self.score = 0
        self.t = 0.0
        self.record = None
        self.sparks = []
        self.next_level()

    @property
    def over(self):
        return self.state == "over"

    def next_level(self):
        self.level += 1
        self.grid = [[0] * GW for _ in range(GH)]      # 0 = bare, else player number
        self.time_left = LEVEL_TIME
        self.bots = []
        for i in range(self.level):
            a = random.uniform(0, math.tau)
            sp = 45 + self.level * 6
            self.bots.append(dict(x=random.choice((30.0, 290.0)), y=random.uniform(30, 210),
                                  vx=math.cos(a) * sp, vy=math.sin(a) * sp, sp=sp, stun=0.0, turn=random.uniform(1, 3)))
        for p, b in self.balls.items():
            b.home = (100.0 + (p - 1) * 120, 120.0)
            b.respawn()
        self.state, self.timer = "countdown", 2.0

    @property
    def cover(self):
        return sum(1 for row in self.grid for v in row if v) / (GW * GH)

    def stamp(self, x, y, rad, val):
        c0, c1 = int((x - rad) // CELL), int((x + rad) // CELL)
        r0, r1 = int((y - rad) // CELL), int((y + rad) // CELL)
        for r in range(max(0, r0), min(GH, r1 + 1)):
            for c in range(max(0, c0), min(GW, c1 + 1)):
                if math.hypot(c * CELL + CELL / 2 - x, r * CELL + CELL / 2 - y) < rad:
                    self.grid[r][c] = val

    def step(self, dt, tilts):
        self.t += dt
        for s in self.sparks:
            s[0] += s[2] * dt
            s[1] += s[3] * dt
            s[4] -= dt
        self.sparks = [s for s in self.sparks if s[4] > 0]
        if self.state in ("countdown", "cleared"):
            self.timer -= dt
            if self.timer <= 0:
                if self.state == "cleared":
                    self.next_level()
                else:
                    self.state = "play"
            return
        if self.state != "play":
            return
        self.time_left -= dt
        b1, b2 = self.balls[1], self.balls[2]
        h = dt / SUBSTEPS
        for _ in range(SUBSTEPS):
            for b in (b1, b2):
                tl.integrate(b, tilts[b.p], h, accel=480, friction=1.6, max_speed=240)
                for w in BORDER:
                    tl.collide_rect(b, w, bounce=0.5)
            tl.collide_balls(b1, b2, restitution=0.7)
        for b in (b1, b2):
            b.trail.append((b.x, b.y))
            del b.trail[:-4]
            self.stamp(b.x, b.y, PAINT_R, b.p)

        for bot in self.bots:
            if bot["stun"] > 0:
                bot["stun"] -= dt
                bot["vx"] *= max(0.0, 1 - 3 * dt)
                bot["vy"] *= max(0.0, 1 - 3 * dt)
            else:
                bot["turn"] -= dt
                if bot["turn"] <= 0:          # wander: pick a new heading now and then
                    a = math.atan2(bot["vy"], bot["vx"]) + random.uniform(-1.2, 1.2)
                    bot["vx"], bot["vy"] = math.cos(a) * bot["sp"], math.sin(a) * bot["sp"]
                    bot["turn"] = random.uniform(1, 3)
                sp = math.hypot(bot["vx"], bot["vy"]) or 1
                if sp < bot["sp"]:
                    bot["vx"] *= bot["sp"] / sp
                    bot["vy"] *= bot["sp"] / sp
                self.stamp(bot["x"], bot["y"], ERASE_R, 0)
            bot["x"] += bot["vx"] * dt
            bot["y"] += bot["vy"] * dt
            if not 12 < bot["x"] < 308:
                bot["vx"] = -bot["vx"]
                bot["x"] = max(12.0, min(308.0, bot["x"]))
            if not 12 < bot["y"] < 228:
                bot["vy"] = -bot["vy"]
                bot["y"] = max(12.0, min(228.0, bot["y"]))
            for b in (b1, b2):
                dx, dy = bot["x"] - b.x, bot["y"] - b.y
                d = math.hypot(dx, dy) or 1e-6
                if d < R + 9 and bot["stun"] <= 0:
                    bot["stun"] = 3.0
                    bot["vx"], bot["vy"] = dx / d * 160, dy / d * 160
                    b.vx -= dx / d * 60
                    b.vy -= dy / d * 60
                    for _ in range(10):
                        a = random.uniform(0, math.tau)
                        self.sparks.append([bot["x"], bot["y"], math.cos(a) * 70, math.sin(a) * 70, 0.4, (255, 230, 120)])

        if self.cover >= TARGET:
            self.score += 100 * self.level + int(self.time_left) * 5
            self.state, self.timer = "cleared", 2.2
        elif self.time_left <= 0:
            self.time_left = 0
            self.state = "over"
            self.record = tl.submit("paint_coop_best", self.score)


def draw(view, g, ctrl, end):
    view.update()
    scr, W, H = view.screen, view.W, view.H
    scr.fill(tl.C_BG)
    view.field((58, 60, 70))
    cols = {p: tuple(int(c * 0.75) for c in tl.PLAYER_COL[p]) for p in (1, 2)}
    cw = view.L(CELL) + 1
    for r, row in enumerate(g.grid):
        for c, v in enumerate(row):
            if v:
                pygame.draw.rect(scr, cols[v], (*view.P(c * CELL, r * CELL), cw, cw))
    for w in BORDER:
        view.wall(w)
    for bot in g.bots:
        x, y = bot["x"], bot["y"]
        stunned = bot["stun"] > 0
        pygame.draw.rect(scr, (90, 92, 100) if stunned else (170, 172, 180),
                         (*view.P(x - 9, y - 9), view.L(18), view.L(18)), border_radius=int(view.L(4)))
        eye = (255, 230, 120) if stunned else (230, 60, 60)
        pygame.draw.circle(scr, eye, view.P(x - 3.5, y - 2), view.L(2))
        pygame.draw.circle(scr, eye, view.P(x + 3.5, y - 2), view.L(2))
        if stunned:
            for i in range(3):
                a = g.t * 5 + i * math.tau / 3
                pygame.draw.circle(scr, (255, 230, 120), view.P(x + math.cos(a) * 9, y - 12 + math.sin(a) * 3), view.L(1.4))
    for x, y, _vx, _vy, ttl, col in g.sparks:
        pygame.draw.circle(scr, col, view.P(x, y), view.L(1.4))
    if not g.over:
        for b in g.balls.values():
            view.ball(b)

    # coverage bar
    frac = g.cover
    bx, by, bw, bh = view.P(60, 230)[0], view.P(0, 228)[1], view.L(200), view.L(6)
    pygame.draw.rect(scr, (30, 30, 40), (bx, by, bw, bh), border_radius=3)
    pygame.draw.rect(scr, tl.C_GOAL if frac >= TARGET else (200, 200, 210), (bx, by, bw * min(1, frac), bh), border_radius=3)
    tx = bx + bw * TARGET
    pygame.draw.line(scr, tl.C_GOLD, (tx, by - 3), (tx, by + bh + 3), 2)

    tl.hud_solo(view, f"SCORE  {g.score}", f"level {g.level}   {math.ceil(g.time_left)} s   {frac * 100:.0f}%",
                "paint_coop_best")
    if g.state == "countdown":
        tl.draw_countdown(view, g.timer, f"paint {int(TARGET * 100)}% of the floor together - bump the robots!",
                          go=f"LEVEL {g.level}")
    elif g.state == "cleared":
        view.panel(0.22)
        view.text(f"LEVEL {g.level} PAINTED!", tl.C_GOAL, (W / 2, H / 2), 0.1)
    elif g.over:
        tl.draw_solo_result(view, f"{g.score} points", g.record)
        view.text(f"reached level {g.level}", tl.C_DIM, (W / 2, H * 0.62), 0.045)
    if end:
        end.draw(view, 0.72)


def run(ctrl):
    tl.game_loop(ctrl, PaintCoop, draw)


if __name__ == "__main__":
    tl.run_standalone(run)
