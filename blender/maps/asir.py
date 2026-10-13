"""ASIR - 'Soudah Switchbacks'.

Concept (reference photos): the green Asir escarpment - a serpentine of hairpins stacked up a steep
mountain nose, a road running along a knife-edge ridge with drops on both sides, morning mist lying in
the valleys, juniper forest, terraced fields and the stone tower-house village of Rijal Almaa, linked
to the top by the Soudah cable car.

Main circuit (~4.7 km, anticlockwise, climbs ~120 m and comes back down):
  Rijal Almaa plaza (start) -> valley road along the wadi -> three stacked hairpins up the mountain
  nose -> the knife-edge ridge road (guardrails, drops both sides, mist below) -> tunnel through the
  Soudah peak -> long sweeping descent through juniper forest and terraces, over a stone viaduct ->
  back into the village.
Shortcuts:
  WadiRun    (visible)  drop into the dry riverbed and blast along the gravel, cutting the valley bow
  SaddleJump (visible)  the old road over the peak's shoulder; ends at a washed-out bridge - jump it
  GoatTrack  (hidden)   rutted goat track straight down through the junipers, behind two trees
  MulePath   (hidden)   stepped mule path down the terraces and through the village alleys
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

NAME = "AsirMountains"
TITLE = "Asir - Soudah Switchbacks"
PEAK = (255.0, 405.0)          # Soudah peak (the main track tunnels straight through it)
VILLAGE = (-250.0, -560.0)     # Rijal Almaa, terraced up the hill north of the plaza


def river_y(x):
    return -728 + 12 * np.sin(x / 150.0) + 6 * np.sin(x / 47.0 + 1.0)


def floor_z(x):
    return 6 + 0.008 * (x + 1008)


def hairpin(cx, cy, r, a0, a1, z0, z1, w=11.0, bank=8.0, n=4, **kw):
    """CPs on a circular arc from angle a0 to a1 (deg), height z0 -> z1."""
    out = []
    for k in range(n + 1):
        t = k / n
        a = math.radians(a0 + (a1 - a0) * t)
        out.append(CP(cx + r * math.cos(a), cy + r * math.sin(a), w, z=z0 + (z1 - z0) * t, bank=bank, **kw))
    return out


# ------------------------------------------------------------------ tracks ---
def tracks():
    G, K, W_, N = "guardrail", "rock", "wall", "none"
    main = [
        # Rijal Almaa plaza -> valley road (eastbound, wadi on the right)
        CP(-300, -622, 13, L=W_, R=W_, surf="asphalt", tags={"curbs"}),
        CP(-185, -640, 13, L=K, R=G),
        CP(-80, -590, 12, bank=-3),
        CP(10, -500, 12, bank=6),                                               # bow round the terraced knoll
        CP(110, -590, 12, bank=4),
        CP(220, -662, 12, bank=-3),
        CP(410, -664, 12, L=K, R=G),
    ]
    # three stacked hairpins up the mountain nose (guardrail on the drop side, rock on the cut side)
    main += hairpin(480, -628, 36, -90, 90, 29, 35, bank=-8, L=K, R=G)[:-1]    # H1 (east, left)
    main += [CP(480, -592, 11, z=35, bank=0, L=G, R=K), CP(370, -592, 11, z=45)]
    main += hairpin(260, -556, 36, -90, -270, 55, 61, bank=8, L=G, R=K)[:-1]   # H2 (west, right)
    main += [CP(260, -520, 11, z=61, bank=0, L=K, R=G), CP(370, -520, 11, z=71)]
    main += hairpin(480, -484, 36, -90, 90, 81, 87, bank=-8, L=K, R=G)[:-1]    # H3 (east, left)
    main += [CP(480, -448, 11, z=87, bank=0, L=G, R=K), CP(385, -446, 11, z=95, bank=-4),
             CP(325, -405, 11, z=101, bank=-6)]
    # knife-edge ridge (northbound)
    main += [
        CP(300, -330, 11, z=106, bank=0, L=G, R=G),
        CP(338, -200, 11, z=112),
        CP(302, -62, 11, z=118, bank=3),
        CP(345, 78, 11, z=124, bank=-3),
        CP(305, 205, 11, z=130),
        CP(325, 300, 11, z=135),
        CP(318, 352, 12, z=138, tags={"tunnel"}),                               # Soudah peak tunnel
        CP(250, 410, 12, z=139.5, tags={"tunnel"}),
        CP(185, 462, 12, z=140, L=G, R=K),
        # descent: sweeping through the juniper forest (guardrail on the valley side)
        CP(80, 497, 12, bank=4),
        CP(-40, 472, 12, bank=3),
        CP(-170, 432, 12),
        CP(-300, 362, 12, bank=4),
        CP(-405, 252, 12, bank=6),
        CP(-430, 120, 12, bank=4),
        CP(-355, 10, 12, bank=-5),
        AUTO(CP(-232, -58, 12, bank=-4, deck="stone", tags={"bridge"})),       # stone viaduct over the gully
        AUTO(CP(-232, -165, 12, bank=-3)),
        CP(-345, -232, 12, bank=0),
        CP(-495, -262, 12, bank=5),
        CP(-598, -350, 12, bank=6),
        CP(-590, -470, 12, bank=4),
        CP(-512, -560, 12, L=W_, R=G, bank=-3),
        CP(-420, -606, 13, bank=-3),
    ]
    main_t = Track("Track", main, closed=True, surf="asphalt", L=G, R=G)
    main_t.smooth_m = 40.0
    wadi = Track("Shortcut_WadiRun", [
        CP(-185, -640, 10, surf="dirt", L=N, R=N), CP(-100, -702, 10), CP(30, -720, 11), CP(160, -712, 11),
        CP(220, -662, 10)], closed=False, label="Wadi run", hidden=False)
    saddle = Track("Shortcut_SaddleJump", [
        CP(305, 205, 9, surf="asphalt_old", L=G, R=N), CP(250, 262, 8, z=136), CP(170, 318, 8, z=143),
        CP(85, 365, 8, z=146, R=G), CP(20, 398, 8, z=147.5, tags={"gap"}),          # washed-out bridge
        CP(-32, 424, 9, z=133, L=N, R=N), CP(-120, 452, 10)], closed=False, label="Saddle jump", hidden=False)
    goat = Track("Shortcut_GoatTrack", [
        CP(-300, 362, 7, surf="dirt", L=N, R=N), CP(-305, 285, 6, dz=0.0), CP(-292, 190, 6, dz=0.6),
        CP(-300, 95, 6), CP(-282, 15, 6, dz=0.5), CP(-250, -45, 7)], closed=False, label="Goat track", hidden=True)
    mule = Track("Shortcut_MulePath", [
        CP(-495, -262, 7, surf="cobble", L=N, R=N), CP(-440, -330, 6), CP(-420, -410, 6, dz=0.4),
        CP(-370, -470, 6, L=W_, R=W_), CP(-330, -545, 6), CP(-300, -622, 8, L=N, R=N)],
        closed=False, label="Mule path", hidden=True)
    return main_t, [wadi, saddle, goat, mule]


def AUTO(c):
    """CP whose height is taken from the generated terrain (e.g. both ends of a viaduct)."""
    c["auto"] = True
    return c


def dense_profile(tr):
    """Dense (x, y, z) of a track's control spline (z interpolated between the CP heights)."""
    pts = [c["p"] for c in tr.cps]
    P, par = catmull_rom(pts, tr.closed)
    zs = np.array([c["z"] if c["z"] is not None else np.nan for c in tr.cps], float)
    idx = np.arange(len(zs))
    ok = ~np.isnan(zs)
    zs = np.interp(idx, idx[ok], zs[ok])
    k = np.floor(par).astype(int) % len(zs)
    k2 = (k + 1) % len(zs) if tr.closed else np.minimum(k + 1, len(zs) - 1)
    u = par - np.floor(par)
    return P, zs[k] * (1 - u) + zs[k2] * u


