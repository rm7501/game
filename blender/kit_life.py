"""Sahara Racers - LIFE kit: people, crowds, animals, traffic, boats, camps, trackside dressing.

Everything that makes a map feel inhabited (assets/life/):
  People      SM_Person_Thobe / _Abaya / _Casual / _Kid, SM_Crowd_10m (spectators behind a fence),
              SM_CrowdCheer_10m (fans with raised arms and flags)
  Animals     SM_Camel, SM_Camel_Sitting, SM_Goat, SM_Sheep, SM_BirdFlock, SM_Seagulls
  Traffic     SM_Car_Sedan_White/_Silver/_Red, SM_Car_SUV_White/_Black, SM_Car_Pickup_White,
              SM_Bus_City, SM_Truck_Water
  Boats       SM_Dhow, SM_FishingBoat, SM_Yacht, SM_CargoShip
  Camps       SM_BedouinTent, SM_EventTent, SM_Gazebo_Green / _Red, SM_Campfire, SM_FoodTruck
  City        SM_Mosque_Dome, SM_Mosque_Najdi, SM_Villa, SM_ShopRow, SM_GasStation, SM_WaterTower,
              SM_BeachUmbrella, SM_Kiosk, SM_Bench, SM_LampClassic, SM_PowerPylon, SM_RoadSign
  Trackside   SM_ChevronBoard, SM_SponsorBoard_01..04, SM_Bunting_20m, SM_FlagPole, SM_MarshalPost,
              SM_CameraTower, SM_Floodlight, SM_DistanceBoard_100/_200, SM_Helicopter, SM_StackedTyres
  Plants      SM_Shrub_A/B, SM_SidrTree, SM_GrassTuft, SM_Flowers, SM_RockGrey_A/B
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))
import sr  # noqa: E402

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

KIT = "life"
OUT = os.path.join(sr.ROOT, "assets", KIT)
TEXOUT = os.path.join(OUT, "textures")

BANNERS = [("SAHARA RACERS", "سباق الصحراء", (0, 108, 53), (255, 255, 255), (214, 170, 60)),
           ("DUNE FUEL", "وقود الكثبان", (20, 20, 24), (255, 196, 40), (255, 196, 40)),
           ("NAKHLA COLA", "نخلة كولا", (190, 20, 30), (255, 255, 255), (255, 255, 255)),
           ("FALCON TYRES", "إطارات الصقر", (240, 240, 236), (18, 40, 110), (200, 30, 40))]


# ---------------------------------------------------------------- textures ---
def make_textures():
    try:
        from PIL import Image, ImageDraw, ImageFont, features
    except ImportError:
        return
    os.makedirs(TEXOUT, exist_ok=True)
    bold = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    if features.check("raqm"):
        ar = lambda s: s  # noqa: E731
    else:
        import arabic_reshaper
        from bidi.algorithm import get_display
        ar = lambda s: get_display(arabic_reshaper.reshape(s))  # noqa: E731
    for k, (en, arb, bg, fg, accent) in enumerate(BANNERS):
        W, H = 1024, 256
        im = Image.new("RGB", (W, H), bg)
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, W, 14], fill=accent)
        d.rectangle([0, H - 14, W, H], fill=accent)
        f1 = ImageFont.truetype(bold, 96)
        f2 = ImageFont.truetype(bold, 64)
        l, t, r, b = d.textbbox((0, 0), en, font=f1)
        d.text((40 - l, (H - (b - t)) / 2 - t), en, font=f1, fill=fg)
        txt = ar(arb)
        l2, t2, r2, b2 = d.textbbox((0, 0), txt, font=f2)
        d.text((W - 40 - (r2 - l2) - l2, (H - (b2 - t2)) / 2 - t2), txt, font=f2, fill=accent if accent != bg else fg)
        im.save(os.path.join(TEXOUT, f"T_Banner_{k + 1:02d}.png"))
    for dist in (100, 200):
        im = Image.new("RGB", (256, 256), (245, 245, 240))
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, 255, 255], outline=(20, 20, 20), width=14)
        f = ImageFont.truetype(bold, 110)
        l, t, r, b = d.textbbox((0, 0), str(dist), font=f)
        d.text(((256 - (r - l)) / 2 - l, (256 - (b - t)) / 2 - t), str(dist), font=f, fill=(20, 20, 20))
        im.save(os.path.join(TEXOUT, f"T_Distance_{dist}.png"))


# --------------------------------------------------------------- materials ---
def M():
    return dict(
        thobe=sr.mat("Cloth_ThobeWhite", (0.92, 0.92, 0.9), rough=0.8),
        shemagh=sr.mat("Cloth_ShemaghRed", (0.62, 0.08, 0.08), rough=0.8),
        agal=sr.mat("Cloth_AgalBlack", (0.03, 0.03, 0.03), rough=0.7),
        abaya=sr.mat("Cloth_AbayaBlack", (0.03, 0.03, 0.035), rough=0.6),
        skin=sr.mat("Skin_Tan", (0.55, 0.38, 0.27), rough=0.6),
        shirts=[sr.mat(f"Cloth_Shirt_{n}", c, rough=0.8) for n, c in (("Green", (0.0, 0.4, 0.2)), ("Blue", (0.1, 0.25, 0.6)),
                                                                          ("Yellow", (0.85, 0.65, 0.1)), ("Red", (0.65, 0.08, 0.08)),
                                                                          ("Grey", (0.45, 0.45, 0.47)), ("Orange", (0.85, 0.4, 0.08)))],
        jeans=sr.mat("Cloth_Jeans", (0.12, 0.16, 0.28), rough=0.85),
        flag=sr.mat("Flag_Green", (0.0, 0.42, 0.22), rough=0.7, kind="foliage"),
        flag_w=sr.mat("Pennant_White", (0.88, 0.88, 0.85), rough=0.7, kind="foliage"),
        gold=sr.mat("Pennant_Gold", (0.85, 0.62, 0.15), rough=0.7, kind="foliage"),
        camel=sr.mat("Hide_Camel", (0.62, 0.45, 0.28), rough=0.9),
        goat=sr.mat("Hide_GoatBlack", (0.07, 0.06, 0.05), rough=0.9),
        goat_b=sr.mat("Hide_GoatBrown", (0.38, 0.24, 0.14), rough=0.9),
        wool=sr.mat("Hide_Wool", (0.85, 0.82, 0.74), rough=0.95),
        hoof=sr.mat("Hoof_Dark", (0.08, 0.07, 0.06), rough=0.8),
        bird=sr.mat("Bird_Dark", (0.08, 0.08, 0.09), rough=0.7),
        gull=sr.mat("Bird_White", (0.9, 0.9, 0.9), rough=0.7),
        glass=sr.mat("Car_GlassDark", (0.02, 0.025, 0.03), rough=0.05, metal=0.6),
        tyre=sr.mat("TyreRubber", (0.03, 0.03, 0.03), rough=0.85),
        rim=sr.mat("RimSilver", (0.7, 0.7, 0.72), rough=0.3, metal=1.0),
        chrome=sr.mat("Chrome", (0.8, 0.8, 0.82), rough=0.1, metal=1.0),
        head=sr.mat("Light_Head", (1, 1, 0.95), emit=(1, 0.98, 0.9), emit_str=4, kind="emissive"),
        tail=sr.mat("Light_Tail", (0.6, 0.02, 0.02), emit=(1, 0.05, 0.03), emit_str=3, kind="emissive"),
        paints={n: sr.mat(f"Traffic_Paint_{n}", c, rough=0.25, metal=0.3, coat=0.8) for n, c in
                (("White", (0.88, 0.88, 0.86)), ("Silver", (0.6, 0.62, 0.64)), ("Red", (0.55, 0.04, 0.04)),
                 ("Black", (0.03, 0.03, 0.035)), ("Bus", (0.9, 0.9, 0.88)), ("Tanker", (0.85, 0.85, 0.85)))},
        wood=sr.mat("DhowWood", (0.42, 0.27, 0.15), rough=0.75, tex="WoodPainted", tile=1.2),
        wood_dk=sr.mat("PalmWood", (0.42, 0.3, 0.2), rough=0.8, tex="WoodPainted", tile=1.0),
        sail=sr.mat("Sail_Canvas", (0.9, 0.85, 0.74), rough=0.8, kind="foliage"),
        hull_w=sr.mat("Hull_White", (0.92, 0.92, 0.9), rough=0.25, coat=0.6),
        hull_b=sr.mat("Hull_Blue", (0.08, 0.2, 0.45), rough=0.4),
        hull_r=sr.mat("Hull_Red", (0.45, 0.08, 0.06), rough=0.6),
        steel=sr.mat("SteelGalvanised", (0.55, 0.56, 0.58), rough=0.45, metal=1.0),
        steel_dk=sr.mat("SteelDark", (0.08, 0.08, 0.09), rough=0.4, metal=1.0),
        containers=[sr.mat(f"Container_{n}", c, rough=0.6, metal=0.4) for n, c in
                    (("Red", (0.55, 0.1, 0.06)), ("Blue", (0.08, 0.2, 0.5)), ("Green", (0.1, 0.4, 0.2)),
                     ("Orange", (0.8, 0.35, 0.05)), ("Grey", (0.45, 0.46, 0.48)))],
        tent_black=sr.mat("Tent_GoatHair", (0.06, 0.05, 0.045), rough=0.95, kind="foliage"),
        tent_white=sr.mat("CanopyFabric", (0.92, 0.9, 0.85), rough=0.7, kind="foliage"),
        canopy_g=sr.mat("Canopy_Green", (0.02, 0.4, 0.2), rough=0.7, kind="foliage"),
        canopy_r=sr.mat("Canopy_Red", (0.6, 0.06, 0.05), rough=0.7, kind="foliage"),
        rug=sr.mat("Rug_Red", (0.5, 0.08, 0.06), rough=0.9),
        cushion=sr.mat("Cushion_Cream", (0.85, 0.78, 0.64), rough=0.85),
        fire=sr.mat("Fire_Glow", (1.0, 0.45, 0.1), emit=(1.0, 0.45, 0.1), emit_str=12, kind="emissive"),
        stone=sr.mat("Stone_Grey", (0.42, 0.41, 0.4), rough=0.9, tex="Rock", tile=1.5),
        rock=sr.mat("Rock_Granite", (0.55, 0.53, 0.52), rough=0.9, tex="Rock", tile=2.5),
        plaster=sr.mat("Plaster_White", (0.93, 0.92, 0.88), rough=0.8, tex="Concrete", tile=3.0),
        plaster_b=sr.mat("Plaster_Beige", (0.9, 0.8, 0.64), rough=0.85, tex="MudPlaster", tile=3.0),
        mud=sr.mat("MudBrick", (1.0, 0.95, 0.9), tex="MudPlaster", tile=3.0),
        dome=sr.mat("Dome_Green", (0.1, 0.42, 0.3), rough=0.35, metal=0.3),
        dome_w=sr.mat("Dome_White", (0.92, 0.92, 0.9), rough=0.4),
        dome_gold=sr.mat("Dome_Gold", (0.85, 0.62, 0.2), rough=0.25, metal=1.0),
        win=sr.mat("Win_Dark", (0.02, 0.025, 0.035), rough=0.05, metal=0.7),
        win_lit=sr.mat("Win_LitWarm", (0.25, 0.18, 0.12), emit=(1.0, 0.72, 0.42), emit_str=1.1, kind="emissive"),
        concrete=sr.mat("Concrete", (1, 1, 1), tex="Concrete", tile=2.0),
        asphalt=sr.mat("Asphalt", (1, 1, 1), tex="Asphalt", tile=4.0),
        red=sr.mat("Paint_RaceRed", (0.7, 0.04, 0.03), rough=0.5),
        white=sr.mat("PaintWhite", (0.85, 0.85, 0.83), rough=0.5),
        green=sr.mat("Paint_SaudiGreen", (0.0, 0.42, 0.22), rough=0.5),
        orange=sr.mat("Paint_Orange", (0.9, 0.38, 0.05), rough=0.5),
        yellow=sr.mat("Paint_Yellow", (0.9, 0.7, 0.05), rough=0.5),
        sign_green=sr.mat("Sign_HighwayGreen", (0.02, 0.32, 0.17), rough=0.4),
        lamp=sr.mat("Lamp_Warm", (1.0, 0.85, 0.6), emit=(1.0, 0.82, 0.55), emit_str=10, kind="emissive"),
        flood=sr.mat("Lamp_Flood", (1.0, 1.0, 0.95), emit=(1.0, 0.98, 0.92), emit_str=25, kind="emissive"),
        led_g=sr.mat("LED_Green", (0.1, 0.8, 0.4), emit=(0.15, 1.0, 0.45), emit_str=10, kind="emissive"),
        leaf=sr.mat("Leaf_Olive", (0.2, 0.27, 0.1), rough=0.85, kind="foliage"),
        leaf_dk=sr.mat("Leaf_Dark", (0.1, 0.18, 0.08), rough=0.85, kind="foliage"),
        grass=sr.mat("Grass_Blades", (0.22, 0.36, 0.12), rough=0.9, kind="foliage"),
        flower_y=sr.mat("Flower_Yellow", (0.95, 0.75, 0.1), rough=0.8, kind="foliage"),
        flower_p=sr.mat("Flower_Pink", (0.85, 0.3, 0.55), rough=0.8, kind="foliage"),
        bark=sr.mat("Bark_Dark", (0.25, 0.2, 0.16), rough=0.95, tex="Rock", tile=1.0),
        water=sr.mat("Water_Sea", (0.02, 0.12, 0.16), rough=0.04, metal=0.0, kind="water", tex="WaterWaves", tile=24.0),
    )


# ------------------------------------------------------------------ people ---
def _person(mb, mm, kind, loc=(0, 0, 0), yaw=0.0, arms_up=False, rnd=None, shirt=None, scale=1.0):
    """Stylised standing figure (~1.75 m): thobe + shemagh, abaya, or shirt + jeans."""
    rnd = rnd or random.Random(1)
    c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    ox, oy, oz = loc
    k = scale

    def P(x, y, z):
        return (ox + (x * c - y * s) * k, oy + (x * s + y * c) * k, oz + z * k)
    if kind == "kid":
        k *= 0.68
    if kind in ("thobe", "abaya"):
        body = mm["thobe"] if kind == "thobe" else mm["abaya"]
        prof = [(0.25, 0.0), (0.24, 0.5), (0.2, 1.0), (0.22, 1.32), (0.12, 1.45)]
        mb.lathe([(r * k, z * k) for r, z in prof], seg=10, loc=P(0, 0, 0), m=body, close_bottom=True)
    else:
        shirt = shirt or rnd.choice(mm["shirts"])
        for sg in (1, -1):
            mb.cyl(0.075 * k, 0.86 * k, P(0, sg * 0.1, 0.43), m=mm["jeans"], seg=6)
        mb.lathe([(r * k, z * k) for r, z in ((0.2, 0.84), (0.21, 1.1), (0.22, 1.32), (0.12, 1.45))], seg=10,
                 loc=P(0, 0, 0), m=shirt, close_bottom=True)
    # arms
    for sg in (1, -1):
        sh = Vector(P(0, sg * 0.24, 1.36))
        if arms_up and (sg > 0 or rnd.random() < 0.6):
            hand = Vector(P(0.05, sg * 0.32, 1.95))
        else:
            hand = Vector(P(0.04, sg * 0.28, 0.9))
        arm_m = mm["thobe"] if kind == "thobe" else mm["abaya"] if kind == "abaya" else shirt
        mb.tube([tuple(sh), tuple(hand)], 0.05 * k, arm_m, seg=5)
        mb.sphere(0.045 * k, tuple(hand), m=mm["skin"] if kind != "abaya" else mm["abaya"], seg=6, rings=4)
    # head
    hz = 1.6
    if kind == "thobe":
        mb.sphere(0.1 * k, P(0, 0, hz), m=mm["skin"], seg=8, rings=6)
        mb.lathe([(r * k, z * k) for r, z in ((0.14, 1.3), (0.16, 1.48), (0.13, 1.66), (0.0, 1.73))], seg=10,
                 loc=P(-0.02, 0, 0), m=mm["shemagh"])                 # shemagh draped to the shoulders
        mb.lathe([(0.105 * k, 1.66 * k), (0.11 * k, 1.69 * k)], seg=10, loc=P(-0.01, 0, 0), m=mm["agal"])
    elif kind == "abaya":
        mb.sphere(0.11 * k, P(0, 0, hz), m=mm["abaya"], seg=8, rings=6)
        mb.box((0.02 * k, 0.12 * k, 0.03 * k), P(0.105, 0, hz + 0.01), (0, 0, yaw), m=mm["skin"])  # eye slit
    else:
        mb.sphere(0.1 * k, P(0, 0, hz - (0.0 if kind != "kid" else 0.0)), m=mm["skin"], seg=8, rings=6)
        if rnd.random() < 0.5:
            mb.cyl(0.11 * k, 0.05 * k, P(0, 0, hz + 0.09), m=rnd.choice(mm["shirts"]), seg=8)   # cap


def person(mm, name, kind, shirt=None):
    mb = sr.MB(name)
    _person(mb, mm, kind, shirt=shirt)
    return mb.to_object(origin="base", sharp_angle=None)


def crowd(mm, name, length=10.0, rows=3, cheer=False, seed=4):
    """Spectators packed behind a low fence (fence on the +X side = towards the track when yaw faces it)."""
    rnd = random.Random(seed)
    mb = sr.MB(name)
    for r in range(rows):
        n = int(length / 0.62)
        for i in range(n):
            if rnd.random() < 0.12:
                continue
            x = -r * 0.7 - rnd.uniform(0, 0.25)
            y = -length / 2 + (i + 0.5) * length / n + rnd.uniform(-0.12, 0.12)
            kind = rnd.choices(["thobe", "casual", "abaya", "kid"], [0.45, 0.3, 0.15, 0.1])[0]
            _person(mb, mm, kind, (x, y, r * 0.18), yaw=rnd.uniform(-15, 15), arms_up=cheer and rnd.random() < 0.45,
                    rnd=rnd)
            if cheer and rnd.random() < 0.12:       # waving a green flag
                top = (x + 0.05, y + 0.32, r * 0.18 + 2.4)
                mb.tube([(x + 0.05, y + 0.32, r * 0.18 + 1.0), top], 0.012, mm["steel_dk"], seg=4)
                mb.poly_facing([top, (top[0], top[1] + 0.6, top[2] - 0.05), (top[0], top[1] + 0.6, top[2] - 0.42),
                                (top[0], top[1], top[2] - 0.38)], (1, 0, 0), mm["flag"])
    # fence in front
    mb.box((0.06, length, 1.0), (0.55, 0, 0.5), m=mm["steel"])
    for i in range(int(length / 2) + 1):
        mb.box((0.06, 0.06, 1.1), (0.55, -length / 2 + i * 2, 0.55), m=mm["steel_dk"])
    return mb.to_object(origin="base", sharp_angle=None)


# ----------------------------------------------------------------- animals ---
def camel(mm, name="SM_Camel", sitting=False):
    mb = sr.MB(name)
    hide = mm["camel"]
    if not sitting:
        for x in (0.55, -0.55):
            for y in (0.22, -0.22):
                mb.tube([(x, y, 1.25), (x + 0.04, y, 0.6), (x - 0.02, y, 0.05)], [0.09, 0.07, 0.06], hide, seg=6)
                mb.cyl(0.09, 0.06, (x - 0.02, y, 0.03), m=mm["hoof"], seg=6)
        bz = 1.45
    else:
        bz = 0.55
        for y in (0.3, -0.3):
            mb.sphere(0.25, (0.3, y, 0.18), m=hide, seg=8, rings=5, scale=(2.2, 0.6, 0.6))
    mb.sphere(0.5, (0, 0, bz), m=hide, seg=12, rings=8, scale=(1.5, 0.75, 0.75))           # body
    mb.sphere(0.36, (-0.05, 0, bz + 0.42), m=hide, seg=10, rings=6, scale=(1.1, 0.8, 0.95))  # hump
    neck = [(0.62, 0, bz + 0.05), (0.95, 0, bz + 0.15), (1.1, 0, bz + 0.65), (1.15, 0, bz + 0.95)]
    mb.tube(neck, [0.17, 0.14, 0.12, 0.11], hide, seg=8)
    mb.sphere(0.13, (1.27, 0, bz + 0.97), m=hide, seg=8, rings=5, scale=(1.9, 0.9, 0.9))   # head
    for y in (0.07, -0.07):
        mb.sphere(0.03, (1.2, y, bz + 1.08), m=hide, seg=5, rings=3)                      # ears
    mb.tube([(-0.72, 0, bz + 0.1), (-0.8, 0, bz - 0.45)], [0.04, 0.02], hide, seg=4)       # tail
    return mb.to_object(origin="base", sharp_angle=None)


def goat(mm, name="SM_Goat", hide=None, sheep=False):
    mb = sr.MB(name)
    hide = hide or mm["goat"]
    for x in (0.28, -0.28):
        for y in (0.1, -0.1):
            mb.cyl(0.03, 0.45, (x, y, 0.22), m=hide if not sheep else mm["hoof"], seg=5)
    mb.sphere(0.24 if not sheep else 0.3, (0, 0, 0.6), m=hide, seg=10, rings=6, scale=(1.65, 0.85, 0.85))
    head = (0.48, 0, 0.82)
    mb.tube([(0.32, 0, 0.66), head], 0.08, hide, seg=6)
    mb.sphere(0.09, head, m=hide if not sheep else mm["hoof"], seg=8, rings=5, scale=(1.6, 0.8, 0.9))
    if not sheep:
        for y in (0.05, -0.05):          # horns
            mb.tube([(0.46, y, 0.9), (0.4, y * 1.6, 1.02), (0.32, y * 2.2, 1.05)], [0.025, 0.015, 0.005], mm["hoof"], seg=4)
        mb.tube([(-0.38, 0, 0.7), (-0.44, 0, 0.82)], [0.03, 0.01], hide, seg=4)
    return mb.to_object(origin="base", sharp_angle=None)


def birds(mm, name="SM_BirdFlock", n=14, white=False, seed=3):
    rnd = random.Random(seed)
    mb = sr.MB(name)
    m = mm["gull"] if white else mm["bird"]
    for k in range(n):
        x, y, z = rnd.gauss(0, 6), rnd.gauss(0, 6), rnd.gauss(0, 2)
        span = rnd.uniform(0.6, 1.0)
        a = rnd.uniform(0, math.pi * 2)
        up = rnd.uniform(0.05, 0.35)
        ca, sa = math.cos(a), math.sin(a)
        for sg in (1, -1):
            tip = (x - sa * span * sg, y + ca * span * sg, z + up)
            mb.poly([(x + ca * 0.15, y + sa * 0.15, z), (x - ca * 0.15, y - sa * 0.15, z), tip], m)
    return mb.to_object(origin="center", sharp_angle=None)


# ----------------------------------------------------------------- traffic ---
def _wheels(mb, mm, xs, half_w, r, width=0.22):
    for x in xs:
        for sg in (1, -1):
            mb.cyl(r, width, (x, sg * half_w, r), (90, 0, 0), m=mm["tyre"], seg=12)
            mb.cyl(r * 0.62, width + 0.02, (x, sg * half_w, r), (90, 0, 0), m=mm["rim"], seg=10)


def _body(mb, sections, paint, glass, win_rows):
    """Loft a car body from (x, half_width, z_bottom, z_top) sections; side windows from win_rows."""
    rings = []
    for x, w, zb, zt in sections:
        rings.append([(x, -w, zb), (x, w, zb), (x, w * 0.97, zt * 0.8 + zb * 0.2), (x, w * 0.85, zt),
                      (x, -w * 0.85, zt), (x, -w * 0.97, zt * 0.8 + zb * 0.2)])
    mb.loft(rings, paint, closed=True, cap_start=True, cap_end=True, smooth=False)


def car(mm, name, kind="sedan", paint="White"):
    mb = sr.MB(name)
    p = mm["paints"][paint]
    g = mm["glass"]
    if kind == "sedan":
        L, W, r = 4.8, 0.9, 0.33
        mb.box((L, W * 2, 0.62), (0, 0, 0.62), m=p, bevel=0.12, seg=2)
        rings = [[(x, -w, 0.92), (x, w, 0.92), (x, w * 0.8, 1.42), (x, -w * 0.8, 1.42)]
                 for x, w in ((1.0, 0.86), (0.55, 0.82), (-0.75, 0.82), (-1.2, 0.84))]
        mb.loft(rings, g, closed=True, cap_start=True, cap_end=True, smooth=False)
        mb.box((1.3, 1.4, 0.06), (-0.1, 0, 1.44), m=p)
        _wheels(mb, mm, (1.45, -1.45), 0.82, r)
    elif kind == "suv":
        L, W, r = 4.95, 0.98, 0.4
        mb.box((L, W * 2, 0.95), (0, 0, 0.88), m=p, bevel=0.1, seg=2)
        rings = [[(x, -w, 1.34), (x, w, 1.34), (x, w * 0.92, 1.92), (x, -w * 0.92, 1.92)]
                 for x, w in ((1.05, 0.95), (0.7, 0.94), (-2.3, 0.94), (-2.42, 0.94))]
        mb.loft(rings, g, closed=True, cap_start=True, cap_end=True, smooth=False)
        mb.box((3.0, 1.82, 0.08), (-0.8, 0, 1.95), m=p)
        mb.box((2.2, 1.5, 0.06), (-0.8, 0, 2.03), m=mm["steel_dk"])      # roof rack
        _wheels(mb, mm, (1.55, -1.5), 0.9, r, 0.28)
    elif kind == "pickup":
        L, W, r = 5.3, 0.92, 0.38
        mb.box((2.3, W * 2, 0.95), (1.5, 0, 0.86), m=p, bevel=0.08, seg=2)
        rings = [[(x, -w, 1.3), (x, w, 1.3), (x, w * 0.9, 1.85), (x, -w * 0.9, 1.85)]
                 for x, w in ((1.0, 0.9), (0.7, 0.9), (-0.45, 0.9), (-0.5, 0.9))]
        mb.loft(rings, g, closed=True, cap_start=True, cap_end=True, smooth=False)
        mb.box((1.2, 1.75, 0.07), (0.15, 0, 1.87), m=p)
        mb.box((2.4, W * 2, 0.5), (-1.45, 0, 0.75), m=p)                     # bed
        mb.box((2.3, W * 2 - 0.15, 0.45), (-1.45, 0, 0.82), m=mm["steel_dk"])
        _wheels(mb, mm, (1.75, -1.6), 0.86, r, 0.26)
    elif kind == "bus":
        L, W, r = 12.0, 1.27, 0.5
        mb.box((L, W * 2, 2.6), (0, 0, 1.75), m=p, bevel=0.15, seg=2)
        for sg in (1, -1):
            mb.box((L - 2.5, 0.04, 1.0), (-0.6, sg * W, 2.15), m=g)
            mb.box((L - 0.4, 0.03, 0.14), (0, sg * (W + 0.005), 1.35), m=mm["green"])
        mb.box((0.04, W * 1.8, 1.3), (L / 2, 0, 2.0), m=g)
        _wheels(mb, mm, (3.9, -3.6), 1.13, r, 0.3)
    elif kind == "tanker":
        L, W, r = 8.5, 1.25, 0.5
        mb.box((2.2, W * 2, 2.3), (3.0, 0, 1.75), m=mm["paints"]["White"], bevel=0.1, seg=2)
        mb.box((0.04, W * 1.7, 0.9), (4.11, 0, 2.3), m=g)
        mb.cyl(1.05, 5.6, (-0.9, 0, 1.75), (0, 90, 0), m=mm["paints"]["Tanker"], seg=16)
        mb.box((6.0, 0.6, 0.3), (-0.6, 0, 0.75), m=mm["steel_dk"])
        _wheels(mb, mm, (3.0, -1.8, -3.0), 1.1, r, 0.32)
    x_front = L / 2
    for sg in (1, -1):
        mb.box((0.06, 0.32, 0.12), (x_front + 0.01, sg * (W - 0.25), 0.85 if kind != "bus" else 1.0), m=mm["head"])
        mb.box((0.06, 0.28, 0.12), (-x_front - 0.01, sg * (W - 0.25), 0.9 if kind != "bus" else 1.0), m=mm["tail"])
    return mb.to_object(origin="base", sharp_angle=35)


# ------------------------------------------------------------------- boats ---
def dhow(mm, name="SM_Dhow", L=14.0):
    mb = sr.MB(name)
    rings = []
    for k in range(13):
        t = k / 12
        x = -L / 2 + L * t
        w = 2.1 * math.sin(math.pi * min(1, 0.15 + 0.85 * t)) ** 0.7 + 0.15
        zt = 1.6 + 1.2 * (t - 0.6) ** 2 * 2.2 + (0.9 if t > 0.9 else 0)
        rings.append([(x, 0, -0.9 + 0.5 * abs(t - 0.5)), (x, w, 0.2), (x, w * 1.02, zt), (x, -w * 1.02, zt), (x, -w, 0.2)])
    mb.loft(rings, mm["wood"], closed=True, cap_start=True, cap_end=True, smooth=True)
    mb.box((L * 0.8, 3.6, 0.1), (-0.2, 0, 1.7), m=mm["wood_dk"])                    # deck
    mb.cyl(0.13, 11, (1.0, 0, 7.0), (0, -8, 0), m=mm["wood_dk"], seg=8)             # mast
    yard = [(-4.5, 0, 10.5), (6.5, 0, 5.0)]
    mb.tube(yard, 0.08, mm["wood_dk"], seg=6)
    mb.poly_facing([(-4.4, 0.05, 10.4), (6.3, 0.05, 5.0), (1.3, 0.05, 2.6)], (0, 1, 0), mm["sail"])   # lateen sail
    return mb.to_object(origin="base", sharp_angle=None)


def fishing_boat(mm, name="SM_FishingBoat", L=8.0):
    mb = sr.MB(name)
    rings = []
    for k in range(9):
        t = k / 8
        x = -L / 2 + L * t
        w = 1.2 * math.sin(math.pi * min(1, 0.2 + 0.8 * t)) ** 0.6 + 0.1
        rings.append([(x, 0, -0.5), (x, w, 0.1), (x, w, 0.9 + 0.4 * t * t), (x, -w, 0.9 + 0.4 * t * t), (x, -w, 0.1)])
    mb.loft(rings, mm["hull_b"], closed=True, cap_start=True, cap_end=True, smooth=True)
    mb.box((L * 0.9, 2.0, 0.08), (0, 0, 0.9), m=mm["white"])
    mb.box((1.6, 1.4, 1.5), (-1.2, 0, 1.65), m=mm["white"])
    mb.box((1.62, 1.42, 0.08), (-1.2, 0, 2.43), m=mm["red"])
    return mb.to_object(origin="base", sharp_angle=None)


def yacht(mm, name="SM_Yacht", L=22.0):
    mb = sr.MB(name)
    rings = []
    for k in range(11):
        t = k / 10
        x = -L / 2 + L * t
        w = 2.6 * (1 - max(0, t - 0.55) ** 1.6 * 2.3) + 0.1
        rings.append([(x, 0, -1.2 + 0.6 * t), (x, w, 0.0), (x, w, 2.0 + 0.6 * t), (x, -w, 2.0 + 0.6 * t), (x, -w, 0.0)])
    mb.loft(rings, mm["hull_w"], closed=True, cap_start=True, cap_end=True, smooth=True)
    mb.box((L * 0.55, 4.0, 1.8), (-1.5, 0, 3.2), m=mm["hull_w"], bevel=0.3, seg=2)
    mb.box((L * 0.56, 4.05, 0.7), (-1.5, 0, 3.3), m=mm["glass"])
    mb.box((L * 0.3, 3.0, 1.4), (-2.5, 0, 4.7), m=mm["hull_w"], bevel=0.3, seg=2)
    mb.box((L * 0.31, 3.05, 0.5), (-2.5, 0, 4.8), m=mm["glass"])
    mb.box((L, 0.06, 0.1), (0, 2.65, 0.6), m=mm["hull_b"])
    mb.box((L, 0.06, 0.1), (0, -2.65, 0.6), m=mm["hull_b"])
    return mb.to_object(origin="base", sharp_angle=None)


def cargo_ship(mm, name="SM_CargoShip", L=180.0, seed=5):
    rnd = random.Random(seed)
    mb = sr.MB(name)
    W = 15.0
    rings = []
    for k in range(13):
        t = k / 12
        x = -L / 2 + L * t
        w = W * (1 - max(0, t - 0.82) ** 1.5 * 9) if t > 0.82 else W * (0.75 + 0.25 * min(1, t * 8))
        w = max(w, 1.0)
        rings.append([(x, 0, -6), (x, w, -4), (x, w, 9), (x, -w, 9), (x, -w, -4)])
    mb.loft(rings, mm["hull_r"], closed=True, cap_start=True, cap_end=True, smooth=False)
    mb.box((L * 0.96, W * 2 + 0.2, 4.0), (0, 0, 7.5), m=mm["steel_dk"])          # black topsides
    mb.box((14, W * 2 - 2, 18), (-L / 2 + 14, 0, 18), m=mm["white"])              # bridge
    mb.box((14.2, W * 2 - 1.8, 1.6), (-L / 2 + 14, 0, 25), m=mm["glass"])
    mb.box((5, 5, 10), (-L / 2 + 20, 0, 31), m=mm["red"])                          # funnel
    for i in range(int((L * 0.72) / 6.2)):
        x = -L / 2 + 26 + i * 6.2
        for j in range(5):
            for lv in range(rnd.randint(2, 5)):
                mb.box((6.0, 2.45, 2.55), (x, -W + 3 + j * 2.5 * 2.3, 10.3 + lv * 2.6), m=rnd.choice(mm["containers"]))
    return mb.to_object(origin="keep", sharp_angle=35)


# ------------------------------------------------------------------- camps ---
def bedouin_tent(mm, name="SM_BedouinTent"):
    """Bait al-sha'ar: long low black goat-hair tent on poles, open front, rugs and cushions inside."""
    mb = sr.MB(name)
    L, D = 12.0, 6.0
    grid = []
    for i in range(9):
        x = -L / 2 + L * i / 8
        row = []
        for j in range(5):
            y = -D / 2 + D * j / 4
            sag = 0.35 * math.sin(math.pi * i / 8 * 4) ** 2
            z = 2.4 - 0.9 * (abs(y) / (D / 2)) ** 1.4 - sag
            row.append((x, y, z))
        grid.append(row)
    mb.strip(grid, None, mm["tent_black"], smooth=True, keep=True)
    mb.box((L, 0.04, 1.4), (0, D / 2, 0.75), m=mm["tent_black"])                   # back wall
    for i in range(5):
        x = -L / 2 + L * i / 4
        mb.cyl(0.05, 2.4, (x, 0, 1.2), m=mm["wood_dk"], seg=6)
    mb.box((L - 1, D - 1.5, 0.03), (0, 0.3, 0.02), m=mm["rug"])
    for i in range(6):
        mb.box((1.2, 0.6, 0.35), (-L / 2 + 1.5 + i * 1.8, D / 2 - 0.9, 0.2), m=mm["cushion"], bevel=0.1, seg=2)
    return mb.to_object(origin="base", sharp_angle=None)


