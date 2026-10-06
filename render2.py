"""Immersive Interactive Warm Up v2 - 3D-skeleton silhouette + sparkly worlds (1080p30, 8 min)."""
import math, subprocess, sys, wave, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops
import imageio_ffmpeg

W, H, FPS = 1920, 1080, 30
OUT = os.path.dirname(os.path.abspath(__file__))
IMPACT = "/System/Library/Fonts/Supplemental/Impact.ttf"
if not os.path.exists(IMPACT):
    IMPACT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts", "Anton-Regular.ttf")
FF = imageio_ffmpeg.get_ffmpeg_exe()

# ================================================================ timeline
INTRO, PREP, WORK, OUTRO = 8.0, 8.0, 30.0, 16.0
EXS = [  # key, label, cycle seconds, world
    ("run", "RUN IN PLACE", 0.72, 0),
    ("jacks", "JUMPING JACKS", 1.1, 0),
    ("circles", "ARM CIRCLES", 1.2, 0),
    ("squat", "SQUATS", 2.4, 0),
    ("knees", "HIGH KNEES", 0.62, 1),
    ("punch", "SKY PUNCHES", 0.9, 1),
    ("shuffle", "SIDE SHUFFLE", 2.4, 1),
    ("reach", "JUMP & REACH", 2.0, 1),
    ("kicks", "BUTT KICKS", 0.7, 2),
    ("skater", "SKATER HOPS", 1.8, 2),
    ("bend", "SIDE BENDS", 3.6, 2),
    ("breath", "BIG BREATHS", 5.0, 2),
]
WORLDS = ["CANDY LAND RUN", "JUNGLE RUN", "SNOW RUN"]
TOTAL = INTRO + len(EXS) * (PREP + WORK) + OUTRO
NF = int(TOTAL * FPS)


def segment(t):
    if t < INTRO:
        return "intro", 0, t, INTRO
    t2 = t - INTRO
    i = int(t2 // (PREP + WORK))
    if i >= len(EXS):
        return "outro", len(EXS) - 1, t2 - len(EXS) * (PREP + WORK), OUTRO
    lt = t2 - i * (PREP + WORK)
    return ("prep", i, lt, PREP) if lt < PREP else ("work", i, lt - PREP, WORK)


# ================================================================ pose model
# angles in degrees. sides r_/l_: sf shoulder flex (fwd), sa shoulder abduction (out), el elbow,
# hf hip flex, ha hip abduction, kn knee flex, an toes-down angle (absolute)
SIDE = ["sf", "sa", "el", "hf", "ha", "kn", "an"]
GLOB = ["dx", "dy", "pt", "pl", "sl", "ss", "st", "hn", "ht", "hs"]
KEYS = GLOB + ["r_" + k for k in SIDE] + ["l_" + k for k in SIDE]
IDX = {k: i for i, k in enumerate(KEYS)}
BASE = dict(sl=3, r_sa=8, l_sa=8, r_el=14, l_el=14, r_ha=4, l_ha=4, r_kn=5, l_kn=5, r_sf=4, l_sf=4)


def P(**kw):
    v = np.zeros(len(KEYS))
    for k, x in BASE.items():
        v[IDX[k]] = x
    for k, x in kw.items():
        if k.startswith("x_"):  # both sides
            v[IDX["r_" + k[2:]]] = x
            v[IDX["l_" + k[2:]]] = x
        else:
            v[IDX[k]] = x
    return v


def mirror(v):
    m = v.copy()
    for k in SIDE:
        m[IDX["r_" + k]], m[IDX["l_" + k]] = v[IDX["l_" + k]], v[IDX["r_" + k]]
    for k in ("dx", "pt", "pl", "ss", "st", "ht", "hs"):
        m[IDX[k]] = -v[IDX[k]]
    return m


def sstep(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def keyframes(ph, keys):
    """keys: list of (phase, pose) cyclic; smoothstep between neighbours."""
    ph %= 1.0
    for j in range(len(keys)):
        t0, p0 = keys[j]
        t1, p1 = keys[(j + 1) % len(keys)]
        if t1 <= t0:
            t1 += 1.0
        x = ph if ph >= t0 else ph + 1.0
        if t0 <= x < t1:
            return p0 + (p1 - p0) * sstep((x - t0) / (t1 - t0))
    return keys[0][1]


def lift(x):
    return max(0.0, math.sin(2 * math.pi * x)) ** 1.3


def run_like(ph, kind):
    lr, ll = lift(ph), lift(ph + 0.5)
    w = math.sin(2 * math.pi * (ph - 0.05))  # arm swing, lags legs a little
    big = kind == "knees"
    if kind == "kicks":
        hf, kn, an = -6, 128, 35
    elif big:
        hf, kn, an = 92, 100, 30
    else:
        hf, kn, an = 52, 78, 25
    amp = 55 if big else 40
    v = P(dy=(0.06 if big else 0.035) * (lr + ll) ** 0.8,
          dx=-0.02 * (lr - ll), pl=5 * (lr - ll), pt=-4 * w, st=7 * w, ht=-6 * w, sl=3 if big else 7,
          hn=2 * (lr + ll),
          r_sf=-amp * w + 10, l_sf=amp * w + 10, r_el=78 + 18 * max(0, -w), l_el=78 + 18 * max(0, w), x_sa=14,
          r_hf=hf * lr - 6 * ll + 4, l_hf=hf * ll - 6 * lr + 4, r_kn=10 + kn * lr, l_kn=10 + kn * ll,
          r_an=an * lr, l_an=an * ll, x_ha=4)
    if kind == "kicks":
        v[IDX["r_hf"]], v[IDX["l_hf"]] = 3 - 9 * lr, 3 - 9 * ll
    return v


def jacks(ph):
    def open_(x):
        x %= 1.0
        if x < 0.08: return 0.0
        if x < 0.42: return sstep((x - 0.08) / 0.34)
        if x < 0.58: return 1.0
        if x < 0.92: return 1 - sstep((x - 0.58) / 0.34)
        return 0.0
    def air(x):
        x %= 1.0
        if 0.08 <= x < 0.42: return math.sin(math.pi * (x - 0.08) / 0.34)
        if 0.58 <= x < 0.92: return math.sin(math.pi * (x - 0.58) / 0.34)
        return 0.0
    o, oa, a = open_(ph), open_(ph - 0.035), air(ph)
    return P(dy=0.09 * a, x_sa=10 + 160 * oa, x_el=12 + 25 * math.sin(math.pi * oa), x_sf=10 * math.sin(math.pi * oa),
             x_ha=3 + 17 * o, x_kn=6 + 16 * (1 - a), x_hf=4 + 6 * (1 - a), x_an=22 * a, hn=-4 * oa, sl=2)


def circles(ph):
    th = 2 * math.pi * ph
    return P(x_sa=86 + 16 * math.cos(th), x_sf=4 + 16 * math.sin(th), x_el=6, x_ha=9, x_kn=7,
             dy=0.006 * math.sin(2 * th), sl=2, hn=1.5 * math.sin(th))


K_SQUAT = [
    (0.00, P(x_sf=6)),
    (0.42, P(x_hf=88, x_kn=108, sl=32, x_sf=86, x_sa=12, x_el=6, x_ha=13, hn=-14)),
    (0.55, P(x_hf=90, x_kn=110, sl=33, x_sf=88, x_sa=12, x_el=6, x_ha=13, hn=-15)),
    (0.93, P(x_sf=8, sl=1)),
]

GUARD = dict(x_sf=48, x_sa=22, x_el=128, x_ha=12, x_kn=18, x_hf=12, sl=8)


def punch(ph):
    def prof(x):
        x %= 1.0
        if x >= 0.5: return 0.0
        u = x / 0.5
        if u < 0.28: return 1 - (1 - u / 0.28) ** 3
        if u < 0.42: return 1.0
        return 1 - sstep((u - 0.42) / 0.5)
    pr, pl = prof(ph), prof(ph + 0.5)
    v = P(**GUARD)
    for s, p in (("r_", pr), ("l_", pl)):
        v[IDX[s + "sf"]] = 48 + (86 - 48) * p
        v[IDX[s + "sa"]] = 22 - 28 * p
        v[IDX[s + "el"]] = 128 * (1 - p) + 4 * p
    v[IDX["st"]] = 22 * (pr - pl)
    v[IDX["pt"]] = 8 * (pr - pl)
    v[IDX["ht"]] = -10 * (pr - pl)
    v[IDX["dy"]] = 0.012 * (pr + pl)
    v[IDX["r_kn"]] = 18 + 8 * pl
    v[IDX["l_kn"]] = 18 + 8 * pr
    return v


def shuffle(ph):
    steps = 3  # shuffle steps per direction
    u = ph % 1.0
    half = 0 if u < 0.5 else 1
    lu = (u % 0.5) / 0.5  # 0..1 within one direction
    sp = lu * steps
    k, f = int(sp), sp - int(sp)
    xs = (k + sstep(f)) / steps  # stepped progress
    dirn = 1 if half == 0 else -1
    x = (-0.42 + 0.84 * xs) * dirn
    open_ = math.sin(math.pi * f)  # legs open mid-step
    a = math.sin(math.pi * f)
    v = P(dx=x, dy=0.045 * a, x_kn=24 - 8 * a, x_hf=18, sl=16, ss=-5 * dirn, x_sf=38 + 8 * a, x_sa=16, x_el=88,
          x_ha=8 + 14 * open_, x_an=10 * a, hn=-4)
    return v


K_REACH = [
    (0.00, P(x_sf=6)),
    (0.26, P(x_hf=72, x_kn=96, sl=36, x_sf=-48, x_el=16, x_ha=9, hn=-10)),
    (0.38, P(dy=0.06, x_hf=6, x_kn=4, x_an=38, sl=4, x_sf=150, x_sa=18, x_el=8, hn=-12)),
    (0.50, P(dy=0.33, x_hf=12, x_kn=26, x_an=26, sl=0, x_sf=172, x_sa=16, x_el=4, hn=-16)),
    (0.62, P(dy=0.0, x_hf=16, x_kn=20, x_an=5, x_sf=120, x_sa=20, x_el=10, hn=-6)),
    (0.72, P(x_hf=48, x_kn=64, sl=22, x_sf=34, x_sa=14, x_el=20, x_ha=7)),
    (0.92, P(x_sf=8)),
]

_SK_LAND = P(dx=0.48, dy=0, sl=28, ss=6, st=-14, pt=-6,
             r_hf=44, r_kn=50, r_ha=6, l_hf=-18, l_kn=74, l_ha=-20, l_an=34,
             l_sf=62, l_sa=-20, l_el=34, r_sf=-38, r_sa=14, r_el=20, hn=-6)
_SK_HOLD = _SK_LAND.copy()
_SK_HOLD[IDX['sl']] = 31
_SK_HOLD[IDX['r_kn']] = 58
_SK_HOLD[IDX['r_hf']] = 50
_SK_AIR = P(dx=0.0, dy=0.2, sl=18, x_hf=24, x_kn=40, x_ha=10, x_an=24, x_sf=22, x_sa=16, x_el=30, hn=-6)
K_SKATER = [(0.00, _SK_LAND), (0.16, _SK_HOLD), (0.34, _SK_AIR), (0.50, mirror(_SK_LAND)),
            (0.66, mirror(_SK_HOLD)), (0.84, _SK_AIR)]

_BEND_R = P(ss=30, dx=-0.05, pl=-4, l_sa=168, l_el=26, l_sf=6, r_sa=4, r_el=6, r_sf=2, x_ha=11, hs=8)
K_BEND = [(0.00, P(x_ha=11, x_sa=8)), (0.20, _BEND_R), (0.32, _BEND_R + (P(ss=3) - P())),
          (0.50, P(x_ha=11, x_sa=8)), (0.70, mirror(_BEND_R)), (0.82, mirror(_BEND_R + (P(ss=3) - P())))]

_BR_UP = P(x_sa=166, x_el=14, x_sf=8, dy=0.035, x_an=24, sl=-5, hn=-14, x_ha=6)
K_BREATH = [(0.00, P(x_ha=6)), (0.42, _BR_UP), (0.55, _BR_UP), (0.97, P(x_ha=6))]


def wave_pose(ph, t):
    s = math.sin(2 * math.pi * ph)
    sway = math.sin(2 * math.pi * t / 2.6)
    return P(dx=0.025 * sway, pl=3 * sway, ss=-2 * sway, r_sa=140 + 16 * s, r_el=30 + 10 * s, r_sf=12,
             l_sa=9, l_el=16, r_kn=5 + 6 * max(0, -sway), l_kn=5 + 6 * max(0, sway), hs=4 + 3 * s)


def cheer_pose(ph):
    a = max(0.0, math.sin(2 * math.pi * ph))
    land = 1 - a
    return P(dy=0.16 * a ** 0.9, x_sa=150 + 10 * a, x_sf=18, x_el=24 + 30 * land, x_kn=6 + 26 * land ** 3,
             x_hf=6 + 18 * land ** 3, x_an=20 * a, hn=-12)


def pose(key, ph, t=0.0):
    if key in ("run", "knees", "kicks"): v = run_like(ph, key)
    elif key == "jacks": v = jacks(ph)
    elif key == "circles": v = circles(ph)
    elif key == "squat": v = keyframes(ph, K_SQUAT)
    elif key == "punch": v = punch(ph)
    elif key == "shuffle": v = shuffle(ph)
    elif key == "reach": v = keyframes(ph, K_REACH)
    elif key == "skater": v = keyframes(ph, K_SKATER)
    elif key == "bend": v = keyframes(ph, K_BEND)
    elif key == "breath": v = keyframes(ph, K_BREATH)
    elif key == "wave": v = wave_pose(ph, t)
    elif key == "cheer": v = cheer_pose(ph)
    else: v = P()
    # breathing / life
    v = v.copy()
    v[IDX["sl"]] += 0.8 * math.sin(2 * math.pi * t / 3.7)
    v[IDX["ht"]] += 2.0 * math.sin(2 * math.pi * t / 5.3)
    return v


def pose_at(t):
    kind, i, lt, L = segment(t)
    key, _, cyc, _ = EXS[i]
    if kind == "intro":
        return pose("wave", t / 1.5, t)
    if kind == "outro":
        if lt < OUTRO - 6:
            p = pose("cheer", lt / 0.95, t)
        else:
            p = pose("wave", lt / 1.5, t)
            q = pose("cheer", (OUTRO - 6) / 0.95, t)
            p = q + (p - q) * sstep((lt - (OUTRO - 6)) / 0.6)
        if lt < 0.6:
            q = pose(key, (PREP + WORK) / cyc, t)
            p = q + (p - q) * sstep(lt / 0.6)
        return p
    if kind == "prep":
        p = pose(key, lt / (cyc * 1.5), t)
        if lt < 0.7:
            st = t - lt
            if i == 0:
                q = pose("wave", st / 1.5, st)
            else:
                pk, _, pc, _ = EXS[i - 1]
                q = pose(pk, WORK / pc, st)
            p = q + (p - q) * sstep(lt / 0.7)
        return p
    p = pose(key, lt / cyc, t)
    if lt < 0.5:
        q = pose(key, PREP / (cyc * 1.5), t)
        p = q + (p - q) * sstep(lt / 0.5)
    return p


# ================================================================ 3D skeleton + projection
def Rx(a):
    a = math.radians(a); c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
def Ry(a):
    a = math.radians(a); c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
def Rz(a):
    a = math.radians(a); c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])

