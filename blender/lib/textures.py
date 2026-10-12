"""Seamless (tileable) PBR texture generator for Sahara Racers.

Pure numpy: every texture is built from periodic noise (FFT-filtered white noise
and periodic Voronoi), so all of them tile perfectly in Unreal and Blender.

Run:  python blender/lib/textures.py  [out_dir]
Writes T_<Name>_D.png (base colour), _N.png (OpenGL normal, Unreal: flip green
is handled by the import script), _R.png (roughness) and _E.png (emissive) where needed.
"""
import math
import os
import sys

import numpy as np
from PIL import Image
from scipy.spatial import cKDTree

N = 1024
RNG = np.random.default_rng(7)


# ---------------------------------------------------------------- noise ----
def fbm(n=N, beta=2.0, lo=1.0, hi=None, seed=None, aniso=(1.0, 1.0)):
    """Periodic fractal noise in [0,1]. beta = spectral slope, aniso stretches x/y."""
    r = np.random.default_rng(seed) if seed is not None else RNG
    w = r.standard_normal((n, n))
    fx = np.fft.fftfreq(n)[None, :] * n * aniso[0]
    fy = np.fft.fftfreq(n)[:, None] * n * aniso[1]
    f = np.sqrt(fx * fx + fy * fy)
    f[0, 0] = 1
    filt = 1.0 / f ** (beta / 2)
    filt[f < lo] = 0
    if hi:
        filt *= np.exp(-(f / hi) ** 2)
    out = np.real(np.fft.ifft2(np.fft.fft2(w) * filt))
    out -= out.min()
    return out / max(out.max(), 1e-9)


def voronoi(n=N, cells=24, seed=1, jitter=1.0):
    """Periodic Voronoi: returns (F1 distance, F2-F1 edge distance, cell id), distances in px."""
    r = np.random.default_rng(seed)
    g = int(np.ceil(np.sqrt(cells)))
    base = (np.stack(np.meshgrid(np.arange(g), np.arange(g)), -1).reshape(-1, 2) + 0.5) / g
    pts = (base + (r.random(base.shape) - 0.5) * jitter / g) % 1.0
    pts *= n
    tree = cKDTree(pts, boxsize=n)
    yy, xx = np.mgrid[0:n, 0:n]
    q = np.stack([xx.ravel() + 0.5, yy.ravel() + 0.5], -1)
    d, i = tree.query(q, k=2)
    f1 = d[:, 0].reshape(n, n)
    edge = (d[:, 1] - d[:, 0]).reshape(n, n)
    return f1, edge, i[:, 0].reshape(n, n)


def normal_from_height(h, strength=4.0):
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5 * strength
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5 * strength
    nx, ny, nz = -dx, dy, np.ones_like(h)  # OpenGL (+Y up)
    l = np.sqrt(nx * nx + ny * ny + nz * nz)
    return np.stack([nx / l, ny / l, nz / l], -1) * 0.5 + 0.5


def blur(a, px):
    """Periodic gaussian blur (FFT)."""
    n = a.shape[0]
    f = np.fft.fftfreq(n)
    g = np.exp(-2 * (np.pi * px) ** 2 * (f[None, :] ** 2 + f[:, None] ** 2))
    if a.ndim == 2:
        return np.real(np.fft.ifft2(np.fft.fft2(a) * g))
    return np.stack([blur(a[..., c], px) for c in range(a.shape[2])], -1)


def ramp(t, stops):
    """Colour ramp: stops = [(pos, (r,g,b)), ...] with rgb 0-255."""
    t = np.clip(t, 0, 1)
    pos = np.array([s[0] for s in stops])
    cols = np.array([s[1] for s in stops], float) / 255.0
    out = np.empty(t.shape + (3,))
    for c in range(3):
        out[..., c] = np.interp(t, pos, cols[:, c])
    return out


