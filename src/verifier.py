"""
Answer verifier: 透過 kubernetes Python client 驗證叢集狀態。
每個 CheckType 對應一個 check 函式，回傳 (passed: bool, message: str)。
"""

from __future__ import annotations
import subprocess
from typing import Optional

from kubernetes import client, config
from kubernetes.client.exceptions import ApiException

from schema import VerifyCheck, CheckType

CheckResult = tuple[bool, str]


def load_k8s_config(context: str = "kind-ckad") -> None:
    """載入 kubeconfig。"""
    try:
        config.load_kube_config(context=context)
    except Exception:
        config.load_incluster_config()


# ─── 個別 check 函式 ────────────────────────────────────────────

def _check_namespace_exists(c: VerifyCheck) -> CheckResult:
    v1 = client.CoreV1Api()
    try:
        v1.read_namespace(c.name)
        return True, f"Namespace '{c.name}' 存在"
    except ApiException as e:
        if e.status == 404:
            return False, f"Namespace '{c.name}' 不存在"
        return False, f"API 錯誤 {e.status}: {e.reason}"


def _check_pod_exists(c: VerifyCheck) -> CheckResult:
    v1 = client.CoreV1Api()
    ns = c.namespace or "default"
    try:
        v1.read_namespaced_pod(c.name, ns)
        return True, f"Pod '{c.name}' 存在於 {ns}"
    except ApiException as e:
        if e.status == 404:
            return False, f"Pod '{c.name}' 不存在於 {ns}"
        return False, f"API 錯誤 {e.status}: {e.reason}"


def _check_pod_running(c: VerifyCheck) -> CheckResult:
    v1 = client.CoreV1Api()
    ns = c.namespace or "default"
    try:
        pod = v1.read_namespaced_pod(c.name, ns)
        phase = pod.status.phase
        if phase == "Running":
            return True, f"Pod '{c.name}' Running"
        return False, f"Pod '{c.name}' 狀態為 {phase}（預期 Running）"
    except ApiException as e:
        if e.status == 404:
            return False, f"Pod '{c.name}' 不存在於 {ns}"
        return False, f"API 錯誤 {e.status}"


def _check_pod_image(c: VerifyCheck) -> CheckResult:
    v1 = client.CoreV1Api()
    ns = c.namespace or "default"
    try:
        pod = v1.read_namespaced_pod(c.name, ns)
        images = [cont.image for cont in pod.spec.containers]
        if any(c.image in img for img in images):
            return True, f"Pod '{c.name}' 使用 image '{c.image}'"
        return False, f"Pod '{c.name}' image 為 {images}，預期包含 '{c.image}'"
    except ApiException as e:
        if e.status == 404:
            return False, f"Pod '{c.name}' 不存在於 {ns}"
        return False, f"API 錯誤 {e.status}"


def _check_pod_label(c: VerifyCheck) -> CheckResult:
    v1 = client.CoreV1Api()
    ns = c.namespace or "default"
    try:
        pod = v1.read_namespaced_pod(c.name, ns)
        labels = pod.metadata.labels or {}
        if "=" in (c.label or ""):
            k, v = c.label.split("=", 1)
            if labels.get(k) == v:
                return True, f"Pod '{c.name}' 有 label {c.label}"
            return False, f"Pod '{c.name}' labels={labels}，預期有 {c.label}"
        return False, "label 格式應為 key=value"
    except ApiException as e:
        if e.status == 404:
            return False, f"Pod '{c.name}' 不存在於 {ns}"
        return False, f"API 錯誤 {e.status}"


def _check_deployment_exists(c: VerifyCheck) -> CheckResult:
    apps = client.AppsV1Api()
    ns = c.namespace or "default"
    try:
        apps.read_namespaced_deployment(c.name, ns)
        return True, f"Deployment '{c.name}' 存在於 {ns}"
    except ApiException as e:
        if e.status == 404:
            return False, f"Deployment '{c.name}' 不存在於 {ns}"
        return False, f"API 錯誤 {e.status}: {e.reason}"


