#!/usr/bin/env python3
"""
Lap Race - roll your marble round the track, clockwise, 3 laps.
You have to pass every checkpoint, so no cutting corners. Mud slows you
down, boost pads speed you up.

  1 player: time trial, best time per track is saved.
  2 players: first across the line after 3 laps wins. Bumping allowed!

Run on its own:  python3 laprace.py [--fullscreen] [--vs]
"""

import math
import sys

import pygame

import tiltlib as tl

LAPS = 3
R = 6.0
SUBSTEPS = 4
BORDER = [(0, 0, 320, 4), (0, 236, 320, 4), (0, 0, 4, 240), (316, 0, 4, 240)]
# checkpoints in order (clockwise from the start line at the top)
CPS = [(150, 4, 20, 66), (250, 110, 66, 20), (150, 170, 20, 66), (4, 110, 66, 20)]
TRACKS = [
    dict(name="Oval", desc="Nice and simple. Go fast.",
         walls=[(70, 70, 180, 100)], mud=[], boost=[(200, 20, 30, 30), (90, 190, 30, 30)]),
    dict(name="Chicane", desc="Wiggly straights and mud on the corners",
         walls=[(70, 70, 180, 100), (110, 4, 8, 40), (200, 30, 8, 40), (110, 196, 8, 40), (200, 170, 8, 40)],
         mud=[(250, 4, 66, 50), (4, 186, 66, 50)], boost=[(262, 140, 40, 24), (18, 76, 40, 24)]),
    dict(name="Pinball", desc="Pillars everywhere",
         walls=[(70, 70, 180, 100), (185, 22, 10, 10), (210, 46, 10, 10), (235, 22, 10, 10), (90, 210, 10, 10),
                (275, 80, 10, 10), (290, 150, 10, 10), (100, 195, 10, 10), (160, 210, 10, 10), (220, 190, 10, 10),
                (30, 160, 10, 10), (25, 80, 10, 10)],
         mud=[(150, 180, 40, 50)], boost=[(260, 190, 40, 30)]),
]
STARTS = {1: (130, 22), 2: (130, 50)}


def inside(x, y, r):
    rx, ry, w, h = r
    return rx <= x <= rx + w and ry <= y <= ry + h


def best_key(i):
    return f"lap_race_{i + 1}"


class Race:
    def __init__(self, solo=True, track=0):
        self.solo = solo
        self.track = track
        tr = TRACKS[track]
        self.walls = BORDER + tr["walls"]
        self.mud, self.boost = tr["mud"], tr["boost"]
        players = [1] if solo else [1, 2]
        self.balls = {p: tl.Ball(*(STARTS[p] if not solo else (130, 37)), r=R, color=tl.PLAYER_COL[p], p=p)
                      for p in players}
        self.next_cp = {p: 1 for p in players}
        self.lap = {p: 0 for p in players}
        self.lap_times = {p: [] for p in players}
        self.lap_start = {p: 0.0 for p in players}
        self.done = {p: None for p in players}
        self.time = 0.0
        self.t = 0.0
        self.flash = {}
        self.record = None
        self.winner = None
        self.state, self.timer = "countdown", 3.0

    @property
    def over(self):
        return self.state == "over"

    def step(self, dt, tilts):
        self.t += dt
        for k in list(self.flash):
            self.flash[k] -= dt
            if self.flash[k] <= 0:
                del self.flash[k]
        if self.state == "countdown":
            self.timer -= dt
            if self.timer <= 0:
                self.state = "play"
            return
        if self.state != "play":
            return
        self.time += dt
        h = dt / SUBSTEPS
        racing = [b for p, b in self.balls.items() if self.done[p] is None]
        for _ in range(SUBSTEPS):
            for b in racing:
                fr = 1.4
                if any(inside(b.x, b.y, m) for m in self.mud):
                    fr = 6.0
                tl.integrate(b, tilts[b.p], h, accel=430, friction=fr, max_speed=260)
                if any(inside(b.x, b.y, bz) for bz in self.boost):
                    sp = math.hypot(b.vx, b.vy)
                    if 1 < sp < 330:
                        b.vx *= 1 + 2.5 * h
                        b.vy *= 1 + 2.5 * h
                for w in self.walls:
                    tl.collide_rect(b, w, bounce=0.4)
            if len(racing) == 2:
                tl.collide_balls(racing[0], racing[1], restitution=0.8)
        for b in racing:
            b.trail.append((b.x, b.y))
            del b.trail[:-8]
            p = b.p
            if inside(b.x, b.y, CPS[self.next_cp[p]]):
                if self.next_cp[p] == 0:
                    self.lap[p] += 1
                    self.lap_times[p].append(self.time - self.lap_start[p])
                    self.lap_start[p] = self.time
                    self.flash[p] = 1.2
                    if self.lap[p] >= LAPS:
                        self.done[p] = self.time
                self.next_cp[p] = (self.next_cp[p] + 1) % len(CPS)

        if self.solo:
            if self.done[1] is not None:
                self.state = "over"
                self.record = tl.submit(best_key(self.track), round(self.done[1], 2), higher_better=False)
        else:
            fin = [p for p in (1, 2) if self.done[p] is not None]
            if fin:
                self.winner = fin[0] if len(fin) == 1 else min(fin, key=lambda p: self.done[p])
                self.state = "over"


