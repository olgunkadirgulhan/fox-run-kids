#!/usr/bin/env python3
"""Bigger Than You Think — gerçek ölçülerle boyut karşılaştırmaları (2026-10-14, Fox Run kanalının yeni konsepti).

Ölçüler resmî/yaygın kaynaklardan (CTBUH bina yükseklikleri, üretici uzunlukları, müze/rekor kayıtları); her açıklamada
yazar. Görsel kimlik (diğer kanallara benzemesin): lacivert teknik çizim (blueprint), beyaz çizgi sanatı, ölçü okları,
Barlow Condensed + JetBrains Mono, Kanadalı anlatıcı (en-CA-LiamNeural). Emoji yok, krem zemin yok.

Short kurguları (15): taller2, lineup5, humans, stackfit, guess, rank3, truefalse, oddone, sideways, percent, floors,
fields, reveal, scaleman, closer.  Uzun (16:9): lineup (12-16 nesne tek tek, ~4 dk).

  python bigger.py --dry-run [--kurgu taller2] [--long]
  python bigger.py --auto        # günde 4 Short + 1 uzun, publishAt ile ABD saatine
"""
import asyncio
import csv
import json
import math
import os
import random
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
FD = HERE / 'fonts' / 'bigger'
OUT = HERE / 'out' / 'bigger'
LOG = HERE / 'records' / 'bigger_published.csv'
FPS = 30
BG, BG2, GRID, LINE, DIM, CYAN, YEL, RED = (14, 42, 92), (10, 30, 70), (30, 66, 124), (235, 242, 255), (140, 170, 215), (90, 220, 255), (255, 214, 64), (255, 96, 96)
BOLD, MED, MONO = str(FD / 'BarlowCondensed-Bold.ttf'), str(FD / 'BarlowCondensed-Medium.ttf'), str(FD / 'JetBrainsMono.ttf')
VOICE = os.environ.get('BG_VOICE', 'en-CA-LiamNeural')
DRY = '--dry-run' in sys.argv
HUMAN = 1.7

# id: (EKRAN ADI, konuşma adı, metre, yön 'h' yükseklik / 'l' uzunluk, şekil, kaynak)
OBJ = {
    'burj': ('BURJ KHALIFA', 'the Burj Khalifa', 828, 'h', 'spire', 'CTBUH'),
    'merdeka': ('MERDEKA 118', 'Merdeka 118', 678.9, 'h', 'spire', 'CTBUH'),
    'shanghai': ('SHANGHAI TOWER', 'the Shanghai Tower', 632, 'h', 'tower', 'CTBUH'),
    'wtc': ('ONE WORLD TRADE', 'One World Trade Center', 541.3, 'h', 'spire', 'CTBUH'),
    'taipei': ('TAIPEI 101', 'Taipei 101', 508, 'h', 'tower', 'CTBUH'),
    'empire': ('EMPIRE STATE', 'the Empire State Building', 443, 'h', 'spire', 'to the antenna tip'),
    'eiffel': ('EIFFEL TOWER', 'the Eiffel Tower', 330, 'h', 'eiffel', 'with antennas, 2022'),
    'needle': ('SPACE NEEDLE', 'the Space Needle', 184, 'h', 'needle', 'official height'),
    'pyramid': ('GREAT PYRAMID', 'the Great Pyramid of Giza', 138.5, 'h', 'pyramid', 'current height'),
    'saturnv': ('SATURN V', 'the Saturn V rocket', 110.6, 'h', 'rocket', 'NASA'),
    'bigben': ('BIG BEN TOWER', 'Big Ben\'s tower', 96, 'h', 'tower', 'Elizabeth Tower, UK Parliament'),
    'liberty': ('STATUE OF LIBERTY', 'the Statue of Liberty', 93, 'h', 'statue', 'ground to torch, NPS'),
    'pisa': ('TOWER OF PISA', 'the Leaning Tower of Pisa', 56, 'h', 'tower', 'about 56 m'),
    'redeemer': ('CHRIST THE REDEEMER', 'Christ the Redeemer', 38, 'h', 'statue', 'statue + pedestal'),
    'hyperion': ('HYPERION TREE', 'Hyperion, the tallest known tree', 116.1, 'h', 'tree', 'coast redwood, measured 2006'),
    'sherman': ('GENERAL SHERMAN', 'General Sherman, the largest tree by volume', 83.8, 'h', 'tree', 'giant sequoia, NPS'),
    'angel': ('ANGEL FALLS', 'Angel Falls', 979, 'h', 'falls', 'tallest waterfall'),
    'niagara': ('NIAGARA FALLS', 'Niagara\'s Horseshoe Falls', 51, 'h', 'falls', 'Horseshoe Falls drop'),
    'hoover': ('HOOVER DAM', 'the Hoover Dam', 221, 'h', 'dam', 'US Bureau of Reclamation'),
    'giraffe': ('GIRAFFE', 'a tall giraffe', 5.5, 'h', 'giraffe', 'tall adult male'),
    'elephant': ('ELEPHANT', 'an African elephant', 4.0, 'h', 'elephant', 'large bull, shoulder height'),
    'human': ('PERSON', 'an average adult', HUMAN, 'h', 'human', 'average adult'),
    'icon': ('ICON OF THE SEAS', 'Icon of the Seas, the largest cruise ship', 365, 'l', 'ship', 'Royal Caribbean'),
    'ford': ('USS GERALD R. FORD', 'the aircraft carrier USS Gerald R. Ford', 337, 'l', 'ship', 'US Navy'),
    'titanic': ('TITANIC', 'the Titanic', 269.1, 'l', 'ship', 'overall length'),
    'a380': ('AIRBUS A380', 'an Airbus A380', 72.7, 'l', 'plane', 'Airbus'),
    'b747': ('BOEING 747-8', 'a Boeing 747-8', 76.3, 'l', 'plane', 'Boeing'),
    'an225': ('ANTONOV AN-225', 'the Antonov An-225', 84, 'l', 'plane', 'longest cargo plane ever'),
    'whale': ('BLUE WHALE', 'a blue whale', 30, 'l', 'whale', 'largest recorded, about 30 m'),
    'trex': ('T. REX', 'a Tyrannosaurus rex', 12.3, 'l', 'dino', 'Sue specimen, Field Museum'),
    'argentino': ('ARGENTINOSAURUS', 'Argentinosaurus', 35, 'l', 'sauropod', 'estimated 30 to 35 m'),
    'bus': ('SCHOOL BUS', 'a school bus', 13.7, 'l', 'bus', '45 ft, large US school bus'),
    'football': ('FOOTBALL FIELD', 'an American football field', 109.7, 'l', 'field', '120 yards with end zones'),
    'goldengate': ('GOLDEN GATE SPAN', 'the Golden Gate Bridge main span', 1280, 'l', 'bridge', 'main span'),
}
H_IDS = [k for k, v in OBJ.items() if v[3] == 'h']
L_IDS = [k for k, v in OBJ.items() if v[3] == 'l']
KURGU = ['taller2', 'lineup5', 'humans', 'stackfit', 'guess', 'rank3', 'truefalse', 'oddone', 'sideways', 'percent', 'floors',
         'fields', 'reveal', 'scaleman', 'closer']


