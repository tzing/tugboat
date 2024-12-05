from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from tugboat.schemas.basic import Dict


class Manifest[T_Spec: BaseModel](BaseModel):
    """
    The base schema for the Kubernetes manifest.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    apiVersion: str
    kind: str
    metadata: Metadata
    spec: T_Spec


class Metadata(BaseModel):
    """
    Kubernetes manifest metadata.
    """

    model_config = ConfigDict(frozen=True)

    name: str | None = Field(None, min_length=1, max_length=253)
    generateName: str | None = Field(None, min_length=1, max_length=248)
    labels: Dict[str, str] | None = None
    annotations: Dict[str, str] | None = None
