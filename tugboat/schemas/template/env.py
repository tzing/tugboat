from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from tugboat.schemas.basic import ConfigKeySelector


class _BaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


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
