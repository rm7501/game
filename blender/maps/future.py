"""FUTURE CITY - 'The Line Circuit' (NEOM concept).

Concept: no reference photos were given for this one, so it follows the NEOM idea - The Line, a
500 m tall mirrored megastructure running dead straight through the desert and mountains with a
green, terraced canyon inside it; Oxagon, an octagonal port city floating on the Red Sea; maglev
lines, solar trees and wind helixes. Blue hour, everything glowing.

Main circuit (~4.6 km, clockwise):
  start INSIDE The Line's canyon (glow road, terraces and sky bridges overhead) -> chicanes under the
  Skyway -> out through a portal in the south wall -> a big banked curve wrapped round a granite
  mountain -> futuristic bridge over a gorge -> bridge out to Oxagon, once round the octagon ->
  north up the mountain valley beside the maglev -> back in through a second portal.
Shortcuts:
  Skyway      (visible)  elevated deck down the middle of the canyon, straight over the chicanes
  MarinaJump  (visible)  straight through Oxagon's core: launch over the marina basin
  MaglevLine  (hidden)   a service ramp up onto the maglev guideway, dead straight up the valley
"""
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "lib"))
sys.path.insert(0, os.path.join(HERE, ".."))
import numpy as np  # noqa: E402

import sr  # noqa: E402
import track as trk  # noqa: E402
from track import CP, Track  # noqa: E402
from terrain import Terrain, Noise, smoothstep, terrain_material, dist_to_polyline  # noqa: E402
from mapkit import MapBuild, kit_objects  # noqa: E402

NAME = "FutureCity"
TITLE = "Future City - The Line Circuit"
LINE_Y = 320.0          # centre line of The Line (runs east-west, inner canyon +-60 m, walls to +-100 m)
BASE = 30.0             # canyon floor height
PORTALS = (420.0, -780.0)
OXA = (-330.0, -760.0)  # Oxagon centre (octagon, vertex radius 150)
MOUNT = (600.0, -260.0)  # granite mountain the banked curve wraps round
WATER = 0.0
AP = 119.2              # Oxagon ring road: apothem of the track octagon (vertex radius 129)


def coast_y(x):
    return -590 + 25 * np.sin(x / 120.0) - 420 * smoothstep(80, 520, x)


def oct_pt(a_deg, r):
    a = math.radians(a_deg)
    return OXA[0] + r * math.cos(a), OXA[1] + r * math.sin(a)


