"""Sahara Racers - race tracks on heightfield terrain.

A Track is a centripetal Catmull-Rom spline through control points (CP). Each CP carries:
    p      (x, y) metres                 w      road width (m)
    z      absolute height or None (= follow the smoothed terrain)
    dz     extra height added to the ground-following profile (ramps, crests)
    bank   roll in degrees (+ raises the left edge: use + for right-hand turns)
    L / R  edge style for the segment that starts here:
           jersey | guardrail | wall | railing | glow | berm | rock | none
    surf   road surface material key (see SURFACES)
    tags   set of segment tags: tunnel, gap (jump - no road), curbs, nocarve, bridge
    deck   bridge style: highway | metro | pier | stone | future
Shortcuts are open tracks whose first/last CP sit on the main track (joined smoothly).
"""
import json
import math
import os

import numpy as np

import sr
from mathutils import Vector

UP = np.array([0.0, 0.0, 1.0])


def CP(x, y, w=14.0, z=None, dz=0.0, bank=0.0, L=None, R=None, surf=None, tags=(), deck=None):
    return dict(p=(float(x), float(y)), w=w, z=z, dz=dz, bank=bank, L=L, R=R, surf=surf, tags=set(tags), deck=deck)


def _ss(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)


def catmull_rom(pts, closed=True, per_seg=40, alpha=0.5, phantom=None):
    """Centripetal Catmull-Rom. Returns dense points (M,2) and param (segment index + local t)."""
    P = [np.array(p, float) for p in pts]
    n = len(P)
    if closed:
        get = lambda i: P[i % n]  # noqa: E731
        segs = n
    else:
        a = phantom[0] if phantom else 2 * P[0] - P[1]
        b = phantom[1] if phantom else 2 * P[-1] - P[-2]
        ext = [np.array(a, float)] + P + [np.array(b, float)]
        get = lambda i: ext[i + 1]  # noqa: E731
        segs = n - 1
    out, par = [], []
    for i in range(segs):
        p0, p1, p2, p3 = get(i - 1), get(i), get(i + 1), get(i + 2)

        def tj(ti, a_, b_):
            return ti + max(np.linalg.norm(b_ - a_), 1e-6) ** alpha
        t0 = 0.0
        t1 = tj(t0, p0, p1)
        t2 = tj(t1, p1, p2)
        t3 = tj(t2, p2, p3)
        for k in range(per_seg):
            t = t1 + (t2 - t1) * k / per_seg
            A1 = (t1 - t) / (t1 - t0) * p0 + (t - t0) / (t1 - t0) * p1
            A2 = (t2 - t) / (t2 - t1) * p1 + (t - t1) / (t2 - t1) * p2
            A3 = (t3 - t) / (t3 - t2) * p2 + (t - t2) / (t3 - t2) * p3
            B1 = (t2 - t) / (t2 - t0) * A1 + (t - t0) / (t2 - t0) * A2
            B2 = (t3 - t) / (t3 - t1) * A2 + (t - t1) / (t3 - t1) * A3
            C = (t2 - t) / (t2 - t1) * B1 + (t - t1) / (t2 - t1) * B2
            out.append(C)
            par.append(i + k / per_seg)
    if not closed:
        out.append(P[-1])
        par.append(float(n - 1))
    return np.array(out), np.array(par)


def circ_smooth(a, sigma_samples, closed=True):
    if sigma_samples < 0.5:
        return a
    r = int(3 * sigma_samples)
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma_samples) ** 2)
    k /= k.sum()
    if closed:
        ext = np.concatenate([a[-r:], a, a[:r]])
    else:
        ext = np.concatenate([np.full(r, a[0]), a, np.full(r, a[-1])])
    return np.convolve(ext, k, mode="valid")


SURFACES = {}      # filled by materials(): key -> material


