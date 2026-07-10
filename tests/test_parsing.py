from rebar_converter.parsing import RebarParser, parse_bar_number, parse_page_number


def test_parse_bar_and_page_number() -> None:
    assert parse_bar_number("#4") == "4"
    assert parse_page_number("右下角 3-2") == "2"


def test_parser_extracts_basic_fields_and_review() -> None:
    item = RebarParser().parse("A區\n號數：#4\n長度：120\n支數：2\n總重：15\n頁碼 3-1")[0]
    assert (item.region, item.bar_number, item.total_length, item.page) == ("A區", "4", "120", "1")
    assert not item.needs_review


def test_parser_marks_crossed_out_and_handwritten() -> None:
    item = RebarParser().parse("A區\n號數 #4\n手寫修改 X 劃掉")[0]
    assert item.excluded
    assert item.needs_review


def test_parser_parse_lines_accepts_iterable() -> None:
    items = RebarParser().parse_lines(["A區", "支數：1", "總重：2"])
    assert len(items) == 1
    assert items[0].quantity == "1"
