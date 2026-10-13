"""Sahara Racers - shared Blender helpers.

Everything is built procedurally with bmesh so the assets are reproducible:
    python blender/build_all.py
Units: 1 Blender unit = 1 metre (Unreal imports FBX as centimetres automatically).
Forward axis for vehicles: +X (maps to Unreal +X forward with default FBX import).
"""
import json
import math
import os

import bpy  # noqa: must import before bmesh when running as a Python module
import bmesh
from mathutils import Euler, Matrix, Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TEX_DIR = os.path.join(ROOT, "assets", "textures")
MANIFEST = {}          # material name -> parameters, consumed by unreal/import_assets.py
_MAT_CACHE = {}


# ------------------------------------------------------------------ scene ---
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _MAT_CACHE.clear()
    sc = bpy.context.scene
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0


def collection(name):
    c = bpy.data.collections.get(name)
    if not c:
        c = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(c)
    return c


# -------------------------------------------------------------- materials ---
def _img(path):
    for im in bpy.data.images:
        if im.filepath == path:
            return im
    im = bpy.data.images.load(path)
    return im


def _tex_path(tex, suffix):
    for ext in (".jpg", ".png"):
        p = os.path.join(TEX_DIR, f"T_{tex}_{suffix}{ext}")
        if os.path.exists(p):
            return p
    return None


def mat(name, color=(0.8, 0.8, 0.8), rough=0.5, metal=0.0, tex=None, tile=1.0,
        emit=None, emit_str=0.0, transmission=0.0, alpha=1.0, coat=0.0, normal=1.0,
        kind="opaque", image=None, image_emit=False):
    """Create (or fetch) a PBR material. Name is used 1:1 in Unreal (MI_<name>).

    tex      : texture set name in assets/textures (T_<tex>_D/N/R/E)
    tile     : metres per texture repeat (UVs are generated in world metres)
    kind     : opaque | glass | mirror | emissive   (selects the Unreal parent material)
    image    : explicit (non-tiling) image file for decals/signs, UV 0..1 set by the mesh
    """
    name = name if name.startswith("M_") else "M_" + name
    if name in _MAT_CACHE:
        return _MAT_CACHE[name]
    m = bpy.data.materials.new(name)
    m["tile_m"] = float(tile)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bs = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bs.outputs[0], out.inputs["Surface"])
    col = tuple(color) + (1.0,) if len(color) == 3 else tuple(color)
    bs.inputs["Base Color"].default_value = col
    bs.inputs["Roughness"].default_value = rough
    bs.inputs["Metallic"].default_value = metal
    if coat:
        bs.inputs["Coat Weight"].default_value = coat
        bs.inputs["Coat Roughness"].default_value = 0.03
    if transmission:
        bs.inputs["Transmission Weight"].default_value = transmission
        bs.inputs["IOR"].default_value = 1.5
    if alpha < 1:
        bs.inputs["Alpha"].default_value = alpha
    if emit:
        bs.inputs["Emission Color"].default_value = tuple(emit) + (1.0,)
        bs.inputs["Emission Strength"].default_value = emit_str
    if tex:
        uv = nt.nodes.new("ShaderNodeUVMap")
        uv.uv_map = "UVMap"
        d = _tex_path(tex, "D")
        if d:
            it = nt.nodes.new("ShaderNodeTexImage")
            it.image = _img(d)
            nt.links.new(uv.outputs[0], it.inputs[0])
            mix = nt.nodes.new("ShaderNodeMix")
            mix.data_type = "RGBA"
            mix.blend_type = "MULTIPLY"
            mix.inputs["Factor"].default_value = 1.0
            nt.links.new(it.outputs[0], mix.inputs["A"])
            mix.inputs["B"].default_value = col
            nt.links.new(mix.outputs["Result"], bs.inputs["Base Color"])
        r = _tex_path(tex, "R")
        if r:
            it = nt.nodes.new("ShaderNodeTexImage")
            it.image = _img(r)
            it.image.colorspace_settings.name = "Non-Color"
            nt.links.new(uv.outputs[0], it.inputs[0])
            nt.links.new(it.outputs[0], bs.inputs["Roughness"])
        n = _tex_path(tex, "N")
        if n:
            it = nt.nodes.new("ShaderNodeTexImage")
            it.image = _img(n)
            it.image.colorspace_settings.name = "Non-Color"
            nm = nt.nodes.new("ShaderNodeNormalMap")
            nm.inputs["Strength"].default_value = normal
            nt.links.new(uv.outputs[0], it.inputs[0])
            nt.links.new(it.outputs[0], nm.inputs["Color"])
            nt.links.new(nm.outputs[0], bs.inputs["Normal"])
        e = _tex_path(tex, "E")
        if e:
            it = nt.nodes.new("ShaderNodeTexImage")
            it.image = _img(e)
            nt.links.new(uv.outputs[0], it.inputs[0])
            nt.links.new(it.outputs[0], bs.inputs["Emission Color"])
            bs.inputs["Emission Strength"].default_value = emit_str or 4.0
    if image:
        uv = nt.nodes.new("ShaderNodeUVMap")
        uv.uv_map = "UVMap"
        it = nt.nodes.new("ShaderNodeTexImage")
        it.image = _img(image)
        it.extension = "EXTEND"
        nt.links.new(uv.outputs[0], it.inputs[0])
        nt.links.new(it.outputs[0], bs.inputs["Base Color"])
        if image_emit:
            nt.links.new(it.outputs[0], bs.inputs["Emission Color"])
            bs.inputs["Emission Strength"].default_value = emit_str or 2.0
    MANIFEST[name] = dict(kind=kind, color=list(col[:3]), rough=rough, metal=metal, tex=tex,
                          tile=tile, emit=list(emit) if emit else None, emit_str=emit_str,
                          transmission=transmission, alpha=alpha, coat=coat,
                          image=os.path.relpath(image, ROOT).replace(os.sep, "/") if image else None,
                          image_emit=image_emit)
    _MAT_CACHE[name] = m
    return m