def poly_field(X, Y, pts, zs, half):
    """Distance field to a polyline: crest height zs (interpolated) and distance beyond the crest
    half-width `half`. Returns (crest height, e = metres outside the crest)."""
    best = np.full(X.shape, np.inf)
    zc = np.zeros(X.shape)
    hw = np.zeros(X.shape)
    for k in range(len(pts) - 1):
        (ax, ay), (bx, by) = pts[k], pts[k + 1]
        vx, vy = bx - ax, by - ay
        L2 = vx * vx + vy * vy or 1e-9
        t = np.clip(((X - ax) * vx + (Y - ay) * vy) / L2, 0, 1)
        d = np.hypot(X - (ax + t * vx), Y - (ay + t * vy))
        m = d < best
        best = np.where(m, d, best)
        zc = np.where(m, zs[k] + (zs[k + 1] - zs[k]) * t, zc)
        hw = np.where(m, half[k] + (half[k + 1] - half[k]) * t, hw)
    return zc, np.maximum(best - hw, 0)


def mountains(nz, X, Y, scale=300.0):
    """0..1 rugged mountain field: warped ridged noise + rounded fbm massing."""
    wx = X + 90 * (nz.fbm(X + 4000, Y, 260, 3) - 0.5) * 2
    wy = Y + 90 * (nz.fbm(X, Y - 4000, 260, 3) - 0.5) * 2
    r = nz.ridged(wx * 0.87 - wy * 0.5, wx * 0.5 + wy * 0.87, scale, 5)
    b = nz.fbm(wx, wy, scale * 1.6, 4)
    return np.clip(0.55 * r + 0.65 * b ** 1.6, 0, 1.2)


