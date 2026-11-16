"""
Shared code for the Tilt Arcade games:
Bluetooth controllers, tilt input, marble physics, drawing helpers, high scores.
"""

import asyncio
import json
import math
import os
import struct
import sys
import threading
import time

import pygame

try:
    from bleak import BleakClient, BleakScanner
    HAVE_BLEAK = True
except ImportError:
    HAVE_BLEAK = False

HERE = os.path.dirname(os.path.abspath(__file__))
SCORES_FILE = os.path.join(HERE, "scores.json")

# ---------------------------------------------------------------- settings
SERVICE_UUID = "6e400001-7a3b-4c1d-9e8f-0123456789ab"
TILT_UUID = "6e400002-7a3b-4c1d-9e8f-0123456789ab"

# Controller setup (which board is which player, colours, how it's held) is
# chosen on the Settings page in the arcade and saved in settings.json.
SETTINGS_FILE = os.path.join(HERE, "settings.json")
BOARD_NAME = {1: "ESP32-S3", 2: "ESP32 38-pin"}       # board 1 = Marble-P1 firmware, 2 = Marble-P2
HOLDS = ["normal", "sideways left", "sideways right", "upside down"]
DEFAULT_SETTINGS = {
    "p1_board": 1,              # which board plays as player 1 (the other one is player 2)
    "p1_colour": "blue",        # player 1's colour (player 2 gets the other one)
    "boards": {"1": {"hold": "normal", "invert_y": False, "invert_x": False},
               "2": {"hold": "normal", "invert_y": False, "invert_x": False}},
}
SENSITIVITY = 1.0     # >1 = react more to small tilts
DEADZONE = 0.03

FIELD_W, FIELD_H = 320, 240   # every game uses this logical size, scaled to the screen

# ---------------------------------------------------------------- colours
C_BG = (18, 20, 30)
C_FIELD = (34, 38, 54)
C_WALL = (150, 160, 190)
C_WALL_EDGE = (200, 210, 235)
C_HOLE = (6, 6, 10)
C_HOLE_RIM = (70, 72, 90)
C_GOAL = (40, 200, 100)
C_GOLD = (250, 200, 60)
C_TEXT = (235, 238, 245)
C_DIM = (140, 145, 165)
COLOURS = {"blue": ((70, 140, 250), "BLUE"), "red": ((235, 70, 70), "RED")}
PLAYER_COL = {1: COLOURS["blue"][0], 2: COLOURS["red"][0]}
PLAYER_NAME = {1: "BLUE", 2: "RED"}
DEV = {1: 1, 2: 2}          # player -> board


def _defaults():
    return json.loads(json.dumps(DEFAULT_SETTINGS))


def load_settings():
    st = _defaults()
    try:
        with open(SETTINGS_FILE) as f:
            saved = json.load(f)
        if saved.get("p1_board") in (1, 2):
            st["p1_board"] = saved["p1_board"]
        if saved.get("p1_colour") in COLOURS:
            st["p1_colour"] = saved["p1_colour"]
        for d in ("1", "2"):
            b = saved.get("boards", {}).get(d, {})
            if b.get("hold") in HOLDS:
                st["boards"][d]["hold"] = b["hold"]
            for k in ("invert_y", "invert_x"):
                if isinstance(b.get(k), bool):
                    st["boards"][d][k] = b[k]
    except (OSError, ValueError, AttributeError):
        pass
    return st


def apply_settings(st):
    """Make st the live settings (games read PLAYER_COL / PLAYER_NAME / DEV)."""
    SETTINGS.clear()
    SETTINGS.update(st)
    DEV[1] = st["p1_board"]
    DEV[2] = 3 - st["p1_board"]
    c1 = st["p1_colour"]
    c2 = "red" if c1 == "blue" else "blue"
    for p, c in ((1, c1), (2, c2)):
        PLAYER_COL[p], PLAYER_NAME[p] = COLOURS[c]