def save(out, name, d=None, n=None, r=None, e=None):
    def w(arr, suffix, mode="RGB"):
        a = np.clip(arr, 0, 1)
        img = Image.fromarray((a * 255 + 0.5).astype(np.uint8), mode if a.ndim == 3 else "L")
        if suffix in ("D", "N"):   # colour + normal as high quality JPG (small repo), masks as PNG
            img.save(os.path.join(out, f"T_{name}_{suffix}.jpg"), quality=92, subsampling=0)
        else:
            img.save(os.path.join(out, f"T_{name}_{suffix}.png"), optimize=True)
    if d is not None: w(d, "D")
    if n is not None: w(n, "N")
    if r is not None: w(r, "R")
    if e is not None: w(e, "E")
    print("texture", name)


# ------------------------------------------------------------- materials ---
def sand(out):
    warp = fbm(beta=3.2, seed=11)
    yy = np.mgrid[0:N, 0:N][0] / N
    ripple = np.sin((yy * 22 + warp * 3.0) * 2 * np.pi)            # 22 ripples / tile (periodic)
    ripple = np.sign(ripple) * np.abs(ripple) ** 0.6
    grain = fbm(beta=0.6, seed=12)
    big = fbm(beta=3.0, seed=13)
    h = ripple * 0.35 + grain * 0.25 + big * 0.6
    col = ramp(big * 0.7 + ripple * 0.12 + 0.2,
               [(0, (196, 146, 92)), (0.5, (222, 176, 118)), (1, (240, 204, 150))])
    col *= (0.92 + grain[..., None] * 0.12)
    save(out, "Sand", col, normal_from_height(h, 3), 0.85 + grain * 0.12)


def sandstone_strata(out):
    """AlUla / Hegra sandstone: warm tan with subtle bedding (along U, so V = world height),
    vertical desert-varnish streaks and pitting."""
    yy, xx = np.mgrid[0:N, 0:N] / N
    warp = fbm(beta=3.0, seed=21)
    v = yy + warp * 0.08
    band = (np.sin(v * 2 * np.pi * 7) * 0.5 + 0.5) * 0.55 + (np.sin(v * 2 * np.pi * 19 + 1) * 0.5 + 0.5) * 0.45
    detail = fbm(beta=1.4, seed=22)
    big = fbm(beta=3.2, seed=24)
    streak = np.clip((fbm(beta=2.6, seed=25, aniso=(1.0, 7.0)) - 0.5) * 2.2, 0, 1)   # desert varnish runs
    pits, edge, _ = voronoi(cells=500, seed=23)
    pits = np.clip(pits / 16, 0, 1)
    t = band * 0.28 + detail * 0.32 + big * 0.4
    col = ramp(t, [(0, (150, 92, 58)), (0.35, (188, 124, 78)), (0.65, (212, 156, 104)), (1, (230, 190, 142))])
    col *= (1 - 0.38 * streak[..., None]) * (0.86 + 0.14 * pits[..., None])
    col[..., 2] *= 1 - 0.1 * streak                     # varnish is slightly purple-brown
    h = band * 0.25 + detail * 0.45 + pits * 0.3 - streak * 0.2
    save(out, "SandstoneStrata", col, normal_from_height(h, 5), 0.88 - detail * 0.08)


def rock(out):
    """Asir granite / generic mountain rock."""
    a = fbm(beta=2.4, seed=31)
    b = fbm(beta=1.0, seed=32)
    f1, edge, _ = voronoi(cells=60, seed=33, jitter=0.9)
    crack = np.clip(edge / 4, 0, 1)
    col = ramp(a * 0.8 + b * 0.2, [(0, (70, 64, 58)), (0.5, (112, 102, 92)), (1, (150, 140, 126))])
    col *= (0.7 + 0.3 * crack[..., None])
    h = a * 0.7 + b * 0.2 + crack * 0.3
    save(out, "Rock", col, normal_from_height(h, 7), 0.75 + b * 0.2)


