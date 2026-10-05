"""decide.py <k> '<swaps [[from,to],...]>' '<decisions {"idx":["accepted",from,to]|["dismissed"]}>'

Edit work/spec<k>.py with the swaps, rebuild the deck, record the fact decisions on the draft, start the rewrite.
Every contradicted or conflict claim needs a decision; not_found claims do not. An accepted decision's `from`
must be text in the rebuilt deck, so never also swap that same text.
"""
import json, subprocess, sys
from pipe import HERE, R, W, call, mid, name, patch, strip
k, swaps, dec = sys.argv[1], json.loads(sys.argv[2]), json.loads(sys.argv[3])
p = W / f"spec{k}.py"; s = p.read_text()
for a, b in swaps:
    assert a in s, f"not in spec: {a}"
    s = s.replace(a, b)
p.write_text(s)
deck = R / f"{name(k)}.json"
print(subprocess.run([sys.executable, str(HERE / "build.py"), str(p), str(deck)], check=True, capture_output=True, text=True).stdout.strip())
item = json.load(open(W / f"f{k}.json")); c = item["content"]; c.pop("status", None)
c["slides"] = strip(json.load(open(deck)))["slides"]
claims = c["review"]["facts"]["claims"]
for i, d in dec.items():
    cl = claims[int(i)]; cl["decision"] = d[0]
    if d[0] == "accepted": cl["swap"] = {"from": d[1], "to": d[2]}
print(patch(item, c))
st, r = call("POST", f"/media/{mid(k)}/write-script", {"rewrite": True})
print(st, r if st >= 300 else r["content"].get("status"))
