"""Upload videos rendered before YouTube secrets existed (records/pending/<tag>.csv: cfg, publish_at, run_id, tag)."""
import csv, datetime, glob, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
files = sorted(glob.glob(os.path.join(HERE, "records", "pending", "*.csv")))
now = datetime.datetime.now(datetime.timezone.utc)
k = 0
for path in files:
    cfg, at, run_id, tag = next(csv.reader(open(path)))
    d = os.path.join(HERE, "dl_" + tag)
    if subprocess.run(["gh", "run", "download", run_id, "-n", "video-" + tag.replace(".", "-"), "-D", d]).returncode:
        print("artifact missing for", cfg)
        continue
    when = datetime.datetime.fromisoformat(at.replace("Z", "+00:00"))
    if when < now + datetime.timedelta(minutes=30):  # slot passed: spread catch-up uploads 3 h apart
        k += 1
        when = now + datetime.timedelta(minutes=40 + 180 * (k - 1))
    env = dict(os.environ, WARMUP_CFG=cfg)
    r = subprocess.run([sys.executable, "publish.py", "--upload-only", os.path.join(d, "final_%s.mp4" % tag),
                        when.strftime("%Y-%m-%dT%H:%M:%SZ")], env=env, cwd=HERE)
    if r.returncode == 0:
        os.remove(path)
