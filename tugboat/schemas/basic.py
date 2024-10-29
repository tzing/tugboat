from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class _BaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ConfigMapKeySelector(_BaseModel):
    key: str
    name: str
    optional: bool | None = None


class Empty(_BaseModel): ...


class KeyValuePair(_BaseModel):
    key: str
    value: str


class NameValuePair(_BaseModel):
    name: str
    value: str


class PodMetadata(_BaseModel):
    annotations: dict[str, str] | None = None
    labels: dict[str, str] | None = None


class SecretKeySelector(_BaseModel):
    key: str
    name: str
    optional: bool | None = None
