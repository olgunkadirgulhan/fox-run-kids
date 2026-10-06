"""Title / description / tags for a WARMUP_CFG (English, kids audience)."""
import game as Gm


def _pick(options, k=0):
    return options[(Gm.SEED + k) % len(options)]


def _ts(t):
    t = int(t)
    return f"{t // 60}:{t % 60:02d}"


def meta():
    world = Gm.KITS[Gm.SEGS[0]["world"]].title()
    if Gm.SHORT:
        ex = [s for s in Gm.SEGS if s["kind"] == "ex"]
        if Gm.FORMAT == "levelup":
            title = _pick([f"3 Levels of Dodge! 🦊 Can You Keep Up? {world} Run #shorts",
                           f"It Gets FASTER! 🦊 {world} Obstacle Run Levels #shorts",
                           f"Level 1, 2, 3! Can You Beat The Fox? {world} Run #shorts"])
        elif Gm.FORMAT == "movemix":
            moves = ", ".join(s["label"].title() for s in ex)
            title = _pick([f"Copy The Fox! 🦊 {moves} #shorts", f"Move With Me! {moves} 🦊 Brain Break #shorts"])
        elif Gm.FORMAT == "count":
            n, mv = Gm.rep_target(ex[0]), ex[0]["label"].title()
            title = _pick([f"Can You Do {n} {mv}? 🦊 Kids Challenge #shorts", f"{n} {mv} Challenge! Count With The Fox 🦊 #shorts"])
        else:
            title = _pick([
                f"Can You Dodge Them All? 🦊 {world} Run Challenge #shorts",
                f"Jump, Duck & Dodge! 🦊 {world} Obstacle Run #shorts",
                f"Can You Beat The Fox? {world} Run Brain Break #shorts",
                f"Dodge Challenge for Kids! 🦊 {world} Run #shorts",
                f"Stand Up & Play! {world} Obstacle Dodge #shorts",
            ])
        desc = (f"Stand up and play along! 🦊 Jump over hurdles, duck under bars and dodge left and right "
                f"with the fox in the {world} world. How many obstacles can you dodge?\n\n"
                "A quick active brain break for kids at home or in the classroom.\n\n"
                "#shorts #kidsworkout #brainbreak #kidsexercise #getmoving")
        tags = ["kids workout", "brain break", "kids exercise", "obstacle run", "dodge challenge", "fox run",
                f"{world.lower()} run", "movement break", "kids fitness", "shorts"]
    else:
        title = _pick([
            f"Immersive Interactive Warm Up | {world} Run Obstacle Course | Kids Exercise Game (8 Min)",
            f"{world} Run! 🦊 Jump, Duck & Dodge | Interactive Kids Workout | Brain Break",
            f"Kids Obstacle Run Game | {world} World Warm Up | Easy Daily Routine (8 Min)",
            f"Fox Run Warm Up 🦊 {world} Adventure | Immersive Kids Exercise | Brain Break",
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
        desc = (f"Stand up and run with the fox! 🦊 This immersive interactive warm up takes kids through the "
                f"{worlds} worlds. Jump over hurdles, duck under barriers, dodge left and right and do fun "
                "warm up moves between the obstacle runs.\n\n"
                "Great as a brain break, PE warm up or rainy-day workout at home or in the classroom. "
                "Make some space, copy the fox and collect the coins!\n\n"
                + "\n".join(ch) +
                "\n\nSafety: clear the space around you and wear comfy shoes. Grown-ups, please supervise.\n\n"
                "#kidsworkout #brainbreak #kidsexercise #warmup #pewarmup")
        tags = ["kids workout", "brain break", "immersive warm up", "interactive warm up", "kids exercise",
                "obstacle course", "fox run", f"{world.lower()} run", "pe warm up", "kids fitness", "movement break",
                "daily routine", "exercise for kids"]
    return title[:100], desc[:4900], tags


if __name__ == "__main__":
    t, d, g = meta()
    print(t)
    print(d)
    print(g)
