from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from tugboat.schemas.basic import ConfigMapKeySelector, Empty


class _BaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Parameter(_BaseModel):

    name: str

    default: str | None = None
    description: str | None = None
    enum: list[str] | None = None
    globalName: str | None = None
    value: Any | None = None
    valueFrom: ValueFrom | None = None


class ValueFrom(_BaseModel):
    configMapKeyRef: ConfigMapKeySelector | None = None
    default: str | None = None
    event: str | None = None
    expression: str | None = None
    jqFilter: str | None = None
    jsonPath: str | None = None
    parameter: str | None = None
    path: str | None = None
    supplied: Empty | None = None