def log(m): print(m, flush=True)
def M(k): return OBJ[k][2]
def nm(k): return OBJ[k][1]
def NM(k): return OBJ[k][0]
def cap(s): return s[0].upper() + s[1:]
def meters(v): return f'{v:,.0f} meters' if v >= 20 else f'{v:,.1f} meters'.replace('.0 ', ' ')
def mt(v): return f'{v:,.0f} M' if v >= 20 else f'{v:,.1f} M'.replace('.0 ', ' ')
def ft(v): return f'{v * 3.281:,.0f} FT'
def word(k): return 'tall' if OBJ[k][3] == 'h' else 'long'


SPECIAL = {'wtc': 'One World Trade Center', 'icon': 'Icon of the Seas', 'ford': 'USS Gerald R. Ford', 'a380': 'Airbus A380',
           'b747': 'Boeing 747-8', 'an225': 'Antonov An-225', 'trex': 'T. Rex', 'goldengate': 'Golden Gate Bridge',
           'redeemer': 'Christ the Redeemer', 'bigben': 'Big Ben', 'pisa': 'Tower of Pisa', 'liberty': 'Statue of Liberty',
           'football': 'Football Field', 'saturnv': 'Saturn V', 'hyperion': 'Hyperion Tree', 'sherman': 'General Sherman Tree'}
def TN(k): return SPECIAL.get(k) or ' '.join(w.capitalize() for w in NM(k).split())
def sn(k): return nm(k).split(',')[0]


