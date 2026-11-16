#!/usr/bin/env python3
"""
Settings page for the tilt controllers: which board is player 1, the colours,
how each remote is held, and up/down or left/right inverting.
Saved in settings.json, so it's remembered next time.

Controller: tilt forward/back to choose a row, hold RIGHT to change it,
            hold LEFT to go back.
Keyboard:   up/down to choose, Enter or left/right to change, Esc to go back.

Run on its own:  python3 settings_page.py [--fullscreen]
"""

import pygame

import tiltlib as tl


def rows(st):
    """[(label, value text, kind, key)] for the current settings."""
    p1, p2 = st["p1_board"], 3 - st["p1_board"]
    c1 = st["p1_colour"]
    c2 = "red" if c1 == "blue" else "blue"
    out = [
        ("Player 1 controller", f"{tl.BOARD_NAME[p1]}   (player 2 = {tl.BOARD_NAME[p2]})", "p1_board", None),
        ("Player 1 colour", f"{c1.upper()}   (player 2 = {c2.upper()})", "p1_colour", None),
    ]
    for d in (1, 2):
        b = st["boards"][str(d)]
        n = tl.BOARD_NAME[d]
        out += [
            (f"{n}: hold it", b["hold"], "hold", d),
            (f"{n}: up / down", "inverted" if b["invert_y"] else "normal", "invert_y", d),
            (f"{n}: left / right", "inverted" if b["invert_x"] else "normal", "invert_x", d),
        ]
    out += [("Reset to defaults", "", "reset", None), ("Back", "", "back", None)]
    return out


def change(st, kind, d, step=1):
    if kind == "p1_board":
        st["p1_board"] = 3 - st["p1_board"]
    elif kind == "p1_colour":
        st["p1_colour"] = "red" if st["p1_colour"] == "blue" else "blue"
    elif kind == "hold":
        b = st["boards"][str(d)]
        b["hold"] = tl.HOLDS[(tl.HOLDS.index(b["hold"]) + step) % len(tl.HOLDS)]
    elif kind in ("invert_y", "invert_x"):
        b = st["boards"][str(d)]
        b[kind] = not b[kind]
    elif kind == "reset":
        st.clear()
        st.update(tl._defaults())
    tl.save_settings(st)


def draw_tester(view, ctrl, cx, cy, size, d, t):
    """A box with a dot that follows board d's tilt (with the settings applied)."""
    scr = view.screen
    p = 1 if tl.DEV[1] == d else 2
    col = tl.PLAYER_COL[p]
    r = pygame.Rect(0, 0, size, size)
    r.center = (cx, cy)
    pygame.draw.rect(scr, (30, 33, 46), r, border_radius=int(size * 0.08))
    pygame.draw.rect(scr, col, r, max(2, int(size * 0.015)), border_radius=int(size * 0.08))
    pygame.draw.line(scr, (55, 60, 80), (r.centerx, r.top + 6), (r.centerx, r.bottom - 6))
    pygame.draw.line(scr, (55, 60, 80), (r.left + 6, r.centery), (r.right - 6, r.centery))
    view.text("forward", tl.C_DIM, (cx, r.top + size * 0.08), 0.022)
    view.text("back", tl.C_DIM, (cx, r.bottom - size * 0.08), 0.022)
    view.text(f"P{p} {tl.PLAYER_NAME[p]}", col, (cx, r.top - view.H * 0.055), 0.04)
    view.text(tl.BOARD_NAME[d], tl.C_TEXT, (cx, r.top - view.H * 0.02), 0.03)
    if ctrl.board_connected(d):
        x, y = tl.board_tilt(ctrl, d)
        x, y = max(-1.0, min(1.0, x)), max(-1.0, min(1.0, y))
        pos = (cx + x * size * 0.42, cy + y * size * 0.42)
        pygame.draw.circle(scr, col, pos, size * 0.07)
        pygame.draw.circle(scr, (255, 255, 255), pos, size * 0.07, 2)
        view.text("tilt it: the dot should go the same way", tl.C_DIM, (cx, r.bottom + view.H * 0.025), 0.024)
    else:
        view.text("not connected", tl.C_DIM, (cx, cy), 0.035)


