import json, re, sys, time, io, urllib.request
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from commons import get, UA
from PIL import Image
DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../../../api/app/features/media_production/assets/slides/images/")
PICKS = dict(x.split("=",1) for x in sys.argv[1:])
credits_path = DIR + "CREDITS.json"
credits = json.load(open(credits_path))
for name, title in PICKS.items():
    if name in credits:
        print("exists", name); continue
    d = get({"action": "query", "titles": title, "prop": "imageinfo", "iiprop": "url|extmetadata", "iiurlwidth": 1280})
    page = next(iter(d["query"]["pages"].values()))
    ii = page["imageinfo"][0]; m = ii["extmetadata"]
    url = ii.get("thumburl") or ii["url"]
    for i in range(5):
        try:
            data = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read(); break
        except urllib.error.HTTPError as e:
            if e.code != 429: raise
            time.sleep(15 * (i + 1))
    img = Image.open(io.BytesIO(data)).convert("RGB")
    img.save(DIR + name, "JPEG", quality=88)
    credits[name] = {
        "author": re.sub("<[^>]+>", "", m.get("Artist", {}).get("value", "")).strip() or "Unknown",
        "licence": m.get("LicenseShortName", {}).get("value", ""),
        "source": "https://commons.wikimedia.org/wiki/" + title.replace(" ", "_"),
    }
    print("saved", name, img.size, credits[name]["licence"])
    time.sleep(3)
json.dump(credits, open(credits_path, "w"), indent=2, ensure_ascii=False)
open(credits_path, "a").write("\n")
