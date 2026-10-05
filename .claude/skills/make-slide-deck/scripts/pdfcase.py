"""pdfcase.py <pdf> <case#>... : save each case's text, from its 'Station N -' header to the next header, to work/cases/<n>.txt."""
import re, sys
from pypdf import PdfReader
from pipe import W
pdf, wants = sys.argv[1], sys.argv[2:]
(W / "cases").mkdir(exist_ok=True)
cache = W / "cases" / "_all.txt"
if not cache.exists():
    cache.write_text("\n".join(p.extract_text() or "" for p in PdfReader(pdf).pages))
txt = cache.read_text()
for n in wants:
    hits = [m.start() for m in re.finditer(rf"\n\s*Station\s*{n}\s*[-–—]", txt)]
    if not hits: print(n, "not found"); continue
    a = hits[-1]  # the case itself, not its index entry
    m = re.search(r"\n\s*Station\s*\d+\s*[-–—]", txt[a + 50:])
    body = txt[a: a + 50 + m.start()] if m else txt[a:]
    (W / "cases" / f"{n}.txt").write_text(body); print(n, len(body))
