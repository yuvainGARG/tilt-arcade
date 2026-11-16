#!/usr/bin/env python3
"""
Core Defense (2 players, co-op) - slimes crawl towards the crystal core in
the middle. Roll into them to squash them before they reach it. Big slimes
need two hits. The core has 10 HP; each wave is bigger. Best score saved.

Run on its own:  python3 defend.py [--fullscreen]
"""

import math
import random

import pygame

import tiltlib as tl

R = 7.0
CORE = (160.0, 120.0)
CORE_R = 13.0
CORE_HP = 10
SUBSTEPS = 4
BORDER = [(0, 0, 320, 4), (0, 236, 320, 4), (0, 0, 4, 240), (316, 0, 4, 240)]


class Defend:
    def __init__(self):
        self.balls = {p: tl.Ball(120.0 + (p - 1) * 80, 120.0, r=R, color=tl.PLAYER_COL[p], p=p) for p in (1, 2)}
        self.hp = CORE_HP
        self.score = 0
        self.wave = 0
        self.slimes = []
        self.queue = 0
        self.spawn_t = 0.0
        self.sparks = []
        self.pops = []
        self.hurt = 0.0
        self.banner = 0.0
        self.t = 0.0
        self.record = None
        self.state, self.timer = "countdown", 2.5

    @property
    def over(self):
        return self.state == "over"

    def next_wave(self):
        self.wave += 1
        self.queue = 5 + self.wave * 3
        self.spawn_t = 1.5
        self.banner = 1.6
        if self.wave > 1:
            self.hp = min(CORE_HP, self.hp + 1)

    def burst(self, x, y, col, n=12, sp=90):
        for _ in range(n):
            a = random.uniform(0, math.tau)
            s = random.uniform(20, sp)
            self.sparks.append([x, y, math.cos(a) * s, math.sin(a) * s, random.uniform(0.3, 0.7), col])

    def spawn(self):
        a = random.uniform(0, math.tau)
        x = CORE[0] + math.cos(a) * 200
        y = CORE[1] + math.sin(a) * 200
        x, y = max(-10, min(330, x)), max(-10, min(250, y))
        big = random.random() < min(0.45, 0.08 * self.wave)
        sp = random.uniform(16, 24) + self.wave * 2.0
        self.slimes.append(dict(x=x, y=y, vx=0.0, vy=0.0, r=9.0 if big else 6.0, hp=2 if big else 1,
                                sp=sp * (0.75 if big else 1.0), stun=0.0, ph=random.uniform(0, 6)))

    def step(self, dt, tilts):
        self.t += dt
        self.hurt = max(0.0, self.hurt - dt)
        self.banner = max(0.0, self.banner - dt)
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
                self.next_wave()
            return
        if self.state != "play":
            return

        b1, b2 = self.balls[1], self.balls[2]
        h = dt / SUBSTEPS
        for _ in range(SUBSTEPS):
            for b in (b1, b2):
                tl.integrate(b, tilts[b.p], h, accel=500, friction=1.6, max_speed=250)
                for w in BORDER:
                    tl.collide_rect(b, w, bounce=0.5)
                # bounce off the core
                dx, dy = b.x - CORE[0], b.y - CORE[1]
                d = math.hypot(dx, dy) or 1e-6
                if d < CORE_R + R:
                    nx, ny = dx / d, dy / d
                    b.x, b.y = CORE[0] + nx * (CORE_R + R), CORE[1] + ny * (CORE_R + R)
                    vn = b.vx * nx + b.vy * ny
                    if vn < 0:
                        b.vx -= 1.6 * vn * nx
                        b.vy -= 1.6 * vn * ny
            tl.collide_balls(b1, b2, restitution=0.8)
        for b in (b1, b2):
            b.trail.append((b.x, b.y))
            del b.trail[:-6]

        if self.queue > 0:
            self.spawn_t -= dt
            if self.spawn_t <= 0:
                self.spawn()
                self.queue -= 1
                self.spawn_t = max(0.35, 1.5 - self.wave * 0.1) * random.uniform(0.5, 1.4)

        for s in self.slimes[:]:
            if s["stun"] > 0:
                s["stun"] -= dt
                s["x"] += s["vx"] * dt
                s["y"] += s["vy"] * dt
                s["vx"] *= max(0.0, 1 - 4 * dt)
                s["vy"] *= max(0.0, 1 - 4 * dt)
            else:
                dx, dy = CORE[0] - s["x"], CORE[1] - s["y"]
                d = math.hypot(dx, dy) or 1e-6
                s["x"] += dx / d * s["sp"] * dt
                s["y"] += dy / d * s["sp"] * dt
            if math.hypot(CORE[0] - s["x"], CORE[1] - s["y"]) < CORE_R + s["r"]:
                self.slimes.remove(s)
                self.hp -= 2 if s["r"] > 7 else 1
                self.hurt = 0.4
                self.burst(s["x"], s["y"], (240, 90, 120), 18, 110)
                continue
            for b in (b1, b2):
                dx, dy = s["x"] - b.x, s["y"] - b.y
                d = math.hypot(dx, dy) or 1e-6
                if d < R + s["r"] and s["stun"] < 0.25:
                    s["hp"] -= 1
                    if s["hp"] <= 0:
                        self.slimes.remove(s)
                        pts = 20 if s["r"] > 7 else 10
                        self.score += pts
                        self.burst(s["x"], s["y"], (120, 230, 110))
                        self.pops.append([s["x"], s["y"] - 8, f"+{pts}", 0.7, tl.PLAYER_COL[b.p]])
                    else:
                        sp = max(120.0, math.hypot(b.vx, b.vy) * 1.2)
                        s["vx"], s["vy"] = dx / d * sp, dy / d * sp
                        s["stun"] = 0.8
                        s["r"] = 7.5
                        self.burst(s["x"], s["y"], (120, 230, 110), 6)
                    break

        if self.hp <= 0:
            self.hp = 0
            self.state = "over"
            self.burst(*CORE, (120, 220, 255), 50, 160)
            self.record = tl.submit("defend_best", self.score)
        elif self.queue == 0 and not self.slimes:
            self.score += 25 * self.wave
            self.next_wave()


