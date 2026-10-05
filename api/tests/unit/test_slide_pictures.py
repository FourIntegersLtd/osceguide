"""Searching a faked Commons for a deck's pictures, and where the renderer looks for a stored one."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

from app.features.media_production.slide_av import picture_file
from app.features.media_production.slide_pictures import Candidate, commons_search

BUCKET = "https://osceguide.s3.eu-west-2.amazonaws.com/teaching_videos/v2/pictures/"


def _page(index: int, title: str, licence: str, width: int = 2000) -> dict[str, Any]:
    return {
        "index": index,
        "title": title,
        "imageinfo": [
            {
                "width": width,
                "thumburl": f"https://upload.wikimedia.org/{index}.jpg",
                "descriptionurl": f"https://commons.wikimedia.org/wiki/{index}",
                "extmetadata": {
                    "LicenseShortName": {"value": licence},
                    "Artist": {"value": '<a href="x">Jo  Bloggs</a>'},
                },
            }
        ],
    }


def test_commons_search_keeps_only_wide_freely_licensed_files_in_rank_order() -> None:
    pages = {
        "1": _page(2, "File:Second.jpg", "CC BY-SA 4.0"),
        "2": _page(1, "File:First.jpg", "Public domain"),
        "3": _page(3, "File:NonCommercial.jpg", "CC BY-NC 2.0"),
        "4": _page(4, "File:NoDerivatives.jpg", "CC BY-ND 2.0"),
        "5": _page(5, "File:Narrow.jpg", "CC0", width=400),
        "6": _page(6, "File:AllRights.jpg", "Copyrighted"),
    }
    asked: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        asked.append(request.url.params["gsrsearch"])
        return httpx.Response(200, json={"query": {"pages": pages}})

    with httpx.Client(transport=httpx.MockTransport(handler)) as http:
        found = commons_search(http, "estradiol patch")

    assert asked == ["estradiol patch filetype:bitmap"]
    assert [candidate.title for candidate in found] == ["File:First.jpg", "File:Second.jpg"]
    assert found[0] == Candidate(
        title="File:First.jpg",
        url="https://upload.wikimedia.org/1.jpg",
        page="https://commons.wikimedia.org/wiki/1",
        author="Jo Bloggs",
        licence="Public domain",
    )


def test_the_renderer_draws_a_stored_picture_from_the_deck_folder_only_by_its_file_name(
    tmp_path: Path,
) -> None:
    deck_dir = tmp_path / "deck"
    assert picture_file(f"{BUCKET}abc.jpg", deck_dir) == deck_dir / "pictures" / "abc.jpg"
    assert picture_file("https://evil.example/../../etc/passwd", deck_dir) == deck_dir / "pictures" / "passwd"
    assert not picture_file("../../etc/passwd", deck_dir).exists()
