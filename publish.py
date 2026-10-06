"""Assemble chunk videos + audio, then upload to YouTube as private with scheduled publishAt (made for kids).
Usage: python publish.py <chunks_dir> <publish_at ISO8601 UTC>"""
import csv, datetime, glob, os, subprocess, sys
import game as Gm
import meta as Meta
import render2 as R
import post4

HERE = os.path.dirname(os.path.abspath(__file__))
SCOPES = ["https://www.googleapis.com/auth/youtube"]


def assemble(chunks_dir):
    parts = sorted(glob.glob(os.path.join(chunks_dir, "**", "chunk_*.mp4"), recursive=True))
    if not parts:
        sys.exit("no chunks found")
    lst = os.path.join(HERE, "parts.txt")
    with open(lst, "w") as fh:
        for p in parts:
            fh.write(f"file '{os.path.abspath(p)}'\n")
    post4.audio()
    out = os.path.join(HERE, "final_%s.mp4" % Gm.TAG)
    subprocess.run([R.FF, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst,
                    "-i", os.path.join(HERE, "audio_%s.wav" % Gm.TAG), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out], check=True)
    return out, len(parts)


def yt():
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    creds = Credentials(None, refresh_token=os.environ["YT_REFRESH_TOKEN"], client_id=os.environ["YT_CLIENT_ID"],
                        client_secret=os.environ["YT_CLIENT_SECRET"], token_uri="https://oauth2.googleapis.com/token")
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def upload(mp4, publish_at, thumb=None):
    from googleapiclient.http import MediaFileUpload
    title, desc, tags = Meta.meta()
    now = datetime.datetime.now(datetime.timezone.utc)
    when = datetime.datetime.fromisoformat(publish_at.replace("Z", "+00:00"))
    status = {"selfDeclaredMadeForKids": True, "containsSyntheticMedia": False, "embeddable": True}
    if when > now + datetime.timedelta(minutes=20):
        status.update(privacyStatus="private", publishAt=when.strftime("%Y-%m-%dT%H:%M:%SZ"))
    else:
        status.update(privacyStatus="public")  # slot already passed: publish right away
    body = {"snippet": {"title": title, "description": desc, "tags": tags, "categoryId": "27",
                        "defaultLanguage": "en", "defaultAudioLanguage": "en"}, "status": status}
    client = yt()
    want = os.environ.get("YT_CHANNEL_ID")
    if want:
        mine = client.channels().list(part="id", mine=True).execute()["items"][0]["id"]
        if mine != want:
            sys.exit(f"token belongs to {mine}, expected {want}")
    req = client.videos().insert(part="snippet,status", body=body,
                                 media_body=MediaFileUpload(mp4, mimetype="video/mp4", resumable=True, chunksize=-1))
    resp = None
    while resp is None:
        _, resp = req.next_chunk()
    vid = resp["id"]
    add_to_playlists(vid)
    if thumb and os.path.exists(thumb):
        try:
            client.thumbnails().set(videoId=vid, media_body=MediaFileUpload(thumb, mimetype="image/jpeg")).execute()
        except Exception as e:  # custom thumbnails need a verified channel
            print("thumbnail skipped:", e)
    return vid, title, status.get("publishAt", "now")


def add_to_playlist(client, playlist_id, video_id):
    have = client.playlistItems().list(part="contentDetails", playlistId=playlist_id, maxResults=50).execute().get("items", [])
    if any(i["contentDetails"]["videoId"] == video_id for i in have):
        return
    client.playlistItems().insert(part="snippet", body={"snippet": {
        "playlistId": playlist_id, "resourceId": {"kind": "youtube#video", "videoId": video_id}}}).execute()


def add_to_playlists(vid):
    import json
    path = os.path.join(HERE, "playlists.json")
    if not os.path.exists(path):
        return
    ids = json.load(open(path))
    for key in (["shorts"] if Gm.SHORT else ["long", "brain"]):
        if key in ids:
            try:
                add_to_playlist(yt(), ids[key], vid)
            except Exception as e:
                print("playlist skipped:", e)


def log(vid, title, when):
    d = os.path.join(HERE, "records", "published")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, Gm.TAG + ".csv"), "w", newline="") as fh:
        csv.writer(fh).writerow([Gm.CFG, vid, when, title])


if __name__ == "__main__":
    if sys.argv[1] == "--upload-only":
        mp4, publish_at = sys.argv[2], sys.argv[3]
        thumb = sys.argv[4] if len(sys.argv) > 4 else None
        vid, title, when = upload(mp4, publish_at, thumb)
        log(vid, title, when)
        print("uploaded", vid, title, when)
        sys.exit()
    chunks, publish_at = sys.argv[1], sys.argv[2]
    mp4, n = assemble(chunks)
    print("assembled", mp4, n, "chunks")
    thumb = None
    if not Gm.SHORT:
        src = glob.glob(os.path.join(chunks, "**", "thumb_src.jpg"), recursive=True)
        if src:
            thumb = os.path.join(HERE, "thumb_%s.jpg" % Gm.TAG)
            post4.thumbnail(src[0], thumb)
    if not all(os.environ.get(k) for k in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN")):
        print("YouTube secrets missing: queued in records/pending, video kept as artifact")
        os.makedirs(os.path.join(HERE, "records", "pending"), exist_ok=True)
        with open(os.path.join(HERE, "records", "pending", Gm.TAG + ".csv"), "w", newline="") as fh:
            csv.writer(fh).writerow([Gm.CFG, publish_at, os.environ.get("GITHUB_RUN_ID", ""), Gm.TAG])
        sys.exit(0)
    vid, title, when = upload(mp4, publish_at, thumb)
    log(vid, title, when)
    print("uploaded", vid, title, when)
