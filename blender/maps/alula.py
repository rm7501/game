"""ALULA - 'Hegra Canyon Rally'.

Concept (reference photos): a golden sand valley winding between towering, honeycomb-eroded sandstone
massifs; landmarks sit IN the landscape - Maraya reflecting the canyon, Qasr al-Farid alone on the
open plain, Hegra tombs carved into a cliff face, a land-art sand labyrinth with a palm in its centre,
and Elephant Rock lit by lanterns at dusk.

Main circuit (~4.3 km, packed-sand rally road):
  Maraya plaza (start) -> open plain past Qasr al-Farid -> under the Rainbow Rock arch ->
  the Grand Canyon S-bends between cliffs -> around the sand labyrinth -> Hegra tomb cliff ->
  around a giant dune -> the Elephant Rock lantern lounge -> southern plain back to Maraya.
Shortcuts:
  ElephantArch (hidden)  straight through the trunk arch of Elephant Rock
  SlotCanyon   (hidden)  a 7 m crack through a whole massif, behind a boulder
  LabyrinthRun (visible) straight across the sand spiral (bumpy ridges)
  DuneJump     (visible) over the crest of the big dune instead of around it
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
from track import CP, Track, catmull_rom  # noqa: E402
from terrain import Terrain, Noise, smoothstep, terrain_material, dist_to_polyline  # noqa: E402
from mapkit import MapBuild, kit_objects  # noqa: E402

NAME = "AlUla"
TITLE = "AlUla - Hegra Canyon Rally"
ELEPHANT = (-40.0, -640.0, 25.0)        # x, y, yaw of Elephant Rock
LABY = (-420.0, 360.0)                  # sand labyrinth centre
DUNE = (-330.0, -300.0)                 # giant dune


def tracks():
    B, K, N = "berm", "rock", "none"
    main = [
        CP(640, -260, 15, surf="sand", L=B, R=B, tags={"curbs"}),           # start: Maraya plaza
        CP(645, -40, 15),
        CP(610, 220, 15),
        CP(560, 430, 14, bank=-6),
        CP(440, 560, 13, bank=-4, L=K, R=K),                                # Rainbow Rock gate -> canyon
        CP(290, 590, 12),
        CP(170, 500, 12, bank=6),
        CP(40, 560, 12, bank=-6),
        CP(-90, 500, 12, bank=6),
        CP(-210, 560, 12),
        CP(-300, 470, 13, L=B, R=B),
        CP(-360, 420, 13, bank=6),                                          # around the labyrinth
        CP(-420, 440, 13, bank=6),
        CP(-480, 400, 13, bank=6),
        CP(-490, 320, 13, bank=6),
        CP(-470, 230, 13),
        CP(-520, 110, 13, L=K, R=B),                                        # Hegra tomb cliff
        CP(-500, -40, 13),
        CP(-430, -150, 14, L=B, R=B),
        CP(-420, -260, 14, bank=-5),                                        # around the giant dune
        CP(-350, -400, 14, bank=-6),
        CP(-230, -430, 14),
        CP(-170, -560, 13, bank=6),                                         # Elephant Rock lounge
        CP(-110, -700, 13, bank=6),
        CP(20, -740, 13, bank=6),
        CP(100, -660, 13),
        CP(200, -560, 14),
        CP(380, -520, 15),
        CP(560, -460, 15, bank=-5),
    ]
    main_t = Track("Track", main, closed=True, surf="sand", L=B, R=B)
    ex, ey, eyaw = ELEPHANT
    c, s_ = math.cos(math.radians(eyaw)), math.sin(math.radians(eyaw))
    ax, ay = ex + 23 * c, ey + 23 * s_                                       # middle of the trunk arch
    dxa, dya = -s_, c                                                       # arch axis (local +Y)
    s_arch = Track("Shortcut_ElephantArch", [
        CP(-170, -560, 9, surf="sand", L=N, R=N), CP(ax + dxa * 45, ay + dya * 45, 8), CP(ax, ay, 7),
        CP(ax - dxa * 45, ay - dya * 45, 8), CP(100, -660, 9)], closed=False, label="Elephant Rock arch", hidden=True)
    s_slot = Track("Shortcut_SlotCanyon", [
        CP(290, 590, 8, surf="sand", L=N, R=N), CP(180, 632, 7), CP(40, 642, 7), CP(-100, 628, 7), CP(-210, 560, 8)],
        closed=False, label="Slot canyon", hidden=True)
    lx, ly = LABY
    s_lab = Track("Shortcut_LabyrinthRun", [
        CP(-360, 420, 9, surf="sand", L=N, R=N), CP(lx + 25, ly + 10, 9, dz=0.5), CP(lx, ly, 9, dz=-0.2),
        CP(lx - 20, ly - 15, 9, dz=0.5), CP(-470, 230, 9)], closed=False, label="Labyrinth run", hidden=False)
    dx_, dy_ = DUNE
    s_dune = Track("Shortcut_DuneJump", [
        CP(-430, -150, 9, surf="sand", L=N, R=N), CP(dx_ - 20, dy_ + 60, 9, dz=4), CP(dx_, dy_, 9, dz=9, tags={"gap"}),
        CP(dx_ + 25, dy_ - 45, 9, dz=2), CP(-230, -430, 9)], closed=False, label="Dune jump", hidden=False)
    return main_t, [s_arch, s_slot, s_lab, s_dune]


def massif_field(X, Y):
    """Sandstone massif mask (0..1), massif top height and sand undulation for any coordinates."""
    nz = Noise(23)
    wx = (nz.fbm(X, Y, 400, 3) - 0.5) * 260
    wy = (nz.fbm(X + 900, Y, 400, 3) - 0.5) * 260
    m = nz.fbm(X + wx, Y + wy, 330, 4)
    jag = (nz.ridged(X, Y, 26, 3) - 0.5) * 0.035                             # fluted, jagged cliff outlines
    mask = smoothstep(0.5, 0.56, m + jag)
    top = 48 + 38 * nz.fbm(X, Y, 160, 4) + 14 * (nz.ridged(X, Y, 60, 3) - 0.5)
    sand = 1.5 * (nz.fbm(X, Y, 120, 4) - 0.5) + 2.5 * (nz.ridged(X + 50, Y, 70, 3) ** 3)
    return mask, top, sand, jag


def far_height(X, Y):
    mask, top, sand, jag = massif_field(X, Y)
    r = np.hypot(X, Y)
    nz = Noise(24)
    # the horizon: bigger table mountains and the dark basalt of Harrat Uwayrid to the west
    far_w = smoothstep(3000, 6500, r)
    wx = (nz.fbm(X, Y, 1500, 3) - 0.5) * 900
    wy = (nz.fbm(X + 700, Y, 1500, 3) - 0.5) * 900
    big = smoothstep(0.5, 0.56, nz.fbm((X + wx) * 0.8 - (Y + wy) * 0.6, (X + wx) * 0.6 + (Y + wy) * 0.8, 1300, 4)) * far_w
    mask = mask * (1 - far_w)
    top = top * (1 + 1.2 * smoothstep(2500, 9000, r))
    harrat = smoothstep(-3500, -6500, X) * (90 + 40 * nz.fbm(X, Y, 500, 3))
    dunes = 6 * nz.ridged(X * 0.6, Y * 1.4, 220, 3) ** 2
    h = sand + dunes + np.maximum(mask, big) * top
    apron = smoothstep(0.0, 0.25, mask) * (1 - smoothstep(0.25, 0.6, mask))
    return np.maximum(h + apron * 4, harrat)


def far_paint(X, Y, H, slope, d):
    mask, top, sand, jag = massif_field(X, Y)
    w = np.zeros((4,) + X.shape)
    w[1] = smoothstep(0.55, 0.9, slope)
    w[3] = smoothstep(0.25, 0.5, slope) * (1 - w[1]) * smoothstep(-3500, -6000, X) + \
        smoothstep(0.0, 0.25, mask) * (1 - smoothstep(0.25, 0.6, mask)) * 0.6
    w[2] = smoothstep(0.55, 0.7, Noise(25).fbm(X, Y, 90, 3)) * 0.5 * (1 - w[1])
    w[0] = np.clip(1 - w[1] - w[2] - w[3], 0, 1)
    return w


def far_detail(m):
    """Palm oases in the valleys, scattered acacias, distant old-town clusters (merged chunks)."""
    from backdrop import Merged, scatter_points, outside
    B = m.backdrop
    rnd = random.Random(41)
    palm_t = sr.mat("Far_PalmTrunk", (0.3, 0.22, 0.15), rough=0.9)
    palm_f = sr.mat("Far_PalmFrond", (0.16, 0.24, 0.08), rough=0.8, kind="foliage")
    acacia = sr.mat("Far_AcaciaCrown", (0.22, 0.26, 0.1), rough=0.9, kind="foliage")
    mud = sr.mat("MudBrick", (1.0, 0.95, 0.9), tex="MudPlaster", tile=3.0)
    mg = Merged(f"SM_{NAME}_Far_Oasis")

    def flat(x, y):
        return outside(x, y, pad=50) and float(B.slope(np.array([x]), np.array([y]))[0]) < 0.12 and math.hypot(x, y) < 6000
    centres = scatter_points(rnd, 14, flat, (-6000, 6000, -6000, 6000))
    for cx, cy in centres:
        for k in range(rnd.randint(40, 110)):
            x, y = cx + rnd.gauss(0, 90), cy + rnd.gauss(0, 90)
            if not outside(x, y, pad=30):
                continue
            z = float(B.height(np.array([x]), np.array([y]))[0])
            mg.palm(x, y, z, rnd.uniform(7, 11), palm_t, palm_f, rnd)
        if rnd.random() < 0.5:                  # a mud-brick hamlet next to some oases
            for k in range(rnd.randint(8, 20)):
                x, y = cx + rnd.gauss(0, 60) + 140, cy + rnd.gauss(0, 60)
                if not outside(x, y, pad=30):
                    continue
                z = float(B.height(np.array([x]), np.array([y]))[0])
                mg.block(x, y, z, rnd.uniform(6, 12), rnd.uniform(6, 12), rnd.uniform(4, 9), rnd.uniform(0, 90), mud)
    for x, y in scatter_points(rnd, 1400, flat, (-6000, 6000, -6000, 6000)):
        z = float(B.height(np.array([x]), np.array([y]))[0])
        mg.tree(x, y, z, rnd.uniform(4, 7), acacia, palm_t, kind="round")
    return mg.objects()


def make_terrain(main, shorts):
    t = Terrain(layers=("Sand", "Sandstone", "PackedSand", "Scree"))
    X, Y = t.X, t.Y
    nz = Noise(23)
    mask, top, sand, jag = massif_field(X, Y)
    # designed massifs: north block (the slot canyon cracks through it), south canyon wall, Hegra cliff
    for (cx, cy, rx, ry) in ((40, 700, 360, 150), (60, 400, 300, 75), (-660, -20, 110, 230), (-180, -170, 160, 120)):
        e = ((X - cx) / rx) ** 2 + ((Y - cy) / ry) ** 2
        mask = np.maximum(mask, smoothstep(1.0, 0.75, e + jag * 4))
    # keep the race lines clear: canyon walls 26-60 m from the main line, slot walls 4-9 m
    dense, _ = catmull_rom([c["p"] for c in main.cps], True, per_seg=12)
    d_main = dist_to_polyline(X, Y, np.vstack([dense, dense[:1]]))
    clear = smoothstep(19, 44, d_main)
    for sc in shorts:
        pts = np.array([c["p"] for c in sc.cps])
        dpts, _ = catmull_rom(pts, False, per_seg=10)
        ds = dist_to_polyline(X, Y, dpts)
        lo, hi = (4.0, 9.0) if sc.name.endswith("SlotCanyon") else (14.0, 30.0)
        clear = np.minimum(clear, smoothstep(lo, hi, ds))
    # open plazas: Maraya, Qasr al-Farid plain, labyrinth, dune field, Elephant Rock lounge
    for (cx, cy, r) in ((650, -150, 260), (430, 150, 300), (LABY[0], LABY[1], 130), (DUNE[0], DUNE[1], 160),
                        (ELEPHANT[0], ELEPHANT[1], 170), (300, -500, 220)):
        clear *= smoothstep(r * 0.7, r, np.hypot(X - cx, Y - cy))
    mask *= clear
    dune = 22 * np.exp(-(((X - DUNE[0]) / 70) ** 2 + ((Y - DUNE[1]) / 50) ** 2))
    labyrinth_floor = -0.6 * np.exp(-(np.hypot(X - LABY[0], Y - LABY[1]) / 70) ** 4)
    t.h = sand + dune + labyrinth_floor + mask * top
    # scree aprons at cliff feet
    apron = smoothstep(0.0, 0.25, mask) * (1 - smoothstep(0.25, 0.6, mask))
    t.h += apron * 4
    slope = t.slope()
    t.set_layer(1, smoothstep(0.55, 0.9, slope) * smoothstep(0.05, 0.2, mask))
    t.set_layer(3, apron * smoothstep(0.2, 0.5, slope))
    t.set_layer(2, smoothstep(0.55, 0.7, nz.fbm(X, Y, 50, 3)) * 0.6 * (1 - mask))
    return t


def sand_labyrinth(name="SM_SandLabyrinth"):
    """Land-art spiral: low raked sand ridges + stone border (palm placed separately)."""
    ridge = sr.mat("LabyrinthSand", (0.95, 0.86, 0.72), rough=0.95, tex="Sand", tile=4)
    mb = sr.MB(name)
    turns = 5
    pts = []
    for k in range(turns * 64):
        a = 2 * math.pi * k / 64
        r = 6 + 8.5 * a / (2 * math.pi)
        pts.append((r * math.cos(a), r * math.sin(a), 0.05))
    mb.tube(pts, 0.45, ridge, seg=6)
    for k in range(48):
        a = 2 * math.pi * k / 48
        mb.sphere(0.5, (54 * math.cos(a), 54 * math.sin(a), 0.1), m=ridge, seg=6, rings=4, scale=(1, 1, 0.5))
    o = mb.to_object(sharp_angle=None)
    for v in o.data.vertices:          # flatten the bottom half of the tubes into the sand
        if v.co.z < 0.05:
            v.co.z = 0.02
    return o


def sand_lantern(name="SM_SandLantern"):
    """Paper-bag / glass lantern on the sand (Elephant Rock lounge)."""
    glow = sr.mat("LanternGlowWarm", (1.0, 0.75, 0.4), emit=(1.0, 0.68, 0.32), emit_str=9, kind="emissive")
    base = sr.mat("LanternBase", (0.25, 0.2, 0.15), rough=0.8)
    mb = sr.MB(name)
    mb.cyl(0.2, 0.05, (0, 0, 0.025), m=base, seg=12)
    mb.lathe([(0.17, 0.05), (0.19, 0.25), (0.17, 0.45), (0.0, 0.47)], seg=12, m=glow)
    return mb.to_object(origin="base", sharp_angle=None)


def lounge_seat(name="SM_LoungeSeat"):
    rug = sr.mat("Rug_Red", (0.5, 0.08, 0.06), rough=0.9)
    cush = sr.mat("Cushion_Cream", (0.85, 0.78, 0.64), rough=0.85)
    mb = sr.MB(name)
    mb.box((3.0, 2.0, 0.05), (0, 0, 0.025), m=rug)
    for k in range(3):
        mb.box((0.8, 0.6, 0.3), (-1.0 + k, 0.65, 0.2), m=cush, bevel=0.1, seg=2)
    mb.box((1.0, 0.6, 0.35), (0, -0.2, 0.18), m=sr.mat("LowTable", (0.3, 0.2, 0.12), rough=0.6))
    return mb.to_object(origin="base", sharp_angle=None)


def map_props():
    objs = [sand_labyrinth(), sand_lantern(), lounge_seat()]
    folder = os.path.join(sr.ROOT, "assets", "maps", NAME, "props")
    sr.export_kit(objs, os.path.relpath(folder, os.path.join(sr.ROOT, "assets")), blend=False)
    return objs


def dress(m: MapBuild):
    T = m.main
    p, t, n, w, b = T.frame(0)
    m.place("common", "SM_StartGantry", p[0], p[1], yaw=math.degrees(math.atan2(t[1], t[0])) + 90)
    m.place("alula", "SM_Maraya", 760, -140, yaw=90)                        # mirrors the start grid
    m.place("alula", "SM_QasrAlFarid", 470, 150, yaw=-50)
    pr, tr, nr, wr, br = T.frame(T.nearest_s((480, 545)))
    m.place("alula", "SM_RainbowRock", pr[0], pr[1], yaw=math.degrees(math.atan2(tr[1], tr[0])) + 90)
    m.place("alula", "SM_HegraTombCliff", -585, 60, yaw=-95)
    m.place("alula", "SM_HegraTombCliff", -600, -110, yaw=-80, scale=0.9)
    ex, ey, eyaw = ELEPHANT
    m.place("alula", "SM_ElephantRock", ex, ey, yaw=eyaw)
    lx, ly = LABY
    m.place(f"maps/{NAME}/props", "SM_SandLabyrinth", lx, ly)
    m.place("common", "SM_DatePalm_C", lx, ly)
    # lantern lounge around Elephant Rock
    import random
    rnd = random.Random(5)
    for k in range(70):
        a = rnd.uniform(0, 2 * math.pi)
        r = rnd.uniform(45, 110)
        x, y = ex + r * math.cos(a), ey + r * math.sin(a)
        if m.clearance(x, y) > 3:
            m.place(f"maps/{NAME}/props", "SM_SandLantern", x, y)
    for k in range(10):
        a = rnd.uniform(0, 2 * math.pi)
        r = rnd.uniform(55, 100)
        x, y = ex + r * math.cos(a), ey + r * math.sin(a)
        if m.clearance(x, y) > 6:
            m.place(f"maps/{NAME}/props", "SM_LoungeSeat", x, y, yaw=math.degrees(a) + 90)
    # hoodoos, boulders, acacia and palm oasis on the plains
    m.scatter("alula", ["SM_RockPillar_A", "SM_RockPillar_B"], 26, (-950, 950, -950, 950), clearance=30, seed=3,
              max_slope=0.25, min_spacing=90, scale=(0.7, 1.3))
    m.scatter("alula", ["SM_Boulder_A", "SM_Boulder_B"], 220, (-950, 950, -950, 950), clearance=12,
              seed=4, max_slope=0.6, scale=(0.4, 1.0), sink=0.4)
    m.scatter("alula", "SM_Boulder_C", 40, (-950, 950, -950, 950), clearance=35, seed=14, max_slope=0.6,
              scale=(0.8, 1.4), sink=0.8)
    m.scatter("common", "SM_Acacia", 160, (-950, 950, -950, 950), clearance=10, seed=5, max_slope=0.2, min_spacing=12)
    m.scatter("common", ["SM_DatePalm_A", "SM_DatePalm_C"], 140, (150, 650, 650, 950), clearance=8, seed=6,
              max_slope=0.2, min_spacing=7)
    m.place("alula", "SM_AlUlaOldTown", 380, 820, yaw=-20)
    for k, (x, y, z) in enumerate(((300, 0, 150), (-200, 200, 190), (100, -300, 170), (-500, -500, 210), (650, 600, 160))):
        m.place("alula", f"SM_HotAirBalloon_{'ABC'[k % 3]}", x, y, z=z, yaw=k * 70)
    # the slot canyon is hidden behind a boulder pile
    sp = m.shortcuts[1].frame(14)[0]
    for k in range(3):
        m.place("alula", "SM_Boulder_C", sp[0] + 6 + k * 3, sp[1] - 9 + k * 4, scale=0.7)
    life(m)


def life(m: MapBuild):
    """Rally day in AlUla: spectator zones, Bedouin camps with camels, caravans crossing the plain,
    goats by the old town, visitors at Elephant Rock and the labyrinth."""
    import dressing as D
    rnd = random.Random(23)
    T = m.main
    D.trackside(m, spots=[T.nearest_s((480, 545)), T.nearest_s((-420, -260))])
    cars = ["SM_Car_SUV_White", "SM_Car_SUV_Black", "SM_Car_Pickup_White"]
    for k, (cx, cy) in enumerate(((380, -40), (180, -470), (-230, -420), (560, 680), (-700, 520))):
        D.cluster(m, "life", "SM_BedouinTent", cx, cy, 1, 15, seed=100 + k, clearance=25, max_slope=0.2)
        D.cluster(m, "life", "SM_Campfire", cx, cy, 1, 18, seed=110 + k, clearance=25, max_slope=0.2)
        D.cluster(m, "life", "SM_Camel_Sitting", cx, cy, rnd.randint(3, 5), 30, seed=120 + k, clearance=22, max_slope=0.25)
        D.cluster(m, "life", "SM_Camel", cx, cy, rnd.randint(2, 4), 45, seed=130 + k, clearance=22, max_slope=0.25)
        D.cluster(m, "life", cars, cx, cy, 2, 35, seed=140 + k, clearance=20, max_slope=0.2, min_spacing=5)
        D.people(m, cx, cy, 6, 20, seed=150 + k, clearance=20, kinds=("SM_Person_Thobe", "SM_Person_Kid"))
    # camel caravans walking across the open plains
    for k, (x0, y0, a) in enumerate(((430, 260, 30), (120, -640, 160), (-560, -620, 80))):
        for j in range(7):
            x = x0 + j * 4.2 * math.cos(math.radians(a))
            y = y0 + j * 4.2 * math.sin(math.radians(a))
            if m.clearance(x, y) > 12:
                m.place("life", "SM_Camel", x, y, yaw=a + 180 + rnd.uniform(-6, 6))
        m.place("life", "SM_Person_Thobe", x0 - 3 * math.cos(math.radians(a)), y0 - 3 * math.sin(math.radians(a)), yaw=a + 180)
    D.cluster(m, "life", ["SM_Goat", "SM_Goat_Brown", "SM_Sheep"], 330, 760, 24, 60, seed=160, clearance=15)
    D.people(m, ELEPHANT[0], ELEPHANT[1], 34, 100, seed=161, clearance=4)
    D.people(m, LABY[0], LABY[1], 16, 70, seed=162, clearance=4)
    D.people(m, 760, -140, 20, 60, seed=163, clearance=6)               # at Maraya
    m.scatter("life", ["SM_Shrub_A", "SM_Shrub_B"], 260, (-950, 950, -950, 950), clearance=5, seed=164, max_slope=0.25,
              min_spacing=6, scale=(0.6, 1.2))
    for k in range(4):
        m.place("life", "SM_BirdFlock", rnd.uniform(-600, 600), rnd.uniform(-600, 600), z=rnd.uniform(60, 120),
                yaw=rnd.uniform(0, 360), scale=1.6)


def build(render=True, layout_only=False):
    sr.reset()
    main, shorts = tracks()
    t = make_terrain(main, shorts)
    tm = terrain_material(f"{NAME}_Terrain", ["Sand", "SandstoneStrata", "TrackSand", "Rock"], [6, 16, 8, 5],
                          [(1, 1, 1), (1.0, 0.95, 0.92), (0.95, 0.85, 0.75), (0.95, 0.7, 0.55)])
    m = MapBuild(NAME, TITLE, t, tm)
    m.set_backdrop(far_height, far_paint, blend=500)
    m.far_detail.append(far_detail)
    m.set_tracks(main, shorts)
    m.build_tracks(carve_layer=2, falloff=14)
    if layout_only:
        trk.minimap("/tmp/claude-0/alula_layout.png", t, main, shorts, TITLE)
        return m
    props = map_props()
    dress(m)
    m.export()
    m.write_gameplay(pickups=(500, 1600, 2700, 3700), boosts=(150, 1200, 2300, 3400))
    sr.write_manifest()
    if render:
        previews(m, props)
    return m


def lighting():
    sr.world_sky(6, 250, 0.24)
    sr.sun((84, 0, 250), 5.0, (1.0, 0.68, 0.42), 1.2)


def previews(m, props):
    from mapkit import render_previews
    kits = kit_objects("alula", "common", "life") + props
    m.preview_scene(kits)
    cars = [("AlUlaRally", 120, -2.5, None), ("DuneFox", 140, 3.0, None), ("NajdiGXR", 1060, 0.0, None),
            ("HiluxRaider", 3150, 2.0, None)]
    shots = [("overview", (1200, -1350, 820), (-80, 60, 0), 30),
             ("chase", 100, dict(back=12, height=3.0, ahead=60, lens=28)),
             ("chase", 1040, dict(back=12, height=3.5, ahead=60, lens=28)),
             ("chase", 3130, dict(back=12, height=3.5, ahead=70, lens=28)),
             ("chase", 40, dict(back=14, height=4.0, ahead=70, lens=26, track=m.shortcuts[0]))]
    render_previews(m, shots, lighting, cars)


if __name__ == "__main__":
    build(layout_only="--layout" in sys.argv)
