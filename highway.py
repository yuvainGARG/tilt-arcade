#!/usr/bin/env python3
"""
Highway (1 player) - weave through traffic. Tilt left/right to steer,
tilt up (like rolling a marble up the screen) to go faster, down to brake. Traffic gets
heavier the further you go. Grab the coins on the road for bonus points.

Run on its own:  python3 highway.py [--fullscreen]
"""

import math
import random

import pygame

import tiltlib as tl

ROAD_X0, ROAD_X1 = 70.0, 250.0
LANES = 4
LANE_W = (ROAD_X1 - ROAD_X0) / LANES
CAR_W, CAR_H = 16.0, 28.0
PLAYER_Y = 190.0
CAR_COLS = [(230, 230, 235), (240, 200, 60), (90, 200, 120), (170, 110, 230), (240, 140, 60), (90, 200, 220)]


def lane_x(i):
    return ROAD_X0 + LANE_W * (i + 0.5)


class Highway:
    def __init__(self):
        self.x = lane_x(1.5)
        self.vx = 0.0
        self.speed = 120.0          # road scroll speed
        self.dist = 0.0
        self.bonus = 0
        self.cars = []              # [x, y, speed, colour]
        self.coins = []             # [x, y]
        self.scroll = 0.0
        self.spawn_t = 1.0
        self.coin_t = 2.0
        self.t = 0.0
        self.state, self.timer = "countdown", 2.5
        self.record = None
        self.crash = None
        self.sparks = []

    @property
    def over(self):
        return self.state == "over"

    @property
    def score(self):
        return int(self.dist / 20) + self.bonus

    def spawn_car(self):
        lane = random.randrange(LANES)
        # always leave at least 2 lanes open where cars come in, so there's a way through
        busy = {round((c[0] - ROAD_X0) / LANE_W - 0.5) for c in self.cars if c[1] < 70}
        if lane in busy or len(busy) + 1 > LANES - 2:
            return
        self.cars.append([lane_x(lane), -CAR_H, random.uniform(40, 80), random.choice(CAR_COLS)])

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
        if self.state != "play":
            return
        tx, ty = tilts[1]
        base = 120 + min(110.0, self.dist * 0.004)
        target = base * (1 - ty * 0.55)            # tilt up the screen (negative y) = faster
        self.speed += (target - self.speed) * min(1.0, 2.5 * dt)
        self.vx += (tx * 260 - self.vx) * min(1.0, 9 * dt)
        self.x = max(ROAD_X0 + CAR_W / 2 + 2, min(ROAD_X1 - CAR_W / 2 - 2, self.x + self.vx * dt))
        self.dist += self.speed * dt
        self.scroll = (self.scroll + self.speed * dt) % 40

        self.spawn_t -= dt
        if self.spawn_t <= 0:
            self.spawn_car()
            self.spawn_t = max(0.35, 1.3 - self.dist * 0.00004) * random.uniform(0.6, 1.3) * 120 / self.speed
        self.coin_t -= dt
        if self.coin_t <= 0:
            self.coins.append([lane_x(random.randrange(LANES)), -10.0])
            self.coin_t = random.uniform(1.5, 3.5)

        for c in self.cars:
            c[1] += (self.speed - c[2]) * dt
        # a car that catches up with the one in front slows down to match it (no driving through)
        by_lane = {}
        for c in self.cars:
            by_lane.setdefault(c[0], []).append(c)
        for cs in by_lane.values():
            cs.sort(key=lambda c: -c[1])            # front-most (lowest on screen) first
            for front, back in zip(cs, cs[1:]):
                if front[1] - back[1] < CAR_H + 6:
                    back[1] = front[1] - CAR_H - 6
                    back[2] = front[2]
        self.cars = [c for c in self.cars if c[1] < 280]
        for c in self.coins:
            c[1] += self.speed * dt
        self.coins = [c for c in self.coins if c[1] < 260]

        for c in self.coins[:]:
            if abs(c[0] - self.x) < CAR_W / 2 + 4 and abs(c[1] - PLAYER_Y) < CAR_H / 2 + 4:
                self.bonus += 20
                self.coins.remove(c)
                for _ in range(8):
                    a = random.uniform(0, math.tau)
                    self.sparks.append([c[0], c[1], math.cos(a) * 50, math.sin(a) * 50, 0.4, tl.C_GOLD])
        for c in self.cars:
            if abs(c[0] - self.x) < CAR_W - 3 and abs(c[1] - PLAYER_Y) < CAR_H - 4:
                self.state = "over"
                self.crash = (self.x, PLAYER_Y)
                self.record = tl.submit("highway_best", self.score)
                for _ in range(35):
                    a = random.uniform(0, math.tau)
                    sp = random.uniform(30, 140)
                    self.sparks.append([self.x, PLAYER_Y, math.cos(a) * sp, math.sin(a) * sp,
                                        random.uniform(0.4, 1.0), random.choice([(255, 170, 60), (255, 90, 50)])])
                break


