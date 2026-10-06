"""v4 post: HUD/cue overlays on Blender frames + game audio + encode.
python post4.py [--preview t1,t2,...] | [--worker k n] | (all)"""
import math, os, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw
import render2 as R
import game as Gm

HERE = os.path.dirname(os.path.abspath(__file__))
FR = os.environ.get("FRAMES_DIR") or os.path.join(HERE, "frames_" + Gm.TAG)
W, H, FPS = (1080, 1920, Gm.FPS) if Gm.SHORT else (1920, 1080, Gm.FPS)
R.W, R.H = W, H
TAG = Gm.TAG
CUE_X, CUE_Y, CUE_S = (540, 610, 0.85) if Gm.SHORT else (960, 175, 1.0)
sstep = R.sstep
CUE = {"jump": ("JUMP!", (60, 205, 90)), "duck": ("DUCK!", (255, 150, 30)),
       "left": ("LEFT!", (70, 160, 255)), "right": ("RIGHT!", (70, 160, 255))}
WACC = [(60, 205, 90), (255, 170, 40), (90, 170, 255), (255, 140, 40), (255, 90, 170), (120, 140, 255),
        (255, 120, 30), (80, 220, 255), (120, 200, 60), (40, 190, 110)]


# ------------------------------------------------------------------ coin collection times (mirror of bl_scene logic)
def coin_list():
    out = []
    for e in Gm.EVENTS:
        lane = e["lane"] * Gm.LANE
        if e["type"] == "jump":
            out += [(e["s"] + (j - 2) * 0.9, lane) for j in range(5)]
        elif e["type"] == "duck":
            out += [(e["s"] + (j - 1.5) * 0.9, lane) for j in range(4)]
        else:
            out += [(e["s"] + 3.0 + j * 1.2, e["to"] * Gm.LANE) for j in range(5)]
    return out


def collect_times():
    ts = []
    for s_, x in coin_list():
        k = int(np.searchsorted(Gm.DIST, s_ - 0.35))
        t = k / Gm.HZ
        if t < Gm.TOTAL and abs(Gm.lane_x(t) - x) < 0.6:
            ts.append(t)
    return sorted(ts)


COINT = collect_times()
COINT_ARR = np.array(COINT)


# ------------------------------------------------------------------ drawing helpers
def arrow(d, cx, cy, size, kind, col):
    s = size
    if kind == "jump":
        pts = [(0, -1), (0.8, -0.1), (0.35, -0.1), (0.35, 0.9), (-0.35, 0.9), (-0.35, -0.1), (-0.8, -0.1)]
    elif kind == "duck":
        pts = [(0, 1), (0.8, 0.1), (0.35, 0.1), (0.35, -0.9), (-0.35, -0.9), (-0.35, 0.1), (-0.8, 0.1)]
    elif kind == "left":
        pts = [(-1, 0), (-0.1, -0.8), (-0.1, -0.35), (0.9, -0.35), (0.9, 0.35), (-0.1, 0.35), (-0.1, 0.8)]
    else:
        pts = [(1, 0), (0.1, -0.8), (0.1, -0.35), (-0.9, -0.35), (-0.9, 0.35), (0.1, 0.35), (0.1, 0.8)]
    P = [(cx + x * s, cy + y * s) for x, y in pts]
    d.polygon([(x + 5, y + 6) for x, y in P], fill=(20, 20, 35))
    d.polygon(P, fill=col, outline=(255, 255, 255), width=6)