def draw(view, g, ctrl, end):
    view.update()
    scr, W, H = view.screen, view.W, view.H
    scr.fill(tl.C_BG)
    view.field((70, 74, 84))
    for m in g.mud:
        pygame.draw.rect(scr, (100, 74, 48), (*view.P(m[0], m[1]), view.L(m[2]), view.L(m[3])), border_radius=int(view.L(6)))
    for bz in g.boost:
        x, y, w, h = bz
        pygame.draw.rect(scr, (40, 120, 150), (*view.P(x, y), view.L(w), view.L(h)), border_radius=int(view.L(3)))
        off = (g.t * 3) % 1
        view.text(">>", (140, 230, 250), view.P(x + w / 2 + off * 3, y + h / 2), 0.035)
    # start / finish line (chequered)
    x, y, w, h = CPS[0]
    sq = 5.5
    for i in range(int(h / sq) + 1):
        for j in range(2):
            col = (240, 240, 240) if (i + j) % 2 else (20, 20, 24)
            pygame.draw.rect(scr, col, (*view.P(x + 7 + j * sq, y + i * sq), view.L(sq) + 1, view.L(min(sq, y + h - (y + i * sq)))))
    # arrows show the direction
    for ax, ay, ang in ((280, 37, 0.8), (283, 203, 2.4), (37, 203, 3.9), (37, 37, 5.5)):
        pts = [(8, 0), (-5, -6), (-2, 0), (-5, 6)]
        ca, sa = math.cos(ang), math.sin(ang)
        pygame.draw.polygon(scr, (95, 100, 112), [view.P(ax + px * ca - py * sa, ay + px * sa + py * ca) for px, py in pts])
    for wl in g.walls:
        if wl[2] > 100 and wl[3] > 60:
            pygame.draw.rect(scr, (50, 110, 60), (*view.P(wl[0], wl[1]), view.L(wl[2]), view.L(wl[3])))
            pygame.draw.rect(scr, (210, 60, 60), (*view.P(wl[0], wl[1]), view.L(wl[2]), view.L(wl[3])), max(2, int(view.L(2))))
        else:
            view.wall(wl)
    view.text(TRACKS[g.track]["name"].upper(), (80, 150, 90), view.P(160, 120), 0.07)
    for b in g.balls.values():
        view.ball(b)

    if g.solo:
        lap = min(LAPS, g.lap[1] + 1)
        tl.hud_solo(view, f"{g.time:.2f} s", f"lap {lap}/{LAPS}", best_key(g.track), "{:.2f} s")
    else:
        hy = view.hud * 0.42
        for p, side in ((1, 0.2), (2, 0.8)):
            view.text(f"{tl.PLAYER_NAME[p]}  lap {min(LAPS, g.lap[p] + 1)}/{LAPS}", tl.PLAYER_COL[p], (W * side, hy), 0.05)
        view.text(f"{g.time:.1f} s", tl.C_TEXT, (W / 2, hy), 0.045)
    for p, k in g.flash.items():
        if g.lap_times[p] and g.state == "play":
            b = g.balls[p]
            view.text(f"lap {g.lap_times[p][-1]:.2f}s", tl.PLAYER_COL[p], view.P(b.x, b.y - 14), 0.03)
    if g.state == "countdown":
        tl.draw_countdown(view, g.timer, f"{LAPS} laps, clockwise - follow the arrows")
    elif g.over:
        if g.solo:
            tl.draw_solo_result(view, f"{g.done[1]:.2f} s", g.record, "{:.2f} s")
            if g.lap_times[1]:
                view.text("best lap " + f"{min(g.lap_times[1]):.2f} s", tl.C_DIM, (W / 2, H * 0.62), 0.04)
        else:
            tl.draw_match(view, g.winner, f"{g.time:.2f} s")
    if end:
        end.draw(view, 0.75)


def run(ctrl, solo=True, track=None):
    if track is None:
        track = tl.pick(ctrl, "Lap Race - pick a track", [(t["name"], t["desc"]) for t in TRACKS])
        if track is None:
            return
    tl.game_loop(ctrl, lambda: Race(solo, track), draw, solo=solo)


if __name__ == "__main__":
    vs = "--vs" in sys.argv
    if vs:
        sys.argv.remove("--vs")
    tl.run_standalone(lambda c: run(c, solo=not vs))
