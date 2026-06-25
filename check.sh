#!/usr/bin/env bash
# check.sh — CKAD Practice System 驗收閘門測試
# 執行方式: bash check.sh
# 靜態 Gate（G1-G6）全部 PASS 才算通過；動態 Gate（G7-G8）需 kind cluster 運行

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
RESET='\033[0m'

PASS=0
FAIL=0
SKIP=0

pass() { echo -e "${GREEN}✅ PASS${RESET}  $1"; PASS=$((PASS + 1)); }
fail() { echo -e "${RED}❌ FAIL${RESET}  $1"; FAIL=$((FAIL + 1)); }
skip() { echo -e "${YELLOW}⚠️  SKIP${RESET}  $1"; SKIP=$((SKIP + 1)); }
section() { echo -e "\n${BOLD}── $1 ──${RESET}"; }

PY_RUNNER="uv run python"
CLI_RUNNER="uv run ckad"
SRC="src"

# ──────────────────────────────────────────────────────────────────
# G1: 依賴工具安裝
# ──────────────────────────────────────────────────────────────────
section "G1: 依賴工具安裝"

cmd_exists() { command -v "$1" &>/dev/null; }

cmd_exists kind    && pass "kind 已安裝"    || fail "kind 未安裝（請參考 https://kind.sigs.k8s.io/docs/user/quick-start/#installation）"
cmd_exists kubectl && pass "kubectl 已安裝" || fail "kubectl 未安裝"
cmd_exists docker  && pass "docker 已安裝"  || fail "docker 未安裝"
cmd_exists uv      && pass "uv 已安裝"      || fail "uv 未安裝（curl -LsSf https://astral.sh/uv/install.sh | sh）"

PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "0.0")
PY_MAJOR=$(echo "$PY_VER" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VER" | cut -d. -f2)
if [ "$PY_MAJOR" -ge 3 ] && [ "$PY_MINOR" -ge 11 ]; then
    pass "Python $PY_VER >= 3.11"
else
    fail "Python $PY_VER 未達 3.11（當前: $PY_VER）"
fi

# ──────────────────────────────────────────────────────────────────
# G2: Python 模組導入
# ──────────────────────────────────────────────────────────────────
section "G2: Python 模組導入"

import_ok() {
    local mod="$1"
    $PY_RUNNER -c "import sys; sys.path.insert(0,'$SRC'); import $mod" 2>/dev/null \
        && pass "import $mod" \
        || fail "import $mod 失敗"
}

import_ok schema
import_ok loader
import_ok verifier
import_ok scorer
import_ok environment
import_ok ui

# ──────────────────────────────────────────────────────────────────
# G3: CheckType + dispatch 完整性（23 種）
# ──────────────────────────────────────────────────────────────────
section "G3: CheckType + dispatch 完整性（23 種）"

CT_COUNT=$($PY_RUNNER -c "
import sys; sys.path.insert(0,'$SRC')
from schema import CheckType
print(len(CheckType))
" 2>/dev/null || echo 0)

if [ "$CT_COUNT" -eq 23 ]; then
    pass "CheckType 定義 $CT_COUNT 個值"
else
    fail "CheckType 數量=$CT_COUNT（預期 23）"
fi

DISPATCH_COUNT=$($PY_RUNNER -c "
import sys; sys.path.insert(0,'$SRC')
from verifier import _DISPATCH
print(len(_DISPATCH))
" 2>/dev/null || echo 0)

if [ "$DISPATCH_COUNT" -eq 23 ]; then
    pass "_DISPATCH 包含 $DISPATCH_COUNT 個 CheckType"
else
    fail "_DISPATCH 數量=$DISPATCH_COUNT（預期 23）"
fi

MISSING=$($PY_RUNNER -c "
import sys; sys.path.insert(0,'$SRC')
from schema import CheckType
from verifier import _DISPATCH
missing = [ct.value for ct in CheckType if ct not in _DISPATCH]
print(','.join(missing) if missing else 'OK')
" 2>/dev/null || echo "error")

if [ "$MISSING" = "OK" ]; then
    pass "_DISPATCH 完整覆蓋所有 CheckType"
else
    fail "_DISPATCH 缺少 CheckType: $MISSING"
fi

# ──────────────────────────────────────────────────────────────────
# G4: 題庫完整性
# ──────────────────────────────────────────────────────────────────
section "G4: 題庫完整性"

Q_COUNT=$($PY_RUNNER -c "
import sys; sys.path.insert(0,'$SRC')
import loader
print(len(loader.load_all()))
" 2>/dev/null || echo 0)

if [ "$Q_COUNT" -ge 65 ]; then
    pass "題庫載入 $Q_COUNT 道題目（>= 65）"
else
    fail "題庫載入 $Q_COUNT 道題目（預期 >= 65）"
fi

DUP_IDS=$($PY_RUNNER -c "
import sys; sys.path.insert(0,'$SRC')
import loader
qs = loader.load_all()
ids = [q.id for q in qs]
dups = [i for i in set(ids) if ids.count(i) > 1]
print(','.join(dups) if dups else 'OK')
" 2>/dev/null || echo "error")

if [ "$DUP_IDS" = "OK" ]; then
    pass "題目 ID 無重複"
else
    fail "重複 ID: $DUP_IDS"
fi

WEIGHT_BAD=$($PY_RUNNER -c "
import sys; sys.path.insert(0,'$SRC')
import loader
bad = [q.id for q in loader.load_all() if not (1 <= q.weight <= 30)]
print(','.join(bad) if bad else 'OK')
" 2>/dev/null || echo "error")

if [ "$WEIGHT_BAD" = "OK" ]; then
    pass "所有題目 weight 介於 1–30"
else
    fail "weight 超出範圍的題目: $WEIGHT_BAD"
fi

NO_VERIFY=$($PY_RUNNER -c "
import sys; sys.path.insert(0,'$SRC')
import loader
bad = [q.id for q in loader.load_all() if not q.verify]
print(','.join(bad) if bad else 'OK')
" 2>/dev/null || echo "error")

if [ "$NO_VERIFY" = "OK" ]; then
    pass "所有題目具有至少 1 條 verify[] 規則"
else
    fail "缺少 verify[] 的題目: $NO_VERIFY"
fi

# ──────────────────────────────────────────────────────────────────
# G5: 計分純函式邏輯
# ──────────────────────────────────────────────────────────────────
section "G5: 計分純函式邏輯"

SCORE_RESULT=$($PY_RUNNER -c "
import sys; sys.path.insert(0,'$SRC')
from scorer import QuestionResult, SessionResult
from schema import Question, VerifyCheck, CheckType, Domain, Difficulty

q = Question(
    id='gate-test',
    domain=Domain.DESIGN_BUILD,
    title='Gate Test',
    prompt='test',
    weight=10,
    difficulty=Difficulty.MEDIUM,
    verify=[
        VerifyCheck(type=CheckType.POD_EXISTS, name='p1'),
        VerifyCheck(type=CheckType.POD_EXISTS, name='p2'),
    ],
)

checks_all_pass = [
    {'check': q.verify[0], 'passed': True,  'message': 'ok'},
    {'check': q.verify[1], 'passed': True,  'message': 'ok'},
]
checks_half = [
    {'check': q.verify[0], 'passed': True,  'message': 'ok'},
    {'check': q.verify[1], 'passed': False, 'message': 'fail'},
]
checks_all_fail = [
    {'check': q.verify[0], 'passed': False, 'message': 'fail'},
    {'check': q.verify[1], 'passed': False, 'message': 'fail'},
]

r1 = QuestionResult(question=q, check_results=checks_all_pass, elapsed_seconds=0)
r2 = QuestionResult(question=q, check_results=checks_half,     elapsed_seconds=0)
r3 = QuestionResult(question=q, check_results=checks_all_fail, elapsed_seconds=0)

assert r1.score == 10.0, f'全通過應得 10.0，得到 {r1.score}'
assert r2.score == 5.0,  f'半通過應得 5.0，得到 {r2.score}'
assert r3.score == 0.0,  f'全失敗應得 0.0，得到 {r3.score}'

session = SessionResult()
session.add(r1)
session.finish()
assert session.percentage == 100.0, f'percentage 應為 100.0，得到 {session.percentage}'

print('OK')
" 2>/dev/null || echo "error")

if [ "$SCORE_RESULT" = "OK" ]; then
    pass "scorer 計分邏輯正確（全通過 10.0 / 半通過 5.0 / 全失敗 0.0）"
    pass "SessionResult.percentage 計算正確（100.0）"
else
    fail "scorer 計分邏輯錯誤，請執行 python -c 手動排查"
fi

# ──────────────────────────────────────────────────────────────────
# G6: CLI 基本運作
# ──────────────────────────────────────────────────────────────────
section "G6: CLI 基本運作"

cli_help_ok() {
    local args="$1"
    local desc="$2"
    if $CLI_RUNNER $args --help &>/dev/null; then
        pass "$desc"
    else
        fail "$desc"
    fi
}

cli_help_ok ""         "ckad --help 退出碼 0"
cli_help_ok "list"     "ckad list --help 退出碼 0"
cli_help_ok "practice" "ckad practice --help 退出碼 0"
cli_help_ok "verify"   "ckad verify --help 退出碼 0"
cli_help_ok "fetch"    "ckad fetch --help 退出碼 0"

LIST_OUT=$($CLI_RUNNER list 2>/dev/null || echo "")
LIST_LINES=$(echo "$LIST_OUT" | grep -c "│" || echo 0)
if [ "$LIST_LINES" -ge 65 ]; then
    pass "ckad list 顯示 $LIST_LINES 行題目（>= 65）"
else
    fail "ckad list 僅顯示 $LIST_LINES 行（預期 >= 65）"
fi

# ──────────────────────────────────────────────────────────────────
# G7: Cluster 動態測試（需 kind cluster）
# ──────────────────────────────────────────────────────────────────
section "G7: Cluster 動態測試（需 kind cluster 'ckad' 運行）"

if kind get clusters 2>/dev/null | grep -q "^ckad$"; then
    STATUS_OUT=$($CLI_RUNNER cluster status 2>&1)
    STATUS_CODE=$?
    if [ $STATUS_CODE -eq 0 ] && echo "$STATUS_OUT" | grep -qi "ckad"; then
        pass "ckad cluster status 退出碼 0，輸出包含 'ckad'"
    else
        fail "ckad cluster status 異常（exit=$STATUS_CODE）"
    fi

    NODE_COUNT=$(kubectl get nodes --context kind-ckad --no-headers 2>/dev/null | wc -l | tr -d ' ')
    if [ "$NODE_COUNT" -ge 3 ]; then
        pass "Cluster 具有 $NODE_COUNT 個節點（>= 3）"
    else
        fail "Cluster 節點數=$NODE_COUNT（預期 >= 3）"
    fi
else
    skip "kind cluster 'ckad' 未運行，跳過 G7（執行 'bash kind/setup.sh' 後可測試）"
    skip "（G7-2）Cluster 節點數檢查"
fi

# ──────────────────────────────────────────────────────────────────
# G8: verifier 404 錯誤訊息回歸防護（ERR-001）
# ──────────────────────────────────────────────────────────────────
section "G8: verifier 404 錯誤訊息格式（ERR-001 回歸防護）"

if kind get clusters 2>/dev/null | grep -q "^ckad$"; then
    VERIFY_OUT=$($CLI_RUNNER verify 01-02 2>&1 || true)
    if echo "$VERIFY_OUT" | grep -qiE "audit-id|content-type|application/json|x-kubernetes"; then
        fail "verifier 仍輸出 HTTP headers（ERR-001 回歸）"
    else
        pass "verifier 404 訊息格式乾淨（無 HTTP headers）"
    fi
else
    skip "kind cluster 'ckad' 未運行，跳過 G8（ERR-001 回歸防護）"
fi

# ──────────────────────────────────────────────────────────────────
# 總結
# ──────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
TOTAL=$((PASS + FAIL + SKIP))
echo -e "  測試總計: $TOTAL   ${GREEN}PASS: $PASS${RESET}   ${RED}FAIL: $FAIL${RESET}   ${YELLOW}SKIP: $SKIP${RESET}"
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"

if [ "$FAIL" -eq 0 ]; then
    echo -e "\n${GREEN}${BOLD}🎉 全部強制測試通過！CKAD Practice v0.1.0 驗收完成。${RESET}\n"
    exit 0
else
    echo -e "\n${RED}${BOLD}❌ $FAIL 項測試失敗，請依上方輸出修復後重新執行 bash check.sh${RESET}\n"
    exit 1
fi
