"""Sahara Racers - automatic race-day dressing for any map (uses the 'life' kit).

trackside(m)  chevron boards round every tight corner (pointing the way), tyre stacks at the apexes,
              100/200 m braking boards, sponsor boards along the start straight, marshal posts, and
              spectator zones (crowds behind fences, flags, bunting, gazebos, food trucks, a car park,
              camera towers, floodlights at night) at the start and the most dramatic corners/jumps.
cluster(m, ...)  scatter a group of props round a point (camps, herds, picnics, beach umbrellas).
"""
import math
import random

import numpy as np

L = "life"
C = "common"


def _yaw(t):
    return math.degrees(math.atan2(t[1], t[0]))


class Occupancy:
    """Very small spatial check so dressing does not land on buildings or each other."""

    def __init__(self, m, radius_of=None):
        self.pts = [(p[2][0], p[2][1], 6.0) for p in m.place_list]

    def free(self, x, y, r):
        for (px, py, pr) in self.pts:
            if (x - px) ** 2 + (y - py) ** 2 < (r + pr) ** 2:
                return False
        return True

    def add(self, x, y, r):
        self.pts.append((x, y, r))


def corners(T, min_curv=1 / 75.0, min_len=18.0):
    """Corner runs on a track: list of dict(s0, s1, apex_s, sign (+1 left turn), max_curv)."""
    n = len(T.S)
    tt = T.T
    nxt = np.roll(tt, -1, 0) if T.closed else np.vstack([tt[1:], tt[-1:]])
    curv = (tt[:, 0] * nxt[:, 1] - tt[:, 1] * nxt[:, 0]) / T.step
    k = 4
    curv = np.convolve(np.concatenate([curv[-k:], curv, curv[:k]]), np.ones(2 * k + 1) / (2 * k + 1), "valid")
    tight = np.abs(curv) > min_curv
    out, i = [], 0
    while i < n:
        if tight[i]:
            j = i
            while j + 1 < n and tight[j + 1] and np.sign(curv[j + 1]) == np.sign(curv[i]):
                j += 1
            if (j - i) * T.step >= min_len:
                a = i + int(np.argmax(np.abs(curv[i:j + 1])))
                out.append(dict(s0=float(T.S[i]), s1=float(T.S[j]), apex_s=float(T.S[a]), sign=int(np.sign(curv[a])),
                                curv=float(abs(curv[a])), i0=i, i1=j))
            i = j + 1
        else:
            i += 1
    return out, curv


