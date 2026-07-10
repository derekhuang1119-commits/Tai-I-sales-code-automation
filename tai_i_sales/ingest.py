"""PDF and image input, including the scanned-PDF OCR fallback."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from .models import OCRToken, PageOCR
from .ocr import OCRBackend

TEXT_THRESHOLD = 20
RENDER_DPI = 300


def _image_size(image: Any) -> tuple[int, int]:
    return tuple(getattr(image, "size", (0, 0)))  # type: ignore[return-value]


def image_to_page(image: Any, backend: OCRBackend, page_number: int = 1) -> PageOCR:
    """Run the injected offline backend for a JPG/PNG image."""

    width, height = _image_size(image)
    return PageOCR(page_number, width, height, backend.recognize(image, page_number), image)


def pdf_to_pages(
    path: str | Path,
    backend: OCRBackend,
    *,
    text_threshold: int = TEXT_THRESHOLD,
    pdf_open: Callable[[str], Any] | None = None,
) -> list[PageOCR]:
    """Extract a PDF and OCR pages whose extracted text is below the threshold.

    Scanned pages are rendered at exactly 300 DPI and then sent through the
    same backend used by image files.
    """

    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError("PDF 支援需要安裝 PyMuPDF。") from exc
    document = pdf_open(str(path)) if pdf_open else fitz.open(str(path))
    pages: list[PageOCR] = []
    for index, pdf_page in enumerate(document):
        raw_text = pdf_page.get_text("text")
        if len(raw_text.strip()) >= text_threshold:
            rect = pdf_page.rect
            tokens = []
            for word in pdf_page.get_text("words"):
                x0, y0, x1, y1, text = word[:5]
                tokens.append(OCRToken(str(text), 1.0, ((x0, y0), (x1, y0), (x1, y1), (x0, y1)), index + 1))
            if not tokens:
                polygon = ((0, 0), (rect.width, 0), (rect.width, rect.height), (0, rect.height))
                tokens = [OCRToken(raw_text.strip(), 1.0, polygon, index + 1)]
            pages.append(PageOCR(index + 1, int(rect.width), int(rect.height), tokens))
            continue
        zoom = RENDER_DPI / 72
        pixmap = pdf_page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
        try:
            from PIL import Image
            import io
            image = Image.open(io.BytesIO(pixmap.tobytes("png")))
        except ImportError as exc:
            raise RuntimeError("掃描 PDF OCR 需要安裝 Pillow。") from exc
        page = image_to_page(image, backend, index + 1)
        page.used_ocr_fallback = True
        pages.append(page)
    return pages


def load_source(path: str | Path, backend: OCRBackend) -> list[PageOCR]:
    """Load PDF/JPG/PNG through the appropriate offline path."""

    source = Path(path)
    if source.suffix.lower() == ".pdf":
        return pdf_to_pages(source, backend)
    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("圖片支援需要安裝 Pillow。") from exc
    with Image.open(source) as image:
        return [image_to_page(image.copy(), backend)]