def event_tent(mm, name="SM_EventTent", L=16.0, D=10.0):
    mb = sr.MB(name)
    for x in (-L / 2, L / 2):
        for y in (-D / 2, D / 2):
            mb.cyl(0.08, 3.2, (x, y, 1.6), m=mm["steel"], seg=6)
    for k in range(4):                              # peaked white roof modules
        x0 = -L / 2 + k * L / 4
        x1 = x0 + L / 4
        xc = (x0 + x1) / 2
        apex = (xc, 0, 6.0)
        for a, b in (((x0, -D / 2, 3.2), (x1, -D / 2, 3.2)), ((x1, -D / 2, 3.2), (x1, D / 2, 3.2)),
                     ((x1, D / 2, 3.2), (x0, D / 2, 3.2)), ((x0, D / 2, 3.2), (x0, -D / 2, 3.2))):
            mb.poly([a, b, apex], mm["tent_white"])
    mb.box((L, 0.04, 3.2), (0, D / 2, 1.6), m=mm["tent_white"])
    return mb.to_object(origin="base", sharp_angle=None)


def gazebo(mm, name, canopy):
    mb = sr.MB(name)
    for x in (-1.5, 1.5):
        for y in (-1.5, 1.5):
            mb.cyl(0.03, 2.2, (x, y, 1.1), m=mm["steel"], seg=6)
    for a, b in (((-1.6, -1.6), (1.6, -1.6)), ((1.6, -1.6), (1.6, 1.6)), ((1.6, 1.6), (-1.6, 1.6)), ((-1.6, 1.6), (-1.6, -1.6))):
        mb.poly([(a[0], a[1], 2.2), (b[0], b[1], 2.2), (0, 0, 3.1)], canopy)
        mb.box((abs(b[0] - a[0]) + 0.02, abs(b[1] - a[1]) + 0.02, 0.25), ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, 2.1), m=canopy)
    mb.box((1.8, 0.7, 0.75), (0, 0.6, 0.38), m=mm["white"])                       # table
    return mb.to_object(origin="base", sharp_angle=None)