def materials():
    if SURFACES:
        return SURFACES
    M = SURFACES
    M["asphalt"] = sr.mat("Track_Asphalt", (1, 1, 1), rough=0.75, tex="TrackAsphalt", tile=1.0)
    M["asphalt_old"] = sr.mat("Track_AsphaltWorn", (0.95, 0.93, 0.9), rough=0.8, tex="TrackAsphalt", tile=1.0)
    M["sand"] = sr.mat("Track_PackedSand", (1, 1, 1), rough=0.95, tex="TrackSand", tile=1.0)
    M["cobble"] = sr.mat("Track_Cobble", (0.95, 0.9, 0.82), rough=0.85, tex="StoneMasonry", tile=3.0)
    M["glow"] = sr.mat("Track_Glow", (1, 1, 1), rough=0.3, metal=0.3, tex="TrackGlow", tile=1.0, emit_str=6.0)
    M["metal"] = sr.mat("Track_MetalDeck", (0.6, 0.62, 0.66), rough=0.45, metal=0.8, tex="MetalPanels", tile=4.0)
    M["dirt"] = sr.mat("Track_Dirt", (0.75, 0.62, 0.5), rough=0.95, tex="MudPlaster", tile=4.0)
    M["shoulder"] = sr.mat("Track_Shoulder", (0.75, 0.7, 0.62), rough=0.9, tex="Concrete", tile=2.0)
    M["concrete"] = sr.mat("Concrete", (1, 1, 1), tex="Concrete", tile=2.0)
    M["curb_r"] = sr.mat("Curb_Red", (0.7, 0.05, 0.04), rough=0.5)
    M["curb_w"] = sr.mat("Curb_White", (0.9, 0.9, 0.88), rough=0.5)
    M["steel"] = sr.mat("SteelGalvanised", (0.55, 0.56, 0.58), rough=0.45, metal=1.0)
    M["stone"] = sr.mat("Track_StoneWall", (0.95, 0.85, 0.72), rough=0.9, tex="StoneMasonry", tile=2.0)
    M["rock"] = sr.mat("AlUla_Sandstone", (1.0, 0.95, 0.92), rough=0.9, tex="SandstoneStrata", tile=11.0)
    M["rock_dark"] = sr.mat("VergeRock", (0.62, 0.48, 0.4), rough=0.9, tex="Rock", tile=1.5)
    M["glowline"] = sr.mat("Neon_Cyan", (0.1, 0.9, 1.0), emit=(0.1, 0.85, 1.0), emit_str=14, kind="emissive")
    M["white"] = sr.mat("Future_White", (0.92, 0.93, 0.95), rough=0.25, metal=0.1, coat=0.6, tex="MetalPanels", tile=3.0)
    M["tunnel"] = sr.mat("Tunnel_Lining", (0.8, 0.8, 0.78), rough=0.7, tex="Concrete", tile=3.0)
    M["tunnel_light"] = sr.mat("TunnelLight", (1.0, 0.85, 0.6), emit=(1.0, 0.8, 0.55), emit_str=10, kind="emissive")
    M["checker_w"] = sr.mat("Checker_White", (0.9, 0.9, 0.9), rough=0.5)
    M["checker_b"] = sr.mat("Checker_Black", (0.02, 0.02, 0.02), rough=0.5)
    M["reflector"] = sr.mat("ReflectorAmber", (0.9, 0.5, 0.1), emit=(1, 0.5, 0.1), emit_str=1.0)
    M["railing"] = sr.mat("Railing_White", (0.88, 0.88, 0.86), rough=0.35, metal=0.6)
    return M


