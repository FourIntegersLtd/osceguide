"""respin.py <k> show | <k> <respin.json>... | <k> keep : change a voiced deck's scenario without touching its teaching.

show: prints each slide's title, bullets, highlights and narration.
respin.json: {"title": ..., "about": ..., "slides": {"<n>": {"title", "img", "bullets", "highlights",
"intro", "items"}}, "insert": {"<n>": [slide, ...]}, "edits": [[old,new],...]}, every key optional; a slide
with only "img" changes its picture. A listed slide is replaced whole (items: one spoken line per bullet).
"insert" adds new slides (same keys, "img" required) after slide n of the deck as given, copying that
slide's layout, and moves the section cards after it along. Edits then apply to every
text field of every slide, the presentation, title and about; each must hit at least once. Several
files apply in order, starting from the deck as last voiced (work/v<k>.json). The result is saved as
work/want<k>.json and to the item. Unchanged lines keep their exact text, so voicing reuses their audio.
keep: the script check rewrites every slide whose source changed, and the framing. Once it has, this
puts back the narration and framing from want<k>.json (as repl.py fixes a rewrite); then chk.sh again.
"""
import json, re, sys
from pipe import W, call, mid, wait
from lint import lint, narration

LAYOUTS = ("text_image_right", "text_image_left")  # list slides with a picture
DEFAULT_LAYOUT = LAYOUTS[0]
PIC = "https://osceguide-platform.s3.eu-west-2.amazonaws.com/teaching_videos/sca/pictures/{}.jpg"
k = sys.argv[1]
st, item = call("GET", f"/media/by-id/{mid(k)}")


def save(c):
    st, r = call("PATCH", f"/media/{item['id']}", {"title": c["title"], "summary": c.get("about") or item["summary"], "content": c})
    print(st, r if st >= 300 else r["status"])
    st, fresh = call("GET", f"/media/by-id/{mid(k)}"); lint(k, fresh["content"])


def spoken(label, bullets, new):
    """The fields a slide's spoken lines fill, shared by a replaced and an inserted slide; and the lines."""
    intro, items = new["intro"], new.get("items", [])
    assert len(items) == len(bullets), f"{label}: {len(items)} items for {len(bullets)} bullets"
    assert all(h in " ".join(bullets) for h in new.get("highlights", [])), f"{label}: highlight not in bullets"
    said = [intro, *items]
    fields = {"narration": {"intro": intro, "items": items, "callouts": [None] * len(items)},
              "speaker_notes": "\n\n".join(said), "bullet_audio_segments": []}  # segments rebuilt when voiced
    return fields, said


def insert(c, after, new_slides):
    template, used = c["slides"][after - 1], [int(s["id"].rsplit("_", 1)[1]) for s in c["slides"]]
    added = []
    for number, new in enumerate(new_slides, max(used) + 1):
        fields, _ = spoken(f"new slide {new['title']}", new["bullets"], new)
        s = json.loads(json.dumps(template))
        s.update(fields, id=f"slide_{number:04d}", title=new["title"], bullets=new["bullets"], highlights=new.get("highlights", []),
                 image_urls=[PIC.format(new["img"])], explanation=None,
                 layout=template["layout"] if template.get("layout") in LAYOUTS else DEFAULT_LAYOUT,
                 has_pause=False, pause_duration=None, audio_url=None)
        added.append(s)
    c["slides"][after:after] = added
    for position, s in enumerate(c["slides"], 1):
        s["position"] = position
    for section in c["presentation"]["sections"]:
        if section["before"] > after:
            section["before"] += len(added)
    if "slides_count" in c:
        c["slides_count"] = len(c["slides"])


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
        fields, said = spoken(f"slide {n}", bullets, new)
        s.update(fields, title=new.get("title", s["title"]), bullets=bullets or None, highlights=new.get("highlights", s.get("highlights") if not bullets else []))
        if s.get("explanation"): s["explanation"] = " ".join(said)
    # n is a slide number of the deck as given: insert from the back so earlier numbers still hold.
    for after, new_slides in sorted(spec.get("insert", {}).items(), key=lambda pair: -int(pair[0])):
        insert(c, int(after), new_slides)
    hits = {o: 0 for o, _ in edits}
    def fix(x):
        if isinstance(x, str):
            for o, n in edits:
                if o in x: hits[o] += 1; x = x.replace(o, n)
            return re.sub(r" +([.,;:!?])", r"\1", x)
        if isinstance(x, list): return [fix(v) for v in x]
        if isinstance(x, dict): return {kk: fix(v) for kk, v in x.items()}
        return x
    if edits or spec.get("slides"):  # an insert-only spec leaves every existing text as it is
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
    said_before = {s["id"]: s["narration"] for s in c["slides"]}
    for path in sys.argv[2:]: apply(c, json.load(open(path)))
    # No stale scenario left in notes; unchanged slides keep theirs, and a new slide (no earlier entry) gets its own.
    for s, parts in zip(c["slides"], narration(c)):
        if said_before.get(s["id"]) != s["narration"]: s["source_notes"] = " ".join(parts)
    json.dump(c, open(W / f"want{k}.json", "w"), ensure_ascii=False)
    save(c)
