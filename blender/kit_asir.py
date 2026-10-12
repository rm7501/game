"""Sahara Racers - ASIR MOUNTAINS map kit (Abha, Rijal Almaa, Al-Soudah).

  SM_RijalAlmaaHouse_01..04   stacked-stone tower houses: white-painted window surrounds, coloured
                              shutters, white stepped crenellations, slight batter
  SM_RijalAlmaaVillage        hillside cluster of tower houses (terraced platforms)
  SM_AsiriMudTower_A/B        mud 'qasaba' towers with protruding slate rain ledges (rafaf)
  SM_QattDoor                 door painted with Al-Qatt Al-Asiri geometric art (UNESCO heritage)
  SM_TerraceHill              terraced farming hillside (stone retaining walls + green fields)
  SM_AsirMountain_A/B         escarpment mountains (rock on steep slopes, green on ledges)
  SM_Juniper_A/B              Arar juniper trees (Asir highlands)
  SM_CableCar_Pylon / _Cabin  Abha cable car
  SM_Road_Mountain_25m        2-lane mountain road with stone gutter
  SM_Guardrail_10m            W-beam guardrail with reflectors
  SM_TunnelPortal             cut-stone tunnel portal + 30 m tube
  SM_RetainingWall_20m        dry-stone retaining wall
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))
import sr  # noqa: E402

import bpy  # noqa: E402
from mathutils import Vector, noise  # noqa: E402

KIT = "asir"
TEXOUT = os.path.join(sr.ROOT, "assets", KIT, "textures")


def make_textures():
    """Al-Qatt Al-Asiri door art: bands of triangles, chevrons and diamonds in bold colours."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return
    os.makedirs(TEXOUT, exist_ok=True)
    W, H = 512, 1024
    im = Image.new("RGB", (W, H), (245, 240, 225))
    d = ImageDraw.Draw(im)
    pal = [(200, 30, 40), (30, 120, 60), (250, 200, 30), (40, 80, 170), (230, 110, 30), (20, 20, 20), (120, 40, 140)]
    rnd = random.Random(4)
    y = 0
    band = 0
    while y < H:
        h = rnd.choice((48, 64, 80))
        kind = band % 4
        c1, c2 = rnd.sample(pal, 2)
        d.rectangle([0, y, W, y + h], fill=c1)
        n = W // h * 2
        if kind == 0:      # triangles
            for i in range(n + 1):
                x = i * h / 2 * 2
                d.polygon([(x, y + h), (x + h / 2, y), (x + h, y + h)], fill=c2)
        elif kind == 1:    # diamonds
            for i in range(n + 1):
                x = i * h
                d.polygon([(x, y + h / 2), (x + h / 2, y), (x + h, y + h / 2), (x + h / 2, y + h)], fill=c2)
        elif kind == 2:    # chevrons
            for i in range(n + 1):
                x = i * h / 1.5
                d.line([(x, y + h), (x + h / 3, y + 4), (x + 2 * h / 3, y + h)], fill=c2, width=10)
        else:              # vertical stripes
            for i in range(0, W, 24):
                d.rectangle([i, y, i + 10, y + h], fill=c2)
        d.line([(0, y), (W, y)], fill=(20, 20, 20), width=5)
        y += h
        band += 1
    im.save(os.path.join(TEXOUT, "T_QattAsiri.png"))


