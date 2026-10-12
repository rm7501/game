"""Sahara Racers - eight detailed race cars.

Each car is generated from real-world-proportioned profile curves:
  side profile  (zb underbody, zs belt/hood line, zt roof line)
  plan view     (w half-width, wt roof half-width)
  sections      (13-point half section, Catmull-Clark subdivided, creased at material edges)
Details (lights, grilles, intakes, stripes, seams) are ray-projected onto the curved body.

Outputs per car (assets/cars/<Name>/):
  SK_<Name>.fbx         skeletal mesh: bones Root, Wheel_FL, Wheel_FR, Wheel_RL, Wheel_RR (Chaos Vehicle ready)
  SM_<Name>_Body.fbx    static body (no wheels) for menus / blueprint vehicles
  SM_<Name>_Wheel_F.fbx static front wheel (left side orientation, origin at hub)
  SM_<Name>_Wheel_R.fbx static rear wheel
Forward = +X, Left = +Y, Up = +Z, origin = ground point midway between the axles.

Run: python blender/cars.py [CarName ...]
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))
import sr  # noqa: E402

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402

OUT = os.path.join(sr.ROOT, "assets", "cars")
PREV = os.path.join(sr.ROOT, "docs", "previews", "cars")
PLATES = os.path.join(sr.ROOT, "assets", "cars", "textures")


def curve(pts):
    """Monotone cubic (PCHIP / Fritsch-Carlson) through (t, value) points: smooth, never overshoots.
    Pure Python so the script also runs inside Blender's bundled interpreter."""
    ts = [float(p[0]) for p in pts]
    vs = [float(p[1]) for p in pts]
    n = len(ts)
    h = [ts[i + 1] - ts[i] for i in range(n - 1)]
    d = [(vs[i + 1] - vs[i]) / h[i] for i in range(n - 1)]
    m = [0.0] * n
    if n == 2:
        m = [d[0], d[0]]
    else:
        for i in range(1, n - 1):
            if d[i - 1] * d[i] <= 0:
                m[i] = 0.0
            else:
                w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
                m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])
        # end slopes (non-centred three-point formula, shape preserving)
        def end(h0, h1, d0, d1):
            e = ((2 * h0 + h1) * d0 - h0 * d1) / (h0 + h1)
            if e * d0 <= 0:
                return 0.0
            if d0 * d1 <= 0 and abs(e) > abs(3 * d0):
                return 3 * d0
            return e
        m[0] = end(h[0], h[1], d[0], d[1])
        m[-1] = end(h[-1], h[-2], d[-1], d[-2])

    def f(t):
        if t <= ts[0]:
            return vs[0]
        if t >= ts[-1]:
            return vs[-1]
        i = 0
        while t > ts[i + 1]:
            i += 1
        u = (t - ts[i]) / h[i]
        h00 = (1 + 2 * u) * (1 - u) ** 2
        h10 = u * (1 - u) ** 2
        h01 = u * u * (3 - 2 * u)
        h11 = u * u * (u - 1)
        return h00 * vs[i] + h10 * h[i] * m[i] + h01 * vs[i + 1] + h11 * h[i] * m[i + 1]
    return f


class T(float):
    """Marks an x coordinate given as normalised length t (0 = rear, 1 = front) in specs."""


def in_ranges(t, ranges):
    return any(a <= t <= b for a, b in ranges)


def lerp(a, b, f):
    return a + (b - a) * f


def clamp(v, a, b):
    return a if v < a else b if v > b else v


# ------------------------------------------------------------ materials ---
def car_mats(spec):
    cid = spec["id"]
    M = {}
    M["paint"] = sr.mat(f"Car{cid}_Paint", spec["paint"], rough=0.28, metal=spec.get("metal", 0.55),
                        coat=1.0, kind="carpaint")
    M["accent"] = sr.mat(f"Car{cid}_Accent", spec["accent"], rough=0.3, metal=spec.get("accent_metal", 0.4),
                         coat=1.0, kind="carpaint")
    M["rim"] = sr.mat(f"Car{cid}_Rim", spec["rim_color"], rough=spec.get("rim_rough", 0.25),
                      metal=1.0 if spec.get("rim_metal", True) else 0.0)
    M["glow"] = sr.mat(f"Car{cid}_Glow", spec.get("glow", (0.2, 0.9, 1.0)), rough=0.4,
                       emit=spec.get("glow", (0.2, 0.9, 1.0)), emit_str=12.0, kind="emissive")
    M["glass"] = sr.mat("Car_Glass", (0.02, 0.025, 0.03), rough=0.02, metal=0.0, transmission=0.7, kind="glass")
    M["trim"] = sr.mat("Car_TrimBlack", (0.015, 0.015, 0.017), rough=0.55)
    M["gloss"] = sr.mat("Car_GlossBlack", (0.008, 0.008, 0.009), rough=0.12, coat=1.0)
    M["grille"] = sr.mat("Car_Grille", (0.8, 0.8, 0.82), rough=0.5, metal=0.6, tex="HexMesh", tile=0.18)
    M["carbon"] = sr.mat("Car_Carbon", (0.02, 0.021, 0.024), rough=0.22, metal=0.3, coat=1.0)
    M["chrome"] = sr.mat("Car_Chrome", (0.95, 0.95, 0.95), rough=0.04, metal=1.0, kind="mirror")
    M["under"] = sr.mat("Car_Underbody", (0.03, 0.03, 0.03), rough=0.8)
    M["tire"] = sr.mat("Car_Tire", (0.025, 0.025, 0.027), rough=0.88)
    M["disc"] = sr.mat("Car_BrakeDisc", (0.45, 0.45, 0.46), rough=0.38, metal=1.0)
    M["head"] = sr.mat("Car_Headlight", (0.9, 0.95, 1.0), rough=0.1, emit=(0.85, 0.92, 1.0), emit_str=10.0,
                       kind="emissive")
    M["drl"] = sr.mat("Car_DRL", (0.95, 0.97, 1.0), rough=0.1, emit=(0.9, 0.95, 1.0), emit_str=20.0, kind="emissive")
    M["tail"] = sr.mat("Car_Taillight", (0.3, 0.0, 0.0), rough=0.1, emit=(1.0, 0.0, 0.0), emit_str=2.5,
                       kind="emissive")
    M["amber"] = sr.mat("Car_Indicator", (0.9, 0.4, 0.02), rough=0.1, emit=(1.0, 0.45, 0.02), emit_str=6.0,
                        kind="emissive")
    M["lens"] = sr.mat("Car_LightHousing", (0.05, 0.05, 0.06), rough=0.08, metal=0.8)
    M["interior"] = sr.mat("Car_Interior", (0.05, 0.045, 0.04), rough=0.7)
    M["leather"] = sr.mat(f"Car{cid}_Seat", spec.get("seat", (0.35, 0.08, 0.05)), rough=0.55)
    M["mirror"] = sr.mat("Car_MirrorGlass", (0.8, 0.82, 0.85), rough=0.02, metal=1.0, kind="mirror")
    M["exhaust"] = sr.mat("Car_Exhaust", (0.55, 0.5, 0.45), rough=0.3, metal=1.0)
    M["soot"] = sr.mat("Car_ExhaustInner", (0.01, 0.01, 0.01), rough=0.9)
    M["plate"] = sr.mat(f"Car{cid}_Plate", (1, 1, 1), rough=0.4,
                        image=os.path.join(PLATES, f"T_Plate_{cid}.png"))
    M["number"] = sr.mat(f"Car{cid}_Number", (1, 1, 1), rough=0.35,
                         image=os.path.join(PLATES, f"T_Number_{cid}.png"))
    return M


