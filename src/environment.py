"""
Kind cluster 管理模組。
負責建立、重製、狀態查詢。
"""

from __future__ import annotations
import subprocess
import shutil
from pathlib import Path
from typing import Optional

CLUSTER_NAME = "ckad"
CONFIG_PATH = Path(__file__).parent.parent / "kind" / "cluster-config.yaml"

METRICS_SERVER_URL = (
    "https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml"
)
CONTOUR_URL = "https://projectcontour.io/quickstart/contour.yaml"


def _run(cmd: list[str], check: bool = True, capture: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        check=check,
        capture_output=capture,
        text=True,
    )


def is_cluster_running() -> bool:
    """回傳 kind cluster 是否存在。"""
    if not shutil.which("kind"):
        return False
    result = _run(["kind", "get", "clusters"], capture=True, check=False)
    return CLUSTER_NAME in result.stdout.split()


def get_cluster_info() -> dict:
    """取得 cluster 基本資訊。"""
    if not is_cluster_running():
        return {"running": False}

    result = _run(
        ["kubectl", "cluster-info", "--context", f"kind-{CLUSTER_NAME}"],
        capture=True, check=False,
    )
    node_result = _run(
        ["kubectl", "get", "nodes", "--no-headers"],
        capture=True, check=False,
    )
    nodes = [line.split() for line in node_result.stdout.strip().split("\n") if line]
    return {
        "running": True,
        "cluster_name": CLUSTER_NAME,
        "nodes": [{"name": n[0], "status": n[1], "role": n[2]} for n in nodes if len(n) >= 3],
    }


def create_cluster(with_components: bool = True) -> None:
    """建立 kind cluster。"""
    if is_cluster_running():
        raise RuntimeError(f"Cluster '{CLUSTER_NAME}' 已存在")
    _run(["kind", "create", "cluster", "--name", CLUSTER_NAME, "--config", str(CONFIG_PATH)])
    if with_components:
        _install_base_components()


def delete_cluster() -> None:
    """刪除 kind cluster。"""
    _run(["kind", "delete", "cluster", "--name", CLUSTER_NAME], check=False)


def reset_cluster() -> None:
    """重製 cluster（刪除後重建）。"""
    delete_cluster()
    _run(["kind", "create", "cluster", "--name", CLUSTER_NAME, "--config", str(CONFIG_PATH)])
    _install_base_components()


def _install_base_components() -> None:
    """安裝 metrics-server 與 contour。"""
    _run(["kubectl", "apply", "-f", METRICS_SERVER_URL], check=False)
    _run(
        [
            "kubectl", "patch", "deployment", "metrics-server",
            "-n", "kube-system", "--type", "json",
            "-p", '[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"}]',
        ],
        check=False,
    )
    _run(["kubectl", "apply", "-f", CONTOUR_URL], check=False)


def apply_setup_commands(commands: list[str]) -> list[tuple[str, bool, str]]:
    """
    執行題目的 setup 指令清單。
    回傳 [(command, success, output), ...]
    """
    results = []
    for cmd in commands:
        try:
            parts = cmd.strip().split()
            proc = _run(parts, capture=True, check=True)
            results.append((cmd, True, proc.stdout.strip()))
        except subprocess.CalledProcessError as e:
            results.append((cmd, False, e.stderr.strip()))
    return results


def apply_cleanup_commands(commands: list[str]) -> None:
    """執行 cleanup 指令，失敗不拋例外。"""
    for cmd in commands:
        try:
            _run(cmd.strip().split(), capture=True, check=False)
        except Exception:
            pass