def trackside(m, spots=None, n_spots=3, night=False, sponsor_len=220.0, seed=7, chevrons=True, crowds=True):
    """Dress the main track. spots: extra list of lap distances for spectator zones."""
    T = m.main
    rnd = random.Random(seed)
    occ = Occupancy(m)
    cs, curv = corners(T)

    def frame(s):
        s = s % T.length
        i = int(round(s / T.step)) % len(T.S)
        return i, T.P[i], T.T[i], T.Nrm[i], T.W[i], T.Z[i], bool(T.bridge[i]), bool(T.tunnel[i] or T.gap[i])

    def z_at(i, x, y, bridge):
        return float(T.Z[i]) if bridge else None

    # chevrons on the outside of every tight corner, tyre stacks at the apex, braking boards
    for c in (cs if chevrons else []):
        out = -c["sign"]
        s = c["s0"] - 8
        while s <= c["s1"] + 8:
            i, p, t, n, w, z, br, skip = frame(s)
            q = p + n * out * (w / 2 + 2.8)
            if not skip and m.clearance(q[0], q[1]) > 1.8 and occ.free(q[0], q[1], 1.0):
                m.place(L, "SM_ChevronBoard", q[0], q[1], z=z_at(i, *q, br), yaw=_yaw(t) + (0 if c["sign"] > 0 else 180))
                occ.add(q[0], q[1], 1.0)
            s += 8.0
        i, p, t, n, w, z, br, skip = frame(c["apex_s"])
        for k in (-1, 0, 1):
            ii, pp, tt_, nn, ww, zz, br2, sk2 = frame(c["apex_s"] + k * 4)
            q = pp + nn * out * (ww / 2 + 4.6)
            if not sk2 and m.clearance(q[0], q[1]) > 3.0 and occ.free(q[0], q[1], 1.5):
                m.place(L, "SM_StackedTyres", q[0], q[1], z=z_at(ii, *q, br2), yaw=_yaw(tt_) + 90)
                occ.add(q[0], q[1], 1.5)
        before = curv[max(0, c["i0"] - int(220 / T.step)):c["i0"]]
        if len(before) and np.abs(before).max() < 1 / 300.0:          # long straight into it: braking boards
            for d, nm in ((100, "SM_DistanceBoard_100"), (200, "SM_DistanceBoard_200")):
                ii, pp, tt_, nn, ww, zz, br2, sk2 = frame(c["s0"] - d)
                q = pp + nn * out * (ww / 2 + 2.2)
                if not sk2 and m.clearance(q[0], q[1]) > 1.5:
                    m.place(L, nm, q[0], q[1], z=z_at(ii, *q, br2), yaw=_yaw(tt_))
    # sponsor boards along the start straight, both sides
    s = -sponsor_len
    k = 0
    while s < sponsor_len:
        for sg in (1, -1):
            i, p, t, n, w, z, br, skip = frame(s)
            q = p + n * sg * (w / 2 + 2.4)
            if not skip and m.clearance(q[0], q[1]) > 1.6 and occ.free(q[0], q[1], 2.0):
                m.place(L, f"SM_SponsorBoard_{(k % 4) + 1:02d}", q[0], q[1], z=z_at(i, *q, br), yaw=_yaw(t) + 90)
                occ.add(q[0], q[1], 2.0)
            k += 1
        s += 7.0
    # marshal posts every ~550 m on the outside of a corner
    last = -1e9
    for c in cs:
        if c["apex_s"] - last < 550:
            continue
        i, p, t, n, w, z, br, skip = frame(c["apex_s"] + 15)
        q = p + n * (-c["sign"]) * (w / 2 + 7.5)
        if not skip and not br and m.clearance(q[0], q[1]) > 5 and occ.free(q[0], q[1], 2.0):
            m.place(L, "SM_MarshalPost", q[0], q[1], yaw=_yaw(t) + (90 if c["sign"] < 0 else -90))
            occ.add(q[0], q[1], 2.0)
            last = c["apex_s"]
    # spectator zones: start/finish + the tightest long corners + any explicit spots
    if crowds:
        zones = [(0.0, 1), (0.0, -1)]
        for c in sorted(cs, key=lambda c: -(c["curv"] * (c["s1"] - c["s0"])))[:n_spots]:
            zones.append((c["apex_s"], -c["sign"]))
        for s in spots or []:
            zones.append((s, 0))
        heli = False
        for s, side in zones:
            sides = (side,) if side else (1, -1)
            for sg in sides:
                if spectator_zone(m, occ, s, sg, rnd, night=night, start=(s == 0.0)) and not heli:
                    i, p, t, n, w, z, br, skip = frame(s)
                    m.place(L, "SM_Helicopter", p[0] - n[0] * 30, p[1] - n[1] * 30, z=float(z) + 38, yaw=_yaw(t) + 30)
                    heli = True


def spectator_zone(m, occ, s, sg, rnd, night=False, start=False, segments=None):
    """Crowd fence segments along the road at lap distance s on side sg (+1 left), with a fan zone behind."""
    T = m.main
    segments = segments or rnd.randint(3, 5)
    placed = 0
    back = 9.5 if start else 12.0
    base = None
    for k in range(segments):
        ss = (s + (k - segments / 2 + 0.5) * 10.5) % T.length
        i = int(round(ss / T.step)) % len(T.S)
        if T.tunnel[i] or T.gap[i] or T.bridge[i]:
            continue
        p, t, n, w = T.P[i], T.T[i], T.Nrm[i], T.W[i]
        q = p + n * sg * (w / 2 + back)
        if m.clearance(q[0], q[1]) < back - 1.5 or not occ.free(q[0], q[1], 5.0):
            continue
        face = math.degrees(math.atan2(-n[1] * sg, -n[0] * sg))          # fence (+X) towards the road
        m.place(L, rnd.choice(["SM_CrowdCheer_10m", "SM_Crowd_10m"]), q[0], q[1], yaw=face + 90 - 90)
        occ.add(q[0], q[1], 5.0)
        placed += 1
        base = (q, n, t, face)
    if not placed:
        return False
    q, n, t, face = base
    behind = q + n * sg * 9
    for k, asset in enumerate(("SM_FlagPole", "SM_FlagPole")):
        r = q + t * (k * 2 - 1) * (segments * 5.5) + n * sg * 2
        if occ.free(r[0], r[1], 1.0) and m.clearance(r[0], r[1]) > 4:
            m.place(L, asset, r[0], r[1], yaw=rnd.uniform(0, 360))
            occ.add(r[0], r[1], 1.0)
    if occ.free(behind[0], behind[1], 9) and m.clearance(behind[0], behind[1]) > 8:
        m.place(L, "SM_Bunting_20m", behind[0] - n[0] * sg * 4, behind[1] - n[1] * sg * 4, yaw=math.degrees(math.atan2(t[1], t[0])))
        for k, asset in enumerate(rnd.sample(["SM_Gazebo_Green", "SM_Gazebo_Red", "SM_FoodTruck", "SM_Kiosk"], 3)):
            r = behind + t * (k - 1) * 9 + n * sg * 4
            if occ.free(r[0], r[1], 3.5) and m.clearance(r[0], r[1]) > 8:
                m.place(L, asset, r[0], r[1], yaw=face + 180 + rnd.uniform(-8, 8))
                occ.add(r[0], r[1], 3.5)
        cars = ["SM_Car_Sedan_White", "SM_Car_Sedan_Silver", "SM_Car_Sedan_Red", "SM_Car_SUV_White", "SM_Car_SUV_Black",
                "SM_Car_Pickup_White"]
        for row in range(2):                                  # spectators' car park
            for k in range(6):
                r = behind + n * sg * (12 + row * 7) + t * (k - 2.5) * 3.2
                if occ.free(r[0], r[1], 1.6) and m.clearance(r[0], r[1]) > 10:
                    m.place(L, rnd.choice(cars), r[0], r[1], yaw=face + 90 + rnd.uniform(-4, 4))
                    occ.add(r[0], r[1], 1.6)
        r = q - t * (segments * 5.5 + 6)
        if occ.free(r[0], r[1], 2.0) and m.clearance(r[0], r[1]) > 5:
            m.place(L, "SM_CameraTower", r[0], r[1], yaw=face)
            occ.add(r[0], r[1], 2.0)
        if night:
            for k in (-1, 1):
                r = q + t * k * (segments * 5.5 + 2) + n * sg * 4
                if occ.free(r[0], r[1], 1.0):
                    m.place(L, "SM_Floodlight", r[0], r[1], yaw=face + 90)
                    occ.add(r[0], r[1], 1.0)
    return True


