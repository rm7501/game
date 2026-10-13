"""RIYADH NIGHTS - 'Olaya Interchange to Wadi Hanifa'.

Concept (from the reference photos): golden-hour/night Riyadh is a flat desert city of highways,
flyovers with loop ramps and the elevated Metro, with the KAFD and Kingdom Centre skyline rising out of
it. The track uses that multi-level road network, then drops off the Tuwaiq limestone escarpment
into the green Wadi Hanifa valley and climbs back through the mud-brick ruins of Diriyah.

Main circuit (~4 km, clockwise):
  King Fahd Road (start) -> flyover -> descending cloverleaf loop that passes UNDER the flyover ->
  KAFD chicane between towers -> escarpment descent with a hairpin -> Wadi Hanifa floor (palms, pond)
  -> climb out -> Diriyah ruins S-bends -> back onto King Fahd Road.
Shortcuts:
  StadiumCut    (visible)  straight across the stadium car park, inside the last corner
  MetroLeap     (hidden)   construction ramp onto the unfinished Metro viaduct, leap off its end
  PalmTrail     (hidden)   dirt trail through the palm grove cutting the wadi meander
  DiriyahBreach (hidden)   through a breach in the old mud wall, skipping the ruins S-bends
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

NAME = "RiyadhNights"
TITLE = "Riyadh Nights - Olaya Interchange to Wadi Hanifa"
WATER = 0.3
PL = 55.0          # city plateau height above the wadi floor (Tuwaiq escarpment)


def valley_center(y):
    return -620 + 70 * np.sin(y / 260.0) + 30 * np.sin(y / 97.0 + 1.0)


def field(X, Y, far=False):
    """Height field of the Riyadh landscape. far=True: the version used beyond the map edge
    (city plateau everywhere, Tuwaiq escarpment on the western horizon, dunes far to the east)."""
    nz = Noise(11)
    vc = valley_center(Y)
    dx = np.abs(X - vc)
    wall = smoothstep(95, 240, dx)
    # stepped limestone escarpment: quantise the wall into ledges
    raw = wall * PL
    q = np.floor(raw / 7.0)
    frac = raw / 7.0 - q
    ledges = (q + smoothstep(0.6, 1.0, frac)) * 7.0
    cliff = 0.65 * ledges + 0.35 * raw
    plateau_noise = (nz.fbm(X, Y, 180, 4) - 0.5) * 2.0
    floor = 2.2 + (nz.fbm(X, Y, 90, 4) - 0.5) * 1.2 - 1.2 * np.exp(-((X - vc) / 14.0) ** 2)    # dry stream bed
    h = floor * (1 - wall) + (cliff + plateau_noise * wall)
    # western desert plateau is higher and rougher
    west = smoothstep(0, 1, (vc - 240 - X) / 120)
    h += west * (6 + (nz.ridged(X, Y, 220, 4) - 0.4) * 10)
    east = smoothstep(780, 950, X)
    if far:
        # Tuwaiq escarpment: a stepped limestone wall on the western horizon
        tw = -5200 + 600 * (nz.fbm(X * 0.2, Y * 0.2, 400, 3) - 0.5)
        esc = smoothstep(tw + 300, tw - 300, X)
        h += esc * (110 + 40 * nz.ridged(X, Y, 700, 3))
        # open desert with red dunes far to the east
        east = smoothstep(7000, 9500, X)
    h += east * (nz.ridged(X + 300, Y, 140, 3) ** 2) * 9
    return h, wall, east


def make_terrain():
    t = Terrain(layers=("Sand", "Limestone", "WadiSoil", "Paving"))
    X, Y = t.X, t.Y
    nz = Noise(11)
    h, wall, east = field(X, Y)
    # the pond (Wadi Hanifa lake)
    pond = np.exp(-(((X - (-600)) / 60) ** 2 + ((Y - 360) / 42) ** 2))
    h -= pond * 4.0
    t.h = h
    t.water_level = WATER
    slope = t.slope()
    t.set_layer(1, smoothstep(0.25, 0.6, slope))
    t.set_layer(2, (1 - wall) * smoothstep(0.35, 0.6, nz.fbm(X, Y, 40, 3) + 0.15) * (1 - smoothstep(0.3, 0.6, slope)))
    city = smoothstep(-330, -260, X) * (1 - east)
    t.set_layer(3, city * smoothstep(0.45, 0.55, nz.fbm(X, Y, 25, 2) * 0.3 + 0.5))
    return t


def far_height(X, Y):
    return field(X, Y, far=True)[0]


def far_paint(X, Y, H, slope, d):
    nz = Noise(12)
    vc = valley_center(Y)
    floor = 1 - smoothstep(95, 200, np.abs(X - vc))
    w = np.zeros((4,) + X.shape)
    w[0] = 1
    w[1] = smoothstep(0.25, 0.6, slope)
    w[2] = floor * (1 - w[1])
    city = (1 - floor) * (1 - w[1]) * (1 - smoothstep(6000, 8000, X)) * (1 - smoothstep(-4500, -5200, X))
    w[3] = city * smoothstep(0.45, 0.55, nz.fbm(X, Y, 60, 2) * 0.3 + 0.5)
    w[0] = np.clip(1 - w[1] - w[2] - w[3], 0, 1)
    return w


def far_city(m):
    """Night-time Riyadh sprawling to the horizon: lit blocks, a tower corridor continuing King Fahd Road,
    glowing street grid, palms in the wadi. Merged into 4 chunk meshes."""
    from backdrop import Merged, scatter_points, outside
    B = m.backdrop
    rnd = random.Random(31)
    tower = sr.mat("Riyadh_FacadeNight", (1, 1, 1), rough=0.1, metal=0.6, tex="FacadeNight", tile=24.0, emit_str=2.0)
    homes = sr.mat("Far_NajdiNight", (1.0, 0.9, 0.75), rough=0.8, tex="FacadeNight", tile=16.0, emit_str=0.9)
    roof = sr.mat("Far_RoofDark", (0.16, 0.14, 0.13), rough=0.9)
    crown = sr.mat("LED_White", (0.9, 0.95, 1.0), emit=(0.85, 0.9, 1.0), emit_str=10, kind="emissive")
    street = sr.mat("Far_StreetGlow", (0.9, 0.45, 0.15), emit=(1.0, 0.5, 0.16), emit_str=2.2, kind="emissive")
    palm_t = sr.mat("Far_PalmTrunk", (0.3, 0.22, 0.15), rough=0.9)
    palm_f = sr.mat("Far_PalmFrond", (0.12, 0.2, 0.08), rough=0.8, kind="foliage")
    mg = Merged(f"SM_{NAME}_Far_City")
    mt = Merged(f"SM_{NAME}_Far_Towers")
    ms = Merged(f"SM_{NAME}_Far_Streets")

    def city_ok(x, y):
        vc = float(valley_center(np.array(y)))
        return outside(x, y, pad=60) and abs(x - vc) > 280 and x > -4700 and x < 6500 and math.hypot(x, y) < 7500
    pts = scatter_points(rnd, 4200, lambda x, y: city_ok(x, y) and rnd.random() < 2200 / max(math.hypot(x, y), 1100),
                         (-4700, 6500, -7500, 7500))
    zs = B.height(np.array([p[0] for p in pts]), np.array([p[1] for p in pts]))
    for (x, y), z in zip(pts, zs):
        w, d = rnd.uniform(18, 40), rnd.uniform(18, 40)
        h = rnd.choice((7, 9, 11, 14, 18, 24)) * rnd.uniform(0.9, 1.1)
        mg.block(x, y, float(z), w, d, h, rnd.choice((0, 0, 0, 90)) + rnd.uniform(-3, 3), homes, roof)
    # tower corridor along King Fahd Road (x ~ 320) running north and south to the horizon
    for k in range(260):
        y = rnd.choice((-1, 1)) * rnd.uniform(1150, 7000)
        x = 320 + rnd.choice((-1, 1)) * rnd.uniform(60, 230)
        z = float(B.height(np.array([x]), np.array([y]))[0])
        h = rnd.uniform(60, 220) * (1.25 if abs(y) < 3500 else 0.9)
        if rnd.random() < 0.3:
            mt.tower(x, y, z, rnd.uniform(14, 22), h, tower, crown, seg=rnd.choice((4, 6, 8)))
        else:
            mt.block(x, y, z, rnd.uniform(26, 40), rnd.uniform(26, 40), h, rnd.uniform(0, 90), tower, None, crown)
    # a second business cluster to the north-east (Olaya / Al Murooj) and one south (the old centre)
    for cx, cy, n in ((1900, 2600, 45), (1400, -2900, 30), (-2600, 3400, 25)):
        for k in range(n):
            x, y = cx + rnd.gauss(0, 260), cy + rnd.gauss(0, 260)
            z = float(B.height(np.array([x]), np.array([y]))[0])
            mt.block(x, y, z, rnd.uniform(24, 40), rnd.uniform(24, 40), rnd.uniform(50, 170), rnd.uniform(0, 90),
                     tower, None, crown)
    # glowing street grid on the plateau
    for g in np.arange(-7200, 7300, 180.0):
        for horiz in (True, False):
            seg_pts = []
            for u in np.arange(-7200, 7300, 60.0):
                x, y = (u, g) if horiz else (g, u)
                ok = city_ok(x, y)
                if ok:
                    seg_pts.append((x, y))
                if (not ok or u >= 7240) and len(seg_pts) > 1:
                    xs = np.array([p[0] for p in seg_pts])
                    ys = np.array([p[1] for p in seg_pts])
                    zz = B.height(xs, ys) + 0.4
                    mb = ms._mb(xs.mean(), ys.mean())
                    grid = []
                    for x, y, z in zip(xs, ys, zz):
                        nx, ny = (0, 1.4) if horiz else (1.4, 0)
                        grid.append([(x - nx, y - ny, z), (x + nx, y + ny, z)])
                    mb.strip([r[::-1] for r in grid] if horiz else grid, None, street, smooth=False, keep=False)
                    seg_pts = []
                elif not ok:
                    seg_pts = []
    # palm groves continuing along Wadi Hanifa
    for k in range(1600):
        y = rnd.uniform(-7000, 7000)
        if abs(y) < 1050:
            continue
        x = float(valley_center(np.array(y))) + rnd.gauss(0, 55)
        z = float(B.height(np.array([x]), np.array([y]))[0])
        mg.palm(x, y, z, rnd.uniform(7, 11), palm_t, palm_f, rnd)
    return mg.objects() + mt.objects() + ms.objects()


def tracks():
    J, G, W_, R_, N = "jersey", "guardrail", "wall", "railing", "none"
    loop_c = np.array([400.0, 520.0])

    def loop(a, z, bank=7, w=14):
        return CP(loop_c[0] + 70 * math.cos(math.radians(a)), loop_c[1] + 70 * math.sin(math.radians(a)), w, z=z, bank=bank)
    main = [
        CP(320, -360, 16, L=J, R=J, surf="asphalt", tags={"curbs"}),       # start / finish (King Fahd Rd)
        CP(320, -120, 16),
        CP(320, 140, 16),
        CP(322, 300, 15, z=PL + 12, deck="highway"),                       # flyover
        CP(330, 470, 14, z=PL + 14),
        loop(180, PL + 14), loop(135, PL + 13), loop(90, PL + 11), loop(45, PL + 9), loop(0, PL + 7),
        loop(-45, PL + 5), loop(-90, PL + 2.5, bank=5),
        CP(330, 452, 14, z=PL + 0.2, bank=0),                               # passes under the flyover
        CP(220, 455, 14),
        CP(140, 430, 13, tags={"curbs"}),                                   # KAFD chicane
        CP(70, 478, 13, tags={"curbs"}),
        CP(-10, 445, 13),
        CP(-120, 420, 14),
        CP(-250, 370, 13, L=G, R=G),                                        # escarpment edge
        CP(-345, 335, 12, bank=-4),
        CP(-430, 300, 12, bank=-6),                                         # descending the cliff road
        CP(-470, 255, 11, bank=-10, tags={"curbs"}),                        # hairpin
        CP(-430, 215, 11, bank=-6),
        CP(-470, 160, 12, surf="asphalt_old", L="rock", R="rock"),
        CP(-560, 80, 13, L=N, R=N),                                         # wadi floor
        CP(-600, -30, 13),
        CP(-575, -150, 13, bank=5),                                         # wadi meander
        CP(-755, -285, 13, bank=-6),
        CP(-610, -420, 13, tags={"curbs"}),
        CP(-520, -520, 12, L=G, R=G),                                       # climb out
        CP(-400, -575, 12),
        CP(-280, -610, 12, surf="cobble", L=W_, R=W_),                     # Diriyah ruins
        CP(-200, -560, 10, tags={"curbs"}),
        CP(-120, -625, 10, tags={"curbs"}),
        CP(-40, -570, 10, tags={"curbs"}),
        CP(60, -620, 12, surf="asphalt", L=J, R=J),
        CP(200, -630, 14),
        CP(300, -560, 15, bank=6),
    ]
    main_t = Track("Track", main, closed=True, surf="asphalt", L=J, R=J)
    s_jump = Track("Shortcut_StadiumCut", [
        CP(140, -628, 11, surf="asphalt_old", L=N, R=N), CP(205, -560, 11, tags={"curbs"}), CP(265, -495, 11),
        CP(318, -425, 12)], closed=False, label="Stadium car-park cut", hidden=False)
    # unfinished Metro viaduct: ride the deck to where it stops at the cliff edge and leap into the wadi
    s_metro = Track("Shortcut_MetroLeap", [
        CP(40, 463, 8, L=N, R=N, surf="metal"), CP(0, 410, 8, z=PL + 7, deck="metro", tags={"nocarve"}),
        CP(-140, 340, 8, z=PL + 8), CP(-300, 302, 8, z=PL + 7, tags={"gap"}), CP(-362, 270, 9, z=PL - 6),
        CP(-418, 224, 11, deck="highway", surf="asphalt_old")], closed=False, label="Metro leap", hidden=True)
    s_palm = Track("Shortcut_PalmTrail", [
        CP(-602, -40, 7, surf="dirt", L=N, R=N), CP(-636, -150, 7), CP(-668, -255, 7), CP(-700, -338, 7)],
        closed=False, label="Palm grove trail", hidden=True)
    s_dir = Track("Shortcut_DiriyahBreach", [
        CP(-262, -600, 6, surf="cobble", L=W_, R=W_), CP(-180, -600, 6), CP(-90, -600, 6), CP(-20, -592, 6),
        CP(40, -612, 7)], closed=False, label="Diriyah wall breach", hidden=True)
    return main_t, [s_jump, s_metro, s_palm, s_dir]


def dress(m: MapBuild):
    T = m.main
    # start / finish
    p, t, n, w, b = T.frame(0)
    yaw = math.degrees(math.atan2(t[1], t[0]))
    m.place("common", "SM_StartGantry", p[0], p[1], yaw=yaw + 90)
    # King Fahd Road furniture
    m.along(T, "riyadh", "SM_StreetLight_KFR", 40, 3.0, s0=10, s1=560, face_road=True)
    m.along(T, "common", ["SM_DatePalm_A", "SM_DatePalm_B"], 22, 9.0, s0=0, s1=560, jitter=2)
    m.along(T, "common", ["SM_DatePalm_A", "SM_DatePalm_B"], 22, 9.0, s0=T.length - 260, s1=T.length, jitter=2)
    pg, tg, ng, wg, bg = T.frame(230)
    m.place("riyadh", "SM_Gantry_KFR", pg[0], pg[1], yaw=math.degrees(math.atan2(tg[1], tg[0])) + 90)
    # skyline landmarks (broad face of Kingdom Centre towards the road)
    m.place("riyadh", "SM_KingdomCentre", 560, -160, yaw=90)
    m.place("riyadh", "SM_KingdomMall", 560, -160, yaw=90)
    m.place("riyadh", "SM_AlFaisaliah", 540, 250, yaw=15)
    m.place("riyadh", "SM_RiyadhTVTower", 760, -620)
    for asset, x, y in (("SM_PIFTower", 110, 640), ("SM_KAFD_Twist", 10, 560), ("SM_KAFD_Slant", 200, 560),
                        ("SM_KAFD_Diagrid", -90, 600), ("SM_KAFD_Stepped", 230, 700), ("SM_KAFD_Twist", 40, 360),
                        ("SM_KAFD_Slant", 140, 350)):
        m.place("riyadh", asset, x, y, yaw=20)
    for k, y in enumerate(range(-560, 260, 70)):          # tower canyon lining King Fahd Road
        for sx in (1, -1):
            x = 320 + sx * (70 + (k % 3) * 18)
            if sx > 0 and -260 < y < 60:
                continue                                    # Kingdom Centre plaza
            m.place("riyadh", ("SM_KAFD_Twist", "SM_KAFD_Slant", "SM_KAFD_Stepped", "SM_KAFD_Diagrid")[(k + (sx > 0)) % 4],
                    x, y, yaw=(k * 37) % 90, scale=0.42 + 0.12 * ((k * 7 + (sx > 0) * 3) % 4))
    m.place("riyadh", "SM_Billboard_LED", 360, -40, yaw=-90)
    m.place("riyadh", "SM_Billboard_LED", 250, 520, yaw=180)
    # city fabric on the plateau: a street grid with lit streets, blocks, villas, shops, mosques, car parks
    city(m)
    # Wadi Hanifa: palm groves, acacias, boulders, the lake
    vmask = lambda x, y: abs(x - valley_center(y)) < 110  # noqa: E731
    m.scatter("common", ["SM_DatePalm_A", "SM_DatePalm_B", "SM_DatePalm_C"], 700, (-900, -300, -950, 950),
              clearance=3.5, seed=7, mask=vmask, min_spacing=5, max_slope=0.3)
    m.scatter("common", "SM_Acacia", 50, (-1000, -250, -950, 950), clearance=6, seed=8,
              mask=lambda x, y: 100 < abs(x - valley_center(y)) < 400, max_slope=0.35)
    m.scatter("alula", ["SM_Boulder_A", "SM_Boulder_B"], 70, (-950, -250, -950, 950), clearance=14, seed=9,
              mask=lambda x, y: 100 < abs(x - valley_center(y)) < 260, max_slope=2.0, sink=0.6, scale=(0.4, 0.8))
    # Diriyah (At-Turaif): mud-brick fort walls + old houses around the cobbled S-bends
    m.place("riyadh", "SM_Masmak", -140, -690, yaw=8)
    m.place("alula", "SM_AlUlaOldTown", -210, -520, yaw=-12)
    m.place("alula", "SM_AlUlaOldTown", -60, -515, yaw=5)
    m.scatter("alula", ["SM_AlUlaHouse_A", "SM_AlUlaHouse_B"], 30, (-330, 40, -760, -470), clearance=4, seed=12,
              min_spacing=14, yaw=None)
    # gameplay: checkpoints arches every ~1 km, boost pads and card pickups
    for s in (900, 1900, 2900):
        p, t, n, w, b = T.frame(s)
        m.place("common", "SM_Checkpoint_Arch", p[0], p[1], yaw=math.degrees(math.atan2(t[1], t[0])) + 90)
    # hidden-shortcut entrances: construction cones / fencing hide the metro ramp
    pm = m.shortcuts[1].frame(4)[0]
    for k in range(6):
        m.place("common", "SM_Cone", pm[0] + k * 1.2 - 3, pm[1] + 2.0, z=pm[2])
    m.place("common", "SM_Barrier_Water", pm[0] + 3, pm[1] - 1, z=pm[2], yaw=30)
    life(m)


def city(m: MapBuild):
    import dressing as D
    blocks = [f"SM_RiyadhBlock_{i:02d}" for i in range(1, 7)]

    def mask(x, y):
        vc = float(valley_center(np.array(y)))
        return (x - vc > 270 and not (470 < x < 650 and -270 < y < 330) and not (-160 < x < 290 and 320 < y < 770)
                and not (200 < x < 445 and -620 < y < 290))
    lots = D.city_grid(m, (-300, 1000, -1000, 1000), mask, block=118, street=16, angle=0,
                       lamps=("riyadh", "SM_StreetLight_KFR"))

    def towers(m, x, y, yaw, size, rnd):
        for q in D.lot_quads(x, y, yaw, size, rnd.choice((2, 3, 4))):
            m.place("riyadh", rnd.choice(blocks), q[0], q[1], yaw=yaw + rnd.choice((0, 90, 180, 270)),
                    scale=rnd.uniform(0.85, 1.3))

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

    def park(m, x, y, yaw, size, rnd):
        for k in range(8):
            m.place("common", rnd.choice(["SM_DatePalm_A", "SM_DatePalm_B"]), x + rnd.uniform(-35, 35), y + rnd.uniform(-35, 35),
                    yaw=rnd.uniform(0, 360))
        D.people(m, x, y, 10, 30, seed=rnd.randint(0, 9999), clearance=6)
    D.fill_lots(m, lots, [(0.52, towers), (0.16, villas), (0.12, shops), (0.1, D.parking), (0.04, mosque), (0.06, park)],
                seed=5)


def life(m: MapBuild):
    """Race night in Riyadh: crowds and floodlights, mosques, villas, shops and traffic in the city,
    families picnicking in Wadi Hanifa, visitors in Diriyah."""
    import dressing as D
    rnd = random.Random(19)
    T = m.main
    D.trackside(m, night=True, spots=[T.nearest_s((140, 430)), T.nearest_s((-470, 255))])
    plateau = lambda x, y: abs(x - float(valley_center(np.array(y)))) > 260 and x > -300  # noqa: E731
    # city fabric between the blocks
    m.place("life", "SM_GasStation", 395, -230, yaw=90)
    m.place("life", "SM_WaterTower", 860, 380)
    m.place("life", "SM_Mosque_Najdi", -330, -690, yaw=10)
    cars = ["SM_Car_Sedan_White", "SM_Car_Sedan_Silver", "SM_Car_Sedan_Red", "SM_Car_SUV_White", "SM_Car_SUV_Black",
            "SM_Car_Pickup_White"]
    m.scatter("life", cars, 70, (-280, 950, -950, 950), clearance=6, seed=33, max_slope=0.1, min_spacing=4,
              mask=plateau, yaw=None)
    m.scatter("life", ["SM_Bus_City", "SM_Truck_Water"], 10, (-280, 950, -950, 950), clearance=8, seed=34,
              max_slope=0.1, min_spacing=30, mask=plateau)
    D.people(m, 560, -100, 40, 70, seed=35)                 # Kingdom Centre plaza
    D.people(m, 120, 560, 50, 90, seed=36)                  # KAFD
    D.people(m, -170, -560, 45, 90, seed=37)                # Diriyah visitors
    # Wadi Hanifa picnics: tent / gazebo, campfire, cars and families
    for k, y in enumerate((-820, -420, 120, 520, 820)):
        x = float(valley_center(np.array(y))) + rnd.uniform(-40, 40)
        if m.clearance(x, y) < 25:
            x += 60
        D.cluster(m, "life", ["SM_BedouinTent", "SM_Gazebo_Green"], x, y, 1, 10, seed=40 + k, clearance=12)
        D.cluster(m, "life", "SM_Campfire", x, y, 1, 14, seed=50 + k, clearance=12)
        D.cluster(m, "life", cars[3:], x, y, 3, 30, seed=60 + k, clearance=10, min_spacing=5)
        D.people(m, x, y, 9, 22, seed=70 + k, clearance=8)
    for k in range(5):
        m.place("life", "SM_BirdFlock", -650 + rnd.uniform(-80, 80), rnd.uniform(-700, 700), z=rnd.uniform(35, 70),
                yaw=rnd.uniform(0, 360), scale=1.4)
    for k, y in enumerate(range(-900, 901, 300)):              # power line along the wadi rim
        m.place("life", "SM_PowerPylon", float(valley_center(np.array(y))) + 330, y, yaw=0)


def build(render=True, layout_only=False):
    sr.reset()
    t = make_terrain()
    tm = terrain_material(f"{NAME}_Terrain", ["Sand", "SandstoneStrata", "TerraceGrass", "Concrete"], [6, 14, 6, 4],
                          [(1, 1, 1), (1.05, 1.0, 0.92), (0.85, 0.82, 0.6), (1.0, 0.94, 0.85)])
    m = MapBuild(NAME, TITLE, t, tm, water=WATER)
    m.set_backdrop(far_height, far_paint, blend=700)
    m.far_detail.append(far_city)
    main, shorts = tracks()
    m.set_tracks(main, shorts)
    m.build_tracks(carve_layer=3)
    if layout_only:
        trk.minimap("/tmp/claude-0/riyadh_layout.png", t, main, shorts, TITLE, WATER)
        return m
    dress(m)
    m.export()
    m.write_gameplay(pickups=(450, 1500, 2600, 3500), boosts=(120, 1300, 2200, 3300))
    sr.write_manifest()
    if render:
        previews(m)
    return m


def lighting():
    sr.world_sky(2.5, 255, 0.22)
    sr.sun((87.5, 0, 255), 3.0, (1.0, 0.62, 0.36), 1.0)


def previews(m):
    from mapkit import render_previews
    kits = kit_objects("riyadh", "common", "alula", "life")
    m.preview_scene(kits)
    L = m.main.length
    cars = [("Falcon", 280, -2.5, None), ("JeddahGT", 296, 3.0, None), ("RiyadhMuscle", 318, -1.0, None),
            ("NajdiGXR", 2380, 2.0, None), ("HiluxRaider", 2400, -2.5, None), ("AlUlaRally", 3420, 0.0, None)]
    shots = [("overview", (1150, -1250, 760), (-120, 40, 0), 30),
             ("chase", 262, dict(back=12, height=3.0, ahead=60, lens=28)),
             ("overview", (520, 300, PL + 70), (330, 500, PL), 26),
             ("chase", 1780, dict(back=12, height=4.0, ahead=80, lens=26)),
             ("chase", 2362, dict(back=12, height=3.5, ahead=60, lens=28)),
             ("chase", 3402, dict(back=11, height=3.2, ahead=50, lens=30))]
    render_previews(m, shots, lighting, cars)


if __name__ == "__main__":
    build(layout_only="--layout" in sys.argv)
