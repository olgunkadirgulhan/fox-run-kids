"""Title / description / tags for a WARMUP_CFG (English, general 13+ audience)."""
import game as Gm


def _pick(options, k=0):
    return options[(Gm.SEED + k) % len(options)]


def _ts(t):
    t = int(t)
    return f"{t // 60}:{t % 60:02d}"


def meta():
    # 2026-10-10: kanal "made for kids" çocuk egzersizinden genel kitleye (13+) döndü: çocuk etiketli Shorts
    # akışta neredeyse hiç gösterilmiyordu (10 videoda 2 izlenme). Ton: oyun gibi refleks testi + masa başı mola.
    world = Gm.KITS[Gm.SEGS[0]["world"]].title()
    if Gm.SHORT:
        ex = [s for s in Gm.SEGS if s["kind"] == "ex"]
        if Gm.FORMAT == "levelup":
            title = _pick([f"Only 1% Reach Level 3 🦊 {world} Run Reaction Test #shorts",
                           f"It Gets FASTER… How Far Can You Get? {world} Run #shorts",
                           f"Level 1 vs Level 3: Can Your Reflexes Keep Up? 🦊 #shorts"])
        elif Gm.FORMAT == "movemix":
            moves = ", ".join(s["label"].title() for s in ex)
            title = _pick([f"40-Second Desk Break: {moves} 🦊 #shorts",
                           f"Been Sitting All Day? Do This Now 🦊 {moves} #shorts"])
        elif Gm.FORMAT == "count":
            n, mv = Gm.rep_target(ex[0]), ex[0]["label"].title()
            title = _pick([f"Can You Do {n} {mv} Before The Fox? 🦊 #shorts",
                           f"{n} {mv} Challenge — Most People Quit at Half 😮‍💨 #shorts"])
        else:
            title = _pick([
                f"Can You Dodge Them All? 🦊 {world} Run Reaction Test #shorts",
                f"Jump, Duck & Dodge — Test Your Reflexes 🦊 {world} Run #shorts",
                f"Your Reaction Time vs The Fox 🦊 {world} Run #shorts",
                f"Don't Get Hit! {world} Obstacle Run Challenge #shorts",
                f"Stand Up & Play: {world} Dodge Challenge 🦊 #shorts",
            ])
        desc = (f"Stand up and play along! 🦊 Jump over hurdles, duck under bars and dodge left and right "
                f"with the fox in the {world} world. How many obstacles did you dodge? Tell us in the comments!\n\n"
                "A quick game-style movement break for anyone stuck at a desk.\n\n"
                "#shorts #reactiontest #deskbreak #challenge #workout")
        tags = ["reaction test", "reflex test", "dodge challenge", "desk break", "movement break", "obstacle run",
                "fox run", f"{world.lower()} run", "follow along workout", "game workout", "shorts"]
    else:
        title = _pick([
            f"8 Min Immersive Obstacle Run Workout | {world} World | Follow Along",
            f"{world} Run! 🦊 Jump, Duck & Dodge | 8 Min Game-Style Workout",
            f"Virtual Run Workout: {world} World Obstacle Course (8 Min, No Equipment)",
            f"Desk Break Workout 🦊 {world} Adventure | 8 Min Immersive Run",
        ])
        ch = []
        for s in Gm.SEGS:
            if s["kind"] == "hook":
                ch.append(f"{_ts(s['t0'])} Get Ready!")
            elif s["kind"] == "game":
                ch.append(f"{_ts(s['t0'])} Obstacle Run {s['n']} - {Gm.KITS[s['world']].title()}")
            elif s["kind"] == "ex":
                ch.append(f"{_ts(s['t0'])} {s['label'].title()}")
            else:
                ch.append(f"{_ts(s['t0'])} Great Job!")
        worlds = ", ".join(Gm.KITS[w].title() for w in dict.fromkeys(s["world"] for s in Gm.SEGS))
        desc = (f"Stand up and run with the fox! 🦊 This immersive, game-style workout takes you through the "
                f"{worlds} worlds. Jump over hurdles, duck under barriers, dodge left and right and do quick "
                "moves between the obstacle runs.\n\n"
                "No equipment, about 8 minutes: a fun way to break up a long day of sitting. "
                "Make some space, copy the fox and collect the coins!\n\n"
                + "\n".join(ch) +
                "\n\nSafety: clear the space around you, wear comfy shoes and skip any move that hurts.\n\n"
                "#workout #followalong #deskbreak #virtualrun #noequipment")
        tags = ["follow along workout", "virtual run", "immersive workout", "game workout", "desk break",
                "obstacle course", "fox run", f"{world.lower()} run", "no equipment workout", "8 minute workout",
                "movement break", "home workout"]
    return title[:100], desc[:4900], tags


if __name__ == "__main__":
    t, d, g = meta()
    print(t)
    print(d)
    print(g)