def cluster(m, kit, assets, cx, cy, count, radius, seed=1, clearance=6.0, max_slope=0.5, yaw=None, scale=(0.9, 1.1),
            min_spacing=2.0, z=None):
    """Scatter `count` props within `radius` of (cx, cy) (camps, herds, picnics, beach rows)."""
    rnd = random.Random(seed)
    return m.scatter(kit, assets, count, (cx - radius, cx + radius, cy - radius, cy + radius), clearance=clearance,
                     seed=rnd.randint(0, 10 ** 6), max_slope=max_slope,
                     mask=lambda x, y: (x - cx) ** 2 + (y - cy) ** 2 < radius * radius, min_spacing=min_spacing,
                     scale=scale, yaw=yaw)


def people(m, cx, cy, count, radius, seed=1, clearance=3.0, kinds=("SM_Person_Thobe", "SM_Person_Abaya", "SM_Person_Casual",
                                                                    "SM_Person_Kid")):
    return cluster(m, L, list(kinds), cx, cy, count, radius, seed=seed, clearance=clearance, min_spacing=1.2,
                   scale=(0.95, 1.05))


def city_grid(m, bounds, mask, block=120.0, street=16.0, angle=0.0, lamps=("riyadh", "SM_StreetLight_KFR"),
              lamp_every=48.0, clear=7.0):
    """Lay a street grid (asphalt with lane markings) inside the map wherever `mask(x, y)` allows and the race
    track is clear, line it with street lights, and return the building lots [(x, y, yaw, size)].
    Street meshes are merged into SM_<Map>_Far_Streets_<k> (sit 6 cm on the terrain, no collision needed)."""
    t = m.terrain
    a = math.radians(angle)
    c, s_ = math.cos(a), math.sin(a)
    x0, x1, y0, y1 = bounds
    half = t.size / 2 - 6
    span = max(x1 - x0, y1 - y0) * 1.5
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    slope = t.slope()

    def ok(x, y):
        if not (x0 <= x <= x1 and y0 <= y <= y1) or abs(x) > half or abs(y) > half or not mask(x, y):
            return False
        j, i = int(y + t.size / 2), int(x + t.size / 2)
        return slope[j, i] < 0.18 and m.clearance(x, y) > street / 2 + clear

    def to_xy(u, v):
        return cx + u * c - v * s_, cy + u * s_ + v * c
    runs = []
    lines = np.arange(-span / 2, span / 2 + 1, block)
    for horiz in (True, False):
        for g in lines:
            cur = []
            for w in np.arange(-span / 2, span / 2 + 1, 6.0):
                u, v = (w, g) if horiz else (g, w)
                x, y = to_xy(u, v)
                if ok(x, y):
                    cur.append((x, y))
                else:
                    if len(cur) > 12:
                        runs.append((np.array(cur), horiz))
                    cur = []
            if len(cur) > 12:
                runs.append((np.array(cur), horiz))
    # lots: cell centres that are clear of the race track
    lots = []
    for gu in lines[:-1] + block / 2:
        for gv in lines[:-1] + block / 2:
            x, y = to_xy(gu, gv)
            if ok(x, y) and m.clearance(x, y) > block / 2 and all(ok(*to_xy(gu + du, gv + dv)) for du, dv in
                                                                    ((-block / 3, 0), (block / 3, 0), (0, -block / 3), (0, block / 3))):
                lots.append((x, y, angle, block - street))
    # street lights along the right-hand kerb of every street
    if lamps:
        for pts, horiz in runs:
            d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))]
            dirv = np.array([c, s_]) if horiz else np.array([-s_, c])
            nrm = np.array([-dirv[1], dirv[0]])
            for dd in np.arange(10, d[-1] - 5, lamp_every):
                k = int(np.searchsorted(d, dd))
                q = pts[min(k, len(pts) - 1)] - nrm * (street / 2 + 1.0)
                if m.clearance(q[0], q[1]) > 4:
                    m.place(lamps[0], lamps[1], q[0], q[1], yaw=math.degrees(math.atan2(nrm[1], nrm[0])))

    def build(mm):
        import sr
        from backdrop import Merged
        mat = sr.mat("CityStreet", (1, 1, 1), rough=0.8, tex="RoadLanes", tile=1.0)
        side = sr.mat("Concrete", (1, 1, 1), tex="Concrete", tile=2.0)
        mg = Merged(f"SM_{m.name}_Far_Streets")
        for pts, horiz in runs:
            dirv = np.array([c, s_]) if horiz else np.array([-s_, c])
            nrm = np.array([-dirv[1], dirv[0]])                      # left of the travel direction
            z = t.sample(pts[:, 0], pts[:, 1]) + 0.06
            d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))]
            grid, uvs, kerb_l, kerb_r = [], [], [], []
            for p, zz, dd in zip(pts, z, d):
                l = p + nrm * street / 2
                r = p - nrm * street / 2
                grid.append([(l[0], l[1], zz), (r[0], r[1], zz)])
                uvs.append([(0.0, dd / 16.0), (1.0, dd / 16.0)])
                for arr, sg in ((kerb_l, 1), (kerb_r, -1)):
                    a_ = p + nrm * sg * (street / 2)
                    b_ = p + nrm * sg * (street / 2 + 2.5)
                    arr.append([(b_[0], b_[1], zz + 0.15), (a_[0], a_[1], zz + 0.15)] if sg > 0 else
                               [(a_[0], a_[1], zz + 0.15), (b_[0], b_[1], zz + 0.15)])
            mb = mg._mb(pts[:, 0].mean(), pts[:, 1].mean())
            mb.strip(grid, uvs, mat, smooth=False, keep=True)
            mb.strip(kerb_l, None, side, smooth=False, keep=True)
            mb.strip(kerb_r, None, side, smooth=False, keep=True)
        return mg.objects()
    m.far_detail.append(build)
    return lots


