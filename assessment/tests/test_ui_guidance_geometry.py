"""The model answers in screenshot pixels; the browser needs CSS pixels."""

from __future__ import annotations

from livekit_assistant_worker.ui_guidance.geometry import Viewport


def test_a_downscaled_capture_maps_back_up_to_the_viewport() -> None:
    # The browser rasterises at the viewport size, then downscales before sending.
    viewport = Viewport(viewport_width=1600, viewport_height=900, capture_width=800, capture_height=450)

    assert viewport.to_viewport(400, 225) == (800, 450)
    assert viewport.to_viewport(0, 0) == (0, 0)


def test_a_capture_at_viewport_size_is_left_alone() -> None:
    viewport = Viewport(viewport_width=1280, viewport_height=720, capture_width=1280, capture_height=720)

    assert viewport.to_viewport(640, 360) == (640, 360)


def test_coordinates_outside_the_page_are_pulled_back_onto_it() -> None:
    """A model that mis-reads the image must not send the pointer off screen."""
    viewport = Viewport(viewport_width=1000, viewport_height=500, capture_width=1000, capture_height=500)

    assert viewport.to_viewport(4000, 4000) == (1000, 500)
    assert viewport.to_viewport(-50, -50) == (0, 0)


def test_a_capture_reported_as_zero_sized_does_not_divide_by_zero() -> None:
    """Bad metadata should cost a misplaced pointer, not the whole turn."""
    viewport = Viewport(viewport_width=1280, viewport_height=720, capture_width=0, capture_height=0)

    assert viewport.to_viewport(100, 200) == (100, 200)


def test_it_is_built_from_the_screenshot_rpc_metadata() -> None:
    viewport = Viewport.from_metadata(
        {"viewportWidth": 1512, "viewportHeight": 858, "captureWidth": 1200, "captureHeight": 681, "mediaType": "image/jpeg"}
    )

    assert (viewport.viewport_width, viewport.capture_width) == (1512, 1200)