def save_settings(st):
    apply_settings(st)
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(st, f, indent=2)
    except OSError as e:
        print(f"could not save settings: {e}", file=sys.stderr)


SETTINGS = {}
apply_settings(load_settings())


# ================================================================ Bluetooth
class Controllers:
    """Thread-safe store of the latest tilt from each controller."""

    def __init__(self):
        self.lock = threading.Lock()
        self.tilt = {1: (0.0, 0.0), 2: (0.0, 0.0)}
        self.last = {1: 0.0, 2: 0.0}
        s = "searching" if HAVE_BLEAK else "no bleak"
        self.status = {1: s, 2: s}

    def update(self, p, x, y):
        with self.lock:
            self.tilt[p] = (x, y)
            self.last[p] = time.monotonic()

    def set_status(self, p, s):
        with self.lock:
            self.status[p] = s

    # update / set_status are per board (1 = Marble-P1, 2 = Marble-P2).
    # connected / get / label take a PLAYER and look up that player's board.
    def board_connected(self, d):
        with self.lock:
            return time.monotonic() - self.last[d] < 0.5

    def board_get(self, d):
        with self.lock:
            return self.tilt[d]

    def connected(self, p):
        return self.board_connected(DEV[p])

    def get(self, p):
        return self.board_get(DEV[p])

    def label(self, p):
        d = DEV[p]
        return "controller" if self.connected(p) else f"keyboard ({self.status[d]})"


async def _run_player(ctrl, p, device, radio_lock):
    def on_notify(_char, data):
        if len(data) >= 4:
            x, y = struct.unpack("<hh", bytes(data[:4]))
            ctrl.update(p, x / 1000.0, y / 1000.0)

    try:
        ctrl.set_status(p, "connecting")
        client = BleakClient(device, timeout=15.0)
        async with radio_lock:          # BlueZ dislikes scanning + connecting at once
            await client.connect()
        try:
            await client.start_notify(TILT_UUID, on_notify)
            ctrl.set_status(p, "connected")
            print(f"[P{p}] controller connected", flush=True)
            while client.is_connected:
                await asyncio.sleep(0.5)
        finally:
            try:
                await client.disconnect()
            except Exception:
                pass
    except Exception as e:
        print(f"[P{p}] connection problem: {e}", file=sys.stderr)
    ctrl.set_status(p, "searching")


async def _bluetoothctl(*args):
    if not sys.platform.startswith("linux"):    # BlueZ tool, Linux only (not needed on Windows/macOS)
        return ""
    try:
        proc = await asyncio.create_subprocess_exec(
            "bluetoothctl", *args,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=8)
        return out.decode(errors="replace")
    except Exception:
        return ""


async def _drop_stale_links(players):
    """A controller still linked to the Pi from an earlier run (game closed without
    disconnecting) stops advertising, so it can't be found. Disconnect it so it
    advertises again."""
    out = await _bluetoothctl("devices", "Connected")
    for line in out.splitlines():
        parts = line.split(maxsplit=2)       # "Device AA:BB:.. Marble-P1"
        if len(parts) == 3 and parts[0] == "Device":
            for p in players:
                if parts[2].strip() == f"Marble-P{p}":
                    print(f"[P{p}] dropping leftover Bluetooth link, reconnecting...")
                    await _bluetoothctl("disconnect", parts[1])
                    await asyncio.sleep(1.0)


async def _ble_main(ctrl):
    radio_lock = asyncio.Lock()
    tasks = {}
    while True:
        missing = [p for p in (1, 2) if p not in tasks or tasks[p].done()]
        if missing:
            await _drop_stale_links(missing)
            try:
                async with radio_lock:
                    found = await BleakScanner.discover(timeout=3.0, return_adv=True)
            except Exception as e:
                print(f"[BLE] scan failed: {e}", file=sys.stderr)
                for p in missing:
                    ctrl.set_status(p, "BT error")
                await asyncio.sleep(3)
                continue
            for _addr, (dev, adv) in found.items():
                name = adv.local_name or dev.name or ""
                for p in missing:
                    if name == f"Marble-P{p}" and (p not in tasks or tasks[p].done()):
                        tasks[p] = asyncio.create_task(_run_player(ctrl, p, dev, radio_lock))
        await asyncio.sleep(1.0)