# ------------------------------------------------------------- plate art ---
def make_plate_textures(spec):
    """Saudi-style licence plate + race number roundel (Arabic + English)."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        import arabic_reshaper
        from bidi.algorithm import get_display
    except ImportError:      # inside Blender's bundled Python: use the committed textures
        return

    os.makedirs(PLATES, exist_ok=True)
    cid = spec["id"]
    from PIL import features
    if features.check("raqm"):          # libraqm shapes + reorders Arabic itself
        ar = lambda s: s  # noqa: E731
    else:
        ar = lambda s: get_display(arabic_reshaper.reshape(s))  # noqa: E731
    font = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    W, H = 1040, 220
    im = Image.new("RGB", (W, H), (245, 245, 240))
    d = ImageDraw.Draw(im)
    d.rectangle([4, 4, W - 5, H - 5], outline=(20, 20, 20), width=8)
    d.line([(840, 4), (840, H - 5)], fill=(20, 20, 20), width=6)
    d.line([(4, H // 2), (840, H // 2)], fill=(20, 20, 20), width=5)
    d.line([(420, 4), (420, H - 5)], fill=(20, 20, 20), width=5)
    num = spec["plate"][0]
    letters_en, letters_ar = spec["plate"][1], spec["plate"][2]
    arabic_digits = "".join("٠١٢٣٤٥٦٧٨٩"[int(c)] for c in num)
    f1 = ImageFont.truetype(font, 82)
    f2 = ImageFont.truetype(font, 34)

    def centered(text, box, f):
        l, t, r, b = d.textbbox((0, 0), text, font=f)
        x = box[0] + (box[2] - box[0] - (r - l)) / 2 - l
        y = box[1] + (box[3] - box[1] - (b - t)) / 2 - t
        d.text((x, y), text, font=f, fill=(15, 15, 15))

    centered(ar(" ".join(arabic_digits)), (4, 4, 420, H // 2), f1)
    centered(ar(" ".join(letters_ar)), (420, 4, 840, H // 2), f1)
    centered(" ".join(num), (4, H // 2, 420, H - 5), f1)
    centered(" ".join(letters_en), (420, H // 2, 840, H - 5), f1)
    centered(ar("السعودية"), (840, 10, W - 5, 80), f2)
    d.ellipse([890, 92, 990, 150], outline=(20, 120, 60), width=6)
    centered("KSA", (840, 150, W - 5, H - 10), f2)
    im.save(os.path.join(PLATES, f"T_Plate_{cid}.png"))

    # race number roundel (door decal)
    S = 512
    im = Image.new("RGB", (S, S), spec["accent_rgb_bg"])
    d = ImageDraw.Draw(im)
    d.ellipse([16, 16, S - 16, S - 16], fill=(250, 250, 248), outline=(20, 20, 20), width=14)
    f = ImageFont.truetype(font, 250)
    centered(spec["number"], (16, 40, S - 16, S - 110), f)
    f = ImageFont.truetype(font, 64)
    centered(ar(spec["name_ar"]), (60, S - 170, S - 60, S - 60), f)
    im.save(os.path.join(PLATES, f"T_Number_{cid}.png"))


# ------------------------------------------------------------ body build ---
class Car:
    def __init__(self, spec):
        self.s = spec
        self.L = spec["L"]
        self.tr, self.tf = spec["axles"]
        self.tm = (self.tr + self.tf) / 2
        self.c = {k: curve(spec[k]) for k in ("zb", "zs", "zt", "w", "wt", "cr")}
        make_plate_textures(spec)
        self.M = car_mats(spec)
        self.R = spec["R"]                       # (front, rear) tyre radius
        self.TW = spec["TW"]                     # (front, rear) tyre width
        self.parts = []                          # detail objects to join into the body

    # coordinates
    def X(self, t):
        return (t - self.tm) * self.L

    def prof(self, t):
        zb = self.c["zb"](t)
        zs = self.c["zs"](t)
        zt = max(self.c["zt"](t), zs)
        w = self.c["w"](t)
        wt = min(self.c["wt"](t), w * 0.97)
        cr = self.c["cr"](t)
        return zb, zs, zt, w, wt, cr

    def half(self, t):
        zb, zs, zt, w, wt, cr = self.prof(t)
        sh = self.s.get("shape", {})
        s1, s2 = sh.get("sh", (0.965, 0.9))
        side = sh.get("side", (0.985, 1.0))
        bot = sh.get("bot", (0.55, 0.9))
        bulge = sh.get("bulge", 0.03)
        d = zs - zb
        hc = zt - zs
        fc = clamp(hc / 0.25, 0, 1)              # 0 = hood/deck, 1 = full cabin
        wb = s2 * w - 0.015
        pts = [(0.0, zb), (bot[0] * w, zb), (bot[1] * w, zb + 0.035),
               (side[0] * w, zb + 0.3 * d), (side[1] * w, zb + 0.64 * d),
               (s1 * w, zs - 0.045 * d), (s2 * w, zs + 0.004),
               (lerp(wb, wt, 0.06), zs + 0.012 + 0.05 * hc),
               (lerp(wb, wt, 0.5) + bulge * hc, zs + 0.5 * hc),
               (lerp(wb, wt, 0.9) + 0.25 * bulge * hc, zs + 0.9 * hc),
               (wt, zt), (0.58 * wt, zt), (0.0, zt)]
        out = []
        for k, (y, z) in enumerate(pts):
            if k >= 7:
                dome_hood = cr * max(0.0, 1 - (y / max(s2 * w, 1e-3)) ** 2)
                dome_roof = cr * max(0.0, 1 - (y / max(wt, 1e-3)) ** 2) if k >= 10 else 0.0
                z += lerp(dome_hood, dome_roof, fc)
            out.append((y, z))
        return out, hc

    def ring(self, t):
        half, hc = self.half(t)
        x = self.X(t)
        pts = [(x, y, z) for y, z in half] + [(x, -y, z) for y, z in reversed(half[1:-1])]
        return pts, hc

    @staticmethod
    def hb(i):
        return i if i <= 11 else 23 - i

    def face_mat(self, t, hb, hc):
        s, M = self.s, self.M
        cab = hc > 0.12
        if hb <= 1:
            return M["under"]
        if hb == 2:
            return M[s.get("rocker", "paint")]
        if hb in (7, 8):
            if cab and in_ranges(t, s["side_glass"]) and not in_ranges(t, s.get("pillars", [])):
                return M["glass"]
            if cab and s.get("blackout"):
                return M["gloss"]
        if hb == 6 and cab and s.get("belt_trim"):
            return M["chrome"] if s.get("belt_trim") == "chrome" else M["trim"]
        if hb in (10, 11):
            if in_ranges(t, s["roof_glass"]):
                return M["glass"]
            if s.get("roof_black") and hc > 0.2:
                return M[s["roof_black"]]
        if hb == 9 and s.get("roof_black") and hc > 0.2 and not in_ranges(t, s["roof_glass"]):
            return M[s["roof_black"]]
        return M["paint"]

    def build_body(self):
        s = self.s
        n = s.get("stations", 72)
        ts = [i / n for i in range(n + 1)]
        rings, hcs = [], []
        for t in ts:
            r, hc = self.ring(t)
            rings.append(r)
            hcs.append(hc)
        es, ed = s.get("end", (0.78, 0.035))

        def shrink(ring, sc, dx):
            cz = sum(p[2] for p in ring) / len(ring)
            return [(p[0] + dx, p[1] * sc, cz + (p[2] - cz) * sc) for p in ring]

        rings = [shrink(rings[0], es, -ed)] + rings + [shrink(rings[-1], es, ed)]
        tt = [0.0] + ts + [1.0]
        hh = [hcs[0]] + hcs + [hcs[-1]]
        mats = {}

        def fm(j, i):
            tm = (tt[j] + tt[j + 1]) / 2
            hc = (hh[j] + hh[j + 1]) / 2
            m = self.face_mat(tm, self.hb(i), hc)
            mats[(j, i)] = m
            return m

        mb = sr.MB(f"{s['name']}_Shell")
        mb.loft(rings, closed=True, smooth=True, mats=fm, zip_caps=True)
        vr = mb.grid_last
        nr = len(rings[0])
        # crease material boundaries + character lines
        for j in range(len(vr)):
            for i in range(nr):
                i2 = (i + 1) % nr
                if 0 < j < len(vr) - 1 and mats.get((j - 1, i)) is not mats.get((j, i)):
                    mb.crease([vr[j][i]], [vr[j][i2]], 0.95)
        for j in range(len(vr) - 1):
            for i in range(nr):
                im = (i - 1) % nr
                if mats.get((j, im)) is not mats.get((j, i)):
                    mb.crease([vr[j][i]], [vr[j + 1][i]], 0.95)
        for hcrease, val in s.get("creases", {6: 0.55, 3: 0.3}).items():
            for i in (hcrease, 24 - hcrease):
                for j in range(len(vr) - 1):
                    mb.crease([vr[j][i]], [vr[j + 1][i]], val)
        body = mb.to_object(uv=False, sharp_angle=None)
        sr.subsurf(body, s.get("subdiv", 2))
        sr.smooth_all(body, 60)
        # wheel arches
        for (t, R, TW) in ((self.tr, self.R[1], self.TW[1]), (self.tf, self.R[0], self.TW[0])):
            if t == self.tr and s.get("rear_skirts"):
                continue
            w = self.c["w"](t)
            depth = TW + s.get("arch_depth", 0.16)
            ra = R + s.get("arch_gap", 0.045)
            for side in (1, -1):
                cm = sr.MB("cut")
                yc = side * (w - depth / 2 + 0.25)
                cm.cyl(ra, depth + 0.5, (self.X(t), yc, R + s.get("arch_lift", 0.0)), (90, 0, 0),
                       m=self.M["under"], seg=48)
                cut = cm.to_object(uv=False)
                sr.boolean(body, cut)
        # recessed intakes / vents / ducts: (center, size, rot, material, mirror_y)
        for (ctr, size, rot, mname, mirror) in s.get("cuts", []):
            cx = self.X(ctr[0]) if isinstance(ctr[0], T) else ctr[0]
            for sg in ((1, -1) if mirror else (1,)):
                cm = sr.MB("cut")
                cm.box(size, (cx, ctr[1] * sg, ctr[2]), (rot[0] * sg, rot[1], rot[2] * sg), m=self.M[mname],
                       bevel=min(size) * 0.2, seg=2)
                sr.boolean(body, cm.to_object(uv=False))
        self.body = body
        self.build_surface()
        return body

    def build_surface(self):
        me = self.body.data
        verts = [v.co.copy() for v in me.vertices]
        polys = [tuple(p.vertices) for p in me.polygons]
        self.bvh = BVHTree.FromPolygons(verts, polys)
        self.pmat = [self.body.material_slots[p.material_index].material for p in me.polygons]

    # ------------------------------------------------------ projection ---
    AX = {
        "front": (lambda a, b, f: (f, a, b), (-1, 0, 0)),
        "rear": (lambda a, b, f: (-f, a, b), (1, 0, 0)),
        "left": (lambda a, b, f: (a, f, b), (0, -1, 0)),
        "right": (lambda a, b, f: (a, -f, b), (0, 1, 0)),
        "top": (lambda a, b, f: (a, b, f), (0, 0, -1)),
    }

    def axis(self, axis):
        """axis: 'front'|'rear'|'left'|'right'|'top' or ('front'|'rear', tilt_deg, x_ref) for rays that
        come down at an angle (follows sloped noses / decks without stretching the decal)."""
        if isinstance(axis, str):
            fn, d = self.AX[axis]
            return fn, Vector(d)
        side, th, xref = axis
        th = math.radians(th)
        c_, s_ = math.cos(th), math.sin(th)
        if side == "front":
            return (lambda a, b, f: (xref + f * c_, a, b + f * s_)), Vector((-c_, 0, -s_))
        return (lambda a, b, f: (xref - f * c_, a, b + f * s_)), Vector((c_, 0, -s_))

    @staticmethod
    def mirrored(axis):
        """Return (axis, coord_fn) for the opposite side of the car."""
        name = axis if isinstance(axis, str) else axis[0]
        if name in ("front", "rear"):
            return axis, (lambda a, b: (-a, b))
        if name == "left":
            return "right", (lambda a, b: (a, b))
        if name == "top":
            return axis, (lambda a, b: (a, -b))
        return axis, (lambda a, b: (a, b))

    def hit(self, axis, a, b, avoid=()):
        fn, d = self.axis(axis)
        o = Vector(fn(a, b, 20.0))
        loc, nor, idx, dist = self.bvh.ray_cast(o, d)
        if loc is None:
            return None, None
        if avoid and self.pmat[idx] in avoid:
            return None, None
        if nor.dot(d) > 0:
            nor = -nor
        return loc, nor

    def patch(self, mb, axis, grid, m, off=0.004, avoid=(), uv=False, uv_rect=None):
        """grid: rows of (a,b) plane points. Projects onto the body and builds a conforming patch."""
        rows = []
        for r in grid:
            row = []
            for (a, b) in r:
                loc, nor = self.hit(axis, a, b, avoid)
                row.append(None if loc is None else loc + nor * off)
            rows.append(row)
        made = []
        nu, nv = len(rows), len(rows[0])
        vcache = {}
        vuv = {}
        outward = -self.axis(axis)[1]

        def V(i, j):
            if (i, j) not in vcache:
                v = mb.bm.verts.new(rows[i][j])
                vcache[(i, j)] = v
                if uv_rect:      # planar mapping: (a0, b0, a1, b1) -> 0..1 (a0 > a1 mirrors)
                    a_, b_ = grid[i][j]
                    a0, b0, a1, b1 = uv_rect
                    vuv[v] = ((a_ - a0) / (a1 - a0), (b_ - b0) / (b1 - b0))
                else:
                    vuv[v] = (i / (nu - 1), j / (nv - 1))
            return vcache[(i, j)]
        for i in range(nu - 1):
            for j in range(nv - 1):
                c = [rows[i][j], rows[i + 1][j], rows[i + 1][j + 1], rows[i][j + 1]]
                if any(p is None for p in c):
                    continue
                f = mb.bm.faces.new((V(i, j), V(i + 1, j), V(i + 1, j + 1), V(i, j + 1)))
                mb._tag([f], m, True)
                f.normal_update()
                if f.normal.dot(outward) < 0:
                    f.normal_flip()
                f[mb.keep] = 1
                if uv:
                    f[mb.uvfix] = 1
                    for lp in f.loops:
                        lp[mb.uvl].uv = vuv[lp.vert]
                made.append(f)
        return made

    @staticmethod
    def quad_grid(c00, c10, c11, c01, nu=10, nv=6):
        g = []
        for i in range(nu + 1):
            u = i / nu
            row = []
            for j in range(nv + 1):
                v = j / nv
                a = (1 - u) * (1 - v) * c00[0] + u * (1 - v) * c10[0] + u * v * c11[0] + (1 - u) * v * c01[0]
                b = (1 - u) * (1 - v) * c00[1] + u * (1 - v) * c10[1] + u * v * c11[1] + (1 - u) * v * c01[1]
                row.append((a, b))
            g.append(row)
        return g

    @staticmethod
    def disc_grid(ca, cb, ra, rb, n=8):
        g = []
        for i in range(n + 1):
            u = -1 + 2 * i / n
            row = []
            for j in range(n + 1):
                v = -1 + 2 * j / n
                x = u * math.sqrt(max(0, 1 - v * v / 2))
                y = v * math.sqrt(max(0, 1 - u * u / 2))
                row.append((ca + x * ra, cb + y * rb))
            g.append(row)
        return g

    @staticmethod
    def strip_grid(poly, width, step=0.03):
        pts = []
        for k in range(len(poly) - 1):
            a, b = Vector(poly[k]), Vector(poly[k + 1])
            n = max(1, int((b - a).length / step))
            for i in range(n):
                pts.append(a.lerp(b, i / n))
        pts.append(Vector(poly[-1]))
        g = []
        for k, p in enumerate(pts):
            t = (pts[min(k + 1, len(pts) - 1)] - pts[max(k - 1, 0)]).normalized()
            nrm = Vector((-t.y, t.x))
            g.append([tuple(p - nrm * width / 2), tuple(p + nrm * width / 2)])
        return g

    def both(self, fn):
        """Call fn(sign) for the left (+1) and right (-1) side."""
        fn(1)
        fn(-1)

    # ---------------------------------------------------------- wheels ---
    def wheel(self, name, front=True):
        s, M = self.s, self.M
        R = self.R[0] if front else self.R[1]
        TW = self.TW[0] if front else self.TW[1]
        Rr = R * s.get("rim_ratio", 0.68)
        tread = s.get("tread", "road")
        depth = {"road": 0.008, "rally": 0.016, "offroad": 0.03, "slick": 0.0}[tread]
        R0 = R - depth
        mb = sr.MB(name)
        prof = [(Rr + 0.004, TW * 0.40), (lerp(Rr, R0, 0.35), TW * 0.49), (lerp(Rr, R0, 0.8), TW * 0.5),
                (R0 - 0.012, TW * 0.475), (R0, TW * 0.42), (R0, -TW * 0.42), (R0 - 0.012, -TW * 0.475),
                (lerp(Rr, R0, 0.8), -TW * 0.5), (lerp(Rr, R0, 0.35), -TW * 0.49), (Rr + 0.004, -TW * 0.40)]
        mb.lathe(prof, seg=72, rot=(-90, 0, 0), m=M["tire"])
        # tread blocks
        if tread == "road":
            N, rows, bw, fill = 64, (-0.3, -0.1, 0.1, 0.3), 0.17, 0.78
        elif tread == "rally":
            N, rows, bw, fill = 40, (-0.32, 0.0, 0.32), 0.24, 0.6
        elif tread == "offroad":
            N, rows, bw, fill = 26, (-0.24, 0.24), 0.40, 0.55
        else:
            N, rows = 0, ()
        for k in range(N):
            for ri, yr in enumerate(rows):
                a = 2 * math.pi * (k + (0.5 if ri % 2 else 0.0)) / N
                arc = 2 * math.pi * R / N
                rad = R0 + depth / 2 - 0.002
                mb.box((arc * fill, TW * bw, depth + 0.004),
                       (rad * math.sin(a), yr * TW, rad * math.cos(a)), (0, math.degrees(a), 0), m=M["tire"])
            if tread == "offroad":   # shoulder lugs wrapping the sidewall
                for sgn in (1, -1):
                    a = 2 * math.pi * (k + (0.5 if sgn > 0 else 0)) / N
                    rad = R0 - 0.02
                    mb.box((2 * math.pi * R / N * 0.42, 0.05, 0.07),
                           (rad * math.sin(a), sgn * TW * 0.47, rad * math.cos(a)), (0, math.degrees(a), 0),
                           m=M["tire"])
        # rim barrel + lip
        rp = [(Rr - 0.02, -TW * 0.40), (Rr + 0.012, -TW * 0.43), (Rr + 0.012, -TW * 0.38),
              (Rr - 0.012, -TW * 0.30), (Rr - 0.016, TW * 0.30), (Rr - 0.005, TW * 0.40),
              (Rr + 0.016, TW * 0.43), (Rr + 0.018, TW * 0.47), (Rr - 0.004, TW * 0.475),
              (Rr - 0.02, TW * 0.44)]
        mb.lathe(rp, seg=64, rot=(-90, 0, 0), m=M["rim"])
        # brake disc + hat
        mb.cyl(Rr * 0.8, 0.028, (0, -TW * 0.05, 0), (90, 0, 0), m=M["disc"], seg=40)
        mb.cyl(Rr * 0.42, 0.06, (0, -TW * 0.02, 0), (90, 0, 0), m=M["disc"], seg=32)
        self.rim_face(mb, Rr, TW, s.get("rim", "split5"))
        return mb.to_object(uv=False, sharp_angle=50)

    def spoke(self, mb, a, r0, r1, y0, y1, w0, w1, th, m):
        er = Vector((math.sin(a), 0, math.cos(a)))
        et = Vector((math.cos(a), 0, -math.sin(a)))
        ey = Vector((0, 1, 0))
        p0 = er * r0 + ey * y0
        p1 = er * r1 + ey * y1
        vs = []
        for p, w in ((p0, w0), (p1, w1)):
            for sy in (0, -th):
                for st in (-0.5, 0.5):
                    vs.append(mb.bm.verts.new(p + et * (w * st) + ey * sy))
        # vs: 0 p0 front -, 1 p0 front +, 2 p0 back -, 3 p0 back +, 4..7 same at p1
        F = [(0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5), (0, 2, 3, 1), (4, 5, 7, 6)]
        faces = [mb.bm.faces.new([vs[i] for i in f]) for f in F]
        mb._tag(faces, m, False)

    def rim_face(self, mb, Rr, TW, style):
        M = self.M
        rim = M["rim"]
        yf = TW * 0.40           # outer face plane at lip
        yh = TW * 0.22           # hub plane (concave dish)
        hub_r = 0.075
        rin = Rr - 0.012
        if style in ("split5", "multi", "mono", "y6", "mesh"):
            if style == "split5":
                for k in range(5):
                    for off in (-0.11, 0.11):
                        a = 2 * math.pi * k / 5 + off
                        self.spoke(mb, a, hub_r, rin, yh, yf, 0.045, 0.03, 0.03, rim)
            elif style == "multi":
                for k in range(10):
                    a = 2 * math.pi * k / 10
                    self.spoke(mb, a, hub_r, rin, yh, yf, 0.04, 0.026, 0.028, rim)
            elif style == "mono":
                for k in range(5):
                    a = 2 * math.pi * k / 5
                    self.spoke(mb, a, hub_r, rin, yh, yf, 0.085, 0.07, 0.04, rim)
            elif style == "y6":
                for k in range(6):
                    a = 2 * math.pi * k / 6
                    self.spoke(mb, a, hub_r, Rr * 0.55, yh, (yh + yf) / 2, 0.06, 0.05, 0.035, rim)
                    for off in (-0.16, 0.16):
                        self.spoke(mb, a + off * 0.4, Rr * 0.52, rin, (yh + yf) / 2, yf, 0.035, 0.03, 0.03, rim)
            elif style == "mesh":
                for k in range(12):
                    for off in (-0.26, 0.26):
                        a = 2 * math.pi * k / 12
                        er0 = a
                        self.spoke(mb, er0, hub_r, rin, yh, yf, 0.022, 0.018, 0.022, rim)
                        self.spoke(mb, a + off, Rr * 0.45, rin, (yh + yf) / 2, yf, 0.016, 0.016, 0.018, rim)
                mb.lathe([(Rr * 0.45, yh + 0.03), (Rr * 0.48, yh + 0.03), (Rr * 0.48, yh + 0.05), (Rr * 0.45, yh + 0.05)],
                         seg=48, rot=(-90, 0, 0), m=rim)
        elif style in ("steel", "beadlock"):
            # pressed dish with round holes
            mb.lathe([(hub_r, yh), (Rr * 0.5, yh + 0.01), (Rr * 0.7, yh + 0.05), (rin, yf - 0.03), (rin, yf - 0.06)],
                     seg=48, rot=(-90, 0, 0), m=rim, smooth=True)
            nh = 8 if style == "steel" else 6
            for k in range(nh):
                a = 2 * math.pi * (k + 0.5) / nh
                r = Rr * 0.62
                mb.cyl(0.035 if style == "steel" else 0.05, 0.03, (r * math.sin(a), yh + 0.035, r * math.cos(a)),
                       (90, 0, 0), m=M["trim"], seg=16)
            if style == "beadlock":
                mb.lathe([(Rr - 0.01, yf + 0.0), (Rr + 0.03, yf + 0.0), (Rr + 0.03, yf + 0.025), (Rr - 0.01, yf + 0.025)],
                         seg=48, rot=(-90, 0, 0), m=M["trim"])
                for k in range(24):
                    a = 2 * math.pi * k / 24
                    r = Rr + 0.01
                    mb.cyl(0.007, 0.02, (r * math.sin(a), yf + 0.03, r * math.cos(a)), (90, 0, 0), m=M["chrome"], seg=6)
        elif style == "turbine":
            mb.lathe([(hub_r, yh + 0.02), (rin * 0.98, yf - 0.02), (rin, yf - 0.03)], seg=64, rot=(-90, 0, 0),
                     m=M["trim"])
            for k in range(14):
                a = 2 * math.pi * k / 14
                self.spoke(mb, a, hub_r + 0.02, rin, yh + 0.035, yf, 0.03, 0.08, 0.012, rim)
            mb.lathe([(rin - 0.02, yf - 0.005), (rin, yf - 0.005), (rin, yf + 0.005), (rin - 0.02, yf + 0.005)],
                     seg=64, rot=(-90, 0, 0), m=M["glow"])
        # hub, lug nuts, centre cap
        mb.cyl(hub_r, 0.05, (0, yh - 0.01, 0), (90, 0, 0), m=rim, seg=24)
        nl = 6 if style in ("steel", "beadlock") else 5
        for k in range(nl):
            a = 2 * math.pi * k / nl
            mb.cyl(0.011, 0.03, (0.05 * math.sin(a), yh + 0.02, 0.05 * math.cos(a)), (90, 0, 0), m=M["chrome"], seg=6)
        mb.cyl(0.032, 0.012, (0, yh + 0.03, 0), (90, 0, 0), m=M["accent"], seg=24)

    # -------------------------------------------------------- interior ---
    def interior(self, mb):
        s, M = self.s, self.M
        a, b = s["side_glass"][0][0], s["side_glass"][-1][1]
        rings = []
        for k in range(14):
            t = lerp(a + 0.01, b - 0.005, k / 13)
            half, hc = self.half(t)
            zb, zs, zt, w, wt, cr = self.prof(t)
            x = self.X(t)
            pts = []
            for (y, z) in half:
                y2 = max(0.0, y - 0.06)
                z2 = clamp(z, zb + 0.1, zt - 0.04)
                pts.append((x, y2, z2))
            ring = pts + [(x, -y, z) for (x, y, z) in reversed(pts[1:-1])]
            rings.append(ring)
        faces = mb.loft(rings, M["interior"], closed=True, cap_start=True, cap_end=True, smooth=False)
        mb.flip(faces)
        # seats, dash, wheel
        ts = lerp(a, b, 0.42)
        zb, zs, zt, w, wt, cr = self.prof(ts)
        xs = self.X(ts)
        floor = zb + 0.1
        head = zt - floor - 0.12              # usable height under the roof
        k = clamp(head / 1.0, 0.55, 1.0)       # shrink seats in low supercars
        for sy in (1, -1):
            y = sy * w * 0.38
            mb.box((0.5, 0.48, 0.14 * k), (xs, y, floor + 0.2 * k), m=M["leather"], bevel=0.04, seg=2)
            mb.box((0.14, 0.48, 0.6 * k), (xs - 0.24, y, floor + 0.55 * k), (0, -14, 0), m=M["leather"], bevel=0.04, seg=2)
            mb.box((0.1, 0.26, 0.15 * k), (xs - 0.24 - 0.2 * k, y, floor + 0.93 * k), (0, -14, 0), m=M["leather"],
                   bevel=0.03, seg=2)
        xd = self.X(lerp(a, b, 0.85))
        mb.box((0.35, w * 1.5, 0.2), (xd, 0, zs + 0.02), m=M["interior"], bevel=0.05, seg=2)
        # steering wheel (driver on the left = +Y)
        xw = xd - 0.3
        rim_pts = [(0.17 + 0.018 * math.cos(2 * math.pi * k / 8), 0.018 * math.sin(2 * math.pi * k / 8)) for k in range(9)]
        mb.lathe(rim_pts, seg=28, loc=(xw, w * 0.38, zs + 0.12), rot=(0, -62, 0), m=M["trim"])
        mb.cyl(0.05, 0.08, (xw + 0.04, w * 0.38, zs + 0.1), (0, -62, 0), m=M["trim"], seg=16)
        mb.box((0.2, 0.18, 0.12), (xd - 0.12, 0, zb + 0.35), m=M["interior"], bevel=0.02, seg=2)  # centre console

    # --------------------------------------------------------- generic ---
    def lights_and_trim(self, mb):
        s, M = self.s, self.M
        avoid = (M["glass"], M["trim"], M["grille"])
        for item in s.get("decals", []):
            kind = item[0]
            if kind == "roundel":  # ("roundel", (x, z), radius): race number on both doors
                _, (cx, cz), rad = item
                for axis, flip in (("left", True), ("right", False)):   # text reads left-to-right
                    g = self.disc_grid(cx, cz, rad, rad, n=12)
                    r2 = rad / 0.94                   # roundel art is inset 6% inside the texture
                    rect = (cx + r2, cz - r2, cx - r2, cz + r2) if flip else (cx - r2, cz - r2, cx + r2, cz + r2)
                    self.patch(mb, axis, g, M["number"], 0.0055, avoid, uv=True, uv_rect=rect)
                continue
            if kind == "quad":     # ("quad", axis, corners, material, offset, mirror)
                _, axis, cs, mname, off, mirror = item
                make = lambda f: self.quad_grid(*[f(*c) for c in cs], nu=12, nv=6)  # noqa: E731
            elif kind == "disc":   # ("disc", axis, (a, b), (ra, rb), material, offset, mirror)
                _, axis, (ca, cb), (ra, rb), mname, off, mirror = item
                make = lambda f: self.disc_grid(*f(ca, cb), ra, rb)  # noqa: E731
            elif kind == "strip":  # ("strip", axis, polyline, width, material, offset, mirror)
                _, axis, poly, width, mname, off, mirror = item
                make = lambda f: self.strip_grid([f(*p) for p in poly], width)  # noqa: E731
            else:
                continue
            self.patch(mb, axis, make(lambda a, b: (a, b)), M[mname], off, avoid)
            if mirror:
                ax2, f2 = self.mirrored(axis)
                self.patch(mb, ax2, make(f2), M[mname], off, avoid)
        self.doors(mb)
        self.plates(mb)

    def doors(self, mb):
        """Door shut-lines + handles on both sides (doors given as (t_rear, t_front) spans)."""
        M = self.M
        for (t0, t1) in self.s.get("doors", []):
            x0, x1 = self.X(t0), self.X(t1)
            zb0, zs0 = self.prof(t0)[:2]
            zb1, zs1 = self.prof(t1)[:2]
            bot = max(zb0, zb1) + 0.13
            poly = [(x0, zs0 - 0.015), (x0, bot), (x1, bot), (x1, zs1 - 0.015)]
            g = self.strip_grid(poly, 0.007, step=0.02)
            for axis in ("left", "right"):
                self.patch(mb, axis, g, M["trim"], 0.0015, (M["glass"],))
                loc, nor = self.hit(axis, x0 + 0.16, zs0 - 0.1)
                if loc is not None:
                    mb.box((0.15, 0.022, 0.028), tuple(loc + nor * 0.008), m=M["chrome"], bevel=0.008, seg=2)

    def plates(self, mb):
        """Licence plates front and rear (52 x 11 cm, Saudi format)."""
        s, M = self.s, self.M
        hw, hh = 0.26, 0.055
        for axis, spec in (("front", s["plate_z"][0]), ("rear", s["plate_z"][1])):
            if spec is None:
                continue
            z, sgn = spec
            loc, nor = self.hit(axis, 0.0, z)
            if loc is None:
                continue
            x = loc.x + sgn * 0.016
            if axis == "front":   # viewer at +X looking -X: screen-right is +Y
                pts = [(x, -hw, z - hh), (x, hw, z - hh), (x, hw, z + hh), (x, -hw, z + hh)]
            else:                 # viewer at -X looking +X: screen-right is -Y
                pts = [(x, hw, z - hh), (x, -hw, z - hh), (x, -hw, z + hh), (x, hw, z + hh)]
            f = mb.quad_uv(pts, ((0, 0), (1, 0), (1, 1), (0, 1)), M["plate"])
            f[mb.keep] = 1
            mb.box((0.02, 2 * hw + 0.03, 2 * hh + 0.03), (x - sgn * 0.011, 0, z), m=M["trim"])

    def mirrors(self, mb):
        s, M = self.s, self.M
        if not s.get("mirror_t"):
            return
        t = s["mirror_t"]
        zb, zs, zt, w, wt, cr = self.prof(t)
        x = self.X(t)
        for sg in (1, -1):
            y0 = sg * (w * 0.9)
            z0 = zs + 0.06
            mb.box((0.06, 0.12, 0.035), (x, sg * (w * 0.9 + 0.05), z0), m=M["trim"], bevel=0.01, seg=2)
            mb.box((0.11, 0.2, 0.11), (x - 0.02, sg * (w * 0.9 + 0.17), z0 + 0.05), m=M["paint"], bevel=0.035, seg=3)
            mb.box((0.012, 0.17, 0.085), (x - 0.078, sg * (w * 0.9 + 0.17), z0 + 0.05), m=M["mirror"])

    def exhausts(self, mb):
        s, M = self.s, self.M
        for (y, z, r, length) in s.get("exhaust", []):
            loc, nor = self.hit("rear", y, z)
            x = (loc.x if loc is not None else self.X(0)) + 0.02
            mb.cyl(r, length, (x + 0.02 - length / 2, y, z), (0, 90, 0), m=M["exhaust"], seg=24, caps=False)
            mb.cyl(r * 0.82, length, (x + 0.019 - length / 2, y, z), (0, 90, 0), m=M["soot"], seg=24, caps=True)

    def wing(self, mb, x, z, span, chord, stand=True, m="carbon", endplate=True, angle=-8):
        M = self.M
        prof = [(0.0, 0.0), (0.12, 0.035), (0.35, 0.05), (0.7, 0.035), (1.0, 0.0), (0.7, 0.012), (0.3, 0.012), (0.08, -0.004)]
        rings = []
        ca, sa = math.cos(math.radians(angle)), math.sin(math.radians(angle))
        for yy in (-span / 2, span / 2):
            ring = []
            for (u, v) in prof:
                px, pz = -u * chord, v * chord * 1.6
                ring.append((x + px * ca - pz * sa, yy, z + px * sa + pz * ca))
            rings.append(ring)
        mb.loft(rings, M[m], closed=True, cap_start=True, cap_end=True, smooth=False)
        if endplate:
            for sg in (1, -1):
                mb.box((chord * 1.1, 0.012, 0.15), (x - chord * 0.5, sg * span / 2, z - 0.01), m=M[m], bevel=0.004)
        if stand:
            for sg in (1, -1):
                y = sg * span * 0.28
                loc, nor = self.hit("top", x - chord * 0.5, y)
                zb_ = loc.z if loc is not None else z - 0.3
                h = z - zb_
                mb.box((0.12, 0.018, h + 0.02), (x - chord * 0.5, y, zb_ + h / 2), (0, 12, 0), m=M[m], bevel=0.004)

    def tube_cage(self, mb, paths, r=0.025, m="trim"):
        for p in paths:
            mb.tube(p, r, self.M[m], seg=10)

    # ------------------------------------------------------- assemble ---
    def build(self):
        s = self.s
        body = self.build_body()
        det = sr.MB(f"{s['name']}_Details")
        self.lights_and_trim(det)
        self.mirrors(det)
        self.exhausts(det)
        self.interior(det)
        for fn in s.get("extras", []):
            fn(self, det)
        det_o = det.to_object(uv=True, sharp_angle=40)
        body = sr.join([body, det_o], f"SM_{s['name']}_Body")
        self.body = body
        wheels = {}
        for key, front, sx, sy in (("FL", True, 1, 1), ("FR", True, 1, -1), ("RL", False, -1, 1), ("RR", False, -1, -1)):
            wo = self.wheel(f"Wheel_{key}", front)
            t = self.tf if front else self.tr
            R = self.R[0] if front else self.R[1]
            TW = self.TW[0] if front else self.TW[1]
            w = self.c["w"](t)
            yc = w - TW / 2 - s.get("wheel_inset", 0.04)
            wo.location = (self.X(t), sy * yc, R)
            if sy < 0:
                wo.rotation_euler = (0, 0, math.pi)
            wheels[key] = wo
        return body, wheels


# ------------------------------------------------------------- rigging ---
def rig_and_export(car, body, wheels):
    s = car.s
    name = s["name"]
    folder = os.path.join(OUT, name)
    # static exports first
    sr.export_fbx(body, os.path.join(folder, f"SM_{name}_Body.fbx"))
    for key, label in (("FL", "F"), ("RL", "R")):
        w = wheels[key]
        loc = w.location.copy()
        w.location = (0, 0, 0)
        sr.export_fbx(w, os.path.join(folder, f"SM_{name}_Wheel_{label}.fbx"))
        w.location = loc
    # skeletal: one mesh, vertex groups -> bones
    arm_d = bpy.data.armatures.new("Armature")
    arm = bpy.data.objects.new("Armature", arm_d)
    bpy.context.scene.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    root = arm_d.edit_bones.new("Root")
    root.head = (0, 0, 0)
    root.tail = (0.5, 0, 0)
    for key, w in wheels.items():
        b = arm_d.edit_bones.new(f"Wheel_{key}")
        b.head = w.location
        b.tail = Vector(w.location) + Vector((0, 0.25 if key.endswith("L") else -0.25, 0))
        b.parent = root
    bpy.ops.object.mode_set(mode="OBJECT")

    parts = []
    bcopy = body.copy()
    bcopy.data = body.data.copy()
    bpy.context.scene.collection.objects.link(bcopy)
    vg = bcopy.vertex_groups.new(name="Root")
    vg.add(list(range(len(bcopy.data.vertices))), 1.0, "REPLACE")
    parts.append(bcopy)
    for key, w in wheels.items():
        wc = w.copy()
        wc.data = w.data.copy()
        bpy.context.scene.collection.objects.link(wc)
        g = wc.vertex_groups.new(name=f"Wheel_{key}")
        g.add(list(range(len(wc.data.vertices))), 1.0, "REPLACE")
        parts.append(wc)
    for o in bpy.context.scene.objects:
        o.select_set(False)
    for o in parts:
        o.select_set(True)
    bpy.context.view_layer.objects.active = bcopy
    with bpy.context.temp_override(active_object=bcopy, selected_editable_objects=parts, selected_objects=parts):
        bpy.ops.object.join()
    sk = bcopy
    sk.name = f"SK_{name}"
    sk.data.name = f"SK_{name}"
    sk.parent = arm
    mod = sk.modifiers.new("Armature", "ARMATURE")
    mod.object = arm
    sr.export_fbx([arm], os.path.join(folder, f"SK_{name}.fbx"), armature=True)
    sr.export_glb([arm], os.path.join(folder, f"{name}_preview.glb"))
    bpy.data.objects.remove(sk, do_unlink=True)
    bpy.data.objects.remove(arm, do_unlink=True)
    return


# --------------------------------------------------------------- studio ---
def studio(L=4.6):
    sr.setup_render((1280, 720), samples=64, exposure=-0.3)
    mb = sr.MB("Cyc")
    floor = sr.mat("Studio_Floor", (0.18, 0.18, 0.19), rough=0.35)
    mb.lathe([(0, 0), (9, 0), (11, 0.4), (13, 1.8), (14.5, 4.5), (15.5, 9), (16, 14)], seg=96, m=floor,
             close_bottom=False)
    mb.to_object(uv=False)
    sr.world_color((0.05, 0.05, 0.055), (0.12, 0.12, 0.13), 0.45)
    sr.area_light((3, 5, 6), (0, 0, 0.6), 1300, 6)
    sr.area_light((5, -6, 3), (0, 0, 0.6), 500, 5, (0.9, 0.95, 1.0))
    sr.area_light((-7, 1, 4), (0, 0, 0.6), 1000, 4, (1.0, 0.93, 0.85))
    sr.area_light((0, 0, 8), (0, 0, 0), 700, 7)


def render_car(car, body, wheels, tag=""):
    name = car.s["name"]
    L = car.L
    studio(L)
    parts = [body] + list(wheels.values())
    sr.frame_camera(parts, (1.25, 0.95, 0.32), 50, margin=0.62)
    sr.render(os.path.join(PREV, f"{name}_front.png"))
    sr.frame_camera(parts, (-1.2, 0.9, 0.36), 50, margin=0.62)
    sr.render(os.path.join(PREV, f"{name}_rear.png"))


# ============================================================ car specs ===
def ex_falcon(c, mb):
    M = c.M
    c.wing(mb, c.X(0.035), 1.16, 1.78, 0.34, stand=True, m="carbon")
    # front splitter (placed against the nose) + diffuser fins
    loc, n = c.hit("front", 0.0, 0.2)
    xn = loc.x if loc is not None else c.X(1.0)
    mb.box((0.36, 1.7, 0.022), (xn - 0.1, 0, 0.12), m=M["carbon"], bevel=0.005)
    for y in (-0.55, -0.3, 0.3, 0.55):
        mb.box((0.5, 0.012, 0.16), (c.X(0.05), y, 0.2), (0, 18, 0), m=M["carbon"])
    # engine cover louvres
    for k in range(7):
        x = c.X(0.2 + k * 0.022)
        loc, n = c.hit("top", x, 0)
        if loc is not None:
            mb.box((0.03, 0.7, 0.02), (x, 0, loc.z + 0.005), (0, -10, 0), m=M["gloss"])


def ex_dunefox(c, mb):
    M = c.M
    # open bed, roll cage over it + spare tyre
    cut_bed(c, 0.025, 0.415, 0.82, 0.95)
    x0, x1 = c.X(0.08), c.X(0.44)
    zt = 1.86
    zbed = 0.95
    for sg in (1, -1):
        y = sg * 0.78
        c.tube_cage(mb, [[(x1, y, zt), (x0 + 0.3, y, 1.62), (x0, y, zbed)]], 0.035, "trim")
        c.tube_cage(mb, [[(c.X(0.3), y, 1.72), (c.X(0.3), y, zbed)]], 0.03, "trim")
    c.tube_cage(mb, [[(x0 + 0.3, 0.78, 1.62), (x0 + 0.3, -0.78, 1.62)]], 0.035, "trim")
    # spare tyre lying in the bed
    sp = c.wheel("spare", False)
    mb.add_object(sp, loc=(c.X(0.2), 0, zbed + 0.17), rot=(90, 0, 0))
    bpy.data.objects.remove(sp, do_unlink=True)
    # roof light bar
    mb.box((0.14, 1.3, 0.11), (c.X(0.56), 0, 1.98), m=M["trim"], bevel=0.02, seg=2)
    for k in range(8):
        mb.cyl(0.045, 0.02, (c.X(0.56) + 0.07, -0.56 + k * 0.16, 1.98), (0, 90, 0), m=M["head"], seg=16)
    # long-travel front suspension arms + shocks (visible under body)
    for sg in (1, -1):
        yw = sg * 0.82
        for z in (0.42, 0.62):
            c.tube_cage(mb, [[(c.X(c.tf) - 0.15, sg * 0.25, z + 0.05), (c.X(c.tf), yw, z)], [(c.X(c.tf) + 0.15, sg * 0.25, z + 0.05), (c.X(c.tf), yw, z)]], 0.028, "accent")
        mb.cyl(0.045, 0.6, (c.X(c.tf) - 0.05, sg * 0.6, 0.88), (sg * 25, 0, 0), m=M["chrome"], seg=16)
        mb.cyl(0.07, 0.3, (c.X(c.tf) - 0.05, sg * 0.66, 1.0), (sg * 25, 0, 0), m=M["accent"], seg=16)
        for z in (0.45,):
            c.tube_cage(mb, [[(c.X(c.tr) + 0.6, sg * 0.3, 0.6), (c.X(c.tr), sg * 0.85, z)]], 0.04, "accent")
    # bash plate + front bumper tube
    mb.box((0.6, 1.0, 0.03), (c.X(0.97), 0, 0.72), (0, 22, 0), m=M["chrome"], bevel=0.008)
    c.tube_cage(mb, [[(c.X(1.0) + 0.05, -0.75, 0.95), (c.X(1.0) + 0.12, -0.4, 0.88), (c.X(1.0) + 0.12, 0.4, 0.88), (c.X(1.0) + 0.05, 0.75, 0.95)]], 0.035, "trim")
    flares(c, mb, 0.07)


def flares(c, mb, width=0.06, m="trim"):
    """Fender flares hugging the cut wheel arches."""
    for (t, R) in ((c.tr, c.R[1]), (c.tf, c.R[0])):
        if t == c.tr and c.s.get("rear_skirts"):
            continue
        w = c.c["w"](t)
        ra = R + c.s.get("arch_gap", 0.045)
        z = R + c.s.get("arch_lift", 0.0)
        for sg in (1, -1):
            mb.lathe([(ra, -0.11), (ra + width, -0.06), (ra + width, 0.0), (ra, 0.03)], seg=40, arc=180,
                     loc=(c.X(t), sg * (w - 0.04), z), rot=(90, 0, 0 if sg > 0 else 180), m=c.M[m])


def ex_najdi(c, mb):
    M = c.M
    # roof rack
    zr = 1.97
    x0, x1 = c.X(0.08), c.X(0.6)
    for sg in (1, -1):
        c.tube_cage(mb, [[(x0, sg * 0.72, zr), (x1, sg * 0.72, zr)]], 0.022, "trim")
        for t in (0.1, 0.33, 0.58):
            mb.box((0.05, 0.05, 0.08), (c.X(t), sg * 0.72, zr - 0.04), m=M["trim"])
    for t in (0.12, 0.2, 0.28, 0.36, 0.44, 0.52):
        c.tube_cage(mb, [[(c.X(t), -0.72, zr), (c.X(t), 0.72, zr)]], 0.016, "trim")
    # bull bar
    xf = c.X(1.0) + 0.1
    c.tube_cage(mb, [[(xf - 0.05, -0.85, 0.42), (xf, -0.8, 0.95), (xf, 0.8, 0.95), (xf - 0.05, 0.85, 0.42)]], 0.038, "chrome")
    c.tube_cage(mb, [[(xf, -0.35, 0.45), (xf + 0.02, -0.35, 0.95)], [(xf, 0.35, 0.45), (xf + 0.02, 0.35, 0.95)]], 0.034, "chrome")
    mb.box((0.06, 1.75, 0.18), (xf - 0.04, 0, 0.48), m=M["chrome"], bevel=0.015)
    # snorkel (right side)
    xs = c.X(0.63)
    c.tube_cage(mb, [[(xs + 0.25, -0.99, 0.95), (xs + 0.05, -1.0, 1.15), (xs, -0.98, 1.6), (xs + 0.1, -0.9, 1.95)]], 0.05, "trim")
    mb.box((0.18, 0.14, 0.12), (xs + 0.12, -0.9, 1.98), m=M["trim"], bevel=0.02)
    # side steps
    for sg in (1, -1):
        mb.box((2.1, 0.2, 0.05), (c.X(0.43), sg * 0.94, 0.42), m=M["chrome"], bevel=0.01)
    # spare wheel on tailgate
    sp = c.wheel("spare", False)
    loc, n = c.hit("rear", 0.3, 1.05)
    mb.add_object(sp, loc=((loc.x if loc else c.X(0)) - 0.15, 0.3, 1.05), rot=(0, 0, 90))
    bpy.data.objects.remove(sp, do_unlink=True)
    flares(c, mb, 0.07)


def cut_bed(c, t0, t1, half_w, z_floor):
    """Boolean an open load bed into the body; cut faces get the black bed-liner material."""
    x0, x1 = c.X(t0), c.X(t1)
    cm = sr.MB("bedcut")
    cm.box((x1 - x0, 2 * half_w, 1.5), ((x0 + x1) / 2, 0, z_floor + 0.75), m=c.M["trim"])
    sr.boolean(c.body, cm.to_object(uv=False))
    c.build_surface()
    return x0, x1


def ex_hilux(c, mb):
    M = c.M
    x0, x1 = cut_bed(c, 0.025, 0.4, 0.8, 0.66)
    zb = 1.08
    # sports roll bar
    for sg in (1, -1):
        c.tube_cage(mb, [[(x1 - 0.15, sg * 0.72, zb), (x1 - 0.25, sg * 0.66, 1.62)]], 0.04, "chrome")
    c.tube_cage(mb, [[(x1 - 0.25, 0.66, 1.62), (x1 - 0.25, -0.66, 1.62)]], 0.04, "chrome")
    # light bar on roll bar
    mb.box((0.1, 1.0, 0.09), (x1 - 0.25, 0, 1.69), m=M["trim"], bevel=0.015)
    for k in range(6):
        mb.cyl(0.035, 0.02, (x1 - 0.19, -0.4 + k * 0.16, 1.69), (0, 90, 0), m=M["head"], seg=14)
    # front bumper guard
    xf = c.X(1.0) + 0.06
    c.tube_cage(mb, [[(xf, -0.6, 0.5), (xf + 0.05, -0.55, 0.85), (xf + 0.05, 0.55, 0.85), (xf, 0.6, 0.5)]], 0.035, "trim")
    for sg in (1, -1):
        mb.box((1.6, 0.18, 0.045), (c.X(0.5), sg * 0.92, 0.42), m=M["trim"], bevel=0.01)
    flares(c, mb, 0.055)


def ex_muscle(c, mb):
    M = c.M
    # hood scoop
    loc, n = c.hit("top", c.X(0.8), 0)
    z = loc.z if loc else 0.9
    mb.box((0.55, 0.42, 0.09), (c.X(0.8), 0, z + 0.03), m=M["gloss"], bevel=0.035, seg=3)
    mb.box((0.04, 0.34, 0.05), (c.X(0.8) + 0.27, 0, z + 0.045), m=M["trim"])
    # chrome bumpers
    for t, sg in ((1.0, 1), (0.0, -1)):
        loc, n = c.hit("front" if sg > 0 else "rear", 0, 0.42)
        x = loc.x if loc else c.X(t)
        mb.box((0.08, 1.7, 0.1), (x + sg * 0.03, 0, 0.42), m=M["chrome"], bevel=0.03, seg=3)
    # ducktail spoiler
    loc, n = c.hit("top", c.X(0.04), 0)
    z = loc.z if loc else 0.95
    mb.box((0.12, 1.5, 0.05), (c.X(0.04), 0, z + 0.015), (0, 12, 0), m=M["gloss"], bevel=0.01)


def ex_neom(c, mb):
    M = c.M
    # rear aero blade + under-glow strip
    c.wing(mb, c.X(0.03), 0.98, 1.7, 0.22, stand=False, m="gloss", endplate=False, angle=-4)
    for sg in (1, -1):
        mb.box((2.2, 0.03, 0.02), (c.X(0.5), sg * 0.92, 0.17), m=M["glow"])
    mb.box((0.03, 1.4, 0.02), (c.X(0.99), 0, 0.16), m=M["glow"])


def ex_rally(c, mb):
    M = c.M
    # roof spoiler at the top of the hatch
    c.wing(mb, c.X(0.02) + 0.02, 1.4, 1.42, 0.3, stand=False, m="accent", endplate=True, angle=-14)
    # roof scoop
    loc, n = c.hit("top", c.X(0.4), 0)
    z = loc.z if loc else 1.4
    mb.box((0.3, 0.26, 0.06), (c.X(0.4), 0, z + 0.02), m=M["trim"], bevel=0.02, seg=2)
    # bonnet light pod: 4 round rally lights
    xf = c.X(0.99) + 0.08
    mb.box((0.06, 1.25, 0.18), (xf, 0, 0.82), m=M["trim"], bevel=0.02, seg=2)
    for k in range(4):
        y = -0.45 + k * 0.3
        mb.cyl(0.085, 0.07, (xf + 0.05, y, 0.82), (0, 90, 0), m=M["trim"], seg=24)
        mb.cyl(0.07, 0.02, (xf + 0.09, y, 0.82), (0, 90, 0), m=M["head"], seg=24)
    # mud flaps
    for sg in (1, -1):
        for t in (c.tr - 0.065, c.tf - 0.07):
            mb.box((0.012, 0.3, 0.28), (c.X(t), sg * 0.78, 0.17), m=M["accent"])
    flares(c, mb, 0.06, "accent")
    # front splitter
    mb.box((0.24, 1.6, 0.02), (c.X(0.985), 0, 0.17), m=M["trim"], bevel=0.004)


def ex_gt(c, mb):
    M = c.M
    # side gill strakes behind front wheels
    for sg in (1, -1):
        for k in range(3):
            t = c.tf - 0.13 - k * 0.012
            loc, n = c.hit("left" if sg > 0 else "right", c.X(t), 0.62)
            if loc is not None:
                mb.box((0.012, 0.012, 0.16), (loc.x, loc.y + sg * 0.004, 0.62), (0, -20, 0), m=M["chrome"])
    # lip spoiler on rear deck
    loc, n = c.hit("top", c.X(0.03), 0)
    z = loc.z if loc else 0.9
    mb.box((0.08, 1.35, 0.02), (c.X(0.03), 0, z + 0.008), (0, 8, 0), m=M["carbon"])
    mb.box((0.26, 1.6, 0.02), (c.X(0.985), 0, 0.12), m=M["carbon"], bevel=0.004)


CARS = [
    dict(id="01", name="Falcon", doors=[(0.405, 0.63)], name_ar="الصقر", number="1", plate=("1001", "SRA", "سرا"),
         accent_rgb_bg=(10, 110, 70),
         L=4.55, axles=(0.19, 0.8), R=(0.335, 0.35), TW=(0.26, 0.32), rim="split5", rim_color=(0.08, 0.08, 0.09),
         rim_rough=0.3, tread="road", rim_ratio=0.69,
         paint=(0.0, 0.17, 0.085), metal=0.6, accent=(0.95, 0.95, 0.93), seat=(0.55, 0.42, 0.25),
         zb=[(0, 0.24), (0.05, 0.13), (0.9, 0.11), (0.97, 0.12), (1, 0.18)],
         zs=[(0, 0.86), (0.08, 0.92), (0.19, 0.92), (0.32, 0.84), (0.45, 0.77), (0.62, 0.73), (0.74, 0.74),
             (0.8, 0.76), (0.88, 0.68), (0.95, 0.55), (1, 0.42)],
         zt=[(0, 0), (0.1, 0.9), (0.2, 0.99), (0.31, 1.07), (0.4, 1.13), (0.47, 1.14), (0.54, 1.06),
             (0.6, 0.92), (0.65, 0.78), (0.7, 0.0), (1, 0)],
         w=[(0, 0.88), (0.04, 0.96), (0.15, 1.0), (0.27, 1.0), (0.38, 0.95), (0.55, 0.93), (0.72, 0.96),
            (0.82, 0.97), (0.93, 0.92), (1, 0.72)],
         wt=[(0, 0.5), (0.3, 0.58), (0.45, 0.6), (0.62, 0.6), (1, 0.55)],
         cr=[(0, 0.02), (0.4, 0.035), (0.75, 0.05), (1, 0.03)],
         shape=dict(sh=(0.96, 0.88), bulge=0.04), end=(0.8, 0.04),
         side_glass=[(0.395, 0.635)], roof_glass=[(0.5, 0.66), (0.27, 0.36)], roof_black="gloss",
         rocker="carbon", mirror_t=0.6, plate_z=(None, (0.5, -1)), creases={6: 0.8, 4: 0.35, 3: 0.3},
         exhaust=[(0.12, 0.42, 0.055, 0.25), (-0.12, 0.42, 0.055, 0.25)],
         cuts=[((2.3, 0.0, 0.27), (0.42, 0.78, 0.17), (0, 0, 0), "grille", False),         # main intake
               ((2.22, 0.66, 0.29), (0.42, 0.34, 0.17), (0, 0, 12), "grille", True),       # corner intakes
               ((-0.74, 1.02, 0.6), (0.55, 0.3, 0.3), (0, 0, -10), "grille", True),       # side radiator intakes
               ((1.85, 0.3, 0.75), (0.32, 0.26, 0.09), (0, -6, 0), "trim", True),          # bonnet vents
               ((-2.32, 0.55, 0.6), (0.3, 0.5, 0.2), (0, 0, 0), "grille", True)],          # rear heat vents
         decals=[
             ("quad", ("front", 38, 2.05), ((0.3, 0.46), (0.84, 0.53), (0.82, 0.7), (0.38, 0.62)), "lens", 0.004, True),
             ("strip", ("front", 38, 2.05), [(0.36, 0.6), (0.79, 0.665), (0.81, 0.56)], 0.028, "drl", 0.007, True),
             ("disc", ("front", 38, 2.05), (0.5, 0.555), (0.06, 0.045), "chrome", 0.006, True),
             ("disc", ("front", 38, 2.05), (0.5, 0.555), (0.045, 0.034), "head", 0.009, True),
             ("disc", ("front", 38, 2.05), (0.66, 0.575), (0.06, 0.045), "chrome", 0.006, True),
             ("disc", ("front", 38, 2.05), (0.66, 0.575), (0.045, 0.034), "head", 0.009, True),
             ("strip", ("front", 38, 2.05), [(0.82, 0.5), (0.86, 0.6)], 0.03, "amber", 0.007, True),
             ("strip", "rear", [(-0.86, 0.8), (0.86, 0.8)], 0.035, "tail", 0.006, False),
             ("quad", "rear", ((-0.8, 0.22), (0.8, 0.22), (0.7, 0.36), (-0.7, 0.36)), "trim", 0.004, False),
             ("strip", "top", [(1.9, 0.12), (-2.3, 0.12)], 0.12, "accent", 0.003, True),
             ("strip", "left", [(-1.8, 0.33), (1.6, 0.31)], 0.03, "accent", 0.003, True),
             ("roundel", (0.35, 0.5), 0.17),
         ],
         extras=[ex_falcon]),

    dict(id="02", name="DuneFox", doors=[(0.46, 0.64)], name_ar="ثعلب الكثبان", number="2", plate=("2002", "DFX", "دفص"),
         accent_rgb_bg=(200, 90, 20),
         L=5.6, axles=(0.2, 0.775), R=(0.48, 0.48), TW=(0.36, 0.36), rim="beadlock", rim_color=(0.75, 0.75, 0.78),
         tread="offroad", rim_ratio=0.53, arch_gap=0.08, arch_depth=0.3, wheel_inset=0.02,
         paint=(0.86, 0.45, 0.1), metal=0.3, accent=(0.08, 0.08, 0.09), seat=(0.1, 0.1, 0.1),
         zb=[(0, 0.8), (0.06, 0.72), (0.9, 0.7), (1, 0.82)],
         zs=[(0, 1.3), (0.4, 1.33), (0.5, 1.36), (0.62, 1.34), (0.85, 1.3), (0.97, 1.2), (1, 1.1)],
         zt=[(0, 0), (0.42, 1.36), (0.45, 1.88), (0.5, 1.93), (0.56, 1.92), (0.64, 1.6), (0.67, 1.37), (0.7, 0)],
         w=[(0, 0.9), (0.06, 1.05), (0.2, 1.08), (0.35, 1.0), (0.5, 0.95), (0.7, 1.05), (0.78, 1.08),
            (0.92, 1.0), (1, 0.82)],
         wt=[(0, 0.7), (0.5, 0.76), (1, 0.7)],
         cr=[(0, 0.01), (0.5, 0.04), (0.8, 0.04), (1, 0.02)],
         shape=dict(sh=(0.99, 0.95), side=(1.0, 1.0), bulge=0.0), end=(0.85, 0.03),
         side_glass=[(0.455, 0.645)], pillars=[(0.545, 0.56)], roof_glass=[(0.565, 0.67), (0.43, 0.46)],
         rocker="trim", mirror_t=0.62, plate_z=(None, (1.0, -1)), exhaust=[(-0.5, 0.9, 0.06, 0.2)],
         cuts=[((T(1.0), 0.0, 1.085), (0.36, 0.8, 0.27), (0, 0, 0), "grille", False),
               ((T(0.6), 1.12, 1.25), (0.5, 0.2, 0.07), (0, 0, 0), "trim", True)],
         decals=[
             ("quad", "front", ((0.45, 1.05), (0.78, 1.05), (0.78, 1.2), (0.45, 1.2)), "lens", 0.004, True),
             ("disc", "front", (0.53, 1.12), (0.06, 0.06), "head", 0.008, True),
             ("disc", "front", (0.7, 1.12), (0.06, 0.06), "head", 0.008, True),
             ("strip", "front", [(-0.42, 0.93), (0.42, 0.93), (0.42, 1.24), (-0.42, 1.24), (-0.42, 0.93)], 0.03, "trim", 0.004, False),
             ("quad", "rear", ((0.7, 1.05), (0.95, 1.05), (0.95, 1.2), (0.7, 1.2)), "tail", 0.005, True),
             ("strip", "left", [(-2.6, 1.0), (2.6, 1.0)], 0.12, "accent", 0.003, True),
             ("strip", "top", [(2.7, 0.0), (0.4, 0.0)], 0.22, "accent", 0.003, False),
             ("roundel", (-0.1, 1.08), 0.2),
         ],
         extras=[ex_dunefox]),

    dict(id="03", name="NajdiGXR", doors=[(0.445, 0.66), (0.23, 0.44)], name_ar="النجدي", number="3", plate=("3003", "NJD", "نجد"),
         accent_rgb_bg=(170, 130, 60),
         L=4.95, axles=(0.17, 0.745), R=(0.4, 0.4), TW=(0.29, 0.29), rim="steel", rim_color=(0.72, 0.62, 0.38),
         rim_rough=0.3, tread="offroad", rim_ratio=0.56,
         paint=(0.93, 0.92, 0.88), metal=0.35, accent=(0.72, 0.58, 0.32), seat=(0.6, 0.5, 0.38),
         zb=[(0, 0.42), (0.04, 0.36), (0.9, 0.36), (1, 0.44)],
         zs=[(0, 1.12), (0.5, 1.14), (0.66, 1.14), (0.8, 1.12), (0.96, 1.08), (1, 1.0)],
         zt=[(0, 0), (0.01, 1.84), (0.03, 1.89), (0.5, 1.91), (0.6, 1.89), (0.66, 1.42), (0.685, 1.16), (0.7, 0)],
         w=[(0, 0.95), (0.02, 0.98), (0.1, 0.99), (0.9, 0.99), (0.98, 0.95), (1, 0.88)],
         wt=[(0, 0.86), (0.5, 0.88), (1, 0.86)],
         cr=[(0, 0.01), (0.5, 0.03), (0.8, 0.02), (1, 0.01)],
         shape=dict(sh=(1.0, 0.97), side=(1.0, 1.0), bot=(0.7, 0.96), bulge=0.0), end=(0.9, 0.02), stations=80,
         side_glass=[(0.06, 0.665)], pillars=[(0.215, 0.235), (0.43, 0.45)], roof_glass=[(0.625, 0.69)],
         rocker="trim", belt_trim="chrome", mirror_t=0.645, plate_z=((0.6, 1), (0.62, -1)),
         cuts=[((T(1.0), 0.0, 0.9), (0.3, 1.04, 0.24), (0, 0, 0), "grille", False),
               ((T(0.9), 0.0, 1.17), (0.6, 0.6, 0.06), (0, 0, 0), "trim", False)],
         exhaust=[(-0.6, 0.45, 0.04, 0.15)], creases={6: 0.8, 3: 0.5, 10: 0.7},
         decals=[
             ("strip", "front", [(-0.54, 0.77), (0.54, 0.77), (0.54, 1.03), (-0.54, 1.03), (-0.54, 0.77)], 0.04, "chrome", 0.005, False),
             ("strip", "front", [(-0.5, 0.86), (0.5, 0.86)], 0.025, "chrome", 0.005, False),
             ("strip", "front", [(-0.5, 0.94), (0.5, 0.94)], 0.025, "chrome", 0.005, False),
             ("quad", "front", ((0.58, 0.82), (0.92, 0.84), (0.92, 1.02), (0.58, 1.02)), "lens", 0.004, True),
             ("disc", "front", (0.68, 0.92), (0.07, 0.07), "head", 0.008, True),
             ("disc", "front", (0.84, 0.92), (0.06, 0.06), "head", 0.008, True),
             ("strip", "front", [(0.6, 0.835), (0.9, 0.85)], 0.015, "drl", 0.008, True),
             ("quad", "rear", ((-0.9, 1.12), (-0.77, 1.12), (-0.77, 1.58), (-0.9, 1.58)), "tail", 0.005, True),
             ("quad", "rear", ((-0.75, 1.2), (0.75, 1.2), (0.72, 1.82), (-0.72, 1.82)), "glass", 0.004, False),
             ("strip", "left", [(-2.2, 0.82), (2.4, 0.82)], 0.06, "accent", 0.003, True),
             ("strip", "left", [(-2.2, 0.72), (2.4, 0.72)], 0.025, "accent", 0.003, True),
             ("roundel", (0.48, 0.99), 0.15),
         ],
         extras=[ex_najdi]),

    dict(id="04", name="HiluxRaider", doors=[(0.545, 0.65), (0.43, 0.54)], name_ar="الغزّاي", number="4", plate=("4004", "HLX", "حلص"),
         accent_rgb_bg=(170, 20, 30),
         L=5.3, axles=(0.17, 0.745), R=(0.38, 0.38), TW=(0.28, 0.28), rim="y6", rim_color=(0.05, 0.05, 0.055),
         tread="offroad", rim_ratio=0.58, wheel_inset=0.05,
         paint=(0.62, 0.03, 0.04), metal=0.55, accent=(0.07, 0.07, 0.08), seat=(0.12, 0.12, 0.12),
         zb=[(0, 0.42), (0.05, 0.35), (0.9, 0.34), (1, 0.42)],
         zs=[(0, 1.1), (0.4, 1.1), (0.42, 1.08), (0.66, 1.09), (0.85, 1.07), (0.96, 1.0), (1, 0.92)],
         zt=[(0, 0), (0.405, 0), (0.41, 1.7), (0.43, 1.78), (0.6, 1.79), (0.645, 1.52), (0.685, 1.12), (0.7, 0)],
         w=[(0, 0.9), (0.02, 0.93), (0.1, 0.94), (0.9, 0.94), (0.98, 0.9), (1, 0.82)],
         wt=[(0, 0.78), (0.5, 0.8), (1, 0.78)],
         cr=[(0, 0.01), (0.5, 0.03), (0.8, 0.03), (1, 0.01)],
         shape=dict(sh=(0.99, 0.95), side=(0.995, 1.0), bot=(0.65, 0.94), bulge=0.01), end=(0.88, 0.025),
         stations=80,
         side_glass=[(0.43, 0.655)], pillars=[(0.535, 0.55)], roof_glass=[(0.625, 0.69), (0.405, 0.42)],
         rocker="trim", belt_trim="trim", mirror_t=0.645, plate_z=((0.55, 1), (0.6, -1)), creases={6: 0.7, 3: 0.4},
         cuts=[((T(1.0), 0.0, 0.85), (0.3, 1.0, 0.26), (0, 0, 0), "grille", False),
               ((T(1.0), 0.0, 0.5), (0.3, 0.9, 0.14), (0, 0, 0), "grille", False)],
         exhaust=[(-0.62, 0.4, 0.04, 0.15)],
         decals=[
             ("strip", "front", [(-0.53, 0.71), (0.53, 0.71), (0.51, 0.99), (-0.51, 0.99), (-0.53, 0.71)], 0.035, "gloss", 0.005, False),
             ("strip", "front", [(-0.5, 0.85), (0.5, 0.85)], 0.05, "gloss", 0.005, False),
             ("quad", "front", ((0.56, 0.84), (0.9, 0.86), (0.88, 0.99), (0.56, 0.98)), "lens", 0.004, True),
             ("disc", "front", (0.72, 0.92), (0.08, 0.05), "head", 0.008, True),
             ("strip", "front", [(0.58, 0.86), (0.88, 0.88)], 0.014, "drl", 0.008, True),
             ("quad", "rear", ((-0.94, 0.75), (-0.82, 0.75), (-0.82, 1.05), (-0.94, 1.05)), "tail", 0.005, True),
             ("strip", "left", [(-2.4, 0.95), (2.2, 0.95)], 0.08, "accent", 0.003, True),
             ("roundel", (0.25, 0.85), 0.18),
         ],
         extras=[ex_hilux]),

    dict(id="05", name="RiyadhMuscle", doors=[(0.36, 0.615)], name_ar="عضلات الرياض", number="5", plate=("5005", "RYD", "ريد"),
         accent_rgb_bg=(20, 20, 20),
         L=4.75, axles=(0.17, 0.765), R=(0.34, 0.35), TW=(0.25, 0.3), rim="mono", rim_color=(0.86, 0.86, 0.88),
         rim_rough=0.12, tread="road", rim_ratio=0.62,
         paint=(0.75, 0.52, 0.12), metal=0.8, accent=(0.02, 0.02, 0.022), seat=(0.08, 0.08, 0.08),
         zb=[(0, 0.3), (0.05, 0.17), (0.92, 0.16), (1, 0.28)],
         zs=[(0, 0.84), (0.1, 0.87), (0.3, 0.86), (0.6, 0.86), (0.85, 0.85), (0.97, 0.8), (1, 0.7)],
         zt=[(0, 0), (0.04, 0.88), (0.12, 0.98), (0.25, 1.17), (0.38, 1.3), (0.46, 1.31), (0.53, 1.25),
             (0.6, 1.02), (0.63, 0.9), (0.66, 0)],
         w=[(0, 0.9), (0.05, 0.95), (0.18, 0.97), (0.4, 0.95), (0.75, 0.94), (0.95, 0.93), (1, 0.88)],
         wt=[(0, 0.6), (0.4, 0.66), (0.55, 0.66), (1, 0.62)],
         cr=[(0, 0.02), (0.6, 0.03), (1, 0.02)],
         shape=dict(sh=(0.99, 0.94), side=(0.99, 1.0), bulge=0.03), end=(0.88, 0.03),
         side_glass=[(0.33, 0.62)], pillars=[(0.47, 0.485)], roof_glass=[(0.53, 0.64), (0.13, 0.3)],
         roof_black="gloss", belt_trim="chrome", mirror_t=0.6, plate_z=((0.45, 1), (0.62, -1)),
         exhaust=[(0.55, 0.3, 0.05, 0.2), (-0.55, 0.3, 0.05, 0.2)], creases={6: 0.8, 3: 0.4, 10: 0.5},
         cuts=[((T(1.0), 0.0, 0.67), (0.34, 0.98, 0.18), (0, 0, 0), "grille", False)],
         decals=[
             ("strip", "front", [(-0.5, 0.57), (0.5, 0.57), (0.5, 0.77), (-0.5, 0.77), (-0.5, 0.57)], 0.03, "chrome", 0.005, False),
             ("disc", "front", (0.66, 0.67), (0.09, 0.09), "chrome", 0.007, True),
             ("disc", "front", (0.66, 0.67), (0.07, 0.07), "head", 0.009, True),
             ("quad", "rear", ((-0.85, 0.6), (0.85, 0.6), (0.85, 0.76), (-0.85, 0.76)), "chrome", 0.004, False),
             ("quad", "rear", ((-0.82, 0.62), (-0.1, 0.62), (-0.1, 0.74), (-0.82, 0.74)), "tail", 0.006, True),
             ("strip", "top", [(2.4, 0.2), (-2.4, 0.2)], 0.18, "accent", 0.003, True),
             ("strip", "left", [(-1.8, 0.45), (1.9, 0.45)], 0.05, "accent", 0.003, True),
             ("roundel", (0.0, 0.62), 0.19),
         ],
         extras=[ex_muscle]),

    dict(id="06", name="NeomGlide", doors=[(0.36, 0.7)], name_ar="نيوم", number="6", plate=("6006", "NEO", "نيو"),
         accent_rgb_bg=(10, 120, 140),
         L=4.85, axles=(0.18, 0.78), R=(0.36, 0.36), TW=(0.27, 0.3), rim="turbine", rim_color=(0.9, 0.9, 0.92),
         tread="slick", rim_ratio=0.7, rear_skirts=True, glow=(0.15, 0.95, 1.0),
         paint=(0.93, 0.94, 0.95), metal=0.2, accent=(0.02, 0.05, 0.08), seat=(0.9, 0.9, 0.9),
         zb=[(0, 0.3), (0.06, 0.15), (0.9, 0.14), (1, 0.24)],
         zs=[(0, 0.8), (0.1, 0.86), (0.25, 0.86), (0.5, 0.78), (0.75, 0.74), (0.86, 0.68), (0.95, 0.56),
             (1, 0.44)],
         zt=[(0, 0), (0.05, 0.84), (0.15, 0.95), (0.3, 1.08), (0.45, 1.15), (0.55, 1.12), (0.66, 0.98),
             (0.76, 0.78), (0.8, 0)],
         w=[(0, 0.85), (0.06, 0.95), (0.2, 1.0), (0.4, 0.97), (0.6, 0.96), (0.8, 1.0), (0.93, 0.95), (1, 0.7)],
         wt=[(0, 0.4), (0.3, 0.62), (0.5, 0.66), (0.7, 0.6), (1, 0.4)],
         cr=[(0, 0.03), (0.5, 0.05), (1, 0.04)],
         shape=dict(sh=(0.95, 0.86), side=(0.98, 1.0), bulge=0.06), end=(0.75, 0.05),
         side_glass=[(0.2, 0.75)], roof_glass=[(0.12, 0.78)], rocker="accent", mirror_t=None,
         plate_z=(None, (0.45, -1)), exhaust=[], creases={6: 0.3},
         cuts=[((T(1.0), 0.0, 0.27), (0.4, 1.1, 0.13), (0, 0, 0), "grille", False),
               ((T(0.0), 0.0, 0.3), (0.3, 1.2, 0.12), (0, 0, 0), "glow", False)],
         decals=[
             ("strip", "front", [(-0.9, 0.5), (0.9, 0.5)], 0.03, "glow", 0.007, False),
             ("quad", ("front", 30, 2.2), ((0.3, 0.52), (0.82, 0.56), (0.8, 0.6), (0.34, 0.565)), "glow", 0.006, True),
             ("strip", "rear", [(-0.86, 0.72), (0.86, 0.72)], 0.03, "tail", 0.007, False),
             ("strip", "left", [(-2.35, 0.78), (2.3, 0.6)], 0.018, "glow", 0.004, True),
             ("strip", "left", [(-2.0, 0.3), (2.0, 0.28)], 0.12, "accent", 0.003, True),
             ("roundel", (-0.95, 0.55), 0.16),
         ],
         extras=[ex_neom]),

    dict(id="07", name="AlUlaRally", doors=[(0.415, 0.675), (0.185, 0.41)], name_ar="رالي العُلا", number="7", plate=("7007", "ULA", "علا"),
         accent_rgb_bg=(240, 240, 235),
         L=4.2, axles=(0.15, 0.81), R=(0.33, 0.33), TW=(0.25, 0.25), rim="multi", rim_color=(0.95, 0.95, 0.95),
         rim_metal=False, tread="rally", rim_ratio=0.64, arch_gap=0.06,
         paint=(0.78, 0.33, 0.12), metal=0.45, accent=(0.95, 0.95, 0.93), seat=(0.1, 0.1, 0.1),
         zb=[(0, 0.32), (0.05, 0.22), (0.92, 0.21), (1, 0.32)],
         zs=[(0, 0.98), (0.1, 0.96), (0.5, 0.95), (0.7, 0.93), (0.9, 0.86), (0.98, 0.78), (1, 0.68)],
         zt=[(0, 0), (0.01, 1.3), (0.04, 1.38), (0.12, 1.42), (0.45, 1.44), (0.55, 1.38), (0.66, 1.1),
             (0.7, 0.98), (0.72, 0)],
         w=[(0, 0.9), (0.05, 0.94), (0.15, 0.96), (0.5, 0.92), (0.81, 0.95), (0.95, 0.9), (1, 0.8)],
         wt=[(0, 0.68), (0.4, 0.7), (1, 0.66)],
         cr=[(0, 0.02), (0.5, 0.04), (1, 0.03)],
         shape=dict(sh=(0.98, 0.9), side=(0.99, 1.0), bulge=0.03), end=(0.85, 0.035),
         side_glass=[(0.06, 0.68)], pillars=[(0.17, 0.19), (0.4, 0.42)], roof_glass=[(0.57, 0.71)],
         rocker="trim", mirror_t=0.66, plate_z=((0.3, 1), (0.6, -1)), exhaust=[(-0.5, 0.32, 0.05, 0.2)],
         cuts=[((T(1.0), 0.0, 0.5), (0.34, 0.86, 0.16), (0, 0, 0), "grille", False),
               ((T(1.0), 0.62, 0.36), (0.34, 0.26, 0.12), (0, 0, 0), "grille", True),
               ((T(0.88), 0.0, 0.9), (0.24, 0.5, 0.05), (0, 0, 0), "trim", False)],
         decals=[
             ("quad", "front", ((0.48, 0.66), (0.86, 0.68), (0.84, 0.8), (0.5, 0.78)), "lens", 0.004, True),
             ("disc", "front", (0.62, 0.72), (0.06, 0.045), "head", 0.008, True),
             ("strip", "front", [(-0.44, 0.6), (0.44, 0.6)], 0.03, "accent", 0.005, False),
             ("quad", "rear", ((-0.88, 0.85), (-0.66, 0.85), (-0.66, 1.0), (-0.88, 0.98)), "tail", 0.005, True),
             ("quad", "rear", ((-0.6, 1.05), (0.6, 1.05), (0.55, 1.36), (-0.55, 1.36)), "glass", 0.004, False),
             ("strip", "left", [(-2.1, 0.62), (-0.6, 0.62), (0.4, 0.92), (2.1, 0.92)], 0.16, "accent", 0.003, True),
             ("strip", "top", [(1.8, 0.0), (-1.4, 0.0)], 0.3, "accent", 0.003, False),
             ("roundel", (0.05, 0.62), 0.18),
         ],
         extras=[ex_rally]),

    dict(id="08", name="JeddahGT", doors=[(0.335, 0.585)], name_ar="جدة جي تي", number="8", plate=("8008", "JED", "جدة"),
         accent_rgb_bg=(10, 50, 90),
         L=4.75, axles=(0.18, 0.79), R=(0.35, 0.355), TW=(0.26, 0.3), rim="mesh", rim_color=(0.7, 0.7, 0.72),
         rim_rough=0.2, tread="road", rim_ratio=0.68,
         paint=(0.02, 0.18, 0.32), metal=0.85, accent=(0.85, 0.72, 0.42), seat=(0.75, 0.62, 0.45),
         zb=[(0, 0.24), (0.05, 0.14), (0.92, 0.13), (1, 0.2)],
         zs=[(0, 0.83), (0.06, 0.88), (0.2, 0.87), (0.4, 0.82), (0.6, 0.8), (0.8, 0.8), (0.92, 0.72),
             (1, 0.55)],
         zt=[(0, 0), (0.06, 0.88), (0.14, 0.97), (0.26, 1.15), (0.36, 1.27), (0.44, 1.28), (0.5, 1.22),
             (0.56, 1.03), (0.6, 0.86), (0.63, 0)],
         w=[(0, 0.86), (0.05, 0.95), (0.18, 0.99), (0.32, 0.96), (0.55, 0.92), (0.78, 0.96), (0.92, 0.92),
            (1, 0.72)],
         wt=[(0, 0.5), (0.3, 0.6), (0.45, 0.63), (0.6, 0.6), (1, 0.55)],
         cr=[(0, 0.03), (0.5, 0.04), (0.8, 0.05), (1, 0.03)],
         shape=dict(sh=(0.965, 0.89), side=(0.985, 1.0), bulge=0.04), end=(0.8, 0.04),
         side_glass=[(0.3, 0.585)], pillars=[], roof_glass=[(0.5, 0.62), (0.16, 0.33)], belt_trim="chrome",
         mirror_t=0.57, plate_z=((0.18, 1), (0.52, -1)),
         cuts=[((T(1.0), 0.0, 0.37), (0.34, 0.92, 0.24), (0, 0, 0), "grille", False),
               ((T(0.0), 0.0, 0.22), (0.3, 1.3, 0.1), (0, 0, 0), "grille", False)],
         exhaust=[(0.42, 0.26, 0.04, 0.2), (0.32, 0.26, 0.04, 0.2), (-0.42, 0.26, 0.04, 0.2),
                  (-0.32, 0.26, 0.04, 0.2)],
         decals=[
             ("strip", "front", [(-0.44, 0.24), (0.44, 0.24), (0.5, 0.5), (-0.5, 0.5), (-0.44, 0.24)], 0.025, "chrome", 0.004, False),
             ("quad", ("front", 30, 2.1), ((0.5, 0.56), (0.86, 0.64), (0.84, 0.72), (0.53, 0.65)), "lens", 0.004, True),
             ("strip", ("front", 30, 2.1), [(0.53, 0.635), (0.84, 0.705)], 0.02, "drl", 0.007, True),
             ("disc", ("front", 30, 2.1), (0.68, 0.645), (0.05, 0.03), "chrome", 0.006, True),
             ("disc", ("front", 30, 2.1), (0.68, 0.645), (0.038, 0.022), "head", 0.008, True),
             ("strip", "rear", [(-0.84, 0.74), (0.84, 0.74)], 0.03, "tail", 0.006, False),
             ("strip", "left", [(-1.9, 0.68), (1.9, 0.7)], 0.012, "accent", 0.003, True),
             ("roundel", (-0.1, 0.55), 0.16),
         ],
         extras=[ex_gt]),
]


def build_car(spec, render=True, export=True):
    sr.reset()
    car = Car(spec)
    body, wheels = car.build()
    print(f"{spec['name']}: body tris {sr.tri_count(body)}, wheel tris {sr.tri_count(wheels['FL'])}")
    if render:
        render_car(car, body, wheels)
    if export:
        rig_and_export(car, body, wheels)
    sr.write_manifest()
    return car


# ------------------------------------------------------- Chaos vehicle data ---
CLASS_TUNING = {   # arcade-leaning starting points per car (mass kg, torque Nm, max rpm, susp travel cm, drive)
    "Falcon": (1350, 720, 8500, 8, "AWD"), "DuneFox": (2200, 900, 6500, 35, "AWD"),
    "NajdiGXR": (2400, 650, 6000, 20, "AWD"), "HiluxRaider": (2000, 600, 6000, 18, "RWD"),
    "RiyadhMuscle": (1600, 800, 7000, 10, "RWD"), "NeomGlide": (1500, 850, 12000, 8, "AWD"),
    "AlUlaRally": (1250, 520, 8000, 16, "AWD"), "JeddahGT": (1650, 760, 7800, 9, "RWD"),
}


def vehicle_spec(spec):
    """Wheel/axle data in Unreal units (cm, X forward, Y right) for the Chaos Wheeled Vehicle component."""
    L = spec["L"]
    tr, tf = spec["axles"]
    tm = (tr + tf) / 2
    wc = curve(spec["w"])
    mass, torque, rpm, travel, drive = CLASS_TUNING.get(spec["name"], (1500, 600, 7000, 10, "AWD"))
    wheels = {}
    for key, front, side in (("FL", True, -1), ("FR", True, 1), ("RL", False, -1), ("RR", False, 1)):
        t = tf if front else tr
        R = spec["R"][0 if front else 1]
        TW = spec["TW"][0 if front else 1]
        y = wc(t) - TW / 2 - spec.get("wheel_inset", 0.04)
        wheels[f"Wheel_{key}"] = dict(bone=f"Wheel_{key}", x_cm=round((t - tm) * L * 100, 1), y_cm=round(side * y * 100, 1),
                                      z_cm=round(R * 100, 1), radius_cm=round(R * 100, 1), width_cm=round(TW * 100, 1),
                                      steer=front, max_steer_deg=40 if front else 0,
                                      driven=(drive == "AWD") or (drive == "RWD" and not front))
    return dict(car=spec["name"], name_ar=spec["name_ar"], number=spec["number"], skeletal_mesh=f"SK_{spec['name']}",
                root_bone="Root", length_cm=round(L * 100), wheelbase_cm=round((tf - tr) * L * 100, 1),
                track_front_cm=round(2 * abs(wheels["Wheel_FL"]["y_cm"]), 1), track_rear_cm=round(2 * abs(wheels["Wheel_RL"]["y_cm"]), 1),
                mass_kg=mass, max_torque_nm=torque, max_rpm=rpm, drive=drive, suspension_travel_cm=travel,
                center_of_mass_offset_cm=dict(x=0, y=0, z=-15), wheels=wheels,
                notes="Bones are in the skeletal mesh. Physics asset: keep only the Root body (delete wheel bodies).")


def write_vehicle_specs():
    import json
    allspecs = {}
    for spec in CARS:
        vs = vehicle_spec(spec)
        allspecs[spec["name"]] = vs
        os.makedirs(os.path.join(OUT, spec["name"]), exist_ok=True)
        with open(os.path.join(OUT, spec["name"], "vehicle_spec.json"), "w") as f:
            json.dump(vs, f, indent=1, ensure_ascii=False)
    with open(os.path.join(OUT, "vehicle_specs.json"), "w") as f:
        json.dump(allspecs, f, indent=1, ensure_ascii=False)
    print("wrote vehicle specs")


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    names = [a for a in argv if not a.startswith("-")]
    render = "--no-render" not in argv
    export = "--no-export" not in argv
    for spec in CARS:
        if names and spec["name"] not in names:
            continue
        build_car(spec, render, export)
    write_vehicle_specs()
