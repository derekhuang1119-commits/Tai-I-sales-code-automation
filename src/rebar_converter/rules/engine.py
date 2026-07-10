from rebar_converter.models import RebarItem


class RuleEngine:
    """Applies business rules without making uncertain guesses."""

    def apply(self, item: RebarItem) -> RebarItem:
        item.steel_grade = ""
        item.bar_number = item.bar_number.removeprefix("#").strip()
        if item.shape_type in {"直料", "straight"} and item.middle_top and not item.total_length:
            item.total_length = item.middle_top
        if item.shape_type != "箍筋":
            item.has_bird_beak = False
        if item.has_bird_beak and "鳥嘴" not in item.warnings:
            item.warnings.append("箍筋含鳥嘴")
        item.needs_review = item.needs_review or not item.quantity or not item.total_weight
        return item

    def apply_all(self, items: list[RebarItem]) -> list[RebarItem]:
        return [self.apply(item) for item in items if not item.excluded]

