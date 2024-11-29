from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from tugboat.schemas.arguments import Arguments
from tugboat.schemas.manifest import Manifest
from tugboat.schemas.template import Template


class WorkflowSpec(BaseModel):
    """
    `WorkflowSpec`_ is the specification of a Workflow.

    .. _WorkflowSpec: https://argo-workflows.readthedocs.io/en/latest/fields/#workflowspec
    """

    model_config = ConfigDict(extra="forbid")

    activeDeadlineSeconds: int | None = None
    archiveLogs: bool | None = None
    arguments: Arguments | None = None
    automountServiceAccountToken: bool | None = None
    dnsPolicy: str | None = None
    entrypoint: str | None = None
    hostNetwork: bool | None = None
    nodeSelector: dict[str, str] | None = None
    onExit: str | None = None
    parallelism: int | None = None
    podPriorityClassName: str | None = None
    podSpecPatch: str | None = None
    priority: int | None = None
    schedulerName: str | None = None
    serviceAccountName: str | None = None
    shutdown: str | None = None
    suspend: bool | None = None
    templateDefaults: Template | None = None
    templates: list[Template] | None = None
    workflowTemplateRef: WorkflowTemplateRef | None = None

    affinity: Any | None = None
    artifactGC: Any | None = None
    artifactRepositoryRef: Any | None = None
    dnsConfig: Any | None = None
    executor: Any | None = None
    hooks: Any | None = None
    hostAliases: list[Any] | None = None
    imagePullSecrets: list[Any] | None = None
    metrics: Any | None = None
    podDisruptionBudget: Any | None = None
    podGC: Any | None = None
    podMetadata: Any | None = None
    retryStrategy: Any | None = None
    securityContext: Any | None = None
    synchronization: Any | None = None
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


class Workflow(Manifest[WorkflowSpec]):
    """
    `Workflows` are the top-level resource in Argo Workflows that define a single
    unit of work.

    .. _Workflows: https://argo-workflows.readthedocs.io/en/latest/workflow-concepts/
    """

    apiVersion: Literal["argoproj.io/v1alpha1"]  # type: ignore[reportIncompatibleVariableOverride]
    kind: Literal["Workflow"]  # type: ignore[reportIncompatibleVariableOverride]


class WorkflowTemplate(Workflow):
    """
    `WorkflowTemplates`_ are reusable Workflow definitions stored in the cluster.

    .. _WorkflowTemplates: https://argo-workflows.readthedocs.io/en/latest/workflow-templates/
    """

    kind: Literal["WorkflowTemplate"]  # type: ignore[reportIncompatibleVariableOverride]
