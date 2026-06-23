"""
Question schema definitions using Pydantic.
每道題的資料結構。
"""

from __future__ import annotations
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class Domain(str, Enum):
    DESIGN_BUILD = "Application Design and Build"
    ENV_CONFIG = "Application Environment, Configuration and Security"
    DEPLOYMENT = "Application Deployment"
    SERVICES = "Services and Networking"
    OBSERVABILITY = "Observability and Maintenance"
    MISC = "Miscellaneous"


class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class CheckType(str, Enum):
    # Namespace
    NAMESPACE_EXISTS = "namespace_exists"
    # Pod
    POD_EXISTS = "pod_exists"
    POD_RUNNING = "pod_running"
    POD_IMAGE = "pod_image"
    POD_LABEL = "pod_label"
    # Deployment
    DEPLOYMENT_EXISTS = "deployment_exists"
    DEPLOYMENT_REPLICAS = "deployment_replicas"
    DEPLOYMENT_IMAGE = "deployment_image"
    # Service
    SERVICE_EXISTS = "service_exists"
    SERVICE_TYPE = "service_type"
    SERVICE_PORT = "service_port"
    # ConfigMap / Secret
    CONFIGMAP_EXISTS = "configmap_exists"
    CONFIGMAP_KEY = "configmap_key"
    SECRET_EXISTS = "secret_exists"
    # PV / PVC
    PV_EXISTS = "pv_exists"
    PVC_EXISTS = "pvc_exists"
    PVC_BOUND = "pvc_bound"
    # Container resources
    CONTAINER_RESOURCES = "container_resources"
    # Job / CronJob
    JOB_EXISTS = "job_exists"
    JOB_COMPLETED = "job_completed"
    CRONJOB_EXISTS = "cronjob_exists"
    # Ingress
    INGRESS_EXISTS = "ingress_exists"
    # Generic kubectl output check
    KUBECTL_OUTPUT = "kubectl_output"


class VerifyCheck(BaseModel):
    type: CheckType
    # 通用欄位
    name: Optional[str] = None
    namespace: Optional[str] = None
    # Pod / container
    image: Optional[str] = None
    label: Optional[str] = None
    # Deployment
    replicas: Optional[int] = None
    # Service
    service_type: Optional[str] = None
    port: Optional[int] = None
    target_port: Optional[int] = None
    # Resources
    memory_request: Optional[str] = None
    memory_limit: Optional[str] = None
    cpu_request: Optional[str] = None
    cpu_limit: Optional[str] = None
    # ConfigMap / Secret key
    key: Optional[str] = None
    value: Optional[str] = None
    # Generic kubectl
    command: Optional[list[str]] = None
    expected_output: Optional[str] = None
    # Extra arbitrary fields
    extra: Optional[dict[str, Any]] = None


class QuestionSource(BaseModel):
    repo: Optional[str] = None
    file: Optional[str] = None
    url: Optional[str] = None


class Question(BaseModel):
    id: str
    domain: Domain
    weight: int = Field(default=10, ge=1, le=30)
    difficulty: Difficulty = Difficulty.MEDIUM
    title: str
    prompt: str
    tips: Optional[str] = None
    setup: list[str] = Field(default_factory=list)
    verify: list[VerifyCheck] = Field(default_factory=list)
    cleanup: list[str] = Field(default_factory=list)
    sources: list[QuestionSource] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
