"""leftover.py <k> <regex>: print every text in a deck (outside review) matching the regex."""
import re, sys
from pipe import call, mid
k, rx = sys.argv[1], re.compile(sys.argv[2], re.I)
st, it = call("GET", f"/media/by-id/{mid(k)}"); c = it["content"]; c.pop("review", None); c.pop("final_video_url", None)
def walk(x, p):
    if isinstance(x, str):
        for m in rx.finditer(x): print(p, "|", x[max(0, m.start()-50):m.end()+50].replace("\n", " "))
    elif isinstance(x, list): [walk(v, f"{p}[{i}]") for i, v in enumerate(x)]
    elif isinstance(x, dict): [walk(v, f"{p}.{kk}") for kk, v in x.items()]
walk(c, k)