def _check_deployment_replicas(c: VerifyCheck) -> CheckResult:
    apps = client.AppsV1Api()
    ns = c.namespace or "default"
    try:
        dep = apps.read_namespaced_deployment(c.name, ns)
        actual = dep.spec.replicas
        if actual == c.replicas:
            return True, f"Deployment '{c.name}' replicas={actual} ✓"
        return False, f"Deployment '{c.name}' replicas={actual}，預期={c.replicas}"
    except ApiException as e:
        return False, f"API 錯誤 {e.status}: {e.reason}"


def _check_deployment_image(c: VerifyCheck) -> CheckResult:
    apps = client.AppsV1Api()
    ns = c.namespace or "default"
    try:
        dep = apps.read_namespaced_deployment(c.name, ns)
        images = [cont.image for cont in dep.spec.template.spec.containers]
        if any(c.image in img for img in images):
            return True, f"Deployment '{c.name}' image 包含 '{c.image}'"
        return False, f"Deployment '{c.name}' images={images}，預期包含 '{c.image}'"
    except ApiException as e:
        return False, f"API 錯誤 {e.status}: {e.reason}"


def _check_service_exists(c: VerifyCheck) -> CheckResult:
    v1 = client.CoreV1Api()
    ns = c.namespace or "default"
    try:
        v1.read_namespaced_service(c.name, ns)
        return True, f"Service '{c.name}' 存在於 {ns}"
    except ApiException as e:
        if e.status == 404:
            return False, f"Service '{c.name}' 不存在於 {ns}"
        return False, f"API 錯誤 {e.status}: {e.reason}"


def _check_service_type(c: VerifyCheck) -> CheckResult:
    v1 = client.CoreV1Api()
    ns = c.namespace or "default"
    try:
        svc = v1.read_namespaced_service(c.name, ns)
        actual = svc.spec.type
        if actual == c.service_type:
            return True, f"Service '{c.name}' type={actual} ✓"
        return False, f"Service '{c.name}' type={actual}，預期={c.service_type}"
    except ApiException as e:
        return False, f"API 錯誤 {e.status}: {e.reason}"


def _check_service_port(c: VerifyCheck) -> CheckResult:
    v1 = client.CoreV1Api()
    ns = c.namespace or "default"
    try:
        svc = v1.read_namespaced_service(c.name, ns)
        ports = [(p.port, p.target_port) for p in svc.spec.ports]
        for (port, target) in ports:
            if c.port and port != c.port:
                continue
            if c.target_port and str(target) != str(c.target_port):
                continue
            return True, f"Service '{c.name}' port 設定正確 {ports}"
        return False, f"Service '{c.name}' ports={ports}，預期 port={c.port} targetPort={c.target_port}"
    except ApiException as e:
        return False, f"API 錯誤 {e.status}: {e.reason}"


def _check_configmap_exists(c: VerifyCheck) -> CheckResult:
    v1 = client.CoreV1Api()
    ns = c.namespace or "default"
    try:
        v1.read_namespaced_config_map(c.name, ns)
        return True, f"ConfigMap '{c.name}' 存在於 {ns}"
    except ApiException as e:
        if e.status == 404:
            return False, f"ConfigMap '{c.name}' 不存在於 {ns}"
        return False, f"API 錯誤 {e.status}: {e.reason}"


def _check_configmap_key(c: VerifyCheck) -> CheckResult:
    v1 = client.CoreV1Api()
    ns = c.namespace or "default"
    try:
        cm = v1.read_namespaced_config_map(c.name, ns)
        data = cm.data or {}
        if c.key not in data:
            return False, f"ConfigMap '{c.name}' 沒有 key '{c.key}'"
        if c.value and data[c.key] != c.value:
            return False, f"ConfigMap '{c.name}[{c.key}]'={data[c.key]}，預期={c.value}"
        return True, f"ConfigMap '{c.name}[{c.key}]' ✓"
    except ApiException as e:
        return False, f"API 錯誤 {e.status}: {e.reason}"