# ------------------------------------------------------------------- track ---
class Track:
    def __init__(self, name, cps, closed=True, step=2.0, surf="asphalt", L="jersey", R="jersey",
                 kind="main", hidden=False, label=None):
        self.name, self.cps, self.closed, self.step = name, cps, closed, step
        self.kind, self.hidden, self.label = kind, hidden, label or name
        # carry styles forward: a CP without L/R/surf inherits the previous one
        cur = dict(L=L, R=R, surf=surf, deck="highway")
        for c in cps:
            for k in ("L", "R", "surf", "deck"):
                if c.get(k) is None:
                    c[k] = cur[k]
                cur[k] = c[k]
        self.phantom = None
        self.smooth_m = 20.0           # along-track smoothing of the ground-following height profile
        self.pillar_ok = None          # optional callable (x, y) -> bool: skip bridge pillars that would hit a road

    # -- geometry -----------------------------------------------------------
    def build(self, terrain, main=None):
        pts = [c["p"] for c in self.cps]
        dense, par = catmull_rom(pts, self.closed, phantom=self.phantom)
        seg = np.linalg.norm(np.diff(dense, axis=0, append=dense[:1] if self.closed else dense[-1:]), axis=1)
        if not self.closed:
            seg[-1] = 0
        s_dense = np.concatenate([[0], np.cumsum(seg[:-1])]) if not self.closed else np.concatenate([[0], np.cumsum(seg)])[:-1]
        total = float(s_dense[-1] + (seg[-1] if self.closed else 0))
        self.length = total
        N = max(4, int(total / self.step))
        S = np.linspace(0, total, N, endpoint=not self.closed)
        sd = s_dense if not self.closed else np.concatenate([s_dense, [total]])
        pd = par if not self.closed else np.concatenate([par, [len(pts)]])
        xd = dense[:, 0] if not self.closed else np.concatenate([dense[:, 0], dense[:1, 0]])
        yd = dense[:, 1] if not self.closed else np.concatenate([dense[:, 1], dense[:1, 1]])
        self.S = S
        self.P = np.stack([np.interp(S, sd, xd), np.interp(S, sd, yd)], -1)
        self.par = np.interp(S, sd, pd)
        # tangents
        if self.closed:
            T = np.roll(self.P, -1, 0) - np.roll(self.P, 1, 0)
        else:
            T = np.gradient(self.P, axis=0)
        self.T = T / np.maximum(np.linalg.norm(T, axis=1, keepdims=True), 1e-9)
        self.Nrm = np.stack([-self.T[:, 1], self.T[:, 0]], -1)     # left
        ncp = len(self.cps)
        k = np.floor(self.par).astype(int) % ncp
        k2 = (k + 1) % ncp if self.closed else np.minimum(k + 1, ncp - 1)
        u = _ss(self.par - np.floor(self.par))
        self.seg = k
        cp = self.cps
        w = np.array([c["w"] for c in cp], float)
        bank = np.array([c["bank"] for c in cp], float)
        dz = np.array([c["dz"] for c in cp], float)
        self.W = w[k] * (1 - u) + w[k2] * u
        self.bank = np.radians(bank[k] * (1 - u) + bank[k2] * u)
        self.dzp = dz[k] * (1 - u) + dz[k2] * u
        self.tag = [cp[i]["tags"] for i in k]
        self.Ls = [cp[i]["L"] for i in k]
        self.Rs = [cp[i]["R"] for i in k]
        self.surf = [cp[i]["surf"] for i in k]
        self.deck = [cp[i]["deck"] for i in k]
        # elevation: smoothed ground + overrides
        ground = terrain.sample(self.P[:, 0], self.P[:, 1])
        self.ground0 = ground.copy()
        zg = circ_smooth(ground, self.smooth_m / self.step, self.closed) + self.dzp
        zo = np.zeros(len(S))
        wo = np.zeros(len(S))
        zabs = [c["z"] for c in cp]
        for i in range(len(S)):
            a, b = k[i], k2[i]
            za, zb = zabs[a], zabs[b]
            t = u[i]
            if za is not None and zb is not None:
                zo[i], wo[i] = za * (1 - t) + zb * t, 1.0
            elif za is not None:
                zo[i], wo[i] = za, 1 - t
            elif zb is not None:
                zo[i], wo[i] = zb, t
        z = wo * (zo + self.dzp) + (1 - wo) * zg
        z = circ_smooth(z, 4.0 / self.step, self.closed)
        if main is not None and not self.closed:      # glue shortcut ends to the main track surface
            for end in (0, -1):
                zm = main.height_at(self.P[end])
                n_blend = int(30 / self.step)
                idx = np.arange(n_blend) if end == 0 else np.arange(len(z) - n_blend, len(z))
                f = 1 - _ss(np.arange(n_blend) / n_blend)
                f = f if end == 0 else f[::-1]
                z[idx] = zm * f + z[idx] * (1 - f)
        self.nomesh = np.zeros(len(S), bool)
        if main is not None and not self.closed:
            # where a shortcut still lies on the main road, don't mesh it (and keep it a hair below)
            from scipy.spatial import cKDTree
            d, j = cKDTree(main.P).query(self.P)
            self.nomesh = d + self.W / 2 < main.W[j] / 2 + 0.8
            over = d < main.W[j] / 2 + self.W / 2
            # where it overlaps the main road, sit exactly on the main's (banked) surface, a hair below it
            lat = np.einsum("ij,ij->i", self.P - main.P[j], main.Nrm[j])
            surf = main.Z[j] + lat * np.sin(main.bank[j])
            blend = np.clip(1.0 - (d - main.W[j] / 2) / (self.W / 2 + 4.0), 0, 1) * over
            z = z * (1 - blend) + (surf - 0.06) * blend
            self.bank = self.bank * (1 - blend) + main.bank[j] * blend
        self.Z = z
        self.edge_skip = np.zeros((2, len(S)), bool)      # [left, right] barrier openings (junctions)
        tun = np.array(["tunnel" in t for t in self.tag])
        gap = np.array(["gap" in t for t in self.tag])
        noc = np.array([("nocarve" in t) or ("bridge" in t) for t in self.tag])
        self.tunnel = tun
        self.gap = gap
        self.bridge = (~tun) & ((z - ground > 3.2) | noc | gap)
        return self

    def open_junctions(self, other, margin=1.5, dz=3.0):
        """Open this track's barriers where `other` (a shortcut) drives through them, and drop
        `other`'s own barriers where they would stand on this road."""
        from scipy.spatial import cKDTree
        t_other, t_self = cKDTree(other.P), cKDTree(self.P)
        road = ~other.gap
        for k, sg in ((0, 1), (1, -1)):
            q = self.P + self.Nrm * (sg * (self.W / 2 + 0.8))[:, None]
            d, j = t_other.query(q)
            self.edge_skip[k] |= (d < other.W[j] / 2 + margin) & road[j] & (np.abs(other.Z[j] - self.Z) < dz)
            q = other.P + other.Nrm * (sg * (other.W / 2 + 0.8))[:, None]
            d, j = t_self.query(q)
            other.edge_skip[k] |= (d < self.W[j] / 2 + margin) & (np.abs(self.Z[j] - other.Z) < dz)
        # widen the openings a little so the gap reads clearly
        for arr in (self.edge_skip, other.edge_skip):
            for k in range(2):
                a = arr[k]
                if a.any():
                    grow = np.convolve(a.astype(float), np.ones(5), mode="same") > 0
                    arr[k] = grow

    def height_at(self, xy):
        d = np.linalg.norm(self.P - np.array(xy), axis=1)
        return float(self.Z[int(np.argmin(d))])

    def nearest_s(self, xy):
        d = np.linalg.norm(self.P - np.array(xy), axis=1)
        return float(self.S[int(np.argmin(d))])

    def frame(self, s):
        """Position (x,y,z), tangent, left normal, width at arclength s."""
        i = int(np.clip(round(s / self.step), 0, len(self.S) - 1)) if not self.closed else int(round(s / self.step)) % len(self.S)
        p = self.P[i]
        return np.array([p[0], p[1], self.Z[i]]), self.T[i], self.Nrm[i], self.W[i], self.bank[i]

    # -- terrain interaction ------------------------------------------------
    def carve(self, terrain, falloff=18.0, shoulder=2.5, layer=None):
        sel = ~(self.bridge | self.tunnel)
        hw = self.W / 2 + shoulder + np.abs(np.sin(self.bank)) * self.W / 2
        drop = np.abs(np.sin(self.bank)) * self.W / 2
        terrain.carve(self.P[sel], self.Z[sel] - drop[sel], hw[sel], falloff=falloff, layer=layer)

    def cut_tunnel_holes(self, terrain, roof=7.5):
        """Open the hillside where tunnel tubes emerge (terrain between road and roof)."""
        if not self.tunnel.any():
            return
        sel = self.tunnel
        P, Z, W = self.P[sel], self.Z[sel], self.W[sel]
        from scipy.spatial import cKDTree
        tree = cKDTree(P)
        q = np.c_[terrain.X.ravel(), terrain.Y.ravel()]
        d, idx = tree.query(q, distance_upper_bound=float(W.max()) / 2 + 3)
        ok = np.isfinite(d)
        h = terrain.h.ravel()
        cut = np.zeros(len(q), bool)
        cut[ok] = (h[ok] > Z[idx[ok]] - 1.0) & (h[ok] < Z[idx[ok]] + roof + 3.5) & (d[ok] < W[idx[ok]] / 2 + 2.5)
        terrain.holes |= cut.reshape(terrain.h.shape)

    # -- meshes ---------------------------------------------------------------
    def section(self, i, offsets):
        """World points across the road at sample i for lateral offsets (+ = left), banked."""
        c = np.array([self.P[i][0], self.P[i][1], self.Z[i]])
        n = np.array([self.Nrm[i][0], self.Nrm[i][1], 0.0])
        b = self.bank[i]
        nb = n * math.cos(b) + UP * math.sin(b)
        return [c + nb * o for o in offsets]

    def build_meshes(self, map_name, chunk_len=420.0):
        """Road + skirts + curbs + barriers + bridges + tunnels, split into chunks. Returns objects."""
        M = materials()
        n = len(self.S)
        idx_all = np.arange(n)
        if self.closed:
            nchunks = max(1, int(round(self.length / chunk_len)))
            bounds = np.linspace(0, n, nchunks + 1).astype(int)
        else:
            nchunks = max(1, int(round(self.length / chunk_len)))
            bounds = np.linspace(0, n - 1, nchunks + 1).astype(int)
        objs = []
        for c in range(nchunks):
            i0, i1 = bounds[c], bounds[c + 1]
            rng = list(range(i0, i1 + 1))
            if self.closed:
                rng = [i % n for i in rng]
            nm = f"SM_{map_name}_{self.name}_{c + 1:02d}" if nchunks > 1 else f"SM_{map_name}_{self.name}"
            mb = sr.MB(nm)
            self._road(mb, rng, M)
            self._edges(mb, rng, M)
            self._bridges(mb, rng, M)
            self._tunnels(mb, rng, M)
            objs.append(mb.to_object(uv=True, sharp_angle=50))
        return objs

    def _runs(self, rng, pred):
        """Split index list into contiguous runs where pred(i) is True."""
        runs, cur = [], []
        for i in rng:
            if pred(i):
                cur.append(i)
            elif cur:
                runs.append(cur)
                cur = []
        if cur:
            runs.append(cur)
        return [r for r in runs if len(r) > 1]

    def _road(self, mb, rng, M):
        sub = 6
        for run in self._runs(rng, lambda i: not self.gap[i] and not self.nomesh[i]):
            grid, uvs = [], []
            for i in run:
                hw = self.W[i] / 2
                offs = [hw + 0.6] + [hw - self.W[i] * k / sub for k in range(sub + 1)] + [-hw - 0.6]
                pts = self.section(i, offs)
                pts[0] = pts[0] - UP * 1.6
                pts[-1] = pts[-1] - UP * 1.6
                grid.append([tuple(p) for p in pts])
                v = self.S[i] / 16.0
                uvs.append([(-0.04, v)] + [(k / sub, v) for k in range(sub + 1)] + [(1.04, v)])
            surf = [self.surf[i] for i in run]

            def mat(ii, k, surf=surf):
                if k == 0 or k == sub + 1:
                    return M["shoulder"]
                return M.get(surf[ii], M["asphalt"])
            mb.strip(grid, uvs, mat, smooth=True, keep=True)
        # curbs on the inside of tight corners (or where tagged)
        curv = np.zeros(len(self.S))
        a_, b_ = self.T[1:-1], self.T[2:]
        curv[1:-1] = (a_[:, 0] * b_[:, 1] - a_[:, 1] * b_[:, 0]) / self.step     # signed curvature (+ = left turn)
        for side in (1, -1):
            def want(i, side=side):
                tight = abs(curv[i]) > 1 / 90.0 and np.sign(curv[i]) == side
                return ((tight or "curbs" in self.tag[i]) and not self.gap[i] and not self.nomesh[i]
                        and self.surf[i] in ("asphalt", "glow", "asphalt_old"))
            for run in self._runs(rng, want):
                grid = []
                for i in run:
                    hw = self.W[i] / 2
                    o = [side * (hw - 1.1), side * (hw + 0.2)]
                    pts = self.section(i, o[::-1] if side > 0 else o)    # left->right order = faces up
                    grid.append([tuple(p + UP * 0.05) for p in pts])
                mb.strip(grid, None, lambda ii, k, run=run: M["curb_r"] if int(self.S[run[ii]] / 2.0) % 2 else M["curb_w"],
                         smooth=False, keep=True)

    def _edges(self, mb, rng, M):
        for side in ("L", "R"):
            styles = self.Ls if side == "L" else self.Rs
            sg = 1 if side == "L" else -1
            skip = self.edge_skip[0 if side == "L" else 1]
            for style in set(styles[i] for i in rng):
                if style in (None, "none"):
                    continue
                runs = self._runs(rng, lambda i: styles[i] == style and not self.gap[i] and not self.tunnel[i]
                                  and not self.nomesh[i] and not skip[i])
                for run in runs:
                    self._edge_run(mb, run, sg, style, M)

    PROFILES = {
        "jersey": ([(-0.3, 0), (0.3, 0), (0.3, 0.08), (0.2, 0.33), (0.08, 0.81), (-0.08, 0.81), (-0.2, 0.33), (-0.3, 0.08)], "concrete"),
        "wall": ([(-0.35, -0.5), (0.35, -0.5), (0.3, 1.2), (-0.3, 1.2)], "stone"),
        "glow": ([(-0.35, 0), (0.35, 0), (0.3, 0.6), (0.12, 0.9), (-0.12, 0.9), (-0.3, 0.6)], "white"),
        "berm": ([(-2.5, -0.4), (2.0, -0.4), (0.6, 0.9), (-0.6, 0.9)], "rock"),
    }

    def _edge_run(self, mb, run, sg, style, M):
        off_extra = {"jersey": 0.7, "wall": 0.8, "glow": 0.8, "berm": 2.4, "guardrail": 0.9, "railing": 0.8, "rock": 2.0}.get(style, 0.8)

        def base(i):
            hw = self.W[i] / 2
            p = self.section(i, [sg * (hw + off_extra)])[0]
            return p, np.array([self.Nrm[i][0], self.Nrm[i][1], 0.0]) * sg
        if style in self.PROFILES:
            prof, mk = self.PROFILES[style]
            rings = []
            for i in run:
                p, out = base(i)
                rings.append([tuple(p + out * y + UP * z) for y, z in prof])
            mb.loft(rings, M[mk], closed=True, cap_start=True, cap_end=True, smooth=False)
            if style == "glow":
                rings = []
                for i in run:
                    p, out = base(i)
                    rings.append([tuple(p - out * 0.32 + UP * z) for z in (0.62, 0.7)])
                mb.strip(rings, None, M["glowline"], smooth=False, keep=False)
        elif style in ("guardrail", "railing"):
            prof = [(0.0, 0.55), (-0.1, 0.6), (-0.04, 0.68), (-0.1, 0.76), (0.0, 0.81)] if style == "guardrail" else \
                   [(0.0, 1.0), (-0.06, 1.05), (0.0, 1.1), (0.06, 1.05)]
            rings = []
            for i in run:
                p, out = base(i)
                rings.append([tuple(p - out * y + UP * z) for y, z in prof])
            mb.loft(rings, M["steel"] if style == "guardrail" else M["railing"], closed=(style == "railing"),
                    cap_start=False, cap_end=False, smooth=True)
            if style == "railing":   # lower rails + balusters (seaside promenade)
                rings = []
                for i in run:
                    p, out = base(i)
                    rings.append([tuple(p + UP * z) for z in (0.25, 0.32)])
                mb.strip(rings, None, M["railing"], smooth=False, keep=False)
            post_every = 2.0 if style == "guardrail" else 1.5
            last = -1e9
            for i in run:
                if self.S[i] - last >= post_every:
                    p, out = base(i)
                    h = 0.85 if style == "guardrail" else 1.05
                    mb.box((0.1, 0.1, h + 0.4), tuple(p + UP * (h / 2 - 0.2)), m=M["steel"] if style == "guardrail" else M["railing"])
                    last = self.S[i]
        elif style == "rock":   # scattered angular rocks on the verge
            rnd = np.random.default_rng(int(self.S[run[0]]))
            last = -1e9
            gap = rnd.uniform(6, 14)
            for i in run:
                if self.S[i] - last >= gap:
                    p, out = base(i)
                    r = rnd.uniform(0.35, 0.9)
                    mb.sphere(r, tuple(p + out * rnd.uniform(0.5, 3) + UP * r * 0.15), rot=tuple(rnd.uniform(0, 90, 3)),
                              m=M["rock_dark"], seg=5, rings=3, scale=(1.0, rnd.uniform(0.6, 1.0), rnd.uniform(0.45, 0.7)))
                    last = self.S[i]
                    gap = rnd.uniform(6, 14)

    def _bridges(self, mb, rng, M):
        for run in self._runs(rng, lambda i: self.bridge[i] and not self.gap[i] and not self.nomesh[i]):
            style = self.deck[run[0]]
            # deck underside
            grid = []
            for i in run:
                hw = self.W[i] / 2 + 0.6
                pts = self.section(i, [-hw, hw])
                grid.append([tuple(p - UP * 1.6) for p in pts])
            mb.strip(grid, None, M["concrete"] if style != "future" else M["white"], smooth=False, keep=True)
            if style == "metro":   # U-trough parapets
                for sg in (1, -1):
                    rings = []
                    for i in run:
                        p = self.section(i, [sg * (self.W[i] / 2 + 0.3)])[0]
                        rings.append([tuple(p + UP * z + np.array([self.Nrm[i][0], self.Nrm[i][1], 0]) * sg * y)
                                      for y, z in ((0, -1.6), (0.35, -1.6), (0.35, 1.3), (0.0, 1.3))])
                    mb.loft(rings, M["concrete"], closed=True, cap_start=True, cap_end=True, smooth=False)
            # pillars
            spacing = {"highway": 26.0, "metro": 30.0, "pier": 14.0, "stone": 22.0, "future": 40.0}.get(style, 26.0)
            last = -1e9
            for i in run:
                if self.S[i] - last < spacing:
                    continue
                last = self.S[i]
                x, y = self.P[i]
                top = self.Z[i] - 1.6
                g = float(self.ground0[i]) - 1.0
                if top - g < 1.0:
                    continue
                if self.pillar_ok is not None and not self.pillar_ok(x, y):
                    last = -1e9
                    continue
                h = top - g
                yaw = math.degrees(math.atan2(self.T[i][1], self.T[i][0]))
                if style == "highway":
                    mb.box((1.6, 2.2, h), (x, y, g + h / 2), (0, 0, yaw), m=M["concrete"])
                    mb.box((2.0, self.W[i] * 0.85, 1.2), (x, y, top - 0.6), (0, 0, yaw), m=M["concrete"])
                elif style == "metro":
                    mb.cyl(1.3, h, (x, y, g + h / 2), m=M["concrete"], seg=16)
                    mb.cyl(2.8, 1.2, (x, y, top - 0.6), m=M["concrete"], seg=16, r2=1.4)
                elif style == "pier":
                    for sg in (1, -1):
                        nx, ny = self.Nrm[i]
                        o = sg * self.W[i] * 0.35
                        mb.cyl(0.35, h, (x + nx * o, y + ny * o, g + h / 2), m=M["concrete"], seg=10)
                elif style == "stone":
                    mb.box((3.0, self.W[i] + 1.2, h), (x, y, g + h / 2), (0, 0, yaw), m=M["stone"])
                elif style == "future":
                    mb.tube([(x, y, g), (x, y, g + h * 0.6), (x, y, top)], [1.6, 1.0, 2.2], M["white"], seg=14)
                    mb.box((0.3, self.W[i], 0.15), (x, y, top - 0.1), (0, 0, yaw), m=M["glowline"])

    def _tunnels(self, mb, rng, M):
        for run in self._runs(rng, lambda i: self.tunnel[i]):
            grid = []
            H = 7.0
            for i in run:
                hw = self.W[i] / 2 + 1.5
                c = np.array([self.P[i][0], self.P[i][1], self.Z[i]])
                n = np.array([self.Nrm[i][0], self.Nrm[i][1], 0.0])
                row = [c - n * hw - UP * 0.5, c - n * hw + UP * 3.5]
                for k in range(1, 12):
                    a = math.pi * k / 12
                    row.append(c - n * hw * math.cos(a) + UP * (3.5 + (H - 3.5) * math.sin(a)))
                row += [c + n * hw + UP * 3.5, c + n * hw - UP * 0.5]
                grid.append([tuple(p) for p in row])
            # rows run right->left, so the strip winding already faces into the tube
            mb.strip(grid, None, M["tunnel"], smooth=True, keep=True)
            last = -1e9
            for i in run:
                if self.S[i] - last >= 10:
                    c = np.array([self.P[i][0], self.P[i][1], self.Z[i] + H - 0.25])
                    yaw = math.degrees(math.atan2(self.T[i][1], self.T[i][0]))
                    mb.box((2.5, 0.4, 0.12), tuple(c), (0, 0, yaw), m=M["tunnel_light"])
                    last = self.S[i]
            # portals
            for i in (run[0], run[-1]):
                c = np.array([self.P[i][0], self.P[i][1], self.Z[i]])
                yaw = math.degrees(math.atan2(self.T[i][1], self.T[i][0]))
                hw = self.W[i] / 2 + 1.5
                for k in range(13):
                    a = math.pi * k / 12
                    n = np.array([self.Nrm[i][0], self.Nrm[i][1], 0.0])
                    p = c - n * (hw + 0.6) * math.cos(a) + UP * (3.5 + (H - 3.5 + 0.6) * math.sin(a))
                    mb.box((1.6, 1.0, 1.0), tuple(p), (0, -math.degrees(a) + 90, yaw - 90), m=M["stone"])
                for sg in (1, -1):
                    n = np.array([self.Nrm[i][0], self.Nrm[i][1], 0.0])
                    p = c + n * sg * (hw + 0.8) + UP * 1.5
                    mb.box((1.6, 1.4, 4.5), tuple(p), (0, 0, yaw), m=M["stone"])

    # -- data -------------------------------------------------------------------
    def samples_json(self, every=5.0):
        out = []
        k = max(1, int(round(every / self.step)))
        for i in range(0, len(self.S), k):
            x, y = self.P[i]
            yaw = math.degrees(math.atan2(self.T[i][1], self.T[i][0]))
            out.append(dict(s=round(float(self.S[i]), 1), x=round(float(x) * 100, 1), y=round(float(-y) * 100, 1),
                            z=round(float(self.Z[i]) * 100, 1), yaw=round(-yaw, 2), width=round(float(self.W[i]) * 100),
                            bank=round(float(-math.degrees(self.bank[i])), 2),
                            air=bool(self.gap[i]), tunnel=bool(self.tunnel[i]), bridge=bool(self.bridge[i])))
        return out


