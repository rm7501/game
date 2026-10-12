"""Sahara Racers - ALULA map kit (Hegra, Elephant Rock, Maraya, sandstone canyon).

  SM_QasrAlFarid         Hegra's lone tomb: rock monolith with carved Nabataean facade
                         (4 pilasters, double cornice, attic, crow-steps, pedimented doorway)
  SM_HegraTombCliff      cliff wall with three smaller crow-step tombs
  SM_ElephantRock        Jabal AlFil, ~50 m, trunk forming a walk-through arch
  SM_RainbowRock         natural sandstone arch
  SM_Maraya              mirror-clad concert hall (individually tilted mirror panels)
  SM_RockPillar_A/B      fluted hoodoo pillars
  SM_Mesa_A              eroded mesa wall (canyon backdrop)
  SM_Boulder_A/B/C       scatter boulders
  SM_AlUlaHouse_A/B      old-town mud & stone houses
  SM_AlUlaOldTown        tight cluster of old-town houses
  SM_HotAirBalloon       AlUla Skies festival balloon
  SM_Dune_A              sand dune tile (200 m)
  SM_Road_Desert_25m     2-lane desert road with sand shoulders
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))
import sr  # noqa: E402

import bpy  # noqa: E402
from mathutils import Vector, noise  # noqa: E402

KIT = "alula"


def M():
    return dict(
        rock=sr.mat("AlUla_Sandstone", (1.0, 0.95, 0.92), rough=0.9, tex="SandstoneStrata", tile=11.0),
        rock_dark=sr.mat("AlUla_SandstoneDark", (0.82, 0.7, 0.64), rough=0.92, tex="SandstoneStrata", tile=8.0),
        carved=sr.mat("Hegra_CarvedFacade", (1.1, 1.02, 0.95), rough=0.85, tex="SandstoneStrata", tile=14.0, normal=0.4),
        interior=sr.mat("TombInterior", (0.05, 0.03, 0.02), rough=0.95),
        mirror=sr.mat("Maraya_Mirror", (0.92, 0.93, 0.95), rough=0.015, metal=1.0, kind="mirror"),
        mirror_back=sr.mat("Maraya_Backing", (0.05, 0.05, 0.055), rough=0.6),
        mud=sr.mat("AlUla_MudPlaster", (1.0, 0.9, 0.8), tex="MudPlaster", tile=3.0),
        stone=sr.mat("AlUla_StoneBase", (0.95, 0.8, 0.68), tex="StoneMasonry", tile=2.5),
        wood=sr.mat("PalmWood", (0.42, 0.3, 0.2), rough=0.8, tex="WoodPainted", tile=1.0),
        wood_dark=sr.mat("WoodDark", (0.2, 0.13, 0.08), rough=0.8, tex="WoodPainted", tile=1.0),
        window=sr.mat("WindowDarkHole", (0.02, 0.015, 0.01), rough=0.9),
        sand=sr.mat("Sand", (1, 1, 1), tex="Sand", tile=6),
        asphalt=sr.mat("Asphalt", (1, 1, 1), tex="Asphalt", tile=4.0),
        line_y=sr.mat("RoadLineYellow", (0.85, 0.65, 0.1), rough=0.5),
        line_w=sr.mat("RoadLineWhite", (0.9, 0.9, 0.88), rough=0.5),
        wicker=sr.mat("Wicker", (0.62, 0.45, 0.25), rough=0.8, tex="WoodPainted", tile=0.5),
        steel=sr.mat("SteelDark", (0.08, 0.08, 0.09), rough=0.4, metal=1.0),
        rope=sr.mat("Rope", (0.7, 0.62, 0.48), rough=0.9),
        flame=sr.mat("BurnerFlame", (1.0, 0.5, 0.1), emit=(1.0, 0.5, 0.1), emit_str=15, kind="emissive"),
    )


# ------------------------------------------------------------- rock helpers ---
def blob_union(name, parts, voxel=0.7):
    """parts: list of callables(mb) adding closed primitives; voxel remesh = boolean union."""
    mb = sr.MB(name)
    for p in parts:
        p(mb)
    o = mb.to_object(uv=False, sharp_angle=None)
    sr.remesh(o, voxel)
    return o


def finish_rock(o, mat, name=None):
    """Clamp to the ground, assign material, world-UV, origin at base."""
    sr.ground_clamp(o, 0.0)
    mb = sr.MB(name or o.name)
    mb.add_object(o)
    bpy.data.objects.remove(o, do_unlink=True)
    for f in mb.bm.faces:
        f.material_index = mb.mi(mat)
        f.smooth = True
    out = mb.to_object(sharp_angle=None)
    sr.set_origin(out, "base")
    return out


def carved_rock(name, parts, voxel, cuts=(), mask=None, **rock_kw):
    """Union -> boolean carve (on clean voxel mesh) -> re-voxelise -> masked rockify."""
    o = blob_union(name, parts, voxel)
    for c in cuts:
        cm = sr.MB("cut")
        c(cm)
        sr.boolean(o, cm.to_object(uv=False))
    if cuts:
        sr.remesh(o, voxel * 0.8)
    sr.rockify(o, mask=mask, **rock_kw)
    return o


def box_mask(x0, x1, y0, y1, z0, z1, fall=1.2):
    """1 outside the box, 0 inside, smooth falloff - keeps carved planes flat."""
    def m(p):
        dx = max(x0 - p.x, 0, p.x - x1)
        dy = max(y0 - p.y, 0, p.y - y1)
        dz = max(z0 - p.z, 0, p.z - z1)
        d = math.sqrt(dx * dx + dy * dy + dz * dz)
        return min(1.0, d / fall)
    return m


# -------------------------------------------------------------- Qasr al-Farid ---
def crow_steps(mb, x_outer, x_inner, z, y_front, depth, m, steps=5, step_h=0.8):
    """Nabataean half-merlon staircase rising from x_outer towards x_inner."""
    w = (x_inner - x_outer)
    for i in range(steps):
        xa = x_outer + w * i / steps
        cx = (xa + x_inner) / 2
        mb.box((abs(x_inner - xa), depth, step_h), (cx, y_front + depth / 2, z + step_h * (i + 0.5)), m=m)


def hegra_facade(mb, mm, cx, y, z0, W, H, door_w=3.0, door_h=5.2, attic=True, pilasters=4, eagle=False):
    """Carved Hegra tomb facade standing proud of the plane y (facing -Y)."""
    m = mm["carved"]
    zc = z0 + H * 0.62          # top of the main pilasters
    # pilasters + Nabataean capitals
    xs = [cx - W / 2 + 0.75, cx + W / 2 - 0.75] if pilasters == 2 else \
         [cx - W / 2 + 0.75, cx - W * 0.2, cx + W * 0.2, cx + W / 2 - 0.75]
    for x in xs:
        mb.box((1.4, 0.55, zc - z0), (x, y - 0.27, (z0 + zc) / 2), m=m)
        mb.box((1.9, 0.8, 0.55), (x, y - 0.4, zc + 0.27), m=m)
        mb.box((1.6, 0.7, 0.4), (x, y - 0.35, zc - 0.2), m=m)
        mb.box((1.9, 0.75, 0.35), (x, y - 0.37, z0 + 0.17), m=m)
    # entablature: architrave, frieze, projecting cornice
    za = zc + 0.55
    mb.box((W, 0.6, 0.75), (cx, y - 0.3, za + 0.37), m=m)
    mb.box((W, 0.4, 1.2), (cx, y - 0.2, za + 1.35), m=m)
    mb.box((W + 1.0, 1.0, 0.55), (cx, y - 0.5, za + 2.2), m=m)
    mb.box((W + 1.3, 1.2, 0.25), (cx, y - 0.6, za + 2.6), m=m)
    zt = za + 2.73
    if attic:   # attic storey with small half-pilasters
        ah = 2.1
        mb.box((W * 0.98, 0.3, ah), (cx, y - 0.15, zt + ah / 2), m=m)
        for x in xs:
            mb.box((0.9, 0.5, ah), (x, y - 0.25, zt + ah / 2), m=m)
        mb.box((W + 0.6, 0.8, 0.5), (cx, y - 0.4, zt + ah + 0.25), m=m)
        zt += ah + 0.5
    # crow-steps: two half-merlons rising towards the centre
    gap = 0.9
    crow_steps(mb, cx - W / 2 + 0.2, cx - gap, zt, y - 0.6, 0.6, m)
    crow_steps(mb, cx + W / 2 - 0.2, cx + gap, zt, y - 0.6, 0.6, m)
    # doorway frame + pediment
    dz = z0 + 0.4
    for sg in (1, -1):
        mb.box((0.5, 0.45, door_h + 0.4), (cx + sg * (door_w / 2 + 0.25), y - 0.22, dz + door_h / 2), m=m)
    mb.box((door_w + 1.6, 0.5, 0.45), (cx, y - 0.25, dz + door_h + 0.45), m=m)
    ped = [(-door_w / 2 - 0.9, 0), (door_w / 2 + 0.9, 0), (0, 1.5)]
    mb.prism(ped, 0, 0.5, (cx, y, dz + door_h + 0.68), (90, 0, 0), m=m)
    mb.box((0.5, 0.5, 0.7), (cx, y - 0.25, dz + door_h + 2.5), m=m)       # finial urn
    if eagle:   # eagle relief over the pediment (common on Hegra tombs)
        mb.sphere(0.45, (cx, y - 0.45, dz + door_h + 2.9), m=m, seg=10, rings=6, scale=(1.4, 0.5, 1.0))
    return zt + 5 * 0.8


def qasr_al_farid(mm, name="SM_QasrAlFarid"):
    W, H = 15.5, 15.0
    fy = -8.6
    ch = 20.6
    rock = carved_rock("qaf_rock", [
        lambda mb: mb.box((26, 22, 24), (0, 0, 11), m=mm["rock"], bevel=4.0, seg=3),
        lambda mb: mb.sphere(9, (6, 4, 21), m=mm["rock"], seg=16, rings=10),
        lambda mb: mb.sphere(8, (-7, 5, 20), m=mm["rock"], seg=16, rings=10),
    ], 0.7, cuts=[lambda cm: cm.box((W + 0.8, 14, ch), (0, fy - 7.0, ch / 2 - 0.5), m=mm["rock"])],
        mask=box_mask(-W / 2 - 0.4, W / 2 + 0.4, fy - 8, fy + 0.6, -2, ch, 1.5),
        amp=1.6, scale=0.07, flute=1.6, flute_scale=0.3, strata=0.35, seed=3)
    rock = finish_rock(rock, mm["rock"], "qaf_tmp")
    mb = sr.MB(name)
    mb.add_object(rock)
    bpy.data.objects.remove(rock, do_unlink=True)
    hegra_facade(mb, mm, 0, fy, 0.4, W, H, attic=True, eagle=False)
    mb.box((3.0, 0.3, 5.2), (0, fy - 0.12, 0.4 + 2.6), m=mm["interior"])          # dark doorway
    # unfinished rough lower zone + rubble at the foot
    rub = blob_union("rubble", [lambda mb2: mb2.box((W + 3, 3.5, 1.4), (0, fy - 1.2, 0.3), m=mm["rock"], bevel=0.5, seg=2)], 0.45)
    sr.rockify(rub, amp=0.45, scale=0.4, seed=7)
    sr.ground_clamp(rub)
    mb.add_object(rub)
    bpy.data.objects.remove(rub, do_unlink=True)
    return mb.to_object(origin="base", sharp_angle=None)


def hegra_cliff(mm, name="SM_HegraTombCliff"):
    fy = -3.2
    tombs = [(-14.0, 8.5, 10.0, 2), (0.0, 10.5, 12.5, 4), (13.5, 7.5, 9.0, 2)]
    cuts, masks = [], []
    for (cx, W, H, pil) in tombs:
        h = H + 6.0
        cuts.append(lambda cm, cx=cx, W=W, h=h: cm.box((W + 0.6, 12, h), (cx, fy - 6.0, h / 2 - 0.5), m=mm["rock"]))
        masks.append(box_mask(cx - W / 2 - 0.3, cx + W / 2 + 0.3, fy - 8, fy + 0.6, -2, h, 1.4))
    rock = carved_rock("cliff", [
        lambda mb: mb.box((46, 16, 22), (0, 4, 10), m=mm["rock"], bevel=3.0, seg=2),
        lambda mb: mb.sphere(10, (-15, 6, 19), m=mm["rock"], seg=16, rings=10),
        lambda mb: mb.sphere(11, (12, 8, 20), m=mm["rock"], seg=16, rings=10),
    ], 0.75, cuts=cuts, mask=lambda p: min(m_(p) for m_ in masks),
        amp=1.8, scale=0.06, flute=2.0, flute_scale=0.28, strata=0.4, seed=11)
    rock = finish_rock(rock, mm["rock"], "cliff_tmp")
    mb = sr.MB(name)
    mb.add_object(rock)
    bpy.data.objects.remove(rock, do_unlink=True)
    for (cx, W, H, pil) in tombs:
        hegra_facade(mb, mm, cx, fy, 0.2, W, H, door_w=2.2, door_h=3.8, attic=(pil == 4), pilasters=pil, eagle=True)
        mb.box((2.2, 0.3, 3.8), (cx, fy - 0.12, 0.2 + 1.9), m=mm["interior"])
    return mb.to_object(origin="base", sharp_angle=None)


# ------------------------------------------------------------ Elephant Rock ---
def elephant_rock(mm, name="SM_ElephantRock"):
    trunk = [(20, 0, 38), (27, 0, 36), (32, 0, 28), (34.5, 0, 17), (35, 0, 7), (34, 0, -2)]
    rock = blob_union("ele", [
        lambda mb: mb.sphere(1.0, (0, 0, 22), m=mm["rock"], seg=32, rings=20, scale=(21, 14, 24)),
        lambda mb: mb.sphere(1.0, (-14, 2, 15), m=mm["rock"], seg=24, rings=14, scale=(12, 12, 16)),
        lambda mb: mb.sphere(1.0, (14, 0, 35), m=mm["rock"], seg=24, rings=14, scale=(11, 10.5, 12)),
        lambda mb: mb.tube(trunk, [7.5, 7.0, 6.2, 5.4, 5.2, 6.5], mm["rock"], seg=20),
        lambda mb: mb.sphere(1.0, (35, 0, 0), m=mm["rock"], seg=16, rings=10, scale=(7, 7, 3)),
    ], voxel=0.75)
    sr.rockify(rock, amp=2.2, scale=0.045, flute=2.6, flute_scale=0.22, strata=0.45, strata_freq=1.1, seed=5)
    return finish_rock(rock, mm["rock"], name)


def rainbow_rock(mm, name="SM_RainbowRock"):
    arc = [(-14 + 28 * t, 0, 4 + 22 * math.sin(math.pi * t) ** 0.8) for t in [i / 16 for i in range(17)]]
    rock = blob_union("rainbow", [
        lambda mb: mb.tube(arc, [5.5, 5, 4.4, 4.0, 3.8, 3.6, 3.4, 3.3, 3.3, 3.3, 3.4, 3.6, 3.8, 4.0, 4.4, 5, 5.5], mm["rock"], seg=18),
        lambda mb: mb.sphere(1.0, (-15, 0, 3), m=mm["rock"], seg=20, rings=12, scale=(8, 7, 8)),
        lambda mb: mb.sphere(1.0, (15, 0, 3), m=mm["rock"], seg=20, rings=12, scale=(8, 7, 8)),
    ], voxel=0.6)
    sr.rockify(rock, amp=1.3, scale=0.07, flute=1.0, strata=0.6, strata_freq=1.6, seed=9)
    return finish_rock(rock, mm["rock_dark"], name)


def rock_pillar(mm, name, H=28.0, r=6.0, seed=1, twin=False):
    def pillar(mb, x, y, h, rr):
        rings = []
        for j in range(13):
            z = h * j / 12
            f = z / h
            rad = rr * (0.72 + 0.12 * f + 0.35 * max(0, f - 0.8) / 0.2) if f > 0.15 else rr * (0.95 - 1.2 * f)
            rings.append([(x + rad * 1.2 * math.cos(2 * math.pi * i / 20), y + rad * math.sin(2 * math.pi * i / 20), z) for i in range(20)])
        mb.loft(rings, mm["rock"], closed=True, cap_start=True, cap_end=True)
    parts = [lambda mb: pillar(mb, 0, 0, H, r)]
    if twin:
        parts.append(lambda mb: pillar(mb, r * 1.9, r * 0.6, H * 0.78, r * 0.8))
    rock = blob_union(name, parts, voxel=0.6)
    sr.rockify(rock, amp=1.5, scale=0.08, flute=1.8, flute_scale=0.35, strata=0.5, seed=seed)
    return finish_rock(rock, mm["rock"], name)


def mesa(mm, name="SM_Mesa_A"):
    rock = blob_union(name, [
        lambda mb: mb.box((90, 34, 30), (0, 0, 14), m=mm["rock"], bevel=5, seg=2),
        lambda mb: mb.box((40, 26, 12), (-38, 8, 32), m=mm["rock"], bevel=4, seg=2),
        lambda mb: mb.sphere(1.0, (30, -6, 26), m=mm["rock"], seg=20, rings=12, scale=(18, 14, 14)),
    ], voxel=1.1)
    sr.rockify(rock, amp=3.0, scale=0.035, flute=3.0, flute_scale=0.18, strata=0.7, strata_freq=0.8, seed=21)
    return finish_rock(rock, mm["rock"], name)


def boulder(mm, name, size=3.0, seed=1):
    rnd = random.Random(seed)
    rock = blob_union(name, [lambda mb: mb.sphere(1.0, (0, 0, size * 0.35), m=mm["rock"], seg=16, rings=10,
                                                   scale=(size, size * rnd.uniform(0.6, 0.9), size * rnd.uniform(0.5, 0.8)))],
                      voxel=size * 0.08)
    sr.rockify(rock, amp=size * 0.18, scale=0.6 / size, strata=size * 0.03, seed=seed)
    return finish_rock(rock, mm["rock_dark"], name)


# ------------------------------------------------------------------- Maraya ---
def maraya(mm, name="SM_Maraya"):
    """100 x 40 x 26 m mirror box. Each 3.0 x 1.5 m panel is slightly tilted so reflections break up
    like the real building."""
    rnd = random.Random(12)
    mb = sr.MB(name)
    L, D, H = 100.0, 40.0, 26.0
    mb.box((L - 0.2, D - 0.2, H - 0.1), (0, 0, H / 2), m=mm["mirror_back"])
    pw, ph, gap = 3.0, 1.5, 0.025
    faces = [((0, -1), L, (0, -D / 2)), ((0, 1), L, (0, D / 2)), ((1, 0), D, (L / 2, 0)), ((-1, 0), D, (-L / 2, 0))]
    for (nx, ny), width, (cx, cy) in faces:
        n = Vector((nx, ny, 0))
        t = Vector((-ny, nx, 0))
        cols = int(width / pw)
        rows = int(H / ph)
        for i in range(cols):
            for j in range(rows):
                # entrance slot in the south face
                if ny == -1 and abs((i + 0.5) * pw - width / 2) < 2.0 and j < 4:
                    continue
                u0 = -width / 2 + i * pw + gap
                u1 = u0 + pw - 2 * gap
                z0 = j * ph + gap
                z1 = z0 + ph - 2 * gap
                tilt = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), 0)) * 0.004
                base = Vector((cx, cy, 0)) + n * 0.03
                pts = []
                for (u, z) in ((u0, z0), (u1, z0), (u1, z1), (u0, z1)):
                    p = base + t * u + Vector((0, 0, z))
                    off = (u - (u0 + u1) / 2) * tilt.x + (z - (z0 + z1) / 2) * tilt.y
                    pts.append(tuple(p + n * off))
                mb.poly_facing(pts, tuple(n), mm["mirror"])
    # roof edge coping
    mb.box((L + 0.2, D + 0.2, 0.25), (0, 0, H + 0.12), m=mm["mirror_back"])
    # entrance: dark recess
    mb.box((3.6, 0.5, 6.0), (0, -D / 2 + 0.1, 3.0), m=mm["interior"])
    return mb.to_object(origin="base", sharp_angle=10)


# --------------------------------------------------------------- old town ---
def alula_house(mm, name, w=7.0, d=6.0, floors=2, seed=1, mb=None, loc=(0, 0, 0), rot=0.0):
    rnd = random.Random(seed)
    own = mb is None
    mb = mb or sr.MB(name)
    ox, oy, oz = loc
    c, s_ = math.cos(math.radians(rot)), math.sin(math.radians(rot))

    def P(x, y, z):
        return (ox + x * c - y * s_, oy + x * s_ + y * c, oz + z)
    fh = 3.2
    H = floors * fh
    mb.box((w, d, 1.3), P(0, 0, 0.65), (0, 0, rot), m=mm["stone"])
    mb.box((w - 0.08, d - 0.08, H - 1.3), P(0, 0, 1.3 + (H - 1.3) / 2), (0, 0, rot), m=mm["mud"])
    # irregular parapet
    for k in range(int((w + d) * 2 / 1.0)):
        per = k * 1.0
        if per < w:
            x, y = -w / 2 + per, -d / 2
        elif per < w + d:
            x, y = w / 2, -d / 2 + (per - w)
        elif per < 2 * w + d:
            x, y = w / 2 - (per - w - d), d / 2
        else:
            x, y = -w / 2, d / 2 - (per - 2 * w - d)
        mb.box((1.0, 1.0, 0.6 + rnd.uniform(-0.15, 0.2)), P(x, y, H + 0.3), (0, 0, rot), m=mm["mud"])
    # protruding palm-trunk roof beams + spouts
    for k in range(int(w / 0.8)):
        x = -w / 2 + 0.4 + k * 0.8
        mb.cyl(0.08, 0.6, P(x, -d / 2 - 0.15, H - 0.25), (90, 0, rot), m=mm["wood"], seg=6)
    mb.box((0.18, 0.7, 0.14), P(w * 0.25, -d / 2 - 0.3, H + 0.05), (0, 0, rot), m=mm["wood"])
    # door + small windows with wooden shutters
    mb.box((1.1, 0.12, 2.1), P(rnd.uniform(-w / 4, w / 4), -d / 2 - 0.02, 1.05), (0, 0, rot), m=mm["wood_dark"])
    for f in range(floors):
        for k in range(rnd.randint(1, 3)):
            x = rnd.uniform(-w / 2 + 0.8, w / 2 - 0.8)
            z = f * fh + (1.8 if f == 0 else 1.6)
            if f == 0 and abs(x) < 0.9:
                continue
            mb.box((0.6, 0.1, 0.7), P(x, -d / 2 - 0.02, z), (0, 0, rot), m=mm["window"])
            mb.box((0.75, 0.14, 0.08), P(x, -d / 2 - 0.04, z - 0.4), (0, 0, rot), m=mm["wood"])
        for k in range(rnd.randint(0, 2)):
            x = rnd.uniform(-d / 2 + 0.8, d / 2 - 0.8)
            mb.box((0.1, 0.6, 0.7), P(w / 2 + 0.02, x, f * fh + 1.7), (0, 0, rot), m=mm["window"])
    # triangle vents (shared regional motif)
    for k in range(3):
        mb.prism([(-0.2, 0), (0.2, 0), (0, 0.35)], 0, 0.06, P(-0.8 + k * 0.8, -d / 2 - 0.03, H - 1.0), (90, 0, rot), m=mm["window"])
    if own:
        return mb.to_object(origin="base", sharp_angle=30)


def old_town(mm, name="SM_AlUlaOldTown"):
    """Tight cluster of 2-3 storey houses along a crooked lane (AlUla Old Town, ~900 houses)."""
    rnd = random.Random(33)
    mb = sr.MB(name)
    k = 0
    for row, y in ((0, -6.0), (1, 6.0)):
        x = -30.0
        while x < 30:
            w = rnd.uniform(5.5, 9.0)
            d = rnd.uniform(6, 9)
            fl = rnd.choice((2, 2, 3))
            yy = y + rnd.uniform(-0.6, 0.6) + (d / 2 if row else -d / 2)
            alula_house(mm, "h", w, d, fl, seed=100 + k, mb=mb, loc=(x + w / 2, yy, 0), rot=0 if row == 0 else 180)
            x += w + rnd.uniform(-0.2, 0.3)
            k += 1
    # lane: packed earth + covered passage beam
    mb.box((62, 3.0, 0.08), (0, 0, 0.04), m=mm["sand"])
    for x in (-12, 9):
        mb.box((3.5, 13, 0.6), (x, 0, 6.2), m=mm["mud"])
        for q in range(8):
            mb.cyl(0.08, 13, (x - 1.5 + q * 0.43, 0, 5.85), (90, 0, 0), m=mm["wood"], seg=6)
    return mb.to_object(origin="base", sharp_angle=30)


# -------------------------------------------------------------------- props ---
def hot_air_balloon(mm, name="SM_HotAirBalloon", seed=1):
    rnd = random.Random(seed)
    palettes = [[(0.85, 0.15, 0.1), (0.95, 0.75, 0.2)], [(0.05, 0.35, 0.25), (0.95, 0.9, 0.8)],
                [(0.15, 0.25, 0.6), (0.9, 0.5, 0.15)]]
    pal = palettes[seed % len(palettes)]
    mats = [sr.mat(f"BalloonFabric_{seed}_{i}", c, rough=0.6) for i, c in enumerate(pal)]
    mb = sr.MB(name)
    base_z = 6.0
    prof = [(1.6, 0), (3.2, 2.5), (6.0, 6.0), (8.4, 10.0), (9.2, 13.5), (8.9, 16.5), (7.4, 19.5), (4.6, 21.8), (1.5, 22.8), (0.0, 23.0)]
    prof = [(r, z + base_z) for r, z in prof]
    gores = 16
    for g in range(gores):
        mb.lathe(prof, seg=3, arc=360 / gores, rot=(0, 0, g * 360 / gores), m=mats[g % 2])
    # load band ring + ropes + basket + burner
    for k in range(8):
        a = 2 * math.pi * k / 8
        mb.tube([(1.6 * math.cos(a), 1.6 * math.sin(a), base_z), (0.6 * math.cos(a), 0.6 * math.sin(a), 1.4)], 0.02, mm["rope"], seg=4)
    mb.box((1.3, 1.3, 1.1), (0, 0, 0.55), m=mm["wicker"], bevel=0.08, seg=2)
    mb.box((1.4, 1.4, 0.1), (0, 0, 1.1), m=mm["wood_dark"], bevel=0.03)
    mb.box((0.5, 0.5, 0.35), (0, 0, 2.0), m=mm["steel"])
    mb.lathe([(0.0, 2.2), (0.25, 2.5), (0.0, 3.6)], seg=12, m=mm["flame"])
    return mb.to_object(origin="base", sharp_angle=None)


def dune(mm, name="SM_Dune_A", size=200.0, seed=2):
    mb = sr.MB(name)
    off = Vector((seed * 10.0, seed * 3.0, 0))

    def fn(x, y):
        p = Vector((x, y, 0)) * 0.012 + off
        base = noise.fractal(p, 0.7, 2.0, 4, noise_basis="PERLIN_NEW")
        ridge = 1 - abs(noise.noise(p * 1.6 + Vector((3, 1, 0)), noise_basis="PERLIN_NEW"))
        edge = max(0.0, 1 - (max(abs(x), abs(y)) / (size / 2)) ** 6)
        return (base * 6 + ridge ** 3 * 10) * edge
    n = 110
    mb.grid(fn, n, n, -size / 2, size / 2, -size / 2, size / 2, m=mm["sand"])
    return mb.to_object(origin="keep", sharp_angle=None)


def road_desert(mm, name="SM_Road_Desert_25m", L=25.0):
    mb = sr.MB(name)
    mb.box((L, 8.0, 0.1), (0, 0, 0.0), m=mm["asphalt"])
    for sg in (1, -1):
        mb.box((L, 0.15, 0.012), (0, sg * 3.7, 0.055), m=mm["line_w"])
        mb.box((L, 2.5, 0.12), (0, sg * 5.2, -0.03), (sg * 4, 0, 0), m=mm["sand"])
    for k in range(int(L / 6)):
        mb.box((3.0, 0.12, 0.012), (-L / 2 + 1.5 + k * 6, 0, 0.055), m=mm["line_y"])
    return mb.to_object(origin="keep")


# -------------------------------------------------------------------- build ---
def build_all():
    sr.reset()
    mm = M()
    objs = []
    for fn in (qasr_al_farid, hegra_cliff, elephant_rock, rainbow_rock, maraya):
        o = fn(mm)
        objs.append(o)
    objs.append(rock_pillar(mm, "SM_RockPillar_A", 30.0, 6.5, 41))
    objs.append(rock_pillar(mm, "SM_RockPillar_B", 22.0, 5.0, 42, twin=True))
    objs.append(mesa(mm))
    for i, (sz, sd) in enumerate(((2.0, 51), (3.5, 52), (6.0, 53))):
        objs.append(boulder(mm, f"SM_Boulder_{'ABC'[i]}", sz, sd))
    objs.append(alula_house(mm, "SM_AlUlaHouse_A", 7.0, 6.0, 2, 61))
    objs.append(alula_house(mm, "SM_AlUlaHouse_B", 9.0, 7.0, 3, 62))
    objs.append(old_town(mm))
    for i in range(3):
        objs.append(hot_air_balloon(mm, f"SM_HotAirBalloon_{'ABC'[i]}", i))
    objs.append(dune(mm))
    objs.append(road_desert(mm))
    for o in objs:
        print(f"{o.name}: {sr.tri_count(o)} tris")
    return objs


def diorama(objs, extra=(), out=None, cars=("AlUlaRally", "DuneFox")):
    """Golden hour: desert road through the sandstone valley past Elephant Rock and Hegra."""
    by = {o.name: o for o in list(objs) + list(extra)}
    for o in by.values():
        sr.hide(o)
    rnd = random.Random(8)
    for k in range(-1, 30):
        sr.inst(by["SM_Road_Desert_25m"], (k * 25.0, 0, 0.02))
    # hero landmarks posed for the road: Elephant Rock side-on (arch visible), tomb facades facing traffic
    sr.inst(by["SM_ElephantRock"], (235, -62, 0), (0, 0, 95))
    sr.inst(by["SM_QasrAlFarid"], (120, 42, 0), (0, 0, -70))
    sr.inst(by["SM_HegraTombCliff"], (330, 105, 0), (0, 0, -80))
    sr.inst(by["SM_Maraya"], (470, 40, 0), (0, 0, 12))
    sr.inst(by["SM_RainbowRock"], (560, -70, 0), (0, 0, 80))
    sr.inst(by["SM_RockPillar_A"], (175, -30, 0), (0, 0, 30))
    sr.inst(by["SM_RockPillar_B"], (60, 36, 0), (0, 0, 120))
    for k in range(6):
        sr.inst(by["SM_Mesa_A"], (700 + k * 60, -500 + k * 200, 0), (0, 0, rnd.uniform(-40, 40)), scale=rnd.uniform(1.2, 2.0))
    for k in range(4):
        sr.inst(by["SM_Mesa_A"], (200 + k * 160, 420 + rnd.uniform(0, 80), 0), (0, 0, rnd.uniform(-30, 30)), scale=rnd.uniform(1.0, 1.6))
    boulders = [by[f"SM_Boulder_{c}"] for c in "ABC"]
    for k in range(80):
        x, y = rnd.uniform(0, 600), rnd.uniform(-160, 160)
        if abs(y) < 9 or (abs(x - 235) < 45 and abs(y + 62) < 40) or (abs(x - 120) < 30 and abs(y - 42) < 30):
            continue
        sr.inst(rnd.choice(boulders), (x, y, 0), (0, 0, rnd.uniform(0, 360)), scale=rnd.uniform(0.6, 1.6))
    trees = [by[n] for n in ("SM_Acacia", "SM_DatePalm_A", "SM_DatePalm_C") if n in by]
    for k in range(45):
        x, y = rnd.uniform(10, 500), rnd.uniform(-120, 120)
        if abs(y) < 10:
            continue
        sr.inst(rnd.choice(trees), (x, y, 0), (0, 0, rnd.uniform(0, 360)), scale=rnd.uniform(0.8, 1.2))
    for i, (x, y, z) in enumerate(((260, -30, 70), (380, 90, 95), (180, 120, 60), (470, -110, 110), (330, 10, 140))):
        sr.inst(by[f"SM_HotAirBalloon_{'ABC'[i % 3]}"], (x, y, z), (0, 0, rnd.uniform(0, 360)))
    sr.ground(5000, sr.mat("Sand", (1, 1, 1), tex="Sand", tile=6), z=0.0)
    for i, c in enumerate(cars):
        glb = os.path.join(sr.ROOT, "assets", "cars", c, f"{c}_preview.glb")
        if os.path.exists(glb):
            sr.import_glb(glb, ((16, 30)[i], (-1.9, 1.9)[i], 0.07), (0, 180)[i])
    sr.setup_render((1600, 900), 64, exposure=-0.2)
    sr.world_sky(6, 250, 0.22)
    sr.sun((84, 0, 250), 5.5, (1.0, 0.68, 0.4), 1.2)
    sr.camera((-14, -6.5, 3.4), (300, 8, 20), 30)
    sr.render(out or os.path.join(sr.ROOT, "docs", "previews", "map_alula.png"))


if __name__ == "__main__":
    objs = build_all()
    sr.export_kit(objs, KIT)
    sr.write_manifest()
