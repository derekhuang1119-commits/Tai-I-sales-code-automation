# 離線鋼筋料單 PDF 轉 Excel

這是完全離線執行的 MVP。PDF、圖片、OCR 結果只會在本機處理；專案不包含雲端 OCR、外部 API、遙測、客戶檔案或 OCR 模型。

## 安裝與執行

需要 Python 3.11 或 3.12。建議在 Windows 虛擬環境執行：

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m rebar_converter.gui.app
```

PaddleOCR 的模型需預先下載到本機環境，首次使用前請依 PaddleOCR 版本將模型快取準備在本機；程式不會上傳任何資料。

GUI 可選擇單一 PDF/圖片或資料夾、Excel 範本及輸出資料夾。範本不會被覆寫，結果會產生新的 `.xlsx`。目前 OCR 後的欄位解析是可替換的基本文字解析器；複雜圖形與手寫修正需在預覽中人工確認。

## 測試與打包

```bat
pytest
build.bat
```

MVP 已涵蓋文字型 PDF、基本欄位規則、頁碼/號數解析、範本寫入與批次處理。掃描件與手機照片需要本機 PaddleOCR 模型；圖形尺寸的自動定位及手寫 X/修改辨識仍是下一步。

