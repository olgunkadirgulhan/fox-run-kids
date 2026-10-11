"""Make a (scheduled/private) video public right now, or hold it: python publish_now.py VIDEO_ID [private]
(private = zamanlanmış yayını iptal eder, video gizli kalır; silmez)"""
import sys
import publish

vid = sys.argv[1]
yt = publish.yt()
v = yt.videos().list(part="status", id=vid).execute()["items"][0]
st = v["status"]
target = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] else "public"
yt.videos().update(part="status", body={"id": vid, "status": {
    "privacyStatus": target, "selfDeclaredMadeForKids": False, "embeddable": True,
    "license": st.get("license", "youtube"), "publicStatsViewable": st.get("publicStatsViewable", True)}}).execute()
import json
after = yt.videos().list(part="status,processingDetails,suggestions", id=vid).execute()["items"][0]
print("before:", json.dumps(st))
print("after:", json.dumps(after.get("status")))
print("processing:", json.dumps(after.get("processingDetails", {}))[:300])
