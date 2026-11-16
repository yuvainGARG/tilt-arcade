#!/usr/bin/env python3
"""
King of the Hill (2 players) - a glowing zone sits somewhere in the arena.
Your clock only runs while you're in it ALONE. Shove the other marble out!
The zone moves every few seconds and shrinks as the game goes on.
First to 20 seconds wins.

Run on its own:  python3 koth.py [--fullscreen]
"""

import math
import random

import pygame

import tiltlib as tl

GOAL = 20.0
R = 8.0
SUBSTEPS = 4
MOVE_EVERY = 7.0
BORDER = [(0, 0, 320, 4), (0, 236, 320, 4), (0, 0, 4, 240), (316, 0, 4, 240)]
BUMPERS = [(80, 60), (240, 60), (80, 180), (240, 180)]
BUMP_R = 9.0


class Hill:
    def __init__(self):
        self.balls = {1: tl.Ball(30, 120, r=R, color=tl.PLAYER_COL[1], p=1),
                      2: tl.Ball(290, 120, r=R, color=tl.PLAYER_COL[2], p=2)}
        self.held = {1: 0.0, 2: 0.0}
        self.zx, self.zy, self.zr = 160.0, 120.0, 40.0
        self.tx, self.ty = self.zx, self.zy
        self.move_t = MOVE_EVERY
        self.t = 0.0
        self.owner = None
        self.winner = None
        self.state, self.timer = "countdown", 2.5

    @property
    def over(self):
        return self.state == "over"

    def new_spot(self):
        for _ in range(50):
            x, y = random.uniform(50, 270), random.uniform(45, 195)
            if math.hypot(x - self.zx, y - self.zy) > 80:
                return x, y
        return 160.0, 120.0

    def step(self, dt, tilts):
        self.t += dt
        if self.state == "countdown":
            self.timer -= dt
            if self.timer <= 0:
                self.state = "play"
            return
        if self.state != "play":
            return
        h = dt / SUBSTEPS
        a, b = self.balls[1], self.balls[2]
        for _ in range(SUBSTEPS):
            for ball in (a, b):
                tl.integrate(ball, tilts[ball.p], h, accel=440, friction=1.5, max_speed=250)
                for w in BORDER:
                    tl.collide_rect(ball, w, bounce=0.5)
                for bx, by in BUMPERS:          # springy round bumpers
                    dx, dy = ball.x - bx, ball.y - by
                    d = math.hypot(dx, dy)
                    if 1e-6 < d < BUMP_R + R:
                        nx, ny = dx / d, dy / d
                        ball.x, ball.y = bx + nx * (BUMP_R + R), by + ny * (BUMP_R + R)
                        vn = ball.vx * nx + ball.vy * ny
                        if vn < 0:
                            ball.vx -= 2.3 * vn * nx
                            ball.vy -= 2.3 * vn * ny
            tl.collide_balls(a, b, restitution=1.0)
        for ball in (a, b):
            ball.trail.append((ball.x, ball.y))
            del ball.trail[:-6]

        # zone moves and slowly shrinks
        self.move_t -= dt
        if self.move_t <= 0:
            self.tx, self.ty = self.new_spot()
            self.move_t = MOVE_EVERY
        self.zx += (self.tx - self.zx) * min(1.0, 1.5 * dt)
        self.zy += (self.ty - self.zy) * min(1.0, 1.5 * dt)
        self.zr = max(24.0, 40.0 - self.t * 0.15)

        inside = [p for p, ball in self.balls.items() if math.hypot(ball.x - self.zx, ball.y - self.zy) < self.zr]
        self.owner = inside[0] if len(inside) == 1 else (0 if inside else None)
        if self.owner:
            self.held[self.owner] += dt
            if self.held[self.owner] >= GOAL:
                self.held[self.owner] = GOAL
                self.winner = self.owner
                self.state = "over"


def draw(view, g, ctrl, end):
    view.update()
    scr, W, H = view.screen, view.W, view.H
    scr.fill(tl.C_BG)
    view.field((36, 40, 56))
    for w in BORDER:
        view.wall(w)
    # zone
    if g.owner:
        col = tl.PLAYER_COL[g.owner]
    elif g.owner == 0:
        col = (230, 230, 230)
    else:
        col = (90, 210, 170)
    pulse = 0.5 + 0.5 * math.sin(g.t * 5)
    surf = pygame.Surface((int(view.L(g.zr * 2)) + 2, int(view.L(g.zr * 2)) + 2), pygame.SRCALPHA)
    c = surf.get_width() / 2
    pygame.draw.circle(surf, (*col, int(50 + 30 * pulse)), (c, c), view.L(g.zr))
    scr.blit(surf, (view.P(g.zx, g.zy)[0] - c, view.P(g.zx, g.zy)[1] - c))
    pygame.draw.circle(scr, col, view.P(g.zx, g.zy), view.L(g.zr), max(2, int(view.L(1.5))))
    view.text("CONTESTED" if g.owner == 0 else "", (240, 240, 240), view.P(g.zx, g.zy), 0.03)
    if g.move_t < 2 and g.state == "play":
        pygame.draw.circle(scr, (90, 210, 170), view.P(g.tx, g.ty), view.L(6), 1)
    for bx, by in BUMPERS:
        pygame.draw.circle(scr, (200, 120, 60), view.P(bx, by), view.L(BUMP_R))
        pygame.draw.circle(scr, (250, 190, 110), view.P(bx, by), view.L(BUMP_R * 0.55))
    for ball in g.balls.values():
        view.ball(ball)

    # HUD: progress bars
    hy = view.hud * 0.45
    for p, side in ((1, 0.06), (2, 0.56)):
        x0, w, hh = W * side, W * 0.38, view.hud * 0.32
        pygame.draw.rect(scr, (40, 44, 60), (x0, hy - hh / 2, w, hh), border_radius=int(hh / 2))
        pygame.draw.rect(scr, tl.PLAYER_COL[p], (x0, hy - hh / 2, w * g.held[p] / GOAL, hh), border_radius=int(hh / 2))
        view.text(f"{tl.PLAYER_NAME[p]}  {g.held[p]:.1f} / {GOAL:.0f} s", tl.C_TEXT, (x0 + w / 2, hy), 0.032)
    if g.state == "countdown":
        tl.draw_countdown(view, g.timer, "be alone in the zone to score - push them out!")
    elif g.over:
        tl.draw_match(view, g.winner, f"{g.held[1]:.1f} s - {g.held[2]:.1f} s")
    if end:
        end.draw(view, 0.72)


def run(ctrl):
    tl.game_loop(ctrl, Hill, draw)


if __name__ == "__main__":
    tl.run_standalone(run)