def fill_lots(m, lots, plan, seed=3, occ=None):
    """Put buildings on city lots. plan: list of (weight, fn(m, x, y, yaw, size, rnd))."""
    rnd = random.Random(seed)
    occ = occ or Occupancy(m)
    weights = [w for w, _ in plan]
    for (x, y, yaw, size) in lots:
        if not occ.free(x, y, size * 0.35):
            continue
        fn = rnd.choices([f for _, f in plan], weights)[0]
        fn(m, x, y, yaw, size, rnd)
        occ.add(x, y, size * 0.45)


def lot_quads(x, y, yaw, size, n=4):
    """Sub-plot centres inside a lot (2x2), rotated with the grid."""
    a = math.radians(yaw)
    c, s_ = math.cos(a), math.sin(a)
    o = size / 4
    pts = [(-o, -o), (o, -o), (-o, o), (o, o)][:n]
    return [(x + u * c - v * s_, y + u * s_ + v * c) for u, v in pts]


def parking(m, x, y, yaw, size, rnd, cars=None):
    cars = cars or ["SM_Car_Sedan_White", "SM_Car_Sedan_Silver", "SM_Car_Sedan_Red", "SM_Car_SUV_White",
                    "SM_Car_SUV_Black", "SM_Car_Pickup_White"]
    a = math.radians(yaw)
    c, s_ = math.cos(a), math.sin(a)
    for row in range(-2, 3):
        for k in range(-5, 6):
            if rnd.random() < 0.35:
                continue
            u, v = k * 3.0, row * 9.0
            m.place(L, rnd.choice(cars), x + u * c - v * s_, y + u * s_ + v * c, yaw=yaw + 90 + rnd.uniform(-3, 3))
