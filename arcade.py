#!/usr/bin/env python3
"""
Tilt Arcade - game menu for the ESP32 + ADXL345 tilt controllers.

Menu controls
  Controller: tilt forward/back to choose, hold tilt RIGHT to start
  Keyboard:   up/down to choose, Enter/Space to start, Esc to quit
  Mouse:      click a game (click again to start)

Run:  python3 arcade.py            (fullscreen)
      python3 arcade.py --window
"""

import math
import random
import sys

import pygame

import tiltlib as tl
import balance
import bricks
import catch
import cave
import coins
import defend
import dodge
import highway
import hole_maze
import hockey
import koth
import laprace
import laser
import marble_race
import meteor
import paint
import paint_coop
import pong
import settings_page
import shooter
import potato
import snake
import sumo
import tanks
import targets
import tether
import trail_duel
import vault

GAMES = [
    dict(name="Random 1P game", tag="?", desc="Can't decide? Let the arcade pick a 1-player game",
         run=lambda c: random_game(c, "1P")),
    dict(name="Random 2P game", tag="?", desc="Let the arcade pick a 2-player game",
         run=lambda c: random_game(c, "2P")),
    dict(name="Random Co-op game", tag="?", desc="Let the arcade pick a team-up game for two",
         run=lambda c: random_game(c, "CO-OP")),
    # ---- 1 player
    dict(name="Tilt Dodge", tag="1P", desc="Steer left/right and dodge the falling blocks",
         run=dodge.run, best=("dodge_best", "{} pts")),
    dict(name="Maze Time Trial", tag="1P", desc="Fastest run through the marble maze - 4 mazes",
         run=lambda c: marble_race.run(c, solo=True), best=("maze_time", "{:.2f} s")),
    dict(name="Coin Rush", tag="1P", desc="Grab coins for 45 s while holes open up - 4 arenas",
         run=lambda c: coins.run(c, solo=True), best=("coins_best", "{} coins")),
    dict(name="Tilt Snake", tag="1P", desc="Eat apples, grow longer, don't bite yourself - 4 maps",
         run=snake.run, best=("snake_best", "{} pts")),
    dict(name="Brick Breaker", tag="1P", desc="Tilt the paddle, smash every brick - 6 levels",
         run=bricks.run, best=("bricks_best", "{} pts")),
    dict(name="Cave Flyer", tag="1P", desc="Fly through an endless cave that keeps narrowing",
         run=cave.run, best=("cave_best", "{} pts")),
    dict(name="Pong vs CPU", tag="1P", desc="Tilt forward/back to move - Easy, Normal or Hard",
         run=lambda c: pong.run(c, solo=True)),
    dict(name="Hole Maze", tag="1P", desc="Wooden tilt labyrinth - don't drop it in a hole - 5 levels",
         run=hole_maze.run, best=("hole_maze_time", "{:.1f} s")),
    dict(name="Meteor Storm", tag="1P", desc="Dodge the meteors as long as you can, grab stars",
         run=lambda c: meteor.run(c, solo=True), best=("meteor_best", "{} pts")),
    dict(name="Fruit Catch", tag="1P", desc="Catch the falling fruit with your basket, not the bombs",
         run=lambda c: catch.run(c, solo=True), best=("catch_best", "{} pts")),
    dict(name="Highway", tag="1P", desc="Weave through traffic - tilt up to go faster",
         run=highway.run, best=("highway_best", "{} pts")),
    dict(name="Star Shooter", tag="1P", desc="Auto-fire space shooter - waves and bosses",
         run=lambda c: shooter.run(c, solo=True), best=("shooter_best", "{} pts")),
    dict(name="Lap Race Time Trial", tag="1P", desc="3 laps against the clock - 3 tracks",
         run=lambda c: laprace.run(c, solo=True)),
    dict(name="Target Rush", tag="1P", desc="Hit as many targets as you can in 40 s",
         run=lambda c: targets.run(c, solo=True), best=("targets_best", "{} pts")),
    dict(name="Balance Beam", tag="1P", desc="Tip the beam, keep the ball in the zone, mind the wind",
         run=balance.run, best=("balance_best", "{} pts")),
    # ---- 2 players
    dict(name="Marble Race", tag="2P", desc="Race down the maze - first to 3 goals - 4 mazes",
         run=lambda c: marble_race.run(c, solo=False)),
    dict(name="Sumo", tag="2P", desc="Knock the other marble off - 4 platforms",
         run=sumo.run),
    dict(name="Coin Rush VS", tag="2P", desc="Most coins in 45 s wins - 4 arenas",
         run=lambda c: coins.run(c, solo=False)),
    dict(name="Marble Hockey", tag="2P", desc="Smash the puck into their goal - first to 5",
         run=hockey.run),
    dict(name="Paint Wars", tag="2P", desc="Paint more of the floor than them in 45 s",
         run=paint.run),
    dict(name="Hot Potato", tag="2P", desc="Pass the bomb by bumping - don't hold it when it blows",
         run=potato.run),
    dict(name="Trail Duel", tag="2P", desc="Leave a wall behind you - make them crash",
         run=trail_duel.run),
    dict(name="Pong", tag="2P", desc="Classic paddles, BLUE left vs RED right",
         run=lambda c: pong.run(c, solo=False)),
    dict(name="Cave Flyer VS", tag="2P", desc="Same cave, bump them into the rock - first to 3",
         run=lambda c: cave.run(c, solo=False)),
    dict(name="Meteor Storm VS", tag="2P", desc="Last marble standing - push them into a meteor",
         run=lambda c: meteor.run(c, solo=False)),
    dict(name="Fruit Catch VS", tag="2P", desc="Two baskets, one sky - most points in 60 s",
         run=lambda c: catch.run(c, solo=False)),
    dict(name="Tank Duel", tag="2P", desc="Tilt to drive, auto-fire, bouncing shells - first to 5",
         run=tanks.run),
    dict(name="King of the Hill", tag="2P", desc="Be alone in the zone - first to 20 s",
         run=koth.run),
    dict(name="Lap Race", tag="2P", desc="3 laps, bumping allowed - 3 tracks",
         run=lambda c: laprace.run(c, solo=False)),
    dict(name="Target Rush VS", tag="2P", desc="Race to the same target - first to 15",
         run=lambda c: targets.run(c, solo=False)),

    dict(name="Star Shooter Co-op", tag="CO-OP", desc="Team up against the aliens - shared lives and gun power",
         run=lambda c: shooter.run(c, solo=False), best=("shooter_coop_best", "{} pts")),
    dict(name="Tether", tag="CO-OP", desc="Tied together by a rope - both into the goal - 4 levels",
         run=tether.run, best=("tether_time", "{:.1f} s")),
    dict(name="Laser Link", tag="CO-OP", desc="A laser joins your marbles - sweep it across the bugs",
         run=laser.run, best=("laser_best", "{} pts")),
    dict(name="Core Defense", tag="CO-OP", desc="Squash the slimes before they reach the crystal",
         run=defend.run, best=("defend_best", "{} pts")),
    dict(name="Switch Vault", tag="CO-OP", desc="Hold the plates to open doors for each other - 4 vaults",
         run=vault.run, best=("vault_time", "{:.1f} s")),
    dict(name="Paint Together", tag="CO-OP", desc="Paint 75% of the floor, bump the eraser robots",
         run=paint_coop.run, best=("paint_coop_best", "{} pts")),
    dict(name="Meteor Storm Co-op", tag="CO-OP", desc="Survive together - roll onto a ghost to revive them",
         run=lambda c: meteor.run(c, coop=True), best=("meteor_coop_best", "{} pts")),

    dict(name="Settings", tag="", desc="Which controller is P1, colours, holding it sideways, inverting",
         run=settings_page.run),
    dict(name="Quit", tag="", desc="Close Tilt Arcade", run=None),
]
VISIBLE = 8           # rows shown at once; the list scrolls

