#!/usr/bin/env python3
"""
Brick Breaker (1 player) - tilt left/right to move the paddle. Clear every brick
to go to the next level. Grey bricks take 2 hits, dark ones never break.
Catch the falling capsules: W = wide paddle, + = extra life.

Run on its own:  python3 bricks.py [--fullscreen]
"""

import math
import random

import pygame

import tiltlib as tl

PAD_Y, PAD_H = 222.0, 5.0
PAD_W, PAD_WIDE = 46.0, 74.0
PAD_SPEED = 520.0
BALL_R = 3.5
BW, BH = 24.0, 10.0
BX0, BY0 = 16.0, 26.0
LIVES = 3

# 12 columns. 1 = normal, 2 = tough (2 hits), # = solid (never breaks), . = empty
LEVELS = [
    ("Warm Up", ["............",
                 "111111111111",
                 "111111111111",
                 "111111111111",
                 "111111111111"]),
    ("Pyramid", [".....11.....",
                 "....1111....",
                 "...112211...",
                 "..11122111..",
                 ".1111111111.",
                 "111111111111"]),
    ("Checkers", ["2.2.2.2.2.2.",
                  ".1.1.1.1.1.1",
                  "2.2.2.2.2.2.",
                  ".1.1.1.1.1.1",
                  "2.2.2.2.2.2.",
                  ".1.1.1.1.1.1"]),
    ("Fortress", ["############",
                  "#1111111111#",
                  "#1222222221#",
                  "#1211111121#",
                  "#1222222221#",
                  "#1111111111#",
                  "#....##....#"]),
    ("Diamond", [".....22.....",
                 "....2112....",
                 "...211112...",
                 "..21111112..",
                 "...211112...",
                 "....2112....",
                 ".#...22...#."]),
    ("Gauntlet", ["222222222222",
                  "1#1#1#1#1#1#",
                  "111111111111",
                  "#1#1#1#1#1#1",
                  "222222222222",
                  "111111111111"]),
]

ROW_COL = [(235, 90, 90), (240, 150, 70), (240, 210, 80), (110, 210, 110), (80, 170, 240), (160, 120, 240),
           (230, 110, 200)]


class Bricks:
    def __init__(self):
        self.level = 0
        self.score = 0
        self.lives = LIVES
        self.t = 0.0
        self.record = None
        self.pad_x = tl.FIELD_W / 2
        self.wide = 0.0
        self.caps = []          # [x, y, kind]
        self.load_level()

    @property
    def over(self):
        return self.state == "over"

    def load_level(self):
        name, rows = LEVELS[self.level % len(LEVELS)]
        self.level_name = name
        self.bricks = []        # [x, y, hits_left(-1 = solid), row]
        for r, row in enumerate(rows):
            for c, ch in enumerate(row):
                if ch != ".":
                    hits = -1 if ch == "#" else int(ch)
                    self.bricks.append([BX0 + c * BW, BY0 + r * BH, hits, r])
        self.loops = self.level // len(LEVELS)
        self.caps = []
        self.reset_ball()
        self.state, self.timer = "ready", 1.5

    def reset_ball(self):
        self.stuck = True
        self.bx, self.by = self.pad_x, PAD_Y - BALL_R - 1
        self.speed = 165.0 + 20 * self.loops + 6 * (self.level % len(LEVELS))
        self.vx = self.vy = 0.0

    def pad_w(self):
        return PAD_WIDE if self.wide > 0 else PAD_W

    def step(self, dt, tilts):
        self.t += dt
        if self.state == "over":
            return
        self.wide = max(0.0, self.wide - dt)
        tx = tilts[1][0]
        pw = self.pad_w()
        self.pad_x = max(pw / 2 + 4, min(tl.FIELD_W - pw / 2 - 4, self.pad_x + tx * PAD_SPEED * dt))
        if self.state == "cleared":
            self.timer -= dt
            if self.timer <= 0:
                self.level += 1
                self.load_level()
            return
        if self.stuck:
            self.bx, self.by = self.pad_x, PAD_Y - BALL_R - 1
            self.timer -= dt
            if self.timer <= 0:
                self.stuck = False
                self.state = "play"
                ang = random.uniform(-0.5, 0.5)
                self.vx, self.vy = math.sin(ang) * self.speed, -math.cos(ang) * self.speed
            return

        for c in self.caps:
            c[1] += 60 * dt
            if abs(c[0] - self.pad_x) < pw / 2 + 5 and PAD_Y - 5 < c[1] < PAD_Y + PAD_H + 5:
                if c[2] == "W":
                    self.wide = 12.0
                else:
                    self.lives += 1
                c[1] = 999
        self.caps = [c for c in self.caps if c[1] < tl.FIELD_H]

        steps = 5
        h = dt / steps
        for _ in range(steps):
            self.bx += self.vx * h
            self.by += self.vy * h
            if self.bx < 4 + BALL_R:
                self.bx, self.vx = 4 + BALL_R, abs(self.vx)
            elif self.bx > tl.FIELD_W - 4 - BALL_R:
                self.bx, self.vx = tl.FIELD_W - 4 - BALL_R, -abs(self.vx)
            if self.by < 4 + BALL_R:
                self.by, self.vy = 4 + BALL_R, abs(self.vy)
            # paddle
            if self.vy > 0 and PAD_Y - BALL_R < self.by < PAD_Y + PAD_H and abs(self.bx - self.pad_x) < pw / 2 + BALL_R:
                off = max(-1.0, min(1.0, (self.bx - self.pad_x) / (pw / 2)))
                ang = off * math.radians(60) + random.uniform(-0.05, 0.05)
                if abs(ang) < 0.12:                 # never straight up and down forever
                    ang = 0.12 if ang >= 0 else -0.12
                self.speed = min(330.0, self.speed * 1.015)
                self.vx, self.vy = math.sin(ang) * self.speed, -math.cos(ang) * self.speed
                self.by = PAD_Y - BALL_R
            # bricks
            for b in self.bricks:
                x, y = b[0], b[1]
                cx = min(max(self.bx, x), x + BW)
                cy = min(max(self.by, y), y + BH)
                if (self.bx - cx) ** 2 + (self.by - cy) ** 2 < BALL_R ** 2:
                    ox = min(self.bx + BALL_R - x, x + BW - (self.bx - BALL_R))
                    oy = min(self.by + BALL_R - y, y + BH - (self.by - BALL_R))
                    if ox < oy:
                        self.vx = -abs(self.vx) if self.bx < x + BW / 2 else abs(self.vx)
                    else:
                        self.vy = -abs(self.vy) if self.by < y + BH / 2 else abs(self.vy)
                    if b[2] > 0:
                        b[2] -= 1
                        self.score += 10
                        if b[2] == 0:
                            self.score += 10
                            r = random.random()
                            if r < 0.08:
                                self.caps.append([x + BW / 2, y + BH / 2, "W"])
                            elif r < 0.1:
                                self.caps.append([x + BW / 2, y + BH / 2, "+"])
                    break
            self.bricks = [b for b in self.bricks if b[2] != 0]
            if self.by > tl.FIELD_H + 10:
                self.lives -= 1
                if self.lives <= 0:
                    self.state = "over"
                    self.record = tl.submit("bricks_best", self.score)
                else:
                    self.reset_ball()
                    self.state, self.timer = "ready", 1.2
                return
        if not any(b[2] > 0 for b in self.bricks):
            self.score += 100
            self.state, self.timer = "cleared", 2.0