def asphalt(out):
    a = fbm(beta=0.4, seed=41)
    b = fbm(beta=2.8, seed=42)
    f1, _, ids = voronoi(cells=9000, seed=43)
    agg = np.clip(1 - f1 / 4.5, 0, 1) * (np.random.default_rng(44).random(ids.max() + 1)[ids] > 0.6)
    v = 0.15 + a * 0.08 + b * 0.06 + agg * 0.12
    col = np.stack([v, v, v * 1.03], -1)
    h = a * 0.4 + agg * 0.6
    save(out, "Asphalt", col, normal_from_height(h, 3), 0.8 - agg * 0.25 + b * 0.1)


def road_lanes(out):
    """3-lane highway, 1 tile = 12 m wide (U) x 12 m long (V). Dashed lane lines, solid edges."""
    base = np.array(Image.open(os.path.join(out, "T_Asphalt_D.jpg")), float) / 255
    rough = np.array(Image.open(os.path.join(out, "T_Asphalt_R.png")), float) / 255
    yy, xx = np.mgrid[0:N, 0:N]
    u = xx / N * 12.0
    vv = yy / N * 12.0
    paint = np.zeros((N, N))
    for x0 in (0.35, 11.65):                                  # solid edge lines 15 cm
        paint = np.maximum(paint, (np.abs(u - x0) < 0.075).astype(float))
    for x0 in (4.0, 8.0):                                     # dashed lane lines 3 m on / 3 m off
        paint = np.maximum(paint, ((np.abs(u - x0) < 0.06) & ((vv % 6.0) < 3.0)).astype(float))
    wear = fbm(beta=1.0, seed=45)
    paint *= np.clip(wear * 1.6, 0.55, 1)
    col = base * (1 - paint[..., None]) + np.array([0.92, 0.92, 0.88]) * paint[..., None]
    save(out, "RoadLanes", col, None, rough * (1 - paint) + 0.55 * paint)


def coral_stone(out):
    """Jeddah Al-Balad coral-stone plaster: off-white, porous, weathered."""
    a = fbm(beta=2.6, seed=51)
    b = fbm(beta=0.8, seed=52)
    f1, _, ids = voronoi(cells=2500, seed=53)
    pore = np.clip(1 - f1 / 3.2, 0, 1) * (np.random.default_rng(54).random(ids.max() + 1)[ids] > 0.55)
    stain = np.clip((fbm(beta=3.2, seed=55, aniso=(0.6, 3)) - 0.55) * 2.5, 0, 1)
    col = ramp(a * 0.6 + b * 0.4, [(0, (205, 194, 172)), (0.6, (228, 220, 202)), (1, (240, 235, 222))])
    col *= (1 - 0.35 * pore[..., None]) * (1 - 0.18 * stain[..., None])
    h = a * 0.4 + b * 0.2 - pore * 0.6
    save(out, "CoralStone", col, normal_from_height(h, 4), 0.88 + b * 0.1)


def mud_plaster(out):
    """Najdi / Asiri mud-straw plaster."""
    a = fbm(beta=2.4, seed=61)
    b = fbm(beta=0.9, seed=62)
    straw = np.clip((fbm(beta=0.5, seed=63, aniso=(0.12, 1)) - 0.7) * 4, 0, 1)
    col = ramp(a * 0.7 + b * 0.3, [(0, (138, 96, 62)), (0.5, (170, 124, 82)), (1, (196, 152, 106))])
    col = col * (1 - straw[..., None] * 0.1) + np.array([0.86, 0.74, 0.5]) * straw[..., None] * 0.1
    h = a * 0.6 + b * 0.3 + straw * 0.2
    save(out, "MudPlaster", col, normal_from_height(h, 5), 0.93 - b * 0.05)


