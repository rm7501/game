"""Sahara Racers - shared map pipeline (terrain + tracks + props -> Unreal-ready map folder).

Map folder (assets/maps/<Map>/):
  SM_<Map>_Terrain_<r>_<c>.fbx   terrain tiles (vertex-colour layer blend, Nanite)
  SM_<Map>_<Track>_<NN>.fbx      track chunks (road, kerbs, barriers, bridges, tunnels)
  SM_<Map>_Water.fbx             sea / lake surface (if any)
  landscape/                     UE Landscape heightmap + weightmaps + landscape.json
  track.json                     racing line, shortcuts, checkpoints, start grid, pickups (UE units)
  layout.json                    every prop: kit, asset, UE transform
  minimap.png                    top-down map with the shortcuts marked
"""
import json
import math
import os
import random

import numpy as np

import sr
import track as trk
from terrain import Terrain, terrain_material

try:
    from scipy.spatial import cKDTree
except ImportError:
    cKDTree = None


class MapBuild:
    def __init__(self, name, title, terrain: Terrain, terrain_mat, water=None):
        self.name, self.title = name, title
        self.terrain = terrain
        self.terrain_mat = terrain_mat
        self.water = water
        self.folder = os.path.join(sr.ROOT, "assets", "maps", name)
        self.main = None
        self.shortcuts = []
        self.place_list = []           # (kit, asset, (x, y, z), yaw_deg, scale)
        self._tree = None
        self.objects = {}              # asset name -> blender object (for previews)
        self.backdrop_args = None      # (far, paint, blend): scenery ring to the horizon
        self.far_detail = []           # callables returning merged distant-detail objects
        self._backdrop = None

    # -- tracks ------------------------------------------------------------
    def set_tracks(self, main, shortcuts):
        self.main = main
        self.shortcuts = shortcuts

    def build_tracks(self, carve_layer=None, falloff=18.0):
        t = self.terrain
        self.main.build(t)
        for sc in self.shortcuts:
            a, b = sc.cps[0]["p"], sc.cps[-1]["p"]
            sa, sb = self.main.nearest_s(a), self.main.nearest_s(b)
            pa = self.main.frame((sa - 25) % self.main.length)[0][:2]
            pb = self.main.frame((sb + 25) % self.main.length)[0][:2]
            sc.phantom = (pa, pb)
            sc.build(t, main=self.main)
        # carve: shortcuts first (narrower), main last so it wins where they overlap
        for sc in self.shortcuts:
            sc.carve(t, falloff=falloff * 0.7, layer=carve_layer)
        self.main.carve(t, falloff=falloff, layer=carve_layer)
        for tr in [self.main] + self.shortcuts:
            tr.cut_tunnel_holes(t)
        for sc in self.shortcuts:            # barrier openings where shortcuts leave / rejoin
            self.main.open_junctions(sc)
        allp = np.concatenate([tr.P for tr in [self.main] + self.shortcuts])
        allw = np.concatenate([tr.W for tr in [self.main] + self.shortcuts])
        self._pts, self._w = allp, allw
        if cKDTree is not None:
            self._tree = cKDTree(allp)

    def clearance(self, x, y):
        """Distance from (x,y) to the nearest road edge (negative = on the road)."""
        if self._tree is None:
            d = np.linalg.norm(self._pts - np.array([x, y]), axis=1)
            i = int(np.argmin(d))
            return float(d[i] - self._w[i] / 2)
        d, i = self._tree.query([x, y])
        return float(d - self._w[i] / 2)

    # -- props ----------------------------------------------------------------
    def place(self, kit, asset, x, y, z=None, yaw=0.0, scale=1.0, sink=0.0):
        if z is None:
            half = self.terrain.size / 2
            if (abs(x) > half or abs(y) > half) and self.backdrop is not None:
                z = float(self.backdrop.height(np.array([x]), np.array([y]))[0]) - sink
            else:
                z = float(self.terrain.sample(x, y)) - sink
        self.place_list.append((kit, asset, (float(x), float(y), float(z)), float(yaw), float(scale)))

    def scatter(self, kit, assets, count, bounds, clearance=12.0, seed=1, max_slope=0.6, scale=(0.8, 1.2),
                mask=None, min_spacing=0.0, sink=0.0, yaw=None):
        rnd = random.Random(seed)
        x0, x1, y0, y1 = bounds
        slope = self.terrain.slope()
        placed, tries = [], 0
        while len(placed) < count and tries < count * 40:
            tries += 1
            x, y = rnd.uniform(x0, x1), rnd.uniform(y0, y1)
            if mask is not None and not mask(x, y):
                continue
            if self.clearance(x, y) < clearance:
                continue
            j = int((y + self.terrain.size / 2) / self.terrain.res)
            i = int((x + self.terrain.size / 2) / self.terrain.res)
            if not (0 <= i < self.terrain.n and 0 <= j < self.terrain.n) or slope[j, i] > max_slope:
                continue
            if self.water is not None and self.terrain.h[j, i] < self.water + 0.3:
                continue
            if min_spacing and any((x - px) ** 2 + (y - py) ** 2 < min_spacing ** 2 for px, py in placed):
                continue
            a = rnd.choice(assets) if isinstance(assets, (list, tuple)) else assets
            self.place(kit, a, x, y, yaw=rnd.uniform(0, 360) if yaw is None else yaw, scale=rnd.uniform(*scale), sink=sink)
            placed.append((x, y))
        return placed

    def along(self, track, kit, asset, every, offset, s0=0.0, s1=None, side=(1, -1), yaw_add=0.0, jitter=0.0,
              seed=3, face_road=True, min_clear=None):
        """Place props along a track edge at lateral `offset` from the road edge."""
        rnd = random.Random(seed)
        s1 = track.length if s1 is None else s1
        s = s0
        while s < s1:
            p, t, n, w, b = track.frame(s % track.length if track.closed else min(s, track.length))
            i = int(round(s / track.step)) % len(track.S) if track.closed else min(int(round(s / track.step)), len(track.S) - 1)
            if not track.tunnel[i] and not track.gap[i]:
                for sg in side:
                    q = p[:2] + n * sg * (w / 2 + offset + rnd.uniform(-jitter, jitter))
                    if min_clear is not None and self.clearance(q[0], q[1]) < min_clear:
                        continue
                    yaw = math.degrees(math.atan2(t[1], t[0])) + (90 if face_road and sg > 0 else -90 if face_road else 0) + yaw_add
                    z = None if not track.bridge[i] else float(track.Z[i])
                    a = rnd.choice(asset) if isinstance(asset, (list, tuple)) else asset
                    self.place(kit, a, q[0], q[1], z=z, yaw=yaw)
            s += every

    # -- backdrop ---------------------------------------------------------------
    def set_backdrop(self, far, paint=None, blend=600.0):
        self.backdrop_args = (far, paint, blend)

    @property
    def backdrop(self):
        if self._backdrop is None and self.backdrop_args:
            from backdrop import Backdrop
            far, paint, blend = self.backdrop_args
            self._backdrop = Backdrop(self.terrain, far, paint, blend=blend)
        return self._backdrop

    def backdrop_objects(self):
        objs = []
        if self.backdrop is not None:
            objs.append(self.backdrop.mesh_object(f"SM_{self.name}_Backdrop", self.terrain_mat))
        for fn in self.far_detail:
            objs += fn(self)
        return objs

    # -- export ------------------------------------------------------------------
    def export(self, tiles=4, step=6, landscape=True):
        os.makedirs(self.folder, exist_ok=True)
        t = self.terrain
        objs = t.export_tiles(self.folder, self.name, tiles=tiles, step=step, material=self.terrain_mat)
        for o in objs:
            bpy_remove(o)
        track_objs = []
        for tr in [self.main] + self.shortcuts:
            for o in tr.build_meshes(self.name):
                sr.export_fbx(o, os.path.join(self.folder, f"{o.name}.fbx"))
                track_objs.append(o)
        if self.water is not None:
            w = self.water_object()
            sr.export_fbx(w, os.path.join(self.folder, f"{w.name}.fbx"))
            track_objs.append(w)
        for o in self.backdrop_objects():
            sr.export_fbx(o, os.path.join(self.folder, f"{o.name}.fbx"), colors="LINEAR")
            track_objs.append(o)
        for o in track_objs:          # exported - the preview scene rebuilds its own copies
            bpy_remove(o)
        if landscape:
            t.export_landscape(os.path.join(self.folder, "landscape"), self.name)
        self.write_layout()
        trk.minimap(os.path.join(self.folder, "minimap.png"), t, self.main, self.shortcuts, self.title, self.water)
        return track_objs

    def write_gameplay(self, pickups=(), boosts=()):
        extra = trk.gameplay(self.main, self.shortcuts, pickups=pickups, boosts=boosts)
        return trk.write_track_json(self.folder, self.name, self.main, self.shortcuts, extra)

    def water_object(self):
        wm = sr.mat("Water_Sea", (0.02, 0.12, 0.16), rough=0.04, metal=0.0, kind="water", tex="WaterWaves", tile=24.0)
        mb = sr.MB(f"SM_{self.name}_Water")
        s = 30000.0
        mb.poly_facing([(-s, -s, self.water), (s, -s, self.water), (s, s, self.water), (-s, s, self.water)], (0, 0, 1), wm)
        return mb.to_object(uv=True)

    def write_layout(self):
        items = []
        for kit, asset, (x, y, z), yaw, sc in self.place_list:
            items.append(dict(kit=kit, asset=asset, x=round(x * 100, 1), y=round(-y * 100, 1), z=round(z * 100, 1),
                              yaw=round(-yaw, 2), scale=round(sc, 3)))
        with open(os.path.join(self.folder, "layout.json"), "w") as f:
            json.dump(dict(map=self.name, units="Unreal cm / degrees", count=len(items), props=items), f, indent=0)

    # -- preview scene ----------------------------------------------------------
    def preview_scene(self, kit_objects, step=2):
        """Terrain + tracks + instanced props in the current Blender scene (for renders / .blend)."""
        by = {o.name: o for o in kit_objects}
        for o in kit_objects:
            sr.hide(o)
        self.terrain.mesh_object(f"{self.name}_Terrain", step=step, material=self.terrain_mat)
        for tr in [self.main] + self.shortcuts:
            tr.build_meshes(self.name)
        if self.water is not None:
            self.water_object()
        # scenery ring to the horizon, then a distant ground plane beyond it (renders only)
        self.backdrop_objects()
        h = self.terrain.h if self.backdrop is None else self.backdrop.H
        hmin = float(min(h[0, :].min(), h[-1, :].min(), h[:, 0].min(), h[:, -1].min()))
        far = getattr(self, "far_mat", None) or sr.mat("Sand", (1, 1, 1), tex="Sand", tile=6)
        sr.ground(120000, far, z=hmin - 0.5, name="FarGround")
        missing = set()
        for kit, asset, loc, yaw, sc in self.place_list:
            o = by.get(asset)
            if o is None:
                missing.add(asset)
                continue
            sr.inst(o, loc, (0, 0, yaw), sc)
        if missing:
            print("preview: missing assets", sorted(missing))

    def car_on_track(self, car, s, lateral=0.0, track=None):
        tr = track or self.main
        p, t, n, w, b = tr.frame(s)
        q = p + np.array([n[0], n[1], 0]) * lateral
        glb = os.path.join(sr.ROOT, "assets", "cars", car, f"{car}_preview.glb")
        if os.path.exists(glb):
            sr.import_glb(glb, (q[0], q[1], q[2] + 0.02), math.degrees(math.atan2(t[1], t[0])))

    def chase_camera(self, s, back=11.0, height=3.4, ahead=40.0, lens=30, lateral=0.0, track=None):
        tr = track or self.main
        p, t, n, w, b = tr.frame(s)
        L = tr.length
        p2, *_ = tr.frame((s + ahead) % L if tr.closed else min(s + ahead, L))
        nn = np.array([n[0], n[1], 0])
        cam = p - np.array([t[0], t[1], 0]) * back + nn * lateral + np.array([0, 0, height])
        return sr.camera(tuple(cam), tuple(p2 + np.array([0, 0, 1.5])), lens)


