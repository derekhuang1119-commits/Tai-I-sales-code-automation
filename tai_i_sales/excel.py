"""Excel template mapping by header title rather than fixed column numbers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import BarItem


HEADERS = {
    "region": "區域", "page_number": "頁數", "bar_number": "號數",
    "total_length": "總長", "quantity": "支數", "total_weight": "總重",
    "steel_grade": "鋼種",
}
REQUIRED_FIELDS = ("region", "bar_number", "total_length", "quantity", "total_weight")


def write_excel(items: list[BarItem], destination: str | Path, template: Any = None) -> Path:
    """Write rows beneath matching Chinese headers and validate required data."""

    try:
        from openpyxl import Workbook, load_workbook
    except ImportError as exc:
        raise RuntimeError("Excel 支援需要安裝 openpyxl。") from exc
    workbook = load_workbook(template) if template else Workbook()
    sheet = workbook.active
    if template is None and sheet.max_row == 1 and all(cell.value is None for cell in sheet[1]):
        for column, title in enumerate(HEADERS.values(), 1):
            sheet.cell(row=1, column=column, value=title)
    headers = {cell.value: cell.column for cell in sheet[1] if cell.value}
    for title in HEADERS.values():
        if title not in headers:
            raise ValueError(f"Excel 範本缺少欄位標題：{title}")
    for item in items:
        if item.excluded:
            continue
        missing = [HEADERS[key] for key in REQUIRED_FIELDS if not getattr(item, key)]
        if missing:
            raise ValueError(f"料件缺少必要欄位：{', '.join(missing)}")
        row = sheet.max_row + 1
        values = {**{key: getattr(item, key) for key in HEADERS}, "page_number": item.page_number}
        for key, title in HEADERS.items():
            sheet.cell(row=row, column=headers[title], value=values[key])
    path = Path(destination)
    workbook.save(path)
    return path
