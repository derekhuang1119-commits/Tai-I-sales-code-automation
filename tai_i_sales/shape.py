"""Geometry-aware shape classification and crossed-out row detection."""

from __future__ import annotations

from typing import Any

from .models import OCRToken, ShapeAnalysis


def analyze_shape(tokens: list[OCRToken], *, is_stirrup: bool = False) -> ShapeAnalysis:
    """Assign numeric labels to the nearest of eight drawing regions."""

    result = ShapeAnalysis(is_stirrup=is_stirrup)
    numeric = [token for token in tokens if any(char.isdigit() for char in token.text)]
    if not numeric:
        result.warnings.append("找不到圖形尺寸")
        return result
    if len(numeric) == 1:
        result.middle_top = numeric[0].text
        return result
    xs = [token.center[0] for token in numeric]
    ys = [token.center[1] for token in numeric]
    mid_x, mid_y = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    for token in numeric:
        x, y = token.center
        vertical = "top" if y <= mid_y else "bottom"
        horizontal = "left" if x < mid_x else "right"
        if abs(x - mid_x) < (max(xs) - min(xs)) * 0.2:
            key = "middle_top" if vertical == "top" else "middle_bottom"
        elif abs(y - mid_y) < (max(ys) - min(ys)) * 0.2:
            key = f"{horizontal}_long"
        else:
            key = f"{horizontal}_{vertical}"
        if not getattr(result, key):
            setattr(result, key, token.text)
    if not is_stirrup:
        result.bird_mouth = ""
    return result


def row_is_crossed_out(image: Any, roi: tuple[int, int, int, int]) -> bool | None:
    """Detect crossed lines in a row ROI; text containing ``X`` is irrelevant.

    Returns ``None`` when OpenCV is unavailable or the image is ambiguous so
    callers can request human confirmation rather than silently dropping data.
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
    edges = cv2.Canny(gray, 50, 150)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=max(10, min(crop.shape[:2]) // 5),
                             minLineLength=max(10, min(crop.shape[:2]) // 2), maxLineGap=5)
    if lines is None:
        return False
    diagonals = []
    for line in lines[:, 0]:
        dx, dy = line[2] - line[0], line[3] - line[1]
        if abs(dx) > 0 and abs(dy) > 0 and abs(dy / dx) > 0.25:
            diagonals.append(line)
    return len(diagonals) >= 2
