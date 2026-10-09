"""vary.py <out_dir> : spread the stock pictures across the live decks, so a learner who watches several
decks in a row (or one deck through) does not see the same few pictures again and again.

Every picture in a pool can stand in for any other. Decks are taken in number order; each slide whose
picture is in a pool gets the pool picture used longest ago that this deck does not already show.
Writes <out_dir>/<slide_id>.json (every slide's image_urls, for refilm.py) for each deck that changes.
"""

import json
import sys
from pathlib import Path

from pipe import R, W

PUBLISHED = R / "published"
PREFIX = "https://osceguide.s3.eu-west-2.amazonaws.com/teaching_videos/v2/pictures/"

POOLS = [
    "telephone_handset phone_call_centre phone_candlestick phone_cordless_modem phone_cordless_panasonic"
    " phone_cordless_vtech phone_hands_coffee_smartphone phone_laptop_desk phone_rotary_grey"
    " phone_rotary_vintage_bw phone_smartphone_hand_black phone_smartphone_use",
    "consultation listening explaining counselling talk_anatomy_torso talk_books_shelf talk_coffee_notebooks"
    " talk_compass talk_empty_bench talk_hands_mug talk_hiking_signpost talk_jigsaw_red talk_leaflet_stands"
    " talk_lightbulb talk_man_writing talk_notebook_handwriting talk_notepad_laptop talk_pen_notes"
    " talk_question_mark talk_sofa_grey talk_stationery_desk talk_tea_for_two talk_waiting_room_clinic",
    "ambulance urgent_street_ambulance urgent_hospital_bay_aerial urgent_response_car urgent_welsh_ambulance"
    " urgent_ae_entrance",
    "tablets blister_pack meds_capsule_jar meds_mixed_tablets meds_pill_organiser",
    "calendar alarm_clock time_clock_face time_hourglasses time_diary_page",
    "bloods lab_tube_rack lab_vacutainer lab_analyser lab_centrifuge",
    "pharmacy chemist_shopfront chemist_dispensary",
    "padlock privacy_chain_padlock",
    "car_keys driving_alto_dashboard",
    "office_desk work_top_workspace work_laptop_neat_desk",
    "stethoscope exam_bp_cuff exam_stethoscope_desk",
]


def live_decks() -> list[tuple[int, str]]:
    """The live slide id of each deck number. pub.sh appends "<k> <deck> <slide_id> [replaced <date>]"."""
    live: dict[int, str] = {}
    for line in (W / "published.txt").read_text().splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[2].startswith("slide_"):
            live[int(parts[0])] = parts[2]
    return sorted(live.items())


def main() -> None:
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    pools = [pool.split() for pool in POOLS]
    pool_of = {name: pool for pool in pools for name in pool}
    if len(pool_of) != sum(map(len, pools)):
        sys.exit("a picture is in two pools")
    last_used: dict[str, int] = {}
    clock = 0
    changed = 0
    for _, sid in live_decks():
        # A deck refilm.py already gave new pictures is planned from its state before that.
        before = PUBLISHED / f"{sid}.before-pictures.json"
        source = before if before.exists() else PUBLISHED / f"{sid}.json"
        slides = json.loads(source.read_text(encoding="utf-8"))["slides"]
        shown = {Path(url).stem for slide in slides for url in slide.get("image_urls") or [] if Path(url).stem not in pool_of}
        images = []
        for slide in slides:
            urls = []
            for url in slide.get("image_urls") or []:
                name = Path(url).stem
                if name in pool_of:
                    free = [n for n in pool_of[name] if n not in shown] or [name]
                    # Least recently used; on a tie, keep the picture the slide already has.
                    name = min(free, key=lambda n: (last_used.get(n, -1), n != name))
                    clock += 1
                    last_used[name] = clock
                shown.add(name)
                urls.append(PREFIX + name + ".jpg")
            images.append(urls)
        if images != [slide.get("image_urls") or [] for slide in slides]:
            changed += 1
            (out / f"{sid}.json").write_text(json.dumps(images), encoding="utf-8")
    print(f"{changed} decks change")


if __name__ == "__main__":
    main()