def campfire(mm, name="SM_Campfire"):
    mb = sr.MB(name)
    for k in range(9):
        a = 2 * math.pi * k / 9
        mb.sphere(0.16, (0.55 * math.cos(a), 0.55 * math.sin(a), 0.08), m=mm["stone"], seg=6, rings=4, scale=(1, 1, 0.6))
    for k in range(4):
        a = math.pi * k / 4
        mb.tube([(-0.35 * math.cos(a), -0.35 * math.sin(a), 0.05), (0.35 * math.cos(a), 0.35 * math.sin(a), 0.15)], 0.05,
                mm["wood_dk"], seg=5)
    mb.lathe([(0.3, 0.05), (0.22, 0.35), (0.08, 0.75), (0.0, 0.95)], seg=8, m=mm["fire"])
    mb.cyl(0.12, 0.6, (0.9, 0.3, 0.3), m=mm["dome_gold"], seg=10, r2=0.06)          # dallah coffee pot
    return mb.to_object(origin="base", sharp_angle=None)


def food_truck(mm, name="SM_FoodTruck"):
    mb = sr.MB(name)
    mb.box((5.5, 2.2, 2.4), (0, 0, 1.6), m=mm["yellow"], bevel=0.15, seg=2)
    mb.box((1.6, 2.2, 1.6), (3.4, 0, 1.2), m=mm["yellow"], bevel=0.15, seg=2)
    mb.box((0.05, 1.9, 0.8), (4.2, 0, 1.55), m=mm["glass"])
    mb.box((3.0, 0.05, 1.0), (-0.3, -1.12, 2.0), m=mm["win_lit"])                     # serving hatch
    grid = [[(-1.8, -1.15, 2.8), (-1.8, -2.2, 2.4)], [(1.2, -1.15, 2.8), (1.2, -2.2, 2.4)]]
    mb.strip(grid, None, mm["canopy_r"], smooth=False, keep=True)
    _wheels(mb, mm, (2.6, -1.8), 1.0, 0.42, 0.26)
    return mb.to_object(origin="base", sharp_angle=None)


