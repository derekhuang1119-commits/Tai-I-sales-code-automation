"""Optional PySide6 review window; business logic remains GUI-independent."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .batch import BatchProcessor
from .excel import HEADERS, write_excel
from .models import BarItem
from .ocr import OCRBackend, OCRModelUnavailable, PaddleOCRBackend

# Human-readable column labels matching HEADERS order
_FIELD_LABELS = list(HEADERS.values())
_FIELD_KEYS = list(HEADERS.keys())
# Fields sourced from item.shape rather than item
_SHAPE_FIELDS = frozenset({
    "left_top", "left_long", "left_bottom",
    "middle_top", "middle_bottom",
    "right_top", "right_long", "right_bottom",
    "bird_mouth",
})


def _get_field(item: BarItem, key: str) -> Any:
    if key in _SHAPE_FIELDS:
        return getattr(item.shape, key, None)
    return getattr(item, key, None)


def _set_field(item: BarItem, key: str, value: Any) -> None:
    if key in _SHAPE_FIELDS:
        setattr(item.shape, key, value)
    else:
        setattr(item, key, value)


def _coerce_field(key: str, text: str) -> Any:
    """Convert GUI text to the correct Python type for the given field key."""
    if text == "" or text is None:
        return None
    if key == "page_number":
        try:
            return int(text)
        except ValueError:
            return None
    if key == "quantity":
        try:
            return int(text)
        except ValueError:
            return None
    if key == "bar_number" or key == "region" or key == "steel_grade":
        return text.lstrip("#") if key == "bar_number" else text
    # Numeric dimension fields
    numeric_keys = {
        "total_length", "total_weight",
        "left_top", "left_long", "left_bottom",
        "middle_top", "middle_bottom",
        "right_top", "right_long", "right_bottom",
        "bird_mouth",
    }
    if key in numeric_keys:
        try:
            return float(text.replace(",", ""))
        except ValueError:
            return None
    return text


def _review_window_class():
    """Build the optional Qt class without importing PySide6 in core code."""

    from PySide6.QtCore import Qt
    from PySide6.QtGui import QImage, QPixmap
    from PySide6.QtWidgets import (
        QCheckBox, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
        QPushButton, QSplitter, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
    )

    class ReviewWindow(QWidget):
        """Two-pane review screen: item list with ROI images + editable field table."""

        def __init__(self, items: list[BarItem]):
            super().__init__()
            self.items = items

            # Left: list of items
            self.item_list = QListWidget()
            self.item_list.currentRowChanged.connect(self._on_row_selected)

            # Right top: ROI image
            self.image_label = QLabel("料件圖片")
            self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.image_label.setMinimumHeight(150)

            # Right middle: editable table
            self.table = QTableWidget(1, len(_FIELD_KEYS))
            self.table.setHorizontalHeaderLabels(_FIELD_LABELS)
            self.table.horizontalHeader().setStretchLastSection(True)

            # Right bottom: buttons
            self.exclude_btn = QPushButton("排除此筆")
            self.restore_btn = QPushButton("恢復此筆")
            self.exclude_btn.clicked.connect(self._on_exclude)
            self.restore_btn.clicked.connect(self._on_restore)
            btn_row = QHBoxLayout()
            btn_row.addWidget(self.exclude_btn)
            btn_row.addWidget(self.restore_btn)

            right = QVBoxLayout()
            right.addWidget(self.image_label, 1)
            right.addWidget(self.table, 2)
            right.addLayout(btn_row)

            right_widget = QWidget()
            right_widget.setLayout(right)

            splitter = QSplitter(Qt.Orientation.Horizontal)
            splitter.addWidget(self.item_list)
            splitter.addWidget(right_widget)
            splitter.setStretchFactor(0, 1)
            splitter.setStretchFactor(1, 3)

            outer = QVBoxLayout(self)
            outer.addWidget(splitter)

            self._populate_list()
            if self.items:
                self.item_list.setCurrentRow(0)

        def _populate_list(self) -> None:
            self.item_list.clear()
            for i, item in enumerate(self.items):
                label = f"{'[排除] ' if item.excluded else ''}{'[審查] ' if item.needs_review else ''}#{item.bar_number or i + 1}"
                list_item = QListWidgetItem(label)
                self.item_list.addItem(list_item)

        def _on_row_selected(self, row: int) -> None:
            if row < 0 or row >= len(self.items):
                return
            self._save_current_row()
            self._current_row = row
            item = self.items[row]
            # Load ROI image
            roi_img = self._get_roi_image(item)
            if roi_img is not None:
                self.image_label.setPixmap(roi_img)
            else:
                self.image_label.setText("無圖片")
            # Populate fields
            for col, key in enumerate(_FIELD_KEYS):
                val = _get_field(item, key)
                cell = QTableWidgetItem("" if val is None else str(val))
                if item.confidence.get(key, 1.0) < 0.8:
                    cell.setBackground(Qt.GlobalColor.yellow)
                self.table.setItem(0, col, cell)

        def _save_current_row(self) -> None:
            if not hasattr(self, "_current_row"):
                return
            row = getattr(self, "_current_row", -1)
            if row < 0 or row >= len(self.items):
                return
            item = self.items[row]
            for col, key in enumerate(_FIELD_KEYS):
                cell = self.table.item(0, col)
                text = cell.text() if cell is not None else ""
                _set_field(item, key, _coerce_field(key, text))

        def _get_roi_image(self, item: BarItem) -> "QPixmap | None":
            try:
                import numpy as np
                from PySide6.QtGui import QImage, QPixmap
            except ImportError:
                return None
            # Prefer source_roi crop from source_page.image
            if item.source_page and item.source_page.image is not None and item.source_roi:
                img = item.source_page.image
                x1, y1, x2, y2 = item.source_roi
                try:
                    arr = np.asarray(img)[y1:y2, x1:x2]
                    if arr.size == 0:
                        return None
                    if len(arr.shape) == 2:
                        arr = np.stack([arr] * 3, axis=-1)
                    h, w = arr.shape[:2]
                    data = arr.tobytes()
                    qimg = QImage(data, w, h, w * 3, QImage.Format.Format_RGB888)
                    return QPixmap.fromImage(qimg)
                except Exception:
                    pass
            # Fall back to full page image
            if item.source_page and item.source_page.image is not None:
                src = item.source_page.image
                try:
                    if hasattr(src, "toqimage"):
                        qimage = src.toqimage()
                    else:
                        src = src.convert("RGB")
                        raw = src.tobytes("raw", "RGB")
                        qimage = QImage(raw, src.width, src.height, QImage.Format.Format_RGB888)
                    return QPixmap.fromImage(qimage)
                except Exception:
                    pass
            return None

        def _on_exclude(self) -> None:
            row = getattr(self, "_current_row", -1)
            if 0 <= row < len(self.items):
                self.items[row].excluded = True
                self._populate_list()

        def _on_restore(self) -> None:
            row = getattr(self, "_current_row", -1)
            if 0 <= row < len(self.items):
                self.items[row].excluded = False
                self._populate_list()

        def apply_edits(self) -> None:
            """Flush the currently displayed row's edits back to the item list."""
            self._save_current_row()

    return ReviewWindow


