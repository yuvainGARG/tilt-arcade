#!/usr/bin/env python3
"""
Sumo (2 players) - both marbles on a round platform. Ram the other one off
the edge! The platform starts shrinking after a few seconds. First to 3.

Run on its own:  python3 sumo.py [--fullscreen]
"""

import math

import pygame

import tiltlib as tl

CENTER = (160, 126)
R_START = 108.0
R_MIN = 48.0
SHRINK_AFTER = 8.0    # seconds before the platform starts shrinking
SHRINK_RATE = 5.0     # units per second
BR = 11.0             # marble radius (bigger = more sumo)
FALL_TIME = 0.8
WIN_SCORE = 3
SUBSTEPS = 4

MAPS = [
    dict(name="Classic Ring", desc="Round platform that shrinks", shape="circle"),
    dict(name="Square", desc="Corners are safe... until they aren't", shape="square"),
    dict(name="Donut", desc="Don't fall through the middle either", shape="donut"),
    dict(name="Ice Rink", desc="Slippery - hard to stop", shape="circle", ice=True),
]


def map_names():
    return [(m["name"], m["desc"]) for m in MAPS]


def is_out(shape, dx, dy, r):
    if shape == "square":
        return max(abs(dx), abs(dy)) > r * 0.88
    d = math.hypot(dx, dy)
    if shape == "donut":
        return d > r or d < r * 0.32
    return d > r


class Sumo:
    def __init__(self, map_i=0):
        self.map_i = map_i
        self.shape = MAPS[map_i]["shape"]
        self.friction = 0.12 if MAPS[map_i].get("ice") else 0.55
        self.balls = {
            1: tl.Ball(CENTER[0] - 50, CENTER[1], r=BR, color=tl.PLAYER_COL[1], p=1),
            2: tl.Ball(CENTER[0] + 50, CENTER[1], r=BR, color=tl.PLAYER_COL[2], p=2),
        }
        self.score = {1: 0, 2: 0}
        self.t = 0.0
        self.winner = None
        self.shake = 0.0
        self.start_round()

    def start_round(self):
        for b in self.balls.values():
            b.respawn()
        self.radius = R_START
        self.round_t = 0.0
        self.state = "countdown"
        self.timer = 3.0
        self.out = set()
        self.round_winner = None

    def step(self, dt, tilts):
        self.t += dt
        self.shake = max(0.0, self.shake - dt)
        if self.state == "countdown":
            self.timer -= dt
            if self.timer <= 0:
                self.state = "play"
            return
        if self.state == "match":
            return

        if self.state == "play":
            self.round_t += dt
            if self.round_t > SHRINK_AFTER:
                self.radius = max(R_MIN, R_START - (self.round_t - SHRINK_AFTER) * SHRINK_RATE)

        h = dt / SUBSTEPS
        a, b = self.balls[1], self.balls[2]
        for _ in range(SUBSTEPS):
            for ball in (a, b):
                if ball.falling > 0:      # drifting off the edge, no control
                    ball.x += ball.vx * h
                    ball.y += ball.vy * h
                    continue
                tl.integrate(ball, tilts[ball.p], h, accel=360, friction=self.friction, max_speed=320)
            hit = tl.collide_balls(a, b, restitution=1.25)
            if hit > 120:
                self.shake = 0.15
            for ball in (a, b):
                if ball.falling <= 0 and ball.p not in self.out:
                    if is_out(self.shape, ball.x - CENTER[0], ball.y - CENTER[1], self.radius):
                        ball.falling = FALL_TIME
                        self.out.add(ball.p)

        for ball in (a, b):
            if ball.falling > 0:
                ball.falling = max(0.001, ball.falling - dt)
            else:
                ball.trail.append((ball.x, ball.y))
                del ball.trail[:-8]

        if self.state == "play" and self.out:
            self.state = "ko"
            self.timer = FALL_TIME + 1.4
            if len(self.out) == 1:
                self.round_winner = 2 if 1 in self.out else 1
                self.score[self.round_winner] += 1
        elif self.state == "ko":
            self.timer -= dt
            if self.timer <= 0:
                if max(self.score.values()) >= WIN_SCORE:
                    self.winner = 1 if self.score[1] > self.score[2] else 2
                    self.state = "match"
                else:
                    self.start_round()


