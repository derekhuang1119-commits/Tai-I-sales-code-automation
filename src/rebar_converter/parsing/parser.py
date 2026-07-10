import re
from typing import Iterable

from rebar_converter.models import RebarItem

REVIEW_CONFIDENCE_THRESHOLD = 0.8


def parse_bar_number(value: str) -> str:
    """Return a bar number without the drawing marker."""
    return re.sub(r"^\s*#", "", value).strip()


def parse_page_number(value: str) -> str:
    """Extract the page after the final dash in a drawing page marker."""
    match = re.search(r"(\d+)\s*-\s*(\d+)", value)
    return match.group(2) if match else ""


class RebarParser:
    """Conservative parser for text extracted from common rebar schedules."""

    _field_patterns = {
        "region": r"(?:區域|區)\s*[:：]?\s*([A-Za-zＡ-Ｚａ-ｚ０-９]+區?)",
        "bar_number": r"(?:號數|號)\s*[:：]?\s*(#?\s*[A-Za-z0-9]+)",
        "total_length": r"(?:總長|長度)\s*[:：]?\s*([\d.,]+)",
        "quantity": r"(?:支數|數量|支)\s*[:：]?\s*([\d.,]+)",
        "total_weight": r"(?:總重|重量)\s*[:：]?\s*([\d.,]+)",
    }

    def parse(self, text: str, page_hint: str = "") -> list[RebarItem]:
        blocks = [block.strip() for block in re.split(r"\n\s*\n", text) if block.strip()]
        if not blocks:
            return []
        return [self._parse_block(block, page_hint) for block in blocks]

    def _parse_block(self, block: str, page_hint: str) -> RebarItem:
        item = RebarItem(raw_text=block)
        for field_name, pattern in self._field_patterns.items():
            match = re.search(pattern, block, re.IGNORECASE)
            if match:
                setattr(item, field_name, match.group(1).replace(",", ""))
        if not item.region:
            match = re.search(r"(?m)^\s*([A-Za-zＡ-Ｚａ-ｚ]\s*區)\s*$", block)
            if match:
                item.region = match.group(1).replace(" ", "")
        item.bar_number = parse_bar_number(item.bar_number)
        item.page = parse_page_number(block) or page_hint
        item.steel_grade = ""
        item.shape_type = "箍筋" if re.search(r"箍筋|箍", block) else "一般成型料"
        item.has_bird_beak = item.shape_type == "箍筋" and bool(
            re.search(r"鳥嘴|鸟嘴|bird\s*beak", block, re.IGNORECASE)
        )
        if re.search(r"(?:手寫\s*)?X|劃掉|划掉", block, re.IGNORECASE):
            item.excluded = True
            item.warnings.append("疑似整筆料件被劃掉")
        item.confidence = 0.7 if re.search(r"手寫|修改", block) else 1.0
        item.needs_review = (
            item.confidence < REVIEW_CONFIDENCE_THRESHOLD
            or not item.quantity
            or not item.total_weight
        )
        if item.needs_review:
            item.warnings.append("欄位不足或信心度偏低，請人工確認")
        return item

    def parse_lines(self, lines: Iterable[str], page_hint: str = "") -> list[RebarItem]:
        return self.parse("\n".join(lines), page_hint)
