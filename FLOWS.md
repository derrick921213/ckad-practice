# FLOWS.md — 交互邏輯定義

**版本**：v1.0  
**日期**：2026-06-26  
**上游參考**：`PRD.md` v1.0, `PROJECT_FRAME.md` v1.0  

---

## 1. CLI 頂層指令樹

```
ckad
├── practice   [--domain] [--difficulty] [--id] [--skip-verify] [--context]
├── list       [--domain] [--difficulty]
├── verify     <id>
├── fetch      <url> [--save]
└── cluster
    ├── create
    ├── delete
    ├── reset
    └── status
```

---

## 2. Flow A — Lab 生命週期（cluster 子指令）

### A1. `ckad cluster create`

```
[START]
  │
  ▼
檢查 Docker 是否執行中
  ├── NO  → 印出錯誤「請先啟動 Docker」→ [EXIT 1]
  └── YES ▼
檢查 kind cluster "ckad" 是否已存在
  ├── YES → 印出警告「cluster 已存在，請先執行 delete 或 reset」→ [EXIT 1]
  └── NO  ▼
執行 kind create cluster --config kind/cluster-config.yaml --name ckad
  ├── FAIL → 印出錯誤訊息 → [EXIT 1]
  └── OK  ▼
印出成功訊息 + kubectl context 提示（kind-ckad）
  │
[EXIT 0]
```

### A2. `ckad cluster delete`

```
[START]
  │
  ▼
檢查 kind cluster "ckad" 是否存在
  ├── NO  → 印出「cluster 不存在，略過」→ [EXIT 0]
  └── YES ▼
詢問確認：「確定要刪除 ckad cluster？[y/N]」
  ├── N   → 取消 → [EXIT 0]
  └── Y   ▼
執行 kind delete cluster --name ckad
  ├── FAIL → 印出錯誤 → [EXIT 1]
  └── OK  ▼
印出成功訊息
  │
[EXIT 0]
```

### A3. `ckad cluster reset`

```
[START]
  │
  ▼
印出「重製中：先刪除再重建...」
  │
  ▼
執行 delete 流程（跳過確認提示，直接刪除）
  ├── FAIL → [EXIT 1]
  └── OK  ▼
執行 create 流程
  ├── FAIL → [EXIT 1]
  └── OK  ▼
印出「重製完成」
  │
[EXIT 0]
```

### A4. `ckad cluster status`

```
[START]
  │
  ▼
執行 kind get clusters
  ├── "ckad" 不在列表 → 印出 Panel「cluster: 未建立」→ [EXIT 0]
  └── 存在 ▼
執行 kubectl cluster-info --context kind-ckad
執行 kubectl get nodes --context kind-ckad
  │
  ▼
印出 Rich Panel：
  - cluster 名稱、狀態（Running / NotReady）
  - 節點清單 + 角色 + 狀態
  - kubeconfig context 名稱
  │
[EXIT 0]
```

---

## 3. Flow B — 互動練習（`ckad practice`）

```
[START]
  │
  ▼
（若無 --skip-verify）檢查 cluster 是否存在
  ├── NO  → 詢問「cluster 不存在，是否建立？[Y/n]」
  │         ├── Y → 執行 create → 繼續
  │         └── N → [EXIT 1]
  └── YES ▼
依 options 篩選題目（--domain / --difficulty / --id）
  ├── 結果為空 → 「找不到符合條件的題目」→ [EXIT 0]
  └── 有題目 ▼
印出題目清單（Rich Table）+ 題數摘要
詢問「開始練習？[Y/n]」
  ├── N → [EXIT 0]
  └── Y ▼
  │
  ▼
╔══════════════════════════════╗
║   逐題迴圈（每題流程如下）   ║
╚══════════════════════════════╝
  │
  ▼
執行 setup[] 指令（subprocess，逐條執行）
  ├── 任一失敗 → 印出警告「setup 失敗，跳過本題」→ 執行 cleanup → 下一題
  └── 全部成功 ▼
印出題目 Panel（id, domain, difficulty, weight, prompt, tips）
印出「完成後按 Enter 驗證，輸入 s 跳過，輸入 q 結束」
  │
  ├── [q] → 執行 cleanup → 跳出迴圈 → 印出報告
  ├── [s] → 記錄「跳過」→ 執行 cleanup → 下一題
  └── [Enter] ▼
（若有 --skip-verify）→ 記錄「略過驗證」→ 執行 cleanup → 下一題
（正常模式）↓
執行 verify_question()（kubernetes client 讀取 cluster）
印出 CheckResult 表格（✅/❌ 每條規則）
score_question() → 印出單題得分
執行 cleanup[] 指令（逐條執行，失敗僅警告不中斷）
詢問「繼續下一題？[Y/n]」
  ├── N → 跳出迴圈
  └── Y → 下一題
  │
  ▼
score_session() → 印出總分報告
  - 總分 / 滿分 / 百分比
  - 是否達 CKAD 及格線（66%）
  - 逐題明細表格
  │
[EXIT 0]
```

