#!/usr/bin/env python3
"""
Hot Potato (2 players) - one marble is carrying a bomb. Bump into the other
marble to pass it on. When the fuse runs out, whoever has the bomb loses the
round. The fuse is secret, but the sparks speed up near the end. First to 3.

Run on its own:  python3 potato.py [--fullscreen]
"""

import math
import random

import pygame

import tiltlib as tl

WIN_SCORE = 3
R = 8.0
SUBSTEPS = 4
WALLS = [(0, 0, 320, 4), (0, 236, 320, 4), (0, 0, 4, 240), (316, 0, 4, 240),
         (60, 50, 50, 8), (210, 50, 50, 8), (60, 182, 50, 8), (210, 182, 50, 8),
         (130, 100, 8, 40), (182, 100, 8, 40)]


class Potato:
    def __init__(self):
        self.score = {1: 0, 2: 0}
        self.balls = {1: tl.Ball(30, 120, r=R, color=tl.PLAYER_COL[1], p=1),
                      2: tl.Ball(290, 120, r=R, color=tl.PLAYER_COL[2], p=2)}
        self.winner = None
        self.t = 0.0
        self.start_round()

    @property
    def over(self):
        return self.state == "match"

    def start_round(self):
        for b in self.balls.values():
            b.respawn()
        self.holder = random.choice((1, 2))
        self.fuse_total = random.uniform(12, 22)
        self.fuse = self.fuse_total
        self.cool = 0.0
        self.state, self.timer = "countdown", 3.0
        self.loser = None
        self.passes = 0

    def step(self, dt, tilts):
        self.t += dt
        if self.state == "countdown":
            self.timer -= dt
            if self.timer <= 0:
                self.state = "play"
            return
        if self.state == "boom":
            self.timer -= dt
            if self.timer <= 0:
                if max(self.score.values()) >= WIN_SCORE:
                    self.winner = 1 if self.score[1] > self.score[2] else 2
                    self.state = "match"
                else:
                    self.start_round()
            return
        if self.state != "play":
            return
        self.fuse -= dt
        self.cool = max(0.0, self.cool - dt)
        a, b = self.balls[1], self.balls[2]
        h = dt / SUBSTEPS
        for _ in range(SUBSTEPS):
            for ball in (a, b):
                boost = 1.15 if ball.p == self.holder else 1.0
                tl.integrate(ball, tilts[ball.p], h, accel=420 * boost, friction=1.4, max_speed=250 * boost)
                for w in WALLS:
                    tl.collide_rect(ball, w, bounce=0.5)
            if tl.collide_balls(a, b, restitution=0.9) > 0 or math.hypot(a.x - b.x, a.y - b.y) <= 2 * R + 0.5:
                if self.cool <= 0:
                    self.holder = 2 if self.holder == 1 else 1
                    self.cool = 0.7
                    self.passes += 1
        for ball in (a, b):
            ball.trail.append((ball.x, ball.y))
            del ball.trail[:-6]
        if self.fuse <= 0:
            self.loser = self.holder
            survivor = 2 if self.loser == 1 else 1
            self.score[survivor] += 1
            self.state, self.timer = "boom", 2.2


def draw(view, g, ctrl, end):
    view.update()
    scr, W, H = view.screen, view.W, view.H
    scr.fill(tl.C_BG)
    danger = 1 - max(0.0, g.fuse) / g.fuse_total
    field = (int(34 + 30 * danger * danger), 38, 54)
    view.field(field)
    for w in WALLS:
        view.wall(w)
    for b in g.balls.values():
        if g.state == "boom" and b.p == g.loser:
            continue
        view.ball(b)
    if g.state in ("countdown", "play"):
        hb = g.balls[g.holder]
        bx, by = hb.x, hb.y - R - 6
        pygame.draw.circle(scr, (20, 20, 24), view.P(bx, by), view.L(5))
        pygame.draw.circle(scr, (90, 90, 100), view.P(bx - 1.5, by - 1.5), view.L(1.5))
        rate = 4 + 26 * danger * danger
        if math.sin(g.t * rate) > 0:
            for i in range(5):
                a = random.uniform(0, math.tau)
                pygame.draw.circle(scr, random.choice([(255, 220, 90), (255, 140, 60)]),
                                   view.P(bx + 4 + math.cos(a) * 3, by - 5 + math.sin(a) * 3), view.L(1))
        if g.cool > 0:
            pygame.draw.circle(scr, tl.C_TEXT, view.P(hb.x, hb.y), view.L(R + 4), max(1, int(view.s / 2)))
    if g.state == "boom":
        k = 1 - g.timer / 2.2
        lb = g.balls[g.loser]
        for i, col in enumerate(((255, 240, 160), (255, 160, 60), (220, 70, 40))):
            rad = (40 - i * 10) * min(1, k * 3)
            if rad > 0:
                pygame.draw.circle(scr, col, view.P(lb.x, lb.y), view.L(rad))

    tl.hud_scores(view, ctrl, g.score, f"first to {WIN_SCORE}")
    if g.state == "countdown":
        tl.draw_countdown(view, g.timer, f"{tl.PLAYER_NAME[g.holder]} has the bomb - bump to pass it!")
    elif g.state == "boom":
        view.panel(0.22)
        s = 2 if g.loser == 1 else 1
        view.text(f"BOOM! {tl.PLAYER_NAME[s]} SURVIVES", tl.PLAYER_COL[s], (W / 2, H / 2), 0.09)
    elif g.over:
        tl.draw_match(view, g.winner, f"{g.score[1]} - {g.score[2]}")
    if end:
        end.draw(view, 0.72)


def run(ctrl):
    tl.game_loop(ctrl, Potato, draw)


if __name__ == "__main__":
    tl.run_standalone(run)