def M():
    return dict(
        stone=sr.mat("Asir_StoneMasonry", (1.25, 1.2, 1.15), rough=0.9, tex="StoneMasonry", tile=2.4),
        stone_dark=sr.mat("Asir_StoneDark", (0.72, 0.7, 0.68), rough=0.9, tex="StoneMasonry", tile=2.0),
        white=sr.mat("Asir_WhitePaint", (0.94, 0.94, 0.9), rough=0.7, tex="Concrete", tile=2.0),
        mud=sr.mat("Asir_MudPlaster", (0.9, 0.78, 0.66), tex="MudPlaster", tile=2.5),
        slate=sr.mat("Asir_Slate", (0.3, 0.29, 0.28), rough=0.85, tex="Rock", tile=1.0),
        dark=sr.mat("WindowDarkHole", (0.02, 0.015, 0.01), rough=0.9),
        shutters=[sr.mat(f"Asir_Shutter_{n}", c, rough=0.6, tex="WoodPainted", tile=0.8) for n, c in
                  (("Green", (0.1, 0.45, 0.2)), ("Red", (0.65, 0.1, 0.08)), ("Blue", (0.12, 0.3, 0.6)),
                   ("Yellow", (0.85, 0.65, 0.1)), ("Turquoise", (0.1, 0.55, 0.55)))],
        rock=sr.mat("Asir_Granite", (1, 1, 1), rough=0.9, tex="Rock", tile=6.0),
        grass=sr.mat("Asir_TerraceGrass", (1, 1, 1), rough=0.95, tex="TerraceGrass", tile=4.0),
        juniper=sr.mat("Juniper_Foliage", (0.13, 0.22, 0.14), rough=0.8, kind="foliage"),
        bark=sr.mat("Juniper_Bark", (0.32, 0.24, 0.2), rough=0.95, tex="Rock", tile=1.0),
        steel=sr.mat("SteelGalvanised", (0.55, 0.56, 0.58), rough=0.45, metal=1.0),
        red=sr.mat("CableCar_Red", (0.7, 0.08, 0.06), rough=0.35, coat=0.6),
        glass=sr.mat("Car_Glass", (0.02, 0.025, 0.03), rough=0.02, metal=0.0, transmission=0.7, kind="glass"),
        asphalt=sr.mat("Asphalt", (1, 1, 1), tex="Asphalt", tile=4.0),
        line_w=sr.mat("RoadLineWhite", (0.9, 0.9, 0.88), rough=0.5),
        line_y=sr.mat("RoadLineYellow", (0.85, 0.65, 0.1), rough=0.5),
        reflect=sr.mat("ReflectorAmber", (0.9, 0.5, 0.1), emit=(1, 0.5, 0.1), emit_str=1.0),
        concrete=sr.mat("Concrete", (1, 1, 1), tex="Concrete", tile=2.0),
        tunnel_light=sr.mat("TunnelLight", (1.0, 0.85, 0.6), emit=(1.0, 0.8, 0.55), emit_str=10, kind="emissive"),
    )


# ------------------------------------------------------------ Rijal Almaa ---
def white_crenellations(mb, a, b, z, m, size=0.55, step=0.7):
    """Stepped white merlons (same family as Najdi ones, smaller and sharper in Asir)."""
    from kit_riyadh import najdi_merlons
    najdi_merlons(mb, a, b, z, m, step=step, thick=0.35, size=size)