TAG_COL = {"1P": tl.C_GOLD, "2P": (180, 120, 250), "CO-OP": (90, 190, 250), "?": (90, 210, 170), "": tl.C_DIM}
_last_random = {}


def random_game(ctrl, tag):
    """Spin through the games of this type, land on one, then play it."""
    pool = [g for g in GAMES if g["tag"] == tag]
    if len(pool) > 1 and _last_random.get(tag) in pool:
        pool_pick = [g for g in pool if g is not _last_random[tag]]
    else:
        pool_pick = pool
    chosen = random.choice(pool_pick)
    _last_random[tag] = chosen
    view = tl.View()
    clock = pygame.time.Clock()
    spin, t, i, step = 2.2, 0.0, random.randrange(len(pool)), 0.0
    while t < spin + 1.4:
        dt = min(clock.tick(60) / 1000.0, 1 / 30)
        t += dt
        if pygame.K_ESCAPE in tl.events():
            return
        if t < spin:
            step += dt
            if step > 0.05 + 0.25 * (t / spin) ** 2:      # slows down like a wheel
                step = 0.0
                i = (i + 1) % len(pool)
            shown = pool[i]
        else:
            shown = chosen
        view.update()
        scr, W, H = view.screen, view.W, view.H
        scr.fill(tl.C_BG)
        view.text(f"RANDOM {tag} GAME", TAG_COL["?"], (W / 2, H * 0.25), 0.07)
        col = tl.C_GOLD if t >= spin else tl.C_TEXT
        view.text(shown["name"], col, (W / 2, H * 0.46), 0.13)
        view.text(shown["desc"], tl.C_DIM, (W / 2, H * 0.58), 0.04)
        if t >= spin:
            view.text("get ready!", tl.C_TEXT, (W / 2, H * 0.72), 0.05)
        pygame.display.flip()
    chosen["run"](ctrl)


