import json, re, sys, io
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../commons-images/scripts"))
from commons_images import api_get, download
from PIL import Image
DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../../../api/app/features/media_production/assets/slides/images/")
PICKS = dict(x.split("=",1) for x in sys.argv[1:])
credits_path = DIR + "CREDITS.json"
credits = json.load(open(credits_path))
for name, title in PICKS.items():
    if name in credits:
        print("exists", name); continue
    d = api_get({"action": "query", "titles": title, "prop": "imageinfo", "iiprop": "url|extmetadata", "iiurlwidth": 1280})
    page = d["query"]["pages"][0]
    ii = page["imageinfo"][0]; m = ii["extmetadata"]
    url = ii.get("thumburl") or ii["url"]
    img = Image.open(io.BytesIO(download(url))).convert("RGB")
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
