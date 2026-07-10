"""Batch orchestration with explicit OCR dependency injection."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .excel import write_excel
from .ingest import load_source
from .models import BarItem, PageOCR
from .ocr import OCRBackend
from .parsing import detect_region, page_marker_number, parse_row, row_rois
from .shape import analyze_shape, row_is_crossed_out


def _detect_table_lines(image: Any) -> tuple[list[float], list[float]]:
    """Detect horizontal and vertical table lines using OpenCV.

    Returns ``(h_lines, v_lines)`` as lists of y-coordinates and x-coordinates
    respectively. Falls back to empty lists when OpenCV is not available.
    """
    try:
        import cv2
        import numpy as np
    except ImportError:
        return [], []
    if image is None:
        return [], []
    arr = np.asarray(image)
    gray = cv2.cvtColor(arr, cv2.COLOR_BGR2GRAY) if len(arr.shape) == 3 else arr
    h, w = gray.shape[:2]
    # Detect long horizontal lines (spanning > 40 % of width)
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(1, w // 3), 1))
    h_mask = cv2.morphologyEx(255 - gray, cv2.MORPH_OPEN, h_kernel)
    h_contours, _ = cv2.findContours(h_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    h_lines = sorted({int(cv2.boundingRect(c)[1] + cv2.boundingRect(c)[3] / 2)
                      for c in h_contours if cv2.boundingRect(c)[2] > w * 0.4})
    # Detect long vertical lines (spanning > 20 % of height)
    v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(1, h // 5)))
    v_mask = cv2.morphologyEx(255 - gray, cv2.MORPH_OPEN, v_kernel)
    v_contours, _ = cv2.findContours(v_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    v_lines = sorted({int(cv2.boundingRect(c)[0] + cv2.boundingRect(c)[2] / 2)
                      for c in v_contours if cv2.boundingRect(c)[3] > h * 0.2})
    return h_lines, v_lines


def _row_image_roi(
    image: Any, y_lines: list[float], row_index: int
) -> tuple[int, int, int, int] | None:
    """Return pixel bounding box (x1, y1, x2, y2) for a table row."""
    if image is None or len(y_lines) < 2:
        return None
    import numpy as np
    arr = np.asarray(image)
    h, w = arr.shape[:2]
    if row_index >= len(y_lines) - 1:
        return None
    y1 = max(0, int(y_lines[row_index]))
    y2 = min(h, int(y_lines[row_index + 1]))
    return (0, y1, w, y2)


def _crop_image(image: Any, roi: tuple[int, int, int, int]) -> Any:
    """Crop a numpy/PIL image to the given (x1, y1, x2, y2) ROI."""
    if image is None:
        return None
    try:
        import numpy as np
        arr = np.asarray(image)
        x1, y1, x2, y2 = roi
        return arr[y1:y2, x1:x2]
    except Exception:
        return None


def _col_bounds_from_v_lines(
    v_lines: list[float],
) -> dict[str, tuple[float, float]]:
    """Map standard column names to x-ranges from detected vertical lines.

    Column order assumption (from left to right):
      0  bar_number (號數)
      1  shape drawing (成型圖) — not mapped here
      2  total_length (總長)
      3  quantity (支數)
      4  total_weight (總重)

    Returns an empty dict when fewer than 4 vertical lines are detected.
    """
    if len(v_lines) < 5:
        return {}
    xs = v_lines
    # Estimate total_weight right boundary as extending one extra column width to
    # the right of xs[4], using the previous column's width as a reference.
    weight_right = xs[4] + (xs[4] - xs[3]) * 2
    return {
        "bar_number": (xs[0], xs[1]),
        # xs[1]..xs[2] is the shape/drawing column — handled separately
        "total_length": (xs[2], xs[3]),
        "quantity": (xs[3], xs[4]),
        "total_weight": (xs[4], weight_right),
    }


def _shape_col_roi(
    v_lines: list[float], row_roi: tuple[int, int, int, int] | None
) -> tuple[int, int, int, int] | None:
    """Return pixel bounding box of the shape/drawing column within a row ROI."""
    if len(v_lines) < 3 or row_roi is None:
        return None
    x1, y1, x2, y2 = row_roi
    return (int(v_lines[1]), y1, int(v_lines[2]), y2)


class BatchProcessor:
    """Convert sources after an OCR backend has explicitly been configured."""

    def __init__(self, ocr_backend: OCRBackend | None) -> None:
        if ocr_backend is None:
            raise ValueError("必須注入離線 OCR backend，不可使用沒有 OCR 的 BatchProcessor。")
        self.ocr_backend = ocr_backend

    def extract(self, source: str | Path, region: str = "") -> list[BarItem]:
        """Extract BarItems from a source file with shape analysis and X detection."""
        items: list[BarItem] = []
        for page in load_source(source, self.ocr_backend):
            page_number = page_marker_number(page)
            if page_number is None:
                # Cannot determine page number from marker — flag for review
                page_number_for_item: int | None = None
                needs_page_review = True
            else:
                page_number_for_item = page_number
                needs_page_review = False

            # Auto-detect region if not supplied
            effective_region = region or detect_region(page) or ""

            h_lines, v_lines = _detect_table_lines(page.image)
            col_bounds = _col_bounds_from_v_lines(v_lines)

            row_token_groups = row_rois(page, h_lines)
            for row_index, tokens in enumerate(row_token_groups):
                if not tokens:
                    continue

                row_roi = _row_image_roi(page.image, h_lines, row_index)
                row_img = _crop_image(page.image, row_roi) if row_roi else None

                # Step 1: crossed-out detection on the full row crop
                if row_img is not None:
                    img_h, img_w = row_img.shape[:2]
                    full_roi = (0, 0, img_w, img_h)
                else:
                    full_roi = (0, 0, 0, 0)
                crossed = row_is_crossed_out(row_img, full_roi)

                item = parse_row(
                    tokens,
                    region=effective_region,
                    page_number=page_number_for_item,
                    col_bounds=col_bounds if col_bounds else None,
                )
                item.source_page = page
                item.source_roi = row_roi

                if needs_page_review:
                    item.needs_review = True
                    item.warnings.append("無法從右下角辨識頁數，需人工確認")

                # Step 2: shape analysis on shape-column ROI only
                shape_roi = _shape_col_roi(v_lines, row_roi)
                if shape_roi is not None:
                    shape_tokens = [
                        t for t in tokens
                        if shape_roi[0] <= t.center[0] < shape_roi[2]
                    ]
                else:
                    # No column detection available — use all tokens not matching
                    # numeric fields; heuristic: exclude the rightmost N tokens
                    shape_tokens = tokens

                item.shape = analyze_shape(shape_tokens)

                # Step 3: apply crossout result
                if crossed is True:
                    item.excluded = True
                elif crossed is None:
                    item.needs_review = True
                    item.warnings.append("打X偵測結果不確定，需人工確認")

                items.append(item)
        return items

    def export(
        self,
        source: str | Path,
        destination: str | Path,
        region: str = "",
        template: str | Path | None = None,
    ) -> Path:
        """Extract items and write them to an Excel file."""
        return write_excel(self.extract(source, region), destination, template=template)