# -------------------------------------------------------------------- city ---
def mosque_dome(mm, name="SM_Mosque_Dome"):
    mb = sr.MB(name)
    mb.box((22, 22, 9), (0, 0, 4.5), m=mm["plaster"])
    for sg in (1, -1):
        for k in range(4):
            mb.box((0.06, 2.0, 3.6), (sg * 11.01, -6 + k * 4, 4.5), m=mm["win"])
    mb.cyl(6.5, 2.0, (0, 0, 10), m=mm["plaster"], seg=24)
    mb.lathe([(6.6 * math.cos(a), 11 + 7.5 * math.sin(a)) for a in [math.pi / 2 * i / 12 for i in range(13)]][::-1],
             seg=32, m=mm["dome"])
    mb.cyl(0.12, 2.0, (0, 0, 19.4), m=mm["dome_gold"], seg=8)
    mb.sphere(0.35, (0, 0, 20.2), m=mm["dome_gold"], seg=10, rings=6)
    # minaret
    mx, my = 13.0, 9.0
    mb.cyl(1.5, 30, (mx, my, 15), m=mm["plaster"], seg=12)
    for z in (14, 24):
        mb.cyl(2.1, 0.8, (mx, my, z), m=mm["plaster"], seg=12)
    mb.cyl(1.2, 4, (mx, my, 32), m=mm["plaster"], seg=12)
    mb.cyl(1.25, 3.0, (mx, my, 35.5), m=mm["dome"], seg=12, r2=0.1)
    mb.sphere(0.25, (mx, my, 37.2), m=mm["dome_gold"], seg=8, rings=5)
    return mb.to_object(origin="base", sharp_angle=35)