# ----------------------------------------------------------------- terrain ---
def make_terrain(main, shorts):
    t = Terrain(layers=("Grass", "Rock", "Soil", "Stone"))
    X, Y = t.X, t.Y
    nz = Noise(23)
    yr = river_y(X)
    fl = floor_z(X)
    dn = Y - yr                                          # metres north of the wadi
    # warped coordinates so the big zones have organic edges
    WX = X + 70 * (nz.fbm(X + 900, Y + 300, 300, 3) - 0.5) * 2
    WY = Y + 70 * (nz.fbm(X - 700, Y + 1300, 300, 3) - 0.5) * 2
    M = mountains(nz, X, Y)
    # south range: terraced green slopes facing the escarpment, rugged tops
    south = fl + (60 + 150 * M) * smoothstep(10, 320, -(WY - yr)) ** 1.2
    # north: central basin, western forest slope (the descent), Soudah plateau, eastern gorge + range
    basin = fl + 12 + 40 * smoothstep(-700, 260, Y) + 6 * (nz.fbm(X, Y, 120, 3) - 0.5)
    west = 16 + 0.105 * (Y + 640) + 60 * smoothstep(-430, -1000, WX) * (0.6 + 0.6 * M)
    north = basin + (west - basin) * smoothstep(-90, -300, WX)
    plateau = 131 + 8 * smoothstep(380, 620, Y)
    north = north + (plateau - north) * smoothstep(250, 400, WY)
    east = 34 + 6 * np.sin(Y / 90.0) + (40 + 190 * M) * smoothstep(640, 980, WX)
    north = north + (east - north) * smoothstep(430, 560, WX) * (1 - smoothstep(560, 760, WY))
    north = north + (50 + 230 * M) * smoothstep(540, 940, WY)                 # northern Sarawat range
    north = fl + (north - fl) * smoothstep(8, 90, dn)
    h = np.where(dn < 0, south, north)
    # the mountain nose (hairpins): a broad rounded spur climbing north
    nose = [(372, -700, 22, 120), (372, -660, 28, 115), (368, -588, 46, 110), (370, -516, 70, 105),
            (372, -470, 88, 95), (345, -430, 99, 50), (305, -380, 104, 12)]
    zc, e = poly_field(X, Y, [(a, b) for a, b, _, _ in nose], np.array([n[2] for n in nose]),
                       np.array([n[3] for n in nose]))
    flank = 0.45 + 0.35 * nz.fbm(X, Y, 90, 3)
    f = zc - 0.004 * np.minimum(e, 60) ** 2 * 1.2 - flank * np.maximum(e - 60, 0)
    # knife-edge ridge following the road heights: steep concave flanks cut by erosion gullies
    P, Z = dense_profile(main)
    i_peak = int(np.argmin(np.linalg.norm(P - np.array([318, 352]), axis=1)))
    i_r0 = int(np.argmin(np.linalg.norm(P - np.array([300, -330]), axis=1)))
    rp = [(float(P[i, 0]), float(P[i, 1])) for i in range(i_r0, i_peak, 6)]
    rz = np.array([float(Z[i]) + 1.2 for i in range(i_r0, i_peak, 6)])
    zc2, e2 = poly_field(X, Y, rp, rz, np.full(len(rp), 8.0))
    gull = nz.ridged(X * 0.3 + Y * 0.95, Y * 0.3 - X * 0.95, 70, 3)          # gullies down the flanks
    spur = nz.fbm(X + 50, Y * 0.6, 110, 3)                                   # shoulders and spurs
    L2 = 85 + 170 * smoothstep(0.35, 0.7, spur)
    drop = (115 + 40 * nz.fbm(X, Y, 150, 3)) * (1 - np.exp(-(e2 / L2) ** 1.4))   # rounded green shoulder
    f2 = zc2 - drop - 16 * gull * smoothstep(5, 25, e2) * (1 - smoothstep(100, 170, e2))
    h = np.maximum(h, np.maximum(f, f2))
    # Soudah peak: a rugged granite dome (the main road tunnels straight through it)
    dx, dy = X - PEAK[0], Y - PEAK[1]
    th = np.arctan2(dy, dx)
    r = np.hypot(dx, dy) / (1 + 0.18 * np.sin(3 * th + 1.0) + 0.12 * np.sin(5 * th + 2.0) + 0.2 * (nz.fbm(X, Y, 50, 3) - 0.5))
    dome = 255 * (1 - np.clip(r / 185.0, 0, 1) ** 1.35) + 18 * (nz.ridged(X, Y, 45, 3) - 0.4) * smoothstep(185, 90, r)
    h = np.maximum(h, dome)
    # spur under the old saddle road
    sp, sz = dense_profile(shorts[1])
    cut = int(np.argmin(np.linalg.norm(sp - np.array([20, 398]), axis=1)))
    pts = [(float(a), float(b)) for a, b in sp[:cut:5]]
    zz = np.array([float(z) + 1.0 for z in sz[:cut:5]])
    zc3, e3 = poly_field(X, Y, pts, zz, np.full(len(pts), 7.0))
    h = np.maximum(h, zc3 - 70 * (1 - np.exp(-e3 / 60.0)))
    # the ravine under the washed-out bridge, and the gully under the stone viaduct
    d = dist_to_polyline(X, Y, [(-2, 452), (-8, 400), (-40, 320), (-90, 200)])
    h -= 30 * np.exp(-(d / 20.0) ** 2) * smoothstep(-120, 60, Y)
    d = dist_to_polyline(X, Y, [(-700, -60), (-420, -120), (-232, -112), (-60, -170)])
    h -= 14 * np.exp(-(d / 22.0) ** 2)
    # terraced knoll inside the valley-road bow
    h = np.maximum(h, fl + 22 * np.exp(-(((X - 40) / 60.0) ** 2 + ((Y + 615) / 45.0) ** 2)))
    # the wadi bed itself
    h -= 3.0 * np.exp(-((Y - yr) / 16.0) ** 2)
    # Rijal Almaa hill: the village climbs it in stone platforms
    vx, vy = VILLAGE
    hill = np.exp(-(((X - vx) / 110.0) ** 2 + ((Y - (vy + 40)) / 70.0) ** 2))
    h = np.maximum(h, fl + 4 + 22 * hill * smoothstep(vy - 45, vy + 25, Y))
    # detail: soft noise everywhere, granite outcrops up high
    h += (nz.fbm(X, Y, 70, 4) - 0.5) * 6
    h += (nz.ridged(X + 500, Y, 110, 3) - 0.35) * 8 * smoothstep(120, 220, h)
    # terraces on the farmed slopes (basin, lower west slope, south range, village hill)
    t.h = h
    slope = t.slope()
    farm = (smoothstep(0.06, 0.18, slope) * (1 - smoothstep(0.5, 0.75, slope)) * (1 - smoothstep(115, 150, h))
            * smoothstep(0.4, 0.52, nz.fbm(X + 900, Y, 130, 3) + 0.1))
    step = 2.4
    q = np.floor(h / step)
    fr = h / step - q
    terr = (q + smoothstep(0.8, 1.0, fr)) * step
    h = h + (terr - h) * farm * 0.9
    t.h = h
    return t, farm


