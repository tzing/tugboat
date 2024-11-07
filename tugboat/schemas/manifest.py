from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Manifest[T_Spec: BaseModel](BaseModel):
    """
    The base schema for the Kubernetes manifest.
    """

    model_config = ConfigDict(extra="forbid")

    apiVersion: str
    kind: str
    metadata: Metadata
    spec: T_Spec


class Metadata(BaseModel):
    """
    Kubernetes manifest metadata.
    """

    name: str | None = Field(None, min_length=1, max_length=253)
    generateName: str | None = Field(None, min_length=1, max_length=248)
    labels: dict = Field(default_factory=dict)
    annotations: dict = Field(default_factory=dict)
