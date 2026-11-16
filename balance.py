#!/usr/bin/env python3
"""
Balance Beam (1 player) - tilt left/right to tip the beam. Keep the ball
inside the glowing zone to score; the zone wanders and gets smaller, and
gusts of wind push the ball. Roll off either end and it's over.

Run on its own:  python3 balance.py [--fullscreen]
"""

import math
import random

import pygame

import tiltlib as tl

CX, CY = 160.0, 150.0
HALF = 125.0
BALL_R = 8.0
MAX_ANG = 0.3
GRAV = 520.0


class Balance:
    def __init__(self):
        self.ang = 0.0
        self.s = 0.0            # ball position along the beam
        self.v = 0.0
        self.zone = 0.0
        self.zone_v = 0.0
        self.zone_w = 70.0
        self.points = 0.0
        self.time = 0.0
        self.wind = 0.0
        self.wind_t = 6.0
        self.gust = 0.0
        self.in_zone = False
        self.t = 0.0
        self.fall = None
        self.record = None
        self.state, self.timer = "countdown", 2.5

    @property
    def over(self):
        return self.state == "over"

    @property
    def score(self):
        return int(self.points)

    def step(self, dt, tilts):
        self.t += dt
        if self.state == "countdown":
            self.timer -= dt
            if self.timer <= 0:
                self.state = "play"
            return
        if self.state == "falling":
            fx, fy, fvx, fvy = self.fall
            fvy += 600 * dt
            self.fall = (fx + fvx * dt, fy + fvy * dt, fvx, fvy)
            if fy > 260:
                self.state = "over"
                self.record = tl.submit("balance_best", self.score)
            return
        if self.state != "play":
            return
        self.time += dt
        target = max(-1.0, min(1.0, tilts[1][0])) * MAX_ANG
        self.ang += (target - self.ang) * min(1.0, 5 * dt)

        # wind gusts
        self.wind_t -= dt
        if self.wind_t <= 0:
            self.gust = 1.8
            self.wind = random.choice((-1, 1)) * random.uniform(60, 90 + self.time * 1.5)
            self.wind_t = random.uniform(5, 9) * max(0.5, 1 - self.time / 120)
        if self.gust > 0:
            self.gust -= dt
        acc = GRAV * math.sin(self.ang) + (self.wind if self.gust > 0 else 0.0)
        self.v += acc * dt
        self.v *= max(0.0, 1 - 0.6 * dt)
        self.s += self.v * dt

        # zone wanders
        self.zone_w = max(30.0, 70.0 - self.time * 0.5)
        lim = HALF - self.zone_w / 2 - 6
        self.zone_v += random.uniform(-1, 1) * (40 + self.time) * dt
        self.zone_v = max(-25 - self.time * 0.6, min(25 + self.time * 0.6, self.zone_v))
        self.zone += self.zone_v * dt
        if abs(self.zone) > lim:
            self.zone = math.copysign(lim, self.zone)
            self.zone_v = -self.zone_v

        self.in_zone = abs(self.s - self.zone) < self.zone_w / 2
        if self.in_zone:
            self.points += dt * (10 + self.time * 0.25)

        if abs(self.s) > HALF:
            ca, sa = math.cos(self.ang), math.sin(self.ang)
            x = CX + self.s * ca
            y = CY + self.s * sa - BALL_R
            self.fall = (x, y, self.v * ca, self.v * sa)
            self.state = "falling"


def draw(view, g, ctrl, end):
    view.update()
    scr, W, H = view.screen, view.W, view.H
    scr.fill(tl.C_BG)
    view.field((30, 44, 70))
    # hills in the background
    for i, col in enumerate(((36, 54, 80), (42, 64, 88))):
        pts = [view.P(0, 240)]
        for x in range(0, 321, 20):
            pts.append(view.P(x, 180 + i * 15 + math.sin(x * 0.03 + i) * 12))
        pts.append(view.P(320, 240))
        pygame.draw.polygon(scr, col, pts)
    # wind streaks
    if g.gust > 0 and g.state == "play":
        d = 1 if g.wind > 0 else -1
        random.seed(int(g.t * 10))
        for _ in range(8):
            y = random.uniform(30, 200)
            x = (random.uniform(0, 320) + g.t * 300 * d) % 320
            pygame.draw.line(scr, (140, 160, 200), view.P(x, y), view.P(x - 20 * d, y), 1)
        random.seed()
        view.text("WIND  >>>" if d > 0 else "<<<  WIND", (170, 190, 230), (W / 2, view.oy + view.L(20)), 0.045)

    ca, sa = math.cos(g.ang), math.sin(g.ang)

    def on_beam(s, off=0.0):
        return (CX + s * ca - off * sa, CY + s * sa + off * ca)
    # pivot
    pygame.draw.polygon(scr, (120, 100, 80), [view.P(CX, CY + 4), view.P(CX - 18, 232), view.P(CX + 18, 232)])
    # beam
    a, b = on_beam(-HALF), on_beam(HALF)
    a2, b2 = on_beam(-HALF, 6), on_beam(HALF, 6)
    pygame.draw.polygon(scr, (180, 140, 90), [view.P(*a), view.P(*b), view.P(*b2), view.P(*a2)])
    # zone
    z0, z1 = on_beam(g.zone - g.zone_w / 2, -1), on_beam(g.zone + g.zone_w / 2, -1)
    zc = tl.C_GOAL if g.in_zone else (60, 150, 100)
    pygame.draw.line(scr, zc, view.P(*z0), view.P(*z1), max(3, int(view.L(4))))
    for zz in (z0, z1):
        pygame.draw.circle(scr, zc, view.P(*zz), view.L(2.5))
    # ball
    if g.state == "falling" or g.over:
        if g.fall:
            fx, fy, _a, _b = g.fall
            pygame.draw.circle(scr, tl.PLAYER_COL[1], view.P(fx, fy), view.L(BALL_R))
    else:
        bx, by = on_beam(g.s, -BALL_R)
        pygame.draw.circle(scr, (10, 10, 15), view.P(bx + 1.5, by + 2), view.L(BALL_R))
        pygame.draw.circle(scr, tl.PLAYER_COL[1], view.P(bx, by), view.L(BALL_R))
        rot = g.s / BALL_R
        pygame.draw.line(scr, tuple(min(255, c + 80) for c in tl.PLAYER_COL[1]), view.P(bx, by),
                         view.P(bx + math.cos(rot) * BALL_R * 0.8, by + math.sin(rot) * BALL_R * 0.8), 2)
        if g.in_zone and g.state == "play":
            view.text("+", tl.C_GOAL, view.P(bx, by - 16 - (g.t * 40) % 10), 0.04)

    tl.hud_solo(view, f"SCORE  {g.score}", f"{g.time:.0f} s", "balance_best")
    if g.state == "countdown":
        tl.draw_countdown(view, g.timer, "tilt left / right - keep the ball in the green zone")
    elif g.over:
        tl.draw_solo_result(view, f"{g.score} points", g.record)
    if end:
        end.draw(view, 0.72)


def run(ctrl):
    tl.game_loop(ctrl, Balance, draw, solo=True)


if __name__ == "__main__":
    tl.run_standalone(run)