# ---------------------------------------------------------------- konu
def done():
    if not LOG.exists(): return set(), []
    with LOG.open(encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    return {r['topic_id'] for r in rows}, rows


def key_for(k, rnd):
    grp = rnd.choice([H_IDS, H_IDS, L_IDS])
    big = [x for x in grp if x not in ('human',)]
    if k in ('taller2', 'percent'):
        a, b = sorted(rnd.sample(big, 2)); r = M(a) / M(b)
        return [k, a, b] if 0.25 < r < 4 and r != 1 else None
    if k in ('lineup5', 'rank3', 'oddone', 'closer'):
        n = {'lineup5': 5, 'rank3': 3, 'oddone': 4, 'closer': 4}[k]; s = sorted(rnd.sample(big, n), key=M)
        if k == 'oddone' and sum(M(x) > 300 for x in s) != 1: return None
        if len({round(M(x)) for x in s}) < n: return None
        return [k] + s
    if k in ('humans', 'guess', 'floors', 'scaleman'):
        x = rnd.choice([i for i in (H_IDS if k == 'floors' else big) if i not in ('human', 'football')])
        if k == 'scaleman' and M(x) > 150: return None
        return [k, x]
    if k == 'stackfit':
        a, b = rnd.sample(big, 2)
        if OBJ[a][3] != OBJ[b][3] or not (2 <= M(b) / M(a) <= 60): return None
        return [k, a, b]
    if k == 'truefalse':
        a, b = rnd.sample(big, 2); f = rnd.choice([2, 3, 5])
        return [k, a, b, f] if OBJ[a][3] == OBJ[b][3] and 1.2 < M(a) / M(b) < 8 else None
    if k == 'sideways':
        a, b = rnd.choice(L_IDS), rnd.choice(H_IDS)
        return [k, a, b] if 0.4 < M(a) / M(b) < 2.5 else None
    if k == 'fields':
        x = rnd.choice([i for i in big if M(i) > 100 and i != 'football']); return [k, x]
    if k == 'reveal':
        s = sorted(rnd.sample(big, 3), key=M)
        return [k] + s if M(s[2]) / M(s[0]) > 3 else None


def pick(rnd, kurgu=None):
    seen, rows = done(); last = [r['topic_id'].split(':')[1] for r in rows[-4:] if r['topic_id'].startswith('bg:')]
    for _ in range(4000):
        k = kurgu or rnd.choice([x for x in KURGU if x not in last] or KURGU)
        key = key_for(k, rnd)
        if key is None: continue
        tid = 'bg:' + ':'.join(str(x) for x in key)
        if tid not in seen: return key, tid
    raise RuntimeError('yeni konu kalmadı')


def C(rnd, *o): return rnd.choice(o)


def build(key, rnd):
    k = key[0]; B = []; used = []
    if k == 'taller2':
        a, b = key[1], key[2]; w = a if M(a) > M(b) else b; wd = 'taller' if OBJ[a][3] == 'h' else 'longer'
        B = [(C(rnd, f'Which is {wd}: {nm(a)} or {nm(b)}?', f'{cap(nm(a))} versus {nm(b)}. Which one is {wd}?'), dict(t='line', ids=[a, b], hide=True)),
             ('Make your guess.', dict(t='line', ids=[a, b], hide=True, timer=True)),
             (f'{cap(sn(a))}: {meters(M(a))}. {cap(sn(b))}: {meters(M(b))}.', dict(t='line', ids=[a, b], anim=True)),
             (f'{cap(sn(w))} wins by {meters(abs(M(a) - M(b)))}.', dict(t='line', ids=[a, b], mark=w)),
             (C(rnd, 'Did you get it? Comment below.', 'What should I compare next? Comment below.'), dict(t='line', ids=[a, b], mark=w, cta='DID YOU GET IT?'))]
        title = f'{TN(a)} vs {TN(b)}: Which Is {wd.title()}?'; used = [a, b]
    elif k in ('lineup5', 'reveal'):
        ids = key[1:]
        B = [(C(rnd, f'{len(ids)} giants, from smallest to biggest. First, {sn(ids[0])}: {meters(M(ids[0]))}.', f'Let us line them up, starting with {sn(ids[0])} at {meters(M(ids[0]))}.') if k == 'lineup5' else f'This is {nm(ids[0])}. It is {meters(M(ids[0]))} {word(ids[0])}. Now zoom out.', dict(t='line', ids=ids[:1], anim=True))]
        for i in range(1, len(ids)):
            B.append((f'{cap(sn(ids[i]))}: {meters(M(ids[i]))}.' + (f' That is {M(ids[i]) / M(ids[i - 1]):.1f} times bigger.' if k == 'reveal' else ''), dict(t='line', ids=ids[:i + 1], anim=True)))
        B.append((C(rnd, 'Which one surprised you? Comment below.', 'What should be next in line? Comment below.'), dict(t='line', ids=ids, cta='WHAT NEXT?')))
        title = (f'{TN(ids[0])} to {TN(ids[-1])}: {len(ids)} Giants Compared' if k == 'lineup5' else f'Start With {TN(ids[0])}, Then Zoom Out')
        used = list(ids)
    elif k == 'humans':
        x = key[1]; n = M(x) / HUMAN
        B = [(f'How many people would you need to stack to match {nm(x)}?', dict(t='line', ids=['human', x], hide=True)),
             (f'{cap(nm(x))} is {meters(M(x))} {word(x)}. An average adult is about 1.7 meters.', dict(t='line', ids=['human', x], anim=True)),
             (f'So about {n:,.0f} people{" stacked on top of each other" if OBJ[x][3] == "h" else " lying head to toe"}.', dict(t='count', n=n, lab='PEOPLE', ids=[x])),
             ('Did you guess higher or lower? Comment below.', dict(t='count', n=n, lab='PEOPLE', ids=[x], cta='HIGHER OR LOWER?'))]
        title = f'How Many People Tall Is {TN(x)}?' if OBJ[x][3] == 'h' else f'How Many People Long Is {TN(x)}?'; used = [x]
    elif k == 'stackfit':
        a, b = key[1], key[2]; n = M(b) / M(a)
        B = [(f'How many copies of {sn(a)}, end to end, would match {nm(b)}?', dict(t='line', ids=[a, b], hide=True)),
             (f'{cap(sn(a))} is {meters(M(a))}. {cap(sn(b))} is {meters(M(b))}.', dict(t='line', ids=[a, b], anim=True)),
             (f'You would need {n:,.1f}.'.replace('.0.', '.'), dict(t='count', n=n, lab=f'X {NM(a)}', ids=[b], dec=True)),
             ('Close to your guess? Comment below.', dict(t='count', n=n, lab=f'{NM(a)}S', ids=[b], dec=True, cta='YOUR GUESS?'))]
        title = f'{TN(b)} = How Many {TN(a)}?'; used = [a, b]
    elif k == 'guess':
        x = key[1]; v = M(x); o = [v, v * rnd.choice([0.5, 0.6]), v * rnd.choice([1.6, 2])]; rnd.shuffle(o); r = o.index(v)
        ops = [mt(z) for z in o]
        B = [(f'How {word(x)} is {nm(x)}?', dict(t='opts', ids=[x], o=ops)),
             (f'A: {meters(o[0])}. B: {meters(o[1])}. C: {meters(o[2])}.', dict(t='opts', ids=[x], o=ops, timer=True)),
             (f'It is {"ABC"[r]}: {meters(v)}, or {ft(v).lower().replace(" ft", " feet")}.', dict(t='opts', ids=[x], o=ops, r=r)),
             (f'That is about {v / HUMAN:,.0f} people {"tall" if OBJ[x][3] == "h" else "long"}.', dict(t='line', ids=['human', x])),
             ('Did you get it? Comment below.', dict(t='opts', ids=[x], o=ops, r=r, cta='DID YOU GET IT?'))]
        title = f'How {word(x).title()} Is {TN(x)}? Guess First'; used = [x]
    elif k in ('rank3', 'closer'):
        ids = list(key[1:]); sh = ids[:]; rnd.shuffle(sh)
        B = [(f'Rank these from smallest to biggest: ' + ', '.join(nm(x) for x in sh) + '.', dict(t='names', ids=sh)),
             ('Lock in your order.', dict(t='names', ids=sh, timer=True))]
        for i in range(len(ids)):
            B.append((f'Number {i + 1}: {sn(ids[i])}, {meters(M(ids[i]))}.', dict(t='line', ids=ids[:i + 1], anim=True)))
        B.append(('How many did you get right? Comment below.', dict(t='line', ids=ids, cta='YOUR SCORE?')))
        title = f'Rank These {len(ids)} by Size: ' + ', '.join(TN(x) for x in sh[:3]); used = ids
    elif k == 'truefalse':
        a, b, f = key[1], key[2], key[3]; r = M(a) / M(b); tr = r >= f
        claim = f'{cap(nm(a))} is at least {f} times as {word(a)} as {nm(b)}.'
        B = [(f'True or false? {claim}', dict(t='tf', q=claim)), ('Think about it.', dict(t='tf', q=claim, timer=True)),
             (f'{"True" if tr else "False"}. {meters(M(a))} versus {meters(M(b))}: {r:.1f} times.', dict(t='line', ids=[b, a], anim=True)),
             ('Did you get it? Comment true or false.', dict(t='tf', q=claim, r=0 if tr else 1, cta='TRUE OR FALSE?'))]
        title = f'True or False: {TN(a)} Is {f}x {TN(b)}'; used = [a, b]
    elif k == 'oddone':
        ids = list(key[1:]); sh = ids[:]; rnd.shuffle(sh); x = [i for i in ids if M(i) > 300][0]; r = sh.index(x)
        ops = [NM(i) for i in sh]
        B = [(f'Only one of these is over 300 meters. Which one?', dict(t='opts', ids=[], o=ops)), ('A, B, C or D?', dict(t='opts', ids=[], o=ops, timer=True)),
             (f'It is {"ABCD"[r]}: {sn(x)}, at {meters(M(x))}.', dict(t='opts', ids=[], o=ops, r=r)),
             (' '.join(f'{cap(sn(i))}: {meters(M(i))}.' for i in sh if i != x), dict(t='line', ids=ids, mark=x)),
             ('Did you spot it? Comment below.', dict(t='line', ids=ids, mark=x, cta='DID YOU SPOT IT?'))]
        title = 'Only One of These Is Over 300 Meters. Which?'; used = ids
    elif k == 'sideways':
        a, b = key[1], key[2]; w = a if M(a) > M(b) else b
        B = [(f'If you stood {sn(a)} on its end, would it be taller than {sn(b)}?', dict(t='line', ids=[a, b], hide=True, stand=True)),
             ('Guess first.', dict(t='line', ids=[a, b], hide=True, stand=True, timer=True)),
             (f'{cap(sn(a))} is {meters(M(a))} long. {cap(sn(b))} is {meters(M(b))} tall.', dict(t='line', ids=[a, b], stand=True, anim=True)),
             (f'So {"yes" if w == a else "no"}: {"it would tower over" if w == a else "it would come up short of"} {nm(b)} by {meters(abs(M(a) - M(b)))}.', dict(t='line', ids=[a, b], stand=True, mark=w)),
             ('Did you expect that? Comment below.', dict(t='line', ids=[a, b], stand=True, mark=w, cta='DID YOU EXPECT IT?'))]
        title = f'{TN(a)} Standing Up vs {TN(b)}'; used = [a, b]
    elif k == 'percent':
        a, b = sorted(key[1:3], key=M); p = M(a) / M(b) * 100
        B = [(f'{cap(nm(a))} is what percent of {nm(b)}?', dict(t='line', ids=[a, b], hide=True)),
             (f'{meters(M(a))} versus {meters(M(b))}.', dict(t='line', ids=[a, b], anim=True)),
             (f'{p:.0f} percent.', dict(t='count', n=p, lab='PERCENT', ids=[a, b])),
             ('Close? Comment your guess.', dict(t='count', n=p, lab='PERCENT', ids=[a, b], cta='YOUR GUESS?'))]
        title = f'{TN(a)} Is What % of {TN(b)}?'; used = [a, b]
    elif k == 'floors':
        x = key[1]; n = M(x) / 3.5
        B = [(f'If {nm(x)} were an apartment building, how many floors would it have?', dict(t='line', ids=['human', x], hide=True)),
             (f'A typical floor is about 3.5 meters. {cap(nm(x))} is {meters(M(x))} tall.', dict(t='line', ids=['human', x], anim=True)),
             (f'That is about {n:,.0f} floors.', dict(t='count', n=n, lab='FLOORS', ids=[x])),
             ('Which floor would you live on? Comment below.', dict(t='count', n=n, lab='FLOORS', ids=[x], cta='WHICH FLOOR?'))]
        title = f'{TN(x)} in Apartment Floors'; used = [x]
    elif k == 'fields':
        x = key[1]; n = M(x) / 109.7
        B = [(f'How many American football fields is {nm(x)}?', dict(t='line', ids=['football', x], hide=True)),
             (f'One field, end zones included, is 109.7 meters. {cap(nm(x))} is {meters(M(x))} {word(x)}.', dict(t='line', ids=['football', x], anim=True)),
             (f'That is {n:,.1f} football fields.', dict(t='count', n=n, lab='FOOTBALL FIELDS', ids=[x], dec=True)),
             ('Did you guess right? Comment below.', dict(t='count', n=n, lab='FOOTBALL FIELDS', ids=[x], dec=True, cta='YOUR GUESS?'))]
        title = f'{TN(x)} in Football Fields'; used = [x, 'football']
    else:                                                             # scaleman
        x = key[1]
        B = [(f'Here is {nm(x)} next to a person, to scale.', dict(t='line', ids=['human', x], anim=True)),
             (f'{cap(nm(x))}: {meters(M(x))}, or {ft(M(x)).lower().replace(" ft", " feet")}.', dict(t='line', ids=['human', x])),
             (f'That is {M(x) / HUMAN:,.1f} times a person.', dict(t='count', n=M(x) / HUMAN, lab='TIMES A PERSON', ids=[x], dec=True)),
             ('What should I put next to a person next? Comment below.', dict(t='line', ids=['human', x], cta='WHAT NEXT?'))]
        title = f'{TN(x)} Next to a Person, to Scale'; used = [x]
    if k in ('humans', 'floors', 'fields', 'stackfit', 'scaleman', 'percent') and len(B) >= 3:      # kıyas cümlesi
        base_ = key[1] if k != 'percent' else key[2]
        pool = [o for o in OBJ if o not in key and o not in ('human', 'football') and OBJ[o][3] == OBJ[base_][3] and 1.5 < max(M(o), M(base_)) / min(M(o), M(base_)) < 12]
        if pool:
            o = rnd.choice(pool); unit = {'humans': (HUMAN, 'people'), 'floors': (3.5, 'floors'), 'fields': (109.7, 'football fields'),
                                          'stackfit': (M(key[1]), f'copies of {sn(key[1])}'), 'scaleman': (HUMAN, 'times a person'), 'percent': (M(base_) / 100, f'percent of {sn(base_)}')}[k]
            n2 = M(o) / unit[0]
            B.insert(len(B) - 1, (f'For comparison, {sn(o)} is {meters(M(o))}: ' + (f'{n2:,.0f}' if k in ('humans', 'floors', 'percent') else f'{n2:,.1f}') + f' {unit[1]}.', dict(t='line', ids=sorted([base_, o], key=M), mark=o)))
            used.append(o)
    src = '\n'.join(f'{TN(i)}: {meters(OBJ[i][2])} ({OBJ[i][5]})' for i in dict.fromkeys(used + ['human']) if i in OBJ)
    title = title[:95]
    desc = (title + '\n\nMeasurements:\n' + src + '\nAverage adult shown at 1.7 m. Drawings are simplified, but every size is to scale.'
            + '\n\n#sizecomparison #biggerthanyouthink #scale #shorts')
    return dict(key=key, kurgu=k, beats=[b for b, _ in B], scenes=[s for _, s in B], title=title, desc=desc,
                tags=['size comparison', 'how big', 'scale comparison', 'bigger than you think', 'shorts'])


# ---------------------------------------------------------------- çizim
_FC = {}


def font(p, s):
    if (p, s) not in _FC:
        f = ImageFont.truetype(p, s)
        if p == MONO:
            try: f.set_variation_by_axes([700])
            except Exception: pass
        _FC[(p, s)] = f
    return _FC[(p, s)]


def ease(x): x = max(0.0, min(1.0, x)); return 1 - (1 - x) ** 3


def background(w, h):
    img = Image.new('RGB', (w, h), BG); d = ImageDraw.Draw(img)
    for x in range(0, w, 40): d.line([(x, 0), (x, h)], fill=GRID if x % 200 else (40, 82, 146), width=1)
    for y in range(0, h, 40): d.line([(0, y), (w, y)], fill=GRID if y % 200 else (40, 82, 146), width=1)
    return img


def shape(d, kind, x, gy, w, h, col=LINE, lw=4):
    """Taban ortası x, zemin gy; w genişlik, h yükseklik (piksel). Basit teknik çizim silüetleri."""
    L = x - w / 2; R = x + w / 2; T = gy - h
    if kind in ('spire', 'tower', 'needle'):
        bw = w * (0.8 if kind != 'needle' else 0.25)
        d.polygon([(x - bw / 2, gy), (x - bw * 0.35, T + h * 0.18), (x + bw * 0.35, T + h * 0.18), (x + bw / 2, gy)], outline=col, width=lw)
        d.line([(x, T + h * 0.18), (x, T)], fill=col, width=lw)
        if kind == 'needle': d.ellipse([x - w * 0.45, T + h * 0.12, x + w * 0.45, T + h * 0.22], outline=col, width=lw)
        for yy in range(int(gy - 12), int(T + h * 0.2), -max(8, int(h / 30))):
            d.line([(x - bw * 0.3, yy), (x + bw * 0.3, yy)], fill=DIM, width=1)
    elif kind == 'eiffel':
        d.polygon([(L, gy), (x - w * 0.08, T + h * 0.15), (x + w * 0.08, T + h * 0.15), (R, gy)], outline=col, width=lw)
        d.line([(x, T + h * 0.15), (x, T)], fill=col, width=lw); d.line([(L + w * 0.18, gy - h * 0.3), (R - w * 0.18, gy - h * 0.3)], fill=col, width=lw)
        d.arc([L + w * 0.2, gy - h * 0.2, R - w * 0.2, gy + h * 0.1], 180, 360, fill=col, width=lw)
    elif kind == 'pyramid':
        d.polygon([(L, gy), (x, T), (R, gy)], outline=col, width=lw)
    elif kind == 'rocket':
        d.rectangle([x - w * 0.18, T + h * 0.1, x + w * 0.18, gy], outline=col, width=lw); d.polygon([(x - w * 0.18, T + h * 0.1), (x, T), (x + w * 0.18, T + h * 0.1)], outline=col, width=lw)
        d.polygon([(x - w * 0.18, gy - h * 0.15), (x - w * 0.4, gy), (x - w * 0.18, gy)], outline=col, width=lw); d.polygon([(x + w * 0.18, gy - h * 0.15), (x + w * 0.4, gy), (x + w * 0.18, gy)], outline=col, width=lw)
    elif kind == 'statue':
        d.rectangle([x - w * 0.3, gy - h * 0.45, x + w * 0.3, gy], outline=col, width=lw)
        d.polygon([(x - w * 0.18, gy - h * 0.45), (x - w * 0.1, T + h * 0.12), (x + w * 0.1, T + h * 0.12), (x + w * 0.18, gy - h * 0.45)], outline=col, width=lw)
        d.ellipse([x - w * 0.08, T + h * 0.04, x + w * 0.08, T + h * 0.14], outline=col, width=lw); d.line([(x + w * 0.1, T + h * 0.2), (x + w * 0.2, T)], fill=col, width=lw)
    elif kind == 'tree':
        d.rectangle([x - w * 0.06, gy - h * 0.45, x + w * 0.06, gy], outline=col, width=lw); d.ellipse([L + w * 0.1, T, R - w * 0.1, gy - h * 0.35], outline=col, width=lw)
    elif kind == 'falls':
        d.polygon([(L, gy), (L, T), (x - w * 0.05, T), (x - w * 0.05, gy)], outline=col, width=lw)
        for i in range(5): d.line([(x + i * w * 0.08, T), (x + i * w * 0.08, gy)], fill=CYAN, width=2)
    elif kind == 'dam':
        d.polygon([(L, gy), (x - w * 0.1, T), (x + w * 0.1, T), (R, gy)], outline=col, width=lw); d.line([(L - w * 0.3, T + h * 0.1), (x - w * 0.1, T + h * 0.1)], fill=CYAN, width=3)
    elif kind == 'giraffe':
        d.rectangle([x - w * 0.3, gy - h * 0.5, x + w * 0.2, gy - h * 0.3], outline=col, width=lw)
        for xx in (x - w * 0.25, x + w * 0.15): d.line([(xx, gy - h * 0.3), (xx, gy)], fill=col, width=lw)
        d.line([(x + w * 0.15, gy - h * 0.5), (x + w * 0.35, T + h * 0.1)], fill=col, width=lw); d.ellipse([x + w * 0.28, T, x + w * 0.5, T + h * 0.1], outline=col, width=lw)
    elif kind == 'elephant':
        d.ellipse([L, T, R - w * 0.15, gy - h * 0.3], outline=col, width=lw)
        for xx in (L + w * 0.15, R - w * 0.35): d.rectangle([xx, gy - h * 0.4, xx + w * 0.12, gy], outline=col, width=lw)
        d.arc([R - w * 0.3, T + h * 0.1, R, gy], 270, 90, fill=col, width=lw)
    elif kind == 'human':
        hd = h * 0.13; d.ellipse([x - hd / 2, T, x + hd / 2, T + hd], outline=col, width=lw)
        d.line([(x, T + hd), (x, gy - h * 0.45)], fill=col, width=lw); d.line([(x, gy - h * 0.45), (x - w * 0.25, gy)], fill=col, width=lw)
        d.line([(x, gy - h * 0.45), (x + w * 0.25, gy)], fill=col, width=lw); d.line([(x - w * 0.3, T + h * 0.3), (x + w * 0.3, T + h * 0.3)], fill=col, width=lw)
    elif kind == 'ship':
        d.polygon([(L, gy - h * 0.6), (L + w * 0.06, gy), (R - w * 0.04, gy), (R, gy - h * 0.6)], outline=col, width=lw)
        d.rectangle([L + w * 0.25, T, R - w * 0.15, gy - h * 0.6], outline=col, width=lw)
    elif kind == 'plane':
        d.rounded_rectangle([L, gy - h * 0.55, R, gy - h * 0.2], radius=max(2, h * 0.15), outline=col, width=lw)
        d.polygon([(L + w * 0.02, gy - h * 0.55), (L + w * 0.08, T), (L + w * 0.16, gy - h * 0.55)], outline=col, width=lw)
        d.line([(x - w * 0.1, gy - h * 0.38), (x + w * 0.12, gy)], fill=col, width=lw)
    elif kind == 'whale':
        d.ellipse([L + w * 0.1, T + h * 0.2, R, gy], outline=col, width=lw); d.polygon([(L + w * 0.12, T + h * 0.6), (L, T), (L, gy)], outline=col, width=lw)
    elif kind in ('dino', 'sauropod'):
        if kind == 'dino':
            d.ellipse([x - w * 0.25, T + h * 0.25, x + w * 0.15, gy - h * 0.3], outline=col, width=lw); d.line([(x - w * 0.25, T + h * 0.5), (L, T + h * 0.45)], fill=col, width=lw)
            d.rectangle([x + w * 0.1, T, R, T + h * 0.3], outline=col, width=lw)
        else:
            d.ellipse([x - w * 0.2, T + h * 0.3, x + w * 0.15, gy - h * 0.3], outline=col, width=lw); d.line([(x + w * 0.12, T + h * 0.45), (R, T)], fill=col, width=lw); d.line([(x - w * 0.2, T + h * 0.55), (L, gy - h * 0.3)], fill=col, width=lw)
        for xx in (x - w * 0.12, x + w * 0.05): d.line([(xx, gy - h * 0.35), (xx, gy)], fill=col, width=lw)
    elif kind == 'bus':
        d.rounded_rectangle([L, T, R, gy - h * 0.12], radius=max(2, h * 0.1), outline=col, width=lw)
        for xx in (L + w * 0.18, R - w * 0.18): d.ellipse([xx - h * 0.14, gy - h * 0.26, xx + h * 0.14, gy], outline=col, width=lw)
    elif kind == 'field':
        d.rectangle([L, gy - max(4, h), R, gy], outline=col, width=lw)
        for i in range(1, 12): d.line([(L + w * i / 12, gy - max(4, h)), (L + w * i / 12, gy)], fill=DIM, width=1)
    elif kind == 'bridge':
        d.line([(L, gy - h * 0.2), (R, gy - h * 0.2)], fill=col, width=lw)
        for xx in (L, R): d.line([(xx, gy - h * 0.2), (xx, T)], fill=col, width=lw)
        d.arc([L, T, R, gy + h * 0.3], 0, 180, fill=col, width=lw)
    else:
        d.rectangle([L, T, R, gy], outline=col, width=lw)


ASPECT = {'spire': 0.12, 'tower': 0.14, 'needle': 0.2, 'eiffel': 0.38, 'pyramid': 1.6, 'rocket': 0.12, 'statue': 0.3, 'tree': 0.25,
          'falls': 0.35, 'dam': 1.2, 'giraffe': 0.6, 'elephant': 1.3, 'human': 0.35, 'ship': 0.17, 'plane': 0.26, 'whale': 0.2,
          'dino': 0.33, 'sauropod': 0.35, 'bus': 0.23, 'field': 0.02, 'bridge': 0.18}


def lineup(img, d, ids, box, k=1.0, hide=False, mark=None, stand=False, labels=True):
    """Nesneleri aynı ölçekte yan yana çizer. box=(x0,y0,x1,gy). Uzunluk nesneleri yatay; stand=True ise uzunluğu dik."""
    x0, y0, x1, gy = box
    if not stand and all(OBJ[i][3] == 'l' for i in ids) and (gy - y0) > (x1 - x0) * 0.6:   # dikey ekranda: satır satır, aynı ölçek
        n = len(ids); rh = (gy - y0) / n; sc_ = (x1 - x0 - 40) / max(M(i) for i in ids)
        for j, i in enumerate(ids):
            o = OBJ[i]; w = max(4, M(i) * sc_ * k); hgt = min(rh * 0.55, max(6, M(i) * ASPECT[o[4]] * sc_)); yb = y0 + (j + 1) * rh - 60
            col = YEL if i == mark else LINE
            d.line([(x0 - 20, yb), (x1 + 20, yb)], fill=GRID, width=2)
            shape(d, o[4], x0 + w / 2, yb, w, hgt, col)
            if labels:
                d.text((x0, yb + 12), o[0], font=font(BOLD, 34), fill=col, anchor='lt')
                d.text((x1, yb + 12), '?' if hide else mt(M(i) * k), font=font(MONO, 36) if not hide else font(BOLD, 50), fill=YEL if hide else CYAN, anchor='rt')
                if not hide: d.line([(x0, yb - hgt - 14), (x0 + w, yb - hgt - 14)], fill=CYAN, width=2)
        return
    def dims(i):
        o = OBJ[i]; a = ASPECT[o[4]]
        if o[3] == 'h' or (stand and o[3] == 'l'): return o[2] * min(a, 0.5) * (2 if stand and o[3] == 'l' else 1), o[2]
        return o[2], o[2] * a
    ws = [dims(i)[0] for i in ids]; hs = [dims(i)[1] for i in ids]
    scale = min((gy - y0) / max(hs), (x1 - x0) * 0.85 / sum(ws) if sum(ws) else 1)
    gap = ((x1 - x0) - sum(w * scale for w in ws)) / (len(ids) + 1); x = x0 + gap
    d.line([(x0 - 40, gy), (x1 + 40, gy)], fill=LINE, width=3)
    for i, w, h in zip(ids, ws, hs):
        pw, ph = max(3, w * scale), max(3, h * scale * k); cx = x + pw / 2
        o = OBJ[i]; col = YEL if i == mark else LINE
        if stand and o[3] == 'l':
            shape(d, 'tower', cx, gy, pw, ph, col)
        else:
            shape(d, o[4], cx, gy, pw, ph, col)
        if labels:
            d.text((cx, gy + 30), o[0], font=font(BOLD, 34 if len(ids) <= 3 else 26), fill=col, anchor='mt')
            if not hide:
                d.line([(cx + pw / 2 + 8, gy), (cx + pw / 2 + 8, gy - ph)], fill=CYAN, width=2)
                d.text((cx, gy - ph - 14), mt(o[2] * k), font=font(MONO, 34 if len(ids) <= 3 else 24), fill=CYAN, anchor='mb')
            else:
                d.text((cx, gy - ph - 14), '?', font=font(BOLD, 70), fill=YEL, anchor='mb')
        x += pw + gap


def wrap(d, text, f, maxw):
    out, cur = [], ''
    for w_ in text.split():
        t = (cur + ' ' + w_).strip()
        if d.textlength(t, font=f) > maxw and cur: out.append(cur); cur = w_
        else: cur = t
    return out + [cur] if cur else out


def frame(base, v, bi, t, dur, W=1080, H=1920):
    img = base.copy(); d = ImageDraw.Draw(img); sc = v['scenes'][bi]; T = sc['t']
    prev = v['scenes'][bi - 1] if bi else {}
    a = 1.0 if (prev.get('t') == T and prev.get('ids') == sc.get('ids') and not prev.get('hide')) else ease(t / 1.1)
    d.text((W // 2, 120), 'BIGGER THAN YOU THINK', font=font(BOLD, 74), fill=LINE, anchor='mm')
    d.line([(W // 2 - 260, 170), (W // 2 + 260, 170)], fill=YEL, width=5)
    if T == 'line':
        lineup(img, d, sc['ids'], (90, 330, W - 90, 1350), k=a if sc.get('anim') else 1.0, hide=sc.get('hide'), mark=sc.get('mark'), stand=sc.get('stand'))
    elif T == 'count':
        if sc.get('ids'): lineup(img, d, sc['ids'], (200, 300, W - 200, 820), labels=False)
        n = sc['n'] * a; txt = f'{n:,.1f}' if sc.get('dec') else f'{n:,.0f}'
        d.text((W // 2, 1080), txt, font=font(BOLD, 260 if len(txt) < 6 else 200), fill=YEL, anchor='mm')
        d.text((W // 2, 1250), sc['lab'], font=font(BOLD, 64), fill=LINE, anchor='mm')
    elif T in ('opts', 'names'):
        if sc.get('ids'): lineup(img, d, sc['ids'], (300, 280, W - 300, 760), hide=True)
        ops = sc.get('o') or [NM(i) for i in sc['ids']]
        for i, o in enumerate(ops):
            y = 880 + i * 150 if len(ops) <= 3 else 820 + i * 135; on = sc.get('r') == i
            d.rounded_rectangle([110, y, W - 110, y + 118], radius=14, fill=YEL if on else BG2, outline=LINE, width=4)
            d.text((W // 2, y + 59), (f'{"ABCD"[i]}   ' if T == 'opts' else '') + o, font=font(BOLD, 60 if len(o) < 20 else 46), fill=BG if on else LINE, anchor='mm')
    elif T == 'tf':
        for j, l in enumerate(wrap(d, sc['q'], font(BOLD, 72), 880)[:5]):
            d.text((W // 2, 460 + j * 84), l, font=font(BOLD, 72), fill=LINE, anchor='mm')
        for i, o in enumerate(['TRUE', 'FALSE']):
            x = 110 + i * 440; on = sc.get('r') == i
            d.rounded_rectangle([x, 960, x + 420, 1110], radius=14, fill=YEL if on else BG2, outline=LINE, width=4)
            d.text((x + 210, 1035), o, font=font(BOLD, 90), fill=BG if on else LINE, anchor='mm')
    if sc.get('timer'): d.text((W // 2, 1460), f'{max(0, 3 - int(t * 1.2))}', font=font(MONO, 110), fill=RED, anchor='mm')
    if sc.get('cta'):
        d.rounded_rectangle([150, 1580, W - 150, 1720], radius=14, fill=YEL)
        d.text((W // 2, 1650), sc['cta'], font=font(BOLD, 84), fill=BG, anchor='mm')
    else:
        f = font(MED, 50); ls = wrap(d, v['beats'][bi], f, 940)
        groups = [ls[i:i + 3] for i in range(0, len(ls), 3)] or [[]]
        for j, l in enumerate(groups[min(len(groups) - 1, int(t / max(dur, 0.1) * len(groups)))]):
            d.text((W // 2, 1580 + j * 62), l, font=f, fill=LINE, anchor='mm')
    return img


# ---------------------------------------------------------------- ses + video
def ff(): return os.environ.get('FFMPEG') or 'ffmpeg'


def tts(text, path):
    import edge_tts

    async def go():
        await edge_tts.Communicate(text, VOICE, rate='+6%').save(str(path))
    for i in range(3):
        try:
            asyncio.run(go())
            if path.exists() and path.stat().st_size > 1000: return
        except Exception as e:
            log(f'  tts deneme {i + 1}: {e}')
    raise RuntimeError('edge-tts çalışmadı')


def voice(beats, tmp, pad=0.3, holds=()):
    durs, ws = [], []
    for i, b in enumerate(beats):
        a = tmp / f'a{i}.mp3'; tts(b, a); w = tmp / f'w{i}.wav'
        af = f'silenceremove=start_periods=1:start_threshold=-45dB,areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse,apad=pad_dur={pad}'
        if i in holds: af += ',apad=whole_dur=3.0'
        subprocess.run([ff(), '-y', '-loglevel', 'error', '-i', str(a), '-af', af, '-ar', '24000', '-ac', '1', '-c:a', 'pcm_s16le', str(w)], check=True)
        r = subprocess.run([ff(), '-i', str(w), '-f', 'null', '-'], capture_output=True, text=True)
        tm = [l for l in r.stderr.split('time=')[1:]][-1].split()[0]; hh, mm, ss = tm.split(':'); durs.append(int(hh) * 3600 + int(mm) * 60 + float(ss)); ws.append(w)
    (tmp / 'a.txt').write_text(''.join(f"file '{w}'\n" for w in ws))
    subprocess.run([ff(), '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', str(tmp / 'a.txt'), '-ar', '44100', '-ac', '2', str(tmp / 'voice.wav')], check=True)
    return durs


def encode(fn, durs, wav, mp4, w, h):
    p = subprocess.Popen([ff(), '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{w}x{h}', '-r', str(FPS), '-i', '-', '-i', str(wav),
                          '-c:v', 'libx264', '-preset', 'medium', '-crf', '20', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '160k', '-shortest',
                          '-movflags', '+faststart', str(mp4)], stdin=subprocess.PIPE)
    for i, dd in enumerate(durs):
        for k in range(int(dd * FPS)):
            p.stdin.write(fn(i, k / FPS, dd).tobytes())
    p.stdin.close(); p.wait()
    if p.returncode: raise RuntimeError('ffmpeg hata')


def render(v, mp4):
    tmp = mp4.with_suffix(''); tmp.mkdir(parents=True, exist_ok=True)
    durs = voice(v['beats'], tmp, holds=[i for i, s in enumerate(v['scenes']) if s.get('timer')])
    base = background(1080, 1920)
    encode(lambda i, t, dd: frame(base, v, i, t, dd), durs, tmp / 'voice.wav', mp4, 1080, 1920)
    return mp4


# ---------------------------------------------------------------- uzun video (16:9)
def pick_long(rnd):
    seen, _ = done()
    for _ in range(500):
        grp = rnd.choice(['h', 'h', 'l', 'mix']); pool = [k for k in OBJ if k != 'human' and (grp == 'mix' or OBJ[k][3] == grp)]
        ids = sorted(rnd.sample(pool, min(len(pool), rnd.randint(10, 14))), key=M)
        tid = 'bgl:' + grp + ':' + '-'.join(ids)
        if tid not in seen: return ids, tid
    raise RuntimeError('yeni uzun konu kalmadı')


def build_long(ids, rnd):
    B = [(C(rnd, f'{len(ids)} of the biggest things on Earth, lined up to scale, from smallest to biggest.', f'From {nm(ids[0])} to {nm(ids[-1])}: {len(ids)} giants, one scale.'), dict(n=1))]
    for i in range(1, len(ids)):
        x, p = ids[i], ids[i - 1]
        s = f'Next: {nm(x)}. {meters(M(x))} {word(x)}, about {M(x) / HUMAN:,.0f} people.'
        s += ' ' + C(rnd, f'That is {M(x) / M(p):.1f} times {nm(p)}.', f'{meters(M(x) - M(p))} more than {nm(p)}.')
        s += f' Source: {OBJ[x][5]}.' if rnd.random() < 0.4 else ''
        B.append((s, dict(n=i + 1)))
    B.append((f'From {meters(M(ids[0]))} to {meters(M(ids[-1]))}: {nm(ids[-1])} is {M(ids[-1]) / M(ids[0]):,.0f} times bigger. Which size surprised you? Tell me in the comments.', dict(n=len(ids), cta=True)))
    title = C(rnd, f'{len(ids)} Giants Compared to Scale: {TN(ids[0])} to {TN(ids[-1])}', f'How Big Are They Really? {len(ids)} Things to Scale')
    desc = (title + '\n\nMeasurements:\n' + '\n'.join(f'{TN(i)}: {meters(M(i))} ({OBJ[i][5]})' for i in ids)
            + '\nDrawings are simplified, but every size is to scale.\n\n#sizecomparison #biggerthanyouthink #scale')
    return dict(ids=ids, beats=[b for b, _ in B], scenes=[s for _, s in B], title=title[:95], desc=desc,
                tags=['size comparison', 'scale comparison', 'how big', 'bigger than you think'])


def frame_long(base, v, bi, t, dur):
    W, H = 1920, 1080; img = base.copy(); d = ImageDraw.Draw(img); sc = v['scenes'][bi]; n = sc['n']
    d.text((60, 60), 'BIGGER THAN YOU THINK', font=font(BOLD, 56), fill=LINE, anchor='lm')
    ids = v['ids'][max(0, n - 5):n]                                  # son 5 nesne ekranda, aynı ölçekte
    lineup(img, d, ids, (120, 150, W - 120, 860), k=1.0, mark=v['ids'][n - 1])
    f = font(MED, 42); ls = wrap(d, v['beats'][bi], f, 1760)
    groups = [ls[i:i + 2] for i in range(0, len(ls), 2)] or [[]]
    d.rectangle([0, 960, W, H], fill=BG2)
    for j, l in enumerate(groups[min(len(groups) - 1, int(t / max(dur, 0.1) * len(groups)))]):
        d.text((W // 2, 995 + j * 50), l, font=f, fill=LINE, anchor='mm')
    return img


def render_long(v, mp4):
    tmp = mp4.with_suffix(''); tmp.mkdir(parents=True, exist_ok=True)
    durs = voice(v['beats'], tmp, pad=0.6); base = background(1920, 1080)
    cache = {}
    def fn(i, t, dd):
        ck = (i, int(t / max(dd, 0.1) * 6))
        if ck not in cache: cache.clear(); cache[ck] = frame_long(base, v, i, t, dd)
        return cache[ck]
    encode(fn, durs, tmp / 'voice.wav', mp4, 1920, 1080)
    return mp4


# ---------------------------------------------------------------- akış
def yt():
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build as gbuild
    creds = Credentials(None, refresh_token=os.environ['YT_REFRESH_TOKEN'], client_id=os.environ['YT_CLIENT_ID'],
                        client_secret=os.environ['YT_CLIENT_SECRET'], token_uri='https://oauth2.googleapis.com/token')
    return gbuild('youtube', 'v3', credentials=creds, cache_discovery=False)


def record(tid, vid, kind, title, pa):
    LOG.parent.mkdir(parents=True, exist_ok=True); new = not LOG.exists()
    with LOG.open('a', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['topic_id', 'date_utc', 'video_id', 'kind', 'title', 'publish_at'])
        if new: w.writeheader()
        w.writerow(dict(topic_id=tid, date_utc=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M'), video_id=vid, kind=kind, title=title, publish_at=pa))


def publish_at(kind, n):
    slots = {'short': ['14:30', '17:30', '20:30', '23:30'], 'long': ['19:00']}[kind]
    hh, mm = map(int, slots[min(n, len(slots) - 1)].split(':'))
    now = datetime.now(timezone.utc); t = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    if t < now + timedelta(minutes=30): t = now + timedelta(minutes=40)
    return t.strftime('%Y-%m-%dT%H:%M:%SZ')


def main():
    a = sys.argv[1:]; kurgu = a[a.index('--kurgu') + 1] if '--kurgu' in a else None
    kind = 'long' if '--long' in a else 'short'; n_today = 0
    if '--auto' in a:
        _, rows = done(); today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        tr = [r for r in rows if r['date_utc'].startswith(today)]
        ns, nl = sum(r['kind'] == 'short' for r in tr), sum(r['kind'] == 'long' for r in tr)
        if ns < int(os.environ.get('SHORTS_PER_DAY') or 4): kind, n_today = 'short', ns
        elif nl < int(os.environ.get('LONGS_PER_DAY') or 1) and datetime.now(timezone.utc).strftime('%a').lower()[:3] in (os.environ.get('LONG_DAYS') or 'mon,wed,fri').split(','): kind, n_today = 'long', nl   # haftada 3 uzun
        else: log(f'bugün {ns} short + {nl} uzun yüklendi, iş yok'); return
    rnd = random.Random(); OUT.mkdir(parents=True, exist_ok=True); stamp = datetime.now(timezone.utc).strftime('%Y-%m-%d_%H%M')
    if kind == 'long':
        ids, tid = pick_long(rnd); v = build_long(ids, rnd); log(f'[bigger-long] {tid} → {v["title"]}'); mp4 = render_long(v, OUT / f'long_{stamp}.mp4')
    else:
        key, tid = pick(rnd, kurgu); v = build(key, rnd); log(f'[bigger] {tid} → {v["title"]}'); mp4 = render(v, OUT / f'short_{stamp}.mp4')
    if DRY:
        log(f'  [dry-run] {mp4}\n{v["desc"]}'); return
    api = yt(); ch = api.channels().list(part='id,snippet', mine=True).execute()['items'][0]
    want = os.environ.get('YT_CHANNEL_ID')
    if want and ch['id'] != want: raise RuntimeError(f"yanlış kanal: {ch['snippet']['title']}")
    log(f"kanal: {ch['snippet']['title']}")
    pa = publish_at(kind, n_today)
    from googleapiclient.http import MediaFileUpload
    body = {'snippet': {'title': (v['title'] + (' #shorts' if kind == 'short' else ''))[:100], 'description': v['desc'][:4900], 'tags': v['tags'],
                        'categoryId': '27', 'defaultLanguage': 'en', 'defaultAudioLanguage': 'en'},
            'status': {'privacyStatus': 'private', 'publishAt': pa, 'selfDeclaredMadeForKids': False}}
    vid = api.videos().insert(part='snippet,status', body=body, media_body=MediaFileUpload(str(mp4), resumable=True)).execute()['id']
    record(tid, vid, kind, v['title'], pa); log(f'  ✓ https://youtu.be/{vid} (yayın {pa})')


if __name__ == '__main__':
    main()
