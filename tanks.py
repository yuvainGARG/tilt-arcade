#!/usr/bin/env python3
"""
Tank Duel (2 players) - tilt to drive. Your tank turns to face the way it's
driving and fires by itself every second. Shells bounce off walls once.
Hit the other tank to score. First to 5.

Run on its own:  python3 tanks.py [--fullscreen]
"""

import math
import random

import pygame

import tiltlib as tl

WIN_SCORE = 5
TANK_R = 8.0
SPEED = 110.0
RELOAD = 1.0
SHELL_SPEED = 190.0
BORDER = [(0, 0, 320, 4), (0, 236, 320, 4), (0, 0, 4, 240), (316, 0, 4, 240)]
MAPS = [
    dict(name="Bunkers", desc="Four blocks to hide behind",
         walls=[(70, 50, 30, 30), (220, 50, 30, 30), (70, 160, 30, 30), (220, 160, 30, 30), (150, 100, 20, 40)]),
    dict(name="Corridors", desc="Long walls - bank your shots",
         walls=[(60, 60, 200, 8), (60, 172, 200, 8), (156, 90, 8, 60)]),
    dict(name="Open Field", desc="Nowhere to hide",
         walls=[(155, 115, 10, 10)]),
]
STARTS = {1: (30, 120, 0.0), 2: (290, 120, math.pi)}


class Tank:
    def __init__(self, p):
        self.p = p
        self.reset()

    def reset(self):
        self.x, self.y, self.ang = STARTS[self.p]
        self.r = TANK_R
        self.falling = 0.0      # lets tanks use the marble collision helpers
        self.vx = self.vy = 0.0
        self.reload = RELOAD
        self.hit = 0.0


class Duel:
    def __init__(self, map_i=0):
        self.map_i = map_i
        self.walls = BORDER + MAPS[map_i]["walls"]
        self.tanks = {1: Tank(1), 2: Tank(2)}
        self.score = {1: 0, 2: 0}
        self.shells = []        # [x, y, vx, vy, bounces, owner, age]
        self.sparks = []
        self.t = 0.0
        self.winner = None
        self.state, self.timer = "countdown", 2.5

    @property
    def over(self):
        return self.state == "match"

    def burst(self, x, y, col, n=16):
        for _ in range(n):
            a = random.uniform(0, math.tau)
            s = random.uniform(20, 120)
            self.sparks.append([x, y, math.cos(a) * s, math.sin(a) * s, random.uniform(0.3, 0.8), col])

    def wall_hit(self, x, y):
        for wx, wy, w, h in self.walls:
            if wx <= x <= wx + w and wy <= y <= wy + h:
                return (wx, wy, w, h)
        return None

    def step(self, dt, tilts):
        self.t += dt
        for s in self.sparks:
            s[0] += s[2] * dt
            s[1] += s[3] * dt
            s[4] -= dt
        self.sparks = [s for s in self.sparks if s[4] > 0]
        if self.state == "countdown":
            self.timer -= dt
            if self.timer <= 0:
                self.state = "play"
            return
        if self.state == "hit":
            self.timer -= dt
            if self.timer <= 0:
                if max(self.score.values()) >= WIN_SCORE:
                    self.winner = 1 if self.score[1] > self.score[2] else 2
                    self.state = "match"
                else:
                    for tk in self.tanks.values():
                        tk.reset()
                    self.shells = []
                    self.state, self.timer = "countdown", 1.5
            return
        if self.state != "play":
            return

        for p, tk in self.tanks.items():
            tx, ty = tilts[p]
            mag = min(1.0, math.hypot(tx, ty) * 1.6)
            if mag > 0.12:
                want = math.atan2(ty, tx)
                diff = (want - tk.ang + math.pi) % math.tau - math.pi
                tk.ang += max(-5 * dt, min(5 * dt, diff))
                fwd = mag * SPEED * max(0.0, math.cos(diff))
            else:
                fwd = 0.0
            tk.vx = math.cos(tk.ang) * fwd
            tk.vy = math.sin(tk.ang) * fwd
            tk.x += tk.vx * dt
            tk.y += tk.vy * dt
            for w in self.walls:
                tl.collide_rect(tk, w, bounce=0.0)
            tk.reload -= dt
            if tk.reload <= 0:
                tk.reload = RELOAD
                sx, sy = tk.x + math.cos(tk.ang) * 12, tk.y + math.sin(tk.ang) * 12
                if not self.wall_hit(sx, sy):
                    self.shells.append([sx, sy, math.cos(tk.ang) * SHELL_SPEED, math.sin(tk.ang) * SHELL_SPEED, 1, p, 0.0])
        a, b = self.tanks[1], self.tanks[2]
        tl.collide_balls(a, b, 0.0)

        for sh in self.shells:
            steps = 3
            for _ in range(steps):
                ox, oy = sh[0], sh[1]
                sh[0] += sh[2] * dt / steps
                sh[1] += sh[3] * dt / steps
                w = self.wall_hit(sh[0], sh[1])
                if w:
                    if sh[4] <= 0:
                        sh[6] = 99
                        self.burst(sh[0], sh[1], (200, 200, 200), 5)
                        break
                    sh[4] -= 1
                    wx, wy, ww, wh = w
                    # bounce off the side we came through
                    if not (wx <= ox <= wx + ww):
                        sh[2] = -sh[2]
                    else:
                        sh[3] = -sh[3]
                    sh[0], sh[1] = ox, oy
            sh[6] += dt
        self.shells = [sh for sh in self.shells if sh[6] < 4]

        for sh in self.shells:
            for p, tk in self.tanks.items():
                if sh[5] == p and sh[4] > 0:
                    continue        # can't hit yourself until it has bounced
                if math.hypot(sh[0] - tk.x, sh[1] - tk.y) < TANK_R:
                    scorer = 2 if p == 1 else 1
                    self.score[scorer] += 1
                    self.burst(tk.x, tk.y, tl.PLAYER_COL[p], 40)
                    tk.hit = 1.0
                    self.last_hit = p
                    self.state, self.timer = "hit", 1.6
                    return


