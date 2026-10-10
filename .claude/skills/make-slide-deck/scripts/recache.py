"""recache.py <k>... [--compare] (from api/, via poetry, PYTHONPATH=.)

Puts a published deck's voiced lines back where the api looks for them, so voicing it again pays only
for lines that changed. The api keeps lines in a temp folder that a restart or clean-up empties; this
cuts every line out of the published video's soundtrack instead, from the timings stored on its slides.
The recap and sign-off have no stored timings: their line starts come from the frames, where each
takeaway row appears (ROW_LEAD before its line) and the sign-off card fades in.

Lines already in the folder are kept. Any `slide-scripts/voice-cache/<media_id>/` lines (real takes,
saved earlier) are copied in first. --compare cuts the lines into a scratch folder and prints how far
their lengths are from those real takes, proving the cuts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
import urllib.request
import wave
from pathlib import Path

from pydub import AudioSegment

from app.features.media_production import slide_av as av
from app.features.media_production.podcast_tts import ffmpeg_binary
from app.features.media_production.slide_scenes import HEIGHT, WIDTH
from app.features.media_production.slide_voice import SAMPLE_RATE
from pipe import R, W, live_decks, mid
from refilm import _takes

VOICE = Path(tempfile.gettempdir()) / "media_av_voice"
SMALL = (WIDTH // 4, HEIGHT // 4)
ROWS_BOTTOM = 0.75  # captions sit below this share of the frame; row changes are looked for above it
TAIL_CHECK = 0.25  # seconds at the end of every cut that must be the silence the api adds after a line
QUIET_DBFS = -40.0
FRAME_JUMP = 0.12  # mean grey difference (of 255) between two frames that marks a row or card appearing
ROW_GAP = 1.0  # seconds; a row fading in can change the frame twice, and no recap line is this short


def _name(text: str) -> str:
    return f"{hashlib.sha256(text.strip().encode()).hexdigest()[:32]}.wav"


def _soundtrack(video: Path, out: Path) -> bytes:
    if not out.exists():
        subprocess.run(  # noqa: S603 - fixed arguments
            [ffmpeg_binary(), "-y", "-loglevel", "error", "-i", str(video), "-ac", "2", "-ar", str(SAMPLE_RATE),
             "-sample_fmt", "s16", str(out)],
            check=True,
        )
    with wave.open(str(out), "rb") as track:
        return track.readframes(track.getnframes())


def _jumps(video: Path, start: float, end: float) -> list[float]:
    """Times (seconds into the video) where the area above the captions changes sharply."""
    height = int(SMALL[1] * ROWS_BOTTOM)
    raw = subprocess.run(  # noqa: S603 - fixed arguments
        [ffmpeg_binary(), "-loglevel", "error", "-ss", f"{start:.3f}", "-t", f"{end - start:.3f}", "-i", str(video),
         "-vf", f"scale={SMALL[0]}:{SMALL[1]},format=gray", "-f", "rawvideo", "-"],
        check=True, capture_output=True,
    ).stdout
    size = SMALL[0] * SMALL[1]
    frames = [raw[i * size : i * size + SMALL[0] * height] for i in range(len(raw) // size)]
    found, quiet = [], True
    for number in range(1, len(frames)):
        a, b = frames[number - 1], frames[number]
        jump = sum(abs(x - y) for x, y in zip(a, b, strict=True)) / len(a)
        if jump > FRAME_JUMP and quiet:
            found.append(start + (number - 1) / av.FPS)
        quiet = jump <= FRAME_JUMP
    return found


def _ending(takes: list[av._Take], video: Path, total: float) -> list[tuple[str, float, float]]:
    """(text, start, length) of the recap's and sign-off's lines, from where their rows and card appear."""
    recap, goodbye = takes[-2], takes[-1]
    begin = recap.start
    jumps: list[float] = []
    for t in _jumps(video, begin, total):
        if t > begin + 1.0 and (not jumps or t - jumps[-1] >= ROW_GAP):  # past the crossfade in, one per row
            jumps.append(t)
    rows = len(recap.lines) - 1
    if len(jumps) < rows + 1:
        raise SystemExit(f"recap: found {len(jumps)} changes, need {rows + 1}")
    starts = [begin + av.LEAD_IN] + [t + av.ROW_LEAD for t in jumps[:rows]]
    card = jumps[rows]
    ends = starts[1:] + [card - av.SCENE_TAIL]
    lines = [(text, s, e - s) for (text, _), s, e in zip(recap.lines, starts, ends, strict=True)]
    signoff = goodbye.lines[0][0]
    return [*lines, (signoff, card + av.LEAD_IN, total - av.SCENE_TAIL - card - av.LEAD_IN)]


def _lines(content: dict, work: Path, video: Path) -> list[tuple[str, float, float]]:
    total = float(content["total_duration"])
    takes = _takes(content, work / "takes", total)
    found = []
    for take in takes[:-2]:
        lengths = [b - a for a, b in zip(take.line_starts, take.line_starts[1:])]
        last_end = take.duration - av.SCENE_TAIL - (av.COUNTDOWN_SECONDS if take.countdown else 0)
        lengths.append(last_end - take.line_starts[-1])
        found += [(text, take.start + s, n) for (text, _), s, n in zip(take.lines, take.line_starts, lengths, strict=True)]
    return found + _ending(takes, video, total)


BYTES_PER_FRAME = 4  # two channels of 16 bits


def _span(pcm: bytes, start: float, length: float) -> bytes:
    return pcm[round(start * SAMPLE_RATE) * BYTES_PER_FRAME : round((start + length) * SAMPLE_RATE) * BYTES_PER_FRAME]


def _loud_tail(pcm: bytes, start: float, length: float) -> bool:
    """Whether a cut's last moments hold speech, i.e. it ends inside the next line or this one."""
    tail = _span(pcm, start + length - TAIL_CHECK, TAIL_CHECK)
    return AudioSegment(data=tail, sample_width=2, frame_rate=SAMPLE_RATE, channels=2).dBFS > QUIET_DBFS


