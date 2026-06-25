# PRD — CKAD Practice Lab System

**版本**：v1.0  
**日期**：2026-06-26  
**作者**：Derrick  

---

## 1. 產品概述

本地 Kubernetes 練習評分系統，使用 **Python + kind + Docker** 建立隔離的 K8s 練習環境。使用者可透過 CLI 開啟 Lab、銷毀環境、或重製回初始狀態，並自動驗證練習答案計分。

**目標族群**：備考 CKAD 認證的工程師

---

## 2. 核心功能需求

### 2.1 Lab 生命週期管理（最高優先）

| 功能 | 指令 | 說明 |
|------|------|------|
| 開啟 Lab | `ckad cluster create` | 建立 kind cluster，套用初始設定 |
| 銷毀 Lab | `ckad cluster delete` | 完全刪除 kind cluster 與所有資源 |
| 重製 Lab | `ckad cluster reset` | 刪除後重建，回到乾淨初始狀態 |
| 查看狀態 | `ckad cluster status` | 顯示 cluster 健康狀態 |

### 2.2 練習模式

| 功能 | 指令 | 說明 |
|------|------|------|
| 列出題目 | `ckad list` | 顯示所有題目（可過濾 domain/difficulty） |
| 互動練習 | `ckad practice` | 逐題練習，自動執行 setup → 顯示題目 → 驗證 → cleanup |
| 驗證答案 | `ckad verify <id>` | 單題驗證，不進入互動模式 |
| 匯入題目 | `ckad fetch <url>` | 從 GitHub Markdown URL 匯入題目 |

### 2.3 題目系統

- 題目為 **YAML 格式**，包含：`id`, `domain`, `title`, `prompt`, `setup[]`, `verify[]`, `cleanup[]`
- `setup[]`：題目前置環境指令（自動執行）
- `verify[]`：答案驗證規則（透過 kubernetes Python client）
- `cleanup[]`：練習後清理指令（自動執行）

### 2.4 驗證引擎

透過 `kubernetes` Python client 直接與 kind cluster 通訊，支援以下 CheckType：

- Pod 類：`pod_exists`, `pod_running`, `pod_image`, `pod_label`
- Deployment 類：`deployment_exists`, `deployment_replicas`, `deployment_image`
- Service 類：`service_exists`, `service_type`, `service_port`
- 儲存類：`pv_exists`, `pvc_exists`, `pvc_bound`
- 其他：`namespace_exists`, `configmap_exists`, `configmap_key`, `secret_exists`, `job_exists`, `job_completed`, `cronjob_exists`, `ingress_exists`, `container_resources`, `kubectl_output`

### 2.5 計分系統

- 每題有 `weight`（1~30，預設 10）
- 單題得分 = `weight × (通過 check 數 / 總 check 數)`
- 練習結束顯示總分報告（CKAD 及格線：**66%**）

---

## 3. 技術架構

### 3.1 技術棧

| 層級 | 技術 |
|------|------|
| 語言 | Python 3.11+ |
| 套件管理 | uv |
| CLI 框架 | Typer |
| UI 輸出 | Rich |
| 資料模型 | Pydantic |
| K8s 通訊 | kubernetes（Python client） |
| 本地叢集 | kind（Kubernetes in Docker） |
| 容器 | Docker |

### 3.2 檔案結構

```
ckad-practice/
├── kind/
│   ├── cluster-config.yaml   # kind cluster 設定（單節點）
│   ├── setup.sh              # 初始化腳本（建立 cluster + 安裝依賴）
│   └── reset.sh              # 重製腳本
├── questions/                # 題庫（YAML），依 domain 分資料夾
│   ├── 01-design-build/
│   ├── 02-env-config/
│   ├── 03-deployment/
│   ├── 04-services/
│   ├── 05-observability/
│   ├── 06-misc/
│   └── custom/               # 使用者自訂題目
├── src/
│   ├── main.py               # CLI 入口（Typer app）
│   ├── schema.py             # Pydantic 資料模型（Question, CheckResult）
│   ├── loader.py             # 題目載入器（從 YAML 載入，支援 fetch）
│   ├── verifier.py           # 驗證邏輯（CheckType dispatcher）
│   ├── scorer.py             # 計分模組
│   ├── environment.py        # kind cluster 管理（create/delete/reset/status）
│   └── ui.py                 # Rich UI 元件（表格、進度條、報告）
└── pyproject.toml
```

### 3.3 CLI 入口設計

```
ckad <command> [options]
  practice  [--domain 1~6] [--difficulty] [--id] [--skip-verify] [--context]
  list      [--domain 1~6] [--difficulty]
  verify    <id>
  fetch     <url> [--save]
  cluster   <create|delete|reset|status>
```

---

## 4. 題目 YAML Schema

```yaml
id: "03-01"                          # 必填，唯一識別
domain: "Application Deployment"    # 必填
weight: 15                           # 選填，預設 10
difficulty: medium                   # easy / medium / hard
title: "建立 Deployment 含資源限制"
prompt: |
  請在 foo namespace 建立名為 my-deployment 的 Deployment...
tips: |
  使用 kubectl create deployment --help
setup:
  - "kubectl create namespace foo"
verify:
  - type: deployment_exists
    name: my-deployment
    namespace: foo
  - type: deployment_replicas
    name: my-deployment
    namespace: foo
    replicas: 3
cleanup:
  - "kubectl delete namespace foo --force"
sources:
  - repo: jamesbuckett/ckad-questions
    file: 03-ckad-deployment.md
tags:
  - deployment
  - resources
```

---

## 5. 題庫規劃

| Domain | 代碼 | CKAD 比重 | 目標題數 |
|--------|------|-----------|---------|
| Application Design and Build | 01 | 20% | 15 題 |
| Environment, Configuration & Security | 02 | 25% | 16 題 |
| Application Deployment | 03 | 20% | 10 題 |
| Services and Networking | 04 | 20% | 8 題 |
| Observability and Maintenance | 05 | 15% | 12 題 |
| Miscellaneous | 06 | — | 4 題 |
| **合計** | | | **65 題** |

來源：
- [jamesbuckett/ckad-questions](https://github.com/jamesbuckett/ckad-questions)（33 題）
- [bmuschko/ckad-crash-course](https://github.com/bmuschko/ckad-crash-course)（32 題）

---

## 6. 系統需求

| 工具 | 最低版本 |
|------|---------|
| Docker | 20.10+ |
| kind | 0.20+ |
| kubectl | 1.28+ |
| Python | 3.11+ |
| uv | 0.4+ |

---

## 7. 非功能需求

- **隔離性**：每道題的 setup/cleanup 確保環境互不干擾
- **離線可用**：僅需本地 Docker + kind，不依賴外部服務
- **快速重置**：`cluster reset` 完成時間 < 2 分鐘
- **可擴充性**：使用者可新增 custom/ 題目，無需修改核心程式碼

---

## 8. 超出範圍（Out of Scope）

- 網頁 UI（純 CLI）
- 雲端叢集支援（僅 kind 本地）
- 多使用者/帳號系統
- 自動更新題庫

---

## 9. 里程碑規劃

| 里程碑 | 目標 |
|--------|------|
| M1 | kind cluster 生命週期管理（create/delete/reset/status） |
| M2 | 題目 YAML schema + 載入器 + CLI 骨架 |
| M3 | 驗證引擎（全 CheckType 實作） |
| M4 | 互動練習模式 + 計分報告 |
| M5 | 題庫填充（65 題） + fetch 功能 |
| M6 | 整合測試 + README 完整文件 |
