"""JEDDAH - 'Corniche & Al-Balad'.

Concept (reference photos): the Red Sea Corniche - a curved seawall promenade with palms and white
railings, a white mosque standing on the sea, the long coastline with a lagoon and the city towers
beyond - and the old town Al-Balad: narrow lanes of coral-stone houses with teal and brown rawasheen,
string lights and souq awnings.

Main circuit (~4.2 km): Corniche (start, sea on the left) -> past the floating mosque -> cove bridge ->
through the great Bab Makkah gate -> Al-Balad lanes with string lights -> Nassif House plaza ->
lagoon bridge -> back onto the Corniche.
Shortcuts:
  BeachRun     (visible) drop onto the sand and race along the waterline
  SouqPassage  (hidden)  a covered souq alley straight through an Al-Balad block
  LagoonJump   (hidden)  ramp off the fishing pier and fly across the lagoon mouth
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
from terrain import Terrain, Noise, smoothstep, terrain_material  # noqa: E402
from mapkit import MapBuild, kit_objects  # noqa: E402

NAME = "JeddahCorniche"
TITLE = "Jeddah - Corniche & Al-Balad"
WATER = 0.0
MOSQUE = (-600.0, 250.0)


def coast_x(y):
    return -470 + 22 * np.sin(y / 170.0) + 10 * np.sin(y / 61.0)


def far_height(X, Y):
    """Red Sea to the west, the city plain rising gently inland, the Hijaz mountains on the eastern horizon."""
    nz = Noise(38)
    cx = coast_x(Y)
    d = X - cx
    land = 2.2 + np.clip(d, 0, None) * 0.008 + (nz.fbm(X, Y, 300, 4) - 0.5) * 3.0
    sea = -np.clip(-d, 0, 600) * 0.05 - 1.5
    h = np.where(d > 0, land, sea)
    h = h * smoothstep(-25, 25, d) + np.minimum(h, sea) * (1 - smoothstep(-25, 25, d))
    beach = smoothstep(-20, 0, d) * (1 - smoothstep(0, 45, d))
    h = h * (1 - beach) + (0.3 + np.clip(d, 0, None) * 0.05) * beach
    # Hijaz escarpment: dark rocky ranges 8-20 km inland, with foothills
    wx = X + 400 * (nz.fbm(X, Y, 900, 3) - 0.5)
    rng = nz.ridged(wx * 0.6, Y * 0.6, 900, 5)
    h += (60 + 650 * rng ** 1.4) * smoothstep(6500, 14000, wx)
    h += 40 * nz.ridged(X, Y, 400, 3) ** 2 * smoothstep(3000, 7000, wx)
    # offshore reefs: a few low sandy islands far out to sea
    isl = smoothstep(0.7, 0.76, nz.fbm(X, Y, 700, 3)) * smoothstep(-3000, -5000, d)
    return np.maximum(h, -1.5 + isl * 3.5)


def far_paint(X, Y, H, slope, d):
    cx = coast_x(Y)
    dd = X - cx
    w = np.zeros((4,) + X.shape)
    w[1] = smoothstep(0.3, 0.6, slope) + smoothstep(120, 300, H)
    w[3] = smoothstep(1.2, 0.2, H) * (H > -0.5)
    w[2] = smoothstep(150, 300, dd) * (1 - smoothstep(9000, 12000, dd)) * smoothstep(0.55, 0.62, Noise(39).fbm(X, Y, 80, 2)) * 0.6
    w[0] = np.clip(1 - w[1] - w[2] - w[3], 0, 1)
    return w


def far_city(m):
    """Jeddah spreading inland and along the coast at sunset: white and beige blocks, towers on the
    Corniche, palms; merged chunk meshes."""
    from backdrop import Merged, scatter_points, outside
    B = m.backdrop
    rnd = random.Random(52)
    wall = sr.mat("Far_JeddahWhite", (0.95, 0.92, 0.86), rough=0.7, tex="FacadeNight", tile=14.0, emit_str=0.5)
    beige = sr.mat("Far_JeddahBeige", (0.95, 0.82, 0.66), rough=0.75, tex="FacadeNight", tile=14.0, emit_str=0.5)
    glass = sr.mat("KC_FacadeNight", (0.8, 0.85, 0.95), rough=0.08, metal=0.7, tex="FacadeTower", tile=24.0, emit_str=1.6)
    roof = sr.mat("Far_RoofLight", (0.75, 0.72, 0.66), rough=0.9)
    palm_t = sr.mat("Far_PalmTrunk", (0.3, 0.22, 0.15), rough=0.9)
    palm_f = sr.mat("Far_PalmFrond", (0.16, 0.24, 0.08), rough=0.8, kind="foliage")
    mg = Merged(f"SM_{NAME}_Far_City")
    mt = Merged(f"SM_{NAME}_Far_Towers")

    def land(x, y, inset=60):
        return outside(x, y, pad=50) and x - float(coast_x(np.array(y))) > inset and x < 7000 and abs(y) < 9000
    street = sr.mat("Far_Asphalt", (0.22, 0.22, 0.23), rough=0.8)
    ms = Merged(f"SM_{NAME}_Far_Streets")
    for g in np.arange(-9000, 9001, 140.0):          # street grid (rotated 12 deg like the old city plan)
        for horiz in (True, False):
            run = []
            for u in np.arange(-9000, 9001, 50.0):
                x0, y0 = (u, g) if horiz else (g, u)
                c, s_ = math.cos(math.radians(12)), math.sin(math.radians(12))
                x, y = x0 * c - y0 * s_, x0 * s_ + y0 * c
                ok = land(x, y, 120)
                if ok:
                    run.append((x, y))
                if (not ok or u >= 8950) and len(run) > 1:
                    xs, ys = np.array([p[0] for p in run]), np.array([p[1] for p in run])
                    zz = B.height(xs, ys) + 0.25
                    nx, ny = ((-s_ * 3.0, c * 3.0) if horiz else (c * 3.0, s_ * 3.0))
                    rows = [[(x - nx, y - ny, z), (x + nx, y + ny, z)] for x, y, z in zip(xs, ys, zz)]
                    ms._mb(xs.mean(), ys.mean()).strip([r[::-1] for r in rows] if horiz else rows, None, street,
                                                     smooth=False, keep=False)
                    run = []
                elif not ok:
                    run = []
    pts = scatter_points(rnd, 9000, lambda x, y: land(x, y) and rnd.random() < 3000 / max(math.hypot(x, y), 1100),
                         (-1500, 7000, -9000, 9000))
    zs = B.height(np.array([p[0] for p in pts]), np.array([p[1] for p in pts]))
    for (x, y), z in zip(pts, zs):
        h = rnd.choice((6, 9, 12, 15, 18, 24, 30))
        mg.block(x, y, float(z), rnd.uniform(14, 36), rnd.uniform(14, 36), h, rnd.uniform(-4, 4) + rnd.choice((0, 90)),
                 rnd.choice((wall, beige)), roof)
    # towers along the Corniche to the north (Al-Shati, Obhur) and south
    for k in range(150):
        y = rnd.choice((1, -1)) * rnd.uniform(1100, 8500)
        x = float(coast_x(np.array(y))) + rnd.uniform(90, 600)
        z = float(B.height(np.array([x]), np.array([y]))[0])
        if rnd.random() < 0.35:
            mt.tower(x, y, z, rnd.uniform(12, 20), rnd.uniform(60, 180), glass, seg=rnd.choice((6, 8)))
        else:
            mt.block(x, y, z, rnd.uniform(22, 36), rnd.uniform(22, 36), rnd.uniform(40, 150), rnd.uniform(0, 90), glass)
    for k in range(900):                    # Corniche palms continuing both ways
        y = rnd.choice((1, -1)) * rnd.uniform(1050, 8500)
        x = float(coast_x(np.array(y))) + rnd.uniform(25, 60)
        z = float(B.height(np.array([x]), np.array([y]))[0])
        mg.palm(x, y, z, rnd.uniform(7, 10), palm_t, palm_f, rnd)
    return mg.objects() + mt.objects() + ms.objects()


def make_terrain():
    t = Terrain(layers=("Sand", "CoralRock", "Paving", "WetSand"))
    X, Y = t.X, t.Y
    nz = Noise(37)
    cx = coast_x(Y)
    d = X - cx                                     # + inland, - sea
    land = 2.2 + np.clip(d, 0, None) * 0.012 + (nz.fbm(X, Y, 200, 4) - 0.5) * 2.0
    sea = -np.clip(-d, 0, 400) * 0.05 - 1.5
    h = np.where(d > 0, land, sea)
    h = h * smoothstep(-25, 25, d) + np.minimum(h, sea) * (1 - smoothstep(-25, 25, d))
    beach = smoothstep(-20, 0, d) * (1 - smoothstep(0, 45, d))
    h = h * (1 - beach) + (0.3 + np.clip(d, 0, None) * 0.05) * beach
    # lagoon inlet cutting east into the land
    lag = smoothstep(70, 40, np.abs(Y - (-560) - 12 * np.sin(X / 60.0))) * smoothstep(-120, -160, X - 0) * (X > cx - 40)
    lag = lag * smoothstep(-300, -250, -X - 150)
    h = h * (1 - lag) + (-3.0) * lag
    # cove north of the mosque (crossed by a bridge)
    cove = np.exp(-(((X - (-430)) / 70) ** 2 + ((Y - 620) / 45) ** 2))
    h = h - cove * 6
    # old town plateau (very gentle) and modern city east
    t.h = h
    t.water_level = WATER
    slope = t.slope()
    wet = smoothstep(1.2, 0.2, t.h) * (t.h > -0.5)
    t.set_layer(3, wet)
    t.set_layer(1, smoothstep(0.35, 0.7, slope) * (t.h < 4))
    town = smoothstep(-100, -40, X - cx - 300) * 0 + smoothstep(-80, 0, X + 80) * (Y > -480)
    t.set_layer(2, town * smoothstep(0.4, 0.6, nz.fbm(X, Y, 20, 2) * 0.3 + 0.55))
    return t


def tracks():
    RL, J, N = "railing", "jersey", "none"
    main = [
        CP(-430, -330, 15, surf="asphalt", L=RL, R=N, tags={"curbs"}),       # start: Corniche, sea on the left
        CP(-440, -120, 15),
        CP(-408, -30, 15, bank=3),                                           # swings inland round the palm park
        CP(-328, 60, 15, bank=4),
        CP(-330, 150, 15, bank=-4),
        CP(-405, 232, 15, bank=-3),
        CP(-418, 300, 15),                                                   # floating mosque on the left
        CP(-420, 430, 15),
        CP(-430, 560, 14, z=5.5, deck="stone"),                              # cove bridge
        CP(-410, 690, 14, bank=-6),
        CP(-290, 760, 14, L=J, R=J),
        CP(-80, 720, 14),
        CP(90, 640, 13, bank=6),
        CP(160, 560, 12, surf="cobble", L=N, R=N),                           # through Bab Makkah
        CP(170, 440, 11),
        CP(140, 330, 11, tags={"curbs"}),                                    # Al-Balad lanes
        CP(280, 300, 11, tags={"curbs"}),
        CP(330, 180, 11),
        CP(250, 90, 11, tags={"curbs"}),
        CP(120, 80, 11, tags={"curbs"}),
        CP(80, -40, 11),
        CP(170, -140, 11, tags={"curbs"}),
        CP(320, -170, 12),                                                   # Nassif House plaza
        CP(330, -300, 12, bank=6),
        CP(200, -380, 12),
        CP(40, -420, 13, surf="asphalt", L=J, R=J),
        CP(-100, -470, 14),
        CP(-55, -560, 14, bank=-6),                                          # around the lagoon's east end
        CP(-120, -670, 14, bank=-4),
        CP(-280, -690, 14),
        CP(-420, -665, 14, bank=-6),
        CP(-455, -585, 14, z=5.0, deck="highway"),                           # bridge over the lagoon mouth
        CP(-445, -470, 15, L=RL, R=N),
    ]
    main_t = Track("Track", main, closed=True, surf="asphalt", L=RL, R=N)
    s_beach = Track("Shortcut_BeachRun", [CP(-440, -120, 10, surf="sand", L=N, R=N)] +
                    [CP(float(coast_x(y)) + 5, y, 10, z=0.9) for y in (-20, 100, 215)] +
                    [CP(-418, 300, 10)], closed=False, label="Beach run", hidden=False)
    s_souq = Track("Shortcut_SouqPassage", [
        CP(280, 300, 6, surf="cobble", L=N, R=N), CP(240, 220, 6), CP(200, 150, 6), CP(120, 80, 7)],
        closed=False, label="Souq passage", hidden=True)
    s_lag = Track("Shortcut_LagoonJump", [
        CP(-100, -470, 9, surf="asphalt_old", L=N, R=N), CP(-165, -495, 8, z=4.5, deck="pier"),
        CP(-205, -535, 8, z=6.5, tags={"gap"}), CP(-255, -632, 9, z=2.8), CP(-280, -690, 10)],
        closed=False, label="Lagoon jump", hidden=True)
    return main_t, [s_beach, s_souq, s_lag]


# ------------------------------------------------------------- new assets ---
def floating_mosque(name="SM_FloatingMosque"):
    """White mosque on a platform over the sea (inspired by Al-Rahma), causeway towards the shore."""
    w = sr.mat("Mosque_White", (0.93, 0.93, 0.9), rough=0.6, tex="Concrete", tile=3.0)
    trim = sr.mat("Mosque_Trim", (0.75, 0.72, 0.65), rough=0.5)
    dark = sr.mat("WindowDarkHole", (0.02, 0.015, 0.01), rough=0.9)
    glass = sr.mat("Mosque_Glass", (0.1, 0.25, 0.3), rough=0.1, metal=0.5)
    brass = sr.mat("Brass", (0.8, 0.58, 0.25), rough=0.3, metal=1.0)
    mb = sr.MB(name)
    # platform on piles
    mb.box((60, 60, 1.2), (0, 0, 1.6), m=w)
    for x in range(-27, 28, 9):
        for y in range(-27, 28, 9):
            mb.cyl(0.5, 6, (x, y, -1.8), m=trim, seg=8)
    # prayer hall + arcade of arches
    mb.box((34, 34, 9), (0, 0, 6.7), m=w)
    for side in range(4):
        ang = side * 90
        c, s_ = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        for k in range(7):
            u = -15 + k * 5
            x, y = 17.05 * c - u * s_, 17.05 * s_ + u * c
            mb.box((0.1 if c else 2.4, 2.4 if c else 0.1, 4.6), (x, y, 5.4), m=dark)
            mb.lathe([(1.2, 0), (1.2, 0.1)], seg=12, arc=180, loc=(x, y, 7.7), rot=(90, 0, ang + 90), m=dark)
        mb.box((34.6 if not c else 0.6, 0.6 if not c else 34.6, 0.8), (17.2 * c, 17.2 * s_, 11.6), m=trim)
    # central dome on a drum + four small domes
    mb.cyl(9, 3, (0, 0, 12.7), m=w, seg=48)
    mb.lathe([(9.6, 14.2), (9.4, 16), (8, 19), (5.5, 21.5), (2.5, 23), (0, 23.6)], seg=48, m=w)
    for k in range(16):
        a = 2 * math.pi * k / 16
        mb.box((0.15, 1.2, 1.8), (9.05 * math.cos(a), 9.05 * math.sin(a), 12.7), (0, 0, math.degrees(a)), m=glass)
    mb.cyl(0.08, 2.5, (0, 0, 24.8), m=brass, seg=8)
    for sx in (1, -1):
        for sy in (1, -1):
            mb.cyl(3.2, 2, (sx * 12, sy * 12, 12.2), m=w, seg=24)
            mb.lathe([(3.4, 13.2), (3.1, 14.4), (1.8, 15.6), (0, 16.1)], seg=24, loc=(sx * 12, sy * 12, 0), m=w)
    # minaret with two balconies
    mx, my = 22, -22
    mb.box((5, 5, 10), (mx, my, 7.2), m=w)
    mb.cyl(1.9, 22, (mx, my, 23.2), m=w, seg=16, r2=1.6)
    for z in (22, 32):
        mb.cyl(2.8, 0.4, (mx, my, z), m=trim, seg=24)
        for k in range(20):
            a = 2 * math.pi * k / 20
            mb.box((0.1, 0.1, 1.0), (mx + 2.7 * math.cos(a), my + 2.7 * math.sin(a), z + 0.7), m=w)
    mb.lathe([(1.7, 34.2), (1.8, 35.5), (1.2, 37), (0.3, 38.4), (0, 38.6)], seg=16, loc=(mx, my, 0), m=w)
    mb.cyl(0.06, 1.6, (mx, my, 39.4), m=brass, seg=6)
    # causeway towards the shore (+X)
    mb.box((150, 9, 0.9), (105, 0, 1.4), m=w)
    for x in range(35, 180, 12):
        for sy in (1, -1):
            mb.box((0.15, 0.15, 1.1), (x, sy * 4.4, 2.4), m=trim)
        mb.cyl(0.4, 5, (x, 0, -1.6), m=trim, seg=8)
    mb.box((150, 0.1, 0.1), (105, 4.4, 2.9), m=trim)
    mb.box((150, 0.1, 0.1), (105, -4.4, 2.9), m=trim)
    return mb.to_object(origin="keep", sharp_angle=35)


def jeddah_tower(name="SM_JeddahTower", H=650.0):
    """Tri-lobed super-tall under construction (backdrop)."""
    glass = sr.mat("Riyadh_FacadeNight", (1, 1, 1), rough=0.1, metal=0.6, tex="FacadeNight", tile=24.0, emit_str=2.0)
    conc = sr.mat("ConcreteWarm", (1.0, 0.95, 0.86), tex="Concrete", tile=4.0)
    steel = sr.mat("SteelDark", (0.08, 0.08, 0.09), rough=0.4, metal=1.0)
    red = sr.mat("AviationRed", (0.6, 0.0, 0.0), emit=(1, 0.02, 0.0), emit_str=20, kind="emissive")
    mb = sr.MB(name)
    rings = []
    for j in range(41):
        z = H * j / 40
        f = z / H
        ring = []
        for i in range(36):
            a = 2 * math.pi * i / 36
            lobes = 1 + 0.55 * max(0, math.cos(3 * a)) ** 2 * (1 - f) ** 1.2
            r = 42 * (1 - 0.82 * f) * lobes
            ring.append((r * math.cos(a), r * math.sin(a), z))
        rings.append(ring)
    mb.loft(rings, glass, closed=True, cap_end=True, smooth=True)
    mb.cyl(6, 80, (0, 0, H + 40), m=conc, seg=12, r2=3)       # exposed core at the top
    mb.box((70, 2, 2), (20, 0, H + 85), m=steel)               # tower crane
    mb.box((3, 3, 90), (0, 0, H + 40), m=steel)
    mb.sphere(1.5, (0, 0, H + 82), m=red, seg=8, rings=6)
    return mb.to_object(origin="base", sharp_angle=40)


def fountain(name="SM_KingFahdFountain"):
    jet = sr.mat("FountainJet", (0.95, 0.97, 1.0), emit=(0.9, 0.95, 1.0), emit_str=2.5, kind="emissive", alpha=0.55)
    mb = sr.MB(name)
    mb.lathe([(1.6, 0), (0.9, 60), (0.6, 200), (1.4, 290), (3.0, 305), (0, 312)], seg=16, m=jet)   # the jet
    mb.lathe([(0, 300), (5, 292), (8, 250), (9.5, 180), (10, 120)], seg=16, m=jet)                  # falling spray veil
    return mb.to_object(origin="base", sharp_angle=None)


def map_props():
    objs = [floating_mosque(), jeddah_tower(), fountain()]
    sr.export_kit(objs, f"maps/{NAME}/props", blend=False)
    return objs


def dress(m: MapBuild):
    T = m.main
    rnd = random.Random(11)
    p, t, n, w, b = T.frame(0)
    m.place("common", "SM_StartGantry", p[0], p[1], yaw=math.degrees(math.atan2(t[1], t[0])) + 90)
    m.place(f"maps/{NAME}/props", "SM_FloatingMosque", MOSQUE[0], MOSQUE[1], z=0.0)
    m.place(f"maps/{NAME}/props", "SM_JeddahTower", 650, 1500, z=0.0)
    m.place(f"maps/{NAME}/props", "SM_KingFahdFountain", -900, -150, z=0.0)
    # Corniche: palms on the land side, lights both sides, breakwater on the sea side
    s_corn = T.nearest_s((-410, 690))
    m.along(T, "common", ["SM_DatePalm_A", "SM_DatePalm_B"], 16, 6.0, s0=0, s1=s_corn, side=(-1,), jitter=1.5)
    m.along(T, "riyadh", "SM_StreetLight_KFR", 45, 2.0, s0=10, s1=s_corn, side=(-1,))
    # the palm park the Corniche swings round (the beach run passes in front of it)
    m.scatter("common", ["SM_DatePalm_A", "SM_DatePalm_B", "SM_DatePalm_C"], 70, (-470, -330, -60, 230), clearance=5,
              seed=13, min_spacing=9, mask=lambda x, y: x - coast_x(y) > 22)
    for k, (x, y) in enumerate(((-385, 40), (-392, 110), (-372, 170))):
        m.place("jeddah", "SM_SouqStall", x, y, yaw=90 + k * 20)
    m.scatter("alula", ["SM_Boulder_A", "SM_Boulder_B"], 260, (-560, -380, -700, 900), clearance=3, seed=3,
              max_slope=3.0, mask=lambda x, y: -14 < x - coast_x(y) < 4, scale=(0.4, 0.9), sink=0.6)
    # Al-Balad: houses lining every lane (facades to the street), string lights and awnings overhead
    s_old0, s_old1 = T.nearest_s((160, 560)), T.nearest_s((40, -420))
    houses = [f"SM_HijaziHouse_{i:02d}" for i in range(1, 7)]
    m.along(T, "jeddah", houses, 11, 6.0, s0=s_old0 + 25, s1=s_old1, yaw_add=-90, jitter=0.8, min_clear=1.0)
    for sc in m.shortcuts[1:2]:
        m.along(sc, "jeddah", houses, 11, 5.5, s0=8, s1=sc.length - 8, yaw_add=-90, min_clear=1.0)
    s = s_old0 + 30
    while s < s_old1 - 20:
        p, t, n, w, b = T.frame(s)
        yaw = math.degrees(math.atan2(t[1], t[0])) + 90
        m.place("jeddah", "SM_StringLights" if int(s) % 2 else "SM_SouqAwning", p[0], p[1], z=p[2] + 7.2, yaw=yaw)
        s += 24
    sc = m.shortcuts[1]
    for s in range(6, int(sc.length) - 4, 9):          # the covered souq: awnings + stalls + lanterns
        p, t, n, w, b = sc.frame(s)
        yaw = math.degrees(math.atan2(t[1], t[0])) + 90
        m.place("jeddah", "SM_SouqAwning", p[0], p[1], z=p[2] + 5.0, yaw=yaw)
        m.place("jeddah", "SM_Lantern", p[0], p[1], z=p[2] + 4.8)
    sp = sc.frame(3)[0]
    m.place("jeddah", "SM_SouqStall", sp[0] + 1.5, sp[1] + 1.5, z=sp[2], yaw=30)       # hides the entrance
    pg, tg, ng, wg, bg = T.frame(T.nearest_s((160, 560)))
    m.place("jeddah", "SM_BabMakkah", pg[0], pg[1], z=pg[2], yaw=math.degrees(math.atan2(tg[1], tg[0])) + 90, scale=2.3)
    m.place("jeddah", "SM_NassifHouse", 420, -230, yaw=90)
    m.place("jeddah", "SM_HijaziMinaret", 230, 200)
    m.place("jeddah", "SM_HijaziMinaret", 60, -250)
    # modern Jeddah to the east and north
    blocks = [f"SM_RiyadhBlock_{i:02d}" for i in range(1, 7)]
    modern_city(m)
    m.scatter("riyadh", blocks, 60, (-350, 450, 760, 980), clearance=20, seed=6, max_slope=0.2, min_spacing=40, yaw=0)
    m.scatter("jeddah", houses, 90, (-60, 460, -460, 520), clearance=14, seed=7, max_slope=0.2, min_spacing=14)
    m.scatter("common", ["SM_DatePalm_A", "SM_DatePalm_B"], 120, (-430, 450, -950, 950), clearance=8, seed=8,
              max_slope=0.2, min_spacing=10, mask=lambda x, y: x - coast_x(y) > 20)
    life(m)


def modern_city(m: MapBuild):
    """Modern Jeddah east of Al-Balad: a street grid (rotated like the far city) with blocks, villas,
    Hijazi-style houses, shops, mosques and car parks."""
    import dressing as D
    blocks = [f"SM_RiyadhBlock_{i:02d}" for i in range(1, 7)]
    houses = [f"SM_HijaziHouse_{i:02d}" for i in range(1, 7)]
    lots = D.city_grid(m, (440, 1000, -1000, 1000), lambda x, y: True, block=110, street=15, angle=12,
                       lamps=("riyadh", "SM_StreetLight_KFR"))

    def towers(m, x, y, yaw, size, rnd):
        for q in D.lot_quads(x, y, yaw, size, rnd.choice((2, 3, 4))):
            m.place("riyadh", rnd.choice(blocks), q[0], q[1], yaw=yaw + rnd.choice((0, 90, 180, 270)), scale=rnd.uniform(0.8, 1.15))

    def hijazi(m, x, y, yaw, size, rnd):
        for q in D.lot_quads(x, y, yaw, size):
            m.place("jeddah", rnd.choice(houses), q[0], q[1], yaw=yaw + rnd.choice((0, 90, 180, 270)), scale=rnd.uniform(1.1, 1.5))

    def villas(m, x, y, yaw, size, rnd):
        for q in D.lot_quads(x, y, yaw, size):
            m.place("life", "SM_Villa", q[0], q[1], yaw=yaw + rnd.choice((0, 180)))

    def shops(m, x, y, yaw, size, rnd):
        a = math.radians(yaw)
        for sg in (1, -1):
            m.place("life", "SM_ShopRow", x - math.sin(a) * sg * size * 0.32, y + math.cos(a) * sg * size * 0.32,
                    yaw=yaw + (0 if sg > 0 else 180))
        D.parking(m, x, y, yaw, size * 0.5, rnd)

    def mosque(m, x, y, yaw, size, rnd):
        m.place("life", "SM_Mosque_Dome", x, y, yaw=yaw)
    D.fill_lots(m, lots, [(0.4, towers), (0.2, hijazi), (0.15, villas), (0.12, shops), (0.08, D.parking), (0.05, mosque)],
                seed=6)


def life(m: MapBuild):
    """Race evening in Jeddah: crowds on the Corniche, families on the beach, dhows, fishing boats and
    yachts on the water, cargo ships on the horizon, people in the Al-Balad lanes, the city behind."""
    import dressing as D
    rnd = random.Random(29)
    T = m.main
    D.trackside(m, spots=[T.nearest_s((-410, 236)), T.nearest_s((160, 560))])
    t = m.terrain

    def sea(x, y, depth=1.2):
        return float(t.sample(x, y)) < -depth
    boats = []
    for k in range(70):                                      # fishing boats and dhows along the coast
        y = rnd.uniform(-950, 950)
        x = float(coast_x(np.array(y))) - rnd.uniform(40, 260)
        if sea(x, y) and all((x - bx) ** 2 + (y - by) ** 2 > 400 for bx, by in boats) and abs(y - MOSQUE[1]) > 80:
            m.place("life", rnd.choice(["SM_FishingBoat", "SM_FishingBoat", "SM_Dhow"]), x, y, z=0.0, yaw=rnd.uniform(0, 360))
            boats.append((x, y))
    for k in range(40):                                      # boats moored in the lagoon and the cove
        x, y = rnd.uniform(-460, -150), rnd.uniform(-620, -500)
        if rnd.random() < 0.3:
            x, y = -430 + rnd.uniform(-50, 50), 620 + rnd.uniform(-30, 30)
        if sea(x, y, 1.5) and m.clearance(x, y) > 8 and all((x - bx) ** 2 + (y - by) ** 2 > 200 for bx, by in boats):
            m.place("life", rnd.choice(["SM_FishingBoat", "SM_Dhow", "SM_Yacht"]), x, y, z=0.0, yaw=rnd.uniform(0, 360))
            boats.append((x, y))
    for x, y in ((-700, 450), (-760, 150), (-680, -40), (-820, 620)):
        m.place("life", "SM_Yacht", x, y, z=0.0, yaw=rnd.uniform(0, 360))
    for x, y, a in ((-2600, -900, 15), (-3400, 600, 190), (-2200, 1800, 20), (-4200, -2200, 200), (-1800, 3400, 160)):
        m.place("life", "SM_CargoShip", x, y, z=0.0, yaw=a)
    # families on the beach: umbrellas, people, kiosks and benches on the promenade
    m.scatter("life", "SM_BeachUmbrella", 90, (-520, -300, -950, 950), clearance=4, seed=31, max_slope=0.3, min_spacing=9,
              mask=lambda x, y: 6 < x - float(coast_x(np.array(y))) < 40, yaw=None)
    m.scatter("life", ["SM_Person_Thobe", "SM_Person_Abaya", "SM_Person_Casual", "SM_Person_Kid"], 160,
              (-520, -300, -950, 950), clearance=2.5, seed=32, max_slope=0.3, min_spacing=1.5,
              mask=lambda x, y: 2 < x - float(coast_x(np.array(y))) < 45, scale=(0.95, 1.05))
    s_corn = T.nearest_s((-410, 690))
    m.along(T, "life", "SM_Bench", 30, 3.2, s0=15, s1=s_corn, side=(1,), min_clear=2.2, yaw_add=180)
    m.along(T, "life", "SM_LampClassic", 30, 3.4, s0=30, s1=s_corn, side=(1,), min_clear=2.2)
    m.along(T, "life", "SM_Kiosk", 170, 9.0, s0=80, s1=s_corn, side=(-1,), min_clear=6)
    m.along(T, "life", ["SM_Person_Thobe", "SM_Person_Abaya", "SM_Person_Casual", "SM_Person_Kid"], 9, 4.5, s0=10,
            s1=s_corn, side=(1, -1), jitter=1.5, min_clear=2.0, seed=33)
    # people in the Al-Balad lanes (on the edges, under the awnings)
    s_old0, s_old1 = T.nearest_s((160, 560)), T.nearest_s((40, -420))
    m.along(T, "life", ["SM_Person_Thobe", "SM_Person_Abaya", "SM_Person_Casual", "SM_Person_Kid"], 13, 0.6, s0=s_old0 + 20,
            s1=s_old1, side=(1, -1), jitter=0.3, min_clear=0.4, seed=34)
    # modern city: mosques, traffic, a water tower
    m.place("life", "SM_Mosque_Dome", 300, 820, yaw=12)
    m.place("life", "SM_WaterTower", 860, -760)
    cars = ["SM_Car_Sedan_White", "SM_Car_Sedan_Silver", "SM_Car_Sedan_Red", "SM_Car_SUV_White", "SM_Car_SUV_Black",
            "SM_Car_Pickup_White", "SM_Bus_City"]
    m.scatter("life", cars, 60, (450, 980, -950, 950), clearance=6, seed=35, max_slope=0.15, min_spacing=5)
    for k in range(8):
        m.place("life", "SM_Seagulls", float(coast_x(np.array(0.0))) - rnd.uniform(-20, 200), rnd.uniform(-900, 900),
                z=rnd.uniform(15, 45), yaw=rnd.uniform(0, 360), scale=1.4)


def build(render=True, layout_only=False):
    sr.reset()
    t = make_terrain()
    tm = terrain_material(f"{NAME}_Terrain", ["Sand", "CoralStone", "Concrete", "Sand"], [6, 4, 3, 6],
                          [(1.05, 1.0, 0.95), (0.9, 0.88, 0.82), (0.98, 0.95, 0.9), (0.7, 0.62, 0.52)])
    m = MapBuild(NAME, TITLE, t, tm, water=WATER)
    m.set_backdrop(far_height, far_paint, blend=500)
    m.far_detail.append(far_city)
    main, shorts = tracks()
    m.set_tracks(main, shorts)
    m.build_tracks(carve_layer=2, falloff=14)
    if layout_only:
        trk.minimap("/tmp/claude-0/jeddah_layout.png", t, main, shorts, TITLE, WATER)
        return m
    props = map_props()
    dress(m)
    m.export()
    m.write_gameplay(pickups=(500, 1500, 2600, 3600), boosts=(150, 1250, 2300, 3300))
    sr.write_manifest()
    if render:
        previews(m, props)
    return m


def lighting():
    sr.world_sky(3.5, 265, 0.26)
    sr.sun((86.5, 0, 265), 3.8, (1.0, 0.6, 0.35), 1.0)


def previews(m, props):
    from mapkit import render_previews
    kits = kit_objects("jeddah", "riyadh", "common", "alula", "life") + props
    m.preview_scene(kits)
    T = m.main
    s_mosque = T.nearest_s((-410, 236))
    s_old = T.nearest_s((170, 440))
    cars = [("JeddahGT", s_mosque + 18, -2.5, None), ("Falcon", s_mosque + 34, 3.0, None),
            ("RiyadhMuscle", s_old + 15, 0.0, None), ("AlUlaRally", 72, 0.0, m.shortcuts[1])]
    shots = [("overview", (-1300, -1100, 600), (100, 100, 0), 30),
             ("chase", s_mosque, dict(back=12, height=3.0, ahead=60, lens=28)),
             ("overview", (-385, 95, 9), (-600, 260, 12), 32),
             ("chase", s_old, dict(back=11, height=3.0, ahead=40, lens=28)),
             ("chase", 62, dict(back=9, height=2.3, ahead=45, lens=24, track=m.shortcuts[1])),
             ("side", -30, dict(side=1, off=15, height=6.5, ahead=80, lens=26))]
    render_previews(m, shots, lighting, cars)


if __name__ == "__main__":
    build(layout_only="--layout" in sys.argv)