def draw(view, g, ctrl, end):
    view.update()
    scr, W, H = view.screen, view.W, view.H
    scr.fill(tl.C_BG)
    view.field((40, 34, 56))
    scr.set_clip(pygame.Rect(*view.P(0, 0), view.L(320) + 1, view.L(240) + 1))   # bugs off the edge stay hidden
    for rr in (40, 80, 120, 160):
        pygame.draw.circle(scr, (48, 42, 66), view.P(*CORE), view.L(rr), 1)
    for w in BORDER:
        view.wall(w)
    # core
    if not g.over:
        pulse = 1 + 0.06 * math.sin(g.t * 4)
        col = (255, 120, 140) if g.hurt > 0 else (110, 210, 255)
        cx, cy = CORE
        r = CORE_R * pulse
        pts = [view.P(cx, cy - r), view.P(cx + r * 0.8, cy), view.P(cx, cy + r), view.P(cx - r * 0.8, cy)]
        pygame.draw.circle(scr, (40, 60, 90), view.P(cx, cy), view.L(CORE_R + 3))
        pygame.draw.polygon(scr, col, pts)
        pygame.draw.polygon(scr, (230, 250, 255), [view.P(cx, cy - r * 0.6), view.P(cx + r * 0.3, cy),
                                                   view.P(cx, cy + r * 0.2), view.P(cx - r * 0.3, cy)])
        # hp ring
        frac = g.hp / CORE_HP
        rect = pygame.Rect(0, 0, view.L(CORE_R * 2 + 12), view.L(CORE_R * 2 + 12))
        rect.center = view.P(cx, cy)
        if frac > 0:
            pygame.draw.arc(scr, tl.C_GOAL if frac > 0.4 else (240, 90, 90), rect, math.pi / 2,
                            math.pi / 2 + math.tau * frac, max(2, int(view.L(1.5))))
    for s in g.slimes:
        x, y, r = s["x"], s["y"], s["r"]
        wob = 1 + 0.12 * math.sin(g.t * 8 + s["ph"])
        col = (90, 190, 80) if r < 7 else (60, 150, 60)
        if s["stun"] > 0:
            col = (170, 230, 150)
        pygame.draw.ellipse(scr, col, (*view.P(x - r * wob, y - r / wob), view.L(2 * r * wob), view.L(2 * r / wob)))
        pygame.draw.circle(scr, (20, 30, 20), view.P(x - r * 0.3, y - r * 0.2), view.L(1.3))
        pygame.draw.circle(scr, (20, 30, 20), view.P(x + r * 0.3, y - r * 0.2), view.L(1.3))
    for x, y, _vx, _vy, ttl, col in g.sparks:
        pygame.draw.circle(scr, col, view.P(x, y), view.L(1.4))
    if not g.over:
        for b in g.balls.values():
            view.ball(b)
    for x, y, txt, ttl, col in g.pops:
        view.text(txt, col, view.P(x, y), 0.035)

    scr.set_clip(None)
    tl.hud_solo(view, f"SCORE  {g.score}", f"wave {g.wave}   core {g.hp}/{CORE_HP}", "defend_best")
    if g.state == "countdown":
        tl.draw_countdown(view, g.timer, "squash the slimes before they reach the core!")
    elif g.banner > 0 and g.state == "play":
        view.text(f"WAVE {g.wave}", tl.C_TEXT, (W / 2, H * 0.3), 0.09)
    if g.over:
        tl.draw_solo_result(view, f"{g.score} points", g.record)
        view.text(f"reached wave {g.wave}", tl.C_DIM, (W / 2, H * 0.62), 0.045)
    if end:
        end.draw(view, 0.72)


def run(ctrl):
    tl.game_loop(ctrl, Defend, draw)


if __name__ == "__main__":
    tl.run_standalone(run)