def precarve(t, tracks, falloff=30.0):
    """Shape the mountain to the designed road heights first (benches, cuttings, embankments)."""
    for tr in tracks:
        tr.build(t)
        keep = np.array([("bridge" not in g) and ("nocarve" not in g) for g in tr.tag]) & ~tr.tunnel & ~tr.gap
        hw = tr.W / 2 + 3.0 + np.abs(np.sin(tr.bank)) * tr.W / 2
        t.carve(tr.P[keep], tr.Z[keep] - 0.3, hw[keep], falloff=falloff)


def paint(t, farm):
    """Grass on the fields, granite on steep faces and high tops, dry-stone on terrace risers,
    soil in the wadi bed and on the road verges (carve layer)."""
    X, Y = t.X, t.Y
    nz = Noise(5)
    slope = t.slope()
    t.set_layer(1, smoothstep(0.9, 1.35, slope) * smoothstep(0.35, 0.6, nz.fbm(X, Y, 22, 3) + 0.2)
                + smoothstep(200, 270, t.h) * smoothstep(0.4, 0.7, slope))
    t.set_layer(3, farm * smoothstep(0.45, 0.8, slope) * 0.9)
    t.set_layer(2, np.exp(-((Y - river_y(X)) / 14.0) ** 2) * (1 - smoothstep(0.3, 0.5, slope)))


