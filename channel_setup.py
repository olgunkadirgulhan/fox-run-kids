"""One-shot (re-runnable) channel setup via the YouTube Data API using the repo secrets:
description, keywords, country/language, banner, made-for-kids audience, playlists, home page sections.
The profile picture and @handle cannot be changed through the API (see README)."""
import json, os, sys
from googleapiclient.http import MediaFileUpload
import publish

HERE = os.path.dirname(os.path.abspath(__file__))
TITLE = "Fox Run"   # API kanal adını değiştiremiyor: Studio'da elle "Fox Run" yapılmalı
DESCRIPTION = """Jump, duck and dodge with the fox! 🦊

Fox Run turns movement into a game. Our fox runs through a new 3D world every week (Candy World, Desert, Space, Snow, Jungle and more) and you play along from your desk, couch or living room:

⬆️ JUMP over hurdles
⬇️ DUCK under barriers
⬅️➡️ DODGE left and right
🪙 Collect coins and finish the quick moves

🎬 New Shorts every day: reaction tests and 40-second desk breaks
🏃 8-minute immersive run workouts every Wednesday and Saturday, no equipment needed

Been sitting too long? Stand up and beat the fox.
Safety: make some space and skip any move that hurts.

#reactiontest #deskbreak #workout"""
KEYWORDS = ('"reaction test" "reflex test" "desk break" "follow along workout" "virtual run" "immersive workout" '
            '"obstacle run" "fox run" "game workout" "no equipment workout" "dodge challenge" "movement break"')
PLAYLISTS = {
    "shorts": ("Reaction Tests & Dodge Challenges 🦊", "Quick jump, duck and dodge challenges. A new one every day!"),
    "long": ("8 Min Immersive Run Workouts 🏃", "Full game-style obstacle-run workouts through a new world every week."),
    "brain": ("Desk Break Workouts 🪑", "Short movement breaks for long days at the desk."),
}
SECTIONS = ["long", "shorts", "brain"]
PL_FILE = os.path.join(HERE, "playlists.json")


def step(name, fn):
    try:
        fn()
        print(f"✓ {name}", flush=True)
    except Exception as e:
        print(f"✗ {name}: {str(e)[:300]}", flush=True)


def main():
    yt = publish.yt()
    ch = yt.channels().list(part="id,snippet,brandingSettings,status", mine=True).execute()["items"][0]
    cid = ch["id"]
    print("channel:", ch["snippet"]["title"], cid)

    def branding():
        banner = yt.channelBanners().insert(media_body=MediaFileUpload(os.path.join(HERE, "branding", "banner.png"),
                                                                       mimetype="image/png")).execute()
        yt.channels().update(part="brandingSettings", body={"id": cid, "brandingSettings": {
            "channel": {"title": TITLE, "description": DESCRIPTION, "keywords": KEYWORDS, "country": "US",
                        "defaultLanguage": "en"},
            "image": {"bannerExternalUrl": banner["url"]}}}).execute()
    step("description, keywords, country/language, banner", branding)
    step("audience: not made for kids (13+)", lambda: yt.channels().update(part="status", body={
        "id": cid, "status": {"selfDeclaredMadeForKids": False}}).execute())

    existing = {p["snippet"]["title"]: p["id"] for p in
                yt.playlists().list(part="snippet", mine=True, maxResults=50).execute().get("items", [])}
    ids = json.load(open(PL_FILE)) if os.path.exists(PL_FILE) else {}
    for key, (t, d) in PLAYLISTS.items():
        if key in ids:  # var olan listenin adı/açıklaması güncellenir (2026-10-10 genel kitleye geçiş)
            step(f"playlist rename {key}", lambda: yt.playlists().update(part="snippet", body={"id": ids[key],
                 "snippet": {"title": t, "description": d + "\n\nNew Fox Run videos every day.", "defaultLanguage": "en"}}).execute())
            continue
        if t in existing:
            ids[key] = existing[t]
            continue
        p = yt.playlists().insert(part="snippet,status", body={
            "snippet": {"title": t, "description": d + "\n\nNew Fox Run videos every day.",
                        "defaultLanguage": "en"}, "status": {"privacyStatus": "public"}}).execute()
        ids[key] = p["id"]
        print("✓ playlist", t)
    json.dump(ids, open(PL_FILE, "w"), indent=2)

    if not ids.get("_sections"):
        def sections():
            for pos, key in enumerate(SECTIONS):
                yt.channelSections().insert(part="snippet,contentDetails", body={
                    "snippet": {"type": "singlePlaylist", "position": pos},
                    "contentDetails": {"playlists": [ids[key]]}}).execute()
        step("home page sections", sections)
        ids["_sections"] = True
        json.dump(ids, open(PL_FILE, "w"), indent=2)

    # back-fill playlists for videos uploaded before they existed
    import csv, glob
    for path in glob.glob(os.path.join(HERE, "records", "published", "*.csv")):
        for row in csv.reader(open(path)):
            cfg, vid = row[0], row[1]
            for key in (["shorts"] if cfg.startswith("short") else ["long", "brain"]):
                step(f"{vid} -> {key}", lambda: publish.add_to_playlist(yt, ids[key], vid))
    after = yt.channels().list(part="snippet", mine=True).execute()["items"][0]["snippet"]["title"]
    print("channel title now:", after)


if __name__ == "__main__":
    main()
