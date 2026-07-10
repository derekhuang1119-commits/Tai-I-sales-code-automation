# 離線鋼筋料單轉 Excel MVP

本工具在本機以注入的 OCR backend 處理 PDF、JPG、PNG，保留 OCR 的文字、
頁碼、polygon、bbox 與信心度，再將料件寫入 Excel。掃描 PDF 文字不足
20 字時會以 300 DPI render，並使用同一個 PaddleOCR backend；不會上傳
文件或使用 telemetry。

## 安裝與使用

```bash
python -m pip install -e ".[dev]"
python -m pip install -e ".[ocr]"
python -m pytest -q
python -m tai_i_sales.cli input.pdf output.xlsx --region 北區 --model-dir C:\models\paddle
```

`PaddleOCRBackend` 必須使用本機模型；模型不存在或無法載入時會顯示明確
錯誤。GUI 可由應用程式呼叫 `tai_i_sales.gui.run_review_gui(backend)`，
提供左側圖片、右側可編輯欄位、低信心黃色標示，以及恢復排除列的功能。

目前限制：表格線偵測與複雜手寫/鳥嘴圖形仍需要針對現場表單校正；GUI 的
確認結果尚未包含專用的儲存按鈕，應由宿主程式在 `apply_edits()` 後呼叫
`write_excel()`。測試使用合成 OCR、圖片與 PDF fixture，不包含模型或客戶資料。
