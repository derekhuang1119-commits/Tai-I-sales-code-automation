"""Command-line entry point for offline batch conversion."""

import argparse

from .batch import BatchProcessor
from .ocr import PaddleOCRBackend


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("destination")
    parser.add_argument("--region", required=True)
    parser.add_argument("--model-dir")
    args = parser.parse_args()
    backend = PaddleOCRBackend(args.model_dir)
    BatchProcessor(backend).export(args.source, args.destination, args.region)
