"""Desktop application entry point for packaged Windows builds."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from tai_i_sales.gui import run_review_gui
from tai_i_sales.ocr import OCRModelUnavailable, PaddleOCRBackend


def _default_model_dir() -> Path:
    """Return the model directory next to the executable or source tree."""
    if getattr(sys, "frozen", False):
        base_dir = Path(sys.executable).resolve().parent
    else:
        base_dir = Path(__file__).resolve().parent.parent
    return base_dir / "models"


def main() -> None:
    """Launch the offline review GUI using a local OCR model directory."""
    parser = argparse.ArgumentParser(description="離線鋼筋料單確認工具")
    parser.add_argument(
        "--model-dir",
        type=Path,
        default=Path(os.environ.get("TAI_I_SALES_MODEL_DIR", _default_model_dir())),
        help="本機 PaddleOCR 模型目錄；預設為執行檔旁的 models 資料夾",
    )
    args = parser.parse_args()
    try:
        backend = PaddleOCRBackend(args.model_dir)
    except OCRModelUnavailable as exc:
        try:
            from PySide6.QtWidgets import QApplication, QMessageBox
        except ImportError:
            raise RuntimeError(str(exc)) from exc
        app = QApplication.instance() or QApplication([])
        QMessageBox.critical(
            None,
            "OCR 模型錯誤",
            f"{exc}\n\n請使用 --model-dir 或 TAI_I_SALES_MODEL_DIR 指定本機模型。",
        )
        sys.exit(1)
    run_review_gui(backend)


if __name__ == "__main__":
    main()
