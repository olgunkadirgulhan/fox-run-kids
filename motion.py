"""Physics-driven character motion: ballistic jumps, planted feet + two-bone IK,
spring-damper secondary motion, verlet ponytail. Produces packed joint arrays at 90 Hz."""
import math
import numpy as np
from render2 import segment, EXS, INTRO, PREP, WORK, OUTRO, TOTAL, Rx, Ry, Rz, sstep

G = 9.81
L1, L2 = 0.45, 0.43
REACH = 0.872
SIM_HZ, REC_HZ = 180, 90

ANG = ["pt", "pl", "sl", "ss", "st", "hn", "ht", "hs",
       "r_sf", "r_sa", "r_el", "l_sf", "l_sa", "l_el", "r_an", "l_an"]
POS = ["px", "py", "pz", "rx", "ry", "rz", "lx", "ly", "lz", "pole"]
CH = ANG + POS
CI = {k: i for i, k in enumerate(CH)}
# spring params per channel: (freq Hz, damping, coupling to pelvis vertical accel)
SPRING = {"sl": (2.2, 0.7, 0.9), "ss": (2.2, 0.75, 0), "st": (2.6, 0.65, 0), "pt": (3.0, 0.8, 0), "pl": (3.5, 0.8, 0),
          "hn": (2.4, 0.5, 1.4), "ht": (2.4, 0.6, 0), "hs": (2.4, 0.6, 0),
          "r_sf": (3.0, 0.5, 0), "l_sf": (3.0, 0.5, 0), "r_sa": (3.0, 0.5, -1.2), "l_sa": (3.0, 0.5, -1.2),
          "r_el": (3.6, 0.45, 1.0), "l_el": (3.6, 0.45, 1.0)}
FAST_ARMS = {"r_sf": (5.5, 0.42, 0), "l_sf": (5.5, 0.42, 0), "r_sa": (5.0, 0.45, 0), "l_sa": (5.0, 0.45, 0),
             "r_el": (6.0, 0.4, 0), "l_el": (6.0, 0.4, 0), "st": (4.0, 0.55, 0)}


def base(**kw):
    d = dict(px=0.0, py=0.985, pz=0.0, pt=0.0, pl=0.0, sl=3.0, ss=0.0, st=0.0, hn=0.0, ht=0.0, hs=0.0,
             r_sf=4.0, r_sa=9.0, r_el=14.0, l_sf=4.0, l_sa=9.0, l_el=14.0, r_an=0.0, l_an=0.0,
             rx=0.11, ry=0.08, rz=0.0, lx=-0.11, ly=0.08, lz=0.0, pole=0.25)
    d.update(kw)
    return d


def stand_h(foot_x, bend=0.845):
    dx = max(0.0, abs(foot_x) - 0.092)
    return 0.14 + math.sqrt(max(0.01, bend * bend - dx * dx))


def herm(p0, v0, p1, v1, dur, s):
    s2, s3 = s * s, s * s * s
    return (2 * s3 - 3 * s2 + 1) * p0 + (s3 - 2 * s2 + s) * dur * v0 + (-2 * s3 + 3 * s2) * p1 + (s3 - s2) * dur * v1


def hop(tau, P, tf, y0, k=0.8):
    """stance (compression) then ballistic flight; period P, flight time tf."""
    ts = P - tf
    v = G * tf / 2
    if tau < ts:
        s = tau / ts
        return y0 - k * v * ts * (s - s * s)
    q = tau - ts
    return y0 + v * q - G * q * q / 2


def bump(u, p=1.2):
    return math.sin(math.pi * min(1, max(0, u))) ** p


def heel_y(an):
    return 0.08 + 0.15 * math.sin(math.radians(max(0, an)))


# ------------------------------------------------------------------ exercises (tc = seconds since prep start)
def ex_run(tc, kind):
    T = {"run": 0.72, "knees": 0.64, "kicks": 0.70}[kind]
    tf = {"run": 0.11, "knees": 0.14, "kicks": 0.12}[kind]
    P = T / 2
    ts = P - tf
    d = base(py=hop(tc % P, P, tf, 0.972, 0.8))
    Hl, dz, an, A, lean = {"run": (0.24, 0.05, 30, 38, 6), "knees": (0.46, -0.12, 38, 55, 2),
                           "kicks": (0.44, 0.30, 55, 26, 9)}[kind]
    b = {}
    for sd, off in (("r", 0.0), ("l", P)):
        c = (tc - off) % T
        bb = 0.0 if c < ts else bump((c - ts) / (T - ts))
        b[sd] = bb
        s = 1 if sd == "r" else -1
        d[sd + "x"], d[sd + "y"], d[sd + "z"] = s * 0.11, 0.08 + Hl * bb, dz * bb
        d[sd + "_an"] = an * bb
    bR, bL = b["r"], b["l"]
    d.update(r_sf=12 + A * (bL - bR), l_sf=12 + A * (bR - bL), r_el=80 + 14 * bL, l_el=80 + 14 * bR, r_sa=14, l_sa=14,
             px=0.022 * (bL - bR), pl=4 * (bR - bL), st=6 * (bL - bR), pt=-4 * (bL - bR), sl=lean)
    d["ht"] = -0.7 * d["st"]
    return d