def _write(pcm: bytes, start: float, length: float, out: Path) -> None:
    partial = out.with_suffix(".partial")
    with wave.open(str(partial), "wb") as clip:
        clip.setnchannels(2)
        clip.setsampwidth(2)
        clip.setframerate(SAMPLE_RATE)
        clip.writeframes(_span(pcm, start, length))
    partial.replace(out)


def _seconds(path: Path) -> float:
    with wave.open(str(path), "rb") as clip:
        return clip.getnframes() / clip.getframerate()


def main() -> None:
    parser = argparse.ArgumentParser(description="Cut a published deck's voiced lines back into the api's reuse folder.")
    parser.add_argument("decks", nargs="+")
    parser.add_argument("--compare", action="store_true", help="compare the cuts with saved real takes, writing nothing")
    args = parser.parse_args()
    for k in args.decks:
        sid, media = dict(live_decks())[int(k)], mid(k)
        content = json.loads((R / "published" / f"{sid}.json").read_text(encoding="utf-8"))
        work = W / "recache" / sid
        work.mkdir(parents=True, exist_ok=True)
        video = work / "published.mp4"
        if not video.exists():
            urllib.request.urlretrieve(content["final_video_url"], video)
        pcm = _soundtrack(video, work / "soundtrack.wav")
        lines = _lines(content, work, video)
        loud = [text[:40] for text, start, length in lines if _loud_tail(pcm, start, length)]
        if loud:
            raise SystemExit(f"{k}: {len(loud)} cuts end in speech, writing nothing: {loud}")
        saved = R / "voice-cache" / media
        if args.compare:
            gaps = [(abs(_seconds(saved / _name(t)) - n), t[:40]) for t, _, n in lines if (saved / _name(t)).exists()]
            worst = max(gaps, default=(0.0, ""))
            print(f"{k}: {len(gaps)}/{len(lines)} lines have a real take; worst length gap {worst[0]:.3f}s ({worst[1]})")
            continue
        folder = VOICE / media
        folder.mkdir(parents=True, exist_ok=True)
        if saved.is_dir():
            for take in saved.glob("*.wav"):
                if not (folder / take.name).exists():
                    shutil.copy(take, folder / take.name)
        cut = 0
        for text, start, length in lines:
            if not (folder / _name(text)).exists():
                _write(pcm, start, length, folder / _name(text))
                cut += 1
        print(f"{k}: {len(lines)} lines, {cut} cut from the video, folder {folder}")


if __name__ == "__main__":
    main()
