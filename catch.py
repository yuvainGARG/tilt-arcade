#!/usr/bin/env python3
"""
Fruit Catch - tilt left/right to slide your basket and catch the falling fruit.
Apple = 1, orange = 2, golden star = 5. Don't catch the bombs (-5 and you're
stunned for a moment). 60 seconds, and it rains harder near the end.

  1 player: best score is saved.
  2 players: two baskets, one sky. Most points wins. Baskets bump each other.

Run on its own:  python3 catch.py [--fullscreen] [--vs]
"""

import math
import random
import sys

import pygame

import tiltlib as tl

ROUND = 60.0
BASKET_W, BASKET_Y = 40.0, 214.0
SPEED = 330.0
KINDS = {   # value, colour, radius, weight
    "apple": (1, (220, 60, 60), 5.5, 55),
    "orange": (2, (245, 150, 40), 6.0, 25),
    "star": (5, (250, 210, 60), 6.0, 6),
    "bomb": (-5, (30, 30, 36), 6.5, 18),
}


class Catch:
    def __init__(self, solo=True):
        self.solo = solo
        players = [1] if solo else [1, 2]
        self.x = {1: 160.0} if solo else {1: 100.0, 2: 220.0}
        self.vx = {p: 0.0 for p in players}
        self.score = {p: 0 for p in players}
        self.stun = {p: 0.0 for p in players}
        self.items = []          # [x, y, vy, kind, spin]
        self.pops = []           # [x, y, text, ttl, colour]
        self.time_left = ROUND
        self.spawn_t = 0.5
        self.t = 0.0
        self.state, self.timer = "countdown", 2.5
        self.record = None
        self.winner = None

    @property
    def over(self):
        return self.state == "over"

    def step(self, dt, tilts):
        self.t += dt
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
        self.time_left -= dt
        k = 1 - self.time_left / ROUND          # 0 -> 1 over the round

        # baskets
        for p in self.x:
            if self.stun[p] > 0:
                self.stun[p] -= dt
                target = 0.0
            else:
                target = tilts[p][0] * SPEED
            self.vx[p] += (target - self.vx[p]) * min(1.0, 10 * dt)
            self.x[p] += self.vx[p] * dt
            self.x[p] = max(4 + BASKET_W / 2, min(316 - BASKET_W / 2, self.x[p]))
        if not self.solo:
            gap = self.x[2] - self.x[1]
            if abs(gap) < BASKET_W:
                push = (BASKET_W - abs(gap)) / 2 * (1 if gap >= 0 else -1)
                self.x[1] -= push
                self.x[2] += push
                self.vx[1], self.vx[2] = self.vx[2] * 0.6, self.vx[1] * 0.6
                for p in (1, 2):
                    self.x[p] = max(4 + BASKET_W / 2, min(316 - BASKET_W / 2, self.x[p]))

        # spawn
        self.spawn_t -= dt
        if self.spawn_t <= 0:
            names = list(KINDS)
            kind = random.choices(names, [KINDS[n][3] for n in names])[0]
            self.items.append([random.uniform(14, 306), -10.0, random.uniform(55, 80) + 90 * k, kind,
                               random.uniform(0, math.tau)])
            rate = (0.62 - 0.38 * k) * (0.8 if not self.solo else 1.0)
            self.spawn_t = rate * random.uniform(0.6, 1.4)

        for it in self.items[:]:
            it[1] += it[2] * dt
            it[4] += dt * 3
            val, col, r, _w = KINDS[it[3]]
            caught = False
            for p in self.x:
                if abs(it[0] - self.x[p]) < BASKET_W / 2 + r * 0.4 and BASKET_Y - 4 < it[1] < BASKET_Y + 8:
                    self.score[p] += val
                    if it[3] == "bomb":
                        self.stun[p] = 1.0
                        self.score[p] = max(0, self.score[p])
                    self.pops.append([it[0], BASKET_Y - 12, f"{val:+d}", 0.8,
                                      (255, 120, 90) if val < 0 else tl.C_GOLD])
                    caught = True
                    break
            if caught or it[1] > 250:
                self.items.remove(it)

        if self.time_left <= 0:
            self.time_left = 0
            self.state = "over"
            if self.solo:
                self.record = tl.submit("catch_best", self.score[1])
            else:
                s1, s2 = self.score[1], self.score[2]
                self.winner = 1 if s1 > s2 else 2 if s2 > s1 else None