def ex_jacks(tc):
    T, tf = 1.1, 0.28
    P = T / 2
    ts = P - tf
    k = int(tc // P)
    tau = tc - k * P
    S0 = k % 2
    S1 = 1 - S0
    if tau < ts:
        o, fl = S0, 0.0
    else:
        q = (tau - ts) / tf
        o, fl = S0 + (S1 - S0) * sstep(q), bump(q, 1)
    lead = ts - 0.08
    oa = S0 if tau < lead else S0 + (S1 - S0) * sstep((tau - lead) / (tf + 0.04))
    d = base(py=hop(tau, P, tf, 0.962, 0.7))
    for sd, s in (("r", 1), ("l", -1)):
        d[sd + "x"] = s * (0.11 + 0.27 * o)
        d[sd + "_an"] = 30 * fl
        d[sd + "_sa"] = 10 + 158 * oa
        d[sd + "_el"] = 14 + 22 * math.sin(math.pi * oa)
        d[sd + "_sf"] = 6 + 10 * math.sin(math.pi * oa)
    d["hn"] = -4 * oa
    return d


def ex_circles(tc):
    th = 2 * math.pi * tc / 1.2
    d = base(rx=0.16, lx=-0.16, py=stand_h(0.16) - 0.008 * (1 + math.sin(2 * th)))
    for sd in ("r", "l"):
        d[sd + "_sa"] = 86 + 16 * math.cos(th)
        d[sd + "_sf"] = 4 + 16 * math.sin(th)
        d[sd + "_el"] = 6
    return d


def ex_squat(tc):
    ph = (tc / 2.4) % 1
    if ph < 0.42: dd = sstep(ph / 0.42)
    elif ph < 0.52: dd = 1.0
    elif ph < 0.92: dd = 1 - sstep((ph - 0.52) / 0.40)
    else: dd = 0.0
    d = base(rx=0.2, lx=-0.2, pole=0.55)
    d.update(py=stand_h(0.2) - 0.42 * dd, pz=0.20 * dd, sl=3 + 34 * dd, hn=-14 * dd,
             r_sf=6 + 82 * dd, l_sf=6 + 82 * dd, r_sa=12, l_sa=12, r_el=10, l_el=10)
    return d


def _punch_prof(x):
    x %= 1.0
    if x >= 0.5: return 0.0
    u = x / 0.5
    if u < 0.25: return 1 - (1 - u / 0.25) ** 3
    if u < 0.38: return 1.0
    return 1 - sstep((u - 0.38) / 0.5)


def ex_punch(tc):
    T = 0.9
    pr, pl = _punch_prof(tc / T), _punch_prof(tc / T + 0.5)
    d = base(rx=0.17, rz=0.08, lx=-0.17, lz=-0.08, pole=0.35)
    d["py"] = stand_h(0.17) - 0.05 + 0.012 * math.sin(2 * math.pi * 2 * tc / T)
    for sd, p in (("r", pr), ("l", pl)):
        d[sd + "_sf"] = 48 - 36 * p
        d[sd + "_sa"] = 22 + 146 * p
        d[sd + "_el"] = 128 * (1 - p) + 4 * p
        d[sd + "_an"] = 4
    d.update(ss=-7 * (pr - pl), st=6 * (pr - pl), pl=3 * (pr - pl), py=d["py"] + 0.02 * (pr + pl), sl=6, hn=-6 * (pr + pl))
    return d


def ex_shuffle(tc):
    T, Q = 2.4, 0.4
    ph = tc % T
    dirn = 1 if ph < T / 2 else -1
    hp = ph % (T / 2)
    j = min(2, int(hp / Q))
    u = (hp - j * Q) / Q
    c = -0.45 * dirn + dirn * 0.30 * j
    if u < 0.5:
        lead = c + dirn * (0.15 + 0.30 * sstep(u / 0.5)); trail = c - dirn * 0.15
        ll, tl = 0.06 * bump(u / 0.5, 1), 0.0
    else:
        lead = c + dirn * 0.45; trail = c - dirn * 0.15 + dirn * 0.30 * sstep((u - 0.5) / 0.5)
        ll, tl = 0.0, 0.06 * bump((u - 0.5) / 0.5, 1)
    xr, yr, xl, yl = (lead, ll, trail, tl) if dirn > 0 else (trail, tl, lead, ll)
    w = (xr - xl) / 2
    d = base(rx=xr, ry=0.08 + yr, lx=xl, ly=0.08 + yl, pole=0.4)
    d.update(px=(xr + xl) / 2, py=stand_h(w, 0.80) + 0.015 * math.sin(2 * math.pi * u), sl=16, ss=-4 * dirn, hn=-4,
             r_sf=38, l_sf=38, r_sa=16, l_sa=16, r_el=88, l_el=88, r_an=40 * yr / 0.06, l_an=40 * yl / 0.06)
    return d


def ex_reach(tc):
    T = 2.0
    tau = tc % T
    y0 = stand_h(0.14)
    v0 = 2.2
    t1, t2 = 0.55, 0.80
    tf = 2 * v0 / G
    t3 = t2 + tf
    t4, t5 = t3 + 0.25, t3 + 0.70
    yt = y0 + 0.05
    if tau < t1:
        py = y0 - 0.32 * sstep(tau / t1)
    elif tau < t2:
        py = herm(y0 - 0.32, 0, yt, v0, t2 - t1, (tau - t1) / (t2 - t1))
    elif tau < t3:
        q = tau - t2
        py = yt + v0 * q - G * q * q / 2
    elif tau < t4:
        py = herm(yt, -v0, y0 - 0.22, 0, t4 - t3, (tau - t3) / (t4 - t3))
    elif tau < t5:
        py = y0 - 0.22 + 0.22 * sstep((tau - t4) / (t5 - t4))
    else:
        py = y0
    crouch = max(0.0, y0 - py)
    if t1 < tau < t2:
        an = 32 * sstep((tau - (t1 + t2) / 2) / ((t2 - t1) / 2))
    elif t2 <= tau < t3:
        an = 35
    elif t3 <= tau < t3 + 0.05:
        an = 35 * (1 - (tau - t3) / 0.05)
    else:
        an = 0
    if tau < t1: sf = 6 - 52 * sstep(tau / t1)
    elif tau < t2 + 0.12: sf = -46 + 218 * sstep((tau - t1) / (t2 + 0.12 - t1))
    elif tau < t3: sf = 172
    elif tau < t4: sf = 172 - 110 * sstep((tau - t3) / (t4 - t3))
    elif tau < t5 + 0.2: sf = 62 - 56 * sstep((tau - t4) / (t5 + 0.2 - t4))
    else: sf = 6
    d = base(rx=0.14, lx=-0.14, pole=0.4)
    d.update(py=py, pz=0.45 * crouch, sl=3 + 100 * crouch, r_an=an, l_an=an, r_sf=sf, l_sf=sf, r_sa=14, l_sa=14,
             r_el=10, l_el=10, hn=-16 if t2 <= tau < t3 else -25 * crouch)
    d["ry"] = d["ly"] = heel_y(an) if py < yt + 0.01 else 0.08
    return d


def ex_skater(tc):
    T, tf = 1.8, 0.38
    Ps = T / 2
    ts = Ps - tf
    k = int(tc // Ps)
    tau = tc - k * Ps
    side = 1 if k % 2 == 0 else -1
    X = 0.34
    vx = 2 * X / tf
    if tau < ts:
        px = herm(side * X, side * 0.55 * vx, side * X, -side * 0.55 * vx, ts, tau / ts)
        f = 0.0
    else:
        q = tau - ts
        px = side * X - side * vx * q
        f = sstep(q / tf)
    def feet(sd_stance, sgn):
        stance = (sgn * 0.44, 0.08, 0.0)
        free = (sgn * 0.44 - sgn * 0.20, 0.24, 0.36)
        return stance, free
    st_now, fr_now = feet(None, side)
    st_nxt, fr_nxt = feet(None, -side)
    # foot on 'side' is stance now, becomes free next; other foot free now, stance next
    a_now, b_now = st_now, fr_now
    a_nxt, b_nxt = fr_nxt, st_nxt
    A = tuple(a_now[i] + (a_nxt[i] - a_now[i]) * f for i in range(3))
    B = tuple(b_now[i] + (b_nxt[i] - b_now[i]) * f for i in range(3))
    if f > 0:
        A = (A[0], A[1] + 0.08 * bump(f, 1), A[2])
        B = (B[0], B[1] + 0.05 * bump(f, 1), B[2])
    sideA = "r" if side > 0 else "l"
    sideB = "l" if side > 0 else "r"
    d = base(pole=0.35)
    d[sideA + "x"], d[sideA + "y"], d[sideA + "z"] = A
    d[sideB + "x"], d[sideB + "y"], d[sideB + "z"] = B
    d[sideA + "_an"] = 35 * f
    d[sideB + "_an"] = 35 * (1 - f)
    d.update(px=px, py=hop(tau, Ps, tf, 0.90, 0.55), sl=26)
    # arms swing across: opposite arm forward
    def arms(sgn):
        fwd, back = ("l", "r") if sgn > 0 else ("r", "l")
        return {fwd + "_sf": 60, fwd + "_sa": -22, fwd + "_el": 30, back + "_sf": -35, back + "_sa": 14, back + "_el": 20}
    a0, a1 = arms(side), arms(-side)
    for kk in a0:
        d[kk] = a0[kk] + (a1[kk] - a0[kk]) * f
    sg = side + (-side - side) * f
    d.update(ss=7 * sg, st=-12 * sg, ht=8 * sg)
    return d


def _bend_sig(ph):
    keys = [(0.0, 0), (0.2, 1), (0.32, 1), (0.5, 0), (0.7, -1), (0.82, -1), (1.0, 0)]
    for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
        if t0 <= ph < t1:
            return v0 + (v1 - v0) * sstep((ph - t0) / (t1 - t0))
    return 0.0


def ex_bend(tc):
    b = _bend_sig((tc / 3.6) % 1)
    bp, bn = max(0, b), max(0, -b)
    d = base(rx=0.2, lx=-0.2)
    d.update(py=stand_h(0.2), px=-0.05 * b, ss=30 * b, pl=-3 * b, hs=8 * b,
             l_sa=10 + 158 * bp - 5 * bn, l_el=14 + 14 * bp, r_sa=10 + 158 * bn - 5 * bp, r_el=14 + 14 * bn)
    return d


def ex_breath(tc):
    ph = (tc / 5.0) % 1
    if ph < 0.42: dd = sstep(ph / 0.42)
    elif ph < 0.55: dd = 1.0
    elif ph < 0.97: dd = 1 - sstep((ph - 0.55) / 0.42)
    else: dd = 0.0
    an = 22 * dd
    d = base(rx=0.12, lx=-0.12)
    d.update(r_an=an, l_an=an, ry=heel_y(an), ly=heel_y(an), py=0.985 + (heel_y(an) - 0.08),
             r_sa=10 + 156 * dd, l_sa=10 + 156 * dd, r_el=14, l_el=14, r_sf=4 + 6 * dd, l_sf=4 + 6 * dd, sl=3 - 7 * dd, hn=-14 * dd)
    return d


def ex_wave(t):
    w = math.sin(2 * math.pi * t / 2.8)
    s = math.sin(2 * math.pi * t / 0.8)
    d = base(rx=0.13, lx=-0.13)
    d.update(px=0.035 * w, py=0.978, pl=-3 * w, r_sa=140 + 16 * s, r_el=32 + 12 * math.sin(2 * math.pi * t / 0.8 + 1),
             r_sf=10, hs=4 + 3 * s)
    return d


def ex_cheer(tc):
    P, tf = 0.62, 0.30
    tau = tc % P
    ts = P - tf
    fl = bump((tau - ts) / tf, 1) if tau >= ts else 0.0
    st = 1 - fl
    d = base(rx=0.14, lx=-0.14, py=hop(tau, P, tf, 0.97, 0.8))
    d.update(r_an=30 * fl, l_an=30 * fl, r_sa=150, l_sa=150, r_sf=15, l_sf=15, r_el=20 + 30 * st, l_el=20 + 30 * st, hn=-12)
    return d


FN = {"run": lambda tc: ex_run(tc, "run"), "knees": lambda tc: ex_run(tc, "knees"), "kicks": lambda tc: ex_run(tc, "kicks"),
      "jacks": ex_jacks, "circles": ex_circles, "squat": ex_squat, "punch": ex_punch, "shuffle": ex_shuffle,
      "reach": ex_reach, "skater": ex_skater, "bend": ex_bend, "breath": ex_breath}


def raw_target(t):
    kind, i, lt, L = segment(t)
    if kind == "intro":
        return ex_wave(t)
    if kind == "outro":
        return ex_cheer(lt) if lt < OUTRO - 6 else ex_wave(t)
    tc = lt if kind == "prep" else PREP + lt
    return FN[EXS[i][0]](tc)


def blend(a, b, s):
    out = {k: a[k] + (b[k] - a[k]) * s for k in a}
    for sd in ("r", "l"):  # step feet instead of sliding
        dist = math.hypot(b[sd + "x"] - a[sd + "x"], b[sd + "z"] - a[sd + "z"])
        if dist > 0.03:
            out[sd + "y"] += 0.08 * bump(s, 1)
    return out


def target(t):
    kind, i, lt, L = segment(t)
    cur = raw_target(t)
    BL = 0.7
    if kind == "prep" and lt < BL:
        st = t - lt
        if i == 0:
            prev = ex_wave(t)
        else:
            prev = FN[EXS[i - 1][0]](PREP + WORK + lt)
        return blend(prev, cur, sstep(lt / BL)), kind, i
    if kind == "outro":
        if lt < BL:
            return blend(FN[EXS[-1][0]](PREP + WORK + lt), cur, sstep(lt / BL)), kind, i
        if OUTRO - 6 <= lt < OUTRO - 6 + BL:
            return blend(ex_cheer(lt), cur, sstep((lt - (OUTRO - 6)) / BL)), kind, i
    return cur, kind, i


# ------------------------------------------------------------------ skeleton (FK upper body + IK legs)
DOWN = np.array([0.0, -1.0, 0.0])
NPTS = 36


def ik(H, A, pole):
    v = A - H
    d = np.linalg.norm(v)
    if d > REACH:
        A = H + v / d * REACH
        v, d = A - H, REACH
    d = max(d, 0.2)
    u = v / d
    ca = (L1 * L1 + d * d - L2 * L2) / (2 * L1 * d)
    sa = math.sqrt(max(0.0, 1 - ca * ca))
    p = pole - np.dot(pole, u) * u
    n = np.linalg.norm(p)
    p = p / n if n > 1e-6 else np.array([0, 0, -1.0])
    K = H + L1 * (ca * u + sa * p)
    return K, H + u * d


def skeleton(s, tail):
    g = lambda k: s[CI[k]]
    pel = np.array([g("px"), g("py"), g("pz")])
    Rp = Ry(g("pt")) @ Rz(g("pl"))
    Rm = Rp @ Ry(g("st") / 2) @ Rz(-g("ss") / 2) @ Rx(-g("sl") / 2)
    Rt = Rp @ Ry(g("st")) @ Rz(-g("ss")) @ Rx(-g("sl"))
    mid = pel + Rm @ np.array([0, 0.25, 0])
    nb = mid + Rt @ np.array([0, 0.27, 0])
    Rh = Rt @ Ry(g("ht")) @ Rz(-g("hs")) @ Rx(-g("hn"))
    head = nb + Rh @ np.array([0, 0.155, -0.01])
    torso = [pel + Rp @ np.array([0.165, -0.03, 0]), mid + Rm @ np.array([0.135, -0.04, 0]),
             mid + Rt @ np.array([0.16, 0.12, 0]), mid + Rt @ np.array([0.17, 0.215, 0]), nb + Rt @ np.array([0.06, -0.005, 0]),
             nb + Rt @ np.array([-0.06, -0.005, 0]), mid + Rt @ np.array([-0.17, 0.215, 0]), mid + Rt @ np.array([-0.16, 0.12, 0]),
             mid + Rm @ np.array([-0.135, -0.04, 0]), pel + Rp @ np.array([-0.165, -0.03, 0]),
             pel + Rp @ np.array([-0.07, -0.13, 0]), pel + Rp @ np.array([0.07, -0.13, 0])]
    arms, legs = [], []
    for sgn, sd in ((1, "r"), (-1, "l")):
        sh = mid + Rt @ np.array([sgn * 0.175, 0.215, 0])
        Ra = Rt @ Rz(sgn * g(sd + "_sa")) @ Rx(g(sd + "_sf"))
        el = sh + Ra @ DOWN * 0.29
        Rf = Rt @ Rz(sgn * g(sd + "_sa")) @ Rx(g(sd + "_sf") + g(sd + "_el"))
        wr = el + Rf @ DOWN * 0.255
        arms.append([sh, el, wr, wr + Rf @ DOWN * 0.055])
        hip = pel + Rp @ np.array([sgn * 0.092, -0.06, 0])
        A = np.array([g(sd + "x"), g(sd + "y"), g(sd + "z")])
        pole = Rp @ np.array([sgn * g("pole"), 0.0, -1.0])
        kn, an = ik(hip, A, pole)
        Rfo = Ry(g("pt") * 0.5 - sgn * 8) @ Rx(-g(sd + "_an"))
        legs.append([hip, kn, an, an + Rfo @ np.array([0, -0.045, 0.045]), an + Rfo @ np.array([0, -0.05, -0.16])])
    anchor = head + Rh @ np.array([0, 0.02, 0.09])
    pts = torso + arms[0] + arms[1] + legs[0] + legs[1] + [nb, head, pel, anchor] + list(tail[:2])
    return np.array(pts), Rh


def unpack(a):
    return dict(torso=list(a[0:12]), r_arm=tuple(a[12:16]), l_arm=tuple(a[16:20]), r_leg=tuple(a[20:25]),
                l_leg=tuple(a[25:30]), nb=a[30], head=a[31], pel=a[32], tail=[a[33], a[34], a[35]])


# ------------------------------------------------------------------ simulation
def simulate(progress=False):
    dt = 1.0 / SIM_HZ
    n = int(TOTAL * SIM_HZ) + 2
    tg, _, _ = target(0.0)
    s = np.array([tg[k] for k in CH], float)
    vel = np.zeros(len(CH))
    py_hist = [tg["py"]] * 3
    tail = None
    tail_prev = None
    recs = []
    step_rec = SIM_HZ // REC_HZ
    for k in range(n):
        t = k * dt
        tg, kind, i = target(min(t, TOTAL - 1e-6))
        # idle life
        tg["sl"] += 0.8 * math.sin(2 * math.pi * t / 3.7)
        tg["ht"] += 2.0 * math.sin(2 * math.pi * t / 5.3)
        py_hist = py_hist[1:] + [tg["py"]]
        acc = (py_hist[2] - 2 * py_hist[1] + py_hist[0]) / (dt * dt)
        acc = max(-30.0, min(30.0, acc))
        fast = kind == "work" and EXS[i][0] == "punch" or (kind == "prep" and EXS[i][0] == "punch")
        for c, key in enumerate(CH):
            x = tg[key]
            sp = (FAST_ARMS.get(key) if fast else None) or SPRING.get(key)
            if sp is None:
                s[c] = x
                continue
            f, z, cpl = sp
            w = 2 * math.pi * f
            a = w * w * (x - s[c]) - 2 * z * w * vel[c] + cpl * 60 * acc
            vel[c] += a * dt
            s[c] += vel[c] * dt
        # ponytail verlet in world space (3 points)
        if k % step_rec == 0 or tail is None:
            pts, Rh = skeleton(s, tail if tail is not None else np.zeros((3, 3)))
            anchor = pts[33]
            rest = [anchor + Rh @ np.array([0, -0.06 * j, 0.035 * j]) for j in range(1, 4)]
        if tail is None:
            tail = np.array([anchor + np.array([0, -0.06 * j, 0.03 * j]) for j in range(1, 4)])
            tail_prev = tail.copy()
        nt = tail + (tail - tail_prev) * 0.985 + np.array([0, -G, 0]) * dt * dt
        tail_prev = tail
        tail = nt
        prev = anchor
        hc = pts[31]
        for j in range(3):
            v = tail[j] - prev
            L = np.linalg.norm(v) or 1e-6
            tail[j] = prev + v / L * 0.065
            # keep outside head sphere
            hv = tail[j] - hc
            hl = np.linalg.norm(hv)
            if hl < 0.12:
                tail[j] = hc + hv / (hl or 1e-6) * 0.12
            prev = tail[j]
        tail += (np.array(rest) - tail) * 0.06
        if k % step_rec == 0:
            pts, _ = skeleton(s, tail)
            pts[33:36] = [pts[33], tail[0], tail[1]]
            full = np.vstack([pts[:34], tail[0:2]])
            recs.append(full)
            if progress and len(recs) % 9000 == 0:
                print("sim", len(recs), flush=True)
    out = np.array(recs)
    # store last tail point instead of anchor duplication: layout = 33 anchor, 34 tail0, 35 tail1
    return out
