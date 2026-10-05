"""new.py <k> <deck-basename> [exam_code] : build work/spec<k>.py into slide-scripts/<basename>.json, create the draft, start the rewrite.
No platform fact check: it calls Clinical Buddy, which the user stopped for cost. Check facts yourself first (SKILL.md)."""
import json, subprocess, sys
from pipe import HERE, R, W, call
k, base = sys.argv[1], sys.argv[2]
deck = R / f"{base}.json"
print(subprocess.run([sys.executable, str(HERE / "build.py"), str(W / f"spec{k}.py"), str(deck)], check=True, capture_output=True, text=True).stdout.strip())
from pipe import strip
d = json.load(open(deck))
st, r = call("POST", "/media", {"kind": "slide_deck", "title": d["title"], "exam_code": sys.argv[3] if len(sys.argv) > 3 else None,
                                "summary": d["about"], "content": strip(d)})
if st >= 300: raise SystemExit(f"create failed {st} {r}")
(W / f"d{k}.id").write_text(r["id"]); (W / f"d{k}.name").write_text(base)
st, r = call("POST", f"/media/{r['id']}/write-script", {"rewrite": True})
print(k, (W / f"d{k}.id").read_text(), st, r if st >= 300 else r["content"].get("status"))