def draw_menu(view, sel, hold, ctrl, t, first):
    view.update()
    scr, W, H = view.screen, view.W, view.H
    scr.fill(tl.C_BG)

    # little marbles rolling across the top for decoration
    for i, p in enumerate((1, 2)):
        x = (t * 90 + i * W / 2) % (W + 60) - 30
        y = H * 0.045 + math.sin(t * 2 + i) * H * 0.008
        pygame.draw.circle(scr, tl.PLAYER_COL[p], (x, y), H * 0.014)

    view.text("TILT ARCADE", tl.C_TEXT, (W / 2, H * 0.1), 0.1)
    status = []
    for p in (1, 2):
        on = ctrl.connected(p)
        status.append((f"{tl.PLAYER_NAME[p]} controller: {'connected' if on else ctrl.status[tl.DEV[p]]}",
                       tl.PLAYER_COL[p] if on else tl.C_DIM))
    view.text(status[0][0], status[0][1], (W * 0.33, H * 0.17), 0.032)
    view.text(status[1][0], status[1][1], (W * 0.67, H * 0.17), 0.032)

    top, bottom = H * 0.21, H * 0.89
    rh = (bottom - top) / VISIBLE
    cw = min(W * 0.8, H * 1.3)
    x0 = (W - cw) / 2
    rects = []
    for i, gm in enumerate(GAMES):
        if not first <= i < first + VISIBLE:
            rects.append(pygame.Rect(0, 0, 0, 0))
            continue
        y = top + (i - first) * rh
        rect = pygame.Rect(x0, y + rh * 0.08, cw, rh * 0.84)
        rects.append(rect)
        selected = i == sel
        pygame.draw.rect(scr, (52, 58, 82) if selected else (30, 33, 46), rect, border_radius=int(rh * 0.2))
        if selected and hold.progress > 0:
            fill = rect.copy()
            fill.width = int(rect.width * hold.progress)
            pygame.draw.rect(scr, (40, 120, 80), fill, border_radius=int(rh * 0.2))
        if selected:
            pygame.draw.rect(scr, tl.C_GOLD, rect, max(2, int(H * 0.004)), border_radius=int(rh * 0.2))

        if gm["tag"]:
            badge = pygame.Rect(0, 0, rh * 0.9, rh * 0.45)
            badge.center = (rect.x + rh * 0.65, rect.centery)
            pygame.draw.rect(scr, TAG_COL[gm["tag"]], badge, border_radius=int(rh * 0.12))
            img = view.font(0.034).render(gm["tag"], True, (20, 20, 30))
            if img.get_width() > badge.width * 0.92:        # long tags (CO-OP) get squeezed to fit
                img = pygame.transform.smoothscale(img, (int(badge.width * 0.92), img.get_height()))
            scr.blit(img, img.get_rect(center=badge.center))

        name_img = view.font(0.05).render(gm["name"], True, tl.C_TEXT if selected else (200, 205, 220))
        scr.blit(name_img, (rect.x + rh * 1.3, rect.centery - name_img.get_height() * 0.95))
        desc_img = view.font(0.03).render(gm["desc"], True, tl.C_DIM)
        scr.blit(desc_img, (rect.x + rh * 1.3, rect.centery + desc_img.get_height() * 0.25))

        if gm.get("best"):
            key, fmt = gm["best"]
            b = tl.best(key)
            txt = f"best {fmt.format(b)}" if b is not None else "no best yet"
            img = view.font(0.032).render(txt, True, tl.C_GOLD if b is not None else tl.C_DIM)
            scr.blit(img, img.get_rect(midright=(rect.right - rh * 0.4, rect.centery)))

    # scroll bar + arrows
    if len(GAMES) > VISIBLE:
        bx = x0 + cw + W * 0.015
        bh = bottom - top
        pygame.draw.rect(scr, (30, 33, 46), (bx, top, W * 0.008, bh), border_radius=4)
        pygame.draw.rect(scr, tl.C_DIM, (bx, top + bh * first / len(GAMES), W * 0.008, bh * VISIBLE / len(GAMES)),
                         border_radius=4)
        if first > 0:
            view.text("more above", tl.C_DIM, (W / 2, top - H * 0.012), 0.025)
        if first + VISIBLE < len(GAMES):
            view.text("more below", tl.C_DIM, (W / 2, bottom + H * 0.012), 0.025)

    hint = ("tilt forward/back to choose  -  hold tilt RIGHT to play"
            if ctrl.connected(1) or ctrl.connected(2)
            else "arrow keys to choose  -  Enter to play  -  Esc to quit")
    view.text(hint, tl.C_DIM, (W / 2, H * 0.94), 0.032)
    return rects


