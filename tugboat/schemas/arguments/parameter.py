from __future__ import annotations

import os
from typing import Any

from pydantic import BaseModel, ConfigDict

from tugboat.schemas.basic import Array, ConfigKeySelector, Empty

if os.getenv("DOCUTILSCONFIG"):
    __all__ = ["RelaxedParameter", "ValueFrom"]


class _BaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Parameter(_BaseModel):
    """
    `Parameter`_ indicate a passed string parameter to a service template with
    an optional default value.

    .. _Parameter: https://argo-workflows.readthedocs.io/en/latest/fields/#parameter
    """

    default: str | None = None
    description: str | None = None
    enum: Array[str] | None = None
    globalName: str | None = None
    name: str
    value: bool | int | str | None = None
    valueFrom: ValueFrom | None = None


class RelaxedParameter(Parameter):
    """
    A relaxed version of :py:class:`Parameter` that allows some often misused fields.

    Please refer to the original class for the full list of fields.
    This class only shows the fields that are changed.
    """

    value: Any | None = None


class ValueFrom(_BaseModel):
    configMapKeyRef: ConfigKeySelector | None = None
    default: str | None = None
    event: str | None = None
    expression: str | None = None
    jqFilter: str | None = None
    jsonPath: str | None = None
    parameter: str | None = None
    path: str | None = None
    supplied: Empty | None = None
