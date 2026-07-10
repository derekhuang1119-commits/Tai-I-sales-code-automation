from pathlib import Path

from openpyxl import load_workbook

from rebar_converter.excel import ExcelWriter
from rebar_converter.models import RebarItem


def test_writer_creates_new_workbook(tmp_path: Path) -> None:
    output = tmp_path / "result.xlsx"
    ExcelWriter().write([RebarItem(region="A區", bar_number="4", quantity="2", total_weight="5")], output)
    sheet = load_workbook(output).active
    assert sheet["A2"].value == "A區"
    assert sheet["D2"].value == "4"
    assert sheet["O2"].value == "2"

