"""Drive the staff media pipeline over the local platform-api, the way the staff screen does.

pipe.py create <deck.json> [exam_code] | get <id> <out.json> | post <id> <action> [json] | wait <id> <busy,statuses> <out.json>
Every other script imports ROOT, W (work dir), R (slide-scripts) and call() from here.
"""
import json, os, shutil, subprocess, sys, time, urllib.request, urllib.error
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]                      # repo root: .claude/skills/make-slide-deck/scripts
R = ROOT / "slide-scripts"                  # deck JSONs and mp4s: the source of truth, not in git
W = R / "work"                              # per-deck working files: spec<k>.py, d<k>.id, f<k>.json ...
W.mkdir(parents=True, exist_ok=True)
BASE = os.environ.get("PLATFORM_API_URL", "http://127.0.0.1:8012") + "/api/v1"
NODE = shutil.which("node") or os.path.expanduser("~/.nvm/versions/node/v22.22.3/bin/node")


def mid(k):
    return (W / f"d{k}.id").read_text().strip()


def name(k):
    return (W / f"d{k}.name").read_text().strip()


def token(fresh=False):
    p = W / "session.json"
    if fresh or not p.exists():
        subprocess.run([NODE, str(HERE / "signin.mjs"), str(p)], check=True, capture_output=True)
    return json.loads(p.read_text())["access_token"]


def call(method, path, body=None, retry=True):
    req = urllib.request.Request(BASE + path, method=method, data=None if body is None else json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {token()}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            raw = r.read(); return r.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        if e.code == 401 and retry:
            token(fresh=True); return call(method, path, body, False)
        return e.code, e.read().decode()[:2000]


def patch(item, content):
    st, r = call("PATCH", f"/media/{item['id']}", {"title": item["title"], "summary": item["summary"], "content": content})
    return f"{st} {r if st >= 300 else r['status']}"


def strip(content):
    c = {k: v for k, v in content.items() if k != "references"}
    c["slides"] = [{k: v for k, v in s.items() if k != "refs"} for s in c["slides"]]
    return c


def wait(media_id, busy, limit=3600):
    t0 = time.time()
    while time.time() - t0 < limit:
        st, item = call("GET", f"/media/by-id/{media_id}")
        if st == 200 and item["content"].get("status") not in busy:
            return item
        time.sleep(15)
    raise SystemExit("timed out")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "create":
        deck = json.load(open(sys.argv[2]))
        st, r = call("POST", "/media", {"kind": "slide_deck", "title": deck["title"], "exam_code": sys.argv[3] if len(sys.argv) > 3 else None,
                                        "summary": deck["about"], "content": strip(deck)})
        print(st, r if st >= 300 else r["id"])
    elif cmd == "get":
        st, item = call("GET", f"/media/by-id/{sys.argv[2]}")
        json.dump(item, open(sys.argv[3], "w"), indent=1); print(st, item.get("status") if isinstance(item, dict) else item)
    elif cmd == "post":
        body = json.loads(sys.argv[4]) if len(sys.argv) > 4 else None
        st, r = call("POST", f"/media/{sys.argv[2]}/{sys.argv[3]}", body)
        print(st, r if st >= 300 else r["content"].get("status"))
    elif cmd == "wait":
        item = wait(sys.argv[2], set(sys.argv[3].split(",")))
        json.dump(item, open(sys.argv[4], "w"), indent=1)
        print(item["content"].get("status"), json.dumps(item["content"].get("review", {}).get("error")))
