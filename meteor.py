#!/usr/bin/env python3
"""
Meteor Storm - roll your marble around and dodge the meteors flying across
the arena. They come faster and more often. Grab stars for bonus points.

  1 player: survive as long as you can (best score is saved).
  2 players: last marble standing wins the round. First to 3.
  co-op: survive together. If one of you is hit, the other can roll onto
         the ghost to bring them back. Best team score is saved.

Run on its own:  python3 meteor.py [--fullscreen] [--vs | --coop]
"""

import math
import random
import sys

import pygame

import tiltlib as tl

R = 7.0
WIN_SCORE = 3
SUBSTEPS = 4
BORDER = [(0, 0, 320, 4), (0, 236, 320, 4), (0, 0, 4, 240), (316, 0, 4, 240)]
STARTS = {1: (110, 120), 2: (210, 120)}
REVIVE_T = 1.2
REVIVE_R = 16.0


class Storm:
    def __init__(self, solo=True, coop=False):
        self.solo = solo
        self.coop = coop
        self.wins = {1: 0, 2: 0}
        self.winner = None
        self.record = None
        self.t = 0.0
        self.start_round()

    def start_round(self):
        players = [1] if self.solo else [1, 2]
        self.balls = {p: tl.Ball(*(STARTS[p] if not self.solo else (160, 120)), r=R,
                                 color=tl.PLAYER_COL[p], p=p) for p in players}
        self.alive = {p: True for p in players}
        self.ghost = {}         # co-op: p -> [x, y, revive progress]
        self.inv = {p: 0.0 for p in players}
        self.meteors = []       # [x, y, vx, vy, r, warn]
        self.stars = []         # [x, y, age]
        self.sparks = []
        self.time = 0.0
        self.bonus = 0
        self.spawn_t = 1.0
        self.star_t = 3.0
        self.state, self.timer = "countdown", 2.5
        self.round_winner = None

    @property
    def over(self):
        return self.state in ("over", "match")

    @property
    def score(self):
        return int(self.time * 10) + self.bonus

    def spawn_meteor(self):
        side = random.randrange(4)
        speed = random.uniform(70, 110) + self.time * 2.2
        r = random.uniform(5, 11)
        # aim roughly at a random point in the middle of the arena
        tx, ty = random.uniform(60, 260), random.uniform(50, 190)
        x, y = [(-15, random.uniform(10, 230)), (335, random.uniform(10, 230)),
                (random.uniform(10, 310), -15), (random.uniform(10, 310), 255)][side]
        d = math.hypot(tx - x, ty - y)
        self.meteors.append([x, y, (tx - x) / d * speed, (ty - y) / d * speed, r, 0.6])

    def burst(self, x, y, col, n=20):
        for _ in range(n):
            a = random.uniform(0, math.tau)
            s = random.uniform(30, 130)
            self.sparks.append([x, y, math.cos(a) * s, math.sin(a) * s, random.uniform(0.4, 0.9), col])

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
        if self.state == "round":
            self.timer -= dt
            if self.timer <= 0:
                if max(self.wins.values()) >= WIN_SCORE:
                    self.winner = 1 if self.wins[1] > self.wins[2] else 2
                    self.state = "match"
                else:
                    self.start_round()
            return
        if self.state != "play":
            return
        self.time += dt

        # spawning
        self.spawn_t -= dt
        if self.spawn_t <= 0:
            self.spawn_meteor()
            self.spawn_t = max(0.22, 1.1 - self.time * 0.018) * random.uniform(0.7, 1.3)
        if self.solo or self.coop:
            self.star_t -= dt
            if self.star_t <= 0 and len(self.stars) < 2:
                self.stars.append([random.uniform(20, 300), random.uniform(20, 220), 0.0])
                self.star_t = random.uniform(3, 6)

        live = [b for p, b in self.balls.items() if self.alive[p]]
        h = dt / SUBSTEPS
        for _ in range(SUBSTEPS):
            for b in live:
                tl.integrate(b, tilts[b.p], h, accel=460, friction=1.6, max_speed=240)
                for w in BORDER:
                    tl.collide_rect(b, w, bounce=0.5)
            if len(live) == 2:
                tl.collide_balls(live[0], live[1], restitution=0.9)
        for b in live:
            b.trail.append((b.x, b.y))
            del b.trail[:-6]

        for m in self.meteors:
            m[0] += m[2] * dt
            m[1] += m[3] * dt
            m[5] -= dt
        self.meteors = [m for m in self.meteors if -40 < m[0] < 360 and -40 < m[1] < 280]

        for st in self.stars[:]:
            st[2] += dt
            if st[2] > 7:
                self.stars.remove(st)
                continue
            for b in live:
                if math.hypot(st[0] - b.x, st[1] - b.y) < R + 6:
                    self.bonus += 50
                    self.burst(st[0], st[1], tl.C_GOLD, 12)
                    self.stars.remove(st)
                    break

        for b in live:
            self.inv[b.p] = max(0.0, self.inv[b.p] - dt)
            if self.inv[b.p] > 0:
                continue
            for m in self.meteors:
                if math.hypot(m[0] - b.x, m[1] - b.y) < m[4] + R * 0.85:
                    self.alive[b.p] = False
                    self.burst(b.x, b.y, b.color, 30)
                    if self.coop:
                        self.ghost[b.p] = [b.x, b.y, 0.0]
                    break

        if self.coop:
            # roll onto your partner's ghost and stay there to bring them back
            for p, gh in list(self.ghost.items()):
                other = self.balls[3 - p]
                if self.alive[3 - p] and math.hypot(other.x - gh[0], other.y - gh[1]) < REVIVE_R:
                    gh[2] += dt
                    if gh[2] >= REVIVE_T:
                        b = self.balls[p]
                        b.x, b.y, b.vx, b.vy, b.trail = gh[0], gh[1], 0.0, 0.0, []
                        self.alive[p] = True
                        self.inv[p] = 2.0
                        self.bonus += 25
                        self.burst(gh[0], gh[1], tl.C_GOAL, 20)
                        del self.ghost[p]
                else:
                    gh[2] = max(0.0, gh[2] - dt * 0.5)
            if not any(self.alive.values()):
                self.state = "over"
                self.record = tl.submit("meteor_coop_best", self.score)
        elif self.solo:
            if not self.alive[1]:
                self.state = "over"
                self.record = tl.submit("meteor_best", self.score)
        else:
            left = [p for p, a in self.alive.items() if a]
            if len(left) < 2:
                self.round_winner = left[0] if left else None
                if self.round_winner:
                    self.wins[self.round_winner] += 1
                self.state, self.timer = "round", 2.2


