"""Slide renderer image-path traversal (security regression).

Finding SEC-018 (Medium). `resolve_image_path` joins an
LLM-generated `image_url` onto a base directory. The values are untrusted
(prompt-injection can reach them), so a `..` sequence or an absolute path must
not be able to escape the slides tree and be embedded into the rendered video
that is later uploaded to S3. These assert the traversal is neutralised while
ordinary in-tree images still resolve.
"""

from __future__ import annotations

from pathlib import Path

from app.features.media_production.slide_scenes import resolve_image_path


def test_legit_in_tree_image_resolves(tmp_path: Path) -> None:
    topic = tmp_path / "topic"
    topic.mkdir()
    (topic / "diagram.png").write_bytes(b"\x89PNG\r\n")
    resolved = resolve_image_path("diagram.png", tmp_path, topic)
    assert resolved == (topic / "diagram.png").resolve()
    assert resolved.exists()


def test_parent_traversal_is_rejected(tmp_path: Path) -> None:
    topic = tmp_path / "topic"
    topic.mkdir()
    # A secret the worker can read that sits outside the slides tree.
    secret = tmp_path.parent / "outside_secret.png"
    secret.write_bytes(b"\x89PNG\r\n")
    resolved = resolve_image_path("../../outside_secret.png", tmp_path, topic)
    # Must not resolve to the out-of-tree file, and must not exist so callers skip it.
    assert resolved != secret.resolve()
    assert not resolved.exists()


def test_absolute_path_is_rejected(tmp_path: Path) -> None:
    topic = tmp_path / "topic"
    topic.mkdir()
    resolved = resolve_image_path("/etc/hostname", tmp_path, topic)
    assert str(resolved) != "/etc/hostname"
    assert not resolved.exists()


def test_traversal_inside_images_prefix_is_rejected(tmp_path: Path) -> None:
    topic = tmp_path / "topic"
    topic.mkdir()
    resolved = resolve_image_path("images/../../../etc/hostname", tmp_path, topic)
    assert not resolved.exists()
    # Stays anchored under the slides base, not escaped above it.
    assert str(resolved).startswith(str(tmp_path))