def run_review_gui(ocr_backend: OCRBackend | None = None) -> None:
    """Launch the full review GUI with file selection and complete workflow.

    The host application does **not** need to call apply_edits() or
    write_excel() separately; the GUI handles both on confirmation.
    """

    try:
        from PySide6.QtWidgets import (
            QApplication, QFileDialog, QInputDialog, QMainWindow,
            QMessageBox, QPushButton, QStatusBar, QVBoxLayout, QWidget,
        )
    except ImportError as exc:
        raise RuntimeError("GUI 支援需要安裝 PySide6。") from exc

    app = QApplication.instance() or QApplication([])

    if ocr_backend is None:
        try:
            ocr_backend = PaddleOCRBackend()
        except OCRModelUnavailable as exc:
            window = QMainWindow()
            QMessageBox.critical(window, "OCR 模型錯誤", str(exc))
            window.setWindowTitle("離線鋼筋料單確認")
            window.show()
            app.exec()
            return

    ReviewWindow = _review_window_class()

    class MainWindow(QMainWindow):
        """Full-workflow main window: select → recognise → review → export."""

        def __init__(self, backend: OCRBackend) -> None:
            super().__init__()
            self.backend = backend
            self.processor = BatchProcessor(backend)
            self._items: list[BarItem] = []
            self._template: str | None = None
            self._output: str | None = None
            self._review_widget: Any = None

            self.status_bar = QStatusBar()
            self.setStatusBar(self.status_bar)
            self.setWindowTitle("離線鋼筋料單確認")
            self.resize(1100, 700)

            # --- toolbar buttons ---
            self._btn_open = QPushButton("選擇 PDF/JPG/PNG…")
            self._btn_template = QPushButton("選擇 Excel 範本…")
            self._btn_output = QPushButton("選擇輸出檔…")
            self._btn_region = QPushButton("輸入/確認區域…")
            self._btn_start = QPushButton("▶ 開始辨識")
            self._btn_save = QPushButton("✔ 確認並輸出 Excel")

            self._btn_open.clicked.connect(self._select_source)
            self._btn_template.clicked.connect(self._select_template)
            self._btn_output.clicked.connect(self._select_output)
            self._btn_region.clicked.connect(self._input_region)
            self._btn_start.clicked.connect(self._start_recognition)
            self._btn_save.clicked.connect(self._save_excel)

            toolbar = QWidget()
            tb_layout = QVBoxLayout(toolbar)
            for btn in [self._btn_open, self._btn_template, self._btn_output,
                        self._btn_region, self._btn_start, self._btn_save]:
                tb_layout.addWidget(btn)
            tb_layout.addStretch()

            self._central = QWidget()
            self._layout = QVBoxLayout(self._central)
            self.setCentralWidget(self._central)

            from PySide6.QtWidgets import QSplitter
            from PySide6.QtCore import Qt
            self._splitter = QSplitter(Qt.Orientation.Horizontal)
            self._splitter.addWidget(toolbar)
            review_placeholder = QWidget()
            self._splitter.addWidget(review_placeholder)
            self._splitter.setStretchFactor(0, 0)
            self._splitter.setStretchFactor(1, 1)
            self._layout.addWidget(self._splitter)

            self._source: str | None = None
            self._region: str = ""
            self.status_bar.showMessage("請選擇來源檔案、範本及輸出路徑。")

        def _select_source(self) -> None:
            path, _ = QFileDialog.getOpenFileName(
                self, "選擇料單檔案", "", "支援格式 (*.pdf *.jpg *.jpeg *.png)")
            if path:
                self._source = path
                self.status_bar.showMessage(f"來源：{path}")

        def _select_template(self) -> None:
            path, _ = QFileDialog.getOpenFileName(
                self, "選擇 Excel 範本", "", "Excel 活頁簿 (*.xlsx *.xls)")
            if path:
                self._template = path
                self.status_bar.showMessage(f"範本：{path}")

        def _select_output(self) -> None:
            path, _ = QFileDialog.getSaveFileName(
                self, "儲存輸出 Excel", "", "Excel 活頁簿 (*.xlsx)")
            if path:
                self._output = path
                self.status_bar.showMessage(f"輸出：{path}")

        def _input_region(self) -> None:
            text, ok = QInputDialog.getText(self, "輸入區域", "區域名稱（如 A區、北區）：",
                                            text=self._region)
            if ok:
                self._region = text.strip()
                self.status_bar.showMessage(f"區域：{self._region}")

        def _start_recognition(self) -> None:
            if not self._source:
                QMessageBox.warning(self, "缺少來源", "請先選擇 PDF/JPG/PNG 檔案。")
                return
            self.status_bar.showMessage("辨識中，請稍候…")
            try:
                self._items = self.processor.extract(self._source, self._region)
            except Exception as exc:
                QMessageBox.critical(self, "辨識錯誤", str(exc))
                self.status_bar.showMessage("辨識失敗。")
                return
            # Replace the placeholder with the review widget
            review = ReviewWindow(self._items)
            self._review_widget = review
            old = self._splitter.widget(1)
            self._splitter.replaceWidget(1, review)
            old.deleteLater()
            self._splitter.setStretchFactor(1, 1)
            self.status_bar.showMessage(f"辨識完成，共 {len(self._items)} 筆料件。")

        def _save_excel(self) -> None:
            if not self._output:
                self._output, _ = QFileDialog.getSaveFileName(
                    self, "儲存輸出 Excel", "", "Excel 活頁簿 (*.xlsx)")
                if not self._output:
                    QMessageBox.warning(self, "缺少輸出路徑", "請先選擇輸出檔案路徑。")
                    return
            if self._review_widget is not None:
                self._review_widget.apply_edits()
            try:
                write_excel(self._items, self._output, template=self._template)
                QMessageBox.information(self, "完成", f"已輸出至：{self._output}")
                self.status_bar.showMessage(f"已儲存：{self._output}")
            except Exception as exc:
                QMessageBox.critical(self, "輸出錯誤", str(exc))
                self.status_bar.showMessage("輸出失敗。")

    window = MainWindow(ocr_backend)
    window.show()
    app.exec()
