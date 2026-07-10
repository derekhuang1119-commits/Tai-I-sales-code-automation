"""Typed data exchanged between the offline conversion pipeline stages."""

from dataclasses import dataclass, field
from typing import Any

Point = tuple[float, float]
Polygon = tuple[Point, ...]
REQUIRED_FIELDS = ("region", "bar_number", "total_length", "quantity", "total_weight")


@dataclass(frozen=True)
class OCRToken:
    """One OCR result, retaining its page, geometry and confidence."""

    text: str
    confidence: float
    polygon: Polygon
    page_number: int

    @property
    def bbox(self) -> tuple[float, float, float, float]:
        xs, ys = zip(*self.polygon)
        return min(xs), min(ys), max(xs), max(ys)

    @property
    def center(self) -> Point:
        left, top, right, bottom = self.bbox
        return ((left + right) / 2, (top + bottom) / 2)


@dataclass
class PageOCR:
    """OCR tokens and source image metadata for one source page."""

    page_number: int
    width: int
    height: int
    tokens: list[OCRToken] = field(default_factory=list)
    image: Any = None
    used_ocr_fallback: bool = False

    @property
    def text(self) -> str:
        return " ".join(token.text for token in self.tokens)


@dataclass
class ShapeAnalysis:
    """Shape fields inferred from the shape-column ROI and nearby OCR coordinates."""

    left_top: float | None = None
    left_long: float | None = None
    left_bottom: float | None = None
    middle_top: float | None = None
    middle_bottom: float | None = None
    right_top: float | None = None
    right_long: float | None = None
    right_bottom: float | None = None
    bird_mouth: float | None = None
    is_stirrup: bool = False
    warnings: list[str] = field(default_factory=list)


@dataclass
class BarItem:
    """A reviewable, exportable reinforcement-bar row."""

    region: str = ""
    page_number: int | None = None
    bar_number: str = ""
    total_length: float | None = None
    quantity: int | None = None
    total_weight: float | None = None
    steel_grade: str = ""
    shape: ShapeAnalysis = field(default_factory=ShapeAnalysis)
    confidence: dict[str, float] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    excluded: bool = False
    needs_review: bool = False
    source_page: PageOCR | None = None
    source_roi: tuple[int, int, int, int] | None = None
