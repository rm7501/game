"""Sahara Racers - heightfield terrain (numpy).

Terrain = a square heightfield (default 2016 m, 1 m per sample = UE Landscape 2017x2017) with up to
four material layers (weights 0..1). Generated procedurally per map, carved by the tracks, then
exported three ways:
  * UE Landscape: 16-bit heightmap PNG + 8-bit weight PNGs + landscape.json (location/scale numbers)
  * Nanite terrain mesh tiles (FBX) with vertex-colour layer blend (one-click path)
  * preview mesh for Blender renders
Coordinates: metres, Blender frame (x east, y north, z up). Array row j = y, column i = x.
"""
import json
import math
import os

import numpy as np

try:
    from scipy.spatial import cKDTree
except ImportError:          # Blender's bundled Python has no scipy
    cKDTree = None


# ------------------------------------------------------------------- noise ---
class Noise:
    """Vectorised 2D value noise with quintic fade (arbitrary sample coordinates)."""

    def __init__(self, seed=0, size=512):
        self.g = np.random.default_rng(seed).random((size, size))
        self.n = size

    def __call__(self, x, y):
        n = self.n
        xi = np.floor(x).astype(np.int64)
        yi = np.floor(y).astype(np.int64)
        fx, fy = x - xi, y - yi
        u = fx * fx * fx * (fx * (fx * 6 - 15) + 10)
        v = fy * fy * fy * (fy * (fy * 6 - 15) + 10)
        x0, x1, y0, y1 = xi % n, (xi + 1) % n, yi % n, (yi + 1) % n
        g = self.g
        a, b, c, d = g[y0, x0], g[y0, x1], g[y1, x0], g[y1, x1]
        return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v

    def fbm(self, x, y, scale=200.0, octaves=5, gain=0.5, lac=2.0):
        tot, amp, norm = 0.0, 1.0, 0.0
        f = 1.0 / scale
        for o in range(octaves):
            tot = tot + self(x * f + o * 17.3, y * f - o * 9.1) * amp
            norm += amp
            amp *= gain
            f *= lac
        return tot / norm

    def ridged(self, x, y, scale=300.0, octaves=5, gain=0.5, lac=2.0):
        tot, amp, norm = 0.0, 1.0, 0.0
        f = 1.0 / scale
        for o in range(octaves):
            r = 1.0 - np.abs(self(x * f + o * 31.7, y * f + o * 7.7) * 2 - 1)
            tot = tot + r * r * amp
            norm += amp
            amp *= gain
            f *= lac
        return tot / norm


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def blur(a, radius):
    """Separable box-blur x3 (~gaussian) with edge clamping."""
    r = int(max(1, radius))
    out = a.astype(np.float64)
    for _ in range(3):
        for axis in (0, 1):
            pad = [(0, 0), (0, 0)]
            pad[axis] = (r, r)
            p = np.pad(out, pad, mode="edge")
            c = np.cumsum(p, axis=axis)
            c = np.concatenate([np.zeros_like(c.take([0], axis=axis)), c], axis=axis)
            hi = c.take(np.arange(2 * r + 1, c.shape[axis]), axis=axis)
            lo = c.take(np.arange(0, c.shape[axis] - 2 * r - 1), axis=axis)
            out = (hi - lo) / (2 * r + 1)
    return out


def dist_to_polyline(X, Y, pts):
    """Distance from grid points to a 2D polyline (vectorised over the grid, loop over segments)."""
    d = np.full(X.shape, np.inf)
    for (ax, ay), (bx, by) in zip(pts[:-1], pts[1:]):
        vx, vy = bx - ax, by - ay
        L2 = vx * vx + vy * vy or 1e-9
        t = np.clip(((X - ax) * vx + (Y - ay) * vy) / L2, 0, 1)
        dx, dy = X - (ax + t * vx), Y - (ay + t * vy)
        d = np.minimum(d, np.sqrt(dx * dx + dy * dy))
    return d


