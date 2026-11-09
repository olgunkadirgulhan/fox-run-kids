"""Emoji görsel bilmece Shorts (2026-11-08). Aynı dosya iki kanalda, QUIZ_KIND ile:
  food   — Guess the Food (Bigger Than You Think kanalı; trend "guess the food" medyan 1.8M, 34 kanal): aşırı yakından başlayıp
           uzaklaşan görüntü ("zoom") → 3 şık → cevap
  animal — Guess the Animal (Wild Matchups kanalı; "guess the animal" medyan 539K, 38 kanal): siyah gölge → renkli cevap
Her video 6 tur, kolaydan zora (zoom başlangıcı / benzer şıklar), seri numarası #N. İngilizce, ABD izleyicisi.
Emoji: Noto Color Emoji (SIL OFL). Uydurma bilgi yok, sadece tanıma oyunu.
    QUIZ_KIND=food python emojiquiz.py --dry-run | --auto
"""
import os, random, sys
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps
import shortkit as K

HERE = Path(__file__).resolve().parent
KIND = os.environ.get('QUIZ_KIND', 'food')
LOG = HERE / 'records' / f'{KIND}quiz_published.csv'
OUT = HERE / 'out' / f'{KIND}quiz'
DRY = '--dry-run' in sys.argv
N_Q, THINK, SHOW = 6, 3.4, 1.6
INTRO, OUTRO = 1.4, 3.0
GOLD = (255, 215, 60)

FOOD = {'🍎': 'Apple', '🍐': 'Pear', '🍊': 'Orange', '🍋': 'Lemon', '🍌': 'Banana', '🍉': 'Watermelon', '🍇': 'Grapes',
        '🍓': 'Strawberry', '🫐': 'Blueberries', '🍈': 'Melon', '🍒': 'Cherries', '🍑': 'Peach', '🥭': 'Mango', '🍍': 'Pineapple',
        '🥥': 'Coconut', '🥝': 'Kiwi', '🍅': 'Tomato', '🍆': 'Eggplant', '🥑': 'Avocado', '🥦': 'Broccoli', '🥬': 'Lettuce',
        '🥒': 'Cucumber', '🌽': 'Corn', '🥕': 'Carrot', '🧄': 'Garlic', '🧅': 'Onion', '🥔': 'Potato', '🥐': 'Croissant',
        '🥯': 'Bagel', '🍞': 'Bread', '🥖': 'Baguette', '🥨': 'Pretzel', '🧀': 'Cheese', '🥚': 'Egg', '🥞': 'Pancakes',
        '🧇': 'Waffle', '🥓': 'Bacon', '🍗': 'Chicken Leg', '🌭': 'Hot Dog', '🍔': 'Burger', '🍟': 'Fries', '🍕': 'Pizza',
        '🥪': 'Sandwich', '🌮': 'Taco', '🌯': 'Burrito', '🥗': 'Salad', '🍝': 'Spaghetti', '🍜': 'Ramen', '🍣': 'Sushi',
        '🥟': 'Dumpling', '🍤': 'Fried Shrimp', '🍙': 'Rice Ball', '🍦': 'Ice Cream Cone', '🥧': 'Pie', '🧁': 'Cupcake',
        '🍰': 'Cake Slice', '🍮': 'Pudding', '🍭': 'Lollipop', '🍫': 'Chocolate Bar', '🍿': 'Popcorn', '🍩': 'Donut',
        '🍪': 'Cookie', '🥜': 'Peanuts', '🍯': 'Honey', '🧈': 'Butter', '🥥': 'Coconut', '🫑': 'Bell Pepper', '🥙': 'Pita Wrap'}