# ------------------------------------------------------------------ tracks ---
def tracks():
    GL, N = "glow", "none"
    zc = BASE
    main = [
        CP(-600, 320, 16, z=zc, L=GL, R=GL, surf="glow", tags={"curbs"}),    # start: inside The Line
        CP(-500, 320, 16, z=zc),
        CP(-410, 288, 15, z=zc, bank=-4, tags={"curbs"}),                     # canyon chicanes
        CP(-320, 352, 15, z=zc, bank=4, tags={"curbs"}),
        CP(-220, 288, 15, z=zc, bank=-4, tags={"curbs"}),
        CP(-110, 345, 15, z=zc, bank=3),
        CP(30, 296, 15, z=zc, bank=-3),
        CP(165, 342, 15, z=zc, bank=3),
        CP(285, 320, 15, z=zc),
        CP(365, 312, 15, z=zc, bank=7),
        CP(412, 272, 15, z=zc, bank=4),
        CP(420, 232, 15, z=zc, bank=0, L=N, R=N),                             # portal through the south wall
        CP(423, 185, 15, L=GL, R=GL),
        CP(447, 70, 15),
        CP(510, -35, 15, bank=6),
        CP(605, -105, 15, z=33, bank=12),                                     # banked mountain curve
        CP(705, -190, 15, z=38, bank=15),
        CP(735, -310, 15, z=40, bank=15),
        CP(675, -420, 15, z=37, bank=12),
        CP(560, -472, 15, z=33, bank=5),
        CP(440, -484, 15, z=31, bank=0, deck="future"),                       # bridge over the gorge
        CP(320, -492, 15, z=31),
        CP(205, -522, 15, z=24, bank=-4),
        CP(85, -565, 15, z=12, bank=-3),
        CP(-25, -642, 15, z=4.2, bank=-4),                                    # bridge out to Oxagon
        CP(-125, -730, 15, z=3.4, bank=-3),
    ]
    for k in range(11):                                                       # Oxagon ring (clockwise)
        a = -22.5 * k
        main.append(CP(*oct_pt(a, AP if k % 2 == 0 else 129), 15, z=3.0, bank=0 if k % 2 == 0 else 5,
                       tags={"curbs"} if k % 2 else ()))
    main += [
        CP(-505, -598, 15, z=4.0),                                            # bridge back to shore
        CP(-575, -515, 15),
        CP(-648, -420, 14, bank=-5),                                          # mountain valley S-bends
        CP(-590, -300, 14, bank=6),
        CP(-735, -170, 14, bank=-6),
        CP(-650, -40, 14, bank=6),
        CP(-770, 85, 14, bank=-5),
        CP(-785, 175, 15, bank=0),
        CP(-780, 232, 15, z=zc, L=N, R=N),                                    # second portal
        CP(-760, 290, 15, z=zc, bank=8, L=GL, R=GL),
        CP(-690, 318, 16, z=zc, bank=3),
    ]
    main_t = Track("Track", main, closed=True, surf="glow", L=GL, R=GL)
    main_t.smooth_m = 30.0
    sky = Track("Shortcut_Skyway", [
        CP(-500, 320, 10, z=zc, surf="metal", L=GL, R=GL), CP(-440, 322, 10, z=zc + 6, deck="future"),
        CP(-370, 325, 10, z=zc + 14), CP(-100, 325, 10, z=zc + 15), CP(110, 325, 10, z=zc + 14),
        CP(205, 327, 10, z=zc + 6), CP(285, 320, 11, z=zc)], closed=False, label="Skyway", hidden=False)
    e_mid, w_mid = oct_pt(0, AP), oct_pt(180, AP)
    marina = Track("Shortcut_MarinaJump", [
        CP(*e_mid, 11, z=3.0, surf="glow", L=GL, R=GL), CP(OXA[0] + 94, OXA[1], 10, z=4.9, L=N, R=N, tags={"gap"}),
        CP(OXA[0] + 37, OXA[1], 10, z=3.0, L=GL, R=GL), CP(OXA[0] - 60, OXA[1], 11, z=3.0), CP(*w_mid, 12, z=3.0)],
        closed=False, label="Marina jump", hidden=False)
    maglev = Track("Shortcut_MaglevLine", [
        CP(-648, -420, 8, surf="metal", L=N, R=N), CP(-668, -330, 8, dz=3, deck="future", L=GL, R=GL),
        CP(-690, -150, 8, dz=13), CP(-712, 20, 8, dz=13), CP(-745, 110, 8, dz=4), CP(-785, 175, 9)],
        closed=False, label="Maglev line", hidden=True)
    return main_t, [sky, marina, maglev]