def ue_transform(p, yaw_deg):
    """Blender (m, CCW yaw) -> Unreal (cm, X fwd, Y right, yaw clockwise)."""
    return dict(x=round(float(p[0]) * 100, 1), y=round(float(-p[1]) * 100, 1), z=round(float(p[2]) * 100, 1),
                yaw=round(-float(yaw_deg), 2))


def gameplay(main, shortcuts, checkpoint_every=250.0, pickups=(), boosts=(), grid_spacing=8.0):
    """Checkpoints, start grid, card pickup rows and boost pads in Unreal coordinates."""
    cps = []
    s = 0.0
    while s < main.length - 50:
        p, t, n, w, b = main.frame(s)
        yaw = math.degrees(math.atan2(t[1], t[0]))
        cps.append(dict(index=len(cps), s=round(s, 1), width_cm=round(float(w) * 100 + 400), **ue_transform(p, yaw)))
        s += checkpoint_every
    grid = []
    for k in range(8):
        row, col = divmod(k, 2)
        p, t, n, w, b = main.frame((main.length - 12 - row * grid_spacing) % main.length)
        off = (w * 0.22) * (1 if col == 0 else -1)
        pos = p + np.array([n[0], n[1], 0]) * off + np.array([0, 0, 0.6])
        yaw = math.degrees(math.atan2(t[1], t[0]))
        grid.append(dict(slot=k + 1, **ue_transform(pos, yaw)))
    items = []
    for s in pickups:
        p, t, n, w, b = main.frame(s)
        yaw = math.degrees(math.atan2(t[1], t[0]))
        for lat in (-0.3, 0.0, 0.3):
            pos = p + np.array([n[0], n[1], 0]) * w * lat + np.array([0, 0, 1.2])
            items.append(dict(type="card", s=s, **ue_transform(pos, yaw)))
    for s in boosts:
        p, t, n, w, b = main.frame(s)
        yaw = math.degrees(math.atan2(t[1], t[0]))
        items.append(dict(type="boost", s=s, **ue_transform(p + np.array([0, 0, 0.05]), yaw)))
    return dict(checkpoints=cps, start_grid=grid, items=items)


