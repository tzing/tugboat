from __future__ import annotations

import os
import typing

from pydantic import BaseModel, ConfigDict, field_validator
from pydantic_core import PydanticCustomError

from tugboat.schemas.basic import Array, ConfigKeySelector, Empty

if typing.TYPE_CHECKING:
    from typing import Any

if os.getenv("DOCUTILSCONFIG"):
    __all__ = ["ValueFrom"]


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
    valueFrom: ValueFrom | None = None

    value: bool | int | str | None = None
    """
    The literal value to use for the parameter.

    .. note::

       While documented as a string type in the official Argo Workflows documentation,
       this field also accepts boolean and integer values in practice.
    """

    def __hash__(self):
        return hash((repr(self.value), self.valueFrom))

    @field_validator("value", mode="plain")
    @classmethod
    def _validate_value(cls, value: Any) -> bool | int | str | None:
        if value is None:
            return value
        if isinstance(value, bool | int | str):
            return value
        raise PydanticCustomError("parameter_value_type_error", "")


class ValueFrom(_BaseModel):
    """
    `ValueFrom`_ describes a location in which to obtain the value to a parameter.

    .. _ValueFrom: https://argo-workflows.readthedocs.io/en/latest/fields/#valuefrom
    """

    configMapKeyRef: ConfigKeySelector | None = None
    default: str | None = None
    event: str | None = None
    expression: str | None = None
    jqFilter: str | None = None
    jsonPath: str | None = None
    parameter: str | None = None
    path: str | None = None
    supplied: Empty | None = None
