"""build.py <spec.py> <deck.json> : build a deck JSON from a compact spec module (TITLE, SPECIALTY, ABOUT, SLIDES)."""
import json, sys, importlib.util
spec_path, out = sys.argv[1], sys.argv[2]
s = importlib.util.spec_from_file_location("spec", spec_path); m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
slides = []
for i, sl in enumerate(m.SLIDES, 1):
    title, img, bullets, highlights, notes = sl[:5]
    pause = len(sl) > 5 and sl[5] == "pause"
    edge = i == 1 or i == len(m.SLIDES)
    slides.append({
        "title": title,
        "layout": "text_image_right" if bullets else "text_only",
        "bullets": bullets or None,
        "highlights": highlights or [],
        "source_notes": notes,
        "explanation": notes if edge else None,
        "has_pause": pause,
        "refs": [],
        "position": i,
        "id": f"slide_{i:04d}",
        "image_urls": [f"https://osceguide-platform.s3.eu-west-2.amazonaws.com/teaching_videos/sca/pictures/{img}.jpg"],
    })
deck = {"title": m.TITLE, "topic": m.TITLE, "specialty": m.SPECIALTY, "app_type": "sca",
        "about": m.ABOUT, "slides": slides, "references": [], "slides_count": len(slides)}
json.dump(deck, open(out, "w"), indent=2, ensure_ascii=False)
words = sum(len(x["source_notes"].split()) for x in slides)
print(out, len(slides), "slides", words, "words")