DOWN = np.array([0.0, -1.0, 0.0])
FOC, DEPTH, CAMY, Y0 = 1700.0, 4.0, 1.0, 620.0


def skeleton3d(v):
    g = lambda k: v[IDX[k]]
    Rp = Ry(g("pt")) @ Rz(g("pl"))
    Rm = Rp @ Ry(g("st") / 2) @ Rz(-g("ss") / 2) @ Rx(-g("sl") / 2)
    Rt = Rp @ Ry(g("st")) @ Rz(-g("ss")) @ Rx(-g("sl"))
    pel = np.zeros(3)
    mid = pel + Rm @ np.array([0, 0.25, 0])
    nb = mid + Rt @ np.array([0, 0.27, 0])
    Rh = Rt @ Ry(g("ht")) @ Rz(-g("hs")) @ Rx(-g("hn"))
    head = nb + Rh @ np.array([0, 0.155, -0.01])
    J = dict(pel=pel, mid=mid, nb=nb, head=head)
    J["torso"] = [
        pel + Rp @ np.array([0.165, -0.03, 0]), mid + Rm @ np.array([0.135, -0.04, 0]),
        mid + Rt @ np.array([0.16, 0.12, 0]), mid + Rt @ np.array([0.17, 0.215, 0]), nb + Rt @ np.array([0.06, -0.005, 0]),
        nb + Rt @ np.array([-0.06, -0.005, 0]), mid + Rt @ np.array([-0.17, 0.215, 0]), mid + Rt @ np.array([-0.16, 0.12, 0]),
        mid + Rm @ np.array([-0.135, -0.04, 0]), pel + Rp @ np.array([-0.165, -0.03, 0]),
        pel + Rp @ np.array([-0.07, -0.13, 0]), pel + Rp @ np.array([0.07, -0.13, 0])]
    for s, sd in ((1, "r_"), (-1, "l_")):
        sh = mid + Rt @ np.array([s * 0.175, 0.215, 0])
        Ra = Rt @ Rz(s * g(sd + "sa")) @ Rx(g(sd + "sf"))
        el = sh + Ra @ DOWN * 0.29
        Rf = Rt @ Rz(s * g(sd + "sa")) @ Rx(g(sd + "sf") + g(sd + "el"))
        wr = el + Rf @ DOWN * 0.255
        hd = wr + Rf @ DOWN * 0.055
        hip = pel + Rp @ np.array([s * 0.092, -0.06, 0])
        Rl = Rp @ Rz(s * g(sd + "ha")) @ Rx(g(sd + "hf"))
        kn = hip + Rl @ DOWN * 0.45
        Rs = Rp @ Rz(s * g(sd + "ha")) @ Rx(g(sd + "hf") - g(sd + "kn"))
        an = kn + Rs @ DOWN * 0.43
        Rfo = Rp @ Ry(-s * 8) @ Rx(-g(sd + "an"))
        heel = an + Rfo @ np.array([0, -0.045, 0.045])
        toe = an + Rfo @ np.array([0, -0.05, -0.16])
        J[sd + "arm"] = (sh, el, wr, hd)
        J[sd + "leg"] = (hip, kn, an, heel, toe)
    # ground + depth anchoring
    lows = [min(J[sd + "leg"][3][1], J[sd + "leg"][4][1]) - 0.04 for sd in ("r_", "l_")]
    ymin = min(lows)
    ws = [math.exp(-(y - ymin) / 0.02) for y in lows]
    zan = sum(w * J[sd + "leg"][2][2] for w, sd in zip(ws, ("r_", "l_"))) / sum(ws)
    off = np.array([g("dx"), -ymin + g("dy"), -zan])
    def mv(o):
        if isinstance(o, (list, tuple)):
            return type(o)(mv(q) for q in o)
        return o + off
    return {k: mv(o) for k, o in J.items()}


