from __future__ import annotations

import functools
import itertools
import os
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from tugboat.schemas.arguments import Arguments
from tugboat.schemas.basic import Array, ConfigKeySelector, Dict
from tugboat.schemas.template.probe import Probe
from tugboat.schemas.template.volume import VolumeMount

if os.getenv("DOCUTILSCONFIG"):
    __all__ = [
        "ContainerSetRetryStrategy",
        "ContainerSetTemplate",
        "EnvFromSource",
        "EnvVar",
        "EnvVarSource",
        "ObjectFieldSelector",
        "OptionalName",
        "ResourceFieldSelector",
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
# container / script
# ----------------------------------------------------------------------------
class _ContainerEntry(_BaseModel):

    image: str

    command: Array[str] | None = None
    env: Array[EnvVar] | None = None
    envFrom: Array[EnvFromSource] | None = None
    imagePullPolicy: Literal["Always", "Never", "IfNotPresent"] | None = None
    livenessProbe: Probe | None = None
    name: str | None = None
    readinessProbe: Probe | None = None
    restartPolicy: Literal["Always"] | None = None
    startupProbe: Probe | None = None
    stdin: bool | None = None
    stdinOnce: bool | None = None
    terminationMessagePath: str | None = None
    terminationMessagePolicy: Literal["File", "FallbackToLogsOnError"] | None = None
    tty: bool | None = None
    volumeMounts: Array[VolumeMount] | None = None
    workingDir: str | None = None

    lifecycle: Any | None = None
    ports: Array[Any] | None = None
    resizePolicy: Array[Any] | None = None
    resources: Any | None = None
    securityContext: Any | None = None
    volumeDevices: Array[Any] | None = None


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


class ContainerNode(_ContainerEntry):
    """
    Represents an individual `ContainerNode`_ within a `ContainerSetTemplate`_.

    .. _ContainerNode:
       https://argo-workflows.readthedocs.io/en/latest/fields/#containernode
    .. _ContainerSetTemplate:
       https://argo-workflows.readthedocs.io/en/latest/fields/#containersettemplate
    """

    args: Array[str] | None = None
    dependencies: Array[str] | None = None

    def __hash__(self):
        return hash((self.image, self.command, self.args))


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


# ----------------------------------------------------------------------------
# field - env
# ----------------------------------------------------------------------------
class EnvVar(_BaseModel):
    """
    `EnvVar`_ represents an environment variable present in a Container.

    .. _EnvVar: https://argo-workflows.readthedocs.io/en/latest/fields/#envvar
    """

    name: str
    value: str | None = None
    valueFrom: EnvVarSource | None = None


class EnvVarSource(_BaseModel):
    configMapKeyRef: ConfigKeySelector | None = None
    fieldRef: ObjectFieldSelector | None = None
    resourceFieldRef: ResourceFieldSelector | None = None
    secretKeyRef: ConfigKeySelector | None = None


class ObjectFieldSelector(_BaseModel):
    apiVersion: str | None = None
    fieldPath: str


class ResourceFieldSelector(_BaseModel):
    containerName: str | None = None
    divisor: str | None = None
    resource: str


# ----------------------------------------------------------------------------
# field - envFrom
# ----------------------------------------------------------------------------
class EnvFromSource(_BaseModel):
    """
    `EnvFromSource`_ represents the source of a set of ConfigMaps.

    .. _EnvFromSource: https://argo-workflows.readthedocs.io/en/latest/fields/#envfromsource
    """

    configMapRef: OptionalName | None = None
    prefix: str | None = None
    secretRef: OptionalName | None = None


class OptionalName(_BaseModel):
    """
    Represents a reference to a ConfigMap or Secret.
    This class is utilized by both the `ConfigMapEnvSource`_ and `SecretEnvSource`_ classes.

    .. _ConfigMapEnvSource:
       https://argo-workflows.readthedocs.io/en/latest/fields/#configmapenvsource
    .. _SecretEnvSource:
       https://argo-workflows.readthedocs.io/en/latest/fields/#secretenvsource
    """

    name: str
    optional: bool | None = None
