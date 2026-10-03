"""Draws the frames of a narrated slide deck with Pillow.

A `Scene` is one slide, a section card, the recap or the sign-off. It lays its text out once,
from real font measurements, and can then paint any moment of itself: how many rows are
showing, which one is being spoken, and the caption underneath. When each moment happens is
decided in `slide_av.py`.
"""

from __future__ import annotations

import logging
import math
import re
from collections.abc import Sequence
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

logger = logging.getLogger(__name__)

WIDTH, HEIGHT = 1920, 1080
COUNTDOWN_SECONDS = 3.0

BRAND = (23, 25, 235)
BRAND_DEEP = (15, 17, 176)
INK = (24, 27, 33)
SUBTLE = (104, 111, 125)
MUTED = (163, 169, 181)
TRACK = (224, 229, 242)
WHITE = (255, 255, 255)
PAPER_LOW = (239, 243, 253)

LEFT = 132
RIGHT = WIDTH - 110
TITLE_TOP = 190
CONTENT_BOTTOM = 936
CAPTION_MIDDLE = 1004
CAPTION_WIDTH = 1500
CAPTION_SIZE = 30
CAPTION_FILL = (0, 0, 0)
RING_MIDDLE = (WIDTH // 2, 590)
BAR_HEIGHT = 8
READING_WIDTH = 1500
NARROW_WIDTH = 1010
SIDE_WIDTH = 520
IMAGE_ZOOM = 1.1

ASSETS = Path(__file__).resolve().parent / "assets"
_LOGO_BOX = (60, 60, 268, 120)
_LOGO_AT = (LEFT, 60)
_SUPERSAMPLE = 4
# Font scale and gap scale to try in turn when a slide is crowded: the gaps give way first.
_SCALES = (
    (1.0, 1.0),
    (1.0, 0.75),
    (0.94, 0.75),
    (0.94, 0.55),
    (0.88, 0.55),
    (0.82, 0.5),
    (0.76, 0.45),
    (0.7, 0.4),
    (0.64, 0.4),
    (0.58, 0.35),
    (0.52, 0.3),
)

Colour = tuple[int, int, int]
Words = list[tuple[str, bool]]


@dataclass(frozen=True)
class Row:
    """One line of a slide's list (or its one paragraph), before it is wrapped."""

    text: str
    size: int = 40
    indent: int = 0
    gap: int = 0
    marker: str = "dot"  # "dot", "dash", "" for none, or a numeral such as "1"
    parent: int | None = None
    strong: tuple[str, ...] = ()


@dataclass(frozen=True)
class _Placed:
    """A row once wrapped: its lines, its final font size and where its text starts."""

    row: Row
    lines: list[Words]
    size: int
    left: int
    top: int


def resolve_image_path(image_url: str, slides_dir: Path, deck_dir: Path) -> Path:
    """Where a slide's `image_url` points: under `slides_dir` for `images/...`, else `deck_dir`.

    Security (SEC-018): `image_urls` are LLM-generated, so the value is untrusted. An absolute
    path, a `..` traversal or anything that resolves outside its base directory comes back as
    a path that does not exist, so it can never be drawn into a video that is then uploaded.
    """
    base = slides_dir if image_url.startswith("images/") else deck_dir
    rejected = base / "__rejected_unsafe_image_path__"
    candidate = Path(image_url)
    if candidate.is_absolute() or ".." in candidate.parts:
        logger.warning("Rejected unsafe image path (traversal/absolute): %r", image_url)
        return rejected
    image_path = (base / candidate).resolve()
    try:
        image_path.relative_to(base.resolve())
    except ValueError:
        logger.warning("Rejected out-of-tree image path: %r", image_url)
        return rejected
    return image_path


def _gradient(top: Colour, bottom: Colour) -> Image.Image:
    """A full-frame background that fades evenly from `top` to `bottom`."""
    column = Image.new("RGB", (1, HEIGHT))
    for line in range(HEIGHT):
        shade = tuple(
            round(first + (last - first) * line / (HEIGHT - 1))
            for first, last in zip(top, bottom, strict=True)
        )
        column.putpixel((0, line), shade)
    return column.resize((WIDTH, HEIGHT))


@lru_cache(maxsize=128)
def _rounded(width: int, height: int, radius: int) -> Image.Image:
    """A smooth-edged rounded rectangle as a paste mask (Pillow's own shapes are not antialiased)."""
    scale = _SUPERSAMPLE
    large = Image.new("L", (width * scale, height * scale), 0)
    ImageDraw.Draw(large).rounded_rectangle(
        (0, 0, width * scale - 1, height * scale - 1), radius * scale, fill=255
    )
    return large.resize((width, height), Image.Resampling.LANCZOS)


def _line_height(size: int) -> int:
    return round(size * 1.5)


class Painter:
    """The deck's look: fonts, the two backgrounds and the text measurements every scene shares."""

    def __init__(self, font_dir: Path | None = None) -> None:
        self._font_dir = font_dir or ASSETS / "fonts"
        self._fonts: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}
        logo = Image.open(ASSETS / "slides" / "images" / "bg.png").convert("RGB").crop(_LOGO_BOX)
        # The logo is brand blue on white, so its red channel says how white each pixel is.
        logo_ink = logo.getchannel("R").point(lambda red: min(255, round((255 - red) * 1.1)))
        self.light = _gradient(WHITE, PAPER_LOW)
        self.light.paste(BRAND, _LOGO_AT, logo_ink)
        self.card = _gradient(BRAND, BRAND_DEEP)
        self.card.paste(WHITE, _LOGO_AT, logo_ink)

    def font(self, weight: str, size: int) -> ImageFont.FreeTypeFont:
        """Poppins in the given weight and size, loaded once."""
        key = (weight, size)
        if key not in self._fonts:
            self._fonts[key] = ImageFont.truetype(str(self._font_dir / f"Poppins-{weight}.ttf"), size)
        return self._fonts[key]

    def wrap(self, row: Row, size: int, width: int, weight: str = "Regular") -> list[Words]:
        """The row's words split into lines no wider than `width`, each word marked strong or not."""
        normal, strong = self.font(weight, size), self.font("SemiBold", size)
        space = normal.getlength(" ")
        spans = [
            match.span()
            for phrase in row.strong
            if phrase.strip()
            for match in re.finditer(re.escape(phrase.strip()), row.text, re.IGNORECASE)
        ]
        lines: list[Words] = [[]]
        used = 0.0
        for word in re.finditer(r"\S+", row.text):
            is_strong = any(word.start() < end and start < word.end() for start, end in spans)
            length = (strong if is_strong else normal).getlength(word.group())
            if lines[-1] and used + space + length > width:
                lines.append([])
                used = 0.0
            used += (space if lines[-1] else 0.0) + length
            lines[-1].append((word.group(), is_strong))
        return lines

    def marker_room(self, row: Row, size: int) -> int:
        """The width kept clear to the left of a row's text for its bullet, dash or numeral."""
        if not row.marker:
            return 0
        return round(size * (0.9 if row.marker in ("dot", "dash") else 1.7))

    def stack(self, rows: Sequence[Row], left: int, width: int, top: int, bottom: int) -> list[_Placed]:
        """Places the rows under each other, shrinking every font together until they all fit."""
        placed: list[_Placed] = []
        for scale, gap_scale in _SCALES:
            placed = []
            row_top = top
            for index, row in enumerate(rows):
                size = round(row.size * scale)
                inset = round(row.indent * scale) + self.marker_room(row, size)
                lines = self.wrap(row, size, width - inset)
                row_top += round(row.gap * gap_scale) if index else 0
                placed.append(_Placed(row, lines, size, left + inset, row_top))
                row_top += len(lines) * _line_height(size)
            if row_top <= bottom:
                break
        return placed

    def headline(self, text: str, size: int, width: int, max_lines: int, floor: int) -> tuple[list[str], int]:
        """`text` wrapped in SemiBold, shrunk from `size` until it takes at most `max_lines`."""
        lines: list[str] = []
        while True:
            wrapped = self.wrap(Row(text), size, width, weight="SemiBold")
            lines = [" ".join(word for word, _ in line) for line in wrapped]
            if len(lines) <= max_lines or size <= floor:
                return lines, size
            size -= 4

    def fit_one_line(self, text: str, weight: str, size: int, width: int) -> ImageFont.FreeTypeFont:
        """The largest font, from `size` down, in which `text` fits `width` on one line."""
        while size > 24 and self.font(weight, size).getlength(text) > width:
            size -= 4
        return self.font(weight, size)


