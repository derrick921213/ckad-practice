# CHANGELOG.md

本檔依 [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) 格式撰寫，版本號遵循 [Semantic Versioning](https://semver.org/spec/v2.0.0.html)。

---

## [Unreleased]

## [0.1.0] — 2026-06-26

### Added
- **PRD.md**：產品需求文件，定義 6 大功能區塊、65 題目標、技術棧與 YAML schema
- **PROJECT_FRAME.md**：項目框架，7 模組邊界定義、依賴圖、API/Mock 決策
- **FLOWS.md**：交互邏輯，Flow A–E 完整流程圖、7 狀態機、錯誤處理原則
- **`src/schema.py`**：Pydantic v2 資料模型；`Domain`(6)、`Difficulty`(3)、`CheckType`(23) enums；`VerifyCheck`、`Question`、`QuestionSource` models
- **`src/environment.py`**：kind cluster 生命週期管理（`create_cluster`、`delete_cluster`、`reset_cluster`、`get_cluster_info`、`apply_setup_commands`、`apply_cleanup_commands`）
- **`src/loader.py`**：YAML 題目載入器（`load_all`、`load_by_id`、`load_from_github`、`save_question`）
- **`src/verifier.py`**：23 CheckType 驗證引擎（`run_checks`、`_DISPATCH` table、`load_k8s_config`）
- **`src/scorer.py`**：計分模組（`QuestionResult`、`SessionResult` dataclasses；weight × 通過率計算；66% 及格線）
- **`src/ui.py`**：Rich UI 元件（`show_banner`、`show_question`、`show_check_results`、`show_session_summary`、`show_cluster_status`、`wait_with_live_timer`）
- **`src/main.py`**：Typer CLI 入口，5 commands：`practice`、`list`、`verify`、`fetch`、`cluster`（含 create/delete/reset/status 子指令）
- **`kind/cluster-config.yaml`**：3 節點 kind cluster（1 control-plane + 2 worker；ingress-ready 標籤；port 8080→80、8443→443）
- **`kind/setup.sh`**：初始化腳本（依賴檢查、cluster 建立、Metrics Server + Contour 安裝、`uv sync`）
- **`kind/reset.sh`**：重製腳本（確認提示、delete + create + 元件安裝）
- **`questions/`**：65 道 CKAD 練習題，分布於 6 個 domain 資料夾
- **`pyproject.toml`**：uv 專案設定，CLI 入口 `ckad = "src.main:app"`

### Fixed
- **`src/verifier.py`**：`_check_pod_running`、`_check_pod_image`、`_check_pod_label` 在資源不存在（HTTP 404）時，原本回傳完整 HTTP response headers（含 audit-id、body），修正為簡潔訊息（例：`Pod 'pod-1' 不存在於 default`）
- **`src/verifier.py`**：其餘所有 check 函式的 `except ApiException` 由 `str(e)` 改為 `f"API 錯誤 {e.status}: {e.reason}"`，統一錯誤訊息格式

### Changed
- 無

### Removed
- 無