def draw_tank(view, tk, t, hidden):
    if hidden:
        return
    scr = view.screen
    col = tl.PLAYER_COL[tk.p]
    dark = tuple(c // 2 for c in col)
    ca, sa = math.cos(tk.ang), math.sin(tk.ang)

    def rot(px, py):
        return view.P(tk.x + px * ca - py * sa, tk.y + px * sa + py * ca)
    for side in (-1, 1):
        pygame.draw.polygon(scr, (40, 40, 46), [rot(-9, side * 9), rot(9, side * 9), rot(9, side * 5), rot(-9, side * 5)])
    pygame.draw.polygon(scr, col, [rot(-8, -6), rot(8, -6), rot(8, 6), rot(-8, 6)])
    pygame.draw.line(scr, dark, rot(0, 0), rot(13, 0), max(2, int(view.L(3))))
    pygame.draw.circle(scr, dark, rot(0, 0), view.L(4))
    # reload bar
    k = 1 - max(0.0, tk.reload) / RELOAD
    pygame.draw.rect(scr, (50, 50, 60), (*view.P(tk.x - 8, tk.y + 12), view.L(16), view.L(2)))
    pygame.draw.rect(scr, col, (*view.P(tk.x - 8, tk.y + 12), view.L(16 * k), view.L(2)))


def draw(view, g, ctrl, end):
    view.update()
    scr, W, H = view.screen, view.W, view.H
    scr.fill(tl.C_BG)
    view.field((70, 78, 52))
    random.seed(11)
    for _ in range(30):
        pygame.draw.circle(scr, (62, 70, 46), view.P(random.uniform(0, 320), random.uniform(0, 240)), view.L(random.uniform(4, 10)))
    random.seed()
    for w in g.walls:
        view.wall(w)
    for x, y, vx, vy, bounces, owner, age in g.shells:
        pygame.draw.circle(scr, (30, 30, 30), view.P(x, y), view.L(2.6))
        pygame.draw.circle(scr, tuple(min(255, c + 60) for c in tl.PLAYER_COL[owner]), view.P(x, y), view.L(1.8))
    for tk in g.tanks.values():
        draw_tank(view, tk, g.t, g.state == "hit" and tk.hit > 0 and tk.p == getattr(g, "last_hit", 0))
    for x, y, _vx, _vy, ttl, col in g.sparks:
        pygame.draw.circle(scr, col, view.P(x, y), view.L(1.6))

    tl.hud_scores(view, ctrl, g.score, f"first to {WIN_SCORE}")
    if g.state == "countdown":
        tl.draw_countdown(view, g.timer, "tilt to drive - you fire by yourself")
    elif g.state == "hit":
        sc = 2 if g.last_hit == 1 else 1
        view.panel(0.22)
        view.text(f"{tl.PLAYER_NAME[sc]} SCORES!", tl.PLAYER_COL[sc], (W / 2, H / 2), 0.1)
    elif g.over:
        tl.draw_match(view, g.winner, f"{g.score[1]} - {g.score[2]}")
    if end:
        end.draw(view, 0.72)


def run(ctrl, map_i=None):
    if map_i is None:
        map_i = tl.pick(ctrl, "Tank Duel - pick an arena", [(m["name"], m["desc"]) for m in MAPS])
        if map_i is None:
            return
    tl.game_loop(ctrl, lambda: Duel(map_i), draw)


if __name__ == "__main__":
    tl.run_standalone(run)