def _spaced(
    draw: ImageDraw.ImageDraw, at: tuple[int, int], text: str, font: ImageFont.FreeTypeFont, fill: Colour
) -> None:
    """Small capitals with a little air between the letters."""
    pen = float(at[0])
    for character in text.upper():
        draw.text((pen, at[1]), character, font=font, fill=fill)
        pen += font.getlength(character) + 4


class Scene:
    """One slide's layout, able to paint itself at any moment."""

    def __init__(
        self,
        painter: Painter,
        *,
        kind: str = "content",  # "content", "question" or "card"
        title: str,
        rows: Sequence[Row] = (),
        eyebrow: str = "",
        counter: str = "",
        callouts: dict[int, tuple[str, str]] | None = None,
        images: Sequence[Path] = (),
        image_left: bool = False,
    ) -> None:
        self.painter = painter
        self.kind = kind
        self.eyebrow = eyebrow
        self.counter = counter
        self.rows = list(rows)
        self.callouts = callouts or {}
        self._painted: dict[tuple[int, int, str], Image.Image] = {}
        self._images: list[tuple[Image.Image, tuple[int, int, int, int]]] = []

        if kind == "card":
            self.title_lines, self.title_size = painter.headline(title, 96, 1560, 3, 60)
            block = 6 + 40 + 42 + 30 + len(self.title_lines) * round(self.title_size * 1.2)
            self.rule_top = (HEIGHT - block) // 2 - 10
            self.eyebrow_top = self.rule_top + 46
            self.title_top = self.eyebrow_top + 72
        elif kind == "question":
            self.eyebrow_top = TITLE_TOP
            self.title_lines, self.title_size = painter.headline(title, 76, 1560, 3, 52)
            self.title_top = TITLE_TOP + 64
        else:
            self.title_lines, self.title_size = painter.headline(title, 62, RIGHT - LEFT, 2, 42)
            self.title_top = TITLE_TOP
        self.title_bottom = self.title_top + len(self.title_lines) * round(self.title_size * 1.2)

        content_top = self.title_bottom + 50
        left, width = LEFT, READING_WIDTH
        usable = [path for path in images if path.exists()]
        if len(usable) == 3:
            each, gap = (RIGHT - LEFT - 72) // 3, 36
            for index, path in enumerate(usable):
                self._add_image(path, (LEFT + index * (each + gap), content_top, each, 300))
            content_top += 344
        elif usable and self.rows:
            box_height = min(520, CONTENT_BOTTOM - content_top)
            width = NARROW_WIDTH
            if image_left:
                self._add_image(usable[0], (LEFT, content_top, 600, box_height))
                left = LEFT + 670
            else:
                self._add_image(usable[0], (RIGHT - 600, content_top, 600, box_height))
        elif usable:
            self._add_image(usable[0], (LEFT, content_top, RIGHT - LEFT, CONTENT_BOTTOM - content_top))
        elif self.callouts:
            width = NARROW_WIDTH
        if self._images:
            self.callouts = {}
        self.content_top = content_top
        self.placed = painter.stack(self.rows, left, width, content_top, CONTENT_BOTTOM)

    def _add_image(self, path: Path, box: tuple[int, int, int, int]) -> None:
        """Readies a picture to be shown, slowly zooming, in `box` (left, top, width, height)."""
        # Kept a little larger than its box, so the slow zoom never has to enlarge a pixel.
        size = (round(box[2] * IMAGE_ZOOM), round(box[3] * IMAGE_ZOOM))
        source = ImageOps.fit(Image.open(path).convert("RGB"), size, Image.Resampling.LANCZOS)
        self._images.append((source, box))

    def paint(self, shown: int, active: int, caption: str) -> Image.Image:
        """The slide with its first `shown` rows visible, row `active` being spoken, and a caption.

        The result is shared between frames: copy it before drawing on it (`finish` does).
        """
        key = (shown, active, caption)
        if key not in self._painted:
            if len(self._painted) >= 6:
                self._painted.pop(next(iter(self._painted)))
            self._painted[key] = self._draw(shown, active, caption)
        return self._painted[key]

    def _draw(self, shown: int, active: int, caption: str) -> Image.Image:
        """Paints the whole slide for one moment; `paint` keeps the result."""
        painter, on_card = self.painter, self.kind == "card"
        image = (painter.card if on_card else painter.light).copy()
        draw = ImageDraw.Draw(image)
        if self.counter:
            fill = WHITE if on_card else SUBTLE
            draw.text((RIGHT, 90), self.counter, font=painter.font("Medium", 26), fill=fill, anchor="rm")
        if on_card:
            draw.rectangle((LEFT, self.rule_top, LEFT + 84, self.rule_top + 5), fill=WHITE)
        if self.eyebrow:
            fill = WHITE if on_card else BRAND
            _spaced(draw, (LEFT, self.eyebrow_top), self.eyebrow, painter.font("Medium", 28), fill)
        title_fill = WHITE if on_card else INK if self.kind == "question" else BRAND
        title_font = painter.font("SemiBold", self.title_size)
        for index, line in enumerate(self.title_lines):
            top = self.title_top + index * round(self.title_size * 1.2)
            draw.text((LEFT, top), line, font=title_font, fill=title_fill)

        lit = {active, self.rows[active].parent} if 0 <= active < len(self.rows) else set()
        for index, placed in enumerate(self.placed[:shown]):
            self._draw_row(image, draw, placed, index in lit)
        self._draw_callout(draw, active)
        if caption:
            self._draw_caption(image, draw, caption)
        return image

    def _draw_row(self, image: Image.Image, draw: ImageDraw.ImageDraw, placed: _Placed, lit: bool) -> None:
        """One row of the list: dark while it is being spoken, grey once it has been."""
        painter, size, row = self.painter, placed.size, placed.row
        normal, strong = painter.font("Regular", size), painter.font("SemiBold", size)
        ascent, descent = normal.getmetrics()
        line_height = _line_height(size)
        text_top = placed.top + (line_height - ascent - descent) // 2
        marker_left = placed.left - painter.marker_room(row, size)
        accent = BRAND if lit else MUTED
        if row.marker == "dot":
            diameter = max(8, round(size * 0.24))
            middle = text_top + ascent - round(size * 0.34)
            image.paste(accent, (marker_left, middle - diameter // 2), _rounded(diameter, diameter, diameter))
        elif row.marker == "dash":
            draw.text((marker_left, text_top), "–", font=normal, fill=accent)
        elif row.marker:
            draw.text((marker_left, text_top), row.marker, font=strong, fill=accent)
        space = normal.getlength(" ")
        for number, line in enumerate(placed.lines):
            pen = float(placed.left)
            for word, is_strong in line:
                font = strong if is_strong else normal
                draw.text((pen, text_top + number * line_height), word, font=font, fill=INK if lit else MUTED)
                pen += font.getlength(word) + space

    def _draw_callout(self, draw: ImageDraw.ImageDraw, active: int) -> None:
        """The key number of the row being spoken, large on the right, for as long as it is spoken."""
        if active not in self.callouts:
            return
        value, label = self.callouts[active]
        painter = self.painter
        left = RIGHT - SIDE_WIDTH
        value_font = painter.fit_one_line(value, "SemiBold", 132, SIDE_WIDTH)
        label_lines = painter.wrap(Row(label), 32, SIDE_WIDTH, weight="Medium")
        value_height = sum(value_font.getmetrics())
        block = 6 + 30 + value_height + 6 + len(label_lines) * 46
        top = max(self.content_top, (self.content_top + CONTENT_BOTTOM - block) // 2)
        draw.rectangle((left, top, left + 72, top + 5), fill=BRAND)
        draw.text((left, top + 36), value, font=value_font, fill=BRAND)
        label_font = painter.font("Medium", 32)
        for number, line in enumerate(label_lines):
            words = " ".join(word for word, _ in line)
            draw.text((left, top + 42 + value_height + number * 46), words, font=label_font, fill=SUBTLE)

    def _draw_caption(self, image: Image.Image, draw: ImageDraw.ImageDraw, caption: str) -> None:
        """Ben's current words, white on a black pill along the bottom so they stand out on any slide."""
        font = self.painter.fit_one_line(caption, "Medium", CAPTION_SIZE, CAPTION_WIDTH)
        width, height = round(font.getlength(caption)) + 68, 62
        left, top = (WIDTH - width) // 2, CAPTION_MIDDLE - height // 2
        image.paste(CAPTION_FILL, (left, top), _rounded(width, height, height // 2))
        draw.text((WIDTH // 2, CAPTION_MIDDLE), caption, font=font, fill=WHITE, anchor="mm")

    def finish(
        self, image: Image.Image, progress: float, countdown: float | None, deck_fraction: float
    ) -> Image.Image:
        """A copy of a painted slide with everything that moves every frame drawn on top.

        `progress` is how far through this scene we are (the image zoom), `countdown` the
        seconds left on a question's ring (None when it is not running), and `deck_fraction`
        how far through the whole talk (the bar along the bottom).
        """
        image = image.copy()
        for source, (left, top, width, height) in self._images:
            scale = 1 + (IMAGE_ZOOM - 1) * min(1.0, max(0.0, progress))
            window = (source.width / scale, source.height / scale)
            edge = ((source.width - window[0]) / 2, (source.height - window[1]) / 2)
            box = (edge[0], edge[1], edge[0] + window[0], edge[1] + window[1])
            zoomed = source.resize((width, height), Image.Resampling.BILINEAR, box=box)
            image.paste(zoomed, (left, top), _rounded(width, height, 18))
        if self.kind == "question":
            self._draw_ring(image, countdown)
        on_card = self.kind == "card"
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, HEIGHT - BAR_HEIGHT, WIDTH, HEIGHT), fill=BRAND_DEEP if on_card else TRACK)
        filled = round(WIDTH * min(1.0, max(0.0, deck_fraction)))
        if filled:
            draw.rectangle((0, HEIGHT - BAR_HEIGHT, filled, HEIGHT), fill=WHITE if on_card else BRAND)
        return image

    def _draw_ring(self, image: Image.Image, countdown: float | None) -> None:
        """The thinking ring in the middle of a question slide: idle while Ben asks, then counting
        three seconds down."""
        diameter, stroke, scale = 240, 16, _SUPERSAMPLE
        left = RING_MIDDLE[0] - diameter // 2
        top = max(self.title_bottom + 50, RING_MIDDLE[1] - diameter // 2)
        large = Image.new("RGBA", (diameter * scale, diameter * scale), (0, 0, 0, 0))
        ring = ImageDraw.Draw(large)
        box = (0, 0, diameter * scale - 1, diameter * scale - 1)
        ring.ellipse(box, outline=(*TRACK, 255), width=stroke * scale)
        if countdown is not None:
            sweep = 360 * min(1.0, max(0.0, countdown / COUNTDOWN_SECONDS))
            ring.arc(box, start=-90, end=-90 + sweep, fill=(*BRAND, 255), width=stroke * scale)
        small = large.resize((diameter, diameter), Image.Resampling.LANCZOS)
        image.paste(small, (left, top), small)
        draw = ImageDraw.Draw(image)
        middle = (left + diameter // 2, top + diameter // 2)
        number_font = self.painter.font("SemiBold", 92)
        if countdown is None:
            draw.text(middle, "?", font=number_font, fill=MUTED, anchor="mm")
            return
        draw.text(middle, str(max(1, math.ceil(countdown))), font=number_font, fill=INK, anchor="mm")
        label_font = self.painter.font("Medium", 34)
        under = (middle[0], top + diameter + 52)
        draw.text(under, "Take a moment to think", font=label_font, fill=SUBTLE, anchor="mm")