def mosque_najdi(mm, name="SM_Mosque_Najdi"):
    """Mud-brick Najdi mosque with a tapering square minaret (Diriyah style)."""
    mb = sr.MB(name)
    mb.box((20, 16, 6), (0, 0, 3), m=mm["mud"])
    for k in range(10):
        mb.prism([(-0.5, 0), (0.5, 0), (0, 0.8)], -0.2, 0.2, (-9.5 + k * 2.1, -8.0, 6.0), (90, 0, 0), m=mm["mud"])
    rings = [[(9 + sx * s, 6 + sy * s, z) for sx, sy in ((1, -1), (1, 1), (-1, 1), (-1, -1))]
             for s, z in ((2.0, 0), (1.3, 18))]
    mb.loft(rings, mm["mud"], closed=True, cap_end=True, smooth=False)
    for z in (6, 10, 14):
        for sx, sy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            k = 2.0 - 0.7 * z / 18
            mb.box((0.4 if sx else 0.06, 0.06 if sx else 0.4, 0.9), (9 + sx * (k + 0.01), 6 + sy * (k + 0.01), z), m=mm["win"])
    mb.box((3.2, 3.2, 0.5), (9, 6, 18.25), m=mm["mud"])
    return mb.to_object(origin="base", sharp_angle=35)


