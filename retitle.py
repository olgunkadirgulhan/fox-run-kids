"""Yayınlanmış bir videonun başlığını değiştirir (ör. tescilli marka adı geçen başlıklar).
Usage: python retitle.py VIDEO_ID "New title" """
import os, sys
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

vid, title = sys.argv[1], sys.argv[2][:100]
creds = Credentials(None, refresh_token=os.environ["YT_REFRESH_TOKEN"], client_id=os.environ["YT_CLIENT_ID"],
                    client_secret=os.environ["YT_CLIENT_SECRET"], token_uri="https://oauth2.googleapis.com/token")
yt = build("youtube", "v3", credentials=creds, cache_discovery=False)
sn = yt.videos().list(part="snippet", id=vid).execute()["items"][0]["snippet"]
old = sn["title"]
sn["title"] = title
import re
sn["description"] = sn.get("description", "").replace("Candy Land", "Candy World")
# 2026-10-13: kanal 13+ genel kitle (madeForKids=False) → çocuğa hitap eden ifadeler başlık/açıklama/etiketten çıkar (COPPA tutarlılığı)
KID = re.compile(r"\b(for kids|kids'?|children'?s?|brain breaks?|preschool|toddlers?|classroom|PE class)\b", re.I)
sn["description"] = re.sub(r"[ \t]{2,}", " ", KID.sub("", sn["description"]))
sn["tags"] = [t for t in sn.get("tags", []) if not KID.search(t)]
yt.videos().update(part="snippet", body={"id": vid, "snippet": {k: sn[k] for k in
                   ("title", "description", "tags", "categoryId", "defaultLanguage", "defaultAudioLanguage") if k in sn}}).execute()
print(f"{vid}: {old!r} -> {title!r}")
