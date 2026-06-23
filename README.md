# CKAD Practice System

本地 Kubernetes 練習評分系統，用於備考 [CKAD（Certified Kubernetes Application Developer）](https://www.cncf.io/certification/ckad/) 認證。內建 65 道題目，涵蓋所有 CKAD 考試領域，透過 kind cluster 自動驗證答案並計分。

---

## 系統需求

| 工具 | 版本 | 安裝 |
|------|------|------|
| Docker | 20.10+ | [docs.docker.com](https://docs.docker.com/get-docker/) |
| kind | 0.20+ | `brew install kind` |
| kubectl | 1.28+ | `brew install kubectl` |
| uv | 0.4+ | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |

---

## 快速開始

```bash
# 1. 建立 kind cluster 並安裝 Python 依賴
bash kind/setup.sh

# 2. 列出所有題目
uv run ckad list

# 3. 開始互動式練習（全部題目）
uv run ckad practice

# 4. 練習特定領域（1~6）
uv run ckad practice --domain 3

# 5. 練習特定題目
uv run ckad practice --id 03-01

# 6. 只瀏覽題目，不連接叢集
uv run ckad practice --skip-verify
```

> **提示：** 若看到 `VIRTUAL_ENV` 警告，執行 `unset VIRTUAL_ENV` 後重試。

---

## CLI 指令

```
uv run ckad <command> [options]
```

| 指令 | 說明 |
|------|------|
| `practice` | 互動式練習模式（主要功能） |
| `list` | 列出所有可用題目 |
| `verify <id>` | 直接驗證指定題目，不進入練習模式 |
| `fetch <url>` | 從 GitHub Markdown URL 匯入題目 |
| `cluster <action>` | 管理 kind cluster |

### practice

```bash
uv run ckad practice [options]

Options:
  --domain, -d  1~6      過濾練習領域
  --difficulty           easy / medium / hard
  --id                   直接練習指定題目 ID（如 03-01）
  --skip-verify          只顯示題目，不驗證答案
  --context              kubectl context（預設 kind-ckad）
```

### list

```bash
uv run ckad list [--domain 1~6] [--difficulty easy|medium|hard]
```

### verify

```bash
uv run ckad verify 03-01
```

### fetch

```bash
# 從 GitHub 匯入並儲存到 custom/
uv run ckad fetch https://raw.githubusercontent.com/jamesbuckett/ckad-questions/main/03-ckad-deployment.md --save
```

### cluster

```bash
uv run ckad cluster status   # 查看 cluster 狀態
uv run ckad cluster create   # 建立 cluster
uv run ckad cluster reset    # 重製 cluster（清除所有資源）
uv run ckad cluster delete   # 刪除 cluster
```

---

## 題目結構

```
questions/
├── 01-design-build/     # Application Design and Build        (20%) — 15 題
├── 02-env-config/       # Environment, Configuration & Security (25%) — 16 題
├── 03-deployment/       # Application Deployment              (20%) — 10 題
├── 04-services/         # Services and Networking             (20%) —  8 題
├── 05-observability/    # Observability and Maintenance       (15%) — 12 題
├── 06-misc/             # Miscellaneous                               —  4 題
└── custom/              # 自定義題目（手動新增）
```

每道題為 YAML 格式：

```yaml
id: "03-01"
domain: Application Deployment
weight: 15          # 配分（1~30）
difficulty: medium  # easy / medium / hard
title: "建立 Deployment 含資源限制"
prompt: |
  # 題目描述（多行）
tips: |
  # 指令提示（可選）
setup:
  - "kubectl create namespace foo"   # 題目前置設定，自動執行
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

## 驗證機制（CheckType）

系統透過 `kubernetes` Python client 直接與 kind cluster 通訊驗證答案：

| CheckType | 說明 |
|-----------|------|
| `namespace_exists` | Namespace 存在 |
| `pod_exists` | Pod 存在 |
| `pod_running` | Pod 狀態為 Running |
| `pod_image` | Pod 使用指定 image |
| `pod_label` | Pod 具有指定 label |
| `deployment_exists` | Deployment 存在 |
| `deployment_replicas` | Deployment replica 數量符合 |
| `deployment_image` | Deployment 使用指定 image |
| `service_exists` | Service 存在 |
| `service_type` | Service 類型符合（ClusterIP / NodePort / LoadBalancer） |
| `service_port` | Service port / targetPort 符合 |
| `configmap_exists` | ConfigMap 存在 |
| `configmap_key` | ConfigMap 包含指定 key/value |
| `secret_exists` | Secret 存在 |
| `pv_exists` | PersistentVolume 存在 |
| `pvc_exists` | PersistentVolumeClaim 存在 |
| `pvc_bound` | PVC 已 Bound |
| `container_resources` | Container 資源限制符合 |
| `job_exists` | Job 存在 |
| `job_completed` | Job 已完成 |
| `cronjob_exists` | CronJob 存在 |
| `ingress_exists` | Ingress 存在 |
| `kubectl_output` | 執行自訂指令並比對輸出內容 |

---

## 計分方式

- 每道題有 `weight` 配分（預設 10，範圍 1~30）
- 單題得分 = `weight × (通過 check 數 / 總 check 數)`
- 練習結束後顯示總分報告及逐題明細
- CKAD 正式考試及格線：**66%**

---

## 新增自定義題目

複製任一現有 YAML，修改後放入 `questions/custom/` 即可自動載入：

```bash
cp questions/01-design-build/q01_docker_build.yaml questions/custom/my_question.yaml
# 編輯內容後直接使用
uv run ckad list
```

也可從 GitHub Markdown 匯入（支援 jamesbuckett 格式）：

```bash
uv run ckad fetch <github-raw-url> --save
```

---

## 重製環境

```bash
# 方法一：直接執行腳本
bash kind/reset.sh

# 方法二：透過 CLI
uv run ckad cluster reset
```

---

## 題目來源

| 來源 | 題數 | 說明 |
|------|------|------|
| [jamesbuckett/ckad-questions](https://github.com/jamesbuckett/ckad-questions) | 33 題 | 涵蓋 01~06 全部章節 |
| [bmuschko/ckad-crash-course](https://github.com/bmuschko/ckad-crash-course) | 32 題 | 全部 exercises 01~32 |

---

## 專案結構

```
ckad-practice/
├── kind/
│   ├── cluster-config.yaml   # kind cluster 設定
│   ├── setup.sh              # 初始化腳本
│   └── reset.sh              # 重製腳本
├── questions/                # 題庫（YAML）
├── src/
│   ├── main.py               # CLI 入口（Typer）
│   ├── schema.py             # Pydantic 資料模型
│   ├── loader.py             # 題目載入器
│   ├── verifier.py           # 答案驗證邏輯
│   ├── scorer.py             # 計分模組
│   ├── environment.py        # cluster 管理
│   └── ui.py                 # Rich UI 元件
└── pyproject.toml
```