def villa(mm, name="SM_Villa", seed=3):
    rnd = random.Random(seed)
    mb = sr.MB(name)
    W, D = 26, 22
    for sg in (1, -1):                          # boundary wall
        mb.box((W, 0.3, 3.0), (0, sg * D / 2, 1.5), m=mm["plaster_b"])
        mb.box((0.3, D, 3.0), (sg * W / 2, 0, 1.5), m=mm["plaster_b"])
    mb.box((4, 0.35, 2.6), (W / 4, -D / 2, 1.3), m=mm["steel_dk"])                 # gate
    mb.box((14, 11, 7), (-2, 3, 3.5), m=mm["plaster"])
    mb.box((7, 8, 3.2), (-4, 3, 8.6), m=mm["plaster"])
    for k in range(4):
        mb.box((1.6, 0.06, 1.6), (-7 + k * 3.2, -2.53, 4.5), m=mm["win"])
        mb.box((1.2, 0.06, 1.2), (-7 + k * 3.2, -2.53, 1.6), m=mm["win"])
    mb.box((14.2, 11.2, 0.4), (-2, 3, 7.1), m=mm["plaster_b"])
    return mb.to_object(origin="base", sharp_angle=35)


def shop_row(mm, name="SM_ShopRow", n=5, seed=7):
    rnd = random.Random(seed)
    mb = sr.MB(name)
    L = n * 6.0
    mb.box((L, 10, 4.5), (0, 0, 2.25), m=mm["plaster_b"])
    mb.box((L, 10, 3.5), (0, 0.5, 6.25), m=mm["plaster"])
    for i in range(n):
        x = -L / 2 + 3 + i * 6
        mb.box((5.2, 0.06, 2.8), (x, -5.02, 1.5), m=mm["win_lit"])
        mb.box((5.6, 0.25, 1.0), (x, -5.15, 3.8), m=rnd.choice((mm["green"], mm["red"], mm["sign_green"], mm["orange"])))
        mb.box((5.6, 1.6, 0.08), (x, -5.8, 3.2), (12, 0, 0), m=rnd.choice((mm["canopy_g"], mm["canopy_r"], mm["tent_white"])))
    return mb.to_object(origin="base", sharp_angle=35)


def gas_station(mm, name="SM_GasStation"):
    mb = sr.MB(name)
    mb.box((24, 14, 0.8), (0, 0, 6.2), m=mm["white"])
    mb.box((24.1, 14.1, 0.5), (0, 0, 6.2), m=mm["green"])
    for x in (-8, 0, 8):
        mb.box((0.5, 0.5, 5.8), (x, 0, 2.9), m=mm["white"])
        mb.box((1.0, 0.6, 1.6), (x, 2.5, 0.8), m=mm["white"])
        mb.box((1.0, 0.6, 1.6), (x, -2.5, 0.8), m=mm["white"])
        mb.box((1.02, 0.62, 0.3), (x, 2.5, 1.5), m=mm["green"])
        mb.box((1.02, 0.62, 0.3), (x, -2.5, 1.5), m=mm["green"])
    mb.box((16, 9, 4), (0, 14, 2), m=mm["plaster"])
    mb.box((14, 0.06, 2.4), (0, 9.52, 1.6), m=mm["win_lit"])
    mb.box((1.0, 1.0, 9), (14, -8, 4.5), m=mm["white"])
    mb.box((2.6, 0.6, 3.2), (14, -8, 9.5), m=mm["green"])
    return mb.to_object(origin="base", sharp_angle=35)


def water_tower(mm, name="SM_WaterTower"):
    """Mushroom water tower (Riyadh / Jeddah landmark type)."""
    mb = sr.MB(name)
    mb.cyl(1.8, 30, (0, 0, 15), m=mm["plaster"], seg=16, r2=1.4)
    mb.lathe([(1.4, 29), (6, 31), (9, 34.5), (8.5, 38), (0, 39)], seg=24, m=mm["plaster"])
    mb.lathe([(9.02, 34.0), (9.02, 35.2)], seg=24, m=mm["sign_green"])
    return mb.to_object(origin="base", sharp_angle=None)


def beach_umbrella(mm, name="SM_BeachUmbrella", seed=2):
    rnd = random.Random(seed)
    mb = sr.MB(name)
    mb.cyl(0.04, 2.5, (0, 0, 1.25), m=mm["wood_dk"], seg=6)
    canopy = rnd.choice((mm["canopy_g"], mm["canopy_r"], mm["tent_white"]))
    mb.lathe([(0.0, 2.6), (1.4, 2.25), (1.45, 2.2)], seg=12, m=canopy)
    for sg in (1, -1):
        mb.box((1.9, 0.62, 0.08), (0.2, sg * 0.9, 0.32), (0, -8, 0), m=mm["white"])
        mb.box((0.6, 0.62, 0.06), (-0.85, sg * 0.9, 0.55), (0, -50, 0), m=mm["white"])
    return mb.to_object(origin="base", sharp_angle=None)


def kiosk(mm, name="SM_Kiosk"):
    mb = sr.MB(name)
    mb.box((3.2, 2.6, 2.6), (0, 0, 1.3), m=mm["white"])
    mb.box((2.6, 0.05, 1.1), (0, -1.32, 1.6), m=mm["win_lit"])
    mb.box((3.8, 3.2, 0.15), (0, 0, 2.75), m=mm["canopy_g"])
    mb.box((3.0, 0.15, 0.6), (0, -1.4, 3.1), m=mm["green"])
    return mb.to_object(origin="base", sharp_angle=None)


def bench(mm, name="SM_Bench"):
    mb = sr.MB(name)
    mb.box((1.8, 0.45, 0.06), (0, 0, 0.45), m=mm["wood_dk"])
    mb.box((1.8, 0.06, 0.4), (0, 0.22, 0.72), m=mm["wood_dk"])
    for x in (-0.8, 0.8):
        mb.box((0.06, 0.45, 0.45), (x, 0, 0.22), m=mm["steel_dk"])
    return mb.to_object(origin="base", sharp_angle=None)


def lamp_classic(mm, name="SM_LampClassic"):
    mb = sr.MB(name)
    mb.cyl(0.18, 0.6, (0, 0, 0.3), m=mm["steel_dk"], seg=8)
    mb.cyl(0.07, 4.2, (0, 0, 2.6), m=mm["steel_dk"], seg=8, r2=0.05)
    for sg in (1, -1):
        mb.tube([(0, 0, 4.4), (sg * 0.5, 0, 4.7), (sg * 0.7, 0, 4.5)], 0.03, mm["steel_dk"], seg=5)
        mb.lathe([(0.0, 4.0), (0.16, 4.1), (0.18, 4.35), (0.0, 4.5)], seg=8, loc=(sg * 0.7, 0, 0), m=mm["lamp"])
    return mb.to_object(origin="base", sharp_angle=None)


def power_pylon(mm, name="SM_PowerPylon", H=38.0):
    mb = sr.MB(name)
    for sx in (1, -1):
        for sy in (1, -1):
            mb.tube([(sx * 4, sy * 4, 0), (sx * 1.0, sy * 1.0, H)], 0.15, mm["steel"], seg=5)
    for k in range(9):
        z0, z1 = H * k / 9, H * (k + 1) / 9
        r0, r1 = 4 - 3 * k / 9, 4 - 3 * (k + 1) / 9
        for (ax, ay, bx, by) in ((1, 1, 1, -1), (1, -1, -1, -1), (-1, -1, -1, 1), (-1, 1, 1, 1)):
            mb.tube([(ax * r0, ay * r0, z0), (bx * r1, by * r1, z1)], 0.06, mm["steel"], seg=4)
    for z, w in ((H * 0.72, 9), (H * 0.86, 7), (H, 5)):
        mb.box((0.4, w * 2, 0.4), (0, 0, z), m=mm["steel"])
    return mb.to_object(origin="base", sharp_angle=40)


def road_sign(mm, name="SM_RoadSign"):
    mb = sr.MB(name)
    for y in (-2.0, 2.0):
        mb.cyl(0.1, 6.5, (0, y, 3.25), m=mm["steel"], seg=8)
    mb.box((0.15, 5.5, 2.4), (0, 0, 5.6), m=mm["sign_green"])
    for k in range(3):            # arrow + text bars
        mb.box((0.04, 2.6 - k * 0.6, 0.18), (-0.09, -0.6, 6.3 - k * 0.5), m=mm["white"])
    mb.prism([(0, 0), (0.6, 0.5), (0.3, 0.5), (0.3, 1.2), (-0.3, 1.2), (-0.3, 0.5), (-0.6, 0.5)], -0.05, 0.05,
             (-0.1, 1.7, 4.9), (90, 0, 90), m=mm["white"])
    return mb.to_object(origin="base", sharp_angle=None)


