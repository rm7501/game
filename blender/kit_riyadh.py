"""Sahara Racers - RIYADH NIGHTS map kit.

Landmarks (real-world scale, metres):
  SM_KingdomCentre        302 m, lens-plan tower with parabolic opening + sky bridge, LED-lit arch
  SM_KingdomMall          podium mall at the tower base
  SM_AlFaisaliah          267 m, four converging legs, golden globe, spire
  SM_RiyadhTVTower        170 m concrete TV tower with observation pod
  SM_PIFTower             385 m faceted crystal tower (KAFD) with LED diamond lines
  SM_KAFD_Twist / _Slant / _Diagrid / _Stepped   KAFD skyline towers
  SM_Masmak               Masmak fortress (mud brick, round towers, Najdi merlons, palm-wood gate)
  SM_RiyadhBlock_01..06   Najdi-modern mid-rises: triangle parapets, lit windows, shops, roof tanks
Road & street:
  SM_Road_KingFahd_25m    6-lane boulevard segment with median (UVs match T_RoadLanes, 12 m tile)
  SM_StreetLight_KFR      14 m double-arm LED street light
  SM_Gantry_KFR           overhead gantry with green Arabic/English direction signs
  SM_MetroViaduct_30m     Riyadh Metro elevated viaduct segment (tulip pier)
  SM_MetroCar             Riyadh Metro car (Line 1 blue)
  SM_Billboard_LED        digital billboard
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))
import sr  # noqa: E402

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

KIT = "riyadh"
OUT = os.path.join(sr.ROOT, "assets", KIT)
TEXOUT = os.path.join(OUT, "textures")


# ------------------------------------------------------------------ signs ---
def make_textures():
    try:
        from PIL import Image, ImageDraw, ImageFont, features
    except ImportError:
        return
    os.makedirs(TEXOUT, exist_ok=True)
    bold = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    raqm = features.check("raqm")
    if not raqm:
        import arabic_reshaper
        from bidi.algorithm import get_display
    ar = (lambda s: s) if raqm else (lambda s: get_display(arabic_reshaper.reshape(s)))
    green = (0, 105, 62)

    def arrow(d, cx, cy, s, ang):
        a = math.radians(ang)
        pts = [(0, -1.0), (0.55, -0.25), (0.2, -0.25), (0.2, 1.0), (-0.2, 1.0), (-0.2, -0.25), (-0.55, -0.25)]
        rp = [(cx + s * (x * math.cos(a) - y * math.sin(a)), cy + s * (x * math.sin(a) + y * math.cos(a))) for x, y in pts]
        d.polygon(rp, fill=(255, 255, 255))

    signs = [("T_Sign_KingFahd", "طريق الملك فهد", "King Fahd Rd", 0, None),
             ("T_Sign_Kingdom", "برج المملكة", "Kingdom Centre", 45, "5"),
             ("T_Sign_KAFD", "المركز المالي", "KAFD", 45, "7"),
             ("T_Sign_Olaya", "العليا", "Olaya", -45, "6")]
    for fname, arabic, english, ang, exitno in signs:
        W, H = 1024, 512
        im = Image.new("RGB", (W, H), green)
        d = ImageDraw.Draw(im)
        d.rounded_rectangle([10, 10, W - 11, H - 11], 30, outline=(255, 255, 255), width=10)
        fa = ImageFont.truetype(bold, 120)
        fe = ImageFont.truetype(bold, 92)
        for txt, f, cy in ((ar(arabic), fa, 165), (english, fe, 340)):
            l, t, r, b = d.textbbox((0, 0), txt, font=f)
            d.text((W * 0.42 - (r - l) / 2 - l, cy - (b - t) / 2 - t), txt, font=f, fill=(255, 255, 255))
        arrow(d, W - 150, H / 2, 110, ang)
        if exitno:
            d.rectangle([40, H - 120, 330, H - 40], fill=(245, 245, 245))
            fx = ImageFont.truetype(bold, 52)
            d.text((60, H - 112), f"EXIT {exitno}", font=fx, fill=green)
        im.save(os.path.join(TEXOUT, fname + ".png"))
    # LED billboard (Riyadh Season style gradient + calligraphic-ish title)
    W, H = 1024, 512
    im = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(im)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)], fill=(int(120 + 120 * t), int(20 + 30 * t), int(160 - 80 * t)))
    for k in range(40):
        rnd = random.Random(k)
        x, y, r = rnd.randint(0, W), rnd.randint(0, H), rnd.randint(4, 14)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 220, 120))
    f = ImageFont.truetype(bold, 150)
    txt = ar("موسم الرياض")
    l, t, r, b = d.textbbox((0, 0), txt, font=f)
    d.text(((W - (r - l)) / 2 - l, 120 - t), txt, font=f, fill=(255, 255, 255))
    f = ImageFont.truetype(bold, 70)
    txt = "SAHARA RACERS  ·  NIGHT GP"
    l, t, r, b = d.textbbox((0, 0), txt, font=f)
    d.text(((W - (r - l)) / 2 - l, 360 - t), txt, font=f, fill=(255, 240, 200))
    im.save(os.path.join(TEXOUT, "T_Billboard_RiyadhSeason.png"))


# -------------------------------------------------------------- materials ---
def M():
    return dict(
        facade=sr.mat("Riyadh_FacadeNight", (1, 1, 1), rough=0.1, metal=0.6, tex="FacadeNight", tile=24.0, emit_str=2.0),
        facade_dim=sr.mat("KC_FacadeNight", (0.8, 0.85, 0.95), rough=0.08, metal=0.7, tex="FacadeTower", tile=24.0, emit_str=1.6),
        kc_led=sr.mat("KC_ArchLED", (0.35, 0.3, 1.0), emit=(0.35, 0.25, 1.0), emit_str=9.0, kind="emissive"),
        kc_bridge=sr.mat("KC_BridgeLight", (0.9, 0.95, 1.0), emit=(0.85, 0.92, 1.0), emit_str=12.0, kind="emissive"),
        red=sr.mat("AviationRed", (0.6, 0.0, 0.0), emit=(1, 0.02, 0.0), emit_str=20, kind="emissive"),
        concrete=sr.mat("Concrete", (1, 1, 1), tex="Concrete", tile=2.0),
        concrete_lt=sr.mat("ConcreteWarm", (1.0, 0.95, 0.86), tex="Concrete", tile=4.0),
        gold=sr.mat("Faisaliah_GoldGlass", (0.95, 0.7, 0.3), rough=0.12, metal=1.0, emit=(1.0, 0.65, 0.25), emit_str=3.0),
        led_green=sr.mat("LED_Green", (0.1, 0.8, 0.4), emit=(0.15, 1.0, 0.45), emit_str=10, kind="emissive"),
        led_white=sr.mat("LED_White", (0.9, 0.95, 1.0), emit=(0.85, 0.9, 1.0), emit_str=10, kind="emissive"),
        led_amber=sr.mat("LED_Amber", (1.0, 0.55, 0.15), emit=(1.0, 0.55, 0.15), emit_str=12, kind="emissive"),
        glass_dark=sr.mat("GlassDark", (0.03, 0.04, 0.06), rough=0.05, metal=0.8),
        limestone=sr.mat("Limestone", (0.9, 0.8, 0.64), tex="MudPlaster", tile=3.0),
        mud=sr.mat("MudBrick", (1.0, 0.95, 0.9), tex="MudPlaster", tile=3.0),
        wood=sr.mat("PalmWood", (0.42, 0.3, 0.2), rough=0.8, tex="WoodPainted", tile=1.0),
        win_warm=sr.mat("Win_LitWarm", (0.25, 0.18, 0.12), emit=(1.0, 0.72, 0.42), emit_str=1.1, kind="emissive"),
        win_cool=sr.mat("Win_LitCool", (0.2, 0.22, 0.26), emit=(0.8, 0.88, 1.0), emit_str=0.9, kind="emissive"),
        win_dark=sr.mat("Win_Dark", (0.02, 0.025, 0.035), rough=0.05, metal=0.7),
        frame=sr.mat("WindowFrameDark", (0.06, 0.05, 0.045), rough=0.6),
        steel=sr.mat("SteelDark", (0.08, 0.08, 0.09), rough=0.4, metal=1.0),
        galv=sr.mat("SteelGalvanised", (0.55, 0.56, 0.58), rough=0.45, metal=1.0),
        white=sr.mat("PaintWhite", (0.85, 0.85, 0.83), rough=0.5),
        tank=sr.mat("WaterTank", (0.8, 0.82, 0.85), rough=0.45),
        tank_blue=sr.mat("WaterTankBlue", (0.15, 0.3, 0.55), rough=0.45),
        road=sr.mat("RoadLanes", (1, 1, 1), tex="RoadLanes", tile=12.0),
        asphalt=sr.mat("Asphalt", (1, 1, 1), tex="Asphalt", tile=4.0),
        curb=sr.mat("CurbPaint", (0.85, 0.85, 0.8), rough=0.6),
        curb_blk=sr.mat("CurbBlack", (0.05, 0.05, 0.05), rough=0.6),
        paver=sr.mat("Paver", (0.85, 0.75, 0.62), tex="Concrete", tile=1.0),
        sand=sr.mat("Sand", (1, 1, 1), tex="Sand", tile=6),
        metro_white=sr.mat("Metro_White", (0.9, 0.9, 0.9), rough=0.3, metal=0.2, coat=0.6),
        metro_blue=sr.mat("Metro_Line1Blue", (0.0, 0.32, 0.72), rough=0.3, coat=0.6),
        metro_win=sr.mat("Metro_Window", (0.7, 0.8, 0.9), emit=(0.8, 0.88, 1.0), emit_str=3.5, kind="emissive"),
    )


# ----------------------------------------------------------- Kingdom Centre ---
def kingdom_centre(mm, name="SM_KingdomCentre"):
    H = 302.0
    A0, B0 = 38.0, 19.0          # semi-axes of the ellipse plan at the base (broad x, narrow y)

    def A(z):                    # broad half-width: straight, then the parabolic shoulder
        if z < 110:
            return A0 - 0.6 * z / 110
        t = (z - 110) / (H - 110)
        return A0 - 0.6 - 13.5 * t ** 1.9

    def B(z):                    # narrow half-depth
        if z < 150:
            return B0
        t = (z - 150) / (H - 150)
        return B0 - 8.5 * t ** 1.5

    z0, Htip = 183.0, 22.6       # opening starts at 183 m, reaches the tips at the top

    def h(z):
        return 0.0 if z <= z0 else Htip * math.sqrt((z - z0) / (H - z0))

    mb = sr.MB("kc_body")
    seg = 96
    rings = []
    nz = 101
    for j in range(nz):
        z = H * j / (nz - 1)
        a, b = A(z), B(z)
        rings.append([(a * math.cos(2 * math.pi * i / seg), b * math.sin(2 * math.pi * i / seg), z) for i in range(seg)])
    mb.loft(rings, mm["facade_dim"], closed=True, cap_start=True, cap_end=True, smooth=True)
    body = mb.to_object(uv=True, sharp_angle=60)
    # parabolic opening (cut faces become LED-lit soffits)
    cut = sr.MB("kc_cut")
    poly = []
    for k in range(40):
        z = z0 + (H + 30 - z0) * (k / 39) ** 1.5
        poly.append((h(min(z, H)) + (z - H if z > H else 0) * 0.5, z))
    poly = [(x, z) for x, z in poly]
    full = [(-x, z) for x, z in reversed(poly)] + poly[1:]
    cut.prism(full, -40, 40, rot=(90, 0, 0), m=mm["kc_led"])
    sr.boolean(body, cut.to_object(uv=False))
    mb2 = sr.MB(name)
    mb2.add_object(body)
    bpy.data.objects.remove(body, do_unlink=True)
    # sky bridge (300 m), slightly bowed, with light strip
    zb = 289.0
    span = 2 * h(zb) + 4
    for k in range(12):
        x0 = -span / 2 + span * k / 12
        x1 = x0 + span / 12
        zc0 = zb - 1.5 * (1 - (2 * (x0 + span / 12 / 2) / span) ** 2)
        mb2.box((span / 12 + 0.05, 7.0, 4.0), ((x0 + x1) / 2, 0, zc0), m=mm["glass_dark"])
        mb2.box((span / 12 + 0.05, 7.2, 0.5), ((x0 + x1) / 2, 0, zc0 - 2.0), m=mm["kc_bridge"])
    # aviation lights on the tips
    for sg in (1, -1):
        mb2.sphere(0.8, (sg * (A(H) + h(H)) / 2, 0, H + 0.5), m=mm["red"], seg=8, rings=6)
    # floor-line LED bands on the outer edges of the opening rim
    return mb2.to_object(origin="base", sharp_angle=60)


def kingdom_mall(mm, name="SM_KingdomMall"):
    mb = sr.MB(name)
    L, Wd, Hh = 190.0, 82.0, 20.0
    # stadium-shaped plan (rounded ends) built as a loft of rounded rectangles
    def plan(inset):
        pts = []
        r = Wd / 2 - inset
        for k in range(48):
            a = 2 * math.pi * k / 48
            x = math.cos(a)
            y = math.sin(a)
            px = (L / 2 - Wd / 2) * (1 if x > 0 else -1) + r * x
            pts.append((px, r * y))
        return pts
    rings = []
    for z, inset in ((0, 0), (5.5, 0), (5.5, 1.5), (14, 1.5), (14, 0), (Hh, 0)):
        rings.append([(x, y, z) for x, y in plan(inset)])
    mats = {0: mm["glass_dark"], 1: mm["limestone"], 2: mm["win_warm"], 3: mm["limestone"], 4: mm["limestone"]}
    mb.loft(rings, closed=True, cap_end=True, smooth=False, mats=lambda j, i: mats[j])
    # shopfront glazing bars
    for k in range(48):
        a = 2 * math.pi * k / 48
        x, y = math.cos(a), math.sin(a)
        px = (L / 2 - Wd / 2) * (1 if x > 0 else -1) + (Wd / 2 + 0.05) * x
        mb.box((0.4, 0.4, 5.5), (px, (Wd / 2 + 0.05) * y, 2.75), (0, 0, math.degrees(a)), m=mm["steel"])
    # roof skylights
    for k in range(6):
        mb.box((14, 10, 1.2), (-60 + k * 24, 0, Hh + 0.6), m=mm["kc_bridge"])
    return mb.to_object(origin="base")


# ------------------------------------------------------------ Al Faisaliah ---
def al_faisaliah(mm, name="SM_AlFaisaliah"):
    Hap = 245.0
    S0 = 27.0
    zg = 168.0                   # top of the glazed office body

    def c(z):
        return S0 * max(0.0, 1 - z / Hap) ** 0.5

    mb = sr.MB(name)
    # four legs (rhombic section, pointing outward)
    nz = 60
    for sx, sy in ((1, 1), (-1, 1), (-1, -1), (1, -1)):
        rings = []
        for j in range(nz + 1):
            z = Hap * j / nz
            cc = c(z)
            w = 1.2 + 4.0 * (cc / S0) ** 0.8
            o = 0.9 + 0.8 * (cc / S0)
            pts = [(cc + o, cc + o), (cc - w, cc + o * 0.4), (cc - w * 0.6, cc - w * 0.6), (cc + o * 0.4, cc - w)]
            ring = [(sx * x, sy * y, z) for x, y in pts]
            if sx * sy < 0:
                ring = list(reversed(ring))
            rings.append(ring)
        mb.loft(rings, mm["concrete_lt"], closed=True, cap_start=True, smooth=False)
        # LED strip along the outer edge
        mb.tube([(sx * (c(z) + 0.9 + 0.8 * c(z) / S0 + 0.15), sy * (c(z) + 0.9 + 0.8 * c(z) / S0 + 0.15), z)
                 for z in [Hap * k / 30 for k in range(31)]], 0.25, mm["led_green"], seg=6, caps=False)
    # glazed body (pyramid frustum between the legs)
    rings = []
    for j in range(31):
        z = zg * j / 30
        cc = c(z) - 1.6
        rings.append([(cc, cc, z), (-cc, cc, z), (-cc, -cc, z), (cc, -cc, z)])
    mb.loft(rings, mm["facade"], closed=True, cap_end=True, smooth=False)
    # ring beams in the open crown + platform
    for z in (zg + 2, 222.0):
        cc = c(z)
        mb.box((2 * cc, 2 * cc, 1.6), (0, 0, z), m=mm["concrete_lt"])
    # golden globe (24 m) + slab
    mb.sphere(12.0, (0, 0, 196.0), m=mm["gold"], seg=48, rings=24)
    for k in range(4):   # meridian mullions
        mb.lathe([(12.1 * math.sin(math.pi * i / 16), 196 + 12.1 * math.cos(math.pi * i / 16)) for i in range(17)],
                 seg=2, arc=4, rot=(0, 0, 45 * k), m=mm["steel"], smooth=False)
    # spire to 267 m
    mb.cyl(0.9, 25, (0, 0, Hap + 10), m=mm["galv"], seg=12, r2=0.15)
    mb.sphere(0.6, (0, 0, 267.5), m=mm["red"], seg=8, rings=6)
    # entrance canopy / plaza block
    mb.box((70, 70, 1.0), (0, 0, 0.5), m=mm["paver"])
    return mb.to_object(origin="base", sharp_angle=35)


# ----------------------------------------------------------------- TV tower ---
def tv_tower(mm, name="SM_RiyadhTVTower"):
    mb = sr.MB(name)
    prof = [(13, 0), (11, 3), (8, 10), (6.2, 25), (5.2, 60), (4.6, 108), (5.5, 118), (8.5, 126), (14.5, 131),
            (15, 134), (14.5, 137), (12, 140), (11.5, 146), (9.5, 150), (6, 153), (2.5, 155)]
    mb.lathe(prof, seg=48, m=mm["concrete_lt"], close_top=True)
    mb.lathe([(15.05, 132), (15.05, 136)], seg=48, m=mm["win_cool"])
    mb.lathe([(11.6, 141.5), (11.6, 145)], seg=48, m=mm["win_warm"])
    for k in range(3):     # vertical light fins on the shaft
        a = 2 * math.pi * k / 3
        mb.box((0.5, 0.5, 95), (5.25 * math.cos(a), 5.25 * math.sin(a), 60), (0, 0, math.degrees(a)), m=mm["led_white"])
    mb.cyl(0.8, 18, (0, 0, 164), m=mm["galv"], seg=10, r2=0.2)
    mb.sphere(0.5, (0, 0, 173.2), m=mm["red"], seg=8, rings=6)
    return mb.to_object(origin="base", sharp_angle=40)


# ---------------------------------------------------------------- PIF Tower ---
def pif_tower(mm, name="SM_PIFTower"):
    """385 m crystalline tower: octagon rings alternately rotated -> diamond facets; LED facet edges."""
    mb = sr.MB(name)
    Hb, Ht = 318.0, 385.0
    n_side = 8
    bands = 18
    rings, edges = [], []
    for j in range(bands + 1):
        z = Hb * j / bands
        r = 30 - 4.0 * (z / Hb) ** 1.3
        rot = (math.pi / n_side) * (j % 2)
        ring = []
        for i in range(n_side):
            a = rot + 2 * math.pi * i / n_side
            # chamfered-square character: stretch cardinal directions
            k = 1.0 + 0.08 * math.cos(4 * a)
            ring.append((r * k * math.cos(a), r * k * math.sin(a), z))
        rings.append(ring)
    # anti-prism bands (triangles) for true diamond faceting
    vr = [[mb.bm.verts.new(Vector(p)) for p in ring] for ring in rings]
    m_i = mm["facade"]
    for j in range(bands):
        A, Bv = vr[j], vr[j + 1]
        for i in range(n_side):
            i2 = (i + 1) % n_side
            if j % 2 == 0:
                f1 = mb.bm.faces.new((A[i], A[i2], Bv[i]))
                f2 = mb.bm.faces.new((A[i2], Bv[i2], Bv[i]))
            else:
                f1 = mb.bm.faces.new((A[i], A[i2], Bv[i2]))
                f2 = mb.bm.faces.new((A[i], Bv[i2], Bv[i]))
            mb._tag([f1, f2], m_i, False)
    # crown: rings converge to a faceted point
    top = rings[-1]
    crown = []
    for j in range(1, 5):
        t = j / 4
        z = Hb + (Ht - Hb) * t ** 0.8
        sc = (1 - t) ** 1.2
        rot = (math.pi / n_side) * ((bands + j) % 2)
        ring = []
        for i in range(n_side):
            a = rot + 2 * math.pi * i / n_side
            r = 26 * sc + 0.3
            ring.append((r * math.cos(a), r * math.sin(a), z))
        crown.append(ring)
    prev = vr[-1]
    for j, ring in enumerate(crown):
        nv = [mb.bm.verts.new(Vector(p)) for p in ring]
        for i in range(n_side):
            i2 = (i + 1) % n_side
            if (bands + j) % 2 == 0:
                fs = [mb.bm.faces.new((prev[i], prev[i2], nv[i])), mb.bm.faces.new((prev[i2], nv[i2], nv[i]))]
            else:
                fs = [mb.bm.faces.new((prev[i], prev[i2], nv[i2])), mb.bm.faces.new((prev[i], nv[i2], nv[i]))]
            mb._tag(fs, mm["glass_dark"] if j > 0 else m_i, False)
        prev = nv
    f = mb.bm.faces.new(prev)
    mb._tag([f], mm["glass_dark"], False)
    # LED lines along every facet edge (diamond lattice glow)
    allr = rings + crown
    for i in range(n_side):
        path = []
        for j in range(len(allr)):
            p = Vector(allr[j][i])
            out = Vector((p.x, p.y, 0)).normalized() * 0.35
            path.append(tuple(p + out))
        mb.tube(path, 0.3, mm["led_white"], seg=5, caps=False)
    for j in range(0, len(allr), 2):
        ring = allr[j] + [allr[j][0]]
        mb.tube([tuple(Vector(p) + Vector((p[0], p[1], 0)).normalized() * 0.35) for p in ring], 0.25,
                mm["led_white"], seg=5, caps=False)
    mb.cyl(0.6, 12, (0, 0, Ht + 5), m=mm["galv"], seg=8, r2=0.1)
    return mb.to_object(origin="base", sharp_angle=20)


def kafd_twist(mm, name="SM_KAFD_Twist", H=230.0, half=17.0, turns=0.25):
    mb = sr.MB(name)
    rings = []
    n = 60
    for j in range(n + 1):
        z = H * j / n
        a0 = 2 * math.pi * turns * j / n
        rings.append([(half * 1.414 * math.cos(a0 + math.pi / 4 + k * math.pi / 2),
                       half * 1.414 * math.sin(a0 + math.pi / 4 + k * math.pi / 2), z) for k in range(4)])
    mb.loft(rings, mm["facade"], closed=True, cap_end=True, smooth=False)
    for k in range(4):   # corner LED fins
        mb.tube([tuple(Vector(rings[j][k]) * 1.01) for j in range(0, n + 1, 3)], 0.3, mm["led_white"], seg=5, caps=False)
    mb.box((half * 1.2, half * 1.2, 6), (0, 0, H + 3), m=mm["steel"])
    return mb.to_object(origin="base", sharp_angle=20)


def kafd_slant(mm, name="SM_KAFD_Slant", H=190.0):
    mb = sr.MB(name)
    W, D = 44.0, 26.0
    poly = [(-W / 2, -D / 2), (W / 2, -D / 2), (W / 2, D / 2), (-W / 2, D / 2)]
    rings = [[(x, y, 0) for x, y in poly], [(x, y, H - 30 + 30 * (x + W / 2) / W) for x, y in poly]]
    mb.loft(rings, mm["facade"], closed=True, cap_end=True, smooth=False)
    for k in range(12):   # vertical fins on the broad faces
        x = -W / 2 + 2 + k * (W - 4) / 11
        top = H - 30 + 30 * (x + W / 2) / W
        for sg in (1, -1):
            mb.box((0.6, 1.4, top), (x, sg * (D / 2 + 0.7), top / 2), m=mm["concrete_lt"])
    mb.tube([(-W / 2, -D / 2 - 0.5, H - 30), (W / 2, -D / 2 - 0.5, H)], 0.4, mm["led_amber"], seg=6)
    mb.tube([(-W / 2, D / 2 + 0.5, H - 30), (W / 2, D / 2 + 0.5, H)], 0.4, mm["led_amber"], seg=6)
    return mb.to_object(origin="base", sharp_angle=20)


def kafd_diagrid(mm, name="SM_KAFD_Diagrid", H=260.0):
    mb = sr.MB(name)
    rings = []
    seg = 32
    for j in range(41):
        z = H * j / 40
        r = 21 - 3 * math.sin(math.pi * z / H) + (-4 if z > H * 0.9 else 0) * (z - H * 0.9) / (H * 0.1)
        rings.append([(r * 1.25 * math.cos(2 * math.pi * i / seg), r * math.sin(2 * math.pi * i / seg), z) for i in range(seg)])
    mb.loft(rings, mm["facade"], closed=True, cap_end=True, smooth=True)
    # external diagrid
    for i in range(0, seg, 2):
        for sgn in (1, -1):
            path = []
            for j in range(0, 41, 2):
                ii = (i + sgn * j // 2) % seg
                p = Vector(rings[j][ii])
                path.append(tuple(p + Vector((p.x, p.y, 0)).normalized() * 0.8))
            mb.tube(path, 0.45, mm["concrete_lt"], seg=5, caps=False)
    return mb.to_object(origin="base", sharp_angle=30)


def kafd_stepped(mm, name="SM_KAFD_Stepped"):
    mb = sr.MB(name)
    z = 0.0
    for (w, d, h) in ((50, 36, 70), (42, 30, 55), (34, 24, 45), (24, 18, 30)):
        mb.box((w, d, h), (0, 0, z + h / 2), m=mm["facade"])
        mb.box((w + 1, d + 1, 1.2), (0, 0, z + h), m=mm["led_white"])
        z += h
    mb.cyl(0.8, 30, (0, 0, z + 15), m=mm["galv"], seg=8, r2=0.2)
    return mb.to_object(origin="base", sharp_angle=20)


# ------------------------------------------------------------------- Masmak ---
def najdi_merlons(mb, p0, p1, z, m, step=1.1, thick=0.9, size=0.75):
    """Stepped triangular Najdi crenellations along a wall top from p0 to p1."""
    p0, p1 = Vector(p0), Vector(p1)
    L = (p1 - p0).length
    n = max(1, int(L / step))
    ang = math.degrees(math.atan2(p1.y - p0.y, p1.x - p0.x))
    s = size
    poly = [(-s / 2, 0), (s / 2, 0), (s / 2, s * 0.35), (s * 0.28, s * 0.35), (s * 0.28, s * 0.68), (s * 0.08, s * 0.68),
            (s * 0.08, s), (-s * 0.08, s), (-s * 0.08, s * 0.68), (-s * 0.28, s * 0.68), (-s * 0.28, s * 0.35), (-s / 2, s * 0.35)]
    for k in range(n):
        c = p0.lerp(p1, (k + 0.5) / n)
        mb.prism(poly, -thick / 2, thick / 2, (c.x, c.y, z), (90, 0, ang), m=m)


def masmak(mm, name="SM_Masmak"):
    mb = sr.MB(name)
    mud = mm["mud"]
    W, D, Hw, t = 56.0, 50.0, 9.5, 2.2
    corners = [(-W / 2, -D / 2), (W / 2, -D / 2), (W / 2, D / 2), (-W / 2, D / 2)]
    # battered walls
    for k in range(4):
        a, b = Vector(corners[k] + (0,)), Vector(corners[(k + 1) % 4] + (0,))
        mid = (a + b) / 2
        L = (b - a).length
        ang = math.degrees(math.atan2(b.y - a.y, b.x - a.x))
        prof = [(-t / 2 - 0.4, 0), (t / 2 + 0.4, 0), (t / 2, Hw), (-t / 2, Hw)]
        rings = []
        for x in (-L / 2, L / 2):
            rings.append([(x, y, z) for y, z in prof])
        tmp = sr.MB("wall")
        tmp.loft(rings, mud, closed=True, cap_start=True, cap_end=True, smooth=False)
        mb.add_mb(tmp, (mid.x, mid.y, 0), (0, 0, ang))
        tmp.bm.free()
        nrm = Vector((-(b.y - a.y), b.x - a.x, 0)).normalized()
        najdi_merlons(mb, a.xy + nrm.xy * 0.0, b.xy, Hw, mud, thick=0.7)
        # triangular vent holes band + drain spouts
        for q in range(int(L / 3)):
            p = a.lerp(b, (q + 0.5) / int(L / 3)) - nrm * (t / 2 + 0.05)
            mb.prism([(-0.25, 0), (0.25, 0), (0, 0.45)], -0.08, 0.08, (p.x, p.y, Hw - 1.6), (90, 0, ang), m=mm["frame"])
            if q % 3 == 1:
                mb.cyl(0.12, 1.4, tuple(p - nrm * 0.5 + Vector((0, 0, Hw - 2.4))), (90, 0, ang + 90), m=mm["wood"], seg=8)
    # four round corner towers (tapering, merlons, slit windows)
    for (x, y) in corners:
        Ht = 17.0
        prof = [(5.0, 0), (4.6, Ht * 0.6), (4.2, Ht), (4.5, Ht + 0.3), (4.5, Ht + 0.6), (4.2, Ht + 0.6)]
        mb.lathe(prof, seg=36, loc=(x, y, 0), m=mud, close_top=True, smooth=True)
        for k in range(14):
            a = 2 * math.pi * k / 14
            najdi_merlons(mb, (x + 4.25 * math.cos(a) - 0.6 * math.sin(a), y + 4.25 * math.sin(a) + 0.6 * math.cos(a)),
                          (x + 4.25 * math.cos(a) + 0.6 * math.sin(a), y + 4.25 * math.sin(a) - 0.6 * math.cos(a)),
                          Ht + 0.6, mud, step=1.2, thick=0.5, size=0.7)
        for lvl in (6.0, 11.0):
            for k in range(4):
                a = 2 * math.pi * (k + 0.5) / 4
                r = 4.55 if lvl < 9 else 4.4
                mb.box((0.3, 0.3, 1.1), (x + r * math.cos(a), y + r * math.sin(a), lvl), (0, 0, math.degrees(a)), m=mm["frame"])
    # main watchtower (square, tallest) at the front-left
    tx, ty = -W / 2 + 12, -D / 2 + 4
    prof = []
    rings = [[(tx + sx * (5 - z * 0.04), ty + sy * (5 - z * 0.04), z) for sx, sy in ((1, 1), (-1, 1), (-1, -1), (1, -1))]
             for z in (0, 20.0)]
    mb.loft(rings, mud, closed=True, cap_end=True, smooth=False)
    for k in range(4):
        sx, sy = ((1, 1), (-1, 1), (-1, -1), (1, -1))[k]
        nx, ny = ((-1, 1), (-1, -1), (1, -1), (1, 1))[k]
        najdi_merlons(mb, (tx + sx * 4.2, ty + sy * 4.2), (tx + nx * 4.2, ty + ny * 4.2), 20.0, mud, thick=0.6)
    # gate: recessed frame + palm-wood door with studs + wicket door
    gx, gy = 6.0, -D / 2 - 0.5
    mb.box((7.5, 1.6, 7.5), (gx, gy + 0.2, 3.75), m=mud, bevel=0.1)
    mb.box((4.2, 0.4, 5.6), (gx, gy - 0.5, 2.8), m=mm["wood"])
    for i in range(6):
        for j in range(8):
            mb.sphere(0.06, (gx - 1.75 + i * 0.7, gy - 0.72, 0.5 + j * 0.65), m=mm["galv"], seg=6, rings=4)
    mb.box((1.0, 0.1, 1.5), (gx + 0.9, gy - 0.72, 0.85), m=mm["frame"])
    # warm floodlights at the base (the fort is lit from below at night)
    for k in range(10):
        a = 2 * math.pi * k / 10
        mb.box((0.6, 0.6, 0.3), (math.cos(a) * (W / 2 + 6), math.sin(a) * (D / 2 + 6), 0.15), m=mm["led_amber"])
    # courtyard ground
    mb.box((W, D, 0.2), (0, 0, 0.1), m=mm["sand"])
    return mb.to_object(origin="base", sharp_angle=35)


# ------------------------------------------------------------ Riyadh blocks ---
def riyadh_block(mm, name, w=30.0, d=22.0, floors=7, seed=1, style=0):
    """Najdi-modern mid-rise: limestone, vertical slit windows (some lit), triangle parapet, roof clutter."""
    rnd = random.Random(seed)
    mb = sr.MB(name)
    fh = 3.6
    gh = 5.0
    H = gh + floors * fh
    wall = [mm["limestone"], mm["concrete_lt"], mm["mud"]][style % 3]
    mb.box((w, d, H), (0, 0, H / 2), m=wall)
    # ground floor shops: glazing + sign band
    sign_cols = [(0.1, 0.6, 1.0), (1.0, 0.3, 0.2), (0.2, 1.0, 0.5), (1.0, 0.8, 0.2), (0.8, 0.3, 1.0)]
    for side, (L, nrm, ang) in enumerate(((w, (0, -1), 0), (d, (1, 0), 90), (w, (0, 1), 180), (d, (-1, 0), 270))):
        n = max(1, int(L / 6))
        cx = nrm[0] * (w / 2) if nrm[0] else 0
        cy = nrm[1] * (d / 2) if nrm[1] else 0
        tx, ty = -nrm[1], nrm[0]
        for k in range(n):
            o = -L / 2 + (k + 0.5) * L / n
            p = Vector((cx + tx * o + nrm[0] * 0.06, cy + ty * o + nrm[1] * 0.06, 0))
            mb.box((L / n - 0.8, 0.12, 3.4), (p.x, p.y, 1.9), (0, 0, ang), m=mm["win_warm"] if rnd.random() < 0.7 else mm["win_cool"])
            col = sign_cols[rnd.randrange(len(sign_cols))]
            sm = sr.mat(f"ShopSign_{sign_cols.index(col)}", col, emit=col, emit_str=4, kind="emissive")
            mb.box((L / n - 1.4, 0.3, 0.8), (p.x + nrm[0] * 0.1, p.y + nrm[1] * 0.1, 4.2), (0, 0, ang), m=sm)
        # upper floor windows (vertical slits in pairs, Najdi rhythm)
        bays = max(1, int(L / 3.2))
        for f in range(floors):
            z = gh + f * fh + fh * 0.55
            for k in range(bays):
                o = -L / 2 + (k + 0.5) * L / bays
                if style == 1 and k % 3 == 1:
                    continue
                p = Vector((cx + tx * o + nrm[0] * 0.04, cy + ty * o + nrm[1] * 0.04, z))
                r_ = rnd.random()
                m = mm["win_warm"] if r_ < 0.42 else mm["win_cool"] if r_ < 0.55 else mm["win_dark"]
                mb.box((1.1, 0.1, 2.0), tuple(p), (0, 0, ang), m=m)
                mb.box((1.4, 0.16, 0.18), (p.x, p.y, z - 1.1), (0, 0, ang), m=mm["frame"])
        # vertical Najdi pilaster strips on the corners
        for sgn in (-1, 1):
            o = sgn * (L / 2 - 0.4)
            mb.box((0.8, 0.25, H - gh), (cx + tx * o + nrm[0] * 0.12, cy + ty * o + nrm[1] * 0.12, gh + (H - gh) / 2),
                   (0, 0, ang), m=wall)
    # parapet with triangle merlons + triangle vent band
    corners = [(-w / 2, -d / 2), (w / 2, -d / 2), (w / 2, d / 2), (-w / 2, d / 2)]
    for k in range(4):
        a, b = corners[k], corners[(k + 1) % 4]
        mb.box((abs(b[0] - a[0]) + 0.3 if a[1] == b[1] else 0.3, abs(b[1] - a[1]) + 0.3 if a[0] == b[0] else 0.3, 1.0),
               ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, H + 0.5), m=wall)
        najdi_merlons(mb, a, b, H + 1.0, wall, step=1.0, thick=0.3, size=0.7)
    # roof clutter: water tanks, AC units, satellite dishes
    for k in range(rnd.randint(3, 6)):
        x, y = rnd.uniform(-w / 2 + 3, w / 2 - 3), rnd.uniform(-d / 2 + 3, d / 2 - 3)
        m = mm["tank"] if rnd.random() < 0.6 else mm["tank_blue"]
        if rnd.random() < 0.5:
            mb.cyl(0.9, 1.8, (x, y, H + 0.9), m=m, seg=16)
        else:
            mb.cyl(0.7, 2.6, (x, y, H + 0.9), (90, 0, rnd.uniform(0, 180)), m=m, seg=16)
    for k in range(rnd.randint(4, 8)):
        x, y = rnd.uniform(-w / 2 + 2, w / 2 - 2), rnd.uniform(-d / 2 + 2, d / 2 - 2)
        mb.box((1.0, 0.7, 0.8), (x, y, H + 0.4), (0, 0, rnd.choice((0, 90))), m=mm["white"])
    for k in range(rnd.randint(2, 5)):
        x, y = rnd.uniform(-w / 2 + 1.5, w / 2 - 1.5), rnd.uniform(-d / 2 + 1.5, d / 2 - 1.5)
        mb.lathe([(0.0, 0.0), (0.4, 0.05), (0.7, 0.2), (0.75, 0.25)], seg=16, loc=(x, y, H + 1.2),
                 rot=(rnd.uniform(40, 60), 0, rnd.uniform(0, 360)), m=mm["white"])
        mb.cyl(0.04, 1.2, (x, y, H + 0.6), m=mm["galv"], seg=6)
    return mb.to_object(origin="base", sharp_angle=30)


# --------------------------------------------------------------- road kit ---
def road_kingfahd(mm, name="SM_Road_KingFahd_25m", L=25.0):
    """Two 3-lane carriageways (12 m each) + 4 m planted median + curbs + 3 m sidewalks. Runs along X."""
    mb = sr.MB(name)
    med = 4.0
    cw = 12.0
    sw = 3.0
    y_med = med / 2
    for sg in (1, -1):
        y0, y1 = sg * y_med, sg * (y_med + cw)
        # lane texture: u across the carriageway (0 = median side), v along the road (12 m tile)
        lo, hi = (y0, y1) if sg > 0 else (y1, y0)
        if sg > 0:
            pts = [(-L / 2, lo, 0), (L / 2, lo, 0), (L / 2, hi, 0), (-L / 2, hi, 0)]
            uv = ((0, -L / 2 / cw), (0, L / 2 / cw), (1, L / 2 / cw), (1, -L / 2 / cw))
        else:
            pts = [(-L / 2, lo, 0), (L / 2, lo, 0), (L / 2, hi, 0), (-L / 2, hi, 0)]
            uv = ((1, -L / 2 / cw), (1, L / 2 / cw), (0, L / 2 / cw), (0, -L / 2 / cw))
        mb.quad_uv(pts, uv, mm["road"])
        # outer curb + sidewalk
        yc = sg * (y_med + cw + 0.15)
        mb.box((L, 0.3, 0.2), (0, yc, 0.1), m=mm["curb"])
        mb.box((L, sw, 0.2), (0, sg * (y_med + cw + 0.3 + sw / 2), 0.1), m=mm["paver"])
    # median: alternating black/white painted curbs, sand planter
    for k in range(int(L / 1.0)):
        x = -L / 2 + 0.5 + k
        for sg in (1, -1):
            mb.box((1.0, 0.25, 0.3), (x, sg * (y_med - 0.125), 0.15), m=mm["curb"] if k % 2 else mm["curb_blk"])
    mb.box((L, med - 0.5, 0.25), (0, 0, 0.125), m=mm["sand"])
    return mb.to_object(origin="keep")


def street_light(mm, name="SM_StreetLight_KFR"):
    mb = sr.MB(name)
    H = 14.0
    mb.cyl(0.35, 1.0, (0, 0, 0.5), m=mm["concrete"], seg=12)
    mb.cyl(0.16, H, (0, 0, H / 2), m=mm["galv"], seg=12, r2=0.1)
    for sg in (1, -1):
        pts = [(0, 0, H - 1.2), (sg * 0.8, 0, H - 0.3), (sg * 2.2, 0, H + 0.05), (sg * 3.0, 0, H + 0.0)]
        mb.tube(pts, 0.07, mm["galv"], seg=8)
        mb.box((1.0, 0.36, 0.14), (sg * 3.2, 0, H - 0.05), m=mm["galv"], bevel=0.04, seg=2)
        mb.box((0.85, 0.28, 0.03), (sg * 3.2, 0, H - 0.135), m=mm["led_white"])
    # decorative band (Riyadh poles carry a light ring near the top)
    mb.lathe([(0.2, H - 2.0), (0.22, H - 1.9), (0.22, H - 1.5), (0.2, H - 1.4)], seg=16, m=mm["led_amber"])
    return mb.to_object(origin="base")


def gantry(mm, name="SM_Gantry_KFR", span=27.0):
    mb = sr.MB(name)
    H = 7.0
    for sg in (1, -1):
        x = sg * span / 2
        for dx in (-0.5, 0.5):
            for dy in (-0.5, 0.5):
                mb.cyl(0.1, H + 1.5, (x + dx, dy, (H + 1.5) / 2), m=mm["galv"], seg=8)
        for k in range(7):
            z = 0.6 + k * 1.15
            mb.tube([(x - 0.5, -0.5, z), (x + 0.5, 0.5, z + 1.1)], 0.04, mm["galv"], seg=5)
            mb.tube([(x - 0.5, 0.5, z), (x + 0.5, -0.5, z + 1.1)], 0.04, mm["galv"], seg=5)
        mb.box((1.6, 1.6, 0.6), (x, 0, 0.3), m=mm["concrete"])
    # horizontal box truss
    for dz in (H, H + 1.5):
        for dy in (-0.5, 0.5):
            mb.cyl(0.1, span + 1, (0, dy, dz), (0, 90, 0), m=mm["galv"], seg=8)
    n = int(span / 1.5)
    for k in range(n):
        x = -span / 2 + k * 1.5
        for dy in (-0.5, 0.5):
            mb.tube([(x, dy, H), (x + 1.5, dy, H + 1.5)], 0.04, mm["galv"], seg=5)
    # three signs (front face = -Y, drivers approach from -Y)
    signs = [("T_Sign_Olaya", -8.6), ("T_Sign_KingFahd", 0.0), ("T_Sign_Kingdom", 8.6)]
    for fname, x in signs:
        m = sr.mat(f"RoadSign_{fname[7:]}", (1, 1, 1), rough=0.5, image=os.path.join(TEXOUT, fname + ".png"),
                   image_emit=True, emit_str=0.6)
        w, h = 8.0, 4.0
        y = -0.75
        mb.quad_uv([(x - w / 2, y, H - 0.5), (x + w / 2, y, H - 0.5), (x + w / 2, y, H - 0.5 + h), (x - w / 2, y, H - 0.5 + h)],
                   ((0, 0), (1, 0), (1, 1), (0, 1)), m)
        mb.box((w, 0.12, h), (x, y + 0.08, H - 0.5 + h / 2), m=mm["galv"])
        # sign lights
        for k in range(3):
            mb.box((0.4, 0.5, 0.12), (x - 2.5 + k * 2.5, y - 0.3, H - 0.6), m=mm["led_white"])
    return mb.to_object(origin="base")


def metro_viaduct(mm, name="SM_MetroViaduct_30m", L=30.0):
    mb = sr.MB(name)
    Hd = 11.0
    # tulip pier
    prof = [(1.4, 0), (1.25, 2), (1.15, 6), (1.4, 8.5), (2.6, 9.8), (3.4, 10.3)]
    rings = []
    for z_r in prof:
        r, z = z_r
        rings.append([(r * 1.6 * math.cos(2 * math.pi * i / 24), r * math.sin(2 * math.pi * i / 24) * 1.0 + 0, z) for i in range(24)])
    rings = [[(y, x, z) for (x, y, z) in ring] for ring in rings]   # wide across the track (Y)
    mb.loft(rings, mm["concrete_lt"], closed=True, cap_start=True, smooth=True)
    # U-trough girder deck
    prof = [(-4.6, Hd - 0.7), (4.6, Hd - 0.7), (4.8, Hd + 1.4), (4.4, Hd + 1.4), (4.2, Hd + 0.2), (-4.2, Hd + 0.2),
            (-4.4, Hd + 1.4), (-4.8, Hd + 1.4)]
    rings = [[(x, y, z) for y, z in prof] for x in (-L / 2, L / 2)]
    mb.loft(rings, mm["concrete_lt"], closed=True, cap_start=True, cap_end=True, smooth=False)
    # rails + LED line under the deck edge
    for y in (-2.2, -0.8, 0.8, 2.2):
        mb.box((L, 0.15, 0.18), (0, y, Hd + 0.3), m=mm["galv"])
    for sg in (1, -1):
        mb.box((L, 0.12, 0.12), (0, sg * 4.75, Hd - 0.6), m=mm["led_white"])
    # catenary-free (third rail) - add lamp posts every 15 m
    for x in (-L / 4, L / 4):
        for sg in (1, -1):
            mb.cyl(0.06, 3.0, (x, sg * 4.6, Hd + 2.9), m=mm["galv"], seg=6)
            mb.box((0.5, 0.2, 0.1), (x, sg * 4.4, Hd + 4.4), m=mm["led_white"])
    return mb.to_object(origin="base")


def metro_car(mm, name="SM_MetroCar"):
    mb = sr.MB(name)
    L, W, H = 18.0, 2.9, 3.7
    rings = []
    stations = [(-L / 2, 0.85), (-L / 2 + 0.6, 0.97), (-L / 2 + 1.6, 1.0), (L / 2 - 2.6, 1.0), (L / 2 - 1.2, 0.93), (L / 2 - 0.3, 0.7), (L / 2, 0.45)]
    for x, sc in stations:
        hz = H * (0.6 + 0.4 * sc) if x > 0 else H
        half = []
        for k in range(9):
            a = -math.pi / 2 + math.pi * k / 8
            yy = (W / 2) * math.cos(a) * (0.95 + 0.05 * sc)
            zz = 0.5 + (hz - 0.5) * (0.5 + 0.5 * math.sin(a)) * (0.92 + 0.08 * sc)
            half.append((yy * sc ** 0.3, zz))
        ring = [(x, y, z) for y, z in half] + [(x, -y, z) for y, z in reversed(half[1:-1])]
        rings.append(ring)
    mb.loft(rings, mm["metro_white"], closed=True, cap_start=True, cap_end=True, smooth=True)
    for sg in (1, -1):   # window band, line colour stripe, doors
        mb.box((L - 4.0, 0.05, 1.0), (-0.6, sg * (W / 2 + 0.01), 2.4), m=mm["metro_win"])
        mb.box((L - 1.5, 0.05, 0.35), (0.0, sg * (W / 2 + 0.01), 1.55), m=mm["metro_blue"])
        for k in range(3):
            mb.box((1.4, 0.06, 2.1), (-5.0 + k * 5.0, sg * (W / 2 + 0.02), 1.65), m=mm["frame"])
    mb.box((0.06, 2.2, 1.0), (L / 2 - 0.55, 0, 2.6), (0, 30, 0), m=mm["metro_win"])
    mb.box((0.06, 0.4, 0.15), (L / 2 - 0.1, 1.0, 1.2), m=mm["led_white"])
    mb.box((0.06, 0.4, 0.15), (L / 2 - 0.1, -1.0, 1.2), m=mm["led_white"])
    for x in (-L / 2 + 3, L / 2 - 3):   # bogies
        mb.box((2.6, 2.2, 0.6), (x, 0, 0.4), m=mm["steel"])
    return mb.to_object(origin="base", sharp_angle=40)


def billboard(mm, name="SM_Billboard_LED"):
    mb = sr.MB(name)
    img = sr.mat("Billboard_RiyadhSeason", (1, 1, 1), rough=0.3, image=os.path.join(TEXOUT, "T_Billboard_RiyadhSeason.png"),
                 image_emit=True, emit_str=4.0)
    mb.cyl(0.5, 12, (0, 0, 6), m=mm["steel"], seg=12)
    mb.box((14.6, 0.8, 7.6), (0, 0.3, 15), m=mm["steel"])
    mb.quad_uv([(-7, -0.11, 11.5), (7, -0.11, 11.5), (7, -0.11, 18.5), (-7, -0.11, 18.5)], ((0, 0), (1, 0), (1, 1), (0, 1)), img)
    return mb.to_object(origin="base")


# --------------------------------------------------------------------- build ---
def build_all():
    sr.reset()
    make_textures()
    mm = M()
    objs = [kingdom_centre(mm), kingdom_mall(mm), al_faisaliah(mm), tv_tower(mm), pif_tower(mm),
            kafd_twist(mm), kafd_slant(mm), kafd_diagrid(mm), kafd_stepped(mm), masmak(mm)]
    specs = [(30, 22, 7, 1, 0), (24, 24, 5, 2, 1), (40, 18, 9, 3, 2), (22, 16, 4, 4, 0), (36, 26, 12, 5, 1), (28, 20, 6, 6, 2)]
    for i, (w, d, f, sd, st) in enumerate(specs):
        objs.append(riyadh_block(mm, f"SM_RiyadhBlock_{i + 1:02d}", w, d, f, sd, st))
    objs += [road_kingfahd(mm), street_light(mm), gantry(mm), metro_viaduct(mm), metro_car(mm), billboard(mm)]
    for o in objs:
        print(f"{o.name}: {sr.tri_count(o)} tris")
    return objs


if __name__ == "__main__":
    objs = build_all()
    sr.export_kit(objs, KIT)
    sr.write_manifest()


# ------------------------------------------------------------------ diorama ---
def diorama(objs, out=None, cars=("Falcon", "JeddahGT", "RiyadhMuscle")):
    """Night shot down King Fahd Road towards Kingdom Centre and Al Faisaliah."""
    by = {o.name: o for o in objs}
    for o in objs:
        sr.hide(o)
    rnd = random.Random(4)
    road = by["SM_Road_KingFahd_25m"]
    for k in range(-1, 44):
        sr.inst(road, (k * 25.0, 0, 0))
    light = by["SM_StreetLight_KFR"]
    for k in range(0, 28):
        x = 10 + k * 40
        sr.inst(light, (x, 0, 0), (0, 0, 90))
        for sg in (1, -1):
            sr.point_light((x, sg * 3.2, 13.6), 900, (1.0, 0.92, 0.8), 0.4, name="StreetLamp")
    sr.inst(by["SM_Gantry_KFR"], (95, -8.0, 0), (0, 0, 90))
    sr.inst(by["SM_Gantry_KFR"], (95, 8.0, 0), (0, 0, -90))
    blocks = [by[f"SM_RiyadhBlock_{i:02d}"] for i in range(1, 7)]
    towers = [by[n] for n in ("SM_KAFD_Twist", "SM_KAFD_Slant", "SM_KAFD_Diagrid", "SM_KAFD_Stepped")]
    for sg in (1, -1):
        x = 20.0
        while x < 1000:
            b = rnd.choice(blocks)
            sr.inst(b, (x, sg * (42 + rnd.uniform(0, 8)), 0), (0, 0, 0 if sg > 0 else 180))
            x += 36 + rnd.uniform(0, 14)
        x = 160.0 if sg > 0 else 90.0
        while x < 1100:            # office towers set back from the boulevard
            t = rnd.choice(towers)
            sr.inst(t, (x, sg * rnd.uniform(95, 140), 0), (0, 0, rnd.uniform(0, 90)), scale=rnd.uniform(0.45, 0.7))
            x += rnd.uniform(130, 220)
    palms = [by[n] for n in ("SM_DatePalm_A", "SM_DatePalm_B") if n in by]
    for k in range(0, 70):
        if palms:
            sr.inst(rnd.choice(palms), (5 + k * 15, rnd.uniform(-0.6, 0.6), 0.25), (0, 0, rnd.uniform(0, 360)))
    sr.inst(by["SM_Billboard_LED"], (140, -24, 0), (0, 0, -70))
    # skyline: Kingdom Centre closes the vista (arch facing the boulevard), Al Faisaliah to the left
    sr.inst(by["SM_KingdomCentre"], (1150, -25, 0), (0, 0, 98))
    sr.inst(by["SM_KingdomMall"], (1150, -25, 0), (0, 0, 98))
    sr.inst(by["SM_AlFaisaliah"], (640, 150, 0), (0, 0, 20))
    sr.inst(by["SM_RiyadhTVTower"], (1750, 430, 0))
    for name, loc in (("SM_PIFTower", (2100, -420, 0)), ("SM_KAFD_Twist", (1950, -560, 0)), ("SM_KAFD_Slant", (2250, -300, 0)),
                      ("SM_KAFD_Diagrid", (2300, -600, 0)), ("SM_KAFD_Stepped", (1900, -330, 0))):
        sr.inst(by[name], loc, (0, 0, rnd.uniform(0, 90)))
    for k in range(70):   # distant mid-rise carpet
        b = rnd.choice(blocks)
        x = rnd.uniform(1000, 2800)
        y = rnd.uniform(-1300, 1300)
        if abs(y) < 90:
            continue
        sr.inst(b, (x, y, 0), (0, 0, rnd.uniform(0, 360)), scale=rnd.uniform(0.9, 1.6))
    g = sr.ground(4000, sr.mat("Sand", (1, 1, 1), tex="Sand", tile=6), z=-0.02)
    # cars
    for i, c in enumerate(cars):
        glb = os.path.join(sr.ROOT, "assets", "cars", c, f"{c}_preview.glb")
        if os.path.exists(glb):
            sr.import_glb(glb, ((18, 34, 26)[i], (-6.0, -10.0, 6.5)[i], 0.0), (0, 0, 180)[i])
    # night lighting
    sr.setup_render((1600, 900), 128, exposure=0.0)
    sr.world_color(top=(0.004, 0.006, 0.02), horizon=(0.09, 0.05, 0.06), strength=1.0)
    sr.sun((60, 0, -30), 0.06, (0.6, 0.7, 1.0), 0.5, name="Moon")
    sr.camera((-12, -7.0, 2.4), (700, 0, 92), 30)
    sr.render(out or os.path.join(sr.ROOT, "docs", "previews", "map_riyadh_nights.png"))
