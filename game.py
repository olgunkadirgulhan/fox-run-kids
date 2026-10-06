"""Shared timeline for the fox runner videos.

WARMUP_CFG selects what is produced:
  long:YYYY-MM-DD      8-minute obstacle run + warm-up moves (published on that date)
  short:YYYY-MM-DD:K   ~42 s vertical dodge challenge, K = 1..3 (slot of the day)
Everything (worlds, obstacle order, moves, speeds, music, outfit) is derived
deterministically from the date so every video differs but re-runs reproduce."""
import math, os, datetime
import numpy as np

CFG = os.environ.get("WARMUP_CFG", "long:2026-10-10")
_p = CFG.split(":")
KIND = _p[0]
DATE = datetime.date.fromisoformat(_p[1]) if len(_p) > 1 else datetime.date(2026, 10, 10)
SLOT = int(_p[2]) if len(_p) > 2 else 0
SHORT = KIND == "short"

FPS = 30
LANE = 1.15
PREP = 6.0

# world kits (visuals live in bl_scene.py)
KITS = ["FOREST", "BEACH", "SNOW", "DESERT", "CANDY LAND", "CITY", "AUTUMN", "SPACE", "FARM", "JUNGLE"]
ROTATION = [4, 3, 6, 5, 9, 8, 7, 0, 1, 2]  # featured "new world" per week
WEEK0 = datetime.date(2026, 10, 5)
WEEK = max(0, (DATE - WEEK0).days // 7)
FEATURED = ROTATION[WEEK % len(ROTATION)]
SEED = DATE.toordinal() * 10 + SLOT + (0 if SHORT else 7)


def _rng(seed):
    s = [seed * 7919 + 13]
    def r():
        s[0] = (s[0] * 1103515245 + 12345) & 0x7FFFFFFF
        return s[0] / 0x7FFFFFFF
    return r


_r = _rng(SEED)
# worlds seen so far (featured ones only become available once introduced)
UNLOCKED = [ROTATION[i % len(ROTATION)] for i in range(WEEK + 1)] + [0, 1, 2]
UNLOCKED = list(dict.fromkeys(UNLOCKED))


def pick_other(exclude):
    pool = [k for k in UNLOCKED if k not in exclude] or [k for k in range(len(KITS)) if k not in exclude]
    return pool[int(_r() * len(pool))]


EX_POOL = [("jacks", "JUMPING JACKS"), ("knees", "HIGH KNEES"), ("skater", "SKATER HOPS"), ("circles", "ARM CIRCLES"),
           ("reach", "JUMP & REACH"), ("kicks", "BUTT KICKS"), ("squat", "SQUATS"), ("punch", "SKY PUNCHES")]

if SHORT:
    TOTAL = 42.0
    W0 = FEATURED if SLOT == 1 else pick_other([FEATURED] if SLOT == 2 else [])
    SEGS = [dict(kind="game", t0=0, dur=36, world=W0, gap=2.2 + 0.3 * _r(), types="jdlr", n=1, lead=2.3),
            dict(kind="outro", t0=36, dur=6, world=W0)]
else:
    TOTAL = 480.0
    w1 = FEATURED
    w2 = pick_other([w1])
    w3 = pick_other([w1, w2])
    order = list(range(len(EX_POOL)))
    for i in range(len(order) - 1, 0, -1):
        j = int(_r() * (i + 1))
        order[i], order[j] = order[j], order[i]
    ex = [EX_POOL[k] for k in order[:5]]
    SEGS = [dict(kind="hook", t0=0, dur=12, world=w1)]
    t, n = 12, 1
    worlds = [w1, w1, w2, w2, w3, w3]
    for r in range(6):
        SEGS.append(dict(kind="game", t0=t, dur=42, world=worlds[r], gap=[3.0, 2.6, 2.5, 2.3, 2.15, 2.0][r],
                         types="jd" if r == 0 else "jdlr", n=r + 1))
        t += 42
        if r < 5:
            SEGS.append(dict(kind="ex", t0=t, dur=36, world=worlds[r], key=ex[r][0], label=ex[r][1]))
            t += 36
    SEGS.append(dict(kind="ex", t0=t, dur=21, world=w3, key="breath", label="BIG BREATHS"))
    t += 21
    SEGS.append(dict(kind="outro", t0=t, dur=TOTAL - t, world=w3))

NF = int(TOTAL * FPS)
WORLDS = {k: KITS[k] + " RUN" for k in range(len(KITS))}
USED_WORLDS = sorted({s["world"] for s in SEGS})
OUTFITS = [(0.02, 0.55, 0.62), (0.75, 0.08, 0.35), (0.1, 0.25, 0.8), (0.95, 0.55, 0.05), (0.35, 0.12, 0.65), (0.05, 0.5, 0.15)]
OUTFIT = OUTFITS[WEEK % len(OUTFITS)]
TEMPO = 120 + int(_r() * 14)
KEY_SHIFT = int(_r() * 5) - 2


def seg_at(t):
    for i, s in enumerate(SEGS):
        if s["t0"] <= t < s["t0"] + s["dur"]:
            return i, s
    return len(SEGS) - 1, SEGS[-1]


def speed_target(t):
    i, s = seg_at(t)
    lt = t - s["t0"]
    if s["kind"] == "hook":
        return 7.0
    if s["kind"] == "game":
        return 6.6 if SHORT else 6.0 + 0.25 * s["n"]
    if s["kind"] == "ex":
        if lt < PREP:
            return 3.0
        return {"knees": 4.5, "skater": 3.5, "jacks": 3.0, "reach": 3.0, "kicks": 4.0}.get(s["key"], 2.0)
    return 4.0 if lt < 1.0 else 0.0


HZ = 90
_n = int(TOTAL * HZ) + 4
DIST = np.zeros(_n)
_v = speed_target(0)
for _k in range(1, _n):
    _v += (speed_target(_k / HZ) - _v) * (1 - math.exp(-1.6 / HZ))
    DIST[_k] = DIST[_k - 1] + _v / HZ


def dist(t):
    x = t * HZ
    k = max(0, min(_n - 2, int(x)))
    f = x - k
    return DIST[k] * (1 - f) + DIST[k + 1] * f


def build_events():
    ev = []
    if not SHORT:
        ev += [(2.0, "j"), (3.7, "l"), (5.3, "d"), (6.9, "r"), (8.6, "j"), (10.2, "d")]
    for s in SEGS:
        if s["kind"] != "game":
            continue
        r = _rng(SEED * 31 + s["n"])
        t = s["t0"] + s.get("lead", 4.0)
        end = s["t0"] + s["dur"] - 3.0
        last = []
        while t < end:
            ty = s["types"][int(r() * len(s["types"]))]
            if len(last) >= 2 and last[-1] == last[-2] == ty:
                continue
            ev.append((t, ty))
            last.append(ty)
            t += s["gap"] + (r() - 0.5) * 0.5
    ev.sort()
    out, lane = [], 0
    for t, ty in ev:
        e = dict(t=t)
        if ty == "j":
            e["type"] = "jump"
        elif ty == "d":
            e["type"] = "duck"
        else:
            want = -1 if ty == "l" else 1
            to = lane + want
            if to < -1 or to > 1:
                to = lane - want
            if lane != 0 and abs(to) == 1:
                to = 0
            if to == lane:
                continue
            e["type"] = "left" if to < lane else "right"
            e["from"], e["to"] = lane, to
            lane = to
        out.append(e)
    final, lane = [], 0
    for i, e in enumerate(out):
        si, s = seg_at(e["t"])
        if e["type"] in ("left", "right"):
            if e["to"] == lane:
                continue
            e["from"] = lane
            e["type"] = "left" if e["to"] < lane else "right"
            lane = e["to"]
        final.append(e)
        later = [x for x in out[i + 1:] if seg_at(x["t"])[0] == si]
        if not later and lane != 0:
            tb = e["t"] + 1.6
            if tb < s["t0"] + s["dur"] - 0.8:
                final.append(dict(t=tb, type="left" if lane > 0 else "right", **{"from": lane, "to": 0}))
                lane = 0
    lane = 0
    for e in final:
        e["s"] = dist(e["t"])
        if e["type"] in ("left", "right"):
            lane = e["to"]
        e["lane"] = lane
    return final


EVENTS = build_events()


def lane_x(t):
    x = 0.0
    for e in EVENTS:
        if e["type"] not in ("left", "right"):
            continue
        t0, t1 = e["t"] - 0.45, e["t"] - 0.13
        if t < t0:
            break
        a, b = e["from"] * LANE, e["to"] * LANE
        x = b if t >= t1 else a + (b - a) * (t - t0) / (t1 - t0)
    return x


if __name__ == "__main__":
    print(CFG, "week", WEEK, "featured", KITS[FEATURED], "worlds", [KITS[w] for w in USED_WORLDS], "events", len(EVENTS),
          "tempo", TEMPO)
    for s in SEGS:
        print(" ", s["kind"], s["t0"], s["dur"], KITS[s["world"]], s.get("label", ""))
TAG = CFG.replace(":", "_")