def prj(p):
    d = DEPTH - p[2]
    return (960 + FOC * p[0] / d, Y0 + FOC * (CAMY - p[1]) / d, FOC / d)


RX0, RW = 260, 1400  # silhouette render region
SS = 2


class Pen:
    def __init__(self, d, grow):
        self.d, self.g = d, grow  # grow in metres
    def pt(self, p):
        x, y, k = prj(p)
        return (x - RX0) * SS, y * SS, k * SS
    def disc(self, p, r):
        x, y, k = self.pt(p)
        R = (r + self.g) * k
        self.d.ellipse([x - R, y - R, x + R, y + R], fill=255)
    def cap(self, a, b, ra, rb):
        xa, ya, ka = self.pt(a); xb, yb, kb = self.pt(b)
        Ra, Rb = (ra + self.g) * ka, (rb + self.g) * kb
        dx, dy = xb - xa, yb - ya
        L = math.hypot(dx, dy) or 1e-6
        nx, ny = -dy / L, dx / L
        self.d.polygon([(xa + nx * Ra, ya + ny * Ra), (xb + nx * Rb, yb + ny * Rb),
                        (xb - nx * Rb, yb - ny * Rb), (xa - nx * Ra, ya - ny * Ra)], fill=255)
        self.d.ellipse([xa - Ra, ya - Ra, xa + Ra, ya + Ra], fill=255)
        self.d.ellipse([xb - Rb, yb - Rb, xb + Rb, yb + Rb], fill=255)
    def limb(self, a, b, radii, fr=0.4):
        m = a + (b - a) * fr
        self.cap(a, m, radii[0], radii[1])
        self.cap(m, b, radii[1], radii[2])


def draw_figure(d, J, grow):
    pen = Pen(d, grow)
    # torso (polygon grown via outline discs)
    pts = [pen.pt(p) for p in J["torso"]]
    d.polygon([(x, y) for x, y, _ in pts], fill=255)
    if grow:
        for a, b in zip(J["torso"], J["torso"][1:] + J["torso"][:1]):
            pen.cap(a, b, 0.0, 0.0)
    for sd in ("r_", "l_"):
        hip, kn, an, heel, toe = J[sd + "leg"]
        pen.disc(hip + np.array([0, 0.02, 0]), 0.085)
        pen.limb(hip, kn, (0.083, 0.072, 0.054), 0.45)
        pen.limb(kn, an, (0.054, 0.062, 0.036), 0.32)
        pen.cap(heel, toe, 0.042, 0.04)
        sh, el, wr, hd = J[sd + "arm"]
        pen.disc(sh, 0.066)
        pen.limb(sh, el, (0.058, 0.05, 0.042), 0.35)
        pen.limb(el, wr, (0.042, 0.04, 0.031), 0.4)
        pen.disc(hd, 0.047)
    pen.cap(J["nb"], J["head"], 0.052, 0.05)
    x, y, k = pen.pt(J["head"])
    rx, ry = (0.098 + grow) * k, (0.118 + grow) * k
    d.ellipse([x - rx, y - ry, x + rx, y + ry], fill=255)
    # ponytail for a friendlier silhouette
    pen.cap(J["head"] + np.array([0.0, 0.05, 0.06]), J["head"] + np.array([0.03 * math.sin(J["pel"][1] * 40), -0.07, 0.11]), 0.04, 0.03)


