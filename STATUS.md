# STATUS.md — 專案狀態快照

**更新日期**：2026-06-26  
**版本**：v0.1.0（開發完成，未正式發布）

---

## 整體進度

| 步驟 | 名稱 | 狀態 | 完成日期 |
|------|------|------|---------|
| Step 1 | PRD 規劃 | ✅ 完成 | 2026-06-26 |
| Step 2 | 項目框架 | ✅ 完成 | 2026-06-26 |
| Step 3 | 交互邏輯 | ✅ 完成 | 2026-06-26 |
| Step 4 | 前端交接包 | ➖ 跳過（純 CLI，無前端） | — |
| Step 5 | 專業編碼 | ✅ 完成 | 2026-06-26 |
| Step 6 | 項目記錄 | ✅ 完成 | 2026-06-26 |
| Step 7 | 驗收閘門 | ⬜ 待完成 | — |

---

## 模組完成狀態

| 模組 | 檔案 | 狀態 | 備註 |
|------|------|------|------|
| 資料模型 | `src/schema.py` | ✅ 完成 | 23 CheckType，Pydantic v2 |
| 題目載入 | `src/loader.py` | ✅ 完成 | 65 題，YAML 解析，fetch 功能 |
| 驗證引擎 | `src/verifier.py` | ✅ 完成 | 23 dispatcher，已修復 404 錯誤訊息 |
| 計分模組 | `src/scorer.py` | ✅ 完成 | 純函式，weight × 通過率 |
| UI 元件 | `src/ui.py` | ✅ 完成 | Rich Panel/Table/Timer |
| Lab 管理 | `src/environment.py` | ✅ 完成 | kind create/delete/reset/status |
| CLI 入口 | `src/main.py` | ✅ 完成 | 5 commands，Typer |

---

## 題庫狀態

| Domain | 資料夾 | 題數 |
|--------|--------|------|
| Application Design and Build | `01-design-build/` | 15 題 |
| Environment, Configuration & Security | `02-env-config/` | 16 題 |
| Application Deployment | `03-deployment/` | 10 題 |
| Services and Networking | `04-services/` | 8 題 |
| Observability and Maintenance | `05-observability/` | 12 題 |
| Miscellaneous | `06-misc/` | 4 題 |
| **合計** | | **65 題** |

---

## 整合測試結果（2026-06-26）

| 測試項目 | 結果 |
|---------|------|
| `bash kind/setup.sh` — 3 節點 kind cluster 建立 | ✅ |
| `ckad cluster status` — 節點全 Ready | ✅ |
| `ckad list` — 65 題正常載入 | ✅ |
| `ckad verify <id>` — 資源不存在時訊息乾淨 | ✅ |
| `ckad verify <id>` — 資源存在時 4/4 checks 全過 | ✅ |
| `bash kind/reset.sh` — 刪除重建完成時間 < 2 分鐘 | ✅ |

---

## 已知問題

| 編號 | 描述 | 嚴重度 | 狀態 |
|------|------|--------|------|
| — | 無已知問題 | — | — |

---

## 下一步

- **Step 7**：撰寫 `GATES.md` 與 `check.sh`，執行自動化驗收測試
