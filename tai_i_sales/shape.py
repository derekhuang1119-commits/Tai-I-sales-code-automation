"""Geometry-aware shape classification and crossed-out row detection."""

from __future__ import annotations

from typing import Any

from .models import OCRToken, ShapeAnalysis

SHAPE_CENTER_RATIO = 0.2


def analyze_shape(tokens: list[OCRToken], *, is_stirrup: bool = False) -> ShapeAnalysis:
    """Assign numeric labels to the nearest of eight shape-column drawing regions.

    Only tokens from the shape-column ROI should be supplied. Tokens containing
    bar number, total length, quantity, or total weight must be excluded before
    calling this function.
    """

    result = ShapeAnalysis(is_stirrup=is_stirrup)
    numeric = []
    for token in tokens:
        text = token.text.strip()
        # Accept tokens that look like numeric dimension values
        try:
            float(text.replace(",", ""))
            numeric.append(token)
        except ValueError:
            pass

    if not numeric:
        result.warnings.append("找不到圖形尺寸")
        return result

    if len(numeric) == 1:
        result.middle_top = float(numeric[0].text.replace(",", ""))
        return result

    xs = [token.center[0] for token in numeric]
    ys = [token.center[1] for token in numeric]
    mid_x = (min(xs) + max(xs)) / 2
    mid_y = (min(ys) + max(ys)) / 2
    x_span = max(xs) - min(xs) or 1.0
    y_span = max(ys) - min(ys) or 1.0

    for token in numeric:
        x, y = token.center
        try:
            val = float(token.text.replace(",", ""))
        except ValueError:
            continue
        vertical = "top" if y <= mid_y else "bottom"
        horizontal = "left" if x < mid_x else "right"
        if abs(x - mid_x) < x_span * SHAPE_CENTER_RATIO:
            key = "middle_top" if vertical == "top" else "middle_bottom"
        elif abs(y - mid_y) < y_span * SHAPE_CENTER_RATIO:
            key = f"{horizontal}_long"
        else:
            key = f"{horizontal}_{vertical}"
        if getattr(result, key) is None:
            setattr(result, key, val)

    if not is_stirrup:
        result.bird_mouth = None
    return result


def _segments_intersect(
    x1: float, y1: float, x2: float, y2: float,
    x3: float, y3: float, x4: float, y4: float,
) -> tuple[float, float] | None:
    """Return the intersection point of two line segments, or None if they don't intersect."""
    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(denom) < 1e-9:
        return None
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
    u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom
    if 0.0 <= t <= 1.0 and 0.0 <= u <= 1.0:
        ix = x1 + t * (x2 - x1)
        iy = y1 + t * (y2 - y1)
        return ix, iy
    return None


def row_is_crossed_out(image: Any, roi: tuple[int, int, int, int]) -> bool | None:
    """Detect a true X mark in a row ROI using geometric line validation.

    Returns ``True`` only when both a positive-slope and a negative-slope long
    line are found **and** they actually intersect within the ROI. Returns
    ``None`` when OpenCV is unavailable or the result is ambiguous (so callers
    can request human confirmation rather than silently dropping data).
    ``False`` means the ROI was analysed and no X was detected.

    OCR text containing ``X`` is irrelevant to this function.
    """

    try:
        import cv2
        import numpy as np
    except ImportError:
        return None
    if image is None:
        return None
    x1, y1, x2, y2 = roi
    crop = np.asarray(image)[y1:y2, x1:x2]
    if crop.size == 0:
        return None
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if len(crop.shape) == 3 else crop
    h, w = crop.shape[:2]
    min_dim = min(h, w)
    # Minimum line length: 30 % of the smaller ROI dimension
    min_line_len = max(10, int(min_dim * 0.30))

    edges = cv2.Canny(gray, 50, 150)
    lines = cv2.HoughLinesP(
        edges, 1, np.pi / 180,
        threshold=max(10, min_dim // 5),
        minLineLength=min_line_len,
        maxLineGap=max(5, min_dim // 10),
    )
    if lines is None:
        return False

    pos_slope: list[tuple[float, float, float, float]] = []  # negative image slope (↗)
    neg_slope: list[tuple[float, float, float, float]] = []  # positive image slope (↘)

    for line in lines[:, 0]:
        lx1, ly1, lx2, ly2 = float(line[0]), float(line[1]), float(line[2]), float(line[3])
        dx = lx2 - lx1
        dy = ly2 - ly1
        if abs(dx) < 1:
            continue
        slope = dy / dx
        # Must be a genuine diagonal: |slope| between 0.3 and 3.0
        if abs(slope) < 0.3 or abs(slope) > 3.0:
            continue
        if slope > 0:
            neg_slope.append((lx1, ly1, lx2, ly2))
        else:
            pos_slope.append((lx1, ly1, lx2, ly2))

    if not pos_slope or not neg_slope:
        return False

    # Check whether any positive-slope line intersects any negative-slope line
    # and whether the intersection point lies within the crop bounds
    for ps in pos_slope:
        for ns in neg_slope:
            pt = _segments_intersect(*ps, *ns)
            if pt is not None:
                ix, iy = pt
                if 0 <= ix <= w and 0 <= iy <= h:
                    return True
    # Lines found but no confirmed intersection inside ROI -> ambiguous
    return None
