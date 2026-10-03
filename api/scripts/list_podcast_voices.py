"""List ElevenLabs shared-library voices that suit a conversational podcast host.

    poetry run python scripts/list_podcast_voices.py --gender male --accent british
    poetry run python scripts/list_podcast_voices.py --gender female --accent british

Add a voice to your ElevenLabs library, then put its id in ELEVENLABS_VOICE_BEN or
ELEVENLABS_VOICE_MICHELLE. Audition it with `--limit 1` of regenerate_podcasts.py.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--gender", choices=("male", "female"), required=True)
    parser.add_argument("--accent", default="british")
    parser.add_argument("--use-case", default="conversational")
    parser.add_argument("--limit", type=int, default=15)
    args = parser.parse_args()
    response = httpx.get(
        "https://api.elevenlabs.io/v1/shared-voices",
        headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"]},
        params={
            "gender": args.gender,
            "accent": args.accent,
            "language": "en",
            "use_cases": args.use_case,
            "sort": "usage_character_count_7d",
            "page_size": args.limit,
        },
        timeout=30,
    )
    response.raise_for_status()
    for voice in response.json().get("voices", []):
        print(  # noqa: T201
            f"{voice['voice_id']}  {voice['name']:<22} {voice.get('descriptive', '')}, {voice.get('age', '')}"
        )
        print(f"    {voice.get('preview_url', '')}")  # noqa: T201


if __name__ == "__main__":
    main()