# ------------------------------------------------------------------- props ---
def cable_line(stations):
    """Cable car ropes between pylon tops (map prop, catenary sag)."""
    rope = sr.mat("SteelDark", (0.08, 0.08, 0.09), rough=0.4, metal=1.0)
    mb = sr.MB("SM_SoudahCableRopes")
    for off in (-2.6, 2.6):
        for a, b in zip(stations[:-1], stations[1:]):
            a, b = np.array(a, float), np.array(b, float)
            d = b[:2] - a[:2]
            n = np.array([-d[1], d[0]]) / max(np.linalg.norm(d), 1e-6)
            L = float(np.linalg.norm(d))
            pts = []
            for k in range(25):
                u = k / 24
                p = a + (b - a) * u
                sag = 4 * (L / 120.0) * u * (1 - u) * 2.0
                pts.append((p[0] + n[0] * off, p[1] + n[1] * off, p[2] - sag))
            mb.tube(pts, 0.05, rope, seg=5)
    return mb.to_object(origin="keep", sharp_angle=None)


def cable_station(name="SM_SoudahCableStation"):
    conc = sr.mat("Concrete", (1, 1, 1), tex="Concrete", tile=2.0)
    glass = sr.mat("Car_Glass", (0.02, 0.025, 0.03), rough=0.02, metal=0.0, transmission=0.7, kind="glass")
    red = sr.mat("CableCar_Red", (0.7, 0.08, 0.06), rough=0.35, coat=0.6)
    stone = sr.mat("Asir_StoneMasonry", (1.25, 1.2, 1.15), rough=0.9, tex="StoneMasonry", tile=2.4)
    mb = sr.MB(name)
    mb.box((22, 14, 6), (0, 0, 3), m=stone)
    mb.box((20, 12.4, 3.2), (0, 0, 7.6), m=glass)
    mb.box((26, 18, 0.8), (0, 0, 9.6), m=conc)
    mb.box((6, 18.5, 0.6), (0, 0, 10.3), m=red)
    mb.cyl(3.2, 0.8, (8, 0, 11.2), m=red, seg=24)
    return mb.to_object(origin="base", sharp_angle=40)