# ----------------------------------------------------------------- terrain ---
def make_terrain():
    t = Terrain(layers=("Sand", "Granite", "Paving", "Gravel"))
    X, Y = t.X, t.Y
    nz = Noise(77)
    WX = X + 60 * (nz.fbm(X + 900, Y + 300, 280, 3) - 0.5) * 2
    WY = Y + 60 * (nz.fbm(X - 700, Y + 1300, 280, 3) - 0.5) * 2
    rid = nz.ridged(WX * 0.8 - WY * 0.6, WX * 0.6 + WY * 0.8, 240, 5)
    big = nz.fbm(WX, WY, 420, 4)
    # desert plain with long dunes
    dunes = nz.ridged(X * 0.35 + 300, Y * 0.9, 90, 3) ** 2
    h = 24 + 8 * (big - 0.5) + 5 * dunes
    # northern granite range behind The Line
    h += (40 + 230 * (0.55 * rid + 0.45 * big ** 1.5)) * smoothstep(470, 900, WY)
    # western range + the ridge that walls the valley
    h += (30 + 200 * rid) * smoothstep(-830, -1000, WX)
    ridge = dist_to_polyline(WX, WY, [(-470, -470), (-430, -200), (-460, 60), (-430, 190)])
    h += (35 + 70 * rid) * np.exp(-(ridge / 70.0) ** 2)
    # granite mountain the banked curve wraps round (road cut into its flank at r ~ 135 m)
    r = np.hypot(X - MOUNT[0], Y - MOUNT[1])
    th = np.arctan2(Y - MOUNT[1], X - MOUNT[0])
    r = r / (1 + 0.12 * np.sin(3 * th) + 0.1 * (nz.fbm(X, Y, 60, 3) - 0.5))
    h = np.maximum(h, 30 + 150 * (1 - np.clip(r / 150.0, 0, 1)) ** 1.3 + 14 * (rid - 0.4) * smoothstep(150, 60, r))
    h += 30 * smoothstep(170, 120, r) * smoothstep(60, 120, r) * 0.0
    # the gorge from the mountain down to the sea
    g = dist_to_polyline(WX, WY, [(420, -330), (395, -520), (430, -720), (390, -1000)])
    h -= 32 * np.exp(-(g / 26.0) ** 2) * smoothstep(-300, -380, Y)
    # The Line: dead-flat band under the megastructure
    band = smoothstep(150, 110, np.abs(Y - LINE_Y))
    h = h + (BASE - 0.3 - h) * band
    # sea to the south-west: beach then a shelf
    cy = coast_y(X)
    sea = smoothstep(cy + 30, cy - 60, Y)
    h = h * (1 - sea) + (-8 + 3 * nz.fbm(X, Y, 80, 2)) * sea
    beach = smoothstep(cy + 170, cy + 10, Y) * (1 - sea)
    h = h + (3.5 - h) * beach ** 1.5 * 0.92
    t.h = h
    t.water_level = WATER
    slope = t.slope()
    t.set_layer(1, smoothstep(0.35, 0.7, slope) + smoothstep(90, 160, h) * 0.6)
    t.set_layer(3, beach * 0.6 + np.exp(-(g / 18.0) ** 2) * (Y < -300))
    t.set_layer(2, band * smoothstep(105, 95, np.abs(Y - LINE_Y)))
    return t


# ------------------------------------------------------------------- props ---
def _clip(poly, a, b, c):
    """Clip a convex polygon to the half-plane a*x + b*y <= c (Sutherland-Hodgman)."""
    out = []
    n = len(poly)
    for i in range(n):
        p, q = poly[i], poly[(i + 1) % n]
        fp, fq = a * p[0] + b * p[1] - c, a * q[0] + b * q[1] - c
        if fp <= 0:
            out.append(p)
        if fp * fq < 0:
            t = fp / (fp - fq)
            out.append((p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t))
    return out