_ctrl = None


def controllers():
    """The shared Controllers object; starts Bluetooth the first time."""
    global _ctrl
    if _ctrl is None:
        _ctrl = Controllers()
        if HAVE_BLEAK:
            threading.Thread(target=lambda: asyncio.run(_ble_main(_ctrl)), daemon=True).start()
        else:
            print("bleak not installed - keyboard only")
    return _ctrl


# ================================================================ display + events
_fullscreen = False


def init_display(fullscreen):
    global _fullscreen
    pygame.init()
    _fullscreen = fullscreen
    _apply_mode()
    pygame.display.set_caption("Tilt Arcade")


def _apply_mode():
    if _fullscreen:
        pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    else:
        pygame.display.set_mode((1280, 800), pygame.RESIZABLE)
    pygame.mouse.set_visible(not _fullscreen)


def events():
    """Handle quit / F11 / resize. Returns this frame's key presses (and ('click', pos))."""
    global _fullscreen
    out = []
    for ev in pygame.event.get():
        if ev.type == pygame.QUIT:
            pygame.quit()
            sys.exit(0)
        elif ev.type == pygame.VIDEORESIZE and not _fullscreen:
            pygame.display.set_mode(ev.size, pygame.RESIZABLE)
        elif ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_F11:
                _fullscreen = not _fullscreen
                _apply_mode()
            else:
                out.append(ev.key)
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            out.append(("click", ev.pos))
    return out


# ================================================================ tilt input
KEYS = {
    1: (pygame.K_a, pygame.K_d, pygame.K_w, pygame.K_s),
    2: (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN),
}


def _kb(p):
    pressed = pygame.key.get_pressed()
    left, right, up, down = KEYS[p]
    return ((pressed[right] - pressed[left]) * 0.6, (pressed[down] - pressed[up]) * 0.6)


def board_tilt(ctrl, d):
    """Tilt from board d with its hold direction / invert settings applied."""
    x, y = ctrl.board_get(d)
    a = SETTINGS["boards"][str(d)]
    hold = a["hold"]
    if hold == "sideways left":
        x, y = -y, x
    elif hold == "sideways right":
        x, y = y, -x
    elif hold == "upside down":
        x, y = -x, -y
    if a["invert_x"]:
        x = -x
    if a["invert_y"]:
        y = -y
    return x, y


def _ctrl_tilt(ctrl, p):
    x, y = board_tilt(ctrl, DEV[p])
    x *= SENSITIVITY
    y *= SENSITIVITY
    return (0.0 if abs(x) < DEADZONE else x, 0.0 if abs(y) < DEADZONE else y)


def player_tilt(ctrl, p):
    """Tilt for player p: its controller, or its keys (WASD / arrows) if pressed or not connected."""
    kx, ky = _kb(p)
    if kx or ky or not ctrl.connected(p):
        return (kx, ky)
    return _ctrl_tilt(ctrl, p)


def solo_tilt(ctrl):
    """Tilt for single-player games: any keys, else controller 1, else controller 2."""
    for p in (1, 2):
        k = _kb(p)
        if k[0] or k[1]:
            return k
    for p in (1, 2):
        if ctrl.connected(p):
            return _ctrl_tilt(ctrl, p)
    return (0.0, 0.0)


def controller_tilt(ctrl):
    """Strongest tilt from connected controllers only (no keyboard)."""
    cands = [_ctrl_tilt(ctrl, p) for p in (1, 2) if ctrl.connected(p)] or [(0.0, 0.0)]
    return max(cands, key=lambda t: abs(t[0]) + abs(t[1]))