# --------------------------------------------------------------- trackside ---
def chevron_board(mm, name="SM_ChevronBoard"):
    """Red board with white chevrons pointing the way (+Y), facing -X (towards oncoming cars)."""
    mb = sr.MB(name)
    for y in (-0.7, 0.7):
        mb.cyl(0.05, 1.5, (0.05, y, 0.75), m=mm["steel"], seg=6)
    mb.box((0.06, 1.8, 0.9), (0, 0, 1.45), m=mm["red"])
    for k in range(2):
        y0 = -0.45 + k * 0.6
        pts = [(y0, 0.15), (y0 + 0.25, 0.45), (y0, 0.75), (y0 + 0.14, 0.75), (y0 + 0.39, 0.45), (y0 + 0.14, 0.15)]
        mb.poly_facing([(-0.035, y, 1.0 + z) for y, z in pts], (-1, 0, 0), mm["white"])
        mb.poly_facing([(0.035, y, 1.0 + z) for y, z in pts], (1, 0, 0), mm["white"])
    return mb.to_object(origin="base", sharp_angle=None)


def sponsor_board(mm, name, k):
    mb = sr.MB(name)
    tex = sr.mat(f"Banner_{k:02d}", (1, 1, 1), rough=0.5, image=os.path.join(TEXOUT, f"T_Banner_{k:02d}.png"))
    L, H = 6.0, 1.5
    for y in (-2.8, 0, 2.8):
        mb.box((0.08, 0.08, 1.9), (0.1, y, 0.95), m=mm["steel_dk"])
    mb.box((0.06, L, H), (0.04, 0, 1.15), m=mm["white"])
    mb.quad_uv([(-0.005, L / 2, 0.42), (-0.005, -L / 2, 0.42), (-0.005, -L / 2, 1.88), (-0.005, L / 2, 1.88)],
               ((0, 0), (1, 0), (1, 1), (0, 1)), tex)
    mb.quad_uv([(0.075, -L / 2, 0.42), (0.075, L / 2, 0.42), (0.075, L / 2, 1.88), (0.075, -L / 2, 1.88)],
               ((0, 0), (1, 0), (1, 1), (0, 1)), tex)
    return mb.to_object(origin="base", sharp_angle=None)


def bunting(mm, name="SM_Bunting_20m", L=20.0):
    mb = sr.MB(name)
    cols = [mm["flag"], mm["flag_w"], mm["gold"], mm["red"]]
    n = int(L / 0.6)
    pts = [(-L / 2 + L * i / n, 0, 6.0 - 1.0 * math.sin(math.pi * i / n)) for i in range(n + 1)]
    mb.tube(pts, 0.015, mm["steel_dk"], seg=4)
    for i in range(n):
        a, b = Vector(pts[i]), Vector(pts[i + 1])
        mb.poly([tuple(a + Vector((0.05, 0, 0))), tuple(b - Vector((0.05, 0, 0))), tuple((a + b) / 2 - Vector((0, 0, 0.5)))],
                cols[i % 4])
    for x in (-L / 2, L / 2):
        mb.cyl(0.08, 6.2, (x, 0, 3.1), m=mm["steel"], seg=6)
    return mb.to_object(origin="base", sharp_angle=None)


def flag_pole(mm, name="SM_FlagPole", H=10.0):
    mb = sr.MB(name)
    mb.cyl(0.08, H, (0, 0, H / 2), m=mm["steel"], seg=8, r2=0.05)
    grid = []
    for i in range(9):
        t = i / 8
        x = 0.1 + 3.0 * t
        wave = 0.25 * math.sin(t * 5)
        grid.append([(x, wave, H - 0.1), (x, wave, H - 2.0)])
    mb.strip(grid, None, mm["flag"], smooth=True, keep=True)
    return mb.to_object(origin="base", sharp_angle=None)


def marshal_post(mm, name="SM_MarshalPost"):
    mb = sr.MB(name)
    mb.box((2.2, 2.2, 0.15), (0, 0, 1.4), m=mm["concrete"])
    for x in (-1, 1):
        for y in (-1, 1):
            mb.box((0.1, 0.1, 1.4), (x, y, 0.7), m=mm["steel"])
    mb.box((2.2, 2.2, 0.08), (0, 0, 3.6), m=mm["orange"])
    for x in (-1, 1):
        mb.box((0.08, 0.08, 2.2), (x, 1.05, 2.5), m=mm["steel"])
    _person(mb, mm, "casual", (0.2, 0, 1.48), yaw=180, shirt=mm["orange"])
    mb.tube([(0.1, -0.3, 2.9), (-0.4, -0.6, 3.4)], 0.015, mm["steel_dk"], seg=4)
    mb.poly([(-0.4, -0.6, 3.4), (-0.4, -1.2, 3.35), (-0.4, -1.2, 2.95), (-0.4, -0.6, 3.0)], mm["yellow"])
    return mb.to_object(origin="base", sharp_angle=None)


def camera_tower(mm, name="SM_CameraTower"):
    mb = sr.MB(name)
    H = 8.0
    for x in (-1.2, 1.2):
        for y in (-1.2, 1.2):
            mb.cyl(0.05, H, (x, y, H / 2), m=mm["steel"], seg=6)
    for z in (2, 4, 6):
        for a, b in (((-1.2, -1.2), (1.2, 1.2)), ((1.2, -1.2), (-1.2, 1.2))):
            mb.tube([(a[0], a[1], z - 1.5), (b[0], b[1], z + 0.5)], 0.03, mm["steel"], seg=4)
    mb.box((2.8, 2.8, 0.12), (0, 0, H), m=mm["wood_dk"])
    mb.box((0.8, 0.35, 0.4), (0.3, 0, H + 1.4), m=mm["steel_dk"])                     # TV camera
    mb.cyl(0.12, 0.35, (0.8, 0, H + 1.4), (0, 90, 0), m=mm["glass"], seg=10)
    mb.tube([(0, 0, H), (0.2, 0, H + 1.2)], 0.04, mm["steel_dk"], seg=5)
    _person(mb, mm, "casual", (-0.6, 0.3, H + 0.06), yaw=0)
    mb.box((3.0, 3.0, 0.06), (0, 0, H + 2.4), m=mm["tent_white"])
    return mb.to_object(origin="base", sharp_angle=None)


def floodlight(mm, name="SM_Floodlight", H=18.0):
    mb = sr.MB(name)
    mb.cyl(0.3, H, (0, 0, H / 2), m=mm["steel"], seg=10, r2=0.18)
    mb.box((3.6, 0.3, 1.8), (0, -0.3, H + 0.6), (20, 0, 0), m=mm["steel_dk"])
    for i in range(4):
        for j in range(2):
            mb.box((0.7, 0.1, 0.6), (-1.2 + i * 0.8, -0.5, H + 0.25 + j * 0.75), (20, 0, 0), m=mm["flood"])
    return mb.to_object(origin="base", sharp_angle=None)


def distance_board(mm, name, dist):
    mb = sr.MB(name)
    tex = sr.mat(f"Distance_{dist}", (1, 1, 1), rough=0.5, image=os.path.join(TEXOUT, f"T_Distance_{dist}.png"))
    mb.cyl(0.05, 1.2, (0, 0, 0.6), m=mm["steel"], seg=6)
    mb.box((0.05, 0.9, 0.9), (0.03, 0, 1.55), m=mm["white"])
    mb.quad_uv([(-0.005, 0.45, 1.1), (-0.005, -0.45, 1.1), (-0.005, -0.45, 2.0), (-0.005, 0.45, 2.0)],
               ((0, 0), (1, 0), (1, 1), (0, 1)), tex)
    return mb.to_object(origin="base", sharp_angle=None)