def draw_item(view, x, y, kind, spin):
    scr = view.screen
    val, col, r, _w = KINDS[kind]
    if kind == "star":
        pts = []
        for i in range(10):
            a = spin + i * math.pi / 5
            rr = r if i % 2 == 0 else r * 0.45
            pts.append(view.P(x + math.cos(a) * rr, y + math.sin(a) * rr))
        pygame.draw.polygon(scr, col, pts)
        return
    pygame.draw.circle(scr, col, view.P(x, y), view.L(r))
    if kind == "bomb":
        pygame.draw.line(scr, (140, 120, 90), view.P(x + 2, y - r + 1), view.P(x + 4, y - r - 3), 2)
        if int(spin * 4) % 2:
            pygame.draw.circle(scr, (255, 200, 60), view.P(x + 4, y - r - 3), view.L(1.6))
    else:
        pygame.draw.circle(scr, tuple(min(255, c + 70) for c in col), view.P(x - r * 0.35, y - r * 0.35), view.L(r * 0.3))
        pygame.draw.line(scr, (90, 60, 30), view.P(x, y - r), view.P(x + 1, y - r - 3), 2)
        if kind == "apple":
            pygame.draw.ellipse(scr, (80, 180, 80), (*view.P(x + 1, y - r - 3), view.L(4), view.L(2)))


def draw(view, g, ctrl, end):
    view.update()
    scr, W, H = view.screen, view.W, view.H
    scr.fill(tl.C_BG)
    view.field((40, 64, 96))
    pygame.draw.rect(scr, (60, 120, 70), (*view.P(0, 226), view.L(320), view.L(14)))
    for x, y, vy, kind, spin in g.items:
        draw_item(view, x, y, kind, spin)
    for p, x in g.x.items():
        col = tl.PLAYER_COL[p]
        if g.stun[p] > 0 and int(g.t * 12) % 2:
            col = (120, 120, 130)
        pts = [view.P(x - BASKET_W / 2, BASKET_Y), view.P(x + BASKET_W / 2, BASKET_Y),
               view.P(x + BASKET_W / 2 - 5, BASKET_Y + 11), view.P(x - BASKET_W / 2 + 5, BASKET_Y + 11)]
        pygame.draw.polygon(scr, col, pts)
        pygame.draw.line(scr, tuple(min(255, c + 60) for c in col), pts[0], pts[1], max(2, int(view.L(1.5))))
        for i in range(1, 4):
            xx = x - BASKET_W / 2 + i * BASKET_W / 4
            pygame.draw.line(scr, tuple(c // 2 for c in col), view.P(xx, BASKET_Y + 1), view.P(xx, BASKET_Y + 10))
    for x, y, txt, ttl, col in g.pops:
        view.text(txt, col, view.P(x, y), 0.04)

    secs = f"{math.ceil(g.time_left)} s"
    if g.solo:
        tl.hud_solo(view, f"SCORE  {g.score[1]}", secs, "catch_best")
    else:
        tl.hud_scores(view, ctrl, g.score, secs)
    if g.state == "countdown":
        tl.draw_countdown(view, g.timer, "tilt left / right - catch fruit, not bombs!")
    elif g.over:
        if g.solo:
            tl.draw_solo_result(view, f"{g.score[1]} points", g.record)
        else:
            tl.draw_match(view, g.winner, f"{g.score[1]} - {g.score[2]}")
    if end:
        end.draw(view, 0.72)


def run(ctrl, solo=True):
    tl.game_loop(ctrl, lambda: Catch(solo), draw, solo=solo)


if __name__ == "__main__":
    vs = "--vs" in sys.argv
    if vs:
        sys.argv.remove("--vs")
    tl.run_standalone(lambda c: run(c, solo=not vs))