def menu_tilt(ctrl):
    """Strongest tilt from any controller or key set (for menus)."""
    cands = [_kb(1), _kb(2)] + [_ctrl_tilt(ctrl, p) for p in (1, 2) if ctrl.connected(p)]
    return max(cands, key=lambda t: abs(t[0]) + abs(t[1]))


# ================================================================ physics
class Ball:
    def __init__(self, x, y, r=6.0, color=(255, 255, 255), p=1):
        self.home = (x, y)
        self.r = r
        self.color = color
        self.p = p
        self.respawn()

    def respawn(self):
        self.x, self.y = self.home
        self.vx = self.vy = 0.0
        self.falling = 0.0      # >0 while dropping into a hole / off an edge
        self.trail = []


def integrate(b, tilt, h, accel=420.0, friction=1.2, max_speed=260.0):
    b.vx += tilt[0] * accel * h
    b.vy += tilt[1] * accel * h
    f = max(0.0, 1.0 - friction * h)
    b.vx *= f
    b.vy *= f
    sp = math.hypot(b.vx, b.vy)
    if sp > max_speed:
        b.vx *= max_speed / sp
        b.vy *= max_speed / sp
    b.x += b.vx * h
    b.y += b.vy * h


def collide_rect(b, rect, bounce=0.45):
    x, y, w, h = rect
    cx = min(max(b.x, x), x + w)
    cy = min(max(b.y, y), y + h)
    dx, dy = b.x - cx, b.y - cy
    d2 = dx * dx + dy * dy
    if d2 >= b.r * b.r:
        return
    if d2 > 1e-9:
        d = math.sqrt(d2)
        nx, ny, pen = dx / d, dy / d, b.r - d
    else:  # centre ended up inside the wall: push out the shortest way
        options = [(b.x - x, -1, 0), (x + w - b.x, 1, 0), (b.y - y, 0, -1), (y + h - b.y, 0, 1)]
        dist, nx, ny = min(options)
        pen = dist + b.r
    b.x += nx * pen
    b.y += ny * pen
    vn = b.vx * nx + b.vy * ny
    if vn < 0:
        b.vx -= (1 + bounce) * vn * nx
        b.vy -= (1 + bounce) * vn * ny


def collide_balls(a, b, restitution=0.8):
    if a.falling > 0 or b.falling > 0:
        return 0.0
    dx, dy = b.x - a.x, b.y - a.y
    rr = a.r + b.r
    d2 = dx * dx + dy * dy
    if d2 >= rr * rr or d2 < 1e-9:
        return 0.0
    d = math.sqrt(d2)
    nx, ny = dx / d, dy / d
    overlap = rr - d
    a.x -= nx * overlap / 2
    a.y -= ny * overlap / 2
    b.x += nx * overlap / 2
    b.y += ny * overlap / 2
    rel = (b.vx - a.vx) * nx + (b.vy - a.vy) * ny
    if rel < 0:  # moving toward each other: equal-mass bounce
        imp = -(1 + restitution) * rel / 2
        a.vx -= imp * nx
        a.vy -= imp * ny
        b.vx += imp * nx
        b.vy += imp * ny
        return -rel
    return 0.0


