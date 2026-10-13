"""Sahara Racers - map backdrops: scenery from the edge of the 2 km play area to the horizon.

Backdrop terrain
    A ring mesh around the map (out to ~24 km). Its inner edge matches the real terrain exactly (and
    tucks 36 m under it so there is never a crack), then blends into a per-map `far(X, Y)` height field:
    the map's own landscape continued, plus distant mountain ranges / sea / plateaus. Vertex colours
    carry the same 4-layer blend as the map terrain, so it uses the same material.
    Rings get coarser with distance (14 m at the edge, ~1.5 km at the horizon): ~150k triangles.

Distant detail
    `Merged` builds many tiny, low-poly instances (city blocks, towers, trees, palms) into a few chunk
    meshes - far cheaper than thousands of actors, and Nanite-friendly in Unreal.
"""
import math
import os
import random

import numpy as np

from terrain import blur, smoothstep


def ring_coords(half=1008.0, inner_step=14.0, first=14.0, growth=1.07, outer=24000.0):
    inner = np.linspace(-half, half, int(round(2 * half / inner_step)) + 1)
    out, d, s = [], 0.0, first
    while half + d < outer:
        d += s
        out.append(half + d)
        s *= growth
    out = np.array(out)
    return np.concatenate([-out[::-1], inner, out])


class Backdrop:
    def __init__(self, terrain, far, paint=None, blend=600.0, margin=36.0, **ring):
        """far(X, Y) -> heights; paint(X, Y, H, slope, dist) -> (4, ...) weights or None."""
        self.t = terrain
        self.half = terrain.size / 2
        self.margin = margin
        xs = ring_coords(self.half, **ring)
        self.xs = xs
        X, Y = np.meshgrid(xs, xs)
        self.X, self.Y = X, Y
        dx = np.maximum(np.abs(X) - self.half, 0)
        dy = np.maximum(np.abs(Y) - self.half, 0)
        d = np.hypot(dx, dy)
        self.dist = d
        ex, ey = np.clip(X, -self.half, self.half), np.clip(Y, -self.half, self.half)
        h_exact = terrain.sample(ex, ey)
        h_soft = terrain.sample(ex, ey, h=blur(terrain.h, 20))
        he = h_exact + (h_soft - h_exact) * smoothstep(0, 80, d)
        inside = d <= 0
        he = np.where(inside, terrain.sample(X, Y) - 0.6, he)
        F = far(X, Y)
        s = smoothstep(0, blend, d)
        self.H = he * (1 - s) + F * s
        # layer weights: the map's own weights at the edge, blending into the backdrop paint
        n = terrain.n
        ii = np.clip(((ex + self.half) / terrain.res).round().astype(int), 0, n - 1)
        jj = np.clip(((ey + self.half) / terrain.res).round().astype(int), 0, n - 1)
        w_edge = terrain.w[:, jj, ii]
        gy, gx = np.gradient(self.H, xs, xs)
        slope = np.hypot(gx, gy)
        w_far = paint(X, Y, self.H, slope, d) if paint else None
        if w_far is None:
            w_far = np.zeros_like(w_edge)
            w_far[0] = 1
        w_far = np.asarray(w_far, float)
        w_far = w_far / np.maximum(w_far.sum(0), 1e-6)
        self.W = w_edge * (1 - s) + w_far * s

    def mesh_object(self, name, material=None):
        import bpy
        xs = self.xs
        N = len(xs)
        verts = np.stack([self.X, self.Y, self.H], -1).reshape(-1, 3)
        idx = np.arange(N * N).reshape(N, N)
        a, b = idx[:-1, :-1], idx[:-1, 1:]
        c, d_ = idx[1:, 1:], idx[1:, :-1]
        quads = np.stack([a, b, c, d_], -1).reshape(-1, 4)
        lim = self.half - self.margin
        cx = 0.5 * (xs[:-1] + xs[1:])
        CX, CY = np.meshgrid(cx, cx)
        keep = ~((np.abs(CX) < lim) & (np.abs(CY) < lim)).reshape(-1)
        quads = quads[keep]
        me = bpy.data.meshes.new(name)
        me.from_pydata(verts.tolist(), [], quads.tolist())
        me.update()
        uv = me.uv_layers.new(name="UVMap")
        loop_vi = np.zeros(len(me.loops), dtype=np.int64)
        me.loops.foreach_get("vertex_index", loop_vi)
        uv.data.foreach_set("uv", verts[loop_vi][:, :2].ravel())
        from terrain import Terrain
        mf = Terrain.mix_factors(None, self.W.reshape(self.W.shape[0], -1)).reshape(-1, 3)
        col = me.color_attributes.new("Weights", "FLOAT_COLOR", "POINT")
        col.data.foreach_set("color", np.concatenate([mf, np.ones((len(mf), 1))], 1).ravel())
        me.color_attributes.active_color = col
        me.color_attributes.render_color_index = me.color_attributes.active_color_index
        for p in me.polygons:
            p.use_smooth = True
        if material:
            me.materials.append(material)
        ob = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(ob)
        return ob

    def height(self, x, y):
        """Backdrop height at points (bilinear on the non-uniform grid)."""
        from scipy.interpolate import RegularGridInterpolator
        f = RegularGridInterpolator((self.xs, self.xs), self.H, bounds_error=False, fill_value=None)
        return f(np.stack([np.asarray(y, float), np.asarray(x, float)], -1))

    def slope(self, x, y):
        from scipy.interpolate import RegularGridInterpolator
        gy, gx = np.gradient(self.H, self.xs, self.xs)
        f = RegularGridInterpolator((self.xs, self.xs), np.hypot(gx, gy), bounds_error=False, fill_value=None)
        return f(np.stack([np.asarray(y, float), np.asarray(x, float)], -1))