def map_props(pylons):
    objs = [cable_line(pylons), cable_station()]
    folder = os.path.join(sr.ROOT, "assets", "maps", NAME, "props")
    sr.export_kit(objs, os.path.relpath(folder, os.path.join(sr.ROOT, "assets")), blend=False)
    return objs


def cable_route(m):
    """Village station -> pylons -> top station on the ridge (x, y, ground z, top z)."""
    a = np.array([-150.0, -515.0])
    b = np.array([250.0, -160.0])
    pts = []
    for k in range(5):
        p = a + (b - a) * k / 4
        g = float(m.terrain.sample(p[0], p[1]))
        pts.append((float(p[0]), float(p[1]), g))
    return pts


def dress(m: MapBuild):
    T = m.main
    rnd = random.Random(17)

    def yaw_at(tr, s):
        t_ = tr.frame(s)[1]
        return math.degrees(math.atan2(t_[1], t_[0]))
    p0 = T.frame(0)[0]
    m.place("common", "SM_StartGantry", p0[0], p0[1], yaw=yaw_at(T, 0) + 90)
    # Rijal Almaa: the stepped village climbs the hill north of the plaza, plus loose tower houses
    vx, vy = VILLAGE
    m.place("asir", "SM_RijalAlmaaVillage", vx, vy, yaw=0)
    m.place("asir", "SM_RijalAlmaaVillage", vx - 70, vy + 18, yaw=-14, scale=0.9)
    houses = [f"SM_RijalAlmaaHouse_{i:02d}" for i in range(1, 5)]
    m.scatter("asir", houses, 26, (vx - 190, vx + 160, vy - 30, vy + 140), clearance=5, seed=21, min_spacing=13,
              max_slope=0.9, yaw=None, scale=(0.9, 1.15))
    m.place("common", "SM_Grandstand", p0[0] + 30, p0[1] - 20, yaw=yaw_at(T, 0) + 180)
    # Asiri mud towers (qasaba) on the farmland and as watchtowers along the ridge
    for x, y in ((-80, -360), (40, -250), (-120, -120), (90, 30), (-30, 180), (140, -420)):
        m.place("asir", "SM_AsiriMudTower_" + "AB"[int(x) % 2], x, y, yaw=rnd.uniform(0, 90))
    for s in (T.nearest_s((338, -200)) + 40, T.nearest_s((345, 78)) + 30):
        p, t_, n, w, b = T.frame(s)
        q = p[:2] - n * (w / 2 + 9)
        m.place("asir", "SM_AsiriMudTower_B", q[0], q[1], yaw=yaw_at(T, s))
    # juniper forest: dense on the west slope + massif, scattered elsewhere
    def forest(x, y):
        return (x < 150 and y > -330) or (y > 420)
    m.scatter("asir", ["SM_Juniper_A", "SM_Juniper_B"], 1500, (-990, 990, -400, 990), clearance=5, seed=3,
              max_slope=0.75, mask=forest, min_spacing=6, scale=(0.8, 1.5))
    m.scatter("asir", ["SM_Juniper_A", "SM_Juniper_B"], 260, (-990, 990, -990, -400), clearance=6, seed=4,
              max_slope=0.6, min_spacing=10, scale=(0.7, 1.3))
    # retaining walls on the cut side of the hairpin legs
    s_a, s_b = T.nearest_s((480, -664)), T.nearest_s((325, -405))
    s = s_a
    while s < s_b:
        p, t_, n, w, b = T.frame(s)
        hl = float(m.terrain.sample(*(p[:2] + n * (w / 2 + 7))))
        hr = float(m.terrain.sample(*(p[:2] - n * (w / 2 + 7))))
        if abs(hl - hr) > 4:
            sg = 1 if hl > hr else -1
            q = p[:2] + n * sg * (w / 2 + 2.2)
            m.place("asir", "SM_RetainingWall_20m", q[0], q[1], z=float(p[2]) - 0.3, yaw=yaw_at(T, s) + (180 if sg > 0 else 0))
        s += 20
    # cable car: village station -> pylons -> ridge station
    route = cable_route(m)
    tops = []
    for k, (x, y, g) in enumerate(route):
        yaw = math.degrees(math.atan2(route[-1][1] - route[0][1], route[-1][0] - route[0][0]))
        if k in (0, len(route) - 1):
            m.place(f"maps/{NAME}/props", "SM_SoudahCableStation", x, y, yaw=yaw)
            tops.append((x, y, g + 11.2))
        else:
            m.place("asir", "SM_CableCar_Pylon", x, y, yaw=yaw + 90)
            tops.append((x, y, g + 33.0))
    m.cable_tops = tops
    m.place(f"maps/{NAME}/props", "SM_SoudahCableRopes", 0, 0, z=0)
    for u in (0.18, 0.43, 0.71):
        k = int(u * (len(tops) - 1))
        f = u * (len(tops) - 1) - k
        a, b = np.array(tops[k]), np.array(tops[k + 1])
        p = a + (b - a) * f
        m.place("asir", "SM_CableCar_Cabin", p[0] + 2.6, p[1], z=float(p[2]) - 5.2 - 3.0)
    # checkpoint arches
    for s in (1150, 2350, 3550):
        p = T.frame(s)[0]
        m.place("common", "SM_Checkpoint_Arch", p[0], p[1], yaw=yaw_at(T, s) + 90)
    # hidden entrances: junipers in front of the goat track, a gap between walls for the mule path
    g0 = m.shortcuts[2].frame(16)
    for sg in (1, -1):
        q = g0[0][:2] + g0[2] * sg * 4.5
        m.place("asir", "SM_Juniper_A", q[0], q[1], scale=1.4)
    m0 = m.shortcuts[3].frame(14)
    for sg in (1, -1):
        q = m0[0][:2] + m0[2] * sg * 9.0
        m.place("asir", "SM_RetainingWall_20m", q[0], q[1], yaw=math.degrees(math.atan2(m0[1][1], m0[1][0])) + 90)
    # backdrop mountains beyond the map edge
    for x, y, a, sc, nm in ((0, 1550, 0, 1.2, "A"), (-1300, 900, 60, 1.0, "B"), (1350, 700, 200, 1.0, "A"),
                            (1500, -500, 120, 1.0, "B"), (-1500, -300, 250, 1.1, "A"), (-600, -1600, 30, 1.0, "B"),
                            (800, -1550, 160, 1.0, "A")):
        m.place("asir", f"SM_AsirMountain_{nm}", x, y, z=-30, yaw=a, scale=sc)