def draw(view, g, ctrl, end):
    view.update()
    scr, W, H = view.screen, view.W, view.H
    scr.fill((8, 9, 16))
    ox = math.sin(g.t * 90) * view.L(1.5) if g.shake > 0 else 0
    view.ox += ox

    cx, cy = view.P(*CENTER)
    shrinking = g.radius < R_START - 0.5
    edge = (230, 90, 70) if shrinking else (120, 130, 170)
    top = (90, 100, 140) if g.friction < 0.3 else (52, 56, 78)
    line = (140, 160, 200) if g.friction < 0.3 else (66, 70, 96)
    if g.shape == "square":
        a = view.L(g.radius * 0.88)
        pygame.draw.rect(scr, (20, 22, 34), (cx - a - 2, cy - a + view.L(6), 2 * a + 4, 2 * a + 4))
        pygame.draw.rect(scr, edge, (cx - a - view.L(2), cy - a - view.L(2), 2 * a + view.L(4), 2 * a + view.L(4)))
        pygame.draw.rect(scr, top, (cx - a, cy - a, 2 * a, 2 * a))
        pygame.draw.rect(scr, line, (cx - a * 0.55, cy - a * 0.55, a * 1.1, a * 1.1), max(1, int(view.s)))
    else:
        pygame.draw.circle(scr, (20, 22, 34), (cx, cy + view.L(6)), view.L(g.radius + 2))   # shadow
        pygame.draw.circle(scr, edge, (cx, cy), view.L(g.radius + 2))
        pygame.draw.circle(scr, top, (cx, cy), view.L(g.radius))
        pygame.draw.circle(scr, line, (cx, cy), view.L(g.radius * 0.55), max(1, int(view.s)))
        if g.shape == "donut":
            pygame.draw.circle(scr, edge, (cx, cy), view.L(g.radius * 0.32 + 2))
            pygame.draw.circle(scr, (8, 9, 16), (cx, cy), view.L(g.radius * 0.32))
        else:
            pygame.draw.circle(scr, line, (cx, cy), view.L(4))

    for b in sorted(g.balls.values(), key=lambda b: b.falling > 0, reverse=True):
        scale = (b.falling / FALL_TIME) if b.falling > 0 else 1.0
        view.ball(b, scale)

    view.ox -= ox
    hy = view.hud * 0.42
    for p, side in ((1, 0.2), (2, 0.8)):
        view.text(f"{tl.PLAYER_NAME[p]}  {g.score[p]}", tl.PLAYER_COL[p], (W * side, hy), 0.06)
        view.text(ctrl.label(p), tl.C_TEXT if ctrl.connected(p) else tl.C_DIM,
                  (W * side, view.hud * 0.85), 0.032)
    view.text(f"{MAPS[g.map_i]['name']} - first to {WIN_SCORE}", tl.C_DIM, (W / 2, view.hud * 0.5), 0.035)

    if g.state == "countdown":
        n = math.ceil(g.timer)
        view.text(str(n) if n > 0 else "FIGHT!", tl.C_TEXT, (W / 2, H * 0.45), 0.2)
        view.text("push the other marble off!", tl.C_DIM, (W / 2, H * 0.62), 0.045)
    elif g.state == "ko":
        view.panel(0.25)
        if g.round_winner:
            view.text(f"{tl.PLAYER_NAME[g.round_winner]} TAKES THE ROUND!", tl.PLAYER_COL[g.round_winner],
                      (W / 2, H / 2), 0.09)
        else:
            view.text("DOUBLE KO - no point!", tl.C_TEXT, (W / 2, H / 2), 0.09)
    elif g.state == "match":
        view.panel(0.6)
        view.text(f"{tl.PLAYER_NAME[g.winner]} WINS!", tl.PLAYER_COL[g.winner], (W / 2, H * 0.38), 0.18)
        view.text(f"{g.score[1]} - {g.score[2]}", tl.C_TEXT, (W / 2, H * 0.54), 0.07)
    if end:
        end.draw(view, 0.72)


def run(ctrl, map_i=None):
    if map_i is None:
        map_i = tl.pick(ctrl, "Sumo - pick a platform", map_names())
        if map_i is None:
            return
    view = tl.View()
    clock = pygame.time.Clock()
    g, end = Sumo(map_i), None
    while True:
        dt = min(clock.tick(60) / 1000.0, 1 / 30)
        keys = tl.events()
        if pygame.K_ESCAPE in keys and g.state != "match":
            return
        g.step(dt, {p: tl.player_tilt(ctrl, p) for p in (1, 2)})
        if g.state == "match":
            end = end or tl.EndChoice()
            choice = end.update(ctrl, dt, keys)
            if choice == "again":
                g, end = Sumo(map_i), None
            elif choice == "menu":
                return
        draw(view, g, ctrl, end)
        pygame.display.flip()


if __name__ == "__main__":
    tl.run_standalone(run)
