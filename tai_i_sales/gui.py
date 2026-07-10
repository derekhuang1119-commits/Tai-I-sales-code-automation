"""Optional PySide6 review window; business logic remains GUI-independent."""

from __future__ import annotations

from .batch import BatchProcessor
from .models import BarItem
from .ocr import OCRBackend, OCRModelUnavailable, PaddleOCRBackend


def _review_window_class():
    """Build the optional Qt class without importing PySide6 in core code."""

    from PySide6.QtCore import Qt
    from PySide6.QtGui import QPixmap
    from PySide6.QtWidgets import (
        QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
    )

    class ReviewWindow(QWidget):
        """Two-pane review screen with editable values and row restoration."""

        fields = ["region", "page_number", "bar_number", "total_length", "quantity", "total_weight", "steel_grade"]

        def __init__(self, items: list[BarItem]):
            super().__init__()
            self.items = items
            self.image = QLabel("料件圖片")
            self.image.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table = QTableWidget(len(items), len(self.fields))
            self.table.setHorizontalHeaderLabels(["區域", "頁數", "號數", "總長", "支數", "總重", "鋼種"])
            self.restore = QPushButton("恢復排除項目")
            self.restore.clicked.connect(self.restore_excluded)
            layout = QHBoxLayout(self)
            layout.addWidget(self.image, 1)
            right = QVBoxLayout()
            right.addWidget(self.table)
            right.addWidget(self.restore)
            layout.addLayout(right, 2)
            self.populate()

        def populate(self) -> None:
            for row, item in enumerate(self.items):
                for col, field in enumerate(self.fields):
                    cell = QTableWidgetItem("" if getattr(item, field) is None else str(getattr(item, field)))
                    if item.confidence.get(field, 1.0) < 0.8:
                        cell.setBackground(Qt.GlobalColor.yellow)
                    self.table.setItem(row, col, cell)
                if item.excluded:
                    self.table.setRowHidden(row, True)
            if self.items and self.items[0].source_page and self.items[0].source_page.image:
                self.image.setPixmap(QPixmap.fromImage(self.items[0].source_page.image.toqimage()))

        def restore_excluded(self) -> None:
            for row, item in enumerate(self.items):
                item.excluded = False
                self.table.setRowHidden(row, False)

        def apply_edits(self) -> None:
            for row, item in enumerate(self.items):
                for col, field in enumerate(self.fields):
                    value = self.table.item(row, col).text()
                    setattr(item, field, int(value) if field == "page_number" and value else value)

    return ReviewWindow


def run_review_gui(ocr_backend: OCRBackend | None = None) -> None:
    """Launch the review UI with an injected local OCR backend."""

    try:
        from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox, QStatusBar
    except ImportError as exc:
        raise RuntimeError("GUI 支援需要安裝 PySide6。") from exc
    app = QApplication.instance() or QApplication([])
    window = QMainWindow()
    window.setWindowTitle("離線鋼筋料單確認")
    window.setCentralWidget(_review_window_class()([]))
    if ocr_backend is None:
        try:
            ocr_backend = PaddleOCRBackend()
        except OCRModelUnavailable as exc:
            QMessageBox.critical(window, "OCR 模型錯誤", str(exc))
    if ocr_backend is not None:
        status_bar = QStatusBar()
        window.setStatusBar(status_bar)
        status_bar.showMessage("已載入離線 OCR；低信心欄位需人工確認")
        window.status_bar = status_bar
        window.ocr_backend = ocr_backend
        window.batch_processor = BatchProcessor(ocr_backend)
    window.resize(900, 500)
    window.show()
    app.exec()