def draw(view, g, ctrl, end):
    view.update()
    scr, W, H = view.screen, view.W, view.H
    scr.fill(tl.C_BG)
    view.field((16, 18, 34))
    random.seed(7)
    for _ in range(40):         # fixed background stars
        pygame.draw.circle(scr, (60, 64, 90), view.P(random.uniform(0, 320), random.uniform(0, 240)), 1)
    random.seed()
    for w in BORDER:
        view.wall(w)
    for x, y, age in g.stars:
        if age < 5.5 or int(age * 8) % 2:
            pts = []
            for i in range(10):
                a = -math.pi / 2 + i * math.pi / 5
                rr = 6 if i % 2 == 0 else 2.6
                pts.append(view.P(x + math.cos(a) * rr, y + math.sin(a) * rr))
            pygame.draw.polygon(scr, tl.C_GOLD, pts)
    for x, y, vx, vy, r, warn in g.meteors:
        sp = math.hypot(vx, vy) or 1
        for k in range(1, 4):
            pygame.draw.circle(scr, (120, 60, 30), view.P(x - vx / sp * r * k * 0.9, y - vy / sp * r * k * 0.9),
                               view.L(r * (1 - k * 0.22)))
        pygame.draw.circle(scr, (150, 110, 90), view.P(x, y), view.L(r))
        pygame.draw.circle(scr, (110, 80, 66), view.P(x + r * 0.3, y - r * 0.2), view.L(r * 0.35))
    for x, y, _vx, _vy, ttl, col in g.sparks:
        pygame.draw.circle(scr, col, view.P(x, y), view.L(1.4))
    for p, (gx, gy, prog) in g.ghost.items():
        col = tl.PLAYER_COL[p]
        pygame.draw.circle(scr, tuple(c // 2 for c in col), view.P(gx, gy), view.L(REVIVE_R), 1)
        pygame.draw.circle(scr, tuple(c // 3 for c in col), view.P(gx, gy), view.L(R))
        if prog > 0:
            rect = pygame.Rect(0, 0, view.L(REVIVE_R * 2), view.L(REVIVE_R * 2))
            rect.center = view.P(gx, gy)
            pygame.draw.arc(scr, tl.C_GOAL, rect, math.pi / 2, math.pi / 2 + math.tau * prog / REVIVE_T,
                            max(2, int(view.L(2))))
        if g.state == "play":
            view.text("help!", col, view.P(gx, gy - REVIVE_R - 6), 0.03)
    for p, b in g.balls.items():
        if g.alive[p] and (g.inv[p] <= 0 or int(g.t * 12) % 2):
            view.ball(b)

    if g.coop:
        tl.hud_solo(view, f"SCORE  {g.score}", f"{g.time:.1f} s", "meteor_coop_best")
    elif g.solo:
        tl.hud_solo(view, f"SCORE  {g.score}", f"{g.time:.1f} s", "meteor_best")
    else:
        tl.hud_scores(view, ctrl, g.wins, f"last one standing - first to {WIN_SCORE}")
    if g.state == "countdown":
        tl.draw_countdown(view, g.timer, "dodge the meteors together - roll onto a ghost to revive!" if g.coop
                          else "dodge the meteors!" if g.solo else "dodge - and push them into meteors!")
    elif g.state == "round":
        view.panel(0.22)
        if g.round_winner:
            view.text(f"{tl.PLAYER_NAME[g.round_winner]} SURVIVES!", tl.PLAYER_COL[g.round_winner], (W / 2, H / 2), 0.1)
        else:
            view.text("BOTH HIT!", tl.C_TEXT, (W / 2, H / 2), 0.1)
    elif g.state == "over":
        tl.draw_solo_result(view, f"{g.score} points", g.record)
    elif g.state == "match":
        tl.draw_match(view, g.winner, f"{g.wins[1]} - {g.wins[2]}")
    if end:
        end.draw(view, 0.72)


def run(ctrl, solo=True, coop=False):
    tl.game_loop(ctrl, lambda: Storm(solo and not coop, coop), draw, solo=solo and not coop)


if __name__ == "__main__":
    vs = "--vs" in sys.argv
    coop = "--coop" in sys.argv
    for f in ("--vs", "--coop"):
        if f in sys.argv:
            sys.argv.remove(f)
    tl.run_standalone(lambda c: run(c, solo=not (vs or coop), coop=coop))
