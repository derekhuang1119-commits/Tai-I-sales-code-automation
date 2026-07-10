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

    Supports both the legacy ``ocr(...)`` / ``__call__`` API (PaddleOCR ≤ 2.6)
    and the newer ``predict(...)`` API (PaddleOCR ≥ 2.7). The method is chosen
    at runtime to avoid ``AttributeError`` on either version.
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

    def _call_ocr(self, image: Any) -> Any:
        """Call the OCR engine using whichever API is available."""
        if hasattr(self._ocr, "predict"):
            return self._ocr.predict(image)
        # Legacy API: __call__ / ocr()
        return self._ocr(image, cls=False)

    def _parse_predict_result(self, result: Any, page_number: int) -> list[OCRToken]:
        """Parse the result from the predict() API (PaddleOCR ≥ 2.7)."""
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

    def _parse_legacy_result(self, result: Any, page_number: int) -> list[OCRToken]:
        """Parse the result from the legacy ocr() API (PaddleOCR ≤ 2.6).

        Legacy format: list of lines, each line is ``[polygon, (text, score)]``.
        """
        tokens: list[OCRToken] = []
        if result is None:
            return tokens
        for line_group in result:
            if line_group is None:
                continue
            for line in line_group:
                if not (isinstance(line, (list, tuple)) and len(line) == 2):
                    continue
                polygon_raw, text_score = line
                if not (isinstance(text_score, (list, tuple)) and len(text_score) == 2):
                    continue
                text, score = text_score
                try:
                    poly = tuple(tuple(p) for p in polygon_raw)
                    tokens.append(OCRToken(str(text), float(score), poly, page_number))
                except Exception:
                    continue
        return tokens

    def recognize(self, image: Any, page_number: int) -> list[OCRToken]:
        result = self._call_ocr(image)
        # Determine which result format was returned
        if hasattr(self._ocr, "predict"):
            return self._parse_predict_result(result, page_number)
        return self._parse_legacy_result(result, page_number)