def menu(ctrl, sel):
    tl.phone_recalibrate()  # Android: the way the phone is held in the menu counts as level
    view = tl.View()
    clock = pygame.time.Clock()
    hold = tl.Hold(1.0)
    cool = 0.0
    lock = 0.8          # ignore tilt right after returning from a game
    t = 0.0
    rects = []
    n = len(GAMES)
    first = 0
    while True:
        dt = min(clock.tick(60) / 1000.0, 1 / 30)
        t += dt
        for k in tl.events():
            if isinstance(k, tuple):
                for i, r in enumerate(rects):
                    if r.collidepoint(k[1]):
                        if i == sel:
                            return sel
                        sel = i
            elif k == pygame.K_ESCAPE:
                return None
            elif k in (pygame.K_UP, pygame.K_w):
                sel = (sel - 1) % n
            elif k in (pygame.K_DOWN, pygame.K_s):
                sel = (sel + 1) % n
            elif k in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER):
                return sel

        tx, ty = tl.controller_tilt(ctrl)
        lock -= dt
        cool -= dt
        if lock <= 0:
            if abs(ty) > 0.35 and cool <= 0:
                sel = (sel + (1 if ty > 0 else -1)) % n
                cool = 0.4
                hold.t = 0.0
            elif abs(ty) < 0.2:
                cool = min(cool, 0.0)
            if hold.update(tx > 0.4 and abs(ty) < 0.35, dt):
                return sel
        first = min(max(first, sel - VISIBLE + 1), sel, n - VISIBLE)
        first = max(0, first)
        rects = draw_menu(view, sel, hold, ctrl, t, first)
        pygame.display.flip()


def main():
    tl.init_display("--window" not in sys.argv)
    ctrl = tl.controllers()
    sel = 0
    while True:
        sel = menu(ctrl, sel)
        if sel is None or GAMES[sel]["run"] is None:
            break
        GAMES[sel]["run"](ctrl)
    pygame.quit()


if __name__ == "__main__":
    main()