def line_portal(mm, name="SM_TheLine_Portal", L=200.0, H=500.0, OW=40.0, OH=40.0):
    """The Line segment with a 40 x 40 m portal through the south wall (same 200 m tiling)."""
    rnd = random.Random(6)
    mb = sr.MB(name)
    inner, outer = 60.0, 100.0
    for sg in (1, -1):
        cut = sg < 0
        yc = sg * (inner + outer) / 2
        if cut:
            for x0, x1 in ((-L / 2, -OW / 2), (OW / 2, L / 2)):
                mb.box((x1 - x0, outer - inner, H), ((x0 + x1) / 2, yc, H / 2), m=mm["backing"])
            mb.box((OW, outer - inner, H - OH), (0, yc, OH + (H - OH) / 2), m=mm["backing"])
        else:
            mb.box((L, outer - inner, H), (0, yc, H / 2), m=mm["backing"])
        for i in range(int(L / 10)):
            for j in range(int(H / 10)):
                x0, x1 = -L / 2 + i * 10 + 0.05, -L / 2 + (i + 1) * 10 - 0.05
                z0, z1 = j * 10 + 0.05, (j + 1) * 10 - 0.05
                t = rnd.uniform(-0.04, 0.04)
                if cut and x1 > -OW / 2 and x0 < OW / 2 and z0 < OH:
                    continue
                y = sg * (outer + 0.1)
                mb.poly_facing([(x0, y + t, z0), (x1, y - t, z0), (x1, y - t, z1), (x0, y + t, z1)], (0, sg, 0), mm["mirror"])
        y = sg * (inner - 0.05)
        quads = [(-L / 2, L / 2, 0, H)] if not cut else [(-L / 2, -OW / 2, 0, H), (OW / 2, L / 2, 0, H), (-OW / 2, OW / 2, OH, H)]
        for x0, x1, z0, z1 in quads:
            mb.poly_facing([(x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1)], (0, -sg, 0), mm["inner"])
        n = 48
        for lv in range(1, int(H / 10)):
            z = lv * 10.0
            ph = lv * 0.73 + (0 if sg > 0 else 1.9)
            xs = [-L / 2 + L * k / n for k in range(n + 1)]
            parts = [xs]
            if cut and z < OH + 3:
                parts = [[x for x in xs if x <= -OW / 2 - 1], [x for x in xs if x >= OW / 2 + 1]]
            for part in parts:
                if len(part) < 2:
                    continue
                def depth(x, lv=lv, ph=ph):
                    return 4.0 + 7.0 * (0.5 + 0.5 * math.sin(2 * math.pi * x / L * (1 + lv % 3) + ph))
                pts_out = [(x, sg * (inner - depth(x))) for x in part]
                rings = [[(x, sg * inner, z - 0.6), (x, yo, z - 0.6), (x, yo, z + 0.3), (x, sg * inner, z + 0.3)] for x, yo in pts_out]
                mb.loft(rings, mm["slab"], closed=True, cap_start=True, cap_end=True, smooth=False)
                rings = [[(x, yo + sg * 0.1, z + 0.3), (x, yo + sg * 1.4, z + 0.3), (x, yo + sg * 1.4, z + 1.2),
                          (x, yo + sg * 0.1, z + 1.0 + 0.3 * math.sin(x * 0.7 + lv))] for x, yo in pts_out]
                mb.loft(rings, mm["green"], closed=True, cap_start=True, cap_end=True, smooth=True)
                if lv % 2 == 0:
                    mb.tube([(x, yo + sg * 0.3, z - 0.65) for x, yo in pts_out], 0.12, mm["warm"], seg=4, caps=False)
        for k in range(6):
            x = -L / 2 + (k + 0.5) * L / 6
            z0 = rnd.uniform(40, 300)
            hgt = rnd.uniform(30, 90)
            if cut and abs(x) < OW / 2 + 8 and z0 - hgt / 2 < OH + 4:
                continue
            mb.box((rnd.uniform(4, 9), 0.8, hgt), (x, sg * (inner - 0.6), z0), m=mm["green"])
        if cut:     # portal passage: lining, glowing frames on both faces, ceiling lights
            for sx in (1, -1):
                mb.box((0.6, outer - inner, OH), (sx * (OW / 2 - 0.3), yc, OH / 2), m=mm["white"])
            mb.box((OW, outer - inner, 0.6), (0, yc, OH - 0.3), m=mm["white"])
            for yy in (sg * inner, sg * outer):
                mb.tube([(-OW / 2 - 0.8, yy, 0), (-OW / 2 - 0.8, yy, OH + 0.8), (OW / 2 + 0.8, yy, OH + 0.8), (OW / 2 + 0.8, yy, 0)],
                        0.6, mm["cyan"], seg=8, smooth=False)
            for k in range(5):
                yy = sg * (inner + 4 + k * 8)
                mb.box((OW - 6, 0.6, 0.15), (0, yy, OH - 0.7), m=mm["warm"])
    for k, (x, z) in enumerate(((-60, 85), (20, 160), (70, 240), (-30, 330), (40, 420))):
        span = 2 * inner + 2
        path = [(x + 6 * math.sin(math.pi * t), -span / 2 + span * t, z - 6 * math.sin(math.pi * t)) for t in [i / 16 for i in range(17)]]
        rings = [[(px - 4, py, pz - 1.5), (px + 4, py, pz - 1.5), (px + 4, py, pz + 2.5), (px - 4, py, pz + 2.5)] for (px, py, pz) in path]
        mb.loft(rings, None, closed=True, smooth=False, mats=lambda j, i: mm["glass"] if i in (1, 3) else mm["white"])
        mb.tube([(px - 4.05, py, pz - 1.55) for (px, py, pz) in path], 0.15, mm["cyan"], seg=4, caps=False)
        mb.tube([(px + 4.05, py, pz - 1.55) for (px, py, pz) in path], 0.15, mm["cyan"], seg=4, caps=False)
    mb.box((L, 2 * inner, 0.4), (0, 0, -0.2), m=mm["green"])
    return mb.to_object(origin="keep", sharp_angle=30)