def write_manifest():
    path = os.path.join(ROOT, "assets", "materials.json")
    data = {}
    if os.path.exists(path):
        with open(path) as f:
            data = json.load(f)
    data.update(MANIFEST)
    with open(path, "w") as f:
        json.dump(dict(sorted(data.items())), f, indent=1)


# ------------------------------------------------------------ mesh build ---
def _m4(loc=(0, 0, 0), rot=(0, 0, 0), scale=None):
    M = Matrix.Translation(Vector(loc)) @ Euler([math.radians(a) for a in rot]).to_matrix().to_4x4()
    if scale is not None:
        if isinstance(scale, (int, float)):
            scale = (scale, scale, scale)
        M = M @ Matrix.Diagonal(Vector(tuple(scale) + (1.0,)))
    return M


class MB:
    """Mesh builder: accumulates primitives (each with its own material) in one bmesh."""

    def __init__(self, name):
        self.name = name
        self.bm = bmesh.new()
        self.mats = []
        self.keep = self.bm.faces.layers.int.new("keep")      # 1 = do not recalc normal
        self.uvfix = self.bm.faces.layers.int.new("uvfix")    # 1 = explicit UVs already set
        self.uvl = self.bm.loops.layers.uv.new("UVMap")
        self.grid_last = None

    def mi(self, m):
        if m is None:
            m = mat("Default")
        if m not in self.mats:
            self.mats.append(m)
        return self.mats.index(m)

    def _tag(self, faces, m, smooth):
        idx = self.mi(m)
        for f in faces:
            f.material_index = idx
            f.smooth = smooth
        return faces

    @staticmethod
    def _faces_of(verts):
        s = set()
        for v in verts:
            s.update(v.link_faces)
        return list(s)

    # --- primitives -------------------------------------------------------
    def box(self, size, loc=(0, 0, 0), rot=(0, 0, 0), m=None, bevel=0.0, seg=1, smooth=False):
        M = _m4(loc, rot) @ Matrix.Diagonal(Vector((size[0], size[1], size[2], 1.0)))
        r = bmesh.ops.create_cube(self.bm, size=1.0, matrix=M)
        verts = r["verts"]
        faces = self._faces_of(verts)
        if bevel > 0:
            edges = list({e for f in faces for e in f.edges})
            res = bmesh.ops.bevel(self.bm, geom=edges + verts, offset=bevel, segments=seg,
                                  affect="EDGES", profile=0.5, clamp_overlap=True)
            faces = faces + list(res["faces"])
            faces = [f for f in set(faces) if f.is_valid]
        return self._tag(faces, m, smooth or (bevel > 0 and seg > 1))

    def cyl(self, r, h, loc=(0, 0, 0), rot=(0, 0, 0), m=None, seg=24, r2=None, caps=True,
            smooth=True):
        """Cylinder / cone along local Z, centred on loc."""
        M = _m4(loc, rot)
        res = bmesh.ops.create_cone(self.bm, cap_ends=caps, cap_tris=False, segments=seg,
                                    radius1=r, radius2=r if r2 is None else r2, depth=h, matrix=M)
        faces = self._faces_of(res["verts"])
        self._tag(faces, m, smooth)
        if smooth and caps:   # keep caps flat-shaded
            for f in faces:
                if len(f.verts) > 4:
                    f.smooth = False
        return faces

    def sphere(self, r, loc=(0, 0, 0), rot=(0, 0, 0), m=None, seg=24, rings=12, scale=None):
        M = _m4(loc, rot, scale)
        res = bmesh.ops.create_uvsphere(self.bm, u_segments=seg, v_segments=rings, radius=r, matrix=M)
        return self._tag(self._faces_of(res["verts"]), m, True)

    def lathe(self, prof, seg=32, loc=(0, 0, 0), rot=(0, 0, 0), m=None, smooth=True,
              close_top=False, close_bottom=False, arc=360.0):
        """Surface of revolution around local Z. prof = [(radius, z), ...]."""
        M = _m4(loc, rot)
        full = abs(arc - 360.0) < 1e-6
        n = seg if full else seg + 1
        rings = []
        for (rr, z) in prof:
            ring = []
            for i in range(n):
                a = math.radians(arc) * i / seg
                ring.append(self.bm.verts.new(M @ Vector((rr * math.cos(a), rr * math.sin(a), z))))
            rings.append(ring)
        faces = []
        for j in range(len(rings) - 1):
            A, B = rings[j], rings[j + 1]
            for i in range(seg):
                i2 = (i + 1) % n
                faces.append(self.bm.faces.new((A[i], A[i2], B[i2], B[i])))
        if close_bottom and full:
            faces.append(self.bm.faces.new(list(reversed(rings[0]))))
        if close_top and full:
            faces.append(self.bm.faces.new(rings[-1]))
        return self._tag(faces, m, smooth)

    def loft(self, rings, m=None, closed=True, cap_start=False, cap_end=False, smooth=True,
             mats=None, zip_caps=False):
        """Loft through rings of points (each ring same length).
        mats: optional callable(j, i) -> material for face between ring j..j+1, point i..i+1.
        zip_caps: close the ends with a quad strip bridging the two mirrored halves of the ring
                  (ring = [bottom, +side..., top, -side...]); subdivides far cleaner than an n-gon."""
        vr = [[self.bm.verts.new(Vector(p)) for p in ring] for ring in rings]
        self.grid_last = vr
        n = len(rings[0])
        faces = []
        span = n if closed else n - 1
        for j in range(len(vr) - 1):
            for i in range(span):
                i2 = (i + 1) % n
                f = self.bm.faces.new((vr[j][i], vr[j][i2], vr[j + 1][i2], vr[j + 1][i]))
                fm = mats(j, i) if mats else m
                self._tag([f], fm, smooth)
                faces.append(f)
        if zip_caps:
            h = n // 2
            for ring, fm_j in ((vr[0], 0), (vr[-1], len(vr) - 2)):
                for k in range(h):
                    a, b = ring[k], ring[k + 1]
                    c, d = ring[(n - k - 1) % n], ring[(n - k) % n]
                    quad = [a, b, c, d]
                    uniq = []
                    for v in quad:
                        if v not in uniq:
                            uniq.append(v)
                    if len(uniq) < 3:
                        continue
                    f = self.bm.faces.new(uniq)
                    fm = mats(fm_j, k) if mats else m
                    self._tag([f], fm, smooth)
                    faces.append(f)
            return faces
        if cap_start:
            f = self.bm.faces.new(list(reversed(vr[0])))
            self._tag([f], m, False)
            faces.append(f)
        if cap_end:
            f = self.bm.faces.new(vr[-1])
            self._tag([f], m, False)
            faces.append(f)
        return faces

    def prism(self, poly, z0, z1, loc=(0, 0, 0), rot=(0, 0, 0), m=None, top=True, bottom=True,
              smooth=False):
        """Extrude a 2D polygon (CCW list of (x,y)) from z0 to z1."""
        M = _m4(loc, rot)
        b = [self.bm.verts.new(M @ Vector((x, y, z0))) for x, y in poly]
        t = [self.bm.verts.new(M @ Vector((x, y, z1))) for x, y in poly]
        n = len(poly)
        faces = [self.bm.faces.new((b[i], b[(i + 1) % n], t[(i + 1) % n], t[i])) for i in range(n)]
        if bottom:
            faces.append(self.bm.faces.new(list(reversed(b))))
        if top:
            faces.append(self.bm.faces.new(t))
        return self._tag(faces, m, smooth)

    def tube(self, path, r, m=None, seg=8, caps=True, smooth=True):
        """Sweep a circle of radius r (float or per-point list) along a polyline."""
        pts = [Vector(p) for p in path]
        rr = r if isinstance(r, (list, tuple)) else [r] * len(pts)
        rings = []
        up = Vector((0, 0, 1))
        for k, p in enumerate(pts):
            if k == 0:
                t = pts[1] - pts[0]
            elif k == len(pts) - 1:
                t = pts[-1] - pts[-2]
            else:
                t = (pts[k + 1] - pts[k - 1])
            t.normalize()
            ref = up if abs(t.dot(up)) < 0.95 else Vector((1, 0, 0))
            a = t.cross(ref).normalized()
            b = t.cross(a).normalized()
            rings.append([p + (a * math.cos(2 * math.pi * i / seg) + b * math.sin(2 * math.pi * i / seg)) * rr[k]
                          for i in range(seg)])
        return self.loft(rings, m, closed=True, cap_start=caps, cap_end=caps, smooth=smooth)

    def grid(self, fn, nx, ny, x0, x1, y0, y1, m=None, smooth=True, loc=(0, 0, 0)):
        """Height-field surface z = fn(x, y)."""
        L = Vector(loc)
        vs = []
        for j in range(ny + 1):
            row = []
            for i in range(nx + 1):
                x = x0 + (x1 - x0) * i / nx
                y = y0 + (y1 - y0) * j / ny
                row.append(self.bm.verts.new(L + Vector((x, y, fn(x, y)))))
            vs.append(row)
        faces = [self.bm.faces.new((vs[j][i], vs[j][i + 1], vs[j + 1][i + 1], vs[j + 1][i]))
                 for j in range(ny) for i in range(nx)]
        return self._tag(faces, m, smooth)

    def poly(self, pts, m=None, smooth=False):
        f = self.bm.faces.new([self.bm.verts.new(Vector(p)) for p in pts])
        return self._tag([f], m, smooth)

    def strip(self, grid, uvs=None, mat=None, smooth=True, keep=True, closed=False):
        """Quad grid from rows of points grid[i][k] (rows along the path, k across).
        Face (i,k)->(i,k+1)->(i+1,k+1)->(i+1,k): with k running left->right and i forward this faces UP.
        uvs: same shape list of (u,v) or None (world UVs); mat: material or callable(i, k) -> material."""
        vs = [[self.bm.verts.new(Vector(p)) for p in row] for row in grid]
        faces = []
        nrow = len(vs)
        for i in range(nrow - 1 + (1 if closed else 0)):
            A, B = vs[i], vs[(i + 1) % nrow]
            for k in range(len(A) - 1):
                f = self.bm.faces.new((A[k], A[k + 1], B[k + 1], B[k]))
                m = mat(i, k) if callable(mat) else mat
                self._tag([f], m, smooth)
                if keep:
                    f[self.keep] = 1
                if uvs is not None:
                    f[self.uvfix] = 1
                    U0, U1 = uvs[i], uvs[(i + 1) % nrow]
                    for lp, uv in zip(f.loops, (U0[k], U0[k + 1], U1[k + 1], U1[k])):
                        lp[self.uvl].uv = uv
                faces.append(f)
        return faces

    def poly_facing(self, pts, normal, m=None, smooth=False):
        """Single face guaranteed to face `normal` (isolated faces cannot be auto-oriented)."""
        f = self.bm.faces.new([self.bm.verts.new(Vector(p)) for p in pts])
        f.normal_update()
        if f.normal.dot(Vector(normal)) < 0:
            f.normal_flip()
        self._tag([f], m, smooth)
        f[self.keep] = 1
        return f

    def quad_uv(self, pts, uvs=((0, 0), (1, 0), (1, 1), (0, 1)), m=None):
        """Single face with explicit UVs (signs, plates, card art)."""
        f = self.bm.faces.new([self.bm.verts.new(Vector(p)) for p in pts])
        self._tag([f], m, False)
        f[self.uvfix] = 1
        f[self.keep] = 1   # winding given by caller (CCW = front)
        for lp, uv in zip(f.loops, uvs):
            lp[self.uvl].uv = uv
        return f

    def flip(self, faces):
        """Reverse normals and protect them from recalculation (interior shells)."""
        bmesh.ops.reverse_faces(self.bm, faces=faces)
        for f in faces:
            f[self.keep] = 1
        return faces

    def crease(self, verts_a, verts_b, value=1.0):
        """Edge crease between paired vertex lists (used by Subdivision Surface)."""
        lay = self.bm.edges.layers.float.get("crease_edge") or self.bm.edges.layers.float.new("crease_edge")
        for a, b in zip(verts_a, verts_b):
            e = self.bm.edges.get((a, b))
            if e:
                e[lay] = value

    def add_object(self, obj, loc=(0, 0, 0), rot=(0, 0, 0), scale=None, apply_mods=True):
        """Append another object's (evaluated) mesh, keeping its materials."""
        me = evaluated_mesh(obj) if apply_mods else obj.data
        tmp = bmesh.new()
        tmp.from_mesh(me)
        remap = [self.mi(s.material) for s in obj.material_slots] or [self.mi(None)]
        for f in tmp.faces:
            f.material_index = remap[min(f.material_index, len(remap) - 1)]
        tmp.transform(_m4(loc, rot, scale) @ obj.matrix_world)
        me2 = bpy.data.meshes.new("_tmp")
        tmp.to_mesh(me2)
        tmp.free()
        self.bm.from_mesh(me2)
        bpy.data.meshes.remove(me2)

    def add_mb(self, other, loc=(0, 0, 0), rot=(0, 0, 0), scale=None):
        """Append another MB (copy) with a transform."""
        me = bpy.data.meshes.new("_tmp")
        other.bm.to_mesh(me)
        tmp = bmesh.new()
        tmp.from_mesh(me)
        remap = [self.mi(mm) for mm in other.mats]
        for f in tmp.faces:
            if remap:
                f.material_index = remap[f.material_index]
        tmp.transform(_m4(loc, rot, scale))
        tmp.to_mesh(me)
        tmp.free()
        self.bm.from_mesh(me)
        bpy.data.meshes.remove(me)

    # --- output -----------------------------------------------------------
    def to_object(self, coll=None, uv=True, sharp_angle=40.0, origin=None):
        me = bpy.data.meshes.new(self.name)
        bmesh.ops.recalc_face_normals(self.bm, faces=[f for f in self.bm.faces if not f[self.keep]])
        ngons = [f for f in self.bm.faces if len(f.verts) > 4]
        if ngons:   # keep quads, triangulate n-gons so FBX can export tangents
            bmesh.ops.triangulate(self.bm, faces=ngons, quad_method="BEAUTY", ngon_method="BEAUTY")
        if uv:
            world_uv_bm(self.bm, self.mats)
        self.bm.to_mesh(me)
        self.bm.free()
        for m in self.mats:
            me.materials.append(m)
        if sharp_angle:
            try:
                me.set_sharp_from_angle(angle=math.radians(sharp_angle))
            except Exception:
                pass
        ob = bpy.data.objects.new(self.name, me)
        (coll or bpy.context.scene.collection).objects.link(ob)
        if origin is not None:
            set_origin(ob, origin)
        return ob


