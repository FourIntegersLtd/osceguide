"""Licence check: python3 -I -m unittest discover -s .claude/skills/commons-images/scripts"""

import unittest
from unittest import mock

import commons_images
from commons_images import _existing_status, _trace_existing, licence_verdict


def meta(short: str, code: str = "", artist: str = "Dr A", **extra: str) -> dict:
    fields = {"LicenseShortName": short, "License": code, "Artist": artist, **extra}
    return {k: {"value": v} for k, v in fields.items()}


class LicenceVerdict(unittest.TestCase):
    def test_commercial_licences_pass(self):
        for short, code in [("CC0", "cc0"), ("Public domain", "pd"), ("CC BY 4.0", "cc-by-4.0"),
                            ("CC BY-SA 3.0", "cc-by-sa-3.0")]:
            self.assertEqual(licence_verdict(meta(short, code), [], []), (True, []), short)

    def test_non_commercial_and_no_derivatives_fail(self):
        for short, code in [("CC BY-NC 4.0", "cc-by-nc-4.0"), ("CC BY-ND 4.0", "cc-by-nd-4.0"),
                            ("CC BY-NC-SA 2.0", "cc-by-nc-sa-2.0")]:
            self.assertFalse(licence_verdict(meta(short, code), [], [])[0], short)

    def test_unclear_licences_fail(self):
        self.assertFalse(licence_verdict(meta("No restrictions"), [], [])[0])
        self.assertFalse(licence_verdict(meta(""), [], [])[0])
        self.assertFalse(licence_verdict(meta("Fair use", "fair use"), [], [])[0])

    def test_red_flag_on_page_fails_even_with_good_licence(self):
        ok, reasons = licence_verdict(meta("CC BY 4.0", "cc-by-4.0"), ["Category:Deletion requests October 2026"], [])
        self.assertFalse(ok)
        self.assertIn("red flag on file page: Category:Deletion requests October 2026", reasons)

    def test_attribution_licence_without_author_fails(self):
        self.assertFalse(licence_verdict(meta("CC BY 4.0", "cc-by-4.0", artist=""), [], [])[0])

    def test_restrictions_need_a_human(self):
        self.assertFalse(licence_verdict(meta("CC0", "cc0", Restrictions="personality"), [], [])[0])



def page(title: str, **flags: bool) -> dict:
    meta_ = {k: {"value": v} for k, v in {"LicenseShortName": "CC BY-SA 3.0", "License": "cc-by-sa-3.0", "Artist": "Dr A"}.items()}
    return {"title": title, **flags, "imageinfo": [{"descriptionurl": "https://c/x", "extmetadata": meta_}]}


class TraceExisting(unittest.TestCase):
    def test_matches_commons_file_whose_extension_case_differs(self):
        reply = {"query": {"pages": [page("File:Kneeffusion.jpg", missing=True), page("File:Kneeffusion.JPG")]}}
        with mock.patch.object(commons_images, "api_get", return_value=reply):
            found = _trace_existing("https://osceguide.s3.eu-west-2.amazonaws.com/yahayakenny/Kneeffusion.jpg")
        self.assertEqual((found["file"], found["licence"], found["licence_ok"]), ("File:Kneeffusion.JPG", "CC BY-SA 3.0", True))

    def test_no_match_reports_licence_unknown(self):
        with mock.patch.object(commons_images, "api_get", return_value={"query": {"pages": [page("File:images.jpg", missing=True)]}}):
            found = _trace_existing("https://x/images.jpg")
        self.assertIsNone(found)
        self.assertEqual(_existing_status({"commons_source": found}), '<span class="warn">licence unknown — check source</span>')

    def test_invalid_title_does_not_crash(self):
        with mock.patch.object(commons_images, "api_get", return_value={}):
            self.assertIsNone(_trace_existing("https://x/a.jpg"))
        self.assertIsNone(_trace_existing("https://x/a|b.jpg"))


if __name__ == "__main__":
    unittest.main()