def stone_masonry(out):
    """Asir / Rijal Almaa dry-stone coursing: irregular blocks in rows, dark mortar."""
    n = N
    rows = 10
    h = np.zeros((n, n))
    col = np.zeros((n, n, 3))
    r = np.random.default_rng(71)
    yy, xx = np.mgrid[0:n, 0:n]
    noise = fbm(beta=1.3, seed=72)
    row_h = n // rows
    for ri in range(rows):
        y0 = ri * row_h
        x = r.integers(0, n)
        widths = []
        total = 0
        while total < n:
            w = int(r.uniform(0.8, 2.2) * row_h)
            widths.append(w)
            total += w
        scale = n / total
        for w in widths:
            w = max(8, int(w * scale))
            x0 = x
            x = x + w
            m = (yy >= y0) & (yy < y0 + row_h)
            dx = (xx - x0) % n
            m &= dx < w
            # rounded block profile
            cy = (yy - y0 - row_h / 2) / (row_h / 2)
            cx = (dx - w / 2) / (w / 2)
            prof = np.clip(1 - np.maximum(np.abs(cx) ** 6, np.abs(cy) ** 6), 0, 1) ** 0.35
            h = np.where(m, prof * (0.8 + 0.2 * noise), h)
            tone = r.uniform(0.75, 1.15)
            hue = r.choice([0, 1, 2])
            base = np.array([[118, 104, 92], [96, 90, 86], [134, 116, 96]][hue]) / 255 * tone
            col = np.where(m[..., None], base * (0.85 + 0.3 * noise[..., None]), col)
    mortar = h < 0.08
    col[mortar] = np.array([60, 52, 46]) / 255
    save(out, "StoneMasonry", col, normal_from_height(h, 9), 0.9 - h * 0.12)


def concrete(out):
    a = fbm(beta=2.2, seed=81)
    b = fbm(beta=0.5, seed=82)
    v = 0.62 + a * 0.12 + b * 0.05
    col = np.stack([v, v * 0.99, v * 0.96], -1)
    save(out, "Concrete", col, normal_from_height(a * 0.5 + b * 0.5, 2), 0.82 + b * 0.1)


def wood_painted(out):
    """Neutral weathered painted wood (tinted per material: teal/green/brown rawasheen)."""
    yy, xx = np.mgrid[0:N, 0:N] / N
    warp = fbm(beta=3, seed=91, aniso=(1, 0.15))
    grain = np.sin((xx * 60 + warp * 6) * 2 * np.pi) * 0.5 + 0.5
    chips = np.clip((fbm(beta=1.6, seed=92) - 0.66) * 6, 0, 1)
    paint = 0.82 + 0.1 * grain
    wood = np.stack([0.42 + 0.1 * grain, 0.3 + 0.07 * grain, 0.2 + 0.05 * grain], -1)
    col = np.stack([paint] * 3, -1) * (1 - chips[..., None]) + wood * chips[..., None]
    h = grain * 0.3 - chips * 0.5
    save(out, "WoodPainted", col, normal_from_height(h, 3), 0.7 + chips * 0.2)


