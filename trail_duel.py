#!/usr/bin/env python3
"""
Trail Duel (2 players) - you never stop moving and you leave a wall behind you.
Tilt to turn. Make the other player crash into a wall or a trail. First to 3.

Run on its own:  python3 trail_duel.py [--fullscreen]
"""

import pygame

import tiltlib as tl

CELL = 5
GW, GH = tl.FIELD_W // CELL, tl.FIELD_H // CELL     # 64 x 48
WIN_SCORE = 3
TURN = 0.25


class Duel:
    def __init__(self):
        self.score = {1: 0, 2: 0}
        self.winner = None
        self.t = 0.0
        self.start_round()

    @property
    def over(self):
        return self.state == "match"

    def start_round(self):
        self.pos = {1: (8, GH // 2), 2: (GW - 9, GH // 2)}
        self.dir = {1: (1, 0), 2: (-1, 0)}
        self.want = dict(self.dir)
        self.trail = {1: [self.pos[1]], 2: [self.pos[2]]}
        self.taken = {self.pos[1], self.pos[2]}
        self.state, self.timer = "countdown", 3.0
        self.move_t = 0.0
        self.round_t = 0.0
        self.round_winner = None
        self.crash = []

    def step(self, dt, tilts):
        self.t += dt
        if self.state == "countdown":
            self.timer -= dt
            if self.timer <= 0:
                self.state = "play"
            return
        if self.state == "crash":
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
        for p in (1, 2):
            tx, ty = tilts[p]
            if max(abs(tx), abs(ty)) > TURN:
                w = ((1 if tx > 0 else -1), 0) if abs(tx) > abs(ty) else (0, (1 if ty > 0 else -1))
                d = self.dir[p]
                if w != (-d[0], -d[1]):
                    self.want[p] = w
        self.round_t += dt
        interval = max(0.03, 0.06 - self.round_t * 0.0015)
        self.move_t += dt
        while self.move_t >= interval and self.state == "play":
            self.move_t -= interval
            self.advance()

    def advance(self):
        heads = {}
        for p in (1, 2):
            self.dir[p] = self.want[p]
            x, y = self.pos[p]
            heads[p] = (x + self.dir[p][0], y + self.dir[p][1])
        dead = set()
        for p, (x, y) in heads.items():
            if not (0 <= x < GW and 0 <= y < GH) or (x, y) in self.taken:
                dead.add(p)
        if heads[1] == heads[2]:
            dead = {1, 2}
        for p in (1, 2):
            if p not in dead:
                self.pos[p] = heads[p]
                self.trail[p].append(heads[p])
                self.taken.add(heads[p])
        if dead:
            self.crash = [self.pos[p] if p in dead else None for p in (1, 2)]
            self.state, self.timer = "crash", 2.0
            if len(dead) == 1:
                self.round_winner = 2 if 1 in dead else 1
                self.score[self.round_winner] += 1


def draw(view, g, ctrl, end):
    view.update()
    scr, W, H = view.screen, view.W, view.H
    scr.fill(tl.C_BG)
    view.field((16, 18, 28))
    grid = (26, 29, 42)
    for x in range(0, GW + 1, 4):
        pygame.draw.line(scr, grid, view.P(x * CELL, 0), view.P(x * CELL, tl.FIELD_H))
    for y in range(0, GH + 1, 4):
        pygame.draw.line(scr, grid, view.P(0, y * CELL), view.P(tl.FIELD_W, y * CELL))
    for p in (1, 2):
        c = tl.PLAYER_COL[p]
        dim = tuple(v * 2 // 3 for v in c)
        for (x, y) in g.trail[p]:
            pygame.draw.rect(scr, dim, (*view.P(x * CELL, y * CELL), view.L(CELL) + 1, view.L(CELL) + 1))
        hx, hy = g.pos[p]
        glow = tuple(min(255, v + 80) for v in c)
        pygame.draw.circle(scr, glow, view.P(hx * CELL + CELL / 2, hy * CELL + CELL / 2), view.L(CELL * 0.9))
    if g.state == "crash":
        k = 1 - g.timer / 2.0
        for c in g.crash:
            if c:
                pygame.draw.circle(scr, (255, 220, 120), view.P(c[0] * CELL + 2.5, c[1] * CELL + 2.5),
                                   view.L(4 + 20 * k), max(1, int(view.s)))

    tl.hud_scores(view, ctrl, g.score, f"first to {WIN_SCORE}")
    if g.state == "countdown":
        tl.draw_countdown(view, g.timer, "tilt to turn - don't crash!")
    elif g.state == "crash":
        view.panel(0.22)
        if g.round_winner:
            view.text(f"{tl.PLAYER_NAME[g.round_winner]} TAKES THE ROUND!", tl.PLAYER_COL[g.round_winner],
                      (W / 2, H / 2), 0.08)
        else:
            view.text("BOTH CRASHED - no point", tl.C_TEXT, (W / 2, H / 2), 0.08)
    elif g.over:
        tl.draw_match(view, g.winner, f"{g.score[1]} - {g.score[2]}")
    if end:
        end.draw(view, 0.72)


def run(ctrl):
    tl.game_loop(ctrl, Duel, draw)


if __name__ == "__main__":
    tl.run_standalone(run)