def oxagon(mm, name="SM_OxagonPlatform", R=150.0):
    """Floating octagonal port city: deck with a marina basin cut through its core, terraced white
    blocks round a central avenue, harbour cranes, glowing edge. Origin = centre at sea level."""
    rnd = random.Random(8)
    mb = sr.MB(name)
    octa = [(R * math.cos(math.radians(22.5 + 45 * k)), R * math.sin(math.radians(22.5 + 45 * k))) for k in range(8)]
    bx0, bx1, by = 42.0, 90.0, 62.0                       # marina basin (the jump crosses it)
    pieces = [_clip(octa, 1, 0, bx0), _clip(octa, -1, 0, -bx1),
              _clip(_clip(_clip(octa, -1, 0, -bx0), 1, 0, bx1), 0, -1, -by),
              _clip(_clip(_clip(octa, -1, 0, -bx0), 1, 0, bx1), 0, 1, -by)]
    for poly in pieces:
        if len(poly) >= 3:
            mb.prism(poly, -1.2, 2.6, m=mm["white"])
    ring = octa + [octa[0]]
    mb.tube([(x * 1.002, y * 1.002, 2.65) for x, y in ring], 0.25, mm["cyan"], seg=6, caps=False, smooth=False)
    mb.tube([(x * 1.004, y * 1.004, 0.3) for x, y in ring], 0.35, mm["magenta"], seg=6, caps=False, smooth=False)
    for x in (bx0, bx1):         # basin edge light lines
        mb.box((0.3, 2 * by, 0.2), (x, 0, 2.7), m=mm["cyan"])
    # terraced blocks north and south of the central avenue (|y| < 16), inside the ring road (r < 100)
    for k in range(26):
        for _ in range(30):
            x, y = rnd.uniform(-95, 35), rnd.uniform(-95, 95)
            if abs(y) > 18 and math.hypot(x, y) < 96:
                break
        w, d = rnd.uniform(12, 22), rnd.uniform(10, 18)
        levels = rnd.randint(2, 6)
        for lv in range(levels):
            s = 1 - lv * 0.12
            z0 = 2.6 + lv * 4.2
            mb.box((w * s, d * s, 3.2), (x, y, z0 + 1.6), m=mm["white"])
            mb.box((w * s + 0.1, d * s + 0.1, 0.9), (x, y, z0 + 3.65), m=mm["glass"])
            mb.box((w * s * 0.9, 0.5, 0.25), (x, y + d * s / 2 + 0.2, z0 + 3.3), m=mm["green"])
    # central dome over the avenue's west end
    mb.lathe([(20 * math.cos(a), 2.6 + 15 * math.sin(a)) for a in [math.pi / 2 * i / 10 for i in range(11)]][::-1],
             seg=48, loc=(-55, 52, 0), m=mm["glass"])
    mb.lathe([(20.3, 2.6), (20.3, 3.2)], seg=48, loc=(-55, 52, 0), m=mm["cyan"])
    # harbour cranes on the south-west quay
    for k in range(3):
        a = math.radians(-140 + k * 14)
        cx, cy = (R - 18) * math.cos(a), (R - 18) * math.sin(a)
        yaw = math.degrees(a)
        for sx in (-5, 5):
            for sy in (-4, 4):
                mb.box((0.8, 0.8, 26), (cx + sx * math.cos(a) - sy * math.sin(a), cy + sx * math.sin(a) + sy * math.cos(a), 15.6), (0, 0, yaw), m=mm["dark"])
        mb.box((40, 3, 2.4), (cx + 6 * math.cos(a), cy + 6 * math.sin(a), 29), (0, 0, yaw), m=mm["white"])
        mb.box((40, 0.3, 0.3), (cx + 6 * math.cos(a), cy + 6 * math.sin(a), 27.6), (0, 0, yaw), m=mm["magenta"])
    return mb.to_object(origin="keep", sharp_angle=35)


