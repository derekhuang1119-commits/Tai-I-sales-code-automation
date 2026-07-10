import re

from rebar_converter.models import RebarItem


class ShapeAnalyzer:
    """Extracts explicitly labelled dimensions without inferring missing values."""

    _labels = {
        "左上": "left_top", "左長": "left_long", "左下": "left_bottom",
        "中上": "middle_top", "中下": "middle_bottom", "右上": "right_top",
        "右長": "right_long", "右下": "right_bottom",
    }

    def apply(self, item: RebarItem) -> RebarItem:
        for label, field in self._labels.items():
            match = re.search(rf"{label}\s*[:：]?\s*([\d.,]+)", item.raw_text)
            if match:
                setattr(item, field, match.group(1).replace(",", ""))
        return item