def silhouette(img, v, glow_col=(255, 255, 255)):
    J = skeleton3d(v)
    masks = []
    for grow in (0.022, 0.0):
        m = Image.new("L", (RW * SS, H * SS), 0)
        draw_figure(ImageDraw.Draw(m), J, grow)
        masks.append(m.reduce(SS))
    # contact shadow
    px, py, k = prj(np.array([J["pel"][0], 0.0, 0.0]))
    hgt = max(0.0, min(J["r_leg"][3][1], J["l_leg"][3][1]))
    sc = 1.0 / (1.0 + hgt * 2.5)
    sw, sh_ = int(SHADOW.width * sc), int(SHADOW.height * sc)
    s = SHADOW.resize((max(2, sw), max(2, sh_)))
    img.paste((0, 0, 0, 255), (int(px - sw / 2), int(py + 2 - sh_ / 2)), s)
    g = masks[0].resize((RW // 4, H // 4), Image.BILINEAR).filter(ImageFilter.GaussianBlur(7)).resize((RW, H), Image.BILINEAR)
    img.paste(glow_col + (255,), (RX0, 0, RX0 + RW, H), g.point(lambda q: min(255, q * 2)))
    img.paste((255, 255, 255, 255), (RX0, 0, RX0 + RW, H), masks[0].point(lambda q: q * 92 // 100))
    img.paste((0, 0, 0, 255), (RX0, 0, RX0 + RW, H), masks[1])


SHADOW = None


# ================================================================ worlds
HOR, F, CAMH = 455, 950, 1.7
RWD = 2.6


def lerp(a, b, t):
    t = min(1.0, max(0.0, t))
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def dark(c, k=0.62):
    return tuple(int(x * k) for x in c)


THEMES = [
    dict(sky=[(255, 120, 205), (255, 190, 232), (255, 238, 210)], hills=[(245, 170, 230), (190, 150, 245)],
         ground=[(150, 238, 190), (128, 224, 172)], tiles=[(255, 140, 200), (255, 246, 252)],
         curb=[(240, 40, 90), (255, 255, 255)], side=(255, 240, 170), glow=175,
         spark=[(255, 255, 255), (255, 230, 90), (120, 230, 255), (255, 140, 220)]),
    dict(sky=[(30, 130, 255), (120, 210, 255), (225, 252, 225)], hills=[(110, 200, 150), (60, 165, 95)],
         ground=[(95, 205, 85), (75, 185, 75)], tiles=[(242, 205, 120), (226, 182, 98)],
         curb=[(150, 95, 45), (255, 215, 70)], side=(70, 160, 60), glow=185,
         spark=[(255, 245, 140), (255, 255, 255), (190, 255, 120)]),
    dict(sky=[(22, 30, 92), (88, 98, 190), (238, 196, 225)], hills=[(205, 210, 245), (240, 245, 255)],
         ground=[(244, 249, 255), (226, 238, 252)], tiles=[(196, 228, 255), (238, 249, 255)],
         curb=[(60, 140, 255), (255, 255, 255)], side=(210, 230, 252), glow=234,
         spark=[(255, 255, 255), (160, 230, 255), (200, 180, 255)]),
]
SUNPOS = [(1480, 175), (1500, 150), (430, 175)]


def vgrad(stops, h):
    a = np.zeros((h, 3))
    n = len(stops) - 1
    for y in range(h):
        f = y / max(1, h - 1) * n
        i = min(n - 1, int(f))
        a[y] = np.array(stops[i]) + (np.array(stops[i + 1]) - np.array(stops[i])) * (f - i)
    return a


def make_base(wi):
    th = THEMES[wi]
    a = np.zeros((H, W, 3))
    a[:HOR] = vgrad(th["sky"], HOR)[:, None, :]
    a[HOR:] = np.array(th["ground"][0])
    img = Image.fromarray(a.astype(np.uint8)).convert("RGBA")
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    rng = np.random.default_rng(wi + 3)
    if wi == 0:  # rainbow
        cols = [(255, 70, 90), (255, 160, 60), (255, 235, 80), (90, 220, 120), (80, 170, 255), (170, 110, 255)]
        for k, c in enumerate(cols):
            r = 760 - k * 30
            d.arc([960 - r - 300, HOR + 60 - r, 960 + r - 300, HOR + 60 + r], 180, 360, fill=c + (120,), width=30)
    if wi == 2:  # stars + aurora
        for _ in range(160):
            x, y = rng.integers(0, W), rng.integers(0, 260)
            r = rng.random() * 1.8 + 0.6
            d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, int(120 + rng.random() * 135)))
        au = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ad = ImageDraw.Draw(au)
        for band, col in ((0, (80, 255, 170)), (1, (120, 200, 255)), (2, (200, 120, 255))):
            pts = []
            for x in range(-50, W + 100, 40):
                y = 120 + band * 45 + 50 * math.sin(x / 260 + band) + 25 * math.sin(x / 90 + band * 2)
                pts.append((x, y))
            ad.line(pts, fill=col + (150,), width=46 - band * 8, joint="curve")
        ov = Image.alpha_composite(ov, au.filter(ImageFilter.GaussianBlur(18)))
        d = ImageDraw.Draw(ov)
    img = Image.alpha_composite(img, ov)
    # sun / moon glow
    sx, sy = SUNPOS[wi]
    glow = Image.new("RGBA", (700, 700), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for r in range(330, 0, -12):
        al = int(150 * (1 - r / 330) ** 2)
        gd.ellipse([350 - r, 350 - r, 350 + r, 350 + r], fill=(255, 250, 220, al))
    img.alpha_composite(glow, (sx - 350, sy - 350))
    d = ImageDraw.Draw(img)
    disc = (255, 248, 190) if wi != 2 else (250, 248, 255)
    d.ellipse([sx - 72, sy - 72, sx + 72, sy + 72], fill=disc)
    if wi == 2:
        d.ellipse([sx - 40, sy - 30, sx - 18, sy - 8], fill=(225, 225, 240))
        d.ellipse([sx + 10, sy + 12, sx + 38, sy + 40], fill=(225, 225, 240))
    # layered hills
    for layer, col in enumerate(th["hills"]):
        pts = [(0, HOR + 2)]
        base = HOR - 95 + layer * 45
        ph = rng.random() * 6
        for x in range(0, W + 40, 40):
            y = base - 55 * math.sin(x / (230 - layer * 60) + ph) - 30 * math.sin(x / 97 + ph * 2)
            pts.append((x, y))
        pts.append((W, HOR + 2))
        c = lerp(col, th["sky"][-1], 0.25 - layer * 0.15)
        d.polygon(pts, fill=c)
        if wi == 2 and layer == 0:  # snow caps sparkle line
            d.line(pts[1:-1], fill=(255, 255, 255), width=6)
        if wi == 1 and layer == 0:  # waterfall
            d.rectangle([520, HOR - 150, 548, HOR], fill=(200, 240, 255))
            d.rectangle([528, HOR - 150, 536, HOR], fill=(255, 255, 255))
    return img.convert("RGB")


def make_rays():
    r = Image.new("RGBA", (900, 900), (0, 0, 0, 0))
    d = ImageDraw.Draw(r)
    for k in range(14):
        a0 = math.radians(k * 360 / 14)
        a1 = a0 + math.radians(10)
        d.polygon([(450, 450), (450 + 450 * math.cos(a0), 450 + 450 * math.sin(a0)),
                   (450 + 450 * math.cos(a1), 450 + 450 * math.sin(a1))], fill=(255, 255, 230, 46))
    return r.filter(ImageFilter.GaussianBlur(3))


def make_cloud(tint):
    c = Image.new("RGBA", (460, 200), (0, 0, 0, 0))
    d = ImageDraw.Draw(c)
    blobs = ((95, 125, 62), (180, 92, 82), (275, 105, 72), (350, 132, 52), (215, 140, 62))
    for x, y, r in blobs:
        d.ellipse([x - r, y - r + 10, x + r, y + r + 10], fill=tint + (255,))
    for x, y, r in blobs:
        d.ellipse([x - r, y - r, x + r, y + r - 6], fill=(255, 255, 255, 255))
    return c.filter(ImageFilter.GaussianBlur(1.5))


def make_shadow():
    s = Image.new("L", (560, 110), 0)
    ImageDraw.Draw(s).ellipse([40, 20, 520, 90], fill=120)
    return s.filter(ImageFilter.GaussianBlur(14))


BASES, CLOUDS, RAYS = [], [], None
FLARES = []


def make_flares():
    out = []
    for f_, r, col, a in ((0.45, 40, (255, 255, 200), 70), (0.8, 70, (180, 255, 220), 45), (1.15, 26, (255, 200, 255), 80),
                          (1.5, 110, (200, 220, 255), 35), (1.75, 45, (255, 230, 150), 60)):
        sp = Image.new("RGBA", (r * 2 + 20, r * 2 + 20), (0, 0, 0, 0))
        ImageDraw.Draw(sp).ellipse([10, 10, 10 + 2 * r, 10 + 2 * r], fill=col + (a,), outline=col + (min(255, a * 2),), width=3)
        out.append((f_, sp.filter(ImageFilter.GaussianBlur(2))))
    return out


def proj(x, z, y=0.0):
    return 960 + F * x / z, HOR + F * (CAMH - y) / z


def hsh(n):
    n = (n * 2654435761) & 0xFFFFFFFF
    return ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF


def star(d, x, y, r, col):
    k = r * 0.28
    d.polygon([(x, y - r), (x + k, y - k), (x + r, y), (x + k, y + k), (x, y + r), (x - k, y + k), (x - r, y), (x - k, y - k)], fill=col)


def ell(d, cx, cy, rx, ry, fill, ow=0):
    d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=fill, outline=dark(fill) if ow else None, width=ow)


def draw_object(d, kind, wi, x, z, fog, th, t):
    sx, sy = proj(x, z)
    u = F / z
    fc = lambda c: lerp(c, th["sky"][-1], fog)
    ow = max(1, int(u * 0.06))
    ell(d, sx, sy, 1.0 * u, 0.22 * u, fc(dark(th["ground"][0], 0.82)))  # ground shadow
    if wi == 0:
        k = kind % 5
        if k == 0:  # lollipop
            d.line([sx, sy, sx, sy - 2.6 * u], fill=fc((255, 255, 255)), width=max(1, int(0.2 * u)))
            cols = [(255, 70, 150), (255, 220, 60), (80, 200, 255), (170, 110, 255)]
            for j, rr in enumerate((1.0, 0.75, 0.5, 0.25)):
                ell(d, sx, sy - 2.7 * u, rr * u, rr * u, fc(cols[(kind + j) % 4] if j % 2 == 0 else (255, 255, 255)), ow if j == 0 else 0)
            ell(d, sx - 0.4 * u, sy - 3.05 * u, 0.15 * u, 0.1 * u, fc((255, 255, 255)))
        elif k == 1:  # cupcake house
            w_, h_ = 2.4 * u, 1.7 * u
            d.polygon([(sx - w_ / 2, sy - h_), (sx + w_ / 2, sy - h_), (sx + w_ * 0.4, sy), (sx - w_ * 0.4, sy)], fill=fc((215, 150, 95)), outline=fc((150, 95, 55)))
            for j in range(4):
                xx = sx - w_ * 0.36 + j * w_ * 0.24
                d.line([xx, sy - h_, xx + 0.05 * u, sy], fill=fc((180, 120, 70)), width=max(1, int(0.07 * u)))
            ell(d, sx, sy - h_ - 0.45 * u, w_ * 0.62, 0.85 * u, fc((255, 160, 210)), ow)
            ell(d, sx, sy - h_ - 1.15 * u, w_ * 0.4, 0.6 * u, fc((255, 190, 225)))
            ell(d, sx, sy - h_ - 1.85 * u, 0.3 * u, 0.3 * u, fc((235, 30, 60)), ow)
            for j in range(7):
                hh = hsh(kind * 31 + j)
                ell(d, sx + ((hh % 100) / 50 - 1) * w_ * 0.5, sy - h_ - 0.3 * u - (hh >> 8) % 100 / 100 * 0.9 * u, 0.08 * u, 0.08 * u,
                    fc([(255, 255, 255), (90, 200, 255), (255, 230, 60)][j % 3]))
        elif k == 2:  # candy cane
            wd = max(1, int(0.32 * u))
            d.line([sx, sy, sx, sy - 2.5 * u], fill=fc((255, 255, 255)), width=wd)
            d.arc([sx, sy - 3.1 * u, sx + 1.2 * u, sy - 1.9 * u], 180, 360, fill=fc((230, 40, 60)), width=wd)
            for j in range(5):
                yy = sy - (0.25 + 0.48 * j) * u
                d.line([sx - wd / 2, yy, sx + wd / 2, yy - 0.22 * u], fill=fc((230, 40, 60)), width=max(1, int(0.13 * u)))
        elif k == 3:  # gumdrop tree
            d.rectangle([sx - 0.15 * u, sy - 1.6 * u, sx + 0.15 * u, sy], fill=fc((170, 110, 70)))
            c = [(120, 230, 190), (255, 150, 200), (255, 210, 110)][kind % 3]
            for ox, oy, r in ((-0.6, 2.0, 0.8), (0.6, 2.0, 0.8), (0, 2.7, 0.95)):
                ell(d, sx + ox * u, sy - oy * u, r * u, r * u, fc(c), ow)
            ell(d, sx - 0.3 * u, sy - 3.1 * u, 0.25 * u, 0.15 * u, fc((255, 255, 255)))
        else:  # ice cream tower
            d.polygon([(sx - 0.7 * u, sy - 2.0 * u), (sx + 0.7 * u, sy - 2.0 * u), (sx, sy)], fill=fc((235, 180, 100)), outline=fc((170, 120, 60)))
            ell(d, sx, sy - 2.3 * u, 0.8 * u, 0.7 * u, fc((140, 230, 200)), ow)
            ell(d, sx, sy - 3.1 * u, 0.65 * u, 0.6 * u, fc((255, 170, 210)), ow)
            ell(d, sx, sy - 3.8 * u, 0.22 * u, 0.22 * u, fc((235, 30, 60)))
    elif wi == 1:
        k = kind % 4
        if k in (0, 1):  # palm
            tw = max(1, int(0.38 * u))
            top = (sx + (0.6 if x > 0 else -0.6) * u, sy - 4.4 * u)
            mid = (sx + (0.15 if x > 0 else -0.15) * u, sy - 2.2 * u)
            d.line([sx, sy, mid[0], mid[1], top[0], top[1]], fill=fc((140, 95, 50)), width=tw, joint="curve")
            sway = 6 * math.sin(t * 1.5 + kind)
            for ang in range(0, 360, 45):
                a = math.radians(ang + 15 + sway)
                ex, ey = top[0] + math.cos(a) * 2.1 * u, top[1] + math.sin(a) * 0.8 * u + 0.6 * u
                mx, my = (top[0] + ex) / 2, (top[1] + ey) / 2 - 0.3 * u
                d.line([top[0], top[1], mx, my, ex, ey], fill=fc((40, 170, 60) if ang % 90 else (60, 200, 80)), width=max(1, int(0.42 * u)), joint="curve")
            for j in range(3):
                ell(d, top[0] + (j - 1) * 0.25 * u, top[1] + 0.3 * u, 0.18 * u, 0.18 * u, fc((120, 80, 35)))
        elif k == 2:  # mushroom
            d.rectangle([sx - 0.3 * u, sy - 1.3 * u, sx + 0.3 * u, sy], fill=fc((250, 240, 220)), outline=fc((190, 170, 140)))
            d.pieslice([sx - 1.2 * u, sy - 2.5 * u, sx + 1.2 * u, sy - 0.5 * u], 180, 360, fill=fc((235, 40, 50)), outline=fc((150, 20, 30)), width=ow)
            for ox, oy, r in ((-0.6, 1.75, 0.18), (0.1, 2.1, 0.22), (0.65, 1.7, 0.15)):
                ell(d, sx + ox * u, sy - oy * u, r * u, r * u, fc((255, 255, 255)))
        else:  # flower bush
            r = 1.0 * u
            ell(d, sx, sy - 0.6 * r, 1.5 * r, 0.75 * r, fc((35, 140, 50)), ow)
            ell(d, sx - 0.5 * r, sy - 0.9 * r, 0.8 * r, 0.6 * r, fc((50, 165, 60)))
            for j, (fx, fy) in enumerate(((-0.8, -0.9), (0.3, -1.15), (0.9, -0.6), (-0.2, -0.5))):
                c = [(255, 80, 120), (255, 215, 40), (255, 130, 220), (255, 255, 255)][j]
                for a in range(5):
                    aa = a * 1.256
                    ell(d, sx + fx * r + math.cos(aa) * 0.12 * u, sy + fy * r + math.sin(aa) * 0.12 * u, 0.09 * u, 0.09 * u, fc(c))
                ell(d, sx + fx * r, sy + fy * r, 0.07 * u, 0.07 * u, fc((255, 230, 80)))
    else:
        k = kind % 4
        if k in (0, 1):  # snowy pine
            d.rectangle([sx - 0.2 * u, sy - 0.8 * u, sx + 0.2 * u, sy], fill=fc((110, 75, 45)))
            for j in range(3):
                b = sy - 0.6 * u - j * 1.0 * u
                wdt = (1.5 - 0.4 * j) * u
                d.polygon([(sx - wdt, b), (sx + wdt, b), (sx, b - 1.7 * u)], fill=fc((25, 115, 80)), outline=fc((15, 70, 50)))
                d.polygon([(sx - wdt * 0.45, b - 0.95 * u), (sx + wdt * 0.45, b - 0.95 * u), (sx, b - 1.7 * u)], fill=fc((255, 255, 255)))
            if kind % 2 == 0:  # fairy lights
                for j in range(6):
                    hh = hsh(kind * 17 + j)
                    on = (math.sin(t * 4 + j * 1.7) > -0.2)
                    c = [(255, 80, 80), (255, 220, 60), (90, 200, 255)][j % 3] if on else (60, 60, 70)
                    ell(d, sx + ((hh % 100) / 50 - 1) * 0.9 * u, sy - (1.0 + (hh >> 8) % 100 / 100 * 2.0) * u, 0.09 * u, 0.09 * u, fc(c))
        elif k == 2:  # snowman
            for r, yc in ((0.75, 0.75), (0.55, 1.95), (0.4, 2.85)):
                ell(d, sx, sy - yc * u, r * u, r * u, fc((255, 255, 255)), ow)
            d.polygon([(sx, sy - 2.85 * u), (sx + 0.5 * u, sy - 2.8 * u), (sx, sy - 2.75 * u)], fill=fc((255, 140, 30)))
            d.rectangle([sx - 0.35 * u, sy - 3.6 * u, sx + 0.35 * u, sy - 3.15 * u], fill=fc((40, 40, 60)))
            d.rectangle([sx - 0.5 * u, sy - 3.2 * u, sx + 0.5 * u, sy - 3.1 * u], fill=fc((40, 40, 60)))
            d.rectangle([sx - 0.45 * u, sy - 2.45 * u, sx + 0.45 * u, sy - 2.3 * u], fill=fc((230, 40, 60)))
        else:  # ice crystals
            for ox, hgt, wd, c in ((-0.5, 2.2, 0.35, (120, 210, 255)), (0.4, 2.9, 0.42, (160, 230, 255)), (0.0, 1.6, 0.3, (200, 170, 255))):
                bx = sx + ox * u
                d.polygon([(bx - wd * u, sy - 0.3 * u), (bx, sy - hgt * u), (bx + wd * u, sy - 0.3 * u), (bx, sy)], fill=fc(c), outline=fc((255, 255, 255)))
                d.polygon([(bx, sy - hgt * u), (bx + wd * u * 0.5, sy - 0.5 * u), (bx, sy - 0.2 * u)], fill=fc((235, 250, 255)))


def draw_arch(d, wi, z, fog, th, t):
    sx, sy = proj(0, z)
    u = F / z
    fc = lambda c: lerp(c, th["sky"][-1], fog)
    r = (RWD + 0.7) * u
    if wi == 0:
        cols = [(255, 70, 90), (255, 160, 60), (255, 235, 80), (90, 220, 120), (80, 170, 255), (170, 110, 255)]
        bw = 0.24 * u
        for k, c in enumerate(cols):
            rr = r - k * bw
            d.arc([sx - rr, sy - rr - 0.6 * u, sx + rr, sy + rr - 0.6 * u], 180, 360, fill=fc(c), width=max(1, int(bw + 1)))
        for s in (-1, 1):
            d.rectangle([sx + s * r - 0.3 * u, sy - 0.6 * u, sx + s * r + 0.3 * u, sy], fill=fc((255, 255, 255)))
            ell(d, sx + s * r, sy - 0.1 * u, 0.5 * u, 0.25 * u, fc((255, 255, 255)))
    elif wi == 1:
        top = sy - 4.6 * u
        for s in (-1, 1):
            d.rectangle([sx + s * r - 0.3 * u, top, sx + s * r + 0.3 * u, sy], fill=fc((130, 85, 45)), outline=fc((80, 50, 25)))
        d.rectangle([sx - r - 0.6 * u, top - 0.5 * u, sx + r + 0.6 * u, top + 0.2 * u], fill=fc((150, 100, 55)), outline=fc((80, 50, 25)))
        for j in range(14):
            xx = sx - r + j * (2 * r / 13)
            ln = (0.8 + (hsh(j) % 100) / 100 * 1.4) * u
            d.line([xx, top + 0.2 * u, xx + 0.1 * u * math.sin(t * 2 + j), top + ln], fill=fc((40, 160, 60)), width=max(1, int(0.12 * u)))
            ell(d, xx, top + ln, 0.16 * u, 0.12 * u, fc([(255, 90, 120), (255, 220, 60), (60, 190, 70)][j % 3]))
    else:
        bw = 0.42 * u
        for k, c in enumerate([(255, 255, 255), (170, 225, 255), (110, 190, 255)]):
            rr = r - k * bw
            d.arc([sx - rr, sy - rr - 0.6 * u, sx + rr, sy + rr - 0.6 * u], 180, 360, fill=fc(c), width=max(1, int(bw + 1)))
        for j in range(9):
            a = math.pi + j * math.pi / 8
            star(d, sx + math.cos(a) * (r - bw), sy - 0.6 * u + math.sin(a) * (r - bw), (0.15 + 0.08 * math.sin(t * 5 + j)) * u, fc((255, 255, 255)))


def draw_coin(d, wi, x, z, n, t, fog, th):
    hgt = 0.65 + 0.08 * math.sin(t * 3 + n)
    sx, sy = proj(x, z, hgt)
    gx, gy = proj(x, z)
    u = F / z
    ell(d, gx, gy, 0.28 * u, 0.07 * u, lerp(dark(th["tiles"][0], 0.8), th["sky"][-1], fog))
    if wi == 0 and n % 2 == 0:  # gem
        c = [(255, 60, 140), (80, 200, 255), (170, 100, 255)][n % 3]
        r = 0.32 * u
        wf = max(0.25, abs(math.cos(t * 3 + n)))
        pts = [(sx, sy - r), (sx + r * wf, sy - r * 0.25), (sx, sy + r), (sx - r * wf, sy - r * 0.25)]
        d.polygon(pts, fill=lerp(c, th["sky"][-1], fog), outline=lerp(dark(c), th["sky"][-1], fog))
        d.polygon([pts[0], pts[1], (sx, sy - r * 0.1)], fill=lerp((255, 255, 255), c, 0.4))
    else:
        r = 0.3 * u
        wf = max(0.12, abs(math.cos(t * 3.2 + n * 0.7)))
        ell(d, sx, sy, r * wf, r, lerp((235, 160, 20), th["sky"][-1], fog))
        ell(d, sx, sy, r * wf * 0.82, r * 0.82, lerp((255, 210, 50), th["sky"][-1], fog))
        ell(d, sx, sy, r * wf * 0.45, r * 0.45, lerp((255, 235, 120), th["sky"][-1], fog))
        ell(d, sx - r * wf * 0.35, sy - r * 0.4, r * wf * 0.18, r * 0.18, (255, 255, 255))
    tw = math.sin(t * 6 + n * 2.3)
    if tw > 0.6 and z < 40:
        star(d, sx + 0.3 * u, sy - 0.32 * u, (tw - 0.6) * 0.9 * u, (255, 255, 255))


def draw_world(wi, dist, t):
    th = THEMES[wi]
    img = BASES[wi].copy()
    if wi != 2:
        rot = RAYS.rotate(t * 6, resample=Image.BILINEAR)
        sx, sy = SUNPOS[wi]
        img.paste(rot, (sx - 450, sy - 450), rot)
    cl = CLOUDS[wi]
    for k in range(4):
        x = int((k * 560 - t * 14) % (W + 520)) - 470
        img.paste(cl, (x, 30 + (k % 2) * 115), cl)
    d = ImageDraw.Draw(img)
    zn, zf = 1.6, 120.0
    # ground bands
    bp = 8.0
    off = dist % bp
    for k in range(-1, 15):
        z1 = max(zn, k * bp - off + zn)
        z2 = max(zn, (k + 1) * bp - off + zn)
        if z2 <= z1:
            continue
        y1, y2 = proj(0, z1)[1], proj(0, z2)[1]
        col = lerp(th["ground"][k % 2], th["sky"][-1], (z1 - 20) / 100)
        d.rectangle([0, y2, W, y1], fill=col)
    # side sidewalk + curb + road
    for half, col in ((RWD + 1.3, th["side"]),):
        d.polygon([proj(-half, zn), proj(half, zn), proj(half, zf), proj(-half, zf)], fill=col)
    tp = 2.5
    off = dist % tp
    cols = 4
    for k in range(-1, 50):
        z1 = max(zn, k * tp - off + zn)
        z2 = max(zn, (k + 1) * tp - off + zn)
        if z2 <= z1 or z1 > zf:
            continue
        fog = (z1 - 20) / 100
        rowpar = (k + int(dist // tp)) % 2
        for c in range(cols):
            x1 = -RWD + c * 2 * RWD / cols
            x2 = x1 + 2 * RWD / cols
            col = lerp(th["tiles"][(c + rowpar) % 2], th["sky"][-1], fog)
            d.polygon([proj(x1, z1), proj(x2, z1), proj(x2, z2), proj(x1, z2)], fill=col)
        for s in (-1, 1):  # curbs
            col = lerp(th["curb"][rowpar], th["sky"][-1], fog)
            d.polygon([proj(s * RWD, z1), proj(s * (RWD + 0.35), z1), proj(s * (RWD + 0.35), z2), proj(s * RWD, z2)], fill=col)
    # glitter twinkling on the road
    gp = 0.9
    for k in range(80):
        n = int(dist // gp) + k
        z = n * gp - dist + zn
        if z < zn or z > 45:
            continue
        hh = hsh(n + 4242)
        tw = math.sin(t * 7 + (hh % 628) / 100)
        if tw > 0.35:
            gx, gy = proj(((hh % 1000) / 1000 * 2 - 1) * (RWD + 1.2), z)
            star(d, gx, gy, min(26, (tw - 0.35) * 0.16 * F / z), (255, 255, 255))
    # objects, coins and arches sorted by depth
    items = []
    spacing = 7.0
    base_n = int(dist // spacing)
    for k in range(17):
        n = base_n + k
        z = n * spacing - dist + 1.0
        if z < 1.5:
            continue
        for side in (-1, 1):
            hh = hsh(n * 2 + (side > 0))
            x = side * (RWD + 2.6 + (hh % 1000) / 1000 * 3.8)
            items.append((z, "obj", hh % 20, x))
    ap = 55.0
    for k in range(3):
        n = int(dist // ap) + k
        z = n * ap - dist + 20
        if 1.2 < z < zf:
            items.append((z, "arch", n, 0))
    cp = 18.0
    for k in range(5):
        n = int(dist // cp) + k
        lane = 1.35 if hsh(n + 99) % 2 else -1.35
        for j in range(5):
            z = n * cp - dist + 8 + j * 1.7
            if 1.8 < z < 70:
                items.append((z, "coin", n * 5 + j, lane))
    for z, typ, kind, x in sorted(items, key=lambda q: -q[0]):
        fog = min(0.85, max(0.0, (z - 25) / 80))
        if typ == "obj":
            draw_object(d, kind, wi, x, z, fog, th, t)
        elif typ == "arch":
            draw_arch(d, wi, z, fog, th, t)
        else:
            draw_coin(d, wi, x, z, kind, t, fog, th)
    # floating sparkles / particles
    sp = th["spark"]
    for k in range(34):
        hh = hsh(k + 1000 * wi)
        x = (hh % W + 18 * math.sin(t * 0.7 + k)) % W
        y = ((hh >> 7) % 520 + 10 * math.sin(t + k * 0.5))
        if wi == 0:
            y = (y - t * 25) % 760
        tw = 0.5 + 0.5 * math.sin(t * (2 + (hh % 5)) + k)
        star(d, x, y, 4 + 13 * tw, sp[k % len(sp)])
    if wi == 0:  # bubbles
        for k in range(14):
            hh = hsh(k + 555)
            x = (hh % W + 30 * math.sin(t * 0.8 + k)) % W
            y = H - ((hh >> 9) % H + t * (40 + hh % 40)) % (H + 100)
            r = 10 + hh % 18
            d.ellipse([x - r, y - r, x + r, y + r], outline=(255, 255, 255), width=3)
            d.ellipse([x - r * 0.45, y - r * 0.6, x - r * 0.1, y - r * 0.25], fill=(255, 255, 255))
    elif wi == 1:  # fireflies / pollen
        for k in range(30):
            hh = hsh(k + 777)
            x = (hh % W + 60 * math.sin(t * 0.6 + k)) % W
            y = 350 + (hh >> 9) % 500 + 30 * math.sin(t * 0.9 + k * 2)
            r = 4 + 3 * math.sin(t * 3 + k)
            d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 250, 150))
    else:  # snow
        for k in range(90):
            hh = hsh(k + 7)
            x = (hh % W + 30 * math.sin(t + k)) % W
            y = ((hh >> 8) % H + t * (55 + hh % 50)) % H
            r = 2.5 + hh % 4
            d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255))
    # bloom
    small = img.resize((W // 4, H // 4), Image.BILINEAR)
    thr = th["glow"]
    lut = [max(0, min(255, int((v - thr + 15) * 255 / (255 - thr) * 1.15))) for v in range(256)] * 3
    gl = small.point(lut).filter(ImageFilter.GaussianBlur(7)).resize((W, H), Image.BILINEAR)
    img = ImageChops.screen(img, gl)
    if wi != 2:
        sx, sy = SUNPOS[wi]
        for f_, spr in FLARES:
            fx, fy = sx + (960 - sx) * f_, sy + (560 - sy) * f_
            img.paste(spr, (int(fx - spr.width / 2), int(fy - spr.height / 2)), spr)
    return img


# ================================================================ HUD / text
_tc = {}
def text_img(s, size, fill=(255, 220, 40), stroke=(20, 20, 30), sw=None):
    k = (s, size, fill, stroke, sw)
    if k not in _tc:
        f = ImageFont.truetype(IMPACT, size)
        sw_ = sw if sw is not None else max(3, size // 12)
        bb = ImageDraw.Draw(Image.new("L", (1, 1))).textbbox((0, 0), s, font=f, stroke_width=sw_)
        im = Image.new("RGBA", (bb[2] - bb[0] + 8, bb[3] - bb[1] + 8), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((4 - bb[0], 4 - bb[1]), s, font=f, fill=fill, stroke_width=sw_, stroke_fill=stroke)
        _tc[k] = im
    return _tc[k]


def paste_c(img, ti, cx, cy, scale=1.0, alpha=1.0):
    if scale != 1.0:
        ti = ti.resize((max(1, int(ti.width * scale)), max(1, int(ti.height * scale))), Image.BILINEAR)
    if alpha < 1.0:
        ti = ti.copy()
        ti.putalpha(ti.getchannel("A").point(lambda v: int(v * max(0, alpha))))
    img.paste(ti, (int(cx - ti.width / 2), int(cy - ti.height / 2)), ti)


def paste_l(img, ti, x, y):
    img.paste(ti, (int(x), int(y)), ti)


def panel(img, box, fill=(20, 20, 45, 165), r=28, border=None):
    ov = Image.new("RGBA", (box[2] - box[0], box[3] - box[1]), (0, 0, 0, 0))
    ImageDraw.Draw(ov).rounded_rectangle([0, 0, ov.width - 1, ov.height - 1], r, fill=fill,
                                         outline=border + (255,) if border else None, width=5 if border else 0)
    img.paste(ov, box[:2], ov)


def timer(img, remain, total, col):
    cx, cy, R = 1765, 155, 100
    d = ImageDraw.Draw(img)
    d.ellipse([cx - R - 6, cy - R - 6, cx + R + 6, cy + R + 6], fill=(255, 255, 255))
    d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=(25, 25, 50))
    d.arc([cx - R + 10, cy - R + 10, cx + R - 10, cy + R - 10], 0, 360, fill=(70, 70, 100), width=18)
    frac = max(0, remain / total)
    if frac > 0:
        d.arc([cx - R + 10, cy - R + 10, cx + R - 10, cy + R - 10], -90, -90 + 360 * frac, fill=col, width=18)
    paste_c(img, text_img(str(int(math.ceil(remain))), 92, fill=(255, 255, 255), sw=4), cx, cy + 2)


ACC = [(255, 80, 165), (60, 205, 90), (80, 170, 255)]


def progress(img, cur, frac):
    n = len(EXS)
    x0, y0, w, h, g = 330, 1036, 1260, 22, 8
    sw = (w - g * (n - 1)) / n
    d = ImageDraw.Draw(img)
    for i in range(n):
        x = x0 + i * (sw + g)
        d.rounded_rectangle([x - 2, y0 - 2, x + sw + 2, y0 + h + 2], 9, fill=(255, 255, 255))
        d.rounded_rectangle([x, y0, x + sw, y0 + h], 8, fill=(30, 30, 55))
        f = 1 if i < cur else (frac if i == cur else 0)
        if f > 0:
            d.rounded_rectangle([x, y0, x + max(h, sw * f), y0 + h], 8, fill=ACC[EXS[i][3]])


def hud(img, t):
    kind, i, lt, L = segment(t)
    wi = 0 if kind == "intro" else (2 if kind == "outro" else EXS[i][3])
    accent = ACC[wi]
    if kind == "intro":
        paste_c(img, text_img("IMMERSIVE INTERACTIVE", 116), 960, 110, alpha=min(1, lt * 2))
        paste_c(img, text_img("WARM UP RUN!", 170, fill=(255, 255, 255)), 960, 250, alpha=min(1, max(0, lt * 2 - 0.5)))
        if lt > 2.5:
            panel(img, (540, 930, 1380, 1015), border=accent)
            paste_c(img, text_img("STAND UP & COPY THE SHADOW!", 58, fill=(255, 255, 255), sw=3), 960, 972)
    elif kind in ("prep", "work"):
        name = EXS[i][1]
        panel(img, (30, 30, 830, 250), border=accent)
        top = "GET READY!" if kind == "prep" else f"EXERCISE {i + 1} / {len(EXS)}"
        paste_l(img, text_img(top, 54, fill=accent, sw=4), 62, 45)
        paste_l(img, text_img(name, 112), 57, 112)
        rem = L - lt
        timer(img, rem, L, accent)
        progress(img, i, lt / L if kind == "work" else 0)
        new_world = i == 0 or EXS[i - 1][3] != wi
        if kind == "prep":
            if new_world and lt < 4.5:
                a = min(1, lt * 3, (4.5 - lt) * 2)
                paste_c(img, text_img(f"WELCOME TO {WORLDS[wi]}!", 110, fill=(255, 255, 255)), 960, 400, scale=0.9 + 0.1 * a, alpha=a)
            if rem <= 3:
                n = int(math.ceil(rem))
                fr = n - rem
                paste_c(img, text_img(str(n), 330, fill=(255, 255, 255), sw=14), 960, 560, scale=1.3 - 0.3 * min(1, fr * 4), alpha=1 - max(0, fr - 0.7) / 0.3)
            elif lt > 4.5 or not new_world:
                panel(img, (650, 930, 1270, 1012), border=accent)
                paste_c(img, text_img("WATCH THE MOVE...", 54, fill=(255, 255, 255), sw=3), 960, 971)
        else:
            if lt < 1.0:
                paste_c(img, text_img("GO!", 300, fill=accent, sw=14), 960, 560, scale=0.8 + 0.4 * lt, alpha=1 - lt)
            if L - lt <= 8 and i + 1 < len(EXS):
                panel(img, (1370, 860, 1890, 1000), border=ACC[EXS[i + 1][3]])
                paste_l(img, text_img("NEXT:", 44, fill=(255, 255, 255), sw=3), 1398, 876)
                paste_l(img, text_img(EXS[i + 1][1], 56), 1398, 928)
            if 10 < lt < 13 or 19 < lt < 21:
                msg = "KEEP GOING!" if lt < 15 else "YOU'RE DOING GREAT!"
                panel(img, (600, 930, 1320, 1012), border=accent)
                paste_c(img, text_img(msg, 60, fill=(255, 255, 255), sw=3), 960, 971)
    else:
        progress(img, len(EXS), 0)
        a = min(1, lt * 2)
        paste_c(img, text_img("GREAT JOB!", 220, fill=(255, 220, 40)), 960, 180, scale=1 + 0.04 * math.sin(lt * 5), alpha=a)
        if lt > 1.5:
            paste_c(img, text_img("YOU FINISHED THE WARM UP!", 80, fill=(255, 255, 255)), 960, 345, alpha=min(1, (lt - 1.5) * 2))
        if lt > 7:
            panel(img, (540, 920, 1380, 1012), border=accent)
            paste_c(img, text_img("DRINK SOME WATER & SEE YOU NEXT TIME!", 46, fill=(255, 255, 255), sw=3), 960, 966)


# ================================================================ frame
def speed(t):
    kind, i, lt, L = segment(t)
    if kind == "work":
        return {"run": 6, "knees": 7.5, "kicks": 6.5, "shuffle": 4, "skater": 5, "jacks": 4.5, "reach": 4}.get(EXS[i][0], 2.6)
    return 1.8


DIST = np.zeros(NF + 2)
_v = 1.8
for _f in range(1, NF + 2):
    _v += (speed(_f / FPS) - _v) * 0.04
    DIST[_f] = DIST[_f - 1] + _v / FPS


def world_index(t):
    kind, i, lt, L = segment(t)
    return 0 if kind == "intro" else (2 if kind == "outro" else EXS[i][3])


def frame(t):
    wi = world_index(t)
    img = draw_world(wi, DIST[min(NF, int(t * FPS))], t)
    # crossfade into a new world during first 0.8 s of its first prep
    kind, i, lt, L = segment(t)
    if kind == "prep" and i > 0 and EXS[i - 1][3] != wi and lt < 0.8:
        prev = draw_world(EXS[i - 1][3], DIST[min(NF, int(t * FPS))], t)
        img = Image.blend(prev, img, sstep(lt / 0.8))
    img = img.convert("RGBA")
    silhouette(img, pose_at(t), ACC[wi])
    d = ImageDraw.Draw(img)
    trails(d, t)
    fx(d, t)
    hud(img, t)
    hud_sparkles(ImageDraw.Draw(img), t, kind)
    return img.convert("RGB")


RAINBOW = [(255, 70, 90), (255, 160, 60), (255, 235, 80), (90, 230, 120), (80, 180, 255), (190, 120, 255)]


def trails(d, t):
    kind, i, lt, L = segment(t)
    feet = kind == "work" and EXS[i][0] in ("run", "knees", "kicks", "jacks", "skater", "shuffle", "reach")
    for k in range(7, -1, -1):
        J = skeleton3d(pose_at(max(0.0, t - k * 0.04)))
        pts = [J["r_arm"][3], J["l_arm"][3]]
        if feet:
            pts += [J["r_leg"][4], J["l_leg"][4]]
        for j, p in enumerate(pts):
            x, y, _ = prj(p)
            if k == 0:
                tw = 0.6 + 0.4 * math.sin(t * 9 + j)
                star(d, x, y, 26 * tw, (255, 255, 255))
            else:
                star(d, x + 6 * math.sin(k * 2.1 + j), y + 6 * math.cos(k * 1.7 + j), 17 * (1 - k / 8), RAINBOW[(k + j + int(t * 8)) % 6])


def confetti_burst(d, age, seed, n=110, x0=960, y0=560):
    if age < 0 or age > 3.0:
        return
    for k in range(n):
        h = hsh(seed * 1000 + k)
        ang = (h % 3600) / 3600 * 2 * math.pi
        sp = 500 + (h >> 12) % 900
        vx, vy = math.cos(ang) * sp, math.sin(ang) * sp - 500
        drag = (1 - math.exp(-2.2 * age)) / 2.2
        x = x0 + vx * drag
        y = y0 + vy * drag + 420 * age * age
        if y > H + 20:
            continue
        rot = age * (4 + h % 7) + k
        w_, h_ = 9, 5 + 8 * abs(math.sin(rot))
        c, s_ = math.cos(rot), math.sin(rot)
        col = RAINBOW[k % 6] if age < 2.4 else lerp(RAINBOW[k % 6], (255, 255, 255), (age - 2.4) / 0.6)
        d.polygon([(x + c * w_ - s_ * h_, y + s_ * w_ + c * h_), (x - c * w_ - s_ * h_, y - s_ * w_ + c * h_),
                   (x - c * w_ + s_ * h_, y - s_ * w_ - c * h_), (x + c * w_ + s_ * h_, y + s_ * w_ - c * h_)], fill=col)


def firework(d, age, seed):
    if age < 0 or age > 1.6:
        return
    h = hsh(seed)
    cx, cy = 300 + h % 1320, 120 + (h >> 10) % 260
    col = RAINBOW[seed % 6]
    r = 260 * (1 - math.exp(-3 * age))
    for k in range(26):
        a = k * 2 * math.pi / 26
        x, y = cx + math.cos(a) * r, cy + math.sin(a) * r + 60 * age * age
        sz = 12 * (1 - age / 1.6)
        star(d, x, y, sz + 2, col if k % 2 else (255, 255, 255))


def fx(d, t):
    kind, i, lt, L = segment(t)
    if kind == "work":
        confetti_burst(d, lt, i + 1)
    elif kind == "prep" and i > 0:
        confetti_burst(d, lt, 50 + i, n=60, x0=960, y0=300)
    elif kind == "outro":
        confetti_burst(d, lt, 99, n=160)
        confetti_burst(d, lt - 2.5, 98, n=120, x0=500, y0=400)
        confetti_burst(d, lt - 4.0, 97, n=120, x0=1420, y0=400)
        k0 = int(lt / 0.55)
        for k in range(max(0, k0 - 3), k0 + 1):
            firework(d, lt - k * 0.55, 300 + k)


def hud_sparkles(d, t, kind):
    spots = [(820, 40), (40, 245), (1860, 70), (1680, 250)] if kind in ("prep", "work") else [(300, 60), (1620, 300), (420, 330), (1540, 70)]
    for j, (x, y) in enumerate(spots):
        tw = math.sin(t * 3 + j * 1.9)
        if tw > 0:
            star(d, x, y, 30 * tw, (255, 255, 255))


def init():
    global RAYS, SHADOW
    BASES[:] = [make_base(w) for w in range(3)]
    CLOUDS[:] = [make_cloud(c) for c in ((255, 200, 235), (215, 235, 255), (200, 205, 240))]
    RAYS = make_rays()
    SHADOW = make_shadow()
    FLARES[:] = make_flares()


# ================================================================ audio (same as v1)
SR = 44100
def mtof(m):
    return 440 * 2 ** ((m - 69) / 12)


def audio():
    n = int(TOTAL * SR)
    mus, sfx = np.zeros(n), np.zeros(n)
    beat = 60 / 124
    chords = [[60, 64, 67], [55, 59, 62], [57, 60, 64], [53, 57, 60]]
    def add(buf, t0, sig):
        a = int(t0 * SR)
        if a >= n: return
        b = min(n, a + len(sig)); buf[a:b] += sig[:b - a]
    tt = lambda d: np.arange(int(d * SR)) / SR
    kt = tt(0.25); kick = np.sin(2 * np.pi * np.cumsum(50 + 110 * np.exp(-kt * 30)) / SR) * np.exp(-kt * 14)
    rng = np.random.default_rng(1)
    ht = tt(0.05); hat = np.diff(rng.standard_normal(len(ht) + 1)) * np.exp(-ht * 90) * 0.18
    ct = tt(0.15); clap = rng.standard_normal(len(ct)) * np.exp(-ct * 30) * 0.25
    def pluck(m, d, vol):
        x = tt(d); f = mtof(m)
        return (np.sin(2 * np.pi * f * x) + 0.35 * np.sin(4 * np.pi * f * x) + 0.15 * np.sin(6 * np.pi * f * x)) * np.exp(-x * 9) * vol
    def bass(m, d):
        x = tt(d); f = mtof(m)
        return sum(np.sin(2 * np.pi * f * k * x) / k for k in range(1, 6)) * np.minimum(1, x * 200) * np.exp(-x * 4) * 0.35
    def bell(m, d, vol):  # sparkle chime
        x = tt(d); f = mtof(m)
        return (np.sin(2 * np.pi * f * x) + 0.4 * np.sin(2 * np.pi * f * 2.76 * x)) * np.exp(-x * 6) * vol
    arp = [0, 1, 2, 1, 0, 2, 1, 2]
    for b in range(int(TOTAL / beat) + 1):
        t0 = b * beat
        kind, i, lt, L = segment(t0)
        en = kind == "work"
        ch = chords[(b // 4) % 4]
        if en or (kind == "intro" and lt > 4): add(mus, t0, kick * 0.9)
        if b % 2 == 1 and en: add(mus, t0, clap)
        add(mus, t0 + beat / 2, hat if en else hat * 0.5)
        add(mus, t0, bass(ch[0] - 24, beat * 0.9))
        add(mus, t0 + beat / 2, bass(ch[0] - 24, beat * 0.45))
        for k in range(2):
            add(mus, t0 + k * beat / 2, pluck(ch[arp[(b * 2 + k) % 8]] + 12, beat * 0.6, 0.22 if en else 0.16))
        if b % 8 == 0: add(mus, t0, bell(ch[2] + 24, 1.2, 0.08))
    def tone(f, d, vol=0.5):
        x = tt(d)
        return np.sin(2 * np.pi * f * x) * np.minimum(1, x * 300) * np.minimum(1, (d - x) * 60) * vol
    for i in range(len(EXS)):
        st = INTRO + i * (PREP + WORK)
        if i == 0 or EXS[i - 1][3] != EXS[i][3]:
            for k, m in enumerate([79, 84, 88, 91]):
                add(sfx, st + 0.2 + k * 0.09, bell(m, 0.8, 0.25))
        for k in (3, 2, 1): add(sfx, st + PREP - k, tone(880, 0.14))
        add(sfx, st + PREP, tone(1320, 0.45, 0.55))
        end = st + PREP + WORK
        for k in (3, 2, 1): add(sfx, end - k, tone(660, 0.08, 0.3))
        add(sfx, end, tone(1500, 0.18, 0.45)); add(sfx, end + 0.22, tone(1500, 0.3, 0.45))
    o = INTRO + len(EXS) * (PREP + WORK)
    for k, m in enumerate([72, 76, 79, 84]): add(sfx, o + k * 0.15, pluck(m, 0.6, 0.6))
    out = mus * 0.55 + sfx
    fade = np.ones(n); fl = int(3 * SR); fade[-fl:] = np.linspace(1, 0, fl); fade[:int(0.5 * SR)] = np.linspace(0, 1, int(0.5 * SR))
    out = np.tanh(out * fade * 1.2) * 0.85
    with wave.open(os.path.join(OUT, "audio.wav"), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((out * 32767).astype(np.int16).tobytes())


def thumbnail():
    img = draw_world(0, 40.0, 3.0).convert("RGBA")
    silhouette(img, pose("knees", 0.25, 0))
    paste_c(img, text_img("WARM UP RUN!", 250, sw=16), 960, 165)
    panel(img, (60, 820, 640, 1040), fill=(230, 40, 110, 240), border=(255, 255, 255))
    paste_c(img, text_img("COPY", 90, fill=(255, 255, 255), sw=5), 350, 875)
    paste_c(img, text_img("THE SHADOW!", 90, fill=(255, 255, 255), sw=5), 350, 975)
    panel(img, (1460, 880, 1860, 1030), fill=(20, 20, 45, 230), border=(255, 220, 40))
    paste_c(img, text_img("8 MIN", 100, fill=(255, 220, 40), sw=5), 1660, 955)
    img.convert("RGB").resize((1280, 720), Image.LANCZOS).save(os.path.join(OUT, "thumbnail.jpg"), quality=92)


def worker(k, n):
    init()
    a, b = NF * k // n, NF * (k + 1) // n
    p = subprocess.Popen([FF, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                          "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
                          os.path.join(OUT, f"part{k:02d}.mp4")], stdin=subprocess.PIPE)
    for f_ in range(a, b):
        p.stdin.write(frame(f_ / FPS).tobytes())
        if (f_ - a) % 300 == 0:
            print(f"w{k} {f_ - a}/{b - a}", flush=True)
    p.stdin.close(); p.wait()


if __name__ == "__main__":
    if "--preview" in sys.argv:
        init()
        for t in [float(x) for x in sys.argv[sys.argv.index("--preview") + 1].split(",")]:
            frame(t).save(os.path.join(OUT, f"prev_{t:07.2f}.jpg"), quality=85)
        thumbnail()
    elif "--worker" in sys.argv:
        k, n = int(sys.argv[sys.argv.index("--worker") + 1]), int(sys.argv[sys.argv.index("--worker") + 2])
        worker(k, n)
    else:
        n = int(os.environ.get("JOBS", "8"))
        init(); audio(); thumbnail()
        procs = [subprocess.Popen([sys.executable, __file__, "--worker", str(k), str(n)]) for k in range(n)]
        if any(p.wait() for p in procs):
            sys.exit("worker failed")
        lst = os.path.join(OUT, "parts.txt")
        with open(lst, "w") as f:
            for k in range(n):
                f.write(f"file 'part{k:02d}.mp4'\n")
        subprocess.run([FF, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-i", os.path.join(OUT, "audio.wav"),
                        "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest",
                        "-movflags", "+faststart", os.path.join(OUT, "warmup_v2.mp4")], check=True)
        for k in range(n):
            os.remove(os.path.join(OUT, f"part{k:02d}.mp4"))
        print("done", TOTAL)
