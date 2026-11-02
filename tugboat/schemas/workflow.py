from __future__ import annotations

import functools
import os
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from tugboat.schemas.arguments import Arguments
from tugboat.schemas.basic import Array, Dict
from tugboat.schemas.manifest import Manifest, Metadata
from tugboat.schemas.metrics import Metrics
from tugboat.schemas.template import PodResourceClaim, Template
from tugboat.schemas.template.container import ContainerTemplate, ResourceRequirements

if os.getenv("DOCUTILSCONFIG"):
    __all__ = [
        "ExecutorPlugin",
        "ExecutorPluginSidecar",
        "ExecutorPluginSpec",
        "WorkflowSpec",
        "WorkflowTemplateRef",
    ]


class WorkflowSpec(BaseModel):
    """
    `WorkflowSpec`_ is the specification of a Workflow.

    .. _WorkflowSpec: https://argo-workflows.readthedocs.io/en/latest/fields/#workflowspec
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    activeDeadlineSeconds: int | None = None
    archiveLogs: bool | None = None
    arguments: Arguments | None = None
    automountServiceAccountToken: bool | None = None
    dnsPolicy: str | None = None
    entrypoint: str | None = None
    executorPlugins: Array[ExecutorPlugin] | None = None
    hostNetwork: bool | None = None
    metrics: Metrics | None = None
    nodeSelector: Dict[str, str] | None = None
    onExit: str | None = None
    parallelism: int | None = None
    podPriorityClassName: str | None = None
    podResources: ResourceRequirements | None = None
    podSpecPatch: str | None = None
    priority: int | None = None
    resourceClaims: Array[PodResourceClaim] | None = None
    schedulerName: str | None = None
    serviceAccountName: str | None = None
    shutdown: str | None = None
    suspend: bool | None = None
    templateDefaults: Template | None = None
    templates: Array[Template] | None = None
    workflowTemplateRef: WorkflowTemplateRef | None = None

    affinity: Any | None = None
    artifactGc: Any | None = Field(None, alias="artifactGC")
    artifactRepositoryRef: Any | None = None
    dnsConfig: Any | None = None
    executor: Any | None = None
    hooks: Any | None = None
    hostAliases: Array[Any] | None = None
    imagePullSecrets: Array[Any] | None = None
    podDisruptionBudget: Any | None = None
    podGc: Any | None = Field(None, alias="podGC")
    podMetadata: Any | None = None
    retryStrategy: Any | None = None
    securityContext: Any | None = None
    synchronization: Any | None = None
    tolerations: Array[Any] | None = None
    ttlStrategy: Any | None = None
    volumeClaimGc: Any | None = Field(None, alias="volumeClaimGC")
    volumeClaimTemplates: Array[Any] | None = None
    volumes: Array[Any] | None = None
    workflowMetadata: Any | None = None

    def __hash__(self):
        return hash((self.arguments, self.templates))


class ExecutorPlugin(BaseModel):
    """
    `ExecutorPlugin <https://argo-workflows.readthedocs.io/en/latest/fields/#executorplugin>`__
    configures a workflow-level executor plugin.

    Execution requires the ``ARGO_WORKFLOW_LEVEL_EXECUTOR_PLUGINS`` feature gate.
    A nonempty plugin list overrides the controller ConfigMap configuration;
    omission or an empty list preserves the controller fallback.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    metadata: Metadata
    spec: ExecutorPluginSpec


class ExecutorPluginSpec(BaseModel):
    """
    `ExecutorPluginSpec <https://argo-workflows.readthedocs.io/en/latest/fields/#executorpluginspec>`__
    specifies the plugin sidecar.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    sidecar: ExecutorPluginSidecar


class ExecutorPluginSidecar(BaseModel):
    """
    `ExecutorPluginSidecar <https://argo-workflows.readthedocs.io/en/latest/fields/#executorpluginsidecar>`__
    configures the plugin container and optional service account token mounting.

    When mounting a token, the service account must be named
    ``<plugin-name>-executor-plugin``. This runtime constraint is not validated.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    automountServiceAccountToken: bool | None = None
    container: ContainerTemplate


class WorkflowTemplateRef(BaseModel):

    model_config = ConfigDict(extra="forbid", frozen=True)

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
    spec: WorkflowSpec

    @functools.cached_property
    def template_dict(self) -> dict[str, Template]:
        """
        Template name to template data model mapping.

        .. note::

           Duplicate names will be overwritten and the empty name will be ignored.
        """
        return {
            template.name: template
            for template in self.spec.templates or ()
            if template.name
        }


class WorkflowTemplate(Workflow):
    """
    `WorkflowTemplates`_ are reusable Workflow definitions stored in the cluster.

    .. _WorkflowTemplates: https://argo-workflows.readthedocs.io/en/latest/workflow-templates/
    """

    kind: Literal["WorkflowTemplate"]  # type: ignore[reportIncompatibleVariableOverride]