def world_uv_bm(bm, mats):
    """Box-project UVs in world metres divided by each material's tile size."""
    uvl = bm.loops.layers.uv.get("UVMap") or bm.loops.layers.uv.new("UVMap")
    fix = bm.faces.layers.int.get("uvfix")
    tiles = [float(m.get("tile_m", 1.0)) if m else 1.0 for m in mats] or [1.0]
    for f in bm.faces:
        if fix is not None and f[fix]:
            continue
        t = tiles[min(f.material_index, len(tiles) - 1)] or 1.0
        n = f.normal
        ax, ay, az = abs(n.x), abs(n.y), abs(n.z)
        for lp in f.loops:
            co = lp.vert.co
            if az >= ax and az >= ay:
                u, v = co.x, co.y
            elif ax >= ay:
                u, v = (co.y if n.x > 0 else -co.y), co.z
            else:
                u, v = (-co.x if n.y > 0 else co.x), co.z
            lp[uvl].uv = (u / t, v / t)


def evaluated_mesh(obj):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    return bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=True, depsgraph=dg)


def apply_modifiers(obj):
    me = evaluated_mesh(obj)
    old = obj.data
    obj.modifiers.clear()
    obj.data = me
    if old.users == 0:
        bpy.data.meshes.remove(old)
    return obj


