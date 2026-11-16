#!/usr/bin/env python3
"""
Tilt Snake (1 player) - tilt the way you want to go. Eat apples to grow,
gold apples are worth 3. Don't bite yourself. Gets faster as you grow.

Maps: Open (wrap around the edges), Walled, Obstacles, Tunnels.

Run on its own:  python3 snake.py [--fullscreen]
"""

import random

import pygame

import tiltlib as tl

CELL = 10
GW, GH = tl.FIELD_W // CELL, tl.FIELD_H // CELL      # 32 x 24
TURN = 0.25           # how far to tilt before it turns


def _border():
    return {(x, 0) for x in range(GW)} | {(x, GH - 1) for x in range(GW)} | \
           {(0, y) for y in range(GH)} | {(GW - 1, y) for y in range(GH)}


def _blocks():
    s = _border()
    for bx, by in ((7, 6), (22, 6), (7, 16), (22, 16)):
        s |= {(bx + i, by + j) for i in range(3) for j in range(2)}
    return s


def _tunnels():
    s = set()
    for x in range(4, 28):
        if not 13 <= x <= 18:
            s |= {(x, 7), (x, 16)}
    return s


MAPS = [
    dict(name="Open", desc="Go off one edge, come back on the other", walls=set, wrap=True),
    dict(name="Walled", desc="Hit the edge and it's over", walls=_border, wrap=False),
    dict(name="Obstacles", desc="Walls plus four blocks", walls=_blocks, wrap=False),
    dict(name="Tunnels", desc="Wrap-around with two long barriers", walls=_tunnels, wrap=True),
]


class Snake:
    def __init__(self, map_i):
        self.map_i = map_i
        m = MAPS[map_i]
        self.walls = m["walls"]()
        self.wrap = m["wrap"]
        self.body = [(8, GH // 2 - 1), (7, GH // 2 - 1), (6, GH // 2 - 1)]
        self.dir = (1, 0)
        self.next_dir = (1, 0)
        self.grow = 0
        self.score = 0
        self.food = None
        self.gold = None          # (cell, time left)
        self.state, self.timer = "countdown", 3.0
        self.move_t = 0.0
        self.t = 0.0
        self.record = None
        self.place_food()

    @property
    def over(self):
        return self.state == "over"

    def free_cell(self):
        taken = set(self.body) | self.walls
        for _ in range(500):
            c = (random.randrange(1, GW - 1), random.randrange(1, GH - 1))
            if c not in taken and c != self.food:
                return c
        return None

    def place_food(self):
        self.food = self.free_cell()

    def step(self, dt, tilts):
        self.t += dt
        if self.state == "countdown":
            self.timer -= dt
            if self.timer <= 0:
                self.state = "play"
            return
        if self.state != "play":
            return
        tx, ty = tilts[1]
        want = None
        if max(abs(tx), abs(ty)) > TURN:
            want = ((1 if tx > 0 else -1), 0) if abs(tx) > abs(ty) else (0, (1 if ty > 0 else -1))
        if want and want != (-self.dir[0], -self.dir[1]):
            self.next_dir = want

        if self.gold:
            c, left = self.gold
            self.gold = (c, left - dt) if left - dt > 0 else None
        elif random.random() < dt / 8:
            c = self.free_cell()
            if c:
                self.gold = (c, 6.0)

        interval = max(0.055, 0.13 - len(self.body) * 0.0018)
        self.move_t += dt
        while self.move_t >= interval and self.state == "play":
            self.move_t -= interval
            self.advance()

    def advance(self):
        self.dir = self.next_dir
        hx, hy = self.body[0]
        nx, ny = hx + self.dir[0], hy + self.dir[1]
        if self.wrap:
            nx, ny = nx % GW, ny % GH
        head = (nx, ny)
        tail_moves = self.grow == 0
        body = self.body[:-1] if tail_moves else self.body
        if not (0 <= nx < GW and 0 <= ny < GH) or head in self.walls or head in body:
            self.state = "over"
            self.record = tl.submit("snake_best", self.score)
            return
        self.body.insert(0, head)
        if tail_moves:
            self.body.pop()
        else:
            self.grow -= 1
        if head == self.food:
            self.score += 1
            self.grow += 2
            self.place_food()
        if self.gold and head == self.gold[0]:
            self.score += 3
            self.grow += 4
            self.gold = None


def draw(view, g, ctrl, end):
    view.update()
    scr, W, H = view.screen, view.W, view.H
    scr.fill(tl.C_BG)
    view.field()

    def cell(c, color, shrink=1.0, radius=2):
        pad = (1 - shrink) * CELL / 2
        x, y = view.P(c[0] * CELL + pad, c[1] * CELL + pad)
        pygame.draw.rect(scr, color, (x, y, view.L(CELL * shrink), view.L(CELL * shrink)),
                         border_radius=int(view.L(radius)))

    for c in g.walls:
        cell(c, tl.C_WALL, 1.0, 1)
    if g.food:
        cell(g.food, (230, 60, 60), 0.8, 5)
    if g.gold:
        if g.gold[1] > 1.5 or int(g.t * 8) % 2:
            cell(g.gold[0], tl.C_GOLD, 0.9, 5)
    n = len(g.body)
    for i, c in enumerate(reversed(g.body)):
        k = 0.45 + 0.55 * (i + 1) / n
        cell(c, (int(60 * k), int(220 * k), int(110 * k)), 0.92, 3)
    if g.body:
        cell(g.body[0], (150, 255, 180), 0.92, 3)

    hy = view.hud * 0.42
    bt = tl.best("snake_best")
    view.text(f"SCORE  {g.score}", tl.C_GOLD, (W * 0.2, hy), 0.06)
    view.text(MAPS[g.map_i]["name"], tl.C_DIM, (W * 0.5, hy), 0.045)
    view.text(f"best {bt}" if bt is not None else "no best yet", tl.C_DIM, (W * 0.8, hy), 0.045)

    if g.state == "countdown":
        tl.draw_countdown(view, g.timer, "tilt to steer - eat the apples")
    elif g.over:
        tl.draw_solo_result(view, f"{g.score} points", g.record)
    if end:
        end.draw(view, 0.72)


def run(ctrl):
    m = tl.pick(ctrl, "Tilt Snake - pick a map", [(x["name"], x["desc"]) for x in MAPS])
    if m is not None:
        tl.game_loop(ctrl, lambda: Snake(m), draw, solo=True)


if __name__ == "__main__":
    tl.run_standalone(run)
