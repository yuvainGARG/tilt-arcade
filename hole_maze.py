#!/usr/bin/env python3
"""
Hole Maze (1 player) - the classic wooden tilt labyrinth. Roll the marble
from the start to the green goal without dropping it into a hole.
Fall in and you go back to the last flag you touched. 5 levels; your total
time is saved (lower is better).

Run on its own:  python3 hole_maze.py [--fullscreen]
"""

import math

import pygame

import tiltlib as tl

CELL = 16.0
R = 5.0
HOLE_R = 6.0
SUBSTEPS = 5
FALL = 0.7

# 20 x 15 cells.  # wall   O hole   S start   G goal   F checkpoint flag   . floor
LEVELS = [
    ("First Steps", [
        "####################",
        "#S.....#...........#",
        "#......#...........#",
        "#..O...#....O......#",
        "#......#...........#",
        "#......#.....####..#",
        "#..........O.#.....#",
        "#............#..O..#",
        "######...#####.....#",
        "#.........O........#",
        "#...O..............#",
        "#.........######...#",
        "#....O....#.....O..#",
        "#.........#......G.#",
        "####################"]),
    ("Zig Zag", [
        "####################",
        "#S..O.........O....#",
        "#...........O......#",
        "##############.....#",
        "#....O.............#",
        "#..........O....O..#",
        "#.....##############",
        "#..O......F........#",
        "#.............O....#",
        "##############.....#",
        "#.O.......O........#",
        "#....O.........O...#",
        "#.....##############",
        "#.................G#",
        "####################"]),
    ("Holey Moley", [
        "####################",
        "#S.O...O...O...O...#",
        "#..................#",
        "#O...O...O...O...O.#",
        "#..................#",
        "#..O...O...O...O...#",
        "#..................#",
        "#O...O...F...O...O.#",
        "#..................#",
        "#..O...O...O...O...#",
        "#..................#",
        "#O...O...O...O...O.#",
        "#..................#",
        "#..O...O...O...O..G#",
        "####################"]),
    ("Spiral", [
        "####################",
        "#S.....O...........#",
        "#..............O...#",
        "#..#############...#",
        "#..#.....O.....#...#",
        "#O.#...........#..O#",
        "#..#..######...#...#",
        "#..#..#G...#...#...#",
        "#..#..#....O...#...#",
        "#..#..#........#...#",
        "#..#..#####..O.#.O.#",
        "#..#...........#...#",
        "#.O#....O.F....#...#",
        "#..........O.......#",
        "####################"]),
    ("Tightrope", [
        "####################",
        "#S..OOOOOOOOOOOO...#",
        "#..................#",
        "#OOOOOOOOOOOOOOO...#",
        "#..................#",
        "#..OOOOOOOOOOOOOOOO#",
        "#.......F..........#",
        "#OOOOOOOOOOOOOOO...#",
        "#..................#",
        "#..OOOOOOOOOOOOOOOO#",
        "#..................#",
        "#OOOOOOOOOOOOOOO...#",
        "#..................#",
        "#..OOOOOOOOOOOO...G#",
        "####################"]),
]


def parse(rows):
    walls, holes, flags = [], [], []
    start = goal = (24.0, 24.0)
    for r, row in enumerate(rows):
        for c, ch in enumerate(row):
            cx, cy = c * CELL + CELL / 2, r * CELL + CELL / 2
            if ch == "#":
                walls.append((c * CELL, r * CELL, CELL, CELL))
            elif ch == "O":
                holes.append((cx, cy))
            elif ch == "S":
                start = (cx, cy)
            elif ch == "G":
                goal = (cx, cy)
            elif ch == "F":
                flags.append((cx, cy))
    return walls, holes, flags, start, goal


