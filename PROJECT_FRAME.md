# PROJECT_FRAME.md — 項目框架定義

**版本**：v1.0  
**日期**：2026-06-26  
**上游參考**：`PRD.md` v1.0  

---

## 1. 技術棧

| 層級 | 技術 | 版本約束 | 用途 |
|------|------|---------|------|
| 語言 | Python | 3.11+ | 核心開發語言 |
| 套件管理 | uv | 0.4+ | 依賴管理、虛擬環境、CLI 入口 |
| CLI 框架 | Typer | 0.12+ | 指令解析、subcommand、option |
| UI 輸出 | Rich | 13+ | 表格、進度條、彩色輸出、Panel |
| 資料模型 | Pydantic | 2.x | YAML schema 驗證、型別安全 |
| K8s 通訊 | kubernetes (Python client) | 28+ | 直接與 kind cluster 通訊驗證答案 |
| 本地叢集 | kind | 0.20+ | Kubernetes in Docker（Lab 環境） |
| 容器執行期 | Docker | 20.10+ | kind 的底層依賴 |
| kubectl | kubectl | 1.28+ | setup/cleanup 指令執行 |

---

## 2. 目錄結構（完整）

```
ckad-practice/
├── AGENTS.md                  # 框架控制檔（唯一真相來源）
├── PRD.md                     # 產品需求文件
├── PROJECT_FRAME.md           # 本檔（項目框架）
├── FLOWS.md                   # 交互邏輯（Step 3 產出）
├── STATUS.md                  # 版本狀態記錄
├── CHANGELOG.md               # 變更日誌
├── ERRORS.md                  # 踩坑記錄
├── GATES.md                   # 驗收閘門規則
├── pyproject.toml             # 套件定義與 CLI 入口點
├── uv.lock                    # 鎖定依賴版本
│
├── kind/
│   ├── cluster-config.yaml    # kind cluster 設定（單控制節點）
│   ├── setup.sh               # 初始化腳本（create cluster + pip deps）
│   └── reset.sh               # 重製腳本（delete + create）
│
├── questions/                 # 題庫（YAML），依 CKAD domain 分資料夾
│   ├── 01-design-build/       # Application Design and Build (20%)
│   ├── 02-env-config/         # Environment, Configuration & Security (25%)
│   ├── 03-deployment/         # Application Deployment (20%)
│   ├── 04-services/           # Services and Networking (20%)
│   ├── 05-observability/      # Observability and Maintenance (15%)
│   ├── 06-misc/               # Miscellaneous
│   └── custom/                # 使用者自訂題目（自動掃描）
│
└── src/
    ├── main.py                # CLI 入口（Typer app + 所有 command 定義）
    ├── schema.py              # Pydantic 資料模型
    ├── loader.py              # 題目載入器
    ├── verifier.py            # 驗證引擎
    ├── scorer.py              # 計分模組
    ├── environment.py         # kind cluster 管理
    └── ui.py                  # Rich UI 元件
```

---

## 3. 模組定義與邊界

### 3.1 `schema.py` — 資料模型層（無外部 I/O）

**職責**：定義所有 Pydantic 模型，作為跨模組的資料契約。

```
模型清單：
- CheckRule        → verify[] 單條規則（type + 動態欄位）
- Question         → 完整題目（id, domain, weight, difficulty, title, prompt,
                     tips, setup[], verify[], cleanup[], sources[], tags[]）
- CheckResult      → 單條驗證結果（passed: bool, message: str）
- QuestionResult   → 單題練習結果（question, check_results[], score, max_score）
- SessionReport    → 整場練習報告（results[], total_score, max_score, pass: bool）
```

**邊界**：只定義型別，不執行任何 I/O 或業務邏輯。

---

### 3.2 `loader.py` — 題目載入層

**職責**：從 `questions/` 目錄掃描、解析 YAML，回傳 `list[Question]`。

```
函式：
- load_all() -> list[Question]
- load_by_id(id: str) -> Question | None
- load_by_domain(domain_num: int) -> list[Question]
- load_by_difficulty(level: str) -> list[Question]
- fetch_from_url(url: str, save: bool = False) -> list[Question]
```

**邊界**：只做 I/O 與解析，不做驗證邏輯。

---

### 3.3 `environment.py` — Lab 生命週期層

**職責**：封裝所有 kind cluster 操作。

```
函式：
- create(config_path: str = "kind/cluster-config.yaml") -> bool
- delete() -> bool
- reset() -> bool   # delete() → create()
- status() -> dict  # { exists: bool, nodes: list, kubeconfig: str }
```

**邊界**：僅呼叫 `subprocess`（kind / kubectl），不碰 kubernetes Python client。

