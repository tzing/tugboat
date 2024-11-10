from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from tugboat.schemas.arguments import Arguments


class Template(BaseModel):
    """
    `Template`_ is a reusable and composable unit of execution in a workflow.

    .. _Template: https://argo-workflows.readthedocs.io/en/latest/fields/#template
    """

    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    container: ContainerTemplate | None = None
    inputs: Arguments | None = None
    outputs: Arguments | None = None
    script: ScriptTemplate | None = None
    steps: list[list[Step]] | None = None

    # acknowledged fields
    activeDeadlineSeconds: int | str | None = None
    affinity: Any | None = None
    archiveLocation: Any | None = None
    automountServiceAccountToken: bool | None = None
    containerSet: Any | None = None
    daemon: bool | None = None
    dag: Any | None = None
    data: Any | None = None
    executor: Any | None = None
    failFast: bool | None = None
    hostAliases: list[Any] | None = None
    http: Any | None = None
    initContainers: list[Any] | None = None
    memoize: Any | None = None
    metadata: Any | None = None
    metrics: Any | None = None
    nodeSelector: dict[str, str] | None = None
    parallelism: int | None = None
    plugins: Any | None = None
    podSpecPatch: str | None = None
    priority: int | None = None
    priorityClassName: str | None = None
    resource: Any | None = None
    retryStrategy: Any | None = None
    schedulerName: str | None = None
    securityContext: Any | None = None
    serviceAccountName: str | None = None
    sidecars: list[Any] | None = None
    suspend: Any | None = None
    synchronization: Any | None = None
    timeout: str | None = None
    tolerations: list[Any] | None = None
    volumes: list[Any] | None = None


# ----------------------------------------------------------------------------
# container / script
# ----------------------------------------------------------------------------
class _ContainerEntry(BaseModel):

    model_config = ConfigDict(extra="forbid")

    image: str

    command: list[str] | None = None
    imagePullPolicy: Literal["Always", "Never", "IfNotPresent"] | None = None
    workingDir: str | None = None

    # acknowledged fields
    env: list[Any] | None = None
    envFrom: list[Any] | None = None
    lifecycle: Any | None = None
    livenessProbe: Any | None = None
    name: str | None = None
    ports: list[Any] | None = None
    readinessProbe: Any | None = None
    resizePolicy: list[Any] | None = None
    resources: Any | None = None
    restartPolicy: Literal["Always"] | None = None
    securityContext: Any | None = None
    startupProbe: Any | None = None
    stdin: bool | None = None
    stdinOnce: bool | None = None
    terminationMessagePath: str | None = None
    terminationMessagePolicy: Literal["File", "FallbackToLogsOnError"] | None = None
    tty: bool | None = None
    volumeDevices: list[Any] | None = None
    volumeMounts: list[Any] | None = None


class ContainerTemplate(_ContainerEntry):
    """
    A single application `container`_ that you want to run within a pod.

    .. _container: https://argo-workflows.readthedocs.io/en/latest/fields/#container
    """

    args: list[str] | None = None


class ScriptTemplate(_ContainerEntry):
    """
    `ScriptTemplate`_ is a template subtype to enable scripting through code steps.

    .. _ScriptTemplate: https://argo-workflows.readthedocs.io/en/latest/fields/#scripttemplate
    """

    source: str


# ----------------------------------------------------------------------------
# steps
# ----------------------------------------------------------------------------
class Step(BaseModel):
    """
    `Step`_ is a reference to a template to execute in a series of step.

    .. _Step: https://argo-workflows.readthedocs.io/en/latest/fields/#workflowstep
    """

    model_config = ConfigDict(extra="forbid")

    name: str

    arguments: Arguments | None = None
    template: str | None = None
    templateRef: TemplateRef | None = None
    when: str | None = None

    # acknowledged fields
    continueOn: Any | None = None
    hooks: Any | None = None
    inline: Template | None = None
    withItems: list[Any] | None = None
    withParam: str | None = None
    withSequence: Any | None = None


class TemplateRef(BaseModel):
    """
    `TemplateRef`_ is a reference of template resource.

    .. _TemplateRef: https://argo-workflows.readthedocs.io/en/latest/fields/#templateref
    """

    model_config = ConfigDict(extra="forbid")

    clusterScope: bool | None = None
    name: str
    template: str
