from rebar_converter.models import RebarItem
from rebar_converter.rules import RuleEngine


def test_rules_keep_steel_blank_and_clear_bird_beak_for_normal_shape() -> None:
    item = RebarItem(steel_grade="SD420", bar_number="#4", shape_type="一般成型料",
                     has_bird_beak=True, quantity="1", total_weight="2")
    result = RuleEngine().apply(item)
    assert result.steel_grade == ""
    assert result.bar_number == "4"
    assert not result.has_bird_beak
    assert result.quantity == "1"
    assert result.total_weight == "2"


def test_rules_use_middle_top_for_straight_bar_length() -> None:
    item = RebarItem(shape_type="直料", middle_top="300", quantity="1", total_weight="2")
    assert RuleEngine().apply(item).total_length == "300"
