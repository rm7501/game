"""Sahara Racers - FUTURE CITY map kit (NEOM / The Line inspired).

  SM_TheLine_Segment     200 m tileable segment: 500 m mirror walls, terraced inner canyon,
                         planters, lit glass, sky bridges (tiles seamlessly along X)
  SM_NeomTower_Petal     organic petal-section tower with glowing ribs
  SM_NeomTower_Halo      slender tower with a floating halo ring
  SM_MaglevGuideway_30m  elevated maglev beam on Y-columns, light strips
  SM_MaglevCar           maglev pod car
  SM_HoloArch            holographic checkpoint gate (floating rings)
  SM_FutureBarrier_10m   track barrier with light strip
  SM_FutureStreetLight   arc street light with halo head
  SM_Drone               delivery / camera drone
  SM_SolarTree           solar 'tree' with hexagonal PV canopy
  SM_WindHelix           vertical-axis helical wind turbine
  SM_Road_Future_25m     glossy road with emissive lane lines + edge lights
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))
import sr  # noqa: E402

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

KIT = "future"


def M():
    return dict(
        mirror=sr.mat("Line_MirrorFacade", (0.9, 0.92, 0.95), rough=0.02, metal=1.0, kind="mirror"),
        backing=sr.mat("Line_Backing", (0.05, 0.05, 0.06), rough=0.5),
        inner=sr.mat("Line_InnerGlass", (0.75, 0.85, 1.0), rough=0.08, metal=0.5, tex="FacadeNight", tile=24.0, emit_str=1.6),
        slab=sr.mat("Line_SlabWhite", (0.88, 0.88, 0.86), rough=0.4, tex="MetalPanels", tile=6.0),
        green=sr.mat("Line_Planting", (0.18, 0.4, 0.14), rough=0.8, tex="TerraceGrass", tile=3.0),
        cyan=sr.mat("Neon_Cyan", (0.1, 0.9, 1.0), emit=(0.1, 0.85, 1.0), emit_str=14, kind="emissive"),
        magenta=sr.mat("Neon_Magenta", (1.0, 0.2, 0.8), emit=(1.0, 0.2, 0.75), emit_str=12, kind="emissive"),
        warm=sr.mat("Neon_Warm", (1.0, 0.75, 0.45), emit=(1.0, 0.72, 0.42), emit_str=8, kind="emissive"),
        white=sr.mat("Future_White", (0.92, 0.93, 0.95), rough=0.25, metal=0.1, coat=0.6, tex="MetalPanels", tile=3.0),
        dark=sr.mat("Future_Graphite", (0.05, 0.055, 0.065), rough=0.25, metal=0.6),
        glass=sr.mat("Future_GlassBlue", (0.05, 0.12, 0.18), rough=0.03, metal=0.6),
        pv=sr.mat("SolarPanel", (0.03, 0.06, 0.15), rough=0.08, metal=0.7, tex="HexMesh", tile=0.6),
        road=sr.mat("Future_Road", (0.35, 0.38, 0.42), rough=0.35, tex="Asphalt", tile=4.0),
    )


# ---------------------------------------------------------------- The Line ---
def the_line(mm, name="SM_TheLine_Segment", L=200.0, H=500.0):
    rnd = random.Random(5)
    mb = sr.MB(name)
    inner, outer = 60.0, 100.0
    for sg in (1, -1):
        # structural mass
        mb.box((L, outer - inner, H), (0, sg * (inner + outer) / 2, H / 2), m=mm["backing"])
        # outer mirror skin: 10 x 10 m panels with slight random tilt
        cols, rows = int(L / 10), int(H / 10)
        for i in range(cols):
            for j in range(rows):
                x0, x1 = -L / 2 + i * 10 + 0.05, -L / 2 + (i + 1) * 10 - 0.05
                z0, z1 = j * 10 + 0.05, (j + 1) * 10 - 0.05
                t = rnd.uniform(-0.04, 0.04)
                y = sg * (outer + 0.1)
                pts = [(x0, y + t, z0), (x1, y - t, z0), (x1, y - t, z1), (x0, y + t, z1)]
                mb.poly_facing(pts, (0, sg, 0), mm["mirror"])
        # inner lit glass face
        y = sg * (inner - 0.05)
        pts = [(-L / 2, y, 0), (L / 2, y, 0), (L / 2, y, H), (-L / 2, y, H)]
        mb.poly_facing(pts, (0, -sg, 0), mm["inner"])
        # organic terraces every 10 m (periodic in X so segments tile)
        n = 48
        for lv in range(1, int(H / 10)):
            z = lv * 10.0
            ph = lv * 0.73 + (0 if sg > 0 else 1.9)
            pts_in, pts_out = [], []
            for k in range(n + 1):
                x = -L / 2 + L * k / n
                p = 4.0 + 7.0 * (0.5 + 0.5 * math.sin(2 * math.pi * x / L * (1 + lv % 3) + ph))
                pts_out.append((x, sg * (inner - p)))
                pts_in.append((x, sg * inner))
            # slab (loft of rectangles along x)
            rings = []
            for k in range(n + 1):
                x, yo = pts_out[k]
                yi = pts_in[k][1]
                rings.append([(x, yi, z - 0.6), (x, yo, z - 0.6), (x, yo, z + 0.3), (x, yi, z + 0.3)])
            mb.loft(rings, mm["slab"], closed=True, cap_start=True, cap_end=True, smooth=False)
            # planter strip with greenery at the edge + under-slab light line
            rings = []
            for k in range(n + 1):
                x, yo = pts_out[k]
                rings.append([(x, yo + sg * 0.1, z + 0.3), (x, yo + sg * 1.4, z + 0.3), (x, yo + sg * 1.4, z + 1.2),
                              (x, yo + sg * 0.1, z + 1.0 + 0.3 * math.sin(x * 0.7 + lv))])
            mb.loft(rings, mm["green"], closed=True, cap_start=True, cap_end=True, smooth=True)
            if lv % 2 == 0:
                mb.tube([(x, yo + sg * 0.3, z - 0.65) for x, yo in pts_out], 0.12, mm["warm"], seg=4, caps=False)
        # vertical gardens hanging down the inner face
        for k in range(6):
            x = -L / 2 + (k + 0.5) * L / 6
            z0 = rnd.uniform(40, 300)
            mb.box((rnd.uniform(4, 9), 0.8, rnd.uniform(30, 90)), (x, sg * (inner - 0.6), z0), m=mm["green"])
    # sky bridges across the canyon
    for k, (x, z) in enumerate(((-60, 85), (20, 160), (70, 240), (-30, 330), (40, 420))):
        span = 2 * inner + 2
        path = [(x + 6 * math.sin(math.pi * t), -span / 2 + span * t, z - 6 * math.sin(math.pi * t)) for t in [i / 16 for i in range(17)]]
        rings = []
        for (px, py, pz) in path:
            rings.append([(px - 4, py, pz - 1.5), (px + 4, py, pz - 1.5), (px + 4, py, pz + 2.5), (px - 4, py, pz + 2.5)])
        mb.loft(rings, None, closed=True, smooth=False,
                mats=lambda j, i: mm["glass"] if i in (1, 3) else mm["white"])
        mb.tube([(px - 4.05, py, pz - 1.55) for (px, py, pz) in path], 0.15, mm["cyan"], seg=4, caps=False)
        mb.tube([(px + 4.05, py, pz - 1.55) for (px, py, pz) in path], 0.15, mm["cyan"], seg=4, caps=False)
    # canyon floor park strip
    mb.box((L, 2 * inner, 0.4), (0, 0, -0.2), m=mm["green"])
    return mb.to_object(origin="keep", sharp_angle=30)


# ------------------------------------------------------------------ towers ---
def petal_tower(mm, name="SM_NeomTower_Petal", H=280.0):
    mb = sr.MB(name)
    rings = []
    seg = 72
    nz = 70
    for j in range(nz + 1):
        z = H * j / nz
        f = z / H
        R = 26 * (1 - 0.55 * f ** 1.5) * (1 - 0.15 * math.sin(math.pi * f))
        tw = f * 1.4
        ring = []
        for i in range(seg):
            a = 2 * math.pi * i / seg
            r = R * (1 + 0.18 * math.cos(5 * (a - tw)))
            ring.append((r * math.cos(a), r * math.sin(a), z))
        rings.append(ring)
    mb.loft(rings, mm["inner"], closed=True, cap_end=True, smooth=True)
    for p in range(5):   # glowing ribs along the petal crests
        path = []
        for j in range(0, nz + 1, 2):
            z = H * j / nz
            f = z / H
            R = 26 * (1 - 0.55 * f ** 1.5) * (1 - 0.15 * math.sin(math.pi * f))
            a = f * 1.4 + 2 * math.pi * p / 5
            path.append((R * 1.19 * math.cos(a), R * 1.19 * math.sin(a), z))
        mb.tube(path, 0.6, mm["cyan"], seg=6, caps=False)
    mb.cyl(0.8, 30, (0, 0, H + 15), m=mm["white"], seg=10, r2=0.1)
    return mb.to_object(origin="base", sharp_angle=None)


def halo_tower(mm, name="SM_NeomTower_Halo", H=240.0):
    mb = sr.MB(name)
    prof = [(16, 0), (13, 40), (10, 120), (8.5, 200), (7.5, H), (0, H + 6)]
    mb.lathe(prof, seg=48, m=mm["inner"])
    for k in range(4):
        a = 2 * math.pi * k / 4
        mb.tube([((r + 0.6) * math.cos(a + z / 120), (r + 0.6) * math.sin(a + z / 120), z) for r, z in
                 [(16 - 8.5 * t, 200 * t) for t in [i / 20 for i in range(21)]]], 0.5, mm["white"], seg=6)
    # floating halo
    zr = H * 0.82
    ring = [(32 + 2.5 * math.cos(t), 2.0 * math.sin(t)) for t in [2 * math.pi * i / 12 for i in range(13)]]
    mb.lathe([(r, zr + z) for r, z in ring], seg=96, m=mm["white"])
    mb.lathe([(34.6, zr - 0.3), (34.6, zr + 0.3)], seg=96, m=mm["magenta"])
    for k in range(3):
        a = 2 * math.pi * k / 3
        mb.tube([(8.2 * math.cos(a), 8.2 * math.sin(a), zr - 12), (29.5 * math.cos(a), 29.5 * math.sin(a), zr - 0.5)], 0.6, mm["white"], seg=8)
    return mb.to_object(origin="base", sharp_angle=40)


# ------------------------------------------------------------------ maglev ---
def maglev_guideway(mm, name="SM_MaglevGuideway_30m", L=30.0, Hd=14.0):
    mb = sr.MB(name)
    # Y column
    mb.tube([(0, 0, 0), (0, 0, Hd - 5)], [1.4, 1.1], mm["white"], seg=16)
    for sg in (1, -1):
        mb.tube([(0, 0, Hd - 5.5), (0, sg * 2.2, Hd - 0.8)], [1.0, 0.7], mm["white"], seg=12)
    # T-beam
    prof = [(-2.6, Hd - 0.8), (2.6, Hd - 0.8), (2.6, Hd), (1.0, Hd), (1.0, Hd + 0.9), (-1.0, Hd + 0.9), (-1.0, Hd), (-2.6, Hd)]
    rings = [[(x, y, z) for y, z in prof] for x in (-L / 2, L / 2)]
    mb.loft(rings, mm["white"], closed=True, cap_start=True, cap_end=True, smooth=False)
    for sg in (1, -1):
        mb.box((L, 0.1, 0.15), (0, sg * 2.62, Hd - 0.4), m=mm["cyan"])
    return mb.to_object(origin="base")


def maglev_car(mm, name="SM_MaglevCar", L=26.0):
    mb = sr.MB(name)
    rings = []
    xs = [-L / 2, -L / 2 + 0.8, -L / 2 + 3, L / 2 - 6, L / 2 - 2.5, L / 2 - 0.6, L / 2]
    for x in xs:
        if x > L / 2 - 6:
            t = (x - (L / 2 - 6)) / 6
            sc = 1 - t ** 1.8 * 0.85
            zc = 1.9 - 0.9 * t ** 1.5
        elif x < -L / 2 + 3:
            t = ((-L / 2 + 3) - x) / 3
            sc = 1 - t ** 2 * 0.5
            zc = 1.9
        else:
            sc, zc = 1.0, 1.9
        ring = [(x, 1.6 * sc * math.cos(2 * math.pi * i / 20), zc + 1.5 * sc * math.sin(2 * math.pi * i / 20)) for i in range(20)]
        rings.append(ring)
    mb.loft(rings, mm["white"], closed=True, cap_start=True, cap_end=True, smooth=True)
    for sg in (1, -1):
        mb.box((L - 8, 0.05, 0.7), (-1.5, sg * 1.58, 2.3), m=mm["warm"])
        mb.box((L - 2, 0.05, 0.12), (0, sg * 1.55, 1.2), m=mm["cyan"])
    mb.box((3.2, 2.2, 0.6), (L / 2 - 3.2, 0, 2.6), (0, 20, 0), m=mm["glass"])
    mb.box((L - 2, 2.0, 0.5), (0, 0, 0.35), m=mm["dark"])
    return mb.to_object(origin="base", sharp_angle=None)


# ------------------------------------------------------------------- props ---
def holo_arch(mm, name="SM_HoloArch", span=22.0):
    mb = sr.MB(name)
    H = 12.0
    for sg in (1, -1):
        x = sg * span / 2
        mb.box((1.2, 2.0, H), (x, 0, H / 2), m=mm["dark"], bevel=0.2, seg=2)
        mb.box((0.15, 2.05, H - 1), (x - sg * 0.6, 0, H / 2), m=mm["cyan"])
    # floating hexagonal frame + rings
    hexp = [(span / 2 * 1.05 * math.cos(math.pi / 6 + k * math.pi / 3), 0, H * 0.62 + span / 2 * 0.62 * math.sin(math.pi / 6 + k * math.pi / 3)) for k in range(7)]
    mb.tube(hexp, 0.35, mm["cyan"], seg=8)
    for k, (r, w) in enumerate(((span * 0.42, 0.25), (span * 0.36, 0.18))):
        mb.lathe([(r + w * math.cos(t), w * math.sin(t)) for t in [2 * math.pi * i / 8 for i in range(9)]],
                 seg=64, loc=(0, -0.5 + k, H * 0.62), rot=(90, 0, 0), m=mm["magenta"] if k else mm["cyan"])
    mb.box((span, 0.4, 0.25), (0, 0, 0.12), m=mm["cyan"])
    return mb.to_object(origin="base")


def future_barrier(mm, name="SM_FutureBarrier_10m", L=10.0):
    mb = sr.MB(name)
    prof = [(-0.35, 0), (0.35, 0), (0.3, 0.6), (0.12, 0.9), (-0.12, 0.9), (-0.3, 0.6)]
    rings = [[(x, y, z) for y, z in prof] for x in (-L / 2, L / 2)]
    mb.loft(rings, mm["white"], closed=True, cap_start=True, cap_end=True, smooth=True)
    for sg in (1, -1):
        mb.box((L, 0.04, 0.08), (0, sg * 0.25, 0.68), (sg * -30, 0, 0), m=mm["cyan"])
    return mb.to_object(origin="base")


def future_light(mm, name="SM_FutureStreetLight", H=11.0):
    mb = sr.MB(name)
    pts = [(0, 0, 0), (0, 0, H * 0.6), (0.6, 0, H * 0.88), (2.0, 0, H), (3.4, 0, H * 0.97)]
    mb.tube(pts, [0.22, 0.16, 0.13, 0.1, 0.08], mm["white"], seg=10)
    mb.lathe([(0.55 + 0.08 * math.cos(t), 0.08 * math.sin(t)) for t in [2 * math.pi * i / 8 for i in range(9)]],
             seg=32, loc=(3.6, 0, H * 0.95), m=mm["cyan"])
    return mb.to_object(origin="base")


def drone(mm, name="SM_Drone"):
    mb = sr.MB(name)
    mb.sphere(0.35, (0, 0, 0), m=mm["white"], seg=16, rings=10, scale=(1.3, 1.0, 0.45))
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        e = (0.9 * math.cos(a), 0.9 * math.sin(a), 0.05)
        mb.tube([(0, 0, 0), e], 0.04, mm["dark"], seg=6)
        mb.cyl(0.07, 0.12, e, m=mm["dark"], seg=10)
        mb.cyl(0.42, 0.01, (e[0], e[1], 0.13), m=mm["glass"], seg=24)
        mb.sphere(0.04, (e[0], e[1], -0.05), m=mm["cyan"] if k < 2 else mm["magenta"], seg=6, rings=4)
    mb.sphere(0.12, (0.35, 0, -0.12), m=mm["glass"], seg=10, rings=6)
    return mb.to_object(origin="center", sharp_angle=None)


def solar_tree(mm, name="SM_SolarTree", H=9.0):
    rnd = random.Random(2)
    mb = sr.MB(name)
    mb.tube([(0, 0, 0), (0, 0, H * 0.55)], [0.35, 0.25], mm["white"], seg=12)
    for k in range(7):
        a = 2 * math.pi * k / 7 + rnd.uniform(-0.2, 0.2)
        r = rnd.uniform(2.2, 4.0)
        tip = (r * math.cos(a), r * math.sin(a), H * rnd.uniform(0.8, 1.0))
        mb.tube([(0, 0, H * 0.5), (r * 0.4 * math.cos(a), r * 0.4 * math.sin(a), H * 0.75), tip], [0.18, 0.12, 0.07], mm["white"], seg=8)
        hexp = [(tip[0] + 1.3 * math.cos(math.pi / 6 + i * math.pi / 3), tip[1] + 1.3 * math.sin(math.pi / 6 + i * math.pi / 3), tip[2] + 0.1) for i in range(6)]
        mb.poly_facing(hexp, (0, 0, 1), mm["pv"])
        mb.tube(hexp + [hexp[0]], 0.04, mm["white"], seg=4, caps=False)
    mb.lathe([(0.45, 0.0), (0.45, 0.2), (0.0, 0.2)], seg=16, m=mm["cyan"])
    return mb.to_object(origin="base", sharp_angle=None)


def wind_helix(mm, name="SM_WindHelix", H=14.0):
    mb = sr.MB(name)
    mb.cyl(0.25, H + 3, (0, 0, (H + 3) / 2), m=mm["white"], seg=12)
    z0 = 4.0
    for b in range(3):
        rings = []
        for j in range(25):
            t = j / 24
            z = z0 + (H - 1) * t
            a = 2 * math.pi * b / 3 + t * math.pi * 1.2
            r = 2.2 * math.sin(math.pi * (0.15 + 0.7 * t)) + 0.6
            c, s_ = math.cos(a), math.sin(a)
            chord = 0.9
            prof = [(0, 0), (0.25, 0.06), (0.6, 0.04), (1.0, 0.0), (0.6, -0.02), (0.25, -0.03)]
            ring = []
            for (u, v) in prof:
                px = r + v
                py = (u - 0.3) * chord
                ring.append((px * c - py * s_, px * s_ + py * c, z))
            rings.append(ring)
        mb.loft(rings, mm["white"], closed=True, cap_start=True, cap_end=True, smooth=True)
        for z in (z0 + 0.5, z0 + H - 1.5):
            mb.tube([(0, 0, z), (2.4 * math.cos(2 * math.pi * b / 3), 2.4 * math.sin(2 * math.pi * b / 3), z)], 0.06, mm["white"], seg=6)
    mb.cyl(0.6, 0.3, (0, 0, 0.15), m=mm["cyan"], seg=16)
    return mb.to_object(origin="base", sharp_angle=None)


def road_future(mm, name="SM_Road_Future_25m", L=25.0, W=16.0):
    mb = sr.MB(name)
    mb.box((L, W, 0.12), (0, 0, -0.06), m=mm["road"])
    for y in (-W / 4, 0.0, W / 4):
        for k in range(int(L / 5)):
            mb.box((2.5, 0.14, 0.015), (-L / 2 + 1.25 + k * 5, y, 0.008), m=mm["cyan"])
    for sg in (1, -1):
        mb.box((L, 0.2, 0.015), (0, sg * (W / 2 - 0.3), 0.008), m=mm["white"])
        for k in range(int(L / 2.5)):
            mb.box((0.25, 0.25, 0.04), (-L / 2 + 1.25 + k * 2.5, sg * (W / 2 + 0.2), 0.02), m=mm["magenta"] if k % 2 else mm["cyan"])
    return mb.to_object(origin="keep")


# --------------------------------------------------------------------- build ---
def build_all():
    sr.reset()
    mm = M()
    objs = [the_line(mm), petal_tower(mm), halo_tower(mm), maglev_guideway(mm), maglev_car(mm), holo_arch(mm),
            future_barrier(mm), future_light(mm), drone(mm), solar_tree(mm), wind_helix(mm), road_future(mm)]
    for o in objs:
        print(f"{o.name}: {sr.tri_count(o)} tris")
    return objs


def diorama(objs, out=None, cars=("NeomGlide", "Falcon")):
    """Blue hour inside The Line: glowing road, terraces, sky bridges, maglev, drones."""
    by = {o.name: o for o in objs}
    for o in by.values():
        sr.hide(o)
    rnd = random.Random(12)
    for k in range(-1, 5):
        sr.inst(by["SM_TheLine_Segment"], (k * 200.0, 0, 0))
    for k in range(-1, 36):
        sr.inst(by["SM_Road_Future_25m"], (k * 25.0, 0, 0.02))
    for k in range(-1, 70):
        for sg in (1, -1):
            sr.inst(by["SM_FutureBarrier_10m"], (k * 10.0, sg * 9.2, 0.02))
    for k in range(0, 24):
        for sg in (1, -1):
            sr.inst(by["SM_FutureStreetLight"], (k * 35.0 + (17 if sg < 0 else 0), sg * 10.5, 0), (0, 0, 180 if sg > 0 else 0))
    for k in range(-1, 30):
        sr.inst(by["SM_MaglevGuideway_30m"], (k * 30.0, 32, 0))
    sr.inst(by["SM_MaglevCar"], (140, 32, 15.0))
    sr.inst(by["SM_MaglevCar"], (113, 32, 15.0))
    sr.inst(by["SM_HoloArch"], (120, 0, 0), (0, 0, 90))
    for k in range(14):
        x, y = rnd.uniform(15, 400), rnd.uniform(-45, 45)
        if abs(y) < 12:
            continue
        sr.inst(by[rnd.choice(("SM_SolarTree", "SM_WindHelix"))], (x, y, 0), (0, 0, rnd.uniform(0, 360)))
    for k in range(10):
        sr.inst(by["SM_Drone"], (rnd.uniform(20, 300), rnd.uniform(-30, 30), rnd.uniform(18, 70)), (0, 0, rnd.uniform(0, 360)), scale=1.5)
    sr.inst(by["SM_NeomTower_Petal"], (1200, 0, 0))
    sr.ground(5000, sr.mat("Sand", (1, 1, 1), tex="Sand", tile=6), z=-0.05)
    for i, c in enumerate(cars):
        glb = os.path.join(sr.ROOT, "assets", "cars", c, f"{c}_preview.glb")
        if os.path.exists(glb):
            sr.import_glb(glb, ((14, 28)[i], (-2.2, 2.2)[i], 0.02), (0, 0)[i])
    sr.setup_render((1600, 900), 80, exposure=0.3)
    sr.world_color(top=(0.01, 0.03, 0.09), horizon=(0.25, 0.18, 0.3), strength=1.0)
    sr.sun((75, 0, 110), 0.25, (0.6, 0.7, 1.0), 2.0, name="Dusk")
    sr.camera((-14, -4.0, 3.2), (300, 4, 70), 26)
    sr.render(out or os.path.join(sr.ROOT, "docs", "previews", "map_future_city.png"))


if __name__ == "__main__":
    objs = build_all()
    sr.export_kit(objs, KIT)
    sr.write_manifest()