# ================================================================ drawing
class View:
    """Maps the 320x240 logical field onto the window, below a HUD strip."""

    def __init__(self, hud_frac=0.09):
        self.hud_frac = hud_frac
        self._fonts = {}
        self.update()

    def update(self):
        self.screen = pygame.display.get_surface()
        W, H = self.screen.get_size()
        self.W, self.H = W, H
        self.hud = int(H * self.hud_frac)
        self.s = min(W / FIELD_W, (H - self.hud) / FIELD_H)
        self.ox = (W - FIELD_W * self.s) / 2
        self.oy = self.hud + (H - self.hud - FIELD_H * self.s) / 2

    def font(self, frac):
        size = max(14, int(self.H * frac))
        if size not in self._fonts:
            self._fonts[size] = pygame.font.SysFont(None, size)
        return self._fonts[size]

    def P(self, x, y):
        return (self.ox + x * self.s, self.oy + y * self.s)

    def L(self, v):
        return v * self.s

    def text(self, msg, color, center, size=0.05):
        img = self.font(size).render(msg, True, color)
        self.screen.blit(img, img.get_rect(center=center))

    def field(self, color=C_FIELD):
        pygame.draw.rect(self.screen, color, (*self.P(0, 0), FIELD_W * self.s, FIELD_H * self.s))

    def wall(self, r):
        x, y, w, h = r
        rect = pygame.Rect(*self.P(x, y), math.ceil(w * self.s), math.ceil(h * self.s))
        pygame.draw.rect(self.screen, C_WALL, rect, border_radius=int(self.s))
        pygame.draw.line(self.screen, C_WALL_EDGE, rect.topleft, rect.topright, max(1, int(self.s / 2)))

    def hole(self, x, y, r, rim=C_HOLE_RIM):
        pygame.draw.circle(self.screen, rim, self.P(x, y), (r + 1.5) * self.s)
        pygame.draw.circle(self.screen, C_HOLE, self.P(x, y), r * self.s)

    def ball(self, b, scale=1.0):
        r = b.r * scale
        if r <= 0.3:
            return
        c = b.color
        for i, (tx, ty) in enumerate(b.trail):
            k = (i + 1) / (len(b.trail) + 1)
            tc = tuple(int(C_FIELD[j] + (c[j] - C_FIELD[j]) * 0.35 * k) for j in range(3))
            pygame.draw.circle(self.screen, tc, self.P(tx, ty), b.r * self.s * (0.4 + 0.5 * k))
        pygame.draw.circle(self.screen, (10, 10, 15), self.P(b.x + r * 0.2, b.y + r * 0.25), r * self.s)
        pygame.draw.circle(self.screen, c, self.P(b.x, b.y), r * self.s)
        hl = tuple(min(255, v + 90) for v in c)
        pygame.draw.circle(self.screen, hl, self.P(b.x - r * 0.35, b.y - r * 0.35), r * 0.35 * self.s)

    def panel(self, frac, alpha=170):
        h = self.H * frac
        surf = pygame.Surface((self.W, h), pygame.SRCALPHA)
        surf.fill((0, 0, 0, alpha))
        self.screen.blit(surf, (0, (self.H - h) / 2))

    def hold_bar(self, progress, center, label, color):
        w, h = self.W * 0.3, self.H * 0.05
        x, y = center[0] - w / 2, center[1] - h / 2
        pygame.draw.rect(self.screen, (50, 54, 70), (x, y, w, h), border_radius=int(h / 2))
        if progress > 0:
            pygame.draw.rect(self.screen, color, (x, y, w * progress, h), border_radius=int(h / 2))
        self.text(label, C_TEXT, center, 0.032)


# ================================================================ helpers
class Hold:
    """Hold-to-confirm: returns True once the condition has been held for `secs`."""

    def __init__(self, secs=0.9):
        self.secs = secs
        self.t = 0.0

    def update(self, active, dt):
        self.t = self.t + dt if active else max(0.0, self.t - 2 * dt)
        if self.t >= self.secs:
            self.t = 0.0
            return True
        return False

    @property
    def progress(self):
        return min(1.0, self.t / self.secs)