def helicopter(mm, name="SM_Helicopter"):
    mb = sr.MB(name)
    mb.sphere(1.2, (0, 0, 0), m=mm["white"], seg=14, rings=8, scale=(2.0, 1.0, 1.05))
    mb.sphere(0.95, (1.05, 0, 0.15), m=mm["glass"], seg=12, rings=6, scale=(1.3, 0.92, 0.9))
    mb.tube([(-1.8, 0, 0.3), (-6.0, 0, 0.8)], [0.45, 0.18], mm["white"], seg=8)
    mb.box((0.1, 0.06, 1.4), (-6.0, 0.2, 1.2), m=mm["red"])
    mb.cyl(0.12, 0.5, (0, 0, 1.4), m=mm["steel_dk"], seg=8)
    for a in (0, 90):
        mb.box((10.5, 0.3, 0.04), (0, 0, 1.7), (0, 0, a + 20), m=mm["steel_dk"])
    for y in (-0.8, 0.8):
        mb.tube([(1.2, y, -1.35), (-1.2, y, -1.35)], 0.05, mm["steel_dk"], seg=5)
        for x in (0.7, -0.6):
            mb.tube([(x, y * 0.8, -0.8), (x, y, -1.35)], 0.04, mm["steel_dk"], seg=4)
    mb.box((2.0, 0.04, 0.35), (-0.2, -1.02, 0.0), m=mm["red"])
    mb.box((2.0, 0.04, 0.35), (-0.2, 1.02, 0.0), m=mm["red"])
    return mb.to_object(origin="center", sharp_angle=None)


def stacked_tyres(mm, name="SM_StackedTyres"):
    mb = sr.MB(name)
    for i in range(4):
        for lv in range(3):
            mb.lathe([(0.32, 0), (0.38, 0.05), (0.38, 0.22), (0.32, 0.27)], seg=12,
                     loc=(0, -1.2 + i * 0.8, lv * 0.27), m=mm["tyre"])
            if lv == 2:
                mb.lathe([(0.381, 0.08), (0.381, 0.19)], seg=12, loc=(0, -1.2 + i * 0.8, lv * 0.27),
                         m=mm["red"] if i % 2 else mm["white"])
    return mb.to_object(origin="base", sharp_angle=None)


# ------------------------------------------------------------------ plants ---
def shrub(mm, name, seed, r=0.9, m=None):
    rnd = random.Random(seed)
    mb = sr.MB(name)
    for k in range(7):
        a = rnd.uniform(0, 2 * math.pi)
        d = rnd.uniform(0, r * 0.6)
        mb.sphere(r * rnd.uniform(0.45, 0.7), (d * math.cos(a), d * math.sin(a), r * rnd.uniform(0.3, 0.6)),
                  m=m or mm["leaf"], seg=7, rings=4, scale=(1, 1, 0.7))
    return mb.to_object(origin="base", sharp_angle=None)


def sidr_tree(mm, name="SM_SidrTree", seed=4):
    rnd = random.Random(seed)
    mb = sr.MB(name)
    mb.tube([(0, 0, 0), (0.2, 0.1, 1.6), (0.1, 0.0, 2.6)], [0.28, 0.2, 0.14], mm["bark"], seg=7)
    for k in range(4):
        a = 2 * math.pi * k / 4 + rnd.uniform(-0.3, 0.3)
        mb.tube([(0.1, 0, 2.2), (1.4 * math.cos(a), 1.4 * math.sin(a), 3.3)], [0.1, 0.05], mm["bark"], seg=5)
    for k in range(14):
        a = rnd.uniform(0, 2 * math.pi)
        d = rnd.uniform(0.4, 2.4)
        mb.sphere(rnd.uniform(0.8, 1.3), (d * math.cos(a), d * math.sin(a), rnd.uniform(3.0, 4.3)), m=mm["leaf"], seg=7,
                  rings=4, scale=(1, 1, 0.6))
    return mb.to_object(origin="base", sharp_angle=None)


def grass_tuft(mm, name="SM_GrassTuft", seed=5, flowers=None):
    rnd = random.Random(seed)
    mb = sr.MB(name)
    for k in range(22):
        a = rnd.uniform(0, 2 * math.pi)
        d = rnd.uniform(0, 0.35)
        x, y = d * math.cos(a), d * math.sin(a)
        h = rnd.uniform(0.35, 0.75)
        lean = rnd.uniform(0, 2 * math.pi)
        tip = (x + 0.18 * math.cos(lean), y + 0.18 * math.sin(lean), h)
        n = (math.cos(lean + math.pi / 2) * 0.03, math.sin(lean + math.pi / 2) * 0.03)
        mb.poly([(x - n[0], y - n[1], 0), (x + n[0], y + n[1], 0), tip], mm["grass"])
        if flowers and rnd.random() < 0.4:
            mb.sphere(0.05, tip, m=flowers, seg=5, rings=3)
    return mb.to_object(origin="base", sharp_angle=None)


def grey_rock(mm, name, seed, size=1.6):
    rnd = random.Random(seed)
    mb = sr.MB(name)
    mb.sphere(size, (0, 0, size * 0.35), (rnd.uniform(0, 40), rnd.uniform(0, 40), rnd.uniform(0, 90)), m=mm["rock"],
              seg=7, rings=4, scale=(1.3, 1.0, 0.65))
    o = mb.to_object(origin="base", sharp_angle=30)
    sr.displace(o, size * 0.18, size * 0.8, "VORONOI")
    return o


# ------------------------------------------------------------------- build ---
def build_all():
    sr.reset()
    make_textures()
    mm = M()
    objs = [person(mm, "SM_Person_Thobe", "thobe"), person(mm, "SM_Person_Abaya", "abaya"),
            person(mm, "SM_Person_Casual", "casual", mm["shirts"][1]), person(mm, "SM_Person_Kid", "kid", mm["shirts"][2]),
            crowd(mm, "SM_Crowd_10m"), crowd(mm, "SM_CrowdCheer_10m", cheer=True, seed=9),
            camel(mm), camel(mm, "SM_Camel_Sitting", sitting=True), goat(mm),
            goat(mm, "SM_Goat_Brown", hide=mm["goat_b"]), goat(mm, "SM_Sheep", hide=mm["wool"], sheep=True),
            birds(mm), birds(mm, "SM_Seagulls", 10, white=True, seed=8),
            car(mm, "SM_Car_Sedan_White", "sedan", "White"), car(mm, "SM_Car_Sedan_Silver", "sedan", "Silver"),
            car(mm, "SM_Car_Sedan_Red", "sedan", "Red"), car(mm, "SM_Car_SUV_White", "suv", "White"),
            car(mm, "SM_Car_SUV_Black", "suv", "Black"), car(mm, "SM_Car_Pickup_White", "pickup", "White"),
            car(mm, "SM_Bus_City", "bus", "Bus"), car(mm, "SM_Truck_Water", "tanker", "White"),
            dhow(mm), fishing_boat(mm), yacht(mm), cargo_ship(mm),
            bedouin_tent(mm), event_tent(mm), gazebo(mm, "SM_Gazebo_Green", mm["canopy_g"]),
            gazebo(mm, "SM_Gazebo_Red", mm["canopy_r"]), campfire(mm), food_truck(mm),
            mosque_dome(mm), mosque_najdi(mm), villa(mm), shop_row(mm), gas_station(mm), water_tower(mm),
            beach_umbrella(mm), kiosk(mm), bench(mm), lamp_classic(mm), power_pylon(mm), road_sign(mm),
            chevron_board(mm)] + [sponsor_board(mm, f"SM_SponsorBoard_{k:02d}", k) for k in range(1, 5)] + [
            bunting(mm), flag_pole(mm), marshal_post(mm), camera_tower(mm), floodlight(mm),
            distance_board(mm, "SM_DistanceBoard_100", 100), distance_board(mm, "SM_DistanceBoard_200", 200),
            helicopter(mm), stacked_tyres(mm),
            shrub(mm, "SM_Shrub_A", 1), shrub(mm, "SM_Shrub_B", 2, 1.3, mm["leaf_dk"]), sidr_tree(mm),
            grass_tuft(mm), grass_tuft(mm, "SM_Flowers", 6, mm["flower_y"]), grass_tuft(mm, "SM_FlowersPink", 7, mm["flower_p"]),
            grey_rock(mm, "SM_RockGrey_A", 1, 1.4), grey_rock(mm, "SM_RockGrey_B", 2, 2.6)]
    for o in objs:
        print(f"{o.name}: {sr.tri_count(o)} tris")
    return objs


def lineup_render(objs):
    sr.layout_grid(objs, spacing=3.0, row_width=120)
    sr.ground(400, sr.mat("Sand", (1, 1, 1), tex="Sand", tile=6))
    sr.setup_render((1600, 900), 48)
    sr.world_sky(28, 200, 0.35)
    sr.sun((60, 0, 200), 3.5, (1.0, 0.88, 0.72), 1.5)
    sr.frame_camera(objs, (0.55, -1.0, 0.55), 35, margin=0.62)
    sr.render(os.path.join(sr.ROOT, "docs", "previews", f"kit_{KIT}.png"))


if __name__ == "__main__":
    objs = build_all()
    sr.export_kit(objs, KIT)
    sr.write_manifest()
    if "--no-render" not in sys.argv:
        lineup_render(objs)
