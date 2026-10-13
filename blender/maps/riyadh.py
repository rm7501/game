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
  FlyoverJump   (visible)  gap in the flyover barrier: fly off the deck and land on the loop exit
  MetroLine     (hidden)   construction ramp up onto the Metro viaduct, straight across the valley
  PalmTrail     (hidden)   dirt trail through the palm grove cutting the wadi meander
  DiriyahBreach (hidden)   through a breach in the old mud wall, skipping the ruins S-bends
"""
import math
import os
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


def make_terrain():
    t = Terrain(layers=("Sand", "Limestone", "WadiSoil", "Paving"))
    X, Y = t.X, t.Y
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
    # eastern desert beyond the city: low dunes
    east = smoothstep(780, 950, X)
    h += east * (nz.ridged(X + 300, Y, 140, 3) ** 2) * 9
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
        CP(-560, -150, 13),                                                 # past the pond
        CP(-630, -280, 13),
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
    s_jump = Track("Shortcut_FlyoverJump", [
        CP(321, 270, 10, z=PL + 10, L=J, R=N), CP(318, 360, 9, z=PL + 15.5, tags={"gap"}), CP(312, 420, 9, z=PL + 1.5),
        CP(300, 452, 10, z=PL + 0.3, L=N, R=N)], closed=False, label="Flyover jump", hidden=False)
    # unfinished Metro viaduct: ride the deck to where it stops at the cliff edge and leap into the wadi
    s_metro = Track("Shortcut_MetroLeap", [
        CP(40, 463, 8, L=N, R=N, surf="metal"), CP(0, 410, 8, z=PL + 7, deck="metro", tags={"nocarve"}),
        CP(-140, 340, 8, z=PL + 8), CP(-300, 302, 8, z=PL + 7, tags={"gap"}), CP(-362, 270, 9, z=PL - 6),
        CP(-418, 224, 11, deck="highway", surf="asphalt_old")], closed=False, label="Metro leap", hidden=True)
    s_palm = Track("Shortcut_PalmTrail", [
        CP(-602, -40, 7, surf="dirt", L=N, R=N), CP(-640, -120, 7), CP(-660, -210, 7), CP(-632, -285, 7)],
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
    # city fabric on the plateau
    blocks = [f"SM_RiyadhBlock_{i:02d}" for i in range(1, 7)]
    m.scatter("riyadh", blocks, 260, (-300, 950, -950, 950), clearance=16, seed=4, max_slope=0.15,
              mask=lambda x, y: not (480 < x < 640 and -260 < y < 320) and not (-150 < x < 280 and 330 < y < 760),
              min_spacing=36, scale=(0.9, 1.35), yaw=0)
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


def build(render=True, layout_only=False):
    sr.reset()
    t = make_terrain()
    tm = terrain_material(f"{NAME}_Terrain", ["Sand", "SandstoneStrata", "TerraceGrass", "Concrete"], [6, 14, 6, 4],
                          [(1, 1, 1), (1.05, 1.0, 0.92), (0.85, 0.82, 0.6), (1.0, 0.94, 0.85)])
    m = MapBuild(NAME, TITLE, t, tm, water=WATER)
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
    kits = kit_objects("riyadh", "common", "alula")
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
