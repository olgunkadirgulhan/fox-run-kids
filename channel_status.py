"""Print channel-level settings (audience, branding) as YouTube reports them."""
import json
import publish

yt = publish.yt()
c = yt.channels().list(part="snippet,status,brandingSettings", mine=True).execute()["items"][0]
print("title:", c["snippet"]["title"])
print("status:", json.dumps(c["status"]))
b = c.get("brandingSettings", {}).get("channel", {})
print("country/lang:", b.get("country"), b.get("defaultLanguage"))
print("description starts:", (b.get("description") or "")[:60].replace("\n", " "))