class EndChoice:
    """Game-over picker: tilt RIGHT (or SPACE) = play again, tilt LEFT (or ESC) = menu."""

    def __init__(self):
        self.again = Hold()
        self.menu = Hold()
        self.lock = 1.0     # ignore tilt briefly so a mid-game tilt doesn't pick

    def update(self, ctrl, dt, keys):
        for k in keys:
            if k in (pygame.K_SPACE, pygame.K_RETURN):
                return "again"
            if k == pygame.K_ESCAPE:
                return "menu"
        self.lock -= dt
        if self.lock > 0:
            return None
        tx, _ = menu_tilt(ctrl)
        if self.again.update(tx > 0.4, dt):
            return "again"
        if self.menu.update(tx < -0.4, dt):
            return "menu"
        return None

    def draw(self, view, y_frac=0.8):
        view.hold_bar(self.menu.progress, (view.W * 0.3, view.H * y_frac), "< tilt LEFT: menu", C_DIM)
        view.hold_bar(self.again.progress, (view.W * 0.7, view.H * y_frac), "tilt RIGHT: again >", C_GOAL)


def pick(ctrl, title, options, sel=0):
    """Full-screen chooser (maps, modes). options = [(name, description)].
    Tilt forward/back to choose, hold RIGHT to play, hold LEFT to go back.
    Returns the chosen index, or None for back."""
    view = View()
    clock = pygame.time.Clock()
    go, back = Hold(0.9), Hold(0.9)
    cool, lock, t = 0.0, 0.7, 0.0
    n = len(options)
    rects = []
    while True:
        dt = min(clock.tick(60) / 1000.0, 1 / 30)
        t += dt
        for k in events():
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
        tx, ty = controller_tilt(ctrl)
        lock -= dt
        cool -= dt
        if lock <= 0:
            if abs(ty) > 0.35 and cool <= 0:
                sel = (sel + (1 if ty > 0 else -1)) % n
                cool, go.t = 0.4, 0.0
            elif abs(ty) < 0.2:
                cool = min(cool, 0.0)
            if go.update(tx > 0.4 and abs(ty) < 0.35, dt):
                return sel
            if back.update(tx < -0.4 and abs(ty) < 0.35, dt):
                return None

        view.update()
        scr, W, H = view.screen, view.W, view.H
        scr.fill(C_BG)
        view.text(title, C_TEXT, (W / 2, H * 0.1), 0.08)
        top, bottom = H * 0.2, H * 0.84
        rh = min((bottom - top) / n, H * 0.13)
        top = (top + bottom) / 2 - rh * n / 2
        cw = min(W * 0.7, H * 1.1)
        x0 = (W - cw) / 2
        rects = []
        for i, (name, desc) in enumerate(options):
            rect = pygame.Rect(x0, top + i * rh + rh * 0.08, cw, rh * 0.84)
            rects.append(rect)
            on = i == sel
            br = int(rh * 0.2)
            pygame.draw.rect(scr, (52, 58, 82) if on else (30, 33, 46), rect, border_radius=br)
            if on and go.progress > 0:
                f = rect.copy()
                f.width = int(rect.width * go.progress)
                pygame.draw.rect(scr, (40, 120, 80), f, border_radius=br)
            if on:
                pygame.draw.rect(scr, C_GOLD, rect, max(2, int(H * 0.004)), border_radius=br)
            img = view.font(0.05).render(name, True, C_TEXT if on else (200, 205, 220))
            scr.blit(img, (rect.x + rh * 0.4, rect.centery - img.get_height() * 0.95))
            img = view.font(0.03).render(desc, True, C_DIM)
            scr.blit(img, (rect.x + rh * 0.4, rect.centery + img.get_height() * 0.25))
        if back.progress > 0:
            view.hold_bar(back.progress, (W / 2, H * 0.9), "< going back", C_DIM)
        else:
            view.text("tilt forward/back to choose  -  hold RIGHT to play  -  hold LEFT to go back",
                      C_DIM, (W / 2, H * 0.92), 0.03)
        pygame.display.flip()