def cue(img, t):
    for e in Gm.EVENTS:
        u = t - e["t"]
        if u < -1.7 or u > 0.4:
            continue
        txt, col = CUE[e["type"]]
        a = min(1.0, (u + 1.7) / 0.18, (0.4 - u) / 0.15)
        pop = (1.0 + 0.25 * max(0.0, 1 - abs(u) / 0.25) + 0.15 * max(0.0, 1 - (u + 1.7) / 0.2)) * CUE_S
        cx, cy = CUE_X, CUE_Y
        bw = int(560 * pop)
        bh = int(200 * pop)
        R.panel(img, (cx - bw // 2, cy - bh // 2, cx + bw // 2, cy + bh // 2), fill=col + (int(225 * a),), r=40, border=(255, 255, 255))
        d = ImageDraw.Draw(img)
        arrow(d, cx - bw // 2 + 105 * pop, cy, 70 * pop, e["type"], (255, 255, 255))
        R.paste_c(img, R.text_img(txt, int(120 * pop), fill=(255, 255, 255), sw=8), cx + 70 * pop, cy - 4, alpha=a)
        # timing bar shrinking to the moment of action
        if u < 0:
            f = -u / 1.7
            d.rounded_rectangle([cx - 230, cy + bh // 2 + 14, cx + 230, cy + bh // 2 + 34], 10, fill=(20, 20, 40))
            d.rounded_rectangle([cx - 230, cy + bh // 2 + 14, cx - 230 + 460 * f, cy + bh // 2 + 34], 10, fill=(255, 255, 255))
        if abs(u) < 0.25:
            for k in range(10):
                ang = k * 0.628 + t
                rr = 300 + 120 * (u + 0.25) / 0.5
                R.star(d, cx + math.cos(ang) * rr, cy + math.sin(ang) * rr * 0.45, 20, R.RAINBOW[k % 6])
        return


def coin_hud(img, t):
    n = int(np.searchsorted(COINT_ARR, t))
    d = ImageDraw.Draw(img)
    x, y = (740, 120) if Gm.SHORT else (1590, 300)
    R.panel(img, (x - 10, y - 45, x + 300, y + 45), fill=(20, 20, 45, 190), border=(255, 210, 60))
    bump = 0.0
    if n > 0:
        dt = t - COINT[n - 1]
        bump = max(0.0, 1 - dt / 0.25)
    r = 32 * (1 + 0.25 * bump)
    d.ellipse([x + 40 - r, y - r, x + 40 + r, y + r], fill=(235, 160, 20))
    d.ellipse([x + 40 - r * 0.78, y - r * 0.78, x + 40 + r * 0.78, y + r * 0.78], fill=(255, 210, 50))
    R.paste_l(img, R.text_img(f"x {n}", 66, fill=(255, 255, 255), sw=4), x + 92, y - 40)
    # +1 pops near the fox
    for tc in COINT[max(0, n - 4):n]:
        dt = t - tc
        if 0 <= dt < 0.6:
            cx = W / 2 + Gm.lane_x(tc) * 0.4 * 380
            by = 900 if Gm.SHORT else 560
            R.paste_c(img, R.text_img("+1", 60, fill=(255, 220, 50), sw=4), cx + 90, by - dt * 220, alpha=1 - dt / 0.6)
            R.star(d, cx + 40, by + 40 - dt * 150, 30 * (1 - dt / 0.6), (255, 255, 255))


def big_banner(img, text, y, size, alpha, fill=(255, 220, 40), scale=1.0):
    R.paste_c(img, R.text_img(text, size, fill=fill, sw=max(6, size // 11)), 960, y, scale=scale, alpha=alpha)


def seg_timer(img, rem, total, col):
    R.timer(img, rem, total, col)


def progress(img, t):
    segs = [s for s in Gm.SEGS if s["kind"] in ("game", "ex")]
    n = len(segs)
    x0, y0, w, h, g = 330, 1036, 1260, 22, 6
    sw = (w - g * (n - 1)) / n
    d = ImageDraw.Draw(img)
    for i, s in enumerate(segs):
        x = x0 + i * (sw + g)
        d.rounded_rectangle([x - 2, y0 - 2, x + sw + 2, y0 + h + 2], 9, fill=(255, 255, 255))
        d.rounded_rectangle([x, y0, x + sw, y0 + h], 8, fill=(30, 30, 55))
        f = min(1.0, max(0.0, (t - s["t0"]) / s["dur"]))
        if f > 0:
            d.rounded_rectangle([x, y0, x + max(h, sw * f), y0 + h], 8, fill=WACC[s["world"]] if s["kind"] == "game" else (255, 90, 165))


def hud(img, t):
    i, s = Gm.seg_at(t)
    lt = t - s["t0"]
    wi = s["world"]
    acc = WACC[wi]
    d = ImageDraw.Draw(img)
    if s["kind"] == "hook":
        if lt < 3.1:
            a = min(1.0, lt * 4, (3.1 - lt) * 4)
            big_banner(img, "CAN YOU DODGE IT ALL?", 905, 120, a, scale=1 + 0.06 * math.sin(lt * 8))
        elif lt < 6.6:
            a = min(1.0, (lt - 3.1) * 4, (6.6 - lt) * 4)
            R.panel(img, (330, 850, 1590, 965), fill=(230, 40, 110, int(230 * a)), border=(255, 255, 255))
            big_banner(img, "STAND UP & PLAY ALONG!", 907, 84, a, fill=(255, 255, 255))
        elif lt > 7.0:
            a = min(1.0, (lt - 7.0) * 3, (12.0 - lt) * 3)
            big_banner(img, "IMMERSIVE INTERACTIVE", 805, 92, a)
            big_banner(img, "WARM UP RUN!", 925, 150, a, fill=(255, 255, 255), scale=0.9 + 0.1 * min(1, (lt - 7.0) * 3))
    elif s["kind"] == "game":
        R.panel(img, (30, 30, 600, 140), border=acc)
        R.paste_l(img, R.text_img(f"OBSTACLE RUN {s['n']}/6", 70, fill=(255, 255, 255), sw=4), 58, 45)
        seg_timer(img, s["dur"] - lt, s["dur"], acc)
        coin_hud(img, t)
        if lt < 2.6:
            a = min(1.0, lt * 4, (2.6 - lt) * 3)
            big_banner(img, "OBSTACLE RUN!", 470, 150, a, scale=0.8 + 0.2 * min(1, lt * 4))
            big_banner(img, "JUMP • DUCK • DODGE", 600, 70, a, fill=(255, 255, 255))
        nxt = Gm.SEGS[i + 1] if i + 1 < len(Gm.SEGS) else None
        if nxt and nxt["kind"] == "ex" and s["dur"] - lt < 3.2:
            R.panel(img, (1370, 860, 1890, 1000), border=(255, 90, 165))
            R.paste_l(img, R.text_img("NEXT:", 44, fill=(255, 255, 255), sw=3), 1398, 876)
            R.paste_l(img, R.text_img(nxt["label"], 56), 1398, 928)
    elif s["kind"] == "ex":
        prep = s.get("prep", Gm.PREP)
        work = s["dur"] - prep
        R.panel(img, (30, 30, 830, 250), border=acc)
        if lt < prep:
            R.paste_l(img, R.text_img("GET READY!", 54, fill=acc, sw=4), 62, 45)
            rem = prep - lt
            seg_timer(img, rem, prep, acc)
            if rem <= 3:
                n = int(math.ceil(rem))
                fr = n - rem
                R.paste_c(img, R.text_img(str(n), 330, fill=(255, 255, 255), sw=14), 960, 520, scale=1.3 - 0.3 * min(1, fr * 4),
                          alpha=1 - max(0, fr - 0.7) / 0.3)
            else:
                R.panel(img, (650, 930, 1270, 1012), border=acc)
                R.paste_c(img, R.text_img("WATCH THE MOVE...", 54, fill=(255, 255, 255), sw=3), 960, 971)
        else:
            wl = lt - prep
            R.paste_l(img, R.text_img("WARM UP MOVE", 54, fill=acc, sw=4), 62, 45)
            seg_timer(img, work - wl, work, acc)
            if wl < 1.0:
                R.paste_c(img, R.text_img("GO!", 300, fill=acc, sw=14), 960, 520, scale=0.8 + 0.4 * wl, alpha=1 - wl)
                R.confetti_burst(d, wl, i + 7)
            if 10 < wl < 13 or 19 < wl < 21:
                msg = "KEEP GOING!" if wl < 15 else "YOU'RE DOING GREAT!"
                R.panel(img, (600, 930, 1320, 1012), border=acc)
                R.paste_c(img, R.text_img(msg, 60, fill=(255, 255, 255), sw=3), 960, 971)
        R.paste_l(img, R.text_img(s["label"], 104), 57, 116)
    else:  # outro
        n = len(COINT)
        a = min(1.0, max(0.0, (lt - 1.0) * 2))
        big_banner(img, "GREAT JOB!", 170, 220, a, scale=1 + 0.04 * math.sin(lt * 5))
        if lt > 2.0:
            big_banner(img, f"YOU COLLECTED {n} COINS!", 335, 80, min(1, (lt - 2.0) * 2), fill=(255, 255, 255))
        if lt > 8:
            R.panel(img, (540, 920, 1380, 1012), border=acc)
            R.paste_c(img, R.text_img("DRINK SOME WATER & SEE YOU NEXT TIME!", 46, fill=(255, 255, 255), sw=3), 960, 966)
        R.confetti_burst(d, lt - 1.0, 99, n=160)
        R.confetti_burst(d, lt - 3.5, 98, n=120, x0=500, y0=400)
        R.confetti_burst(d, lt - 5.0, 97, n=120, x0=1420, y0=400)
        k0 = int(max(0, lt - 1.0) / 0.55)
        for k in range(max(0, k0 - 3), k0 + 1):
            R.firework(d, lt - 1.0 - k * 0.55, 300 + k)
    if s["kind"] != "hook":
        progress(img, t)
    # world banner + white flash on world change
    for j in range(1, len(Gm.SEGS)):
        sw_ = Gm.SEGS[j]
        if sw_["world"] != Gm.SEGS[j - 1]["world"]:
            ts = sw_["t0"]
            if -0.3 < t - ts < 0.4:
                fa = 1 - abs(t - ts - 0.05) / 0.35
                ov = Image.new("RGBA", (W, H), (255, 255, 255, int(255 * max(0, min(1, fa)))))
                img.alpha_composite(ov)
            if 0.3 < t - ts < 3.8:
                a = min(1.0, (t - ts - 0.3) * 3, (3.8 - (t - ts)) * 2)
                big_banner(img, f"WELCOME TO {Gm.WORLDS[sw_['world']]}!", 430, 110, a, fill=(255, 255, 255))
    cue(img, t)


INTRO = {"dodge": ("CAN YOU DODGE", "THEM ALL?"), "levelup": ("3 LEVELS!", "CAN YOU KEEP UP?"),
         "movemix": ("COPY", "THE FOX!"), "count": ("CAN YOU DO", "")}
OUTRO = {"dodge": ("HOW MANY DID", "YOU DODGE?"), "levelup": ("YOU BEAT", "LEVEL 3!"), "movemix": ("GREAT", "MOVES!"),
         "count": ("DID YOU DO", "ALL OF THEM?")}


def hud_short(img, t):
    i, s = Gm.seg_at(t)
    lt = t - s["t0"]
    d = ImageDraw.Draw(img)
    acc = WACC[s["world"]]
    fmt = Gm.FORMAT
    ex_segs = [x for x in Gm.SEGS if x["kind"] == "ex"]
    tot = len(Gm.EVENTS)
    done = sum(1 for e in Gm.EVENTS if t > e["t"] + 0.3)
    if t < 2.4:  # format intro
        a = min(1.0, t * 4, (2.4 - t) * 3)
        l1, l2 = INTRO[fmt]
        if fmt == "count":
            l1, l2 = f"CAN YOU DO {Gm.rep_target(ex_segs[0])}", ex_segs[0]["label"] + "?"
        big_banner2(img, l1, 255, 112, a)
        big_banner2(img, l2, 385, 130, a, fill=(255, 255, 255))
    if s["kind"] == "game":
        R.panel(img, (30, 75, 400, 165), fill=(20, 20, 45, 190), border=acc)
        label = f"LEVEL {s['n']}/3" if fmt == "levelup" else f"DODGED {done}/{tot}"
        R.paste_l(img, R.text_img(label, 62, fill=(255, 255, 255), sw=4), 52, 85)
        coin_hud(img, t)
        if fmt == "levelup" and s["n"] > 1 and lt < 1.6:
            a = min(1.0, lt * 4, (1.6 - lt) * 3)
            big_banner2(img, f"LEVEL {s['n']}!", 330, 170, a)
            big_banner2(img, "FASTER!", 470, 100, a, fill=(255, 255, 255))
    elif s["kind"] == "ex":
        prep = s.get("prep", Gm.PREP)
        R.panel(img, (40, 70, 1040, 200), fill=(20, 20, 45, 200), border=acc)
        big_banner2(img, s["label"], 135, 96, 1.0)
        if lt < prep:
            rem = prep - lt
            if rem <= 3:
                n = int(math.ceil(rem))
                fr = n - rem
                R.paste_c(img, R.text_img(str(n), 300, fill=(255, 255, 255), sw=14), 540, 560,
                          scale=1.3 - 0.3 * min(1, fr * 4), alpha=1 - max(0, fr - 0.7) / 0.3)
            if fmt == "movemix":
                k = ex_segs.index(s) + 1
                big_banner2(img, f"MOVE {k} OF {len(ex_segs)}", 300, 70, 1.0, fill=(255, 255, 255))
        else:
            wl = lt - prep
            if wl < 0.9:
                R.paste_c(img, R.text_img("GO!", 260, fill=acc, sw=14), 540, 560, scale=0.8 + 0.4 * wl, alpha=1 - wl / 0.9)
            if fmt == "count":
                n, tgt = Gm.rep_count(s, t), Gm.rep_target(s)
                R.panel(img, (290, 1560, 790, 1720), fill=(20, 20, 45, 215), border=acc)
                big_banner2(img, f"{n} / {tgt}", 1640, 120, 1.0, fill=(255, 220, 50))
        f = min(1.0, max(0.0, (lt - prep) / (s["dur"] - prep)))
        d.rounded_rectangle([90, 1790, 990, 1822], 14, fill=(255, 255, 255))
        d.rounded_rectangle([94, 1794, 986, 1818], 12, fill=(30, 30, 55))
        d.rounded_rectangle([94, 1794, 94 + max(24, 892 * f), 1818], 12, fill=acc)
    else:
        a = min(1.0, lt * 3)
        l1, l2 = OUTRO[fmt]
        big_banner2(img, l1, 300, 120, a)
        big_banner2(img, l2, 440, 140, a, fill=(255, 255, 255))
        if lt > 1.5:
            R.panel(img, (190, 1560, 890, 1690), fill=(230, 40, 110, 235), border=(255, 255, 255))
            big_banner2(img, "PLAY AGAIN!", 1625, 96, min(1, (lt - 1.5) * 3), fill=(255, 255, 255))
        R.confetti_burst(d, lt, 99, n=140, x0=540, y0=700)
        R.confetti_burst(d, lt - 1.8, 98, n=100, x0=300, y0=600)
        R.confetti_burst(d, lt - 3.0, 97, n=100, x0=780, y0=600)
    if s["kind"] == "game":
        f = min(1.0, t / max(1e-6, sum(x["dur"] for x in Gm.SEGS if x["kind"] == "game")))
        d.rounded_rectangle([90, 1790, 990, 1822], 14, fill=(255, 255, 255))
        d.rounded_rectangle([94, 1794, 986, 1818], 12, fill=(30, 30, 55))
        d.rounded_rectangle([94, 1794, 94 + max(24, 892 * f), 1818], 12, fill=acc)
    cue(img, t)


def big_banner2(img, text, y, size, alpha, fill=(255, 220, 40)):
    ti = R.text_img(text, size, fill=fill, sw=max(6, size // 11))
    sc = min(1.0, (W - 60) / ti.width)
    R.paste_c(img, ti, W / 2, y, scale=sc, alpha=alpha)


def frame(f):
    p = os.path.join(FR, "f%05d.jpg" % f)
    img = Image.open(p).convert("RGBA")
    (hud_short if Gm.SHORT else hud)(img, f / FPS)
    return img.convert("RGB")


# ------------------------------------------------------------------ audio
SR = 44100


def audio():
    n = int(Gm.TOTAL * SR)
    mus, sfx = np.zeros(n), np.zeros(n)
    tt = lambda d: np.arange(int(d * SR)) / SR
    def add(buf, t0, sig):
        a = int(t0 * SR)
        if a < 0 or a >= n: return
        b = min(n, a + len(sig)); buf[a:b] += sig[:b - a]
    mt = lambda m: 440 * 2 ** ((m - 69) / 12)
    rng = np.random.default_rng(3)
    kt = tt(0.25); kick = np.sin(2 * np.pi * np.cumsum(50 + 120 * np.exp(-kt * 30)) / SR) * np.exp(-kt * 13)
    ht = tt(0.05); hat = np.diff(rng.standard_normal(len(ht) + 1)) * np.exp(-ht * 90) * 0.16
    ct = tt(0.16); clap = rng.standard_normal(len(ct)) * np.exp(-ct * 28) * 0.22
    def pluck(m, d, vol):
        x = tt(d); f = mt(m)
        return (np.sin(2 * np.pi * f * x) + 0.35 * np.sin(4 * np.pi * f * x) + 0.12 * np.sin(6 * np.pi * f * x)) * np.exp(-x * 8) * vol
    def bass(m, d):
        x = tt(d); f = mt(m)
        return sum(np.sin(2 * np.pi * f * k * x) / k for k in range(1, 6)) * np.minimum(1, x * 200) * np.exp(-x * 4) * 0.33
    def bell(m, d, vol):
        x = tt(d); f = mt(m)
        return (np.sin(2 * np.pi * f * x) + 0.4 * np.sin(2 * np.pi * f * 2.76 * x)) * np.exp(-x * 7) * vol
    def sweep(f0, f1, d, vol):
        x = tt(d)
        f = f0 * (f1 / f0) ** (x / d)
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * x / d) * vol
    def whoosh(d, vol):
        x = tt(d)
        z = rng.standard_normal(len(x))
        z = np.convolve(z, np.ones(12) / 12, mode="same")
        return z * np.sin(np.pi * x / d) ** 2 * vol
    beat = 60 / Gm.TEMPO
    progs = [[[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]], [[48, 52, 55], [55, 59, 62], [57, 60, 64], [53, 57, 60]],
             [[53, 57, 60], [55, 59, 62], [52, 55, 59], [57, 60, 64]]]
    prog = [[n + Gm.KEY_SHIFT for n in c] for c in progs[Gm.SEED % 3]]
    arp = [0, 1, 2, 1, 2, 1, 0, 2]
    for b in range(int(Gm.TOTAL / beat) + 1):
        t0 = b * beat
        i, s = Gm.seg_at(t0)
        lt = t0 - s["t0"]
        en = s["kind"] in ("hook", "game") or (s["kind"] == "ex" and lt >= s.get("prep", Gm.PREP))
        ch = prog[(b // 4) % 4]
        if en or s["kind"] == "outro":
            add(mus, t0, kick)
        if b % 2 == 1 and en:
            add(mus, t0, clap)
        add(mus, t0 + beat / 2, hat if en else hat * 0.5)
        if en:
            add(mus, t0 + beat / 4, hat * 0.5); add(mus, t0 + 3 * beat / 4, hat * 0.5)
        add(mus, t0, bass(ch[0] - 24, beat * 0.9))
        add(mus, t0 + beat / 2, bass(ch[0] - 12 if en else ch[0] - 24, beat * 0.45))
        for k in range(2):
            add(mus, t0 + k * beat / 2, pluck(ch[arp[(b * 2 + k) % 8]] + 12, beat * 0.6, 0.2 if en else 0.14))
        if b % 8 == 0:
            add(mus, t0, bell(ch[2] + 24, 1.2, 0.07))
    for e in Gm.EVENTS:
        add(sfx, e["t"] - 1.7, sweep(600, 900, 0.12, 0.25))
        if e["type"] == "jump":
            add(sfx, e["t"] - 0.3, sweep(260, 950, 0.32, 0.4))
        elif e["type"] == "duck":
            add(sfx, e["t"] - 0.6, sweep(800, 220, 0.35, 0.35))
        else:
            add(sfx, e["t"] - 0.5, whoosh(0.35, 0.5))
    for tc in COINT:
        add(sfx, tc, bell(88, 0.25, 0.18)); add(sfx, tc + 0.06, bell(95, 0.3, 0.16))
    def tone(f, d, vol=0.5):
        x = tt(d)
        return np.sin(2 * np.pi * f * x) * np.minimum(1, x * 300) * np.minimum(1, (d - x) * 60) * vol
    for j, s in enumerate(Gm.SEGS):
        if s["kind"] == "ex":
            st = s["t0"]
            pr = s.get("prep", Gm.PREP)
            for k in (3, 2, 1): add(sfx, st + pr - k, tone(880, 0.14))
            add(sfx, st + pr, tone(1320, 0.45, 0.55))
            if Gm.SHORT and Gm.FORMAT == "count":
                cyc, per = Gm.REPS.get(s["key"], (1.0, 1))
                for r_ in range(1, Gm.rep_target(s) + 1):
                    add(sfx, st + pr + r_ * cyc / per, tone(1760, 0.05, 0.18))
            end = st + s["dur"]
            add(sfx, end, tone(1500, 0.18, 0.45)); add(sfx, end + 0.22, tone(1500, 0.3, 0.45))
        if s["kind"] == "game":
            for k, m in enumerate([72, 76, 79, 84]):
                add(sfx, s["t0"] + 0.1 + k * 0.08, pluck(m, 0.5, 0.45))
        if j > 0 and s["world"] != Gm.SEGS[j - 1]["world"]:
            for k, m in enumerate([79, 84, 88, 91, 96]):
                add(sfx, s["t0"] + k * 0.07, bell(m, 0.8, 0.22))
    o = Gm.SEGS[-1]["t0"]
    for k, m in enumerate([72, 76, 79, 84, 88]):
        add(sfx, o + 1.0 + k * 0.13, pluck(m, 0.7, 0.55))
    out = mus * 0.5 + sfx
    fade = np.ones(n); fl = int(3 * SR); fade[-fl:] = np.linspace(1, 0, fl)
    out = np.tanh(out * fade * 1.2) * 0.85
    with wave.open(os.path.join(HERE, "audio_%s.wav" % TAG), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((out * 32767).astype(np.int16).tobytes())


def worker(k, n):
    a, b = Gm.NF * k // n, Gm.NF * (k + 1) // n
    p = subprocess.Popen([R.FF, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                          "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
                          os.path.join(HERE, f"p_{TAG}_{k:02d}.mp4")], stdin=subprocess.PIPE)
    for f_ in range(a, b):
        p.stdin.write(frame(f_).tobytes())
    p.stdin.close(); p.wait()


def thumb_frame():
    e = next(e for e in Gm.EVENTS if e["type"] == "jump" and e["t"] > 14)
    return int(round(e["t"] * FPS))


def thumbnail(src=None, out=None):
    img = Image.open(src or os.path.join(FR, "f%05d.jpg" % thumb_frame())).convert("RGBA")
    R.paste_c(img, R.text_img(Gm.WORLDS[Gm.FEATURED], 110, fill=(255, 255, 255), sw=9), 960, 270)
    R.paste_c(img, R.text_img("JUMP! DUCK! DODGE!", 150, sw=12), 960, 130)
    R.panel(img, (60, 830, 700, 1040), fill=(230, 40, 110, 240), border=(255, 255, 255))
    R.paste_c(img, R.text_img("KIDS WARM UP", 84, fill=(255, 255, 255), sw=5), 380, 885)
    R.paste_c(img, R.text_img("RUN GAME!", 84, fill=(255, 220, 40), sw=5), 380, 980)
    R.panel(img, (1480, 880, 1860, 1030), fill=(20, 20, 45, 230), border=(255, 220, 40))
    R.paste_c(img, R.text_img("8 MIN", 100, fill=(255, 220, 40), sw=5), 1670, 955)
    img.convert("RGB").resize((1280, 720), Image.LANCZOS).save(out or os.path.join(HERE, "thumbnail_%s.jpg" % TAG), quality=92)


def encode_range(a, b, out):
    p = subprocess.Popen([R.FF, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                          "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    for f_ in range(a, b):
        p.stdin.write(frame(f_).tobytes())
    p.stdin.close()
    if p.wait():
        sys.exit("ffmpeg failed")


if __name__ == "__main__":
    if "--range" in sys.argv:
        i = sys.argv.index("--range")
        encode_range(int(sys.argv[i + 1]), int(sys.argv[i + 2]), sys.argv[i + 3])
        sys.exit()
    if "--audio" in sys.argv:
        audio()
        sys.exit()
    if "--preview" in sys.argv:
        for t in [float(x) for x in sys.argv[sys.argv.index("--preview") + 1].split(",")]:
            frame(int(round(t * FPS))).save(os.path.join(HERE, f"pp_{t:07.2f}.jpg"), quality=85)
    elif "--worker" in sys.argv:
        worker(int(sys.argv[sys.argv.index("--worker") + 1]), int(sys.argv[sys.argv.index("--worker") + 2]))
    else:
        n = int(os.environ.get("JOBS", "8"))
        audio()
        if not Gm.SHORT:
            thumbnail()
        procs = [subprocess.Popen([sys.executable, __file__, "--worker", str(k), str(n)]) for k in range(n)]
        if any(p.wait() for p in procs):
            sys.exit("worker failed")
        with open(os.path.join(HERE, "p_%s.txt" % TAG), "w") as fh:
            for k in range(n):
                fh.write(f"file 'p_{TAG}_{k:02d}.mp4'\n")
        subprocess.run([R.FF, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", os.path.join(HERE, "p_%s.txt" % TAG),
                        "-i", os.path.join(HERE, "audio_%s.wav" % TAG), "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac",
                        "-b:a", "192k", "-shortest", "-movflags", "+faststart", os.path.join(HERE, "warmup_v4.mp4" if not Gm.SHORT else "short_%s.mp4" % Gm.CFG)], check=True)
        for k in range(n):
            os.remove(os.path.join(HERE, f"p_{TAG}_{k:02d}.mp4"))
        print("done")
