"""Upload videos that were rendered before YouTube secrets existed (pending.csv rows: cfg, publish_at, run_id, tag)."""
import csv, datetime, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
path = os.path.join(HERE, "pending.csv")
if not os.path.exists(path):
    sys.exit(0)
rows = [r for r in csv.reader(open(path)) if r]
now = datetime.datetime.now(datetime.timezone.utc)
left, k = [], 0
for cfg, at, run_id, tag in rows:
    d = os.path.join(HERE, "dl_" + tag)
    r = subprocess.run(["gh", "run", "download", run_id, "-n", "video-" + tag.replace(".", "-"), "-D", d])
    if r.returncode:
        print("artifact missing for", cfg)
        left.append([cfg, at, run_id, tag])
        continue
    when = datetime.datetime.fromisoformat(at.replace("Z", "+00:00"))
    if when < now + datetime.timedelta(minutes=30):  # slot passed: spread catch-up uploads 3 h apart
        k += 1
        when = now + datetime.timedelta(minutes=40 + 180 * (k - 1))
    mp4 = os.path.join(d, "final_%s.mp4" % tag)
    env = dict(os.environ, WARMUP_CFG=cfg)
    r = subprocess.run([sys.executable, "publish.py", "--upload-only", mp4, when.strftime("%Y-%m-%dT%H:%M:%SZ")], env=env, cwd=HERE)
    if r.returncode:
        left.append([cfg, at, run_id, tag])
with open(path, "w", newline="") as fh:
    csv.writer(fh).writerows(left)
