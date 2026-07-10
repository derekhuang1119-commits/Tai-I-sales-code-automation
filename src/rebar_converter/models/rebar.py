from dataclasses import dataclass, field
from typing import Optional


DIMENSION_FIELDS = (
    "left_top", "left_long", "left_bottom", "middle_top", "middle_bottom",
    "right_top", "right_long", "right_bottom",
)


@dataclass(frozen=True)
class OCRText:
    text: str
    confidence: float = 1.0
    bbox: Optional[tuple[float, float, float, float]] = None


@dataclass
class RebarItem:
    region: str = ""
    page: str = ""
    steel_grade: str = ""
    bar_number: str = ""
    left_top: str = ""
    left_long: str = ""
    left_bottom: str = ""
    middle_top: str = ""
    middle_bottom: str = ""
    right_top: str = ""
    right_long: str = ""
    right_bottom: str = ""
    total_length: str = ""
    quantity: str = ""
    total_weight: str = ""
    shape_type: str = ""
    has_bird_beak: bool = False
    confidence: float = 1.0
    needs_review: bool = False
    excluded: bool = False
    raw_text: str = ""
    warnings: list[str] = field(default_factory=list)


@dataclass
class RebarPage:
    page_number: int
    text: str = ""
    items: list[RebarItem] = field(default_factory=list)