def run(ctrl):
    view = tl.View()
    clock = pygame.time.Clock()
    st = tl.load_settings()
    tl.apply_settings(st)
    go, back = tl.Hold(0.7), tl.Hold(0.9)
    sel, cool, lock, t = 0, 0.0, 0.8, 0.0
    released = True
    rects = []
    while True:
        dt = min(clock.tick(60) / 1000.0, 1 / 30)
        t += dt
        rs = rows(st)
        n = len(rs)
        for k in tl.events():
            if isinstance(k, tuple):
                for i, rc in enumerate(rects):
                    if rc.collidepoint(k[1]):
                        if i == sel:
                            if rs[i][2] == "back":
                                return
                            change(st, rs[i][2], rs[i][3])
                        sel = i
            elif k == pygame.K_ESCAPE:
                return
            elif k in (pygame.K_UP, pygame.K_w):
                sel = (sel - 1) % n
            elif k in (pygame.K_DOWN, pygame.K_s):
                sel = (sel + 1) % n
            elif k in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_KP_ENTER, pygame.K_RIGHT, pygame.K_d,
                       pygame.K_LEFT, pygame.K_a):
                if rs[sel][2] == "back":
                    return
                change(st, rs[sel][2], rs[sel][3], -1 if k in (pygame.K_LEFT, pygame.K_a) else 1)

        tx, ty = tl.controller_tilt(ctrl)
        lock -= dt
        cool -= dt
        if lock <= 0:
            if abs(ty) > 0.35 and cool <= 0:
                sel = (sel + (1 if ty > 0 else -1)) % n
                cool, go.t = 0.4, 0.0
            elif abs(ty) < 0.2:
                cool = min(cool, 0.0)
            if abs(tx) < 0.2:
                released = True
            # one change per hold: tilt back to level before the next one
            if go.update(released and tx > 0.4 and abs(ty) < 0.35, dt):
                released = False
                if rs[sel][2] == "back":
                    return
                change(st, rs[sel][2], rs[sel][3])
            if back.update(tx < -0.4 and abs(ty) < 0.35, dt):
                return

        # ------------------------------------------------ draw
        view.update()
        scr, W, H = view.screen, view.W, view.H
        scr.fill(tl.C_BG)
        view.text("SETTINGS", tl.C_TEXT, (W * 0.33, H * 0.07), 0.08)
        rs = rows(st)
        top, bottom = H * 0.14, H * 0.86
        rh = min((bottom - top) / n, H * 0.075)
        cw = W * 0.56
        x0 = W * 0.04
        rects = []
        for i, (label, value, kind, d) in enumerate(rs):
            rect = pygame.Rect(x0, top + i * rh + rh * 0.07, cw, rh * 0.86)
            rects.append(rect)
            on = i == sel
            br = int(rh * 0.2)
            pygame.draw.rect(scr, (52, 58, 82) if on else (30, 33, 46), rect, border_radius=br)
            if on and go.progress > 0:
                f = rect.copy()
                f.width = int(rect.width * go.progress)
                pygame.draw.rect(scr, (40, 120, 80), f, border_radius=br)
            if on:
                pygame.draw.rect(scr, tl.C_GOLD, rect, max(2, int(H * 0.004)), border_radius=br)
            img = view.font(0.036).render(label, True, tl.C_TEXT if on else (200, 205, 220))
            scr.blit(img, img.get_rect(midleft=(rect.x + rh * 0.35, rect.centery)))
            if value:
                vc = tl.C_GOLD
                if kind == "p1_colour":
                    vc = tl.PLAYER_COL[1]
                img = view.font(0.032).render(value, True, vc)
                scr.blit(img, img.get_rect(midright=(rect.right - rh * 0.35, rect.centery)))

        size = min(W * 0.2, H * 0.3)
        tx0 = W * 0.81
        draw_tester(view, ctrl, tx0, H * 0.26, size, 1, t)
        draw_tester(view, ctrl, tx0, H * 0.71, size, 2, t)

        if back.progress > 0:
            view.hold_bar(back.progress, (W * 0.32, H * 0.93), "< going back", tl.C_DIM)
        else:
            view.text("tilt forward/back to choose  -  hold RIGHT to change  -  hold LEFT to go back",
                      tl.C_DIM, (W * 0.32, H * 0.93), 0.026)
        pygame.display.flip()


if __name__ == "__main__":
    tl.run_standalone(run)
