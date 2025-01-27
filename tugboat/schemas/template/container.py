from __future__ import annotations

import os
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from tugboat.schemas.basic import Array
from tugboat.schemas.template.env import EnvFromSource, EnvVar
from tugboat.schemas.template.probe import Probe
from tugboat.schemas.template.volume import VolumeMount

if os.getenv("DOCUTILSCONFIG"):
    __all__ = [
        "ContainerSetRetryStrategy",
        "ContainerSetTemplate",
    ]


class _BaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class _ContainerEntry(_BaseModel):

    command: Array[str] | None = None
    env: Array[EnvVar] | None = None
    envFrom: Array[EnvFromSource] | None = None
    image: str
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
