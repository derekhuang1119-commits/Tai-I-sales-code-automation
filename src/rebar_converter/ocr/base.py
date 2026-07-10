from pathlib import Path
from typing import Protocol

from rebar_converter.models import OCRText


class OCRBackend(Protocol):
    def recognize(self, image_path: Path) -> list[OCRText]:
        ...

