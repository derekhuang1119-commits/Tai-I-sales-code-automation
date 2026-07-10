"""Coordinate-aware row parsing and page-marker extraction."""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Iterable

from .models import BarItem, OCRToken, PageOCR

PAGE_MARKER = re.compile(r"(?<!\d)\d+\s*-\s*(\d+)(?!\d)")
FIELD_LABELS = {
    "region": "區域", "page_number": "頁數", "bar_number": "號數",
    "total_length": "總長", "quantity": "支數", "total_weight": "總重", "steel_grade": "鋼種",
}


def page_marker_number(page: PageOCR, roi_ratio: float = 0.25) -> int | None:
    """Read the number after the dash in the bottom-right page marker."""

    min_x, min_y = page.width * (1 - roi_ratio), page.height * (1 - roi_ratio)
    text = " ".join(
        token.text for token in page.tokens
        if token.center[0] >= min_x and token.center[1] >= min_y
    )
    match = PAGE_MARKER.search(text)
    return int(match.group(1)) if match else None


def row_rois(page: PageOCR, horizontal_lines: Iterable[float] = ()) -> list[list[OCRToken]]:
    """Split tokens into table rows using detected horizontal line y values.

    If no lines are supplied, nearby token centers are used as a conservative
    synthetic table grid. Coordinates are retained in every returned token.
    """

    lines = sorted(set(horizontal_lines))
    if lines:
        groups: dict[int, list[OCRToken]] = defaultdict(list)
        for token in page.tokens:
            y = token.center[1]
            row = next((i for i in range(len(lines) - 1) if lines[i] <= y < lines[i + 1]), 0)
            groups[row].append(token)
        return [sorted(value, key=lambda token: token.center[0]) for _, value in sorted(groups.items())]
    rows: list[list[OCRToken]] = []
    for token in sorted(page.tokens, key=lambda item: item.center[1]):
        if not rows or abs(token.center[1] - rows[-1][0].center[1]) > max(8, token.bbox[3] - token.bbox[1]):
            rows.append([])
        rows[-1].append(token)
    return [sorted(row, key=lambda token: token.center[0]) for row in rows]


def parse_row(tokens: list[OCRToken], *, region: str = "", page_number: int | None = None) -> BarItem:
    """Parse a row by labels and preserve low-confidence warnings."""

    item = BarItem(region=region, page_number=page_number)
    fields = {
        "bar_number": r"(?:號數|號)\s*[:：]?\s*(#[\w-]+|[\w-]+)",
        "total_length": r"(?:總長|長度|長)\s*[:：]?\s*([\d.]+)",
        "quantity": r"(?:支數|數量|支)\s*[:：]?\s*(\d+)",
        "total_weight": r"(?:總重|重量)\s*[:：]?\s*([\d.]+)",
    }
    joined = " ".join(token.text for token in tokens)
    for field, pattern in fields.items():
        match = re.search(pattern, joined, re.IGNORECASE)
        if match:
            setattr(item, field, match.group(1).lstrip("#"))
            source = next((token for token in tokens if match.group(1) in token.text), None)
            item.confidence[field] = source.confidence if source else 0.5
    item.page_number = page_number
    if not item.region:
        item.warnings.append("缺少區域")
    for required in ("bar_number", "total_length", "quantity", "total_weight"):
        if not getattr(item, required):
            item.warnings.append(f"缺少必要欄位：{FIELD_LABELS[required]}")
    item.needs_review = bool(item.warnings) or any(value < 0.8 for value in item.confidence.values())
    return item
