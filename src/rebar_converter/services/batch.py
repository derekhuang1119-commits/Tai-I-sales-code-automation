import logging
from pathlib import Path

from rebar_converter.excel import ExcelWriter
from rebar_converter.parsing import RebarParser
from rebar_converter.pdf import PDFReader
from rebar_converter.ocr import OCRBackend
from rebar_converter.rules import RuleEngine
from rebar_converter.shapes import ShapeAnalyzer

LOGGER = logging.getLogger(__name__)


class BatchProcessor:
    def __init__(self, reader: PDFReader | None = None, ocr: OCRBackend | None = None) -> None:
        self.reader = reader or PDFReader()
        self.parser = RebarParser()
        self.rules = RuleEngine()
        self.writer = ExcelWriter()
        self.shapes = ShapeAnalyzer()
        self.ocr = ocr

    def process(self, source: Path, output_dir: Path, template: Path | None = None) -> list[Path]:
        if source.is_dir():
            sources = sorted(
                path for path in source.iterdir()
                if path.suffix.lower() in {".pdf", ".png", ".jpg", ".jpeg"}
            )
        else:
            sources = [source]
        results: list[Path] = []
        for pdf in sources:
            try:
                items = []
                if pdf.suffix.lower() == ".pdf":
                    for page, text in self.reader.extract_text(pdf):
                        parsed = self.parser.parse(text, str(page))
                        items.extend(self.rules.apply_all([self.shapes.apply(item) for item in parsed]))
                elif self.ocr is None:
                    raise RuntimeError("Image sources require an offline OCR backend")
                else:
                    text = "\n".join(result.text for result in self.ocr.recognize(pdf))
                    items.extend(self.rules.apply_all(self.parser.parse(text)))
                output = output_dir / f"{pdf.stem}.xlsx"
                self.writer.write(items, output, template)
                results.append(output)
            except Exception:
                LOGGER.exception("處理失敗: %s", pdf)
        return results
