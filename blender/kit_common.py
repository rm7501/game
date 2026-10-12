"""Sahara Racers - shared props used on every map + gameplay pieces (cards, boosts, checkpoints).

Assets (assets/common/):
  SM_DatePalm_A/B/C       date palms (3 heights), two-sided foliage material
  SM_Acacia               umbrella acacia (AlUla / desert)
  SM_Barrier_Water        red/white water-filled race barrier
  SM_Barrier_Concrete     jersey barrier
  SM_TireStack            tyre wall segment
  SM_Cone                 traffic cone
  SM_Checkpoint_Arch      Najdi-pattern checkpoint arch with light strip
  SM_StartGantry          start / finish gantry with start lights (Arabic + English)
  SM_BoostPad             emissive chevron boost pad
  SM_JumpRamp             kicker ramp
  SM_CardPickup           floating ability-card pickup (card + holo ring + base)
  SM_Card                 single card (front/back UVs, swap the textures per character)
  SM_VFX_Shield           hex shield bubble   (ability mesh)
  SM_VFX_SandTornado      twisted sand funnel (ability mesh)
  SM_VFX_NitroFlame       exhaust flame cone  (ability mesh)
  SM_VFX_ShockRing        EMP / shock-wave ring (ability mesh)
  SM_VFX_SandTrap         sand-slick decal mesh (dropped hazard)
  SM_FalconDrone          homing falcon projectile (ability mesh)
  SM_Grandstand           spectator stand with canopy
  SM_Flag_Pennant         race pennant string
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))
import sr  # noqa: E402

import bpy  # noqa: E402
from mathutils import Vector, noise  # noqa: E402

KIT = "common"
OUT = os.path.join(sr.ROOT, "assets", KIT)
TEXOUT = os.path.join(OUT, "textures")


# ---------------------------------------------------------------- textures ---
def make_textures():
    """Card art + start gantry signs (Arabic + English). Needs PIL (skipped inside Blender)."""
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

    def star(d, cx, cy, r, col, width=4):
        """8-point Islamic star (two overlapping squares)."""
        for rot in (0, 45):
            pts = []
            for k in range(4):
                a = math.radians(rot + 45 + 90 * k)
                pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
            d.polygon(pts, outline=col, width=width)

    # card back: night-blue with gold girih star lattice + logo
    W, H = 630, 880
    im = Image.new("RGB", (W, H), (16, 20, 44))
    d = ImageDraw.Draw(im)
    for y in range(-60, H + 60, 90):
        for x in range(-60, W + 60, 90):
            star(d, x + (45 if (y // 90) % 2 else 0), y, 34, (70, 60, 40), 3)
    d.rounded_rectangle([18, 18, W - 18, H - 18], 28, outline=(214, 170, 90), width=10)
    d.rounded_rectangle([40, 40, W - 40, H - 40], 20, outline=(214, 170, 90), width=3)
    d.ellipse([W / 2 - 170, H / 2 - 170, W / 2 + 170, H / 2 + 170], fill=(16, 20, 44), outline=(214, 170, 90), width=8)
    star(d, W / 2, H / 2, 130, (232, 190, 100), 8)
    f1 = ImageFont.truetype(bold, 64)
    f2 = ImageFont.truetype(bold, 46)
    for txt, f, y in ((ar("سباق الصحراء"), f1, 120), ("SAHARA RACERS", f2, 730)):
        l, t, r, b = d.textbbox((0, 0), txt, font=f)
        d.text(((W - (r - l)) / 2 - l, y), txt, font=f, fill=(240, 205, 120))
    im.save(os.path.join(TEXOUT, "T_CardBack.png"))

    # card front template (character art goes in the window; replace per character in Unreal)
    im = Image.new("RGB", (W, H), (230, 214, 182))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([18, 18, W - 18, H - 18], 28, outline=(120, 70, 30), width=12)
    d.rectangle([48, 120, W - 48, 560], fill=(60, 40, 30))
    for k in range(9):
        d.line([(48, 560 - k * 50), (W - 48, 560 - k * 50 - 30)], fill=(80, 56, 40), width=3)
    d.text((60, 40), "CHARACTER", font=ImageFont.truetype(bold, 52), fill=(80, 40, 20))
    d.text((60, 590), "ABILITY", font=ImageFont.truetype(bold, 44), fill=(80, 40, 20))
    for k in range(4):
        d.line([(60, 660 + k * 44), (W - 60, 660 + k * 44)], fill=(150, 120, 90), width=4)
    star(d, W - 90, 75, 34, (180, 100, 30), 6)
    im.save(os.path.join(TEXOUT, "T_CardFront_Template.png"))

    # start gantry banner
    im = Image.new("RGB", (2048, 256), (12, 70, 45))
    d = ImageDraw.Draw(im)
    for x in range(0, 2048, 64):
        star(d, x + 32, 26, 16, (30, 110, 70), 3)
        star(d, x + 32, 230, 16, (30, 110, 70), 3)
    f = ImageFont.truetype(bold, 120)
    for txt, cx in ((ar("سباق الصحراء"), 560), ("SAHARA RACERS", 1480)):
        l, t, r, b = d.textbbox((0, 0), txt, font=f)
        d.text((cx - (r - l) / 2 - l, 128 - (b - t) / 2 - t), txt, font=f, fill=(250, 245, 230))
    im.save(os.path.join(TEXOUT, "T_StartBanner.png"))

    # checkpoint banner
    im = Image.new("RGB", (1024, 256), (150, 60, 20))
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(bold, 96)
    for txt, cx in ((ar("نقطة تفتيش"), 300), ("CHECKPOINT", 760)):
        l, t, r, b = d.textbbox((0, 0), txt, font=f if cx < 500 else ImageFont.truetype(bold, 80))
        ff = f if cx < 500 else ImageFont.truetype(bold, 80)
        d.text((cx - (r - l) / 2 - l, 128 - (b - t) / 2 - t), txt, font=ff, fill=(255, 240, 210))
    im.save(os.path.join(TEXOUT, "T_CheckpointBanner.png"))


# ------------------------------------------------------------------ plants ---
def date_palm(name="SM_DatePalm_A", height=9.0, fronds=26, seed=1, lean=4.0, dates=True):
    rnd = random.Random(seed)
    trunk_m = sr.mat("PalmTrunk", (0.42, 0.33, 0.24), rough=0.95, tex="MudPlaster", tile=0.6)
    frond_m = sr.mat("PalmFrond", (0.26, 0.34, 0.15), rough=0.6, kind="foliage")
    dead_m = sr.mat("PalmFrondDry", (0.45, 0.36, 0.22), rough=0.8, kind="foliage")
    date_m = sr.mat("PalmDates", (0.62, 0.3, 0.05), rough=0.4)
    mb = sr.MB(name)
    # trunk: knobbly diamond leaf-base pattern via vertex displacement, gentle lean/curve
    seg, rings = 18, int(height / 0.14)
    lean_r = math.radians(lean)
    pts = []
    for j in range(rings + 1):
        z = height * j / rings
        f = z / height
        cx = math.sin(lean_r) * height * f * f
        ring = []
        r0 = 0.32 - 0.08 * f + (0.08 if j < 3 else 0)
        for i in range(seg):
            a = 2 * math.pi * i / seg
            phase = (j * 0.5 + i * 0.5) % 1.0
            knob = 0.045 * (1 - abs(phase - 0.5) * 2)
            r = r0 + knob
            ring.append((cx + r * math.cos(a), r * math.sin(a), z))
        pts.append(ring)
    mb.loft(pts, trunk_m, closed=True, cap_end=True, smooth=True)
    top = Vector((math.sin(lean_r) * height, 0, height))
    # crown boss
    mb.sphere(0.42, tuple(top + Vector((0, 0, 0.1))), m=trunk_m, seg=12, rings=8, scale=(1, 1, 1.3))
    # fronds
    golden = math.pi * (3 - math.sqrt(5))
    for k in range(fronds):
        az = k * golden + rnd.uniform(-0.1, 0.1)
        frac = k / fronds                         # 0 = young (upright) ... 1 = old (drooping)
        elev = math.radians(70 - 95 * frac + rnd.uniform(-8, 8))
        length = rnd.uniform(3.2, 4.2) * (0.8 + 0.25 * frac)
        droop = 0.35 + 1.4 * frac
        d0 = Vector((math.cos(az) * math.cos(elev), math.sin(az) * math.cos(elev), math.sin(elev)))
        m = dead_m if frac > 0.93 else frond_m
        frond(mb, top, d0, length, droop, m, trunk_m, rnd)
    # date clusters
    if dates:
        for k in range(5):
            az = 2 * math.pi * k / 5 + rnd.uniform(-0.3, 0.3)
            p = top + Vector((math.cos(az) * 0.55, math.sin(az) * 0.55, -0.55))
            mb.tube([tuple(top + Vector((math.cos(az) * 0.3, math.sin(az) * 0.3, -0.1))), tuple(p)], 0.025, trunk_m, seg=5)
            for q in range(10):
                o = Vector((rnd.uniform(-0.15, 0.15), rnd.uniform(-0.15, 0.15), rnd.uniform(-0.45, 0.0)))
                mb.sphere(0.07, tuple(p + o), m=date_m, seg=6, rings=4, scale=(1, 1, 1.4))
    return mb.to_object(sharp_angle=None)


def frond(mb, base, d0, length, droop, m, rachis_m, rnd):
    """Pinnate frond: curved rachis + V-folded leaflet pairs (single quads, two-sided material)."""
    up = Vector((0, 0, 1))
    side = d0.cross(up)
    if side.length < 1e-3:
        side = Vector((1, 0, 0))
    side.normalize()
    pts = []
    n = 14
    for i in range(n + 1):
        t = i / n
        p = base + d0 * length * t - up * droop * t * t
        pts.append(p)
    mb.tube([tuple(p) for p in pts], [0.035 * (1 - 0.8 * i / n) for i in range(n + 1)], rachis_m, seg=5)
    nl = 34
    for i in range(nl):
        t = 0.18 + 0.82 * i / nl
        fi = t * n
        i0 = min(int(fi), n - 1)
        p = pts[i0].lerp(pts[i0 + 1], fi - i0)
        tan = (pts[i0 + 1] - pts[i0]).normalized()
        nrm = tan.cross(side).normalized()
        ll = 0.62 * (1 - 0.65 * t) + 0.12
        w = 0.035
        for sg in (1, -1):
            # leaflet direction: sideways, swept forward, folded up into a V
            dirv = (side * sg * 0.75 + tan * 0.55 + nrm * 0.35).normalized()
            dirv = (dirv + Vector((rnd.uniform(-.06, .06), rnd.uniform(-.06, .06), rnd.uniform(-.06, .06)))).normalized()
            wv = tan * w
            a = p - wv * 0.5
            b = p + wv * 0.5
            c = p + dirv * ll + wv * 0.1
            d = p + dirv * ll - wv * 0.1
            mb.poly([tuple(a), tuple(b), tuple(c), tuple(d)], m, smooth=False)


def acacia(name="SM_Acacia", seed=3):
    """Flat-topped umbrella thorn tree (Vachellia) common around AlUla."""
    rnd = random.Random(seed)
    bark = sr.mat("AcaciaBark", (0.28, 0.22, 0.17), rough=0.95, tex="Rock", tile=1.0)
    leaf = sr.mat("AcaciaLeaves", (0.30, 0.36, 0.16), rough=0.7, kind="foliage")
    mb = sr.MB(name)
    trunk = [(0, 0, 0), (0.1, 0.05, 1.0), (0.05, 0.0, 1.8)]
    mb.tube(trunk, [0.22, 0.17, 0.14], bark, seg=10)
    tips = []
    for k in range(6):
        az = 2 * math.pi * k / 6 + rnd.uniform(-0.3, 0.3)
        r = rnd.uniform(2.0, 3.2)
        mid = (0.05 + math.cos(az) * r * 0.45, math.sin(az) * r * 0.45, 2.7 + rnd.uniform(-0.2, 0.3))
        tip = (math.cos(az) * r, math.sin(az) * r, 3.6 + rnd.uniform(-0.2, 0.4))
        mb.tube([trunk[-1], mid, tip], [0.12, 0.08, 0.04], bark, seg=7)
        tips.append(tip)
    canopy = sr.MB("canopy")
    for k in range(26):
        az = rnd.uniform(0, 2 * math.pi)
        r = rnd.uniform(0, 3.2)
        c = (math.cos(az) * r, math.sin(az) * r, 3.9 + rnd.uniform(-0.2, 0.25) - 0.04 * r * r)
        canopy.sphere(rnd.uniform(0.8, 1.3), c, m=leaf, seg=10, rings=6, scale=(1, 1, 0.38))
    co = canopy.to_object(uv=False)
    sr.remesh(co, 0.22)
    sr.displace(co, 0.35, 0.45, "VORONOI", subdiv=0)
    mb.add_object(co)
    bpy.data.objects.remove(co, do_unlink=True)
    return mb.to_object(sharp_angle=None)


# ------------------------------------------------------------- race props ---
def barrier_water(name="SM_Barrier_Water"):
    red = sr.mat("Plastic_Red", (0.6, 0.04, 0.03), rough=0.45)
    white = sr.mat("Plastic_White", (0.85, 0.85, 0.83), rough=0.45)
    mb = sr.MB(name)
    prof = [(-0.3, 0), (0.3, 0), (0.28, 0.12), (0.12, 0.35), (0.11, 0.85), (0.14, 0.95), (-0.14, 0.95),
            (-0.11, 0.85), (-0.12, 0.35), (-0.28, 0.12)]
    for k, m in ((0, red), (1, white)):
        x0 = -1.0 + k * 1.0
        rings = [[(x0 + 0.03, y, z) for y, z in prof], [(x0 + 0.97, y, z) for y, z in prof]]
        mb.loft(rings, m, closed=True, cap_start=True, cap_end=True, smooth=False)
    mb.box((0.15, 0.05, 0.05), (1.0, 0, 0.8), m=white)
    return mb.to_object(origin="base")


def barrier_concrete(name="SM_Barrier_Concrete", length=4.0):
    c = sr.mat("Concrete", (1, 1, 1), tex="Concrete", tile=2.0)
    stripe = sr.mat("ReflectorStripe", (0.9, 0.75, 0.1), rough=0.3, emit=(1, 0.75, 0.1), emit_str=0.5)
    mb = sr.MB(name)
    prof = [(-0.3, 0), (0.3, 0), (0.3, 0.08), (0.2, 0.33), (0.08, 0.81), (-0.08, 0.81), (-0.2, 0.33), (-0.3, 0.08)]
    rings = [[(x, y, z) for y, z in prof] for x in (-length / 2, length / 2)]
    mb.loft(rings, c, closed=True, cap_start=True, cap_end=True, smooth=False)
    for sg in (1, -1):
        mb.box((length * 0.9, 0.01, 0.08), (0, sg * 0.15, 0.55), (sg * -14, 0, 0), m=stripe)
    return mb.to_object(origin="base")


def tire_stack(name="SM_TireStack"):
    t = sr.mat("Car_Tire", (0.025, 0.025, 0.027), rough=0.88)
    w = sr.mat("Plastic_White", (0.85, 0.85, 0.83), rough=0.45)
    r = sr.mat("Plastic_Red", (0.6, 0.04, 0.03), rough=0.45)
    mb = sr.MB(name)
    for i in range(5):
        for j in range(4):
            prof = [(0.22, -0.11), (0.31, -0.12), (0.34, -0.07), (0.34, 0.07), (0.31, 0.12), (0.22, 0.11)]
            mb.lathe(prof, seg=20, loc=(i * 0.66 - 1.32, 0, 0.12 + j * 0.24), m=t, close_top=False)
        mb.box((0.66, 0.7, 0.04), (i * 0.66 - 1.32, 0, 0.98), m=(w if i % 2 else r))
    return mb.to_object(origin="base")


def cone(name="SM_Cone"):
    o = sr.mat("Plastic_Orange", (0.9, 0.3, 0.02), rough=0.45)
    w = sr.mat("ReflectorWhite", (0.9, 0.9, 0.9), rough=0.3)
    mb = sr.MB(name)
    mb.box((0.38, 0.38, 0.03), (0, 0, 0.015), m=o, bevel=0.02, seg=2)
    mb.lathe([(0.15, 0.03), (0.12, 0.25), (0.105, 0.33), (0.08, 0.5), (0.035, 0.7), (0.0, 0.7)], seg=24, m=o)
    mb.lathe([(0.112, 0.28), (0.096, 0.38), (0.093, 0.39)], seg=24, m=w)
    return mb.to_object(origin="base")


def najdi_arch_profile(span, height, rise, n=24, pointed=False):
    """Arch outline from springline `height` to apex `height + rise`.
    pointed=True : two-centred Gothic arch, radius r = (a^2 + h^2) / 2a (needs rise >= half-span)
    otherwise    : segmental arch, one circle through both springings and the apex, r = (a^2 + h^2) / 2h"""
    a = span / 2
    pts = []
    if pointed and rise >= a:
        r = (a * a + rise * rise) / (2 * a)
        for i in range(n + 1):
            x = -a + span * i / n
            cx = -a + r if x < 0 else a - r
            pts.append((x, height + math.sqrt(max(r * r - (x - cx) ** 2, 0.0))))
        return pts
    r = (a * a + rise * rise) / (2 * rise)
    cz = height + rise - r
    for i in range(n + 1):
        x = -a + span * i / n
        pts.append((x, cz + math.sqrt(max(r * r - x * x, 0.0))))
    return pts


def checkpoint_arch(name="SM_Checkpoint_Arch", span=22.0):
    stone = sr.mat("Limestone", (0.9, 0.8, 0.64), tex="MudPlaster", tile=3.0)
    trim = sr.mat("ArchTrimDark", (0.18, 0.12, 0.08), rough=0.7)
    led = sr.mat("LED_Amber", (1.0, 0.55, 0.15), emit=(1.0, 0.55, 0.15), emit_str=12, kind="emissive")
    banner = sr.mat("CheckpointBanner", (1, 1, 1), rough=0.6,
                    image=os.path.join(TEXOUT, "T_CheckpointBanner.png"))
    mb = sr.MB(name)
    pw = 2.2
    spring, rise = 5.5, 3.0
    top = spring + rise + 1.8
    ph = top
    for sg in (1, -1):
        x = sg * (span / 2 + pw / 2)
        mb.box((pw, 2.2, ph), (x, 0, ph / 2), m=stone, bevel=0.05)
        mb.box((pw + 0.4, 2.6, 0.5), (x, 0, 0.25), m=stone)
        mb.box((pw + 0.3, 2.5, 0.35), (x, 0, spring - 0.2), m=trim)
        # Najdi triangle vents
        for k in range(3):
            z = 5.0 + k * 0.8
            mb.prism([(-0.25, 0), (0.25, 0), (0, 0.45)], -1.12, 1.12, (x, 0, z), (90, 0, 0), m=trim)
    # beam with pointed-arch soffit
    outline = najdi_arch_profile(span, spring, rise)
    beam = sr.MB("beam")
    beam.prism([(-span / 2 - 0.01, spring), (span / 2 + 0.01, spring), (span / 2 + 0.01, top), (-span / 2 - 0.01, top)],
               -1.1, 1.1, rot=(90, 0, 0), m=stone)
    bo = beam.to_object(uv=False)
    cut = sr.MB("cut")
    poly = [(-span / 2 - 0.5, spring - 1), (span / 2 + 0.5, spring - 1)] + [(p[0], p[1]) for p in reversed(outline)]
    cut.prism(poly, -2, 2, rot=(90, 0, 0), m=stone)
    sr.boolean(bo, cut.to_object(uv=False))
    mb.add_object(bo)
    bpy.data.objects.remove(bo, do_unlink=True)
    # crenellations (stepped Najdi merlons)
    n = int((span + 2 * pw) / 1.1)
    for k in range(n):
        x = -span / 2 - pw + 0.55 + k * 1.1
        mb.prism([(-0.35, 0), (0.35, 0), (0.35, 0.35), (0.18, 0.35), (0.18, 0.7), (-0.18, 0.7), (-0.18, 0.35), (-0.35, 0.35)],
                 -0.6, 0.6, (x, 0, top), (90, 0, 0), m=stone)
    # LED strip following the arch + banner both sides
    path = [(x, 1.13, z - 0.15) for x, z in outline]
    mb.tube(path, 0.07, led, seg=6)
    mb.tube([(x, -1.13, z) for (x, _, z) in path], 0.07, led, seg=6)
    for sg in (1, -1):
        y = sg * 1.12
        w2 = 4.8
        pts = [(-w2, y, top - 1.35), (w2, y, top - 1.35), (w2, y, top - 0.15), (-w2, y, top - 0.15)]
        if sg > 0:     # viewer at +Y sees -X as "right": swap so the text reads correctly, CCW winding
            pts = [pts[1], pts[0], pts[3], pts[2]]
        mb.quad_uv(pts, ((0, 0), (1, 0), (1, 1), (0, 1)), banner)
    return mb.to_object(origin="base")


def start_gantry(name="SM_StartGantry", span=24.0):
    steel = sr.mat("SteelDark", (0.08, 0.08, 0.09), rough=0.4, metal=1.0)
    banner = sr.mat("StartBanner", (1, 1, 1), rough=0.6, image=os.path.join(TEXOUT, "T_StartBanner.png"))
    red = sr.mat("StartLight_Red", (0.6, 0.02, 0.02), emit=(1, 0.02, 0.02), emit_str=10, kind="emissive")
    grn = sr.mat("StartLight_Green", (0.02, 0.5, 0.1), emit=(0.1, 1, 0.2), emit_str=10, kind="emissive")
    housing = sr.mat("Car_TrimBlack", (0.015, 0.015, 0.017), rough=0.55)
    chk_w = sr.mat("Checker_White", (0.9, 0.9, 0.9), rough=0.5)
    chk_b = sr.mat("Checker_Black", (0.02, 0.02, 0.02), rough=0.5)
    mb = sr.MB(name)
    h = 9.0
    for sg in (1, -1):
        x = sg * span / 2
        for dy in (-0.6, 0.6):
            mb.box((0.35, 0.35, h), (x, dy, h / 2), m=steel)
        for k in range(8):   # lattice bracing
            z = 0.5 + k * 1.05
            mb.tube([(x, -0.6, z), (x, 0.6, z + 1.0)], 0.04, steel, seg=6)
    for dz in (h - 0.2, h + 1.8):
        for dy in (-0.6, 0.6):
            mb.box((span + 0.4, 0.3, 0.3), (0, dy, dz), m=steel)
    a, b = span / 2 - 0.6, -span / 2 + 0.6
    uv = ((0, 0), (1, 0), (1, 1), (0, 1))
    mb.quad_uv([(a, 0.75, h + 0.05), (b, 0.75, h + 0.05), (b, 0.75, h + 1.55), (a, 0.75, h + 1.55)], uv, banner)
    mb.quad_uv([(b, -0.75, h + 0.05), (a, -0.75, h + 0.05), (a, -0.75, h + 1.55), (b, -0.75, h + 1.55)], uv, banner)
    # 5 start lights pods (top two rows red, bottom green)
    for k in range(5):
        x = -2.4 + k * 1.2
        mb.box((0.9, 0.4, 1.6), (x, 0, h - 1.2), m=housing, bevel=0.08, seg=2)
        for z, m in ((h - 0.75, red), (h - 1.2, red), (h - 1.65, grn)):
            for sy in (1, -1):
                mb.cyl(0.17, 0.08, (x, sy * 0.2, z), (90, 0, 0), m=m, seg=20)
    # chequered strip under banner
    for k in range(int(span / 0.5)):
        x = -span / 2 + 0.25 + k * 0.5
        mb.box((0.5, 0.62, 0.25), (x, 0, h - 0.48), m=chk_w if k % 2 else chk_b)
    return mb.to_object(origin="base")


def boost_pad(name="SM_BoostPad"):
    base = sr.mat("BoostBase", (0.03, 0.03, 0.04), rough=0.3, metal=0.5)
    glow = sr.mat("BoostGlow", (0.1, 0.8, 1.0), emit=(0.1, 0.8, 1.0), emit_str=15, kind="emissive")
    mb = sr.MB(name)
    mb.box((6.0, 4.0, 0.06), (0, 0, 0.03), m=base, bevel=0.03, seg=2)
    for k in range(4):
        x = -1.8 + k * 1.2
        for sg in (1, -1):
            mb.box((0.25, 1.6, 0.02), (x + 0.35, sg * 0.62, 0.07), (0, 0, -sg * 35), m=glow)
    for sg in (1, -1):
        mb.box((6.0, 0.08, 0.02), (0, sg * 1.96, 0.07), m=glow)
    return mb.to_object(origin="base")


def jump_ramp(name="SM_JumpRamp"):
    c = sr.mat("RampSteel", (0.5, 0.5, 0.52), rough=0.5, metal=1.0, tex="MetalPanels", tile=1.0)
    y = sr.mat("HazardYellow", (0.9, 0.7, 0.05), rough=0.5)
    mb = sr.MB(name)
    L, W, H = 8.0, 6.0, 1.6
    prof = [(0, 0)] + [(L * t, H * t * t) for t in [i / 12 for i in range(1, 13)]] + [(L, 0)]
    mb.prism(prof, -W / 2, W / 2, rot=(90, 0, 0), m=c)
    for k in range(8):
        mb.box((0.25, 0.75, 0.02), (L - 0.15, -W / 2 + 0.375 + k * 0.75, H + 0.01), m=y if k % 2 else c)
    return mb.to_object(origin="base")


def card(name="SM_Card", w=0.63, h=0.88, t=0.012):
    """Playing card with front/back UV quads (front = template, back = Sahara Racers back)."""
    front = sr.mat("CardFront", (1, 1, 1), rough=0.35, image=os.path.join(TEXOUT, "T_CardFront_Template.png"))
    back = sr.mat("CardBack", (1, 1, 1), rough=0.35, image=os.path.join(TEXOUT, "T_CardBack.png"))
    edge = sr.mat("CardEdge", (0.84, 0.66, 0.34), rough=0.25, metal=1.0)
    mb = sr.MB(name)
    hw, hh = w / 2, h / 2
    mb.quad_uv([(t / 2, -hw, -hh), (t / 2, hw, -hh), (t / 2, hw, hh), (t / 2, -hw, hh)], ((0, 0), (1, 0), (1, 1), (0, 1)), front)
    mb.quad_uv([(-t / 2, hw, -hh), (-t / 2, -hw, -hh), (-t / 2, -hw, hh), (-t / 2, hw, hh)], ((0, 0), (1, 0), (1, 1), (0, 1)), back)
    mb.box((t * 0.98, w, 0.006), (0, 0, hh - 0.003), m=edge)
    mb.box((t * 0.98, w, 0.006), (0, 0, -hh + 0.003), m=edge)
    mb.box((t * 0.98, 0.006, h), (0, hw - 0.003, 0), m=edge)
    mb.box((t * 0.98, 0.006, h), (0, -hw + 0.003, 0), m=edge)
    return mb.to_object()


def card_pickup(name="SM_CardPickup"):
    """Floating pickup: enlarged card over a glowing hex pedestal with a holo ring (rotate the card in UE)."""
    base = sr.mat("PickupBase", (0.06, 0.05, 0.05), rough=0.3, metal=0.8)
    gold = sr.mat("PickupGold", (0.85, 0.6, 0.25), rough=0.25, metal=1.0)
    holo = sr.mat("PickupHolo", (0.9, 0.6, 0.2), emit=(1.0, 0.65, 0.2), emit_str=10, kind="emissive")
    mb = sr.MB(name)
    mb.cyl(1.1, 0.25, (0, 0, 0.125), m=base, seg=6, smooth=False)
    mb.cyl(0.95, 0.06, (0, 0, 0.28), m=holo, seg=6, smooth=False)
    mb.lathe([(1.15, 1.6), (1.25, 1.6), (1.25, 1.66), (1.15, 1.66)], seg=48, m=holo)
    for k in range(6):
        a = 2 * math.pi * k / 6
        mb.box((0.12, 0.12, 0.35), (1.05 * math.cos(a), 1.05 * math.sin(a), 0.3), (0, 0, math.degrees(a)), m=gold)
    c = card("tmp_card", 1.26, 1.76, 0.03)
    mb.add_object(c, loc=(0, 0, 1.6))
    bpy.data.objects.remove(c, do_unlink=True)
    return mb.to_object(origin="base")


# ---------------------------------------------------------- ability meshes ---
def vfx_shield(name="SM_VFX_Shield"):
    m = sr.mat("VFX_ShieldHex", (0.2, 0.8, 1.0), emit=(0.2, 0.8, 1.0), emit_str=4, kind="emissive", alpha=0.35)
    mb = sr.MB(name)
    # geodesic-ish: icosphere hexes approximated by per-face inset frames
    import bmesh
    tmp = bmesh.new()
    bmesh.ops.create_icosphere(tmp, subdivisions=3, radius=1.0)
    for f in tmp.faces:
        c = f.calc_center_median()
        vs = [v.co for v in f.verts]
        inner = [c.lerp(v, 0.78) for v in vs]
        S = Vector((3.2, 2.0, 1.55))           # encloses a 4.6 m car
        sc = lambda v: tuple(Vector((v.x * S.x, v.y * S.y, v.z * S.z)))  # noqa: E731
        for i in range(3):
            a, b = vs[i], vs[(i + 1) % 3]
            ia, ib = inner[i], inner[(i + 1) % 3]
            mb.poly([sc(a), sc(b), sc(ib), sc(ia)], m)
    tmp.free()
    return mb.to_object(uv=True, sharp_angle=None)


def vfx_tornado(name="SM_VFX_SandTornado"):
    m = sr.mat("VFX_Sand", (0.85, 0.65, 0.4), rough=0.9, kind="foliage", alpha=0.6)
    mb = sr.MB(name)
    for arm in range(3):
        rings = []
        for j in range(40):
            t = j / 39
            z = t * 14
            r = 0.6 + 4.0 * t ** 1.6
            twist = arm * 2 * math.pi / 3 + t * 6.0
            ring = []
            for i in range(10):
                a = twist + (i / 10) * 1.6
                ring.append((r * math.cos(a), r * math.sin(a), z + 0.4 * math.sin(i / 9 * math.pi)))
            rings.append(ring)
        mb.loft(rings, m, closed=False, smooth=True)
    return mb.to_object(origin="base", sharp_angle=None)


def vfx_flame(name="SM_VFX_NitroFlame"):
    core = sr.mat("VFX_FlameCore", (0.6, 0.85, 1.0), emit=(0.5, 0.8, 1.0), emit_str=20, kind="emissive")
    outer = sr.mat("VFX_FlameOuter", (1.0, 0.45, 0.1), emit=(1.0, 0.4, 0.08), emit_str=10, kind="emissive", alpha=0.6)
    mb = sr.MB(name)
    prof = [(0.0, 0.0), (0.09, 0.05), (0.1, 0.3), (0.06, 0.9), (0.0, 1.3)]
    mb.lathe(prof, seg=16, rot=(0, -90, 0), m=core)
    prof = [(0.0, -0.02), (0.14, 0.05), (0.17, 0.4), (0.1, 1.2), (0.0, 1.9)]
    mb.lathe(prof, seg=16, rot=(0, -90, 0), m=outer)
    return mb.to_object(sharp_angle=None)


def vfx_ring(name="SM_VFX_ShockRing"):
    m = sr.mat("VFX_Shock", (0.6, 0.4, 1.0), emit=(0.6, 0.4, 1.0), emit_str=12, kind="emissive", alpha=0.7)
    mb = sr.MB(name)
    mb.lathe([(3.6, 0.0), (4.0, 0.35), (4.2, 0.5), (4.6, 0.3), (5.0, 0.0)], seg=96, m=m)
    return mb.to_object(sharp_angle=None)


def vfx_sandtrap(name="SM_VFX_SandTrap"):
    m = sr.mat("SandTrap", (0.86, 0.66, 0.42), tex="Sand", tile=2.0)
    mb = sr.MB(name)

    def fn(x, y):
        r = math.hypot(x, y * 1.4)
        h = max(0.0, 0.25 * (1 - (r / 2.6) ** 2))
        return h + 0.04 * noise.noise(Vector((x * 1.5, y * 1.5, 0.3)))
    mb.grid(fn, 40, 40, -3, 3, -2.2, 2.2, m=m)
    return mb.to_object(origin="base", sharp_angle=None)


def falcon_drone(name="SM_FalconDrone"):
    """Stylised saker falcon used for a homing attack ability (wings spread, flying +X)."""
    body = sr.mat("Falcon_Feathers", (0.45, 0.33, 0.22), rough=0.8)
    belly = sr.mat("Falcon_Belly", (0.85, 0.78, 0.66), rough=0.8)
    beak = sr.mat("Falcon_Beak", (0.85, 0.7, 0.2), rough=0.4)
    eye = sr.mat("Falcon_Eye", (0.02, 0.02, 0.02), rough=0.1)
    hood = sr.mat("Falcon_Hood", (0.5, 0.15, 0.08), rough=0.5)
    mb = sr.MB(name)
    rings = []
    prof = [(-0.55, 0.02, 0.0), (-0.35, 0.09, 0.0), (0.0, 0.14, 0.02), (0.22, 0.12, 0.04), (0.35, 0.08, 0.06), (0.42, 0.03, 0.06)]
    for x, r, dz in prof:
        rings.append([(x, r * math.cos(a), dz + r * 0.85 * math.sin(a)) for a in [2 * math.pi * i / 12 for i in range(12)]])
    mb.loft(rings, body, closed=True, cap_start=True, cap_end=True, smooth=True)
    mb.sphere(0.1, (0.3, 0, 0.09), m=hood, seg=12, rings=8)
    mb.lathe([(0.03, 0), (0.0, 0.08)], seg=8, loc=(0.38, 0, 0.07), rot=(0, 110, 0), m=beak)
    for sg in (1, -1):
        mb.sphere(0.018, (0.36, sg * 0.05, 0.11), m=eye, seg=8, rings=4)
        # wing: feathered trailing edge
        root = Vector((0.05, sg * 0.1, 0.06))
        for k in range(9):
            t = k / 8
            p = root + Vector((-0.1 * t, sg * (0.15 + 0.85 * t), 0.08 * math.sin(t * math.pi)))
            length = 0.42 - 0.18 * t
            sweep = Vector((-length, sg * 0.05 * t, 0))
            mb.poly([tuple(p + Vector((0.08, 0, 0))), tuple(p + Vector((0.08, sg * 0.1, 0))),
                     tuple(p + sweep + Vector((0, sg * 0.12, -0.01))), tuple(p + sweep + Vector((0, 0, -0.01)))],
                    body if k % 2 else belly)
    for k in range(5):   # fanned tail
        a = math.radians(-24 + 12 * k)
        mb.poly([(-0.5, -0.03, 0.0), (-0.5, 0.03, 0.0),
                 (-0.5 - 0.35 * math.cos(a), 0.35 * math.sin(a) + 0.04, -0.01),
                 (-0.5 - 0.35 * math.cos(a), 0.35 * math.sin(a) - 0.04, -0.01)], body)
    o = mb.to_object(sharp_angle=None)
    sr.apply_scale(o, 2.2)
    return o


def grandstand(name="SM_Grandstand", length=30.0, rows=10):
    c = sr.mat("Concrete", (1, 1, 1), tex="Concrete", tile=2.0)
    seat_cols = [sr.mat("Seat_Green", (0.02, 0.35, 0.18), rough=0.5), sr.mat("Plastic_White", (0.85, 0.85, 0.83), rough=0.45)]
    roof = sr.mat("CanopyFabric", (0.92, 0.9, 0.85), rough=0.7, kind="foliage")
    steel = sr.mat("SteelDark", (0.08, 0.08, 0.09), rough=0.4, metal=1.0)
    mb = sr.MB(name)
    for r in range(rows):
        z = 0.5 + r * 0.45
        y = r * 0.8
        mb.box((length, 0.8, z), (0, y, z / 2), m=c)
        for k in range(int(length / 0.55)):
            x = -length / 2 + 0.3 + k * 0.55
            m = seat_cols[0] if (k // 6 + r) % 3 else seat_cols[1]
            mb.box((0.45, 0.4, 0.08), (x, y + 0.1, z + 0.22), m=m)
            mb.box((0.45, 0.06, 0.35), (x, y + 0.32, z + 0.4), m=m)
    top = 0.5 + rows * 0.45 + 3.5
    for k in range(5):
        x = -length / 2 + k * length / 4
        mb.box((0.3, 0.3, top), (x, rows * 0.8 + 0.3, top / 2), m=steel)
    # tensile canopy: sawtooth sails
    for k in range(6):
        x0 = -length / 2 + k * length / 6
        x1 = x0 + length / 6
        mb.poly([(x0, -1.0, top - 1.2), (x1, -1.0, top - 1.2), (x1, rows * 0.8 + 0.5, top), (x0, rows * 0.8 + 0.5, top)], roof)
        mb.poly([((x0 + x1) / 2, -1.0, top - 0.6), (x1, -1.0, top - 1.2), (x0, -1.0, top - 1.2)], roof)
    return mb.to_object(origin="base")


def pennants(name="SM_Flag_Pennant", length=20.0):
    cols = [sr.mat("Pennant_Green", (0.0, 0.42, 0.22), rough=0.7, kind="foliage"),
            sr.mat("Plastic_White", (0.85, 0.85, 0.83), rough=0.45),
            sr.mat("Pennant_Gold", (0.85, 0.62, 0.15), rough=0.7, kind="foliage")]
    rope = sr.mat("SteelDark", (0.08, 0.08, 0.09), rough=0.4, metal=1.0)
    mb = sr.MB(name)
    n = int(length / 0.5)
    pts = [(-length / 2 + length * i / n, 0, -0.8 * math.sin(math.pi * i / n)) for i in range(n + 1)]
    mb.tube(pts, 0.012, rope, seg=5)
    for i in range(n):
        a, b = Vector(pts[i]), Vector(pts[i + 1])
        mid = (a + b) / 2 - Vector((0, 0, 0.42))
        mb.poly([tuple(a + Vector((0.04, 0, 0))), tuple(b - Vector((0.04, 0, 0))), tuple(mid)], cols[i % 3])
    o = mb.to_object(sharp_angle=None)
    return o


# -------------------------------------------------------------------- build ---
BUILDERS = [
    lambda: date_palm("SM_DatePalm_A", 9.0, 26, 1, 4.0),
    lambda: date_palm("SM_DatePalm_B", 12.5, 28, 2, 7.0),
    lambda: date_palm("SM_DatePalm_C", 5.5, 22, 3, 2.0, dates=False),
    acacia, barrier_water, barrier_concrete, tire_stack, cone, checkpoint_arch, start_gantry, boost_pad,
    jump_ramp, card, card_pickup, vfx_shield, vfx_tornado, vfx_flame, vfx_ring, vfx_sandtrap, falcon_drone,
    grandstand, pennants,
]


def build(render=True):
    sr.reset()
    make_textures()
    objs = []
    for b in BUILDERS:
        o = b()
        objs.append(o)
        print(f"{o.name}: {sr.tri_count(o)} tris")
    sr.export_kit(objs, KIT)
    if render:
        lineup_render(objs)
    sr.write_manifest()
    return objs


def lineup_render(objs):
    sr.layout_grid(objs, spacing=4.0, row_width=60)
    g = sr.ground(120, sr.mat("Sand", (1, 1, 1), tex="Sand", tile=6))
    sr.setup_render((1600, 900), 64)
    sr.world_sky(28, 200, 0.35)
    sr.sun((60, 0, 200), 3.5, (1.0, 0.88, 0.72), 1.5)
    c = sr.frame_camera(objs, (0.55, -1.0, 0.5), 35, margin=0.62)
    sr.render(os.path.join(sr.ROOT, "docs", "previews", f"kit_{KIT}.png"))


if __name__ == "__main__":
    build("--no-render" not in sys.argv)
