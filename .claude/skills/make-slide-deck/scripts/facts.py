"""facts.py <k> : wait for the fact check, save work/f<k>.json, print every claim that is not supported."""
import collections, json, sys
from pipe import W, mid, wait
k = sys.argv[1]
d = wait(mid(k), {"checking_facts"}); json.dump(d, open(W / f"f{k}.json", "w"), indent=1)
rv = d["content"].get("review", {}); cs = rv.get("facts", {}).get("claims", [])
print(k, d["content"].get("status"), len(cs), dict(collections.Counter(c["verdict"] for c in cs)), "error", rv.get("error"))
for i, c in enumerate(cs):
    if c["verdict"] != "supported":
        print(f"\n[{i}] {c['verdict']} s{c.get('slide')}: {c.get('claim')}\n  WHY {c.get('reason') or c.get('why') or c.get('explanation')}\n  SUG {c.get('suggestion')}")
