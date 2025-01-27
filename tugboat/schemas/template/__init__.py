from __future__ import annotations

import functools
import itertools
import os
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from tugboat.schemas.arguments import Arguments
from tugboat.schemas.basic import Array, Dict
from tugboat.schemas.template.container import (
    ContainerNode,
    ContainerTemplate,
    ScriptTemplate,
)
from tugboat.schemas.template.volume import VolumeMount

if os.getenv("DOCUTILSCONFIG"):
    __all__ = [
        "ContainerSetRetryStrategy",
        "ContainerSetTemplate",
        "SuspendTemplate",
        "TemplateRef",
    ]


class _BaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Template(_BaseModel):
    """
    `Template`_ is a reusable and composable unit of execution in a workflow.

    .. _Template: https://argo-workflows.readthedocs.io/en/latest/fields/#template
    """

    activeDeadlineSeconds: int | str | None = None
    automountServiceAccountToken: bool | None = None
    container: ContainerTemplate | None = None
    containerSet: ContainerSetTemplate | None = None
    daemon: bool | None = None
    failFast: bool | None = None
    inputs: Arguments | None = None
    name: str | None = None
    nodeSelector: Dict[str, str] | None = None
    outputs: Arguments | None = None
    parallelism: int | None = None
    podSpecPatch: str | None = None
    priority: int | None = None
    priorityClassName: str | None = None
    schedulerName: str | None = None
    script: ScriptTemplate | None = None
    serviceAccountName: str | None = None
    steps: Array[Array[Step]] | None = None
    suspend: SuspendTemplate | None = None
    timeout: str | None = None

    affinity: Any | None = None
    archiveLocation: Any | None = None
    dag: Any | None = None
    data: Any | None = None
    executor: Any | None = None
    hostAliases: Array[Any] | None = None
    http: Any | None = None
    initContainers: Array[Any] | None = None
    memoize: Any | None = None
    metadata: Any | None = None
    metrics: Any | None = None
    plugins: Any | None = None
    resource: Any | None = None
    retryStrategy: Any | None = None
    securityContext: Any | None = None
    sidecars: Array[Any] | None = None
    synchronization: Any | None = None
    tolerations: Array[Any] | None = None
    volumes: Array[Any] | None = None

    def __hash__(self):
        return hash((self.name, self.container, self.script, self.steps))

    @functools.cached_property
    def step_dict(self) -> dict[str, Step]:
        """
        Step name to step data model mapping.

        .. note::

           Duplicate names will be overwritten and the empty name will be ignored.
        """
        return {
            step.name: step
            for step in itertools.chain.from_iterable(self.steps or ())
            if step.name
        }


# ----------------------------------------------------------------------------
# containerSet
# ----------------------------------------------------------------------------
class ContainerSetTemplate(_BaseModel):
    """
    `ContainerSetTemplate`_ to specify multiple containers to run within a single pod.

    .. _ContainerSetTemplate:
       https://argo-workflows.readthedocs.io/en/latest/fields/#containersettemplate
    """

    containers: Array[ContainerNode]
    retryStrategy: ContainerSetRetryStrategy | None = None
    volumeMounts: Array[VolumeMount] | None = None


class ContainerSetRetryStrategy(_BaseModel):
    duration: str | None = Field(None, pattern=r"\d+(ns|us|µs|ms|s|m|h)")
    retries: int | str


# ----------------------------------------------------------------------------
# steps
# ----------------------------------------------------------------------------
class Step(_BaseModel):
    """
    `Step`_ is a reference to a template to execute in a series of step.

    .. _Step: https://argo-workflows.readthedocs.io/en/latest/fields/#workflowstep
    """

    name: str

    arguments: Arguments | None = None
    inline: Template | None = None
    onExit: str | None = None
    template: str | None = None
    templateRef: TemplateRef | None = None
    when: str | None = None
    withItems: Array[str | bool | int | dict[str, Any]] | None = None
    withParam: str | None = None

    continueOn: Any | None = None
    hooks: Any | None = None
    withSequence: Any | None = None

    def __hash__(self):
        return hash((self.name, self.template, self.templateRef))


class TemplateRef(_BaseModel):
    """
    `TemplateRef`_ is a reference of template resource.

    .. _TemplateRef: https://argo-workflows.readthedocs.io/en/latest/fields/#templateref
    """

    clusterScope: bool | None = None
    name: str
    template: str


# ----------------------------------------------------------------------------
# suspend
# ----------------------------------------------------------------------------
class SuspendTemplate(_BaseModel):
    """
    `SuspendTemplate`_ is a template subtype to suspend a workflow at a predetermined point in time.

    .. _SuspendTemplate: https://argo-workflows.readthedocs.io/en/latest/fields/#suspendtemplate
    """

    duration: str | None = None
