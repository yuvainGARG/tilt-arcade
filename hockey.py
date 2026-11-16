#!/usr/bin/env python3
"""
Marble Hockey (2 players) - your marble is the striker, smash the white puck
into the other player's goal. Stay on your own half. First to 5.

Run on its own:  python3 hockey.py [--fullscreen]
"""

import math
import random

import pygame

import tiltlib as tl

WIN_SCORE = 5
PR = 11.0             # player marbles
PUCK_R = 7.0
GOAL_TOP, GOAL_BOT = 82.0, 158.0
SUBSTEPS = 5
MID = tl.FIELD_W / 2

WALLS = [(0, 0, 320, 4), (0, 236, 320, 4),
         (0, 0, 4, GOAL_TOP), (0, GOAL_BOT, 4, 240 - GOAL_BOT),
         (316, 0, 4, GOAL_TOP), (316, GOAL_BOT, 4, 240 - GOAL_BOT)]


def collide_mass(a, b, ma, mb, e=0.9):
    dx, dy = b.x - a.x, b.y - a.y
    rr = a.r + b.r
    d2 = dx * dx + dy * dy
    if d2 >= rr * rr or d2 < 1e-9:
        return 0.0
    d = math.sqrt(d2)
    nx, ny = dx / d, dy / d
    ov = rr - d
    a.x -= nx * ov * mb / (ma + mb)
    a.y -= ny * ov * mb / (ma + mb)
    b.x += nx * ov * ma / (ma + mb)
    b.y += ny * ov * ma / (ma + mb)
    rel = (b.vx - a.vx) * nx + (b.vy - a.vy) * ny
    if rel < 0:
        j = -(1 + e) * rel / (1 / ma + 1 / mb)
        a.vx -= j / ma * nx
        a.vy -= j / ma * ny
        b.vx += j / mb * nx
        b.vy += j / mb * ny
        return -rel
    return 0.0


class Hockey:
    def __init__(self):
        self.score = {1: 0, 2: 0}
        self.winner = None
        self.t = 0.0
        self.balls = {1: tl.Ball(60, 120, r=PR, color=tl.PLAYER_COL[1], p=1),
                      2: tl.Ball(260, 120, r=PR, color=tl.PLAYER_COL[2], p=2)}
        self.puck = tl.Ball(MID, 120, r=PUCK_R, color=(240, 240, 245), p=0)
        self.flash = 0.0
        self.reset()

    @property
    def over(self):
        return self.state == "match"

    def reset(self):
        for b in self.balls.values():
            b.respawn()
        self.puck.respawn()
        self.state, self.timer = "countdown", 2.0
        self.scorer = None
        self.stuck = 0.0

    def step(self, dt, tilts):
        self.t += dt
        self.flash = max(0.0, self.flash - dt)
        if self.state == "countdown":
            self.timer -= dt
            if self.timer <= 0:
                self.state = "play"
            return
        if self.state == "goal":
            self.timer -= dt
            if self.timer <= 0:
                if max(self.score.values()) >= WIN_SCORE:
                    self.winner = self.scorer
                    self.state = "match"
                else:
                    self.reset()
            return
        if self.state != "play":
            return
        h = dt / SUBSTEPS
        pk = self.puck
        for _ in range(SUBSTEPS):
            for p, b in self.balls.items():
                tl.integrate(b, tilts[p], h, accel=520, friction=2.2, max_speed=280)
                for w in WALLS:
                    tl.collide_rect(b, w, bounce=0.3)
                lo, hi = (4 + PR, MID - PR) if p == 1 else (MID + PR, 316 - PR)
                if b.x < lo:
                    b.x, b.vx = lo, max(0.0, b.vx)
                elif b.x > hi:
                    b.x, b.vx = hi, min(0.0, b.vx)
            tl.integrate(pk, (0, 0), h, accel=0, friction=0.25, max_speed=420)
            for w in WALLS:
                tl.collide_rect(pk, w, bounce=0.85)
            for b in self.balls.values():
                if collide_mass(b, pk, 3.0, 1.0, 0.95) > 80:
                    self.flash = 0.08
            if pk.x < -PUCK_R or pk.x > tl.FIELD_W + PUCK_R:
                self.scorer = 2 if pk.x < 0 else 1
                self.score[self.scorer] += 1
                self.state, self.timer = "goal", 1.6
                return
        # puck pinned between both players (or dead still)? give it a kick sideways
        self.stuck = self.stuck + dt if math.hypot(pk.vx, pk.vy) < 25 else 0.0
        if self.stuck > 1.5:
            self.stuck = 0.0
            pk.vx += random.uniform(-40, 40)
            pk.vy = random.choice((-1, 1)) * 160
        for b in list(self.balls.values()) + [pk]:
            b.trail.append((b.x, b.y))
            del b.trail[:-6]


def draw(view, g, ctrl, end):
    view.update()
    scr, W, H = view.screen, view.W, view.H
    scr.fill(tl.C_BG)
    view.field((30, 46, 62))
    line = (70, 100, 130)
    pygame.draw.line(scr, line, view.P(MID, 4), view.P(MID, 236), max(1, int(view.L(1.5))))
    pygame.draw.circle(scr, line, view.P(MID, 120), view.L(30), max(1, int(view.L(1.5))))
    for p, x in ((1, -8), (2, 316)):
        c = tl.PLAYER_COL[p]
        pygame.draw.rect(scr, (c[0] // 3, c[1] // 3, c[2] // 3), (*view.P(x, GOAL_TOP), view.L(12), view.L(GOAL_BOT - GOAL_TOP)))
        gx = 4 if p == 1 else 316
        pygame.draw.arc(scr, line, (*view.P(gx - 36, 84), view.L(72), view.L(72)),
                        -math.pi / 2 if p == 1 else math.pi / 2, math.pi / 2 if p == 1 else 3 * math.pi / 2,
                        max(1, int(view.L(1.5))))
    for w in WALLS:
        view.wall(w)
    pk = g.puck
    if g.state != "goal":
        pygame.draw.circle(scr, (10, 10, 15), view.P(pk.x + 1.5, pk.y + 1.5), view.L(PUCK_R))
        pygame.draw.circle(scr, (255, 255, 200) if g.flash > 0 else (235, 235, 240), view.P(pk.x, pk.y), view.L(PUCK_R))
        pygame.draw.circle(scr, (180, 180, 190), view.P(pk.x, pk.y), view.L(PUCK_R * 0.6), max(1, int(view.s / 2)))
    for b in g.balls.values():
        view.ball(b)

    tl.hud_scores(view, ctrl, g.score, f"first to {WIN_SCORE}")
    if g.state == "countdown":
        tl.draw_countdown(view, g.timer, "hit the puck into their goal", go="FACE OFF!")
    elif g.state == "goal":
        view.panel(0.25)
        view.text(f"{tl.PLAYER_NAME[g.scorer]} SCORES!", tl.PLAYER_COL[g.scorer], (W / 2, H / 2), 0.13)
    elif g.over:
        tl.draw_match(view, g.winner, f"{g.score[1]} - {g.score[2]}")
    if end:
        end.draw(view, 0.72)


def run(ctrl):
    tl.game_loop(ctrl, Hockey, draw)


if __name__ == "__main__":
    tl.run_standalone(run)
