"""lint.py <k>... : re-read the draft and flag a 'Welcome' opener, stray spacing, ellipses and lines that break a telephone setting (asides and audio tags stay)."""
import re, sys
W_ = re.compile(r"\b(video|videos|in the chair|in clinic today|face to face)\b", re.I)
def walk(x, out):
    if isinstance(x, str): out.append(x)
    elif isinstance(x, dict): [walk(v, out) for v in x.values()]
    elif isinstance(x, list): [walk(v, out) for v in x]
    return out
def narration(c):
    return [[x for x in walk(s.get("narration"), []) if len(x) > 20] for s in c["slides"]]
def lint(k, c):
    slides = narration(c); flags = []
    if slides and re.search(r"\bwelcome\b", " ".join(slides[0]), re.I): flags.append("slide 1 opens with 'Welcome'")
    for i, parts in enumerate(slides, 1):
        for x in parts:
            for pat, why in ((r" [,.;:]", "space before punctuation"), (r"\.\.\.|…", "ellipsis")):
                if re.search(pat, x): flags.append(f"s{i} {why}: {x[:120]}")
            for sent in re.split(r"(?<=[.!?])\s+", x):
                if W_.search(sent): flags.append(f"s{i} setting?: {sent[:160]}")
    print(f"LINT {k}: {len(flags)} flags"); [print("  -", f) for f in flags]
    return flags
if __name__ == "__main__":
    from pipe import call, mid
    for k in sys.argv[1:]:
        st, item = call("GET", f"/media/by-id/{mid(k)}"); lint(k, item["content"])
