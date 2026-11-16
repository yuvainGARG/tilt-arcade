#!/usr/bin/env python3
"""
Laser Link (2 players, co-op) - a laser beam joins your two marbles. Bugs
crawl in from the edges and chase you: sweep the beam across them to zap
them, but don't let them touch a marble. The beam only works when you're
not too far apart. Shared lives and score; best score is saved.

Run on its own:  python3 laser.py [--fullscreen]
"""

import math
import random

import pygame

import tiltlib as tl

R = 7.0
LIVES = 5
BEAM_MIN, BEAM_MAX = 18.0, 140.0
SUBSTEPS = 4
BORDER = [(0, 0, 320, 4), (0, 236, 320, 4), (0, 0, 4, 240), (316, 0, 4, 240)]


def seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    s = 0.0 if L2 < 1e-9 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
    return math.hypot(px - (ax + dx * s), py - (ay + dy * s))


class Laser:
    def __init__(self):
        self.balls = {p: tl.Ball(110.0 + (p - 1) * 100, 120.0, r=R, color=tl.PLAYER_COL[p], p=p) for p in (1, 2)}
        self.inv = {1: 0.0, 2: 0.0}
        self.lives = LIVES
        self.score = 0
        self.combo = 0
        self.combo_t = 0.0
        self.bugs = []          # dict
        self.sparks = []
        self.pops = []
        self.time = 0.0
        self.spawn_t = 1.0
        self.t = 0.0
        self.record = None
        self.state, self.timer = "countdown", 2.5

    @property
    def over(self):
        return self.state == "over"

    @property
    def beam_on(self):
        b1, b2 = self.balls[1], self.balls[2]
        return BEAM_MIN < math.hypot(b1.x - b2.x, b1.y - b2.y) < BEAM_MAX

    def burst(self, x, y, col, n=12, sp=90):
        for _ in range(n):
            a = random.uniform(0, math.tau)
            s = random.uniform(20, sp)
            self.sparks.append([x, y, math.cos(a) * s, math.sin(a) * s, random.uniform(0.3, 0.7), col])

    def spawn(self):
        side = random.randrange(4)
        x, y = [(-8, random.uniform(10, 230)), (328, random.uniform(10, 230)),
                (random.uniform(10, 310), -8), (random.uniform(10, 310), 248)][side]
        kind = "gold" if random.random() < 0.06 else ("fast" if random.random() < min(0.4, self.time / 150) else "bug")
        sp = {"bug": 20, "fast": 36, "gold": 18}[kind] + min(25.0, self.time * 0.2)
        head = math.atan2(120 - y, 160 - x)
        self.bugs.append(dict(x=x, y=y, r=6.0 if kind != "fast" else 5.0, sp=sp, kind=kind, head=head,
                              wob=random.uniform(0, 6)))

    def step(self, dt, tilts):
        self.t += dt
        for s in self.sparks:
            s[0] += s[2] * dt
            s[1] += s[3] * dt
            s[4] -= dt
        self.sparks = [s for s in self.sparks if s[4] > 0]
        for pp in self.pops:
            pp[1] -= 25 * dt
            pp[3] -= dt
        self.pops = [pp for pp in self.pops if pp[3] > 0]
        if self.state == "countdown":
            self.timer -= dt
            if self.timer <= 0:
                self.state = "play"
            return
        if self.state != "play":
            return
        self.time += dt
        b1, b2 = self.balls[1], self.balls[2]
        h = dt / SUBSTEPS
        for _ in range(SUBSTEPS):
            for b in (b1, b2):
                tl.integrate(b, tilts[b.p], h, accel=480, friction=1.8, max_speed=230)
                for w in BORDER:
                    tl.collide_rect(b, w, bounce=0.5)
            tl.collide_balls(b1, b2, restitution=0.6)
        for b in (b1, b2):
            b.trail.append((b.x, b.y))
            del b.trail[:-5]
            self.inv[b.p] = max(0.0, self.inv[b.p] - dt)

        self.spawn_t -= dt
        if self.spawn_t <= 0:
            self.spawn()
            self.spawn_t = max(0.4, 1.7 - self.time * 0.01) * random.uniform(0.6, 1.3)
        self.combo_t -= dt
        if self.combo_t <= 0:
            self.combo = 0

        beam = self.beam_on
        for bug in self.bugs[:]:
            # chase the nearest marble, wobbling a bit
            tgt = min((b1, b2), key=lambda b: math.hypot(b.x - bug["x"], b.y - bug["y"]))
            want = math.atan2(tgt.y - bug["y"], tgt.x - bug["x"]) + math.sin(self.t * 3 + bug["wob"]) * 0.4
            diff = (want - bug["head"] + math.pi) % math.tau - math.pi
            turn = 1.6 * dt                     # bugs turn slowly, so you can dodge them
            bug["head"] += max(-turn, min(turn, diff))
            bug["x"] += math.cos(bug["head"]) * bug["sp"] * dt
            bug["y"] += math.sin(bug["head"]) * bug["sp"] * dt
            if beam and seg_dist(bug["x"], bug["y"], b1.x, b1.y, b2.x, b2.y) < bug["r"] + 3:
                self.bugs.remove(bug)
                self.combo += 1
                self.combo_t = 1.2
                pts = 10 * min(self.combo, 5)
                self.score += pts
                col = tl.C_GOLD if bug["kind"] == "gold" else (140, 240, 120)
                self.burst(bug["x"], bug["y"], col)
                txt = f"+{pts}"
                if bug["kind"] == "gold":
                    self.lives = min(9, self.lives + 1)
                    txt += "  +1 life"
                self.pops.append([bug["x"], bug["y"] - 8, txt, 0.8, col])
                continue
            for b in (b1, b2):
                if math.hypot(b.x - bug["x"], b.y - bug["y"]) < R + bug["r"] - 1:
                    self.bugs.remove(bug)
                    self.burst(bug["x"], bug["y"], (140, 240, 120), 8)
                    if self.inv[b.p] <= 0:
                        self.lives -= 1
                        self.inv[b.p] = 1.5
                        self.burst(b.x, b.y, b.color, 25, 130)
                        self.pops.append([b.x, b.y - 12, "OUCH", 0.8, b.color])
                    break
        if self.lives <= 0:
            self.state = "over"
            self.record = tl.submit("laser_best", self.score)


