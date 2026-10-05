import json, sys, urllib.error, urllib.parse, urllib.request, re
UA = {"User-Agent": "OSCEGuideSlides/1.0 (https://osceguide.com)"}
import time
def get(params, tries=5):
    for i in range(tries):
        try:
            return _get(params)
        except urllib.error.HTTPError as e:
            if e.code != 429: raise
            time.sleep(10 * (i + 1))
    raise SystemExit("rate limited")
def _get(params):
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode({**params, "format": "json"})
    return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30))
def search(q, n=6):
    d = get({"action": "query", "generator": "search", "gsrsearch": f"filetype:bitmap {q}", "gsrnamespace": 6,
             "gsrlimit": n, "prop": "imageinfo", "iiprop": "url|extmetadata|size", "iiurlwidth": 1280})
    out = []
    for p in sorted((d.get("query") or {}).get("pages", {}).values(), key=lambda p: p.get("index", 0)):
        ii = p["imageinfo"][0]; m = ii.get("extmetadata", {})
        lic = m.get("LicenseShortName", {}).get("value", "")
        art = re.sub("<[^>]+>", "", m.get("Artist", {}).get("value", "")).strip()[:60]
        out.append((p["title"], lic, art, ii.get("width"), ii.get("height")))
    return out
if __name__ == "__main__":
    for q in sys.argv[1:]:
        print("##", q)
        for r in search(q): print("  ", r)
        time.sleep(4)
