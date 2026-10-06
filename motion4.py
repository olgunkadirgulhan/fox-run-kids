"""v4 motion: fox runner. Run cycle + physics events (jump / duck / dodge), exercise segments,
spring secondary motion, verlet tail. Output: anim4.npy (N_rec, 51, 3) at 90 Hz."""
import math
import numpy as np
import game as Gm
import motion as M
from motion import base, stand_h, herm, bump, sstep, G, CH, CI, SPRING, ik, Rx, Ry, Rz, DOWN

REC_HZ, SIM_HZ = 90, 180


def lerpd(a, b, w):
    return {k: a[k] + (b[k] - a[k]) * w for k in a}


def run_dict(t, lx):
    d = M.ex_run(t, "run")
    d["px"] += lx
    d["rx"] += lx
    d["lx"] += lx
    return d


def ev_jump(u, lx):
    tf = 0.56
    v = G * tf / 2
    ttk, tl = -tf / 2, tf / 2
    y0 = 0.975
    if u < ttk - 0.30: py = y0
    elif u < ttk - 0.13: py = y0 - 0.14 * sstep((u - (ttk - 0.30)) / 0.17)
    elif u < ttk: py = herm(y0 - 0.14, 0, y0 + 0.04, v, 0.13, (u - (ttk - 0.13)) / 0.13)
    elif u < tl:
        q = u - ttk
        py = y0 + 0.04 + v * q - G * q * q / 2
    elif u < tl + 0.22: py = herm(y0 + 0.04, -v, y0 - 0.13, 0, 0.22, (u - tl) / 0.22)
    elif u < tl + 0.45: py = y0 - 0.13 + 0.13 * sstep((u - tl - 0.22) / 0.23)
    else: py = y0
    fl = bump((u - ttk) / tf, 1) if ttk <= u < tl else 0.0
    crouch = max(0.0, y0 - py) / 0.14
    if u < ttk: sf = 12 - 52 * sstep((u - (ttk - 0.30)) / 0.30)
    elif u < tl: sf = -40 + 170 * sstep((u - ttk) / 0.2)
    else: sf = 130 - 118 * sstep((u - tl) / 0.4)
    d = base(px=lx, py=py, rx=lx + 0.12, lx=lx - 0.12, pole=0.3)
    d.update(ry=0.08 + 0.48 * fl, ly=0.08 + 0.48 * fl, rz=-0.06 * fl, lz=-0.06 * fl,
             r_an=30 * fl + (25 * sstep((u - (ttk - 0.08)) / 0.08) if ttk - 0.08 < u < ttk else 0),
             sl=5 + 22 * crouch, r_sf=sf, l_sf=sf, r_sa=22, l_sa=22, r_el=30, l_el=30, hn=-10 * fl)
    d["l_an"] = d["r_an"]
    return d


def ev_duck(u, lx):
    if u < -0.4: dd = sstep((u + 0.7) / 0.3)
    elif u < 0.2: dd = 1.0
    else: dd = 1 - sstep((u - 0.2) / 0.4)
    d = base(px=lx, rx=lx + 0.19, lx=lx - 0.19, pole=0.5)
    d.update(py=stand_h(0.19) - 0.47 * dd, pz=0.2 * dd, sl=3 + 40 * dd, hn=-24 * dd,
             r_sf=12 + 18 * dd, l_sf=12 + 18 * dd, r_sa=14 + 44 * dd, l_sa=14 + 44 * dd, r_el=80 + 62 * dd, l_el=80 + 62 * dd)
    return d


def ev_dodge(u, a, b):
    tf = 0.32
    v = G * tf / 2
    ttk, tl = -0.45, -0.45 + tf
    y0 = 0.965
    if u < ttk - 0.2: py = y0
    elif u < ttk: py = y0 - 0.08 * math.sin(math.pi * (u - (ttk - 0.2)) / 0.2)
    elif u < tl:
        q = u - ttk
        py = y0 + v * q - G * q * q / 2
    elif u < tl + 0.2: py = herm(y0, -v, y0 - 0.09, 0, 0.2, (u - tl) / 0.2)
    elif u < tl + 0.45: py = y0 - 0.09 + 0.09 * sstep((u - tl - 0.2) / 0.25)
    else: py = y0
    if u < ttk: px = a
    elif u < tl: px = a + (b - a) * (u - ttk) / tf
    else: px = b
    fl = bump((u - ttk) / tf, 1) if ttk <= u < tl else 0.0
    dirn = 1 if b > a else -1
    lean = bump((u - (ttk - 0.2)) / 0.85, 1)
    fx = a if u < ttk else (b if u >= tl else px)
    d = base(px=px, py=py, rx=fx + 0.12 + 0.12 * fl, lx=fx - 0.12 - 0.12 * fl, pole=0.3)
    d.update(ry=0.08 + 0.1 * fl, ly=0.08 + 0.1 * fl, r_an=25 * fl, l_an=25 * fl,
             ss=-12 * dirn * lean, st=6 * dirn * lean, sl=8, hs=6 * dirn * lean,
             r_sa=14 + 50 * lean, l_sa=14 + 50 * lean, r_el=40, l_el=40, r_sf=20, l_sf=20)
    return d


