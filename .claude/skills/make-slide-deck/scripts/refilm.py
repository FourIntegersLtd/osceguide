"""refilm.py <slide_id> <images.json> [--check] [--upload] (from api/, via poetry, PYTHONPATH=.)

Gives a published deck new slide pictures and nothing else: no voicing, no rewriting. The published
video's soundtrack is copied as it is, and so is every frame where no changed picture shows. On a frame
of a slide whose picture changed (or the crossfade out of it), only the picture boxes are drawn again,
from the stored timings, and pasted over the published frame. `images.json` lists every slide's
`image_urls`, in slide order. The deck is read from <slide_id>.before-pictures.json when an earlier run
left one, so a deck can be filmed again from its first published state.

--check   also redraw slides whose pictures did not change and compare them with the published frames,
          proving the timings were rebuilt exactly (prints the worst difference).
--upload  upload the new video and write slide-scripts/published/<slide_id>.json with the new pictures
          and video url (the old file is kept as <slide_id>.before-pictures.json).
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import urllib.request
from bisect import bisect_right
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageStat

from app.core.settings import get_settings
from app.features.media_production import slide_av as av
from app.features.media_production.podcast_tts import ffmpeg_binary
from app.features.media_production.s3 import s3_client
from app.features.media_production.slide_pictures import fetch_pictures
from app.features.media_production.slide_scenes import COUNTDOWN_SECONDS, HEIGHT, WIDTH, Painter
from app.features.media_production.slide_voice import TAIL_PAUSE_MS
from pipe import R, W

PUBLISHED = R / "published"
FRAME = WIDTH * HEIGHT * 3
TIMING_SLACK = 0.05  # seconds a rebuilt scene may differ from its stored length
PICTURE_MARGIN = 8  # pixels around a picture box that are drawn again with it (its rounded corners)
SAMPLE_EVERY = 12  # frames between two comparisons with the published video
WORST_ALLOWED = 6  # mean difference out of 255; encoding noise alone is about 2


def _timed(takes: list[av._Take], total: float) -> None:
    """Puts every scene back where the published video has it, from the timings stored on its slides.

    Section cards fill the gap between two slides; the recap and sign-off (no pictures) only need their
    start, for the crossfade out of the last slide."""
    clock = 0.0
    for index, take in enumerate(takes):
        slide = take.slide
        take.start = clock
        take.events = [(0.0, len(take.scene.rows), 0)] if take.rows_from_start else [(0.0, 0, -1)]
        take.line_starts, take.captions = [], []
        if slide is not None:
            take.start = slide["start_time"]
            take.duration = slide["end_time"] - slide["start_time"]
            seconds = [slide["intro_duration"]] + [seg["duration"] for seg in slide["bullet_audio_segments"]]
        elif index + 1 < len(takes) and takes[index + 1].slide is not None:
            take.duration = takes[index + 1].slide["start_time"] - clock
            seconds = [take.duration - av.LEAD_IN - av.SCENE_TAIL]
        else:
            take.duration = total - clock
            clock = total
            continue
        local = av.LEAD_IN
        for (text, row), length in zip(take.lines, seconds, strict=True):
            if row is not None:
                take.events.append((local - av.ROW_LEAD, row + 1, row))
            take.line_starts.append(local)
            take.captions += av._caption_chunks(text, local, length - TAIL_PAUSE_MS / 1000)
            local += length
        if take.countdown:
            take.countdown_at = local
            local += COUNTDOWN_SECONDS
        if abs(local + av.SCENE_TAIL - take.duration) > TIMING_SLACK:
            sys.exit(f"take {index}: rebuilt {local + av.SCENE_TAIL:.2f}s, stored {take.duration:.2f}s")
        clock = take.start + take.duration


def _takes(content: dict, deck_dir: Path, total: float) -> list[av._Take]:
    shutil.rmtree(deck_dir, ignore_errors=True)
    deck_dir.mkdir(parents=True)
    slides = [dict(slide) for slide in content["slides"]]
    # A picture that cannot be fetched is left out, as it was when the published video was drawn;
    # --check proves the unchanged slides still match.
    fetch_pictures(get_settings(), slides, deck_dir)
    takes = av._storyboard(Painter(), {**content, "slides": slides}, content["presentation"], deck_dir)
    _timed(takes, total)
    return takes


def _where(takes: list[av._Take], starts: list[float], number: int) -> tuple[int, float]:
    moment = number / av.FPS
    index = max(0, bisect_right(starts, moment) - 1)
    return index, moment - starts[index]


def _boxes(takes: list[av._Take], indexes: set[int]) -> list[tuple[int, int, int, int]]:
    """The picture boxes of the given scenes, with their margin, as (left, top, right, bottom)."""
    return [
        (left - PICTURE_MARGIN, top - PICTURE_MARGIN, left + width + PICTURE_MARGIN, top + height + PICTURE_MARGIN)
        for index in indexes
        for _, (left, top, width, height) in takes[index].scene._images
    ]


def _difference(a: Image.Image, b: Image.Image, mask: Image.Image | None = None) -> float:
    return max(ImageStat.Stat(ImageChops.difference(a, b), mask).mean)


def _inside(boxes: list[tuple[int, int, int, int]]) -> Image.Image:
    mask = Image.new("L", (WIDTH, HEIGHT), 0)
    draw = ImageDraw.Draw(mask)
    for box in boxes:
        draw.rectangle(box, fill=255)
    return mask


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Give a published deck new slide pictures and nothing else.")
    parser.add_argument("slide_id")
    parser.add_argument("images", type=Path, help="every slide's image_urls, in slide order")
    parser.add_argument("--check", action="store_true", help="also prove the unchanged slides redraw exactly")
    parser.add_argument("--upload", action="store_true", help="upload and write the published file")
    return parser.parse_args()


def _film(
    old_video: Path, out: Path, old_takes: list[av._Take], new_takes: list[av._Take], total: float, check: bool
) -> tuple[float, str, float]:
    """Writes `out`; returns how far the old pictures, drawn again, are from the published ones (and
    where), and with --check how far the unchanged slides are."""
    starts = [take.start for take in new_takes]
    changed = {
        index
        for index, (old, new) in enumerate(zip(old_takes, new_takes, strict=True))
        if old.slide is not None and old.slide.get("image_urls") != new.slide.get("image_urls")
    }
    print(f"{len(changed)} slides get new pictures")
    decoder = subprocess.Popen(  # noqa: S603 - fixed arguments
        [ffmpeg_binary(), "-loglevel", "error", "-i", str(old_video), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        stdout=subprocess.PIPE,
    )
    encode = [ffmpeg_binary(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24"]
    encode += ["-s", f"{WIDTH}x{HEIGHT}", "-r", str(av.FPS), "-i", "-", "-i", str(old_video)]
    encode += ["-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "medium", "-crf", "20"]
    encode += ["-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", str(out)]
    encoder = subprocess.Popen(encode, stdin=subprocess.PIPE)  # noqa: S603 - fixed arguments
    assert decoder.stdout is not None and encoder.stdin is not None
    worst_picture = worst_same = 0.0
    worst_at = ""
    last = b""
    for number in range(round(total * av.FPS)):
        raw = decoder.stdout.read(FRAME)
        original = raw if len(raw) == FRAME else last
        last = original
        moment = number / av.FPS
        index, local = _where(new_takes, starts, number)
        showing = {index} & changed
        if index - 1 in changed and local < av.CROSSFADE:
            showing.add(index - 1)
        if not showing:
            if check and number % (2 * SAMPLE_EVERY) == 0 and new_takes[index].slide is not None and local > av.CROSSFADE:
                again = av._frame(old_takes, starts, total, moment)
                worst_same = max(worst_same, _difference(again, Image.frombytes("RGB", (WIDTH, HEIGHT), original)))
            encoder.stdin.write(original)
            continue
        boxes = _boxes(new_takes, showing)
        frame = Image.frombytes("RGB", (WIDTH, HEIGHT), original)
        drawn = av._frame(new_takes, starts, total, moment)
        if number % SAMPLE_EVERY == 0:
            # The old pictures drawn in the same boxes at the same moment must be what was published.
            difference = _difference(av._frame(old_takes, starts, total, moment), frame, _inside(boxes))
            if difference > worst_picture:
                worst_picture, worst_at = difference, f" (take {index} at {local:.2f}s, frame {number})"
        for box in boxes:
            frame.paste(drawn.crop(box), box[:2])
        encoder.stdin.write(frame.tobytes())
    encoder.stdin.close()
    decoder.stdout.close()
    if encoder.wait() or decoder.wait() not in (0, -13, 255):
        sys.exit("ffmpeg failed")
    return worst_picture, worst_at, worst_same


def _upload(sid: str, content: dict, new_content: dict, out: Path) -> None:
    settings = get_settings()
    topic = re.sub(r"[^a-z0-9_-]", "_", str(content["topic"]).lower())[:50]
    key = f"{av.S3_FOLDER}/{content['app_type']}/{topic}_{sid}_pictures.mp4"
    with out.open("rb") as handle:
        s3_client(settings).upload_fileobj(handle, settings.aws_s3_bucket, key, ExtraArgs={"ContentType": "video/mp4"})
    published = PUBLISHED / f"{sid}.json"
    backup = PUBLISHED / f"{sid}.before-pictures.json"
    if not backup.exists():
        shutil.copy(published, backup)
    new_content["final_video_url"] = f"https://{settings.aws_s3_bucket}.s3.{settings.aws_region}.amazonaws.com/{key}"
    staged = published.with_suffix(".json.part")
    staged.write_text(json.dumps(new_content, indent=1, ensure_ascii=False), encoding="utf-8")
    staged.replace(published)
    print(f"{sid}: uploaded {new_content['final_video_url']}")


def main() -> None:
    args = _arguments()
    sid = args.slide_id
    backup = PUBLISHED / f"{sid}.before-pictures.json"
    content = json.loads((backup if backup.exists() else PUBLISHED / f"{sid}.json").read_text(encoding="utf-8"))
    images = json.loads(args.images.read_text(encoding="utf-8"))
    if len(images) != len(content["slides"]):
        sys.exit("images.json must list every slide")
    work = W / "refilm" / sid
    work.mkdir(parents=True, exist_ok=True)
    old_video = work / "published.mp4"
    if not old_video.exists():
        urllib.request.urlretrieve(content["final_video_url"], old_video)
    total = float(content["total_duration"])

    old_takes = _takes(content, work / "old", total)
    new_content = json.loads(json.dumps(content))
    for slide, urls in zip(new_content["slides"], images, strict=True):
        slide["image_urls"] = urls
    new_takes = _takes(new_content, work / "new", total)
    out = work / "refilmed.mp4"
    worst_picture, worst_at, worst_same = _film(old_video, out, old_takes, new_takes, total, args.check)
    print(f"{sid}: old pictures redrawn {worst_picture:.2f}/255{worst_at}", end="")
    print(f", unchanged slides redrawn {worst_same:.2f}/255" if args.check else "")
    # Unchanged frames are copied, never redrawn, so only the picture boxes decide; the whole-frame
    # --check figure also counts caption timing, which the copied frames keep as published.
    if worst_picture > WORST_ALLOWED:
        sys.exit(f"{sid}: the redrawn frames do not match the published video: not uploading")
    if args.upload:
        _upload(sid, content, new_content, out)
    else:
        print("written", out)


if __name__ == "__main__":
    main()
