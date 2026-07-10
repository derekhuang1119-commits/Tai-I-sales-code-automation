from pathlib import Path

from rebar_converter.models import OCRText


class PaddleOCREngine:
    """Offline PaddleOCR adapter; network access is explicitly disabled."""

    def __init__(self, language: str = "ch", use_angle_cls: bool = True,
                 model_dir: Path | None = None) -> None:
        if model_dir is not None and not model_dir.exists():
            raise FileNotFoundError(f"本機 OCR 模型不存在: {model_dir}")
        try:
            from paddleocr import PaddleOCR
        except ImportError as exc:
            raise RuntimeError("PaddleOCR is required for image OCR") from exc
        options = {
            "lang": language,
            "use_angle_cls": use_angle_cls,
            "use_gpu": False,
            "show_log": False,
        }
        if model_dir is not None:
            options["det_model_dir"] = str(model_dir / "det")
            options["rec_model_dir"] = str(model_dir / "rec")
            options["cls_model_dir"] = str(model_dir / "cls")
        self._ocr = PaddleOCR(**options)

    def recognize(self, image_path: Path) -> list[OCRText]:
        result = self._ocr.ocr(str(image_path), cls=True)
        texts: list[OCRText] = []
        for page in result or []:
            for box, recognition in page or []:
                # Bounding boxes are retained by the backend for future layout analysis.
                _ = box
                text, score = recognition
                texts.append(OCRText(str(text), float(score)))
        return texts
