"""One-shot (re-runnable) channel setup via the YouTube Data API using the repo secrets:
description, keywords, country/language, banner, made-for-kids audience, playlists, home page sections.
The profile picture and @handle cannot be changed through the API (see README)."""
import json, os, sys
from googleapiclient.http import MediaFileUpload
import publish

HERE = os.path.dirname(os.path.abspath(__file__))
TITLE = "Fox Run Kids"
DESCRIPTION = """Stand up, kids! 🦊 Run, jump, duck and dodge with the fox!

Fox Run Kids makes immersive, interactive workout games for children. Our fox runs through a new 3D world every week (Candy World, Desert, Space, Snow, Jungle and more) and kids copy every move at home or in the classroom:

⬆️ JUMP over hurdles
⬇️ DUCK under barriers
⬅️➡️ DODGE left and right
🪙 Collect coins and finish the warm up moves

🎬 New Shorts every day: quick dodge challenges and brain breaks
🏃 New 8-minute immersive warm ups every Wednesday and Saturday

Perfect for brain breaks, PE warm ups, rainy days and daily movement.
Safety: make some space and play with a grown-up nearby.

#kidsworkout #brainbreak #kidsexercise"""
KEYWORDS = ('"kids workout" "brain break" "kids exercise" "immersive warm up" "interactive warm up" '
            '"obstacle run" "fox run" "pe warm up" "movement break" "classroom exercise" "dodge challenge" '
            '"kids fitness" "exercise for kids"')
PLAYLISTS = {
    "shorts": ("Dodge Challenge Shorts 🦊", "Quick jump, duck and dodge challenges. A new one every day!"),
    "long": ("Immersive Warm Ups (8 Min) 🏃", "Full interactive obstacle-run warm ups through a new world every week."),
    "brain": ("Classroom Brain Breaks 🧠", "Ready-to-play movement breaks for teachers and parents."),
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
    step("audience: made for kids", lambda: yt.channels().update(part="status", body={
        "id": cid, "status": {"selfDeclaredMadeForKids": True}}).execute())

    existing = {p["snippet"]["title"]: p["id"] for p in
                yt.playlists().list(part="snippet", mine=True, maxResults=50).execute().get("items", [])}
    ids = json.load(open(PL_FILE)) if os.path.exists(PL_FILE) else {}
    for key, (t, d) in PLAYLISTS.items():
        if key in ids:
            continue
        if t in existing:
            ids[key] = existing[t]
            continue
        p = yt.playlists().insert(part="snippet,status", body={
            "snippet": {"title": t, "description": d + "\n\nNew Fox Run Kids videos every day. #kidsworkout",
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
