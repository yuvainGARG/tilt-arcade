#!/usr/bin/env python3
"""
Tether (2 players, co-op) - your marbles are tied together with a rope.
Roll BOTH of them into the green goal without dropping either one into a
hole. If one falls, you both go back to the start. 4 levels; your team time
is saved (lower is better).

Run on its own:  python3 tether.py [--fullscreen]
"""

import math

import pygame

import tiltlib as tl

R = 5.0
HOLE_R = 6.0
ROPE = 80.0
SUBSTEPS = 5
FALL = 0.7
BORDER = [(0, 0, 320, 4), (0, 236, 320, 4), (0, 0, 4, 240), (316, 0, 4, 240)]


def _cheese():
    holes = []
    for j, y in enumerate(range(30, 231, 40)):
        for x in range(70, 271, 40):
            holes.append((x + (20 if j % 2 else 0), y))
    return [h for h in holes if h[0] < 290]


LEVELS = [
    dict(name="First Knot", walls=[(150, 4, 12, 150)],
         holes=[(90, 60), (90, 170), (215, 185), (240, 90), (200, 40)],
         starts=((30, 30), (30, 60)), goal=(275, 40)),
    dict(name="Two Lanes", walls=[(60, 116, 200, 8)],
         holes=[(110, 95), (170, 50), (230, 95), (110, 145), (170, 190), (230, 145)],
         starts=((30, 100), (30, 140)), goal=(290, 120)),
    dict(name="Swiss Cheese", walls=[], holes=_cheese(),
         starts=((25, 100), (25, 140)), goal=(295, 120)),
    dict(name="The Gate", walls=[(100, 4, 8, 96), (100, 140, 8, 96), (210, 44, 8, 152)],
         holes=[(135, 120), (160, 60), (160, 180), (245, 75), (250, 150), (60, 40), (60, 200)],
         starts=((30, 105), (30, 135)), goal=(285, 210)),
]
GOAL_R = 24.0


def tie(a, b):
    """Rope: they can't get further apart than ROPE."""
    dx, dy = b.x - a.x, b.y - a.y
    d = math.hypot(dx, dy)
    if d <= ROPE or d < 1e-6:
        return
    nx, ny = dx / d, dy / d
    ex = d - ROPE
    a.x += nx * ex / 2
    a.y += ny * ex / 2
    b.x -= nx * ex / 2
    b.y -= ny * ex / 2
    rel = (b.vx - a.vx) * nx + (b.vy - a.vy) * ny
    if rel > 0:                 # moving apart: the rope takes it
        a.vx += nx * rel / 2
        a.vy += ny * rel / 2
        b.vx -= nx * rel / 2
        b.vy -= ny * rel / 2


class Tether:
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
        lv = LEVELS[self.level]
        self.name = lv["name"]
        self.walls = BORDER + lv["walls"]
        self.holes = lv["holes"]
        self.goal = lv["goal"]
        self.balls = {p: tl.Ball(*lv["starts"][p - 1], r=R, color=tl.PLAYER_COL[p], p=p) for p in (1, 2)}
        self.fall_t = 0.0
        self.fallen = None
        self.level_time = 0.0
        self.state, self.timer = "ready", 1.5

    def in_goal(self, b):
        return math.hypot(b.x - self.goal[0], b.y - self.goal[1]) < GOAL_R - R

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
                    self.record = tl.submit("tether_time", round(self.total, 2), higher_better=False)
                else:
                    self.load()
            return
        if self.state != "play":
            return
        self.level_time += dt
        self.total += dt
        if self.fall_t > 0:
            self.fall_t -= dt
            if self.fall_t <= 0:
                for b in self.balls.values():
                    b.respawn()
                self.fallen = None
            return
        b1, b2 = self.balls[1], self.balls[2]
        h = dt / SUBSTEPS
        for _ in range(SUBSTEPS):
            for b in (b1, b2):
                tl.integrate(b, tilts[b.p], h, accel=380, friction=1.4, max_speed=190)
            tie(b1, b2)
            tl.collide_balls(b1, b2, restitution=0.5)
            for b in (b1, b2):
                for w in self.walls:
                    tl.collide_rect(b, w, bounce=0.3)
        for b in (b1, b2):
            b.trail.append((b.x, b.y))
            del b.trail[:-5]
            for hx, hy in self.holes:
                if math.hypot(b.x - hx, b.y - hy) < HOLE_R - 1:
                    self.fallen = (b.p, hx, hy, b.x, b.y)
                    self.fall_t = FALL
                    self.falls += 1
                    return
        if self.in_goal(b1) and self.in_goal(b2):
            self.state, self.timer = "cleared", 1.8


