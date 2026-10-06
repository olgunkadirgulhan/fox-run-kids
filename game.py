"""Shared timeline for v4 (3D fox runner): segments, speed/distance, obstacle events."""
import math, os
import numpy as np

CFG = os.environ.get("WARMUP_CFG", "long")
SHORT = CFG.startswith("short")
SHORT_K = int(CFG[5:]) if SHORT else 0

FPS = 30
TOTAL = 42.0 if SHORT else 480.0
NF = int(TOTAL * FPS)
LANE = 1.15  # lane width (m)
PREP = 6.0

SEGS = [
    dict(kind="hook", t0=0, dur=12, world=0),
    dict(kind="game", t0=12, dur=42, world=0, gap=3.0, types="jd", n=1),
    dict(kind="ex", t0=54, dur=36, world=0, key="jacks", label="JUMPING JACKS"),
    dict(kind="game", t0=90, dur=42, world=0, gap=2.6, types="jdlr", n=2),
    dict(kind="ex", t0=132, dur=36, world=0, key="knees", label="HIGH KNEES"),
    dict(kind="game", t0=168, dur=42, world=1, gap=2.5, types="jdlr", n=3),
    dict(kind="ex", t0=210, dur=36, world=1, key="skater", label="SKATER HOPS"),
    dict(kind="game", t0=246, dur=42, world=1, gap=2.3, types="jdlr", n=4),
    dict(kind="ex", t0=288, dur=36, world=1, key="circles", label="ARM CIRCLES"),
    dict(kind="game", t0=324, dur=42, world=2, gap=2.15, types="jdlr", n=5),
    dict(kind="ex", t0=366, dur=36, world=2, key="reach", label="JUMP & REACH"),
    dict(kind="game", t0=402, dur=42, world=2, gap=2.0, types="jdlr", n=6),
    dict(kind="ex", t0=444, dur=21, world=2, key="breath", label="BIG BREATHS"),
    dict(kind="outro", t0=465, dur=15, world=2),
]
if SHORT:
    SEGS = [dict(kind="game", t0=0, dur=36, world=SHORT_K % 3, gap=2.35, types="jdlr", n=100 + SHORT_K, lead=2.3),
            dict(kind="outro", t0=36, dur=6, world=SHORT_K % 3)]
WORLDS = ["FOREST RUN", "BEACH RUN", "SNOW RUN"]


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
        return {"knees": 4.5, "skater": 3.5, "jacks": 3.0, "reach": 3.0}.get(s["key"], 2.0)
    return 4.0 if lt < 1.0 else 0.0


# distance along track at 90 Hz resolution (smooth speed changes)
HZ = 90
_n = int(TOTAL * HZ) + 4
DIST = np.zeros(_n)
_v = 7.0
for _k in range(1, _n):
    _v += (speed_target(_k / HZ) - _v) * (1 - math.exp(-1.6 / HZ))
    DIST[_k] = DIST[_k - 1] + _v / HZ


def dist(t):
    x = t * HZ
    k = int(x)
    k = max(0, min(_n - 2, k))
    f = x - k
    return DIST[k] * (1 - f) + DIST[k + 1] * f


# ------------------------------------------------------------------ events
def _rng(seed):
    s = [seed * 7919 + 13]
    def r():
        s[0] = (s[0] * 1103515245 + 12345) & 0x7FFFFFFF
        return s[0] / 0x7FFFFFFF
    return r


def build_events():
    ev = []
    lane = 0
    hook = [] if SHORT else [(2.0, "j"), (3.7, "l"), (5.3, "d"), (6.9, "r"), (8.6, "j"), (10.2, "d")]
    for t, ty in hook:
        ev.append((t, ty))
    for s in SEGS:
        if s["kind"] != "game":
            continue
        r = _rng(s["n"])
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
    out = []
    lane = 0
    for t, ty in ev:
        e = dict(t=t, s=dist(t))
        if ty == "j":
            e["type"] = "jump"
        elif ty == "d":
            e["type"] = "duck"
        else:
            # dodge out of the current lane; prefer the requested side when possible
            want = -1 if ty == "l" else 1
            to = lane + want
            if to < -1 or to > 1:
                to = lane - want
            if lane != 0 and abs(to) == 1 and to != 0:
                to = 0
            e["type"] = "left" if to < lane else "right"
            e["from"], e["to"] = lane, to
            lane = to
        e["lane"] = lane
        out.append(e)
    # bring the runner back to the centre lane before every non-game segment
    fixed = []
    for e in out:
        fixed.append(e)
    final = []
    lane = 0
    for i, e in enumerate(fixed):
        si, s = seg_at(e["t"])
        nxt_t = s["t0"] + s["dur"]
        if e["type"] in ("left", "right"):
            e["from"] = lane
            e["to"] = e["to"]
            e["type"] = "left" if e["to"] < lane else "right"
            if e["to"] == lane:
                continue
            lane = e["to"]
        final.append(e)
        later = [x for x in fixed[i + 1:] if seg_at(x["t"])[0] == si]
        if not later and lane != 0:
            tb = e["t"] + 1.6
            if tb < nxt_t - 0.8:
                final.append(dict(t=tb, s=dist(tb), type="left" if lane > 0 else "right", **{"from": lane, "to": 0}))
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
    """runner lateral position from dodge events (physics hop timing handled in motion4)."""
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
    print(len(EVENTS), "events; total distance", round(dist(TOTAL), 1))
    for e in EVENTS[:12]:
        print(e)
