"""Batch orchestration with explicit OCR dependency injection."""

from pathlib import Path

from .excel import write_excel
from .ingest import load_source
from .models import BarItem
from .ocr import OCRBackend
from .parsing import page_marker_number, parse_row, row_rois


class BatchProcessor:
    """Convert sources after an OCR backend has explicitly been configured."""

    def __init__(self, ocr_backend: OCRBackend | None) -> None:
        if ocr_backend is None:
            raise ValueError("必須注入離線 OCR backend，不可使用沒有 OCR 的 BatchProcessor。")
        self.ocr_backend = ocr_backend

    def extract(self, source: str | Path, region: str = "") -> list[BarItem]:
        items: list[BarItem] = []
        for page in load_source(source, self.ocr_backend):
            page_number = page_marker_number(page) or page.page_number
            for tokens in row_rois(page):
                if tokens:
                    item = parse_row(tokens, region=region, page_number=page_number)
                    item.source_page = page
                    items.append(item)
        return items

    def export(self, source: str | Path, destination: str | Path, region: str = "") -> Path:
        return write_excel(self.extract(source, region), destination)
