#!/usr/bin/env bash
set -euo pipefail

CLUSTER_NAME="ckad"
CONFIG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$CONFIG_DIR")"

echo "================================================"
echo "  CKAD Practice Environment Setup"
echo "================================================"

check_deps() {
  local missing=()
  for cmd in kind kubectl docker uv; do
    if ! command -v "$cmd" &>/dev/null; then
      missing+=("$cmd")
    fi
  done
  if [ ${#missing[@]} -gt 0 ]; then
    echo "❌ 缺少依賴工具: ${missing[*]}"
    echo ""
    echo "  安裝 uv:   curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo "  安裝 kind: https://kind.sigs.k8s.io/docs/user/quick-start/#installation"
    exit 1
  fi
  echo "✅ 依賴檢查通過"
}

create_cluster() {
  if kind get clusters 2>/dev/null | grep -q "^${CLUSTER_NAME}$"; then
    echo "⚠️  Cluster '${CLUSTER_NAME}' 已存在，跳過建立"
  else
    echo "🔧 建立 kind cluster..."
    kind create cluster --name "$CLUSTER_NAME" --config "$CONFIG_DIR/cluster-config.yaml"
    echo "✅ Cluster 建立完成"
  fi
  kubectl cluster-info --context "kind-${CLUSTER_NAME}"
}

install_components() {
  echo ""
  echo "📦 安裝 Metrics Server..."
  kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
  kubectl patch deployment metrics-server -n kube-system --type 'json' \
    -p '[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"}]' \
    2>/dev/null || true

  echo ""
  echo "📦 安裝 Contour Ingress Controller..."
  kubectl apply -f https://projectcontour.io/quickstart/contour.yaml 2>/dev/null || \
    echo "⚠️  Contour 安裝失敗，可手動補裝"

  echo ""
  echo "⏳ 等待 coredns 就緒..."
  kubectl wait --for=condition=Available deployment/coredns -n kube-system --timeout=120s 2>/dev/null || true
}

install_python_deps() {
  echo ""
  echo "🐍 uv sync — 安裝 Python 依賴..."
  cd "$ROOT_DIR"
  uv sync
  echo "✅ Python 依賴安裝完成"
}

check_deps
create_cluster
install_components
install_python_deps

echo ""
echo "================================================"
echo "  ✅ 環境建立完成！"
echo ""
echo "  啟動練習系統："
echo "    cd $ROOT_DIR"
echo "    uv run python src/main.py"
echo "================================================"