def draw(view, g, ctrl, end):
    view.update()
    scr, W, H = view.screen, view.W, view.H
    scr.fill(tl.C_BG)
    view.field((22, 24, 36))
    for b in g.bricks:
        x, y, hits, row = b
        if hits < 0:
            col = (70, 74, 92)
        elif hits >= 2:
            col = (175, 180, 200)
        else:
            col = ROW_COL[row % len(ROW_COL)]
        pygame.draw.rect(scr, col, (*view.P(x + 0.5, y + 0.5), view.L(BW - 1), view.L(BH - 1)),
                         border_radius=int(view.L(1.5)))
        pygame.draw.line(scr, tuple(min(255, v + 50) for v in col), view.P(x + 1, y + 1), view.P(x + BW - 2, y + 1))
    for x, y, k in g.caps:
        col = (80, 200, 240) if k == "W" else (240, 90, 120)
        pygame.draw.rect(scr, col, (*view.P(x - 7, y - 4), view.L(14), view.L(8)), border_radius=int(view.L(4)))
        view.text(k, (20, 20, 30), view.P(x, y), 0.03)
    pw = g.pad_w()
    pygame.draw.rect(scr, (90, 200, 240) if g.wide > 0 else tl.C_TEXT,
                     (*view.P(g.pad_x - pw / 2, PAD_Y), view.L(pw), view.L(PAD_H)), border_radius=int(view.L(2.5)))
    if g.state != "over" and g.state != "cleared":
        pygame.draw.circle(scr, (255, 245, 200), view.P(g.bx, g.by), view.L(BALL_R))

    hy = view.hud * 0.42
    bt = tl.best("bricks_best")
    view.text(f"SCORE  {g.score}", tl.C_GOLD, (W * 0.18, hy), 0.055)
    view.text(f"Level {g.level + 1}: {g.level_name}", tl.C_TEXT, (W * 0.5, hy), 0.045)
    view.text("lives " + "o " * g.lives, tl.PLAYER_COL[1], (W * 0.8, hy), 0.045)
    view.text(f"best {bt}" if bt is not None else "no best yet", tl.C_DIM, (W * 0.5, view.hud * 0.85), 0.03)

    if g.state == "ready" and g.lives == LIVES and g.score == 0:
        view.text("tilt left / right to move", tl.C_DIM, (W / 2, H * 0.62), 0.05)
    elif g.state == "cleared":
        view.panel(0.25)
        view.text(f"LEVEL {g.level + 1} CLEAR!", tl.C_GOAL, (W / 2, H / 2), 0.1)
    elif g.over:
        tl.draw_solo_result(view, f"{g.score} points", g.record)
    if end:
        end.draw(view, 0.72)


def run(ctrl):
    tl.game_loop(ctrl, Bricks, draw, solo=True)


if __name__ == "__main__":
    tl.run_standalone(run)
