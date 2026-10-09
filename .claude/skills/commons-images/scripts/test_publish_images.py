"""Publish payloads: python3 -I -m unittest discover -s .claude/skills/commons-images/scripts"""

import json
import tempfile
import unittest
from pathlib import Path

from publish_images import _entries, _firestore_update, _merge, _stations_by_document_id

ROW = {"station_id": "abc", "file": "File:Knee x-ray.jpg", "page_url": "https://commons.wikimedia.org/wiki/File:Knee_x-ray.jpg",
       "author": "Dr A", "licence": "CC BY-SA 4.0", "licence_url": "https://cc/by-sa/4.0", "description": "",
       "s3_url": "https://b.s3/yahayakenny/commons/abc/Knee_x-ray.jpg"}


def entries(*rows: dict) -> dict:
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "manifest.json").write_text(json.dumps(list(rows)))
        return _entries(Path(d))


class Entries(unittest.TestCase):
    def test_caption_credits_author_licence_and_source(self):
        (e,) = entries(ROW)["abc"]
        self.assertEqual(e["caption"], "Dr A, CC BY-SA 4.0, via Wikimedia Commons (https://commons.wikimedia.org/wiki/File:Knee_x-ray.jpg)")
        self.assertEqual((e["url"], e["kind"], e["alt"]), (ROW["s3_url"], "image", "Knee x-ray.jpg"))

    def test_image_not_yet_uploaded_stops_the_run(self):
        with self.assertRaises(SystemExit):
            entries({**ROW, "s3_url": None})


class Merge(unittest.TestCase):
    def test_keeps_existing_items_and_skips_urls_already_present(self):
        new = [{"url": "u1"}, {"url": "u2"}]
        self.assertEqual(_merge(["old", {"url": "u1", "caption": "x"}], new), ["old", {"url": "u1", "caption": "x"}, {"url": "u2"}])

    def test_second_run_changes_nothing(self):
        new = [{"url": "u1"}]
        once = _merge([], new)
        self.assertEqual(_merge(once, new), once)


class FirestoreUpdate(unittest.TestCase):
    def test_only_cc0_and_public_domain_reach_the_uncredited_field(self):
        new = [{"url": "by", "licence": "CC BY 4.0"}, {"url": "zero", "licence": "CC0"}, {"url": "pd", "licence": "Public domain"}]
        update = _firestore_update({"additional_image_urls": ["old"]}, new)
        self.assertEqual(update["additional_image_urls"], ["old", "zero", "pd"])
        self.assertEqual([e["url"] for e in update["commons_images"]], ["by", "zero", "pd"])

    def test_licence_spellings_needing_no_credit(self):
        new = [{"url": u, "licence": u} for u in ("CC0 1.0", "Public Domain Mark 1.0", "CC BY-SA 4.0", "PDM")]
        self.assertEqual(_firestore_update({}, new)["additional_image_urls"], ["CC0 1.0", "Public Domain Mark 1.0"])

    def test_second_run_writes_nothing(self):
        new = [{"url": "zero", "licence": "CC0"}]
        doc = {"additional_image_urls": ["old"]}
        self.assertEqual(_firestore_update({**doc, **_firestore_update(doc, new)}, new), {})


class StationsByDocumentId(unittest.TestCase):
    def test_matches_on_the_documents_station_id_field_else_its_id(self):
        rows = [("s1", {"station_id": "uuid-1"}), ("s2", {"station_id": "docB"})]
        docs = [{"id": "docA", "station_id": "uuid-1"}, {"id": "docB"}, {"id": "docC", "station_id": "gone"}]
        self.assertEqual(_stations_by_document_id(rows, docs),
                         {"docA": ("s1", {"station_id": "uuid-1"}), "docB": ("s2", {"station_id": "docB"})})


if __name__ == "__main__":
    unittest.main()
