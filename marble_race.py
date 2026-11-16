#!/usr/bin/env python3
"""
Marble Race - tilt your marble down the maze, dodge the holes, reach the green goal.

  2 players: race each other, first to 3 goals wins.
  1 player (Time Trial): fastest run to the goal; best time is saved.

Maps: Classic, Zigzag, Pillars, Columns (picked before the game).

Run on its own:  python3 marble_race.py [--fullscreen] [--solo]
(or pick it from the Tilt Arcade menu: python3 arcade.py)
"""

import math
import sys

import pygame

import tiltlib as tl

WIN_SCORE = 3
R = 6.0
HOLE_R = 9.0
GOAL_R = 10.0
FALL_TIME = 0.7
SUBSTEPS = 4

# ---------------------------------------------------------------- the maze
# Left half is defined once and mirrored so both players get the same course.
def _mirror_rect(r):
    x, y, w, h = r
    return (tl.FIELD_W - x - w, y, w, h)

BORDER = [(0, 0, 320, 4), (0, 236, 320, 4), (0, 0, 4, 240), (316, 0, 4, 240)]
DIVIDER = [(157, 0, 6, 146)]
CUP = (130, 190, 6, 46)       # left side of the goal cup
GOAL = (160, 218)
STARTS = {1: (20, 20), 2: (300, 20)}

# Each map: the LEFT half (player 1's side); player 2 gets the mirror image.
MAPS = [
    dict(name="Classic", desc="Two rows, four holes - the original",
         walls=[(4, 70, 113, 6), (44, 140, 113, 6), (75, 4, 6, 40), (80, 100, 6, 40), CUP],
         holes=[(125, 35), (110, 115), (60, 180), (105, 215)]),
    dict(name="Zigzag", desc="Three rows to snake through",
         walls=[(4, 50, 113, 6), (44, 100, 113, 6), (4, 150, 113, 6), CUP],
         holes=[(90, 40), (70, 66), (110, 138), (22, 125), (60, 200), (100, 215)]),
    dict(name="Pillars", desc="Open floor, lots of holes",
         walls=[(40, 40, 8, 30), (90, 20, 8, 40), (30, 110, 40, 8), (100, 90, 8, 40),
                (60, 160, 50, 8), CUP],
         holes=[(70, 60), (130, 60), (20, 150), (80, 135), (135, 140), (40, 200), (95, 205)]),
    dict(name="Columns", desc="Up and down the long lanes",
         walls=[(40, 4, 6, 190), (80, 50, 6, 186), (120, 4, 6, 176)],
         holes=[(22, 120), (55, 100), (71, 180), (95, 60), (111, 140), (140, 110)]),
]


def map_names():
    return [(m["name"], m["desc"]) for m in MAPS]


def build_map(i):
    m = MAPS[i]
    walls = BORDER + DIVIDER + m["walls"] + [_mirror_rect(r) for r in m["walls"]]
    holes = m["holes"] + [(tl.FIELD_W - x, y) for x, y in m["holes"]]
    return walls, holes


def best_key(i):
    return "maze_time" if i == 0 else f"maze_time_{i + 1}"


class Race:
    def __init__(self, solo, map_i=0):
        self.solo = solo
        self.map_i = map_i
        self.walls, self.holes = build_map(map_i)
        players = [1] if solo else [1, 2]
        self.balls = {p: tl.Ball(*STARTS[p], r=R, color=tl.PLAYER_COL[p], p=p) for p in players}
        self.score = {p: 0 for p in players}
        self.winner = None
        self.t = 0.0
        self.elapsed = 0.0
        self.falls = 0
        self.record = None   # (is_new, best) for time trial
        self.start_round()

    def start_round(self):
        for b in self.balls.values():
            b.respawn()
        self.state = "countdown"
        self.timer = 3.0
        self.elapsed = 0.0

    def step(self, dt, tilts):
        self.t += dt
        if self.state == "countdown":
            self.timer -= dt
            if self.timer <= 0:
                self.state = "play"
        elif self.state == "play":
            self.elapsed += dt
            self._physics(dt, tilts)
        elif self.state == "round":
            self.timer -= dt
            if self.timer <= 0:
                if max(self.score.values()) >= WIN_SCORE:
                    self.state = "match"
                else:
                    self.start_round()

    def _physics(self, dt, tilts):
        h = dt / SUBSTEPS
        balls = list(self.balls.values())
        for _ in range(SUBSTEPS):
            for b in balls:
                if b.falling > 0:
                    continue
                tl.integrate(b, tilts[b.p], h)
                for w in self.walls:
                    tl.collide_rect(b, w)
            if len(balls) == 2:
                tl.collide_balls(balls[0], balls[1])
            for b in balls:
                if b.falling > 0:
                    continue
                if math.hypot(b.x - GOAL[0], b.y - GOAL[1]) < GOAL_R:
                    self._goal(b.p)
                    return
                for hx, hy in self.holes:
                    if math.hypot(b.x - hx, b.y - hy) < HOLE_R - 1:
                        b.falling = FALL_TIME
                        b.x, b.y, b.vx, b.vy = hx, hy, 0.0, 0.0
                        b.trail = []
                        self.falls += 1
                        break
        for b in balls:
            if b.falling > 0:
                b.falling -= dt
                if b.falling <= 0:
                    b.respawn()
            else:
                b.trail.append((b.x, b.y))
                del b.trail[:-10]

    def _goal(self, p):
        self.winner = p
        if self.solo:
            self.state = "done"
            self.record = tl.submit(best_key(self.map_i), round(self.elapsed, 2), higher_better=False)
        else:
            self.score[p] += 1
            self.state, self.timer = "round", 2.5