def rijal_house(mm, name, w=8.0, d=7.0, floors=5, seed=1, mb=None, loc=(0, 0, 0), rot=0.0):
    rnd = random.Random(seed)
    own = mb is None
    mb = mb or sr.MB(name)
    fh = 3.0
    H = floors * fh
    bat = 0.03                                            # batter: walls lean in with height
    ox, oy, oz = loc
    c, s_ = math.cos(math.radians(rot)), math.sin(math.radians(rot))

    def P(x, y, z):
        return (ox + x * c - y * s_, oy + x * s_ + y * c, oz + z)
    # battered stone body
    rings = []
    for z in (0.0, H):
        k = 1 - bat * z / H * 2
        rings.append([P(sx * w / 2 * k, sy * d / 2 * k, z) for sx, sy in ((1, -1), (1, 1), (-1, 1), (-1, -1))])
    mb.loft(rings, mm["stone"], closed=True, cap_end=True, smooth=False)
    # quartz-white corner strips + floor bands
    for f in range(1, floors):
        z = f * fh
        k = 1 - bat * z / H * 2
        mb.box((w * k + 0.08, d * k + 0.08, 0.16), P(0, 0, z), (0, 0, rot), m=mm["white"])
    # windows: white painted surround + coloured shutters (front and sides)
    faces = [((0, -1), w, d), ((1, 0), d, w), ((-1, 0), d, w)]
    for (nx, ny), L, D2 in faces:
        n = max(1, int(L / 2.6))
        for f in range(floors):
            z = f * fh + 1.6
            k = 1 - bat * z / H * 2
            for i in range(n):
                if rnd.random() < 0.25:
                    continue
                u = (-L / 2 + (i + 0.5) * L / n) * k
                tx, ty = -ny, nx
                ex = nx * (D2 / 2 * k + 0.02) + tx * u
                ey = ny * (D2 / 2 * k + 0.02) + ty * u
                ang = math.degrees(math.atan2(ny, nx)) + 90
                ww, wh = (0.75, 0.95) if f > 0 else (0.6, 0.7)
                mb.box((ww + 0.7, 0.04, wh + 0.75), P(ex, ey, z), (0, 0, ang + rot), m=mm["white"])
                mb.box((ww, 0.06, wh), P(ex + nx * 0.02, ey + ny * 0.02, z), (0, 0, ang + rot), m=mm["dark"])
                sh = rnd.choice(mm["shutters"])
                for sg in (1, -1):    # open shutters
                    hx = ex + tx * sg * (ww / 2 + ww / 4) + nx * 0.06
                    hy = ey + ty * sg * (ww / 2 + ww / 4) + ny * 0.06
                    mb.box((ww / 2, 0.05, wh), P(hx, hy, z), (0, 0, ang + rot + sg * 15), m=sh)
                # triangle 'eye' decoration above some windows
                if rnd.random() < 0.5:
                    mb.prism([(-0.25, 0), (0.25, 0), (0, 0.3)], 0, 0.05, P(ex + nx * 0.02, ey + ny * 0.02, z + wh / 2 + 0.45),
                             (90, 0, ang + rot), m=mm["white"])
    # door painted in Al-Qatt Al-Asiri style
    qatt = sr.mat("QattAsiri_Door", (1, 1, 1), rough=0.6, image=os.path.join(TEXOUT, "T_QattAsiri.png"))
    dx = rnd.uniform(-w / 4, w / 4)
    yd = -d / 2 - 0.03
    p0, p1, p2, p3 = P(dx - 0.6, yd, 0.05), P(dx + 0.6, yd, 0.05), P(dx + 0.6, yd, 2.25), P(dx - 0.6, yd, 2.25)
    mb.quad_uv([p0, p1, p2, p3], ((0, 0), (1, 0), (1, 1), (0, 1)), qatt)
    mb.box((1.6, 0.05, 2.6), P(dx, yd + 0.02, 1.25), (0, 0, rot), m=mm["white"])
    # roof: white stepped crenellations + corner horns
    k = 1 - bat * 2
    corners = [(w / 2 * k, -d / 2 * k), (w / 2 * k, d / 2 * k), (-w / 2 * k, d / 2 * k), (-w / 2 * k, -d / 2 * k)]
    for i in range(4):
        a, b = corners[i], corners[(i + 1) % 4]
        pa = P(a[0], a[1], 0)
        pb = P(b[0], b[1], 0)
        mb.box((abs(b[0] - a[0]) + 0.3 if abs(b[0] - a[0]) > 0.1 else 0.3, abs(b[1] - a[1]) + 0.3 if abs(b[1] - a[1]) > 0.1 else 0.3, 0.6),
               P((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, H + 0.3), (0, 0, rot), m=mm["white"])
        white_crenellations(mb, (pa[0], pa[1]), (pb[0], pb[1]), oz + H + 0.6, mm["white"])
        mb.prism([(-0.3, 0), (0.3, 0), (0, 1.4)], -0.3, 0.3, P(a[0], a[1], H + 0.6), (90, 0, rot + 45), m=mm["white"])
    if own:
        return mb.to_object(origin="base", sharp_angle=30)


def rijal_village(mm, name="SM_RijalAlmaaVillage"):
    rnd = random.Random(9)
    mb = sr.MB(name)
    # stepped platforms down a slope
    for row in range(4):
        z = row * 4.0
        y = row * 10.0
        mb.box((60, 10.5, z + 1.0), (0, y, (z + 1.0) / 2), m=mm["stone_dark"])
        x = -26.0
        while x < 26:
            w = rnd.uniform(6, 9)
            dd = rnd.uniform(6, 8)
            rijal_house(mm, "h", w, dd, rnd.randint(3, 7), seed=200 + row * 20 + int(x), mb=mb, loc=(x + w / 2, y, z + 1.0),
                        rot=rnd.uniform(-4, 4))
            x += w + rnd.uniform(0.0, 1.5)
    return mb.to_object(origin="base", sharp_angle=30)


def mud_tower(mm, name, H=12.0, w=6.5, seed=1):
    """Asiri qasaba: tapering mud tower with slate ledges every 35 cm shedding the monsoon rain."""
    rnd = random.Random(seed)
    mb = sr.MB(name)
    top = 0.72
    rings = [[(sx * w / 2 * (1 - (1 - top) * z / H), sy * w / 2 * (1 - (1 - top) * z / H), z)
              for sx, sy in ((1, -1), (1, 1), (-1, 1), (-1, -1))] for z in (0, H)]
    mb.loft(rings, mm["mud"], closed=True, cap_end=True, smooth=False)
    z = 0.6
    while z < H - 0.6:
        k = 1 - (1 - top) * z / H
        ww = w * k + 0.32
        mb.box((ww, ww, 0.05), (0, 0, z), (0, 0, rnd.uniform(-0.5, 0.5)), m=mm["slate"])
        z += 0.36
    # small windows with white frames on each side
    for f in range(int(H / 3)):
        zz = 1.8 + f * 3.0
        k = 1 - (1 - top) * zz / H
        for (nx, ny) in ((0, -1), (1, 0), (0, 1), (-1, 0)):
            if rnd.random() < 0.3:
                continue
            ang = math.degrees(math.atan2(ny, nx)) + 90
            px, py = nx * (w / 2 * k + 0.17), ny * (w / 2 * k + 0.17)
            mb.box((0.9, 0.04, 1.1), (px, py, zz), (0, 0, ang), m=mm["white"])
            mb.box((0.5, 0.06, 0.65), (px + nx * 0.02, py + ny * 0.02, zz), (0, 0, ang), m=mm["dark"])
    kt = top * w / 2
    corners = [(kt, -kt), (kt, kt), (-kt, kt), (-kt, -kt)]
    for i in range(4):
        white_crenellations(mb, corners[i], corners[(i + 1) % 4], H, mm["white"], size=0.6, step=0.75)
    return mb.to_object(origin="base", sharp_angle=30)


def qatt_door(mm, name="SM_QattDoor"):
    qatt = sr.mat("QattAsiri_Door", (1, 1, 1), rough=0.6, image=os.path.join(TEXOUT, "T_QattAsiri.png"))
    mb = sr.MB(name)
    mb.box((1.6, 0.25, 2.7), (0, 0.12, 1.35), m=mm["white"])
    mb.quad_uv([(-0.6, -0.02, 0.05), (0.6, -0.02, 0.05), (0.6, -0.02, 2.25), (-0.6, -0.02, 2.25)], ((0, 0), (1, 0), (1, 1), (0, 1)), qatt)
    return mb.to_object(origin="base")


# --------------------------------------------------------------- landscape ---
def slope_material(obj, steep_mat, flat_mat, thresh=0.72):
    me = obj.data
    names = [m.name for m in me.materials]
    for m in (steep_mat, flat_mat):
        if m.name not in names:
            me.materials.append(m)
            names.append(m.name)
    si, fi = names.index(steep_mat.name), names.index(flat_mat.name)
    for p in me.polygons:
        p.material_index = fi if p.normal.z > thresh else si
    return obj


def terrace_hill(mm, name="SM_TerraceHill", size=120.0):
    mb = sr.MB(name)
    step = 2.2

    def fn(x, y):
        r = math.hypot(x, y * 1.2)
        h = max(0.0, 24 * (1 - (r / (size * 0.55)) ** 1.4))
        h += 3 * noise.noise(Vector((x * 0.02, y * 0.02, 0.5)))
        q = math.floor(h / step)
        frac = h / step - q
        # terrace: flat shelf then a steep (retaining wall) riser in the last 18 %
        t = 0.0 if frac < 0.82 else (frac - 0.82) / 0.18
        return max(0.0, (q + t) * step)
    mb.grid(fn, 240, 240, -size / 2, size / 2, -size / 2, size / 2, m=mm["grass"], smooth=False)
    o = mb.to_object(origin="keep", sharp_angle=None)
    slope_material(o, mm["stone"], mm["grass"], 0.8)
    return o


def mountain(mm, name, size=900.0, height=420.0, seed=1):
    mb = sr.MB(name)
    off = Vector((seed * 7.0, seed * 3.0, 0))

    def fn(x, y):
        p = Vector((x, y, 0)) / size * 3.0 + off
        ridge = 1 - abs(noise.noise(p, noise_basis="PERLIN_NEW"))
        ridge2 = 1 - abs(noise.noise(p * 2.3 + Vector((2, 7, 0)), noise_basis="PERLIN_NEW"))
        base = noise.fractal(p * 0.7, 0.6, 2.0, 6, noise_basis="PERLIN_NEW")
        e = max(0.0, 1 - (max(abs(x), abs(y)) / (size / 2)) ** 4)
        # escarpment: steep drop on the -Y side (towards Tihama)
        esc = 0.5 + 0.5 * math.tanh((y + size * 0.1) / (size * 0.08))
        return (height * (0.35 * ridge ** 2 + 0.2 * ridge2 ** 3 + 0.15 * base) * e) * (0.35 + 0.65 * esc)
    mb.grid(fn, 160, 160, -size / 2, size / 2, -size / 2, size / 2, m=mm["rock"], smooth=True)
    o = mb.to_object(origin="keep", sharp_angle=None)
    slope_material(o, mm["rock"], mm["grass"], 0.66)
    return o


def juniper(mm, name, H=7.0, seed=1):
    rnd = random.Random(seed)
    mb = sr.MB(name)
    mb.tube([(0, 0, 0), (0.2, 0.1, H * 0.35), (0.0, 0.0, H * 0.7)], [0.28, 0.2, 0.1], mm["bark"], seg=8)
    can = sr.MB("c")
    for k in range(16):
        z = rnd.uniform(H * 0.3, H)
        r = (H - z) / H * 2.6 + 0.6
        a = rnd.uniform(0, 2 * math.pi)
        can.sphere(rnd.uniform(0.9, 1.5) * (0.6 + 0.4 * r / 3), (math.cos(a) * r * 0.5, math.sin(a) * r * 0.5, z), m=mm["juniper"], seg=10, rings=6)
    co = can.to_object(uv=False)
    sr.remesh(co, 0.22)
    sr.displace(co, 0.45, 0.35, "VORONOI")
    mb.add_object(co)
    bpy.data.objects.remove(co, do_unlink=True)
    return mb.to_object(origin="base", sharp_angle=None)


# ------------------------------------------------------------------ cable car ---
def cable_pylon(mm, name="SM_CableCar_Pylon", H=32.0):
    mb = sr.MB(name)
    for sx in (1, -1):
        for sy in (1, -1):
            mb.tube([(sx * 2.5, sy * 2.5, 0), (sx * 0.8, sy * 0.8, H)], 0.12, mm["steel"], seg=8)
    n = 10
    for k in range(n):
        z0, z1 = H * k / n, H * (k + 1) / n
        r0, r1 = 2.5 - 1.7 * k / n, 2.5 - 1.7 * (k + 1) / n
        for (ax, ay, bx, by) in ((1, 1, 1, -1), (1, -1, -1, -1), (-1, -1, -1, 1), (-1, 1, 1, 1)):
            mb.tube([(ax * r0, ay * r0, z0), (bx * r1, by * r1, z1)], 0.05, mm["steel"], seg=5)
    mb.box((9, 1.0, 0.8), (0, 0, H + 0.4), m=mm["steel"])
    for sg in (1, -1):
        mb.cyl(0.5, 0.25, (sg * 4.0, 0, H + 1.0), (90, 0, 0), m=mm["red"], seg=16)
    return mb.to_object(origin="base", sharp_angle=40)


def cable_cabin(mm, name="SM_CableCar_Cabin"):
    mb = sr.MB(name)
    rings = []
    for z, s in ((0, 0.8), (0.3, 1.0), (1.9, 1.0), (2.3, 0.82)):
        rings.append([(1.3 * s * math.cos(2 * math.pi * i / 16) * (1 + 0.12 * abs(math.cos(2 * math.pi * i / 16))),
                       1.0 * s * math.sin(2 * math.pi * i / 16), z) for i in range(16)])
    mb.loft(rings, mm["red"], closed=True, cap_start=True, cap_end=True, smooth=True,
            mats=lambda j, i: mm["glass"] if j == 1 else mm["red"])
    mb.cyl(0.08, 2.2, (0, 0, 3.4), m=mm["steel"], seg=8)
    mb.box((1.2, 0.3, 0.3), (0, 0, 4.5), m=mm["steel"])
    return mb.to_object(origin="base", sharp_angle=None)


# ------------------------------------------------------------------- roads ---
def road_mountain(mm, name="SM_Road_Mountain_25m", L=25.0):
    mb = sr.MB(name)
    mb.box((L, 8.0, 0.12), (0, 0, -0.06), m=mm["asphalt"])
    for sg in (1, -1):
        mb.box((L, 0.15, 0.012), (0, sg * 3.65, 0.006), m=mm["line_w"])
        mb.box((L, 0.8, 0.3), (0, sg * 4.4, -0.15), (sg * 12, 0, 0), m=mm["concrete"])   # stone gutter
    for k in range(int(L / 6)):
        mb.box((3.0, 0.12, 0.012), (-L / 2 + 1.5 + k * 6, 0, 0.006), m=mm["line_y"])
    return mb.to_object(origin="keep")


def guardrail(mm, name="SM_Guardrail_10m", L=10.0):
    mb = sr.MB(name)
    for k in range(int(L / 2) + 1):
        x = -L / 2 + k * 2.0
        mb.box((0.1, 0.15, 1.0), (x, 0, 0.5), m=mm["steel"])
        mb.box((0.04, 0.08, 0.12), (x, -0.2, 0.75), m=mm["reflect"])
    prof = [(0.0, 0.55), (-0.1, 0.6), (-0.04, 0.68), (-0.1, 0.76), (0.0, 0.81)]
    rings = [[(x, y - 0.1, z) for y, z in prof] for x in (-L / 2, L / 2)]
    mb.loft(rings, mm["steel"], closed=False, smooth=True)
    return mb.to_object(origin="base")


def tunnel_portal(mm, name="SM_TunnelPortal"):
    mb = sr.MB(name)
    W, H = 11.0, 7.2
    # cut-stone portal wall with arch opening
    wall = sr.MB("wall")
    wall.box((20, 2.0, 12), (0, 0, 6), m=mm["stone"])
    wo = wall.to_object(uv=False)
    cut = sr.MB("arch")
    pts = [(-W / 2, -1), (W / 2, -1), (W / 2, 4.2)]
    for i in range(1, 24):
        a = math.pi * i / 24
        pts.append((W / 2 * math.cos(a), 4.2 + (H - 4.2) * math.sin(a)))
    pts.append((-W / 2, 4.2))
    cut.prism(pts, -3, 3, rot=(90, 0, 0), m=mm["concrete"])
    sr.boolean(wo, cut.to_object(uv=False))
    mb.add_object(wo)
    bpy.data.objects.remove(wo, do_unlink=True)
    # voussoir ring
    for i in range(25):
        a = math.pi * i / 24
        mb.box((0.9, 2.3, 0.6), (W / 2 * 1.06 * math.cos(a), 0, 4.2 + (H - 4.2) * 1.08 * math.sin(a)),
               (0, -math.degrees(a) + 90, 0), m=mm["stone_dark"])
    # tunnel tube (inside faces) + lights
    rings = []
    for y in (0.9, 30.0):
        ring = [(W / 2, y, 0), (W / 2, y, 4.2)] + [(W / 2 * math.cos(math.pi * i / 16), y, 4.2 + (H - 4.2) * math.sin(math.pi * i / 16)) for i in range(1, 16)] + [(-W / 2, y, 4.2), (-W / 2, y, 0)]
        rings.append(ring)
    faces = mb.loft(rings, mm["concrete"], closed=False, smooth=True)
    mb.flip(faces)
    for k in range(6):
        mb.box((1.2, 0.3, 0.12), (0, 3 + k * 5, H - 0.1), m=mm["tunnel_light"])
    mb.box((W + 0.2, 30, 0.1), (0, 15.5, -0.05), m=mm["asphalt"])
    return mb.to_object(origin="base", sharp_angle=35)


def retaining_wall(mm, name="SM_RetainingWall_20m", L=20.0):
    mb = sr.MB(name)
    prof = [(0, 0), (1.2, 0), (0.6, 4.0), (0.0, 4.0)]
    rings = [[(x, y, z) for y, z in prof] for x in (-L / 2, L / 2)]
    mb.loft(rings, mm["stone"], closed=True, cap_start=True, cap_end=True, smooth=False)
    mb.box((L, 0.7, 0.25), (0, 0.3, 4.1), m=mm["concrete"])
    return mb.to_object(origin="base")


# --------------------------------------------------------------------- build ---
def build_all():
    sr.reset()
    make_textures()
    mm = M()
    objs = []
    for i, (w, d, f, sd) in enumerate(((8, 7, 5, 1), (6.5, 6.5, 4, 2), (9, 7.5, 7, 3), (7, 6, 3, 4))):
        objs.append(rijal_house(mm, f"SM_RijalAlmaaHouse_{i + 1:02d}", w, d, f, sd))
    objs.append(rijal_village(mm))
    objs.append(mud_tower(mm, "SM_AsiriMudTower_A", 12.0, 6.5, 1))
    objs.append(mud_tower(mm, "SM_AsiriMudTower_B", 16.0, 7.5, 2))
    objs.append(qatt_door(mm))
    objs.append(terrace_hill(mm))
    objs.append(mountain(mm, "SM_AsirMountain_A", 900, 420, 1))
    objs.append(mountain(mm, "SM_AsirMountain_B", 700, 300, 2))
    objs.append(juniper(mm, "SM_Juniper_A", 7.0, 1))
    objs.append(juniper(mm, "SM_Juniper_B", 4.5, 2))
    objs += [cable_pylon(mm), cable_cabin(mm), road_mountain(mm), guardrail(mm), tunnel_portal(mm), retaining_wall(mm)]
    for o in objs:
        print(f"{o.name}: {sr.tri_count(o)} tris")
    return objs


def diorama(objs, out=None, cars=("NajdiGXR", "HiluxRaider")):
    """Misty morning on an Asir mountain road: Rijal Almaa village, terraces, cable car, escarpment."""
    by = {o.name: o for o in objs}
    for o in by.values():
        sr.hide(o)
    rnd = random.Random(31)
    for k in range(-1, 24):
        sr.inst(by["SM_Road_Mountain_25m"], (k * 25.0, 0, 0.1))
        if k % 2 == 0:
            sr.inst(by["SM_Guardrail_10m"], (k * 25.0, -4.9, 0.1))
    sr.inst(by["SM_TunnelPortal"], (420, 0, 0), (0, 0, -90))
    sr.inst(by["SM_RijalAlmaaVillage"], (150, 50, 0), (0, 0, 180))
    sr.inst(by["SM_AsiriMudTower_B"], (70, 18, 0))
    sr.inst(by["SM_AsiriMudTower_A"], (95, 24, 0))
    sr.inst(by["SM_TerraceHill"], (300, 140, -1), (0, 0, 20))
    sr.inst(by["SM_TerraceHill"], (130, -78, -3), (0, 0, 70))
    sr.inst(by["SM_TerraceHill"], (260, -150, -2), (0, 0, 140))
    sr.inst(by["SM_AsirMountain_A"], (620, 220, -25), (0, 0, 10))
    sr.inst(by["SM_AsirMountain_B"], (560, -330, -40), (0, 0, 120))
    sr.inst(by["SM_AsirMountain_A"], (900, 700, -40), (0, 0, 200))
    sr.inst(by["SM_RetainingWall_20m"], (40, 7.5, 0), (0, 0, 180))
    sr.inst(by["SM_RetainingWall_20m"], (60, 7.5, 0), (0, 0, 180))
    for k in range(60):
        x, y = rnd.uniform(0, 400), rnd.uniform(-120, 150)
        if abs(y) < 10:
            continue
        sr.inst(by[rnd.choice(("SM_Juniper_A", "SM_Juniper_B"))], (x, y, 0), (0, 0, rnd.uniform(0, 360)), scale=rnd.uniform(0.8, 1.3))
    # cable car line across the valley
    p0, p1 = Vector((120, -80, 0)), Vector((330, 200, 30))
    for t in (0.0, 0.5, 1.0):
        sr.inst(by["SM_CableCar_Pylon"], tuple(p0.lerp(p1, t)), (0, 0, math.degrees(math.atan2(p1.y - p0.y, p1.x - p0.x)) + 90))
    for t in (0.22, 0.7):
        p = p0.lerp(p1, t) + Vector((0, 0, 28))
        sr.inst(by["SM_CableCar_Cabin"], tuple(p))
    cab = sr.MB("cables")
    cab.tube([tuple(p0 + Vector((0, 0, 33))), tuple(p0.lerp(p1, 0.5) + Vector((0, 0, 33))), tuple(p1 + Vector((0, 0, 33)))],
             0.05, sr.mat("SteelDark", (0.08, 0.08, 0.09), rough=0.4, metal=1.0), seg=5)
    cab.to_object()
    sr.ground(5000, sr.mat("Asir_TerraceGrass", (1, 1, 1), rough=0.95, tex="TerraceGrass", tile=4.0), z=-0.05)
    for i, c in enumerate(cars):
        glb = os.path.join(sr.ROOT, "assets", "cars", c, f"{c}_preview.glb")
        if os.path.exists(glb):
            sr.import_glb(glb, ((16, 32)[i], (-1.9, 1.9)[i], 0.1), (0, 180)[i])
    # morning mist: thin volumetric box over the valley
    fog = sr.MB("Mist")
    fog.box((3000, 3000, 140), (0, 0, 60), m=None)
    fo = fog.to_object(uv=False)
    vm = bpy.data.materials.new("MistVolume")
    vm.use_nodes = True
    nt = vm.node_tree
    nt.nodes.clear()
    o = nt.nodes.new("ShaderNodeOutputMaterial")
    v = nt.nodes.new("ShaderNodeVolumePrincipled")
    v.inputs["Density"].default_value = 0.0016
    v.inputs["Color"].default_value = (0.85, 0.9, 1.0, 1)
    nt.links.new(v.outputs[0], o.inputs["Volume"])
    fo.data.materials.clear()
    fo.data.materials.append(vm)
    sr.setup_render((1600, 900), 64, exposure=0.35)
    bpy.context.scene.cycles.volume_step_rate = 4.0
    sr.world_sky(14, 120, 0.3)
    sr.sun((70, 0, 130), 5.0, (1.0, 0.88, 0.74), 2.0)
    sr.camera((-12, -3.5, 3.0), (200, 30, 25), 30)
    sr.render(out or os.path.join(sr.ROOT, "docs", "previews", "map_asir_mountains.png"))


if __name__ == "__main__":
    objs = build_all()
    sr.export_kit(objs, KIT)
    sr.write_manifest()
