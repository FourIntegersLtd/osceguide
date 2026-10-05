"""repl.py <k> <edits.json> : apply [[old,new],...] substring edits to narration and framing (not the checked lines), report hits, lint."""
import json, re, sys
from pipe import call, mid, patch
from lint import lint
k, edits = sys.argv[1], json.load(open(sys.argv[2]))
st, item = call("GET", f"/media/by-id/{mid(k)}"); c = item["content"]; c.pop("status", None)
hits = {o: 0 for o, _ in edits}
def fix(x):
    if isinstance(x, str):
        for o, n in edits:
            if o in x: hits[o] += 1; x = x.replace(o, n)
        return re.sub(r" +([.,;:!?])", r"\1", x)
    if isinstance(x, list): return [fix(v) for v in x]
    if isinstance(x, dict): return {kk: fix(v) for kk, v in x.items()}
    return x
for s in c["slides"]: s["narration"] = fix(s["narration"])
c["presentation"] = fix(c["presentation"])
miss = [o[:60] for o, h in hits.items() if h != 1]
print(k, "edits", len(edits), "hit once", len(edits) - len(miss), "MISSED/MULTI:" if miss else "", *miss)
print(patch(item, c))
st, item = call("GET", f"/media/by-id/{mid(k)}"); lint(k, item["content"])