def render_previews(m, shots, lighting, cars=(), res=(1600, 900), samples=64, prefix=None):
    """shots: list of ('overview', (cam_loc), (target), lens) or ('chase', s, dict(...)).
    cars: list of (car, s, lateral, track or None). lighting: callable that sets world/sun."""
    import bpy
    for car, s, lat, tr in cars:
        m.car_on_track(car, s, lat, tr)
    sr.setup_render(res, samples)
    lighting()
    out = []
    folder = os.path.join(sr.ROOT, "docs", "previews", "maps")
    os.makedirs(folder, exist_ok=True)
    for k, shot in enumerate(shots):
        if shot[0] == "overview":
            _, loc, target, lens = shot
            sr.camera(loc, target, lens)
        else:
            _, s, kw = shot
            m.chase_camera(s, **kw)
        path = os.path.join(folder, f"{prefix or m.name}_{k + 1}.png")
        sr.render(path)
        out.append(path)
    return out


def bpy_remove(o):
    import bpy
    bpy.data.objects.remove(o, do_unlink=True)


def kit_objects(*kits):
    """Build the requested asset kits (objects stay in the scene, hidden) for preview instancing."""
    import sys
    here = os.path.join(sr.ROOT, "blender")
    if here not in sys.path:
        sys.path.insert(0, here)
    objs = []
    orig_reset = sr.reset
    sr.reset = lambda: None          # kits normally wipe the scene; keep everything for composition
    try:
        objs = _build_kits(kits)
    finally:
        sr.reset = orig_reset
    return objs


def _build_kits(kits):
    objs = []
    for k in kits:
        if k == "common":
            import kit_common
            kit_common.make_textures()
            objs += [b() for b in kit_common.BUILDERS]
        else:
            mod = __import__(f"kit_{k}")
            if hasattr(mod, "make_textures"):
                mod.make_textures()
            objs += mod.build_all()
    return objs
