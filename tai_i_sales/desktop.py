"""Desktop application entry point for packaged Windows builds."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from tai_i_sales.gui import run_review_gui
from tai_i_sales.ocr import PaddleOCRBackend


def _default_model_dir() -> Path:
    """Return the model directory next to the executable or source tree."""
    base_dir = Path(sys.executable).resolve().parent if getattr(
        sys, "frozen", False
    ) else Path(__file__).resolve().parent.parent
    return base_dir / "models"


def main() -> None:
    """Launch the offline review GUI using a local OCR model directory."""
    parser = argparse.ArgumentParser(description="離線鋼筋料單確認工具")
    parser.add_argument(
        "--model-dir",
        default=os.environ.get("TAI_I_SALES_MODEL_DIR", str(_default_model_dir())),
        help="本機 PaddleOCR 模型目錄；預設為執行檔旁的 models 資料夾",
    )
    args = parser.parse_args()
    run_review_gui(PaddleOCRBackend(args.model_dir))


if __name__ == "__main__":
    main()
