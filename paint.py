#!/usr/bin/env python3
"""
Paint Wars (2 players) - your marble paints the floor as it rolls. After 45 s
whoever has painted more of the floor wins. Grab the paint bombs (stars) to
splat a big area. Rolling over the other colour paints over it.

Run on its own:  python3 paint.py [--fullscreen]
"""

import math
import random

import pygame

import tiltlib as tl

ROUND_TIME = 45.0
CELL = 8
GW, GH = tl.FIELD_W // CELL, tl.FIELD_H // CELL      # 40 x 30
R = 7.0
SUBSTEPS = 4
WALLS = [(0, 0, 320, 4), (0, 236, 320, 4), (0, 0, 4, 240), (316, 0, 4, 240),
         (100, 56, 16, 16), (204, 56, 16, 16), (100, 168, 16, 16), (204, 168, 16, 16), (152, 112, 16, 16)]
SOLID = set()
for _wx, _wy, _ww, _wh in WALLS:
    for _cx in range(GW):
        for _cy in range(GH):
            mx, my = _cx * CELL + CELL / 2, _cy * CELL + CELL / 2
            if _wx <= mx <= _wx + _ww and _wy <= my <= _wy + _wh:
                SOLID.add((_cx, _cy))
TOTAL = GW * GH - len(SOLID)


class Paint:
    def __init__(self):
        self.balls = {1: tl.Ball(40, 120, r=R, color=tl.PLAYER_COL[1], p=1),
                      2: tl.Ball(280, 120, r=R, color=tl.PLAYER_COL[2], p=2)}
        self.grid = {}          # (cx, cy) -> player
        self.time_left = ROUND_TIME
        self.state, self.timer = "countdown", 3.0
        self.bombs = []         # [x, y]
        self.splats = []        # [x, y, radius, ttl, player]
        self.bomb_t = 4.0
        self.t = 0.0
        self.winner = None

    @property
    def over(self):
        return self.state == "over"

    def count(self, p):
        return sum(1 for v in self.grid.values() if v == p)

    def paint(self, x, y, rad, p):
        c0, c1 = int((x - rad) // CELL), int((x + rad) // CELL)
        r0, r1 = int((y - rad) // CELL), int((y + rad) // CELL)
        for cx in range(max(0, c0), min(GW, c1 + 1)):
            for cy in range(max(0, r0), min(GH, r1 + 1)):
                if (cx, cy) in SOLID:
                    continue
                if math.hypot(cx * CELL + CELL / 2 - x, cy * CELL + CELL / 2 - y) <= rad:
                    self.grid[(cx, cy)] = p

    def step(self, dt, tilts):
        self.t += dt
        for s in self.splats:
            s[3] -= dt
        self.splats = [s for s in self.splats if s[3] > 0]
        if self.state == "countdown":
            self.timer -= dt
            if self.timer <= 0:
                self.state = "play"
            return
        if self.state != "play":
            return
        self.time_left -= dt
        self.bomb_t -= dt
        if self.bomb_t <= 0 and len(self.bombs) < 2:
            self.bomb_t = random.uniform(4, 7)
            for _ in range(50):
                x, y = random.uniform(20, 300), random.uniform(20, 220)
                if not any(wx - 10 < x < wx + w + 10 and wy - 10 < y < wy + h + 10 for wx, wy, w, h in WALLS):
                    self.bombs.append([x, y])
                    break
        balls = list(self.balls.values())
        h = dt / SUBSTEPS
        for _ in range(SUBSTEPS):
            for b in balls:
                tl.integrate(b, tilts[b.p], h, accel=440, friction=1.3, max_speed=240)
                for w in WALLS:
                    tl.collide_rect(b, w, bounce=0.5)
            tl.collide_balls(balls[0], balls[1], restitution=0.9)
        for b in balls:
            self.paint(b.x, b.y, R + 3, b.p)
            for bm in self.bombs[:]:
                if math.hypot(b.x - bm[0], b.y - bm[1]) < R + 6:
                    self.bombs.remove(bm)
                    self.paint(bm[0], bm[1], 34, b.p)
                    self.splats.append([bm[0], bm[1], 34, 0.4, b.p])
            b.trail.append((b.x, b.y))
            del b.trail[:-6]
        if self.time_left <= 0:
            self.time_left = 0
            self.state = "over"
            a, c = self.count(1), self.count(2)
            self.winner = None if a == c else (1 if a > c else 2)


def draw(view, g, ctrl, end):
    view.update()
    scr, W, H = view.screen, view.W, view.H
    scr.fill(tl.C_BG)
    view.field()
    paint_col = {p: tuple(int(c * 0.55 + 34 * 0.45) for c in tl.PLAYER_COL[p]) for p in (1, 2)}
    cs = view.L(CELL) + 1
    for (cx, cy), p in g.grid.items():
        pygame.draw.rect(scr, paint_col[p], (*view.P(cx * CELL, cy * CELL), cs, cs))
    for w in WALLS[4:]:
        view.wall(w)
    for w in WALLS[:4]:
        view.wall(w)
    for x, y in g.bombs:
        pts = []
        for i in range(10):
            a = g.t * 2 + i * math.pi / 5
            rr = 7 if i % 2 == 0 else 3
            pts.append(view.P(x + math.cos(a) * rr, y + math.sin(a) * rr))
        pygame.draw.polygon(scr, tl.C_GOLD, pts)
    for x, y, rad, ttl, p in g.splats:
        k = 1 - ttl / 0.4
        pygame.draw.circle(scr, tl.PLAYER_COL[p], view.P(x, y), view.L(rad * (0.5 + 0.6 * k)), max(1, int(view.L(2))))
    for b in g.balls.values():
        view.ball(b)

    a, c = g.count(1), g.count(2)
    hy = view.hud * 0.42
    view.text(f"{tl.PLAYER_NAME[1]}  {100 * a // TOTAL}%", tl.PLAYER_COL[1], (W * 0.2, hy), 0.06)
    view.text(f"{tl.PLAYER_NAME[2]}  {100 * c // TOTAL}%", tl.PLAYER_COL[2], (W * 0.8, hy), 0.06)
    tcol = (240, 90, 90) if g.time_left < 10 and g.state == "play" else tl.C_TEXT
    view.text(f"{math.ceil(g.time_left)}s", tcol, (W / 2, hy), 0.07)
    bw = W * 0.5
    x0, y0, bh = W * 0.25, view.hud * 0.78, max(4, view.hud * 0.12)
    pygame.draw.rect(scr, (40, 44, 60), (x0, y0, bw, bh))
    pygame.draw.rect(scr, tl.PLAYER_COL[1], (x0, y0, bw * a / TOTAL, bh))
    pygame.draw.rect(scr, tl.PLAYER_COL[2], (x0 + bw - bw * c / TOTAL, y0, bw * c / TOTAL, bh))

    if g.state == "countdown":
        tl.draw_countdown(view, g.timer, "paint the most floor!")
    elif g.over:
        tl.draw_match(view, g.winner, f"{100 * a // TOTAL}% - {100 * c // TOTAL}%")
    if end:
        end.draw(view, 0.72)


def run(ctrl):
    tl.game_loop(ctrl, Paint, draw)


if __name__ == "__main__":
    tl.run_standalone(run)
