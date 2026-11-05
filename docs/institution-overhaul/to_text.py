"""Render each design board (boards/*.dc.html) to plain text in design/<Board>.md:
one section per tab and per dialog, every word as drawn. Run: python3 to_text.py"""
import re, json, os, html
from html.parser import HTMLParser

BLOCK = {"div","p","li","ul","ol","h1","h2","h3","tr","section","details","summary","main","label","textarea","select","option"}

class R(HTMLParser):
    def __init__(s):
        super().__init__(); s.out=[]; s.href=[]; s.skip=0; s.sel=False
    def handle_starttag(s,t,a):
        a=dict(a)
        if t in("style","script"): s.skip+=1; return
        if t in BLOCK: s.out.append("\n")
        if t=="li": s.out.append("- ")
        if t in("h1","h2","h3"): s.out.append("#"*int(t[1])+" ")
        if t=="summary": s.out.append("▸ ")
        if t=="button": s.out.append("[")
        if t=="a": s.out.append("["); s.href.append(a.get("href",""))
        if t=="input":
            ty=a.get("type","text"); v=a.get("placeholder") or a.get("value") or a.get("aria-label") or ""
            if ty=="checkbox": s.out.append("[%s] "%("x" if "checked" in a else " "))
            elif ty=="radio": s.out.append("(%s) "%("•" if "checked" in a else " "))
            else: s.out.append("‹input: %s›"%v)
        if t=="textarea": s.out.append("‹textarea: %s›"%(a.get("placeholder") or ""))
        if t=="select": s.out.append("‹select: "); s.sel=True
        if t=="option" and s.sel: s.out.append(("*" if "selected" in a else "")+"")
        if t=="span" and "chip" in a.get("class",""): s.out.append("(")
        if t=="code": s.out.append("`")
    def handle_endtag(s,t):
        if t in("style","script"): s.skip-=1; return
        if t=="button": s.out.append("] ")
        if t=="a":
            h=s.href.pop() if s.href else ""
            s.out.append("](%s) "%h if h and h!="#" else "] ")
        if t=="select": s.out.append("›"); s.sel=False
        if t=="option" and s.sel: s.out.append(" | ")
        if t=="code": s.out.append("`")
        if t in BLOCK: s.out.append("\n")
    def handle_data(s,d):
        if s.skip: return
        s.out.append(d)
    def text(s):
        t="".join(s.out)
        t=re.sub(r"\(\s*([^()\n]*?)\s*(?=\n|$)", lambda m:m.group(0), t)
        t=html.unescape(t); t=re.sub(r"[ \t]+\n","\n",t); t=re.sub(r"\n{3,}","\n\n",t)
        return re.sub(r"[ \t]{2,}"," ",t).strip()

def render(h):
    r=R(); r.feed(h); return r.text()

def balanced(s,start):
    """index after the closing tag of the sc-if that begins at start"""
    depth=0
    for m in re.finditer(r"<(/?)sc-if\b",s[start:]):
        depth+= -1 if m.group(1) else 1
        if depth==0: return start+m.end()+s[start+m.end():].find(">")+1
    return len(s)

def board(path):
    s=open(path).read()
    m=re.search(r"const L = (\[.*?\]);",s); tabs=json.loads(m.group(1)) if m else []
    title=re.search(r"<title>(.*?)</title>",s); title=title.group(1) if title else os.path.basename(path)
    body=s[s.find("<x-dc>"):s.find("</x-dc>")]
    body=re.sub(r"<helmet>.*?</helmet>","",body,flags=re.S)
    body=re.sub(r'<script type="text/x-dc".*?</script>',"",body,flags=re.S)
    parts=[]; # (kind,name,html)
    out=[]; pos=0
    for m in re.finditer(r'<sc-if value="\{\{\s*(p\d+|d_\w+)\s*\}\}"[^>]*>',body):
        if m.start()<pos: continue
        end=balanced(body,m.start())
        out.append(("shared",None,body[pos:m.start()])); pos=end
        inner=body[m.end():end-len("</sc-if>")]
        key=m.group(1)
        out.append(("tab",int(key[1:]),inner) if key[0]=="p" else ("dialog",key[2:],inner))
    out.append(("shared",None,body[pos:]))
    md=["# %s"%title,"","Source: `boards/%s`. Tabs are screens or states to build; dialogs are `Modal`/`ConfirmModal`."%os.path.basename(path),""]
    if tabs: md+=["Tabs: "+" | ".join("%d. %s"%(i+1,t) for i,t in enumerate(tabs)),""]
    shared="\n".join(render(h) for k,_,h in out if k=="shared" and h.strip())
    md+=["## Always on screen (menu, header, notes, build spec)","",shared,""]
    for k,n,h in out:
        if k=="tab": md+=["## Tab %d: %s"%(n+1,tabs[n] if n<len(tabs) else n),"",render(h),""]
    for k,n,h in out:
        if k=="dialog": md+=["## Dialog: %s"%n,"",render(h),""]
    return "\n".join(md)

os.makedirs("design",exist_ok=True)
idx=["# Design: one file per board","","Open the file for the screen you are building. Read the matching `boards/*.dc.html` only if a word is unclear.",""]
c=json.load(open("boards/canvas.json"))
for f in c["order"]:
    n=f.replace(".dc.html","")
    open("design/%s.md"%n,"w").write(board("boards/"+f))
    idx.append("%d. [%s](%s.md): %s"%(c["order"].index(f)+1,n,n,c["boards"][f]["title"]))
open("design/README.md","w").write("\n".join(idx)+"\n")
print(len(c["order"]),"boards")
