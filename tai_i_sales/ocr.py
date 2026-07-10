"""Offline OCR interfaces and the PaddleOCR adapter."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from .models import OCRToken


class OCRBackend(Protocol):
    """Dependency-injection contract for an offline OCR implementation."""

    def recognize(self, image: Any, page_number: int) -> list[OCRToken]:
        """Recognize an image without sending it outside the local machine."""


class OCRModelUnavailable(RuntimeError):
    """Raised when the configured local OCR model cannot be loaded."""


class PaddleOCRBackend:
    """PaddleOCR adapter configured for local-only inference.

    PaddleOCR is imported lazily so parsing and tests remain usable without the
    optional model package. No network or telemetry mode is enabled.
    """

    def __init__(self, model_dir: str | Path | None = None, **kwargs: Any) -> None:
        self.model_dir = Path(model_dir) if model_dir else None
        try:
            from paddleocr import PaddleOCR
        except ImportError as exc:
            raise OCRModelUnavailable(
                "離線 OCR 模型未安裝。請安裝 paddleocr/paddlepaddle 並設定本機模型路徑。"
            ) from exc
        if self.model_dir and not self.model_dir.exists():
            raise OCRModelUnavailable(f"找不到本機 OCR 模型：{self.model_dir}")
        options = dict(kwargs)
        options.setdefault("use_doc_orientation_classify", False)
        options.setdefault("use_doc_unwarping", False)
        options.setdefault("use_textline_orientation", False)
        if self.model_dir:
            options.setdefault("text_detection_model_dir", str(self.model_dir))
            options.setdefault("text_recognition_model_dir", str(self.model_dir))
        try:
            self._ocr = PaddleOCR(**options)
        except Exception as exc:
            raise OCRModelUnavailable(f"無法載入本機離線 OCR 模型：{exc}") from exc

    def recognize(self, image: Any, page_number: int) -> list[OCRToken]:
        result = self._ocr.predict(image)
        tokens: list[OCRToken] = []
        for page in result:
            data = page if isinstance(page, dict) else getattr(page, "json", lambda: {})()
            data = data.get("res", data)
            polygons = data.get("rec_polys", data.get("dt_polys", []))
            texts = data.get("rec_texts", [])
            scores = data.get("rec_scores", [])
            for polygon, text, score in zip(polygons, texts, scores):
                tokens.append(OCRToken(str(text), float(score), tuple(tuple(p) for p in polygon), page_number))
        return tokens
