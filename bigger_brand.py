#!/usr/bin/env python3
"""Bigger Than You Think kanal kimliği: banner, profil, açıklama; --hide-old eski Fox videolarını gizler (silmez).
    python bigger_brand.py --make | --apply [--hide-old]"""
import csv, glob, json, sys
from pathlib import Path
from PIL import Image, ImageDraw
import bigger as B

A = Path('branding')
DESCRIPTION = """How big is it, really?

Skyscrapers, ships, planes, dinosaurs, whales, waterfalls and more, drawn side by side at the same scale, with a person for reference. Every size is a real measurement, and the source is in every description.

Guess first, then see the answer. New Shorts every day, plus longer lineups of the biggest things on Earth."""
KEYWORDS = ['size comparison', 'scale comparison', 'how big', 'bigger than you think', 'tallest buildings', 'biggest ships',
            'largest animals', 'skyscrapers', 'blue whale', 'burj khalifa', 'titanic', 'education']


def banner():
    W, H = 2560, 1440; img = B.background(W, H); d = ImageDraw.Draw(img)
    B.lineup(img, d, ['human', 'trex', 'liberty', 'eiffel', 'empire', 'burj'], (560, 520, 2000, 980), labels=False)
    d.text((W // 2, 360), 'BIGGER THAN YOU THINK', font=B.font(B.BOLD, 150), fill=B.LINE, anchor='mm')
    d.line([(W // 2 - 520, 450), (W // 2 + 520, 450)], fill=B.YEL, width=8)
    d.text((W // 2, 1040), 'REAL SIZES  ·  ONE SCALE  ·  NEW SHORTS DAILY', font=B.font(B.MONO, 40), fill=B.CYAN, anchor='mm')
    img.save(A / 'bigger_banner_2560x1440.png')


def profile():
    img = B.background(800, 800); d = ImageDraw.Draw(img)
    B.shape(d, 'human', 230, 640, 60, 120, B.LINE, 8)
    B.shape(d, 'spire', 470, 640, 120, 520, B.YEL, 8)
    d.line([(120, 640), (680, 640)], fill=B.LINE, width=6)
    d.text((400, 720), 'BIGGER', font=B.font(B.BOLD, 110), fill=B.LINE, anchor='mm')
    img.save(A / 'bigger_profile_800x800.png')


def apply(hide_old):
    from bigger import yt
    from googleapiclient.http import MediaFileUpload
    api = yt(); ch = api.channels().list(part='snippet,brandingSettings', mine=True).execute()['items'][0]
    print('kanal:', ch['snippet']['title'])
    url = api.channelBanners().insert(media_body=MediaFileUpload(str(A / 'bigger_banner_2560x1440.png'), mimetype='image/png')).execute()['url']
    b = ch.get('brandingSettings', {}); b.setdefault('channel', {})
    b['channel']['description'] = DESCRIPTION; b['channel']['keywords'] = ' '.join(f'"{k}"' if ' ' in k else k for k in KEYWORDS)
    b['channel'].pop('unsubscribedTrailer', None); b['channel']['defaultLanguage'] = 'en'
    b.setdefault('image', {})['bannerExternalUrl'] = url; b.pop('hints', None)
    api.channels().update(part='brandingSettings', body={'id': ch['id'], 'brandingSettings': b}).execute()
    api.channels().update(part='status', body={'id': ch['id'], 'status': {'selfDeclaredMadeForKids': False}}).execute()
    print('✓ banner + açıklama + çocuklara özel değil')
    if not hide_old: return
    old = []
    for f in glob.glob('records/published/*.csv'):
        for row in csv.reader(open(f, encoding='utf-8')):
            if len(row) > 1 and row[1]: old.append(row[1])
    hf = Path('records/hidden_old.json'); hidden = json.loads(hf.read_text()) if hf.exists() else []
    for i in range(0, len(old), 50):
        for v in api.videos().list(part='status,snippet', id=','.join(old[i:i + 50])).execute().get('items', []):
            if v['status']['privacyStatus'] == 'private' and not v['status'].get('publishAt'): continue
            st = v['status']; was = st['privacyStatus']; st['privacyStatus'] = 'private'; st.pop('publishAt', None)
            api.videos().update(part='status', body={'id': v['id'], 'status': st}).execute()
            hidden.append({'id': v['id'], 'was': was, 'title': v['snippet']['title']})
    hf.write_text(json.dumps(hidden, indent=1, ensure_ascii=False)); print(f'✓ {len(hidden)} eski video gizli (records/hidden_old.json)')


if __name__ == '__main__':
    if '--make' in sys.argv or not (A / 'bigger_banner_2560x1440.png').exists():
        banner(); profile(); print('✓ görseller')
    if '--apply' in sys.argv: apply('--hide-old' in sys.argv)