# ----------------------------------------------------------------- terrain ---
class Terrain:
    def __init__(self, size=2016.0, n=2017, layers=("L0", "L1", "L2", "L3")):
        self.size = float(size)
        self.n = int(n)
        self.res = self.size / (self.n - 1)
        lin = np.linspace(-self.size / 2, self.size / 2, self.n)
        self.X, self.Y = np.meshgrid(lin, lin)
        self.h = np.zeros((self.n, self.n))
        self.layer_names = list(layers)
        self.w = np.zeros((len(layers), self.n, self.n))
        self.w[0] = 1.0
        self.holes = np.zeros((self.n, self.n), dtype=bool)
        self.water_level = None

    # -- sampling ---------------------------------------------------------
    def sample(self, x, y, h=None):
        h = self.h if h is None else h
        fx = (np.asarray(x) + self.size / 2) / self.res
        fy = (np.asarray(y) + self.size / 2) / self.res
        i0 = np.clip(np.floor(fx).astype(int), 0, self.n - 2)
        j0 = np.clip(np.floor(fy).astype(int), 0, self.n - 2)
        tx, ty = np.clip(fx - i0, 0, 1), np.clip(fy - j0, 0, 1)
        a, b = h[j0, i0], h[j0, i0 + 1]
        c, d = h[j0 + 1, i0], h[j0 + 1, i0 + 1]
        return (a * (1 - tx) + b * tx) * (1 - ty) + (c * (1 - tx) + d * tx) * ty

    def slope(self):
        gy, gx = np.gradient(self.h, self.res)
        return np.sqrt(gx * gx + gy * gy)

    def set_layer(self, idx, weight):
        """Paint layer idx with weight (0..1) on top of the existing layers."""
        weight = np.clip(weight, 0, 1)
        for k in range(len(self.w)):
            if k != idx:
                self.w[k] *= (1 - weight)
        self.w[idx] = self.w[idx] * (1 - weight) + weight
        s = self.w.sum(0)
        s[s == 0] = 1
        self.w /= s

    # -- carving -----------------------------------------------------------
    def carve(self, pts, z, hw, falloff=18.0, depth=0.35, layer=None, layer_width=4.0):
        """Flatten the terrain under road samples: pts (M,2), z (M,), hw half-width incl. shoulder (M,).
        Blends back to the original ground over `falloff` metres (cuttings and embankments)."""
        if len(pts) == 0:
            return
        reach = float(np.max(hw)) + falloff
        lo = pts.min(0) - reach
        hi = pts.max(0) + reach
        i0 = max(0, int((lo[0] + self.size / 2) / self.res))
        i1 = min(self.n, int((hi[0] + self.size / 2) / self.res) + 2)
        j0 = max(0, int((lo[1] + self.size / 2) / self.res))
        j1 = min(self.n, int((hi[1] + self.size / 2) / self.res) + 2)
        Xs, Ys = self.X[j0:j1, i0:i1], self.Y[j0:j1, i0:i1]
        q = np.c_[Xs.ravel(), Ys.ravel()]
        if cKDTree is not None:
            d, idx = cKDTree(pts).query(q, distance_upper_bound=reach)
        else:                               # slow fallback (Blender Python)
            from mathutils.kdtree import KDTree
            kd = KDTree(len(pts))
            for k, p in enumerate(pts):
                kd.insert((p[0], p[1], 0.0), k)
            kd.balance()
            d = np.full(len(q), np.inf)
            idx = np.zeros(len(q), dtype=int)
            for k, (x, y) in enumerate(q):
                co, ii, dist = kd.find((x, y, 0.0))
                if dist <= reach:
                    d[k], idx[k] = dist, ii
        ok = np.isfinite(d)
        d, idx = d[ok], idx[ok]
        H = self.h[j0:j1, i0:i1].ravel()
        target = z[idx] - depth
        t = np.clip((d - hw[idx]) / falloff, 0, 1)
        s = t * t * (3 - 2 * t)
        H[ok] = target * (1 - s) + H[ok] * s
        self.h[j0:j1, i0:i1] = H.reshape(Xs.shape)
        if layer is not None:
            wgt = np.zeros(len(q))
            wgt[ok] = 1 - np.clip((d - hw[idx]) / layer_width, 0, 1)
            full = np.zeros((self.n, self.n))
            full[j0:j1, i0:i1] = wgt.reshape(Xs.shape)
            self.set_layer(layer, full)

    # -- exports ------------------------------------------------------------
    def export_landscape(self, folder, name, zscale=None):
        """UE Landscape import set: 16-bit heightmap, layer weights, numbers in landscape.json."""
        from PIL import Image
        os.makedirs(folder, exist_ok=True)
        hmin, hmax = float(self.h.min()), float(self.h.max())
        extent = max(abs(hmin), abs(hmax), 1.0)
        # UE: height_cm = (v - 32768) * ZScale / 128   ->   ZScale so that +-extent fits in +-32767
        zs = zscale or math.ceil(extent * 100 * 128 / 32000.0)
        v = np.clip(np.round(32768 + self.h * 100 * 128 / zs), 0, 65535).astype(np.uint16)
        v = np.flipud(v)                         # image row 0 = north (+y) = UE -Y edge
        Image.fromarray(v).save(os.path.join(folder, f"H_{name}.png"))
        for k, ln in enumerate(self.layer_names):
            w8 = (np.flipud(self.w[k]) * 255 + 0.5).astype(np.uint8)
            Image.fromarray(w8).save(os.path.join(folder, f"W_{name}_{ln}.png"), optimize=True)
        if self.holes.any():
            Image.fromarray((np.flipud(self.holes) * 255).astype(np.uint8)).save(os.path.join(folder, f"W_{name}_Holes.png"))
        info = dict(heightmap=f"H_{name}.png", resolution=self.n, size_m=self.size,
                    ue_location_cm=[-self.size / 2 * 100, -self.size / 2 * 100, 0.0],
                    ue_scale=[self.res * 100, self.res * 100, zs], layers=self.layer_names,
                    weightmaps=[f"W_{name}_{ln}.png" for ln in self.layer_names],
                    height_range_m=[hmin, hmax], water_level_m=self.water_level,
                    note="Landscape mode > New > Import from File. Use the location/scale above exactly.")
        with open(os.path.join(folder, "landscape.json"), "w") as f:
            json.dump(info, f, indent=1)
        return info

    def mix_factors(self, w):
        """Convert 4 normalised weights into 3 sequential lerp factors (vertex colour RGB)."""
        w0, w1, w2, w3 = (w[k] if k < len(w) else 0 for k in range(4))
        f1 = w1 / np.maximum(w0 + w1, 1e-6)
        f2 = w2 / np.maximum(w0 + w1 + w2, 1e-6)
        f3 = w3
        return np.stack([f1, f2, f3], -1)

    def mesh_object(self, name, step=4, region=None, material=None, skirt=0.0, cut_holes=True):
        """Build a Blender mesh from the heightfield (every `step` samples).
        region = (i0, i1, j0, j1) sample index window. Vertex colour 'Weights' = lerp factors."""
        import bpy
        i0, i1, j0, j1 = region or (0, self.n, 0, self.n)
        ii = np.arange(i0, i1, step)
        if ii[-1] != i1 - 1:
            ii = np.append(ii, i1 - 1)
        jj = np.arange(j0, j1, step)
        if jj[-1] != j1 - 1:
            jj = np.append(jj, j1 - 1)
        J, I = np.meshgrid(jj, ii, indexing="ij")
        xs, ys, zs = self.X[J, I], self.Y[J, I], self.h[J, I]
        nj, ni = J.shape
        verts = np.stack([xs, ys, zs], -1).reshape(-1, 3)
        a = (np.arange(nj - 1)[:, None] * ni + np.arange(ni - 1)[None, :]).ravel()
        faces = np.stack([a, a + 1, a + ni + 1, a + ni], -1)
        if cut_holes and self.holes.any():
            hole = self.holes[J, I]
            hq = (hole[:-1, :-1] | hole[:-1, 1:] | hole[1:, :-1] | hole[1:, 1:]).ravel()
            faces = faces[~hq]
        me = bpy.data.meshes.new(name)
        me.from_pydata(verts.tolist(), [], faces.tolist())
        me.update()
        # UVs in metres (Unreal / Blender scale them per layer)
        uv = me.uv_layers.new(name="UVMap")
        loop_vi = np.zeros(len(me.loops), dtype=np.int64)
        me.loops.foreach_get("vertex_index", loop_vi)
        uvs = verts[loop_vi][:, :2]
        uv.data.foreach_set("uv", uvs.ravel())
        # layer blend factors as a point colour attribute
        mf = self.mix_factors(self.w[:, J, I]).reshape(-1, 3)
        col = me.color_attributes.new("Weights", "FLOAT_COLOR", "POINT")
        rgba = np.concatenate([mf, np.ones((len(mf), 1))], 1)
        col.data.foreach_set("color", rgba.ravel())
        for p in me.polygons:
            p.use_smooth = True
        if material:
            me.materials.append(material)
        ob = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(ob)
        return ob

    def export_tiles(self, folder, name, tiles=4, step=6, material=None):
        """Nanite-ready terrain mesh tiles: SM_<name>_Terrain_<row>_<col>.fbx (origin = world origin)."""
        import sr
        os.makedirs(folder, exist_ok=True)
        edges = np.linspace(0, self.n - 1, tiles + 1).astype(int)
        objs = []
        for r in range(tiles):
            for c in range(tiles):
                region = (edges[c], edges[c + 1] + 1, edges[r], edges[r + 1] + 1)
                o = self.mesh_object(f"SM_{name}_Terrain_{r}_{c}", step=step, region=region, material=material)
                sr.export_fbx(o, os.path.join(folder, f"{o.name}.fbx"))
                objs.append(o)
        return objs

    def hillshade(self, size=1024, light=(-1, 1, 1.4)):
        """Shaded relief image (numpy RGB float) for minimaps."""
        step = max(1, self.n // size)
        h = self.h[::step, ::step]
        gy, gx = np.gradient(h, self.res * step)
        nrm = np.stack([-gx, -gy, np.ones_like(h)], -1)
        nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True)
        L = np.array(light, float)
        L /= np.linalg.norm(L)
        return np.clip(nrm @ L, 0, 1)