def draw(view, g, ctrl, end):
    view.update()
    scr, W, H = view.screen, view.W, view.H
    scr.fill(tl.C_BG)
    view.field((34, 70, 74))
    for i in range(0, 320, 20):
        pygame.draw.line(scr, (38, 78, 82), view.P(i, 0), view.P(i, 240))
    for x, y in g.holes:
        view.hole(x, y, HOLE_R)
    gx, gy = g.goal
    pygame.draw.circle(scr, (20, 110, 50), view.P(gx, gy), view.L(GOAL_R))
    pygame.draw.circle(scr, tl.C_GOAL, view.P(gx, gy), view.L(GOAL_R - 3), max(2, int(view.L(2))))
    for w in g.walls:
        view.wall(w)
    b1, b2 = g.balls[1], g.balls[2]
    p1, p2 = (b1.x, b1.y), (b2.x, b2.y)
    if g.fallen:
        p, fx, fy, ox, oy = g.fallen
        k = g.fall_t / FALL
        pos = (fx + (ox - fx) * k, fy + (oy - fy) * k)
        if p == 1:
            p1 = pos
        else:
            p2 = pos
    d = math.hypot(p1[0] - p2[0], p1[1] - p2[1])
    taut = d > ROPE - 3
    rc = (240, 220, 160) if taut else (170, 150, 110)
    # slack rope sags a little
    mid = ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2 + max(0.0, (ROPE - d) * 0.25))
    pts = []
    for i in range(9):
        s = i / 8
        x = (1 - s) ** 2 * p1[0] + 2 * (1 - s) * s * mid[0] + s * s * p2[0]
        y = (1 - s) ** 2 * p1[1] + 2 * (1 - s) * s * mid[1] + s * s * p2[1]
        pts.append(view.P(x, y))
    pygame.draw.lines(scr, rc, False, pts, max(2, int(view.L(1.4 if taut else 1))))
    for p, b in g.balls.items():
        if g.fallen and g.fallen[0] == p:
            k = g.fall_t / FALL
            b2_ = tl.Ball(*(p1 if p == 1 else p2), r=R, color=b.color)
            view.ball(b2_, scale=k)
        elif g.state != "over":
            view.ball(b)

    tl.hud_solo(view, f"{g.total:.1f} s", f"Level {min(g.level + 1, len(LEVELS))}: {g.name}",
                "tether_time", "{:.1f} s")
    if g.state == "ready" and g.level == 0:
        view.text("you're tied together - get BOTH marbles into the green goal", tl.C_TEXT, (W / 2, H * 0.94), 0.04)
    elif g.state == "cleared":
        view.panel(0.22)
        view.text(f"LEVEL {g.level + 1} DONE  -  {g.level_time:.1f} s", tl.C_GOAL, (W / 2, H / 2), 0.08)
    elif g.over:
        tl.draw_solo_result(view, f"{g.total:.1f} s", g.record, "{:.1f} s")
        view.text(f"{g.falls} falls", tl.C_DIM, (W / 2, H * 0.62), 0.045)
    if end:
        end.draw(view, 0.75)


def run(ctrl):
    tl.game_loop(ctrl, Tether, draw)


if __name__ == "__main__":
    tl.run_standalone(run)
