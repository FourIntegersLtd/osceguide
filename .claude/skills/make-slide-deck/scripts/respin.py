"""respin.py <k> show | <k> <respin.json>... | <k> keep : change a voiced deck's scenario without touching its teaching.

show: prints each slide's title, bullets, highlights and narration.
respin.json: {"title": ..., "about": ..., "slides": {"<n>": {"title", "img", "bullets", "highlights",
"intro", "items"}}, "edits": [[old,new],...]}, every key optional; a slide with only "img" changes its
picture. A listed slide is replaced whole (items: one spoken line per bullet). Edits then apply to every
text field of every slide, the presentation, title and about; each must hit at least once. Several
files apply in order, starting from the deck as last voiced (work/v<k>.json). The result is saved as
work/want<k>.json and to the item. Unchanged lines keep their exact text, so voicing reuses their audio.
keep: the script check rewrites every slide whose source changed, and the framing. Once it has, this
puts back the narration and framing from want<k>.json (as repl.py fixes a rewrite); then chk.sh again.
"""
import json, re, sys
from pipe import W, call, mid, wait
from lint import lint, narration

PIC = "https://osceguide.s3.eu-west-2.amazonaws.com/teaching_videos/v2/pictures/{}.jpg"
k = sys.argv[1]
st, item = call("GET", f"/media/by-id/{mid(k)}")


def save(c):
    st, r = call("PATCH", f"/media/{item['id']}", {"title": c["title"], "summary": c.get("about") or item["summary"], "content": c})
    print(st, r if st >= 300 else r["status"])
    st, fresh = call("GET", f"/media/by-id/{mid(k)}"); lint(k, fresh["content"])


def apply(c, spec):
    edits = spec.get("edits", [])
    for key in ("title", "about"):
        if key in spec: c[key] = spec[key]
    if "title" in spec: c["topic"] = spec["title"]
    if "presentation" in spec: c["presentation"] = {**c["presentation"], **spec["presentation"]}  # framing for an unvoiced deck
    for n, new in spec.get("slides", {}).items():
        s = c["slides"][int(n) - 1]
        if "img" in new: s["image_urls"] = [PIC.format(new["img"])]
        if "intro" not in new: continue  # picture only
        bullets = new.get("bullets", s.get("bullets")) or []
        intro, items = new["intro"], new.get("items", [])
        assert len(items) == len(bullets), f"slide {n}: {len(items)} items for {len(bullets)} bullets"
        assert all(h in " ".join(bullets) for h in new.get("highlights", [])), f"slide {n}: highlight not in bullets"
        said = [intro, *items]
        s.update(title=new.get("title", s["title"]), bullets=bullets or None, highlights=new.get("highlights", s.get("highlights") if not bullets else []),
                 narration={"intro": intro, "items": items, "callouts": [None] * len(items)}, speaker_notes="\n\n".join(said))
        s["bullet_audio_segments"] = []  # rebuilt when the deck is voiced
        if s.get("explanation"): s["explanation"] = " ".join(said)
    hits = {o: 0 for o, _ in edits}
    def fix(x):
        if isinstance(x, str):
            for o, n in edits:
                if o in x: hits[o] += 1; x = x.replace(o, n)
            return re.sub(r" +([.,;:!?])", r"\1", x)
        if isinstance(x, list): return [fix(v) for v in x]
        if isinstance(x, dict): return {kk: fix(v) for kk, v in x.items()}
        return x
    c["slides"] = fix(c["slides"]); c["presentation"] = fix(c["presentation"])
    for key in ("title", "topic", "about"): c[key] = fix(c.get(key))
    miss = [o[:70] for o, h in hits.items() if h == 0]
    print(k, "edits", len(edits), "missed", len(miss), *miss, sep="\n  " if miss else " ")
    if miss: raise SystemExit("nothing saved: fix the missed edits")


if sys.argv[2] == "show":
    c = item["content"]; print("TITLE:", c["title"]); print("ABOUT:", c.get("about"))
    for i, (s, parts) in enumerate(zip(c["slides"], narration(c)), 1):
        print(f"[{i}] {s['title']} | img={s['image_urls'][0].rsplit('/', 1)[-1]}")
        for b in s.get("bullets") or []: print("   •", b)
        if s.get("highlights"): print("   hl:", s["highlights"])
        print("   >", " | ".join(parts))
elif sys.argv[2] == "keep":
    item = wait(mid(k), {"writing_script"}); c = item["content"]; c.pop("status", None)
    want = json.load(open(W / f"want{k}.json"))
    assert len(want["slides"]) == len(c["slides"]), "slide count changed"
    for s, w in zip(c["slides"], want["slides"]):
        s["narration"], s["speaker_notes"] = w["narration"], w["speaker_notes"]
    c["presentation"] = want["presentation"]
    save(c)
else:
    c = json.load(open(W / f"v{k}.json"))["content"]; c.pop("status", None)
    c["review"] = item["content"].get("review", c.get("review"))
    for path in sys.argv[2:]: apply(c, json.load(open(path)))
    for s, parts in zip(c["slides"], narration(c)): s["source_notes"] = " ".join(parts)  # no stale scenario left in notes
    json.dump(c, open(W / f"want{k}.json", "w"), ensure_ascii=False)
    save(c)
