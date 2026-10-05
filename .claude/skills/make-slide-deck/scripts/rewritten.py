"""rewritten.py <k>... : wait for each rewrite, save work/g<k>.json, print the narration and lint it."""
import json, sys
from pipe import W, call, mid, wait
from lint import lint, narration
for k in sys.argv[1:]:
    wait(mid(k), {"writing_script"})
    st, item = call("GET", f"/media/by-id/{mid(k)}"); json.dump(item, open(W / f"g{k}.json", "w"), indent=1)
    print(f"######## {k}")
    for i, parts in enumerate(narration(item["content"]), 1): print(f"[{i}] " + " | ".join(parts))
    lint(k, item["content"])
