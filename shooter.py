#!/usr/bin/env python3
"""
Star Shooter - your ship fires by itself. Tilt to fly around the bottom of the
screen, shoot the waves of aliens, dodge their shots. Every 5th wave is a boss.
Blue capsule = one more gun: 2x, then 3x, 4x, up to 5x. No timer - it lasts
until you die, then you're back to 1x. In co-op a capsule powers up BOTH
ships, but when a ship dies only that ship loses its power.
Pink capsule = extra life.

  1 player: 3 lives, best score is saved.
  2 players (co-op): two ships, shared lives and score.

Run on its own:  python3 shooter.py [--fullscreen] [--coop]
"""

import math
import random
import sys

import pygame

import tiltlib as tl

SHIP_R = 6.0
FIRE = 0.2
LIVES = 3
MAX_POWER = 5          # most guns you can stack (5x)
TOP_LIMIT = 140.0       # ships stay below this line
SHAPES = [((240, 90, 90), 1, 10), ((240, 180, 60), 2, 20), ((160, 110, 240), 3, 40)]


class Ship:
    def __init__(self, p, x):
        self.p, self.x, self.y = p, x, 205.0
        self.vx = self.vy = 0.0
        self.fire = random.uniform(0, FIRE)
        self.power = 1          # guns: 1x..5x, kept until this ship dies
        self.lost = 0.0         # shows 'POWER LOST' for a moment
        self.inv = 2.0          # invulnerable after (re)spawn
        self.dead = 0.0         # >0 = waiting to respawn


