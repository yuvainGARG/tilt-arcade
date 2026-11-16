#!/usr/bin/env python3
"""
Tilt Dodge (1 player) - tilt left/right to steer, dodge the falling blocks,
grab gold coins for bonus points. It keeps getting faster. Best score is saved.

Run on its own:  python3 dodge.py [--fullscreen]
"""

import math
import random

import pygame

import tiltlib as tl

PY = 222      # player height on the field
PR = 7        # player radius


class Dodge:
    def __init__(self):
        self.ball = tl.Ball(160, PY, r=PR, color=tl.PLAYER_COL[1])
        self.vx = 0.0
        self.blocks = []    # [x, y, w, h, speed, colour]
        self.coins = []     # [x, y, speed]
        self.pops = []      # [x, y, ttl]
        self.t = 0.0
        self.score = 0.0
        self.spawn = 0.6
        self.state = "countdown"
        self.timer = 3.0
        self.record = None
        self.flash = 0.0
        self.stars = [[random.uniform(0, 320), random.uniform(0, 240), random.uniform(0.3, 1.0)]
                      for _ in range(70)]

    def speed(self):
        return min(260.0, 80.0 + 7.0 * self.t)

    def step(self, dt, tilt):
        self.flash = max(0.0, self.flash - dt)
        sp = self.speed() if self.state == "play" else 40.0
        for s in self.stars:
            s[1] += sp * 0.35 * s[2] * dt
            if s[1] > 240:
                s[1] -= 240
                s[0] = random.uniform(0, 320)
        for p in self.pops:
            p[1] -= 30 * dt
            p[2] -= dt
        self.pops = [p for p in self.pops if p[2] > 0]

        if self.state == "countdown":
            self.timer -= dt
            if self.timer <= 0:
                self.state = "play"
            return
        if self.state != "play":
            return

        self.t += dt
        self.score += dt * 10

        # steer: tilt sets target speed, ship eases toward it
        target = max(-1.2, min(1.2, tilt[0])) * 330
        self.vx += (target - self.vx) * min(1.0, 8 * dt)
        b = self.ball
        b.x += self.vx * dt
        if b.x < PR:
            b.x, self.vx = PR, 0.0
        if b.x > 320 - PR:
            b.x, self.vx = 320 - PR, 0.0
        b.trail.append((b.x, b.y + 4))
        del b.trail[:-8]

        self.spawn -= dt
        if self.spawn <= 0:
            self.spawn = max(0.22, 0.85 - 0.02 * self.t)
            w = random.uniform(16, 26 + min(40, self.t))
            hue = random.choice([(230, 90, 120), (240, 150, 70), (170, 110, 240), (90, 200, 220)])
            self.blocks.append([random.uniform(0, 320 - w), -12, w, 10, sp * random.uniform(0.85, 1.2), hue])
            if random.random() < 0.3:
                self.coins.append([random.uniform(10, 310), -6, sp * 0.9])

        for blk in self.blocks:
            blk[1] += blk[4] * dt
        self.blocks = [blk for blk in self.blocks if blk[1] < 250]
        for c in self.coins:
            c[1] += c[2] * dt
        self.coins = [c for c in self.coins if c[1] < 250]

        for x, y, w, h, _s, _c in self.blocks:
            cx = min(max(b.x, x), x + w)
            cy = min(max(PY, y), y + h)
            if (b.x - cx) ** 2 + (PY - cy) ** 2 < (PR - 1) ** 2:
                self.state = "over"
                self.flash = 0.5
                self.record = tl.submit("dodge_best", int(self.score))
                return
        for c in self.coins[:]:
            if math.hypot(c[0] - b.x, c[1] - PY) < PR + 5:
                self.coins.remove(c)
                self.score += 25
                self.pops.append([c[0], c[1], 0.8])


def draw(view, g, end):
    view.update()
    scr, W, H = view.screen, view.W, view.H
    scr.fill(tl.C_BG)
    view.field((12, 14, 26))
    for x, y, k in g.stars:
        c = int(60 + 120 * k)
        pygame.draw.circle(scr, (c, c, c + 20), view.P(x, y), max(1, view.L(0.6 * k)))

    for x, y, w, h, _s, col in g.blocks:
        rect = pygame.Rect(*view.P(x, y), view.L(w), view.L(h))
        pygame.draw.rect(scr, col, rect, border_radius=int(view.L(2)))
        pygame.draw.line(scr, tuple(min(255, v + 60) for v in col), rect.topleft, rect.topright, max(1, int(view.s / 2)))
    for x, y, _s in g.coins:
        pygame.draw.circle(scr, (150, 110, 20), view.P(x, y), view.L(5))
        pygame.draw.circle(scr, tl.C_GOLD, view.P(x, y), view.L(4))
    view.ball(g.ball)
    for x, y, ttl in g.pops:
        view.text("+25", tl.C_GOLD, view.P(x, y), 0.04)

    # clip anything outside the field (blocks entering from the top)
    pygame.draw.rect(scr, tl.C_BG, (0, 0, W, view.oy))

    bt = tl.best("dodge_best")
    view.text(f"{int(g.score)}", tl.C_TEXT, (W / 2, view.hud * 0.42), 0.07)
    view.text(f"best {bt}" if bt else "no best yet", tl.C_DIM, (W / 2, view.hud * 0.85), 0.032)
    view.text(f"speed {g.speed() / 80:.1f}x", tl.C_DIM, (W * 0.15, view.hud * 0.5), 0.04)

    if g.flash > 0:
        s = pygame.Surface((W, H), pygame.SRCALPHA)
        s.fill((255, 40, 40, int(150 * g.flash / 0.5)))
        scr.blit(s, (0, 0))
    if g.state == "countdown":
        n = math.ceil(g.timer)
        view.text(str(n) if n > 0 else "GO!", tl.C_TEXT, (W / 2, H * 0.45), 0.22)
        view.text("tilt left / right to steer", tl.C_DIM, (W / 2, H * 0.62), 0.045)
    elif g.state == "over":
        view.panel(0.6)
        is_new, rec = g.record
        view.text("CRASH!", (240, 90, 90), (W / 2, H * 0.3), 0.12)
        view.text(f"{int(g.score)} points", tl.C_TEXT, (W / 2, H * 0.45), 0.09)
        view.text("NEW HIGH SCORE!" if is_new else f"best: {rec}",
                  tl.C_GOLD if is_new else tl.C_DIM, (W / 2, H * 0.57), 0.06)
    if end:
        end.draw(view, 0.72)


def run(ctrl):
    view = tl.View()
    clock = pygame.time.Clock()
    g, end = Dodge(), None
    while True:
        dt = min(clock.tick(60) / 1000.0, 1 / 30)
        keys = tl.events()
        if pygame.K_ESCAPE in keys and g.state != "over":
            return
        g.step(dt, tl.solo_tilt(ctrl))
        if g.state == "over":
            end = end or tl.EndChoice()
            choice = end.update(ctrl, dt, keys)
            if choice == "again":
                g, end = Dodge(), None
            elif choice == "menu":
                return
        draw(view, g, end)
        pygame.display.flip()


if __name__ == "__main__":
    tl.run_standalone(run)