# ----------------------------------------------------------- merged detail ---
class Merged:
    """Collect low-poly instances and bake them into a few chunk meshes (SM_<Map>_Far_<name>_<k>)."""

    def __init__(self, name, chunks=4):
        import sr
        self.name = name
        self.chunks = chunks
        self.mbs = {}
        self.sr = sr

    def _mb(self, x, y):
        k = (0 if x < 0 else 1) + (0 if y < 0 else 2) if self.chunks == 4 else 0
        if k not in self.mbs:
            self.mbs[k] = self.sr.MB(f"{self.name}_{k + 1}")
        return self.mbs[k]

    def objects(self):
        return [mb.to_object(origin="keep", sharp_angle=40) for k, mb in sorted(self.mbs.items())]

    # ---- generators -------------------------------------------------------
    def block(self, x, y, z, w, d, h, yaw, wall, roof=None, crown=None):
        mb = self._mb(x, y)
        mb.box((w, d, h), (x, y, z + h / 2 - 1.0), (0, 0, yaw), m=wall)
        if roof is not None:
            mb.box((w * 0.92, d * 0.92, 0.6), (x, y, z + h - 0.7), (0, 0, yaw), m=roof)
        if crown is not None and h > 30:
            mb.box((w * 0.5, d * 0.5, 4.0), (x, y, z + h + 1.0), (0, 0, yaw), m=crown)

    def tower(self, x, y, z, r, h, wall, cap=None, seg=8, taper=0.75):
        mb = self._mb(x, y)
        mb.cyl(r, h, (x, y, z + h / 2 - 1.0), m=wall, seg=seg, r2=r * taper)
        if cap is not None:
            mb.cyl(r * taper * 0.4, h * 0.12, (x, y, z + h * 1.05), m=cap, seg=seg, r2=0.2)

    def tree(self, x, y, z, h, foliage, trunk=None, kind="cone"):
        mb = self._mb(x, y)
        if trunk is not None:
            mb.cyl(0.25 * h / 7, h * 0.35, (x, y, z + h * 0.15), m=trunk, seg=5)
        if kind == "cone":
            mb.cyl(h * 0.32, h * 0.8, (x, y, z + h * 0.6), m=foliage, seg=6, r2=0.05)
        else:   # round crown (acacia / sidr / far broadleaf)
            mb.sphere(h * 0.35, (x, y, z + h * 0.72), m=foliage, seg=6, rings=3, scale=(1.3, 1.3, 0.55))

    def palm(self, x, y, z, h, trunk, frond, rnd):
        mb = self._mb(x, y)
        lean = rnd.uniform(-0.6, 0.6), rnd.uniform(-0.6, 0.6)
        top = (x + lean[0], y + lean[1], z + h)
        mb.tube([(x, y, z - 0.5), top], 0.22, trunk, seg=5, caps=False)
        for k in range(6):
            a = 2 * math.pi * k / 6 + rnd.uniform(0, 0.5)
            tip = (top[0] + 3.2 * math.cos(a), top[1] + 3.2 * math.sin(a), top[2] - 1.2)
            mid = (top[0] + 1.6 * math.cos(a), top[1] + 1.6 * math.sin(a), top[2] + 0.4)
            p = (math.cos(a + math.pi / 2) * 0.45, math.sin(a + math.pi / 2) * 0.45)
            mb.poly_facing([(top[0] + p[0], top[1] + p[1], top[2]), (top[0] - p[0], top[1] - p[1], top[2]),
                            (mid[0] - p[0], mid[1] - p[1], mid[2]), (mid[0] + p[0], mid[1] + p[1], mid[2])], (0, 0, 1), frond)
            mb.poly_facing([(mid[0] + p[0], mid[1] + p[1], mid[2]), (mid[0] - p[0], mid[1] - p[1], mid[2]), tip], (0, 0, 1), frond)


def scatter_points(rnd, n, accept, bounds, tries=40):
    """Rejection-sample up to n points (x, y) within bounds where accept(x, y) is True."""
    x0, x1, y0, y1 = bounds
    out = []
    for _ in range(n * tries):
        if len(out) >= n:
            break
        x, y = rnd.uniform(x0, x1), rnd.uniform(y0, y1)
        if accept(x, y):
            out.append((x, y))
    return out


def outside(x, y, half=1008.0, pad=40.0):
    return abs(x) > half + pad or abs(y) > half + pad