def map_props():
    import kit_future
    mm = kit_future.M()
    objs = [line_portal(mm), oxagon(mm)]
    folder = os.path.join(sr.ROOT, "assets", "maps", NAME, "props")
    sr.export_kit(objs, os.path.relpath(folder, os.path.join(sr.ROOT, "assets")), blend=False)
    return objs


def dress(m: MapBuild):
    T = m.main
    rnd = random.Random(23)

    def yaw_at(tr, s):
        t_ = tr.frame(s)[1]
        return math.degrees(math.atan2(t_[1], t_[0]))
    P = f"maps/{NAME}/props"
    # The Line: endless 200 m segments (portals where the track passes the south wall)
    for k in range(-11, 10):
        x = PORTALS[0] + 200 * k
        if any(abs(x - px) < 1 for px in PORTALS):
            m.place(P, "SM_TheLine_Portal", x, LINE_Y, z=BASE - 0.25)
        else:
            m.place("future", "SM_TheLine_Segment", x, LINE_Y, z=BASE - 0.25)
    p0 = T.frame(0)[0]
    m.place("future", "SM_HoloArch", p0[0], p0[1], z=BASE, yaw=yaw_at(T, 0) + 90, scale=0.85)
    # canyon life: drones, light poles along the glow road
    for k in range(40):
        m.place("future", "SM_Drone", rnd.uniform(-900, 900), LINE_Y + rnd.uniform(-45, 45), z=BASE + rnd.uniform(12, 160),
                yaw=rnd.uniform(0, 360), scale=2.0)
    m.along(T, "future", "SM_FutureStreetLight", 45, 2.5, s0=T.nearest_s((423, 185)) + 20,
            s1=T.nearest_s((-25, -642)), face_road=True, min_clear=1.5)
    m.along(T, "future", "SM_FutureStreetLight", 45, 2.5, s0=T.nearest_s((-575, -515)),
            s1=T.nearest_s((-785, 175)), face_road=True, min_clear=1.5)
    # maglev line running beside The Line (south side) with two pods
    for k in range(-34, 34):          # phase chosen so no column lands on the portal roads
        m.place("future", "SM_MaglevGuideway_30m", 15.0 + k * 30.0, LINE_Y - 128, yaw=0)
    for x in (-420.0, 260.0):
        m.place("future", "SM_MaglevCar", x, LINE_Y - 128, z=float(m.terrain.sample(x, LINE_Y - 128)) + 14.9)
    # Oxagon + its towers
    m.place(P, "SM_OxagonPlatform", OXA[0], OXA[1], z=0.0)
    for (dx, dy, a, nm, sc) in ((-20, 58, 0, "Halo", 0.55), (-2, -60, 40, "Petal", 0.45), (-60, -48, 10, "Halo", 0.4)):
        m.place("future", f"SM_NeomTower_{nm}", OXA[0] + dx, OXA[1] + dy, z=2.6, yaw=a, scale=sc)
    # solar-tree groves and wind helix farms in the desert
    m.scatter("future", "SM_SolarTree", 160, (-400, 350, -420, 140), clearance=10, seed=4, max_slope=0.12,
              min_spacing=14, scale=(1.0, 1.4), mask=lambda x, y: math.hypot(x - MOUNT[0], y - MOUNT[1]) > 200)
    m.scatter("future", "SM_WindHelix", 60, (-1000, 1000, 450, 1000), clearance=20, seed=5, max_slope=0.4,
              min_spacing=40, scale=(1.4, 2.2))
    m.scatter("future", "SM_WindHelix", 30, (700, 1000, -700, 100), clearance=20, seed=6, max_slope=0.4,
              min_spacing=40, scale=(1.4, 2.2))
    m.scatter("alula", ["SM_Boulder_A", "SM_Boulder_B"], 120, (-1000, 1000, -1000, 200), clearance=12, seed=7,
              max_slope=0.8, scale=(0.5, 1.1), sink=0.4)
    # checkpoints: holographic arches
    for s in (1150, 2300, 3450):
        p = T.frame(s)
        m.place("future", "SM_HoloArch", p[0][0], p[0][1], z=float(p[0][2]), yaw=yaw_at(T, s) + 90, scale=0.85)
    # hidden: the maglev service ramp starts behind a row of solar trees
    q = m.shortcuts[2].frame(30)
    for k in (-1, 1):
        r = q[0][:2] + q[2] * 9 * k
        m.place("future", "SM_SolarTree", r[0], r[1], scale=1.5)


