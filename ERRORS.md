# ERRORS.md — 踩坑與修復記錄

> **用途**：每次對話中發現的 Bug、環境問題與修復方案，供後續對話讀取以避免重複踩坑。
> 新對話開始時，AI 必須讀取本檔作為全局唯讀參考（見 `AGENTS.md` 第 4 條）。

---

## ERR-001：verifier.py 404 回傳完整 HTTP Response Headers

**發現日期**：2026-06-26  
**嚴重度**：中（影響使用者體驗，CLI 輸出雜訊過多）  
**狀態**：✅ 已修復

### 問題描述

執行 `uv run ckad verify 01-02` 時，若 Pod 尚未建立，`pod_running` 與 `pod_image` checks 的失敗訊息輸出完整的 HTTP response，包含：
- HTTP headers（`Content-Type`, `X-Kubernetes-Pf-*`, `Audit-Id` 等）
- 完整 JSON body（`{"kind":"Status","apiVersion":"v1",...}`）

導致每個失敗 check 輸出超過 20 行噪音。

### 根本原因

`_check_pod_running`、`_check_pod_image`、`_check_pod_label` 三個函式的 `except ApiException` 區塊直接使用 `return False, str(e)`。

`kubernetes.client.exceptions.ApiException.__str__()` 會格式化完整的 HTTP response（status + headers + body）為字串，而非只取 `e.status` 和 `e.reason`。

### 修復方案

**Step 1**：對 404 狀態碼加入明確判斷，回傳語義化訊息：

```python
# 修復前（_check_pod_running 為例）
except ApiException as e:
    return False, str(e)  # ← 輸出整個 HTTP response

# 修復後
except ApiException as e:
    if e.status == 404:
        return False, f"Pod '{c.name}' 不存在於 {ns}"
    return False, f"API 錯誤 {e.status}"
```

**Step 2**：全域替換所有其他函式的 `return False, str(e)`：

```python
# 修復前
return False, str(e)

# 修復後
return False, f"API 錯誤 {e.status}: {e.reason}"
```

影響範圍：`_check_deployment_replicas`、`_check_deployment_image`、`_check_service_type`、`_check_service_port`、`_check_configmap_key`、`_check_pvc_bound`、`_check_container_resources`、`_check_job_completed`。

### 預防措施

- 新增任何 `_check_*` 函式時，**禁止**使用 `str(e)` 作為錯誤訊息
- 標準模式：先判斷 `e.status == 404` → 語義化訊息；其餘 → `f"API 錯誤 {e.status}: {e.reason}"`

---

## ERR-002：Write tool 需要先 Read 才能寫入空檔案

**發現日期**：2026-06-26  
**嚴重度**：低（工具使用問題，不影響程式碼品質）  
**狀態**：✅ 已知，規避方式確立

### 問題描述

嘗試對已存在但內容為空的檔案（例如 `PROJECT_FRAME.md`）直接使用 Write tool，報錯：
```
File has not been read yet. Read the file first before writing to it.
```

### 根本原因

Write tool 在 Claude Code 中有保護機制：修改現有檔案前，必須先使用 Read tool 讀取，以確認 AI 看過原始內容，避免意外覆蓋。

### 規避方式

對已存在的空白檔（包含僅有 1 行換行的檔案）：
1. 先執行 Read 讀取（即使內容為空也需執行）
2. 再執行 Write 覆寫

---

## ERR-003：Edit tool old_string 上下文不足導致匹配失敗

**發現日期**：2026-06-26  
**嚴重度**：低（工具使用問題）  
**狀態**：✅ 已知，操作規範確立

### 問題描述

嘗試用 Edit tool 修復 `_check_pod_label` 的 exception handler 時，提供的 `old_string` 上下文不足，工具報告找不到匹配字串，導致第一次嘗試失敗。

### 根本原因

多個 `_check_*` 函式有相同或相似的 `except ApiException as e:` 結構，若 `old_string` 僅含 exception 區塊而不包含足夠的前後上下文，Edit tool 無法唯一定位目標位置。

### 規避方式

使用 Edit tool 修改重複片段時：
1. 先用 Read 確認目標區塊的完整行號與內容
2. `old_string` 必須包含**足夠唯一**的上下文（至少含函式名稱所在行）
3. 或改用 `replace_all=True` 做全域替換（適用於修改格式統一的模式）
