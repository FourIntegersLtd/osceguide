"""The cheap checks that run before a PDF is parsed or a model is paid."""

from __future__ import annotations

import pytest

from app.features.cv import domain


def test_an_ordinary_pdf_is_accepted() -> None:
    domain.validate_upload(filename="CV.pdf", size=2048)


def test_the_extension_is_read_case_insensitively() -> None:
    domain.validate_upload(filename="My CV.PDF", size=2048)


def test_a_non_pdf_is_refused() -> None:
    with pytest.raises(domain.InvalidCv):
        domain.validate_upload(filename="cv.docx", size=2048)


def test_an_oversized_file_is_refused() -> None:
    with pytest.raises(domain.InvalidCv):
        domain.validate_upload(filename="cv.pdf", size=domain.MAX_BYTES + 1)


def test_a_file_too_small_to_be_a_cv_is_refused() -> None:
    with pytest.raises(domain.InvalidCv):
        domain.validate_upload(filename="cv.pdf", size=domain.MIN_BYTES - 1)


def test_enough_text_passes_through_stripped() -> None:
    body = "x" * domain.MIN_TEXT_CHARS
    assert domain.ensure_enough_text(f"  {body}  ") == body


def test_a_pdf_with_nothing_to_read_is_refused() -> None:
    with pytest.raises(domain.InvalidCv):
        domain.ensure_enough_text("too short")
