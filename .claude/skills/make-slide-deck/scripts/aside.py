"""aside.py <k>... start | merge : put Ben's asides back into a voiced deck while reusing most of its audio.

start: saves the deck's voiced narration to work/old<k>.json and asks for a full rewrite.
merge: once rewritten, keeps the old narration except each slide's new intro (slide 1 stays, so the
opener style is kept), any new bullet line that carries an [audio tag], and the new framing. Unchanged
lines keep their exact text, so voicing reuses their audio. Prints every new line for review; then chk.sh.
"""
import json, re, sys
from pipe import W, call, mid, patch, wait
from lint import lint
TAG = re.compile(r"\[[^\]]*\]")
*ks, mode = sys.argv[1:]
for k in ks:
    if mode == "start":
        st, item = call("GET", f"/media/by-id/{mid(k)}"); c = item["content"]
        json.dump({"slides": [s.get("narration") for s in c["slides"]], "presentation": c.get("presentation")},
                  open(W / f"old{k}.json", "w"), ensure_ascii=False)
        print(k, *call("POST", f"/media/{mid(k)}/write-script", {"rewrite": True})[:1])
        continue
    item = wait(mid(k), {"writing_script"}); c = item["content"]; c.pop("status", None)
    old = json.load(open(W / f"old{k}.json")); new_lines = []
    assert len(old["slides"]) == len(c["slides"]), "slide count changed"
    for i, (s, o) in enumerate(zip(c["slides"], old["slides"]), 1):
        n = s["narration"]
        if i == 1: s["narration"] = o; continue
        items = o["items"]
        if len(n["items"]) == len(items):
            items = [b if TAG.search(b) else a for a, b in zip(items, n["items"])]
        m = {**o, "intro": n["intro"], "items": items}
        new_lines += [(i, x) for x in [m["intro"], *items] if x not in [o["intro"], *o["items"]]]
        s["narration"] = m
        s["speaker_notes"] = "\n\n".join(" ".join(TAG.sub(" ", x).split()) for x in [m["intro"], *items])
    print(k, "merge", patch(item, c))
    json.dump(c, open(W / f"want{k}.json", "w"), ensure_ascii=False)
    print(f"######## {k}: {len(new_lines)} new lines")
    for i, x in new_lines: print(f"[{i}] {x}")
    p = c.get("presentation") or {}
    for sec in p.get("sections") or []: print("  §", sec.get("line"))
    for key in ("recap_intro", "signoff"): print(f"  {key}:", p.get(key))
    lint(k, c)
