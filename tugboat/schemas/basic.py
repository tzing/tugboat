from __future__ import annotations

import typing

import frozendict
import pydantic_core.core_schema
from pydantic import BaseModel, ConfigDict

if typing.TYPE_CHECKING:
    from typing import Any

    from pydantic import GetCoreSchemaHandler
    from pydantic_core import CoreSchema


type Array[T] = tuple[T, ...]
"""Type alias representing an immutable sequence.
"""


class Dict[TK, TV](frozendict.frozendict[TK, TV]):
    """
    A frozen dictionary type that can be used in Pydantic models.
    """

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        if type_args := typing.get_args(source_type):
            key_type, value_type = type_args
        else:
            key_type = value_type = typing.Any

        key_schema = handler.generate_schema(key_type)
        value_schema = handler.generate_schema(value_type)

        return pydantic_core.core_schema.no_info_after_validator_function(
            function=frozendict.frozendict,
            schema=pydantic_core.core_schema.dict_schema(
                keys_schema=key_schema,
                values_schema=value_schema,
            ),
        )


class _BaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


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
    annotations: Dict[str, str] | None = None
    labels: Dict[str, str] | None = None


class SecretKeySelector(_BaseModel):
    key: str
    name: str
    optional: bool | None = None