def write_track_json(folder, map_name, main, shortcuts, extra):
    data = dict(map=map_name, units="Unreal cm, yaw in degrees (UE convention)", length_m=round(main.length, 1),
                main=main.samples_json(),
                shortcuts=[dict(name=s.name, label=s.label, hidden=s.hidden, length_m=round(s.length, 1),
                                joins_main_at_m=[round(main.nearest_s(s.P[0]), 1), round(main.nearest_s(s.P[-1]), 1)],
                                saves_m=round((main.nearest_s(s.P[-1]) - main.nearest_s(s.P[0])) % main.length - s.length, 1),
                                samples=s.samples_json()) for s in shortcuts])
    data.update(extra)
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, "track.json"), "w") as f:
        json.dump(data, f, indent=1)
    return data


def minimap(path, terrain, main, shortcuts, title="", water=None, size=1024):
    """Top-down map: hillshade + water + track (white), shortcuts (orange) and hidden ones (magenta)."""
    from PIL import Image, ImageDraw, ImageFont
    shade = terrain.hillshade(size)
    h = terrain.h[:: max(1, terrain.n // size), :: max(1, terrain.n // size)]
    base = np.stack([0.55 + 0.35 * shade, 0.5 + 0.32 * shade, 0.42 + 0.28 * shade], -1)
    if water is not None:
        wm = h < water
        base[wm] = np.array([0.12, 0.35, 0.5]) * (0.8 + 0.2 * shade[wm, None])
    img = Image.fromarray((np.flipud(base) * 255).astype(np.uint8)).resize((size, size))
    d = ImageDraw.Draw(img)

    def px(p):
        return ((p[0] + terrain.size / 2) / terrain.size * size, (terrain.size / 2 - p[1]) / terrain.size * size)
    for sc in shortcuts:
        col = (230, 60, 200) if sc.hidden else (255, 150, 30)
        pts = [px(p) for p in sc.P[::3]]
        for k in range(0, len(pts) - 1, 2):
            d.line([pts[k], pts[k + 1]], fill=col, width=6)
    pts = [px(p) for p in main.P[::2]] + [px(main.P[0])]
    d.line(pts, fill=(20, 20, 20), width=14)
    d.line(pts, fill=(250, 250, 245), width=8)
    sp = px(main.P[0])
    d.ellipse([sp[0] - 12, sp[1] - 12, sp[0] + 12, sp[1] + 12], fill=(40, 200, 90), outline=(0, 0, 0), width=3)
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 30)
    if title:
        d.rectangle([0, 0, size, 48], fill=(0, 0, 0))
        d.text((16, 8), title, font=f, fill=(255, 255, 255))
    f2 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
    d.rectangle([0, size - 40, size, size], fill=(0, 0, 0))
    d.text((16, size - 32), f"track {main.length / 1000:.2f} km   ", font=f2, fill=(250, 250, 245))
    d.text((250, size - 32), "── shortcut", font=f2, fill=(255, 150, 30))
    d.text((450, size - 32), "── hidden shortcut", font=f2, fill=(230, 60, 200))
    d.ellipse([720, size - 30, 740, size - 10], fill=(40, 200, 90))
    d.text((750, size - 32), "start", font=f2, fill=(250, 250, 245))
    img.save(path)