def draw(view, g, ctrl, end):
    view.update()
    scr, W, H = view.screen, view.W, view.H
    scr.fill(tl.C_BG)
    view.field((20, 26, 36))
    scr.set_clip(pygame.Rect(*view.P(0, 0), view.L(320) + 1, view.L(240) + 1))   # bugs off the edge stay hidden
    for i in range(0, 320, 16):
        pygame.draw.line(scr, (26, 34, 46), view.P(i, 0), view.P(i, 240))
    for j in range(0, 240, 16):
        pygame.draw.line(scr, (26, 34, 46), view.P(0, j), view.P(320, j))
    for w in BORDER:
        view.wall(w)
    b1, b2 = g.balls[1], g.balls[2]
    if g.state != "over":
        if g.beam_on:
            flick = 0.7 + 0.3 * math.sin(g.t * 40)
            glow = (int(120 * flick), int(255 * flick), int(200 * flick))
            pygame.draw.line(scr, (40, 90, 80), view.P(b1.x, b1.y), view.P(b2.x, b2.y), max(4, int(view.L(4))))
            pygame.draw.line(scr, glow, view.P(b1.x, b1.y), view.P(b2.x, b2.y), max(2, int(view.L(1.6))))
        else:
            # dashed, dim: out of range
            n = 14
            for i in range(0, n, 2):
                a, c = i / n, (i + 1) / n
                pygame.draw.line(scr, (70, 80, 90), view.P(b1.x + (b2.x - b1.x) * a, b1.y + (b2.y - b1.y) * a),
                                 view.P(b1.x + (b2.x - b1.x) * c, b1.y + (b2.y - b1.y) * c), 1)
    for bug in g.bugs:
        x, y, r = bug["x"], bug["y"], bug["r"]
        col = {"bug": (110, 200, 90), "fast": (230, 140, 60), "gold": tl.C_GOLD}[bug["kind"]]
        leg = math.sin(g.t * 18 + bug["wob"]) * 2
        for s in (-1, 1):
            pygame.draw.line(scr, (30, 40, 30), view.P(x - r, y + s * 2 + leg * s), view.P(x + r, y - s * 2 + leg * s), 1)
        pygame.draw.circle(scr, col, view.P(x, y), view.L(r))
        pygame.draw.circle(scr, (20, 20, 20), view.P(x - r * 0.35, y - r * 0.3), view.L(1.2))
        pygame.draw.circle(scr, (20, 20, 20), view.P(x + r * 0.35, y - r * 0.3), view.L(1.2))
    for x, y, _vx, _vy, ttl, col in g.sparks:
        pygame.draw.circle(scr, col, view.P(x, y), view.L(1.4))
    if g.state != "over":
        for p, b in g.balls.items():
            if g.inv[p] <= 0 or int(g.t * 12) % 2:
                view.ball(b)
    for x, y, txt, ttl, col in g.pops:
        view.text(txt, col, view.P(x, y), 0.035)

    scr.set_clip(None)
    tl.hud_solo(view, f"SCORE  {g.score}", f"lives {g.lives}   {g.time:.0f} s", "laser_best")
    if g.state == "countdown":
        tl.draw_countdown(view, g.timer, "sweep the laser between you across the bugs!")
    elif g.state == "play" and not g.beam_on and g.time < 20:
        view.text("too far apart - the laser is off!", (200, 120, 120), (W / 2, H * 0.94), 0.04)
    if g.over:
        tl.draw_solo_result(view, f"{g.score} points", g.record)
    if end:
        end.draw(view, 0.72)


def run(ctrl):
    tl.game_loop(ctrl, Laser, draw)


if __name__ == "__main__":
    tl.run_standalone(run)