---

### 3.4 `verifier.py` — 驗證引擎層

**職責**：接收 `Question`，對 kind cluster 執行所有 `CheckRule`，回傳 `list[CheckResult]`。

```
主入口：
- verify_question(question: Question, context: str = "kind-ckad") -> list[CheckResult]

內部 dispatcher（依 check_type 路由，共 23 種 CheckType）
```

**邊界**：只讀 cluster，不修改任何 K8s 資源。

---

### 3.5 `scorer.py` — 計分層（純函式）

```
函式：
- score_question(question, check_results) -> QuestionResult
- score_session(results: list[QuestionResult]) -> SessionReport
- is_passing(report: SessionReport, threshold: float = 0.66) -> bool
```

**邊界**：純函式，無 I/O，可單元測試。

---

### 3.6 `ui.py` — 呈現層

```
函式：
- print_question(question: Question)
- print_check_results(results: list[CheckResult])
- print_session_report(report: SessionReport)
- print_question_list(questions: list[Question])
- print_cluster_status(status: dict)
- prompt_continue() -> bool
```

**邊界**：只負責輸出，不呼叫任何 cluster 操作或驗證邏輯。

---

### 3.7 `main.py` — CLI 入口層（組合層）

```
Commands：
- app = typer.Typer()
- cluster_app = typer.Typer()   # cluster subcommand group

@cluster_app: create / delete / reset / status
@app:         practice / list / verify / fetch
```

**呼叫流程**（`practice` 為例）：
```
main.practice()
  → loader.load_all()
  → ui.print_question_list()
  → 逐題：
      subprocess 執行 setup cmds
      ui.print_question()
      [等待使用者操作 cluster]
      verifier.verify_question()
      scorer.score_question()
      ui.print_check_results()
      subprocess 執行 cleanup cmds
  → scorer.score_session()
  → ui.print_session_report()
```

---

## 4. 模組依賴圖

```
main.py
  ├── loader.py     ──► schema.py
  ├── verifier.py   ──► schema.py  (kubernetes client)
  ├── scorer.py     ──► schema.py
  ├── ui.py         ──► schema.py  (Rich)
  └── environment.py              (subprocess: kind, kubectl)
```

**核心約束**：
- `schema.py` 不依賴任何其他 src 模組
- `scorer.py` 純函式，無 I/O
- `verifier.py` 只讀 K8s，不寫
- `ui.py` 不依賴 kubernetes client

---

## 5. pyproject.toml 入口點

```toml
[project.scripts]
ckad = "src.main:app"
```

執行方式：`uv run ckad <command>`

---

## 6. API / Mock 決策（CLI 適配版）

> 本專案無 HTTP API，此節說明「外部依賴」的 Mock 策略。

| 外部依賴 | 生產模式 | 測試模式 |
|---------|---------|---------|
| kind cluster | 真實 kind | `--skip-verify` 跳過 |
| kubernetes Python client | 連接 `kind-ckad` context | Mock `kubernetes.client.*` |
| subprocess (kubectl/kind) | 真實執行 | Mock `subprocess.run` |
| GitHub fetch URL | 真實 HTTP | 本地 Markdown fixture |

**決策**：單元測試 mock 外部依賴；整合測試使用真實 kind cluster。

---

## 7. 開發優先順序

| 優先 | 模組 | 原因 |
|------|------|------|
| 1 | `schema.py` | 所有模組的資料契約，必須最先定義 |
| 2 | `environment.py` | Lab 生命週期（使用者最高優先需求） |
| 3 | `main.py` 骨架 | CLI 可執行、cluster subcommand 可用 |
| 4 | `loader.py` | 題目載入，practice 前置 |
| 5 | `verifier.py` | 驗證引擎，最複雜的核心邏輯 |
| 6 | `scorer.py` | 純函式，依賴 verifier 輸出 |
| 7 | `ui.py` | 呈現層，最後整合 |

---

## 8. kind cluster 規格

```yaml
# kind/cluster-config.yaml
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
name: ckad
nodes:
  - role: control-plane
```

- Cluster 名稱：`ckad`
- kubectl context：`kind-ckad`（kind 自動產生）
- 單節點，足夠 CKAD 所有練習場景

---

## 9. 非功能約束確認

| 約束 | 實作方式 |
|------|---------|
| 環境隔離 | 每題 setup/cleanup 自動執行 |
| 離線可用 | 僅需本地 Docker，不依賴外部 SaaS |
| 快速重置 | `kind delete` + `kind create` < 2 分鐘 |
| 可擴充題庫 | `questions/custom/` 自動掃描 |
| 跳過驗證模式 | `--skip-verify` flag |
