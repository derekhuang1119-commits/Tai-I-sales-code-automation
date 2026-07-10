import sys
from pathlib import Path

from rebar_converter.services import BatchProcessor


def main() -> int:
    try:
        from PySide6.QtWidgets import QApplication, QFileDialog, QLabel, QMainWindow, QPushButton, QVBoxLayout, QWidget
    except ImportError as exc:
        raise RuntimeError("PySide6 is required to run the GUI") from exc

    class Window(QMainWindow):
        def __init__(self) -> None:
            super().__init__()
            self.setWindowTitle("離線鋼筋料單轉 Excel")
            self.status = QLabel("請選擇 PDF/圖片或資料夾")
            button = QPushButton("選擇來源、範本並轉換")
            button.clicked.connect(self.convert)
            layout = QVBoxLayout()
            layout.addWidget(self.status)
            layout.addWidget(button)
            container = QWidget()
            container.setLayout(layout)
            self.setCentralWidget(container)

        def convert(self) -> None:
            source_dir = QFileDialog.getExistingDirectory(self, "選擇 PDF/圖片資料夾")
            source_path = source_dir
            if not source_path:
                source_file, _ = QFileDialog.getOpenFileName(
                    self, "選擇 PDF", filter="PDF (*.pdf)"
                )
                source_path = source_file
            if not source_path:
                return
            template, _ = QFileDialog.getOpenFileName(self, "選擇 Excel 範本（可取消）",
                                                      filter="Excel (*.xlsx)")
            output = QFileDialog.getExistingDirectory(self, "選擇輸出資料夾")
            if output:
                count = len(BatchProcessor().process(
                    Path(source_path), Path(output), Path(template) if template else None))
                self.status.setText(f"完成 {count} 個檔案；低信心欄位請人工確認")

    application = QApplication(sys.argv)
    window = Window()
    window.resize(420, 160)
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
