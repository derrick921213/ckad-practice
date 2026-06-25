# GATES.md — 驗收閘門

**版本**：v1.0  
**日期**：2026-06-26  
**執行方式**：`bash check.sh`  
**通過條件**：靜態 Gate（G1–G6）全部 PASS，動態 Gate（G7–G8）需 kind cluster 運行

---

## 靜態驗收（不需 cluster）

### G1 — 依賴工具安裝

| 檢查項目 | 指令 / 條件 |
|---------|-----------|
| kind 已安裝 | `kind version` 退出碼 0 |
| kubectl 已安裝 | `kubectl version --client` 退出碼 0 |
| docker 已安裝 | `docker info` 退出碼 0 |
| uv 已安裝 | `uv --version` 退出碼 0 |
| Python >= 3.11 | `python3 --version` 主版本 ≥ 3，次版本 ≥ 11 |

---

### G2 — Python 模組導入

所有 6 個 src 模組必須在 `uv run python` 環境下無錯誤導入：

| 模組 | 期望結果 |
|------|---------|
| `schema` | 無 ImportError |
| `loader` | 無 ImportError |
| `verifier` | 無 ImportError |
| `scorer` | 無 ImportError |
| `environment` | 無 ImportError |
| `ui` | 無 ImportError |

---

### G3 — CheckType + dispatch 完整性

| 檢查項目 | 期望值 |
|---------|--------|
| `schema.CheckType` 定義值數量 | **23** |
| `verifier._DISPATCH` key 數量 | **23** |
| `_DISPATCH` 與 `CheckType` 完全一致（無遺漏） | OK（無缺失 key） |

---

### G4 — 題庫完整性

| 檢查項目 | 期望值 |
|---------|--------|
| `loader.load_all()` 回傳題目數 | **>= 65** |
| 所有題目 `id` 唯一（無重複） | OK |
| 所有題目 `weight` 介於 1–30 | OK |
| 所有題目具有至少 1 條 `verify[]` 規則 | OK |

---

### G5 — 計分純函式邏輯

以 `weight=10` 的題目、2 條 check 為基準：

| 測試情境 | 期望 `score` |
|---------|-------------|
| 2/2 checks 通過 | `10.0` |
| 1/2 checks 通過 | `5.0` |
| 0/2 checks 通過 | `0.0` |
| `SessionResult.percentage`（1 題 10/10） | `100.0` |

---

### G6 — CLI 基本運作

| 指令 | 期望結果 |
|------|---------|
| `uv run ckad --help` | 退出碼 0 |
| `uv run ckad list --help` | 退出碼 0 |
| `uv run ckad practice --help` | 退出碼 0 |
| `uv run ckad verify --help` | 退出碼 0 |
| `uv run ckad fetch --help` | 退出碼 0 |
| `uv run ckad list`（無 flag） | 輸出行數 >= 65，最後一行含「道題目」 |

---

## 動態驗收（需 kind cluster 運行）

> 執行 `bash kind/setup.sh` 建立 cluster 後可測試。
> cluster 不存在時，G7–G8 自動標記為 `SKIP`（不計入 FAIL）。

### G7 — Cluster 狀態

| 檢查項目 | 期望結果 |
|---------|---------|
| `ckad cluster status` 退出碼 | 0 |
| 輸出包含 cluster 名稱 "ckad" | 是 |
| `kubectl get nodes --context kind-ckad` 節點數 | >= 3 |

---

### G8 — verifier 404 訊息格式（ERR-001 回歸防護）

| 檢查項目 | 期望結果 |
|---------|---------|
| `ckad verify 01-02` 在資源不存在時輸出 | 不含 `audit-id`、`Content-Type`、`application/json` 等 HTTP 字串 |

> 此 Gate 為 ERR-001（verifier 詳細 HTTP 錯誤訊息）的回歸測試，確保修復不被意外還原。

---

## 評分

| 類別 | Gate | 必須通過 |
|------|------|---------|
| 靜態 | G1–G6 | ✅ 強制 |
| 動態 | G7–G8 | ⚠️ 選擇性（SKIP 不算失敗） |
