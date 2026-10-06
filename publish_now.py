"""Make a (scheduled/private) video public right now. Usage: python publish_now.py VIDEO_ID"""
import sys
import publish

vid = sys.argv[1]
yt = publish.yt()
v = yt.videos().list(part="status", id=vid).execute()["items"][0]
st = v["status"]
yt.videos().update(part="status", body={"id": vid, "status": {
    "privacyStatus": "public", "selfDeclaredMadeForKids": True, "embeddable": True,
    "license": st.get("license", "youtube"), "publicStatsViewable": st.get("publicStatsViewable", True)}}).execute()
print("public:", vid, yt.videos().list(part="status", id=vid).execute()["items"][0]["status"]["privacyStatus"])
