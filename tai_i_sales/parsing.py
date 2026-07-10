"""Coordinate-aware row parsing and page-marker extraction."""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Iterable

from .models import REQUIRED_FIELDS, BarItem, OCRToken, PageOCR

PAGE_MARKER = re.compile(r"(?<!\d)\d+\s*-\s*(\d+)(?!\d)")
FIELD_LABELS = {
    "region": "區域", "page_number": "頁數", "bar_number": "號數",
    "total_length": "總長", "quantity": "支數", "total_weight": "總重", "steel_grade": "鋼種",
}
REGION_PATTERN = re.compile(r"([A-Za-z\u4e00-\u9fff]\s*區)")


def page_marker_number(page: PageOCR, roi_ratio: float = 0.25) -> int | None:
    """Read the number after the dash in the bottom-right page marker.

    Selects the most bottom-then-rightmost token that matches the page-marker
    pattern so results are stable regardless of OCR token ordering.
    """

    min_x = page.width * (1 - roi_ratio)
    min_y = page.height * (1 - roi_ratio)
    candidates: list[tuple[float, float, int]] = []
    for token in page.tokens:
        cx, cy = token.center
        if cx < min_x or cy < min_y:
            continue
        match = PAGE_MARKER.search(token.text)
        if match:
            candidates.append((cy, cx, int(match.group(1))))

    if candidates:
        # Sort descending by y (bottom-most) then descending by x (rightmost)
        candidates.sort(key=lambda c: (-c[0], -c[1]))
        return candidates[0][2]

    # Fall back: concatenate all ROI tokens and search (handles split tokens)
    roi_text = " ".join(
        token.text for token in page.tokens
        if token.center[0] >= min_x and token.center[1] >= min_y
    )
    match = PAGE_MARKER.search(roi_text)
    return int(match.group(1)) if match else None


def detect_region(page: PageOCR, header_ratio: float = 0.15) -> str | None:
    """Auto-detect region label such as 'A區' or '北區' from the page header area."""

    max_y = page.height * header_ratio
    for token in sorted(page.tokens, key=lambda t: t.center[1]):
        if token.center[1] > max_y:
            break
        match = REGION_PATTERN.search(token.text)
        if match:
            return match.group(1).replace(" ", "")
    return None


def row_rois(page: PageOCR, horizontal_lines: Iterable[float] = ()) -> list[list[OCRToken]]:
    """Split tokens into table rows using detected horizontal line y values.

    If no lines are supplied, nearby token centers are used as a conservative
    synthetic table grid. Coordinates are retained in every returned token.
    """

    lines = sorted(set(horizontal_lines))
    if lines:
        groups: dict[int, list[OCRToken]] = defaultdict(list)
        num_bands = len(lines) - 1
        for token in page.tokens:
            y = token.center[1]
            if num_bands <= 0:
                row = 0
            elif y < lines[0]:
                row = 0
            elif y >= lines[-1]:
                row = max(0, num_bands - 1)
            else:
                row = next(
                    (i for i in range(num_bands) if lines[i] <= y < lines[i + 1]),
                    num_bands - 1,
                )
            groups[row].append(token)
        return [sorted(value, key=lambda t: t.center[0]) for _, value in sorted(groups.items())]

    rows: list[list[OCRToken]] = []
    for token in sorted(page.tokens, key=lambda item: item.center[1]):
        # Eight pixels prevents tiny OCR baseline jitter from making new rows.
        if not rows or abs(token.center[1] - rows[-1][0].center[1]) > max(8, token.bbox[3] - token.bbox[1]):
            rows.append([])
        rows[-1].append(token)
    return [sorted(row, key=lambda t: t.center[0]) for row in rows]


def parse_row(
    tokens: list[OCRToken],
    *,
    region: str = "",
    page_number: int | None = None,
    col_bounds: dict[str, tuple[float, float]] | None = None,
) -> BarItem:
    """Parse a row by column x-bounds when provided, else fall back to label patterns.

    When *col_bounds* supplies ``{field_name: (x_min, x_max)}`` mappings the
    function reads numeric values from tokens whose center falls in the matching
    x range instead of requiring label text such as '號數：'.
    """

    item = BarItem(region=region, page_number=page_number)

    if col_bounds:
        for field_name, (xmin, xmax) in col_bounds.items():
            col_tokens = [t for t in tokens if xmin <= t.center[0] < xmax]
            if not col_tokens:
                continue
            col_tokens.sort(key=lambda t: t.center[0])
            text = " ".join(t.text for t in col_tokens).strip()
            conf = min(t.confidence for t in col_tokens)
            if field_name == "bar_number":
                item.bar_number = text.lstrip("#")
                item.confidence["bar_number"] = conf
            elif field_name == "total_length":
                try:
                    item.total_length = float(text.replace(",", ""))
                    item.confidence["total_length"] = conf
                except ValueError:
                    pass
            elif field_name == "quantity":
                try:
                    item.quantity = int(text)
                    item.confidence["quantity"] = conf
                except ValueError:
                    pass
            elif field_name == "total_weight":
                try:
                    item.total_weight = float(text.replace(",", ""))
                    item.confidence["total_weight"] = conf
                except ValueError:
                    pass
    else:
        # Label-based fallback
        label_fields = {
            "bar_number": r"(?:號數|號)\s*[:：]?\s*(#[\w-]+|[\w-]+)",
            "total_length": r"(?:總長|長度|長)\s*[:：]?\s*([\d.,]+)",
            "quantity": r"(?:支數|數量|支)\s*[:：]?\s*(\d+)",
            "total_weight": r"(?:總重|重量)\s*[:：]?\s*([\d.,]+)",
        }
        joined = " ".join(token.text for token in tokens)
        for field_name, pattern in label_fields.items():
            match = re.search(pattern, joined, re.IGNORECASE)
            if match:
                raw = match.group(1).lstrip("#")
                source = next((t for t in tokens if match.group(1) in t.text), None)
                conf = source.confidence if source else 0.5
                if field_name == "bar_number":
                    item.bar_number = raw
                    item.confidence["bar_number"] = conf
                elif field_name == "total_length":
                    try:
                        item.total_length = float(raw.replace(",", ""))
                        item.confidence["total_length"] = conf
                    except ValueError:
                        pass
                elif field_name == "quantity":
                    try:
                        item.quantity = int(raw)
                        item.confidence["quantity"] = conf
                    except ValueError:
                        pass
                elif field_name == "total_weight":
                    try:
                        item.total_weight = float(raw.replace(",", ""))
                        item.confidence["total_weight"] = conf
                    except ValueError:
                        pass

    item.page_number = page_number
    if not item.region:
        item.warnings.append("缺少區域")
    for required in REQUIRED_FIELDS[1:]:
        if getattr(item, required) in (None, ""):
            item.warnings.append(f"缺少必要欄位：{FIELD_LABELS.get(required, required)}")
    item.needs_review = bool(item.warnings) or any(value < 0.8 for value in item.confidence.values())
    return item
