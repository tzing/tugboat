from __future__ import annotations

import os

from pydantic import BaseModel, ConfigDict, Field

from tugboat.schemas.basic import Dict

if os.getenv("DOCUTILSCONFIG"):
    __all__ = ["Metadata"]


class Manifest[T_Spec: BaseModel](BaseModel):
    """
    The base schema for the Kubernetes manifest.

    This schema is generic and must be inherited with the ``T_Spec`` type
    parameter, which is the schema for the :data:`spec` field of the manifest:

    .. code-block:: python

        class MyManifestSpec(BaseModel):
            ...

        class MyManifest(Manifest[MyManifestSpec]):
            ...
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    apiVersion: str
    kind: str
    metadata: Metadata
    spec: T_Spec

    @property
    def name(self) -> str | None:
        """Short-cut to the name of the manifest."""
        return self.metadata.name or self.metadata.generateName


class Metadata(BaseModel):
    """
    Kubernetes manifest metadata.
    """

    model_config = ConfigDict(frozen=True)

    name: str | None = Field(None, min_length=1, max_length=253)
    generateName: str | None = Field(None, min_length=1, max_length=248)
    labels: Dict[str, str] | None = None
    annotations: Dict[str, str] | None = None