def _facade(out, name, seed, floor_on_p, win_on_lit, win_on_dark):
    """Office curtain wall at night. 1 tile = 8 bays (3 m) x 6 floors (4 m) = 24 x 24 m.
    Windows light up floor by floor (real offices), mostly cool white, some warm."""
    r = np.random.default_rng(seed)
    bays, floors = 8, 6
    yy, xx = np.mgrid[0:N, 0:N]
    bw, fh = N / bays, N / floors
    bx, fy = xx % bw, yy % fh
    ci, cj = (yy // fh).astype(int), (xx // bw).astype(int)
    mull = (bx < 3) | (bx > bw - 3)
    slab = fy > fh * 0.80                     # spandrel at the bottom of each floor band (image y down)
    glass = ~(mull | slab)
    col = np.zeros((N, N, 3))
    refl = fbm(beta=2.5, seed=seed + 1)
    col[...] = (np.array([0.04, 0.06, 0.085]) * (0.75 + 0.5 * refl[..., None]))
    col[mull] = [0.22, 0.23, 0.25]
    col[slab] = [0.1, 0.1, 0.11]
    floor_on = r.random(floors) < floor_on_p
    temps = np.array([[0.82, 0.9, 1.0], [1.0, 0.84, 0.62], [0.95, 0.95, 0.9]])
    floor_t = r.choice(3, size=floors, p=[0.6, 0.28, 0.12])
    on = np.where(floor_on[:, None], r.random((floors, bays)) < win_on_lit, r.random((floors, bays)) < win_on_dark)
    level = r.uniform(0.55, 1.0, (floors, bays)) * np.where(floor_on[:, None], 1.0, 0.7)
    blind = r.random((floors, bays)) < 0.18      # lowered blinds: only the lower part glows
    em = np.zeros((N, N, 3))
    lit = on[ci, cj] & glass
    vert = fy / (fh * 0.8)                        # 0 = top of window, 1 = sill
    grad = 1.0 - 0.35 * vert
    bl = np.where(blind[ci, cj] & (vert < 0.45), 0.25, 1.0)
    em[lit] = (temps[floor_t[ci]] * (level[ci, cj] * grad * bl)[..., None])[lit]
    rough = np.where(glass, 0.06, 0.5)
    save(out, name, col, None, rough, em)


def facade_night(out):
    _facade(out, "FacadeNight", 101, 0.72, 0.9, 0.12)   # busy office tower / street blocks


def facade_tower(out):
    _facade(out, "FacadeTower", 202, 0.35, 0.75, 0.06)  # landmark glass towers: mostly dark glass


def metal_panels(out):
    """Future-city white composite panels with seams."""
    yy, xx = np.mgrid[0:N, 0:N]
    seam = ((xx % 256) < 3) | ((yy % 128) < 3)
    a = fbm(beta=2.0, seed=111)
    v = 0.86 + 0.06 * a
    col = np.stack([v, v, v * 1.01], -1)
    col[seam] = 0.35
    h = np.where(seam, 0.0, 1.0)
    h = blur(h, 1.2)
    save(out, "MetalPanels", col, normal_from_height(h, 6), np.where(seam, 0.6, 0.25 + 0.1 * a))


def terrace_grass(out):
    """Asir terraced fields / juniper ground cover."""
    a = fbm(beta=2.0, seed=121)
    b = fbm(beta=0.4, seed=122)
    dirt = np.clip((fbm(beta=2.8, seed=123) - 0.6) * 3, 0, 1)
    col = ramp(a * 0.6 + b * 0.4, [(0, (54, 78, 34)), (0.5, (82, 108, 46)), (1, (120, 132, 66))])
    col = col * (1 - dirt[..., None]) + np.array([0.42, 0.33, 0.24]) * dirt[..., None]
    save(out, "TerraceGrass", col, normal_from_height(b * 0.6 + a * 0.4, 3), 0.92 * np.ones((N, N)))


def hex_mesh(out):
    """Honeycomb grille (racing intake mesh). Dark holes, satin metal frame."""
    cx = 12
    a = N / cx
    h = a * math.sqrt(3) / 2
    ny = int(round(N / h / 2)) * 2
    h = N / ny                                     # tiny vertical stretch so it tiles exactly
    pts = np.array([((i + 0.5 * (j % 2)) * a, j * h) for j in range(ny) for i in range(cx)])
    tree = cKDTree(pts, boxsize=N)
    yy, xx = np.mgrid[0:N, 0:N]
    q = np.stack([xx.ravel() + 0.5, yy.ravel() + 0.5], -1)
    d, _ = tree.query(q, k=2)
    edge = (d[:, 1] - d[:, 0]).reshape(N, N)
    frame = np.clip(1 - edge / 9.0, 0, 1)
    hgt = frame ** 0.7
    col = np.stack([0.02 + 0.5 * frame] * 3, -1)
    save(out, "HexMesh", col, normal_from_height(hgt, 10), 0.85 - 0.45 * frame)


ALL = [facade_tower, hex_mesh, sand, sandstone_strata, rock, asphalt, road_lanes, coral_stone, mud_plaster,
       stone_masonry, concrete, wood_painted, facade_night, metal_panels, terrace_grass]

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "..", "assets", "textures")
    os.makedirs(out, exist_ok=True)
    only = sys.argv[2:] if len(sys.argv) > 2 else None
    for fn in ALL:
        if only and fn.__name__ not in only:
            continue
        fn(out)