ANIMAL = {'🐶': 'Dog', '🐱': 'Cat', '🐭': 'Mouse', '🐹': 'Hamster', '🐰': 'Rabbit', '🦊': 'Fox', '🐻': 'Bear', '🐼': 'Panda',
          '🐨': 'Koala', '🐯': 'Tiger', '🦁': 'Lion', '🐮': 'Cow', '🐷': 'Pig', '🐸': 'Frog', '🐵': 'Monkey', '🐔': 'Chicken',
          '🐧': 'Penguin', '🦆': 'Duck', '🦅': 'Eagle', '🦉': 'Owl', '🦇': 'Bat', '🐺': 'Wolf', '🐗': 'Boar', '🐴': 'Horse',
          '🐝': 'Bee', '🦋': 'Butterfly', '🐌': 'Snail', '🐞': 'Ladybug', '🐜': 'Ant', '🦂': 'Scorpion', '🐢': 'Turtle',
          '🐍': 'Snake', '🦎': 'Lizard', '🦖': 'T. Rex', '🐙': 'Octopus', '🦑': 'Squid', '🦐': 'Shrimp', '🦞': 'Lobster',
          '🦀': 'Crab', '🐡': 'Pufferfish', '🐠': 'Tropical Fish', '🐬': 'Dolphin', '🐳': 'Whale', '🦈': 'Shark',
          '🐊': 'Crocodile', '🐆': 'Leopard', '🦓': 'Zebra', '🦍': 'Gorilla', '🐘': 'Elephant', '🦛': 'Hippo', '🦏': 'Rhino',
          '🐪': 'Camel', '🦒': 'Giraffe', '🦘': 'Kangaroo', '🦬': 'Bison', '🐑': 'Sheep', '🦙': 'Llama', '🐐': 'Goat', '🦌': 'Deer',
          '🦃': 'Turkey', '🦚': 'Peacock', '🦜': 'Parrot', '🦢': 'Swan', '🦩': 'Flamingo', '🦝': 'Raccoon', '🦨': 'Skunk',
          '🦡': 'Badger', '🦫': 'Beaver', '🦦': 'Otter', '🦥': 'Sloth', '🦔': 'Hedgehog', '🐿': 'Squirrel'}
CFG = {'food': dict(items=FOOD, head='GUESS THE FOOD', c1=(120, 40, 30), c2=(50, 15, 12), noun='FOOD', tags=['guess the food', 'food quiz', 'emoji quiz', 'guess the emoji', 'zoom quiz', 'quiz', 'shorts']),
       'animal': dict(items=ANIMAL, head='GUESS THE ANIMAL', c1=(30, 90, 50), c2=(10, 35, 18), noun='ANIMAL', tags=['guess the animal', 'animal quiz', 'shadow quiz', 'animals', 'quiz', 'shorts'])}[KIND]


def big(e):
    return K.emoji_img(e, 900)


def silhouette(im):
    a = im.split()[-1]
    return Image.merge('RGBA', (Image.new('L', im.size, 15), Image.new('L', im.size, 15), Image.new('L', im.size, 25), a))


def make_plan(rnd, recent):
    items = [e for e in CFG['items'] if K.emoji_ok(e)]
    fresh = [e for e in items if e not in recent] or items
    picks = rnd.sample(fresh, N_Q); qs = []
    for i, e in enumerate(picks):
        opts = [e] + rnd.sample([x for x in items if x != e], 2); rnd.shuffle(opts)
        # zorluk: zoom başlangıcı (food) 3x → 9x ; gölge (animal) sonlarda daha küçük
        qs.append(dict(e=e, opts=opts, lv=i + 1, z=2.2 + i * 0.7, fx=rnd.uniform(0.3, 0.7), fy=rnd.uniform(0.3, 0.7)))
    return qs