def _check_secret_exists(c: VerifyCheck) -> CheckResult:
    v1 = client.CoreV1Api()
    ns = c.namespace or "default"
    try:
        v1.read_namespaced_secret(c.name, ns)
        return True, f"Secret '{c.name}' 存在於 {ns}"
    except ApiException as e:
        if e.status == 404:
            return False, f"Secret '{c.name}' 不存在於 {ns}"
        return False, f"API 錯誤 {e.status}: {e.reason}"


def _check_pv_exists(c: VerifyCheck) -> CheckResult:
    v1 = client.CoreV1Api()
    try:
        v1.read_persistent_volume(c.name)
        return True, f"PersistentVolume '{c.name}' 存在"
    except ApiException as e:
        if e.status == 404:
            return False, f"PersistentVolume '{c.name}' 不存在"
        return False, f"API 錯誤 {e.status}: {e.reason}"


def _check_pvc_exists(c: VerifyCheck) -> CheckResult:
    v1 = client.CoreV1Api()
    ns = c.namespace or "default"
    try:
        v1.read_namespaced_persistent_volume_claim(c.name, ns)
        return True, f"PVC '{c.name}' 存在於 {ns}"
    except ApiException as e:
        if e.status == 404:
            return False, f"PVC '{c.name}' 不存在於 {ns}"
        return False, f"API 錯誤 {e.status}: {e.reason}"


def _check_pvc_bound(c: VerifyCheck) -> CheckResult:
    v1 = client.CoreV1Api()
    ns = c.namespace or "default"
    try:
        pvc = v1.read_namespaced_persistent_volume_claim(c.name, ns)
        phase = pvc.status.phase
        if phase == "Bound":
            return True, f"PVC '{c.name}' 已 Bound ✓"
        return False, f"PVC '{c.name}' 狀態={phase}（預期 Bound）"
    except ApiException as e:
        return False, f"API 錯誤 {e.status}: {e.reason}"


def _check_container_resources(c: VerifyCheck) -> CheckResult:
    apps = client.AppsV1Api()
    ns = c.namespace or "default"
    name = c.name
    try:
        dep = apps.read_namespaced_deployment(name, ns)
        containers = dep.spec.template.spec.containers
        for cont in containers:
            r = cont.resources
            msgs = []
            if c.memory_request:
                actual = r.requests.get("memory") if r.requests else None
                if actual != c.memory_request:
                    msgs.append(f"memory.request={actual} 預期={c.memory_request}")
            if c.memory_limit:
                actual = r.limits.get("memory") if r.limits else None
                if actual != c.memory_limit:
                    msgs.append(f"memory.limit={actual} 預期={c.memory_limit}")
            if c.cpu_request:
                actual = r.requests.get("cpu") if r.requests else None
                if actual != c.cpu_request:
                    msgs.append(f"cpu.request={actual} 預期={c.cpu_request}")
            if c.cpu_limit:
                actual = r.limits.get("cpu") if r.limits else None
                if actual != c.cpu_limit:
                    msgs.append(f"cpu.limit={actual} 預期={c.cpu_limit}")
            if msgs:
                return False, f"Container resources 不符: {'; '.join(msgs)}"
        return True, f"Container resources 設定正確 ✓"
    except ApiException as e:
        return False, f"API 錯誤 {e.status}: {e.reason}"


def _check_job_exists(c: VerifyCheck) -> CheckResult:
    batch = client.BatchV1Api()
    ns = c.namespace or "default"
    try:
        batch.read_namespaced_job(c.name, ns)
        return True, f"Job '{c.name}' 存在於 {ns}"
    except ApiException as e:
        if e.status == 404:
            return False, f"Job '{c.name}' 不存在於 {ns}"
        return False, f"API 錯誤 {e.status}: {e.reason}"


def _check_job_completed(c: VerifyCheck) -> CheckResult:
    batch = client.BatchV1Api()
    ns = c.namespace or "default"
    try:
        job = batch.read_namespaced_job(c.name, ns)
        conditions = job.status.conditions or []
        for cond in conditions:
            if cond.type == "Complete" and cond.status == "True":
                return True, f"Job '{c.name}' 已完成 ✓"
        return False, f"Job '{c.name}' 尚未完成"
    except ApiException as e:
        return False, f"API 錯誤 {e.status}: {e.reason}"


