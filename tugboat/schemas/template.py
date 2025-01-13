from __future__ import annotations

import os
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from tugboat.schemas.arguments import Arguments
from tugboat.schemas.basic import Array, Dict

if os.getenv("DOCUTILSCONFIG"):
    __all__ = [
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
    timeout: str | None = None

    affinity: Any | None = None
    archiveLocation: Any | None = None
    containerSet: Any | None = None
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
    suspend: Any | None = None
    synchronization: Any | None = None
    tolerations: Array[Any] | None = None
    volumes: Array[Any] | None = None

    def __hash__(self):
        # Override the default __hash__ method to skip unhashable fields.
        return hash((self.name, self.container, self.script, self.steps))


# ----------------------------------------------------------------------------
# container / script
# ----------------------------------------------------------------------------
class _ContainerEntry(_BaseModel):

    image: str

    command: Array[str] | None = None
    imagePullPolicy: Literal["Always", "Never", "IfNotPresent"] | None = None
    name: str | None = None
    restartPolicy: Literal["Always"] | None = None
    stdin: bool | None = None
    stdinOnce: bool | None = None
    terminationMessagePath: str | None = None
    terminationMessagePolicy: Literal["File", "FallbackToLogsOnError"] | None = None
    tty: bool | None = None
    workingDir: str | None = None

    env: Array[Any] | None = None
    envFrom: Array[Any] | None = None
    lifecycle: Any | None = None
    livenessProbe: Any | None = None
    ports: Array[Any] | None = None
    readinessProbe: Any | None = None
    resizePolicy: Array[Any] | None = None
    resources: Any | None = None
    securityContext: Any | None = None
    startupProbe: Any | None = None
    volumeDevices: Array[Any] | None = None
    volumeMounts: Array[Any] | None = None


class ContainerTemplate(_ContainerEntry):
    """
    A single application `container`_ that you want to run within a pod.

    .. _container: https://argo-workflows.readthedocs.io/en/latest/fields/#container
    """

    args: Array[str] | None = None

    def __hash__(self):
        return hash((self.image, self.command, self.args))


class ScriptTemplate(_ContainerEntry):
    """
    `ScriptTemplate`_ is a template subtype to enable scripting through code steps.

    .. _ScriptTemplate: https://argo-workflows.readthedocs.io/en/latest/fields/#scripttemplate
    """

    source: str

    def __hash__(self):
        return hash((self.image, self.source))


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