def draw(view, g, ctrl, end):
    view.update()
    scr, W, H = view.screen, view.W, view.H
    scr.fill(tl.C_BG)
    view.field()

    for p in g.balls:
        x, y = STARTS[p]
        c = tl.PLAYER_COL[p]
        pygame.draw.circle(scr, (c[0] // 4, c[1] // 4, c[2] // 4), view.P(x, y), view.L(11))
    for x, y in g.holes:
        view.hole(x, y, HOLE_R)
    pulse = 0.5 + 0.5 * math.sin(g.t * 4)
    pygame.draw.circle(scr, (20, 70, 40), view.P(*GOAL), view.L(GOAL_R + 3 + 2 * pulse))
    pygame.draw.circle(scr, tl.C_GOAL, view.P(*GOAL), view.L(GOAL_R))
    for w in g.walls:
        view.wall(w)
    for b in g.balls.values():
        view.ball(b, b.falling / FALL_TIME if b.falling > 0 else 1.0)

    # HUD
    hy = view.hud * 0.4
    if g.solo:
        bt = tl.best(best_key(g.map_i))
        view.text(f"TIME  {g.elapsed:5.2f}", tl.C_TEXT, (W * 0.5, hy), 0.06)
        view.text(f"best {bt:.2f}" if bt else "no best yet", tl.C_DIM, (W * 0.5, view.hud * 0.82), 0.032)
        view.text(f"falls: {g.falls}", tl.C_DIM, (W * 0.15, hy), 0.04)
    else:
        for p, side in ((1, 0.2), (2, 0.8)):
            view.text(f"{tl.PLAYER_NAME[p]}  {g.score[p]}", tl.PLAYER_COL[p], (W * side, hy), 0.06)
            view.text(ctrl.label(p), tl.C_TEXT if ctrl.connected(p) else tl.C_DIM,
                      (W * side, view.hud * 0.82), 0.032)
        view.text(f"{MAPS[g.map_i]['name']} - first to {WIN_SCORE}", tl.C_DIM, (W / 2, view.hud * 0.5), 0.035)

    # overlays
    if g.state == "countdown":
        n = math.ceil(g.timer)
        view.text(str(n) if n > 0 else "GO!", tl.C_TEXT, (W / 2, H / 2), 0.22)
    elif g.state == "round":
        view.panel(0.3)
        view.text(f"{tl.PLAYER_NAME[g.winner]} SCORES!", tl.PLAYER_COL[g.winner], (W / 2, H / 2), 0.16)
    elif g.state == "match":
        view.panel(0.6)
        view.text(f"{tl.PLAYER_NAME[g.winner]} WINS!", tl.PLAYER_COL[g.winner], (W / 2, H * 0.4), 0.18)
        view.text(f"{g.score[1]} - {g.score[2]}", tl.C_TEXT, (W / 2, H * 0.56), 0.07)
    elif g.state == "done":
        view.panel(0.6)
        is_new, rec = g.record
        view.text(f"{g.elapsed:.2f} s", tl.C_GOAL, (W / 2, H * 0.38), 0.18)
        view.text("NEW BEST TIME!" if is_new else f"best: {rec:.2f} s",
                  tl.C_GOLD if is_new else tl.C_TEXT, (W / 2, H * 0.55), 0.07)
    if end:
        end.draw(view, 0.72)


def run(ctrl, solo=False, map_i=None):
    if map_i is None:
        map_i = tl.pick(ctrl, "Maze Time Trial - pick a maze" if solo else "Marble Race - pick a maze",
                        map_names())
        if map_i is None:
            return
    view = tl.View()
    clock = pygame.time.Clock()
    g = Race(solo, map_i)
    end = None
    while True:
        dt = min(clock.tick(60) / 1000.0, 1 / 30)
        keys = tl.events()
        over = g.state in ("match", "done")
        if pygame.K_ESCAPE in keys and not over:
            return
        tilts = {1: tl.solo_tilt(ctrl)} if solo else {p: tl.player_tilt(ctrl, p) for p in (1, 2)}
        g.step(dt, tilts)
        if g.state in ("match", "done"):
            end = end or tl.EndChoice()
            choice = end.update(ctrl, dt, keys)
            if choice == "again":
                g, end = Race(solo, map_i), None
            elif choice == "menu":
                return
        draw(view, g, ctrl, end)
        pygame.display.flip()


if __name__ == "__main__":
    tl.run_standalone(run, solo="--solo" in sys.argv)