class Maze:
    def __init__(self):
        self.level = 0
        self.total = 0.0
        self.falls = 0
        self.t = 0.0
        self.record = None
        self.load()

    @property
    def over(self):
        return self.state == "over"

    def load(self):
        name, rows = LEVELS[self.level]
        self.name = name
        self.walls, self.holes, self.flags, self.start, self.goal = parse(rows)
        self.check = self.start
        self.flag_on = set()
        self.ball = tl.Ball(*self.start, r=R, color=tl.PLAYER_COL[1], p=1)
        self.level_time = 0.0
        self.state, self.timer = "ready", 1.5

    def near_walls(self, b):
        c0, r0 = int(b.x // CELL), int(b.y // CELL)
        for x, y, w, h in self.walls:
            if abs(x / CELL - c0) <= 1 and abs(y / CELL - r0) <= 1:
                yield (x, y, w, h)

    def step(self, dt, tilts):
        self.t += dt
        if self.state == "ready":
            self.timer -= dt
            if self.timer <= 0:
                self.state = "play"
            return
        if self.state == "cleared":
            self.timer -= dt
            if self.timer <= 0:
                self.level += 1
                if self.level >= len(LEVELS):
                    self.state = "over"
                    self.record = tl.submit("hole_maze_time", round(self.total, 2), higher_better=False)
                else:
                    self.load()
            return
        if self.state != "play":
            return
        b = self.ball
        self.level_time += dt
        self.total += dt
        if b.falling > 0:
            b.falling -= dt
            if b.falling <= 0:
                b.home = self.check
                b.respawn()
            return
        h = dt / SUBSTEPS
        for _ in range(SUBSTEPS):
            tl.integrate(b, tilts[1], h, accel=380, friction=1.3, max_speed=200)
            for w in list(self.near_walls(b)):
                tl.collide_rect(b, w, bounce=0.3)
        b.trail.append((b.x, b.y))
        del b.trail[:-6]
        for hx, hy in self.holes:
            if math.hypot(b.x - hx, b.y - hy) < HOLE_R - 1:
                b.falling = FALL
                b.fx, b.fy = hx, hy
                self.falls += 1
                return
        for f in self.flags:
            if f not in self.flag_on and math.hypot(b.x - f[0], b.y - f[1]) < 10:
                self.flag_on.add(f)
                self.check = f
        if math.hypot(b.x - self.goal[0], b.y - self.goal[1]) < 8:
            self.state, self.timer = "cleared", 1.8


def draw(view, g, ctrl, end):
    view.update()
    scr, W, H = view.screen, view.W, view.H
    scr.fill(tl.C_BG)
    view.field((150, 112, 72))           # wooden board
    for i in range(0, 240, 6):
        pygame.draw.line(scr, (140, 104, 66), view.P(0, i), view.P(320, i + 3))
    for x, y in g.holes:
        view.hole(x, y, HOLE_R, rim=(90, 66, 40))
    gx, gy = g.goal
    pygame.draw.circle(scr, (20, 110, 50), view.P(gx, gy), view.L(8))
    pygame.draw.circle(scr, tl.C_GOAL, view.P(gx, gy), view.L(6))
    for f in g.flags:
        col = tl.C_GOLD if f in g.flag_on else (230, 230, 230)
        pygame.draw.line(scr, (60, 40, 20), view.P(f[0] - 3, f[1] + 6), view.P(f[0] - 3, f[1] - 7), 2)
        pygame.draw.polygon(scr, col, [view.P(f[0] - 3, f[1] - 7), view.P(f[0] + 6, f[1] - 4), view.P(f[0] - 3, f[1] - 1)])
    for w in g.walls:
        x, y, ww, hh = w
        pygame.draw.rect(scr, (96, 66, 38), (*view.P(x, y), view.L(ww) + 1, view.L(hh) + 1))
    for x, y, ww, hh in g.walls:
        pygame.draw.line(scr, (130, 92, 56), view.P(x, y), view.P(x + ww, y))
    b = g.ball
    if b.falling > 0:
        k = b.falling / FALL
        b2 = tl.Ball(b.fx + (b.x - b.fx) * k, b.fy + (b.y - b.fy) * k, r=R, color=b.color)
        view.ball(b2, scale=k)
    elif g.state != "over":
        view.ball(b)

    tl.hud_solo(view, f"{g.total:.1f} s", f"Level {g.level + 1 if g.level < len(LEVELS) else len(LEVELS)}: {g.name}",
                "hole_maze_time", "{:.1f} s")
    if g.state == "ready" and g.level == 0:
        view.text("roll to the green goal - don't fall in the holes!", tl.C_TEXT, (W / 2, H * 0.94), 0.04)
    elif g.state == "cleared":
        view.panel(0.22)
        view.text(f"LEVEL {g.level + 1} DONE  -  {g.level_time:.1f} s", tl.C_GOAL, (W / 2, H / 2), 0.08)
    elif g.over:
        tl.draw_solo_result(view, f"{g.total:.1f} s", g.record, "{:.1f} s")
        view.text(f"{g.falls} falls", tl.C_DIM, (W / 2, H * 0.62), 0.045)
    if end:
        end.draw(view, 0.75)


def run(ctrl):
    tl.game_loop(ctrl, Maze, draw, solo=True)


if __name__ == "__main__":
    tl.run_standalone(run)
