#!/usr/bin/env bash
set -euo pipefail

CLUSTER_NAME="ckad"
CONFIG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "================================================"
echo "  CKAD Practice Environment Reset"
echo "================================================"
echo ""
echo "⚠️  這將會："
echo "   1. 刪除現有 kind cluster（含所有資源）"
echo "   2. 重新建立乾淨的 cluster"
echo "   3. 重新安裝基礎元件"
echo ""
read -rp "確認重製？(y/N) " confirm
if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
  echo "取消重製"
  exit 0
fi

echo ""
echo "🗑️  刪除現有 cluster..."
kind delete cluster --name "$CLUSTER_NAME" 2>/dev/null || echo "（cluster 不存在，略過）"

echo ""
echo "🔧 重新建立 cluster..."
kind create cluster --name "$CLUSTER_NAME" --config "$CONFIG_DIR/cluster-config.yaml"
echo "✅ Cluster 重建完成"

echo ""
echo "📦 重新安裝 Metrics Server..."
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
kubectl patch deployment metrics-server -n kube-system --type 'json' \
  -p '[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"}]' \
  2>/dev/null || true

echo ""
echo "📦 重新安裝 Contour Ingress..."
kubectl apply -f https://projectcontour.io/quickstart/contour.yaml 2>/dev/null || \
  echo "⚠️  Contour 安裝失敗，可手動補裝"

echo ""
echo "⏳ 等待 coredns 就緒..."
kubectl wait --for=condition=Available deployment/coredns -n kube-system --timeout=120s 2>/dev/null || true

echo ""
echo "================================================"
echo "  ✅ 環境重製完成！回到乾淨狀態"
echo "================================================"