def game_target(t):
    lx = Gm.lane_x(t)
    d = run_dict(t, lx)
    for e in Gm.EVENTS:
        u = t - e["t"]
        if u < -0.8:
            break
        if u > 0.9:
            continue
        if e["type"] == "jump" and -0.62 <= u <= 0.75:
            w = min(1.0, (u + 0.62) / 0.12, (0.75 - u) / 0.2)
            d = lerpd(d, ev_jump(u, lx), sstep(w))
        elif e["type"] == "duck" and -0.72 <= u <= 0.65:
            w = min(1.0, (u + 0.72) / 0.12, (0.65 - u) / 0.15)
            d = lerpd(d, ev_duck(u, lx), sstep(w))
        elif e["type"] in ("left", "right") and -0.7 <= u <= 0.3:
            w = min(1.0, (u + 0.7) / 0.1, (0.3 - u) / 0.15)
            d = lerpd(d, ev_dodge(u, e["from"] * Gm.LANE, e["to"] * Gm.LANE), sstep(w))
    return d


def seg_target(i, t):
    s = Gm.SEGS[i]
    lt = t - s["t0"]
    if s["kind"] in ("hook", "game"):
        return game_target(t), 0.0
    if s["kind"] == "ex":
        return M.FN[s["key"]](lt), 0.0
    # outro: slow down, turn to face camera, cheer, wave
    if lt < 1.6:
        d = lerpd(run_dict(t, 0.0), base(), sstep(lt / 1.6))
        return d, 0.0
    if lt < 3.0:
        q = (lt - 1.6) / 1.4
        d = base()
        for sd, ph in (("r", 0.0), ("l", 0.5)):
            d[sd + "y"] = 0.08 + 0.07 * bump((q * 2 + ph) % 1, 1)
        return d, 180.0 * sstep(q)
    if lt < 9.0:
        return M.ex_cheer(lt - 3.0), 180.0
    d = M.ex_wave(t)
    if lt < 9.6:
        d = lerpd(M.ex_cheer(lt - 3.0), d, sstep((lt - 9.0) / 0.6))
    return d, 180.0


def target(t):
    i, s = Gm.seg_at(t)
    d, yaw = seg_target(i, t)
    lt = t - s["t0"]
    if i > 0 and lt < 0.8 and s["kind"] != "outro":
        p, _ = seg_target(i - 1, t)
        d = M.blend(p, d, sstep(lt / 0.8))
    return d, yaw, i


# ------------------------------------------------------------------ skeleton
def skeleton(s, tail, yaw):
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
    pts = torso + arms[0] + arms[1] + legs[0] + legs[1] + [nb, head, pel, mid]
    rots = [Rp, Rm, Rt, Rh]
    if abs(yaw) > 1e-6:
        Y = Ry(yaw)
        c = np.array([pel[0], 0, pel[2]])
        pts = [c + Y @ (p - c) for p in pts]
        rots = [Y @ r for r in rots]
    return pts, rots


def tail_anchor(pts, rots):
    pel, Rp = pts[32], rots[0]
    offs = [(0, -0.13, 0.20), (0, -0.27, 0.27), (0, -0.40, 0.30), (0, -0.50, 0.27)]
    return pel + Rp @ np.array([0, -0.05, 0.11]), [pel + Rp @ np.array(o) for o in offs]


def simulate():
    dt = 1.0 / SIM_HZ
    n = int(Gm.TOTAL * SIM_HZ) + 2
    tg, yaw, _ = target(0.0)
    s = np.array([tg[k] for k in CH], float)
    vel = np.zeros(len(CH))
    pyh = [tg["py"]] * 3
    tail = tail_prev = None
    recs = []
    for k in range(n):
        t = min(k * dt, Gm.TOTAL - 1e-6)
        tg, yaw, si = target(t)
        tg["sl"] += 0.8 * math.sin(2 * math.pi * t / 3.7)
        tg["ht"] += 2.0 * math.sin(2 * math.pi * t / 5.3)
        pyh = pyh[1:] + [tg["py"]]
        acc = max(-30.0, min(30.0, (pyh[2] - 2 * pyh[1] + pyh[0]) / (dt * dt)))
        for c, key in enumerate(CH):
            sp = SPRING.get(key)
            if sp is None:
                s[c] = tg[key]
                continue
            f, z, cpl = sp
            w = 2 * math.pi * f
            vel[c] += (w * w * (tg[key] - s[c]) - 2 * z * w * vel[c] + cpl * 60 * acc) * dt
            s[c] += vel[c] * dt
        pts, rots = skeleton(s, None, yaw)
        anc, rest = tail_anchor(pts, rots)
        if tail is None:
            tail = np.array(rest)
            tail_prev = tail.copy()
        nt = tail + (tail - tail_prev) * 0.97 + np.array([0, -G * 0.6, 0]) * dt * dt
        tail_prev, tail = tail, nt
        prev = anc
        for j in range(4):
            v = tail[j] - prev
            tail[j] = prev + v / (np.linalg.norm(v) or 1e-6) * 0.14
            prev = tail[j]
        tail += (np.array(rest) - tail) * 0.07
        if k % (SIM_HZ // REC_HZ) == 0:
            rows = list(pts) + [r[:, j] for r in rots for j in range(3)] + list(tail) + [np.array([Gm.lane_x(t), yaw, 0.0])]
            recs.append(np.array(rows))
    return np.array(recs)


# record layout
IDX = dict(torso=0, r_arm=12, l_arm=16, r_leg=20, l_leg=25, nb=30, head=31, pel=32, mid=33, rots=34, tail=46, cam=50)

if __name__ == "__main__":
    import os, time
    t0 = time.time()
    A = simulate()
    np.save(os.path.join(os.path.dirname(os.path.abspath(__file__)), "anim4.npy" if Gm.CFG == "long" else "anim_%s.npy" % Gm.CFG), A)
    print(A.shape, round(time.time() - t0, 1), "s", np.isnan(A).sum())
