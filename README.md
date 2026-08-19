# 關稅政策消息監控爬蟲工具 (Tariff Policy News Monitoring Crawler Tool)

> 自動化持續監控國際財經新聞與官方政府公告中的關稅政策資訊，追蹤「美國 ↔ 台灣」與「美國 ↔ 中國」關鍵貿易動態。

---

## 🌟 核心特色

- **四大權威來源**：台灣經濟部國際貿易署、美國商務部 (U.S. Commerce)、路透社 (Reuters)、CNBC。
- **雙層智慧過濾**：關鍵字/國家前置規則過濾 + AI 語義分類與重複事件比對。
- **時間線生命週期 (Timeline)**：同一事件自動合併更新歷程，避免新聞重複洗版。
- **雙格式儲存**：核心結構化 JSON (`data/events.json`) + Excel 開啟不亂碼的 CSV (`data/events.csv`)。
- **GitHub Actions 自動化**：每 3 小時定時爬取、自動分析並 Commit 回存 GitHub。

---

## 📁 專案架構

```text
.
├── .github/workflows/monitor.yml   # 每 3 小時自動執行之 GitHub Actions 工作流
├── crawler/                        # 爬蟲模組 (CNBC, Reuters, Commerce, 國貿署)
├── filter/                         # 規則過濾與 AI / 語義分類去重模組
├── storage/                        # 事件生命週期與 JSON / CSV 同步管理
├── data/                           # 關稅事件資料庫 (events.json, events.csv)
├── tests/                          # 單元測試與整合驗證
├── main.py                         # 系統主程式入口
├── requirements.txt                # 依賴套件清單
├── PLAN.md                         # 專案開發規劃書
├── task.md                         # 任務清單與進度追蹤
├── memory.md                       # 開發紀錄與決策歷程
└── FINAL_PROJECT.md                # 期末專題成果報告
```

---

## 🚀 快速開始

### 1. 安裝套件
```bash
pip install -r requirements.txt
```

### 2. 執行爬蟲與監控管線
```bash
python main.py
```

### 3. 執行測試
```bash
pytest tests/ -v
```

---

## ⚙️ 環境變數設定 (選填)

若需使用 Google Gemini AI 進行雲端大模型深度判斷，可在環境變數或 GitHub Secrets 中設定：
- `GEMINI_API_KEY`: 您的 Gemini API Key（若未提供，系統會自動切換為內建高精度語義規則比對引擎）。