# ------------------------------------------------------------------- build ---
def build(render=True, layout_only=False):
    sr.reset()
    main, shorts = tracks()
    t, farm = make_terrain(main, shorts)
    sm = t.h.copy()
    from terrain import blur
    sm = blur(t.h, 6)
    for c in main.cps:
        if c.get("auto"):
            c["z"] = float(t.sample(*c["p"], h=sm)) + 0.5
    precarve(t, [main, shorts[1]])
    paint(t, farm)
    tm = terrain_material(f"{NAME}_Terrain", ["TerraceGrass", "Rock", "Sand", "StoneMasonry"], [5, 9, 6, 3],
                          [(1, 1, 1), (0.85, 0.85, 0.88), (0.62, 0.48, 0.36), (0.9, 0.88, 0.85)])
    m = MapBuild(NAME, TITLE, t, tm)
    m.far_mat = sr.mat("Asir_TerraceGrass", (1, 1, 1), rough=0.95, tex="TerraceGrass", tile=4.0)
    m.set_tracks(main, shorts)
    m.build_tracks(carve_layer=2, falloff=16)
    if layout_only:
        trk.minimap("/tmp/claude-0/asir_layout.png", t, main, shorts, TITLE)
        for tr in [main] + shorts:
            print(f"{tr.name}: {tr.length:.0f} m  bridge {tr.bridge.sum() * tr.step:.0f} m  tunnel {tr.tunnel.sum() * tr.step:.0f} m"
                  f"  max grade {np.abs(np.diff(tr.Z) / tr.step).max() * 100:.0f}%")
        for sc in shorts:
            a, b = main.nearest_s(sc.P[0]), main.nearest_s(sc.P[-1])
            print(f"  {sc.name}: saves {(b - a) % main.length - sc.length:.0f} m")
        return m
    dress(m)
    props = map_props(m.cable_tops)
    m.export()
    m.write_gameplay(pickups=(420, 1500, 2700, 3800), boosts=(150, 1300, 2500, 3400))
    sr.write_manifest()
    if render:
        previews(m, props)
    return m