def set_origin(ob, mode="base"):
    """Move mesh so the object origin sits at base-centre ('base') or bounds centre ('center')."""
    vs = ob.data.vertices
    if not len(vs):
        return ob
    xs = [v.co.x for v in vs]
    ys = [v.co.y for v in vs]
    zs = [v.co.z for v in vs]
    c = Vector(((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2,
                min(zs) if mode == "base" else (min(zs) + max(zs)) / 2))
    if mode == "keep":
        return ob
    ob.data.transform(Matrix.Translation(-c))
    ob.location = Vector(ob.location) + c
    return ob


def displace(obj, strength=1.0, size=1.0, kind="CLOUDS", depth=2, subdiv=0, seed=0, apply=True):
    if subdiv:
        sm = obj.modifiers.new("sub", "SUBSURF")
        sm.levels = subdiv
        sm.render_levels = subdiv
        sm.subdivision_type = "SIMPLE"
    tx = bpy.data.textures.new(f"tx_{obj.name}_{kind}_{seed}", kind)
    if hasattr(tx, "noise_scale"):
        tx.noise_scale = size
    if hasattr(tx, "noise_depth"):
        tx.noise_depth = depth
    if kind == "VORONOI":
        tx.distance_metric = "DISTANCE"
    dm = obj.modifiers.new("disp", "DISPLACE")
    dm.texture = tx
    dm.strength = strength
    dm.mid_level = 0.5
    dm.texture_coords = "GLOBAL" if seed == 0 else "OBJECT"
    if seed:
        e = bpy.data.objects.new(f"_seed{seed}", None)
        e.location = (seed * 13.7, seed * 7.3, seed * 3.1)
        bpy.context.scene.collection.objects.link(e)
        dm.texture_coords_object = e
    if apply:
        apply_modifiers(obj)
    return obj


def remesh(obj, voxel=0.5, apply=True):
    rm = obj.modifiers.new("remesh", "REMESH")
    rm.mode = "VOXEL"
    rm.voxel_size = voxel
    if apply:
        apply_modifiers(obj)
    return obj


def subsurf(obj, levels=2, apply=True):
    sm = obj.modifiers.new("sub", "SUBSURF")
    sm.levels = levels
    sm.render_levels = levels
    if apply:
        apply_modifiers(obj)
    return obj


def boolean(obj, cutter, op="DIFFERENCE", apply=True, hide=True):
    bm_ = obj.modifiers.new("bool", "BOOLEAN")
    bm_.operation = op
    bm_.object = cutter
    bm_.solver = "EXACT"
    try:
        bm_.material_mode = "TRANSFER"
    except Exception:
        pass
    if apply:
        apply_modifiers(obj)
    if hide:
        bpy.data.objects.remove(cutter, do_unlink=True)
    return obj


def smooth_all(obj, angle=40):
    for p in obj.data.polygons:
        p.use_smooth = True
    try:
        obj.data.set_sharp_from_angle(angle=math.radians(angle))
    except Exception:
        pass


def join(objs, name):
    """Join objects into one (keeps materials). Returns the joined object."""
    objs = [o for o in objs if o]
    mb = MB(name)
    for o in objs:
        mb.add_object(o)
    coll = objs[0].users_collection[0] if objs and objs[0].users_collection else None
    for o in objs:
        bpy.data.objects.remove(o, do_unlink=True)
    ob = mb.to_object(coll, uv=False, sharp_angle=None)
    return ob


def rockify(obj, amp=1.5, scale=0.06, flute=0.0, flute_scale=0.25, strata=0.0, strata_freq=1.4,
            seed=0, undercut=0.0, base_z=0.0, height=None, mask=None, smooth=2):
    """Displace a remeshed rock along vertex normals:
    fractal noise (overall form) + vertical fluting (wind/rain-cut grooves) + horizontal strata ridges.
    undercut pulls the base inward (mushroom / hoodoo erosion).
    mask(p) -> 0..1 scales the displacement (keep carved facades flat)."""
    from mathutils import noise
    off = Vector((seed * 31.7, seed * 17.3, seed * 7.9))
    me = obj.data
    zs = [v.co.z for v in me.vertices]
    z0, z1 = min(zs), max(zs)
    hh = height or max(z1 - z0, 1e-3)
    for v in me.vertices:
        p = v.co.copy()
        n = v.normal.copy()
        d = noise.fractal(p * scale + off, 0.55, 2.1, 6, noise_basis="PERLIN_NEW") * amp
        if flute:
            q = Vector((p.x * flute_scale, p.y * flute_scale, p.z * flute_scale * 0.08)) + off
            d += (abs(noise.noise(q, noise_basis="PERLIN_NEW")) - 0.25) * flute
        if strata:
            w = noise.noise(p * 0.04 + off, noise_basis="PERLIN_NEW") * 2.5
            d += (abs(math.sin(p.z * strata_freq + w)) - 0.5) * strata
        if mask is not None:
            d *= mask(p)
        if undercut:
            f = max(0.0, 1.0 - (p.z - z0) / (0.25 * hh))
            horiz = Vector((n.x, n.y, 0))
            p -= horiz * undercut * f * f
        v.co = p + n * d
    me.update()
    if smooth:
        relax(obj, smooth, 0.5)
    return obj


def relax(obj, iterations=2, factor=0.5):
    """Laplacian smoothing (removes displacement spikes / fold-overs)."""
    import bmesh as _bm
    bm = _bm.new()
    bm.from_mesh(obj.data)
    for _ in range(iterations):
        new = {}
        for v in bm.verts:
            if not v.link_edges:
                continue
            avg = Vector((0, 0, 0))
            for e in v.link_edges:
                avg += e.other_vert(v).co
            avg /= len(v.link_edges)
            new[v] = v.co.lerp(avg, factor)
        for v, co in new.items():
            v.co = co
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return obj


def ground_clamp(obj, z=0.0):
    """Flatten everything below z onto the ground plane (robust replacement for a boolean trim)."""
    for v in obj.data.vertices:
        if v.co.z < z:
            v.co.z = z
    obj.data.update()
    return obj


def tri_count(obj):
    return sum(len(p.vertices) - 2 for p in obj.data.polygons)


# ----------------------------------------------------------------- export ---
def export_fbx(objs, path, armature=False, colors="SRGB"):
    """colors: vertex-colour encoding. Terrain layer weights use LINEAR (raw 0..1 factors in Unreal)."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    objs = objs if isinstance(objs, (list, tuple)) else [objs]
    for o in bpy.context.scene.objects:
        o.select_set(False)
    sel = []
    for o in objs:
        sel.append(o)
        sel.extend(o.children_recursive)
    for o in sel:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.export_scene.fbx(
        filepath=path, use_selection=True, apply_unit_scale=True, apply_scale_options="FBX_SCALE_NONE",
        object_types={"MESH", "ARMATURE", "EMPTY"} if armature else {"MESH"},
        mesh_smooth_type="FACE", use_mesh_modifiers=True, add_leaf_bones=False,
        use_armature_deform_only=True, bake_anim=False, path_mode="STRIP",
        axis_forward="-Z", axis_up="Y", use_tspace=True, colors_type=colors)
    for o in sel:
        o.select_set(False)
    print("exported", os.path.relpath(path, ROOT))


def export_glb(objs, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    objs = objs if isinstance(objs, (list, tuple)) else [objs]
    for o in bpy.context.scene.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
        for c in o.children_recursive:
            c.select_set(True)
    bpy.ops.export_scene.gltf(filepath=path, use_selection=True, export_format="GLB",
                              export_image_format="JPEG", export_jpeg_quality=85)


# ----------------------------------------------------------------- render ---
def setup_render(res=(1600, 900), samples=64, exposure=0.0):
    if os.environ.get("SR_PREVIEW"):          # fast iteration mode
        res = (res[0] * 3 // 5, res[1] * 3 // 5)
        samples = max(16, samples // 3)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    try:
        sc.cycles.denoiser = "OPENIMAGEDENOISE"
    except Exception:
        pass
    sc.cycles.max_bounces = 6
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    try:   # keeps saturated emissives (tail lights, neon) from turning pastel like AgX does
        sc.view_settings.view_transform = "Khronos PBR Neutral"
    except Exception:
        sc.view_settings.view_transform = "AgX"
    sc.view_settings.exposure = exposure
    sc.render.film_transparent = False


def world_sky(sun_elev=25.0, sun_rot=40.0, strength=1.0):
    w = bpy.data.worlds.new("Sky")
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    sky = nt.nodes.new("ShaderNodeTexSky")
    for t in ("MULTIPLE_SCATTERING", "NISHITA", "SINGLE_SCATTERING", "HOSEK_WILKIE"):
        try:
            sky.sky_type = t
            break
        except Exception:
            continue
    if hasattr(sky, "sun_disc"):        # the scene's sun lamp provides direct light + shadows
        sky.sun_disc = False
    for attr, val in (("sun_elevation", math.radians(sun_elev)), ("sun_rotation", math.radians(sun_rot)),
                      ("altitude", 500.0), ("air_density", 1.2), ("dust_density", 2.5)):
        if hasattr(sky, attr):
            setattr(sky, attr, val)
    bg.inputs["Strength"].default_value = strength
    nt.links.new(sky.outputs[0], bg.inputs[0])
    nt.links.new(bg.outputs[0], out.inputs[0])
    return w


def world_color(top=(0.01, 0.015, 0.04), horizon=(0.08, 0.05, 0.08), strength=1.0):
    """Simple gradient sky (for night scenes)."""
    w = bpy.data.worlds.new("Grad")
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])   # world 'Generated' = view direction
    nt.links.new(sep.outputs["Z"], ramp.inputs[0])
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = tuple(horizon) + (1,)
    ramp.color_ramp.elements[1].position = 0.45
    ramp.color_ramp.elements[1].color = tuple(top) + (1,)
    nt.links.new(ramp.outputs[0], bg.inputs[0])
    bg.inputs["Strength"].default_value = strength
    nt.links.new(bg.outputs[0], out.inputs[0])
    return w


def sun(direction_deg=(50, 0, 40), strength=3.0, color=(1, 0.95, 0.88), angle=1.0, name="Sun"):
    l = bpy.data.lights.new(name, "SUN")
    l.energy = strength
    l.color = color
    l.angle = math.radians(angle)
    o = bpy.data.objects.new(name, l)
    o.rotation_euler = [math.radians(a) for a in direction_deg]
    bpy.context.scene.collection.objects.link(o)
    return o


def point_light(loc, power=1000, color=(1, 0.8, 0.6), radius=0.2, kind="POINT", name="L"):
    l = bpy.data.lights.new(name, kind)
    l.energy = power
    l.color = color
    if hasattr(l, "shadow_soft_size"):
        l.shadow_soft_size = radius
    o = bpy.data.objects.new(name, l)
    o.location = loc
    bpy.context.scene.collection.objects.link(o)
    return o


def area_light(loc, target, power=500, size=5, color=(1, 1, 1)):
    l = bpy.data.lights.new("Area", "AREA")
    l.energy = power
    l.size = size
    l.color = color
    o = bpy.data.objects.new("Area", l)
    o.location = loc
    bpy.context.scene.collection.objects.link(o)
    look_at(o, target)
    return o


def look_at(obj, target):
    d = Vector(target) - Vector(obj.location)
    obj.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def camera(loc, target, lens=35, name="Cam"):
    c = bpy.data.cameras.new(name)
    c.lens = lens
    c.clip_end = 20000
    o = bpy.data.objects.new(name, c)
    o.location = loc
    bpy.context.scene.collection.objects.link(o)
    look_at(o, target)
    bpy.context.scene.camera = o
    return o


def render(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("rendered", os.path.relpath(path, ROOT))


def ground(size=400, m=None, z=0.0, name="Ground"):
    mb = MB(name)
    mb.poly([(-size, -size, z), (size, -size, z), (size, size, z), (-size, size, z)], m or mat("Sand", (1, 1, 1), tex="Sand", tile=6))
    return mb.to_object()


def apply_scale(obj, s):
    s = (s, s, s) if isinstance(s, (int, float)) else s
    obj.data.transform(Matrix.Diagonal(Vector(tuple(s) + (1.0,))))
    obj.scale = (1, 1, 1)
    return obj


def bounds(objs):
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    for o in objs:
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            lo = Vector((min(lo.x, w.x), min(lo.y, w.y), min(lo.z, w.z)))
            hi = Vector((max(hi.x, w.x), max(hi.y, w.y), max(hi.z, w.z)))
    return lo, hi


def export_kit(objs, kit, glb=False, blend=True):
    """Export each object to assets/<kit>/<name>.fbx with its origin at the world origin,
    write assets/<kit>/kit.json (tris + size per asset) and an editable <kit>_kit.blend."""
    folder = os.path.join(ROOT, "assets", kit)
    os.makedirs(folder, exist_ok=True)
    info = {}
    for o in objs:
        bpy.context.view_layer.update()
        lo, hi = bounds([o])
        info[o.name] = dict(tris=tri_count(o), size_m=[round(hi.x - lo.x, 2), round(hi.y - lo.y, 2), round(hi.z - lo.z, 2)],
                            materials=[m.name for m in o.data.materials])
    with open(os.path.join(folder, "kit.json"), "w") as f:
        json.dump(info, f, indent=1)
    for o in objs:
        loc = o.location.copy()
        o.location = (0, 0, 0)
        bpy.context.view_layer.update()
        export_fbx(o, os.path.join(folder, f"{o.name}.fbx"))
        if glb:
            export_glb(o, os.path.join(folder, "glb", f"{o.name}.glb"))
        o.location = loc
    bpy.context.view_layer.update()
    if blend:
        layout_grid(objs, spacing=6.0, row_width=400.0)
        for im in bpy.data.images:          # keep texture paths relative to the .blend
            if im.filepath:
                im.filepath = bpy.path.relpath(im.filepath, start=folder) if hasattr(bpy.path, "relpath") else im.filepath
        save_blend(os.path.join(folder, f"{kit}_kit.blend"))


def layout_grid(objs, spacing=4.0, row_width=80.0):
    """Lay objects out left-to-right in rows (for lineup renders)."""
    x = y = 0.0
    row_depth = 0.0
    for o in objs:
        bpy.context.view_layer.update()
        lo, hi = bounds([o])
        w, d = hi.x - lo.x, hi.y - lo.y
        if x > 0 and x + w > row_width:
            x = 0.0
            y += row_depth + spacing
            row_depth = 0.0
        o.location.x += x - lo.x
        o.location.y += y - lo.y
        x += w + spacing
        row_depth = max(row_depth, d)
    bpy.context.view_layer.update()


def frame_camera(objs, direction=(1, -1, 0.5), lens=35, margin=1.08, target_z=None):
    """Place a camera looking along -direction so every object fits in frame."""
    bpy.context.view_layer.update()
    lo, hi = bounds(objs)
    c = (lo + hi) / 2
    if target_z is not None:
        c.z = target_z
    r = (hi - lo).length / 2
    sc = bpy.context.scene
    aspect = sc.render.resolution_x / sc.render.resolution_y
    fov = 2 * math.atan(36 / 2 / lens)              # horizontal sensor fit (36 mm)
    fov_v = 2 * math.atan(math.tan(fov / 2) / aspect)
    dist = r * margin / math.sin(min(fov, fov_v) / 2)
    d = Vector(direction).normalized()
    return camera(tuple(c + d * dist), tuple(c), lens)


def inst(obj, loc=(0, 0, 0), rot=(0, 0, 0), scale=1.0, name=None):
    """Linked duplicate (shares mesh data) - cheap instancing for dioramas."""
    o = obj.copy()
    o.name = name or obj.name + "_i"
    o.location = loc
    o.rotation_euler = [math.radians(a) for a in rot]
    o.scale = (scale, scale, scale) if isinstance(scale, (int, float)) else scale
    o.hide_render = False
    o.hide_viewport = False
    (obj.users_collection[0] if obj.users_collection else bpy.context.scene.collection).objects.link(o)
    return o


def hide(obj):
    obj.hide_render = True
    obj.hide_viewport = True


def import_glb(path, loc=(0, 0, 0), rot_z=0.0):
    """Import a glTF (e.g. a car preview) and place its root objects."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    roots = [o for o in new if o.parent is None]
    for r in roots:
        r.location = Vector(loc) + Vector(r.location)
        r.rotation_euler.z += math.radians(rot_z)
    return new


def save_blend(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=path, compress=True)