def frame_fn(p):
    qs = p['qs']; seg = THINK + SHOW; total = INTRO + N_Q * seg + OUTRO; names = CFG['items']

    def f(T):
        img = K.gradient(CFG['c1'], CFG['c2'], False).copy(); d = ImageDraw.Draw(img)
        if T < INTRO:
            u = K.ease(T / 0.5)
            K.text(d, (K.W / 2, 760), 'GUESS THE', int(130 * u) + 1)
            K.text(d, (K.W / 2, 900), CFG['noun'] + '!', int(170 * u) + 1, fill=GOLD)
            K.text(d, (K.W / 2, 1070), f"6 LEVELS · #{p['n']}", int(64 * u) + 1)
            return img
        if T >= INTRO + N_Q * seg:
            u = K.ease((T - INTRO - N_Q * seg) / 0.5)
            K.text(d, (K.W / 2, 720), 'HOW MANY', int(110 * u) + 1)
            K.text(d, (K.W / 2, 850), 'DID YOU GET?', int(110 * u) + 1, fill=GOLD)
            K.text(d, (K.W / 2, 1010), 'COMMENT YOUR SCORE', int(70 * u) + 1)
            K.text(d, (K.W / 2, 1160), f"NEXT: QUIZ #{p['n'] + 1}", int(60 * u) + 1)
            return img
        i = int((T - INTRO) // seg); lt = T - INTRO - i * seg; q = qs[i]; show = lt >= THINK
        K.text(d, (K.W / 2, 140), f"LEVEL {q['lv']}/6", 70, fill=GOLD)
        box = (110, 260, K.W - 110, 1010)   # resim kartı
        d.rounded_rectangle(box, radius=44, fill=(255, 255, 255, 240))
        bw, bh = box[2] - box[0] - 40, box[3] - box[1] - 40
        src = big(q['e'])
        if KIND == 'food' and not show:
            z = q['z'] - (q['z'] - 1.4) * K.ease(lt / THINK)   # uzaklaşan zoom (ama tam açılmaz)
            cw, ch = src.width / z, src.height / z
            cx, cy = src.width * q['fx'], src.height * q['fy']
            x0 = min(max(0, cx - cw / 2), src.width - cw); y0 = min(max(0, cy - ch / 2), src.height - ch)
            crop = src.crop((int(x0), int(y0), int(x0 + cw), int(y0 + ch))).resize((bw, int(bw * ch / cw)), Image.LANCZOS)
            crop = crop.crop((0, 0, bw, min(bh, crop.height)))
            img.alpha_composite(crop, (box[0] + 20, box[1] + 20 + (bh - crop.height) // 2))
        else:
            s = min(bw, bh) * (0.8 if show else (0.85 - 0.06 * i))
            e = src.resize((int(s), int(s * src.height / src.width)), Image.LANCZOS)
            if KIND == 'animal' and not show: e = silhouette(e)
            img.alpha_composite(e, (int(K.W / 2 - e.width / 2), int((box[1] + box[3]) / 2 - e.height / 2)))
        for j, c in enumerate(q['opts']):
            y = 1170 + j * 170; ok = c == q['e']
            col = ((60, 180, 100) if ok else (95, 95, 105)) if show else (255, 255, 255)
            d.rounded_rectangle([110, y - 68, K.W - 110, y + 68], radius=38, fill=col + (255,))
            K.text(d, (K.W / 2, y), f"{'ABC'[j]}. {names[c].upper()}", 62, fill=(255, 255, 255) if show else (40, 30, 30),
                   stroke=(40, 30, 30) if show else (255, 255, 255), max_w=K.W - 300)
        if not show:
            frac = max(0.0, 1 - lt / THINK)
            d.rounded_rectangle([90, 1720, K.W - 90, 1766], radius=23, fill=(255, 255, 255, 120))
            d.rounded_rectangle([90, 1720, 90 + max(46, (K.W - 180) * frac), 1766], radius=23, fill=GOLD)
        return img
    events = [(INTRO + i * seg, 'new') for i in range(N_Q)] + [(INTRO + i * seg + s, 'tick') for i in range(N_Q) for s in (1, 2, 3)]
    events += [(INTRO + i * seg + THINK, 'ding') for i in range(N_Q)] + [(INTRO + N_Q * seg, 'end')]
    return f, total, events


# 2026-11-09: 576 kombinasyon/tür (3/gün ≈ 6 ay); tkey #N'i yok saydığından 5 sabit başlık 5. videoda bitiyordu
_HOOKS = {'food': ['Guess the Food From the Zoom!', 'Can You Guess the Food?', 'Zoom Quiz: Guess the Food!', 'Only Foodies Pass Level 6!', 'What Food Is This?', 'Name This Food!', 'Zoomed-In Food Quiz!', 'Food Zoom Challenge!', 'Guess What We Zoomed Into!', 'How Many Foods Can You Name?', 'Food Detective Quiz!', 'Can You Beat the Food Zoom?', 'Mystery Food Zoom!', 'Too Close to Tell?', 'Name That Food!', 'The Real Foodie Test!', 'Zoom In, Guess the Food!', 'Food Guessing Game!', 'Close-Up Food Quiz!', 'Test Your Food Eyes!', 'Spot the Food!', 'Think You Know Food?', 'Hungry Brain Quiz!', 'Which Food Is Hiding?'], 'animal': ['Guess the Animal by Its Shadow!', 'Shadow Quiz: Guess the Animal!', 'Can You Name All 6 Animals?', 'Guess the Animal!', 'Whose Shadow Is This?', 'Name This Animal!', 'Animal Shadow Challenge!', 'Mystery Animal Shadow!', 'How Many Animals Can You Name?', 'Animal Detective Quiz!', 'Can You Beat the Shadow Quiz?', 'Name That Shadow!', 'The Real Animal Lover Test!', 'Which Animal Is Hiding?', 'Silhouette Quiz: Name the Animal!', 'Animal Guessing Game!', 'Spot the Animal!', 'Test Your Animal Eyes!', 'Think You Know Animals?', 'Shadow Animals Quiz!', 'Who Made This Shadow?', 'Wild Shadow Challenge!', 'Zoo Shadow Quiz!', 'Guess Who From the Shadow!']}[KIND]
_EM = {'food': ['🔍', '🍔', '🍕', '🍩'], 'animal': ['🐾', '🦁', '🐘', '🐼']}[KIND]
_TAILS = ['6 Levels {0}', 'Level 1-6 {1}', 'Easy to Hard {2}', '6 Rounds {3}', 'Can You Get 6/6? {0}', 'Hard Mode at the End {1}', 'Comment Your Score {2}', 'Beat Your Friends {3}', '3 Seconds Each {0}', 'No Cheating {1}', 'Level 6 Is Tough {2}', 'How Far Can You Go? {3}', 'Daily Quiz {0}', 'Quick Brain Test {1}', 'Try It With Family {2}', 'Keep Your Streak {3}', 'Six Chances {0}', 'Answer Before Time Ends {1}', 'Fast Round {2}', 'Play Along {3}', 'Score Yourself {0}', 'Test Yourself {1}', 'Challenge a Friend {2}', 'Beat the Timer {3}']
TITLES = [f'{h} {t.format(*_EM)} #{{n}}' for h in _HOOKS for t in _TAILS]


def main():
    a = sys.argv[1:]
    if '--auto' in a and K.today_count(LOG) >= int(os.environ.get('PER_DAY') or 3):
        print('bugünkü sayı doldu'); return
    rows = K.rows(LOG); recent = {x for r in rows[-8:] for x in r['topic_id'].split(':', 1)[-1].split('|')}
    rnd = random.Random(); qs = make_plan(rnd, recent)
    n = len(rows) + 1; p = dict(qs=qs, n=n, seed=rnd.randrange(10 ** 6))
    seen = {K.tkey(r['title']) for r in rows}
    opts = [t.format(n=n) for t in TITLES]; rnd.shuffle(opts)
    title = next((o for o in opts if K.tkey(o) not in seen), opts[0])
    desc = (f"Guess the {CFG['noun'].lower()}! 6 levels from easy to hard.\n\n"
            + '\n'.join(f"Level {q['lv']}: {CFG['items'][q['e']]} {q['e']}" for q in qs)
            + '\n\nHow many did you get? Comment your score 👇 New quiz every day.\n\n'
            'Emoji: Noto Color Emoji by Google (SIL Open Font License).\n\n#shorts #quiz #' + ('guessthefood #food' if KIND == 'food' else 'guesstheanimal #animals'))
    f, total, events = frame_fn(p)
    stamp = datetime.now(timezone.utc).strftime('%Y-%m-%d_%H%M%S')
    print(f'[{KIND}] #{n} {title}', flush=True)
    mp4 = K.render(f, total, events, p['seed'], OUT / f'{KIND}_{stamp}.mp4')
    if DRY: print('  [dry-run]', mp4); return
    pa = K.publish_at(['15:00', '18:00', '20:30'], K.today_count(LOG))
    vid = K.upload(mp4, title + ' #shorts', desc, CFG['tags'], pa, category='24')
    K.record(LOG, f'{KIND}:' + '|'.join(q['e'] for q in qs), vid, title, pa)
    print(f'  ✓ https://youtu.be/{vid} ({pa})')


if __name__ == '__main__':
    main()
