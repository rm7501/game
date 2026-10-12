"""Sahara Racers - JEDDAH AL-BALAD map kit (UNESCO historic district).

  SM_HijaziHouse_01..06   coral-stone tower houses: wooden takaleel bands, stacked rawasheen
                          (projecting lattice bay windows), flush mashrabiya windows, carved doors,
                          pierced roof parapets
  SM_NassifHouse          Bayt Nassif - the grand house with its famous tree in front
  SM_Roshan_2F / _3F      standalone rawasheen (2 / 3 storeys) to dress your own facades
  SM_HijaziMinaret        octagonal minaret with gallery and cap (Al-Shafi'i / Al-Mimar style)
  SM_BabMakkah            old city gate with arched passage and merlons
  SM_SouqAwning           fabric awning strip spanning a lane
  SM_Lantern              hanging brass lantern (emissive)
  SM_StringLights         festive string lights across a lane
  SM_SouqStall            market stall with goods
  SM_MarkazBench          wooden 'markaz' bench with cushions
  SM_Lane_Paving_20m      stone-paved lane section (10 m wide, fits a race car)
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))
import sr  # noqa: E402

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

KIT = "jeddah"

ROSHAN_COLOURS = {
    "Teal": (0.08, 0.38, 0.36), "Green": (0.1, 0.32, 0.17), "Blue": (0.12, 0.26, 0.48),
    "Brown": (0.32, 0.2, 0.11), "Turquoise": (0.16, 0.52, 0.55), "White": (0.82, 0.82, 0.78),
}


def M():
    m = dict(
        coral=sr.mat("Jeddah_CoralStone", (1.0, 0.98, 0.95), rough=0.9, tex="CoralStone", tile=3.0),
        coral_warm=sr.mat("Jeddah_CoralStoneWarm", (0.96, 0.88, 0.76), rough=0.9, tex="CoralStone", tile=3.0),
        timber=sr.mat("Jeddah_Takaleel", (0.48, 0.36, 0.24), rough=0.85, tex="WoodPainted", tile=1.0),
        door=sr.mat("Jeddah_DoorWood", (0.38, 0.24, 0.13), rough=0.7, tex="WoodPainted", tile=0.8),
        dark=sr.mat("WindowDarkHole", (0.02, 0.015, 0.01), rough=0.9),
        paver=sr.mat("Jeddah_StonePaving", (0.85, 0.8, 0.7), rough=0.8, tex="StoneMasonry", tile=2.0),
        brass=sr.mat("Brass", (0.8, 0.58, 0.25), rough=0.3, metal=1.0),
        lamp=sr.mat("LanternGlow", (1.0, 0.7, 0.35), emit=(1.0, 0.65, 0.3), emit_str=14, kind="emissive"),
        bulb=sr.mat("BulbWarm", (1.0, 0.8, 0.5), emit=(1.0, 0.75, 0.45), emit_str=20, kind="emissive"),
        wire=sr.mat("SteelDark", (0.08, 0.08, 0.09), rough=0.4, metal=1.0),
        green_trim=sr.mat("Minaret_GreenTrim", (0.05, 0.35, 0.2), rough=0.5),
        white=sr.mat("Lime_White", (0.92, 0.91, 0.87), rough=0.8, tex="CoralStone", tile=4.0),
        cushion_r=sr.mat("Cushion_Red", (0.55, 0.06, 0.05), rough=0.8),
        cushion_g=sr.mat("Cushion_Green", (0.08, 0.3, 0.15), rough=0.8),
        cloth=[sr.mat("Awning_Red", (0.6, 0.12, 0.08), rough=0.8, kind="foliage"),
               sr.mat("Awning_Cream", (0.88, 0.82, 0.68), rough=0.8, kind="foliage"),
               sr.mat("Awning_Indigo", (0.15, 0.17, 0.4), rough=0.8, kind="foliage")],
        goods=[sr.mat(f"Goods_{i}", c, rough=0.7) for i, c in enumerate(
            ((0.7, 0.35, 0.1), (0.85, 0.65, 0.2), (0.45, 0.12, 0.08), (0.2, 0.4, 0.15), (0.9, 0.85, 0.7)))],
        leaf=sr.mat("Tree_NeemLeaves", (0.16, 0.3, 0.1), rough=0.7, kind="foliage"),
        bark=sr.mat("Tree_Bark", (0.3, 0.24, 0.18), rough=0.95, tex="Rock", tile=1.5),
    )
    for k, c in ROSHAN_COLOURS.items():
        m["roshan_" + k] = sr.mat(f"Roshan_{k}", c, rough=0.75, tex="WoodPainted", tile=1.2)
    return m


# ----------------------------------------------------------------- roshan ---
def lattice(mb, x0, x1, z0, z1, y, m, pitch=0.085, slat=0.022, depth=0.03, axis="x"):
    """Mashrabiya grid. axis='x': panel in the XZ plane at y; axis='y': panel in the YZ plane at x=y."""
    W = x1 - x0
    H = z1 - z0
    nv = max(2, int(W / pitch))
    nh = max(2, int(H / pitch))
    for i in range(nv + 1):
        u = x0 + W * i / nv
        if axis == "x":
            mb.box((slat, depth, H), (u, y, (z0 + z1) / 2), m=m)
        else:
            mb.box((depth, slat, H), (y, u, (z0 + z1) / 2), m=m)
    for j in range(nh + 1):
        z = z0 + H * j / nh
        if axis == "x":
            mb.box((W, depth, slat), ((x0 + x1) / 2, y, z), m=m)
        else:
            mb.box((depth, W, slat), (y, (x0 + x1) / 2, z), m=m)


def roshan(mm, colour="Teal", W=2.4, floors=2, fh=3.4, p=0.7, name="roshan"):
    """Projecting Hijazi bay window stack. Local frame: wall plane y=0, projects to -Y, base z=0."""
    m = mm["roshan_" + colour]
    mb = sr.MB(name)
    H = floors * fh
    # corbel brackets + base board
    for x in (-W / 2 + 0.15, 0.0, W / 2 - 0.15):
        mb.prism([(0, 0), (p, 0), (0, -0.55)], -0.06, 0.06, (x, 0, 0), (90, 0, -90), m=m)
    mb.box((W + 0.1, p + 0.05, 0.14), (0, -p / 2, 0.07), m=m)
    for k in range(floors):
        z0 = k * fh + 0.14
        # kick panel with carved inset panels
        mb.box((W, 0.05, 0.8), (0, -p, z0 + 0.4), m=m)
        for q in range(3):
            x = -W / 2 + W * (q + 0.5) / 3
            mb.box((W / 3 - 0.18, 0.03, 0.5), (x, -p - 0.035, z0 + 0.4), m=m, bevel=0.01)
        for sg in (1, -1):
            mb.box((0.05, p, 0.8), (sg * W / 2, -p / 2, z0 + 0.4), m=m)
        # lattice zone (front + sides)
        zl0, zl1 = z0 + 0.82, z0 + fh - 0.4
        lattice(mb, -W / 2 + 0.04, W / 2 - 0.04, zl0, zl1, -p, m)
        for sg in (1, -1):
            lattice(mb, -p + 0.04, -0.04, zl0, zl1, sg * W / 2, m, axis="y")
        # rails + corner posts
        mb.box((W + 0.06, 0.08, 0.1), (0, -p, zl0), m=m)
        mb.box((W + 0.06, 0.08, 0.12), (0, -p, zl1 + 0.06), m=m)
        mb.box((W + 0.1, p + 0.1, 0.22), (0, -p / 2, zl1 + 0.25), m=m)      # floor band between storeys
        for sg in (1, -1):
            mb.box((0.1, 0.1, fh), (sg * W / 2, -p, z0 + fh / 2), m=m)
        # hinged upper shutter (slightly open on some levels)
        if k % 2 == 0:
            mb.box((W * 0.45, 0.04, 0.55), (W * 0.22, -p - 0.18, zl1 - 0.3), (25, 0, 0), m=m)
    # crown: projecting cornice with stepped teeth
    zt = H + 0.14
    mb.box((W + 0.3, p + 0.3, 0.2), (0, -p / 2 - 0.1, zt + 0.1), m=m)
    n = int((W + 0.3) / 0.22)
    for i in range(n):
        x = -(W + 0.3) / 2 + 0.11 + i * 0.22
        mb.prism([(-0.08, 0), (0.08, 0), (0.08, 0.1), (0.04, 0.1), (0.04, 0.2), (-0.04, 0.2), (-0.04, 0.1), (-0.08, 0.1)],
                 -0.03, 0.03, (x, -p - 0.24, zt + 0.2), (90, 0, 0), m=m)
    return mb


# ------------------------------------------------------------- Hijazi house ---
def hijazi_house(mm, name, w=10.0, d=9.0, floors=4, seed=1, stacks=2, side_stacks=0):
    rnd = random.Random(seed)
    mb = sr.MB(name)
    gf, fh = 4.0, 3.4
    H = gf + (floors - 1) * fh
    wall = mm["coral"] if rnd.random() < 0.65 else mm["coral_warm"]
    mb.box((w, d, H), (0, 0, H / 2), m=wall)
    colours = list(ROSHAN_COLOURS)
    # takaleel timber bands (every ~1 m) and floor bands
    z = 0.9
    while z < H - 0.6:      # takaleel: timber courses bedded in the coral masonry every ~1 m
        t = rnd.uniform(0.05, 0.08)
        mb.box((w + 0.02, 0.03, t), (0, -d / 2 - 0.004, z), m=mm["timber"])
        mb.box((w + 0.02, 0.03, t), (0, d / 2 + 0.004, z), m=mm["timber"])
        mb.box((0.03, d + 0.02, t), (w / 2 + 0.004, 0, z), m=mm["timber"])
        mb.box((0.03, d + 0.02, t), (-w / 2 - 0.004, 0, z), m=mm["timber"])
        z += rnd.uniform(0.85, 1.25)
    # main facade (-Y): roshan stacks from first floor up
    slots = [(-w / 2 + w * (i + 0.5) / stacks) for i in range(stacks)]
    used = []
    for x in slots:
        col = rnd.choice(colours)
        nf = rnd.randint(max(1, floors - 2), floors - 1)
        Wr = min(2.8, w / stacks - 0.8)
        r = roshan(mm, col, Wr, nf, fh)
        mb.add_mb(r, (x, -d / 2, gf - 0.2))
        r.bm.free()
        used.append(x)
    # flush mashrabiya windows elsewhere on the facades
    for f in range(1, floors):
        z = gf + (f - 1) * fh + 1.6
        for k in range(max(1, int(w / 3.2))):
            x = -w / 2 + (k + 0.5) * w / max(1, int(w / 3.2))
            if any(abs(x - u) < 1.9 for u in used):
                continue
            m = mm["roshan_" + rnd.choice(colours)]
            mb.box((1.1, 0.06, 1.6), (x, -d / 2 - 0.02, z), m=mm["dark"])
            lattice(mb, x - 0.52, x + 0.52, z - 0.76, z + 0.76, -d / 2 - 0.06, m, pitch=0.1)
            mb.box((1.3, 0.12, 0.1), (x, -d / 2 - 0.06, z + 0.85), m=m)
    for side in (1, -1):   # side facades: smaller windows (+ optional roshan)
        for f in range(1, floors):
            z = gf + (f - 1) * fh + 1.6
            for k in range(max(1, int(d / 3.5))):
                y = -d / 2 + (k + 0.5) * d / max(1, int(d / 3.5))
                m = mm["roshan_" + rnd.choice(colours)]
                mb.box((0.06, 0.9, 1.3), (side * (w / 2 + 0.02), y, z), m=mm["dark"])
                lattice(mb, y - 0.42, y + 0.42, z - 0.62, z + 0.62, side * (w / 2 + 0.05), m, pitch=0.1, axis="y")
        if side_stacks and side > 0:
            r = roshan(mm, rnd.choice(colours), 2.2, floors - 1, fh)
            mb.add_mb(r, (w / 2, rnd.uniform(-d / 4, d / 4), gf - 0.2), (0, 0, 90))
            r.bm.free()
    # carved double door with stone surround + steps
    dx = rnd.uniform(-w / 4, w / 4)
    if any(abs(dx - u) < 1.6 for u in used) and used:
        dx = used[0] + (2.0 if used[0] < 0 else -2.0)
    mb.box((2.6, 0.3, 3.4), (dx, -d / 2 - 0.1, 1.7), m=mm["white"])
    mb.box((1.9, 0.2, 2.9), (dx, -d / 2 - 0.2, 1.45), m=mm["door"])
    for i in range(2):
        for j in range(4):
            mb.box((0.7, 0.05, 0.55), (dx - 0.45 + i * 0.9, -d / 2 - 0.32, 0.45 + j * 0.65), m=mm["door"], bevel=0.02)
    mb.box((3.0, 0.8, 0.18), (dx, -d / 2 - 0.4, 0.09), m=mm["white"])
    # ground-floor shop shutters on some houses
    if rnd.random() < 0.5:
        for k in range(2):
            x = (-w / 2 + 1.6) if k == 0 else (w / 2 - 1.6)
            if abs(x - dx) < 2:
                continue
            mb.box((2.2, 0.1, 2.6), (x, -d / 2 - 0.05, 1.3), m=mm["roshan_" + rnd.choice(colours)])
            for q in range(10):
                mb.box((2.2, 0.03, 0.05), (x, -d / 2 - 0.11, 0.2 + q * 0.25), m=mm["timber"])
    # pierced roof parapet (Hijazi lattice of small openings)
    for (cx, cy, L, ang) in ((0, -d / 2, w, 0), (0, d / 2, w, 0), (w / 2, 0, d, 90), (-w / 2, 0, d, 90)):
        n = int(L / 0.5)
        c, s_ = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        for i in range(n + 1):
            u = -L / 2 + L * i / n
            mb.box((0.18, 0.25, 1.1), (cx + u * c, cy + u * s_, H + 0.55), (0, 0, ang), m=wall)
        mb.box((L + 0.25, 0.3, 0.2), (cx, cy, H + 1.2), (0, 0, ang), m=wall)
        mb.box((L + 0.25, 0.3, 0.25), (cx, cy, H + 0.12), (0, 0, ang), m=wall)
    # rooftop wooden pavilion (mabeet) on tall houses
    if floors >= 5 and rnd.random() < 0.7:
        r = roshan(mm, rnd.choice(colours), 3.0, 1, 2.8)
        mb.add_mb(r, (0, d / 4, H + 0.1), (0, 0, 0))
        r.bm.free()
    return mb.to_object(origin="base", sharp_angle=30)


def nassif_house(mm, name="SM_NassifHouse"):
    """Bayt Nassif (1872): 4-storey + roof pavilion, many rawasheen, the 'only tree in old Jeddah' in front."""
    mb = sr.MB(name)
    h = hijazi_house(mm, "nassif_core", 18.0, 15.0, 5, seed=77, stacks=4, side_stacks=1)
    mb.add_object(h)
    bpy.data.objects.remove(h, do_unlink=True)
    # the famous neem tree at the front
    rnd = random.Random(5)
    mb.tube([(-3.0, -12.0, 0), (-3.2, -12.2, 3.0), (-2.6, -12.0, 5.5)], [0.55, 0.45, 0.35], mm["bark"], seg=10)
    for k in range(5):
        a = 2 * math.pi * k / 5
        mb.tube([(-2.6, -12.0, 5.5), (-2.6 + 2.6 * math.cos(a), -12.0 + 2.6 * math.sin(a), 7.5 + rnd.uniform(-0.5, 0.8))],
                [0.3, 0.14], mm["bark"], seg=7)
    can = sr.MB("canopy")
    for k in range(22):
        c = (-2.6 + rnd.uniform(-4.5, 4.5), -12.0 + rnd.uniform(-4.0, 4.0), 8.0 + rnd.uniform(-1.2, 2.2))
        can.sphere(rnd.uniform(1.6, 2.6), c, m=mm["leaf"], seg=10, rings=6)
    co = can.to_object(uv=False)
    sr.remesh(co, 0.35)
    sr.displace(co, 0.6, 0.6, "VORONOI")
    mb.add_object(co)
    bpy.data.objects.remove(co, do_unlink=True)
    mb.lathe([(1.6, 0), (1.7, 0.45), (1.4, 0.5)], seg=24, loc=(-3.0, -12.0, 0), m=mm["white"])   # tree bed
    return mb.to_object(origin="base", sharp_angle=30)


def standalone_roshan(mm, name, floors, colour):
    r = roshan(mm, colour, 2.4, floors, 3.4, name=name)
    return r.to_object(origin="keep", sharp_angle=30)


# ---------------------------------------------------------------- landmarks ---
def minaret(mm, name="SM_HijaziMinaret"):
    mb = sr.MB(name)
    w = mm["white"]
    mb.box((4.2, 4.2, 9.0), (0, 0, 4.5), m=w)
    mb.box((4.6, 4.6, 0.4), (0, 0, 9.2), m=mm["green_trim"])
    # octagonal shaft
    rings = []
    for z, r in ((9.4, 1.9), (21.0, 1.65)):
        rings.append([(r * math.cos(math.pi / 8 + 2 * math.pi * i / 8), r * math.sin(math.pi / 8 + 2 * math.pi * i / 8), z) for i in range(8)])
    mb.loft(rings, w, closed=True, smooth=False)
    for k in range(8):
        a = math.pi / 8 + 2 * math.pi * k / 8 + math.pi / 8
        for z in (13.0, 17.5):
            mb.box((0.35, 0.12, 1.1), (1.78 * math.cos(a), 1.78 * math.sin(a), z), (0, 0, math.degrees(a) + 90), m=mm["dark"])
    # muezzin gallery: corbels, slab, balustrade
    for k in range(16):
        a = 2 * math.pi * k / 16
        mb.box((0.9, 0.18, 0.5), (2.0 * math.cos(a), 2.0 * math.sin(a), 20.8), (0, 30, math.degrees(a)), m=w)
    mb.cyl(2.7, 0.3, (0, 0, 21.2), m=w, seg=32)
    for k in range(32):
        a = 2 * math.pi * k / 32
        mb.box((0.08, 0.08, 1.0), (2.6 * math.cos(a), 2.6 * math.sin(a), 21.85), m=mm["green_trim"])
    mb.lathe([(2.65, 22.35), (2.65, 22.45)], seg=32, m=mm["green_trim"])
    # upper shaft + onion cap + crescent
    mb.cyl(1.3, 4.5, (0, 0, 23.6), m=w, seg=16)
    mb.lathe([(1.45, 25.9), (1.6, 26.6), (1.3, 27.6), (0.6, 28.4), (0.15, 29.0), (0.0, 29.1)], seg=24, m=mm["green_trim"])
    mb.cyl(0.05, 1.4, (0, 0, 29.7), m=mm["brass"], seg=8)
    mb.lathe([(0.3 + 0.05 * math.cos(t), 0.05 * math.sin(t)) for t in [2 * math.pi * k / 8 for k in range(9)]],
             seg=16, arc=250, loc=(0, 0, 30.6), rot=(90, 0, 0), m=mm["brass"])
    return mb.to_object(origin="base", sharp_angle=30)


def bab_makkah(mm, name="SM_BabMakkah"):
    mb = sr.MB(name)
    w = mm["white"]
    W, D, H = 14.0, 7.0, 9.0
    body = sr.MB("gate")
    body.box((W, D, H), (0, 0, H / 2), m=w)
    bo = body.to_object(uv=False)
    cut = sr.MB("arch")
    span, spring, rise = 5.0, 4.6, 2.2
    a = span / 2
    r = (a * a + rise * rise) / (2 * a) if rise >= a else (a * a + rise * rise) / (2 * rise)
    pts = [(-a, -1), (a, -1)]
    for i in range(25):
        x = a - span * i / 24
        if rise >= a:
            cx = -a + r if x < 0 else a - r
            pts.append((x, spring + math.sqrt(max(r * r - (x - cx) ** 2, 0))))
        else:
            cz = spring + rise - r
            pts.append((x, cz + math.sqrt(max(r * r - x * x, 0))))
    cut.prism(pts, -D, D, rot=(90, 0, 0), m=mm["paver"])
    sr.boolean(bo, cut.to_object(uv=False))
    mb.add_object(bo)
    bpy.data.objects.remove(bo, do_unlink=True)
    # flanking buttress towers
    for sg in (1, -1):
        mb.box((2.6, D + 1.0, H + 1.6), (sg * (W / 2 + 0.8), 0, (H + 1.6) / 2), m=w)
        for k in range(3):
            mb.box((0.5, 0.1, 1.2), (sg * (W / 2 + 0.8), -D / 2 - 0.52, 3 + k * 2.4), m=mm["dark"])
    # merlons + plaque + arch moulding
    from kit_riyadh import najdi_merlons
    najdi_merlons(mb, (-W / 2 - 2.1, -D / 2 - 0.4), (W / 2 + 2.1, -D / 2 - 0.4), H, w, step=0.9, thick=0.4, size=0.7)
    najdi_merlons(mb, (-W / 2 - 2.1, D / 2 + 0.4), (W / 2 + 2.1, D / 2 + 0.4), H, w, step=0.9, thick=0.4, size=0.7)
    mb.box((W + 4.6, D + 1.4, 0.3), (0, 0, H + 0.0), m=mm["green_trim"])
    mb.box((3.6, 0.15, 1.1), (0, -D / 2 - 0.08, spring + rise + 1.0), m=mm["green_trim"])
    mb.tube([(x, -D / 2 - 0.06, z + 0.1) for x, z in pts[2:]], 0.12, mm["timber"], seg=6)
    # heavy timber doors swung open
    for sg in (1, -1):
        mb.box((2.4, 0.18, 4.6), (sg * (a + 1.0), -D / 2 + 0.6, 2.3), (0, 0, sg * 70), m=mm["door"])
    return mb.to_object(origin="base", sharp_angle=30)


# -------------------------------------------------------------------- souq ---
def awning(mm, name="SM_SouqAwning", span=10.0, length=12.0):
    mb = sr.MB(name)
    n = 6
    for k in range(n):
        y0 = -length / 2 + k * length / n
        y1 = y0 + length / n - 0.15
        m = mm["cloth"][k % 3]
        rows = []
        for i in range(13):
            t = i / 12
            x = -span / 2 + span * t
            z = -0.6 * math.sin(math.pi * t)
            rows.append(((x, y0, z), (x, y1, z)))
        for i in range(12):
            a, b = rows[i], rows[i + 1]
            mb.poly([a[0], b[0], b[1], a[1]], m)
    for sg in (1, -1):
        mb.tube([(sg * span / 2, -length / 2, 0), (sg * span / 2, length / 2, 0)], 0.04, mm["wire"], seg=6)
    return mb.to_object(origin="keep", sharp_angle=None)


def lantern(mm, name="SM_Lantern"):
    mb = sr.MB(name)
    mb.cyl(0.012, 0.6, (0, 0, -0.3), m=mm["brass"], seg=6)
    rings = []
    for z, r in ((-0.62, 0.05), (-0.66, 0.16), (-0.9, 0.2), (-1.15, 0.16), (-1.22, 0.06)):
        rings.append([(r * math.cos(2 * math.pi * i / 8), r * math.sin(2 * math.pi * i / 8), z) for i in range(8)])
    mb.loft(rings, mm["lamp"], closed=True, cap_start=True, cap_end=True, smooth=False)
    for i in range(8):
        a = 2 * math.pi * i / 8
        mb.tube([(0.05 * math.cos(a), 0.05 * math.sin(a), -0.62), (0.2 * math.cos(a), 0.2 * math.sin(a), -0.9),
                 (0.06 * math.cos(a), 0.06 * math.sin(a), -1.22)], 0.008, mm["brass"], seg=4)
    mb.lathe([(0.0, -0.5), (0.12, -0.6), (0.18, -0.66)], seg=8, m=mm["brass"])
    return mb.to_object(origin="keep", sharp_angle=None)


def string_lights(mm, name="SM_StringLights", span=10.0):
    mb = sr.MB(name)
    n = 24
    pts = [(-span / 2 + span * i / n, 0, -0.9 * math.sin(math.pi * i / n)) for i in range(n + 1)]
    mb.tube(pts, 0.008, mm["wire"], seg=4)
    for p in pts[1:-1]:
        mb.sphere(0.045, (p[0], p[1], p[2] - 0.06), m=mm["bulb"], seg=8, rings=5)
    return mb.to_object(origin="keep", sharp_angle=None)


def souq_stall(mm, name="SM_SouqStall"):
    rnd = random.Random(3)
    mb = sr.MB(name)
    mb.box((2.4, 1.2, 0.85), (0, 0, 0.425), m=mm["door"])
    for k in range(24):
        x, y = rnd.uniform(-1.05, 1.05), rnd.uniform(-0.5, 0.5)
        m = rnd.choice(mm["goods"])
        if rnd.random() < 0.5:
            mb.sphere(rnd.uniform(0.07, 0.12), (x, y, 0.95), m=m, seg=8, rings=5)
        else:
            mb.box((0.18, 0.14, 0.12), (x, y, 0.92), (0, 0, rnd.uniform(0, 90)), m=m)
    for x in (-1.15, 1.15):
        for y in (-0.55, 0.55):
            mb.box((0.06, 0.06, 2.3), (x, y, 1.15), m=mm["timber"])
    mb.poly([(-1.3, -0.9, 2.1), (1.3, -0.9, 2.1), (1.3, 0.7, 2.4), (-1.3, 0.7, 2.4)], mm["cloth"][0])
    for k in range(3):   # hanging goods (baskets / lamps)
        mb.sphere(0.12, (-0.8 + k * 0.8, -0.75, 1.75), m=mm["goods"][k], seg=8, rings=5)
    return mb.to_object(origin="base", sharp_angle=None)


def markaz_bench(mm, name="SM_MarkazBench"):
    mb = sr.MB(name)
    mb.box((2.0, 0.9, 0.45), (0, 0, 0.225), m=mm["door"])
    for x in (-0.95, 0.95):
        mb.box((0.08, 0.9, 0.75), (x, 0, 0.375), m=mm["door"])
    mb.box((2.0, 0.08, 0.6), (0, 0.42, 0.75), m=mm["door"])
    mb.box((1.85, 0.8, 0.1), (0, 0, 0.5), m=mm["cushion_r"], bevel=0.03, seg=2)
    for k in range(3):
        mb.box((0.55, 0.18, 0.35), (-0.62 + k * 0.62, 0.3, 0.72), (10, 0, 0), m=mm["cushion_g"], bevel=0.05, seg=2)
    return mb.to_object(origin="base", sharp_angle=None)


def lane_paving(mm, name="SM_Lane_Paving_20m", L=20.0, W=10.0):
    mb = sr.MB(name)
    mb.box((L, W, 0.12), (0, 0, -0.06), m=mm["paver"])
    mb.box((L, 0.5, 0.06), (0, 0, 0.03), m=mm["white"])    # central drainage line
    return mb.to_object(origin="keep")


# -------------------------------------------------------------------- build ---
def build_all():
    sr.reset()
    mm = M()
    objs = []
    specs = [(10, 9, 4, 1, 2, 0), (8, 8, 3, 2, 1, 0), (12, 10, 5, 3, 2, 1), (9, 11, 4, 4, 2, 1), (14, 10, 6, 5, 3, 0), (7, 8, 3, 6, 1, 1)]
    for i, (w, d, f, sd, st, ss) in enumerate(specs):
        objs.append(hijazi_house(mm, f"SM_HijaziHouse_{i + 1:02d}", w, d, f, sd, st, ss))
    objs.append(nassif_house(mm))
    objs.append(standalone_roshan(mm, "SM_Roshan_2F", 2, "Teal"))
    objs.append(standalone_roshan(mm, "SM_Roshan_3F", 3, "Green"))
    objs += [minaret(mm), bab_makkah(mm), awning(mm), lantern(mm), string_lights(mm), souq_stall(mm),
             markaz_bench(mm), lane_paving(mm)]
    for o in objs:
        print(f"{o.name}: {sr.tri_count(o)} tris")
    return objs


def diorama(objs, out=None, cars=("JeddahGT", "Falcon")):
    """Sunset in a souq lane of Al-Balad: houses with rawasheen, awnings, lanterns, minaret."""
    by = {o.name: o for o in objs}
    for o in by.values():
        sr.hide(o)
    rnd = random.Random(21)
    for k in range(-1, 14):
        sr.inst(by["SM_Lane_Paving_20m"], (k * 20.0, 0, 0))
    houses = [by[f"SM_HijaziHouse_{i:02d}"] for i in range(1, 7)]
    for sg in (1, -1):
        x = -10.0
        while x < 260:
            h = rnd.choice(houses)
            o = sr.inst(h, (x, sg * 11.5, 0), (0, 0, 0 if sg > 0 else 180))     # main facade (-Y) faces the lane
            bpy.context.view_layer.update()
            lo, hi = sr.bounds([o])
            x += (hi.x - lo.x) + rnd.uniform(-0.3, 0.6)
    sr.inst(by["SM_NassifHouse"], (95, -27, 0), (0, 0, 180))
    sr.inst(by["SM_HijaziMinaret"], (150, 24, 0))
    sr.inst(by["SM_BabMakkah"], (230, 0, 0), (0, 0, 90))
    for k in range(4):
        sr.inst(by["SM_SouqAwning"], (40 + k * 14, 0, 7.5), (0, 0, 90))
        sr.inst(by["SM_StringLights"], (34 + k * 14, 0, 6.8), (0, 0, 90))
    for k in range(18):
        sr.inst(by["SM_Lantern"], (12 + k * 11, (-1) ** k * 5.2, 5.0))
        sr.point_light((12 + k * 11, (-1) ** k * 5.2, 3.9), 120, (1.0, 0.68, 0.35), 0.15)
    for k in range(10):
        sr.inst(by["SM_SouqStall"], (20 + k * 18, (-1) ** k * 4.4, 0), (0, 0, 90 if k % 2 else -90))
        sr.inst(by["SM_MarkazBench"], (28 + k * 18, (-1) ** k * 4.6, 0), (0, 0, 90 if k % 2 else -90))
    sr.ground(2000, sr.mat("Sand", (1, 1, 1), tex="Sand", tile=6), z=-0.13)
    for i, c in enumerate(cars):
        glb = os.path.join(sr.ROOT, "assets", "cars", c, f"{c}_preview.glb")
        if os.path.exists(glb):
            sr.import_glb(glb, ((14, 26)[i], (-1.8, 1.8)[i], 0.0), (0, 0)[i])
    sr.setup_render((1600, 900), 96, exposure=0.2)
    sr.world_sky(3, 260, 0.35)
    sr.sun((87, 0, 255), 4.0, (1.0, 0.55, 0.3), 1.0)
    sr.camera((-8, -3.5, 2.6), (80, 2, 8.5), 28)
    sr.render(out or os.path.join(sr.ROOT, "docs", "previews", "map_jeddah_albalad.png"))


if __name__ == "__main__":
    objs = build_all()
    sr.export_kit(objs, KIT)
    sr.write_manifest()