def game_loop(ctrl, make, draw, solo=False):
    """Standard loop for a game object with .step(dt, tilts) and .over.
    draw(view, game, ctrl, end_choice_or_None). ESC quits mid-game."""
    view = View()
    clock = pygame.time.Clock()
    g, end = make(), None
    while True:
        dt = min(clock.tick(60) / 1000.0, 1 / 30)
        keys = events()
        if pygame.K_ESCAPE in keys and not g.over:
            return
        tilts = {1: solo_tilt(ctrl)} if solo else {p: player_tilt(ctrl, p) for p in (1, 2)}
        g.step(dt, tilts)
        if g.over:
            end = end or EndChoice()
            choice = end.update(ctrl, dt, keys)
            if choice == "again":
                g, end = make(), None
            elif choice == "menu":
                return
        draw(view, g, ctrl, end)
        pygame.display.flip()


def hud_scores(view, ctrl, score, middle=None):
    hy = view.hud * 0.42
    for p, side in ((1, 0.2), (2, 0.8)):
        view.text(f"{PLAYER_NAME[p]}  {score[p]}", PLAYER_COL[p], (view.W * side, hy), 0.06)
        view.text(ctrl.label(p), C_TEXT if ctrl.connected(p) else C_DIM,
                  (view.W * side, view.hud * 0.85), 0.032)
    if middle:
        view.text(middle, C_DIM, (view.W / 2, view.hud * 0.5), 0.035)


def draw_countdown(view, timer, sub=None, go="GO!"):
    n = math.ceil(timer)
    view.text(str(n) if n > 0 else go, C_TEXT, (view.W / 2, view.H * 0.45), 0.2)
    if sub:
        view.text(sub, C_DIM, (view.W / 2, view.H * 0.62), 0.045)


def draw_match(view, winner, line2=None):
    view.panel(0.6)
    if winner:
        view.text(f"{PLAYER_NAME[winner]} WINS!", PLAYER_COL[winner], (view.W / 2, view.H * 0.37), 0.17)
    else:
        view.text("DRAW!", C_TEXT, (view.W / 2, view.H * 0.37), 0.17)
    if line2:
        view.text(line2, C_TEXT, (view.W / 2, view.H * 0.54), 0.07)


def draw_solo_result(view, big, record, unit_fmt="{}", color=C_GOLD):
    """Game-over panel for 1-player games. record = (is_new, best) from submit()."""
    view.panel(0.6)
    view.text(big, color, (view.W / 2, view.H * 0.36), 0.14)
    is_new, rec = record
    view.text("NEW HIGH SCORE!" if is_new else f"best: {unit_fmt.format(rec)}",
              C_GOLD if is_new else C_DIM, (view.W / 2, view.H * 0.53), 0.06)


def hud_solo(view, left, middle, best_key, fmt="{}"):
    """HUD for 1-player games: score on the left, info in the middle, best on the right."""
    hy = view.hud * 0.42
    bt = best(best_key)
    view.text(left, C_GOLD, (view.W * 0.2, hy), 0.055)
    if middle:
        view.text(middle, C_TEXT, (view.W * 0.5, hy), 0.045)
    view.text(f"best {fmt.format(bt)}" if bt is not None else "no best yet", C_DIM, (view.W * 0.8, hy), 0.045)


def load_scores():
    try:
        with open(SCORES_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def best(key):
    return load_scores().get(key)


def submit(key, value, higher_better=True):
    """Save value if it beats the record. Returns (is_new_record, record)."""
    s = load_scores()
    old = s.get(key)
    if old is None or (value > old if higher_better else value < old):
        s[key] = value
        try:
            with open(SCORES_FILE, "w") as f:
                json.dump(s, f, indent=1)
        except Exception as e:
            print(f"could not save scores: {e}", file=sys.stderr)
        return True, value
    return False, old


def run_standalone(run_fn, **kw):
    """Let a game file run on its own: python3 game.py [--fullscreen]."""
    init_display("--fullscreen" in sys.argv)
    try:
        run_fn(controllers(), **kw)
    finally:
        pygame.quit()