def draw_car(view, x, y, col, lights=False):
    scr = view.screen
    pygame.draw.rect(scr, (10, 10, 14), (*view.P(x - CAR_W / 2 + 1.5, y - CAR_H / 2 + 2), view.L(CAR_W), view.L(CAR_H)),
                     border_radius=int(view.L(4)))
    pygame.draw.rect(scr, col, (*view.P(x - CAR_W / 2, y - CAR_H / 2), view.L(CAR_W), view.L(CAR_H)),
                     border_radius=int(view.L(4)))
    glass = (40, 50, 70)
    pygame.draw.rect(scr, glass, (*view.P(x - CAR_W / 2 + 2.5, y - CAR_H / 2 + 6), view.L(CAR_W - 5), view.L(6)),
                     border_radius=int(view.L(2)))
    pygame.draw.rect(scr, glass, (*view.P(x - CAR_W / 2 + 2.5, y + CAR_H / 2 - 9), view.L(CAR_W - 5), view.L(4)),
                     border_radius=int(view.L(2)))
    if lights:
        for dx in (-5, 5):
            pygame.draw.circle(scr, (255, 250, 200), view.P(x + dx, y - CAR_H / 2 + 1), view.L(1.6))


def draw(view, g, ctrl, end):
    view.update()
    scr, W, H = view.screen, view.W, view.H
    scr.fill(tl.C_BG)
    view.field((50, 110, 60))
    pygame.draw.rect(scr, (52, 54, 62), (*view.P(ROAD_X0, 0), view.L(ROAD_X1 - ROAD_X0), view.L(240)))
    for xe in (ROAD_X0, ROAD_X1 - 3):
        pygame.draw.rect(scr, (230, 230, 230), (*view.P(xe, 0), view.L(3), view.L(240)))
    for i in range(1, LANES):
        x = ROAD_X0 + i * LANE_W
        y = -40 + g.scroll
        while y < 240:
            pygame.draw.rect(scr, (210, 210, 200), (*view.P(x - 1, y), view.L(2), view.L(18)))
            y += 40
    # roadside trees scroll by
    for side in (35, 285):
        y = -60 + (g.scroll * 1.5) % 60
        while y < 260:
            pygame.draw.circle(scr, (30, 80, 40), view.P(side, y), view.L(10))
            y += 60
    for x, y in g.coins:
        pygame.draw.circle(scr, tl.C_GOLD, view.P(x, y), view.L(5))
        pygame.draw.circle(scr, (200, 150, 30), view.P(x, y), view.L(3), 1)
    for x, y, _sp, col in g.cars:
        draw_car(view, x, y, col)
    if not g.over:
        draw_car(view, g.x, PLAYER_Y, tl.PLAYER_COL[1], lights=True)
    for x, y, _vx, _vy, ttl, col in g.sparks:
        pygame.draw.circle(scr, col, view.P(x, y), view.L(1.6))

    tl.hud_solo(view, f"SCORE  {g.score}", f"{g.speed * 0.6:.0f} km/h", "highway_best")
    if g.state == "countdown":
        tl.draw_countdown(view, g.timer, "tilt left/right to steer, tilt up = faster")
    elif g.over:
        tl.draw_solo_result(view, f"{g.score} points", g.record)
    if end:
        end.draw(view, 0.72)


def run(ctrl):
    tl.game_loop(ctrl, Highway, draw, solo=True)


if __name__ == "__main__":
    tl.run_standalone(run)
