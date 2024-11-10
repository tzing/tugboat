from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from tugboat.schemas.arguments import Arguments
from tugboat.schemas.manifest import Manifest, Metadata
from tugboat.schemas.template import Template


class Workflow(Manifest):
    apiVersion: Literal["argoproj.io/v1alpha1"]  # type: ignore[reportIncompatibleVariableOverride]
    kind: Literal["Workflow"]  # type: ignore[reportIncompatibleVariableOverride]
    metadata: Metadata
    spec: Spec


class WorkflowTemplate(Workflow):
    kind: Literal["WorkflowTemplate"]  # type: ignore[reportIncompatibleVariableOverride]


class Spec(BaseModel):
    """
    `WorkflowSpec`_ is the specification of a Workflow.

    .. _WorkflowSpec: https://argo-workflows.readthedocs.io/en/latest/fields/#workflowspec
    """

    model_config = ConfigDict(extra="forbid")

    arguments: Arguments | None = None
    entrypoint: str | None = None
    templates: list[Template] | None = None
    workflowTemplateRef: WorkflowTemplateRef | None = None

    # acknowledged fields
    activeDeadlineSeconds: int | None = None
    affinity: Any | None = None
    archiveLogs: bool | None = None
    artifactGC: Any | None = None
    artifactRepositoryRef: Any | None = None
    automountServiceAccountToken: bool | None = None
    dnsConfig: Any | None = None
    dnsPolicy: str | None = None
    executor: Any | None = None
    hooks: Any | None = None
    hostAliases: list[Any] | None = None
    hostNetwork: bool | None = None
    imagePullSecrets: list[Any] | None = None
    metrics: Any | None = None
    nodeSelector: dict[str, str] | None = None
    onExit: str | None = None
    parallelism: int | None = None
    podDisruptionBudget: Any | None = None
    podGC: Any | None = None
    podMetadata: Any | None = None
    podPriorityClassName: str | None = None
    podSpecPatch: str | None = None
    priority: int | None = None
    retryStrategy: Any | None = None
    schedulerName: str | None = None
    securityContext: Any | None = None
    serviceAccountName: str | None = None
    shutdown: str | None = None
    suspend: bool | None = None
    synchronization: Any | None = None
    templateDefaults: Template | None = None
    tolerations: list[Any] | None = None
    ttlStrategy: Any | None = None
    volumeClaimGC: Any | None = None
    volumeClaimTemplates: list[Any] | None = None
    volumes: list[Any] | None = None
    workflowMetadata: Any | None = None


class WorkflowTemplateRef(BaseModel):

    model_config = ConfigDict(extra="forbid")

    name: str
    clusterScope: bool | None = None