---

## 4. Flow C — 列出題目（`ckad list`）

```
[START]
  │
  ▼
load_all()，依 options 篩選（--domain / --difficulty）
  ├── 結果為空 → 「無符合題目」→ [EXIT 0]
  └── 有結果 ▼
印出 Rich Table：
  columns: ID | Domain | Difficulty | Weight | Title
  依 domain → id 排序
  │
[EXIT 0]
```

---

## 5. Flow D — 單題驗證（`ckad verify <id>`）

```
[START]
  │
  ▼
load_by_id(id)
  ├── 找不到 → 「題目 <id> 不存在」→ [EXIT 1]
  └── 找到 ▼
檢查 cluster 是否存在
  ├── NO → 「cluster 未建立，請執行 ckad cluster create」→ [EXIT 1]
  └── YES ▼
verify_question()
score_question()
印出 CheckResult 表格 + 單題得分
  │
[EXIT 0]
```

---

## 6. Flow E — 匯入題目（`ckad fetch <url>`）

```
[START]
  │
  ▼
驗證 URL 格式（必須為 https://raw.githubusercontent.com/...）
  ├── 格式錯誤 → 「僅支援 GitHub Raw URL」→ [EXIT 1]
  └── OK ▼
HTTP GET url
  ├── 失敗 → 「無法取得內容，請確認 URL 與網路」→ [EXIT 1]
  └── 成功 ▼
解析 Markdown（jamesbuckett 格式）→ list[Question]
  ├── 解析失敗 / 0 題 → 「無法識別格式，請確認來源格式」→ [EXIT 1]
  └── 有題目 ▼
印出解析結果預覽（題目清單）
（若有 --save）→ 寫入 questions/custom/<filename>.yaml
  印出「已儲存至 questions/custom/」
（若無 --save）→ 僅顯示預覽，不儲存
  │
[EXIT 0]
```

---

## 7. 狀態機 — 練習 Session

```
          ┌──────────────┐
          │   IDLE       │  （程式未執行）
          └──────┬───────┘
                 │ ckad practice
                 ▼
          ┌──────────────┐
          │  CHECKING    │  （檢查 cluster 狀態）
          └──────┬───────┘
                 │ cluster OK
                 ▼
          ┌──────────────┐
          │  SELECTING   │  （篩選題目、顯示清單）
          └──────┬───────┘
                 │ 使用者確認開始
                 ▼
          ┌──────────────┐
    ┌────►│  SETUP       │  （執行題目 setup[]）
    │     └──────┬───────┘
    │            │ setup 成功
    │            ▼
    │     ┌──────────────┐
    │     │  WAITING     │  （顯示題目，等待使用者操作 cluster）
    │     └──────┬───────┘
    │            │ Enter / s / q
    │            ▼
    │     ┌──────────────┐
    │     │  VERIFYING   │  （執行 verify + score）
    │     └──────┬───────┘
    │            │ 完成
    │            ▼
    │     ┌──────────────┐
    │     │  CLEANUP     │  （執行題目 cleanup[]）
    │     └──────┬───────┘
    │            │ 有下一題 & 使用者繼續
    └────────────┘
                 │ 無下一題 / 使用者結束
                 ▼
          ┌──────────────┐
          │  REPORTING   │  （印出總分報告）
          └──────┬───────┘
                 │
                 ▼
          ┌──────────────┐
          │   IDLE       │
          └──────────────┘
```

---

## 8. 錯誤處理原則

| 場景 | 行為 |
|------|------|
| Docker 未啟動 | 立即中止，印出明確錯誤 |
| cluster 不存在（practice） | 詢問是否建立，不強制退出 |
| setup 指令失敗 | 警告 + 跳過本題，繼續下一題 |
| cleanup 指令失敗 | 僅警告，不中斷流程 |
| verify 連線失敗 | 印出錯誤，該 check 記為 FAIL |
| 題目 YAML 格式錯誤 | 載入時跳過並警告，不影響其他題目 |
| 使用者 Ctrl+C | 執行當前題 cleanup，印出部分報告後退出 |
