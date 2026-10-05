import json, secrets, sys

from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "slide-scripts" / "tools"))
import publish_deck as p

snap, *keep = sys.argv[1:]  # keep: an existing slide id, to replace that deck in place
c = json.load(open(snap))["content"]
sid = keep[0] if keep else "slide_" + secrets.token_hex(4)
c.pop("local_video_path", None)
url = c["final_video_url"]
tmp = snap + ".sample.json"
json.dump(c, open(tmp, "w"))
content = p._content(tmp, sid)
content["final_video_url"] = url
content["narration_voice"] = "elevenlabs-ben-v1"
p.OUT.mkdir(exist_ok=True)
p._published_file(sid).write_text(json.dumps(content, indent=1, ensure_ascii=False), encoding="utf-8")
print(sid)