def terrain_material(name, layers, tiles, tints=None):
    """Blender preview material blending up to 4 tileable texture sets via the 'Weights' colour attribute.
    Also registers a manifest entry (kind='terrain') so Unreal builds a matching blend instance."""
    import bpy
    import sr
    tints = tints or [(1, 1, 1)] * len(layers)
    m = bpy.data.materials.new("M_" + name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    attr = nt.nodes.new("ShaderNodeAttribute")
    attr.attribute_name = "Weights"
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(attr.outputs["Color"], sep.inputs[0])
    uvn = nt.nodes.new("ShaderNodeUVMap")
    uvn.uv_map = "UVMap"
    shaders = []
    for k, (tex, tile) in enumerate(zip(layers, tiles)):
        bs = nt.nodes.new("ShaderNodeBsdfPrincipled")
        mapping = nt.nodes.new("ShaderNodeVectorMath")
        mapping.operation = "SCALE"
        mapping.inputs[3].default_value = 1.0 / tile
        nt.links.new(uvn.outputs[0], mapping.inputs[0])
        for suf, sock in (("D", "Base Color"), ("R", "Roughness"), ("N", None)):
            p = sr._tex_path(tex, suf)
            if not p:
                continue
            it = nt.nodes.new("ShaderNodeTexImage")
            it.image = sr._img(p)
            nt.links.new(mapping.outputs[0], it.inputs[0])
            if suf == "D":
                mix = nt.nodes.new("ShaderNodeMix")
                mix.data_type = "RGBA"
                mix.blend_type = "MULTIPLY"
                mix.inputs["Factor"].default_value = 1.0
                nt.links.new(it.outputs[0], mix.inputs["A"])
                mix.inputs["B"].default_value = tuple(tints[k]) + (1,)
                nt.links.new(mix.outputs["Result"], bs.inputs["Base Color"])
            elif suf == "R":
                it.image.colorspace_settings.name = "Non-Color"
                nt.links.new(it.outputs[0], bs.inputs["Roughness"])
            else:
                it.image.colorspace_settings.name = "Non-Color"
                nm = nt.nodes.new("ShaderNodeNormalMap")
                nt.links.new(it.outputs[0], nm.inputs["Color"])
                nt.links.new(nm.outputs[0], bs.inputs["Normal"])
        shaders.append(bs)
    cur = shaders[0].outputs[0]
    for k in range(1, len(shaders)):
        mx = nt.nodes.new("ShaderNodeMixShader")
        nt.links.new(sep.outputs[k - 1], mx.inputs[0])
        nt.links.new(cur, mx.inputs[1])
        nt.links.new(shaders[k].outputs[0], mx.inputs[2])
        cur = mx.outputs[0]
    nt.links.new(cur, out.inputs["Surface"])
    sr.MANIFEST["M_" + name] = dict(kind="terrain", layers=list(layers), tiles=list(tiles),
                                    tints=[list(t) for t in tints], color=[1, 1, 1], rough=0.9, metal=0.0)
    return m