def _check_cronjob_exists(c: VerifyCheck) -> CheckResult:
    batch = client.BatchV1Api()
    ns = c.namespace or "default"
    try:
        batch.read_namespaced_cron_job(c.name, ns)
        return True, f"CronJob '{c.name}' 存在於 {ns}"
    except ApiException as e:
        if e.status == 404:
            return False, f"CronJob '{c.name}' 不存在於 {ns}"
        return False, f"API 錯誤 {e.status}: {e.reason}"


def _check_ingress_exists(c: VerifyCheck) -> CheckResult:
    networking = client.NetworkingV1Api()
    ns = c.namespace or "default"
    try:
        networking.read_namespaced_ingress(c.name, ns)
        return True, f"Ingress '{c.name}' 存在於 {ns}"
    except ApiException as e:
        if e.status == 404:
            return False, f"Ingress '{c.name}' 不存在於 {ns}"
        return False, f"API 錯誤 {e.status}: {e.reason}"


def _check_kubectl_output(c: VerifyCheck) -> CheckResult:
    """執行自定義 kubectl 指令，比對輸出是否包含預期字串。"""
    try:
        result = subprocess.run(
            c.command, capture_output=True, text=True, timeout=15
        )
        output = result.stdout + result.stderr
        if c.expected_output and c.expected_output in output:
            return True, f"指令輸出包含預期內容 ✓"
        elif not c.expected_output and result.returncode == 0:
            return True, "指令執行成功 ✓"
        return False, f"輸出:\n{output.strip()[:300]}"
    except Exception as e:
        return False, f"API 錯誤 {e.status}: {e.reason}"


# ─── dispatch 表 ────────────────────────────────────────────────

_DISPATCH: dict[CheckType, callable] = {
    CheckType.NAMESPACE_EXISTS: _check_namespace_exists,
    CheckType.POD_EXISTS: _check_pod_exists,
    CheckType.POD_RUNNING: _check_pod_running,
    CheckType.POD_IMAGE: _check_pod_image,
    CheckType.POD_LABEL: _check_pod_label,
    CheckType.DEPLOYMENT_EXISTS: _check_deployment_exists,
    CheckType.DEPLOYMENT_REPLICAS: _check_deployment_replicas,
    CheckType.DEPLOYMENT_IMAGE: _check_deployment_image,
    CheckType.SERVICE_EXISTS: _check_service_exists,
    CheckType.SERVICE_TYPE: _check_service_type,
    CheckType.SERVICE_PORT: _check_service_port,
    CheckType.CONFIGMAP_EXISTS: _check_configmap_exists,
    CheckType.CONFIGMAP_KEY: _check_configmap_key,
    CheckType.SECRET_EXISTS: _check_secret_exists,
    CheckType.PV_EXISTS: _check_pv_exists,
    CheckType.PVC_EXISTS: _check_pvc_exists,
    CheckType.PVC_BOUND: _check_pvc_bound,
    CheckType.CONTAINER_RESOURCES: _check_container_resources,
    CheckType.JOB_EXISTS: _check_job_exists,
    CheckType.JOB_COMPLETED: _check_job_completed,
    CheckType.CRONJOB_EXISTS: _check_cronjob_exists,
    CheckType.INGRESS_EXISTS: _check_ingress_exists,
    CheckType.KUBECTL_OUTPUT: _check_kubectl_output,
}


def run_checks(checks: list[VerifyCheck], context: str = "kind-ckad") -> list[dict]:
    """
    執行所有 check，回傳結果清單：
    [{"check": VerifyCheck, "passed": bool, "message": str}, ...]
    """
    load_k8s_config(context)
    results = []
    for check in checks:
        fn = _DISPATCH.get(check.type)
        if fn is None:
            results.append({"check": check, "passed": False, "message": f"未知 check type: {check.type}"})
            continue
        try:
            passed, msg = fn(check)
        except Exception as e:
            passed, msg = False, f"例外: {e}"
        results.append({"check": check, "passed": passed, "message": msg})
    return results