# ------------------------------------------------------------------- build ---
def build(render=True, layout_only=False):
    sr.reset()
    t = make_terrain()
    tm = terrain_material(f"{NAME}_Terrain", ["Sand", "Rock", "Concrete", "TrackSand"], [6, 8, 4, 6],
                          [(1.0, 0.9, 0.8), (0.75, 0.5, 0.42), (0.9, 0.92, 0.95), (0.85, 0.75, 0.62)])
    m = MapBuild(NAME, TITLE, t, tm, water=WATER)
    main, shorts = tracks()
    # elevated decks never drop pillars onto a road below
    from scipy.spatial import cKDTree
    m.set_tracks(main, shorts)
    m.build_tracks(carve_layer=2, falloff=16)
    tree = cKDTree(main.P)
    for sc in shorts:
        sc.pillar_ok = lambda x, y: tree.query([x, y])[0] > 12.0
    if layout_only:
        trk.minimap("/tmp/claude-0/future_layout.png", t, main, shorts, TITLE, WATER)
        for tr in [main] + shorts:
            print(f"{tr.name}: {tr.length:.0f} m  bridge {tr.bridge.sum() * tr.step:.0f} m"
                  f"  max grade {np.abs(np.diff(tr.Z) / tr.step).max() * 100:.0f}%")
        for sc in shorts:
            a, b = main.nearest_s(sc.P[0]), main.nearest_s(sc.P[-1])
            print(f"  {sc.name}: saves {(b - a) % main.length - sc.length:.0f} m")
        return m
    props = map_props()
    dress(m)
    m.export()
    m.write_gameplay(pickups=(450, 1500, 2600, 3700), boosts=(200, 1250, 2400, 3500))
    sr.write_manifest()
    if render:
        previews(m, props)
    return m


def lighting():
    sr.world_color(top=(0.015, 0.04, 0.12), horizon=(0.32, 0.22, 0.36), strength=1.3)
    sr.sun((84, 0, 250), 0.6, (0.75, 0.75, 1.0), 2.0, name="Dusk")
    import bpy
    bpy.context.scene.view_settings.exposure = 0.6


def previews(m, props):
    from mapkit import render_previews
    kits = kit_objects("future", "common", "alula") + props
    m.preview_scene(kits)
    T = m.main
    s_mtn = T.nearest_s((705, -190))
    s_oxa = T.nearest_s(oct_pt(-67.5, 129))
    # (Oxagon octagon: vertex CPs at r=129, side midpoints at the apothem AP)
    cars = [("NeomGlide", 58, -3.0, None), ("Falcon", 74, 3.0, None), ("JeddahGT", s_mtn + 14, 2.0, None),
            ("RiyadhMuscle", s_oxa + 16, -2.0, None), ("DuneFox", 120, 0.0, m.shortcuts[0])]
    shots = [("overview", (1250, -1350, 520), (-120, 120, 90), 30),
             ("chase", 44, dict(back=12, height=3.2, ahead=60, lens=26)),
             ("chase", s_mtn - 4, dict(back=13, height=4.0, ahead=70, lens=26)),
             ("overview", (-60, -560, 70), (OXA[0], OXA[1], 10), 30),
             ("chase", 100, dict(back=12, height=3.5, ahead=60, lens=26, track=m.shortcuts[0])),
             ("overview", (300, -650, 160), (60, 320, 190), 26)]
    render_previews(m, shots, lighting, cars)


if __name__ == "__main__":
    build(layout_only="--layout" in sys.argv)
