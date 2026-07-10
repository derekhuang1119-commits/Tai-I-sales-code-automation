from pathlib import Path
from typing import Iterator


class PDFReader:
    """Local PDF reader. PyMuPDF is imported only when PDF operations are used."""

    def __init__(self, dpi: int = 200) -> None:
        self.dpi = dpi

    def extract_text(self, path: Path) -> Iterator[tuple[int, str]]:
        try:
            import fitz
        except ImportError as exc:
            raise RuntimeError("PyMuPDF is required for PDF processing") from exc
        with fitz.open(path) as document:
            for index, page in enumerate(document, 1):
                yield index, page.get_text("text")

    def render_pages(self, path: Path, output_dir: Path) -> Iterator[tuple[int, Path]]:
        try:
            import fitz
        except ImportError as exc:
            raise RuntimeError("PyMuPDF is required for PDF processing") from exc
        output_dir.mkdir(parents=True, exist_ok=True)
        scale = self.dpi / 72
        matrix = fitz.Matrix(scale, scale)
        with fitz.open(path) as document:
            for index, page in enumerate(document, 1):
                output = output_dir / f"{path.stem}-{index}.png"
                page.get_pixmap(matrix=matrix, alpha=False).save(output)
                yield index, output