def lighting():
    import bpy
    sr.world_sky(13, 115, 0.3)
    sr.sun((77, 0, 115), 4.5, (1.0, 0.86, 0.7), 2.0)
    # morning mist lying in the valleys (the ridge rides above it)
    fog = sr.MB("Mist")
    fog.box((4200, 4200, 75), (0, 0, 22), m=None)
    fo = fog.to_object(uv=False)
    vm = bpy.data.materials.new("MistVolume")
    vm.use_nodes = True
    nt = vm.node_tree
    nt.nodes.clear()
    o = nt.nodes.new("ShaderNodeOutputMaterial")
    v = nt.nodes.new("ShaderNodeVolumePrincipled")
    v.inputs["Density"].default_value = 0.0028
    v.inputs["Color"].default_value = (0.86, 0.9, 1.0, 1)
    nt.links.new(v.outputs[0], o.inputs["Volume"])
    fo.data.materials.clear()
    fo.data.materials.append(vm)
    bpy.context.scene.cycles.volume_step_rate = 4.0
    bpy.context.scene.view_settings.exposure = 0.3


def previews(m, props):
    from mapkit import render_previews
    kits = kit_objects("asir", "common") + props
    m.preview_scene(kits)
    T = m.main
    s_ridge = T.nearest_s((338, -200))
    s_desc = T.nearest_s((-300, 362))
    s_pin = T.nearest_s((370, -520))
    cars = [("NajdiGXR", 22, -2.5, None), ("HiluxRaider", 40, 3.0, None),
            ("Falcon", s_ridge + 16, 1.5, None), ("AlUlaRally", s_desc + 18, -2.0, None),
            ("RiyadhMuscle", s_pin + 8, 0.0, None), ("DuneFox", 60, 0.0, m.shortcuts[1])]
    shots = [("overview", (1250, -1500, 760), (0, -60, 40), 30),
             ("chase", 6, dict(back=12, height=3.2, ahead=60, lens=28)),
             ("overview", (330, -930, 175), (385, -545, 58), 32),
             ("chase", s_ridge, dict(back=13, height=4.0, ahead=80, lens=26)),
             ("chase", s_desc, dict(back=12, height=3.4, ahead=60, lens=28)),
             ("chase", 40, dict(back=12, height=3.5, ahead=60, lens=26, track=m.shortcuts[1]))]
    render_previews(m, shots, lighting, cars)


if __name__ == "__main__":
    build(layout_only="--layout" in sys.argv)
