"""A moved bucket file: every spelling of its old link points at the new bucket, and nothing else changes."""

from __future__ import annotations

import re

import pytest

from app.features.media_production import slide_av, slide_pictures
from app.features.media_production.podcast_tts import podcast_folder
from app.migration import b2c_firestore, bucket_moves
from app.migration.bucket_copy import plan_copies

OLD = "https://osceguide.s3.eu-west-2.amazonaws.com"
NEW = "https://osceguide-platform.s3.eu-west-2.amazonaws.com"
NEW_FOLDERS = re.compile(r"^(station_images|teaching_videos|podcasts)/[a-z]+/")


def test_an_old_station_photo_link_in_every_spelling_points_at_its_new_folder() -> None:
    document = {
        "raw": f"{OLD}/yahayakenny/Collesfracture (1).jpg",
        "spaces": f"{OLD}/yahayakenny/Collesfracture%20(1).jpg",
        "plus": f"{OLD}/yahayakenny/Collesfracture+(1).jpg",
        "encoded": f"{OLD}/yahayakenny/Collesfracture%20%281%29.jpg",
    }

    rewritten = bucket_moves.rewrite_value(document)

    assert rewritten == {
        "raw": f"{NEW}/station_images/ortho/Collesfracture (1).jpg",
        "spaces": f"{NEW}/station_images/ortho/Collesfracture%20(1).jpg",
        "plus": f"{NEW}/station_images/ortho/Collesfracture+(1).jpg",
        "encoded": f"{NEW}/station_images/ortho/Collesfracture%20%281%29.jpg",
    }


def test_a_deck_a_picture_and_a_podcast_move_under_their_exam() -> None:
    deck = "_copd__advanced_cancer_-_palliative_care_slide_d47aec21.mp4"
    document = {
        "deck": f"{OLD}/teaching_videos/v2/sca/{deck}",
        "picture": f"{OLD}/teaching_videos/v2/pictures/00f28cdd5667bcfd5e02.jpg",
        "podcast": f"{OLD}/podcasts/v4/acne_vulgaris.mp3",
        "in_prose": f"watch {OLD}/podcasts/v4/asthma.mp3 now",
    }

    assert bucket_moves.rewrite_value(document) == {
        "deck": f"{NEW}/teaching_videos/sca/{deck}",
        "picture": f"{NEW}/teaching_videos/sca/pictures/00f28cdd5667bcfd5e02.jpg",
        "podcast": f"{NEW}/podcasts/sca/acne_vulgaris.mp3",
        "in_prose": f"watch {NEW}/podcasts/sca/asthma.mp3 now",
    }


def test_links_that_name_no_moved_file_come_back_untouched() -> None:
    untouched = {
        "kept": f"{OLD}/yahayakenny/not-in-the-list.jpg",
        "already_moved": f"{NEW}/stations/11111111-1111-1111-1111-111111111111/a.png",
        "another_bucket": "https://eventtz.s3.eu-west-2.amazonaws.com/avatars/u/a.jpg",
        "an_app_route": "https://app.example.com/api/v1/orgs/kings/stations/11111111/photos",
        "elsewhere": "https://upload.wikimedia.org/yahayakenny/Collesfracture (1).jpg",
        "count": 3,
    }

    assert bucket_moves.rewrite_value(untouched) == untouched


def test_rewriting_twice_changes_nothing_more() -> None:
    once = bucket_moves.rewrite_value({"u": f"{OLD}/podcasts/v4/acne_vulgaris.mp3"})

    assert bucket_moves.rewrite_value(once) == once


def test_the_legacy_importer_never_brings_an_old_link_back() -> None:
    firestore_document = {"blocks": [{"image": f"{OLD}/fourint/IMG_1206.jpeg"}], "note": "a\x00b"}

    assert b2c_firestore.serialize(firestore_document) == {
        "blocks": [{"image": f"{NEW}/station_images/sca/IMG_1206.jpeg"}],
        "note": "ab",
    }


