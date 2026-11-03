"""Paid media links: signed for a reader, never signed in storage, other folders left alone."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import pytest
from botocore.exceptions import NoCredentialsError

from app.core import object_urls
from app.features.media_production import service_storage
from app.features.stations import domain_photos

ORIGIN = "https://osceguide-platform.s3.eu-west-2.amazonaws.com"
DECK = f"{ORIGIN}/teaching_videos/sca/a_topic_0b5f1c4e-9d3a-4c7e-8a55-3f1d2e6b7a90.mp4"
PICTURE = f"{ORIGIN}/teaching_videos/sca/pictures/aspirin.jpg"
MARKETING = f"{ORIGIN}/marketing/osceguide-sca.mp4"
EPISODE = f"{ORIGIN}/podcasts/sca/episodes/0b5f1c4e.mp3"
MINE = f"{ORIGIN}/stations/11111111-1111-1111-1111-111111111111/a.png"
THEIRS = f"{ORIGIN}/stations/22222222-2222-2222-2222-222222222222/a.png"
MY_FOLDER = ("stations/11111111-1111-1111-1111-111111111111/",)
MEDIA = service_storage.MEDIA_KEY_PREFIXES


def settings_with(access_key: str = "AKIAFAKE", secret: str = "fake") -> SimpleNamespace:  # noqa: S107
    return SimpleNamespace(
        aws_s3_bucket="osceguide-platform",
        aws_region="eu-west-2",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret,
    )


@pytest.fixture
def configured(monkeypatch: pytest.MonkeyPatch) -> None:
    """A bucket with throwaway credentials: signing is local arithmetic, so nothing is called."""
    monkeypatch.setattr(service_storage, "get_settings", settings_with)
    monkeypatch.setattr(service_storage, "_warned_unsignable", False)


def keys_signed(value: object, prefixes: tuple[str, ...]) -> object:
    """The value with each signable link replaced by `SIGNED[<key>]`, so a test sees which key was read."""
    return object_urls.sign_bucket_urls(
        value,
        bucket="osceguide-platform",
        region="eu-west-2",
        allowed_prefixes=prefixes,
        sign_key=lambda key: f"SIGNED[{key}]",
    )


def test_a_gated_link_comes_back_signed_and_expiring(configured: None) -> None:
    signed = service_storage.sign_urls({"final_video_url": DECK}, prefixes=MEDIA)["final_video_url"]

    parts = urlparse(signed)
    query = parse_qs(parts.query)
    assert f"{parts.scheme}://{parts.netloc}{parts.path}" == DECK
    assert query["X-Amz-Expires"] == [str(service_storage.MEDIA_URL_TTL_SECONDS)]
    assert query["X-Amz-SignedHeaders"] == ["host"]  # a Range header is not signed, so seeking works
    assert "X-Amz-Signature" in query


def test_other_folders_and_other_hosts_are_left_alone(configured: None) -> None:
    other = "https://upload.wikimedia.org/a.jpg"
    content = {"hero": MARKETING, "elsewhere": other, "n": 3}

    assert service_storage.sign_urls(content, prefixes=MEDIA) == content


def test_a_link_inside_markdown_and_inside_a_slide_list_is_signed(configured: None) -> None:
    content = {"body_md": f"See ![x]({DECK}) now", "slides": [{"image_urls": [DECK]}]}

    signed = service_storage.sign_urls(content, prefixes=MEDIA)

    assert "X-Amz-Signature" in signed["body_md"] and signed["body_md"].endswith(") now")
    assert "X-Amz-Signature" in signed["slides"][0]["image_urls"][0]


def test_stripping_returns_exactly_the_stored_link(configured: None) -> None:
    content = {"final_video_url": DECK, "slides": [{"image_urls": [DECK]}]}

    assert service_storage.strip_urls(service_storage.sign_urls(content, prefixes=MEDIA)) == content


def test_signing_twice_does_not_stack_signatures(configured: None) -> None:
    once = service_storage.sign_urls({"u": DECK}, prefixes=MEDIA)

    assert service_storage.sign_urls(once, prefixes=MEDIA)["u"].count("X-Amz-Signature") == 1


# 1. A surface signs only the folders it owns.


def test_a_station_signs_its_own_folder_and_nothing_else(configured: None) -> None:
    content = {"own": MINE, "other_station": THEIRS, "podcast": EPISODE, "deck": DECK}

    signed = service_storage.sign_urls(content, prefixes=MY_FOLDER)

    assert "X-Amz-Signature" in signed["own"]
    assert {name: signed[name] for name in ("other_station", "podcast", "deck")} == {
        "other_station": THEIRS,
        "podcast": EPISODE,
        "deck": DECK,
    }


def test_study_media_signs_decks_and_podcasts_but_not_a_stations_photo(configured: None) -> None:
    signed = service_storage.sign_urls({"deck": DECK, "podcast": EPISODE, "photo": MINE}, prefixes=MEDIA)

    assert "X-Amz-Signature" in signed["deck"] and "X-Amz-Signature" in signed["podcast"]
    assert signed["photo"] == MINE


# 3. When signing cannot be done the page still loads, with no file and never the raw link.


@pytest.mark.parametrize("keys", [("", ""), ("AKIAFAKE", ""), ("", "fake")])
def test_without_both_storage_credentials_links_are_left_as_stored(
    monkeypatch: pytest.MonkeyPatch, keys: tuple[str, str]
) -> None:
    """Local development: nothing can be signed and nothing is stored, so a link is not touched."""
    monkeypatch.setattr(service_storage, "get_settings", lambda: settings_with(*keys))

    content = {"video": DECK, "picture": PICTURE, "hero": MARKETING, "n": 1}

    assert service_storage.sign_urls(content, prefixes=MEDIA) == content


def test_a_signer_that_raises_withholds_the_link_and_says_so_once(
    configured: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    said: list[str] = []

    def no_credentials(*_: object, **__: object) -> str:
        raise NoCredentialsError()

    monkeypatch.setattr(service_storage, "readable_url", no_credentials)
    monkeypatch.setattr(service_storage._log, "error", lambda event, **fields: said.append(event))

    first = service_storage.sign_urls({"a": DECK, "b": EPISODE}, prefixes=MEDIA)
    second = service_storage.sign_urls({"a": DECK}, prefixes=MEDIA)

    assert first == {"a": "", "b": ""} and second == {"a": ""}
    assert said == ["media_links_withheld"]


# 4. One decoding for a key, used by the folder check and by signing alike.


def test_a_plus_in_a_stored_link_is_a_space_in_the_key() -> None:
    signed = keys_signed({"u": f"{ORIGIN}/teaching_videos/My+Deck.mp4"}, MEDIA)

    assert signed == {"u": "SIGNED[teaching_videos/My Deck.mp4]"}


def test_percent_20_and_a_literal_space_name_the_same_key() -> None:
    signed = keys_signed(
        [
            f"{ORIGIN}/teaching_videos/My%20Deck.mp4",
            f"{ORIGIN}/teaching_videos/My Deck.mp4",
        ],
        MEDIA,
    )

    assert signed == ["SIGNED[teaching_videos/My Deck.mp4]"] * 2


def test_the_folder_check_and_signing_agree_on_a_plus_or_a_percent_20() -> None:
    links = [f"{ORIGIN}/marketing/a%20b.mp4", f"{ORIGIN}/marketing/a+b.mp4"]

    assert keys_signed(links, MEDIA) == links


def test_a_station_signs_its_own_folder_and_the_moved_photos_but_not_another_stations() -> None:
    moved = f"{ORIGIN}/station_images/sca/IMG_1206.jpeg"
    old_folder = f"{ORIGIN}/fourint/IMG_1206.jpeg"
    prefixes = domain_photos.key_prefixes(uuid.UUID("11111111-1111-1111-1111-111111111111"))

    signed = keys_signed([MINE, moved, THEIRS, old_folder], prefixes)

    assert signed == [
        "SIGNED[stations/11111111-1111-1111-1111-111111111111/a.png]",
        "SIGNED[station_images/sca/IMG_1206.jpeg]",
        THEIRS,
        old_folder,
    ]


def test_prose_ends_a_link_at_its_first_space() -> None:
    signed = keys_signed(f"watch {DECK} then rest", MEDIA)

    assert signed.startswith("watch SIGNED[teaching_videos/sca/") and signed.endswith("] then rest")


# 5. Every spelling of our bucket's host.


@pytest.mark.parametrize(
    "link",
    [
        "https://osceguide-platform.s3.eu-west-2.amazonaws.com/podcasts/a.mp3",
        "https://osceguide-platform.s3.amazonaws.com/podcasts/a.mp3",
        "https://osceguide-platform.s3-eu-west-2.amazonaws.com/podcasts/a.mp3",
        "https://s3.eu-west-2.amazonaws.com/osceguide-platform/podcasts/a.mp3",
        "https://s3.amazonaws.com/osceguide-platform/podcasts/a.mp3",
        "https://s3-eu-west-2.amazonaws.com/osceguide-platform/podcasts/a.mp3",
        "http://osceguide-platform.s3.amazonaws.com/podcasts/a.mp3",
    ],
)
def test_every_host_spelling_of_our_bucket_is_signed(link: str) -> None:
    assert keys_signed(link, MEDIA) == "SIGNED[podcasts/a.mp3]"


def test_another_bucket_is_not_ours() -> None:
    other = "https://elsewhere.s3.eu-west-2.amazonaws.com/podcasts/a.mp3"

    assert keys_signed(other, MEDIA) == other


# 7. Stripping touches only our bucket.


def test_a_signature_on_another_host_is_left_alone(configured: None) -> None:
    theirs = "https://elsewhere.s3.amazonaws.com/a.mp3?X-Amz-Signature=abc&X-Amz-Expires=60"
    other_cdn = "https://cdn.example.com/a.mp3?X-Amz-Signature=abc"
    signed_ours = service_storage.sign_urls({"u": EPISODE}, prefixes=MEDIA)["u"]

    stripped = service_storage.strip_urls({"theirs": theirs, "cdn": other_cdn, "ours": signed_ours})

    assert stripped == {"theirs": theirs, "cdn": other_cdn, "ours": EPISODE}


def test_a_stations_folder_ends_at_its_slash(configured: None) -> None:
    """Without the trailing slash, `stations/<id>-evil/` and `stations/<id>0/` would pass for the station."""
    from app.features.stations import domain_photos

    station_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    own = f"{ORIGIN}/stations/{station_id}/a.png"
    lookalikes = [f"{ORIGIN}/stations/{station_id}-copy/a.png", f"{ORIGIN}/stations/{station_id}0/a.png"]

    signed = service_storage.sign_urls([own, *lookalikes], prefixes=domain_photos.key_prefixes(station_id))

    assert "X-Amz-Signature=" in signed[0]
    assert signed[1:] == lookalikes
