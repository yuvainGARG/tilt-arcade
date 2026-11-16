#!/usr/bin/env python3
"""
Builds the 3D-printable controller cases (base + screw-on lid) as STL files.

    python3 case/make_cases.py

Every size is in millimetres. If your board doesn't fit, measure it and change
the numbers in BOARDS below, then run this again.

Hardware per case: 4 x M3 x 12 mm countersunk (flat-head) screws.
They self-tap into the 2.5 mm holes in the corner posts (PLA / PETG).
If you have M3 heat-set inserts, set INSERTS = True instead.
"""

import os

import numpy as np
import trimesh
from manifold3d import CrossSection, JoinType, Manifold, set_circular_segments

set_circular_segments(64)
OUT = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------- settings
BOARDS = {
    # name: board length / width (measured + 1.5 mm clearance), USB opening width, dots on the lid
    "P1_ESP32-S3": dict(board_l=66.5, board_w=26.5, usb_w=24.0, dots=1),   # measured ~65 x 25 mm, 2 USB-C ports
    "P2_ESP32-38pin": dict(board_l=51.5, board_w=26.5, usb_w=13.0, dots=2),  # measured ~50 x 25 mm
}
ADXL = (20.8, 16.2)   # GY-291 ADXL345 board pocket (along width, along length) + clearance
WALL = 2.4            # side walls
FLOOR = 2.4
LID = 2.4
IN_W = 42.0           # inside width (room for wires beside the board)
IN_H = 28.0           # inside height
BOARD_Z = 21.0        # board sits this high so jumper wires fit underneath it
ADXL_ZONE = 28.0      # extra inside length for the accelerometer
POST_R = 3.6          # corner screw posts
POST_IN = 2.6         # post centre distance from the inside walls
INSERTS = False       # True = 4.0 mm holes for M3 heat-set inserts
FIT = 0.25            # lid lip clearance


def rrect(w, h, r):
    """Rounded rectangle, lower-left corner at the origin."""
    return CrossSection.square([w - 2 * r, h - 2 * r]).offset(r, JoinType.Round).translate([r, r])


def box(x, y, z, w, d, h):
    return Manifold.cube([w, d, h]).translate([x, y, z])


def cyl(x, y, z, h, r, r2=None):
    return Manifold.cylinder(h, r, r if r2 is None else r2).translate([x, y, z])


def build(board_l, board_w, usb_w, dots):
    in_l = board_l + 2.0 + ADXL_ZONE
    inner = rrect(in_l, IN_W, 1.5)
    outer = inner.offset(WALL, JoinType.Round)
    cy = IN_W / 2
    posts = [(POST_IN, POST_IN), (in_l - POST_IN, POST_IN),
             (POST_IN, IN_W - POST_IN), (in_l - POST_IN, IN_W - POST_IN)]

    # ------------------------------------------------ base (opening up, x=0 is the USB end)
    base = outer.extrude(FLOOR + IN_H) - inner.extrude(IN_H + 1).translate([0, 0, FLOOR])
    for px, py in posts:
        base += cyl(px, py, 0, FLOOR + IN_H, POST_R)
        # fillet the post into the corner so it's strong
        base += box(px - POST_R if px < in_l / 2 else px, py - POST_R if py < cy else py,
                    0, POST_R, POST_R, FLOOR + IN_H)
    # board supports: one at the USB end, a long one at the far end (fits shorter boards too)
    base += box(0, cy - 5, 0, 5, 10, FLOOR + BOARD_Z)
    base += box(board_l - 16, cy - 5, 0, 15, 10, FLOOR + BOARD_Z)
    # accelerometer pocket, open toward the board for the header pins
    ax0 = board_l + 2.0 + (ADXL_ZONE - ADXL[1]) / 2
    ring = box(ax0 - 0.01, cy - ADXL[0] / 2 - 1.6, FLOOR, ADXL[1] + 1.6, ADXL[0] + 3.2, 3.0)
    ring -= box(ax0 - 1, cy - ADXL[0] / 2, FLOOR - 0.1, ADXL[1] + 1, ADXL[0], 4.0)
    base += ring
    # screw holes
    hole_r, depth = (2.0, 6.0) if INSERTS else (1.25, 14.0)
    for px, py in posts:
        base -= cyl(px, py, FLOOR + IN_H - depth, depth + 1, hole_r)
    # USB slot (open to the top; the lid closes over it)
    base -= box(-WALL - 1, cy - usb_w / 2, FLOOR + BOARD_Z - 2.5, WALL + 2, usb_w, IN_H)
    # cable / wire relief under the board for a battery lead if needed
    base -= box(in_l - 1, cy - 4, FLOOR + 3, WALL + 2, 8, 6)

    # ------------------------------------------------ lid (printed outer face down)
    lid = outer.extrude(LID)
    lip_out = rrect(in_l - 2 * FIT, IN_W - 2 * FIT, 1.3).translate([FIT, FIT])
    lip_in = lip_out.offset(-1.2, JoinType.Round)
    lip = (lip_out - lip_in).extrude(2.2).translate([0, 0, LID])
    for px, py in posts:
        lip -= cyl(px, py, LID - 1, 5, POST_R + 0.6)
        lip -= box(px - POST_R - 0.6 if px < in_l / 2 else px, py - POST_R - 0.6 if py < cy else py,
                   LID - 1, POST_R + 0.6, POST_R + 0.6, 5)
    lip -= box(-1, cy - usb_w / 2 - 0.5, LID - 1, 4, usb_w + 1, 5)
    lid += lip
    for px, py in posts:
        lid -= cyl(px, py, -0.1, LID + 1, 1.7)                 # M3 clearance
        lid -= cyl(px, py, -0.01, 1.7, 3.3, 1.6)               # countersink, head on the outside
    # player dots on the outside
    for i in range(dots):
        off = (i - (dots - 1) / 2) * 10
        lid -= cyl(in_l * 0.62 + off, cy, -0.1, 0.7, 3.2)
    # mirror so the lid's USB end matches the base when it's flipped over
    lid = lid.mirror([0, 1, 0]).translate([0, IN_W, 0])
    return base, lid, (in_l + 2 * WALL, IN_W + 2 * WALL, FLOOR + IN_H + LID)


def save(m, path):
    mesh = m.to_mesh()
    tm = trimesh.Trimesh(vertices=np.asarray(mesh.vert_properties)[:, :3],
                         faces=np.asarray(mesh.tri_verts), process=False)
    assert tm.is_watertight, path
    tm.export(path)
    return tm


def main():
    for name, b in BOARDS.items():
        base, lid, size = build(**b)
        for part, m in (("base", base), ("lid", lid)):
            path = os.path.join(OUT, f"{name}_{part}.stl")
            tm = save(m, path)
            print(f"{os.path.basename(path):28s} {tm.volume / 1000:5.1f} cm3  watertight={tm.is_watertight}")
        print(f"  closed case: {size[0]:.0f} x {size[1]:.0f} x {size[2]:.0f} mm")


if __name__ == "__main__":
    main()
