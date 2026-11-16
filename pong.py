#!/usr/bin/env python3
"""
Tilt Pong - tilt forward/back to move your paddle. First to 7.

  1 player: you (left) against the computer, pick how hard.
  2 players: BLUE left, RED right.

Run on its own:  python3 pong.py [--fullscreen] [--solo]
"""

import math
import random
import sys

import pygame

import tiltlib as tl

WIN_SCORE = 7
PAD_H, PAD_W = 46.0, 6.0
PAD_X = {1: 12.0, 2: tl.FIELD_W - 12.0 - PAD_W}
PAD_SPEED = 430.0
BALL_R = 4.0
TOP, BOTTOM = 6.0, tl.FIELD_H - 6.0

LEVELS = [
    ("Easy", "The computer is slow and sleepy", 150.0, 26.0),
    ("Normal", "A fair fight", 210.0, 14.0),
    ("Hard", "Fast and accurate", 290.0, 6.0),
]


class Pong:
    def __init__(self, solo, level=1):
        self.solo = solo
        self.level = level
        self.pad = {1: tl.FIELD_H / 2, 2: tl.FIELD_H / 2}
        self.score = {1: 0, 2: 0}
        self.winner = None
        self.t = 0.0
        self.serve_to = random.choice((1, 2))
        self.cpu_err = 0.0
        self.new_ball()

    @property
    def over(self):
        return self.state == "match"

    def new_ball(self):
        self.bx, self.by = tl.FIELD_W / 2, tl.FIELD_H / 2
        ang = random.uniform(-0.5, 0.5)
        d = -1 if self.serve_to == 1 else 1
        self.speed = 170.0
        self.vx, self.vy = d * math.cos(ang) * self.speed, math.sin(ang) * self.speed
        self.state, self.timer = "serve", 1.4
        self.flash = 0.0

    def step(self, dt, tilts):
        self.t += dt
        self.flash = max(0.0, self.flash - dt)
        if self.state == "match":
            return
        # paddles
        for p in (1, 2):
            if p == 2 and self.solo:
                speed, err = LEVELS[self.level][2], LEVELS[self.level][3]
                target = self.by + self.cpu_err if self.vx > 0 else tl.FIELD_H / 2
                diff = target - self.pad[2]
                self.pad[2] += max(-speed * dt, min(speed * dt, diff))
            else:
                ty = tilts.get(p, (0, 0))[1]
                self.pad[p] += ty * PAD_SPEED * dt
            self.pad[p] = max(TOP + PAD_H / 2, min(BOTTOM - PAD_H / 2, self.pad[p]))
        if self.state == "serve":
            self.timer -= dt
            if self.timer <= 0:
                self.state = "play"
            return
        if self.state == "point":
            self.timer -= dt
            if self.timer <= 0:
                if max(self.score.values()) >= WIN_SCORE:
                    self.winner = 1 if self.score[1] > self.score[2] else 2
                    self.state = "match"
                else:
                    self.new_ball()
            return

        steps = 4
        h = dt / steps
        for _ in range(steps):
            self.bx += self.vx * h
            self.by += self.vy * h
            if self.by < TOP + BALL_R:
                self.by, self.vy = TOP + BALL_R, abs(self.vy)
            elif self.by > BOTTOM - BALL_R:
                self.by, self.vy = BOTTOM - BALL_R, -abs(self.vy)
            for p in (1, 2):
                px = PAD_X[p]
                if px - BALL_R < self.bx < px + PAD_W + BALL_R and abs(self.by - self.pad[p]) < PAD_H / 2 + BALL_R:
                    going_in = self.vx < 0 if p == 1 else self.vx > 0
                    if going_in:
                        off = (self.by - self.pad[p]) / (PAD_H / 2)
                        ang = max(-1, min(1, off)) * math.radians(55)
                        self.speed = min(400.0, self.speed * 1.07)
                        d = 1 if p == 1 else -1
                        self.vx, self.vy = d * math.cos(ang) * self.speed, math.sin(ang) * self.speed
                        self.bx = px + PAD_W + BALL_R if p == 1 else px - BALL_R
                        self.flash = 0.1
                        self.cpu_err = random.uniform(-1, 1) * LEVELS[self.level][3] * 1.6
            if self.bx < -BALL_R * 2 or self.bx > tl.FIELD_W + BALL_R * 2:
                scorer = 2 if self.bx < 0 else 1
                self.score[scorer] += 1
                self.serve_to = 1 if scorer == 2 else 2
                self.state, self.timer = "point", 1.0
                return


def draw(view, g, ctrl, end):
    view.update()
    scr, W, H = view.screen, view.W, view.H
    scr.fill(tl.C_BG)
    view.field((14, 16, 26))
    for y in range(8, int(tl.FIELD_H), 14):
        pygame.draw.rect(scr, (50, 54, 72), (*view.P(159, y), view.L(2), view.L(7)))
    pygame.draw.rect(scr, (60, 64, 84), (*view.P(0, 0), view.L(tl.FIELD_W), view.L(TOP)))
    pygame.draw.rect(scr, (60, 64, 84), (*view.P(0, BOTTOM), view.L(tl.FIELD_W), view.L(TOP)))
    for p in (1, 2):
        c = tl.PLAYER_COL[p] if not (g.solo and p == 2) else (200, 200, 210)
        pygame.draw.rect(scr, c, (*view.P(PAD_X[p], g.pad[p] - PAD_H / 2), view.L(PAD_W), view.L(PAD_H)),
                         border_radius=int(view.L(2)))
    if g.state in ("play", "serve"):
        col = (255, 255, 200) if g.flash > 0 else tl.C_TEXT
        pygame.draw.circle(scr, col, view.P(g.bx, g.by), view.L(BALL_R))

    hy = view.hud * 0.42
    if g.solo:
        view.text(f"YOU  {g.score[1]}", tl.PLAYER_COL[1], (W * 0.2, hy), 0.06)
        view.text(f"CPU  {g.score[2]}", (200, 200, 210), (W * 0.8, hy), 0.06)
        view.text(f"{LEVELS[g.level][0]} - first to {WIN_SCORE}", tl.C_DIM, (W / 2, hy), 0.035)
    else:
        tl.hud_scores(view, ctrl, g.score, f"first to {WIN_SCORE}")
    if g.state == "match":
        if g.solo:
            view.panel(0.6)
            won = g.winner == 1
            view.text("YOU WIN!" if won else "CPU WINS", tl.C_GOLD if won else tl.C_DIM, (W / 2, H * 0.37), 0.16)
            view.text(f"{g.score[1]} - {g.score[2]}", tl.C_TEXT, (W / 2, H * 0.54), 0.07)
        else:
            tl.draw_match(view, g.winner, f"{g.score[1]} - {g.score[2]}")
    if end:
        end.draw(view, 0.72)


def run(ctrl, solo=False):
    level = 1
    if solo:
        level = tl.pick(ctrl, "Pong vs CPU - how hard?", [(n, d) for n, d, _s, _e in LEVELS], sel=1)
        if level is None:
            return
    tl.game_loop(ctrl, lambda: Pong(solo, level), draw, solo=solo)


if __name__ == "__main__":
    tl.run_standalone(run, solo="--solo" in sys.argv)
