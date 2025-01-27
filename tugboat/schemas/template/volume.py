from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class VolumeMount(BaseModel):
    """
    `VolumeMount`_ describes a mounting of a `Volume`_ within a container.

    .. _VolumeMount: https://argo-workflows.readthedocs.io/en/latest/fields/#volumemount
    .. _Volume: https://kubernetes.io/docs/concepts/storage/volumes/
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    mountPath: str
    mountPropagation: str | None = None
    name: str
    readOnly: bool | None = None
    recursiveReadOnly: bool | None = None
    subPath: str | None = None
    subPathExpr: str | None = None