def test_every_destination_is_inside_an_exam_folder_and_no_two_files_share_one() -> None:
    moves = bucket_moves.load_moves()

    assert all(NEW_FOLDERS.match(new) for new in moves.values())
    assert len(set(moves.values())) == len(moves)


@pytest.mark.parametrize("old_folder", ["teaching_videos/v2/", "podcasts/v4/", "yahayakenny/", "fourint/"])
def test_the_code_no_longer_writes_to_an_old_folder(old_folder: str) -> None:
    written = [
        slide_av.S3_FOLDER,
        slide_pictures.PICTURE_FOLDER,
        podcast_folder(None),
        podcast_folder("ortho"),
    ]

    assert not any(folder.startswith(old_folder) for folder in written)
    assert slide_pictures.PICTURE_FOLDER == "teaching_videos/sca/pictures"
    assert podcast_folder("ORTHO") == "podcasts/ortho"
    assert podcast_folder(None) == "podcasts/general"


def test_a_new_station_upload_is_filed_under_its_exam_not_its_station() -> None:
    from app.features.stations import domain_photos

    key = domain_photos.object_key(exam_code="ORTHO", filename="Xray.PNG")

    assert key.startswith("station_images/ortho/") and key.endswith(".png")
    assert domain_photos.object_key(exam_code="", filename="a.jpg").startswith("station_images/general/")


def test_whole_folders_move_to_the_new_bucket_in_every_address_style() -> None:
    document = {
        "avatar": f"{OLD}/avatars/u1/a.jpg",
        "path_style": "https://s3.eu-west-2.amazonaws.com/osceguide/stations/s1/a.png",
        "recording": f"{OLD}/human_practice/sca/s1/consultation.ogg",
        "video": f"{OLD}/marketing/osceguide-sca.mp4",
    }

    assert bucket_moves.rewrite_value(document) == {
        "avatar": f"{NEW}/avatars/u1/a.jpg",
        "path_style": f"{NEW}/stations/s1/a.png",
        "recording": f"{NEW}/peer_practice/sca/s1/consultation.ogg",
        "video": f"{NEW}/marketing/osceguide-sca.mp4",
    }


def test_platform_key_says_where_any_key_belongs() -> None:
    assert bucket_moves.platform_key("human_practice/sca/s1/c.ogg") == "peer_practice/sca/s1/c.ogg"
    assert bucket_moves.platform_key("peer_practice/ortho/s2/c.ogg") == "peer_practice/ortho/s2/c.ogg"
    assert bucket_moves.platform_key("avatars/u1/a.jpg") == "avatars/u1/a.jpg"
    assert bucket_moves.platform_key("yahayakenny/Collesfracture (1).jpg") == (
        "station_images/ortho/Collesfracture (1).jpg"
    )
    assert bucket_moves.platform_key("platform/avatars/u1/a.jpg") is None
    assert bucket_moves.platform_key("screenshots/logo-image.png") is None


def test_the_copy_plan_sends_each_file_once_and_skips_what_is_already_there() -> None:
    source = {
        "human_practice/sca/s1/c.ogg": 10,
        "peer_practice/sca/s1/c.ogg": 10,
        "avatars/u1/a.jpg": 5,
        "yahayakenny/Collesfracture (1).jpg": 7,
        "screenshots/logo-image.png": 3,
    }
    already_there = {"avatars/u1/a.jpg": 5}

    to_copy, conflicts = plan_copies(source, already_there)

    assert conflicts == []
    assert to_copy == {
        "peer_practice/sca/s1/c.ogg": "human_practice/sca/s1/c.ogg",
        "station_images/ortho/Collesfracture (1).jpg": "yahayakenny/Collesfracture (1).jpg",
    }
    assert plan_copies({**source, "peer_practice/sca/s1/c.ogg": 11}, already_there)[1] != []
