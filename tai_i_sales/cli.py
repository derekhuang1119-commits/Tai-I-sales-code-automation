"""Command-line entry point for offline batch conversion."""

import argparse

from .batch import BatchProcessor
from .ocr import PaddleOCRBackend


def main() -> None:
    parser = argparse.ArgumentParser(description="離線鋼筋料單 PDF/JPG/PNG → Excel 轉換")
    parser.add_argument("source", help="來源 PDF/JPG/PNG 檔案")
    parser.add_argument("destination", help="輸出 Excel 路徑")
    parser.add_argument("--region", default="", help="區域名稱（如 A區、北區）")
    parser.add_argument("--template", default=None, help="Excel 範本路徑")
    parser.add_argument("--model-dir", default=None, help="本機 PaddleOCR 模型目錄")
    args = parser.parse_args()
    backend = PaddleOCRBackend(args.model_dir)
    BatchProcessor(backend).export(
        args.source, args.destination, args.region, template=args.template
    )

