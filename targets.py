#!/usr/bin/env python3
"""
Target Rush - roll onto the target as fast as you can, then the next one
appears. Quick hits build a combo for extra points.

  1 player: 40 seconds, best score is saved. Red X spots cost you 3 s.
  2 players: race to the same target. First to 15 wins.

Run on its own:  python3 targets.py [--fullscreen] [--vs]
"""

import math
import random
import sys

import pygame

import tiltlib as tl

ROUND = 40.0
WIN_SCORE = 15
R = 6.0
T_R = 11.0
SUBSTEPS = 4
BORDER = [(0, 0, 320, 4), (0, 236, 320, 4), (0, 0, 4, 240), (316, 0, 4, 240)]
WALLS = [(100, 70, 8, 100), (212, 70, 8, 100), (140, 40, 40, 8), (140, 192, 40, 8)]


class Rush:
    def __init__(self, solo=True):
        self.solo = solo
        self.walls = BORDER + WALLS
        players = [1] if solo else [1, 2]
        starts = {1: (160, 120)} if solo else {1: (40, 120), 2: (280, 120)}
        self.balls = {p: tl.Ball(*starts[p], r=R, color=tl.PLAYER_COL[p], p=p) for p in players}
        self.score = {p: 0 for p in players}
        self.hits = 0
        self.combo = 0
        self.since = 0.0
        self.time_left = ROUND
        self.traps = []         # [x, y, ttl]
        self.pops = []
        self.rings = []
        self.t = 0.0
        self.record = None
        self.winner = None
        self.target = self.new_target()
        self.state, self.timer = "countdown", 2.5

    @property
    def over(self):
        return self.state == "over"

    def free(self, x, y, margin):
        return not any(wx - margin < x < wx + w + margin and wy - margin < y < wy + h + margin
                       for wx, wy, w, h in self.walls)

    def new_target(self):
        for _ in range(200):
            x, y = random.uniform(20, 300), random.uniform(20, 220)
            if not self.free(x, y, T_R + 2):
                continue
            if any(math.hypot(x - b.x, y - b.y) < 70 for b in self.balls.values()):
                continue
            return [x, y]
        return [160.0, 120.0]

    def step(self, dt, tilts):
        self.t += dt
        for pp in self.pops:
            pp[1] -= 25 * dt
            pp[3] -= dt
        self.pops = [pp for pp in self.pops if pp[3] > 0]
        for rg in self.rings:
            rg[2] += 60 * dt
            rg[3] -= dt
        self.rings = [rg for rg in self.rings if rg[3] > 0]
        if self.state == "countdown":
            self.timer -= dt
            if self.timer <= 0:
                self.state = "play"
            return
        if self.state != "play":
            return
        self.since += dt
        h = dt / SUBSTEPS
        bl = list(self.balls.values())
        for _ in range(SUBSTEPS):
            for b in bl:
                tl.integrate(b, tilts[b.p], h, accel=470, friction=1.8, max_speed=260)
                for w in self.walls:
                    tl.collide_rect(b, w, bounce=0.5)
            if len(bl) == 2:
                tl.collide_balls(bl[0], bl[1], restitution=0.9)
        for b in bl:
            b.trail.append((b.x, b.y))
            del b.trail[:-6]

        tx, ty = self.target
        for b in bl:
            if math.hypot(b.x - tx, b.y - ty) < T_R:
                if self.solo:
                    self.combo = self.combo + 1 if self.since < 2.0 else 1
                    pts = 10 * min(self.combo, 5)
                    self.score[1] += pts
                    self.pops.append([tx, ty - 10, f"+{pts}" + (f"  x{min(self.combo, 5)}" if self.combo > 1 else ""),
                                      0.8, tl.C_GOLD])
                    self.hits += 1
                    if self.hits % 4 == 0:
                        self.traps.append(self.new_target() + [12.0])
                else:
                    self.score[b.p] += 1
                    self.pops.append([tx, ty - 10, "+1", 0.8, tl.PLAYER_COL[b.p]])
                self.rings.append([tx, ty, T_R, 0.4])
                self.since = 0.0
                self.target = self.new_target()
                break

        if self.solo:
            for tr in self.traps[:]:
                tr[2] -= dt
                if tr[2] <= 0:
                    self.traps.remove(tr)
                elif math.hypot(bl[0].x - tr[0], bl[0].y - tr[1]) < 9:
                    self.time_left -= 3
                    self.pops.append([tr[0], tr[1] - 10, "-3 s", 0.9, (255, 100, 90)])
                    self.traps.remove(tr)
            self.time_left -= dt
            if self.time_left <= 0:
                self.time_left = 0
                self.state = "over"
                self.record = tl.submit("targets_best", self.score[1])
        else:
            for p in (1, 2):
                if self.score[p] >= WIN_SCORE:
                    self.winner = p
                    self.state = "over"


def draw(view, g, ctrl, end):
    view.update()
    scr, W, H = view.screen, view.W, view.H
    scr.fill(tl.C_BG)
    view.field((32, 40, 52))
    for w in g.walls:
        view.wall(w)
    for x, y, ttl in g.traps:
        c = (220, 70, 70)
        s = 6
        pygame.draw.line(scr, c, view.P(x - s, y - s), view.P(x + s, y + s), max(2, int(view.L(2.5))))
        pygame.draw.line(scr, c, view.P(x + s, y - s), view.P(x - s, y + s), max(2, int(view.L(2.5))))
    tx, ty = g.target
    pulse = 1 + 0.08 * math.sin(g.t * 8)
    for i, col in enumerate(((240, 240, 240), (230, 70, 70), (240, 240, 240), (230, 70, 70))):
        pygame.draw.circle(scr, col, view.P(tx, ty), view.L(T_R * pulse * (1 - i * 0.24)))
    for x, y, r, ttl in g.rings:
        pygame.draw.circle(scr, (255, 255, 255), view.P(x, y), view.L(r), 1)
    for b in g.balls.values():
        view.ball(b)
    for x, y, txt, ttl, col in g.pops:
        view.text(txt, col, view.P(x, y), 0.04)

    if g.solo:
        tl.hud_solo(view, f"SCORE  {g.score[1]}", f"{math.ceil(g.time_left)} s", "targets_best")
    else:
        tl.hud_scores(view, ctrl, g.score, f"first to {WIN_SCORE}")
    if g.state == "countdown":
        tl.draw_countdown(view, g.timer, "roll onto the targets - quick hits = combo!" if g.solo
                          else "race to the target!")
    elif g.over:
        if g.solo:
            tl.draw_solo_result(view, f"{g.score[1]} points", g.record)
        else:
            tl.draw_match(view, g.winner, f"{g.score[1]} - {g.score[2]}")
    if end:
        end.draw(view, 0.72)


def run(ctrl, solo=True):
    tl.game_loop(ctrl, lambda: Rush(solo), draw, solo=solo)


if __name__ == "__main__":
    vs = "--vs" in sys.argv
    if vs:
        sys.argv.remove("--vs")
    tl.run_standalone(lambda c: run(c, solo=not vs))