class Shooter:
    def __init__(self, solo=True):
        self.solo = solo
        self.ships = [Ship(1, 160.0)] if solo else [Ship(1, 110.0), Ship(2, 210.0)]
        self.lives = LIVES + (0 if solo else 2)
        self.score = 0
        self.wave = 0
        self.enemies = []       # dict
        self.shots = []         # [x, y, vy, p]
        self.bombs = []         # [x, y, vx, vy]
        self.caps = []          # [x, y, kind]
        self.sparks = []
        self.t = 0.0
        self.record = None
        self.state, self.timer = "countdown", 2.0
        self.banner = 0.0

    @property
    def over(self):
        return self.state == "over"

    def next_wave(self):
        self.wave += 1
        self.banner = 1.6
        w = self.wave
        if w % 5 == 0:
            hp = 30 + 10 * w
            self.enemies.append(dict(x=160.0, y=-30.0, hx=160.0, hy=45.0, r=18.0, hp=hp, max=hp, kind=3,
                                     col=(230, 90, 160), pts=200 + 20 * w, ph=0.0, boss=True, fire=1.0))
            return
        rows = min(4, 2 + w // 3)
        cols = min(8, 5 + w // 2)
        for r in range(rows):
            col, hp, pts = SHAPES[min(2, (rows - 1 - r) * (1 + w // 4) // 3)]
            for c in range(cols):
                hx = 160 + (c - (cols - 1) / 2) * 30
                hy = 26 + r * 22
                self.enemies.append(dict(x=hx, y=hy - 140 - c * 6, hx=hx, hy=hy, r=7.0, hp=hp, max=hp, kind=hp,
                                         col=col, pts=pts, ph=random.uniform(0, math.tau), boss=False,
                                         fire=random.uniform(1.5, 6.0)))

    def burst(self, x, y, col, n=14, sp=110):
        for _ in range(n):
            a = random.uniform(0, math.tau)
            s = random.uniform(20, sp)
            self.sparks.append([x, y, math.cos(a) * s, math.sin(a) * s, random.uniform(0.3, 0.7), col])

    def hit_ship(self, s):
        if s.inv > 0 or s.dead > 0:
            return
        self.burst(s.x, s.y, tl.PLAYER_COL[s.p], 30, 140)
        self.lives -= 1
        s.dead = 1.5
        if s.power > 1:                     # only the ship that died loses its power
            s.lost = 1.5
        s.power = 1
        if self.lives <= 0:
            self.state = "over"
            self.record = tl.submit("shooter_best" if self.solo else "shooter_coop_best", self.score)

    def step(self, dt, tilts):
        self.t += dt
        for s in self.sparks:
            s[0] += s[2] * dt
            s[1] += s[3] * dt
            s[4] -= dt
        self.sparks = [s for s in self.sparks if s[4] > 0]
        self.banner = max(0.0, self.banner - dt)
        if self.state == "countdown":
            self.timer -= dt
            if self.timer <= 0:
                self.state = "play"
                self.next_wave()
            return
        if self.state != "play":
            return

        for s in self.ships:
            s.lost = max(0.0, s.lost - dt)
        # ships
        for s in self.ships:
            if s.dead > 0:
                s.dead -= dt
                if s.dead <= 0 and self.lives > 0:
                    s.x, s.y, s.vx, s.vy, s.inv = 160.0, 205.0, 0.0, 0.0, 2.0
                continue
            s.inv = max(0.0, s.inv - dt)
            tx, ty = tilts[s.p]
            s.vx += (tx * 280 - s.vx) * min(1.0, 10 * dt)
            s.vy += (ty * 220 - s.vy) * min(1.0, 10 * dt)
            s.x = max(10.0, min(310.0, s.x + s.vx * dt))
            s.y = max(TOP_LIMIT, min(228.0, s.y + s.vy * dt))
            s.fire -= dt
            if s.fire <= 0:
                s.fire = FIRE
                n = s.power
                for i in range(n):
                    self.shots.append([s.x + (i - (n - 1) / 2) * 4.5, s.y - 7 + abs(i - (n - 1) / 2), -330, s.p])

        for sh in self.shots:
            sh[1] += sh[2] * dt
        self.shots = [sh for sh in self.shots if sh[1] > -10]

        # enemies glide into formation and sway
        speed_k = 1 + 0.08 * self.wave
        live_ships = [s for s in self.ships if s.dead <= 0]
        for e in self.enemies:
            e["ph"] += dt * (0.8 if e["boss"] else 1.6)
            tx = e["hx"] + math.sin(e["ph"]) * (60 if e["boss"] else 14)
            ty = e["hy"] + (math.sin(e["ph"] * 0.7) * 12 if e["boss"] else math.sin(e["ph"] * 2) * 3)
            e["x"] += (tx - e["x"]) * min(1.0, 3 * dt)
            e["y"] += (ty - e["y"]) * min(1.0, 2 * dt)
            e["fire"] -= dt * speed_k
            if e["fire"] <= 0 and live_ships and e["y"] > 0:
                if e["boss"]:
                    for a in (-0.5, -0.25, 0, 0.25, 0.5):
                        self.bombs.append([e["x"], e["y"] + 14, math.sin(a) * 110, math.cos(a) * 110])
                    e["fire"] = 1.4
                else:
                    tgt = random.choice(live_ships)
                    dx, dy = tgt.x - e["x"], tgt.y - e["y"]
                    d = math.hypot(dx, dy) or 1
                    v = 85 + 6 * self.wave
                    self.bombs.append([e["x"], e["y"] + 6, dx / d * v * 0.4, v])
                    e["fire"] = random.uniform(3.0, 7.0)

        for b in self.bombs:
            b[0] += b[2] * dt
            b[1] += b[3] * dt
        self.bombs = [b for b in self.bombs if -10 < b[0] < 330 and b[1] < 250]
        for c in self.caps:
            c[1] += 55 * dt
        self.caps = [c for c in self.caps if c[1] < 250]

        # shots vs enemies
        for sh in self.shots[:]:
            for e in self.enemies:
                if abs(sh[0] - e["x"]) < e["r"] and abs(sh[1] - e["y"]) < e["r"]:
                    e["hp"] -= 1
                    if sh in self.shots:
                        self.shots.remove(sh)
                    if e["hp"] <= 0:
                        self.score += e["pts"]
                        self.burst(e["x"], e["y"], e["col"], 40 if e["boss"] else 14)
                        r = random.random()
                        if e["boss"] or r < 0.05:
                            self.caps.append([e["x"], e["y"], "D"])
                        elif r < 0.065:
                            self.caps.append([e["x"], e["y"], "+"])
                    break
        self.enemies = [e for e in self.enemies if e["hp"] > 0]

        for s in self.ships:
            if s.dead > 0:
                continue
            for b in self.bombs[:]:
                if math.hypot(b[0] - s.x, b[1] - s.y) < SHIP_R:
                    self.bombs.remove(b)
                    self.hit_ship(s)
                    break
            for e in self.enemies:
                if math.hypot(e["x"] - s.x, e["y"] - s.y) < e["r"] + SHIP_R - 2:
                    self.hit_ship(s)
            for c in self.caps[:]:
                if math.hypot(c[0] - s.x, c[1] - s.y) < SHIP_R + 6:
                    if c[2] == "D":
                        for sh in self.ships:           # a capsule powers up the whole team
                            sh.power = min(MAX_POWER, sh.power + 1)
                        self.burst(c[0], c[1], (90, 200, 240), 12, 60)
                    else:
                        self.lives += 1
                    self.caps.remove(c)

        if self.state == "play" and not self.enemies:
            self.score += 50 * self.wave
            self.bombs = []
            self.next_wave()


def draw_ship(view, s, t, power=1):
    scr = view.screen
    col = tl.PLAYER_COL[s.p]
    if s.inv > 0 and int(t * 12) % 2:
        return
    pts = [view.P(s.x, s.y - 8), view.P(s.x + 7, s.y + 6), view.P(s.x, s.y + 3), view.P(s.x - 7, s.y + 6)]
    if int(t * 20) % 2:
        pygame.draw.circle(scr, (255, 170, 60), view.P(s.x, s.y + 6), view.L(2.2))
    pygame.draw.polygon(scr, col, pts)
    pygame.draw.circle(scr, (220, 240, 255), view.P(s.x, s.y - 1), view.L(1.8))
    for i in range(power - 1):              # one ring per extra gun
        pygame.draw.circle(scr, (90, 200, 240), view.P(s.x, s.y), view.L(10 + i * 2.5), 1)


def draw_enemy(view, e, t):
    scr = view.screen
    x, y, r, col = e["x"], e["y"], e["r"], e["col"]
    if e["boss"]:
        pygame.draw.ellipse(scr, col, (*view.P(x - r * 1.4, y - r * 0.7), view.L(r * 2.8), view.L(r * 1.4)))
        pygame.draw.circle(scr, (250, 200, 230), view.P(x, y - r * 0.4), view.L(r * 0.6))
        for i in range(5):
            pygame.draw.circle(scr, (255, 240, 120) if int(t * 6 + i) % 2 else (120, 60, 90),
                               view.P(x - r + i * r / 2, y + r * 0.2), view.L(1.8))
        w = 60
        pygame.draw.rect(scr, (60, 30, 40), (*view.P(x - w / 2, y - r - 8), view.L(w), view.L(3)))
        pygame.draw.rect(scr, (240, 90, 120), (*view.P(x - w / 2, y - r - 8), view.L(w * e["hp"] / e["max"]), view.L(3)))
        return
    wob = math.sin(t * 8 + e["ph"]) * 1.5
    pygame.draw.circle(scr, col, view.P(x, y), view.L(r))
    pygame.draw.rect(scr, col, (*view.P(x - r, y), view.L(2 * r), view.L(r * 0.7)))
    for dx in (-r * 0.7, 0, r * 0.7):
        pygame.draw.line(scr, col, view.P(x + dx, y + r * 0.6), view.P(x + dx + wob, y + r + 2), max(1, int(view.L(1.5))))
    for dx in (-2.5, 2.5):
        pygame.draw.circle(scr, (20, 20, 30), view.P(x + dx, y - 1), view.L(1.6))
    if e["hp"] < e["max"]:
        pygame.draw.circle(scr, (255, 255, 255), view.P(x, y), view.L(r), 1)


def draw(view, g, ctrl, end):
    view.update()
    scr, W, H = view.screen, view.W, view.H
    scr.fill(tl.C_BG)
    view.field((8, 10, 22))
    random.seed(3)
    for i in range(60):
        sx = random.uniform(0, 320)
        sy = (random.uniform(0, 240) + g.t * (10 + i % 3 * 12)) % 240
        pygame.draw.circle(scr, (90, 95, 130) if i % 3 else (160, 165, 200), view.P(sx, sy), 1)
    random.seed()
    for x, y, _vy, p in g.shots:
        pygame.draw.rect(scr, tuple(min(255, c + 80) for c in tl.PLAYER_COL[p]),
                         (*view.P(x - 0.8, y - 4), max(2, view.L(1.6)), view.L(7)))
    for e in g.enemies:
        draw_enemy(view, e, g.t)
    for x, y, _vx, _vy in g.bombs:
        pygame.draw.circle(scr, (255, 120, 90), view.P(x, y), view.L(2.6))
        pygame.draw.circle(scr, (255, 230, 180), view.P(x, y), view.L(1.2))
    for x, y, k in g.caps:
        col = (80, 200, 240) if k == "D" else (240, 90, 160)
        pygame.draw.rect(scr, col, (*view.P(x - 7, y - 4), view.L(14), view.L(8)), border_radius=int(view.L(4)))
        view.text("+1x" if k == "D" else "+", (20, 20, 30), view.P(x, y), 0.026)
    if g.state != "over":
        for s in g.ships:
            if s.dead <= 0:
                draw_ship(view, s, g.t, s.power)
    for x, y, _vx, _vy, ttl, col in g.sparks:
        pygame.draw.circle(scr, col, view.P(x, y), view.L(1.4))

    key = "shooter_best" if g.solo else "shooter_coop_best"
    tl.hud_solo(view, f"SCORE  {g.score}", f"wave {g.wave}   lives {g.lives}", key)
    if g.state == "play":
        n = len(g.ships)
        for i, s in enumerate(g.ships):
            x = W / 2 if n == 1 else W * (0.32 + 0.36 * i)
            name = "" if g.solo else tl.PLAYER_NAME[s.p] + "  "
            if s.lost > 0:
                view.text(f"{name}POWER LOST!", (240, 100, 100), (x, H * 0.94), 0.045)
            elif s.power > 1:
                view.text(f"{name}{s.power}x" + ("  MAX" if s.power >= MAX_POWER else ""),
                          tl.PLAYER_COL[s.p] if not g.solo else (90, 200, 240), (x, H * 0.94), 0.05)
    if g.state == "countdown":
        tl.draw_countdown(view, g.timer, "you fire by yourself - tilt to fly and dodge" if g.solo
                          else "team up! shared lives and score")
    elif g.banner > 0 and g.state == "play":
        boss = g.wave % 5 == 0
        view.text("BOSS WAVE!" if boss else f"WAVE {g.wave}", (240, 90, 160) if boss else tl.C_TEXT,
                  (W / 2, H * 0.55), 0.09)
    if g.over:
        tl.draw_solo_result(view, f"{g.score} points", g.record)
    if end:
        end.draw(view, 0.72)


def run(ctrl, solo=True):
    tl.game_loop(ctrl, lambda: Shooter(solo), draw, solo=solo)


if __name__ == "__main__":
    coop = "--coop" in sys.argv
    if coop:
        sys.argv.remove("--coop")
    tl.run_standalone(lambda c: run(c, solo=not coop))
